"""Independent forward mesh observations using Open3D's CPU first-hit BVH.

New helper: MIT; see HELPER-LICENSE. Mesh data has separate Stanford terms.
No scanner inverse, decoder, pose estimator or reconstruction is imported here.
"""
from pathlib import Path

import numpy as np
import open3d as o3d


def load_mesh(path):
    """Return (float64 vertices[N,3], int32 faces[M,3]) without repair/remesh."""
    path = Path(path)
    if path.suffix == ".npz":
        with np.load(path, allow_pickle=False) as data:
            return data["vertices"].copy(), data["faces"].copy()
    mesh = o3d.io.read_triangle_mesh(str(path), enable_post_processing=False)
    return np.asarray(mesh.vertices).copy(), np.asarray(mesh.triangles).copy()


class Scene:
    """Two-sided triangle first-hit queries; rays use o + t*d, not unit d.

    Open3D raycasting uses float32. Returned t is a parameter: it is a metric
    distance only if d is a unit vector. Misses are inf/-1/zero-normal.
    No ground-truth mesh points are passed to any scanner inverse by this API.
    """

    def __init__(self, vertices, faces, nthreads=0):
        vertices = np.asarray(vertices, dtype=np.float64)
        faces = np.asarray(faces)
        if (vertices.ndim != 2 or vertices.shape[1] != 3
                or not len(vertices) or not np.isfinite(vertices).all()):
            raise ValueError("vertices must be nonempty finite Nx3")
        if (faces.ndim != 2 or faces.shape[1] != 3 or not len(faces)
                or not np.issubdtype(faces.dtype, np.integer)
                or faces.min() < 0 or faces.max() >= len(vertices)):
            raise ValueError("faces must be in-range integer Mx3 triangles")
        if not np.isfinite(vertices.astype(np.float32)).all():
            raise ValueError("vertices exceed float32 range")
        self.vertices = vertices.copy()
        self.faces = faces.astype(np.int32, copy=True)
        self.nthreads = int(nthreads)
        if self.nthreads < 0:
            raise ValueError("nthreads must be nonnegative")
        self._scene = o3d.t.geometry.RaycastingScene(nthreads=self.nthreads)
        self._scene.add_triangles(
            o3d.core.Tensor(vertices.astype(np.float32)),
            o3d.core.Tensor(faces.astype(np.uint32)),
        )

    def intersect(self, origins, directions, tnear=0.0, tfar=np.inf):
        """Return (t[N], face_index[N], unit_triangle_normal[N,3]).

        origins may be one XYZ or match directions[N,3]. tnear is a scalar
        nonnegative ray parameter; tfar may be a scalar or an N-vector.
        Rays are shifted by tnear before the native query, so clipping also
        works when an earlier surface lies before the near bound.
        """
        directions = np.asarray(directions, dtype=np.float64)
        if directions.ndim != 2 or directions.shape[1] != 3:
            raise ValueError("directions must be Nx3")
        origins = np.broadcast_to(np.asarray(origins, dtype=np.float64), directions.shape)
        if (not np.isfinite(origins).all() or not np.isfinite(directions).all()
                or np.any(np.linalg.norm(directions, axis=1) == 0)):
            raise ValueError("rays must be finite with nonzero directions")
        tnear = float(tnear)
        far = np.broadcast_to(np.asarray(tfar, dtype=np.float64), (len(directions),))
        if not np.isfinite(tnear) or tnear < 0 or np.any(np.isnan(far)) or np.any(far < tnear):
            raise ValueError("invalid near/far bounds")
        if not len(directions):
            return np.empty(0), np.empty(0, dtype=np.int64), np.empty((0, 3))
        rays = np.concatenate((origins + tnear * directions, directions), axis=1).astype(np.float32)
        if not np.isfinite(rays).all():
            raise ValueError("rays exceed float32 range")
        result = self._scene.cast_rays(o3d.core.Tensor(rays), nthreads=self.nthreads)
        t = result["t_hit"].numpy().astype(np.float64) + tnear
        face = result["primitive_ids"].numpy().astype(np.int64)
        normal = result["primitive_normals"].numpy().astype(np.float64)
        valid = np.isfinite(t) & (t <= far) & (face < len(self.faces))
        t[~valid] = np.inf
        face[~valid] = -1
        normal[~valid] = 0
        return t, face, normal

    def visible(self, origins, targets, epsilon_m=2e-5):
        """True when no triangle blocks the open segment to each target.

        A 20 micrometre target tolerance avoids float32 self-shadow artifacts.
        This is geometric visibility only, not projector-FOV or brightness.
        """
        targets = np.asarray(targets, dtype=np.float64)
        origins = np.broadcast_to(np.asarray(origins, dtype=np.float64), targets.shape)
        if targets.ndim != 2 or targets.shape[1] != 3:
            raise ValueError("targets must be Nx3")
        delta = targets - origins
        length = np.linalg.norm(delta, axis=1)
        if not np.isfinite(epsilon_m) or epsilon_m <= 0 or np.any(length <= epsilon_m):
            raise ValueError("epsilon must be positive and segments must be longer")
        t, _, _ = self.intersect(origins, delta / length[:, None])
        return t >= length - epsilon_m

    def distance(self, points):
        """Unsigned closest triangle distance, scoring only (float32 engine)."""
        points = np.asarray(points, dtype=np.float64)
        if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
            raise ValueError("points must be finite Nx3")
        if not len(points):
            return np.empty(0)
        return self._scene.compute_distance(
            o3d.core.Tensor(points.astype(np.float32)), nthreads=self.nthreads
        ).numpy().astype(np.float64)


