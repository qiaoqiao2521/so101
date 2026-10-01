"""Analytic geometry and fail-closed acceptance tests, independent of VLA."""
import types
import unittest
from unittest.mock import patch

import numpy as np
from scipy.spatial.transform import Rotation

from cbf_filter import Ellipsoid, SafetyFilter, barrier_terms


def world_sphere(center=(0., 0., 0.), radius=.05, jaw_jacobian=False):
    jac = np.zeros((6, 6 if jaw_jacobian else 5))
    jac[0, 0] = 1.
    if jaw_jacobian:
        jac[0, 5] = 1000.
    return types.SimpleNamespace(center=np.array(center), rotation=np.eye(3),
                                 semi_axes=np.full(3, radius), jacobian=jac)


class BarrierTests(unittest.TestCase):
    def test_rotated_ellipsoids_world_central_derivatives(self):
        rng = np.random.default_rng(41)
        error = np.zeros(4)
        for _ in range(30):
            robot = Ellipsoid(rng.normal(size=3), Rotation.random(random_state=rng).as_matrix(), rng.uniform(.04, .3, 3))
            hazard = Ellipsoid(rng.normal(size=3), Rotation.random(random_state=rng).as_matrix(), rng.uniform(.04, .3, 3))
            z = rng.normal(size=3); z /= np.linalg.norm(z)
            h, pose, tangent, _, obstacle_row = barrier_terms(robot, hazard, z)
            eps = 1e-6
            def value(p=robot.center, r=robot.rotation, o=hazard.center, direction=z):
                return barrier_terms(Ellipsoid(p, r, robot.semi_axes),
                                     Ellipsoid(o, hazard.rotation, hazard.semi_axes), direction)[0]
            translation = np.array([(value(p=robot.center+b*eps)-value(p=robot.center-b*eps))/(2*eps) for b in np.eye(3)])
            angular = np.array([(value(r=Rotation.from_rotvec(b*eps).as_matrix()@robot.rotation)-value(r=Rotation.from_rotvec(-b*eps).as_matrix()@robot.rotation))/(2*eps) for b in np.eye(3)])
            direction = np.array([(value(direction=z+b*eps)-value(direction=z-b*eps))/(2*eps) for b in np.eye(3)])
            obstacle = np.array([(value(o=hazard.center+b*eps)-value(o=hazard.center-b*eps))/(2*eps) for b in np.eye(3)])
            error = np.maximum(error, [np.max(abs(translation-pose[:3])), np.max(abs(angular-pose[3:])), np.max(abs(direction-tangent)), np.max(abs(obstacle-obstacle_row))])
            self.assertTrue(np.isfinite(h))
        self.assertLess(error.max(), 1e-7, str(error))

    def test_sphere_gap_and_sign(self):
        robot = world_sphere()
        obstacle = Ellipsoid(np.array([.106, 0., 0.]), np.eye(3), np.full(3, .05))
        h, pose, tangent, _, other = barrier_terms(robot, obstacle, [1., 0., 0.])
        self.assertAlmostEqual(h, .006)
        np.testing.assert_allclose(pose[:3], [-1., 0., 0.])
        np.testing.assert_allclose(other, [1., 0., 0.])
        np.testing.assert_allclose(tangent, 0., atol=1e-12)


