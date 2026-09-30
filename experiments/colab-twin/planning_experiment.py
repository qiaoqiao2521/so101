"""Cartesian target -> Mink -> OMPL -> independent MuJoCo execution."""
import csv
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
import os
from zipfile import ZipFile, ZIP_DEFLATED

import imageio.v2 as imageio
import mujoco
import numpy as np

from collision_scene import build_scene, CollisionChecker
from joint_planner import plan_joint_path, validate_joint_path
from position_ik import solve_position_ik, JOINT_NAMES


RESULT_FILES = {"trajectory.csv", "preview.png", "simulation.mp4", "report.json",
                "scene.xml", "planning.json", "benchmark.json"}


def execute_path(model, path, initial, target_xyz, checker, *, render=False):
    """Follow the geometric path with bounded speed and measure actual state.

    Quintic progress starts/stops at zero speed. Piecewise linear joint-space
    corners are retained, so this is a velocity bound, not an acceleration or
    torque guarantee. Position actuators and gravity remain the original model.
    """
    points = np.asarray(path, dtype=float)
    distances = np.linalg.norm(np.diff(points, axis=0), axis=1)
    keep = np.r_[True, distances > 1e-12]
    points = points[keep]
    if len(points) == 1:
        points = np.repeat(points, 2, axis=0)
    arc = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    length = float(arc[-1])
    speed_limit = 0.4
    duration = max(2.0, 1.875 * length / speed_limit)
    settle_s = 1.0
    data = mujoco.MjData(model)  # Never reuse collision-search state.
    data.qpos[:] = initial
    data.ctrl[:] = initial
    mujoco.mj_forward(model, data)
    tip = model.site("gripperframe").id
    rows, frames = [], []
    renderer = mujoco.Renderer(model, height=480, width=640) if render else None
    camera = mujoco.MjvCamera()
    camera.lookat[:] = [0.08, -0.02, 0.16]
    camera.distance, camera.azimuth, camera.elevation = 0.9, 135, -25
    minimum_distance = float("inf")
    invalid_samples = 0
    first_invalid = None
    max_excess = 0.0
    timestep = float(model.opt.timestep)
    sample_steps = max(1, round(0.02 / timestep))
    video_steps = max(1, round(0.04 / timestep))
    steps = math.ceil((duration + 2 * settle_s) / timestep)
    try:
        for step in range(steps):
            u = float(np.clip((data.time - settle_s) / duration, 0.0, 1.0))
            progress = 10 * u**3 - 15 * u**4 + 6 * u**5
            arm = np.array([np.interp(progress * length, arc, points[:, j]) for j in range(5)])
            command = np.r_[arm, initial[5]]
            if np.any(command < model.actuator_ctrlrange[:, 0]) or np.any(command > model.actuator_ctrlrange[:, 1]):
                raise RuntimeError("Time-parameterized command exceeds actuator bounds")
            data.ctrl[:] = command
            old_time = float(data.time)
            mujoco.mj_step(model, data)
            if not math.isclose(data.time, old_time + timestep, abs_tol=1e-9):
                raise RuntimeError("Simulation time stopped advancing")
            if not np.all(np.isfinite(data.qpos)) or not np.all(np.isfinite(data.qvel)):
                raise RuntimeError("Non-finite simulation state")
            max_excess = max(max_excess, float(np.max(np.maximum(
                model.jnt_range[:, 0] - data.qpos, data.qpos - model.jnt_range[:, 1]))))
            if step % sample_steps == 0 or step == steps - 1:
                mujoco.mj_forward(model, data)
                collision = checker.evaluate(data.qpos, require_fixed_gripper=False)
                distance = collision["min_distance_m"]
                if distance is not None and math.isfinite(distance):
                    minimum_distance = min(minimum_distance, distance)
                if not collision["valid"]:
                    invalid_samples += 1
                    if first_invalid is None:
                        first_invalid = {"time_s": float(data.time), **collision}
                rows.append([float(data.time), *data.qpos.tolist(), *command.tolist(),
                             *data.site_xpos[tip].tolist(), int(data.ncon)])
            if renderer is not None and step % video_steps == 0:
                mujoco.mj_forward(model, data)
                renderer.update_scene(data, camera=camera)
                frames.append(renderer.render().copy())
    finally:
        if renderer is not None:
            renderer.close()
    mujoco.mj_forward(model, data)
    error = float(np.linalg.norm(data.site_xpos[tip] - target_xyz))
    values = np.asarray(rows)
    return {
        "passed": error <= 0.01 and invalid_samples == 0 and max_excess <= 0.01,
        "final_tcp_m": data.site_xpos[tip].tolist(), "final_error_m": error,
        "reach_tolerance_m": 0.01, "invalid_samples": invalid_samples,
        "first_invalid": first_invalid, "min_distance_m": minimum_distance,
        "collision_sample_period_s": sample_steps * timestep,
        "max_joint_limit_excess_rad": max_excess,
        "tracking_rmse_rad": dict(zip(JOINT_NAMES, np.sqrt(np.mean(
            (values[:, 1:7] - values[:, 7:13]) ** 2, axis=0)).tolist())),
        "command_joint_speed_limit_rad_s": speed_limit,
        "path_length_rad": length, "simulation_seconds": float(data.time),
        "steps": steps, "frames": len(frames),
    }, rows, frames


