"""Simulation-only adapter: actual MuJoCo state -> certified joint target.

This module does not step physics or access hardware. A stopped result is
latched until an explicit reset; callers must never substitute the raw action.
"""
from __future__ import annotations

import time
import mujoco
import numpy as np

from arm_geometry import build_arm_geometry, world_ellipsoids
from cbf_filter import Ellipsoid, FilterResult, SafetyFilter
from hazard_tracking import TrackingFailure

JOINT_NAMES = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper")


class SimulationSafetyAdapter:
    def __init__(self, model, *, control_dt=.02, velocity_limit=.3, margin_m=.012,
                 barrier_buffer_m=.006, plane_reference="gradient", allow_visible_enclosure=False):
        self.model = model
        self.ellipsoids, self.geometry_metadata = build_arm_geometry(model)
        self.q_indices = np.array([int(model.joint(n).qposadr[0]) for n in JOINT_NAMES])
        self.ctrl_indices = np.array([model.actuator(n).id for n in JOINT_NAMES])
        self.bounds = np.array([model.joint(n).range for n in JOINT_NAMES])
        for i, aid in enumerate(self.ctrl_indices):
            if model.actuator_ctrllimited[aid]:
                self.bounds[i, 0] = max(self.bounds[i, 0], model.actuator_ctrlrange[aid, 0])
                self.bounds[i, 1] = min(self.bounds[i, 1], model.actuator_ctrlrange[aid, 1])
        self.bounds[5] = self.geometry_metadata["jaw_range_rad"]
        self.filter = SafetyFilter(dt=control_dt, max_joint_velocity=velocity_limit,
                                   margin_m=margin_m, barrier_buffer_m=barrier_buffer_m,
                                   plane_reference=plane_reference)
        self.stopped_reason = None
        self.allow_visible_enclosure = allow_visible_enclosure

    def reset(self):
        self.filter.reset()
        self.stopped_reason = None

    def _stop(self, reason):
        self.stopped_reason = reason
        return FilterResult("stopped", None, {"reason": reason})

    def apply(self, data, nominal_target, hazard, *, step=None, max_age_steps=5,
              hazard_velocity=None):
        """Refresh FK, validate perception, filter; leave ctrl/qpos untouched.

        Ellipsoid is an explicit simulator oracle. A tracked HazardEstimate
        must carry freshness/status and cannot silently degrade to the oracle.
        """
        started = time.perf_counter()
        if self.stopped_reason is not None:
            return self._stop("latched:" + self.stopped_reason.removeprefix("latched:"))
        if not isinstance(hazard, Ellipsoid):
            if step is None or not hasattr(hazard, "require_safe"):
                return self._stop("unverified_perception")
            try:
                hazard.require_safe(step, max_age_steps)
                if getattr(hazard, "fit_method", None) == "conservative_pca_visible_points" and not self.allow_visible_enclosure:
                    return self._stop("perception_missing_whole_obstacle_envelope")
                hazard = Ellipsoid(hazard.center, hazard.rotation, hazard.axes)
            except (TrackingFailure, ValueError, TypeError):
                return self._stop("perception_invalid_or_stale")
        mujoco.mj_forward(self.model, data)
        q = data.qpos[self.q_indices].copy()
        if q[5] < self.bounds[5, 0] - 1e-9 or q[5] > self.bounds[5, 1] + 1e-9:
            return self._stop("jaw_outside_modelled_sweep")
        ellipsoids = world_ellipsoids(self.model, data, self.ellipsoids,
                                     joint_names=JOINT_NAMES)
        result = self.filter.filter(q, nominal_target, ellipsoids, hazard,
                                    self.bounds, hazard_velocity)
        result.metrics["adapter_latency_ms"] = (time.perf_counter() - started) * 1000
        if result.status == "stopped":
            self.stopped_reason = result.metrics["reason"]
        return result
