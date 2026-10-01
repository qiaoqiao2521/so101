#!/usr/bin/env python3
"""Check an existing GR00T environment; never allocate GPU/Colab or read tokens."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess

from common import ROOT, load_lock, verify_gr00t_checkout, write_report

MIN_VRAM_BYTES = 16_000_000_000


def inspect_device(python: Path) -> dict:
    code = """
import json
try:
 import torch
 d={'torch_version':torch.__version__,'cuda_available':torch.cuda.is_available()}
 if d['cuda_available']:
  p=torch.cuda.get_device_properties(0)
  d.update(name=p.name,total_vram_bytes=p.total_memory,
           capability=list(torch.cuda.get_device_capability(0)),
           bf16_supported=torch.cuda.is_bf16_supported(including_emulation=False))
 print(json.dumps(d))
except Exception as e:
 print(json.dumps({'cuda_available':False,'error_type':type(e).__name__}))
"""
    try:
        result = subprocess.run([str(python), "-c", code], capture_output=True, text=True, timeout=30)
        if result.returncode:
            return {"cuda_available": False, "error": "torch_probe_failed"}
        return json.loads(result.stdout.strip().splitlines()[-1])
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {"cuda_available": False, "error": "python_probe_unavailable"}


def blockers(device: dict) -> list[str]:
    failures = []
    if not device.get("cuda_available"):
        return ["cuda_unavailable"]
    if device.get("total_vram_bytes", 0) < MIN_VRAM_BYTES:
        failures.append("less_than_16GB_total_vram")
    if tuple(device.get("capability", (0, 0))) < (8, 0):
        failures.append("default_flash_attention_2_requires_ampere_or_newer")
    if not device.get("bf16_supported"):
        failures.append("native_bf16_unavailable")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gr00t-root", type=Path)
    parser.add_argument("--python", type=Path, default=Path(shutil.which("python3") or "python3"))
    parser.add_argument("--output", type=Path, default=ROOT / "output/preflight.json")
    args = parser.parse_args()
    lock = load_lock()
    issues = []
    if args.gr00t_root:
        try:
            verify_gr00t_checkout(args.gr00t_root, lock)
        except (OSError, ValueError, subprocess.SubprocessError):
            issues.append("gr00t_checkout_missing_changed_or_wrong_revision")
        args.python = args.gr00t_root / ".venv/bin/python"
        if not (args.gr00t_root / "gr00t/eval/sim/LIBERO/libero_uv/.venv/bin/python").is_file():
            issues.append("official_libero_client_environment_missing")
    else:
        issues.append("gr00t_checkout_not_checked")
    device = inspect_device(args.python)
    issues.extend(blockers(device))
    report = {
        "schema_version": 1, "kind": "gr00t_libero_preflight", "status": "blocked",
        "versions": lock, "device": device, "blockers": issues,
        "backbone_access": "not_checked_requires_user_HF_authorization",
        "checkpoint_downloaded": False, "colab_gpu_availability": "not_checked",
        "gr00t_rollout_completed": False,
    }
    if not issues:
        report["status"] = "device_ready_model_access_unchecked"
    write_report(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
