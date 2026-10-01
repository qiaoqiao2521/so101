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


def run_episode(source, output, *, render=False, seed=0, empty_close=False, place=False, noslip_iterations=None):
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
    baseline_z = float(data.xpos[object_id, 2])
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
    def advance(stage, ctrl, steps):
        nonlocal step_count, obstacle_contact_steps, lost_carry_samples
        for index in range(steps):
            data.ctrl[:] = ctrl(index / max(1, steps-1))
            mujoco.mj_step(model, data)
            step_count += 1
            obstacle_id = model.geom('approach_obstacle').id
            obstacle_contact_steps += int(any(obstacle_id in (c.geom1, c.geom2) for c in data.contact))
            if step_count % 10 == 0:
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
    def move(stage, points, jaw):
        points = np.asarray(points)
        lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
        cumulative = np.r_[0, np.cumsum(lengths)]
        total = cumulative[-1]
        # Arc-length interpolation traverses each already validated edge.
        def ctrl(t):
            fraction = t*t*t*(10+t*(-15+6*t))
            distance = fraction*total
            segment = min(np.searchsorted(cumulative, distance, side='right')-1, len(points)-2)
            alpha = (distance-cumulative[segment])/max(lengths[segment], 1e-12)
            return np.r_[points[segment]+alpha*(points[segment+1]-points[segment]), jaw]
        advance(stage, ctrl, max(1000, int(np.ceil(total*1.875/.3/.002))))
        advance(stage, lambda t: np.r_[points[-1], jaw], 300)
    try:
        advance('ready', lambda t: np.r_[start, .5], 500)
        move('approach', planned['path'], .5)
        move('descend', [approach, down], .5)
        advance('close', lambda t: np.r_[down, closed_ctrl], 3000)
        move('lift', [down, lift], closed_ctrl)
        advance('hold', lambda t: np.r_[lift, closed_ctrl], 750)
        if place and grasp_acceptance(rows, baseline_z)['grasp_success']:
            paths, transport_report = plan_transport(model, rig, data, closed_checker, solve_ik=solve_pinch_ik, pinch_point=PINCH_POINT)
            for index, route in enumerate(paths):
                move('lower' if index==len(paths)-1 else 'transport', route, closed_ctrl)
            release_pose = paths[-1][-1]
            advance('release', lambda t: np.r_[release_pose, .5], 3000)
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
    success = all((metrics['grasp_success'], metrics['finite_state'],
                   metrics['obstacle_contact_steps']==0, metrics['invalid_arm_samples']==0))
    if place:
        success = success and metrics['place_success']
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
              'empty_close_negative': empty_close}
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
    args = parser.parse_args()
    if args.output.exists():
        print(json.dumps({'status': 'failed', 'error': 'Output already exists; choose a fresh directory'}))
        return 1
    try:
        report = run_episode(args.source, args.output, render=args.render, empty_close=args.empty_close, place=args.place)
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
