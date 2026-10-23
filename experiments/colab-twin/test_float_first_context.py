"""Owned context and guard equivalence across the float-first alternative."""
from dataclasses import replace
import math
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from configuration_sweep import (ConfigurationSweepInvocation, SweepBinding,
    _immutable_float_first_context, _immutable_snapshot_context)
from route_policy import RoutePolicy, load_route_policy
import test_single_pass_context as controller_fixtures


class FloatFirstContextTests(unittest.TestCase):
    def outcome(self, function, value):
        try:
            return ('value', function(value))
        except (TypeError, ValueError) as error:
            return ('error', type(error), str(error))

    def test_raw_values_and_original_errors_are_equal(self):
        values = [None, True, False, b'bits', 'text', 3, -7, 0., -0., 1.25,
            (1, [2., (False, None, 'x')]), (), [], np.float64(-0.),
            math.inf, -math.inf, math.nan, (1., [math.nan]), {}, set(),
            bytearray(b'x'), object(), np.array([1., -0.]), np.array(2.),
            np.array([[1., -0.], [2., 3.]]), np.array([math.nan]),
            {'b': [1., -0.], 'a': np.array([[2., 3.]])}, RoutePolicy(),
            {np.float64(-0.): 1.}, (1, [object()]), np.float32(1.),
            np.array([np.float32(1.)]), {'a': object()},
            (RoutePolicy(), np.array([1., 2.]))]
        for value in values:
            with self.subTest(value=type(value).__name__):
                self.assertEqual(self.outcome(_immutable_snapshot_context, value),
                                 self.outcome(_immutable_float_first_context, value))

    def test_encoding_owns_mutable_inputs_and_distinguishes_signed_zero(self):
        raw = {'arr': np.array([[1., -0.]]), 'list': [[2.]]}
        encoded = _immutable_float_first_context(raw)
        original = _immutable_snapshot_context(raw)
        raw['arr'][:] = 99.
        raw['list'][0][0] = 77.
        self.assertEqual(encoded, original)
        self.assertNotEqual(_immutable_float_first_context(-0.),
                            _immutable_float_first_context(0.))
        self.assertEqual(_immutable_float_first_context(encoded),
                         _immutable_snapshot_context(original))

    def test_current_controller_fields_keep_original_ownership(self):
        fixture = controller_fixtures.SinglePassContextTests()
        for purpose in ('planned_closure', 'measured_closure', 'online_chord'):
            c = fixture.controller()
            c.route_policy = RoutePolicy(fused_context_freeze=True)
            start, end = [0.]*5+[.5], [0.]*5+[.015]
            parent = c._sweep_binding(start, end, purpose)
            c.route_policy = replace(c.route_policy, float_first_context=True)
            candidate = c._sweep_binding(start, end, purpose)
            with self.subTest(purpose=purpose):
                self.assertEqual(fixture.without_policy(parent),
                                 fixture.without_policy(candidate))
                self.assertEqual(parent._jaw_bits, candidate._jaw_bits)
                owned = candidate.context
                c.target_xy[0] += .01
                c.released_query.rotation[0, 0] += .001
                self.assertEqual(candidate.context, owned)
                self.assertFalse(candidate.matches(c._sweep_binding(start, end, purpose)))

    def test_mutation_invalidates_a_previous_request(self):
        owner, checker, model = object(), object(), object()
        raw = np.array([1., -0.])
        def binding():
            return SweepBinding(owner, checker, model, 'close', .015, (raw,),
                                snapshot_context=True, float_first_context=True)
        invocation = ConfigurationSweepInvocation([0.]*5+[.5], [0.]*5+[.015],
                                                  binding=binding())
        invocation.execute(lambda q: True)
        raw[0] = 2.
        with self.assertRaisesRegex(RuntimeError, 'ownership or context changed'):
            invocation.consume(binding())
        self.assertEqual(invocation.state, 'failed')

    def test_constructor_rejections_keep_original_errors(self):
        common = dict(owner=object(), checker=object(), model=object(), stage='close',
                      jaw_intent_rad=.015, context=())
        for changes in ({'owner': None}, {'checker': None}, {'model': None},
                        {'stage': ''}, {'jaw_intent_rad': math.nan},
                        {'guard_scope': 'other'}, {'context': []}):
            errors = []
            for enabled in (False, True):
                try:
                    SweepBinding(**dict(common, **changes), snapshot_context=True,
                                 float_first_context=enabled)
                except (ValueError, TypeError) as error:
                    errors.append((type(error), str(error)))
            with self.subTest(changes=changes):
                self.assertEqual(len(errors), 2)
                self.assertEqual(errors[0], errors[1])

    def test_non_snapshot_paths_never_select_the_new_helper(self):
        common = dict(owner=object(), checker=object(), model=object(), stage='close',
                      jaw_intent_rad=.015, context=(1., -0., 'async'))
        for mapped in (False, True):
            parent = SweepBinding(**common, map_context=mapped)
            with patch('configuration_sweep._immutable_float_first_context',
                       side_effect=AssertionError('unexpected float-first call')):
                candidate = SweepBinding(**common, map_context=mapped,
                                         float_first_context=True)
            self.assertTrue(parent.matches(candidate))

    def test_candidate_is_one_flag_and_low_level_default_remains_off(self):
        folder = Path(__file__).parent/'route_strategies'
        parent, _ = load_route_policy(folder/'compact_status_json.py')
        candidate, _ = load_route_policy(folder/'float_first_context.py')
        default, _ = load_route_policy()
        self.assertFalse(RoutePolicy().float_first_context)
        self.assertTrue(default.float_first_context)
        self.assertEqual([key for key, value in parent.preferences().items()
                          if value != candidate.preferences()[key]], ['float_first_context'])
        for bad in (1, 0, None, 'true'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                RoutePolicy(float_first_context=bad)


if __name__ == '__main__':
    unittest.main()
