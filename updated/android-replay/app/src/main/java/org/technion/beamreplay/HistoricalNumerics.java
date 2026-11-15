package org.technion.beamreplay;

import android.util.Log;

/** Mechanically selected historical numerical methods; see SOURCE_PROVENANCE.md.
 * Snapshot SHA-256: 720351709b2c5f6219cf2779ff5bef7c09380d934d601b1625b966e9e972ad4b
 * Original student credits: Arkadi Godlin and Alex Kligman; Alon Zvirin; Aaron Wetzler.
 * No new license is assigned to this historical adaptation.
 */
final class HistoricalNumerics {
    private final int mRowsC, mColsC, mColsP, mNumTexturesForDecode;
    private final Calibration mCalibFile;
    private final Captures mPhotoGrabber;
    static final class Calibration { float[] RD, C, P; }
    static final class Captures { byte[][] mImages; }
    HistoricalNumerics(ReplayScene scene) {
        mRowsC=scene.rows; mColsC=scene.cols; mColsP=scene.projectorColumns;
        mNumTexturesForDecode=scene.patternCount;
        mCalibFile=new Calibration(); mCalibFile.RD=scene.rd;
        mCalibFile.C=scene.camera; mCalibFile.P=scene.projector;
        mPhotoGrabber=new Captures(); mPhotoGrabber.mImages=scene.frames;
    }
    float[][] historical() {
        int n=mRowsC*mColsC;
        float[] xp=new float[n], w=new float[n], xc=new float[n], yc=new float[n];
        DecodeGraySimpleBW(xp,w); NormalizeDecodedValues(xp);
        CorrectOpticalDistortionCPU(xc,yc);
        return triangulate(xp,xc,yc);
    }
    float[][] triangulate(float[] xp,float[] xc,float[] yc) {
        int n=mRowsC*mColsC;
        float[] x=new float[n],y=new float[n],z=new float[n];
        ReconstructCPU(x,y,z,xp,xc,yc);
        return new float[][]{x,y,z};
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
				for (int k = 0; k < mNumTexturesForDecode-2; ++k) {
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
		int numProjectorLines = (int)Math.pow(2.0f, mNumTexturesForDecode);
		float pHalf = (float)(mColsP - 1.0f) / 2.0f;
		float a = aspectRatio * (float)numProjectorLines / pHalf;
		float b = -aspectRatio;

		for (int i = 0 ; i < mRowsC ; ++i) {
			for (int j = 0; j < mColsC ; ++j) {
				int idx = i*mColsC + j;
				ixp[idx] = a * ixp[idx] + b;
				if (ixp[idx] < (eps - aspectRatio) || ixp[idx] > (aspectRatio - eps)){
					ixp[idx] =  Float.NaN;//-99999.9f;
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

	private void ReconstructCPU(float[] X, float[] Y, float[] Z, float[] XP, float[] XC, float[] YC){
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

}
