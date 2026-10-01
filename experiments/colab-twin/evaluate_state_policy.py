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


def run_attempt(env, policy, monitor, *, seed, perturbed, limits, clock=time.perf_counter):
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
            action = np.asarray(policy.predict(before), dtype=np.float64)
            if action.shape != (6,) or not np.isfinite(action).all():
                result.update(failure_reason="invalid_policy_action", safety_stop=True)
                break
            injecting = False
            if (perturbed and perturb_start_s is None and elapsed >= limits.perturb_at_s
                    and can_inject_perturbation(diagnostic, env.baseline_z)):
                perturb_start_s = elapsed
            if perturb_start_s is not None and injected_ticks < required_ticks:
                action = action + perturbation_offset
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
        policy = load_policy(str(args.checkpoint), args.device)
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
                                                  perturbed=perturbed, limits=limits)
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
                                                      (POLICY_OBSERVATION_KEYS[1], 30), ("action", 6))},
                                timestamp=np.array([row["timestamp"] for row in transitions], dtype=np.float64),
                                next_timestamp=np.array([row["next_timestamp"] for row in transitions], dtype=np.float64),
                                perturbation=np.array([row["perturbation"] for row in transitions], dtype=bool))
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
    if args.output is None:
        args.output = Path(__file__).parent / "output" / f"policy-eval-{uuid.uuid4().hex}"
    args.output.mkdir(parents=True, exist_ok=False)
    report = evaluate(args)
    print(json.dumps({"output": str(args.output.resolve()), "status": report["status"], **report["summary"]}, indent=2))
    return 0 if report["status"] == "completed_evaluation" and report["summary"]["failed_attempt_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
