"""Controller regressions for interior q6 rejection; fake FK, no physics."""

import unittest
import json
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

import test_visual_grasp_controller as fixtures
import visual_grasp_controller as module
from configuration_sweep import validate_configuration_path


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
        expected = []
        original_report = validate_configuration_path(start, end,
            lambda sample: expected.append(sample) or True)
        self.assertEqual(report, original_report)
        self.assertEqual(np.asarray(seen).tobytes(), np.asarray(expected).tobytes())

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

    def close_controller(self):
        controller = self.controller()
        controller.target_frozen = True
        controller._set_dwell('close', controller.down, .015, 0., 6.)
        return controller

    def completed_invocation(self, controller, start, end, purpose='online_chord'):
        binding = controller._sweep_binding(start, end, purpose)
        invocation = module.ConfigurationSweepInvocation(start, end, binding=binding)
        invocation.execute(lambda q: True)
        return invocation

    def test_initial_observation_is_absent_and_accepted_inputs_are_owned_and_sequenced(self):
        controller = self.close_controller()
        self.assertEqual(controller.observation_seq, 0)
        self.assertIsNone(controller.observation)
        initial = controller._result(controller.initial_q)['gripper']
        for field in ('measured_rad', 'velocity_rad_s', 'target_error_rad', 'observation_seq'):
            self.assertIsNone(initial[field])
        self.assertEqual(initial['contact_evidence'], 'unobserved')
        q = np.r_[controller.down, .2]
        velocity = np.array([0., -.001, .002, 0., -.003, .004])
        first = controller.update(q, velocity, .1)
        self.assertEqual(first['status'], 'running')
        self.assertEqual(controller.observation_seq, 1)
        self.assertEqual(controller.observation,
                         (1, .1, tuple(q), tuple(velocity)))
        q_before, velocity_before = q.copy(), velocity.copy()
        q[:] = 9.
        velocity[:] = 8.
        self.assertEqual(controller.observation,
                         (1, .1, tuple(q_before), tuple(velocity_before)))
        second = controller.update(q_before, velocity_before, .1)
        self.assertEqual(second['status'], 'running')
        self.assertEqual(controller.observation_seq, 2)
        self.assertEqual(second['gripper']['observation_seq'], 2)
        self.assertEqual(second['gripper']['measured_rad'], .2)
        self.assertEqual(second['gripper']['velocity_rad_s'], .004)
        self.assertEqual(second['gripper']['target_error_rad'], .015-.2)

    def test_new_same_pose_observation_rejects_old_result_for_velocity_or_sequence_change(self):
        for changed_velocity in (0., .001):
            with self.subTest(changed_velocity=changed_velocity):
                controller = self.close_controller()
                q, velocity = np.r_[controller.down, .2], np.zeros(6)
                self.assertEqual(controller.update(q, velocity, .1)['status'], 'running')
                invocation = self.completed_invocation(controller, q, controller.reference)
                previous = controller.observation
                velocity[-1] = changed_velocity
                self.assertEqual(controller.update(q, velocity, .1)['status'], 'running')
                self.assertEqual(controller.observation[2], previous[2])
                self.assertEqual(controller.observation[1], previous[1])
                self.assertEqual(controller.observation[0], previous[0]+1)
                self.assertEqual(controller.observation[3][-1], changed_velocity)
                with self.assertRaisesRegex(RuntimeError, 'ownership or context changed'):
                    invocation.consume(controller._sweep_binding(q, controller.reference, 'online_chord'))
                self.assertEqual(invocation.state, 'failed')

    def test_same_sequence_velocity_change_is_also_bound_independently(self):
        controller = self.close_controller()
        q, velocity = np.r_[controller.down, .2], np.zeros(6)
        controller.update(q, velocity, .1)
        invocation = self.completed_invocation(controller, q, controller.reference)
        seq, elapsed, position, old_velocity = controller.observation
        new_velocity = list(old_velocity)
        new_velocity[-1] = -.001
        # Isolate velocity identity from both monotonic counters. The caller
        # normally supplies this tuple only through update's copied encoders.
        controller.observation = (seq, elapsed, position, tuple(new_velocity))
        with self.assertRaisesRegex(RuntimeError, 'ownership or context changed'):
            invocation.consume(controller._sweep_binding(q, controller.reference, 'online_chord'))
        self.assertEqual(invocation.state, 'failed')

    def test_aba_encoder_return_cannot_revive_an_earlier_observation(self):
        controller = self.close_controller()
        a, velocity = np.r_[controller.down, .2], np.zeros(6)
        controller.update(a, velocity, .1)
        before = controller.observation
        invocation = self.completed_invocation(controller, a, controller.reference)
        b = a.copy()
        b[0] += .001
        controller.update(b, velocity, .1)
        controller.update(a, velocity, .1)
        self.assertEqual(controller.observation[1:], before[1:])
        self.assertEqual(controller.observation[0], before[0]+2)
        with self.assertRaisesRegex(RuntimeError, 'ownership or context changed'):
            invocation.consume(controller._sweep_binding(a, controller.reference, 'online_chord'))
        self.assertEqual(invocation.state, 'failed')

    def test_changed_reference_servo_jaw_and_route_context_fail_consumption(self):
        mutations = {
            'reference': lambda c: c.reference.__setitem__(0, c.reference[0]+.001),
            'servo_offset': lambda c: c.servo_offset.__setitem__(0, .001),
            'jaw': lambda c: setattr(c, 'jaw', .2),
            'replans': lambda c: setattr(c, 'replans', c.replans+1),
            'transport_index': lambda c: setattr(c, 'transport_index', c.transport_index+1),
            'target_timestamp': lambda c: setattr(c, 'target_timestamp', .1),
            'target_frozen': lambda c: setattr(c, 'target_frozen', not c.target_frozen),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                controller = self.controller()
                start, end = controller.initial_q.copy(), controller.initial_q.copy()
                seen = []

                def valid(q):
                    seen.append(q.copy())
                    if len(seen) == 1:
                        mutate(controller)
                    return True

                self.install_predicate(controller, valid)
                context, invocations = self.track_invocations()
                with context, self.assertRaisesRegex(RuntimeError, 'ownership or context changed'):
                    controller._configuration_sweep(start, end)
                self.assertEqual(len(seen), 2)
                self.assertEqual(len(invocations), 1)
                self.assertEqual(invocations[0].state, 'failed')

    def test_purpose_and_both_endpoints_cannot_be_substituted_at_consumption(self):
        controller = self.controller()
        start, end = controller.initial_q.copy(), np.r_[controller.down, .015]
        bindings = {purpose: controller._sweep_binding(start, end, purpose)
                    for purpose in ('planned_closure', 'measured_closure', 'online_chord')}
        for first, binding in bindings.items():
            for second, consumer in bindings.items():
                if first == second:
                    self.assertTrue(binding.matches(consumer))
                    continue
                with self.subTest(first=first, second=second):
                    invocation = module.ConfigurationSweepInvocation(start, end, binding=binding)
                    invocation.execute(lambda q: True)
                    with self.assertRaisesRegex(RuntimeError, 'ownership or context changed'):
                        invocation.consume(consumer)
                    self.assertEqual(invocation.state, 'failed')
        for endpoint in ('start', 'end'):
            with self.subTest(endpoint=endpoint):
                invocation = self.completed_invocation(controller, start, end, 'planned_closure')
                changed_start, changed_end = start.copy(), end.copy()
                (changed_start if endpoint == 'start' else changed_end)[0] += .001
                with self.assertRaisesRegex(RuntimeError, 'ownership or context changed'):
                    invocation.consume(controller._sweep_binding(changed_start, changed_end, 'planned_closure'))
        controller.checker.reset_mock()
        with self.assertRaises(ValueError):
            controller._configuration_sweep(start, end, purpose='payload_certificate')
        controller.checker.evaluate.assert_not_called()

    def test_all_three_purposes_preserve_original_samples_and_measured_transition_purpose(self):
        controller = self.controller()
        start, end = np.r_[controller.down, .5], np.r_[controller.down, .015]
        expected = []
        original_report = validate_configuration_path(start, end,
            lambda q: expected.append(q) or True)
        for purpose in ('planned_closure', 'measured_closure', 'online_chord'):
            with self.subTest(purpose=purpose):
                seen = []
                self.install_predicate(controller, lambda q: seen.append(q.copy()) or True)
                report = controller._configuration_sweep(start, end, purpose=purpose)
                self.assertEqual(report, original_report)
                self.assertEqual(np.asarray(seen).tobytes(), np.asarray(expected).tobytes())
        controller.target_frozen = True
        controller.stage = 'descend'
        controller._set_motion([controller.down, controller.down], .5, 0.)
        context, invocations = self.track_invocations()
        with context:
            result = controller.update(start, np.zeros(6), controller.duration+.61)
        self.assertEqual(result['stage'], 'close')
        self.assertEqual(len(invocations), 2)  # preclosure and this update's full chord
        first = invocations[0].request.binding
        # Snapshot the recorded purpose independently of counters that advanced
        # when the update admitted its second online invocation.
        self.assertEqual(dict(first.context)['purpose'], 'measured_closure')
        self.assertEqual(dict(invocations[1].request.binding.context)['purpose'], 'online_chord')

    def test_nested_same_input_invocation_invalidates_the_outer_result(self):
        controller = self.controller()
        q, nested, seen = controller.initial_q.copy(), [], []
        request_seq = controller.sweep_request_seq

        def valid(sample):
            seen.append(sample.copy())
            if not nested:
                nested.append(None)  # prevent recursive nesting by its callback
                nested[0] = controller._configuration_sweep(q, q)
            return True

        self.install_predicate(controller, valid)
        context, invocations = self.track_invocations()
        with context, self.assertRaisesRegex(RuntimeError, 'ownership or context changed'):
            controller._configuration_sweep(q, q)
        self.assertEqual(len(invocations), 2)
        self.assertEqual(len(seen), 4)
        self.assertEqual(controller.sweep_request_seq, request_seq+2)
        self.assertEqual(invocations[0].state, 'failed')
        self.assertEqual(invocations[1].state, 'consumed')
        self.assertTrue(nested[0]['valid'])
        with self.assertRaises(RuntimeError):
            invocations[0].consume(invocations[0].request.binding)

    def test_gripper_reports_stage_intent_without_contact_confirmation(self):
        controller = self.controller()
        q, velocity = np.r_[controller.down, .2], np.zeros(6)
        controller.observation_seq = 7
        controller.observation = (7, .1, tuple(q), tuple(velocity))
        stages = {'close': 'close', 'lift': 'maintain_close', 'hold': 'maintain_close',
                  'transport': 'maintain_close', 'lower': 'maintain_close',
                  'approach': 'open', 'descend': 'open', 'release': 'open',
                  'separate': 'open', 'retreat': 'open', 'settle': 'open',
                  'unknown_stage': 'unspecified'}
        for stage, intent in stages.items():
            with self.subTest(stage=stage):
                controller.stage = stage
                controller.jaw = .015 if intent in ('close', 'maintain_close') else .5
                result = controller._result(q)
                gripper = result['gripper']
                self.assertEqual(gripper, {'intent': intent, 'setpoint_rad': controller.jaw,
                    'measured_rad': .2, 'velocity_rad_s': 0.,
                    'target_error_rad': controller.jaw-.2, 'observation_seq': 7,
                    'contact_evidence': 'unobserved', 'guard_extent': 'full_reference_chord'})
                np.testing.assert_array_equal(result['command'], q)

    def test_same_encoders_with_different_hidden_contact_have_identical_unobserved_metadata(self):
        results = []
        for contact in ({'force_n': 0., 'object_held': False},
                        {'force_n': .2, 'object_held': True}):
            controller = self.close_controller()
            controller.hidden_contact = contact
            q = np.r_[controller.down, .2]
            result = controller.update(q, np.zeros(6), .1)
            self.assertEqual(result['status'], 'running')
            self.assertEqual(result['gripper']['contact_evidence'], 'unobserved')
            self.assertNotIn('confirmed', result['gripper'].values())
            results.append(result)
        self.assertEqual(results[0]['gripper'], results[1]['gripper'])
        np.testing.assert_array_equal(results[0]['command'], results[1]['command'])

    def test_returned_gripper_metadata_is_owned_and_cannot_feed_back_into_control(self):
        controller = self.close_controller()
        q, velocity = np.r_[controller.down, .2], np.zeros(6)
        first = controller.update(q, velocity, .1)
        command, reference = first['command'].copy(), first['geometric_reference'].copy()
        expected = first['gripper'].copy()
        first['gripper'].update(intent='open', setpoint_rad=9., measured_rad=-9.,
                                contact_evidence='confirmed', guard_extent='none', observation_seq=-1)
        self.assertEqual(controller.jaw, .015)
        second = controller.update(q, velocity, .2)
        self.assertEqual(second['status'], 'running')
        np.testing.assert_array_equal(second['command'], command)
        np.testing.assert_array_equal(second['geometric_reference'], reference)
        expected['observation_seq'] = 2
        self.assertEqual(second['gripper'], expected)
        self.assertIsNot(first['gripper'], second['gripper'])


if __name__ == '__main__':
    unittest.main()
