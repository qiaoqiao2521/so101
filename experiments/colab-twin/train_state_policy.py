"""Bounded local ACT/MLP sanity training on the same audited HDF5 transitions.

Archives are split by episode before fitting normalization. Expert stage/time
and perturbation flags are never model inputs. This is a training diagnostic;
task success must be measured separately by the pure-policy simulator runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
import traceback
import uuid

import numpy as np
import torch

from learning_data import SCHEMA_VERSION, audit_episodes, load_episode, training_rows
from learning_models import (ACTION, ACTION_ENCODINGS, ACTION_ENCODING_SEMANTICS,
                             ENV_STATE, STATE, LEROBOT_REVISION, ModelSpec,
                             StateNormalizer, build_policy, load_policy_checkpoint)


def make_chunks(rows: dict, chunk_size: int, normalizer: StateNormalizer) -> dict:
    """Pad segment tails, never bridge failed labels, frame gaps or episodes."""
    count = len(rows[ACTION])
    if not count:
        raise ValueError("No eligible expert transitions")
    normalized = {key: normalizer.normalize(key, rows[key]) for key in (STATE, ENV_STATE)}
    actions = np.zeros((count, chunk_size, rows[ACTION].shape[1]), dtype=np.float32)
    padding = np.ones((count, chunk_size), dtype=bool)
    for start in range(count):
        end = start + 1
        while end < min(count, start + chunk_size):
            if (rows["episode_index"][end] != rows["episode_index"][start] or
                    rows["frame_index"][end] != rows["frame_index"][end - 1] + 1):
                break
            end += 1
        length = end - start
        # All future commands use the CURRENT chunk-start q as their anchor.
        # Future q is deliberately not consulted to construct model labels.
        actions[start, :length] = normalizer.normalize(
            ACTION, rows[ACTION][start:end], anchor=rows[STATE][start])
        padding[start, :length] = False
    return {STATE: torch.from_numpy(normalized[STATE]),
            ENV_STATE: torch.from_numpy(normalized[ENV_STATE]),
            ACTION: torch.from_numpy(actions), "action_is_pad": torch.from_numpy(padding),
            "action_anchor": torch.from_numpy(np.asarray(rows[STATE], dtype=np.float64))}


def evaluate_regression(policy, batch: dict, normalizer: StateNormalizer,
                        device: str, batch_size: int) -> dict:
    """Deterministic eval latent=0; report reconstruction rather than VAE total."""
    policy.eval()
    total = 0.0
    count = 0
    per_joint = np.zeros(6)
    chunk_per_joint = np.zeros(6)
    chunk_valid_count = 0
    chunk_max = 0.0
    first_errors = []
    with torch.no_grad():
        for start in range(0, len(batch[ACTION]), batch_size):
            part = {key: value[start:start + batch_size].to(device) for key, value in batch.items()}
            if hasattr(policy, "predict_action_chunk"):
                prediction = policy.predict_action_chunk({STATE: part[STATE], ENV_STATE: part[ENV_STATE]})
            else:
                prediction = policy.select_action({STATE: part[STATE], ENV_STATE: part[ENV_STATE]})[:, None, :]
                part[ACTION] = part[ACTION][:, :1]
                part["action_is_pad"] = part["action_is_pad"][:, :1]
            valid = ~part["action_is_pad"]
            error = (prediction - part[ACTION]).abs()
            total += float((error * valid[..., None]).sum())
            count += int(valid.sum()) * prediction.shape[-1]
            # First-action regression expresses the command used at a control tick.
            anchors = part["action_anchor"].cpu().numpy()
            absolute = normalizer.action_radians(prediction, anchor=anchors)
            target = normalizer.action_radians(part[ACTION], anchor=anchors)
            physical_error = np.abs(absolute - target)
            first_error = physical_error[:, 0]
            first_errors.append(first_error)
            per_joint += first_error.sum(axis=0)
            chunk_error = physical_error[valid.cpu().numpy()]
            chunk_per_joint += chunk_error.sum(axis=0)
            chunk_valid_count += len(chunk_error)
            chunk_max = max(chunk_max, float(chunk_error.max()))
    first_errors = np.concatenate(first_errors)
    startup = {}
    for requested in (1, 16, 50):
        selected = first_errors[:requested]
        startup[str(requested)] = {"frame_count": len(selected), "mae_rad": float(selected.mean()),
                                   "max_abs_error_rad": float(selected.max()),
                                   "mae_rad_per_joint": selected.mean(axis=0).tolist(),
                                   "max_abs_error_rad_per_joint": selected.max(axis=0).tolist()}
    return {"normalized_l1": total / max(1, count),
            "first_action_mae_rad_per_joint": (per_joint / len(batch[ACTION])).tolist(),
            "first_action_mae_rad": float(per_joint.sum() / (len(batch[ACTION]) * 6)),
            "first_action_max_abs_error_rad": float(first_errors.max()),
            "all_chunk_mae_rad_per_joint": (chunk_per_joint / chunk_valid_count).tolist(),
            "all_chunk_mae_rad": float(chunk_per_joint.sum() / (chunk_valid_count * 6)),
            "all_chunk_max_abs_error_rad": chunk_max,
            "startup_first_frames": startup,
            "startup_scope": "first 1/16/50 caller-selected rows, in chronological archive order",
            "physical_units": "absolute_joint_target_rad"}


def expert_delta_statistics(rows: dict) -> dict:
    delta = np.abs(rows[ACTION] - rows[STATE])
    return {"semantics": "abs(expert_absolute_target-current_q), joint order matches observation.state",
            "median_rad_per_joint": np.median(delta, axis=0).tolist(),
            "p95_rad_per_joint": np.quantile(delta, .95, axis=0).tolist(),
            "max_rad_per_joint": delta.max(axis=0).tolist(),
            "arm_joint_count": 5, "gripper_index": 5}


def critical_sampling_weights(rows: dict, critical_weight: float = 1.0) -> tuple[np.ndarray, dict]:
    """Identify difficult training frames without crossing validity boundaries.

    Only archive indices and absolute expert gripper commands define sampling;
    neither sampling labels nor phase/time metadata become model inputs.
    """
    if not np.isfinite(critical_weight) or critical_weight < 1:
        raise ValueError("Critical sample weight must be finite and at least one")
    count = len(rows[ACTION])
    episodes = np.asarray(rows["episode_index"])
    frames = np.asarray(rows["frame_index"])
    if not count or episodes.shape != (count,) or frames.shape != (count,):
        raise ValueError("Sampling requires nonempty aligned episode/frame indices")
    same_episode = episodes[1:] == episodes[:-1]
    if np.any(same_episode & (frames[1:] <= frames[:-1])):
        raise ValueError("Frames must increase within each episode")
    boundary = np.r_[True, ~same_episode | (frames[1:] != frames[:-1] + 1)]
    starts = np.flatnonzero(boundary)
    ends = np.r_[starts[1:], count]
    startup = frames < 50
    correction = np.zeros(count, dtype=bool)
    gripper = np.zeros(count, dtype=bool)
    correction_events = 0
    gripper_events = 0
    for start, end in zip(starts, ends):
        # A positive first frame means an invalid prefix was filtered out.
        # Later same-episode boundaries represent actual invalid-label gaps.
        if ((start == 0 or episodes[start] != episodes[start - 1]) and frames[start] > 0
                or start > 0 and episodes[start] == episodes[start - 1]):
            correction[start:min(end, start + 6)] = True
            correction_events += 1
        switches = start + 1 + np.flatnonzero(np.abs(np.diff(rows[ACTION][start:end, 5])) > .1)
        for switch in switches:
            gripper[max(start, switch - 8):min(end, switch + 9)] = True
        gripper_events += len(switches)
    critical = startup | correction | gripper
    weights = np.where(critical, critical_weight, 1.0)
    if not np.isfinite(weights.sum()):
        raise ValueError("Critical sample weight is too large for the dataset")
    values, counts = np.unique(weights, return_counts=True)
    audit = {
        "mode": "weighted_with_replacement" if critical_weight > 1 else "uniform_permutation",
        "critical_sample_weight": float(critical_weight), "rows_per_epoch_draw": count,
        "criteria": {"startup": "each episode original frame_index < 50",
                     "correction": "invalid prefix/gap first correction plus up to five subsequent contiguous valid frames",
                     "gripper_switch": "adjacent valid absolute gripper command change > .1 rad, up to eight frames either side"},
        "criterion_row_counts": {"startup": int(startup.sum()), "correction": int(correction.sum()),
                                  "gripper_switch": int(gripper.sum())},
        "event_counts": {"correction": correction_events, "gripper_switch": gripper_events},
        "critical_union_row_count": int(critical.sum()), "total_row_count": count,
        "overlap_rule": "union; multiply a row only once",
        "row_weight_counts": {str(float(value)): int(n) for value, n in zip(values, counts)},
        "expected_critical_probability_mass": float(weights[critical].sum() / weights.sum()),
        "actual_draw_count": 0, "actual_upweighted_draw_count": 0,
        "actual_draw_weight_counts": {str(float(value)): 0 for value in values},
    }
    return weights, audit


def load_initialization_checkpoint(path: Path, *, spec: ModelSpec, control_period_s: float,
                                   model_sha256: str, velocity_scale_floor: float,
                                   eligible_train_hashes, validation_hashes=(), robot_velocity_mask: bool = False,
                                   object_velocity_mask: bool = False):
    """Validate weight initialization and keep its training-only normalization.

    The caller constructs a fresh Adam afterwards. Optimizer state, training
    counters and sampler RNG are deliberately not resumed from this file.
    """
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    data = torch.load(path, map_location="cpu", weights_only=True)
    if data.get("format") != "so101-state-policy-v1" or data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Initialization checkpoint format/schema differs")
    saved_spec = ModelSpec(**data["model_spec"])
    encoding = data.get("action_encoding", saved_spec.action_encoding)
    if saved_spec.to_dict() != spec.to_dict() or encoding != spec.action_encoding:
        raise ValueError("Initialization model specification/action encoding differs")
    if data.get("model_sha256") != model_sha256 or data.get("control_period_s") != control_period_s:
        raise ValueError("Initialization physical model hash/control period differs")
    if spec.model == "act" and data.get("lerobot_revision") != LEROBOT_REVISION:
        raise ValueError("Initialization ACT source revision differs")
    floor = data.get("normalization_options", {}).get("velocity_scale_floor_rad_s", 0.0)
    if floor != velocity_scale_floor:
        raise ValueError("Initialization velocity scale floor differs")
    source_mask = data.get("normalization_options", {}).get("robot_velocity_mask", False)
    if not isinstance(source_mask, bool) or not isinstance(robot_velocity_mask, bool):
        raise ValueError("Initialization robot velocity masks must be explicit booleans")
    if source_mask and not robot_velocity_mask:
        raise ValueError("Initialization robot velocity mask cannot be silently removed")
    source_object_mask = data.get("normalization_options", {}).get("object_velocity_mask", False)
    if not isinstance(source_object_mask, bool) or not isinstance(object_velocity_mask, bool):
        raise ValueError("Initialization object velocity masks must be explicit booleans")
    if source_object_mask and not object_velocity_mask:
        raise ValueError("Initialization object velocity mask cannot be silently removed")
    original_hashes = data.get("train_dataset_sha256", [])
    if (not original_hashes or not set(original_hashes) <= set(eligible_train_hashes)
            or set(original_hashes) & set(validation_hashes)):
        raise ValueError("Initialization training hashes must be an eligible training subset, disjoint from validation")
    normalization_hashes = data.get("normalization_source", {}).get("training_dataset_sha256", original_hashes)
    if not normalization_hashes or not set(normalization_hashes) <= set(original_hashes):
        raise ValueError("Initialization normalization origin must belong to its training hashes")
    stats = data["normalization"]
    for key, width in ((STATE, spec.state_dim), (ENV_STATE, spec.environment_dim), (ACTION, spec.action_dim)):
        for name in ("mean", "std"):
            vector = np.asarray(stats[key][name], dtype=float)
            if vector.shape != (width,) or not np.isfinite(vector).all() or name == "std" and np.any(vector <= 0):
                raise ValueError(f"Invalid initialization normalization {key}.{name}")
    state_dict = data["state_dict"]
    if not state_dict or any(not isinstance(value, torch.Tensor) or not torch.isfinite(value).all()
                             for value in state_dict.values()):
        raise ValueError("Initialization parameters must be finite tensors")
    normalization = StateNormalizer(stats, spec.action_encoding, floor, robot_velocity_mask, object_velocity_mask)
    audit = {"status": "validated_weight_initialization", "checkpoint_sha256": digest,
             "original_training_dataset_sha256": list(original_hashes),
             "normalization_training_dataset_sha256": list(normalization_hashes),
             "normalization_source": "unchanged initialization checkpoint training statistics",
             "optimizer": "fresh Adam; optimizer state is not resumed",
             "training_state": "fresh counters, sampler RNG and requested seed",
             "observation_ablation": {"robot_velocity_mask_from": source_mask,
                                      "robot_velocity_mask_to": robot_velocity_mask,
                                      "explicit_new_mask": bool(robot_velocity_mask and not source_mask),
                                      "object_velocity_mask_from": source_object_mask,
                                      "object_velocity_mask_to": object_velocity_mask,
                                      "explicit_new_object_mask": bool(object_velocity_mask and not source_object_mask)}}
    return state_dict, normalization, audit


def train(args) -> dict:
    started = time.perf_counter()
    report = {"status": "failed", "model": args.model, "schema_version": SCHEMA_VERSION,
              "task_acceptance": "not_run", "max_steps": args.max_steps,
              "max_epochs": args.max_epochs, "max_wall_s": args.max_wall_s,
              "training_options": {"learning_rate": args.learning_rate, "batch_size": args.batch_size,
                                   "seed": args.seed}}
    policy = None
    try:
        if args.device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError("CUDA unavailable; choose --device cpu explicitly")
        torch.set_num_threads(2)
        torch.manual_seed(args.seed)
        rng = np.random.default_rng(args.seed)
        paths = [path.resolve() for path in args.dataset]
        validation_paths = [path.resolve() for path in args.validation_dataset]
        if set(paths) & set(validation_paths):
            raise ValueError("Train and validation episode paths overlap")
        digests = lambda entries: [hashlib.sha256(path.read_bytes()).hexdigest() for path in entries]
        train_hashes, validation_hashes = digests(paths), digests(validation_paths)
        if set(train_hashes) & set(validation_hashes):
            raise ValueError("Train and validation contain byte-identical archives")
        train_audit = audit_episodes(paths)
        report["train_audit"] = train_audit
        report["validation_audit"] = audit_episodes(validation_paths) if validation_paths else None
        rows = training_rows(paths)
        sample_weights, sample_audit = critical_sampling_weights(rows, args.critical_sample_weight)
        report["sampling"] = sample_audit
        sampled_rows = np.zeros(len(rows[ACTION]), dtype=bool)
        sampling_probabilities = sample_weights / sample_weights.sum()
        environment_dim = rows[ENV_STATE].shape[1]
        mask_robot_velocity = getattr(args, "mask_robot_velocity", False)
        mask_object_velocity = getattr(args, "mask_object_velocity", False)
        spec = ModelSpec(model=args.model, environment_dim=environment_dim,
                         chunk_size=args.chunk_size, use_vae=not args.no_vae,
                         dropout=args.dropout, action_encoding=args.action_encoding)
        episodes = [load_episode(path) for path in paths]
        metadata = [episode["metadata"] for episode in episodes if episode["eligible_for_training"]]
        eligible_hashes = [digest for digest, episode in zip(train_hashes, episodes)
                           if episode["eligible_for_training"] and episode["report"].get("passed") is True]
        periods = {meta["control_period_s"] for meta in metadata}
        model_hashes = {meta["model_sha256"] for meta in metadata}
        if len(periods) != 1 or len(model_hashes) != 1:
            raise ValueError("Mixed control periods or physical models require an explicit adapter")
        initialization_state = None
        if getattr(args, "init_checkpoint", None) is not None:
            initialization_state, normalization, initialization = load_initialization_checkpoint(
                args.init_checkpoint, spec=spec, control_period_s=next(iter(periods)),
                model_sha256=next(iter(model_hashes)), velocity_scale_floor=args.velocity_scale_floor,
                eligible_train_hashes=eligible_hashes, validation_hashes=validation_hashes,
                robot_velocity_mask=mask_robot_velocity, object_velocity_mask=mask_object_velocity)
            normalization_source = {"kind": "initialization_checkpoint_training_statistics",
                                    "checkpoint_sha256": initialization["checkpoint_sha256"],
                                    "training_dataset_sha256": initialization["normalization_training_dataset_sha256"]}
        else:
            normalization = StateNormalizer.fit(rows, action_encoding=args.action_encoding,
                                                 velocity_scale_floor=args.velocity_scale_floor,
                                                 robot_velocity_mask=mask_robot_velocity,
                                                 object_velocity_mask=mask_object_velocity)
            initialization = {"status": "not_requested", "optimizer": "fresh Adam"}
            normalization_source = {"kind": "fitted_current_eligible_training_rows",
                                    "training_dataset_sha256": eligible_hashes}
        report["initialization"] = initialization
        report["normalization_source"] = normalization_source
        data = make_chunks(rows, spec.chunk_size, normalization)
        validation_rows = training_rows(validation_paths) if validation_paths else None
        validation = make_chunks(validation_rows, spec.chunk_size, normalization) if validation_paths else None
        policy = build_policy(spec, args.device)
        if initialization_state is not None:
            policy.load_state_dict(initialization_state, strict=True)
        optimizer = torch.optim.Adam(policy.parameters(), lr=args.learning_rate)
        report["model_spec"] = spec.to_dict()
        report["action_encoding"] = spec.action_encoding
        report["action_encoding_semantics"] = ACTION_ENCODING_SEMANTICS[spec.action_encoding]
        report["normalization_options"] = {"velocity_scale_floor_rad_s": normalization.velocity_scale_floor,
                                           "robot_velocity_mask": normalization.robot_velocity_mask,
                                           "object_velocity_mask": normalization.object_velocity_mask}
        report["policy_observation_ablation"] = {"robot_velocity_mask": normalization.robot_velocity_mask,
                                                 "object_velocity_mask": normalization.object_velocity_mask,
                                                 "masked_environment_indices": (
                                                     (list(range(6)) if normalization.robot_velocity_mask else []) +
                                                     (list(range(13, 19)) if normalization.object_velocity_mask else [])),
                                                 "other_environment_channels": "unchanged",
                                                 "finite_validation": "before masking"}
        report["expert_delta_statistics"] = expert_delta_statistics(rows)
        report["parameters"] = sum(p.numel() for p in policy.parameters())
        report["before_training"] = evaluate_regression(policy, data, normalization, args.device, args.batch_size)
        if args.device.startswith("cuda"):
            torch.cuda.reset_peak_memory_stats()
        losses = []
        steps = 0
        training_started = time.perf_counter()
        stop = "epoch_limit"
        for epoch in range(args.max_epochs):
            indices = (rng.choice(len(rows[ACTION]), size=len(rows[ACTION]), replace=True,
                                  p=sampling_probabilities) if args.critical_sample_weight > 1
                       else rng.permutation(len(rows[ACTION])))
            for start in range(0, len(indices), args.batch_size):
                if steps >= args.max_steps:
                    stop = "step_limit"
                    break
                if time.perf_counter() - training_started >= args.max_wall_s:
                    stop = "wall_time_limit"
                    break
                selection = indices[start:start + args.batch_size]
                # The raw anchor is for decoding audit metrics; it is not an
                # extra input to the official policy or to its training loss.
                batch = {key: value[selection].to(args.device) for key, value in data.items()
                         if key != "action_anchor"}
                policy.train()
                optimizer.zero_grad(set_to_none=True)
                loss, metrics = policy(batch)
                if not torch.isfinite(loss):
                    raise RuntimeError("Nonfinite training loss")
                loss.backward()
                if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in policy.parameters()):
                    raise RuntimeError("Nonfinite training gradient")
                torch.nn.utils.clip_grad_norm_(policy.parameters(), 10.0)
                optimizer.step()
                sampled_rows[selection] = True
                sample_audit["actual_draw_count"] += len(selection)
                selected_weights = sample_weights[selection]
                sample_audit["actual_upweighted_draw_count"] += int((selected_weights > 1).sum())
                for value, n in zip(*np.unique(selected_weights, return_counts=True)):
                    sample_audit["actual_draw_weight_counts"][str(float(value))] += int(n)
                if args.device.startswith("cuda"):
                    torch.cuda.synchronize()
                steps += 1
                if steps == 1 or steps % 25 == 0:
                    losses.append({"step": steps, "epoch": epoch + 1,
                                   "total_loss": float(loss.detach()), **metrics})
            if stop != "epoch_limit":
                break
        report.update(steps=steps, epochs_started=epoch + 1, stop_reason=stop,
                      training_s=time.perf_counter() - training_started, loss_samples=losses)
        sample_audit["actual_unique_row_count"] = int(sampled_rows.sum())
        sample_audit["epoch_semantics"] = ("N draws with replacement; not every frame is visited each epoch"
                                           if args.critical_sample_weight > 1 else "one permutation of all N rows")
        report["after_training"] = evaluate_regression(policy, data, normalization, args.device, args.batch_size)
        if validation is not None:
            report["validation"] = evaluate_regression(policy, validation, normalization, args.device, args.batch_size)
        else:
            report["validation"] = {"status": "not_run", "reason": "single-episode sanity check has no held-out evidence"}
        policy.eval()
        policy.reset()
        reference_batch = {key: data[key][:min(args.batch_size, len(rows[ACTION]))].to(args.device)
                           for key in (STATE, ENV_STATE)}
        with torch.no_grad():
            expected = policy.select_action(reference_batch).detach().cpu()
        checkpoint = {
            "format": "so101-state-policy-v1", "schema_version": SCHEMA_VERSION,
            "model_spec": spec.to_dict(), "normalization": normalization.stats,
            "action_encoding": spec.action_encoding,
            "action_encoding_semantics": ACTION_ENCODING_SEMANTICS[spec.action_encoding],
            "normalization_options": {"velocity_scale_floor_rad_s": normalization.velocity_scale_floor,
                                      "robot_velocity_mask": normalization.robot_velocity_mask,
                                      "object_velocity_mask": normalization.object_velocity_mask},
            "initialization": initialization, "normalization_source": normalization_source,
            "training_options": report["training_options"],
            "sampling": sample_audit,
            "state_dict": {key: value.detach().cpu() for key, value in policy.state_dict().items()},
            "lerobot_revision": LEROBOT_REVISION if args.model == "act" else None,
            "control_period_s": next(iter(periods)), "model_sha256": next(iter(model_hashes)),
            "train_dataset_sha256": train_hashes, "validation_dataset_sha256": validation_hashes,
            "torch_version": str(torch.__version__),
        }
        checkpoint_path = args.output / "policy.pt"
        torch.save(checkpoint, checkpoint_path)
        restored, restored_normalization, _ = load_policy_checkpoint(str(checkpoint_path), "cpu")
        restored.reset()
        with torch.no_grad():
            actual = restored.select_action({key: value.cpu() for key, value in reference_batch.items()})
        reload_error = float((actual - expected).abs().max())
        if (restored_normalization.stats != normalization.stats or
                restored_normalization.action_encoding != normalization.action_encoding or
                restored_normalization.velocity_scale_floor != normalization.velocity_scale_floor or
                restored_normalization.robot_velocity_mask != normalization.robot_velocity_mask or
                restored_normalization.object_velocity_mask != normalization.object_velocity_mask or
                reload_error > 1e-4):
            raise RuntimeError(f"Checkpoint reload changed predictions/statistics: {reload_error}")
        report["checkpoint"] = {"filename": checkpoint_path.name,
                                "sha256": hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
                                "reload_max_abs_error_normalized": reload_error}
        reference_anchor = data["action_anchor"][:len(expected)].numpy()
        report["checkpoint"]["reload_max_abs_error_rad"] = float(np.abs(
            restored_normalization.action_radians(actual, anchor=reference_anchor) -
            normalization.action_radians(expected, anchor=reference_anchor)).max())
        if args.device.startswith("cuda"):
            report["gpu"] = {"peak_allocated_mib": torch.cuda.max_memory_allocated() / 2**20,
                             "peak_reserved_mib": torch.cuda.max_memory_reserved() / 2**20}
        report["status"] = "completed_diagnostic"
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        report["traceback"] = traceback.format_exc()
    report["total_s"] = time.perf_counter() - started
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, nargs="+", required=True)
    parser.add_argument("--validation-dataset", type=Path, nargs="*", default=[])
    parser.add_argument("--model", choices=("act", "mlp"), default="act")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--init-checkpoint", type=Path,
                        help="Initialize compatible weights and preserve its training normalization; create a fresh Adam")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--chunk-size", type=int, default=16)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--max-epochs", type=int, default=200)
    parser.add_argument("--max-wall-s", type=float, default=120)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--no-vae", action="store_true", help="explicit deterministic ACT diagnostic variant")
    parser.add_argument("--action-encoding", choices=ACTION_ENCODINGS, default="absolute",
                        help="Internal label encoding only; HDF5 and simulator commands remain absolute radians")
    parser.add_argument("--velocity-scale-floor", type=float, default=0.0,
                        help="Minimum training normalization scale for robot qvel, in rad/s; zero keeps the old scale")
    parser.add_argument("--critical-sample-weight", type=float, default=1.0,
                        help="Relative sampling weight for startup, gap-recovery and gripper-switch windows; one preserves uniform sampling")
    parser.add_argument("--mask-robot-velocity", action="store_true",
                        help="Observation ablation: zero normalized robot qvel six-vector consistently in training and inference")
    parser.add_argument("--mask-object-velocity", action="store_true",
                        help="Observation ablation: zero normalized object velocity indices 13:19 in training and inference")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    if (min(args.max_steps, args.max_epochs, args.batch_size, args.chunk_size, args.max_wall_s) <= 0
            or not np.isfinite(args.max_wall_s)):
        parser.error("training budgets and dimensions must be positive")
    if not np.isfinite(args.learning_rate) or args.learning_rate <= 0 or not np.isfinite(args.dropout) or not 0 <= args.dropout < 1:
        parser.error("learning rate must be finite and positive; dropout must be finite in [0,1)")
    if not np.isfinite(args.velocity_scale_floor) or args.velocity_scale_floor < 0:
        parser.error("velocity scale floor must be finite and nonnegative")
    if not np.isfinite(args.critical_sample_weight) or args.critical_sample_weight < 1:
        parser.error("critical sample weight must be finite and at least one")
    if args.output is None:
        args.output = Path(__file__).resolve().parent / "output" / f"state-training-{uuid.uuid4().hex}"
    args.output.mkdir(parents=True, exist_ok=False)
    report = train(args)
    temporary = args.output / "report.tmp"
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(args.output / "report.json")
    print(json.dumps({"output": str(args.output), "status": report["status"],
                      "steps": report.get("steps"), "error": report.get("error")}, ensure_ascii=False))
    return 0 if report["status"] == "completed_diagnostic" else 1


if __name__ == "__main__":
    raise SystemExit(main())
