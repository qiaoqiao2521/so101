"""One bounded, credential-free visual ACT training job on an owned Colab VM.

The launcher owns allocation, input extraction, recovery and unassignment. This
worker consumes work-dir/project and work-dir/job.json; it never calls Colab APIs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time
from zipfile import ZIP_STORED, ZipFile


UV_VERSION = "0.11.15"
TOTAL_SECONDS = 1200
SHARD_BYTES = 8 * 1024**2
EXPERIMENT = Path("experiments/colab-twin")
EXPECTED_SOURCES = {"learning_vision.py", "run_vision_learning.py"}


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            value.update(block)
    return value.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    partial.replace(path)


class JobFailure(RuntimeError):
    pass


def terminate_requested(signum, frame):
    raise JobFailure("termination_requested")


class Worker:
    def __init__(self, work):
        self.work = work
        self.project = work / "project"
        self.artifacts = work / "artifacts"
        self.artifacts.mkdir(exist_ok=False)
        self.logs = self.artifacts / "logs"
        self.logs.mkdir()
        self.start = time.monotonic()
        self.deadline = self.start + TOTAL_SECONDS
        self.allowed = {"report.json", "runtime.json", "imports.json",
                        "microbenchmark/report.json", "fit/report.json",
                        "fit/policy.pt", "fit/policy-step-2115.pt"}
        self.report = {"schema_version": 1, "kind": "so101_colab_visual_training",
                       "status": "running", "phase": "validate", "phases": [],
                       "total_budget_s": TOTAL_SECONDS, "training_invocations": 0,
                       "physical_rollout": "not_run", "offline_gate": "not_run",
                       "task_acceptance": "not_run", "hardware_connected": False}
        # Do not copy account credentials or notebook environment overrides into
        # install/training children. Keep HOME unchanged; use task-specific caches.
        self.env = {name: os.environ[name] for name in
                    ("PATH", "HOME", "LD_LIBRARY_PATH", "CUDA_VISIBLE_DEVICES", "SSL_CERT_FILE",
                     "REQUESTS_CA_BUNDLE", "LANG", "LC_ALL") if name in os.environ}
        self.env.update(UV_CACHE_DIR=str(work / "uv-cache"),
                        UV_PYTHON_INSTALL_DIR=str(work / "uv-python"), UV_SYSTEM_PYTHON="0",
                        HF_HOME=str(work / "hf-cache"), HF_HUB_OFFLINE="1",
                        GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1",
                        GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1",
                        PIP_DISABLE_PIP_VERSION_CHECK="1", PYTHONUNBUFFERED="1",
                        MPLBACKEND="agg", MUJOCO_GL="egl", PYOPENGL_PLATFORM="egl")
        self.save()

    def save(self):
        self.report["elapsed_wall_s"] = round(time.monotonic() - self.start, 3)
        atomic_json(self.artifacts / "report.json", self.report)

    def phase(self, name, argv, timeout, *, cwd=None):
        remaining = self.deadline - time.monotonic() - 30
        if remaining <= 0:
            raise JobFailure("total_deadline_exhausted")
        self.report["phase"] = name
        entry = {"phase": name, "status": "running", "timeout_s": min(timeout, remaining)}
        self.report["phases"].append(entry)
        self.save()
        relative = f"logs/{len(self.report['phases']):02d}-{name}.log"
        self.allowed.add(relative)
        started = time.monotonic()
        process = None
        try:
            with (self.artifacts / relative).open("wb") as stream:
                process = subprocess.Popen(list(map(str, argv)), cwd=cwd or self.project,
                                           env=self.env, stdin=subprocess.DEVNULL,
                                           stdout=stream, stderr=subprocess.STDOUT,
                                           start_new_session=True)
                try:
                    code = process.wait(timeout=entry["timeout_s"])
                except BaseException:
                    if process.poll() is None:
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
                    raise
            entry["exit_code"] = code
            if code != 0:
                raise JobFailure("phase_nonzero:" + name)
            entry["status"] = "passed"
        except BaseException as error:
            entry.update(status="failed", error_type=type(error).__name__)
            raise
        finally:
            entry["elapsed_s"] = round(time.monotonic() - started, 3)
            self.save()

    def validate(self):
        job = json.loads((self.work / "job.json").read_text())
        local_balance = job.get("local_balance", False)
        if type(local_balance) is not bool:
            raise JobFailure("job_local_balance_must_be_bool")
        expected = {"max_steps": 5000, "max_wall_s": 600, "snapshot_step": 2115, "seed": 0}
        if any(type(job.get(key)) is not int or job[key] != value for key, value in expected.items()):
            raise JobFailure("job_budget_or_seed_mismatch")
        sources = job.get("source_sha256")
        if not isinstance(sources, dict) or set(sources) != EXPECTED_SOURCES:
            raise JobFailure("unexpected_source_manifest")
        for name, expected_sha in sources.items():
            path = self.project / EXPERIMENT / name
            if path.is_symlink() or digest(path) != expected_sha:
                raise JobFailure("source_hash_mismatch:" + name)
        paths, hashes = job.get("dataset_paths"), job.get("visual_dataset_sha256")
        if not isinstance(paths, list) or len(paths) != 4 or len(set(paths)) != 4:
            raise JobFailure("need_four_unique_datasets")
        if not isinstance(hashes, list) or len(hashes) != 4:
            raise JobFailure("need_four_visual_hashes")
        self.datasets = []
        for name, expected_sha in zip(paths, hashes):
            path = Path(name)
            resolved = (self.project / path).resolve()
            if (path.is_absolute() or ".." in path.parts or "\\" in name
                    or not resolved.is_relative_to(self.project.resolve())
                    or not resolved.is_file() or (self.project / path).is_symlink()
                    or digest(resolved) != expected_sha):
                raise JobFailure("dataset_path_or_hash_mismatch")
            self.datasets.append(resolved)
        self.job = job
        self.report.update(job_sha256=digest(self.work / "job.json"),
                           source_sha256=sources, visual_dataset_sha256=hashes,
                           dataset_paths=paths, budget=expected,
                           requested_local_balance=local_balance,
                           worker_sha256=digest(Path(__file__)))
        self.save()

    def setup(self):
        atomic_json(self.artifacts / "runtime.json", {
            "platform": platform.platform(), "bootstrap_python": sys.version,
            "bootstrap_executable": sys.executable,
            "free_disk_bytes": shutil.disk_usage(self.work).free,
            "source_sha256": self.report["source_sha256"],
            "visual_dataset_sha256": self.report["visual_dataset_sha256"]})
        self.phase("gpu_inventory", ["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                                     "--format=csv,noheader"], 20)
        uv = shutil.which("uv")
        if uv is None:
            tools = self.work / "bootstrap-tools"
            self.phase("uv_install", [sys.executable, "-m", "pip", "install", "--no-input",
                                       "--no-deps", "--target", tools, "uv==" + UV_VERSION,
                                       "--index-url", "https://pypi.org/simple"], 120)
            uv = str(tools / "bin" / "uv")
            if not Path(uv).is_file() or not os.access(uv, os.X_OK):
                raise JobFailure("uv_binary_missing")
        self.phase("uv_version", [uv, "--version"], 20)
        venv = self.work / "learning-venv"
        self.phase("python312_venv", [uv, "venv", "--python", "3.12", venv], 180)
        self.python = venv / "bin" / "python"
        self.phase("torch_install", [uv, "pip", "install", "--python", self.python,
                                      "torch==2.7.1+cu126", "torchvision==0.22.1+cu126",
                                      "--index-url", "https://download.pytorch.org/whl/cu126"], 360)
        self.phase("learning_install", [uv, "pip", "install", "--no-sources", "--python", self.python,
                                         "-r", self.project / EXPERIMENT / "requirements-learning.txt",
                                         "--index-url", "https://pypi.org/simple",
                                         "--extra-index-url", "https://download.pytorch.org/whl/cu126",
                                         "--index-strategy", "unsafe-best-match"], 360)
        self.phase("dependency_check", [uv, "pip", "check", "--python", self.python], 30)
        output = self.artifacts / "imports.json"
        code = "\n".join([
            "import sys,json,inspect,hashlib,importlib.metadata as md",
            "from pathlib import Path",
            "import torch,torchvision,numpy,h5py,mujoco",
            "from learning_vision import OFFICIAL_SOURCE_SHA256, LEROBOT_REVISION",
            "from lerobot.policies.act.configuration_act import ACTConfig",
            "from lerobot.policies.act.modeling_act import ACTPolicy",
            "assert sys.version_info[:2] == (3,12), 'requires Python 3.12'",
            "assert torch.__version__ == '2.7.1+cu126'",
            "assert torchvision.__version__ == '0.22.1+cu126'",
            "assert torch.cuda.is_available(), 'CUDA unavailable'",
            "actual={cls.__name__:hashlib.sha256(Path(inspect.getfile(cls)).read_bytes()).hexdigest() for cls in (ACTConfig,ACTPolicy)}",
            "assert actual == OFFICIAL_SOURCE_SHA256, 'official ACT source mismatch'",
            "direct=json.loads(md.distribution('lerobot').read_text('direct_url.json'))",
            "assert direct.get('vcs_info',{}).get('commit_id') == LEROBOT_REVISION, 'LeRobot revision mismatch'",
            "result={'python':sys.version,'python_executable':sys.executable,'versions':{n:md.version(n) for n in ['torch','torchvision','numpy','h5py','mujoco','lerobot']},'official_source_sha256':actual,'lerobot_revision':LEROBOT_REVISION,'gpu':torch.cuda.get_device_name(),'cuda':torch.version.cuda,'gpu_total_bytes':torch.cuda.get_device_properties(0).total_memory}",
            f"Path({str(output)!r}).write_text(json.dumps(result,indent=2)+'\\n')",
        ])
        self.phase("import_provenance", [self.python, "-c", code], 45,
                   cwd=self.project / EXPERIMENT)

    def train(self):
        script = self.project / EXPERIMENT / "run_vision_learning.py"
        common = ["--dataset", *self.datasets, "--device", "cuda", "--seed", "0"]
        resource_dir = self.artifacts / "microbenchmark"
        self.phase("microbenchmark", [self.python, script, "microbenchmark", *common,
                                       "--output", resource_dir, "--max-wall-s", "120"], 150)
        resource = json.loads((resource_dir / "report.json").read_text())
        if (resource.get("source_sha256") != self.job["source_sha256"]
                or resource.get("visual_dataset_sha256") != self.job["visual_dataset_sha256"]
                or ("raw_dataset_sha256" in self.job and
                    resource.get("raw_dataset_sha256") != self.job["raw_dataset_sha256"])):
            raise JobFailure("resource_provenance_mismatch")
        attempts = resource.get("attempts", [])
        selected = [a for a in attempts if a.get("batch_size") == 8 and a.get("status") == "passed"]
        if (resource.get("status") != "passed" or resource.get("selected_batch_size") != 8
                or len(attempts) != 1 or len(selected) != 1 or selected[0].get("steps") != 5):
            raise JobFailure("requires_first_attempt_batch8_five_step_resource_pass")
        for key in ("peak_allocated_mib", "peak_reserved_mib"):
            value = selected[0].get("memory_after", {}).get(key)
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or not 0 <= value <= 3200):
                raise JobFailure("resource_memory_limit")
        self.report["training_invocations"] = 1
        self.save()
        fit_dir = self.artifacts / "fit"
        sampling_flags = ["--local-balance"] if self.job.get("local_balance", False) else []
        self.phase("fit", [self.python, script, "fit", *common, "--output", fit_dir,
                            "--resource-report", resource_dir / "report.json", "--camera-reviewed",
                            "--startup-weight", "5", "--extended-fit-budget", "--max-wall-s", "600",
                            "--max-steps", "5000", "--max-epochs", "200", "--snapshot-step", "2115",
                            *sampling_flags], 660)
        fit = json.loads((fit_dir / "report.json").read_text())
        sampler = fit.get("training_sampler")
        if not isinstance(sampler, dict) or type(sampler.get("weight")) is not int or sampler["weight"] != 5:
            raise JobFailure("training_sampler_mode_mismatch")
        if self.job.get("local_balance", False):
            local = sampler.get("local_balance")
            if (not isinstance(local, dict)
                    or local.get("group_order") != ["nonlocal", "startup", "settle"]):
                raise JobFailure("training_sampler_mode_mismatch")
        elif "local_balance" in sampler:
            # Original startup5 reports omit this key entirely; presence is not
            # silently treated as disabled, including malformed null/false values.
            raise JobFailure("training_sampler_mode_mismatch")
        if (fit.get("status") != "completed_diagnostic" or fit.get("checkpoint_reload_exact") is not True
                or fit.get("batch_size") != 8 or not (fit_dir / "policy.pt").is_file()
                or digest(fit_dir / "policy.pt") != fit.get("checkpoint_sha256")):
            raise JobFailure("training_artifact_not_verified")
        self.report.update(status="completed", phase="completed",
                           training_steps=fit.get("training_steps"), stop_reason=fit.get("stop_reason"),
                           checkpoint_sha256=fit["checkpoint_sha256"], snapshot=fit.get("snapshot"),
                           fit_report="fit/report.json")
        self.save()

    def package(self):
        self.save()
        included = []
        total = 0
        for relative in sorted(self.allowed):
            path = self.artifacts / relative
            if not path.exists():
                continue
            if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(self.artifacts.resolve()):
                raise JobFailure("unsafe_artifact")
            size = path.stat().st_size
            limit = 128 * 1024**2 if path.suffix == ".pt" else 16 * 1024**2
            if size > limit:
                raise JobFailure("artifact_size_limit")
            total += size
            included.append({"file": relative, "bytes": size, "sha256": digest(path)})
        if total > 256 * 1024**2:
            raise JobFailure("total_artifact_size_limit")
        manifest = self.artifacts / "artifact-manifest.json"
        atomic_json(manifest, {"files": included})
        archive = self.work / "results.zip"
        with ZipFile(archive, "x", ZIP_STORED) as package:
            for item in included:
                package.write(self.artifacts / item["file"], item["file"])
            package.write(manifest, manifest.name)
        recovery = self.work / "recovery"
        recovery.mkdir(exist_ok=False)
        shards = []
        with archive.open("rb") as stream:
            for index, block in enumerate(iter(lambda: stream.read(SHARD_BYTES), b"")):
                target = recovery / f"results.zip.part-{index:04d}"
                target.write_bytes(block)
                shards.append({"file": target.name, "bytes": len(block), "sha256": digest(target)})
        atomic_json(recovery / "index.json", {
            "schema_version": 1, "zip": {"file": archive.name, "bytes": archive.stat().st_size,
                                          "sha256": digest(archive)},
            "shard_size_bytes": SHARD_BYTES, "shards": shards})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    work = args.work_dir.resolve()
    if (not Path("/content").is_dir() or not work.is_relative_to(Path("/content"))
            or work == Path("/content") or not work.is_dir() or args.work_dir.is_symlink()):
        parser.error("requires an existing dedicated work directory under /content")
    os.umask(0o077)
    worker = Worker(work)
    old_term = signal.signal(signal.SIGTERM, terminate_requested)
    code = 1
    try:
        worker.validate()
        worker.setup()
        worker.train()
        code = 0
    except BaseException as error:
        worker.report.update(status="failed", error_type=type(error).__name__,
                             failure=str(error) if isinstance(error, JobFailure) else "worker_exception")
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        try:
            worker.package()
        except BaseException as error:
            code = 1
            worker.report.update(status="failed", recovery_error_type=type(error).__name__)
            worker.save()
        signal.signal(signal.SIGTERM, old_term)
    print(json.dumps({"status": worker.report["status"], "phase": worker.report["phase"],
                      "recovery_index": str(work / "recovery/index.json")}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
