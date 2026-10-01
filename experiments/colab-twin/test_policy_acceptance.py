"""Evaluation boundary tests; physical grasp/place evidence is a separate gate."""
import unittest

import numpy as np

from evaluate_state_policy import (EvaluationLimits, can_inject_perturbation,
                                   run_attempt, summarize_attempts)
from learning_data import POLICY_OBSERVATION_KEYS


class Policy:
    metadata = {"control_period_s": .02}

    def __init__(self, action=None):
        self.action = np.full(6, .3) if action is None else action
        self.inputs = []
        self.resets = 0

    def reset(self):
        self.resets += 1

    def predict(self, observation):
        self.inputs.append(observation)
        return self.action.copy()


class Checker:
    def __init__(self, valid=True):
        self.valid = valid
        self.queries = []

    def evaluate(self, action, require_fixed_gripper):
        self.queries.append((action.copy(), require_fixed_gripper))
        return {"valid": self.valid}


class SafetyStop(Exception):
    pass


class Environment:
    baseline_z = .01

    def __init__(self, *, contact=False, valid=True, exception=None):
        self.contact = contact
        self.checker = Checker(valid)
        self.exception = exception
        self.actions = []
        self.steps = 0

    def observation(self):
        return {"observation.state": np.full(6, self.steps * .001),
                "observation.environment_state": np.zeros(30),
                "time_s": 1 + self.steps * .02,
                "stage": "expert_stage_must_be_ignored", "reference_waypoint": 17}

    def reset(self):
        self.steps = 0
        return self.observation()

    def step(self, action):
        if self.exception:
            raise self.exception
        self.actions.append(action.copy())
        self.steps += 1
        diagnostic = {"finite_state": True, "arm_valid": True, "obstacle_contact": False,
                      "tip_forces_n": [.2, .2] if self.contact else [0, 0],
                      "object_z_m": self.baseline_z, "time_s": 1 + self.steps * .02}
        return self.observation(), diagnostic


class Monitor:
    def __init__(self, pass_at=100, failure_at=None, safety=False):
        self.pass_at = pass_at
        self.failure_at = failure_at
        self.safety = safety
        self.updates = 0

    def update(self, diagnostic):
        self.updates += 1
        return self.report()

    def report(self):
        failure = self.failure_at is not None and self.updates >= self.failure_at
        return {"passed": self.updates >= self.pass_at,
                "failure_reason": "payload_lost" if failure else None,
                "safety_stop": bool(failure and self.safety)}


