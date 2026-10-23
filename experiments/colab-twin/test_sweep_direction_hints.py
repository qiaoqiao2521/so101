"""Real optional ABI integration: same grid, rejection prefix and observers."""
import ctypes as C
import unittest
from unittest.mock import patch
import warnings

import mujoco
import numpy as np

from conservative_collision import ConservativeCollisionChecker
from configuration_sweep import validate_configuration_path
import sweep_batch
from test_conservative_collision import rig_xml


class SweepDirectionHintsTests(unittest.TestCase):
    def checker(self, *, middle_collision=False):
        xml = rig_xml()
        if not middle_collision:
            xml = xml.replace('pos=".0484456 .0123702 0"', 'pos=".3 .1 0"')
        model = mujoco.MjModel.from_xml_string(xml)
        checker = ConservativeCollisionChecker(model, gripper=.5, margin_m=.001)
        self.addCleanup(checker.native.close)
        return checker

    def sweep(self, checker, validator):
        return validate_configuration_path(
            [0.]*5+[.5], [0.]*5+[.015],
            lambda q: checker.evaluate(q, require_fixed_gripper=False)['valid'],
            batch_valid=validator)

    def test_all_244_points_and_final_data_match_original(self):
        reports, states = [], []
        before = sweep_batch.runtime_metadata()
        for selected in (False, True):
            checker = self.checker()
            validator = sweep_batch.make_validator(checker, direction_hints=selected)
            self.assertIsNotNone(validator)
            reports.append(self.sweep(checker, validator))
            states.append([getattr(checker.data, key).tobytes() for key in
                           ('qpos', 'qvel', 'xpos', 'xquat', 'xmat', 'geom_xpos', 'geom_xmat')])
        after = sweep_batch.runtime_metadata()
        self.assertEqual(reports[0], reports[1])
        self.assertEqual(states[0], states[1])
        self.assertTrue(reports[1]['valid'])
        self.assertEqual(reports[1]['checked_states'], 244)
        self.assertEqual(after['direction_sweeps']-before['direction_sweeps'], 1)
        self.assertEqual(after['direction_hint_attempts']-before['direction_hint_attempts'], 243)
        self.assertGreaterEqual(after['direction_certificate_work']-
                                before['direction_certificate_work'], 244)

    def test_original_first_middle_collision_is_not_hidden(self):
        reports = []
        for selected in (False, True):
            checker = self.checker(middle_collision=True)
            reports.append(self.sweep(checker, sweep_batch.make_validator(
                checker, direction_hints=selected)))
        self.assertEqual(reports[0], reports[1])
        self.assertFalse(reports[1]['valid'])
        self.assertGreater(reports[1]['checked_states'], 2)
        self.assertLess(reports[1]['checked_states'], 244)

    def test_c_abi_observer_before_or_after_factory_still_sees_every_point(self):
        for before_factory in (False, True):
            with self.subTest(before_factory=before_factory):
                checker = self.checker()
                lib = checker.native._lib
                original = lib.ns_evaluate_hinted
                calls = []
                callback_type = C.CFUNCTYPE(original.restype, *original.argtypes)

                @callback_type
                def observed(*args):
                    calls.append(1)
                    return original(*args)

                validator = None if before_factory else sweep_batch.make_validator(
                    checker, direction_hints=True)
                initial = sweep_batch.runtime_metadata()['direction_sweeps']
                with patch.object(lib, 'ns_evaluate_hinted', observed), \
                        warnings.catch_warnings(record=True) as captured:
                    warnings.simplefilter('always')
                    if before_factory:
                        validator = sweep_batch.make_validator(checker, direction_hints=True)
                    result = self.sweep(checker, validator)
                self.assertTrue(result['valid'])
                self.assertEqual(len(calls), result['checked_states'])
                self.assertEqual(sweep_batch.runtime_metadata()['direction_sweeps'], initial)
                self.assertEqual(len(captured), int(before_factory))

    def test_missing_optional_symbol_retains_original_batch(self):
        for target in ('kernel', 'bridge'):
            with self.subTest(target=target):
                checker = self.checker()
                owner = checker.native._lib if target == 'kernel' else sweep_batch._get_bridge()
                symbol = 'ns_evaluate_direction_hinted' if target == 'kernel' else 'sb_run_direction'
                initial = sweep_batch.runtime_metadata()['direction_sweeps']
                with patch.object(owner, symbol, None), warnings.catch_warnings(record=True) as seen:
                    warnings.simplefilter('always')
                    validator = sweep_batch.make_validator(checker, direction_hints=True)
                    self.assertTrue(self.sweep(checker, validator)['valid'])
                self.assertEqual(len(seen), 1)
                self.assertEqual(sweep_batch.runtime_metadata()['direction_sweeps'], initial)

    def test_protected_fk_error_keeps_original_prefix_and_exception_object(self):
        for exception in (RuntimeError('original FK failure'), KeyboardInterrupt('original stop')):
            checker = self.checker()
            validator = sweep_batch.make_validator(checker, direction_hints=True)
            original = mujoco.mj_kinematics
            calls = []

            def fail_second(model, data):
                calls.append(1)
                if len(calls) == 2:
                    raise exception
                return original(model, data)

            with patch.object(mujoco, 'mj_kinematics', fail_second):
                if isinstance(exception, RuntimeError):
                    self.assertEqual(validator(np.zeros((4, 6))), (2, 1))
                else:
                    with self.assertRaises(KeyboardInterrupt) as raised:
                        validator(np.zeros((4, 6)))
                    self.assertIs(raised.exception, exception)
            self.assertEqual(len(calls), 2)


if __name__ == '__main__':
    unittest.main()
