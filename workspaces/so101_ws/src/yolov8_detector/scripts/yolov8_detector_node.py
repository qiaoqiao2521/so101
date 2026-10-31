#!/usr/bin/env python3
import json
import time
from dataclasses import dataclass
from typing import Any, Iterable, List, Tuple

import rclpy
from cv_bridge import CvBridge
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from rclpy.parameter import Parameter
from sensor_msgs.msg import Image
from std_msgs.msg import String


@dataclass(frozen=True)
class DetectorStatus:
    state: str
    model_path: str
    image_topic: str
    detections_topic: str
    detail: str = ""
    frame_count: int = 0
    detection_count: int = 0
    last_inference_ms: float | None = None


def normalize_target_classes(raw_value: object) -> List[str]:
    def _clean_token(token: object) -> str:
        text = str(token).strip()
        if (text.startswith("'") and text.endswith("'")) or (
            text.startswith('"') and text.endswith('"')
        ):
            text = text[1:-1].strip()
        return text.lower()

    if isinstance(raw_value, str):
        text = raw_value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [_clean_token(item) for item in parsed if _clean_token(item)]
        except Exception:
            pass
        return [_clean_token(item) for item in text.split(",") if _clean_token(item)]

    if isinstance(raw_value, (list, tuple, set)):
        return [_clean_token(item) for item in raw_value if _clean_token(item)]

    return []


def build_status_payload(status: DetectorStatus, *, ts_ms: int | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source": "real_yolo",
        "state": status.state,
        "model_path": status.model_path,
        "image_topic": status.image_topic,
        "detections_topic": status.detections_topic,
        "detail": status.detail,
        "frame_count": int(status.frame_count),
        "detection_count": int(status.detection_count),
        "ts": int(time.time() * 1000) if ts_ms is None else int(ts_ms),
    }
    if status.last_inference_ms is not None:
        payload["last_inference_ms"] = round(float(status.last_inference_ms), 3)
    return payload


def _tensor_item(value: object, default: float = 0.0) -> float:
    try:
        if hasattr(value, "item"):
            return float(value.item())
        if isinstance(value, (list, tuple)):
            if not value:
                return default
            return _tensor_item(value[0], default)
        return float(value)
    except Exception:
        return default


def _sequence_values(value: object) -> list[float]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if value and isinstance(value, list) and value and isinstance(value[0], list):
        value = value[0]
    if not isinstance(value, (list, tuple)):
        return [0.0, 0.0, 0.0, 0.0]
    padded = list(value)[:4]
    while len(padded) < 4:
        padded.append(0.0)
    return [float(item) for item in padded]


def extract_detections_from_results(
    results: object,
    *,
    conf_threshold: float,
    target_classes: list[str],
) -> list[dict[str, Any]]:
    detections: list[dict[str, Any]] = []
    items = list(results or [])
    if not items:
        return detections

    result = items[0]
    names = getattr(result, "names", {}) or {}
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return detections

    for box in boxes:
        cls_id = int(_tensor_item(getattr(box, "cls", [-1]), -1.0))
        conf = float(_tensor_item(getattr(box, "conf", [0.0]), 0.0))
        if conf < conf_threshold:
            continue
        xyxy = _sequence_values(getattr(box, "xyxy", [0, 0, 0, 0]))
        x1, y1, x2, y2 = xyxy
        category = str(names.get(cls_id, str(cls_id))) if isinstance(names, dict) else str(cls_id)
        if target_classes and category.lower() not in target_classes:
            continue
        detections.append(
            {
                "category": category,
                "class_id": cls_id,
                "confidence": round(conf, 6),
                "bbox_xyxy": [round(x1, 3), round(y1, 3), round(x2, 3), round(y2, 3)],
                "bbox_xywh": [
                    round((x1 + x2) / 2.0, 3),
                    round((y1 + y2) / 2.0, 3),
                    round(x2 - x1, 3),
                    round(y2 - y1, 3),
                ],
            }
        )
    return detections


def build_detection_payload(
    *,
    frame_id: str,
    stamp_sec: int,
    stamp_nanosec: int,
    detections: list[dict[str, Any]],
    ts_ms: int | None = None,
) -> dict[str, Any]:
    return {
        "source": "real_yolo",
        "frame_id": frame_id,
        "stamp": {"sec": int(stamp_sec), "nanosec": int(stamp_nanosec)},
        "ts": int(time.time() * 1000) if ts_ms is None else int(ts_ms),
        "count": len(detections),
        "detections": detections,
    }


