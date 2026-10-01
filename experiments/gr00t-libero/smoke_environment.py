#!/usr/bin/env python3
"""Exercise official LIBERO physics/cameras on CPU; never claim a GR00T rollout."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
from pathlib import Path
import time

from common import ROOT, load_lock, verify_source, write_report


def positive_steps(value: str) -> int:
    count = int(value)
    if not 1 <= count <= 1000:
        raise argparse.ArgumentTypeError("steps must be between 1 and 1000")
    return count


def run(args: argparse.Namespace, report: dict) -> None:
    lock = load_lock()
    source = args.work_dir / "upstream" / f"LIBERO-{lock['libero_revision']}"
    source_manifest = json.loads((args.work_dir / "upstream/source.json").read_text())
    verified_files = verify_source(source, source_manifest, lock["libero_revision"])
    config_dir = args.output_dir / "libero-config"
    config_dir.mkdir(parents=True, exist_ok=True)
    benchmark_root = source / "libero/libero"
    dataset_dir = args.output_dir / "unused-datasets"
    dataset_dir.mkdir(exist_ok=True)
    # JSON is a YAML subset. Pre-create the dedicated config before LIBERO imports,
    # avoiding its interactive initialization and the user's ~/.libero entirely.
    config = {
        "benchmark_root": str(benchmark_root),
        "bddl_files": str(benchmark_root / "bddl_files"),
        "init_states": str(benchmark_root / "init_files"),
        "assets": str(benchmark_root / "assets"),
        "datasets": str(dataset_dir),
    }
    (config_dir / "config.yaml").write_text(json.dumps(config))
    os.environ["LIBERO_CONFIG_PATH"] = str(config_dir)
    os.environ["MUJOCO_GL"] = args.renderer
    os.environ["PYOPENGL_PLATFORM"] = args.renderer
    os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["MPLCONFIGDIR"] = str(args.output_dir / "matplotlib-cache")
    os.environ["NUMBA_CACHE_DIR"] = str(args.output_dir / "numba-cache")
    import numpy as np
    from PIL import Image
    from libero.libero import benchmark
    from libero.libero.envs import OffScreenRenderEnv

    suite = benchmark.get_benchmark_dict()[args.suite]()
    task_names = suite.get_task_names()
    if args.task not in task_names:
        raise ValueError(f"Unknown task for suite {args.suite}: {args.task}")
    task = suite.get_task(task_names.index(args.task))
    bddl = Path(config["bddl_files"]) / task.problem_folder / task.bddl_file
    if not bddl.is_file():
        raise FileNotFoundError("Pinned LIBERO task BDDL is missing")
    report.update({
        "libero_revision": source_manifest["revision"],
        "archive_sha256": source_manifest["archive_sha256"],
        "source_files_verified": verified_files,
        "bddl_sha256": hashlib.sha256(bddl.read_bytes()).hexdigest(),
        "task": task.name, "language": task.language, "renderer": args.renderer,
        "execution_device": "cpu", "policy_kind": "environment_noop_or_random",
        "seed": args.seed, "action_kind": args.action,
        "initial_state_kind": "seeded_env_reset_not_benchmark_init_state",
        "versions": {name: importlib.metadata.version(name) for name in
                     ("numpy", "mujoco", "robosuite", "bddl", "torch")},
        "python_version": platform.python_version(),
    })
    env = OffScreenRenderEnv(
        bddl_file_name=str(bddl), camera_heights=256, camera_widths=256,
        ignore_done=True,
    )
    image_reports = {}

    def observe(observation: dict, phase: str) -> None:
        for key in ("robot0_eef_pos", "robot0_eef_quat", "robot0_joint_pos"):
            value = np.asarray(observation[key])
            if not np.isfinite(value).all():
                raise ValueError(f"Non-finite state: {key}")
        for key in ("agentview_image", "robot0_eye_in_hand_image"):
            pixels = np.asarray(observation[key])
            if pixels.shape != (256, 256, 3) or pixels.dtype != np.uint8:
                raise ValueError(f"Unexpected camera shape/dtype: {key}")
            if float(pixels.std()) <= 0:
                raise ValueError(f"Camera image is constant: {key}")
            path = args.output_dir / f"{phase}_{key}.png"
            # Same orientation correction used by GR00T's official LIBERO adapter.
            Image.fromarray(pixels[::-1, ::-1]).save(path)
            image_reports[f"{phase}_{key}"] = {
                "file": path.name, "shape": list(pixels.shape), "dtype": str(pixels.dtype),
                "pixel_sha256": hashlib.sha256(pixels.tobytes()).hexdigest(),
                "std": float(pixels.std()),
            }

    try:
        env.seed(args.seed)
        observation = env.reset()
        observe(observation, "reset")
        from OpenGL.GL import GL_RENDERER, GL_VENDOR, glGetString
        report["graphics"] = {name: (glGetString(key) or b"").decode("utf-8", "replace")
                              for name, key in (("renderer", GL_RENDERER), ("vendor", GL_VENDOR))}
        initial_eef = np.asarray(observation["robot0_eef_pos"]).copy()
        initial_time = float(env.sim.data.time)
        rng = np.random.default_rng(args.seed)
        successes = [bool(env.check_success())]
        rewards = []
        states = []
        for index in range(args.steps):
            action = np.zeros(7, dtype=np.float32)
            if args.action == "random":
                action[:6] = rng.uniform(-0.05, 0.05, 6)
            observation, reward, done, _ = env.step(action)
            successes.append(bool(env.check_success()))
            rewards.append(float(reward))
            states.append({"step": index + 1, "sim_time_s": float(env.sim.data.time),
                           "action": action.tolist(),
                           "eef_xyz": np.asarray(observation["robot0_eef_pos"]).tolist(),
                           "success": successes[-1], "done": bool(done)})
        observe(observation, "final")
        elapsed = float(env.sim.data.time) - initial_time
        if not elapsed > 0:
            raise ValueError("MuJoCo simulation time did not advance")
        if not np.isfinite(rewards).all():
            raise ValueError("Non-finite reward")
        report.update({
            "status": "passed", "environment_completed": True,
            "task_success": successes[-1], "success_seen": any(successes),
            "steps_executed": len(states), "sim_time_advanced_s": elapsed,
            "initial_eef_xyz": initial_eef.tolist(),
            "final_eef_xyz": np.asarray(observation["robot0_eef_pos"]).tolist(),
            "images": image_reports, "steps": states,
        })
    finally:
        env.close()


def main() -> int:
    lock = load_lock()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, default=ROOT / "output")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output/environment-smoke")
    parser.add_argument("--suite", choices=("libero_10", "libero_goal", "libero_object", "libero_spatial"), default="libero_10")
    parser.add_argument("--task", default=lock["default_task"])
    parser.add_argument("--steps", type=positive_steps, default=10)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--action", choices=("noop", "random"), default="noop")
    parser.add_argument("--renderer", choices=("osmesa", "egl"), default="osmesa")
    args = parser.parse_args()
    if not 0 <= args.seed < 2**32:
        parser.error("seed must be in [0, 2**32)")
    args.work_dir = args.work_dir.resolve()
    args.output_dir = args.output_dir.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {"schema_version": 1, "kind": "libero_environment_only", "status": "failed",
              "environment_completed": False, "gr00t_rollout_completed": False,
              "task_success": None, "gr00t_revision": lock["gr00t_revision"]}
    start = time.monotonic()
    try:
        run(args, report)
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    report["elapsed_wall_s"] = time.monotonic() - start
    write_report(args.output_dir / "report.json", report)
    print(json.dumps({key: report[key] for key in
                     ("kind", "status", "environment_completed", "gr00t_rollout_completed", "task_success")}))
    print(f"Report: {args.output_dir / 'report.json'}")
    return 0 if report["environment_completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
