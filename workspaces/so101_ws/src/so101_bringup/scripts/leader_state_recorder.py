#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_srvs.srv import Trigger

START_RECORDING_SERVICE = "/leader/start_recording"
STOP_RECORDING_SERVICE = "/leader/stop_recording"
RECORDING_STATUS_SERVICE = "/leader/recording_status"
DEFAULT_POSITION_ABS_LIMIT_RAD = 6.4
DEFAULT_POSITION_SPIKE_THRESHOLD_RAD = 0.35


class FrameValidationError(ValueError):
    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = str(reason)


def _timestamp_slug(now: Optional[datetime] = None) -> str:
    current = now or datetime.now().astimezone()
    return current.strftime("%Y%m%d-%H%M%S")


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


def default_recordings_dir(start_path: Optional[Path] = None) -> Path:
    return discover_workspace_root(start_path) / "docs" / "generated" / "leader-recordings"


def build_recording_file_path(output_dir: Path, slug: str) -> Path:
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    base = output_dir / f"leader-recording-{slug}.jsonl"
    if not base.exists():
        return base
    for suffix in range(1, 1_000):
        candidate = output_dir / f"leader-recording-{slug}-{suffix:02d}.jsonl"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"failed to allocate recording path for slug '{slug}' in {output_dir}")


def build_metadata_file_path(recording_path: Path) -> Path:
    return Path(recording_path).with_suffix(".meta.json")


def _ensure_finite(values: list[float], field_name: str) -> None:
    for index, value in enumerate(values):
        if not math.isfinite(value):
            raise FrameValidationError(
                f"{field_name}_non_finite",
                f"{field_name}[{index}] is not finite: {value}",
            )


def _sanitize_optional_numeric_field(values: list[float], *, sanitize_non_finite: bool) -> list[float]:
    if not values:
        return []
    if sanitize_non_finite and any(not math.isfinite(value) for value in values):
        return []
    return values


def validate_joint_state_message(
    msg: JointState,
    *,
    position_abs_limit_rad: float = DEFAULT_POSITION_ABS_LIMIT_RAD,
    sanitize_non_finite_auxiliary_fields: bool = False,
) -> tuple[list[str], list[float], list[float], list[float]]:
    joint_names = [str(value) for value in msg.name]
    positions = [float(value) for value in msg.position]
    velocities = [float(value) for value in msg.velocity]
    efforts = [float(value) for value in msg.effort]

    if not joint_names:
        raise FrameValidationError("joint_names_empty", "joint_names is empty")
    if len(positions) != len(joint_names):
        raise FrameValidationError(
            "positions_length_mismatch",
            f"positions length mismatch: expected {len(joint_names)}, got {len(positions)}"
        )
    if velocities and len(velocities) != len(joint_names):
        raise FrameValidationError(
            "velocities_length_mismatch",
            f"velocities length mismatch: expected {len(joint_names)}, got {len(velocities)}"
        )
    if efforts and len(efforts) != len(joint_names):
        raise FrameValidationError(
            "efforts_length_mismatch",
            f"efforts length mismatch: expected {len(joint_names)}, got {len(efforts)}"
        )

    _ensure_finite(positions, "positions")
    velocities = _sanitize_optional_numeric_field(
        velocities,
        sanitize_non_finite=sanitize_non_finite_auxiliary_fields,
    )
    efforts = _sanitize_optional_numeric_field(
        efforts,
        sanitize_non_finite=sanitize_non_finite_auxiliary_fields,
    )
    _ensure_finite(velocities, "velocities")
    _ensure_finite(efforts, "efforts")
    if any(abs(value) > position_abs_limit_rad for value in positions):
        raise FrameValidationError(
            "position_limit_violation",
            f"positions exceed +/-{position_abs_limit_rad} rad heuristic limit",
        )

    return joint_names, positions, velocities, efforts


def build_frame_payload(
    msg: JointState,
    *,
    position_abs_limit_rad: float = DEFAULT_POSITION_ABS_LIMIT_RAD,
    sanitize_non_finite_auxiliary_fields: bool = False,
) -> Dict[str, Any]:
    stamp = msg.header.stamp
    stamp_ns = int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)
    joint_names, positions, velocities, efforts = validate_joint_state_message(
        msg,
        position_abs_limit_rad=position_abs_limit_rad,
        sanitize_non_finite_auxiliary_fields=sanitize_non_finite_auxiliary_fields,
    )
    return {
        "stamp_ns": stamp_ns,
        "joint_names": joint_names,
        "positions": positions,
        "velocities": velocities,
        "efforts": efforts,
    }


