"""CPU-only return ownership and measured-pose admission regressions.

The controller bindings and original samplers use analytical geometry fixtures.
No MuJoCo data, FK, native checker, integration or rendering is created. These
tests establish admission/lifecycle behavior, not physical task success or 50Hz.
"""
from dataclasses import FrozenInstanceError
import json
import math
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

import return_worker
from return_worker import AsyncReturnPlanningJob, ReturnPlan, run_return_plan
from route_policy import RoutePolicy
from separation_worker import SeparationSnapshot
import test_separation_admission as admission_fixture
import visual_grasp_controller as module


class ReturnPlanTests(unittest.TestCase):
    def snapshot(self):
        return SeparationSnapshot(
            q6=[.2, -.0, .1, .01, 0., .5],
            initial_q6=[.1, -.1, .06, .01, 0., .5],
            last_command6=[.201, -.0, .1, .01, 0., .5], seed=3,
            elapsed=70., center=[.24, .14, .01], uncertainty=.002)

    def plan(self, **changes):
        snapshot = self.snapshot()
        values = dict(path=[list(snapshot.q6[:5]), [.17, -.05, .08, .01, 0.],
                            list(snapshot.initial_q6[:5])],
                      method='validated_ompl_shortcuts', report_json='[]',
                      snapshot=snapshot)
        values.update(changes)
        return ReturnPlan(**values)

    def test_plan_owns_all_waypoints_and_is_immutable(self):
        snapshot = self.snapshot()
        rows = [list(snapshot.q6[:5]), [.17, -.05, .08, .01, 0.],
                list(snapshot.initial_q6[:5])]
        expected = np.asarray(rows).tobytes()
        plan = self.plan(path=rows, snapshot=snapshot)
        rows[0][0] += 1.
        rows[1][:] = [99.] * 5
        rows.pop()
        self.assertEqual(np.asarray(plan.path).tobytes(), expected)
        self.assertTrue(all(isinstance(row, tuple) for row in plan.path))
        self.assertEqual(np.asarray(plan.path).view(np.uint64)[0, 1], 1 << 63)
        with self.assertRaises(FrozenInstanceError):
            plan.method = 'validated_direct'

    def test_endpoints_must_exactly_match_measured_snapshot_and_home(self):
        snapshot = self.snapshot()
        for endpoint, axis in ((0, 0), (-1, 0), (0, 1)):
            with self.subTest(endpoint=endpoint, axis=axis):
                rows = [list(snapshot.q6[:5]), list(snapshot.initial_q6[:5])]
                if axis == 1:
                    rows[endpoint][axis] = .0  # Signed zero is part of the pose.
                else:
                    rows[endpoint][axis] = np.nextafter(rows[endpoint][axis], math.inf)
                with self.assertRaisesRegex(ValueError, 'endpoints'):
                    self.plan(path=rows, snapshot=snapshot)

    def test_malformed_nonfinite_or_incomplete_proposals_are_rejected(self):
        snapshot = self.snapshot()
        valid = [list(snapshot.q6[:5]), list(snapshot.initial_q6[:5])]
        for rows in ([], valid[:1], [[0.] * 4, valid[-1]],
                     [valid[0], [math.nan] * 5, valid[-1]],
                     [valid[0], [math.inf] * 5, valid[-1]]):
            with self.subTest(path=rows), self.assertRaises((TypeError, ValueError)):
                self.plan(path=rows)
        for changes in ({'snapshot': object()}, {'method': 'unchecked_direct'},
                        {'report_json': '{}'}, {'report_json': '[NaN]'},
                        {'report_json': '[Infinity]'}, {'report_json': '[1e999]'}):
            with self.subTest(changes=changes), self.assertRaises((TypeError, ValueError)):
                self.plan(**changes)


