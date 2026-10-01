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
from learning_models import (ACTION, ENV_STATE, STATE, LEROBOT_REVISION, ModelSpec,
                             StateNormalizer, build_policy, load_policy_checkpoint)


def make_chunks(rows: dict, chunk_size: int, normalizer: StateNormalizer) -> dict:
    """Pad segment tails, never bridge failed labels, frame gaps or episodes."""
    count = len(rows[ACTION])
    if not count:
        raise ValueError("No eligible expert transitions")
    normalized = {key: normalizer.normalize(key, rows[key]) for key in (STATE, ENV_STATE, ACTION)}
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
        actions[start, :length] = normalized[ACTION][start:end]
        padding[start, :length] = False
    return {STATE: torch.from_numpy(normalized[STATE]),
            ENV_STATE: torch.from_numpy(normalized[ENV_STATE]),
            ACTION: torch.from_numpy(actions), "action_is_pad": torch.from_numpy(padding)}


def evaluate_regression(policy, batch: dict, normalizer: StateNormalizer,
                        device: str, batch_size: int) -> dict:
    """Deterministic eval latent=0; report reconstruction rather than VAE total."""
    policy.eval()
    total = 0.0
    count = 0
    per_joint = np.zeros(6)
    with torch.no_grad():
        for start in range(0, len(batch[ACTION]), batch_size):
            part = {key: value[start:start + batch_size].to(device) for key, value in batch.items()}
            if hasattr(policy, "predict_action_chunk"):
                prediction = policy.predict_action_chunk({STATE: part[STATE], ENV_STATE: part[ENV_STATE]})
            else:
                prediction = policy.select_action(part)[:, None, :]
                part[ACTION] = part[ACTION][:, :1]
                part["action_is_pad"] = part["action_is_pad"][:, :1]
            valid = ~part["action_is_pad"]
            error = (prediction - part[ACTION]).abs()
            total += float((error * valid[..., None]).sum())
            count += int(valid.sum()) * prediction.shape[-1]
            # First-action regression expresses the command used at a control tick.
            absolute = normalizer.action_radians(prediction[:, 0])
            target = normalizer.action_radians(part[ACTION][:, 0])
            per_joint += np.abs(absolute - target).sum(axis=0)
    return {"normalized_l1": total / max(1, count),
            "first_action_mae_rad_per_joint": (per_joint / len(batch[ACTION])).tolist(),
            "first_action_mae_rad": float(per_joint.sum() / (len(batch[ACTION]) * 6))}


def train(args) -> dict:
    started = time.perf_counter()
    report = {"status": "failed", "model": args.model, "schema_version": SCHEMA_VERSION,
              "task_acceptance": "not_run", "max_steps": args.max_steps,
              "max_epochs": args.max_epochs, "max_wall_s": args.max_wall_s}
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
        normalization = StateNormalizer.fit(rows)
        environment_dim = rows[ENV_STATE].shape[1]
        spec = ModelSpec(model=args.model, environment_dim=environment_dim,
                         chunk_size=args.chunk_size, use_vae=not args.no_vae,
                         dropout=args.dropout)
        data = make_chunks(rows, spec.chunk_size, normalization)
        validation_rows = training_rows(validation_paths) if validation_paths else None
        validation = make_chunks(validation_rows, spec.chunk_size, normalization) if validation_paths else None
        metadata = [load_episode(path)["metadata"] for path in paths if load_episode(path)["eligible_for_training"]]
        periods = {meta["control_period_s"] for meta in metadata}
        model_hashes = {meta["model_sha256"] for meta in metadata}
        if len(periods) != 1 or len(model_hashes) != 1:
            raise ValueError("Mixed control periods or physical models require an explicit adapter")
        policy = build_policy(spec, args.device)
        optimizer = torch.optim.Adam(policy.parameters(), lr=args.learning_rate)
        report["model_spec"] = spec.to_dict()
        report["parameters"] = sum(p.numel() for p in policy.parameters())
        report["before_training"] = evaluate_regression(policy, data, normalization, args.device, args.batch_size)
        if args.device.startswith("cuda"):
            torch.cuda.reset_peak_memory_stats()
        losses = []
        steps = 0
        training_started = time.perf_counter()
        stop = "epoch_limit"
        for epoch in range(args.max_epochs):
            indices = rng.permutation(len(rows[ACTION]))
            for start in range(0, len(indices), args.batch_size):
                if steps >= args.max_steps:
                    stop = "step_limit"
                    break
                if time.perf_counter() - training_started >= args.max_wall_s:
                    stop = "wall_time_limit"
                    break
                selection = indices[start:start + args.batch_size]
                batch = {key: value[selection].to(args.device) for key, value in data.items()}
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
        if restored_normalization.stats != normalization.stats or reload_error > 1e-4:
            raise RuntimeError(f"Checkpoint reload changed predictions/statistics: {reload_error}")
        report["checkpoint"] = {"filename": checkpoint_path.name,
                                "sha256": hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
                                "reload_max_abs_error_normalized": reload_error}
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
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--chunk-size", type=int, default=16)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--max-epochs", type=int, default=200)
    parser.add_argument("--max-wall-s", type=float, default=120)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--no-vae", action="store_true", help="explicit deterministic ACT diagnostic variant")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    if min(args.max_steps, args.max_epochs, args.batch_size, args.chunk_size, args.max_wall_s) <= 0:
        parser.error("training budgets and dimensions must be positive")
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
