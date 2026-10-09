"""CPU-only separation admission regression fixtures.

Real controller bindings and original samplers run against analytical geometry
stubs. No MuJoCo data, native checker, FK, integration or rendering is created.
Worker algorithm and lifecycle tests are separate from these admission tests.
"""
import copy
from dataclasses import replace
import json
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

import visual_grasp_controller as module
from separation_worker import (SeparationPlan, SeparationSample, SeparationSnapshot,
                               separation_sample_coordinates)


class ProposalSource:
    """Controlled availability; binding and once-only consumption stay real."""

    def __init__(self, binding, proposal, trace, *, ready=True, error=None):
        self.binding, self.proposal, self.trace = binding, proposal, trace
        self.ready, self.error = ready, error
        self.state = 'running'
        self.poll_count = self.consume_count = 0
        self.rejections = []
        self.execution = {'mode': 'cpu_stub', 'joined': True,
                          'abort_requested': False, 'worker_wall_s': .01}

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
        result = self.peek(binding)
        self.trace.append(('consume',))
        self.consume_count += 1
        self.state = 'consumed'
        return result

    def reject(self, reason):
        self.rejections.append(str(reason))
        if self.state not in ('failed', 'consumed', 'rejected'):
            self.state = 'rejected'

    def close(self):
        self.trace.append(('close',))
        self.execution['joined'] = True


class ReleaseGeometry:
    """An analytical pad fixture, deliberately independent of MuJoCo FK."""

    def __init__(self, controller):
        self.controller = controller
        self.model = object()
        self.center = np.array([.24, .14, .01])
        self.uncertainty_m = .002
        self.pose = None
        self.distance_predicate = None
        self.vertex_predicate = None

    def distances(self, q6):
        self.pose = np.asarray(q6, dtype=float).copy()
        self.controller.trace.append(('distance', tuple(self.pose)))
        if self.distance_predicate is not None:
            return self.distance_predicate(self.pose)
        height = self.pose[2] - .06
        return {'arm_guard': .01,
                'pad_gripper': .0005 + .1 * height,
                'pad_moving_jaw': .01}

    def pad_vertices(self):
        if self.pose is None:
            raise AssertionError('Vertices must follow their distance query')
        if self.vertex_predicate is not None:
            return self.vertex_predicate(self.pose)
        c = self.controller
        pinch = c._fk(self.pose)[2]
        offsets = np.array([[x, y, z] for x in (-.003, .003)
                            for y in (-.003, .003) for z in (-.002, .002)])
        return {'pad_gripper': pinch + offsets,
                'pad_moving_jaw': pinch + offsets + [.01, 0., 0.]}


