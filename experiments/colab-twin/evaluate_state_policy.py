"""Bounded pure-policy MuJoCo evaluation; no IK, planner, stage input or fallback.

Default: one nominal sanity attempt. Batch repeatability and recovery trials
must be requested explicitly. Physical task acceptance comes from the separate
StateWorkcell monitor; regression loss cannot count as a successful grasp/place.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import time
import uuid

import numpy as np

from learning_data import POLICY_OBSERVATION_KEYS, SCHEMA_VERSION, load_episode


@dataclass(frozen=True)
class EvaluationLimits:
    max_simulation_s: float = 90.0
    max_wall_s: float = 30.0
    perturb_at_s: float = 3.0
    perturb_duration_s: float = .2
    perturb_rad: float = .02

    def validate(self, control_period_s):
        values = (self.max_simulation_s, self.max_wall_s, self.perturb_duration_s, self.perturb_rad)
        if any(not math.isfinite(value) or value <= 0 for value in values):
            raise ValueError("Evaluation bounds must be finite and positive")
        if not math.isfinite(self.perturb_at_s) or self.perturb_at_s < 0:
            raise ValueError("perturb_at_s must be finite and nonnegative")
        ticks = self.perturb_duration_s / control_period_s
        if ticks < 1 or not math.isclose(ticks, round(ticks), abs_tol=1e-8):
            raise ValueError("Perturbation duration must span integer control cycles")
        if self.perturb_rad > math.radians(5):
            raise ValueError("This evaluation fixture caps perturbations at five degrees")


def _json_dump(path, value):
    def scalar(item):
        if isinstance(item, np.ndarray):
            return item.tolist()
        if isinstance(item, np.generic):
            return item.item()
        raise TypeError(type(item).__name__)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False, default=scalar) + "\n", encoding="utf-8")
    temporary.replace(path)


def policy_observation(obs):
    """Project audit-rich observations onto the only two allowed policy features."""
    result = {}
    for key, size in zip(POLICY_OBSERVATION_KEYS, (6, 30)):
        values = np.asarray(obs[key], dtype=np.float64)
        if values.shape != (size,) or not np.isfinite(values).all():
            raise ValueError(f"Invalid policy observation {key}")
        result[key] = values.copy()
    return result


def can_inject_perturbation(diagnostic, baseline_z):
    """Inject only before object lift and without either finger contacting it."""
    return bool(diagnostic is not None and diagnostic.get("finite_state", False)
                and diagnostic.get("arm_valid", False)
                and not diagnostic.get("obstacle_contact", True)
                and len(diagnostic.get("tip_forces_n", [])) == 2
                and np.isfinite(diagnostic["tip_forces_n"]).all()
                and max(diagnostic["tip_forces_n"]) <= .02
                and diagnostic["object_z_m"] - baseline_z <= .005)


def fit_gripper_projection(paths, metadata, mode="clip"):
    """Freeze support bounds from exactly this checkpoint's positive archives."""
    paths = [Path(path).resolve() for path in paths]
    hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
    expected = metadata.get("train_dataset_sha256", [])
    if not hashes or len(set(hashes)) != len(hashes) or set(hashes) != set(expected):
        raise ValueError("Gripper bound archives must exactly match checkpoint training hashes")
    labels = []
    for path in paths:
        episode = load_episode(path)
        if not episode["eligible_for_training"] or episode["report"].get("passed") is not True:
            raise ValueError("Gripper bounds require positive eligible training episodes")
        valid = episode["action"][episode["label_valid"], 5]
        if not len(valid) or not np.isfinite(valid).all():
            raise ValueError("Gripper bounds require finite valid expert labels")
        labels.append(valid)
    labels = np.concatenate(labels)
    if mode not in ("clip", "nearest"):
        raise ValueError("Unknown gripper projection mode")
    unique = np.unique(labels)
    if mode == "nearest" and len(unique) != 2:
        raise ValueError("Nearest gripper projection requires exactly two unique valid training labels")
    config = {"enabled": True, "mode": mode, "training_dataset_sha256": hashes,
            "minimum_rad": float(labels.min()), "maximum_rad": float(labels.max()),
            "valid_label_frame_count": len(labels),
            "scope": "fixed training-label support projection of gripper only"}
    if mode == "nearest":
        config.update(allowed_labels_rad=unique.tolist(), midpoint_rad=float(unique.mean()),
                      tie_rule="lower_label_at_exact_midpoint")
    return config


