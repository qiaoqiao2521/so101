"""Exercise operator sequencing and original-result preservation without physics."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import warnings
from unittest.mock import patch

from carry_gate import CarryGate


class CarryGateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.marker = Path(self.temporary.name)/'carry-resume.request'
        self.q6 = [0., .1, .2, .3, .4, .5]

    def test_pending_is_not_a_release_or_a_wait(self):
        gate = CarryGate(self.marker)
        snapshot = gate.report()
        self.assertEqual(snapshot['state'], 'pending')
        self.assertIsNone(snapshot['waiting_since_s'])
        self.assertIsNone(snapshot['released_at_s'])
        self.assertEqual(snapshot['events'], [])
        self.assertFalse(self.marker.exists())

    def test_repeated_wait_keeps_one_transition_and_reports_observed_duration(self):
        changes = []
        gate = CarryGate(self.marker, on_change=changes.append)
        self.assertFalse(gate(self.q6, 10.))
        self.assertFalse(gate(self.q6, 11.))
        self.assertFalse(gate(self.q6, 12.))
        snapshot = gate.report()
        self.assertEqual(snapshot['state'], 'waiting')
        self.assertEqual(snapshot['waiting_since_s'], 10.)
        self.assertEqual(snapshot['wait_s'], 2.)
        self.assertEqual([event['event'] for event in snapshot['events']], ['waiting'])
        self.assertEqual(len(changes), 1)
        self.assertFalse(self.marker.exists())

    def test_release_is_once_and_does_not_read_marker_on_later_calls(self):
        changes = []
        gate = CarryGate(self.marker, on_change=changes.append)
        self.assertFalse(gate(self.q6, 10.))
        self.marker.touch()
        self.assertTrue(gate(self.q6, 11.))
        self.marker.unlink()
        with patch.object(Path, 'exists', side_effect=AssertionError('Already released')):
            self.assertTrue(gate(self.q6, 12.))
        snapshot = gate.report()
        self.assertEqual(snapshot['released_at_s'], 11.)
        self.assertEqual(snapshot['wait_s'], 1.)
        self.assertEqual([event['event'] for event in snapshot['events']], ['waiting', 'released'])
        self.assertEqual(len(changes), 2)

    def test_early_marker_is_explicitly_rejected_and_never_removed(self):
        self.marker.touch()
        gate = CarryGate(self.marker)
        with self.assertRaisesRegex(RuntimeError, 'carry_resume_before_waiting'):
            gate(self.q6, 10.)
        self.assertEqual(gate.report()['state'], 'pending')
        self.assertIsNone(gate.report()['released_at_s'])
        self.assertTrue(self.marker.exists())

    def test_finalize_keeps_wait_and_original_timeout_or_cancellation(self):
        for original in [
            {'passed': False, 'failure_reason': 'stage_timeout', 'simulation_s': 20.},
            {'passed': False, 'error_type': 'Cancelled', 'failure_reason': 'operator stopped',
             'cancelled': True, 'simulation_s': 11., 'planner_cleanup_error': None},
        ]:
            with self.subTest(original=original):
                gate = CarryGate(self.marker)
                gate(self.q6, 10.)
                before = deepcopy(original)
                snapshot = gate.finalize(original)
                self.assertEqual(original, before)
                self.assertEqual(snapshot['state'], 'ended')
                self.assertEqual(snapshot['events'][0]['event'], 'waiting')
                self.assertIsNone(snapshot['released_at_s'])
                for key in ('passed', 'error_type', 'failure_reason', 'cancelled'):
                    self.assertEqual(snapshot['attempt'][key], original.get(key))
                with self.assertRaisesRegex(RuntimeError, 'carry_gate_ended'):
                    gate(self.q6, 21.)

    def test_finalize_preserves_release_then_later_failure_and_is_idempotent(self):
        gate = CarryGate(self.marker)
        gate(self.q6, 10.)
        self.marker.touch()
        gate(self.q6, 11.)
        original = {'passed': False, 'failure_reason': 'payload_lost', 'simulation_s': 30.}
        snapshot = gate.finalize(original)
        self.assertEqual(snapshot['released_at_s'], 11.)
        self.assertEqual(snapshot['wait_s'], 1.)
        self.assertEqual(snapshot['attempt']['failure_reason'], 'payload_lost')
        self.assertEqual([event['event'] for event in snapshot['events']],
                         ['waiting', 'released', 'ended'])
        self.assertEqual(gate.finalize(original), snapshot)

    def test_callbacks_reports_and_original_input_are_isolated(self):
        def mutate(snapshot):
            snapshot['events'][0]['q6'][0] = 99.
            snapshot['state'] = 'released'
        gate = CarryGate(self.marker, on_change=mutate)
        original_q = self.q6.copy()
        self.assertFalse(gate(self.q6, 10.))
        self.assertEqual(self.q6, original_q)
        self.q6[0] = 88.
        first = gate.report()
        first['events'][0]['q6'][1] = 77.
        self.assertEqual(gate.report()['events'][0]['q6'], original_q)
        self.assertEqual(gate.report()['state'], 'waiting')

    def test_optional_observer_failure_does_not_change_operator_release(self):
        def broken(snapshot):
            raise ValueError('viewer unavailable')
        gate = CarryGate(self.marker, on_change=broken)
        with self.assertWarnsRegex(UserWarning, 'observation callback failed'):
            self.assertFalse(gate(self.q6, 10.))
        self.marker.touch()
        with self.assertWarnsRegex(UserWarning, 'observation callback failed'):
            self.assertTrue(gate(self.q6, 11.))
        self.assertEqual(gate.report()['state'], 'released')
        self.assertEqual(len(gate.report()['callback_errors']), 2)

    def test_observer_failure_with_warnings_as_errors_preserves_gate_and_final_report(self):
        def broken(snapshot):
            snapshot['state'] = 'released'
            raise ValueError('viewer unavailable')

        original = {'passed': False, 'failure_reason': 'payload_lost', 'simulation_s': 30.,
                    'planner_cleanup_errors': [{'planner': 'return', 'error': 'join failed'}]}
        before = deepcopy(original)
        gate = CarryGate(self.marker, on_change=broken)
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            self.assertFalse(gate(self.q6, 10.))
            self.assertEqual(gate.report()['state'], 'waiting')
            self.marker.touch()
            self.assertTrue(gate(self.q6, 11.))
            snapshot = gate.finalize(original)
        self.assertEqual(original, before)
        self.assertEqual(snapshot['state'], 'ended')
        self.assertEqual(snapshot['released_at_s'], 11.)
        self.assertFalse(snapshot['attempt']['passed'])
        self.assertEqual(snapshot['attempt']['failure_reason'], 'payload_lost')
        self.assertEqual(snapshot['attempt']['planner_cleanup_errors'], original['planner_cleanup_errors'])
        self.assertEqual(len(snapshot['callback_errors']), 3)
        self.assertEqual([event['event'] for event in snapshot['events']],
                         ['waiting', 'released', 'ended'])


if __name__ == '__main__':
    unittest.main()
