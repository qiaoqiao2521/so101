"""Actual MuJoCo-state integration and stop-latch contract checks."""
from pathlib import Path
import unittest

import mujoco
import numpy as np

from cbf_filter import Ellipsoid
from hazard_tracking import HazardEstimate
from runtime import SimulationSafetyAdapter

SOURCE = Path(__file__).resolve().parents[2] / "workspaces/so101_ws/src/so101_mujoco/models/so101.xml"


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = mujoco.MjModel.from_xml_path(str(SOURCE))

    def setUp(self):
        self.data = mujoco.MjData(self.model)
        self.data.qpos[5] = .3
        self.data.ctrl[:] = self.data.qpos
        mujoco.mj_forward(self.model, self.data)
        self.adapter = SimulationSafetyAdapter(self.model)
        self.hazard = Ellipsoid(np.array([2., 2., 2.]), np.eye(3), np.full(3, .03))

    def test_filter_reads_actual_state_and_does_not_execute(self):
        before = (self.data.qpos.copy(), self.data.ctrl.copy(), self.data.time)
        self.data.qpos[0] = .1
        target = self.data.qpos.copy()
        target[0] += .002
        result = self.adapter.apply(self.data, target, self.hazard)
        # OSQP's small numerical changes can cross the reporting-only
        # accepted/modified threshold; the control contract is a valid,
        # essentially nominal action computed from actual q, without execution.
        self.assertIn(result.status, ("accepted", "modified"))
        np.testing.assert_allclose(result.action, target, atol=5e-7)
        self.assertAlmostEqual(result.metrics["nominal_velocity"][0], .1)
        self.assertAlmostEqual(self.data.qpos[0], .1)
        np.testing.assert_array_equal(self.data.ctrl, before[1])
        self.assertEqual(self.data.time, before[2])

    def test_stale_tracking_latches_and_reset_is_explicit(self):
        estimate = HazardEstimate(self.hazard.center, self.hazard.rotation,
                                  self.hazard.semi_axes, 0, "tracked")
        result = self.adapter.apply(self.data, self.data.qpos.copy(), estimate, step=6)
        self.assertIsNone(result.action)
        self.assertEqual(result.metrics["reason"], "perception_invalid_or_stale")
        result = self.adapter.apply(self.data, self.data.qpos.copy(), self.hazard)
        self.assertIsNone(result.action)
        self.assertTrue(result.metrics["reason"].startswith("latched:"))
        self.adapter.reset()
        self.assertIsNotNone(self.adapter.apply(self.data, self.data.qpos.copy(), self.hazard).action)

    def test_failed_estimate_never_degrades_to_oracle(self):
        estimate = HazardEstimate(self.hazard.center, self.hazard.rotation,
                                  self.hazard.semi_axes, 0, "failed", "depth_missing")
        self.assertIsNone(self.adapter.apply(self.data, self.data.qpos.copy(), estimate, step=0).action)

    def test_visible_only_point_fit_requires_explicit_research_opt_in(self):
        estimate = HazardEstimate(self.hazard.center, self.hazard.rotation,
                                  self.hazard.semi_axes, 0, "tracked")
        result = self.adapter.apply(self.data, self.data.qpos.copy(), estimate, step=0)
        self.assertEqual(result.metrics["reason"], "perception_missing_whole_obstacle_envelope")
        research = SimulationSafetyAdapter(self.model, allow_visible_enclosure=True)
        self.assertIsNotNone(research.apply(self.data, self.data.qpos.copy(), estimate, step=0).action)

    def test_invalid_timestamp_cannot_authorize_motion(self):
        for step, measurement in ((np.nan, 0), (0, np.nan), (-1, 0), (True, 0), (0, 1.5)):
            with self.subTest(step=step, measurement=measurement):
                self.adapter.reset()
                estimate = HazardEstimate(self.hazard.center, self.hazard.rotation,
                                          self.hazard.semi_axes, measurement, "tracked")
                result = self.adapter.apply(self.data, self.data.qpos.copy(), estimate, step=step)
                self.assertIsNone(result.action)
                self.assertEqual(result.metrics["reason"], "perception_invalid_or_stale")

    def test_unverified_and_missing_timestamp_stop(self):
        self.assertIsNone(self.adapter.apply(self.data, self.data.qpos.copy(), object()).action)
        self.adapter.reset()
        estimate = HazardEstimate(self.hazard.center, self.hazard.rotation,
                                  self.hazard.semi_axes, 0, "tracked")
        self.assertIsNone(self.adapter.apply(self.data, self.data.qpos.copy(), estimate).action)

    def test_jaw_actual_and_target_must_be_within_covered_sweep(self):
        target = self.data.qpos.copy()
        target[5] = .7
        self.assertIsNone(self.adapter.apply(self.data, target, self.hazard).action)
        self.adapter.reset()
        self.data.qpos[5] = .51
        result = self.adapter.apply(self.data, target, self.hazard)
        self.assertIsNone(result.action)
        self.assertEqual(result.metrics["reason"], "jaw_outside_modelled_sweep")


if __name__ == "__main__":
    unittest.main()