class PolicyAcceptanceTests(unittest.TestCase):
    def limits(self, **overrides):
        return EvaluationLimits(**{"max_simulation_s": 1, "max_wall_s": 5,
                                   "perturb_at_s": .02, "perturb_duration_s": .2,
                                   "perturb_rad": .02, **overrides})

    def test_nominal_uses_only_policy_inputs_and_no_checker_generated_action(self):
        env, policy = Environment(), Policy()
        result, transitions = run_attempt(env, policy, Monitor(pass_at=5), seed=3,
                                          perturbed=False, limits=self.limits())
        self.assertTrue(result["passed"])
        self.assertEqual(len(transitions), 5)
        self.assertEqual(policy.resets, 1)
        self.assertTrue(all(set(obs) == set(POLICY_OBSERVATION_KEYS) for obs in policy.inputs))
        self.assertEqual(env.checker.queries, [])
        np.testing.assert_allclose(env.actions, np.full((5, 6), .3))

    def test_real_control_perturbation_is_bounded_and_recovery_is_pure_policy(self):
        env, policy = Environment(), Policy()
        result, transitions = run_attempt(env, policy, Monitor(pass_at=16), seed=3,
                                          perturbed=True, limits=self.limits())
        self.assertTrue(result["passed"])
        self.assertTrue(result["perturbation_fully_injected"])
        self.assertEqual(result["perturbation_control_ticks"], 10)
        injected = [row for row in transitions if row["perturbation"]]
        self.assertEqual(len(injected), 10)
        offset = np.array(result["perturbation_offset_rad"])
        self.assertTrue(np.all(np.abs(offset) <= .02))
        self.assertEqual(offset[-1], 0)
        np.testing.assert_allclose(injected[0]["action"], policy.action + offset)
        np.testing.assert_allclose(env.actions[-1], policy.action)
        self.assertTrue(all(not fixed for _, fixed in env.checker.queries))

    def test_contact_blocks_injection_and_never_counts_as_recovery_success(self):
        result, _ = run_attempt(Environment(contact=True), Policy(), Monitor(pass_at=15), seed=3,
                                perturbed=True, limits=self.limits())
        self.assertFalse(result["passed"])
        self.assertFalse(result["perturbation_injected"])
        self.assertEqual(result["failure_reason"], "perturbation_not_fully_injected")

    def test_partial_perturbation_cannot_count_as_success(self):
        result, _ = run_attempt(Environment(), Policy(), Monitor(pass_at=4), seed=3,
                                perturbed=True, limits=self.limits())
        self.assertFalse(result["passed"])
        self.assertTrue(result["perturbation_injected"])
        self.assertFalse(result["perturbation_fully_injected"])
        self.assertEqual(summarize_attempts([result])["perturbed"]["fully_injected_attempt_count"], 0)

    def test_safety_precheck_stops_before_unsafe_command_without_fallback(self):
        env = Environment(valid=False)
        result, _ = run_attempt(env, Policy(), Monitor(pass_at=100), seed=3,
                                perturbed=True, limits=self.limits())
        self.assertFalse(result["passed"])
        self.assertTrue(result["safety_stop"])
        self.assertEqual(result["failure_reason"], "perturbation_safety_precheck")
        self.assertEqual(len(env.actions), 1)

    def test_environment_safety_stop_preserves_failed_attempt(self):
        result, transitions = run_attempt(Environment(exception=SafetyStop("joint limit")), Policy(),
                                         Monitor(pass_at=1), seed=3, perturbed=False, limits=self.limits())
        self.assertFalse(result["passed"])
        self.assertTrue(result["safety_stop"])
        self.assertEqual(result["failure_reason"], "safety_stop")
        self.assertEqual(transitions, [])

    def test_physical_failure_is_terminal_even_when_monitor_also_flags_passed(self):
        result, _ = run_attempt(Environment(), Policy(), Monitor(pass_at=2, failure_at=2), seed=3,
                                perturbed=False, limits=self.limits())
        self.assertFalse(result["passed"])
        self.assertEqual(result["failure_reason"], "payload_lost")

    def test_invalid_policy_action_is_safety_failure(self):
        env = Environment()
        result, _ = run_attempt(env, Policy(np.full(6, np.nan)), Monitor(pass_at=1), seed=3,
                                perturbed=False, limits=self.limits())
        self.assertFalse(result["passed"])
        self.assertTrue(result["safety_stop"])
        self.assertEqual(result["failure_reason"], "invalid_policy_action")
        self.assertEqual(env.actions, [])

    def test_simulation_and_wall_budgets_terminate_without_declaring_success(self):
        result, transitions = run_attempt(Environment(), Policy(), Monitor(pass_at=100), seed=3,
                                         perturbed=False, limits=self.limits(max_simulation_s=.06))
        self.assertEqual(result["failure_reason"], "simulation_time_limit")
        self.assertEqual(len(transitions), 3)
        readings = iter([0., 6., 6.])
        result, transitions = run_attempt(Environment(), Policy(), Monitor(pass_at=1), seed=3,
                                         perturbed=False, limits=self.limits(), clock=lambda: next(readings))
        self.assertEqual(result["failure_reason"], "wall_time_limit")
        self.assertFalse(result["passed"])
        self.assertEqual(transitions, [])

    def test_attempt_denominators_include_stops_timeouts_and_uninjected_trials(self):
        attempts = [{"passed": True, "perturbed": False},
                    {"passed": False, "perturbed": False, "safety_stop": True},
                    {"passed": False, "perturbed": True, "failure_reason": "simulation_time_limit"},
                    {"passed": True, "perturbed": True, "perturbation_injected": True,
                     "perturbation_fully_injected": True}]
        summary = summarize_attempts(attempts)
        self.assertEqual(summary["attempt_count"], 4)
        self.assertEqual(summary["failed_attempt_count"], 2)
        self.assertEqual(summary["safety_stop_count"], 1)
        self.assertEqual(summary["timeout_count"], 1)
        self.assertEqual(summary["nominal"]["success_rate"], .5)
        self.assertEqual(summary["perturbed"]["success_rate"], .5)

    def test_perturbation_window_rejects_nonfinite_contact_and_already_lifted_object(self):
        diagnostic = {"finite_state": True, "arm_valid": True, "obstacle_contact": False,
                      "tip_forces_n": [0, 0], "object_z_m": .01}
        self.assertTrue(can_inject_perturbation(diagnostic, .01))
        diagnostic["object_z_m"] = .02
        self.assertFalse(can_inject_perturbation(diagnostic, .01))
        diagnostic["object_z_m"] = .01
        diagnostic["tip_forces_n"] = [np.nan, 0]
        self.assertFalse(can_inject_perturbation(diagnostic, .01))

    def test_perturbation_fixture_limits_control_duration_and_amplitude(self):
        with self.assertRaisesRegex(ValueError, "integer control cycles"):
            self.limits(perturb_duration_s=.021).validate(.02)
        with self.assertRaisesRegex(ValueError, "five degrees"):
            self.limits(perturb_rad=.1).validate(.02)


