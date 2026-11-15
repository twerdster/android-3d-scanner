"""Render independent mesh captures, run the existing decoder, score and save.

Requires NumPy, Pillow and Open3D. The mesh is an explicit external input;
large raw/evaluator arrays stay in task scratch. No historical file is edited.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np
import open3d as o3d
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from updated.synthetic import decode_corrected
from showcase.mesh_scene import Scene, load_mesh
from showcase.observations import camera_rays, make_rig, render_observations, score


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_ply(path, xyz):
    xyz = np.asarray(xyz, dtype='<f4')
    header = ('ply\nformat binary_little_endian 1.0\ncomment Synthetic corrected Beam reconstruction; Stanford Dragon derivative\n'
              f'element vertex {len(xyz)}\nproperty float x\nproperty float y\nproperty float z\nend_header\n')
    path.write_bytes(header.encode()+xyz.tobytes())


def depth_image(points, valid, rig):
    c = np.asarray(rig['camera_matrix']).reshape(3, 4)
    z = points @ c[2, :3] + c[2, 3]
    colors = np.array([[16, 35, 65], [32, 113, 142], [55, 177, 157], [172, 218, 159], [249, 225, 145]])
    t = np.clip((z-.65)/.45, 0, 1)*4
    t[~valid] = 0
    i = np.minimum(t.astype(int), 3); f = (t-i)[:, None]
    rgb = np.rint(colors[i]*(1-f)+colors[i+1]*f).astype(np.uint8)
    rgb[~valid] = [8, 15, 27]
    return Image.fromarray(rgb.reshape(rig['rows'], rig['cols'], 3))


def build(mesh_path, output, scratch, rows=384, cols=512):
    start = time.monotonic()
    provenance = json.loads((ROOT/'showcase/mesh-provenance.json').read_text())
    if digest(mesh_path) != provenance['files']['dragon-normalized.npz']:
        raise ValueError('Expected the pinned, uniformly normalized Stanford Dragon NPZ; run prepare_mesh.py')
    if type(rows) is not int or type(cols) is not int or min(rows, cols) < 2 or max(rows, cols) > 2048 or rows*cols > 1000000:
        raise ValueError('Camera dimensions must be 2..2048 with at most 1,000,000 pixels')
    output.mkdir(parents=True, exist_ok=True); scratch.mkdir(parents=True, exist_ok=True)
    vertices, faces = load_mesh(mesh_path)
    geometry = Scene(vertices, faces)
    rig = make_rig(rows, cols)
    origins, directions = camera_rays(rig)
    distance, face, normal = geometry.intersect(origins, directions)
    hit = face >= 0
    points = np.full((len(face), 3), np.nan)
    points[hit] = origins[hit]+distance[hit, None]*directions[hit]
    shadow = np.zeros(len(face), dtype=bool)
    shadow[hit] = ~geometry.visible(rig['projector_origin'], points[hit])
    decoder_input, evaluator = render_observations(points, normal, hit, shadow, rig)
    # The actual inverse receives no mesh, ground truth, normals, hit mask,
    # visibility or projector address. All of those remain in the evaluator.
    assert set(decoder_input) == {'schema', 'name', 'rows', 'cols', 'projector_columns',
           'pattern_count', 'rd', 'camera_matrix', 'projector_matrix', 'frames'}
    decoded = decode_corrected(decoder_input)
    metrics, reconstruction, valid = score(decoded, evaluator)
    surface_distance = geometry.distance(reconstruction[valid])
    metrics['accepted_mesh_distance_rmse_m'] = float(np.sqrt(np.mean(surface_distance**2))) if len(surface_distance) else None
    metrics['accepted_mesh_distance_p95_m'] = float(np.quantile(surface_distance, .95)) if len(surface_distance) else None
    write_ply(output/'dragon-reconstruction.ply', reconstruction[valid])
    (output/'captures').mkdir(exist_ok=True)
    for i, frame in enumerate(evaluator['frames']):
        Image.fromarray(frame.reshape(rows, cols)).save(output/'captures'/f'{i:02d}.png')
    depth_image(reconstruction, valid, rig).save(output/'depth.png')
    depth_image(points, hit, rig).save(output/'truth-depth.png')
    Image.fromarray(np.where(evaluator['visible'], 255, 0).astype(np.uint8).reshape(rows, cols)).save(output/'illuminated-mask.png')
    Image.fromarray(np.where(evaluator['shadow'], 255, 0).astype(np.uint8).reshape(rows, cols)).save(output/'shadow-mask.png')
    # No object/pickle arrays. Public observations/calibration are separate from
    # evaluation.npz; the actual decoder call above receives no evaluation data.
    np.savez_compressed(output/'observations.npz', frames=evaluator['frames'],
                        camera_matrix=rig['camera_matrix'], projector_matrix=rig['projector_matrix'],
                        rd=rig['rd'], dimensions=[rows, cols], projector_columns=rig['projector_columns'])
    np.savez_compressed(output/'reconstruction.npz', xyz=reconstruction, valid=valid,
                        q=np.array([r['q'] if r['q'] is not None else -1 for r in decoded], dtype=np.int32))
    np.savez_compressed(output/'evaluation.npz', truth_xyz=points, hit=hit,
                        visible=evaluator['visible'], shadow=evaluator['shadow'],
                        projector_integer=evaluator['projector_integer'])
    np.savez_compressed(scratch/'evaluator.npz', **{k: v for k,v in evaluator.items() if k != 'frames'})
    (output/'rig.json').write_text(json.dumps(rig, indent=2)+'\n')
    report = {'schema': 'beam-dense-showcase-v1', 'scene': 'Stanford Dragon',
        'conditions': {'resolution': [cols, rows], 'gray_bits': 10, 'captures': 12,
        'projector_columns': 1024, 'world_units': 'metres', 'mesh_height_m': .35,
        'baseline_m': rig['baseline_m'], 'seed': 20261116, 'read_noise_std_levels': .8,
        'radiometry': 'Lambertian direct illumination, inverse-square falloff, spatial reflectance, ambient and independent read noise',
        'normal_policy': 'Two-sided raycasting; source triangle normals oriented toward observing camera before illumination, including scan-hole/back-facing boundaries',
        'sampling': 'pixel-centre pinhole rays; hard-edged binary projector patterns',
        'not_modelled': ['optical blur', 'interreflection', 'inter-frame motion', 'calibration estimation', 'real hardware'],
        'decoder': 'existing updated.synthetic.decode_corrected unchanged; before clipping/median; supplied calibration',
        'decoder_inputs': '8-bit captures and calibration only; no truth, normals or visibility'},
        'metrics': metrics, 'mesh': {'vertices': len(vertices), 'triangles': len(faces),
        'normalized_npz_sha256': digest(mesh_path), 'source_member_sha256': provenance['source_member_sha256']},
        'software': {'python': platform.python_version(), 'numpy': np.__version__, 'open3d': o3d.__version__},
        'elapsed_seconds': time.monotonic()-start,
        'source_sha256': {p.relative_to(ROOT).as_posix(): digest(p) for p in [
            ROOT/'showcase/build_showcase.py', ROOT/'showcase/observations.py', ROOT/'showcase/mesh_scene.py', ROOT/'updated/synthetic.py']},
        'output_sha256': {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'metrics.json'}}
    (output/'metrics.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=ROOT/'showcase/results')
    parser.add_argument('--scratch', required=True, type=Path)
    parser.add_argument('--rows', type=int, default=384)
    parser.add_argument('--cols', type=int, default=512)
    args = parser.parse_args()
    build(args.mesh, args.output.resolve(), args.scratch.resolve(), args.rows, args.cols)
