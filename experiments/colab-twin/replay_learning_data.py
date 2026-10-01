"""One bounded physical action replay; this does not evaluate a learned policy.

The replay ignores expert stage labels, regenerates the workcell, restores the
initial snapshot and executes the archive's fixed-period absolute commands.
Trajectory agreement and physical task acceptance are independent outcomes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
import uuid

import numpy as np

from learning_data import POLICY_OBSERVATION_KEYS, load_episode
from learning_env import PhysicalTaskMonitor, StateWorkcell


STATE_ATOL = 1e-5
ENVIRONMENT_ATOL = 1e-3
TIME_ATOL = 1e-8


def replay(archive_path, source_path, output, *, max_wall_s=120.0):
    started = time.perf_counter()
    report = {
        'status': 'failed',
        'kind': 'recorded_expert_action_replay',
        'learned_policy_evaluated': False,
        'stage_labels_consumed': False,
        'thresholds': {'state_abs': STATE_ATOL, 'environment_abs': ENVIRONMENT_ATOL,
                       'timestamp_abs_s': TIME_ATOL},
        'max_wall_s': max_wall_s,
        'steps_executed': 0,
        'first_divergence': None,
    }
    rows = []
    maxima = {key: np.zeros(width) for key, width in zip(POLICY_OBSERVATION_KEYS, (6, 30))}
    time_error = 0.0
    monitor = None

    def compare(actual, expected, timestamp, frame_index, boundary):
        nonlocal time_error
        mismatches = {}
        for key, tolerance in zip(POLICY_OBSERVATION_KEYS, (STATE_ATOL, ENVIRONMENT_ATOL)):
            error = np.abs(np.asarray(actual[key]) - np.asarray(expected[key]))
            if not np.isfinite(error).all():
                raise RuntimeError('Nonfinite replay observation difference')
            maxima[key] = np.maximum(maxima[key], error)
            if np.any(error > tolerance):
                mismatches[key] = {
                    'max_abs_error': float(error.max()),
                    'feature_index': int(error.argmax()),
                    'actual': float(actual[key][error.argmax()]),
                    'expected': float(expected[key][error.argmax()]),
                }
        delta = abs(actual['time_s'] - timestamp)
        time_error = max(time_error, delta)
        if delta > TIME_ATOL:
            mismatches['time_s'] = {'abs_error_s': float(delta)}
        if mismatches and report['first_divergence'] is None:
            report['first_divergence'] = {'frame_index': frame_index, 'boundary': boundary,
                                          'mismatches': mismatches}

    try:
        episode = load_episode(archive_path)
        if not len(episode['executed_action']):
            raise ValueError('An empty attempt has no actions to replay')
        report['archive_sha256'] = hashlib.sha256(Path(archive_path).read_bytes()).hexdigest()
        report['archive_passed'] = episode['report']['passed']
        report['archive_transition_count'] = len(episode['executed_action'])
        metadata = episode['metadata']
        cell = StateWorkcell(source_path, Path(output) / 'workcell', metadata)
        monitor = PhysicalTaskMonitor(cell.baseline_z)
        observation = cell.reset()
        compare(observation, {key: episode[key][0] for key in POLICY_OBSERVATION_KEYS},
                float(episode['timestamp'][0]), 0, 'reset')
        report['initial_snapshot_matches'] = report['first_divergence'] is None
        for index, action in enumerate(episode['executed_action']):
            if time.perf_counter() - started >= max_wall_s:
                raise TimeoutError('Replay reached its wall-time budget')
            observation, row = cell.step(action)
            rows.append(row)
            report['steps_executed'] = index + 1
            compare(observation,
                    {key: episode['next_' + key][index] for key in POLICY_OBSERVATION_KEYS},
                    float(episode['next_timestamp'][index]), index, 'after_step')
            physical = monitor.update(row)
            if physical['failure_reason']:
                raise RuntimeError('Physical replay stopped: ' + physical['failure_reason'])
        report['physical_acceptance'] = monitor.report()
        report['trajectory_matches'] = report['first_divergence'] is None
        report['status'] = ('passed' if report['trajectory_matches'] and monitor.report()['passed']
                            else 'failed')
    except Exception as error:
        report['error'] = {'type': type(error).__name__, 'message': str(error)}
        report['trajectory_matches'] = False
        if monitor is not None:
            report['physical_acceptance'] = monitor.report()
    report['max_abs_error_per_feature'] = {key: value.tolist() for key, value in maxima.items()}
    report['max_timestamp_error_s'] = time_error
    report['wall_s'] = time.perf_counter() - started
    Path(output).mkdir(parents=True, exist_ok=True)
    (Path(output) / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    (Path(output) / 'trajectory.json').write_text(json.dumps(rows, allow_nan=False) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[2] /
                        'workspaces/so101_ws/src/so101_mujoco/models/so101.xml')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--max-wall-s', type=float, default=120.)
    args = parser.parse_args()
    if not np.isfinite(args.max_wall_s) or args.max_wall_s <= 0 or args.max_wall_s > 120:
        parser.error('Replay wall-time budget must be finite and in (0, 120] seconds')
    if args.output is None:
        args.output = Path(__file__).resolve().parent / 'output' / f'learning-replay-{uuid.uuid4().hex}'
    args.output.mkdir(parents=True, exist_ok=False)
    report = replay(args.archive, args.source, args.output, max_wall_s=args.max_wall_s)
    print(json.dumps({'output': str(args.output), 'status': report['status'],
                      'steps_executed': report['steps_executed'],
                      'physical_acceptance': report.get('physical_acceptance'),
                      'first_divergence': report['first_divergence'],
                      'error': report.get('error')}, ensure_ascii=False))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
