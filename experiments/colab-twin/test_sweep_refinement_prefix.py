"""ABI-only prefix checks; no real model, FK, native query or simulation."""
import copy
import ctypes as C
from threading import RLock
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import numpy as np
from conservative_collision import ConservativeCollisionChecker
import support_native
import sweep_batch


class RefinementPrefixTests(unittest.TestCase):
    def fixture(self, reason=0, at=0):
        c = ConservativeCollisionChecker.__new__(ConservativeCollisionChecker)
        c.model = SimpleNamespace(nq=6, nv=6, njnt=6, _address=1)
        c.data = SimpleNamespace(_address=2, qpos=np.zeros(6), qvel=np.ones(6), extra=np.array([17., 19.]))
        c.geometry_ids = np.array([0, 1], dtype=np.int64)
        c.margin_m, c.mesh_box_axis_refinement = .001, True
        query = C.CFUNCTYPE(C.c_int)(lambda: 0)
        query.__name__ = 'ns_evaluate_hinted'
        owner = SimpleNamespace(geometry_count=2, _lib=SimpleNamespace(ns_evaluate_hinted=query, _FuncPtr=type(query)),
            _handle=1, _lock=RLock(), _witness_hints=np.array([7], dtype=np.int64), _query_generation=0)
        bound = support_native._BoundPairs.__new__(support_native._BoundPairs)
        bound._owner, bound._pairs = owner, np.array([[0, 1]], dtype=np.int64)
        bound._summary_busy, bound._scalar_directions = False, [np.array([31])]
        for field in ('pairs', 'positions', 'rotations', 'numeric', 'flags', 'hint_in', 'hint_out'):
            setattr(bound, '_summary_'+field+'_pointer', None)
        c._native_query, c.native = bound, owner
        calls = []
        def run(*args):
            q = np.ctypeslib.as_array(args[2], shape=(args[3]*6,)).reshape(-1, 6)
            committed, info = args[-2:]
            info[0], info[1], info[2], info[3], info[4] = 0, -1, 0, 0, 0
            callback = C.cast(args[8], sweep_batch._KINEMATICS)
            for index, row in enumerate(q):
                info[0] = index+1
                if reason == 1 and index == at:
                    info[1], info[4] = index, 1
                    break
                c.data.qpos[:], c.data.qvel[:] = row, 0
                c.data.extra[:] += 1
                if callback(None):
                    info[1], info[4] = index, 4
                    break
                calls.append(index)
                info[2] += 1
                if reason in (2, 3) and index == at:
                    info[1], info[4] = index, reason
                    break
                committed[0] += 1
                info[3] += 1
            return 0
        return c, SimpleNamespace(sb_run=Mock(side_effect=run)), calls

    @staticmethod
    def copy_data(target, model, source):
        address = target._address
        target.__dict__.update(copy.deepcopy(source.__dict__))
        target._address = address

    def prepare(self, c, bridge, **options):
        with patch.object(sweep_batch, '_get_bridge', return_value=bridge), \
                patch.object(sweep_batch.mujoco, 'MjData', side_effect=lambda model: SimpleNamespace(_address=3)):
            return sweep_batch.make_validator(c, **options)

    def call(self, validate, fk=None):
        with patch.object(sweep_batch.mujoco, 'mj_copyData', side_effect=self.copy_data), \
                patch.object(sweep_batch.mujoco, 'mj_kinematics', side_effect=fk):
            return validate([[.1]*6, [.2]*6])

    def test_default_refinement_and_direction_mode_do_not_prepare(self):
        c, bridge, _ = self.fixture()
        with patch.object(sweep_batch, '_get_bridge') as prepare:
            self.assertIsNone(sweep_batch.make_validator(c))
            self.assertIsNone(sweep_batch.make_validator(c, refinement_prefix=True, direction_hints=True))
            c.mesh_box_axis_refinement = False
            self.assertIsNone(sweep_batch.make_validator(c, refinement_prefix=True))
        prepare.assert_not_called()

    def test_clear_accepts_complete_prefix_without_clearing_direction_history(self):
        c, bridge, calls = self.fixture()
        validate = self.prepare(c, bridge, refinement_prefix=True)
        self.assertEqual(self.call(validate), (2, -1))
        np.testing.assert_array_equal(c.data.qpos, [.2]*6)
        self.assertEqual(calls, [0, 1])
        self.assertEqual(c.native._witness_hints[0], 9)
        self.assertEqual(c.native._query_generation, 3)
        self.assertEqual(c._refinement_generation, 3)
        self.assertEqual(c._native_query._scalar_directions[0][0], 31)
        self.assertEqual(validate.last_info, (2, -1, 2, 2, 0))

    def test_uncertified_restores_complete_data_and_hints_not_generation(self):
        c, bridge, calls = self.fixture(3, at=1)
        before = copy.deepcopy(c.data.__dict__)
        validate = self.prepare(c, bridge, refinement_prefix=True)
        self.assertIsNone(self.call(validate))
        for key, value in before.items():
            np.testing.assert_array_equal(getattr(c.data, key), value)
        self.assertEqual(c.native._witness_hints[0], 7)
        self.assertGreater(c.native._query_generation, 0)
        self.assertEqual(validate.metadata['restored'], 1)
        self.assertEqual(calls, [0, 1])

    def test_badq_and_native_error_keep_original_prefix_without_replay(self):
        for reason in (1, 2):
            with self.subTest(reason=reason):
                c, bridge, calls = self.fixture(reason, at=1)
                validate = self.prepare(c, bridge, refinement_prefix=True)
                self.assertEqual(self.call(validate), (2, 1))
                self.assertEqual(validate.last_info[4], reason)
                self.assertEqual(validate.metadata['restored'], 0)
                self.assertEqual(c.native._witness_hints[0], 8)
                self.assertEqual(bridge.sb_run.call_count, 1)

    def test_first_fk_runtime_error_keeps_original_error_and_written_data(self):
        c, bridge, calls = self.fixture()
        validate = self.prepare(c, bridge, refinement_prefix=True)
        def fk(*args):
            self.assertGreater(c.native._query_generation, 0)
            self.assertGreater(c._refinement_generation, 0)
            raise RuntimeError('first FK failed')
        self.assertEqual(self.call(validate, fk), (1, 0))
        self.assertEqual(validate.last_info[4], 4)
        np.testing.assert_array_equal(c.data.qpos, [.1]*6)
        self.assertEqual(calls, [])

    def test_baseexception_propagates_same_object_without_rollback(self):
        c, bridge, calls = self.fixture()
        validate = self.prepare(c, bridge, refinement_prefix=True)
        error = KeyboardInterrupt('original callback')
        def fk(*args): raise error
        with self.assertRaises(KeyboardInterrupt) as observed: self.call(validate, fk)
        self.assertIs(observed.exception, error)
        np.testing.assert_array_equal(c.data.qpos, [.1]*6)
        self.assertEqual(calls, [])
        self.assertFalse(c._native_query._summary_busy)

    def test_close_never_queries_stale_handle_or_restores_closed_hints(self):
        c, bridge, calls = self.fixture()
        validate = self.prepare(c, bridge, refinement_prefix=True)
        def fk(*args):
            c.native._handle = None
            c.native._witness_hints = np.array([99])
        self.assertIsNone(self.call(validate, fk))
        self.assertEqual(calls, [])
        self.assertEqual(c.native._witness_hints[0], 99)
        np.testing.assert_array_equal(c.data.qpos, [.1]*6)

    def test_reentry_preserves_callback_state_and_invalidates_details(self):
        c, bridge, calls = self.fixture()
        validate = self.prepare(c, bridge, refinement_prefix=True)
        def fk(*args):
            c.native._query_generation += 1
            c._refinement_generation += 1
            c.data.extra[:] = 85
            c.native._witness_hints = np.array([93])
        self.assertIsNone(self.call(validate, fk))
        self.assertEqual(calls, [])
        np.testing.assert_array_equal(c.data.extra, [85, 85])
        self.assertEqual(c.native._witness_hints[0], 93)
        self.assertGreater(c.native._query_generation, 2)

    def test_initial_observers_are_not_bypassed(self):
        for field in ('evaluate', '_evaluate_original', '_evaluate_with_details', '_refine_original'):
            c, bridge, _ = self.fixture()
            setattr(c, field, Mock())
            self.assertIsNone(self.prepare(c, bridge, refinement_prefix=True))
            bridge.sb_run.assert_not_called()
        c, bridge, _ = self.fixture()
        c.native._lib.ns_evaluate_hinted = Mock()
        self.assertIsNone(self.prepare(c, bridge, refinement_prefix=True))

    def test_changed_binding_returns_none_without_native_work(self):
        for field in ('margin', 'pairs', 'ids', 'handle', 'bound', 'native', 'observer'):
            with self.subTest(field=field):
                c, bridge, calls = self.fixture()
                validate = self.prepare(c, bridge, refinement_prefix=True)
                if field == 'margin': c.margin_m = .002
                elif field == 'pairs': c._native_query._pairs[0, 1] = 0
                elif field == 'ids': c.geometry_ids[0] = 1
                elif field == 'handle': c.native._handle = 7
                elif field == 'bound': c._native_query = SimpleNamespace()
                elif field == 'native': c.native = SimpleNamespace()
                else: c._evaluate_original = Mock()
                self.assertIsNone(self.call(validate))
                self.assertEqual(calls, [])
                bridge.sb_run.assert_not_called()

    def test_reentry_or_binding_change_then_fk_error_preserves_original_failure(self):
        for change in ('reentry', 'binding'):
            for error_type in (RuntimeError, ValueError):
                with self.subTest(change=change, error_type=error_type):
                    c, bridge, calls = self.fixture()
                    validate = self.prepare(c, bridge, refinement_prefix=True)
                    def fk(*args):
                        c.native._query_generation += 1
                        c._refinement_generation += 1
                        if change == 'binding': c.margin_m = .002
                        c.data.extra[:] = 85
                        c.native._witness_hints = np.array([93])
                        raise error_type('callback failed after mutation')
                    self.assertEqual(self.call(validate, fk), (1, 0))
                    self.assertEqual(bridge.sb_run.call_count, 1)
                    self.assertEqual(calls, [])
                    self.assertEqual(validate.last_info[4], 4)
                    self.assertEqual(validate.metadata['restored'], 0)
                    self.assertEqual(validate.metadata['original_error_prefixes'], 1)
                    np.testing.assert_array_equal(c.data.extra, [85, 85])
                    self.assertEqual(c.native._witness_hints[0], 93)
                    self.assertGreater(c.native._query_generation, 2)
                    self.assertGreater(c._refinement_generation, 2)

    def test_bound_summary_observer_is_preserved(self):
        c, bridge, _ = self.fixture()
        c._native_query.summary = Mock()
        self.assertIsNone(self.prepare(c, bridge, refinement_prefix=True))
        bridge.sb_run.assert_not_called()

    def test_callback_native_symbol_change_stops_before_abi_query(self):
        c, bridge, calls = self.fixture()
        validate = self.prepare(c, bridge, refinement_prefix=True)
        observer = Mock()
        def fk(*args):
            c.native._lib.ns_evaluate_hinted = observer
        self.assertIsNone(self.call(validate, fk))
        self.assertEqual(calls, [])
        observer.assert_not_called()

    def test_preexisting_closed_owner_rejects_before_snapshot(self):
        c, bridge, _ = self.fixture()
        c.native._handle = None
        self.assertIsNone(self.prepare(c, bridge, refinement_prefix=True))
        bridge.sb_run.assert_not_called()

    def test_callback_binding_change_stops_c_and_keeps_new_state(self):
        c, bridge, calls = self.fixture()
        validate = self.prepare(c, bridge, refinement_prefix=True)
        def fk(*args):
            c.margin_m = .002
            c.data.extra[:] = 42
        self.assertIsNone(self.call(validate, fk))
        self.assertEqual(calls, [])
        np.testing.assert_array_equal(c.data.extra, [42, 42])


if __name__ == '__main__': unittest.main()
