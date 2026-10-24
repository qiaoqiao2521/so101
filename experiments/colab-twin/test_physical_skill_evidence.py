"""Observe the real task monitor without copying its acceptance implementation."""
from copy import deepcopy
import unittest

from learning_env import PhysicalTaskMonitor
from physical_skill_evidence import PhysicalSkillEvidence, deliver_evidence


BASELINE_Z = .01


def row(time_s, **changes):
    value = {
        'time_s': time_s, 'elapsed_s': time_s - 100., 'stage': 'hold',
        'object_z_m': BASELINE_Z, 'tip_forces_n': [0., 0.],
        'floor_contact': True, 'place_floor_contact': False,
        'in_place_tray': False, 'object_speed_m_s': 0.,
        'obstacle_contact': False, 'arm_valid': True, 'finite_state': True,
    }
    value.update(changes)
    return value


class PhysicalSkillEvidenceTests(unittest.TestCase):
    def test_display_mutation_and_error_cannot_rewrite_saved_attempt_evidence(self):
        observer = PhysicalSkillEvidence()
        saved = observer.finalize({'passed': False, 'failure_reason': 'planner_cleanup_failed',
                                   'planner_cleanup_errors': [{'error': 'join failed'}]})
        original = deepcopy(saved)

        def display(snapshot):
            snapshot['attempt']['passed'] = True
            snapshot['attempt']['planner_cleanup_errors'].clear()
            raise RuntimeError('display disconnected')

        with self.assertRaisesRegex(RuntimeError, 'display disconnected'):
            deliver_evidence(display, saved)
        self.assertEqual(saved, original)
        self.assertEqual(observer.report(), original)

    def confirmed_grasp(self):
        monitor = PhysicalTaskMonitor(BASELINE_Z)
        evidence = PhysicalSkillEvidence()
        first = row(101., object_z_m=.04, tip_forces_n=[.3, .4], floor_contact=False)
        second = dict(first, time_s=102., elapsed_s=2.)
        self.assertIsNone(evidence.observe(first, monitor.update(first), BASELINE_Z))
        event = evidence.observe(second, monitor.update(second), BASELINE_Z)
        self.assertIsNotNone(event)
        return monitor, evidence, second, event

    def test_close_and_hold_stage_without_monitor_grasp_do_not_emit(self):
        monitor = PhysicalTaskMonitor(BASELINE_Z)
        evidence = PhysicalSkillEvidence()
        for t, stage in [(101., 'close'), (103., 'hold')]:
            sample = row(t, stage=stage)
            self.assertIsNone(evidence.observe(sample, monitor.update(sample), BASELINE_Z))
        report = evidence.report()
        self.assertFalse(report['grasp']['postcondition_met'])
        self.assertEqual(report['events'], [])
        self.assertIsNone(report['attempt']['passed'])
        self.assertEqual(report['observations'], {'count': 2, 'last_elapsed_s': 3.})

    def test_only_exact_true_triggers_not_truthy_stage_or_flag(self):
        evidence = PhysicalSkillEvidence()
        self.assertIsNone(evidence.observe(row(101.), {'grasp_success': 1}, BASELINE_Z))
        self.assertIsNone(evidence.observe(row(102.), {'grasp_success': 'true'}, BASELINE_Z))
        self.assertFalse(evidence.report()['grasp']['postcondition_met'])

    def test_first_real_monitor_confirmation_emits_once_with_original_proof(self):
        monitor, evidence, sample, event = self.confirmed_grasp()
        confirmed_status = monitor.report()
        later = dict(sample, time_s=103., elapsed_s=3.)
        self.assertIsNone(evidence.observe(later, monitor.update(later), BASELINE_Z))
        report = evidence.report()
        self.assertEqual(len(report['events']), 1)
        self.assertEqual(event['skill'], 'Grasp')
        self.assertEqual(event['event'], 'postcondition_met')
        self.assertEqual(event['observation_index'], 1)
        self.assertEqual(report['grasp']['first_met_elapsed_s'], 2.)
        self.assertEqual(event['evidence']['source'], 'PhysicalTaskMonitor.update')
        self.assertEqual(event['evidence']['time_s'], 102.)
        self.assertEqual(event['evidence']['elapsed_s'], 2.)
        self.assertEqual(event['evidence']['stage'], 'hold')
        self.assertEqual(event['evidence']['tip_forces_n'], [.3, .4])
        self.assertAlmostEqual(event['evidence']['lift_m'], .03)
        self.assertEqual(event['evidence']['hold_duration_s'], confirmed_status['hold_duration_s'])
        self.assertIs(event['evidence']['floor_contact'], False)
        self.assertIs(event['evidence']['place_floor_contact'], False)
        self.assertEqual(report['observations'], {'count': 3, 'last_elapsed_s': 3.})

    def test_inputs_event_and_report_are_isolated(self):
        evidence = PhysicalSkillEvidence()
        sample = row(101., tip_forces_n=[.3, .4])
        status = {'grasp_success': True, 'hold_duration_s': 1.25}
        original = deepcopy((sample, status))
        event = evidence.observe(sample, status, BASELINE_Z)
        self.assertEqual((sample, status), original)
        sample['tip_forces_n'][0] = 99
        status['hold_duration_s'] = 99
        event['evidence']['tip_forces_n'][1] = 88
        snapshot = evidence.report()
        snapshot['grasp']['evidence']['tip_forces_n'][0] = 77
        snapshot['events'][0]['evidence']['tip_forces_n'][0] = 66
        current = evidence.report()
        self.assertEqual(current['grasp']['evidence']['tip_forces_n'], [.3, .4])
        self.assertEqual(current['events'][0]['evidence']['tip_forces_n'], [.3, .4])
        self.assertEqual(current['grasp']['evidence']['hold_duration_s'], 1.25)

    def test_later_payload_loss_preserves_historical_grasp_and_original_failure(self):
        monitor, evidence, sample, _ = self.confirmed_grasp()
        lost = dict(sample, time_s=103., elapsed_s=3., tip_forces_n=[0., 0.])
        evidence.observe(lost, monitor.update(lost), BASELINE_Z)
        lost = dict(lost, time_s=103.2, elapsed_s=3.2)
        original = monitor.update(lost)
        evidence.observe(lost, original, BASELINE_Z)
        self.assertEqual(original['failure_reason'], 'payload_lost')
        result = evidence.finalize(original)
        self.assertTrue(result['grasp']['postcondition_met'])
        self.assertIs(result['attempt']['passed'], False)
        self.assertEqual(result['attempt']['failure_reason'], original['failure_reason'])
        self.assertEqual(len(result['events']), 1)

    def test_cancel_and_cleanup_outcomes_are_copied_without_success_inference(self):
        for original in [
            {'passed': False, 'error_type': 'Cancelled', 'failure_reason': 'cancelled', 'safety_stop': False},
            {'passed': False, 'error_type': 'RuntimeError', 'failure_reason': 'planner_cleanup_failed',
             'safety_stop': True, 'planner_cleanup_error': 'join failed',
             'planner_cleanup_errors': [{'worker': 'return', 'error': 'join failed'}]},
        ]:
            with self.subTest(outcome=original):
                _, evidence, _, _ = self.confirmed_grasp()
                before = deepcopy(original)
                result = evidence.finalize(original)
                self.assertEqual(original, before)
                for key, value in original.items():
                    self.assertEqual(result['attempt'][key], value)
                self.assertTrue(result['grasp']['postcondition_met'])
                self.assertEqual(len(result['events']), 1)
                original['planner_cleanup_errors'] = ['changed']
                result['attempt']['planner_cleanup_errors'] = ['changed again']
                self.assertEqual(evidence.report()['attempt']['planner_cleanup_errors'],
                                 before.get('planner_cleanup_errors'))

    def test_absolute_time_is_not_mislabeled_as_elapsed(self):
        evidence = PhysicalSkillEvidence()
        sample = row(101.)
        del sample['elapsed_s']
        event = evidence.observe(sample, {'grasp_success': True}, BASELINE_Z)
        self.assertEqual(event['evidence']['time_s'], 101.)
        self.assertIsNone(event['elapsed_s'])
        self.assertIsNone(evidence.report()['grasp']['first_met_elapsed_s'])
        self.assertEqual(evidence.report()['observations'], {'count': 1, 'last_elapsed_s': None})

    def test_finalize_does_not_count_an_unobserved_terminal_physics_row(self):
        _, evidence, _, _ = self.confirmed_grasp()
        result = evidence.finalize({
            'passed': False, 'error_type': 'Cancelled',
            'failure_reason': 'cancelled', 'safety_stop': False,
            'steps': 3, 'simulation_s': 2.02,
        })
        self.assertEqual(result['observations'], {'count': 2, 'last_elapsed_s': 2.})
        self.assertEqual(result['events'][0]['observation_index'], 1)
        self.assertEqual(result['attempt']['error_type'], 'Cancelled')


if __name__ == '__main__':
    unittest.main()
