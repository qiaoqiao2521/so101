"""CPU sampler/dispatch checks; policy, optimizer and CUDA work are mocked."""
from __future__ import annotations

from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import DEFAULT, MagicMock, patch

import h5py
import numpy as np
import torch

from learning_data import EpisodeRecorder
from learning_vision import (ACTION, IMAGE, STATE, CameraSpec, VisionDataset,
                             startup_sampling_metadata, startup_sampling_order)
import run_vision_learning as runner


class StartupSamplingTests(unittest.TestCase):
    def test_default_keeps_each_old_epoch_and_subsequent_rng_call_exact(self):
        frames = np.array([0, 49, 50, 450, 161], dtype=np.int64)
        for seed in (0, 19):
            for kwargs in ({}, {"weight": 1}):
                with self.subTest(seed=seed, kwargs=kwargs):
                    old, new = np.random.default_rng(seed), np.random.default_rng(seed)
                    for _ in range(3):
                        np.testing.assert_array_equal(
                            startup_sampling_order(frames, new, **kwargs),
                            old.permutation(len(frames)))
                    np.testing.assert_array_equal(new.integers(0, 2**31, 17),
                                                  old.integers(0, 2**31, 17))

    def test_fivefold_uses_raw_frame_boundary_and_preserves_inputs(self):
        frames = np.array([0, 49, 50, 450, 0, 50, 161], dtype=np.int64)
        episodes = np.array([0, 0, 0, 0, 1, 1, 2], dtype=np.int64)
        original_frames, original_episodes = frames.copy(), episodes.copy()
        frames.flags.writeable = episodes.flags.writeable = False
        first = startup_sampling_order(frames, np.random.default_rng(7), 5)
        second = startup_sampling_order(frames, np.random.default_rng(7), 5)
        np.testing.assert_array_equal(first, second)
        np.testing.assert_array_equal(np.bincount(first, minlength=7), [5, 5, 1, 1, 5, 1, 1])
        self.assertEqual(first.dtype.kind, "i")
        metadata = startup_sampling_metadata(frames, episodes, 5)
        self.assertEqual(metadata["mask"], "label_valid && original_raw_frame_index < 50")
        self.assertEqual(metadata["sampling_unit"], "eligible_chunk_start")
        self.assertEqual(metadata["raw_frame_threshold"], 50)
        self.assertEqual(metadata["weight"], 5)
        self.assertEqual(metadata["unique_rows"], 7)
        self.assertEqual(metadata["startup_rows"], 3)
        self.assertEqual(metadata["pool_len"], 19)
        self.assertEqual(metadata["theoretical_startup_fraction"], 15 / 19)
        self.assertEqual(metadata["per_episode"], [
            {"episode_id": 0, "unique_rows": 4, "startup_rows": 2, "pool_len": 12},
            {"episode_id": 1, "unique_rows": 2, "startup_rows": 1, "pool_len": 6},
            {"episode_id": 2, "unique_rows": 1, "startup_rows": 0, "pool_len": 1}])
        self.assertIn("not a unique-row pass", metadata["epoch_semantics"])
        json.dumps(metadata, allow_nan=False)
        np.testing.assert_array_equal(frames, original_frames)
        np.testing.assert_array_equal(episodes, original_episodes)

    def test_no_startup_keeps_old_order_and_rng_even_with_weight_five(self):
        frames = np.array([50, 51, 161, 450], dtype=np.int64)
        old, new = np.random.default_rng(13), np.random.default_rng(13)
        for _ in range(2):
            np.testing.assert_array_equal(startup_sampling_order(frames, new, 5),
                                          old.permutation(4))
        np.testing.assert_array_equal(new.random(11), old.random(11))
        metadata = startup_sampling_metadata(frames, np.zeros(4, dtype=np.int64), 5)
        self.assertEqual(metadata["pool_len"], 4)
        self.assertEqual(metadata["startup_rows"], 0)
        self.assertEqual(metadata["theoretical_startup_fraction"], 0.)

    def test_bad_frames_or_weights_are_rejected_before_rng_consumption(self):
        bad_frames = (np.array([], dtype=np.int64), np.array([[0, 1]]),
                      np.array([0, -1]), np.array([0., 1.]), np.array([True, False]),
                      np.array(0), np.array([0, "1"]), np.array([np.nan]),
                      np.array([np.inf]))
        for frames in bad_frames:
            with self.subTest(frames=frames):
                rng, control = np.random.default_rng(11), np.random.default_rng(11)
                with self.assertRaises(ValueError):
                    startup_sampling_order(frames, rng, 5)
                with self.assertRaises(ValueError):
                    startup_sampling_metadata(frames, np.zeros(2, dtype=np.int64), 5)
                np.testing.assert_array_equal(rng.random(7), control.random(7))
        for weight in (True, np.bool_(False), 0, -1, 2, 1., 5., "5", None, np.nan):
            with self.subTest(weight=weight):
                rng, control = np.random.default_rng(11), np.random.default_rng(11)
                with self.assertRaises(ValueError):
                    startup_sampling_order(np.array([0, 50]), rng, weight)
                with self.assertRaises(ValueError):
                    startup_sampling_metadata(np.array([0, 50]), np.array([0, 0]), weight)
                np.testing.assert_array_equal(rng.random(7), control.random(7))

    def test_metadata_rejects_malformed_episode_indices(self):
        for episodes in (np.array([], dtype=np.int64), np.array([0]),
                         np.array([[0, 1]]), np.array([0, -1]),
                         np.array([0., 1.]), np.array([False, True])):
            with self.subTest(episodes=episodes), self.assertRaises(ValueError):
                startup_sampling_metadata(np.array([0, 50]), episodes, 5)

    def test_real_dataset_filtering_keeps_raw_indices_and_chunk_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "visual.h5"
            recorder = EpisodeRecorder(path, {"control_period_s": .02, "physics_dt_s": .002,
                "seed": 0, "model_sha256": "0" * 64, "scene_configuration": {}})
            valid = {0, 48, 49, 50, 52}
            for index in range(53):
                before = {STATE: np.full(6, index * .01),
                          "observation.environment_state": np.zeros(30), "time_s": index * .02}
                after = {STATE: np.full(6, (index + 1) * .01),
                         "observation.environment_state": np.zeros(30), "time_s": (index + 1) * .02}
                action = np.r_[np.arange(5) * .01 + index * .001, .5 if index == 52 else .015]
                recorder.append(before, action if index in valid else None, action, after,
                                index in valid, "test-only", False)
            recorder.finalize({"passed": True})
            with h5py.File(path, "a") as archive:
                archive.attrs["vision_format"] = "so101-synchronized-rgb-v1"
                archive.attrs["vision_complete"] = True
                archive.attrs["vision_raw64_exact"] = True
                archive.attrs["source_raw_sha256"] = "1" * 64
                archive.attrs["camera_json"] = json.dumps(CameraSpec().to_dict())
                archive.create_dataset(IMAGE, data=np.stack([
                    np.full((128, 128, 3), i, np.uint8) for i in range(53)]))
                archive.create_dataset("image_timestamp", data=archive["timestamp"][:])
                archive.create_dataset("image_frame_index", data=archive["frame_index"][:])
            dataset = VisionDataset([path])
            try:
                np.testing.assert_array_equal(dataset.frames, [0, 48, 49, 50, 52])
                np.testing.assert_array_equal(dataset.lengths, [1, 3, 2, 1, 1])
                baseline = dataset.batch([1, 3, 4], "cpu")
                arrays = [a.copy() for a in (dataset.frames, dataset.episodes,
                                             dataset.lengths, dataset.states, dataset.actions)]
                order = startup_sampling_order(dataset.frames, np.random.default_rng(0), 5)
                np.testing.assert_array_equal(np.bincount(order, minlength=5), [5, 5, 5, 1, 1])
                metadata = startup_sampling_metadata(dataset.frames, dataset.episodes, 5)
                self.assertEqual((metadata["unique_rows"], metadata["startup_rows"], metadata["pool_len"]),
                                 (5, 3, 17))
                repeated = dataset.batch([1, 1, 3, 4], "cpu")
                for key in (STATE, IMAGE, ACTION, "action_is_pad"):
                    self.assertTrue(torch.equal(repeated[key][0], baseline[key][0]))
                    self.assertTrue(torch.equal(repeated[key][1], baseline[key][0]))
                    self.assertTrue(torch.equal(repeated[key][2:], baseline[key][1:]))
                self.assertFalse(repeated["action_is_pad"][0, :3].any())
                self.assertTrue(repeated["action_is_pad"][0, 3:].all())
                self.assertTrue(repeated["action_is_pad"][2:, 1:].all())
                for before, after in zip(arrays, (dataset.frames, dataset.episodes,
                                                  dataset.lengths, dataset.states, dataset.actions)):
                    np.testing.assert_array_equal(before, after)
            finally:
                dataset.close()


