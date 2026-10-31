#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import rclpy
from builtin_interfaces.msg import Time
from rclpy.node import Node
from sensor_msgs.msg import JointState


@dataclass(frozen=True)
class ReplayFrame:
    stamp_ns: int
    joint_names: list[str]
    positions: list[float]
    velocities: list[float]
    efforts: list[float]


def load_recording(path: Path) -> list[ReplayFrame]:
    frames: list[ReplayFrame] = []
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        joint_names = [str(value) for value in payload["joint_names"]]
        positions = [float(value) for value in payload["positions"]]
        velocities = [float(value) for value in payload.get("velocities", [])]
        efforts = [float(value) for value in payload.get("efforts", [])]
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
        if efforts and len(efforts) != len(joint_names):
            raise ValueError(
                f"{path}:{line_no}: efforts length mismatch: expected {len(joint_names)}, got {len(efforts)}"
            )
        frames.append(
            ReplayFrame(
                stamp_ns=int(payload["stamp_ns"]),
                joint_names=joint_names,
                positions=positions,
                velocities=velocities,
                efforts=efforts,
            )
        )
    if not frames:
        raise ValueError(f"no replayable frames found in {path}")
    return frames


def discover_workspace_root(start_path: Optional[Path] = None) -> Path:
    search_roots: list[Path] = []
    for candidate in (start_path, Path.cwd()):
        if candidate is None:
            continue
        resolved = Path(candidate).resolve()
        search_roots.append(resolved)
        search_roots.extend(resolved.parents)

    for candidate in search_roots:
        if (candidate / "AGENTS.md").is_file() and (candidate / "docs").is_dir() and (candidate / "src").is_dir():
            return candidate

    resolved = Path(start_path or __file__).resolve()
    return resolved.parents[3]


def default_recording_path(start_path: Optional[Path] = None) -> Path:
    recordings_dir = discover_workspace_root(start_path) / "docs" / "generated" / "leader-recordings"
    candidates = sorted(recordings_dir.glob("leader-recording-*.jsonl"))
    if not candidates:
        raise FileNotFoundError(f"no leader recording jsonl found in {recordings_dir}")
    return candidates[-1]


def compute_inter_frame_delay_sec(previous_stamp_ns: int, current_stamp_ns: int, rate_scale: float) -> float:
    if rate_scale <= 0.0:
        raise ValueError(f"rate_scale must be positive, got {rate_scale}")
    raw_delay = (current_stamp_ns - previous_stamp_ns) / 1_000_000_000.0
    if raw_delay <= 0.0:
        return 0.0
    return raw_delay / rate_scale


def build_joint_state_message(frame: ReplayFrame, stamp_mode: str, now_ns: int) -> JointState:
    msg = JointState()
    stamp_ns = now_ns if stamp_mode == "now" else frame.stamp_ns
    msg.header.stamp = Time(sec=stamp_ns // 1_000_000_000, nanosec=stamp_ns % 1_000_000_000)
    msg.name = list(frame.joint_names)
    msg.position = list(frame.positions)
    msg.velocity = list(frame.velocities)
    msg.effort = list(frame.efforts)
    return msg


class LeaderRecordingReplay(Node):
    def __init__(self) -> None:
        super().__init__("leader_recording_replay")

        try:
            default_input_path = str(default_recording_path(Path(__file__)))
        except FileNotFoundError:
            default_input_path = ""

        self.declare_parameter("input_path", default_input_path)
        self.declare_parameter("output_topic", "/leader/joint_states")
        self.declare_parameter("loop", False)
        self.declare_parameter("rate_scale", 1.0)
        self.declare_parameter("startup_delay_sec", 1.0)
        self.declare_parameter("stamp_mode", "now")

        input_path = Path(str(self.get_parameter("input_path").value).strip())
        output_topic = str(self.get_parameter("output_topic").value).strip() or "/leader/joint_states"
        self.loop = bool(self.get_parameter("loop").value)
        self.rate_scale = float(self.get_parameter("rate_scale").value)
        self.startup_delay_sec = max(float(self.get_parameter("startup_delay_sec").value), 0.0)
        self.stamp_mode = str(self.get_parameter("stamp_mode").value).strip() or "now"

        if self.stamp_mode not in {"now", "original"}:
            raise ValueError(f"stamp_mode must be 'now' or 'original', got {self.stamp_mode}")
        if not input_path:
            raise ValueError("input_path is required")
        if not input_path.is_file():
            raise FileNotFoundError(f"input_path not found: {input_path}")

        self.frames = load_recording(input_path)
        self.publisher = self.create_publisher(JointState, output_topic, 20)
        self.get_logger().info(
            "leader recording replay ready: "
            f"input_path={input_path}, output_topic={output_topic}, frames={len(self.frames)}, "
            f"loop={self.loop}, rate_scale={self.rate_scale}, startup_delay_sec={self.startup_delay_sec}, "
            f"stamp_mode={self.stamp_mode}"
        )
        self._run_replay()

    def _run_replay(self) -> None:
        if self.startup_delay_sec > 0.0:
            self.get_logger().info(f"waiting {self.startup_delay_sec:.2f}s before replay")
            time.sleep(self.startup_delay_sec)

        cycles = 0
        while rclpy.ok():
            cycles += 1
            self.get_logger().info(f"starting replay cycle {cycles}")
            self._publish_cycle(self.frames)
            self.get_logger().info(f"replay cycle {cycles} finished")
            if not self.loop:
                break

        self.get_logger().info("leader recording replay finished")

    def _publish_cycle(self, frames: Iterable[ReplayFrame]) -> None:
        previous_stamp_ns: Optional[int] = None
        for index, frame in enumerate(frames, start=1):
            if previous_stamp_ns is not None:
                delay_sec = compute_inter_frame_delay_sec(previous_stamp_ns, frame.stamp_ns, self.rate_scale)
                if delay_sec > 0.0:
                    time.sleep(delay_sec)
            now_ns = self.get_clock().now().nanoseconds
            self.publisher.publish(build_joint_state_message(frame, self.stamp_mode, now_ns))
            previous_stamp_ns = frame.stamp_ns
            if index == 1 or index % 100 == 0 or index == len(self.frames):
                self.get_logger().info(f"leader recording replay progress: frame={index}/{len(self.frames)}")


def safe_shutdown() -> None:
    try:
        if rclpy.ok():
            rclpy.shutdown()
    except Exception:
        pass


def main() -> None:
    rclpy.init()
    node: Optional[LeaderRecordingReplay] = None
    try:
        node = LeaderRecordingReplay()
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        safe_shutdown()


if __name__ == "__main__":
    main()
