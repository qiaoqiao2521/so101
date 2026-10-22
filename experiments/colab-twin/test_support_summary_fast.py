"""Failure selection and output semantics of the optional Python fast path."""
import struct
import unittest
from types import SimpleNamespace

import numpy as np

from test_support_native import fresh_module


class SummaryFastTests(unittest.TestCase):
    def setUp(self):
        self.module = fresh_module()
        self.module.configure_summary_fast(True)

    def inputs(self, count=3):
        pairs = np.zeros((count, 2), dtype=np.int64)
        bound = self.module._BoundPairs(SimpleNamespace(geometry_count=2), pairs)
        numeric = np.zeros((count, 12))
        numeric[:, 11] = np.arange(count, 0, -1) / 100
        flags = np.ones((count, 6), dtype=np.int64)
        flags[:, 4] = 0
        return bound, numeric, flags

    def test_selection_is_per_binding_and_original_method_stays_available(self):
        bound, _, _ = self.inputs()
        self.assertEqual(bound._summarize.__func__, self.module._BoundPairs._summarize_all_valid)
        module = fresh_module()
        old = module._BoundPairs(SimpleNamespace(geometry_count=2), np.zeros((3, 2), dtype=np.int64))
        self.assertNotIn('_summarize', old.__dict__)
        self.assertEqual(old._summarize.__func__, module._BoundPairs._summarize)

    def test_all_nonzero_flags_are_certified_and_nearest_is_the_argmin(self):
        bound, numeric, flags = self.inputs()
        flags[:, 0] = [-1, 2, np.iinfo(np.int64).min]
        result = bound._summarize(numeric, flags)
        self.assertEqual(result, {'valid': True, 'nearest_index': 2, 'lower_bound_m': .01,
            'certificate_reason': str(self.module._REASONS[0]),
            'certified_pairs': 3, 'checked_pairs': 3})

    def test_first_failed_pair_takes_precedence_over_the_smallest_bound(self):
        bound, numeric, flags = self.inputs()
        flags[[0, 2], 0] = 0
        flags[0, 4] = 4
        result = bound._summarize(numeric, flags)
        self.assertFalse(result['valid'])
        self.assertEqual(result['nearest_index'], 0)
        self.assertEqual(result['certified_pairs'], 1)
        self.assertEqual(result['lower_bound_m'], .03)
        self.assertEqual(result['certificate_reason'], str(self.module._REASONS[4]))

    def test_all_failed_keeps_the_first_failure(self):
        bound, numeric, flags = self.inputs()
        flags[:, 0] = 0
        result = bound._summarize(numeric, flags)
        self.assertEqual((result['valid'], result['nearest_index'], result['certified_pairs']),
                         (False, 0, 0))

    def test_ties_keep_the_first_signed_zero(self):
        bound, numeric, flags = self.inputs()
        numeric[:, 11] = [0., -0., 0.]
        result = bound._summarize(numeric, flags)
        self.assertEqual(result['nearest_index'], 0)
        self.assertEqual(struct.pack('=d', result['lower_bound_m']), struct.pack('=d', 0.))

    def test_nonfinite_values_keep_original_argmin_semantics(self):
        bound, numeric, flags = self.inputs()
        numeric[:, 11] = [np.inf, np.nan, -np.inf]
        result = bound._summarize(numeric, flags)
        self.assertEqual(result['nearest_index'], 1)
        self.assertTrue(np.isnan(result['lower_bound_m']))

    def test_empty_input_keeps_the_original_exception(self):
        bound, numeric, flags = self.inputs(0)
        with self.assertRaisesRegex(ValueError, 'argmin'):
            bound._summarize(numeric, flags)


if __name__ == '__main__':
    unittest.main()
