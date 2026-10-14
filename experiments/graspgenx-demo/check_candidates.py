"""Static endpoint and jaw-chord diagnostics using the existing safety kernel."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

from compare import validate
from infer import digest

# Numerical reproduction only. These are not physical grasp pose tolerances.
NUMERIC_POSITION_M = 1e-6
NUMERIC_ROTATION_RAD = 1e-5


def check(root, source):
    descriptor = json.loads((source / "descriptor.json").read_text())
    model_path = root / "workspaces/so101_ws/src/so101_mujoco/models/so101.xml"
    if digest(model_path) != descriptor["source_model_sha256"]:
        raise ValueError("Model changed since inference")
    audit_path = source / "all-candidates/audit.json"
    audit = json.loads(audit_path.read_text())
    if audit["source_pool_sha256"] != digest(source / "pool.npz"):
        raise ValueError("Saved candidate pool changed since pose audit")
    fits = json.loads((source / "all-candidates/pose-inspection.json").read_text())["candidates"]
    pool = np.load(source / "pool.npz", allow_pickle=False)
    poses, scores = validate(pool["poses"], pool["scores"], pool["origins"])
    if len(fits) != len(poses) or len(poses) != audit["inspected_candidates"]:
        raise ValueError("Incomplete pose audit")
    geometry = np.load(source / "geometry.npz", allow_pickle=False)
    out = source / "collision-diagnostic"
    out.mkdir(exist_ok=False)
    sys.path.insert(0, str(root / "experiments/colab-twin"))
    from grasp_episode import build_contact_scene
    from conservative_collision import ConservativeCollisionChecker
    from configuration_sweep import validate_configuration_path
    from support_native import library_metadata
    report = {"status": "started", "candidates": [], "physics_steps": 0,
              "motion_accepted": False, "model_descriptor_validated": False,
              "target_solid_checked": False, "path_planned": False,
              "numerical_reproduction_tolerances": {"position_m": NUMERIC_POSITION_M,
                                                    "rotation_rad": NUMERIC_ROTATION_RAD},
              "boundary": "Static arm/world guard and full jaw chord only; target removed by original planning rig. No physical pose tolerance, trajectory, payload or contact certificate"}
    start = time.monotonic()
    try:
        _, rig, _ = build_contact_scene(model_path, out / "scene", noslip_iterations=10)
        checker = ConservativeCollisionChecker(rig, gripper=.5, margin_m=.001)
        data = mujoco.MjData(rig)
        body = rig.body("gripper").id
        report["checked_pair_count"] = len(checker.pairs)
        report["pair_policy"] = {"pairs": [[checker._names[a], checker._names[b]] for a,b in checker.pairs],
                                 "excluded_pairs": checker.excluded_pairs}
        for index, fit in enumerate(fits):
            if fit["candidate"] != index:
                raise ValueError("Pose audit order differs from pool")
            q5 = np.asarray(fit["fitted_q5_rad"], dtype=float)
            if q5.shape != (5,) or not np.isfinite(q5).all():
                raise ValueError("Malformed fitted joint pose")
            data.qpos[:5], data.qpos[5] = q5, .5
            mujoco.mj_forward(rig, data)
            actual_rotation = data.xmat[body].reshape(3,3) @ geometry["body_from_grasp"]
            position = float(np.linalg.norm(data.xpos[body]-poses[index,:3,3]))
            angle = float(Rotation.from_matrix(poses[index,:3,:3].T @ actual_rotation).magnitude())
            reproduced = position <= NUMERIC_POSITION_M and angle <= NUMERIC_ROTATION_RAD
            endpoint = checker.evaluate(np.r_[q5,.5], require_fixed_gripper=False)
            row = {"candidate": index, "origin": str(pool["origins"][index]),
                   "model_score": float(scores[index]), "position_error_m": position,
                   "rotation_error_rad": angle, "numerically_reproduced": reproduced,
                   "open_endpoint": endpoint, "closure_sweep": None, "motion_accepted": False}
            if reproduced and endpoint["valid"]:
                last_failure = []
                def valid(q6):
                    result = checker.evaluate(q6, require_fixed_gripper=False)
                    if not result["valid"]:
                        last_failure.append(result)
                    return result["valid"]
                row["closure_sweep"] = validate_configuration_path(
                    np.r_[q5,.5], np.r_[q5,.015], valid,
                    arm_resolution_rad=.005, jaw_resolution_rad=.002, max_samples=4096)
                if last_failure:
                    row["closure_failure"] = last_failure[-1]
            report["candidates"].append(row)
        eligible = [r for r in report["candidates"] if r["closure_sweep"] and r["closure_sweep"]["valid"]]
        eligible.sort(key=lambda r: -r["model_score"])
        report.update(status="static_guards_completed", candidates_total=len(poses),
                      numerically_reproduced=sum(r["numerically_reproduced"] for r in report["candidates"]),
                      open_endpoint_certified=sum(r["open_endpoint"]["valid"] for r in report["candidates"]),
                      closure_sweeps_run=sum(r["closure_sweep"] is not None for r in report["candidates"]),
                      closure_sweeps_certified=len(eligible),
                      diagnostic_ranked_candidates=[r["candidate"] for r in eligible],
                      endpoint_reasons=dict(Counter(r["open_endpoint"]["reason"] for r in report["candidates"])),
                      native_build=library_metadata())
        lines = ["# Static SO101 candidate guards", "",
                 "No motion accepted. Descriptor remains provisional; target contact and paths are not checked.", "",
                 f"All pool candidates: {len(poses)}; original pairs: {len(checker.pairs)}; margin: 1 mm.",
                 f"Numerical pose reproduction: {report['numerically_reproduced']}; open endpoint certificates: {report['open_endpoint_certified']}.",
                 f"Full jaw chords checked: {report['closure_sweeps_run']}; certified: {len(eligible)}.", "",
                 "Numerical tolerances are 1e-6 m / 1e-5 rad, not physical grasp acceptance thresholds.",
                 "Jaw chord uses original 0.002 rad spacing and both endpoints (244 states when complete).",
                 "Uncertified clearance is a conservative rejection, not proof of actual collision.", "",
                 "| Diagnostic rank | Candidate | Origin | Score | Jaw states |",
                 "| ---: | ---: | --- | ---: | ---: |"]
        for rank, row in enumerate(eligible,1):
            lines.append(f"| {rank} | {row['candidate']} | {row['origin']} | {row['model_score']:.6f} | {row['closure_sweep']['checked_states']} |")
        (out / "REPORT.md").write_text("\n".join(lines)+"\n")
        print(json.dumps({k:report[k] for k in ("status","candidates_total","checked_pair_count",
             "numerically_reproduced","open_endpoint_certified","closure_sweeps_run","closure_sweeps_certified")}))
    except Exception as error:
        report.update(status="failed", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        report["elapsed_s"] = time.monotonic()-start
        report["source_hashes"] = {name:digest(root / "experiments/colab-twin" / name) for name in
            ("grasp_episode.py","grasp_workcell.py","collision_scene.py","conservative_collision.py",
             "configuration_sweep.py","support_native.py","support_kernel.cpp")}
        report["adapter_sha256"] = digest(Path(__file__))
        report["input_hashes"] = {name:digest(source / name) for name in
            ("pool.npz","descriptor.json","geometry.npz","all-candidates/audit.json","all-candidates/pose-inspection.json")}
        (out / "report.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True,help="Completed comparison with all-candidate pose audit")
    args = parser.parse_args()
    check(args.root.resolve(),args.output.resolve())
