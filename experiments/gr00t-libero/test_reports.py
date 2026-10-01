"""Report boundaries: completed rollouts are not necessarily successful tasks."""
import unittest
import tempfile
from pathlib import Path

from common import ROOT, file_sha256, verify_source
from preflight import blockers
from run_rollout import parse_result


class ReportBoundaryTests(unittest.TestCase):
    def test_completed_failed_task_remains_false(self):
        report = parse_result("results: ('libero_sim/task', [False], {'episode_lengths': [720], 'episode_rewards': [0.0]})\n")
        self.assertIs(report["task_success"], False)
        self.assertEqual(report["episode_lengths"], [720])

    def test_missing_or_empty_episode_is_rejected(self):
        for text in ("success rate: 1.0\n",
                     "results: ('task', [True], {'episode_lengths': [0]})\n"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_result(text)

    def test_t4_does_not_pass_default_runtime_gate(self):
        device = {"cuda_available": True, "total_vram_bytes": 16_000_000_000,
                  "capability": [7, 5], "bf16_supported": False}
        self.assertIn("default_flash_attention_2_requires_ampere_or_newer", blockers(device))
        self.assertIn("native_bf16_unavailable", blockers(device))

    def test_modified_source_asset_is_rejected(self):
        temp_root = ROOT / "output/test-integrity"
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            source = Path(directory)
            asset = source / "scene.xml"
            asset.write_text("<mujoco/>")
            manifest = {"revision": "pinned", "files": {"scene.xml": file_sha256(asset)}}
            self.assertEqual(verify_source(source, manifest, "pinned"), 1)
            asset.write_text("<mujoco><worldbody/></mujoco>")
            with self.assertRaisesRegex(ValueError, "modified or missing"):
                verify_source(source, manifest, "pinned")

    def test_unexpected_source_file_is_rejected(self):
        temp_root = ROOT / "output/test-integrity"
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            source = Path(directory)
            asset = source / "scene.xml"
            asset.write_text("<mujoco/>")
            manifest = {"revision": "pinned", "files": {"scene.xml": file_sha256(asset)}}
            (source / "new_code.py").write_text("pass")
            with self.assertRaisesRegex(ValueError, "Unexpected file"):
                verify_source(source, manifest, "pinned")


if __name__ == "__main__":
    unittest.main()
