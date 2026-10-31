#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "leader_recording_replay.py"


def load_module():
    spec = importlib.util.spec_from_file_location("leader_recording_replay", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_recording(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


class LeaderRecordingReplayTests(unittest.TestCase):
    def test_load_recording_parses_frames(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.jsonl"
            write_recording(
                path,
                [
                    {
                        "stamp_ns": 123,
                        "joint_names": ["j1", "j2"],
                        "positions": [0.1, 0.2],
                        "velocities": [],
                        "efforts": [],
                    }
                ],
            )

            frames = module.load_recording(path)

        self.assertEqual(1, len(frames))
        self.assertEqual(123, frames[0].stamp_ns)
        self.assertEqual(["j1", "j2"], frames[0].joint_names)
        self.assertEqual([0.1, 0.2], frames[0].positions)

    def test_load_recording_rejects_length_mismatch(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.jsonl"
            write_recording(
                path,
                [{"stamp_ns": 1, "joint_names": ["j1", "j2"], "positions": [0.1], "velocities": [], "efforts": []}],
            )

            with self.assertRaisesRegex(ValueError, "positions length mismatch"):
                module.load_recording(path)

    def test_compute_inter_frame_delay_sec_handles_scale_and_non_monotonic(self):
        module = load_module()
        self.assertAlmostEqual(0.5, module.compute_inter_frame_delay_sec(0, 1_000_000_000, 2.0))
        self.assertEqual(0.0, module.compute_inter_frame_delay_sec(5, 5, 1.0))
        self.assertEqual(0.0, module.compute_inter_frame_delay_sec(8, 7, 1.0))

    def test_build_joint_state_message_supports_now_stamp_mode(self):
        module = load_module()
        frame = module.ReplayFrame(
            stamp_ns=123,
            joint_names=["j1"],
            positions=[0.2],
            velocities=[],
            efforts=[],
        )

        message = module.build_joint_state_message(frame, "now", 456)

        self.assertEqual(0, message.header.stamp.sec)
        self.assertEqual(456, message.header.stamp.nanosec)
        self.assertEqual(["j1"], list(message.name))
        self.assertEqual([0.2], list(message.position))


if __name__ == "__main__":
    unittest.main()