def project_gripper(action, config):
    """Validate before clipping; an infinity must not turn into a finite command."""
    raw = np.asarray(action, dtype=np.float64)
    if raw.shape != (6,) or not np.isfinite(raw).all():
        raise ValueError("Projection requires a finite six-coordinate policy action")
    projected = raw.copy()
    if config is not None:
        lo, hi = float(config["minimum_rad"]), float(config["maximum_rad"])
        if not np.isfinite([lo, hi]).all() or lo > hi:
            raise ValueError("Invalid gripper support bounds")
        mode = config.get("mode", "clip")
        if mode == "clip":
            projected[5] = np.clip(projected[5], lo, hi)
        elif mode == "nearest":
            labels = np.asarray(config["allowed_labels_rad"], dtype=float)
            if labels.shape != (2,) or not np.isfinite(labels).all() or labels[0] >= labels[1]:
                raise ValueError("Nearest projection requires two ordered finite training labels")
            projected[5] = labels[0] if projected[5] <= labels.mean() else labels[1]
        else:
            raise ValueError("Unknown gripper projection mode")
    return projected, bool(projected[5] != raw[5])


def run_attempt(env, policy, monitor, *, seed, perturbed, limits,
                gripper_projection=None, clock=time.perf_counter):
    """Return an honest terminal report plus all completed policy transitions.

    The supplied interfaces deliberately have no expert/planner argument. A
    safety checker verifies perturbed commands only, and never supplies actions.
    """
    period = float(policy.metadata["control_period_s"])
    limits.validate(period)
    started = clock()
    transitions = []
    injected_ticks = 0
    perturb_start_s = None
    perturbation_offset = np.r_[np.random.default_rng(seed).uniform(-limits.perturb_rad, limits.perturb_rad, 5), 0.0]
    required_ticks = int(round(limits.perturb_duration_s / period))
    result = {"seed": seed, "perturbed": bool(perturbed), "passed": False,
              "safety_stop": False, "failure_reason": None, "perturbation_injected": False,
              "perturbation_control_ticks": 0, "perturbation_offset_rad": perturbation_offset.tolist() if perturbed else None}
    action_audit = {"finite_policy_command_count": 0, "gripper_projection_count": 0,
                    "gripper_projection_rate": None, "raw_action_min_rad_per_joint": None,
                    "raw_action_max_rad_per_joint": None}
    result["action_audit"] = action_audit
    result["execution_adapter"] = {"execute_chunk_steps": getattr(policy, "execute_chunk_steps", 1),
                                   "gripper_projection_enabled": gripper_projection is not None}
    first_time = None
    diagnostic = None
    try:
        policy.reset()
        obs = env.reset()
        first_time = float(obs["time_s"])
        while True:
            elapsed = float(obs["time_s"]) - first_time
            if clock() - started >= limits.max_wall_s:
                result["failure_reason"] = "wall_time_limit"
                break
            if elapsed + period > limits.max_simulation_s + 1e-8:
                result["failure_reason"] = "simulation_time_limit"
                break
            before = policy_observation(obs)
            raw_action = np.asarray(policy.predict(before), dtype=np.float64)
            if raw_action.shape != (6,) or not np.isfinite(raw_action).all():
                result.update(failure_reason="invalid_policy_action", safety_stop=True)
                result["invalid_action"] = {"shape": list(raw_action.shape), "finite": bool(np.isfinite(raw_action).all())}
                break
            policy_action, projected = project_gripper(raw_action, gripper_projection)
            action = policy_action.copy()
            action_audit["finite_policy_command_count"] += 1
            action_audit["gripper_projection_count"] += int(projected)
            previous_min = action_audit["raw_action_min_rad_per_joint"]
            previous_max = action_audit["raw_action_max_rad_per_joint"]
            action_audit["raw_action_min_rad_per_joint"] = (raw_action if previous_min is None
                                                          else np.minimum(previous_min, raw_action)).tolist()
            action_audit["raw_action_max_rad_per_joint"] = (raw_action if previous_max is None
                                                          else np.maximum(previous_max, raw_action)).tolist()
            result["last_command"] = {"time_s": float(obs["time_s"]), "raw_action": raw_action.tolist(),
                                      "policy_action": policy_action.tolist(), "action": action.tolist(),
                                      "projected": projected, "perturbation": False}
            injecting = False
            if (perturbed and perturb_start_s is None and elapsed >= limits.perturb_at_s
                    and can_inject_perturbation(diagnostic, env.baseline_z)):
                perturb_start_s = elapsed
            if perturb_start_s is not None and injected_ticks < required_ticks:
                action = action + perturbation_offset
                result["last_command"].update(action=action.tolist(), perturbation=True)
                # This query is a stop decision, not a replacement action or a
                # planned path. StateWorkcell also monitors actual physics.
                check = env.checker.evaluate(action, require_fixed_gripper=False)
                if not check["valid"]:
                    result.update(failure_reason="perturbation_safety_precheck", safety_stop=True)
                    break
                injecting = True
            next_obs, diagnostic = env.step(action)
            next_time = float(next_obs["time_s"])
            if not math.isclose(next_time - float(obs["time_s"]), period, rel_tol=0, abs_tol=1e-8):
                raise RuntimeError("Simulator and policy control periods differ")
            if injecting:
                injected_ticks += 1
            transitions.append({"timestamp": float(obs["time_s"]),
                                "next_timestamp": next_time,
                                **before, "action": action.copy(),
                                "raw_action": raw_action.copy(), "policy_action": policy_action.copy(),
                                "projected": projected,
                                "perturbation": injecting, "diagnostic": diagnostic.copy()})
            observed = monitor.update(diagnostic)
            obs = next_obs
            if observed.get("failure_reason") or observed.get("safety_stop"):
                result.update(failure_reason=observed.get("failure_reason") or "physical_safety_stop",
                              safety_stop=bool(observed.get("safety_stop")))
                break
            if observed.get("passed"):
                if perturbed and injected_ticks != required_ticks:
                    result["failure_reason"] = "perturbation_not_fully_injected"
                else:
                    result["passed"] = True
                break
    except Exception as error:
        result["failure_reason"] = "safety_stop" if type(error).__name__ == "SafetyStop" else "execution_exception"
        result["safety_stop"] = type(error).__name__ == "SafetyStop"
        result["error"] = {"type": type(error).__name__, "message": str(error)}
        if hasattr(error, "details"):
            result["failure_details"] = error.details
    physical = monitor.report()
    # Never allow a physical monitor snapshot to override a timeout or stop.
    result["physical_acceptance"] = physical
    result["passed"] = bool(result["passed"] and physical.get("passed")
                            and not result["safety_stop"] and result["failure_reason"] is None)
    result["perturbation_injected"] = injected_ticks > 0
    result["perturbation_fully_injected"] = injected_ticks == required_ticks
    result["perturbation_control_ticks"] = injected_ticks
    result["perturbation_start_s"] = perturb_start_s
    result["completed_control_cycles"] = len(transitions)
    commands = action_audit["finite_policy_command_count"]
    action_audit["gripper_projection_rate"] = action_audit["gripper_projection_count"] / commands if commands else None
    result["simulated_s"] = transitions[-1]["next_timestamp"] - first_time if transitions else 0.0
    result["wall_s"] = clock() - started
    if perturbed and not result["perturbation_injected"] and result["failure_reason"] is None:
        result["failure_reason"] = "perturbation_not_injected"
        result["passed"] = False
    return result, transitions


