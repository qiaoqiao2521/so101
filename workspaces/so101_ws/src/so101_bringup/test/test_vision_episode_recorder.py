#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from builtin_interfaces.msg import Time
from sensor_msgs.msg import JointState
from std_msgs.msg import String


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "vision_episode_recorder_node.py"


def load_module():
    spec = importlib.util.spec_from_file_location("vision_episode_recorder_node", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class VisionEpisodeRecorderTests(unittest.TestCase):
    def test_allocate_episode_dir_avoids_collision(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            first = module.allocate_episode_dir(Path(temp_dir), "demo")
            second = module.allocate_episode_dir(Path(temp_dir), "demo")

        self.assertEqual("demo", first.name)
        self.assertEqual("demo-01", second.name)

    def test_build_string_event_decodes_json_payload(self):
        module = load_module()
        msg = String()
        msg.data = '{"count":1,"targets":[{"category":"red"}]}'

        event = module.build_string_event("vision_targets", msg)

        self.assertEqual("vision_targets", event["stream"])
        self.assertEqual(1, event["payload"]["count"])

    def test_build_string_event_keeps_benchmark_payload(self):
        module = load_module()
        msg = String()
        msg.data = json.dumps(
            {
                "schema": "so101_sim_grasp_benchmark_v1",
                "target_object": {"category": "red", "world_xyz": [0.32, 0.18, 0.8]},
                "evaluation_result": {"result_label": "trainable_smoke"},
            }
        )

        event = module.build_string_event("benchmark_result", msg)

        self.assertEqual("benchmark_result", event["stream"])
        self.assertEqual("so101_sim_grasp_benchmark_v1", event["payload"]["schema"])
        self.assertEqual("trainable_smoke", event["payload"]["evaluation_result"]["result_label"])

    def test_build_joint_state_event_serializes_joint_state(self):
        module = load_module()
        msg = JointState()
        msg.header.stamp = Time(sec=3, nanosec=4)
        msg.name = ["a"]
        msg.position = [1.2]
        msg.velocity = [0.3]
        msg.effort = [0.4]

        event = module.build_joint_state_event(msg)

        self.assertEqual("joint_states", event["stream"])
        self.assertEqual(3_000_000_004, event["stamp_ns"])
        self.assertEqual(["a"], event["joint_names"])
        self.assertEqual([1.2], event["positions"])

    def test_build_manifest_includes_counts_and_topics(self):
        module = load_module()
        stats = module.EpisodeStats(started_at="2026-04-27T00:00:00+08:00")
        stats.mark("detections", 1000)
        stats.mark("vision_targets", 1500)
        stats.mark("benchmark_result", 1600)

        manifest = module.build_manifest(
            episode_id="demo",
            episode_dir=Path("/tmp/demo"),
            events_path=Path("/tmp/demo/events.jsonl"),
            stats=stats,
            topics={"detections": "/detections"},
            stopped_at="2026-04-27T00:00:01+08:00",
        )

        self.assertEqual("so101_vision_episode_v1", manifest["schema"])
        self.assertEqual(1, manifest["event_counts"]["detections"])
        self.assertEqual(1, manifest["event_counts"]["benchmark_result"])
        self.assertEqual(0.6, manifest["duration_sec"])
        self.assertEqual("/detections", manifest["topics"]["detections"])
        json.dumps(manifest)

    def test_required_streams_ready_reports_missing_and_stale(self):
        module = load_module()
        required = module.parse_required_streams("detections, vision_targets, joint_states")

        ready, reasons = module.required_streams_ready(
            required_streams=required,
            last_stream_wall_ms={"detections": 1000, "vision_targets": 1300},
            now_wall_ms=2000,
            max_stream_age_sec=0.75,
        )

        self.assertFalse(ready)
        self.assertIn("detections:stale", reasons)
        self.assertIn("joint_states:missing", reasons)

    def test_required_streams_ready_accepts_recent_streams(self):
        module = load_module()
        required = module.parse_required_streams("detections,vision_targets,joint_states")

        ready, reasons = module.required_streams_ready(
            required_streams=required,
            last_stream_wall_ms={"detections": 1900, "vision_targets": 1950, "joint_states": 1980},
            now_wall_ms=2000,
            max_stream_age_sec=0.75,
        )

        self.assertTrue(ready)
        self.assertEqual([], reasons)


if __name__ == "__main__":
    unittest.main()
