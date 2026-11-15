"""Compile unchanged archived numerical classes with new desktop-only adapters.

No Android/OpenCV behavior is emulated: UI, image processing and capture are
unavailable and throw if called. The reflection runner calls numerical methods
only, before Clear/median postprocessing.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'updated/build/headless'
SHIMS = {
'com/project/activities/MainActivity.java': '''package com.project.activities;
import com.project.logic.*;
public class MainActivity {
 public static String sProjectPath="";
 private static MainActivity instance;
 private CalibrationFile calibration;
 private XMLparser parser;
 private PhotoGrabber grabber;
 public static void configure(int rows,int cols,int projector,int count,float[] rd,float[] c,float[] p,byte[][] frames){
  instance=new MainActivity(); instance.calibration=new CalibrationFile("");
  instance.calibration.RD=rd; instance.calibration.C=c; instance.calibration.P=p;
  instance.parser=new XMLparser(rows,cols,projector,count); instance.grabber=new PhotoGrabber(frames);
 }
 public static MainActivity GetMainActivity(){return instance;}
 public CalibrationFile GetCalibrationFile(){return calibration;}
 public XMLparser GetXmlParser(){return parser;}
 public PhotoGrabber GetPhotoGrabber(){return grabber;}
 public void ShowToast(String s){throw new UnsupportedOperationException("UI unavailable");}
 public void startActivityForResult(Object o,int c){throw new UnsupportedOperationException("UI unavailable");}
}''',
'com/project/activities/MeshViewActivity.java':'package com.project.activities; public class MeshViewActivity {}',
'com/project/logic/PhotoGrabber.java':'''package com.project.logic;
public class PhotoGrabber {
 public enum Mode {Reconstruct}
 public byte[][] mImages;
 public PhotoGrabber(byte[][] images){mImages=images;}
 public void SetMode(Mode m){throw new UnsupportedOperationException("Capture unavailable");}
 public void run(){throw new UnsupportedOperationException("Capture unavailable");}
}''',
'com/project/logic/XMLparser.java':'''package com.project.logic;
public class XMLparser {
 private int rows,cols,projector,count;
 public XMLparser(int r,int c,int p,int n){rows=r;cols=c;projector=p;count=n;}
 public int GetIntParam(String name,int fallback){
  if(name.equals("CameraRows"))return rows; if(name.equals("CameraColumns"))return cols;
  if(name.equals("ProjectorColumns"))return projector;
  if(name.equals("NumOfDecodePatterns"))return count; return fallback;
 }
}''',
'android/content/Intent.java':'package android.content; public class Intent { public Intent(Object a,Class<?> b){} }',
'android/util/Log.java':'package android.util; public class Log { public static int i(String a,String b){return 0;} }',
'android/graphics/Color.java':'package android.graphics; public class Color { public static int rgb(int r,int g,int b){return 0;} }',
'android/graphics/Bitmap.java':'''package android.graphics; public class Bitmap {
 public enum Config {ARGB_8888} public enum CompressFormat {PNG}
 public static Bitmap createBitmap(int[] a,int w,int h,Config c){throw new UnsupportedOperationException("Bitmap unavailable");}
 public boolean compress(CompressFormat f,int q,java.io.OutputStream s){throw new UnsupportedOperationException("Bitmap unavailable");}
}''',
'org/opencv/core/CvType.java':'package org.opencv.core; public class CvType { public static final int CV_32F=5,CV_8U=0; }',
'org/opencv/core/Size.java':'package org.opencv.core; public class Size {}',
'org/opencv/core/Mat.java':'''package org.opencv.core; public class Mat {
 public Mat(int r,int c,int t){throw new UnsupportedOperationException("OpenCV unavailable");}
 public int put(int r,int c,float[] x){throw new UnsupportedOperationException();}
 public int put(int r,int c,byte[] x){throw new UnsupportedOperationException();}
 public int get(int r,int c,float[] x){throw new UnsupportedOperationException();}
}''',
'org/opencv/highgui/Highgui.java':'package org.opencv.highgui; public class Highgui { public static boolean imwrite(String s,org.opencv.core.Mat m){throw new UnsupportedOperationException("OpenCV unavailable");} }',
'org/opencv/imgproc/Imgproc.java':'package org.opencv.imgproc; public class Imgproc { public static void medianBlur(org.opencv.core.Mat a,org.opencv.core.Mat b,int k){throw new UnsupportedOperationException("OpenCV unavailable");} }',
}

def build():
    generated=BUILD/'shims'
    for path,text in SHIMS.items():
        dest=generated/path; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text(text+'\n')
    originals=[ROOT/'source/src/com/project/logic'/name for name in ['Reconstructor.java','CalibrationFile.java']]
    expected={f['path']:f['sha256'] for f in json.loads((ROOT/'recovery/manifest.json').read_text())['files']}
    for original in originals:
        if hashlib.sha256(original.read_bytes()).hexdigest()!=expected[str(original.relative_to(ROOT))]:
            raise ValueError('Archived source does not match recovery manifest: '+original.name)
    files=[*originals, ROOT/'updated/headless/BeamHeadless.java', *sorted(generated.rglob('*.java'))]
    output=BUILD/'classes'; output.mkdir(parents=True,exist_ok=True)
    command=['javac','-encoding','UTF-8','-d',str(output),*[str(p) for p in files]]
    result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
    evidence={'schema':'beam-headless-build-v1','status':'passed' if result.returncode==0 else 'failed',
      'compiler':subprocess.run(['javac','-version'],text=True,capture_output=True).stdout.strip(),
      'exit_code':result.returncode,'diagnostics':(result.stdout+result.stderr).replace(str(ROOT),'<repo>'),
      'unchanged_original_sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in originals},
      'scope':'Desktop numerical-method execution with compile-only platform shims; not an Android/OpenCV application build',
      'original_methods':['DecodeGraySimpleBW','NormalizeDecodedValues','CorrectOpticalDistortionCPU','ReconstructCPU'],
      'excluded_runtime':['capture','Android UI','OpenCV','Clear clipping','Z median filter']}
    target=ROOT/'validation/headless-build.json'; target.write_text(json.dumps(evidence,indent=2)+'\n')
    if result.returncode: raise RuntimeError(evidence['diagnostics'])
    return output

if __name__=='__main__':
    print(build().relative_to(ROOT))
