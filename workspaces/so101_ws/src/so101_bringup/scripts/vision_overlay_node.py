#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String


ColorBgr = tuple[int, int, int]

PALETTE: dict[str, ColorBgr] = {
    "red": (50, 70, 240),
    "blue": (240, 110, 50),
    "green": (80, 210, 90),
    "yellow": (60, 210, 230),
}
DEFAULT_COLOR: ColorBgr = (230, 230, 230)


@dataclass(frozen=True)
class OverlayItem:
    category: str
    confidence: float
    bbox_xyxy: list[int]
    pixel_center: list[float] | None = None
    world_xyz: list[float] | None = None


def decode_json_dict(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def parse_bbox_xyxy(detection: dict[str, Any]) -> list[int] | None:
    bbox = detection.get("bbox_xyxy")
    if isinstance(bbox, list) and len(bbox) == 4:
        values = [_finite_float(item) for item in bbox]
        if all(value is not None for value in values):
            x1, y1, x2, y2 = [int(round(float(value))) for value in values]
            return [x1, y1, x2, y2]

    bbox = detection.get("bbox_xywh") or detection.get("bbox")
    if isinstance(bbox, list) and len(bbox) == 4:
        values = [_finite_float(item) for item in bbox]
        if all(value is not None for value in values):
            x, y, w, h = [float(value) for value in values]
            return [int(round(x)), int(round(y)), int(round(x + w)), int(round(y + h))]
    return None


def parse_xy_pair(value: Any) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 2:
        return None
    parsed = [_finite_float(item) for item in value]
    return [float(item) for item in parsed] if all(item is not None for item in parsed) else None


def parse_xyz(value: Any) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 3:
        return None
    parsed = [_finite_float(item) for item in value]
    return [float(item) for item in parsed] if all(item is not None for item in parsed) else None


def _target_key(category: str, pixel_center: list[float] | None) -> tuple[str, int, int] | None:
    if pixel_center is None:
        return None
    return (category, int(round(pixel_center[0])), int(round(pixel_center[1])))


def target_world_map(target_payload: dict[str, Any]) -> dict[tuple[str, int, int], list[float]]:
    result: dict[tuple[str, int, int], list[float]] = {}
    for target in target_payload.get("targets") or []:
        if not isinstance(target, dict):
            continue
        category = str(target.get("category") or "").strip().lower()
        pixel_center = parse_xy_pair(target.get("pixel_center"))
        world_xyz = parse_xyz(target.get("world_xyz"))
        key = _target_key(category, pixel_center)
        if key is not None and world_xyz is not None:
            result[key] = world_xyz
    return result


def detection_items(detection_payload: dict[str, Any], target_payload: dict[str, Any]) -> list[OverlayItem]:
    worlds = target_world_map(target_payload)
    items: list[OverlayItem] = []
    for detection in detection_payload.get("detections") or []:
        if not isinstance(detection, dict):
            continue
        bbox = parse_bbox_xyxy(detection)
        if bbox is None:
            continue
        category = str(detection.get("category") or "").strip().lower()
        confidence = _finite_float(detection.get("confidence"))
        if confidence is None:
            confidence = 0.0
        pixel_center = parse_xy_pair(detection.get("pixel_center"))
        if pixel_center is None:
            pixel_center = [(bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0]
        world_xyz = worlds.get(_target_key(category, pixel_center))
        items.append(
            OverlayItem(
                category=category or "object",
                confidence=float(confidence),
                bbox_xyxy=bbox,
                pixel_center=pixel_center,
                world_xyz=world_xyz,
            )
        )
    return items


def clamp_bbox(bbox: list[int], width: int, height: int) -> list[int]:
    x1, y1, x2, y2 = bbox
    x1 = max(0, min(width - 1, x1))
    x2 = max(0, min(width - 1, x2))
    y1 = max(0, min(height - 1, y1))
    y2 = max(0, min(height - 1, y2))
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    return [x1, y1, x2, y2]


def _text_size(text: str, scale: float, thickness: int) -> tuple[int, int]:
    (width, height), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    return width, height + baseline


def draw_label(image: np.ndarray, x: int, y: int, text: str, color: ColorBgr, *, scale: float = 0.45) -> None:
    thickness = 1
    text_width, text_height = _text_size(text, scale, thickness)
    y_top = max(0, y - text_height - 4)
    x_right = min(image.shape[1] - 1, x + text_width + 8)
    cv2.rectangle(image, (x, y_top), (x_right, y), color, -1)
    cv2.putText(
        image,
        text,
        (x + 4, max(12, y - 5)),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        (20, 20, 20),
        thickness,
        cv2.LINE_AA,
    )


def overlay_image(
    rgb_image: np.ndarray,
    detection_payload: dict[str, Any],
    target_payload: dict[str, Any],
    *,
    stale_sec: float = 1.0,
    now_ms: int | None = None,
) -> np.ndarray:
    if rgb_image.ndim != 3 or rgb_image.shape[2] < 3:
        raise ValueError("expected RGB image with shape HxWx3")
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    overlay = rgb_image.copy()
    height, width = overlay.shape[:2]
    source = str(detection_payload.get("source") or "unknown")
    try:
        age_sec = max((now_ms - int(detection_payload.get("ts", now_ms))) / 1000.0, 0.0)
    except Exception:
        age_sec = 0.0
    stale = age_sec > stale_sec

    for item in detection_items(detection_payload, target_payload):
        color = PALETTE.get(item.category, DEFAULT_COLOR)
        x1, y1, x2, y2 = clamp_bbox(item.bbox_xyxy, width, height)
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
        if item.pixel_center is not None:
            center = (int(round(item.pixel_center[0])), int(round(item.pixel_center[1])))
            cv2.drawMarker(overlay, center, color, markerType=cv2.MARKER_CROSS, markerSize=12, thickness=2)
        label = f"{item.category} {item.confidence:.2f}"
        draw_label(overlay, x1, y1, label, color)
        if item.world_xyz is not None:
            xyz = item.world_xyz
            coord = f"xyz {xyz[0]:.3f}, {xyz[1]:.3f}, {xyz[2]:.3f}"
            cv2.putText(
                overlay,
                coord,
                (x1, min(height - 8, y2 + 18)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                color,
                1,
                cv2.LINE_AA,
            )

    header_color = (80, 210, 90) if not stale else (50, 180, 240)
    header = f"{source} | detections={len(detection_items(detection_payload, target_payload))} | age={age_sec:.2f}s"
    cv2.rectangle(overlay, (0, 0), (width - 1, 28), (25, 25, 25), -1)
    cv2.putText(overlay, header, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, header_color, 1, cv2.LINE_AA)
    return overlay


class VisionOverlayNode(Node):
    def __init__(self) -> None:
        super().__init__("vision_overlay")
        self.declare_parameter("image_topic", "/camera/color/image_raw")
        self.declare_parameter("detections_topic", "/detections")
        self.declare_parameter("vision_targets_topic", "/vision/targets")
        self.declare_parameter("overlay_topic", "/vision/debug/image_overlay")
        self.declare_parameter("stale_sec", 1.0)

        self._bridge = CvBridge()
        self._detection_payload: dict[str, Any] = {}
        self._target_payload: dict[str, Any] = {}
        image_topic = str(self.get_parameter("image_topic").value)
        detections_topic = str(self.get_parameter("detections_topic").value)
        targets_topic = str(self.get_parameter("vision_targets_topic").value)
        overlay_topic = str(self.get_parameter("overlay_topic").value)
        self._pub = self.create_publisher(Image, overlay_topic, 10)
        self.create_subscription(Image, image_topic, self._on_image, 10)
        self.create_subscription(String, detections_topic, self._on_detection, 20)
        self.create_subscription(String, targets_topic, self._on_target, 20)
        self.get_logger().info(
            "Vision overlay ready: "
            f"image_topic={image_topic}, detections_topic={detections_topic}, "
            f"vision_targets_topic={targets_topic}, overlay_topic={overlay_topic}"
        )

    def _on_detection(self, msg: String) -> None:
        payload = decode_json_dict(msg.data)
        if payload:
            self._detection_payload = payload

    def _on_target(self, msg: String) -> None:
        payload = decode_json_dict(msg.data)
        if payload:
            self._target_payload = payload

    def _on_image(self, msg: Image) -> None:
        try:
            image = self._bridge.imgmsg_to_cv2(msg, desired_encoding="rgb8")
            overlay = overlay_image(
                image,
                self._detection_payload,
                self._target_payload,
                stale_sec=float(self.get_parameter("stale_sec").value),
            )
            out = self._bridge.cv2_to_imgmsg(overlay, encoding="rgb8")
            out.header = msg.header
            self._pub.publish(out)
        except Exception as exc:  # pragma: no cover - ROS runtime guard
            self.get_logger().warning(f"Failed to render vision overlay: {exc}")


def main() -> None:
    rclpy.init()
    node = VisionOverlayNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
