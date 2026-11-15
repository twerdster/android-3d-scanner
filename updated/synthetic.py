"""Independent geometric scenes and a corrected adaptation of Beam decoding.

Scene geometry is intersected by camera rays. Projector coordinates are obtained
by forward projection, never from either reconstruction implementation.
All lengths are metres; all random observation noise uses a recorded seed.
"""
import base64
import math
from pathlib import Path
import random
import struct
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SCENES=['plane','tilted','sphere','step','calibrated','distorted','projector_shadow','noise',
        'bright_contrast','low_contrast','corrupt_bit','zero_baseline','radial_center']

def camera_ray(row,col,rows,cols):
    xhalf=(1+rows)/2; yhalf=(1+cols)/2; scale=min(xhalf,yhalf)-1
    return ((row+1-xhalf)/scale,(col+1-yhalf)/scale,1.0)

def box_intersection(origin,direction,low=(-.14,-.25,.35),high=(.14,-.10,.42)):
    near,far=-math.inf,math.inf
    for o,d,a,b in zip(origin,direction,low,high):
        if abs(d)<1e-14:
            if not a<=o<=b:return None
        else:
            t1,t2=(a-o)/d,(b-o)/d
            near=max(near,min(t1,t2)); far=min(far,max(t1,t2))
    if far<max(near,0):return None
    return near if near>1e-8 else far if far>1e-8 else None

def surface_intersection(name,ray,origin=(0,0,0)):
    x,y,z=ray; ox,oy,oz=origin
    if name in ('tilted','calibrated','distorted'):
        distance=(.72+.12*ox+.08*oy-oz)/(z-.12*x-.08*y)
    elif name=='step':distance=((.58 if x>0 else .82)-oz)/z
    elif name=='sphere':
        # Analytic first intersection with sphere center(0,0,.8), radius .24;
        # rays missing it hit the independently defined background plane.
        a=x*x+y*y+z*z; b=2*(x*ox+y*oy+z*(oz-.8)); c=ox*ox+oy*oy+(oz-.8)**2-.24**2; discriminant=b*b-4*a*c
        distance=(-b-math.sqrt(discriminant))/(2*a) if discriminant>=0 else (.95-oz)/z
    else:distance=(.72-oz)/z
    if name=='projector_shadow':
        hit=box_intersection(origin,ray)
        if hit is not None and hit<distance:distance=hit
    return tuple(o+d*distance for o,d in zip(origin,ray))

def rotation(rx,ry,rz):
    cx,sx=math.cos(rx),math.sin(rx);cy,sy=math.cos(ry),math.sin(ry);cz,sz=math.cos(rz),math.sin(rz)
    return [[cz*cy,cz*sy*sx-sz*cx,cz*sy*cx+sz*sx],
            [sz*cy,sz*sy*sx+cz*cx,sz*sy*cx-cz*sx],[-sy,cy*sx,cy*cx]]

def projection_matrix(r,origin):
    return [value for row in r for value in (*row,-sum(a*b for a,b in zip(row,origin)))]

def independent_world_ray(row,col,rows,cols,rd,r):
    xn,yn,_=camera_ray(row,col,rows,cols);cx,cy,aspect,k1,k2,k3=rd
    # Independent polar evaluation of the calibration's elliptical radial map.
    dx,dy=(xn-cx)/aspect,yn-cy;radius=math.hypot(dx,dy);theta=math.atan2(dy,dx)
    corrected_radius=k1*radius+k2*radius**2+k3*radius**3
    camera=(cx+aspect*corrected_radius*math.cos(theta),cy+corrected_radius*math.sin(theta),1)
    return tuple(sum(r[j][i]*camera[j] for j in range(3)) for i in range(3))

def project(matrix,point):
    h=(*point,1)
    values=[sum(a*b for a,b in zip(matrix[i:i+4],h)) for i in (0,4,8)]
    return values[0]/values[2],values[1]/values[2]

