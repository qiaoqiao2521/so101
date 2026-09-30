"""Real SO101 physics execution checks, without rendering or cloud resources."""

import math
from pathlib import Path
import tempfile
import unittest

import mujoco
import numpy as np

from collision_scene import build_scene, CollisionChecker
from joint_planner import plan_joint_path
from planning_experiment import execute_path


class PlanningExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        source = Path(__file__).resolve().parents[2] / (
            "workspaces/so101_ws/src/so101_mujoco/models/so101.xml"
        )
        cls.model = build_scene(source, Path(cls.directory.name) / "scene.xml", [])
        cls.initial = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.35])
        cls.goal = cls.initial.copy()
        cls.goal[0] = 0.05
        cls.checker = CollisionChecker(cls.model, gripper=float(cls.initial[5]))
        data = mujoco.MjData(cls.model)
        data.qpos[:] = cls.goal
        mujoco.mj_forward(cls.model, data)
        cls.target = data.site("gripperframe").xpos.copy()
        bounds = np.c_[
            np.maximum(cls.model.jnt_range[:5, 0], cls.model.actuator_ctrlrange[:5, 0]),
            np.minimum(cls.model.jnt_range[:5, 1], cls.model.actuator_ctrlrange[:5, 1]),
        ]
        cls.planned = plan_joint_path(
            cls.initial[:5], cls.goal[:5], bounds, cls.checker.is_valid, timeout_s=1.0
        )
        if cls.planned["status"] != "solved":
            raise AssertionError(f"The collision-free small-motion fixture failed: {cls.planned}")

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def execute(self, target):
        return execute_path(
            self.model, self.planned["path"], self.initial, target, self.checker,
            render=False,
        )

    def test_actual_physics_follows_small_motion_and_preserves_speed_bound(self):
        actual, rows, frames = self.execute(self.target)
        self.assertTrue(actual["passed"], actual)
        self.assertEqual(frames, [])
        self.assertEqual(actual["invalid_samples"], 0)
        self.assertLessEqual(actual["final_error_m"], 0.01)
        self.assertGreaterEqual(actual["min_distance_m"], self.checker.margin_m)
        trace = np.asarray(rows)
        self.assertTrue(np.all(np.isfinite(trace)))
        self.assertGreater(len(trace), 100)
        self.assertTrue(np.all(np.diff(trace[:, 0]) > 0))
        self.assertAlmostEqual(trace[-1, 0], actual["steps"] * self.model.opt.timestep)
        np.testing.assert_allclose(trace[-1, 7:13], self.goal, atol=1e-12)
        self.assertLess(float(np.max(np.abs(trace[-1, 1:7] - self.goal))), 0.01)
        # Joint commands must traverse the path at the promised speed. This
        # checks measured command increments, not the duration formula itself.
        speeds = np.linalg.norm(np.diff(trace[:, 7:12], axis=0), axis=1) / np.diff(trace[:, 0])
        self.assertLessEqual(float(np.max(speeds)), 0.4 + 1e-9)
        self.assertGreater(float(np.max(speeds)), 0.0)
        # Position servos do not impose exact kinematic gripper equality.
        # Actual collision validation must still inspect these physical states.
        self.assertGreater(float(np.max(np.abs(trace[:, 6] - self.initial[5]))), 1e-9)
        measured_error = math.dist(trace[-1, 13:16], self.target)
        self.assertAlmostEqual(measured_error, actual["final_error_m"])

    def test_successful_plan_cannot_pass_execution_for_wrong_cartesian_target(self):
        actual, _, _ = self.execute(np.array([4.0, 4.0, 4.0]))
        self.assertFalse(actual["passed"])
        self.assertGreater(actual["final_error_m"], actual["reach_tolerance_m"])
        self.assertEqual(actual["invalid_samples"], 0)


if __name__ == "__main__":
    unittest.main()
