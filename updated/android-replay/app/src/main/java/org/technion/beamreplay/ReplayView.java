package org.technion.beamreplay;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.MotionEvent;
import android.view.View;
import java.util.Locale;

final class ReplayView extends View {
    private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
    private ReplayScene scene;
    private float[][] points;
    private boolean truth;
    private int kind,pattern;
    private float yaw=.3f,pitch=-.3f,lastX,lastY;
    ReplayView(Context context) {super(context);setBackgroundColor(0xff142237);}
    void setScene(ReplayScene value,float[][] xyz,boolean isTruth,int displayKind,int capture) {
        scene=value;points=xyz;truth=isTruth;kind=displayKind;pattern=capture;invalidate();
    }
    private boolean valid(int i) {
        return (!truth || scene.visible[i]) && Float.isFinite(points[0][i])
                && Float.isFinite(points[1][i]) && Float.isFinite(points[2][i]);
    }
    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);if (scene==null) return;
        int n=scene.rows*scene.cols;
        // A common range from independent visible truth makes modes visually comparable.
        float min=Float.POSITIVE_INFINITY,max=Float.NEGATIVE_INFINITY;
        for (int i=0;i<n;i++) if (scene.visible[i] && Float.isFinite(scene.truth[2][i])) {
            min=Math.min(min,scene.truth[2][i]);max=Math.max(max,scene.truth[2][i]);
        }
        if (!Float.isFinite(min)) {min=0;max=1;} if (max-min<.001f) {min-=.05f;max+=.05f;}
        if (kind==1) cloud(canvas,min,max);
        else {
            int[] colors=new int[n];
            for (int i=0;i<n;i++) colors[i]=kind==2 ? Color.rgb(scene.frames[pattern][i]&255,scene.frames[pattern][i]&255,scene.frames[pattern][i]&255)
                    : valid(i) ? depth(points[2][i],min,max) : 0xff142237;
            Bitmap image=Bitmap.createBitmap(colors,scene.cols,scene.rows,Bitmap.Config.ARGB_8888);
            float scale=Math.min((getWidth()-24f)/scene.cols,(getHeight()-44f)/scene.rows);
            float w=scene.cols*scale,h=scene.rows*scale;
            paint.setFilterBitmap(false);
            canvas.drawBitmap(image,null,new RectF((getWidth()-w)/2,(getHeight()-h)/2,(getWidth()+w)/2,(getHeight()+h)/2),paint);
            image.recycle();
        }
        paint.setColor(Color.WHITE);paint.setTextSize(12*getResources().getDisplayMetrics().scaledDensity);
        canvas.drawText(kind==2?"8-bit synthetic camera intensity":String.format(Locale.US,"Truth depth range %.3f–%.3f m",min,max),12,getHeight()-12,paint);
    }
    private void cloud(Canvas canvas,float min,float max) {
        float[] center=new float[3];float count=0;
        for (int i=0;i<scene.rows*scene.cols;i++) if (scene.visible[i]) {
            boolean finite=true;for(int a=0;a<3;a++) finite &= Float.isFinite(scene.truth[a][i]);
            if (finite) {for(int a=0;a<3;a++) center[a]+=scene.truth[a][i];count++;}
        }
        if (count==0) return;for(int a=0;a<3;a++) center[a]/=count;
        float extent=.05f;
        for (int i=0;i<scene.rows*scene.cols;i++) if (scene.visible[i]) for(int a=0;a<3;a++) {
            if(Float.isFinite(scene.truth[a][i])) extent=Math.max(extent,Math.abs(scene.truth[a][i]-center[a]));
        }
        float scale=Math.min(getWidth(),getHeight()-40)/(2.8f*extent);
        float cy=(float)Math.cos(yaw),sy=(float)Math.sin(yaw),cp=(float)Math.cos(pitch),sp=(float)Math.sin(pitch);
        for (int i=0;i<scene.rows*scene.cols;i++) if (valid(i)) {
            float x=points[0][i]-center[0],y=points[1][i]-center[1],z=points[2][i]-center[2];
            float rx=cy*x+sy*z,rz=-sy*x+cy*z,ry=cp*y-sp*rz;
            paint.setColor(depth(points[2][i],min,max));
            canvas.drawCircle(getWidth()/2f+rx*scale,getHeight()/2f-ry*scale,2.3f,paint);
        }
    }
    private int depth(float z,float min,float max) {
        float t=Math.max(0,Math.min(1,(z-min)/(max-min)));
        return Color.HSVToColor(new float[]{240*(1-t),.75f,1f});
    }
    @Override public boolean onTouchEvent(MotionEvent event) {
        if (event.getAction()==MotionEvent.ACTION_DOWN) {lastX=event.getX();lastY=event.getY();return true;}
        if (event.getAction()==MotionEvent.ACTION_MOVE) {
            yaw+=(event.getX()-lastX)*.008f;pitch+=(event.getY()-lastY)*.008f;
            lastX=event.getX();lastY=event.getY();invalidate();return true;
        }
        if (event.getAction()==MotionEvent.ACTION_UP) {performClick();return true;}
        return true;
    }
    @Override public boolean performClick() {super.performClick();return true;}
}
