"""CPU-only contracts for real-row local balancing; no model or GPU work."""
from __future__ import annotations

from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import DEFAULT, MagicMock, patch

import numpy as np
import torch

from learning_vision import (IMAGE, STATE, local_balance_groups, local_balance_sampling_metadata,
                             local_balance_sampling_order, startup_sampling_order)
import run_vision_learning as runner


def local_fixture():
    """Two real starts, 300 real settled rows and eight untouched retreat rows."""
    states = np.zeros((310, 6), dtype=np.float64)
    states[1, 0] = .001
    states[2:302, 0] = .0001
    states[302:, 0] = .002
    frames = np.r_[0, 1, np.arange(2050, 2350), np.arange(50, 58)].astype(np.int64)
    episodes = np.zeros(310, dtype=np.int64)
    stages = np.array(["approach"] * 2 + ["settle"] * 300 + ["retreat"] * 8)
    return states, frames, episodes, stages


class LocalBalanceGroupingTests(unittest.TestCase):
    def test_closed_radius_uses_all_six_axes_and_raw_frame_stage_intersection(self):
        states = np.zeros((9, 6), dtype=np.float64)
        states[1, 0] = .01
        states[2, 0] = np.nextafter(.01, np.inf)
        states[3, 5] = .01
        states[4, :2] = .008
        states[7, 0] = -.01
        frames = np.array([0, 49, 2, 3, 4, 50, 49, 50, 0], dtype=np.int64)
        episodes = np.array([0] * 8 + [1], dtype=np.int64)
        stages = np.array(["approach"] * 6 + ["settle", "settle", "approach"])
        originals = [x.copy() for x in (states, frames, episodes, stages)]
        for array in (states, frames, episodes, stages):
            array.flags.writeable = False
        result = local_balance_groups(states, frames, episodes, stages)
        np.testing.assert_array_equal(result, [1, 1, 0, 1, 0, 0, 0, 2, 1])
        self.assertEqual(result.dtype, np.dtype(np.int8))
        for original, actual in zip(originals, (states, frames, episodes, stages)):
            np.testing.assert_array_equal(actual, original)

    def test_anchor_is_episode_zero_raw_zero_not_first_row(self):
        values = local_fixture()
        expected = local_balance_groups(*values)
        permutation = np.r_[np.arange(5, 310), np.arange(5)]
        shuffled = local_balance_groups(*(value[permutation] for value in values))
        np.testing.assert_array_equal(shuffled, expected[permutation])

    def test_anchor_must_exist_exactly_once(self):
        for condition in ("absent", "duplicate"):
            states, frames, episodes, stages = local_fixture()
            if condition == "absent":
                episodes[0] = 1
            else:
                frames[1] = 0
            with self.subTest(condition=condition), self.assertRaises(ValueError):
                local_balance_groups(states, frames, episodes, stages)

    def test_empty_local_side_is_rejected(self):
        for condition in ("startup", "settle"):
            states, frames, episodes, stages = local_fixture()
            stages[stages == ("approach" if condition == "startup" else "settle")] = "retreat"
            with self.subTest(condition=condition), self.assertRaises(ValueError):
                local_balance_groups(states, frames, episodes, stages)

    def test_malformed_or_nonfinite_observations_are_rejected(self):
        states, frames, episodes, stages = local_fixture()
        bad_states = [states[:, :5], np.c_[states, np.zeros(len(states))],
                      states[0], states[:-1], states.astype(complex)]
        # Complex q has no physical interpretation even if its imaginary part is zero.
        for value in (np.nan, np.inf, -np.inf):
            bad = states.copy()
            bad[2, 5] = value
            bad_states.append(bad)
        for index, bad in enumerate(bad_states):
            with self.subTest(index=index), self.assertRaises(ValueError):
                local_balance_groups(bad, frames, episodes, stages)

    def test_malformed_index_and_stage_arrays_are_rejected(self):
        values = local_fixture()
        for slot in (1, 2):
            for kind in ("short", "matrix", "float", "negative", "boolean"):
                altered = list(values)
                original = values[slot]
                if kind == "short":
                    bad = original[:-1]
                elif kind == "matrix":
                    bad = original[:, None]
                elif kind == "float":
                    bad = original.astype(np.float64)
                elif kind == "boolean":
                    bad = original.astype(bool)
                else:
                    bad = original.copy()
                    bad[2] = -1
                altered[slot] = bad
                with self.subTest(slot=slot, kind=kind), self.assertRaises(ValueError):
                    local_balance_groups(*altered)
        for bad in (values[3][:-1], values[3][:, None]):
            with self.subTest(stages_shape=bad.shape), self.assertRaises(ValueError):
                local_balance_groups(*values[:3], bad)


