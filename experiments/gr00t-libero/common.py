"""Shared, credential-free paths and report helpers."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parent


def load_lock() -> dict:
    return json.loads((ROOT / "upstream.json").read_text())


def write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def source_manifest(archive: Path, lock: dict) -> dict:
    """Derive expected file hashes from the pinned archive, not the mutable checkout."""
    files = {}
    prefix = f"LIBERO-{lock['libero_revision']}/"
    with tarfile.open(archive) as tar:
        for member in tar:
            if member.isdir():
                continue
            if not member.isfile() or not member.name.startswith(prefix):
                raise ValueError("Unexpected link or path in pinned source archive")
            relative = member.name[len(prefix):]
            if not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
                raise ValueError("Unsafe source archive path")
            stream = tar.extractfile(member)
            if stream is None:
                raise ValueError("Missing archive file stream")
            with stream:
                files[relative] = hashlib.file_digest(stream, "sha256").hexdigest()
    if not files:
        raise ValueError("Source archive has no files")
    return {"repository": lock["libero_repository"], "revision": lock["libero_revision"],
            "archive_sha256": file_sha256(archive), "files": files,
            "generated_exclusions": ["__pycache__", "*.pyc", "*.egg-info"]}


def verify_source(source: Path, manifest: dict, expected_revision: str) -> int:
    if manifest.get("revision") != expected_revision or not manifest.get("files"):
        raise ValueError("LIBERO source revision or file manifest is missing/mismatched")
    expected = manifest["files"]
    source = source.resolve()
    for relative, digest in expected.items():
        rel = Path(relative)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Unsafe source manifest path")
        path = source / rel
        if not path.resolve().is_relative_to(source) or path.is_symlink():
            raise ValueError("Source manifest file escapes its source directory")
        if not path.is_file() or file_sha256(path) != digest:
            raise ValueError(f"Pinned LIBERO source modified or missing: {relative}")
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        generated = any(part == "__pycache__" or part.endswith(".egg-info")
                        for part in relative.parts) or path.suffix == ".pyc"
        if not generated and (path.is_file() or path.is_symlink()) and relative.as_posix() not in expected:
            raise ValueError(f"Unexpected file in pinned LIBERO source: {relative}")
    return len(expected)


def verify_gr00t_checkout(path: Path, lock: dict) -> None:
    revision = subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"], text=True, timeout=10,
        stderr=subprocess.DEVNULL,
    ).strip()
    if revision != lock["gr00t_revision"]:
        raise ValueError("GR00T checkout revision differs from upstream.json")
    libero = subprocess.check_output(
        ["git", "-C", str(path / "external_dependencies/LIBERO"), "rev-parse", "HEAD"],
        text=True, timeout=10, stderr=subprocess.DEVNULL,
    ).strip()
    if libero != lock["libero_revision"]:
        raise ValueError("LIBERO submodule revision differs from upstream.json")
    clean = subprocess.run(
        ["git", "-C", str(path), "diff", "--quiet", "HEAD", "--"], timeout=10
    )
    if clean.returncode:
        raise ValueError("GR00T checkout has tracked modifications")