def summarize_attempts(attempts):
    """Report every attempt; failed trials never vanish from either denominator."""
    summary = {"attempt_count": len(attempts), "passed_attempt_count": sum(bool(a["passed"]) for a in attempts),
               "safety_stop_count": sum(bool(a.get("safety_stop")) for a in attempts),
               "timeout_count": sum(a.get("failure_reason") in ("wall_time_limit", "simulation_time_limit") for a in attempts)}
    summary["failed_attempt_count"] = summary["attempt_count"] - summary["passed_attempt_count"]
    summary["safety_stop_rate"] = summary["safety_stop_count"] / len(attempts) if attempts else None
    audits = [attempt.get("action_audit", {}) for attempt in attempts]
    commands = sum(audit.get("finite_policy_command_count", 0) for audit in audits)
    projections = sum(audit.get("gripper_projection_count", 0) for audit in audits)
    minimum = [audit["raw_action_min_rad_per_joint"] for audit in audits
               if audit.get("raw_action_min_rad_per_joint") is not None]
    maximum = [audit["raw_action_max_rad_per_joint"] for audit in audits
               if audit.get("raw_action_max_rad_per_joint") is not None]
    summary["action_audit"] = {"finite_policy_command_count": commands,
                               "gripper_projection_count": projections,
                               "gripper_projection_rate": projections / commands if commands else None,
                               "raw_action_min_rad_per_joint": np.min(minimum, axis=0).tolist() if minimum else None,
                               "raw_action_max_rad_per_joint": np.max(maximum, axis=0).tolist() if maximum else None}
    for name, perturbed in (("nominal", False), ("perturbed", True)):
        group = [a for a in attempts if a["perturbed"] == perturbed]
        passed = sum(bool(a["passed"]) for a in group)
        summary[name] = {"attempt_count": len(group), "passed_attempt_count": passed,
                         "success_rate": passed / len(group) if group else None}
        if perturbed:
            summary[name]["fully_injected_attempt_count"] = sum(bool(a.get("perturbation_fully_injected")) for a in group)
    return summary


