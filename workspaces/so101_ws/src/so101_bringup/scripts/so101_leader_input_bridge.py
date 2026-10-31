#!/usr/bin/env python3
from __future__ import annotations

import importlib
import inspect
import json
import math
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger


STATE_BOOTING = "BOOTING"
STATE_DISCONNECTED = "DISCONNECTED"
STATE_CALIBRATING = "CALIBRATING"
STATE_READY = "READY"
STATE_DEGRADED = "DEGRADED"
STATE_ERROR = "ERROR"

DEFAULT_JOINT_NAMES = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]

EMPTY_PARAM_SENTINEL = "__empty__"


class BridgeError(RuntimeError):
    def __init__(self, state: str, detail: str):
        super().__init__(detail)
        self.state = state
        self.detail = detail


@dataclass
class LeaderSample:
    joint_names: list[str]
    positions_rad: list[float]
    positions_raw: list[float]
    read_latency_ms: float
    source_timestamp_sec: float


@dataclass
class AdapterStatus:
    connected: bool
    calibrated: bool
    device_label: str
    backend: str


class LeaderAdapterBase:
    def connect(self) -> AdapterStatus:
        raise NotImplementedError

    def read_sample(self) -> LeaderSample:
        raise NotImplementedError

    def reload_calibration(self) -> str:
        raise NotImplementedError

    def close(self) -> None:
        return None


class UnavailableLeaderAdapter(LeaderAdapterBase):
    def __init__(self, detail: str, *, backend: str = "unavailable"):
        self.detail = detail
        self.backend = backend

    def connect(self) -> AdapterStatus:
        raise BridgeError(STATE_ERROR, self.detail)

    def read_sample(self) -> LeaderSample:
        raise BridgeError(STATE_ERROR, self.detail)

    def reload_calibration(self) -> str:
        raise BridgeError(STATE_ERROR, self.detail)


class OfficialSOLeaderAdapter(LeaderAdapterBase):
    def __init__(
        self,
        *,
        leader_type: str,
        port: str,
        calibration_path: str,
        joint_names: Sequence[str],
        positions_in_degrees: str,
    ) -> None:
        self.leader_type = leader_type
        self.port = port
        self.calibration_path = calibration_path
        self.joint_names = list(joint_names)
        self.positions_in_degrees = positions_in_degrees
        self._device = None
        self._config = None
        self._connected = False
        self._calibrated = False

    def _build_config(self):
        config_module = importlib.import_module("lerobot.teleoperators.so_leader.config_so_leader")
        config_class = getattr(config_module, "SOLeaderTeleopConfig")
        kwargs = {}
        signature = inspect.signature(config_class)
        if self.port:
            for key in ("port", "serial_port", "usb_port"):
                if key in signature.parameters:
                    kwargs[key] = self.port
                    break
        if self.calibration_path:
            for key in ("calibration_path", "calibration_file", "calibration_dir"):
                if key in signature.parameters:
                    kwargs[key] = self.calibration_path
                    break
        return config_class(**kwargs)

    def _ensure_device(self):
        if self._device is not None:
            return self._device
        leader_module = importlib.import_module("lerobot.teleoperators.so_leader.so_leader")
        leader_class = getattr(leader_module, "SOLeader")
        self._config = self._build_config()
        self._device = leader_class(self._config)
        return self._device

    def connect(self) -> AdapterStatus:
        try:
            device = self._ensure_device()
            if not self._connected:
                device.connect(calibrate=False)
                self._connected = True
            self._calibrated = True
            return AdapterStatus(
                connected=True,
                calibrated=self._calibrated,
                device_label=self.leader_type,
                backend="lerobot-official",
            )
        except Exception as exc:  # pragma: no cover - depends on local lerobot runtime
            raise BridgeError(STATE_DISCONNECTED, f"failed to connect official SOLeader: {exc}") from exc

    def _coerce_positions(self, action: Any) -> list[float]:
        payload = action
        if isinstance(payload, dict):
            for key in ("action", "joint_positions", "positions"):
                if key in payload:
                    payload = payload[key]
                    break
            else:
                if all(name in payload for name in self.joint_names):
                    payload = [payload[name] for name in self.joint_names]
                elif all(f"{name}.pos" in payload for name in self.joint_names):
                    payload = [payload[f"{name}.pos"] for name in self.joint_names]
        if hasattr(payload, "tolist"):
            payload = payload.tolist()
        if not isinstance(payload, (list, tuple)):
            raise BridgeError(STATE_DEGRADED, f"unsupported leader action payload: {type(action).__name__}")

        flat = [float(value) for value in payload]
        if len(flat) != len(self.joint_names):
            raise BridgeError(
                STATE_DEGRADED,
                f"leader action length mismatch: expected {len(self.joint_names)}, got {len(flat)}",
            )
        return flat

    def _positions_to_rad(self, values: Sequence[float]) -> list[float]:
        mode = self.positions_in_degrees
        if mode == "auto":
            mode = "true" if any(abs(value) > (2.0 * math.pi + 0.2) for value in values) else "false"
        if mode == "true":
            return [math.radians(value) for value in values]
        return [float(value) for value in values]

    def read_sample(self) -> LeaderSample:
        if not self._connected:
            raise BridgeError(STATE_DISCONNECTED, "leader device is not connected")
        started = time.time()
        try:
            action = self._device.get_action()
        except Exception as exc:  # pragma: no cover - depends on local lerobot runtime
            raise BridgeError(STATE_DEGRADED, f"failed to read leader action: {exc}") from exc
        raw_positions = self._coerce_positions(action)
        return LeaderSample(
            joint_names=list(self.joint_names),
            positions_rad=self._positions_to_rad(raw_positions),
            positions_raw=raw_positions,
            read_latency_ms=(time.time() - started) * 1000.0,
            source_timestamp_sec=time.time(),
        )

    def reload_calibration(self) -> str:
        self.close()
        self._device = None
        self._config = None
        self._connected = False
        self._calibrated = False
        self.connect()
        return "official SOLeader calibration/runtime reloaded"

    def close(self) -> None:
        if self._device is None:
            return
        try:
            self._device.disconnect()
        except Exception:  # pragma: no cover - best effort cleanup
            pass
        self._connected = False


