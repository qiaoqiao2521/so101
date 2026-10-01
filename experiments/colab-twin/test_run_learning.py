"""Child exit zero cannot bypass failed or missing learning gate evidence."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from run_learning import main, run


class LearningGateStopTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name)
        self.args = argparse.Namespace(
            dataset=[self.output / name for name in ('nominal.h5', 'recovery.h5', 'failed.h5')],
            output=self.output, device='cpu', max_train_steps=5,
            max_train_s=1., max_episode_s=1.,
        )

    @staticmethod
    def episode(path):
        failed = path.name == 'failed.h5'
        recovery = path.name.startswith('recovery')
        return {'eligible_for_training': not failed,
                'perturbation': np.array([recovery], dtype=bool),
                'report': {'passed': not failed, 'metrics': {'place_success': not failed},
                           'recovery': {'kind': 'physical_replan'} if recovery else None}}

    def exercise(self, responses, expected_status='stopped'):
        called = []
        self.commands = {}
        responses = {'data_replay': {'status': 'passed', 'trajectory_matches': True}, **responses}

        def subprocess_result(command, **unused):
            destination = Path(command[command.index('--output') + 1])
            stage = destination.name
            called.append(stage)
            self.commands[stage] = command
            if stage not in responses:
                self.fail('A stopped workflow invoked an unauthorized later stage: ' + stage)
            report = responses[stage]
            if report is not None:
                destination.mkdir()
                (destination / 'report.json').write_text(json.dumps(report))
            return subprocess.CompletedProcess(command, 0)

        with patch('learning_data.audit_episodes', return_value={'failed_attempt_count': 1}), \
                patch('learning_data.load_episode', side_effect=self.episode), \
                patch('run_learning.subprocess.run', side_effect=subprocess_result):
            report = run(self.args)
        self.assertEqual(report['status'], expected_status)
        self.assertEqual(json.loads((self.output / 'report.json').read_text()), report)
        return report, called

    @staticmethod
    def successful_sanity():
        return {
            'resource': {'recommendation': 'act'},
            'sanity_training': {'status': 'completed_diagnostic', 'checkpoint': {'filename': 'policy.pt'}},
            'sanity_task': {'status': 'completed_evaluation',
                            'summary': {'attempt_count': 1, 'passed_attempt_count': 1,
                                        'failed_attempt_count': 0}},
        }

    def test_exit_zero_without_resource_report_stops_before_training(self):
        report, called = self.exercise({'resource': None})
        self.assertEqual(called, ['data_replay', 'resource'])
        self.assertEqual(report['stages']['resource']['status'], 'failed')
        for stage in ('sanity_training', 'sanity_task', 'evaluation', 'vision'):
            self.assertEqual(report['stages'][stage]['status'], 'not_run')

    def test_exit_zero_failed_training_report_stops_before_policy_task(self):
        report, called = self.exercise({
            'resource': {'recommendation': 'act'},
            'sanity_training': {'status': 'failed', 'checkpoint': {'filename': 'partial-policy.pt'}},
        })
        self.assertEqual(called, ['data_replay', 'resource', 'sanity_training'])
        self.assertEqual(report['stages']['sanity_training']['status'], 'failed')
        for stage in ('sanity_task', 'evaluation', 'vision'):
            self.assertEqual(report['stages'][stage]['status'], 'not_run')

    def test_exit_zero_physical_sanity_failure_stops_before_twenty_plus_twenty(self):
        report, called = self.exercise({
            'resource': {'recommendation': 'act'},
            'sanity_training': {'status': 'completed_diagnostic',
                                'checkpoint': {'filename': 'policy.pt'}},
            'sanity_task': {'status': 'completed_evaluation',
                            'summary': {'attempt_count': 1, 'passed_attempt_count': 0,
                                        'failed_attempt_count': 1}},
        })
        self.assertEqual(called, ['data_replay', 'resource', 'sanity_training', 'sanity_task'])
        self.assertEqual(report['stages']['sanity_task']['status'], 'failed')
        self.assertEqual(report['stages']['evaluation']['status'], 'not_run')
        self.assertEqual(report['stages']['vision']['status'], 'not_run')
        self.assertIn('pure-policy', report['stop_reason'])

    def test_sanity_only_success_does_not_run_batch_or_vision(self):
        self.args.sanity_only = True
        report, called = self.exercise(self.successful_sanity(), 'passed_single_episode_gate')
        self.assertEqual(called, ['data_replay', 'resource', 'sanity_training', 'sanity_task'])
        for stage in ('evaluation', 'vision'):
            self.assertEqual(report['stages'][stage]['status'], 'not_run')
            self.assertTrue(report['stages'][stage]['reason'])
        self.assertEqual(report['vision_gate'], 'not_evaluated')

    def test_sanity_only_failure_still_returns_stopped(self):
        self.args.sanity_only = True
        responses = self.successful_sanity()
        responses['sanity_task']['summary']['passed_attempt_count'] = 0
        responses['sanity_task']['summary']['failed_attempt_count'] = 1
        report, called = self.exercise(responses)
        self.assertEqual(called[-1], 'sanity_task')
        self.assertEqual(report['stages']['evaluation']['status'], 'not_run')

    def test_default_success_continues_to_twenty_plus_twenty(self):
        responses = self.successful_sanity()
        responses['evaluation'] = {'status': 'completed_evaluation',
            'summary': {'attempt_count': 40,
                        'nominal': {'attempt_count': 20, 'success_rate': .9},
                        'perturbed': {'attempt_count': 20, 'success_rate': .9}}}
        report, called = self.exercise(responses, 'passed_state_gate')
        self.assertEqual(called[-1], 'evaluation')
        command = self.commands['evaluation']
        self.assertEqual(command[command.index('--episodes') + 1], '20')
        self.assertEqual(command[command.index('--perturbed-episodes') + 1], '20')
        self.assertEqual(report['training_datasets'], [str(self.args.dataset[0])])
        self.assertNotIn('--no-vae', self.commands['sanity_training'])
        self.assertNotIn('--velocity-scale-floor', self.commands['sanity_training'])
        for stage in ('sanity_task', 'evaluation'):
            command = self.commands[stage]
            self.assertEqual(command[command.index('--execute-chunk-steps') + 1], '1')
            self.assertNotIn('--gripper-training-dataset', command)
            self.assertNotIn('--gripper-projection', command)
        self.assertEqual(report['adapter_requested'], {'execute_chunk_steps': 1,
            'gripper_projection': None, 'gripper_training_datasets': []})

    def test_training_parameters_and_positive_recovery_paths_are_forwarded(self):
        self.args.sanity_only = True
        self.args.train_recovery = True
        self.args.action_encoding = 'arm_delta'
        self.args.velocity_scale_floor = .3
        self.args.no_vae = True
        self.args.dropout = 0.
        self.args.critical_sample_weight = 8.
        self.args.learning_rate = 2e-4
        self.args.mask_robot_velocity = True
        self.args.mask_object_velocity = True
        self.args.init_checkpoint = self.output/'previous-policy.pt'
        report, _ = self.exercise(self.successful_sanity(), 'passed_single_episode_gate')
        command = self.commands['sanity_training']
        for flag, value in (('--action-encoding', 'arm_delta'), ('--velocity-scale-floor', '0.3'),
                            ('--dropout', '0.0'), ('--critical-sample-weight', '8.0'),
                            ('--learning-rate', '0.0002')):
            self.assertEqual(command[command.index(flag) + 1], value)
        self.assertIn('--no-vae', command)
        self.assertIn('--mask-robot-velocity', command)
        self.assertIn('--mask-object-velocity', command)
        self.assertEqual(command[command.index('--init-checkpoint') + 1], str(self.args.init_checkpoint.resolve()))
        self.assertTrue(report['training_options']['mask_robot_velocity'])
        self.assertTrue(report['training_options']['mask_object_velocity'])
        self.assertEqual(report['training_options']['init_checkpoint'], str(self.args.init_checkpoint.resolve()))
        self.assertEqual(command[command.index('--dataset') + 1:command.index('--model')],
                         list(map(str, self.args.dataset[:2])))
        self.assertNotIn(str(self.args.dataset[2]), command)
        self.assertEqual(report['training_datasets'], list(map(str, self.args.dataset[:2])))
        self.assertEqual(report['training_dataset_selection'], 'all_positive_nominal_and_recovery')

    def test_cli_single_episode_success_returns_zero_and_preserves_defaults(self):
        destination = self.output / 'cli-output'
        captured = {}

        def result(args):
            captured.update(vars(args))
            return {'status': 'passed_single_episode_gate', 'stages': {}, 'stop_reason': None}

        with patch('sys.argv', ['run_learning.py', '--dataset', 'nominal.h5',
                                '--output', str(destination), '--device', 'cpu', '--sanity-only']), \
                patch('run_learning.run', side_effect=result), patch('builtins.print'):
            self.assertEqual(main(), 0)
        self.assertTrue(captured['sanity_only'])
        self.assertFalse(captured['train_recovery'])
        self.assertEqual(captured['action_encoding'], 'absolute')
        self.assertIsNone(captured['velocity_scale_floor'])
        self.assertEqual(captured['dropout'], .1)
        self.assertEqual(captured['critical_sample_weight'], 1.)
        self.assertEqual(captured['learning_rate'], 1e-4)
        self.assertFalse(captured['mask_robot_velocity'])
        self.assertFalse(captured['mask_object_velocity'])
        self.assertIsNone(captured['init_checkpoint'])
        self.assertEqual(captured['execute_chunk_steps'], 1)
        self.assertIsNone(captured['gripper_projection'])

    def test_four_positive_training_archives_bind_both_execution_adapters(self):
        self.args.dataset = [self.output / name for name in (
            'nominal.h5', 'recovery.h5', 'recovery2.h5', 'recovery3.h5', 'failed.h5')]
        self.args.train_recovery = True
        self.args.execute_chunk_steps = 16
        self.args.gripper_projection = 'nearest'
        responses = self.successful_sanity()
        responses['evaluation'] = {'status': 'completed_evaluation',
            'summary': {'attempt_count': 40,
                        'nominal': {'attempt_count': 20, 'success_rate': .9},
                        'perturbed': {'attempt_count': 20, 'success_rate': .9}}}
        report, _ = self.exercise(responses, 'passed_state_gate')
        expected = list(map(str, self.args.dataset[:4]))
        train_command = self.commands['sanity_training']
        self.assertEqual(train_command[train_command.index('--dataset') + 1:train_command.index('--model')], expected)
        for stage in ('sanity_task', 'evaluation'):
            command = self.commands[stage]
            support = command[command.index('--gripper-training-dataset') + 1:command.index('--gripper-projection')]
            self.assertEqual(support, expected)
            self.assertEqual(command[command.index('--execute-chunk-steps') + 1], '16')
            self.assertEqual(command[command.index('--gripper-projection') + 1], 'nearest')
            self.assertNotIn(str(self.args.dataset[4]), command)
        self.assertEqual(report['adapter_requested']['gripper_training_datasets'], expected)

    def test_default_nominal_projection_support_excludes_recovery_reference(self):
        self.args.gripper_projection = 'clip'
        responses = self.successful_sanity()
        responses['evaluation'] = {'status': 'completed_evaluation',
            'summary': {'attempt_count': 40,
                        'nominal': {'attempt_count': 20, 'success_rate': .9},
                        'perturbed': {'attempt_count': 20, 'success_rate': .9}}}
        report, _ = self.exercise(responses, 'passed_state_gate')
        for stage in ('sanity_task', 'evaluation'):
            command = self.commands[stage]
            support = command[command.index('--gripper-training-dataset') + 1:command.index('--gripper-projection')]
            self.assertEqual(support, [str(self.args.dataset[0])])
        evaluation = self.commands['evaluation']
        references = evaluation[evaluation.index('--dataset') + 1:evaluation.index('--device')]
        self.assertEqual(references, list(map(str, self.args.dataset[:2])))
        self.assertEqual(report['adapter_requested']['gripper_training_datasets'], [str(self.args.dataset[0])])

    def test_sanity_only_with_adapters_passes_without_running_batch(self):
        self.args.sanity_only = True
        self.args.execute_chunk_steps = 16
        self.args.gripper_projection = 'nearest'
        report, called = self.exercise(self.successful_sanity(), 'passed_single_episode_gate')
        self.assertNotIn('evaluation', called)
        self.assertEqual(report['stages']['evaluation']['status'], 'not_run')
        self.assertEqual(report['adapter_requested']['execute_chunk_steps'], 16)
        self.assertEqual(report['adapter_requested']['gripper_projection'], 'nearest')


if __name__ == '__main__':
    unittest.main()
