"""Image/state adapter for the pinned official ACT, separate from state policies.

Privileged environment truth is allowed in physics/audit code, never in a
VisionPolicyRunner input. Images are measured at the current command boundary.
"""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
import hashlib
import inspect
import json
from pathlib import Path

import h5py
import numpy as np
import torch

STATE = "observation.state"
IMAGE = "observation.images.workcell"
ACTION = "action"
VISION_INPUT_KEYS = (STATE, IMAGE)
VISION_FORMAT = "so101-vision-policy-v1"
LEROBOT_REVISION = "e0d50211ef236143ae867228662b7dfaba554f02"
OFFICIAL_SOURCE_SHA256 = {
    "ACTPolicy": "83d954f79ccd3eaa6774dbea92524939c8ac08359bb355ba7cd37b8601e1e3af",
    "ACTConfig": "35a60c0dd3c811b137b5eb035bdbd40d40e2c24ba0cda61756052e6e1c829282",
}
VISUAL_MODEL_SPEC = {
    "vision_backbone": "resnet18", "pretrained_backbone_weights": None,
    "chunk_size": 16, "dim_model": 256, "n_heads": 4,
    "dim_feedforward": 1024, "n_encoder_layers": 2, "n_decoder_layers": 2,
    "use_vae": False, "dropout": 0.,
}
RGB_NORMALIZATION = {"storage": "uint8_rgb_hwc", "policy_tensor": "float32_chw_div255",
                     "image_mean_std": None}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def visual_source_hashes():
    root = Path(__file__).resolve().parent
    return {name: sha256(root / name) for name in ("learning_vision.py", "run_vision_learning.py")}


def validate_resource_report(report, camera, visual_hashes, raw_hashes):
    expected = {"status": "passed", "kind": "visual_act_cuda_five_step_microbenchmark",
                "source_sha256": visual_source_hashes(), "camera": camera,
                "visual_dataset_sha256": visual_hashes, "raw_dataset_sha256": raw_hashes,
                "model_spec": VISUAL_MODEL_SPEC, "rgb_normalization": RGB_NORMALIZATION,
                "official_source_sha256": OFFICIAL_SOURCE_SHA256, "lerobot_revision": LEROBOT_REVISION}
    if any(report.get(key) != value for key, value in expected.items()):
        raise ValueError("Resource report differs from implementation, camera, dataset or official ACT")
    batch = report.get("selected_batch_size")
    selected = [a for a in report.get("attempts", []) if a.get("batch_size") == batch and a.get("status") == "passed"]
    if batch not in (4, 8) or len(selected) != 1 or selected[0].get("steps") != 5 or len(selected[0].get("step_s", [])) != 5:
        raise ValueError("Resource gate requires a complete five-step selected batch 4 or 8 attempt")
    memory = selected[0].get("memory_after", {})
    peaks = [memory.get(key) for key in ("peak_allocated_mib", "peak_reserved_mib")]
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) or not 0 <= v <= 3200 for v in peaks):
        raise ValueError("Resource gate exceeds the 3200MiB limit or lacks finite peaks")
    return batch


@dataclass(frozen=True)
class CameraSpec:
    width: int = 128
    height: int = 128
    lookat: tuple = (.24, 0., .06)
    distance: float = .60
    azimuth: float = 135.
    elevation: float = -40.
    shadow_size: int = 512
    multisamples: int = 0

    def to_dict(self):
        result = asdict(self)
        result["lookat"] = list(self.lookat)
        return result

    def validate(self):
        if (self.width, self.height) != (128, 128):
            raise ValueError("This bounded visual diagnostic fixes RGB at 128x128")
        values = (*self.lookat, self.distance, self.azimuth, self.elevation)
        if len(self.lookat) != 3 or not np.isfinite(values).all() or self.distance <= 0:
            raise ValueError("Invalid fixed camera")
        if self.shadow_size != 512 or self.multisamples != 0:
            raise ValueError("Unexpected rendering resource parameters")


