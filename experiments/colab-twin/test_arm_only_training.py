"""CPU counterexamples for the deterministic ACT five-axis training objective.

These checks establish loss/gradient scope and the default dispatch contract.
They do not establish policy grasp/place acceptance or run the simulator.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

from learning_models import (ACTION, ENV_STATE, STATE, ModelSpec,
                             StatePolicyRunner, build_policy)
from train_state_policy import (arm_only_training_loss, train,
                                validate_arm_only_training_options)


def small_act(**overrides):
    torch.manual_seed(281)
    options = dict(model="act", dim_model=16, dim_feedforward=32, n_heads=4,
                   n_encoder_layers=1, n_decoder_layers=1, chunk_size=4,
                   use_vae=False, dropout=0)
    options.update(overrides)
    return build_policy(ModelSpec(**options), "cpu")


def batch_for(policy):
    generator = torch.Generator().manual_seed(283)
    observations = {STATE: torch.randn(3, 6, generator=generator),
                    ENV_STATE: torch.randn(3, 30, generator=generator)}
    with torch.no_grad():
        prediction = policy.model(observations)[0]
    # Nonzero errors on every arm row avoid a false zero-gradient success.
    targets = prediction + torch.tensor([1., -2., 3., -.4, .5, 2.])[None, None]
    return {**observations, ACTION: targets,
            "action_is_pad": torch.tensor([[False, False, True, True],
                                           [False, True, True, True],
                                           [False, False, False, True]])}


def clone_batch(batch):
    return {key: value.detach().clone() for key, value in batch.items()}


def gradients(policy, batch):
    policy.zero_grad(set_to_none=True)
    loss, metrics = arm_only_training_loss(policy, batch)
    loss.backward()
    values = {name: None if parameter.grad is None else parameter.grad.clone()
              for name, parameter in policy.named_parameters()}
    return loss.detach().clone(), metrics, values


def options(**overrides):
    values = dict(arm_only_loss=True, train_gripper_head_only=False, model="act",
                  init_checkpoint=Path("explicit-compatible-init.pt"),
                  no_vae=True, dropout=0)
    values.update(overrides)
    return SimpleNamespace(**values)


class ArmOnlyTrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_threads = torch.get_num_threads()
        torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.previous_threads)

    def assert_gradients_equal(self, left, right):
        self.assertEqual(left.keys(), right.keys())
        for name in left:
            if left[name] is None:
                self.assertIsNone(right[name], name)
            else:
                self.assertIsNotNone(right[name], name)
                self.assertTrue(torch.equal(left[name], right[name]), name)

    def test_finite_jaw_labels_cannot_change_arm_loss_or_any_parameter_gradient(self):
        policy = small_act().train()
        batch = batch_for(policy)
        loss, metrics, before = gradients(policy, batch)
        changed = clone_batch(batch)
        changed[ACTION][..., 5] = torch.tensor([[1e20, -1e20, 7., -8.],
                                               [-3., 2e10, -2e10, 0.],
                                               [99., -99., .015, .5]])
        changed_loss, changed_metrics, after = gradients(policy, changed)
        self.assertTrue(torch.equal(loss, changed_loss))
        self.assertEqual(metrics, changed_metrics)
        self.assert_gradients_equal(before, after)

    def test_arm_rows_have_gradients_jaw_row_has_none_and_fresh_adam_respects_scope(self):
        policy = small_act().train()
        head = policy.model.action_head
        original_weight, original_bias = head.weight.detach().clone(), head.bias.detach().clone()
        optimizer = torch.optim.Adam(policy.parameters(), lr=.01)
        self.assertEqual(optimizer.state, {})
        self.assertEqual(optimizer.param_groups[0]["weight_decay"], 0)
        loss, metrics, values = gradients(policy, batch_for(policy))
        self.assertTrue(torch.isfinite(loss))
        self.assertEqual(metrics["valid_action_count"], 6)
        self.assertEqual(metrics["valid_arm_coordinate_count"], 30)
        for row in range(5):
            self.assertGreater(int(torch.count_nonzero(head.weight.grad[row])), 0, row)
            self.assertGreater(int(torch.count_nonzero(head.bias.grad[row])), 0, row)
        self.assertEqual(int(torch.count_nonzero(head.weight.grad[5])), 0)
        self.assertEqual(int(torch.count_nonzero(head.bias.grad[5])), 0)
        self.assertTrue(any(gradient is not None and torch.count_nonzero(gradient)
                            for name, gradient in values.items()
                            if not name.startswith("model.action_head.")))
        optimizer.step()
        self.assertFalse(torch.equal(head.weight[:5], original_weight[:5]))
        self.assertTrue(torch.equal(head.weight[5], original_weight[5]))
        self.assertTrue(torch.equal(head.bias[5], original_bias[5]))

    def test_padding_targets_do_not_change_loss_or_any_parameter_gradient(self):
        policy = small_act().train()
        batch = batch_for(policy)
        loss, metrics, before = gradients(policy, batch)
        changed = clone_batch(batch)
        changed[ACTION][changed["action_is_pad"]] = 1e20
        changed_loss, changed_metrics, after = gradients(policy, changed)
        self.assertTrue(torch.equal(loss, changed_loss))
        self.assertEqual(metrics, changed_metrics)
        self.assert_gradients_equal(before, after)

    def test_only_valid_arm_output_and_label_coordinates_receive_gradients(self):
        policy = small_act().train()
        batch = batch_for(policy)
        batch[ACTION].requires_grad_(True)
        captured = []

        def capture(_module, _inputs, output):
            output.retain_grad()
            captured.append(output)

        with policy.model.action_head.register_forward_hook(capture):
            loss, _ = arm_only_training_loss(policy, batch)
            loss.backward()
        prediction = captured[0]
        valid = ~batch["action_is_pad"]
        for gradient in (prediction.grad, batch[ACTION].grad):
            self.assertEqual(int(torch.count_nonzero(gradient[..., 5])), 0)
            self.assertEqual(int(torch.count_nonzero(gradient[~valid])), 0)
            self.assertEqual(int(torch.count_nonzero(gradient[..., :5][valid])), 30)

    def test_all_padding_and_empty_batch_are_rejected(self):
        policy = small_act()
        batch = batch_for(policy)
        all_padding = clone_batch(batch)
        all_padding["action_is_pad"].fill_(True)
        with self.assertRaisesRegex(ValueError, "at least one valid"):
            arm_only_training_loss(policy, all_padding)
        with self.assertRaisesRegex(ValueError, "Nxchunkx6"):
            arm_only_training_loss(policy, {key: value[:0] for key, value in batch.items()})

    def test_malformed_targets_padding_and_observations_are_rejected(self):
        policy = small_act()
        batch = batch_for(policy)
        changes = [
            (ACTION, batch[ACTION][:, :, :5]),
            (ACTION, batch[ACTION][:, :3]),
            (ACTION, batch[ACTION][:, 0]),
            (ACTION, batch[ACTION].long()),
            (ACTION, batch[ACTION].numpy()),
            ("action_is_pad", batch["action_is_pad"].float()),
            ("action_is_pad", batch["action_is_pad"][:, :3]),
            (STATE, batch[STATE][:, :5]),
            (STATE, batch[STATE][:2]),
            (STATE, batch[STATE].long()),
            (ENV_STATE, batch[ENV_STATE][:, :29]),
            (ENV_STATE, batch[ENV_STATE].numpy()),
        ]
        for key, value in changes:
            with self.subTest(key=key, type=type(value).__name__, shape=value.shape):
                malformed = clone_batch(batch)
                malformed[key] = value
                with self.assertRaises(ValueError):
                    arm_only_training_loss(policy, malformed)

    def test_nan_and_inf_are_rejected_including_unsupervised_jaw_and_padding(self):
        policy = small_act()
        batch = batch_for(policy)
        for key, index in ((STATE, (0, 0)), (ENV_STATE, (0, 13)),
                           (ACTION, (0, 0, 0)), (ACTION, (0, 0, 5)),
                           (ACTION, (0, 2, 0))):
            for value in (float("nan"), float("inf"), -float("inf")):
                with self.subTest(key=key, index=index, value=value):
                    malformed = clone_batch(batch)
                    malformed[key][index] = value
                    with self.assertRaises(ValueError):
                        arm_only_training_loss(policy, malformed)

    def test_missing_or_extra_batch_keys_are_rejected(self):
        policy = small_act()
        batch = batch_for(policy)
        for key in batch:
            with self.subTest(missing=key):
                malformed = clone_batch(batch)
                del malformed[key]
                with self.assertRaisesRegex(ValueError, "tensors only"):
                    arm_only_training_loss(policy, malformed)
        for key in ("stage", "time_s", "action_anchor"):
            with self.subTest(extra=key):
                malformed = clone_batch(batch)
                malformed[key] = torch.ones(3)
                with self.assertRaisesRegex(ValueError, "tensors only"):
                    arm_only_training_loss(policy, malformed)

    def test_mlp_vae_or_dropout_act_is_rejected(self):
        batch = batch_for(small_act())
        for policy in (build_policy(ModelSpec(model="mlp"), "cpu"),
                       small_act(use_vae=True), small_act(dropout=.1)):
            with self.subTest(policy=type(policy).__name__, config=getattr(policy, "config", None)):
                with self.assertRaisesRegex(ValueError, "deterministic ACTPolicy"):
                    arm_only_training_loss(policy, batch)

    def test_nonfinite_or_malformed_official_predictions_are_rejected(self):
        policy = small_act()
        batch = batch_for(policy)
        for prediction in (torch.full((3, 4, 6), float("nan")), torch.zeros(3, 4, 5)):
            with self.subTest(shape=prediction.shape):
                with patch.object(policy.model, "forward", return_value=(prediction, (None, None))):
                    with self.assertRaisesRegex(RuntimeError, "malformed/nonfinite"):
                        arm_only_training_loss(policy, batch)

    def test_options_require_explicit_deterministic_act_init_and_exclude_jaw_only(self):
        validate_arm_only_training_options(options())
        for changes in ({"model": "mlp"}, {"init_checkpoint": None},
                        {"no_vae": False}, {"dropout": .1},
                        {"train_gripper_head_only": True}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    validate_arm_only_training_options(options(**changes))
        # The opt-in validator must not impose ACT/init constraints on old jobs.
        validate_arm_only_training_options(SimpleNamespace(arm_only_loss=False))
        validate_arm_only_training_options(SimpleNamespace())

    def test_unsupervised_jaw_checkpoint_is_rejected_before_policy_execution(self):
        metadata = {"model_spec": {"model": "act", "chunk_size": 16},
                    "training_loss_scope": "arm5_only"}
        with self.assertRaisesRegex(ValueError, "needs its learned gripper"):
            StatePolicyRunner(None, None, metadata, "cpu", execute_chunk_steps=16)

    def test_arm_checkpoint_with_learned_gripper_can_construct_runtime_adapter(self):
        # Constructor admission only; actual component loading/behavior is
        # validated by the learned-gripper suite and physical policy evaluation.
        metadata = {"model_spec": {"model": "act", "chunk_size": 16},
                    "training_loss_scope": "arm5_only", "learned_gripper_classifier": {}}
        runner = StatePolicyRunner(None, None, metadata, "cpu", execute_chunk_steps=16)
        self.assertIs(runner.metadata, metadata)
        self.assertEqual(runner.execute_chunk_steps, 16)

    def test_disabled_or_absent_option_uses_official_policy_batch_training(self):
        class StopAfterStep(Exception):
            pass

        rng = np.random.default_rng(293)
        rows = {STATE: rng.normal(size=(3, 6)), ENV_STATE: rng.normal(size=(3, 30)),
                ACTION: rng.normal(size=(3, 6)), "episode_index": np.zeros(3, dtype=int),
                "frame_index": np.arange(3)}
        episode = {"eligible_for_training": True, "report": {"passed": True},
                   "metadata": {"control_period_s": .02, "model_sha256": "a" * 64}}
        for explicit_false in (False, True):
            with self.subTest(explicit_false=explicit_false), tempfile.TemporaryDirectory() as directory:
                dataset = Path(directory) / "synthetic-archive"
                dataset.write_bytes(b"CPU dispatcher fixture; not a physical episode")
                args = options(arm_only_loss=False, init_checkpoint=None, device="cpu",
                               dataset=[dataset], validation_dataset=[], output=Path(directory),
                               max_steps=1, max_epochs=1, max_wall_s=10, learning_rate=.001,
                               batch_size=3, chunk_size=4, action_encoding="absolute",
                               velocity_scale_floor=0, critical_sample_weight=1, seed=0)
                if not explicit_false:
                    del args.arm_only_loss
                policy = small_act()
                # Stop after an actual backward/Adam step, before serialization.
                # This isolates dispatch without fabricating any task acceptance.
                with patch("train_state_policy.audit_episodes", return_value={}), \
                     patch("train_state_policy.training_rows", return_value=rows), \
                     patch("train_state_policy.load_episode", return_value=episode), \
                     patch("train_state_policy.build_policy", return_value=policy), \
                     patch("train_state_policy.evaluate_regression",
                           side_effect=[{}, StopAfterStep("default dispatch checked")]), \
                     patch("train_state_policy.arm_only_training_loss",
                           side_effect=AssertionError("opt-in loss used by default")) as arm_loss, \
                     patch.object(policy, "forward", wraps=policy.forward) as official_forward:
                    report = train(args)
                arm_loss.assert_not_called()
                official_forward.assert_called_once()
                self.assertEqual(report["steps"], 1)
                self.assertEqual(report["training_loss_scope"], "all_action_coordinates")
                self.assertFalse(report["training_options"]["arm_only_loss"])
                self.assertEqual(report["error"]["type"], "StopAfterStep", report)
                self.assertEqual(report["error"]["message"], "default dispatch checked")
                self.assertGreater(int(torch.count_nonzero(policy.model.action_head.weight.grad[5])), 0)


if __name__ == "__main__":
    unittest.main()
