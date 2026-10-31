#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import rclpy
from control_msgs.msg import JointTrajectoryControllerState
from rclpy.node import Node


def point_to_dict(point: Any) -> dict[str, Any]:
    return {
        "positions": [float(value) for value in point.positions],
        "velocities": [float(value) for value in point.velocities],
        "accelerations": [float(value) for value in point.accelerations],
        "effort": [float(value) for value in point.effort],
        "time_from_start_sec": float(point.time_from_start.sec) + float(point.time_from_start.nanosec) / 1_000_000_000.0,
    }


def build_state_payload(msg: JointTrajectoryControllerState) -> dict[str, Any]:
    stamp_ns = int(msg.header.stamp.sec) * 1_000_000_000 + int(msg.header.stamp.nanosec)
    return {
        "stamp_ns": stamp_ns,
        "joint_names": [str(value) for value in msg.joint_names],
        "reference": point_to_dict(msg.reference),
        "feedback": point_to_dict(msg.feedback),
        "error": point_to_dict(msg.error),
        "output": point_to_dict(msg.output),
    }


class JointTrajectoryControllerStateRecorder(Node):
    def __init__(self) -> None:
        super().__init__("joint_trajectory_controller_state_recorder")

        self.declare_parameter("input_topic", "/joint_trajectory_controller/controller_state")
        self.declare_parameter("output_path", "")
        self.declare_parameter("flush_every_n_messages", 20)
        self.declare_parameter("log_every_n_messages", 100)

        output_path = Path(str(self.get_parameter("output_path").value).strip())
        if not output_path:
            raise ValueError("output_path is required")

        self.input_topic = str(self.get_parameter("input_topic").value).strip() or "/joint_trajectory_controller/controller_state"
        self.output_path = output_path.resolve()
        self.flush_every_n_messages = max(int(self.get_parameter("flush_every_n_messages").value), 1)
        self.log_every_n_messages = max(int(self.get_parameter("log_every_n_messages").value), 1)

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_handle = self.output_path.open("w", encoding="utf-8")
        self.message_count = 0
        self.first_stamp_ns: int | None = None
        self.last_stamp_ns: int | None = None
        self.joint_names: list[str] | None = None

        self.subscription = self.create_subscription(
            JointTrajectoryControllerState,
            self.input_topic,
            self._on_message,
            20,
        )
        self.get_logger().info(
            "joint trajectory controller state recorder ready: "
            f"input_topic={self.input_topic}, output_path={self.output_path}"
        )

    def _on_message(self, msg: JointTrajectoryControllerState) -> None:
        payload = build_state_payload(msg)
        self.file_handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.message_count += 1
        self.last_stamp_ns = int(payload["stamp_ns"])
        if self.first_stamp_ns is None:
            self.first_stamp_ns = self.last_stamp_ns
            self.joint_names = list(payload["joint_names"])
        if self.message_count % self.flush_every_n_messages == 0:
            self.file_handle.flush()
        if self.message_count % self.log_every_n_messages == 0:
            self.get_logger().info(
                "controller state recording: "
                f"messages={self.message_count}, duration_sec={self.duration_sec():.3f}"
            )

    def duration_sec(self) -> float:
        if self.first_stamp_ns is None or self.last_stamp_ns is None:
            return 0.0
        return max((self.last_stamp_ns - self.first_stamp_ns) / 1_000_000_000.0, 0.0)

    def close(self) -> None:
        if self.file_handle.closed:
            return
        self.file_handle.flush()
        self.file_handle.close()
        meta = {
            "schema_version": "joint_trajectory_controller_state_recorder.v1",
            "output_path": str(self.output_path),
            "input_topic": self.input_topic,
            "message_count": self.message_count,
            "first_stamp_ns": self.first_stamp_ns,
            "last_stamp_ns": self.last_stamp_ns,
            "duration_sec": round(self.duration_sec(), 6),
            "joint_names": self.joint_names or [],
        }
        self.output_path.with_suffix(".meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def safe_shutdown() -> None:
    try:
        if rclpy.ok():
            rclpy.shutdown()
    except Exception:
        pass


def main() -> None:
    rclpy.init()
    node: JointTrajectoryControllerStateRecorder | None = None
    try:
        node = JointTrajectoryControllerStateRecorder()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.close()
            node.destroy_node()
        safe_shutdown()


if __name__ == "__main__":
    main()
