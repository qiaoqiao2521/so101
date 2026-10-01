"""Single-arm obstacle approach and contact-only grasp/lift, entirely local.

Finger pads, friction and a 0.15 Nm jaw cap are explicit simulation fixtures,
not calibrated hardware. The target remains a free body throughout execution.
"""
from __future__ import annotations

import argparse
import ctypes.util
import hashlib
import json
import os
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET

os.environ.setdefault('MUJOCO_GL', 'osmesa' if ctypes.util.find_library('OSMesa') else 'egl')
import mujoco
import numpy as np
from scipy.optimize import least_squares

from collision_scene import CollisionChecker
from grasp_workcell import build_workcell, numbers
from joint_planner import plan_joint_path, validate_joint_path

OBSTACLE = {'pos': (.265, 0, .065), 'size': (.025, .028, .065)}
PINCH_POINT = np.array([.006, 0, -.094])
PAD_NAMES = ('pad_gripper', 'pad_moving_jaw')


def load_policy_prefix(path, cycles, period_s, initial):
    """Read a bounded physical prefix without changing its control cadence."""
    if (not isinstance(cycles, int) or isinstance(cycles, bool) or
            not 1 <= cycles <= 250 or not np.isfinite(period_s) or
            period_s <= 0 or cycles*period_s > 5+1e-9):
        raise ValueError('Policy prefix must span 1..250 cycles and at most five seconds')
    with np.load(path, allow_pickle=False) as archive:
        commands = np.asarray(archive['action'][:cycles], dtype=float)
        times = np.asarray(archive['timestamp'][:cycles], dtype=float)
        next_times = np.asarray(archive['next_timestamp'][:cycles], dtype=float)
        if (commands.shape != (cycles, 6) or not np.isfinite(commands).all() or
                times.shape != (cycles,) or next_times.shape != (cycles,) or
                not np.isfinite(times).all() or not np.isfinite(next_times).all() or
                not np.allclose(next_times-times, period_s, rtol=0, atol=1e-9) or
                not np.allclose(times[1:], next_times[:-1], rtol=0, atol=1e-9)):
            raise ValueError('Policy prefix must contain finite commands at the collection control period')
        for key in ('observation.state', 'observation.environment_state'):
            if not np.allclose(archive[key][0], initial[key], rtol=0, atol=1e-6):
                raise ValueError('Policy prefix initial observations differ from the collection scene')
    return commands


def build_contact_scene(source: Path, output: Path, *, jaw_force_cap_nm=.15, noslip_iterations=0):
    """Refine only finger/target contact; keep hulls for all arm/world checks."""
    _, path = build_workcell(source, output)
    tree = ET.parse(path)
    root = tree.getroot()
    world = root.find('worldbody')
    root.find('option').set('noslip_iterations', str(noslip_iterations))
    for geom in world.iter('geom'):
        if geom.get('contype') == '1' or geom.get('class') == 'collision':
            geom.set('conaffinity', '3')
        if geom.get('name') in ('collision_gripper_1', 'collision_moving_jaw_so101_v1_0'):
            geom.set('conaffinity', '1')
    # Bit 2 restricts target/finger contact to the tip surfaces. Other links
    # and all physical world geoms accept both bits; they still hit the target.
    target = root.find('.//geom[@name="target_collision"]')
    target.set('contype', '2')
    target.set('conaffinity', '2')
    target.set('solref', '.004 1')
    for body, name, pos, size in [
        ('gripper', PAD_NAMES[0], (-.012, 0, -.096), (.004, .006, .008)),
        ('moving_jaw_so101_v1', PAD_NAMES[1], (-.0082, -.0726, .0188), (.004, .008, .006)),
    ]:
        ET.SubElement(root.find(f'.//body[@name="{body}"]'), 'geom', name=name,
                      type='box', pos=numbers(pos), size=numbers(size), mass='0',
                      contype='2', conaffinity='2', group='0', friction='1 .005 .0001',
                      solref='.004 1', rgba='.10 .12 .14 1')
    root.find('actuator')[-1].set('forcerange', numbers([-jaw_force_cap_nm, jaw_force_cap_nm]))
    ET.SubElement(world, 'geom', name='approach_obstacle', type='box',
                  pos=numbers(OBSTACLE['pos']), size=numbers(OBSTACLE['size']),
                  contype='1', conaffinity='3', group='0', rgba='.78 .39 .12 1')
    path = output / 'contact-workcell.xml'
    tree.write(path, encoding='utf-8', xml_declaration=True)
    model = mujoco.MjModel.from_xml_path(str(path))
    # Planning clone: remove just the free target; world/trays/hulls are shared.
    world.remove(world.find('body[@name="grasp_target"]'))
    for geom in world.iter('geom'):
        if geom.get('contype', '0') != '0' or geom.get('class') == 'collision':
            if geom.get('name') not in PAD_NAMES:
                geom.set('group', '3')
    rig_path = output / 'grasp-planning.xml'
    tree.write(rig_path, encoding='utf-8', xml_declaration=True)
    return model, mujoco.MjModel.from_xml_path(str(rig_path)), path


