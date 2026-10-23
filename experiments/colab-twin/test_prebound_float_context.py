"""Check numeric tokens, mutation rejection and the optional snapshot path."""
from dataclasses import replace
import math
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from configuration_sweep import (ConfigurationSweepInvocation, SweepBinding,
    _immutable_float_first_context, _immutable_prebound_float_context)
from route_policy import RoutePolicy, load_route_policy
import test_single_pass_context as fixtures


class PreboundFloatContextTests(unittest.TestCase):
    def outcome(self, function, value):
        try:
            return ('value', function(value))
        except (TypeError, ValueError) as error:
            return ('error', type(error), str(error))

    def test_original_bits_and_errors_remain_identical(self):
        values = [None, True, b'x', 'x', 3, 0., -0., 1e-300, 1e300,
            (1., [2., -0.]), np.eye(3), np.arange(24.).reshape(4, 6)[::2, ::-2],
            np.empty((0, 3)), np.empty((3, 0)), np.array(1.),
            np.array([1., -0.], dtype='>f8'), np.array([1., -0.], dtype=object),
            np.arange(3, dtype=np.float32), np.arange(3, dtype=np.int64),
            np.float32(1.), {'a': np.eye(3)}, RoutePolicy(), object(),
            math.inf, -math.inf, math.nan, np.array([math.nan]), {math.inf: 1.}]
        for value in values:
            with self.subTest(kind=type(value).__name__):
                self.assertEqual(self.outcome(_immutable_float_first_context, value),
                                 self.outcome(_immutable_prebound_float_context, value))
        self.assertNotEqual(_immutable_prebound_float_context(-0.),
                            _immutable_prebound_float_context(0.))

    def test_owned_snapshot_still_rejects_a_mutated_request(self):
        owner, checker, model = object(), object(), object()
        raw = np.array([1., -0.])
        def binding():
            return SweepBinding(owner, checker, model, 'close', .015, (('arr', raw),),
                snapshot_context=True, float_first_context=True, prebound_float_pack=True)
        first = binding()
        invocation = ConfigurationSweepInvocation([0.]*5+[.5], [0.]*5+[.015], binding=first)
        invocation.execute(lambda q: True)
        stored = first.context
        raw[0] = 2.
        self.assertEqual(first.context, stored)
        with self.assertRaisesRegex(RuntimeError, 'ownership or context changed'):
            invocation.consume(binding())
        self.assertEqual(invocation.state, 'failed')

    def test_actual_controller_passes_the_selected_option(self):
        fixture = fixtures.SinglePassContextTests()
        for purpose in ('planned_closure', 'measured_closure', 'online_chord'):
            c = fixture.controller()
            c.route_policy = RoutePolicy(fused_context_freeze=True, float_first_context=True)
            start, end = [0.]*5+[.5], [0.]*5+[.015]
            parent = c._sweep_binding(start, end, purpose)
            c.route_policy = replace(c.route_policy, prebound_float_pack=True)
            candidate = c._sweep_binding(start, end, purpose)
            with self.subTest(purpose=purpose):
                self.assertTrue(candidate.prebound_float_pack)
                self.assertEqual(fixture.without_policy(parent), fixture.without_policy(candidate))
                self.assertEqual(parent._jaw_bits, candidate._jaw_bits)

    def test_other_paths_keep_the_original_encoders(self):
        common = dict(owner=object(), checker=object(), model=object(), stage='close',
                      jaw_intent_rad=.015, context=(('x', (1., -0.)),))
        for options in ({}, {'map_context': True}, {'snapshot_context': True},
                        {'snapshot_context': True, 'float_first_context': True,
                         'named_context_freeze': True}):
            parent = SweepBinding(**common, **options)
            with patch('configuration_sweep._immutable_prebound_float_context',
                       side_effect=AssertionError('unexpected prebound path')):
                candidate = SweepBinding(**common, **options, prebound_float_pack=True)
            self.assertTrue(parent.matches(candidate))

    def test_explicit_candidate_is_one_flag_and_defaults_stay_off(self):
        folder = Path(__file__).parent/'route_strategies'
        parent, _ = load_route_policy(folder/'float_first_context.py')
        candidate, _ = load_route_policy(folder/'prebound_float_pack.py')
        self.assertFalse(RoutePolicy().prebound_float_pack)
        self.assertFalse(load_route_policy()[0].prebound_float_pack)
        self.assertEqual([key for key, value in parent.preferences().items()
                          if value != candidate.preferences()[key]], ['prebound_float_pack'])
        for bad in (1, 0, None, 'true'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                RoutePolicy(prebound_float_pack=bad)


if __name__ == '__main__':
    unittest.main()
