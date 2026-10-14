"""Inspect all saved proposals before score pruning; never accept motion."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

import numpy as np

from compare import validate
from infer import digest
from inspect_candidates import inspect
from render_preview import render


def audit(root, source, seed):
    record = json.loads((source / "comparison.json").read_text())
    if record["status"] != "static_comparison_completed" or record["seed"] != seed:
        raise ValueError("Completed source comparison and matching seed required")
    pool = np.load(source / "pool.npz", allow_pickle=False)
    poses, scores = validate(pool["poses"], pool["scores"], pool["origins"])
    if not len(poses):
        raise ValueError("Empty source pool")
    out = source / "all-candidates"
    out.mkdir(exist_ok=False)
    shutil.copyfile(source / "geometry.npz", out / "geometry.npz")
    np.savez_compressed(out / "candidates.npz", poses=poses, scores=scores,
                        origins=pool["origins"], pool_indices=np.arange(len(poses)))
    inspect(root, out, seed)
    fits = json.loads((out / "pose-inspection.json").read_text())["candidates"]
    summary = {}
    for branch in ("diff", "obb"):
        indices = np.flatnonzero(pool["origins"] == branch)
        if not len(indices):
            summary[branch] = {"count": 0, "status": "empty_pool"}
            continue
        best_index = min(indices, key=lambda i: np.hypot(fits[i]["translation_error_mm"],
                         fits[i]["rotation_error_deg"]*np.pi/180*100))
        ordering = indices[np.argsort(-scores[indices], kind="stable")]
        summary[branch] = {"count": len(indices), "best_weighted_fit": fits[best_index],
                           "score_rank_within_branch": int(np.flatnonzero(ordering == best_index)[0])+1}
    report = {"kind": "all_saved_proposals_pose_audit", "seed": seed,
              "source_pool_sha256": digest(source / "pool.npz"),
              "source_comparison_sha256": digest(source / "comparison.json"),
              "source_hashes": {name: digest(Path(__file__).parent / name) for name in
                                ("audit_pool.py", "compare.py", "inspect_candidates.py", "render_preview.py")},
              "summary": summary, "inspected_candidates": len(fits),
              "descriptor_validated": False, "physics_steps": 0,
              "motion_accepted": False, "collision_checked": False,
              "boundary": "All saved proposals, finite local multistart fit only; no pose threshold or physical acceptance"}
    (out / "audit.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    render(out)
    print(json.dumps({"inspected_candidates": len(fits), "summary": summary}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Completed comparison directory")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    audit(args.root.resolve(), args.output.resolve(), args.seed)
