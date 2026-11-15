package org.technion.beamreplay;

/** Explicit repairs around the archived scalar triangulation, not a hardware scanner. */
final class CorrectedNumerics {
    static float[][] reconstruct(ReplayScene s) {
        int n=s.rows*s.cols, bits=s.patternCount-2;
        if (!finiteShape(s.rd,6) || !finiteShape(s.camera,12) || !finiteShape(s.projector,12)
                || s.rd[2]==0 || !nonsingularLeft(s.camera) || !nonsingularLeft(s.projector)) return rejected(n);
        float[] xp=new float[n],xc=new float[n],yc=new float[n];
        float halfRow=(1f+s.rows)/2f,halfCol=(1f+s.cols)/2f;
        float scale=Math.min(halfRow,halfCol)-1f;
        for (int i=0;i<n;i++) {
            float contrast=(s.frames[1][i]&255)-(s.frames[0][i]&255);
            int decoded=0, binary=0;
            boolean valid=contrast>=10f;
            for (int k=0;k<bits;k++) {
                float normalized=((s.frames[k+2][i]&255)-(s.frames[0][i]&255))/contrast;
                normalized=Math.max(0f,Math.min(1f,normalized));
                valid &= Float.isFinite(normalized) && Math.abs(normalized-.5f)>=.1f;
                binary ^= normalized>.5f ? 1 : 0;
                decoded=(decoded<<1)|binary;
            }
            valid &= decoded<s.projectorColumns;
            xp[i]=valid ? 2f*decoded/(s.projectorColumns-1f)-1f : Float.NaN;
            float xn=(i/s.cols+1-halfRow)/scale,yn=(i%s.cols+1-halfCol)/scale;
            float dx=xn-s.rd[0],dy=yn-s.rd[1];
            float radius=(float)Math.sqrt(dx*dx/(s.rd[2]*s.rd[2])+dy*dy);
            // Analytic limit of (k1*r+k2*r^2+k3*r^3)/r at zero.
            float radialScale=s.rd[3]+s.rd[4]*radius+s.rd[5]*radius*radius;
            xc[i]=s.rd[0]+dx*radialScale; yc[i]=s.rd[1]+dy*radialScale;
            float[] a=s.camera,p=s.projector;
            double q00=xc[i]*a[8]-a[0],q01=xc[i]*a[9]-a[1],q02=xc[i]*a[10]-a[2];
            double q10=yc[i]*a[8]-a[4],q11=yc[i]*a[9]-a[5],q12=yc[i]*a[10]-a[6];
            double q20=xp[i]*p[8]-p[4],q21=xp[i]*p[9]-p[5],q22=xp[i]*p[10]-p[6];
            double determinant=q00*(q11*q22-q12*q21)-q01*(q10*q22-q12*q20)+q02*(q10*q21-q11*q20);
            double norm0=Math.sqrt(q00*q00+q01*q01+q02*q02);
            double norm1=Math.sqrt(q10*q10+q11*q11+q12*q12);
            double norm2=Math.sqrt(q20*q20+q21*q21+q22*q22);
            double volume=norm0*norm1*norm2;
            if (!Double.isFinite(determinant) || volume==0 || Math.abs(determinant)/volume<1e-7
                    || s.rd[2]==0) xp[i]=Float.NaN;
        }
        float[][] result=new HistoricalNumerics(s).triangulate(xp,xc,yc);
        for (int i=0;i<n;i++) {
            float x=result[0][i],y=result[1][i],z=result[2][i];
            double cameraDepth=s.camera[8]*x+s.camera[9]*y+s.camera[10]*z+s.camera[11];
            double projectorDepth=s.projector[8]*x+s.projector[9]*y+s.projector[10]*z+s.projector[11];
            if (!Float.isFinite(x) || !Float.isFinite(y) || !Float.isFinite(z)
                    || !(cameraDepth>1e-8) || !(projectorDepth>1e-8)) {
                result[0][i]=Float.NaN;result[1][i]=Float.NaN;result[2][i]=Float.NaN;
            }
        }
        return result;
    }

    private static boolean finiteShape(float[] values,int count) {
        if (values==null || values.length!=count) return false;
        for (float value:values) if (!Float.isFinite(value)) return false;
        return true;
    }
    private static boolean nonsingularLeft(float[] a) {
        double det=a[0]*(a[5]*a[10]-a[6]*a[9])-a[1]*(a[4]*a[10]-a[6]*a[8])+a[2]*(a[4]*a[9]-a[5]*a[8]);
        double r0=Math.sqrt(a[0]*a[0]+a[1]*a[1]+a[2]*a[2]);
        double r1=Math.sqrt(a[4]*a[4]+a[5]*a[5]+a[6]*a[6]);
        double r2=Math.sqrt(a[8]*a[8]+a[9]*a[9]+a[10]*a[10]);
        return Double.isFinite(det) && r0*r1*r2>0 && Math.abs(det)/(r0*r1*r2)>1e-12;
    }
    private static float[][] rejected(int count) {
        float[][] result=new float[3][count];
        for (float[] axis:result) java.util.Arrays.fill(axis,Float.NaN);
        return result;
    }
}