class StartupDispatchTests(unittest.TestCase):
    def test_nonfit_weight_five_rejected_before_directory_or_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            for stage in ("export", "microbenchmark", "evaluate"):
                output = Path(tmp) / stage / "output"
                argv = [stage, "--dataset", "mock.h5", "--output", str(output),
                        "--device", "cpu", "--startup-weight", "5"]
                if stage == "evaluate":
                    argv += ["--checkpoint", "mock.pt"]
                with self.subTest(stage=stage), patch.multiple(runner, export=DEFAULT,
                        microbenchmark=DEFAULT, fit=DEFAULT, evaluate=DEFAULT) as stages:
                    errors = StringIO()
                    with redirect_stderr(errors), self.assertRaises(SystemExit) as raised:
                        runner.main(argv)
                    self.assertEqual(raised.exception.code, 2)
                    self.assertIn("only allowed for fit", errors.getvalue())
                    self.assertFalse(output.parent.exists())
                    for function in stages.values():
                        function.assert_not_called()

    def test_default_dispatch_and_explicit_fit_weight_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            for stage, weight in (("export", 1), ("microbenchmark", 1), ("evaluate", 1), ("fit", 5)):
                output = Path(tmp) / stage
                argv = [stage, "--dataset", "mock.h5", "--output", str(output), "--device", "cpu"]
                if stage == "evaluate":
                    argv += ["--checkpoint", "mock.pt"]
                if stage == "fit":
                    argv += ["--startup-weight", "5", "--resource-report", "mock.json", "--camera-reviewed"]
                with self.subTest(stage=stage), patch.object(runner, stage,
                        return_value={"status": "completed_diagnostic"}) as dispatch, redirect_stdout(StringIO()):
                    self.assertEqual(runner.main(argv), 0)
                    self.assertEqual(dispatch.call_args.args[0].startup_weight, weight)
                    self.assertTrue(output.is_dir())

    def test_invalid_cli_weights_do_not_create_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"
            for weight in ("0", "2", "-1", "1.0", "5.0", "True"):
                with self.subTest(weight=weight), patch.object(runner, "fit") as fit, \
                        redirect_stderr(StringIO()), self.assertRaises(SystemExit) as raised:
                    runner.main(["fit", "--dataset", "mock.h5", "--output", str(output),
                                 "--resource-report", "mock.json", "--camera-reviewed",
                                 "--startup-weight", weight])
                self.assertEqual(raised.exception.code, 2)
                fit.assert_not_called()
                self.assertFalse(output.exists())


