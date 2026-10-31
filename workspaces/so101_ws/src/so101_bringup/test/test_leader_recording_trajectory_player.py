#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "leader_recording_trajectory_player.py"


def load_module():
    spec = importlib.util.spec_from_file_location("leader_recording_trajectory_player", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_recording(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


class LeaderRecordingTrajectoryPlayerTests(unittest.TestCase):
    def test_build_trajectory_message_keeps_monotonic_times(self):
        module = load_module()
        frames = [
            module.ReplayFrame(0, ["j1"], [0.0], []),
            module.ReplayFrame(1_000_000_000, ["j1"], [0.5], []),
            module.ReplayFrame(2_000_000_000, ["j1"], [1.0], []),
        ]

        trajectory, summary = module.build_trajectory_message(
            frames,
            rate_scale=2.0,
            min_point_dt_sec=0.02,
            initial_hold_sec=0.0,
            prepend_first_point_copy=False,
        )

        self.assertEqual(["j1"], list(trajectory.joint_names))
        self.assertEqual(3, len(trajectory.points))
        self.assertEqual(0, summary["duplicate_stamp_count"])
        self.assertEqual(0, summary["removed_non_monotonic_count"])
        self.assertEqual(0, summary["adjusted_timepoint_count"])
        self.assertEqual(1.0, summary["total_duration_sec"])
        self.assertEqual(500000000, trajectory.points[1].time_from_start.nanosec)

    def test_build_trajectory_message_sanitizes_non_monotonic_timestamps(self):
        module = load_module()
        frames = [
            module.ReplayFrame(0, ["j1"], [0.0], []),
            module.ReplayFrame(1_000_000_000, ["j1"], [0.5], []),
            module.ReplayFrame(1_000_000_000, ["j1"], [0.6], []),
            module.ReplayFrame(500_000_000, ["j1"], [0.2], []),
        ]

        trajectory, summary = module.build_trajectory_message(
            frames,
            rate_scale=1.0,
            min_point_dt_sec=0.05,
            initial_hold_sec=0.0,
            prepend_first_point_copy=False,
        )

        times = [
            point.time_from_start.sec + point.time_from_start.nanosec / 1_000_000_000.0
            for point in trajectory.points
        ]
        self.assertEqual(4, summary["source_frame_count"])
        self.assertEqual(2, len(trajectory.points))
        self.assertEqual(1, summary["duplicate_stamp_count"])
        self.assertEqual(1, summary["removed_non_monotonic_count"])
        self.assertEqual(0, summary["adjusted_timepoint_count"])
        self.assertEqual(sorted(times), times)
        self.assertEqual(1.0, times[-1])

    def test_load_recording_rejects_joint_name_mismatch(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            recording_path = Path(temp_dir) / "bad.jsonl"
            write_recording(
                recording_path,
                [
                    {"stamp_ns": 0, "joint_names": ["j1"], "positions": [0.0]},
                    {"stamp_ns": 1_000_000_000, "joint_names": ["j2"], "positions": [1.0]},
                ],
            )

            with self.assertRaises(ValueError):
                module.load_recording(recording_path)

    def test_build_command_dump_serializes_time_and_positions(self):
        module = load_module()
        frames = [
            module.ReplayFrame(0, ["j1"], [0.0], []),
            module.ReplayFrame(1_000_000_000, ["j1"], [1.0], [0.5]),
        ]
        trajectory, summary = module.build_trajectory_message(
            frames,
            rate_scale=1.0,
            min_point_dt_sec=0.01,
            initial_hold_sec=0.0,
            prepend_first_point_copy=False,
        )
        trajectory.header.stamp = module.time_from_ns(2_500_000_000)

        payload = module.build_command_dump(
            trajectory,
            summary,
            input_path=Path("/tmp/input.jsonl"),
            publish_request_ns=2_000_000_000,
            header_start_delay_sec=0.5,
        )

        self.assertEqual("leader_player_command.v1", payload["schema_version"])
        self.assertEqual(["j1"], payload["joint_names"])
        self.assertEqual(2, len(payload["points"]))
        self.assertEqual("topic", payload["command_mode"])
        self.assertEqual(2500000000, payload["header"]["stamp_ns"])
        self.assertEqual(0.5, payload["header"]["start_delay_sec"])
        self.assertEqual(2000000000, payload["header"]["publish_request_ns"])
        self.assertEqual(1.0, payload["points"][1]["time_from_start_sec"])
        self.assertEqual([1.0], payload["points"][1]["positions"])

    def test_build_trajectory_message_supports_initial_hold_and_prepend_copy(self):
        module = load_module()
        frames = [
            module.ReplayFrame(0, ["j1"], [0.2], [0.1]),
            module.ReplayFrame(1_000_000_000, ["j1"], [0.5], [0.2]),
        ]

        trajectory, summary = module.build_trajectory_message(
            frames,
            rate_scale=1.0,
            min_point_dt_sec=0.01,
            initial_hold_sec=0.2,
            prepend_first_point_copy=True,
        )

        times = [
            point.time_from_start.sec + point.time_from_start.nanosec / 1_000_000_000.0
            for point in trajectory.points
        ]
        self.assertEqual([0.0, 0.2, 1.2], times)
        self.assertEqual(True, summary["prepend_first_point_copy"])
        self.assertEqual(0.2, summary["initial_hold_sec"])

    def test_resolve_header_stamp_ns_applies_future_delay(self):
        module = load_module()
        self.assertEqual(
            0,
            module.resolve_header_stamp_ns(now_ns=1_200_000_000, header_start_delay_sec=0.0),
        )
        self.assertEqual(
            1_700_000_000,
            module.resolve_header_stamp_ns(now_ns=1_200_000_000, header_start_delay_sec=0.5),
        )
        with self.assertRaises(ValueError):
            module.resolve_header_stamp_ns(now_ns=1_200_000_000, header_start_delay_sec=-0.1)

    def test_build_action_feedback_payload_serializes_desired_actual_error(self):
        module = load_module()
        feedback = module.FollowJointTrajectory.Feedback()
        feedback.header.stamp = module.time_from_ns(1_250_000_000)
        feedback.joint_names = ["j1"]
        feedback.desired.positions = [1.0]
        feedback.desired.velocities = [0.1]
        feedback.desired.time_from_start = module.duration_from_sec(0.2)
        feedback.actual.positions = [0.8]
        feedback.actual.velocities = [0.05]
        feedback.actual.time_from_start = module.duration_from_sec(0.2)
        feedback.error.positions = [0.2]
        feedback.error.velocities = [0.05]
        feedback.error.time_from_start = module.duration_from_sec(0.2)

        payload = module.build_action_feedback_payload(feedback, joint_names=["j1"])

        self.assertEqual(1250000000, payload["stamp_ns"])
        self.assertEqual(["j1"], payload["joint_names"])
        self.assertEqual([1.0], payload["desired"]["positions"])
        self.assertEqual([0.8], payload["actual"]["positions"])
        self.assertEqual([0.2], payload["error"]["positions"])

    def test_build_action_result_payload_serializes_status_and_error_code(self):
        module = load_module()
        result = module.FollowJointTrajectory.Result()
        result.error_code = module.FollowJointTrajectory.Result.SUCCESSFUL
        result.error_string = ""

        payload = module.build_action_result_payload(
            action_name="/joint_trajectory_controller/follow_joint_trajectory",
            goal_status=module.GoalStatus.STATUS_SUCCEEDED,
            goal_result=result,
            joint_names=["j1"],
            summary={"command_mode": "action"},
        )

        self.assertEqual("leader_follow_joint_trajectory_result.v1", payload["schema_version"])
        self.assertEqual("STATUS_SUCCEEDED", payload["goal_status_label"])
        self.assertEqual(0, payload["result"]["error_code"])
        self.assertEqual(["j1"], payload["joint_names"])

    def test_build_action_runtime_error_payload_serializes_runtime_error(self):
        module = load_module()
        payload = module.build_action_runtime_error_payload(
            action_name="/joint_trajectory_controller/follow_joint_trajectory",
            joint_names=["j1"],
            summary={"command_mode": "action"},
            error_type="result_timeout",
            error_message="timed out",
            goal_status=module.GoalStatus.STATUS_EXECUTING,
        )

        self.assertEqual("leader_follow_joint_trajectory_result.v1", payload["schema_version"])
        self.assertEqual("STATUS_EXECUTING", payload["goal_status_label"])
        self.assertEqual("result_timeout", payload["runtime_error"]["type"])
        self.assertEqual("timed out", payload["runtime_error"]["message"])


if __name__ == "__main__":
    unittest.main()
