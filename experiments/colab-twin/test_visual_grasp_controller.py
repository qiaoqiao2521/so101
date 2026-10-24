"""Controller protocol/state-machine tests with fake FK/planning, no physics."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock
import numpy as np
import visual_grasp_controller as module


class VisualControllerTests(unittest.TestCase):
    def controller(self, target_xy=(.24, -.13), **options):
        rig = SimpleNamespace(nq=6, nv=6, ngeom=0,
                              jnt_range=np.tile([-3.,3.],(6,1)),
                              actuator_ctrlrange=np.tile([-3.,3.],(6,1)),
                              body=lambda name: SimpleNamespace(id=0))
        query = SimpleNamespace(qpos=np.zeros(6), qvel=np.zeros(6),
                                xpos=np.zeros((1, 3)), xmat=np.eye(3).reshape(1, 9))
        checker = Mock(bounds=np.tile([-3., 3.], (5, 1)))
        checker.evaluate.return_value = {'valid': True}

        def forward(rig, data):
            data.xpos[0] = data.qpos[:3] - module.PINCH_POINT

        def solve(rig, xyz, initial=None):
            return np.r_[xyz, 0., 0.]

        def plan(start, goal, *args, **kwargs):
            return {'status': 'solved', 'path': [list(start), list(goal)]}

        for target, replacement in [
            ('CollisionChecker', Mock(return_value=checker)),
            ('solve_pinch_ik', solve), ('plan_joint_path', plan),
        ]:
            p = patch.object(module, target, replacement)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(module.mujoco, 'MjData', return_value=query)
        p.start()
        self.addCleanup(p.stop)
        p = patch.object(module.mujoco, 'mj_forward', side_effect=forward)
        p.start()
        self.addCleanup(p.stop)
        p = patch.object(module.TopDownCalibration, 'from_mujoco_model',
                         return_value=module.TopDownCalibration())
        p.start()
        self.addCleanup(p.stop)
        return module.VisualGraspController(rig, target_xy, [.24, .14, .06, 0, 0, .5], **options)

    def test_carry_wait_keeps_hold_target_and_original_stage_timeout(self):
        gate = Mock(return_value=False)
        controller = self.controller(transport_gate=gate)
        controller.target_frozen = True
        controller._set_dwell('hold', controller.lift, .015, 10., 1.5)
        controller._payload_valid = Mock(return_value=True)
        controller._start_transport = Mock()
        controller._poll_transport = Mock()
        measured = np.r_[controller.lift, .015]
        points = controller.points.copy()
        before_checks = controller.checker.evaluate.call_count
        with patch.object(controller, '_configuration_sweep', wraps=controller._configuration_sweep) as sweep:
            for elapsed in (12.11, 12.13, 14.):
                with self.subTest(elapsed=elapsed):
                    result = controller.update(measured, np.zeros(6), elapsed)
                    self.assertEqual(result['status'], 'running')
                    self.assertEqual(result['stage'], 'hold')
                    self.assertEqual(controller.stage_started, 10.)
                    self.assertEqual(controller.duration, 1.5)
                    np.testing.assert_array_equal(controller.points, points)
                    np.testing.assert_array_equal(result['command'], measured)
            self.assertEqual(sweep.call_count, 3)
        self.assertEqual(gate.call_count, 3)
        self.assertGreater(controller.checker.evaluate.call_count-before_checks, 3)
        self.assertGreaterEqual(controller._payload_valid.call_count, 3)
        result = controller.update(measured, np.zeros(6), 19.51)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failure_reason'], 'encoder_stage_timeout')
        self.assertEqual(controller.stage_started, 10.)
        self.assertEqual(gate.call_count, 3)
        controller._start_transport.assert_not_called()
        controller._poll_transport.assert_not_called()

    def test_carry_gate_is_not_called_before_measured_sweep_or_payload_guards_pass(self):
        for failed_guard in ('measured', 'sweep', 'payload'):
            with self.subTest(guard=failed_guard):
                gate = Mock(return_value=True)
                controller = self.controller(transport_gate=gate)
                controller.target_frozen = True
                controller._set_dwell('hold', controller.lift, .015, 10., 1.5)
                controller._payload_valid = Mock(return_value=failed_guard != 'payload')
                controller._start_transport = Mock()
                controller._poll_transport = Mock()
                if failed_guard == 'measured':
                    controller.checker.evaluate.return_value = {'valid': False}
                with patch.object(controller, '_configuration_sweep',
                                  return_value={'valid': failed_guard != 'sweep'}):
                    result = controller.update(np.r_[controller.lift, .015], np.zeros(6), 12.11)
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['failure_reason'],
                    'measured_arm_configuration_invalid' if failed_guard == 'measured'
                    else 'current_pose_command_chord_invalid')
                gate.assert_not_called()
                controller._start_transport.assert_not_called()
                controller._poll_transport.assert_not_called()

    def test_default_pickup_hover_keeps_original_high_and_down_targets(self):
        controller = self.controller()
        self.assertEqual(controller.pickup_hover_z_m, .06)
        np.testing.assert_array_equal(controller.approach[:3], [.24, -.13, .06])
        np.testing.assert_array_equal(controller.down[:3], [.24, -.13, .019])
        np.testing.assert_array_equal(controller.lift[:3], [.24, -.13, .06])

    def test_development_pickup_hover_changes_high_targets_only(self):
        controller = self.controller(pickup_hover_z_m=.054)
        self.assertEqual(controller.pickup_hover_z_m, .054)
        np.testing.assert_array_equal(controller.approach[:3], [.24, -.13, .054])
        np.testing.assert_array_equal(controller.down[:3], [.24, -.13, .019])
        np.testing.assert_array_equal(controller.lift[:3], [.24, -.13, .054])
        np.testing.assert_array_equal(controller.initial_q, [.24, .14, .06, 0, 0, .5])
        self.assertEqual(controller.sweep_reports[0]['stage'], 'planned_closure')

    def test_invalid_pickup_hover_heights_are_rejected_before_planning(self):
        for height in (True, np.bool_(False), None, '.054', .054+0j,
                       np.nan, np.inf, -.001, .0539999, .0600001):
            with self.subTest(height=height), \
                    patch.object(module.VisualGraspController, '_plan_approach') as plan, \
                    self.assertRaisesRegex(ValueError, 'pickup_hover_z_m'):
                self.controller(pickup_hover_z_m=height)
            plan.assert_not_called()

    def test_default_target_region_keeps_legacy_bounds_and_static_call(self):
        for xy in ([.23000001, -.13999999], [.25000009, -.11999991]):
            with self.subTest(xy=xy):
                controller = self.controller(target_xy=xy)
                self.assertIsNone(controller.target_region_xy_m)
                np.testing.assert_array_equal(controller.target_xy, xy)
                np.testing.assert_array_equal(module.VisualGraspController._target(xy), xy)
        for xy in ([.26, -.13], [.24, -.11], [.25000011, -.13], [.24, -.14000011]):
            with self.subTest(xy=xy):
                for accept in (module.VisualGraspController._target,
                               lambda value: self.controller(target_xy=value)):
                    with self.assertRaisesRegex(ValueError, 'declared red-tray') as failure:
                        accept(xy)
                    self.assertEqual(str(failure.exception),
                                     'Target outside the declared red-tray +/-10 mm region')

    def test_declared_target_region_applies_to_initial_and_later_rgb_estimates(self):
        region = ((.22, .27), (-.15, -.11))
        controller = self.controller(target_xy=[.26, -.13], target_region_xy_m=region)
        np.testing.assert_array_equal(controller.target_xy, [.26, -.13])
        q = controller.initial_q.copy()
        result = controller.update(q, np.zeros(6), .1,
                                   {'valid': True, 'xy': [.265, -.12], 'timestamp_s': .1})
        self.assertEqual(result['status'], 'running')
        np.testing.assert_array_equal(controller.latest_xy, [.265, -.12])
        for xy in ([.22, -.15], [.27, -.11]):
            np.testing.assert_array_equal(controller._target(xy, controller.target_region_xy_m), xy)
        for xy in ([.219, -.13], [.271, -.13], [.26, -.151], [.26, -.109]):
            with self.subTest(xy=xy):
                with self.assertRaisesRegex(ValueError, 'target_region_xy_m'):
                    self.controller(target_xy=xy, target_region_xy_m=region)
                with self.assertRaisesRegex(ValueError, 'target_region_xy_m'):
                    controller._ingest_estimate({'valid': True, 'xy': xy, 'timestamp_s': .2}, .2)
        np.testing.assert_array_equal(controller.latest_xy, [.265, -.12])
        self.assertEqual(controller.target_timestamp, .1)

    def test_declared_target_region_owns_immutable_bounds(self):
        requested = np.array([[.22, .27], [-.15, -.11]])
        controller = self.controller(target_xy=[.26, -.13], target_region_xy_m=requested)
        requested[:] = 99
        self.assertEqual(controller.target_region_xy_m, ((.22, .27), (-.15, -.11)))
        self.assertTrue(all(isinstance(axis, tuple) for axis in controller.target_region_xy_m))
        controller._ingest_estimate({'valid': True, 'xy': [.265, -.12], 'timestamp_s': .1}, .1)
        np.testing.assert_array_equal(controller.latest_xy, [.265, -.12])
        with self.assertRaisesRegex(ValueError, 'target_region_xy_m'):
            controller._ingest_estimate({'valid': True, 'xy': [99, 99], 'timestamp_s': .2}, .2)

    def test_invalid_declared_target_regions_have_named_errors(self):
        for region in (True, 'region', [], [.22, .27], [[.22, .27]],
                       [[.22, .27], [-.15, -.13, -.11]],
                       [[.27, .22], [-.15, -.11]], [[.22, .22], [-.15, -.11]],
                       [[True, .27], [-.15, -.11]], [[.22, .27], [-.15, np.bool_(False)]],
                       [[np.nan, .27], [-.15, -.11]], [[.22, np.inf], [-.15, -.11]],
                       [['.22', .27], [-.15, -.11]], [[.22+0j, .27], [-.15, -.11]]):
            with self.subTest(region=region), self.assertRaisesRegex(ValueError, 'target_region_xy_m'):
                self.controller(target_region_xy_m=region)

    def test_fake_controller_without_declared_region_keeps_default_estimate_check(self):
        controller = module.VisualGraspController.__new__(module.VisualGraspController)
        controller.target_frozen = False
        controller.target_timestamp = 0.
        controller.estimate_ttl = 1.
        controller._ingest_estimate({'valid': True, 'xy': [.24, -.13], 'timestamp_s': .1}, .1)
        np.testing.assert_array_equal(controller.latest_xy, [.24, -.13])
        with self.assertRaisesRegex(ValueError, 'declared red-tray'):
            controller._ingest_estimate({'valid': True, 'xy': [.26, -.13], 'timestamp_s': .2}, .2)

    def test_place_target_uses_original_default_and_owns_requested_xy(self):
        default = self.controller()
        np.testing.assert_array_equal(default.place_xy, module.PLACE_CENTER)
        requested = np.array([.252, .124])
        changed = self.controller(place_xy=requested)
        requested[:] = 99
        np.testing.assert_array_equal(changed.place_xy, [.252, .124])
        for invalid in ([.25], [.25, .14, .01], [np.nan, .14], [.25, np.inf]):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, 'place_xy'):
                self.controller(place_xy=invalid)

    def test_transport_worker_plans_all_final_legs_to_requested_place(self):
        for requested in (None, [.252, .124]):
            with self.subTest(place_xy=requested):
                controller = self.controller(place_xy=requested)
                controller.stage = 'hold'
                controller.last_elapsed = 3.
                controller.payload_relative = np.zeros(3)
                controller.payload_rotation = np.eye(3)
                controller._plan_transport(np.r_[controller.lift, .015])
                goal = np.array(module.PLACE_CENTER if requested is None else requested)
                np.testing.assert_allclose(controller.transport[2][-1][:3], [.18, goal[1], .06])
                np.testing.assert_allclose(controller.transport[3][-1][:3], [*goal, .06])
                np.testing.assert_allclose(controller.transport[4][-1][:3], [*goal, .023])
                self.assertEqual(controller.plan_reports[-1]['place_xy'], goal.tolist())
                self.assertEqual(controller.plan_reports[-1]['transition_height_m'], .06)
                self.assertEqual(controller.plan_reports[-1]['transition_height_reason'], 'original_height')
                self.assertEqual(len(controller.plan_reports[-1]['transition_attempts']), 1)

    def test_raised_tray_moves_certified_transport_and_release_world_height(self):
        controller = self.controller(place_height_m=.010, release_pinch_height_m=.028)
        controller.stage, controller.last_elapsed = 'hold', 3.
        controller.payload_relative, controller.payload_rotation = np.zeros(3), np.eye(3)
        controller._plan_transport(np.r_[controller.lift, .015])
        np.testing.assert_allclose(controller.transport[3][-1][:3], [*module.PLACE_CENTER, .070])
        np.testing.assert_allclose(controller.transport[4][-1][:3], [*module.PLACE_CENTER, .038])
        self.assertEqual(controller.plan_reports[-1]['place_height_m'], .010)
        self.assertAlmostEqual(controller.plan_reports[-1]['release_world_height_m'], .038)
        self.assertEqual(controller.release_pinch_height_m, .028)
        for height in (-.001, np.nan, np.inf, True):
            with self.subTest(height=height), self.assertRaisesRegex(ValueError, 'place_height_m'):
                self.controller(place_height_m=height)

    def test_unreachable_raised_release_cannot_fall_back_to_table_height(self):
        controller = self.controller(place_height_m=.010, release_pinch_height_m=.028)
        with patch.object(module, 'solve_pinch_ik', side_effect=RuntimeError('No vertical pinch IK candidate')) as solve, \
                patch.object(controller, '_transport_at_height') as route, \
                self.assertRaisesRegex(RuntimeError, 'No vertical pinch IK candidate'):
            controller._compute_transport(np.r_[controller.lift, .015])
        np.testing.assert_allclose(solve.call_args.args[1], [*module.PLACE_CENTER, .038])
        route.assert_not_called()
        self.assertEqual(controller.transport, [])

    def test_release_estimate_uses_raised_support_in_both_rotation_modes(self):
        for mode in ('axis_aligned', 'floor_yaw'):
            with self.subTest(mode=mode):
                controller = self.controller(place_height_m=.010, release_rotation_mode=mode)
                controller.stage, controller.transport_index = 'lower', -1
                controller.payload_relative, controller.payload_rotation = np.zeros(3), np.eye(3)
                controller._fk = Mock(return_value=(np.array([.24, .14, .038]), np.eye(3), np.zeros(3)))
                controller.released_query = Mock(uncertainty_m=.002)
                controller._transition(controller.initial_q.copy(), 40.)
                frozen_center = controller.released_query.freeze.call_args.args[0]
                np.testing.assert_allclose(frozen_center, [.24, .14, .020])
                self.assertEqual(controller.release_record['place_height_m'], .010)
                self.assertEqual(controller.stage, 'release')

    def test_raised_tray_height_is_frozen_for_transport_and_separation_jobs(self):
        controller = self.controller(place_height_m=.010)
        controller.stage, controller.last_elapsed = 'hold', 3.
        controller.payload_relative, controller.payload_rotation = np.zeros(3), np.eye(3)
        job = Mock()
        with patch.object(module, 'AsyncTransportPlanningJob', return_value=job):
            controller._start_transport(np.r_[controller.lift, .015], 3.)
        snapshot = job.start.call_args.args[2]
        self.assertEqual(snapshot.place_height_m, .010)
        self.assertEqual(controller.transport_events[-1]['snapshot']['place_height_m'], .010)
        controller.place_height_m = .020
        with self.assertRaisesRegex(module.ControllerFailure, 'transport_context_changed'):
            controller._check_transport_context()
        self.assertEqual(snapshot.place_height_m, .010)

        controller = self.controller(place_height_m=.010)
        controller.stage = 'release'
        controller.released_query = SimpleNamespace(center=np.array([.24, .14, .020]),
                                                    uncertainty_m=.002, model=object(), rotation=np.eye(3))
        job = Mock()
        with patch.object(module, 'AsyncSeparationPlanningJob', return_value=job):
            controller._start_separation(controller.initial_q.copy(), 40.)
        snapshot = job.start.call_args.args[3]
        self.assertEqual(snapshot.place_height_m, .010)
        self.assertEqual(snapshot.center, (.24, .14, .020))
        self.assertEqual(controller.separation_events[-1]['place_height_m'], .010)
        controller.place_height_m = .020
        with self.assertRaisesRegex(module.ControllerFailure, 'separation_context_changed'):
            controller._check_separation_context()

    def test_lower_transition_requires_complete_route_after_endpoint_ik_precheck(self):
        controller = self.controller(place_xy=[.252, .124])
        def limited_ik(rig, xyz, initial=None):
            if np.allclose(xyz[:2], controller.place_xy) and xyz[2] > .0540001:
                raise RuntimeError('No vertical pinch IK candidate')
            return np.r_[xyz, 0., 0.]
        checked = []
        def payload_valid(q):
            checked.append(np.array(q))
            # The first IK-reachable hover is unsafe. It must not be adopted.
            return not (np.allclose(q[:2], controller.place_xy) and q[2] > .053999)
        controller._payload_valid = payload_valid
        with patch.object(module, 'solve_pinch_ik', side_effect=limited_ik):
            controller._compute_transport(np.r_[controller.lift, .015])
        report = controller.plan_reports[-1]
        self.assertAlmostEqual(report['transition_height_m'], .051)
        self.assertEqual(report['transition_height_reason'], 'lower_certified_route')
        self.assertEqual([row['status'] for row in report['transition_attempts']],
                         ['rejected', 'rejected', 'rejected', 'accepted'])
        self.assertEqual([row['validation_stage'] for row in report['transition_attempts']],
                         ['endpoint_ik', 'endpoint_ik', 'complete_route', 'complete_route'])
        self.assertGreater(len(checked), 100)
        np.testing.assert_allclose(controller.transport[-2][-1][:3], [.252, .124, .051])
        np.testing.assert_allclose(controller.transport[-1][-1][:3], [.252, .124, .023])

    def test_failed_height_search_does_not_commit_partial_paths_or_cancel_fallback(self):
        for failure in ('estimated_payload_route_collision', 'transport_planning_cancelled'):
            with self.subTest(failure=failure):
                controller = self.controller(place_xy=[.252, .124])
                previous = [np.full((2, 5), .7)]
                controller.transport = previous
                controller._payload_valid = Mock(side_effect=module.ControllerFailure(failure))
                with self.assertRaisesRegex(module.ControllerFailure, failure):
                    controller._compute_transport(np.r_[controller.lift, .015])
                self.assertIs(controller.transport, previous)
                self.assertFalse(any(item.get('stage') == 'transport_execution_plan'
                                     for item in controller.plan_reports))
                if failure == 'transport_planning_cancelled':
                    self.assertEqual(controller._payload_valid.call_count, 1)

    def test_async_transport_freezes_place_and_rejects_changed_target_context(self):
        controller = self.controller(place_xy=[.252, .124])
        controller.stage = 'hold'
        controller.last_elapsed = 3.
        controller.payload_relative = np.zeros(3)
        controller.payload_rotation = np.eye(3)
        job = Mock()
        with patch.object(module, 'AsyncTransportPlanningJob', return_value=job):
            controller._start_transport(np.r_[controller.lift, .015], 3.)
        snapshot = job.start.call_args.args[2]
        self.assertEqual(snapshot.place_xy, (.252, .124))
        self.assertEqual(controller.transport_events[-1]['snapshot']['place_xy'], (.252, .124))
        controller.place_xy[0] += .001
        self.assertEqual(snapshot.place_xy, (.252, .124))
        with self.assertRaisesRegex(module.ControllerFailure, 'transport_context_changed'):
            controller._check_transport_context()
        job.reject.assert_called_once_with('transport_context_changed')

    def test_unreachable_new_place_is_not_replaced_by_original_center(self):
        controller = self.controller(place_xy=[.252, .124])
        controller.payload_relative = np.zeros(3)
        controller.payload_rotation = np.eye(3)
        def reject_requested(rig, xyz, initial=None):
            if xyz[0] > .25:
                raise ValueError('requested_place_unreachable')
            return np.r_[xyz, 0., 0.]
        with patch.object(module, 'solve_pinch_ik', side_effect=reject_requested), \
                self.assertRaisesRegex(ValueError, 'requested_place_unreachable'):
            controller._compute_transport(np.r_[controller.lift, .015])
        self.assertFalse(any(report.get('stage') == 'transport_execution_plan'
                             for report in controller.plan_reports))

    def separation_controller(self, distance=.002):
        controller = self.controller()
        controller.released_query = Mock()
        controller.released_query.distances.return_value = {module.PAD_NAMES[0]: distance}
        controller.released_query.pad_vertices.return_value = {module.PAD_NAMES[0]: np.zeros((8, 3))}
        controller.release_record = {}
        return controller

    @staticmethod
    def limited_vertical_ik(rig, xyz, initial=None):
        if xyz[2] > .0942:
            raise RuntimeError('No vertical pinch IK candidate')
        return np.r_[xyz, 0., 0.]

    def test_default_separation_keeps_original_height_and_fourteen_waypoints(self):
        controller = self.separation_controller()
        controller._legacy_plan_separation(controller.initial_q.copy(), 0.)
        record = controller.release_record
        self.assertEqual(len(record['separation_path']), 14)
        self.assertEqual(record['separation_end']['reason'], 'original_vertical_height')
        self.assertEqual(record['separation_end']['height_m'], .037)
        self.assertEqual(controller.stage, 'separate')

    def test_vertical_ik_limit_can_use_only_clear_validated_prefix_and_return(self):
        controller = self.separation_controller()
        with patch.object(module, 'solve_pinch_ik', side_effect=self.limited_vertical_ik):
            controller._legacy_plan_separation(controller.initial_q.copy(), 0.)
        record = controller.release_record
        self.assertEqual(len(record['separation_path']), 13)
        self.assertEqual(record['separation_end']['reason'], 'vertical_ik_limit_after_clearance')
        self.assertAlmostEqual(record['separation_end']['height_m'], .037*12/13)
        self.assertEqual(record['return_method'], 'validated_direct')
        self.assertEqual(controller.stage, 'separate')

    def test_vertical_ik_limit_cannot_accept_a_reachable_but_uncleared_prefix(self):
        controller = self.separation_controller(distance=.0005)
        with patch.object(module, 'solve_pinch_ik', side_effect=self.limited_vertical_ik), \
                patch.object(controller, '_return_path') as return_path, \
                self.assertRaisesRegex(RuntimeError, 'No vertical pinch IK candidate'):
            controller._legacy_plan_separation(controller.initial_q.copy(), 0.)
        return_path.assert_not_called()
        self.assertEqual(controller.release_record, {})

    def test_vertical_ik_limit_cannot_bypass_failed_return_path(self):
        controller = self.separation_controller()
        with patch.object(module, 'solve_pinch_ik', side_effect=self.limited_vertical_ik), \
                patch.object(controller, '_return_path', side_effect=module.ControllerFailure('return_invalid')), \
                self.assertRaisesRegex(module.ControllerFailure, 'return_invalid'):
            controller._legacy_plan_separation(controller.initial_q.copy(), 0.)
        self.assertEqual(controller.release_record, {})

    def test_separation_unknown_backend_error_and_cancel_are_not_ik_fallbacks(self):
        for error in (RuntimeError('unknown_ik_backend_failure'),
                      module.ControllerFailure('separation_planning_cancelled')):
            with self.subTest(error=type(error).__name__):
                controller = self.separation_controller()
                def solve(rig, xyz, initial=None):
                    if xyz[2] > .0942:
                        raise error
                    return np.r_[xyz, 0., 0.]
                with patch.object(module, 'solve_pinch_ik', side_effect=solve), \
                     self.assertRaises(type(error)) as failure:
                    controller._legacy_plan_separation(controller.initial_q.copy(), 0.)
                self.assertIs(failure.exception, error)
                self.assertEqual(controller.release_record, {})

    def test_minimum_jerk_endpoints_and_monotonic_waypoint_progress(self):
        path = np.array([[0., 0, 0, 0, 0], [1., 0, 0, 0, 0], [1., 1., 0, 0, 0]])
        np.testing.assert_array_equal(module.sample_minimum_jerk(path, 0), path[0])
        np.testing.assert_array_equal(module.sample_minimum_jerk(path, 1), path[-1])
        sampled = np.array([module.sample_minimum_jerk(path, t) for t in np.linspace(0, 1, 21)])
        self.assertTrue(np.all(np.diff(sampled[:, :2], axis=0) >= -1e-12))

    def test_observation_expires_before_handover(self):
        c = self.controller()
        c._occlusion_warning = lambda q, elapsed: {'lookahead_s': .5}
        result = c.update(c.initial_q.copy(), np.zeros(6), 1.01)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failure_reason'], 'visual_estimate_expired')
        self.assertFalse(c.target_frozen)

    def test_invalid_image_cannot_trigger_target_freeze(self):
        c = self.controller()
        c._occlusion_warning = lambda q, elapsed: {'lookahead_s': .5}
        q = np.array([.27, -.13, .06, 0, 0, .5])
        result = c.update(q, np.zeros(6), .5, {'valid': False, 'timestamp_s': .5})
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(c.target_frozen)

    def test_occlusion_warning_freezes_prior_valid_estimate_not_current_biased_image(self):
        c = self.controller()
        c._occlusion_warning = lambda q, elapsed: {'lookahead_s': .5}
        q = np.array([.27, -.13, .06, 0, 0, .5])
        result = c.update(q, np.zeros(6), .5,
                          {'valid': True, 'xy': [.245, -.13], 'timestamp_s': .5})
        self.assertEqual(result['status'], 'running')
        self.assertTrue(result['target_frozen'])
        self.assertEqual(c.freeze_record['estimate_timestamp_s'], 0)
        np.testing.assert_array_equal(c.target_xy, [.24, -.13])
        self.assertIn('stationary target', c.freeze_record['assumption'])
        result = c.update(q, np.zeros(6), 2., {'valid': False, 'timestamp_s': 2.})
        self.assertEqual(result['status'], 'running')
        self.assertFalse(result['controller_completion_is_task_success'])

    def test_projection_overlap_and_depth_direction(self):
        calibration = module.TopDownCalibration()
        target = module.projected_box_bounds([.24, -.13, .010], [.011, .011, .0085], calibration)
        aligned = module.projected_box_bounds([.244, -.078, .386], [.006, .006, .006], calibration)
        separated = module.projected_box_bounds([.1, .2, .3], [.006, .006, .006], calibration)
        self.assertTrue(module.bounds_overlap(target, aligned))
        self.assertFalse(module.bounds_overlap(target, separated))
        self.assertIsNone(module.projected_box_bounds([0, 0, 1.1], [.01]*3, calibration))

    def test_occlusion_uses_visible_robot_and_front_depth_not_target_truth(self):
        c = self.controller()
        c.visible_robot_geoms = [0]
        c.rig.geom_rbound = np.array([.006])
        c.rig.geom_bodyid = np.array([1])
        c.rig.body = lambda i: SimpleNamespace(name='forearm')
        c.query.geom_xpos = np.array([[.244, -.078, .386]])
        warning = c._occlusion_warning(c.initial_q, 0.)
        self.assertEqual(warning['body'], 'forearm')
        self.assertEqual(warning['lookahead_s'], 0.)
        c.query.geom_xpos[0] = [.24, -.13, -.02]
        self.assertIsNone(c._occlusion_warning(c.initial_q, 0.))

    def test_future_observation_and_backward_clock_fail(self):
        c = self.controller()
        q = c.initial_q.copy()
        result = c.update(q, np.zeros(6), .5,
                          {'valid': True, 'xy': [.24, -.13], 'timestamp_s': .6})
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failure_reason'], 'stale_or_future_visual_estimate')
        c.failure_reason = None
        result = c.update(q, np.zeros(6), .4)
        self.assertEqual(result['failure_reason'], 'invalid_or_expired_controller_time')

    def test_close_dwell_uses_encoders_not_object_or_grasp_truth(self):
        c = self.controller()
        c.target_frozen = True
        c._set_dwell('close', c.down, .015, 0, 6.)
        q = np.r_[c.down, .2]  # Jaw need not fully close around a hypothetical payload.
        result = c.update(q, np.zeros(6), 6.0)
        self.assertEqual(result['stage'], 'close')
        result = c.update(q, np.zeros(6), 6.61)
        self.assertEqual(result['stage'], 'lift')
        self.assertFalse(result['controller_completion_is_task_success'])
        np.testing.assert_allclose(c.payload_rotation, np.eye(3))

    def test_continuous_jaw_uses_command_endpoints_and_original_dwell(self):
        from route_policy import RoutePolicy
        c = self.controller(route_policy=RoutePolicy(smooth_jaw_dwell=True))
        for stage, start, goal in (('close', .5, .015), ('release', .015, .5)):
            with self.subTest(stage=stage):
                c.last_command[5] = start
                c._set_dwell(stage, c.down, goal, 12., 6.)
                self.assertEqual(c.stage_started, 12.)
                self.assertEqual(c.duration, 6.)
                self.assertEqual(c._jaw_reference(0.), start)
                self.assertEqual(c._jaw_reference(6.), goal)
                self.assertEqual(c._jaw_reference(6.6), goal)
                values = np.array([c._jaw_reference(t) for t in np.arange(301)*.02])
                direction = np.sign(goal-start)
                self.assertTrue(np.all(np.diff(values)*direction >= 0))
                self.assertLessEqual(float(np.max(np.abs(np.diff(values)))),
                                     1.875*abs(goal-start)/6*.02+1e-12)
                self.assertEqual(c._jaw_reference(3.), c._jaw_reference(3.))
                self.assertAlmostEqual(c._jaw_reference(3.), (start+goal)/2)

    def test_original_jaw_step_and_other_stages_are_preserved(self):
        from route_policy import RoutePolicy
        for enabled, stage in ((False, 'close'), (True, 'hold')):
            with self.subTest(enabled=enabled, stage=stage):
                c = self.controller(route_policy=RoutePolicy(smooth_jaw_dwell=enabled))
                c.last_command[5] = .5
                c._set_dwell(stage, c.down, .015, 0., 6.)
                for age in (0., 1., 3., 6.):
                    self.assertEqual(c._jaw_reference(age), .015)

    def test_loaded_jaw_latches_once_after_lift_with_original_dwell_and_stage_scope(self):
        from route_policy import RoutePolicy
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                c = self.controller(route_policy=RoutePolicy(loaded_jaw_preload=enabled))
                self.assertEqual(c.sweep_reports[0]['checked_states'], 244)
                c.stage, c.last_command = 'lift', np.r_[c.lift, .015]
                c._transition(np.r_[c.lift, .121], 1.)
                self.assertEqual(c.duration, 1.5)
                if not enabled:
                    self.assertFalse(hasattr(c, '_loaded_jaw_target'))
                    self.assertEqual(c.jaw, .015)
                    continue
                self.assertEqual(c._loaded_jaw_target, .068)
                self.assertEqual(c._jaw_reference(0.), .015)
                self.assertEqual(c._jaw_reference(1.5), .068)
                values = [c._jaw_reference(t) for t in np.linspace(0., 1.5, 76)]
                self.assertTrue(all(a <= b for a, b in zip(values, values[1:])))
                c.stage = 'lift'
                c._transition(np.r_[c.lift, .4], 4.)
                self.assertEqual(c._loaded_jaw_target, .068)
                for stage, request, expected in [('hold', .015, .068), ('transport', .015, .068),
                                                  ('lower', .015, .068), ('release', .5, .5),
                                                  ('descend', .5, .5), ('retreat', .5, .5)]:
                    c.stage = stage
                    c._set_motion([c.lift, c.lift], request, 5.)
                    self.assertEqual(c.jaw, expected)

    def test_loaded_jaw_ramp_keeps_interior_collision_guard(self):
        from route_policy import RoutePolicy
        c = self.controller(route_policy=RoutePolicy(loaded_jaw_preload=True))
        c.stage, c.last_command, c.target_frozen = 'lift', np.r_[c.lift, .015], True
        q = np.r_[c.lift, .121]
        c._transition(q, 1.)
        c._payload_valid = lambda q5: True
        c.checker.evaluate.side_effect = lambda q6, **kw: {'valid': not .09 < q6[5] < .10}
        result = c.update(q, np.zeros(6), 1.75)
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(c.last_sweep_report['valid'])
        self.assertEqual(c.last_sweep_report['jaw_resolution_rad'], .002)
        self.assertGreater(c.last_sweep_report['checked_states'], 1)

    def test_continuous_close_keeps_full_measured_closure_precheck(self):
        from route_policy import RoutePolicy
        c = self.controller(route_policy=RoutePolicy(smooth_jaw_dwell=True, loaded_jaw_preload=True))
        c.target_frozen = True
        q = np.r_[c.down, .5]
        c.last_command = q.copy()
        c.stage = 'descend'
        c._set_motion([c.down, c.down], .5, 0.)
        result = c.update(q, np.zeros(6), c.duration+.6)
        self.assertEqual(result['stage'], 'close')
        self.assertEqual(result['status'], 'running')
        self.assertEqual(result['command'][5], .5)
        self.assertEqual(c.sweep_reports[-1]['stage'], 'measured_closure')
        self.assertEqual(c.sweep_reports[-1]['checked_states'], 244)
        self.assertEqual(c.last_sweep_report['checked_states'], 2)
        self.assertFalse(hasattr(c, '_loaded_jaw_target'))

    def test_continuous_jaw_still_rejects_collision_inside_actual_command_chord(self):
        from route_policy import RoutePolicy
        c = self.controller(route_policy=RoutePolicy(smooth_jaw_dwell=True))
        c.target_frozen = True
        q = np.r_[c.down, .5]
        c.last_command = q.copy()
        c._set_dwell('close', c.down, .015, 0., 6.)
        checked = []
        def validity(pose, **kwargs):
            checked.append(np.asarray(pose).copy())
            return {'valid': not .36 < pose[5] < .37}
        c.checker.evaluate.side_effect = validity
        result = c.update(q, np.zeros(6), 3.)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failure_reason'], 'current_pose_command_chord_invalid')
        self.assertTrue(any(.36 < pose[5] < .37 for pose in checked))
        self.assertEqual(c.last_sweep_report['jaw_resolution_rad'], .002)
        np.testing.assert_array_equal(c.last_command, q)

    def test_continuous_close_does_not_shorten_original_encoder_wait(self):
        from route_policy import RoutePolicy
        c = self.controller(route_policy=RoutePolicy(smooth_jaw_dwell=True))
        c.target_frozen = True
        c._set_dwell('close', c.down, .015, 0., 6.)
        q = np.r_[c.down, .12]
        self.assertEqual(c.update(q, np.zeros(6), 6.)['stage'], 'close')
        self.assertEqual(c.update(q, np.zeros(6), 6.61)['stage'], 'lift')

    def test_continuous_release_prefetch_requires_open_jaw_and_stable_bound_command(self):
        from route_policy import RoutePolicy
        c = self.controller(route_policy=RoutePolicy(smooth_jaw_dwell=True))
        c.target_frozen = True
        c.last_command = np.r_[c.down, .015]
        c._set_dwell('release', c.down, .5, 0., 6.)
        def start(q6, elapsed):
            c.separation_request_binding = c._separation_binding()
            c.separation_job = Mock()
        c._start_separation = Mock(side_effect=start)
        c._poll_separation = Mock(return_value=False)
        result = c.update(np.r_[c.down, .12], np.zeros(6), 3.)
        self.assertEqual(result['status'], 'running')
        self.assertAlmostEqual(result['command'][5], .2575)
        c._start_separation.assert_not_called()
        c._poll_separation.assert_not_called()
        result = c.update(np.r_[c.down, .4511], np.zeros(6), 4.)
        self.assertEqual(result['stage'], 'release')
        c._start_separation.assert_not_called()
        c.update(np.r_[c.down, .4511], np.zeros(6), 6.)
        c._start_separation.assert_not_called()  # Previous issued command still evolves.
        c.update(np.r_[c.down, .4491], np.zeros(6), 6.02)
        c._start_separation.assert_not_called()  # Original measured-open gate remains.
        c.update(np.r_[c.down, .4511], np.zeros(6), 6.04)
        c._start_separation.assert_called_once()
        c._poll_separation.assert_called_once()
        result = c.update(np.r_[c.down, .4511], np.zeros(6), 6.06)
        self.assertEqual(result['status'], 'running')
        c.separation_job.reject.assert_not_called()  # Real full binding passes next tick.

    def test_uncertain_payload_envelope_preserves_point_two_mm_margin(self):
        c = self.controller()
        c.payload_relative = np.zeros(3)
        c.payload_rotation = np.eye(3)
        c._fk = lambda q: (np.array([0., 0., .020]), np.eye(3), np.zeros(3))
        c.world = [('wall', int(module.mujoco.mjtGeom.mjGEOM_BOX),
                    np.array([.0211, 0., .020]), np.eye(3), np.array([.01, .1, .1]))]
        # .0211 - .009 - .002 - .010 = .0001, less than the .0002 margin.
        self.assertFalse(c._payload_valid(np.zeros(5)))
        c.world[0] = ('wall', int(module.mujoco.mjtGeom.mjGEOM_BOX),
                      np.array([.0213, 0., .020]), np.eye(3), np.array([.01, .1, .1]))
        self.assertTrue(c._payload_valid(np.zeros(5)))

    def test_replan_is_bounded_and_forbidden_after_handover(self):
        c = self.controller()
        c.replans = 3
        with self.assertRaisesRegex(module.ControllerFailure, 'replan_budget'):
            c.replan_approach(c.initial_q, 0,
                             {'valid': True, 'xy': [.24, -.13], 'timestamp_s': 0})
        c.target_frozen = True
        with self.assertRaisesRegex(module.ControllerFailure, 'outside_visible'):
            c.replan_approach(c.initial_q, 0, None)

    def test_return_shortcut_cannot_cut_through_obstacle(self):
        points=np.array([[0.,0,0,0,0],[0,1.,0,0,0],[1.,1.,0,0,0],[1.,0,0,0,0]])
        valid=lambda q: not (.2<q[0]<.8 and q[1]<.8)
        result=module.shorten_path(points,valid)
        self.assertGreater(len(result),2)
        self.assertTrue(module.validate_joint_path(result,valid,.005)['valid'])
        clear=module.shorten_path(points,lambda q:True)
        np.testing.assert_array_equal(clear,points[[0,-1]])

    def test_separation_cannot_return_below_recorded_high_water(self):
        c=self.controller();q=c.initial_q
        c.separation_pinch=q[:3].copy()
        c.separation_floors={'pad_gripper':-.00105}
        c.separation_vertices={'pad_gripper':np.zeros((8,3))}
        c.separation_high_z={'pad_gripper':np.full(8,.002)}
        c.released_query=Mock()
        c.released_query.distances.return_value={'pad_gripper':-.001}
        c.released_query.pad_vertices.return_value={'pad_gripper':np.tile([0,0,.0005],(8,1))}
        self.assertFalse(c._separation_valid(q[:5]))
        c.released_query.pad_vertices.return_value={'pad_gripper':np.tile([0,0,.002],(8,1))}
        self.assertTrue(c._separation_valid(q[:5]))
        self.assertFalse(c._released_valid(q[:5]))  # No contact exception on return.

    def test_continuous_phase_preserves_setpoint_without_treating_it_as_pose(self):
        c=self.controller();q=c.initial_q.copy();c.target_frozen=True
        offset=np.array([.0001,-.00056,-.00031,0,.00005])
        previous=q.copy();previous[:5]+=offset;c.last_command=previous.copy()
        c.stage='retreat'
        c._set_continuous_motion([q[:5],q[:5]+.01],0)
        # The setpoint may differ from a collision-free achieved pose under load.
        # This predicate permits only the geometric start, not the servo target.
        c._released_valid=lambda pose,jaw=.5: np.allclose(pose,q[:5],rtol=0,atol=1e-12)
        result=c.update(q,np.zeros(6),0)
        self.assertEqual(result['status'],'running')
        np.testing.assert_array_equal(result['command'],previous)
        np.testing.assert_array_equal(result['geometric_reference'],q)
        np.testing.assert_allclose(result['command'][:5]-q[:5],offset,atol=1e-17)
        c._released_valid=lambda pose,jaw=.5:True
        result=c.update(q,np.zeros(6),.02)
        np.testing.assert_array_equal(result['servo_offset'],previous[:5]-q[:5])
        self.assertGreater(np.linalg.norm(result['geometric_reference']-q),0)

    def transport_leg_controller(self, *, refresh=False, next_start_offset=0.):
        from route_policy import RoutePolicy
        c = self.controller(route_policy=RoutePolicy(refresh_leg_age=refresh))
        c.target_frozen = True
        q = c.initial_q.copy()
        q[5] = .015
        start, end = q[:5].copy(), q[:5]+.1
        previous = np.array([start-.02, start])
        c.transport = [previous, np.array([start+next_start_offset, end]),
                       np.array([end, end+.1])]
        c.transport_index = 0
        c.stage = 'transport'
        c._set_motion(previous, .015, 0.)
        c._payload_valid = lambda pose: True
        return c, q, end

    def test_same_stage_transport_starts_the_new_leg_at_its_beginning(self):
        c, q, _ = self.transport_leg_controller(refresh=True)
        elapsed = c.duration+.6
        first = c.update(q, np.zeros(6), elapsed)
        self.assertEqual(first['status'], 'running')
        self.assertEqual(first['stage'], 'transport')
        self.assertEqual(c.transport_index, 1)
        self.assertEqual(c.stage_started, elapsed)
        np.testing.assert_array_equal(first['geometric_reference'], q)
        following = c.update(q, np.zeros(6), elapsed+.02)
        movement = following['geometric_reference'][:5]-q[:5]
        self.assertTrue(np.all(movement > 0))
        self.assertLess(float(np.max(movement)), .00001)

    def test_legacy_same_stage_transport_remains_explicitly_reproducible(self):
        c, q, end = self.transport_leg_controller(refresh=False)
        first = c.update(q, np.zeros(6), c.duration+.6)
        np.testing.assert_array_equal(first['geometric_reference'][:5], end)

    def test_clock_candidate_preserves_samples_without_a_leg_change(self):
        legacy, q, _ = self.transport_leg_controller(refresh=False)
        child, _, _ = self.transport_leg_controller(refresh=True)
        for elapsed in (.02, .8, 1.6):
            left = legacy.update(q, np.zeros(6), elapsed)
            right = child.update(q, np.zeros(6), elapsed)
            self.assertEqual(left['status'], right['status'])
            np.testing.assert_array_equal(left['geometric_reference'], right['geometric_reference'])
            np.testing.assert_array_equal(left['command'], right['command'])
            self.assertEqual(legacy.transport_index, child.transport_index)

    def test_new_leg_begin_still_runs_the_original_configuration_sweep(self):
        c, q, _ = self.transport_leg_controller(refresh=True, next_start_offset=.01)
        checked = []
        def validity(pose, **kwargs):
            checked.append(np.asarray(pose).copy())
            return {'valid': pose[0] <= q[0]+.005}
        c.checker.evaluate.side_effect = validity
        result = c.update(q, np.zeros(6), c.duration+.6)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failure_reason'], 'current_pose_command_chord_invalid')
        self.assertGreater(len(checked), 1)
        self.assertTrue(any(pose[0] > q[0]+.005 for pose in checked))

    def test_phase_bias_is_recaptured_once_and_retained_through_settle(self):
        c=self.controller();c.target_frozen=True
        q=c.initial_q.copy();q[:5]+=.01
        c.last_command=q.copy();c.last_command[:5]+=.0005
        c.stage='retreat';c._set_continuous_motion([q[:5],c.initial_q[:5]],0)
        c._released_valid=lambda pose,jaw=.5:True
        terminal=c.update(c.initial_q.copy(),np.zeros(6),c.duration-.01)['command']
        terminal=c.update(c.initial_q.copy(),np.zeros(6),c.duration+.01)['command']
        result=c.update(c.initial_q.copy(),np.zeros(6),c.duration+.61)
        self.assertEqual(result['stage'],'settle')
        np.testing.assert_array_equal(result['command'],terminal)
        result=c.update(c.initial_q.copy(),np.zeros(6),c.stage_started+c.duration+.61)
        self.assertTrue(result['done'])
        np.testing.assert_array_equal(result['command'],terminal)
        repeated=c.update(c.initial_q.copy(),np.zeros(6),c.last_elapsed+.02)
        np.testing.assert_array_equal(repeated['command'],terminal)
        expired=c.update(c.initial_q.copy(),np.zeros(6),90.02)
        self.assertEqual(expired['status'],'done')
        np.testing.assert_array_equal(expired['command'],terminal)

    def test_large_bias_or_mapped_limit_violation_is_rejected_without_clipping(self):
        c=self.controller();q=c.initial_q.copy();c.stage='separate'
        c.last_command=q.copy();c.last_command[0]+=.00301
        with self.assertRaisesRegex(module.ControllerFailure,'servo_offset_exceeds'):
            c._set_continuous_motion([q[:5],q[:5]+.1],0)
        c.last_command=q.copy();c.last_command[0]+=.002
        goal=q[:5].copy();goal[0]=2.999
        with self.assertRaisesRegex(module.ControllerFailure,'out_of_bounds'):
            c._set_continuous_motion([q[:5],goal],0)


if __name__ == '__main__':
    unittest.main()
