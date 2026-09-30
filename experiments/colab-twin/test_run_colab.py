"""Failure-path tests for releasing this run's cloud resources."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import run_colab


class LifecycleTests(unittest.TestCase):
    def exercise(self, *, new_fails=False, exec_fails=False, stop_fails=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            calls = []
            state_paths = []
            def fake_run(argv, **kwargs):
                if argv[0] != "colab":
                    return subprocess.CompletedProcess(argv, 0)
                command = argv[3]
                calls.append(command)
                state = Path(argv[2])
                state_paths.append(state.parent)
                if command == "new":
                    state.write_text('{}\n')
                    if new_fails:
                        raise subprocess.CalledProcessError(1, argv)
                if command == "exec" and exec_fails:
                    raise subprocess.CalledProcessError(1, argv)
                if command == "download":
                    with ZipFile(argv[-1], "w") as archive:
                        for name in ["trajectory.csv", "preview.png", "simulation.mp4", "scene.xml"]:
                            archive.writestr(name, "fixture")
                        archive.writestr("report.json", json.dumps({"status": "physics_baseline_passed", "frames": 150}))
                if command == "stop" and stop_fails:
                    raise subprocess.CalledProcessError(1, argv)
                return subprocess.CompletedProcess(argv, 0)
            with patch.object(run_colab, "__file__", str(root / "run_colab.py")), \
                 patch.object(Path, "home", return_value=root), \
                 patch.object(run_colab.subprocess, "run", side_effect=fake_run), \
                 patch("sys.argv", ["run_colab.py", "--session", "test-session", "--mode", "baseline"]):
                if new_fails or exec_fails or stop_fails:
                    with self.assertRaises(subprocess.CalledProcessError):
                        run_colab.main()
                else:
                    run_colab.main()
            self.assertEqual(calls.count("stop"), 1)
            self.assertEqual(state_paths[0].exists(), stop_fails)
            return calls

    def test_success_releases_and_removes_state(self):
        self.assertIn("download", self.exercise())

    def test_failed_creation_after_allocation_still_releases(self):
        self.assertEqual(self.exercise(new_fails=True), ["new", "stop"])

    def test_execution_failure_still_releases(self):
        self.assertNotIn("download", self.exercise(exec_fails=True))

    def test_release_failure_preserves_recovery_state(self):
        self.exercise(stop_fails=True)

    def test_planning_acceptance_rejects_tracking_failure(self):
        with self.assertRaises(RuntimeError):
            run_colab.validate_report({"status": "motion_planning_passed", "frames": 100}, "planning", 20)

    def test_seed_overflow_rejected_before_allocating(self):
        with patch("sys.argv", ["run_colab.py", "--seed", str(0xFFFFFFFF)]), \
             patch.object(run_colab.subprocess, "run") as command:
            with self.assertRaises(SystemExit):
                run_colab.main()
            command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
