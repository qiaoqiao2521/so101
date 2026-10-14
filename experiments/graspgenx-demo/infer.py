"""Use the official frozen GraspGen-X sampler; never command a robot."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np

MODEL_REVISION = "7c834043c11a11417e31d6d5ea9355801e40a2c1"
UPSTREAM_REVISION = "b9429097728cb1c430dd78b92edf17ba318aad03"
WEIGHTS = {
    "release/gen/epoch_736.pth": "8b55f31cdb8340a573b4df27b027c15cff326bd6debcb389bf631d2aaab7ac44",
    "release/dis/epoch_1056.pth": "cbf3f3bdb2e4c03fca8486ed24de0e6a8a859e6bd22bce2f1434a610335abd3e",
    "release/gen/config.yaml": "16aedbdc23441a1db818261b865f55bd71451d6224fc514615e0d1ab744b7dcb",
    "release/dis/config.yaml": "43cf8ea0ade67d938040bde0df318b3f4c9c19e4f88d97052dc175df2c28c8e7",
}


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def run(args) -> None:
    out, models = args.output.resolve(), args.models.resolve()
    receipt = {"status": "started", "model_revision": MODEL_REVISION,
               "upstream_revision": UPSTREAM_REVISION, "seed": args.seed,
               "requested_candidates": args.candidates,
               "descriptor_validated": False, "physical_grasp_verified": False,
               "physics_steps": 0, "hardware_access": False, "training_steps": 0}
    start = time.monotonic()
    try:
        hashes = {name: digest(models / name) for name in WEIGHTS}
        if hashes != WEIGHTS:
            raise ValueError("Official checkpoint/config SHA-256 mismatch")
        receipt["verified_files"] = hashes
        os.environ["GRASPGENX_CHECKPOINT_DIR"] = str(models)
        # Official sweep-only interface needs no named gripper assets.
        os.environ["GRASPGENX_GRIPPER_CFG_DIR"] = str(out)
        import torch
        import trimesh
        from graspgenx.grasp_server import GraspGenXSampler
        from graspgenx.utils.checkpoint_io import load_model_cfg

        if not torch.cuda.is_available():
            raise RuntimeError("Official sampler requires CUDA; CPU fallback is not implemented")
        np.random.seed(args.seed)
        torch.manual_seed(args.seed)
        torch.cuda.manual_seed_all(args.seed)
        torch.set_num_threads(2)
        geo = np.load(out / "geometry.npz", allow_pickle=False)
        mesh = trimesh.creation.box(extents=geo["target_size"])
        mesh.apply_translation(geo["target_center"])
        points, _ = trimesh.sample.sample_surface(mesh, 3500, seed=args.seed)
        # The official sampler checks exact ndarray type, not ndarray subclasses.
        points = np.ascontiguousarray(points, dtype=np.float32)
        np.save(out / "object_points.npy", points)
        mesh.export(out / "object.ply")
        descriptor = json.loads((out / "descriptor.json").read_text())
        cfg = load_model_cfg(models / "release/gen", models / "release/dis",
                             "epoch_736.pth", "epoch_1056.pth")
        torch.cuda.reset_peak_memory_stats()
        loaded = time.monotonic()
        sampler = GraspGenXSampler.from_sweep_volume(cfg, descriptor["params"])
        torch.cuda.synchronize()
        receipt["model_load_s"] = time.monotonic() - loaded
        predicted = time.monotonic()
        poses, scores = GraspGenXSampler.run_inference(
            points, sampler, num_grasps=args.candidates, topk_num_grasps=args.candidates,
            grasp_threshold=-1., min_grasps=1, max_tries=1)
        torch.cuda.synchronize()
        receipt["inference_s"] = time.monotonic() - predicted
        if not isinstance(poses, torch.Tensor) or poses.ndim != 3 or poses.shape[1:] != (4, 4):
            raise RuntimeError("Official sampler returned no valid pose array")
        poses, scores = poses.cpu().numpy(), scores.cpu().numpy()
        if len(poses) == 0 or not np.isfinite(poses).all() or not np.isfinite(scores).all():
            raise ValueError("Empty or nonfinite candidate output")
        rotations = poses[:, :3, :3]
        if not np.allclose(rotations.transpose(0, 2, 1) @ rotations, np.eye(3), atol=1e-4):
            raise ValueError("Candidate rotations are not orthonormal")
        if not np.allclose(np.linalg.det(rotations), 1., atol=1e-4):
            raise ValueError("Candidate rotations are not proper rotations")
        np.savez_compressed(out / "candidates.npz", poses=poses, scores=scores)
        receipt.update(status="candidates_generated", candidates=len(poses),
                       gpu=torch.cuda.get_device_name(0), torch_version=torch.__version__,
                       peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                       peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,
                       score_min=float(scores.min()), score_max=float(scores.max()),
                       planner="diffusion + official discriminator; no OBB")
    except Exception as error:
        receipt.update(status="failed", error_type=type(error).__name__, error=str(error))
        if "torch" in locals() and torch.cuda.is_available():
            receipt.update(peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                           peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
        raise
    finally:
        receipt["elapsed_s"] = time.monotonic() - start
        (out / "report.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--candidates", type=int, default=16)
    args = parser.parse_args()
    if not 1 <= args.candidates <= 256:
        parser.error("candidates must be 1..256")
    run(args)
