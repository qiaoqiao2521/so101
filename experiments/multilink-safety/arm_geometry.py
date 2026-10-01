"""Five conservative SO101 distal-link envelopes from MuJoCo collision geometry.

The forearm is covered by three overlapping ellipsoids, the wrist by one,
and the fixed and moving fingers together by one. The upper arm, elbow,
shoulder and base are outside this filter's scope. These are model-derived
envelopes, not calibrated hardware geometry or a functional-safety claim.
"""
from __future__ import annotations

from dataclasses import dataclass
import itertools
from typing import Sequence

import mujoco
import numpy as np

BODY_SCOPE = ("lower_arm", "wrist", "gripper", "moving_jaw_so101_v1")
EXCLUDED_SCOPE = ("upper_arm", "shoulder", "base", "carried_object")
DEFAULT_JAW_RANGE = (.015, .5)


@dataclass(frozen=True)
class LinkEllipsoid:
    name: str
    body_name: str
    center_local: np.ndarray
    rotation_local: np.ndarray
    semi_axes: np.ndarray

    def __post_init__(self):
        center = np.asarray(self.center_local, dtype=float)
        rotation = np.asarray(self.rotation_local, dtype=float)
        axes = np.asarray(self.semi_axes, dtype=float)
        if center.shape != (3,) or axes.shape != (3,) or rotation.shape != (3, 3):
            raise ValueError("Invalid ellipsoid shape")
        if not all(np.isfinite(x).all() for x in (center, rotation, axes)):
            raise ValueError("Ellipsoid parameters must be finite")
        if np.any(axes <= 0) or not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-8) or np.linalg.det(rotation) < .999999:
            raise ValueError("Axes must be positive and rotation must be right handed")
        object.__setattr__(self, "center_local", center.copy())
        object.__setattr__(self, "rotation_local", rotation.copy())
        object.__setattr__(self, "semi_axes", axes.copy())

    def normalized_radius_squared(self, local_points):
        points = np.asarray(local_points, dtype=float)
        return np.sum((((points - self.center_local) @ self.rotation_local) / self.semi_axes) ** 2, axis=-1)

    def as_dict(self):
        return {"name": self.name, "body_name": self.body_name,
                "center_local_m": self.center_local.tolist(),
                "rotation_local": self.rotation_local.tolist(),
                "semi_axes_m": self.semi_axes.tolist()}


@dataclass(frozen=True)
class WorldEllipsoid:
    name: str
    body_name: str
    center: np.ndarray
    rotation: np.ndarray
    semi_axes: np.ndarray
    jacobian: np.ndarray  # Linear xyz, then angular xyz; columns are selected DOFs.


def _rotation(quaternion):
    matrix = np.zeros(9)
    mujoco.mju_quat2Mat(matrix, np.asarray(quaternion, dtype=float))
    return matrix.reshape(3, 3)


