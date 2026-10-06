"""RGB-only localization of the workcell's upright, axis-aligned green box.

This is a calibrated finite-scene detector, not general 6D pose estimation.
Known box dimensions, top-plane height and an identity-oriented fixed camera
are explicit priors. RGB cannot verify every violation of those priors: a
similarly colored object of matching silhouette remains indistinguishable.

MuJoCo camera convention and perspective fovy:
https://mujoco.readthedocs.io/en/3.3.7/XMLreference.html#body-camera
Pixel coordinates use integer pixel centers; the principal point is
((width - 1) / 2, (height - 1) / 2). No MjData, target body, depth image,
segmentation render or physical-state input is used by this module.
"""
from dataclasses import asdict, dataclass, field
import math

import cv2
import numpy as np


TARGET_SIZE_M = (0.018, 0.018, 0.016)


def _finite_tuple(values, count, name):
    try:
        result = tuple(float(value) for value in values)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{name} must contain {count} finite numbers') from exc
    if len(result) != count or not all(math.isfinite(value) for value in result):
        raise ValueError(f'{name} must contain {count} finite numbers')
    return result


@dataclass(frozen=True)
class TopDownCalibration:
    width: int = 640
    height: int = 480
    camera_position_m: tuple = (0.25, 0.0, 0.95)
    fovy_deg: float = 45.0
    top_plane_z_m: float = 0.018
    top_plane_tolerance_m: float = 0.0005

    def __post_init__(self):
        for name in ('width', 'height'):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < 2:
                raise ValueError(f'{name} must be an integer >= 2')
        object.__setattr__(self, 'camera_position_m',
                           _finite_tuple(self.camera_position_m, 3, 'camera_position_m'))
        if not math.isfinite(self.fovy_deg) or not 0 < self.fovy_deg < 180:
            raise ValueError('fovy_deg must be between 0 and 180 degrees')
        if not math.isfinite(self.top_plane_z_m) or self.depth_m <= 0:
            raise ValueError('top plane must be below the camera')
        if (not math.isfinite(self.top_plane_tolerance_m)
                or not 0 <= self.top_plane_tolerance_m < self.depth_m):
            raise ValueError('invalid top-plane height tolerance')

    @property
    def focal_px(self):
        return self.height / (2 * math.tan(math.radians(self.fovy_deg) / 2))

    @property
    def principal_px(self):
        return ((self.width - 1) / 2, (self.height - 1) / 2)

    @property
    def depth_m(self):
        return self.camera_position_m[2] - self.top_plane_z_m

    @property
    def metres_per_pixel(self):
        return self.depth_m / self.focal_px

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_mujoco_model(cls, model, *, width=640, height=480,
                          camera_name='topdown', top_plane_z_m=0.018,
                          top_plane_tolerance_m=0.0005):
        """Extract only static world-camera fields; reject unsupported cameras.

        No forward kinematics or MjData is required. A fixed camera attached
        to a moving body, nonidentity orientation, orthographic projection or
        physical sensor intrinsics cannot silently use this pinhole model.
        """
        camera_id = int(model.camera(camera_name).id)
        if int(model.cam_bodyid[camera_id]) != 0 or int(model.cam_mode[camera_id]) != 0:
            raise ValueError('camera must be fixed on the world body')
        quat = np.asarray(model.cam_quat[camera_id], dtype=np.float64)
        if not (np.allclose(quat[1:], 0, atol=1e-10, rtol=0)
                and math.isclose(abs(float(quat[0])), 1, abs_tol=1e-10)):
            raise ValueError('camera orientation must be identity (look down world -Z)')
        if bool(model.cam_orthographic[camera_id]):
            raise ValueError('orthographic camera is unsupported')
        if np.any(np.asarray(model.cam_sensorsize[camera_id]) != 0):
            raise ValueError('sensor intrinsics are unsupported; use a fovy camera')
        return cls(width=width, height=height,
                   camera_position_m=tuple(model.cam_pos[camera_id]),
                   fovy_deg=float(model.cam_fovy[camera_id]),
                   top_plane_z_m=top_plane_z_m,
                   top_plane_tolerance_m=top_plane_tolerance_m)


