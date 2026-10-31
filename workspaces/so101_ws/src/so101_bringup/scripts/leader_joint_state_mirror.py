#!/usr/bin/env python3
from __future__ import annotations

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class LeaderJointStateMirror(Node):
    def __init__(self) -> None:
        super().__init__("leader_joint_state_mirror")
        self.declare_parameter("input_topic", "/leader/joint_states")
        self.declare_parameter("output_topic", "/joint_states")
        self.declare_parameter("frame_prefix", "")

        input_topic = str(self.get_parameter("input_topic").value).strip() or "/leader/joint_states"
        output_topic = str(self.get_parameter("output_topic").value).strip() or "/joint_states"
        self.frame_prefix = str(self.get_parameter("frame_prefix").value).strip()

        self.publisher = self.create_publisher(JointState, output_topic, 20)
        self.subscription = self.create_subscription(JointState, input_topic, self._on_joint_state, 20)

        self.get_logger().info(
            f"leader joint state mirror ready: input_topic={input_topic}, output_topic={output_topic}, frame_prefix={self.frame_prefix or '-'}"
        )

    def _on_joint_state(self, msg: JointState) -> None:
        mirrored = JointState()
        mirrored.header = msg.header
        mirrored.name = [
            f"{self.frame_prefix}{name}" if self.frame_prefix else name
            for name in msg.name
        ]
        mirrored.position = list(msg.position)
        mirrored.velocity = list(msg.velocity)
        mirrored.effort = list(msg.effort)
        self.publisher.publish(mirrored)


def safe_shutdown() -> None:
    try:
        if rclpy.ok():
            rclpy.shutdown()
    except Exception:
        pass


def main() -> None:
    rclpy.init()
    node = LeaderJointStateMirror()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        safe_shutdown()


if __name__ == "__main__":
    main()
