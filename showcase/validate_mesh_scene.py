"""Independent hand-specified and float64 exhaustive first-hit checks (MIT)."""
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image
import open3d as o3d

from mesh_scene import Scene, camera_rays, load_mesh, look_at


def brute_first(vertices, faces, origin, direction):
    """Float64 exhaustive Moller-Trumbore, no Open3D/spatial acceleration."""
    nearest = np.inf
    for start in range(0, len(faces), 100000):
        tri = vertices[faces[start:start + 100000]]
        edge1, edge2 = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
        p = np.cross(np.broadcast_to(direction, edge2.shape), edge2)
        det = np.einsum("ij,ij->i", edge1, p)
        nonparallel = np.abs(det) > 1e-16
        inv = np.zeros(len(det))
        inv[nonparallel] = 1 / det[nonparallel]
        s = origin - tri[:, 0]
        u = np.einsum("ij,ij->i", s, p) * inv
        q = np.cross(s, edge1)
        v = q @ direction * inv
        t = np.einsum("ij,ij->i", edge2, q) * inv
        ok = nonparallel & (u >= 0) & (v >= 0) & (u + v <= 1) & (t >= 0)
        if np.any(ok):
            nearest = min(nearest, float(t[ok].min()))
    return nearest


def main():
    root = Path(__file__).parent
    checks = {}
    # Two identical triangular surfaces at distinct, hand-specified depths.
    vertices = np.array([[0, 0, 1], [1, 0, 1], [0, 1, 1],
                         [0, 0, 2], [1, 0, 2], [0, 1, 2]], dtype=float)
    scene = Scene(vertices, np.array([[0, 1, 2], [3, 4, 5]]))
    origins = np.array([[.2, .2, 0], [.2, .2, 0], [1, 1, 0], [.2, .2, 3]])
    directions = np.array([[0, 0, 1], [0, 0, 2], [0, 0, 1], [0, 0, 1]])
    t, face, normal = scene.intersect(origins, directions)
    assert np.allclose(t[:2], [1, .5]) and np.isinf(t[2:]).all()
    assert np.array_equal(face, [0, 0, -1, -1])
    assert np.allclose(normal[:2], [[0, 0, 1], [0, 0, 1]])
    checks["analytic_nearest_scaled_direction_miss_and_behind"] = True
    t, _, _ = scene.intersect([.2, .2, 0], [[0, 0, 1]], tnear=1.1)
    assert abs(t[0] - 2) < 1e-6
    t, _, _ = scene.intersect([.2, .2, 0], [[0, 0, 1]], tfar=.9)
    assert np.isinf(t[0])
    checks["near_shift_finds_next_surface_and_far_clip"] = True
    assert np.array_equal(scene.visible([.2, .2, 0], [[.2, .2, 1], [.2, .2, 2]]), [True, False])
    assert np.allclose(scene.distance([[.2, .2, 1.5], [.2, .2, 2]]), [.5, 0], atol=3e-7)
    checks["open_segment_shadow_and_known_distance"] = True
    pose = look_at([0, 0, 0], [0, 0, 1])
    origin, rays = camera_rays(np.array([[2, 0, 1], [0, 2, 1], [0, 0, 1]]), pose, 3, 3)
    assert np.allclose(rays[4], [0, 0, 1])
    assert np.allclose(rays[0], [.5, .5, 1])
    assert np.allclose(pose[:3, :3].T @ pose[:3, :3], np.eye(3))
    assert np.isclose(np.linalg.det(pose[:3, :3]), 1)
    checks["pinhole_center_corner_and_right_handed_pose"] = True

    vertices, faces = load_mesh(root / "dragon-normalized.npz")
    assert len(vertices) == 437645 and len(faces) == 871414
    assert abs(vertices[:, 1].min()) < 1e-12 and abs(vertices[:, 1].max() - .35) < 1e-12
    checks["full_mesh_counts_and_uniform_scale_bounds"] = True
    before = time.perf_counter()
    dragon = Scene(vertices, faces)
    build_seconds = time.perf_counter() - before
    K = np.array([[380., 0, 159.5], [0, 380., 119.5], [0, 0, 1]])
    pose = look_at([.27, .25, -.85], [0, .175, 0])
    origin, rays = camera_rays(K, pose, 320, 240)
    before = time.perf_counter()
    t, face, normals = dragon.intersect(origin, rays)
    query_seconds = time.perf_counter() - before
    valid = np.isfinite(t)
    # Pick known hits and misses throughout the image; no mesh vertex becomes
    # a predicted scanner point. The reference exhaustively visits every face.
    rng = np.random.default_rng(20261115)
    selected = np.r_[rng.choice(np.flatnonzero(valid), 24, replace=False),
                     rng.choice(np.flatnonzero(~valid), 8, replace=False)]
    reference = np.array([brute_first(vertices, faces, origin, rays[i]) for i in selected])
    assert np.array_equal(np.isfinite(t[selected]), np.isfinite(reference))
    delta = np.abs(t[selected][np.isfinite(reference)] - reference[np.isfinite(reference)])
    assert delta.max() < 1e-5, delta.max()
    checks["32_full_mesh_exhaustive_float64_reference_rays"] = True
    points = origin + rays[valid] * t[valid, None]
    own_visible = dragon.visible(origin, points)
    assert own_visible.all()
    other_visible = dragon.visible([-.35, .35, -.45], points)
    assert 0 < other_visible.sum() < len(points)
    checks["camera_self_shadow_tolerance_and_other_view_occlusion"] = True
    # Flat triangle normal shading and depth visualize only first-hit geometry.
    image = np.full((len(rays), 3), [14, 20, 32], dtype=np.uint8)
    light = np.array([-.5, .7, -.5]); light /= np.linalg.norm(light)
    brightness = .24 + .76 * np.maximum(0, normals[valid] @ light)
    image[valid] = np.clip(brightness[:, None] * [200, 175, 110], 0, 255).astype(np.uint8)
    Image.fromarray(image.reshape(240, 320, 3)).resize((960, 720)).save(root / "dragon-first-hit-preview.png")
    report = {"scope": "Forward mesh raycasting only; no scanner inverse or hardware test",
              "checks": checks, "all_passed": all(checks.values()),
              "versions": {"numpy": np.__version__, "open3d": o3d.__version__},
              "mesh_vertices": len(vertices), "mesh_triangles": len(faces),
              "rays": len(rays), "first_hits": int(valid.sum()),
              "other_view_unoccluded": int(other_visible.sum()),
              "exhaustive_reference_rays": len(selected),
              "maximum_first_hit_parameter_error": float(delta.max()),
              "mesh_build_seconds": build_seconds, "ray_batch_seconds": query_seconds,
              "input_sha256": {n: hashlib.sha256((root / n).read_bytes()).hexdigest()
                               for n in ["mesh_scene.py", "dragon-normalized.npz"]}}
    (root / "raycast-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
