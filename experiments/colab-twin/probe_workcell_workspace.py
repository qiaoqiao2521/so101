"""Offline SO101 pinch-point screen; no physics steps or admission decision.

Pass a six-joint planning model to ``probe_workspace`` to reuse a caller's
scene. The CLI can load that planning scene or invoke the existing contact
scene builder from the original arm source. It never edits the source MJCF.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

import mujoco
import numpy as np

from conservative_collision import ConservativeCollisionChecker as CollisionChecker
from grasp_episode import PINCH_POINT, build_contact_scene, solve_pinch_ik
from grasp_workcell import PICK_CENTER
from joint_planner import validate_joint_path


REFERENCE_START_M = (.24, .14, .06)
STAGES = (('approach', .06, .5), ('down', .019, .5), ('lift', .06, .015))
MARGIN_M = .001
GRASP_RESOLUTION_RAD = .005
DIRECT_RESOLUTION_RAD = .015
DEFAULT_POINTS = (
    ('center', 0., 0.),
    ('inside_x_minus_9mm', -.009, 0.), ('inside_x_plus_9mm', .009, 0.),
    ('inside_y_minus_9mm', 0., -.009), ('inside_y_plus_9mm', 0., .009),
    ('boundary_x_plus_10mm', .010, 0.), ('boundary_y_minus_10mm', 0., -.010),
    ('outside_x_minus_20mm', -.020, 0.), ('outside_x_plus_20mm', .020, 0.),
    ('outside_y_minus_20mm', 0., -.020), ('outside_y_plus_20mm', 0., .020),
)


def default_points():
    return [{'id': name, 'xy_m': [PICK_CENTER[0]+dx, PICK_CENTER[1]+dy]}
            for name, dx, dy in DEFAULT_POINTS]


def normalize_points(points):
    """Reject ambiguous input before starting a batch of independent points."""
    result, identifiers = [], set()
    for point in points:
        ident = point.get('id')
        if not isinstance(ident, str) or not ident.strip() or ident in identifiers:
            raise ValueError('Point IDs must be nonempty and unique')
        xy = np.asarray(point.get('xy_m'), dtype=float)
        if xy.shape != (2,) or not np.isfinite(xy).all():
            raise ValueError(f'{ident}: xy_m must contain two finite world coordinates')
        identifiers.add(ident)
        result.append({'id': ident, 'xy_m': xy.tolist()})
    if not result:
        raise ValueError('At least one point is required')
    return result


def _pose_metrics(model, q5, xyz, gripper):
    data = mujoco.MjData(model)
    data.qpos[:] = np.r_[q5, gripper]
    mujoco.mj_forward(model, data)
    body = model.body('gripper').id
    rotation = data.xmat[body].reshape(3, 3)
    pinch = data.xpos[body] + rotation @ PINCH_POINT
    axis = rotation[:, 2]
    limits = model.jnt_range[:5]
    return {
        'pinch_world_m': pinch.tolist(),
        'position_error_m': float(np.linalg.norm(pinch-xyz)),
        'gripper_local_z_world': axis.tolist(),
        'axis_vector_error': float(np.linalg.norm(axis-[0., 0., 1.])),
        'axis_error_rad': float(np.arccos(np.clip(axis[2], -1., 1.))),
        'q4_wrist_roll_rad': float(q5[4]),
        'joint_min_margin_rad': float(np.min(np.minimum(q5-limits[:, 0], limits[:, 1]-q5))),
    }


def _frame_facts(model, reference_q):
    if reference_q is None:
        return {'status': 'not_available', 'reason': 'reference_ik_failed'}
    data = mujoco.MjData(model)
    data.qpos[:] = np.r_[reference_q, .5]
    mujoco.mj_forward(model, data)
    facts = {'status': 'queried', 'pose': 'reference_start solution, gripper=.5 rad',
             'q6_rad': data.qpos.tolist(), 'coordinate_units': 'world meters',
             'rotation_convention': 'local-to-world 3x3, row-major',
             'pinch_point_gripper_local_m': PINCH_POINT.tolist(),
             'radial_angle_note': 'World atan2 bearing is not the shoulder_pan joint angle.'}
    for name in ('base', 'gripper'):
        try:
            body = model.body(name).id
            facts[name] = {'position_world_m': data.xpos[body].tolist(),
                           'rotation_local_to_world': data.xmat[body].reshape(3, 3).tolist()}
        except (KeyError, ValueError) as error:
            facts[name] = {'status': 'not_available', 'error': str(error)}
    try:
        joint = model.joint('shoulder_pan').id
        facts['shoulder_pan'] = {'xanchor_world_m': data.xanchor[joint].tolist(),
                                 'xaxis_world': data.xaxis[joint].tolist()}
    except (KeyError, ValueError) as error:
        facts['shoulder_pan'] = {'status': 'not_available', 'error': str(error)}
    try:
        camera = model.camera('topdown').id
        rotation = data.cam_xmat[camera].reshape(3, 3)
        facts['topdown_camera'] = {
            'cam_xpos_world_m': data.cam_xpos[camera].tolist(),
            'cam_xmat_local_to_world': rotation.tolist(),
            'fovy_degrees': float(model.cam_fovy[camera]),
            'view_axis_camera_local': [0., 0., -1.],
            'view_direction_world': (-rotation[:, 2]).tolist(),
            'source': 'compiled simulator camera; not a hardware calibration',
        }
    except (KeyError, ValueError) as error:
        facts['topdown_camera'] = {'status': 'not_available', 'error': str(error)}
    return facts


def _path(start, goal, checker, *, diagnostic_only=False, resolution_rad=GRASP_RESOLUTION_RAD):
    report = {'diagnostic_only': diagnostic_only,
              'gripper_rad': checker.gripper, 'margin_m': MARGIN_M,
              'resolution_rad': resolution_rad}
    if start is None or goal is None:
        return {**report, 'status': 'not_checked', 'reason': 'missing_ik_endpoint'}
    try:
        checked = validate_joint_path([start, goal], checker.is_valid, resolution_rad)
        return {**report, **checked, 'status': 'checked'}
    except Exception as error:
        return {**report, 'status': 'check_error', 'error': f'{type(error).__name__}: {error}'}


def _extra_axis_screen(model, checker, solutions, reference_q):
    """Separate original rejection from extra-direction sampled certificates."""
    from configuration_sweep import validate_configuration_path
    from mesh_box_axes import MeshBoxAxes
    axes = MeshBoxAxes(model)
    result = {'not_physical': True, 'not_admitted': True, 'checks': {}}
    if reference_q is None or any(name not in solutions for name in ('approach', 'down', 'lift')):
        return dict(result, status='missing_ik_endpoint', supplemental_valid=False)
    approach, down, lift = (solutions[name] for name in ('approach', 'down', 'lift'))
    checks = (
        ('reference', np.r_[reference_q, .5], np.r_[reference_q, .5]),
        ('descent', np.r_[approach, .5], np.r_[down, .5]),
        ('closure', np.r_[down, .5], np.r_[down, .015]),
        ('ascent', np.r_[down, .015], np.r_[lift, .015]),
    )
    for name, start, end in checks:
        rejected = []
        observed = 0

        def inspect(q6):
            nonlocal observed
            observation = axes.inspect(checker, q6)
            if not observation['original']['valid']:
                rejected.append(dict(index=observed, q6_rad=list(q6), **observation))
            observed += 1
            return observation['supplemental_valid']

        validation = validate_configuration_path(start, end, inspect)
        result['checks'][name] = {'validation': validation, 'observed_samples': observed,
                                 'complete': observed == validation.get('required_states'),
                                 'original_rejections': rejected}
    result['supplemental_valid'] = all(
        check['validation']['valid'] is True for check in result['checks'].values())
    result['status'] = 'sampled_certificates_only'
    return result


def probe_workspace(model, points=None, *, pickup_hover_z_m=.06, extra_mesh_box_axes=False):
    """Screen fixed world XY points without changing IK seeds or acceptance.

    Each point starts from the same original reference solution. After an IK
    failure, later stages still run using the last successful solution. The
    report names that seed source; a failed stage is never silently passed.
    """
    if (isinstance(pickup_hover_z_m, (bool, np.bool_)) or
            not isinstance(pickup_hover_z_m, (int, float)) or
            not np.isfinite(pickup_hover_z_m) or not .054 <= pickup_hover_z_m <= .06):
        raise ValueError('pickup_hover_z_m must be finite within [.054, .06] metres')
    points = normalize_points(default_points() if points is None else points)
    open_checker = CollisionChecker(model, gripper=.5, margin_m=MARGIN_M)
    closed_checker = CollisionChecker(model, gripper=.015, margin_m=MARGIN_M)
    reference_q = None
    reference = {'target_pinch_world_m': list(REFERENCE_START_M)}
    try:
        reference_q = solve_pinch_ik(model, np.array(REFERENCE_START_M))
    except Exception as error:
        reference.update(status='ik_error', error=f'{type(error).__name__}: {error}')
    else:
        reference.update(status='solved', q5_rad=reference_q.tolist())
        try:
            reference['collision'] = open_checker.evaluate(reference_q)
        except Exception as error:
            reference.update(status='check_error', error=f'{type(error).__name__}: {error}')

    report = {
        'schema_version': 1,
        'evidence': 'offline_fk_ik_discrete_collision_only',
        'not_physical': True, 'not_admitted': True,
        'contract': {
            'coordinates': 'world', 'position_units': 'm', 'joint_units': 'rad',
            'position_target': 'gripper body pose + R @ PINCH_POINT',
            'pinch_point_gripper_local_m': PINCH_POINT.tolist(),
            'gripper_local_z_world_target': [0., 0., 1.],
            'ik': 'unchanged solve_pinch_ik, original eight seeds and residual < 1e-5',
            'collision_checker': 'conservative_collision.ConservativeCollisionChecker',
            'distance_kind': 'certified_lower_bound, not a measured clearance',
            'collision_margin_m': MARGIN_M,
            'grasp_leg_resolution_rad': GRASP_RESOLUTION_RAD,
            'direct_approach_resolution_rad': DIRECT_RESOLUTION_RAD,
            'open_gripper_rad': .5, 'closed_gripper_rad': .015,
            'pickup_hover_z_m': pickup_hover_z_m,
            'extra_mesh_box_axes': bool(extra_mesh_box_axes),
            'admission': 'Offline results never change station acceptance or authorize execution.',
        },
        'limits': [
            'Planning scene omits the free target; object contacts and object yaw are not checked.',
            'Existing table, fixed trays and obstacles remain; failed clearance may be scene-specific.',
            'Complete compiled geometry uses the existing conservative lower-bound certificate.',
            'Paths are discrete joint-linear checks, not continuous collision proof.',
            'Direct start-to-approach is diagnostic; the original task needs obstacle detour planning.',
            'No mj_step, grasp, transport, release, retreat, hardware or station admission is evaluated.',
            'The default screen omits closure; optional extra-axis diagnostics include the original 244-point closure spacing, never pad/object contacts.',
            'Passing sampled points does not establish a continuous workspace or a +/-150mm envelope.',
        ],
        'reference_start': reference, 'compiled_frame_facts': _frame_facts(model, reference_q), 'points': [],
    }
    for point in points:
        stages, solutions = {}, {}
        seed = reference_q
        seed_source = 'reference_start' if seed is not None else 'solver_default_after_reference_failure'
        for name, _, gripper in STAGES:
            height = .019 if name == 'down' else pickup_hover_z_m
            xyz = np.array([*point['xy_m'], height])
            stage = {'target_pinch_world_m': xyz.tolist(), 'gripper_rad': gripper,
                     'seed_source': seed_source}
            try:
                q = solve_pinch_ik(model, xyz, seed)
            except Exception as error:
                stage.update(status='ik_error', error=f'{type(error).__name__}: {error}')
            else:
                solutions[name] = q
                seed, seed_source = q, name
                stage.update(status='solved', q5_rad=q.tolist())
                try:
                    stage.update(_pose_metrics(model, q, xyz, gripper))
                    checker = closed_checker if name == 'lift' else open_checker
                    stage['collision'] = checker.evaluate(q)
                except Exception as error:
                    stage.update(status='check_error', error=f'{type(error).__name__}: {error}')
            stages[name] = stage
        paths = {
            'start_to_approach_direct': _path(reference_q, solutions.get('approach'), open_checker,
                                              diagnostic_only=True, resolution_rad=DIRECT_RESOLUTION_RAD),
            'approach_to_down': _path(solutions.get('approach'), solutions.get('down'), open_checker),
            'down_to_lift': _path(solutions.get('down'), solutions.get('lift'), closed_checker),
        }
        endpoints_pass = all(stage.get('collision', {}).get('valid') is True
                             and stage['status'] == 'solved' for stage in stages.values())
        legs_pass = all(paths[name].get('valid') is True
                        for name in ('approach_to_down', 'down_to_lift'))
        point_report = {**point, 'stages': stages, 'paths': paths,
                        'offline_screen_pass': bool(endpoints_pass and legs_pass),
                        'not_physical': True, 'not_admitted': True}
        if extra_mesh_box_axes:
            point_report['extra_axis_screen'] = _extra_axis_screen(
                model, open_checker, solutions, reference_q)
        report['points'].append(point_report)
    report['summary'] = {'points': len(points),
                         'offline_screen_pass': sum(p['offline_screen_pass'] for p in report['points']),
                         'not_admitted_points': len(points)}
    return report


def print_table(report, stream=None):
    if stream is None:
        stream = sys.stderr
    print('OFFLINE ONLY | not_physical=true | not_admitted=true', file=stream)
    print('point / stage                     XY world [m]       pos[mm] axis[deg] q4[rad] margin[rad] collision', file=stream)
    for point in report.get('points', []):
        for name, stage in point.get('stages', {}).items():
            xy = ','.join(f'{x:.3f}' for x in point['xy_m'])
            if stage['status'] != 'solved':
                print(f"{point['id']}/{name}: {stage['status']} {stage.get('error', '')}", file=stream)
                continue
            collision = stage['collision']
            print(f"{point['id']+'/'+name:<34} {xy:<18} "
                  f"{stage['position_error_m']*1000:7.4f} {np.degrees(stage['axis_error_rad']):9.5f} "
                  f"{stage['q4_wrist_roll_rad']:7.4f} {stage['joint_min_margin_rad']:10.4f} "
                  f"{collision['valid']}:{collision['reason']}", file=stream)
        paths = ', '.join(f"{name}={path.get('valid', path['status'])}"
                          for name, path in point.get('paths', {}).items())
        print(f"  offline_screen_pass={point.get('offline_screen_pass', False)}; {paths}", file=stream)
    if 'error' in report:
        print(report['error'], file=stream)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    scene = parser.add_mutually_exclusive_group(required=True)
    scene.add_argument('--source', type=Path, help='Original arm MJCF; reuse build_contact_scene in a temporary directory')
    scene.add_argument('--planning-scene', type=Path, help='Existing six-joint planning MJCF from the caller')
    parser.add_argument('--pickup-hover-z-m', type=float, default=.06)
    parser.add_argument('--extra-mesh-box-axes', action='store_true',
                        help='Diagnose original rejected pairs with extra interval-certified axes; never admit execution')
    parser.add_argument('--point', nargs=3, action='append', metavar=('ID', 'WORLD_X_M', 'WORLD_Y_M'),
                        help='Probe this point; repeated options replace the fixed representative set')
    parser.add_argument('--output', type=Path, help='Write JSON here; otherwise JSON goes to stdout. Table goes to stderr.')
    args = parser.parse_args(argv)
    if args.output and args.output.resolve() == (args.source or args.planning_scene).resolve():
        parser.error('JSON output must not overwrite the selected source or planning scene')
    try:
        points = normalize_points([{'id': row[0], 'xy_m': row[1:]} for row in args.point]) if args.point else None
    except (TypeError, ValueError) as error:
        parser.error(str(error))
    try:
        if args.planning_scene:
            model = mujoco.MjModel.from_xml_path(str(args.planning_scene.resolve()))
            report = probe_workspace(model, points, pickup_hover_z_m=args.pickup_hover_z_m,
                                     extra_mesh_box_axes=args.extra_mesh_box_axes)
            report['scene'] = {'kind': 'existing_planning_scene', 'path': str(args.planning_scene.resolve())}
        else:
            with tempfile.TemporaryDirectory(prefix='so101-workspace-probe-') as folder:
                _, model, _ = build_contact_scene(args.source.resolve(), Path(folder))
                report = probe_workspace(model, points, pickup_hover_z_m=args.pickup_hover_z_m,
                                         extra_mesh_box_axes=args.extra_mesh_box_axes)
            report['scene'] = {'kind': 'existing_build_contact_scene', 'source': str(args.source.resolve()),
                               'pick_center_world_m': list(PICK_CENTER)}
        result = 0
    except Exception as error:
        report = {'schema_version': 1, 'not_physical': True, 'not_admitted': True,
                  'status': 'scene_or_probe_error', 'error': f'{type(error).__name__}: {error}', 'points': []}
        result = 2
    print_table(report)
    try:
        serialized = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
    except (TypeError, ValueError) as error:
        report = {'schema_version': 1, 'not_physical': True, 'not_admitted': True,
                  'status': 'report_encoding_error', 'error': f'{type(error).__name__}: {error}', 'points': []}
        serialized = json.dumps(report, indent=2)+'\n'
        result = 2
    try:
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized)
        else:
            sys.stdout.write(serialized)
    except OSError as error:
        report.update(status='report_output_error', output_error=f'{type(error).__name__}: {error}',
                      requested_output=str(args.output))
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
        print(f"WARNING: {report['output_error']}; report returned on stdout", file=sys.stderr)
        return 2
    return result


if __name__ == '__main__':
    raise SystemExit(main())
