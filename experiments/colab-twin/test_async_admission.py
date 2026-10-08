"""Controller admission tests with real samplers and CPU-only geometry stubs.

The worker lifecycle has separate Event-controlled tests. Here a controllable
proposal source isolates the controller's guards, commit and waiting behavior.
No MuJoCo data, FK, native geometry, integration or renderer is constructed.
"""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

import visual_grasp_controller as module
from transport_worker import TransportPlan


class ProposalSource:
    """Pollable fixture: availability never bypasses binding or once-consume."""

    def __init__(self, binding, proposal, trace, *, ready=False, error=None):
        self.binding, self.proposal, self.trace = binding, proposal, trace
        self.ready, self.error = ready, error
        self.state = 'running'
        self.poll_count = self.consume_count = 0
        self.rejections = []
        self.execution = {'mode': 'cpu_stub', 'joined': True}

    def poll(self):
        self.poll_count += 1
        self.trace.append(('poll',))
        if self.state in ('rejected', 'failed', 'consumed'):
            raise RuntimeError('proposal permanently unavailable')
        if self.error is not None:
            self.state = 'failed'
            raise self.error
        if self.ready:
            self.state = 'completed'
        return self.ready

    def peek(self, binding):
        if self.state != 'completed' or not self.binding.matches(binding):
            raise RuntimeError('proposal unavailable or context changed')
        return self.proposal

    def consume(self, binding):
        plan = self.peek(binding)
        self.trace.append(('consume',))
        self.consume_count += 1
        self.state = 'consumed'
        return plan

    def reject(self, reason):
        self.rejections.append(str(reason))
        if self.state not in ('failed', 'consumed', 'rejected'):
            self.state = 'rejected'