class YoloV8DetectorNode(Node):
    def __init__(self) -> None:
        super().__init__("yolov8_detector")

        self.declare_parameter("image_topic", "/camera/color/image_raw")
        self.declare_parameter("detections_topic", "/detections")
        self.declare_parameter("status_topic", "/yolo/status")
        self.declare_parameter("model_path", "yolov8n.pt")
        self.declare_parameter("conf_threshold", 0.5)
        self.declare_parameter("device", "cpu")
        self.declare_parameter("max_detections", 20)
        self.declare_parameter("status_period_sec", 1.0)
        # Use STRING to avoid Humble inferring empty list as BYTE_ARRAY.
        self.declare_parameter("target_classes", "")

        self.image_topic = str(self.get_parameter("image_topic").value)
        self.detections_topic = str(self.get_parameter("detections_topic").value)
        self.status_topic = str(self.get_parameter("status_topic").value)
        self.model_path = str(self.get_parameter("model_path").value)
        self.conf_threshold = float(self.get_parameter("conf_threshold").value)
        self.device = str(self.get_parameter("device").value)
        self.max_detections = int(self.get_parameter("max_detections").value)
        self.status_period_sec = max(float(self.get_parameter("status_period_sec").value), 0.1)
        self.target_classes = normalize_target_classes(self.get_parameter("target_classes").value)

        self.bridge = CvBridge()
        self.publisher = self.create_publisher(String, self.detections_topic, 10)
        self.status_publisher = self.create_publisher(String, self.status_topic, 10)
        self.subscription = self.create_subscription(Image, self.image_topic, self.on_image, 10)
        self.add_on_set_parameters_callback(self._on_parameters_changed)

        self.model = None
        self.model_state = "STARTING"
        self.model_detail = ""
        self.frame_count = 0
        self.detection_count = 0
        self.last_inference_ms: float | None = None
        self._load_model()
        self.create_timer(self.status_period_sec, self._publish_status)
        self._publish_status()

        self.get_logger().info(
            "YOLOv8 detector ready: image_topic=%s, detections_topic=%s, status_topic=%s"
            % (self.image_topic, self.detections_topic, self.status_topic)
        )

    def _status(self) -> DetectorStatus:
        return DetectorStatus(
            state=self.model_state,
            model_path=self.model_path,
            image_topic=self.image_topic,
            detections_topic=self.detections_topic,
            detail=self.model_detail,
            frame_count=self.frame_count,
            detection_count=self.detection_count,
            last_inference_ms=self.last_inference_ms,
        )

    def _publish_status(self) -> None:
        self.status_publisher.publish(
            String(data=json.dumps(build_status_payload(self._status()), ensure_ascii=False))
        )

    def _load_model(self) -> None:
        try:
            from ultralytics import YOLO  # type: ignore
        except Exception as exc:  # pragma: no cover
            self.model_state = "ERROR"
            self.model_detail = f"ultralytics_import_failed: {type(exc).__name__}: {exc}"
            self.get_logger().error(
                "Failed to import ultralytics. Install with `pip install ultralytics`. "
                f"Detail: {exc}"
            )
            return

        try:
            self.model = YOLO(self.model_path)
            self.model_state = "READY"
            self.model_detail = "model_loaded"
            self.get_logger().info(f"Loaded YOLO model: {self.model_path}")
        except Exception as exc:  # pragma: no cover
            self.model = None
            self.model_state = "ERROR"
            self.model_detail = f"model_load_failed: {type(exc).__name__}: {exc}"
            self.get_logger().error(f"Failed to load YOLO model '{self.model_path}': {exc}")

    def _normalize_target_classes(self, raw_value: object) -> List[str]:
        return normalize_target_classes(raw_value)

    def _validate_and_extract_params(
        self, params: Iterable[Parameter]
    ) -> Tuple[bool, str, dict]:
        updates = {}
        for param in params:
            if param.name == "conf_threshold":
                value = float(param.value)
                if value < 0.0 or value > 1.0:
                    return False, "conf_threshold must be within [0.0, 1.0]", {}
                updates["conf_threshold"] = value
            elif param.name == "max_detections":
                value = int(param.value)
                if value < 1:
                    return False, "max_detections must be >= 1", {}
                updates["max_detections"] = value
            elif param.name == "target_classes":
                updates["target_classes"] = self._normalize_target_classes(param.value)
        return True, "", updates

    def _on_parameters_changed(self, params: List[Parameter]) -> SetParametersResult:
        valid, reason, updates = self._validate_and_extract_params(params)
        if not valid:
            return SetParametersResult(successful=False, reason=reason)

        if "conf_threshold" in updates:
            self.conf_threshold = updates["conf_threshold"]
        if "max_detections" in updates:
            self.max_detections = updates["max_detections"]
        if "target_classes" in updates:
            self.target_classes = updates["target_classes"]

        if updates:
            self.get_logger().info(
                "Updated params: conf_threshold=%.3f, max_detections=%d, target_classes=%s"
                % (self.conf_threshold, self.max_detections, self.target_classes)
            )
        return SetParametersResult(successful=True)

    def on_image(self, msg: Image) -> None:
        self.frame_count += 1
        if self.model is None:
            return

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self.get_logger().warn(f"cv_bridge conversion failed: {exc}")
            return

        start = time.perf_counter()
        try:
            results = self.model.predict(
                source=frame,
                conf=self.conf_threshold,
                device=self.device,
                verbose=False,
                max_det=self.max_detections,
            )
        except Exception as exc:  # pragma: no cover
            self.model_state = "ERROR"
            self.model_detail = f"inference_failed: {type(exc).__name__}: {exc}"
            self.get_logger().warn(f"YOLO inference failed: {exc}")
            self._publish_status()
            return
        self.last_inference_ms = (time.perf_counter() - start) * 1000.0
        self.model_state = "READY"
        self.model_detail = "last_inference_ok"
        detections = extract_detections_from_results(
            results,
            conf_threshold=self.conf_threshold,
            target_classes=self.target_classes,
        )
        self.detection_count += len(detections)

        payload = build_detection_payload(
            frame_id=msg.header.frame_id,
            stamp_sec=msg.header.stamp.sec,
            stamp_nanosec=msg.header.stamp.nanosec,
            detections=detections,
        )
        self.publisher.publish(String(data=json.dumps(payload, ensure_ascii=False)))


def main() -> None:
    rclpy.init()
    node = YoloV8DetectorNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
