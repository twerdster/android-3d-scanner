package com.project.mesh.logic;

import java.nio.FloatBuffer;

import android.opengl.GLES20;

public class Mesh {
	private final String vertexShaderCode =
			"uniform mat4 uMVPMatrix;" +

	        "attribute vec4 vPosition;" +
	        "void main() {" +
	        "  gl_Position = vPosition * uMVPMatrix;" +
	        "}";

	private final String fragmentShaderCode =
			"precision mediump float;" +
					"uniform vec4 vColor;" +
					"void main() {" +
					"  gl_FragColor = vColor;" +
					"}";

	
	private final int mProgram;
	private int mPositionHandle;
	private int mColorHandle;
	private int mMVPMatrixHandle;

	// number of coordinates per vertex in this array
	static final int COORDS_PER_VERTEX = 3;
	
	private final FloatBuffer vertexBuffer;
	private final int vertexCount;
	private final int vertexStride = COORDS_PER_VERTEX * 4; // 4 bytes per vertex
	
	// Set color with red, green, blue and alpha (opacity) values
	// If you want to change the color change here!
	float color[] = { 0.63671875f, 0.76953125f, 0.22265625f, 1.0f };

	public Mesh(FloatBuffer fb) {
		
		vertexBuffer = fb;
		vertexCount = fb.capacity() / COORDS_PER_VERTEX;
		
        // prepare shaders and OpenGL program
        int vertexShader = MeshGLRenderer.loadShader(GLES20.GL_VERTEX_SHADER,
                                                   vertexShaderCode);
        int fragmentShader = MeshGLRenderer.loadShader(GLES20.GL_FRAGMENT_SHADER,
                                                     fragmentShaderCode);

        mProgram = GLES20.glCreateProgram();             // create empty OpenGL Program
        GLES20.glAttachShader(mProgram, vertexShader);   // add the vertex shader to program
        GLES20.glAttachShader(mProgram, fragmentShader); // add the fragment shader to program
        GLES20.glLinkProgram(mProgram);                  // create OpenGL program executables
        
        
        
	}

	public void draw(float[] mvpMatrix) {
		// Add program to OpenGL environment
		GLES20.glUseProgram(mProgram);

		// get handle to vertex shader's vPosition member
		mPositionHandle = GLES20.glGetAttribLocation(mProgram, "vPosition");

		// Enable a handle to the vertices
		GLES20.glEnableVertexAttribArray(mPositionHandle);

		// Prepare the vertex coordinate data
		GLES20.glVertexAttribPointer(mPositionHandle, COORDS_PER_VERTEX,
				GLES20.GL_FLOAT, false,
				vertexStride, vertexBuffer);
		

		// Get handle to fragment shader's vColor member
		mColorHandle = GLES20.glGetUniformLocation(mProgram, "vColor");

		// Set color for drawing the mesh
		GLES20.glUniform4fv(mColorHandle, 1, color, 0);

		// Get handle to shape's transformation matrix
		mMVPMatrixHandle = GLES20.glGetUniformLocation(mProgram, "uMVPMatrix");

		// Apply the projection and view transformation
		GLES20.glUniformMatrix4fv(mMVPMatrixHandle, 1, false, mvpMatrix, 0);

		// Draw the mesh
		GLES20.glDrawArrays(GLES20.GL_POINTS, 0, vertexCount);

		// Disable vertex array
		GLES20.glDisableVertexAttribArray(mPositionHandle);
	}
}
