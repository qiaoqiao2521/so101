"""Counterexamples for physical policy error and coverage audit metrics."""
import unittest
import json
from pathlib import Path
import tempfile

import numpy as np

from diagnose_state_policy import (action_error_summary, arm_tracking_summary,
                                   contradictory_neighbors, coverage_summary,
                                   _predict_absolute, saved_action_consistency,
                                   _execution_adapter)


class StateDiagnosticTests(unittest.TestCase):
    def test_global_mean_does_not_hide_a_gripper_boundary_failure(self):
        target = np.zeros((100, 6))
        prediction = target.copy()
        prediction[20, 5] = .485
        result = action_error_summary(prediction, target)
        self.assertLess(result["mae_rad"], .001)
        self.assertEqual(result["max_abs_rad_per_joint"][5], .485)
        self.assertEqual(result["max_abs_rad_per_joint"][0], 0)

    def test_near_identical_observations_with_opposite_gripper_labels_are_reported(self):
        observation = np.array([[0., 0.], [1e-6, 0.], [1., 1.]])
        action = np.zeros((3, 6))
        action[0, 5] = .5
        action[1:, 5] = .015
        result = contradictory_neighbors(observation, action, [1285, 1286, 1400],
                                         ["descend", "close", "close"])
        pair = result["returned_pairs"][0]
        self.assertEqual({pair["frame_a"], pair["frame_b"]}, {1285, 1286})
        self.assertAlmostEqual(pair["max_action_difference_rad"], .485)
        self.assertEqual(result["candidate_pairs_found"], 1)

    def test_stage_change_without_target_conflict_is_not_a_false_alias(self):
        result = contradictory_neighbors(np.zeros((2, 3)), np.zeros((2, 6)),
                                         [0, 1], ["approach", "descend"])
        self.assertEqual(result["returned_pairs"], [])

    def test_online_velocity_shift_is_reported_even_when_positions_match(self):
        # Joint position can be covered while velocity is far outside training.
        training = np.array([[0., -.01], [0., .01]])
        online = np.array([[0., 1.0], [0., 0.]])
        scale = np.array([1., .01])
        result = coverage_summary(training / scale, online / scale, training, online,
                                  feature_names=["joint.position", "joint.velocity"])
        self.assertEqual(result["outside_training_range_frame_count"], 1)
        self.assertEqual(result["detail"][0]["outside_training_range_features"], ["joint.velocity"])
        self.assertEqual(result["detail"][0]["normalized_nearest_l2"], 99)
        self.assertEqual(result["detail"][1]["outside_training_range_features"], [])

    def test_float32_constant_serialization_noise_is_not_distribution_shift(self):
        training = np.array([[.24], [.24]])
        online = np.array([[np.float32(.24)]])
        result = coverage_summary(training, online, training, online, feature_names=["object.x"])
        self.assertEqual(result["outside_training_range_frame_count"], 0)

    def test_tracking_offsets_remain_distinct_from_absolute_joint_coordinates(self):
        state = np.full((3, 6), 1.5)
        action = state + np.array([.001, -.002, .003, 0, 0, .485])
        result = arm_tracking_summary(state, action)
        self.assertAlmostEqual(result["max_abs_rad"][0], .001)
        self.assertAlmostEqual(result["max_abs_rad"][5], .485)

    def test_nonfinite_inputs_are_rejected_instead_of_reported_as_small_error(self):
        with self.assertRaises(ValueError):
            action_error_summary(np.full((1, 6), np.nan), np.zeros((1, 6)))
        with self.assertRaises(ValueError):
            contradictory_neighbors(np.array([[np.nan]]), np.zeros((1, 6)), [0], ["approach"])

    def test_batch_prediction_decodes_residual_against_current_state_not_training_mean(self):
        import torch
        from types import SimpleNamespace
        from learning_models import StateNormalizer, STATE, ENV_STATE, ACTION

        stats = {STATE: {"mean": [0.] * 6, "std": [1.] * 6},
                 ENV_STATE: {"mean": [0.] * 30, "std": [1.] * 30},
                 ACTION: {"mean": [.01] * 5 + [.5], "std": [1.] * 6}}

        class Policy:
            def predict_action_chunk(self, batch):
                # Only chunk index zero should become the current command.
                output = torch.zeros((len(batch[STATE]), 2, 6))
                output[:, 1] = 1000
                return output

        runner = SimpleNamespace(policy=Policy(),
                                 normalizer=StateNormalizer(stats, "arm_delta"),
                                 metadata={"model_spec": {"action_encoding": "arm_delta"}})
        rows = {STATE: np.array([[1.] * 6, [2.] * 6]), ENV_STATE: np.zeros((2, 30))}
        result = _predict_absolute(runner, rows, lambda: None)
        np.testing.assert_allclose(result[0], [1.01] * 5 + [.5])
        np.testing.assert_allclose(result[1], [2.01] * 5 + [.5])

    def test_projected_and_perturbed_actions_do_not_change_model_consistency(self):
        raw = np.full((2, 6), .02)
        policy = raw.copy()
        policy[:, 5] = .015
        action = policy.copy()
        action[1, 0] += .02
        saved = {'raw_action': raw, 'policy_action': policy, 'action': action,
                 'projected': np.ones(2, dtype=bool), 'perturbation': np.array([False, True])}
        result = saved_action_consistency(raw, saved)
        self.assertEqual(result['target_source'], 'raw_action')
        self.assertEqual(result['consistency_status'], 'matches')
        self.assertEqual(result['physical_difference']['frames'], 2)
        self.assertEqual(result['excluded_perturbed_ticks'], 0)
        self.assertEqual(result['projection_audit']['raw_to_policy_changed_frame_count'], 2)
        self.assertEqual(result['projection_audit']['projection_flag_disagreement_frame_count'], 0)
        self.assertEqual(result['executed_vs_policy_unperturbed_difference']['mae_rad'], 0)

    def test_legacy_log_ignores_injected_action_offsets(self):
        fresh = np.zeros((2, 6))
        action = fresh.copy()
        action[1] = 100
        result = saved_action_consistency(fresh, {'action': action, 'perturbation': np.array([False, True])})
        self.assertEqual(result['target_source'], 'action')
        self.assertEqual(result['physical_difference']['frames'], 1)
        self.assertEqual(result['excluded_perturbed_ticks'], 1)
        self.assertEqual(result['consistency_status'], 'matches')

    def test_chunk_cache_difference_is_not_an_equivalence_failure(self):
        result = saved_action_consistency(np.zeros((3, 6)),
                                          {'raw_action': np.ones((3, 6)), 'action': np.ones((3, 6))},
                                          execute_chunk_steps=16)
        self.assertEqual(result['frames_exceeding_tolerance'], 3)
        self.assertFalse(result['equivalence_check'])
        self.assertEqual(result['consistency_status'], 'not_equivalence_check')
        self.assertEqual(result['scope'], 'fresh_inference_vs_cached_chunk_not_equivalence_check')

    def test_legacy_projected_action_is_not_equivalent_to_raw_output(self):
        result = saved_action_consistency(np.zeros((1, 6)), {'action': np.ones((1, 6))},
                                          gripper_projection={'mode': 'nearest'})
        self.assertFalse(result['equivalence_check'])
        self.assertEqual(result['consistency_status'], 'not_equivalence_check')
        disabled = saved_action_consistency(np.zeros((1, 6)), {'action': np.zeros((1, 6))},
                                           gripper_projection={'enabled': False})
        self.assertTrue(disabled['equivalence_check'])
        self.assertEqual(disabled['consistency_status'], 'matches')

    def test_attempt_execution_config_precedes_root_adapter_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            attempt = root / 'attempt-000-nominal'
            attempt.mkdir()
            (root / 'report.json').write_text(json.dumps({'adapter_config': {
                'execute_chunk_steps': 1, 'gripper_projection': {'mode': 'nearest'}}}))
            (attempt / 'report.json').write_text(json.dumps({'execution_adapter': {
                'execute_chunk_steps': 16, 'gripper_projection_enabled': True}}))
            adapter = _execution_adapter(attempt / 'policy-transitions.npz')
            self.assertEqual(adapter['execute_chunk_steps'], 16)
            self.assertEqual(adapter['gripper_projection']['mode'], 'nearest')
            (attempt / 'report.json').unlink()
            self.assertEqual(_execution_adapter(attempt / 'policy-transitions.npz')['execute_chunk_steps'], 1)
            (root / 'report.json').unlink()
            self.assertEqual(_execution_adapter(attempt / 'policy-transitions.npz')['execute_chunk_steps'], 1)


if __name__ == "__main__":
    unittest.main()
