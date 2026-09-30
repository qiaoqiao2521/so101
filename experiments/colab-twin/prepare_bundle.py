#!/usr/bin/env python3
"""Bundle only public model assets and this experiment, excluding local data."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["planning", "baseline"], default="planning")
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    if not 1 <= args.episodes <= 100 or not 0 <= args.seed <= 0xFFFFFFFF - args.episodes:
        raise ValueError("episodes/seed outside supported ranges")
    experiment = Path(__file__).resolve().parent
    repo = experiment.parents[1]
    workspace = repo / "workspaces" / "so101_ws"
    models = workspace / "src" / "so101_mujoco" / "models"
    source = models / "so101.xml"
    files = [(source, "models/so101.xml"),
             (workspace / "src" / "SO-ARM100" / "LICENSE", "MODEL_LICENSE"),
             (experiment / "run_experiment.py", "run_experiment.py"),
             (experiment / "requirements.txt", "requirements.txt")]
    if args.mode == "planning":
        for name in ["planning_experiment.py", "collision_scene.py", "position_ik.py",
                     "joint_planner.py", "planning_scenario.json"]:
            files.append((experiment / name, name))
    for mesh in ET.parse(source).findall("./asset/mesh"):
        name = mesh.get("file")
        if Path(name).name != name:
            raise ValueError(f"Unexpected mesh path: {name}")
        files.append((models / "assets" / name, "models/assets/" + name))
    manifest = {"source": "TheRobotStudio/SO-ARM100 (existing repository assets)", "files": []}
    with ZipFile(experiment / "bundle.zip", "w", ZIP_DEFLATED) as archive:
        for path, name in files:
            data = path.read_bytes()
            if not data:
                raise ValueError(f"Empty asset: {path}")
            archive.writestr(name, data)
            manifest["files"].append({"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        config = json.dumps(vars(args), indent=2).encode() + b"\n"
        archive.writestr("experiment_config.json", config)
        manifest["files"].append({"path": "experiment_config.json", "bytes": len(config),
                                  "sha256": hashlib.sha256(config).hexdigest()})
        archive.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
    print(f"Prepared {len(manifest['files'])} allowlisted files: {experiment / 'bundle.zip'}")


if __name__ == "__main__":
    main()
