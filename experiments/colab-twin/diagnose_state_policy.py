"""Bounded CPU audit of absolute policy actions and expert coverage.

Stage/time/label masks are audit columns, never policy inputs. Near-neighbor
label conflicts expose candidates; they do not prove observation sufficiency.
No simulation, training, GPU, expert solver, or fallback action is used here.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from pathlib import Path
import signal
import time
import uuid

import numpy as np
from scipy.spatial import cKDTree

from learning_data import (ENVIRONMENT_FEATURE_NAMES, POLICY_OBSERVATION_KEYS,
                           STATE_FEATURE_NAMES, load_episode)

STATE, ENV_STATE = POLICY_OBSERVATION_KEYS
ACTION = "action"
OFFICIAL_REVISION = "e0d50211ef236143ae867228662b7dfaba554f02"
OFFICIAL_ACT = ("https://github.com/huggingface/lerobot/blob/" + OFFICIAL_REVISION +
                "/src/lerobot/policies/act/modeling_act.py")


def action_error_summary(prediction, target):
    """Report physical errors, including tails hidden by a global mean."""
    prediction, target = np.asarray(prediction), np.asarray(target)
    if prediction.shape != target.shape or prediction.ndim != 2 or prediction.shape[1] != 6:
        raise ValueError("Actions must be matching N x 6 arrays")
    if not np.isfinite(prediction).all() or not np.isfinite(target).all():
        raise ValueError("Action errors require finite predictions and labels")
    if not len(target):
        return {"frames": 0, "status": "no_valid_labels"}
    error = np.abs(prediction - target)
    return {"frames": len(target), "mae_rad": float(error.mean()),
            "mae_rad_per_joint": error.mean(axis=0).tolist(),
            "max_abs_rad_per_joint": error.max(axis=0).tolist(),
            "p95_abs_rad": float(np.quantile(error, .95))}


def arm_tracking_summary(state, action):
    """The expert target/current offset defines a useful precision reference."""
    offset = np.asarray(action) - np.asarray(state)
    if offset.ndim != 2 or offset.shape[1] != 6 or not len(offset) or not np.isfinite(offset).all():
        raise ValueError("Tracking offsets require nonempty finite N x 6 arrays")
    return {"joint_names": list(STATE_FEATURE_NAMES), "std_rad": offset.std(axis=0).tolist(),
            "p50_abs_rad": np.quantile(np.abs(offset), .5, axis=0).tolist(),
            "p95_abs_rad": np.quantile(np.abs(offset), .95, axis=0).tolist(),
            "max_abs_rad": np.abs(offset).max(axis=0).tolist()}


def saved_action_consistency(fresh_prediction, saved, *, execute_chunk_steps=1,
                             gripper_projection=None, tolerance_rad=1e-5):
    """Compare model output before adapters; cached chunks have a different scope.

    Legacy archives expose only the final action, so externally perturbed ticks
    must be excluded. Projection changes belong to a separate execution audit.
    """
    prediction = np.asarray(fresh_prediction)
    count = len(prediction)
    if (prediction.ndim != 2 or prediction.shape[1] != 6 or not np.isfinite(prediction).all() or
            isinstance(execute_chunk_steps, bool) or not isinstance(execute_chunk_steps, int) or
            execute_chunk_steps < 1 or not np.isfinite(tolerance_rad) or tolerance_rad < 0):
        raise ValueError("Consistency audit needs finite N x 6 predictions and valid execution bounds")
    arrays = {}
    for key in (ACTION, 'raw_action', 'policy_action'):
        if key in saved:
            value = np.asarray(saved[key])
            if value.shape != prediction.shape or not np.isfinite(value).all():
                raise ValueError(f"Malformed saved action field: {key}")
            arrays[key] = value
    perturbation = np.asarray(saved.get('perturbation', np.zeros(count, dtype=bool)))
    projected = np.asarray(saved.get('projected', np.zeros(count, dtype=bool)))
    if (perturbation.shape != (count,) or projected.shape != (count,) or
            perturbation.dtype != np.dtype(bool) or projected.dtype != np.dtype(bool)):
        raise ValueError("Saved perturbation/projection masks must be N booleans")
    source = 'raw_action' if 'raw_action' in arrays else ACTION
    if source not in arrays:
        raise ValueError("Saved archive exposes neither raw_action nor legacy action")
    mask = np.ones(count, dtype=bool) if source == 'raw_action' else ~perturbation
    target = arrays[source]
    equivalence = execute_chunk_steps == 1
    if execute_chunk_steps > 1:
        scope = 'fresh_inference_vs_cached_chunk_not_equivalence_check'
    elif source == ACTION and gripper_projection is not None and gripper_projection is not False and not (
            isinstance(gripper_projection, dict) and gripper_projection.get('enabled') is False):
        scope = 'fresh_inference_vs_projected_action_not_model_output_equivalence_check'
        equivalence = False
    else:
        scope = 'fresh_inference_vs_raw_model_action' if source == 'raw_action' else 'fresh_inference_vs_legacy_unperturbed_action'
    errors = np.max(np.abs(prediction[mask] - target[mask]), axis=1)
    result = {'target_source': source, 'scope': scope, 'equivalence_check': equivalence,
              'execute_chunk_steps': execute_chunk_steps,
              'excluded_perturbed_ticks': int((~mask).sum()),
              'tolerance_rad': tolerance_rad, 'frames_exceeding_tolerance': int((errors > tolerance_rad).sum()),
              'physical_difference': action_error_summary(prediction[mask], target[mask]),
              'consistency_status': ('matches' if not np.any(errors > tolerance_rad) else 'differs')
                                    if equivalence else 'not_equivalence_check'}
    if not equivalence:
        result['interpretation'] = ('Fresh inference observes the current state; cached chunk actions were decoded at chunk start. '
                                    'Their difference is expected and is not an adapter inconsistency.') if execute_chunk_steps > 1 else (
                                    'Legacy action is already projected; its difference from raw inference is not a model-output change.')
    projection = {'status': 'not_available', 'reason': 'Raw/policy action stages absent in legacy archive'}
    if 'raw_action' in arrays and 'policy_action' in arrays:
        changed = np.any(arrays['raw_action'] != arrays['policy_action'], axis=1)
        projection = {'status': 'audited_execution_adapter',
                      'raw_to_policy_changed_frame_count': int(changed.sum()),
                      'raw_to_policy_difference': action_error_summary(arrays['raw_action'], arrays['policy_action']),
                      'scope': 'execution_projection_difference_not_model_prediction_change'}
        if 'projected' in saved:
            projection.update(logged_projected_frame_count=int(projected.sum()),
                              projection_flag_disagreement_frame_count=int((changed != projected).sum()),
                              flag_disagreement_note='Tiny float64 projection changes may serialize to identical float32 values')
    result['projection_audit'] = projection
    if 'policy_action' in arrays and ACTION in arrays:
        result['executed_vs_policy_unperturbed_difference'] = action_error_summary(
            arrays[ACTION][~perturbation], arrays['policy_action'][~perturbation])
    return result


def contradictory_neighbors(observations, actions, frames, stages, *, radius=.001,
                            action_threshold_rad=.05, max_pairs=20, neighbors=8):
    """Find nearby valid labels with different targets using a bounded k-NN query.

    Searching only the nearest k neighbors can miss conflicts in dense regions;
    returned candidates are diagnostic evidence, not a complete conflict count.
    """
    observations, actions = np.asarray(observations), np.asarray(actions)
    count = len(observations)
    if observations.ndim != 2 or actions.shape != (count, 6):
        raise ValueError("Alias observations/actions have incompatible shapes")
    if len(frames) != count or len(stages) != count:
        raise ValueError("Alias audit indices have incompatible shapes")
    if not np.isfinite(observations).all() or not np.isfinite(actions).all():
        raise ValueError("Alias search requires finite data")
    if min(radius, action_threshold_rad) <= 0 or min(max_pairs, neighbors) < 1:
        raise ValueError("Alias thresholds/budgets must be positive")
    candidates = []
    if count > 1:
        distances, indices = cKDTree(observations).query(observations, k=min(count, neighbors + 1))
        seen = set()
        for i in range(count):
            for distance, j in zip(distances[i], indices[i]):
                j = int(j)
                pair = (min(i, j), max(i, j))
                if i == j or pair in seen or distance > radius:
                    continue
                seen.add(pair)
                difference = np.abs(actions[i] - actions[j])
                if difference.max() >= action_threshold_rad:
                    candidates.append({"frame_a": int(frames[i]), "frame_b": int(frames[j]),
                                       "stage_a": str(stages[i]), "stage_b": str(stages[j]),
                                       "normalized_observation_l2": float(distance),
                                       "max_action_difference_rad": float(difference.max()),
                                       "action_difference_rad_per_joint": difference.tolist()})
    candidates.sort(key=lambda item: item["normalized_observation_l2"])
    return {"scope": "nearest_neighbors_only_not_observation_sufficiency_proof",
            "radius_normalized_l2": radius, "action_threshold_rad": action_threshold_rad,
            "nearest_neighbors_searched": neighbors, "candidate_pairs_found": len(candidates),
            "returned_pairs": candidates[:max_pairs]}


def coverage_summary(training_normalized, online_normalized, training_raw, online_raw,
                     *, feature_names, max_detail=20):
    """Nearest training distance and raw ranges are distinct coverage indicators."""
    training_normalized, online_normalized = map(np.asarray, (training_normalized, online_normalized))
    training_raw, online_raw = map(np.asarray, (training_raw, online_raw))
    width = training_normalized.shape[1] if training_normalized.ndim == 2 else -1
    if (width < 1 or not len(training_normalized) or training_raw.shape != training_normalized.shape or
            online_raw.shape != online_normalized.shape or online_normalized.ndim != 2 or
            online_normalized.shape[1] != width or len(feature_names) != width):
        raise ValueError("Coverage matrices must be compatible and training nonempty")
    if any(not np.isfinite(value).all() for value in
           (training_normalized, online_normalized, training_raw, online_raw)):
        raise ValueError("Coverage matrices must be finite")
    minimum, maximum = training_raw.min(axis=0), training_raw.max(axis=0)
    if not len(online_raw):
        return {"frames": 0, "outside_training_range_frame_count": 0, "detail": []}
    distance, nearest = cKDTree(training_normalized).query(online_normalized)
    # Ignore float32 serialization noise around a constant feature.
    tolerance = 1e-7 + 1e-6 * np.maximum(np.abs(minimum), np.abs(maximum))
    outside = (online_raw < minimum - tolerance) | (online_raw > maximum + tolerance)
    detail = []
    for i in range(min(len(online_raw), max_detail)):
        difference = online_normalized[i] - training_normalized[nearest[i]]
        largest = np.argsort(np.abs(difference))[-5:][::-1]
        detail.append({"tick": i, "nearest_training_row": int(nearest[i]),
                       "normalized_nearest_l2": float(distance[i]),
                       "outside_training_range_features": [feature_names[j] for j in np.where(outside[i])[0]],
                       "largest_normalized_deviations": [
                           {"feature": feature_names[j], "difference": float(difference[j]),
                            "online_raw": float(online_raw[i, j]),
                            "nearest_training_raw": float(training_raw[nearest[i], j])} for j in largest]})
    return {"frames": len(online_raw), "outside_training_range_frame_count": int(outside.any(axis=1).sum()),
            "max_nearest_normalized_l2": float(distance.max()),
            "training_min_raw": minimum.tolist(), "training_max_raw": maximum.tolist(), "detail": detail}


def _matrix(rows, normalizer, *, normalized):
    return np.concatenate([normalizer.normalize(key, rows[key]) if normalized else rows[key]
                           for key in POLICY_OBSERVATION_KEYS], axis=1)


def _predict_absolute(runner, rows, check_budget, batch_size=64):
    """Reuse the checkpoint adapter's decoding, including residual anchors."""
    import torch
    predictions = []
    supports_anchor = "anchor" in inspect.signature(runner.normalizer.action_radians).parameters
    if runner.metadata["model_spec"].get("action_encoding", "absolute") != "absolute" and not supports_anchor:
        raise ValueError("Residual checkpoint needs an anchor-aware action adapter")
    with torch.no_grad():
        for start in range(0, len(rows[STATE]), batch_size):
            check_budget()
            raw_state = rows[STATE][start:start + batch_size]
            batch = {key: torch.from_numpy(runner.normalizer.normalize(key, rows[key][start:start + batch_size]))
                     for key in POLICY_OBSERVATION_KEYS}
            if hasattr(runner.policy, "predict_action_chunk"):
                predicted = runner.policy.predict_action_chunk(batch)[:, 0]
            else:
                predicted = runner.policy.select_action(batch)
            kwargs = {"anchor": raw_state} if supports_anchor else {}
            predictions.append(runner.normalizer.action_radians(predicted, **kwargs))
    return np.concatenate(predictions) if predictions else np.empty((0, 6))


