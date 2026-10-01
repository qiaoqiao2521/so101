"""Registered RGB-D hazard transport, inspired by paper section III-C.

Source: https://arxiv.org/html/2609.40007v1#S3.SS3
The caller designates a tight pixel bbox; there is no VLM or detector here.
Depth is axial camera depth in metres; the camera frame is x-right/y-down/
z-forward. The fit is a conservative PCA enclosure of retained *visible*
points, not the paper's MVEE or an enclosure of the unseen whole object.
Unlike the paper's held estimate on tracking failure, failures latch a stop.
No fallback detection or template-search recovery is implemented.
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np


class TrackingFailure(RuntimeError):
    """The estimate must not be used to authorize further robot motion."""


def _immutable(value):
    result = np.asarray(value, dtype=np.float64).copy()
    result.setflags(write=False)
    return result


@dataclass(frozen=True)
class CameraModel:
    fx: float
    fy: float
    cx: float
    cy: float
    world_from_camera: np.ndarray

    def __post_init__(self):
        transform = np.asarray(self.world_from_camera, dtype=float)
        if (not np.all(np.isfinite([self.fx, self.fy, self.cx, self.cy]))
                or self.fx <= 0 or self.fy <= 0 or transform.shape != (4, 4)
                or not np.isfinite(transform).all()
                or not np.allclose(transform[3], [0, 0, 0, 1], atol=1e-8)
                or not np.allclose(transform[:3, :3].T @ transform[:3, :3], np.eye(3), atol=1e-6)
                or not np.isclose(np.linalg.det(transform[:3, :3]), 1, atol=1e-6)):
            raise ValueError("camera intrinsics and rigid world_from_camera must be valid")
        object.__setattr__(self, "world_from_camera", _immutable(transform))

    def unproject(self, pixels, depth):
        pixels = np.asarray(pixels, dtype=float)
        depth = np.asarray(depth, dtype=float)
        camera_points = np.column_stack(((pixels[:, 0] - self.cx) * depth / self.fx,
                                         (pixels[:, 1] - self.cy) * depth / self.fy, depth))
        return camera_points @ self.world_from_camera[:3, :3].T + self.world_from_camera[:3, 3]

    def project(self, point):
        camera_point = self.world_from_camera[:3, :3].T @ (np.asarray(point) - self.world_from_camera[:3, 3])
        if camera_point[2] <= 0 or not np.isfinite(camera_point).all():
            raise TrackingFailure("hazard_center_behind_camera")
        return np.array([self.fx * camera_point[0] / camera_point[2] + self.cx,
                         self.fy * camera_point[1] / camera_point[2] + self.cy]), float(camera_point[2])

    def ray_at_height(self, pixel, height):
        ray = self.world_from_camera[:3, :3] @ np.array([(pixel[0] - self.cx) / self.fx,
                                                      (pixel[1] - self.cy) / self.fy, 1.0])
        origin = self.world_from_camera[:3, 3]
        if abs(ray[2]) < 1e-9:
            raise TrackingFailure("camera_ray_parallel_to_horizontal_plane")
        distance = (height - origin[2]) / ray[2]
        if distance <= 0 or not np.isfinite(distance):
            raise TrackingFailure("horizontal_plane_behind_camera")
        return origin + distance * ray


@dataclass(frozen=True)
class HazardEstimate:
    center: np.ndarray
    rotation: np.ndarray
    axes: np.ndarray
    measurement_step: int
    status: str
    reason: str = ""
    fit_method: str = "conservative_pca_visible_points"

    def __post_init__(self):
        for key in ("center", "rotation", "axes"):
            object.__setattr__(self, key, _immutable(getattr(self, key)))

    def require_safe(self, step, max_age_steps=5):
        times = (step, self.measurement_step, max_age_steps)
        if any(isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < 0 for value in times):
            raise TrackingFailure("invalid_tracking_timestamp")
        if self.status not in {"initialized", "tracked", "held"}:
            raise TrackingFailure(self.reason or "tracking_failed")
        if step < self.measurement_step or step - self.measurement_step > max_age_steps:
            raise TrackingFailure("hazard_estimate_stale")
        return self


def conservative_pca_enclosure(points, minimum_axis_m=0.005, margin_m=0.005):
    """Enclose supplied finite points, without claiming invisible geometry."""
    points = np.asarray(points, dtype=float)
    if (points.ndim != 2 or points.shape[1] != 3 or len(points) < 4
            or not np.isfinite(points).all() or minimum_axis_m <= 0 or margin_m < 0):
        raise ValueError("at least four finite 3D points and valid fit margins required")
    origin = points.mean(axis=0)
    _, rotation = np.linalg.eigh(np.cov((points - origin).T))
    rotation = rotation[:, ::-1]
    if np.linalg.det(rotation) < 0:
        rotation[:, -1] *= -1
    local = (points - origin) @ rotation
    low, high = local.min(axis=0), local.max(axis=0)
    midpoint = (low + high) / 2
    center = origin + rotation @ midpoint
    axes = np.maximum((high - low) / 2, minimum_axis_m)
    radial = np.linalg.norm((local - midpoint) / axes, axis=1).max()
    axes = axes * max(1.0, radial) + margin_m
    return center, rotation, axes


@dataclass(frozen=True)
class TrackerConfig:
    update_every_steps: int = 5
    max_age_steps: int = 5
    max_displacement_m: float = 0.025
    forward_backward_px: float = 1.0
    depth_consistency_m: float = 0.03
    initialization_depth_band_m: float = 0.08
    minimum_points: int = 8
    seed_radius_px: int = 18
    seed_spacing_px: int = 4
    minimum_correlation: float = 0.65
    geometry_margin_m: float = 0.005
    minimum_axis_m: float = 0.005

    def __post_init__(self):
        finite = [self.max_displacement_m, self.forward_backward_px, self.depth_consistency_m,
                  self.initialization_depth_band_m, self.minimum_correlation,
                  self.geometry_margin_m, self.minimum_axis_m]
        if (not np.isfinite(finite).all()
                or self.update_every_steps < 1 or self.max_age_steps < self.update_every_steps
                or self.max_displacement_m <= 0 or self.forward_backward_px <= 0
                or self.depth_consistency_m <= 0 or self.initialization_depth_band_m <= 0
                or self.minimum_points < 4 or self.seed_radius_px < 2 or self.seed_spacing_px < 1
                or not -1 <= self.minimum_correlation <= 1
                or self.geometry_margin_m < 0 or self.minimum_axis_m <= 0):
            raise ValueError("invalid tracker bounds")


class SparseHazardTracker:
    """Fixed-camera, approximately constant-height translation tracker.

    Call update on each control step, then require_safe before commanding.
    Any failure is latched; only a new explicit initialize can clear it.
    Object rotation, deformation, off-plane movement and unobserved volume
    require a different estimator; this tracker is not a safety guarantee.
    """

    def __init__(self, camera: CameraModel, config: TrackerConfig | None = None):
        self.camera = camera
        self.config = config or TrackerConfig()
        self.estimate = None
        self.failure = None
        self.last_call_step = None

    @staticmethod
    def _images(rgb, depth):
        import cv2
        rgb, depth = np.asarray(rgb), np.asarray(depth, dtype=float)
        if (rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3
                or depth.shape != rgb.shape[:2]):
            raise TrackingFailure("expected_uint8_RGB_and_registered_metric_depth")
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), depth

    def _fail(self, reason):
        self.failure = reason
        if self.estimate is not None:
            old = self.estimate
            self.estimate = HazardEstimate(old.center, old.rotation, old.axes,
                                           old.measurement_step, "failed", reason)
        raise TrackingFailure(reason)

    @staticmethod
    def _depth_at(depth, points):
        integer = np.rint(points).astype(int)
        inside = ((integer[:, 0] >= 0) & (integer[:, 0] < depth.shape[1])
                  & (integer[:, 1] >= 0) & (integer[:, 1] < depth.shape[0]))
        values = np.full(len(points), np.nan)
        values[inside] = depth[integer[inside, 1], integer[inside, 0]]
        return values, inside & np.isfinite(values) & (values > 0)

    def initialize(self, rgb, depth, bbox, step=0, workspace_bounds=None):
        """Initialize from a caller-designated [x0,y0,x1,y1) bbox.

        Optional workspace_bounds is [[xmin,ymin,zmin],[xmax,ymax,zmax]].
        Tight bbox/object identity and registered axial depth are caller duties.
        """
        self.failure = "initialization_in_progress"
        try:
            return self._initialize(rgb, depth, bbox, step, workspace_bounds)
        except TrackingFailure as error:
            return self._fail(str(error))
        except (TypeError, ValueError) as error:
            return self._fail("invalid_initialization_input: " + str(error))

    def _initialize(self, rgb, depth, bbox, step, workspace_bounds):
        gray, depth = self._images(rgb, depth)
        if not isinstance(step, (int, np.integer)) or step < 0:
            raise TrackingFailure("invalid_control_step")
        bbox = np.asarray(bbox, dtype=int)
        if (bbox.shape != (4,) or bbox[0] < 0 or bbox[1] < 0
                or bbox[2] > gray.shape[1] or bbox[3] > gray.shape[0]
                or bbox[2] - bbox[0] < 8 or bbox[3] - bbox[1] < 8):
            raise TrackingFailure("invalid_designated_bbox")
        x0, y0, x1, y1 = bbox
        yy, xx = np.mgrid[y0:y1, x0:x1]
        pixels = np.column_stack((xx.ravel(), yy.ravel()))
        values, valid = self._depth_at(depth, pixels)
        if valid.sum() < self.config.minimum_points:
            raise TrackingFailure("insufficient_initial_depth")
        median_depth = np.median(values[valid])
        valid &= abs(values - median_depth) <= self.config.initialization_depth_band_m
        points = self.camera.unproject(pixels[valid], values[valid])
        if workspace_bounds is not None:
            bounds = np.asarray(workspace_bounds, dtype=float)
            if bounds.shape != (2, 3) or not np.isfinite(bounds).all() or not (bounds[1] > bounds[0]).all():
                raise TrackingFailure("invalid_workspace_bounds")
            points = points[((points >= bounds[0]) & (points <= bounds[1])).all(axis=1)]
        if len(points) < self.config.minimum_points:
            raise TrackingFailure("insufficient_filtered_initial_depth")
        center, rotation, axes = conservative_pca_enclosure(points, self.config.minimum_axis_m,
                                                            self.config.geometry_margin_m)
        center_pixel, center_depth = self.camera.project(center)
        radius, spacing = self.config.seed_radius_px, self.config.seed_spacing_px
        offset = np.arange(-radius, radius + 1, spacing)
        gx, gy = np.meshgrid(offset, offset)
        seeds = np.rint(center_pixel + np.column_stack((gx.ravel(), gy.ravel()))).astype(np.float32)
        seed_depth, valid_seed = self._depth_at(depth, seeds)
        valid_seed &= ((seeds[:, 0] >= x0) & (seeds[:, 0] < x1)
                       & (seeds[:, 1] >= y0) & (seeds[:, 1] < y1)
                       & (abs(seed_depth - center_depth) <= self.config.depth_consistency_m))
        if valid_seed.sum() < self.config.minimum_points:
            raise TrackingFailure("insufficient_depth_consistent_seeds")
        template = gray[y0:y1, x0:x1].astype(np.float64)
        if template.std() < 2:
            raise TrackingFailure("initial_appearance_has_insufficient_texture")
        self.seed_points = seeds[valid_seed].copy()
        self.current_points = self.seed_points.copy()
        self.seed_depth = seed_depth[valid_seed].copy()
        self.center_pixel = center_pixel.copy()
        self.initial_center = center.copy()
        self.initial_center_depth = center_depth
        self.initial_tracker_position = self.camera.ray_at_height(center_pixel, center[2])
        self.bbox = bbox.copy()
        self.template = template
        self.previous_gray = gray.copy()
        self.last_call_step = step
        self.failure = None
        self.estimate = HazardEstimate(center, rotation, axes, step, "initialized")
        return self.estimate

    def require_safe(self, step):
        if self.failure is not None:
            raise TrackingFailure(self.failure)
        if self.estimate is None:
            raise TrackingFailure("tracker_not_initialized")
        if (not isinstance(step, (int, np.integer)) or step < self.last_call_step):
            return self._fail("non_monotonic_control_step")
        try:
            return self.estimate.require_safe(step, self.config.max_age_steps)
        except TrackingFailure as error:
            return self._fail(str(error))

    def update(self, rgb, depth, step):
        import cv2
        self.require_safe(step)
        self.last_call_step = step
        old = self.estimate
        if step - old.measurement_step < self.config.update_every_steps:
            self.estimate = HazardEstimate(old.center, old.rotation, old.axes, old.measurement_step, "held")
            return self.estimate
        try:
            gray, depth = self._images(rgb, depth)
            if gray.shape != self.previous_gray.shape:
                return self._fail("camera_image_shape_changed")
            lk = dict(winSize=(21, 21), maxLevel=2,
                      criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
            current, forward, _ = cv2.calcOpticalFlowPyrLK(self.previous_gray, gray,
                                                         self.current_points.reshape(-1, 1, 2), None, **lk)
            if current is None:
                return self._fail("optical_flow_lost")
            back, backward, _ = cv2.calcOpticalFlowPyrLK(gray, self.previous_gray, current, None, **lk)
            if back is None:
                return self._fail("backward_flow_lost")
            current, back = current.reshape(-1, 2), back.reshape(-1, 2)
            valid = (forward.reshape(-1).astype(bool) & backward.reshape(-1).astype(bool)
                     & np.isfinite(current).all(axis=1) & np.isfinite(back).all(axis=1)
                     & (np.linalg.norm(back - self.current_points, axis=1) <= self.config.forward_backward_px))
            if valid.sum() < self.config.minimum_points:
                return self._fail("insufficient_forward_backward_support")
            displacement = np.median(current[valid] - self.seed_points[valid], axis=0)
            candidate_position = self.camera.ray_at_height(self.center_pixel + displacement,
                                                          self.initial_center[2])
            candidate = self.initial_center + candidate_position - self.initial_tracker_position
            _, candidate_depth = self.camera.project(candidate)
            measured_depth, valid_depth = self._depth_at(depth, current)
            expected_depth = self.seed_depth + candidate_depth - self.initial_center_depth
            valid &= valid_depth & (abs(measured_depth - expected_depth) <= self.config.depth_consistency_m)
            if valid.sum() < self.config.minimum_points:
                return self._fail("insufficient_depth_consistent_support")
            displacement = np.median(current[valid] - self.seed_points[valid], axis=0)
            candidate_position = self.camera.ray_at_height(self.center_pixel + displacement,
                                                          self.initial_center[2])
            candidate = self.initial_center + candidate_position - self.initial_tracker_position
            if np.linalg.norm(candidate - old.center) > self.config.max_displacement_m:
                return self._fail("maximum_measurement_displacement_exceeded")
            dx, dy = np.rint(displacement).astype(int)
            x0, y0, x1, y1 = self.bbox + np.array([dx, dy, dx, dy])
            if x0 < 0 or y0 < 0 or x1 > gray.shape[1] or y1 > gray.shape[0]:
                return self._fail("appearance_patch_outside_image")
            patch = gray[y0:y1, x0:x1].astype(np.float64)
            left, right = self.template - self.template.mean(), patch - patch.mean()
            denominator = np.linalg.norm(left) * np.linalg.norm(right)
            correlation = float(np.sum(left * right) / denominator) if denominator > 1e-12 else -1.0
            if correlation < self.config.minimum_correlation:
                return self._fail("appearance_correlation_rejected")
            self.seed_points = self.seed_points[valid]
            self.seed_depth = self.seed_depth[valid]
            self.current_points = current[valid].astype(np.float32)
            self.previous_gray = gray.copy()
            self.estimate = HazardEstimate(candidate, old.rotation, old.axes, step, "tracked")
            return self.estimate
        except TrackingFailure as error:
            return self._fail(str(error))
        except cv2.error as error:
            return self._fail("opencv_tracking_error: " + str(error).splitlines()[0])
