"""Explicit learned state gripper attached to a frozen official ACT arm.

The classifier sees the base policy's two normalized observation tensors.
Existing base masks remain in force; there is no clock, stage or geometry rule.
"""
from __future__ import annotations

import numpy as np
import torch
from torch import nn

from learning_models import ACTION, ENV_STATE, STATE

GRIPPER_FORMAT = "so101-learned-gripper-classifier-v1"
INPUT_WIDTHS = {STATE: 6, ENV_STATE: 30}
GRIPPER_CLASSES = (.015, .5)


def validate_input_statistics(statistics):
    if set(statistics) != set(INPUT_WIDTHS):
        raise ValueError("Classifier statistics require only the two observation keys")
    for key, width in INPUT_WIDTHS.items():
        for name in ("mean", "std"):
            values = np.asarray(statistics[key][name], dtype=float)
            if (values.shape != (width,) or not np.isfinite(values).all()
                    or name == "std" and np.any(values <= 0)):
                raise ValueError("Invalid classifier input statistics: " + key + "." + name)


def fit_input_statistics(batch):
    """Fit only caller-supplied valid training, already-base-normalized rows."""
    if set(batch) != set(INPUT_WIDTHS):
        raise ValueError("Classifier fitting requires only the two observation keys")
    statistics = {}
    for key, width in INPUT_WIDTHS.items():
        values = batch[key].detach().cpu().numpy() if isinstance(batch[key], torch.Tensor) else np.asarray(batch[key])
        values = np.asarray(values, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != width or not len(values) or not np.isfinite(values).all():
            raise ValueError("Expected finite training observations: " + key)
        std = values.std(axis=0)
        std[std == 0] = 1
        statistics[key] = {"mean": values.mean(axis=0).tolist(), "std": std.tolist()}
    validate_input_statistics(statistics)
    return statistics


def classifier_inputs(batch, statistics):
    validate_input_statistics(statistics)
    if set(batch) != set(INPUT_WIDTHS):
        raise ValueError("Classifier requires only the two observation keys")
    normalized = []
    count = None
    for key, width in INPUT_WIDTHS.items():
        values = batch[key]
        if (not isinstance(values, torch.Tensor) or values.ndim != 2 or values.shape[1] != width
                or not torch.isfinite(values).all()):
            raise ValueError("Expected finite classifier observations: " + key)
        count = len(values) if count is None else count
        if len(values) != count:
            raise ValueError("Classifier observation batch sizes differ")
        mean = torch.as_tensor(statistics[key]["mean"], dtype=values.dtype, device=values.device)
        std = torch.as_tensor(statistics[key]["std"], dtype=values.dtype, device=values.device)
        transformed = (values - mean) / std
        if not torch.isfinite(transformed).all():
            raise ValueError("Nonfinite classifier transformed observations")
        normalized.append(transformed)
    return torch.cat(normalized, dim=-1)


class GripperClassifier(nn.Module):
    def __init__(self, chunk_size):
        super().__init__()
        if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size < 1:
            raise ValueError("Classifier chunk size must be a positive integer")
        self.chunk_size = chunk_size
        self.net = nn.Sequential(nn.Linear(36, 64), nn.ReLU(), nn.Linear(64, 64),
                                 nn.ReLU(), nn.Linear(64, chunk_size * 2))

    def forward(self, inputs):
        if inputs.ndim != 2 or inputs.shape[1] != 36 or not torch.isfinite(inputs).all():
            raise ValueError("Expected finite classifier matrix with 36 slots")
        return self.net(inputs).reshape(len(inputs), self.chunk_size, 2)


def masked_classification_loss(logits, labels, padding):
    if (logits.ndim != 3 or logits.shape[-1] != 2 or labels.shape != logits.shape[:2]
            or padding.shape != labels.shape or padding.dtype != torch.bool
            or labels.dtype != torch.long or not torch.isfinite(logits).all()
            or torch.any((labels < 0) | (labels > 1))):
        raise ValueError("Invalid finite classification chunks, labels or padding")
    valid = ~padding
    if not valid.any():
        raise ValueError("Classifier batch has no valid expert labels")
    return torch.nn.functional.cross_entropy(logits[valid], labels[valid])


class LearnedGripperPolicy(nn.Module):
    """Composite inference only; unchanged ACT arm plus categorical jaw chunk."""
    def __init__(self, base_policy, component, action_statistics, training_hashes, device="cpu"):
        super().__init__()
        if (component.get("format") != GRIPPER_FORMAT
                or component.get("input_keys") != [STATE, ENV_STATE]
                or component.get("inputs_are_base_normalized_and_masked") is not True
                or component.get("classes_rad") != list(GRIPPER_CLASSES)
                or component.get("architecture") != {"input_width": 36, "hidden_widths": [64, 64],
                                                      "chunk_size": base_policy.config.chunk_size,
                                                      "classes": 2}):
            raise ValueError("Unsupported learned gripper classifier contract")
        hashes = component.get("train_dataset_sha256", [])
        if not hashes or len(set(hashes)) != len(hashes) or hashes != list(training_hashes):
            raise ValueError("Classifier and checkpoint training hashes differ")
        if base_policy.config.n_action_steps != 1:
            raise ValueError("Composite select_action requires one base action step")
        self.base_policy = base_policy
        # Inference is no-grad below. Preserve the original flags as well as
        # weights: toggling them can select a different CPU Transformer kernel.
        # The trainer freezes the base and optimizes classifier parameters only.
        self.base_policy.eval()
        self.statistics = component["input_statistics"]
        validate_input_statistics(self.statistics)
        self.classifier = GripperClassifier(base_policy.config.chunk_size).to(device)
        state = component["state_dict"]
        if not state or any(not torch.isfinite(value).all() for value in state.values()):
            raise ValueError("Classifier weights must be finite")
        self.classifier.load_state_dict(state, strict=True)
        self.classifier.eval()
        self.jaw_mean = float(action_statistics["mean"][5])
        self.jaw_std = float(action_statistics["std"][5])
        if not np.isfinite([self.jaw_mean, self.jaw_std]).all() or self.jaw_std <= 0:
            raise ValueError("Invalid base jaw normalization")

    @property
    def config(self):
        return self.base_policy.config

    def reset(self):
        self.base_policy.reset()

    @torch.no_grad()
    def predict_action_chunk(self, batch):
        inputs = classifier_inputs(batch, self.statistics)
        self.base_policy.eval()
        base_chunk = self.base_policy.predict_action_chunk(batch)
        logits = self.classifier(inputs)
        if (base_chunk.shape != (len(inputs), self.config.chunk_size, 6)
                or not torch.isfinite(base_chunk).all() or not torch.isfinite(logits).all()):
            raise RuntimeError("Composite policy produced a malformed/nonfinite chunk")
        classes = logits.argmax(dim=-1)  # Exact tie chooses training class zero.
        support = torch.tensor(GRIPPER_CLASSES, dtype=base_chunk.dtype, device=base_chunk.device)
        output = base_chunk.clone()
        output[..., 5] = (support[classes] - self.jaw_mean) / self.jaw_std
        return output

    @torch.no_grad()
    def select_action(self, batch):
        return self.predict_action_chunk(batch)[:, 0]