@dataclass
class RecordingSession:
    slug: str
    path: Path
    metadata_path: Path
    started_at_sec: float
    started_at_iso: str
    frame_count: int = 0
    first_stamp_ns: int = 0
    last_stamp_ns: int = 0
    invalid_frame_count: int = 0
    non_monotonic_stamp_count: int = 0
    duplicate_stamp_count: int = 0
    backward_stamp_count: int = 0
    joint_name_mismatch_count: int = 0
    invalid_reason_counts: Optional[Dict[str, int]] = None
    joint_names: Optional[list[str]] = None
    frame_interval_count: int = 0
    frame_interval_sum_sec: float = 0.0
    frame_interval_min_sec: float = 0.0
    frame_interval_max_sec: float = 0.0
    large_interval_count: int = 0
    position_min_by_joint: Optional[list[float]] = None
    position_max_by_joint: Optional[list[float]] = None
    total_motion_by_joint: Optional[list[float]] = None
    max_step_by_joint: Optional[list[float]] = None
    previous_positions: Optional[list[float]] = None
    static_transition_count: int = 0
    active_transition_count: int = 0
    position_spike_frame_count: int = 0


def record_invalid_reason(session: RecordingSession, reason: str) -> None:
    if session.invalid_reason_counts is None:
        session.invalid_reason_counts = {}
    session.invalid_reason_counts[reason] = session.invalid_reason_counts.get(reason, 0) + 1


def update_position_extrema(session: RecordingSession, positions: list[float]) -> None:
    if session.position_min_by_joint is None or session.position_max_by_joint is None:
        session.position_min_by_joint = list(positions)
        session.position_max_by_joint = list(positions)
        return

    for index, value in enumerate(positions):
        session.position_min_by_joint[index] = min(session.position_min_by_joint[index], value)
        session.position_max_by_joint[index] = max(session.position_max_by_joint[index], value)


def update_interval_metrics(session: RecordingSession, stamp_ns: int, large_gap_threshold_sec: float) -> None:
    if not session.last_stamp_ns:
        return

    delta_sec = (stamp_ns - session.last_stamp_ns) / 1_000_000_000.0
    if delta_sec <= 0.0:
        return

    session.frame_interval_count += 1
    session.frame_interval_sum_sec += delta_sec
    if session.frame_interval_count == 1:
        session.frame_interval_min_sec = delta_sec
        session.frame_interval_max_sec = delta_sec
    else:
        session.frame_interval_min_sec = min(session.frame_interval_min_sec, delta_sec)
        session.frame_interval_max_sec = max(session.frame_interval_max_sec, delta_sec)

    if delta_sec > large_gap_threshold_sec:
        session.large_interval_count += 1


def update_motion_metrics(session: RecordingSession, positions: list[float], motion_epsilon_rad: float) -> list[float]:
    update_position_extrema(session, positions)

    if session.total_motion_by_joint is None:
        session.total_motion_by_joint = [0.0 for _ in positions]
    if session.max_step_by_joint is None:
        session.max_step_by_joint = [0.0 for _ in positions]

    if session.previous_positions is None:
        session.previous_positions = list(positions)
        return [0.0 for _ in positions]

    deltas = [abs(current - previous) for current, previous in zip(positions, session.previous_positions)]
    for index, delta in enumerate(deltas):
        session.total_motion_by_joint[index] += delta
        session.max_step_by_joint[index] = max(session.max_step_by_joint[index], delta)

    step_motion = sum(deltas)
    if step_motion <= motion_epsilon_rad:
        session.static_transition_count += 1
    else:
        session.active_transition_count += 1

    session.previous_positions = list(positions)
    return deltas


