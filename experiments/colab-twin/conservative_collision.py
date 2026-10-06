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

    def __init__(self, model, *, gripper=.35, margin_m=.002):
        super().__init__(model, gripper=gripper, margin_m=margin_m)
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
        self.native = NativeSupport(points, kinds)
        self.distance_kind = 'certified_lower_bound'

    def evaluate(self, q5orq6, *, require_fixed_gripper=True):
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
            result = self.native.evaluate(self.data.geom_xpos[self.geometry_ids],
                                          self.data.geom_xmat[self.geometry_ids].reshape(-1, 3, 3),
                                          self.pair_indices, self.margin_m)
        except (RuntimeError, ValueError) as error:
            return dict(invalid, reason='geometry_certificate_unavailable', detail=str(error))
        failures = np.flatnonzero(~result['certified'])
        bounds = result['lower_bound_m']
        nearest = int(failures[0]) if len(failures) else int(np.argmin(bounds))
        first, second = self.pairs[nearest]
        lower_bound = float(bounds[nearest]) if np.isfinite(bounds[nearest]) else None
        return {'valid': not len(failures),
                'min_distance_m': lower_bound if not len(failures) else None,
                'pair_lower_bound_m': lower_bound,
                'distance_kind': self.distance_kind,
                'reason': 'clear' if not len(failures) else 'uncertified_geometry_clearance',
                'certificate_reason': str(result['reason'][nearest]),
                'pair': [self._names[first], self._names[second]],
                'certified_pairs': int(result['certified'].sum()),
                'checked_pairs': len(self.pairs)}
