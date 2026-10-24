"""Focused adapter checks; no physical simulation or rendering is started."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_workspace_case as workspace


class WorkspaceCaseTests(unittest.TestCase):
    def test_invalid_profile_and_case_are_local_rejections(self):
        profile = json.loads(workspace.DEFAULT_PROFILE.read_text())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'profile.json'
            profile['cases'][1]['initial_xy_m'] = [True, -.11]
            path.write_text(json.dumps(profile))
            with self.assertRaisesRegex(ValueError, 'finite metre'):
                workspace.select_case(path, 'outside_y_plus20')
            self.assertEqual(workspace.select_case(path, 'center_primary')['id'], 'center_primary')
            with self.assertRaisesRegex(ValueError, 'unknown or duplicate'):
                workspace.select_case(path, 'missing')
            profile['development_only'] = False
            path.write_text(json.dumps(profile))
            with self.assertRaisesRegex(ValueError, 'development_only'):
                workspace.select_case(path, 'center_primary')

    def test_baselines_use_original_controller_region(self):
        for ident in ('center_primary', 'center_secondary'):
            case = workspace.select_case(workspace.DEFAULT_PROFILE, ident)
            options = workspace.controller_options(case, object())
            self.assertNotIn('target_region_xy_m', options)
            self.assertEqual(options['release_rotation_mode'], 'floor_yaw')
            self.assertEqual(options['release_pinch_height_m'], .028)
            self.assertNotIn('pickup_hover_z_m', options)
            self.assertNotIn('pickup_open_jaw_rad', options)
            self.assertNotIn('pick_xy', options)

    def test_preclose_is_explicit_and_keeps_original_tray_and_protocol(self):
        profile = workspace.DEFAULT_PROFILE.with_name('workspace-x-preclose-m1a.json')
        case = workspace.select_case(profile, 'right_preclose35')
        self.assertNotIn('pick_xy_m', case)
        self.assertEqual(case['initial_xy_m'], [.26, -.13])
        self.assertEqual(workspace.controller_options(case, None)['pickup_open_jaw_rad'], .35)
        baseline = workspace.select_case(profile, 'right_original_open50')
        self.assertNotIn('pickup_open_jaw_rad', workspace.controller_options(baseline, None))
        self.assertEqual(workspace.PROTOCOL, {'max_sim_s': 90, 'max_episode_wall_s': 120})
        document = json.loads(profile.read_text())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'profile.json'
            for value in (True, .34, .36, 0., float('nan')):
                document['cases'][1]['pickup_open_jaw_rad'] = value
                path.write_text(json.dumps(document))
                with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'pickup_open_jaw_rad'):
                    workspace.select_case(path, 'right_preclose35')

    def test_x_layout_and_hover_are_explicit_and_do_not_retarget_the_object(self):
        profile = workspace.DEFAULT_PROFILE.with_name('workspace-x-m1a.json')
        case = workspace.select_case(profile, 'outside_x_plus20_layout')
        self.assertEqual(case['initial_xy_m'], [.26, -.13])
        self.assertEqual(case['pick_xy_m'], [.26, -.13])
        self.assertEqual(workspace.controller_options(case, None)['pickup_hover_z_m'], .054)
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(workspace, '_run_original', return_value={'passed': False}) as original:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(workspace.run_case(profile, case['id'], folder), 1)
            _, physical_case, options, _ = original.call_args.args
            self.assertEqual(physical_case['pick_xy_m'], case['pick_xy_m'])
            self.assertEqual(physical_case['initial_xy_m'], case['initial_xy_m'])
            self.assertNotIn('pick_xy', options)  # Scene layout never enters controller inputs.

    def test_x_layout_reaches_original_scene_builder(self):
        profile = workspace.DEFAULT_PROFILE.with_name('workspace-x-m1a.json')
        case = workspace.select_case(profile, 'outside_x_plus20_layout')
        def physical(*args, **kwargs):
            return kwargs['scene_builder']('source', 'folder', noslip_iterations=10)
        with patch.object(workspace, '_configure_native'), \
                patch('grasp_episode.build_contact_scene', return_value='built') as builder, \
                patch('run_visual_grasp.run_physical_episode', side_effect=physical):
            self.assertEqual(workspace._run_original(Path('/tmp/unused'), case,
                              workspace.controller_options(case, None), None), 'built')
        self.assertEqual(builder.call_args.kwargs,
                         {'place_xy': [.24, .14], 'place_height_m': 0.,
                          'pick_xy': [.26, -.13], 'noslip_iterations': 10})

    def test_invalid_optional_layout_and_hover_are_case_local(self):
        profile = json.loads(workspace.DEFAULT_PROFILE.read_text())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'profile.json'
            for key, values in [('pick_xy_m', [[True, 0], [0, float('nan')]]),
                                ('pickup_hover_z_m', [True, .0539, .0601, float('nan')])]:
                for value in values:
                    profile['cases'][1][key] = value
                    path.write_text(json.dumps(profile))
                    with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, key):
                        workspace.select_case(path, 'outside_y_plus20')
                    self.assertEqual(workspace.select_case(path, 'center_primary')['id'], 'center_primary')
                del profile['cases'][1][key]

    def test_selected_case_identity_and_static_region_reach_original_call(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(workspace, '_run_original', return_value={'passed': False}) as original:
                with contextlib.redirect_stdout(io.StringIO()):
                    code = workspace.run_case(workspace.DEFAULT_PROFILE,
                                              'outside_y_minus20_secondary', folder)
            self.assertEqual(code, 1)
            _, physical_case, options, _ = original.call_args.args
            self.assertEqual(physical_case['id'], 'outside_y_minus20_secondary')
            self.assertEqual(physical_case['initial_xy_m'], [.24, -.15])
            self.assertEqual(options['place_xy'], [.20, .20])
            self.assertEqual(options['target_region_xy_m'], ((.21, .27), (-.16, -.10)))
            run = next(p for p in Path(folder).iterdir() if p.is_dir())
            result = json.loads((run/'evaluation.json').read_text())
            self.assertEqual(json.loads((Path(folder)/'evaluation.json').read_text()), result)
            self.assertEqual(result['requested_case']['id'], physical_case['id'])
            self.assertTrue(result['development_only'])
            self.assertTrue(result['not_admitted'])

    def test_original_failure_and_unknown_case_never_become_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(workspace, '_run_original', return_value={
                    'passed': False, 'failure_reason': 'original physical rejection'}) as original:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(workspace.run_case(workspace.DEFAULT_PROFILE, 'center_primary', folder), 1)
                    self.assertEqual(workspace.run_case(workspace.DEFAULT_PROFILE, 'unknown', folder), 1)
            self.assertEqual(original.call_count, 1)
            results = [json.loads((p/'evaluation.json').read_text())
                       for p in Path(folder).iterdir() if p.is_dir()]
            self.assertEqual({r['requested_case']['id'] for r in results}, {'center_primary', 'unknown'})
            self.assertTrue(all(r['passed'] is False for r in results))
            scored = next(r for r in results if r['requested_case']['id'] == 'center_primary')
            self.assertEqual(scored['verdict'], 'fail')
            self.assertEqual(scored['failure_reason'], 'original physical rejection')
            unknown = next(r for r in results if r['requested_case']['id'] == 'unknown')
            self.assertEqual(unknown['verdict'], 'unscored')


if __name__ == '__main__':
    unittest.main()