def plan_target(model, checker, initial, target, seed):
    ik = solve_position_ik(model, initial, target, seed=seed, tolerance_m=0.002,
                           candidate_valid=checker.is_valid)
    if ik["status"] != "solved":
        return {"ik": ik, "planner": {"status": "ik_failed", "path": None}}
    bounds = np.c_[np.maximum(model.jnt_range[:5, 0], model.actuator_ctrlrange[:5, 0]),
                   np.minimum(model.jnt_range[:5, 1], model.actuator_ctrlrange[:5, 1])]
    goal = np.asarray(ik["qpos"])
    direct = validate_joint_path([initial[:5], goal[:5]], checker.is_valid)
    planned = plan_joint_path(initial[:5], goal[:5], bounds, checker.is_valid, seed=seed)
    return {"ik": ik, "direct_path": direct, "planner": planned}


def main(source: Path, output: Path, *, episodes=20, seed=0, render=True):
    if episodes < 1 or episodes > 100:
        raise ValueError("episodes must be in [1, 100]")
    if not 0 <= seed <= 0xFFFFFFFF - episodes:
        raise ValueError("seed must leave room for all episode seeds")
    output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent
    scenario = json.loads((root / "planning_scenario.json").read_text())
    initial = np.asarray(scenario["initial_qpos"], dtype=float)
    target = np.asarray(scenario["target_xyz"], dtype=float)
    model = build_scene(source, output / "scene.xml", scenario["obstacles"])
    checker = CollisionChecker(model, gripper=float(initial[5]), margin_m=0.002)
    if not checker.is_valid(initial):
        raise RuntimeError(f"Invalid fixture start: {checker.evaluate(initial)}")
    main_plan = plan_target(model, checker, initial, target, seed)
    (output / "planning.json").write_text(json.dumps(main_plan, indent=2) + "\n")
    if main_plan["planner"]["status"] != "solved":
        raise RuntimeError("Obstacle scenario did not produce an exact path")
    if main_plan["direct_path"]["valid"]:
        raise RuntimeError("Fixture did not block direct joint interpolation")
    execution, rows, frames = execute_path(model, main_plan["planner"]["path"], initial, target, checker, render=render)
    # Each episode perturbs the Cartesian target, then independently solves and
    # physically executes. OMPL uses one process-wide seed sequence, not resets.
    rng = np.random.default_rng(seed)
    trials = []
    for index in range(episodes):
        trial_target = target + rng.uniform(-0.003, 0.003, size=3)
        planned = plan_target(model, checker, initial, trial_target, seed + index + 1)
        trial = {"episode": index, "ik_seed": seed + index + 1,
                 "target_xyz": trial_target.tolist(), "ik": planned["ik"],
                 "planner": {k: v for k, v in planned["planner"].items() if k != "path"}}
        if planned["planner"]["status"] == "solved":
            actual, _, _ = execute_path(model, planned["planner"]["path"], initial, trial_target, checker)
            trial["execution"] = actual
            trial["passed"] = actual["passed"]
            trial["direct_path_blocked"] = not planned["direct_path"]["valid"]
        else:
            trial["passed"] = False
        trials.append(trial)
    negative_ik = solve_position_ik(model, initial, np.array([4.0, 4.0, 4.0]), attempts=2, max_iterations=60)
    blocked_model = build_scene(source, output / "blocked-scene.xml", [
        {"name": "sealed_workspace", "pos": [0, 0, 0.3], "size": [0.5, 0.5, 0.6]}])
    blocked = CollisionChecker(blocked_model, gripper=float(initial[5]))
    blocked_plan = plan_joint_path(initial[:5], np.asarray(main_plan["ik"]["qpos"])[:5],
                                  model.jnt_range[:5], blocked.is_valid, timeout_s=0.1)
    negatives = {"unreachable_target": negative_ik["status"],
                 "sealed_workspace": blocked_plan["status"],
                 "passed": negative_ik["qpos"] is None and blocked_plan["path"] is None}
    errors = [t["execution"]["final_error_m"] for t in trials if "execution" in t]
    benchmark = {"episodes": episodes, "passed": sum(t["passed"] for t in trials),
                 "jitter_xyz_half_width_m": 0.003, "seed": seed, "trials": trials,
                 "direct_path_blocked_count": sum(t.get("direct_path_blocked", False) for t in trials),
                 "error_m": {"mean": float(np.mean(errors)), "p90": float(np.percentile(errors, 90)),
                              "max": max(errors)} if errors else None,
                 "negative_cases": negatives}
    (output / "benchmark.json").write_text(json.dumps(benchmark, indent=2) + "\n")
    with (output / "trajectory.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", *[f"actual_{n}_rad" for n in JOINT_NAMES],
                         *[f"target_{n}_rad" for n in JOINT_NAMES], "tip_x_m", "tip_y_m", "tip_z_m", "contacts"])
        writer.writerows(rows)
    if frames:
        imageio.imwrite(output / "preview.png", frames[-1])
        imageio.mimsave(output / "simulation.mp4", frames, fps=25, macro_block_size=16)
    passed = execution["passed"] and benchmark["passed"] == episodes and negatives["passed"]
    report = {
        "status": "motion_planning_passed" if passed else "motion_planning_failed",
        "target_xyz": target.tolist(), "direct_path_blocked": True,
        "path_validation": main_plan["planner"]["validation"],
        "ik_error_m": main_plan["ik"]["error_m"], "execution": execution,
        "benchmark_passed": benchmark["passed"], "benchmark_episodes": episodes,
        "benchmark_error_m": benchmark["error_m"],
        "benchmark_direct_path_blocked": benchmark["direct_path_blocked_count"],
        "negative_cases": negatives, "frames": len(frames),
        "model_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "versions": {name: version(name) for name in ("mujoco", "mink", "ompl")},
        "python_version": platform.python_version(), "render_backend": os.environ.get("MUJOCO_GL"),
        "hardware_connected": False,
        "collision_scope": "Discrete mesh convex-hull distances; same-body and direct-parent exclusions; fixed base/table installation excluded.",
        "excluded_collision_pairs": checker.excluded_pairs,
        "not_validated": ["continuous collision detection", "grasp", "vision", "real calibration", "live state synchronization", "acceleration and torque limits"],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    if render:
        with ZipFile(root / "results.zip", "w", ZIP_DEFLATED) as archive:
            for name in sorted(RESULT_FILES):
                archive.write(output / name, name)
    print(json.dumps({k: v for k, v in report.items() if k != "excluded_collision_pairs"}, indent=2))
    if not passed:
        raise RuntimeError("Motion planning acceptance failed; inspect report and benchmark")