def _source_references(checkpoint):
    directory = Path(__file__).resolve().parent
    files = ("diagnose_state_policy.py", "learning_models.py", "learning_data.py",
             "train_state_policy.py", "grasp_episode.py", "evaluate_state_policy.py")
    return {"checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            "local_source_sha256": {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                                    for name in files},
            "official_sources": [{"url": OFFICIAL_ACT + "#L103-L138", "supports": "action queue and first-action inference"},
                                 {"url": OFFICIAL_ACT + "#L140-L167", "supports": "padded L1 and optional KL objective"},
                                 {"url": OFFICIAL_ACT + "#L408-L467", "supports": "training latent and inference zero latent"}],
            "source_verification": "ACT adapter checks installed official source hashes before loading"}


def _online_paths(evaluation):
    if evaluation.is_file():
        if evaluation.suffix != ".npz":
            raise ValueError("Evaluation file must be policy-transitions.npz")
        return [evaluation]
    direct = evaluation / "policy-transitions.npz"
    paths = [direct] if direct.exists() else sorted(evaluation.glob("attempt-*/policy-transitions.npz"))
    if not paths:
        raise ValueError("No saved evaluation transition archives found")
    return paths


def _execution_adapter(path):
    """Attempt metadata takes precedence; old logs default to one fresh action."""
    config = {}
    sources = []
    for report_path in (path.parent.parent / 'report.json', path.parent / 'report.json'):
        if report_path.is_file():
            report = json.loads(report_path.read_text())
            current = report.get('execution_adapter', report.get('adapter_config'))
            if current is not None:
                config.update(current)
                sources.append({'path': str(report_path.resolve()),
                                'sha256': hashlib.sha256(report_path.read_bytes()).hexdigest()})
    if sources:
        steps = config.get('execute_chunk_steps', 1)
        if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
            raise ValueError('Saved execution adapter chunk steps must be a positive integer')
        if config.get('gripper_projection_enabled') is False:
            config['gripper_projection'] = None
        elif config.get('gripper_projection_enabled') and not config.get('gripper_projection'):
            config['gripper_projection'] = {'enabled': True, 'scope': 'attempt_reports_enabled_without_details'}
        return {**config, 'execute_chunk_steps': steps, 'source_report': sources[-1]['path'],
                'source_report_sha256': sources[-1]['sha256'], 'source_reports': sources}
    return {'execute_chunk_steps': 1, 'gripper_projection': None, 'source_report': None,
            'scope': 'legacy_log_default_one_fresh_action'}


