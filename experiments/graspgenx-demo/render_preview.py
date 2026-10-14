"""Render hypothetical model grasps using the actual SO101 visual mesh."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh


def render(out: Path) -> None:
    geometry = np.load(out / "geometry.npz", allow_pickle=False)
    candidates = np.load(out / "candidates.npz", allow_pickle=False)
    fits = json.loads((out / "pose-inspection.json").read_text())["candidates"]
    poses, scores = candidates["poses"], candidates["scores"]
    top = int(np.argmax(scores))
    nearest = min(fits, key=lambda x: np.hypot(x["translation_error_mm"],
                  x["rotation_error_deg"] * np.pi / 180 * 100))["candidate"]
    object_mesh = trimesh.creation.box(extents=geometry["target_size"] * 1000)
    fig = plt.figure(figsize=(14, 7), facecolor="#f4f6f8")
    fig.suptitle("GraspGen-X: real pretrained output, provisional SO101 tip-gap descriptor", fontsize=14)
    center = geometry["target_center"]
    for panel, index in enumerate((top, nearest), 1):
        ax = fig.add_subplot(1, 2, panel, projection="3d")
        pose = poses[index]
        points = (geometry["vertices"] @ pose[:3, :3].T + pose[:3, 3] - center) * 1000
        triangles = points[geometry["faces"]]
        ax.add_collection3d(Poly3DCollection(triangles, facecolors="#d9a832",
                           linewidths=0, alpha=1., shade=True))
        ax.add_collection3d(Poly3DCollection(object_mesh.triangles, facecolor="#299b66", edgecolor="#12623d", alpha=.9))
        low = np.minimum(points.min(axis=0), -geometry["target_size"]*500)
        high = np.maximum(points.max(axis=0), geometry["target_size"]*500)
        mid = (low+high)/2
        radius = max(high-low)/2+8
        ax.set_xlim(mid[0]-radius, mid[0]+radius)
        ax.set_ylim(mid[1]-radius, mid[1]+radius)
        ax.set_zlim(mid[2]-radius, mid[2]+radius)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=22, azim=-58)
        fit = fits[index]
        title = "Highest model score" if panel == 1 else "Smallest static pose-fit residual"
        ax.set_title(f"{title}: candidate {index}\nscore {scores[index]:.4f} | position {fit['translation_error_mm']:.2f} mm | angle {fit['rotation_error_deg']:.2f} deg", fontsize=11)
        ax.set_xlabel("X relative to object (mm)")
        ax.set_ylabel("Y relative to object (mm)")
        ax.set_zlabel("Z relative to object (mm)")
    fig.text(.5, .04, "Hypothetical open-jaw poses. No motion, collision acceptance, contact grasp or release verified.\nModel score is not a task success probability.", ha="center", fontsize=11, color="#883e36")
    fig.subplots_adjust(left=.02, right=.98, top=.85, bottom=.15, wspace=.05)
    fig.savefig(out / "preview.png", dpi=150)
    plt.close(fig)
    print(str(out / "preview.png"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    render(parser.parse_args().output.resolve())
