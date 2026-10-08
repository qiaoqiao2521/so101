"""Transport worker ownership and lifecycle tests; no model, FK or physics."""

from dataclasses import FrozenInstanceError
import json
import math
import struct
import threading
import unittest
from unittest.mock import Mock, patch

import numpy as np

from configuration_sweep import SweepBinding
from transport_worker import TransportPlan, TransportPlanningJob, TransportSnapshot


class TransportWorkerTests(unittest.TestCase):
    def setUp(self):
        self.owner, self.checker, self.model = object(), object(), object()

    def binding(self, **changes):
        values = dict(owner=self.owner, checker=self.checker, model=self.model,
                      stage='hold', jaw_intent_rad=.015,
                      context=(('observation', (1, 3., (0.,)*6, (0.,)*6)),
                               ('request', 'transport')))
        values.update(changes)
        return SweepBinding(**values)

    def snapshot_values(self):
        return dict(q6=np.array([0., -.0, .1, -.1, .2, .015]),
                    target_xy=[.24, -.13], payload_relative=[0., 0., -.03],
                    payload_rotation=np.eye(3),
                    world=[['tray', 6, [.24, .14, 0.], np.eye(3), [.1, .1, .01]]],
                    payload_uncertainty=.002, elapsed_s=3.)

    def paths(self):
        return [[[float(index)*.01, 0., 0., 0., 0.],
                 [float(index+1)*.01, -.0, .01, 0., 0.]] for index in range(5)]

    def plan(self):
        paths = self.paths()
        return TransportPlan(paths, self.report(paths))

    def report(self, paths):
        return json.dumps({'stage': 'transport_execution_plan', 'planned_at_s': 3.,
                           'legs': [{'index': i, 'path': path} for i, path in enumerate(paths)]})

    def assert_joined(self, job, caller_id, worker):
        execution = job.execution
        self.assertEqual(execution['mode'], 'isolated_thread_frozen_simulation_wait')
        self.assertEqual(execution['main_thread_id'], caller_id)
        self.assertEqual(execution['worker_thread_id'], worker.ident)
        self.assertNotEqual(worker.ident, caller_id)
        self.assertTrue(execution['joined'])
        self.assertTrue(math.isfinite(execution['wait_wall_s']))
        self.assertGreaterEqual(execution['wait_wall_s'], 0.)
        self.assertFalse(worker.is_alive(), 'run returned before its worker joined')

    def test_snapshot_owns_nested_arrays_and_lists_and_is_frozen(self):
        values = self.snapshot_values()
        snapshot = TransportSnapshot(**values)
        q_bytes = np.asarray(snapshot.q6, dtype=np.float64).tobytes()
        before_world = snapshot.world
        values['q6'][:] = 9.
        values['target_xy'][0] = 9.
        values['payload_relative'][2] = 9.
        values['payload_rotation'][:] = 9.
        values['world'][0][2][0] = 9.
        values['world'][0][3][:] = 9.
        values['world'][0][4][0] = 9.
        self.assertEqual(np.asarray(snapshot.q6, dtype=np.float64).tobytes(), q_bytes)
        self.assertEqual(snapshot.target_xy, (.24, -.13))
        self.assertEqual(snapshot.payload_relative, (0., 0., -.03))
        self.assertEqual(snapshot.payload_rotation, ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.)))
        self.assertEqual(snapshot.world, before_world)
        self.assertIsInstance(snapshot.world, tuple)
        self.assertIsInstance(snapshot.world[0], tuple)
        self.assertIsInstance(snapshot.world[0][3][0], tuple)
        self.assertEqual(struct.pack('!d', snapshot.q6[1]), struct.pack('!d', -.0))
        with self.assertRaises(FrozenInstanceError):
            snapshot.elapsed_s = 4.
        with self.assertRaises(TypeError):
            snapshot.world[0][2][0] = 7.

    def test_snapshot_rejects_malformed_and_nonfinite_planning_inputs(self):
        replacements = [('q6', [0.]*5), ('q6', [0.]*7),
                        ('target_xy', [0.]), ('payload_relative', [0.]*2),
                        ('payload_rotation', [[1., 0.], [0., 1.]]),
                        ('q6', [0., 0., math.nan, 0., 0., .015]),
                        ('target_xy', [math.inf, 0.]),
                        ('payload_relative', [0., -math.inf, 0.]),
                        ('payload_rotation', [[1., 0., 0.], [0., math.nan, 0.], [0., 0., 1.]]),
                        ('world', [['tray', 6, [0., 0., math.inf], np.eye(3), [.1]*3]]),
                        ('payload_uncertainty', math.nan), ('payload_uncertainty', -.001),
                        ('elapsed_s', math.inf), ('elapsed_s', -1.)]
        for name, value in replacements:
            with self.subTest(name=name, value=repr(value)):
                values = self.snapshot_values()
                values[name] = value
                with self.assertRaises((ValueError, TypeError)):
                    TransportSnapshot(**values)

    def test_plan_owns_five_paths_with_signed_zero_and_json_report(self):
        paths = self.paths()
        report_json = self.report(paths)
        plan = TransportPlan(paths, report_json)
        expected = np.asarray(paths, dtype=np.float64).tobytes()
        paths[0][0][0] = 99.
        paths[1].append([9.]*5)
        self.assertEqual(np.asarray(plan.paths, dtype=np.float64).tobytes(), expected)
        self.assertEqual(len(plan.paths), 5)
        self.assertTrue(all(isinstance(path, tuple) and isinstance(path[0], tuple)
                            for path in plan.paths))
        self.assertEqual(struct.pack('!d', plan.paths[0][1][1]), struct.pack('!d', -.0))
        self.assertEqual(json.loads(plan.report_json), json.loads(report_json))
        with self.assertRaises(FrozenInstanceError):
            plan.paths = ()
        with self.assertRaises(TypeError):
            plan.paths[0][0][0] = 1.

    def test_plan_rejects_wrong_leg_count_shape_and_nonfinite_paths_or_reports(self):
        empty_leg = self.paths()
        empty_leg[2] = []
        bad_width = self.paths()
        bad_width[2][1] = [0.]*4
        nonfinite = self.paths()
        nonfinite[4][1][3] = math.inf
        for paths in ([], self.paths()[:4], self.paths()+[self.paths()[0]],
                      empty_leg, bad_width, nonfinite):
            with self.subTest(paths=repr(paths)), self.assertRaises((ValueError, TypeError)):
                TransportPlan(paths, '{}')
        different = self.paths()
        different[1][0][0] += .001
        for report in ('not json', '{"duration":NaN}', '{"duration":Infinity}',
                       '{"duration":1e999}', '{}', self.report(different)):
            with self.subTest(report=report), self.assertRaises((ValueError, TypeError)):
                TransportPlan(self.paths(), report)
        signed_zero_changed = self.paths()
        signed_zero_changed[0][1][1] = .0
        with self.assertRaises(ValueError):
            TransportPlan(self.paths(), self.report(signed_zero_changed))

    def test_success_runs_once_off_caller_thread_and_joins_before_consumption(self):
        binding = self.binding()
        job, expected, workers, seen = TransportPlanningJob(binding), self.plan(), [], []
        marker = object()

        def compute(argument):
            workers.append(threading.current_thread())
            seen.append(argument)
            return expected

        caller_id = threading.get_ident()
        self.assertEqual(job.state, 'new')
        job.run(compute, marker)
        self.assertEqual(seen, [marker])
        self.assertEqual(job.state, 'completed')
        self.assert_joined(job, caller_id, workers[0])
        result = job.consume(self.binding())
        self.assertIsInstance(result, TransportPlan)
        self.assertEqual(np.asarray(result.paths).tobytes(), np.asarray(expected.paths).tobytes())
        self.assertEqual(result.report_json, expected.report_json)
        self.assertEqual(job.state, 'consumed')

    def test_unexecuted_or_already_consumed_job_cannot_supply_a_plan(self):
        binding = self.binding()
        job = TransportPlanningJob(binding)
        with self.assertRaises(RuntimeError):
            job.consume(binding)
        completed = TransportPlanningJob(binding)
        completed.run(self.plan)
        completed.consume(binding)
        with self.assertRaises(RuntimeError):
            completed.consume(binding)

    def test_repeated_execution_is_rejected_without_repeating_callable(self):
        calls = []
        job = TransportPlanningJob(self.binding())

        def compute():
            calls.append(1)
            return self.plan()

        job.run(compute)
        with self.assertRaises(RuntimeError):
            job.run(compute)
        self.assertEqual(calls, [1])
        consumed = TransportPlanningJob(self.binding())
        consumed.run(compute)
        consumed.consume(self.binding())
        with self.assertRaises(RuntimeError):
            consumed.run(compute)
        self.assertEqual(calls, [1, 1])

    def test_wrong_binding_permanently_rejects_even_when_original_context_returns(self):
        changes = ({'owner': object()}, {'checker': object()}, {'model': object()},
                   {'stage': 'transport'}, {'jaw_intent_rad': .5},
                   {'context': (('observation', (2, 3., (0.,)*6, (0.,)*6)),)})
        for changed in changes:
            with self.subTest(changed=changed):
                original = self.binding()
                job = TransportPlanningJob(original)
                job.run(self.plan)
                with self.assertRaises(RuntimeError):
                    job.consume(self.binding(**changed))
                self.assertEqual(job.state, 'failed')
                with self.assertRaises(RuntimeError):
                    job.consume(original)
                with self.assertRaises(RuntimeError):
                    job.run(self.plan)

    def test_signed_zero_and_same_pose_new_velocity_or_sequence_are_not_equivalent(self):
        contexts = ((('value', -.0),), (('observation_seq', 2), ('qvel', (0.,)*6)),
                    (('observation_seq', 1), ('qvel', (0., 0., 0., 0., 0., .001))))
        originals = ((('value', .0),), (('observation_seq', 1), ('qvel', (0.,)*6)),
                     (('observation_seq', 1), ('qvel', (0.,)*6)))
        for original_context, changed_context in zip(originals, contexts):
            with self.subTest(original_context=original_context):
                binding = self.binding(context=original_context)
                job = TransportPlanningJob(binding)
                job.run(self.plan)
                with self.assertRaises(RuntimeError):
                    job.consume(self.binding(context=changed_context))
                self.assertEqual(job.state, 'failed')

    def test_event_blocked_worker_waits_then_rejects_changed_context(self):
        entered, release = threading.Event(), threading.Event()
        workers, caller_ids, errors = [], [], []
        original = self.binding()
        job = TransportPlanningJob(original)

        def compute():
            workers.append(threading.current_thread())
            entered.set()
            if not release.wait(3.):
                raise TimeoutError('test failed to release transport worker')
            return self.plan()

        def run():
            caller_ids.append(threading.get_ident())
            try:
                job.run(compute)
            except BaseException as error:
                errors.append(error)

        caller = threading.Thread(target=run, name='transport-test-caller')
        caller.start()
        try:
            self.assertTrue(entered.wait(3.), 'worker did not enter')
            self.assertTrue(caller.is_alive(), 'run returned during blocked planning')
            self.assertEqual(job.state, 'running')
            changed = self.binding(context=(('observation_seq', 2),))
        finally:
            release.set()
            caller.join(3.)
        self.assertFalse(caller.is_alive(), 'job did not join after event release')
        self.assertEqual(errors, [])
        self.assert_joined(job, caller_ids[0], workers[0])
        with self.assertRaises(RuntimeError):
            job.consume(changed)
        self.assertEqual(job.state, 'failed')
        with self.assertRaises(RuntimeError):
            job.consume(original)

    def test_worker_reads_owned_snapshot_despite_mutation_during_wait(self):
        values = self.snapshot_values()
        snapshot = TransportSnapshot(**values)
        original_q = np.asarray(snapshot.q6, dtype=np.float64).tobytes()
        entered, release = threading.Event(), threading.Event()
        seen, errors = [], []
        job = TransportPlanningJob(self.binding())

        def compute(argument):
            entered.set()
            if not release.wait(3.):
                raise TimeoutError('test failed to release snapshot worker')
            seen.append((np.asarray(argument.q6, dtype=np.float64).tobytes(),
                         argument.target_xy, argument.world[0][2]))
            return self.plan()

        def run():
            try:
                job.run(compute, snapshot)
            except BaseException as error:
                errors.append(error)

        caller = threading.Thread(target=run, name='snapshot-test-caller')
        caller.start()
        try:
            self.assertTrue(entered.wait(3.))
            values['q6'][:] = 99.
            values['target_xy'][0] = 99.
            values['world'][0][2][0] = 99.
        finally:
            release.set()
            caller.join(3.)
        self.assertFalse(caller.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(seen, [(original_q, (.24, -.13), (.24, .14, 0.))])
        self.assertIsInstance(job.consume(self.binding()), TransportPlan)

    def test_worker_exception_propagates_original_object_and_joins_without_retry(self):
        binding, failure = self.binding(), RuntimeError('transport solver failed')
        job, workers, calls = TransportPlanningJob(binding), [], []

        def compute():
            workers.append(threading.current_thread())
            calls.append(1)
            raise failure

        with self.assertRaises(RuntimeError) as caught:
            job.run(compute)
        self.assertIs(caught.exception, failure)
        self.assertEqual(job.state, 'failed')
        self.assert_joined(job, threading.get_ident(), workers[0])
        with self.assertRaises(RuntimeError):
            job.consume(binding)
        with self.assertRaises(RuntimeError):
            job.run(compute)
        self.assertEqual(calls, [1])

    def test_nonplan_worker_results_fail_closed_and_join(self):
        for result in (None, {'paths': self.paths()}, self.paths(), False):
            with self.subTest(result=type(result).__name__):
                binding, workers = self.binding(), []
                job = TransportPlanningJob(binding)

                def compute():
                    workers.append(threading.current_thread())
                    return result

                with self.assertRaises((RuntimeError, TypeError, ValueError)):
                    job.run(compute)
                self.assertEqual(job.state, 'failed')
                self.assert_joined(job, threading.get_ident(), workers[0])
                with self.assertRaises(RuntimeError):
                    job.consume(binding)
                with self.assertRaises(RuntimeError):
                    job.run(compute)

    def test_nonfinite_plan_built_inside_worker_joins_and_cannot_be_consumed(self):
        binding, workers = self.binding(), []
        job = TransportPlanningJob(binding)

        def compute():
            workers.append(threading.current_thread())
            paths = self.paths()
            paths[2][1][0] = math.nan
            return TransportPlan(paths, self.report(paths))

        with self.assertRaises(ValueError):
            job.run(compute)
        self.assertEqual(job.state, 'failed')
        self.assert_joined(job, threading.get_ident(), workers[0])
        with self.assertRaises(RuntimeError):
            job.consume(binding)
        with self.assertRaises(RuntimeError):
            job.run(compute)
        self.assertEqual(len(workers), 1)

    def test_shutdown_failure_rejects_valid_plan_and_does_not_claim_joined(self):
        binding = self.binding()
        job = TransportPlanningJob(binding)
        failure = RuntimeError('transport executor shutdown interrupted')
        pool = Mock()
        pool.submit.return_value.result.return_value = self.plan()
        pool.shutdown.side_effect = failure
        with patch('transport_worker.ThreadPoolExecutor', return_value=pool), \
                self.assertRaises(RuntimeError) as caught:
            job.run(self.plan)
        self.assertIs(caught.exception, failure)
        pool.submit.assert_called_once()
        pool.submit.return_value.result.assert_called_once_with()
        pool.shutdown.assert_called_once_with(wait=True)
        self.assertEqual(job.state, 'failed')
        self.assertFalse(job.execution['joined'])
        self.assertTrue(math.isfinite(job.execution['wait_wall_s']))
        with self.assertRaises(RuntimeError):
            job.consume(binding)
        with self.assertRaises(RuntimeError):
            job.run(self.plan)

    def test_controller_rejects_stale_or_failed_worker_without_partial_transport_commit(self):
        # Every controller dependency is fake. The real job still spawns/joins
        # its thread, but neither real FK nor the native planner is invoked.
        import visual_grasp_controller as module
        from test_visual_grasp_controller import VisualControllerTests

        for fault in ('context_change', 'solver_exception'):
            with self.subTest(fault=fault):
                controller = VisualControllerTests.controller(self)
                controller.stage = 'hold'
                controller.last_elapsed = 3.
                controller.payload_relative = np.zeros(3)
                controller.payload_rotation = np.eye(3)
                previous_paths = [np.full((2, 5), .7)]
                controller.transport = previous_paths
                controller.transport_index = 3
                previous_reports = list(controller.plan_reports)
                q6 = np.r_[controller.lift, .015]
                failure = RuntimeError('private transport worker failed')
                actual_job, jobs = module.TransportPlanningJob, []

                def create(binding):
                    job = actual_job(binding)
                    jobs.append(job)
                    return job

                def compute(rig, snapshot):
                    self.assertIsNot(rig, controller.rig)
                    self.assertIsInstance(snapshot, TransportSnapshot)
                    if fault == 'solver_exception':
                        raise failure
                    # Fault injection models context changing before admission.
                    controller.observation_seq += 1
                    return self.plan()

                with patch.object(module, '_run_transport_plan', side_effect=compute) as worker, \
                        patch.object(module, 'TransportPlanningJob', side_effect=create), \
                        self.assertRaises(RuntimeError) as caught:
                    controller._plan_transport(q6)
                if fault == 'solver_exception':
                    self.assertIs(caught.exception, failure)
                self.assertEqual(worker.call_count, 1)
                self.assertEqual(len(jobs), 1)
                self.assertEqual(jobs[0].state, 'failed')
                self.assertTrue(jobs[0].execution['joined'])
                self.assertIs(controller.transport, previous_paths)
                self.assertEqual(controller.transport_index, 3)
                self.assertEqual(controller.plan_reports, previous_reports)
                self.assertEqual(controller.stage, 'hold')


if __name__ == '__main__':
    unittest.main()
