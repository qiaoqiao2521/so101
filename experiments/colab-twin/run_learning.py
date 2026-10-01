"""Local learning gates: data -> resource -> bounded sanity -> policy evaluation.

Every child has a wall-time budget. Stage failures preserve artifacts, mark
later stages not_run and return nonzero. --sanity-only explicitly ends after
one physical grasp/place pass. Never allocates cloud or uses hardware.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent


def run(args):
    from learning_data import audit_episodes, load_episode
    sanity_only = bool(getattr(args, 'sanity_only', False))
    train_recovery = bool(getattr(args, 'train_recovery', False))
    chunk_steps = getattr(args, 'execute_chunk_steps', 1)
    projection = getattr(args, 'gripper_projection', None)
    training_options = {
        'action_encoding': getattr(args, 'action_encoding', 'absolute'),
        'velocity_scale_floor': getattr(args, 'velocity_scale_floor', None),
        'no_vae': bool(getattr(args, 'no_vae', False)),
        'dropout': getattr(args, 'dropout', .1),
        'critical_sample_weight': getattr(args, 'critical_sample_weight', 1.0),
        'learning_rate': getattr(args, 'learning_rate', 1e-4),
        'mask_robot_velocity': bool(getattr(args, 'mask_robot_velocity', False)),
        'mask_object_velocity': bool(getattr(args, 'mask_object_velocity', False)),
        'init_checkpoint': (str(args.init_checkpoint.resolve())
                            if getattr(args, 'init_checkpoint', None) else None),
    }
    report = {'status': 'running', 'stages': {name: {'status': 'not_run'} for name in
              ('data', 'data_replay', 'resource', 'sanity_training', 'sanity_task', 'evaluation', 'vision')},
              'expert_actions_used_in_policy_evaluation': False,
              'sanity_only': sanity_only, 'train_recovery': train_recovery,
              'training_options': training_options,
              'adapter_requested': {'execute_chunk_steps': chunk_steps,
                                    'gripper_projection': projection,
                                    'gripper_training_datasets': []}}

    def save():
        temporary = args.output/'report.tmp'
        temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
        temporary.replace(args.output/'report.json')

    def finish():
        if report['status'] == 'running':
            report['status'] = 'stopped'
        save()
        return report

    def child(stage, script, options, timeout):
        destination = args.output/stage
        command = [sys.executable, str(ROOT/script), '--output', str(destination), *options]
        started = time.monotonic()
        row = {'status': 'running', 'command': command, 'wall_budget_s': timeout}
        report['stages'][stage] = row
        save()
        with (args.output/f'{stage}.log').open('w') as log:
            try:
                process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
                row['exit_code'] = process.returncode
                if (destination/'report.json').is_file():
                    row['result'] = json.loads((destination/'report.json').read_text())
                row['status'] = 'failed'
                if 'result' not in row:
                    row['error'] = 'missing_report'
                elif process.returncode == 0:
                    semantic_status = row['result'].get('status')
                    if semantic_status not in ('failed', 'stopped', 'setup_failed', 'timeout'):
                        row['status'] = 'passed'
            except subprocess.TimeoutExpired:
                row['status'] = 'timeout'
        row['wall_s'] = time.monotonic()-started
        save()
        return row

    try:
        # Explicit input archives make acquisition repeatable without silently
        # rerunning a costly or failed experiment. Collector is a separate CLI.
        paths = [p.resolve() for p in args.dataset]
        archive_audit = audit_episodes(paths)
        entries = [load_episode(p) for p in paths]
        positive = [p for p, entry in zip(paths, entries) if entry['eligible_for_training'] and
                    entry['report'].get('metrics', {}).get('place_success') is True]
        nominal = [p for p, entry in zip(paths, entries) if p in positive and not entry['perturbation'].any()]
        recovery = [entry for p, entry in zip(paths, entries) if p in positive and
                    entry['perturbation'].any() and entry['report'].get('recovery')]
        data_go = bool(nominal and recovery and archive_audit['failed_attempt_count'])
        report['stages']['data'] = {'status': 'passed' if data_go else 'failed', 'audit': archive_audit,
            'requires': 'positive grasp/place, physical perturbation recovery, retained failed attempt',
            'training_dataset': str(nominal[0]) if nominal else None}
        training_paths = positive if train_recovery else nominal[:1]
        report['training_datasets'] = list(map(str, training_paths))
        report['training_dataset_selection'] = ('all_positive_nominal_and_recovery' if train_recovery
                                                else 'first_positive_nominal')
        execution_flags = ['--execute-chunk-steps', str(chunk_steps)]
        if projection is not None:
            # Bind support to exactly the archives actually sent to training,
            # never to the larger evaluation reference or retained-failure list.
            support = list(map(str, training_paths))
            report['adapter_requested']['gripper_training_datasets'] = support
            execution_flags.extend(['--gripper-training-dataset', *support,
                                    '--gripper-projection', projection])
        save()
        if not data_go:
            return finish()
        replay = child('data_replay', 'replay_learning_data.py', [str(nominal[0]), '--max-wall-s', '120'], 180)
        if replay['status'] != 'passed' or not replay.get('result', {}).get('trajectory_matches'):
            report['stop_reason'] = 'Stored commands did not reproduce synchronized physical transitions'
            save()
            return finish()
        probe = child('resource', 'learning_probe.py', ['--device', args.device], 180)
        selection = probe.get('result', {}).get('recommendation', 'stop')
        if probe['status'] != 'passed' or selection not in ('act', 'mlp'):
            probe['status'] = 'failed'
            save()
            return finish()
        report['selected_model'] = selection
        training_flags = [
            '--action-encoding', str(training_options['action_encoding']),
            '--dropout', str(training_options['dropout']),
            '--critical-sample-weight', str(training_options['critical_sample_weight']),
            '--learning-rate', str(training_options['learning_rate']),
        ]
        if training_options['velocity_scale_floor'] is not None:
            training_flags.extend(['--velocity-scale-floor', str(training_options['velocity_scale_floor'])])
        if training_options['no_vae']:
            training_flags.append('--no-vae')
        if training_options['mask_robot_velocity']:
            training_flags.append('--mask-robot-velocity')
        if training_options['mask_object_velocity']:
            training_flags.append('--mask-object-velocity')
        if training_options['init_checkpoint']:
            training_flags.extend(['--init-checkpoint', training_options['init_checkpoint']])
        training = child('sanity_training', 'train_state_policy.py',
            ['--dataset', *map(str, training_paths), '--model', selection, '--device', args.device,
             '--max-epochs', '200', '--max-steps', str(args.max_train_steps),
             '--max-wall-s', str(args.max_train_s), *training_flags], args.max_train_s+90)
        if (training['status'] != 'passed' or
                training.get('result', {}).get('status') != 'completed_diagnostic' or
                not training.get('result', {}).get('checkpoint')):
            training['status'] = 'failed'
            save()
            return finish()
        checkpoint = args.output/'sanity_training'/'policy.pt'
        sanity = child('sanity_task', 'evaluate_state_policy.py',
            ['--checkpoint', str(checkpoint), '--dataset', str(nominal[0]), '--device', args.device,
             '--episodes', '1', '--max-wall-s', str(args.max_episode_s), *execution_flags], args.max_episode_s+60)
        sanity_result = sanity.get('result', {})
        if (sanity['status'] != 'passed' or sanity_result.get('status') != 'completed_evaluation' or
                sanity_result.get('summary', {}).get('attempt_count') != 1 or
                sanity_result.get('summary', {}).get('passed_attempt_count') != 1):
            sanity['status'] = 'failed'
            report['stop_reason'] = 'Single training episode did not produce pure-policy physical grasp/place'
            save()
            return finish()
        if sanity_only:
            report['status'] = 'passed_single_episode_gate'
            report['stages']['evaluation']['reason'] = (
                'Requested --sanity-only scope ends after one physical grasp/place pass; 20+20 not requested')
            report['stages']['vision']['reason'] = (
                'Single-episode pass does not establish batch recovery or visual-policy acceptance')
            report['vision_gate'] = 'not_evaluated'
            return finish()
        evaluation = child('evaluation', 'evaluate_state_policy.py',
            ['--checkpoint', str(checkpoint), '--dataset', *map(str, positive), '--device', args.device,
             '--episodes', '20', '--perturbed-episodes', '20', '--max-wall-s', str(args.max_episode_s), *execution_flags],
            40*args.max_episode_s+60)
        result = evaluation.get('result', {})
        summary = result.get('summary', {})
        complete = (result.get('status') == 'completed_evaluation' and
                    summary.get('attempt_count') == 40 and
                    summary.get('nominal', {}).get('attempt_count') == 20 and
                    summary.get('perturbed', {}).get('attempt_count') == 20)
        if not complete:
            evaluation['status'] = 'failed'
            report['stop_reason'] = 'Batch evaluation did not return 20+20 completed attempts'
            save()
            return finish()
        evaluation['status'] = 'completed_evaluation'
        report['vision_gate'] = ('candidate' if (summary.get('nominal', {}).get('success_rate') or 0) >= .85 and
                                (summary.get('perturbed', {}).get('success_rate') or 0) >= .85 else 'no_go')
        report['status'] = 'passed_state_gate' if report['vision_gate'] == 'candidate' else 'stopped'
        report['stages']['vision']['reason'] = 'Separate visual observations/training acceptance required'
        save()
        return finish()
    except Exception as error:
        report['error'] = {'type': type(error).__name__, 'message': str(error)}
        save()
        return finish()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, nargs='+', required=True,
                        help='Include nominal, recovery and retained negative HDF5 archives')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--device', default='cuda')
    parser.add_argument('--max-train-steps', type=int, default=5000)
    parser.add_argument('--max-train-s', type=float, default=120)
    parser.add_argument('--max-episode-s', type=float, default=120)
    parser.add_argument('--sanity-only', action='store_true',
                        help='End successfully after one pure-policy physical grasp/place pass; do not run 20+20')
    parser.add_argument('--train-recovery', action='store_true',
                        help='Train on all audited positive archives, including recovery; default is first nominal only')
    parser.add_argument('--action-encoding', choices=('absolute', 'arm_delta'), default='absolute')
    parser.add_argument('--velocity-scale-floor', type=float, default=None,
                        help='Forward an explicit qvel normalization floor; omitted uses trainer default')
    parser.add_argument('--no-vae', action='store_true')
    parser.add_argument('--dropout', type=float, default=.1)
    parser.add_argument('--critical-sample-weight', type=float, default=1.0)
    parser.add_argument('--learning-rate', type=float, default=1e-4)
    parser.add_argument('--mask-robot-velocity', action='store_true',
                        help='Persist a training/inference ablation of six normalized robot qvel inputs')
    parser.add_argument('--mask-object-velocity', action='store_true',
                        help='Persist a training/inference ablation of normalized object linear/angular velocity inputs')
    parser.add_argument('--init-checkpoint', type=Path,
                        help='Initialize weights and reuse validated training normalization with fresh Adam')
    parser.add_argument('--execute-chunk-steps', type=int, default=1,
                        help='Execution ablation: forward cached chunk length to both policy evaluations')
    parser.add_argument('--gripper-projection', choices=('clip', 'nearest'), default=None,
                        help='Optional execution ablation, fitted only from exact checkpoint training archives')
    args = parser.parse_args()
    if (not all(math.isfinite(v) for v in (args.max_train_s, args.max_episode_s)) or
            min(args.max_train_steps, args.max_train_s, args.max_episode_s) <= 0):
        parser.error('Budgets must be positive')
    if args.velocity_scale_floor is not None and (not math.isfinite(args.velocity_scale_floor) or
                                                 args.velocity_scale_floor < 0):
        parser.error('Velocity scale floor must be finite and nonnegative')
    if not math.isfinite(args.dropout) or not 0 <= args.dropout <= 1:
        parser.error('Dropout must be finite and between zero and one')
    if not math.isfinite(args.critical_sample_weight) or args.critical_sample_weight < 1:
        parser.error('Critical sample weight must be finite and at least one')
    if not math.isfinite(args.learning_rate) or args.learning_rate <= 0:
        parser.error('Learning rate must be finite and positive')
    if args.execute_chunk_steps < 1:
        parser.error('Execute chunk steps must be positive; evaluator checks checkpoint chunk size')
    args.output = (args.output or ROOT/'output'/f'learning-gates-{uuid.uuid4().hex}').resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    result = run(args)
    print(json.dumps({'status': result['status'], 'output': str(args.output),
                      'stages': {k: v['status'] for k,v in result['stages'].items()},
                      'stop_reason': result.get('stop_reason')}, ensure_ascii=False))
    return 0 if result['status'] in ('passed_state_gate', 'passed_single_episode_gate') else 1


if __name__ == '__main__':
    raise SystemExit(main())
