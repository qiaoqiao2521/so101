"""Small state policies sharing explicit, externally normalized observations.

ACT is the unmodified official LeRobot implementation at LEROBOT_REVISION.
No hub access, image backbone, expert solver or simulator is used here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

LEROBOT_REVISION = "e0d50211ef236143ae867228662b7dfaba554f02"
STATE = "observation.state"
ENV_STATE = "observation.environment_state"
ACTION = "action"


@dataclass(frozen=True)
class ModelSpec:
    model: str = "act"
    state_dim: int = 6
    environment_dim: int = 30
    action_dim: int = 6
    chunk_size: int = 16
    dim_model: int = 256
    n_heads: int = 4
    n_encoder_layers: int = 2
    n_decoder_layers: int = 2
    dim_feedforward: int = 1024
    use_vae: bool = True
    dropout: float = 0.1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class StateMLP(nn.Module):
    """Three linear layers; one current observation predicts one joint target."""
    def __init__(self, spec: ModelSpec):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(spec.state_dim + spec.environment_dim, 128), nn.ReLU(),
            nn.Linear(128, 128), nn.ReLU(), nn.Linear(128, spec.action_dim),
        )

    def forward(self, batch: dict[str, torch.Tensor]):
        output = self.net(torch.cat((batch[STATE], batch[ENV_STATE]), dim=-1))
        target = batch[ACTION][:, 0] if batch[ACTION].ndim == 3 else batch[ACTION]
        loss = torch.nn.functional.l1_loss(output, target)
        return loss, {"l1_loss": float(loss.detach())}

    @torch.no_grad()
    def select_action(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        return self.net(torch.cat((batch[STATE], batch[ENV_STATE]), dim=-1))

    def reset(self) -> None:
        pass


def build_policy(spec: ModelSpec, device: str = "cpu") -> nn.Module:
    if spec.model == "mlp":
        return StateMLP(spec).to(device)
    if spec.model != "act":
        raise ValueError(f"Unknown policy {spec.model!r}")
    from lerobot.configs.types import FeatureType, PolicyFeature
    from lerobot.policies.act.configuration_act import ACTConfig
    from lerobot.policies.act.modeling_act import ACTPolicy
    for cls, expected in (
        (ACTPolicy, "83d954f79ccd3eaa6774dbea92524939c8ac08359bb355ba7cd37b8601e1e3af"),
        (ACTConfig, "35a60c0dd3c811b137b5eb035bdbd40d40e2c24ba0cda61756052e6e1c829282"),
    ):
        source = Path(inspect.getfile(cls))
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"ACT source does not match pinned official revision {LEROBOT_REVISION}: {cls.__name__}")

    config = ACTConfig(
        input_features={STATE: PolicyFeature(FeatureType.STATE, (spec.state_dim,)),
                        ENV_STATE: PolicyFeature(FeatureType.ENV, (spec.environment_dim,))},
        output_features={ACTION: PolicyFeature(FeatureType.ACTION, (spec.action_dim,))},
        device=device, push_to_hub=False, pretrained_backbone_weights=None,
        chunk_size=spec.chunk_size, n_action_steps=1,
        dim_model=spec.dim_model, n_heads=spec.n_heads,
        dim_feedforward=spec.dim_feedforward,
        n_encoder_layers=spec.n_encoder_layers, n_decoder_layers=spec.n_decoder_layers,
        n_vae_encoder_layers=2, use_vae=spec.use_vae, dropout=spec.dropout,
    )
    # ACTPolicy consumes normalized tensors. Our adapter owns normalization so
    # both probes and saved policies use exactly the same scale/units.
    return ACTPolicy(config).to(device)


class StateNormalizer:
    """Fit only caller-selected training rows; persist the exact statistics."""
    def __init__(self, stats: dict[str, dict[str, list[float]]]):
        self.stats = stats

    @classmethod
    def fit(cls, rows: dict[str, np.ndarray]) -> "StateNormalizer":
        stats = {}
        for key in (STATE, ENV_STATE, ACTION):
            values = np.asarray(rows[key], dtype=np.float64)
            if values.ndim != 2 or not len(values) or not np.isfinite(values).all():
                raise ValueError(f"Invalid finite training matrix for {key}")
            # Near-constant columns use unit scale rather than amplifying tiny
            # physical jitter; this matters for fixed obstacles/target poses.
            scale = values.std(axis=0)
            scale[scale < 1e-4] = 1.0
            stats[key] = {"mean": values.mean(axis=0).tolist(), "std": scale.tolist()}
        return cls(stats)

    def normalize(self, key: str, values: np.ndarray) -> np.ndarray:
        stat = self.stats[key]
        return ((np.asarray(values) - np.asarray(stat["mean"])) /
                np.asarray(stat["std"])).astype(np.float32)

    def action_radians(self, tensor: torch.Tensor) -> np.ndarray:
        stat = self.stats[ACTION]
        values = tensor.detach().cpu().numpy()
        return values * np.asarray(stat["std"]) + np.asarray(stat["mean"])


def load_policy_checkpoint(path: str, device: str = "cpu"):
    """Load this experiment's local weights, not an arbitrary hub checkpoint."""
    data = torch.load(path, map_location="cpu", weights_only=True)
    if data.get("format") != "so101-state-policy-v1":
        raise ValueError("Unsupported policy checkpoint format")
    spec = ModelSpec(**data["model_spec"])
    policy = build_policy(spec, device)
    policy.load_state_dict(data["state_dict"])
    policy.eval()
    return policy, StateNormalizer(data["normalization"]), data


class StatePolicyRunner:
    """Simulation-facing adapter: current physical observation -> radian target.

ACT predicts a chunk but executes its first action (n_action_steps=1), then
observes again next control tick. No stage, clock, expert or hidden replay input.
"""
    def __init__(self, policy, normalizer, metadata, device):
        self.policy, self.normalizer, self.metadata = policy, normalizer, metadata
        self.device = device

    def reset(self) -> None:
        self.policy.reset()

    @torch.no_grad()
    def predict(self, observation: dict[str, np.ndarray]) -> np.ndarray:
        spec = self.metadata["model_spec"]
        batch = {}
        for key, width in ((STATE, spec["state_dim"]), (ENV_STATE, spec["environment_dim"])):
            values = np.asarray(observation[key])
            if values.shape != (width,) or not np.isfinite(values).all():
                raise ValueError(f"Expected finite {key} with shape {(width,)}")
            normalized = self.normalizer.normalize(key, values)
            batch[key] = torch.from_numpy(normalized[None]).to(self.device)
        action = self.normalizer.action_radians(self.policy.select_action(batch))[0]
        if action.shape != (spec["action_dim"],) or not np.isfinite(action).all():
            raise RuntimeError("Policy returned a nonfinite/malformed joint target")
        return action


def load_policy(path: str, device: str = "cpu") -> StatePolicyRunner:
    policy, normalizer, metadata = load_policy_checkpoint(path, device)
    return StatePolicyRunner(policy, normalizer, metadata, device)
