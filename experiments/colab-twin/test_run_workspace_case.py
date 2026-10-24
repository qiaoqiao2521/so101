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
