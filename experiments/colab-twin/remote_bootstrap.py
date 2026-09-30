"""Executed by colab exec after the allowlisted bundle has been uploaded."""
from pathlib import Path
import ctypes.util
import hashlib
import json
import runpy
import subprocess
import sys
from zipfile import ZipFile

if not ctypes.util.find_library("OSMesa"):
    subprocess.run(["apt-get", "update", "-qq"], check=True)
    subprocess.run(["apt-get", "install", "-y", "-qq", "libosmesa6"], check=True)
root = Path("/content/so101-colab-twin")
root.mkdir(exist_ok=True)
with ZipFile("/content/so101-twin-bundle.zip") as archive:
    for name in archive.namelist():
        if not (root / name).resolve().is_relative_to(root.resolve()):
            raise ValueError("Unsafe archive path")
    archive.extractall(root)
manifest = json.loads((root / "manifest.json").read_text())
for entry in manifest["files"]:
    actual = hashlib.sha256((root / entry["path"]).read_bytes()).hexdigest()
    if actual != entry["sha256"]:
        raise ValueError(f"Bundle hash mismatch: {entry['path']}")
sys.argv = [str(root / "run_experiment.py")]
_ = runpy.run_path(sys.argv[0], run_name="__main__")
