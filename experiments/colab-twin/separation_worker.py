"""One-request separation proposals and exact saved-sample guard checks.

The caller gives the worker independently owned planning models. No execution
data, physical object pose or contact-force measurement enters this module.
Saved geometry applies only to the same frozen models, release estimate and
binary64 sample coordinates. The controller owns that binding and admission.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from numbers import Integral

import numpy as np

from joint_planner import validate_joint_path
from transport_worker import AsyncTransportPlanningJob


def _vector(value, size, name):
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (size,) or not np.isfinite(array).all():
        raise ValueError(f'{name} requires {size} finite values')
    return tuple(float(x) for x in array)


def _named(value, name, convert):
    rows = value.items() if isinstance(value, dict) else value
    result = []
    for key, item in rows:
        if not isinstance(key, str) or not key or any(key == old for old, _ in result):
            raise ValueError(f'{name} requires unique nonempty geometry names')
        result.append((key, convert(item)))
    return tuple(result)


def _scalar(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('Finite distance or floor required')
    return number


def _pad(value):
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (8, 3) or not np.isfinite(array).all():
        raise ValueError('Each pad requires eight finite XYZ vertices')
    return tuple(tuple(float(x) for x in row) for row in array)


def _bytes(value):
    return np.asarray(value, dtype=np.float64).tobytes()


def _pad_names():
    from grasp_episode import PAD_NAMES
    return set(PAD_NAMES)


@dataclass(frozen=True)
class SeparationSnapshot:
    q6: tuple
    initial_q6: tuple
    last_command6: tuple
    seed: int
    elapsed: float
    center: tuple
    uncertainty: float

    def __post_init__(self):
        for name in ('q6', 'initial_q6', 'last_command6'):
            object.__setattr__(self, name, _vector(getattr(self, name), 6, name))
        object.__setattr__(self, 'center', _vector(self.center, 3, 'center'))
        if isinstance(self.seed, bool) or not isinstance(self.seed, Integral) or self.seed < 0:
            raise ValueError('Seed requires a nonnegative integer')
        object.__setattr__(self, 'seed', int(self.seed))
        elapsed, uncertainty = float(self.elapsed), float(self.uncertainty)
        if not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError('Elapsed time requires a finite nonnegative value')
        if not math.isfinite(uncertainty) or not .002 <= uncertainty <= .005:
            raise ValueError('Released-object uncertainty must be 2..5 mm')
        object.__setattr__(self, 'elapsed', elapsed)
        object.__setattr__(self, 'uncertainty', uncertainty)


@dataclass(frozen=True)
class SeparationSample:
    q5: tuple
    pinch3: tuple
    distances: tuple
    pad_vertices: tuple

    def __post_init__(self):
        object.__setattr__(self, 'q5', _vector(self.q5, 5, 'sample q5'))
        object.__setattr__(self, 'pinch3', _vector(self.pinch3, 3, 'sample pinch'))
        distances = _named(self.distances, 'distances', _scalar)
        pads = _named(self.pad_vertices, 'pad vertices', _pad)
        if not distances or set(dict(pads)) != _pad_names():
            raise ValueError('Sample requires distances and both original pads')
        if not set(dict(pads)) <= set(dict(distances)):
            raise ValueError('Every pad needs its original distance')
        object.__setattr__(self, 'distances', distances)
        object.__setattr__(self, 'pad_vertices', pads)


def separation_sample_coordinates(path):
    """Reconstruct original callback order, including repeated edge starts.

    This calls only the pure original sampler. It performs no geometry query.
    """
    samples = []
    for start, end in zip(path, path[1:]):
        report = validate_joint_path([start, end], lambda q: samples.append(tuple(q)) or True, .002)
        if not report['valid']:
            raise ValueError('Malformed separation sample coverage')
    return tuple(samples)


@dataclass(frozen=True)
class SeparationPlan:
    paths: tuple
    report_json: str
    samples: tuple
    snapshot: SeparationSnapshot

    def __post_init__(self):
        if not isinstance(self.snapshot, SeparationSnapshot):
            raise TypeError('Separation plan requires its immutable snapshot')
        paths = tuple(tuple(_vector(q, 5, 'path waypoint') for q in path) for path in self.paths)
        if len(paths) != 2 or len(paths[0]) != 14 or len(paths[1]) < 2:
            raise ValueError('Separation requires fourteen waypoints and a return path')
        if (_bytes(paths[0][0]) != _bytes(self.snapshot.q6[:5]) or
                _bytes(paths[1][0]) != _bytes(paths[0][-1]) or
                _bytes(paths[1][-1]) != _bytes(self.snapshot.initial_q6[:5])):
            raise ValueError('Separation and return endpoints differ from their snapshot')
        samples = tuple(self.samples)
        if not samples or not all(isinstance(row, SeparationSample) for row in samples):
            raise TypeError('Separation plan requires immutable complete samples')
        expected = separation_sample_coordinates(paths[0])
        if len(expected) != len(samples) or any(_bytes(q) != _bytes(row.q5)
                                                for q, row in zip(expected, samples)):
            raise ValueError('Separation samples differ from original complete callback order')
        names = tuple(name for name, _ in samples[0].distances)
        if any(tuple(name for name, _ in row.distances) != names for row in samples):
            raise ValueError('Sample distance coverage changed within the request')
        if not isinstance(self.report_json, str):
            raise TypeError('Separation report requires immutable JSON text')
        report = json.loads(self.report_json, parse_constant=lambda text: (_ for _ in ()).throw(
            ValueError('Nonfinite separation report')))
        json.dumps(report, allow_nan=False)
        if not isinstance(report, dict) or not isinstance(report.get('plan_reports'), list):
            raise ValueError('Separation report requires the original planning records')
        records = report['plan_reports']
        if (len(records) < 2 or not all(isinstance(item, dict) for item in records) or
                records[-2].get('stage') != 'release_return_budget' or
                records[-1].get('stage') != 'release_return' or
                not isinstance(report.get('release_record'), dict)):
            raise ValueError('Separation report is missing its original terminal records')
        initial_distances = _named(report['release_record'].get('initial_distances_m', ()),
                                   'initial distances', _scalar)
        if tuple(name for name, _ in initial_distances) != names:
            raise ValueError('Samples do not cover every original initial-distance geometry')
        for record in (report['release_record'], records[-1]):
            reported_paths = tuple(tuple(_vector(q, 5, 'reported path waypoint') for q in record.get(key, ()))
                                   for key in ('separation_path', 'planned_return_path'))
            if (tuple(len(path) for path in reported_paths) != tuple(len(path) for path in paths) or
                    any(_bytes(a) != _bytes(b) for a, b in zip(reported_paths, paths))):
                raise ValueError('Reported separation or return path differs from the proposal')
        object.__setattr__(self, 'paths', paths)
        object.__setattr__(self, 'samples', samples)


class AsyncSeparationPlanningJob(AsyncTransportPlanningJob):
    """Reuse the existing lifecycle; only the immutable proposal type differs."""
    def __init__(self, binding):
        super().__init__(binding, plan_type=SeparationPlan)
        self.execution['mode'] = 'isolated_thread_physics_advancing_release'


def validate_separation_samples(plan, pinch, floors, vertices, high_z, *, expected_names):
    """Check every saved sample against the current original separation guard.

    The caller must first verify the request/model/release binding and validate
    new bridge samples. This function alone never admits a motion or command.
    """
    if not isinstance(plan, SeparationPlan):
        raise TypeError('A validated immutable separation proposal is required')
    expected_names = tuple(expected_names)
    if (not expected_names or any(not isinstance(name, str) or not name for name in expected_names) or
            len(set(expected_names)) != len(expected_names)):
        raise ValueError('Expected original geometry names must be complete and unique')
    if any(set(name for name, _ in row.distances) != set(expected_names) for row in plan.samples):
        raise ValueError('Saved samples do not cover current original geometry names')
    pinch = np.asarray(_vector(pinch, 3, 'live separation pinch'))
    floors = dict(_named(floors, 'live floors', _scalar))
    vertices = dict(_named(vertices, 'live pad vertices', _pad))
    high_z = dict(_named(high_z, 'live pad high Z', lambda v: _vector(v, 8, 'pad high Z')))
    if (set(vertices) != set(high_z) or not set(vertices) <= _pad_names() or
            not set(floors) <= set(vertices)):
        raise ValueError('Live separation exceptions require matching original pad baselines')
    if not set(floors) <= set(dict(plan.samples[0].distances)):
        raise ValueError('Live floors refer to an unknown original geometry')
    report = dict(valid=False, reason=None, sample_count=len(plan.samples),
                  checked_samples=0, invalid_sample_index=None)
    for index, row in enumerate(plan.samples):
        report['checked_samples'] += 1
        point = np.asarray(row.pinch3)
        if np.linalg.norm(point[:2]-pinch[:2]) > .0002 or point[2] < pinch[2]-.0002:
            reason = 'pinch_guard'
        elif not all(distance >= floors.get(name, .001) for name, distance in row.distances):
            reason = 'distance_floor'
        else:
            pads = dict(row.pad_vertices)
            reason = None
            for name, baseline in vertices.items():
                current = np.asarray(pads[name])
                if (np.max(np.abs(current[:, :2]-np.asarray(baseline)[:, :2])) > .0002 or
                        np.min(current[:, 2]-np.asarray(high_z[name])) < -.00005):
                    reason = 'pad_monotonic_guard'
                    break
        if reason is not None:
            report.update(reason=reason, invalid_sample_index=index)
            return report
    report.update(valid=True, reason='all_saved_samples_valid')
    return report


def _planning_context(rig, released_model, snapshot):
    """Construct fresh data/native over caller-owned model copies."""
    import mujoco
    from conservative_collision import ConservativeCollisionChecker
    from grasp_workcell import TARGET_SIZE
    from released_object import ReleasedObjectQuery
    from visual_grasp_controller import VisualGraspController

    if rig is released_model or rig.nq != 6 or rig.nv != 6 or released_model.nq != 6 or released_model.nv != 6:
        raise ValueError('Independent static six-joint planning models are required')
    context = VisualGraspController.__new__(VisualGraspController)
    context.rig, context.query = rig, mujoco.MjData(rig)
    context.gripper_id = rig.body('gripper').id
    context.initial_q = np.asarray(snapshot.initial_q6)
    context.last_command = np.asarray(snapshot.last_command6)
    context.seed, context.last_elapsed = snapshot.seed, snapshot.elapsed
    context.plan_reports, context.release_record, context.servo_transitions = [], {}, []
    query = ReleasedObjectQuery.__new__(ReleasedObjectQuery)
    query.model, query.data = released_model, mujoco.MjData(released_model)
    query.object_id = released_model.geom('estimated_released_box').id
    if (_bytes(released_model.geom_pos[query.object_id]) != _bytes(snapshot.center) or
            _bytes(released_model.geom_size[query.object_id]) !=
            _bytes(np.asarray(TARGET_SIZE)/2+snapshot.uncertainty)):
        raise ValueError('Released model differs from the frozen estimate')
    query.center, query.uncertainty_m = np.asarray(snapshot.center), snapshot.uncertainty
    query.robot_ids = [i for i in range(released_model.ngeom)
                       if released_model.geom_bodyid[i] != 0 and
                       (int(released_model.geom_contype[i]) & 2 or
                        int(released_model.geom_conaffinity[i]) & 2)]
    context.released_query = query
    context.checker = ConservativeCollisionChecker(rig, gripper=.5, margin_m=.001)
    return context


def run_separation_plan(rig, released_model, snapshot, cancel_event=None):
    """Run the original method once; collect geometry without extra queries.

    Both model arguments must be independent copies owned by this request.
    Cancellation is cooperative between callbacks, not a native-call abort.
    """
    from visual_grasp_controller import VisualGraspController
    if not isinstance(snapshot, SeparationSnapshot):
        raise TypeError('Separation worker requires its immutable snapshot')
    def check_cancel():
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError('separation_planning_cancelled')
    check_cancel()
    context = _planning_context(rig, released_model, snapshot)
    try:
        samples, cache = [], {}
        steps = dict(fk_calls=0, distance_calls=0, pad_vertex_calls=0, separation_callbacks=0)
        original_fk, original_distances = context._fk, context.released_query.distances
        original_pads = context.released_query.pad_vertices
        original_valid, original_released_valid = context._separation_valid, context._released_valid

        def recorded_fk(q6):
            result = original_fk(q6)
            steps['fk_calls'] += 1
            cache['fk_q6'], cache['pinch'] = _bytes(q6), np.array(result[2], copy=True)
            return result

        def recorded_distances(q6):
            result = original_distances(q6)
            steps['distance_calls'] += 1
            cache['distance_q6'], cache['distances'] = _bytes(q6), dict(result)
            return result

        def recorded_pads():
            result = original_pads()
            steps['pad_vertex_calls'] += 1
            cache['pad_q6'] = _bytes(context.released_query.data.qpos)
            cache['pads'] = {name: np.array(value, copy=True) for name, value in result.items()}
            return result

        def recorded_valid(q5, jaw=.5):
            check_cancel()
            steps['separation_callbacks'] += 1
            valid = original_valid(q5, jaw)
            check_cancel()
            if valid:
                expected = _bytes(np.r_[q5, jaw])
                if any(cache.get(name) != expected for name in ('fk_q6', 'distance_q6', 'pad_q6')):
                    raise RuntimeError('separation_sample_capture_pose_mismatch')
                samples.append(SeparationSample(q5, cache['pinch'], cache['distances'], cache['pads']))
            return valid

        def cooperative_released_valid(q5, jaw=.5):
            check_cancel()
            valid = original_released_valid(q5, jaw)
            check_cancel()
            return valid

        context._fk = recorded_fk
        context.released_query.distances = recorded_distances
        context.released_query.pad_vertices = recorded_pads
        context._separation_valid, context._released_valid = recorded_valid, cooperative_released_valid
        check_cancel()
        VisualGraspController._legacy_plan_separation(context, np.asarray(snapshot.q6), snapshot.elapsed)
        check_cancel()
        release = context.release_record
        paths = (release['separation_path'], release['planned_return_path'])
        report = dict(plan_reports=context.plan_reports, release_record=release,
                      worker_steps=steps,
                      separation_context=dict(pinch=context.separation_pinch.tolist(),
                                              floors=context.separation_floors,
                                              vertices={k: v.tolist() for k, v in context.separation_vertices.items()},
                                              high_z={k: v.tolist() for k, v in context.separation_high_z.items()}))
        return SeparationPlan(paths, json.dumps(report, allow_nan=False), samples, snapshot)
    finally:
        context.checker.native.close()
