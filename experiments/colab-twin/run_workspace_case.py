"""Run one development-only workspace case through the original physical scorer.

The declared region is a fixed workstation prior, not the target's measured pose.
This entry does not extend public Station admission or infer a physical verdict
from an offline workspace report.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
import uuid

from evaluate_station import source_reference, summarize
from route_policy import DEFAULT_SOURCE, load_route_policy
from station_executor import StationVideo, atomic_json


DEFAULT_PROFILE = Path(__file__).parent / 'scenarios/workspace-m1a.json'
TARGET_REGION_XY_M = ((.21, .27), (-.16, -.10))
PROTOCOL = {'max_sim_s': 90, 'max_episode_wall_s': 120}


def _xy(value, name):
    if (not isinstance(value, list) or len(value) != 2 or
            any(isinstance(v, bool) or not isinstance(v, (int, float)) or
                not math.isfinite(v) for v in value)):
        raise ValueError(f'{name} must contain two finite metre coordinates')
    return [float(v) for v in value]


def select_case(profile_path, case_id):
    """Validate shared declarations and only the selected case's payload."""
    profile = json.loads(Path(profile_path).read_text())
    if not isinstance(profile, dict) or profile.get('development_only') is not True:
        raise ValueError('profile must explicitly declare development_only=true')
    if profile.get('schema') != 'so101.workspace-development.v1':
        raise ValueError('unsupported workspace development profile schema')
    if profile.get('target_region_xy_m') != [list(v) for v in TARGET_REGION_XY_M]:
        raise ValueError('M1a requires the fixed declared workstation target region')
    if profile.get('protocol') != PROTOCOL:
        raise ValueError('M1a retains the original 90 sim / 120 wall second budgets')
    cases = profile.get('cases')
    if not isinstance(cases, list):
        raise ValueError('profile cases must be an array')
    matches = [row for row in cases if isinstance(row, dict) and row.get('id') == case_id]
    if len(matches) != 1:
        available = ', '.join(str(row['id']) for row in cases
                              if isinstance(row, dict) and isinstance(row.get('id'), str))
        raise ValueError(f'unknown or duplicate case {case_id!r}; available: {available}')
    row = matches[0]
    xy = _xy(row.get('initial_xy_m'), 'initial_xy_m')
    place = _xy(row.get('place_xy_m'), 'place_xy_m')
    outside = any(abs(v-c) > .01000001 for v, c in zip(xy, (.24, -.13)))
    expected_mode = 'declared_region' if outside else 'controller_default'
    if row.get('target_region_mode') != expected_mode:
        raise ValueError(f'case target_region_mode must be {expected_mode}')
    if outside and any(not lo <= value <= hi
                       for value, (lo, hi) in zip(xy, TARGET_REGION_XY_M)):
        raise ValueError('requested case lies outside the declared workstation region')
    selected = {'id': case_id, 'initial_xy_m': xy, 'place_xy_m': place,
                'target_region_mode': expected_mode}
    if 'pick_xy_m' in row:
        selected['pick_xy_m'] = _xy(row['pick_xy_m'], 'pick_xy_m')
    if 'pickup_hover_z_m' in row:
        height = row['pickup_hover_z_m']
        if (isinstance(height, bool) or not isinstance(height, (int, float)) or
                not math.isfinite(height) or not .054 <= height <= .06):
            raise ValueError('pickup_hover_z_m must be finite within [.054, .06] metres')
        selected['pickup_hover_z_m'] = float(height)
    if 'pickup_open_jaw_rad' in row:
        opening = row['pickup_open_jaw_rad']
        if (isinstance(opening, bool) or not isinstance(opening, (int, float))
                or opening not in (.35, .5)):
            raise ValueError('pickup_open_jaw_rad supports only explicit .35 or original .5 rad')
        selected['pickup_open_jaw_rad'] = float(opening)
    return selected


def controller_options(case, route_policy):
    options = {'release_rotation_mode': 'floor_yaw', 'release_pinch_height_m': .028,
               'place_xy': case['place_xy_m'], 'place_height_m': 0.,
               'route_policy': route_policy}
    if case['target_region_mode'] == 'declared_region':
        options['target_region_xy_m'] = TARGET_REGION_XY_M
    if 'pickup_hover_z_m' in case:
        options['pickup_hover_z_m'] = case['pickup_hover_z_m']
    if 'pickup_open_jaw_rad' in case:
        options['pickup_open_jaw_rad'] = case['pickup_open_jaw_rad']
    return options


def _configure_native(policy):
    # Keep station_executor.run's native initialization, including disabled flags.
    from support_native import (configure_quad_vertices, configure_small_direction_cache,
                                configure_tree_leaf8, configure_leaf_packed,
                                configure_packed_inline, configure_seed_bound_direct,
                                configure_summary_fast)
    configure_quad_vertices(bool(policy and policy.quad_vertices))
    configure_small_direction_cache(bool(policy and policy.small_direction_cache))
    configure_tree_leaf8(bool(policy and policy.tree_leaf8))
    configure_leaf_packed(bool(policy and policy.leaf_packed))
    configure_packed_inline(bool(policy and policy.packed_inline))
    configure_seed_bound_direct(bool(policy and policy.seed_bound_direct))
    configure_summary_fast(bool(policy and policy.summary_fast))


