"""Approach shortcut regressions with explicit obstacles; no physics or native queries."""

import copy
import json
import unittest
from unittest.mock import patch

import numpy as np

import test_visual_grasp_controller as fixtures
import visual_grasp_controller as module


class ApproachShortcutTests(unittest.TestCase):
    def controller(self):
        controller = fixtures.VisualControllerTests.controller(self)
        controller.checker.evaluate.return_value = {'valid': True, 'min_distance_m': .003}
        return controller

    @staticmethod
    def detour():
        return np.array([[0., 0., 0., 0., 0.],
                         [0., 1., 0., 0., 0.],
                         [1., 1., 0., 0., 0.],
                         [1., 0., 0., 0., 0.]])

    @staticmethod
    def corridor(q):
        # A U-shaped free corridor. Each original edge is free; chords cross its obstacle.
        return q[0] <= .05 or q[1] >= .95 or q[0] >= .95

    def test_clear_shortcut_keeps_exact_endpoints_and_raw_path(self):
        raw = self.detour()
        original = raw.copy()
        report = {}
        result = module.shorten_path(raw, lambda q: True, shortcut_valid=None, report=report)
        np.testing.assert_array_equal(result, original[[0, -1]])
        np.testing.assert_array_equal(raw, original)
        self.assertLess(module.motion_duration(result), module.motion_duration(raw))
        self.assertEqual(report['max_candidate_edges'], 128)
        self.assertEqual(report['accepted_shortcuts'], 1)
        self.assertEqual(report['raw_fallback_edges'], 0)

    def test_strict_rejection_keeps_raw_edges_and_final_original_predicate(self):
        raw = self.detour()
        strict_seen, final_seen = [], []
        report = {}
        result = module.shorten_path(
            raw, lambda q: final_seen.append(q) or self.corridor(q),
            shortcut_valid=lambda q: strict_seen.append(q) or False, report=report)
        np.testing.assert_array_equal(result, raw)
        self.assertEqual(report['raw_fallback_edges'], 3)
        self.assertEqual(report['accepted_shortcuts'], 0)
        self.assertEqual(len(strict_seen), report['candidate_checked_states'])
        self.assertEqual(len(final_seen), report['final_validation']['checked_states'])
        self.assertEqual(final_seen[0], raw[0].tolist())
        self.assertEqual(final_seen[-1], raw[-1].tolist())
        self.assertTrue(report['final_validation']['valid'])

    def test_strict_acceptance_cannot_bypass_original_final_collision(self):
        report = {}
        with self.assertRaisesRegex(module.ControllerFailure, '^shortened_return_path_invalid$'):
            module.shorten_path(self.detour(), self.corridor,
                                shortcut_valid=lambda q: True, report=report)
        self.assertTrue(report['attempts'][0]['validation']['valid'])
        self.assertEqual(report['accepted_shortcuts'], 1)
        self.assertFalse(report['final_validation']['valid'])
        self.assertTrue(.05 < report['final_validation']['invalid_state'][0] < .95)

    def test_infeasible_chords_preserve_the_collision_free_original_route(self):
        raw = self.detour()
        self.assertTrue(module.validate_joint_path(raw, self.corridor, .005)['valid'])
        self.assertFalse(module.validate_joint_path(raw[[0, -1]], self.corridor, .005)['valid'])
        result = module.shorten_path(raw, self.corridor)
        np.testing.assert_array_equal(result, raw)
        self.assertTrue(module.validate_joint_path(result, self.corridor, .005)['valid'])

    def test_candidate_budget_zero_and_one_still_recheck_the_whole_route(self):
        raw = self.detour()
        validate = module.validate_joint_path
        for budget in (0, 1):
            with self.subTest(max_checks=budget):
                calls = []

                def observed(points, valid, resolution):
                    calls.append((np.asarray(points).copy(), resolution))
                    return validate(points, valid, resolution)

                with patch.object(module, 'validate_joint_path', side_effect=observed):
                    report = {}
                    result = module.shorten_path(raw, self.corridor, max_checks=budget, report=report)
                np.testing.assert_array_equal(result, raw)
                self.assertEqual(len(calls), budget + 1)
                np.testing.assert_array_equal(calls[-1][0], raw)
                self.assertTrue(all(resolution == .005 for _, resolution in calls))
                self.assertEqual(report['max_candidate_edges'], budget)
                self.assertEqual(report['candidate_edges_attempted'], budget)
                self.assertEqual(len(report['attempts']), budget)
                self.assertTrue(report['final_validation']['valid'])
                self.assertEqual(report['total_checked_states'],
                                 report['candidate_checked_states'] + report['final_validation']['checked_states'])
                if budget:
                    np.testing.assert_array_equal(calls[0][0], raw[[0, -1]])

    def test_every_accepted_candidate_and_the_final_path_are_revalidated(self):
        raw = self.detour()
        calls = []
        validate = module.validate_joint_path

        def observed(points, valid, resolution):
            calls.append(np.asarray(points).copy())
            self.assertEqual(resolution, .005)
            return validate(points, valid, resolution)

        with patch.object(module, 'validate_joint_path', side_effect=observed):
            result = module.shorten_path(raw, lambda q: True)
        self.assertEqual(len(calls), 2)
        np.testing.assert_array_equal(calls[0], raw[[0, -1]])
        np.testing.assert_array_equal(calls[-1], result)

    def test_final_recheck_rejection_is_not_hidden_by_an_accepted_candidate(self):
        # A checker can reject the final recheck even if its earlier edge check passed.
        # The shortcut must surface that rejection rather than execute the edge.
        validate = module.validate_joint_path
        evaluations = 0

        def valid(q):
            nonlocal evaluations
            if np.array_equal(q, self.detour()[0]):
                evaluations += 1
            return evaluations == 1

        with self.assertRaises(module.ControllerFailure):
            module.shorten_path(self.detour(), valid)
        self.assertEqual(evaluations, 2)

    def test_report_uses_measured_wall_time_and_retains_actual_validation_counts(self):
        report = {}
        seen = []
        with patch.object(module.time, 'perf_counter', side_effect=[123., 123.125]):
            result = module.shorten_path(self.detour(), lambda q: seen.append(q) or True, report=report)
        np.testing.assert_array_equal(result, self.detour()[[0, -1]])
        self.assertEqual(report['wall_s'], .125)
        self.assertEqual(report['candidate_edges_attempted'], 1)
        self.assertEqual(report['total_checked_states'], len(seen))
        attempt = report['attempts'][0]
        self.assertEqual((attempt['start_index'], attempt['end_index']), (0, 3))
        self.assertTrue(attempt['validation']['valid'])
        self.assertTrue(report['final_validation']['valid'])
        # Match the existing planner test's allowance for interpolation roundoff.
        # This tolerance applies only to the recorded measurement, not its resolution input.
        self.assertEqual(attempt['validation']['resolution_rad'], .005)
        self.assertEqual(report['final_validation']['resolution_rad'], .005)
        self.assertLessEqual(attempt['validation']['max_sample_step_rad'], .005 + 1e-12)
        self.assertLessEqual(report['final_validation']['max_sample_step_rad'], .005 + 1e-12)
        json.dumps(report, allow_nan=False)

    def approach_plan(self, controller):
        start, goal = controller.initial_q[:5].copy(), controller.approach.copy()
        first, second = start.copy(), goal.copy()
        first[3] = second[3] = 1.
        path = np.array([start, first, second, goal])
        return {'status': 'solved', 'path': path.tolist(), 'exact_solution': True,
                'resolution_rad': .015, 'planning_seconds': .25, 'elapsed_seconds': .4}

    def test_candidate_reserve_requires_finite_certificate_at_exact_two_mm(self):
        controller = self.controller()
        q5 = controller.initial_q[:5].copy()
        for certificate, expected in (
            ({'valid': True, 'min_distance_m': .002}, True),
            ({'valid': True, 'min_distance_m': np.nextafter(.002, -np.inf)}, False),
            ({'valid': True, 'min_distance_m': .0015}, False),
            ({'valid': False, 'min_distance_m': .003}, False),
            ({'valid': True}, False),
            ({'valid': True, 'min_distance_m': None}, False),
            ({'valid': True, 'min_distance_m': np.nan}, False),
            ({'valid': True, 'min_distance_m': np.inf}, False),
            ({'valid': True, 'min_distance_m': -np.inf}, False),
        ):
            with self.subTest(certificate=certificate):
                controller.checker.evaluate.return_value = certificate
                self.assertEqual(controller._approach_shortcut_valid(q5), expected)
                args, kwargs = controller.checker.evaluate.call_args
                np.testing.assert_array_equal(args[0], np.r_[q5, .5])
                self.assertFalse(kwargs['require_fixed_gripper'])
                self.assertEqual(kwargs['certificate_margin_m'], .002)

    def test_candidate_reserve_does_not_tighten_the_original_raw_path_final_gate(self):
        controller = self.controller()
        controller.checker.evaluate.return_value = {'valid': True, 'min_distance_m': .0015}
        plan = self.approach_plan(controller)
        raw = copy.deepcopy(plan)
        with patch.object(module, 'plan_joint_path', return_value=plan):
            controller._plan_approach(controller.initial_q[:5])
        np.testing.assert_array_equal(controller.approach_path, raw['path'])
        self.assertEqual(controller.plan_reports[-2], raw)
        execution = controller.plan_reports[-1]
        self.assertEqual(execution['arm_margin_m'], .001)
        self.assertEqual(execution['shortcut_candidate_margin_m'], .002)
        self.assertEqual(execution['final_min_certified_bound_m'], .0015)
        self.assertEqual(execution['shortcut']['max_candidate_edges'], 512)
        self.assertEqual(execution['shortcut']['raw_fallback_edges'], 3)
        self.assertEqual(execution['shortcut']['accepted_shortcuts'], 0)
        self.assertTrue(execution['shortcut']['final_validation']['valid'])
        self.assertTrue(all(not a['validation']['valid'] for a in execution['shortcut']['attempts']))
        self.assertEqual(execution['raw_motion_duration_s'], execution['executed_motion_duration_s'])
        json.dumps(execution, allow_nan=False)

    def test_approach_uses_open_jaw_shortcut_without_overwriting_raw_planner_evidence(self):
        controller = self.controller()
        plan = self.approach_plan(controller)
        raw = copy.deepcopy(plan)
        actual_shortcut = module.shorten_path
        attempted = []

        def observe(points, valid, **kwargs):
            self.assertEqual(kwargs['max_checks'], 512)
            self.assertIs(kwargs['shortcut_valid'].__self__, controller)
            self.assertIs(kwargs['shortcut_valid'].__func__, module.VisualGraspController._approach_shortcut_valid)
            for q in (points[0], points[-1]):
                self.assertTrue(valid(q))
                args, call_kwargs = controller.checker.evaluate.call_args
                np.testing.assert_array_equal(args[0], np.r_[q, .5])
                self.assertFalse(call_kwargs['require_fixed_gripper'])
                self.assertNotIn('certificate_margin_m', call_kwargs)
                self.assertTrue(kwargs['shortcut_valid'](q))
                self.assertEqual(controller.checker.evaluate.call_args.kwargs['certificate_margin_m'], .002)
            attempted.append(np.asarray(points).copy())
            return actual_shortcut(points, valid, **kwargs)

        controller.sweep_reports.clear()
        with patch.object(module, 'plan_joint_path', return_value=plan), \
                patch.object(module, 'shorten_path', side_effect=observe):
            controller._plan_approach(controller.initial_q[:5])
        self.assertEqual(len(attempted), 1)
        np.testing.assert_array_equal(attempted[0], raw['path'])
        np.testing.assert_array_equal(controller.approach_path, np.asarray(raw['path'])[[0, -1]])
        self.assertEqual(controller.plan_reports[-2], raw)
        execution = controller.plan_reports[-1]
        self.assertEqual(execution['stage'], 'approach_execution')
        self.assertEqual(execution['method'], 'bounded_validated_shortcuts')
        self.assertEqual(execution['jaw_rad'], .5)
        self.assertEqual(execution['arm_margin_m'], .001)
        self.assertEqual(execution['shortcut_candidate_margin_m'], .002)
        self.assertEqual(execution['final_min_certified_bound_m'], .003)
        self.assertEqual(execution['shortcut']['max_candidate_edges'], 512)
        self.assertEqual(execution['raw_waypoint_count'], 4)
        self.assertAlmostEqual(execution['raw_path_length_rad'], 2.27)
        self.assertAlmostEqual(execution['raw_motion_duration_s'], 2.27 * 1.875 / .3)
        self.assertEqual(execution['executed_waypoint_count'], 2)
        self.assertAlmostEqual(execution['executed_path_length_rad'], .27)
        self.assertEqual(execution['executed_motion_duration_s'], 2.)
        np.testing.assert_array_equal(execution['executed_path'], controller.approach_path)
        self.assertTrue(execution['shortcut']['final_validation']['valid'])
        self.assertGreaterEqual(execution['shortcut']['wall_s'], 0.)
        controller._set_motion(controller.approach_path, .5, 0.)
        self.assertEqual(controller.duration, 2.)
        closure = controller.sweep_reports[-1]
        self.assertEqual(closure['stage'], 'planned_closure')
        self.assertTrue(closure['valid'])
        self.assertEqual(closure['checked_states'], 244)
        json.dumps(controller.plan_reports[-1], allow_nan=False)

    def test_approach_retains_detour_when_the_direct_edge_is_blocked(self):
        controller = self.controller()
        plan = self.approach_plan(controller)
        raw = np.asarray(plan['path'])
        start, goal = raw[0], raw[-1]

        def geometry(q, **kwargs):
            valid = q[1] >= start[1] - .01 or q[3] >= .95 or q[1] <= goal[1] + .01
            return {'valid': valid, 'min_distance_m': .003 if valid else -.001}

        controller.checker.evaluate.side_effect = geometry
        self.assertTrue(module.validate_joint_path(raw, lambda q: controller._arm_valid(q, .5), .005)['valid'])
        self.assertFalse(module.validate_joint_path(raw[[0, -1]], lambda q: controller._arm_valid(q, .5), .005)['valid'])
        with patch.object(module, 'plan_joint_path', return_value=plan):
            controller._plan_approach(controller.initial_q[:5])
        np.testing.assert_array_equal(controller.approach_path, raw)
        controller._set_motion(controller.approach_path, .5, 0.)
        # The known 1 + .27 + 1 rad route still determines its execution time.
        self.assertAlmostEqual(controller.duration, 2.27 * 1.875 / .3)
        execution = controller.plan_reports[-1]
        self.assertEqual(execution['raw_waypoint_count'], execution['executed_waypoint_count'])
        self.assertEqual(execution['raw_path_length_rad'], execution['executed_path_length_rad'])
        self.assertEqual(execution['raw_motion_duration_s'], execution['executed_motion_duration_s'])
        self.assertTrue(all(not attempt['validation']['valid']
                            for attempt in execution['shortcut']['attempts']))

    def test_controller_names_final_recheck_failure_and_records_rejected_execution(self):
        controller = self.controller()
        plan = self.approach_plan(controller)
        actual_shortcut = module.shorten_path

        def final_collision(points, valid, **kwargs):
            return actual_shortcut(points, lambda q: False, **kwargs)

        with patch.object(module, 'plan_joint_path', return_value=plan), \
                patch.object(module, 'shorten_path', side_effect=final_collision):
            with self.assertRaisesRegex(module.ControllerFailure, '^approach_shortcut_final_path_invalid$') as caught:
                module.VisualGraspController(controller.rig, controller.target_xy, controller.initial_q)
        failure = caught.exception
        self.assertEqual(failure.initialization_planning[-2], plan)
        self.assertIs(failure.initialization_checker, controller.checker)
        closure = failure.initialization_sweeps[-1]
        self.assertEqual(closure['stage'], 'planned_closure')
        self.assertTrue(closure['valid'])
        self.assertEqual(closure['checked_states'], 244)
        execution = failure.initialization_planning[-1]
        self.assertEqual(execution['failure_reason'], 'shortened_return_path_invalid')
        self.assertTrue(execution['shortcut']['attempts'][0]['validation']['valid'])
        self.assertFalse(execution['shortcut']['final_validation']['valid'])
        self.assertNotIn('executed_path', execution)
        json.dumps({'planning': failure.initialization_planning,
                    'sweeps': failure.initialization_sweeps}, allow_nan=False)

    def test_callback_error_preserves_initialization_evidence_and_original_cause(self):
        controller = self.controller()
        plan = self.approach_plan(controller)
        raw = copy.deepcopy(plan)
        actual_shortcut = module.shorten_path
        backend_error = RuntimeError('independent collision backend failed')

        def broken_callback(points, valid, **kwargs):
            def broken(q):
                raise backend_error

            return actual_shortcut(points, broken, **kwargs)

        with patch.object(module, 'plan_joint_path', return_value=plan), \
                patch.object(module, 'shorten_path', side_effect=broken_callback):
            with self.assertRaisesRegex(module.ControllerFailure, '^approach_shortcut_validation_error$') as caught:
                module.VisualGraspController(controller.rig, controller.target_xy, controller.initial_q)
        failure = caught.exception
        self.assertIs(failure.__cause__, backend_error)
        self.assertEqual(failure.initialization_planning[-2], raw)
        self.assertIs(failure.initialization_checker, controller.checker)
        execution = failure.initialization_planning[-1]
        self.assertEqual(execution['failure_reason'], str(backend_error))
        self.assertNotIn('executed_path', execution)
        self.assertNotIn('final_validation', execution['shortcut'])
        self.assertEqual(failure.initialization_sweeps[-1]['checked_states'], 244)
        json.dumps({'planning': failure.initialization_planning,
                    'sweeps': failure.initialization_sweeps}, allow_nan=False)

    def test_transport_metadata_preserves_five_original_legs_and_motion_timing(self):
        controller = self.controller()
        controller.last_elapsed = 11.5
        controller._payload_valid = lambda q: True
        q6 = np.r_[controller.lift, .015]
        original_q = q6.copy()
        expected_centers = np.array([[.24, -.13, .06], [.18, -.13, .06],
                                     [.18, 0., .06], [.18, .14, .06],
                                     [.24, .14, .06], [.24, .14, .023]])
        controller._plan_transport(q6)
        np.testing.assert_array_equal(q6, original_q)
        self.assertEqual(len(controller.transport), 5)
        self.assertEqual(controller.transport_index, 0)
        report = controller.plan_reports[-1]
        self.assertEqual(report['stage'], 'transport_execution_plan')
        self.assertEqual(report['planned_at_s'], 11.5)
        self.assertEqual(len(report['legs']), 5)
        lengths = [.06, .13, .14, .06, .037]
        for index, (points, leg) in enumerate(zip(controller.transport, report['legs'])):
            np.testing.assert_array_equal(points[0][:3], expected_centers[index])
            np.testing.assert_array_equal(points[-1][:3], expected_centers[index + 1])
            np.testing.assert_array_equal(points[:, 3:], np.zeros((len(points), 2)))
            np.testing.assert_array_equal(leg['path'], points)
            self.assertEqual(leg['index'], index)
            self.assertEqual(leg['stage'], 'lower' if index == 4 else 'transport')
            self.assertEqual(leg['waypoint_count'], len(points))
            self.assertAlmostEqual(leg['path_length_rad'], lengths[index])
            self.assertEqual(leg['motion_duration_s'], 2.)
            self.assertEqual(leg['arrival_guard_s'], .6)
            self.assertLessEqual(np.linalg.norm(np.diff(points, axis=0), axis=1).max(), .003 + 1e-12)
        self.assertEqual(report['motion_and_arrival_s'], 13.)
        self.assertEqual(report['budget_finish_lower_bound_s'], 38.5)
        self.assertIn('necessary only', report['budget_note'])
        json.dumps(report, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
