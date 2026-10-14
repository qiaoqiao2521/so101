"""Inspect full-pose FK residuals without executing or accepting robot actions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import mujoco
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation


def inspect(root: Path, out: Path, seed: int) -> None:
    source = root / "workspaces/so101_ws/src/so101_mujoco/models/so101.xml"
    model = mujoco.MjModel.from_xml_path(str(source))
    data = mujoco.MjData(model)
    base = model.body("gripper").id
    geometry = np.load(out / "geometry.npz", allow_pickle=False)
    candidates = np.load(out / "candidates.npz", allow_pickle=False)
    lower, upper = model.jnt_range[:5].T.copy()
    for act in range(model.nu):
        joint = int(model.actuator_trnid[act, 0])
        if 0 <= joint < 5 and model.actuator_ctrllimited[act]:
            lower[joint] = max(lower[joint], model.actuator_ctrlrange[act, 0])
            upper[joint] = min(upper[joint], model.actuator_ctrlrange[act, 1])
    random = np.random.default_rng(seed)
    starts = [np.zeros(5), *random.uniform(lower, upper, (5, 5))]
    results = []
    start = time.monotonic()
    for index, (pose, score) in enumerate(zip(candidates["poses"], candidates["scores"])):
        target_rotation = pose[:3, :3] @ geometry["body_from_grasp"].T
        def residual(q):
            data.qpos[:5] = q
            data.qpos[5] = .5
            mujoco.mj_forward(model, data)
            position = data.xpos[base] - pose[:3, 3]
            angle = Rotation.from_matrix(target_rotation.T @ data.xmat[base].reshape(3, 3)).as_rotvec()
            return np.r_[position, angle * .1]
        best = None
        for guess in starts:
            fit = least_squares(residual, np.clip(guess, lower+1e-7, upper-1e-7),
                                bounds=(lower+1e-7, upper-1e-7), max_nfev=120)
            if best is None or np.linalg.norm(fit.fun) < np.linalg.norm(best.fun):
                best = fit
        error = residual(best.x)
        results.append({"candidate": index, "model_score": float(score),
                        "translation_error_mm": float(np.linalg.norm(error[:3])*1000),
                        "rotation_error_deg": float(np.linalg.norm(error[3:])/.1*180/np.pi),
                        "fitted_q5_rad": best.x.tolist(),
                        "motion_accepted": False, "collision_checked": False})
    report = {"kind": "full_pose_static_fit_diagnostic", "candidates": results,
              "elapsed_s": time.monotonic()-start, "physics_steps": 0,
              "grasp_pose_tolerances_frozen": False, "complete_pose_certified": False,
              "boundary": "Local multi-start residuals only; not proof of global infeasibility. Provisional descriptor, no collision/path/physical acceptance"}
    (out / "pose-inspection.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({"inspected": len(results), "complete_pose_certified": False,
                      "min_translation_error_mm": min(x["translation_error_mm"] for x in results),
                      "min_rotation_error_deg": min(x["rotation_error_deg"] for x in results)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    inspect(args.root.resolve(), args.output.resolve(), args.seed)
