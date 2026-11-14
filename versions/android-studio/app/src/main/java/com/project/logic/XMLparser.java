package com.project.logic;


import java.io.File;
import java.util.TreeMap;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;

import android.util.Log;



public class XMLparser {
	private Document mXMLDoc = null;
	private TreeMap<String, String> mParamsDB = new TreeMap<String, String>();
	
	public XMLparser(String xmlFilePath){		
		try {
			DocumentBuilder doctBuilder = DocumentBuilderFactory.newInstance().newDocumentBuilder();
			File f = new File(xmlFilePath);
			mXMLDoc = doctBuilder.parse(f);
		} catch (Exception e) {
			mXMLDoc = null;
		}		
	}
	
	public boolean Load(){
		boolean res = mXMLDoc != null;
		if(res){
			Element root = mXMLDoc.getDocumentElement();
			for (Node node =  root.getFirstChild() ; node != null ; node = node.getNextSibling()){
				mParamsDB.put(node.getNodeName(), node.getTextContent());
			}			
		}
		return res;
	}
	public String GetStringParam(String paramName, String defVal){
		String val = mParamsDB.get(paramName);
		if(val == null){
			Log.i("Paramater: " + paramName, "was not found!");
			return defVal;
		}					
		return val;
	}
	
	public int GetIntParam(String paramName, int defVal){
		String val = mParamsDB.get(paramName);
		if(val == null){
			Log.i("Paramater: " + paramName, "was not found!");
		}
		else{
			try {
				defVal = Integer.parseInt(val);
			} catch (Exception e) {	
				Log.i("Paramater: " + paramName + " value: " + val, "failed converting to integer!");			
			}	
		}	
		return defVal;
	}	
	
	
}//XMLparser
	

