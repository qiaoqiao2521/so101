"""Optional batching preserves sampler density, failure prefixes and fallbacks."""
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import warnings

from configuration_sweep import validate_configuration_path
import sweep_batch


class SweepBatchTests(unittest.TestCase):
    def test_unsupported_checker_keeps_scalar_path_without_preparation(self):
        with patch.object(sweep_batch, '_get_bridge') as prepare:
            self.assertIsNone(sweep_batch.make_validator(SimpleNamespace()))
        prepare.assert_not_called()

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
