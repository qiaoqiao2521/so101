"""CPU counterexamples for preserving ACT arm outputs during jaw-row fitting.

These checks exercise the pinned official ACT and a fresh Adam optimizer.
They establish update scope, not physical grasp/place acceptance.
"""
from __future__ import annotations

import unittest
from pathlib import Path
import tempfile

import torch
from torch import nn

from learning_models import ACTION, ENV_STATE, STATE, ModelSpec, build_policy
from train_state_policy import (configure_gripper_head_training,
                                load_initialization_checkpoint,
                                verify_gripper_head_training)


def small_act():
    torch.manual_seed(271)
    return build_policy(ModelSpec(model="act", dim_model=16, dim_feedforward=32,
                                  n_heads=4, n_encoder_layers=1, n_decoder_layers=1,
                                  chunk_size=4, use_vae=False, dropout=0), "cpu")


def snapshot(policy):
    return {name: value.detach().clone() for name, value in policy.state_dict().items()}


class GripperHeadTrainingTests(unittest.TestCase):
    def test_base_act_initialization_rejects_discarding_a_learned_gripper(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "composite.pt"
            torch.save({"learned_gripper_classifier": {"format": "so101-learned-gripper-classifier-v1"}}, path)
            with self.assertRaisesRegex(ValueError, "silently discard"):
                load_initialization_checkpoint(path, spec=ModelSpec(), control_period_s=.02,
                                               model_sha256="a" * 64, velocity_scale_floor=0,
                                               eligible_train_hashes=[])

    @classmethod
    def setUpClass(cls):
        cls.previous_threads = torch.get_num_threads()
        torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.previous_threads)

    def test_fresh_adam_changes_only_jaw_row_and_preserves_arm_outputs_exactly(self):
        policy = small_act()
        observations = {STATE: torch.randn(3, 6), ENV_STATE: torch.randn(3, 30)}
        self.assertEqual(set(observations), {STATE, ENV_STATE})
        policy.eval()
        with torch.no_grad():
            before_prediction = policy.predict_action_chunk(observations).clone()
        original = snapshot(policy)
        parameters, audit = configure_gripper_head_training(policy)
        head = policy.model.action_head
        parameters = list(parameters)
        self.assertEqual({id(parameter) for parameter in parameters},
                         {id(head.weight), id(head.bias)})
        self.assertIsInstance(audit, dict)
        for name, parameter in policy.named_parameters():
            self.assertEqual(parameter.requires_grad,
                             name in {"model.action_head.weight", "model.action_head.bias"},
                             name)

        # Every output has a wrong target, so zero arm-row gradients must come
        # from the scope guard rather than accidentally correct arm labels.
        target = before_prediction + torch.tensor([1., -2., 3., -.4, .5, 2.])[None, None]
        batch = {**observations, ACTION: target,
                 "action_is_pad": torch.zeros(3, 4, dtype=torch.bool)}
        optimizer = torch.optim.Adam(parameters, lr=.02)
        self.assertEqual(optimizer.state, {})
        self.assertEqual(optimizer.param_groups[0]["weight_decay"], 0)
        policy.train()
        for _ in range(3):
            optimizer.zero_grad(set_to_none=True)
            loss, _ = policy(batch)
            self.assertTrue(torch.isfinite(loss))
            loss.backward()
            self.assertEqual(int(torch.count_nonzero(head.weight.grad[:5])), 0)
            self.assertEqual(int(torch.count_nonzero(head.bias.grad[:5])), 0)
            self.assertGreater(int(torch.count_nonzero(head.weight.grad[5])), 0)
            self.assertGreater(int(torch.count_nonzero(head.bias.grad[5])), 0)
            optimizer.step()
            self.assertTrue(verify_gripper_head_training(policy, original)["frozen_state_verified"])

        after = snapshot(policy)
        for name, value in after.items():
            if name in {"model.action_head.weight", "model.action_head.bias"}:
                self.assertTrue(torch.equal(value[:5], original[name][:5]), name)
                self.assertFalse(torch.equal(value[5], original[name][5]), name)
            else:
                self.assertTrue(torch.equal(value, original[name]), name)
        policy.eval()
        with torch.no_grad():
            after_prediction = policy.predict_action_chunk(observations)
        self.assertTrue(torch.equal(after_prediction[..., :5], before_prediction[..., :5]))
        self.assertFalse(torch.equal(after_prediction[..., 5], before_prediction[..., 5]))

    def test_mutated_arm_weight_or_bias_is_rejected(self):
        for parameter_name, index in (("weight", (0, 0)), ("bias", (4,))):
            with self.subTest(parameter=parameter_name):
                policy = small_act()
                original = snapshot(policy)
                configure_gripper_head_training(policy)
                with torch.no_grad():
                    getattr(policy.model.action_head, parameter_name)[index] += 1
                with self.assertRaisesRegex(RuntimeError, "frozen state"):
                    verify_gripper_head_training(policy, original)

    def test_mutated_backbone_parameter_is_rejected(self):
        policy = small_act()
        original = snapshot(policy)
        configure_gripper_head_training(policy)
        name, parameter = next((name, parameter) for name, parameter in policy.named_parameters()
                               if not name.startswith("model.action_head.") and parameter.numel())
        self.assertFalse(parameter.requires_grad)
        with torch.no_grad():
            parameter.reshape(-1)[0] += 1
        with self.assertRaisesRegex(RuntimeError, "frozen state"):
            verify_gripper_head_training(policy, original)
        self.assertFalse(torch.equal(policy.state_dict()[name], original[name]))

    def test_incomplete_original_state_is_rejected(self):
        policy = small_act()
        original = snapshot(policy)
        original.pop(next(iter(original)))
        configure_gripper_head_training(policy)
        with self.assertRaisesRegex(RuntimeError, "keys"):
            verify_gripper_head_training(policy, original)

    def test_mlp_is_rejected(self):
        policy = build_policy(ModelSpec(model="mlp"), "cpu")
        with self.assertRaises(ValueError):
            configure_gripper_head_training(policy)

    def test_fake_non_act_with_six_output_head_is_rejected(self):
        # Matching attribute names and head shape cannot establish official ACT.
        policy = nn.Module()
        policy.model = nn.Module()
        policy.model.action_head = nn.Linear(16, 6)
        with self.assertRaises(ValueError):
            configure_gripper_head_training(policy)

    def test_invalid_official_act_heads_are_rejected(self):
        for head in (nn.Linear(16, 5), nn.Linear(16, 6, bias=False), nn.Identity()):
            with self.subTest(head=type(head).__name__, output=getattr(head, "out_features", None)):
                policy = small_act()
                policy.model.action_head = head
                with self.assertRaises(ValueError):
                    configure_gripper_head_training(policy)


if __name__ == "__main__":
    unittest.main()
