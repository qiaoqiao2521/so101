"""CPU counterexamples for the explicit frozen-ACT/state-gripper composite."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

from learning_models import (ACTION, ENV_STATE, STATE, ModelSpec, StateNormalizer,
                             build_policy, load_policy_checkpoint)
from learning_gripper import (GRIPPER_CLASSES, GRIPPER_FORMAT, GripperClassifier,
                              LearnedGripperPolicy, classifier_inputs, fit_input_statistics,
                              masked_classification_loss)
from train_gripper_classifier import prepare_classifier_data, train


def rows():
    rng = np.random.default_rng(17)
    return {STATE: rng.normal(size=(6, 6)), ENV_STATE: rng.normal(size=(6, 30)),
            ACTION: np.c_[rng.normal(size=(6, 5)), [.5, .015, .5, .015, .5, .015]],
            "episode_index": np.array([0, 0, 0, 0, 1, 1]),
            "frame_index": np.array([0, 1, 3, 4, 0, 1])}


def base_fixture():
    torch.manual_seed(21)
    raw = rows()
    normalizer = StateNormalizer.fit(raw, action_encoding="arm_delta", robot_velocity_mask=True)
    spec = ModelSpec(model="act", dim_model=16, dim_feedforward=32, n_heads=4,
                     n_encoder_layers=1, n_decoder_layers=1, chunk_size=4,
                     use_vae=False, dropout=0, action_encoding="arm_delta")
    policy = build_policy(spec, "cpu").eval()
    normalized = {key: torch.from_numpy(normalizer.normalize(key, raw[key])) for key in (STATE, ENV_STATE)}
    statistics = fit_input_statistics(normalized)
    classifier = GripperClassifier(4)
    # This test fixture forces a categorical open output to distinguish it
    # from arbitrary original ACT jaw regression; it is not an execution rule.
    with torch.no_grad():
        for parameter in classifier.parameters():
            parameter.zero_()
        classifier.net[-1].bias.reshape(4, 2)[:, 1] = 1
    component = {"format": GRIPPER_FORMAT, "input_keys": [STATE, ENV_STATE],
                 "inputs_are_base_normalized_and_masked": True,
                 "architecture": {"input_width": 36, "hidden_widths": [64, 64], "chunk_size": 4, "classes": 2},
                 "classes_rad": list(GRIPPER_CLASSES), "train_dataset_sha256": ["a" * 64],
                 "input_statistics": statistics, "state_dict": classifier.state_dict()}
    return policy, normalizer, spec, normalized, component


class GripperClassifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.threads = torch.get_num_threads()
        torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.threads)

    def test_label_chunks_do_not_cross_gap_or_episode(self):
        raw = rows()
        normalizer = StateNormalizer.fit(raw, robot_velocity_mask=True)
        data, statistics = prepare_classifier_data(raw, normalizer, 4)
        self.assertEqual(data["padding"].tolist(),
                         [[False, False, True, True], [False, True, True, True],
                          [False, False, True, True], [False, True, True, True],
                          [False, False, True, True], [False, True, True, True]])
        self.assertEqual(data["labels"][0, :2].tolist(), [1, 0])
        self.assertEqual(data["labels"][2, :2].tolist(), [1, 0])
        self.assertEqual(statistics[ENV_STATE]["std"][:6], [1.] * 6)
        torch.testing.assert_close(data["inputs"][:, 6:12], torch.zeros(6, 6), rtol=0, atol=0)
        raw[ACTION][0, 5] = .25
        with self.assertRaisesRegex(ValueError, "expert jaw"):
            prepare_classifier_data(raw, normalizer, 4)

    def test_padding_has_no_loss_or_gradient(self):
        logits = torch.tensor([[[2., -1.], [1000., -1000.]]], requires_grad=True)
        labels = torch.tensor([[0, 1]], dtype=torch.long)
        padding = torch.tensor([[False, True]])
        loss = masked_classification_loss(logits, labels, padding)
        expected = torch.nn.functional.cross_entropy(logits[:, 0], labels[:, 0])
        torch.testing.assert_close(loss, expected, rtol=0, atol=0)
        loss.backward()
        self.assertEqual(int(torch.count_nonzero(logits.grad[:, 1])), 0)
        with self.assertRaisesRegex(ValueError, "no valid"):
            masked_classification_loss(logits, labels, torch.ones_like(padding))

    def test_statistics_do_not_refit_and_nonfinite_or_extra_inputs_reject(self):
        raw = rows()
        batch = {key: torch.from_numpy(raw[key].astype(np.float32)) for key in (STATE, ENV_STATE)}
        statistics = fit_input_statistics(batch)
        saved = copy.deepcopy(statistics)
        classifier_inputs({key: value + 100 for key, value in batch.items()}, statistics)
        self.assertEqual(statistics, saved)
        bad = {key: value.clone() for key, value in batch.items()}
        bad[ENV_STATE][0, 13] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite"):
            classifier_inputs(bad, statistics)
        with self.assertRaises(ValueError):
            classifier_inputs({**batch, "stage": torch.zeros(6)}, statistics)

    def test_composite_preserves_all_five_act_outputs_and_selects_first_chunk(self):
        base, normalizer, _, batch, component = base_fixture()
        with torch.no_grad():
            original = base.predict_action_chunk(batch).clone()
        composite = LearnedGripperPolicy(base, component, normalizer.stats[ACTION], ["a" * 64]).eval()
        prediction = composite.predict_action_chunk(batch)
        self.assertTrue(torch.equal(prediction[..., :5], original[..., :5]))
        torch.testing.assert_close(composite.select_action(batch), prediction[:, 0], rtol=0, atol=0)
        decoded = normalizer.action_radians(prediction, anchor=rows()[STATE])
        np.testing.assert_allclose(decoded[..., 5], .5, atol=1e-7)
        self.assertTrue(all(parameter.grad is None for parameter in base.parameters()))
        composite.reset()

    def test_fresh_adam_classifier_training_never_changes_act(self):
        base, normalizer, _, batch, component = base_fixture()
        composite = LearnedGripperPolicy(base, component, normalizer.stats[ACTION], ["a" * 64])
        original = {name: value.clone() for name, value in base.state_dict().items()}
        prior_head = {name: value.clone() for name, value in composite.classifier.state_dict().items()}
        inputs = classifier_inputs(batch, component["input_statistics"])
        labels = torch.zeros(6, 4, dtype=torch.long)
        padding = torch.zeros(6, 4, dtype=torch.bool)
        optimizer = torch.optim.Adam(composite.classifier.parameters(), lr=.01)
        for _ in range(3):
            optimizer.zero_grad(set_to_none=True)
            loss = masked_classification_loss(composite.classifier(inputs), labels, padding)
            loss.backward()
            optimizer.step()
        self.assertTrue(all(torch.equal(value, original[name]) for name, value in base.state_dict().items()))
        self.assertTrue(any(not torch.equal(value, prior_head[name]) for name, value in composite.classifier.state_dict().items()))

    def test_optional_checkpoint_roundtrip_and_training_hash_counterexample(self):
        base, normalizer, spec, batch, component = base_fixture()
        metadata = {"format": "so101-state-policy-v1", "model_spec": spec.to_dict(),
                    "normalization": normalizer.stats, "state_dict": base.state_dict(),
                    "action_encoding": "arm_delta", "normalization_options": {"robot_velocity_mask": True},
                    "train_dataset_sha256": ["a" * 64], "learned_gripper_classifier": component}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.pt"
            torch.save(metadata, path)
            restored, restored_normalizer, _ = load_policy_checkpoint(str(path), "cpu")
            self.assertIsInstance(restored, LearnedGripperPolicy)
            self.assertEqual(restored_normalizer.stats, normalizer.stats)
            self.assertTrue(restored_normalizer.robot_velocity_mask)
            restored_prediction = restored.predict_action_chunk(batch)
            self.assertTrue(torch.equal(restored_prediction[..., :5], base.predict_action_chunk(batch)[..., :5]))
            metadata["train_dataset_sha256"] = ["b" * 64]
            torch.save(metadata, path)
            with self.assertRaisesRegex(ValueError, "training hashes"):
                load_policy_checkpoint(str(path), "cpu")

    def test_bounded_cpu_training_records_real_draws_and_new_options(self):
        base, normalizer, spec, _, _ = base_fixture()
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            archive = directory / "mock-training-material.h5"
            archive.write_bytes(b"fixture identity; HDF5 reader mocked for this unit test")
            archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
            base_path = directory / "base.pt"
            metadata = {"format": "so101-state-policy-v1", "model_spec": spec.to_dict(),
                        "normalization": normalizer.stats, "state_dict": base.state_dict(),
                        "action_encoding": "arm_delta", "normalization_options": {"robot_velocity_mask": True},
                        "train_dataset_sha256": [archive_hash], "model_sha256": "b" * 64,
                        "control_period_s": .02, "training_options": {"learning_rate": 999, "seed": 999},
                        "training_loss_scope": "arm5_only", "gripper_output_scope": "unsupervised",
                        "normalization_source": {"training_dataset_sha256": [archive_hash]}}
            torch.save(metadata, base_path)
            arguments = SimpleNamespace(output=directory / "result", dataset=[archive], base_checkpoint=base_path,
                                        device="cpu", max_steps=2, max_wall_s=1, max_epochs=2,
                                        batch_size=4, seed=7, learning_rate=.0123, critical_sample_weight=5.)
            episode = {"eligible_for_training": True, "report": {"passed": True},
                       "metadata": {"model_sha256": "b" * 64, "control_period_s": .02}}
            with patch("train_gripper_classifier.load_episode", return_value=episode), \
                    patch("train_gripper_classifier.training_rows", return_value=rows()), \
                    patch("train_gripper_classifier.audit_episodes", return_value={"attempt_count": 1}):
                report = train(arguments)
            self.assertEqual(report["status"], "completed_diagnostic", report.get("error"))
            self.assertEqual(report["task_acceptance"], "not_run")
            self.assertEqual(report["steps"], 2)
            # Six rows per epoch, batch four: actual draw count is four + two.
            self.assertEqual(report["sampling"]["actual_draw_count"], 6)
            self.assertEqual(report["sampling"]["actual_upweighted_draw_count"], 6)
            self.assertGreater(report["sampling"]["actual_unique_row_count"], 0)
            self.assertTrue(report["base_frozen_state_verified"])
            saved = torch.load(arguments.output / "policy.pt", map_location="cpu", weights_only=True)
            self.assertEqual(saved["training_options"]["learning_rate"], .0123)
            self.assertEqual(saved["training_options"]["seed"], 7)
            self.assertEqual(saved["policy_architecture"]["base_training_loss_scope"], "arm5_only")
            self.assertEqual(saved["gripper_output_scope"], "supervised by the independent learned gripper classifier")
            self.assertEqual(saved["normalization"], metadata["normalization"])
            self.assertEqual(saved["normalization_source"], metadata["normalization_source"])
            self.assertTrue(all(torch.equal(value, metadata["state_dict"][name]) for name, value in saved["state_dict"].items()))


if __name__ == "__main__":
    unittest.main()