def generate_scene(name,rows=48,cols=64,seed=20261115):
    if name not in SCENES:raise ValueError('Unknown scene')
    if name=='radial_center':rows,cols=49,65
    baseline=0 if name=='zero_baseline' else .12
    c=[1.,0,0,0, 0,1.,0,0, 0,0,1.,0]
    p=[1.,0,0,0, 0,1.,0,-baseline, 0,0,1.,0]
    rd=[0.,0,1.,1.,0,0]
    camera_origin=(0,0,0);projector_origin=(0,baseline,0);r=rotation(0,0,0)
    if name in ('calibrated','distorted'):
        camera_origin=(.04,-.03,.02);projector_origin=(.05,.10,.035)
        r=rotation(.08,-.10,.06)
        c=projection_matrix(r,camera_origin)
        p=projection_matrix(rotation(.10,-.06,-.03),projector_origin)
        baseline=math.dist(camera_origin,projector_origin)
    if name=='distorted':rd=[.04,-.03,1.15,.92,.08,.015]
    rng=random.Random(seed); n=rows*cols; bits=10; projector=1<<bits
    truth=[]; visible=[]; reasons=[]; integer=[]
    frames=[[] for _ in range(bits+2)]
    for row in range(rows):
        for col in range(cols):
            index=row*cols+col; ray=independent_world_ray(row,col,rows,cols,rd,r)
            point=surface_intersection(name,ray,camera_origin); truth.append(list(point))
            u,v=project(p,point)
            # Analytically on-edge rays can round a few ulps beyond 1 after
            # rotation/polar evaluation; this is numerical tolerance, not FOV.
            reason='visible' if -1-1e-12<=u<=1+1e-12 and -1-1e-12<=v<=1+1e-12 else 'outside_projector'
            if name=='projector_shadow' and reason=='visible':
                origin=projector_origin; direction=tuple(a-b for a,b in zip(point,origin))
                obstruction=box_intersection(origin,direction)
                if obstruction is not None and obstruction<1-1e-6:reason='projector_occluded'
            visible.append(reason=='visible'); reasons.append(reason)
            code=round((v+1)*(projector-1)/2)
            code=max(0,min(projector-1,code)); integer.append(code)
            gray=code^(code>>1)
            black=30+round(4*math.sin(row*.17)+3*math.cos(col*.13))
            contrast=190 if name=='bright_contrast' else 4 if name=='low_contrast' else 80
            contrast=round(contrast*(.8+.2*math.cos(row*.08)**2)) if visible[-1] else 0
            noise=3.0 if name=='noise' else 0
            bits_on=[0,1]+[(gray>>(bits-1-k))&1 for k in range(bits)]
            if name=='corrupt_bit' and visible[-1] and index%37==0:
                bits_on[5]^=1
            for frame,on in zip(frames,bits_on):
                frame.append(max(0,min(255,round(black+contrast*on+rng.gauss(0,noise)))))
    return {'schema':'beam-replay-v1','name':name,'rows':rows,'cols':cols,
            'projector_columns':projector,'pattern_count':bits+2,'seed':seed,
            'rd':rd,'camera_matrix':c,'projector_matrix':p,'baseline_m':baseline,
            'camera_origin':list(camera_origin),'projector_origin':list(projector_origin),
            'geometry':'camera ray first-hit intersection; projector forward projection',
            'frames':frames,'truth_xyz':truth,'visible':visible,
            'visibility_reason':reasons,'projector_integer':integer}

