"""Re-prove every scalar pose; preserve rejection, observers and ownership."""
import ctypes as C
import ctypes.util
from pathlib import Path
import platform
import sys
import unittest
from unittest.mock import patch

import mujoco
import numpy as np

from conservative_collision import ConservativeCollisionChecker
from configuration_sweep import validate_configuration_path
from route_policy import RoutePolicy, load_route_policy
from test_conservative_collision import rig_xml
import test_support_bound_query as bound_tests
from visual_grasp_controller import VisualGraspController


class ScalarDirectionHintsTests(unittest.TestCase):
    def controller(self, selected, *, middle_collision=False):
        xml = rig_xml()
        if not middle_collision:
            xml = xml.replace('pos=".0484456 .0123702 0"', 'pos=".3 .1 0"')
        checker = ConservativeCollisionChecker(mujoco.MjModel.from_xml_string(xml),
                                                gripper=.5, margin_m=.001)
        self.addCleanup(checker.native.close)
        controller = VisualGraspController.__new__(VisualGraspController)
        controller.checker = checker
        controller.route_policy = RoutePolicy(scalar_direction_hints=selected)
        return controller

    def frame(self):
        native, positions, rotations, pairs = bound_tests.BoundPairQueryTests.fixture(self)
        return native, native.bind_pairs(pairs), positions, rotations

    @staticmethod
    def data_bytes(checker):
        return [getattr(checker.data, key).tobytes() for key in
                ('qpos', 'qvel', 'xpos', 'xquat', 'xmat', 'geom_xpos', 'geom_xmat')]

    def test_all_244_states_and_first_middle_collision_match(self):
        for middle in (False, True):
            reports, data = [], []
            for selected in (False, True):
                controller = self.controller(selected, middle_collision=middle)
                reports.append(validate_configuration_path(
                    [0.]*5+[.5], [0.]*5+[.015],
                    lambda q: controller._arm_valid(q[:5], q[5])))
                data.append(self.data_bytes(controller.checker))
            self.assertEqual(reports[0], reports[1])
            self.assertEqual(data[0], data[1])
            self.assertEqual(reports[1]['valid'], not middle)
            if middle:
                self.assertTrue(2 < reports[1]['checked_states'] < 244)
                self.assertTrue((controller.checker._native_query._scalar_directions[0] == -1).all())
            else:
                self.assertEqual(reports[1]['checked_states'], 244)
                self.assertIsNotNone(controller.checker._native_query._scalar_directions)

    def test_observed_original_or_optional_abi_and_missing_symbol_keep_original(self):
        for symbol in ('ns_evaluate_hinted', 'ns_evaluate_direction_hinted', 'missing'):
            with self.subTest(symbol=symbol):
                controller = self.controller(True)
                checker = controller.checker
                controller._arm_valid(np.zeros(5), .5)
                lib = checker.native._lib
                original = lib.ns_evaluate_hinted
                calls = []

                def observed(*args):
                    calls.append(1)
                    return original(*args)

                if symbol == 'ns_evaluate_hinted':
                    callback = C.CFUNCTYPE(original.restype, *original.argtypes)(observed)
                    change = patch.object(lib, symbol, callback)
                else:
                    replacement = None if symbol == 'missing' else observed
                    change = patch.object(lib, 'ns_evaluate_direction_hinted', replacement)
                with change:
                    if symbol == 'ns_evaluate_hinted':
                        for jaw in (.5, .4, .3):
                            self.assertTrue(controller._arm_valid(np.zeros(5), jaw))
                        self.assertEqual(len(calls), 3)
                    else:
                        q = np.r_[np.zeros(5), .5]
                        self.assertEqual(checker.evaluate(q),
                                         checker.evaluate(q, direction_hints=True))
                        self.assertEqual(calls, [])
                self.assertTrue((checker._native_query._scalar_directions[0] == -1).all())

    def test_custom_checker_callbacks_keep_original_signature(self):
        controller = self.controller(True)
        checker = controller.checker
        original = ConservativeCollisionChecker.evaluate
        calls = []

        def observed(q, *, require_fixed_gripper=True):
            calls.append(require_fixed_gripper)
            return original(checker, q, require_fixed_gripper=require_fixed_gripper)

        with patch.object(checker, 'evaluate', observed):
            self.assertTrue(controller._arm_valid(np.zeros(5), .5))
        self.assertEqual(calls, [False])
        calls.clear()

        def class_observer(self, q, *, require_fixed_gripper=True):
            calls.append(require_fixed_gripper)
            return original(self, q, require_fixed_gripper=require_fixed_gripper)

        with patch.object(ConservativeCollisionChecker, 'evaluate', class_observer):
            self.assertTrue(controller._arm_valid(np.zeros(5), .5))
        self.assertEqual(calls, [False])
        self.assertIsNone(checker._native_query._scalar_directions)

    def test_fixed_jaw_limits_margin_and_fk_errors_are_unchanged(self):
        controller = self.controller(True)
        checker = controller.checker
        for q in (np.ones(6)*2, np.ones(6)*np.nan, [0.]*3):
            self.assertEqual(checker.evaluate(q), checker.evaluate(q, direction_hints=True))
        self.assertEqual(checker.evaluate([0.]*6), checker.evaluate([0.]*6, direction_hints=True))
        for margin in (0., np.nan):
            with self.assertRaises(ValueError):
                checker.evaluate([0.]*5+[.5], certificate_margin_m=margin, direction_hints=True)
        for error in (RuntimeError('FK failed'), KeyboardInterrupt('FK stop')):
            with patch.object(mujoco, 'mj_kinematics', side_effect=error):
                if isinstance(error, RuntimeError):
                    self.assertFalse(controller._arm_valid(np.zeros(5), .5))
                else:
                    with self.assertRaises(KeyboardInterrupt) as raised:
                        controller._arm_valid(np.zeros(5), .5)
                    self.assertIs(raised.exception, error)

    def test_failure_and_closed_owner_do_not_publish_hints(self):
        native, bound, p, R = self.frame()
        self.assertTrue(bound.summary(p, R, .001, direction_hints=True)['valid'])
        previous, saved = native._witness_hints, native._witness_hints.tobytes()
        directions = bound._scalar_directions
        self.assertFalse(np.shares_memory(directions[0], directions[1]))
        for fault in ('overlap', 'nonfinite', 'margin'):
            bad, margin = p.copy(), .001
            if fault == 'overlap':
                bad[1] = bad[0]
            elif fault == 'nonfinite':
                bad[0, 0] = np.nan
            else:
                margin = np.nan
            self.assertFalse(bound.summary(bad, R, margin, direction_hints=True)['valid'])
            self.assertIs(native._witness_hints, previous)
            self.assertEqual(previous.tobytes(), saved)
            self.assertTrue((directions[0] == -1).all())
        self.assertTrue(bound.summary(p, R, .001, direction_hints=True)['valid'])
        self.assertFalse(native._witness_hints.flags.writeable)
        self.assertFalse(np.shares_memory(native._witness_hints, bound._summary_hint_out))
        original = native._lib.ns_evaluate_hinted
        with patch.object(native._lib, 'ns_evaluate_hinted', lambda *args: 1):
            previous = native._witness_hints
            with self.assertRaisesRegex(RuntimeError, 'failed closed'):
                bound.summary(p, R, .001, direction_hints=True)
            self.assertIs(native._witness_hints, previous)
        self.assertIs(native._lib.ns_evaluate_hinted, original)
        native.close()
        with self.assertRaisesRegex(RuntimeError, 'closed'):
            bound.summary(p, R, .001, direction_hints=True)

    def test_conversion_reentry_and_errors_keep_outer_owned_frame(self):
        for conversion in ('positions', 'rotations', 'margin', 'error'):
            with self.subTest(conversion=conversion):
                native, bound, p, R = self.frame()
                self.assertTrue(bound.summary(p, R, .001, direction_hints=True)['valid'])
                bad = p.copy()
                bad[1] = bad[0]
                nested = []
                error = ValueError('original conversion error')

                def recurse():
                    nested.append(bound.summary(bad, R, .001, direction_hints=True))

                class ArrayInput:
                    def __init__(self, value):
                        self.value = value

                    def __array__(self, dtype=None, copy=None):
                        recurse()
                        if conversion == 'error':
                            raise error
                        return np.array(self.value, dtype=dtype, copy=True)

                class MarginInput:
                    def __float__(self):
                        recurse()
                        # Conversion happens after the owned p/R snapshot.
                        p[1] = p[0]
                        return .001

                a = ArrayInput(p) if conversion == 'positions' else p
                b = ArrayInput(R) if conversion in ('rotations', 'error') else R
                margin = MarginInput() if conversion == 'margin' else .001
                if conversion == 'error':
                    with self.assertRaises(ValueError) as raised:
                        bound.summary(a, b, margin, direction_hints=True)
                    self.assertIs(raised.exception, error)
                else:
                    self.assertTrue(bound.summary(a, b, margin, direction_hints=True)['valid'])
                self.assertEqual(len(nested), 1)
                self.assertFalse(nested[0]['valid'])
                self.assertFalse(bound._summary_busy)
                if conversion == 'error':
                    self.assertTrue((bound._scalar_directions[0] == -1).all())
                self.assertFalse(bound.summary(bad, R, .001, direction_hints=True)['valid'])

    @unittest.skipUnless(sys.platform.startswith('linux') and
                         platform.machine().lower() in ('x86_64', 'amd64'), 'Linux x86 fenv')
    def test_changed_rounding_environment_keeps_original_rejection(self):
        native, bound, p, R = self.frame()
        bound.summary(p, R, .001, direction_hints=True)
        library = ctypes.util.find_library('m')
        if not library:
            self.skipTest('libm fenv unavailable')
        fenv = C.CDLL(library)
        fenv.fegetround.argtypes, fenv.fegetround.restype = [], C.c_int
        fenv.fesetround.argtypes, fenv.fesetround.restype = [C.c_int], C.c_int
        previous = fenv.fegetround()
        try:
            self.assertEqual(fenv.fesetround(0x400), 0)
            original = bound.summary(p, R, .001)
            actual = bound.summary(p, R, .001, direction_hints=True)
            self.assertEqual(np.float64(original.pop('lower_bound_m')).tobytes(),
                             np.float64(actual.pop('lower_bound_m')).tobytes())
            self.assertEqual(original, actual)
            self.assertFalse(actual['valid'])
            self.assertEqual(fenv.fegetround(), 0x400)
            self.assertTrue((bound._scalar_directions[0] == -1).all())
        finally:
            self.assertEqual(fenv.fesetround(previous), 0)

    def test_direction_state_is_private_and_default_does_not_allocate_it(self):
        native, first, p, R = self.frame()
        second = native.bind_pairs(first._pairs[::-1])
        first.summary(p, R, .001)
        self.assertIsNone(first._scalar_directions)
        first.summary(p, R, .001, direction_hints=True)
        saved = first._scalar_directions[0].tobytes()
        self.assertIsNone(second._scalar_directions)
        second.summary(p, R, .001, direction_hints=True)
        self.assertIsNot(first._scalar_directions, second._scalar_directions)
        second._scalar_directions[0].fill(-1)
        self.assertEqual(first._scalar_directions[0].tobytes(), saved)

    def test_candidate_only_enables_one_flag_and_shortcut_stays_original(self):
        root = Path(__file__).parent/'route_strategies'
        parent = load_route_policy(root/'direction_hint_single_pass.py')[0]
        child = load_route_policy(root/'scalar_direction_hints.py')[0]
        self.assertFalse(load_route_policy()[0].scalar_direction_hints)
        self.assertEqual([k for k, v in child.preferences().items()
                          if parent.preferences()[k] != v], ['scalar_direction_hints'])
        with self.assertRaises(ValueError):
            RoutePolicy(scalar_direction_hints=1)
        controller = self.controller(True)
        original = controller.checker._native_query.summary
        with patch.object(controller.checker._native_query, 'summary', wraps=original) as summary:
            self.assertTrue(controller._approach_shortcut_valid(np.zeros(5)))
        self.assertEqual(summary.call_args.kwargs, {})
        self.assertIsNone(controller.checker._native_query._scalar_directions)


if __name__ == '__main__':
    unittest.main()
