"""Exact support-seed regressions with observations only in an ignored copy."""
from __future__ import annotations

import ctypes as C
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import sys
import time
import unittest

import numpy as np
import test_support_tree as legacy


HERE = Path(__file__).resolve().parent
KERNEL = HERE / 'support_kernel.cpp'
AUDIT = HERE / 'output' / 'visual-grasp-native-profile-20261007' / 'test-audit'
BUILD, RECORDS, PAIR_RECORDS = {}, [], []
DOUBLE, INT64, INT32 = C.POINTER(C.c_double), C.POINTER(C.c_int64), C.POINTER(C.c_int32)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pointer(array, kind=DOUBLE):
    return array.ctypes.data_as(kind)


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError('Observation anchor changed: ' + old[:65])
    return text.replace(old, new, 1)


def observed_copy(source):
    """Add observations without changing original arithmetic or branch choices."""
    marker = '// Seed from real vertices in two greedily selected leaves.'
    globals_text = '''std::array<std::int64_t,12> seed_probe{};
std::array<std::int64_t,5> tree_probe{};
std::array<double,4> seed_points{};
'''
    source = replace_once(source, marker, globals_text + marker)
    begin, end = source.index('bool seed_extreme('), source.index('\n#endif', source.index('bool seed_extreme('))
    body = source[begin:end]
    body = replace_once(body, '    std::size_t index=0;',
                        '    const std::size_t s=minimum?0:6; seed_probe[s]=1;\n    std::size_t index=0;')
    body = replace_once(body, '        if (!finite(first)||!finite(second)) return false;',
                        '        if (!finite(first)||!finite(second)) { seed_probe[s+4]=1; return false; }')
    body = replace_once(body, '    const auto& leaf=geom.nodes[index];',
                        '    seed_probe[s+1]=static_cast<std::int64_t>(index);\n    const auto& leaf=geom.nodes[index];')
    body = replace_once(body, '    if (!vertex_interval(geom,vertex,local,point)) return false;',
                        '    ++seed_probe[s+3];\n    if (!vertex_interval(geom,vertex,local,point)) { seed_probe[s+4]=2; return false; }')
    body = replace_once(body, '        if (!vertex_interval(geom,v,local,candidate)) return false;',
                        '        ++seed_probe[s+3];\n        if (!vertex_interval(geom,v,local,candidate)) { seed_probe[s+4]=2; return false; }')
    body = replace_once(body, '    return true;',
                        '    seed_probe[s+2]=static_cast<std::int64_t>(vertex); seed_probe[s+5]=1;\n'
                        '    seed_points[s/3]=point.lo; seed_points[s/3+1]=point.hi;\n    return true;')
    source = source[:begin] + body + source[end:]
    begin, end = source.index('bool full_tree('), source.index('\nstruct Context', source.index('bool full_tree('))
    body = source[begin:end]
    body = replace_once(body, '        if (bound.lo>minimum && bound.hi<maximum) continue;',
                        '        tree_probe[2]+=(bound.lo==minimum); tree_probe[3]+=(bound.hi==maximum);\n'
                        '        tree_probe[4]+=(bound.lo>minimum && bound.hi<maximum);\n'
                        '        if (bound.lo>minimum && bound.hi<maximum) continue;')
    body = replace_once(body, '    out={minimum,maximum};return true;',
                        '    tree_probe[0]=static_cast<std::int64_t>(min_index);\n'
                        '    tree_probe[1]=static_cast<std::int64_t>(max_index);\n    out={minimum,maximum};return true;')
    source = source[:begin] + body + source[end:]
    source += '''
extern "C" void ns_test_seed_reset() {
    seed_probe={}; tree_probe={}; tree_probe[0]=tree_probe[1]=-1;
    seed_points={NAN_VALUE,NAN_VALUE,NAN_VALUE,NAN_VALUE};
}
extern "C" void ns_test_seed_snapshot(std::int64_t* info,double* points) {
    std::copy(seed_probe.begin(),seed_probe.end(),info);
    std::copy(tree_probe.begin(),tree_probe.end(),info+12);
    std::copy(seed_points.begin(),seed_points.end(),points);
}
'''
    return source