class ReturnLifecycleTests(unittest.TestCase):
    def binding(self):
        return SimpleNamespace(matches=lambda other: other is self.binding_value)

    def setUp(self):
        self.binding_value = self.binding()

    def wait_ready(self, job):
        deadline = time.monotonic() + 2.
        while not job.poll():
            if time.monotonic() >= deadline:
                self.fail('CPU worker did not reach a terminal state within 2 seconds')
            threading.Event().wait(.001)

    def test_owned_thread_result_is_joined_and_consumable_only_once(self):
        expected = ReturnPlanTests().plan()
        job = AsyncReturnPlanningJob(self.binding_value)
        self.addCleanup(job.close)
        calls = []

        def worker():
            calls.append(threading.get_ident())
            return expected

        job.start(worker)
        self.wait_ready(job)
        self.assertNotEqual(calls, [threading.get_ident()])
        self.assertEqual(len(calls), 1)
        self.assertTrue(job.execution['owned_ack'])
        self.assertTrue(job.execution['joined'])
        self.assertFalse(job.execution['launch_unknown'])
        self.assertFalse(job.execution['cleanup_unconfirmed'])
        self.assertEqual(job.execution['mode'], 'isolated_thread_physics_advancing_return_hold')
        self.assertIs(job.peek(self.binding_value), expected)
        self.assertIs(job.consume(self.binding_value), expected)
        self.assertEqual(job.state, 'consumed')
        with self.assertRaises(RuntimeError):
            job.consume(self.binding_value)
        with self.assertRaises(RuntimeError):
            job.start(worker)
        self.assertEqual(len(calls), 1)

    def test_reject_cancels_worker_and_late_valid_result_cannot_revive(self):
        expected = ReturnPlanTests().plan()
        job = AsyncReturnPlanningJob(self.binding_value)
        self.addCleanup(job.close)
        entered, cancellation_seen = threading.Event(), threading.Event()

        def worker():
            entered.set()
            if not job.cancel_event.wait(2.):
                raise RuntimeError('Test worker did not receive cancellation')
            cancellation_seen.set()
            return expected

        job.start(worker)
        self.assertTrue(entered.wait(2.))
        self.assertFalse(job.poll())
        job.reject('return context was replaced')
        job.close()
        self.assertTrue(cancellation_seen.is_set())
        self.assertTrue(job.execution['abort_requested'])
        self.assertTrue(job.execution['joined'])
        self.assertFalse(job._thread.is_alive())
        self.assertEqual(job.state, 'rejected')
        with self.assertRaises(RuntimeError):
            job.consume(self.binding_value)

    def test_worker_runs_original_direct_return_and_always_closes_owned_native(self):
        snapshot = ReturnPlanTests().snapshot()
        native = SimpleNamespace(close=Mock())
        visited = []
        context = SimpleNamespace(
            checker=SimpleNamespace(native=native), initial_q=np.asarray(snapshot.initial_q6),
            _released_valid=lambda q, jaw=.5: visited.append(tuple(q)) or True,
            plan_reports=[])
        with patch.object(return_worker, '_planning_context', return_value=context):
            result = run_return_plan(object(), object(), snapshot)
        self.assertEqual(result.method, 'validated_direct')
        self.assertEqual(result.path, (snapshot.q6[:5], snapshot.initial_q6[:5]))
        self.assertGreater(len(visited), 2)  # Original 5mrad path sampling ran.
        native.close.assert_called_once_with()

        native.close.reset_mock()
        cancellation = threading.Event()

        def cancel_during_query(q, jaw=.5):
            cancellation.set()
            return True

        context._released_valid = cancel_during_query
        with patch.object(return_worker, '_planning_context', return_value=context), \
                self.assertRaisesRegex(RuntimeError, 'return_planning_cancelled'):
            run_return_plan(object(), object(), snapshot, cancellation)
        native.close.assert_called_once_with()


