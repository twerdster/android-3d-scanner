"""Compare exported Android pixels with unchanged Java and independent Python.

Build headless classes first, then keep that output immutable while comparing.
The exported points/fixture hashes contain no device identity requirement.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

from .build_headless import BUILD,ROOT
from .synthetic import decode_corrected,generate_scene,run_historical

def compare(points_path,output):
    exported=json.loads(Path(points_path).read_text())
    fixture=ROOT/'updated/android-replay/app/src/main/assets/replay.json'
    fixture_hash=hashlib.sha256(fixture.read_bytes()).hexdigest()
    if fixture_hash!=exported['fixture_sha256']:raise ValueError('Android fixture hash differs')
    saved=json.loads(fixture.read_text())
    scenes={s['name']:s for s in saved['scenes']}
    records=[];seen=set()
    for item in exported['scenes']:
        name=item['name'];scene=generate_scene(name)
        if name in seen:raise ValueError('Duplicate exported scene: '+name)
        seen.add(name)
        if scene!=scenes[name]:raise ValueError('Saved fixture differs from fresh geometry: '+name)
        expected={'historical':run_historical(scene,BUILD/'classes'),'corrected':decode_corrected(scene)}
        for mode,reference in expected.items():
            actual=item[mode]
            if len(actual)!=len(reference):raise ValueError('Pixel count differs')
            absolute=scaled=0;valid=0
            for pixel,(a,b) in enumerate(zip(actual,reference)):
                if isinstance(a,list) and all(v is None for v in a):a=None
                point=b['xyz']
                if (a is None)!=(point is None):raise ValueError(f'Mask differs: {name}/{mode}/{pixel}')
                if a is not None:
                    if len(a)!=3 or not all(type(v) in (int,float) and math.isfinite(v) for v in a):
                        raise ValueError('Invalid Android point')
                    valid+=1
                    for av,bv in zip(a,point):
                        error=abs(av-bv);relative=error/max(1,abs(bv))
                        absolute=max(absolute,error);scaled=max(scaled,relative)
                        if relative>3e-5:raise ValueError(f'Coordinate differs: {name}/{mode}/{pixel}')
            records.append({'scene':name,'mode':mode,'pixels':len(reference),'valid':valid,
              'mask_exact':True,'max_absolute_m':absolute,'max_relative_scaled':scaled})
    if seen!=set(scenes) or len(records)!=2*len(scenes):raise ValueError('Not every scene/mode exported')
    # A hand-specified center ray, independent of any scene generator helper.
    q=426;gray=q^(q>>1);bits=[(gray>>(9-k))&1 for k in range(10)]
    manual={'rows':3,'cols':3,'pattern_count':12,'projector_columns':1024,'rd':[0,0,1,1,0,0],
      'camera_matrix':[1,0,0,0,0,1,0,0,0,0,1,0],
      'projector_matrix':[1,0,0,0,0,1,0,-.12,0,0,1,0],
      'frames':[[20]*9,[100]*9]+[[20+80*b]*9 for b in bits]}
    point=decode_corrected(manual)[4]['xyz'];depth=.12/(1-2*q/1023)
    if abs(point[0])+abs(point[1])+abs(point[2]-depth)>1e-12:raise ValueError('Closed form differs')
    files=[ROOT/'updated/synthetic.py',ROOT/'updated/compare_android.py',ROOT/'updated/headless/BeamHeadless.java',
           *sorted((ROOT/'updated/android-replay/app/src/main/java').rglob('*.java'))]
    result={'schema':'beam-android-independent-parity-v1','status':'passed','fixture_sha256':fixture_hash,
      'export_sha256':hashlib.sha256(Path(points_path).read_bytes()).hexdigest(),
      'scene_mode_count':len(records),'pixels_compared':sum(r['pixels'] for r in records),
      'all_masks_exact':True,'scaled_coordinate_tolerance':3e-5,
      'scaled_coordinate_definition':'abs(android-reference)/max(1,abs(reference)) per coordinate',
      'maximum_scaled_coordinate_error':max(r['max_relative_scaled'] for r in records),
      'scope':'Historical Android adaptation vs actual unchanged Java; corrected Android vs independent Python/geometry',
      'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
      'scene_modes':records,'independent_closed_form_center_ray':{'decoded_gray_integer':q,
        'point':point,'expected_depth':depth,'passed':True}}
    Path(output).write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--android-points',type=Path,required=True)
    p.add_argument('--output',type=Path,default=ROOT/'validation/android-independent-parity.json');a=p.parse_args()
    result=compare(a.android_points,a.output)
    print(f"PASS: {result['scene_mode_count']} scene/modes, {result['pixels_compared']} pixels, exact masks")

if __name__=='__main__':main()
