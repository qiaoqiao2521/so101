"""Bounded RGB export, official visual ACT resource probe, fit and pure rollout.

The commands are explicit stages. Fitting requires a successful bound GPU probe;
evaluation never invokes an expert, IK or planner, nor reads environment truth
into the visual policy. Reports retain pipeline success and task success apart.
"""
from __future__ import annotations

import argparse
import copy
import ctypes.util
import hashlib
import json
import os
from pathlib import Path
import time
import traceback

os.environ.setdefault("MUJOCO_GL", "osmesa" if ctypes.util.find_library("OSMesa") else "egl")
os.environ.setdefault("MPLBACKEND", "agg")

import h5py
import numpy as np
import torch

from learning_vision import (ACTION, IMAGE, STATE, CameraSpec, LEROBOT_REVISION,
    OFFICIAL_SOURCE_SHA256, RGB_NORMALIZATION, VISUAL_MODEL_SPEC,
    VISION_FORMAT, VISION_INPUT_KEYS, VisionDataset,
    VisionPolicyRunner, build_visual_policy, capture_rgb, load_visual_checkpoint,
    make_renderer, sha256, startup_sampling_metadata, startup_sampling_order,
    local_balance_groups, local_balance_sampling_metadata, local_balance_sampling_order,
    validate_resource_report, visual_source_hashes)


def write_json(path, value):
    def scalar(item):
        if isinstance(item, np.ndarray):
            return item.tolist()
        if isinstance(item, np.generic):
            return item.item()
        raise TypeError(type(item).__name__)
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False, default=scalar) + "\n", encoding="utf8")
    temporary.replace(path)


def source_hashes():
    return visual_source_hashes()


def new_report(kind):
    return {"status": "failed", "kind": kind, "task_acceptance": "not_run",
            "policy_input_keys": list(VISION_INPUT_KEYS),
            "privileged_policy_input": False, "stage_or_clock_policy_input": False,
            "source_sha256": source_hashes(), "lerobot_revision": LEROBOT_REVISION,
            "official_source_sha256": OFFICIAL_SOURCE_SHA256,
            "model_spec": VISUAL_MODEL_SPEC, "rgb_normalization": RGB_NORMALIZATION}


def assert_exact_observation(observation, episode, index, *, after=False):
    keys = (STATE, "observation.environment_state")
    prefix = "next_" if after else ""
    for key in keys:
        if not np.array_equal(observation[key], episode[prefix + key][index]):
            error = np.abs(observation[key] - episode[prefix + key][index])
            raise RuntimeError(f"raw64 {prefix + key} mismatch at frame {index}: {error.max()}")
    expected_time = episode["next_timestamp" if after else "timestamp"][index]
    if float(observation["time_s"]) != float(expected_time):
        raise RuntimeError(f"raw64 timestamp mismatch at frame {index}")


