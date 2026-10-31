#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import rclpy
from action_msgs.msg import GoalStatus
from builtin_interfaces.msg import Duration, Time
from control_msgs.action import FollowJointTrajectory
from rclpy.action import ActionClient
from rclpy.node import Node
from std_srvs.srv import Trigger
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


@dataclass(frozen=True)
class ReplayFrame:
    stamp_ns: int
    joint_names: list[str]
    positions: list[float]
    velocities: list[float]


GOAL_STATUS_LABELS = {
    GoalStatus.STATUS_UNKNOWN: "STATUS_UNKNOWN",
    GoalStatus.STATUS_ACCEPTED: "STATUS_ACCEPTED",
    GoalStatus.STATUS_EXECUTING: "STATUS_EXECUTING",
    GoalStatus.STATUS_CANCELING: "STATUS_CANCELING",
    GoalStatus.STATUS_SUCCEEDED: "STATUS_SUCCEEDED",
    GoalStatus.STATUS_CANCELED: "STATUS_CANCELED",
    GoalStatus.STATUS_ABORTED: "STATUS_ABORTED",
}


def sanitize_timestamp_sequence(frames: list[ReplayFrame]) -> tuple[list[ReplayFrame], dict[str, int]]:
    cleaned: list[ReplayFrame] = []
    duplicate_stamp_count = 0
    removed_non_monotonic_count = 0
    last_stamp_ns: int | None = None
    for frame in frames:
        if last_stamp_ns is None or frame.stamp_ns > last_stamp_ns:
            cleaned.append(frame)
            last_stamp_ns = frame.stamp_ns
            continue
        if frame.stamp_ns == last_stamp_ns:
            duplicate_stamp_count += 1
        else:
            removed_non_monotonic_count += 1
    if not cleaned:
        raise ValueError("all frames were removed by timestamp sanitization")
    return cleaned, {
        "duplicate_stamp_count": duplicate_stamp_count,
        "removed_non_monotonic_count": removed_non_monotonic_count,
    }


def load_recording(path: Path) -> list[ReplayFrame]:
    frames: list[ReplayFrame] = []
    expected_joint_names: list[str] | None = None
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        joint_names = [str(value) for value in payload["joint_names"]]
        positions = [float(value) for value in payload["positions"]]
        velocities = [float(value) for value in payload.get("velocities", [])]
        if not joint_names:
            raise ValueError(f"{path}:{line_no}: joint_names is empty")
        if len(joint_names) != len(positions):
            raise ValueError(
                f"{path}:{line_no}: positions length mismatch: expected {len(joint_names)}, got {len(positions)}"
            )
        if velocities and len(velocities) != len(joint_names):
            raise ValueError(
                f"{path}:{line_no}: velocities length mismatch: expected {len(joint_names)}, got {len(velocities)}"
            )
        if expected_joint_names is None:
            expected_joint_names = list(joint_names)
        elif joint_names != expected_joint_names:
            raise ValueError(
                f"{path}:{line_no}: joint_names mismatch: expected {expected_joint_names}, got {joint_names}"
            )
        frames.append(
            ReplayFrame(
                stamp_ns=int(payload["stamp_ns"]),
                joint_names=joint_names,
                positions=positions,
                velocities=velocities,
            )
        )
    if not frames:
        raise ValueError(f"no replayable frames found in {path}")
    return frames


