"""Lazy, source-bound ctypes API for the audited support-bound kernel.

The C++ constructor owns copies of complete local vertices and extrema.
evaluate freezes p/R/pairs in independent binary64/int64 arrays, then creates
fresh C++ support caches for that frame. No compilation occurs on import.
Only caller-owned vertex IDs persist; every hinted projection is recomputed.
The ignored build cache binds kernel, compiler, strict flags and library hashes.
"""
from __future__ import annotations

import ctypes as C
from contextlib import contextmanager
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
from threading import RLock
import time

import numpy as np

_KERNEL_PATH = Path(__file__).resolve().with_name("support_kernel.cpp")
_CACHE_ROOT = Path(__file__).resolve().parent / "output" / "support-native-build"
_FLAGS = ("-std=c++17", "-shared", "-fPIC", "-O3", "-fno-fast-math",
          "-ffp-contract=off", "-frounding-math", "-Wall", "-Wextra")
_PROBE_TIMEOUT_S, _COMPILE_TIMEOUT_S, _LOCK_TIMEOUT_S = 5, 30, 10
_LIB = None
_METADATA = None
_LOAD_LOCK = RLock()
_DOUBLE = C.POINTER(C.c_double)
_INT64 = C.POINTER(C.c_int64)
_INT32 = C.POINTER(C.c_int32)
_MODES = np.asarray(["none", "enclosing_local_AABB", "full"])
_REASONS = np.asarray(["none", "separation_certified", "no_separation_certificate",
                       "nonfinite_or_unsupported_arithmetic", "invalid_margin",
                       "invalid_arithmetic_environment", "invalid_pair_index"])
