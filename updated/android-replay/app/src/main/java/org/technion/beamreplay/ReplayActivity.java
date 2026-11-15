package org.technion.beamreplay;

import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.SeekBar;
import android.widget.Spinner;
import android.widget.TextView;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import org.json.JSONArray;
import org.json.JSONObject;

/** Dependency-free replay UI. No camera, internet, storage or projector permissions. */
public final class ReplayActivity extends Activity {
    private ReplayScene[] scenes;
    private float[][][][] results;
    private ReplayMetrics[][] metrics;
    private Spinner sceneChoice,modeChoice,viewChoice;
    private TextView status,caption;
    private ReplayView canvas;
    private SeekBar pattern;
    private Button run;
    private String fixtureSha256;

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(14),dp(10),dp(14),dp(8));root.setBackgroundColor(0xfff4f6fa);
        TextView title=new TextView(this);title.setText("Beam · synthetic replay");
        title.setTextSize(24);title.setTextColor(0xff182638);root.addView(title);
        TextView scope=new TextView(this);
        scope.setText("Supplied synthetic calibration · grayscale captures → 3D\nHistorical numerical stage versus explicit repairs");
        scope.setTextColor(0xff40516a);scope.setTextSize(13);root.addView(scope);
        sceneChoice=spinner(root,new String[]{"Loading observations…"});
        LinearLayout controls=new LinearLayout(this);controls.setOrientation(LinearLayout.HORIZONTAL);
        root.addView(controls);
        modeChoice=spinner(controls,new String[]{"Historical", "Corrected", "Ground truth"});
        viewChoice=spinner(controls,new String[]{"Depth map", "Point cloud", "Observation"});
        modeChoice.setLayoutParams(new LinearLayout.LayoutParams(0,dp(48),1));
        viewChoice.setLayoutParams(new LinearLayout.LayoutParams(0,dp(48),1));
        modeChoice.setSelection(Math.max(0,Math.min(2,getIntent().getIntExtra("mode",1))));
        viewChoice.setSelection(Math.max(0,Math.min(2,getIntent().getIntExtra("view",0))));
        run=new Button(this);run.setText("Replay captures");run.setEnabled(false);root.addView(run);
        status=new TextView(this);status.setText("Loading and decoding capture frames…");
        status.setTextSize(14);status.setTextColor(0xff182638);status.setPadding(0,dp(4),0,dp(6));root.addView(status);
        canvas=new ReplayView(this);canvas.setContentDescription("Reconstructed synthetic depth or point cloud");
        root.addView(canvas,new LinearLayout.LayoutParams(-1,0,1));
        pattern=new SeekBar(this);pattern.setContentDescription("Capture pattern number");root.addView(pattern);
        caption=new TextView(this);caption.setTextSize(12);caption.setTextColor(0xff40516a);root.addView(caption);
        setContentView(root);
        AdapterView.OnItemSelectedListener changed=new AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(AdapterView<?> parent,View view,int position,long id) {display();}
            @Override public void onNothingSelected(AdapterView<?> parent) { }
        };
        sceneChoice.setOnItemSelectedListener(changed);modeChoice.setOnItemSelectedListener(changed);
        viewChoice.setOnItemSelectedListener(changed);
        pattern.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override public void onProgressChanged(SeekBar bar,int progress,boolean user) {display();}
            @Override public void onStartTrackingTouch(SeekBar bar) { }
            @Override public void onStopTrackingTouch(SeekBar bar) { }
        });
        run.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View view) {process(false);}
        });
        process(true);
    }

    private void process(boolean load) {
        run.setEnabled(false);status.setText("Replaying grayscale observations through both numerical modes…");
        new Thread(new Runnable() { @Override public void run() {
            try {
                if (load) {
                    String text;
                    try (InputStream input=getAssets().open("replay.json");ByteArrayOutputStream output=new ByteArrayOutputStream()) {
                        byte[] buffer=new byte[8192];int n;
                        while ((n=input.read(buffer))!=-1) output.write(buffer,0,n);
                        text=output.toString(StandardCharsets.UTF_8.name());
                        byte[] digest=java.security.MessageDigest.getInstance("SHA-256").digest(output.toByteArray());
                        StringBuilder hex=new StringBuilder();
                        for (byte value:digest) hex.append(String.format(java.util.Locale.US,"%02x",value&255));
                        fixtureSha256=hex.toString();
                    }
                    JSONObject document=new JSONObject(text);
                    if (!"beam-replay-v1".equals(document.getString("schema"))) throw new IllegalArgumentException("Unknown replay schema");
                    JSONArray list=document.getJSONArray("scenes");
                    if (list.length()==0) throw new IllegalArgumentException("No scenes");
                    scenes=new ReplayScene[list.length()];
                    for (int i=0;i<scenes.length;i++) scenes[i]=new ReplayScene(list.getJSONObject(i));
                }
                results=new float[scenes.length][2][][];metrics=new ReplayMetrics[scenes.length][2];
                JSONArray report=new JSONArray();
                JSONArray pointReport=new JSONArray();
                for (int i=0;i<scenes.length;i++) {
                    results[i][0]=new HistoricalNumerics(scenes[i]).historical();
                    results[i][1]=CorrectedNumerics.reconstruct(scenes[i]);
                    JSONObject item=new JSONObject();item.put("name",scenes[i].name);
                    JSONObject coordinates=new JSONObject();coordinates.put("name",scenes[i].name);
                    for (int mode=0;mode<2;mode++) {
                        metrics[i][mode]=new ReplayMetrics(scenes[i],results[i][mode]);
                        item.put(mode==0?"historical":"corrected",metrics[i][mode].json());
                        JSONArray xyz=new JSONArray();
                        for (int pixel=0;pixel<scenes[i].rows*scenes[i].cols;pixel++) {
                            JSONArray point=new JSONArray();
                            for (int axis=0;axis<3;axis++) {
                                float value=results[i][mode][axis][pixel];
                                point.put(Float.isFinite(value)?value:JSONObject.NULL);
                            }
                            xyz.put(point);
                        }
                        coordinates.put(mode==0?"historical":"corrected",xyz);
                    }
                    report.put(item);
                    pointReport.put(coordinates);
                }
                JSONObject evidence=new JSONObject();evidence.put("schema","beam-android-replay-results-v1");
                evidence.put("scope","Scalar pre-Clear/pre-median numerical replay of bundled synthetic captures; not hardware calibration or scanning");
                evidence.put("fixture_sha256",fixtureSha256);
                evidence.put("scenes",report);
                try (FileOutputStream output=new FileOutputStream(new File(getFilesDir(),"replay-results.json"))) {
                    output.write((evidence.toString(2)+"\n").getBytes(StandardCharsets.UTF_8));
                }
                JSONObject pointEvidence=new JSONObject();pointEvidence.put("schema","beam-android-replay-points-v1");
                pointEvidence.put("fixture_sha256",fixtureSha256);pointEvidence.put("scenes",pointReport);
                try (FileOutputStream output=new FileOutputStream(new File(getFilesDir(),"replay-points.json"))) {
                    output.write((pointEvidence.toString()+"\n").getBytes(StandardCharsets.UTF_8));
                }
                runOnUiThread(new Runnable() { @Override public void run() {
                    if (load) {
                        String[] names=new String[scenes.length];for (int i=0;i<names.length;i++) names[i]=scenes[i].name;
                        sceneChoice.setAdapter(new ArrayAdapter<>(ReplayActivity.this,android.R.layout.simple_spinner_dropdown_item,names));
                        sceneChoice.setSelection(Math.max(0,Math.min(scenes.length-1,getIntent().getIntExtra("scene",0))));
                    }
                    run.setEnabled(true);display();
                }});
            } catch (Exception error) {
                runOnUiThread(new Runnable() { @Override public void run() {
                    status.setText("Replay failed: "+error.getClass().getSimpleName()+": "+error.getMessage());
                }});
            }
        }},"beam-replay").start();
    }

    private void display() {
        if (scenes==null || metrics==null || !run.isEnabled()) return;
        int index=sceneChoice.getSelectedItemPosition(),mode=modeChoice.getSelectedItemPosition();
        if (index<0 || index>=scenes.length) return;
        ReplayScene scene=scenes[index];pattern.setMax(scene.patternCount-1);
        float[][] points=mode==2 ? scene.truth : results[index][mode];
        status.setText(mode==2 ? "Independent renderer surface truth\nVisibility mask excludes projector shadows and field-of-view misses" : metrics[index][mode].summary());
        canvas.setScene(scene,points,mode==2,viewChoice.getSelectedItemPosition(),pattern.getProgress());
        String capture=pattern.getProgress()==0 ? "black reference" : pattern.getProgress()==1 ? "white reference" : "Gray bit "+(pattern.getProgress()-1);
        caption.setText(viewChoice.getSelectedItemPosition()==2 ? "Capture "+(pattern.getProgress()+1)+"/"+scene.patternCount+" · "+capture :
                "Blue = near · red = far · dark = rejected\nDrag point cloud to rotate. Both modes omit historical clipping/Z-only median.");
    }

    private Spinner spinner(LinearLayout parent,String[] labels) {
        Spinner result=new Spinner(this);
        result.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,labels));
        parent.addView(result,new LinearLayout.LayoutParams(-1,dp(48)));return result;
    }
    private int dp(int value) {return Math.round(value*getResources().getDisplayMetrics().density);}
}
