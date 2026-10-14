"""Export static SO101 geometry and a declared fingertip-gap proxy; no steps."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

import mujoco
import numpy as np


def prepare(root: Path, out: Path) -> None:
    source = root / "workspaces/so101_ws/src/so101_mujoco/models/so101.xml"
    definitions = root / "experiments/colab-twin"
    constants = {}
    # Read fixture literals without importing the existing execution stack.
    for filename in ("grasp_workcell.py", "grasp_episode.py"):
        for node in ast.parse((definitions / filename).read_text()).body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
                if name in ("TARGET_SIZE", "PICK_CENTER", "PINCH_POINT"):
                    value = node.value.args[0] if isinstance(node.value, ast.Call) else node.value
                    constants[name] = np.asarray(ast.literal_eval(value), dtype=float)

    model = mujoco.MjModel.from_xml_path(str(source))
    data = mujoco.MjData(model)
    base = model.body("gripper").id
    moving = model.body("moving_jaw_so101_v1").id
    # G +Z follows the fingers; G +X follows the opening direction.
    body_from_g = np.diag([1., -1., -1.])
    fixed_center = np.array([-.012, 0., -.096])
    moving_center = np.array([-.0082, -.0726, .0188])
    fixed_half = np.array([.004, .006, .008])
    moving_half = np.array([.004, .008, .006])
    profile = {}
    boxes = []
    for label, jaw in [("open", .5), ("mid", (.5 + .015) / 2)]:
        data.qpos[5] = jaw
        mujoco.mj_forward(model, data)
        rotation = data.xmat[base].reshape(3, 3)
        relative_rotation = rotation.T @ data.xmat[moving].reshape(3, 3)
        other = rotation.T @ (data.xpos[moving] - data.xpos[base])
        other += relative_rotation @ moving_center
        other_half = np.abs(relative_rotation) @ moving_half
        # This is the tip-pad overlap only, not a validated full-finger volume.
        low = np.maximum(fixed_center - fixed_half, other - other_half)
        high = np.minimum(fixed_center + fixed_half, other + other_half)
        low[0] = fixed_center[0] + fixed_half[0]
        high[0] = other[0] - other_half[0]
        if np.any(high <= low):
            raise ValueError(f"No positive fingertip gap at {label}")
        extent = high - low
        offset = body_from_g.T @ ((high + low) / 2)
        boxes.append((extent, offset))
        profile[label] = {"jaw_rad": jaw, "extents_m": extent.tolist(),
                          "offset_m": offset.tolist(), "moving_tip_body_m": other.tolist()}
    data.qpos[5] = .5
    mujoco.mj_forward(model, data)
    vertices, faces, count = [], [], 0
    for geom in range(model.ngeom):
        if model.geom_bodyid[geom] not in (base, moving) or model.geom_group[geom] != 2:
            continue
        mesh = int(model.geom_dataid[geom])
        if mesh < 0:
            continue
        a, n = int(model.mesh_vertadr[mesh]), int(model.mesh_vertnum[mesh])
        b, m = int(model.mesh_faceadr[mesh]), int(model.mesh_facenum[mesh])
        points = model.mesh_vert[a:a+n].copy()
        world = points @ data.geom_xmat[geom].reshape(3, 3).T + data.geom_xpos[geom]
        local = (world - data.xpos[base]) @ data.xmat[base].reshape(3, 3)
        vertices.append(local @ body_from_g)
        faces.append(model.mesh_face[b:b+m].copy() + count)
        count += n
    if not vertices:
        raise ValueError("Missing actual SO101 visual meshes")
    out.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(out / "geometry.npz", vertices=np.concatenate(vertices),
                        faces=np.concatenate(faces), body_from_grasp=body_from_g,
                        target_size=constants["TARGET_SIZE"],
                        target_center=np.r_[constants["PICK_CENTER"], .010],
                        pinch_point=constants["PINCH_POINT"])
    params = {"extents_open": boxes[0][0].tolist(), "offset_open": boxes[0][1].tolist(),
              "extents_mid": boxes[1][0].tolist(), "offset_mid": boxes[1][1].tolist(),
              "gripper_type": 1, "fingertip_depth": .094}
    record = {"kind": "SO101_simulated_tip_gap_proxy", "params": params,
              "measurements": profile, "descriptor_validated": False,
              "collision_geometry_used_for_inference": False,
              "source_model_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "mujoco_version": mujoco.__version__,
              "boundary": "Tip-pad proxy; not wizard-validated full swept volume or physical grasp proof",
              "physics_steps": 0, "hardware_access": False}
    (out / "descriptor.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"geometry_prepared": True, "descriptor_validated": False,
                      "mesh_vertices": count, "output": str(out)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.root.resolve(), args.output.resolve())
