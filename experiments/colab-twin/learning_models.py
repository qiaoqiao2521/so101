"""Small state policies sharing explicit, externally normalized observations.

ACT is the unmodified official LeRobot implementation at LEROBOT_REVISION.
No hub access, image backbone, expert solver or simulator is used here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from collections import deque
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
ACTION_ENCODINGS = ("absolute", "arm_delta")
ACTION_ENCODING_SEMANTICS = {
    "absolute": "absolute_joint_position_target_rad",
    "arm_delta": "joint_delta_arm_absolute_gripper",
}


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
    action_encoding: str = "absolute"

    def __post_init__(self):
        if self.action_encoding not in ACTION_ENCODINGS:
            raise ValueError(f"Unknown action encoding {self.action_encoding!r}")

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
    def __init__(self, stats: dict[str, dict[str, list[float]]],
                 action_encoding: str = "absolute", velocity_scale_floor: float = 0.0,
                 robot_velocity_mask: bool = False, object_velocity_mask: bool = False):
        if action_encoding not in ACTION_ENCODINGS:
            raise ValueError(f"Unknown action encoding {action_encoding!r}")
        if not np.isfinite(velocity_scale_floor) or velocity_scale_floor < 0:
            raise ValueError("Velocity scale floor must be finite and nonnegative")
        if not isinstance(robot_velocity_mask, bool):
            raise ValueError("Robot velocity mask must be an explicit boolean")
        if not isinstance(object_velocity_mask, bool):
            raise ValueError("Object velocity mask must be an explicit boolean")
        self.stats = stats
        self.action_encoding = action_encoding
        self.velocity_scale_floor = float(velocity_scale_floor)
        self.robot_velocity_mask = robot_velocity_mask
        self.object_velocity_mask = object_velocity_mask

    @staticmethod
    def _anchor_for(values: np.ndarray, anchor: np.ndarray | None) -> np.ndarray:
        if anchor is None:
            raise ValueError("Arm-delta actions require the current raw joint-state anchor")
        anchor = np.asarray(anchor, dtype=np.float64)
        if values.shape[-1] != 6 or anchor.shape[-1:] != (6,) or not np.isfinite(anchor).all():
            raise ValueError("Action and finite joint-state anchor must have six coordinates")
        # A chunk is anchored to its current observation, never to future states.
        if values.ndim == 3 and anchor.ndim == 2:
            anchor = anchor[:, None, :]
        try:
            return np.broadcast_to(anchor, values.shape)
        except ValueError as error:
            raise ValueError("Joint-state anchor cannot broadcast to actions") from error

    def encoded_actions(self, values: np.ndarray, anchor: np.ndarray | None = None) -> np.ndarray:
        encoded = np.asarray(values, dtype=np.float64).copy()
        if self.action_encoding == "arm_delta":
            encoded[..., :5] -= self._anchor_for(encoded, anchor)[..., :5]
        return encoded

    @classmethod
    def fit(cls, rows: dict[str, np.ndarray], action_encoding: str = "absolute",
            velocity_scale_floor: float = 0.0, robot_velocity_mask: bool = False,
            object_velocity_mask: bool = False) -> "StateNormalizer":
        result = cls({}, action_encoding, velocity_scale_floor, robot_velocity_mask, object_velocity_mask)
        stats = {}
        for key in (STATE, ENV_STATE, ACTION):
            values = np.asarray(rows[key], dtype=np.float64)
            if values.ndim != 2 or not len(values) or not np.isfinite(values).all():
                raise ValueError(f"Invalid finite training matrix for {key}")
            if key == ACTION:
                values = result.encoded_actions(values, rows[STATE])
            # Near-constant columns use unit scale rather than amplifying tiny
            # physical jitter; this matters for fixed obstacles/target poses.
            scale = values.std(axis=0)
            scale[scale < 1e-4] = 1.0
            if key == ENV_STATE and velocity_scale_floor:
                # The first six environment coordinates are robot qvel, rad/s.
                # Fit only these training rows, with an explicit physical floor.
                scale[:6] = np.maximum(values.std(axis=0)[:6], velocity_scale_floor)
            stats[key] = {"mean": values.mean(axis=0).tolist(), "std": scale.tolist()}
        result.stats = stats
        return result

    def normalize(self, key: str, values: np.ndarray, anchor: np.ndarray | None = None) -> np.ndarray:
        stat = self.stats[key]
        values = np.asarray(values)
        # Validate before masking, so a sensor NaN never becomes a safe zero.
        if not np.isfinite(values).all():
            raise ValueError(f"Nonfinite observation/action cannot be normalized: {key}")
        values = self.encoded_actions(values, anchor) if key == ACTION else values
        normalized = ((values - np.asarray(stat["mean"])) /
                      np.asarray(stat["std"])).astype(np.float32)
        if not np.isfinite(normalized).all():
            raise ValueError(f"Nonfinite normalized observation/action: {key}")
        if key == ENV_STATE and self.robot_velocity_mask:
            normalized[..., :6] = 0
        if key == ENV_STATE and self.object_velocity_mask:
            normalized[..., 13:19] = 0
        return normalized

    def action_radians(self, tensor: torch.Tensor, anchor: np.ndarray | None = None) -> np.ndarray:
        """Decode to absolute joint targets; raw current q is needed for arm_delta."""
        stat = self.stats[ACTION]
        values = tensor.detach().cpu().numpy()
        actions = values * np.asarray(stat["std"]) + np.asarray(stat["mean"])
        if self.action_encoding == "arm_delta":
            actions[..., :5] += self._anchor_for(actions, anchor)[..., :5]
        return actions


def load_policy_checkpoint(path: str, device: str = "cpu"):
    """Load this experiment's local weights, not an arbitrary hub checkpoint."""
    data = torch.load(path, map_location="cpu", weights_only=True)
    if data.get("format") != "so101-state-policy-v1":
        raise ValueError("Unsupported policy checkpoint format")
    spec_data = dict(data["model_spec"])
    encoding = data.get("action_encoding", spec_data.get("action_encoding", "absolute"))
    if "action_encoding" in spec_data and spec_data["action_encoding"] != encoding:
        raise ValueError("Checkpoint and model action encodings differ")
    spec_data.setdefault("action_encoding", encoding)
    spec = ModelSpec(**spec_data)
    policy = build_policy(spec, device)
    policy.load_state_dict(data["state_dict"])
    policy.eval()
    options = data.get("normalization_options", {})
    normalizer = StateNormalizer(data["normalization"], encoding,
                                 options.get("velocity_scale_floor_rad_s", 0.0),
                                 options.get("robot_velocity_mask", False),
                                 options.get("object_velocity_mask", False))
    if "learned_gripper_classifier" in data:
        from learning_gripper import LearnedGripperPolicy
        if spec.model != "act" or spec.use_vae or spec.dropout != 0:
            raise ValueError("Learned gripper requires a deterministic frozen ACT base")
        gripper_hashes = data["train_dataset_sha256"]
        if "composition" in data:
            from compose_state_policy import validate_composed_policy_metadata
            gripper_hashes = validate_composed_policy_metadata(data)
        policy = LearnedGripperPolicy(policy, data["learned_gripper_classifier"],
                                      data["normalization"][ACTION], gripper_hashes, device).eval()
    return policy, normalizer, data


