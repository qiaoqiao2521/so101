"""Optional sequential sweep ABI; keep FK inside the original Python error scope."""
from __future__ import annotations

import ctypes as C
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from threading import RLock
import warnings

import mujoco
import numpy as np

import support_native as native

HERE = Path(__file__).resolve().parent
_LIB = None
_PREPARED = False
_LOAD_LOCK = RLock()
_META = {'available': False, 'calls': 0, 'checked_states': 0, 'native_calls': 0,
         'successful_frames': 0, 'fallbacks': 0}
_KINEMATICS = C.CFUNCTYPE(C.c_int, C.c_void_p)
_DOUBLE = C.POINTER(C.c_double)
_INT64 = C.POINTER(C.c_int64)


def runtime_metadata():
    """Process-wide diagnostic counts, never a geometry or success certificate."""
    return dict(_META)


def _get_bridge():
    global _PREPARED, _LIB
    with _LOAD_LOCK:
        if _PREPARED:
            return _LIB
        _PREPARED = True
        try:
            compiler = shutil.which('g++')
            if compiler is None:
                raise RuntimeError('g++ is unavailable')
            package = Path(mujoco.__file__).parent
            library = package/f'libmujoco.so.{mujoco.__version__}'
            if not library.is_file() or not (package/'include/mujoco/mujoco.h').is_file():
                raise RuntimeError('Matching MuJoCo header/library is unavailable')
            builds = HERE/'output/sweep-batch-build'
            builds.mkdir(parents=True, exist_ok=True)
            folder = Path(tempfile.mkdtemp(prefix='process-', dir=builds))
            output = folder/'libsweep_batch.so'
            argv = [compiler, *native._FLAGS, '-I'+str(package/'include'),
                    str(HERE/'sweep_batch.cpp'), str(library),
                    '-Wl,-rpath,'+str(package), '-o', str(output)]
            result = native._compile_process(argv)
            (folder/'compile.json').write_text(json.dumps({
                'argv': argv, 'returncode': result.returncode,
                'stdout': result.stdout, 'stderr': result.stderr}, indent=2)+'\n')
            if result.returncode:
                raise RuntimeError('Optional sweep bridge did not compile')
            lib = C.CDLL(str(output))
            lib.sb_mj_version.argtypes = []
            lib.sb_mj_version.restype = C.c_int
            if lib.sb_mj_version() != mujoco.mj_version():
                raise RuntimeError('Optional MuJoCo bridge ABI differs')
            lib.sb_run.argtypes = [C.c_void_p, C.c_void_p, _DOUBLE, C.c_int64,
                _INT64, C.c_int64, C.c_void_p, C.c_void_p, C.c_void_p, C.c_void_p,
                _INT64, C.c_int64, C.c_double, _DOUBLE, _DOUBLE, _DOUBLE,
                _INT64, _INT64, _INT64, _INT64, _INT64]
            lib.sb_run.restype = C.c_int
            _LIB = lib
            _META.update(available=True, library_path=str(output),
                         mujoco_version=mujoco.__version__,
                         source_path=str(HERE/'sweep_batch.cpp'))
        except (OSError, RuntimeError, AttributeError, ValueError, subprocess.SubprocessError) as error:
            _META['unavailable_reason'] = str(error)
            warnings.warn('Optional sweep batch unavailable; using original checks: '+str(error),
                          RuntimeWarning)
        return _LIB


def make_validator(checker):
    """Return None before any query when the original scalar path is required."""
    from conservative_collision import ConservativeCollisionChecker
    if (type(checker) is not ConservativeCollisionChecker
            or 'evaluate' in vars(checker)):
        return None
    evaluate = getattr(checker.evaluate, '__func__', None)
    code = getattr(evaluate, '__code__', None)
    if code is None or Path(code.co_filename).resolve() != HERE/'conservative_collision.py':
        return None
    model, data = checker.model, checker.data
    if (model.nq, model.nv, model.njnt) != (6, 6, 6):
        return None
    if not isinstance(getattr(model, '_address', None), int) \
            or not isinstance(getattr(data, '_address', None), int):
        return None
    lib = _get_bridge()
    if lib is None:
        return None
    bound = checker._native_query
    owner = bound._owner
    ids = np.array(checker.geometry_ids, dtype=np.int64, order='C', copy=True)
    if len(ids) != owner.geometry_count or not len(bound._pairs):
        return None
    ids.setflags(write=False)

    def validate(states):
        # Observers and custom predicates retain their original Python calls.
        fn = owner._lib.ns_evaluate_hinted
        if (checker.model is not model or checker.data is not data
                or 'evaluate' in vars(checker)
                or getattr(checker.evaluate, '__func__', None) is not evaluate
                or checker.geometry_ids.shape != ids.shape
                or not np.array_equal(checker.geometry_ids, ids)
                or not isinstance(fn, C._CFuncPtr)):
            _META['fallbacks'] += 1
            return None
        q = np.ascontiguousarray(states, dtype=np.float64)
        if q.ndim != 2 or q.shape[1] != 6 or not len(q):
            _META['fallbacks'] += 1
            return None
        errors = []
        handle = owner._handle

        @_KINEMATICS
        def protected_fk(context):
            try:
                mujoco.mj_kinematics(model, data)
                if owner._handle != handle:
                    raise RuntimeError('NativeSupport is closed')
                return 0
            except BaseException as error:
                errors.append(error)
                return 1

        with owner._lock:
            if not owner._handle or bound._summary_busy:
                _META['fallbacks'] += 1
                return None
            committed = np.array(owner._witness_hints, dtype=np.int64, order='C', copy=True)
            info = np.full(5, -1, dtype=np.int64)
            bound._summary_busy = True
            try:
                status = lib.sb_run(model._address, data._address,
                    q.ctypes.data_as(_DOUBLE), len(q), ids.ctypes.data_as(_INT64), len(ids),
                    handle, C.cast(fn, C.c_void_p), C.cast(protected_fk, C.c_void_p), None,
                    bound._summary_pairs_pointer, len(bound._pairs), checker.margin_m,
                    bound._summary_positions_pointer, bound._summary_rotations_pointer,
                    bound._summary_numeric_pointer, bound._summary_flags_pointer,
                    bound._summary_hint_in_pointer, bound._summary_hint_out_pointer,
                    committed.ctypes.data_as(_INT64), info.ctypes.data_as(_INT64))
                if status:
                    _META['fallbacks'] += 1
                    return None  # C preconditions reject before any state mutation.
                if info[3] > 0 and owner._handle:
                    committed.setflags(write=False)
                    owner._witness_hints = committed
            finally:
                bound._summary_busy = False
        _META['calls'] += 1
        _META['checked_states'] += int(info[0])
        _META['native_calls'] += int(info[2])
        _META['successful_frames'] += int(info[3])
        if errors and not isinstance(errors[0], (RuntimeError, ValueError)):
            raise errors[0]
        return int(info[0]), int(info[1])

    return validate
