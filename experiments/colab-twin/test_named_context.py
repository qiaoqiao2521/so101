"""Named context retains original bits, failures and request ownership."""
from dataclasses import replace
import math
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from configuration_sweep import (ConfigurationSweepInvocation, SweepBinding,
    _immutable_float_first_context, _immutable_named_context)
from route_policy import RoutePolicy, load_route_policy
import test_single_pass_context as controller_fixtures


class NamedContextTests(unittest.TestCase):
    def outcome(self, function, value):
        try:
            return ('value', function(value))
        except (TypeError, ValueError) as error:
            return ('error', type(error), str(error))

    def test_original_encoding_and_errors_match_for_named_and_fallback_inputs(self):
        values = [None, True, False, b'bits', 'text', 3, -7, 0., -0., 1.25,
            (1, [2., (False, None, 'x')]), (), [], np.float64(-0.), math.inf,
            -math.inf, math.nan, (1., [math.nan]), {}, set(), bytearray(b'x'),
            object(), np.array([1., -0.]), np.array(2.),
            np.array([[1., -0.], [2., 3.]]), np.array([math.nan]),
            {'b': [1., -0.], 'a': np.array([[2., 3.]])}, RoutePolicy(),
            {np.float64(-0.): 1.}, (1, [object()]), np.float32(1.),
            np.array([np.float32(1.)]), {'a': object()},
            (RoutePolicy(), np.array([1., 2.])), (('x', 1.), ('y', -0.)),
            (('x', math.nan),), (('x', object()),), (('x', 1.), ('bad',)),
            (('x', 1.), [1, 2]), (('x', np.array([1., -0.])),),
            ((1, 2.),), (('x',),), (('x', 1.), ('x', 2.)), (('', 1.),)]
        for value in values:
            with self.subTest(value=type(value).__name__):
                self.assertEqual(self.outcome(_immutable_float_first_context, value),
                                 self.outcome(_immutable_named_context, value))

    def test_named_values_remain_owned_and_signed_zero_remains_distinct(self):
        raw = (('arr', np.array([[1., -0.]])), ('list', [[2.]]))
        expected = _immutable_float_first_context(raw)
        result = _immutable_named_context(raw)
        raw[0][1][:] = 99.
        raw[1][1][0][0] = 77.
        self.assertEqual(result, expected)
        self.assertNotEqual(_immutable_named_context((('x', -0.),)),
                            _immutable_named_context((('x', 0.),)))

    def test_actual_controller_fields_keep_current_ownership(self):
        fixture = controller_fixtures.SinglePassContextTests()
        for purpose in ('planned_closure', 'measured_closure', 'online_chord'):
            c = fixture.controller()
            c.route_policy = RoutePolicy(fused_context_freeze=True, float_first_context=True)
            start, end = [0.]*5+[.5], [0.]*5+[.015]
            parent = c._sweep_binding(start, end, purpose)
            c.route_policy = replace(c.route_policy, named_context_freeze=True)
            candidate = c._sweep_binding(start, end, purpose)
            with self.subTest(purpose=purpose):
                self.assertEqual(fixture.without_policy(parent),
                                 fixture.without_policy(candidate))
                self.assertEqual(parent._jaw_bits, candidate._jaw_bits)
                stored = candidate.context
                c.target_xy[0] += .01
                c.released_query.rotation[0, 0] += .001
                self.assertEqual(candidate.context, stored)
                self.assertFalse(candidate.matches(c._sweep_binding(start, end, purpose)))

    def test_mutation_still_rejects_consuming_a_previous_request(self):
        owner, checker, model = object(), object(), object()
        raw = np.array([1., -0.])
        def binding():
            return SweepBinding(owner, checker, model, 'close', .015, (('arr', raw),),
                                snapshot_context=True, float_first_context=True,
                                named_context_freeze=True)
        invocation = ConfigurationSweepInvocation([0.]*5+[.5], [0.]*5+[.015],
                                                  binding=binding())
        invocation.execute(lambda q: True)
        raw[0] = 2.
        with self.assertRaisesRegex(RuntimeError, 'ownership or context changed'):
            invocation.consume(binding())
        self.assertEqual(invocation.state, 'failed')

    def test_constructor_original_rejections_keep_their_errors(self):
        common = dict(owner=object(), checker=object(), model=object(), stage='close',
                      jaw_intent_rad=.015, context=())
        for changes in ({'owner': None}, {'checker': None}, {'model': None},
                        {'stage': ''}, {'jaw_intent_rad': math.nan},
                        {'guard_scope': 'other'}, {'context': []}):
            errors = []
            for enabled in (False, True):
                try:
                    SweepBinding(**dict(common, **changes), snapshot_context=True,
                                 float_first_context=True, named_context_freeze=enabled)
                except (ValueError, TypeError) as error:
                    errors.append((type(error), str(error)))
            with self.subTest(changes=changes):
                self.assertEqual(len(errors), 2)
                self.assertEqual(errors[0], errors[1])

    def test_non_snapshot_paths_keep_the_original_helpers(self):
        common = dict(owner=object(), checker=object(), model=object(), stage='close',
                      jaw_intent_rad=.015, context=(1., -0., 'async'))
        for mapped in (False, True):
            parent = SweepBinding(**common, map_context=mapped)
            with patch('configuration_sweep._immutable_named_context',
                       side_effect=AssertionError('unexpected named-context call')):
                candidate = SweepBinding(**common, map_context=mapped, named_context_freeze=True)
            self.assertTrue(parent.matches(candidate))

    def test_one_preference_delta_and_current_default_off(self):
        folder = Path(__file__).parent/'route_strategies'
        parent, _ = load_route_policy(folder/'float_first_context.py')
        candidate, _ = load_route_policy(folder/'named_context.py')
        self.assertFalse(RoutePolicy().named_context_freeze)
        self.assertFalse(load_route_policy()[0].named_context_freeze)
        self.assertFalse(candidate.flat_policy_preferences)
        self.assertEqual([key for key, value in parent.preferences().items()
                          if value != candidate.preferences()[key]], ['named_context_freeze'])
        for bad in (1, 0, None, 'true'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                RoutePolicy(named_context_freeze=bad)


if __name__ == '__main__':
    unittest.main()