class ReturnAdmissionTests(unittest.TestCase):
    def setUp(self):
        # Reuse only the fixture factory/guards, not its unrelated test cases.
        admission_fixture.SeparationAdmissionTests.setUp(self)

    def controller(self):
        c = admission_fixture.SeparationAdmissionTests.controller(self)
        c.stage, c.stage_started, c.duration = 'separate', 60., 2.
        c.reference[2] += .04
        c.last_command = c.reference.copy()
        c.last_command[0] += .001
        c.points = np.array([c.reference[:5], c.reference[:5]])
        c.route_policy = RoutePolicy(async_measured_return=True)
        c.place_xy, c.place_height_m = np.array([.24, .14]), 0.
        c.released_query.rotation = np.eye(3)
        c.released_query.distance_predicate = lambda q: {
            'arm_guard': .01, 'pad_gripper': .01, 'pad_moving_jaw': .01}
        c.return_job, c.return_request_binding, c.return_events = None, None, []
        return c

    def proposal(self, c):
        snapshot = SeparationSnapshot(
            c.reference, c.initial_q, c.last_command, c.seed, 62.6,
            c.released_query.center, c.released_query.uncertainty_m,
            rotation=c.released_query.rotation, route_policy=c.route_policy)
        middle = np.asarray(snapshot.q6[:5]) + [-.02, .02, .01, .005, -.01]
        return ReturnPlan([snapshot.q6[:5], middle, snapshot.initial_q6[:5]],
                          'validated_ompl_shortcuts',
                          json.dumps([{'stage': 'owned_return_search'}]), snapshot)

    def attach(self, c, *, ready=True):
        proposal = self.proposal(c)
        binding = c._separation_binding()
        c.return_job = admission_fixture.ProposalSource(binding, proposal, c.trace, ready=ready)
        c.return_request_binding = binding
        c.trace.clear()
        return c.return_job, proposal

    def poll(self, c, q6=None, elapsed=62.62):
        q6 = c.reference.copy() if q6 is None else np.asarray(q6).copy()
        c.last_elapsed = elapsed
        c.observation_seq += 1
        c.observation = (c.observation_seq, elapsed, tuple(q6), (0.,) * 6)
        return c._poll_return(q6, elapsed)

    def test_unready_proposal_does_not_change_stage_command_or_query_geometry(self):
        c = self.controller()
        job, _ = self.attach(c, ready=False)
        points, command = c.points.copy(), c.last_command.copy()
        self.assertFalse(self.poll(c))
        self.assertEqual(c.stage, 'separate')
        self.assertEqual(job.consume_count, 0)
        np.testing.assert_array_equal(c.points, points)
        np.testing.assert_array_equal(c.last_command, command)
        self.assertEqual(c.trace, [('poll',)])
        self.assertEqual(c.return_events, [])

    def test_internal_bridge_collision_is_rejected_even_with_safe_endpoints(self):
        for collision in ('arm', 'released_object'):
            with self.subTest(collision=collision):
                c = self.controller()
                job, proposal = self.attach(c)
                q = c.reference.copy()
                q[0] += .018
                middle_x = (q[0] + proposal.path[0][0]) / 2
                blocked = lambda pose: abs(pose[0] - middle_x) < .0001
                if collision == 'arm':
                    c.arm_predicate = lambda pose: not blocked(pose)
                else:
                    c.released_query.distance_predicate = lambda pose: {
                        'arm_guard': .01, 'pad_gripper': .000999 if blocked(pose) else .01,
                        'pad_moving_jaw': .01}
                self.assertFalse(blocked(q))
                self.assertFalse(blocked(proposal.path[0]))
                with self.assertRaisesRegex(module.ControllerFailure, 'return_admission_chord_invalid'):
                    self.poll(c, q)
                event = c.return_events[-1]
                self.assertFalse(event['released_validation']['valid'])
                self.assertGreater(event['released_validation']['checked_states'], 1)
                self.assertEqual(event['configuration_sweep']['valid'], collision != 'arm')
                self.assertEqual(job.consume_count, 0)
                self.assertEqual(c.stage, 'separate')
                self.assertFalse(event['accepted'])
                self.assertEqual(c.plan_reports, [])

    def test_release_context_change_is_rejected_before_poll(self):
        for change in ('center', 'rotation', 'model_owner', 'release_record'):
            with self.subTest(change=change):
                c = self.controller()
                job, _ = self.attach(c)
                if change == 'center':
                    c.released_query.center[0] += .001
                elif change == 'rotation':
                    c.released_query.rotation = np.diag([-1., -1., 1.])
                elif change == 'model_owner':
                    c.released_query.model = object()
                else:
                    c.release_record['uncertainty_m'] = .003
                with self.assertRaisesRegex(module.ControllerFailure, 'return_context_changed'):
                    self.poll(c)
                self.assertEqual(job.poll_count, 0)
                self.assertEqual(job.consume_count, 0)
                self.assertEqual(job.rejections, ['return_context_changed'])
                self.assertEqual(c.stage, 'separate')

    def test_context_mutated_during_admission_cannot_consume_result(self):
        c = self.controller()
        job, _ = self.attach(c)
        changed = False

        def distance(pose):
            nonlocal changed
            if not changed:
                changed = True
                c.release_record['uncertainty_m'] = .003
            return {'arm_guard': .01, 'pad_gripper': .01, 'pad_moving_jaw': .01}

        c.released_query.distance_predicate = distance
        with self.assertRaisesRegex(module.ControllerFailure, 'return_context_changed'):
            self.poll(c)
        self.assertTrue(changed)
        self.assertEqual(job.consume_count, 0)
        self.assertEqual(c.stage, 'separate')

    def test_observation_mutated_during_admission_cannot_consume_result(self):
        c = self.controller()
        job, _ = self.attach(c)
        changed = False

        def distance(pose):
            nonlocal changed
            if not changed:
                changed = True
                seq, elapsed, q, velocity = c.observation
                c.observation = (seq + 1, elapsed, q, velocity)
            return {'arm_guard': .01, 'pad_gripper': .01, 'pad_moving_jaw': .01}

        c.released_query.distance_predicate = distance
        with self.assertRaisesRegex(module.ControllerFailure, 'return_admission_observation_changed'):
            self.poll(c)
        self.assertTrue(changed)
        self.assertEqual(job.consume_count, 0)
        self.assertEqual(c.stage, 'separate')

    def test_original_90_second_budget_is_kept_at_its_boundary(self):
        for beyond in (False, True):
            with self.subTest(beyond=beyond):
                c = self.controller()
                job, proposal = self.attach(c)
                q = c.reference.copy()
                points = np.vstack((q[:5], proposal.path))
                required = module.motion_duration(points) + .6 + 1.5 + .6 + .1
                elapsed = 90. - required
                if beyond:
                    elapsed = np.nextafter(elapsed, math.inf)
                    self.assertGreater(elapsed + required, 90.)
                    with self.assertRaisesRegex(module.ControllerFailure, 'insufficient_time_for_safe_return'):
                        self.poll(c, q, elapsed)
                    self.assertEqual(job.consume_count, 0)
                    self.assertEqual(c.stage, 'separate')
                    self.assertFalse(c.return_events[-1]['accepted'])
                else:
                    self.assertEqual(elapsed + required, 90.)
                    self.assertTrue(self.poll(c, q, elapsed))
                    self.assertEqual(job.consume_count, 1)

    def test_acceptance_retains_all_waypoints_starts_measured_and_keeps_first_command(self):
        c = self.controller()
        job, proposal = self.attach(c)
        q = c.reference.copy()
        q[0] += .0005
        previous_command = c.last_command.copy()
        expected = np.vstack((q[:5], proposal.path))
        self.assertTrue(self.poll(c, q))
        self.assertEqual(c.stage, 'retreat')
        self.assertEqual(job.consume_count, 1)
        np.testing.assert_array_equal(c.points, expected)
        np.testing.assert_array_equal(c.points[0], q[:5])
        np.testing.assert_array_equal(c.points[1:], proposal.path)
        np.testing.assert_array_equal(c.last_command, previous_command)
        np.testing.assert_array_equal(c.servo_start_command, previous_command)
        np.testing.assert_array_equal(c.servo_offset, previous_command[:5] - q[:5])
        event = c.return_events[-1]
        self.assertTrue(event['accepted'])
        self.assertFalse(event['issued'])  # update(), not admission, issues a command.
        self.assertTrue(event['first_command_guard']['continuous'])
        np.testing.assert_array_equal(event['first_command_guard']['reference_q6'], q)
        np.testing.assert_array_equal(event['first_command_guard']['actuator_command'], previous_command)
        self.assertEqual(c.plan_reports[0], {'stage': 'owned_return_search'})
        self.assertEqual(c.plan_reports[-1]['execution'], 'async_measured_return')
        np.testing.assert_array_equal(c.plan_reports[-1]['path'], expected)
        self.assertEqual(c.plan_reports[-1]['snapshot_elapsed_s'], proposal.snapshot.elapsed)

    def test_original_update_issues_previous_command_on_first_return_tick(self):
        c = self.controller()
        c._initialize_separation(c.reference)
        c.separation_live_ready = True
        c.servo_offset = c.last_command[:5] - c.reference[:5]
        c.servo_start_command = c.last_command.copy()
        job, proposal = self.attach(c)
        measured = c.reference.copy()
        measured[0] += .0005
        previous_command = c.last_command.copy()
        result = c.update(measured, np.zeros(6), 62.62)
        self.assertIsNone(result['failure_reason'])
        self.assertEqual(result['status'], 'running')
        self.assertEqual(result['stage'], 'retreat')
        self.assertEqual(job.consume_count, 1)
        np.testing.assert_array_equal(result['command'], previous_command)
        np.testing.assert_array_equal(result['geometric_reference'], measured)
        np.testing.assert_array_equal(c.points, np.vstack((measured[:5], proposal.path)))

    def test_cleanup_attempts_third_worker_and_keeps_first_join_error(self):
        c = self.controller()
        calls = []
        primary = RuntimeError('transport join failure')
        failures = {'transport': primary, 'return': RuntimeError('return join failure')}

        def close(name):
            calls.append(name)
            if name in failures:
                raise failures[name]

        for name in ('transport', 'separation', 'return'):
            setattr(c, name + '_job', SimpleNamespace(close=lambda name=name: close(name)))
        prepared = object()
        c._prepared_worker_models = prepared
        with self.assertRaises(RuntimeError) as observed:
            c.close()
        self.assertIs(observed.exception, primary)
        self.assertEqual(calls, ['transport', 'separation', 'return'])
        self.assertEqual([row['planner'] for row in c.planner_cleanup_errors], ['transport', 'return'])
        self.assertIs(c._prepared_worker_models, prepared)

        failures.clear()
        calls.clear()
        c.close()
        self.assertEqual(calls, ['transport', 'separation', 'return'])
        self.assertEqual(c.planner_cleanup_errors, [])
        self.assertIsNone(c._prepared_worker_models)


if __name__ == '__main__':
    unittest.main()
