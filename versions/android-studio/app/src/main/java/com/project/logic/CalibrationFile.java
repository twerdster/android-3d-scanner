package com.project.logic;

import java.io.BufferedReader;
import java.io.FileReader;

public class CalibrationFile {
	private String  path = "";
	public  float[] RD   = null;
	public	float[] C    = null;
	public  float[] P    = null;
	
	public CalibrationFile(String file){
		path = file;
	}
	
	public boolean Load(){
		try {
			BufferedReader reader = new BufferedReader(new FileReader(path));
			String line = null;
			while((line = reader.readLine()) != null)
			{
				if(line.contains("Radial correction 1:")){
					String[] tmp = reader.readLine().split("\t");
					RD = new float[tmp.length];
					for (int i = 0 ; i < tmp.length ; ++i){
						RD[i] = Float.valueOf(tmp[i]);
					}
				}
				else if(line.contains("Camera 1 matrix:")){
					line = reader.readLine() + reader.readLine() + reader.readLine();
					String tmp[] = line.split("\t");
					C = new float[tmp.length];
					for (int i = 0 ; i < tmp.length ; ++i){
						C[i] = Float.valueOf(tmp[i]);
					}
				}
				else if(line.contains("Camera 2 matrix:")){
					line = reader.readLine() + reader.readLine() + reader.readLine();
					String tmp[] = line.split("\t");
					P = new float[tmp.length];
					for (int i = 0 ; i < tmp.length ; ++i){
						P[i] = Float.valueOf(tmp[i]);
					}
				}	

			}
			reader.close();
		} catch (Exception e) {
			return false;
		}
		return true;	
	}	
}//CalibrationFile