def build_recording_summary(
    session: RecordingSession,
    *,
    input_topic: str,
    output_dir: Path,
    flush_every_n_frames: int,
    log_every_n_frames: int,
    large_gap_threshold_sec: float,
    motion_epsilon_rad: float,
    position_abs_limit_rad: float,
    position_spike_threshold_rad: float,
    active: bool,
    stop_reason: Optional[str] = None,
    stopped_at_sec: Optional[float] = None,
    stopped_at_iso: Optional[str] = None,
    metadata_write_error: Optional[str] = None,
) -> Dict[str, Any]:
    end_sec = stopped_at_sec if stopped_at_sec is not None else time.time()
    duration_sec = max(end_sec - session.started_at_sec, 0.0)
    warnings: list[str] = []
    if session.frame_count == 0:
        warnings.append("no_frames_recorded")
    if session.invalid_frame_count:
        warnings.append("invalid_frames_detected")
    if session.joint_name_mismatch_count:
        warnings.append("joint_name_mismatch_detected")
    if session.non_monotonic_stamp_count:
        warnings.append("non_monotonic_stamps_detected")
    if session.large_interval_count:
        warnings.append("large_intervals_detected")
    if session.position_spike_frame_count:
        warnings.append("position_spikes_detected")

    sample_rate_hz = 0.0 if duration_sec <= 0.0 else round(session.frame_count / duration_sec, 3)
    sample_rate_from_stamps_hz = 0.0
    if session.frame_count > 1 and session.last_stamp_ns > session.first_stamp_ns:
        sample_rate_from_stamps_hz = round(
            (session.frame_count - 1) / ((session.last_stamp_ns - session.first_stamp_ns) / 1_000_000_000.0),
            3,
        )
    average_frame_interval_sec = (
        0.0
        if session.frame_interval_count == 0
        else round(session.frame_interval_sum_sec / session.frame_interval_count, 6)
    )
    transition_count = session.static_transition_count + session.active_transition_count
    static_transition_ratio = 0.0 if transition_count == 0 else round(session.static_transition_count / transition_count, 4)
    active_transition_ratio = 0.0 if transition_count == 0 else round(session.active_transition_count / transition_count, 4)
    joint_names = list(session.joint_names or [])
    joint_position_min = {
        joint_name: round(value, 6)
        for joint_name, value in zip(joint_names, session.position_min_by_joint or [])
    }
    joint_position_max = {
        joint_name: round(value, 6)
        for joint_name, value in zip(joint_names, session.position_max_by_joint or [])
    }
    joint_position_range = {
        joint_name: round(max_value - min_value, 6)
        for joint_name, min_value, max_value in zip(
            joint_names,
            session.position_min_by_joint or [],
            session.position_max_by_joint or [],
        )
    }
    joint_total_motion = {
        joint_name: round(value, 6)
        for joint_name, value in zip(joint_names, session.total_motion_by_joint or [])
    }
    joint_max_step = {
        joint_name: round(value, 6)
        for joint_name, value in zip(joint_names, session.max_step_by_joint or [])
    }
    total_motion_rad = round(sum(session.total_motion_by_joint or []), 6)
    max_step_rad = round(max(session.max_step_by_joint or [0.0]), 6)
    return {
        "active": active,
        "slug": session.slug,
        "path": str(session.path),
        "metadata_path": str(session.metadata_path),
        "input_topic": input_topic,
        "output_dir": str(Path(output_dir).resolve()),
        "started_at": session.started_at_iso,
        "stopped_at": stopped_at_iso,
        "duration_sec": round(duration_sec, 3),
        "frame_count": session.frame_count,
        "sample_rate_hz": sample_rate_hz,
        "sample_rate_from_stamps_hz": sample_rate_from_stamps_hz,
        "first_stamp_ns": session.first_stamp_ns,
        "last_stamp_ns": session.last_stamp_ns,
        "invalid_frame_count": session.invalid_frame_count,
        "joint_name_mismatch_count": session.joint_name_mismatch_count,
        "non_monotonic_stamp_count": session.non_monotonic_stamp_count,
        "duplicate_stamp_count": session.duplicate_stamp_count,
        "backward_stamp_count": session.backward_stamp_count,
        "large_interval_count": session.large_interval_count,
        "position_spike_frame_count": session.position_spike_frame_count,
        "joint_names": joint_names,
        "flush_every_n_frames": int(flush_every_n_frames),
        "log_every_n_frames": int(log_every_n_frames),
        "large_gap_threshold_sec": round(large_gap_threshold_sec, 6),
        "motion_epsilon_rad": round(motion_epsilon_rad, 6),
        "position_abs_limit_rad": round(position_abs_limit_rad, 6),
        "position_spike_threshold_rad": round(position_spike_threshold_rad, 6),
        "anomaly_counts": {
            "invalid_frame_count": session.invalid_frame_count,
            "joint_name_mismatch_count": session.joint_name_mismatch_count,
            "non_monotonic_stamp_count": session.non_monotonic_stamp_count,
            "duplicate_stamp_count": session.duplicate_stamp_count,
            "backward_stamp_count": session.backward_stamp_count,
            "large_interval_count": session.large_interval_count,
            "position_spike_frame_count": session.position_spike_frame_count,
        },
        "invalid_reason_counts": dict(session.invalid_reason_counts or {}),
        "frame_interval_stats": {
            "count": session.frame_interval_count,
            "avg_sec": average_frame_interval_sec,
            "min_sec": round(session.frame_interval_min_sec, 6) if session.frame_interval_count else 0.0,
            "max_sec": round(session.frame_interval_max_sec, 6) if session.frame_interval_count else 0.0,
        },
        "quality_metrics": {
            "static_transition_count": session.static_transition_count,
            "active_transition_count": session.active_transition_count,
            "static_transition_ratio": static_transition_ratio,
            "active_transition_ratio": active_transition_ratio,
            "total_motion_rad": total_motion_rad,
            "joint_position_min": joint_position_min,
            "joint_position_max": joint_position_max,
            "joint_position_range": joint_position_range,
            "joint_total_motion_rad": joint_total_motion,
            "joint_max_step_rad": joint_max_step,
            "max_step_rad": max_step_rad,
        },
        "stop_reason": stop_reason,
        "metadata_write_error": metadata_write_error,
        "warnings": warnings,
    }


