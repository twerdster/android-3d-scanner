package com.project.logic;

import com.project.R;
import com.project.activities.MainActivity;

import android.graphics.Bitmap;
import android.widget.ImageView;

//Changes images in imageview
public class SlideShow  {		
	private int[]   mImageArray = { 
			R.drawable.calib1,  R.drawable.calib2,  R.drawable.calib3,  
			R.drawable.calib4,  R.drawable.calib5,	R.drawable.calib6,  
			R.drawable.calib7,  R.drawable.calib8,	R.drawable.calib9,  
			R.drawable.calib10, R.drawable.calib11,	R.drawable.calib12, 
			R.drawable.calib13, R.drawable.calib14,	R.drawable.calib15, 
			R.drawable.calib16, R.drawable.calib17,	R.drawable.calib18, 
			R.drawable.calib19, R.drawable.calib20,	R.drawable.calib21, 
			R.drawable.calib22, R.drawable.calib23,	R.drawable.calib24 };
	private ImageView mImageView = null;	
	private MainActivity mMainActivity = null;
	// C'tor
	public SlideShow() {
		mMainActivity = MainActivity.GetMainActivity();
		mImageView = mMainActivity.GetImageView();
	}
		
	public void SetVisibility(final int visibility) {
		mMainActivity.runOnUiThread(new Runnable() {			
			@Override
			public void run() {				
				mImageView.setVisibility(visibility);
				mImageView.setImageResource(0);	
			}
		});
	}
	
	public void SetBitmap(final Bitmap bitmap){
		mMainActivity.runOnUiThread(new Runnable() {			
			@Override
			public void run() {				
				mImageView.setImageBitmap(bitmap);			
			}
		});	
	}
	public void SetImage(final int idx){
		mMainActivity.runOnUiThread(new Runnable() {			
			@Override
			public void run() {				
				mImageView.setImageResource(mImageArray[idx]);
			}
		});	
	}
}//SlideShow
