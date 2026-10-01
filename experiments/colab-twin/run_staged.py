#!/usr/bin/env python3
"""Local SO101 dependency -> reset/step -> IK/OMPL -> servo episode gates."""
import argparse
import csv
import ctypes.util
from datetime import datetime, timezone
import importlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import time
import uuid
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent
STAGES = ("dependencies", "reset_step", "single_plan", "servo_episode")


class StageFailure(RuntimeError):
    pass


def run_gate(report, name, check):
    """Run only the next gate, requiring all preceding observations to pass."""
    index = STAGES.index(name)
    if any(report["stages"][previous]["status"] != "passed" for previous in STAGES[:index]):
        raise StageFailure("A preceding gate has not passed")
    stage = report["stages"][name]
    started = time.monotonic()
    stage["status"] = "running"
    try:
        stage["evidence"] = check()
        stage["status"] = "passed"
    except Exception as error:
        stage.update(status="failed", error_type=type(error).__name__, reason=str(error))
        raise StageFailure(name) from error
    finally:
        stage["elapsed_wall_s"] = round(time.monotonic() - started, 6)


def check_dependencies():
    pinned = {}
    for line in (ROOT / "requirements.txt").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        package, expected = line.split("==")
        actual = version(package)
        if actual != expected:
            raise RuntimeError(f"{package}: required {expected}, installed {actual}")
        pinned[package] = actual
    # Verify native imports too: package metadata alone is not runtime evidence.
    for module in ("mujoco", "mink", "ompl.base", "ompl.geometric", "ompl.util",
                   "numpy", "imageio.v2", "imageio_ffmpeg"):
        importlib.import_module(module)
    return {"versions": pinned, "numpy_version": version("numpy"),
            "python_version": platform.python_version(), "native_imports_passed": True}


