"""Run one pinned GR00T/LIBERO episode on a temporary L4 Colab VM."""
from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parent
PUBLIC_FILES = ("common.py", "preflight.py", "run_rollout.py", "upstream.json", "remote_bootstrap.py")


class TerminationRequested(Exception):
    """Enter the normal failure/report/owned-runtime cleanup path on SIGTERM."""


def recover(archive: Path, destination: Path) -> dict:
    with ZipFile(archive) as package:
        names = set()
        for item in package.infolist():
            path = Path(item.filename)
            if (path.is_absolute() or ".." in path.parts or "\\" in item.filename
                    or item.filename in names or item.file_size > 512 * 1024**2):
                raise ValueError("Unsafe or unexpectedly large result archive")
            if path.suffix not in (".json", ".log", ".mp4"):
                raise ValueError("Result archive contains a non-result file")
            names.add(item.filename)
        if "artifact-manifest.json" not in names:
            raise ValueError("Result archive lacks its artifact manifest")
        package.extractall(destination)
    manifest = destination / "artifact-manifest.json"
    listed = set()
    for item in json.loads(manifest.read_text()):
        name = item["file"]
        path = destination / name
        if (name in listed or name == "artifact-manifest.json"
                or not path.resolve().is_relative_to(destination.resolve()) or not path.is_file()):
            raise ValueError("Artifact manifest path is invalid")
        listed.add(name)
        if path.stat().st_size != item["bytes"] or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Recovered artifact differs from its manifest")
    if listed != names - {"artifact-manifest.json"}:
        raise ValueError("Artifact manifest does not cover the exact result archive")
    return json.loads((destination / "report.json").read_text())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--colab-python", type=Path, default=Path.home() / ".local/share/uv/tools/google-colab-cli/bin/python")
    parser.add_argument("--gpu-minutes", type=int, default=45)
    args = parser.parse_args()
    if not 1 <= args.gpu_minutes <= 45:
        parser.error("gpu-minutes must be 1..45")
    from huggingface_hub import get_token
    token = get_token()
    if not token:
        raise RuntimeError("Log in with the official Hugging Face CLI first")
    os.umask(0o077)
    output = ROOT / "output/colab" / uuid.uuid4().hex
    output.mkdir(parents=True)
    session = "gr00t-libero-" + output.name[:12]
    state = output / "private-session"
    state.mkdir(mode=0o700)
    state_file = state / "sessions.json"
    state_file.write_text("{}")
    prefix = [str(args.colab_python), str(ROOT / "colab_safe_cli.py"), "--config", str(state_file)]
    report = {"kind": "gr00t_colab_delivery", "status": "failed", "session": session,
              "requested_gpu": "L4", "started_utc": datetime.now(timezone.utc).isoformat(),
              "runtime_released": False, "gr00t_rollout_completed": False, "task_success": None}
    owned = False
    last_phase = None
    deadline = time.monotonic() + args.gpu_minutes * 60

    def call(*argv, timeout=120, cleanup=False):
        if not cleanup:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Colab experiment deadline exceeded")
            timeout = min(timeout, remaining)
        try:
            result = subprocess.run([*prefix, *map(str, argv)], capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            # Never serialize TimeoutExpired.stdout/stderr: the native CLI may
            # contain transport credentials in an unfinished response.
            report["failed_colab_command"] = {"command": argv[0], "error_type": "TimeoutExpired",
                                               "category": "timeout", "request_failure": None}
            raise
        try:
            data = json.loads(result.stdout)
        except ValueError:
            data = {"exit_code": 1, "error_type": "MissingSafeCLIResult"}
        if not isinstance(data, dict) or type(data.get("exit_code")) is not int:
            data = {"exit_code": 1, "error_type": "InvalidSafeCLIResult"}
        if result.returncode or data["exit_code"]:
            report["failed_colab_command"] = {"command": argv[0], "error_type": data.get("error_type"),
                                               "category": data.get("error_category"),
                                               "request_failure": data.get("request_failure")}
            raise RuntimeError("Colab command failed")
        return data

    remote_token = "/content/.gr00t-private/hf-token"
    local_token = state / "hf-token"
    previous_sigterm_handler = signal.getsignal(signal.SIGTERM)
    sigterm_handler_installed = False

    def request_termination(signum, frame):
        raise TerminationRequested()

    try:
        signal.signal(signal.SIGTERM, request_termination)
        sigterm_handler_installed = True
        bundle = output / "experiment.zip"
        with ZipFile(bundle, "w") as archive:
            for name in PUBLIC_FILES:
                archive.write(ROOT / name, name)
        connection = call("check-connection", timeout=60)
        if connection.get("connection_verified") is not True:
            raise RuntimeError("Colab account connection not verified")
        report["colab_connection_verified"] = True
        print(json.dumps({"phase": "allocate_l4", "session": session}), flush=True)
        # new can allocate before a later local operation fails: always attempt stop.
        owned = True
        call("new", "-s", session, "--gpu", "L4", timeout=180)
        call("upload", "-s", session, bundle, "/content/gr00t-experiment.zip")
        prepare = output / "prepare-private.py"
        prepare.write_text("from pathlib import Path\nimport os\np=Path('/content/.gr00t-private')\np.mkdir(mode=0o700,exist_ok=True)\nos.chmod(p,0o700)\n")
        call("exec", "-s", session, "-f", prepare, "--timeout", "30")
        local_token.write_text(token)
        os.chmod(local_token, 0o600)
        del token
        try:
            call("upload", "-s", session, local_token, remote_token)
        finally:
            local_token.unlink(missing_ok=True)
        launch = output / "launch.py"
        launch.write_text(
            "from zipfile import ZipFile\nimport subprocess,sys,os\nfrom pathlib import Path\n"
            "os.chmod(" + repr(remote_token) + ",0o600)\n"
            "with ZipFile('/content/gr00t-experiment.zip') as z:\n"
            "    Path('/content/gr00t-bootstrap.py').write_bytes(z.read('remote_bootstrap.py'))\n"
            "subprocess.run([sys.executable,'/content/gr00t-bootstrap.py','--token-file',"
            + repr(remote_token) + ",'--timeout'," + repr(str(max(60, int(deadline-time.monotonic())-30))) + "],check=True)\n"
        )
        process = subprocess.Popen([*prefix, "exec", "-s", session, "-f", str(launch),
                                    "--timeout", str(args.gpu_minutes * 60)],
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        try:
            while process.poll() is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Colab experiment deadline exceeded")
                time.sleep(min(30, max(0, deadline - time.monotonic())))
                if time.monotonic() >= deadline:
                    raise TimeoutError("Colab experiment deadline exceeded")
                try:
                    call("download", "-s", session, "/content/gr00t-colab/artifacts/report.json", output / "live-report.json", timeout=45)
                    current = json.loads((output / "live-report.json").read_text())
                    phase = current.get("phase")
                    if phase != last_phase:
                        print(json.dumps({"phase": phase}), flush=True)
                        last_phase = phase
                except (RuntimeError, ValueError, FileNotFoundError, subprocess.TimeoutExpired) as error:
                    # A transient report-download failure does not decide the
                    # remote application's outcome. The shared deadline still
                    # bounds retries and the finally block releases this VM.
                    report["poll_failures"] = report.get("poll_failures", 0) + 1
                    report["last_poll_failure"] = report.pop("failed_colab_command", {
                        "command": "download", "error_type": type(error).__name__})
            process.communicate(timeout=10)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=10)
        call("download", "-s", session, "/content/gr00t-colab/results.zip", output / "results.zip")
        remote = recover(output / "results.zip", output / "results")
        report.update(bootstrap=remote)
        policy_reports = list((output / "results").rglob("report.json"))
        policy = [json.loads(path.read_text()) for path in policy_reports]
        policies = [item for item in policy if item.get("kind") == "gr00t_libero_official_rollout"]
        if len(policies) == 1:
            report.update(gr00t_rollout_completed=policies[0].get("gr00t_rollout_completed", False),
                          task_success=policies[0].get("task_success"))
        report["status"] = "completed" if remote.get("status") == "completed" and report["gr00t_rollout_completed"] else "failed"
    except Exception as error:
        report["error_type"] = type(error).__name__
    finally:
        # A second SIGTERM must not interrupt the already bounded stop/report
        # cleanup. SIGKILL cannot be handled; persistent owned identity remains
        # the recovery route for that case and for process/host crashes.
        if sigterm_handler_installed:
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        try:
            local_token.unlink(missing_ok=True)
            if owned:
                try:
                    stopped = call("stop", "-s", session, timeout=120, cleanup=True)
                    report["runtime_released"] = stopped["unassign_completed"]
                    if report["runtime_released"]:
                        shutil.rmtree(state)
                except Exception as error:
                    report["cleanup_error_type"] = type(error).__name__
            (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        finally:
            if sigterm_handler_installed:
                signal.signal(signal.SIGTERM, previous_sigterm_handler)
    print(json.dumps({key: report[key] for key in ("status", "runtime_released", "gr00t_rollout_completed", "task_success")}), flush=True)
    print("Report: " + str(output / "report.json"), flush=True)
    return 0 if report["status"] == "completed" and report["runtime_released"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
