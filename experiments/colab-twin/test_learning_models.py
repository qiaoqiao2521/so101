"""Regression tests for dataset/policy boundaries, without hardware or GPU."""
from __future__ import annotations

import json
import copy
from pathlib import Path
import tempfile
import unittest

import numpy as np
import torch

from learning_models import (ACTION, ENV_STATE, STATE, ModelSpec, StateNormalizer,
                             StatePolicyRunner, build_policy, load_policy)
from learning_data import SCHEMA_VERSION
from train_state_policy import (critical_sampling_weights, evaluate_regression,
                                load_initialization_checkpoint, make_chunks)


def training_rows(count=6):
    rng = np.random.default_rng(19)
    return {STATE: rng.normal(size=(count, 6)),
            ENV_STATE: rng.normal(size=(count, 30)),
            ACTION: rng.normal(size=(count, 6))}


class LearningBoundaryTests(unittest.TestCase):
    def test_action_chunks_stop_at_invalid_label_gap_and_episode_boundary(self):
        rows = training_rows()
        # Invalid frame 2 has been filtered; episode 1 follows episode 0.
        rows.update(episode_index=np.array([0, 0, 0, 0, 1, 1]),
                    frame_index=np.array([0, 1, 3, 4, 0, 1]))
        normalizer = StateNormalizer.fit(rows)
        chunk = make_chunks(rows, 4, normalizer)
        self.assertEqual(chunk["action_is_pad"].tolist(),
                         [[False, False, True, True], [False, True, True, True],
                          [False, False, True, True], [False, True, True, True],
                          [False, False, True, True], [False, True, True, True]])
        np.testing.assert_allclose(chunk[ACTION][2, :2].numpy(),
                                   normalizer.normalize(ACTION, rows[ACTION][2:4]))

    def test_normalization_fits_training_only_and_constant_columns_use_unit_scale(self):
        rows = training_rows(4)
        rows[STATE][:, 0] = 2.0
        rows[ENV_STATE][:, 1] = np.array([3.0, 3.000001, 3.000002, 3.000003])
        normalizer = StateNormalizer.fit(rows)
        snapshot = json.loads(json.dumps(normalizer.stats))
        validation = {key: np.full_like(rows[key], 1000) for key in (STATE, ENV_STATE, ACTION)}
        for key in validation:
            normalizer.normalize(key, validation[key])
        self.assertEqual(normalizer.stats, snapshot)
        self.assertEqual(normalizer.stats[STATE]["mean"][0], 2.0)
        self.assertEqual(normalizer.stats[STATE]["std"][0], 1.0)
        self.assertEqual(normalizer.stats[ENV_STATE]["std"][1], 1.0)
        np.testing.assert_allclose(normalizer.normalize(STATE, rows[STATE])[:, 0], 0)

    def test_mlp_checkpoint_roundtrip_preserves_absolute_radian_prediction(self):
        torch.manual_seed(7)
        rows = training_rows()
        normalizer = StateNormalizer.fit(rows)
        spec = ModelSpec(model="mlp")
        policy = build_policy(spec).eval()
        metadata = {"format": "so101-state-policy-v1", "model_spec": spec.to_dict(),
                    "normalization": normalizer.stats, "state_dict": policy.state_dict()}
        observation = {key: rows[key][0] for key in (STATE, ENV_STATE)}
        reference = StatePolicyRunner(policy, normalizer, metadata, "cpu").predict(observation)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.pt"
            torch.save(metadata, path)
            reloaded = load_policy(str(path))
            reloaded.reset()
            np.testing.assert_array_equal(reference, reloaded.predict(observation))

    def test_policy_runner_consumes_only_the_two_observation_keys(self):
        normalizer = StateNormalizer.fit(training_rows())
        calls = []

        class SpyPolicy:
            def reset(self):
                calls.append("reset")

            def select_action(self, batch):
                calls.append(set(batch))
                return torch.zeros((1, 6))

        runner = StatePolicyRunner(SpyPolicy(), normalizer,
                                   {"model_spec": ModelSpec(model="mlp").to_dict()}, "cpu")
        runner.reset()
        output = runner.predict({STATE: np.zeros(6), ENV_STATE: np.zeros(30),
                                 "stage": "poison", "time_s": 1e12,
                                 "expert_action": np.full(6, np.nan)})
        self.assertEqual(calls, ["reset", {STATE, ENV_STATE}])
        np.testing.assert_array_equal(output, np.asarray(normalizer.stats[ACTION]["mean"]))

    def test_official_act_reobserves_every_tick_and_selects_first_action(self):
        spec = ModelSpec(model="act", dim_model=16, dim_feedforward=32,
                         n_heads=4, n_encoder_layers=1, n_decoder_layers=1,
                         chunk_size=4, use_vae=False, dropout=0)
        policy = build_policy(spec).eval()
        self.assertEqual(policy.config.n_action_steps, 1)
        calls = []

        def chunk(batch):
            calls.append(batch[STATE].clone())
            return torch.full((1, 4, 6), float(len(calls) * 10)) + torch.arange(4)[None, :, None]

        policy.predict_action_chunk = chunk
        first = policy.select_action({STATE: torch.zeros((1, 6)), ENV_STATE: torch.zeros((1, 30))})
        second = policy.select_action({STATE: torch.ones((1, 6)), ENV_STATE: torch.ones((1, 30))})
        self.assertEqual(len(calls), 2)
        torch.testing.assert_close(first, torch.full((1, 6), 10.0))
        torch.testing.assert_close(second, torch.full((1, 6), 20.0))
        torch.testing.assert_close(calls[1], torch.ones((1, 6)))

    def test_arm_delta_chunk_uses_only_the_current_anchor(self):
        rows = training_rows(4)
        rows.update(episode_index=np.zeros(4, dtype=int), frame_index=np.arange(4))
        normalizer = StateNormalizer.fit(rows, action_encoding="arm_delta")
        chunk = make_chunks(rows, 3, normalizer)
        decoded = normalizer.action_radians(chunk[ACTION][:1], anchor=rows[STATE][:1])
        np.testing.assert_allclose(decoded[0], rows[ACTION][:3], atol=1e-6)
        np.testing.assert_allclose(chunk[ACTION][0].numpy(),
                                   normalizer.normalize(ACTION, rows[ACTION][:3], anchor=rows[STATE][0]))
        # Future observations must not influence this chunk's training labels.
        changed = {key: value.copy() for key, value in rows.items()}
        changed[STATE][1:] += 1234
        after = make_chunks(changed, 3, normalizer)
        torch.testing.assert_close(chunk[ACTION][0], after[ACTION][0])
        with self.assertRaisesRegex(ValueError, "anchor"):
            normalizer.action_radians(chunk[ACTION])

    def test_arm_delta_checkpoint_roundtrip_keeps_absolute_output_and_floor(self):
        rows = training_rows()
        normalizer = StateNormalizer.fit(rows, action_encoding="arm_delta", velocity_scale_floor=.1)
        spec = ModelSpec(model="mlp", action_encoding="arm_delta")
        policy = build_policy(spec).eval()
        metadata = {"format": "so101-state-policy-v1", "model_spec": spec.to_dict(),
                    "action_encoding": "arm_delta", "normalization": normalizer.stats,
                    "normalization_options": {"velocity_scale_floor_rad_s": .1},
                    "state_dict": policy.state_dict()}
        obs = {key: rows[key][0] for key in (STATE, ENV_STATE)}
        reference = StatePolicyRunner(policy, normalizer, metadata, "cpu").predict(obs)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.pt"
            torch.save(metadata, path)
            restored = load_policy(str(path))
            self.assertEqual(restored.normalizer.action_encoding, "arm_delta")
            self.assertEqual(restored.normalizer.velocity_scale_floor, .1)
            np.testing.assert_array_equal(restored.predict(obs), reference)

    def test_old_checkpoint_without_encoding_remains_absolute(self):
        rows = training_rows()
        normalizer = StateNormalizer.fit(rows)
        spec = ModelSpec(model="mlp").to_dict()
        spec.pop("action_encoding")
        policy = build_policy(ModelSpec(model="mlp")).eval()
        metadata = {"format": "so101-state-policy-v1", "model_spec": spec,
                    "normalization": normalizer.stats, "state_dict": policy.state_dict()}
        observation = {STATE: rows[STATE][0], ENV_STATE: rows[ENV_STATE][0]}
        expected = StatePolicyRunner(policy, normalizer, metadata, "cpu").predict(observation)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "old-policy.pt"
            torch.save(metadata, path)
            restored = load_policy(str(path))
            self.assertEqual(restored.normalizer.action_encoding, "absolute")
            np.testing.assert_array_equal(restored.predict(observation), expected)

    def test_velocity_floor_applies_only_to_qvel_and_does_not_refit_validation(self):
        rows = training_rows(4)
        rows[ENV_STATE][:, :7] = np.arange(4)[:, None] * .001
        normalizer = StateNormalizer.fit(rows, velocity_scale_floor=.1)
        np.testing.assert_allclose(normalizer.stats[ENV_STATE]["std"][:6], .1)
        self.assertLess(normalizer.stats[ENV_STATE]["std"][6], .1)
        snapshot = json.loads(json.dumps(normalizer.stats))
        normalizer.normalize(ENV_STATE, np.full((4, 30), 1000))
        self.assertEqual(normalizer.stats, snapshot)

    def test_arm_delta_runner_has_only_two_inputs_and_absolute_gripper(self):
        rows = training_rows()
        normalizer = StateNormalizer.fit(rows, action_encoding="arm_delta")
        calls = []

        class SpyPolicy:
            def select_action(self, batch):
                calls.append(set(batch))
                return torch.zeros((1, 6))

        runner = StatePolicyRunner(SpyPolicy(), normalizer,
                                   {"model_spec": ModelSpec(model="mlp", action_encoding="arm_delta").to_dict()}, "cpu")
        current = np.arange(6, dtype=float) + 10
        output = runner.predict({STATE: current, ENV_STATE: rows[ENV_STATE][0],
                                 "stage": "poison", "time_s": 1e9, "expert_action": np.full(6, np.nan)})
        expected = np.asarray(normalizer.stats[ACTION]["mean"]).copy()
        expected[:5] += current[:5]
        self.assertEqual(calls, [{STATE, ENV_STATE}])
        np.testing.assert_array_equal(output, expected)

    def test_regression_reports_decoded_chunk_and_startup_errors_in_radians(self):
        rows = {STATE: np.broadcast_to(np.arange(3)[:, None], (3, 6)).astype(float).copy(),
                ENV_STATE: np.zeros((3, 30)), "episode_index": np.zeros(3, dtype=int),
                "frame_index": np.arange(3)}
        rows[ACTION] = rows[STATE] + .2
        rows[ACTION][:, 5] = .5
        normalizer = StateNormalizer.fit(rows, action_encoding="arm_delta")
        chunks = make_chunks(rows, 2, normalizer)

        class ConstantResidualPolicy:
            def eval(self):
                pass

            def predict_action_chunk(self, batch):
                if set(batch) != {STATE, ENV_STATE}:
                    raise AssertionError("Audit anchors must not enter policy inputs")
                return torch.zeros((len(batch[STATE]), 2, 6))

        report = evaluate_regression(ConstantResidualPolicy(), chunks, normalizer, "cpu", 2)
        self.assertLess(report["first_action_mae_rad"], 1e-8)
        # Two valid future commands differ by one radian in each of five arm
        # joints; five total valid commands, six joints each => 10/30 radians.
        self.assertAlmostEqual(report["all_chunk_mae_rad"], 1/3, places=7)
        self.assertAlmostEqual(report["all_chunk_max_abs_error_rad"], 1.0, places=7)
        self.assertEqual(report["startup_first_frames"]["1"]["frame_count"], 1)
        self.assertEqual(report["startup_first_frames"]["16"]["frame_count"], 3)

    def test_critical_sampling_marks_each_episode_start_independently(self):
        rows = training_rows(120)
        rows[ACTION][:, 5] = .5
        rows.update(episode_index=np.repeat([0, 7], 60), frame_index=np.tile(np.arange(60), 2),
                    stage=np.full(120, "poison"))
        weights, audit = critical_sampling_weights(rows, 4)
        np.testing.assert_array_equal(weights[:50], 4)
        np.testing.assert_array_equal(weights[50:60], 1)
        np.testing.assert_array_equal(weights[60:110], 4)
        np.testing.assert_array_equal(weights[110:], 1)
        self.assertEqual(audit["criterion_row_counts"]["startup"], 100)
        self.assertEqual(audit["event_counts"], {"correction": 0, "gripper_switch": 0})
        self.assertEqual(audit["row_weight_counts"], {"1.0": 20, "4.0": 100})
        self.assertAlmostEqual(audit["expected_critical_probability_mass"], 400 / 420)
        uniform, old = critical_sampling_weights(rows)
        np.testing.assert_array_equal(uniform, 1)
        self.assertEqual(old["mode"], "uniform_permutation")

    def test_correction_windows_stop_at_next_gap_and_episode_boundary(self):
        frames = np.r_[np.arange(55), [100, 101], np.arange(105, 115), np.arange(55)]
        rows = training_rows(len(frames))
        rows[ACTION][:, 5] = .5
        rows.update(episode_index=np.r_[np.zeros(67, dtype=int), np.ones(55, dtype=int)],
                    frame_index=frames)
        weights, audit = critical_sampling_weights(rows, 5)
        np.testing.assert_array_equal(weights[50:55], 1)
        np.testing.assert_array_equal(weights[55:57], 5)  # two-frame recovery segment
        np.testing.assert_array_equal(weights[57:63], 5)  # first correction plus five
        np.testing.assert_array_equal(weights[63:67], 1)
        np.testing.assert_array_equal(weights[117:], 1)  # episode 1 frames 50-54
        self.assertEqual(audit["event_counts"]["correction"], 2)
        self.assertEqual(audit["criterion_row_counts"]["correction"], 8)

    def test_gripper_switch_windows_ignore_nonadjacent_commands_and_clip_at_gaps(self):
        # A real change at frame 62 is near a gap. The commands also change
        # across the gap and episode boundary; those are not valid switches.
        frames = np.r_[np.arange(64), np.arange(100, 120), np.arange(70)]
        rows = training_rows(len(frames))
        rows[ACTION][:, 5] = 0
        rows[ACTION][62:64, 5] = .5
        rows[ACTION][84:, 5] = .5
        rows.update(episode_index=np.r_[np.zeros(84, dtype=int), np.ones(70, dtype=int)],
                    frame_index=frames)
        weights, audit = critical_sampling_weights(rows, 3)
        np.testing.assert_array_equal(weights[50:54], 1)
        np.testing.assert_array_equal(weights[54:64], 3)
        np.testing.assert_array_equal(weights[64:70], 3)  # independent recovery criterion
        self.assertEqual(weights[70], 1)  # no gripper window expansion across the gap
        self.assertEqual(audit["event_counts"]["gripper_switch"], 1)
        self.assertEqual(audit["criterion_row_counts"]["gripper_switch"], 10)
        np.testing.assert_array_equal(weights[134:], 1)  # episode 1 frames >=50

    def test_critical_sampling_rejects_invalid_weights(self):
        rows = training_rows(3)
        rows.update(episode_index=np.zeros(3, dtype=int), frame_index=np.arange(3))
        for value in (0, .9, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                critical_sampling_weights(rows, value)

    def chunk_runner(self, steps=3, prediction=None):
        stats = {key: {"mean": [0.] * width, "std": [1.] * width}
                 for key, width in ((STATE, 6), (ENV_STATE, 30), (ACTION, 6))}
        normalizer = StateNormalizer(stats, action_encoding="arm_delta")
        calls = []

        class ChunkPolicy:
            def reset(self):
                calls.append("reset")

            def predict_action_chunk(self, batch):
                calls.append(set(batch))
                if prediction is not None:
                    return prediction
                return torch.arange(1, 5, dtype=torch.float32)[None, :, None].expand(1, 4, 6).clone()

        spec = ModelSpec(model="act", chunk_size=4, action_encoding="arm_delta")
        runner = StatePolicyRunner(ChunkPolicy(), normalizer, {"model_spec": spec.to_dict()}, "cpu",
                                   execute_chunk_steps=steps)
        return runner, calls

    def test_chunk_execution_locks_anchor_then_refreshes_only_after_partial_queue(self):
        runner, calls = self.chunk_runner(3)
        observation = {STATE: np.full(6, 10.), ENV_STATE: np.zeros(30), "stage": "poison"}
        first = runner.predict(observation)
        observation[STATE][:] = 100
        second = runner.predict(observation)
        third = runner.predict(observation)
        fourth = runner.predict(observation)
        np.testing.assert_array_equal(first[:5], 11)
        np.testing.assert_array_equal(second[:5], 12)  # not the changed 100 + 2
        np.testing.assert_array_equal(third[:5], 13)
        np.testing.assert_array_equal(fourth[:5], 101)
        self.assertEqual([first[5], second[5], third[5], fourth[5]], [1, 2, 3, 1])
        self.assertEqual(calls, [{STATE, ENV_STATE}, {STATE, ENV_STATE}])

    def test_chunk_reset_discards_remaining_commands_and_takes_a_new_anchor(self):
        runner, calls = self.chunk_runner(4)
        observation = {STATE: np.full(6, 10.), ENV_STATE: np.zeros(30)}
        runner.predict(observation)
        runner.reset()
        observation[STATE][:] = 20
        np.testing.assert_array_equal(runner.predict(observation)[:5], 21)
        self.assertEqual(calls, [{STATE, ENV_STATE}, "reset", {STATE, ENV_STATE}])

    def test_chunk_execution_rejects_shape_nan_invalid_observations_and_budget(self):
        for prediction in (torch.zeros((1, 2, 6)), torch.full((1, 4, 6), float("nan"))):
            with self.subTest(shape=prediction.shape):
                runner, _ = self.chunk_runner(prediction=prediction)
                with self.assertRaisesRegex(RuntimeError, "action chunk"):
                    runner.predict({STATE: np.zeros(6), ENV_STATE: np.zeros(30)})
        runner, _ = self.chunk_runner()
        runner.predict({STATE: np.zeros(6), ENV_STATE: np.zeros(30)})
        with self.assertRaises(ValueError):
            runner.predict({STATE: np.full(6, np.nan), ENV_STATE: np.zeros(30)})
        # Invalid observations are rejected before consuming a cached action.
        self.assertEqual(len(runner._absolute_actions), 2)
        for steps in (0, 5, -1, 1.5, True):
            with self.subTest(steps=steps), self.assertRaises(ValueError):
                self.chunk_runner(steps)
        with self.assertRaisesRegex(ValueError, "MLP"):
            StatePolicyRunner(None, None, {"model_spec": ModelSpec(model="mlp").to_dict()}, "cpu",
                              execute_chunk_steps=2)

    def initialization_fixture(self):
        spec = ModelSpec(model="mlp", action_encoding="arm_delta", use_vae=False, dropout=0)
        normalizer = StateNormalizer.fit(training_rows(), action_encoding="arm_delta", velocity_scale_floor=.1)
        policy = build_policy(spec).eval()
        return {"format": "so101-state-policy-v1", "schema_version": SCHEMA_VERSION,
                "model_spec": spec.to_dict(), "state_dict": policy.state_dict(),
                "action_encoding": "arm_delta", "normalization": normalizer.stats,
                "normalization_options": {"velocity_scale_floor_rad_s": .1},
                "model_sha256": "d" * 64, "control_period_s": .02,
                "train_dataset_sha256": ["a" * 64]}

    def initialize(self, data, **overrides):
        options = {"spec": ModelSpec(model="mlp", action_encoding="arm_delta", use_vae=False, dropout=0),
                   "control_period_s": .02, "model_sha256": "d" * 64, "velocity_scale_floor": .1,
                   "eligible_train_hashes": ["a" * 64, "b" * 64], "validation_hashes": ["c" * 64],
                   **overrides}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "init.pt"
            torch.save(data, path)
            return load_initialization_checkpoint(path, **options)

    def test_checkpoint_initialization_preserves_old_subset_stats_and_uses_fresh_adam(self):
        data = self.initialization_fixture()
        # A stored optimizer payload must not be loaded or described as resumed.
        data["optimizer_state_dict"] = {"old_state": 123}
        states, normalization, audit = self.initialize(data)
        self.assertEqual(normalization.stats, data["normalization"])
        self.assertEqual(normalization.action_encoding, "arm_delta")
        self.assertEqual(normalization.velocity_scale_floor, .1)
        self.assertEqual(audit["original_training_dataset_sha256"], ["a" * 64])
        self.assertEqual(len(audit["checkpoint_sha256"]), 64)
        self.assertIn("fresh Adam", audit["optimizer"])
        new_rows = training_rows()
        new_rows[STATE] += 100
        changed_statistics = StateNormalizer.fit(new_rows, action_encoding="arm_delta", velocity_scale_floor=.1)
        self.assertNotEqual(normalization.stats, changed_statistics.stats)
        policy = build_policy(ModelSpec(**data["model_spec"]))
        policy.load_state_dict(states, strict=True)
        optimizer = torch.optim.Adam(policy.parameters())
        self.assertEqual(dict(optimizer.state), {})
        for name, value in policy.state_dict().items():
            torch.testing.assert_close(value, data["state_dict"][name])

    def test_initialization_distinguishes_weight_training_from_inherited_statistic_origin(self):
        data = self.initialization_fixture()
        data["train_dataset_sha256"] = ["a"*64, "b"*64]
        data["normalization_source"] = {"training_dataset_sha256": ["a"*64]}
        _, normalization, audit = self.initialize(data)
        self.assertEqual(audit["original_training_dataset_sha256"], ["a"*64, "b"*64])
        self.assertEqual(audit["normalization_training_dataset_sha256"], ["a"*64])
        self.assertEqual(normalization.stats, data["normalization"])
        data["normalization_source"]["training_dataset_sha256"] = ["c"*64]
        with self.assertRaisesRegex(ValueError, "normalization origin"):
            self.initialize(data)

    def test_checkpoint_initialization_rejects_schema_model_timing_encoding_or_floor_change(self):
        base = self.initialization_fixture()
        changes = [("format", "wrong"), ("schema_version", "wrong"), ("model_sha256", "e" * 64),
                   ("control_period_s", .04), ("action_encoding", "absolute")]
        for key, value in changes:
            data = copy.deepcopy(base)
            data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.initialize(data)
        for key, value in [("chunk_size", 8), ("dropout", .1), ("use_vae", True), ("action_encoding", "absolute")]:
            data = copy.deepcopy(base)
            data["model_spec"][key] = value
            with self.subTest(spec=key), self.assertRaises(ValueError):
                self.initialize(data)
        data = copy.deepcopy(base)
        data["normalization_options"]["velocity_scale_floor_rad_s"] = .2
        with self.assertRaisesRegex(ValueError, "velocity scale"):
            self.initialize(data)

    def test_checkpoint_initialization_rejects_noneligible_source_or_validation_overlap(self):
        data = self.initialization_fixture()
        with self.assertRaisesRegex(ValueError, "eligible training subset"):
            self.initialize(data, eligible_train_hashes=["b" * 64])
        with self.assertRaisesRegex(ValueError, "disjoint from validation"):
            self.initialize(data, validation_hashes=["a" * 64])
        data["train_dataset_sha256"] = []
        with self.assertRaisesRegex(ValueError, "eligible training subset"):
            self.initialize(data)

    def test_checkpoint_initialization_rejects_bad_statistics_and_nonfinite_parameters(self):
        base = self.initialization_fixture()
        for feature, statistic, value in [(STATE, "mean", [float("inf")] * 6),
                                           (ACTION, "std", [0.] * 6),
                                           (ENV_STATE, "std", [1.] * 2)]:
            data = copy.deepcopy(base)
            data["normalization"][feature][statistic] = value
            with self.subTest(feature=feature, statistic=statistic), self.assertRaisesRegex(ValueError, "normalization"):
                self.initialize(data)
        data = copy.deepcopy(base)
        key = next(iter(data["state_dict"]))
        data["state_dict"][key].reshape(-1)[0] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite tensors"):
            self.initialize(data)

    def test_legacy_absolute_initialization_defaults_missing_encoding_and_floor(self):
        data = self.initialization_fixture()
        spec = ModelSpec(model="mlp", action_encoding="absolute", use_vae=False, dropout=0)
        data["model_spec"] = spec.to_dict()
        data["model_spec"].pop("action_encoding")
        data.pop("action_encoding")
        data.pop("normalization_options")
        data["normalization"] = StateNormalizer.fit(training_rows()).stats
        _, normalization, _ = self.initialize(data, spec=spec, velocity_scale_floor=0)
        self.assertEqual(normalization.action_encoding, "absolute")
        self.assertEqual(normalization.velocity_scale_floor, 0.)

    def test_robot_velocity_mask_changes_only_six_normalized_channels_not_statistics(self):
        rows = training_rows()
        full = StateNormalizer.fit(rows, velocity_scale_floor=.1)
        masked = StateNormalizer.fit(rows, velocity_scale_floor=.1, robot_velocity_mask=True)
        self.assertEqual(full.stats, masked.stats)
        baseline = full.normalize(ENV_STATE, rows[ENV_STATE])
        output = masked.normalize(ENV_STATE, rows[ENV_STATE])
        np.testing.assert_array_equal(output[:, :6], 0)
        np.testing.assert_array_equal(output[:, 6:], baseline[:, 6:])
        np.testing.assert_array_equal(masked.normalize(STATE, rows[STATE]), full.normalize(STATE, rows[STATE]))
        for value in (np.nan, np.inf):
            corrupt = rows[ENV_STATE].copy()
            corrupt[0, 0] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Nonfinite"):
                masked.normalize(ENV_STATE, corrupt)

    def test_robot_velocity_mask_is_persisted_and_shared_by_chunks_and_runner(self):
        rows = training_rows()
        rows.update(episode_index=np.zeros(len(rows[ACTION]), dtype=int), frame_index=np.arange(len(rows[ACTION])))
        normalizer = StateNormalizer.fit(rows, robot_velocity_mask=True)
        spec = ModelSpec(model="mlp")
        policy = build_policy(spec).eval()
        data = {"format": "so101-state-policy-v1", "model_spec": spec.to_dict(),
                "normalization": normalizer.stats, "state_dict": policy.state_dict(),
                "normalization_options": {"robot_velocity_mask": True}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "masked.pt"
            torch.save(data, path)
            runner = load_policy(str(path))
            self.assertTrue(runner.normalizer.robot_velocity_mask)
            self.assertFalse(runner.normalizer.object_velocity_mask)
            observation = {STATE: rows[STATE][0], ENV_STATE: rows[ENV_STATE][0].copy()}
            reference = runner.predict(observation)
            observation[ENV_STATE][:6] += 100
            np.testing.assert_array_equal(runner.predict(observation), reference)
            observation[ENV_STATE][0] = np.nan
            with self.assertRaises(ValueError):
                runner.predict(observation)
        chunks = make_chunks(rows, 3, normalizer)
        np.testing.assert_array_equal(chunks[ENV_STATE][:, :6].numpy(), 0)
        np.testing.assert_array_equal(chunks[ENV_STATE][:, 6:].numpy(), normalizer.normalize(ENV_STATE, rows[ENV_STATE])[:, 6:])

    def test_robot_velocity_mask_initialization_requires_explicit_provenance(self):
        data = self.initialization_fixture()  # old full-observation checkpoint
        _, normalization, audit = self.initialize(data, robot_velocity_mask=True)
        self.assertTrue(normalization.robot_velocity_mask)
        self.assertEqual(normalization.stats, data["normalization"])
        self.assertEqual(audit["observation_ablation"], {"robot_velocity_mask_from": False,
                                                       "robot_velocity_mask_to": True,
                                                       "explicit_new_mask": True,
                                                       "object_velocity_mask_from": False,
                                                       "object_velocity_mask_to": False,
                                                       "explicit_new_object_mask": False})
        data["normalization_options"]["robot_velocity_mask"] = True
        with self.assertRaisesRegex(ValueError, "silently removed"):
            self.initialize(data)
        _, restored, audit = self.initialize(data, robot_velocity_mask=True)
        self.assertTrue(restored.robot_velocity_mask)
        self.assertFalse(audit["observation_ablation"]["explicit_new_mask"])
        data["normalization_options"]["robot_velocity_mask"] = "false"
        with self.assertRaisesRegex(ValueError, "booleans"):
            self.initialize(data, robot_velocity_mask=True)

    def test_object_velocity_mask_changes_only_declared_channels_and_keeps_finite_guard(self):
        rows = training_rows()
        original = rows[ENV_STATE].copy()
        full = StateNormalizer.fit(rows, velocity_scale_floor=.1)
        baseline = full.normalize(ENV_STATE, rows[ENV_STATE])
        for robot_mask in (False, True):
            with self.subTest(robot_mask=robot_mask):
                masked = StateNormalizer.fit(rows, velocity_scale_floor=.1,
                                             robot_velocity_mask=robot_mask, object_velocity_mask=True)
                self.assertEqual(masked.stats, full.stats)
                indices = list(range(13, 19)) + (list(range(6)) if robot_mask else [])
                retained = [i for i in range(30) if i not in indices]
                output = masked.normalize(ENV_STATE, rows[ENV_STATE])
                np.testing.assert_array_equal(output[:, indices], 0)
                np.testing.assert_array_equal(output[:, retained], baseline[:, retained])
                np.testing.assert_array_equal(masked.normalize(STATE, rows[STATE]), full.normalize(STATE, rows[STATE]))
                np.testing.assert_array_equal(masked.normalize(ACTION, rows[ACTION]), full.normalize(ACTION, rows[ACTION]))
                np.testing.assert_array_equal(rows[ENV_STATE], original)
                for value in (np.nan, np.inf):
                    corrupt = original.copy()
                    corrupt[0, 13] = value
                    with self.assertRaisesRegex(ValueError, "Nonfinite"):
                        masked.normalize(ENV_STATE, corrupt)
        with self.assertRaisesRegex(ValueError, "explicit boolean"):
            StateNormalizer(full.stats, object_velocity_mask="false")

    def test_object_velocity_mask_persisted_reload_matches_chunks_and_runner(self):
        rows = training_rows()
        rows.update(episode_index=np.zeros(len(rows[ACTION]), dtype=int), frame_index=np.arange(len(rows[ACTION])))
        normalizer = StateNormalizer.fit(rows, robot_velocity_mask=True, object_velocity_mask=True)
        spec = ModelSpec(model="mlp", dropout=0)
        policy = build_policy(spec).eval()
        data = {"format": "so101-state-policy-v1", "model_spec": spec.to_dict(),
                "normalization": normalizer.stats, "state_dict": policy.state_dict(),
                "normalization_options": {"robot_velocity_mask": True, "object_velocity_mask": True}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "masked-object.pt"
            torch.save(data, path)
            runner = load_policy(str(path))
            self.assertTrue(runner.normalizer.robot_velocity_mask)
            self.assertTrue(runner.normalizer.object_velocity_mask)
            observation = {STATE: rows[STATE][0], ENV_STATE: rows[ENV_STATE][0].copy()}
            reference = runner.predict(observation)
            observation[ENV_STATE][13:19] += 100
            np.testing.assert_array_equal(runner.predict(observation), reference)
            observation[ENV_STATE][13] = np.nan
            with self.assertRaises(ValueError):
                runner.predict(observation)
        chunks = make_chunks(rows, 3, normalizer)
        np.testing.assert_array_equal(chunks[ENV_STATE].numpy(), normalizer.normalize(ENV_STATE, rows[ENV_STATE]))
        np.testing.assert_array_equal(chunks[ENV_STATE][:, 13:19].numpy(), 0)

    def test_object_velocity_mask_initialization_is_explicit_and_preserves_body_mask(self):
        data = self.initialization_fixture()
        data["normalization_options"]["robot_velocity_mask"] = True
        _, normalization, audit = self.initialize(data, robot_velocity_mask=True, object_velocity_mask=True)
        self.assertTrue(normalization.robot_velocity_mask)
        self.assertTrue(normalization.object_velocity_mask)
        self.assertEqual(normalization.stats, data["normalization"])
        ablation = audit["observation_ablation"]
        self.assertTrue(ablation["robot_velocity_mask_from"])
        self.assertTrue(ablation["robot_velocity_mask_to"])
        self.assertFalse(ablation["explicit_new_mask"])
        self.assertFalse(ablation["object_velocity_mask_from"])
        self.assertTrue(ablation["object_velocity_mask_to"])
        self.assertTrue(ablation["explicit_new_object_mask"])
        data["normalization_options"]["object_velocity_mask"] = True
        with self.assertRaisesRegex(ValueError, "object velocity mask cannot be silently removed"):
            self.initialize(data, robot_velocity_mask=True)
        _, restored, audit = self.initialize(data, robot_velocity_mask=True, object_velocity_mask=True)
        self.assertTrue(restored.object_velocity_mask)
        self.assertFalse(audit["observation_ablation"]["explicit_new_object_mask"])
        data["normalization_options"]["object_velocity_mask"] = "false"
        with self.assertRaisesRegex(ValueError, "booleans"):
            self.initialize(data, robot_velocity_mask=True, object_velocity_mask=True)


if __name__ == "__main__":
    unittest.main()
