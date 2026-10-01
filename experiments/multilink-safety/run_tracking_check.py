#!/usr/bin/env python3
"""Actual MuJoCo offscreen RGB-D tracking check, separate from robot control.

Uses a caller-designated simulator bbox and a textured translating box.
This verifies registered-depth/LK integration, not VLM/detection, unseen
geometry enclosure, arbitrary hazard rotation, or the safety filter itself.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
from pathlib import Path
import time
import uuid

os.environ.setdefault("MUJOCO_GL", "egl")

import cv2
import mujoco
import numpy as np

from hazard_tracking import CameraModel, SparseHazardTracker, TrackingFailure


WIDTH, HEIGHT = 320, 240
CONTROL_PERIOD_S = 0.02
VELOCITY_M_S = 0.03
MAX_ERROR_M = 0.002

FIXTURE_XML = """
<mujoco model="registered_rgbd_tracking_fixture">
  <option timestep="0.002" gravity="0 0 0"/>
  <visual><global offwidth="320" offheight="240"/><quality shadowsize="1024"/></visual>
  <asset>
    <texture name="hazard_checker" type="2d" builtin="checker" width="256" height="256"
             rgb1="0.85 0.18 0.08" rgb2="0.05 0.30 0.85"/>
    <material name="hazard_material" texture="hazard_checker" texrepeat="4 4"
              texuniform="true" reflectance="0" shininess="0"/>
  </asset>
  <worldbody>
    <light pos="0 0 1.5" dir="0 0 -1" diffuse="0.8 0.8 0.8" ambient="0.4 0.4 0.4"/>
    <geom name="floor" type="plane" size="1 1 .01" rgba=".18 .18 .18 1"/>
    <camera name="external" pos="0 0 .6" quat="1 0 0 0" fovy="45"/>
    <body name="hazard" mocap="true" pos="-.025 .012 .08">
      <geom name="hazard_box" type="box" size=".035 .030 .015" material="hazard_material"/>
    </body>
  </worldbody>