def make_renderer(model, camera_spec):
    """Allocate a small offscreen buffer; these fields change visuals only."""
    import mujoco
    camera_spec.validate()
    model.vis.global_.offwidth = camera_spec.width
    model.vis.global_.offheight = camera_spec.height
    model.vis.quality.shadowsize = camera_spec.shadow_size
    model.vis.quality.offsamples = camera_spec.multisamples
    camera = mujoco.MjvCamera()
    camera.lookat[:] = camera_spec.lookat
    camera.distance = camera_spec.distance
    camera.azimuth = camera_spec.azimuth
    camera.elevation = camera_spec.elevation
    renderer = mujoco.Renderer(model, height=camera_spec.height, width=camera_spec.width)
    return renderer, camera


def capture_rgb(renderer, camera, data):
    """Render without calling mj_forward or changing the physical integration."""
    before = [np.array(value, copy=True) for value in
              (data.qpos, data.qvel, data.ctrl, data.qacc_warmstart)]
    time_before = float(data.time)
    renderer.update_scene(data, camera=camera)
    image = np.array(renderer.render(), copy=True)
    after = (data.qpos, data.qvel, data.ctrl, data.qacc_warmstart)
    if float(data.time) != time_before or any(not np.array_equal(a, b) for a, b in zip(before, after)):
        raise RuntimeError("Rendering modified the physical state")
    validate_rgb(image)
    return image


def validate_rgb(image):
    image = np.asarray(image)
    if image.shape != (128, 128, 3) or image.dtype != np.uint8:
        raise ValueError("Expected uint8 RGB image with shape (128,128,3)")
    return image


class VisionNormalizer:
    """Only q6/action6 train statistics; fixed RGB conversion is shared online."""
    def __init__(self, stats):
        if set(stats) != {STATE, ACTION}:
            raise ValueError("Visual normalization must contain only state/action")
        for key, value in stats.items():
            if set(value) != {"mean", "std"}:
                raise ValueError("Invalid normalization fields")
            if (np.asarray(value["mean"]).shape != (6,) or
                    np.asarray(value["std"]).shape != (6,) or
                    not np.isfinite([value["mean"], value["std"]]).all() or
                    np.any(np.asarray(value["std"]) <= 0)):
                raise ValueError("Invalid finite six-axis normalization")
        self.stats = stats

    @classmethod
    def fit(cls, states, actions):
        states, actions = np.asarray(states), np.asarray(actions)
        if states.ndim != 2 or states.shape[1:] != (6,) or actions.shape != states.shape:
            raise ValueError("State/action training matrices must be Nx6")
        if not len(states) or not np.isfinite(states).all() or not np.isfinite(actions).all():
            raise ValueError("Need finite eligible training rows")
        encoded = actions.copy()
        encoded[:, :5] -= states[:, :5]
        stats = {}
        for key, values in ((STATE, states), (ACTION, encoded)):
            scale = values.std(axis=0)
            scale[scale < 1e-4] = 1.
            stats[key] = {"mean": values.mean(axis=0).tolist(), "std": scale.tolist()}
        return cls(stats)

    def normalize_state(self, state):
        state = np.asarray(state)
        if state.shape[-1:] != (6,) or not np.isfinite(state).all():
            raise ValueError("Invalid finite state6")
        stat = self.stats[STATE]
        return ((state - stat["mean"]) / stat["std"]).astype(np.float32)

    def normalize_actions(self, actions, anchor):
        values, anchor = np.asarray(actions).copy(), np.asarray(anchor)
        if values.ndim != 2 or values.shape[1:] != (6,) or anchor.shape != (6,):
            raise ValueError("Actions require one current six-axis anchor")
        if not np.isfinite(values).all() or not np.isfinite(anchor).all():
            raise ValueError("Nonfinite action/anchor")
        values[:, :5] -= anchor[:5]
        stat = self.stats[ACTION]
        return ((values - stat["mean"]) / stat["std"]).astype(np.float32)

    def decode_actions(self, normalized, anchor):
        values = np.asarray(normalized)
        anchor = np.asarray(anchor)
        if values.ndim != 2 or values.shape[1:] != (6,) or anchor.shape != (6,):
            raise ValueError("Decode requires chunkx6 and current state6")
        if not np.isfinite(values).all() or not np.isfinite(anchor).all():
            raise ValueError("Nonfinite normalized action/anchor")
        stat = self.stats[ACTION]
        result = values * stat["std"] + stat["mean"]
        result[:, :5] += anchor[:5]
        return result


