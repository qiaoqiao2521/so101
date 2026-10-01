"""Data contracts: label timing, failed-attempt accounting and archive integrity."""
from pathlib import Path
import tempfile
import unittest

import h5py
import numpy as np

from learning_data import (
    ENVIRONMENT_FEATURE_NAMES, POLICY_OBSERVATION_KEYS, EpisodeRecorder,
    audit_episodes, load_episode, split_episodes, training_rows,
)


def metadata(**overrides):
    return {"control_period_s": .02, "physics_dt_s": .002, "seed": 7,
            "model_sha256": "a" * 64, "scene_configuration": {"noslip_iterations": 10}, **overrides}


def observation(index):
    return {"observation.state": np.full(6, index * .01),
            "observation.environment_state": np.full(30, index * .02),
            "time_s": 1 + index * .02, "stage": "must_not_be_policy_input"}


class DataContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def record(self, name, *, passed=True, count=3, invalid=()):
        recorder = EpisodeRecorder(self.root / f"{name}.h5", metadata())
        for index in range(count):
            valid = index not in invalid
            recorder.append(observation(index), np.full(6, .1 + index), np.full(6, .2 + index),
                            observation(index+1), valid, "approach", not valid)
        return recorder.finalize({"passed": passed, "failure": None if passed else "payload lost"})

    def test_expert_target_is_not_executed_action_or_next_state(self):
        path = self.record("aligned")
        episode = load_episode(path)
        np.testing.assert_allclose(episode["action"][:, 0], [.1, 1.1, 2.1])
        np.testing.assert_allclose(episode["executed_action"][:, 0], [.2, 1.2, 2.2])
        np.testing.assert_allclose(episode["observation.state"][:, 0], [0, .01, .02])
        np.testing.assert_allclose(episode["next_observation.state"][:, 0], [.01, .02, .03])
        np.testing.assert_allclose(episode["timestamp"], [1, 1.02, 1.04])
        self.assertEqual(len(ENVIRONMENT_FEATURE_NAMES), 30)
        rows = training_rows([path])
        self.assertEqual(set(rows), {*POLICY_OBSERVATION_KEYS, "action", "episode_index", "frame_index"})
        self.assertNotIn("stage", rows)
        self.assertNotIn("timestamp", rows)

    def test_append_copies_numpy_views_before_simulation_mutates_them(self):
        recorder = EpisodeRecorder(self.root / "copied.h5", metadata())
        before, after, action = observation(0), observation(1), np.full(6, .1)
        recorder.append(before, action, action, after, True, "approach", False)
        before["observation.state"][:] = 90
        after["observation.environment_state"][:] = 90
        action[:] = 90
        episode = load_episode(recorder.finalize({"passed": True}))
        np.testing.assert_array_equal(episode["observation.state"], np.zeros((1, 6)))
        np.testing.assert_allclose(episode["next_observation.environment_state"], np.full((1, 30), .02))
        np.testing.assert_allclose(episode["action"], np.full((1, 6), .1))

    def test_raw_float64_roundtrip_preserves_commands_not_representable_as_float32(self):
        before, after = observation(0), observation(1)
        command = np.array([.123456789123, -.234567891234, .345678912345,
                            -.456789123456, .567891234567, .015000000123], dtype=np.float64)
        before["observation.state"] = command.copy()
        after["observation.state"] = command + 1e-10
        before["observation.environment_state"] = np.linspace(.123456789123, .234567891234, 30)
        after["observation.environment_state"] = before["observation.environment_state"] + 1e-10
        self.assertFalse(np.array_equal(command, command.astype(np.float32).astype(np.float64)))
        recorder = EpisodeRecorder(self.root / "precise.h5", metadata())
        recorder.append(before, command, command + 1e-10, after, True, "release", False)
        episode = load_episode(recorder.finalize({"passed": True}))
        self.assertEqual(episode["storage_precision"], "raw_float64_policy_tensor_float32")
        for key, expected in (("observation.state", before["observation.state"]),
                              ("observation.environment_state", before["observation.environment_state"]),
                              ("next_observation.state", after["observation.state"]),
                              ("next_observation.environment_state", after["observation.environment_state"]),
                              ("action", command), ("executed_action", command + 1e-10)):
            self.assertEqual(episode[key].dtype, np.dtype("float64"))
            np.testing.assert_array_equal(episode[key][0], expected)

    def test_legacy_float32_v1_archive_remains_readable_without_changing_outcome(self):
        path = self.record("legacy-failed", passed=False)
        with h5py.File(path, "r+") as archive:
            del archive.attrs["storage_precision"]
            for key in (*POLICY_OBSERVATION_KEYS, "next_observation.state",
                        "next_observation.environment_state", "action", "executed_action"):
                values = archive[key][:].astype(np.float32)
                del archive[key]
                archive.create_dataset(key, data=values)
        episode = load_episode(path)
        self.assertEqual(episode["storage_precision"], "legacy_raw_float32")
        self.assertEqual(episode["executed_action"].dtype, np.dtype("float32"))
        self.assertFalse(episode["report"]["passed"])
        self.assertFalse(episode["eligible_for_training"])
        self.assertEqual(audit_episodes([path])["failed_attempt_count"], 1)

    def test_control_cycle_and_previous_next_state_must_match(self):
        recorder = EpisodeRecorder(self.root / "timing.h5", metadata())
        late = observation(1)
        late["time_s"] += .001
        with self.assertRaisesRegex(ValueError, "control period"):
            recorder.append(observation(0), np.zeros(6), np.zeros(6), late, True, "approach", False)
        recorder.append(observation(0), np.zeros(6), np.zeros(6), observation(1), True, "approach", False)
        with self.assertRaisesRegex(ValueError, "Noncontiguous"):
            recorder.append(observation(2), np.zeros(6), np.zeros(6), observation(3), True, "approach", False)
        shifted = observation(1)
        shifted["observation.state"][0] += .1
        with self.assertRaisesRegex(ValueError, "preceding obs_after"):
            recorder.append(shifted, np.zeros(6), np.zeros(6), observation(2), True, "approach", False)

    def test_perturbation_excluded_and_recovery_labels_keep_original_indices(self):
        path = self.record("recovery", invalid=(1,))
        episode = load_episode(path)
        self.assertEqual(episode["perturbation"].tolist(), [False, True, False])
        rows = training_rows([path])
        self.assertEqual(rows["frame_index"].tolist(), [0, 2])
        np.testing.assert_allclose(rows["action"][:, 0], [.1, 2.1])
        recorder = EpisodeRecorder(self.root / "bad-label.h5", metadata())
        with self.assertRaisesRegex(ValueError, "perturbation cannot"):
            recorder.append(observation(0), np.zeros(6), np.ones(6), observation(1), True, "perturb", True)

    def test_invalid_label_can_be_absent_without_fabricating_a_correction(self):
        recorder = EpisodeRecorder(self.root / "unlabelled.h5", metadata())
        recorder.append(observation(0), None, np.ones(6), observation(1), False, "perturb", True)
        recorder.append(observation(1), np.full(6, .2), np.full(6, .2), observation(2), True, "recovery", False)
        path = recorder.finalize({"passed": True})
        self.assertTrue(np.isnan(load_episode(path)["action"][0]).all())
        self.assertEqual(training_rows([path])["frame_index"].tolist(), [1])

    def test_failed_and_empty_attempts_retained_but_not_trained(self):
        paths = [self.record("passed"), self.record("failed", passed=False),
                 self.record("early-failure", passed=False, count=0)]
        audit = audit_episodes(paths)
        self.assertEqual(audit["attempt_count"], 3)
        self.assertEqual(audit["passed_attempt_count"], 1)
        self.assertEqual(audit["failed_attempt_count"], 2)
        self.assertEqual(audit["recorded_transition_count"], 6)
        self.assertEqual(audit["training_transition_count"], 3)
        self.assertEqual(training_rows(paths)["episode_index"].tolist(), [0, 0, 0])
        self.assertEqual(load_episode(paths[2])["action"].shape, (0, 6))

    def test_empty_training_rows_have_fixed_shapes(self):
        rows = training_rows([self.record("failed", passed=False)])
        self.assertEqual(rows["observation.state"].shape, (0, 6))
        self.assertEqual(rows["observation.environment_state"].shape, (0, 30))
        self.assertEqual(rows["action"].shape, (0, 6))
        self.assertEqual(rows["episode_index"].shape, (0,))

    def test_archive_rejects_overwrite_even_if_created_after_recorder(self):
        target = self.root / "protected.h5"
        recorder = EpisodeRecorder(target, metadata())
        target.write_bytes(b"existing result")
        with self.assertRaises(FileExistsError):
            recorder.finalize({"passed": False})
        self.assertEqual(target.read_bytes(), b"existing result")
        self.assertEqual(list(self.root.glob("*.partial")), [])
        with self.assertRaises(FileExistsError):
            EpisodeRecorder(target, metadata())

    def test_finalize_requires_explicit_result_and_disallows_append_afterward(self):
        recorder = EpisodeRecorder(self.root / "result.h5", metadata())
        with self.assertRaisesRegex(ValueError, "explicit boolean"):
            recorder.finalize({"passed": "true"})
        recorder.finalize({"passed": False})
        with self.assertRaises(RuntimeError):
            recorder.append(observation(0), np.zeros(6), np.zeros(6), observation(1), True, "approach", False)

    def test_tampered_archive_alignment_and_invalid_expert_labels_rejected(self):
        path = self.record("tampered")
        with h5py.File(path, "r+") as archive:
            archive["observation.state"][1, 0] = .9
        with self.assertRaisesRegex(ValueError, "Shifted state"):
            load_episode(path)
        path = self.record("nonfinite")
        with h5py.File(path, "r+") as archive:
            archive["action"][0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "Nonfinite action"):
            load_episode(path)

    def test_train_validation_split_is_whole_episode_and_deterministic(self):
        paths = [self.record(f"episode-{index}") for index in range(5)]
        failed = self.record("failed", passed=False)
        split = split_episodes(paths + [failed], seed=9)
        self.assertEqual(split, split_episodes(paths + [failed], seed=9))
        self.assertFalse(set(split["train"]) & set(split["validation"]))
        self.assertEqual(set(split["train"] + split["validation"]), set(paths))
        self.assertEqual(len(split["validation"]), 1)
        with self.assertRaisesRegex(ValueError, "two successful"):
            split_episodes([paths[0], failed])

    def test_metadata_and_duplicate_attempt_paths_rejected(self):
        with self.assertRaisesRegex(ValueError, "integer number"):
            EpisodeRecorder(self.root / "period.h5", metadata(control_period_s=.021))
        with self.assertRaisesRegex(ValueError, "SHA256"):
            EpisodeRecorder(self.root / "hash.h5", metadata(model_sha256="unidentified"))
        path = self.record("once")
        with self.assertRaisesRegex(ValueError, "double-count"):
            audit_episodes([path, path])


if __name__ == "__main__":
    unittest.main()
