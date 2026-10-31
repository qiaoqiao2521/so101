#!/usr/bin/env python3
import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "so101_leader_input_bridge.py"


def load_module():
    spec = importlib.util.spec_from_file_location("so101_leader_input_bridge", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class LeaderInputBridgeTests(unittest.TestCase):
    def test_build_status_payload_ready(self):
        module = load_module()
        payload = module.build_status_payload(
            state=module.STATE_READY,
            connected=True,
            calibrated=True,
            publishing=True,
            hz=29.93,
            last_frame_age_ms=11.4,
            last_error="",
            device_label="so101_leader",
            backend="plugin",
        )

        self.assertEqual(module.STATE_READY, payload["state"])
        self.assertTrue(payload["connected"])
        self.assertTrue(payload["calibrated"])
        self.assertTrue(payload["publishing"])
        self.assertEqual("so101_leader", payload["deviceLabel"])
        self.assertEqual("plugin", payload["backend"])

    def test_build_adapter_without_factory_returns_builtin_adapter(self):
        module = load_module()
        adapter = module.build_adapter(
            adapter_factory="",
            leader_type="so101_leader",
            port="",
            calibration_path="",
            joint_names=module.DEFAULT_JOINT_NAMES,
            positions_in_degrees="auto",
        )
        self.assertIsInstance(
            adapter,
            (module.UnavailableLeaderAdapter, module.OfficialSOLeaderAdapter),
        )

    def test_invalid_factory_path_raises_bridge_error(self):
        module = load_module()
        with self.assertRaises(module.BridgeError):
            module.build_adapter(
                adapter_factory="invalid_factory_path",
                leader_type="so101_leader",
                port="",
                calibration_path="",
                joint_names=module.DEFAULT_JOINT_NAMES,
                positions_in_degrees="auto",
            )

    def test_official_action_dict_with_pos_suffix_is_accepted(self):
        module = load_module()
        adapter = module.OfficialSOLeaderAdapter(
            leader_type="so101_leader",
            port="",
            calibration_path="",
            joint_names=module.DEFAULT_JOINT_NAMES,
            positions_in_degrees="false",
        )
        payload = {
            "shoulder_pan.pos": 1.0,
            "shoulder_lift.pos": 2.0,
            "elbow_flex.pos": 3.0,
            "wrist_flex.pos": 4.0,
            "wrist_roll.pos": 5.0,
            "gripper.pos": 6.0,
        }

        positions = adapter._coerce_positions(payload)
        self.assertEqual([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], positions)


if __name__ == "__main__":
    unittest.main()
