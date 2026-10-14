"""Bind a saved official wizard annotation to the declared simulation region."""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import trimesh
import yourdfpy

from infer import digest


def validate_region(root, wizard, out):
    config_path = wizard / "so101_task_tip_region/config.json"
    config = json.loads(config_path.read_text())
    launch = json.loads((wizard / "launcher.json").read_text())
    descriptor = json.loads((out / "descriptor.json").read_text())
    geo = np.load(out / "geometry.npz", allow_pickle=False)
    model = root / "workspaces/so101_ws/src/so101_mujoco/models/so101.xml"
    if descriptor["source_model_sha256"] != digest(model):
        raise ValueError("Source model binding changed")
    if config["open"] != {"gripper": .5} or config["close"] != {"gripper": .015}:
        raise ValueError("Task jaw interval changed")
    transform = np.asarray(config["base_rotation"], dtype=float)
    expected = np.eye(4); expected[:3,:3] = geo["body_from_grasp"].T
    if not np.allclose(transform,expected,rtol=0,atol=1e-12):
        raise ValueError("Wizard frame differs from verified geometry")
    if config["symmetric"] is not False or config["type"] != "revolute_2f":
        raise ValueError("Unsupported SO101 type or unproven symmetry")
    if config["fingertip"] != config["sweep_volume"]["offset"]:
        raise ValueError("Official fingertip semantics differ from open box center")
    robot = yourdfpy.URDF.load(str(config_path.parent / "gripper.urdf"),load_meshes=True)
    rows=[]
    for name,jaw,suffix in (("open",.5,""),("half",.2575,"2")):
        ext=np.asarray(config["sweep_volume"]["extents"+suffix],float)
        off=np.asarray(config["sweep_volume"]["offset"+suffix],float)
        if ext.shape!=(3,) or off.shape!=(3,) or not np.isfinite(np.r_[ext,off]).all() or np.any(ext<=0):
            raise ValueError("Malformed region box")
        robot.update_cfg({"gripper":jaw});manager=trimesh.collision.CollisionManager();components=[]
        for geom,mesh in robot.scene.geometry.items():
            mesh=mesh.copy();mesh.apply_transform(transform @ robot.scene.graph.get(geom)[0])
            manager.add_object(geom,mesh);components.extend(mesh.split(only_watertight=False))
        if not components or any(not mesh.is_watertight for mesh in components):
            raise ValueError("Region containment requires complete watertight meshes")
        box=trimesh.creation.box(extents=ext);box.apply_translation(off)
        collision=bool(manager.in_collision_single(box))
        inside=any(bool(mesh.contains([off])[0]) for mesh in components)
        enclosed=any(np.all(mesh.bounds[0]>=off-ext/2) and np.all(mesh.bounds[1]<=off+ext/2) for mesh in components)
        distance=float(manager.min_distance_single(box))
        if collision or inside or enclosed or not np.isfinite(distance) or distance<.001:
            raise ValueError(f"Region {name} intersects geometry or has <1mm raw-mesh clearance")
        rows.append({"name":name,"jaw_rad":jaw,"extents_m":ext.tolist(),"offset_m":off.tolist(),
                     "raw_mesh_distance_m":distance,"surface_collision":collision,"center_inside":inside,"component_enclosed":bool(enclosed)})
    # The official config carries complete geometry; these released backbones
    # consume only the two annotated boxes. Keep pinch reference separate.
    params={"extents_open":rows[0]["extents_m"],"offset_open":rows[0]["offset_m"],
            "extents_mid":rows[1]["extents_m"],"offset_mid":rows[1]["offset_m"],
            "gripper_type":1,"fingertip_depth":float(config["fingertip"][2])}
    report={"status":"simulation_tip_region_verified","descriptor_validated":True,
            "validation_scope":"Declared simulated conservative tip region at jaw .5/.2575; no hardware calibration or maximum aperture claim",
            "rows":rows,"wizard_config_sha256":digest(config_path),"wizard_launcher":launch,
            "wizard_assets_sha256":{str(p.relative_to(config_path.parent)):digest(p) for p in config_path.parent.rglob('*') if p.is_file()},
            "source_model_sha256":digest(model),"geometry_sha256":digest(out/"geometry.npz"),
            "adapter_sha256":digest(Path(__file__)),"minimum_annotation_clearance_m":.001,
            "pinch_reference_grasp_m":(geo["body_from_grasp"].T @ geo["pinch_point"]).tolist(),
            "official_fingertip_grasp_m":config["fingertip"],"params":params,
            "physics_steps":0,"hardware_access":False,"physical_grasp_verified":False}
    (out/"region-validation.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"descriptor-before-region-review.json").write_text(json.dumps(descriptor,indent=2)+"\n")
    descriptor.update(kind="SO101_declared_simulated_tip_region",params=params,descriptor_validated=True,
                      validation_scope=report["validation_scope"],region_validation_sha256=digest(out/"region-validation.json"),
                      boundary="Official wizard annotation verified for this task region; raw full mesh check is not motion/physics acceptance")
    (out/"descriptor.json").write_text(json.dumps(descriptor,indent=2)+"\n")
    print(json.dumps({"status":report["status"],"distances_m":[r["raw_mesh_distance_m"] for r in rows]}))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("root","wizard","output"):p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args();validate_region(a.root.resolve(),a.wizard.resolve(),a.output.resolve())
