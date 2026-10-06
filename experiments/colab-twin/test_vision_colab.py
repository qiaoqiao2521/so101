"""CPU-only hostile/incomplete Colab artifact checks; never invokes the CLI."""
import copy
from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import warnings
from zipfile import ZipFile, ZIP_STORED

import run_vision_colab as runner


def digest(data):
    return hashlib.sha256(data).hexdigest()


class RecoveryIndexTests(unittest.TestCase):
    def valid(self):
        return {"zip": {"file": "results.zip", "bytes": 3, "sha256": digest(b"abc")},
                "shards": [{"file": "results.zip.part-0000", "bytes": 3, "sha256": digest(b"abc")}]}

    def test_valid_index(self):
        runner.validate_index(self.valid())

    def test_path_escaping_and_dot_shard_names_rejected(self):
        for name in ("..", ".", "../part", "/tmp/part", "x/part", "x\\part", ""):
            with self.subTest(name=name):
                index = self.valid()
                index["shards"][0]["file"] = name
                with self.assertRaises(ValueError):
                    runner.validate_index(index)

    def test_duplicate_shards_rejected(self):
        index = self.valid()
        index["shards"].append(copy.deepcopy(index["shards"][0]))
        index["zip"]["bytes"] = 6
        with self.assertRaises(ValueError):
            runner.validate_index(index)

    def test_incomplete_shard_coverage_rejected(self):
        index = self.valid()
        index["zip"]["bytes"] = 4
        with self.assertRaises(ValueError):
            runner.validate_index(index)

    def test_archive_size_bounds_rejected(self):
        for size in (True, 0, -1, 256 * 2**20 + 1):
            with self.subTest(size=size):
                index = self.valid()
                index["zip"]["bytes"] = size
                with self.assertRaises(ValueError):
                    runner.validate_index(index)

    def test_shard_size_bounds_rejected(self):
        for size in (True, 0, -1, runner.SHARD_BYTES + 1):
            with self.subTest(size=size):
                index = self.valid()
                index["shards"][0]["bytes"] = size
                with self.assertRaises(ValueError):
                    runner.validate_index(index)

    def test_archive_and_shard_hashes_must_be_sha256_hex(self):
        for target in ("zip", "shard"):
            for value in ("g" * 64, "", None, "0" * 63):
                with self.subTest(target=target, value=value):
                    index = self.valid()
                    row = index["zip"] if target == "zip" else index["shards"][0]
                    row["sha256"] = value
                    with self.assertRaises(ValueError):
                        runner.validate_index(index)


class ArtifactRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def make_archive(self, files=None, *, manifest=None, duplicate=None):
        files = files if files is not None else {"report.json": b'{"status":"failed"}'}
        rows = [{"file": name, "bytes": len(data), "sha256": digest(data)} for name, data in files.items()]
        archive = self.root / "result.zip"
        with ZipFile(archive, "w", ZIP_STORED) as result:
            for name, data in files.items():
                result.writestr(name, data)
            result.writestr("artifact-manifest.json", json.dumps(manifest if manifest is not None else {"files": rows}))
            if duplicate:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    result.writestr(duplicate, files[duplicate])
        return archive

    def reject(self, archive):
        destination = self.root / "recovered"
        with self.assertRaises(ValueError):
            runner.recover(archive, destination)
        self.assertFalse(destination.exists(), "Rejected packages must not create partial extraction")

    def test_failed_job_and_logs_are_recovered_without_success_claim(self):
        files = {"report.json": b'{"status":"failed","phase":"setup"}',
                 "logs/setup.log": b"diagnostic output\n", "imports.json": b"{}"}
        result = runner.recover(self.make_archive(files), self.root / "recovered")
        self.assertEqual(result["status"], "failed")
        for name, data in files.items():
            self.assertEqual((self.root / "recovered" / name).read_bytes(), data)

    def test_traversal_absolute_and_backslash_members_rejected(self):
        for name in ("../outside.log", "/tmp/outside.log", "logs/../../outside.log", "logs\\outside.log"):
            with self.subTest(name=name):
                archive = self.make_archive({"report.json": b'{"status":"failed"}', name: b"x"})
                self.reject(archive)
                self.assertFalse((self.root / "outside.log").exists())

    def test_normalized_log_alias_cannot_overwrite_a_distinct_member(self):
        for alias in ("logs/./train.log", "logs//train.log"):
            with self.subTest(alias=alias):
                self.reject(self.make_archive({"report.json": b'{"status":"failed"}',
                    "logs/train.log": b"first", alias: b"second"}))

    def test_unknown_artifact_rejected(self):
        self.reject(self.make_archive({"report.json": b'{"status":"failed"}', "secrets.txt": b"x"}))

    def test_duplicate_archive_members_rejected(self):
        self.reject(self.make_archive(duplicate="report.json"))

    def test_manifest_must_cover_exact_members(self):
        self.reject(self.make_archive(manifest={"files": []}))

    def test_content_hash_mismatch_rejected_before_any_write(self):
        self.reject(self.make_archive(manifest={"files": [{"file": "report.json", "bytes": 19,
                                                           "sha256": "0" * 64}]}))

    def test_missing_report_rejected_before_any_write(self):
        self.reject(self.make_archive({"logs/train.log": b"x"}))

    def test_completed_without_training_artifacts_is_not_success(self):
        self.reject(self.make_archive({"report.json": b'{"status":"completed"}'}))

    def completed_files(self):
        policy = b"fake opaque weights; loading is a separate offline acceptance check"
        fit = {"status": "completed_diagnostic", "checkpoint_reload_exact": True,
               "batch_size": 8, "checkpoint_sha256": digest(policy)}
        return {"report.json": b'{"status":"completed"}', "runtime.json": b"{}",
                "imports.json": b"{}", "microbenchmark/report.json": b"{}",
                "fit/report.json": json.dumps(fit).encode(), "fit/policy.pt": policy}

    def test_completed_package_preserves_verified_weight_bytes(self):
        files = self.completed_files()
        result = runner.recover(self.make_archive(files), self.root / "recovered")
        self.assertEqual(result["status"], "completed")
        self.assertEqual((self.root / "recovered/fit/policy.pt").read_bytes(), files["fit/policy.pt"])

    def test_archive_integrity_cannot_hide_invalid_fit_evidence(self):
        for key, value in (("status", "failed"), ("checkpoint_reload_exact", False),
                           ("batch_size", 4), ("checkpoint_sha256", "0" * 64)):
            with self.subTest(key=key):
                files = self.completed_files()
                fit = json.loads(files["fit/report.json"])
                fit[key] = value
                files["fit/report.json"] = json.dumps(fit).encode()
                self.reject(self.make_archive(files))

    def test_nonterminal_report_is_not_recovered_as_finished(self):
        self.reject(self.make_archive({"report.json": b'{"status":"running"}'}))

    def test_existing_destination_is_never_overwritten(self):
        destination = self.root / "recovered"
        destination.mkdir()
        protected = destination / "report.json"
        protected.write_bytes(b"existing protected content")
        with self.assertRaises(FileExistsError):
            runner.recover(self.make_archive(), destination)
        self.assertEqual(protected.read_bytes(), b"existing protected content")


