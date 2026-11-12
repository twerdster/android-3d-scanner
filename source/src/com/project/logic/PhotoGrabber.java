package com.project.logic;

import java.io.FileOutputStream;

import com.project.activities.MainActivity;

import android.graphics.ImageFormat;
import android.hardware.Camera;
import android.hardware.Camera.PreviewCallback;
import android.util.Log;
import android.view.View;


public class PhotoGrabber implements Runnable, PreviewCallback {								
	//Public Members	
	public byte[][] mImages = null;
	//Private Members
	private SlideShow mSlideShow = null;	
	private Camera mCamera = null;				
	private String mSavepath = MainActivity.sProjectPath + "Calibration/";
	private int mNumOfpatterns = 0;
	private MainActivity mMainActivity = null;
	private Mode mMode = Mode.Calibrate;
	private XMLparser mXMLparser = null;
	private int mSyncDelay = 1000;
	private int mRows = 480;
	private int mCols = 800;	
	
	
	public static enum Mode { Calibrate, Reconstruct }
	
	public PhotoGrabber(){
		mMainActivity = MainActivity.GetMainActivity();				
		mXMLparser = mMainActivity.GetXmlParser();	
		mSlideShow = new SlideShow();
		mSyncDelay = mXMLparser.GetIntParam("SyncDelay", mSyncDelay);
		mRows = mXMLparser.GetIntParam("CameraRows", mRows);
		mCols = mXMLparser.GetIntParam("CameraColumns", mCols);
	}
	
	public void SetMode(Mode mode){
		mMode = mode;		
		switch (mMode){
		case Calibrate:
			mNumOfpatterns = 24;
			mNumOfpatterns = mXMLparser.GetIntParam("NumOfCalibPatterns", mNumOfpatterns);
			break;
		case Reconstruct:
			mNumOfpatterns = 12;
			mNumOfpatterns = mXMLparser.GetIntParam("NumOfDecodePatterns", mNumOfpatterns);
		}
		mImages = new byte[mNumOfpatterns][];
	}
	
	
	//Implement runnable
	public void run() {
		//Can't open camera -> return
		if (!InitializeCamera()){	
			mMainActivity.ShowToast("Failed initializing camera!");
			return;
		}		
		mSlideShow.SetVisibility(View.VISIBLE);
		mCamera.startPreview();
		int bufferSize = (mRows*mCols*3)/2;
		for (int i = 0; i < mNumOfpatterns; ++i){			
			mImages[i] = new byte[bufferSize];		
			mSlideShow.SetImage(i);
			Sleep(mSyncDelay);
			mCamera.addCallbackBuffer(mImages[i]);
			//Synchronize thread and picture callback.				
			Wait(mCamera);					
		}					
		//Close camera
		mCamera.stopPreview();
		mCamera.release();	
		if (mMode == Mode.Calibrate){
			SaveImages();
			//Post done!
			mSlideShow.SetVisibility(View.INVISIBLE);
			mMainActivity.ShowToast("Done!");
		}	
		mMainActivity.SetMenuVisibility(true);
	}		

	private void SaveImages(){		
		for (int i = 0; i < mImages.length; ++i) {
			String path = mSavepath + "image" + Integer.toString(i+1);
			try {
				FileOutputStream file = new FileOutputStream(path);
				file.write(mImages[i], 0, mRows*mCols);
				file.close();
			} catch (Exception e) {
				Log.e("PhotGrabber", "Failed saving image: " + path);
			}
		}	
	}
	
	//Try to initialize camera
	private boolean InitializeCamera(){
		mCamera = Camera.open();
		if (mCamera == null){
			return false;
		}				
		//Set camera params and callback
		try {				
			SetParams();
			mCamera.setPreviewDisplay(null);
			mCamera.setPreviewCallbackWithBuffer(this);
		} catch (Exception e) {
			mCamera.release();
			return false;
		}			
		return true;
	}
	
	private void SetParams() throws Exception{		
		Camera.Parameters params = mCamera.getParameters();		
		if (!params.getSupportedPreviewSizes().contains(mCamera.new Size(mCols, mRows))){
			String errMsg = "Preview size: " + Integer.toString(mCols) + "x" + Integer.toString(mRows) + " not supported";
			Log.e("PhotGrabber", errMsg);
			mMainActivity.ShowToast(errMsg);
			throw new Exception();
		}		
		params.setPreviewFormat(ImageFormat.NV21);
		params.setPreviewSize(mCols, mRows);
		params.setFocusMode(Camera.Parameters.FOCUS_MODE_AUTO);	
		mCamera.setParameters(params);				
	}
	//Implement runnable Preview CallBack
	public void onPreviewFrame(byte[] data, Camera camera) {								
		Notify(mCamera);
	}

	
	//Makes thread wait for object
	private void Wait(Object obj) {
		synchronized (obj) {
			try {
				obj.wait();				
			} catch (InterruptedException e) {
				e.printStackTrace();
			}			
		}
	}
	//Notify thread waiting on object
	private void Notify(Object obj){
		synchronized (obj) {
			obj.notify();					
		}	
	}

	
	private void Sleep(long time){
		try {
			Thread.sleep(time);
		} catch (Exception e) {}
	}
	
	public SlideShow GetSlideShow(){
		return mSlideShow;
	}
	
	public void FreeMemory(){
		mImages = null;
		System.gc();
	}
}//StartTest


