"""Review exported full meshes and explicit frames, with provisional boxes."""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import mujoco
import numpy as np
from scipy.spatial.transform import Rotation
import trimesh
import yourdfpy

from infer import digest


def preview(root, source):
    folder = source / "gripper-assets/so101_sim_tip_region"
    audit = json.loads((folder / "geometry-audit.json").read_text())
    for name, expected in audit["gripper_asset_files_sha256"].items():
        if digest(folder / name) != expected:
            raise ValueError("Gripper asset changed after geometry audit: "+name)
    model_path = root / "workspaces/so101_ws/src/so101_mujoco/models/so101.xml"
    if digest(model_path) != audit["source_model_sha256"]:
        raise ValueError("Source model changed")
    config = json.loads((folder / "config.json").read_text())
    robot = yourdfpy.URDF.load(str(folder / "gripper.urdf"), load_meshes=True)
    frames = np.asarray(config["base_rotation"])
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model,data)
    base, site = model.body("gripper").id, model.site("gripperframe").id
    body_rotation = data.xmat[base].reshape(3,3)
    body_from_site = np.eye(4)
    body_from_site[:3,:3] = body_rotation.T @ data.site_xmat[site].reshape(3,3)
    body_from_site[:3,3] = body_rotation.T @ (data.site_xpos[site]-data.xpos[base])
    grasp_from_site = frames @ body_from_site
    record = {"grasp_from_body": frames.tolist(), "body_from_gripperframe_site": body_from_site.tolist(),
              "grasp_from_gripperframe_site": grasp_from_site.tolist(),
              "pinch_reference_in_grasp_m": config["fingertip"],
              "site_origin_to_pinch_reference_mm": float(np.linalg.norm(grasp_from_site[:3,3]-config["fingertip"])*1000),
              "site_to_grasp_rotation_deg": float(Rotation.from_matrix(grasp_from_site[:3,:3]).magnitude()*180/np.pi),
              "source_model_sha256": digest(model_path), "preview_source_sha256": digest(Path(__file__)),
              "model_descriptor_validated": False, "physics_steps":0}
    (folder / "frame-audit.json").write_text(json.dumps(record,indent=2)+"\n")
    fig = plt.figure(figsize=(15,6))
    fig.suptitle("Exact SO101 gripper assets: independent URDF / MuJoCo geometry audit", fontsize=14)
    for column, (label,jaw) in enumerate((("Open",.5),("Half-open",.2575),("Closed",.015)),1):
        robot.update_cfg({"gripper":jaw})
        ax=fig.add_subplot(1,3,column,projection="3d")
        for name,mesh in robot.scene.geometry.items():
            transform = frames @ robot.scene.graph.get(name)[0]
            triangles = trimesh.transform_points(mesh.vertices,transform)[mesh.faces]*1000
            ax.add_collection3d(Poly3DCollection(triangles,facecolors="#d9a832",linewidths=0,shade=True))
        suffix = "" if column==1 else "2"
        if column<3:
            extent=np.array(config["sweep_volume"]["extents"+suffix])*1000
            center=np.array(config["sweep_volume"]["offset"+suffix])*1000
            corners=np.array(list(itertools.product((-.5,.5),repeat=3)))*extent+center
            for i,j in itertools.combinations(range(8),2):
                if np.count_nonzero(corners[i]!=corners[j])==1:
                    ax.plot(*corners[[i,j]].T,color="#276cc7" if column==1 else "#d26027",linewidth=2)
        ax.set_title(f"{label}: jaw {jaw:.4f} rad")
        ax.set_xlim(-30,75); ax.set_ylim(-52.5,52.5); ax.set_zlim(-5,120)
        ax.set_box_aspect((105,105,125)); ax.view_init(elev=18,azim=-68)
        ax.set_xlabel("G X mm"); ax.set_ylabel("G Y mm"); ax.set_zlabel("G Z mm")
    fig.text(.5,.03,"Full meshes verified. Inner boxes and pinch reference remain provisional; no wizard or motion acceptance.",ha="center",fontsize=11)
    fig.subplots_adjust(left=.01,right=.99,top=.84,bottom=.15,wspace=.01)
    fig.savefig(folder/"geometry-preview.png",dpi=150)
    plt.close(fig)
    print(json.dumps({"preview":str(folder/"geometry-preview.png"),
                      "site_origin_to_pinch_reference_mm":record["site_origin_to_pinch_reference_mm"],
                      "site_to_grasp_rotation_deg":record["site_to_grasp_rotation_deg"]}))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    preview(args.root.resolve(),args.output.resolve())
