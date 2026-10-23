"""Search-order safety: nonmonotonic obstacles, budget, and final rejection."""
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from route_policy import RoutePolicy, load_route_policy
import test_approach_shortcut as fixtures
import visual_grasp_controller as module


class MidpointShortcutTests(unittest.TestCase):
    def test_explicit_policy_has_only_one_delta_and_default_remains_off(self):
        parent, _ = load_route_policy()
        candidate, _ = load_route_policy(Path(__file__).parent/'route_strategies/approach_midpoint_order.py')
        self.assertFalse(RoutePolicy().approach_midpoint_order)
        self.assertFalse(parent.approach_midpoint_order)
        self.assertEqual([key for key, value in parent.preferences().items()
                          if value != candidate.preferences()[key]], ['approach_midpoint_order'])
        for bad in (1, None, 'true'):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                RoutePolicy(approach_midpoint_order=bad)

    def test_u_corridor_keeps_raw_route_and_complete_final_sampling(self):
        raw = fixtures.ApproachShortcutTests.detour()
        valid = fixtures.ApproachShortcutTests.corridor
        before, report = raw.copy(), {}
        output = module.shorten_path(raw, valid, report=report, midpoint_order=True)
        np.testing.assert_array_equal(output, raw)
        np.testing.assert_array_equal(raw, before)
        self.assertTrue(report['final_validation']['valid'])
        self.assertEqual(report['final_validation']['resolution_rad'], .005)
        self.assertTrue(all(row['validation']['resolution_rad'] == .005 for row in report['attempts']))

    def test_zero_and_one_budget_preserve_raw_fallback_and_final_gate(self):
        for budget in (0, 1):
            report, raw = {}, fixtures.ApproachShortcutTests.detour()
            with self.subTest(budget=budget):
                output = module.shorten_path(raw, fixtures.ApproachShortcutTests.corridor,
                    max_checks=budget, report=report, midpoint_order=True)
                np.testing.assert_array_equal(output, raw)
                self.assertEqual(report['candidate_edges_attempted'], budget)
                self.assertTrue(report['final_validation']['valid'])

    def test_nonmonotonic_search_uses_original_descending_fallback(self):
        tried = []
        def attempt(end):
            tried.append(end)
            return end == 7
        self.assertEqual(module._midpoint_shortcut_index(0, 8, attempt), 7)
        self.assertIn(7, tried)
        self.assertEqual(len(tried), len(set(tried)))

    def test_midpoint_result_does_not_claim_global_optimum(self):
        allowed = {4, 7}
        selected = module._midpoint_shortcut_index(0, 8, lambda end: end in allowed)
        self.assertIn(selected, allowed)
        self.assertLess(selected, max(allowed))

    def test_accepted_chord_cannot_override_final_original_collision(self):
        report = {}
        with self.assertRaisesRegex(module.ControllerFailure, '^shortened_return_path_invalid$'):
            module.shorten_path(fixtures.ApproachShortcutTests.detour(), fixtures.ApproachShortcutTests.corridor,
                shortcut_valid=lambda q: True, report=report, midpoint_order=True)
        self.assertTrue(report['attempts'][0]['validation']['valid'])
        self.assertFalse(report['final_validation']['valid'])

    def test_callback_error_is_not_replaced_or_swallowed(self):
        error = RuntimeError('original collision query failed')
        def fail(q):
            raise error
        with self.assertRaises(RuntimeError) as caught:
            module.shorten_path(fixtures.ApproachShortcutTests.detour(), fail, midpoint_order=True)
        self.assertIs(caught.exception, error)

    def test_flag_reaches_only_approach_with_original_guards(self):
        fixture = fixtures.ApproachShortcutTests()
        controller = fixture.controller()
        controller.route_policy = replace(RoutePolicy(), approach_midpoint_order=True)
        plan = fixture.approach_plan(controller)
        original, calls = module.shorten_path, []
        def observe(points, valid, **kwargs):
            calls.append(kwargs.copy())
            return original(points, valid, **kwargs)
        with patch.object(module, 'plan_joint_path', return_value=plan), patch.object(module, 'shorten_path', side_effect=observe):
            controller._plan_approach(controller.initial_q[:5])
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0]['midpoint_order'], True)
        self.assertEqual(calls[0]['max_checks'], 512)
        self.assertIs(calls[0]['shortcut_valid'].__self__, controller)
        self.assertTrue(controller.plan_reports[-1]['shortcut']['final_validation']['valid'])


if __name__ == '__main__':
    unittest.main()
