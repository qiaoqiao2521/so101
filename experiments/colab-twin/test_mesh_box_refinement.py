"""Optional original-geometry certificates; FK only, no task admission."""
from copy import deepcopy
import ctypes
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import mujoco
import numpy as np

from conservative_collision import ConservativeCollisionChecker
from configuration_sweep import validate_configuration_path
from grasp_episode import build_contact_scene
from mesh_box_axes import MeshBoxAxes
from test_conservative_collision import rig_xml


SOURCE = Path(__file__).resolve().parents[2]/'workspaces/so101_ws/src/so101_mujoco/models/so101.xml'
# Saved original fixed-tray X endpoints, not regenerated IK or target truth.
# Left: workspace-x-20261024/fixed-left-extra-axes.json points[0].stages.down.
LEFT = np.array([.6203200714974911, .2848702656947972, .07520128397644561,
                 1.210724777123653, -8.6649604384653e-17, .5])
# Right: round102-workspace-x-20261024/wall/right_symmetry.json down.
RIGHT = np.array([.5295673994985538, .5989791439095056, -.4141037308946587,
                  1.3859209137800415, 1.145968274084528e-15, .5])


class MeshBoxRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix='mesh-box-refinement-')
        _, cls.model, _ = build_contact_scene(SOURCE, Path(cls.folder.name))

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def checker(self, enabled=False, model=None):
        checker = ConservativeCollisionChecker(self.model if model is None else model,
            gripper=.5, margin_m=.001, mesh_box_axis_refinement=enabled)
        self.addCleanup(checker.native.close)
        return checker

    def original(self, checker, q=LEFT):
        return checker._evaluate_original(q, require_fixed_gripper=False)

    def details(self, checker):
        return checker.native.evaluate(checker.data.geom_xpos[checker.geometry_ids],
            checker.data.geom_xmat[checker.geometry_ids].reshape(-1, 3, 3),
            checker.pair_indices, .001)

    def test_real_left_full_certificate_keeps_global_nearest_pair_and_all_285(self):
        checker = self.checker(True)
        baseline = self.original(checker)
        self.assertFalse(baseline['valid'])
        self.assertEqual(baseline['certificate_reason'], 'no_separation_certificate')
        with patch.object(mujoco, 'mj_step', side_effect=AssertionError('physics forbidden')):
            refined = checker.evaluate(LEFT, require_fixed_gripper=False)
        self.assertTrue(refined['valid'])
        self.assertEqual(refined['checked_pairs'], 285)
        self.assertEqual(refined['certified_pairs'], 285)
        self.assertGreaterEqual(refined['min_distance_m'], .001)
        # The repaired left wall pair is clear by ~12mm. The global minimum
        # remains the ~1.4mm lower-arm/y-wall pair, not that larger new bound.
        self.assertLess(refined['min_distance_m'], .002)
        self.assertEqual(refined['pair'], ['pick_wall_y_1', 'collision_lower_arm_1'])
        self.assertEqual(checker.mesh_box_refinement_stats['certified_frames'], 1)
        self.assertEqual(checker.mesh_box_refinement_stats['certified_pairs'], 1)

    def test_real_right_still_rejected_and_box_box_not_eligible(self):
        checker = self.checker(True)
        baseline = self.original(checker, RIGHT)
        result = checker.evaluate(RIGHT, require_fixed_gripper=False)
        self.assertEqual(result, baseline)
        self.assertFalse(result['valid'])
        self.assertEqual(result['checked_pairs'], 285)
        box_checker = self.checker(True, mujoco.MjModel.from_xml_string(rig_xml()))
        with patch.object(box_checker.native, 'certify_directions') as certify:
            blocked = box_checker.evaluate(np.r_[np.zeros(5), .25], require_fixed_gripper=False)
        self.assertFalse(blocked['valid'])
        certify.assert_not_called()
        self.assertEqual(box_checker.mesh_box_refinement_stats['pair_queries'], 0)

    def test_default_false_is_original_result_without_optional_work(self):
        checker = self.checker()
        for q in (LEFT, RIGHT, np.r_[LEFT[:5], .35]):
            with self.subTest(q=q.tolist()), patch.object(MeshBoxAxes, 'refine') as refine:
                expected = self.original(checker, q)
                self.assertEqual(checker.evaluate(q, require_fixed_gripper=False), expected)
                refine.assert_not_called()
        self.assertIsNone(checker._mesh_box_axes)
        self.assertEqual(checker.mesh_box_refinement_stats['attempted_frames'], 0)

    def test_limits_fixed_jaw_nonfinite_and_low_margin_reject_before_refinement(self):
        checker = self.checker(True)
        with patch.object(MeshBoxAxes, 'refine') as refine:
            for q, fixed, reason in ((np.r_[LEFT[:5], .35], True, 'gripper_not_fixed'),
                    (np.r_[LEFT[:5], np.nan], False, 'configuration_shape_or_nonfinite'),
                    (np.r_[np.full(5, 100.), .5], False, 'joint_limit')):
                with self.subTest(reason=reason):
                    result = checker.evaluate(q, require_fixed_gripper=fixed)
                    self.assertFalse(result['valid'])
                    self.assertEqual(result['reason'], reason)
            for margin in (.0009, 0., np.nan, np.inf):
                with self.subTest(margin=margin), self.assertRaises(ValueError):
                    checker.evaluate(LEFT, certificate_margin_m=margin)
            refine.assert_not_called()

    def test_original_environment_or_backend_errors_cannot_be_refined(self):
        checker = self.checker(True)
        original_summary = checker._native_query.summary
        summary = original_summary(checker.data.geom_xpos[checker.geometry_ids],
            checker.data.geom_xmat[checker.geometry_ids].reshape(-1, 3, 3), .001)
        for reason in ('invalid_arithmetic_environment', 'nonfinite_or_unsupported_arithmetic',
                       'invalid_pair_index', 'invalid_margin'):
            bad = dict(summary, valid=False, certificate_reason=reason)
            with self.subTest(reason=reason), patch.object(checker._native_query, 'summary', return_value=bad), \
                    patch.object(checker.native, 'certify_directions') as certify:
                result = checker.evaluate(LEFT, require_fixed_gripper=False)
                self.assertFalse(result['valid'])
                certify.assert_not_called()
        with patch.object(checker._native_query, 'summary', side_effect=RuntimeError('ABI error')):
            self.assertEqual(checker.evaluate(LEFT, require_fixed_gripper=False)['reason'],
                             'geometry_certificate_unavailable')

    def test_actual_unsupported_arithmetic_environment_cannot_be_refined(self):
        checker = self.checker(True)
        libm = ctypes.CDLL('libm.so.6')
        rounding = libm.fegetround()
        try:
            self.assertEqual(libm.fesetround(0x400), 0)
            with patch.object(checker.native, 'certify_directions') as certify:
                result = checker.evaluate(LEFT, require_fixed_gripper=False)
        finally:
            libm.fesetround(rounding)
        self.assertFalse(result['valid'])
        self.assertEqual(result['certificate_reason'], 'invalid_arithmetic_environment')
        certify.assert_not_called()

    def test_every_missing_pair_must_be_certified_not_just_first(self):
        checker = self.checker()
        baseline = self.original(checker)
        details = self.details(checker)
        missing = int(np.flatnonzero(~details['certified'])[0])
        # A second reported mesh/box failure must be processed even after the
        # first pair is repaired. Simulate a second valid ABI no-certificate row.
        mesh, box = int(mujoco.mjtGeom.mjGEOM_MESH), int(mujoco.mjtGeom.mjGEOM_BOX)
        second = next(i for i, pair in enumerate(checker.pairs) if i != missing
            and sorted(int(checker.model.geom_type[g]) for g in pair) == sorted((mesh, box)))
        details['certified'][second] = False
        details['reason'][second] = 'no_separation_certificate'
        baseline = dict(baseline, certified_pairs=283)
        # Obtain a fresh one-row native certificate rather than inventing one.
        axes = MeshBoxAxes(self.model)
        pair = checker.pair_indices[missing]
        valid = checker.native.certify_directions(checker.data.geom_xpos[checker.geometry_ids],
            checker.data.geom_xmat[checker.geometry_ids].reshape(-1, 3, 3), pair,
            axes.directions(checker.data, *checker.pairs[missing]), .001)
        failed = deepcopy(valid)
        failed['certified'][0] = False
        failed['reason'][0] = 'no_separation_certificate'
        failed['lower_bound_m'][0] = 0.
        with patch.object(checker.native, 'evaluate', return_value=details), \
                patch.object(axes, 'directions', return_value=np.array([[1., 0., 0.]])), \
                patch.object(checker.native, 'certify_directions', side_effect=[valid, failed]) as certify:
            result = axes.refine(checker, baseline)
        self.assertEqual(certify.call_count, 2)
        self.assertEqual(len(result['pairs']), 2)
        self.assertFalse(result['supplemental_valid'])
        self.assertEqual(result['refined_result'], baseline)

    def test_any_original_detail_error_or_malformed_array_keeps_original_rejection(self):
        checker = self.checker(True)
        baseline = self.original(checker)
        details = self.details(checker)
        mutations = [lambda d: d['reason'].__setitem__(0, 'invalid_arithmetic_environment'),
                     lambda d: d['lower_bound_m'].__setitem__(0, np.nan),
                     lambda d: d.__setitem__('certified', d['certified'][:-1]),
                     lambda d: d['evaluations'].__setitem__(0, -1),
                     lambda d: d['n'].__setitem__((0, 0), np.inf)]
        for mutate in mutations:
            bad = deepcopy(details); mutate(bad)
            with self.subTest(mutation=mutate), patch.object(checker.native, 'evaluate', return_value=bad), \
                    patch.object(checker.native, 'certify_directions') as certify:
                self.assertEqual(checker.evaluate(LEFT, require_fixed_gripper=False), baseline)
                certify.assert_not_called()
        with patch.object(checker.native, 'evaluate', side_effect=RuntimeError('detail ABI unavailable')):
            self.assertEqual(checker.evaluate(LEFT, require_fixed_gripper=False), baseline)

    def test_supplemental_abi_errors_and_inconsistent_certificates_never_pass(self):
        checker = self.checker(True)
        baseline = self.original(checker)
        axes = MeshBoxAxes(self.model)
        details = self.details(checker)
        index = int(np.flatnonzero(~details['certified'])[0])
        valid = checker.native.certify_directions(checker.data.geom_xpos[checker.geometry_ids],
            checker.data.geom_xmat[checker.geometry_ids].reshape(-1, 3, 3), checker.pair_indices[index],
            axes.directions(checker.data, *checker.pairs[index]), .001)
        mutations = [lambda d: d['reason'].__setitem__(0, 'invalid_arithmetic_environment'),
                     lambda d: d['lower_bound_m'].__setitem__(0, .0009),
                     lambda d: d['squared_gap_lower'].__setitem__(0, 0.),
                     lambda d: d['support_mode'].__setitem__(0, 'enclosing_local_AABB'),
                     lambda d: d['n'].__setitem__((0, 0), np.nan),
                     lambda d: d.__setitem__('certified', d['certified'].astype(int)),
                     lambda d: d.__setitem__('reason', d['reason'][:0])]
        for mutate in mutations:
            bad = deepcopy(valid); mutate(bad)
            with self.subTest(mutation=mutate), patch.object(checker.native, 'certify_directions', return_value=bad):
                self.assertEqual(checker.evaluate(LEFT, require_fixed_gripper=False), baseline)
        with patch.object(checker.native, 'certify_directions', side_effect=RuntimeError('closed backend')):
            self.assertEqual(checker.evaluate(LEFT, require_fixed_gripper=False), baseline)
        self.assertEqual(checker.mesh_box_refinement_stats['certified_frames'], 0)

    def test_inspection_does_not_recurse_and_each_frame_reprojects(self):
        checker = self.checker(True)
        axes = MeshBoxAxes(self.model)
        with patch.object(checker, 'evaluate', side_effect=AssertionError('recursive public evaluation')) as public:
            inspected = axes.inspect(checker, LEFT)
        public.assert_not_called()
        self.assertFalse(inspected['original']['valid'])
        self.assertTrue(inspected['supplemental_valid'])
        with patch.object(checker.native, 'certify_directions', wraps=checker.native.certify_directions) as certify:
            checker.evaluate(LEFT, require_fixed_gripper=False)
            checker.evaluate(LEFT, require_fixed_gripper=False)
        self.assertEqual(certify.call_count, 2)
        self.assertIsNot(certify.call_args_list[0].args[0], certify.call_args_list[1].args[0])

    def warm_hint(self):
        checker = self.checker(True)
        self.assertTrue(checker.evaluate(LEFT, require_fixed_gripper=False)['valid'])
        axes = checker._mesh_box_axes
        self.assertEqual(axes.hint_stats['full_direction_searches'], 1)
        self.assertEqual(axes.hint_stats['hint_attempts'], 0)
        return checker, axes

    def test_real_adjacent_pose_reprojects_one_hint_after_full_cold_search(self):
        checker = self.checker(True)
        with patch.object(checker.native, 'certify_directions', wraps=checker.native.certify_directions) as certify, \
                patch.object(checker.native, 'evaluate', wraps=checker.native.evaluate) as detail:
            first = checker.evaluate(LEFT, require_fixed_gripper=False)
            adjacent = LEFT.copy(); adjacent[0] += 1e-6
            second = checker.evaluate(adjacent, require_fixed_gripper=False)
        self.assertTrue(first['valid'] and second['valid'])
        self.assertEqual(detail.call_count, 2)
        self.assertEqual(certify.call_count, 2)
        self.assertGreater(len(certify.call_args_list[0].args[3]), 1)
        self.assertEqual(certify.call_args_list[1].args[3].shape, (1, 3))
        self.assertEqual(checker.mesh_box_refinement_stats['hint_successes'], 1)
        self.assertEqual(checker.mesh_box_refinement_stats['full_direction_searches'], 1)
        self.assertEqual(second['checked_pairs'], 285)
        self.assertEqual(second['certified_pairs'], 285)
        self.assertTrue(all(len(v) == 3 for v in checker._mesh_box_axes._direction_hints.values()))

    def test_real_244_point_closure_keeps_every_original_pair_query(self):
        checker = self.checker(True)
        results = []
        def valid(q):
            result = checker.evaluate(q, require_fixed_gripper=False)
            results.append(result)
            return result['valid']
        end = LEFT.copy(); end[5] = .015
        with patch.object(checker._native_query, 'summary', wraps=checker._native_query.summary) as summary, \
                patch.object(checker.native, 'evaluate', wraps=checker.native.evaluate) as detail:
            sweep = validate_configuration_path(LEFT, end, valid)
        self.assertTrue(sweep['valid'])
        self.assertEqual(sweep['checked_states'], 244)
        self.assertEqual(summary.call_count, 244)
        self.assertEqual(detail.call_count, checker.mesh_box_refinement_stats['attempted_frames'])
        self.assertTrue(all(r['checked_pairs'] == 285 and r['certified_pairs'] == 285 for r in results))
        self.assertGreater(checker.mesh_box_refinement_stats['hint_successes'], 0)

    def test_hint_negative_gap_nan_gate_is_discarded_then_full_search_runs(self):
        checker, axes = self.warm_hint()
        key = next(iter(axes._direction_hints))
        first, second, native_first, native_second = key
        mesh_gid = first if int(self.model.geom_type[first]) == int(mujoco.mjtGeom.mjGEOM_MESH) else second
        mesh_r = checker.data.geom_xmat[mesh_gid].reshape(3, 3)
        axes._direction_hints[key] = tuple(np.linalg.solve(mesh_r, [1., 0., 0.]))
        miss = checker.native.certify_directions(checker.data.geom_xpos[checker.geometry_ids],
            checker.data.geom_xmat[checker.geometry_ids].reshape(-1, 3, 3),
            [native_first, native_second], [[1., 0., 0.]], .001)
        self.assertFalse(miss['certified'][0])
        self.assertLessEqual(miss['gap_lower'][0], 0)
        self.assertTrue(np.isnan(miss['squared_gap_lower'][0]))
        before = checker.mesh_box_refinement_stats['pair_queries']
        with patch.object(checker.native, 'certify_directions', wraps=checker.native.certify_directions) as certify:
            result = checker.evaluate(LEFT, require_fixed_gripper=False)
        self.assertTrue(result['valid'])
        self.assertEqual(certify.call_count, 2)
        self.assertEqual(checker.mesh_box_refinement_stats['pair_queries'] - before, 2)
        self.assertEqual(axes.hint_stats['hint_misses'], 1)
        self.assertEqual(axes.hint_stats['full_direction_searches'], 2)
        self.assertEqual(checker.mesh_box_refinement_stats['error_frames'], 0)

    def test_hint_abi_errors_are_rejected_without_full_search_rescue(self):
        checker, axes = self.warm_hint()
        # Capture the native one-direction answer from an ordinary successful hint.
        original = checker.native.certify_directions
        answers = []
        def capture(*args):
            value = original(*args); answers.append(deepcopy(value)); return value
        with patch.object(checker.native, 'certify_directions', side_effect=capture):
            self.assertTrue(checker.evaluate(LEFT, require_fixed_gripper=False)['valid'])
        current = answers[0]
        changes = [lambda d: d['reason'].__setitem__(0, 'invalid_arithmetic_environment'),
                   lambda d: d['evaluations'].__setitem__(0, 2),
                   lambda d: d['direction_index'].__setitem__(0, 7),
                   lambda d: d['n'].__setitem__((0, 0), np.nan),
                   lambda d: d['support_mode'].__setitem__(0, 'enclosing_local_AABB'),
                   lambda d: d.__setitem__('certified', d['certified'].astype(int)),
                   lambda d: d.__setitem__('reason', d['reason'][:0])]
        for change in changes:
            bad = deepcopy(current); change(bad)
            with self.subTest(change=change), patch.object(checker.native, 'certify_directions', return_value=bad) as query:
                baseline = self.original(checker)
                self.assertEqual(checker.evaluate(LEFT, require_fixed_gripper=False), baseline)
                self.assertEqual(query.call_count, 1)
        with patch.object(checker.native, 'certify_directions', side_effect=RuntimeError('ABI failure')) as query:
            self.assertFalse(checker.evaluate(LEFT, require_fixed_gripper=False)['valid'])
            self.assertEqual(query.call_count, 1)
        self.assertEqual(axes.hint_stats['hint_misses'], 0)

    def test_direction_owner_does_not_cross_checkers_or_models_and_default_is_cold(self):
        checker, axes = self.warm_hint()
        other = self.checker()
        before = axes.hint_stats['hint_attempts']
        self.assertTrue(axes.inspect(other, LEFT)['supplemental_valid'])
        self.assertEqual(axes.hint_stats['hint_attempts'], before)
        self.assertIs(axes._hint_owner[0], other)
        changed = self.checker(model=deepcopy(self.model))
        result = axes.inspect(changed, LEFT)
        self.assertFalse(result['supplemental_valid'])
        self.assertIn('original model', result['error'])
        diagnostic = MeshBoxAxes(self.model)
        diagnostic.inspect(checker, LEFT); diagnostic.inspect(checker, LEFT)
        self.assertEqual(diagnostic.hint_stats['hint_attempts'], 0)
        self.assertEqual(diagnostic.hint_stats['full_direction_searches'], 2)
        self.assertEqual(diagnostic._direction_hints, {})

    def test_failed_later_pair_cannot_publish_pending_direction_hints(self):
        checker = self.checker()
        baseline = self.original(checker)
        details = self.details(checker)
        missing = int(np.flatnonzero(~details['certified'])[0])
        mesh, box = int(mujoco.mjtGeom.mjGEOM_MESH), int(mujoco.mjtGeom.mjGEOM_BOX)
        second = next(i for i, pair in enumerate(checker.pairs) if i != missing
            and sorted(int(self.model.geom_type[g]) for g in pair) == sorted((mesh, box)))
        details['certified'][second] = False
        details['reason'][second] = 'no_separation_certificate'
        baseline = dict(baseline, certified_pairs=283)
        axes = MeshBoxAxes(self.model, reuse_direction_hints=True)
        valid = checker.native.certify_directions(checker.data.geom_xpos[checker.geometry_ids],
            checker.data.geom_xmat[checker.geometry_ids].reshape(-1, 3, 3), checker.pair_indices[missing],
            axes.directions(checker.data, *checker.pairs[missing]), .001)
        failed = deepcopy(valid); failed['certified'][0] = False
        failed['reason'][0] = 'no_separation_certificate'; failed['lower_bound_m'][0] = 0.
        with patch.object(checker.native, 'evaluate', return_value=details), \
                patch.object(axes, 'directions', return_value=np.array([[1., 0., 0.]])), \
                patch.object(checker.native, 'certify_directions', side_effect=[valid, failed]):
            result = axes.refine(checker, baseline)
        self.assertFalse(result['supplemental_valid'])
        self.assertEqual(result['refined_result'], baseline)
        self.assertEqual(axes._direction_hints, {})


if __name__ == '__main__':
    unittest.main()
