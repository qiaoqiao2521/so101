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


class AsyncTransportPlanningJob:
    """Own one cooperative worker; the caller alone admits or rejects results.

    ``start`` and ``poll`` never wait for planning. The caller must serialize
    lifecycle methods and call ``close`` inside its measured case cleanup.
    A running native call has no hard cancellation guarantee.
    """
    def __init__(self, binding):
        if not callable(getattr(binding, 'matches', None)):
            raise TypeError('Transport binding requires matches')
        self._binding = binding
        self._state = 'new'
        self._thread = None
        self._thread_started = False
        self._launch_attempted = False
        self._owned_ack = threading.Event()
        self._startup_error = None
        self._closed = False
        self._result = None
        self._worker_error = None
        self._plan = None
        self._error = None
        self._rejection = None
        self.cancel_event = threading.Event()
        self.execution = {'mode': 'isolated_thread_physics_advancing_hold',
                          'main_thread_id': threading.get_ident(),
                          'worker_thread_id': None, 'worker_wall_s': None,
                          'poll_count': 0, 'joined': False,
                          'abort_requested': False, 'shutdown_wall_s': 0.,
                          'launch_attempted': False, 'owned_ack': False,
                          'launch_unknown': False, 'cleanup_unconfirmed': False}

    @property
    def state(self):
        return self._state

    def start(self, worker, *args):
        if self._closed or self._state != 'new':
            raise RuntimeError('Transport job has already started or closed')
        if not callable(worker):
            self._state = 'failed'
            raise TypeError('Transport worker must be callable')
        self._state = 'running'

        def execute():
            started = time.perf_counter()
            self.execution['worker_thread_id'] = threading.get_ident()
            self.execution['owned_ack'] = True
            self._owned_ack.set()
            try:
                result = worker(*args)
                if not isinstance(result, TransportPlan):
                    raise TypeError('Transport worker did not return a TransportPlan')
                self._result = result
            except BaseException as error:
                self._worker_error = error
            finally:
                self.execution['worker_wall_s'] = time.perf_counter()-started

        try:
            self._thread = threading.Thread(target=execute, name='so101-transport-async',
                                            daemon=False)
            # start() may launch the OS thread and then be interrupted. Its
            # return flag does not establish whether owned work needs joining.
            self._launch_attempted = True
            self.execution['launch_attempted'] = True
            self._thread.start()
            self._thread_started = True
        except BaseException as error:
            self._startup_error = error
            self._error = error
            self._state = 'failed'
            self.cancel_event.set()
            self.execution['abort_requested'] = True
            self.execution['startup_error_type'] = type(error).__name__
            self.execution['startup_error'] = str(error)
            self.execution['cleanup_unconfirmed'] = self._launch_attempted
            self.execution['launch_unknown'] = self._launch_attempted and not self._owned_ack.is_set()
            raise

    def _join_failed(self, error):
        # Preserve the primary startup exception and the separate join cause.
        self._error = self._startup_error if self._startup_error is not None else error
        self._state = 'failed'
        self._plan = self._result = None
        self.execution.update(joined=False, cleanup_unconfirmed=True,
                              launch_unknown=not self._owned_ack.is_set(),
                              cleanup_error_type=type(error).__name__, cleanup_error=str(error))

    def _join_confirmed(self):
        self.execution.update(joined=True, cleanup_unconfirmed=False, launch_unknown=False)

    def _raise_unavailable(self):
        if self._error is not None:
            raise self._error
        raise RuntimeError(self._rejection or 'Transport result is unavailable or already consumed')

    def poll(self):
        self.execution['poll_count'] += 1
        if self._closed or self._state == 'new':
            self._raise_unavailable()
        if self._launch_attempted and self._thread.is_alive():
            return False
        if self._launch_attempted and not self.execution['joined']:
            try:
                self._thread.join(timeout=0)
                if self._thread.is_alive():
                    return False
            except BaseException as error:
                self._join_failed(error)
                raise
            self._join_confirmed()
        if self._state in ('rejected', 'failed', 'consumed'):
            self._result = None
            self._raise_unavailable()
        if self._worker_error is not None:
            self._error = self._worker_error
            self._state = 'failed'
            self._result = None
            raise self._error
        if self._state == 'running':
            if not isinstance(self._result, TransportPlan):
                self._error = RuntimeError('Transport worker exited without a plan')
                self._state = 'failed'
                raise self._error
            self._plan, self._result = self._result, None
            self._state = 'completed'
        return True

    def peek(self, binding):
        if self._closed or self._state != 'completed':
            self._raise_unavailable()
        try:
            matches = self._binding.matches(binding)
        except BaseException as error:
            self._error = error
            self._state = 'failed'
            self._plan = self._result = None
            self.cancel_event.set()
            self.execution['abort_requested'] = True
            raise
        if not matches:
            self.reject('Transport result ownership or context changed')
            self._raise_unavailable()
        return self._plan

    def consume(self, binding):
        plan = self.peek(binding)
        self._plan = None
        self._state = 'consumed'
        return plan

    def reject(self, reason):
        self.cancel_event.set()
        self.execution['abort_requested'] = True
        self._plan = self._result = None
        if self._state not in ('failed', 'consumed', 'rejected'):
            self._rejection = str(reason)
            self._state = 'rejected'

    def close(self):
        if self._closed and (self.execution['joined'] or not self._launch_attempted):
            return
        started = time.perf_counter()
        self.execution.setdefault('state_before_close', self._state)
        try:
            if self._launch_attempted and self._thread.is_alive():
                self.reject('Transport job closed before result admission')
            elif self._state in ('new', 'running', 'completed'):
                self.reject('Transport job closed before result admission')
            if self._launch_attempted and not self.execution['joined']:
                self._thread.join()
                if self._thread.is_alive():
                    raise RuntimeError('Transport worker did not exit during close')
                self._join_confirmed()
        except BaseException as error:
            self._join_failed(error)
            raise
        finally:
            self._plan = self._result = None
            self._closed = True
            self.execution['shutdown_wall_s'] += time.perf_counter()-started