def pixel_to_world_xy(pixel_xy, calibration):
    """Backproject a top-face pixel onto the declared horizontal top plane."""
    u, v = _finite_tuple(pixel_xy, 2, 'pixel_xy')
    cu, cv = calibration.principal_px
    cx, cy, _ = calibration.camera_position_m
    scale = calibration.metres_per_pixel
    return (cx + (u - cu) * scale, cy - (v - cv) * scale)


def world_xy_to_pixel(xy_m, calibration):
    """Project a point on the declared top plane, with image v pointing down."""
    x, y = _finite_tuple(xy_m, 2, 'xy_m')
    cu, cv = calibration.principal_px
    cx, cy, _ = calibration.camera_position_m
    scale = calibration.metres_per_pixel
    return (cu + (x - cx) / scale, cv - (y - cy) / scale)


@dataclass(frozen=True)
class LocalizationResult:
    valid: bool
    reason: str
    xy_m: tuple | None = None
    pixel_xy: tuple | None = None
    uncertainty_m: float | None = None
    timestamp_s: float = 0.0
    diagnostics: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


def _box_projection_bounds(xy_m, size_m, calibration):
    """Projected silhouette bounds of the declared axis-aligned 3D box."""
    cx, cy, _ = calibration.camera_position_m
    cu, cv = calibration.principal_px
    focal = calibration.focal_px
    depths = (calibration.depth_m, calibration.depth_m + size_m[2])
    u = [cu + focal * (xy_m[0] + side * size_m[0] / 2 - cx) / depth
         for side in (-1, 1) for depth in depths]
    v = [cv - focal * (xy_m[1] + side * size_m[1] / 2 - cy) / depth
         for side in (-1, 1) for depth in depths]
    return (min(u), min(v), max(u), max(v))


def _center_from_silhouette(bounds, size_m, calibration):
    """Account for the visible side faces using the declared box height.

    The farther edge toward the optical axis can originate at the bottom;
    the outer edge originates at the top. Averaging these two independent
    center estimates avoids interpreting the whole silhouette as a top face.
    """
    left, top, right, bottom = bounds
    cu, cv = calibration.principal_px
    normalized = (((left - cu) / calibration.focal_px,
                   (right - cu) / calibration.focal_px),
                  ((cv - bottom) / calibration.focal_px,
                   (cv - top) / calibration.focal_px))
    result = []
    for axis, (low, high) in enumerate(normalized):
        camera_axis = calibration.camera_position_m[axis]
        low_depth = calibration.depth_m + (size_m[2] if low >= 0 else 0)
        high_depth = calibration.depth_m + (size_m[2] if high <= 0 else 0)
        from_low = camera_axis + low * low_depth + size_m[axis] / 2
        from_high = camera_axis + high * high_depth - size_m[axis] / 2
        result.append((from_low + from_high) / 2)
    return tuple(result)