class SeparationAdmissionTests(unittest.TestCase):
    def setUp(self):
        def forbidden(*args, **kwargs):
            raise AssertionError('Admission tests must not query real geometry')
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

        def evaluate(q, *, require_fixed_gripper=True):
            self.assertFalse(require_fixed_gripper)
            q = np.asarray(q, dtype=float).copy()
            c.trace.append(('arm', tuple(q)))
            return {'valid': bool(c.arm_predicate(q))}

        c.checker = SimpleNamespace(evaluate=evaluate)
        arm = np.array([.2, -.1, .06, .01, 0.])
        c.points = np.array([arm, arm])
        c.reference = np.r_[arm, .5]
        c.last_command = c.reference.copy()
        c.initial_q = np.r_[arm, .5]
        c.stage, c.stage_started, c.duration, c.jaw = 'release', 10., 6., .5
        c.last_elapsed, c.observation_seq, c.sweep_request_seq = 16.6, 8, 0
        c.observation = (8, 16.6, tuple(c.reference), (0.,) * 6)
        c.seed, c.replans, c.transport_index = 3, 0, 5
        c.target_xy = np.array([.24, -.13])
        c.target_timestamp, c.target_frozen, c.estimate_ttl = 0., True, 1.
        c.payload_relative, c.payload_rotation = np.zeros(3), np.eye(3)
        c.payload_uncertainty = .002
        c.world = [('floor', 6, np.zeros(3), np.eye(3), np.ones(3))]
        c.servo_offset = np.zeros(5)
        c.servo_transitions = []
        c.transport_job = None
        c.transport_events = []
        c.plan_reports, c.sweep_reports = [], []
        c.failure_reason, c.done = None, False
        c.release_record = {'estimated_center_m': [.24, .14, .01],
                            'uncertainty_m': .002, 'estimate_frozen_at_s': 10.}
        c.separation_job = None
        c.separation_request_seq = 1
        c.separation_request_binding = None
        c.separation_events = []
        c.separation_live_ready = False

        def fk(q):
            q = np.asarray(q)
            c.trace.append(('fk', tuple(q)))
            pinch = np.array([.24 + .01 * (q[0] - .2),
                              .14 + .01 * (q[1] + .1),
                              .03 + .02 * (q[2] - .06)])
            return np.zeros(3), np.eye(3), pinch

        c._fk = fk
        c.released_query = ReleaseGeometry(c)
        return c

    def measured(self, c, *, displacement=0., jaw=.5):
        q = c.reference.copy()
        q[0] += displacement
        q[5] = jaw
        return q

    def arm_rows(self, c):
        return np.array([row[1] for row in c.trace if row[0] == 'arm'])

    def proposal(self, c, *, q6=None, bad_sample=None, mutate=None):
        q6 = self.measured(c) if q6 is None else np.asarray(q6).copy()
        start = q6[:5].copy()
        end = start.copy()
        end[2] += .04
        separation = np.linspace(start, end, 14)
        return_path = np.array([end, c.initial_q[:5]])
        snapshot = SeparationSnapshot(q6, c.initial_q, c.last_command,
                                      c.seed, 16.2, c.released_query.center,
                                      c.released_query.uncertainty_m)
        samples = []
        for index, q5 in enumerate(separation_sample_coordinates(separation)):
            distances = c.released_query.distances(np.r_[q5, .5])
            vertices = c.released_query.pad_vertices()
            pinch = c._fk(np.r_[q5, .5])[2]
            values = {'q5': q5, 'pinch3': pinch, 'distances': distances,
                      'pad_vertices': vertices}
            if index == bad_sample and mutate is not None:
                mutate(values)
            samples.append(SeparationSample(**values))
        record = {**copy.deepcopy(c.release_record),
                  'separation_path': separation.tolist(),
                  'planned_return_path': return_path.tolist(),
                  'initial_distances_m': dict(samples[0].distances),
                  'separation_floors_m': {'pad_gripper': .00045},
                  'return_method': 'validated_direct',
                  'predicted_completion_s': snapshot.elapsed + 7.4}
        report = {'release_record': record,
                  'plan_reports': [{'stage': 'release_return_budget',
                                    'planned_at_s': snapshot.elapsed,
                                    'separation_motion_s': 2., 'return_motion_s': 2.,
                                    'required_s': 7.4,
                                    'predicted_completion_s': snapshot.elapsed + 7.4,
                                    'within_original_90s': True},
                                   {'stage': 'release_return', **record}]}
        return SeparationPlan((separation, return_path),
                              json.dumps(report, allow_nan=False), samples, snapshot)

    def attach(self, c, *, ready=True, proposal=None, error=None):
        proposal = self.proposal(c) if proposal is None else proposal
        binding = c._separation_binding()
        job = ProposalSource(binding, proposal, c.trace, ready=ready, error=error)
        c.separation_request_binding, c.separation_job = binding, job
        c.trace.clear()
        return job

    def initialize(self, c, q6=None):
        c._initialize_separation(self.measured(c) if q6 is None else q6)
        c.separation_live_ready = True
        c.trace.clear()

    def poll(self, c, q6=None, elapsed=16.61, **kwargs):
        q6 = self.measured(c) if q6 is None else q6
        c.last_elapsed = elapsed
        c.observation_seq += 1
        c.observation = (c.observation_seq, elapsed, tuple(q6), (0.,) * 6)
        return c._poll_separation(q6, elapsed, **kwargs)

    def test_initial_contact_exception_is_pad_only_and_keeps_original_depth_limit(self):
        for name, value, accepted in [('pad_gripper', -.003, True),
                                     ('pad_gripper', -.003001, False),
                                     ('arm_guard', .000999, False)]:
            with self.subTest(name=name, distance=value):
                c = self.controller()
                def distance(q, name=name, value=value):
                    row = {'arm_guard': .01, 'pad_gripper': .001,
                           'pad_moving_jaw': .01}
                    row[name] = value
                    return row
                c.released_query.distance_predicate = distance
                if accepted:
                    c._initialize_separation(self.measured(c))
                    self.assertEqual(c.separation_floors[name], value - .00005)
                    self.assertEqual(set(c.separation_vertices), {name})
                else:
                    with self.assertRaisesRegex(module.ControllerFailure,
                                                'release_initial_overlap_not_allowed'):
                        c._initialize_separation(self.measured(c))

    def test_initialize_requires_measured_jaw_at_original_point45_boundary(self):
        for jaw, accepted in [(.45, True), (np.nextafter(.45, -np.inf), False)]:
            with self.subTest(jaw=jaw):
                c = self.controller()
                q = self.measured(c, jaw=jaw)
                if accepted:
                    c._initialize_separation(q)
                    self.assertEqual(c.released_query.pose.tobytes(), q.tobytes())
                else:
                    with self.assertRaisesRegex(module.ControllerFailure, 'release_jaw_not_open'):
                        c._initialize_separation(q)

    def test_ratchet_keeps_max_height_and_clear_exception_never_returns(self):
        c = self.controller()
        q = self.measured(c)
        self.initialize(c, q)
        c.released_query.distance_predicate = lambda q: {
            'arm_guard': .01, 'pad_gripper': .0005, 'pad_moving_jaw': .01}
        old = c.separation_high_z['pad_gripper'].copy()
        raised = q.copy()
        raised[2] += .003
        c._ratchet_separation(raised)
        high = c.separation_high_z['pad_gripper'].copy()
        self.assertTrue(np.all(high > old))
        with self.assertRaisesRegex(module.ControllerFailure, 'measured_separation_invalid'):
            c._ratchet_separation(q)
        self.assertEqual(c.separation_high_z['pad_gripper'].tobytes(), high.tobytes())
        clear = q.copy()
        clear[2] += .006
        c.released_query.distance_predicate = lambda q: {
            'arm_guard': .01, 'pad_gripper': .002, 'pad_moving_jaw': .01}
        c._ratchet_separation(clear)
        self.assertNotIn('pad_gripper', c.separation_floors)
        c.released_query.distance_predicate = lambda q: {
            'arm_guard': .01, 'pad_gripper': .0005, 'pad_moving_jaw': .01}
        with self.assertRaisesRegex(module.ControllerFailure, 'measured_separation_invalid'):
            c._ratchet_separation(clear)
        self.assertNotIn('pad_gripper', c.separation_floors)
        self.assertFalse(c._separation_valid(clear[:5], clear[5]))

    def test_complete_saved_suffix_must_pass_even_when_current_bridge_is_clear(self):
        cases = [('distance_floor', 'distance_floor'),
                 ('clear_exception', 'distance_floor'),
                 ('raised_high_z', 'pad_monotonic_guard'),
                 ('pad_xy', 'pad_monotonic_guard'),
                 ('pinch_xy', 'pinch_guard'), ('pinch_z', 'pinch_guard')]
        for fault, reason in cases:
            with self.subTest(fault=fault):
                c = self.controller()
                q = self.measured(c)
                self.initialize(c, q)
                baseline = c.separation_vertices['pad_gripper'].copy()

                def mutate(values):
                    if fault == 'distance_floor':
                        values['distances']['pad_gripper'] = .00046
                    elif fault == 'raised_high_z':
                        values['pad_vertices']['pad_gripper'] = baseline.copy()
                        values['pad_vertices']['pad_gripper'][:, 2] -= .00004
                    elif fault == 'pad_xy':
                        values['pad_vertices']['pad_gripper'][0, 0] += .000201
                    elif fault == 'pinch_xy':
                        values['pinch3'][0] += .000201
                    elif fault == 'pinch_z':
                        values['pinch3'][2] = c.separation_pinch[2] - .000201

                plan = self.proposal(c, bad_sample=5, mutate=mutate)
                if fault == 'distance_floor':
                    c.separation_floors['pad_gripper'] = .00048
                elif fault == 'raised_high_z':
                    c.separation_high_z['pad_gripper'] += .00003
                elif fault == 'clear_exception':
                    c.released_query.distance_predicate = lambda q: {
                        'arm_guard': .01, 'pad_gripper': .002, 'pad_moving_jaw': .01}
                    c._ratchet_separation(q)
                    self.assertNotIn('pad_gripper', c.separation_floors)
                # This independently proves the proposed new bridge is clear;
                # the rejected evidence lies beyond its endpoints.
                bridge = module.validate_joint_path(
                    [q[:5], plan.paths[0][0]], c._separation_valid, .002)
                self.assertTrue(bridge['valid'])
                job = self.attach(c, proposal=plan)
                with self.assertRaisesRegex(module.ControllerFailure,
                                            'separation_saved_samples_invalid'):
                    self.poll(c, q)
                evidence = c.separation_events[-1]['sample_inclusion']
                self.assertFalse(evidence['valid'])
                self.assertEqual(evidence['reason'], reason)
                bad_index = 0 if fault == 'clear_exception' else 5
                self.assertEqual(evidence['invalid_sample_index'], bad_index)
                self.assertEqual(evidence['checked_samples'], bad_index + 1)
                self.assertEqual(evidence['sample_count'], len(plan.samples))
                self.assertEqual(job.consume_count, 0)
                self.assertEqual(c.stage, 'release')
                self.assertEqual(c.plan_reports, [])
                self.assertFalse(c.separation_events[-1]['accepted'])
                self.assertFalse(c.separation_events[-1]['issued'])

    def test_consistent_but_incomplete_geometry_names_cannot_admit(self):
        c = self.controller()
        self.initialize(c)
        plan = self.proposal(c)
        samples = tuple(replace(row, distances=tuple((name, distance)
                                                    for name, distance in row.distances
                                                    if name != 'arm_guard'))
                        for row in plan.samples)
        report = json.loads(plan.report_json)
        for record in (report['release_record'], report['plan_reports'][-1]):
            del record['initial_distances_m']['arm_guard']
        incomplete = SeparationPlan(plan.paths, json.dumps(report), samples, plan.snapshot)
        job = self.attach(c, proposal=incomplete)
        with self.assertRaisesRegex(module.ControllerFailure, 'separation_geometry_coverage_changed'):
            self.poll(c)
        self.assertEqual(job.consume_count, 0)
        self.assertEqual(c.plan_reports, [])
        self.assertEqual(c.stage, 'release')

    def test_binding_allows_new_observations_but_semantic_changes_reject_and_ABA_stays_dead(self):
        c = self.controller()
        job = self.attach(c)
        original = c._separation_binding()
        c.last_elapsed += .02
        c.observation_seq += 1
        c.observation = (c.observation_seq, c.last_elapsed, tuple(self.measured(c)), (.01,) * 6)
        c.sweep_request_seq += 1
        self.assertTrue(original.matches(c._separation_binding()))
        changes = [lambda c: setattr(c, 'separation_request_seq', 2),
                   lambda c: setattr(c, 'stage', 'separate'),
                   lambda c: setattr(c, 'stage_started', 10.01),
                   lambda c: setattr(c, 'jaw', .49),
                   lambda c: setattr(c, 'seed', 4),
                   lambda c: setattr(c, 'checker', object()),
                   lambda c: setattr(c, 'rig', object()),
                   lambda c: setattr(c.released_query, 'model', object()),
                   lambda c: c.released_query.center.__setitem__(0, .241),
                   lambda c: setattr(c.released_query, 'uncertainty_m', .003),
                   lambda c: c.last_command.__setitem__(0, .2001),
                   lambda c: c.world[0][2].__setitem__(0, .001),
                   lambda c: c.release_record.__setitem__('estimate_frozen_at_s', 10.01)]
        for index, change in enumerate(changes):
            with self.subTest(change=index):
                c = self.controller()
                job = self.attach(c)
                change(c)
                with self.assertRaisesRegex(module.ControllerFailure, 'separation_context_changed'):
                    self.poll(c)
                self.assertEqual(job.state, 'rejected')
                self.assertEqual(job.consume_count, 0)
        c = self.controller()
        c.released_query.center[0] = .0
        job = self.attach(c)
        c.released_query.center[0] = -.0
        with self.assertRaisesRegex(module.ControllerFailure, 'separation_context_changed'):
            self.poll(c)
        c.released_query.center[0] = .0
        self.assertTrue(job.binding.matches(c._separation_binding()))
        with self.assertRaisesRegex(RuntimeError, 'permanently unavailable'):
            self.poll(c)
        self.assertEqual(job.consume_count, 0)

    def test_prefetch_once_after_original_guard_does_not_shorten_release_readiness(self):
        c = self.controller()
        c.separation_request_seq, c.last_elapsed = 0, 10.
        created = []

        def factory(binding):
            job = ProposalSource(binding, None, c.trace, ready=False)
            job.cancel_event = threading.Event()
            def start(worker, *args):
                job.args = args
                c.trace.append(('start',))
            job.start = start
            created.append(job)
            return job

        with patch.object(module, 'AsyncSeparationPlanningJob', side_effect=factory):
            for elapsed in (11., 11.02, 16.59):
                result = c.update(self.measured(c, jaw=.451), np.zeros(6), elapsed)
                self.assertEqual(result['status'], 'running')
                self.assertEqual(result['stage'], 'release')
                self.assertEqual(result['command'].tobytes(), c.reference.tobytes())
                self.assertEqual(c.stage_started, 10.)
                self.assertEqual(c.duration, 6.)
                self.assertFalse(c.separation_live_ready)
            self.assertEqual(len(created), 1)
            self.assertEqual(c.separation_request_seq, 1)
            self.assertEqual(created[0].poll_count, 3)
            self.assertEqual(created[0].consume_count, 0)
            first_start = next(i for i, row in enumerate(c.trace) if row[0] == 'start')
            self.assertGreaterEqual(sum(row[0] == 'arm' for row in c.trace[:first_start]), 3)
            self.assertEqual(created[0].args[2].q6[-1], .451)
            self.assertIsNot(created[0].args[0], c.rig)
            self.assertIsNot(created[0].args[1], c.released_query.model)

    def test_ready_pending_keeps_stage_timeout_and_ratchet_cannot_reintroduce_contact(self):
        for fault in ('stage_timeout', 'recontact_after_clear'):
            with self.subTest(fault=fault):
                c = self.controller()
                job = self.attach(c, ready=False)
                q = self.measured(c)
                result = c.update(q, np.zeros(6), 16.61)
                self.assertEqual(result['status'], 'running')
                self.assertTrue(c.separation_live_ready)
                self.assertEqual(c.stage_started, 10.)
                self.assertEqual(c.duration, 6.)
                if fault == 'stage_timeout':
                    elapsed, expected = 24.01, 'encoder_stage_timeout'
                else:
                    c.released_query.distance_predicate = lambda q: {
                        'arm_guard': .01, 'pad_gripper': .002, 'pad_moving_jaw': .01}
                    self.assertEqual(c.update(q, np.zeros(6), 16.63)['status'], 'running')
                    self.assertNotIn('pad_gripper', c.separation_floors)
                    c.released_query.distance_predicate = lambda q: {
                        'arm_guard': .01, 'pad_gripper': .0005, 'pad_moving_jaw': .01}
                    elapsed, expected = 16.65, 'measured_separation_invalid'
                result = c.update(q, np.zeros(6), elapsed)
                self.assertEqual(result['failure_reason'], expected)
                self.assertEqual(job.state, 'rejected')
                self.assertEqual(job.consume_count, 0)
                self.assertEqual(c.stage_started, 10.)
                self.assertEqual(c.plan_reports, [])

    def test_bridge_interior_arm_or_separation_collision_rejects_safe_endpoints(self):
        for fault in ('arm', 'separation'):
            with self.subTest(fault=fault):
                c = self.controller()
                q, snapshot_q = self.measured(c), self.measured(c)
                snapshot_q[0] += .018
                plan = self.proposal(c, q6=snapshot_q)
                self.initialize(c, q)
                job = self.attach(c, proposal=plan)
                if fault == 'arm':
                    c.arm_predicate = lambda q: not (.207 < q[0] < .213)
                else:
                    def distances(q):
                        return {'arm_guard': .0009 if .207 < q[0] < .213 else .01,
                                'pad_gripper': .0005 + .1 * (q[2] - .06),
                                'pad_moving_jaw': .01}
                    c.released_query.distance_predicate = distances
                self.assertTrue(c._separation_valid(q[:5], q[5]))
                self.assertTrue(c._separation_valid(snapshot_q[:5], .5))
                with self.assertRaisesRegex(module.ControllerFailure, 'separation_admission_chord_invalid'):
                    self.poll(c, q)
                event = c.separation_events[-1]
                self.assertTrue(event['sample_inclusion']['valid'])
                report = event['configuration_sweep'] if fault == 'arm' else event['separation_validation']
                self.assertFalse(report['valid'])
                if fault == 'arm':
                    self.assertGreater(report['invalid_sample_index'], 0)
                    self.assertEqual(report['checked_states'], report['invalid_sample_index'] + 1)
                else:
                    self.assertEqual(report['invalid_segment'], 0)
                    self.assertGreater(report['checked_states'], 1)
                    self.assertTrue(.207 < report['invalid_state'][0] < .213)
                self.assertEqual(event['separation_validation']['resolution_rad'], .002)
                self.assertEqual(job.consume_count, 0)
                self.assertEqual(c.stage, 'release')

    def test_success_preserves_waypoints_first_setpoint_and_separate_geometric_reference(self):
        c = self.controller()
        c.last_command[0] += .0025
        command_before = c.last_command.copy()
        c.arm_predicate = lambda q: q[0] <= .201
        q = self.measured(c, displacement=.0004)
        plan = self.proposal(c)
        self.initialize(c, q)
        job = self.attach(c, proposal=plan)
        result = c.update(q, np.zeros(6), 16.61)
        self.assertEqual(result['status'], 'running')
        self.assertEqual(result['stage'], 'separate')
        self.assertEqual(result['command'].tobytes(), command_before.tobytes())
        self.assertEqual(result['geometric_reference'].tobytes(), np.r_[q[:5], .5].tobytes())
        self.assertEqual(c.points[0].tobytes(), q[:5].tobytes())
        self.assertEqual(c.points[1:].tobytes(), np.asarray(plan.paths[0]).tobytes())
        self.assertEqual(job.consume_count, 1)
        self.assertEqual(c.stage_started, 16.61)
        event = c.separation_events[-1]
        self.assertTrue(event['accepted'])
        self.assertFalse(event['issued'])  # Only the real runner can acknowledge ctrl issuance.
        self.assertEqual(event['sample_inclusion']['checked_samples'], len(plan.samples))
        first = event['first_command_guard']
        self.assertTrue(first['continuous'])
        self.assertTrue(first['configuration_sweep']['valid'])
        self.assertTrue(first['separation_validation']['valid'])
        self.assertEqual(np.array(first['end_q6']).tobytes(), result['geometric_reference'].tobytes())
        self.assertEqual(np.array(first['actuator_command']).tobytes(), command_before.tobytes())
        self.assertTrue(np.all(self.arm_rows(c)[:, 0] <= .201))
        # Saved suffix inclusion must not rerun all original geometry callbacks.
        self.assertLess(len(self.arm_rows(c)), len(plan.samples))
        with self.assertRaises(RuntimeError):
            self.poll(c, q, 16.63)
        self.assertEqual(job.consume_count, 1)
        self.assertEqual(c.points[1:].tobytes(), np.asarray(plan.paths[0]).tobytes())

    def test_current_budget_mapping_and_offset_fail_before_consumption(self):
        for fault in ('budget', 'joint_bounds', 'actuator_bounds', 'offset'):
            with self.subTest(fault=fault):
                c = self.controller()
                elapsed = 16.61
                if fault == 'budget':
                    c.stage_started = 75.99
                    elapsed = 82.601
                if fault in ('joint_bounds', 'actuator_bounds'):
                    c.last_command[2] += .0025
                    reason = 'mapped_servo_target_out_of_bounds'
                elif fault == 'offset':
                    c.last_command[0] += .004
                    reason = 'servo_offset_exceeds_arrival_tolerance'
                else:
                    reason = 'insufficient_time_for_safe_return'
                plan = self.proposal(c)
                self.initialize(c)
                job = self.attach(c, proposal=plan)
                if fault in ('joint_bounds', 'actuator_bounds'):
                    bounds = c.rig.jnt_range if fault == 'joint_bounds' else c.rig.actuator_ctrlrange
                    bounds[2, 1] = plan.paths[0][-1][2] + .001
                with self.assertRaisesRegex(module.ControllerFailure, reason):
                    self.poll(c, elapsed=elapsed)
                self.assertEqual(job.consume_count, 0)
                self.assertEqual(c.plan_reports, [])
                self.assertEqual(c.stage, 'release')
                self.assertFalse(c.separation_events[-1]['accepted'])
                if fault == 'budget':
                    self.assertAlmostEqual(c.separation_events[-1]['required_s'], 7.4)
                    self.assertGreater(c.separation_events[-1]['predicted_completion_s'], 90.)
        c = self.controller()
        c.stage_started = 75.99
        job = self.attach(c)
        self.assertTrue(self.poll(c, elapsed=82.6))
        self.assertEqual(c.separation_events[-1]['predicted_completion_s'], 90.)
        self.assertEqual(job.consume_count, 1)

    def test_actual_jaw_relapse_cannot_admit_even_with_ready_plan(self):
        c = self.controller()
        job = self.attach(c, ready=True)
        self.initialize(c)
        q = self.measured(c, jaw=np.nextafter(.45, -np.inf))
        result = c.update(q, np.zeros(6), 16.61)
        self.assertEqual(result['stage'], 'release')
        self.assertEqual(result['status'], 'running')
        self.assertEqual(job.consume_count, 0)
        self.assertEqual(result['command'][5], .5)
        self.assertGreater(c.last_sweep_report['checked_states'], 2)

    def test_ready_release_pending_keeps_loaded_setpoint_and_guards_achieved_reference(self):
        c = self.controller()
        achieved = self.measured(c, jaw=.49)
        target = self.measured(c)
        target[0] += .0025
        c.points = np.array([target[:5], target[:5]])
        c.reference = target.copy()
        c.last_command = target.copy()
        original_fk = c._fk

        def fk(q):
            origin, rotation, pinch = original_fk(q)
            # A small encoder offset crosses the original 0.2 mm XY guard.
            pinch[0] = .24 + .2 * (q[0] - .2)
            return origin, rotation, pinch

        c._fk = fk
        plan = self.proposal(c, q6=achieved)
        job = self.attach(c, ready=False, proposal=plan)
        old_setpoint, old_points = c.last_command.copy(), c.points.copy()
        for elapsed in (16.61, 16.63):
            result = c.update(achieved, np.zeros(6), elapsed)
            self.assertEqual(result['status'], 'running')
            self.assertEqual(result['stage'], 'release')
            self.assertTrue(c.separation_live_ready)
            self.assertEqual(result['command'].tobytes(), old_setpoint.tobytes())
            self.assertEqual(result['geometric_reference'].tobytes(),
                             np.r_[achieved[:5], .5].tobytes())
            self.assertEqual(c.points.tobytes(), old_points.tobytes())
            self.assertEqual(c.stage_started, 10.)
            self.assertEqual(c.duration, 6.)
            self.assertTrue(c.last_sweep_report['valid'])
            self.assertGreater(c.last_sweep_report['checked_states'], 2)
        rows = self.arm_rows(c)
        self.assertTrue(np.all(rows[:, :5] == achieved[:5]))
        self.assertTrue(np.any((rows[:, 5] > achieved[5]) & (rows[:, 5] < .5)))
        self.assertTrue(c._separation_valid(achieved[:5], .5))
        # This target is a holding setpoint; treating it as achieved geometry
        # would reject the original pinch guard instead of validating the wait.
        self.assertFalse(c._separation_valid(old_setpoint[:5], .5))
        self.assertEqual(job.consume_count, 0)
        self.assertEqual(c.plan_reports, [])
        result = c.update(achieved, np.zeros(6), 24.01)
        self.assertEqual(result['failure_reason'], 'encoder_stage_timeout')
        self.assertEqual(c.stage_started, 10.)
        self.assertEqual(job.consume_count, 0)
        self.assertEqual(job.state, 'rejected')

    def test_observation_or_first_guard_setpoint_mutation_cannot_consume(self):
        for fault in ('observation', 'first_guard_setpoint'):
            with self.subTest(fault=fault):
                c = self.controller()
                plan = self.proposal(c)
                q = self.measured(c, displacement=.001, jaw=.49)
                self.initialize(c, q)
                job = self.attach(c, proposal=plan)
                changed = False

                def predicate(sample):
                    nonlocal changed
                    first_only = (sample[0] == q[0] and .49 < sample[5] < .5)
                    if not changed and (fault == 'observation' or first_only):
                        changed = True
                        if fault == 'observation':
                            seq, elapsed, pose, velocity = c.observation
                            c.observation = (seq + 1, elapsed, pose, (.01,) * 6)
                        else:
                            c.last_command[0] += .0001
                    return True

                c.arm_predicate = predicate
                with self.assertRaises(RuntimeError):
                    self.poll(c, q)
                self.assertTrue(changed)
                self.assertEqual(job.consume_count, 0)
                self.assertEqual(c.stage, 'release')
                self.assertEqual(c.plan_reports, [])
                if fault == 'first_guard_setpoint':
                    event = c.separation_events[-1]
                    self.assertTrue(event['configuration_sweep']['valid'])
                    self.assertTrue(event['separation_validation']['valid'])
                    self.assertTrue(event['first_command_guard']['configuration_sweep']['valid'])
                    self.assertEqual(job.state, 'rejected')

    def test_worker_error_is_terminal_and_late_completion_cannot_revive(self):
        c = self.controller()
        failure = RuntimeError('separation worker rejected its route')
        job = self.attach(c, ready=False, error=failure)
        result = c.update(self.measured(c), np.zeros(6), 16.61)
        self.assertEqual(result['failure_reason'], str(failure))
        self.assertEqual(job.state, 'failed')
        self.assertEqual(job.consume_count, 0)
        polls = job.poll_count
        job.error, job.ready = None, True
        result = c.update(self.measured(c), np.zeros(6), 16.63)
        self.assertEqual(result['failure_reason'], str(failure))
        self.assertEqual(job.poll_count, polls)
        self.assertEqual(c.plan_reports, [])

    def test_cleanup_attempts_both_owned_jobs_and_preserves_first_error(self):
        c = self.controller()
        calls = []
        first = RuntimeError('first join failed')
        second = RuntimeError('second join failed')

        def close_first():
            calls.append('transport')
            raise first

        def close_second():
            calls.append('separation')
            raise second

        c.transport_job = SimpleNamespace(close=close_first)
        c.separation_job = SimpleNamespace(close=close_second)
        with self.assertRaises(RuntimeError) as observed:
            c.close()
        self.assertIs(observed.exception, first)
        self.assertEqual(calls, ['transport', 'separation'])


if __name__ == '__main__':
    unittest.main()
