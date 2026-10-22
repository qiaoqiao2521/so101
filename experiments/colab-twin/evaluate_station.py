"""Call the existing station executor and expose its physical verdict as JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import uuid

from station_executor import atomic_json, run
from route_policy import BASELINE_SOURCE, load_route_policy


def source_reference(path):
    """Describe the actual checkout, without preventing human edits."""
    path = Path(path).resolve()
    result = {'path': str(path), 'commit': None, 'dirty_paths': None}
    try:
        result['commit'] = subprocess.check_output(
            ['git', '-C', str(path.parent), 'rev-parse', 'HEAD'], text=True,
            stderr=subprocess.DEVNULL).strip()
        result['dirty_paths'] = subprocess.check_output(
            ['git', '-C', str(path.parent), 'status', '--short', '--untracked-files=no'],
            text=True, stderr=subprocess.DEVNULL).splitlines()
    except (OSError, subprocess.CalledProcessError):
        result['note'] = 'Git provenance unavailable; source path remains recorded'
    return result


def summarize(status, *, run_id, scenario_path, output, candidate, scorer):
    report = status.get('report')
    physical = isinstance(report, dict)
    report = report if physical else {}
    state = status.get('status', 'failed')
    passed = physical and state == 'succeeded' and report.get('passed') is True
    layout = status.get('layout', {})
    metrics = {key: report.get(key) for key in (
        'simulation_s', 'wall_s', 'max_lift_m', 'final_object_xyz_m',
        'hold_duration_s', 'settled_duration_s', 'grasp_success', 'place_success',
        'safety_stop', 'place_goal_xy_m', 'place_height_m', 'place_support_z_m')}
    return {
        'schema': 'so101.station-evaluation.v1',
        'scenario_id': scenario_path.stem, 'scenario_path': str(scenario_path),
        'scenario_name': status.get('station_name'), 'run_id': run_id,
        'mode': 'physical_simulation' if physical else 'not_run_or_incomplete',
        'state': state, 'verdict': 'pass' if passed else 'fail' if physical else 'unscored',
        'passed': passed, 'metrics': metrics,
        'units': {'distance': 'm', 'time': 's', 'joint_angle': 'rad', 'force': 'N'},
        'failure_reason': None if passed else report.get('failure_reason') or status.get('message'),
        'unsupported': status.get('unsupported', []),
        'scene': {'place_xy_m': layout.get('place_xy_m'),
                  'place_height_m': layout.get('place_height_m')},
        'candidate': candidate, 'scorer': scorer,
        'artifacts': dict(status.get('artifacts', {}), status=str(output/'status.json')),
    }


def evaluate(station_path, output_root, cancel_file=None, *, candidate_path=None, timing=False):
    station_path, output_root = Path(station_path).resolve(), Path(output_root).resolve()
    run_id = str(uuid.uuid4())
    output = output_root/run_id
    source = Path(__file__).parent
    candidate = source_reference(candidate_path or BASELINE_SOURCE)
    candidate['controller'] = source_reference(source/'visual_grasp_controller.py')
    scorer = source_reference(source/'learning_env.py')
    # Each invocation owns a new result directory; stale results cannot pass a new run.
    try:
        policy, loaded = load_route_policy(candidate['path'])
        candidate.update(loaded)
    except Exception as error:
        output.mkdir(parents=True, exist_ok=True)
        candidate.update(loaded_path=None, load_error_type=type(error).__name__)
        atomic_json(output/'status.json', {'status': 'failed', 'phase': 'candidate_loading',
                    'message': str(error), 'error_type': type(error).__name__})
        code = 1
    else:
        timer = None
        if timing:
            from episode_timing import EpisodeTiming
            timer = EpisodeTiming()
        code = run(station_path, output, cancel_file, route_policy=policy,
                   **({'timing': timer} if timer is not None else {}))
        if timer is not None:
            atomic_json(output/'timing.json', timer.report())
    status = json.loads((output/'status.json').read_text())
    for reference, module_name in ((candidate['controller'], 'visual_grasp_controller'), (scorer, 'learning_env')):
        module = sys.modules.get(module_name)
        reference['loaded_path'] = str(Path(module.__file__).resolve()) if module else None
    result = summarize(status, run_id=run_id, scenario_path=station_path,
                       output=output, candidate=candidate, scorer=scorer)
    planning = output/'episode/planning.json'
    if planning.is_file():
        rows = json.loads(planning.read_text())
        result['policy_execution'] = {
            'transport': [{key: row.get(key) for key in ('route_policy', 'transition_height_m',
                           'transition_attempts', 'motion_and_arrival_s', 'route_search')}
                          for row in rows if row.get('stage') == 'transport_execution_plan'],
            'separation': ((status.get('report') or {}).get('release_plan') or {}).get('separation_end')}
    atomic_json(output/'evaluation.json', result)
    atomic_json(output_root/'evaluation.json', result)
    print(json.dumps({'run_id': run_id, 'verdict': result['verdict'],
                      'failure_reason': result['failure_reason'],
                      'evaluation': str(output/'evaluation.json')}, ensure_ascii=False))
    return 0 if result['passed'] else code or 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--station', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--cancel-file', type=Path)
    parser.add_argument('--candidate', type=Path, help='Local source exporting route_preferences()')
    parser.add_argument('--timing', action='store_true', help='Record exclusive original-loop timings')
    args = parser.parse_args()
    return evaluate(args.station, args.output_dir, args.cancel_file,
                    candidate_path=args.candidate, timing=args.timing)


if __name__ == '__main__':
    raise SystemExit(main())
