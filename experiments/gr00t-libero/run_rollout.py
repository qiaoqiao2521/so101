#!/usr/bin/env python3
"""Run one official GR00T/LIBERO episode on an existing compatible GPU."""
from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import uuid

from common import ROOT, file_sha256, load_lock, verify_gr00t_checkout, write_report
from preflight import blockers, inspect_device


def parse_result(text: str) -> dict:
    lines = [line.partition("results: ")[2] for line in text.splitlines()
             if line.startswith("results: ")]
    if len(lines) != 1:
        raise ValueError("Exactly one official rollout result is required")
    result = ast.literal_eval(lines[0])
    if not isinstance(result, tuple) or len(result) != 3:
        raise ValueError("Unexpected official result structure")
    env_name, successes, infos = result
    if not isinstance(successes, list) or len(successes) != 1 or type(successes[0]) is not bool:
        raise ValueError("Expected one boolean episode success")
    lengths = infos.get("episode_lengths", [])
    if len(lengths) != 1 or type(lengths[0]) is not int or lengths[0] < 1:
        raise ValueError("Official rollout did not report a nonempty episode")
    return {"env_name": env_name, "task_success": successes[0],
            "episode_lengths": lengths, "episode_infos": infos}


def logged_command(argv: list[str], log: Path, env: dict, cwd: Path, timeout: int,
                   authenticated_download: bool = False) -> None:
    if authenticated_download:
        result = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=timeout)
        write_report(log, {"kind": "authenticated_model_download", "exit_code": result.returncode})
        result.check_returncode()
        return
    with log.open("w") as stream:
        subprocess.run(argv, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT,
                       check=True, timeout=timeout)


def models_ready(work: Path, lock: dict) -> bool:
    marker = work / "model-provenance.json"
    try:
        provenance = json.loads(marker.read_text())
        model = work / "checkpoints" / lock["checkpoint_subdirectory"]
        index = json.loads((model / "model.safetensors.index.json").read_text())
        required = {"config.json", "processor_config.json", "statistics.json", "embodiment_id.json"}
        required.update(index["weight_map"].values())
        cache = work / "hf-cache" / "models--nvidia--Cosmos-Reason2-2B"
        cached_revision = (cache / "refs/main").read_text().strip()
        snapshot = cache / "snapshots" / cached_revision
        return (
            provenance["checkpoint_revision"] == lock["checkpoint_revision"]
            and provenance["backbone_revision"] == lock["backbone_revision_observed"]
            and cached_revision == lock["backbone_revision_observed"]
            and all((model / name).is_file() for name in required)
            and (snapshot / "config.json").is_file()
            and any(snapshot.glob("*.safetensors"))
        )
    except (OSError, ValueError, KeyError):
        return False


def download_models(root: Path, work: Path, lock: dict, env: dict, run_dir: Path) -> None:
    hf = root / ".venv/bin/hf"
    if not hf.is_file():
        raise ValueError("Official GR00T environment lacks the hf command")
    # Use the official CLI and the minimal published inference file allowlist.
    logged_command(
        [str(hf), "download", lock["checkpoint_repository"], "--revision",
         lock["checkpoint_revision"], "--include", *lock["checkpoint_include"],
         "--local-dir", str(work / "checkpoints")],
        run_dir / "download-checkpoint.log", env, root, 1800, authenticated_download=True,
    )
    # GR00T's official server uses the backbone's main ref. Download into our own
    # cache, verify its exact resolved revision, then serve offline. If main has
    # moved, fail instead of silently running a different backbone or patching it.
    logged_command(
        [str(hf), "download", lock["backbone_repository"], "--revision", "main",
         "--cache-dir", str(work / "hf-cache")],
        run_dir / "download-backbone.log", env, root, 1800, authenticated_download=True,
    )
    cache = work / "hf-cache" / "models--nvidia--Cosmos-Reason2-2B"
    actual = (cache / "refs/main").read_text().strip()
    if actual != lock["backbone_revision_observed"]:
        raise ValueError("Backbone main moved; explicit upstream lock review is required")
    write_report(work / "model-provenance.json", {
        "checkpoint_repository": lock["checkpoint_repository"],
        "checkpoint_revision": lock["checkpoint_revision"],
        "checkpoint_include": lock["checkpoint_include"],
        "backbone_repository": lock["backbone_repository"], "backbone_revision": actual,
    })
    if not models_ready(work, lock):
        raise ValueError("Downloaded model files or provenance are incomplete")


