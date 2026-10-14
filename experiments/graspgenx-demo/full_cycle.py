"""Reuse the original transport/release/separation/return after verified lift."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import mujoco
import numpy as np

from contact_probe import probe
from infer import digest
from transfer_preflight import REUSED,held_controller


def run(root,source,preflight,render=False):
    sys.path.insert(0,str(root/"experiments/colab-twin"))
    from released_object import ReleasedObjectQuery,ReleaseAudit,robot_target_force
    from learning_env import SafetyStop
    from visual_grasp_controller import BOX_CORNERS
    from grasp_workcell import TARGET_SIZE
    record=json.loads((preflight/"report.json").read_text())
    if record["status"]!="transport_preflight_verified":raise ValueError("Transport preflight required")
    if record["motion_plan_sha256"]!=digest(source/"motion-plan/report.json"):
        raise ValueError("Motion plan changed")
    if (record["source_adapter_sha256"]!=digest(Path(__file__).parent/"transfer_preflight.py") or
            record["contact_probe_adapter_sha256"]!=digest(Path(__file__).parent/"contact_probe.py")):
        raise ValueError("Contact/transfer adapter binding changed")
    for name,value in record["reused_sources_sha256"].items():
        if digest(root/"experiments/colab-twin"/name)!=value:raise ValueError("Transfer source changed: "+name)
    def continue_cycle(env,goal,step,report,monitor):
        data=env.data;controller=None;release=ReleaseAudit()
        report.update(scope="One full simulated free-body grasp/place/detach/return",full_cycle_adapter_sha256=digest(Path(__file__)),
                      transfer_preflight_sha256=digest(preflight/"report.json"),
                      continuation_sources_sha256={name:digest(root/"experiments/colab-twin"/name) for name in REUSED})
        def release_observer(model,physical):
            if release.anchor is not None:
                release.update(physical.qpos[6:8],robot_target_force(model,physical),float(physical.time))
                if release.failure_reason:raise SafetyStop(release.failure_reason)
        try:
            scene=env.checker.model
            released=ReleasedObjectQuery(Path(report["output_directory"])/"scene/grasp-planning.xml")
            geometry=np.load(source/"geometry.npz",allow_pickle=False)
            controller=held_controller(scene,goal,geometry,released,data.qpos[:6].copy(),data.ctrl.copy(),float(data.time))
            report["payload_corner_error_max_m"]=0.
            report["payload_corner_audit_period_s"]=.02
            corners=BOX_CORNERS*np.asarray(TARGET_SIZE)/2
            target=env.model.body("grasp_target").id
            while not controller.done:
                result=controller.update(data.qpos[:6].copy(),data.qvel[:6].copy(),float(data.time))
                if result["failure_reason"]:raise RuntimeError(result["failure_reason"])
                if result["stage"]=="release":release.start(data.qpos[6:8])
                step(result["stage"],result["command"],release_observer)
                if result["stage"] in ("hold","transport","lower"):
                    origin,rotation,_=controller._fk(data.qpos[:6])
                    predicted=origin+rotation @ controller.payload_relative+corners @ (rotation @ controller.payload_rotation).T
                    actual=data.xpos[target]+corners @ data.xmat[target].reshape(3,3).T
                    error=float(np.max(np.linalg.norm(predicted-actual,axis=1)))
                    report["payload_corner_error_max_m"]=max(report["payload_corner_error_max_m"],error)
                    if error>.002:raise SafetyStop("carried_hypothesis_exceeds_original_2mm_bound")
            # The monitor still independently requires an actual supported 1s rest.
            report.update(status="full_cycle_completed",controller_done=True,
                          full_grasp_place_passed=bool(monitor.report()["passed"] and release.report()["passed"]),
                          place_verified=bool(monitor.place_success))
        finally:
            report["release_audit"]=release.report()
            # Component evidence remains visible even when separation fails.
            report["place_verified"]=bool(monitor.place_success and not monitor.failure_reason)
            report["grasp_place_component_passed"]=bool(monitor.report()["passed"] and release.report()["passed"])
            if controller is not None:
                controller.close()
                report.update(controller_stage=controller.stage,controller_done=controller.done,
                              controller_failure=controller.failure_reason,release_record=controller.release_record,
                              continuation_plans=controller.plan_reports,servo_transitions=controller.servo_transitions,
                              transport_events=controller.transport_events,separation_events=controller.separation_events)
                controller.checker.native.close()
    probe(root,source,render=render,continuation=continue_cycle)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    for name in ("root","output","preflight"):parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--render",action="store_true")
    args=parser.parse_args();run(args.root.resolve(),args.output.resolve(),args.preflight.resolve(),args.render)