def build_libraries():
    spec = importlib.util.spec_from_file_location('support_seed_test_loader', HERE / 'support_native.py')
    loader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loader)
    identity, original_hash = loader._compiler_identity(), sha(KERNEL)
    directory = AUDIT / 'build' / original_hash
    directory.mkdir(parents=True, exist_ok=True)
    copied = directory / 'support_seed_observed.cpp'
    copied.write_text(observed_copy(KERNEL.read_text()))
    BUILD.update(kernel_path=str(KERNEL), kernel_sha256=original_hash,
                 observed_copy_path=str(copied), observed_copy_sha256=sha(copied),
                 compiler=identity, compile_timeout_s=loader._COMPILE_TIMEOUT_S, libraries={})
    libraries = {}
    for name, extra in (('seed', []), ('original', ['-DSUPPORT_TREE_SEED_DISABLED'])):
        flags = [*loader._FLAGS, '-DSUPPORT_TREE_TESTS', *extra]
        path = directory / ('libsupport_seed_' + name + '.so')
        command = [identity['path'], *flags, str(copied), '-o', str(path)]
        process = loader._compile_process(command)
        BUILD['libraries'][name] = dict(flags=flags, command=command, returncode=process.returncode,
                                      stdout=process.stdout, stderr=process.stderr,
                                      library_path=str(path))
        if process.returncode or not path.is_file():
            raise RuntimeError('Strict isolated test build failed: ' + name)
        if sha(KERNEL) != original_hash or sha(identity['path']) != identity['binary_sha256']:
            raise RuntimeError('Kernel or compiler changed during build')
        BUILD['libraries'][name]['library_sha256'] = sha(path)
        lib = C.CDLL(str(path))
        loader._configure_library(lib)
        lib.ns_test_full_vertices.argtypes = [C.c_int64, DOUBLE, DOUBLE, C.c_int, DOUBLE, INT64]
        lib.ns_test_full_vertices.restype = C.c_int
        lib.ns_test_seed_reset.argtypes, lib.ns_test_seed_reset.restype = [], None
        lib.ns_test_seed_snapshot.argtypes = [INT64, DOUBLE]
        lib.ns_test_seed_snapshot.restype = None
        libraries[name] = lib
    return loader, libraries


