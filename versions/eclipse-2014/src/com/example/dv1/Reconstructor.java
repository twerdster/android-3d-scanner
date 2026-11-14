package com.example.dv1;

import java.io.FileOutputStream;

import android.graphics.Bitmap;
import android.graphics.Color;
import android.util.Log;


public class Reconstructor implements Runnable{		
		
	
	private int mColsC = 800;
	private int mColsP = 360;
	private int mRowsC = 480;
	private int mRowsP = 640;
	private int mNumTexturesForDecode = 12;	
	private int mNumGrayPatterns = 10;		
	private final String mDecodePath = MainActivity.sProjectPath + "Decode/";	
	
	private CalibrationFile mCalibFile = null;
	private XMLparser mXMLparser= null;
	
	private PhotoGrabber mPhotoGrabber = null; 
	private MainActivity mMainActivity = null;
	
	public void run() {		
		mPhotoGrabber.SetMode(PhotoGrabber.Mode.Reconstruct);
		mPhotoGrabber.run();
		DoReconstruction();		
		mMainActivity.ShowToast("Reconstruct done!");	
	}		
	
	public Reconstructor(){
		mMainActivity = MainActivity.GetMainActivity();
		mCalibFile = mMainActivity.GetCalibrationFile();
		mXMLparser = mMainActivity.GetXmlParser();
		mPhotoGrabber = mMainActivity.GetPhotoGrabber();
		LoadParams();		
	}
		
	private void  DoReconstruction(){
		//projector's xp coordinate, after decoding computation
		float[] XP = new float[mRowsC*mColsC];
		//camera's corrected coordinates (after radial correction)
		float[] XC = new float[mRowsC*mColsC];
		float[] YC = new float[mRowsC*mColsC];
		//3D output X/Y/Z axis
		float[] X = new float[mRowsC*mColsC];
		float[] Y = new float[mRowsC*mColsC];
		float[] Z = new float[mRowsC*mColsC];
		//output fidelity values
		float[] W = new float[mRowsC*mColsC];			
		DecodeGraySimpleBW(XP, W);
		NormalizeDecodedValues(XP);
		CorrectOpticalDistortionCPU(XC, YC);
		ReconstructCPU(X, Y, Z, XP, XC, YC);
		mPhotoGrabber.GetSlideShow().SetBitmap(CreateBitmap(Z));
		WriteBinary(X, "X");
		WriteBinary(Y, "Y");
		WriteBinary(Z, "Z");		
		Log.i("DoReconstruction", "Done!");
	}
	
	private void  DecodeGraySimpleBW(float[] ixp, float[] iF){
		byte[][] textures = mPhotoGrabber.mImages;								
		float eps = 0.001f;							
		float TH = 0.5f;							
		float denom;
		float x,xp,w;
		int g = 0;
		float p;		
		int i0 = 0;		
		for (int i = 0; i < mRowsC ; ++i) {
			for (int j = 0; j < mColsC ; ++j) {				
				denom = (byte)(textures[1][i0] - textures[0][i0]);
				if (denom < eps) denom = eps;
				denom = 1.0f/denom;				
				p = 0.5f;
				xp = 0.0f;
				g = 0;
				w = 0.0f;				
				for (int k = 0; k < mNumGrayPatterns ; ++k) {		
					float tempMinus = (byte)(textures[k+2][i0] - textures[0][i0]);
					x = tempMinus * denom;
					if (x < 0.0f) x = 0.0f;
					if (x > 1.0f) x = 1.0f;				
					w = w + p * Math.abs(x - 0.5f);	
					g ^= (x > TH) ? 1 : 0;					
					xp += (p*g);
					p = 0.5f*p;
				}	
				ixp[i0] = xp;
				iF[i0]  = w;
				i0++;
			}
		}
		Log.i("DecodeGraySimpleBW", "Done!");
	}
	