def format_recording_summary(summary: Dict[str, Any]) -> str:
    state = "active" if summary.get("active") else "stopped"
    return (
        f"recording {state}: {summary['path']} "
        f"(frames={summary['frame_count']}, invalid={summary['invalid_frame_count']}, "
        f"joint_name_mismatch={summary['joint_name_mismatch_count']}, "
        f"non_monotonic={summary['non_monotonic_stamp_count']}, "
        f"duration_sec={summary['duration_sec']:.2f}, metadata={summary['metadata_path']})"
    )


class LeaderStateRecorder(Node):
    def __init__(self) -> None:
        super().__init__("leader_state_recorder")

        default_output_dir = default_recordings_dir(Path(__file__))

        self.declare_parameter("input_topic", "/leader/joint_states")
        self.declare_parameter("output_dir", str(default_output_dir))
        self.declare_parameter("flush_every_n_frames", 1)
        self.declare_parameter("log_every_n_frames", 30)
        self.declare_parameter("auto_start", False)
        self.declare_parameter("large_gap_threshold_sec", 0.1)
        self.declare_parameter("motion_epsilon_rad", 0.01)
        self.declare_parameter("position_abs_limit_rad", DEFAULT_POSITION_ABS_LIMIT_RAD)
        self.declare_parameter("position_spike_threshold_rad", DEFAULT_POSITION_SPIKE_THRESHOLD_RAD)
        self.declare_parameter("sanitize_non_finite_auxiliary_fields", False)

        self.input_topic = str(self.get_parameter("input_topic").value).strip() or "/leader/joint_states"
        self.output_dir = Path(str(self.get_parameter("output_dir").value).strip() or str(default_output_dir))
        self.flush_every_n_frames = max(int(self.get_parameter("flush_every_n_frames").value), 1)
        self.log_every_n_frames = max(int(self.get_parameter("log_every_n_frames").value), 1)
        self.auto_start = bool(self.get_parameter("auto_start").value)
        self.large_gap_threshold_sec = max(float(self.get_parameter("large_gap_threshold_sec").value), 0.0)
        self.motion_epsilon_rad = max(float(self.get_parameter("motion_epsilon_rad").value), 0.0)
        self.position_abs_limit_rad = max(float(self.get_parameter("position_abs_limit_rad").value), 0.1)
        self.position_spike_threshold_rad = max(float(self.get_parameter("position_spike_threshold_rad").value), 0.001)
        self.sanitize_non_finite_auxiliary_fields = bool(
            self.get_parameter("sanitize_non_finite_auxiliary_fields").value
        )

        self._lock = threading.Lock()
        self._session: Optional[RecordingSession] = None
        self._last_summary: Optional[Dict[str, Any]] = None
        self._handle = None

        self.subscription = self.create_subscription(JointState, self.input_topic, self._on_joint_state, 50)
        self.start_srv = self.create_service(Trigger, START_RECORDING_SERVICE, self._handle_start_recording)
        self.stop_srv = self.create_service(Trigger, STOP_RECORDING_SERVICE, self._handle_stop_recording)
        self.status_srv = self.create_service(Trigger, RECORDING_STATUS_SERVICE, self._handle_recording_status)

        self.get_logger().info(
            f"leader state recorder ready: input_topic={self.input_topic}, output_dir={self.output_dir}, "
            f"auto_start={self.auto_start}, flush_every_n_frames={self.flush_every_n_frames}, "
            f"log_every_n_frames={self.log_every_n_frames}, large_gap_threshold_sec={self.large_gap_threshold_sec}, "
            f"motion_epsilon_rad={self.motion_epsilon_rad}, position_abs_limit_rad={self.position_abs_limit_rad}, "
            f"position_spike_threshold_rad={self.position_spike_threshold_rad}, "
            f"sanitize_non_finite_auxiliary_fields={self.sanitize_non_finite_auxiliary_fields}"
        )

        if self.auto_start:
            ok, message = self._start_recording_locked()
            if ok:
                self.get_logger().info(message)
            else:
                self.get_logger().warn(message)

    def _start_recording_locked(self) -> tuple[bool, str]:
        with self._lock:
            if self._session is not None:
                return False, f"recording already active: {self._session.path}"

            slug = _timestamp_slug()
            started_at_sec = time.time()
            started_at_iso = datetime.now().astimezone().isoformat(timespec="seconds")
            try:
                path = build_recording_file_path(self.output_dir, slug)
                self._handle = path.open("w", encoding="utf-8", buffering=1)
            except (OSError, RuntimeError) as exc:
                self._handle = None
                return False, f"failed to start recording: {exc}"

            self._session = RecordingSession(
                slug=slug,
                path=path,
                metadata_path=build_metadata_file_path(path),
                started_at_sec=started_at_sec,
                started_at_iso=started_at_iso,
            )
            return True, f"recording started: {path}"

    def _status_payload_locked(self) -> Dict[str, Any]:
        if self._session is not None:
            return build_recording_summary(
                self._session,
                input_topic=self.input_topic,
                output_dir=self.output_dir,
                flush_every_n_frames=self.flush_every_n_frames,
                log_every_n_frames=self.log_every_n_frames,
                large_gap_threshold_sec=self.large_gap_threshold_sec,
                motion_epsilon_rad=self.motion_epsilon_rad,
                position_abs_limit_rad=self.position_abs_limit_rad,
                position_spike_threshold_rad=self.position_spike_threshold_rad,
                active=True,
            )
        return {
            "active": False,
            "input_topic": self.input_topic,
            "output_dir": str(self.output_dir.resolve()),
            "last_session": self._last_summary,
        }

    def _finalize_recording_locked(self, *, stop_reason: str) -> tuple[bool, str]:
        if self._session is None:
            return False, "recording is not active"

        session = self._session
        stopped_at_sec = time.time()
        stopped_at_iso = datetime.now().astimezone().isoformat(timespec="seconds")
        metadata_write_error = None

        if self._handle is not None:
            self._handle.flush()
            try:
                os.fsync(self._handle.fileno())
            except OSError:
                pass
            self._handle.close()

        summary = build_recording_summary(
            session,
            input_topic=self.input_topic,
            output_dir=self.output_dir,
            flush_every_n_frames=self.flush_every_n_frames,
            log_every_n_frames=self.log_every_n_frames,
            large_gap_threshold_sec=self.large_gap_threshold_sec,
            motion_epsilon_rad=self.motion_epsilon_rad,
            position_abs_limit_rad=self.position_abs_limit_rad,
            position_spike_threshold_rad=self.position_spike_threshold_rad,
            active=False,
            stop_reason=stop_reason,
            stopped_at_sec=stopped_at_sec,
            stopped_at_iso=stopped_at_iso,
        )

        try:
            session.metadata_path.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            metadata_write_error = str(exc)
            summary["metadata_write_error"] = metadata_write_error

        self._handle = None
        self._session = None
        self._last_summary = summary
        return True, format_recording_summary(summary)

    def _stop_recording_locked(self) -> tuple[bool, str]:
        with self._lock:
            return self._finalize_recording_locked(stop_reason="manual_stop")

    def _handle_start_recording(self, _request: Trigger.Request, response: Trigger.Response) -> Trigger.Response:
        success, message = self._start_recording_locked()
        response.success = success
        response.message = message
        if success:
            self.get_logger().info(message)
        else:
            self.get_logger().warn(message)
        return response

    def _handle_stop_recording(self, _request: Trigger.Request, response: Trigger.Response) -> Trigger.Response:
        success, message = self._stop_recording_locked()
        response.success = success
        response.message = message
        if success:
            self.get_logger().info(message)
        else:
            self.get_logger().warn(message)
        return response

    def _handle_recording_status(self, _request: Trigger.Request, response: Trigger.Response) -> Trigger.Response:
        with self._lock:
            payload = self._status_payload_locked()
        response.success = True
        response.message = json.dumps(payload, ensure_ascii=False)
        return response

    def _on_joint_state(self, msg: JointState) -> None:
        with self._lock:
            if self._session is None or self._handle is None:
                return

            try:
                payload = build_frame_payload(
                    msg,
                    position_abs_limit_rad=self.position_abs_limit_rad,
                    sanitize_non_finite_auxiliary_fields=self.sanitize_non_finite_auxiliary_fields,
                )
            except FrameValidationError as exc:
                self._session.invalid_frame_count += 1
                record_invalid_reason(self._session, exc.reason)
                if self._session.invalid_frame_count <= 3 or self._session.invalid_frame_count % 10 == 0:
                    self.get_logger().warn(f"skipping invalid leader joint_state frame: {exc}")
                return

            if self._session.joint_names is None:
                self._session.joint_names = list(payload["joint_names"])
            elif payload["joint_names"] != self._session.joint_names:
                self._session.joint_name_mismatch_count += 1
                if (
                    self._session.joint_name_mismatch_count <= 3
                    or self._session.joint_name_mismatch_count % 10 == 0
                ):
                    self.get_logger().warn(
                        "skipping frame due to joint_names mismatch: expected=%s got=%s"
                        % (self._session.joint_names, payload["joint_names"])
                    )
                return

            stamp_ns = int(payload["stamp_ns"])
            if self._session.last_stamp_ns and stamp_ns <= self._session.last_stamp_ns:
                self._session.non_monotonic_stamp_count += 1
                if stamp_ns == self._session.last_stamp_ns:
                    self._session.duplicate_stamp_count += 1
                else:
                    self._session.backward_stamp_count += 1
                if (
                    self._session.non_monotonic_stamp_count <= 3
                    or self._session.non_monotonic_stamp_count % 10 == 0
                ):
                    self.get_logger().warn(
                        "leader recording observed non-monotonic stamp: current=%s previous=%s"
                        % (stamp_ns, self._session.last_stamp_ns)
                    )

            update_interval_metrics(self._session, stamp_ns, self.large_gap_threshold_sec)
            deltas = update_motion_metrics(self._session, payload["positions"], self.motion_epsilon_rad)
            if any(delta >= self.position_spike_threshold_rad for delta in deltas):
                self._session.position_spike_frame_count += 1
            self._handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            self._session.frame_count += 1
            if self._session.frame_count == 1:
                self._session.first_stamp_ns = stamp_ns
            self._session.last_stamp_ns = stamp_ns
            if self._session.frame_count % self.flush_every_n_frames == 0:
                self._handle.flush()
            if self._session.frame_count % self.log_every_n_frames == 0:
                self.get_logger().info(
                    "leader recording progress: frames=%s path=%s last_stamp_ns=%s"
                    % (self._session.frame_count, self._session.path, self._session.last_stamp_ns)
                )

    def destroy_node(self) -> bool:
        with self._lock:
            if self._session is not None:
                success, message = self._finalize_recording_locked(stop_reason="node_shutdown")
                if success:
                    self.get_logger().info(message)
                else:
                    self.get_logger().warn(message)
            elif self._handle is not None:
                self._handle.flush()
                self._handle.close()
                self._handle = None
        return super().destroy_node()


def safe_shutdown() -> None:
    try:
        if rclpy.ok():
            rclpy.shutdown()
    except Exception:
        pass


def main() -> None:
    rclpy.init()
    node = LeaderStateRecorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        safe_shutdown()


if __name__ == "__main__":
    main()