class LocalBalanceOrderTests(unittest.TestCase):
    def setUp(self):
        self.states, self.frames, self.episodes, self.stages = local_fixture()
        self.groups = local_balance_groups(self.states, self.frames, self.episodes, self.stages)
        self.base = startup_sampling_order(self.frames, np.random.default_rng(0), 5)

    def test_equal_155_mass_and_exact_nonlocal_slots_without_mutating_inputs(self):
        base_before, groups_before = self.base.copy(), self.groups.copy()
        self.base.flags.writeable = self.groups.flags.writeable = False
        result = local_balance_sampling_order(self.base, self.groups, np.random.default_rng(37))
        self.assertEqual(result.shape, self.base.shape)
        self.assertEqual(len(result), 318)
        np.testing.assert_array_equal(np.bincount(self.groups[result], minlength=3), [8, 155, 155])
        nonlocal_slots = self.groups[self.base] == 0
        np.testing.assert_array_equal(result[nonlocal_slots], self.base[nonlocal_slots])
        self.assertFalse(np.any(self.groups[result[~nonlocal_slots]] == 0))
        np.testing.assert_array_equal(self.base, base_before)
        np.testing.assert_array_equal(self.groups, groups_before)

    def test_within_group_coverage_is_balanced_and_large_side_has_no_replacement(self):
        local_rng = np.random.default_rng(21)
        for epoch in range(5):
            with self.subTest(epoch=epoch):
                result = local_balance_sampling_order(self.base, self.groups, local_rng)
                counts = np.bincount(result, minlength=len(self.groups))
                self.assertEqual(sorted(counts[self.groups == 1].tolist()), [77, 78])
                self.assertEqual(int(np.count_nonzero(counts[self.groups == 2])), 155)
                self.assertTrue(np.all(counts[self.groups == 2] <= 1))

    def test_seed_reproducibility_and_legacy_rng_independence_across_epochs(self):
        legacy, reference = np.random.default_rng(17), np.random.default_rng(17)
        local_a, local_b = np.random.default_rng(23), np.random.default_rng(23)
        for _ in range(3):
            base_a = startup_sampling_order(self.frames, legacy, 5)
            base_b = startup_sampling_order(self.frames, reference, 5)
            np.testing.assert_array_equal(base_a, base_b)
            np.testing.assert_array_equal(
                local_balance_sampling_order(base_a, self.groups, local_a),
                local_balance_sampling_order(base_b, self.groups, local_b))
        np.testing.assert_array_equal(legacy.integers(0, 2**31, 20),
                                      reference.integers(0, 2**31, 20))

    def test_invalid_orders_or_groups_fail_before_consuming_rng(self):
        bad_cases = [(self.base[:-1], self.groups),  # remove one local slot: odd mass
                     (self.base[:, None], self.groups),
                     (self.base.astype(np.float64), self.groups),
                     (np.r_[-1, self.base[1:]], self.groups),
                     (np.r_[len(self.groups), self.base[1:]], self.groups),
                     (self.base, self.groups[:, None]),
                     (self.base, self.groups.astype(float)),
                     (self.base, np.where(self.groups == 2, 3, self.groups)),
                     (self.base, np.where(self.groups == 2, 0, self.groups))]
        # Explicitly remove a local slot; the last shuffled slot need not be local.
        local_slot = int(np.flatnonzero(self.groups[self.base] != 0)[0])
        bad_cases[0] = (np.delete(self.base, local_slot), self.groups)
        for index, (base, groups) in enumerate(bad_cases):
            rng, control = np.random.default_rng(4), np.random.default_rng(4)
            with self.subTest(index=index), self.assertRaises(ValueError):
                local_balance_sampling_order(base, groups, rng)
            np.testing.assert_array_equal(rng.random(8), control.random(8))

    def test_metadata_reports_real_rows_and_conserved_local_pool(self):
        metadata = local_balance_sampling_metadata(self.frames, self.episodes, self.groups, weight=5)
        for key, value in {"startup_rows": 2, "settle_rows": 300,
                           "base_startup_slots": 10, "base_settle_slots": 300,
                           "pool_slots": 310, "target_slots_per_group": 155,
                           "radius_rad": .01}.items():
            self.assertEqual(metadata[key], value, key)
        self.assertEqual(metadata["startup_indices"], [0, 1])
        self.assertEqual(metadata["settle_indices"], list(range(2, 302)))
        json.dumps(metadata, allow_nan=False)