def run(source, output, *, seed=0, render=False):
    if not 0 <= seed <= 0xFFFFFFFF:
        raise ValueError("seed must be in [0, 2**32 - 1]")
    output.mkdir(parents=True, exist_ok=False)
    report = {"kind": "so101_staged_acceptance", "status": "running",
              "started_utc": datetime.now(timezone.utc).isoformat(), "seed": seed,
              "hardware_connected": False, "cloud_allocated": False,
              "episodes_requested": 1, "servo_episode_completed": False,
              "task_success": None, "render_requested": render,
              "stages": {name: {"status": "not_run"} for name in STAGES},
              "feedback_scope": "MuJoCo position servos and measured execution validation; static preplanned path",
              "not_validated": ["dynamic replanning", "grasp", "vision", "real hardware",
                                "continuous collision detection", "acceleration/torque limits"]}
    context = {}
    # This runner is headless and local; graphics imports occur after the first gate.
    os.environ.setdefault("MPLBACKEND", "agg")
    os.environ.setdefault("MUJOCO_GL", "osmesa" if ctypes.util.find_library("OSMesa") else "egl")

    def reset_step():
        import hashlib
        import mujoco
        import numpy as np
        from collision_scene import build_scene, CollisionChecker, JOINT_NAMES
        scenario = json.loads((ROOT / "planning_scenario.json").read_text())
        initial = np.asarray(scenario["initial_qpos"], dtype=float)
        target = np.asarray(scenario["target_xyz"], dtype=float)
        model = build_scene(source, output / "scene.xml", scenario["obstacles"])
        if model.nq != 6 or model.nu != 6 or tuple(model.joint(i).name for i in range(6)) != JOINT_NAMES:
            raise RuntimeError("Unexpected SO101 joint/actuator layout")
        checker = CollisionChecker(model, gripper=float(initial[5]),
                                   margin_m=float(scenario["clearance_margin_m"]))
        if not checker.is_valid(initial):
            raise RuntimeError("Fixture initial configuration is invalid")
        data = mujoco.MjData(model)
        mujoco.mj_resetData(model, data)
        data.qpos[:] = initial
        data.ctrl[:] = initial
        mujoco.mj_forward(model, data)
        for _ in range(10):
            previous = float(data.time)
            mujoco.mj_step(model, data)
            if not np.isclose(data.time - previous, model.opt.timestep, rtol=0, atol=1e-10):
                raise RuntimeError("Simulation time did not advance by one timestep")
            if not np.all(np.isfinite(data.qpos)) or not np.all(np.isfinite(data.qvel)):
                raise RuntimeError("Reset/step produced nonfinite physical state")
            if not checker.evaluate(data.qpos, require_fixed_gripper=False)["valid"]:
                raise RuntimeError("Reset/step produced an invalid physical configuration")
        context.update(model=model, checker=checker, initial=initial, target=target)
        xml = ET.parse(source).getroot()
        meshdir = source.parent / xml.find("compiler").get("meshdir", ".")
        assets = {mesh.get("file"): hashlib.sha256((meshdir / mesh.get("file")).read_bytes()).hexdigest()
                  for mesh in xml.findall(".//asset/mesh")}
        return {"model_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "mesh_sha256": assets,
                "physical_steps": 10, "simulation_seconds": float(data.time),
                "initial_valid": True, "physical_samples_valid": True}

    def single_plan():
        from planning_experiment import plan_target
        from joint_planner import validate_joint_path
        planned = plan_target(context["model"], context["checker"], context["initial"], context["target"], seed)
        (output / "planning.json").write_text(json.dumps(planned, indent=2, allow_nan=False) + "\n")
        if planned["ik"]["status"] != "solved" or planned["planner"]["status"] != "solved":
            raise RuntimeError("IK/OMPL did not find an exact route")
        if planned["direct_path"]["valid"]:
            raise RuntimeError("Fixture direct interpolation was not blocked")
        verified = validate_joint_path(planned["planner"]["path"], context["checker"].is_valid)
        if not verified["valid"]:
            raise RuntimeError("Independent path recheck failed")
        context["planned"] = planned
        return {"ik_error_m": planned["ik"]["error_m"], "direct_path_blocked": True,
                "exact_solution": planned["planner"]["exact_solution"],
                "waypoints": len(planned["planner"]["path"]), "path_validation": verified}

    def servo_episode():
        from planning_experiment import execute_path
        from position_ik import JOINT_NAMES
        actual, rows, frames = execute_path(context["model"], context["planned"]["planner"]["path"],
                                           context["initial"], context["target"], context["checker"], render=render)
        report["servo_episode_completed"] = True
        report["task_success"] = bool(actual["passed"])
        with (output / "trajectory.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["time_s", *[f"actual_{name}_rad" for name in JOINT_NAMES],
                             *[f"target_{name}_rad" for name in JOINT_NAMES],
                             "tip_x_m", "tip_y_m", "tip_z_m", "contacts"])
            writer.writerows(rows)
        (output / "execution.json").write_text(json.dumps(actual, indent=2, allow_nan=False) + "\n")
        if render:
            if not frames:
                raise RuntimeError("Rendered episode produced no frames")
            import imageio.v2 as imageio
            imageio.imwrite(output / "preview.png", frames[-1])
            imageio.mimsave(output / "simulation.mp4", frames, fps=25, macro_block_size=16)
        if not actual["passed"]:
            raise RuntimeError("Actual execution failed TCP/collision/joint-limit acceptance")
        return actual

    try:
        for name, check in zip(STAGES, (check_dependencies, reset_step, single_plan, servo_episode)):
            run_gate(report, name, check)
            (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
            print(json.dumps({"stage": name, "status": "passed"}), flush=True)
        report["status"] = "passed"
    except StageFailure as error:
        report["status"] = "failed"
        report["failed_stage"] = str(error)
    finally:
        (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    source = args.model or ROOT.parents[1] / "workspaces/so101_ws/src/so101_mujoco/models/so101.xml"
    output = args.output.resolve() / ("staged-" + uuid.uuid4().hex)
    report = run(source.resolve(), output, seed=args.seed, render=args.render)
    print(json.dumps({"status": report["status"], "task_success": report["task_success"],
                      "report": str(output / "report.json")}), flush=True)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
