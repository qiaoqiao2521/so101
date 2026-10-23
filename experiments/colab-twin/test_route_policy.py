"""A candidate changes route choices, never the available geometry or guards."""
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluate_station import evaluate
from route_policy import BASELINE_SOURCE, DEFAULT_SOURCE, RoutePolicy, load_route_policy
from station_executor import atomic_json
from visual_grasp_controller import VisualGraspController


class RoutePolicyTests(unittest.TestCase):
    def test_baseline_preserves_original_order(self):
        values = [.06, .057, .054, .051, .048, .028]
        self.assertEqual(RoutePolicy().transport_heights(values, 0), values)

    def test_candidate_reorders_without_adding_or_dropping_height(self):
        values = [.07, .067, .064, .061, .058, .038]
        ordered = RoutePolicy(.051, 10).transport_heights(values, .01)
        self.assertEqual(ordered[0], .061)
        self.assertCountEqual(ordered, values)
        self.assertEqual(values[0], .07)

    def test_invalid_or_mutable_preferences_are_rejected(self):
        for options in ({'separation_steps': 0}, {'separation_steps': 14},
                        {'separation_steps': True}, {'separation_steps': 1.5},
                        {'transport_preference_m': float('nan')},
                        {'transport_preference_m': .2}, {'ik_seed': 'change_tolerance'},
                        {'reuse_adjacent_validity': 1}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                RoutePolicy(**options)
        with self.assertRaises(ValueError):
            RoutePolicy(reuse_separation_distances=1)
        with self.assertRaises(ValueError):
            RoutePolicy(batch_separation_axes=1)
        with self.assertRaises(ValueError):
            RoutePolicy(quad_vertices=1)
        with self.assertRaises(ValueError):
            RoutePolicy(small_direction_cache=1)
        with self.assertRaises(ValueError):
            RoutePolicy(tree_leaf8=1)
        with self.assertRaises(ValueError):
            RoutePolicy(leaf_packed=1)
        with self.assertRaises(ValueError):
            RoutePolicy(packed_inline=1)
        with self.assertRaises(ValueError):
            RoutePolicy(seed_bound_direct=1)
        with self.assertRaises(ValueError):
            RoutePolicy(summary_fast=1)
        with self.assertRaises(ValueError):
            RoutePolicy(refresh_leg_age=1)
        with self.assertRaises(ValueError):
            RoutePolicy(batch_configuration_sweep=1)
        with self.assertRaises(ValueError):
            RoutePolicy(smooth_jaw_dwell=1)
        with self.assertRaises(FrozenInstanceError):
            RoutePolicy().separation_steps = 1

    def test_ik_choice_only_selects_the_existing_initial_argument(self):
        controller = VisualGraspController.__new__(VisualGraspController)
        controller.rig = object()
        xyz, previous = [0, 0, .06], [0]*5
        for mode in ('continuation', 'neutral'):
            controller.route_policy = RoutePolicy(ik_seed=mode)
            with patch('visual_grasp_controller.solve_pinch_ik') as solver:
                controller._route_ik(xyz, previous)
                solver.assert_called_once_with(controller.rig, xyz,
                                               previous if mode == 'continuation' else None)

    def test_adjacent_validity_reuses_only_exact_completed_state(self):
        from visual_grasp_controller import reuse_last_validity
        calls = []
        validate = reuse_last_validity(lambda q: calls.append(tuple(q)) or False)
        self.assertFalse(validate([0., 0., 0., 0., 0.]))
        self.assertFalse(validate([0., 0., 0., 0., 0.]))
        self.assertEqual(calls, [(0., 0., 0., 0., 0.)])
        self.assertEqual(validate.counters, {'calls': 2, 'hits': 1, 'computations': 1})

        def fail(q):
            raise RuntimeError('original validation exception')
        failing = reuse_last_validity(fail)
        with self.assertRaisesRegex(RuntimeError, 'original validation exception'):
            failing([0.]*5)
        self.assertEqual(failing.counters, {'calls': 1, 'hits': 0, 'computations': 0})

    def test_source_is_executed_fresh_and_records_real_entrypoint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'candidate.py'
            for steps in (10, 11):
                path.write_text(f'def route_preferences():\n    return {{"separation_steps": {steps}}}\n')
                policy, loaded = load_route_policy(path)
                self.assertEqual(policy.separation_steps, steps)
                self.assertEqual(loaded['loaded_path'], str(path.resolve()))
                self.assertEqual(loaded['entrypoint_path'], str(path.resolve()))

    def test_quad_candidate_is_explicit_and_baseline_stays_scalar(self):
        self.assertFalse(load_route_policy()[0].quad_vertices)
        path = Path(__file__).parent/'route_strategies/quad_vertices.py'
        policy, loaded = load_route_policy(path)
        self.assertTrue(policy.quad_vertices)
        self.assertEqual(loaded['preferences']['quad_vertices'], True)

    def test_small_cache_candidate_does_not_combine_quad(self):
        self.assertFalse(load_route_policy()[0].small_direction_cache)
        path = Path(__file__).parent/'route_strategies/small_direction_cache.py'
        policy, loaded = load_route_policy(path)
        self.assertTrue(policy.small_direction_cache)
        self.assertFalse(policy.quad_vertices)
        self.assertEqual(loaded['preferences']['small_direction_cache'], True)

    def test_leaf8_only_changes_the_tree_partition(self):
        self.assertFalse(load_route_policy()[0].tree_leaf8)
        policy, loaded = load_route_policy(Path(__file__).parent/'route_strategies/tree_leaf8.py')
        self.assertTrue(policy.tree_leaf8)
        self.assertFalse(policy.quad_vertices)
        self.assertFalse(policy.small_direction_cache)
        self.assertEqual(loaded['preferences']['tree_leaf8'], True)

    def test_packed_candidate_only_selects_immutable_storage(self):
        self.assertFalse(load_route_policy(BASELINE_SOURCE)[0].leaf_packed)
        policy, loaded = load_route_policy(Path(__file__).parent/'route_strategies/leaf_packed.py')
        self.assertTrue(policy.leaf_packed)
        self.assertFalse(policy.packed_inline)
        self.assertFalse(policy.quad_vertices)
        self.assertFalse(policy.small_direction_cache)
        self.assertFalse(policy.tree_leaf8)
        self.assertEqual(loaded['preferences']['leaf_packed'], True)

    def test_factory_default_and_explicit_original_remain_distinct(self):
        recommended, source = load_route_policy()
        self.assertTrue(recommended.leaf_packed)
        self.assertTrue(recommended.packed_inline)
        self.assertTrue(recommended.seed_bound_direct)
        self.assertTrue(recommended.summary_fast)
        self.assertTrue(recommended.batch_configuration_sweep)
        self.assertFalse(recommended.refresh_leg_age)
        self.assertEqual(source['entrypoint_path'], str(DEFAULT_SOURCE.resolve()))
        original, source = load_route_policy(BASELINE_SOURCE)
        self.assertFalse(original.leaf_packed)
        self.assertEqual(original, RoutePolicy())
        self.assertEqual(source['entrypoint_path'], str(BASELINE_SOURCE.resolve()))

    def test_inline_parent_and_original_remain_available(self):
        child, source = load_route_policy(
            Path(__file__).parent/'route_strategies/leaf_packed_inline.py')
        self.assertTrue(child.leaf_packed)
        self.assertTrue(child.packed_inline)
        self.assertFalse(child.quad_vertices)
        self.assertEqual(source['preferences']['packed_inline'], True)
        self.assertFalse(child.seed_bound_direct)
        parent, _ = load_route_policy(Path(__file__).parent/'route_strategies/leaf_packed.py')
        self.assertTrue(parent.leaf_packed)
        self.assertFalse(parent.packed_inline)
        self.assertEqual(load_route_policy(BASELINE_SOURCE)[0], RoutePolicy())

    def test_evaluator_default_passes_the_recommended_policy_to_original_executor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            observed = []

            def execute(station, output, cancel, *, route_policy):
                observed.append(route_policy)
                output.mkdir(parents=True)
                atomic_json(output/'status.json', {'status': 'failed', 'report': {
                    'passed': False, 'failure_reason': 'original_failure'}})
                return 1

            with patch('evaluate_station.run', execute):
                evaluate(root/'station.json', root/'output')
            self.assertTrue(observed[0].leaf_packed)
            self.assertTrue(observed[0].packed_inline)
            self.assertTrue(observed[0].seed_bound_direct)
            self.assertTrue(observed[0].summary_fast)
            self.assertTrue(observed[0].batch_configuration_sweep)
            self.assertFalse(observed[0].refresh_leg_age)
            result = json.loads((root/'output/evaluation.json').read_text())
            self.assertEqual(result['candidate']['loaded_path'], str(DEFAULT_SOURCE.resolve()))
            self.assertEqual(result['verdict'], 'fail')

    def test_seed_bound_parent_and_earlier_implementations_remain_available(self):
        child, source = load_route_policy(
            Path(__file__).parent/'route_strategies/seed_bound_direct.py')
        self.assertTrue(child.leaf_packed)
        self.assertTrue(child.packed_inline)
        self.assertTrue(child.seed_bound_direct)
        self.assertFalse(child.quad_vertices)
        self.assertEqual(source['preferences']['seed_bound_direct'], True)
        self.assertFalse(child.summary_fast)
        parent, _ = load_route_policy(Path(__file__).parent/'route_strategies/leaf_packed_inline.py')
        self.assertFalse(parent.seed_bound_direct)
        self.assertTrue(parent.packed_inline)
        self.assertEqual(load_route_policy(BASELINE_SOURCE)[0], RoutePolicy())

    def test_summary_parent_remains_explicit_after_batch_adoption(self):
        child, source = load_route_policy(Path(__file__).parent/'route_strategies/summary_fast.py')
        self.assertTrue(child.summary_fast)
        self.assertTrue(child.seed_bound_direct)
        self.assertTrue(child.packed_inline)
        self.assertTrue(child.leaf_packed)
        self.assertEqual(source['preferences']['summary_fast'], True)
        self.assertFalse(child.batch_configuration_sweep)
        self.assertTrue(load_route_policy()[0].batch_configuration_sweep)
        parent, _ = load_route_policy(Path(__file__).parent/'route_strategies/seed_bound_direct.py')
        self.assertFalse(parent.summary_fast)
        self.assertTrue(parent.seed_bound_direct)

    def test_continuous_jaw_is_adopted_with_unchanged_batch_parent(self):
        child, _ = load_route_policy(Path(__file__).parent/'route_strategies/smooth_jaw_dwell.py')
        parent, _ = load_route_policy(Path(__file__).parent/'route_strategies/batch_configuration_sweep.py')
        self.assertTrue(child.smooth_jaw_dwell)
        self.assertFalse(parent.smooth_jaw_dwell)
        self.assertTrue(load_route_policy()[0].smooth_jaw_dwell)
        self.assertFalse(child.refresh_leg_age)
        self.assertEqual({key:value for key,value in child.preferences().items()
                          if key != 'smooth_jaw_dwell'},
                         {key:value for key,value in parent.preferences().items()
                          if key != 'smooth_jaw_dwell'})

    def test_evaluator_forwards_actual_choices_and_keeps_physical_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root/'candidate.py'
            candidate.write_text('def route_preferences():\n    return {"separation_steps": 10}\n')
            observed = []
            def execute(station, output, cancel, *, route_policy):
                observed.append(route_policy)
                output.mkdir(parents=True)
                atomic_json(output/'status.json', {'status': 'failed', 'report': {
                    'passed': False, 'failure_reason': 'unchanged_physical_failure'}})
                return 1
            with patch('evaluate_station.run', execute):
                self.assertEqual(evaluate(root/'scene.json', root/'runs', candidate_path=candidate), 1)
            result = json.loads((root/'runs/evaluation.json').read_text())
            self.assertEqual(observed, [RoutePolicy(separation_steps=10)])
            self.assertEqual(result['candidate']['loaded_path'], str(candidate.resolve()))
            self.assertEqual(result['failure_reason'], 'unchanged_physical_failure')
            self.assertFalse(result['passed'])

    def test_invalid_candidate_never_runs_or_falls_back_to_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root/'bad.py'
            candidate.write_text('def route_preferences():\n    return {"separation_steps": 0}\n')
            with patch('evaluate_station.run') as execute:
                self.assertEqual(evaluate(root/'scene.json', root/'runs', candidate_path=candidate), 1)
                execute.assert_not_called()
            result = json.loads((root/'runs/evaluation.json').read_text())
            self.assertEqual(result['verdict'], 'unscored')
            self.assertIsNone(result['candidate']['loaded_path'])


if __name__ == '__main__':
    unittest.main()
