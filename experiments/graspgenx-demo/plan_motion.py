"""Plan a declared model proposal's pregrasp/descent/lift using existing assets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import time

import numpy as np

from infer import digest
from inspect_candidates import inspect


def plan(root, source):
    descriptor=json.loads((source/"descriptor.json").read_text())
    if not descriptor.get("descriptor_validated") or digest(source/"region-validation.json")!=descriptor.get("region_validation_sha256"):
        raise ValueError("Verified task-region descriptor required")
    region=json.loads((source/"region-validation.json").read_text())
    if region["geometry_sha256"]!=digest(source/"geometry.npz") or region["params"]!=descriptor["params"]:
        raise ValueError("Region and geometry/parameter binding differ")
    guards=json.loads((source/"collision-diagnostic/report.json").read_text())
    for name,expected in guards["input_hashes"].items():
        if digest(source/name)!=expected:raise ValueError("Candidate guard input changed: "+name)
    pool=np.load(source/"pool.npz",allow_pickle=False)
    eligible=guards["diagnostic_ranked_candidates"]
    if guards["status"]!="static_guards_completed" or not eligible:raise ValueError("No eligible static diagnostic candidates")
    model_path=root/"workspaces/so101_ws/src/so101_mujoco/models/so101.xml"
    if digest(model_path)!=descriptor["source_model_sha256"]:raise ValueError("Source model changed")
    out=source/"motion-plan";out.mkdir(exist_ok=False)
    sys.path.insert(0,str(root/"experiments/colab-twin"))
    from grasp_episode import build_contact_scene,solve_pinch_ik
    from conservative_collision import ConservativeCollisionChecker
    from joint_planner import plan_joint_path,validate_joint_path
    from configuration_sweep import validate_configuration_path
    _,rig,_=build_contact_scene(model_path,out/"scene",noslip_iterations=10)
    checker=ConservativeCollisionChecker(rig,gripper=.5,margin_m=.001)
    closed=ConservativeCollisionChecker(rig,gripper=.015,margin_m=.001)
    start=solve_pinch_ik(rig,np.array([.24,.14,.06]))
    protocol={"pregrasp_standoff_m":.042,"position_error_m":1e-6,"rotation_error_rad":1e-5,
              "arm_margin_m":.001,"path_resolution_rad":.005,"jaw_resolution_rad":.002,
              "planning_timeout_s":10,"seed":0,"physics_dt_s":.002,"control_period_s":.02,
              "simulation_limit_s":90,"wall_limit_s":120,"nominal_start_q5_rad":start.tolist(),
              "pose_tolerance_scope":"Strict numerical reproduction of selected full pose; not universal physical success tolerance"}
    (out/"protocol.json").write_text(json.dumps(protocol,indent=2)+"\n")
    # Batch the existing full-pose solver; no new IK or altered proposal poses.
    prep=out/"pregrasp-fits";prep.mkdir()
    shutil.copyfile(source/"geometry.npz",prep/"geometry.npz")
    poses=pool["poses"][eligible].copy()
    poses[:,:3,3]-=poses[:,:3,2]*protocol["pregrasp_standoff_m"]
    np.savez_compressed(prep/"candidates.npz",poses=poses,scores=pool["scores"][eligible],pool_indices=eligible)
    inspect(root,prep,0)
    fits=json.loads((prep/"pose-inspection.json").read_text())["candidates"]
    rows=[];chosen=None;began=time.monotonic()
    for slot,index in enumerate(eligible):
        pre=fits[slot];row={"candidate":index,"origin":str(pool["origins"][index]),"model_score":float(pool["scores"][index]),"pregrasp_fit":pre}
        if pre["translation_error_mm"]>protocol["position_error_m"]*1000 or pre["rotation_error_deg"]>protocol["rotation_error_rad"]*180/np.pi:
            row["reason"]="pregrasp_pose_not_reproduced";rows.append(row);continue
        preq=np.array(pre["fitted_q5_rad"]);down=np.array(guards["candidates"][index]["fitted_q5_rad"]) if "fitted_q5_rad" in guards["candidates"][index] else np.array(json.loads((source/"all-candidates/pose-inspection.json").read_text())["candidates"][index]["fitted_q5_rad"])
        descent=validate_joint_path([preq,down],checker.is_valid,.005)
        ascent=validate_joint_path([down,preq],closed.is_valid,.005)
        row.update(descent=descent,ascent=ascent)
        if not descent["valid"] or not ascent["valid"]:
            row["reason"]="grasp_leg_uncertified";rows.append(row);continue
        approach=plan_joint_path(start,preq,checker.bounds,checker.is_valid,seed=0,timeout_s=10,resolution_rad=.005)
        row["approach"]=approach
        if approach["status"]!="solved":
            row["reason"]="approach_not_solved";rows.append(row);continue
        closure=validate_configuration_path(np.r_[down,.5],np.r_[down,.015],lambda q:checker.evaluate(q,require_fixed_gripper=False)["valid"],arm_resolution_rad=.005,jaw_resolution_rad=.002)
        row["closure"]=closure
        if not closure["valid"]:
            row["reason"]="closure_uncertified";rows.append(row);continue
        row["reason"]="planned";rows.append(row)
        chosen={"candidate":index,"origin":row["origin"],"model_score":row["model_score"],
                "target_pose_world":pool["poses"][index].tolist(),"pregrasp_pose_world":poses[slot].tolist(),
                "start_q5":start.tolist(),"pregrasp_q5":preq.tolist(),"grasp_q5":down.tolist(),
                "approach_path":approach["path"],"descent_path":[preq.tolist(),down.tolist()],
                "lift_path":[down.tolist(),preq.tolist()]}
        break
    report={"status":"motion_plan_verified" if chosen else "no_motion_plan","chosen":chosen,"attempts":rows,
            "protocol":protocol,"protocol_sha256":digest(out/"protocol.json"),"elapsed_s":time.monotonic()-began,
            "checked_pair_count":len(checker.pairs),"source_model_sha256":digest(model_path),
            "source_adapter_sha256":digest(Path(__file__)),"input_hashes":{name:digest(source/name) for name in
            ("descriptor.json","region-validation.json","geometry.npz","pool.npz","collision-diagnostic/report.json","all-candidates/pose-inspection.json")},
            "reused_sources_sha256":{name:digest(root/"experiments/colab-twin"/name) for name in
            ("grasp_episode.py","conservative_collision.py","configuration_sweep.py","joint_planner.py")},
            "physics_steps":0,"hardware_access":False,"target_contact_verified":False,"physical_grasp_verified":False,
            "boundary":"Pregrasp/descent/lift arm/world plan, fixed scene, full object input; payload and full release cycle not accepted"}
    (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"status":report["status"],"candidate":chosen["candidate"] if chosen else None,"attempts":len(rows)}))
    if chosen is None:raise RuntimeError("No full pose/arm-world motion plan; no physical execution")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();plan(a.root.resolve(),a.output.resolve())
