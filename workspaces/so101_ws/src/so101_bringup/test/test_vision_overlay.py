#!/usr/bin/env python3
import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "vision_overlay_node.py"


def load_module():
    spec = importlib.util.spec_from_file_location("vision_overlay_node", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class VisionOverlayTests(unittest.TestCase):
    def test_detection_items_merges_bbox_with_world_target(self):
        module = load_module()

        items = module.detection_items(
            {
                "detections": [
                    {
                        "category": "red",
                        "confidence": 0.75,
                        "bbox_xyxy": [10, 20, 30, 40],
                    }
                ]
            },
            {
                "targets": [
                    {
                        "category": "red",
                        "pixel_center": [20.0, 30.0],
                        "world_xyz": [0.65, 0.18, 0.8],
                    }
                ]
            },
        )

        self.assertEqual(1, len(items))
        self.assertEqual("red", items[0].category)
        self.assertEqual([10, 20, 30, 40], items[0].bbox_xyxy)
        self.assertEqual([20.0, 30.0], items[0].pixel_center)
        self.assertEqual([0.65, 0.18, 0.8], items[0].world_xyz)

    def test_parse_bbox_xywh_legacy_payload(self):
        module = load_module()

        bbox = module.parse_bbox_xyxy({"bbox_xywh": [5, 6, 20, 30]})

        self.assertEqual([5, 6, 25, 36], bbox)

    def test_overlay_image_draws_pixels(self):
        module = load_module()
        image = np.zeros((80, 120, 3), dtype=np.uint8)

        overlay = module.overlay_image(
            image,
            {
                "source": "gazebo_color_detector",
                "ts": 1000,
                "detections": [
                    {
                        "category": "blue",
                        "confidence": 0.81,
                        "bbox_xyxy": [20, 25, 60, 55],
                    }
                ],
            },
            {
                "targets": [
                    {
                        "category": "blue",
                        "pixel_center": [40.0, 40.0],
                        "world_xyz": [0.6, -0.2, 0.8],
                    }
                ]
            },
            now_ms=1100,
        )

        self.assertEqual(image.shape, overlay.shape)
        self.assertGreater(int(np.count_nonzero(overlay)), 0)
        self.assertTrue(np.any(overlay[25:56, 20:61, 2] > 0))


if __name__ == "__main__":
    unittest.main()
