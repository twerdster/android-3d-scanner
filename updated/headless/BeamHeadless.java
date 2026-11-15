// New 2026 desktop adapter. Numerical methods execute from unchanged archived
// Reconstructor.java, compiled alongside explicit compile-only platform shims.
import java.io.*;
import java.lang.reflect.Method;
import com.project.logic.Reconstructor;
import com.project.activities.MainActivity;

public final class BeamHeadless {
    private static void call(Reconstructor instance, String name, float[]... arrays) throws Exception {
        Class<?>[] types = new Class<?>[arrays.length];
        java.util.Arrays.fill(types, float[].class);
        Method method = Reconstructor.class.getDeclaredMethod(name, types);
        method.setAccessible(true);
        method.invoke(instance, (Object[]) arrays);
    }
    public static void main(String[] args) throws Exception {
        if (args.length < 2 || args.length > 3) throw new IllegalArgumentException("input.bin output.bin [direct-projector]");
        boolean direct=args.length==3 && args[2].equals("direct-projector");
        if(args.length==3 && !direct) throw new IllegalArgumentException("Unknown mode");
        try (DataInputStream in = new DataInputStream(new FileInputStream(args[0]))) {
            if (in.readInt() != 0x4245414d) throw new IOException("Not a BEAM fixture");
            int rows=in.readInt(), cols=in.readInt(), projector=in.readInt(), count=in.readInt();
            if(rows<2 || cols<2 || rows>10000 || cols>10000 || (long)rows*cols>1000000
                || projector<2 || projector>65536 || count<3 || count>24) throw new IOException("Fixture bounds");
            float[] rd=new float[6], c=new float[12], p=new float[12];
            for(float[] a:new float[][]{rd,c,p}) for(int i=0;i<a.length;i++) a[i]=in.readFloat();
            byte[][] frames=new byte[count][rows*cols];
            for(byte[] frame:frames) in.readFully(frame);
            float[] supplied=new float[rows*cols];
            if(direct) for(int i=0;i<supplied.length;i++) supplied[i]=in.readFloat();
            if(in.read()!=-1) throw new IOException("Trailing fixture bytes");
            MainActivity.configure(rows,cols,projector,count,rd,c,p,frames);
            Reconstructor scanner=new Reconstructor();
            int n=rows*cols;
            float[] raw=new float[n], normalized=new float[n], xc=new float[n], yc=new float[n];
            float[] x=new float[n], y=new float[n], z=new float[n], confidence=new float[n];
            call(scanner,"DecodeGraySimpleBW",raw,confidence);
            System.arraycopy(raw,0,normalized,0,n);
            call(scanner,"NormalizeDecodedValues",normalized);
            if(direct) System.arraycopy(supplied,0,normalized,0,n);
            call(scanner,"CorrectOpticalDistortionCPU",xc,yc);
            call(scanner,"ReconstructCPU",x,y,z,normalized,xc,yc);
            try(DataOutputStream out=new DataOutputStream(new FileOutputStream(args[1]))) {
                out.writeInt(0x4245414d); out.writeInt(n);
                for(float[] a:new float[][]{raw,normalized,xc,yc,x,y,z,confidence})
                    for(float value:a) out.writeFloat(value);
            }
        }
    }
}
