"""CPU synthetic-image checks; these do not replace rendered P0 acceptance."""
import json
import math
from types import SimpleNamespace
import unittest

import numpy as np

from visual_localization import (TARGET_SIZE_M, TopDownCalibration,
                                 localize_green_target, pixel_to_world_xy,
                                 world_xy_to_pixel)


GREEN = np.asarray((71, 145, 110), dtype=np.uint8)


def image_with_box(calibration, xy=(0.24, -0.13), size=TARGET_SIZE_M):
    """Analytic pixel occupancy from all eight box vertices, no MuJoCo."""
    image = np.full((calibration.height, calibration.width, 3), 110, dtype=np.uint8)
    vertices = []
    for dx in (-size[0] / 2, size[0] / 2):
        for dy in (-size[1] / 2, size[1] / 2):
            for depth in (calibration.depth_m, calibration.depth_m + size[2]):
                # Independent pinhole expression, in pixel-edge coordinates.
                f = calibration.height / (2 * math.tan(math.radians(calibration.fovy_deg / 2)))
                u = calibration.width / 2 + f * (xy[0] + dx - calibration.camera_position_m[0]) / depth
                v = calibration.height / 2 - f * (xy[1] + dy - calibration.camera_position_m[1]) / depth
                vertices.append((u, v))
    vertices = np.asarray(vertices)
    u, v = np.meshgrid(np.arange(calibration.width) + 0.5, np.arange(calibration.height) + 0.5)
    # Rectangle approximates the complete silhouette, including visible sides.
    mask = ((u >= vertices[:, 0].min()) & (u <= vertices[:, 0].max())
            & (v >= vertices[:, 1].min()) & (v <= vertices[:, 1].max()))
    image[mask] = GREEN
    return image, mask