_MODES.setflags(write=False)
_REASONS.setflags(write=False)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json_sha(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()


def _compiler_identity():
    compiler = shutil.which("g++")
    if not compiler:
        raise RuntimeError("Strict native support compiler g++ is unavailable")
    try:
        path = Path(compiler).resolve(strict=True)
        version = subprocess.run([str(path), "--version"], check=True, capture_output=True,
                                 text=True, timeout=_PROBE_TIMEOUT_S).stdout.strip()
        target = subprocess.run([str(path), "-dumpmachine"], check=True, capture_output=True,
                                text=True, timeout=_PROBE_TIMEOUT_S).stdout.strip()
        if not version or not target:
            raise RuntimeError("Native compiler identity is incomplete")
        return {"path": str(path), "binary_sha256": _sha(path),
                "version": version, "target": target}
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError("Native compiler identity probe failed") from error


def _compile_process(command):
    # g++ can start cc1plus/as/ld children. Timeout must stop this isolated
    # compiler group, not leave compiler children running after g++ is killed.
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, cwd=_KERNEL_PATH.parent, start_new_session=True) as process:
        try:
            stdout, stderr = process.communicate(timeout=_COMPILE_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate(timeout=_PROBE_TIMEOUT_S)
            raise
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def _expected_build(identity):
    try:
        kernel_sha = _sha(_KERNEL_PATH)
    except OSError as error:
        raise RuntimeError("Audited native support kernel is unavailable") from error
    compiler_sha = _json_sha(identity)
    flags_sha = _json_sha(list(_FLAGS))
    key = _json_sha({"schema_version": 1, "kernel_sha256": kernel_sha,
                     "compiler_identity_sha256": compiler_sha, "flags_sha256": flags_sha})
    return {"schema_version": 1, "kernel_path": str(_KERNEL_PATH), "kernel_sha256": kernel_sha,
            "compiler_path": identity["path"], "compiler_sha256": identity["binary_sha256"],
            "compiler_version": identity["version"], "compiler_target": identity["target"],
            "compiler_identity_sha256": compiler_sha,
            "flags": list(_FLAGS), "flags_sha256": flags_sha, "cache_key": key}


def _validated_manifest(directory, expected):
    library, manifest = directory / "libsupport_kernel.so", directory / "manifest.json"
    try:
        data = json.loads(manifest.read_text())
        if not isinstance(data, dict) or any(data.get(k) != v for k, v in expected.items()):
            return None
        if data.get("library_path") != str(library) or data.get("manifest_path") != str(manifest):
            return None
        if not library.is_file() or _sha(library) != data.get("library_sha256"):
            return None
        return data
    except (OSError, ValueError, TypeError):
        return None


@contextmanager
def _build_lock(directory):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "build.lock").open("a+b") as stream:
        deadline = time.monotonic() + _LOCK_TIMEOUT_S
        while True:
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Native support cache lock deadline exceeded")
                time.sleep(.05)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _ensure_build(identity):
    expected = _expected_build(identity)
    directory = _CACHE_ROOT / expected["cache_key"]
    try:
        with _build_lock(directory):
            cached = _validated_manifest(directory, expected)
            if cached is not None:
                return cached
            with tempfile.TemporaryDirectory(prefix=".build-", dir=directory) as temporary:
                temporary = Path(temporary)
                output = temporary / "libsupport_kernel.so"
                command = [identity["path"], *_FLAGS, str(_KERNEL_PATH), "-o", str(output)]
                try:
                    process = _compile_process(command)
                except (OSError, subprocess.SubprocessError) as error:
                    (directory / "compile.log").write_text(
                        json.dumps({"command": command, "error": str(error)}, indent=2) + "\n")
                    raise RuntimeError("Strict native support compilation failed or timed out") from error
                (directory / "compile.log").write_text(json.dumps({"command": command,
                    "returncode": process.returncode, "stdout": process.stdout,
                    "stderr": process.stderr}, indent=2) + "\n")
                if process.returncode or not output.is_file():
                    raise RuntimeError("Strict native support compilation failed")
                # Neither changed source nor a replaced compiler can be published
                # as the identity recorded before the bounded compile.
                if _sha(_KERNEL_PATH) != expected["kernel_sha256"]:
                    raise RuntimeError("Native support kernel changed during compilation")
                if _sha(identity["path"]) != expected["compiler_sha256"]:
                    raise RuntimeError("Native compiler changed during compilation")
                library, manifest = directory / "libsupport_kernel.so", directory / "manifest.json"
                data = {**expected, "library_path": str(library), "library_sha256": _sha(output),
                        "manifest_path": str(manifest)}
                temporary_manifest = temporary / "manifest.json"
                temporary_manifest.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")
                # Both files are replaced only under the process-wide cache lock.
                # No reader accepts an old manifest paired with a new library.
                os.replace(output, library)
                os.replace(temporary_manifest, manifest)
                verified = _validated_manifest(directory, expected)
                if verified is None:
                    raise RuntimeError("Published native support cache failed hash validation")
                return verified
    except OSError as error:
        raise RuntimeError("Native support cache is unavailable") from error


def _configure_library(lib):
    lib.ns_environment.argtypes = [C.POINTER(C.c_int), C.POINTER(C.c_uint32), C.POINTER(C.c_int), C.POINTER(C.c_int)]
    lib.ns_environment.restype = C.c_int
    lib.ns_create.argtypes = [C.c_int64, _INT64, _DOUBLE, _INT32]
    lib.ns_create.restype = C.c_void_p
    lib.ns_destroy.argtypes = [C.c_void_p]
    lib.ns_destroy.restype = None
    lib.ns_evaluate.argtypes = [C.c_void_p, _DOUBLE, _DOUBLE, _INT64, C.c_int64, C.c_double, _DOUBLE, _INT64]
    lib.ns_evaluate.restype = C.c_int
    lib.ns_evaluate_hinted.argtypes = [C.c_void_p, _DOUBLE, _DOUBLE, _INT64,
                                     C.c_int64, C.c_double, _DOUBLE, _INT64, _INT64, _INT64]
    lib.ns_evaluate_hinted.restype = C.c_int
    for name in ("ns_down", "ns_up"):
        getattr(lib, name).argtypes = [C.c_double]
        getattr(lib, name).restype = C.c_double
    for name in ("ns_add", "ns_mul", "ns_dot3"):
        getattr(lib, name).argtypes = [_DOUBLE, _DOUBLE, _DOUBLE]
        getattr(lib, name).restype = None
    lib.ns_gate.argtypes = [C.c_double, C.c_double, C.c_double, _DOUBLE]
    lib.ns_gate.restype = C.c_int


