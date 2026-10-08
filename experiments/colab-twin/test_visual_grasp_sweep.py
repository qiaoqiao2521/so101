"""Controller regressions for interior q6 rejection; fake FK, no physics."""

import unittest
import json
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

import test_visual_grasp_controller as fixtures
import visual_grasp_controller as module


class VisualGraspSweepTests(unittest.TestCase):
    controller = fixtures.VisualControllerTests.controller

    def install_predicate(self, controller, predicate):
        def evaluate(q, *, require_fixed_gripper=True):
            self.assertFalse(require_fixed_gripper)
            q = np.asarray(q)
            self.assertEqual(q.shape, (6,))
            return {'valid': bool(predicate(q))}

        controller.checker.evaluate.side_effect = evaluate

    def test_planned_closure_rejects_interior_jaw_with_safe_endpoints(self):
        controller = self.controller()
        down = controller.down.copy()

        def valid(q):
            return not (np.array_equal(q[:5], down) and .24 < q[5] < .26)

        self.assertTrue(valid(np.r_[down, .5]))
        self.assertTrue(valid(np.r_[down, .015]))
        self.install_predicate(controller, valid)
        with self.assertRaisesRegex(module.ControllerFailure, 'grasp_closure_sweep_invalid'):
            controller._plan_approach(controller.initial_q[:5])
        report = controller.sweep_reports[-1]
        self.assertEqual(report['stage'], 'planned_closure')
        self.assertTrue(.24 < report['invalid_state'][5] < .26)

    def mixed_collision(self, controller):
        origin = float(controller.down[0])
        return lambda q: not (origin + .0008 < q[0] < origin + .0012 and .24 < q[5] < .27)

    def test_measured_closure_precheck_stops_before_first_close_command(self):
        controller = self.controller()
        controller.target_frozen = True
        q = np.r_[controller.down, .5]
        q[0] += .002
        valid = self.mixed_collision(controller)
        self.assertTrue(valid(q))
        self.assertTrue(valid(np.r_[controller.down, .015]))
        # The nominal fixed-arm closure is safe, unlike this measured chord.
        self.assertTrue(all(valid(np.r_[controller.down, jaw]) for jaw in np.linspace(.015, .5, 244)))
        self.install_predicate(controller, valid)
        controller.stage = 'descend'
        controller._set_motion([controller.down, controller.down], .5, 0.)
        result = controller.update(q, np.zeros(6), controller.duration + .61)
        self.assertEqual(result['failure_reason'], 'measured_closure_sweep_invalid')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['stage'], 'descend')
        np.testing.assert_array_equal(result['command'], q)
        self.assertEqual(controller.jaw, .5)
        self.assertEqual(controller.sweep_reports[-1]['stage'], 'measured_closure')

    def test_online_q6_chord_catches_combination_fixed_jaw_check_misses(self):
        controller = self.controller()
        controller.target_frozen = True
        q = np.r_[controller.down, .5]
        q[0] += .002
        valid = self.mixed_collision(controller)
        self.assertTrue(valid(q))
        self.assertTrue(valid(np.r_[controller.down, .015]))
        # Both fixed-q5 jaw sweeps and the old target-jaw arm chord are safe.
        for alpha in np.linspace(0., 1., 244):
            jaw = .5 + (.015 - .5) * alpha
            self.assertTrue(valid(np.r_[q[:5], jaw]))
            self.assertTrue(valid(np.r_[controller.down, jaw]))
            self.assertTrue(valid(np.r_[q[:5] + (controller.down - q[:5]) * alpha, .015]))
        self.install_predicate(controller, valid)
        controller._set_dwell('close', controller.down, .015, 0., 6.)
        result = controller.update(q, np.zeros(6), .1)
        self.assertEqual(result['failure_reason'], 'current_pose_command_chord_invalid')
        self.assertEqual(result['status'], 'failed')
        np.testing.assert_array_equal(result['command'], q)
        self.assertTrue(.24 < controller.last_sweep_report['invalid_state'][5] < .27)

    def track_invocations(self):
        actual, invocations = module.ConfigurationSweepInvocation, []

        def create(*args, **kwargs):
            invocation = actual(*args, **kwargs)
            invocations.append(invocation)
            return invocation

        return patch.object(module, 'ConfigurationSweepInvocation', side_effect=create), invocations

    def test_each_controller_sweep_has_a_fresh_consumed_request_and_original_report(self):
        controller = self.controller()
        controller.checker.reset_mock()
        start = controller.initial_q.copy()
        context, invocations = self.track_invocations()
        with context:
            first = controller._configuration_sweep(start, start)
            second = controller._configuration_sweep(start, start)
        self.assertEqual(len(invocations), 2)
        self.assertIsNot(invocations[0], invocations[1])
        self.assertEqual(controller.checker.evaluate.call_count, 4)
        for invocation in invocations:
            binding = invocation.request.binding
            self.assertIs(binding.owner, controller)
            self.assertIs(binding.checker, controller.checker)
            self.assertIs(binding.model, controller.rig)
            self.assertEqual(binding.stage, controller.stage)
            self.assertEqual(binding.jaw_intent_rad, start[5])
            self.assertEqual(binding.guard_scope, 'arm_q6_chord')
            self.assertEqual(invocation.state, 'consumed')
        self.assertEqual(first, second)
        self.assertTrue(first['valid'])
        self.assertEqual(first['checked_states'], 2)
        self.assertNotIn('binding', first)
        json.dumps(first, allow_nan=False)

    def test_planned_closure_binds_endpoint_intent_before_current_jaw_exists(self):
        context, invocations = self.track_invocations()
        with context:
            controller = self.controller()
        self.assertEqual(len(invocations), 1)
        invocation = invocations[0]
        self.assertEqual(invocation.request.binding.stage, 'approach')
        self.assertEqual(invocation.request.binding.jaw_intent_rad, .015)
        self.assertEqual(invocation.request.endq6[-1], .015)
        self.assertEqual(invocation.state, 'consumed')
        self.assertEqual(controller.sweep_reports[0]['checked_states'], 244)

    def test_invalid_endpoints_keep_legacy_value_error_before_any_geometry(self):
        controller = self.controller()
        start = controller.initial_q.copy()
        invalid = ([], [0.] * 5, [0.] * 7, [0.] * 5 + [np.nan], None)
        for value in invalid:
            for first, last in ((value, start), (start, value)):
                with self.subTest(first=repr(first), last=repr(last)):
                    controller.checker.reset_mock()
                    with self.assertRaises(ValueError):
                        controller._configuration_sweep(first, last)
                    controller.checker.evaluate.assert_not_called()

    def test_generator_endpoints_keep_legacy_values_and_sample_order(self):
        controller = self.controller()
        seen = []
        self.install_predicate(controller, lambda q: seen.append(q.copy()) or True)
        start, end = controller.initial_q.copy(), controller.initial_q.copy()
        end[5] = .015
        report = controller._configuration_sweep((float(x) for x in start),
                                                (float(x) for x in end))
        self.assertTrue(report['valid'])
        self.assertEqual(len(seen), 244)
        self.assertEqual(np.asarray(seen[0]).tobytes(), start.tobytes())
        self.assertEqual(np.asarray(seen[-1]).tobytes(), end.tobytes())

    def test_changed_stage_payload_or_released_hypothesis_rejects_result_consumption(self):
        mutations = {'stage': lambda c: setattr(c, 'stage', 'release'),
                     'payload': lambda c: setattr(c, 'payload_relative', np.array([0., .002, 0.])),
                     'released': lambda c: setattr(c.released_query, 'center', np.array([.24, .15, .02]))}
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                controller = self.controller()
                controller.released_query = SimpleNamespace(model=object(), center=np.zeros(3), uncertainty_m=.002)
                seen = []

                def valid(q):
                    seen.append(q.copy())
                    if len(seen) == 1:
                        mutate(controller)
                    return True

                self.install_predicate(controller, valid)
                context, invocations = self.track_invocations()
                with context, self.assertRaisesRegex(RuntimeError, 'ownership or context changed'):
                    controller._configuration_sweep(controller.initial_q.copy(), controller.initial_q.copy())
                self.assertEqual(len(seen), 2)
                self.assertEqual(len(invocations), 1)
                self.assertEqual(invocations[0].state, 'failed')
                with self.assertRaises(RuntimeError):
                    invocations[0].consume(invocations[0].request.binding)

    def test_checker_exception_has_one_request_no_retry_and_no_report(self):
        controller = self.controller()
        failure = RuntimeError('checker failed during q6 sweep')
        controller.checker.reset_mock()
        controller.checker.evaluate.side_effect = failure
        context, invocations = self.track_invocations()
        with context, self.assertRaises(RuntimeError) as caught:
            controller._configuration_sweep(controller.initial_q.copy(), controller.initial_q.copy())
        self.assertIs(caught.exception, failure)
        self.assertEqual(controller.checker.evaluate.call_count, 1)
        self.assertEqual(len(invocations), 1)
        self.assertEqual(invocations[0].state, 'failed')
        with self.assertRaises(RuntimeError):
            invocations[0].consume(invocations[0].request.binding)

    def test_online_binding_failure_returns_encoder_command_without_claiming_a_sweep(self):
        controller = self.controller()
        controller.target_frozen = True
        controller._set_dwell('close', controller.down, .015, 0., 6.)
        q, seen = np.r_[controller.down, .5], []

        def valid(sample):
            seen.append(sample.copy())
            # update checks the achieved q6 first. Change the hypothesis only
            # inside the new invocation, whose consume must then reject it.
            if len(seen) == 2:
                controller.payload_uncertainty = .003
            return True

        self.install_predicate(controller, valid)
        context, invocations = self.track_invocations()
        with context:
            result = controller.update(q, np.zeros(6), .1)
        self.assertEqual(result['status'], 'failed')
        self.assertIn('ownership or context changed', result['failure_reason'])
        np.testing.assert_array_equal(result['command'], q)
        self.assertEqual(len(invocations), 1)
        self.assertEqual(invocations[0].state, 'failed')
        self.assertFalse(hasattr(controller, 'last_sweep_report'))


if __name__ == '__main__':
    unittest.main()
