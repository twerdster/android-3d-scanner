import copy
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

from updated.build_headless import build, ROOT
from updated.synthetic import (SCENES, camera_ray, decode_corrected, generate_scene,
    independent_world_ray, metrics, project, rotation, run_historical)


class ScannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classes=build()
        cls.scenes={name:generate_scene(name) for name in SCENES}
        cls.fixed={name:decode_corrected(s) for name,s in cls.scenes.items()}
        cls.original={name:run_historical(s,cls.classes) for name,s in cls.scenes.items()}

    def test_unchanged_java_sources_match_recovery_manifest(self):
        manifest={r['path']:r['sha256'] for r in json.loads((ROOT/'recovery/manifest.json').read_text())['files']}
        evidence=json.loads((ROOT/'validation/headless-build.json').read_text())
        for path,actual in evidence['unchanged_original_sources'].items():
            self.assertEqual(actual,manifest[path])
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),actual)
        self.assertEqual(len(evidence['unchanged_original_sources']),2)

    def test_independent_scene_surfaces_and_forward_projection(self):
        for name in ('plane','tilted','sphere','step','calibrated','distorted'):
            scene=self.scenes[name]
            for i,point in enumerate(scene['truth_xyz']):
                camera=project(scene['camera_matrix'],point)
                row,col=divmod(i,scene['cols'])
                nominal=camera_ray(row,col,scene['rows'],scene['cols'])
                if name!='distorted':
                    self.assertAlmostEqual(camera[0],nominal[0],places=12)
                    self.assertAlmostEqual(camera[1],nominal[1],places=12)
                if name in ('tilted','calibrated','distorted'):
                    self.assertAlmostEqual(point[2],.72+.12*point[0]+.08*point[1],places=12)
                elif name=='sphere' and point[2]<.94:
                    self.assertAlmostEqual(point[0]**2+point[1]**2+(point[2]-.8)**2,.24**2,places=12)
            if name in ('calibrated','distorted'):
                self.assertNotEqual(scene['camera_origin'],[0,0,0])
                self.assertNotEqual(scene['camera_matrix'][1],0)

    def test_original_triangulation_with_independent_oracle_projection(self):
        # Isolate actual archived triangulation from the known decoder scaling
        # bug. Inputs here are forward-projected geometry, not decoded captures.
        for name in ('plane','tilted','sphere','step','calibrated','distorted'):
            scene=self.scenes[name]
            original=run_historical(scene,self.classes,direct_projector=True)
            self.assertTrue(all(p['xyz'] is not None for p in original))
            error=max(math.dist(p['xyz'],truth) for p,truth in zip(original,scene['truth_xyz']))
            # Float32 historical calibration/radial/cofactor arithmetic is
            # compared with double-precision world geometry over the full FOV.
            self.assertLess(error,2e-5,(name,error))

    def test_clean_and_calibrated_gray_reconstruction_against_geometry(self):
        for name in ('plane','tilted','sphere','step','calibrated','distorted','radial_center'):
            scene=self.scenes[name];m=metrics(scene,self.fixed[name])
            self.assertEqual(m['visible_coverage'],1)
            self.assertEqual(m['false_valid_unilluminated_points'],0)
            self.assertEqual(m['exact_decoded_integer_points'],sum(scene['visible']))
            self.assertLess(m['rmse_m'],.006)
            self.assertLess(m['max_error_m'],.022)

    def test_unsigned_domain_all_1024_gray_codes(self):
        scene=generate_scene('plane',rows=2,cols=512)
        scene['frames']=[[30]*1024,[220]*1024]+[[] for _ in range(10)]
        for integer in range(1024):
            gray=integer^(integer>>1)
            for k in range(10):scene['frames'][k+2].append(220 if gray&(1<<(9-k)) else 30)
        fixed=decode_corrected(scene);original=run_historical(scene,self.classes)
        self.assertEqual([p['q'] for p in fixed],list(range(1024)))
        self.assertEqual({p['raw'] for p in original},{0.0})

    def test_historical_normalization_is_four_times_decoded_pixel(self):
        scene=self.scenes['plane'];original=self.original['plane']
        for p,q,visible in zip(original,scene['projector_integer'],scene['visible']):
            if not visible:continue
            self.assertAlmostEqual(p['raw']*1024,q,places=5)
            expected=2*(4*q)/(scene['projector_columns']-1)-1
            if -.999<=expected<=.999:self.assertAlmostEqual(p['xp'],expected,places=5)
            else:self.assertTrue(math.isnan(p['xp']))
        self.assertLess(metrics(scene,original)['visible_coverage'],.3)

    def test_projector_occlusion_comes_from_geometry_and_is_rejected(self):
        scene=self.scenes['projector_shadow'];fixed=self.fixed['projector_shadow']
        shadow=[i for i,r in enumerate(scene['visibility_reason']) if r=='projector_occluded']
        self.assertGreater(len(shadow),30)
        self.assertTrue(all(fixed[i]['xyz'] is None for i in shadow))
        self.assertEqual(metrics(scene,fixed)['visible_coverage'],1)
        # Visibility is evaluator ground truth, never an input to the decoder.
        hidden=copy.deepcopy(scene);hidden['visible']=[False]*len(hidden['visible'])
        self.assertEqual(decode_corrected(hidden),fixed)

    def test_noise_replay_and_low_contrast_rejection(self):
        scene=self.scenes['noise'];fixed=self.fixed['noise']
        self.assertEqual(generate_scene('noise'),scene)
        self.assertEqual(metrics(scene,fixed)['visible_coverage'],1)
        self.assertEqual(metrics(scene,fixed)['false_valid_unilluminated_points'],0)
        self.assertGreater(metrics(scene,self.original['noise'])['false_valid_unilluminated_points'],100)
        low=self.fixed['low_contrast']
        self.assertTrue(all(p['xyz'] is None and p['reason']=='low_contrast' for p in low))

    def test_no_depth_without_baseline(self):
        self.assertTrue(all(p['xyz'] is None for p in self.fixed['zero_baseline']))

    def test_nonidentity_radial_expected_ray_and_center_limit(self):
        # At nominal x=.7,y=0, center(.1,0), aspect1.2 => rd=.5.
        # ru=.9*.5+.1*.25+.02*.125=.4775 => corrected x=.673.
        rd=[.1,0,1.2,.9,.1,.02]
        ray=independent_world_ray(17,15,21,31,rd,rotation(0,0,0))
        self.assertAlmostEqual(ray[0],.673,places=12);self.assertAlmostEqual(ray[1],0,places=12)
        scene=generate_scene('plane',rows=21,cols=31);scene['rd']=rd
        original=run_historical(scene,self.classes,direct_projector=True)
        self.assertAlmostEqual(original[17*31+15]['xc'],.673,places=6)
        center=self.scenes['radial_center'];i=(center['rows']//2)*center['cols']+center['cols']//2
        original=run_historical(center,self.classes,direct_projector=True)
        self.assertIsNone(original[i]['xyz']);self.assertIsNotNone(self.fixed['radial_center'][i]['xyz'])

    def test_corrupted_gray_bits_can_produce_undetected_outliers(self):
        scene=self.scenes['corrupt_bit'];m=metrics(scene,self.fixed['corrupt_bit'])
        self.assertLess(m['exact_decoded_integer_points'],m['scored_visible_points'])
        self.assertGreater(m['rmse_m'],.1)
        self.assertGreater(m['max_error_m'],1)

    def test_invalid_calibration_and_frames_rejected(self):
        alterations=[('rd',[0,0,0,1,0,0]),('rd',[0,0,1,float('nan'),0,0]),
          ('camera_matrix',[0]*12),('projector_matrix',[1]*12),('rows',True),
          ('projector_columns',2048),('pattern_count',99),('frames',[[1]])]
        for key,value in alterations:
            scene=copy.deepcopy(self.scenes['plane']);scene[key]=value
            with self.assertRaises(ValueError,msg=key):decode_corrected(scene)
        scene=copy.deepcopy(self.scenes['plane']);scene['frames'][0][0]=256
        with self.assertRaises(ValueError):decode_corrected(scene)

    def test_headless_binary_bounds_and_trailing_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp=Path(tmp)/'in.bin';out=Path(tmp)/'out.bin'
            for rows,cols,projector,count in [(65536,65536,1024,12),(0,64,1024,12),(48,64,1,12),(48,64,1024,25)]:
                inp.write_bytes(struct.pack('>5i',0x4245414d,rows,cols,projector,count))
                proc=subprocess.run(['java','-cp',str(self.classes),'BeamHeadless',str(inp),str(out)],capture_output=True)
                self.assertNotEqual(proc.returncode,0);self.assertIn(b'Fixture bounds',proc.stderr)
            inp.write_bytes(struct.pack('>5i',0x4245414d,2,2,8,5)+struct.pack('>30f',*([1]*30))+bytes(20)+b'extra')
            proc=subprocess.run(['java','-cp',str(self.classes),'BeamHeadless',str(inp),str(out)],capture_output=True)
            self.assertNotEqual(proc.returncode,0);self.assertIn(b'Trailing fixture bytes',proc.stderr)


if __name__=='__main__':unittest.main()