def _geom_vertices_faces(model, geom_id):
    """Compiled mesh vertices transformed into the geom's owning body frame."""
    kind = int(model.geom_type[geom_id])
    if kind == mujoco.mjtGeom.mjGEOM_MESH:
        mesh_id = int(model.geom_dataid[geom_id])
        start, count = int(model.mesh_vertadr[mesh_id]), int(model.mesh_vertnum[mesh_id])
        vertices = np.asarray(model.mesh_vert[start:start + count], dtype=float)
        start, count = int(model.mesh_faceadr[mesh_id]), int(model.mesh_facenum[mesh_id])
        faces = np.asarray(model.mesh_face[start:start + count], dtype=int)
    elif kind == mujoco.mjtGeom.mjGEOM_BOX:
        vertices = np.array(list(itertools.product((-1., 1.), repeat=3))) * model.geom_size[geom_id]
        # Bounding-box corners conservatively contain the complete box.
        faces = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5],
                          [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6],
                          [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    else:
        raise ValueError(f"Unsupported protected collision geom {geom_id}, type={kind}; refusing partial coverage")
    return vertices @ _rotation(model.geom_quat[geom_id]).T + model.geom_pos[geom_id], faces


def _body_geometries(model, body_name):
    body = model.body(body_name).id
    ids = [i for i in range(model.ngeom) if model.geom_bodyid[i] == body
           and (model.geom_contype[i] or model.geom_conaffinity[i])]
    if not ids:
        raise ValueError(f"No collision geometry on protected body {body_name}")
    return [(i, *_geom_vertices_faces(model, i)) for i in ids]


def _points(geometries, *, include_surface=False):
    points = []
    for _, vertices, faces in geometries:
        points.append(vertices)
        if include_surface:
            triangles = vertices[faces]
            points.extend([triangles.mean(axis=1),
                           (triangles[:, 0] + triangles[:, 1]) / 2,
                           (triangles[:, 1] + triangles[:, 2]) / 2,
                           (triangles[:, 2] + triangles[:, 0]) / 2])
    return np.concatenate(points)


def _pca_frame(points):
    centered = points - points.mean(axis=0)
    _, rotation = np.linalg.eigh(centered.T @ centered)
    rotation = rotation[:, ::-1]
    # Deterministic column signs, followed by right-handed correction.
    for j in range(3):
        if rotation[np.argmax(np.abs(rotation[:, j])), j] < 0:
            rotation[:, j] *= -1
    if np.linalg.det(rotation) < 0:
        rotation[:, -1] *= -1
    return rotation


def _box_ellipsoid(name, body, lower, upper, rotation, padding_m):
    midpoint = (lower + upper) / 2
    # sqrt(3) times box half widths encloses its entire volume, including
    # faces and all triangle interiors, rather than only sampled vertices.
    axes = np.sqrt(3.) * ((upper - lower) / 2 + padding_m)
    return LinkEllipsoid(name, body, rotation @ midpoint, rotation, axes)


def _point_ellipsoid(name, body, points, rotation, padding_m):
    """Contain the convex hull of points, hence every triangle they bound."""
    projected = points @ rotation
    lower, upper = projected.min(axis=0), projected.max(axis=0)
    midpoint = (lower + upper) / 2
    base_axes = (upper - lower) / 2 + padding_m
    scale = max(1., float(np.sqrt(np.sum(((projected - midpoint) / base_axes) ** 2, axis=1).max())))
    # A further margin also protects mesh float32 and clipping roundoff.
    axes = base_axes * scale + padding_m
    return LinkEllipsoid(name, body, rotation @ midpoint, rotation, axes)


def _slab_points(geometries, rotation, lower, upper):
    """Vertices of triangles clipped at two long-axis planes.

    Convex containment of the original vertices and plane/edge intersections
    contains the full clipped triangles; surface samples alone would not prove
    that a union of three ellipsoids covers the gaps between their vertices.
    """
    result = []
    axis = rotation[:, 0]
    for _, vertices, faces in geometries:
        coordinate = vertices @ axis
        result.append(vertices[(coordinate >= lower) & (coordinate <= upper)])
        triangles = vertices[faces]
        for first, second in ((0, 1), (1, 2), (2, 0)):
            start, end = triangles[:, first], triangles[:, second]
            a, b = start @ axis, end @ axis
            for bound in (lower, upper):
                crosses = ((a <= bound) & (b >= bound) | (b <= bound) & (a >= bound)) & (np.abs(b - a) > 1e-14)
                fraction = (bound - a[crosses]) / (b[crosses] - a[crosses])
                result.append(start[crosses] + fraction[:, None] * (end[crosses] - start[crosses]))
    return np.concatenate(result)


def _jaw_coefficients(model, jaw_points):
    """p(q)=c+a*cos(q)+b*sin(q), expressed in the fixed gripper frame."""
    query = mujoco.MjData(model)
    gripper_id, jaw_id = model.body("gripper").id, model.body("moving_jaw_so101_v1").id
    joint = model.joint("gripper")
    address = int(joint.qposadr[0])
    coordinates = []
    for angle in (0., np.pi / 2, np.pi):
        query.qpos[address] = angle
        mujoco.mj_forward(model, query)
        world = jaw_points @ query.xmat[jaw_id].reshape(3, 3).T + query.xpos[jaw_id]
        coordinates.append((world - query.xpos[gripper_id]) @ query.xmat[gripper_id].reshape(3, 3))
    center = (coordinates[0] + coordinates[2]) / 2
    return center, coordinates[0] - center, coordinates[1] - center


def _arc_bounds(center, cosine, sine, interval):
    lo, hi = interval
    endpoints = np.stack([center + cosine * np.cos(lo) + sine * np.sin(lo),
                          center + cosine * np.cos(hi) + sine * np.sin(hi)])
    lower, upper = endpoints.min(axis=(0, 1)), endpoints.max(axis=(0, 1))
    phase = np.arctan2(sine, cosine)
    for offset in range(-3, 4):
        angle = phase + offset * np.pi
        valid = (angle >= lo) & (angle <= hi)
        values = center + cosine * np.cos(angle) + sine * np.sin(angle)
        lower = np.minimum(lower, np.where(valid, values, np.inf).min(axis=0))
        upper = np.maximum(upper, np.where(valid, values, -np.inf).max(axis=0))
    return lower, upper


def build_arm_geometry(model, *, jaw_range=DEFAULT_JAW_RANGE, padding_m=.0015):
    """Return (five ellipsoids, JSON-safe source/scope metadata).

    No execution MjData is accepted or changed. The moving finger's continuous
    arc extrema, not merely two open/closed snapshots, bound its sweep.
    """
    if not np.isfinite(padding_m) or padding_m <= 0:
        raise ValueError("padding_m must be positive")
    jaw_range = tuple(float(x) for x in jaw_range)
    joint_range = model.joint("gripper").range
    if len(jaw_range) != 2 or not np.isfinite(jaw_range).all() or jaw_range[0] >= jaw_range[1] or jaw_range[0] < joint_range[0] or jaw_range[1] > joint_range[1]:
        raise ValueError("jaw_range must be an ordered interval within model limits")
    bodies = {body: _body_geometries(model, body) for body in BODY_SCOPE}
    ellipsoids = []
    forearm = _points(bodies["lower_arm"])
    rotation = _pca_frame(forearm)
    projected = forearm @ rotation
    lower, upper = projected.min(axis=0), projected.max(axis=0)
    width = (upper[0] - lower[0]) / 3
    for index in range(3):
        start, end = lower.copy(), upper.copy()
        start[0] = max(lower[0], lower[0] + index * width - .1 * width)
        end[0] = min(upper[0], lower[0] + (index + 1) * width + .1 * width)
        clipped = _slab_points(bodies["lower_arm"], rotation, start[0], end[0])
        ellipsoids.append(_point_ellipsoid(f"forearm_{index}", "lower_arm", clipped, rotation, padding_m))
    wrist = _points(bodies["wrist"])
    rotation = _pca_frame(wrist)
    ellipsoids.append(_point_ellipsoid("wrist", "wrist", wrist, rotation, padding_m))
    fixed = _points(bodies["gripper"])
    jaw = _points(bodies["moving_jaw_so101_v1"])
    center, cosine, sine = _jaw_coefficients(model, jaw)
    lower, upper = _arc_bounds(center, cosine, sine, jaw_range)
    lower, upper = np.minimum(lower, fixed.min(axis=0)), np.maximum(upper, fixed.max(axis=0))
    ellipsoids.append(_box_ellipsoid("gripper_sweep", "gripper", lower, upper, np.eye(3), padding_m))
    sources = [{"body": body, "geom_id": i, "geom_name": model.geom(i).name,
                "mesh_name": model.mesh(int(model.geom_dataid[i])).name if model.geom_type[i] == mujoco.mjtGeom.mjGEOM_MESH else None,
                "vertex_count": len(vertices), "face_count": len(faces)}
               for body, items in bodies.items() for i, vertices, faces in items]
    metadata = {"covered_bodies": list(BODY_SCOPE), "excluded_bodies": list(EXCLUDED_SCOPE),
                "jaw_range_rad": list(jaw_range), "padding_m": padding_m,
                "method": "Conservative convex point envelopes; three overlapping clipped-triangle forearm slabs; analytic continuous jaw sweep box",
                "geometry_sources": sources, "hardware_calibrated": False,
                "ellipsoids": [x.as_dict() for x in ellipsoids]}
    return ellipsoids, metadata


def world_ellipsoids(model, data, ellipsoids: Sequence[LinkEllipsoid], *, joint_names=None):
    """Read world transforms and 6-by-n Jacobians from a forwarded MjData.

    joint_names selects hinge DOFs in the supplied order; omission returns all
    model velocity columns (including free-body DOFs in a contact workcell).
    This function does not call mj_forward or modify the execution state.
    """
    columns = np.arange(model.nv) if joint_names is None else np.array([int(model.joint(name).dofadr[0]) for name in joint_names])
    result = []
    for ellipsoid in ellipsoids:
        body = model.body(ellipsoid.body_name).id
        body_rotation = data.xmat[body].reshape(3, 3)
        center = data.xpos[body] + body_rotation @ ellipsoid.center_local
        linear, angular = np.zeros((3, model.nv)), np.zeros((3, model.nv))
        mujoco.mj_jac(model, data, linear, angular, center, body)
        result.append(WorldEllipsoid(ellipsoid.name, ellipsoid.body_name, center.copy(),
                                     body_rotation @ ellipsoid.rotation_local, ellipsoid.semi_axes.copy(),
                                     np.concatenate([linear, angular])[:, columns]))
    return result


def audit_geometry_coverage(model, ellipsoids, *, jaw_range=DEFAULT_JAW_RANGE, jaw_samples=17):
    """Vertices, every face centroid and every triangle edge midpoint audit.

    The conservative box construction provides continuous-volume containment;
    this independent dense surface audit detects frame or transform mistakes.
    Moving-finger samples validate the analytic sweep at intermediate angles.
    """
    if jaw_samples < 2:
        raise ValueError("At least two jaw angles are required")
    results = []
    for body in BODY_SCOPE:
        points = _points(_body_geometries(model, body), include_surface=True)
        candidates = [x for x in ellipsoids if x.body_name == ("gripper" if body == "moving_jaw_so101_v1" else body)]
        if not candidates:
            raise ValueError(f"Missing envelope for protected body {body}")
        point_sets = [points]
        if body == "moving_jaw_so101_v1":
            center, cosine, sine = _jaw_coefficients(model, points)
            point_sets = (center + cosine * np.cos(angle) + sine * np.sin(angle)
                          for angle in np.linspace(*jaw_range, jaw_samples))
        total, outside, maximum = 0, 0, 0.
        for sample in point_sets:
            radius = np.min(np.stack([x.normalized_radius_squared(sample) for x in candidates]), axis=0)
            total += len(radius)
            outside += int(np.count_nonzero(radius > 1 + 1e-9))
            maximum = max(maximum, float(radius.max()))
        results.append({"body": body, "surface_sample_count": total, "outside_count": outside,
                        "max_min_normalized_radius_squared": maximum})
    return {"passed": all(x["outside_count"] == 0 for x in results), "bodies": results,
            "jaw_angle_samples": jaw_samples, "sampling": "vertices + triangle edge midpoints + face centroids",
            "coverage_scope": list(BODY_SCOPE), "excluded_scope": list(EXCLUDED_SCOPE)}
