"""Launch the pinned official wizard for SO101's fixed and moving fingers."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

from infer import UPSTREAM_REVISION, digest


def launch(args):
    upstream, source, output = args.upstream.resolve(), args.source.resolve(), args.output.resolve()
    revision = subprocess.check_output(["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(upstream), "status", "--porcelain", "--untracked-files=no"], text=True)
    if revision != UPSTREAM_REVISION or dirty:
        raise ValueError("Official upstream binding differs")
    assets = source / "gripper-assets/so101_sim_tip_region"
    audit = json.loads((assets / "geometry-audit.json").read_text())
    for name, expected in audit["gripper_asset_files_sha256"].items():
        if digest(assets / name) != expected:
            raise ValueError("Source gripper asset changed: " + name)
    output.mkdir(parents=True, exist_ok=False)
    os.environ["GRASPGENX_CHECKPOINT_DIR"] = str(args.models.resolve())
    os.environ["GRASPGENX_GRIPPER_CFG_DIR"] = str(source)
    sys.path.insert(0, str(upstream))
    import viser
    from scripts.gripper_config_wizard import ConfigWizard, load_urdf
    config = json.loads((assets / "config.json").read_text())
    urdf = str(assets / "gripper.urdf")
    robot = load_urdf(urdf)
    # Official motion-only detection misses the stationary finger and produces
    # extent_x=0. Select both actual finger meshes; exclude the motor mesh.
    fingers = [name for name in robot.scene.geometry if name in
               ("wrist_roll_follower_so101_v1.stl", "moving_jaw_so101_v1.stl")]
    if len(fingers) != 2:
        raise ValueError("Expected exactly the fixed and moving finger meshes")
    server = viser.ViserServer(host="127.0.0.1", port=args.port)
    wizard = ConfigWizard(server, robot, urdf, "so101_task_tip_region", args.port,
                          output_root=str(output))
    wizard._finger_geoms = fingers
    wizard.base_rotation = np.asarray(config["base_rotation"])
    wizard.open_js, wizard.close_js = config["open"], config["close"]
    manifest = {"upstream_revision": revision, "wizard_source_sha256": digest(upstream / "scripts/gripper_config_wizard.py"),
                "adapter_sha256": digest(Path(__file__)), "source_assets_sha256": audit["gripper_asset_files_sha256"],
                "finger_geometries": fingers, "operating_open": config["open"], "operating_close": config["close"],
                "initial_base_rotation": config["base_rotation"], "bind_host": "127.0.0.1",
                "scope": "Declared task operating jaw interval, not full hardware aperture or entity calibration",
                "physics_steps": 0, "hardware_access": False}
    (output / "launcher.json").write_text(json.dumps(manifest, indent=2)+"\n")
    wizard.start()
    try:
        while True:
            time.sleep(.2)
    finally:
        server.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("upstream", "models", "source", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--port", type=int, default=18081)
    launch(parser.parse_args())
