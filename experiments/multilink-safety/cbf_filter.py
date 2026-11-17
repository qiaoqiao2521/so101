"""CPU joint-space rotating-plane CBF filter for five SO101 link envelopes.

This is a local adaptation of Multi-Link Safety Filtering equation (2) and
AEGIS equation (9), independently implemented in world coordinates. It uses
joint Jacobians directly rather than the paper's J_link @ pinv(J_ee) map.
It is an empirical sampled-data shield, not a functional-safety controller.
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

import numpy as np
import osqp
from scipy import sparse
from scipy.optimize import minimize

SOURCE_METADATA = {
    "variant": "local_joint_space_rotating_plane_cbf",
    "paper": "https://arxiv.org/html/2609.40007v1#S3.SS1",
    "barrier_reference": "https://arxiv.org/html/2512.11891v2#S4.SS3",
    "reference_code_commit": "2457feed5968ae803926e178c8ce8243b9ecdcf9",
    "coordinates": "world translation and left-multiplication world rotation",
    "differences": ["direct joint Jacobians", "known hazard translation velocity term",
                    "hard velocity and position limits", "current-state plane re-certification",
                    "optional stricter QP engineering buffer", "stop on failed certification"],
    "guarantee": "No continuous-time, perception, servo, or hardware safety guarantee",
}


@dataclass(frozen=True)
class Ellipsoid:
    center: np.ndarray
    rotation: np.ndarray
    semi_axes: np.ndarray


@dataclass(frozen=True)
class FilterResult:
    status: str  # accepted, modified, stopped
    action: np.ndarray | None
    metrics: dict[str, Any]


def skew(v):
    v = np.asarray(v, dtype=float)
    return np.array([[0., -v[2], v[1]], [v[2], 0., -v[0]], [-v[1], v[0], 0.]])


def _field(value, name):
    return value[name] if isinstance(value, dict) else getattr(value, name)


def _ellipsoid(value):
    center = np.asarray(_field(value, "center"), dtype=float)
    rotation = np.asarray(_field(value, "rotation"), dtype=float)
    axes = np.asarray(_field(value, "semi_axes"), dtype=float)
    if center.shape != (3,) or rotation.shape != (3, 3) or axes.shape != (3,):
        raise ValueError("invalid ellipsoid dimensions")
    if not all(np.isfinite(x).all() for x in (center, rotation, axes)) or np.any(axes <= 0):
        raise ValueError("nonfinite or nonpositive ellipsoid")
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-8, rtol=0) or not np.isclose(np.linalg.det(rotation), 1., atol=1e-8):
        raise ValueError("ellipsoid rotation must be in SO(3)")
    return Ellipsoid(center.copy(), rotation.copy(), axes.copy())


def barrier_terms(robot, hazard, z):
    """h, d h/d robot world twist, tangent z row, raw z gradient, hazard row.

    Rotation derivative uses R_new = exp(skew(omega) dt) @ R, matching
    MuJoCo's angular Jacobian. Semi-axes are lengths, not quadratic metrics.
    """
    robot, hazard = _ellipsoid(robot), _ellipsoid(hazard)
    z = np.asarray(z, dtype=float)
    if z.shape != (3,) or not np.isfinite(z).all() or np.linalg.norm(z) < 1e-12:
        raise ValueError("invalid separating-plane state")
    z = z / np.linalg.norm(z)
    C = robot.rotation @ np.diag(1. / robot.semi_axes) @ robot.rotation.T
    B = hazard.rotation @ np.diag(hazard.semi_axes) @ hazard.rotation.T
    v = C @ z
    denominator = np.linalg.norm(v)
    support = np.linalg.norm(B @ v)
    delta = hazard.center - robot.center
    h = (delta @ v - support - 1.) / denominator
    grad_v = (delta - B @ B @ v / support) / denominator - h * v / denominator**2
    translation = -v / denominator
    angular = grad_v @ (C @ skew(z) - skew(v))
    grad_z = grad_v @ C
    tangent = grad_z @ (np.eye(3) - np.outer(z, z))
    return float(h), np.concatenate((translation, angular)), tangent, grad_z, -translation


def _initial_plane(robot, hazard):
    """Find a support-plane certificate; failure does not assert collision."""
    A = robot.rotation @ np.diag(robot.semi_axes) @ robot.rotation.T
    B = hazard.rotation @ np.diag(hazard.semi_axes) @ hazard.rotation.T
    delta = hazard.center - robot.center
    if np.linalg.norm(delta) < 1e-12:
        return None
    normal = delta / np.linalg.norm(delta)

    def objective(direction):
        norm = np.linalg.norm(direction)
        if norm < 1e-12 or not np.isfinite(norm):
            return 1e6, np.zeros(3)
        n = direction / norm
        an, bn = A @ n, B @ n
        la, lb = np.linalg.norm(an), np.linalg.norm(bn)
        gap = delta @ n - la - lb
        derivative = delta - A @ an / la - B @ bn / lb
        return -float(gap), -((np.eye(3) - np.outer(n, n)) @ derivative) / norm

    fit = minimize(objective, normal, jac=True, method="BFGS",
                   options={"maxiter": 64, "gtol": 1e-9})
    # The certificate itself is checked below; optimizer status is not proof.
    candidate = np.asarray(fit.x)
    if np.isfinite(candidate).all() and np.linalg.norm(candidate) > 1e-12 and objective(candidate)[0] < objective(normal)[0]:
        normal = candidate / np.linalg.norm(candidate)
    z = A @ normal
    return z / np.linalg.norm(z)


class SafetyFilter:
    """Persistent OSQP instance; callers reject stale/invalid perception first."""

    def __init__(self, guard_count=5, dt=.02, max_joint_velocity=.3,
                 margin_m=.003, alpha=10., max_plane_rate=5.,
                 residual_tolerance=2e-5, plane_reference="zero", barrier_buffer_m=0.):
        velocity = np.broadcast_to(np.asarray(max_joint_velocity, dtype=float), (5,)).copy()
        if not isinstance(guard_count, int) or guard_count <= 0:
            raise ValueError("guard_count must be a positive integer")
        if not np.isfinite([dt, margin_m, alpha, max_plane_rate, residual_tolerance, barrier_buffer_m]).all() or dt <= 0 or margin_m < 0 or alpha <= 0 or max_plane_rate <= 0 or residual_tolerance <= 0 or barrier_buffer_m < 0:
            raise ValueError("invalid filter configuration")
        if not np.isfinite(velocity).all() or np.any(velocity <= 0):
            raise ValueError("max_joint_velocity must be positive")
        if plane_reference not in ("zero", "gradient"):
            raise ValueError("plane_reference must be zero or gradient")
        self.guard_count, self.dt = guard_count, float(dt)
        self.velocity_limit, self.margin_m, self.alpha = velocity, float(margin_m), float(alpha)
        self.max_plane_rate, self.residual_tolerance = float(max_plane_rate), float(residual_tolerance)
        self.barrier_buffer_m = float(barrier_buffer_m)
        self.plane_reference = plane_reference
        self._z = None
        self._solver = None
        self._pattern = None
        self._last_solution = None

    def reset(self):
        self._z = None
        self._last_solution = None
        if self._solver is not None:
            self._solver.warm_start(x=np.zeros(5 + 3 * self.guard_count),
                                    y=np.zeros(self.guard_count + 5 + 3 * self.guard_count))

    def _solve(self, rows, lower, upper, nominal):
        count = 5 + 3 * self.guard_count
        # Full barrier-row pattern is kept even for structural zeros, allowing
        # every subsequent Jacobian to update without rebuilding the solver.
        if self._pattern is None:
            matrix = sparse.csc_matrix(np.vstack((np.ones((self.guard_count, count)), np.eye(count))))
            self._pattern = (matrix.indices.copy(), matrix.indptr.copy(), matrix.shape)
        indices, indptr, shape = self._pattern
        full = np.vstack((rows, np.eye(count)))
        values = np.concatenate([full[indices[indptr[j]:indptr[j + 1]], j]
                                 for j in range(count)])
        weight = np.r_[np.full(5, .04), np.ones(3 * self.guard_count)]
        linear = -2. * weight * nominal
        if self._solver is None:
            matrix = sparse.csc_matrix((values, indices, indptr), shape=shape)
            self._solver = osqp.OSQP()
            self._solver.setup(P=sparse.diags(2. * weight, format="csc"), q=linear,
                               A=matrix, l=lower, u=upper, verbose=False,
                               eps_abs=1e-6, eps_rel=1e-6, max_iter=1000,
                               time_limit=.01, polishing=False, warm_starting=True,
                               adaptive_rho=True)
        else:
            self._solver.update(q=linear, Ax=values, l=lower, u=upper)
        if self._last_solution is not None:
            self._solver.warm_start(x=self._last_solution)
        return self._solver.solve(raise_error=False), full

    def filter(self, qactual, nominaltarget, robot_worldellips, hazard,
               joint_bounds, hazard_velocity=None):
        started = time.perf_counter()
        metrics = {"reason": None, "hvalues": [], "qp_residual": None,
                   "source_metadata": dict(SOURCE_METADATA),
                   "plane_reference": self.plane_reference,
                   "hard_margin_m": self.margin_m, "barrier_buffer_m": self.barrier_buffer_m,
                   "qp_margin_m": self.margin_m + self.barrier_buffer_m,
                   "nominal_velocity": None, "output_velocity": None,
                   "recertified_guards": [], "recertification_ms": 0.,
                   "hvalues_before_recertification": []}

        def stop(reason):
            metrics["reason"] = reason
            metrics["latency_ms"] = (time.perf_counter() - started) * 1000.
            self._last_solution = None
            return FilterResult("stopped", None, metrics)

        try:
            q = np.asarray(qactual, dtype=float)
            target = np.asarray(nominaltarget, dtype=float)
            bounds = np.asarray(joint_bounds, dtype=float)
            velocity = np.zeros(3) if hazard_velocity is None else np.asarray(hazard_velocity, dtype=float)
            if q.shape != (6,) or target.shape != (6,) or bounds.shape != (6, 2) or velocity.shape != (3,):
                return stop("invalid_dimensions")
            if not all(np.isfinite(x).all() for x in (q, target, bounds, velocity)) or np.any(bounds[:, 0] >= bounds[:, 1]):
                return stop("invalid_nonfinite_or_bounds")
            if np.any(q < bounds[:, 0] - 1e-9) or np.any(q > bounds[:, 1] + 1e-9):
                return stop("actual_joint_limit")
            if target[5] < bounds[5, 0] or target[5] > bounds[5, 1]:
                return stop("gripper_target_limit")
            if len(robot_worldellips) != self.guard_count:
                return stop("guard_count_mismatch")
            robots = [_ellipsoid(x) for x in robot_worldellips]
            obstacle = _ellipsoid(hazard)
            jacobians = [np.asarray(_field(x, "jacobian"), dtype=float) for x in robot_worldellips]
            if any(x.shape not in ((6, 5), (6, 6)) or not np.isfinite(x).all() for x in jacobians):
                return stop("invalid_jacobian")
            if self._z is None:
                planes = [_initial_plane(x, obstacle) for x in robots]
                if any(x is None for x in planes):
                    return stop("no_initial_plane_certificate")
                self._z = np.array(planes)
            count = 5 + 3 * self.guard_count
            rows = np.zeros((self.guard_count, count))
            barrier_lower = []
            nominal = np.r_[(target[:5] - q[:5]) / self.dt, np.zeros(3 * self.guard_count)]
            metrics["nominal_velocity"] = nominal[:5].tolist()
            for k, (robot, jac, z) in enumerate(zip(robots, jacobians, self._z)):
                h, pose_row, z_row, raw_z, obstacle_row = barrier_terms(robot, obstacle, z)
                metrics["hvalues_before_recertification"].append(h)
                if h < self.margin_m - 1e-9:
                    # An old plane can become conservative after an estimated
                    # hazard-pose update. A newly verified separator authorizes
                    # the current geometry, never a negative barrier value.
                    recertification_started = time.perf_counter()
                    new_z = _initial_plane(robot, obstacle)
                    if new_z is not None:
                        new_terms = barrier_terms(robot, obstacle, new_z)
                    else:
                        new_terms = None
                    metrics["recertification_ms"] += (time.perf_counter() - recertification_started) * 1000.
                    if new_terms is None or new_terms[0] < self.margin_m - 1e-9:
                        metrics["hvalues"].append(h if new_terms is None else new_terms[0])
                        return stop("plane_certificate_below_margin")
                    z = new_z
                    self._z[k] = new_z
                    h, pose_row, z_row, raw_z, obstacle_row = new_terms
                    metrics["recertified_guards"].append(k)
                metrics["hvalues"].append(h)
                rows[k, :5] = pose_row @ jac[:, :5]
                rows[k, 5 + 3 * k:8 + 3 * k] = z_row
                # The stricter QP threshold anticipates servo/sample errors.
                # It never relaxes the independently checked hard certificate.
                barrier_lower.append(-self.alpha * (h - self.margin_m - self.barrier_buffer_m) - obstacle_row @ velocity)
                if self.plane_reference == "gradient":
                    nominal[5 + 3 * k:8 + 3 * k] = np.clip(10. * raw_z, -self.max_plane_rate, self.max_plane_rate)
            lo_vel = np.maximum(-self.velocity_limit, (bounds[:5, 0] - q[:5]) / self.dt)
            hi_vel = np.minimum(self.velocity_limit, (bounds[:5, 1] - q[:5]) / self.dt)
            lower = np.r_[barrier_lower, lo_vel, np.full(3 * self.guard_count, -self.max_plane_rate)]
            upper = np.r_[np.full(self.guard_count, np.inf), hi_vel, np.full(3 * self.guard_count, self.max_plane_rate)]
            result, full = self._solve(rows, lower, upper, nominal)
            metrics["solver_status"] = result.info.status
            metrics["solver_iterations"] = int(result.info.iter)
            if result.info.status_val != 1 or result.x is None or not np.isfinite(result.x).all():
                return stop("solver_not_solved")
            solution = np.asarray(result.x)
            calculated = full @ solution
            violation = float(max(0., np.max(lower - calculated), np.max(calculated - upper)))
            metrics["qp_residual"] = violation
            metrics["barrier_residuals"] = (rows @ solution - np.asarray(barrier_lower)).tolist()
            if violation > self.residual_tolerance:
                return stop("qp_residual_violation")
            action = q.copy()
            action[:5] += self.dt * solution[:5]
            action[5] = target[5]
            if not np.isfinite(action).all() or np.any(action < bounds[:, 0] - 1e-8) or np.any(action > bounds[:, 1] + 1e-8):
                return stop("output_joint_limit")
            updated = []
            for k, z in enumerate(self._z):
                dz = (np.eye(3) - np.outer(z, z)) @ solution[5 + 3 * k:8 + 3 * k]
                new = z + self.dt * dz
                if not np.isfinite(new).all() or np.linalg.norm(new) < 1e-12:
                    return stop("invalid_plane_update")
                updated.append(new / np.linalg.norm(new))
            self._z = np.array(updated)
            self._last_solution = solution.copy()
            metrics["output_velocity"] = solution[:5].tolist()
            metrics["auxiliary_velocity"] = solution[5:].reshape(self.guard_count, 3).tolist()
            status = "accepted" if np.max(np.abs(action - target)) <= 1e-7 else "modified"
            metrics["reason"] = "nominal_certified" if status == "accepted" else "cbf_or_limit_correction"
            metrics["latency_ms"] = (time.perf_counter() - started) * 1000.
            return FilterResult(status, action, metrics)
        except Exception as error:
            metrics["error_type"] = type(error).__name__
            return stop("filter_error")
