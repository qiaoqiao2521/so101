"""Bounded RGB localization and contact-grasp pilot; never operates hardware.

Scenario reset and scoring may access object truth. The controller receives
only RGB-derived XY, joint encoder state and declared static geometry.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import xml.etree.ElementTree as ET

os.environ.setdefault('MUJOCO_GL', 'egl')
import mujoco
import numpy as np
from PIL import Image, ImageDraw
from collision_scene import CollisionChecker
from grasp_episode import build_contact_scene, solve_pinch_ik
from learning_env import PhysicalTaskMonitor, diagnostics
from visual_localization import TopDownCalibration, localize_green_target

SOURCE = Path(__file__).resolve().parents[2]/'workspaces/so101_ws/src/so101_mujoco/models/so101.xml'


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_hashes():
    root = Path(__file__).parent
    return {p.name: digest(p) for p in root.glob('*.py') if not p.name.startswith('test_')}


def reset_scene(model, rig, xy):
    """Reset-only fixture placement; no scripted object motion after this call."""
    data = mujoco.MjData(model)
    start = solve_pinch_ik(rig, np.array([.24, .14, .06]))
    data.qpos[:6] = np.r_[start, .5]
    data.qpos[6:9] = [*xy, .012]
    data.ctrl[:] = data.qpos[:6]
    mujoco.mj_forward(model, data)
    for _ in range(500):
        mujoco.mj_step(model, data)
    mujoco.mj_forward(model, data)
    return data


def render_rgb(renderer, data):
    renderer.update_scene(data, camera='topdown')
    return renderer.render().copy()


def save_overlay(path, rgb, estimate):
    image = Image.fromarray(rgb)
    draw = ImageDraw.Draw(image)
    if estimate.pixel_xy is not None:
        x, y = estimate.pixel_xy
        draw.line((x-8,y,x+8,y),fill='red',width=1)
        draw.line((x,y-8,x,y+8),fill='red',width=1)
    draw.text((8,8),f'{estimate.valid}: {estimate.reason}',fill='black',stroke_width=1,stroke_fill='white')
    image.save(path)


def run_p0(source, out, protocol, deadline):
    model, rig, scene_path = build_contact_scene(source, out/'scene', noslip_iterations=10)
    # Visual-only negative controls, separated from the unmodified physical scene.
    tree = ET.parse(scene_path)
    world = tree.getroot().find('worldbody')
    ET.SubElement(world,'geom',name='p0_occluder',type='box',pos='.24 -.13 .06',
                  size='.016 .016 .002',rgba='.1 .1 .1 0',contype='0',conaffinity='0')
    ET.SubElement(world,'geom',name='p0_distractor',type='box',pos='.27 -.16 .010',
                  size='.009 .009 .008',rgba='.28 .57 .43 0',contype='0',conaffinity='0')
    negative_scene=out/'p0-scene.xml'
    tree.write(negative_scene,encoding='utf-8',xml_declaration=True)
    model=mujoco.MjModel.from_xml_path(str(negative_scene))
    calibration=TopDownCalibration.from_mujoco_model(model,width=640,height=480,top_plane_z_m=.018)
    renderer=mujoco.Renderer(model,height=480,width=640)
    rows=[]
    try:
        for case in protocol['p0_positives']:
            if time.monotonic()>=deadline:
                break
            data=reset_scene(model,rig,case['initial_xy_m'])
            rgb=render_rgb(renderer,data)
            estimate=localize_green_target(rgb,calibration,timestamp_s=float(data.time))
            truth=data.xpos[model.body('grasp_target').id,:2].copy()
            error=float(np.linalg.norm(np.array(estimate.xy_m)-truth)) if estimate.valid else None
            rows.append({'id':case['id'],'kind':'positive','estimate':estimate.to_dict(),
                         'truth_xy_m':truth.tolist(),'error_m':error,
                         'passed':bool(estimate.valid and error<=protocol['p0_max_xy_error_m'])})
            save_overlay(out/(case['id']+'.png'),rgb,estimate)
        target=model.geom('target_collision').id
        occluder=model.geom('p0_occluder').id
        distractor=model.geom('p0_distractor').id
        for kind in protocol['p0_negatives']:
            if time.monotonic()>=deadline:
                break
            model.geom_rgba[target,3]=1
            model.geom_rgba[occluder,3]=0
            model.geom_rgba[distractor,3]=0
            if kind=='missing': model.geom_rgba[target,3]=0
            elif kind in ('half_occluded','fully_occluded'):
                model.geom_rgba[occluder,3]=1
                model.geom_pos[occluder]=[.250 if kind=='half_occluded' else .24,-.13,.06]
                model.geom_size[occluder]=[.010 if kind=='half_occluded' else .016,.016,.002]
            elif kind=='two_candidates': model.geom_rgba[distractor,3]=1
            else: raise ValueError('Unknown negative fixture')
            data=reset_scene(model,rig,[.24,-.13])
            rgb=render_rgb(renderer,data)
            estimate=localize_green_target(rgb,calibration,timestamp_s=float(data.time))
            rows.append({'id':kind,'kind':'negative','estimate':estimate.to_dict(),'passed':not estimate.valid})
            save_overlay(out/(kind+'.png'),rgb,estimate)
    finally:
        renderer.close()
    errors=[r['error_m'] for r in rows if r['kind']=='positive' and r['error_m'] is not None]
    expected=len(protocol['p0_positives'])+len(protocol['p0_negatives'])
    return {'passed':len(rows)==expected and all(r['passed'] for r in rows),
            'complete':len(rows)==expected,'planned':expected,'attempted':len(rows),
            'max_xy_error_m':max(errors,default=None),'rows':rows,
            'calibration':{'source':'fixed simulator camera intrinsics and pose, not a real camera calibration',
                           'camera_name':'topdown','width':640,'height':480,'fovy_degrees':float(model.cam_fovy[model.camera('topdown').id]),
                           'position_m':model.cam_pos[model.camera('topdown').id].tolist(),'top_plane_z_m':.018},
            'negative_fixtures':'rendered visual-only occluder, invisible target, second green box; no pixel masking'}


def run_physical_episode(source, out, protocol, case, deadline, *, video=False):
    from visual_grasp_controller import VisualGraspController
    from joint_planner import validate_joint_path
    import imageio.v2 as imageio
    out.mkdir(exist_ok=False)
    start_wall=time.monotonic()
    deadline=min(deadline,start_wall+protocol['max_episode_wall_s'])
    rows=[]; observations=[]; frame_count=0; renderer=None; writer=None; monitor=None; controller=None
    pulse_count=0; pulse=None; pulse_before=None; pulse_after=None; obstacle_steps=0
    status={'passed':False,'safety_stop':False,'failure_reason':None}
    try:
        model,rig,_=build_contact_scene(source,out/'scene',noslip_iterations=10)
        data=reset_scene(model,rig,case['initial_xy_m'])
        initial=data.qpos.copy()
        baseline_z=float(data.xpos[model.body('grasp_target').id,2])
        monitor=PhysicalTaskMonitor(baseline_z)
        checker=CollisionChecker(rig,gripper=.5,margin_m=.001)
        calibration=TopDownCalibration.from_mujoco_model(model,width=640,height=480,top_plane_z_m=.018)
        renderer=mujoco.Renderer(model,height=480,width=640)
        rgb=render_rgb(renderer,data)
        first=localize_green_target(rgb,calibration,timestamp_s=0.0)
        observations.append(first.to_dict())
        save_overlay(out/'initial-localization.png',rgb,first)
        if not first.valid: raise RuntimeError('initial_localization_rejected: '+first.reason)
        controller=VisualGraspController(rig,first.xy_m,data.qpos[:6].copy(),seed=0,target_timestamp_s=0.0)
        if video:
            writer=imageio.get_writer(out/'grasp-place.mp4',fps=25,codec='libx264',quality=8)
        time0=float(data.time); tick=0; next_image=.5
        last={'target_frozen':False,'stage':'approach'}
        while float(data.time)-time0 < protocol['max_sim_s']-1e-9:
            if time.monotonic()>=deadline: raise TimeoutError('wall_time_limit')
            elapsed=float(data.time)-time0
            estimate=None
            if not last['target_frozen'] and elapsed>=next_image-1e-9:
                rgb=render_rgb(renderer,data)
                detected=localize_green_target(rgb,calibration,timestamp_s=elapsed)
                observations.append(detected.to_dict())
                estimate={'valid':detected.valid,'xy':detected.xy_m,'timestamp_s':elapsed}
                next_image+=.5
                if not detected.valid:
                    save_overlay(out/'rejected-localization.png',rgb,detected)
            before=data.qpos[:6].copy()
            last=controller.update(before,data.qvel[:6].copy(),elapsed,estimate=estimate)
            if last['status']=='failed':
                if last['failure_reason'] in ('measured_arm_configuration_invalid','current_pose_command_chord_invalid'):
                    status['safety_stop']=True
                raise RuntimeError('controller: '+str(last['failure_reason']))
            if time.monotonic()>=deadline: raise TimeoutError('wall_time_limit_after_controller')
            command=np.asarray(last['command'],dtype=float).copy()
            # Evaluation-only exogenous pulse. Controller does not receive its
            # requested value, onset/offset flags, truth or scoring responses.
            if case['perturbed'] and pulse_count==0 and elapsed>=protocol['perturb_at_elapsed_s']-1e-9:
                if last['stage']!=protocol['perturb_stage']:
                    raise RuntimeError('perturbation_not_in_approach')
                audit=diagnostics(model,data,checker)
                if max(audit['tip_forces_n'])>.02: raise RuntimeError('perturbation_requires_no_contact')
                pulse=np.r_[before[:5]+np.asarray(case['offset_rad']),.5]
                if not validate_joint_path([before[:5],pulse[:5]],checker.is_valid,.005)['valid']:
                    raise RuntimeError('perturbation_rejected_by_guard')
                pulse_before=before.tolist()
            injected=bool(pulse is not None and pulse_count<10)
            if injected:
                command=pulse.copy(); pulse_count+=1
            bounds=model.actuator_ctrlrange
            if (command.shape!=(6,) or not np.isfinite(command).all() or
                    np.any(command<bounds[:,0]) or np.any(command>bounds[:,1])):
                status['safety_stop']=True
                raise RuntimeError('unsafe_command')
            data.ctrl[:]=command
            obstacle=model.geom('approach_obstacle').id
            for _ in range(10):
                mujoco.mj_step(model,data)
                if any(obstacle in (c.geom1,c.geom2) for c in data.contact):
                    obstacle_steps+=1
                    break  # Abort at the first 2 ms contact, before another integration.
            mujoco.mj_forward(model,data)
            row=diagnostics(model,data,checker)
            row.update(stage=last['stage'],elapsed_s=float(data.time)-time0,
                       q6=data.qpos[:6].tolist(),command=command.tolist(),
                       policy_command=np.asarray(last['command']).tolist(),perturbation=injected,
                       target_frozen=last['target_frozen'],replans=last['replans'])
            rows.append(row)
            status=monitor.update(row)
            if injected and pulse_count==10 and pulse_after is None:
                pulse_after=data.qpos[:6].tolist()
            if writer is not None and tick%2==0:
                renderer.update_scene(data,camera='overview')
                writer.append_data(renderer.render()); frame_count+=1
            tick+=1
            if obstacle_steps or status['safety_stop']:
                status['safety_stop']=True
                raise RuntimeError('safety_stop')
            if status['failure_reason']: raise RuntimeError(status['failure_reason'])
            if last['done']:
                break
        else:
            raise TimeoutError('simulation_time_limit')
        if time.monotonic()>=deadline: raise TimeoutError('wall_time_limit')
        status=monitor.report()
        status['passed']=bool(status['passed'] and last['done'] and not obstacle_steps and
                              (not case['perturbed'] or pulse_count==10))
        if not status['passed'] and not status['failure_reason']:
            status['failure_reason']='physical_task_not_complete'
        renderer.update_scene(data,camera='overview')
        Image.fromarray(renderer.render()).save(out/'final.png')
        status.update(controller_done=bool(last['done']),initial_qpos=initial.tolist(),
                      free_object=True,weld_count=int(model.neq),mocap_count=int(model.nmocap))
    except Exception as error:
        if monitor is not None:
            measured=monitor.report()
            measured['safety_stop'] |= status.get('safety_stop',False)
            status.update(measured)
        status.update(passed=False,error_type=type(error).__name__,error=str(error))
        if not status.get('failure_reason'): status['failure_reason']=str(error)
    finally:
        if writer is not None: writer.close()
        if renderer is not None: renderer.close()
        status.update(case=case,wall_s=time.monotonic()-start_wall,steps=len(rows),
                      simulation_s=rows[-1]['elapsed_s'] if rows else 0.,
                      pulse_steps=pulse_count,pulse_before_q6=pulse_before,pulse_after_q6=pulse_after,
                      obstacle_contact_steps=obstacle_steps,video_frames=frame_count,
                      max_lift_m=(max(r['object_z_m'] for r in rows)-baseline_z) if rows else None,
                      final_object_xyz_m=rows[-1]['object_xyz_m'] if rows else None)
        if time.monotonic()>=deadline:
            status.update(passed=False,failure_reason='wall_time_limit')
        if controller is not None:
            status['target_handover']=controller.freeze_record
            write_json(out/'planning.json',controller.plan_reports)
        write_json(out/'trajectory.json',rows)
        write_json(out/'visual-observations.json',observations)
        write_json(out/'report.json',status)
    return status


def run_physical_phase(source, root, out, protocol, phase, variant, deadline):
    cases=protocol[phase]
    reports=[]
    for case in cases:
        if time.monotonic()>=deadline: break
        result=run_physical_episode(source,out/case['id'],protocol,case,deadline,video=phase=='p1')
        reports.append(result)
        print(json.dumps({'case':case['id'],'passed':result['passed'],'reason':result['failure_reason'],
                          'sim_s':result['simulation_s'],'wall_s':result['wall_s']},ensure_ascii=False),flush=True)
    complete=len(reports)==len(cases)
    within_budget=time.monotonic()<deadline
    stops=sum(bool(r['safety_stop']) for r in reports)
    normal=[r for r in reports if not r['case']['perturbed']]
    perturbed=[r for r in reports if r['case']['perturbed']]
    successes=sum(bool(r['passed']) for r in reports)
    passed=complete and within_budget and stops==0 and successes==len(cases)
    if phase=='p3':
        passed=(complete and within_budget and stops==0 and sum(bool(r['passed']) for r in normal)>=20 and
                sum(bool(r['passed']) for r in perturbed)>=17)
    return {'passed':passed,'complete':complete,'planned':len(cases),'attempted':len(reports),
            'successes':successes,'safety_stop':stops,'within_budget':within_budget,
            'normal_successes':sum(bool(r['passed']) for r in normal),'normal_attempted':len(normal),
            'perturbed_successes':sum(bool(r['passed']) for r in perturbed),'perturbed_attempted':len(perturbed),
            'fully_injected':sum(r['pulse_steps']==10 for r in perturbed),
            'rows':reports,'variant':variant,
            'control_scope':'RGB localization then known-static-target contact sequence; q6/qvel6 feedback; no truth control'}


def load_protocol(root):
    path=root/'protocol.json'
    protocol=json.loads(path.read_text())
    checksum=digest(path)
    binding=root/'protocol.sha256'
    if binding.exists():
        if binding.read_text().strip()!=checksum:
            raise ValueError('Protocol changed after freeze')
    else:
        binding.write_text(checksum+'\n')
    return protocol, checksum


def check_phase_prerequisites(root, phase, variant, binding, source_sha256):
    """Prevent test-set reuse and advancement on partial or stale evidence."""
    if phase == 'p0':
        return
    required = ['p0']
    if phase in ('p2', 'p3'):
        required.append('p1-'+variant)
    if phase == 'p3':
        required.append('p2-'+variant)
    for name in required:
        report=json.loads((root/name/'report.json').read_text())
        if not (report.get('passed') and report.get('complete') and report.get('protocol_sha256')==binding):
            raise ValueError('Prerequisite incomplete or failed: '+name)
        if report.get('source_sha256')!=source_sha256:
            raise ValueError('Source model changed after prerequisite: '+name)
        if name == 'p0':
            for f in ('visual_localization.py',):
                if report['code_sha256'][f]!=digest(Path(__file__).parent/f):
                    raise ValueError('Perception changed after P0')
        elif phase=='p3' and name.startswith('p2'):
            if report['code_sha256']!=source_hashes():
                raise ValueError('Implementation changed after development gate')
    if variant=='revision1':
        note=root/'revision-reason.json'
        if not note.is_file():
            raise ValueError('Single revision needs a recorded development cause')
        baseline=[root/name/'report.json' for name in ('p1-baseline','p2-baseline')]
        if not any(p.is_file() and not json.loads(p.read_text()).get('passed') for p in baseline):
            raise ValueError('No failed baseline justifies a revision')
    if phase=='p3':
        lock=root/'final-test-started.json'
        with lock.open('x') as stream:
            json.dump({'variant':variant,'protocol_sha256':binding,'code_sha256':source_hashes()},stream,indent=2)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--phase',choices=['p0','p1','p2','p3'],required=True)
    parser.add_argument('--variant',choices=['baseline','revision1'],default='baseline')
    parser.add_argument('--source',type=Path,default=SOURCE)
    args=parser.parse_args()
    protocol,binding=load_protocol(args.root)
    check_phase_prerequisites(args.root,args.phase,args.variant,binding,digest(args.source))
    ledger_path=args.root/'runtime-budget.json'
    ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else {'spent_wall_s':0,'runs':[]}
    remaining=protocol['total_runtime_wall_s']-ledger['spent_wall_s']
    if remaining<=0: raise RuntimeError('Total pilot runtime budget exhausted')
    out=args.root/(args.phase if args.phase=='p0' else args.phase+'-'+args.variant)
    out.mkdir(exist_ok=False)
    before_hashes=source_hashes()
    before_model=digest(args.source)
    started=time.monotonic()
    report={'passed':False,'complete':False}
    try:
        if args.phase=='p0':
            report=run_p0(args.source,out,protocol,started+remaining)
        else:
            report=run_physical_phase(args.source,args.root,out,protocol,args.phase,args.variant,started+remaining)
    except Exception as error:
        report.update(error_type=type(error).__name__,error=str(error))
    finally:
        elapsed=time.monotonic()-started
        if source_hashes()!=before_hashes or digest(args.source)!=before_model:
            report.update(passed=False,error='Code or model changed during phase')
        report.update(phase=args.phase,variant=args.variant,wall_s=elapsed,protocol_sha256=binding,
                      source_sha256=digest(args.source),code_sha256=source_hashes())
        write_json(out/'report.json',report)
        ledger['spent_wall_s']+=elapsed
        ledger['runs'].append({'phase':args.phase,'variant':args.variant,'wall_s':elapsed,'report':str(out/'report.json')})
        write_json(ledger_path,ledger)
    print(json.dumps({k:v for k,v in report.items() if k not in ('rows','code_sha256')},ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
