"""Exact full-tree/full-scan regressions; isolated strict test build only."""
from __future__ import annotations

import ctypes as C
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

import numpy as np


HERE = Path(__file__).resolve().parent
AUDIT = HERE / "output" / "support-tree-audit"
KERNEL = HERE / "support_kernel.cpp"
RECORDS = []
BUILD = {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_test_library():
    spec = importlib.util.spec_from_file_location("support_tree_test_loader", HERE / "support_native.py")
    loader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loader)
    identity = loader._compiler_identity()
    source_hash = sha(KERNEL)
    flags = [*loader._FLAGS, "-DSUPPORT_TREE_TESTS"]
    build_dir = HERE / "output" / "support-tree-tests" / source_hash
    build_dir.mkdir(parents=True, exist_ok=True)
    library = build_dir / "libsupport_tree_tests.so"
    command = [identity["path"], *flags, str(KERNEL), "-o", str(library)]
    process = loader._compile_process(command)
    BUILD.update(kernel_path=str(KERNEL), kernel_sha256=source_hash,
                 compiler=identity, flags=flags, command=command,
                 compile_timeout_s=loader._COMPILE_TIMEOUT_S,
                 compile_returncode=process.returncode,
                 compile_stdout=process.stdout, compile_stderr=process.stderr)
    if process.returncode or not library.is_file():
        raise RuntimeError("Strict test build failed")
    if sha(KERNEL) != source_hash or sha(identity["path"]) != identity["binary_sha256"]:
        raise RuntimeError("Test build source or compiler changed")
    BUILD.update(library_path=str(library), library_sha256=sha(library))
    lib = C.CDLL(str(library))
    double = C.POINTER(C.c_double)
    int64 = C.POINTER(C.c_int64)
    lib.ns_test_full_vertices.argtypes = [C.c_int64, double, double, C.c_int, double, int64]
    lib.ns_test_full_vertices.restype = C.c_int
    return lib


class SupportTreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = build_test_library()

    @classmethod
    def tearDownClass(cls):
        if sha(KERNEL) != BUILD["kernel_sha256"]:
            raise AssertionError("Candidate changed during test run")

    def compare(self, label, points, coefficients, *, status=0, fallback=None, coverage=True):
        points = np.array(points, dtype=np.float64, order="C", copy=True)
        coefficients = np.array(coefficients, dtype=np.float64, order="C", copy=True)
        self.assertEqual(points.shape[1:], (3,))
        self.assertEqual(coefficients.shape, (3, 2))
        results = []
        for tree in (0, 1):
            output = np.full(2, np.nan, dtype=np.float64)
            info = np.zeros(4, dtype=np.int64)
            result = self.lib.ns_test_full_vertices(
                len(points), points.ctypes.data_as(C.POINTER(C.c_double)),
                coefficients.ctypes.data_as(C.POINTER(C.c_double)), tree,
                output.ctypes.data_as(C.POINTER(C.c_double)),
                info.ctypes.data_as(C.POINTER(C.c_int64)))
            results.append({"status": result, "endpoint_uint64": output.view(np.uint64).tolist(),
                            "endpoint_repr": [repr(float(x)) for x in output], "info": info.tolist()})
        RECORDS.append({"label": label, "vertex_count": len(points),
                        "coefficient_uint64": coefficients.view(np.uint64).tolist(),
                        "scan": results[0], "tree": results[1]})
        self.assertEqual(results[0]["status"], results[1]["status"], label)
        self.assertEqual(results[0]["status"], status, label)
        self.assertEqual(results[0]["endpoint_uint64"], results[1]["endpoint_uint64"], label)
        if coverage:
            for result in results:
                self.assertEqual(result["info"][0], 1, label)
                self.assertLessEqual(result["info"][2], 16, label)
        if fallback is not None:
            self.assertEqual(results[1]["info"][3], int(fallback), label)
        return results

    def test_leaf_split_boundaries_and_complete_coverage(self):
        rng = np.random.default_rng(20261007)
        for count, nodes, largest in ((15, 1, 15), (16, 1, 16), (17, 3, 9), (33, 5, 16)):
            with self.subTest(count=count):
                rows = self.compare(f"split-{count}", rng.normal(size=(count, 3)),
                                    [[1., 1.], [-.5, -.5], [.25, .25]], fallback=False)
                self.assertEqual(rows[1]["info"][1:3], [nodes, largest])

    def test_random_directions_with_interval_coefficients(self):
        rng = np.random.default_rng(541997)
        for count in (17, 33, 65, 129, 257):
            points = rng.uniform(-2., 2., (count, 3))
            for direction in range(12):
                n = rng.normal(size=3)
                n /= np.max(np.abs(n))
                coefficients = np.column_stack((np.nextafter(n, -np.inf), np.nextafter(n, np.inf)))
                self.compare(f"random-{count}-{direction}", points, coefficients, fallback=False)

    def test_duplicate_extrema_original_ties_and_signed_zero(self):
        rng = np.random.default_rng(128191)
        base = np.asarray([[0., -0., 0.], [-0., 0., -0.], [1., -1., -0.],
                           [-1., 1., 0.], [1., -1., 0.], [-1., 1., -0.],
                           [2., -2., 0.], [-2., 2., -0.]])
        points = np.tile(base, (8, 1))
        directions = ([[1., 1.], [1., 1.], [-0., 0.]],
                      [[-0., 0.], [0., -0.], [-0., 0.]],
                      [[-1., -1.], [1., 1.], [0., 0.]])
        for ordering in range(6):
            ordered = points if ordering == 0 else points[rng.permutation(len(points))]
            for index, coefficients in enumerate(directions):
                self.compare(f"ties-{ordering}-{index}", ordered, coefficients, fallback=False)

    def test_one_improvable_endpoint_must_not_prune(self):
        for sign in (-1., 1.):
            points = np.zeros((33, 3))
            points[1:, 0] = sign * np.arange(1., 33.)
            rows = self.compare(f"one-end-{sign:+.0f}", points,
                                [[1., 1.], [0., 0.], [0., 0.]], fallback=False)
            extrema = np.asarray(rows[1]["endpoint_uint64"], dtype=np.uint64).view(np.float64)
            if sign > 0:
                self.assertGreaterEqual(extrema[1], 32.)
            else:
                self.assertLessEqual(extrema[0], -32.)

    def test_interior_subtrees_keep_both_extrema(self):
        rng = np.random.default_rng(185191)
        points = np.zeros((129, 3))
        points[0, 0], points[1, 0] = 10., -10.
        points[2:] = rng.uniform(-.25, .25, (127, 3))
        self.compare("strict-interior-subtrees", points,
                     [[1., 1.], [0., 0.], [0., 0.]], fallback=False)

    def test_nonfinite_node_enclosure_falls_back_to_finite_scan(self):
        large = np.finfo(np.float64).max * .75
        points = np.tile([[large, large, 0.], [-large, -large, 0.]], (17, 1))[:33]
        rows = self.compare("correlated-node-overflow-leaves-finite", points,
                            [[1., 1.], [-1., -1.], [0., 0.]], fallback=True)
        self.assertTrue(np.isfinite(np.asarray(rows[1]["endpoint_uint64"], dtype=np.uint64)
                                   .view(np.float64)).all())

    def test_actual_leaf_overflow_fails_closed(self):
        large = np.finfo(np.float64).max * .75
        for seed_valid in (False, True):
            points = np.zeros((33, 3))
            points[:, 0] = large
            if seed_valid:
                points[0, 0] = 0.
            self.compare(f"leaf-overflow-seed-valid-{seed_valid}", points,
                         [[2., 2.], [0., 0.], [0., 0.]], status=1,
                         fallback=seed_valid)

    def test_nonfinite_input_refuses_support(self):
        for invalid in (np.nan, np.inf, -np.inf):
            points = np.zeros((17, 3))
            points[8, 1] = invalid
            self.compare(f"nonfinite-point-{invalid}", points,
                         [[1., 1.], [0., 0.], [0., 0.]], status=2, coverage=False)
            coefficients = np.ones((3, 2))
            coefficients[1, 0] = invalid
            self.compare(f"nonfinite-coefficient-{invalid}", np.ones((17, 3)),
                         coefficients, status=1, fallback=False)

    def test_subnormal_and_normal_boundary_vertices(self):
        tiny = np.nextafter(0., 1.)
        normal = np.finfo(np.float64).tiny
        values = np.asarray([0., -0., tiny, -tiny, normal, -normal,
                             np.nextafter(normal, 0.), np.nextafter(-normal, 0.)])
        points = np.column_stack((np.tile(values, 5), np.tile(values[::-1], 5), np.zeros(40)))
        for coefficients in ([[1., 1.], [-1., -1.], [0., 0.]],
                             [[-tiny, tiny], [-tiny, tiny], [-tiny, tiny]]):
            self.compare("subnormal-boundary", points, coefficients, fallback=False)


if __name__ == "__main__":
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(SupportTreeTests))
    status_counts = {}
    for row in RECORDS:
        status = str(row["tree"]["status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    report = {"schema_version": 1, "passed": result.wasSuccessful(),
              "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "paired_probes": len(RECORDS), "native_hook_calls": 2 * len(RECORDS),
              "status_counts": status_counts,
              "tree_fallbacks": sum(row["tree"]["info"][3] for row in RECORDS),
              "build": BUILD, "records": RECORDS,
              "script_sha256": sha(__file__), "kernel_sha256_after": sha(KERNEL),
              "scope": "Synthetic full-support hook; no controller, FK, CCD, integration, reset or render",
              "limits": "Finite fixtures test equivalence with original vertex scan; no physical or continuous collision claim"}
    AUDIT.mkdir(parents=True, exist_ok=True)
    (AUDIT / "support-tree-tests.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    sys.exit(0 if result.wasSuccessful() else 1)
