#!/usr/bin/env python3
"""Create a CPU Colab experiment, recover artifacts, and release the session."""
import argparse
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
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = root / "output"
    output.mkdir(exist_ok=True)
    subprocess.run([sys.executable, str(root / "prepare_bundle.py")], check=True)
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
            call("exec", "-s", args.session, "--timeout", "240", "-f", str(root / "remote_bootstrap.py"))
            call("download", "-s", args.session, "/content/so101-colab-twin/results.zip", str(output / "results.zip"))
            with ZipFile(output / "results.zip") as archive:
                expected = {"trajectory.csv", "preview.png", "simulation.mp4", "report.json", "scene.xml"}
                if set(archive.namelist()) != expected:
                    raise ValueError("Unexpected experiment result files")
                archive.extractall(output)
            report = json.loads((output / "report.json").read_text())
            if report["status"] != "physics_baseline_passed" or report["frames"] != 150:
                raise RuntimeError("Experiment acceptance failed")
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


if __name__ == "__main__":
    main()
