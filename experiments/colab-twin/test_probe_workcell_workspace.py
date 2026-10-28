"""Focused offline probe contracts and per-stage failure isolation."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import numpy as np

import probe_workcell_workspace as probe
from grasp_episode import build_contact_scene, solve_pinch_ik


SOURCE = Path(__file__).resolve().parents[2]/'workspaces/so101_ws/src/so101_mujoco/models/so101.xml'


class WorkspaceProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix='test-so101-workspace-')
        _, cls.model, _ = build_contact_scene(SOURCE, Path(cls.folder.name))

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_real_center_checks_grasp_legs_without_physics_or_admission(self):
        with patch.object(probe.mujoco, 'mj_step', side_effect=AssertionError('physics forbidden')):
            report = probe.probe_workspace(self.model, [{'id': 'center', 'xy_m': [.24, -.13]}])
        point = report['points'][0]
        self.assertTrue(point['offline_screen_pass'])
        self.assertNotIn('grasp_sweep_screen', point)
        self.assertNotIn('extra_axis_screen', point)
        self.assertEqual(report['contract']['pickup_open_jaw_rad'], .5)
        self.assertFalse(report['contract']['full_grasp_sweep'])
        self.assertTrue(report['not_physical'])
        self.assertTrue(point['not_admitted'])
        self.assertFalse(point['paths']['start_to_approach_direct']['valid'])
        self.assertTrue(point['paths']['start_to_approach_direct']['diagnostic_only'])
        for stage in point['stages'].values():
            self.assertLess(stage['position_error_m'], 1e-5)
            self.assertLess(stage['axis_error_rad'], 1e-4)
            self.assertGreater(stage['joint_min_margin_rad'], 0.)
        json.dumps(report, allow_nan=False)

    def test_failed_down_does_not_skip_lift_or_the_next_point(self):
        failed = False

        def solve(model, xyz, initial=None):
            nonlocal failed
            if not failed and xyz[2] == .019:
                failed = True
                raise RuntimeError('deliberate down failure')
            return solve_pinch_ik(model, xyz, initial)

        points = [{'id': ident, 'xy_m': [.24, -.13]} for ident in ('first', 'second')]
        with patch.object(probe, 'solve_pinch_ik', side_effect=solve):
            report = probe.probe_workspace(self.model, points)
        first, second = report['points']
        self.assertEqual(first['stages']['down']['status'], 'ik_error')
        self.assertEqual(first['stages']['lift']['status'], 'solved')
        self.assertEqual(first['stages']['lift']['seed_source'], 'approach')
        self.assertEqual(first['paths']['approach_to_down']['status'], 'not_checked')
        self.assertFalse(first['offline_screen_pass'])
        self.assertTrue(second['offline_screen_pass'])
        self.assertEqual(second['stages']['approach']['seed_source'], 'reference_start')

    def test_invalid_point_and_duplicate_identity_are_rejected(self):
        for points in ([{'id': 'bad', 'xy_m': [float('nan'), 0.]}],
                       [{'id': 'bad', 'xy_m': [0., 0., 0.]}],
                       [{'id': 'same', 'xy_m': [0., 0.]}]*2):
            with self.subTest(points=points), self.assertRaises(ValueError):
                probe.normalize_points(points)

    def test_optional_height_keeps_original_ik_threshold_and_bounds(self):
        for height in (True, .05399, .06001, float('nan')):
            with self.subTest(height=height), self.assertRaises(ValueError):
                probe.probe_workspace(self.model, pickup_hover_z_m=height)
        with patch.object(probe.mujoco, 'mj_step', side_effect=AssertionError('physics forbidden')):
            report = probe.probe_workspace(self.model, [{'id': 'center', 'xy_m': [.24, -.13]}],
                                           pickup_hover_z_m=.054)
        self.assertEqual(report['points'][0]['stages']['approach']['target_pinch_world_m'][2], .054)
        self.assertEqual(report['points'][0]['stages']['down']['target_pinch_world_m'][2], .019)
        self.assertEqual(report['contract']['collision_margin_m'], .001)

    def test_optional_extra_directions_retain_original_result_and_full_closure(self):
        with patch.object(probe.mujoco, 'mj_step', side_effect=AssertionError('physics forbidden')):
            report = probe.probe_workspace(self.model, [{'id': 'center', 'xy_m': [.24, -.13]}],
                                           extra_mesh_box_axes=True)
        point = report['points'][0]
        self.assertTrue(point['offline_screen_pass'])
        extra = point['extra_axis_screen']
        self.assertTrue(extra['supplemental_valid'])
        self.assertTrue(extra['not_admitted'])
        self.assertTrue(extra['not_physical'])
        closure = extra['checks']['closure']
        self.assertEqual(closure['observed_samples'], 244)
        self.assertTrue(closure['complete'])
        self.assertTrue(closure['validation']['valid'])
        self.assertLessEqual(closure['validation']['max_jaw_step_rad'], .002)
        self.assertEqual(closure['original_rejections'], [])

    def test_full_grasp_sweep_keeps_original_244_and_all_pairs(self):
        with patch.object(probe.mujoco, 'mj_step', side_effect=AssertionError('physics forbidden')):
            report = probe.probe_workspace(self.model, [{'id': 'center', 'xy_m': [.24, -.13]}],
                                           full_grasp_sweep=True)
        screen = report['points'][0]['grasp_sweep_screen']
        self.assertTrue(screen['original_valid'])
        self.assertTrue(screen['not_admitted'])
        self.assertNotIn('preclose', screen['checks'])
        self.assertEqual(screen['checks']['closure']['observed_samples'], 244)
        for check in screen['checks'].values():
            self.assertTrue(check['complete'])
            self.assertTrue(check['all_pairs_checked'])
            self.assertTrue(check['all_pairs_certified'])
            self.assertEqual(check['minimum_certificate']['checked_pairs'], 285)
            self.assertEqual(check['minimum_certificate']['certified_pairs'], 285)
            self.assertGreaterEqual(check['minimum_certificate']['pair_lower_bound_m'], .001)
        json.dumps(report, allow_nan=False)

    def test_right_original_opening_is_still_rejected_by_full_sweep(self):
        with patch.object(probe.mujoco, 'mj_step', side_effect=AssertionError('physics forbidden')):
            report = probe.probe_workspace(self.model, [{'id': 'right', 'xy_m': [.26, -.13]}],
                                           pickup_hover_z_m=.054, full_grasp_sweep=True)
        point = report['points'][0]
        self.assertFalse(point['offline_screen_pass'])
        screen = point['grasp_sweep_screen']
        self.assertFalse(screen['original_valid'])
        rejected = [check for check in screen['checks'].values() if check['original_rejections']]
        self.assertTrue(rejected)
        self.assertTrue(any(not check['complete'] for check in rejected))
        observation = rejected[0]['original_rejections'][0]
        self.assertEqual(observation['reason'], 'uncertified_geometry_clearance')
        self.assertEqual(observation['checked_pairs'], 285)
        self.assertIn('pair_lower_bound_m', observation)
        json.dumps(report, allow_nan=False)

    def test_right_preclose_preserves_high_open_pose_and_dense_both_closures(self):
        with patch.object(probe.mujoco, 'mj_step', side_effect=AssertionError('physics forbidden')), \
                patch.object(probe.mujoco, 'mj_step1', side_effect=AssertionError('physics forbidden')), \
                patch.object(probe.mujoco, 'mj_step2', side_effect=AssertionError('physics forbidden')):
            report = probe.probe_workspace(self.model, [{'id': 'right', 'xy_m': [.26, -.13]}],
                                           pickup_hover_z_m=.054, pickup_open_jaw_rad=.35,
                                           full_grasp_sweep=True, extra_mesh_box_axes=True)
        point = report['points'][0]
        self.assertTrue(point['offline_screen_pass'])
        self.assertEqual(point['stages']['approach']['gripper_rad'], .5)
        self.assertEqual(point['stages']['down']['gripper_rad'], .35)
        self.assertEqual(point['paths']['start_to_approach_direct']['gripper_rad'], .5)
        self.assertEqual(point['paths']['approach_to_down']['gripper_rad'], .35)
        for name in ('grasp_sweep_screen', 'extra_axis_screen'):
            screen = point[name]
            self.assertTrue(screen.get('original_valid', screen.get('supplemental_valid')))
            for closure_name, span in (('preclose', .5-.35), ('closure', .35-.015)):
                closure = screen['checks'][closure_name]
                self.assertTrue(closure['complete'])
                self.assertGreaterEqual(closure['observed_samples'], 244)
                self.assertEqual(closure['observed_samples'], closure['validation']['required_states'])
                self.assertLessEqual(closure['validation']['max_jaw_step_rad'], span/244)
                self.assertEqual(closure['original_rejections'], [])
        json.dumps(report, allow_nan=False)

    def test_pickup_opening_only_accepts_original_or_explicit_preclose(self):
        for opening in (True, False, .015, .35001, 0, float('nan'), float('inf'), '.35'):
            with self.subTest(opening=opening), self.assertRaises(ValueError):
                probe.probe_workspace(self.model, pickup_open_jaw_rad=opening)

    def test_full_sweep_missing_ik_and_rejected_prefix_are_not_complete(self):
        missing = probe._grasp_sweep_screen(None, {}, np.zeros(5), .5)
        self.assertFalse(missing['original_valid'])
        self.assertEqual(missing['status'], 'missing_ik_endpoint')
        self.assertEqual(missing['checks'], {})
        checker = probe.CollisionChecker(self.model, gripper=.5, margin_m=.001)
        self.addCleanup(checker.native.close)
        rejected = {'valid': False, 'reason': 'uncertified_geometry_clearance',
                    'certificate_reason': 'no_separation_certificate', 'pair': ['wall', 'jaw'],
                    'pair_lower_bound_m': 0., 'checked_pairs': 285, 'certified_pairs': 284}
        with patch.object(checker, 'evaluate', return_value=rejected):
            screen = probe._grasp_sweep_screen(checker,
                {name: np.zeros(5) for name in ('approach', 'down', 'lift')}, np.zeros(5), .5)
        closure = screen['checks']['closure']
        self.assertFalse(screen['original_valid'])
        self.assertFalse(closure['complete'])
        self.assertEqual(closure['observed_samples'], 1)
        self.assertEqual(closure['validation']['required_states'], 244)
        self.assertTrue(closure['all_pairs_checked'])
        self.assertFalse(closure['all_pairs_certified'])
        self.assertEqual(closure['original_rejections'][0]['pair'], ['wall', 'jaw'])
        self.assertIsNone(closure['minimum_certificate'])

    def test_cli_forwards_explicit_pickup_and_full_sweep(self):
        minimal_report = {'not_physical': True, 'not_admitted': True, 'points': []}
        with patch.object(probe, 'probe_workspace', return_value=minimal_report) as run:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = probe.main(['--planning-scene', str(Path(self.folder.name)/'grasp-planning.xml'),
                                   '--pickup-open-jaw-rad', '.35', '--full-grasp-sweep'])
        self.assertEqual(code, 0)
        self.assertEqual(run.call_args.kwargs['pickup_open_jaw_rad'], .35)
        self.assertTrue(run.call_args.kwargs['full_grasp_sweep'])

    def test_extra_axis_diagnostic_cannot_hide_missing_ik(self):
        screen = probe._extra_axis_screen(self.model, None, {}, np.zeros(5))
        self.assertFalse(screen['supplemental_valid'])
        self.assertEqual(screen['status'], 'missing_ik_endpoint')

    def test_extra_axis_first_failure_is_explicitly_incomplete(self):
        # A diagnostic must not call a one-sample rejected prefix a full sweep.
        rejected = {'original': {'valid': False}, 'supplemental_valid': False}
        with patch('mesh_box_axes.MeshBoxAxes.inspect', return_value=rejected):
            screen = probe._extra_axis_screen(self.model, None,
                {name: np.zeros(5) for name in ('approach', 'down', 'lift')}, np.zeros(5))
        closure = screen['checks']['closure']
        self.assertFalse(closure['complete'])
        self.assertEqual(closure['observed_samples'], 1)
        self.assertEqual(closure['validation']['required_states'], 244)
        self.assertFalse(screen['supplemental_valid'])

    def test_real_right_rejected_pose_remains_rejected_and_strict_json(self):
        from mesh_box_axes import MeshBoxAxes
        checker = probe.CollisionChecker(self.model, gripper=.5, margin_m=.001)
        self.addCleanup(checker.native.close)
        # Frozen original fixed-tray X+20mm down/open failure from round102.
        q6 = [.5295673994985538, .5989791439095056, -.4141037308946587,
              1.3859209137800415, 1.145968274084528e-15, .5]
        with patch.object(probe.mujoco, 'mj_step', side_effect=AssertionError('physics forbidden')):
            result = MeshBoxAxes(self.model).inspect(checker, q6)
        self.assertFalse(result['original']['valid'])
        self.assertFalse(result['supplemental_valid'])
        self.assertTrue(result['pairs'])
        self.assertFalse(result['pairs'][0]['certified'])
        self.assertIsNone(result['pairs'][0]['squared_gap_lower'])
        json.dumps(result, allow_nan=False)

    def test_scene_error_is_machine_readable_and_cannot_claim_success(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            status = probe.main(['--planning-scene', '/missing-so101-probe-scene.xml'])
        report = json.loads(output.getvalue())
        self.assertEqual(status, 2)
        self.assertEqual(report['status'], 'scene_or_probe_error')
        self.assertTrue(report['not_physical'])
        self.assertTrue(report['not_admitted'])
        self.assertEqual(report['points'], [])

    def test_json_output_cannot_overwrite_the_input_scene(self):
        with tempfile.TemporaryDirectory() as folder:
            scene = Path(folder)/'scene.xml'
            scene.write_text('<original-scene/>')
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                probe.main(['--planning-scene', str(scene), '--output', str(scene)])
            self.assertEqual(caught.exception.code, 2)
            self.assertEqual(scene.read_text(), '<original-scene/>')

    def test_output_error_preserves_the_offline_report_on_stdout(self):
        output = io.StringIO()
        minimal_report = {'not_physical': True, 'not_admitted': True, 'points': []}
        with patch.object(probe, 'probe_workspace', return_value=minimal_report):
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                status = probe.main(['--planning-scene', str(Path(self.folder.name)/'grasp-planning.xml'),
                                     '--output', self.folder.name])
        report = json.loads(output.getvalue())
        self.assertEqual(status, 2)
        self.assertEqual(report['status'], 'report_output_error')
        self.assertTrue(report['not_admitted'])

    def test_reference_collision_error_is_not_misreported_as_ik_error(self):
        original = probe.CollisionChecker.evaluate
        failed = False

        def evaluate(checker, *args, **kwargs):
            nonlocal failed
            if not failed:
                failed = True
                raise RuntimeError('deliberate reference check failure')
            return original(checker, *args, **kwargs)

        with patch.object(probe.CollisionChecker, 'evaluate', evaluate):
            report = probe.probe_workspace(self.model, [{'id': 'center', 'xy_m': [.24, -.13]}])
        self.assertEqual(report['reference_start']['status'], 'check_error')
        self.assertIn('q5_rad', report['reference_start'])
        self.assertEqual(report['points'][0]['stages']['approach']['status'], 'solved')


class InitialQ6ProbeMockTests(unittest.TestCase):
    """Exercise initial-state contracts without constructing any MuJoCo model."""

    def run_probe(self, solve, *, initial_q6=None, explicit_initial=True, points=None, **options):
        checkers = []

        def checker(model, *, gripper, margin_m):
            result = Mock(gripper=gripper, pairs=list(range(285)))
            result.evaluate.return_value = {
                'valid': True, 'min_distance_m': .002, 'checked_pairs': 285,
                'certified_pairs': 285, 'distance_kind': 'certified_lower_bound',
            }
            checkers.append(result)
            return result

        supplied = {'initial_q6': initial_q6} if explicit_initial else {}
        with patch.object(probe, 'CollisionChecker', side_effect=checker), \
                patch.object(probe, 'solve_pinch_ik', side_effect=solve) as solver, \
                patch.object(probe, '_frame_facts', return_value={'mock_frame': True}) as frame, \
                patch.object(probe, '_pose_metrics', return_value={}), \
                patch.object(probe, '_path', return_value={'status': 'checked', 'valid': True}), \
                patch.object(probe.mujoco, 'MjData', side_effect=AssertionError('model data forbidden')):
            report = probe.probe_workspace(object(), points or [{'id': 'one', 'xy_m': [.24, -.13]}],
                                           **supplied, **options)
        return report, checkers, solver, frame

    def test_default_none_preserves_report_reference_seed_and_failure_continuation(self):
        def solver():
            count = 0
            def solve(model, xyz, initial=None):
                nonlocal count
                count += 1
                if xyz[2] == .019:
                    raise RuntimeError('original down failure')
                return np.full(5, count*.01)
            return solve

        implicit, _, old_calls, old_frame = self.run_probe(solver(), explicit_initial=False)
        explicit, _, calls, frame = self.run_probe(solver())
        self.assertEqual(implicit, explicit)
        self.assertIsNone(calls.call_args_list[0].args[2] if len(calls.call_args_list[0].args) > 2 else None)
        self.assertEqual(calls.call_count, 4)
        self.assertEqual(old_calls.call_count, 4)
        stages = explicit['points'][0]['stages']
        self.assertEqual(stages['down']['status'], 'ik_error')
        self.assertEqual(stages['lift']['status'], 'solved')
        self.assertEqual(stages['lift']['seed_source'], 'approach')
        self.assertNotIn('initial_q6_rad', explicit['contract'])
        self.assertEqual(frame.call_args.kwargs, old_frame.call_args.kwargs)
        self.assertEqual(frame.call_args.kwargs, {})

    def test_supplied_state_preserves_jaw_and_runtime_seed_chain_without_mutating_input(self):
        q6 = np.array([.1, .2, .3, .4, .5, .4999999999754389])
        original = q6.copy()
        q6.setflags(write=False)
        seeds = []
        solutions = [np.full(5, value) for value in (.11, .22, .33)]

        def solve(model, xyz, initial):
            seeds.append(initial.copy())
            return solutions[len(seeds)-1].copy()

        report, checkers, solver, frame = self.run_probe(solve, initial_q6=q6, full_grasp_sweep=True)
        self.assertEqual(solver.call_count, 3)
        for actual, expected in zip(seeds, [original[:5], *solutions[:2]]):
            np.testing.assert_array_equal(actual, expected)
        self.assertEqual([s['seed_source'] for s in report['points'][0]['stages'].values()],
                         ['initial_q6', 'approach', 'down'])
        np.testing.assert_array_equal(q6, original)
        np.testing.assert_array_equal(frame.call_args.kwargs['reference_q6'], original)
        reference_call = checkers[0].evaluate.call_args_list[0]
        np.testing.assert_array_equal(reference_call.args[0], original)
        self.assertEqual(reference_call.kwargs, {'require_fixed_gripper': False})
        self.assertEqual(report['reference_start']['q6_rad'], original.tolist())
        self.assertEqual(report['reference_start']['source'], 'initial_q6')
        screen = report['points'][0]['grasp_sweep_screen']
        self.assertEqual(screen['checks']['reference']['minimum_certificate']['q6_rad'], original.tolist())
        self.assertEqual(screen['checks']['closure']['observed_samples'], 244)
        self.assertTrue(all(row['all_pairs_checked'] for row in screen['checks'].values()))

    def test_explicit_ik_failure_stops_only_that_point_and_never_changes_next_initial_seed(self):
        q6 = np.array([.1, .2, .3, .4, .5, .4999999999754389])
        for failure_stage, failed_index in (('approach', 0), ('down', 1), ('lift', 2)):
            calls = []
            def solve(model, xyz, initial):
                index = len(calls)
                calls.append(initial.copy())
                if index == failed_index:
                    initial[:] = 99.  # Caller data and the next point must stay owned.
                    raise RuntimeError('original IK residual rejection')
                return np.full(5, .01*(index+1))

            points = [{'id': name, 'xy_m': [.24, -.13]} for name in ('first', 'second')]
            with self.subTest(stage=failure_stage):
                report, _, _, _ = self.run_probe(solve, initial_q6=q6, points=points,
                                                full_grasp_sweep=True)
                first, second = report['points']
                self.assertEqual(first['stages'][failure_stage]['status'], 'ik_error')
                for name in ('approach', 'down', 'lift')[failed_index+1:]:
                    self.assertEqual(first['stages'][name]['status'], 'not_attempted')
                    self.assertEqual(first['stages'][name]['failed_stage'], failure_stage)
                self.assertEqual(first['grasp_sweep_screen']['status'], 'missing_ik_endpoint')
                self.assertFalse(first['offline_screen_pass'])
                self.assertTrue(second['offline_screen_pass'])
                self.assertEqual(len(calls), failed_index+1+3)
                np.testing.assert_array_equal(calls[failed_index+1], q6[:5])

    def test_invalid_supplied_q6_is_rejected_before_any_checker_or_solver(self):
        invalid = [True, 1, [], [0.]*5, [0.]*7, [[0.]]*6,
                   [0.]*5+[True], [0.]*5+['.5'], [0.]*5+[float('nan')],
                   [0.]*5+[float('inf')], [0.]*5+[1j]]
        with patch.object(probe, 'CollisionChecker') as checker, patch.object(probe, 'solve_pinch_ik') as solve:
            for q6 in invalid:
                with self.subTest(q6=q6), self.assertRaisesRegex(ValueError, 'initial_q6'):
                    probe.probe_workspace(object(), initial_q6=q6)
        checker.assert_not_called()
        solve.assert_not_called()

    def test_frame_facts_preserve_supplied_q6_and_keep_default_jaw(self):
        q6 = np.array([.1, .2, .3, .4, .5, .4999999999754389])
        model = Mock()
        model.body.side_effect = model.joint.side_effect = model.camera.side_effect = KeyError('unavailable')
        data = Mock(qpos=np.zeros(6))
        with patch.object(probe.mujoco, 'MjData', return_value=data), \
                patch.object(probe.mujoco, 'mj_forward'):
            actual = probe._frame_facts(model, q6[:5], reference_q6=q6)
            default = probe._frame_facts(model, q6[:5])
        self.assertEqual(actual['q6_rad'], q6.tolist())
        self.assertEqual(default['q6_rad'], [*q6[:5], .5])

    def test_extra_axis_helper_uses_original_q6_only_for_reference(self):
        q6 = np.array([.1, .2, .3, .4, .5, .4999999999754389])
        observed = []
        def inspect(checker, q):
            observed.append(q.copy())
            return {'original': {'valid': True}, 'supplemental_valid': True}
        with patch('mesh_box_axes.MeshBoxAxes') as axes:
            axes.return_value.inspect.side_effect = inspect
            result = probe._extra_axis_screen(object(), object(),
                {name: np.zeros(5) for name in ('approach', 'down', 'lift')}, q6[:5], .35,
                reference_q6=q6)
        self.assertTrue(result['supplemental_valid'])
        np.testing.assert_array_equal(observed[0], q6)
        np.testing.assert_array_equal(observed[1], q6)
        self.assertEqual(observed[2][5], .5)
        self.assertEqual(result['checks']['preclose']['observed_samples'], 246)

    def test_cli_forwards_six_values_for_both_scene_entries(self):
        q6 = [.1, .2, .3, .4, .5, .4999999999754389]
        for entry in ('--planning-scene', '--source'):
            model = object()
            with self.subTest(entry=entry), \
                    patch.object(probe.mujoco.MjModel, 'from_xml_path', return_value=model), \
                    patch.object(probe, 'build_contact_scene', return_value=(None, model, None)), \
                    patch.object(probe, 'probe_workspace', return_value={'points': []}) as run, \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = probe.main([entry, '/unused/scene.xml', '--initial-q6', *map(str, q6)])
                self.assertEqual(result, 0)
                self.assertIs(run.call_args.args[0], model)
                self.assertEqual(run.call_args.kwargs['initial_q6'], q6)


if __name__ == '__main__':
    unittest.main()