class FilterTests(unittest.TestCase):
    def setUp(self):
        self.q = np.array([0., 0., 0., 0., 0., .2])
        self.bounds = np.array([[-1., 1.]]*5 + [[.015, .5]])
        self.robots = [world_sphere() for _ in range(5)]

    def hazard(self, x=1.):
        return {"center": [x, 0., 0.], "rotation": np.eye(3), "semi_axes": [.05]*3}

    def test_far_nominal_pass_and_persistent_solver(self):
        shield = SafetyFilter()
        target = self.q.copy(); target[0] += .0004; target[5] = .3
        first = shield.filter(self.q, target, self.robots, self.hazard(), self.bounds)
        self.assertEqual(first.status, "accepted", first.metrics)
        np.testing.assert_allclose(first.action, target, atol=1e-7)
        solver = shield._solver
        second = shield.filter(self.q, target, self.robots, self.hazard(), self.bounds)
        self.assertIs(shield._solver, solver)
        self.assertEqual(second.status, "accepted", second.metrics)
        self.assertEqual(len(second.metrics["hvalues"]), 5)
        self.assertLessEqual(second.metrics["qp_residual"], 2e-5)
        self.assertEqual(second.metrics["source_metadata"]["variant"], "local_joint_space_rotating_plane_cbf")

    def test_near_static_correction(self):
        target = self.q.copy(); target[0] += .004
        result = SafetyFilter().filter(self.q, target, self.robots, self.hazard(.106), self.bounds)
        self.assertEqual(result.status, "modified", result.metrics)
        self.assertLessEqual(result.metrics["output_velocity"][0], .03002)
        self.assertGreater(result.action[0], 0.)

    def test_sparse_pattern_allows_new_nonzero_joint_coefficients(self):
        shield = SafetyFilter()
        first = shield.filter(self.q, self.q, self.robots, self.hazard(.106), self.bounds)
        self.assertEqual(first.status, "accepted", first.metrics)
        solver = shield._solver
        for robot in self.robots:
            robot.jacobian[0, 0] = 0.
            robot.jacobian[0, 1] = 1.
        target = self.q.copy(); target[1] += .004
        second = shield.filter(self.q, target, self.robots, self.hazard(.106), self.bounds)
        self.assertIs(solver, shield._solver)
        self.assertEqual(second.status, "modified", second.metrics)
        self.assertLessEqual(second.metrics["output_velocity"][1], .03002)

    def test_all_five_distinct_rows_constrain_their_joint(self):
        robots = [world_sphere(center=(-.001*k, 0., 0.)) for k in range(5)]
        for k, robot in enumerate(robots):
            robot.jacobian[:] = 0.
            robot.jacobian[0, k] = 1.
        target = self.q.copy(); target[:5] += .004
        result = SafetyFilter().filter(self.q, target, robots, self.hazard(.106), self.bounds)
        self.assertEqual(result.status, "modified", result.metrics)
        np.testing.assert_allclose(result.metrics["output_velocity"], .03+.01*np.arange(5), atol=2e-5)
        self.assertEqual(len(result.metrics["barrier_residuals"]), 5)

    def test_velocity_and_position_bound_correction(self):
        target = self.q.copy(); target[0] = .8
        result = SafetyFilter().filter(self.q, target, self.robots, self.hazard(), self.bounds)
        self.assertEqual(result.status, "modified", result.metrics)
        self.assertLessEqual(abs(result.metrics["output_velocity"][0]), .30002)
        np.testing.assert_allclose(result.action[0], .006, atol=1e-6)
        self.q[0] = .999
        # Other direction is unconstrained by the distant hazard; a near hard
        # limit bounds the admissible target independently of velocity.
        target = self.q.copy(); target[0] = 2.
        result = SafetyFilter().filter(self.q, target, self.robots, self.hazard(2.), self.bounds)
        self.assertIn(result.status, ("modified", "stopped"), result.metrics)
        if result.action is not None:
            self.assertLessEqual(result.action[0], 1. + 1e-8)

    def test_moving_hazard_term_changes_direction(self):
        static = SafetyFilter().filter(self.q, self.q, self.robots, self.hazard(.106), self.bounds)
        moving = SafetyFilter().filter(self.q, self.q, self.robots, self.hazard(.106), self.bounds, [-.1, 0., 0.])
        self.assertEqual(static.status, "accepted", static.metrics)
        self.assertEqual(moving.status, "modified", moving.metrics)
        self.assertLessEqual(moving.metrics["output_velocity"][0], -.06998)

    def test_buffer_promotes_retreat_inside_soft_but_outside_hard_margin(self):
        result = SafetyFilter(barrier_buffer_m=.006).filter(
            self.q, self.q, self.robots, self.hazard(.106), self.bounds)
        # h=.006 > hard=.003, but below soft=.009: require h_dot>=.03.
        self.assertEqual(result.status, "modified", result.metrics)
        self.assertLessEqual(result.metrics["output_velocity"][0], -.02998)
        self.assertAlmostEqual(result.metrics["hard_margin_m"], .003)
        self.assertAlmostEqual(result.metrics["qp_margin_m"], .009)
        self.assertTrue(all(h >= .003 for h in result.metrics["hvalues"]))

    def test_buffer_does_not_relax_hard_certificate(self):
        for center in (.099, .102):
            result = SafetyFilter(barrier_buffer_m=.006).filter(
                self.q, self.q, self.robots, self.hazard(center), self.bounds)
            self.assertEqual(result.status, "stopped", result.metrics)
            self.assertEqual(result.metrics["reason"], "plane_certificate_below_margin")
            self.assertIsNone(result.action)

    def test_infeasible_motion_stops_without_nominal(self):
        result = SafetyFilter().filter(self.q, self.q, self.robots, self.hazard(.106), self.bounds, [-1., 0., 0.])
        self.assertEqual(result.status, "stopped", result.metrics)
        self.assertIsNone(result.action)
        self.assertEqual(result.metrics["reason"], "solver_not_solved")

    def test_initial_no_certificate_and_reset(self):
        shield = SafetyFilter()
        result = shield.filter(self.q, self.q, self.robots, self.hazard(.102), self.bounds)
        self.assertEqual(result.status, "stopped")
        self.assertEqual(result.metrics["reason"], "plane_certificate_below_margin")
        shield.reset()
        self.assertIsNone(shield._z)
        result = shield.filter(self.q, self.q, self.robots, self.hazard(), self.bounds)
        self.assertEqual(result.status, "accepted", result.metrics)
        shield.reset()
        self.assertIsNone(shield._last_solution)

    def test_outdated_plane_can_recertify_separated_current_geometry(self):
        shield = SafetyFilter()
        first = shield.filter(self.q, self.q, self.robots, self.hazard(), self.bounds)
        self.assertEqual(first.status, "accepted", first.metrics)
        moved = self.hazard()
        moved["center"] = [0., 1., 0.]
        # The old x-normal plane has h=-.1, yet the y-normal plane certifies
        # the same two current ellipsoids with h=.9. Neither body is moved.
        second = shield.filter(self.q, self.q, self.robots, moved, self.bounds)
        self.assertEqual(second.status, "accepted", second.metrics)
        self.assertEqual(second.metrics["recertified_guards"], list(range(5)))
        self.assertGreater(second.metrics["recertification_ms"], 0.)
        self.assertTrue(all(h < 0 for h in second.metrics["hvalues_before_recertification"]))
        self.assertTrue(all(h >= shield.margin_m for h in second.metrics["hvalues"]))
        np.testing.assert_allclose(second.action, self.q, atol=1e-7)

    def test_recertification_cannot_allow_overlapping_volumes(self):
        shield = SafetyFilter()
        self.assertEqual(shield.filter(self.q, self.q, self.robots, self.hazard(), self.bounds).status, "accepted")
        result = shield.filter(self.q, self.q, self.robots, self.hazard(.099), self.bounds)
        self.assertEqual(result.status, "stopped", result.metrics)
        self.assertEqual(result.metrics["reason"], "plane_certificate_below_margin")
        self.assertIsNone(result.action)
        self.assertEqual(result.metrics["recertified_guards"], [])

    def test_gripper_is_excluded_from_qp_but_hard_checked(self):
        robots = [world_sphere(jaw_jacobian=True) for _ in range(5)]
        target = self.q.copy(); target[5] = .5
        result = SafetyFilter().filter(self.q, target, robots, self.hazard(.106), self.bounds)
        self.assertEqual(result.status, "accepted", result.metrics)
        self.assertEqual(result.action[5], .5)
        target[5] = .501
        result = SafetyFilter().filter(self.q, target, robots, self.hazard(), self.bounds)
        self.assertEqual(result.metrics["reason"], "gripper_target_limit")
        self.assertIsNone(result.action)

    def test_invalid_geometry_state_jacobian_and_count(self):
        for case in ("state", "geometry", "jacobian", "count"):
            q, robots, hazard = self.q.copy(), self.robots.copy(), self.hazard()
            if case == "state": q[0] = np.nan
            if case == "geometry": hazard["semi_axes"] = [-1., .1, .1]
            if case == "jacobian": robots = [world_sphere() for _ in range(5)]; robots[0].jacobian[0, 0] = np.nan
            if case == "count": robots.pop()
            result = SafetyFilter().filter(q, self.q, robots, hazard, self.bounds)
            self.assertEqual(result.status, "stopped", case)
            self.assertIsNone(result.action, case)

    def test_bad_solver_status_exception_and_residual_stop(self):
        fake = types.SimpleNamespace(info=types.SimpleNamespace(status="solved inaccurate", status_val=2, iter=1), x=np.zeros(20))
        with patch.object(SafetyFilter, "_solve", return_value=(fake, np.zeros((25, 20)))):
            result = SafetyFilter().filter(self.q, self.q, self.robots, self.hazard(), self.bounds)
        self.assertEqual(result.metrics["reason"], "solver_not_solved")
        with patch.object(SafetyFilter, "_solve", side_effect=RuntimeError("injected solver failure")):
            result = SafetyFilter().filter(self.q, self.q, self.robots, self.hazard(), self.bounds)
        self.assertEqual(result.status, "stopped")
        self.assertIsNone(result.action)
        fake.info.status = "solved"; fake.info.status_val = 1; fake.x[0] = 100.
        with patch.object(SafetyFilter, "_solve", return_value=(fake, np.vstack((np.zeros((5, 20)), np.eye(20))))):
            result = SafetyFilter().filter(self.q, self.q, self.robots, self.hazard(), self.bounds)
        self.assertEqual(result.metrics["reason"], "qp_residual_violation")
        self.assertIsNone(result.action)

    def test_invalid_configuration(self):
        for options in ({"dt": 0}, {"max_joint_velocity": 0}, {"margin_m": -1}, {"alpha": np.nan}, {"guard_count": 0}, {"barrier_buffer_m": -.001}, {"barrier_buffer_m": np.nan}):
            with self.assertRaises(ValueError): SafetyFilter(**options)


if __name__ == "__main__":
    unittest.main()