def run(args: argparse.Namespace, report: dict) -> int:
    lock = load_lock()
    root, work = args.gr00t_root.resolve(), args.work_dir.resolve()
    run_dir = args.run_dir
    work.mkdir(parents=True, exist_ok=True)
    verify_gr00t_checkout(root, lock)
    python = root / ".venv/bin/python"
    client_python = root / "gr00t/eval/sim/LIBERO/libero_uv/.venv/bin/python"
    device = inspect_device(python)
    issues = blockers(device)
    if not client_python.is_file():
        issues.append("official_libero_client_environment_missing")
    report["device"] = device
    if issues:
        report.update(status="blocked", blockers=issues)
        return 2
    env = os.environ.copy()
    env.pop("HF_DEBUG", None)
    env.update(HF_HUB_CACHE=str(work / "hf-cache"), HF_HUB_VERBOSITY="error",
               TRANSFORMERS_VERBOSITY="error", HF_HUB_DISABLE_PROGRESS_BARS="1")
    if not models_ready(work, lock):
        if not args.download_models:
            report.update(status="blocked", blockers=["pinned_models_missing_use_download_models"])
            return 2
        download_models(root, work, lock, env, run_dir)
    env.pop("HF_TOKEN", None)
    env.pop("HUGGING_FACE_HUB_TOKEN", None)
    env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", MUJOCO_GL="egl",
               PYOPENGL_PLATFORM="egl")
    # Isolate LIBERO configuration without modifying ~/.libero.
    config_dir = run_dir / "libero-config"
    config_dir.mkdir(exist_ok=True)
    source = root / "external_dependencies/LIBERO/libero/libero"
    (run_dir / "unused-datasets").mkdir(exist_ok=True)
    (config_dir / "config.yaml").write_text(json.dumps({
        "benchmark_root": str(source), "bddl_files": str(source / "bddl_files"),
        "init_states": str(source / "init_files"), "assets": str(source / "assets"),
        "datasets": str(run_dir / "unused-datasets"),
    }))
    env["LIBERO_CONFIG_PATH"] = str(config_dir)
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        port = candidate.getsockname()[1]
    server_command = [str(python), "gr00t/eval/run_gr00t_server.py", "--model-path",
                      str(work / "checkpoints" / lock["checkpoint_subdirectory"]),
                      "--embodiment-tag", "LIBERO_PANDA", "--use-sim-policy-wrapper",
                      "--device", "cuda:0", "--host", "127.0.0.1", "--port", str(port)]
    client_command = [str(client_python), "gr00t/eval/rollout_policy.py", "--n-episodes", "1",
                      "--n-envs", "1", "--seed", str(args.seed), "--policy-client-host",
                      "127.0.0.1", "--policy-client-port", str(port), "--max-episode-steps", "720",
                      "--n-action-steps", "8", "--env-name", "libero_sim/" + lock["default_task"],
                      "--video-dir", str(run_dir / "videos")]
    with (run_dir / "server.log").open("w") as server_log:
        server = subprocess.Popen(server_command, cwd=root, env=env, stdout=server_log,
                                  stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + args.startup_timeout
            while True:
                if server.poll() is not None:
                    raise RuntimeError("Official server exited before becoming ready; inspect server.log")
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=1):
                        break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Official server startup timeout")
                    time.sleep(1)
            logged_command(client_command, run_dir / "client.log", env, root, args.timeout)
            parsed = parse_result((run_dir / "client.log").read_text())
            report.update(parsed)
            report.update(status="completed", gr00t_rollout_completed=True,
                          success_semantics="official_episode_success_with_terminate_on_success",
                          model_provenance=json.loads((work / "model-provenance.json").read_text()),
                          videos=[{"file": p.relative_to(run_dir).as_posix(),
                                   "sha256": file_sha256(p), "bytes": p.stat().st_size}
                                  for p in sorted((run_dir / "videos").rglob("*.mp4"))])
            return 0
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=10)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gr00t-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output/rollout")
    parser.add_argument("--work-dir", type=Path, default=ROOT / "output/gr00t-models",
                        help="Shared pinned model/cache directory; per-run artifacts stay separate")
    parser.add_argument("--download-models", action="store_true",
                        help="Download ~6.915 GB checkpoint plus gated backbone after GPU checks")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--startup-timeout", type=int, default=180)
    args = parser.parse_args()
    if args.timeout < 1 or args.startup_timeout < 1 or not 0 <= args.seed < 2**32:
        parser.error("timeouts must be positive and seed must be in [0, 2**32)")
    args.output_dir = args.output_dir.resolve()
    args.run_dir = args.output_dir / uuid.uuid4().hex
    args.run_dir.mkdir(parents=True)
    report = {"schema_version": 1, "kind": "gr00t_libero_official_rollout", "status": "failed",
              "gr00t_rollout_completed": False, "task_success": None,
              "versions": load_lock(), "run_id": args.run_dir.name,
              "seed": args.seed, "max_episode_steps": 720, "n_action_steps": 8,
              "seed_scope": "client_env_only", "server_rng": "unseeded",
              "initial_state_scope": "seeded_reset_not_benchmark_fixed_initial_state",
              "execution_horizon": 8,
              "n_envs": 1, "n_episodes": 1}
    start = time.monotonic()
    try:
        code = run(args, report)
    except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as error:
        report.update(error={"type": type(error).__name__, "message": "Setup, provenance, or command failed; inspect ignored output logs"})
        code = 1
    except Exception as error:
        report.update(error={"type": type(error).__name__, "message": str(error)})
        code = 1
    report["elapsed_wall_s"] = time.monotonic() - start
    write_report(args.run_dir / "report.json", report)
    print(json.dumps({key: report[key] for key in
                     ("kind", "status", "gr00t_rollout_completed", "task_success")}))
    print(f"Report: {args.run_dir / 'report.json'}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