def decode_corrected(scene,contrast_threshold=10,confidence_threshold=.1):
    """New unsigned/reference-validated adaptation of original prefix-XOR decode.

    Explicit fixes: integer/unsigned differences, true decoded-bit count for
    projector normalization, zero-radius limit, low-contrast/ambiguous rejection,
    singular/behind-camera checks. No denoising or new code-error correction.
    """
    validate_scene(scene)
    n=scene['rows']*scene['cols']; frames=scene['frames']; bits=len(frames)-2
    results=[]
    for i in range(n):
        black,white=frames[0][i],frames[1][i]; contrast=white-black
        if contrast<contrast_threshold:
            results.append({'xyz':None,'reason':'low_contrast','q':None});continue
        binary=0; integer=0; confidence=1
        for frame in frames[2:]:
            normalized=max(0,min(1,(frame[i]-black)/contrast))
            confidence=min(confidence,abs(normalized-.5))
            binary^=int(normalized>.5); integer=(integer<<1)|binary
        if confidence<confidence_threshold:
            results.append({'xyz':None,'reason':'ambiguous_bit','q':integer});continue
        if integer>=scene['projector_columns']:
            results.append({'xyz':None,'reason':'projector_bounds','q':integer});continue
        xp=2*integer/(scene['projector_columns']-1)-1
        ray=camera_ray(i//scene['cols'],i%scene['cols'],scene['rows'],scene['cols'])
        xn,yn=ray[:2]; cx,cy,sx,k1,k2,k3=scene['rd']
        radius=math.sqrt((xn-cx)**2/sx**2+(yn-cy)**2)
        factor=k1+k2*radius+k3*radius**2
        xc=cx+(xn-cx)*factor; yc=cy+(yn-cy)*factor
        c,p=scene['camera_matrix'],scene['projector_matrix']
        a=[[xc*c[8+j]-c[j] for j in range(4)],
           [yc*c[8+j]-c[4+j] for j in range(4)],
           [xp*p[8+j]-p[4+j] for j in range(4)]]
        # Pivoted Gaussian elimination of the recovered three projection
        # constraints, rather than the source's unguarded cofactor divisions.
        scale=max(abs(v) for row in a for v in row[:3]); singular=False
        for col in range(3):
            pivot=max(range(col,3),key=lambda r:abs(a[r][col]))
            if abs(a[pivot][col])<=1e-8*max(scale,1):singular=True;break
            a[col],a[pivot]=a[pivot],a[col]
            divisor=a[col][col]; a[col]=[v/divisor for v in a[col]]
            for r in range(3):
                if r!=col:
                    multiple=a[r][col];a[r]=[x-multiple*y for x,y in zip(a[r],a[col])]
        point=None if singular else [-a[r][3] for r in range(3)]
        if singular:reason='singular'
        elif not all(math.isfinite(v) for v in point):reason='nonfinite'
        elif sum(c[8+j]*(*point,1)[j] for j in range(4))<=1e-8:reason='behind_camera'
        elif sum(p[8+j]*(*point,1)[j] for j in range(4))<=1e-8:reason='behind_projector'
        else:reason='valid'
        if reason!='valid':point=None
        results.append({'xyz':point,'reason':reason,'q':integer,'confidence':confidence})
    return results

def validate_scene(scene):
    rows,cols=scene['rows'],scene['cols']
    if type(rows)is not int or type(cols)is not int or not 2<=rows<=10000 or not 2<=cols<=10000 or rows*cols>1000000:
        raise ValueError('Invalid camera dimensions')
    for key,length in [('rd',6),('camera_matrix',12),('projector_matrix',12)]:
        values=scene[key]
        if len(values)!=length or not all(type(v) in (int,float) and math.isfinite(v) for v in values):
            raise ValueError('Invalid calibration: '+key)
    if abs(scene['rd'][2])<1e-12:raise ValueError('Radial aspect must be nonzero')
    for key in ['camera_matrix','projector_matrix']:
        a=scene[key];det=a[0]*(a[5]*a[10]-a[6]*a[9])-a[1]*(a[4]*a[10]-a[6]*a[8])+a[2]*(a[4]*a[9]-a[5]*a[8])
        scale=max(abs(a[i]) for i in (0,1,2,4,5,6,8,9,10))
        if scale==0 or abs(det)<1e-10*scale**3:raise ValueError('Singular calibration: '+key)
    frames=scene['frames'];count=scene['pattern_count'];projector=scene['projector_columns']
    if type(count)is not int or not 3<=count<=24 or len(frames)!=count:raise ValueError('Invalid pattern count')
    if type(projector)is not int or not 2<=projector<=1<<(count-2):raise ValueError('Projector exceeds code capacity')
    if any(len(f)!=rows*cols or any(type(v)is not int or not 0<=v<=255 for v in f) for f in frames):
        raise ValueError('Invalid unsigned capture data')

def run_historical(scene,classes,direct_projector=False):
    with tempfile.TemporaryDirectory(prefix='beam-fixture-') as tmp:
        input_path=Path(tmp)/'input.bin'; output_path=Path(tmp)/'output.bin'
        with input_path.open('wb') as out:
            out.write(struct.pack('>5i',0x4245414d,scene['rows'],scene['cols'],scene['projector_columns'],scene['pattern_count']))
            for key in ['rd','camera_matrix','projector_matrix']:
                out.write(struct.pack('>'+str(len(scene[key]))+'f',*scene[key]))
            for frame in scene['frames']:out.write(bytes(frame))
            if direct_projector:
                for point in scene['truth_xyz']:
                    out.write(struct.pack('>f',project(scene['projector_matrix'],point)[1]))
        command=['java','-cp',str(classes),'BeamHeadless',str(input_path),str(output_path)]
        if direct_projector:command.append('direct-projector')
        result=subprocess.run(command,
                              text=True,capture_output=True)
        if result.returncode:raise RuntimeError(result.stderr)
        data=output_path.read_bytes();magic,n=struct.unpack('>2i',data[:8])
        if magic!=0x4245414d or len(data)!=8+8*n*4:raise ValueError('Invalid Java output')
        values=struct.unpack('>'+str(n*8)+'f',data[8:])
        arrays={name:values[k*n:(k+1)*n] for k,name in enumerate(['raw','xp','xc','yc','x','y','z','confidence'])}
        return [{'xyz':[arrays[a][i] for a in ['x','y','z']] if all(math.isfinite(arrays[a][i]) for a in ['x','y','z']) else None,
                 'raw':arrays['raw'][i],'xp':arrays['xp'][i],
                 'xc':arrays['xc'][i],'yc':arrays['yc'][i],
                 'confidence':arrays['confidence'][i]} for i in range(n)]

def metrics(scene,result):
    errors=[]; valid=0; false_valid=0; true_visible=sum(scene['visible']); exact_code=0
    reasons={}
    for i,record in enumerate(result):
        reasons[record.get('reason','finite' if record['xyz'] else 'nonfinite')]=reasons.get(record.get('reason','finite' if record['xyz'] else 'nonfinite'),0)+1
        if record['xyz'] is None:continue
        valid+=1
        if not scene['visible'][i]:false_valid+=1;continue
        error=math.dist(record['xyz'],scene['truth_xyz'][i]);errors.append(error)
        q=record.get('q',round(record.get('raw',0)*(1<<(scene['pattern_count']-2))))
        exact_code+=q==scene['projector_integer'][i]
    sorted_errors=sorted(errors)
    return {'pixels':len(result),'visible_ground_truth_pixels':true_visible,'finite_points':valid,
      'scored_visible_points':len(errors),'visible_coverage':len(errors)/true_visible if true_visible else None,
      'false_valid_unilluminated_points':false_valid,'exact_decoded_integer_points':exact_code,
      'rmse_m':math.sqrt(sum(e*e for e in errors)/len(errors)) if errors else None,
      'max_error_m':max(errors) if errors else None,
      'p95_error_m':sorted_errors[min(len(errors)-1,int(.95*len(errors)))] if errors else None,
      'reasons':reasons}
