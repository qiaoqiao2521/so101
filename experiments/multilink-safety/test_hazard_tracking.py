"""Deterministic registered RGB-D checks; no detector, model or hardware."""
import unittest
import numpy as np

from hazard_tracking import (CameraModel, HazardEstimate, SparseHazardTracker,
                             TrackerConfig, TrackingFailure, conservative_pca_enclosure)


class FitTests(unittest.TestCase):
    def test_finite_points_are_enclosed_even_with_planar_cloud(self):
        random = np.random.default_rng(8)
        for points in (random.normal(size=(200, 3)) * [0.08, 0.03, 0.02],
                       np.column_stack((random.normal(size=(100, 2)) * 0.03, np.zeros(100)))):
            center, rotation, axes = conservative_pca_enclosure(points)
            self.assertLessEqual(np.linalg.norm((points - center) @ rotation / axes, axis=1).max(), 1)
            np.testing.assert_allclose(rotation.T @ rotation, np.eye(3), atol=1e-12)
            self.assertAlmostEqual(np.linalg.det(rotation), 1)
            self.assertTrue((axes > 0).all())

    def test_invalid_cloud_and_camera_rejected(self):
        with self.assertRaises(ValueError):
            conservative_pca_enclosure([[0, 0, np.nan]] * 4)
        with self.assertRaises(ValueError):
            CameraModel(100, 100, 10, 10, np.zeros((4, 4)))

    def test_stale_and_failed_estimates_cannot_authorize_motion(self):
        estimate = HazardEstimate(np.zeros(3), np.eye(3), np.ones(3), 0, "tracked")
        estimate.require_safe(5)
        with self.assertRaisesRegex(TrackingFailure, "stale"):
            estimate.require_safe(6)
        with self.assertRaises(ValueError):
            estimate.center[0] = 1


class TrackerTests(unittest.TestCase):
    def setUp(self):
        # Downward-looking fixed camera; camera x-right/y-down/z-forward.
        transform = np.eye(4)
        transform[:3, :3] = np.diag([1, -1, -1])
        transform[:3, 3] = [0, 0, 1]
        self.camera = CameraModel(200, 200, 80, 60, transform)
        self.bbox = [55, 35, 105, 85]
        rng = np.random.default_rng(42)
        texture = rng.integers(20, 235, (50, 50), dtype=np.uint8)
        # Smooth enough for LK and retain a unique template.
        import cv2
        self.texture = cv2.GaussianBlur(texture, (3, 3), 0)

    def frame(self, dx=0, dy=0, depth_value=0.6, texture=None):
        image = np.zeros((120, 160, 3), dtype=np.uint8) + 8
        depth = np.full((120, 160), np.nan)
        x0, y0, x1, y1 = np.asarray(self.bbox) + [dx, dy, dx, dy]
        patch = self.texture if texture is None else texture
        image[y0:y1, x0:x1] = patch[:, :, None]
        depth[y0:y1, x0:x1] = depth_value
        return image, depth

    def tracker(self, config=None):
        tracker = SparseHazardTracker(self.camera, config)
        rgb, depth = self.frame()
        tracker.initialize(rgb, depth, self.bbox)
        return tracker

    def test_pixel_depth_world_roundtrip(self):
        pixels = np.array([[80, 60], [90, 70]], dtype=float)
        world = self.camera.unproject(pixels, np.array([0.6, 0.6]))
        np.testing.assert_allclose(world, [[0, 0, 0.4], [0.03, -0.03, 0.4]], atol=1e-12)
        for pixel, point in zip(pixels, world):
            np.testing.assert_allclose(self.camera.project(point)[0], pixel)
            np.testing.assert_allclose(self.camera.ray_at_height(pixel, 0.4), point)

    def test_tracking_uses_anchored_displacement_and_fixed_shape(self):
        tracker = self.tracker()
        initial = tracker.estimate
        for step, shift in [(1, 0), (5, 3), (10, 6), (15, 9)]:
            rgb, depth = self.frame(shift)
            estimate = tracker.update(rgb, depth, step)
            np.testing.assert_allclose(estimate.center - initial.center, [shift * 0.003, 0, 0], atol=0.0003)
            np.testing.assert_array_equal(estimate.axes, initial.axes)
            np.testing.assert_array_equal(estimate.rotation, initial.rotation)
            tracker.require_safe(step)

    def test_depth_failure_latches_until_explicit_reinitialize(self):
        tracker = self.tracker()
        rgb, depth = self.frame(3, depth_value=0.8)
        with self.assertRaisesRegex(TrackingFailure, "depth"):
            tracker.update(rgb, depth, 5)
        self.assertEqual(tracker.estimate.status, "failed")
        with self.assertRaises(TrackingFailure):
            tracker.update(*self.frame(3), 5)
        tracker.initialize(*self.frame(), self.bbox, step=6)
        tracker.require_safe(6)

    def test_excess_motion_and_appearance_gate_stop(self):
        tracker = self.tracker(TrackerConfig(max_displacement_m=0.005))
        with self.assertRaisesRegex(TrackingFailure, "displacement"):
            tracker.update(*self.frame(3), 5)
        tracker = self.tracker(TrackerConfig(minimum_correlation=0.99))
        changed = self.texture.copy()
        changed[:15] = 0
        with self.assertRaisesRegex(TrackingFailure, "correlation"):
            tracker.update(*self.frame(3, texture=changed), 5)

    def test_missing_depth_blank_initialization_and_stale_stop(self):
        rgb, depth = self.frame()
        tracker = SparseHazardTracker(self.camera)
        with self.assertRaisesRegex(TrackingFailure, "depth"):
            tracker.initialize(rgb, np.zeros_like(depth), self.bbox)
        with self.assertRaisesRegex(TrackingFailure, "texture"):
            tracker.initialize(np.zeros_like(rgb), depth, self.bbox)
        tracker = self.tracker()
        with self.assertRaisesRegex(TrackingFailure, "stale"):
            tracker.update(*self.frame(1), 6)
        self.assertEqual(tracker.estimate.status, "failed")
        with self.assertRaisesRegex(TrackingFailure, "stale"):
            tracker.require_safe(0)

    def test_failed_reinitialization_invalidates_prior_estimate(self):
        tracker = self.tracker()
        rgb, depth = self.frame()
        with self.assertRaises(TrackingFailure):
            tracker.initialize(rgb, np.zeros_like(depth), self.bbox)
        with self.assertRaises(TrackingFailure):
            tracker.require_safe(0)
        tracker.initialize(rgb, depth, self.bbox, step=1)
        tracker.require_safe(1)
        tracker.update(rgb, depth, 2)
        with self.assertRaisesRegex(TrackingFailure, "non_monotonic"):
            tracker.require_safe(1)


if __name__ == "__main__":
    unittest.main()
