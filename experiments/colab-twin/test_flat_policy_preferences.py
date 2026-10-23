"""Preference values, fresh ownership and original complex-copy fallbacks."""
from dataclasses import asdict, dataclass, replace
import math
from pathlib import Path
import pickle
import unittest

import numpy as np

from configuration_sweep import _immutable_context, _immutable_float_first_context
from route_policy import RoutePolicy, load_route_policy


class SeedName(str):
    pass


class BrokenCopy:
    def __deepcopy__(self, memo):
        raise ValueError('original copy failure')


@dataclass(frozen=True)
class ExtendedPolicy(RoutePolicy):
    extra: object = None


class FlatPolicyPreferencesTests(unittest.TestCase):
    def test_values_field_order_and_float_bits_match_original(self):
        policies = [RoutePolicy(), load_route_policy()[0],
            RoutePolicy(transport_preference_m=.054),
            RoutePolicy(ik_seed='neutral', transport_candidates=3, separation_steps=1),
            RoutePolicy(ik_seed=SeedName('continuation')),
            RoutePolicy(transport_preference_m=np.float64(.054)),
            ExtendedPolicy(extra=b'bytes'), ExtendedPolicy(extra=-0.),
            ExtendedPolicy(extra=math.nan)]
        for policy in policies:
            selected = replace(policy, flat_policy_preferences=True)
            with self.subTest(policy=type(policy).__name__):
                self.assertEqual(pickle.dumps(selected.preferences()),
                                 pickle.dumps(asdict(selected)))
                self.assertEqual(list(selected.preferences()), list(asdict(selected)))

    def test_each_call_returns_a_new_independent_dictionary(self):
        policy = RoutePolicy(flat_policy_preferences=True)
        first, second = policy.preferences(), policy.preferences()
        first['separation_steps'] = 1
        self.assertIsNot(first, second)
        self.assertEqual(second['separation_steps'], 13)
        self.assertEqual(policy.separation_steps, 13)

    def test_nested_and_array_values_keep_original_deep_copy(self):
        for extra in ({'a': [1., -0.]}, np.array([[1., -0.], [2., 3.]]), (1., [2.])):
            policy = ExtendedPolicy(flat_policy_preferences=True, extra=extra)
            expected, actual = asdict(policy), policy.preferences()
            with self.subTest(extra=type(extra).__name__):
                self.assertEqual(pickle.dumps(actual), pickle.dumps(expected))
                self.assertIsNot(actual['extra'], extra)
                if isinstance(extra, dict):
                    actual['extra']['a'][0] = 99.
                    self.assertEqual(extra['a'][0], 1.)
                elif isinstance(extra, np.ndarray):
                    actual['extra'][0, 0] = 99.
                    self.assertEqual(extra[0, 0], 1.)
                else:
                    actual['extra'][1][0] = 99.
                    self.assertEqual(extra[1][0], 2.)

    def test_original_copy_failure_still_propagates(self):
        policy = ExtendedPolicy(flat_policy_preferences=True, extra=BrokenCopy())
        for function in (asdict, lambda value: value.preferences()):
            with self.assertRaisesRegex(ValueError, '^original copy failure$'):
                function(policy)

    def test_owned_context_keeps_policy_values_and_mutation_rejection(self):
        policy = RoutePolicy(flat_policy_preferences=True)
        self.assertEqual(_immutable_float_first_context(policy),
                         _immutable_context(tuple(asdict(policy).items())))
        changed = replace(policy, separation_steps=12)
        self.assertNotEqual(_immutable_float_first_context(policy),
                            _immutable_float_first_context(changed))

    def test_selected_source_changes_only_one_flag_and_default_stays_off(self):
        folder = Path(__file__).parent/'route_strategies'
        parent, _ = load_route_policy(folder/'float_first_context.py')
        candidate, _ = load_route_policy(folder/'flat_policy_preferences.py')
        self.assertFalse(RoutePolicy().flat_policy_preferences)
        self.assertFalse(load_route_policy()[0].flat_policy_preferences)
        self.assertEqual([key for key, value in parent.preferences().items()
                          if value != candidate.preferences()[key]], ['flat_policy_preferences'])
        for bad in (1, 0, None, 'true'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                RoutePolicy(flat_policy_preferences=bad)


if __name__ == '__main__':
    unittest.main()