class TransferRetryTests(unittest.TestCase):
    def run_case(self, failures, *, near_deadline=False, allocation_failure=False):
        """Exercise real main dispatch with fake CLI replies, never a subprocess."""
        saved_umask = os.umask(0o077)
        try:
            with tempfile.TemporaryDirectory() as temporary:
                base = Path(temporary)
                repo, home = base / "project", base / "home"
                root = repo / "experiments/colab-twin"
                for name in runner.SOURCES + runner.DATASETS:
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"small test-only input")
                commands, upload_bytes = [], []
                remaining = list(failures)
                clock = [0.]
                def fake_cli(argv, **kwargs):
                    command = argv[4]
                    commands.append((command, tuple(argv)))
                    value = {"exit_code": 0}
                    if command == "check-connection":
                        value.update(connection_verified=True, active_assignments=0)
                    elif command == "new" and allocation_failure:
                        value = {"exit_code": 1, "request_failure": {"type": "ConnectTimeout"}}
                    elif command == "upload":
                        upload_bytes.append(Path(argv[-2]).read_bytes())
                        if remaining:
                            value = {"exit_code": 1, "request_failure": remaining.pop(0)}
                            if near_deadline:
                                clock[0] = 30 * 60 - 149
                    elif command == "exec" and str(argv[-3]).endswith("launch_remote.py"):
                        # Stop after the upload under test. No remote worker is started.
                        value = {"exit_code": 1, "error_type": "IntentionalTestStop"}
                    elif command == "stop":
                        value["unassign_completed"] = True
                    return SimpleNamespace(returncode=value["exit_code"], stdout=json.dumps(value))
                with patch.object(runner, "ROOT", root), patch.object(runner, "REPO", repo), \
                        patch.object(runner.Path, "home", return_value=home), \
                        patch.object(runner.subprocess, "run", side_effect=fake_cli), \
                        patch.object(runner.time, "monotonic", side_effect=lambda: clock[0]), \
                        patch.object(runner.time, "sleep") as sleeps, redirect_stdout(StringIO()):
                    output = base / "result"
                    code = runner.main(["--output", str(output)])
                report = json.loads((output / "delivery.json").read_text())
                self.assertEqual(code, 1)  # Deliberately never reach actual training.
                self.assertTrue(report["runtime_released"])
                self.assertFalse(report["remote_worker_completed"])
                self.assertEqual(sum(command == "new" for command, _ in commands), 1)
                self.assertEqual(sum(command == "stop" for command, _ in commands), 1)
                return commands, upload_bytes, [item.args[0] for item in sleeps.call_args_list], report
        finally:
            os.umask(saved_umask)

    def test_transient_upload_retries_identical_path_and_bytes_then_stops_at_three(self):
        commands, data, sleeps, _ = self.run_case([
            {"type": "ConnectTimeout"}, {"status_code": 503}])
        uploads = [argv for command, argv in commands if command == "upload"]
        self.assertEqual(len(uploads), 3)
        self.assertEqual(uploads[0], uploads[1])
        self.assertEqual(uploads[1], uploads[2])
        self.assertEqual(data, [data[0]] * 3)
        self.assertEqual(sleeps, [5, 10])

    def test_third_transient_failure_stops_without_worker_launch(self):
        commands, data, sleeps, _ = self.run_case([{"type": "ReadTimeout"}] * 4)
        self.assertEqual(len(data), 3)
        self.assertEqual(sum(command == "exec" for command, _ in commands), 1)
        self.assertEqual(sleeps, [5, 10])

    def test_permanent_upload_failure_is_not_retried(self):
        _, data, sleeps, _ = self.run_case([{"status_code": 403}])
        self.assertEqual(len(data), 1)
        self.assertEqual(sleeps, [])

    def test_deadline_protects_cleanup_instead_of_retrying(self):
        _, data, sleeps, report = self.run_case([{"type": "ConnectionError"}], near_deadline=True)
        self.assertEqual(len(data), 1)
        self.assertEqual(sleeps, [])
        self.assertEqual(report["error_type"], "TimeoutError")

    def test_allocation_is_never_retried_even_for_transient_error(self):
        commands, data, sleeps, _ = self.run_case([], allocation_failure=True)
        self.assertEqual(data, [])
        self.assertEqual(sleeps, [])
        self.assertFalse(any(command == "exec" for command, _ in commands))


if __name__ == "__main__":
    unittest.main()
