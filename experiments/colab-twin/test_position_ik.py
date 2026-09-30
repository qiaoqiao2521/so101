"""Small acceptance checks against the actual SO101 MuJoCo model."""

from pathlib import Path
import unittest

import mujoco
import numpy as np

from position_ik import solve_position_ik


MODEL = Path(__file__).resolve().parents[2] / "workspaces/so101_ws/src/so101_mujoco/models/so101.xml"


class PositionIKAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = mujoco.MjModel.from_xml_path(str(MODEL))
        cls.initial = np.array([0.0, -0.3, 0.6, 1.2, 0.0, 0.4])

    def tcp_position(self, q):
        data = mujoco.MjData(self.model)
        data.qpos[:] = q
        mujoco.mj_forward(self.model, data)
        return data.site("gripperframe").xpos.copy()

    def test_fk_known_reachable_position_and_fixed_gripper(self):
        target = self.tcp_position(np.array([0.25, -0.4, 0.9, 0.7, -0.15, 0.4]))
        original_ranges = self.model.jnt_range.copy()
        result = solve_position_ik(self.model, self.initial, target, tolerance_m=0.002)
        self.assertEqual(result["status"], "solved", result)
        goal = np.array(result["qpos"])
        self.assertEqual(goal[5], self.initial[5])
        self.assertLessEqual(np.linalg.norm(self.tcp_position(goal) - target), 0.002)
        self.assertTrue(np.all(goal >= self.model.jnt_range[:, 0]))
        self.assertTrue(np.all(goal <= self.model.jnt_range[:, 1]))
        self.assertTrue(np.all(goal >= self.model.actuator_ctrlrange[:, 0]))
        self.assertTrue(np.all(goal <= self.model.actuator_ctrlrange[:, 1]))
        np.testing.assert_array_equal(self.model.jnt_range, original_ranges)

    def test_obviously_unreachable_returns_no_pseudo_solution(self):
        result = solve_position_ik(self.model, self.initial, np.array([4.0, 4.0, 4.0]),
                                   attempts=2, max_iterations=80)
        self.assertEqual(result["status"], "unreachable")
        self.assertIsNone(result["qpos"])
        self.assertFalse(result["certified_unreachable"])

    def test_collision_callback_rejects_converged_candidate(self):
        result = solve_position_ik(self.model, self.initial, self.tcp_position(self.initial),
                                   attempts=2, candidate_valid=lambda q: False)
        self.assertEqual(result["status"], "unreachable")
        self.assertIsNone(result["qpos"])
        self.assertEqual(result["reason"], "candidate_rejected")

    def test_invalid_input_is_explicitly_rejected(self):
        target = self.tcp_position(self.initial)
        for q, xyz in [(np.zeros(5), target), (self.initial, np.zeros(4)),
                       (np.full(6, np.nan), target), (self.initial, [np.inf, 0, 0]),
                       (np.array([0, 0, 0, 0, 0, 4]), target)]:
            with self.subTest(q=q, xyz=xyz), self.assertRaises(ValueError):
                solve_position_ik(self.model, q, xyz)


if __name__ == "__main__":
    unittest.main()
