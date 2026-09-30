"""Position-only SO101 IK with Mink; this module never runs physics or hardware.

The six input/output coordinates use ``JOINT_NAMES`` order. Only the first five
coordinates are solved; the supplied gripper coordinate is held fixed. Failure
means this bounded numerical search found no acceptable candidate, not a proof
that a Cartesian point is outside the robot's mathematical workspace.
"""

from __future__ import annotations

from collections.abc import Callable

import mink
import mujoco
import numpy as np


JOINT_NAMES = (
    "shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"
)
TCP_SITE = "gripperframe"


def _finite_vector(value: np.ndarray, size: int, name: str) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite vector of shape ({size},)") from exc
    if result.shape != (size,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be a finite vector of shape ({size},)")
    return result.copy()


def _joint_layout_and_bounds(model: mujoco.MjModel) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Intersect each named hinge joint's range with its actuator ctrlrange."""
    addresses, lower, upper = [], [], []
    for name in JOINT_NAMES:
        joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        if joint_id < 0 or model.jnt_type[joint_id] != mujoco.mjtJoint.mjJNT_HINGE:
            raise ValueError(f"model requires the SO101 hinge joint {name!r}")
        if not model.jnt_limited[joint_id]:
            raise ValueError(f"model requires finite limits for joint {name!r}")
        lo, hi = model.jnt_range[joint_id].copy()
        for actuator_id in range(model.nu):
            if (
                model.actuator_trntype[actuator_id] == mujoco.mjtTrn.mjTRN_JOINT
                and model.actuator_trnid[actuator_id, 0] == joint_id
                and model.actuator_ctrllimited[actuator_id]
            ):
                ctrl_lo, ctrl_hi = model.actuator_ctrlrange[actuator_id]
                lo, hi = max(lo, ctrl_lo), min(hi, ctrl_hi)
        if not np.all(np.isfinite([lo, hi])) or lo >= hi:
            raise ValueError(f"joint/actuator limits do not define a valid range for {name!r}")
        addresses.append(int(model.jnt_qposadr[joint_id]))
        lower.append(lo)
        upper.append(hi)
    if mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, TCP_SITE) < 0:
        raise ValueError(f"model requires TCP site {TCP_SITE!r}")
    return np.asarray(addresses), np.asarray(lower), np.asarray(upper)


def solve_position_ik(
    model: mujoco.MjModel,
    initial_qpos: np.ndarray,
    target_xyz: np.ndarray,
    *,
    seed: int = 0,
    attempts: int = 8,
    max_iterations: int = 250,
    tolerance_m: float = 0.005,
    candidate_valid: Callable[[np.ndarray], bool] | None = None,
) -> dict:
    """Return an accepted six-coordinate goal or an explicit no-candidate result.

    ``candidate_valid`` can reject collision-invalid goal configurations. IK
    iterations are kinematic queries, not collision-checked executable paths;
    the caller must plan and validate the path separately. Invalid inputs raise
    ``ValueError``. The model and supplied arrays are never modified.
    """
    initial = _finite_vector(initial_qpos, 6, "initial_qpos")
    target = _finite_vector(target_xyz, 3, "target_xyz")
    for value, name in [(attempts, "attempts"), (max_iterations, "max_iterations")]:
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if not np.isscalar(tolerance_m) or not np.isfinite(tolerance_m) or tolerance_m <= 0:
        raise ValueError("tolerance_m must be finite and positive")
    if candidate_valid is not None and not callable(candidate_valid):
        raise ValueError("candidate_valid must be callable")
    addresses, lower, upper = _joint_layout_and_bounds(model)
    if np.any(initial < lower) or np.any(initial > upper):
        raise ValueError("initial_qpos is outside the joint/actuator limit intersection")

    rng = np.random.default_rng(seed)
    configuration = mink.Configuration(model)
    base_q = configuration.q.copy()
    position_limit = mink.ConfigurationLimit(model)
    # Mink exposes bound arrays used to build its QP inequalities. Tighten only
    # this limit instance; the input model retains its original joint limits.
    position_limit.lower[addresses] = lower
    position_limit.upper[addresses] = upper
    velocity_limit = mink.VelocityLimit(
        model, {name: (0.0 if name == "gripper" else 2.0) for name in JOINT_NAMES}
    )
    task = mink.FrameTask(TCP_SITE, "site", position_cost=1.0, orientation_cost=0.0)
    dt = 0.1
    best_error = float("inf")
    rejected_candidates = 0
    solver_failures = 0
    total_iterations = 0

    for attempt in range(1, attempts + 1):
        start = initial.copy() if attempt == 1 else rng.uniform(lower, upper)
        start[5] = initial[5]
        q = base_q.copy()
        q[addresses] = start
        configuration.update(q)
        for iteration in range(max_iterations + 1):
            tcp = configuration.get_transform_frame_to_world(TCP_SITE, "site")
            error = float(np.linalg.norm(tcp.translation() - target))
            best_error = min(best_error, error)
            goal = configuration.q[addresses].copy()
            if error <= tolerance_m:
                if candidate_valid is None or bool(candidate_valid(goal.copy())):
                    return {
                        "status": "solved", "qpos": goal.tolist(), "error_m": error,
                        "iterations": iteration, "attempt": attempt,
                        "total_iterations": total_iterations,
                        "rejected_candidates": rejected_candidates,
                    }
                rejected_candidates += 1
                break
            if iteration == max_iterations:
                break
            # Reset the unused orientation target to the current orientation.
            # Only Cartesian translation is requested from this five-axis arm.
            task.set_target(mink.SE3.from_rotation_and_translation(tcp.rotation(), target))
            try:
                velocity = mink.solve_ik(
                    configuration, [task], dt, solver="daqp", damping=1e-4,
                    limits=[position_limit, velocity_limit], safety_break=True,
                )
            except mink.NoSolutionFound:
                solver_failures += 1
                break
            if not np.all(np.isfinite(velocity)):
                solver_failures += 1
                break
            q = configuration.integrate(velocity, dt)
            q[addresses] = np.clip(q[addresses], lower, upper)
            q[addresses[5]] = initial[5]
            configuration.update(q)
            total_iterations += 1

    return {
        "status": "unreachable", "qpos": None,
        "reason": "candidate_rejected" if rejected_candidates else "search_exhausted",
        "error_m": best_error, "iterations": total_iterations, "attempt": attempts,
        "total_iterations": total_iterations, "rejected_candidates": rejected_candidates,
        "solver_failures": solver_failures, "certified_unreachable": False,
    }
