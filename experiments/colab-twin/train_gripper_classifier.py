"""Bounded training of an explicit categorical state gripper with frozen ACT."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import time
import traceback

import numpy as np
import torch

from learning_data import audit_episodes, load_episode, training_rows
from learning_models import ACTION, ENV_STATE, STATE, load_policy_checkpoint
from learning_gripper import (GRIPPER_CLASSES, GRIPPER_FORMAT, GripperClassifier,
                              classifier_inputs, fit_input_statistics, masked_classification_loss)
from train_state_policy import critical_sampling_weights, make_chunks


def prepare_classifier_data(rows, base_normalizer, chunk_size):
    chunks = make_chunks(rows, chunk_size, base_normalizer)
    observations = {key: chunks[key] for key in (STATE, ENV_STATE)}
    statistics = fit_input_statistics(observations)
    raw_jaw = np.asarray(rows[ACTION])[:, 5]
    classes = np.full(len(raw_jaw), -1, dtype=np.int64)
    for index, value in enumerate(GRIPPER_CLASSES):
        classes[np.isclose(raw_jaw, value, rtol=0, atol=1e-9)] = index
    if np.any(classes < 0):
        raise ValueError("Valid expert jaw labels must be exactly .015 or .5 radians")
    padding = chunks["action_is_pad"]
    labels = torch.zeros(padding.shape, dtype=torch.long)
    for start in range(len(labels)):
        count = int((~padding[start]).sum())
        labels[start, :count] = torch.from_numpy(classes[start:start + count])
    return {"inputs": classifier_inputs(observations, statistics), "labels": labels,
            "padding": padding}, statistics


def evaluate_classification(model, data, device, batch_size):
    model.eval()
    confusion = torch.zeros(2, 2, dtype=torch.long)
    total_loss = total = first_correct = 0
    with torch.no_grad():
        for start in range(0, len(data["inputs"]), batch_size):
            inputs, labels, padding = [data[key][start:start + batch_size].to(device)
                                      for key in ("inputs", "labels", "padding")]
            logits = model(inputs)
            valid = ~padding
            prediction = logits.argmax(-1)
            loss = masked_classification_loss(logits, labels, padding)
            n = int(valid.sum())
            total_loss += float(loss) * n
            total += n
            first_correct += int((prediction[:, 0] == labels[:, 0]).sum())
            counts = torch.bincount((labels[valid] * 2 + prediction[valid]).cpu(), minlength=4)
            confusion += counts.reshape(2, 2)
    return {"scope": "eligible training rows only; no held-out or physical evidence",
            "valid_chunk_action_count": total, "masked_cross_entropy": total_loss / total,
            "chunk_action_accuracy": float(confusion.diag().sum()) / total,
            "first_action_accuracy": first_correct / len(data["inputs"]),
            "confusion_true_rows_predicted_columns": confusion.tolist()}


def train(args):
    started = time.perf_counter()
    report = {"status": "failed", "task_acceptance": "not_run"}
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        if (not 1 <= args.max_steps <= 6000 or not 0 < args.max_wall_s <= 60 or args.max_epochs < 1
                or args.batch_size < 1 or not np.isfinite(args.learning_rate) or args.learning_rate <= 0):
            raise ValueError("Classifier training requires positive bounded steps, epochs, batches and <=60 seconds")
        if args.device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError("CUDA unavailable; use --device cpu explicitly")
        torch.set_num_threads(2)
        torch.manual_seed(args.seed)
        if args.device.startswith("cuda"):
            torch.cuda.reset_peak_memory_stats(args.device)
        rng = np.random.default_rng(args.seed)
        paths = [Path(path).resolve() for path in args.dataset]
        if not paths or len(set(paths)) != len(paths):
            raise ValueError("Require unique positive training archives")
        hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
        if len(set(hashes)) != len(hashes):
            raise ValueError("Repeated training archive hashes")
        episodes = [load_episode(path) for path in paths]
        if any(not episode["eligible_for_training"] or episode["report"].get("passed") is not True
               for episode in episodes):
            raise ValueError("Classifier accepts positive eligible training archives only")
        base_path = Path(args.base_checkpoint).resolve()
        base_metadata = torch.load(base_path, map_location="cpu", weights_only=True)
        spec = base_metadata["model_spec"]
        if (spec["model"] != "act" or spec["use_vae"] or spec["dropout"] != 0
                or "learned_gripper_classifier" in base_metadata
                or not set(base_metadata["train_dataset_sha256"]) <= set(hashes)):
            raise ValueError("Require deterministic base ACT and its original training subset")
        if any(episode["metadata"]["model_sha256"] != base_metadata["model_sha256"]
               or episode["metadata"]["control_period_s"] != base_metadata["control_period_s"] for episode in episodes):
            raise ValueError("Training episodes and base physical model/control period differ")
        base_policy, normalizer, _ = load_policy_checkpoint(str(base_path), args.device)
        base_policy.eval()
        for parameter in base_policy.parameters():
            parameter.requires_grad_(False)
        frozen = {key: value.detach().cpu().clone() for key, value in base_policy.state_dict().items()}
        rows = training_rows(paths)
        data, statistics = prepare_classifier_data(rows, normalizer, spec["chunk_size"])
        classifier = GripperClassifier(spec["chunk_size"]).to(args.device)
        sample_weights, sample_audit = critical_sampling_weights(rows, args.critical_sample_weight)
        sampled_rows = np.zeros(len(rows[ACTION]), dtype=bool)
        options = {"component": "independent_gripper_classifier", "learning_rate": args.learning_rate,
                   "batch_size": args.batch_size, "seed": args.seed, "max_steps": args.max_steps,
                   "max_wall_s": args.max_wall_s, "max_epochs": args.max_epochs,
                   "critical_sample_weight": args.critical_sample_weight, "optimizer": "fresh Adam"}
        report.update(train_audit=audit_episodes(paths), train_dataset_sha256=hashes,
                      base_checkpoint_sha256=hashlib.sha256(base_path.read_bytes()).hexdigest(),
                      classifier_input_statistics=statistics,
                      input_transform={"inputs_are_base_normalized_and_masked": True,
                                       "zero_std_rule": "exact zero -> 1; no clipping or additional mask",
                                       "base_normalization_options": base_metadata.get("normalization_options", {})},
                      training_options=options, classifier_parameter_count=sum(p.numel() for p in classifier.parameters()),
                      before_training=evaluate_classification(classifier, data, args.device, args.batch_size))
        optimizer = torch.optim.Adam(classifier.parameters(), lr=args.learning_rate)
        train_started = time.perf_counter()
        steps = 0
        stop = "epoch_limit"
        for epoch in range(args.max_epochs):
            indices = (rng.choice(len(rows[ACTION]), len(rows[ACTION]), replace=True,
                                  p=sample_weights / sample_weights.sum()) if args.critical_sample_weight > 1
                       else rng.permutation(len(rows[ACTION])))
            for start in range(0, len(indices), args.batch_size):
                if steps >= args.max_steps:
                    stop = "step_limit"
                    break
                if time.perf_counter() - train_started >= args.max_wall_s:
                    stop = "wall_time_limit"
                    break
                selection = indices[start:start + args.batch_size]
                inputs, labels, padding = [data[key][selection].to(args.device)
                                          for key in ("inputs", "labels", "padding")]
                classifier.train()
                optimizer.zero_grad(set_to_none=True)
                loss = masked_classification_loss(classifier(inputs), labels, padding)
                loss.backward()
                if any(parameter.grad is not None and not torch.isfinite(parameter.grad).all()
                       for parameter in classifier.parameters()):
                    raise RuntimeError("Nonfinite classifier gradient")
                optimizer.step()
                sampled_rows[selection] = True
                sample_audit["actual_draw_count"] += len(selection)
                selected_weights = sample_weights[selection]
                sample_audit["actual_upweighted_draw_count"] += int((selected_weights > 1).sum())
                for value, count in zip(*np.unique(selected_weights, return_counts=True)):
                    sample_audit["actual_draw_weight_counts"][str(float(value))] += int(count)
                steps += 1
                if args.device.startswith("cuda"):
                    torch.cuda.synchronize()
            if stop != "epoch_limit":
                break
        report.update(steps=steps, training_s=time.perf_counter() - train_started,
                      epochs_started=epoch + 1, stop_reason=stop,
                      after_training=evaluate_classification(classifier, data, args.device, args.batch_size))
        sample_audit["actual_unique_row_count"] = int(sampled_rows.sum())
        sample_audit["epoch_semantics"] = ("N draws with replacement; not every frame visited per epoch"
                                            if args.critical_sample_weight > 1 else "one permutation of all N rows")
        current = base_policy.state_dict()
        if set(current) != set(frozen) or any(not torch.equal(current[key].cpu(), frozen[key]) for key in frozen):
            raise RuntimeError("Independent classifier fitting changed base ACT state")
        base_sha = report["base_checkpoint_sha256"]
        component = {"format": GRIPPER_FORMAT,
                     "architecture": {"input_width": 36, "hidden_widths": [64, 64],
                                      "chunk_size": spec["chunk_size"], "classes": 2},
                     "input_keys": [STATE, ENV_STATE], "inputs_are_base_normalized_and_masked": True,
                     "input_statistics": statistics,
                     "input_transform": report["input_transform"], "classes_rad": list(GRIPPER_CLASSES),
                     "train_dataset_sha256": hashes, "base_checkpoint_sha256": base_sha,
                     "input_statistics_training_dataset_sha256": hashes,
                     "classifier_parameter_count": report["classifier_parameter_count"],
                     "training_options": options, "sampling": sample_audit,
                     "initialization": "random classifier; frozen base ACT weights",
                     "source_sha256": hashlib.sha256(Path(__file__).with_name("learning_gripper.py").read_bytes()).hexdigest(),
                     "loss": "masked categorical cross entropy; exclude padding/gaps",
                     "state_dict": {key: value.detach().cpu() for key, value in classifier.state_dict().items()}}
        summary = {"kind": "frozen_official_act_arm_plus_learned_state_gripper",
                   "base_training_loss_scope": base_metadata.get("training_loss_scope", "all_action_coordinates"),
                   "classifier_architecture": component["architecture"], "input_keys": [STATE, ENV_STATE],
                   "inputs_are_base_normalized_and_masked": True,
                   "base_normalization_options": base_metadata.get("normalization_options", {}),
                   "classes_rad": list(GRIPPER_CLASSES), "base_checkpoint_sha256": base_sha,
                   "classifier_source_sha256": component["source_sha256"]}
        checkpoint = copy.deepcopy(base_metadata)
        checkpoint.update(state_dict=frozen, train_dataset_sha256=hashes, validation_dataset_sha256=[],
                          learned_gripper_classifier=component, policy_architecture=summary,
                          gripper_output_scope="supervised by the independent learned gripper classifier",
                          training_options=options, sampling=sample_audit,
                          initialization={"status": "random_classifier_with_frozen_base",
                                          "base_checkpoint_sha256": base_sha,
                                          "base_training_dataset_sha256": base_metadata["train_dataset_sha256"]},
                          parameter_update_scope={"mode": "independent_gripper_classifier", "base_frozen_state_verified": True,
                                                  "checked_base_tensors": len(frozen)})
        destination = args.output / "policy.pt"
        torch.save(checkpoint, destination)
        restored, restored_normalizer, _ = load_policy_checkpoint(str(destination), "cpu")
        raw = {key: rows[key][:2] for key in (STATE, ENV_STATE)}
        batch = {key: torch.from_numpy(normalizer.normalize(key, values)) for key, values in raw.items()}
        with torch.no_grad():
            restored_output = restored.predict_action_chunk(batch)
        if not torch.isfinite(restored_output).all() or restored_normalizer.stats != normalizer.stats:
            raise RuntimeError("Composite checkpoint reload changed normalization or produced invalid output")
        report.update(status="completed_diagnostic", policy_architecture=summary,
                      base_frozen_state_verified=True, checked_base_tensors=len(frozen),
                      checkpoint={"filename": "policy.pt", "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()},
                      sampling=sample_audit, training_options={"learning_rate": args.learning_rate, "batch_size": args.batch_size,
                                                             **options},
                      normalization_preserved=True)
        if args.device.startswith("cuda"):
            report["gpu"] = {"peak_allocated_mib": torch.cuda.max_memory_allocated(args.device) / 2**20,
                             "peak_reserved_mib": torch.cuda.max_memory_reserved(args.device) / 2**20}
    except Exception as error:
        report.update(error={"type": type(error).__name__, "message": str(error)}, traceback=traceback.format_exc())
    report["total_s"] = time.perf_counter() - started
    (args.output / "report.json").write_text(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, nargs="+", required=True)
    parser.add_argument("--base-checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--learning-rate", type=float, default=.001)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--critical-sample-weight", type=float, default=5)
    parser.add_argument("--max-steps", type=int, default=6000)
    parser.add_argument("--max-wall-s", type=float, default=60)
    parser.add_argument("--max-epochs", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    report = train(parser.parse_args())
    print(json.dumps({key: report.get(key) for key in ("status", "steps", "training_s", "checkpoint", "error")}, indent=2))
    return 0 if report["status"] == "completed_diagnostic" else 1


if __name__ == "__main__":
    raise SystemExit(main())
