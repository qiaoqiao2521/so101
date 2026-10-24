"""Caller directions must obtain original full-vertex interval certificates."""
import ctypes
from itertools import product
import unittest

import numpy as np

from support_native import NativeSupport


def box(half):
    return np.asarray(list(product((-1., 1.), repeat=3)))*np.asarray(half)


class ExtraDirectionTests(unittest.TestCase):
    def setUp(self):
        angle = np.pi/4
        c, s = np.cos(angle), np.sin(angle)
        rotation = np.array([[c, -s, 0.], [s, c, 0.], [0., 0., 1.]])
        # The complete mesh is a thin rotated bar inside its original frame.
        # Its actual face normal is absent from the fixed frame-axis list.
        self.mesh = box([.1, .001, .01])@rotation.T
        self.box = box([.005, .005, .005])
        self.tangent = np.array([c, s, 0.])
        self.normal = np.array([-s, c, 0.])
        self.positions = np.vstack((np.zeros(3), .06*self.tangent+.0095*self.normal))
        self.rotations = np.repeat(np.eye(3)[None], 2, axis=0)
        self.native = NativeSupport([self.mesh, self.box], ['mesh', 'box'])
        self.addCleanup(self.native.close)
        self.pair = np.array([0, 1], dtype=np.int64)

    def certify(self, directions=None, margin=.001, positions=None, rotations=None):
        return self.native.certify_directions(
            self.positions if positions is None else positions,
            self.rotations if rotations is None else rotations,
            self.pair, [self.normal] if directions is None else directions, margin)

    def test_rotated_slender_mesh_can_be_certified_beyond_fixed19_axes(self):
        baseline = self.native.evaluate(self.positions, self.rotations, [self.pair], .001)
        self.assertFalse(baseline['certified'][0])
        self.assertEqual(baseline['reason'][0], 'no_separation_certificate')
        result = self.certify([[1., 0., 0.], self.normal, self.tangent])
        self.assertTrue(result['certified'][0])
        self.assertEqual(result['support_mode'][0], 'full')
        self.assertEqual(result['direction_index'][0], 1)
        self.assertEqual(result['evaluations'][0], 2)
        self.assertEqual(result['reason'][0], 'separation_certified')
        self.assertGreater(result['lower_bound_m'][0], .001)
        self.assertGreaterEqual(result['squared_gap_lower'][0],
                                result['squared_threshold_upper'][0])

    def test_intersection_and_positive_but_insufficient_gap_are_rejected(self):
        for offset in (.006, .0085):
            with self.subTest(offset=offset):
                positions = np.vstack((np.zeros(3), .06*self.tangent+offset*self.normal))
                result = self.certify(positions=positions)
                self.assertFalse(result['certified'][0])
                self.assertEqual(result['reason'][0], 'no_separation_certificate')
                self.assertLess(result['lower_bound_m'][0], .001)

    def test_empty_and_invalid_directions_never_obtain_a_certificate(self):
        empty = self.certify([])
        self.assertFalse(empty['certified'][0])
        self.assertEqual(empty['evaluations'][0], 0)
        self.assertEqual(empty['reason'][0], 'no_separation_certificate')
        for directions in ([[0., 0., 0.]], [[np.nan, 0., 0.]],
                           [self.normal, [0., np.inf, 0.]]):
            with self.subTest(directions=directions):
                result = self.certify(directions)
                self.assertFalse(result['certified'][0])
                self.assertEqual(result['reason'][0], 'nonfinite_or_unsupported_arithmetic')

    def test_invalid_margin_and_frame_use_original_rejection_reasons(self):
        for margin in (0., -.001, np.nan, np.inf):
            with self.subTest(margin=margin):
                result = self.certify(margin=margin)
                self.assertFalse(result['certified'][0])
                self.assertEqual(result['reason'][0], 'invalid_margin')
        positions = self.positions.copy()
        positions[0, 0] = np.nan
        result = self.certify(positions=positions)
        self.assertFalse(result['certified'][0])
        self.assertEqual(result['reason'][0], 'nonfinite_or_unsupported_arithmetic')

    def test_nondefault_rounding_cannot_obtain_a_certificate(self):
        libm = ctypes.CDLL('libm.so.6')
        original = libm.fegetround()
        try:
            self.assertEqual(libm.fesetround(0x400), 0)  # Linux FE_DOWNWARD.
            result = self.certify()
        finally:
            libm.fesetround(original)
        self.assertFalse(result['certified'][0])
        self.assertEqual(result['reason'][0], 'invalid_arithmetic_environment')

    def test_input_errors_and_closed_handle_keep_existing_python_conventions(self):
        with self.assertRaises(ValueError):
            self.certify([1., 0., 0.])
        with self.assertRaises(ValueError):
            self.native.certify_directions(self.positions, self.rotations, [0., 1.],
                                           [self.normal], .001)
        with self.assertRaises(ValueError):
            self.native.certify_directions(self.positions, self.rotations, [0, 2],
                                           [self.normal], .001)
        self.native.close()
        with self.assertRaisesRegex(RuntimeError, 'closed'):
            self.certify()

    def test_optional_call_keeps_original_evaluate_and_owned_inputs_unchanged(self):
        pairs = np.array([[0, 1], [1, 0]], dtype=np.int64)
        before = self.native.evaluate(self.positions, self.rotations, pairs, .001)
        p, R, pair = self.positions.copy(), self.rotations.copy(), self.pair.copy()
        directions = np.array([self.normal])
        result = self.native.certify_directions(p, R, pair, directions, .001)
        np.testing.assert_array_equal(p, self.positions)
        np.testing.assert_array_equal(R, self.rotations)
        np.testing.assert_array_equal(pair, self.pair)
        np.testing.assert_array_equal(directions, [self.normal])
        result['n'][0, 0] = 123.
        after = self.native.evaluate(self.positions, self.rotations, pairs, .001)
        for key in before:
            np.testing.assert_array_equal(before[key], after[key], err_msg=key)
        self.assertTrue(self.certify()['certified'][0])


if __name__ == '__main__':
    unittest.main()