def rgb_tensor(images, device):
    images = np.asarray(images)
    if images.ndim != 4 or images.shape[1:] != (128, 128, 3) or images.dtype != np.uint8:
        raise ValueError("Expected batch of uint8 RGB128 images")
    return torch.from_numpy(np.ascontiguousarray(images.transpose(0, 3, 1, 2))).to(
        device=device, dtype=torch.float32) / 255.


def segment_lengths(episode_ids, frame_ids, chunk_size=16):
    """Chunk lengths preserve gaps created by invalid labels and episode ends."""
    episodes, frames = np.asarray(episode_ids), np.asarray(frame_ids)
    if episodes.ndim != 1 or frames.shape != episodes.shape or chunk_size < 1:
        raise ValueError("Invalid chunk index arrays")
    lengths = np.ones(len(frames), dtype=np.int64)
    for start in range(len(frames)):
        end = start + 1
        while end < min(len(frames), start + chunk_size):
            if episodes[end] != episodes[start] or frames[end] != frames[end - 1] + 1:
                break
            end += 1
        lengths[start] = end - start
    return lengths


def _startup_sampling_mask(frames, weight):
    frames = np.asarray(frames)
    if (frames.ndim != 1 or not len(frames) or frames.dtype.kind not in "iu" or
            np.any(frames < 0)):
        raise ValueError("Startup sampling requires nonempty nonnegative integer raw frame indices")
    if (isinstance(weight, (bool, np.bool_)) or
            not isinstance(weight, (int, np.integer)) or weight not in (1, 5)):
        raise ValueError("Startup sampling weight must be integer 1 or 5")
    return frames < 50


def startup_sampling_order(frames, rng, weight=1):
    """Shuffle eligible chunk starts; input raw frames already exclude invalid labels."""
    startup = _startup_sampling_mask(frames, weight)
    if weight == 1 or not startup.any():
        # Keep both the old order and subsequent RNG state exactly unchanged.
        return rng.permutation(len(startup))
    pool = np.repeat(np.arange(len(startup), dtype=np.int64),
                     np.where(startup, weight, 1))
    return rng.permutation(pool)


def startup_sampling_metadata(frames, episodes, weight=1):
    startup = _startup_sampling_mask(frames, weight)
    episodes = np.asarray(episodes)
    if (episodes.shape != startup.shape or episodes.dtype.kind not in "iu" or
            np.any(episodes < 0)):
        raise ValueError("Startup sampling requires matching nonnegative integer episode indices")
    unique_rows, startup_rows = len(startup), int(startup.sum())
    pool_len = unique_rows + (int(weight) - 1) * startup_rows
    per_episode = []
    for episode_id in np.unique(episodes):
        selected = episodes == episode_id
        rows, starts = int(selected.sum()), int(startup[selected].sum())
        per_episode.append({"episode_id": int(episode_id), "unique_rows": rows,
                            "startup_rows": starts,
                            "pool_len": rows + (int(weight) - 1) * starts})
    return {"mask": "label_valid && original_raw_frame_index < 50",
            "weight": int(weight), "raw_frame_threshold": 50,
            "sampling_unit": "eligible_chunk_start", "unique_rows": unique_rows,
            "startup_rows": startup_rows, "per_episode": per_episode,
            "pool_len": pool_len,
            "theoretical_startup_fraction": int(weight) * startup_rows / pool_len,
            "epoch_semantics": ("one permutation of unique eligible chunk starts" if pool_len == unique_rows else
                                "one permutation of the expanded index pool; not a unique-row pass")}


def local_balance_groups(states, frames, episodes, stages):
    """Select real near-q startup/settle rows; these fields never enter the policy."""
    states, frames, episodes, stages = map(np.asarray, (states, frames, episodes, stages))
    _startup_sampling_mask(frames, 5)
    if (states.shape != (len(frames), 6) or states.dtype.kind not in "fiu" or
            not np.isfinite(states).all() or
            episodes.shape != frames.shape or episodes.dtype.kind not in "iu" or
            np.any(episodes < 0) or stages.shape != frames.shape):
        raise ValueError("Local balance requires finite q6 and matching episode/stage rows")
    anchor = np.flatnonzero((episodes == 0) & (frames == 0))
    if len(anchor) != 1:
        raise ValueError("Local balance requires exactly one episode0/frame0 anchor")
    near = np.linalg.norm(states - states[anchor[0]], axis=1) <= .01
    groups = np.zeros(len(frames), dtype=np.int8)
    groups[near & (frames < 50) & (stages == "approach")] = 1
    groups[near & (frames >= 50) & (stages == "settle")] = 2
    if not np.any(groups == 1) or not np.any(groups == 2):
        raise ValueError("Local balance requires both startup and settle groups")
    return groups


