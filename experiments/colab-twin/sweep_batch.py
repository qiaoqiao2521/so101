"""Optional sequential sweep ABI; keep FK inside the original Python error scope."""
from __future__ import annotations

import ctypes as C
import json
from pathlib import Path
import shutil
import struct
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
         'successful_frames': 0, 'fallbacks': 0, 'direction_sweeps': 0,
         'direction_hint_attempts': 0, 'direction_certificate_work': 0}
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
            direction_run = getattr(lib, 'sb_run_direction', None)
            if direction_run is not None:
                direction_run.argtypes = [*lib.sb_run.argtypes, _INT64]
                direction_run.restype = C.c_int
            _LIB = lib
            _META.update(available=True, library_path=str(output),
                         mujoco_version=mujoco.__version__,
                         source_path=str(HERE/'sweep_batch.cpp'))
        except (OSError, RuntimeError, AttributeError, ValueError, subprocess.SubprocessError) as error:
            _META['unavailable_reason'] = str(error)
            warnings.warn('Optional sweep batch unavailable; using original checks: '+str(error),
                          RuntimeWarning)
        return _LIB


def make_validator(checker, *, direction_hints=False, refinement_prefix=False):
    """Return None before any query when the original scalar path is required."""
    from conservative_collision import ConservativeCollisionChecker
    prefix = refinement_prefix is True
    if (type(checker) is not ConservativeCollisionChecker
            or 'evaluate' in vars(checker)
            or (getattr(checker, 'mesh_box_axis_refinement', False) is True
                and not prefix)
            or (prefix and (direction_hints is not False
                or getattr(checker, 'mesh_box_axis_refinement', False) is not True))):
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
    # Preserve an installed ABI observer. Only an untouched library symbol may
    # select the new strategy; re-check its identity at every invocation too.
    original_fn = owner._lib.ns_evaluate_hinted
    prefix_binding = None
    snapshot = None
    if prefix:
        # The opt-in path cannot bypass Python observers or a replaced native
        # ABI symbol. Freeze identities and values, not a cached certificate.
        method_names = ('evaluate', '_evaluate_original', '_evaluate_with_details',
                        '_refine_original')
        methods = tuple(getattr(getattr(checker, name), '__func__', None)
                        for name in method_names)
        if (any(name in vars(checker) for name in method_names)
                or any(getattr(method, '__code__', None) is None
                       or Path(method.__code__.co_filename).resolve()
                       != HERE/'conservative_collision.py' for method in methods)
                or checker.native is not owner
                or type(original_fn) is not getattr(owner._lib, '_FuncPtr', None)
                or getattr(original_fn, '__name__', None) != 'ns_evaluate_hinted'
                or not owner._handle
                or type(checker.margin_m) not in (float, int)
                or not hasattr(owner, '_query_generation')):
            return None
        bound_names = ('summary', 'summary_with_details', '_summary_frame_locked')
        bound_methods = tuple(getattr(native._BoundPairs, name) for name in bound_names)
        if any(name in vars(bound)
               or getattr(getattr(bound, name, None), '__func__', None) is not method
               for name, method in zip(bound_names, bound_methods)):
            return None
        pair_values = bound._pairs.copy()
        pair_object = bound._pairs
        id_object = checker.geometry_ids
        library = owner._lib
        handle_at_setup = owner._handle
        saved_margin = struct.pack('!d', float(checker.margin_m))
        scratch_names = tuple('_summary_'+name+'_pointer' for name in
            ('pairs', 'positions', 'rotations', 'numeric', 'flags', 'hint_in', 'hint_out'))
        scratch = tuple(getattr(bound, name) for name in scratch_names)

        def prefix_binding():
            return (checker.model is model and checker.data is data
                    and checker.native is owner and checker._native_query is bound
                    and bound._owner is owner and owner._lib is library
                    and owner._handle is not None and owner._handle == handle_at_setup
                    and library.ns_evaluate_hinted is original_fn
                    and checker.mesh_box_axis_refinement is True
                    and checker.geometry_ids is id_object
                    and np.array_equal(checker.geometry_ids, ids)
                    and bound._pairs is pair_object
                    and np.array_equal(bound._pairs, pair_values)
                    and type(checker.margin_m) in (float, int)
                    and struct.pack('!d', float(checker.margin_m)) == saved_margin
                    and all(name not in vars(checker)
                            and getattr(getattr(checker, name), '__func__', None) is method
                            for name, method in zip(method_names, methods))
                    and all(name not in vars(bound)
                            and getattr(getattr(bound, name, None), '__func__', None) is method
                            for name, method in zip(bound_names, bound_methods))
                    and all(getattr(bound, name) is value
                            for name, value in zip(scratch_names, scratch)))

        # Allocate once; copy/rollback stays inside each measured invocation.
        snapshot = mujoco.MjData(model)
    direction_fn = direction_run = None
    if direction_hints:
        proposed = getattr(owner._lib, 'ns_evaluate_direction_hinted', None)
        run = getattr(lib, 'sb_run_direction', None)
        symbol_type = getattr(owner._lib, '_FuncPtr', None)
        if (type(original_fn) is symbol_type
                and original_fn.__name__ == 'ns_evaluate_hinted'
                and type(proposed) is symbol_type
                and proposed.__name__ == 'ns_evaluate_direction_hinted'
                and run is not None):
            proposed.argtypes = [*original_fn.argtypes, _INT64, _INT64]
            proposed.restype = C.c_int
            direction_fn, direction_run = proposed, run
        else:
            warnings.warn('Optional sweep direction hints unavailable or observed; '
                          'using original batch checks', RuntimeWarning)

    def validate(states):
        validate.last_info = None
        validate.metadata['attempts'] += 1
        if prefix and not prefix_binding():
            _META['fallbacks'] += 1
            validate.metadata['binding_rejected'] += 1
            return None
        # Observers and custom predicates retain their original Python calls.
        if not prefix and getattr(checker, 'mesh_box_axis_refinement', False) is True:
            _META['fallbacks'] += 1
            return None  # Native SAT alone cannot run the optional scalar refiner.
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
        changed = []
        handle = owner._handle
        expected_generation = None
        expected_refinement = None

        def unchanged():
            return (prefix_binding() and owner._query_generation == expected_generation
                    and getattr(checker, '_refinement_generation', 0) == expected_refinement)

        @_KINEMATICS
        def protected_fk(context):
            nonlocal expected_generation, expected_refinement
            try:
                if prefix:
                    if not unchanged():
                        changed.append(True)
                        return 1
                    owner._query_generation += 1
                    checker._refinement_generation = getattr(checker, '_refinement_generation', 0) + 1
                    expected_generation = owner._query_generation
                    expected_refinement = checker._refinement_generation
                mujoco.mj_kinematics(model, data)
                if prefix and not unchanged():
                    changed.append(True)
                    return 1
                if owner._handle != handle:
                    raise RuntimeError('NativeSupport is closed')
                return 0
            except BaseException as error:
                if prefix and not unchanged():
                    changed.append(True)
                errors.append(error)
                return 1

        with owner._lock:
            if not owner._handle or bound._summary_busy or (prefix and not prefix_binding()):
                _META['fallbacks'] += 1
                return None
            if prefix:
                owner._query_generation += 1
                checker._refinement_generation = getattr(checker, '_refinement_generation', 0) + 1
                expected_generation = owner._query_generation
                expected_refinement = checker._refinement_generation
                mujoco.mj_copyData(snapshot, model, data)
                if not unchanged():
                    _META['fallbacks'] += 1
                    return None
                saved_hints = np.array(owner._witness_hints, dtype=np.int64, order='C', copy=True)
                saved_hints.setflags(write=False)
            committed = np.array(owner._witness_hints, dtype=np.int64, order='C', copy=True)
            info = np.full(5, -1, dtype=np.int64)
            work = np.zeros(2, dtype=np.int64)
            use_direction = (direction_fn is not None and fn is original_fn
                             and owner._lib.ns_evaluate_direction_hinted is direction_fn
                             and lib.sb_run_direction is direction_run)
            run = direction_run if use_direction else lib.sb_run
            query = direction_fn if use_direction else fn
            prefix_outcome = None
            bound._summary_busy = True
            try:
                status = run(model._address, data._address,
                    q.ctypes.data_as(_DOUBLE), len(q), ids.ctypes.data_as(_INT64), len(ids),
                    handle, C.cast(query, C.c_void_p), C.cast(protected_fk, C.c_void_p), None,
                    bound._summary_pairs_pointer, len(bound._pairs), checker.margin_m,
                    bound._summary_positions_pointer, bound._summary_rotations_pointer,
                    bound._summary_numeric_pointer, bound._summary_flags_pointer,
                    bound._summary_hint_in_pointer, bound._summary_hint_out_pointer,
                    committed.ctypes.data_as(_INT64), info.ctypes.data_as(_INT64),
                    *([work.ctypes.data_as(_INT64)] if use_direction else []))
                if status:
                    _META['fallbacks'] += 1
                    return None  # C preconditions reject before any state mutation.
                if info[3] > 0 and owner._handle and (not prefix or (not changed and unchanged())):
                    committed.setflags(write=False)
                    owner._witness_hints = committed
                if prefix:
                    if errors and isinstance(errors[0], (RuntimeError, ValueError)):
                        # Preserve the actual FK error even when its callback
                        # also changed binding/generation. Replaying would wash
                        # away a one-off failure; do not commit or roll back.
                        prefix_outcome = 'original_error_prefixes'
                    elif changed or not unchanged():
                        prefix_outcome = 'binding_rejected'
                    elif info[4] == 3:
                        # Roll back under the same owner lock. Generation is an
                        # invalidation token and deliberately remains advanced.
                        mujoco.mj_copyData(data, model, snapshot)
                        owner._witness_hints = saved_hints
                        prefix_outcome = 'restored'
                    elif info[4] in (1, 2, 4):
                        prefix_outcome = 'original_error_prefixes'
                    elif info[4] == 0 and info[0] == len(q) and info[1] == -1:
                        prefix_outcome = 'accepted'
            finally:
                bound._summary_busy = False
        _META['calls'] += 1
        _META['checked_states'] += int(info[0])
        _META['native_calls'] += int(info[2])
        _META['successful_frames'] += int(info[3])
        if use_direction:
            _META['direction_sweeps'] += 1
            _META['direction_hint_attempts'] += int(work[0])
            _META['direction_certificate_work'] += int(work[1])
        validate.last_info = tuple(int(value) for value in info)
        if errors and not isinstance(errors[0], (RuntimeError, ValueError)):
            raise errors[0]
        if prefix:
            if prefix_outcome is not None:
                validate.metadata[prefix_outcome] += 1
            if prefix_outcome not in ('accepted', 'original_error_prefixes'):
                _META['fallbacks'] += 1
                return None
        return int(info[0]), int(info[1])

    validate.last_info = None
    validate.metadata = {'refinement_prefix': prefix, 'attempts': 0, 'accepted': 0, 'restored': 0,
                         'binding_rejected': 0, 'original_error_prefixes': 0}
    return validate
