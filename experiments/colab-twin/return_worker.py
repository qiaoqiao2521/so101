"""Measured-pose return planning over the existing owned worker lifecycle."""
from dataclasses import dataclass
import json

import numpy as np

from separation_worker import SeparationSnapshot, _planning_context, _vector, _bytes
from transport_worker import AsyncTransportPlanningJob


@dataclass(frozen=True)
class ReturnPlan:
    path: tuple
    method: str
    report_json: str
    snapshot: SeparationSnapshot

    def __post_init__(self):
        if not isinstance(self.snapshot, SeparationSnapshot):
            raise TypeError('Return requires an owned release snapshot')
        path = tuple(_vector(q, 5, 'return waypoint') for q in self.path)
        if (len(path) < 2 or _bytes(path[0]) != _bytes(self.snapshot.q6[:5])
                or _bytes(path[-1]) != _bytes(self.snapshot.initial_q6[:5])):
            raise ValueError('Return endpoints differ from measured start or home')
        if self.method not in ('validated_direct', 'validated_ompl_shortcuts'):
            raise ValueError('Unknown original return method')
        report = json.loads(self.report_json)
        json.dumps(report, allow_nan=False)
        if not isinstance(report, list):
            raise ValueError('Return planning records must be a list')
        object.__setattr__(self, 'path', path)


class AsyncReturnPlanningJob(AsyncTransportPlanningJob):
    def __init__(self, binding):
        super().__init__(binding, plan_type=ReturnPlan)
        self.execution['mode'] = 'isolated_thread_physics_advancing_return_hold'


def run_return_plan(rig, released_model, snapshot, cancel_event=None):
    """Call the unchanged return algorithm, with private data and native state."""
    from visual_grasp_controller import VisualGraspController
    if not isinstance(snapshot, SeparationSnapshot):
        raise TypeError('Return worker requires an immutable release snapshot')

    def check_cancel():
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError('return_planning_cancelled')

    check_cancel()
    context = _planning_context(rig, released_model, snapshot)
    try:
        original_valid = context._released_valid

        def valid(q5, jaw=.5):
            check_cancel()
            result = original_valid(q5, jaw)
            check_cancel()
            return result

        context._released_valid = valid
        path, method = VisualGraspController._return_path(context, np.asarray(snapshot.q6[:5]))
        check_cancel()
        return ReturnPlan(path, method, json.dumps(context.plan_reports, allow_nan=False), snapshot)
    finally:
        context.checker.native.close()
