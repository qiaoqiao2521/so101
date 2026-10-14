"""Compare candidate pools from one official GraspMoE run; no execution."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time

import numpy as np

from infer import MODEL_REVISION, UPSTREAM_REVISION, WEIGHTS, digest
from inspect_candidates import inspect
from render_preview import render


def validate(poses, scores, tags):
    poses, scores = np.asarray(poses), np.asarray(scores)
    if poses.shape != (len(scores), 4, 4) or scores.ndim != 1 or len(tags) != len(scores):
        raise ValueError("Candidate poses, scores and origins must align")
    if not np.isfinite(poses).all() or not np.isfinite(scores).all():
        raise ValueError("Nonfinite candidate output")
    if not np.allclose(poses[:, 3], [0, 0, 0, 1], atol=1e-5):
        raise ValueError("Invalid homogeneous pose row")
    rotations = poses[:, :3, :3]
    if (not np.allclose(rotations.transpose(0, 2, 1) @ rotations, np.eye(3), atol=1e-4)
            or not np.allclose(np.linalg.det(rotations), 1, atol=1e-4)):
        raise ValueError("Invalid candidate rotation")
    return poses, scores


def choose(scores, indices, limit):
    """Stable descending score; ties retain original pool order."""
    indices = np.asarray(indices, dtype=int)
    return indices[np.argsort(-scores[indices], kind="stable")[:limit]]


def fixed_pose(root, geometry):
    # Import the existing solver, whose planner imports are lazy. No runner call.
    import mujoco
    sys.path.insert(0, str(root / "experiments/colab-twin"))
    from grasp_episode import solve_pinch_ik
    model = mujoco.MjModel.from_xml_path(str(
        root / "workspaces/so101_ws/src/so101_mujoco/models/so101.xml"))
    start = solve_pinch_ik(model, np.array([.24, .14, .06]))
    approach = solve_pinch_ik(model, np.array([.24, -.13, .06]), start)
    down = solve_pinch_ik(model, np.array([.24, -.13, .019]), approach)
    data = mujoco.MjData(model)
    data.qpos[:5], data.qpos[5] = down, .5
    mujoco.mj_forward(model, data)
    body = model.body("gripper").id
    pose = np.eye(4)
    pose[:3, :3] = data.xmat[body].reshape(3, 3) @ geometry["body_from_grasp"]
    pose[:3, 3] = data.xpos[body]
    return pose[None].astype(np.float32), down


def run(args):
    out, root, models = args.output.resolve(), args.root.resolve(), args.models.resolve()
    obb_settings = ({"z_offsets_cm": (-2, 0), "obb_density": "dense-topandside"}
                    if args.profile == "cli" else
                    {"z_offsets_cm": (-8, -6, -4, -2, -1, 0), "obb_density": "sparse"})
    receipt = {"status": "started", "seed": args.seed, "topk": args.candidates,
               "obb_profile": args.profile, "obb_settings": {"num_yaws": 36, **obb_settings},
               "upstream_revision": UPSTREAM_REVISION, "model_revision": MODEL_REVISION,
               "descriptor_validated": False, "physics_steps": 0,
               "hardware_access": False, "training_steps": 0,
               "complete_pose_certified": False, "physical_grasp_verified": False,
               "design": "Shared-pool ablation, not four independent runs or equal generation budgets"}
    started = time.monotonic()
    try:
        hashes = {name: digest(models / name) for name in WEIGHTS}
        if hashes != WEIGHTS:
            raise ValueError("Official checkpoint/config SHA-256 mismatch")
        receipt["verified_files"] = hashes
        os.environ["GRASPGENX_CHECKPOINT_DIR"] = str(models)
        os.environ["GRASPGENX_GRIPPER_CFG_DIR"] = str(out)
        import torch
        import trimesh
        from graspgenx.grasp_server import GraspGenXSampler
        from graspgenx.samplers import run_graspmoe
        from graspgenx.samplers.graspmoe import _score_grasps_with_discriminator
        from graspgenx.utils.checkpoint_io import load_model_cfg
        from graspgenx.utils.point_cloud import point_cloud_outlier_removal
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA unavailable; no fallback")
        np.random.seed(args.seed)
        torch.manual_seed(args.seed)
        torch.cuda.manual_seed_all(args.seed)
        torch.set_num_threads(2)
        geo = np.load(out / "geometry.npz", allow_pickle=False)
        descriptor = json.loads((out / "descriptor.json").read_text())
        if descriptor.get("descriptor_validated"):
            validation = out / "region-validation.json"
            if digest(validation) != descriptor.get("region_validation_sha256"):
                raise ValueError("Reviewed region binding changed")
            receipt["descriptor_validated"] = True
            receipt["descriptor_validation_scope"] = descriptor["validation_scope"]
        mesh = trimesh.creation.box(extents=geo["target_size"])
        mesh.apply_translation(geo["target_center"])
        points, _ = trimesh.sample.sample_surface(mesh, 3500, seed=args.seed)
        points = np.ascontiguousarray(points, dtype=np.float32)
        np.save(out / "object_points.npy", points)
        receipt["input_sha256"] = digest(out / "object_points.npy")
        receipt["descriptor_sha256"] = digest(out / "descriptor.json")
        receipt["input_kind"] = "full box surface geometry upper bound, not camera observation"
        cfg = load_model_cfg(models / "release/gen", models / "release/dis",
                             "epoch_736.pth", "epoch_1056.pth")
        params = descriptor["params"]
        torch.cuda.reset_peak_memory_stats()
        t0 = time.monotonic()
        sampler = GraspGenXSampler.from_sweep_volume(cfg, params)
        torch.cuda.synchronize()
        receipt["model_load_s"] = time.monotonic() - t0
        # CLI and public planner API have different OBB defaults. Keep the union to
        # preserve its branch origin before applying the shared downstream cap.
        t0 = time.monotonic()
        result = run_graspmoe(points, sampler, num_grasps=args.candidates,
                              topk_num_grasps=-1, num_yaws=36, **obb_settings)
        torch.cuda.synchronize()
        receipt["graspmoe_inference_s"] = time.monotonic() - t0
        poses = np.concatenate([result["grasps_diff"], result["grasps_obb"]])
        scores = np.concatenate([result["scores_diff"], result["scores_obb"]])
        tags = np.array(["diff"] * len(result["scores_diff"]) +
                        ["obb"] * len(result["scores_obb"]))
        poses, scores = validate(poses, scores, tags)
        np.savez_compressed(out / "pool.npz", poses=poses, scores=scores, origins=tags)
        fixed, fixed_q = fixed_pose(root, geo)
        filtered, _ = point_cloud_outlier_removal(torch.from_numpy(points), threshold=.014)
        center = filtered.numpy().mean(axis=0)
        fixed_scores = _score_grasps_with_discriminator(
            fixed, (filtered-torch.from_numpy(center)).cuda(), center, sampler)
        validate(fixed, fixed_scores, ["fixed"])
        receipt["fixed_reference_q5_rad"] = fixed_q.tolist()
        receipt["raw_pool_counts"] = {"diff": int(np.sum(tags == "diff")),
                                       "obb": int(np.sum(tags == "obb")), "union": len(tags)}
        receipt["obb_skipped"] = bool(result["skipped_obb"])
        receipt["default_diffusion_retry"] = {"min_grasps": 40, "max_tries": 6,
                                             "num_grasps_per_pass": args.candidates}
        groups = {}
        for name, mask in [("fixed", None), ("diffusion", tags == "diff"),
                           ("obb", tags == "obb"), ("graspmoe", np.ones(len(tags), bool))]:
            folder = out / name
            folder.mkdir()
            shutil.copyfile(out / "geometry.npz", folder / "geometry.npz")
            if mask is None:
                selected = np.array([-1])
                group_poses, group_scores, origins = fixed, fixed_scores, np.array(["fixed"])
                available = 1
            else:
                available = int(mask.sum())
                selected = choose(scores, np.flatnonzero(mask), args.candidates)
                group_poses, group_scores, origins = poses[selected], scores[selected], tags[selected]
            np.savez_compressed(folder / "candidates.npz", poses=group_poses,
                                scores=group_scores, origins=origins, pool_indices=selected)
            group = {"raw_candidates": available, "inspected_candidates": len(selected),
                     "origins": origins.tolist(), "pool_indices": selected.tolist()}
            if len(selected):
                inspect(root, folder, args.seed)
                render(folder)
                fits = json.loads((folder / "pose-inspection.json").read_text())["candidates"]
                best = min(fits, key=lambda x: np.hypot(x["translation_error_mm"],
                    x["rotation_error_deg"]*np.pi/180*100))
                group["best_weighted_fit"] = {**best, "origin": str(origins[best["candidate"]])}
                group["highest_model_score_fit"] = fits[int(np.argmax(group_scores))]
            else:
                group["status"] = "empty_pool; not substituted"
            groups[name] = group
        receipt.update(status="static_comparison_completed", groups=groups,
                       gpu=torch.cuda.get_device_name(0), torch_version=torch.__version__,
                       peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                       peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
        lines = ["# Shared-pool static comparison", "",
                 "Tip-gap proxy and full object geometry. No collision, motion or contact acceptance.",
                 "One GraspMoE run; branch subsets share samples. Raw generation budgets differ.", "",
                 "| Group | Raw / inspected | Best-fit origin | Position mm | Rotation deg |",
                 "| --- | ---: | --- | ---: | ---: |"]
        for name, group in groups.items():
            best = group.get("best_weighted_fit")
            values = (f"{best['origin']} | {best['translation_error_mm']:.4f} | {best['rotation_error_deg']:.4f}"
                      if best else "none | — | —")
            lines.append(f"| {name} | {group['raw_candidates']} / {group['inspected_candidates']} | {values} |")
        lines += ["", "Position and rotation above belong to the same candidate, selected by the existing weighted residual.",
                  "No acceptance thresholds, grasp success rate, independent repeats or equal-compute comparison.",
                  "The fixed prior uses the original fixture coordinates; it is not perception-based generalization."]
        (out / "REPORT.md").write_text("\n".join(lines)+"\n")
        print(json.dumps({"status": receipt["status"], "raw_pool_counts": receipt["raw_pool_counts"]}))
    except Exception as error:
        receipt.update(status="failed", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        receipt["elapsed_s"] = time.monotonic()-started
        receipt["source_hashes"] = {p.name: digest(p) for p in Path(__file__).parent.iterdir()
                                    if p.suffix in (".py", ".sh")}
        (out / "comparison.json").write_text(json.dumps(receipt, indent=2, allow_nan=False)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--candidates", type=int, default=16)
    parser.add_argument("--profile", choices=("cli", "api"), default="cli")
    args = parser.parse_args()
    if not 1 <= args.candidates <= 256:
        parser.error("candidates must be 1..256")
    run(args)
