"""CPU ownership, complete coverage and saved-geometry admission regressions."""
from dataclasses import FrozenInstanceError, replace
import json
import math
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import Mock, patch

import numpy as np

from grasp_episode import PAD_NAMES
from joint_planner import validate_joint_path
from separation_worker import (AsyncSeparationPlanningJob, SeparationPlan,
                               SeparationSample, SeparationSnapshot,
                               run_separation_plan, separation_sample_coordinates,
                               validate_separation_samples)
from transport_worker import AsyncTransportPlanningJob, TransportPlan


class SeparationWorkerTests(unittest.TestCase):
    def snapshot(self, **changes):
        values = dict(q6=[0., -.0, 0., 0., 0., .5], initial_q6=[-.1, 0., 0., 0., 0., .5],
                      last_command6=[0., -.0, 0., 0., 0., .5], seed=11,
                      elapsed=60., center=[.24, .13, .010], uncertainty=.002)
        values.update(changes)
        return SeparationSnapshot(**values)

    def paths(self):
        separation = [[i*.003, -.0, 0., 0., 0.] for i in range(14)]
        return [separation, [separation[-1], [-.1, 0., 0., 0., 0.]]]

    def report(self, paths):
        record = dict(separation_path=paths[0], planned_return_path=paths[1],
                      initial_distances_m={name: .002 for name in (*PAD_NAMES, 'robot_mesh')})
        return json.dumps(dict(plan_reports=[dict(stage='release_return_budget'),
                                            dict(stage='release_return', **record)],
                               release_record=record), allow_nan=False)

    def sample(self, q5, **changes):
        distances = {name: .002 for name in (*PAD_NAMES, 'robot_mesh')}
        values = dict(q5=q5, pinch3=[0., 0., .05], distances=distances,
                      pad_vertices={name: np.zeros((8, 3)) for name in PAD_NAMES})
        values.update(changes)
        return SeparationSample(**values)

    def plan(self, **changes):
        paths = self.paths()
        values = dict(paths=paths, report_json=self.report(paths), snapshot=self.snapshot(),
                      samples=[self.sample(q) for q in separation_sample_coordinates(paths[0])])
        values.update(changes)
        return SeparationPlan(**values)

    def guards(self, **changes):
        values = dict(pinch=[0., 0., .05], floors={}, vertices={}, high_z={},
                      expected_names=(*PAD_NAMES, 'robot_mesh'))
        values.update(changes)
        return values

    def replace_sample(self, plan, index, **changes):
        samples = list(plan.samples)
        samples[index] = replace(samples[index], **changes)
        return replace(plan, samples=samples)

    def test_snapshot_owns_inputs_preserves_signed_zero_and_is_frozen(self):
        q, center = np.array([0., -.0, 0., 0., 0., .5]), [.24, .13, .010]
        snapshot = self.snapshot(q6=q, center=center)
        saved = np.asarray(snapshot.q6).tobytes()
        q[:] = 99.; center[:] = [99.]*3
        self.assertEqual(np.asarray(snapshot.q6).tobytes(), saved)
        self.assertEqual(snapshot.center, (.24, .13, .010))
        self.assertEqual(np.asarray(snapshot.q6).view(np.uint64)[1], 1 << 63)
        with self.assertRaises(FrozenInstanceError):
            snapshot.elapsed = 0.

    def test_snapshot_and_sample_reject_nonfinite_or_malformed_geometry(self):
        for changes in ({'q6': [0.]*5}, {'initial_q6': [math.nan]*6},
                        {'last_command6': [math.inf]*6}, {'seed': True}, {'seed': 1.5},
                        {'elapsed': -1.}, {'elapsed': math.inf}, {'center': [0., math.nan, 0.]},
                        {'uncertainty': .001}, {'uncertainty': math.inf}):
            with self.subTest(changes=changes), self.assertRaises((TypeError, ValueError)):
                self.snapshot(**changes)
        for changes in ({'q5': [0.]*4}, {'pinch3': [0., math.nan, 0.]},
                        {'distances': [('robot_mesh', .002), ('robot_mesh', .002)]},
                        {'distances': {name: math.nan for name in PAD_NAMES}},
                        {'pad_vertices': {name: np.zeros((7, 3)) for name in PAD_NAMES}},
                        {'pad_vertices': {PAD_NAMES[0]: np.zeros((8, 3))}}):
            with self.subTest(changes=changes), self.assertRaises((TypeError, ValueError)):
                values = dict(q5=[0.]*5); values.update(changes)
                self.sample(**values)

    def test_sample_owns_distances_pinches_and_all_pad_vertices(self):
        pinch = np.array([0., 0., .05])
        pads = {name: np.zeros((8, 3)) for name in PAD_NAMES}
        distances = {name: .002 for name in (*PAD_NAMES, 'robot_mesh')}
        row = self.sample([0.]*5, pinch3=pinch, pad_vertices=pads, distances=distances)
        pinch[:] = 99.; pads[PAD_NAMES[0]][:] = 99.; distances['robot_mesh'] = -99.
        self.assertEqual(row.pinch3, (0., 0., .05))
        self.assertEqual(dict(row.distances)['robot_mesh'], .002)
        self.assertTrue((np.asarray(dict(row.pad_vertices)[PAD_NAMES[0]]) == 0.).all())
        with self.assertRaises(FrozenInstanceError):
            row.distances = ()

    def test_plan_owns_paths_and_requires_each_original_repeated_sample(self):
        paths = self.paths()
        samples = [self.sample(q) for q in separation_sample_coordinates(paths[0])]
        plan = self.plan(paths=paths, samples=samples, report_json=self.report(paths))
        self.assertEqual(len(samples), 39)  # Thirteen 3-callback edges, not fourteen endpoints.
        self.assertEqual(np.asarray(samples[2].q5).tobytes(), np.asarray(samples[3].q5).tobytes())
        saved = np.asarray(plan.paths[0]).tobytes()
        paths[0][0][0] = 9.; samples.pop()
        self.assertEqual(np.asarray(plan.paths[0]).tobytes(), saved)
        self.assertEqual(len(plan.samples), 39)
        with self.assertRaises(FrozenInstanceError):
            plan.samples = ()
        for altered in (plan.samples[:-1], plan.samples[::2], tuple(reversed(plan.samples))):
            with self.subTest(count=len(altered)), self.assertRaises(ValueError):
                replace(plan, samples=altered)

    def test_sample_coverage_rejects_one_ulp_and_changed_geometry_names(self):
        plan = self.plan()
        q = list(plan.samples[1].q5)
        q[0] = np.nextafter(q[0], math.inf)
        with self.assertRaises(ValueError):
            self.replace_sample(plan, 1, q5=q)
        distances = dict(plan.samples[1].distances)
        distances['extra_mesh'] = .002
        with self.assertRaises(ValueError):
            self.replace_sample(plan, 1, distances=distances)

    def test_report_requires_finite_matching_original_terminal_paths(self):
        plan = self.plan()
        for text in ('{}', '{"value":NaN}', '{"value":1e999}', 'not JSON'):
            with self.subTest(text=text), self.assertRaises((ValueError, TypeError)):
                replace(plan, report_json=text)
        altered = json.loads(plan.report_json)
        altered['release_record']['separation_path'][0][1] = .0
        with self.assertRaises(ValueError):
            replace(plan, report_json=json.dumps(altered))
        altered = json.loads(plan.report_json)
        altered['release_record']['separation_path'] = np.asarray(plan.paths[0]).reshape(-1).tolist()
        with self.assertRaises(ValueError):
            replace(plan, report_json=json.dumps(altered))

    def test_containment_checks_interior_floor_at_first_failure(self):
        plan = self.plan()
        self.assertTrue(validate_separation_samples(plan, **self.guards())['valid'])
        distances = dict(plan.samples[17].distances)
        distances['robot_mesh'] = np.nextafter(.001, -math.inf)
        plan = self.replace_sample(plan, 17, distances=distances)
        result = validate_separation_samples(plan, **self.guards())
        self.assertFalse(result['valid'])
        self.assertEqual(result['reason'], 'distance_floor')
        self.assertEqual(result['invalid_sample_index'], 17)
        self.assertEqual(result['checked_samples'], 18)
        self.assertEqual(result['sample_count'], 39)

    def test_cleared_pad_cannot_reuse_old_contact_exception(self):
        plan = self.plan(); name = PAD_NAMES[0]
        distances = dict(plan.samples[17].distances); distances[name] = .0005
        plan = self.replace_sample(plan, 17, distances=distances)
        baseline = {name: np.zeros((8, 3))}; heights = {name: np.zeros(8)}
        allowed = self.guards(floors={name: .0004}, vertices=baseline, high_z=heights)
        self.assertTrue(validate_separation_samples(plan, **allowed)['valid'])
        allowed['floors'] = {}
        result = validate_separation_samples(plan, **allowed)
        self.assertFalse(result['valid'])
        self.assertEqual(result['invalid_sample_index'], 17)

    def test_live_high_z_and_xy_guards_reject_old_safe_suffix(self):
        plan = self.plan(); name = PAD_NAMES[0]
        baseline = {name: np.zeros((8, 3))}
        guards = self.guards(vertices=baseline, high_z={name: np.zeros(8)})
        for coordinate, value in ((0, np.nextafter(.0002, math.inf)),
                                  (2, np.nextafter(-.00005, -math.inf))):
            pads = {k: np.asarray(v) for k, v in plan.samples[17].pad_vertices}
            pads[name] = pads[name].copy(); pads[name][3, coordinate] = value
            altered = self.replace_sample(plan, 17, pad_vertices=pads)
            result = validate_separation_samples(altered, **guards)
            self.assertFalse(result['valid'])
            self.assertEqual(result['invalid_sample_index'], 17)
            self.assertEqual(result['reason'], 'pad_monotonic_guard')
        guards['high_z'][name][3] = np.nextafter(.00005, math.inf)
        self.assertFalse(validate_separation_samples(plan, **guards)['valid'])

    def test_exact_original_pinches_and_pad_thresholds_are_not_relaxed(self):
        plan = self.plan(); name = PAD_NAMES[0]
        pads = {k: np.asarray(v) for k, v in plan.samples[17].pad_vertices}
        pads[name] = pads[name].copy(); pads[name][0, 0] = .0002; pads[name][0, 2] = -.00005
        altered = self.replace_sample(plan, 17, pinch3=[.0002, 0., .05], pad_vertices=pads)
        guards = self.guards(vertices={name: np.zeros((8, 3))}, high_z={name: np.zeros(8)})
        self.assertTrue(validate_separation_samples(altered, **guards)['valid'])
        altered = self.replace_sample(altered, 17, pinch3=[np.nextafter(.0002, math.inf), 0., .05])
        self.assertFalse(validate_separation_samples(altered, **guards)['valid'])
        with self.assertRaises(ValueError):
            validate_separation_samples(plan, **self.guards(floors={name: .0004}))
        for names in ((*PAD_NAMES,), (*PAD_NAMES, 'robot_mesh', 'missing_mesh'),
                      (*PAD_NAMES, 'robot_mesh', 'robot_mesh')):
            with self.subTest(names=names), self.assertRaises(ValueError):
                validate_separation_samples(plan, **self.guards(expected_names=names))

    def fake_context(self):
        context = SimpleNamespace(released_query=SimpleNamespace(data=SimpleNamespace(qpos=np.zeros(6))),
                                  checker=SimpleNamespace(native=SimpleNamespace(close=Mock())),
                                  plan_reports=[], release_record={})
        counts = dict(fk=0, distances=0, pads=0)
        def fk(q6):
            counts['fk'] += 1
            return np.zeros(3), np.eye(3), np.array([0., 0., .05])
        def distances(q6):
            counts['distances'] += 1
            context.released_query.data.qpos[:] = q6
            return {name: .002 for name in (*PAD_NAMES, 'robot_mesh')}
        def pads():
            counts['pads'] += 1
            return {name: np.zeros((8, 3)) for name in PAD_NAMES}
        def valid(q5, jaw=.5):
            context._fk(np.r_[q5, jaw])
            context.released_query.distances(np.r_[q5, jaw])
            context.released_query.pad_vertices()
            return True
        context._fk, context.released_query.distances = fk, distances
        context.released_query.pad_vertices, context._separation_valid = pads, valid
        context._released_valid = lambda q5, jaw=.5: bool(context.released_query.distances(np.r_[q5, jaw]))
        return context, counts

    def fake_compute(self, context, q6, elapsed):
        paths = self.paths()
        for a, b in zip(paths[0], paths[0][1:]):
            self.assertTrue(validate_joint_path([a, b], context._separation_valid, .002)['valid'])
        context.release_record = json.loads(self.report(paths))['release_record']
        context.plan_reports = json.loads(self.report(paths))['plan_reports']
        context.separation_pinch = np.array([0., 0., .05])
        context.separation_floors, context.separation_vertices, context.separation_high_z = {}, {}, {}

    def test_worker_records_existing_geometry_without_extra_queries_and_closes(self):
        from visual_grasp_controller import VisualGraspController
        context, counts = self.fake_context()
        with patch('separation_worker._planning_context', return_value=context), \
                patch.object(VisualGraspController, '_legacy_plan_separation', side_effect=self.fake_compute, create=True):
            plan = run_separation_plan(object(), object(), self.snapshot())
        self.assertEqual(counts, dict(fk=39, distances=39, pads=39))
        self.assertEqual(len(plan.samples), 39)
        self.assertEqual(json.loads(plan.report_json)['worker_steps']['separation_callbacks'], 39)
        context.checker.native.close.assert_called_once_with()

    def test_worker_cancellation_failure_and_capture_mismatch_close_without_plan(self):
        from visual_grasp_controller import VisualGraspController
        event = threading.Event(); event.set()
        with patch('separation_worker._planning_context') as create:
            with self.assertRaisesRegex(RuntimeError, 'cancelled'):
                run_separation_plan(object(), object(), self.snapshot(), event)
            create.assert_not_called()
        for failure in ('exception', 'bad_pose', 'mid_callback_cancel'):
            context, _ = self.fake_context()
            running_cancel = threading.Event()
            if failure == 'bad_pose':
                old = context.released_query.pad_vertices
                def bad_pads():
                    result = old(); context.released_query.data.qpos[0] += .001; return result
                context.released_query.pad_vertices = bad_pads
            if failure == 'mid_callback_cancel':
                original = context._separation_valid
                def cancel_after_query(q5, jaw=.5):
                    result = original(q5, jaw); running_cancel.set(); return result
                context._separation_valid = cancel_after_query
            compute = Mock(side_effect=RuntimeError('original_failure')) if failure == 'exception' else self.fake_compute
            with patch('separation_worker._planning_context', return_value=context), \
                    patch.object(VisualGraspController, '_legacy_plan_separation', side_effect=compute, create=True):
                with self.assertRaises(RuntimeError):
                    run_separation_plan(object(), object(), self.snapshot(), running_cancel)
            context.checker.native.close.assert_called_once_with()

    def test_async_job_reuses_lifecycle_and_consumes_typed_proposal_once(self):
        binding = SimpleNamespace(matches=lambda other: other is binding)
        job = AsyncSeparationPlanningJob(binding)
        self.addCleanup(job.close)
        entered, release = threading.Event(), threading.Event()
        def compute():
            entered.set()
            if not release.wait(2.):
                raise TimeoutError('test did not release separation worker')
            return self.plan()
        job.start(compute)
        try:
            self.assertTrue(entered.wait(2.))
            self.assertFalse(job.poll())
            self.assertEqual(job.state, 'running')
        finally:
            release.set(); job._thread.join(2.)
        self.assertTrue(job.poll())
        self.assertTrue(job.execution['joined'])
        self.assertIsInstance(job.consume(binding), SeparationPlan)
        with self.assertRaises(RuntimeError):
            job.consume(binding)
        transport = AsyncTransportPlanningJob(binding)
        self.addCleanup(transport.close)
        self.assertIs(transport._plan_type, TransportPlan)

    def test_async_wrong_type_and_context_rejection_never_revive(self):
        binding = SimpleNamespace(matches=lambda other: other is binding)
        wrong = AsyncSeparationPlanningJob(binding); self.addCleanup(wrong.close)
        wrong.start(lambda: object()); wrong._thread.join(2.)
        with self.assertRaises(TypeError):
            wrong.poll()
        job = AsyncSeparationPlanningJob(binding); self.addCleanup(job.close)
        job.start(self.plan); job._thread.join(2.)
        self.assertTrue(job.poll())
        with self.assertRaises(RuntimeError):
            job.consume(object())
        self.assertEqual(job.state, 'rejected')
        with self.assertRaises(RuntimeError):
            job.consume(binding)


if __name__ == '__main__':
    unittest.main(verbosity=2)
