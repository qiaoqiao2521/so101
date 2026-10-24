"""Same-call raw detail reuse: original FK/certificates, no integration."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import mujoco
import numpy as np

from conservative_collision import ConservativeCollisionChecker
from configuration_sweep import validate_configuration_path
from grasp_episode import build_contact_scene
from grasp_workcell import TARGET_SIZE
from mesh_box_axes import MeshBoxAxes
from route_policy import RoutePolicy
from separation_worker import SeparationSnapshot, _planning_context
from test_conservative_collision import rig_xml
from test_mesh_box_refinement import LEFT, RIGHT, SOURCE
from transport_worker import TransportSnapshot
from visual_grasp_controller import _run_transport_plan


class RefinementDetailsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix='refinement-details-')
        _, cls.model, _ = build_contact_scene(SOURCE, Path(cls.folder.name))

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def checker(self, reuse=True, refine=True, model=None):
        checker = ConservativeCollisionChecker(self.model if model is None else model,
            gripper=.5, margin_m=.001, mesh_box_axis_refinement=refine,
            reuse_refinement_details=reuse)
        self.addCleanup(checker.native.close)
        return checker

    def test_same_call_retains_full_results_hints_and_supplemental_work(self):
        baseline, candidate = self.checker(False), self.checker()
        for hints in (False, True):
            for q in (LEFT, np.r_[LEFT[:5], .35], RIGHT):
                with self.subTest(hints=hints, q=q.tolist()):
                    with patch.object(candidate.native, 'evaluate', wraps=candidate.native.evaluate) as raw:
                        actual = candidate.evaluate(q, require_fixed_gripper=False, direction_hints=hints)
                    expected = baseline.evaluate(q, require_fixed_gripper=False, direction_hints=hints)
                    self.assertEqual(actual, expected)
                    if np.array_equal(q, RIGHT):
                        # Original uncertified detail has rejected numeric
                        # sentinels; optional handoff must take the original
                        # detail/error path instead of treating it as proof.
                        self.assertFalse(actual['valid'])
                        raw.assert_called_once()
                    else:
                        raw.assert_not_called()
                    self.assertEqual(candidate.mesh_box_refinement_stats, baseline.mesh_box_refinement_stats)
                    self.assertEqual(candidate._mesh_box_axes._direction_hints,
                                     baseline._mesh_box_axes._direction_hints)
                    np.testing.assert_array_equal(candidate.native._witness_hints,
                                                  baseline.native._witness_hints)

    def test_default_and_refinement_disabled_never_request_optional_details(self):
        for reuse, refine in ((False, True), (True, False)):
            checker = self.checker(reuse, refine)
            with patch.object(checker._native_query, 'summary_with_details',
                              side_effect=AssertionError('optional path forbidden')):
                result = checker.evaluate(LEFT, require_fixed_gripper=False)
            self.assertEqual(result['valid'], refine)

    def test_only_literal_true_enables_the_original_checker_direction_hint_path(self):
        for value in (False, None, 0, 1, np.bool_(True), np.array([False, True])):
            baseline, candidate = self.checker(False), self.checker()
            with self.subTest(value=value):
                expected = baseline.evaluate(LEFT, require_fixed_gripper=False, direction_hints=value)
                actual = candidate.evaluate(LEFT, require_fixed_gripper=False, direction_hints=value)
                self.assertEqual(actual, expected)
                self.assertIsNone(candidate._native_query._scalar_directions)

    def test_optional_copy_failure_falls_back_to_original_detail(self):
        checker = self.checker()
        decode = checker.native._decode
        failed = [False]
        def fail_once(*args):
            if not failed[0]:
                failed[0] = True
                raise MemoryError('optional ownership copy')
            return decode(*args)
        with patch.object(checker.native, '_decode', side_effect=fail_once), \
                patch.object(checker.native, 'evaluate', wraps=checker.native.evaluate) as raw:
            result = checker.evaluate(LEFT, require_fixed_gripper=False)
        self.assertTrue(result['valid'])
        raw.assert_called_once()

    def test_handoff_mismatches_and_second_consume_use_original_query(self):
        original = MeshBoxAxes.refine
        for field in ('qpos', 'positions', 'rotations', 'pairs', 'margin', 'owner', 'model', 'handle'):
            checker = self.checker()
            captured = []
            def inspect(axes, current, result, *, details_provider=None, **kwargs):
                p = current.data.geom_xpos[current.geometry_ids].copy()
                R = current.data.geom_xmat[current.geometry_ids].reshape(-1, 3, 3).copy()
                pairs = current.pair_indices.copy()
                margin = .001
                restore = None
                if field in ('positions', 'rotations'):
                    values = p if field == 'positions' else R
                    values.flat[0] = np.nextafter(values.flat[0], np.inf)
                elif field == 'pairs':
                    pairs = pairs[::-1].copy()
                elif field == 'margin':
                    margin = np.nextafter(margin, np.inf)
                elif field == 'qpos':
                    saved = current.data.qpos.copy()
                    current.data.qpos[0] = np.nextafter(current.data.qpos[0], np.inf)
                    restore = lambda: np.copyto(current.data.qpos, saved)
                else:
                    owner, attribute = (current.native, '_handle') if field == 'handle' else (current, 'native' if field == 'owner' else 'model')
                    saved = getattr(owner, attribute)
                    setattr(owner, attribute, None if field == 'handle' else object())
                    restore = lambda: setattr(owner, attribute, saved)
                try:
                    self.assertIsNone(details_provider(p, R, pairs, margin))
                finally:
                    if restore is not None:
                        restore()
                self.assertIsNone(details_provider(p, R, pairs, .001))
                captured.append((details_provider, p, R, pairs))
                return original(axes, current, result, details_provider=details_provider, **kwargs)
            with self.subTest(field=field), patch.object(MeshBoxAxes, 'refine', new=inspect), \
                    patch.object(checker.native, 'evaluate', wraps=checker.native.evaluate) as raw:
                result = checker.evaluate(LEFT, require_fixed_gripper=False)
                self.assertTrue(result['valid'])
                raw.assert_called_once()
            provider, p, R, pairs = captured[0]
            self.assertIsNone(provider(p, R, pairs, .001))

    def test_checker_reentry_and_extra_native_query_cannot_reuse_outer_details(self):
        original = MeshBoxAxes.refine
        for nested in ('checker', 'native'):
            checker = self.checker()
            def reenter(axes, current, result, *, details_provider=None, **kwargs):
                p = current.data.geom_xpos[current.geometry_ids].copy()
                R = current.data.geom_xmat[current.geometry_ids].reshape(-1, 3, 3).copy()
                if nested == 'checker':
                    # Even a nested rejected input which performs no native work
                    # must invalidate the enclosing checker call's handoff.
                    self.assertFalse(current.evaluate(np.full(6, np.nan))['valid'])
                else:
                    current.native.evaluate(p, R, current.pair_indices, .001)
                self.assertIsNone(details_provider(p, R, current.pair_indices, .001))
                return original(axes, current, result, details_provider=details_provider, **kwargs)
            with self.subTest(nested=nested), patch.object(MeshBoxAxes, 'refine', new=reenter), \
                    patch.object(checker.native, 'evaluate', wraps=checker.native.evaluate) as raw:
                self.assertTrue(checker.evaluate(LEFT, require_fixed_gripper=False)['valid'])
                self.assertEqual(raw.call_count, 1 if nested == 'checker' else 2)

    def test_native_close_before_refinement_keeps_original_rejection(self):
        checker = self.checker()
        original = MeshBoxAxes.refine
        def close(axes, current, result, **kwargs):
            current.native.close()
            return original(axes, current, result, **kwargs)
        with patch.object(MeshBoxAxes, 'refine', new=close), \
                patch.object(checker.native, 'evaluate', wraps=checker.native.evaluate) as raw:
            result = checker.evaluate(LEFT, require_fixed_gripper=False)
        self.assertFalse(result['valid'])
        raw.assert_called_once()
        self.assertEqual(checker.mesh_box_refinement_stats['error_frames'], 1)

    def test_malformed_provider_falls_back_without_removing_original_validation(self):
        checker = self.checker()
        baseline = checker._evaluate_original(LEFT, require_fixed_gripper=False)
        axes = MeshBoxAxes(self.model)
        for provider in (lambda *args: {'certified': np.array([True])},
                         lambda *args: (_ for _ in ()).throw(RuntimeError('optional provider error'))):
            with self.subTest(provider=provider), \
                    patch.object(checker.native, 'evaluate', wraps=checker.native.evaluate) as raw:
                result = axes.refine(checker, baseline, details_provider=provider)
            self.assertTrue(result['supplemental_valid'])
            raw.assert_called_once()

    def test_real_rotating_jaw_contact_is_rejected_with_complete_sampling(self):
        model = mujoco.MjModel.from_xml_string(rig_xml())
        baseline, candidate = self.checker(False, model=model), self.checker(model=model)
        # Independent static MuJoCo contact evidence, not an uncertified SO101
        # pose mislabeled as physical collision. No physical integration runs.
        data = mujoco.MjData(model)
        data.qpos[5] = .25
        mujoco.mj_forward(model, data)
        self.assertGreater(data.ncon, 0)
        self.assertTrue(any(contact.dist < 0 for contact in data.contact))
        opened, closed = np.r_[np.zeros(5), .5], np.r_[np.zeros(5), .015]
        reports = []
        for checker in (baseline, candidate):
            self.assertTrue(checker.evaluate(opened, require_fixed_gripper=False)['valid'])
            self.assertTrue(checker.evaluate(closed, require_fixed_gripper=False)['valid'])
            self.assertFalse(checker.evaluate(np.r_[np.zeros(5), .25], require_fixed_gripper=False)['valid'])
            reports.append(validate_configuration_path(opened, closed,
                lambda q: checker.evaluate(q, require_fixed_gripper=False)['valid']))
        self.assertEqual(*reports)
        self.assertFalse(reports[0]['valid'])
        self.assertEqual(reports[0]['required_states'], 244)

    def test_invalid_inputs_and_original_backend_error_keep_original_results(self):
        baseline, candidate = self.checker(False), self.checker()
        for q in (np.full(6, np.nan), np.full(6, 99.), LEFT[:4]):
            with self.subTest(q=q.tolist()):
                self.assertEqual(baseline.evaluate(q), candidate.evaluate(q))
        with patch.object(candidate._native_query, 'summary', side_effect=RuntimeError('original ABI')):
            result = candidate.evaluate(LEFT, require_fixed_gripper=False)
        self.assertFalse(result['valid'])
        self.assertEqual(result['reason'], 'geometry_certificate_unavailable')
        for value in (1, None, 'true'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ConservativeCollisionChecker(self.model, reuse_refinement_details=value)


class RefinementWorkerOptionTests(unittest.TestCase):
    def test_transport_and_separation_use_the_explicit_choice(self):
        for enabled in (False, True):
            policy = RoutePolicy(reuse_refinement_details=enabled)
            rig = SimpleNamespace(nq=6, nv=6, body=lambda name: SimpleNamespace(id=0))
            snapshot = TransportSnapshot(q6=[0.]*6, target_xy=[.24,-.13],
                payload_relative=[0.,0.,-.03], payload_rotation=np.eye(3), world=[],
                payload_uncertainty=.002, elapsed_s=3., route_policy=policy)
            stop = RuntimeError('stop after checker construction')
            with patch('visual_grasp_controller.mujoco.MjData'), \
                    patch('visual_grasp_controller.CollisionChecker', side_effect=stop) as factory, \
                    self.assertRaisesRegex(RuntimeError, 'stop after'):
                _run_transport_plan(rig, snapshot)
            self.assertEqual(factory.call_args.kwargs.get('reuse_refinement_details',False), enabled)
            self.assertNotIn('mesh_box_axis_refinement', factory.call_args.kwargs)

            sep = SeparationSnapshot(q6=[0.]*5+[.5], initial_q6=[0.]*5+[.5],
                last_command6=[0.]*5+[.5], seed=0, elapsed=60., center=[.24,.14,.01],
                uncertainty=.002, route_policy=policy)
            released = SimpleNamespace(nq=6,nv=6,ngeom=0,
                geom=lambda name:SimpleNamespace(id=0),geom_pos=np.array([sep.center]),
                geom_quat=np.array([[1.,0.,0.,0.]]),
                geom_size=np.array([np.asarray(TARGET_SIZE)/2+.002]))
            with patch('mujoco.MjData'), \
                    patch('conservative_collision.ConservativeCollisionChecker', side_effect=stop) as factory, \
                    self.assertRaisesRegex(RuntimeError, 'stop after'):
                _planning_context(rig, released, sep)
            self.assertEqual(factory.call_args.kwargs.get('reuse_refinement_details',False), enabled)
            self.assertNotIn('mesh_box_axis_refinement', factory.call_args.kwargs)


if __name__ == '__main__':
    unittest.main()
