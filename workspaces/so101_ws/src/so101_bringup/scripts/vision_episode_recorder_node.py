#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image, JointState
from std_msgs.msg import String


DEFAULT_OUTPUT_DIR = "docs/generated/vision-episodes"


def discover_workspace_root(start_path: Path | None = None) -> Path:
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

    return Path(start_path or __file__).resolve().parents[3]


def timestamp_slug(now: datetime | None = None) -> str:
    current = now or datetime.now().astimezone()
    return current.strftime("%Y%m%d-%H%M%S")


def sanitize_episode_id(value: str) -> str:
    text = value.strip()
    if not text:
        text = f"vision_episode_{timestamp_slug()}"
    safe = "".join(ch if (ch.isalnum() or ch in {"_", "-"}) else "_" for ch in text).strip("_")
    return safe or f"vision_episode_{timestamp_slug()}"


def allocate_episode_dir(output_dir: Path, episode_id: str) -> Path:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    base = root / sanitize_episode_id(episode_id)
    if not base.exists():
        base.mkdir(parents=True)
        return base
    for suffix in range(1, 1_000):
        candidate = root / f"{base.name}-{suffix:02d}"
        if not candidate.exists():
            candidate.mkdir(parents=True)
            return candidate
    raise RuntimeError(f"failed to allocate vision episode dir for {episode_id}")


def stamp_ns_from_msg(msg: Any) -> int:
    stamp = getattr(getattr(msg, "header", None), "stamp", None)
    if stamp is None:
        return 0
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


def decode_string_payload(msg: String) -> Any:
    try:
        return json.loads(msg.data)
    except json.JSONDecodeError:
        return {"raw": msg.data}


def build_string_event(stream: str, msg: String) -> dict[str, Any]:
    return {
        "stream": stream,
        "received_wall_ms": int(time.time() * 1000),
        "payload": decode_string_payload(msg),
    }


def build_joint_state_event(msg: JointState) -> dict[str, Any]:
    return {
        "stream": "joint_states",
        "received_wall_ms": int(time.time() * 1000),
        "stamp_ns": stamp_ns_from_msg(msg),
        "joint_names": list(msg.name),
        "positions": [float(value) for value in msg.position],
        "velocities": [float(value) for value in msg.velocity],
        "efforts": [float(value) for value in msg.effort],
    }


def build_image_event(msg: Image, *, snapshot_path: str | None = None) -> dict[str, Any]:
    return {
        "stream": "image",
        "received_wall_ms": int(time.time() * 1000),
        "stamp_ns": stamp_ns_from_msg(msg),
        "frame_id": str(msg.header.frame_id),
        "height": int(msg.height),
        "width": int(msg.width),
        "encoding": str(msg.encoding),
        "step": int(msg.step),
        "snapshot_path": snapshot_path,
    }


