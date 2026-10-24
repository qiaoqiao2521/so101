"""Optional batching preserves sampler density, failure prefixes and fallbacks."""
import ctypes as C
import subprocess
from threading import RLock
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import warnings

import numpy as np

from configuration_sweep import (ConfigurationSweepInvocation, SweepBinding,
                                 validate_configuration_path)
import sweep_batch


class SweepBatchTests(unittest.TestCase):
    def bridge_fixture(self):
        from conservative_collision import ConservativeCollisionChecker
        checker = ConservativeCollisionChecker.__new__(ConservativeCollisionChecker)
        checker.model = SimpleNamespace(nq=6, nv=6, njnt=6, _address=1)
        checker.data = SimpleNamespace(_address=2)
        checker.geometry_ids = np.array([0, 1], dtype=np.int64)
        checker.margin_m = .001
        query = C.CFUNCTYPE(C.c_int)(lambda: 0)
        owner = SimpleNamespace(geometry_count=2, _lib=SimpleNamespace(ns_evaluate_hinted=query),
                                _handle=1, _lock=RLock(), _witness_hints=np.zeros(1, dtype=np.int64))
        bound = SimpleNamespace(_owner=owner, _pairs=[(0, 1)], _summary_busy=False)
        for field in ('pairs', 'positions', 'rotations', 'numeric', 'flags', 'hint_in', 'hint_out'):
            setattr(bound, '_summary_'+field+'_pointer', None)
        checker._native_query = bound

        def run(*args):
            # ABI-only fixture; do not dereference model addresses or run physics.
            count, info = args[3], args[-1]
            info[0], info[1], info[2], info[3] = count, -1, count, count
            return 0

        bridge = SimpleNamespace(sb_run=Mock(side_effect=run))
        return checker, bridge

    def test_unsupported_checker_keeps_scalar_path_without_preparation(self):
        with patch.object(sweep_batch, '_get_bridge') as prepare:
            self.assertIsNone(sweep_batch.make_validator(SimpleNamespace()))
        prepare.assert_not_called()

    def test_enabled_scalar_refinement_skips_bridge_preparation(self):
        from conservative_collision import ConservativeCollisionChecker
        checker = ConservativeCollisionChecker.__new__(ConservativeCollisionChecker)
        checker.mesh_box_axis_refinement = True
        with patch.object(sweep_batch, '_get_bridge') as prepare:
            self.assertIsNone(sweep_batch.make_validator(checker))
        prepare.assert_not_called()

    def test_default_or_false_refinement_keeps_original_native_batch(self):
        for explicit_false in (False, True):
            with self.subTest(explicit_false=explicit_false):
                checker, bridge = self.bridge_fixture()
                if explicit_false:
                    checker.mesh_box_axis_refinement = False
                with patch.object(sweep_batch, '_get_bridge', return_value=bridge) as prepare:
                    validate = sweep_batch.make_validator(checker)
                self.assertIsNotNone(validate)
                prepare.assert_called_once_with()
                self.assertEqual(validate([[0.]*6, [0.]*5+[.1]]), (2, -1))
                bridge.sb_run.assert_called_once()

    def test_later_refinement_flag_requests_full_scalar_invocation_without_native(self):
        checker, bridge = self.bridge_fixture()
        with patch.object(sweep_batch, '_get_bridge', return_value=bridge):
            validate = sweep_batch.make_validator(checker)
        self.assertIsNotNone(validate)
        checker.mesh_box_axis_refinement = True
        self.assertIsNone(validate([[0.]*6, [0.]*5+[.1]]))
        start, end, samples = [0.]*5+[.5], [0.]*5+[.015], []
        binding = SweepBinding(checker, checker, checker.model, 'close', .015)
        invocation = ConfigurationSweepInvocation(start, end, binding=binding)
        invocation.execute(lambda q: samples.append(q) or True, batch_valid=validate)
        fallback = invocation.consume(binding)
        original = validate_configuration_path(start, end, lambda q: True)
        self.assertEqual(fallback, original)
        self.assertEqual(len(samples), 244)
        self.assertEqual(samples[0], start)
        self.assertEqual(samples[-1], end)
        bridge.sb_run.assert_not_called()

    def test_class_level_predicate_override_keeps_original_callback(self):
        from conservative_collision import ConservativeCollisionChecker
        checker = ConservativeCollisionChecker.__new__(ConservativeCollisionChecker)
        with patch.object(ConservativeCollisionChecker, 'evaluate', lambda self, q: False), \
                patch.object(sweep_batch, '_get_bridge') as prepare:
            self.assertIsNone(sweep_batch.make_validator(checker))
        prepare.assert_not_called()

    def test_optional_missing_compiler_warns_once_and_keeps_scalar_path(self):
        with patch.object(sweep_batch, '_PREPARED', False), \
                patch.object(sweep_batch, '_LIB', None), \
                patch.object(sweep_batch.shutil, 'which', return_value=None), \
                patch.dict(sweep_batch._META, {}, clear=True), \
                warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter('always')
            self.assertIsNone(sweep_batch._get_bridge())
            self.assertIsNone(sweep_batch._get_bridge())
        self.assertEqual(len(observed), 1)
        self.assertIn('using original checks', str(observed[0].message))

    def test_optional_compile_timeout_uses_the_original_path(self):
        with patch.object(sweep_batch, '_PREPARED', False), \
                patch.object(sweep_batch, '_LIB', None), \
                patch.object(sweep_batch.native, '_compile_process',
                             side_effect=subprocess.TimeoutExpired('g++', 30)), \
                patch.dict(sweep_batch._META, {}, clear=True), \
                warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter('always')
            self.assertIsNone(sweep_batch._get_bridge())
        self.assertEqual(len(observed), 1)
        self.assertIn('using original checks', str(observed[0].message))

    def test_unavailable_batch_returns_the_original_failure_prefix(self):
        start, end = [0.]*6, [0.]*5+[.006]
        def run(batch):
            calls = []
            def valid(q):
                calls.append(q)
                return len(calls) < 3
            return validate_configuration_path(start, end, valid, batch_valid=batch), calls
        original, calls = run(None)
        fallback, fallback_calls = run(lambda states: None)
        self.assertEqual(fallback, original)
        self.assertEqual(fallback_calls, calls)

    def test_batch_cannot_report_all_valid_after_checking_only_a_prefix(self):
        with self.assertRaisesRegex(ValueError, 'invalid checked prefix'):
            validate_configuration_path([0.]*6, [0.]*5+[.006], lambda q: True,
                                        batch_valid=lambda states: (1, -1))

    def test_original_sample_budget_rejection_runs_neither_predicate(self):
        scalar, batch = Mock(return_value=True), Mock(return_value=(1, -1))
        result = validate_configuration_path([0.]*6, [0.]*5+[.5], scalar,
                                             max_samples=10, batch_valid=batch)
        self.assertEqual(result['reason'], 'sample_budget_exceeded')
        scalar.assert_not_called()
        batch.assert_not_called()
