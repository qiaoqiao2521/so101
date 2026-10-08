"""One transport job with owned numeric inputs and synchronous result admission.

Waiting here does not advance simulation. This is not a real-time executor or
a safe-hold controller. A running thread cannot be forcibly cancelled.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json
import math
import threading
import time

import numpy as np


def _vector(value, size, name):
    array = np.asarray(value, dtype=float)
    if array.shape != (size,) or not np.isfinite(array).all():
        raise ValueError(f'{name} requires {size} finite values')
    return tuple(float(x) for x in array)


def _rotation(value):
    array = np.asarray(value, dtype=float)
    if array.shape != (3, 3) or not np.isfinite(array).all():
        raise ValueError('Rotation requires a finite 3x3 matrix')
    return tuple(tuple(float(x) for x in row) for row in array)


@dataclass(frozen=True)
class TransportSnapshot:
    q6: tuple
    target_xy: tuple
    payload_relative: tuple
    payload_rotation: tuple
    world: tuple
    payload_uncertainty: float
    elapsed_s: float

    def __post_init__(self):
        for name, size in (('q6', 6), ('target_xy', 2), ('payload_relative', 3)):
            object.__setattr__(self, name, _vector(getattr(self, name), size, name))
        object.__setattr__(self, 'payload_rotation', _rotation(self.payload_rotation))
        world = []
        for name, kind, center, rotation, size in self.world:
            if not isinstance(name, str) or isinstance(kind, bool) or int(kind) != kind:
                raise ValueError('Static world requires a name and integer geometry kind')
            world.append((name, int(kind), _vector(center, 3, 'center'),
                          _rotation(rotation), _vector(size, 3, 'size')))
        object.__setattr__(self, 'world', tuple(world))
        for name in ('payload_uncertainty', 'elapsed_s'):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < 0:
                raise ValueError(f'{name} requires a finite nonnegative value')
            object.__setattr__(self, name, value)


@dataclass(frozen=True)
class TransportPlan:
    paths: tuple
    report_json: str

    def __post_init__(self):
        paths = []
        for path in self.paths:
            rows = tuple(_vector(row, 5, 'transport waypoint') for row in path)
            if len(rows) < 2:
                raise ValueError('Transport leg requires at least two waypoints')
            paths.append(rows)
        if len(paths) != 5:
            raise ValueError('Transport requires the original five legs')
        object.__setattr__(self, 'paths', tuple(paths))
        if not isinstance(self.report_json, str):
            raise TypeError('Transport report requires immutable JSON text')
        report = json.loads(self.report_json, parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError('Nonfinite transport report')))
        json.dumps(report, allow_nan=False)  # Also reject overflowing numeric literals.
        if not isinstance(report, dict) or report.get('stage') != 'transport_execution_plan':
            raise ValueError('Transport report has an invalid stage')
        if len(report.get('legs', [])) != 5:
            raise ValueError('Transport report requires five legs')
        for path, leg in zip(paths, report['legs']):
            reported = tuple(_vector(row, 5, 'reported waypoint') for row in leg['path'])
            if np.asarray(reported).tobytes() != np.asarray(path).tobytes():
                raise ValueError('Transport report and paths differ')


class TransportPlanningJob:
    """Consume one proposal in its unchanged caller context, after worker join.

    The binding is retained only by the caller. It is never sent to the worker,
    and does not substitute for the controller's subsequent geometry guards.
    """
    def __init__(self, binding):
        self._binding = binding
        self._state = 'new'
        self._plan = None
        self.execution = {}

    @property
    def state(self):
        return self._state

    def run(self, worker, *args):
        if self._state != 'new':
            raise RuntimeError('Transport job has already started')
        self._state = 'running'
        started = time.perf_counter()
        self.execution = {'mode': 'isolated_thread_frozen_simulation_wait',
                          'main_thread_id': threading.get_ident(), 'joined': False}

        def execute():
            self.execution['worker_thread_id'] = threading.get_ident()
            return worker(*args)

        try:
            pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='so101-transport')
            try:
                self._plan = pool.submit(execute).result()
            finally:
                # Do not report a successful join if shutdown itself fails.
                pool.shutdown(wait=True)
                self.execution['joined'] = True
            if not isinstance(self._plan, TransportPlan):
                raise TypeError('Transport worker did not return a TransportPlan')
        except BaseException:
            self._plan = None
            self._state = 'failed'
            raise
        else:
            self._state = 'completed'
        finally:
            self.execution['wait_wall_s'] = time.perf_counter()-started

    def consume(self, binding):
        if self._state != 'completed':
            raise RuntimeError('Transport result is unavailable or already consumed')
        if not self._binding.matches(binding):
            self._plan = None
            self._state = 'failed'
            raise RuntimeError('Transport result ownership or context changed')
        plan = self._plan
        self._plan = None
        self._state = 'consumed'
        return plan
