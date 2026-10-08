"""Event-controlled async transport lifecycle tests; no native or physics."""

import json
import math
import threading
import unittest
from unittest.mock import patch

from configuration_sweep import SweepBinding
from transport_worker import AsyncTransportPlanningJob, TransportPlan


class AsyncTransportTests(unittest.TestCase):
    def setUp(self):
        self.owner, self.checker, self.model = object(), object(), object()
        self.jobs = []

    def tearDown(self):
        for job in self.jobs:
            job.cancel_event.set()
            job.close()

    def binding(self, **changes):
        values = dict(owner=self.owner, checker=self.checker, model=self.model,
                      stage='hold', jaw_intent_rad=.015,
                      context=(('epoch', 1), ('target', (.24, -.13))))
        values.update(changes)
        return SweepBinding(**values)

    def job(self, binding=None):
        job = AsyncTransportPlanningJob(binding or self.binding())
        self.jobs.append(job)
        return job

    def plan(self):
        paths = [[[float(i)*.01, 0., 0., 0., 0.],
                  [float(i+1)*.01, -.0, .01, 0., 0.]] for i in range(5)]
        return TransportPlan(paths, json.dumps({
            'stage': 'transport_execution_plan',
            'legs': [{'index': i, 'path': path} for i, path in enumerate(paths)]}))

    def exited(self, job):
        # Test synchronization only. The production poll still must do join(0).
        job._thread.join(3.)
        self.assertFalse(job._thread.is_alive(), 'test worker did not exit')

    def completed(self, job=None):
        job = job or self.job()
        expected = self.plan()
        job.start(lambda: expected)
        self.exited(job)
        self.assertFalse(job.execution['joined'])
        with patch.object(job._thread, 'join', wraps=job._thread.join) as joined:
            self.assertTrue(job.poll())
        joined.assert_called_once_with(timeout=0)
        self.assertEqual(job.state, 'completed')
        self.assertTrue(job.execution['joined'])
        self.assertTrue(job.execution['launch_attempted'])
        self.assertTrue(job.execution['owned_ack'])
        self.assertFalse(job.execution['cleanup_unconfirmed'])
        self.assertFalse(job.execution['launch_unknown'])
        return job, expected

    def test_event_delayed_start_and_repeated_polls_do_not_wait_or_join(self):
        entered = threading.Event()
        seen = []
        job = self.job()
        expected, marker = self.plan(), object()

        def compute(argument):
            seen.append((argument, threading.current_thread()))
            entered.set()
            if not job.cancel_event.wait(3.):
                raise TimeoutError('test worker was not released')
            return expected

        job.start(compute, marker)
        self.assertTrue(entered.wait(3.))
        self.assertEqual(job.state, 'running')
        self.assertIs(seen[0][0], marker)
        self.assertFalse(seen[0][1].daemon)
        self.assertNotEqual(seen[0][1].ident, threading.get_ident())
        with patch.object(job._thread, 'join', side_effect=AssertionError('poll waited')):
            for _ in range(20):
                self.assertFalse(job.poll())
        self.assertEqual(job.execution['poll_count'], 20)
        self.assertFalse(job.execution['joined'])
        with self.assertRaises(RuntimeError):
            job.start(lambda: expected)
        job.cancel_event.set()  # Release the test callable, not reject this job.
        self.exited(job)
        self.assertTrue(job.poll())
        self.assertIs(job.consume(self.binding()), expected)

    def test_completed_peek_is_repeatable_but_consumption_is_once(self):
        job, expected = self.completed()
        for _ in range(2):
            self.assertIs(job.peek(self.binding()), expected)
        self.assertTrue(job.poll())
        self.assertIs(job.consume(self.binding()), expected)
        self.assertEqual(job.state, 'consumed')
        for operation in (lambda: job.consume(self.binding()),
                          lambda: job.peek(self.binding()), job.poll,
                          lambda: job.start(self.plan)):
            with self.assertRaises(RuntimeError):
                operation()
        execution = job.execution
        self.assertEqual(execution['mode'], 'isolated_thread_physics_advancing_hold')
        self.assertEqual(execution['main_thread_id'], threading.get_ident())
        self.assertNotEqual(execution['worker_thread_id'], threading.get_ident())
        self.assertTrue(math.isfinite(execution['worker_wall_s']))
        self.assertGreaterEqual(execution['worker_wall_s'], 0.)

    def test_new_or_closed_job_cannot_return_or_start_a_proposal(self):
        job = self.job()
        for operation in (job.poll, lambda: job.peek(self.binding()),
                          lambda: job.consume(self.binding())):
            with self.assertRaises(RuntimeError):
                operation()
        job.close()
        self.assertEqual(job.execution['state_before_close'], 'new')
        self.assertFalse(job.execution['joined'])
        with self.assertRaises(RuntimeError):
            job.start(self.plan)

    def test_stale_owner_epoch_jaw_and_signed_zero_permanently_reject(self):
        changes = ({'owner': object()}, {'checker': object()}, {'model': object()},
                   {'stage': 'transport'}, {'jaw_intent_rad': .5},
                   {'context': (('epoch', 2), ('target', (.24, -.13)))})
        for changed in changes:
            with self.subTest(changed=changed):
                job, _ = self.completed()
                with self.assertRaisesRegex(RuntimeError, 'context changed'):
                    job.peek(self.binding(**changed))
                self.assertEqual(job.state, 'rejected')
                self.assertTrue(job.cancel_event.is_set())
                for operation in (job.poll, lambda: job.consume(self.binding())):
                    with self.assertRaises(RuntimeError):
                        operation()
        original = self.binding(context=(('epoch', 1), ('signed_zero', -.0)))
        job, _ = self.completed(self.job(original))
        with self.assertRaises(RuntimeError):
            job.consume(self.binding(context=(('epoch', 1), ('signed_zero', .0))))
        with self.assertRaises(RuntimeError):
            job.consume(original)

    def test_worker_exception_and_baseexception_propagate_after_exit_with_cause(self):
        cause = ValueError('planning cause')
        errors = [LookupError('planning failed'), KeyboardInterrupt('worker interrupted')]
        for error in errors:
            with self.subTest(error=type(error).__name__):
                job = self.job()

                def compute():
                    raise error from cause

                job.start(compute)
                self.exited(job)
                with self.assertRaises(type(error)) as caught:
                    job.poll()
                self.assertIs(caught.exception, error)
                self.assertIs(caught.exception.__cause__, cause)
                self.assertEqual(job.state, 'failed')
                self.assertTrue(job.execution['joined'])
                with self.assertRaises(type(error)):
                    job.consume(self.binding())

    def test_invalid_and_nonfinite_worker_results_fail_without_admission(self):
        for result in (None, {'paths': []}, float('nan')):
            with self.subTest(result=repr(result)):
                job = self.job()
                job.start(lambda: result)
                self.exited(job)
                with self.assertRaisesRegex(TypeError, 'TransportPlan'):
                    job.poll()
                self.assertEqual(job.state, 'failed')
                with self.assertRaises(TypeError):
                    job.peek(self.binding())

    def test_reject_pending_then_late_valid_result_never_resurrects(self):
        entered, release = threading.Event(), threading.Event()
        job, expected = self.job(), self.plan()

        def compute():
            entered.set()
            if not release.wait(3.):
                raise TimeoutError('test worker was not released')
            return expected

        job.start(compute)
        try:
            self.assertTrue(entered.wait(3.))
            job.reject('epoch superseded')
            self.assertTrue(job.cancel_event.is_set())
            self.assertFalse(job.poll())
            self.assertEqual(job.state, 'rejected')
        finally:
            release.set()
            self.exited(job)
        with self.assertRaisesRegex(RuntimeError, 'epoch superseded'):
            job.poll()
        self.assertTrue(job.execution['joined'])
        self.assertEqual(job.state, 'rejected')
        self.assertIsNone(job._result)
        for binding in (self.binding(context=(('epoch', 2),)), self.binding()):
            with self.assertRaises(RuntimeError):
                job.consume(binding)

    def test_close_requests_cooperative_abort_and_joins_actual_worker(self):
        entered, cancelled, release, closed = (threading.Event() for _ in range(4))
        errors = []
        job = self.job()

        def compute():
            entered.set()
            if not job.cancel_event.wait(3.):
                raise TimeoutError('cancel was not requested')
            cancelled.set()
            if not release.wait(3.):
                raise TimeoutError('test worker was not released')
            return self.plan()

        def cleanup():
            try:
                job.close()
            except BaseException as error:
                errors.append(error)
            finally:
                closed.set()

        job.start(compute)
        self.assertTrue(entered.wait(3.))
        closer = threading.Thread(target=cleanup)
        closer.start()
        try:
            self.assertTrue(cancelled.wait(3.))
            self.assertFalse(closed.is_set(), 'close returned before worker exit')
        finally:
            release.set()
            closer.join(3.)
        self.assertFalse(closer.is_alive())
        self.assertEqual(errors, [])
        self.assertFalse(job._thread.is_alive())
        self.assertTrue(job.execution['joined'])
        self.assertTrue(job.execution['abort_requested'])
        self.assertEqual(job.execution['state_before_close'], 'running')
        self.assertEqual(job.state, 'rejected')
        self.assertGreaterEqual(job.execution['shutdown_wall_s'], 0.)
        with self.assertRaises(RuntimeError):
            job.consume(self.binding())

    def test_close_after_consumption_is_idempotent_and_preserves_state(self):
        job, expected = self.completed()
        self.assertIs(job.consume(self.binding()), expected)
        job.close()
        first = dict(job.execution)
        job.close()
        self.assertEqual(job.execution, first)
        self.assertEqual(job.state, 'consumed')
        self.assertEqual(first['state_before_close'], 'consumed')
        self.assertFalse(first['abort_requested'])
        with self.assertRaises(RuntimeError):
            job.peek(self.binding())

    def test_join_failures_do_not_claim_success_or_permit_consumption(self):
        job = self.job()
        job.start(self.plan)
        self.exited(job)
        failure = RuntimeError('join interrupted')
        with patch.object(job._thread, 'join', side_effect=failure):
            with self.assertRaises(RuntimeError) as caught:
                job.poll()
            self.assertIs(caught.exception, failure)
            self.assertEqual(job.state, 'failed')
            self.assertFalse(job.execution['joined'])
            with self.assertRaises(RuntimeError):
                job.consume(self.binding())
            with self.assertRaises(RuntimeError) as caught:
                job.close()
            self.assertIs(caught.exception, failure)
            self.assertFalse(job.execution['joined'])
        job.close()  # Retry resource cleanup only; state remains permanently failed.
        self.assertTrue(job.execution['joined'])
        self.assertEqual(job.state, 'failed')

    def test_thread_start_failure_is_preserved_and_never_retried(self):
        job = self.job()
        failure = RuntimeError('thread could not start')
        with patch('transport_worker.threading.Thread.start', side_effect=failure):
            with self.assertRaises(RuntimeError) as caught:
                job.start(self.plan)
        self.assertIs(caught.exception, failure)
        self.assertEqual(job.state, 'failed')
        self.assertFalse(job.execution['joined'])
        with self.assertRaises(RuntimeError):
            job.start(self.plan)
        try:
            with self.assertRaisesRegex(RuntimeError, 'before it is started'):
                job.close()
            self.assertFalse(job.execution['joined'])
            self.assertTrue(job.execution['launch_attempted'])
            self.assertTrue(job.execution['cleanup_unconfirmed'])
            self.assertTrue(job.execution['launch_unknown'])
            self.assertFalse(job.execution['owned_ack'])
            self.assertTrue(job.execution['abort_requested'])
            self.assertIs(job._error, failure)
            with patch.object(job._thread, 'join', wraps=job._thread.join) as joining:
                with self.assertRaisesRegex(RuntimeError, 'before it is started'):
                    job.close()
            joining.assert_called_once_with()  # Unconfirmed cleanup is retryable.
            with self.assertRaises(RuntimeError) as caught:
                job.consume(self.binding())
            self.assertIs(caught.exception, failure)
        finally:
            # This test's mock did not invoke Thread.start. Production retains
            # unknown launch status rather than inferring it from that return.
            self.jobs.remove(job)

    def test_real_started_thread_then_start_interrupt_is_cancelled_and_joined(self):
        entered, cancelled, release, closed = (threading.Event() for _ in range(4))
        errors = []
        job, expected = self.job(), self.plan()
        interrupt = KeyboardInterrupt('after actual OS-thread creation')
        original_start = threading.Thread.start

        def compute():
            entered.set()
            if not job.cancel_event.wait(3.):
                raise TimeoutError('startup abort was not requested')
            cancelled.set()
            if not release.wait(3.):
                raise TimeoutError('test worker was not released')
            return expected

        def interrupted_start(thread):
            original_start(thread)
            if not entered.wait(3.):
                raise TimeoutError('actual worker did not enter')
            raise interrupt

        with patch('transport_worker.threading.Thread.start', new=interrupted_start):
            with self.assertRaises(KeyboardInterrupt) as caught:
                job.start(compute)
        self.assertIs(caught.exception, interrupt)
        self.assertFalse(job._thread_started)
        self.assertTrue(job.execution['launch_attempted'])
        self.assertTrue(job.execution['owned_ack'])
        self.assertTrue(job._owned_ack.is_set())
        self.assertTrue(job.execution['cleanup_unconfirmed'])
        self.assertTrue(job.execution['abort_requested'])
        self.assertEqual(job.state, 'failed')
        self.assertTrue(cancelled.wait(3.))
        self.assertTrue(job._thread.is_alive())

        def cleanup():
            try:
                job.close()
            except BaseException as error:
                errors.append(error)
            finally:
                closed.set()

        closer = threading.Thread(target=cleanup)
        joining = threading.Event()
        original_join = job._thread.join

        def tracked_join(*args, **kwargs):
            joining.set()
            return original_join(*args, **kwargs)

        with patch.object(job._thread, 'join', new=tracked_join):
            closer.start()
            try:
                self.assertTrue(joining.wait(3.), 'close skipped the actual owned thread join')
                self.assertFalse(closed.is_set(), 'close returned while the worker was blocked')
            finally:
                release.set()
                closer.join(3.)
        self.assertFalse(closer.is_alive())
        self.assertEqual(errors, [])
        self.assertFalse(job._thread.is_alive())
        self.assertTrue(job.execution['joined'])
        self.assertFalse(job.execution['cleanup_unconfirmed'])
        self.assertFalse(job.execution['launch_unknown'])
        self.assertEqual(job.execution['state_before_close'], 'failed')
        self.assertEqual(job.state, 'failed')
        self.assertIsNone(job._result)
        self.assertIsNone(job._plan)
        for operation in (job.poll, lambda: job.peek(self.binding()),
                          lambda: job.consume(self.binding())):
            with self.assertRaises(KeyboardInterrupt) as caught:
                operation()
            self.assertIs(caught.exception, interrupt)

    def test_start_interrupt_primary_and_join_exception_cause_are_both_retained(self):
        entered = threading.Event()
        job = self.job()
        interrupt = KeyboardInterrupt('startup interrupted')
        cause = OSError('join underlying cause')
        join_error = RuntimeError('join interrupted')
        join_error.__cause__ = cause
        original_start = threading.Thread.start

        def compute():
            entered.set()
            if not job.cancel_event.wait(3.):
                raise TimeoutError('startup abort was not requested')
            return self.plan()

        def interrupted_start(thread):
            original_start(thread)
            if not entered.wait(3.):
                raise TimeoutError('actual worker did not enter')
            raise interrupt

        with patch('transport_worker.threading.Thread.start', new=interrupted_start):
            with self.assertRaises(KeyboardInterrupt):
                job.start(compute)
        self.exited(job)
        with patch.object(job._thread, 'join', side_effect=join_error):
            with self.assertRaises(RuntimeError) as caught:
                job.close()
            self.assertIs(caught.exception, join_error)
            self.assertIs(caught.exception.__cause__, cause)
            self.assertIs(job._error, interrupt)
            self.assertEqual(job.state, 'failed')
            self.assertFalse(job.execution['joined'])
            self.assertTrue(job.execution['cleanup_unconfirmed'])
            self.assertEqual(job.execution['startup_error_type'], 'KeyboardInterrupt')
            self.assertEqual(job.execution['cleanup_error_type'], 'RuntimeError')
        job.close()  # Retry join, not planning or proposal admission.
        self.assertTrue(job.execution['joined'])
        self.assertFalse(job.execution['cleanup_unconfirmed'])
        self.assertEqual(job.state, 'failed')
        with self.assertRaises(KeyboardInterrupt) as caught:
            job.consume(self.binding())
        self.assertIs(caught.exception, interrupt)

    def test_binding_validator_exception_permanently_fails_admission(self):
        failure = ValueError('binding validator failed')

        class BrokenBinding:
            def matches(self, other):
                raise failure

        job, _ = self.completed(self.job(BrokenBinding()))
        with self.assertRaises(ValueError) as caught:
            job.peek(self.binding())
        self.assertIs(caught.exception, failure)
        self.assertEqual(job.state, 'failed')
        self.assertTrue(job.execution['abort_requested'])
        with self.assertRaises(ValueError):
            job.consume(self.binding())

    def test_two_owned_jobs_have_independent_cancellation_and_results(self):
        first, second = self.job(), self.job()
        entered = threading.Event()

        def compute():
            entered.set()
            if not first.cancel_event.wait(3.):
                raise TimeoutError('first worker was not cancelled')
            return self.plan()

        first.start(compute)
        self.assertTrue(entered.wait(3.))
        second, expected = self.completed(second)
        first.reject('first epoch expired')
        self.exited(first)
        with self.assertRaisesRegex(RuntimeError, 'first epoch expired'):
            first.poll()
        self.assertFalse(second.cancel_event.is_set())
        self.assertIs(second.consume(self.binding()), expected)
        self.assertEqual(second.state, 'consumed')


if __name__ == '__main__':
    unittest.main(verbosity=2)
