"""Independent pinhole projection and radiometry for the dense mesh showcase.

This module renders observations. It does not call or invert a decoder.
World axes are X right, Y up, Z completing the right-handed frame; Beam's
calibration rows are image-down, image-right and forward, respectively.
"""
import math

import numpy as np


def look_at(origin, target, focal):
    origin = np.asarray(origin, dtype=np.float64)
    forward = np.asarray(target, dtype=np.float64) - origin
    forward /= np.linalg.norm(forward)
    right = np.cross([0., 1., 0.], forward)
    right /= np.linalg.norm(right)
    down = -np.cross(forward, right)
    basis = np.array([down, right, forward])
    linear = np.diag([focal, focal, 1.]) @ basis
    return basis, np.column_stack([linear, -linear @ origin])


def make_rig(rows=384, cols=512):
    camera = np.array([.26, .24, -.88])
    target = np.array([0., .17, 0.])
    camera_basis, c = look_at(camera, target, 4.2)
    projector = camera + .12 * camera_basis[1]
    projector_basis, p = look_at(projector, target, 3.2)
    return {
        'rows': rows, 'cols': cols, 'projector_columns': 1024,
        'pattern_count': 12, 'rd': [0., 0., 1., 1., 0., 0.],
        'camera_matrix': c.ravel().tolist(),
        'projector_matrix': p.ravel().tolist(),
        'camera_origin': camera.tolist(),
        'projector_origin': projector.tolist(),
        'camera_basis_rows_down_right_forward': camera_basis.tolist(),
        'projector_basis_rows_down_right_forward': projector_basis.tolist(),
        'camera_focal_scale': 4.2, 'projector_focal_scale': 3.2,
        'look_at': target.tolist(), 'baseline_m': float(np.linalg.norm(projector-camera)),
        'world_coordinates': '+X right, +Y up, +Z completing a right-handed frame',
        'projection_rows': 'image down, image right, forward',
    }


def camera_rays(rig):
    """Forward rays from an explicitly defined pinhole camera, before raycasting."""
    rows, cols = rig['rows'], rig['cols']
    row, col = np.indices((rows, cols), dtype=np.float64)
    scale = (min(rows, cols)-1)/2
    down = (row-(rows-1)/2)/scale/rig['camera_focal_scale']
    right = (col-(cols-1)/2)/scale/rig['camera_focal_scale']
    basis = np.asarray(rig['camera_basis_rows_down_right_forward'])
    directions = down[..., None]*basis[0] + right[..., None]*basis[1] + basis[2]
    directions /= np.linalg.norm(directions, axis=2, keepdims=True)
    origins = np.broadcast_to(rig['camera_origin'], directions.shape)
    return origins.reshape(-1, 3).copy(), directions.reshape(-1, 3)


def project(points, matrix):
    matrix = np.asarray(matrix).reshape(3, 4)
    homogeneous = points @ matrix[:, :3].T + matrix[:, 3]
    with np.errstate(invalid='ignore', divide='ignore'):
        return homogeneous[:, :2]/homogeneous[:, 2, None], homogeneous[:, 2]


