"""Bounded RGB localization and contact-grasp pilot; never operates hardware.

Scenario reset and scoring may access object truth. The controller receives
only RGB-derived XY, joint encoder state and declared static geometry.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time
import warnings
import xml.etree.ElementTree as ET

os.environ.setdefault('MUJOCO_GL', 'egl')
import mujoco
import numpy as np
from PIL import Image, ImageDraw
from conservative_collision import ConservativeCollisionChecker as CollisionChecker
from grasp_episode import build_contact_scene, solve_pinch_ik
from learning_env import PhysicalTaskMonitor, diagnostics
from released_object import ReleasedObjectQuery, ReleaseAudit, robot_target_force
from visual_localization import TopDownCalibration, localize_green_target
from support_native import library_metadata

SOURCE = Path(__file__).resolve().parents[2]/'workspaces/so101_ws/src/so101_mujoco/models/so101.xml'


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_hashes():
    root = Path(__file__).parent
    sources = list(root.glob('*.py')) + list(root.glob('support_kernel.cpp'))
    return {p.name: digest(p) for p in sources if not p.name.startswith('test_')}


def native_binding():
    metadata = library_metadata()
    return {key: metadata[key] for key in ('kernel_sha256', 'library_sha256',
                                           'compiler_identity_sha256', 'flags_sha256')}


def record_collision_backend(status, checker, *, batch_sweep=False):
    """Preserve case evidence when provenance verification fails at closeout."""
    status['collision_backend'] = {'method':'conservative_support_projection',
                                   'distance_kind':checker.distance_kind,
                                   'margin_m':checker.margin_m}
    if getattr(checker, 'mesh_box_axis_refinement', False) is True:
        status['collision_backend']['mesh_box_axis_refinement'] = dict(
            checker.mesh_box_refinement_stats)
    try:
        status['collision_backend']['library'] = library_metadata()
    except RuntimeError as error:
        status.update(passed=False, safety_stop=True, native_provenance_error=str(error))
        status['failure_reason'] = status.get('failure_reason') or 'native_runtime_provenance_invalid'
    else:
        if batch_sweep:
            try:
                from sweep_batch import runtime_metadata
                status['collision_backend']['library']['process_sweep_bridge'] = runtime_metadata()
            except Exception as error:
                warnings.warn('Sweep diagnostics unavailable: '+str(error), RuntimeWarning)
                status['collision_backend']['library']['process_sweep_bridge'] = {
                    'available':False, 'diagnostic_error':str(error)}
    finally:
        checker.native.close()


def finalize_episode_video(writer, status, frame_count):
    """Encoding belongs to the case budget and cannot silently pass on failure."""
    if writer is None:
        return
    try:
        writer.close()
        receipt = writer.report()
        status['video_recording'] = receipt
        if (not receipt.get('complete') or receipt.get('captured_frames') != frame_count
                or receipt.get('encoded_frames') != frame_count
                or (status.get('passed') and frame_count == 0)):
            raise RuntimeError('video_recording_incomplete')
    except Exception as error:
        status.update(passed=False, video_recording=writer.report(),
                      video_error_type=type(error).__name__, video_error=str(error))
        status['failure_reason'] = status.get('failure_reason') or 'video_finalize_failed'


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
    fixture_ids={name:model.geom(name).id for name in
                 ('target_collision','p0_occluder','p0_distractor')}
    indices=list(fixture_ids.values())
    fixture_baseline={name:np.asarray(getattr(model,name)[indices]).copy()
                      for name in ('geom_pos','geom_size','geom_rgba')}
    raw_rgb_dir=out/'rgb'
    raw_rgb_dir.mkdir(exist_ok=True)
    renderer=mujoco.Renderer(model,height=480,width=640)
    seen_ids=set()

    def restore_fixture():
        for name,values in fixture_baseline.items():
            getattr(model,name)[indices]=values

    def fixture_geometry(data):
        return {name:{'position_m':np.asarray(data.geom_xpos[index]).tolist(),
                      'model_position_m':np.asarray(model.geom_pos[index]).tolist(),
                      'size_m':np.asarray(model.geom_size[index]).tolist(),
                      'rgba':np.asarray(model.geom_rgba[index]).tolist(),
                      'alpha':float(model.geom_rgba[index,3])}
                for name,index in fixture_ids.items()}

    def save_images(case_id,rgb,estimate):
        raw_path=Path('rgb')/(case_id+'.png')
        Image.fromarray(rgb).save(out/raw_path)
        seen_ids.add(case_id)
        save_overlay(out/(case_id+'.png'),rgb,estimate)
        return raw_path.as_posix()

    rows=[]
    try:
        for case in protocol['p0_positives']:
            if deadline is not None and time.monotonic()>=deadline:
                break
            restore_fixture()
            try:
                data=reset_scene(model,rig,case['initial_xy_m'])
                rgb=render_rgb(renderer,data)
                estimate=localize_green_target(rgb,calibration,timestamp_s=float(data.time))
                truth=data.xpos[model.body('grasp_target').id,:2].copy()
                error=float(np.linalg.norm(np.array(estimate.xy_m)-truth)) if estimate.valid else None
                rows.append({'id':case['id'],'kind':'positive','estimate':estimate.to_dict(),
                             'fixture_xy_m':list(case['initial_xy_m']),
                             'fixture_geometry':fixture_geometry(data),
                             'raw_rgb_path':save_images(case['id'],rgb,estimate),
                             'truth_xy_m':truth.tolist(),'error_m':error,
                             'passed':bool(estimate.valid and error<=protocol['p0_max_xy_error_m'])})
            finally:
                restore_fixture()
        target=fixture_ids['target_collision']
        occluder=fixture_ids['p0_occluder']
        distractor=fixture_ids['p0_distractor']
        for index,case in enumerate(protocol['p0_negatives']):
            if deadline is not None and time.monotonic()>=deadline:
                break
            restore_fixture()
            case_id=f'negative_{index}'
            kind=None
            xy=None
            try:
                if isinstance(case,str):
                    case_id=kind=case
                    xy=[.24,-.13]
                elif isinstance(case,dict):
                    case_id=case.get('id')
                    kind=case.get('kind')
                    xy=case.get('initial_xy_m')
                else:
                    raise ValueError('Negative fixture must be a name or dictionary')
                if (not isinstance(case_id,str) or not case_id or case_id in ('.','..')
                        or any(character.isspace() or not character.isprintable()
                               or character in '/\\' for character in case_id)):
                    raise ValueError('Fixture id must be a safe filename')
                if case_id in seen_ids:
                    raise ValueError('Duplicate fixture id would overwrite saved evidence')
                if kind not in ('missing','half_occluded','fully_occluded','two_candidates'):
                    raise ValueError('Unknown negative fixture')
                if (not isinstance(xy,(list,tuple)) or len(xy)!=2
                        or any(isinstance(value,bool) or not isinstance(value,(int,float))
                               or not math.isfinite(value) for value in xy)):
                    raise ValueError('initial_xy_m must contain two finite numbers')
                xy=[float(value) for value in xy]
            except (TypeError,ValueError,OverflowError) as error:
                rows.append({'id':case_id if isinstance(case_id,str) else f'negative_{index}',
                             'kind':'negative','fixture_kind':kind if isinstance(kind,str) else None,
                             'fixture_error':str(error),'passed':False})
                continue
            try:
                delta=np.asarray(xy)-(.24,-.13)
                model.geom_pos[occluder,:2]+=delta
                model.geom_pos[distractor,:2]+=delta
                if kind=='missing':
                    model.geom_rgba[target,3]=0
                elif kind in ('half_occluded','fully_occluded'):
                    model.geom_rgba[occluder,3]=1
                    if kind=='half_occluded':
                        model.geom_pos[occluder,0]+=.010
                        model.geom_size[occluder,0]=.010
                else:
                    model.geom_rgba[distractor,3]=1
                data=reset_scene(model,rig,xy)
                rgb=render_rgb(renderer,data)
                estimate=localize_green_target(rgb,calibration,timestamp_s=float(data.time))
                rejected=(not estimate.valid and estimate.xy_m is None
                          and estimate.pixel_xy is None and estimate.uncertainty_m is None)
                rows.append({'id':case_id,'kind':'negative','fixture_kind':kind,
                             'fixture_xy_m':xy,'fixture_geometry':fixture_geometry(data),
                             'raw_rgb_path':save_images(case_id,rgb,estimate),
                             'estimate':estimate.to_dict(),'passed':rejected})
            finally:
                restore_fixture()
    finally:
        restore_fixture()
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


def run_physical_episode(source, out, protocol, case, deadline, *, video=False,
                         scene_builder=None, progress_callback=None, cancel_check=None,
                         video_factory=None, video_stride=2, controller_options=None,
                         scene_callback=None, timing=None, evidence_callback=None):
    from episode_gc import DeferredGCWindow
    gc_window = DeferredGCWindow()
    try:
        return _run_physical_episode(source, out, protocol, case, deadline,
            video=video, scene_builder=scene_builder, progress_callback=progress_callback,
            cancel_check=cancel_check, video_factory=video_factory, video_stride=video_stride,
            controller_options=controller_options, scene_callback=scene_callback,
            timing=timing, gc_window=gc_window, evidence_callback=evidence_callback)
    finally:
        gc_window.restore()


def _run_physical_episode(source, out, protocol, case, deadline, *, video=False,
                          scene_builder=None, progress_callback=None, cancel_check=None,
                          video_factory=None, video_stride=2, controller_options=None,
                          scene_callback=None, timing=None, gc_window, evidence_callback=None):
    from visual_grasp_controller import VisualGraspController
    from joint_planner import validate_joint_path
    from deferred_video import DeferredVideo
    from physical_skill_evidence import PhysicalSkillEvidence, deliver_evidence
    out.mkdir(exist_ok=False)
    start_wall=time.monotonic()
    if timing is not None: timing.start()
    case_deadline=start_wall+protocol['max_episode_wall_s']
    deadline=case_deadline if deadline is None else min(deadline,case_deadline)
    rows=[]; observations=[]; frame_count=0; renderer=None; writer=None; monitor=None; controller=None; checker=None
    initialization_planning=None; initialization_sweeps=None; initialization_checker=None
    pulse_count=0; pulse=None; pulse_before=None; pulse_after=None; obstacle_steps=0
    release_audit=ReleaseAudit(); release_samples=[]; reset_record={}
    status={'passed':False,'safety_stop':False,'failure_reason':None}
    model=None; data=None; time0=0.; last={'stage':'initializing'}
    scene_warning=False
    skill_evidence=PhysicalSkillEvidence()
    evidence_warning=False

    def emit_evidence(snapshot):
        nonlocal evidence_warning
        if evidence_callback is None:
            return
        try:
            deliver_evidence(evidence_callback,snapshot)
        except Exception as error:
            if not evidence_warning:
                warnings.warn('WARNING physical evidence display failed: '+str(error))
                evidence_warning=True

    def emit_scene(*, final=False, row=None):
        nonlocal scene_warning
        if scene_callback is None or model is None or data is None:
            return
        try:
            scene_callback(model, data, elapsed_s=float(data.time)-time0,
                           phase=last['stage'], final=final, row=row)
        except Exception as error:
            # Display transport is optional. A disconnected viewer must not
            # change the physical controller, original task result or guards.
            if not scene_warning:
                warnings.warn('WARNING station scene update failed: ' + str(error))
                scene_warning=True
    try:
        emit_evidence(skill_evidence.report())
        if cancel_check is not None:
            cancel_check()
        builder = build_contact_scene if scene_builder is None else scene_builder
        model,rig,_=builder(source,out/'scene',noslip_iterations=10)
        data=reset_scene(model,rig,case['initial_xy_m'])
        time0=float(data.time)
        emit_scene()
        initial=data.qpos.copy()
        baseline_z=float(data.xpos[model.body('grasp_target').id,2])
        place_floor=model.geom('place_floor').id
        reset_record={'initial_qpos':initial.tolist(), 'initial_qvel':data.qvel.copy().tolist(),
                      'place_goal_xy_m':data.geom_xpos[place_floor, :2].tolist(),
                      'place_height_m':float(data.geom_xpos[place_floor, 2]-model.geom_size[place_floor, 2]),
                      'place_support_z_m':float(data.geom_xpos[place_floor, 2]+model.geom_size[place_floor, 2]),
                      'baseline_object_z_m':baseline_z, 'free_object':True,
                      'weld_count':int(model.neq), 'mocap_count':int(model.nmocap)}
        monitor=PhysicalTaskMonitor(baseline_z)
        policy = (controller_options or {}).get('route_policy')
        checker_options = ({'mesh_box_axis_refinement': True}
                           if getattr(policy, 'mesh_box_axis_refinement', False) else {})
        if getattr(policy, 'reuse_refinement_details', False):
            checker_options['reuse_refinement_details'] = True
        checker=CollisionChecker(rig,gripper=.5,margin_m=.001,**checker_options)
        calibration=TopDownCalibration.from_mujoco_model(model,width=640,height=480,top_plane_z_m=.018)
        renderer=mujoco.Renderer(model,height=480,width=640)
        rgb=render_rgb(renderer,data)
        first=localize_green_target(rgb,calibration,timestamp_s=0.0)
        observations.append(first.to_dict())
        save_overlay(out/'initial-localization.png',rgb,first)
        if not first.valid: raise RuntimeError('initial_localization_rejected: '+first.reason)
        released_query=ReleasedObjectQuery(out/'scene/grasp-planning.xml')
        controller=VisualGraspController(rig,first.xy_m,data.qpos[:6].copy(),seed=0,target_timestamp_s=0.0,
                                         released_query=released_query, **(controller_options or {}))
        if video:
            factory = DeferredVideo if video_factory is None else video_factory
            writer=factory(model,out/'grasp-place.mp4',max_frames=2250,deadline=deadline)
        time0=float(data.time); tick=0; next_image=.5
        last={'target_frozen':False,'stage':'approach'}
        if getattr(getattr(controller, 'route_policy', None), 'defer_cyclic_gc', False):
            gc_window.begin()
        if timing is not None: timing.mark('initialization')
        while float(data.time)-time0 < protocol['max_sim_s']-1e-9:
            if timing is not None: timing.begin_cycle(float(data.time)-time0)
            if cancel_check is not None:
                cancel_check()
            if time.monotonic()>=deadline: raise TimeoutError('wall_time_limit')
            elapsed=float(data.time)-time0
            if timing is not None: timing.mark('poll_and_clock')
            estimate=None
            if not last['target_frozen'] and elapsed>=next_image-1e-9:
                rgb=render_rgb(renderer,data)
                detected=localize_green_target(rgb,calibration,timestamp_s=elapsed)
                observations.append(detected.to_dict())
                estimate={'valid':detected.valid,'xy':detected.xy_m,'timestamp_s':elapsed}
                next_image+=.5
                if not detected.valid:
                    save_overlay(out/'rejected-localization.png',rgb,detected)
            if timing is not None: timing.mark('perception')
            before=data.qpos[:6].copy()
            last=controller.update(before,data.qvel[:6].copy(),elapsed,estimate=estimate)
            if timing is not None: timing.mark('controller')
            if last['status']=='failed':
                if last['failure_reason'] in ('measured_arm_configuration_invalid','current_pose_command_chord_invalid',
                                              'measured_closure_sweep_invalid','measured_separation_invalid',
                                              'measured_released_object_clearance_invalid',
                                              'transport_admission_chord_invalid',
                                              'transport_admission_payload_invalid',
                                              'transport_first_command_invalid',
                                              'separation_saved_samples_invalid',
                                              'separation_admission_chord_invalid',
                                              'separation_first_command_invalid',
                                              'return_admission_chord_invalid',
                                              'return_first_command_invalid'):
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
            if last['stage']=='release':
                release_audit.start(data.qpos[6:8])  # Before the first opening command.
            data.ctrl[:]=command
            if (controller.transport_events and controller.transport_events[-1]['event']=='admission'
                    and controller.transport_events[-1]['elapsed_s']==elapsed
                    and controller.transport_events[-1]['accepted']):
                controller.transport_events[-1]['issued']=True
            if (controller.separation_events and controller.separation_events[-1]['event']=='admission'
                    and controller.separation_events[-1]['elapsed_s']==elapsed
                    and controller.separation_events[-1]['accepted']):
                controller.separation_events[-1]['issued']=True
            return_events = getattr(controller, 'return_events', [])
            if (return_events and return_events[-1]['event']=='admission'
                    and return_events[-1]['elapsed_s']==elapsed
                    and return_events[-1]['accepted']):
                return_events[-1]['issued']=True
            obstacle_ids = {model.geom(name).id for name in
                            case.get('obstacle_geom_names', ['approach_obstacle'])}
            release_force_peak=0.
            if timing is not None: timing.mark('command_checks')
            for _ in range(10):
                mujoco.mj_step(model,data)
                if release_audit.anchor is not None:
                    force=robot_target_force(model,data)
                    release_force_peak=max(release_force_peak,force)
                    release_audit.update(data.qpos[6:8],force,float(data.time)-time0)
                    release_samples.append({'elapsed_s':float(data.time)-time0,
                                            'object_xy_m':data.qpos[6:8].tolist(),
                                            'q6':data.qpos[:6].tolist(), 'stage':last['stage'],
                                            'robot_target_force_n':force,
                                            'detached':release_audit.detached})
                    if release_audit.failure_reason:
                        break
                if any(obstacle_ids.intersection((c.geom1,c.geom2)) for c in data.contact):
                    obstacle_steps+=1
                    break  # Abort at the first 2 ms contact, before another integration.
            mujoco.mj_forward(model,data)
            if timing is not None: timing.mark('physics_and_guards')
            row=diagnostics(model,data,checker)
            row.update(stage=last['stage'],elapsed_s=float(data.time)-time0,
                       q6=data.qpos[:6].tolist(),command=command.tolist(),
                       qvel6=data.qvel[:6].tolist(),controller_done=last['done'],
                       policy_command=np.asarray(last['command']).tolist(),perturbation=injected,
                       geometric_reference=np.asarray(last['geometric_reference']).tolist(),
                       servo_offset=np.asarray(last['servo_offset']).tolist(),
                       target_frozen=last['target_frozen'],replans=last['replans'],
                       robot_target_force_peak_n=release_force_peak,
                       released_detached=release_audit.detached)
            rows.append(row)
            if timing is not None: timing.mark('diagnostics_and_record')
            if progress_callback is not None:
                progress_callback(row)
            emit_scene(row=row)
            if timing is not None: timing.mark('callbacks')
            status=monitor.update(row)
            if skill_evidence.observe(row,status,baseline_z) is not None:
                emit_evidence(skill_evidence.report())
            if release_audit.failure_reason:
                status['safety_stop']=True
                raise RuntimeError(release_audit.failure_reason)
            if injected and pulse_count==10 and pulse_after is None:
                pulse_after=data.qpos[:6].tolist()
            if timing is not None: timing.mark('task_monitor')
            if writer is not None and tick%video_stride==0:
                writer.capture(data,tick); frame_count+=1
            if timing is not None: timing.mark('video_capture')
            tick+=1
            if timing is not None: timing.end_cycle(last['stage'], float(data.time)-time0)
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
        status['passed']=bool(status['passed'] and last['done'] and not obstacle_steps and release_audit.report()['passed'] and
                              (not case['perturbed'] or pulse_count==10))
        if not status['passed'] and not status['failure_reason']:
            status['failure_reason']='physical_task_not_complete'
        renderer.update_scene(data,camera='overview')
        Image.fromarray(renderer.render()).save(out/'final.png')
        status.update(controller_done=bool(last['done']),initial_qpos=initial.tolist(),
                      free_object=True,weld_count=int(model.neq),mocap_count=int(model.nmocap))
    except Exception as error:
        initialization_planning=getattr(error,'initialization_planning',None)
        initialization_sweeps=getattr(error,'initialization_sweeps',None)
        initialization_checker=getattr(error,'initialization_checker',None)
        if monitor is not None:
            measured=monitor.report()
            measured['safety_stop'] |= status.get('safety_stop',False)
            status.update(measured)
        status.update(passed=False,error_type=type(error).__name__,error=str(error))
        if not status.get('failure_reason'): status['failure_reason']=str(error)
    finally:
        if timing is not None: timing.begin_cleanup()
        # Capture the actual final physical state even when cancellation or a
        # guard interrupts between sparse updates. Deferred video uses its own
        # MjData and cannot overwrite this terminal scene.
        emit_scene(final=True, row=rows[-1] if rows else None)
        if controller is not None:
            try:
                controller.close()
            except Exception as cleanup_error:
                status.update(passed=False, planner_cleanup_error=str(cleanup_error),
                              planner_cleanup_errors=controller.planner_cleanup_errors)
                if not status.get('failure_reason'):
                    status['failure_reason'] = 'planner_cleanup_failed'
            status['transport_events'] = controller.transport_events
            status['transport_job'] = (dict(controller.transport_job.execution,
                                          state=controller.transport_job.state)
                                       if controller.transport_job is not None else None)
            status['separation_events'] = controller.separation_events
            status['return_events'] = getattr(controller, 'return_events', [])
            return_job = getattr(controller, 'return_job', None)
            status['return_job'] = (dict(return_job.execution, state=return_job.state)
                                    if return_job is not None else None)
            status['separation_job'] = (dict(controller.separation_job.execution,
                                           state=controller.separation_job.state)
                                        if controller.separation_job is not None else None)
            proposal = controller.separation_accepted_plan
            status['separation_proof'] = None if proposal is None else {
                'snapshot': {name: getattr(proposal.snapshot, name) for name in
                             ('q6', 'initial_q6', 'last_command6', 'seed', 'elapsed', 'center', 'uncertainty')},
                'paths': proposal.paths,
                'samples': [{name: getattr(row, name) for name in
                             ('q5', 'pinch3', 'distances', 'pad_vertices')} for row in proposal.samples]}
        if timing is not None: timing.mark('controller_cleanup')
        if gc_window.enabled_before is not None:
            # Existing worker joins precede collection; never collect over a failed join.
            gc_window.finish(collect='planner_cleanup_error' not in status)
            status['gc_scheduling'] = gc_window.details
            if timing is not None: timing.mark('gc_finalize')
        finalize_episode_video(writer,status,frame_count)
        if timing is not None: timing.mark('video_finalize')
        if renderer is not None: renderer.close()
        if timing is not None: timing.mark('renderer_close')
        status.update(case=case,wall_s=time.monotonic()-start_wall,steps=len(rows),
                      release_audit=release_audit.report(),
                      simulation_s=rows[-1]['elapsed_s'] if rows else 0.,
                      pulse_steps=pulse_count,pulse_before_q6=pulse_before,pulse_after_q6=pulse_after,
                      obstacle_contact_steps=obstacle_steps,video_frames=frame_count,
                      max_lift_m=(max(r['object_z_m'] for r in rows)-baseline_z) if rows else None,
                      final_object_xyz_m=rows[-1]['object_xyz_m'] if rows else None)
        status.update(reset_record)
        if time.monotonic()>=deadline:
            status.update(passed=False,failure_reason='wall_time_limit')
        if controller is not None:
            status['target_handover']=controller.freeze_record
            status['release_plan']=controller.release_record
            status['servo_transitions']=controller.servo_transitions
            write_json(out/'planning.json',controller.plan_reports)
            write_json(out/'jaw-sweeps.json',controller.sweep_reports)
            controller.checker.native.close()
        elif initialization_planning is not None:
            write_json(out/'planning.json',initialization_planning)
            write_json(out/'jaw-sweeps.json',initialization_sweeps)
        if initialization_checker is not None:
            initialization_checker.native.close()
        if checker is not None:
            record_collision_backend(status, checker, batch_sweep=bool(
                getattr(getattr(controller, 'route_policy', None), 'batch_configuration_sweep', False)))
        write_json(out/'trajectory.json',rows)
        write_json(out/'release-2ms.json',release_samples)
        write_json(out/'visual-observations.json',observations)
        if timing is not None: timing.mark('artifact_write')
        from episode_gc import peak_rss_kib
        status['process_peak_rss_kib'] = peak_rss_kib()
        status['wall_s'] = time.monotonic()-start_wall
        if time.monotonic()>=deadline:
            status.update(passed=False,failure_reason='wall_time_limit')
        status['skill_evidence']=skill_evidence.finalize(status)
        emit_evidence(status['skill_evidence'])
        write_json(out/'report.json',status)
        if timing is not None: timing.mark('report_write')
    return status


def run_physical_phase(source, root, out, protocol, phase, variant, deadline):
    cases=protocol[phase]
    reports=[]
    for case in cases:
        if deadline is not None and time.monotonic()>=deadline: break
        result=run_physical_episode(source,out/case['id'],protocol,case,deadline,video=phase=='p1')
        reports.append(result)
        print(json.dumps({'case':case['id'],'passed':result['passed'],'reason':result['failure_reason'],
                          'sim_s':result['simulation_s'],'wall_s':result['wall_s']},ensure_ascii=False),flush=True)
    complete=len(reports)==len(cases)
    within_budget=deadline is None or time.monotonic()<deadline
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
    if 'total_runtime_wall_s' in protocol:
        total=protocol['total_runtime_wall_s']
        if total is not None and (isinstance(total,bool) or not isinstance(total,(int,float))
                                  or not math.isfinite(total)):
            raise ValueError('Total runtime wall limit must be a finite number or null')
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
        elif (phase=='p3' and name.startswith('p2')) or (phase=='p2' and name.startswith('p1')):
            if report['code_sha256']!=source_hashes():
                raise ValueError('Implementation changed after development gate')
            if report.get('native_binding') != native_binding():
                raise ValueError('Native collision runtime changed after development gate')
        continuation=root/'continuation.json'
        if name != 'p0' and continuation.is_file() and report.get('continuation_sha256')!=digest(continuation):
            raise ValueError('Continuation criteria changed after prerequisite')
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
            json.dump({'variant':variant,'protocol_sha256':binding,'code_sha256':source_hashes(),
                       'native_binding':native_binding()},stream,indent=2)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--phase',choices=['p0','p1','p2','p3'],required=True)
    parser.add_argument('--variant',choices=['baseline','revision1'],default='baseline')
    parser.add_argument('--source',type=Path,default=SOURCE)
    args=parser.parse_args()
    protocol,binding=load_protocol(args.root)
    continuation=args.root/'continuation.json'
    continuation_hash=digest(continuation) if continuation.is_file() else None
    if continuation_hash is not None:
        if (args.root/'continuation.sha256').read_text().strip()!=continuation_hash:
            raise ValueError('Continuation scope changed after freeze')
        scope=json.loads(continuation.read_text())
        if scope['max_new_physical_variants']==1 and args.variant!='baseline':
            raise ValueError('Continuation permits only one physical variant')
    check_phase_prerequisites(args.root,args.phase,args.variant,binding,digest(args.source))
    ledger_path=args.root/'runtime-budget.json'
    ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else {'spent_wall_s':0,'runs':[]}
    total=protocol['total_runtime_wall_s']
    remaining=None if total is None else total-ledger['spent_wall_s']
    if remaining is not None and remaining<=0:
        raise RuntimeError('Total pilot runtime budget exhausted')
    out=args.root/(args.phase if args.phase=='p0' else args.phase+'-'+args.variant)
    out.mkdir(exist_ok=False)
    before_hashes=source_hashes()
    before_model=digest(args.source)
    started=time.monotonic()
    deadline=None if remaining is None else started+remaining
    report={'passed':False,'complete':False}
    before_native = None
    try:
        if args.phase=='p0':
            report=run_p0(args.source,out,protocol,deadline)
        else:
            before_native = native_binding()
            report=run_physical_phase(args.source,args.root,out,protocol,args.phase,args.variant,deadline)
    except Exception as error:
        report.update(error_type=type(error).__name__,error=str(error))
    finally:
        elapsed=time.monotonic()-started
        if before_native is not None:
            try:
                if native_binding() != before_native:
                    report.update(passed=False,error='Native collision runtime changed during phase')
            except RuntimeError as error:
                report.update(passed=False,error='Native collision runtime unavailable: '+str(error))
        if (source_hashes()!=before_hashes or digest(args.source)!=before_model
                or (continuation_hash is not None and digest(continuation)!=continuation_hash)):
            report.update(passed=False,error='Code or model changed during phase')
        report.update(phase=args.phase,variant=args.variant,wall_s=elapsed,protocol_sha256=binding,
                      native_binding=before_native,
                      continuation_sha256=continuation_hash,
                      source_sha256=digest(args.source),code_sha256=source_hashes())
        write_json(out/'report.json',report)
        ledger['spent_wall_s']+=elapsed
        ledger['runs'].append({'phase':args.phase,'variant':args.variant,'wall_s':elapsed,'report':str(out/'report.json')})
        write_json(ledger_path,ledger)
    print(json.dumps({k:v for k,v in report.items() if k not in ('rows','code_sha256')},ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
