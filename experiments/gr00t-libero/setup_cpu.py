#!/usr/bin/env python3
"""Install an isolated CPU environment and the pinned LIBERO source, no models."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

from common import ROOT, file_sha256, load_lock, source_manifest, verify_source, write_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, default=ROOT / "output")
    parser.add_argument("--python", default="python3.12")
    parser.add_argument("--download-osmesa", action="store_true",
                        help="Ubuntu: download/extract libosmesa6 into output, without system install")
    args = parser.parse_args()
    lock = load_lock()
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    source_dir = work / "upstream"
    source_dir.mkdir(exist_ok=True)
    archive = source_dir / "libero.tar.gz"
    source = source_dir / f"LIBERO-{lock['libero_revision']}"
    manifest = source_dir / "source.json"
    uv = shutil.which("uv")
    if uv is None:
        parser.error("uv is required")
    if not source.exists():
        subprocess.run(
            ["curl", "-fsSL", "--retry", "2", "--retry-delay", "1", "--max-time", "300",
             f"https://codeload.github.com/Lifelong-Robot-Learning/LIBERO/tar.gz/{lock['libero_revision']}",
             "-o", str(archive)], check=True, timeout=950,
        )
        with tarfile.open(archive) as tar:
            tar.extractall(source_dir, filter="data")
        write_report(manifest, source_manifest(archive, lock))
    elif not manifest.exists():
        raise ValueError("Existing LIBERO source lacks source.json; use a fresh work directory")
    recorded = json.loads(manifest.read_text())
    if recorded.get("revision") != lock["libero_revision"]:
        raise ValueError("Existing source revision differs from the lock")
    if not recorded.get("files"):
        # Upgrade the earlier archive-only record only if that exact archive remains.
        if not archive.is_file() or file_sha256(archive) != recorded.get("archive_sha256"):
            raise ValueError("Cannot upgrade source manifest without its verified archive")
        recorded = source_manifest(archive, lock)
        write_report(manifest, recorded)
    print(f"Verified {verify_source(source, recorded, lock['libero_revision'])} pinned source files")
    if not (source / "libero/libero/assets").is_dir():
        raise ValueError("Pinned LIBERO assets are missing")
    if args.download_osmesa:
        packages = work / "osmesa-package"
        packages.mkdir(exist_ok=True)
        subprocess.run(["apt", "download", "libosmesa6"], cwd=packages, check=True, timeout=180)
        candidates = list(packages.glob("libosmesa6_*_amd64.deb"))
        if len(candidates) != 1:
            raise ValueError("Expected exactly one downloaded amd64 libosmesa6 package")
        subprocess.run(["dpkg-deb", "-x", str(candidates[0]), str(work / "osmesa")], check=True)
    venv = work / "cpu-venv"
    subprocess.run([uv, "venv", str(venv), "--python", args.python, "--allow-existing"], check=True)
    python = venv / "bin/python"
    subprocess.run(
        [uv, "pip", "install", "--python", str(python), "--index-url",
         "https://download.pytorch.org/whl/cpu", "torch==2.9.0+cpu"], check=True,
    )
    subprocess.run(
        [uv, "pip", "install", "--python", str(python), "-r", str(ROOT / "requirements-cpu.txt")],
        check=True,
    )
    subprocess.run(
        [uv, "pip", "install", "--python", str(python), "--no-deps", "-e", str(source),
         "--config-settings", "editable_mode=compat"], check=True
    )
    print(f"CPU environment installed: {python}")
    print("Run this Python with smoke_environment.py; this setup does not run GR00T inference.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
