"""CPU tests for provenance-preserving arm/gripper checkpoint composition."""
from __future__ import annotations

import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import torch

from compose_state_policy import compose, compose_metadata, validate_composed_policy_metadata
from learning_data import SCHEMA_VERSION
from learning_models import ACTION_ENCODING_SEMANTICS, LEROBOT_REVISION, load_policy_checkpoint
from test_gripper_classifier import base_fixture


def fixture():
    base, normalizer, spec, batch, component = base_fixture()
    component.update(train_dataset_sha256=["a" * 64, "b" * 64],
                     input_statistics_training_dataset_sha256=["a" * 64, "b" * 64],
                     base_checkpoint_sha256="d" * 64, source_sha256="e" * 64,
                     input_transform={"base_normalization_options": {
                         "velocity_scale_floor_rad_s": 0., "robot_velocity_mask": True,
                         "object_velocity_mask": False}})
    old = {"format": "so101-state-policy-v1", "schema_version": SCHEMA_VERSION,
           "model_spec": spec.to_dict(), "normalization": normalizer.stats,
           "normalization_options": component["input_transform"]["base_normalization_options"],
           "action_encoding": "arm_delta", "action_encoding_semantics": ACTION_ENCODING_SEMANTICS["arm_delta"],
           "lerobot_revision": LEROBOT_REVISION, "control_period_s": .02, "model_sha256": "f" * 64,
           "state_dict": copy.deepcopy(base.state_dict()), "training_loss_scope": "arm5_only",
           "train_dataset_sha256": ["a" * 64, "b" * 64], "validation_dataset_sha256": [],
           "normalization_source": {"training_dataset_sha256": ["a" * 64]},
           "initialization": {"base_checkpoint_sha256": "d" * 64, "base_training_dataset_sha256": ["a" * 64]},
           "learned_gripper_classifier": component}
    arm = copy.deepcopy(old)
    del arm["learned_gripper_classifier"]
    arm["train_dataset_sha256"].append("c" * 64)
    arm["initialization"] = {"checkpoint_sha256": "d" * 64, "original_training_dataset_sha256": ["a" * 64]}
    first = next(iter(arm["state_dict"]))
    arm["state_dict"][first] += .01
    return arm, old, batch


def combine(arm, old):
    return compose_metadata(arm, old, arm_sha256="1" * 64, gripper_sha256="2" * 64)


class ComposeStatePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.threads = torch.get_num_threads()
        torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.threads)

    def test_keeps_each_component_training_identity_and_exact_tensor_bytes(self):
        arm, old, _ = fixture()
        combined = combine(arm, old)
        self.assertEqual(combined["train_dataset_sha256"], ["a" * 64, "b" * 64, "c" * 64])
        head = combined["learned_gripper_classifier"]
        self.assertEqual(head["train_dataset_sha256"], ["a" * 64, "b" * 64])
        self.assertEqual(head["base_checkpoint_sha256"], "d" * 64)
        self.assertEqual(head["source_sha256"], "e" * 64)
        self.assertEqual(head["input_statistics"], old["learned_gripper_classifier"]["input_statistics"])
        for key, value in arm["state_dict"].items():
            self.assertTrue(torch.equal(value, combined["state_dict"][key]))
        for key, value in old["learned_gripper_classifier"]["state_dict"].items():
            self.assertTrue(torch.equal(value, head["state_dict"][key]))
        self.assertEqual(combined["normalization"], old["normalization"])
        self.assertNotIn("composition", arm)
        self.assertNotIn("composition", old)

    def test_loader_preserves_new_arm_output_old_jaw_and_legacy_strict_hash_check(self):
        arm, old, batch = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            paths = [directory / name for name in ("arm.pt", "old.pt", "combined.pt")]
            for path, metadata in zip(paths, (arm, old, combine(arm, old))):
                torch.save(metadata, path)
            arm_policy, _, _ = load_policy_checkpoint(str(paths[0]))
            old_policy, _, _ = load_policy_checkpoint(str(paths[1]))
            policy, normalizer, _ = load_policy_checkpoint(str(paths[2]))
            with torch.no_grad():
                result = policy.predict_action_chunk(batch)
                self.assertTrue(torch.equal(result[..., :5], arm_policy.predict_action_chunk(batch)[..., :5]))
                self.assertTrue(torch.equal(result[..., 5], old_policy.predict_action_chunk(batch)[..., 5]))
            self.assertEqual(normalizer.stats, arm["normalization"])
            old["train_dataset_sha256"].append("c" * 64)
            torch.save(old, paths[1])
            with self.assertRaisesRegex(ValueError, "training hashes"):
                load_policy_checkpoint(str(paths[1]))

    def test_rejects_specification_encoding_and_official_revision_mismatches(self):
        arm, old, _ = fixture()
        for key, value in (("chunk_size", 5), ("use_vae", True), ("dropout", .1), ("action_encoding", "absolute")):
            bad = copy.deepcopy(arm)
            bad["model_spec"][key] = value
            with self.subTest(model_field=key), self.assertRaises(ValueError):
                combine(bad, old)
        for key, value in (("action_encoding", "absolute"), ("lerobot_revision", "wrong"),
                           ("action_encoding_semantics", "wrong"), ("schema_version", "wrong")):
            bad = copy.deepcopy(arm)
            bad[key] = value
            with self.subTest(field=key), self.assertRaises(ValueError):
                combine(bad, old)

    def test_rejects_any_scale_refit_mask_or_physical_model_change(self):
        arm, old, _ = fixture()
        changes = [lambda data: data["normalization"]["observation.state"]["mean"].__setitem__(0, 123.),
                   lambda data: data["normalization"]["action"]["std"].__setitem__(5, 0.),
                   lambda data: data["normalization_options"].__setitem__("robot_velocity_mask", False),
                   lambda data: data["normalization_options"].__setitem__("object_velocity_mask", True),
                   lambda data: data.__setitem__("control_period_s", .04),
                   lambda data: data.__setitem__("model_sha256", "9" * 64)]
        for index, change in enumerate(changes):
            bad = copy.deepcopy(arm)
            change(bad)
            with self.subTest(change=index), self.assertRaises(ValueError):
                combine(bad, old)

    def test_rejects_missing_head_training_duplicate_hashes_and_validation_overlap(self):
        arm, old, _ = fixture()
        for training, validation in ((["a" * 64, "c" * 64], []),
                                     (["a" * 64, "b" * 64, "b" * 64], []),
                                     (["a" * 64, "b" * 64, "c" * 64], ["a" * 64])):
            bad = copy.deepcopy(arm)
            bad.update(train_dataset_sha256=training, validation_dataset_sha256=validation)
            with self.subTest(training=training), self.assertRaises(ValueError):
                combine(bad, old)

    def test_rejects_wrong_original_base_or_normalization_origin(self):
        arm, old, _ = fixture()
        bad = copy.deepcopy(arm)
        bad["initialization"]["checkpoint_sha256"] = "9" * 64
        with self.assertRaisesRegex(ValueError, "initialization"):
            combine(bad, old)
        bad = copy.deepcopy(arm)
        bad["normalization_source"]["training_dataset_sha256"] = ["b" * 64]
        with self.assertRaisesRegex(ValueError, "normalization training identities"):
            combine(bad, old)
        bad = copy.deepcopy(old)
        bad["initialization"]["base_checkpoint_sha256"] = "9" * 64
        with self.assertRaisesRegex(ValueError, "base checkpoint provenance"):
            combine(arm, bad)

    def test_loader_rejects_tampered_tensor_head_statistics_union_and_source(self):
        arm, old, _ = fixture()
        original = combine(arm, old)
        changes = [lambda data: data["state_dict"][next(iter(data["state_dict"]))].add_(.01),
                   lambda data: data["learned_gripper_classifier"]["state_dict"]["net.0.weight"].add_(.01),
                   lambda data: data["learned_gripper_classifier"]["input_statistics"]["observation.state"]["mean"].__setitem__(0, 999.),
                   lambda data: data["learned_gripper_classifier"].__setitem__("source_sha256", "9" * 64),
                   lambda data: data["train_dataset_sha256"].append("9" * 64),
                   lambda data: data["normalization_options"].__setitem__("velocity_scale_floor_rad_s", .5)]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tampered.pt"
            for index, change in enumerate(changes):
                bad = copy.deepcopy(original)
                change(bad)
                torch.save(bad, path)
                with self.subTest(change=index), self.assertRaises(ValueError):
                    load_policy_checkpoint(str(path))

    def test_composition_command_records_reload_evidence_without_claiming_task_success(self):
        arm, old, _ = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            arm_path, head_path = directory / "arm.pt", directory / "head.pt"
            torch.save(arm, arm_path)
            torch.save(old, head_path)
            arguments = SimpleNamespace(arm_checkpoint=arm_path, gripper_checkpoint=head_path,
                                        output=directory / "result")
            report = compose(arguments)
            self.assertEqual(report["status"], "completed_composition", report.get("error"))
            self.assertEqual(report["task_acceptance"], "not_run")
            self.assertTrue(report["gripper_component_unchanged"])
            self.assertEqual(report["reload_arm_max_abs_error"], 0.)
            self.assertEqual(report["reload_gripper_max_abs_error"], 0.)
            with self.assertRaises(FileExistsError):
                compose(arguments)


if __name__ == "__main__":
    unittest.main()
