#!/usr/bin/env python3
import importlib.util
import sys
import unittest
from pathlib import Path

from builtin_interfaces.msg import Duration, Time
from control_msgs.msg import JointTrajectoryControllerState
from std_msgs.msg import Header
from trajectory_msgs.msg import JointTrajectoryPoint


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "joint_trajectory_controller_state_recorder.py"


def load_module():
    spec = importlib.util.spec_from_file_location("joint_trajectory_controller_state_recorder", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_point(position: float, time_from_start_sec: float) -> JointTrajectoryPoint:
    point = JointTrajectoryPoint()
    point.positions = [position]
    point.velocities = [position * 0.1]
    point.accelerations = []
    point.effort = []
    point.time_from_start = Duration(
        sec=int(time_from_start_sec),
        nanosec=int(round((time_from_start_sec % 1.0) * 1_000_000_000.0)),
    )
    return point


class JointTrajectoryControllerStateRecorderTests(unittest.TestCase):
    def test_build_state_payload_serializes_reference_feedback_and_output(self):
        module = load_module()
        msg = JointTrajectoryControllerState()
        msg.header = Header(stamp=Time(sec=12, nanosec=345))
        msg.joint_names = ["elbow_flex"]
        msg.reference = make_point(1.0, 0.5)
        msg.feedback = make_point(0.9, 0.5)
        msg.error = make_point(0.1, 0.5)
        msg.output = make_point(0.8, 0.5)

        payload = module.build_state_payload(msg)

        self.assertEqual(12_000_000_345, payload["stamp_ns"])
        self.assertEqual(["elbow_flex"], payload["joint_names"])
        self.assertEqual([1.0], payload["reference"]["positions"])
        self.assertEqual([0.9], payload["feedback"]["positions"])
        self.assertEqual([0.8], payload["output"]["positions"])
        self.assertEqual(0.5, payload["reference"]["time_from_start_sec"])


if __name__ == "__main__":
    unittest.main()