class PhysicalMonitorTests(unittest.TestCase):
    def setUp(self):
        from learning_env import PhysicalTaskMonitor
        self.monitor = PhysicalTaskMonitor(.01)

    def diagnostic(self, time_s, *, held=True, **changes):
        return {"time_s": time_s, "object_z_m": .05 if held else .01,
                "tip_forces_n": [.2, .2] if held else [0, 0],
                "floor_contact": False, "place_floor_contact": not held,
                "in_place_tray": not held, "object_speed_m_s": 0.,
                "finite_state": True, "arm_valid": True, "obstacle_contact": False, **changes}

    def held_episode(self):
        for tick in range(52):
            self.monitor.update(self.diagnostic(tick * .02))
        self.assertTrue(self.monitor.report()["grasp_success"])

    def test_requires_actual_grasp_before_a_cube_at_rest_can_pass(self):
        for tick in range(60):
            self.monitor.update(self.diagnostic(tick * .02, held=False))
        self.assertFalse(self.monitor.report()["passed"])
        self.assertFalse(self.monitor.report()["grasp_success"])

    def test_sustained_two_finger_lift_then_released_supported_settle_passes(self):
        self.held_episode()
        self.assertFalse(self.monitor.report()["passed"])
        for tick in range(52, 105):
            self.monitor.update(self.diagnostic(tick * .02, held=False))
        self.assertTrue(self.monitor.report()["passed"])
        self.assertTrue(self.monitor.report()["place_success"])

    def test_blue_position_without_real_floor_support_is_not_a_place(self):
        self.held_episode()
        for tick in range(52, 105):
            self.monitor.update(self.diagnostic(tick * .02, held=False, place_floor_contact=False))
        self.assertFalse(self.monitor.report()["passed"])
        self.assertFalse(self.monitor.report()["place_success"])

    def test_one_finger_force_is_not_sustained_grasp(self):
        for tick in range(60):
            self.monitor.update(self.diagnostic(tick * .02, tip_forces_n=[.2, 0]))
        self.assertFalse(self.monitor.report()["grasp_success"])

    def test_dropped_payload_and_physical_collision_are_terminal_failures(self):
        self.held_episode()
        for tick in range(52, 59):
            self.monitor.update(self.diagnostic(tick * .02, tip_forces_n=[0, 0],
                                               object_speed_m_s=.1))
        self.assertEqual(self.monitor.report()["failure_reason"], "payload_lost")
        self.monitor.update(self.diagnostic(1.2, obstacle_contact=True))
        self.assertTrue(self.monitor.report()["safety_stop"])
        self.assertFalse(self.monitor.report()["passed"])


if __name__ == "__main__":
    unittest.main()