def solve_pinch_ik(model, xyz, initial=None):
    """Five-axis position/vertical-axis IK with a fixed wrist-roll preference.

    Uses its own MjData. Never changes execution qpos, free-body state or ctrl.
    TCP on the original fixed tip is unsuitable as the pinch-centre target.
    """
    query = mujoco.MjData(model)
    body_id = model.body('gripper').id
    lo, hi = model.jnt_range[:5].T
    def residual(q):
        query.qpos[:5] = q
        mujoco.mj_forward(model, query)
        rotation = query.xmat[body_id].reshape(3, 3)
        return np.r_[(query.xpos[body_id] + rotation @ PINCH_POINT - xyz) * 10,
                     rotation[:, 2] - [0, 0, 1], q[4] * .1]
    best = None
    for seed in range(8):
        guess = (np.zeros(5) if initial is None else initial) if seed == 0 else np.random.default_rng(seed).uniform(lo, hi)
        result = least_squares(residual, guess, bounds=(lo+1e-6, hi-1e-6), max_nfev=400)
        if best is None or np.linalg.norm(result.fun) < np.linalg.norm(best.fun):
            best = result
        if np.linalg.norm(best.fun) < 1e-5:
            return best.x.copy()
    raise RuntimeError(f'No vertical pinch IK candidate, residual={np.linalg.norm(best.fun)}')


def grasp_contacts(model, data):
    """Per-tip positive normal forces, evaluated from actual solver contacts."""
    target = model.geom('target_collision').id
    forces = {name: 0.0 for name in PAD_NAMES}
    for index, contact in enumerate(data.contact):
        if target not in (contact.geom1, contact.geom2):
            continue
        other = contact.geom2 if contact.geom1 == target else contact.geom1
        name = model.geom(int(other)).name
        if name in forces:
            wrench = np.zeros(6)
            mujoco.mj_contactForce(model, data, index, wrench)
            forces[name] += max(0.0, float(wrench[0]))
    return forces


def grasp_acceptance(rows, baseline_z):
    """Reject air closes, impacts, unsupported one-tip lifts and transient tosses."""
    hold = [row for row in rows if row['stage'] == 'hold']
    held = [r for r in hold if r['object_z_m'] - baseline_z >= .025
            and min(r['tip_forces_n']) > .02 and not r['floor_contact']]
    duration = held[-1]['time_s'] - held[0]['time_s'] if len(held) == len(hold) and len(held) > 1 else 0.0
    return {'grasp_success': duration >= 1.0, 'lift_success': duration >= 1.0,
            'hold_duration_s': duration,
            'final_lift_m': hold[-1]['object_z_m'] - baseline_z if hold else 0,
            'obstacle_contact_samples': sum(r['obstacle_contact'] for r in rows),
            'invalid_arm_samples': sum(not r['arm_valid'] for r in rows),
            'finite_state': bool(rows) and all(r['finite_state'] for r in rows)}


