"""Bounded ACT/MLP compute probes; setup/import/warmup are timed separately.

The synthetic batch checks dependencies and resource feasibility only. Passing
does not establish convergence, task success, robustness or visual-policy fit.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import uuid


def atomic_json(path: Path, data: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def run_worker(args: argparse.Namespace) -> int:
    report = {"model": args.worker, "status": "failed", "synthetic_only": True,
              "batch_size": args.batch_size, "steps": args.steps,
              "device_requested": args.device, "threshold_mib": args.threshold_mib,
              "compute_budget_s": args.compute_budget_s}
    started = time.perf_counter()
    try:
        import numpy as np
        import torch
        from learning_models import (ACTION, ENV_STATE, STATE, LEROBOT_REVISION,
                                     ModelSpec, build_policy)
        report["import_s"] = time.perf_counter() - started
        if args.device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError("CUDA requested but unavailable; no silent CPU substitution")
        torch.set_num_threads(2)
        torch.manual_seed(args.seed)
        spec = ModelSpec(model=args.worker, environment_dim=args.environment_dim)
        report["model_spec"] = spec.to_dict()
        report["lerobot_revision"] = LEROBOT_REVISION if args.worker == "act" else None
        report["torch_version"] = torch.__version__
        report["cuda_runtime"] = torch.version.cuda
        device = torch.device(args.device)
        cuda = device.type == "cuda"
        if cuda:
            if device.index is None:
                device = torch.device("cuda", torch.cuda.current_device())
            torch.cuda.set_device(device)
            free, total = torch.cuda.mem_get_info(device)
            report["gpu"] = {"name": torch.cuda.get_device_name(device),
                             "free_before_mib": free / 2**20, "total_mib": total / 2**20}
        setup_started = time.perf_counter()
        policy = build_policy(spec, str(device))
        report["policy_class"] = f"{type(policy).__module__}.{type(policy).__name__}"
        report["parameters"] = sum(p.numel() for p in policy.parameters())
        optimizer = torch.optim.Adam(policy.parameters(), lr=1e-4)
        batch = {
            STATE: torch.randn(args.batch_size, spec.state_dim, device=device),
            ENV_STATE: torch.randn(args.batch_size, spec.environment_dim, device=device),
            ACTION: torch.randn(args.batch_size, spec.chunk_size, spec.action_dim, device=device),
            "action_is_pad": torch.zeros(args.batch_size, spec.chunk_size, dtype=torch.bool, device=device),
        }

        def step():
            policy.train()
            optimizer.zero_grad(set_to_none=True)
            loss, metrics = policy(batch)
            if not torch.isfinite(loss):
                raise RuntimeError("Non-finite forward loss")
            loss.backward()
            if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in policy.parameters()):
                raise RuntimeError("Non-finite gradient")
            optimizer.step()
            return float(loss.detach()), metrics

        if cuda:
            torch.cuda.synchronize(device)
        report["construction_s"] = time.perf_counter() - setup_started
        warm_started = time.perf_counter()
        for _ in range(args.warmup_steps):
            step()
        if cuda:
            torch.cuda.synchronize(device)
            report["warmup_peak_reserved_mib"] = torch.cuda.max_memory_reserved(device) / 2**20
            torch.cuda.reset_peak_memory_stats(device)
        report["warmup_s"] = time.perf_counter() - warm_started
        compute_started = time.perf_counter()
        losses = [step()[0] for _ in range(args.steps)]
        if cuda:
            torch.cuda.synchronize(device)
        report["compute_s"] = time.perf_counter() - compute_started
        report["losses"] = losses
        if cuda:
            free, _ = torch.cuda.mem_get_info(device)
            report["gpu"].update({
                "peak_allocated_mib": torch.cuda.max_memory_allocated(device) / 2**20,
                "peak_reserved_mib": torch.cuda.max_memory_reserved(device) / 2**20,
                "free_after_mib": free / 2**20,
            })
        policy.eval()
        policy.reset()
        with torch.no_grad():
            prediction = policy.select_action({STATE: batch[STATE], ENV_STATE: batch[ENV_STATE]})
        report["inference_shape"] = list(prediction.shape)
        if not torch.isfinite(prediction).all() or list(prediction.shape) != [args.batch_size, spec.action_dim]:
            raise RuntimeError("Invalid policy inference shape/values")
        memory_ok = (not cuda or max(report["gpu"]["peak_reserved_mib"],
                     report["warmup_peak_reserved_mib"]) <= args.threshold_mib)
        report["memory_gate"] = "go" if memory_ok else "no_go"
        report["compute_budget_gate"] = "go" if report["compute_s"] <= args.compute_budget_s else "no_go"
        report["status"] = "passed"
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        report["traceback"] = traceback.format_exc()
        # CUDA errors are preserved in this process; the next model starts in a
        # fresh process so a failed context does not contaminate the fallback.
    report["total_s"] = time.perf_counter() - started
    atomic_json(args.output / f"{args.worker}.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "traceback"}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--environment-dim", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--steps", type=int, default=5)
    parser.add_argument("--warmup-steps", type=int, default=2)
    parser.add_argument("--threshold-mib", type=float, default=3200)
    parser.add_argument("--compute-budget-s", type=float, default=10)
    parser.add_argument("--worker-timeout-s", type=float, default=90)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--worker", choices=("act", "mlp"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if min(args.batch_size, args.steps, args.environment_dim) < 1 or args.warmup_steps < 1:
        parser.error("dimensions/step counts must be positive")
    if args.output is None:
        args.output = Path(__file__).resolve().parent / "output" / f"learning-probe-{uuid.uuid4().hex}"
    if args.worker:
        return run_worker(args)
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    results = {}
    for model in ("act", "mlp"):
        command = [sys.executable, str(Path(__file__).resolve()), "--worker", model,
                   "--output", str(args.output), "--device", args.device,
                   "--environment-dim", str(args.environment_dim), "--batch-size", str(args.batch_size),
                   "--steps", str(args.steps), "--warmup-steps", str(args.warmup_steps),
                   "--threshold-mib", str(args.threshold_mib), "--compute-budget-s", str(args.compute_budget_s),
                   "--seed", str(args.seed)]
        environment = dict(os.environ)
        for key in ("PYTHONPATH", "PYTHONHOME"):
            environment.pop(key, None)
        environment["PYTHONNOUSERSITE"] = "1"
        try:
            with (args.output / f"{model}.log").open("w") as log:
                process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                         env=environment, timeout=args.worker_timeout_s)
            if (args.output / f"{model}.json").exists():
                result = json.loads((args.output / f"{model}.json").read_text())
            else:
                result = {"model": model, "status": "failed", "error": "worker did not return a report"}
            result["process_exit_code"] = process.returncode
        except subprocess.TimeoutExpired:
            result = {"model": model, "status": "timeout", "worker_timeout_s": args.worker_timeout_s,
                      "interpretation": "setup/import/warmup/compute were not distinguished; no performance conclusion"}
        results[model] = result
    act = results["act"]
    mlp = results["mlp"]
    def go(row):
        return row.get("status") == "passed" and row.get("memory_gate") == "go" and row.get("compute_budget_gate") == "go"
    recommendation = "act" if go(act) else "mlp" if go(mlp) else "stop"
    report = {"synthetic_only": True, "models": results, "recommendation": recommendation,
              "total_wall_s": time.perf_counter() - started,
              "scope": "Resource/dependency gate only; dataset convergence and pure-policy task acceptance remain separate."}
    atomic_json(args.output / "report.json", report)
    print(json.dumps({"output": str(args.output), "recommendation": recommendation,
                      "statuses": {key: value["status"] for key, value in results.items()}}, ensure_ascii=False))
    return 0 if recommendation != "stop" else 1


if __name__ == "__main__":
    raise SystemExit(main())