def render_observations(points, normals, hit, shadow, rig, seed=20261116):
    """Render twelve 8-bit exposures, and return truth in a separate evaluator.

    The projector has binary hard-edged Gray patterns, Lambertian direct
    illumination and inverse-square falloff. Camera samples are pixel-centre
    rays. Gaussian read noise is independent across exposures. No motion,
    calibration estimation, optical blur, interreflection or saturation model
    beyond unsigned-byte clipping is claimed.
    """
    points = np.asarray(points, dtype=np.float64)
    normals = np.asarray(normals, dtype=np.float64)
    hit, shadow = np.asarray(hit, dtype=bool), np.asarray(shadow, dtype=bool)
    count = rig['rows']*rig['cols']
    if points.shape != (count, 3) or normals.shape != (count, 3):
        raise ValueError('Geometry dimensions differ from the camera')
    safe = np.where(hit[:, None], points, 0.)
    uv, projected_depth = project(safe, rig['projector_matrix'])
    in_projector = np.all(np.abs(uv) <= 1+1e-10, axis=1) & (projected_depth > 0)
    toward_light = np.asarray(rig['projector_origin'])-safe
    distances = np.linalg.norm(toward_light, axis=1)
    toward_light /= np.maximum(distances[:, None], 1e-12)
    # Raycasting is two-sided; orient a normal toward the observing camera for
    # the source scan's documented holes/back-facing boundary triangles.
    toward_camera = np.asarray(rig['camera_origin'])-safe
    sign = np.where(np.sum(normals*toward_camera, axis=1) >= 0, 1., -1.)
    oriented = normals*sign[:, None]
    cosine = np.maximum(0., np.sum(oriented*toward_light, axis=1))
    visible = hit & in_projector & ~shadow & (cosine > 0)
    q = np.rint((uv[:, 1]+1)*(rig['projector_columns']-1)/2)
    q = np.clip(q, 0, rig['projector_columns']-1).astype(np.int32)
    gray = q ^ (q >> 1)
    # Mild surface reflectance variation is independent of Gray-code address.
    reflectance = .82+.12*np.sin(safe[:, 0]*33)*np.cos(safe[:, 1]*27)
    black = np.where(hit, 18+3*np.sin(safe[:, 1]*21), 8.)
    contrast = np.where(visible, np.minimum(215., 180*reflectance*cosine*(.92/np.maximum(distances, .1))**2), 0.)
    rng = np.random.default_rng(seed)
    bits = rig['pattern_count']-2
    modulation = [np.zeros(count), np.ones(count)]
    modulation += [((gray >> (bits-1-k)) & 1) for k in range(bits)]
    frames = np.stack([np.rint(np.clip(black+contrast*on+rng.normal(0, .8, count), 0, 255)).astype(np.uint8)
                       for on in modulation])
    decoder_input = {key: rig[key] for key in ['rows', 'cols', 'projector_columns', 'pattern_count',
                     'rd', 'camera_matrix', 'projector_matrix']}
    decoder_input.update({'schema': 'beam-replay-v1', 'name': 'stanford_dragon',
                          'frames': frames.tolist()})
    evaluator = {'truth_xyz': points, 'hit': hit, 'visible': visible,
                 'shadow': hit & in_projector & shadow,
                 'outside_projector': hit & ~in_projector,
                 'backlit': hit & in_projector & ~shadow & (cosine <= 0),
                 'projector_integer': q, 'contrast': contrast,
                 'normal': oriented, 'frames': frames}
    return decoder_input, evaluator


def score(decoded, evaluator):
    points = np.array([r['xyz'] if r['xyz'] is not None else [math.nan]*3 for r in decoded])
    valid = np.all(np.isfinite(points), axis=1)
    visible = evaluator['visible']
    scored = valid & visible
    errors = np.linalg.norm(points[scored]-evaluator['truth_xyz'][scored], axis=1)
    reasons = {}
    for r in decoded:
        reasons[r['reason']] = reasons.get(r['reason'], 0)+1
    return {'camera_pixels': len(decoded), 'camera_surface_pixels': int(evaluator['hit'].sum()),
            'illuminated_surface_pixels': int(visible.sum()),
            'projector_shadow_pixels': int(evaluator['shadow'].sum()),
            'outside_projector_pixels': int(evaluator['outside_projector'].sum()),
            'backlit_surface_pixels': int(evaluator['backlit'].sum()),
            'accepted_points': int(valid.sum()), 'scored_illuminated_points': int(scored.sum()),
            'illuminated_coverage': float(scored.sum()/visible.sum()) if visible.any() else None,
            'false_valid_background_points': int((valid & ~evaluator['hit']).sum()),
            'false_valid_unilluminated_points': int((valid & evaluator['hit'] & ~visible).sum()),
            'exact_projector_integer_points': sum(int(decoded[i]['q'] == evaluator['projector_integer'][i]) for i in np.flatnonzero(scored)),
            'rmse_m': float(np.sqrt(np.mean(errors**2))) if len(errors) else None,
            'median_error_m': float(np.median(errors)) if len(errors) else None,
            'p95_error_m': float(np.quantile(errors, .95)) if len(errors) else None,
            'max_error_m': float(errors.max()) if len(errors) else None,
            'rejections': reasons}, points, valid
