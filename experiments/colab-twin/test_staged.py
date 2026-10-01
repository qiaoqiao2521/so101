"""Gate failure boundaries; physical solver/execution tests already exist."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import run_staged


class StagedAcceptanceTests(unittest.TestCase):
    def report(self):
        return {"stages": {name: {"status": "not_run"} for name in run_staged.STAGES}}

    def test_failed_previous_gate_never_invokes_next_solver(self):
        report = self.report()
        report["stages"]["dependencies"]["status"] = "failed"
        solver = Mock()
        with self.assertRaises(run_staged.StageFailure):
            run_staged.run_gate(report, "reset_step", solver)
        solver.assert_not_called()
        self.assertEqual(report["stages"]["reset_step"]["status"], "not_run")

    def test_solver_exception_keeps_following_execution_unobserved(self):
        report = self.report()
        for name in run_staged.STAGES[:2]:
            report["stages"][name]["status"] = "passed"
        with self.assertRaises(run_staged.StageFailure):
            run_staged.run_gate(report, "single_plan", Mock(side_effect=RuntimeError("no route")))
        self.assertEqual(report["stages"]["single_plan"]["status"], "failed")
        self.assertEqual(report["stages"]["servo_episode"]["status"], "not_run")

    def test_dependency_failure_persists_report_without_compiling_model(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            with patch.object(run_staged, "check_dependencies", side_effect=ImportError("native import unavailable")):
                result = run_staged.run(Path(directory) / "missing.xml", output)
            saved = json.loads((output / "report.json").read_text())
            self.assertEqual(saved, result)
            self.assertEqual(saved["failed_stage"], "dependencies")
            self.assertEqual(saved["stages"]["reset_step"]["status"], "not_run")
            self.assertFalse(saved["servo_episode_completed"])
            self.assertIsNone(saved["task_success"])
            self.assertFalse((output / "scene.xml").exists())


if __name__ == "__main__":
    unittest.main()
