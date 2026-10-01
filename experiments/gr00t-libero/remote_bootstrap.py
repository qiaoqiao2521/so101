#!/usr/bin/env python3
"""Single-use bootstrap for an already authorized, disposable Colab GPU VM.

Creates no runtime and changes no host/account settings. Invoke only on Colab:
python3 remote_bootstrap.py --token-file /content/<private-temporary-file>
The experiment bundle is /content/gr00t-experiment.zip; results are returned in
/content/gr00t-colab/results.zip, including failures after workspace creation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
import subprocess
import sys
import time
from zipfile import ZipFile, ZIP_STORED


WORK = Path("/content/gr00t-colab")
BUNDLE = Path("/content/gr00t-experiment.zip")
GR00T_REVISION = "51d4c89f72fda44cbf77285c6a8114b52676b8a1"
LIBERO_REVISION = "8f1084e3132a39270c3a13ebe37270a43ece2a01"
CHECKPOINT_REVISION = "2ea293aa20ba7cf5bbf3ba17a5fbcb1a01cbfe21"
UV_VERSION = "0.11.15"
ALLOWED_BUNDLE_FILES = {
    ".gitignore", "README.md", "upstream.json", "requirements-cpu.txt",
    "common.py", "setup_cpu.py", "preflight.py", "smoke_environment.py",
    "run_rollout.py", "test_reports.py", "remote_bootstrap.py",
}
REQUIRED_BUNDLE_FILES = {"common.py", "preflight.py", "run_rollout.py", "upstream.json"}


class PhaseFailure(RuntimeError):
    def __init__(self, kind: str, code: int | None = None):
        super().__init__(kind)
        self.kind, self.code = kind, code


def redact(text: str, token: str = "") -> str:
    if token:
        text = text.replace(token, "[REDACTED]")
    text = re.sub(r"hf_[A-Za-z0-9]{16,}", "[REDACTED]", text)
    return re.sub(r"(?i)(authorization\s*[:=]\s*(?:bearer\s+)?)[^\s,}'\"]+",
                  r"\1[REDACTED]", text)


def consume_token(path: Path) -> str:
    """Consume only the explicitly supplied temporary token, then unlink it."""
    descriptor = None
    try:
        if not path.is_absolute():
            raise PhaseFailure("token_file_must_be_absolute")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077
                or info.st_uid != os.geteuid() or not 1 <= info.st_size <= 4096):
            raise PhaseFailure("token_file_requires_private_owned_regular_file")
        raw = os.read(descriptor, 4097)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        path.unlink(missing_ok=True)
    try:
        token = raw.decode("ascii").strip()
    except UnicodeDecodeError:
        raise PhaseFailure("invalid_token_file") from None
    # The official OAuth issuer can use a different token alphabet/prefix.
    # Validate transport safety, never infer authorization from token syntax.
    if not token or len(token) > 4096 or any(not 33 <= ord(c) <= 126 for c in token):
        raise PhaseFailure("invalid_token_file")
    return token


def unpack_bundle(destination: Path) -> dict:
    destination.mkdir()
    names = set()
    with ZipFile(BUNDLE) as archive:
        for item in archive.infolist():
            if item.is_dir():
                continue
            relative = PurePosixPath(item.filename)
            if relative.is_absolute() or ".." in relative.parts or "\\" in item.filename:
                raise PhaseFailure("unsafe_bundle_path")
            parts = relative.parts
            if len(parts) == 3 and parts[:2] == ("experiments", "gr00t-libero"):
                parts = parts[2:]
            if (len(parts) != 1 or parts[0] not in ALLOWED_BUNDLE_FILES
                    or parts[0] in names or stat.S_ISLNK(item.external_attr >> 16)
                    or item.file_size > 1024 * 1024):
                raise PhaseFailure("unexpected_bundle_member")
            names.add(parts[0])
            (destination / parts[0]).write_bytes(archive.read(item))
    if not REQUIRED_BUNDLE_FILES <= names:
        raise PhaseFailure("experiment_bundle_incomplete")
    lock = json.loads((destination / "upstream.json").read_text())
    expected = {
        "gr00t_repository": "https://github.com/NVIDIA/Isaac-GR00T",
        "gr00t_revision": GR00T_REVISION,
        "libero_repository": "https://github.com/Lifelong-Robot-Learning/LIBERO",
        "libero_revision": LIBERO_REVISION,
        "checkpoint_repository": "nvidia/GR00T-N1.7-LIBERO",
        "checkpoint_revision": CHECKPOINT_REVISION,
        "checkpoint_subdirectory": "libero_10",
        "backbone_repository": "nvidia/Cosmos-Reason2-2B",
        "backbone_revision_observed": "9ce19a195e423419c349abfc86fd07178b230561",
        "default_task": "KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it",
    }
    if any(lock.get(key) != value for key, value in expected.items()):
        raise PhaseFailure("upstream_lock_mismatch")
    expected_include = {
        "libero_10/config.json", "libero_10/embodiment_id.json",
        "libero_10/model-*.safetensors", "libero_10/model.safetensors.index.json",
        "libero_10/processor_config.json", "libero_10/statistics.json",
    }
    if set(lock.get("checkpoint_include", [])) != expected_include:
        raise PhaseFailure("checkpoint_allowlist_mismatch")
    return lock


def uv_binary(tools: Path) -> Path:
    """Use the wheel's standalone executable without venv/ensurepip."""
    binary = tools / "bin" / "uv"
    if not binary.is_file() or binary.is_symlink() or not os.access(binary, os.X_OK):
        raise PhaseFailure("uv_native_binary_missing_or_not_executable")
    return binary