class LocalBalanceDispatchTests(unittest.TestCase):
    def test_flag_requires_fit_weight_five_before_directory_or_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            cases = [("export", 1), ("microbenchmark", 1), ("evaluate", 1),
                     ("export", 5), ("fit", 1)]
            for index, (stage, weight) in enumerate(cases):
                output = Path(tmp) / str(index) / "output"
                argv = [stage, "--dataset", "mock.h5", "--output", str(output),
                        "--local-balance", "--startup-weight", str(weight),
                        "--resource-report", "mock.json", "--camera-reviewed"]
                if stage == "evaluate":
                    argv += ["--checkpoint", "mock.pt"]
                with (self.subTest(stage=stage, weight=weight), patch.multiple(runner,
                        export=DEFAULT, microbenchmark=DEFAULT, fit=DEFAULT, evaluate=DEFAULT) as dispatch,
                        redirect_stderr(StringIO()), self.assertRaises(SystemExit) as raised):
                    runner.main(argv)
                self.assertEqual(raised.exception.code, 2)
                self.assertFalse(output.parent.exists())
                for function in dispatch.values():
                    function.assert_not_called()

    def test_default_is_off_and_fit_explicit_flag_is_passed(self):
        with tempfile.TemporaryDirectory() as tmp:
            for enabled in (False, True):
                output = Path(tmp) / str(enabled)
                argv = ["fit", "--dataset", "mock.h5", "--output", str(output),
                        "--startup-weight", "5", "--resource-report", "mock.json", "--camera-reviewed"]
                if enabled:
                    argv += ["--local-balance"]
                with self.subTest(enabled=enabled), patch.object(runner, "fit",
                        return_value={"status": "completed_diagnostic"}) as fit, redirect_stdout(StringIO()):
                    self.assertEqual(runner.main(argv), 0)
                    self.assertIs(fit.call_args.args[0].local_balance, enabled)


