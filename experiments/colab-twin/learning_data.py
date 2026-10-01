"""Neutral HDF5 protocol for MuJoCo expert transitions, independent of a trainer.

This is an explicitly versioned adapter format, not a LeRobot native dataset.
Only ``observation.state`` and ``observation.environment_state`` are policy
inputs; clocks, expert stages and perturbation flags remain audit columns.
Raw transitions use float64 for faithful physics replay. A trainer explicitly
normalizes and casts policy tensors to float32; old float32 v1 archives remain
readable without relabelling their recorded task outcome.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import tempfile

import h5py
import numpy as np

SCHEMA_VERSION = "so101-state-transition-v1"
STATE_FEATURE_NAMES = (
    "shoulder_pan.position_rad", "shoulder_lift.position_rad",
    "elbow_flex.position_rad", "wrist_flex.position_rad",
    "wrist_roll.position_rad", "gripper.position_rad",
)
ENVIRONMENT_FEATURE_NAMES = (
    *(name.replace("position_rad", "velocity_rad_s") for name in STATE_FEATURE_NAMES),
    "object.position_x_m", "object.position_y_m", "object.position_z_m",
    "object.quaternion_w", "object.quaternion_x", "object.quaternion_y", "object.quaternion_z",
    "object.linear_velocity_x_m_s", "object.linear_velocity_y_m_s", "object.linear_velocity_z_m_s",
    "object.angular_velocity_x_rad_s", "object.angular_velocity_y_rad_s", "object.angular_velocity_z_rad_s",
    "goal.position_x_m", "goal.position_y_m", "goal.position_z_m",
    "obstacle.position_x_m", "obstacle.position_y_m", "obstacle.position_z_m",
    "obstacle.half_size_x_m", "obstacle.half_size_y_m", "obstacle.half_size_z_m",
    "pad_gripper.normal_force_n", "pad_moving_jaw.normal_force_n",
)
POLICY_OBSERVATION_KEYS = ("observation.state", "observation.environment_state")
FEATURE_NAMES = {
    "observation.state": STATE_FEATURE_NAMES,
    "observation.environment_state": ENVIRONMENT_FEATURE_NAMES,
    "action": STATE_FEATURE_NAMES,
    "executed_action": STATE_FEATURE_NAMES,
}
_FLOAT_COLUMNS = {
    "observation.state": 6, "observation.environment_state": 30,
    "next_observation.state": 6, "next_observation.environment_state": 30,
    "action": 6, "executed_action": 6,
}
_TIME_ATOL = 1e-8


def _json(value):
    def numpy_value(item):
        if isinstance(item, np.ndarray):
            return item.tolist()
        if isinstance(item, np.generic):
            return item.item()
        raise TypeError(f"Not JSON metadata: {type(item).__name__}")
    return json.dumps(value, sort_keys=True, allow_nan=False, default=numpy_value)


def _metadata(value):
    result = json.loads(_json(value))
    for key in ("control_period_s", "physics_dt_s", "seed", "model_sha256", "scene_configuration"):
        if key not in result:
            raise ValueError(f"Missing metadata: {key}")
    period, physics_dt = result["control_period_s"], result["physics_dt_s"]
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0
           for v in (period, physics_dt)):
        raise ValueError("Control period and physics dt must be finite positive seconds")
    ticks = period / physics_dt
    if not math.isclose(ticks, round(ticks), abs_tol=1e-8) or ticks < 1:
        raise ValueError("Control period must be an integer number of physics steps")
    seed = result["seed"]
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    model_hash = result["model_sha256"]
    if not isinstance(model_hash, str) or len(model_hash) != 64 or any(c not in "0123456789abcdef" for c in model_hash):
        raise ValueError("model_sha256 must be a lowercase SHA256 hex digest")
    if not isinstance(result["scene_configuration"], dict):
        raise ValueError("scene_configuration must be a JSON object")
    return result


def _vector(value, count, name, *, finite=True):
    result = np.array(value, dtype=np.float64, copy=True)
    if result.shape != (count,) or (finite and not np.all(np.isfinite(result))):
        raise ValueError(f"{name} must be a finite {count}-vector")
    return result


def _observation(value):
    result = {key: _vector(value[key], len(FEATURE_NAMES[key]), key) for key in POLICY_OBSERVATION_KEYS}
    timestamp = value.get("time_s")
    if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float, np.number)) or not np.isfinite(timestamp):
        raise ValueError("Observation time_s must be a finite simulation timestamp")
    result["time_s"] = float(timestamp)
    return result


class EpisodeRecorder:
    """Record obs_t -> executed_action_t -> obs_t+1, with expert_action_t labels.

    A perturbed command is not a correction label. Pass ``label_valid=False``
    for that transition, and compute the next label from the resulting state.
    Calls copy all arrays, so advancing MuJoCo cannot mutate previous samples.
    ``finalize({'passed': False, ...})`` preserves failed and partial attempts.
    """

    def __init__(self, output_path, metadata):
        self.output_path = Path(output_path)
        if self.output_path.exists():
            raise FileExistsError(self.output_path)
        self.metadata = _metadata(metadata)
        self.rows = []
        self.finalized = False

    def append(self, obs_before, expert_action, executed_action, obs_after,
               label_valid: bool, stage: str, perturbation: bool):
        if self.finalized:
            raise RuntimeError("Episode already finalized")
        if not isinstance(label_valid, (bool, np.bool_)) or not isinstance(perturbation, (bool, np.bool_)):
            raise ValueError("label_valid and perturbation must be booleans")
        if not isinstance(stage, str) or not stage:
            raise ValueError("stage must be a nonempty audit label")
        before, after = _observation(obs_before), _observation(obs_after)
        period = self.metadata["control_period_s"]
        if not math.isclose(after["time_s"] - before["time_s"], period, rel_tol=0, abs_tol=_TIME_ATOL):
            raise ValueError("Transition does not span exactly one control period")
        if self.rows:
            previous = self.rows[-1]["after"]
            if not math.isclose(before["time_s"], previous["time_s"], rel_tol=0, abs_tol=_TIME_ATOL):
                raise ValueError("Noncontiguous transition timestamps")
            if any(not np.allclose(before[key], previous[key], atol=1e-7, rtol=0) for key in POLICY_OBSERVATION_KEYS):
                raise ValueError("obs_before is not the preceding obs_after")
        if expert_action is None and not label_valid:
            expert_action = np.full(6, np.nan)
        action = _vector(expert_action, 6, "expert_action", finite=bool(label_valid))
        executed = _vector(executed_action, 6, "executed_action")
        if perturbation and label_valid:
            raise ValueError("An injected perturbation cannot be a valid expert correction label")
        self.rows.append({"before": before, "after": after, "action": action,
                          "executed_action": executed, "label_valid": bool(label_valid),
                          "stage": stage, "perturbation": bool(perturbation)})

    def finalize(self, report):
        if self.finalized:
            raise RuntimeError("Episode already finalized")
        report = json.loads(_json(report))
        if not isinstance(report.get("passed"), bool):
            raise ValueError("Report must contain an explicit boolean passed")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{self.output_path.name}.", suffix=".partial",
                                                dir=self.output_path.parent)
        os.close(descriptor)
        temporary = Path(temporary)
        try:
            with h5py.File(temporary, "w") as archive:
                archive.attrs["schema_version"] = SCHEMA_VERSION
                archive.attrs["metadata_json"] = _json(self.metadata)
                archive.attrs["report_json"] = _json(report)
                archive.attrs["feature_names_json"] = _json(FEATURE_NAMES)
                archive.attrs["action_semantics"] = "absolute_joint_position_target_rad"
                archive.attrs["storage_precision"] = "raw_float64_policy_tensor_float32"
                archive.attrs["attempt_count"] = 1
                archive.attrs["episode_passed"] = report["passed"]
                for key, width in _FLOAT_COLUMNS.items():
                    if key.startswith("next_"):
                        values = [row["after"][key.removeprefix("next_")] for row in self.rows]
                    elif key in POLICY_OBSERVATION_KEYS:
                        values = [row["before"][key] for row in self.rows]
                    else:
                        values = [row[key] for row in self.rows]
                    archive.create_dataset(key, data=np.asarray(values, dtype=np.float64).reshape(-1, width))
                archive.create_dataset("timestamp", data=np.array([r["before"]["time_s"] for r in self.rows], dtype=np.float64))
                archive.create_dataset("next_timestamp", data=np.array([r["after"]["time_s"] for r in self.rows], dtype=np.float64))
                archive.create_dataset("frame_index", data=np.arange(len(self.rows), dtype=np.int64))
                archive.create_dataset("episode_index", data=np.zeros(len(self.rows), dtype=np.int64))
                for key in ("label_valid", "perturbation"):
                    archive.create_dataset(key, data=np.array([r[key] for r in self.rows], dtype=np.bool_))
                archive.create_dataset("stage", data=np.array([r["stage"] for r in self.rows], dtype=object),
                                       dtype=h5py.string_dtype("utf-8"))
                archive.flush()
            # A same-filesystem hard link publishes only a completely closed
            # archive and refuses overwrite even if another writer raced us.
            with temporary.open("rb") as stream:
                os.fsync(stream.fileno())
            os.link(temporary, self.output_path)
            self.finalized = True
        finally:
            temporary.unlink(missing_ok=True)
        return self.output_path


def load_episode(path):
    """Read and independently audit a whole attempt before exposing training rows."""
    with h5py.File(path, "r") as archive:
        if archive.attrs.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Unsupported episode schema")
        metadata = _metadata(json.loads(archive.attrs["metadata_json"]))
        report = json.loads(archive.attrs["report_json"])
        if not isinstance(report.get("passed"), bool) or bool(archive.attrs["episode_passed"]) != report["passed"]:
            raise ValueError("Inconsistent episode success report")
        if json.loads(archive.attrs["feature_names_json"]) != json.loads(_json(FEATURE_NAMES)):
            raise ValueError("Feature layout does not match schema")
        if archive.attrs.get("action_semantics") != "absolute_joint_position_target_rad" or archive.attrs.get("attempt_count") != 1:
            raise ValueError("Unknown action semantics or attempt count")
        storage_precision = archive.attrs.get("storage_precision", "legacy_raw_float32")
        if storage_precision not in ("raw_float64_policy_tensor_float32", "legacy_raw_float32"):
            raise ValueError("Unsupported raw storage precision")
        result = {key: archive[key][:] for key in _FLOAT_COLUMNS}
        for key in ("timestamp", "next_timestamp", "frame_index", "episode_index", "label_valid", "perturbation"):
            result[key] = archive[key][:]
        result["stage"] = archive["stage"].asstr()[:]
    count = len(result["timestamp"])
    for key in ("timestamp", "next_timestamp", "frame_index", "episode_index", "label_valid", "perturbation", "stage"):
        if result[key].shape != (count,):
            raise ValueError(f"Bad shape for {key}")
    if result["label_valid"].dtype != np.dtype(bool) or result["perturbation"].dtype != np.dtype(bool):
        raise ValueError("Label masks must be boolean")
    for key, width in _FLOAT_COLUMNS.items():
        values = result[key]
        if values.shape != (count, width):
            raise ValueError(f"Bad shape for {key}")
        if values.dtype not in (np.dtype("float32"), np.dtype("float64")):
            raise ValueError(f"Unsupported floating dtype for {key}")
        if storage_precision == "raw_float64_policy_tensor_float32" and values.dtype != np.dtype("float64"):
            raise ValueError(f"Raw float64 storage declaration differs from {key}")
        checked = values[result["label_valid"]] if key == "action" else values
        if not np.all(np.isfinite(checked)):
            raise ValueError(f"Nonfinite {key}")
    if np.any(result["label_valid"] & result["perturbation"]):
        raise ValueError("Perturbation falsely marked as expert label")
    if not np.array_equal(result["frame_index"], np.arange(count)) or np.any(result["episode_index"] != 0):
        raise ValueError("Corrupt episode/frame indices")
    if any(not np.all(np.isfinite(result[key])) for key in ("timestamp", "next_timestamp")):
        raise ValueError("Nonfinite timestamps")
    if not np.allclose(result["next_timestamp"] - result["timestamp"], metadata["control_period_s"], rtol=0, atol=_TIME_ATOL):
        raise ValueError("Invalid control period")
    if not np.allclose(result["timestamp"][1:], result["next_timestamp"][:-1], rtol=0, atol=_TIME_ATOL):
        raise ValueError("Noncontiguous timestamps")
    if any(not np.allclose(result[key][1:], result["next_" + key][:-1], atol=1e-7, rtol=0)
           for key in POLICY_OBSERVATION_KEYS):
        raise ValueError("Shifted state/next-state alignment")
    result.update(metadata=metadata, report=report, schema_version=SCHEMA_VERSION,
                  storage_precision=storage_precision, path=str(Path(path).resolve()),
                  eligible_for_training=bool(report["passed"] and np.any(result["label_valid"])))
    return result


def _paths(paths):
    result = [Path(path).resolve() for path in paths]
    if len(set(result)) != len(result):
        raise ValueError("Repeated archive paths would double-count attempts")
    return result


def training_rows(paths):
    """Both ACT and MLP consume these same state/environment/action arrays.

    Failed attempts remain in the source audit denominator, but contribute no
    labels. ``episode_index`` and original ``frame_index`` preserve boundaries
    and gaps: ACT chunks must never cross a perturbation, gap or episode end.
    """
    keys = (*POLICY_OBSERVATION_KEYS, "action", "episode_index", "frame_index")
    pieces = {key: [] for key in keys}
    for episode_index, path in enumerate(_paths(paths)):
        episode = load_episode(path)
        if not episode["eligible_for_training"]:
            continue
        mask = episode["label_valid"]
        for key in (*POLICY_OBSERVATION_KEYS, "action", "frame_index"):
            pieces[key].append(episode[key][mask])
        pieces["episode_index"].append(np.full(mask.sum(), episode_index, dtype=np.int64))
    return {key: np.concatenate(values) if values else np.empty((0, _FLOAT_COLUMNS[key]), dtype=np.float64)
            if key in _FLOAT_COLUMNS else np.empty(0, dtype=np.int64) for key, values in pieces.items()}


def audit_episodes(paths):
    episodes = [load_episode(path) for path in _paths(paths)]
    return {
        "schema_version": SCHEMA_VERSION,
        "attempt_count": len(episodes),
        "passed_attempt_count": sum(e["report"]["passed"] for e in episodes),
        "failed_attempt_count": sum(not e["report"]["passed"] for e in episodes),
        "training_episode_count": sum(e["eligible_for_training"] for e in episodes),
        "recorded_transition_count": sum(len(e["timestamp"]) for e in episodes),
        "training_transition_count": sum(int(e["label_valid"].sum()) for e in episodes if e["eligible_for_training"]),
        "invalid_label_count": sum(int((~e["label_valid"]).sum()) for e in episodes),
        "perturbation_transition_count": sum(int(e["perturbation"].sum()) for e in episodes),
    }


def split_episodes(paths, *, validation_fraction=.2, seed=0):
    """Split successful archives as indivisible groups, before normalization."""
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be between zero and one")
    eligible = [path for path in _paths(paths) if load_episode(path)["eligible_for_training"]]
    if len(eligible) < 2:
        raise ValueError("Need at least two successful episodes for a held-out split")
    order = np.random.default_rng(seed).permutation(len(eligible))
    count = max(1, min(len(eligible)-1, math.ceil(len(eligible) * validation_fraction)))
    validation = [eligible[index] for index in order[:count]]
    train = [eligible[index] for index in order[count:]]
    return {"train": train, "validation": validation}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit_episodes(args.archives), indent=2))


if __name__ == "__main__":
    main()
