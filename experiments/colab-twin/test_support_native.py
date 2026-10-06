"""Lazy-loader, cache-integrity and bounded-build failure regressions."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import numpy as np


SOURCE = Path(__file__).with_name("support_native.py")


def fresh_module():
    spec = importlib.util.spec_from_file_location("native_loader_test_instance", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NativeLoaderTests(unittest.TestCase):
    def test_import_has_no_compile_or_library_load(self):
        with mock.patch("subprocess.run", side_effect=AssertionError("Import must not run compiler")), \
             mock.patch("ctypes.CDLL", side_effect=AssertionError("Import must not load library")):
            module = fresh_module()
        self.assertIsNone(module._LIB)
        self.assertIsNone(module._METADATA)

    def test_missing_compiler_fails_closed(self):
        module = fresh_module()
        with mock.patch.object(module.shutil, "which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "unavailable"):
                module.library_metadata()
        self.assertIsNone(module._LIB)

    def fixture(self, temporary):
        module = fresh_module()
        root = Path(temporary)
        module._KERNEL_PATH = root / "kernel.cpp"
        module._KERNEL_PATH.write_text("// isolated cache test input\n")
        compiler = root / "compiler"
        compiler.write_bytes(b"isolated compiler identity")
        identity = {"path": str(compiler), "binary_sha256": module._sha(compiler),
                    "version": "isolated test compiler", "target": "isolated-test"}
        module._CACHE_ROOT = root / "cache"
        expected = module._expected_build(identity)
        directory = module._CACHE_ROOT / expected["cache_key"]
        return module, identity, expected, directory

    def install_manifest(self, module, expected, directory):
        directory.mkdir(parents=True)
        library, manifest = directory / "libsupport_kernel.so", directory / "manifest.json"
        library.write_bytes(b"isolated cache payload")
        data = {**expected, "library_path": str(library), "library_sha256": module._sha(library),
                "manifest_path": str(manifest)}
        manifest.write_text(json.dumps(data))
        return data

    def test_cache_hit_does_not_compile(self):
        with tempfile.TemporaryDirectory() as temporary:
            module, identity, expected, directory = self.fixture(temporary)
            data = self.install_manifest(module, expected, directory)
            with mock.patch.object(module, "_compile_process", side_effect=AssertionError("Cache hit rebuilt")):
                self.assertEqual(module._ensure_build(identity), data)

    def test_manifest_and_library_tampering_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            module, identity, expected, directory = self.fixture(temporary)
            original = self.install_manifest(module, expected, directory)
            self.assertEqual(module._validated_manifest(directory, expected), original)
            for field in ("kernel_sha256", "compiler_sha256", "compiler_identity_sha256", "flags_sha256", "library_path"):
                with self.subTest(field=field):
                    tampered = {**original, field: "invalid"}
                    (directory / "manifest.json").write_text(json.dumps(tampered))
                    self.assertIsNone(module._validated_manifest(directory, expected))
            (directory / "manifest.json").write_text(json.dumps(original))
            (directory / "libsupport_kernel.so").write_bytes(b"altered cache payload")
            self.assertIsNone(module._validated_manifest(directory, expected))

    def test_compile_timeout_publishes_no_library(self):
        with tempfile.TemporaryDirectory() as temporary:
            module, identity, expected, directory = self.fixture(temporary)
            timeout = subprocess.TimeoutExpired([identity["path"]], module._COMPILE_TIMEOUT_S)
            with mock.patch.object(module, "_compile_process", side_effect=timeout):
                with self.assertRaisesRegex(RuntimeError, "timed out"):
                    module._ensure_build(identity)
            self.assertFalse((directory / "libsupport_kernel.so").exists())
            self.assertFalse((directory / "manifest.json").exists())

    def test_failed_compile_does_not_replace_existing_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            module, identity, expected, directory = self.fixture(temporary)
            data = self.install_manifest(module, expected, directory)
            library = directory / "libsupport_kernel.so"
            library.write_bytes(b"damaged original payload")
            before = library.read_bytes()
            failure = subprocess.CompletedProcess([identity["path"]], 1, "", "compiler failed")
            with mock.patch.object(module, "_compile_process", return_value=failure):
                with self.assertRaisesRegex(RuntimeError, "compilation failed"):
                    module._ensure_build(identity)
            self.assertEqual(library.read_bytes(), before)
            self.assertEqual(json.loads((directory / "manifest.json").read_text()), data)

    def test_source_change_during_build_cannot_publish(self):
        with tempfile.TemporaryDirectory() as temporary:
            module, identity, expected, directory = self.fixture(temporary)
            def compile_then_change_source(command, **kwargs):
                Path(command[-1]).write_bytes(b"isolated compiled artifact")
                module._KERNEL_PATH.write_text("// source changed during build\n")
                return subprocess.CompletedProcess(command, 0, "", "")
            with mock.patch.object(module, "_compile_process", side_effect=compile_then_change_source):
                with self.assertRaisesRegex(RuntimeError, "changed during"):
                    module._ensure_build(identity)
            self.assertFalse((directory / "libsupport_kernel.so").exists())
            self.assertFalse((directory / "manifest.json").exists())

    def test_compile_timeout_kills_only_isolated_compiler_group(self):
        module = fresh_module()
        command = ["g++", "isolated-test-input"]
        process = mock.MagicMock()
        process.pid = 12345
        process.__enter__.return_value = process
        process.communicate.side_effect = [subprocess.TimeoutExpired(command, 30), ("", "")]
        with mock.patch.object(module.subprocess, "Popen", return_value=process) as spawn, \
             mock.patch.object(module.os, "killpg") as kill:
            with self.assertRaises(subprocess.TimeoutExpired):
                module._compile_process(command)
        self.assertTrue(spawn.call_args.kwargs["start_new_session"])
        kill.assert_called_once_with(process.pid, module.signal.SIGKILL)

    def test_real_lazy_load_metadata_and_owned_vertices(self):
        module = fresh_module()
        half = .01
        corners = np.asarray([[x*half, y*half, z*half] for x in (-1, 1)
                              for y in (-1, 1) for z in (-1, 1)], dtype=np.float64)
        native = module.NativeSupport([corners, corners], ["mesh", "box"])
        try:
            # Mutating constructor input must not change the owned native shape.
            corners[:] = 10.
            result = native.evaluate([[0., 0., 0.], [.03, 0., 0.]],
                                     np.tile(np.eye(3), (2, 1, 1)), np.asarray([[0, 1]]), .001)
            self.assertTrue(result["certified"][0])
            self.assertEqual(result["direction_index"][0], 0)
            metadata = module.library_metadata()
            self.assertEqual(metadata["kernel_sha256"], module._sha(module._KERNEL_PATH))
            self.assertEqual(metadata["library_sha256"], module._sha(metadata["library_path"]))
            self.assertEqual(metadata["flags"], list(module._FLAGS))
            self.assertEqual(metadata["compiler_sha256"], module._sha(metadata["compiler_path"]))
            metadata["flags"].append("-ffast-math")
            self.assertEqual(module.library_metadata()["flags"], list(module._FLAGS))
        finally:
            native.close()

    def test_loaded_metadata_rejects_disk_changes_without_rebuild_or_reload(self):
        for changed in ('kernel', 'library', 'compiler', 'flags', 'manifest'):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as temporary:
                module, identity, expected, directory = self.fixture(temporary)
                data = self.install_manifest(module, expected, directory)
                pinned = object()
                module._LIB, module._METADATA = pinned, data
                self.assertEqual(module.library_metadata(), data)
                if changed == 'flags':
                    module._FLAGS = (*module._FLAGS, '-ffast-math')
                elif changed == 'manifest':
                    Path(data['manifest_path']).write_text('{}')
                else:
                    path = module._KERNEL_PATH if changed == 'kernel' else Path(data[changed+'_path'])
                    path.write_bytes(b'changed after library load')
                with mock.patch.object(module, '_compile_process', side_effect=AssertionError('No rebuild')), \
                        mock.patch.object(module.C, 'CDLL', side_effect=AssertionError('No reload')):
                    with self.assertRaisesRegex(RuntimeError, 'provenance changed'):
                        module.library_metadata()
                self.assertIs(module._LIB, pinned)


if __name__ == "__main__":
    unittest.main()
