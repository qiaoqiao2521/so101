"""Sampling-contract tests without a model, IK, or physics."""

import json
import math
import unittest

from configuration_sweep import validate_configuration_path


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


if __name__ == '__main__':
    unittest.main()
