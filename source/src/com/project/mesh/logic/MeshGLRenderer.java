package com.project.mesh.logic;

import java.nio.FloatBuffer;

import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.opengles.GL10;

import android.opengl.GLES20;
import android.opengl.GLSurfaceView.Renderer;
import android.opengl.Matrix;

public class MeshGLRenderer implements Renderer {

	private Mesh mMesh;
	
	 private final float[] mMVPMatrix = new float[16];
	 private final float[] mProjMatrix = new float[16];
	 private final float[] mVMatrix = new float[16];

	 public volatile float mScale = 1.0f;
	 public volatile Quaternion quat = new Quaternion();
	 
	 private FloatBuffer fb;
	 
	 public MeshGLRenderer(FloatBuffer floatBuffer) {
		fb = floatBuffer;
	}
	 
	
	 @Override
	 public void onSurfaceCreated(GL10 arg0, EGLConfig config) {
		 GLES20.glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
		 GLES20.glClear(GLES20.GL_DEPTH_BUFFER_BIT | GLES20.GL_COLOR_BUFFER_BIT);

		 mMesh = new Mesh(fb);
	 }
	 
	@Override
	public void onDrawFrame(GL10 arg0) {
        GLES20.glClear(GLES20.GL_DEPTH_BUFFER_BIT | GLES20.GL_COLOR_BUFFER_BIT);
        
        GLES20.glEnable(GLES20.GL_DEPTH_TEST);
        
        
        // Initialize matrix to identity.
        Matrix.setIdentityM(mMVPMatrix, 0);
        
        // Create scaling.
        Matrix.scaleM(mMVPMatrix, 0, mScale, mScale, mScale);
        
        // Combine the rotation matrix with the projection and camera view
        float[] rotation = quat.toMatrix();
        float[] trans = new float[16];
        Matrix.transposeM(trans, 0, rotation, 0);
        Matrix.multiplyMM(mMVPMatrix, 0, trans, 0, mMVPMatrix, 0);

        // Set the camera position (View matrix)
        Matrix.setLookAtM(mVMatrix, 0, 0, 0, 2, 0f, 0f, 0f, 0f, -1.0f, 0.0f);
        
        Matrix.multiplyMM(mMVPMatrix, 0, mMVPMatrix, 0, mVMatrix, 0);
        Matrix.multiplyMM(mMVPMatrix, 0, mMVPMatrix, 0, mProjMatrix, 0);

        // Draw shape.
        mMesh.draw(mMVPMatrix);
	}

	@Override
	public void onSurfaceChanged(GL10 arg0, int width, int height) {
		GLES20.glViewport(0, 0, width, height);

		 float ratio = (float) width / height;

		 // this projection matrix is applied to object coordinates
		 // in the onDrawFrame() method
		 Matrix.frustumM(mProjMatrix, 0, -ratio, ratio, -1, 1, 3.0f, 8.0f);		
	}

	
	
	public static int loadShader(int type, String shaderCode){

	    // create a vertex shader type (GLES20.GL_VERTEX_SHADER)
	    // or a fragment shader type (GLES20.GL_FRAGMENT_SHADER)
	    int shader = GLES20.glCreateShader(type);

	    // add the source code to the shader and compile it
	    GLES20.glShaderSource(shader, shaderCode);
	    GLES20.glCompileShader(shader);

	    return shader;
	}

}
