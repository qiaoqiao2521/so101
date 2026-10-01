"""Regression tests for dataset/policy boundaries, without hardware or GPU."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import torch

from learning_models import (ACTION, ENV_STATE, STATE, ModelSpec, StateNormalizer,
                             StatePolicyRunner, build_policy, load_policy)
from train_state_policy import make_chunks


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


if __name__ == "__main__":
    unittest.main()