class Bootstrap:
    def __init__(self, token: str, timeout: int = 2700):
        self.token = token
        self.start = time.monotonic()
        self.deadline = self.start + timeout
        self.artifacts = WORK / "artifacts"
        self.artifacts.mkdir()
        self.logs = self.artifacts / "bootstrap-logs"
        self.logs.mkdir()
        self.report = {
            "schema_version": 1, "kind": "gr00t_colab_bootstrap", "status": "failed",
            "phase": "prepare", "phases": [], "deadline_seconds": timeout,
            "gr00t_rollout_completed": False, "task_success": None,
            "n_envs": 1, "n_episodes": 1, "seed": 0,
            "max_episode_steps": 720, "execution_horizon": 8,
            "gr00t_revision": GR00T_REVISION, "libero_revision": LIBERO_REVISION,
            "checkpoint_revision": CHECKPOINT_REVISION, "uv_version": UV_VERSION,
            "hardware_connected": False,
        }
        self.env = os.environ.copy()
        removed_uv = [key for key in ("UV_SYSTEM_PYTHON", "UV_PYTHON",
                                      "UV_PROJECT_ENVIRONMENT", "VIRTUAL_ENV")
                      if key in self.env]
        self.report["inherited_uv_settings_removed"] = removed_uv
        for key in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HF_DEBUG", *removed_uv):
            self.env.pop(key, None)
        self.env.update(
            UV_SYSTEM_PYTHON="0",
            GIT_LFS_SKIP_SMUDGE="1", GIT_TERMINAL_PROMPT="0",
            DEBIAN_FRONTEND="noninteractive", PIP_DISABLE_PIP_VERSION_CHECK="1",
            MUJOCO_GL="egl", PYOPENGL_PLATFORM="egl", DS_BUILD_OPS="0",
            HF_HOME=str(WORK / "hf-home"), HF_HUB_VERBOSITY="error",
            HF_HUB_DISABLE_PROGRESS_BARS="1", TRANSFORMERS_VERBOSITY="error",
        )
        self.save()

    def save(self) -> None:
        self.report["elapsed_wall_s"] = round(time.monotonic() - self.start, 3)
        (self.artifacts / "report.json").write_text(
            redact(json.dumps(self.report, indent=2) + "\n", self.token))

    def phase(self, name: str, argv: list[str], *, timeout: int,
              cwd: Path | None = None, with_token: bool = False) -> None:
        self.report["phase"] = name
        record = {"phase": name, "status": "running"}
        self.report["phases"].append(record)
        self.save()
        print(json.dumps({"phase": name, "status": "started"}), flush=True)
        remaining = self.deadline - time.monotonic() - 45
        if remaining <= 0:
            raise PhaseFailure("total_deadline_exhausted")
        env = self.env.copy()
        if with_token:
            env["HF_TOKEN"] = self.token
        log = self.logs / f"{len(self.report['phases']):02d}-{name}.log"
        started = time.monotonic()
        try:
            with log.open("w") as stream:
                process = subprocess.Popen(argv, cwd=cwd or WORK, env=env, stdout=stream,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    code = process.wait(timeout=min(timeout, remaining))
                except BaseException as error:
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        process.wait(timeout=5)
                    if isinstance(error, subprocess.TimeoutExpired):
                        raise PhaseFailure("subprocess_timeout") from None
                    raise
            record.update(status="passed" if code == 0 else "failed", exit_code=code)
            if code:
                raise PhaseFailure("subprocess_nonzero", code)
        except BaseException:
            record["status"] = "failed"
            raise
        finally:
            record["elapsed_wall_s"] = round(time.monotonic() - started, 3)
            if log.is_file():
                log.write_text(redact(log.read_text(errors="replace"), self.token))
            self.save()
            print(json.dumps({"phase": name, "status": record["status"],
                              "elapsed_wall_s": record["elapsed_wall_s"]}), flush=True)

    def run(self) -> None:
        experiment = WORK / "experiment"
        lock = unpack_bundle(experiment)
        self.report["upstream"] = lock
        self.report["bundle_sha256"] = hashlib.sha256(BUNDLE.read_bytes()).hexdigest()
        # The official setup script contains rm -rf $HOME/.libero. Never run it
        # on an existing user configuration, even if it is an empty directory/link.
        libero_config = Path.home() / ".libero"
        if os.path.lexists(libero_config):
            raise PhaseFailure("existing_home_libero_configuration_refused")
        diagnostic = (
            "import json,platform,shutil,sys; from pathlib import Path; "
            "release={}; "
            "release=dict(line.split('=',1) for line in Path('/etc/os-release').read_text().splitlines() "
            "if '=' in line); disk=shutil.disk_usage('/content'); "
            "print(json.dumps({'python_version':sys.version,'python_executable':sys.executable,"
            "'platform':platform.platform(),'os':{k:release.get(k,'').strip(chr(34)) "
            "for k in ('ID','VERSION_ID','PRETTY_NAME')},"
            "'disk_total_bytes':disk.total,'disk_free_bytes':disk.free}))"
        )
        self.phase("runtime_diagnostics", [sys.executable, "-c", diagnostic], timeout=30)
        self.phase("gpu_inventory", ["nvidia-smi", "--query-gpu=name,memory.total",
                                     "--format=csv,noheader"], timeout=30)
        self.phase("apt_update", ["apt-get", "update", "-qq"], timeout=180)
        self.phase("system_dependencies", ["apt-get", "install", "-y", "-qq",
                   "git", "git-lfs", "ffmpeg", "libegl1-mesa-dev",
                   "libglu1-mesa", "libgl1-mesa-dri"], timeout=300)
        self.phase("ffmpeg_compatibility", [sys.executable, "-c",
                   "import re,subprocess; v=subprocess.check_output(['ffmpeg','-version'],"
                   "text=True,timeout=15); m=re.search(r'ffmpeg version (\\d+)',v); "
                   "assert m and 4<=int(m[1])<=7,'FFmpeg 4-7 required'; print(v.splitlines()[0])"], timeout=30)
        tools = WORK / "bootstrap-tools"
        self.phase("uv_install", [sys.executable, "-m", "pip", "install", "--no-input",
                   "--no-deps", "--target", str(tools), f"uv=={UV_VERSION}"], timeout=180)
        uv = uv_binary(tools)
        self.env["PATH"] = str(uv.parent) + os.pathsep + self.env.get("PATH", "")
        self.phase("uv_version", [str(uv), "--version"], timeout=30)
        upstream = WORK / "Isaac-GR00T"
        self.phase("gr00t_clone", ["git", "clone", "--filter=blob:none", "--no-checkout",
                   lock["gr00t_repository"], str(upstream)], timeout=300)
        self.phase("gr00t_checkout", ["git", "checkout", "--detach", GR00T_REVISION],
                   cwd=upstream, timeout=300)
        self.phase("libero_submodule", ["git", "submodule", "update", "--init",
                   "external_dependencies/LIBERO"], cwd=upstream, timeout=600)
        self.phase("gr00t_uv_frozen", [str(uv), "sync", "--frozen", "--python", "3.12"],
                   cwd=upstream, timeout=900)
        if os.path.lexists(libero_config):
            raise PhaseFailure("existing_home_libero_configuration_refused")
        self.phase("official_libero_setup", ["bash", "gr00t/eval/sim/LIBERO/setup_libero.sh"],
                   cwd=upstream, timeout=900)
        self.phase("preflight", [sys.executable, str(experiment / "preflight.py"),
                   "--gr00t-root", str(upstream), "--output", str(self.artifacts / "preflight.json")],
                   timeout=90)
        # Only this child receives HF_TOKEN. No token is persisted or placed in
        # arguments. The runner delegates downloads to the official hf CLI.
        self.phase("model_download_and_rollout", [sys.executable, str(experiment / "run_rollout.py"),
                   "--gr00t-root", str(upstream), "--work-dir", str(WORK / "model-cache"),
                   "--output-dir", str(self.artifacts / "rollout"), "--download-models",
                   "--seed", "0", "--startup-timeout", "240", "--timeout", "900"],
                   timeout=1800, with_token=True)
        reports = list((self.artifacts / "rollout").glob("*/report.json"))
        if len(reports) != 1:
            raise PhaseFailure("exactly_one_rollout_report_required")
        result = json.loads(reports[0].read_text())
        if (result.get("status") != "completed" or result.get("gr00t_rollout_completed") is not True
                or type(result.get("task_success")) is not bool or not result.get("videos")):
            raise PhaseFailure("rollout_or_video_incomplete")
        for index, video in enumerate(result["videos"], 1):
            path = reports[0].parent / video["file"]
            if (not path.resolve().is_relative_to(reports[0].parent.resolve())
                    or path.is_symlink() or not path.is_file() or video.get("bytes", 0) <= 0
                    or path.stat().st_size != video["bytes"]
                    or hashlib.sha256(path.read_bytes()).hexdigest() != video["sha256"]):
                raise PhaseFailure("rollout_video_provenance_invalid")
            self.phase(f"video_decode_{index}", ["ffmpeg", "-v", "error", "-xerror",
                       "-err_detect", "explode", "-i", str(path), "-map", "0:v:0",
                       "-f", "null", "-"], timeout=120)
        self.report.update(status="completed", phase="completed", gr00t_rollout_completed=True,
                           task_success=result["task_success"],
                           rollout_report=reports[0].relative_to(self.artifacts).as_posix())

    def package(self) -> Path:
        """Allowlist reports/logs/video; never traverse model/HF/cache directories."""
        self.save()
        included = []
        for path in sorted(self.artifacts.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            if path.suffix not in {".json", ".log", ".mp4"}:
                continue
            if path.suffix in {".json", ".log"}:
                path.write_text(redact(path.read_text(errors="replace"), self.token))
            included.append(path)
        manifest = [{"file": path.relative_to(self.artifacts).as_posix(),
                     "bytes": path.stat().st_size,
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                    for path in included]
        manifest_path = self.artifacts / "artifact-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        archive_path = WORK / "results.zip"
        with ZipFile(archive_path, "w", ZIP_STORED) as archive:
            for path in [*included, manifest_path]:
                archive.write(path, path.relative_to(self.artifacts).as_posix())
        return archive_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=2700,
                        help="Total wall-clock budget in seconds, 60..2700")
    args = parser.parse_args()
    if not 60 <= args.timeout <= 2700:
        parser.error("timeout must be in [60, 2700]")
    os.umask(0o077)
    # Check the Colab filesystem boundary before reading an authorized token.
    if not Path("/content").is_dir() or WORK.exists() or WORK.is_symlink():
        print(json.dumps({"status": "failed", "phase": "prepare",
                          "failure_type": "requires_fresh_colab_workspace"}), flush=True)
        return 2
    WORK.mkdir()
    boot = None
    try:
        token = consume_token(args.token_file)
        boot = Bootstrap(token, args.timeout)
        boot.run()
        code = 0
    except BaseException as error:
        code = 1
        failure = {"type": type(error).__name__,
                   "kind": error.kind if isinstance(error, PhaseFailure) else "bootstrap_exception"}
        if isinstance(error, PhaseFailure) and error.code is not None:
            failure["exit_code"] = error.code
        if boot is None:
            boot = Bootstrap("", args.timeout)
        boot.report.update(status="failed", failure=failure)
    finally:
        if boot is not None:
            try:
                archive = boot.package()
                print(json.dumps({"status": boot.report["status"], "phase": boot.report["phase"],
                      "failure": boot.report.get("failure"),
                      "gr00t_rollout_completed": boot.report["gr00t_rollout_completed"],
                      "task_success": boot.report["task_success"],
                      "results_zip": str(archive)}), flush=True)
            except BaseException as error:
                print(json.dumps({"status": "failed", "phase": "package",
                                  "failure_type": type(error).__name__}), flush=True)
                code = 1
    return code


if __name__ == "__main__":
    raise SystemExit(main())