class CalibrationTests(unittest.TestCase):
    def test_center_and_metric_scale(self):
        c = TopDownCalibration()
        self.assertEqual(pixel_to_world_xy((319.5, 239.5), c), (0.25, 0.0))
        expected = 0.932 * 2 * math.tan(math.pi / 8) / 480
        self.assertAlmostEqual(c.metres_per_pixel, expected, places=15)
        self.assertAlmostEqual(pixel_to_world_xy((320.5, 239.5), c)[0], .25 + expected)
        self.assertAlmostEqual(pixel_to_world_xy((319.5, 240.5), c)[1], -expected)

    def test_round_trip_away_from_optical_axis(self):
        c = TopDownCalibration()
        for xy in ((.24, -.13), (.25, 0), (.40, .18), (.10, -.20)):
            with self.subTest(xy=xy):
                np.testing.assert_allclose(pixel_to_world_xy(world_xy_to_pixel(xy, c), c), xy,
                                           rtol=0, atol=1e-16)

    def test_height_changes_scale(self):
        a, b = TopDownCalibration(), TopDownCalibration(top_plane_z_m=0.2)
        self.assertLess(abs(pixel_to_world_xy((319.5, 300), b)[1]),
                        abs(pixel_to_world_xy((319.5, 300), a)[1]))

    def test_invalid_calibration(self):
        for values in ({'width': 640.5}, {'height': True}, {'fovy_deg': 0},
                       {'fovy_deg': float('nan')}, {'top_plane_z_m': .95},
                       {'camera_position_m': (.25, float('nan'), .95)},
                       {'top_plane_tolerance_m': -1}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                TopDownCalibration(**values)

    def test_reads_only_fixed_camera_fields(self):
        model = SimpleNamespace(camera=lambda name: SimpleNamespace(id=0),
                                cam_bodyid=[0], cam_mode=[0], cam_quat=[[1, 0, 0, 0]],
                                cam_orthographic=[0], cam_sensorsize=[[0, 0]],
                                cam_pos=[[.25, 0, .95]], cam_fovy=[45])
        self.assertEqual(TopDownCalibration.from_mujoco_model(model), TopDownCalibration())
        for field, bad_value in (('cam_bodyid', [1]), ('cam_mode', [1]),
                                 ('cam_quat', [[.707, .707, 0, 0]]),
                                 ('cam_orthographic', [1]), ('cam_sensorsize', [[.01, .01]])):
            old = getattr(model, field)
            with self.subTest(field=field), self.assertRaises(ValueError):
                setattr(model, field, bad_value)
                TopDownCalibration.from_mujoco_model(model)
            setattr(model, field, old)


class LocalizationTests(unittest.TestCase):
    def setUp(self):
        self.calibration = TopDownCalibration()

    def test_twenty_positions_without_ground_truth_input(self):
        for x in np.linspace(.230, .250, 5):
            for y in np.linspace(-.140, -.120, 4):
                with self.subTest(x=x, y=y):
                    image, _ = image_with_box(self.calibration, (x, y))
                    result = localize_green_target(image, self.calibration, timestamp_s=1.5)
                    self.assertTrue(result.valid, result.to_dict())
                    self.assertLess(np.linalg.norm(np.asarray(result.xy_m) - (x, y)), .002)
                    self.assertEqual(result.timestamp_s, 1.5)
                    self.assertGreater(result.uncertainty_m, 0)
                    self.assertLess(result.uncertainty_m, .002)
                    json.dumps(result.to_dict(), allow_nan=False)

    def test_green_variations(self):
        for color in ((36, 73, 55), (106, 180, 145)):
            image, mask = image_with_box(self.calibration)
            image[mask] = color
            self.assertTrue(localize_green_target(image, self.calibration).valid)

    def test_missing_and_other_colors(self):
        for color in ((0, 0, 0), (140, 80, 60), (50, 100, 150), (160, 160, 160)):
            image = np.full((480, 640, 3), color, dtype=np.uint8)
            result = localize_green_target(image, self.calibration)
            self.assertFalse(result.valid)
            self.assertEqual(result.reason, 'target_missing')
            self.assertIsNone(result.xy_m)

    def test_half_occluded(self):
        image, mask = image_with_box(self.calibration)
        rows, columns = np.where(mask)
        image[:, :int((columns.min() + columns.max()) / 2) + 1] = 100
        result = localize_green_target(image, self.calibration)
        self.assertFalse(result.valid)
        self.assertIn('occlusion', result.reason)

    def test_internal_occlusion_is_not_filled(self):
        image, mask = image_with_box(self.calibration)
        rows, columns = np.where(mask)
        y, x = int(rows.mean()), int(columns.mean())
        image[y-3:y+3, x-3:x+3] = 100
        result = localize_green_target(image, self.calibration)
        self.assertFalse(result.valid)
        self.assertIn('occlusion', result.reason)

    def test_two_candidates_are_ambiguous(self):
        image, _ = image_with_box(self.calibration)
        other, mask = image_with_box(self.calibration, (.30, -.13))
        image[mask] = other[mask]
        result = localize_green_target(image, self.calibration)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, 'ambiguous_components')

    def test_fragmented_target_is_rejected(self):
        image, mask = image_with_box(self.calibration)
        _, columns = np.where(mask)
        image[:, int(columns.mean())] = 100
        self.assertEqual(localize_green_target(image, self.calibration).reason,
                         'ambiguous_components')

    def test_wrong_shape_even_at_similar_area(self):
        for size in ((.009, .036, .016), (.036, .036, .016), (.007, .007, .016)):
            with self.subTest(size=size):
                image, _ = image_with_box(self.calibration, size=size)
                self.assertFalse(localize_green_target(image, self.calibration).valid)

    def test_border_truncation(self):
        image = np.full((480, 640, 3), 100, dtype=np.uint8)
        image[220:232, :11] = GREEN
        result = localize_green_target(image, self.calibration)
        self.assertEqual(result.reason, 'image_border_truncation')

    def test_isolated_one_pixel_speck_does_not_hide_target(self):
        image, _ = image_with_box(self.calibration)
        image[10, 10] = GREEN
        self.assertTrue(localize_green_target(image, self.calibration).valid)

    def test_invalid_rgb_and_insufficient_resolution(self):
        image, _ = image_with_box(self.calibration)
        for bad in (None, image.astype(float), image[:, :, 0], image[:-1]):
            self.assertEqual(localize_green_target(bad, self.calibration).reason,
                             'invalid_rgb_shape_or_dtype')
        c = TopDownCalibration(width=128, height=128)
        self.assertEqual(localize_green_target(np.zeros((128, 128, 3), np.uint8), c).reason,
                         'insufficient_pixel_resolution')

    def test_invalid_priors_and_timestamp(self):
        image, _ = image_with_box(self.calibration)
        for size in ((.018, .018), (.018, .018, 0), (.018, .018, float('nan'))):
            with self.assertRaises(ValueError):
                localize_green_target(image, self.calibration, target_size_m=size)
        for stamp in (-1, float('nan')):
            with self.assertRaises(ValueError):
                localize_green_target(image, self.calibration, timestamp_s=stamp)

    def test_input_image_is_unchanged(self):
        image, _ = image_with_box(self.calibration)
        before = image.copy()
        localize_green_target(image, self.calibration)
        np.testing.assert_array_equal(image, before)


if __name__ == '__main__':
    unittest.main()
