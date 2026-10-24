"""Fail-closed separation certificates for the finite SO101 grasp rig.

Complete compiled mesh vertices and box corners define the queried convex
geometry. A certificate is a lower bound, never a measured CCD distance.
The legacy checker remains available to other experiment entry points.
"""
from __future__ import annotations

import itertools
import math

import mujoco
import numpy as np

from collision_scene import CollisionChecker
from support_native import NativeSupport


class ConservativeCollisionChecker(CollisionChecker):
    """Reuse the original pair policy, limits and independent planning data."""

    def __init__(self, model, *, gripper=.35, margin_m=.002, capture_native_geometry=False,
                 mesh_box_axis_refinement=False):
        super().__init__(model, gripper=gripper, margin_m=margin_m)
        if type(mesh_box_axis_refinement) is not bool:
            raise ValueError('mesh_box_axis_refinement must be a bool')
        self.mesh_box_axis_refinement = mesh_box_axis_refinement
        self._mesh_box_axes = None
        self.mesh_box_refinement_stats = {
            'attempted_frames': 0, 'certified_frames': 0, 'rejected_frames': 0,
            'error_frames': 0, 'pair_queries': 0, 'certified_pairs': 0,
        }
        if margin_m <= 0:
            raise ValueError('A separation certificate requires a positive margin')
        self.geometry_ids = np.flatnonzero(model.geom_group == 3)
        local_index = {int(g): i for i, g in enumerate(self.geometry_ids)}
        self.pair_indices = np.asarray([[local_index[a], local_index[b]]
                                       for a, b in self.pairs], dtype=np.int64)
        points, kinds = [], []
        corners = np.asarray(list(itertools.product((-1., 1.), repeat=3)))
        for gid in self.geometry_ids:
            kind = int(model.geom_type[gid])
            if kind == int(mujoco.mjtGeom.mjGEOM_MESH):
                mid = int(model.geom_dataid[gid])
                begin = int(model.mesh_vertadr[mid])
                count = int(model.mesh_vertnum[mid])
                points.append(np.array(model.mesh_vert[begin:begin+count], dtype=np.float64))
                kinds.append('mesh')
            elif kind == int(mujoco.mjtGeom.mjGEOM_BOX):
                points.append(corners * model.geom_size[gid])
                kinds.append('box')
            else:
                raise ValueError('Separation certificates support only finite mesh/box geometry')
        self.native = (NativeSupport(points, kinds, capture_geometry=True)
                       if capture_native_geometry is True else NativeSupport(points, kinds))
        self._native_query = self.native.bind_pairs(self.pair_indices)
        self.distance_kind = 'certified_lower_bound'

    def evaluate(self, q5orq6, *, require_fixed_gripper=True, certificate_margin_m=None,
                 direction_hints=False):
        original = self._evaluate_original(
            q5orq6, require_fixed_gripper=require_fixed_gripper,
            certificate_margin_m=certificate_margin_m, direction_hints=direction_hints)
        if (not self.mesh_box_axis_refinement or original['valid']
                or original.get('reason') != 'uncertified_geometry_clearance'
                or original.get('certificate_reason') != 'no_separation_certificate'):
            return original
        stats = self.mesh_box_refinement_stats
        stats['attempted_frames'] += 1
        try:
            if self._mesh_box_axes is None:
                from mesh_box_axes import MeshBoxAxes
                self._mesh_box_axes = MeshBoxAxes(self.model)
            refined = self._mesh_box_axes.refine(
                self, original, margin_m=certificate_margin_m)
            stats['pair_queries'] += sum(row.get('queried') is True for row in refined['pairs'])
            stats['certified_pairs'] += sum(row.get('certified') is True for row in refined['pairs'])
            if refined.get('error'):
                stats['error_frames'] += 1
            if refined['supplemental_valid'] is True:
                stats['certified_frames'] += 1
                return refined['refined_result']
        except Exception:
            # Optional direction generation/backend errors retain the original
            # conservative rejection. They cannot turn into distance evidence.
            stats['error_frames'] += 1
        stats['rejected_frames'] += 1
        return original

    def _evaluate_original(self, q5orq6, *, require_fixed_gripper=True,
                           certificate_margin_m=None, direction_hints=False):
        margin = self.margin_m if certificate_margin_m is None else float(certificate_margin_m)
        if not math.isfinite(margin) or margin < self.margin_m:
            raise ValueError('Certificate margin must retain or increase the original guard margin')
        invalid = {'valid': False, 'min_distance_m': None, 'pair': None,
                   'reason': 'invalid_configuration', 'distance_kind': self.distance_kind}
        try:
            q = np.asarray(q5orq6, dtype=float)
        except (TypeError, ValueError):
            return invalid
        if q.shape not in ((5,), (6,)) or not np.isfinite(q).all():
            return dict(invalid, reason='configuration_shape_or_nonfinite')
        q = np.r_[q, self.gripper] if q.shape == (5,) else q.copy()
        if require_fixed_gripper and not math.isclose(float(q[5]), self.gripper,
                                                     rel_tol=0, abs_tol=1e-9):
            return dict(invalid, reason='gripper_not_fixed')
        if np.any(q < self.model.jnt_range[:, 0]) or np.any(q > self.model.jnt_range[:, 1]):
            return dict(invalid, reason='joint_limit')
        self.data.qpos[:] = q
        self.data.qvel[:] = 0
        try:
            mujoco.mj_kinematics(self.model, self.data)
            inputs = (self.data.geom_xpos[self.geometry_ids],
                      self.data.geom_xmat[self.geometry_ids].reshape(-1, 3, 3), margin)
            result = (self._native_query.summary(*inputs, direction_hints=True)
                      if direction_hints is True else self._native_query.summary(*inputs))
        except (RuntimeError, ValueError) as error:
            return dict(invalid, reason='geometry_certificate_unavailable', detail=str(error))
        nearest = result['nearest_index']
        first, second = self.pairs[nearest]
        lower_bound = result['lower_bound_m'] if np.isfinite(result['lower_bound_m']) else None
        return {'valid': result['valid'],
                'min_distance_m': lower_bound if result['valid'] else None,
                'pair_lower_bound_m': lower_bound,
                'distance_kind': self.distance_kind,
                'reason': 'clear' if result['valid'] else 'uncertified_geometry_clearance',
                'certificate_reason': result['certificate_reason'],
                'pair': [self._names[first], self._names[second]],
                'certified_pairs': result['certified_pairs'],
                'checked_pairs': result['checked_pairs']}
