"""Paired local screens cannot replace physical acceptance."""
import unittest

from factory_minimum_suite import ScreenLimits, screen


class MinimumSuiteTests(unittest.TestCase):
    def measurement(self, value, equivalent=True, verdict='pass', source='report'):
        return {'measurement_s': value, 'output_equivalent': equivalent,
                'verdict': verdict, 'source': source}

    def test_consistent_byte_equal_gain_is_only_eligible_for_physical_ab(self):
        result = screen([self.measurement(1.), self.measurement(1.), self.measurement(1.)],
                        [self.measurement(.9), self.measurement(.8), self.measurement(.9)])
        self.assertEqual(result['decision'], 'eligible_for_physical_ab')
        self.assertIn('not a task pass', result['scope'])

    def test_original_failure_or_different_outputs_never_become_fast_success(self):
        failed = screen([self.measurement(1.), self.measurement(1.), self.measurement(1.)],
                        [self.measurement(.1, verdict='fail'),
                         self.measurement(.1), self.measurement(.1)])
        self.assertEqual((failed['decision'], failed['reason']),
                         ('reject', 'original_or_candidate_pair_not_passed'))
        changed = screen([self.measurement(1.), self.measurement(1.), self.measurement(1.)],
                         [self.measurement(.1, False), self.measurement(.1, False),
                          self.measurement(.1, False)])
        self.assertEqual((changed['decision'], changed['reason']),
                         ('reject', 'outputs_are_not_byte_equivalent'))

    def test_only_explicit_pass_verdicts_are_eligible(self):
        for verdict in (None, 'unknown', 'unscored'):
            with self.subTest(verdict=verdict):
                baseline = self.measurement(1.)
                candidate = self.measurement(.1)
                if verdict is None:
                    candidate.pop('verdict')
                else:
                    candidate['verdict'] = verdict
                result = screen([baseline]*3, [candidate]*3)
                self.assertEqual((result['decision'], result['reason']),
                                 ('reject', 'original_or_candidate_pair_not_passed'))

    def test_thresholds_and_sample_count_are_explicit(self):
        with self.assertRaises(ValueError):
            screen([self.measurement(1.)], [self.measurement(.9)])
        result = screen([self.measurement(1.)]*3, [self.measurement(.999)]*3,
                        limits=ScreenLimits(min_samples=3, max_median_effect_s=.002))
        self.assertEqual(result['reason'], 'median_local_effect_below_threshold')
        with self.assertRaises(ValueError):
            ScreenLimits(min_samples=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