def _validate_local_groups(groups, shape):
    groups = np.asarray(groups)
    if (groups.shape != shape or groups.dtype.kind not in "iu" or
            not np.isin(groups, [0, 1, 2]).all() or
            not np.any(groups == 1) or not np.any(groups == 2)):
        raise ValueError("Local balance requires matching integer groups 0/1/2 and both local groups")
    return groups


def local_balance_sampling_metadata(frames, episodes, groups, weight=5):
    base = startup_sampling_metadata(frames, episodes, weight)
    groups = _validate_local_groups(groups, np.asarray(frames).shape)
    weights = np.where(np.asarray(frames) < 50, weight, 1)
    counts = [int(weights[groups == group].sum()) for group in (1, 2)]
    slots = sum(counts)
    if slots % 2:
        raise ValueError("Exact local 1:1 balance requires an even number of base local slots")
    return {"radius_rad": .01, "distance": "unscaled L2 of all six joints to episode0/raw_frame0",
            "selection": "label_valid; startup: raw<50 && approach; settle: raw>=50 && settle",
            "startup_rows": int((groups == 1).sum()), "settle_rows": int((groups == 2).sum()),
            "startup_indices": np.flatnonzero(groups == 1).tolist(),
            "settle_indices": np.flatnonzero(groups == 2).tolist(),
            "base_startup_slots": counts[0], "base_settle_slots": counts[1],
            "pool_slots": slots, "target_slots_per_group": slots // 2,
            "total_pool_len": base["pool_len"],
            "balance_scope": "complete-pool chunk starts, not partial draws or valid action slots",
            "outside_scope": "all nonlocal positions/values of original shuffled pool unchanged",
            "within_group": "uniform permutations of unique rows, full cycles then remainder"}


def local_balance_sampling_order(base_order, groups, rng):
    """Replace only local slots, preserving base RNG and every nonlocal position."""
    base_order = np.asarray(base_order)
    groups = np.asarray(groups)
    if groups.ndim != 1:
        raise ValueError("Local groups must be one dimensional")
    groups = _validate_local_groups(groups, groups.shape)
    if (base_order.ndim != 1 or base_order.dtype.kind not in "iu" or
            not len(base_order) or np.any(base_order < 0) or np.any(base_order >= len(groups))):
        raise ValueError("Invalid base sampling order")
    positions = np.flatnonzero(groups[base_order] != 0)
    if not len(positions) or len(positions) % 2:
        raise ValueError("Exact local 1:1 balance requires a positive even local slot count")
    count = len(positions) // 2
    draws = []
    for group in (1, 2):
        rows = np.flatnonzero(groups == group)
        cycles, remainder = divmod(count, len(rows))
        draws.extend(rng.permutation(rows) for _ in range(cycles))
        if remainder:
            draws.append(rng.permutation(rows)[:remainder])
    order = base_order.copy()
    order[positions] = rng.permutation(np.concatenate(draws))
    return order


