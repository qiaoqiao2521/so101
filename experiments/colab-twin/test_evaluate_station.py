"""The evaluation adapter must never turn missing or cancelled physics into a pass."""
import json
from pathlib import Path
import tempfile
import unittest

from evaluate_station import evaluate, summarize


class EvaluationTests(unittest.TestCase):
    def summary(self, status):
        return summarize(status, run_id='test-run', scenario_path=Path('/scene.json'),
                         output=Path('/run'), candidate={}, scorer={})

    def test_process_success_without_physical_verdict_is_unscored(self):
        result = self.summary({'status': 'succeeded'})
        self.assertFalse(result['passed'])
        self.assertEqual(result['verdict'], 'unscored')

    def test_cancel_does_not_reuse_previous_physical_success(self):
        result = self.summary({'status': 'cancelled', 'report': {'passed': True}})
        self.assertFalse(result['passed'])

    def test_original_failure_reason_and_units_survive(self):
        result = self.summary({'status': 'failed', 'report': {
            'passed': False, 'failure_reason': 'payload_lost', 'simulation_s': 12.3}})
        self.assertEqual(result['failure_reason'], 'payload_lost')
        self.assertEqual(result['metrics']['simulation_s'], 12.3)
        self.assertEqual(result['units']['distance'], 'm')

    def test_physical_success_requires_original_report(self):
        result = self.summary({'status': 'succeeded', 'report': {'passed': True}})
        self.assertTrue(result['passed'])
        self.assertEqual(result['mode'], 'physical_simulation')

    def test_invalid_scene_and_repeated_calls_keep_separate_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scene = root/'bad.json'
            scene.write_text(json.dumps({'nodes': [], 'program': []}))
            output = root/'runs'
            self.assertEqual(evaluate(scene, output), 1)
            first = json.loads((output/'evaluation.json').read_text())
            self.assertEqual(first['verdict'], 'unscored')
            self.assertTrue(first['unsupported'])
            self.assertEqual(evaluate(scene, output), 1)
            second = json.loads((output/'evaluation.json').read_text())
            self.assertNotEqual(first['run_id'], second['run_id'])
            self.assertTrue((output/first['run_id']/'evaluation.json').is_file())
            self.assertTrue((output/second['run_id']/'evaluation.json').is_file())


if __name__ == '__main__':
    unittest.main()