def _coerce_joint_names(value: Sequence[Any]) -> list[str]:
    names = [str(item).strip() for item in value if str(item).strip()]
    return names or list(DEFAULT_JOINT_NAMES)


def _load_factory(factory_path: str) -> Callable[..., LeaderAdapterBase]:
    module_name, sep, attr_name = factory_path.partition(":")
    if not module_name or not sep or not attr_name:
        raise BridgeError(
            STATE_ERROR,
            "adapter_factory must use module.path:factory_name format",
        )

    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # pragma: no cover - depends on runtime env
        raise BridgeError(
            STATE_ERROR,
            f"failed to import adapter factory module '{module_name}': {exc}",
        ) from exc

    factory = getattr(module, attr_name, None)
    if factory is None or not callable(factory):
        raise BridgeError(
            STATE_ERROR,
            f"adapter factory '{factory_path}' not found or not callable",
        )
    return factory


def build_adapter(
    *,
    adapter_factory: str,
    leader_type: str,
    port: str,
    calibration_path: str,
    joint_names: Sequence[str],
    positions_in_degrees: str,
) -> LeaderAdapterBase:
    if adapter_factory:
        factory = _load_factory(adapter_factory)
        try:
            adapter = factory(
                leader_type=leader_type,
                port=port,
                calibration_path=calibration_path,
                joint_names=list(joint_names),
                positions_in_degrees=positions_in_degrees,
            )
        except Exception as exc:  # pragma: no cover - depends on plugin code
            raise BridgeError(
                STATE_ERROR,
                f"adapter factory '{adapter_factory}' failed: {exc}",
            ) from exc
        if not isinstance(adapter, LeaderAdapterBase) and not all(
            hasattr(adapter, attr) for attr in ("connect", "read_sample", "reload_calibration", "close")
        ):
            raise BridgeError(
                STATE_ERROR,
                f"adapter factory '{adapter_factory}' returned incompatible object",
            )
        return adapter

    if importlib.util.find_spec("lerobot") is None:
        return UnavailableLeaderAdapter(
            "lerobot package is not installed; configure adapter_factory or install official LeRobot runtime",
            backend="builtin-missing-lerobot",
        )

    return OfficialSOLeaderAdapter(
        leader_type=leader_type,
        port=port,
        calibration_path=calibration_path,
        joint_names=joint_names,
        positions_in_degrees=positions_in_degrees,
    )


