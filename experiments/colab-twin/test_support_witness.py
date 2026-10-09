"""Portable witness-ID regressions; no physical model, FK, step or renderer.

Compare the current hinted ABI with the real stateless ``ns_evaluate`` entry
of the same compiled current library. This is an isolated no-hint ABI
reference, not a historical-kernel equivalence claim. Test-only full-support
hooks expose discarded hints and overflow fallback. Trap probes use children.
"""
from __future__ import annotations

import ctypes as C
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import platform
import subprocess
import sys
from types import SimpleNamespace
import unittest

import numpy as np


HERE = Path(__file__).resolve().parent
KERNEL = HERE / 'support_kernel.cpp'
AUDIT = HERE / 'output' / 'support-witness-tests'
DOUBLE = C.POINTER(C.c_double)
INT64 = C.POINTER(C.c_int64)
FIELDS = ('certified', 'support_mode', 'direction_index', 'evaluations', 'reason',
          'orientation', 'n', 'projection_a', 'projection_b', 'gap_lower',
          'norm_squared_upper', 'squared_gap_lower', 'squared_threshold_upper',
          'lower_bound_m')
BUILD = {}
RECORDS = []


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def module_at(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def configure_hooks(lib):
    lib.ns_test_full_vertices.argtypes = [C.c_int64, DOUBLE, DOUBLE, C.c_int, DOUBLE, INT64]
    lib.ns_test_full_vertices.restype = C.c_int
    lib.ns_test_full_vertices_hinted.argtypes = [C.c_int64, DOUBLE, DOUBLE, INT64, DOUBLE, INT64, INT64]
    lib.ns_test_full_vertices_hinted.restype = C.c_int
    lib.ns_test_witness_get_mxcsr.argtypes = []
    lib.ns_test_witness_get_mxcsr.restype = C.c_uint32
    lib.ns_test_witness_set_mxcsr.argtypes = [C.c_uint32]
    lib.ns_test_witness_set_mxcsr.restype = None
    lib.ns_test_witness_traps_masked.argtypes = []
    lib.ns_test_witness_traps_masked.restype = C.c_int


def stateless_adapter(candidate):
    """Use the real C legacy ABI; inherit geometry ownership and result decode.

    This thin test adapter only prepares owned input/output buffers. It does
    not implement support arithmetic, certificates, tree traversal or hints.
    """
    class StatelessNativeSupport(candidate.NativeSupport):
        def _frame_locked(self, positions, rotations, pairs, margin, *, bound=False):
            if not self._handle:
                raise RuntimeError("NativeSupport is closed")
            p = np.array(positions, dtype=np.float64, order="C", copy=True)
            R = np.array(rotations, dtype=np.float64, order="C", copy=True)
            q = pairs if bound else self._copy_pairs(pairs)
            if p.shape != (self.geometry_count, 3) or R.shape != (self.geometry_count, 3, 3):
                raise ValueError("Frame position/rotation shapes do not match original geometry")
            if q.ndim != 2 or q.shape[1] != 2:
                raise ValueError("Pairs must have shape Mx2")
            numeric = np.empty((len(q), 12), dtype=np.float64)
            flags = np.empty((len(q), 6), dtype=np.int64)
            status = self._lib.ns_evaluate(
                self._handle, p.ctypes.data_as(DOUBLE), R.ctypes.data_as(DOUBLE),
                q.ctypes.data_as(INT64), len(q), float(margin),
                numeric.ctypes.data_as(DOUBLE), flags.ctypes.data_as(INT64))
            if status:
                raise RuntimeError("Native frame evaluation failed closed")
            return numeric, flags
    return SimpleNamespace(NativeSupport=StatelessNativeSupport)


def load_libraries(candidate_path):
    candidate = module_at('witness_candidate_loader', HERE / 'support_native.py')
    lib = C.CDLL(str(candidate_path))
    candidate._configure_library(lib)
    configure_hooks(lib)
    candidate._LIB = lib
    return candidate, stateless_adapter(candidate), lib


def compile_test_library():
    loader = module_at('witness_build_loader', HERE / 'support_native.py')
    identity = loader._compiler_identity()
    source_hash = sha(KERNEL)
    directory = AUDIT / 'witness-build' / source_hash
    directory.mkdir(parents=True, exist_ok=True)
    library = directory / 'libsupport_witness_tests.so'
    flags = [*loader._FLAGS, '-DSUPPORT_TREE_TESTS']
    command = [identity['path'], *flags, str(KERNEL), '-o', str(library)]
    process = loader._compile_process(command)
    BUILD.update(kernel_path=str(KERNEL), kernel_sha256=source_hash,
                 wrapper_sha256=sha(HERE / 'support_native.py'), compiler=identity,
                 flags=flags, command=command, compile_returncode=process.returncode,
                 compile_stdout=process.stdout, compile_stderr=process.stderr,
                 compile_timeout_s=loader._COMPILE_TIMEOUT_S)
    if process.returncode or not library.is_file():
        raise RuntimeError('Strict witness test build failed')
    if sha(KERNEL) != source_hash or sha(identity['path']) != identity['binary_sha256']:
        raise RuntimeError('Source or compiler drift during test build')
    BUILD.update(library_path=str(library), library_sha256=sha(library),
                 comparison='same_current_library_stateless_ns_evaluate',
                 reference_library_sha256=sha(library),
                 test_sha256=sha(Path(__file__)))
    return library


def fixture():
    # A diagonal mesh has a broad rotated local AABB but a narrow true world-x
    # span. A small box in that empty AABB region forces a full world-axis query.
    t = np.repeat(np.linspace(-.1, .1, 17), 2)
    mesh = np.column_stack((t, t, np.tile([-.002, .002], 17)))
    corners = np.asarray(list(itertools.product((-1., 1.), repeat=3))) * .001
    p = np.asarray([[0., 0., 0.], [.02, .001, 0.]])
    R = np.tile(np.eye(3), (2, 1, 1))
    c = np.sqrt(.5)
    R[0] = [[c, -c, 0.], [c, c, 0.], [0., 0., 1.]]
    pairs = np.asarray([[0, 1]], dtype=np.int64)
    return [mesh, corners], ['mesh', 'box'], p, R, pairs


def primitive(lib, points, coefficients, hints):
    points = np.array(points, dtype=np.float64, order='C', copy=True)
    coefficients = np.array(coefficients, dtype=np.float64, order='C', copy=True)
    hints = np.array(hints, dtype=np.int64, order='C', copy=True)
    output = np.full(2, np.nan)
    winners = np.full(2, -1, dtype=np.int64)
    info = np.zeros(6, dtype=np.int64)
    status = lib.ns_test_full_vertices_hinted(
        len(points), points.ctypes.data_as(DOUBLE), coefficients.ctypes.data_as(DOUBLE),
        hints.ctypes.data_as(INT64), output.ctypes.data_as(DOUBLE),
        winners.ctypes.data_as(INT64), info.ctypes.data_as(INT64))
    return status, output, winners, info


def legacy_full(lib, points, coefficients, *, tree=0):
    points = np.array(points, dtype=np.float64, order='C', copy=True)
    coefficients = np.array(coefficients, dtype=np.float64, order='C', copy=True)
    output = np.full(2, np.nan)
    info = np.zeros(4, dtype=np.int64)
    status = lib.ns_test_full_vertices(
        len(points), points.ctypes.data_as(DOUBLE), coefficients.ctypes.data_as(DOUBLE),
        tree, output.ctypes.data_as(DOUBLE), info.ctypes.data_as(INT64))
    return status, output, info


def raw_frame(native, p, R, pairs, margin, *, hinted=False, hints=None):
    p, R = (np.array(x, dtype=np.float64, order='C', copy=True) for x in (p, R))
    pairs = np.array(pairs, dtype=np.int64, order='C', copy=True)
    numeric = np.full((len(pairs), 12), np.nan)
    flags = np.full((len(pairs), 6), -1, dtype=np.int64)
    args = (native._handle, p.ctypes.data_as(DOUBLE), R.ctypes.data_as(DOUBLE),
            pairs.ctypes.data_as(INT64), len(pairs), margin,
            numeric.ctypes.data_as(DOUBLE), flags.ctypes.data_as(INT64))
    if not hinted:
        return native._lib.ns_evaluate(*args), numeric, flags
    hin = np.array(hints, dtype=np.int64, order='C', copy=True)
    hout = np.full_like(hin, -99)
    original_bytes = hin.tobytes()
    status = native._lib.ns_evaluate_hinted(
        *args, hin.ctypes.data_as(INT64), hout.ctypes.data_as(INT64))
    if hin.tobytes() != original_bytes:
        raise AssertionError('Hint input was mutated')
    return status, numeric, flags, hout


class SupportWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library_path = compile_test_library()
        cls.candidate, cls.stateless, cls.lib = load_libraries(cls.library_path)

    @classmethod
    def tearDownClass(cls):
        if sha(KERNEL) != BUILD['kernel_sha256'] or sha(HERE / 'support_native.py') != BUILD['wrapper_sha256']:
            raise AssertionError('Candidate drift during tests')
        AUDIT.mkdir(exist_ok=True)
        (AUDIT / 'witness-test-evidence.json').write_text(
            json.dumps({'build': BUILD, 'observations': RECORDS,
                        'physics': 0, 'FK': 0, 'render': 0}, indent=2) + '\n')

    def geometry(self):
        points, kinds, p, R, pairs = fixture()
        candidate = self.candidate.NativeSupport(points, kinds)
        stateless = self.stateless.NativeSupport(points, kinds)
        self.addCleanup(candidate.close)
        self.addCleanup(stateless.close)
        return candidate, stateless, points, p, R, pairs

    def assert_fields(self, a, b):
        self.assertEqual(set(a), set(FIELDS))
        self.assertEqual(set(b), set(FIELDS))
        for field in FIELDS:
            with self.subTest(field=field):
                self.assertEqual(a[field].dtype, b[field].dtype)
                self.assertEqual(a[field].shape, b[field].shape)
                self.assertEqual(a[field].tobytes(), b[field].tobytes())

    def compare_primitive(self, label, points, coefficients, hints, *, expected=0):
        scan = legacy_full(self.lib, points, coefficients)
        tree = legacy_full(self.lib, points, coefficients, tree=1)
        hot = primitive(self.lib, points, coefficients, hints)
        for result in (tree, hot):
            self.assertEqual(result[0], scan[0], label)
            self.assertEqual(result[1].tobytes(), scan[1].tobytes(), label)
        self.assertEqual(hot[0], expected)
        RECORDS.append({'label': label, 'status': hot[0],
                        'endpoints_uint64': hot[1].view(np.uint64).tolist(),
                        'winners': hot[2].tolist(), 'info': hot[3].tolist()})
        return hot

    def test_public_stateless_all14_cold_hot_rotation_translation_margin_history(self):
        candidate, stateless, _, p, R, pairs = self.geometry()
        self.assertEqual(candidate._witness_hints.shape, (2, 3, 2))
        self.assertEqual(candidate._witness_hints.dtype, np.dtype(np.int64))
        self.assertTrue((candidate._witness_hints == -1).all())
        first = candidate.evaluate(p, R, pairs, .001)
        self.assert_fields(first, stateless.evaluate(p, R, pairs, .001))
        self.assertTrue(first['certified'].all())
        self.assertEqual(first['support_mode'][0], 'full')
        self.assertEqual(first['direction_index'][0], 0)
        self.assertTrue((candidate._witness_hints[0, 0] >= 0).all())
        self.assertTrue((candidate._witness_hints[1] == -1).all())
        snapshot = {k: v.tobytes() for k, v in first.items()}
        for shift, margin, changed in ((0., .001, False), (.002, .002, False),
                                       (-.001, .001, True), (0., .001, False)):
            q, rotation = p.copy(), R.copy()
            q[1, 0] += shift
            if changed:
                rotation[0, 0, 0] = np.nextafter(rotation[0, 0, 0], np.inf)
            self.assert_fields(candidate.evaluate(q, rotation, pairs, margin),
                               stateless.evaluate(q, rotation, pairs, margin))
        self.assertEqual({k: v.tobytes() for k, v in first.items()}, snapshot)

    def test_same_library_legacy_stateless_reversed_duplicate_pairs_and_bad_ids(self):
        candidate, _, _, p, R, _ = self.geometry()
        pairs = np.asarray([[0, 1], [1, 0], [0, 1]], dtype=np.int64)
        R[0, 2, 0], R[0, 2, 1] = -0., 0.
        hints = np.full((2, 3, 2), -1, dtype=np.int64)
        hints[0] = [[33, 32], [-2, 2**63-1], [9, 9]]
        for margin in (.001, .002):
            a = raw_frame(candidate, p, R, pairs, margin)
            b = raw_frame(candidate, p, R, pairs, margin, hinted=True, hints=hints)
            self.assertEqual(a[0], b[0])
            self.assertEqual(a[1].tobytes(), b[1].tobytes())
            self.assertEqual(a[2].tobytes(), b[2].tobytes())
        self.assertTrue((candidate._witness_hints == -1).all())

    def test_tree_split_sizes_interval_directions_and_id_reuse(self):
        rng = np.random.default_rng(20261009)
        for count in (15, 16, 17, 33, 65):
            points = rng.uniform(-2., 2., (count, 3))
            hint = [count-1, count//2]
            for n in ([1., -.7, .1], [-.2, .8, -1.]):
                coefficient = np.column_stack((np.nextafter(n, -np.inf), np.nextafter(n, np.inf)))
                row = self.compare_primitive(f'split-{count}-{n}', points, coefficient, hint)
                self.assertEqual(row[3][0], 1)
                hint = row[2]

    def test_original_index_ties_signed_zero_and_duplicate_hint(self):
        points = np.tile([[0., -0., 0.], [-0., 0., -0.], [1., -1., 0.],
                          [-1., 1., 0.], [1., -1., -0.], [-1., 1., -0.]], (6, 1))
        coefficient = np.asarray([[1., 1.], [1., 1.], [-0., 0.]])
        result = self.compare_primitive('ties', points, coefficient, [35, 35])
        rows = [legacy_full(self.lib, [p], coefficient)[1] for p in points]
        minimum = min(range(len(rows)), key=lambda i: (rows[i][0], i))
        maximum = min(range(len(rows)), key=lambda i: (-rows[i][1], i))
        self.assertEqual(result[2].tolist(), [minimum, maximum])
        self.assertEqual(result[3][1], 1)  # Duplicate ID is never reevaluated twice.

    def test_one_sided_hint_and_changed_current_coefficients_do_not_certify_old_extrema(self):
        points = np.column_stack((np.linspace(-3., 3., 33), np.arange(33)%5,
                                  np.arange(33)%3))
        for coefficients in ([[1., 1.], [.01, .01], [.1, .1]],
                             [[-1., -1.], [.9, .9], [-.2, -.2]]):
            row = self.compare_primitive('one-sided', points, coefficients, [16, -1])
            self.assertEqual(row[3][1], 1)
            self.assertTrue((row[2] >= 0).all())

    def test_invalid_ids_and_vertex_zero_are_harmless_work_hints(self):
        points = np.arange(99, dtype=float).reshape(33, 3)/100
        for ids in ([-1, -2], [33, 2**63-1], [0, 0]):
            row = self.compare_primitive(f'invalid-{ids}', points,
                                         [[1., 1.], [-.5, -.5], [0., 0.]], ids)
            self.assertEqual(row[3][1], 0)
            self.assertEqual(row[3][3], 0)

    def test_tighter_hint_cannot_hide_node_overflow_full_scan_fallback(self):
        large = np.finfo(float).max*.75
        points = np.asarray([[large if i%2 else -large]*2+[0.] for i in range(33)])
        row = self.compare_primitive('node-overflow', points,
                                     [[1., 1.], [-1., -1.], [0., 0.]], [31, 32])
        self.assertGreater(row[3][4], 0)
        self.assertEqual(row[3][5], 1)
        self.assertEqual(row[2].tolist(), [-1, -1])  # No guessed scan witness.

    def test_speculative_nonfinite_hint_discards_then_preserves_true_leaf_failure(self):
        points = np.zeros((33, 3))
        points[0, 0], points[32, 0] = 1., np.finfo(float).max
        row = self.compare_primitive('leaf-overflow', points,
                                     [[2., 2.], [0., 0.], [0., 0.]], [32, 31], expected=1)
        self.assertEqual(row[3][3], 1)
        self.assertEqual(row[3][4], 0)
        self.assertEqual(row[2].tolist(), [-1, -1])

    def test_failed_frame_does_not_publish_ids_and_valid_frame_recovers(self):
        candidate, stateless, _, p, R, pairs = self.geometry()
        candidate.evaluate(p, R, pairs, .001)
        history = candidate._witness_hints
        for margin, nonfinite, overlapping in ((float('nan'), False, False),
                                               (.001, True, False), (.001, False, True)):
            frame = p.copy()
            if nonfinite:
                frame[0, 0] = np.nan
            if overlapping:
                frame[1, 0] = 0.
            a = candidate.evaluate(frame, R, pairs, margin)
            b = stateless.evaluate(frame, R, pairs, margin)
            self.assert_fields(a, b)
            self.assertFalse(a['certified'].all())
            self.assertIs(candidate._witness_hints, history)
        self.assert_fields(candidate.evaluate(p, R, pairs, .002),
                           stateless.evaluate(p, R, pairs, .002))

    def test_empty_pairs_do_not_publish_history_even_on_invalid_frame(self):
        candidate, stateless, _, p, R, pairs = self.geometry()
        candidate.evaluate(p, R, pairs, .001)
        history = candidate._witness_hints
        empty = np.empty((0, 2), dtype=np.int64)
        for margin, nonfinite in ((.001, False), (float('nan'), False), (.001, True)):
            frame = p.copy()
            if nonfinite:
                frame[0, 0] = np.nan
            self.assert_fields(candidate.evaluate(frame, R, empty, margin),
                               stateless.evaluate(frame, R, empty, margin))
            self.assertIs(candidate._witness_hints, history)

    def test_one_mm_boundary_uses_original_conservative_gate(self):
        candidate, stateless, _, p, R, pairs = self.geometry()
        for delta in (-1e-9, 0., 1e-9):
            frame = p.copy()
            frame[1, 0] = .002 + delta  # Box half extent .001, mesh world-x ~0.
            a = candidate.evaluate(frame, R, pairs, .001)
            self.assert_fields(a, stateless.evaluate(frame, R, pairs, .001))
            if delta < 0:
                self.assertFalse(a['certified'][0])
            if delta > 0:
                self.assertTrue(a['certified'][0])

    def test_owned_history_points_outputs_bound_pairs_and_close(self):
        points, kinds, p, R, pairs = fixture()
        a = self.candidate.NativeSupport(points, kinds)
        b = self.candidate.NativeSupport(points, kinds)
        self.addCleanup(a.close)
        self.addCleanup(b.close)
        self.assertFalse(np.shares_memory(a._witness_hints, b._witness_hints))
        bound = a.bind_pairs(pairs)
        first = bound.evaluate(p, R, .001)
        saved = {k: v.tobytes() for k, v in first.items()}
        history = a._witness_hints
        self.assertFalse(history.flags.writeable)
        points[0][:] = 1000.
        pairs[:] = 0
        self.assert_fields(first, bound.evaluate(p, R, .001))
        self.assertTrue((b._witness_hints == -1).all())
        self.assertEqual({k: v.tobytes() for k, v in first.items()}, saved)
        a.close()
        self.assertIsNone(a._witness_hints)
        with self.assertRaisesRegex(RuntimeError, 'closed'):
            bound.summary(p, R, .001)
        with self.assertRaisesRegex(RuntimeError, 'closed'):
            a.evaluate(p, R, np.asarray([[0, 1]], dtype=np.int64), .001)

    def test_actual_sampler_first_failure_prefix_and_reports_match_stateless(self):
        sampler = module_at('witness_sampler', HERE / 'configuration_sweep.py')
        candidate, stateless, _, p, R, _ = self.geometry()
        pairs = np.asarray([[0, 1], [1, 0], [0, 1]], dtype=np.int64)
        traces, reports = [], []
        for native in (stateless, candidate):
            trace = []
            def valid(q):
                frame = p.copy()
                frame[1, 0] = float(q[0])*.01
                detailed = native.evaluate(frame, R, pairs, .001)
                trace.append((np.asarray(q, dtype=np.float64).tobytes(),
                              tuple((name, detailed[name].dtype.str, detailed[name].shape,
                                     detailed[name].tobytes()) for name in FIELDS)))
                return bool(detailed['certified'].all())
            reports.append(sampler.validate_configuration_path(
                [.5, 0., 0., 0., 0., .5], [0., 0., 0., 0., 0., .015], valid))
            traces.append(trace)
        self.assertEqual(reports[0], reports[1])
        self.assertEqual(traces[0], traces[1])
        self.assertFalse(reports[0]['valid'])
        self.assertEqual(reports[0]['checked_states'], len(traces[0]))
        self.assertEqual(reports[0]['invalid_sample_index']+1, len(traces[0]))
        self.assertLess(len(traces[0]), reports[0]['required_states'])

    def test_unmasked_x87_and_sse_traps_skip_hints_in_isolated_children(self):
        if platform.machine().lower() not in ('x86_64', 'amd64'):
            self.skipTest('MXCSR trap-mask split is an x86-64 test')
        for mode in ('x87', 'sse', 'rounding_and_denormals'):
            with self.subTest(mode=mode):
                command = [sys.executable, '-B', str(Path(__file__).resolve()),
                           '--trap-child', str(self.library_path), mode]
                process = subprocess.run(command, text=True, capture_output=True, timeout=15)
                RECORDS.append({'trap_child': mode, 'command': command,
                                'exit_code': process.returncode,
                                'stdout': process.stdout, 'stderr': process.stderr})
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertTrue(json.loads(process.stdout)['passed'])


def trap_child(library_path, mode):
    candidate, stateless, lib = load_libraries(Path(library_path))
    libc = C.CDLL(None)
    for name in ('fegetexcept', 'feenableexcept', 'fedisableexcept', 'fegetround', 'fesetround'):
        if not hasattr(libc, name):
            raise RuntimeError('Frozen Linux trap-control probe is unavailable')
        getattr(libc, name).restype = C.c_int
    libc.fegetexcept.argtypes = libc.fegetround.argtypes = []
    for name in ('feenableexcept', 'fedisableexcept', 'fesetround'):
        getattr(libc, name).argtypes = [C.c_int]
    saved_csr = lib.ns_test_witness_get_mxcsr()
    saved_round, saved_traps = libc.fegetround(), libc.fegetexcept()
    points, kinds, p, R, pairs = fixture()
    a, b = candidate.NativeSupport(points, kinds), stateless.NativeSupport(points, kinds)
    a.evaluate(p, R, pairs, .001)
    history = a._witness_hints
    observations = []
    try:
        if mode in ('x87', 'sse'):
            if saved_traps or (saved_csr & 0x1f80) != 0x1f80:
                raise AssertionError('Probe requires initially masked traps')
            if mode == 'x87':
                libc.feenableexcept(4)  # Divide-by-zero only; fixture has no such operation.
                lib.ns_test_witness_set_mxcsr(saved_csr)
                if libc.fegetexcept() & 4 != 4:
                    raise AssertionError('x87 trap control was not set')
            else:
                lib.ns_test_witness_set_mxcsr(saved_csr & ~0x200)
                if libc.fegetexcept() != saved_traps:
                    raise AssertionError('SSE-only test changed x87 control')
            csr_control = lib.ns_test_witness_get_mxcsr() & ~0x3f
            if lib.ns_test_witness_traps_masked():
                raise AssertionError('Unmasked trap incorrectly permits speculative hints')
            hot = primitive(lib, points[0], [[1., 1.], [0., 0.], [0., 0.]], [33, 32])
            cold = legacy_full(lib, points[0], [[1., 1.], [0., 0.], [0., 0.]], tree=1)
            if hot[0] != cold[0] or hot[1].tobytes() != cold[1].tobytes():
                raise AssertionError('Unmasked stateless arithmetic changed')
            if hot[3][0] or hot[3][1] or hot[3][4]:
                raise AssertionError('Unmasked branch reevaluated hints')
            da, db = a.evaluate(p, R, pairs, .001), b.evaluate(p, R, pairs, .001)
            if any(da[k].tobytes() != db[k].tobytes() for k in FIELDS):
                raise AssertionError('Unmasked public outputs differ')
            if lib.ns_test_witness_get_mxcsr() & ~0x3f != csr_control:
                raise AssertionError('Query changed caller SSE controls')
            if libc.fegetround() != saved_round:
                raise AssertionError('Query changed caller rounding')
            observations.append({'mode': mode, 'info': hot[3].tolist()})
        elif mode == 'rounding_and_denormals':
            for altered in ('downward', 'FTZ', 'DAZ'):
                libc.fesetround(saved_round)
                lib.ns_test_witness_set_mxcsr(saved_csr)
                if altered == 'downward':
                    libc.fesetround(0x400)
                else:
                    lib.ns_test_witness_set_mxcsr(saved_csr | (0x8000 if altered == 'FTZ' else 0x40))
                control = lib.ns_test_witness_get_mxcsr() & ~0x3f
                rounding = libc.fegetround()
                da, db = a.evaluate(p, R, pairs, .001), b.evaluate(p, R, pairs, .001)
                if any(da[k].tobytes() != db[k].tobytes() for k in FIELDS):
                    raise AssertionError('Invalid-environment outputs differ')
                if da['reason'][0] != 'invalid_arithmetic_environment' or a._witness_hints is not history:
                    raise AssertionError('Invalid environment accepted or published history')
                if (lib.ns_test_witness_get_mxcsr() & ~0x3f) != control or libc.fegetround() != rounding:
                    raise AssertionError('Invalid query changed caller controls')
                observations.append({'mode': altered, 'reason': str(da['reason'][0])})
        else:
            raise ValueError('Unknown probe mode')
    finally:
        libc.fedisableexcept(0x3d)
        if saved_traps:
            libc.feenableexcept(saved_traps)
        libc.fesetround(saved_round)
        lib.ns_test_witness_set_mxcsr(saved_csr)
    try:
        da, db = a.evaluate(p, R, pairs, .001), b.evaluate(p, R, pairs, .001)
        if any(da[k].tobytes() != db[k].tobytes() for k in FIELDS):
            raise AssertionError('Restored environment did not recover')
        if libc.fegetround() != saved_round or libc.fegetexcept() != saved_traps:
            raise AssertionError('Caller fenv was not restored')
    finally:
        a.close()
        b.close()
    print(json.dumps({'passed': True, 'mode': mode, 'observations': observations}))


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--trap-child':
        trap_child(sys.argv[2], sys.argv[3])
    else:
        unittest.main(verbosity=2)
