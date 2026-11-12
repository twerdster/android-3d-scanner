package com.project.activities;

import java.nio.FloatBuffer;

import android.app.Activity;
import android.opengl.GLSurfaceView;
import android.os.Bundle;
import android.util.Log;

import com.project.mesh.logic.MeshGLSurfaceView;

public class MeshViewActivity extends Activity {
	
	private GLSurfaceView meshGLView;

	
	@Override
	protected void onCreate(Bundle savedInstanceState) {		
		super.onCreate(savedInstanceState);	
		FloatBuffer fb = MainActivity.GetMainActivity().GetReconstructor().GetFloatBuffer();
		meshGLView = new MeshGLSurfaceView(this, fb);
		setContentView(meshGLView);
		Log.i("MeshViewActivity", "Mesh viewer started!");
	}

}
