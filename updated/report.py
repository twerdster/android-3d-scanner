"""Small deterministic PNG, PLY and interactive HTML simulation artifacts."""
import csv
import hashlib
import json
import math
from pathlib import Path
import struct
import zlib

from .synthetic import SCENES, generate_scene, decode_corrected, run_historical, metrics
from .build_headless import build

def bind_metadata(metadata,output,scenes,android_asset=None):
    root=Path(__file__).resolve().parents[1]
    files=[*sorted((root/'updated').glob('*.py')),root/'updated/headless/BeamHeadless.java',
           root/'source/src/com/project/logic/Reconstructor.java',root/'source/src/com/project/logic/CalibrationFile.java']
    metadata['source_sha256']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    for scene in scenes:
        metadata['scenes'][scene['name']]['calibration']={key:scene[key] for key in
           ['rows','cols','rd','camera_matrix','projector_matrix','baseline_m','camera_origin','projector_origin','seed']}
    if android_asset:
        metadata['replay_fixture_sha256']=hashlib.sha256(Path(android_asset).read_bytes()).hexdigest()
    metadata['artifact_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file() and p.name!='metrics.json'}
    return metadata

def png(path,width,height,pixels):
    def chunk(kind,payload):
        return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff)
    rows=b''.join(b'\0'+bytes(pixels[y*width*3:(y+1)*width*3]) for y in range(height))
    data=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(rows,9))+chunk(b'IEND',b'')
    path.write_bytes(data)

def color(value,low=.3,high=1.0):
    if value is None or not math.isfinite(value):return (15,23,42)
    t=max(0,min(1,(value-low)/(high-low)))
    return (round(255*t),round(220*(1-abs(2*t-1))),round(255*(1-t)))

def montage(path,scene,historical,corrected):
    rows,cols=scene['rows'],scene['cols']; scale=4
    w,h=cols*4*scale,rows*4*scale; pixels=bytearray(w*h*3)
    planes=[]
    for frame in scene['frames']:planes.append([(v,v,v) for v in frame])
    planes.extend([[color(p[2]) for p in scene['truth_xyz']],
      [color(p['xyz'][2]) if p['xyz'] else color(None) for p in historical],
      [color(p['xyz'][2]) if p['xyz'] else color(None) for p in corrected],
      [color(math.dist(p['xyz'],truth),0,.015) if p['xyz'] and visible else color(None)
       for p,truth,visible in zip(corrected,scene['truth_xyz'],scene['visible'])]])
    for tile,plane in enumerate(planes):
        tx,ty=tile%4,tile//4
        for y in range(rows):
            for x in range(cols):
                c=bytes(plane[y*cols+x])
                for dy in range(scale):
                    start=(((ty*rows+y)*scale+dy)*w+(tx*cols+x)*scale)*3
                    pixels[start:start+scale*3]=c*scale
    png(path,w,h,pixels)

def ply(path,records):
    points=[r['xyz'] for r in records if r['xyz'] and all(math.isfinite(v) for v in r['xyz'])]
    with path.open('w') as out:
        out.write('ply\nformat ascii 1.0\ncomment independently generated Beam replay; metres\nelement vertex '+str(len(points))+'\nproperty float x\nproperty float y\nproperty float z\nend_header\n')
        for p in points:out.write(' '.join(format(v,'.8g') for v in p)+'\n')

