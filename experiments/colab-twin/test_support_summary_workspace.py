"""Summary workspace ownership and lifecycle regressions with real static ABI.

Reuse existing finite geometry assertions. No physical integration, rendering,
planner, timing benchmark or alternate support arithmetic is used here.
"""
import threading
import unittest

import numpy as np

import support_native
import test_support_bound_query as bound_tests
import test_support_witness as witness_tests


class TracingLibrary:
    """Observe the real call before/after it; never fabricate certificates."""

    def __init__(self, owner, *, before=None, failed_status=False):
        self.original = owner._lib
        self.geometry_count = owner.geometry_count
        self.before = before
        self.failed_status = failed_status
        self.records = []

    def __getattr__(self, name):
        return getattr(self.original, name)

    def ns_evaluate_hinted(self, *args):
        count, geoms = int(args[4]), self.geometry_count
        row = {
            'positions': np.ctypeslib.as_array(args[1], shape=(geoms * 3,)).copy().reshape(geoms, 3),
            'rotations': np.ctypeslib.as_array(args[2], shape=(geoms * 9,)).copy().reshape(geoms, 3, 3),
            'pairs': np.ctypeslib.as_array(args[3], shape=(count * 2,)).copy().reshape(count, 2),
            'hint_in': np.ctypeslib.as_array(args[8], shape=(geoms * 6,)).copy().reshape(geoms, 3, 2),
        }
        self.records.append(row)
        if self.before is not None:
            self.before(row, args)
        status = self.original.ns_evaluate_hinted(*args)
        row['numeric'] = np.ctypeslib.as_array(args[6], shape=(count * 12,)).copy().reshape(count, 12)
        row['flags'] = np.ctypeslib.as_array(args[7], shape=(count * 6,)).copy().reshape(count, 6)
        row['hint_out'] = np.ctypeslib.as_array(args[9], shape=(geoms * 6,)).copy().reshape(geoms, 3, 2)
        row['actual_status'] = int(status)
        return 1 if self.failed_status else status


