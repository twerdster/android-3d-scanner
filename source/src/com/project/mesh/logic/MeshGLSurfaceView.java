package com.project.mesh.logic;

import java.nio.FloatBuffer;

import android.content.Context;
import android.opengl.GLSurfaceView;
import android.view.MotionEvent;
import android.view.ScaleGestureDetector;

public class MeshGLSurfaceView extends GLSurfaceView {

	private final MeshGLRenderer mRenderer;
	private ScaleGestureDetector mScaleDetector;
	
	public MeshGLSurfaceView(Context context, FloatBuffer floatBuffer) {
		super(context);
		
		setEGLContextClientVersion(2);
		
		mRenderer = new MeshGLRenderer(floatBuffer);
		setRenderer(mRenderer);
		
		setRenderMode(RENDERMODE_WHEN_DIRTY);	
		
		mScaleDetector = new ScaleGestureDetector(context, new ScaleListener());
	}

    private float mPreviousX;
    private float mPreviousY;

    @Override
    public boolean onTouchEvent(MotionEvent e) {
        // MotionEvent reports input details from the touch screen
        // and other input controls. In this case, you are only
        // interested in events where the touch position changed.

    	mScaleDetector.onTouchEvent(e);
    	
        float x = e.getX();
        float y = e.getY();

        
        switch (e.getAction()) {
        
        	case MotionEvent.ACTION_DOWN:
                break;
            case MotionEvent.ACTION_MOVE:

            	if (mScaleDetector.isInProgress()) {
            		break;
            	}
                
            	//Find the movement direction.
                float[] anchor = getArcballVector(mPreviousX, mPreviousY);
                float[] current = getArcballVector(x, y);
                float[] axis = crossProduct(anchor, current);
                normalize(axis);
                
                //Find the movement angle.
                float angle = (float)Math.acos(Math.min(1.0f, dotProduct(anchor, current)));
                
                //Apply the movement to the main Quaternion.
                Quaternion Q_rot = new Quaternion(axis, 4*angle);
                mRenderer.quat.mulInplace(Q_rot);
                
                requestRender();
                
                break;
        }

        mPreviousX = x;
        mPreviousY = y;
        	
        return true;
    }
    
    private float[] crossProduct(float v1[], float v2[]) {
    	float[] vR = new float[3];
        vR[0] =   ( (v1[1] * v2[2]) - (v1[2] * v2[1]) );
        vR[1] = - ( (v1[0] * v2[2]) - (v1[2] * v2[0]) );
        vR[2] =   ( (v1[0] * v2[1]) - (v1[1] * v2[0]) );
        
        return vR;
      }
    
    private float dotProduct(float v1[], float v2[]) {
    	return v1[0]*v2[0]+v1[1]*v2[1]+v1[2]*v2[2];
      }
    
    private void normalize(float[] _vector){
    	float magnitude = 
    			(float)(Math.sqrt(_vector[0]*_vector[0] + _vector[1]*_vector[1]  + _vector[2]*_vector[2]));
    	if (magnitude != 0) {
    		_vector[0] /= magnitude;
    		_vector[1] /= magnitude;
    		_vector[2] /= magnitude;
    	}
    }
    
    private float[] getArcballVector(float x, float y) {
		 float[] vec = {x/getWidth()*2 - 1, 1- y/getHeight()*2, 0};
		 float radius = 1.0f;//getWidth()/3;
		 float radius2 = radius*radius;
		 float length2 = vec[0]*vec[0]+vec[1]*vec[1];
		 
		 if (length2 < radius2) {
			vec[2] = (float) Math.sqrt(radius2 - length2);
		} else {
			normalize(vec);
		}
		 
		 return vec; 
	 }
    
    private class ScaleListener extends ScaleGestureDetector.SimpleOnScaleGestureListener {
    	@Override
    	public boolean onScale(ScaleGestureDetector detector) {
            mRenderer.mScale *= detector.getScaleFactor();
            
            // Don't let the object get too small or too large.
            mRenderer.mScale = Math.max(0.1f, Math.min(mRenderer.mScale, 5.0f));

            requestRender();
            return true;
        }
    }
}