</mujoco>
"""


def camera_model(model, data):
    camera_id = model.camera("external").id
    focal = HEIGHT / (2 * np.tan(np.deg2rad(model.cam_fovy[camera_id]) / 2))
    transform = np.eye(4)
    transform[:3, :3] = data.cam_xmat[camera_id].reshape(3, 3) @ np.diag([1, -1, -1])
    transform[:3, 3] = data.cam_xpos[camera_id]
    return CameraModel(focal, focal, WIDTH / 2, HEIGHT / 2, transform)


def designated_bbox(model, data, camera):
    """Oracle bbox designated only at reset, not an online pose observation."""
    geom_id = model.geom("hazard_box").id
    corners = np.asarray(list(itertools.product((-1., 1.), repeat=3))) * model.geom_size[geom_id]
    corners = corners @ data.geom_xmat[geom_id].reshape(3, 3).T + data.geom_xpos[geom_id]
    projected = np.asarray([camera.project(corner)[0] for corner in corners])
    lower = np.floor(projected.min(axis=0)).astype(int)
    upper = np.ceil(projected.max(axis=0)).astype(int) + 1
    return [int(lower[0]), int(lower[1]), int(upper[0]), int(upper[1])]


def render_rgbd(renderer, data):
    renderer.disable_depth_rendering()
    renderer.update_scene(data, camera="external")
    rgb = renderer.render().copy()
    renderer.enable_depth_rendering()
    renderer.update_scene(data, camera="external")
    depth = renderer.render().copy()
    renderer.disable_depth_rendering()
    return rgb, depth


def save_png(path, rgb, bbox=None):
    image = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    if bbox is not None:
        x0, y0, x1, y1 = bbox
        cv2.rectangle(image, (x0, y0), (x1 - 1, y1 - 1), (0, 255, 0), 1)
    if not cv2.imwrite(str(path), image):
        raise RuntimeError("failed to save rendered PNG")


def check(output, steps=100):
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    report = {
        "status": "failed", "source": "https://arxiv.org/html/2609.40007v1#S3.SS3",
        "fixture": "MuJoCo textured mocap box, fixed overhead camera, real offscreen RGB-D",
        "initialization": "simulator-projected reset bbox explicitly designated by caller; no detector or VLM",
        "camera_convention": "world_from_camera rotation = cam_xmat @ diag(1,-1,-1); camera x-right/y-down/z-forward",
        "depth_units": "MuJoCo Renderer metric axial camera depth, metres",
        "fit_method": "conservative_pca_visible_points",
        "scope_limit": "Visible point enclosure is not paper MVEE or complete hidden object geometry. Translation at constant height only; no robot or filter acceptance.",
        "acceptance": {"maximum_measurement_displacement_error_m": MAX_ERROR_M,
                       "fixed_shape": True, "disappearance_must_stop": True, "missing_depth_must_stop": True},
        "mujoco_version": mujoco.__version__, "opencv_version": cv2.__version__,
        "control_period_s": CONTROL_PERIOD_S, "translation_velocity_m_s": VELOCITY_M_S,
        "control_steps": steps, "tracking_every_steps": 5, "samples": [],
    }
    try:
        model = mujoco.MjModel.from_xml_string(FIXTURE_XML)
        data = mujoco.MjData(model)
        mujoco.mj_forward(model, data)
        camera = camera_model(model, data)
        bbox = designated_bbox(model, data, camera)
        initial_pose = data.body("hazard").xpos.copy()
        with mujoco.Renderer(model, height=HEIGHT, width=WIDTH) as renderer:
            initial_rgb, initial_depth = render_rgbd(renderer, data)
            save_png(output / "initial.png", initial_rgb, bbox)
            tracker = SparseHazardTracker(camera)
            initial = tracker.initialize(initial_rgb, initial_depth, bbox)
            report["initial_bbox_px"] = bbox
            report["initial_estimated_center_m"] = initial.center.tolist()
            report["initial_true_box_center_m"] = initial_pose.tolist()
            report["initial_visible_center_offset_m"] = (initial.center - initial_pose).tolist()
            report["initial_axes_m"] = initial.axes.tolist()
            pixel, _ = camera.project(initial_pose + [0, 0, model.geom_size[model.geom("hazard_box").id, 2]])
            depth_value = float(initial_depth[int(round(pixel[1])), int(round(pixel[0]))])
            point = camera.unproject(pixel[None], np.array([depth_value]))[0]
            top_z = float(initial_pose[2] + model.geom_size[model.geom("hazard_box").id, 2])
            report["depth_registration_top_height_error_m"] = abs(float(point[2]) - top_z)
            errors, held_errors, all_errors, measured_times = [], [], [], []
            for step in range(1, steps + 1):
                data.mocap_pos[0] = initial_pose + [VELOCITY_M_S * step * CONTROL_PERIOD_S, 0, 0]
                for _ in range(10):
                    mujoco.mj_step(model, data)
                rgb, depth = render_rgbd(renderer, data)
                tick = time.perf_counter()
                estimate = tracker.update(rgb, depth, step)
                tracker.require_safe(step)
                truth_displacement = data.body("hazard").xpos - initial_pose
                estimate_displacement = estimate.center - initial.center
                error = float(np.linalg.norm(estimate_displacement - truth_displacement))
                all_errors.append(error)
                if estimate.status == "tracked":
                    measured_times.append((time.perf_counter() - tick) * 1000)
                    errors.append(error)
                    report["samples"].append({"step": step,
                                              "truth_displacement_m": truth_displacement.tolist(),
                                              "estimate_displacement_m": estimate_displacement.tolist(),
                                              "displacement_error_m": error})
                    if not (np.array_equal(estimate.axes, initial.axes)
                            and np.array_equal(estimate.rotation, initial.rotation)):
                        raise RuntimeError("tracker changed fixed reset shape")
                else:
                    held_errors.append(error)
                if step == steps:
                    save_png(output / "translated.png", rgb)
            report["tracking_measurements"] = len(errors)
            report["max_center_displacement_error_m"] = max(errors)
            report["mean_center_displacement_error_m"] = float(np.mean(errors))
            report["max_center_error_all_control_steps_m"] = max(all_errors)
            report["max_center_error_held_steps_m"] = max(held_errors)
            report["error_scope"] = "Acceptance bounds measurement displacement error. Held-step errors are reported separately and need motion/error margins before robot integration."
            report["tracking_cpu_measurement_p50_ms"] = float(np.percentile(measured_times, 50))
            report["tracking_cpu_measurement_p99_ms"] = float(np.percentile(measured_times, 99))
            report["fixed_shape_pass"] = True

            # Negative checks both start with an actual rendered reset frame.
            missing_depth = SparseHazardTracker(camera)
            missing_depth.initialize(initial_rgb, initial_depth, bbox)
            try:
                missing_depth.update(initial_rgb, np.zeros_like(initial_depth), 5)
            except TrackingFailure as error:
                report["missing_depth_stop"] = {"pass": True, "reason": str(error),
                                                "latched_status": missing_depth.estimate.status}
                try:
                    missing_depth.require_safe(5)
                except TrackingFailure:
                    report["missing_depth_stop"]["caller_authorization_rejected"] = True
            else:
                report["missing_depth_stop"] = {"pass": False}
            disappeared = SparseHazardTracker(camera)
            disappeared.initialize(initial_rgb, initial_depth, bbox)
            data.mocap_pos[0] = [2, 2, .08]
            mujoco.mj_forward(model, data)
            vanished_rgb, vanished_depth = render_rgbd(renderer, data)
            save_png(output / "disappeared.png", vanished_rgb)
            try:
                disappeared.update(vanished_rgb, vanished_depth, 5)
            except TrackingFailure as error:
                report["disappearance_stop"] = {"pass": True, "reason": str(error),
                                                "latched_status": disappeared.estimate.status}
                try:
                    disappeared.require_safe(5)
                except TrackingFailure:
                    report["disappearance_stop"]["caller_authorization_rejected"] = True
            else:
                report["disappearance_stop"] = {"pass": False}
            report["status"] = "passed" if (
                report["max_center_displacement_error_m"] <= MAX_ERROR_M
                and report["depth_registration_top_height_error_m"] < 1e-5
                and report["missing_depth_stop"].get("caller_authorization_rejected", False)
                and report["disappearance_stop"].get("caller_authorization_rejected", False)
                and len(errors) == steps // 5) else "failed"
    except Exception as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    report["wall_s"] = time.perf_counter() - started
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parent / "output" / ("tracking-" + uuid.uuid4().hex))
    parser.add_argument("--steps", type=int, default=100)
    args = parser.parse_args()
    if args.steps < 10 or args.steps > 500 or args.steps % 5:
        parser.error("steps must be a multiple of five in [10,500]")
    report = check(args.output, args.steps)
    print(json.dumps({"status": report["status"], "report": str((args.output / "report.json").resolve()),
                      "max_error_m": report.get("max_center_displacement_error_m"),
                      "error": report.get("error")}, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
