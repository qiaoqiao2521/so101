"""Export exact static gripper assets; preserve provisional inner-box labels."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
import trimesh
import yourdfpy

from infer import digest


def numbers(values):
    return " ".join(format(float(x), ".17g") for x in values)


def origin(parent, element):
    quat = np.fromstring(element.get("quat", "1 0 0 0"), sep=" ")
    rotation = Rotation.from_quat(np.r_[quat[1:], quat[0]])
    ET.SubElement(parent, "origin", xyz=element.get("pos", "0 0 0"),
                  rpy=numbers(rotation.as_euler("xyz")))


def compiled_mesh(model, data, geom, base):
    mid = int(model.geom_dataid[geom])
    a, n = int(model.mesh_vertadr[mid]), int(model.mesh_vertnum[mid])
    b, m = int(model.mesh_faceadr[mid]), int(model.mesh_facenum[mid])
    world = model.mesh_vert[a:a+n] @ data.geom_xmat[geom].reshape(3, 3).T + data.geom_xpos[geom]
    local = (world-data.xpos[base]) @ data.xmat[base].reshape(3, 3)
    return local, model.mesh_face[b:b+m].copy()


def export(root, comparison):
    source = root / "workspaces/so101_ws/src/so101_mujoco/models/so101.xml"
    descriptor = json.loads((comparison / "descriptor.json").read_text())
    if digest(source) != descriptor["source_model_sha256"]:
        raise ValueError("MuJoCo model changed since candidate generation")
    geometry = np.load(comparison / "geometry.npz", allow_pickle=False)
    assets = comparison / "gripper-assets" / "so101_sim_tip_region"
    assets.mkdir(parents=True, exist_ok=False)
    (assets / "meshes").mkdir()
    xml = ET.parse(source).getroot()
    subtree = xml.find('.//body[@name="gripper"]')
    children = {b.get("name"): b for b in (subtree, *subtree.findall("body"))}
    if set(children) != {"gripper", "moving_jaw_so101_v1"}:
        raise ValueError("Unexpected gripper subtree; review before exporting")
    meshes = {m.get("name", Path(m.get("file")).stem): m for m in xml.findall("asset/mesh")}
    robot = ET.Element("robot", name="so101_sim_tip_region")
    bindings, copied = [], {}
    for name, body in children.items():
        link = ET.SubElement(robot, "link", name=name)
        for geom in body.findall("geom"):
            if geom.get("class") != "visual":
                continue
            filename = meshes[geom.get("mesh")].get("file")
            original = source.parent / xml.find("compiler").get("meshdir", "") / filename
            filename = Path(filename).name
            shutil.copy2(original, assets / "meshes" / filename)
            copied[filename] = digest(original)
            for kind in ("visual", "collision"):
                block = ET.SubElement(link, kind)
                origin(block, geom)
                shape = ET.SubElement(block, "geometry")
                ET.SubElement(shape, "mesh", filename="meshes/"+filename)
            bindings.append((name, geom.get("mesh")))
    moving = children["moving_jaw_so101_v1"]
    joint = ET.SubElement(robot, "joint", name="gripper", type="revolute")
    origin(joint, moving)
    ET.SubElement(joint, "parent", link="gripper")
    ET.SubElement(joint, "child", link="moving_jaw_so101_v1")
    mj_joint = moving.find("joint")
    ET.SubElement(joint, "axis", xyz=mj_joint.get("axis"))
    lower, upper = np.fromstring(mj_joint.get("range"), sep=" ")
    ET.SubElement(joint, "limit", lower=str(lower), upper=str(upper), effort=".15", velocity="2")
    urdf = assets / "gripper.urdf"
    ET.ElementTree(robot).write(urdf, encoding="utf-8", xml_declaration=True)
    parsed = yourdfpy.URDF.load(str(urdf), build_scene_graph=True, load_meshes=True)
    model = mujoco.MjModel.from_xml_path(str(source))
    data = mujoco.MjData(model)
    base = model.body("gripper").id
    body_ids = [model.body(n).id for n in children]
    geoms = [int(i) for i in range(model.ngeom)
             if model.geom_bodyid[i] in body_ids and model.geom_group[i] == 2]
    if len(geoms) != len(bindings):
        raise ValueError("Incomplete mesh export")
    # Relative geometry must agree despite unrelated arm configurations.
    rows, open_meshes = [], []
    for jaw in np.linspace(.015, .5, 9):
        parsed.update_cfg({"gripper": float(jaw)})
        scene = parsed.scene
        urdf_points = np.concatenate([trimesh.transform_points(mesh.vertices, scene.graph.get(name)[0])
                                      for name, mesh in scene.geometry.items()])
        for q5 in (np.zeros(5), np.array([.2, -.3, .4, -.5, .6])):
            data.qpos[:5], data.qpos[5] = q5, jaw
            mujoco.mj_forward(model, data)
            compiled = [compiled_mesh(model, data, i, base) for i in geoms]
            mj_points = np.concatenate([p for p, _ in compiled])
            error = max(cKDTree(urdf_points).query(mj_points)[0].max(),
                        cKDTree(mj_points).query(urdf_points)[0].max())
            if error > 1e-6:
                raise ValueError(f"URDF/MuJoCo geometry mismatch: {error} m")
            rows.append({"jaw_rad": float(jaw), "arm_q5_rad": q5.tolist(),
                         "bidirectional_surface_vertex_error_m": float(error)})
        if jaw == .5:
            open_meshes = [trimesh.Trimesh(p @ geometry["body_from_grasp"], f, process=False)
                           for p, f in compiled]
    visual = trimesh.util.concatenate(open_meshes)
    visual.export(assets / "vis_mesh.obj")
    # Per-geom convex hulls correspond to the existing MuJoCo collision model.
    trimesh.util.concatenate([mesh.convex_hull for mesh in open_meshes]).export(assets / "coll_mesh.obj")
    transform = np.eye(4)
    transform[:3, :3] = geometry["body_from_grasp"].T
    params = descriptor["params"]
    config = {"open": {"gripper": .5}, "close": {"gripper": .015},
              "fingertip": (geometry["body_from_grasp"].T @ geometry["pinch_point"]).tolist(),
              "sweep_volume": {"extents": params["extents_open"], "offset": params["offset_open"],
                               "extents2": params["extents_mid"], "offset2": params["offset_mid"]},
              "links": list(children), "standoff": [0., params["extents_open"][2]/2],
              "symmetric": False, "type": "revolute_2f", "bbox": visual.bounds.tolist(),
              "base_rotation": transform.tolist()}
    (assets / "config.json").write_text(json.dumps(config, indent=2)+"\n")
    report = {"status": "full_gripper_geometry_and_frames_verified",
              "source_model_sha256": digest(source), "source_mesh_sha256": copied,
              "source_code_sha256": digest(Path(__file__)), "source_descriptor_sha256": digest(comparison / "descriptor.json"),
              "geometry_checks": rows, "geometry_tolerance_m": 1e-6,
              "body_from_grasp": geometry["body_from_grasp"].tolist(),
              "pinch_in_grasp_frame_m": config["fingertip"],
              "grasp_frame_is_gripperframe_site": False, "symmetric": False,
              "model_descriptor_validated": False, "inner_region": "existing provisional fingertip-pad annotation",
              "gripper_asset_files_sha256": {str(p.relative_to(assets)): digest(p)
                                             for p in assets.rglob('*') if p.is_file()},
              "physics_steps": 0, "hardware_access": False,
              "boundary": "Full mesh/FK export verified; inner boxes and pinch reference remain provisional; no wizard completion, contact or path certificate"}
    (assets / "geometry-audit.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({"status": report["status"], "checks": len(rows),
                      "max_error_m": max(x["bidirectional_surface_vertex_error_m"] for x in rows),
                      "model_descriptor_validated": False, "assets": str(assets)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Existing comparison directory")
    args = parser.parse_args()
    export(args.root.resolve(), args.output.resolve())