def run_episode(source, output, *, render=False, seed=0, empty_close=False, place=False, noslip_iterations=None,
                record_dataset=False, control_period_s=.02, perturb_rad=0.0,
                perturb_duration_s=.2, perturb_at_fraction=0.0,
                perturb_offset_rad=None, reference_route=None, approach_lookahead_rad=0.0,
                recovery_prefix_npz=None, prefix_control_cycles=0):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    from placement import plan_transport, placement_acceptance, object_inside_tray
    if noslip_iterations is None:
        noslip_iterations = 10 if place else 0
    if not isinstance(noslip_iterations, int) or isinstance(noslip_iterations, bool) or noslip_iterations < 0:
        raise ValueError('noslip_iterations must be a nonnegative integer')
    jaw_cap = .15
    closed_ctrl = .015
    model, rig, path = build_contact_scene(Path(source), output, jaw_force_cap_nm=jaw_cap, noslip_iterations=noslip_iterations)
    start = solve_pinch_ik(rig, np.array([.24, .14, .06]))
    approach = solve_pinch_ik(rig, np.array([.24, -.13, .06]), start)
    down = solve_pinch_ik(rig, np.array([.24, -.13, .019]), approach)
    lift = solve_pinch_ik(rig, np.array([.24, -.13, .06]), down)
    checker = CollisionChecker(rig, gripper=.5, margin_m=.001)
    direct = validate_joint_path([start, approach], checker.is_valid, .015)
    route_hash = None
    if reference_route is not None:
        reference = json.loads(Path(reference_route).read_text())
        route_hash = hashlib.sha256(Path(reference_route).read_bytes()).hexdigest()
        points = np.asarray(reference['planning']['path'], dtype=float)
        if (reference['source_sha256'] != hashlib.sha256(Path(source).read_bytes()).hexdigest()
                or points.ndim != 2 or points.shape[1] != 5
                or not np.allclose(points[0], start, atol=1e-5)
                or not np.allclose(points[-1], approach, atol=1e-5)
                or not validate_joint_path(points, checker.is_valid, .015)['valid']):
            raise ValueError('Reference route does not match the current model/workcell')
        planned = {'status': 'solved', 'path': points.tolist(), 'kind': 'validated_reference_route',
                   'reference_sha256': route_hash}
    else:
        planned = plan_joint_path(start, approach, checker.bounds, checker.is_valid,
                                  seed=seed, timeout_s=10, resolution_rad=.015)
    if planned['status'] != 'solved':
        raise RuntimeError(f'Obstacle planning failed: {planned}')
    descent = validate_joint_path([approach, down], checker.is_valid, .015)
    closed_checker = CollisionChecker(rig, gripper=.025, margin_m=.001)
    ascent = validate_joint_path([down, lift], closed_checker.is_valid, .015)
    if direct['valid'] or not descent['valid'] or not ascent['valid']:
        raise RuntimeError(f'Expected blocked direct approach and clear grasp legs: {direct}, {descent}, {ascent}')
    data = mujoco.MjData(model)
    data.qpos[:6] = np.r_[start, .5]
    data.ctrl[:] = data.qpos[:6]
    mujoco.mj_forward(model, data)
    # Reset-only negative fixture: move object away before any physics step.
    if empty_close:
        data.qpos[6:9] = [.24, -.17, .012]
        mujoco.mj_forward(model, data)
    for _ in range(500):
        mujoco.mj_step(model, data)
    object_id = model.body('grasp_target').id
    mujoco.mj_forward(model, data)
    baseline_z = float(data.xpos[object_id, 2])
    recorder = monitor = None
    recovery_report = None
    ticks = round(control_period_s/model.opt.timestep)
    if ticks < 1 or not np.isclose(ticks*model.opt.timestep, control_period_s):
        raise ValueError('Control period must be integral physics steps')
    if not 0 <= perturb_rad <= .0872665:
        raise ValueError('Perturbation must lie between 0 and 5 degrees')
    if not 0 <= perturb_at_fraction < 1:
        raise ValueError('Perturbation fraction must be in [0,1)')
    if record_dataset and (perturb_duration_s < control_period_s or not np.isclose(
            perturb_duration_s/control_period_s, round(perturb_duration_s/control_period_s))):
        raise ValueError('Perturbation duration must span integral control periods')
    if perturb_offset_rad is not None:
        perturb_offset_rad = np.asarray(perturb_offset_rad, dtype=float)
        if perturb_offset_rad.shape != (5,) or not np.isfinite(perturb_offset_rad).all() or np.max(np.abs(perturb_offset_rad)) > .0872665:
            raise ValueError('Explicit perturbation must be five finite offsets, bounded by five degrees')
    if (not np.isfinite(approach_lookahead_rad) or not 0 <= approach_lookahead_rad <= .015
            or (approach_lookahead_rad and not record_dataset)):
        raise ValueError('Approach lookahead requires dataset collection and a distance in (0,.015] rad')
    if (not isinstance(prefix_control_cycles, int) or isinstance(prefix_control_cycles, bool) or
            bool(recovery_prefix_npz) != bool(prefix_control_cycles) or
            (recovery_prefix_npz and (not record_dataset or not approach_lookahead_rad or
                                     not 1 <= prefix_control_cycles <= 250 or
                                     prefix_control_cycles*control_period_s > 5+1e-9 or perturb_rad or
                                     perturb_offset_rad is not None or perturb_at_fraction))):
        raise ValueError('Policy-prefix recovery requires reactive collection and 1..250 cycles within five seconds')
    prefix_config = ({'source_sha256': hashlib.sha256(Path(recovery_prefix_npz).read_bytes()).hexdigest(),
                      'source': str(recovery_prefix_npz), 'control_cycles': prefix_control_cycles,
                      'commands_are_training_labels': False} if recovery_prefix_npz else None)
    if record_dataset:
        from learning_data import EpisodeRecorder
        from learning_env import observe, PhysicalTaskMonitor
        monitor = PhysicalTaskMonitor(baseline_z)
        metadata = {'control_period_s': control_period_s, 'physics_dt_s': float(model.opt.timestep),
                    'seed': seed, 'model_sha256': hashlib.sha256(Path(source).read_bytes()).hexdigest(),
                    'scene_configuration': {'jaw_force_cap_nm': jaw_cap, 'noslip_iterations': noslip_iterations,
                                            'baseline_object_z_m': baseline_z, 'obstacle': OBSTACLE},
                    'initial_snapshot': {'qpos': data.qpos.tolist(), 'qvel': data.qvel.tolist(),
                                         'ctrl': data.ctrl.tolist(), 'time_s': float(data.time),
                                         'qacc_warmstart': data.qacc_warmstart.tolist()},
                    'angular_velocity_frame': 'MuJoCo free-joint local rotational velocity',
                    'collection_kind': 'bounded perturbation and expert replanning; not fitted DART noise',
                    'collector_version': ('state-conditioned-v5-policy-recovery' if recovery_prefix_npz else
                                          'state-conditioned-v4-approach-reactive' if approach_lookahead_rad else
                                          'state-conditioned-v3'),
                    'policy_deviation_prefix': prefix_config,
                    'approach_motion': {'kind': 'state_projection_lookahead' if approach_lookahead_rad else 'timed_minimum_jerk',
                                        'lookahead_joint_norm_rad': approach_lookahead_rad,
                                        'endpoint_max_joint_error_rad': .0015 if approach_lookahead_rad else None,
                                        'other_motion': 'timed_minimum_jerk'},
                    'reference_route_sha256': route_hash,
                    'expert_jaw_rules': {'close_tcp_height_over_object_m': .010, 'release_object_z_m': .0145,
                                         'move_endpoint_dwell_s': 0.0},
                    'perturb_duration_s': perturb_duration_s,
                    'perturb_at_fraction': perturb_at_fraction}
        recorder = EpisodeRecorder(output/'expert.h5', metadata)
    renderer = mujoco.Renderer(model, height=720, width=1280) if render else None
    camera = mujoco.MjvCamera()
    camera.lookat[:] = [.22, -.025, .15]
    camera.distance, camera.azimuth, camera.elevation = 1.08, 132, -27
    writer = None
    closeup_writer = None
    if render:
        import imageio.v2 as imageio
        writer = imageio.get_writer(output / 'obstacle-grasp.mp4', fps=25, codec='libx264', quality=8)
        closeup_writer = imageio.get_writer(output / 'grasp-closeup.mp4', fps=25, codec='libx264', quality=8)
    rows, step_count, obstacle_contact_steps = [], 0, 0
    lost_carry_samples = 0
    transport_report = None
    delivery_writer = None
    if render and place:
        delivery_writer = imageio.get_writer(output/'transport-place.mp4', fps=25, codec='libx264', quality=8)
    def advance(stage, ctrl, steps, *, label_valid=True, perturbation=False, stop_at_fraction=None):
        nonlocal step_count, obstacle_contact_steps, lost_carry_samples
        if recorder is not None:
            steps = int(np.ceil(steps/ticks))*ticks
        for index in range(steps):
            if recorder is None or index % ticks == 0:
                if recorder is not None:
                    obs_before = observe(model, data)
                command = np.asarray(ctrl(index / max(1, steps-1)), dtype=float)
                data.ctrl[:] = command
            mujoco.mj_step(model, data)
            step_count += 1
            obstacle_id = model.geom('approach_obstacle').id
            obstacle_contact_steps += int(any(obstacle_id in (c.geom1, c.geom2) for c in data.contact))
            if recorder is not None and (index+1) % ticks == 0:
                obs_after = observe(model, data)
                recorder.append(obs_before, command, command, obs_after,
                                label_valid=label_valid, stage=stage, perturbation=perturbation)
            if step_count % 10 == 0:
                if recorder is not None and (index+1) % ticks != 0:
                    mujoco.mj_forward(model, data)
                names = [(model.geom(c.geom1).name, model.geom(c.geom2).name) for c in data.contact]
                forces = grasp_contacts(model, data)
                if stage == 'transport':
                    lost_carry_samples = lost_carry_samples+1 if min(forces.values()) < .02 else 0
                rows.append({'time_s': float(data.time), 'stage': stage,
                             'object_z_m': float(data.xpos[object_id, 2]),
                             'object_xyz_m': data.xpos[object_id].tolist(),
                             'object_speed_m_s': float(np.linalg.norm(data.qvel[6:9])),
                             'in_place_tray': bool(object_inside_tray(data.xmat[object_id].reshape(3,3), data.xpos[object_id])),
                             'place_floor_contact': any('target_collision' in p and 'place_floor' in p for p in names),
                             'tip_forces_n': list(forces.values()),
                             'floor_contact': any('target_collision' in p and ('pick_floor' in p or 'worktable' in p) for p in names),
                             'obstacle_contact': any('approach_obstacle' in p for p in names),
                             'arm_valid': checker.evaluate(data.qpos[:6], require_fixed_gripper=False)['valid'],
                             'finite_state': bool(np.all(np.isfinite(data.qpos)) and np.all(np.isfinite(data.qvel)))})
                if monitor is not None:
                    measured = monitor.update(rows[-1])
                    if measured['failure_reason']:
                        raise RuntimeError('Physical acceptance stopped: '+measured['failure_reason'])
            if lost_carry_samples >= 5:
                raise RuntimeError('Payload lost during transport; execution stopped')
            if render and step_count % 20 == 0:
                renderer.update_scene(data, camera=camera)
                writer.append_data(renderer.render())
                if stage in ('close', 'lift', 'hold'):
                    detail = mujoco.MjvCamera()
                    detail.lookat[:] = [.24, -.13, .06]
                    detail.distance, detail.azimuth, detail.elevation = .43, 140, -20
                    renderer.update_scene(data, camera=detail)
                    closeup_writer.append_data(renderer.render())
                if delivery_writer is not None and stage in ('transport', 'lower', 'release', 'retreat', 'settle'):
                    detail = mujoco.MjvCamera()
                    detail.lookat[:] = [.23, .025, .09]
                    detail.distance, detail.azimuth, detail.elevation = .66, 132, -27
                    renderer.update_scene(data, camera=detail)
                    delivery_writer.append_data(renderer.render())
            if stop_at_fraction is not None and (index+1) % ticks == 0 and index/max(1, steps-1) >= stop_at_fraction:
                return index/max(1, steps-1)
        return 1.0

    def moving_jaw(stage, jaw):
        if recorder is None:
            return jaw
        if stage == 'descend':
            gripper = model.body('gripper').id
            pinch = data.xpos[gripper]+data.xmat[gripper].reshape(3,3) @ PINCH_POINT
            target = data.xpos[object_id]
            # Observable geometry triggers the transition before a stationary
            # endpoint can receive both open and closed expert labels.
            if np.linalg.norm(pinch[:2]-target[:2]) < .002 and pinch[2] < target[2]+.010:
                return closed_ctrl
        if stage == 'lower':
            target = data.xpos[object_id]
            if (object_inside_tray(data.xmat[object_id].reshape(3,3), target)
                    and target[2] < .0145):
                return .5
        return jaw

    def move(stage, points, jaw, *, stop_at_fraction=None):
        points = np.asarray(points)
        lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
        cumulative = np.r_[0, np.cumsum(lengths)]
        total = cumulative[-1]
        if recorder is not None and stage == 'approach' and approach_lookahead_rad:
            from expert_path import joint_path_lookahead
            # Progress depends on the actual pose, never on the loop counter.
            # The clock only caps a failed attempt. Recheck every off-path chord.
            budget_cycles = int(np.ceil((total/.05+10)/control_period_s))
            for _ in range(budget_cycles):
                actual = data.qpos[:5].copy()
                target, _ = joint_path_lookahead(points, actual, approach_lookahead_rad)
                chord = validate_joint_path([actual, target], checker.is_valid, .005)
                if not chord['valid']:
                    raise RuntimeError('Reactive approach lookahead chord is invalid')
                advance(stage, lambda t: np.r_[target, moving_jaw(stage, jaw)], ticks)
                _, fraction = joint_path_lookahead(points, data.qpos[:5], approach_lookahead_rad)
                if stop_at_fraction is not None and fraction >= stop_at_fraction:
                    return fraction
                if (np.max(np.abs(data.qpos[:5]-points[-1])) <= .0015
                        and np.linalg.norm(data.qvel[:5]) < .05):
                    return 1.0
            raise RuntimeError('Reactive approach did not converge before its physical budget')
        # Arc-length interpolation traverses each already validated edge.
        def ctrl(t):
            fraction = t*t*t*(10+t*(-15+6*t))
            distance = fraction*total
            segment = min(np.searchsorted(cumulative, distance, side='right')-1, len(points)-2)
            alpha = (distance-cumulative[segment])/max(lengths[segment], 1e-12)
            return np.r_[points[segment]+alpha*(points[segment+1]-points[segment]), moving_jaw(stage, jaw)]
        reached = advance(stage, ctrl, max(1000, int(np.ceil(total*1.875/.3/.002))),
                          stop_at_fraction=stop_at_fraction)
        if recorder is None:
            advance(stage, lambda t: np.r_[points[-1], jaw], 300)
        return reached

    def recover(suffix, *, apply_noise=True):
        nonlocal recovery_report, approach, down, lift, descent, ascent, planned
        before = observe(model, data)
        if max(grasp_contacts(model, data).values()) > .02:
            raise RuntimeError('Perturbation requires a contact-free approach')
        offset = (np.random.default_rng(seed).uniform(-perturb_rad, perturb_rad, 5)
                  if perturb_offset_rad is None else perturb_offset_rad)
        displaced = data.qpos[:5].copy()+offset
        checked = validate_joint_path([data.qpos[:5].copy(), displaced], checker.is_valid, .005)
        if not checked['valid']:
            raise RuntimeError('Bounded perturbation rejected by collision/limit guard')
        if apply_noise:
            advance('perturbation', lambda t: np.r_[displaced, .5], round(perturb_duration_s/model.opt.timestep),
                    label_valid=False, perturbation=True)
        after = observe(model, data)
        # Label the moving state immediately. Native position-servo damping
        # brakes against its measured current pose without changing qpos.
        brake_pose = data.qpos[:5].copy()
        advance('recovery_brake', lambda t: np.r_[brake_pose, .5], ticks)
        actual_start = data.qpos[:5].copy()
        current_xyz = data.xpos[object_id].copy()
        approach = solve_pinch_ik(rig, np.r_[current_xyz[:2], .06], actual_start)
        down = solve_pinch_ik(rig, np.r_[current_xyz[:2], .019], approach)
        lift = solve_pinch_ik(rig, np.r_[current_xyz[:2], .06], down)
        anchor = np.asarray(suffix[0])
        local = validate_joint_path([actual_start, anchor], checker.is_valid, .005)
        if local['valid']:
            reconnect = [actual_start.tolist(), anchor.tolist()]
        else:
            query = plan_joint_path(actual_start, anchor, checker.bounds, checker.is_valid,
                                    seed=seed, timeout_s=10, resolution_rad=.005)
            if query['status'] != 'solved':
                raise RuntimeError('Expert failed to reconnect actual perturbed pose to reference route')
            reconnect = query['path']
        repaired = np.vstack([np.asarray(reconnect), np.asarray(suffix)[1:]])
        if not np.allclose(repaired[-1], approach, atol=1e-8):
            bridge = validate_joint_path([repaired[-1], approach], checker.is_valid, .005)
            if not bridge['valid']:
                raise RuntimeError('Reference suffix and fresh IK endpoint have an invalid seam')
            repaired = np.vstack([repaired, approach])
        if not validate_joint_path(repaired, checker.is_valid, .005)['valid']:
            raise RuntimeError('Recovery suffix rejected by independent collision check')
        descent = validate_joint_path([approach, down], checker.is_valid, .015)
        ascent = validate_joint_path([down, lift], closed_checker.is_valid, .015)
        if not descent['valid'] or not ascent['valid']:
            raise RuntimeError('Perturbed recovery grasp legs rejected')
        planned = {'status': 'solved', 'path': repaired.tolist(), 'kind': 'actual_pose_reference_suffix_recovery',
                   'reference_sha256': route_hash}
        recovery_report = {'kind': 'physical_joint_command_then_expert_replan',
                           'requested_offset_rad': offset.tolist(),
                           'actual_displacement_rad': (after['observation.state']-before['observation.state']).tolist(),
                           'first_correction_velocity_rad_s': after['observation.environment_state'][:6].tolist(),
                           'brake_target_rad': brake_pose.tolist(),
                           'planning_start_rad': actual_start.tolist(),
                           'object_xyz_at_replan_m': current_xyz.tolist(),
                           'perturb_duration_s': perturb_duration_s,
                           'perturb_at_fraction': perturb_at_fraction,
                           'reference_route_sha256': route_hash,
                           'policy_deviation_prefix': prefix_config,
                           'perturbation_labels_used': False}
        return repaired
    try:
        if recorder is None:
            advance('ready', lambda t: np.r_[start, .5], 500)
        route = np.asarray(planned['path'])
        inject = recorder is not None and (perturb_rad or perturb_offset_rad is not None)
        if recovery_prefix_npz:
            from expert_path import joint_path_lookahead
            commands = load_policy_prefix(recovery_prefix_npz, prefix_control_cycles,
                                          control_period_s, observe(model, data))
            for command in commands:
                if (max(grasp_contacts(model, data).values()) > .02 or
                        data.xpos[object_id, 2]-baseline_z > .005):
                    raise RuntimeError('Policy-prefix deviation must remain before contact/lift')
                if (np.max(np.abs(command[:5]-data.qpos[:5])) > .0872665 or
                        not checker.evaluate(command, require_fixed_gripper=False)['valid'] or
                        not validate_joint_path([data.qpos[:5].copy(), command[:5]], checker.is_valid, .005)['valid']):
                    raise RuntimeError('Policy-prefix command or its physical connection is unsafe')
                advance('policy_deviation', lambda t: command, ticks, label_valid=False, perturbation=True)
            actual = data.qpos[:5].copy()
            _, fraction = joint_path_lookahead(route, actual, approach_lookahead_rad)
            lengths = np.linalg.norm(np.diff(route, axis=0), axis=1)
            cumulative = np.r_[0, np.cumsum(lengths)]
            segment = min(np.searchsorted(cumulative, fraction*cumulative[-1], side='right')-1, len(route)-2)
            prefix_config.update(actual_q_after_prefix_rad=actual.tolist(),
                                 actual_qvel_after_prefix_rad_s=data.qvel[:5].tolist(),
                                 projected_reference_fraction=fraction)
            route = recover(route[segment+1:], apply_noise=False)
            move('approach', route, .5)
        elif inject and perturb_at_fraction == 0:
            route = recover(route[1:])
            move('approach', route, .5)
        elif inject:
            reached = move('approach', route, .5, stop_at_fraction=perturb_at_fraction)
            lengths = np.linalg.norm(np.diff(route, axis=0), axis=1)
            cumulative = np.r_[0, np.cumsum(lengths)]
            distance = (reached if approach_lookahead_rad else
                        reached**3*(10+reached*(-15+6*reached)))*cumulative[-1]
            segment = min(np.searchsorted(cumulative, distance, side='right')-1, len(route)-2)
            route = recover(route[segment+1:])
            move('approach', route, .5)
        else:
            move('approach', route, .5)
        move('descend', [approach, down], .5)
        if recorder is None:
            advance('close', lambda t: np.r_[down, closed_ctrl], 3000)
        else:
            # Actual dual contact, rather than a hidden six-second stage clock,
            # triggers lifting. The clock only limits a failed grasp attempt.
            for _ in range(round(6/control_period_s)):
                advance('close', lambda t: np.r_[down, closed_ctrl], ticks)
                if min(grasp_contacts(model, data).values()) > .02 and abs(data.qvel[5]) < .05:
                    break
            else:
                raise RuntimeError('No stable dual-finger contact before close timeout')
        move('lift', [down, lift], closed_ctrl)
        if recorder is None:
            advance('hold', lambda t: np.r_[lift, closed_ctrl], 750)
        elif not place:
            advance('hold', lambda t: np.r_[lift, closed_ctrl], 750)
        grasp_ready = (min(grasp_contacts(model, data).values()) > .02 and
                       data.xpos[object_id, 2]-baseline_z >= .025)
        if place and (grasp_ready if recorder is not None else grasp_acceptance(rows, baseline_z)['grasp_success']):
            paths, transport_report = plan_transport(model, rig, data, closed_checker, solve_ik=solve_pinch_ik, pinch_point=PINCH_POINT)
            for index, route in enumerate(paths):
                move('lower' if index==len(paths)-1 else 'transport', route, closed_ctrl)
            release_pose = paths[-1][-1]
            if recorder is None:
                advance('release', lambda t: np.r_[release_pose, .5], 3000)
            else:
                for _ in range(round(6/control_period_s)):
                    advance('release', lambda t: np.r_[release_pose, .5], ticks)
                    if (grasp_contacts(model, data)['pad_moving_jaw'] < .02 and data.qpos[5] > .45
                            and rows[-1]['place_floor_contact']):
                        break
                else:
                    raise RuntimeError('Release failed before timeout')
            retreat_check = validate_joint_path([release_pose, start], checker.is_valid, .01)
            if not retreat_check['valid']:
                raise RuntimeError('Open-jaw retreat collides with workcell')
            move('retreat', [release_pose, start], .5)
            advance('settle', lambda t: np.r_[start, .5], 750)
        if render:
            import imageio.v2 as imageio
            camera.lookat[:] = [.24, .14 if place else -.13, .06]
            camera.distance, camera.azimuth, camera.elevation = .43, 140, -20
            renderer.update_scene(data, camera=camera)
            imageio.imwrite(output/('placed_detail.png' if place else 'grasp_detail.png'), renderer.render())
    except Exception as error:
        if recorder is not None:
            recorder.finalize({'passed': False, 'error_type': type(error).__name__, 'error': str(error),
                               'recovery': recovery_report, 'physical_acceptance': monitor.report()})
        raise
    finally:
        (output/'trajectory.json').write_text(json.dumps(rows)+'\n')
        if writer is not None:
            writer.close()
        if closeup_writer is not None:
            closeup_writer.close()
        if delivery_writer is not None:
            delivery_writer.close()
        if renderer is not None:
            renderer.close()
    metrics = grasp_acceptance(rows, baseline_z)
    metrics['obstacle_contact_steps'] = obstacle_contact_steps
    if place:
        metrics.update(placement_acceptance(rows))
    if monitor is not None and place:
        metrics.update(monitor.report())
        metrics['lift_success'] = metrics['grasp_success']
        metrics['maximum_lift_m'] = max((r['object_z_m']-baseline_z for r in rows), default=0)
        metrics['final_lift_m'] = rows[-1]['object_z_m']-baseline_z if rows else 0
    success = all((metrics['grasp_success'], metrics['finite_state'],
                   metrics['obstacle_contact_steps']==0, metrics['invalid_arm_samples']==0))
    if place:
        success = success and metrics['place_success']
    if monitor is not None and place:
        success = success and metrics['passed']
    report = {'status': 'passed' if success else 'failed', 'kind': 'so101_obstacle_contact_grasp',
              'metrics': metrics, 'direct_approach': direct, 'planning': planned,
              'place_requested': place, 'transport_planning': transport_report,
              'descent_validation': descent, 'ascent_validation': ascent,
              'baseline_object_z_m': baseline_z, 'simulation_seconds': float(data.time),
              'free_target': True, 'weld_count': int(model.neq), 'arm_count': 1,
              'source_sha256': hashlib.sha256(Path(source).read_bytes()).hexdigest(),
              'assumptions': {'contact_pads_m': [ .008, .012, .016], 'jaw_force_cap_nm': jaw_cap,
                              'target_mass_kg': .01, 'friction': 1.0, 'minimum_lift_m': .025,
                              'noslip_iterations': noslip_iterations,
                              'collision_sampling_s': .02, 'planner_edge_resolution_rad': .015},
              'empty_close_negative': empty_close, 'learning_dataset': recorder is not None,
              'expert_recovery': recovery_report}
    if recorder is not None:
        recorder.finalize({'passed': bool(success), 'metrics': metrics, 'recovery': recovery_report})
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    (output/'trajectory.json').write_text(json.dumps(rows)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[2]/'workspaces/so101_ws/src/so101_mujoco/models/so101.xml')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent/'output'/f'grasp-{uuid.uuid4().hex}')
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--place', action='store_true', help='Transport to blue tray, release and retreat')
    parser.add_argument('--empty-close', action='store_true')
    parser.add_argument('--record-dataset', action='store_true')
    parser.add_argument('--control-period-s', type=float, default=.02)
    parser.add_argument('--perturb-rad', type=float, default=0.0)
    parser.add_argument('--perturb-duration-s', type=float, default=.2)
    parser.add_argument('--perturb-at-fraction', type=float, default=0.0)
    parser.add_argument('--perturb-offset-rad', type=float, nargs=5)
    parser.add_argument('--reference-route', type=Path)
    parser.add_argument('--approach-lookahead-rad', type=float, default=0.0,
                        help='Explicit reactive expert collection ablation; zero preserves timed approach')
    parser.add_argument('--recovery-prefix-npz', type=Path,
                        help='Recorded safe policy commands to physically realize before expert recovery')
    parser.add_argument('--prefix-control-cycles', type=int, default=0)
    args = parser.parse_args()
    if args.output.exists():
        print(json.dumps({'status': 'failed', 'error': 'Output already exists; choose a fresh directory'}))
        return 1
    try:
        report = run_episode(args.source, args.output, render=args.render, empty_close=args.empty_close, place=args.place,
                             record_dataset=args.record_dataset, control_period_s=args.control_period_s,
                             perturb_rad=args.perturb_rad, perturb_duration_s=args.perturb_duration_s,
                             perturb_at_fraction=args.perturb_at_fraction,
                             perturb_offset_rad=args.perturb_offset_rad, reference_route=args.reference_route,
                             approach_lookahead_rad=args.approach_lookahead_rad,
                             recovery_prefix_npz=args.recovery_prefix_npz,
                             prefix_control_cycles=args.prefix_control_cycles)
    except Exception as error:
        # Preserve failed setup/planning evidence; never overwrite a prior run.
        failure = {'status': 'failed', 'error_type': type(error).__name__, 'error': str(error)}
        if args.output.is_dir() and not (args.output/'report.json').exists():
            (args.output/'report.json').write_text(json.dumps(failure, indent=2)+'\n')
        print(json.dumps(failure, indent=2))
        return 1
    print(json.dumps({'status': report['status'], 'metrics': report['metrics'], 'output': str(args.output)}, indent=2))
    return 0 if report['status']=='passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