class VisionDataset:
    """Keep only uint8 frames on disk, index valid labels, normalize per batch."""
    def __init__(self, paths):
        from learning_data import load_episode
        paths = [Path(path).resolve() for path in paths]
        if not paths or len(set(paths)) != len(paths):
            raise ValueError("Need unique visual episode paths")
        self.paths, self.archives = paths, []
        self.states, self.actions, self.frames, self.episodes = [], [], [], []
        self.stages = []
        self.raw_hashes, self.visual_hashes, self.metadata = [], [], []
        self.camera = None
        try:
            for episode_id, path in enumerate(paths):
                episode = load_episode(path)
                if not episode["eligible_for_training"]:
                    raise ValueError("Visual training requires successful eligible episodes")
                archive = h5py.File(path, "r")
                self.archives.append(archive)
                if (archive.attrs.get("vision_format") != "so101-synchronized-rgb-v1" or
                        not bool(archive.attrs.get("vision_complete", False))):
                    raise ValueError("Incomplete or unsupported visual archive")
                if not bool(archive.attrs.get("vision_raw64_exact", False)):
                    raise ValueError("Visual archive lacks exact raw64 replay")
                camera = json.loads(archive.attrs["camera_json"])
                CameraSpec(**camera).validate()
                if self.camera is not None and self.camera != camera:
                    raise ValueError("Mixed cameras need an explicit adapter")
                self.camera = camera
                count = len(episode["timestamp"])
                rgb = archive[IMAGE]
                if rgb.shape != (count, 128, 128, 3) or rgb.dtype != np.uint8:
                    raise ValueError("Shifted/malformed image rows")
                if not np.array_equal(archive["image_frame_index"][:], episode["frame_index"]):
                    raise ValueError("Image frame indices differ from observations")
                if not np.array_equal(archive["image_timestamp"][:], episode["timestamp"]):
                    raise ValueError("Image timestamps differ from obs_t")
                mask = episode["label_valid"]
                self.states.append(episode[STATE][mask])
                self.actions.append(episode[ACTION][mask])
                self.frames.append(episode["frame_index"][mask])
                self.episodes.append(np.full(mask.sum(), episode_id, dtype=np.int64))
                self.stages.append(episode["stage"][mask])
                self.raw_hashes.append(str(archive.attrs["source_raw_sha256"]))
                self.visual_hashes.append(sha256(path))
                self.metadata.append(episode["metadata"])
            self.states, self.actions, self.frames, self.episodes = (
                np.concatenate(pieces) for pieces in
                (self.states, self.actions, self.frames, self.episodes))
            self.stages = np.concatenate(self.stages)
            if len(set(self.raw_hashes)) != len(self.raw_hashes):
                raise ValueError("Repeated source episodes would duplicate training labels")
            if len({m["control_period_s"] for m in self.metadata}) != 1 or len({m["model_sha256"] for m in self.metadata}) != 1:
                raise ValueError("Mixed physics sources/control periods")
            if self.metadata[0]["control_period_s"] != .02:
                raise ValueError("Visual diagnostic fixes the control period at 20ms")
            if (len({m["physics_dt_s"] for m in self.metadata}) != 1 or
                    self.metadata[0]["physics_dt_s"] != .002 or
                    len({json.dumps(m["scene_configuration"], sort_keys=True) for m in self.metadata}) != 1):
                raise ValueError("Mixed dynamics/scenes or non-2ms physics")
            self.normalizer = VisionNormalizer.fit(self.states, self.actions)
            self.lengths = segment_lengths(self.episodes, self.frames)
            self.gripper_labels = np.unique(self.actions[:, 5])
            if self.gripper_labels.shape != (2,):
                raise ValueError("Nearest jaw projection requires exactly two trained labels")
        except Exception:
            self.close()
            raise

    def __len__(self):
        return len(self.states)

    def batch(self, selection, device):
        selection = np.asarray(selection, dtype=np.int64)
        if selection.ndim != 1 or not len(selection) or np.any(selection < 0) or np.any(selection >= len(self)):
            raise ValueError("Invalid batch indices")
        images = np.stack([self.archives[self.episodes[i]][IMAGE][self.frames[i]] for i in selection])
        actions = np.zeros((len(selection), 16, 6), dtype=np.float32)
        padding = np.ones((len(selection), 16), dtype=bool)
        for row, index in enumerate(selection):
            count = self.lengths[index]
            actions[row, :count] = self.normalizer.normalize_actions(
                self.actions[index:index + count], self.states[index])
            padding[row, :count] = False
        return {STATE: torch.from_numpy(self.normalizer.normalize_state(self.states[selection])).to(device),
                IMAGE: rgb_tensor(images, device),
                ACTION: torch.from_numpy(actions).to(device),
                "action_is_pad": torch.from_numpy(padding).to(device)}

    def close(self):
        for archive in getattr(self, "archives", []):
            archive.close()
        self.archives = []


