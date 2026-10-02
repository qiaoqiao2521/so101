"""Offline expert corrections after a physically executed learned-policy prefix.

This collector is never imported by policy evaluation. Prefix commands are
unlabelled, not demonstrations. Only a successful complete correction episode
can contribute labels, and raw64 replay must be checked separately.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import time
import uuid

import numpy as np

from expert_path import joint_path_lookahead
from grasp_episode import PINCH_POINT, solve_pinch_ik
from joint_planner import plan_joint_path, validate_joint_path
from learning_data import EpisodeRecorder, POLICY_OBSERVATION_KEYS, load_episode
from learning_env import PhysicalTaskMonitor, StateWorkcell
from placement import carried_configuration_checker, plan_transport


def load_recovery_prefix(path, cycles, period_s, initial):
    """Separate late-recovery budget; original precontact <=5s API is unchanged."""
    if (isinstance(cycles, bool) or not isinstance(cycles, int) or not 1 <= cycles <= 3000
            or not np.isfinite(period_s) or period_s <= 0 or cycles * period_s > 60 + 1e-9):
        raise ValueError('Recovery prefix must span 1..3000 cycles and at most 60 seconds')
    with np.load(path, allow_pickle=False) as archive:
        commands = np.asarray(archive['action'][:cycles], dtype=np.float64).copy()
        times = np.asarray(archive['timestamp'][:cycles], dtype=np.float64)
        next_times = np.asarray(archive['next_timestamp'][:cycles], dtype=np.float64)
        if (commands.shape != (cycles, 6) or not np.isfinite(commands).all()
                or times.shape != (cycles,) or next_times.shape != (cycles,)
                or not np.isfinite(times).all() or not np.isfinite(next_times).all()
                or not np.allclose(next_times - times, period_s, rtol=0, atol=1e-9)
                or not np.allclose(times[1:], next_times[:-1], rtol=0, atol=1e-9)
                or not np.isclose(times[0], initial['time_s'], rtol=0, atol=1e-8)):
            raise ValueError('Prefix commands must be finite and use the reset control cadence')
        for key in POLICY_OBSERVATION_KEYS:
            values = np.asarray(archive[key][0])
            if (values.shape != initial[key].shape or not np.isfinite(values).all()
                    or not np.allclose(values, initial[key], rtol=0, atol=1e-6)):
                raise ValueError('Prefix initial observation differs from the reference scene')
    return commands


def recovery_admission(mode, observation, row, monitor, *, current_contact_duration_s=None):
    """Admission depends on current physical evidence, not the source end pose."""
    if mode not in ('approach', 'held', 'release'):
        raise ValueError('Recovery mode must be approach, held or release')
    evidence = np.asarray([row['time_s'], row['object_z_m'], row['object_speed_m_s'],
                           monitor.baseline_z, *row['tip_forces_n']], dtype=float)
    if (evidence.shape != (6,) or not np.isfinite(evidence).all()
            or monitor.lift_start is not None and not np.isfinite(monitor.lift_start)):
        raise RuntimeError('Nonfinite or malformed physical admission evidence')
    if monitor.failure_reason or not row['finite_state'] or not row['arm_valid'] or row['obstacle_contact']:
        raise RuntimeError('Cannot correct a failed or unsafe physical prefix')
    if mode == 'approach':
        if max(row['tip_forces_n']) > .02 or row['object_z_m'] - monitor.baseline_z > .005:
            raise RuntimeError('Approach correction requires a contact-free, unlifted target')
        pinch = np.asarray(row['pinch_xyz_m'], dtype=float)
        target = observation['observation.environment_state'][6:9]
        if (pinch.shape != (3,) or not np.isfinite(pinch).all()
                or observation['observation.state'][5] < .45 or pinch[2] < target[2]+.035
                or np.linalg.norm(pinch[:2]-target[:2]) > .01):
            raise RuntimeError('Late approach requires open jaws above the target, not a descend/closing state')
    elif mode == 'held' and (not monitor.grasp_success or monitor.lift_start is None
          or row['time_s'] - monitor.lift_start < 1.0 - 1e-8
          or min(row['tip_forces_n']) <= .02 or row['floor_contact'] or row['place_floor_contact']
          or row['object_z_m'] - monitor.baseline_z < .025):
        raise RuntimeError('Held correction requires sustained current dual-finger physical lift')
    elif mode == 'release':
        if (isinstance(current_contact_duration_s, (bool, np.bool_))
                or not isinstance(current_contact_duration_s, (int, float, np.integer, np.floating))
                or not np.isfinite(current_contact_duration_s) or current_contact_duration_s < 0):
            raise RuntimeError('Release correction requires finite current contact duration evidence')
        if any(not isinstance(row[key], (bool, np.bool_)) for key in (
                'finite_state', 'arm_valid', 'obstacle_contact', 'floor_contact',
                'place_floor_contact', 'in_place_tray')):
            raise RuntimeError('Nonfinite or malformed release physical evidence')
        if (not monitor.grasp_success or current_contact_duration_s < 1.0 - 1e-8
                or min(row['tip_forces_n']) <= .02 or row['floor_contact'] or row['place_floor_contact']
                or not row['in_place_tray'] or not .010 <= row['object_z_m'] < .0145
                or not 0 <= row['object_speed_m_s'] <= .05):
            raise RuntimeError('Release correction requires current sustained dual contact above blue-tray support')
        timestamp = observation.get('time_s')
        if (any(np.asarray(observation[key]).shape != shape
                for key, shape in zip(POLICY_OBSERVATION_KEYS, ((6,), (30,))))
                or isinstance(timestamp, (bool, np.bool_))
                or not isinstance(timestamp, (int, float, np.integer, np.floating))
                or not np.isfinite(timestamp)):
            raise RuntimeError('Nonfinite or malformed release correction state')
    if any(not np.isfinite(observation[key]).all() for key in POLICY_OBSERVATION_KEYS):
        raise RuntimeError('Nonfinite correction state')


def collect(reference, prefix, policy_report, source, output, *, cycles, mode,
            max_wall_s=120., max_correction_s=60.):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    report = {'status': 'failed', 'kind': 'offline_policy_state_expert_correction',
              'learned_policy_evaluated': False, 'recovery_mode': mode,
              'prefix_control_cycles': cycles, 'prefix_commands_are_labels': False,
              'lower_closed_gripper_payload_chord_guard': True,
              'max_wall_s': max_wall_s, 'max_correction_s': max_correction_s}
    recorder = monitor = None
    rows = []
    try:
        if (not np.isfinite(max_wall_s) or not 0 < max_wall_s <= 120
                or not np.isfinite(max_correction_s) or not 0 < max_correction_s <= 60):
            raise ValueError('Correction and wall budgets must be positive and bounded')
        ref = load_episode(reference)
        evaluation = json.loads(Path(policy_report).read_text())
        attempt = next((a for a in evaluation.get('attempts', [])
                        if (Path(policy_report).parent / a.get('directory', '') /
                            'policy-transitions.npz').resolve() == Path(prefix).resolve()), None)
        if (attempt is None or evaluation.get('expert_intervention') is not False
                or evaluation.get('policy_inputs') != list(POLICY_OBSERVATION_KEYS)
                or hashlib.sha256(Path(reference).read_bytes()).hexdigest()
                not in evaluation.get('reference_dataset_sha256', [])):
            raise ValueError('Prefix must be bound to a stage-free policy report and its reference reset')
        metadata = copy.deepcopy(ref['metadata'])
        origin = {'npz_sha256': hashlib.sha256(Path(prefix).read_bytes()).hexdigest(),
                  'policy_report_sha256': hashlib.sha256(Path(policy_report).read_bytes()).hexdigest(),
                  'checkpoint_sha256': evaluation.get('checkpoint_sha256'),
                  'reference_sha256': hashlib.sha256(Path(reference).read_bytes()).hexdigest(),
                  'control_cycles': cycles, 'commands_are_training_labels': False,
                  'source_state_is_not_restored': True}
        metadata.update(collector_version='state-conditioned-v6-late-policy-recovery',
                        collection_kind='physical policy prefix then offline expert correction',
                        policy_deviation_prefix=origin, recovery_mode=mode,
                        lower_closed_gripper_payload_chord_guard=True)
        report['origin'] = origin
        cell = StateWorkcell(source, output / 'workcell', metadata)
        observation = cell.reset()
        commands = load_recovery_prefix(prefix, cycles, cell.period, observation)
        recorder = EpisodeRecorder(output / 'expert.h5', metadata)
        monitor = PhysicalTaskMonitor(cell.baseline_z)
        correction_start = None
        current_contact_start = None

        def step(command, stage, *, valid=True):
            nonlocal observation, current_contact_start
            if time.perf_counter() - started >= max_wall_s:
                raise TimeoutError('Recovery reached wall-time budget')
            if (correction_start is not None and
                    cell.data.time - correction_start + cell.period > max_correction_s + 1e-9):
                raise TimeoutError('Expert correction reached its simulation budget')
            before = observation
            observation, row = cell.step(command)
            gripper = cell.model.body('gripper').id
            row['pinch_xyz_m'] = (cell.data.xpos[gripper] +
                                   cell.data.xmat[gripper].reshape(3, 3) @ PINCH_POINT).tolist()
            recorder.append(before, command if valid else None, command, observation,
                            label_valid=valid, stage=stage, perturbation=not valid)
            rows.append(dict(row, stage=stage))
            physical = monitor.update(row)
            if mode == 'release':
                # A lowered object resets lift_start, so release needs its own
                # uninterrupted contact clock. Historical hold_duration cannot
                # prove that a lost grasp was continuously reacquired.
                in_contact = (min(row['tip_forces_n']) > .02
                              and not row['floor_contact'] and not row['place_floor_contact'])
                current_contact_start = ((row['time_s'] if current_contact_start is None
                                          else current_contact_start) if in_contact else None)
            if physical['failure_reason']:
                raise RuntimeError('Physical recovery stopped: ' + physical['failure_reason'])
            return row

        for command in commands:
            row = step(command, 'policy_prefix', valid=False)
            if mode == 'approach' and (max(row['tip_forces_n']) > .02
                                      or row['object_z_m'] - cell.baseline_z > .005):
                raise RuntimeError('Approach prefix entered contact or lift')
        admission_options = {}
        if mode == 'release':
            contact_duration = (row['time_s'] - current_contact_start
                                if current_contact_start is not None else 0.)
            admission_options['current_contact_duration_s'] = contact_duration
            release_admission = {'current_dual_contact_duration_s': contact_duration,
                                 'minimum_duration_s': 1., 'object_z_min_m': .010,
                                 'object_z_max_exclusive_m': .0145,
                                 'maximum_object_speed_m_s': .05,
                                 'requires_whole_object_in_place_tray': True,
                                 'requires_no_floor_support': True}
            metadata['release_admission'] = release_admission
            report['release_admission'] = release_admission
            # The recorder owns its copied metadata, not this local mapping.
            recorder.metadata['release_admission'] = copy.deepcopy(release_admission)
        recovery_admission(mode, observation, row, monitor, **admission_options)
        report['actual_correction_boundary'] = {**{k: observation[k].tolist() for k in POLICY_OBSERVATION_KEYS},
                                               'time_s': observation['time_s'], 'physical': monitor.report()}
        correction_start = cell.data.time
        # First valid label brakes the measured arm; release starts open now,
        # rather than assigning an unsupported closed-jaw recovery label.
        step(np.r_[observation['observation.state'][:5], .015 if mode == 'held' else .5], 'recovery_brake')
        rig = cell.checker.model

        def jaw_for(stage, default):
            state = observation['observation.environment_state']
            if stage == 'descend':
                gripper = cell.model.body('gripper').id
                pinch = cell.data.xpos[gripper] + cell.data.xmat[gripper].reshape(3, 3) @ PINCH_POINT
                if np.linalg.norm(pinch[:2] - state[6:8]) < .002 and pinch[2] < state[8] + .010:
                    return .015
            if stage == 'lower' and rows[-1]['in_place_tray'] and state[8] < .0145:
                return .5
            return default

        def move(points, stage, jaw, *, reactive=False, carried=False):
            points = np.asarray(points, dtype=np.float64)
            measured_jaw = observation['observation.state'][5]
            if not validate_joint_path(points, lambda q: cell.checker.evaluate(
                    np.r_[q, measured_jaw], require_fixed_gripper=False)['valid'], .005)['valid']:
                raise RuntimeError('Expert route is invalid')
            lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
            cumulative = np.r_[0., np.cumsum(lengths)]
            total = cumulative[-1]
            if total <= 1e-12:
                return
            payload_valid, payload_audit = (carried_configuration_checker(cell.model, cell.data, cell.checker)
                                           if carried else (None, None))
            duration = max(2., total * 1.875 / .3)
            ticks = max(2, int(np.ceil(duration / cell.period)))
            for index in range(ticks if not reactive else int(np.ceil((total / .05 + 10) / cell.period))):
                if cell.data.time - correction_start >= max_correction_s:
                    raise TimeoutError('Expert correction reached its simulation budget')
                actual = observation['observation.state'][:5]
                if reactive:
                    target, _ = joint_path_lookahead(points, actual, .006)
                else:
                    t = index / (ticks - 1)
                    s = (t**3 * (10 + t * (-15 + 6*t))) * total
                    segment = min(max(0, np.searchsorted(cumulative, s, side='right') - 1), len(lengths)-1)
                    target = points[segment] + (s-cumulative[segment]) / max(lengths[segment], 1e-12) * (points[segment+1]-points[segment])
                command = np.r_[target, jaw_for(stage, jaw)]
                # Keep the measured grasp hypothesis while lowering closed.
                # The geometry-gated open command starts release; contact can
                # still be live then, so do not rigidly carry the falling box.
                carrying_command = carried and not (stage == 'lower' and command[5] == .5)
                valid_chord = (payload_valid if carrying_command else
                               lambda q: cell.checker.evaluate(np.r_[q, command[5]], require_fixed_gripper=False)['valid'])
                if not validate_joint_path([actual, target], valid_chord, .005)['valid']:
                    raise RuntimeError('Actual-to-expert chord invalid: ' + str(payload_audit))
                step(command, stage)
                if reactive and np.max(np.abs(observation['observation.state'][:5]-points[-1])) <= .0015 and np.linalg.norm(cell.data.qvel[:5]) < .05:
                    return
            if reactive:
                raise RuntimeError('Reactive expert did not reach endpoint')

        if mode == 'approach':
            xyz = observation['observation.environment_state'][6:9]
            current = observation['observation.state'][:5]
            hover = solve_pinch_ik(rig, np.r_[xyz[:2], .06], current)
            route = [current, hover]
            if not validate_joint_path(route, cell.checker.is_valid, .005)['valid']:
                plan = plan_joint_path(current, hover, cell.checker.bounds, cell.checker.is_valid,
                                       seed=metadata['seed'], timeout_s=10, resolution_rad=.005)
                if plan['status'] != 'solved':
                    raise RuntimeError('Expert cannot reconnect late approach')
                route = plan['path']
            move(route, 'approach', .5, reactive=True)
            down = solve_pinch_ik(rig, np.r_[xyz[:2], .019], observation['observation.state'][:5])
            move([observation['observation.state'][:5], down], 'descend', .5)
            for _ in range(round(6 / cell.period)):
                step(np.r_[down, .015], 'close')
                if min(rows[-1]['tip_forces_n']) > .02 and abs(cell.data.qvel[5]) < .05:
                    break
            else:
                raise RuntimeError('No stable dual contact after approach correction')
            lift = solve_pinch_ik(rig, np.r_[xyz[:2], .06], observation['observation.state'][:5])
            move([observation['observation.state'][:5], lift], 'lift', .015)
            for _ in range(round(1.1 / cell.period)):
                step(np.r_[lift, .015], 'hold')
            recovery_admission('held', observation, rows[-1], monitor)
        if mode != 'release':
            paths, report['transport_planning'] = plan_transport(cell.model, rig, cell.data, cell.checker,
                                                               solve_ik=solve_pinch_ik, pinch_point=PINCH_POINT,
                                                               continue_forward=mode == 'held')
            for index, points in enumerate(paths):
                lower = index == len(paths)-1
                move(points, 'lower' if lower else 'transport', .015, carried=True)
        release_pose = observation['observation.state'][:5].copy()
        if not rows[-1]['in_place_tray'] or rows[-1]['object_z_m'] >= .0145:
            raise RuntimeError('Expert release requires actual payload in the blue tray below release height')
        for _ in range(round(6 / cell.period)):
            step(np.r_[release_pose, .5], 'release')
            if rows[-1]['place_floor_contact'] and max(rows[-1]['tip_forces_n']) < .02 and cell.data.qpos[5] > .45:
                break
        else:
            raise RuntimeError('Expert release did not reach physical tray support')
        retreat = np.asarray(metadata['initial_snapshot']['qpos'][:5])
        move([observation['observation.state'][:5], retreat], 'retreat', .5)
        for _ in range(round(1.5 / cell.period)):
            step(np.r_[retreat, .5], 'settle')
        report['status'] = 'passed' if monitor.report()['passed'] else 'failed'
    except Exception as error:
        report['error'] = {'type': type(error).__name__, 'message': str(error)}
    report['physical_acceptance'] = monitor.report() if monitor else None
    report['wall_s'] = time.perf_counter() - started
    report['recorded_steps'] = len(recorder.rows) if recorder else 0
    report['correction_steps'] = max(0, report['recorded_steps'] - cycles)
    if recorder:
        recorder.finalize({'passed': report['status'] == 'passed', 'physical_acceptance': report['physical_acceptance'],
                           'recovery': {'kind': 'actual_state_late_expert_correction', 'mode': mode,
                                        'policy_deviation_prefix': report.get('origin')}, 'error': report.get('error')})
    (output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    (output / 'trajectory.json').write_text(json.dumps(rows, allow_nan=False)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--policy-report', type=Path, required=True)
    parser.add_argument('--cycles', type=int, required=True)
    parser.add_argument('--mode', choices=('approach', 'held', 'release'), required=True)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[2] / 'workspaces/so101_ws/src/so101_mujoco/models/so101.xml')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'output' / ('policy-correction-'+uuid.uuid4().hex))
    args = parser.parse_args()
    report = collect(args.reference, args.prefix, args.policy_report, args.source, args.output,
                     cycles=args.cycles, mode=args.mode)
    print(json.dumps({'output': str(args.output), **report}, ensure_ascii=False))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
