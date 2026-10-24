"""Opt-in pickup jaw sequencing with the original guards; fake FK, no physics."""
from dataclasses import replace
import unittest
from unittest.mock import patch

import numpy as np

import test_visual_grasp_controller as fixtures
import visual_grasp_controller as module


class PickupPrecloseTests(unittest.TestCase):
    controller = fixtures.VisualControllerTests.controller

    def arrive_high(self, controller, jaw=.5):
        controller.target_frozen = True
        q = np.r_[controller.approach, jaw]
        elapsed = controller.stage_started + controller.duration + .61
        result = controller.update(q, np.zeros(6), elapsed)
        return q, elapsed, result

    def test_default_keeps_original_descent_and_244_point_closure(self):
        controller = self.controller()
        self.assertEqual(controller.pickup_open_jaw_rad, .5)
        self.assertEqual(controller.sweep_reports[0]['checked_states'], 244)
        self.assertEqual(controller.sweep_reports[0]['jaw_resolution_rad'], .002)
        _, _, result = self.arrive_high(controller)
        self.assertEqual(result['stage'], 'descend')
        self.assertEqual(controller.jaw, .5)
        self.assertEqual([r['stage'] for r in controller.sweep_reports], ['planned_closure'])

    def test_only_explicit_supported_jaw_values_are_accepted(self):
        for invalid in (True, np.bool_(False), '.35', .34, .36, np.nan, np.inf, None):
            with self.subTest(jaw=invalid), self.assertRaisesRegex(ValueError, 'pickup_open_jaw_rad'):
                self.controller(pickup_open_jaw_rad=invalid)

    def test_candidate_keeps_open_approach_but_validates_descent_with_point35(self):
        controller = self.controller(pickup_open_jaw_rad=.35)
        self.assertEqual(controller.jaw, .5)
        np.testing.assert_array_equal(controller.points, controller.approach_path)
        seen = []
        controller._arm_valid = lambda q, jaw: seen.append((np.asarray(q).copy(), jaw)) or True
        controller._plan_approach(controller.initial_q[:5])
        self.assertEqual({jaw for _, jaw in seen}, {.35, .015})
        planned = controller.sweep_reports[-1]
        self.assertEqual(planned['stage'], 'planned_closure')
        self.assertTrue(planned['valid'])
        self.assertGreaterEqual(planned['checked_states'], 244)
        self.assertLess(planned['jaw_resolution_rad'], .002)

    def test_handover_is_required_before_preclose(self):
        controller = self.controller(pickup_open_jaw_rad=.35)
        with self.assertRaisesRegex(module.ControllerFailure, 'visual_handover'):
            controller._transition(np.r_[controller.approach, .5], 5.)
        self.assertEqual(controller.stage, 'approach')
        self.assertEqual(len(controller.sweep_reports), 1)

    def test_preclose_sweeps_actual_pose_before_holding_high(self):
        controller = self.controller(pickup_open_jaw_rad=.35)
        q, _, result = self.arrive_high(controller)
        self.assertEqual(result['stage'], 'preclose')
        self.assertEqual(controller._jaw_intent(), 'close')
        self.assertEqual(result['geometric_reference'][5], .35)
        np.testing.assert_array_equal(result['command'][:5], q[:5])
        np.testing.assert_array_equal(controller.points, [q[:5], q[:5]])
        report = controller.sweep_reports[-1]
        self.assertEqual(report['stage'], 'pickup_preclose')
        self.assertTrue(report['valid'])
        self.assertGreaterEqual(report['checked_states'], 244)

    def test_time_alone_and_unsettled_jaw_cannot_admit_descent(self):
        controller = self.controller(pickup_open_jaw_rad=.35)
        q, started, _ = self.arrive_high(controller)
        for measured, velocity, delay in [(.5, 0., 1.3), (.354, 0., 1.5), (.35, .06, 1.7)]:
            with self.subTest(measured=measured, velocity=velocity):
                q[5] = measured
                qvel = np.zeros(6); qvel[5] = velocity
                result = controller.update(q, qvel, started+delay)
                self.assertEqual(result['stage'], 'preclose')
                self.assertEqual(controller.stage_started, started)
                np.testing.assert_array_equal(result['command'][:5], q[:5])
        q[5] = .35
        result = controller.update(q, np.zeros(6), started+1.9)
        self.assertEqual(result['stage'], 'descend')
        self.assertEqual(controller.jaw, .35)
        np.testing.assert_array_equal(controller.points, [q[:5], controller.down])
        np.testing.assert_array_equal(result['command'][:5], q[:5])

    def test_wait_preserves_original_stage_and_global_timeouts(self):
        controller = self.controller(pickup_open_jaw_rad=.35)
        q, started, _ = self.arrive_high(controller)
        result = controller.update(q, np.zeros(6), started+controller.duration+8.01)
        self.assertEqual(result['failure_reason'], 'encoder_stage_timeout')
        self.assertEqual(controller.stage_started, started)
        controller = self.controller(pickup_open_jaw_rad=.35)
        q, _, _ = self.arrive_high(controller)
        self.assertEqual(controller.update(q, np.zeros(6), 90.01)['failure_reason'],
                         'invalid_or_expired_controller_time')

    def test_bad_high_sweep_stops_before_preclose_or_descent(self):
        controller = self.controller(pickup_open_jaw_rad=.35)
        controller.checker.evaluate.side_effect = lambda q, **kw: {'valid': not (.41 < q[5] < .42)}
        with patch.object(controller, '_set_dwell', wraps=controller._set_dwell) as dwell:
            q, _, result = self.arrive_high(controller)
        self.assertEqual(result['failure_reason'], 'pickup_preclose_sweep_invalid')
        self.assertEqual(result['stage'], 'approach')
        dwell.assert_not_called()
        np.testing.assert_array_equal(result['command'], q)
        self.assertGreaterEqual(controller.sweep_reports[-1]['required_states'], 244)

    def test_measured_low_closure_retains_at_least_244_checks(self):
        controller = self.controller(pickup_open_jaw_rad=.35)
        controller.target_frozen = True
        controller.stage = 'descend'
        controller._set_motion([controller.down, controller.down], .35, 0.)
        result = controller.update(np.r_[controller.down, .35], np.zeros(6), controller.duration+.61)
        self.assertEqual(result['stage'], 'close')
        report = controller.sweep_reports[-1]
        self.assertEqual(report['stage'], 'measured_closure')
        self.assertTrue(report['valid'])
        self.assertGreaterEqual(report['checked_states'], 244)

    def test_zero_motion_preclose_uses_original_static_check(self):
        controller = self.controller(pickup_open_jaw_rad=.35)
        _, _, result = self.arrive_high(controller, jaw=.35)
        self.assertEqual(result['stage'], 'preclose')
        self.assertTrue(controller.sweep_reports[-1]['valid'])
        self.assertEqual(controller.sweep_reports[-1]['checked_states'], 2)

    def test_preclose_smooth_reference_uses_captured_command_and_same_high_pose(self):
        controller = self.controller(pickup_open_jaw_rad=.35)
        controller.route_policy = replace(controller.route_policy, smooth_jaw_dwell=True)
        q, started, result = self.arrive_high(controller)
        self.assertEqual(result['geometric_reference'][5], .5)
        result = controller.update(q, np.zeros(6), started+.3)
        self.assertAlmostEqual(result['geometric_reference'][5], .425)
        np.testing.assert_array_equal(result['command'][:5], q[:5])

    def test_new_sweep_input_is_bound_only_for_opt_in(self):
        for jaw, included in [(.5, False), (.35, True)]:
            controller = self.controller(pickup_open_jaw_rad=jaw)
            q = controller.initial_q
            binding = controller._sweep_binding(q, q, 'measured_closure')
            self.assertEqual('pickup_open_jaw_rad' in dict(binding.context), included)


if __name__ == '__main__':
    unittest.main()
