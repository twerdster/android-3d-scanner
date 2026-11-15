package org.technion.beamreplay;

import java.util.Locale;
import org.json.JSONException;
import org.json.JSONObject;

final class ReplayMetrics {
    int visible,accepted,rejected,falseValid;
    double rmse=Double.NaN,maxError=Double.NaN;
    ReplayMetrics(ReplayScene scene,float[][] result) {
        double squared=0,max=0;
        for (int i=0;i<scene.rows*scene.cols;i++) {
            boolean finite=Float.isFinite(result[0][i]) && Float.isFinite(result[1][i])
                    && Float.isFinite(result[2][i]);
            if (scene.visible[i]) {
                visible++;
                if (finite) {
                    double d2=0;
                    for (int axis=0;axis<3;axis++) {
                        double d=result[axis][i]-scene.truth[axis][i]; d2+=d*d;
                    }
                    accepted++; squared+=d2; max=Math.max(max,Math.sqrt(d2));
                } else rejected++;
            } else if (finite) falseValid++;
        }
        if (accepted>0) {rmse=Math.sqrt(squared/accepted);maxError=max;}
    }
    JSONObject json() throws JSONException {
        JSONObject value=new JSONObject();
        value.put("visible",visible);value.put("accepted_visible",accepted);
        value.put("rejected_visible",rejected);value.put("false_valid_occluded",falseValid);
        value.put("rmse_m",Double.isFinite(rmse)?rmse:JSONObject.NULL);
        value.put("max_error_m",Double.isFinite(maxError)?maxError:JSONObject.NULL);
        return value;
    }
    String summary() {
        return String.format(Locale.US,"Visible accepted %d/%d • rejected %d\nRMSE %s m • max %s m\nFalse valid outside visibility: %d",
                accepted,visible,rejected,format(rmse),format(maxError),falseValid);
    }
    private static String format(double value) {
        return Double.isFinite(value)?String.format(Locale.US,"%.5f",value):"n/a";
    }
}
