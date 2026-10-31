#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from builtin_interfaces.msg import Time
from sensor_msgs.msg import JointState


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "leader_state_recorder.py"


def load_module():
    spec = importlib.util.spec_from_file_location("leader_state_recorder", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class LeaderStateRecorderTests(unittest.TestCase):
    def test_discover_workspace_root_finds_project_markers(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "AGENTS.md").write_text("test", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "src").mkdir()
            nested = root / "src" / "so101_bringup" / "scripts"
            nested.mkdir(parents=True)

            discovered = module.discover_workspace_root(nested)
            self.assertEqual(root, discovered)

    def test_build_recording_file_path_uses_slug(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = module.build_recording_file_path(Path(temp_dir), "demo-slug")
            self.assertTrue(path.parent.exists())
            self.assertEqual("leader-recording-demo-slug.jsonl", path.name)

    def test_build_recording_file_path_avoids_existing_collision(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "leader-recording-demo-slug.jsonl").write_text("", encoding="utf-8")

            path = module.build_recording_file_path(root, "demo-slug")
            self.assertEqual("leader-recording-demo-slug-01.jsonl", path.name)

    def test_build_metadata_file_path_uses_meta_suffix(self):
        module = load_module()
        path = module.build_metadata_file_path(Path("/tmp/demo.jsonl"))
        self.assertEqual(Path("/tmp/demo.meta.json"), path)

    def test_build_frame_payload_serializes_joint_state(self):
        module = load_module()
        msg = JointState()
        msg.header.stamp = Time(sec=12, nanosec=34)
        msg.name = ["a", "b"]
        msg.position = [1.0, 2.0]
        msg.velocity = [0.1, 0.2]
        msg.effort = [0.3, 0.4]

        payload = module.build_frame_payload(msg)
        self.assertEqual(12_000_000_034, payload["stamp_ns"])
        self.assertEqual(["a", "b"], payload["joint_names"])
        self.assertEqual([1.0, 2.0], payload["positions"])
        self.assertEqual([0.1, 0.2], payload["velocities"])
        self.assertEqual([0.3, 0.4], payload["efforts"])

    def test_build_frame_payload_rejects_position_length_mismatch(self):
        module = load_module()
        msg = JointState()
        msg.header.stamp = Time(sec=1, nanosec=2)
        msg.name = ["a", "b"]
        msg.position = [1.0]

        with self.assertRaisesRegex(ValueError, "positions length mismatch"):
            module.build_frame_payload(msg)

    def test_build_frame_payload_rejects_non_finite_position(self):
        module = load_module()
        msg = JointState()
        msg.header.stamp = Time(sec=1, nanosec=2)
        msg.name = ["a"]
        msg.position = [float("nan")]

        with self.assertRaisesRegex(ValueError, "not finite"):
            module.build_frame_payload(msg)

    def test_build_frame_payload_sanitizes_non_finite_auxiliary_fields(self):
        module = load_module()
        msg = JointState()
        msg.header.stamp = Time(sec=1, nanosec=2)
        msg.name = ["a"]
        msg.position = [0.5]
        msg.velocity = [float("nan")]
        msg.effort = [float("nan")]

        payload = module.build_frame_payload(msg, sanitize_non_finite_auxiliary_fields=True)
        self.assertEqual([], payload["velocities"])
        self.assertEqual([], payload["efforts"])

    def test_build_frame_payload_rejects_position_limit_violation(self):
        module = load_module()
        msg = JointState()
        msg.header.stamp = Time(sec=1, nanosec=2)
        msg.name = ["a"]
        msg.position = [7.0]

        with self.assertRaisesRegex(ValueError, "heuristic limit"):
            module.build_frame_payload(msg, position_abs_limit_rad=6.4)

    def test_build_recording_summary_marks_empty_recording_warning(self):
        module = load_module()
        session = module.RecordingSession(
            slug="demo",
            path=Path("/tmp/demo.jsonl"),
            metadata_path=Path("/tmp/demo.meta.json"),
            started_at_sec=10.0,
            started_at_iso="2026-04-09T12:00:00+08:00",
        )

        summary = module.build_recording_summary(
            session,
            input_topic="/leader/joint_states",
            output_dir=Path("/tmp"),
            flush_every_n_frames=1,
            log_every_n_frames=30,
            large_gap_threshold_sec=0.1,
            motion_epsilon_rad=0.01,
            position_abs_limit_rad=6.4,
            position_spike_threshold_rad=0.35,
            active=False,
            stop_reason="manual_stop",
            stopped_at_sec=12.0,
            stopped_at_iso="2026-04-09T12:00:02+08:00",
        )

        self.assertEqual(0, summary["frame_count"])
        self.assertIn("no_frames_recorded", summary["warnings"])
        self.assertEqual("manual_stop", summary["stop_reason"])

    def test_build_recording_summary_includes_anomaly_and_quality_metrics(self):
        module = load_module()
        session = module.RecordingSession(
            slug="demo",
            path=Path("/tmp/demo.jsonl"),
            metadata_path=Path("/tmp/demo.meta.json"),
            started_at_sec=10.0,
            started_at_iso="2026-04-09T12:00:00+08:00",
            frame_count=3,
            first_stamp_ns=1_000_000_000,
            last_stamp_ns=1_100_000_000,
            invalid_frame_count=2,
            non_monotonic_stamp_count=1,
            duplicate_stamp_count=1,
            joint_name_mismatch_count=1,
            invalid_reason_counts={"positions_non_finite": 2},
            joint_names=["j1", "j2"],
            frame_interval_count=2,
            frame_interval_sum_sec=0.1,
            frame_interval_min_sec=0.04,
            frame_interval_max_sec=0.06,
            large_interval_count=1,
            position_min_by_joint=[-0.2, 0.1],
            position_max_by_joint=[0.3, 0.7],
            total_motion_by_joint=[0.4, 0.8],
            max_step_by_joint=[0.3, 0.5],
            static_transition_count=1,
            active_transition_count=1,
            position_spike_frame_count=1,
        )

        summary = module.build_recording_summary(
            session,
            input_topic="/leader/joint_states",
            output_dir=Path("/tmp"),
            flush_every_n_frames=1,
            log_every_n_frames=30,
            large_gap_threshold_sec=0.1,
            motion_epsilon_rad=0.01,
            position_abs_limit_rad=6.4,
            position_spike_threshold_rad=0.35,
            active=False,
            stop_reason="manual_stop",
            stopped_at_sec=12.0,
            stopped_at_iso="2026-04-09T12:00:02+08:00",
        )

        self.assertEqual(1, summary["anomaly_counts"]["large_interval_count"])
        self.assertEqual(1, summary["anomaly_counts"]["duplicate_stamp_count"])
        self.assertEqual(1, summary["anomaly_counts"]["position_spike_frame_count"])
        self.assertEqual(2, summary["invalid_reason_counts"]["positions_non_finite"])
        self.assertEqual(0.05, summary["frame_interval_stats"]["avg_sec"])
        self.assertEqual(1.2, summary["quality_metrics"]["total_motion_rad"])
        self.assertEqual(20.0, summary["sample_rate_from_stamps_hz"])
        self.assertEqual(0.5, summary["quality_metrics"]["static_transition_ratio"])
        self.assertEqual(0.5, summary["quality_metrics"]["joint_position_range"]["j1"])
        self.assertEqual(0.5, summary["quality_metrics"]["joint_max_step_rad"]["j2"])
        self.assertIn("large_intervals_detected", summary["warnings"])
        self.assertIn("position_spikes_detected", summary["warnings"])

    def test_update_motion_metrics_tracks_static_and_active_transitions(self):
        module = load_module()
        session = module.RecordingSession(
            slug="demo",
            path=Path("/tmp/demo.jsonl"),
            metadata_path=Path("/tmp/demo.meta.json"),
            started_at_sec=10.0,
            started_at_iso="2026-04-09T12:00:00+08:00",
        )

        module.update_motion_metrics(session, [0.0, 0.0], motion_epsilon_rad=0.01)
        module.update_motion_metrics(session, [0.005, 0.0], motion_epsilon_rad=0.01)
        module.update_motion_metrics(session, [0.1, 0.2], motion_epsilon_rad=0.01)

        self.assertEqual(1, session.static_transition_count)
        self.assertEqual(1, session.active_transition_count)
        self.assertEqual([0.1, 0.2], session.position_max_by_joint)
        self.assertEqual([0.1, 0.2], session.total_motion_by_joint)
        self.assertEqual([0.095, 0.2], session.max_step_by_joint)

    def test_recording_file_writes_jsonl_payload(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.jsonl"
            payload = {"stamp_ns": 1, "joint_names": ["a"], "positions": [2.0], "velocities": [], "efforts": []}
            path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            written = json.loads(path.read_text(encoding="utf-8").strip())
            self.assertEqual(payload, written)


if __name__ == "__main__":
    unittest.main()
