"""CPU geometry/kinematic checks; no hardware or renderer is initialized."""
from pathlib import Path
import sys
import tempfile
import unittest

import mujoco
import numpy as np

from arm_geometry import (BODY_SCOPE, LinkEllipsoid, _arc_bounds,
                          audit_geometry_coverage, build_arm_geometry, world_ellipsoids)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workspaces/so101_ws/src/so101_mujoco/models/so101.xml"
JOINTS = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper")


class ArmGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = mujoco.MjModel.from_xml_path(str(SOURCE))
        cls.geometry, cls.metadata = build_arm_geometry(cls.model)

    def test_five_valid_envelopes_and_explicit_scope(self):
        self.assertEqual(len(self.geometry), 5)
        self.assertEqual(tuple(self.metadata["covered_bodies"]), BODY_SCOPE)
        self.assertIn("upper_arm", self.metadata["excluded_bodies"])
        self.assertFalse(self.metadata["hardware_calibrated"])
        for item in self.geometry:
            self.assertTrue(np.all(item.semi_axes > 0))
            self.assertAlmostEqual(np.linalg.det(item.rotation_local), 1., places=9)
            np.testing.assert_allclose(item.rotation_local.T @ item.rotation_local, np.eye(3), atol=1e-9)

    def test_dense_original_mesh_coverage(self):
        report = audit_geometry_coverage(self.model, self.geometry, jaw_samples=17)
        self.assertTrue(report["passed"], report)
        self.assertGreater(sum(row["surface_sample_count"] for row in report["bodies"]), 2_000_000)
        self.assertEqual(sum(row["outside_count"] for row in report["bodies"]), 0)

    def test_audit_detects_missing_finger_volume(self):
        bad = list(self.geometry)
        original = bad[-1]
        bad[-1] = LinkEllipsoid(original.name, original.body_name, original.center_local,
                               original.rotation_local, original.semi_axes * .1)
        report = audit_geometry_coverage(self.model, bad, jaw_samples=2)
        self.assertFalse(report["passed"])
        self.assertGreater(report["bodies"][-1]["outside_count"], 0)

    def test_world_position_and_rotation_jacobian_finite_difference(self):
        data = mujoco.MjData(self.model)
        data.qpos[:6] = [.2, -.3, .4, -.1, .15, .25]
        mujoco.mj_forward(self.model, data)
        before = data.qpos.copy()
        reference = world_ellipsoids(self.model, data, self.geometry, joint_names=JOINTS)
        np.testing.assert_array_equal(before, data.qpos)
        epsilon = 1e-7
        for column, joint in enumerate(JOINTS):
            query = mujoco.MjData(self.model)
            query.qpos[:] = before
            query.qpos[int(self.model.joint(joint).qposadr[0])] += epsilon
            mujoco.mj_forward(self.model, query)
            changed = world_ellipsoids(self.model, query, self.geometry, joint_names=JOINTS)
            for a, b in zip(reference, changed):
                np.testing.assert_allclose((b.center - a.center) / epsilon, a.jacobian[:3, column], atol=1e-7)
                derivative = (b.rotation - a.rotation) @ a.rotation.T / epsilon
                angular = np.array([derivative[2, 1], derivative[0, 2], derivative[1, 0]])
                np.testing.assert_allclose(angular, a.jacobian[3:, column], atol=1e-7)
                self.assertEqual(a.jacobian.shape, (6, 6))
        # The swept volume is attached to the fixed gripper, independent of
        # instantaneous jaw motion, so its sixth Jacobian column is zero.
        np.testing.assert_allclose(reference[-1].jacobian[:, 5], 0., atol=1e-12)

    def test_arc_extrema_are_continuous_not_endpoint_only(self):
        center = np.zeros((1, 3))
        cosine = np.ones((1, 3))
        sine = np.array([[1., -1., .3]])
        lower, upper = _arc_bounds(center, cosine, sine, (-.8, .8))
        angles = np.linspace(-.8, .8, 2001)
        points = center + np.cos(angles)[:, None] * cosine + np.sin(angles)[:, None] * sine
        self.assertTrue(np.all(points >= lower - 1e-12))
        self.assertTrue(np.all(points <= upper + 1e-12))
        self.assertAlmostEqual(upper[0], np.sqrt(2.), places=12)

    def test_invalid_inputs_refuse_partial_or_left_handed_geometry(self):
        with self.assertRaises(ValueError):
            build_arm_geometry(self.model, jaw_range=(.5, .015))
        with self.assertRaises(ValueError):
            build_arm_geometry(self.model, padding_m=0)
        with self.assertRaises(ValueError):
            LinkEllipsoid("bad", "gripper", np.zeros(3), np.diag([1, 1, -1]), np.ones(3))

    def test_derived_contact_pads_and_free_body_dofs(self):
        sys.path.insert(0, str(ROOT / "experiments/colab-twin"))
        from grasp_episode import build_contact_scene
        with tempfile.TemporaryDirectory(prefix="so101-geometry-") as output:
            model, _, _ = build_contact_scene(SOURCE, Path(output))
            geometry, metadata = build_arm_geometry(model)
            names = {item["geom_name"] for item in metadata["geometry_sources"]}
            self.assertIn("pad_gripper", names)
            self.assertIn("pad_moving_jaw", names)
            report = audit_geometry_coverage(model, geometry, jaw_samples=9)
            self.assertTrue(report["passed"], report)
            data = mujoco.MjData(model)
            mujoco.mj_forward(model, data)
            full = world_ellipsoids(model, data, geometry)
            arm = world_ellipsoids(model, data, geometry, joint_names=JOINTS[:5])
            self.assertEqual(full[0].jacobian.shape, (6, model.nv))
            self.assertEqual(arm[0].jacobian.shape, (6, 5))
            np.testing.assert_allclose(full[0].jacobian[:, 6:], 0., atol=1e-12)


if __name__ == "__main__":
    unittest.main()