class SupportSeedTests(legacy.SupportTreeTests):
    """Inherit all nine existing tree tests and compare three execution modes."""

    @classmethod
    def setUpClass(cls):
        cls.loader, cls.libraries = build_libraries()
        for lib in cls.libraries.values():
            if not cls.loader._arithmetic_environment(lib)['valid']:
                raise RuntimeError('Tests require original round-to-nearest environment')

    @classmethod
    def tearDownClass(cls):
        if sha(KERNEL) != BUILD['kernel_sha256']:
            raise AssertionError('Kernel changed during tests')

    def compare(self, label, points, coefficients, *, status=0, fallback=None, coverage=True):
        points = np.array(points, dtype=np.float64, order='C', copy=True)
        coefficients = np.array(coefficients, dtype=np.float64, order='C', copy=True)
        self.assertEqual(points.shape[1:], (3,))
        self.assertEqual(coefficients.shape, (3, 2))
        rows = []
        for name, mode in (('original', 0), ('original', 1), ('seed', 1)):
            lib = self.libraries[name]
            output, info = np.full(2, np.nan), np.zeros(4, dtype=np.int64)
            probe, seeds = np.zeros(17, dtype=np.int64), np.full(4, np.nan)
            lib.ns_test_seed_reset()
            result = lib.ns_test_full_vertices(len(points), pointer(points), pointer(coefficients),
                                               mode, pointer(output), pointer(info, INT64))
            lib.ns_test_seed_snapshot(pointer(probe, INT64), pointer(seeds))
            rows.append(dict(mode=name + ('_tree' if mode else '_scan'), status=result,
                             endpoint_uint64=output.view(np.uint64).tolist(), info=info.tolist(),
                             probe=probe.tolist(), seed_endpoint_uint64=seeds.view(np.uint64).tolist()))
        RECORDS.append(dict(label=label, vertex_count=len(points),
                            points_uint64=points.view(np.uint64).tolist(),
                            coefficients_uint64=coefficients.view(np.uint64).tolist(), rows=rows))
        for row in rows:
            self.assertEqual(row['status'], status, label)
            self.assertEqual(row['endpoint_uint64'], rows[0]['endpoint_uint64'], label)
            if coverage:
                self.assertEqual(row['info'][0], 1, label)
                self.assertLessEqual(row['info'][2], 16, label)
        self.assertEqual(rows[1]['info'], rows[2]['info'], label)
        self.assertEqual(rows[1]['probe'][12:14], rows[2]['probe'][12:14], label)
        if fallback is not None:
            self.assertEqual(rows[2]['info'][3], int(fallback), label)
        self.last_rows = rows
        return [rows[0], rows[2]]

    def test_seed_larger_original_index_ties_are_replaced_by_later_dfs(self):
        points = np.zeros((65, 3))
        points[:, 1] = np.linspace(-40., 40., 65)
        points[0] = [0., 0., -0.]
        points[1:5] = [[-10., 10., 0.], [-10., -10., -0.],
                       [10., 12., -0.], [10., -12., 0.]]
        self.compare('seed-larger-index-then-original-dfs-tie', points,
                     [[1., 1.], [-0., 0.], [0., -0.]], fallback=False)
        probe = self.last_rows[2]['probe']
        self.assertEqual(probe[2], 2)  # Actual minimum seed winner in the earlier leaf.
        self.assertEqual(probe[8], 4)  # Actual maximum seed winner in the earlier leaf.
        self.assertEqual(probe[12:14], [1, 3])  # Original lower indices win after DFS.
        self.assertEqual([probe[5], probe[11]], [1, 1])

    def test_seed_only_one_endpoint_improves(self):
        for sign in (-1., 1.):
            points = np.zeros((33, 3))
            points[1:, 0] = sign * np.arange(1., 33.)
            self.compare('seed-one-endpoint-' + str(sign), points,
                         [[1., 1.], [0., 0.], [-0., 0.]], fallback=False)
            probe = self.last_rows[2]['probe']
            self.assertEqual([probe[2], probe[8]], [32, 0] if sign < 0 else [0, 32])
            self.assertEqual(probe[12:14], [32, 0] if sign < 0 else [0, 32])

    def test_seed_same_leaf_degenerate_and_signedzero_inputs(self):
        for count in (1, 16, 17, 32, 33):
            points = np.zeros((count, 3))
            points[1::2, 0], points[::2, 2] = -0., -0.
            self.compare('seed-degenerate-signedzero-' + str(count), points,
                         [[-0., 0.], [1., 1.], [0., -0.]], fallback=False)
            probe = self.last_rows[2]['probe']
            self.assertEqual([probe[5], probe[11]], [1, 1])
            self.assertEqual(probe[12:14], [0, 0])
            if count <= 16:
                self.assertEqual(probe[1], probe[7])
                self.assertEqual([probe[3], probe[9]], [count, count])

    def test_prune_equality_and_adjacent_ulp_vertices(self):
        points = np.zeros((33, 3))
        points[:, 0] = 1.
        self.compare('seed-node-both-endpoints-exact-equality', points,
                     [[1., 1.], [0., 0.], [0., 0.]], fallback=False)
        probe = self.last_rows[2]['probe']
        self.assertGreater(probe[14], 0)
        self.assertGreater(probe[15], 0)
        self.assertEqual(probe[16], 0)
        for endpoint in (-1., 1.):
            for toward in (-np.inf, np.inf):
                points = np.zeros((33, 3))
                points[1, 0], points[2, 0] = -1., 1.
                points[3, 0] = np.nextafter(endpoint, toward)
                self.compare('seed-ulp-' + str(endpoint) + '-' + str(toward), points,
                             [[1., 1.], [-0., 0.], [0., 0.]], fallback=False)

    def test_seed_nonfinite_child_bounds_discard_then_finite_original_scan(self):
        large = np.finfo(np.float64).max * .75
        points = np.tile([-large, -large, 0.], (33, 1))
        points[-1] = [large, large, -0.]
        self.compare('seed-child-bound-nonfinite-original-scan-finite', points,
                     [[1., 1.], [-1., -1.], [0., 0.]], fallback=True)
        probe = self.last_rows[2]['probe']
        self.assertEqual([probe[0], probe[4], probe[5]], [1, 1, 0])
        self.assertEqual(probe[6], 0)  # Failed minimum exploration short-circuits maximum.
        self.assertTrue(np.isfinite(np.asarray(self.last_rows[2]['endpoint_uint64'],
                                             dtype=np.uint64).view(np.float64)).all())

    def test_seed_partial_leaf_overflow_discards_and_preserves_rejection(self):
        points = np.zeros((15, 3))
        points[-1, 0] = np.finfo(np.float64).max * .75
        self.compare('seed-leaf-overflow-after-finite-prefix', points,
                     [[2., 2.], [0., 0.], [0., 0.]], status=1, fallback=True)
        probe = self.last_rows[2]['probe']
        self.assertEqual([probe[0], probe[3], probe[4], probe[5]], [1, 15, 2, 0])
        self.assertEqual(probe[6], 0)

    def pair_probe(self, label, *, points, kinds, positions, rotations, pairs, margin):
        arrays = [np.array(p, dtype=np.float64, order='C', copy=True) for p in points]
        offsets = np.asarray([0, *np.cumsum([len(p) for p in arrays])], dtype=np.int64)
        flat, kinds = np.ascontiguousarray(np.concatenate(arrays)), np.asarray(kinds, dtype=np.int32)
        p, R = np.ascontiguousarray(positions), np.ascontiguousarray(rotations)
        pairs = np.array(pairs, dtype=np.int64, order='C', copy=True).reshape(-1, 2)
        rows = {}
        for name, lib in self.libraries.items():
            handle = lib.ns_create(len(arrays), pointer(offsets, INT64), pointer(flat), pointer(kinds, INT32))
            self.assertTrue(handle)
            try:
                numeric, flags = np.full((len(pairs), 12), -12345.), np.full((len(pairs), 6), -777, dtype=np.int64)
                status = lib.ns_evaluate(handle, pointer(p), pointer(R), pointer(pairs, INT64),
                                         len(pairs), margin, pointer(numeric), pointer(flags, INT64))
                rows[name] = (status, numeric, flags)
            finally:
                lib.ns_destroy(handle)
        a, b = rows['seed'], rows['original']
        self.assertEqual(a[0], b[0], label)
        self.assertEqual(a[0], 0, label)
        np.testing.assert_array_equal(a[1].view(np.uint64), b[1].view(np.uint64), err_msg=label)
        np.testing.assert_array_equal(a[2], b[2], err_msg=label)
        PAIR_RECORDS.append(dict(label=label, pair_count=len(pairs), margin_uint64=np.float64(margin).view(np.uint64).item(),
                                 seed_numeric_uint64=a[1].view(np.uint64).tolist(), original_numeric_uint64=b[1].view(np.uint64).tolist(),
                                 seed_flags=a[2].tolist(), original_flags=b[2].tolist()))
        return a

    def test_public_fullsupport_and_margin_boundaries_all_fields(self):
        triangle = np.asarray([[x, y, z] for x, y in ((0., 0.), (.01, 0.), (0., .01))
                               for z in (-.001, .001)], dtype=np.float64)
        # Repeat vertices so this public full-mesh path also exercises split trees.
        triangle = np.tile(triangle, (6, 1))
        p, R = np.asarray([[0., 0., 0.], [.006, .006, -0.]]), np.tile(np.eye(3), (2, 1, 1))
        R[1, 0, 2] = -0.
        result = self.pair_probe('public-coarse-overlap-fullsupport', points=[triangle, triangle], kinds=[1, 1],
                                 positions=p, rotations=R, pairs=[[0, 1], [1, 0], [0, 1]], margin=.001)
        self.assertTrue(np.all(result[2][:, 0]))
        self.assertTrue(np.all(result[2][:, 1] == 2))
        corners = np.asarray(list(itertools.product((-.01, .01), repeat=3)))
        for margin in (.001, .0002):
            for gap in (margin - 1e-9, margin, margin + 1e-9):
                for axis in range(3):
                    p = np.zeros((2, 3)); p[1, axis] = .02 + gap
                    result = self.pair_probe('public-boundary-' + str(margin) + '-' + str(gap) + '-' + str(axis),
                                             points=[corners, corners], kinds=[1, 0], positions=p, rotations=R,
                                             pairs=[[0, 1], [1, 0], [0, 1]], margin=margin)
                    if gap < margin:
                        self.assertFalse(np.any(result[2][:, 0]))
                    elif gap > margin:
                        self.assertTrue(np.all(result[2][:, 0]))