	private void  NormalizeDecodedValues(float[] ixp){
		float eps = 0.001f, aspectRatio = 1.0f;		
		int numProjectorLines = (int)Math.pow(2.0f, mNumGrayPatterns);					
		float pHalf = (float)(mColsP - 1.0f) / 2.0f;
		float a = aspectRatio * (float)numProjectorLines / pHalf;
		float b = -aspectRatio;
		
		for (int i = 0 ; i < mRowsC ; ++i) {
			for (int j = 0; j < mColsC ; ++j) {
				int idx = i*mColsC + j;
				ixp[idx] = a * ixp[idx] + b;
				if (ixp[idx] < (eps - aspectRatio) || ixp[idx] > (aspectRatio - eps)){
					ixp[idx] =  -99999.9f;
				}
			}
		}
		Log.i("NormalizeDecodedValues", "Done!");
	}
	
	private void  CorrectOpticalDistortionCPU(float[] XC,float[] YC){
		float k1, k2, k3, cx, cy, sx;
		// normalized coordinates
		float xn, yn;						
		float xHalf, yHalf, minHalfMinusOne;
		float rd, rdSquared, ru;
		//because calibration is done on full camera resolution
		xHalf = (1.0f + mRowsC) / 2.0f;		
		yHalf = (1.0f + mColsC) / 2.0f;
		minHalfMinusOne = Math.min(xHalf, yHalf) - 1.0f;
		int xOffset = (mRowsC - mRowsC)/2 + 1;
		int yOffset = (mColsC - mColsC)/2 + 1;
		int i,j;

		cx = mCalibFile.RD[0];
		cy = mCalibFile.RD[1];
		sx = mCalibFile.RD[2];
		k1 = mCalibFile.RD[3];
		k2 = mCalibFile.RD[4];
		k3 = mCalibFile.RD[5];

		for (i = 0 ; i < mRowsC ; ++i) {
			xn = (i + xOffset - xHalf) / minHalfMinusOne;
			for (j = 0 ; j < mColsC ; ++j) {
				yn = (j + yOffset - yHalf) / minHalfMinusOne;			
				rdSquared = ((xn - cx)*(xn - cx)/(sx *sx)) + (yn - cy)*(yn - cy);
				rd = (float)(Math.sqrt(rdSquared));
				ru = k1*rd + k2*rdSquared + k3*rd*rdSquared;
				XC[i*mColsC + j] = (float)(cx + (xn - cx) * (ru/rd));
				YC[i*mColsC + j] = (float)(cy + (yn - cy) * (ru/rd));
			}
		}
		
		
		
		Log.i("CorrectOpticalDistortionCPU", "Done!");
	}
	
	private void ReconstructCPU(float[] X,float[] Y,float[] Z,float[] XP,float[] XC,float[] YC){		
		float xc,yc,xp;
		float[][] Q = new float[3][4];	
		float[][] T = new float[3][3];
		float det;
		int i,j,idx;

		for (i = 0 ; i < mRowsC ; ++i) {
			for (j = 0 ; j < mColsC ; ++j) {

				idx = i*mColsC + j; 
				xc = XC[idx];
				yc = YC[idx];
				xp = XP[idx];

				Q[0][0] = xc*mCalibFile.C[8]  - mCalibFile.C[0];
				Q[0][1] = xc*mCalibFile.C[9]  - mCalibFile.C[1];
				Q[0][2] = xc*mCalibFile.C[10] - mCalibFile.C[2];
				Q[0][3] = xc*mCalibFile.C[11] - mCalibFile.C[3]; 
				Q[1][0] = yc*mCalibFile.C[8]  - mCalibFile.C[4];
				Q[1][1] = yc*mCalibFile.C[9]  - mCalibFile.C[5];
				Q[1][2] = yc*mCalibFile.C[10] - mCalibFile.C[6];
				Q[1][3] = yc*mCalibFile.C[11] - mCalibFile.C[7]; 
				Q[2][0] = xp*mCalibFile.P[8]  - mCalibFile.P[4];
				Q[2][1] = xp*mCalibFile.P[9]  - mCalibFile.P[5];
				Q[2][2] = xp*mCalibFile.P[10] - mCalibFile.P[6];
				Q[2][3] = xp*mCalibFile.P[11] - mCalibFile.P[7]; 

				det = Q[0][0]*(Q[2][2]*Q[1][1]-Q[2][1]*Q[1][2])-Q[1][0]*(Q[2][2]*Q[0][1]-Q[2][1]*Q[0][2])+Q[2][0]*(Q[1][2]*Q[0][1]-Q[1][1]*Q[0][2]);
				T[0][0] = -(Q[2][2]*Q[1][1]-Q[2][1]*Q[1][2]) / det;
				T[0][1] =  (Q[2][2]*Q[0][1]-Q[2][1]*Q[0][2]) / det;
				T[0][2] = -(Q[1][2]*Q[0][1]-Q[1][1]*Q[0][2]) / det;
				T[1][0] =  (Q[2][2]*Q[1][0]-Q[2][0]*Q[1][2]) / det;
				T[1][1] = -(Q[2][2]*Q[0][0]-Q[2][0]*Q[0][2]) / det;
				T[1][2] =  (Q[1][2]*Q[0][0]-Q[1][0]*Q[0][2]) / det;
				T[2][0] = -(Q[2][1]*Q[1][0]-Q[2][0]*Q[1][1]) / det;
				T[2][1] =  (Q[2][1]*Q[0][0]-Q[2][0]*Q[0][1]) / det;
				T[2][2] = -(Q[1][1]*Q[0][0]-Q[1][0]*Q[0][1]) / det;
				X[idx] = T[0][0]*Q[0][3] + T[0][1]*Q[1][3] + T[0][2]*Q[2][3];
				Y[idx] = T[1][0]*Q[0][3] + T[1][1]*Q[1][3] + T[1][2]*Q[2][3];
				Z[idx] = T[2][0]*Q[0][3] + T[2][1]*Q[1][3] + T[2][2]*Q[2][3];	
			}
		}
		Log.i("ReconstructCPU", "Done!");
		return;
	}
	
