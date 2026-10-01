"""Independent checks on real, short-perturbation recovery archives.

Set SO101_RECOVERY_ARCHIVES to colon-separated HDF5 paths. Optionally set
SO101_RECOVERY_REPLAY_REPORT to the report from one physical raw64 replay.
These artifact tests do not call an expert, alter the scene or start training.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import unittest

import numpy as np

from learning_data import POLICY_OBSERVATION_KEYS, load_episode, training_rows


ARCHIVES = tuple(Path(path) for path in os.environ.get("SO101_RECOVERY_ARCHIVES", "").split(os.pathsep)
                 if path)
REPLAY_REPORT = os.environ.get("SO101_RECOVERY_REPLAY_REPORT")


@unittest.skipUnless(ARCHIVES, "Provide real short-perturbation recovery archives")
class RecoveryCollectionTests(unittest.TestCase):
    def test_first_correction_uses_the_actual_disturbed_boundary(self):
        for path in ARCHIVES:
            with self.subTest(archive=str(path)):
                episode = load_episode(path)
                injected = np.flatnonzero(episode["perturbation"])
                self.assertGreater(len(injected), 0, "No physical perturbation was recorded")
                np.testing.assert_array_equal(injected, np.arange(injected[0], injected[-1] + 1))
                self.assertFalse(episode["label_valid"][injected].any())
                correction = int(injected[-1] + 1)
                self.assertLess(correction, len(episode["timestamp"]), "No correction after disturbance")
                self.assertTrue(episode["label_valid"][correction], "Do not discard the moving recovery state")
                for key in POLICY_OBSERVATION_KEYS:
                    np.testing.assert_array_equal(episode[key][correction],
                                                  episode["next_" + key][correction - 1])
                self.assertEqual(episode["timestamp"][correction],
                                 episode["next_timestamp"][correction - 1])
                # qvel occupies the first six environment features. Object
                # angular velocity later in this vector is free-joint local,
                # rather than a promise of world-frame angular coordinates.
                velocity = episode["observation.environment_state"][correction, :5]
                self.assertGreater(float(np.linalg.norm(velocity)), 1e-6,
                                   "An extra settling interval erased recovery velocity")
                np.testing.assert_array_equal(episode["action"][correction, :5],
                                              episode["observation.state"][correction, :5])
                np.testing.assert_array_equal(episode["executed_action"][correction],
                                              episode["action"][correction])

    def test_raw_precision_and_label_filter_survive_real_recovery(self):
        for path in ARCHIVES:
            with self.subTest(archive=str(path)):
                episode = load_episode(path)
                self.assertEqual(episode["storage_precision"], "raw_float64_policy_tensor_float32")
                for key in (*POLICY_OBSERVATION_KEYS, "next_observation.state",
                            "next_observation.environment_state", "executed_action", "action"):
                    self.assertEqual(episode[key].dtype, np.dtype("float64"))
                rows = training_rows([path])
                if episode["report"]["passed"]:
                    np.testing.assert_array_equal(rows["frame_index"],
                                                  episode["frame_index"][episode["label_valid"]])
                    self.assertFalse(np.isin(episode["frame_index"][episode["perturbation"]],
                                             rows["frame_index"]).any())
                else:
                    self.assertEqual(len(rows["frame_index"]), 0,
                                     "A failed complete attempt must stay out of training")

    @unittest.skipUnless(REPLAY_REPORT, "Provide one physical recovery replay report")
    def test_one_recovery_has_exact_physical_replay_without_state_jumps(self):
        report = json.loads(Path(REPLAY_REPORT).read_text())
        matching = [path for path in ARCHIVES
                    if hashlib.sha256(path.read_bytes()).hexdigest() == report["archive_sha256"]]
        self.assertEqual(len(matching), 1, "Replay evidence belongs to another archive")
        episode = load_episode(matching[0])
        self.assertFalse(report["learned_policy_evaluated"])
        self.assertFalse(report["stage_labels_consumed"])
        self.assertTrue(report["trajectory_matches"], report.get("first_divergence"))
        self.assertIsNone(report["first_divergence"])
        self.assertEqual(report["steps_executed"], len(episode["executed_action"]))
        self.assertEqual(report["max_timestamp_error_s"], 0.0)
        for error in report["max_abs_error_per_feature"].values():
            np.testing.assert_array_equal(error, np.zeros(len(error)))
        if episode["report"]["passed"]:
            self.assertEqual(report["status"], "passed", report.get("error"))
            self.assertTrue(report["physical_acceptance"]["passed"])


if __name__ == "__main__":
    unittest.main()
