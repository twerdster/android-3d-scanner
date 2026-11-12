package com.project.activities;



import org.opencv.android.BaseLoaderCallback;
import org.opencv.android.LoaderCallbackInterface;
import org.opencv.android.OpenCVLoader;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.CountDownTimer;
import android.os.Environment;
import android.util.Log;
import android.view.Menu;
import android.view.MenuItem;
import android.widget.ImageView;
import android.widget.Toast;

import com.project.R;
import com.project.logic.CalibrationFile;
import com.project.logic.PhotoGrabber;
import com.project.logic.Reconstructor;
import com.project.logic.XMLparser;





public class MainActivity extends Activity {
			
	//Public Static Members
	public static final String sProjectPath = Environment.getExternalStorageDirectory().getPath() + "/Project/";
	
	
	//Private Members
	private MenuItem mItemCalibrate = null;
	private MenuItem mItemStart = null;
	private boolean mMenuVisible = true;
	private boolean mInitialized = false;	
	private int mCountDownTime = 2000; 		
	private final String mXmlPath = sProjectPath + "config.xml";
	private final String mCalibPath = sProjectPath + "calibration_CB_Ex.log";				
	private CalibrationFile mCalibFile = new CalibrationFile(mCalibPath);
	private XMLparser mXMLparser = new XMLparser(mXmlPath);	
	private PhotoGrabber mPhotoGrabber = null;
	private Reconstructor mReconstructor = null;
	private ImageView mImageView = null;	
	private static  MainActivity mMainActivity = null;
	
	
    private BaseLoaderCallback mLoaderCallback = new BaseLoaderCallback(this) {
        @Override
        public void onManagerConnected(int status) {
            switch (status) {
                case LoaderCallbackInterface.SUCCESS:
                {
                    Log.i("Loader", "OpenCV loaded successfully");
                   
                } break;
                default:
                {
                    super.onManagerConnected(status);
                } break;
            }
        }
    };
	
	
	
	@Override
	protected void onCreate(Bundle savedInstanceState) {		
		super.onCreate(savedInstanceState);				
		LoadCalibration();
		LoadXml();
		setContentView(R.layout.activity_main);
		mImageView = (ImageView)findViewById(R.id.imgView);
		mMainActivity = this;
		mPhotoGrabber = new PhotoGrabber();
		mReconstructor = new Reconstructor();			
	}
	
	
	public static MainActivity GetMainActivity(){
		return mMainActivity;
	}
	
	private void LoadXml(){
		if (!mXMLparser.Load()){
			Log.e("MainActivity", "Failed loading config XML.");
			ShowToast("Failed loading config XML.");
		}
		mCountDownTime = mXMLparser.GetIntParam("CountDownTime", mCountDownTime);		
	}
	
	private void LoadCalibration(){		
		mInitialized = mCalibFile.Load(); 
		if (!mInitialized){
			Log.e("MainActivity", "Failed loading camera config.");
			ShowToast("Failed loading camera config.");
		}		
	}
	
								
    @Override
    public void onResume(){
        super.onResume();         
        OpenCVLoader.initAsync(OpenCVLoader.OPENCV_VERSION_2_4_3, this, mLoaderCallback);
    }
    
    @Override
    protected void onActivityResult (int requestCode, int resultCode, Intent data){
    	mImageView.setImageDrawable(null);
    	mPhotoGrabber.FreeMemory();		
    }

	@Override
	public boolean onPrepareOptionsMenu(Menu menu) {		
		menu.getItem(0).setVisible(mMenuVisible);
		menu.getItem(1).setVisible(mMenuVisible);
		return true;
	}
	
	@Override
	public boolean onCreateOptionsMenu(Menu menu) {
		mItemCalibrate = menu.add("Calibrate");		
		mItemStart = menu.add("Start");
		return true;
	}
	
	@Override
	public void onBackPressed() {
		super.onBackPressed();
		System.exit(0);
	}

	@Override
    public boolean onOptionsItemSelected(MenuItem item) {
    	if (mInitialized == false){
    		ShowToast("Application is not initialized, please restart.");
    		return true;
    	}
		mMenuVisible = false;
    	Runnable runnable = null;
    	if (item == mItemCalibrate) {
    		mPhotoGrabber.SetMode(PhotoGrabber.Mode.Calibrate);
    		runnable = mPhotoGrabber;
    		Log.i("MainActivity", "Starting calibration.");
		}
    	else if (item == mItemStart){    		
    		runnable = mReconstructor;
    		Log.i("MainActivity", "Starting reconstruction.");
    	}
    	DoCountDown(mCountDownTime, runnable);
    	return true;
    }
	
	public void ShowToast(final String text) {				
		runOnUiThread(new Runnable() {			
			@Override
			public void run() {				
				Toast.makeText(mMainActivity, text, Toast.LENGTH_SHORT).show();
			}
		});		
	}
	
	
	private void DoCountDown(int time, final Runnable runnable){
		new CountDownTimer(time, 1000) {			
			@Override
			public void onTick(long millisUntilFinished) {
				ShowToast(Long.toString(millisUntilFinished/1000));				
			}			
			@Override
			public void onFinish() {
				new Thread(runnable).start();
			}
		}.start();		
	}
		
	public void SetMenuVisibility(boolean visible){
		mMenuVisible = visible;
	}
	
	public CalibrationFile GetCalibrationFile(){
		return mCalibFile;
	}
		
	public XMLparser GetXmlParser(){
		return mXMLparser;
	}
	
	public PhotoGrabber GetPhotoGrabber(){
		return mPhotoGrabber;
	}
	
	public Reconstructor GetReconstructor(){
		return mReconstructor;
	}
	
	public ImageView GetImageView(){
		return mImageView;
	}

	
}//MainActivity