def build_status_payload(
    *,
    state: str,
    connected: bool,
    calibrated: bool,
    publishing: bool,
    hz: float,
    last_frame_age_ms: Optional[float],
    last_error: str,
    device_label: str,
    backend: str,
) -> dict:
    return {
        "state": state,
        "connected": bool(connected),
        "calibrated": bool(calibrated),
        "publishing": bool(publishing),
        "hz": round(float(hz), 2),
        "lastFrameAgeMs": None if last_frame_age_ms is None else round(float(last_frame_age_ms), 2),
        "lastError": str(last_error or ""),
        "deviceLabel": str(device_label or "so101_leader"),
        "backend": str(backend or "unknown"),
        "timestamp": time.time(),
    }


def build_raw_state_payload(
    *,
    status: AdapterStatus,
    sample: LeaderSample,
    seq: int,
    last_error: str,
) -> dict:
    return {
        "deviceType": "so101_leader",
        "deviceLabel": status.device_label,
        "backend": status.backend,
        "connected": status.connected,
        "calibrated": status.calibrated,
        "jointNames": sample.joint_names,
        "jointPositionsRaw": sample.positions_raw,
        "jointPositionsRad": sample.positions_rad,
        "readLatencyMs": round(sample.read_latency_ms, 2),
        "frameId": "leader_base",
        "seq": seq,
        "timestamp": sample.source_timestamp_sec,
        "lastError": str(last_error or ""),
    }


