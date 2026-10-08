"""Sampling-contract tests without a model, IK, or physics."""

import json
import math
import struct
import unittest
from dataclasses import FrozenInstanceError, replace

from configuration_sweep import (ConfigurationSweepInvocation, SweepBinding,
                                 validate_configuration_path)


class ConfigurationSweepTests(unittest.TestCase):
    def test_complete_jaw_closure_preserves_endpoints_and_spacing(self):
        start, end = [0., 0., 0., 0., 0., .5], [0., 0., 0., 0., 0., .015]
        seen = []
        report = validate_configuration_path(start, end, lambda q: seen.append(q) or True)
        self.assertTrue(report['valid'], report)
        self.assertEqual(report['checked_states'], 244)
        self.assertEqual(seen[0], start)
        self.assertEqual(seen[-1], end)
        self.assertEqual(report['max_arm_step_rad'], 0.)
        self.assertLessEqual(report['max_jaw_step_rad'], .002)
        self.assertTrue(all(q[:5] == start[:5] for q in seen))
        json.dumps(report, allow_nan=False)

    def test_arm_l2_and_jaw_spacing_are_independent(self):
        start, end = [0.] * 6, [.01, .02, .03, .04, .05, .01]
        seen = []
        report = validate_configuration_path(start, end, lambda q: seen.append(q) or True)
        self.assertTrue(report['valid'], report)
        self.assertEqual(report['checked_states'], 16)
        self.assertLessEqual(max(math.dist(a[:5], b[:5]) for a, b in zip(seen, seen[1:])), .005)
        self.assertLessEqual(max(abs(a[5] - b[5]) for a, b in zip(seen, seen[1:])), .002)
        self.assertEqual(seen[0], start)
        self.assertEqual(seen[-1], end)

    def test_budget_refuses_path_instead_of_deleting_samples(self):
        seen = []
        start, end = [0.] * 5 + [.5], [0.] * 5 + [.015]
        report = validate_configuration_path(start, end, lambda q: seen.append(q) or True, max_samples=243)
        self.assertFalse(report['valid'])
        self.assertEqual(report['reason'], 'sample_budget_exceeded')
        self.assertEqual(report['required_states'], 244)
        self.assertEqual(report['checked_states'], 0)
        self.assertEqual(seen, [])
        self.assertTrue(validate_configuration_path(start, end, lambda q: True, max_samples=244)['valid'])

    def test_first_intermediate_collision_stops_and_identifies_q6(self):
        start, end = [0.] * 5 + [.5], [0.] * 5 + [.015]
        seen = []

        def valid(q):
            seen.append(q)
            return not .24 < q[5] < .26

        report = validate_configuration_path(start, end, valid)
        self.assertFalse(report['valid'])
        self.assertEqual(report['reason'], 'invalid_state')
        self.assertGreater(report['checked_states'], 2)
        self.assertEqual(report['invalid_sample_index'] + 1, report['checked_states'])
        self.assertEqual(report['invalid_state'], seen[-1])
        self.assertTrue(.24 < report['invalid_state'][5] < .26)
        self.assertLess(report['checked_states'], report['required_states'])
        json.dumps(report, allow_nan=False)

    def test_zero_path_and_exact_single_step_keep_both_endpoints(self):
        start = [0.] * 6
        for end in (start, [.005, 0., 0., 0., 0., .002]):
            seen = []
            report = validate_configuration_path(start, end, lambda q: seen.append(q) or True, max_samples=2)
            self.assertTrue(report['valid'], report)
            self.assertEqual(seen, [start, end])
        report = validate_configuration_path(start, start, lambda q: True, max_samples=1)
        self.assertEqual(report['reason'], 'sample_budget_exceeded')

    def test_bad_inputs_raise_and_callback_errors_are_not_swallowed(self):
        start = [0.] * 6
        for bad in ([0.] * 5, [0.] * 7, [0., 0., math.nan, 0., 0., 0.], [math.inf] * 6):
            with self.assertRaises(ValueError):
                validate_configuration_path(bad, start, lambda q: True)
        for kwargs in ({'arm_resolution_rad': 0.}, {'jaw_resolution_rad': math.nan},
                       {'arm_resolution_rad': math.inf}, {'max_samples': 0},
                       {'max_samples': True}, {'max_samples': 2.5}):
            with self.assertRaises(ValueError):
                validate_configuration_path(start, start, lambda q: True, **kwargs)
        with self.assertRaises(TypeError):
            validate_configuration_path(start, start, None)

        def broken(q):
            raise RuntimeError('independent checker failed')

        with self.assertRaisesRegex(RuntimeError, 'independent checker failed'):
            validate_configuration_path(start, start, broken)

    def test_callback_cannot_mutate_saved_endpoints_or_invalid_state(self):
        start, end = [0.] * 6, [.001] * 6

        def invalid(q):
            q[:] = [9.] * 6
            return False

        report = validate_configuration_path(start, end, invalid)
        self.assertEqual(report['invalid_state'], start)
        self.assertEqual(start, [0.] * 6)
        self.assertEqual(end, [.001] * 6)

    def test_tiny_resolution_is_bounded_before_callback(self):
        seen = []
        report = validate_configuration_path([0.] * 6, [1.] * 6,
                                            lambda q: seen.append(q) or True,
                                            jaw_resolution_rad=math.ulp(0.))
        self.assertEqual(report['reason'], 'sample_budget_exceeded')
        self.assertEqual(report['checked_states'], 0)
        self.assertEqual(seen, [])
        json.dumps(report, allow_nan=False)


