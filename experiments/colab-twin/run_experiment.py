#!/usr/bin/env python3
"""Offline SO101 motion planning and physics baseline; no hardware connection."""
import argparse
import csv
import ctypes.util
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

os.environ.setdefault("MUJOCO_GL", "osmesa" if ctypes.util.find_library("OSMesa") else "egl")

import imageio.v2 as imageio
import mujoco
import numpy as np


def synthetic_target(time_s: float, initial: np.ndarray) -> np.ndarray:
    """Small joint-space sweep in radians, for repeatable platform validation."""
    target = initial.copy()
    wave = np.sin(2 * np.pi * time_s / 6.0)
    target[:4] += wave * np.array([0.4, 0.15, -0.2, 0.1])
    return target


def baseline(source: Path, output: Path) -> None:
    root = Path(__file__).resolve().parent
    output.mkdir(parents=True, exist_ok=True)
    scene = ET.parse(source)
    tree = scene.getroot()
    # Rewrite only the experiment copy; keep the original model unchanged.
    tree.find("compiler").set("meshdir", str(source.parent / "assets"))
    ET.SubElement(tree, "option", timestep="0.002", gravity="0 0 -9.81")
    visual = ET.SubElement(tree, "visual")
    ET.SubElement(visual, "headlight", diffuse="0.8 0.8 0.8", ambient="0.4 0.4 0.4")
    ET.SubElement(tree.find("asset"), "texture", type="skybox", builtin="gradient",
                  rgb1="0.9 0.94 0.98", rgb2="0.6 0.7 0.8", width="512", height="3072")
    world = tree.find("worldbody")
    ET.SubElement(world, "light", pos="0 -1 2", dir="0 0 -1")
    ET.SubElement(world, "geom", name="worktable", type="plane", size="0.5 0.5 0.01",
                  pos="0 0 -0.005", rgba="0.2 0.25 0.3 1")
    ET.SubElement(world, "geom", name="test_object", type="box", size="0.02 0.02 0.02",
                  pos="0.2 -0.15 0.02", rgba="0.9 0.25 0.15 1")
    scene_path = output / "scene.xml"
    scene.write(scene_path)
    model = mujoco.MjModel.from_xml_path(str(scene_path))
    if model.nq != 6 or model.nu != 6:
        raise RuntimeError(f"Expected six joints/actuators: nq={model.nq}, nu={model.nu}")
    data = mujoco.MjData(model)
    names = [model.joint(i).name for i in range(model.njnt)]
    expected = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
    if names != expected:
        raise RuntimeError(f"Unexpected joint order: {names}")
    initial = np.array([0, 0, 0, 0, 0, 0.35], dtype=float)
    data.qpos[:] = initial
    data.ctrl[:] = initial
    mujoco.mj_forward(model, data)
    tip_id = model.site("gripperframe").id
    camera = mujoco.MjvCamera()
    camera.lookat[:] = [0.1, -0.03, 0.17]
    camera.distance, camera.azimuth, camera.elevation = 1.0, 135, -25
    renderer = mujoco.Renderer(model, height=480, width=640)
    frames, rows = [], []
    max_joint_excess = 0.0
    for step in range(3000):
        target = synthetic_target(data.time, initial)
        if np.any(target < model.actuator_ctrlrange[:, 0]) or np.any(target > model.actuator_ctrlrange[:, 1]):
            raise RuntimeError("Synthetic trajectory exceeds actuator limits")
        data.ctrl[:] = target
        previous_time = float(data.time)
        mujoco.mj_step(model, data)
        if not math.isclose(data.time, previous_time + model.opt.timestep, abs_tol=1e-10):
            raise RuntimeError("Simulation time reset or stopped advancing")
        if not np.all(np.isfinite(data.qpos)) or not np.all(np.isfinite(data.qvel)):
            raise RuntimeError("Simulation state is not finite")
        excess = np.maximum(model.jnt_range[:, 0] - data.qpos, data.qpos - model.jnt_range[:, 1])
        max_joint_excess = max(max_joint_excess, float(np.max(excess)))
        if step % 20 == 0:
            # mj_step integrates qpos after deriving sites/contacts; refresh them.
            mujoco.mj_forward(model, data)
            rows.append([float(data.time), *data.qpos.tolist(), *target.tolist(),
                         *data.site_xpos[tip_id].tolist(), int(data.ncon)])
            renderer.update_scene(data, camera=camera)
            frames.append(renderer.render().copy())
    renderer.close()
    if not math.isclose(data.time, 6.0, abs_tol=1e-8):
        raise RuntimeError("Simulation did not reach six seconds")
    values = np.array(rows)
    rmse = np.sqrt(np.mean((values[:, 1:7] - values[:, 7:13]) ** 2, axis=0))
    tip_span = np.ptp(values[:, 13:16], axis=0)
    if float(np.linalg.norm(tip_span)) < 0.001:
        raise RuntimeError("End effector did not move")
    if max_joint_excess > 0.01:
        raise RuntimeError(f"Joint limit excess: {max_joint_excess} radians")
    with (output / "trajectory.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", *[f"actual_{n}_rad" for n in names],
                         *[f"target_{n}_rad" for n in names], "tip_x_m", "tip_y_m", "tip_z_m", "contacts"])
        writer.writerows(rows)
    imageio.imwrite(output / "preview.png", frames[0])
    imageio.mimsave(output / "simulation.mp4", frames, fps=25, macro_block_size=16)
    report = {
        "status": "physics_baseline_passed", "simulation_seconds": float(data.time),
        "steps": 3000, "frames": len(frames), "joint_names": names,
        "tracking_rmse_rad": dict(zip(names, rmse.tolist())),
        "tip_span_m": tip_span.tolist(), "max_joint_limit_excess_rad": max_joint_excess,
        "max_contacts": int(np.max(values[:, -1])),
        "model_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "mujoco_version": mujoco.__version__, "python_version": platform.python_version(),
        "render_backend": os.environ["MUJOCO_GL"], "hardware_connected": False,
        "acceptance": "Model load, bounded synthetic motion, finite state, joint limits and headless rendering only.",
        "not_validated": ["real-arm calibration", "collision-free planning", "grasp success", "vision", "live state sync"],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    with ZipFile(root / "results.zip", "w", ZIP_DEFLATED) as archive:
        for name in ["trajectory.csv", "preview.png", "simulation.mp4", "report.json", "scene.xml"]:
            archive.write(output / name, name)
    print(json.dumps(report, indent=2))


def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["planning", "baseline"], default="planning")
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--output", type=Path, default=root / "output")
    parser.add_argument("--no-render", action="store_true")
    args = parser.parse_args()
    source = args.model or root / "models" / "so101.xml"
    if not source.exists() and args.model is None:
        source = root.parents[1] / "workspaces/so101_ws/src/so101_mujoco/models/so101.xml"
    if args.mode == "baseline":
        baseline(source.resolve(), args.output.resolve())
    else:
        from planning_experiment import main as planning_main
        planning_main(source.resolve(), args.output.resolve(), episodes=args.episodes,
                      seed=args.seed, render=not args.no_render)


if __name__ == "__main__":
    main()
