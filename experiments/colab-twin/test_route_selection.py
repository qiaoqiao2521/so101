"""Pure route-selection contracts: synthetic certified paths, no model or physics."""
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

from evaluate_station import evaluate
from route_policy import RoutePolicy, load_route_policy
from station_executor import atomic_json
from transport_worker import TransportSnapshot
from visual_grasp_controller import ControllerFailure, VisualGraspController


class RouteSelectionTests(unittest.TestCase):
    def setUp(self):
        # Any accidental native data construction fails this pure-software suite.
        blocker = patch('visual_grasp_controller.mujoco.MjData',
                        side_effect=AssertionError('No native data in route contracts'))
        blocker.start()
        self.addCleanup(blocker.stop)
        blocker = patch('visual_grasp_controller.mujoco.MjModel')
        model = blocker.start()
        self.addCleanup(blocker.stop)
        model.from_xml_path.side_effect = AssertionError('No model compilation')
        model.from_xml_string.side_effect = AssertionError('No model compilation')
        self.controller = VisualGraspController.__new__(VisualGraspController)
        self.controller.route_policy = RoutePolicy()
        self.controller.place_xy = np.array([.22, .17])
        self.controller.place_height_m = 0.
        self.controller.release_pinch_height_m = .028
        self.controller.last_elapsed = 3.
        self.controller.plan_reports = []
        self.controller._fk = Mock(return_value=(None, None, np.array([.24, -.13, .06])))
        self.controller._route_ik = Mock(return_value=np.zeros(5))
        self.controller._transport_at_height = Mock(side_effect=lambda *args: self.paths(.8))

    @staticmethod
    def paths(distance):
        return [np.array([[0., 0., 0., 0., 0.], [distance, 0., 0., 0., 0.]])
                for _ in range(5)]

    def compute(self, **preferences):
        self.controller.route_policy = RoutePolicy(**preferences)
        self.controller._compute_transport(np.zeros(6))
        return self.controller.plan_reports[-1]

    def test_default_stops_at_first_certified_route_and_preserves_original_cost_budget(self):
        report = self.compute()
        self.controller._transport_at_height.assert_called_once()
        self.assertEqual(report['transition_height_m'], .06)
        self.assertAlmostEqual(report['motion_and_arrival_s'], 28.)
        self.assertAlmostEqual(report['budget_finish_lower_bound_s'], 45.)
        self.assertEqual(report['route_search']['requested_feasible_routes'], 1)
        self.assertEqual(report['route_search']['certified_routes'], 1)

    def test_optional_two_selects_shorter_original_cost_and_does_not_search_third(self):
        self.controller._transport_at_height.side_effect = lambda q, current, height, release: (
            self.paths(.8 if round(height, 3) == .06 else .4))
        report = self.compute(transport_candidates=2)
        self.assertEqual(self.controller._transport_at_height.call_count, 2)
        self.assertAlmostEqual(report['transition_height_m'], .057)
        self.assertAlmostEqual(report['motion_and_arrival_s'], 15.5)
        self.assertEqual([row['selected'] for row in report['transition_attempts']], [False, True])
        self.assertEqual(len(self.controller.transport), 5)

    def test_endpoint_or_complete_route_rejections_do_not_count_as_certified(self):
        def endpoint(xyz, previous):
            if round(xyz[2], 3) == .06:
                raise RuntimeError('No vertical pinch IK candidate, test endpoint')
            return np.zeros(5)
        def route(q, current, height, release):
            if round(height, 3) == .057:
                raise ControllerFailure('estimated_payload_route_collision')
            return self.paths(.8 if round(height, 3) == .054 else .4)
        self.controller._route_ik.side_effect = endpoint
        self.controller._transport_at_height.side_effect = route
        report = self.compute(transport_candidates=2)
        self.assertAlmostEqual(report['transition_height_m'], .051)
        self.assertEqual([row['status'] for row in report['transition_attempts']],
                         ['rejected', 'rejected', 'accepted', 'accepted'])
        self.assertEqual([row['validation_stage'] for row in report['transition_attempts']],
                         ['endpoint_ik', 'complete_route', 'complete_route', 'complete_route'])
        self.assertEqual(self.controller._transport_at_height.call_count, 3)

    def test_fewer_feasible_routes_keeps_certified_result_after_original_fallbacks(self):
        def route(q, current, height, release):
            if height != .06:
                raise ControllerFailure('estimated_payload_route_collision')
            return self.paths(.8)
        self.controller._transport_at_height.side_effect = route
        report = self.compute(transport_candidates=3)
        self.assertEqual(report['transition_height_m'], .06)
        self.assertEqual(report['route_search']['certified_routes'], 1)
        self.assertEqual(report['transition_attempts'][-1]['height_m'], .028)
        self.assertTrue(report['transition_attempts'][0]['selected'])

    def test_equal_cost_keeps_preference_order(self):
        report = self.compute(transport_preference_m=.057, transport_candidates=2)
        self.assertAlmostEqual(report['transition_height_m'], .057)
        self.assertAlmostEqual(report['transition_attempts'][1]['height_m'], .06)
        self.assertTrue(report['transition_attempts'][0]['selected'])

    def test_unknown_failure_and_cancellation_propagate_even_after_first_success(self):
        for reason in ('unexpected_collision_backend', 'transport_planning_cancelled'):
            with self.subTest(reason=reason):
                self.controller._transport_at_height.side_effect = [
                    self.paths(.8), ControllerFailure(reason)]
                with self.assertRaisesRegex(ControllerFailure, reason):
                    self.compute(transport_candidates=2)
                self.assertEqual(self.controller.plan_reports, [])

    def test_no_feasible_route_preserves_original_failure(self):
        self.controller._transport_at_height.side_effect = ControllerFailure(
            'estimated_payload_route_collision')
        with self.assertRaisesRegex(ControllerFailure, 'estimated_payload_route_collision'):
            self.compute(transport_candidates=2)
        self.assertEqual(self.controller.plan_reports, [])

    def test_task_release_endpoint_remains_mandatory(self):
        self.controller._route_ik.side_effect = RuntimeError('No vertical pinch IK candidate')
        with self.assertRaisesRegex(RuntimeError, 'No vertical pinch IK candidate'):
            self.compute(transport_candidates=2)
        self.controller._transport_at_height.assert_not_called()

    def test_search_records_actual_wall_cost_without_subtracting_it_from_motion(self):
        with patch('visual_grasp_controller.time.perf_counter', side_effect=itertools.count(0., .25)):
            report = self.compute(transport_candidates=2)
        self.assertEqual(report['route_search']['wall_s'], 1.25)
        self.assertEqual([row['validation_wall_s'] for row in report['transition_attempts']], [.25, .25])
        self.assertAlmostEqual(report['motion_and_arrival_s'], 28.)

    def test_new_field_is_validated_loaded_and_carried_by_snapshot_and_binding(self):
        for value in (0, 4, True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                RoutePolicy(transport_candidates=value)
        path = Path(__file__).parent/'route_strategies/shortest_two_routes.py'
        policy, loaded = load_route_policy(path)
        self.assertEqual(policy.transport_candidates, 2)
        self.assertEqual(loaded['loaded_path'], str(path.resolve()))
        snapshot = TransportSnapshot(q6=np.zeros(6), target_xy=[.24, -.13],
                    payload_relative=[0., 0., -.03], payload_rotation=np.eye(3), world=[],
                    payload_uncertainty=.002, elapsed_s=3., route_policy=policy)
        self.assertIs(snapshot.route_policy, policy)
        controller = self.controller
        controller.rig, controller.checker = object(), object()
        controller.stage, controller.jaw, controller.released_query = 'hold', .015, None
        first = controller._async_transport_binding()
        controller.route_policy = policy
        self.assertFalse(first.matches(controller._async_transport_binding()))

    def test_evaluator_forwards_search_diagnostics_without_changing_failure_verdict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def execute(station, output, cancel, *, route_policy):
                output.mkdir(parents=True)
                atomic_json(output/'status.json', {'status': 'failed', 'report': {
                    'passed': False, 'failure_reason': 'original_failure'}})
                (output/'episode').mkdir()
                atomic_json(output/'episode/planning.json', [{'stage': 'transport_execution_plan',
                            'route_search': {'requested_feasible_routes': 2,
                                             'certified_routes': 2, 'wall_s': .8}}])
                return 1
            with patch('evaluate_station.run', execute):
                self.assertEqual(evaluate(root/'scene.json', root/'runs'), 1)
            result = json.loads((root/'runs/evaluation.json').read_text())
            self.assertEqual(result['policy_execution']['transport'][0]['route_search']['wall_s'], .8)
            self.assertEqual(result['failure_reason'], 'original_failure')
            self.assertFalse(result['passed'])


if __name__ == '__main__':
    unittest.main()