if __name__ == '__main__':
    start = time.perf_counter()
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(SupportSeedTests))
    report = dict(schema_version=1, passed=result.wasSuccessful(), tests_run=result.testsRun,
                  failures=len(result.failures), errors=len(result.errors), wall_s=time.perf_counter()-start,
                  inherited_tree_methods=9, support_probes=len(RECORDS), support_hook_calls=3*len(RECORDS),
                  public_pair_probes=len(PAIR_RECORDS), public_evaluate_calls=2*len(PAIR_RECORDS),
                  public_pair_rows=sum(row['pair_count'] for row in PAIR_RECORDS),
                  build=BUILD, records=RECORDS, public_records=PAIR_RECORDS,
                  script_sha256=sha(__file__), kernel_sha256_after=sha(KERNEL),
                  loader_sha256=sha(HERE/'support_native.py'), legacy_test_sha256=sha(HERE/'test_support_tree.py'),
                  observation_schema=dict(seed_each=['entered', 'selected_leaf', 'winner_original_index', 'vertex_attempts',
                                                    'failure_0none_1node_2vertex', 'completed'],
                                          tree=['minimum_original_index', 'maximum_original_index', 'bound_lower_equal',
                                                'bound_upper_equal', 'strict_pruned']),
                  scope='Synthetic support/evaluate ABI only; no controller, FK, CCD, integration, reset, render or benchmark',
                  limits='Finite fixtures, original fullscan and same-source disabled-tree reference; no performance, physical or continuous-collision claim')
    AUDIT.mkdir(parents=True, exist_ok=True)
    (AUDIT/'support-seed-tests.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    sys.exit(0 if result.wasSuccessful() else 1)