def camera_rays(K, camera_to_world, width, height):
    """Standard pinhole integer pixel centers; camera +X right/+Y down/+Z forward.

    Output origin[3], directions[height*width,3], row-major. Direction camera Z
    is one, so a hit t is camera-forward depth rather than Euclidean distance.
    This forward fixture helper has no dependency on either inverse scanner.
    """
    K = np.asarray(K, dtype=np.float64)
    pose = np.asarray(camera_to_world, dtype=np.float64)
    if (K.shape != (3, 3) or pose.shape != (4, 4)
            or not np.isfinite(K).all() or not np.isfinite(pose).all()
            or abs(np.linalg.det(K)) < 1e-12
            or not np.allclose(pose[3], [0, 0, 0, 1], atol=1e-10)
            or not np.allclose(pose[:3, :3].T @ pose[:3, :3], np.eye(3), atol=1e-8)
            or not np.isclose(np.linalg.det(pose[:3, :3]), 1, atol=1e-8)
            or int(width) != width or int(height) != height or width < 1 or height < 1):
        raise ValueError("invalid pinhole camera")
    u, v = np.meshgrid(np.arange(int(width)), np.arange(int(height)))
    homogeneous = np.column_stack((u.ravel(), v.ravel(), np.ones(u.size)))
    directions = homogeneous @ np.linalg.inv(K).T @ pose[:3, :3].T
    return pose[:3, 3].copy(), directions


def look_at(eye, target, world_up=(0, 1, 0)):
    """Camera-to-world rigid pose in the declared right/down/forward convention."""
    eye, target, up = [np.asarray(v, dtype=np.float64) for v in (eye, target, world_up)]
    if any(v.shape != (3,) or not np.isfinite(v).all() for v in (eye, target, up)):
        raise ValueError("look-at inputs must be finite XYZ")
    z = target - eye
    if np.linalg.norm(z) < 1e-12:
        raise ValueError("eye and target coincide")
    z /= np.linalg.norm(z)
    x = np.cross(z, up)
    if np.linalg.norm(x) < 1e-12:
        raise ValueError("view and up are parallel")
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    pose = np.eye(4)
    pose[:3, :3] = np.column_stack((x, y, z))
    pose[:3, 3] = eye
    return pose