def parse_required_streams(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def required_streams_ready(
    *,
    required_streams: set[str],
    last_stream_wall_ms: dict[str, int],
    now_wall_ms: int,
    max_stream_age_sec: float,
) -> tuple[bool, list[str]]:
    missing_or_stale = []
    max_age_ms = int(max_stream_age_sec * 1000)
    for stream in sorted(required_streams):
        wall_ms = int(last_stream_wall_ms.get(stream) or 0)
        if not wall_ms:
            missing_or_stale.append(f"{stream}:missing")
        elif max_age_ms > 0 and now_wall_ms - wall_ms > max_age_ms:
            missing_or_stale.append(f"{stream}:stale")
    return not missing_or_stale, missing_or_stale


@dataclass
class EpisodeStats:
    started_at: str
    event_counts: dict[str, int] = field(default_factory=dict)
    image_snapshot_count: int = 0
    first_event_wall_ms: int = 0
    last_event_wall_ms: int = 0

    def mark(self, stream: str, wall_ms: int) -> None:
        self.event_counts[stream] = self.event_counts.get(stream, 0) + 1
        if not self.first_event_wall_ms:
            self.first_event_wall_ms = wall_ms
        self.last_event_wall_ms = wall_ms


def build_manifest(
    *,
    episode_id: str,
    episode_dir: Path,
    events_path: Path,
    stats: EpisodeStats,
    topics: dict[str, str],
    stopped_at: str,
) -> dict[str, Any]:
    duration_sec = 0.0
    if stats.first_event_wall_ms and stats.last_event_wall_ms >= stats.first_event_wall_ms:
        duration_sec = (stats.last_event_wall_ms - stats.first_event_wall_ms) / 1000.0
    return {
        "schema": "so101_vision_episode_v1",
        "episode_id": episode_id,
        "episode_dir": str(episode_dir),
        "events_path": str(events_path),
        "started_at": stats.started_at,
        "stopped_at": stopped_at,
        "duration_sec": round(duration_sec, 3),
        "event_counts": dict(stats.event_counts),
        "image_snapshot_count": stats.image_snapshot_count,
        "topics": dict(topics),
    }


class VisionEpisodeRecorder(Node):
    def __init__(self) -> None:
        super().__init__("vision_episode_recorder")
        workspace_root = discover_workspace_root(Path(__file__))

        self.declare_parameter("episode_id", "")
        self.declare_parameter("output_dir", str(workspace_root / DEFAULT_OUTPUT_DIR))
        self.declare_parameter("image_topic", "/camera/color/image_raw")
        self.declare_parameter("detections_topic", "/detections")
        self.declare_parameter("vision_targets_topic", "/vision/targets")
        self.declare_parameter("task_status_topic", "/mes_task_status")
        self.declare_parameter("joint_states_topic", "/joint_states")
        self.declare_parameter("benchmark_result_topic", "/sim_grasp/benchmark_result")
        self.declare_parameter("record_images", True)
        self.declare_parameter("image_snapshot_every_n", 30)
        self.declare_parameter("max_image_snapshots", 20)
        self.declare_parameter("snapshot_required_streams", "detections,vision_targets,joint_states")
        self.declare_parameter("snapshot_max_stream_age_sec", 0.75)
        self.declare_parameter("duration_sec", 0.0)

        self.episode_id = sanitize_episode_id(str(self.get_parameter("episode_id").value))
        output_dir = Path(str(self.get_parameter("output_dir").value))
        self.episode_dir = allocate_episode_dir(output_dir, self.episode_id)
        self.events_path = self.episode_dir / "events.jsonl"
        self.manifest_path = self.episode_dir / "manifest.json"
        self.images_dir = self.episode_dir / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.record_images = bool(self.get_parameter("record_images").value)
        self.image_snapshot_every_n = max(int(self.get_parameter("image_snapshot_every_n").value), 1)
        self.max_image_snapshots = max(int(self.get_parameter("max_image_snapshots").value), 0)
        self.snapshot_required_streams = parse_required_streams(str(self.get_parameter("snapshot_required_streams").value))
        self.snapshot_max_stream_age_sec = max(float(self.get_parameter("snapshot_max_stream_age_sec").value), 0.0)
        self.duration_sec = max(float(self.get_parameter("duration_sec").value), 0.0)

        self._bridge = CvBridge()
        self._image_event_count = 0
        self._last_stream_wall_ms: dict[str, int] = {}
        self._last_snapshot_skip_reason = ""
        self._handle = self.events_path.open("w", encoding="utf-8", buffering=1)
        self._stats = EpisodeStats(started_at=datetime.now().astimezone().isoformat(timespec="seconds"))

        self.topics = {
            "image": str(self.get_parameter("image_topic").value),
            "detections": str(self.get_parameter("detections_topic").value),
            "vision_targets": str(self.get_parameter("vision_targets_topic").value),
            "task_status": str(self.get_parameter("task_status_topic").value),
            "joint_states": str(self.get_parameter("joint_states_topic").value),
            "benchmark_result": str(self.get_parameter("benchmark_result_topic").value),
        }

        self.create_subscription(Image, self.topics["image"], self._on_image, 10)
        self.create_subscription(String, self.topics["detections"], lambda msg: self._write_event(build_string_event("detections", msg)), 50)
        self.create_subscription(String, self.topics["vision_targets"], lambda msg: self._write_event(build_string_event("vision_targets", msg)), 50)
        self.create_subscription(String, self.topics["task_status"], lambda msg: self._write_event(build_string_event("task_status", msg)), 50)
        self.create_subscription(JointState, self.topics["joint_states"], lambda msg: self._write_event(build_joint_state_event(msg)), 50)
        self.create_subscription(String, self.topics["benchmark_result"], lambda msg: self._write_event(build_string_event("benchmark_result", msg)), 50)

        if self.duration_sec > 0:
            self.create_timer(self.duration_sec, self._stop_after_duration)

        self.get_logger().info(f"vision episode recorder ready: episode_dir={self.episode_dir}")

    def _write_event(self, event: dict[str, Any]) -> None:
        wall_ms = int(event.get("received_wall_ms") or time.time() * 1000)
        stream = str(event.get("stream") or "unknown")
        self._stats.mark(stream, wall_ms)
        self._last_stream_wall_ms[stream] = wall_ms
        self._handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _on_image(self, msg: Image) -> None:
        self._image_event_count += 1
        snapshot_path = None
        now_wall_ms = int(time.time() * 1000)
        streams_ready, skip_reasons = required_streams_ready(
            required_streams=self.snapshot_required_streams,
            last_stream_wall_ms=self._last_stream_wall_ms,
            now_wall_ms=now_wall_ms,
            max_stream_age_sec=self.snapshot_max_stream_age_sec,
        )
        should_snapshot = (
            self.record_images
            and self.max_image_snapshots > 0
            and self._image_event_count % self.image_snapshot_every_n == 0
            and self._stats.image_snapshot_count < self.max_image_snapshots
            and streams_ready
        )
        if not streams_ready and self._image_event_count % self.image_snapshot_every_n == 0:
            reason = ",".join(skip_reasons)
            if reason != self._last_snapshot_skip_reason:
                self.get_logger().info(f"skipping image snapshot until required streams are ready: {reason}")
                self._last_snapshot_skip_reason = reason
        if should_snapshot:
            try:
                image = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
                filename = f"frame-{self._image_event_count:06d}.jpg"
                path = self.images_dir / filename
                cv2.imwrite(str(path), image)
                snapshot_path = str(path.relative_to(self.episode_dir))
                self._stats.image_snapshot_count += 1
            except Exception as exc:  # pragma: no cover - ROS runtime guard
                self.get_logger().warning(f"failed to save image snapshot: {exc}")
        self._write_event(build_image_event(msg, snapshot_path=snapshot_path))

    def _stop_after_duration(self) -> None:
        self.get_logger().info("vision episode duration reached; finalizing")
        self.finalize()
        rclpy.shutdown()

    def finalize(self) -> None:
        if self._handle.closed:
            return
        self._handle.flush()
        try:
            os.fsync(self._handle.fileno())
        except OSError:
            pass
        self._handle.close()
        manifest = build_manifest(
            episode_id=self.episode_id,
            episode_dir=self.episode_dir,
            events_path=self.events_path,
            stats=self._stats,
            topics=self.topics,
            stopped_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        self.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    rclpy.init()
    node = VisionEpisodeRecorder()
    try:
        rclpy.spin(node)
    finally:
        node.finalize()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
