"""CPU-only adapter tests; no renderer, simulation, training or GPU is run."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import h5py
import numpy as np
import torch

from learning_vision import (ACTION, IMAGE, STATE, CameraSpec, VisionDataset,
    LEROBOT_REVISION, OFFICIAL_SOURCE_SHA256, RGB_NORMALIZATION, VISUAL_MODEL_SPEC,
    VISION_FORMAT, VISION_INPUT_KEYS, VisionNormalizer, VisionPolicyRunner,
    capture_rgb, load_visual_checkpoint, rgb_tensor, segment_lengths,
    validate_resource_report, visual_source_hashes)
from run_vision_learning import assert_exact_observation, evaluate


class DummyPolicy:
    def __init__(self):
        self.calls = 0

    def reset(self):
        self.calls = 0

    def predict_action_chunk(self, batch):
        if set(batch) != {STATE, IMAGE}:
            raise AssertionError("Policy received forbidden keys")
        self.calls += 1
        return torch.zeros(1, 16, 6)


def normalizer():
    return VisionNormalizer({key: {"mean": [0.] * 6, "std": [1.] * 6}
                             for key in (STATE, ACTION)})


def checkpoint_fixture():
    resource = {"status": "passed", "kind": "visual_act_cuda_five_step_microbenchmark",
                "source_sha256": visual_source_hashes(), "camera": CameraSpec().to_dict(),
                "visual_dataset_sha256": ["a" * 64], "raw_dataset_sha256": ["b" * 64],
                "model_spec": VISUAL_MODEL_SPEC, "rgb_normalization": RGB_NORMALIZATION,
                "official_source_sha256": OFFICIAL_SOURCE_SHA256, "lerobot_revision": LEROBOT_REVISION,
                "selected_batch_size": 8, "attempts": [{"batch_size": 8, "status": "passed", "steps": 5,
                "step_s": [.1] * 5, "memory_after": {"peak_allocated_mib": 1000., "peak_reserved_mib": 1200.}}]}
    text = json.dumps(resource, sort_keys=True) + "\n"
    checkpoint = {**{key: resource[key] for key in ("source_sha256", "camera", "visual_dataset_sha256",
                  "raw_dataset_sha256", "model_spec", "rgb_normalization", "official_source_sha256", "lerobot_revision")},
                  "format": VISION_FORMAT, "policy_input_keys": list(VISION_INPUT_KEYS),
                  "action_encoding": "arm_delta_absolute_jaw", "control_period_s": .02, "physics_dt_s": .002,
                  "normalization": normalizer().stats, "gripper_labels_rad": [.015, .5], "state_dict": {},
                  "resource_report_text": text, "resource_report_sha256": hashlib.sha256(text.encode()).hexdigest()}
    return checkpoint, resource


class VisionAdapterTests(unittest.TestCase):
    def test_checkpoint_binds_current_source_before_building_policy(self):
        checkpoint, _ = checkpoint_fixture()
        dummy = MagicMock()
        with patch("learning_vision.torch.load", return_value=checkpoint), \
             patch("learning_vision.build_visual_policy", return_value=dummy) as build:
            load_visual_checkpoint("mock.pt")
            build.assert_called_once_with("cpu")
            checkpoint["source_sha256"] = {"learning_vision.py": "0" * 64, "run_vision_learning.py": "0" * 64}
            build.reset_mock()
            with self.assertRaises(ValueError):
                load_visual_checkpoint("mock.pt")
            build.assert_not_called()

    def test_checkpoint_rejects_modified_resource_report_bytes(self):
        checkpoint, _ = checkpoint_fixture()
        checkpoint["resource_report_text"] += " "
        with patch("learning_vision.torch.load", return_value=checkpoint), \
             patch("learning_vision.build_visual_policy") as build:
            with self.assertRaises(ValueError):
                load_visual_checkpoint("mock.pt")
            build.assert_not_called()

    def test_resource_gate_rejects_partial_probe_and_memory_or_config_mismatch(self):
        checkpoint, resource = checkpoint_fixture()
        for mutation in ("prefix", "peak", "model"):
            bad = json.loads(json.dumps(resource))
            if mutation == "prefix":
                bad["attempts"][0]["steps"] = 4
            elif mutation == "peak":
                bad["attempts"][0]["memory_after"]["peak_reserved_mib"] = 3200.01
            else:
                bad["model_spec"]["dim_model"] = 128
            checkpoint["resource_report_text"] = json.dumps(bad)
            checkpoint["resource_report_sha256"] = hashlib.sha256(checkpoint["resource_report_text"].encode()).hexdigest()
            with patch("learning_vision.torch.load", return_value=checkpoint), \
                 patch("learning_vision.build_visual_policy") as build:
                with self.assertRaises(ValueError):
                    load_visual_checkpoint("mock.pt")
                build.assert_not_called()

    def test_rgb_tensor_is_chw_and_same_scaling(self):
        image = np.zeros((1, 128, 128, 3), dtype=np.uint8)
        image[0, 5, 6] = [255, 128, 0]
        result = rgb_tensor(image, "cpu")
        self.assertEqual(tuple(result.shape), (1, 3, 128, 128))
        self.assertEqual(result.dtype, torch.float32)
        np.testing.assert_allclose(result[0, :, 5, 6].numpy(), [1., 128 / 255, 0.])
        with self.assertRaises(ValueError):
            rgb_tensor(image.astype(np.float32), "cpu")

    def test_invalid_label_gap_and_episode_end_stop_chunks(self):
        result = segment_lengths([0, 0, 0, 0, 1, 1], [0, 1, 3, 4, 0, 1])
        np.testing.assert_array_equal(result, [2, 1, 2, 1, 2, 1])

    def test_arm_delta_uses_current_anchor_and_jaw_stays_absolute(self):
        norm = normalizer()
        anchor = np.array([1., 2., 3., 4., 5., .7])
        targets = np.array([[1.1, 2.1, 3.1, 4.1, 5.1, .015],
                            [1.2, 2.2, 3.2, 4.2, 5.2, .5]])
        encoded = norm.normalize_actions(targets, anchor)
        np.testing.assert_allclose(encoded[:, :5], [[.1] * 5, [.2] * 5])
        np.testing.assert_allclose(encoded[:, 5], [.015, .5])
        np.testing.assert_allclose(norm.decode_actions(encoded, anchor), targets, atol=1e-7)

    def test_runner_rejects_privileged_inputs_even_when_actions_are_cached(self):
        policy = DummyPolicy()
        runner = VisionPolicyRunner(policy, normalizer(), {"gripper_labels_rad": [.015, .5]}, "cpu", 16)
        obs = {STATE: np.array([1., 2., 3., 4., 5., .7]),
               IMAGE: np.zeros((128, 128, 3), dtype=np.uint8)}
        raw, command = runner.predict(obs)
        np.testing.assert_array_equal(raw[:5], obs[STATE][:5])
        self.assertEqual(command[5], .015)
        obs2 = {**obs, STATE: np.array([9., 9., 9., 9., 9., .5])}
        raw2, _ = runner.predict(obs2)
        np.testing.assert_array_equal(raw2[:5], obs[STATE][:5])
        self.assertEqual(policy.calls, 1)
        for forbidden in ("observation.environment_state", "time_s", "stage"):
            with self.assertRaises(ValueError):
                runner.predict({**obs, forbidden: 0})

    def test_normalizer_has_no_environment_statistics(self):
        states = np.ones((4, 6))
        actions = states.copy()
        actions[:, 5] = [.015, .5, .015, .5]
        norm = VisionNormalizer.fit(states, actions)
        self.assertEqual(set(norm.stats), {STATE, ACTION})
        with self.assertRaises(ValueError):
            VisionNormalizer({**norm.stats, "observation.environment_state": {"mean": [0], "std": [1]}})

    def test_render_capture_detects_integration_mutation(self):
        data = SimpleNamespace(qpos=np.zeros(13), qvel=np.zeros(12), ctrl=np.zeros(6),
                               qacc_warmstart=np.zeros(12), time=1.)
        class FakeRenderer:
            def update_scene(self, data, camera):
                pass
            def render(self):
                return np.ones((128, 128, 3), dtype=np.uint8)
        image = capture_rgb(FakeRenderer(), object(), data)
        self.assertEqual(image.dtype, np.uint8)
        class MutatingRenderer(FakeRenderer):
            def update_scene(self, data, camera):
                data.qacc_warmstart[0] = 1.
        with self.assertRaises(RuntimeError):
            capture_rgb(MutatingRenderer(), object(), data)

    def test_raw64_observation_comparison_has_no_tolerance(self):
        episode = {STATE: np.zeros((1, 6)), "observation.environment_state": np.zeros((1, 30)),
                   "timestamp": np.array([1.])}
        obs = {STATE: np.zeros(6), "observation.environment_state": np.zeros(30), "time_s": 1.}
        assert_exact_observation(obs, episode, 0)
        obs[STATE][0] = 1e-15
        with self.assertRaises(RuntimeError):
            assert_exact_observation(obs, episode, 0)

    def test_visual_dataset_filters_invalid_rows_and_detects_shifted_images(self):
        from learning_data import EpisodeRecorder
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "visual.h5"
            meta = {"control_period_s": .02, "physics_dt_s": .002, "seed": 0,
                    "model_sha256": "0" * 64, "scene_configuration": {}}
            recorder = EpisodeRecorder(path, meta)
            for index in range(4):
                before = {STATE: np.full(6, index * .01), "observation.environment_state": np.zeros(30), "time_s": index * .02}
                after = {STATE: np.full(6, (index + 1) * .01), "observation.environment_state": np.zeros(30), "time_s": (index + 1) * .02}
                action = np.r_[np.zeros(5), .5 if index == 3 else .015]
                recorder.append(before, action if index != 1 else None, action, after,
                                index != 1, "test-only", index == 1)
            recorder.finalize({"passed": True})
            with h5py.File(path, "a") as archive:
                archive.attrs["vision_format"] = "so101-synchronized-rgb-v1"
                archive.attrs["vision_complete"] = True
                archive.attrs["vision_raw64_exact"] = True
                archive.attrs["source_raw_sha256"] = "1" * 64
                archive.attrs["camera_json"] = json.dumps(CameraSpec().to_dict())
                archive.create_dataset(IMAGE, data=np.stack([np.full((128, 128, 3), i, np.uint8) for i in range(4)]))
                archive.create_dataset("image_timestamp", data=archive["timestamp"][:])
                archive.create_dataset("image_frame_index", data=archive["frame_index"][:])
            dataset = VisionDataset([path])
            try:
                self.assertEqual(len(dataset), 3)
                np.testing.assert_array_equal(dataset.frames, [0, 2, 3])
                np.testing.assert_array_equal(dataset.lengths, [1, 2, 1])
                batch = dataset.batch([0, 1], "cpu")
                self.assertTrue(batch["action_is_pad"][0, 1:].all())
                self.assertFalse(batch["action_is_pad"][1, :2].any())
                self.assertEqual(float(batch[IMAGE][1, 0, 0, 0]), np.float32(2 / 255))
            finally:
                dataset.close()
            with h5py.File(path, "a") as archive:
                archive["image_timestamp"][0] = .01
            with self.assertRaises(ValueError):
                VisionDataset([path])

    def test_safety_failure_not_overridden_by_successful_monitor_snapshot(self):
        class SafetyStop(RuntimeError):
            pass
        class Cell:
            def __init__(self, *args):
                self.baseline_z = .01
                self.model = object()
                self.data = object()
            def reset(self):
                return {STATE: np.zeros(6), "time_s": 1.}
            def step(self, action):
                raise SafetyStop("mock safety stop")
        class Monitor:
            def __init__(self, baseline):
                pass
            def report(self):
                return {"passed": True, "safety_stop": False, "failure_reason": None}
        fake_env = SimpleNamespace(StateWorkcell=Cell, PhysicalTaskMonitor=Monitor)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            ref, checkpoint = output / "ref.h5", output / "policy.pt"
            ref.write_bytes(b"mock")
            checkpoint.write_bytes(b"mock")
            meta = {"model_sha256": "0" * 64, "control_period_s": .02, "physics_dt_s": .002,
                    "scene_configuration": {},
                    "resource_report_sha256": "2" * 64,
                    "camera": CameraSpec().to_dict(), "gripper_labels_rad": [.015, .5]}
            args = SimpleNamespace(dataset=[ref], checkpoint=checkpoint, device="cpu", source=output / "model.xml",
                                   output=output, execute_chunk_steps=16, max_wall_s=120., max_simulation_s=90.)
            fake_renderer = SimpleNamespace(close=lambda: None)
            with patch.dict("sys.modules", {"learning_env": fake_env}), \
                 patch("learning_data.load_episode", return_value={"eligible_for_training": True, "metadata": meta}), \
                 patch("run_vision_learning.load_visual_checkpoint", return_value=(DummyPolicy(), normalizer(), meta)), \
                 patch("run_vision_learning.make_renderer", return_value=(fake_renderer, object())), \
                 patch("run_vision_learning.capture_rgb", return_value=np.zeros((128, 128, 3), np.uint8)):
                report = evaluate(args)
            self.assertFalse(report["passed"])
            self.assertTrue(report["physical_acceptance"]["passed"])
            self.assertTrue(report["safety_stop"])
            self.assertEqual(report["failure_reason"], "safety_stop")
            self.assertTrue((output / "policy-transitions.npz").is_file())
            self.assertTrue((output / "report.json").is_file())


if __name__ == "__main__":
    unittest.main()
