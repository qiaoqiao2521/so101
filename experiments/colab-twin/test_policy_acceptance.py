"""Evaluation boundary tests; physical grasp/place evidence is a separate gate."""
import unittest
from unittest.mock import patch
import hashlib
from pathlib import Path
import tempfile

import numpy as np

from evaluate_state_policy import (EvaluationLimits, can_inject_perturbation,
                                   fit_gripper_projection, project_gripper,
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

    def projection_fixture(self, labels, *, mask=None, passed=True, eligible=True, mode="clip", wrong_hash=False):
        actions = np.zeros((len(labels), 6))
        actions[:, 5] = labels
        episode = {"action": actions, "label_valid": np.ones(len(labels), dtype=bool) if mask is None else np.array(mask),
                   "report": {"passed": passed}, "eligible_for_training": eligible}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "expert.h5"
            path.write_bytes(b"mocked audited episode")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            metadata = {"train_dataset_sha256": ["wrong" if wrong_hash else digest]}
            with patch("evaluate_state_policy.load_episode", return_value=episode):
                return fit_gripper_projection([path], metadata, mode)

    def test_gripper_bounds_fit_only_valid_positive_checkpoint_training_labels(self):
        config = self.projection_fixture([.015, np.nan, .5], mask=[True, False, True])
        self.assertEqual(config["minimum_rad"], .015)
        self.assertEqual(config["maximum_rad"], .5)
        self.assertEqual(config["valid_label_frame_count"], 2)
        with self.assertRaisesRegex(ValueError, "hashes"):
            self.projection_fixture([.015, .5], wrong_hash=True)
        for flags in ({"eligible": False}, {"passed": False}):
            with self.subTest(flags=flags), self.assertRaisesRegex(ValueError, "positive eligible"):
                self.projection_fixture([.015, .5], **flags)

    def test_gripper_interval_projection_changes_only_jaw_and_preserves_raw_action(self):
        raw = np.array([4., -4., .2, .3, .4, .8])
        original = raw.copy()
        projected, changed = project_gripper(raw, {"minimum_rad": .015, "maximum_rad": .5})
        self.assertTrue(changed)
        np.testing.assert_array_equal(projected[:5], original[:5])
        np.testing.assert_array_equal(raw, original)
        self.assertEqual(projected[5], .5)
        raw[5] = -.2
        self.assertEqual(project_gripper(raw, {"minimum_rad": .015, "maximum_rad": .5})[0][5], .015)
        for invalid in (np.full(6, np.nan), np.full(6, np.inf), np.zeros(5)):
            with self.assertRaises(ValueError):
                project_gripper(invalid, {"minimum_rad": .015, "maximum_rad": .5})

    def test_nearest_projection_uses_exact_two_training_labels_and_records_tie(self):
        config = self.projection_fixture([.015, .5, .015], mode="nearest")
        self.assertEqual(config["allowed_labels_rad"], [.015, .5])
        self.assertEqual(config["tie_rule"], "lower_label_at_exact_midpoint")
        raw = np.arange(6, dtype=float)
        raw[5] = config["midpoint_rad"]
        projected, _ = project_gripper(raw, config)
        self.assertEqual(projected[5], .015)
        np.testing.assert_array_equal(projected[:5], raw[:5])
        raw[5] = config["midpoint_rad"] + 1e-6
        self.assertEqual(project_gripper(raw, config)[0][5], .5)
        for labels in ([.5], [.015, .25, .5]):
            with self.subTest(labels=labels), self.assertRaisesRegex(ValueError, "exactly two"):
                self.projection_fixture(labels, mode="nearest")

    def test_clip_and_nearest_are_distinct_for_observed_early_closing_targets(self):
        clip = self.projection_fixture([.015, .5])
        nearest = self.projection_fixture([.015, .5], mode="nearest")
        targets = [.499759, .498278, .459505, .413686, .39474]
        for target in targets:
            raw = np.r_[np.arange(5), target]
            clipped, changed = project_gripper(raw, clip)
            binary, projected = project_gripper(raw, nearest)
            self.assertFalse(changed)
            self.assertTrue(projected)
            self.assertEqual(clipped[5], target)
            self.assertEqual(binary[5], .5)
            np.testing.assert_array_equal(binary[:5], raw[:5])

    def test_projection_attempt_keeps_raw_executed_commands_and_counts_stopped_tick(self):
        config = {"minimum_rad": .015, "maximum_rad": .5}
        policy = Policy(np.r_[np.full(5, .3), .7])
        result, transitions = run_attempt(Environment(), policy, Monitor(pass_at=3), seed=3,
                                          perturbed=False, limits=self.limits(), gripper_projection=config)
        self.assertTrue(result["passed"])
        self.assertEqual(result["action_audit"]["gripper_projection_count"], 3)
        self.assertEqual(result["action_audit"]["gripper_projection_rate"], 1.)
        self.assertTrue(all(row["projected"] for row in transitions))
        np.testing.assert_array_equal(transitions[0]["raw_action"], policy.action)
        self.assertEqual(transitions[0]["policy_action"][5], .5)
        self.assertEqual(transitions[0]["action"][5], .5)
        summary = summarize_attempts([result])
        self.assertEqual(summary["action_audit"]["finite_policy_command_count"], 3)
        self.assertEqual(summary["action_audit"]["raw_action_max_rad_per_joint"][5], .7)
        stopped, completed = run_attempt(Environment(exception=SafetyStop("joint limit")), policy,
                                         Monitor(pass_at=1), seed=3, perturbed=False,
                                         limits=self.limits(), gripper_projection=config)
        self.assertEqual(completed, [])
        self.assertFalse(stopped["passed"])
        self.assertEqual(stopped["last_command"]["raw_action"][5], .7)
        self.assertEqual(stopped["last_command"]["action"][5], .5)
        self.assertEqual(stopped["action_audit"]["finite_policy_command_count"], 1)

    def test_nonfinite_action_is_rejected_before_projection_and_never_reaches_physics(self):
        env = Environment()
        result, transitions = run_attempt(env, Policy(np.full(6, np.inf)), Monitor(pass_at=1), seed=3,
                                          perturbed=False, limits=self.limits(),
                                          gripper_projection={"minimum_rad": .015, "maximum_rad": .5})
        self.assertEqual(result["failure_reason"], "invalid_policy_action")
        self.assertTrue(result["safety_stop"])
        self.assertEqual(env.actions, [])
        self.assertEqual(transitions, [])
        self.assertEqual(result["action_audit"]["gripper_projection_count"], 0)


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
