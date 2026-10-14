"""One free-body grasp/lift probe; reuse the existing guarded workcell step."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import time

import mujoco
import numpy as np

from infer import digest


def probe(root, source, empty_close=False, render=False, continuation=None):
    planned=json.loads((source/"motion-plan/report.json").read_text())
    if planned["status"]!="motion_plan_verified":raise ValueError("Verified full motion plan required")
    for name,expected in planned["input_hashes"].items():
        if digest(source/name)!=expected:raise ValueError("Motion-plan input changed: "+name)
    for name,expected in planned["reused_sources_sha256"].items():
        if digest(root/"experiments/colab-twin"/name)!=expected:raise ValueError("Reused motion source changed: "+name)
    if digest(source/"motion-plan/protocol.json")!=planned["protocol_sha256"]:raise ValueError("Protocol changed")
    goal,protocol=planned["chosen"],planned["protocol"]
    prefix="full-cycle-" if continuation else "empty-close-" if empty_close else "contact-probe-"
    out=source/(prefix+datetime.now().strftime("%Y%m%d-%H%M%S")+f"-{os.getpid()}")
    out.mkdir(exist_ok=False)
    sys.path.insert(0,str(root/"experiments/colab-twin"))
    from learning_env import StateWorkcell,PhysicalTaskMonitor,SafetyStop,observe
    from grasp_episode import OBSTACLE,grasp_acceptance
    from conservative_collision import ConservativeCollisionChecker
    from configuration_sweep import validate_configuration_path
    from expert_path import joint_path_lookahead
    model_path=root/"workspaces/so101_ws/src/so101_mujoco/models/so101.xml"
    metadata={"model_sha256":digest(model_path),"scene_configuration":{"jaw_force_cap_nm":.15,"noslip_iterations":10,
              "baseline_object_z_m":.01,"obstacle":OBSTACLE},"control_period_s":.02,"physics_dt_s":.002}
    began=time.monotonic();rows=[];actions=[];states=[];object_rotations=[];writer=renderer=None;monitor=None;baseline=None
    report={"status":"started","scope":"one simulated free-body contact grasp and lift; no placement/detach/return acceptance",
            "output_directory":str(out),
            "candidate":goal["candidate"],"origin":goal["origin"],"model_score":goal["model_score"],
            "empty_close":empty_close,"motion_plan_sha256":digest(source/"motion-plan/report.json"),
            "protocol":protocol,"hardware_access":False,"training_steps":0,"object_qpos_modified_after_reset":False,
            "full_grasp_place_passed":False,"physical_lift_passed":False,"place_verified":False,"stage":"reset"}
    try:
        env=StateWorkcell(model_path,out/"scene",metadata)
        # Public checker interface stays identical; strengthen with the existing
        # complete support-bound kernel. No production environment rewrite.
        env.checker=ConservativeCollisionChecker(env.checker.model,gripper=.5,margin_m=.001)
        if len(env.checker.pairs)!=planned["checked_pair_count"]:raise ValueError("Collision coverage differs")
        data=env.data
        data.qpos[:6]=np.r_[goal["start_q5"],.5];data.qvel[:]=0;data.ctrl[:]=data.qpos[:6]
        if empty_close:data.qpos[6:9]=[.24,-.17,.012]  # Reset-only negative, as in original episode.
        mujoco.mj_forward(env.model,data)
        report.update(free_object=True,weld_count=int(env.model.neq),mocap_count=int(env.model.nmocap),
                      checked_pair_count=len(env.checker.pairs),initial_qpos=data.qpos.tolist())
        if env.model.neq or env.model.nmocap:raise ValueError("Unexpected weld/mocap fixture")
        if render:
            import imageio.v2 as imageio
            renderer=mujoco.Renderer(env.model,height=480,width=848)
            writer=imageio.get_writer(out/"grasp-lift.mp4",fps=25,codec="libx264",quality=8)
        def step(stage,command,physics_observer=None):
            report["stage"]=stage
            if time.monotonic()-began>protocol["wall_limit_s"]:raise RuntimeError("wall_limit")
            if data.time>=protocol["simulation_limit_s"]:raise RuntimeError("simulation_limit")
            guard=validate_configuration_path(data.qpos[:6].copy(),command,
                lambda q:env.checker.evaluate(q,require_fixed_gripper=False)["valid"],
                arm_resolution_rad=.005,jaw_resolution_rad=.002)
            if not guard["valid"]:raise SafetyStop("Measured-pose command chord uncertified",guard)
            obs,row=env.step(command,physics_observer=physics_observer)
            row["stage"]=stage;rows.append(row);actions.append(np.array(command));states.append(obs["observation.state"])
            object_rotations.append(data.xmat[env.model.body("grasp_target").id].reshape(3,3).copy())
            if monitor is not None:
                measured=monitor.update(row)
                if measured["failure_reason"]:raise RuntimeError(measured["failure_reason"])
            if renderer is not None and len(rows)%2==0:
                renderer.update_scene(data,camera="overview")
                writer.append_data(renderer.render())
            return row
        for _ in range(50):step("ready",np.r_[goal["start_q5"],.5])
        target=env.model.body("grasp_target").id
        baseline=float(data.xpos[target,2]);env.baseline_z=baseline;monitor=PhysicalTaskMonitor(baseline)
        def move(stage,path,jaw):
            path=np.asarray(path,float)
            while True:
                actual=data.qpos[:5].copy()
                command,_=joint_path_lookahead(path,actual,.006)  # 0.3 rad/s x original 20 ms.
                step(stage,np.r_[command,jaw])
                if np.max(np.abs(data.qpos[:5]-path[-1]))<=.0015 and np.linalg.norm(data.qvel[:5])<.05:
                    break
        move("approach",goal["approach_path"],.5)
        move("descend",goal["descent_path"],.5)
        down=np.asarray(goal["grasp_q5"])
        for _ in range(300):
            row=step("close",np.r_[down,.015])
            if min(row["tip_forces_n"])>.02 and abs(data.qvel[5])<.05:break
        else:raise RuntimeError("no_stable_dual_contact_before_6s")
        move("lift",goal["lift_path"],.015)
        for _ in range(75):step("hold",np.r_[goal["pregrasp_q5"],.015])
        accepted=grasp_acceptance(rows,baseline)
        report.update(status="grasp_lift_probe_completed",acceptance=accepted,monitor=monitor.report(),
                      physical_lift_passed=bool(accepted["grasp_success"] and monitor.grasp_success and not monitor.failure_reason))
        if continuation is not None:
            if not report["physical_lift_passed"]:raise RuntimeError("Actual lift gate failed")
            continuation(env,goal,step,report,monitor)
    except Exception as error:
        report.update(status="stopped",error_type=type(error).__name__,error=str(error),error_details=getattr(error,"details",{}))
    finally:
        if writer is not None:writer.close()
        if renderer is not None:renderer.close()
        if "env" in locals():
            report.update(simulation_s=float(env.data.time),physics_steps=int(round(env.data.time/.002)),
                          final_object_xyz_m=env.data.xpos[env.model.body("grasp_target").id].tolist(),
                          final_q6=env.data.qpos[:6].tolist(),
                          final_object_rotation=env.data.xmat[env.model.body("grasp_target").id].reshape(3,3).tolist(),
                          baseline_object_z_m=baseline,monitor=monitor.report() if monitor else None)
        report["wall_s"]=time.monotonic()-began
        report["source_adapter_sha256"]=digest(Path(__file__))
        report["reused_sources_sha256"]={name:digest(root/"experiments/colab-twin"/name) for name in
            ("learning_env.py","grasp_episode.py","conservative_collision.py","configuration_sweep.py","expert_path.py")}
        if rows:
            np.savez_compressed(out/"trace.npz",time_s=np.array([r["time_s"] for r in rows]),stage=np.array([r["stage"] for r in rows]),
                action=np.array(actions),state=np.array(states),object_xyz_m=np.array([r["object_xyz_m"] for r in rows]),
                object_rotation=np.array(object_rotations),
                tip_forces_n=np.array([r["tip_forces_n"] for r in rows]),floor_contact=np.array([r["floor_contact"] for r in rows]),
                arm_valid=np.array([r["arm_valid"] for r in rows]),obstacle_contact=np.array([r["obstacle_contact"] for r in rows]))
            report["trace_sha256"]=digest(out/"trace.npz")
        report["empty_close_rejection_verified"]=bool(empty_close and not report["physical_lift_passed"] and
            report.get("error")=="no_stable_dual_contact_before_6s" and
            monitor is not None and monitor.failure_reason is None and
            rows and all(r["arm_valid"] and not r["obstacle_contact"] and r["finite_state"] for r in rows))
        (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps({"output":str(out),"status":report["status"],"physical_lift_passed":report["physical_lift_passed"],
                          "stage":report["stage"],"error":report.get("error"),"simulation_s":report.get("simulation_s")}))
    if not report["physical_lift_passed"] and not empty_close:raise RuntimeError("Physical probe did not pass; see preserved report")
    if empty_close and not report["empty_close_rejection_verified"]:
        raise RuntimeError("Empty-close negative did not reach the expected safe contact rejection; see report")
    if continuation is not None and not report["full_grasp_place_passed"]:
        raise RuntimeError("Full cycle did not pass; see preserved report")


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--root",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--empty-close",action="store_true");p.add_argument("--render",action="store_true")
    a=p.parse_args();probe(a.root.resolve(),a.output.resolve(),a.empty_close,a.render)