def _get_library():
    global _LIB, _METADATA
    with _LOAD_LOCK:
        if _LIB is None:
            metadata = _ensure_build(_compiler_identity())
            try:
                lib = C.CDLL(metadata["library_path"])
                _configure_library(lib)
            except (OSError, AttributeError) as error:
                raise RuntimeError("Verified native support library could not load") from error
            _LIB, _METADATA = lib, metadata
        return _LIB


def library_metadata() -> dict:
    """Recheck disk identity, then return the binding of the pinned library.

    A mismatch never rebuilds or swaps an active handle. Disk replacement
    does not imply that the already loaded memory image has changed.
    """
    _get_library()
    with _LOAD_LOCK:
        try:
            unchanged = (_sha(_KERNEL_PATH) == _METADATA['kernel_sha256']
                         and str(_KERNEL_PATH) == _METADATA['kernel_path']
                         and _sha(_METADATA['library_path']) == _METADATA['library_sha256']
                         and _sha(_METADATA['compiler_path']) == _METADATA['compiler_sha256']
                         and _json_sha(list(_FLAGS)) == _METADATA['flags_sha256']
                         and json.loads(Path(_METADATA['manifest_path']).read_text()) == _METADATA)
        except (OSError, ValueError, TypeError, KeyError) as error:
            raise RuntimeError('Pinned native library provenance is unavailable') from error
        if not unchanged:
            raise RuntimeError('Pinned native library provenance changed on disk')
        return copy.deepcopy(_METADATA)


def _arithmetic_environment(lib) -> dict:
    rounding, control, subinput, suboutput = C.c_int(), C.c_uint32(), C.c_int(), C.c_int()
    status = lib.ns_environment(C.byref(rounding), C.byref(control), C.byref(subinput), C.byref(suboutput))
    return {"valid": status == 0, "rounding_mode": rounding.value, "mxcsr": control.value,
            "FTZ": bool(control.value & (1 << 15)), "DAZ": bool(control.value & (1 << 6)),
            "subnormal_input_preserved": bool(subinput.value),
            "subnormal_output_preserved": bool(suboutput.value),
            "binary64_mantissa_bits": np.finfo(np.float64).nmant}


def arithmetic_environment() -> dict:
    return _arithmetic_environment(_get_library())