def evaluate(args):
    # Lazy imports keep audit tests independent of Torch and the simulator.
    from learning_env import PhysicalTaskMonitor, StateWorkcell
    from learning_models import load_policy
    report = {"schema_version": SCHEMA_VERSION, "status": "setup_failed", "attempts": [],
              "expert_intervention": False, "policy_inputs": list(POLICY_OBSERVATION_KEYS),
              "requested_nominal_attempts": args.episodes, "requested_perturbed_attempts": args.perturbed_episodes,
              "scope": "repeatability_of_reference_initial_conditions_and_bounded_control_perturbations"}
    try:
        chunk_steps = getattr(args, "execute_chunk_steps", 1)
        policy = load_policy(str(args.checkpoint), args.device, execute_chunk_steps=chunk_steps)
        gripper_paths = getattr(args, "gripper_training_dataset", None)
        projection_mode = getattr(args, "gripper_projection", "clip")
        if projection_mode == "nearest" and gripper_paths is None:
            raise ValueError("Nearest gripper projection requires explicit checkpoint training datasets")
        gripper_projection = fit_gripper_projection(gripper_paths, policy.metadata, projection_mode) if gripper_paths is not None else None
        report["adapter_config"] = {"execute_chunk_steps": chunk_steps,
                                    "chunk_anchor": "decode once at chunk start to cached absolute commands" if chunk_steps > 1
                                                    else "current observation on each tick",
                                    "gripper_projection": gripper_projection or {"enabled": False}}
        report["policy_execution"] = ("policy_with_fixed_execution_adapters" if chunk_steps > 1 or gripper_projection is not None
                                      else "raw_policy")
        report["action_fields"] = {"raw_action": "absolute model output before optional gripper projection",
                                   "policy_action": "after optional fixed training-support gripper projection",
                                   "action": "physically executed after optional evaluation perturbation",
                                   "projected": "gripper projection changed model output on this tick"}
        if policy.metadata.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Policy and dataset schemas differ")
        references = [load_episode(path) for path in args.dataset]
        if any(ref["metadata"]["control_period_s"] != policy.metadata["control_period_s"] or
               ref["metadata"]["model_sha256"] != policy.metadata["model_sha256"] for ref in references):
            raise ValueError("Policy control period/model differs from reference environment")
        reference_hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in args.dataset]
        report["reference_dataset_sha256"] = reference_hashes
        report["uses_training_reference"] = bool(set(reference_hashes) & set(policy.metadata.get("train_dataset_sha256", [])))
        report["checkpoint_sha256"] = hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
        report["model_spec"] = policy.metadata["model_spec"]
        report["normalization_options"] = policy.metadata.get("normalization_options", {})
        velocity_mask = report["normalization_options"].get("robot_velocity_mask", False)
        object_velocity_mask = report["normalization_options"].get("object_velocity_mask", False)
        report["policy_observation_ablation"] = {
            "robot_velocity_mask": velocity_mask,
            "object_velocity_mask": object_velocity_mask,
            "masked_environment_indices": ((list(range(6)) if velocity_mask else []) +
                                           (list(range(13, 19)) if object_velocity_mask else [])),
            "scope": "policy normalized inputs only; physical velocities and safety unchanged"}
        limits = EvaluationLimits(args.max_simulation_s, args.max_wall_s, args.perturb_at_s,
                                  args.perturb_duration_s, args.perturb_rad)
        modes = [False] * args.episodes + [True] * args.perturbed_episodes
        for index, perturbed in enumerate(modes):
            directory = args.output / f"attempt-{index:03d}-{'perturbed' if perturbed else 'nominal'}"
            reference = references[index % len(references)]
            attempt = None
            transitions = []
            try:
                env = StateWorkcell(args.source, directory, reference["metadata"])
                monitor = PhysicalTaskMonitor(env.baseline_z)
                attempt, transitions = run_attempt(env, policy, monitor, seed=args.seed + index,
                                                  perturbed=perturbed, limits=limits,
                                                  gripper_projection=gripper_projection)
            except Exception as error:
                directory.mkdir(parents=True, exist_ok=True)
                attempt = {"seed": args.seed + index, "perturbed": perturbed, "passed": False,
                           "safety_stop": False, "failure_reason": "attempt_setup_exception",
                           "error": {"type": type(error).__name__, "message": str(error)}}
            attempt["reference_dataset_sha256"] = reference_hashes[index % len(references)]
            attempt["directory"] = directory.name
            np.savez_compressed(directory / "policy-transitions.npz",
                                **{key: np.array([row[key] for row in transitions], dtype=np.float32).reshape(-1, width)
                                   for key, width in ((POLICY_OBSERVATION_KEYS[0], 6),
                                                      (POLICY_OBSERVATION_KEYS[1], 30), ("action", 6),
                                                      ("raw_action", 6), ("policy_action", 6))},
                                timestamp=np.array([row["timestamp"] for row in transitions], dtype=np.float64),
                                next_timestamp=np.array([row["next_timestamp"] for row in transitions], dtype=np.float64),
                                perturbation=np.array([row["perturbation"] for row in transitions], dtype=bool),
                                projected=np.array([row["projected"] for row in transitions], dtype=bool))
            _json_dump(directory / "diagnostics.json", [row["diagnostic"] for row in transitions])
            _json_dump(directory / "report.json", attempt)
            report["attempts"].append(attempt)
        report["status"] = "completed_evaluation"
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    report["summary"] = summarize_attempts(report["attempts"])
    _json_dump(args.output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, nargs="+", required=True,
                        help="Reference archives supply the physical initial snapshot, never expert actions")
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[2] /
                        "workspaces/so101_ws/src/so101_mujoco/models/so101.xml")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--execute-chunk-steps", type=int, default=1,
                        help="Execution ablation: decode and cache this many chunk actions at their start-state anchor")
    parser.add_argument("--gripper-training-dataset", type=Path, nargs="+", default=None,
                        help="Projection ablation: exact checkpoint training archives providing valid gripper bounds")
    parser.add_argument("--gripper-projection", choices=("clip", "nearest"), default="clip",
                        help="Training-support projection: interval clipping or nearest of exactly two valid labels")
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument("--perturbed-episodes", type=int, default=0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-simulation-s", type=float, default=90)
    parser.add_argument("--max-wall-s", type=float, default=30)
    parser.add_argument("--perturb-at-s", type=float, default=3)
    parser.add_argument("--perturb-duration-s", type=float, default=.2)
    parser.add_argument("--perturb-rad", type=float, default=.02)
    args = parser.parse_args()
    if args.episodes < 0 or args.perturbed_episodes < 0 or not args.episodes + args.perturbed_episodes:
        parser.error("Request at least one nonnegative nominal/perturbed attempt")
    if args.seed < 0:
        parser.error("seed must be nonnegative")
    if args.execute_chunk_steps < 1:
        parser.error("execute chunk steps must be positive and at most the checkpoint chunk_size")
    if args.output is None:
        args.output = Path(__file__).parent / "output" / f"policy-eval-{uuid.uuid4().hex}"
    args.output.mkdir(parents=True, exist_ok=False)
    report = evaluate(args)
    print(json.dumps({"output": str(args.output.resolve()), "status": report["status"], **report["summary"]}, indent=2))
    return 0 if report["status"] == "completed_evaluation" and report["summary"]["failed_attempt_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