def duration_from_sec(value_sec: float) -> Duration:
    clamped = max(float(value_sec), 0.0)
    total_ns = int(round(clamped * 1_000_000_000.0))
    return Duration(sec=total_ns // 1_000_000_000, nanosec=total_ns % 1_000_000_000)


def duration_to_sec(value: Duration) -> float:
    return float(value.sec) + float(value.nanosec) / 1_000_000_000.0


def time_from_ns(value_ns: int) -> Time:
    clamped = max(int(value_ns), 0)
    return Time(sec=clamped // 1_000_000_000, nanosec=clamped % 1_000_000_000)


def time_to_ns(value: Time) -> int:
    return int(value.sec) * 1_000_000_000 + int(value.nanosec)


def resolve_header_stamp_ns(*, now_ns: int, header_start_delay_sec: float) -> int:
    if header_start_delay_sec < 0.0:
        raise ValueError(f"header_start_delay_sec must be non-negative, got {header_start_delay_sec}")
    if header_start_delay_sec == 0.0:
        return 0
    return int(now_ns) + int(round(float(header_start_delay_sec) * 1_000_000_000.0))


def build_trajectory_message(
    frames: list[ReplayFrame],
    *,
    rate_scale: float,
    min_point_dt_sec: float,
    initial_hold_sec: float,
    prepend_first_point_copy: bool,
) -> tuple[JointTrajectory, dict[str, Any]]:
    if rate_scale <= 0.0:
        raise ValueError(f"rate_scale must be positive, got {rate_scale}")
    if min_point_dt_sec < 0.0:
        raise ValueError(f"min_point_dt_sec must be non-negative, got {min_point_dt_sec}")
    if initial_hold_sec < 0.0:
        raise ValueError(f"initial_hold_sec must be non-negative, got {initial_hold_sec}")

    cleaned_frames, stamp_stats = sanitize_timestamp_sequence(frames)
    start_stamp_ns = cleaned_frames[0].stamp_ns
    trajectory = JointTrajectory()
    trajectory.joint_names = list(cleaned_frames[0].joint_names)

    adjusted_timepoint_count = 0
    previous_time_sec: float | None = None

    if prepend_first_point_copy and initial_hold_sec > 0.0:
        hold_point = JointTrajectoryPoint()
        hold_point.positions = list(cleaned_frames[0].positions)
        if cleaned_frames[0].velocities:
            hold_point.velocities = [0.0 for _ in cleaned_frames[0].velocities]
        hold_point.time_from_start = duration_from_sec(0.0)
        trajectory.points.append(hold_point)
        previous_time_sec = 0.0

    for frame in cleaned_frames:
        raw_time_sec = max((frame.stamp_ns - start_stamp_ns) / 1_000_000_000.0, 0.0) / rate_scale
        raw_time_sec += initial_hold_sec
        target_time_sec = raw_time_sec
        if previous_time_sec is None:
            target_time_sec = raw_time_sec
        elif target_time_sec <= previous_time_sec:
            adjusted_timepoint_count += 1
            target_time_sec = previous_time_sec + min_point_dt_sec

        point = JointTrajectoryPoint()
        point.positions = list(frame.positions)
        if frame.velocities:
            point.velocities = list(frame.velocities)
        point.time_from_start = duration_from_sec(target_time_sec)
        trajectory.points.append(point)
        previous_time_sec = target_time_sec

    total_duration_sec = 0.0 if previous_time_sec is None else previous_time_sec
    summary = {
        "source_frame_count": len(frames),
        "frame_count": len(cleaned_frames),
        "joint_names": list(trajectory.joint_names),
        "rate_scale": rate_scale,
        "min_point_dt_sec": min_point_dt_sec,
        "initial_hold_sec": round(initial_hold_sec, 6),
        "prepend_first_point_copy": bool(prepend_first_point_copy),
        "duplicate_stamp_count": stamp_stats["duplicate_stamp_count"],
        "removed_non_monotonic_count": stamp_stats["removed_non_monotonic_count"],
        "adjusted_timepoint_count": adjusted_timepoint_count,
        "total_duration_sec": round(total_duration_sec, 6),
    }
    return trajectory, summary


def build_command_dump(
    trajectory: JointTrajectory,
    summary: dict[str, Any],
    *,
    input_path: Path,
    publish_request_ns: int | None = None,
    header_start_delay_sec: float = 0.0,
    command_mode: str = "topic",
) -> dict[str, Any]:
    header_stamp_ns = time_to_ns(trajectory.header.stamp)
    return {
        "schema_version": "leader_player_command.v1",
        "input_path": str(input_path.resolve()),
        "joint_names": list(trajectory.joint_names),
        "summary": dict(summary),
        "command_mode": command_mode,
        "header": {
            "stamp_ns": header_stamp_ns,
            "stamp_sec": round(header_stamp_ns / 1_000_000_000.0, 6),
            "start_delay_sec": round(float(header_start_delay_sec), 6),
            "publish_request_ns": int(publish_request_ns) if publish_request_ns is not None else None,
            "publish_request_sec": (
                round(int(publish_request_ns) / 1_000_000_000.0, 6) if publish_request_ns is not None else None
            ),
        },
        "points": [
            {
                "index": index,
                "time_from_start_sec": round(duration_to_sec(point.time_from_start), 6),
                "positions": [float(value) for value in point.positions],
                "velocities": [float(value) for value in point.velocities],
            }
            for index, point in enumerate(trajectory.points)
        ],
    }


def build_action_feedback_payload(
    feedback_msg: FollowJointTrajectory.Feedback,
    *,
    joint_names: list[str],
) -> dict[str, Any]:
    stamp_ns = int(feedback_msg.header.stamp.sec) * 1_000_000_000 + int(feedback_msg.header.stamp.nanosec)
    return {
        "stamp_ns": stamp_ns,
        "joint_names": list(joint_names or feedback_msg.joint_names),
        "desired": {
            "positions": [float(value) for value in feedback_msg.desired.positions],
            "velocities": [float(value) for value in feedback_msg.desired.velocities],
            "accelerations": [float(value) for value in feedback_msg.desired.accelerations],
            "effort": [float(value) for value in feedback_msg.desired.effort],
            "time_from_start_sec": round(duration_to_sec(feedback_msg.desired.time_from_start), 6),
        },
        "actual": {
            "positions": [float(value) for value in feedback_msg.actual.positions],
            "velocities": [float(value) for value in feedback_msg.actual.velocities],
            "accelerations": [float(value) for value in feedback_msg.actual.accelerations],
            "effort": [float(value) for value in feedback_msg.actual.effort],
            "time_from_start_sec": round(duration_to_sec(feedback_msg.actual.time_from_start), 6),
        },
        "error": {
            "positions": [float(value) for value in feedback_msg.error.positions],
            "velocities": [float(value) for value in feedback_msg.error.velocities],
            "accelerations": [float(value) for value in feedback_msg.error.accelerations],
            "effort": [float(value) for value in feedback_msg.error.effort],
            "time_from_start_sec": round(duration_to_sec(feedback_msg.error.time_from_start), 6),
        },
    }


def build_action_result_payload(
    *,
    action_name: str,
    goal_status: int,
    goal_result: FollowJointTrajectory.Result,
    joint_names: list[str],
    summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "leader_follow_joint_trajectory_result.v1",
        "action_name": action_name,
        "goal_status": int(goal_status),
        "goal_status_label": GOAL_STATUS_LABELS.get(int(goal_status), f"UNKNOWN_{goal_status}"),
        "joint_names": list(joint_names),
        "summary": dict(summary),
        "result": {
            "error_code": int(goal_result.error_code),
            "error_string": str(goal_result.error_string),
        },
    }


def build_action_runtime_error_payload(
    *,
    action_name: str,
    joint_names: list[str],
    summary: dict[str, Any],
    error_type: str,
    error_message: str,
    goal_status: int = GoalStatus.STATUS_UNKNOWN,
) -> dict[str, Any]:
    return {
        "schema_version": "leader_follow_joint_trajectory_result.v1",
        "action_name": action_name,
        "goal_status": int(goal_status),
        "goal_status_label": GOAL_STATUS_LABELS.get(int(goal_status), f"UNKNOWN_{goal_status}"),
        "joint_names": list(joint_names),
        "summary": dict(summary),
        "runtime_error": {
            "type": error_type,
            "message": error_message,
        },
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class LeaderRecordingTrajectoryPlayer(Node):
    def __init__(self) -> None:
        super().__init__("leader_recording_trajectory_player")

        self.declare_parameter("input_path", "")
        self.declare_parameter("trajectory_topic", "/joint_trajectory_controller/joint_trajectory")
        self.declare_parameter("startup_delay_sec", 24.0)
        self.declare_parameter("settle_sec", 2.0)
        self.declare_parameter("rate_scale", 1.0)
        self.declare_parameter("min_point_dt_sec", 0.001)
        self.declare_parameter("wait_for_subscribers_sec", 5.0)
        self.declare_parameter("initial_hold_sec", 0.0)
        self.declare_parameter("prepend_first_point_copy", False)
        self.declare_parameter("header_start_delay_sec", 0.0)
        self.declare_parameter("preposition_first_point_sec", 0.0)
        self.declare_parameter("command_mode", "topic")
        self.declare_parameter("follow_joint_trajectory_action", "/joint_trajectory_controller/follow_joint_trajectory")
        self.declare_parameter("action_server_wait_sec", 10.0)
        self.declare_parameter("action_result_timeout_sec", 0.0)
        self.declare_parameter("goal_time_tolerance_sec", 0.0)
        self.declare_parameter("control_recorder", False)
        self.declare_parameter("recorder_start_service", "/leader/start_recording")
        self.declare_parameter("recorder_stop_service", "/leader/stop_recording")
        self.declare_parameter("recorder_service_wait_sec", 5.0)
        self.declare_parameter("command_dump_path", "")
        self.declare_parameter("action_feedback_path", "")
        self.declare_parameter("action_result_path", "")

        input_path = Path(str(self.get_parameter("input_path").value).strip())
        if not input_path:
            raise ValueError("input_path is required")
        if not input_path.is_file():
            raise FileNotFoundError(f"input_path not found: {input_path}")

        trajectory_topic = (
            str(self.get_parameter("trajectory_topic").value).strip()
            or "/joint_trajectory_controller/joint_trajectory"
        )
        self.startup_delay_sec = max(float(self.get_parameter("startup_delay_sec").value), 0.0)
        self.settle_sec = max(float(self.get_parameter("settle_sec").value), 0.0)
        self.wait_for_subscribers_sec = max(float(self.get_parameter("wait_for_subscribers_sec").value), 0.0)
        self.header_start_delay_sec = max(float(self.get_parameter("header_start_delay_sec").value), 0.0)
        self.preposition_first_point_sec = max(float(self.get_parameter("preposition_first_point_sec").value), 0.0)
        self.command_mode = str(self.get_parameter("command_mode").value).strip().lower() or "topic"
        if self.command_mode not in {"topic", "action"}:
            raise ValueError(f"command_mode must be 'topic' or 'action', got {self.command_mode!r}")
        self.follow_joint_trajectory_action = (
            str(self.get_parameter("follow_joint_trajectory_action").value).strip()
            or "/joint_trajectory_controller/follow_joint_trajectory"
        )
        self.action_server_wait_sec = max(float(self.get_parameter("action_server_wait_sec").value), 0.0)
        self.action_result_timeout_sec = max(float(self.get_parameter("action_result_timeout_sec").value), 0.0)
        self.goal_time_tolerance_sec = max(float(self.get_parameter("goal_time_tolerance_sec").value), 0.0)
        self.control_recorder = bool(self.get_parameter("control_recorder").value)
        self.recorder_start_service = (
            str(self.get_parameter("recorder_start_service").value).strip() or "/leader/start_recording"
        )
        self.recorder_stop_service = (
            str(self.get_parameter("recorder_stop_service").value).strip() or "/leader/stop_recording"
        )
        self.recorder_service_wait_sec = max(float(self.get_parameter("recorder_service_wait_sec").value), 0.0)
        command_dump_value = str(self.get_parameter("command_dump_path").value).strip()
        self.command_dump_path = Path(command_dump_value).resolve() if command_dump_value else None
        action_feedback_value = str(self.get_parameter("action_feedback_path").value).strip()
        self.action_feedback_path = Path(action_feedback_value).resolve() if action_feedback_value else None
        action_result_value = str(self.get_parameter("action_result_path").value).strip()
        self.action_result_path = Path(action_result_value).resolve() if action_result_value else None
        self.input_path = input_path
        self.action_feedback_handle = None

        frames = load_recording(input_path)
        self.trajectory, self.summary = build_trajectory_message(
            frames,
            rate_scale=max(float(self.get_parameter("rate_scale").value), 1e-6),
            min_point_dt_sec=max(float(self.get_parameter("min_point_dt_sec").value), 0.0),
            initial_hold_sec=max(float(self.get_parameter("initial_hold_sec").value), 0.0),
            prepend_first_point_copy=bool(self.get_parameter("prepend_first_point_copy").value),
        )
        self.summary["command_mode"] = self.command_mode
        self.summary["preposition_first_point_sec"] = round(self.preposition_first_point_sec, 6)
        self.publisher = None
        self.action_client = None
        if self.command_mode == "topic":
            self.publisher = self.create_publisher(JointTrajectory, trajectory_topic, 10)
        else:
            self.action_client = ActionClient(self, FollowJointTrajectory, self.follow_joint_trajectory_action)
        self.get_logger().info(
            "leader trajectory player ready: "
            f"input_path={input_path}, trajectory_topic={trajectory_topic}, frames={self.summary['frame_count']}, "
            f"duration_sec={self.summary['total_duration_sec']}, startup_delay_sec={self.startup_delay_sec}, "
            f"settle_sec={self.settle_sec}, header_start_delay_sec={self.header_start_delay_sec}, "
            f"preposition_first_point_sec={self.preposition_first_point_sec}, "
            f"command_mode={self.command_mode}, control_recorder={self.control_recorder}, "
            f"command_dump_path={self.command_dump_path}"
        )
        self._run_once()

    def _run_once(self) -> None:
        if self.startup_delay_sec > 0.0:
            self.get_logger().info(f"waiting {self.startup_delay_sec:.2f}s before publishing trajectory")
            time.sleep(self.startup_delay_sec)

        if self.command_mode == "topic" and self.wait_for_subscribers_sec > 0.0 and self.publisher is not None:
            deadline = time.time() + self.wait_for_subscribers_sec
            while time.time() < deadline and self.publisher.get_subscription_count() <= 0:
                time.sleep(0.1)

        publish_request_ns = self.get_clock().now().nanoseconds
        header_stamp_ns = resolve_header_stamp_ns(
            now_ns=publish_request_ns,
            header_start_delay_sec=self.header_start_delay_sec,
        )
        self.trajectory.header.stamp = time_from_ns(header_stamp_ns)
        self.summary["header_start_delay_sec"] = round(self.header_start_delay_sec, 6)
        self.summary["header_stamp_offset_sec"] = round((header_stamp_ns - publish_request_ns) / 1_000_000_000.0, 6)

        if self.command_dump_path is not None:
            write_json(
                self.command_dump_path,
                build_command_dump(
                    self.trajectory,
                    self.summary,
                    input_path=self.input_path,
                    publish_request_ns=publish_request_ns,
                    header_start_delay_sec=self.header_start_delay_sec,
                    command_mode=self.command_mode,
                ),
            )

        recording_started = False
        try:
            if self.preposition_first_point_sec > 0.0:
                self._preposition_to_first_point()

            if self.control_recorder:
                self._call_trigger_service(self.recorder_start_service, "start recorder")
                recording_started = True

            if self.command_mode == "topic":
                assert self.publisher is not None
                self.publisher.publish(self.trajectory)
                self.get_logger().info(
                    "trajectory published: "
                    f"points={len(self.trajectory.points)}, total_duration_sec={self.summary['total_duration_sec']}, "
                    f"header_stamp_offset_sec={self.summary['header_stamp_offset_sec']}, "
                    f"duplicate_stamp_count={self.summary['duplicate_stamp_count']}, "
                    f"removed_non_monotonic_count={self.summary['removed_non_monotonic_count']}, "
                    f"adjusted_timepoint_count={self.summary['adjusted_timepoint_count']}"
                )
                time.sleep(self.summary["total_duration_sec"])
            else:
                self._execute_action_command()
        finally:
            if recording_started:
                self._call_trigger_service(self.recorder_stop_service, "stop recorder")
        if self.settle_sec > 0.0:
            time.sleep(self.settle_sec)
        self.get_logger().info("leader trajectory player finished")

    def _call_trigger_service(self, service_name: str, label: str) -> None:
        client = self.create_client(Trigger, service_name)
        try:
            if not client.wait_for_service(timeout_sec=self.recorder_service_wait_sec):
                raise TimeoutError(f"{label} service unavailable: {service_name}")
            future = client.call_async(Trigger.Request())
            rclpy.spin_until_future_complete(self, future, timeout_sec=max(self.recorder_service_wait_sec, 1.0))
            result = future.result()
            if result is None:
                raise TimeoutError(f"{label} service timed out: {service_name}")
            if not result.success:
                raise RuntimeError(f"{label} service failed: {result.message}")
            self.get_logger().info(f"{label}: {result.message}")
        finally:
            self.destroy_client(client)

    def _execute_action_command(self) -> None:
        assert self.action_client is not None
        if not self.action_client.wait_for_server(timeout_sec=self.action_server_wait_sec):
            self._write_action_runtime_error(
                error_type="action_server_unavailable",
                error_message=f"follow joint trajectory action server not available: {self.follow_joint_trajectory_action}",
            )
            raise TimeoutError(
                f"follow joint trajectory action server not available: {self.follow_joint_trajectory_action}"
            )

        if self.action_feedback_path is not None:
            self.action_feedback_path.parent.mkdir(parents=True, exist_ok=True)
            self.action_feedback_handle = self.action_feedback_path.open("w", encoding="utf-8")

        goal = FollowJointTrajectory.Goal()
        goal.trajectory = self.trajectory
        goal.goal_time_tolerance = duration_from_sec(self.goal_time_tolerance_sec)

        send_goal_future = self.action_client.send_goal_async(goal, feedback_callback=self._on_action_feedback)
        rclpy.spin_until_future_complete(self, send_goal_future, timeout_sec=max(self.action_server_wait_sec, 1.0))
        goal_handle = send_goal_future.result()
        if goal_handle is None:
            self._close_action_feedback_handle()
            self._write_action_runtime_error(
                error_type="goal_response_missing",
                error_message="follow joint trajectory goal response future returned None",
            )
            raise RuntimeError("follow joint trajectory goal response future returned None")
        if not goal_handle.accepted:
            self._close_action_feedback_handle()
            self._write_action_runtime_error(
                error_type="goal_rejected",
                error_message="follow joint trajectory goal was rejected",
                goal_status=GoalStatus.STATUS_UNKNOWN,
            )
            raise RuntimeError("follow joint trajectory goal was rejected")

        self.get_logger().info(
            "follow joint trajectory goal accepted: "
            f"action_name={self.follow_joint_trajectory_action}, points={len(self.trajectory.points)}, "
            f"total_duration_sec={self.summary['total_duration_sec']}"
        )
        result_timeout_sec = self.action_result_timeout_sec
        if result_timeout_sec <= 0.0:
            result_timeout_sec = max(self.summary["total_duration_sec"] + self.settle_sec + 10.0, 10.0)
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=result_timeout_sec)
        wrapped_result = result_future.result()
        if wrapped_result is None:
            self._close_action_feedback_handle()
            self._write_action_runtime_error(
                error_type="result_timeout",
                error_message=(
                    f"follow joint trajectory result timed out after {result_timeout_sec:.2f}s: "
                    f"{self.follow_joint_trajectory_action}"
                ),
                goal_status=GoalStatus.STATUS_EXECUTING,
            )
            raise TimeoutError(
                f"follow joint trajectory result timed out after {result_timeout_sec:.2f}s: "
                f"{self.follow_joint_trajectory_action}"
            )

        result_payload = build_action_result_payload(
            action_name=self.follow_joint_trajectory_action,
            goal_status=int(wrapped_result.status),
            goal_result=wrapped_result.result,
            joint_names=list(self.trajectory.joint_names),
            summary=self.summary,
        )
        if self.action_result_path is not None:
            write_json(self.action_result_path, result_payload)
        self._close_action_feedback_handle()
        self.get_logger().info(
            "follow joint trajectory result: "
            f"status={result_payload['goal_status_label']}, "
            f"error_code={result_payload['result']['error_code']}, "
            f"error_string={result_payload['result']['error_string']!r}"
        )
    def _preposition_to_first_point(self) -> None:
        if not self.trajectory.points:
            return
        preposition = JointTrajectory()
        preposition.joint_names = list(self.trajectory.joint_names)
        point = JointTrajectoryPoint()
        point.positions = list(self.trajectory.points[0].positions)
        if self.trajectory.points[0].velocities:
            point.velocities = [0.0 for _ in self.trajectory.points[0].velocities]
        point.time_from_start = duration_from_sec(self.preposition_first_point_sec)
        preposition.points.append(point)
        self.get_logger().info(
            "prepositioning to first trajectory point: "
            f"duration_sec={self.preposition_first_point_sec}, command_mode={self.command_mode}"
        )
        if self.command_mode == "topic":
            assert self.publisher is not None
            self.publisher.publish(preposition)
            time.sleep(self.preposition_first_point_sec + 0.2)
            return
        self._send_action_trajectory(preposition, result_timeout_sec=self.preposition_first_point_sec + 5.0)

    def _on_action_feedback(self, feedback: Any) -> None:
        if self.action_feedback_handle is None:
            return
        payload = build_action_feedback_payload(
            feedback.feedback,
            joint_names=list(self.trajectory.joint_names),
        )
        self.action_feedback_handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.action_feedback_handle.flush()

    def _close_action_feedback_handle(self) -> None:
        if self.action_feedback_handle is None or self.action_feedback_handle.closed:
            return
        self.action_feedback_handle.flush()
        self.action_feedback_handle.close()

    def _write_action_runtime_error(
        self,
        *,
        error_type: str,
        error_message: str,
        goal_status: int = GoalStatus.STATUS_UNKNOWN,
    ) -> None:
        if self.action_result_path is None:
            return
        write_json(
            self.action_result_path,
            build_action_runtime_error_payload(
                action_name=self.follow_joint_trajectory_action,
                joint_names=list(self.trajectory.joint_names),
                summary=self.summary,
                error_type=error_type,
                error_message=error_message,
                goal_status=goal_status,
            ),
        )

    def _send_action_trajectory(
        self,
        trajectory: JointTrajectory,
        *,
        result_timeout_sec: float,
    ) -> Any:
        assert self.action_client is not None
        if not self.action_client.wait_for_server(timeout_sec=self.action_server_wait_sec):
            raise TimeoutError(
                f"follow joint trajectory action server not available: {self.follow_joint_trajectory_action}"
            )
        goal = FollowJointTrajectory.Goal()
        goal.trajectory = trajectory
        goal.goal_time_tolerance = duration_from_sec(self.goal_time_tolerance_sec)
        send_goal_future = self.action_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_goal_future, timeout_sec=max(self.action_server_wait_sec, 1.0))
        goal_handle = send_goal_future.result()
        if goal_handle is None:
            raise RuntimeError("follow joint trajectory goal response future returned None")
        if not goal_handle.accepted:
            raise RuntimeError("follow joint trajectory goal was rejected")
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=max(result_timeout_sec, 1.0))
        wrapped_result = result_future.result()
        if wrapped_result is None:
            raise TimeoutError(
                f"follow joint trajectory result timed out after {result_timeout_sec:.2f}s: "
                f"{self.follow_joint_trajectory_action}"
            )
        return wrapped_result

    def close(self) -> None:
        self._close_action_feedback_handle()


def safe_shutdown() -> None:
    try:
        if rclpy.ok():
            rclpy.shutdown()
    except Exception:
        pass


def main() -> None:
    rclpy.init()
    node: LeaderRecordingTrajectoryPlayer | None = None
    try:
        node = LeaderRecordingTrajectoryPlayer()
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.close()
            node.destroy_node()
        safe_shutdown()


if __name__ == "__main__":
    main()