class AsyncAdmissionTests(unittest.TestCase):
    def setUp(self):
        def forbidden(*args, **kwargs):
            raise AssertionError('CPU admission tests must not query real geometry')

        for name in ('MjData', 'mj_forward', 'mj_kinematics', 'mj_step'):
            guard = patch.object(module.mujoco, name, side_effect=forbidden)
            guard.start()
            self.addCleanup(guard.stop)
        guard = patch.object(module, 'CollisionChecker', side_effect=forbidden)
        guard.start()
        self.addCleanup(guard.stop)

    def controller(self):
        c = module.VisualGraspController.__new__(module.VisualGraspController)
        c.rig = SimpleNamespace(jnt_range=np.tile([-3., 3.], (6, 1)),
                                actuator_ctrlrange=np.tile([-3., 3.], (6, 1)))
        c.trace = []
        c.arm_predicate = lambda q: True
        c.payload_predicate = lambda q: True

        def evaluate(q, *, require_fixed_gripper=True):
            self.assertFalse(require_fixed_gripper)
            q = np.asarray(q, dtype=float).copy()
            c.trace.append(('arm', tuple(q)))
            return {'valid': bool(c.arm_predicate(q))}

        def payload(q):
            q = np.asarray(q, dtype=float).copy()
            c.trace.append(('payload', tuple(q)))
            return bool(c.payload_predicate(q))

        c.checker = SimpleNamespace(evaluate=evaluate)
        c._payload_valid = payload
        c._fk = lambda q: (_ for _ in ()).throw(AssertionError('unexpected FK'))
        c.stage, c.stage_started, c.duration, c.jaw = 'hold', 10., 1.5, .015
        arm = np.array([.2, -.1, .06, .01, 0.])
        c.points = np.array([arm, arm])
        c.reference = np.r_[arm, .015]
        c.last_command = c.reference.copy()
        c.initial_q = np.r_[arm, .5]
        c.last_elapsed = 12.
        c.observation_seq = 7
        c.observation = (7, 12., tuple(np.r_[arm, .116]), (0.,)*6)
        c.sweep_request_seq = 0
        c.transport_request_seq = 1
        c.target_xy = np.array([.24, -.13])
        c.target_timestamp, c.target_frozen, c.estimate_ttl = 0., True, 1.
        c.payload_relative, c.payload_rotation = np.zeros(3), np.eye(3)
        c.payload_uncertainty = .002
        c.world = [('floor', 6, np.zeros(3), np.eye(3), np.ones(3))]
        c.released_query = SimpleNamespace(model=object(), center=None, uncertainty_m=.002)
        c.seed, c.replans = 3, 0
        c.servo_offset = np.zeros(5)
        c.servo_transitions = []
        c.transport, c.transport_index = [], 0
        c.transport_job, c.transport_request_binding = None, None
        c.transport_events = []
        c.transport_wait = {'started_at_s': 12., 'pending_updates': 0,
                            'snapshot_q6': list(c.reference),
                            'hold_target_q6': list(c.reference)}
        c.plan_reports, c.sweep_reports = [], []
        c.failure_reason, c.done = None, False
        return c

    def proposal(self, c, *, start=None):
        q = c.points[-1].copy() if start is None else np.asarray(start).copy()
        paths = []
        for _ in range(5):
            mid, end = q.copy(), q.copy()
            mid[0] += .01
            end[0] += .02
            paths.append(np.array([q, mid, end]))
            q = end.copy()
        report = {'stage': 'transport_execution_plan', 'planned_at_s': 12.,
                  'legs': [{'index': i, 'path': p.tolist()} for i, p in enumerate(paths)]}
        return TransportPlan(paths, json.dumps(report, allow_nan=False))

    def attach(self, c, *, ready=False, start=None, error=None):
        binding = c._async_transport_binding()
        job = ProposalSource(binding, self.proposal(c, start=start), c.trace,
                             ready=ready, error=error)
        c.transport_request_binding = binding
        c.transport_job = job
        return job

    def measured(self, c, *, displacement=.001, jaw=.116):
        q = c.reference.copy()
        q[0] += displacement
        q[5] = jaw
        return q

    def arm_rows(self, c):
        return np.asarray([row[1] for row in c.trace if row[0] == 'arm'])

    def payload_rows(self, c):
        return np.asarray([row[1] for row in c.trace if row[0] == 'payload'])

    def test_new_observation_time_velocity_and_sweep_sequence_keep_plan_binding(self):
        c = self.controller()
        original = c._async_transport_binding()
        c.last_elapsed = 12.4
        c.observation_seq += 1
        c.observation = (c.observation_seq, 12.4, tuple(self.measured(c)), (.01,)*6)
        c.sweep_request_seq += 4
        c.last_command = self.measured(c)
        self.assertTrue(original.matches(c._async_transport_binding()))

    def test_semantic_changes_reject_including_owned_context_and_release_state(self):
        changes = {
            'stage': lambda c: setattr(c, 'stage', 'transport'),
            'jaw': lambda c: setattr(c, 'jaw', .5),
            'request': lambda c: setattr(c, 'transport_request_seq', 2),
            'hold_start': lambda c: setattr(c, 'stage_started', 10.1),
            'hold_duration': lambda c: setattr(c, 'duration', 2.),
            'hold_points': lambda c: c.points.__setitem__((1, 0), .201),
            'target': lambda c: c.target_xy.__setitem__(0, .241),
            'target_time': lambda c: setattr(c, 'target_timestamp', .1),
            'target_frozen': lambda c: setattr(c, 'target_frozen', False),
            'payload_center': lambda c: c.payload_relative.__setitem__(0, .001),
            'payload_rotation': lambda c: c.payload_rotation.__setitem__((0, 0), .999),
            'payload_uncertainty': lambda c: setattr(c, 'payload_uncertainty', .003),
            'world_center': lambda c: c.world[0][2].__setitem__(0, .001),
            'world_rotation': lambda c: c.world[0][3].__setitem__((0, 0), .999),
            'world_size': lambda c: c.world[0][4].__setitem__(0, 1.001),
            'seed': lambda c: setattr(c, 'seed', 4),
            'servo_offset': lambda c: c.servo_offset.__setitem__(0, .001),
            'checker_owner': lambda c: setattr(c, 'checker', object()),
            'model_owner': lambda c: setattr(c, 'rig', object()),
            'release_owner': lambda c: setattr(c, 'released_query', None),
            'release_model': lambda c: setattr(c.released_query, 'model', object()),
            'release_center': lambda c: setattr(c.released_query, 'center', np.zeros(3)),
            'release_uncertainty': lambda c: setattr(c.released_query, 'uncertainty_m', .003),
        }
        for name, change in changes.items():
            with self.subTest(change=name):
                c = self.controller()
                job = self.attach(c, ready=True)
                original = c.transport_request_binding
                change(c)
                self.assertFalse(original.matches(c._async_transport_binding()))
                with self.assertRaisesRegex(module.ControllerFailure, 'transport_context_changed'):
                    c._check_transport_context()
                self.assertEqual(job.state, 'rejected')
                self.assertEqual(job.consume_count, 0)

    def test_signed_zero_context_rejection_cannot_revive_after_original_bits_return(self):
        c = self.controller()
        job = self.attach(c, ready=True)
        c.world[0][2][0] = -.0
        with self.assertRaisesRegex(module.ControllerFailure, 'transport_context_changed'):
            c._poll_transport(self.measured(c), 12.2)
        c.world[0][2][0] = .0
        self.assertTrue(job.binding.matches(c._async_transport_binding()))
        with self.assertRaisesRegex(RuntimeError, 'permanently unavailable'):
            c._poll_transport(self.measured(c), 12.3)
        self.assertEqual(c.trace, [('poll',)])
        self.assertEqual(c.plan_reports, [])

    def test_admission_checks_complete_244_current_jaw_and_payload_bridge(self):
        c = self.controller()
        job = self.attach(c, ready=True)
        q = self.measured(c, displacement=.012, jaw=.5)
        self.assertTrue(c._poll_transport(q, 12.2))
        # The first sweep is the mixed bridge. A separate pure-jaw guard must
        # also protect the actual first command before the result is consumed.
        first_payload = next(i for i, row in enumerate(c.trace) if row[0] == 'payload')
        rows = np.asarray([row[1] for row in c.trace[:first_payload] if row[0] == 'arm'])
        self.assertEqual(len(rows), 244)
        self.assertEqual(rows[0].tobytes(), q.tobytes())
        self.assertEqual(rows[-1].tobytes(), np.r_[job.proposal.paths[0][0], .015].tobytes())
        self.assertLessEqual(np.linalg.norm(np.diff(rows[:, :5], axis=0), axis=1).max(), .005)
        self.assertLessEqual(np.abs(np.diff(rows[:, 5])).max(), .002)
        payload = self.payload_rows(c)[:4]
        self.assertEqual(payload[0].tobytes(), q[:5].tobytes())
        self.assertEqual(payload[-1].tobytes(), np.asarray(job.proposal.paths[0][0]).tobytes())
        self.assertEqual(len(payload), 4)
        self.assertLessEqual(np.linalg.norm(np.diff(payload, axis=0), axis=1).max(), .005)
        report = c.transport_events[-1]
        self.assertEqual(report['configuration_sweep']['checked_states'], 244)
        self.assertEqual(report['payload_validation']['resolution_rad'], .005)
        self.assertEqual(report['first_command_guard']['configuration_sweep']['checked_states'], 244)
        self.assertEqual(report['first_command_guard']['end_q6'], list(np.r_[q[:5], .015]))
        self.assertTrue(report['accepted'])
        self.assertFalse(report['issued'])  # Only the runner can record ctrl application.

    def test_prepend_preserves_all_five_original_legs_and_commit_is_once(self):
        c = self.controller()
        job = self.attach(c, ready=True)
        q = self.measured(c, displacement=.012)
        original = [np.asarray(path).copy() for path in job.proposal.paths]
        self.assertTrue(c._poll_transport(q, 12.2))
        self.assertEqual(len(c.transport), 5)
        self.assertEqual(c.transport[0][0].tobytes(), q[:5].tobytes())
        self.assertEqual(c.transport[0][1:].tobytes(), original[0].tobytes())
        for actual, expected in zip(c.transport[1:], original[1:]):
            self.assertEqual(actual.tobytes(), expected.tobytes())
        report = c.plan_reports[0]
        self.assertEqual(report['planner_snapshot_elapsed_s'], 12.)
        self.assertEqual(report['planned_at_s'], 12.2)
        self.assertEqual(report['waiting']['elapsed_s'], 12.2-12.)
        for leg, expected, executed in zip(report['proposal_legs'], original, report['legs']):
            self.assertEqual(np.asarray(leg['path']).tobytes(), expected.tobytes())
            self.assertEqual(executed['waypoint_count'], len(executed['path']))
            self.assertEqual(executed['motion_duration_s'], 2.)
            self.assertEqual(executed['arrival_guard_s'], .6)
        self.assertEqual(report['motion_and_arrival_s'], 13.)
        self.assertEqual(report['budget_finish_lower_bound_s'], 12.2+13.+14.)
        self.assertEqual(job.consume_count, 1)
        before = [p.tobytes() for p in c.transport]
        with self.assertRaises(RuntimeError):
            c._poll_transport(q, 12.3)
        self.assertEqual(job.consume_count, 1)
        self.assertEqual(len(c.plan_reports), 1)
        self.assertEqual([p.tobytes() for p in c.transport], before)

    def test_admission_budget_uses_current_time_and_original_14s_reservation(self):
        for elapsed, accepted in ((63., True), (63.001, False)):
            with self.subTest(elapsed=elapsed):
                c = self.controller()
                job = self.attach(c, ready=True)
                q = self.measured(c)
                if accepted:
                    self.assertTrue(c._poll_transport(q, elapsed))
                    self.assertEqual(c.plan_reports[0]['budget_finish_lower_bound_s'], 90.)
                    self.assertEqual(job.consume_count, 1)
                else:
                    with self.assertRaisesRegex(module.ControllerFailure, 'insufficient_time_for_transport'):
                        c._poll_transport(q, elapsed)
                    self.assertEqual(job.consume_count, 0)
                    self.assertEqual(c.transport, [])
                    self.assertEqual(c.plan_reports, [])
                    self.assertFalse(c.transport_events[-1]['accepted'])
                    self.assertFalse(c.transport_events[-1]['issued'])
                    self.assertGreater(c.transport_events[-1]['budget_finish_lower_bound_s'], 90.)
                    self.assertEqual(c.transport_events[-1]['proposal_report']['planned_at_s'], 12.)

    def test_context_changed_inside_payload_callback_cannot_commit_or_revive(self):
        c = self.controller()
        start = c.points[-1].copy()
        start[0] = .22
        job = self.attach(c, ready=True, start=start)

        def mutate_once(q):
            if q[0] > .205:  # Hold checks remain unchanged; mutate during admission.
                c.target_xy[0] = .241
            return True

        c.payload_predicate = mutate_once
        result = c.update(self.measured(c), np.zeros(6), 12.2)
        self.assertEqual(result['failure_reason'], 'transport_admission_observation_changed')
        c.target_xy[0] = .24
        self.assertEqual(job.state, 'rejected')
        self.assertEqual(job.consume_count, 0)
        self.assertEqual(c.transport, [])
        self.assertEqual(c.plan_reports, [])
        self.assertFalse(c.transport_events[-1]['accepted'])
        with self.assertRaisesRegex(RuntimeError, 'permanently unavailable'):
            c._poll_transport(self.measured(c), 12.3)

    def test_pending_update_keeps_reference_jaw_and_stage_start_with_fresh_guards(self):
        c = self.controller()
        job = self.attach(c)
        reference, points = c.reference.tobytes(), c.points.tobytes()
        q = self.measured(c)
        for index, elapsed in enumerate((12.2, 12.22, 12.24), 1):
            result = c.update(q, np.zeros(6), elapsed)
            self.assertEqual(result['status'], 'running')
            self.assertEqual(result['stage'], 'hold')
            self.assertEqual(result['command'].tobytes(), reference)
            self.assertEqual(result['geometric_reference'].tobytes(), reference)
            self.assertEqual(c.points.tobytes(), points)
            self.assertEqual(c.stage_started, 10.)
            self.assertEqual(c.duration, 1.5)
            self.assertEqual(c.jaw, .015)
            self.assertEqual(c.transport_request_seq, 1)
            self.assertEqual(c.last_sweep_report['checked_states'], 52)
            self.assertEqual(c.last_sweep_report['required_states'], 52)
            self.assertEqual(len(self.arm_rows(c)), index*53)  # measured + full chord
            self.assertEqual(len(self.payload_rows(c)), index*2)
            self.assertEqual(job.poll_count, index)
            self.assertEqual(c.transport_wait['pending_updates'], index)
        self.assertEqual(c.observation_seq, 10)
        self.assertEqual(c.transport, [])
        self.assertEqual(c.plan_reports, [])

    def test_arrival_only_gates_admission_and_never_skips_wait_guards(self):
        for displacement, velocity in ((.004, 0.), (.001, .051)):
            with self.subTest(displacement=displacement, velocity=velocity):
                c = self.controller()
                job = self.attach(c, ready=True)
                q, qvel = self.measured(c, displacement=displacement), np.zeros(6)
                qvel[0] = velocity
                result = c.update(q, qvel, 12.2)
                self.assertEqual(result['status'], 'running')
                self.assertEqual(result['stage'], 'hold')
                self.assertEqual(job.poll_count, 1)  # Poll errors promptly, but no admission.
                self.assertEqual(job.consume_count, 0)
                self.assertEqual(c.transport_events, [])
                self.assertEqual(len(self.arm_rows(c)), 53)
                self.assertEqual(len(self.payload_rows(c)), 2)
                self.assertEqual(c.last_sweep_report['checked_states'], 52)

    def test_hold_payload_failure_stops_before_poll_even_with_ready_proposal(self):
        c = self.controller()
        job = self.attach(c, ready=True)
        c.payload_predicate = lambda q: False
        result = c.update(self.measured(c), np.zeros(6), 12.2)
        self.assertEqual(result['failure_reason'], 'current_pose_command_chord_invalid')
        self.assertEqual(job.poll_count, 0)
        self.assertEqual(job.state, 'rejected')
        self.assertEqual(len(self.arm_rows(c)), 53)
        self.assertEqual(len(self.payload_rows(c)), 1)
        self.assertEqual(c.transport, [])

    def test_ready_bridge_interior_arm_collision_is_rejected_after_hold_guards(self):
        c = self.controller()
        start = c.points[-1].copy()
        start[0] = .22
        job = self.attach(c, ready=True, start=start)
        c.arm_predicate = lambda q: not (.208 < q[0] < .214)
        result = c.update(self.measured(c), np.zeros(6), 12.2)
        self.assertEqual(result['failure_reason'], 'transport_admission_chord_invalid')
        self.assertEqual(job.poll_count, 1)
        self.assertEqual(job.consume_count, 0)
        self.assertEqual(job.state, 'rejected')
        admission = c.transport_events[-1]
        sweep = admission['configuration_sweep']
        self.assertEqual(sweep['reason'], 'invalid_state')
        self.assertGreater(sweep['invalid_sample_index'], 0)
        self.assertLess(sweep['checked_states'], sweep['required_states'])
        self.assertEqual(sweep['checked_states'], sweep['invalid_sample_index']+1)
        self.assertTrue(c.arm_predicate(np.asarray(admission['start_q6'])))
        self.assertTrue(c.arm_predicate(np.asarray(admission['end_q6'])))
        self.assertIsNone(admission['payload_validation'])
        self.assertFalse(admission['accepted'])
        self.assertEqual(c.plan_reports, [])
        self.assertEqual(c.transport, [])

    def test_ready_bridge_interior_payload_collision_rejects_safe_endpoints(self):
        c = self.controller()
        start = c.points[-1].copy()
        start[0] = .22
        job = self.attach(c, ready=True, start=start)
        c.payload_predicate = lambda q: not (.208 < q[0] < .214)
        result = c.update(self.measured(c), np.zeros(6), 12.2)
        self.assertEqual(result['failure_reason'], 'transport_admission_payload_invalid')
        self.assertEqual(job.state, 'rejected')
        self.assertEqual(job.consume_count, 0)
        admission = c.transport_events[-1]
        self.assertTrue(admission['configuration_sweep']['valid'])
        self.assertEqual(admission['configuration_sweep']['checked_states'], 52)
        self.assertFalse(admission['payload_validation']['valid'])
        self.assertEqual(admission['payload_validation']['checked_states'], 3)
        self.assertEqual(admission['payload_validation']['resolution_rad'], .005)
        self.assertTrue(c.payload_predicate(np.asarray(admission['start_q6'])[:5]))
        self.assertTrue(c.payload_predicate(np.asarray(admission['end_q6'])[:5]))
        self.assertFalse(admission['accepted'])
        self.assertEqual(c.transport, [])

    def test_worker_exception_is_terminal_even_if_late_source_becomes_valid(self):
        c = self.controller()
        failure = RuntimeError('worker route failed')
        job = self.attach(c, error=failure)
        q = self.measured(c)
        result = c.update(q, np.zeros(6), 12.2)
        self.assertEqual(result['failure_reason'], str(failure))
        self.assertEqual(job.state, 'failed')
        self.assertEqual(job.consume_count, 0)
        self.assertEqual(c.transport, [])
        before = list(c.trace)
        job.error, job.ready = None, True
        result = c.update(q, np.zeros(6), 12.22)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failure_reason'], str(failure))
        self.assertEqual(c.trace, before)
        self.assertEqual(job.poll_count, 1)

    def test_callback_exception_rejects_ready_job_before_transport_commit(self):
        c = self.controller()
        job = self.attach(c, ready=True)

        def fail(q):
            raise ValueError('payload callback failed')

        c.payload_predicate = fail
        result = c.update(self.measured(c), np.zeros(6), 12.2)
        self.assertEqual(result['failure_reason'], 'payload callback failed')
        self.assertEqual(job.state, 'rejected')
        self.assertEqual(job.poll_count, 0)
        self.assertEqual(job.consume_count, 0)
        self.assertEqual(c.transport, [])
        self.assertEqual(c.plan_reports, [])

    def test_successful_update_checks_hold_bridge_and_first_command_before_commit(self):
        c = self.controller()
        start = c.points[-1].copy()
        start[0] = .22
        job = self.attach(c, ready=True, start=start)
        q = self.measured(c)
        result = c.update(q, np.zeros(6), 12.2)
        self.assertEqual(result['status'], 'running')
        self.assertEqual(result['stage'], 'transport')
        self.assertEqual(result['command'][:5].tobytes(), q[:5].tobytes())
        self.assertEqual(result['command'][5], .015)
        self.assertEqual(c.stage_started, 12.2)
        self.assertEqual(job.consume_count, 1)
        self.assertEqual(len(c.transport), 5)
        self.assertEqual(len(c.plan_reports), 1)
        tags = [row[0] for row in c.trace]
        poll, consumed = tags.index('poll'), tags.index('consume')
        self.assertEqual(tags[:poll].count('arm'), 53)
        self.assertEqual(tags[:poll].count('payload'), 2)
        admission = c.transport_events[-1]
        self.assertTrue(admission['configuration_sweep']['valid'])
        self.assertTrue(admission['payload_validation']['valid'])
        first = admission['first_command_guard']
        self.assertTrue(first['configuration_sweep']['valid'])
        self.assertTrue(first['payload_validation']['valid'])
        self.assertEqual(first['start_q6'], list(q))
        self.assertEqual(first['end_q6'], list(np.r_[q[:5], .015]))
        checked_arm = (admission['configuration_sweep']['checked_states']
                       + first['configuration_sweep']['checked_states'])
        checked_payload = (admission['payload_validation']['checked_states']
                           + first['payload_validation']['checked_states'])
        self.assertEqual(tags[poll+1:consumed].count('arm'), checked_arm)
        self.assertEqual(tags[poll+1:consumed].count('payload'), checked_payload)
        self.assertEqual(tags[consumed+1:], [])  # No unsafe commit-before-guard interval.
        self.assertEqual(c.last_sweep_report['checked_states'], 52)

    def test_nested_observation_changes_during_admission_payload_are_rejected(self):
        changes = {
            'sequence': lambda c: setattr(c, 'observation_seq', c.observation_seq+1),
            'observation_time': lambda c: setattr(c, 'observation',
                (c.observation[0], c.observation[1]+.001, *c.observation[2:])),
            'controller_time': lambda c: setattr(c, 'last_elapsed', c.last_elapsed+.001),
        }
        for name, change in changes.items():
            with self.subTest(change=name):
                c = self.controller()
                start = c.points[-1].copy()
                start[0] = .22
                job = self.attach(c, ready=True, start=start)

                def mutate(q):
                    if q[0] > .205:
                        change(c)
                    return True

                c.payload_predicate = mutate
                result = c.update(self.measured(c), np.zeros(6), 12.2)
                self.assertEqual(result['failure_reason'], 'transport_admission_observation_changed')
                self.assertEqual(job.state, 'rejected')
                self.assertEqual(job.consume_count, 0)
                self.assertEqual(c.transport, [])
                self.assertEqual(c.plan_reports, [])
                self.assertFalse(c.transport_events[-1]['accepted'])
                self.assertIsNone(c.transport_events[-1]['first_command_guard'])

    def test_nested_observation_change_in_first_command_payload_blocks_atomic_commit(self):
        c = self.controller()
        start = c.points[-1].copy()
        start[0] = .22
        job = self.attach(c, ready=True, start=start)
        q = self.measured(c)
        actual_sweep = c._configuration_sweep
        first_checked = False

        def observe_sweep(a, b, **kwargs):
            nonlocal first_checked
            result = actual_sweep(a, b, **kwargs)
            if np.asarray(a)[:5].tobytes() == np.asarray(b)[:5].tobytes():
                first_checked = True
            return result

        def mutate(q5):
            if first_checked:
                c.observation_seq += 1
            return True

        c.payload_predicate = mutate
        with patch.object(c, '_configuration_sweep', side_effect=observe_sweep):
            result = c.update(q, np.zeros(6), 12.2)
        self.assertTrue(first_checked)
        self.assertEqual(result['failure_reason'], 'transport_admission_observation_changed')
        self.assertEqual(job.consume_count, 0)
        self.assertEqual(job.state, 'rejected')
        self.assertEqual(c.transport, [])
        self.assertEqual(c.plan_reports, [])
        first = c.transport_events[-1]['first_command_guard']
        self.assertTrue(first['configuration_sweep']['valid'])
        self.assertTrue(first['payload_validation']['valid'])
        self.assertFalse(c.transport_events[-1]['accepted'])

    def test_legal_mixed_bridge_cannot_hide_invalid_pure_jaw_first_command(self):
        c = self.controller()
        start = c.points[-1].copy()
        start[0] = .22
        job = self.attach(c, ready=True, start=start)
        q = self.measured(c)
        # The hold chord moves left and the bridge moves right. Both escape
        # this narrow region; the issued first command keeps the achieved arm.
        c.arm_predicate = lambda state: not (
            abs(state[0]-q[0]) < 1e-9 and .04 < state[5] < .06)
        result = c.update(q, np.zeros(6), 12.2)
        self.assertEqual(result['failure_reason'], 'transport_first_command_invalid')
        admission = c.transport_events[-1]
        self.assertTrue(admission['configuration_sweep']['valid'])
        self.assertTrue(admission['payload_validation']['valid'])
        first = admission['first_command_guard']
        self.assertFalse(first['configuration_sweep']['valid'])
        self.assertIsNone(first['payload_validation'])
        self.assertTrue(c.arm_predicate(np.asarray(first['start_q6'])))
        self.assertTrue(c.arm_predicate(np.asarray(first['end_q6'])))
        self.assertEqual(job.consume_count, 0)
        self.assertEqual(job.state, 'rejected')
        self.assertFalse(admission['accepted'])
        self.assertFalse(admission['issued'])
        self.assertEqual(c.transport, [])
        self.assertEqual(c.plan_reports, [])

    def test_wait_keeps_original_stage_timeout_even_with_ready_proposal(self):
        c = self.controller()
        job = self.attach(c, ready=True)
        result = c.update(self.measured(c), np.zeros(6), 19.501)
        self.assertEqual(result['failure_reason'], 'encoder_stage_timeout')
        self.assertEqual(c.stage_started, 10.)
        self.assertEqual(c.duration, 1.5)
        self.assertEqual(job.poll_count, 0)
        self.assertEqual(job.state, 'rejected')
        self.assertEqual(c.transport, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
