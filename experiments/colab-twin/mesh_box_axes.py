"""Extra search directions for an uncertified mesh/box pair.

Directions are suggestions only. NativeSupport reprojects every complete
geometry using the original interval certificate and unchanged margin.
This module does not install a checker, modify geometry, or admit a task.
"""
from __future__ import annotations

import math
import mujoco
import numpy as np
from scipy.spatial import ConvexHull


def _json_value(value):
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return None if isinstance(value, float) and not math.isfinite(value) else value


class MeshBoxAxes:
    def __init__(self, model):
        self.model = model
        self._mesh_axes = {}

    def _local_axes(self, gid):
        mid = int(self.model.geom_dataid[gid])
        if mid not in self._mesh_axes:
            begin = int(self.model.mesh_vertadr[mid])
            count = int(self.model.mesh_vertnum[mid])
            points = np.asarray(self.model.mesh_vert[begin:begin+count], dtype=float)
            hull = ConvexHull(points)
            edges = {tuple(sorted((int(tri[i]), int(tri[j]))))
                     for tri in hull.simplices for i, j in ((0, 1), (1, 2), (2, 0))}
            edge_vectors = np.asarray([points[j]-points[i] for i, j in sorted(edges)])
            self._mesh_axes[mid] = (hull.equations[:, :3].copy(), edge_vectors)
        return self._mesh_axes[mid]

    def directions(self, data, first, second):
        kinds = [int(self.model.geom_type[g]) for g in (first, second)]
        mesh, box = int(mujoco.mjtGeom.mjGEOM_MESH), int(mujoco.mjtGeom.mjGEOM_BOX)
        if sorted(kinds) != sorted((mesh, box)):
            return np.empty((0, 3))
        mesh_gid, box_gid = (first, second) if kinds[0] == mesh else (second, first)
        normals, edges = self._local_axes(mesh_gid)
        mesh_r = data.geom_xmat[mesh_gid].reshape(3, 3)
        box_r = data.geom_xmat[box_gid].reshape(3, 3)
        world_edges = edges @ mesh_r.T
        axes = np.concatenate((normals @ mesh_r.T, box_r.T,
                               np.cross(world_edges[:, None, :], box_r.T[None, :, :])
                               .reshape(-1, 3)))
        lengths = np.linalg.norm(axes, axis=1)
        axes = axes[np.isfinite(lengths) & (lengths > 1e-12)]
        axes = axes / np.linalg.norm(axes, axis=1)[:, None]
        # Dedupe changes search order only. Every retained direction still
        # needs an independent full-geometry interval certificate.
        signs = np.where(axes[np.arange(len(axes)), np.argmax(np.abs(axes), axis=1)] < 0, -1., 1.)
        axes *= signs[:, None]
        _, indices = np.unique(np.round(axes, 10), axis=0, return_index=True)
        return np.ascontiguousarray(axes[np.sort(indices)])

    def inspect(self, checker, q6, *, margin_m=None):
        """Report original and supplemental results; never replace original."""
        margin = checker.margin_m if margin_m is None else margin_m
        original = checker.evaluate(q6, require_fixed_gripper=False,
                                    certificate_margin_m=margin)
        result = {'original': original, 'supplemental_valid': original['valid'],
                  'pairs': [], 'not_physical': True, 'not_admitted': True}
        if original['valid'] or original['reason'] != 'uncertified_geometry_clearance':
            return result
        p = checker.data.geom_xpos[checker.geometry_ids].copy()
        rotations = checker.data.geom_xmat[checker.geometry_ids].reshape(-1, 3, 3).copy()
        details = checker.native.evaluate(p, rotations, checker.pair_indices, margin)
        for index in np.flatnonzero(~details['certified']):
            first, second = checker.pairs[index]
            row = {'pair_index': int(index), 'pair': [checker._names[first], checker._names[second]],
                   'original_lower_bound_m': float(details['lower_bound_m'][index]),
                   'certified': False}
            result['pairs'].append(row)
            try:
                directions = self.directions(checker.data, first, second)
                row['direction_count'] = len(directions)
                if len(directions):
                    detail = checker.native.certify_directions(
                        p, rotations, checker.pair_indices[index], directions, margin)
                    row.update({key: _json_value(np.asarray(value)[0].tolist())
                                for key, value in detail.items()})
            except (RuntimeError, ValueError) as error:
                row['error'] = str(error)
        result['supplemental_valid'] = bool(result['pairs']) and all(
            row['certified'] is True for row in result['pairs'])
        return result