class StatePolicyRunner:
    """Simulation-facing adapter: current physical observation -> radian target.

Default: ACT predicts a chunk but executes its first action, then reobserves.
The optional execution ablation decodes a chunk once at its current-q anchor
and caches absolute commands. No stage, clock, expert or hidden replay input.
"""
    def __init__(self, policy, normalizer, metadata, device, *, execute_chunk_steps: int = 1):
        if (metadata.get("training_loss_scope") == "arm5_only"
                and "learned_gripper_classifier" not in metadata):
            raise ValueError("Arm-only checkpoint needs its learned gripper before policy execution")
        self.policy, self.normalizer, self.metadata = policy, normalizer, metadata
        self.device = device
        spec = metadata["model_spec"]
        if (isinstance(execute_chunk_steps, bool) or not isinstance(execute_chunk_steps, int)
                or not 1 <= execute_chunk_steps <= spec.get("chunk_size", 1)):
            raise ValueError("Execute chunk steps must be an integer from one through chunk_size")
        if spec.get("model") == "mlp" and execute_chunk_steps != 1:
            raise ValueError("MLP only supports executing one action per observation")
        self.execute_chunk_steps = execute_chunk_steps
        self._absolute_actions = deque()

    def reset(self) -> None:
        self._absolute_actions.clear()
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
        anchor = np.asarray(observation[STATE])[None].copy()
        if self.execute_chunk_steps == 1:
            prediction = self.policy.select_action(batch)
            if prediction.shape != (1, spec["action_dim"]) or not torch.isfinite(prediction).all():
                raise RuntimeError("Policy returned a nonfinite/malformed joint target")
            action = self.normalizer.action_radians(prediction, anchor=anchor)[0]
        else:
            if not self._absolute_actions:
                prediction = self.policy.predict_action_chunk(batch)
                if (prediction.shape != (1, spec["chunk_size"], spec["action_dim"])
                        or not torch.isfinite(prediction).all()):
                    raise RuntimeError("Policy returned a nonfinite/malformed action chunk")
                # Decode ALL queued residuals against this one raw-q snapshot.
                # A later tick must not add its changed q to a cached residual.
                actions = self.normalizer.action_radians(prediction, anchor=anchor)[0]
                if not np.isfinite(actions).all():
                    raise RuntimeError("Decoded action chunk is nonfinite")
                self._absolute_actions.extend(action.copy() for action in actions[:self.execute_chunk_steps])
            action = self._absolute_actions.popleft()
        if action.shape != (spec["action_dim"],) or not np.isfinite(action).all():
            raise RuntimeError("Policy returned a nonfinite/malformed joint target")
        return action


def load_policy(path: str, device: str = "cpu", *, execute_chunk_steps: int = 1) -> StatePolicyRunner:
    policy, normalizer, metadata = load_policy_checkpoint(path, device)
    return StatePolicyRunner(policy, normalizer, metadata, device, execute_chunk_steps=execute_chunk_steps)
