"""Paired physical SO101 collision fixture, bounded and simulation-only.

Uses the same fixed nominal joint policy, start and hazard trajectory off/on.
Hazard pose here is simulator ground truth. RGB-D tracking has its own check;
this experiment must not be presented as a VLA or a perception safety result.
"""
from __future__ import annotations

import argparse
import ctypes.util
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid
import xml.etree.ElementTree as ET

os.environ.setdefault("MUJOCO_GL", "osmesa" if ctypes.util.find_library("OSMesa") else "egl")
import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/colab-twin"))
from grasp_episode import build_contact_scene, solve_pinch_ik
from grasp_workcell import numbers
from arm_geometry import audit_geometry_coverage
from cbf_filter import Ellipsoid
from runtime import JOINT_NAMES, SimulationSafetyAdapter

SOURCE = ROOT / "workspaces/so101_ws/src/so101_mujoco/models/so101.xml"
DT = .02


def build_fixture(output):
    _, rig, base = build_contact_scene(SOURCE, output)
    start = np.r_[solve_pinch_ik(rig, np.array([.24, .14, .06])), .45]
    goal = start.copy()
    goal[0] -= 1.15
    middle = (start + goal) / 2
    query = mujoco.MjData(rig)
    query.qpos[:6] = middle
    mujoco.mj_forward(rig, query)
    center = query.geom_xpos[rig.geom("collision_gripper_1").id].copy()
    tree = ET.parse(base)
    root = tree.getroot()
    world = root.find("worldbody")
    world.remove(world.find("geom[@name='approach_obstacle']"))
    body = ET.SubElement(world, "body", name="safety_hazard", mocap="true", pos=numbers(center))
    ET.SubElement(body, "geom", name="safety_hazard_geom", type="ellipsoid", size=".023 .023 .023",
                  contype="1", conaffinity="3", rgba=".93 .27 .10 1", group="0")
    path = output / "safety-workcell.xml"
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return mujoco.MjModel.from_xml_path(str(path)), start, goal, center, path


def contacts(model, data):
    hazard = model.geom("safety_hazard_geom").id
    pairs = []
    for contact in data.contact:
        if hazard in (contact.geom1, contact.geom2) and contact.dist <= 0:
            other = contact.geom2 if contact.geom1 == hazard else contact.geom1
            body = model.body(int(model.geom_bodyid[other])).name
            if body in ("lower_arm", "wrist", "gripper", "moving_jaw_so101_v1", "upper_arm", "shoulder"):
                pairs.append({"body": body, "distance_m": float(contact.dist)})
    return pairs


def draw_guards(renderer, guards):
    for guard in guards:
        if renderer.scene.ngeom >= renderer.scene.maxgeom:
            break
        geom = renderer.scene.geoms[renderer.scene.ngeom]
        mujoco.mjv_initGeom(geom, mujoco.mjtGeom.mjGEOM_ELLIPSOID,
                           guard.semi_axes, guard.center, guard.rotation.ravel(),
                           np.array([.10, .72, .48, .17], dtype=np.float32))
        renderer.scene.ngeom += 1


