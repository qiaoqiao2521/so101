#!/usr/bin/env python3
"""Create a CPU Colab experiment, recover artifacts, and release the session."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZipFile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", default="so101-twin")
    parser.add_argument("--mode", choices=["planning", "baseline"], default="planning")
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    if not 1 <= args.episodes <= 100 or not 0 <= args.seed <= 0xFFFFFFFF - args.episodes:
        parser.error("episodes must be 1..100 and seed must leave room for all episode seeds")
    root = Path(__file__).resolve().parent
    output_root = root / "output"
    output_root.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix=f"{args.mode}-{datetime.now():%Y%m%d-%H%M%S}-", dir=output_root))
    subprocess.run([sys.executable, str(root / "prepare_bundle.py"), "--mode", args.mode,
                    "--episodes", str(args.episodes), "--seed", str(args.seed)], check=True)
    # Isolate this run's session metadata from the user's other Colab sessions.
    cache = Path.home() / ".cache" / "so101-colab"
    cache.mkdir(parents=True, exist_ok=True)
    state_dir = Path(tempfile.mkdtemp(prefix="run-", dir=cache))
    cli = ["colab", "--config", str(state_dir / "sessions.json")]
    def call(*argv: str) -> None:
        subprocess.run([*cli, *argv], check=True, cwd=root)
    released = False
    try:
        try:
            # new may allocate successfully before a later local step fails.
            call("new", "-s", args.session)
            call("install", "-s", args.session, "-r", str(root / "requirements.txt"))
            call("upload", "-s", args.session, str(root / "bundle.zip"), "/content/so101-twin-bundle.zip")
            call("exec", "-s", args.session, "--timeout", "900", "-f", str(root / "remote_bootstrap.py"))
            call("download", "-s", args.session, "/content/so101-colab-twin/results.zip", str(output / "results.zip"))
            with ZipFile(output / "results.zip") as archive:
                expected = {"trajectory.csv", "preview.png", "simulation.mp4", "report.json", "scene.xml"}
                if args.mode == "planning":
                    expected |= {"planning.json", "benchmark.json"}
                if set(archive.namelist()) != expected:
                    raise ValueError("Unexpected experiment result files")
                archive.extractall(output)
            report = json.loads((output / "report.json").read_text())
            validate_report(report, args.mode, args.episodes)
            print(f"Results recovered: {output}")
        finally:
            try:
                call("stop", "-s", args.session)
                released = True
            except BaseException:
                print(f"Cleanup failed. Session state preserved at {state_dir}.", file=sys.stderr)
                print(f"Release with: colab --config {state_dir / 'sessions.json'} stop -s {args.session}", file=sys.stderr)
                raise
    finally:
        if released:
            shutil.rmtree(state_dir)


def validate_report(report, mode, episodes):
    if mode == "baseline":
        passed = report.get("status") == "physics_baseline_passed" and report.get("frames") == 150
    else:
        execution = report.get("execution", {})
        passed = (report.get("status") == "motion_planning_passed"
                  and report.get("direct_path_blocked") is True
                  and report.get("path_validation", {}).get("valid") is True
                  and execution.get("passed") is True
                  and 0 <= execution.get("final_error_m", float("inf")) <= 0.01
                  and execution.get("invalid_samples") == 0
                  and report.get("benchmark_passed") == episodes
                  and report.get("benchmark_episodes") == episodes
                  and report.get("negative_cases", {}).get("passed") is True
                  and report.get("frames", 0) > 0)
    if not passed:
        raise RuntimeError("Experiment acceptance failed")


if __name__ == "__main__":
    main()