class StartupFitAccountingTests(unittest.TestCase):
    def mock_fit(self, *, max_steps=2, max_epochs=1, wall_after_first=False, sync_failure=False):
        """Exercise only loop bookkeeping; no model, backward, optimizer or CUDA work."""
        dataset = MagicMock()
        dataset.__len__.return_value = 4
        dataset.frames = np.array([0, 49, 50, 161])
        dataset.episodes = np.zeros(4, dtype=np.int64)
        dataset.camera, dataset.visual_hashes, dataset.raw_hashes = {}, [], []
        dataset.normalizer = SimpleNamespace(stats={})
        dataset.metadata = [{"model_sha256": "0" * 64, "scene_configuration": {}}]
        dataset.gripper_labels = np.array([.015, .5])
        selections = []
        def batch(indices, device):
            if device == "cuda":
                selections.append(np.array(indices, copy=True))
            return {STATE: torch.zeros(1, 6), IMAGE: torch.zeros(1)}
        dataset.batch.side_effect = batch
        policy, optimizer, loss = MagicMock(), MagicMock(), MagicMock()
        policy.return_value = (loss, {})
        policy.parameters.return_value = []
        policy.state_dict.return_value = {}
        policy.cpu.return_value = policy
        policy.eval.return_value = policy
        policy.predict_action_chunk.return_value = torch.zeros(1, 16, 6)
        loss.detach.return_value = .1
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            resource = Path(tmp) / "resource.json"
            resource.write_text("{}", encoding="utf8")
            args = SimpleNamespace(dataset=[Path("mock.h5")], resource_report=resource,
                output=Path(tmp), device="cuda", max_wall_s=120., max_steps=max_steps,
                max_epochs=max_epochs, seed=0, startup_weight=5)
            patches = [patch.object(runner, "VisionDataset", return_value=dataset),
                patch.object(runner, "validate_resource_report", return_value=4),
                patch.object(runner, "build_visual_policy", return_value=policy),
                patch.object(runner, "load_visual_checkpoint", return_value=(policy, dataset.normalizer, {})),
                patch.object(runner, "gpu_memory", return_value={}),
                patch.object(runner, "sha256", return_value="a" * 64),
                patch.object(runner, "write_json"),
                patch.object(runner.torch, "set_num_threads"), patch.object(runner.torch, "manual_seed"),
                patch.object(runner.torch, "isfinite", return_value=True),
                patch.object(runner.torch.optim, "Adam", return_value=optimizer),
                patch.object(runner.torch.nn.utils, "clip_grad_norm_", return_value=0.)]
            for replacement in patches:
                stack.enter_context(replacement)
            saved = stack.enter_context(patch.object(runner.torch, "save"))
            stack.enter_context(patch.object(runner.torch.cuda, "is_available", return_value=True))
            for name in ("reset_peak_memory_stats", "empty_cache"):
                stack.enter_context(patch.object(runner.torch.cuda, name))
            for name in ("max_memory_allocated", "max_memory_reserved"):
                stack.enter_context(patch.object(runner.torch.cuda, name, return_value=0))
            sync = stack.enter_context(patch.object(runner.torch.cuda, "synchronize"))
            if sync_failure:
                sync.side_effect = [None, RuntimeError("mock synchronization failure")]
            stack.enter_context(patch.object(runner.time, "perf_counter",
                side_effect=lambda: 121. if wall_after_first and policy.call_count else 0.))
            report = runner.fit(args)
            checkpoint = saved.call_args.args[0] if saved.called else None
        dataset.close.assert_called_once()
        return report, selections, checkpoint, optimizer.step.call_count

    def assert_draws(self, report, completed_selections):
        sampler = report["training_sampler"]
        self.assertEqual(sampler["draw_count_scope"], "chunk starts in completed optimizer updates")
        self.assertEqual(sampler["seed"], 0)
        self.assertEqual(sampler["chunk_start_draw_count"], sum(map(len, completed_selections)))
        self.assertEqual(sampler["startup_draw_count"],
                         sum(np.count_nonzero(selection < 2) for selection in completed_selections))
        return sampler

    def test_step_limit_records_actual_draws_without_claiming_a_pool_pass(self):
        report, selections, checkpoint, updates = self.mock_fit(max_steps=2)
        self.assertEqual(report["status"], "completed_diagnostic")
        self.assertEqual((report["training_steps"], updates, report["stop_reason"]), (2, 2, "step_limit"))
        sampler = self.assert_draws(report, selections)
        self.assertEqual((sampler["chunk_start_draw_count"], sampler["pool_len"]), (8, 12))
        self.assertEqual((sampler["epoch_orders_generated"], sampler["completed_pool_passes"]), (1, 0))
        self.assertEqual(checkpoint["training_sampler"], sampler)

    def test_completed_expanded_pool_has_exact_counts(self):
        report, selections, checkpoint, updates = self.mock_fit(max_steps=3)
        self.assertEqual((report["training_steps"], updates, report["stop_reason"]), (3, 3, "epoch_limit"))
        sampler = self.assert_draws(report, selections)
        self.assertEqual((sampler["chunk_start_draw_count"], sampler["startup_draw_count"]), (12, 10))
        self.assertEqual((sampler["epoch_orders_generated"], sampler["completed_pool_passes"]), (1, 1))
        self.assertEqual(checkpoint["training_sampler"], sampler)

    def test_wall_limit_counts_only_the_completed_batch(self):
        report, selections, _, updates = self.mock_fit(max_steps=20, wall_after_first=True)
        self.assertEqual((report["training_steps"], updates, report["stop_reason"]),
                         (1, 1, "optimization_wall_time_limit"))
        sampler = self.assert_draws(report, selections)
        self.assertEqual((sampler["chunk_start_draw_count"], sampler["completed_pool_passes"]), (4, 0))

    def test_failed_synchronization_excludes_the_uncompleted_batch(self):
        report, selections, checkpoint, attempted_updates = self.mock_fit(sync_failure=True)
        self.assertEqual(report["status"], "failed")
        self.assertIn("mock synchronization failure", report["error"]["message"])
        self.assertEqual((len(selections), attempted_updates), (2, 2))
        sampler = self.assert_draws(report, selections[:1])
        self.assertEqual((sampler["chunk_start_draw_count"], sampler["completed_pool_passes"]), (4, 0))
        self.assertIsNone(checkpoint)


if __name__ == "__main__":
    unittest.main()
