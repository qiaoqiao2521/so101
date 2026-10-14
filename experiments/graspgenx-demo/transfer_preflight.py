"""Check a declared payload hypothesis before reusing the transport lifecycle."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
import time

import mujoco
import numpy as np

from infer import digest


REUSED = ("learning_env.py", "visual_grasp_controller.py", "visual_localization.py", "transport_worker.py", "separation_worker.py",
          "released_object.py", "joint_planner.py", "configuration_sweep.py",
          "conservative_collision.py", "expert_path.py", "grasp_episode.py", "grasp_workcell.py")


def declared_payload(rig, goal, geometry):
    """Use proposal FK and initial geometry only; never execution object truth."""
    query=mujoco.MjData(rig);query.qpos[:]=np.r_[goal["grasp_q5"],.015]
    mujoco.mj_forward(rig,query)
    body=rig.body("gripper").id;rotation=query.xmat[body].reshape(3,3)
    return rotation.T @ (geometry["target_center"]-query.xpos[body]),rotation.T.copy()


def held_controller(rig, goal, geometry, released_query, q6, last_command, elapsed):
    from visual_grasp_controller import VisualGraspController
    controller=VisualGraspController(rig,geometry["target_center"][:2],np.r_[goal["start_q5"],.5],
                                     seed=0,released_query=released_query)
    controller.target_frozen=True
    controller.freeze_record={"source":"frozen full-geometry input upper bound; not live vision"}
    controller.payload_relative,controller.payload_rotation=declared_payload(rig,goal,geometry)
    controller.last_command=np.asarray(last_command).copy()
    controller.reference=np.r_[q6[:5],.015]
    controller._set_dwell("hold",q6[:5],.015,elapsed,1.5)
    return controller


def preflight(root,source,positive,negative):
    sys.path.insert(0,str(root/"experiments/colab-twin"))
    from transport_worker import TransportSnapshot
    from visual_grasp_controller import _run_transport_plan,BOX_CORNERS
    from grasp_workcell import TARGET_SIZE
    from joint_planner import validate_joint_path
    positive_record=json.loads((positive/"report.json").read_text())
    negative_record=json.loads((negative/"report.json").read_text())
    planned=json.loads((source/"motion-plan/report.json").read_text());goal=planned["chosen"]
    for record in (positive_record,negative_record):
        if (record["motion_plan_sha256"]!=digest(source/"motion-plan/report.json") or
                record["source_adapter_sha256"]!=digest(Path(__file__).parent/"contact_probe.py")):
            raise ValueError("Contact probe binding changed")
    if not positive_record["physical_lift_passed"] or not negative_record["empty_close_rejection_verified"]:
        raise ValueError("Actual lift and safe empty-close rejection required")
    if digest(positive/"trace.npz")!=positive_record["trace_sha256"]:
        raise ValueError("Contact trace changed")
    out=source/("transfer-preflight-"+time.strftime("%Y%m%d-%H%M%S"));out.mkdir(exist_ok=False)
    report={"status":"started","physical_transfer_passed":False,"physics_steps":0,
            "payload_uncertainty_m":.002,"payload_clearance_m":.0002,"arm_margin_m":.001,
            "source_adapter_sha256":digest(Path(__file__)),
            "contact_probe_adapter_sha256":digest(Path(__file__).parent/"contact_probe.py"),
            "motion_plan_sha256":digest(source/"motion-plan/report.json"),
            "positive_report_sha256":digest(positive/"report.json"),"negative_report_sha256":digest(negative/"report.json"),
            "reused_sources_sha256":{name:digest(root/"experiments/colab-twin"/name) for name in REUSED},
            "scope":"Frozen initial object geometry + encoders; actual object pose only scores/rejects the hypothesis"}
    controller=None
    try:
        rig=mujoco.MjModel.from_xml_path(str(positive/"scene/grasp-planning.xml"))
        geometry=np.load(source/"geometry.npz",allow_pickle=False)
        trace=np.load(positive/"trace.npz",allow_pickle=False)
        q6=np.asarray(positive_record["final_q6"])
        controller=held_controller(rig,goal,geometry,None,q6,trace["action"][-1],positive_record["simulation_s"])
        query=mujoco.MjData(rig);body=rig.body("gripper").id;corners=BOX_CORNERS*np.asarray(TARGET_SIZE)/2
        errors=[]
        for index in np.flatnonzero(trace["stage"]=="hold"):
            query.qpos[:]=trace["state"][index];mujoco.mj_forward(rig,query)
            rotation=query.xmat[body].reshape(3,3)
            center=query.xpos[body]+rotation @ controller.payload_relative
            predicted=center+corners @ (rotation @ controller.payload_rotation).T
            actual=trace["object_xyz_m"][index]+corners @ trace["object_rotation"][index].T
            errors.append(float(np.max(np.linalg.norm(predicted-actual,axis=1))))
        if not errors:raise ValueError("No actual hold samples")
        report["hold_corner_error_max_m"]=max(errors)
        report["declared_payload_relative_m"]=controller.payload_relative.tolist()
        report["declared_payload_rotation"]=controller.payload_rotation.tolist()
        if max(errors)>.002:raise RuntimeError("payload_hypothesis_exceeds_original_2mm_bound")
        snapshot=TransportSnapshot(q6,geometry["target_center"][:2],controller.payload_relative,
            controller.payload_rotation,controller.world,.002,positive_record["simulation_s"])
        proposal=_run_transport_plan(copy.copy(rig),snapshot)
        checks=[validate_joint_path(path,controller._payload_valid,.005) for path in proposal.paths]
        report.update(transport=json.loads(proposal.report_json),independent_path_checks=checks)
        if not all(row["valid"] for row in checks):raise RuntimeError("transport_postcheck_failed")
        if report["transport"]["budget_finish_lower_bound_s"]>90:raise RuntimeError("necessary_simulation_budget_failed")
        report["status"]="transport_preflight_verified"
    except Exception as error:
        report.update(status="stopped",error_type=type(error).__name__,error=str(error))
    finally:
        if controller is not None:controller.close();controller.checker.native.close()
        (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps({"output":str(out),"status":report["status"],
                          "corner_error_m":report.get("hold_corner_error_max_m"),"error":report.get("error")}))
    if report["status"]!="transport_preflight_verified":raise RuntimeError("Transfer preflight failed; see preserved report")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    for name in ("root","output","positive","negative"):parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args();preflight(args.root.resolve(),args.output.resolve(),args.positive.resolve(),args.negative.resolve())
