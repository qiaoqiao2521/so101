"""Focused offline probe contracts and per-stage failure isolation."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
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


if __name__ == '__main__':
    unittest.main()