class NativeSupport:
    def __init__(self, points: list[np.ndarray], kinds: list[str]):
        self._lock = RLock()
        self._handle = None
        self._witness_hints = None
        if len(points) == 0 or len(points) != len(kinds):
            raise ValueError("Geometry and kind counts must match and be nonempty")
        arrays = [np.array(p, dtype=np.float64, order="C", copy=True) for p in points]
        if any(a.ndim != 2 or a.shape[1] != 3 or len(a) == 0 or not np.isfinite(a).all() for a in arrays):
            raise ValueError("Each original geometry needs nonempty finite Nx3 vertices")
        if any(k not in ("mesh", "box") for k in kinds):
            raise ValueError("Unsupported geometry cannot obtain a certificate")
        self._lib = _get_library()
        if not _arithmetic_environment(self._lib)["valid"]:
            raise RuntimeError("Native support requires binary64 RN with gradual underflow")
        offsets = np.asarray([0, *np.cumsum([len(a) for a in arrays])], dtype=np.int64)
        flat = np.ascontiguousarray(np.concatenate(arrays, axis=0))
        kind_ids = np.asarray([1 if k == "mesh" else 0 for k in kinds], dtype=np.int32)
        hints = np.full((len(arrays), 3, 2), -1, dtype=np.int64)
        hints.setflags(write=False)
        with self._lock:
            handle = self._lib.ns_create(len(arrays), offsets.ctypes.data_as(_INT64),
                                    flat.ctypes.data_as(_DOUBLE), kind_ids.ctypes.data_as(_INT32))
            if not handle:
                raise RuntimeError("Native geometry preprocessing failed closed")
            self._handle = handle
            self.geometry_count = len(arrays)
            self._witness_hints = hints

    def close(self):
        with self._lock:
            if self._handle:
                self._lib.ns_destroy(self._handle)
                self._handle = None
            self._witness_hints = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass  # Interpreter shutdown may already have released ctypes globals.

    def evaluate(self, positions, rotations, pairs, margin: float) -> dict[str, np.ndarray]:
        with self._lock:
            return self._evaluate_locked(positions, rotations, pairs, margin)

    def bind_pairs(self, pairs):
        """Own a validated ordered snapshot; evaluation retains this handle's lock."""
        with self._lock:
            if not self._handle:
                raise RuntimeError("NativeSupport is closed")
            q = self._copy_pairs(pairs)
            q.setflags(write=False)
            return _BoundPairs(self, q)

    def _copy_pairs(self, pairs):
        raw_pairs = np.asarray(pairs)
        if raw_pairs.dtype.kind not in ("i", "u"):
            raise ValueError("Pair indices must have an integer dtype without truncation")
        if raw_pairs.ndim != 2 or raw_pairs.shape[1] != 2:
            raise ValueError("Pairs must have shape Mx2")
        if raw_pairs.size and (np.any(raw_pairs < 0) or np.any(raw_pairs >= self.geometry_count)):
            raise ValueError("Pair indices must refer to owned original geometry")
        return np.array(raw_pairs, dtype=np.int64, order="C", copy=True)

    def _evaluate_locked(self, positions, rotations, pairs, margin):
        if not self._handle:
            raise RuntimeError("NativeSupport is closed")
        return self._decode(*self._frame_locked(positions, rotations, pairs, margin))

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
        hint_in = np.array(self._witness_hints, dtype=np.int64, order="C", copy=True)
        hint_out = np.empty_like(hint_in)
        status = self._lib.ns_evaluate_hinted(
            self._handle, p.ctypes.data_as(_DOUBLE), R.ctypes.data_as(_DOUBLE),
            q.ctypes.data_as(_INT64), len(q), float(margin),
            numeric.ctypes.data_as(_DOUBLE), flags.ctypes.data_as(_INT64),
            hint_in.ctypes.data_as(_INT64), hint_out.ctypes.data_as(_INT64))
        if status:
            raise RuntimeError("Native frame evaluation failed closed")
        # A failed/uncertified frame cannot publish a new history. Neither
        # history nor IDs are a certificate; all pairs still run each call.
        if len(q) and flags[:, 0].all():
            hint_out.setflags(write=False)
            self._witness_hints = hint_out
        return numeric, flags

    @staticmethod
    def _decode(numeric, flags):
        return {"certified": flags[:, 0].astype(bool), "support_mode": _MODES[flags[:, 1]],
                "direction_index": flags[:, 2], "evaluations": flags[:, 3],
                "reason": _REASONS[flags[:, 4]], "orientation": flags[:, 5],
                "n": numeric[:, :3], "projection_a": numeric[:, 3:5], "projection_b": numeric[:, 5:7],
                "gap_lower": numeric[:, 7], "norm_squared_upper": numeric[:, 8],
                "squared_gap_lower": numeric[:, 9], "squared_threshold_upper": numeric[:, 10],
                "lower_bound_m": numeric[:, 11]}


class _BoundPairs:
    """Private immutable query policy; each call owns fresh frame/output arrays."""

    def __init__(self, owner, pairs):
        self._owner = owner
        self._pairs = pairs

    def evaluate(self, positions, rotations, margin):
        with self._owner._lock:
            return self._owner._decode(*self._owner._frame_locked(positions, rotations, self._pairs, margin, bound=True))

    def summary(self, positions, rotations, margin):
        with self._owner._lock:
            numeric, flags = self._owner._frame_locked(positions, rotations, self._pairs, margin, bound=True)
            certified = flags[:, 0].astype(bool)
            failures = np.flatnonzero(~certified)
            nearest = int(failures[0]) if len(failures) else int(np.argmin(numeric[:, 11]))
            return {"valid": not len(failures), "nearest_index": nearest,
                    "lower_bound_m": float(numeric[nearest, 11]),
                    "certificate_reason": str(_REASONS[flags[nearest, 4]]),
                    "certified_pairs": int(certified.sum()), "checked_pairs": len(self._pairs)}
