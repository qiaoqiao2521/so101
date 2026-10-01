"""Child exit zero cannot bypass failed or missing learning gate evidence."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from run_learning import run


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
        recovery = path.name == 'recovery.h5'
        return {'eligible_for_training': not failed,
                'perturbation': np.array([recovery], dtype=bool),
                'report': {'passed': not failed, 'metrics': {'place_success': not failed},
                           'recovery': {'kind': 'physical_replan'} if recovery else None}}

    def exercise(self, responses):
        called = []
        responses = {'data_replay': {'status': 'passed', 'trajectory_matches': True}, **responses}

        def subprocess_result(command, **unused):
            destination = Path(command[command.index('--output') + 1])
            stage = destination.name
            called.append(stage)
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
        self.assertEqual(report['status'], 'stopped')
        self.assertEqual(json.loads((self.output / 'report.json').read_text()), report)
        return report, called

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


if __name__ == '__main__':
    unittest.main()