	private Bitmap CreateBitmap(float[] floatArr){
		float maxValid = 1, minValid = -1;		
		//byte[] byteArr = new byte[rowsC*colsC];
		int[] intArr = new int[mRowsC*mColsC];
		for (int i = 0 ; i < floatArr.length ; ++i){			
		    int j = ((i % mColsC)  * mRowsC) + (i / mColsC);
			if(floatArr[i] > 1f || floatArr[i] < -1f){
		    //	byteArr[j] = 0;
		    	intArr[j] = Color.rgb(0, 0, 0);
		    }
		    else{
		    	int color = (int)(255f*((floatArr[i] - minValid)/(maxValid - minValid)));
		    	intArr[j] = Color.rgb(color, color, color);
		    	//byteArr[j] = (byte)(255f*((floatArr[i] - minValid)/(maxValid - minValid)));
		    }	
		}
		return Bitmap.createBitmap(intArr, mRowsC, mColsC, Bitmap.Config.ARGB_8888);
	}
	
	private void WriteBinary(float[] buff , String name){        		
		byte[] outBuff = new byte[buff.length * 4];
		for (int i = 0; i < buff.length; ++i) {
			int floatBits = Float.floatToIntBits(buff[i]);
			outBuff[(i) * 4]     = (byte) (floatBits & 0xff);
			outBuff[(i) * 4 + 1] = (byte) ((floatBits >>  8)  & 0xff);
			outBuff[(i) * 4 + 2] = (byte) ((floatBits >> 16) & 0xff);
			outBuff[(i) * 4 + 3] = (byte) ((floatBits >> 24) & 0xff);
		}
		// ByteBuffer bf = ByteBuffer.allocate(buff.length * 4);
		// bf.order(ByteOrder.LITTLE_ENDIAN);
		// for (float ft : buff){
		// bf.putFloat(ft);
		// }
		try {
			FileOutputStream fos = new FileOutputStream(mDecodePath + name);
			fos.write(outBuff);
			fos.close();
			// fos.write(bf.array());
		} catch (Exception e) {
		}
		Log.i("WriteBinary:" + name, "Done!");
	}
	
	private void LoadParams(){
		mColsC = mXMLparser.GetIntParam("CameraColumns", mColsC);
		mRowsC = mXMLparser.GetIntParam("CameraRows", mRowsC);
		mColsP = mXMLparser.GetIntParam("ProjectorColumns", mColsP);
		mRowsP = mXMLparser.GetIntParam("ProjectorRows", mRowsP);
		mNumTexturesForDecode = mXMLparser.GetIntParam("NumOfDecodePatterns", mNumTexturesForDecode);		
		mNumGrayPatterns = mXMLparser.GetIntParam("NumOfGrayPatterns", mNumGrayPatterns);
	}

}