def build_visual_policy(device="cpu"):
    from lerobot.configs.types import FeatureType, PolicyFeature
    from lerobot.policies.act.configuration_act import ACTConfig
    from lerobot.policies.act.modeling_act import ACTPolicy
    for cls in (ACTPolicy, ACTConfig):
        if sha256(inspect.getfile(cls)) != OFFICIAL_SOURCE_SHA256[cls.__name__]:
            raise RuntimeError("Official ACT source differs from pinned revision")
    config = ACTConfig(
        input_features={STATE: PolicyFeature(FeatureType.STATE, (6,)),
                        IMAGE: PolicyFeature(FeatureType.VISUAL, (3, 128, 128))},
        output_features={ACTION: PolicyFeature(FeatureType.ACTION, (6,))},
        device=device, push_to_hub=False, pretrained_backbone_weights=None,
        vision_backbone="resnet18", chunk_size=16, n_action_steps=1,
        dim_model=256, n_heads=4, dim_feedforward=1024,
        n_encoder_layers=2, n_decoder_layers=2, use_vae=False, dropout=0.)
    return ACTPolicy(config).to(device)


def load_visual_checkpoint(path, device="cpu"):
    data = torch.load(path, map_location="cpu", weights_only=True)
    if (data.get("format") != VISION_FORMAT or data.get("policy_input_keys") != list(VISION_INPUT_KEYS) or
            data.get("lerobot_revision") != LEROBOT_REVISION or
            data.get("official_source_sha256") != OFFICIAL_SOURCE_SHA256 or
            data.get("model_spec") != VISUAL_MODEL_SPEC or
            data.get("rgb_normalization") != RGB_NORMALIZATION or
            data.get("source_sha256") != visual_source_hashes() or
            data.get("action_encoding") != "arm_delta_absolute_jaw" or
            data.get("control_period_s") != .02 or data.get("physics_dt_s") != .002):
        raise ValueError("Incompatible visual policy checkpoint")
    text = data.get("resource_report_text")
    if not isinstance(text, str) or hashlib.sha256(text.encode("utf8")).hexdigest() != data.get("resource_report_sha256"):
        raise ValueError("Checkpoint resource report bytes do not match its SHA256")
    validate_resource_report(json.loads(text), data["camera"], data["visual_dataset_sha256"], data["raw_dataset_sha256"])
    CameraSpec(**data["camera"]).validate()
    normalizer = VisionNormalizer(data["normalization"])
    labels = np.asarray(data["gripper_labels_rad"], dtype=float)
    if labels.shape != (2,) or not np.isfinite(labels).all() or labels[0] >= labels[1]:
        raise ValueError("Invalid learned jaw support")
    policy = build_visual_policy(device)
    policy.load_state_dict(data["state_dict"], strict=True)
    policy.eval()
    return policy, normalizer, data


class VisionPolicyRunner:
    def __init__(self, policy, normalizer, metadata, device="cpu", execute_chunk_steps=16):
        if execute_chunk_steps not in range(1, 17):
            raise ValueError("Chunk execution must be between 1 and 16")
        self.policy, self.normalizer, self.metadata = policy, normalizer, metadata
        self.device, self.execute_chunk_steps = device, execute_chunk_steps
        self.queue = deque()
        self.labels = np.asarray(metadata["gripper_labels_rad"], dtype=float)

    def reset(self):
        self.queue.clear()
        self.policy.reset()

    @torch.no_grad()
    def predict(self, observation):
        if set(observation) != set(VISION_INPUT_KEYS):
            raise ValueError("Visual policy accepts only state6 and RGB; no privileged/audit inputs")
        state = np.asarray(observation[STATE])
        if state.shape != (6,) or not np.isfinite(state).all():
            raise ValueError("Invalid current state6")
        image = validate_rgb(observation[IMAGE])
        if not self.queue:
            batch = {STATE: torch.from_numpy(self.normalizer.normalize_state(state)[None]).to(self.device),
                     IMAGE: rgb_tensor(image[None], self.device)}
            prediction = self.policy.predict_action_chunk(batch)
            if prediction.shape != (1, 16, 6) or not torch.isfinite(prediction).all():
                raise RuntimeError("Invalid visual action chunk")
            commands = self.normalizer.decode_actions(prediction[0].cpu().numpy(), state)
            # All residuals use the chunk-start anchor, never a later q snapshot.
            self.queue.extend(a.copy() for a in commands[:self.execute_chunk_steps])
        raw = self.queue.popleft()
        projected = raw.copy()
        projected[5] = self.labels[0] if raw[5] <= self.labels.mean() else self.labels[1]
        return raw, projected