def run_trial(model, start, goal, center, output, *, enabled, scenario, render, max_seconds):
    from arm_geometry import world_ellipsoids
    data = mujoco.MjData(model)
    data.qpos[:6] = start
    data.ctrl[:] = start
    mujoco.mj_forward(model, data)
    # Reset-only settling with gravity compensation, outside measured trial.
    for _ in range(250):
        data.qfrc_applied[:6] = data.qfrc_bias[:6]
        mujoco.mj_step(model, data)
    adapter = SimulationSafetyAdapter(model)
    mocap = int(model.body("safety_hazard").mocapid[0])
    writer = renderer = None
    if render:
        import imageio.v2 as imageio
        renderer = mujoco.Renderer(model, height=544, width=960)
        writer = imageio.get_writer(output / f"{scenario}-{'on' if enabled else 'off'}.mp4",
                                    fps=25, codec="libx264", quality=8)
    camera = mujoco.MjvCamera()
    camera.lookat[:] = [.20, .015, .18]
    camera.distance, camera.azimuth, camera.elevation = .9, 120, -30
    rows, hit_ticks, first_hit = [], 0, None
    joint_limit_samples, maximum_actual_velocity = 0, 0.
    contact_checks, physics_steps = 0, 0
    initial_sim_time = data.time
    stop_reason, reached, stable = None, False, 0
    previous_center = center.copy()
    control_steps = int(max_seconds / DT)
    for step in range(control_steps):
        t = step * DT
        hazard_center = center.copy()
        if scenario == "withdrawal":
            # +y retreats from the guarded arm at this fixture's stop pose.
            # Other approach directions are not certified by this one case.
            hazard_center[1] += min(.4, max(0., t - 5.) * .12)
        velocity = (hazard_center - previous_center) / DT
        previous_center = hazard_center.copy()
        data.mocap_pos[mocap] = hazard_center
        mujoco.mj_forward(model, data)
        boundary_hits = contacts(model, data)
        contact_checks += 1
        if boundary_hits:
            hit_ticks += 1
            if first_hit is None:
                first_hit = {"time_s": t, "pairs": boundary_hits}
        q = data.qpos[:6].copy()
        nominal = q.copy()
        nominal[:5] += DT * np.clip(3. * (goal[:5] - q[:5]), -.3, .3)
        nominal[5] = .45
        hazard = Ellipsoid(hazard_center, np.eye(3), np.full(3, .023))
        result = adapter.apply(data, nominal, hazard, hazard_velocity=velocity) if enabled else None
        if result is not None and result.action is None:
            stop_reason = result.metrics["reason"]
            rows.append({"step": step, "time_s": t, "status": "stopped", "metrics": result.metrics})
            break  # terminate physics; no nominal fallback or fictitious hold guarantee
        data.ctrl[:] = nominal if result is None else result.action
        for _ in range(round(DT / model.opt.timestep)):
            data.qfrc_applied[:6] = data.qfrc_bias[:6]
            mujoco.mj_step(model, data)
            # Contact arrays may correspond to the state before integration;
            # refresh at the resulting pose, including the last tick before a stop.
            mujoco.mj_forward(model, data)
            physics_steps += 1
            joint_limit_samples += int(np.any(data.qpos[:6] < adapter.bounds[:, 0] - 1e-6) or
                                       np.any(data.qpos[:6] > adapter.bounds[:, 1] + 1e-6))
            maximum_actual_velocity = max(maximum_actual_velocity, float(np.max(np.abs(data.qvel[:5]))))
            hits = contacts(model, data)
            contact_checks += 1
            if hits:
                hit_ticks += 1
                if first_hit is None:
                    first_hit = {"time_s": t, "pairs": hits}
        row = {"step": step, "time_s": t, "q": data.qpos[:6].tolist(),
               "goal_error_rad": float(np.max(np.abs(goal[:5] - data.qpos[:5]))),
               "status": result.status if result else "unfiltered", "metrics": result.metrics if result else None}
        rows.append(row)
        if not np.isfinite(data.qpos).all():
            stop_reason = "nonfinite_physics"
            break
        stable = stable + 1 if row["goal_error_rad"] < .015 else 0
        if renderer is not None and step % 2 == 0:
            mujoco.mj_forward(model, data)
            renderer.update_scene(data, camera=camera)
            if enabled:
                draw_guards(renderer, world_ellipsoids(model, data, adapter.ellipsoids, joint_names=JOINT_NAMES))
            writer.append_data(renderer.render())
        if stable >= 25:
            reached = True
            break
    if writer is not None:
        writer.close()
        renderer.close()
    # Initialization includes geometry/plane fitting; exclude first filter call
    # from steady-state percentiles and report it separately.
    latency = [r["metrics"]["adapter_latency_ms"] for r in rows if r.get("metrics") and "adapter_latency_ms" in r["metrics"]]
    recertified = [r for r in rows if r.get("metrics") and r["metrics"].get("recertified_guards")]
    summary = {"shield_enabled": enabled, "scenario": scenario,
               "hazard_source": "simulator_ground_truth", "policy": "fixed joint target proportional policy; no VLA",
               "control_steps": len(rows), "contact_samples": hit_ticks,
               "contact_sampling": "refreshed 2ms physics states plus 20ms boundaries; samples are not independent incidents",
               "contact_check_count": contact_checks, "physics_steps": physics_steps,
               "elapsed_sim_s": float(data.time - initial_sim_time),
               "first_contact": first_hit, "goal_reached": reached,
               "safe_completion": reached and hit_ticks == 0 and joint_limit_samples == 0 and stop_reason is None,
               "joint_limit_samples": joint_limit_samples,
               "maximum_actual_arm_velocity_rad_s": maximum_actual_velocity,
               "stop_reason": stop_reason, "modified_steps": sum(r["status"] == "modified" for r in rows),
               "initial_filter_ms": latency[0] if latency else None,
               "steady_filter_ms": dict(zip(("p50", "p95", "p99"), np.percentile(latency[1:], [50, 95, 99]).tolist())) if len(latency) > 2 else None,
               "steady_latency_samples": max(0, len(latency) - 1),
               "maximum_filter_ms": max(latency) if latency else None,
               "control_deadline_overruns": sum(ms > DT * 1000 for ms in latency),
               "recertification_steps": len(recertified),
               "recertification_max_ms": max((r["metrics"]["recertification_ms"] for r in recertified), default=0.),
               "final_goal_error_rad": float(np.max(np.abs(goal[:5] - data.qpos[:5])))}
    (output / f"{scenario}-{'on' if enabled else 'off'}.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--max-seconds", type=float, default=18.)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.max_seconds <= 60:
        parser.error("max-seconds must be between 1 and 60")
    output = args.output or Path(__file__).parent / "output" / f"paired-{uuid.uuid4().hex}"
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    model, start, goal, center, fixture = build_fixture(output)
    adapter = SimulationSafetyAdapter(model)
    coverage = audit_geometry_coverage(model, adapter.ellipsoids)
    if not coverage["passed"]:
        raise RuntimeError("Geometry coverage failed")
    summaries = [run_trial(model, start, goal, center, output, enabled=enabled, scenario=scenario,
                           render=args.render, max_seconds=args.max_seconds)
                 for scenario in ("static", "withdrawal") for enabled in (False, True)]
    accepted = all(s["contact_samples"] > 0 for s in summaries if not s["shield_enabled"]) and all(s["contact_samples"] == 0 for s in summaries if s["shield_enabled"])
    withdrawal_passed = any(s["scenario"] == "withdrawal" and s["shield_enabled"] and s["safe_completion"] for s in summaries)
    report = {"acceptance": {"paired_collision_reduction": accepted,
                              "withdrawal_safe_completion": withdrawal_passed,
                              "scope": "two deterministic fixtures; stopped or incomplete trials remain task failures"},
              "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              "scene": str(fixture), "physics_dt_s": model.opt.timestep, "control_dt_s": DT,
              "modelled_jaw_range_rad": adapter.geometry_metadata["jaw_range_rad"],
              "geometry": adapter.geometry_metadata, "coverage": coverage,
              "trials": summaries, "elapsed_wall_s": time.perf_counter() - started,
              "limitations": ["No VLA inference or hardware", "Oracle obstacle pose in paired trials",
                              "Upper arm, shoulder, base and carried objects excluded from CBF",
                              "Sampled position servo is not continuous-time safe control",
                              "Stopping ends simulation; does not prove a physical braking manoeuvre"]}
    (output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"output": str(output), "accepted": accepted and withdrawal_passed, "trials": summaries}, indent=2))
    return 0 if accepted and withdrawal_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
