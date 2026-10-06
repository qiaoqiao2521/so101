"""Offline worker lifecycle tests; no package installation, network or GPU."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import remote_vision_worker as worker_module

MISSING = object()


class RemoteVisionWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="so101-worker-test-")
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        (self.work / "project").mkdir()

    def test_initial_report_is_running_not_a_failure_terminal(self):
        worker = worker_module.Worker(self.work)
        saved = json.loads((worker.artifacts / "report.json").read_text())
        self.assertEqual(saved["status"], "running")
        self.assertEqual(saved["training_invocations"], 0)
        self.assertEqual(saved["physical_rollout"], "not_run")
        self.assertEqual(saved["offline_gate"], "not_run")

    def test_failed_job_recovers_only_manifested_artifacts_in_exact_shards(self):
        worker = worker_module.Worker(self.work)
        worker.report.update(status="failed", error_type="SyntheticFailure")
        fit = worker.artifacts / "fit"
        fit.mkdir()
        (fit / "report.json").write_text('{"status":"failed"}\n')
        # Cross the real 8 MiB boundary without requiring a torch checkpoint.
        (fit / "policy.pt").write_bytes(b"fixture-not-a-model\n" * 500000)
        (worker.artifacts / "private.txt").write_text("excluded synthetic private fixture")
        (self.work / "private-session.json").write_text('{"synthetic":true}')
        worker.package()

        recovery = self.work / "recovery"
        index = json.loads((recovery / "index.json").read_text())
        self.assertEqual(index["schema_version"], 1)
        self.assertEqual(index["shard_size_bytes"], 8 * 1024**2)
        self.assertGreater(len(index["shards"]), 1)
        self.assertEqual({p.name for p in recovery.iterdir()},
                         {s["file"] for s in index["shards"]} | {"index.json"})
        pieces = []
        for position, shard in enumerate(index["shards"]):
            data = (recovery / shard["file"]).read_bytes()
            self.assertEqual(len(data), shard["bytes"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), shard["sha256"])
            if position < len(index["shards"]) - 1:
                self.assertEqual(len(data), index["shard_size_bytes"])
            else:
                self.assertGreater(len(data), 0)
                self.assertLessEqual(len(data), index["shard_size_bytes"])
            pieces.append(data)
        joined = b"".join(pieces)
        self.assertEqual(joined, (self.work / "results.zip").read_bytes())
        self.assertEqual(len(joined), index["zip"]["bytes"])
        self.assertEqual(hashlib.sha256(joined).hexdigest(), index["zip"]["sha256"])
        with ZipFile(self.work / "results.zip") as package:
            files = json.loads(package.read("artifact-manifest.json"))["files"]
            self.assertEqual(set(package.namelist()),
                             {item["file"] for item in files} | {"artifact-manifest.json"})
            self.assertEqual({item["file"] for item in files},
                             {"report.json", "fit/report.json", "fit/policy.pt"})
            for item in files:
                data = package.read(item["file"])
                self.assertEqual(len(data), item["bytes"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"])
            saved = json.loads(package.read("report.json"))
            self.assertEqual(saved["status"], "failed")
            self.assertEqual(saved["error_type"], "SyntheticFailure")

    def test_timed_out_child_is_terminated_reaped_and_failure_is_saved(self):
        worker = worker_module.Worker(self.work)
        real_popen = subprocess.Popen
        children = []

        def capture_child(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            children.append(child)
            return child

        with patch.object(worker_module.subprocess, "Popen", side_effect=capture_child):
            with self.assertRaises(subprocess.TimeoutExpired):
                worker.phase("timeout_fixture",
                             [sys.executable, "-c", "import time; time.sleep(30)"], .1)
        self.assertEqual(len(children), 1)
        self.assertIsNotNone(children[0].poll(), "timed-out child must not remain alive")
        self.assertLess(children[0].returncode, 0, "child must be terminated by signal")
        saved = json.loads((worker.artifacts / "report.json").read_text())
        self.assertEqual(saved["phase"], "timeout_fixture")
        self.assertEqual(saved["phases"][0]["status"], "failed")
        self.assertEqual(saved["phases"][0]["error_type"], "TimeoutExpired")

    def test_child_keeps_home_and_excludes_credentials_and_python_overrides(self):
        original_home = os.environ.get("HOME")
        excluded = {"HF_TOKEN": "synthetic-not-a-credential", "GH_TOKEN": "synthetic",
                    "PYTHONPATH": "/synthetic/pythonpath", "PYTHONHOME": "/synthetic/pythonhome",
                    "UV_PYTHON": "/synthetic/python", "VIRTUAL_ENV": "/synthetic/venv",
                    "UV_PROJECT_ENVIRONMENT": "/synthetic/project-venv"}
        with patch.dict(os.environ, excluded | {"UV_SYSTEM_PYTHON": "1"}):
            worker = worker_module.Worker(self.work)
            program = ("import json,os; print(json.dumps({'home':os.environ.get('HOME'),"
                       "'present':[k for k in " + repr(list(excluded)) + " if k in os.environ],"
                       "'uv_system':os.environ.get('UV_SYSTEM_PYTHON'),"
                       "'backend':os.environ.get('MPLBACKEND')}))")
            worker.phase("environment_fixture", [sys.executable, "-c", program], 5)
        child = json.loads((worker.artifacts / "logs/01-environment_fixture.log").read_text())
        self.assertEqual(child["home"], original_home)
        self.assertEqual(child["present"], [])
        self.assertEqual(child["uv_system"], "0")
        self.assertEqual(child["backend"], "agg")

    def training_fixture(self, local_balance=MISSING, *, work=None):
        work = work or self.work
        project = work / "project"
        experiment = project / worker_module.EXPERIMENT
        experiment.mkdir(parents=True)
        sources = {}
        for name in worker_module.EXPECTED_SOURCES:
            path = experiment / name
            path.write_text("# offline source fixture\n")
            sources[name] = worker_module.digest(path)
        paths, hashes = [], []
        for index in range(4):
            path = project / f"fixture-{index}.h5"
            path.write_bytes(f"offline archive fixture {index}".encode())
            paths.append(path.name)
            hashes.append(worker_module.digest(path))
        job = {"max_steps": 5000, "max_wall_s": 600, "snapshot_step": 2115, "seed": 0,
               "source_sha256": sources, "dataset_paths": paths, "visual_dataset_sha256": hashes}
        if local_balance is not MISSING:
            job["local_balance"] = local_balance
        (work / "job.json").write_text(json.dumps(job))
        worker = worker_module.Worker(work)
        worker.python = Path(sys.executable)
        return worker

    def training_phase_stub(self, worker, sampler):
        calls = []

        def phase(name, argv, timeout, **kwargs):
            calls.append((name, list(argv), timeout))
            output = Path(argv[argv.index("--output") + 1])
            output.mkdir()
            if name == "microbenchmark":
                report = {"status": "passed", "source_sha256": worker.job["source_sha256"],
                          "visual_dataset_sha256": worker.job["visual_dataset_sha256"],
                          "selected_batch_size": 8,
                          "attempts": [{"batch_size": 8, "status": "passed", "steps": 5,
                                        "memory_after": {"peak_allocated_mib": 309,
                                                         "peak_reserved_mib": 332}}]}
            elif name == "fit":
                checkpoint = output / "policy.pt"
                checkpoint.write_bytes(b"offline checkpoint fixture")
                report = {"status": "completed_diagnostic", "checkpoint_reload_exact": True,
                          "batch_size": 8, "checkpoint_sha256": worker_module.digest(checkpoint),
                          "training_sampler": sampler, "training_steps": 5000,
                          "stop_reason": "step_limit"}
            else:
                self.fail("unexpected phase: " + name)
            (output / "report.json").write_text(json.dumps(report))

        return phase, calls

    def test_missing_or_false_local_balance_keeps_original_training_command(self):
        for mode in (MISSING, False):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(dir=self.work) as temp:
                worker = self.training_fixture(mode, work=Path(temp))
                worker.validate()
                phase, calls = self.training_phase_stub(worker, {"weight": 5})
                with patch.object(worker, "phase", side_effect=phase):
                    worker.train()
                self.assertEqual([call[0] for call in calls], ["microbenchmark", "fit"])
                command = calls[1][1]
                self.assertNotIn("--local-balance", command)
                for flag, value in (("--startup-weight", "5"), ("--max-wall-s", "600"),
                                    ("--max-steps", "5000"), ("--snapshot-step", "2115")):
                    self.assertEqual(command[command.index(flag) + 1], value)
                self.assertEqual(calls[1][2], 660)
                self.assertEqual(worker.report["training_invocations"], 1)
                self.assertFalse(worker.report["requested_local_balance"])
                self.assertEqual(worker.report["status"], "completed")

    def test_true_local_balance_is_forwarded_once_and_report_verified(self):
        worker = self.training_fixture(True)
        worker.validate()
        sampler = {"weight": 5, "local_balance": {"group_order": ["nonlocal", "startup", "settle"]}}
        phase, calls = self.training_phase_stub(worker, sampler)
        with patch.object(worker, "phase", side_effect=phase):
            worker.train()
        self.assertEqual([call[0] for call in calls], ["microbenchmark", "fit"])
        self.assertNotIn("--local-balance", calls[0][1])
        self.assertEqual(calls[1][1].count("--local-balance"), 1)
        self.assertEqual(worker.report["training_invocations"], 1)
        self.assertTrue(worker.report["requested_local_balance"])
        self.assertEqual(worker.report["status"], "completed")

    def test_non_boolean_local_balance_is_rejected_before_training(self):
        for mode in (0, 1, "true", "false", None, [], {}):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(dir=self.work) as temp:
                worker = self.training_fixture(mode, work=Path(temp))
                with patch.object(worker, "phase") as phase:
                    with self.assertRaisesRegex(worker_module.JobFailure, "job_local_balance_must_be_bool"):
                        worker.validate()
                phase.assert_not_called()
                self.assertEqual(worker.report["training_invocations"], 0)

    def test_fit_sampler_mode_mismatch_cannot_report_completion(self):
        cases = [
            (True, {"weight": 5}),
            (True, {"weight": 5, "local_balance": {}}),
            (True, {"weight": 5, "local_balance": False}),
            (False, {"weight": 5, "local_balance": {"group_order": ["nonlocal", "startup", "settle"]}}),
            (False, {"weight": 5, "local_balance": None}),
            (False, {"weight": 1}),
            (False, None),
        ]
        for mode, sampler in cases:
            with self.subTest(mode=mode, sampler=sampler), tempfile.TemporaryDirectory(dir=self.work) as temp:
                worker = self.training_fixture(mode, work=Path(temp))
                worker.validate()
                phase, calls = self.training_phase_stub(worker, sampler)
                with patch.object(worker, "phase", side_effect=phase):
                    with self.assertRaisesRegex(worker_module.JobFailure, "training_sampler_mode_mismatch"):
                        worker.train()
                self.assertNotEqual(worker.report["status"], "completed")
                self.assertEqual([call[0] for call in calls], ["microbenchmark", "fit"])
                self.assertEqual(worker.report["training_invocations"], 1)


if __name__ == "__main__":
    unittest.main()