def diagnose(args):
    started = time.perf_counter()
    report = {"status": "failed", "device": "cpu", "max_wall_s": args.max_wall_s,
              "policy_inputs": list(POLICY_OBSERVATION_KEYS), "expert_intervention": False,
              "scope": "offline_regression_and_saved_online_coverage_not_task_acceptance"}

    def check_budget():
        if time.perf_counter() - started >= args.max_wall_s:
            raise TimeoutError("CPU diagnostic wall-time budget exhausted")

    try:
        from learning_models import load_policy
        import torch
        torch.set_num_threads(2)
        report["sources"] = _source_references(args.checkpoint)
        episode = load_episode(args.dataset)
        indices = np.flatnonzero(episode["label_valid"])
        if not len(indices):
            raise ValueError("Reference archive has no valid expert labels")
        rows = {key: episode[key][indices] for key in (*POLICY_OBSERVATION_KEYS, ACTION)}
        runner = load_policy(str(args.checkpoint), "cpu")
        if (runner.metadata.get("control_period_s") != episode["metadata"]["control_period_s"] or
                runner.metadata.get("model_sha256") != episode["metadata"]["model_sha256"]):
            raise ValueError("Checkpoint and reference physics model/control period differ")
        report.update(model_spec=runner.metadata["model_spec"],
                      normalization_options=runner.metadata.get("normalization_options", {}),
                      dataset_sha256=hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
                      reference_episode_passed=episode["report"]["passed"],
                      recorded_frames=len(episode[ACTION]), valid_label_frames=len(indices),
                      invalid_label_frames=int((~episode["label_valid"]).sum()))
        prediction = _predict_absolute(runner, rows, check_budget)
        report["all_valid_labels"] = action_error_summary(prediction, rows[ACTION])
        report["startup"] = {str(count): {**action_error_summary(prediction[:count], rows[ACTION][:count]),
                                        "first_recorded_frame": int(indices[0]),
                                        "scope": "first_n_valid_labels_not_invalid_perturbation_ticks"}
                             for count in (1, 16, 50)}
        stages = episode["stage"][indices]
        report["per_stage"] = {str(stage): action_error_summary(prediction[stages == stage], rows[ACTION][stages == stage])
                               for stage in dict.fromkeys(stages)}
        report["expert_action_minus_state"] = arm_tracking_summary(rows[STATE], rows[ACTION])
        report["startup_detail"] = [{"frame": int(indices[i]), "stage": str(stages[i]),
                                    "state_rad": rows[STATE][i].tolist(),
                                    "qvel_rad_s": rows[ENV_STATE][i, :6].tolist(),
                                    "expert_absolute_action_rad": rows[ACTION][i].tolist(),
                                    "predicted_absolute_action_rad": prediction[i].tolist(),
                                    "error_rad": (prediction[i] - rows[ACTION][i]).tolist()}
                                   for i in range(min(50, len(indices)))]
        stats = runner.normalizer.stats[ENV_STATE]
        report["qvel_normalization"] = {"feature_names": list(ENVIRONMENT_FEATURE_NAMES[:6]),
                                        "mean_rad_s": stats["mean"][:6], "scale_rad_s": stats["std"][:6],
                                        "policy_inputs_masked": report["normalization_options"].get("robot_velocity_mask", False),
                                        "scope": "raw qvel audit retained; normalized policy inputs follow checkpoint mask"}
        report["object_velocity_normalization"] = {
            "feature_names": list(ENVIRONMENT_FEATURE_NAMES[13:19]),
            "mean": stats["mean"][13:19], "scale": stats["std"][13:19],
            "policy_inputs_masked": report["normalization_options"].get("object_velocity_mask", False),
            "scope": "raw physical velocities retained; normalized policy inputs follow checkpoint mask"}
        normalized = _matrix(rows, runner.normalizer, normalized=True)
        raw = _matrix(rows, runner.normalizer, normalized=False)
        report["near_duplicate_label_conflicts"] = contradictory_neighbors(
            normalized, rows[ACTION], indices, stages)
        report["online"] = []
        feature_names = list(STATE_FEATURE_NAMES) + list(ENVIRONMENT_FEATURE_NAMES)
        for path in _online_paths(args.evaluation) if args.evaluation else []:
            check_budget()
            with np.load(path, allow_pickle=False) as archive:
                online = {key: archive[key][:20] for key in (*POLICY_OBSERVATION_KEYS, ACTION)}
                timestamps = archive["timestamp"][:20]
                saved = {key: archive[key][:20] for key in
                         (ACTION, 'raw_action', 'policy_action', 'perturbation', 'projected') if key in archive}
                perturbation = saved.get('perturbation', np.zeros(len(timestamps), dtype=bool))
            adapter = _execution_adapter(path)
            predicted = _predict_absolute(runner, online, check_budget)
            coverage = coverage_summary(normalized, _matrix(online, runner.normalizer, normalized=True),
                                        raw, _matrix(online, runner.normalizer, normalized=False),
                                        feature_names=feature_names)
            for item in coverage["detail"]:
                row = item["nearest_training_row"]
                tick = item["tick"]
                item.update(nearest_recorded_frame=int(indices[row]), nearest_stage=str(stages[row]),
                            qvel_rad_s=online[ENV_STATE][tick, :6].tolist(),
                            tip_forces_n=online[ENV_STATE][tick, -2:].tolist(),
                            timestamp_s=float(timestamps[tick]), perturbation=bool(perturbation[tick]))
            report["online"].append({"archive": str(path.resolve()), "archive_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                     "scope": "first_20_completed_control_cycles",
                                     "execution_adapter": adapter,
                                     "coverage": coverage,
                                     "prediction_consistency": saved_action_consistency(
                                         predicted, saved, execute_chunk_steps=adapter['execute_chunk_steps'],
                                         gripper_projection=adapter.get('gripper_projection'))})
        check_budget()
        report["status"] = "completed_diagnostic"
        np.savez_compressed(args.output / "offline-predictions.npz", absolute_action=prediction,
                            recorded_frame=indices, expert_absolute_action=rows[ACTION])
    except Exception as error:
        report["status"] = "stopped_budget" if isinstance(error, TimeoutError) else "failed"
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    report["elapsed_s"] = time.perf_counter() - started
    temporary = args.output / "report.json.partial"
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(args.output / "report.json")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-wall-s", type=float, default=120)
    args = parser.parse_args()
    if not np.isfinite(args.max_wall_s) or not 0 < args.max_wall_s <= 120:
        parser.error("CPU wall-time budget must be positive and at most 120 seconds")
    if args.output is None:
        args.output = Path(__file__).resolve().parent / "output" / f"prediction-audit-{uuid.uuid4().hex}"
    args.output.mkdir(parents=True, exist_ok=False)

    def timeout(signum, frame):
        raise TimeoutError("CPU diagnostic wall-time budget exhausted")

    previous = signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, args.max_wall_s)
    try:
        report = diagnose(args)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
    print(json.dumps({"output": str(args.output), "status": report["status"], "error": report.get("error")}, ensure_ascii=False))
    return 0 if report["status"] == "completed_diagnostic" else 1


if __name__ == "__main__":
    raise SystemExit(main())