def export(args):
    from learning_data import load_episode
    from learning_env import PhysicalTaskMonitor, StateWorkcell
    started = time.perf_counter()
    report = new_report("synchronized_raw64_expert_rgb_export")
    renderer = None
    partial = args.output / "expert-rgb.h5.partial"
    try:
        episode = load_episode(args.dataset[0])
        if not episode["eligible_for_training"] or episode["storage_precision"] != "raw_float64_policy_tensor_float32":
            raise ValueError("Need one successful complete raw64 expert episode")
        if episode["metadata"]["control_period_s"] != .02:
            raise ValueError("RGB diagnostic fixes 20ms control")
        count = len(episode["timestamp"])
        if count == 0:
            raise ValueError("Empty expert archive")
        camera_spec = CameraSpec()
        cell = StateWorkcell(args.source, args.output / "workcell", episode["metadata"])
        monitor = PhysicalTaskMonitor(cell.baseline_z)
        obs = cell.reset()
        renderer, camera = make_renderer(cell.model, camera_spec)
        report.update(camera=camera_spec.to_dict(), backend=os.environ["MUJOCO_GL"],
                      source_raw_sha256=sha256(args.dataset[0]),
                      raw_transition_count=count, valid_label_count=int(episode["label_valid"].sum()),
                      rendered_frame_count=0, raw64_exact=False,
                      max_wall_s=args.max_wall_s, sample_frame_indices=sorted(set(
                          (0, count // 4, count // 2, 3 * count // 4, count - 1))))
        import imageio.v2 as imageio
        with h5py.File(args.dataset[0], "r") as original, h5py.File(partial, "x") as out:
            for key, value in original.attrs.items():
                out.attrs[key] = value
            for key in original.keys():
                original.copy(key, out)
            out.attrs["vision_format"] = "so101-synchronized-rgb-v1"
            out.attrs["vision_complete"] = False
            out.attrs["vision_raw64_exact"] = False
            out.attrs["source_raw_sha256"] = report["source_raw_sha256"]
            out.attrs["camera_json"] = json.dumps(camera_spec.to_dict(), sort_keys=True)
            out.attrs["vision_time_semantics"] = "render(obs_t) before executed_action_t"
            out.attrs["renderer_backend"] = os.environ["MUJOCO_GL"]
            out.attrs["vision_source_sha256_json"] = json.dumps(source_hashes(), sort_keys=True)
            images = out.create_dataset(IMAGE, shape=(count, 128, 128, 3), dtype=np.uint8,
                                        chunks=(1, 128, 128, 3), compression="gzip", compression_opts=1)
            out.create_dataset("image_frame_index", data=episode["frame_index"])
            out.create_dataset("image_timestamp", data=episode["timestamp"])
            for index, action in enumerate(episode["executed_action"]):
                if time.perf_counter() - started >= args.max_wall_s:
                    raise TimeoutError("RGB export wall-time limit")
                assert_exact_observation(obs, episode, index)
                image = capture_rgb(renderer, camera, cell.data)
                images[index] = image
                report["rendered_frame_count"] = index + 1
                if index in report["sample_frame_indices"]:
                    imageio.imwrite(args.output / f"sample-{index:05d}.png", image)
                obs, row = cell.step(action)
                assert_exact_observation(obs, episode, index, after=True)
                physical = monitor.update(row)
                if physical["failure_reason"]:
                    raise RuntimeError("Expert replay physical failure: " + physical["failure_reason"])
            report["physical_acceptance"] = monitor.report()
            if not monitor.report()["passed"]:
                raise RuntimeError("Complete raw64 expert replay failed physical grasp/place")
            out.attrs["vision_complete"] = True
            out.attrs["vision_raw64_exact"] = True
            out.flush()
        renderer.close()
        renderer = None
        target = args.output / "expert-rgb.h5"
        # Never publish incomplete image rows or overwrite a prior run.
        os.link(partial, target)
        partial.unlink()
        report.update(status="passed", raw64_exact=True,
                      max_state_error_rad=0., max_environment_error=0., max_timestamp_error_s=0.,
                      archive=str(target), archive_sha256=sha256(target),
                      task_acceptance="expert_replay_passed_not_learned_policy",
                      camera_review="pending_human_or_root_sample_inspection")
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        report["traceback"] = traceback.format_exc()
    finally:
        if renderer is not None:
            renderer.close()
        report["total_s"] = time.perf_counter() - started
        write_json(args.output / "report.json", report)
    return report


def gpu_memory():
    free, total = torch.cuda.mem_get_info()
    return {"free_mib": free / 2**20, "total_mib": total / 2**20,
            "allocated_mib": torch.cuda.memory_allocated() / 2**20,
            "reserved_mib": torch.cuda.memory_reserved() / 2**20,
            "peak_allocated_mib": torch.cuda.max_memory_allocated() / 2**20,
            "peak_reserved_mib": torch.cuda.max_memory_reserved() / 2**20}


def microbenchmark(args):
    started = time.perf_counter()
    report = new_report("visual_act_cuda_five_step_microbenchmark")
    report.update(step_count_required=5, attempts=[], peak_limit_mib=3200.,
                  max_wall_s=args.max_wall_s)
    dataset = None
    try:
        if args.device != "cuda" or not torch.cuda.is_available():
            raise RuntimeError("This resource gate requires local CUDA, no cloud or implicit CPU fallback")
        torch.set_num_threads(2)
        dataset = VisionDataset(args.dataset)
        report.update(visual_dataset_sha256=dataset.visual_hashes,
                      raw_dataset_sha256=dataset.raw_hashes, camera=dataset.camera)
        for batch_size in (8, 4):
            if time.perf_counter() - started >= args.max_wall_s:
                raise TimeoutError("Microbenchmark overall wall-time limit")
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
            torch.manual_seed(0)
            attempt = {"batch_size": batch_size, "steps": 0, "step_s": [], "status": "failed",
                       "memory_before": gpu_memory()}
            report["attempts"].append(attempt)
            policy = optimizer = batch = loss = None
            try:
                policy = build_visual_policy("cuda")
                policy.train()
                optimizer = torch.optim.Adam(policy.parameters(), lr=1e-4)
                for _ in range(5):
                    if time.perf_counter() - started >= args.max_wall_s:
                        raise TimeoutError("Microbenchmark overall wall-time limit")
                    tick = time.perf_counter()
                    selection = np.arange(batch_size) % len(dataset)
                    batch = dataset.batch(selection, "cuda")
                    optimizer.zero_grad(set_to_none=True)
                    loss, _ = policy(batch)
                    if not torch.isfinite(loss):
                        raise RuntimeError("Nonfinite microbenchmark loss")
                    loss.backward()
                    optimizer.step()
                    torch.cuda.synchronize()
                    attempt["steps"] += 1
                    attempt["step_s"].append(time.perf_counter() - tick)
                attempt["memory_after"] = gpu_memory()
                peak = max(attempt["memory_after"]["peak_allocated_mib"],
                           attempt["memory_after"]["peak_reserved_mib"])
                attempt["status"] = "passed" if peak <= 3200 else "memory_limit_exceeded"
                if attempt["status"] == "passed":
                    report.update(status="passed", selected_batch_size=batch_size)
                    break
            except torch.cuda.OutOfMemoryError as error:
                attempt.update(status="cuda_oom", error=str(error), memory_after=gpu_memory())
            finally:
                del policy, optimizer, batch, loss
                torch.cuda.empty_cache()
            # Only one predeclared batch-size fallback is allowed.
        if report["status"] != "passed":
            report["failure_reason"] = "both_prespecified_resource_probes_failed"
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        report["traceback"] = traceback.format_exc()
    finally:
        if dataset is not None:
            dataset.close()
        report["total_s"] = time.perf_counter() - started
        write_json(args.output / "report.json", report)
    return report


def fit(args):
    started = time.perf_counter()
    report = new_report("visual_act_single_bounded_offline_fit")
    report.update(max_wall_s=args.max_wall_s, max_steps=args.max_steps, max_epochs=args.max_epochs,
                  optimizer="fresh Adam", learning_rate=1e-4,
                  initialization="random official ACT including random ResNet18; no downloaded/pretrained weights",
                  training_loss_scope="all_six_action_coordinates")
    dataset = policy = optimizer = None
    try:
        if args.device != "cuda" or not torch.cuda.is_available():
            raise RuntimeError("Bounded fit requires the successful local CUDA resource gate")
        resource_text = args.resource_report.read_bytes().decode("utf8")
        resource_sha256 = hashlib.sha256(resource_text.encode("utf8")).hexdigest()
        resource = json.loads(resource_text)
        dataset = VisionDataset(args.dataset)
        sampler = startup_sampling_metadata(dataset.frames, dataset.episodes,
                                            getattr(args, "startup_weight", 1))
        sampler.update(seed=args.seed, chunk_start_draw_count=0, startup_draw_count=0,
                       epoch_orders_generated=0, completed_pool_passes=0,
                       draw_count_scope="chunk starts in completed optimizer updates")
        report["training_sampler"] = sampler
        startup_mask = dataset.frames < 50
        groups = row_draw_counts = None
        if getattr(args, "local_balance", False):
            if sampler["weight"] != 5:
                raise ValueError("Local balance requires the startup-weight5 baseline")
            groups = local_balance_groups(dataset.states, dataset.frames, dataset.episodes, dataset.stages)
            local = local_balance_sampling_metadata(dataset.frames, dataset.episodes, groups, sampler["weight"])
            local.update(rng="SeedSequence([training_seed, 101]); independent of base sampling RNG",
                         chunk_start_draw_counts=[0, 0, 0], valid_action_slot_counts=[0, 0, 0],
                         group_order=["nonlocal", "startup", "settle"])
            row_draw_counts = np.zeros(len(dataset), dtype=np.int64)
            sampler["local_balance"] = local
            sampler["base_per_episode"] = sampler.pop("per_episode")
            sampler["base_theoretical_startup_fraction"] = sampler["theoretical_startup_fraction"]
            sampler["theoretical_startup_fraction"] = (
                sampler["weight"] * sampler["startup_rows"] - local["base_startup_slots"]
                + local["target_slots_per_group"]) / sampler["pool_len"]
            sampler["epoch_semantics"] += "; replace local slots with equal startup/settle counts"
        batch_size = validate_resource_report(resource, dataset.camera, dataset.visual_hashes, dataset.raw_hashes)
        report.update(resource_report_sha256=resource_sha256, batch_size=batch_size,
                      visual_dataset_sha256=dataset.visual_hashes,
                      raw_dataset_sha256=dataset.raw_hashes, training_row_count=len(dataset),
                      camera=dataset.camera, normalization=dataset.normalizer.stats)
        torch.set_num_threads(2)
        torch.manual_seed(args.seed)
        rng = np.random.default_rng(args.seed)
        local_rng = np.random.default_rng(np.random.SeedSequence([args.seed, 101]))
        policy = build_visual_policy("cuda")
        optimizer = torch.optim.Adam(policy.parameters(), lr=1e-4)
        torch.cuda.reset_peak_memory_stats()
        policy.train()
        steps, losses = 0, []
        def checkpoint_data():
            if row_draw_counts is not None:
                sampler["local_balance"]["row_draw_counts"] = row_draw_counts.tolist()
            return {
                "format": VISION_FORMAT, "policy_input_keys": list(VISION_INPUT_KEYS),
                "lerobot_revision": LEROBOT_REVISION, "official_source_sha256": OFFICIAL_SOURCE_SHA256,
                "source_sha256": source_hashes(), "normalization": dataset.normalizer.stats,
                "resource_report_text": resource_text, "resource_report_sha256": resource_sha256,
                "model_spec": VISUAL_MODEL_SPEC, "rgb_normalization": RGB_NORMALIZATION,
                "camera": dataset.camera, "action_encoding": "arm_delta_absolute_jaw",
                "control_period_s": .02, "model_sha256": dataset.metadata[0]["model_sha256"],
                "physics_dt_s": .002, "scene_configuration": dataset.metadata[0]["scene_configuration"],
                "visual_dataset_sha256": dataset.visual_hashes, "raw_dataset_sha256": dataset.raw_hashes,
                "gripper_labels_rad": dataset.gripper_labels.tolist(),
                "training_row_count": len(dataset), "training_steps": steps,
                "training_sampler": copy.deepcopy(sampler),
                "training_seed": args.seed, "optimizer": "fresh Adam", "learning_rate": 1e-4,
                "initialization": report["initialization"], "torch_version": str(torch.__version__),
                "state_dict": {key: value.detach().cpu() for key, value in policy.state_dict().items()},
            }
        snapshot_step = getattr(args, "snapshot_step", 0)
        report["snapshot"] = {"requested_step": snapshot_step, "status": "not_reached" if snapshot_step else "disabled",
                              "scope": "diagnostic only; final policy.pt remains the acceptance candidate"}
        train_started = time.perf_counter()
        stop = "epoch_limit"
        for epoch in range(args.max_epochs):
            order = startup_sampling_order(dataset.frames, rng, sampler["weight"])
            if groups is not None:
                order = local_balance_sampling_order(order, groups, local_rng)
            sampler["epoch_orders_generated"] += 1
            for start in range(0, len(order), batch_size):
                if steps >= args.max_steps:
                    stop = "step_limit"
                    break
                if time.perf_counter() - train_started >= args.max_wall_s:
                    stop = "optimization_wall_time_limit"
                    break
                selection = order[start:start + batch_size]
                batch = dataset.batch(selection, "cuda")
                optimizer.zero_grad(set_to_none=True)
                loss, loss_metrics = policy(batch)
                if not torch.isfinite(loss):
                    raise RuntimeError("Nonfinite visual training loss")
                loss.backward()
                grad = torch.nn.utils.clip_grad_norm_(policy.parameters(), 10.)
                if not torch.isfinite(grad):
                    raise RuntimeError("Nonfinite visual gradient")
                optimizer.step()
                torch.cuda.synchronize()
                steps += 1
                sampler["chunk_start_draw_count"] += len(selection)
                sampler["startup_draw_count"] += int(startup_mask[selection].sum())
                if groups is not None:
                    np.add.at(row_draw_counts, selection, 1)
                    for group in (0, 1, 2):
                        selected = selection[groups[selection] == group]
                        local["chunk_start_draw_counts"][group] += len(selected)
                        local["valid_action_slot_counts"][group] += int(dataset.lengths[selected].sum())
                if steps == snapshot_step:
                    snapshot_started = time.perf_counter()
                    snapshot_path = args.output / f"policy-step-{steps}.pt"
                    torch.save(checkpoint_data(), snapshot_path)
                    report["snapshot"].update(status="saved", checkpoint=str(snapshot_path),
                        checkpoint_sha256=sha256(snapshot_path), training_steps=steps,
                        save_s=time.perf_counter() - snapshot_started,
                        wall_budget_includes_snapshot_save=True)
                if steps == 1 or steps % 50 == 0:
                    losses.append({"step": steps, "normalized_l1": float(loss.detach()),
                                   "training_s": time.perf_counter() - train_started})
                if max(torch.cuda.max_memory_allocated(), torch.cuda.max_memory_reserved()) > 3200 * 2**20:
                    raise RuntimeError("Training exceeded the original 3200MiB resource gate")
            else:
                sampler["completed_pool_passes"] += 1
            if stop != "epoch_limit":
                break
        if steps == 0:
            raise RuntimeError("No optimization step completed")
        report.update(training_steps=steps, stop_reason=stop,
                      training_s=time.perf_counter() - train_started, loss_samples=losses,
                      gpu=gpu_memory(), parameters=sum(p.numel() for p in policy.parameters()))
        checkpoint = checkpoint_data()
        # Compare reload on the SAME device to avoid hiding a CPU/GPU numerical difference.
        reference = dataset.batch(np.arange(min(batch_size, len(dataset))), "cpu")
        policy = policy.cpu().eval()
        with torch.no_grad():
            expected = policy.predict_action_chunk({key: reference[key] for key in VISION_INPUT_KEYS})
        checkpoint_path = args.output / "policy.pt"
        torch.save(checkpoint, checkpoint_path)
        restored, normalizer, metadata = load_visual_checkpoint(checkpoint_path, "cpu")
        with torch.no_grad():
            actual = restored.predict_action_chunk({key: reference[key] for key in VISION_INPUT_KEYS})
        error = float((expected - actual).abs().max())
        if not torch.equal(expected, actual) or normalizer.stats != dataset.normalizer.stats:
            raise RuntimeError(f"Checkpoint reload changed same-device inference: {error}")
        report.update(status="completed_diagnostic", checkpoint=str(checkpoint_path),
                      checkpoint_sha256=sha256(checkpoint_path), reload_max_abs_error_normalized=error,
                      checkpoint_reload_exact=True, task_acceptance="not_run",
                      diagnostic_limit="single train episode is not held-out validation")
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        report["traceback"] = traceback.format_exc()
    finally:
        if dataset is not None:
            dataset.close()
        del policy, optimizer
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        report["total_s"] = time.perf_counter() - started
        write_json(args.output / "report.json", report)
    return report


def evaluate(args):
    from learning_data import load_episode
    from learning_env import PhysicalTaskMonitor, StateWorkcell
    started = time.perf_counter()
    report = new_report("nominal_pure_visual_policy_single_attempt")
    report.update(passed=False, safety_stop=False, failure_reason=None, steps=0,
                  max_wall_s=args.max_wall_s, max_simulation_s=args.max_simulation_s,
                  expert_or_planner_used=False, held_out_evaluated=False, perturbation_injected=False)
    renderer = monitor = None
    rows, images = [], []
    try:
        reference = load_episode(args.dataset[0])
        if not reference["eligible_for_training"]:
            raise ValueError("Need a passed physical reference")
        policy, normalizer, metadata = load_visual_checkpoint(args.checkpoint, args.device)
        if (metadata["model_sha256"] != reference["metadata"]["model_sha256"] or
                metadata["control_period_s"] != reference["metadata"]["control_period_s"] or
                metadata["physics_dt_s"] != reference["metadata"]["physics_dt_s"] or
                metadata["scene_configuration"] != reference["metadata"]["scene_configuration"]):
            raise ValueError("Checkpoint and reference model/control differ")
        report.update(checkpoint_sha256=sha256(args.checkpoint),
                      resource_report_sha256=metadata["resource_report_sha256"],
                      reference_raw_sha256=sha256(args.dataset[0]), camera=metadata["camera"],
                      execute_chunk_steps=args.execute_chunk_steps, device=args.device,
                      gripper_projection={"kind": "nearest_training_label_support_only", "labels_rad": metadata["gripper_labels_rad"]})
        cell = StateWorkcell(args.source, args.output / "workcell", reference["metadata"])
        monitor = PhysicalTaskMonitor(cell.baseline_z)
        obs = cell.reset()
        camera_spec = CameraSpec(**metadata["camera"])
        renderer, camera = make_renderer(cell.model, camera_spec)
        runner = VisionPolicyRunner(policy, normalizer, metadata, args.device, args.execute_chunk_steps)
        runner.reset()
        first_time = obs["time_s"]
        while True:
            if time.perf_counter() - started >= args.max_wall_s:
                report["failure_reason"] = "wall_time_limit"
                break
            if obs["time_s"] - first_time + .02 > args.max_simulation_s + 1e-8:
                report["failure_reason"] = "simulation_time_limit"
                break
            rgb = capture_rgb(renderer, camera, cell.data)
            before_state = obs[STATE].copy()
            raw, command = runner.predict({STATE: before_state, IMAGE: rgb})
            report["last_command"] = {"time_s": obs["time_s"], "raw_action": raw.tolist(),
                                      "action": command.tolist()}
            next_obs, diagnostic = cell.step(command)
            if not np.isclose(next_obs["time_s"] - obs["time_s"], .02, rtol=0, atol=1e-8):
                raise RuntimeError("Visual policy/control period differs")
            rows.append({"timestamp": obs["time_s"], "next_timestamp": next_obs["time_s"],
                         STATE: before_state, "next_state": next_obs[STATE].copy(),
                         "raw_action": raw.copy(), "action": command.copy(), "diagnostic": diagnostic})
            # Store sparse visual evidence; full 50Hz state/action transitions are retained.
            if len(rows) % 100 == 1:
                images.append((len(rows) - 1, rgb))
            report["steps"] = len(rows)
            physical = monitor.update(diagnostic)
            obs = next_obs
            if physical["failure_reason"] or physical["safety_stop"]:
                report.update(failure_reason=physical["failure_reason"], safety_stop=physical["safety_stop"])
                break
            if physical["passed"]:
                report["passed"] = True
                break
    except Exception as error:
        is_safety = type(error).__name__ == "SafetyStop"
        report.update(failure_reason="safety_stop" if is_safety else "execution_exception",
                      safety_stop=is_safety,
                      error={"type": type(error).__name__, "message": str(error)})
        if hasattr(error, "details"):
            report["failure_details"] = error.details
        report["traceback"] = traceback.format_exc()
    finally:
        if renderer is not None:
            renderer.close()
        physical = monitor.report() if monitor is not None else None
        report["physical_acceptance"] = physical
        report["passed"] = bool(report["passed"] and physical and physical["passed"] and
                                not report["failure_reason"] and not report["safety_stop"])
        report["status"] = "passed" if report["passed"] else "failed"
        report["task_acceptance"] = "single_nominal_visual_passed" if report["passed"] else "not_passed"
        def matrix(key, width):
            return np.asarray([row[key] for row in rows], dtype=np.float64).reshape(-1, width)
        np.savez_compressed(args.output / "policy-transitions.npz",
            timestamp=np.asarray([row["timestamp"] for row in rows]),
            next_timestamp=np.asarray([row["next_timestamp"] for row in rows]),
            **{STATE: matrix(STATE, 6), "next_observation.state": matrix("next_state", 6)},
            raw_action=matrix("raw_action", 6), action=matrix("action", 6),
            diagnostic_json=np.asarray([json.dumps(row["diagnostic"], sort_keys=True) for row in rows]))
        import imageio.v2 as imageio
        for index, image in images:
            imageio.imwrite(args.output / f"policy-sample-{index:05d}.png", image)
        write_json(args.output / "trajectory.json", rows)
        report["total_s"] = time.perf_counter() - started
        write_json(args.output / "report.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("export", "microbenchmark", "fit", "evaluate"))
    parser.add_argument("--dataset", nargs="+", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[2] /
                        "workspaces/so101_ws/src/so101_mujoco/models/so101.xml")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--max-wall-s", type=float, default=120.)
    parser.add_argument("--max-simulation-s", type=float, default=90.)
    parser.add_argument("--max-steps", type=int, default=5000)
    parser.add_argument("--max-epochs", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--startup-weight", type=int, choices=(1, 5), default=1,
                        help="Fit only: repeat eligible chunk starts with raw frame index <50")
    parser.add_argument("--local-balance", action="store_true",
                        help="Fit only with startup-weight5: balance real near-q startup/settle slots 1:1")
    parser.add_argument("--snapshot-step", type=int, default=0,
                        help="Fit only: save a diagnostic checkpoint at this step inside the same wall budget")
    parser.add_argument("--execute-chunk-steps", type=int, default=16)
    parser.add_argument("--resource-report", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--camera-reviewed", action="store_true",
                        help="Root/user inspected the exported sample frames before training")
    args = parser.parse_args(argv)
    if args.stage != "fit" and args.startup_weight != 1:
        parser.error("--startup-weight other than 1 is only allowed for fit")
    if args.local_balance and (args.stage != "fit" or args.startup_weight != 5):
        parser.error("--local-balance is fit-only and requires --startup-weight 5")
    if args.snapshot_step and (args.stage != "fit" or not 1 <= args.snapshot_step <= args.max_steps):
        parser.error("--snapshot-step must be a fit step in [1,max_steps]")
    if not 0 < args.max_wall_s <= 120 or not np.isfinite(args.max_wall_s):
        parser.error("wall budget must be finite and in (0,120] seconds")
    if not 0 < args.max_simulation_s <= 90 or not np.isfinite(args.max_simulation_s):
        parser.error("simulation budget must be finite and in (0,90] seconds")
    if not 1 <= args.max_steps <= 5000 or not 1 <= args.max_epochs <= 200 or args.seed < 0:
        parser.error("training budgets exceed this bounded diagnostic")
    if args.execute_chunk_steps not in range(1, 17):
        parser.error("execution chunk must be 1 through 16")
    if args.stage in ("export", "evaluate") and len(args.dataset) != 1:
        parser.error("export/evaluate accept exactly one reference episode")
    if args.stage == "fit" and (args.resource_report is None or not args.camera_reviewed):
        parser.error("fit requires --resource-report and --camera-reviewed")
    if args.stage == "evaluate" and args.checkpoint is None:
        parser.error("evaluate requires --checkpoint")
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"export": export, "microbenchmark": microbenchmark, "fit": fit, "evaluate": evaluate}[args.stage](args)
    print(json.dumps({"stage": args.stage, "output": str(args.output), "status": report["status"],
                      "passed": report.get("passed"), "steps": report.get("steps", report.get("training_steps")),
                      "error": report.get("error")}, ensure_ascii=False))
    return 0 if report["status"] in ("passed", "completed_diagnostic") else 1


if __name__ == "__main__":
    raise SystemExit(main())