def localize_green_target(rgb, calibration, *, timestamp_s=0.0,
                          target_size_m=TARGET_SIZE_M):
    """Detect one complete green box; reject missing, ambiguous or bad shapes.

    Thresholds are fixed before P0: HSV H=40..92, S>=55, V>=30;
    G-R>=10 and G-B>=6. Components below 3% of expected top area (minimum
    four pixels) are treated as speckles. No closing/filling repairs missing
    pixels. Accepted silhouette dimensions are 0.78..1.25 of projection,
    area 0.72..1.35, filled-box fraction >=0.88, and normalized aspect ratio
    0.8..1.25. At least six pixels per top-face side are required.

    `uncertainty_m` is an engineering radius from a one-pixel radial error
    allowance plus declared height tolerance, NOT a calibrated confidence
    interval or a bound for undetectable prior violations. Rejections carry
    no metric target; the caller must stop or acquire another observation.
    """
    size = _finite_tuple(target_size_m, 3, 'target_size_m')
    if any(value <= 0 for value in size):
        raise ValueError('target dimensions must be positive')
    if not math.isfinite(timestamp_s) or timestamp_s < 0:
        raise ValueError('timestamp_s must be finite and nonnegative')
    diagnostics = {'target_size_m': size, 'top_plane_z_m': calibration.top_plane_z_m,
                   'height_and_axis_alignment_are_priors': True,
                   'uncertainty_kind': 'conditional_engineering_allowance'}

    def reject(reason):
        return LocalizationResult(False, reason, timestamp_s=float(timestamp_s),
                                  diagnostics=diagnostics)

    if (not isinstance(rgb, np.ndarray) or rgb.dtype != np.uint8
            or rgb.shape != (calibration.height, calibration.width, 3)):
        return reject('invalid_rgb_shape_or_dtype')
    expected_top_px = np.asarray(size[:2]) / calibration.metres_per_pixel
    diagnostics['expected_top_size_px'] = expected_top_px.tolist()
    if float(expected_top_px.min()) < 6:
        return reject('insufficient_pixel_resolution')
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    signed_rgb = rgb.astype(np.int16)
    mask = ((hsv[:, :, 0] >= 40) & (hsv[:, :, 0] <= 92)
            & (hsv[:, :, 1] >= 55) & (hsv[:, :, 2] >= 30)
            & (signed_rgb[:, :, 1] - signed_rgb[:, :, 0] >= 10)
            & (signed_rgb[:, :, 1] - signed_rgb[:, :, 2] >= 6))
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), connectivity=8)
    min_area = max(4, math.ceil(0.03 * float(np.prod(expected_top_px))))
    candidates = [index for index in range(1, count)
                  if int(stats[index, cv2.CC_STAT_AREA]) >= min_area]
    diagnostics.update(component_count=len(candidates), min_component_area_px=min_area,
                       green_pixel_count=int(mask.sum()))
    if not candidates:
        return reject('target_missing')
    if len(candidates) != 1:
        return reject('ambiguous_components')
    index = candidates[0]
    x, y, width, height, area = (int(value) for value in stats[index])
    diagnostics.update(bbox_xywh_px=(x, y, width, height), area_px=area,
                       mask_centroid_px=tuple(float(v) for v in centroids[index]))
    if x == 0 or y == 0 or x + width == calibration.width or y + height == calibration.height:
        return reject('image_border_truncation')
    # Pixel centers at integer coordinates occupy cells bounded by +/- 0.5.
    bounds = (x - 0.5, y - 0.5, x + width - 0.5, y + height - 0.5)
    xy = _center_from_silhouette(bounds, size, calibration)
    projected = _box_projection_bounds(xy, size, calibration)
    expected_width, expected_height = projected[2] - projected[0], projected[3] - projected[1]
    scale_ratios = (width / expected_width, height / expected_height)
    area_ratio = area / (expected_width * expected_height)
    fill = area / (width * height)
    aspect_ratio = scale_ratios[0] / scale_ratios[1]
    diagnostics.update(expected_silhouette_size_px=(expected_width, expected_height),
                       dimension_ratios=scale_ratios, area_ratio=area_ratio,
                       fill_fraction=fill, normalized_aspect_ratio=aspect_ratio)
    if not all(0.78 <= value <= 1.25 for value in scale_ratios):
        return reject('size_or_occlusion')
    if not 0.72 <= area_ratio <= 1.35:
        return reject('area_or_occlusion')
    if fill < 0.88 or not 0.8 <= aspect_ratio <= 1.25:
        return reject('shape_or_occlusion')
    pixel = world_xy_to_pixel(xy, calibration)
    radius = math.hypot(xy[0] - calibration.camera_position_m[0],
                        xy[1] - calibration.camera_position_m[1])
    uncertainty = ((calibration.depth_m + size[2]) / calibration.focal_px
                   + radius * calibration.top_plane_tolerance_m / calibration.depth_m)
    diagnostics['estimated_center_z_m_from_prior'] = calibration.top_plane_z_m - size[2] / 2
    return LocalizationResult(True, 'ok', xy, pixel, float(uncertainty),
                              float(timestamp_s), diagnostics)