HTML='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Beam synthetic scanner replay</title>
<style>body{font:16px system-ui;margin:0;background:#0f172a;color:#e2e8f0}main{max-width:1150px;margin:auto;padding:28px}h1{margin-bottom:8px}p{line-height:1.5}select,button{font:inherit;padding:8px;background:#1e293b;color:inherit;border:1px solid #64748b;border-radius:5px}canvas{display:block;width:100%;height:430px;background:#020617;touch-action:none;border:1px solid #475569;margin:16px 0}img{width:100%;image-rendering:pixelated}table{border-collapse:collapse;font-size:14px}td,th{padding:8px;border-bottom:1px solid #475569;text-align:right}td:first-child,th:first-child{text-align:left}.scroll{overflow:auto}.hint{color:#94a3b8}a{color:#7dd3fc}</style>
<main><h1>Beam: synthetic structured-light replay</h1><p>Camera rays intersect planes, a sphere, a step and an opaque box. The virtual projector creates 10-bit Gray stripes. The unchanged historical numerical methods and an explicitly corrected adaptation reconstruct the resulting byte captures.</p><p class="hint">This is new simulated validation, before historical coordinate clipping and OpenCV median filtering. It does not run the Galaxy Beam camera, prism or projector. Drag the cloud to rotate; use the wheel to zoom.</p>
<label>Scene <select id="scene"></select></label> <label>Points <select id="mode"><option value="corrected">Corrected reconstruction</option><option value="truth">Ground truth</option><option value="historical">Unchanged historical equations</option></select></label> <button id="reset">Reset view</button><canvas id="cloud" aria-label="Interactive reconstructed point cloud"></canvas><p id="stats"></p>
<h2>Projected captures and recovered depth</h2><p>First three rows: black, white, then Gray bits from most to least significant. Last row: ground-truth depth, historical depth, corrected depth, corrected 3D error. Depth color runs blue (0.3 m) to red (1 m); error blue (0) to red (15 mm); dark pixels are rejected/unilluminated. Historical values outside the scale saturate.</p><img id="montage" alt="Twelve simulated captured stripes and four depth/error images"><h2>Results</h2><div class="scroll"><table id="table"></table></div><p><a href="metrics.json">Machine-readable metrics and conditions</a>. PLY point clouds use metres. All plots and fixture values can be regenerated with Python and a local JDK.</p></main>
<script>const data=__DATA__;const scenes=document.querySelector('#scene'),modes=document.querySelector('#mode'),cv=document.querySelector('#cloud'),ctx=cv.getContext('2d');let yaw=.35,pitch=-.25,zoom=1,last=null;
Object.keys(data).forEach(n=>{let o=document.createElement('option');o.value=n;o.textContent=n;scenes.append(o)});
function draw(){const d=data[scenes.value],mode=modes.value;cv.width=Math.max(400,cv.clientWidth*devicePixelRatio);cv.height=430*devicePixelRatio;let w=cv.width,h=cv.height;ctx.clearRect(0,0,w,h);let points=d[mode],cy=Math.cos(yaw),sy=Math.sin(yaw),cx=Math.cos(pitch),sx=Math.sin(pitch),scale=Math.min(w,h)*.38*zoom;let projected=[];for(const p of points){let x=p[1],y=-p[0],z=p[2]-.7;let a=cy*x+sy*z,b=-sy*x+cy*z;let yy=cx*y-sx*b,zz=sx*y+cx*b;projected.push([w/2+a*scale,h/2+yy*scale,zz,p[2]])}projected.sort((a,b)=>b[2]-a[2]);for(const p of projected){let t=Math.max(0,Math.min(1,(p[3]-.3)/.7));ctx.fillStyle=`rgb(${255*t},${220*(1-Math.abs(2*t-1))},${255*(1-t)})`;ctx.fillRect(p[0],p[1],2*devicePixelRatio,2*devicePixelRatio)}document.querySelector('#montage').src=d.montage;let m=d.metrics[mode==='historical'?'historical':'corrected'];document.querySelector('#stats').textContent=`${points.length} displayed points. Corrected visible coverage ${(d.metrics.corrected.visible_coverage*100).toFixed(1)}%; 3D RMSE ${d.metrics.corrected.rmse_m===null?'n/a':(d.metrics.corrected.rmse_m*1000).toFixed(2)+' mm'}.`;}
scenes.onchange=draw;modes.onchange=draw;document.querySelector('#reset').onclick=()=>{yaw=.35;pitch=-.25;zoom=1;draw()};cv.onpointerdown=e=>{last=[e.clientX,e.clientY];cv.setPointerCapture(e.pointerId)};cv.onpointerup=()=>last=null;cv.onpointermove=e=>{if(last){yaw+=(e.clientX-last[0])*.01;pitch+=(e.clientY-last[1])*.01;last=[e.clientX,e.clientY];draw()}};cv.onwheel=e=>{e.preventDefault();zoom=Math.max(.1,Math.min(10,zoom*Math.exp(-e.deltaY*.001)));draw()};window.onresize=draw;
let t=document.querySelector('#table');t.innerHTML='<tr><th>Scene / mode</th><th>Visible coverage</th><th>3D RMSE (mm)</th><th>Max error (mm)</th><th>False valid dark pixels</th></tr>'+Object.entries(data).flatMap(([n,d])=>['historical','corrected'].map(mode=>{let m=d.metrics[mode];return `<tr><td>${n} / ${mode}</td><td>${(100*m.visible_coverage).toFixed(1)}%</td><td>${m.rmse_m===null?'—':(1000*m.rmse_m).toFixed(2)}</td><td>${m.max_error_m===null?'—':(1000*m.max_error_m).toFixed(2)}</td><td>${m.false_valid_unilluminated_points}</td></tr>`})).join('');draw();</script></html>'''

def generate_report(output,android_asset=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);classes=build()
    metadata={'schema':'beam-synthetic-validation-v1','conditions':{
      'camera_resolution':'64x48; radial-center test 65x49','projector_columns':1024,'gray_bits':10,
      'baseline_m':.12,'default_plane_depth_m':.72,'noise_standard_deviation_levels':3,
      'seed':20261115,'world_units':'metres','photometry':'black/white plus binary Gray modulation; no blur/interreflection/lens PSF',
      'comparison_stage':'decode, normalization, radial correction and triangulation; before Clear and median',
      'corrected_changes':['unsigned differences','decoded-bit normalization','low-contrast/confidence checks',
       'finite radial-center limit','pivot/singularity and positive-depth guards'],
      'not_validated':['physical camera/projector/prism','calibration estimation','Android historical app','OpenCV filtering','motion between captures']},'scenes':{}}
    interactive={};android=[]
    for name in SCENES:
        scene=generate_scene(name);corrected=decode_corrected(scene);historical=run_historical(scene,classes)
        mm={'historical':metrics(scene,historical),'corrected':metrics(scene,corrected)}
        if name in ('plane','tilted','sphere','step','calibrated','distorted'):
            direct=run_historical(scene,classes,direct_projector=True)
            # Oracle-projected coordinates intentionally bypass capture/FOV.
            direct_error=[math.dist(a['xyz'],b) for a,b in zip(direct,scene['truth_xyz']) if a['xyz']]
            mm['direct_projection_triangulation']={'points':len(direct_error),
              'rmse_m':math.sqrt(sum(e*e for e in direct_error)/len(direct_error)),
              'max_error_m':max(direct_error),'scope':'oracle forward-projected coordinates; isolated unchanged triangulation check'}
        metadata['scenes'][name]={'metrics':mm,'visibility_counts':{r:scene['visibility_reason'].count(r) for r in sorted(set(scene['visibility_reason']))}}
        montage(output/(name+'.png'),scene,historical,corrected)
        ply(output/(name+'.ply'),corrected)
        interactive[name]={'truth':[p for p,v in zip(scene['truth_xyz'],scene['visible']) if v],
          'corrected':[p['xyz'] for p in corrected if p['xyz']],
          'historical':[p['xyz'] for p in historical if p['xyz']],
          'montage':name+'.png','metrics':mm}
        # Keep the full independent fixture for every Android replay scene.
        android.append(scene)
    (output/'index.html').write_text(HTML.replace('__DATA__',json.dumps(interactive,separators=(',',':'))))
    (output/'metrics.json').write_text(json.dumps(metadata,indent=2)+'\n')
    with (output/'metrics.csv').open('w',newline='') as out:
        writer=csv.writer(out,lineterminator='\n');writer.writerow(['scene','mode','visible_coverage','rmse_m','max_error_m','false_valid_unilluminated_points'])
        for name,value in metadata['scenes'].items():
            for mode in ['historical','corrected']:
                m=value['metrics'][mode];writer.writerow([name,mode,*[m[k] for k in ['visible_coverage','rmse_m','max_error_m','false_valid_unilluminated_points']]])
    if android_asset:
        target=Path(android_asset);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps({'schema':'beam-replay-v1','scenes':android},separators=(',',':'))+'\n')
    bind_metadata(metadata,output,android,android_asset)
    (output/'metrics.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return metadata