class LocalBalanceFitAccountingTests(unittest.TestCase):
    def mock_fit(self, *, snapshot_step=0, snapshot_delay=0., max_steps=4):
        """Run production accounting with fake loss/optimizer; no CUDA calls escape."""
        dataset = MagicMock()
        dataset.__len__.return_value = 5
        dataset.frames = np.array([0, 1, 50, 51, 161], dtype=np.int64)
        dataset.episodes = np.zeros(5, dtype=np.int64)
        dataset.states = np.zeros((5, 6), dtype=np.float64)
        dataset.stages = np.array(["approach", "approach", "settle", "settle", "retreat"])
        dataset.lengths = np.array([16, 15, 3, 1, 7], dtype=np.int64)
        dataset.camera, dataset.visual_hashes, dataset.raw_hashes = {}, ["v"], ["r"]
        stats = {STATE: {"mean": [1.] * 6, "std": [2.] * 6}}
        dataset.normalizer = SimpleNamespace(stats=stats)
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
        policy.cpu.return_value = policy.eval.return_value = policy
        policy.predict_action_chunk.return_value = torch.zeros(1, 16, 6)
        loss.detach.return_value = .1
        source = {"learning_vision.py": "1" * 64, "run_vision_learning.py": "2" * 64}
        clock, checkpoints = [0.], []
        def save(checkpoint, path):
            # Keep actual references: a later mutation must not rewrite a past snapshot.
            checkpoints.append((Path(path).name, checkpoint))
            if Path(path).name.startswith("policy-step-"):
                clock[0] += snapshot_delay
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            resource = Path(tmp) / "resource.json"
            resource.write_text('{"resource":"mock-only"}', encoding="utf8")
            args = SimpleNamespace(dataset=[Path("mock.h5")], resource_report=resource,
                output=Path(tmp), device="cuda", max_wall_s=120., max_steps=max_steps,
                max_epochs=1, seed=0, startup_weight=5, local_balance=True,
                snapshot_step=snapshot_step)
            replacements = [patch.object(runner, "VisionDataset", return_value=dataset),
                patch.object(runner, "validate_resource_report", return_value=4),
                patch.object(runner, "build_visual_policy", return_value=policy),
                patch.object(runner, "load_visual_checkpoint", return_value=(policy, dataset.normalizer, {})),
                patch.object(runner, "gpu_memory", return_value={}),
                patch.object(runner, "source_hashes", return_value=source),
                patch.object(runner, "sha256", return_value="a" * 64),
                patch.object(runner, "write_json"),
                patch.object(runner.time, "perf_counter", side_effect=lambda: clock[0]),
                patch.object(runner.torch, "save", side_effect=save),
                patch.object(runner.torch, "set_num_threads"),
                patch.object(runner.torch, "manual_seed"),
                patch.object(runner.torch, "isfinite", return_value=True),
                patch.object(runner.torch.optim, "Adam", return_value=optimizer),
                patch.object(runner.torch.nn.utils, "clip_grad_norm_", return_value=0.),
                patch.object(runner.torch.cuda, "is_available", return_value=True)]
            for replacement in replacements:
                stack.enter_context(replacement)
            for name in ("reset_peak_memory_stats", "empty_cache", "synchronize"):
                stack.enter_context(patch.object(runner.torch.cuda, name))
            for name in ("max_memory_allocated", "max_memory_reserved"):
                stack.enter_context(patch.object(runner.torch.cuda, name, return_value=0))
            report = runner.fit(args)
        dataset.close.assert_called_once()
        self.assertEqual(report["status"], "completed_diagnostic", report.get("error"))
        return report, selections, dict(checkpoints), dataset, source

    def test_enabled_fit_counts_actual_chunk_starts_and_action_slots_preserving_normalization(self):
        report, selections, checkpoints, dataset, _ = self.mock_fit()
        sampler = report["training_sampler"]
        self.assertEqual(report["training_steps"], 4)
        self.assertEqual(sampler["completed_pool_passes"], 1)
        self.assertEqual((sampler["pool_len"], sampler["chunk_start_draw_count"]), (13, 13))
        local = sampler["local_balance"]
        self.assertEqual(local["chunk_start_draw_counts"], [1, 6, 6])
        self.assertEqual(local["valid_action_slot_counts"], [7, 93, 12])
        actual_counts = np.bincount(np.concatenate(selections), minlength=5)
        np.testing.assert_array_equal(local["row_draw_counts"], actual_counts)
        self.assertEqual(local["row_draw_counts"], [3, 3, 3, 3, 1])
        self.assertEqual(report["normalization"], dataset.normalizer.stats)
        self.assertEqual(checkpoints["policy.pt"]["normalization"], dataset.normalizer.stats)
        self.assertEqual(report["normalization"][STATE], {"mean": [1.] * 6, "std": [2.] * 6})
        self.assertEqual(checkpoints["policy.pt"]["training_sampler"], sampler)

    def test_snapshot_is_source_bound_and_independent_and_its_time_counts_toward_budget(self):
        report, selections, checkpoints, _, source = self.mock_fit(snapshot_step=1, max_steps=2)
        self.assertEqual(set(checkpoints), {"policy-step-1.pt", "policy.pt"})
        snapshot, final = checkpoints["policy-step-1.pt"], checkpoints["policy.pt"]
        self.assertEqual((snapshot["training_steps"], final["training_steps"]), (1, 2))
        self.assertEqual(snapshot["source_sha256"], source)
        self.assertEqual(snapshot["resource_report_text"], '{"resource":"mock-only"}')
        self.assertEqual(len(snapshot["resource_report_sha256"]), 64)
        self.assertEqual(snapshot["training_sampler"]["chunk_start_draw_count"], 4)
        self.assertEqual(final["training_sampler"]["chunk_start_draw_count"], 8)
        self.assertIsNot(snapshot["training_sampler"], final["training_sampler"])
        self.assertIsNot(snapshot["training_sampler"]["local_balance"],
                         final["training_sampler"]["local_balance"])
        np.testing.assert_array_equal(snapshot["training_sampler"]["local_balance"]["row_draw_counts"],
                                      np.bincount(selections[0], minlength=5))
        final["training_sampler"]["local_balance"]["row_draw_counts"][0] += 100
        self.assertLess(snapshot["training_sampler"]["local_balance"]["row_draw_counts"][0], 100)
        self.assertEqual(report["snapshot"]["status"], "saved")
        self.assertTrue(report["snapshot"]["wall_budget_includes_snapshot_save"])
        budget_report, budget_selections, _, _, _ = self.mock_fit(snapshot_step=1, snapshot_delay=121.)
        self.assertEqual((budget_report["training_steps"], len(budget_selections)), (1, 1))
        self.assertEqual(budget_report["stop_reason"], "optimization_wall_time_limit")
        self.assertEqual(budget_report["snapshot"]["save_s"], 121.)


if __name__ == "__main__":
    unittest.main()
