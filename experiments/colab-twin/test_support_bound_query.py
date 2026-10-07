"""Owned pair policies and summary regressions with real finite geometry.

These tests perform static queries only. They do not certify continuous
motion, physical tracking, or the complete control-cycle deadline.
"""
import ctypes
import ctypes.util
import itertools
import platform
import sys
import unittest
from unittest.mock import patch

import mujoco
import numpy as np

from conservative_collision import ConservativeCollisionChecker
from configuration_sweep import validate_configuration_path
from support_native import NativeSupport
from test_conservative_collision import rig_xml


DETAIL_FIELDS = (
    'certified', 'support_mode', 'direction_index', 'evaluations', 'reason',
    'orientation', 'n', 'projection_a', 'projection_b', 'gap_lower',
    'norm_squared_upper', 'squared_gap_lower', 'squared_threshold_upper',
    'lower_bound_m',
)


class BoundPairQueryTests(unittest.TestCase):
    def fixture(self):
        corners = np.asarray(list(itertools.product((-1., 1.), repeat=3)))
        points = [corners * half for half in ((.01, .012, .008),
                                             (.009, .007, .011),
                                             (.006, .01, .009))]
        native = NativeSupport(points, ['box'] * len(points))
        self.addCleanup(native.close)
        positions = np.asarray([[0., 0., 0.], [.05, .003, 0.], [.11, -.004, .002]])
        rotations = np.tile(np.eye(3), (3, 1, 1))
        angle = .37
        rotations[1] = [[np.cos(angle), -np.sin(angle), 0.],
                        [np.sin(angle), np.cos(angle), 0.], [0., 0., 1.]]
        angle = -.21
        rotations[2] = [[np.cos(angle), 0., np.sin(angle)], [0., 1., 0.],
                        [-np.sin(angle), 0., np.cos(angle)]]
        pairs = np.asarray([[0, 1], [1, 2], [2, 0]], dtype=np.int64)
        return native, positions, rotations, pairs

    def assert_details_identical(self, first, second):
        self.assertEqual(set(first), set(DETAIL_FIELDS))
        self.assertEqual(set(second), set(DETAIL_FIELDS))
        for field in DETAIL_FIELDS:
            with self.subTest(field=field):
                self.assertEqual(first[field].dtype, second[field].dtype)
                self.assertEqual(first[field].shape, second[field].shape)
                # Preserve signed zero, NaN payloads, and integer/string fields.
                self.assertEqual(first[field].tobytes(), second[field].tobytes())

    def assert_summary_matches(self, detail, summary):
        failures = np.flatnonzero(~detail['certified'])
        index = int(failures[0]) if len(failures) else int(np.argmin(detail['lower_bound_m']))
        self.assertEqual(summary['valid'], bool(detail['certified'].all()))
        self.assertEqual(summary['nearest_index'], index)
        self.assertEqual(summary['certified_pairs'], int(detail['certified'].sum()))
        self.assertEqual(summary['checked_pairs'], len(detail['certified']))
        self.assertEqual(summary['certificate_reason'], str(detail['reason'][index]))
        self.assertEqual(np.float64(summary['lower_bound_m']).tobytes(),
                         detail['lower_bound_m'][index].tobytes())

    def test_real_finite_boxes_preserve_all_fourteen_fields(self):
        native, positions, rotations, pairs = self.fixture()
        bound = native.bind_pairs(pairs)
        for shift in (0., .015, -.038):
            with self.subTest(shift=shift):
                frame = positions.copy()
                frame[1, 0] += shift
                direct = native.evaluate(frame, rotations, pairs, .001)
                detailed = bound.evaluate(frame, rotations, .001)
                self.assert_details_identical(direct, detailed)
                self.assert_summary_matches(direct, bound.summary(frame, rotations, .001))

    def test_clear_summary_uses_minimum_certificate_and_all_pairs(self):
        native, positions, rotations, pairs = self.fixture()
        bound = native.bind_pairs(pairs)
        detail = native.evaluate(positions, rotations, pairs, .001)
        self.assertTrue(detail['certified'].all())
        summary = bound.summary(positions, rotations, .001)
        self.assert_summary_matches(detail, summary)
        self.assertEqual(summary['checked_pairs'], 3)

    def test_reversed_and_duplicate_pairs_keep_order_and_first_failure(self):
        native, positions, rotations, _ = self.fixture()
        positions[1] = positions[0]
        # Clear pair, failing reversed pair, its duplicate, then another clear pair.
        pairs = np.asarray([[2, 0], [1, 0], [1, 0], [2, 1]], dtype=np.int64)
        bound = native.bind_pairs(pairs)
        detail = native.evaluate(positions, rotations, pairs, .001)
        self.assertEqual(detail['certified'].tolist(), [True, False, False, True])
        self.assert_details_identical(detail, bound.evaluate(positions, rotations, .001))
        summary = bound.summary(positions, rotations, .001)
        self.assert_summary_matches(detail, summary)
        self.assertEqual(summary['nearest_index'], 1)
        self.assertEqual(summary['checked_pairs'], 4)
        self.assertEqual(summary['certified_pairs'], 2)

    def test_binding_owns_noncontiguous_pair_input(self):
        native, positions, rotations, pairs = self.fixture()
        backing = np.zeros((len(pairs), 4), dtype=np.int64)
        backing[:, ::2] = pairs
        supplied = backing[:, ::2]
        self.assertFalse(supplied.flags.c_contiguous)
        expected = native.evaluate(positions, rotations, supplied.copy(), .001)
        bound = native.bind_pairs(supplied)
        backing[:] = 0
        self.assert_details_identical(expected, bound.evaluate(positions, rotations, .001))
        self.assert_summary_matches(expected, bound.summary(positions, rotations, .001))

    def test_frame_changes_invalidate_support_cache(self):
        native, positions, rotations, pairs = self.fixture()
        bound = native.bind_pairs(pairs)
        clear = bound.evaluate(positions, rotations, .001)
        changed_positions, changed_rotations = positions.copy(), rotations.copy()
        changed_positions[1] = changed_positions[0]
        changed_rotations[1] = np.eye(3)
        changed = bound.evaluate(changed_positions, changed_rotations, .001)
        self.assertTrue(clear['certified'].all())
        self.assertFalse(changed['certified'].all())
        self.assert_details_identical(
            native.evaluate(changed_positions, changed_rotations, pairs, .001), changed)
        self.assert_details_identical(clear, bound.evaluate(positions, rotations, .001))

    def test_invalid_pair_dtype_shape_and_index_raise_without_truncation(self):
        native, positions, rotations, _ = self.fixture()
        invalid = (
            np.asarray([[0., 1.]]), np.asarray([[False, True]]),
            np.asarray([[0, 1]], dtype=object),
            np.asarray([0, 1], dtype=np.int64),
            np.asarray([[0, 1, 2]], dtype=np.int64),
            np.asarray([[-1, 1]], dtype=np.int64),
            np.asarray([[0, 3]], dtype=np.int64),
            np.asarray([[0, np.iinfo(np.uint64).max]], dtype=np.uint64),
        )
        for pairs in invalid:
            with self.subTest(dtype=str(pairs.dtype), values=pairs.tolist()):
                with self.assertRaises(ValueError):
                    native.bind_pairs(pairs)
                with self.assertRaises(ValueError):
                    native.evaluate(positions, rotations, pairs, .001)

    def test_empty_summary_retains_value_error(self):
        native, positions, rotations, _ = self.fixture()
        with self.assertRaises(ValueError):
            native.bind_pairs(np.asarray([], dtype=np.int64))
        empty = native.bind_pairs(np.empty((0, 2), dtype=np.int64))
        with self.assertRaises(ValueError):
            empty.summary(positions, rotations, .001)

    def test_malformed_frame_shapes_rejected_by_both_bound_apis(self):
        native, positions, rotations, pairs = self.fixture()
        bound = native.bind_pairs(pairs)
        for p, R in ((positions[:-1], rotations), (positions, rotations[:-1]),
                     (positions.ravel(), rotations), (positions, rotations.reshape(3, 9))):
            for method in (bound.evaluate, bound.summary):
                with self.subTest(position_shape=p.shape, rotation_shape=R.shape,
                                  method=method.__name__), self.assertRaises(ValueError):
                    method(p, R, .001)

    def test_later_calls_cannot_overwrite_retained_detail_views(self):
        native, positions, rotations, pairs = self.fixture()
        bound = native.bind_pairs(pairs)
        first = bound.evaluate(positions, rotations, .001)
        saved = {field: array.copy() for field, array in first.items()}
        positions[1] = positions[0]
        second = bound.evaluate(positions, rotations, .001)
        self.assertFalse(second['certified'].all())
        bound.summary(positions, rotations, .002)
        self.assert_details_identical(first, saved)
        for field in DETAIL_FIELDS:
            self.assertFalse(np.shares_memory(first[field], second[field]), field)

    def test_parent_close_rejects_bound_evaluate_summary_and_new_binding(self):
        native, positions, rotations, pairs = self.fixture()
        bound = native.bind_pairs(pairs)
        native.close()
        native.close()
        for method in (bound.evaluate, bound.summary):
            with self.subTest(method=method.__name__), self.assertRaisesRegex(RuntimeError, 'closed'):
                method(positions, rotations, .001)
        with self.assertRaisesRegex(RuntimeError, 'closed'):
            native.bind_pairs(pairs)
        with self.assertRaisesRegex(RuntimeError, 'closed'):
            native.evaluate(positions, rotations, pairs, .001)

    def test_invalid_margin_fails_closed_in_detail_and_summary(self):
        native, positions, rotations, pairs = self.fixture()
        bound = native.bind_pairs(pairs)
        for margin in (0., -.001, np.nan, np.inf, -np.inf):
            with self.subTest(margin=margin):
                detail = bound.evaluate(positions, rotations, margin)
                self.assertFalse(detail['certified'].any())
                self.assertEqual(set(detail['reason']), {'invalid_margin'})
                self.assert_details_identical(
                    native.evaluate(positions, rotations, pairs, margin), detail)
                summary = bound.summary(positions, rotations, margin)
                self.assert_summary_matches(detail, summary)
                self.assertFalse(summary['valid'])

    def test_nonfinite_frames_fail_closed_without_using_previous_certificates(self):
        native, positions, rotations, pairs = self.fixture()
        bound = native.bind_pairs(pairs)
        self.assertTrue(bound.summary(positions, rotations, .001)['valid'])
        for field in ('positions', 'rotations'):
            for value in (np.nan, np.inf, -np.inf):
                with self.subTest(field=field, value=value):
                    p, R = positions.copy(), rotations.copy()
                    (p if field == 'positions' else R).flat[0] = value
                    detail = bound.evaluate(p, R, .001)
                    self.assertFalse(detail['certified'].any())
                    self.assertEqual(set(detail['reason']), {'nonfinite_or_unsupported_arithmetic'})
                    summary = bound.summary(p, R, .001)
                    self.assert_summary_matches(detail, summary)
                    self.assertFalse(summary['valid'])
        self.assertTrue(bound.summary(positions, rotations, .001)['valid'])

    @unittest.skipUnless(sys.platform.startswith('linux') and
                         platform.machine().lower() in ('x86_64', 'amd64'),
                         'This FE_DOWNWARD constant belongs to the Linux x86 fenv ABI')
    def test_changed_arithmetic_environment_fails_closed_and_is_not_reset(self):
        native, positions, rotations, pairs = self.fixture()
        bound = native.bind_pairs(pairs)
        library = ctypes.util.find_library('m')
        if not library:
            self.skipTest('libm fenv entry points unavailable')
        fenv = ctypes.CDLL(library)
        fenv.fegetround.argtypes, fenv.fegetround.restype = [], ctypes.c_int
        fenv.fesetround.argtypes, fenv.fesetround.restype = [ctypes.c_int], ctypes.c_int
        original = fenv.fegetround()
        self.assertEqual(original, 0, 'Native constructor requires FE_TONEAREST')
        downward = 0x400
        try:
            self.assertEqual(fenv.fesetround(downward), 0)
            detail = bound.evaluate(positions, rotations, .001)
            self.assertFalse(detail['certified'].any())
            self.assertEqual(set(detail['reason']), {'invalid_arithmetic_environment'})
            summary = bound.summary(positions, rotations, .001)
            self.assertFalse(summary['valid'])
            self.assertEqual(summary['certificate_reason'], 'invalid_arithmetic_environment')
            self.assertEqual(summary['certified_pairs'], 0)
            self.assertEqual(summary['checked_pairs'], len(pairs))
            self.assertEqual(fenv.fegetround(), downward, 'Query must not repair caller fenv')
        finally:
            restored = fenv.fesetround(original)
        self.assertEqual(restored, 0)
        self.assertEqual(fenv.fegetround(), original)
        self.assertTrue(bound.summary(positions, rotations, .001)['valid'])

    def test_real_rotating_jaw_first_failure_preserves_callback_prefix(self):
        model = mujoco.MjModel.from_xml_string(rig_xml())
        checker = ConservativeCollisionChecker(model, gripper=.5, margin_m=.001)
        self.addCleanup(checker.native.close)
        opened, closed = np.r_[np.zeros(5), .5], np.r_[np.zeros(5), .015]
        detail_prefix, summary_prefix = [], []

        def detailed_valid(q):
            detail_prefix.append(np.asarray(q, dtype=np.float64).copy())
            checker.data.qpos[:] = q
            checker.data.qvel[:] = 0
            mujoco.mj_kinematics(model, checker.data)
            result = checker.native.evaluate(
                checker.data.geom_xpos[checker.geometry_ids],
                checker.data.geom_xmat[checker.geometry_ids].reshape(-1, 3, 3),
                checker.pair_indices, checker.margin_m)
            return bool(result['certified'].all())

        def summary_valid(q):
            summary_prefix.append(np.asarray(q, dtype=np.float64).copy())
            return checker.evaluate(q, require_fixed_gripper=False)['valid']

        with patch.object(mujoco, 'mj_step', side_effect=AssertionError('No dynamics')), \
                patch.object(mujoco, 'mj_forward', side_effect=AssertionError('Kinematics only')), \
                patch.object(mujoco, 'mj_geomDistance', side_effect=AssertionError('No CCD')):
            self.assertTrue(checker.evaluate(opened, require_fixed_gripper=False)['valid'])
            self.assertTrue(checker.evaluate(closed, require_fixed_gripper=False)['valid'])
            self.assertFalse(checker.evaluate(np.r_[np.zeros(5), .25],
                                            require_fixed_gripper=False)['valid'])
            reference = validate_configuration_path(opened, closed, detailed_valid)
            actual = validate_configuration_path(opened, closed, summary_valid)
        self.assertEqual(actual, reference)
        self.assertFalse(actual['valid'])
        self.assertEqual(actual['required_states'], 244)
        self.assertGreater(actual['invalid_sample_index'], 0)
        self.assertLess(actual['checked_states'], actual['required_states'])
        self.assertEqual(actual['checked_states'], actual['invalid_sample_index'] + 1)
        self.assertEqual(len(summary_prefix), actual['checked_states'])
        self.assertEqual(len(detail_prefix), len(summary_prefix))
        for first, second in zip(detail_prefix, summary_prefix):
            self.assertEqual(first.tobytes(), second.tobytes())
        np.testing.assert_array_equal(summary_prefix[-1], actual['invalid_state'])


if __name__ == '__main__':
    unittest.main()