class SummaryWorkspaceTests(unittest.TestCase):
    def fixture(self):
        return bound_tests.BoundPairQueryTests.fixture(self)

    def mesh_fixture(self):
        points, kinds, positions, rotations, pairs = witness_tests.fixture()
        native = support_native.NativeSupport(points, kinds)
        self.addCleanup(native.close)
        return native, positions, rotations, pairs

    def assert_details_identical(self, first, second):
        bound_tests.BoundPairQueryTests.assert_details_identical(self, first, second)

    def assert_summary_matches(self, detail, summary):
        bound_tests.BoundPairQueryTests.assert_summary_matches(self, detail, summary)

    def decoded(self, native, row):
        return native._decode(row['numeric'], row['flags'])

    def test_array_and_margin_reentry_use_isolated_fresh_frames_and_recover(self):
        for conversion in ('positions', 'rotations', 'margin', 'rotations_raise'):
            with self.subTest(conversion=conversion):
                native, p, R, pairs = self.fixture()
                bound = native.bind_pairs(pairs)
                bad = p.copy()
                bad[1] = bad[0]
                expected_outer = native.evaluate(p, R, pairs, .001)
                expected_inner = native.evaluate(bad, R, pairs, .001)
                proxy = TracingLibrary(native)
                native._lib = proxy
                nested, invoked = [], []
                error = RuntimeError('array conversion interrupted after nested query')

                def recurse():
                    if not invoked:
                        invoked.append(True)
                        nested.append(bound.summary(bad, R, .001))

                class ArrayInput:
                    def __init__(self, values):
                        self.values = values

                    def __array__(self, dtype=None, copy=None):
                        recurse()
                        if conversion == 'rotations_raise':
                            raise error
                        return np.array(self.values, dtype=dtype, order='C', copy=True)

                class MarginInput:
                    def __float__(self):
                        recurse()
                        return .001

                supplied_p = ArrayInput(p) if conversion == 'positions' else p
                supplied_R = ArrayInput(R) if conversion.startswith('rotations') else R
                margin = MarginInput() if conversion == 'margin' else .001
                if conversion == 'rotations_raise':
                    with self.assertRaises(RuntimeError) as observed:
                        bound.summary(supplied_p, supplied_R, margin)
                    self.assertIs(observed.exception, error)
                    self.assertEqual(len(proxy.records), 1)
                else:
                    outer = bound.summary(supplied_p, supplied_R, margin)
                    self.assert_summary_matches(expected_outer, outer)
                    self.assertEqual(len(proxy.records), 2)
                    self.assert_details_identical(expected_outer, self.decoded(native, proxy.records[-1]))
                    self.assertEqual(proxy.records[-1]['positions'].tobytes(), p.tobytes())
                    self.assertEqual(proxy.records[-1]['rotations'].tobytes(), R.tobytes())
                self.assertEqual(len(nested), 1)
                self.assert_summary_matches(expected_inner, nested[0])
                self.assert_details_identical(expected_inner, self.decoded(native, proxy.records[0]))
                for row in proxy.records:
                    self.assertEqual(row['pairs'].tobytes(), pairs.tobytes())
                # Conversion failure must not leave the policy permanently busy.
                count = len(proxy.records)
                self.assert_summary_matches(expected_outer, bound.summary(p, R, .001))
                self.assertEqual(len(proxy.records), count + 1)

    def test_margin_conversion_cannot_change_already_owned_position_rotation_inputs(self):
        native, p, R, pairs = self.fixture()
        bound = native.bind_pairs(pairs)
        old_p, old_R = p.copy(), R.copy()
        expected = native.evaluate(old_p, old_R, pairs, .001)
        proxy = TracingLibrary(native)
        native._lib = proxy

        class MarginInput:
            def __float__(self):
                p[1] = p[0]
                R[1] = np.eye(3)
                return .001

        first = bound.summary(p, R, MarginInput())
        self.assert_summary_matches(expected, first)
        self.assertEqual(proxy.records[0]['positions'].tobytes(), old_p.tobytes())
        self.assertEqual(proxy.records[0]['rotations'].tobytes(), old_R.tobytes())
        self.assertNotEqual(p.tobytes(), old_p.tobytes())
        self.assertNotEqual(R.tobytes(), old_R.tobytes())
        second = bound.summary(p, R, .001)
        self.assertFalse(second['valid'])
        self.assertEqual(len(proxy.records), 2)
        self.assertEqual(proxy.records[1]['positions'].tobytes(), p.tobytes())
        self.assertEqual(proxy.records[1]['rotations'].tobytes(), R.tobytes())

    def test_native_status_failure_preserves_history_and_successful_retry_is_owned(self):
        native, p, R, pairs = self.mesh_fixture()
        bound = native.bind_pairs(pairs)
        self.assertTrue(bound.summary(p, R, .001)['valid'])
        history, saved = native._witness_hints, native._witness_hints.tobytes()
        self.assertTrue((history >= 0).any())
        self.assertFalse(history.flags.writeable)
        proxy = TracingLibrary(native, failed_status=True)
        native._lib = proxy
        with self.assertRaisesRegex(RuntimeError, 'failed closed'):
            bound.summary(p, R, .001)
        self.assertEqual(proxy.records[-1]['actual_status'], 0)
        self.assertTrue(proxy.records[-1]['flags'][:, 0].all())
        self.assertIs(native._witness_hints, history)
        self.assertEqual(native._witness_hints.tobytes(), saved)
        proxy.failed_status = False
        self.assertTrue(bound.summary(p, R, .001)['valid'])
        published = native._witness_hints
        self.assertIsNot(published, history)
        self.assertFalse(published.flags.writeable)
        self.assertFalse(np.shares_memory(published, bound._summary_hint_out))
        self.assertFalse(np.shares_memory(published, bound._summary_hint_in))
        self.assertEqual(published.tobytes(), proxy.records[-1]['hint_out'].tobytes())
        for fault in ('margin', 'nonfinite', 'overlap'):
            frame = p.copy()
            margin = .001
            if fault == 'margin':
                margin = np.nan
            elif fault == 'nonfinite':
                frame[0, 0] = np.nan
            else:
                frame[1] = frame[0]
            with self.subTest(fault=fault):
                self.assertFalse(bound.summary(frame, R, margin)['valid'])
                self.assertIs(native._witness_hints, published)
        self.assertEqual(history.tobytes(), saved)
        self.assertTrue(bound.summary(p, R, .001)['valid'])

    def test_public_detail_and_summary_remain_independent_across_policies_and_calls(self):
        native, p, R, pairs = self.fixture()
        a = native.bind_pairs(pairs)
        reversed_pairs = np.vstack((pairs[::-1, ::-1], pairs[1:2]))
        b = native.bind_pairs(reversed_pairs)
        first = a.evaluate(p, R, .001)
        saved = {name: value.copy() for name, value in first.items()}
        original_summary = a.summary(p, R, .001)
        saved_summary = original_summary.copy()
        for arrays in ('plain', 'noncontiguous', 'arraylike', 'readonly'):
            with self.subTest(arrays=arrays):
                frame, rotations = p.copy(), R.copy()
                frame[1] = frame[0]
                if arrays == 'noncontiguous':
                    frame = np.asfortranarray(frame)
                    rotations = np.asfortranarray(rotations)
                elif arrays == 'arraylike':
                    frame, rotations = frame.tolist(), rotations.tolist()
                elif arrays == 'readonly':
                    frame.setflags(write=False)
                    rotations.setflags(write=False)
                expected_b = native.evaluate(frame, rotations, reversed_pairs, .002)
                self.assert_summary_matches(expected_b, b.summary(frame, rotations, .002))
                expected_a = native.evaluate(frame, rotations, pairs, .001)
                self.assert_summary_matches(expected_a, a.summary(frame, rotations, .001))
                self.assert_details_identical(first, saved)
                self.assertEqual(original_summary, saved_summary)
        fresh = a.evaluate(p, R, .001)
        self.assert_details_identical(first, fresh)
        for name in bound_tests.DETAIL_FIELDS:
            self.assertFalse(np.shares_memory(first[name], fresh[name]), name)
        for name in ('_summary_positions', '_summary_rotations', '_summary_numeric',
                     '_summary_flags', '_summary_hint_in', '_summary_hint_out'):
            self.assertFalse(np.shares_memory(getattr(a, name), getattr(b, name)), name)

    def test_same_owner_serializes_policies_and_close_while_other_owner_progresses(self):
        native, p, R, pairs = self.mesh_fixture()
        a = native.bind_pairs(pairs)
        b_pairs = np.vstack((pairs[:, ::-1], pairs, pairs))
        b = native.bind_pairs(b_pairs)
        entered, release, second_entered = threading.Event(), threading.Event(), threading.Event()
        second_attempted = threading.Event()
        results, errors, threads = {}, [], []

        def blocked(row, args):
            if len(proxy.records) == 1:
                entered.set()
                if not release.wait(5):
                    raise RuntimeError('test did not release the owned native call')
            else:
                second_entered.set()

        proxy = TracingLibrary(native, before=blocked)
        native._lib = proxy

        def start(name, call, attempted=None, finished=None):
            def run():
                if attempted is not None:
                    attempted.set()
                try:
                    results[name] = call()
                except BaseException as error:
                    errors.append(error)
                finally:
                    if finished is not None:
                        finished.set()
            thread = threading.Thread(target=run, daemon=False)
            threads.append(thread)
            thread.start()
            return thread

        try:
            caller_p, caller_R = p.copy(), R.copy()
            start('first', lambda: a.summary(caller_p, caller_R, .001))
            self.assertTrue(entered.wait(2))
            # The first call has already copied its inputs under the owner lock.
            caller_p[1] = caller_p[0]
            caller_R[0] = np.eye(3)
            start('second', lambda: b.summary(p, R, .001), second_attempted)
            self.assertTrue(second_attempted.wait(2))
            self.assertFalse(second_entered.wait(.05))
            release.set()
            for thread in threads:
                thread.join(3)
                self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])
            self.assertTrue(results['first']['valid'])
            self.assertTrue(results['second']['valid'])
            self.assertEqual(len(proxy.records), 2)
            self.assertEqual(proxy.records[0]['positions'].tobytes(), p.tobytes())
            self.assertEqual(proxy.records[0]['rotations'].tobytes(), R.tobytes())
            self.assertTrue((proxy.records[0]['hint_out'] >= 0).any())
            self.assertEqual(proxy.records[1]['hint_in'].tobytes(), proxy.records[0]['hint_out'].tobytes())
            self.assertEqual(proxy.records[1]['pairs'].tobytes(), b_pairs.tobytes())

            # Test close separately; do not assume fairness between queued B
            # and close. A different owner must remain independently usable.
            entered.clear()
            release.clear()
            proxy.records.clear()
            other, other_p, other_R, other_pairs = self.fixture()
            other_bound = other.bind_pairs(other_pairs)
            close_attempted, closed, other_finished = threading.Event(), threading.Event(), threading.Event()
            start('inflight', lambda: a.summary(p, R, .001))
            self.assertTrue(entered.wait(2))
            start('close', native.close, close_attempted, closed)
            self.assertTrue(close_attempted.wait(2))
            self.assertFalse(closed.wait(.05))
            start('other', lambda: other_bound.summary(other_p, other_R, .001), finished=other_finished)
            self.assertTrue(other_finished.wait(2))
            self.assertTrue(results['other']['valid'])
            release.set()
            for thread in threads:
                thread.join(3)
                self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])
            self.assertTrue(closed.is_set())
            for policy in (a, b):
                for method in (policy.summary, policy.evaluate):
                    with self.assertRaisesRegex(RuntimeError, 'closed'):
                        method(p, R, .001)
        finally:
            release.set()
            for thread in threads:
                thread.join(3)
            self.assertTrue(all(not thread.is_alive() for thread in threads))


if __name__ == '__main__':
    unittest.main()
