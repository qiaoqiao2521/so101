"""CPU CLI budget contracts; no dataset, model, optimizer or CUDA is invoked."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import DEFAULT, patch

import run_vision_learning as runner


class VisionFitBudgetTests(unittest.TestCase):
    def invoke(self, stage, extra=(), expected_error=None):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "new-parent" / "output"
            argv = [stage, "--dataset", "unused.h5", "--output", str(output)]
            if stage == "fit":
                argv += ["--resource-report", "unused.json", "--camera-reviewed"]
            if stage == "evaluate":
                argv += ["--checkpoint", "unused.pt"]
            argv += list(extra)
            with patch.multiple(runner, export=DEFAULT, microbenchmark=DEFAULT,
                                fit=DEFAULT, evaluate=DEFAULT) as stages:
                for function in stages.values():
                    function.return_value = {"status": "completed_diagnostic"}
                errors = StringIO()
                with redirect_stderr(errors), redirect_stdout(StringIO()):
                    if expected_error is not None:
                        with self.assertRaises(SystemExit) as raised:
                            runner.main(argv)
                        self.assertEqual(raised.exception.code, 2)
                        self.assertIn(expected_error, errors.getvalue())
                        self.assertFalse(output.parent.exists())
                        for function in stages.values():
                            function.assert_not_called()
                        return None
                    self.assertEqual(runner.main(argv), 0)
                stages[stage].assert_called_once()
                for name, function in stages.items():
                    if name != stage:
                        function.assert_not_called()
                self.assertTrue(output.is_dir())
                return stages[stage].call_args.args[0]

    def test_default_fit_remains_120_seconds_5000_steps_200_epochs(self):
        args = self.invoke("fit")
        self.assertEqual((args.max_wall_s, args.max_steps, args.max_epochs), (120., 5000, 200))
        self.assertFalse(args.extended_fit_budget)

    def test_default_accepts_120_but_rejects_121_before_dispatch(self):
        self.assertEqual(self.invoke("fit", ["--max-wall-s", "120"]).max_wall_s, 120.)
        self.invoke("fit", ["--max-wall-s", "121"], "(0,120]")

    def test_extended_fit_accepts_exactly_600_and_preserves_step_budget(self):
        args = self.invoke("fit", ["--extended-fit-budget", "--max-wall-s", "600"])
        self.assertTrue(args.extended_fit_budget)
        self.assertEqual((args.max_wall_s, args.max_steps, args.max_epochs), (600., 5000, 200))

    def test_extension_flag_alone_does_not_increase_requested_wall_time(self):
        self.assertEqual(self.invoke("fit", ["--extended-fit-budget"]).max_wall_s, 120.)

    def test_extended_fit_rejects_601_before_dispatch(self):
        self.invoke("fit", ["--extended-fit-budget", "--max-wall-s", "601"], "(0,600]")

    def test_extension_is_rejected_for_every_nonfit_stage_even_at_120(self):
        for stage in ("export", "microbenchmark", "evaluate"):
            with self.subTest(stage=stage):
                self.invoke(stage, ["--extended-fit-budget"], "only allowed for fit")

    def test_nonfit_wall_limits_are_unchanged(self):
        for stage in ("export", "microbenchmark", "evaluate"):
            with self.subTest(stage=stage):
                self.assertEqual(self.invoke(stage).max_wall_s, 120.)
                self.invoke(stage, ["--max-wall-s", "121"], "(0,120]")

    def test_nonfinite_and_nonpositive_wall_times_are_rejected(self):
        for extension, limit in (([], 120), (["--extended-fit-budget"], 600)):
            for value in ("nan", "inf", "-inf", "0", "-1"):
                with self.subTest(extension=extension, value=value):
                    self.invoke("fit", extension + [f"--max-wall-s={value}"], f"(0,{limit}]")

    def test_extension_does_not_allow_more_than_5000_steps_or_200_epochs(self):
        for extra in (["--max-steps", "5001"], ["--max-epochs", "201"]):
            with self.subTest(extra=extra):
                self.invoke("fit", ["--extended-fit-budget"] + extra, "training budgets exceed")


if __name__ == "__main__":
    unittest.main()
