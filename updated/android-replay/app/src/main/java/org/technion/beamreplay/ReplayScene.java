package org.technion.beamreplay;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/** Synthetic grayscale observations and independent surface truth, never device captures. */
final class ReplayScene {
    final String name;
    final int rows, cols, projectorColumns, patternCount;
    final float[] rd, camera, projector;
    final byte[][] frames;
    final float[][] truth;
    final boolean[] visible;

    ReplayScene(JSONObject value) throws JSONException {
        name=value.getString("name"); rows=value.getInt("rows"); cols=value.getInt("cols");
        projectorColumns=value.getInt("projector_columns");
        patternCount=value.getInt("pattern_count");
        if (rows<3 || cols<3 || rows*cols>200000 || patternCount<3 || patternCount>24
                || projectorColumns<2) throw new JSONException("Unsupported scene dimensions");
        rd=floats(value.getJSONArray("rd"),6);
        camera=floats(value.getJSONArray("camera_matrix"),12);
        projector=floats(value.getJSONArray("projector_matrix"),12);
        int n=rows*cols;
        JSONArray images=value.getJSONArray("frames");
        if (images.length()!=patternCount) throw new JSONException("Capture count mismatch");
        frames=new byte[patternCount][n];
        for (int k=0;k<patternCount;k++) {
            JSONArray pixels=images.getJSONArray(k);
            if (pixels.length()!=n) throw new JSONException("Capture size mismatch");
            for (int i=0;i<n;i++) {
                int intensity=pixels.getInt(i);
                if (intensity<0 || intensity>255) throw new JSONException("Intensity outside 8-bit range");
                frames[k][i]=(byte)intensity;
            }
        }
        truth=new float[3][n];
        JSONArray points=value.getJSONArray("truth_xyz"), mask=value.getJSONArray("visible");
        if (points.length()!=n || mask.length()!=n) throw new JSONException("Truth size mismatch");
        visible=new boolean[n];
        for (int i=0;i<n;i++) {
            JSONArray xyz=points.getJSONArray(i);
            if (xyz.length()!=3) throw new JSONException("Truth point dimension mismatch");
            for (int axis=0;axis<3;axis++) {
                truth[axis][i]=xyz.isNull(axis) ? Float.NaN : (float)xyz.getDouble(axis);
            }
            visible[i]=mask.getBoolean(i);
        }
    }

    private static float[] floats(JSONArray values,int count) throws JSONException {
        if (values.length()!=count) throw new JSONException("Calibration dimension mismatch");
        float[] result=new float[count];
        for (int i=0;i<count;i++) {
            result[i]=(float)values.getDouble(i);
            if (!Float.isFinite(result[i])) throw new JSONException("Nonfinite calibration");
        }
        return result;
    }
}