class ConfigurationSweepInvocationTests(unittest.TestCase):
    def binding(self, *, jaw=.015, context=(), **changes):
        values = {'owner': object(), 'checker': object(), 'model': object(),
                  'stage': 'close', 'jaw_intent_rad': jaw, 'context': context}
        values.update(changes)
        return SweepBinding(**values)

    def invocation(self, binding=None, **kwargs):
        binding = self.binding() if binding is None else binding
        return ConfigurationSweepInvocation([0.] * 5 + [.5], [0.] * 5 + [.015],
                                            binding=binding, **kwargs)

    def test_binding_is_frozen_and_ownership_uses_identity(self):
        class EqualMarker:
            def __eq__(self, other):
                return True

        binding = self.binding(owner=EqualMarker(), checker=EqualMarker(), model=EqualMarker())
        self.assertTrue(binding.matches(replace(binding)))
        for field in ('owner', 'checker', 'model'):
            with self.subTest(field=field):
                self.assertFalse(binding.matches(replace(binding, **{field: EqualMarker()})))
        self.assertFalse(binding.matches(object()))
        with self.assertRaises(FrozenInstanceError):
            binding.stage = 'release'

    def test_context_is_owned_and_float_identity_preserves_signed_zero(self):
        nested = [1, [0., 'hypothesis', b'geometry', True, None]]
        binding = self.binding(context=('snapshot', nested))
        equivalent = replace(binding, context=('snapshot', [1, [0., 'hypothesis', b'geometry', True, None]]))
        self.assertTrue(binding.matches(equivalent))
        nested[1][0] = -0.
        nested.append('changed')
        self.assertTrue(binding.matches(equivalent))
        self.assertFalse(binding.matches(replace(equivalent,
            context=('snapshot', [1, [-0., 'hypothesis', b'geometry', True, None]]))))
        zero_binding = self.binding(jaw=0.)
        self.assertFalse(zero_binding.matches(replace(zero_binding, jaw_intent_rad=-0.)))

    def test_binding_rejects_unsupported_scope_and_mutable_or_nonfinite_context(self):
        for scope in ('payload', 'continuous_motion', '', None):
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                self.binding(guard_scope=scope)
        for context in ([1], ({'unowned': 1},), (bytearray(b'a'),), (object(),)):
            with self.subTest(context=repr(context)), self.assertRaises(TypeError):
                self.binding(context=context)
        for context in ((math.inf,), ((math.nan,),), ([1, -math.inf],)):
            with self.subTest(context=context), self.assertRaises(ValueError):
                self.binding(context=context)
        for jaw in (math.inf, -math.inf, math.nan):
            with self.subTest(jaw=jaw), self.assertRaises(ValueError):
                self.binding(jaw=jaw)

    def test_owned_request_and_callback_lists_do_not_change_the_244_samples(self):
        import numpy as np

        start = np.asarray([0.] * 5 + [.5])
        end = [0.] * 5 + [.015]
        original_start, original_end = start.tolist(), end.copy()
        binding = self.binding()
        invocation = ConfigurationSweepInvocation(start, end, binding=binding)
        start[:] = -7.
        end[:] = [9.] * 6
        self.assertEqual(invocation.request.startq6, tuple(original_start))
        self.assertEqual(invocation.request.endq6, tuple(original_end))
        with self.assertRaises(FrozenInstanceError):
            invocation.request.endq6 = tuple(end)
        with self.assertRaises(TypeError):
            invocation.request.startq6[0] = 1.
        observed, expected = [], []

        def valid(q):
            observed.append(q.copy())
            q[:] = [42.] * 6
            return True

        self.assertIsNone(invocation.execute(valid))
        report = invocation.consume(binding)
        oracle = validate_configuration_path(original_start, original_end,
                                             lambda q: expected.append(q) or True)
        self.assertEqual(report, oracle)
        self.assertEqual(len(observed), 244)
        self.assertEqual(np.asarray(observed).tobytes(), np.asarray(expected).tobytes())
        json.dumps(report, allow_nan=False)

    def test_execute_and_consume_are_one_shot_without_rechecking(self):
        binding, seen = self.binding(), []
        invocation = self.invocation(binding)
        self.assertIsNone(invocation.execute(lambda q: seen.append(q) or True))
        self.assertEqual(invocation.state, 'completed')
        report = invocation.consume(replace(binding))
        self.assertTrue(report['valid'])
        self.assertEqual(invocation.state, 'consumed')
        for operation in (lambda: invocation.consume(binding),
                          lambda: invocation.execute(lambda q: seen.append(q) or True)):
            with self.assertRaises(RuntimeError):
                operation()
        self.assertEqual(len(seen), 244)
        fresh = self.invocation(binding)
        with self.assertRaises(RuntimeError):
            fresh.consume(binding)
        fresh.execute(lambda q: True)
        with self.assertRaises(RuntimeError):
            fresh.execute(lambda q: self.fail('Repeated execution invoked its callback'))

    def test_wrong_consumer_fails_permanently_for_each_binding_field(self):
        binding = self.binding(context=('payload', .002, ('target', b'original')))
        variants = [('owner', replace(binding, owner=object())),
                    ('checker', replace(binding, checker=object())),
                    ('model', replace(binding, model=object())),
                    ('stage', replace(binding, stage='release')),
                    ('jaw', replace(binding, jaw_intent_rad=.5)),
                    ('context', replace(binding, context=('payload', .003, ('target', b'original')))),
                    ('type', None)]
        for field, consumer in variants:
            with self.subTest(field=field):
                invocation, seen = self.invocation(binding), []
                invocation.execute(lambda q: seen.append(q) or True)
                with self.assertRaises(RuntimeError):
                    invocation.consume(consumer)
                self.assertEqual(invocation.state, 'failed')
                with self.assertRaises(RuntimeError):
                    invocation.consume(binding)
                with self.assertRaises(RuntimeError):
                    invocation.execute(lambda q: seen.append(q) or True)
                self.assertEqual(len(seen), 244)

    def test_callback_exception_propagates_the_same_object_and_cannot_retry(self):
        class CheckerFailure(RuntimeError):
            pass

        binding, seen = self.binding(), []
        invocation = self.invocation(binding)
        failure = CheckerFailure('specific checker failure')

        def broken(q):
            seen.append(q)
            raise failure

        with self.assertRaises(CheckerFailure) as caught:
            invocation.execute(broken)
        self.assertIs(caught.exception, failure)
        self.assertEqual(invocation.state, 'failed')
        with self.assertRaises(RuntimeError):
            invocation.execute(lambda q: seen.append(q) or True)
        with self.assertRaises(RuntimeError):
            invocation.consume(binding)
        self.assertEqual(len(seen), 1)
        invalid_callback = self.invocation(binding)
        with self.assertRaises(TypeError):
            invalid_callback.execute(None)
        self.assertEqual(invalid_callback.state, 'failed')

    def test_first_middle_and_last_failure_keep_the_original_callback_prefix(self):
        for rejected_index in (0, 121, 243):
            with self.subTest(rejected_index=rejected_index):
                binding, seen = self.binding(), []
                invocation = self.invocation(binding)

                def valid(q):
                    seen.append(q.copy())
                    q[:] = [99.] * 6
                    return len(seen)-1 != rejected_index

                invocation.execute(valid)
                report = invocation.consume(binding)
                self.assertFalse(report['valid'])
                self.assertEqual(report['reason'], 'invalid_state')
                self.assertEqual(report['invalid_sample_index'], rejected_index)
                self.assertEqual(report['checked_states'], rejected_index+1)
                self.assertEqual(len(seen), rejected_index+1)
                self.assertEqual(report['invalid_state'], seen[-1])
                self.assertEqual(report['required_states'], 244)

    def test_sample_budget_report_consumes_once_with_zero_callbacks(self):
        binding = self.binding()
        invocation = self.invocation(binding, max_samples=243)
        invocation.execute(lambda q: self.fail('Budget rejection invoked geometry'))
        report = invocation.consume(binding)
        self.assertFalse(report['valid'])
        self.assertEqual(report['reason'], 'sample_budget_exceeded')
        self.assertEqual(report['checked_states'], 0)
        self.assertEqual(report['required_states'], 244)
        with self.assertRaises(RuntimeError):
            invocation.consume(binding)

    def test_signed_zero_request_endpoints_and_jaw_binding_are_bit_exact(self):
        start, end = [-0., 0., -0., 0., -0., .002], [0., -0., 0., -0., 0., -0.]
        binding = self.binding(jaw=-0., context=('frame', -0.))
        invocation = ConfigurationSweepInvocation(start, end, binding=binding)
        seen = []
        invocation.execute(lambda q: seen.append(q) or True)
        self.assertTrue(invocation.consume(binding)['valid'])
        for actual, expected in ((invocation.request.startq6, start),
                                 (invocation.request.endq6, end), (seen[0], start), (seen[-1], end)):
            self.assertEqual(struct.pack('!6d', *actual), struct.pack('!6d', *expected))
        with self.assertRaises(ValueError):
            ConfigurationSweepInvocation(start, end, binding=replace(binding, jaw_intent_rad=0.))
        second = ConfigurationSweepInvocation(start, end, binding=binding)
        second.execute(lambda q: True)
        with self.assertRaises(RuntimeError):
            second.consume(replace(binding, context=('frame', 0.)))
        self.assertEqual(second.state, 'failed')

    def test_identical_requests_are_independent_invocations_not_a_result_cache(self):
        binding, seen = self.binding(), []
        first, second = self.invocation(binding), self.invocation(binding)
        first.execute(lambda q: seen.append(q) or True)
        first_report = first.consume(binding)
        second.execute(lambda q: seen.append(q) or True)
        second_report = second.consume(binding)
        self.assertEqual(len(seen), 488)
        self.assertEqual(first_report, second_report)
        self.assertIsNot(first_report, second_report)
        first_report['invalid_state'] = ['changed by caller']
        self.assertIsNone(second_report['invalid_state'])


if __name__ == '__main__':
    unittest.main()
