"""Meaningful observation-only replay, geometry, coverage and media checks."""
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from updated.synthetic import decode_corrected
from showcase.observations import make_rig, project, render_observations


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ShowcaseChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = ROOT/'showcase/results'
        cls.rig = json.loads((cls.results/'rig.json').read_text())
        cls.report = json.loads((cls.results/'metrics.json').read_text())
        with np.load(cls.results/'observations.npz', allow_pickle=False) as capture:
            cls.frames = capture['frames'].copy()
            cls.input = {key: capture[key].tolist() for key in ['rd', 'camera_matrix', 'projector_matrix']}
            cls.input.update({'rows': int(capture['dimensions'][0]), 'cols': int(capture['dimensions'][1]),
                              'projector_columns': int(capture['projector_columns']),
                              'pattern_count': len(capture['frames']), 'frames': cls.frames.tolist()})
        # Decode before opening any evaluator or reconstructed-point data.
        cls.decoded = decode_corrected(cls.input)
        cls.xyz = np.array([r['xyz'] if r['xyz'] is not None else [math.nan]*3 for r in cls.decoded])
        cls.valid = np.isfinite(cls.xyz).all(axis=1)

    def test_observations_only_reproduce_dense_saved_output(self):
        self.assertGreaterEqual(self.input['rows'], 240)
        self.assertGreaterEqual(self.input['cols'], 320)
        with np.load(self.results/'reconstruction.npz', allow_pickle=False) as saved:
            np.testing.assert_array_equal(self.valid, saved['valid'])
            np.testing.assert_allclose(self.xyz, saved['xyz'], rtol=0, atol=0, equal_nan=True)
            np.testing.assert_array_equal([r['q'] if r['q'] is not None else -1 for r in self.decoded], saved['q'])
        self.assertGreater(int(self.valid.sum()), 50000)
        for i, frame in enumerate(self.frames):
            with Image.open(self.results/'captures'/f'{i:02d}.png') as image:
                np.testing.assert_array_equal(np.asarray(image).ravel(), frame)

    def test_independent_error_and_full_illuminated_coverage(self):
        with np.load(self.results/'evaluation.npz', allow_pickle=False) as truth:
            visible, hit, shadow = truth['visible'], truth['hit'], truth['shadow']
            scored = self.valid & visible
            error = np.linalg.norm(self.xyz[scored]-truth['truth_xyz'][scored], axis=1)
            measured = self.report['metrics']
            self.assertAlmostEqual(float(np.sqrt(np.mean(error**2))), measured['rmse_m'], places=14)
            self.assertAlmostEqual(float(np.quantile(error, .95)), measured['p95_error_m'], places=14)
            self.assertAlmostEqual(float(scored.sum()/visible.sum()), measured['illuminated_coverage'], places=14)
            self.assertEqual(int(shadow.sum()), measured['projector_shadow_pixels'])
            self.assertGreater(int(shadow.sum()), 500)
            self.assertFalse((self.valid & shadow).any())
            self.assertFalse((self.valid & ~hit).any())
            self.assertFalse((self.valid & ~visible).any())
            self.assertLess(measured['illuminated_coverage'], 1.)
            self.assertGreater(measured['illuminated_coverage'], .99)
            self.assertLess(measured['rmse_m'], .002)
            np.testing.assert_array_equal(np.array([r['q'] for r in self.decoded if r['xyz'] is not None]), truth['projector_integer'][self.valid])

    def test_projective_constraints_in_declared_pixel_coordinates(self):
        rows, cols = self.input['rows'], self.input['cols']
        index = np.flatnonzero(self.valid)
        scale = (min(rows, cols)-1)/2
        expected = np.column_stack(((index//cols-(rows-1)/2)/scale, (index % cols-(cols-1)/2)/scale))
        uv, depth = project(self.xyz[self.valid], self.rig['camera_matrix'])
        np.testing.assert_allclose(uv, expected, atol=2e-12, rtol=0)
        self.assertTrue((depth > 0).all())
        projector, depth = project(self.xyz[self.valid], self.rig['projector_matrix'])
        expected_q = np.array([r['q'] for r in self.decoded if r['xyz'] is not None])
        np.testing.assert_allclose(projector[:, 1], 2*expected_q/1023-1, atol=2e-12, rtol=0)
        self.assertTrue((depth > 0).all())

    def test_geometric_shadow_removes_pattern_modulation(self):
        rig = make_rig(3, 3)
        points = np.tile([0., .17, 0.], (9, 1))
        normals = np.tile([0., 0., -1.], (9, 1))
        hit = np.ones(9, dtype=bool)
        shadow = np.array([False, True, False, True, False, True, False, True, False])
        observations, evaluation = render_observations(points, normals, hit, shadow, rig)
        frames = np.asarray(observations['frames'], dtype=int)
        self.assertTrue((evaluation['visible'] == ~shadow).all())
        self.assertTrue((np.ptp(frames[:, shadow], axis=0) < 8).all())
        self.assertTrue(((frames[1]-frames[0])[~shadow] > 100).all())
        self.assertNotIn('truth_xyz', observations)
        self.assertNotIn('visible', observations)

    def test_source_artifact_and_gif_frame_bindings(self):
        for field in ['source_sha256', 'output_sha256']:
            for name, digest in self.report[field].items():
                self.assertEqual(sha(ROOT/name), digest, name)
        old = json.loads((ROOT/'validation/numerical-tests.json').read_text())
        for name, digest in old['source_sha256'].items():
            self.assertEqual(sha(ROOT/name), digest, name)
        media = json.loads((ROOT/'showcase/media-validation.json').read_text())
        for field in ['input_sha256', 'output_sha256']:
            for name, digest in media[field].items():
                self.assertEqual(sha(ROOT/name), digest, name)
        with Image.open(ROOT/'showcase/beam-dragon.gif') as gif:
            self.assertEqual(gif.n_frames, media['frames'])
            self.assertEqual(gif.size, tuple(media['dimensions']))
            self.assertEqual(gif.info['loop'], 0)
            duration = 0; cloud_hashes = set()
            for i, expected in enumerate(media['frame_checks']):
                gif.seek(i); rgb = gif.convert('RGB')
                self.assertEqual(hashlib.sha256(rgb.tobytes()).hexdigest(), expected['rgb_sha256'])
                duration += gif.info['duration']
                cloud_hashes.add(hashlib.sha256(rgb.crop((418, 145, 1074, 580)).tobytes()).hexdigest())
            self.assertEqual(duration, 9600)
            self.assertGreater(len(cloud_hashes), 40)


if __name__ == '__main__':
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ShowcaseChecks))
    record = {'schema': 'beam-dense-showcase-checks-v1', 'status': 'passed' if result.wasSuccessful() else 'failed',
              'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'scope': 'Dense observation-only numerical replay, independent scoring/coverage, camera/projector constraints, shadow radiometry and media bindings',
              'source_sha256': sha(Path(__file__)), 'test_log': log.getvalue()}
    (ROOT/'showcase/test-results.json').write_text(json.dumps(record, indent=2)+'\n')
    print(log.getvalue())
    sys.exit(0 if result.wasSuccessful() else 1)