def _run_original(output, case, options, timer):
    os.environ.setdefault('MUJOCO_GL', 'egl')
    _configure_native(options['route_policy'])
    from grasp_episode import build_contact_scene
    from run_visual_grasp import SOURCE, run_physical_episode

    def build_scene(source, folder, **kwargs):
        layout = {'place_xy': options['place_xy'], 'place_height_m': options['place_height_m']}
        if 'pick_xy_m' in case:
            layout['pick_xy'] = case['pick_xy_m']
        return build_contact_scene(source, folder, **layout, **kwargs)

    # The original reset fixture consumes case XY. The controller still receives
    # RGB-derived XY; neither this builder nor this wrapper edits execution state.
    return run_physical_episode(SOURCE, output/'episode', dict(PROTOCOL), case, None,
                                video=True, scene_builder=build_scene, timing=timer,
                                video_factory=StationVideo, video_stride=8,
                                controller_options=options)


def run_case(profile_path, case_id, output_root):
    profile_path, output_root = Path(profile_path).resolve(), Path(output_root).resolve()
    run_id = str(uuid.uuid4())
    output = output_root/run_id
    output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).parent
    requested = {'id': case_id}
    candidate = source_reference(DEFAULT_SOURCE)
    candidate['controller'] = source_reference(source/'visual_grasp_controller.py')
    scorer = source_reference(source/'learning_env.py')
    scorer['entry'] = 'PhysicalTaskMonitor via run_visual_grasp.run_physical_episode'
    status = {'status': 'running', 'phase': 'validating',
              'station_name': f'M1a development: {case_id}',
              'development_only': True, 'not_admitted': True}
    timer = None
    atomic_json(output/'status.json', status)
    try:
        requested = select_case(profile_path, case_id)
        atomic_json(output/'requested-case.json', requested)
        policy, loaded = load_route_policy()
        candidate.update(loaded)
        options = controller_options(requested, policy)
        status.update(phase='running', layout={
            'place_xy_m': requested['place_xy_m'], 'place_height_m': 0.,
            'pick_xy_m': requested.get('pick_xy_m', [.24, -.13]),
            'pickup_hover_z_m': requested.get('pickup_hover_z_m', .06)})
        if 'pickup_open_jaw_rad' in requested:
            status['layout']['pickup_open_jaw_rad'] = requested['pickup_open_jaw_rad']
        atomic_json(output/'status.json', status)
        from episode_timing import EpisodeTiming
        timer = EpisodeTiming()
        physical_case = {'id': requested['id'], 'initial_xy_m': requested['initial_xy_m'],
                         'perturbed': False, 'offset_rad': [0.]*5,
                         'obstacle_geom_names': ['approach_obstacle']}
        if 'pick_xy_m' in requested:
            physical_case['pick_xy_m'] = requested['pick_xy_m']
        report = _run_original(output, physical_case, options, timer)
        status.update(report=report,
                      status='succeeded' if report.get('passed') is True else 'failed',
                      phase='complete', message=report.get('failure_reason'))
    except Exception as error:
        status.update(status='failed', phase='failed', message=str(error),
                      error_type=type(error).__name__)
    if timer is not None:
        atomic_json(output/'timing.json', timer.report())
    artifacts = {'requested_case': str(output/'requested-case.json')}
    for key, filename in [('report', 'report.json'), ('trajectory', 'trajectory.json'),
                          ('release', 'release-2ms.json'), ('planning', 'planning.json'),
                          ('jaw_sweeps', 'jaw-sweeps.json'), ('video', 'grasp-place.mp4'),
                          ('localization', 'initial-localization.png'),
                          ('observations', 'visual-observations.json')]:
        path = output/'episode'/filename
        if path.is_file():
            artifacts[key] = str(path)
    if timer is not None:
        artifacts['timing'] = str(output/'timing.json')
    status['artifacts'] = artifacts
    atomic_json(output/'status.json', status)
    for reference, module_name in ((candidate['controller'], 'visual_grasp_controller'),
                                   (scorer, 'learning_env')):
        module = sys.modules.get(module_name)
        reference['loaded_path'] = str(Path(module.__file__).resolve()) if module else None
    result = summarize(status, run_id=run_id, scenario_path=profile_path,
                       output=output, candidate=candidate, scorer=scorer)
    result.update(development_only=True, not_admitted=True, requested_case=requested,
                  declared_region=[list(v) for v in TARGET_REGION_XY_M],
                  target_region_mode=requested.get('target_region_mode'))
    atomic_json(output/'evaluation.json', result)
    # Reuse the original serial runner's latest-result pointer, while retaining
    # the independent UUID directory for every case and failed attempt.
    atomic_json(output_root/'evaluation.json', result)
    print(json.dumps({'run_id': run_id, 'verdict': result['verdict'],
                      'failure_reason': result['failure_reason'],
                      'evaluation': str(output/'evaluation.json')}, ensure_ascii=False))
    return 0 if result['passed'] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, default=DEFAULT_PROFILE)
    parser.add_argument('--case', help='Run exactly this profile case ID')
    parser.add_argument('--output-dir', type=Path, help='Parent for an independent run UUID directory')
    parser.add_argument('--list-cases', action='store_true', help='List IDs without loading simulation')
    args = parser.parse_args(argv)
    if args.list_cases:
        try:
            profile = json.loads(args.profile.read_text())
            print('\n'.join(row['id'] for row in profile.get('cases', [])
                            if isinstance(row, dict) and isinstance(row.get('id'), str)))
            return 0
        except (OSError, ValueError, AttributeError) as error:
            parser.exit(1, f'{error}\n')
    if not args.case or args.output_dir is None:
        parser.error('--case and --output-dir are required unless --list-cases is used')
    return run_case(args.profile, args.case, args.output_dir)


if __name__ == '__main__':
    raise SystemExit(main())