class SO101LeaderInputBridge(Node):
    def __init__(self) -> None:
        super().__init__("so101_leader_input_bridge")

        self.declare_parameter("leader_type", "so101_leader")
        self.declare_parameter("port", "")
        self.declare_parameter("publish_rate_hz", 30.0)
        self.declare_parameter("joint_names", list(DEFAULT_JOINT_NAMES))
        self.declare_parameter("calibration_path", "")
        self.declare_parameter("raw_state_enabled", True)
        self.declare_parameter("status_topic_enabled", True)
        self.declare_parameter("adapter_factory", "")
        self.declare_parameter("degraded_latency_ms", 120.0)
        self.declare_parameter("positions_in_degrees", "auto")

        self.leader_type = self._normalize_text_param(self.get_parameter("leader_type").value)
        self.port = self._normalize_text_param(self.get_parameter("port").value)
        self.publish_rate_hz = float(self.get_parameter("publish_rate_hz").value)
        self.joint_names = _coerce_joint_names(self.get_parameter("joint_names").value)
        self.calibration_path = self._normalize_text_param(self.get_parameter("calibration_path").value)
        self.raw_state_enabled = bool(self.get_parameter("raw_state_enabled").value)
        self.status_topic_enabled = bool(self.get_parameter("status_topic_enabled").value)
        self.adapter_factory = self._normalize_text_param(self.get_parameter("adapter_factory").value)
        self.degraded_latency_ms = float(self.get_parameter("degraded_latency_ms").value)
        self.positions_in_degrees = self._normalize_text_param(self.get_parameter("positions_in_degrees").value).lower() or "auto"

        self.joint_state_pub = self.create_publisher(JointState, "/leader/joint_states", 20)
        self.raw_state_pub = self.create_publisher(String, "/leader/raw_state", 20)
        self.status_pub = self.create_publisher(String, "/leader/status", 20)
        self.reload_srv = self.create_service(Trigger, "/leader/reload_calibration", self._handle_reload_calibration)

        self.state = STATE_BOOTING
        self.last_error = ""
        self.last_publish_at: Optional[float] = None
        self.last_sample_at: Optional[float] = None
        self.last_hz = 0.0
        self.seq = 0
        self.current_status = AdapterStatus(
            connected=False,
            calibrated=False,
            device_label=self.leader_type,
            backend="booting",
        )

        try:
            self.adapter = build_adapter(
                adapter_factory=self.adapter_factory,
                leader_type=self.leader_type,
                port=self.port,
                calibration_path=self.calibration_path,
                joint_names=self.joint_names,
                positions_in_degrees=self.positions_in_degrees,
            )
        except BridgeError as exc:
            self.adapter = UnavailableLeaderAdapter(exc.detail, backend="adapter-build-error")
            self.state = exc.state
            self.last_error = exc.detail

        period_sec = max(1.0 / max(self.publish_rate_hz, 1.0), 0.02)
        self.timer = self.create_timer(period_sec, self._tick)
        self.get_logger().info(
            f"leader input bridge booting: leader_type={self.leader_type}, port={self.port or 'auto'}, "
            f"publish_rate_hz={self.publish_rate_hz}, adapter_factory={self.adapter_factory or '-'}, "
            f"positions_in_degrees={self.positions_in_degrees}"
        )

    @staticmethod
    def _normalize_text_param(value: Any) -> str:
        text = str(value).strip()
        if not text or text == EMPTY_PARAM_SENTINEL:
            return ""
        return text

    def _publish_status(self) -> None:
        if not self.status_topic_enabled:
            return
        now = time.time()
        age_ms = None if self.last_sample_at is None else max((now - self.last_sample_at) * 1000.0, 0.0)
        payload = build_status_payload(
            state=self.state,
            connected=self.current_status.connected,
            calibrated=self.current_status.calibrated,
            publishing=self.last_sample_at is not None,
            hz=self.last_hz,
            last_frame_age_ms=age_ms,
            last_error=self.last_error,
            device_label=self.current_status.device_label,
            backend=self.current_status.backend,
        )
        self.status_pub.publish(String(data=json.dumps(payload, ensure_ascii=False)))
        self.get_logger().info(
            "leader status: state=%s connected=%s calibrated=%s publishing=%s hz=%.2f age_ms=%s error=%s"
            % (
                payload["state"],
                payload["connected"],
                payload["calibrated"],
                payload["publishing"],
                payload["hz"],
                "n/a" if payload["lastFrameAgeMs"] is None else f"{payload['lastFrameAgeMs']:.2f}",
                payload["lastError"] or "-",
            )
        )

    def _set_state(self, state: str, *, error: str = "") -> None:
        self.state = state
        self.last_error = error
        self._publish_status()

    def _handle_reload_calibration(self, _request: Trigger.Request, response: Trigger.Response) -> Trigger.Response:
        try:
            detail = self.adapter.reload_calibration()
            response.success = True
            response.message = detail or "calibration reload requested"
        except BridgeError as exc:
            response.success = False
            response.message = exc.detail
            self._set_state(exc.state, error=exc.detail)
        except Exception as exc:  # pragma: no cover - runtime safeguard
            detail = f"reload calibration failed: {exc}"
            response.success = False
            response.message = detail
            self._set_state(STATE_ERROR, error=detail)
        return response

    def _publish_joint_state(self, sample: LeaderSample) -> None:
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = list(sample.joint_names)
        msg.position = [float(value) for value in sample.positions_rad]
        self.joint_state_pub.publish(msg)
        self.get_logger().info(
            "leader joint_states published: names=%s positions=%s"
            % (msg.name, [round(value, 4) for value in msg.position])
        )

    def _publish_raw_state(self, sample: LeaderSample) -> None:
        if not self.raw_state_enabled:
            return
        payload = build_raw_state_payload(
            status=self.current_status,
            sample=sample,
            seq=self.seq,
            last_error=self.last_error,
        )
        self.raw_state_pub.publish(String(data=json.dumps(payload, ensure_ascii=False)))

    def _tick(self) -> None:
        try:
            self.get_logger().info("leader tick: connecting adapter")
            status = self.adapter.connect()
            self.current_status = status
            if not status.connected:
                self._set_state(STATE_DISCONNECTED, error="leader adapter reports disconnected")
                return
            if not status.calibrated:
                self._set_state(STATE_CALIBRATING, error="")
                return

            self.get_logger().info("leader tick: reading sample")
            sample = self.adapter.read_sample()
            if len(sample.joint_names) != len(sample.positions_rad):
                raise BridgeError(STATE_ERROR, "joint_names length does not match positions_rad length")

            now = time.time()
            if self.last_publish_at:
                period = max(now - self.last_publish_at, 1e-6)
                self.last_hz = 1.0 / period
            self.last_publish_at = now
            self.last_sample_at = sample.source_timestamp_sec or now
            self.seq += 1

            self._publish_joint_state(sample)
            self._publish_raw_state(sample)

            if sample.read_latency_ms > self.degraded_latency_ms:
                self._set_state(
                    STATE_DEGRADED,
                    error=f"leader read latency high: {sample.read_latency_ms:.1f}ms",
                )
                return

            self._set_state(STATE_READY, error="")
        except BridgeError as exc:
            self._set_state(exc.state, error=exc.detail)
        except Exception as exc:  # pragma: no cover - runtime safeguard
            detail = f"{exc.__class__.__name__}: {exc}"
            self.get_logger().error(detail)
            self.get_logger().debug(traceback.format_exc())
            self._set_state(STATE_ERROR, error=detail)

    def destroy_node(self) -> bool:
        try:
            self.adapter.close()
        except Exception:  # pragma: no cover - best effort cleanup
            pass
        return super().destroy_node()


def main() -> None:
    rclpy.init()
    node = SO101LeaderInputBridge()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
