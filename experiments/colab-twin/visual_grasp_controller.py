"""Finite visual-target grasp controller; no execution data or task-truth input.

The target is stationary, axis-aligned, 18 x 18 x 16 mm on the known tray floor.
RGB is refreshed only before a conservative robot-occlusion warning. Thereafter a
bounded static-target hypothesis drives open-loop grasp contact/holding stages;
controller completion is not evidence that an object was actually grasped.
"""
from __future__ import annotations

import math
import mujoco
import numpy as np

from conservative_collision import ConservativeCollisionChecker as CollisionChecker
from configuration_sweep import validate_configuration_path
from grasp_episode import PAD_NAMES, PINCH_POINT, solve_pinch_ik
from grasp_workcell import PLACE_CENTER, TARGET_SIZE
from joint_planner import plan_joint_path, validate_joint_path
from visual_localization import TopDownCalibration


BOX_CORNERS = np.array([[x, y, z] for x in (-1., 1.)
                        for y in (-1., 1.) for z in (-1., 1.)])


class ControllerFailure(RuntimeError):
    pass


def finite_vector(value, size, name):
    result = np.asarray(value, dtype=float)
    if result.shape != (size,) or not np.isfinite(result).all():
        raise ValueError(f'{name} requires {size} finite values')
    return result.copy()


def box_clearance(center, extent, world_center, world_extent):
    """Conservative signed AABB clearance; positive means disjoint volumes."""
    gap = np.abs(np.asarray(center)-world_center)-extent-world_extent
    return float(np.linalg.norm(np.maximum(gap, 0))) if np.any(gap > 0) else float(np.max(gap))


def projected_box_bounds(center, extent, calibration):
    """Conservative pixel bounds for a world AABB and fixed downward camera."""
    center, extent = np.asarray(center), np.asarray(extent)
    camera = np.asarray(calibration.camera_position_m)
    if center[2]-extent[2] >= camera[2]:
        return None  # Entirely behind the camera.
    if center[2]+extent[2] >= camera[2]:
        return np.array([-np.inf, -np.inf, np.inf, np.inf])
    points = center+BOX_CORNERS*extent
    depth = camera[2]-points[:, 2]
    pixels = (points[:, :2]-camera[:2])/depth[:, None]
    pixels *= np.array([calibration.focal_px, -calibration.focal_px])
    pixels += np.asarray(calibration.principal_px)
    return np.r_[pixels.min(axis=0), pixels.max(axis=0)]


def bounds_overlap(first, second):
    return (first is not None and second is not None
            and bool(np.all(np.asarray(first)[:2] <= np.asarray(second)[2:])
                     and np.all(np.asarray(second)[:2] <= np.asarray(first)[2:])))


def sample_minimum_jerk(points, fraction):
    points = np.asarray(points, dtype=float)
    lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    cumulative = np.r_[0., np.cumsum(lengths)]
    if cumulative[-1] < 1e-12:
        return points[-1].copy()
    t = float(np.clip(fraction, 0, 1))
    distance = t**3*(10+t*(-15+6*t))*cumulative[-1]
    segment = min(max(0, int(np.searchsorted(cumulative, distance, side='right')-1)), len(points)-2)
    alpha = (distance-cumulative[segment])/max(lengths[segment], 1e-12)
    return points[segment]+alpha*(points[segment+1]-points[segment])


def motion_duration(points):
    return max(2., float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())*1.875/.3)


def shorten_path(points, valid, max_checks=128):
    """Greedily shortcut only independently validated edges, with bounded work."""
    points = np.asarray(points, dtype=float)
    result = [points[0]]
    index = 0
    checks = 0
    while index < len(points)-1:
        next_index = index+1
        for candidate in range(len(points)-1, index+1, -1):
            if checks >= max_checks:
                break
            checks += 1
            if validate_joint_path([points[index], points[candidate]], valid, .005)['valid']:
                next_index = candidate
                break
        result.append(points[next_index])
        index = next_index
    if not validate_joint_path(result, valid, .005)['valid']:
        raise ControllerFailure('shortened_return_path_invalid')
    return np.asarray(result)


class VisualGraspController:
    """Only the six-joint planning model, encoder arrays and RGB estimates enter."""
    def __init__(self, rig, target_xy, initial_q6, *, seed=0, target_timestamp_s=0.,
                 estimate_ttl_s=1., payload_uncertainty_m=.002, released_query=None):
        if rig.nq != 6 or rig.nv != 6:
            raise ValueError('Use the six-joint planning rig without a free target')
        if (not np.isfinite(estimate_ttl_s) or not 0 < estimate_ttl_s <= 1
                or not np.isfinite(payload_uncertainty_m) or not .002 <= payload_uncertainty_m <= .005
                or not np.isfinite(target_timestamp_s) or target_timestamp_s < 0):
            raise ValueError('Invalid observation lifetime or payload uncertainty')
        self.rig = rig
        self.query = mujoco.MjData(rig)  # Independent FK only, never mj_step.
        self.calibration = TopDownCalibration.from_mujoco_model(rig)
        self.visible_robot_geoms = []
        for i in range(rig.ngeom):
            material = int(rig.geom_matid[i])
            alpha = rig.mat_rgba[material, 3] if material >= 0 else rig.geom_rgba[i, 3]
            if rig.geom_bodyid[i] != 0 and 0 <= rig.geom_group[i] <= 2 and alpha > 0:
                self.visible_robot_geoms.append(i)
        self.gripper_id = rig.body('gripper').id
        self.checker = CollisionChecker(rig, gripper=.5, margin_m=.001)
        self.initial_q = finite_vector(initial_q6, 6, 'initial_q6')
        self.last_command = self.initial_q.copy()
        self.reference = self.initial_q.copy()
        self.servo_offset = np.zeros(5)
        self.servo_transitions = []
        self.target_xy = self._target(target_xy)
        self.target_timestamp = float(target_timestamp_s)
        self.estimate_ttl = float(estimate_ttl_s)
        self.payload_uncertainty = float(payload_uncertainty_m)
        self.seed = int(seed)
        self.replans = 0
        self.target_frozen = False
        self.freeze_record = None
        self.stage = 'approach'
        self.stage_started = 0.
        self.last_elapsed = -1.
        self.failure_reason = None
        self.done = False
        self.transport = []
        self.transport_index = 0
        self.payload_relative = None
        self.payload_rotation = None
        self.released_query = released_query
        self.release_record = None
        self.plan_reports = []
        self.sweep_reports = []
        self._plan_approach(self.initial_q[:5])
        self._set_motion(self.approach_path, .5, 0.)
        self.world = []
        mujoco.mj_forward(rig, self.query)
        for i in range(rig.ngeom):
            if rig.geom_bodyid[i] != 0 or rig.geom_contype[i] == 0:
                continue
            kind = int(rig.geom_type[i])
            rotation = self.query.geom_xmat[i].reshape(3, 3).copy()
            if kind not in (int(mujoco.mjtGeom.mjGEOM_BOX), int(mujoco.mjtGeom.mjGEOM_PLANE)):
                raise ValueError('Payload query only supports the known box/plane static map')
            self.world.append((rig.geom(i).name, kind, self.query.geom_xpos[i].copy(),
                               rotation, rig.geom_size[i].copy()))

    @staticmethod
    def _target(xy):
        xy = finite_vector(xy, 2, 'target_xy')
        if np.any(np.abs(xy-np.array([.24, -.13])) > .0100001):
            raise ValueError('Target outside the declared red-tray +/-10 mm region')
        return xy

    def _fk(self, q6):
        self.query.qpos[:] = q6
        self.query.qvel[:] = 0
        mujoco.mj_forward(self.rig, self.query)
        rotation = self.query.xmat[self.gripper_id].reshape(3, 3).copy()
        origin = self.query.xpos[self.gripper_id].copy()
        return origin, rotation, origin+rotation @ PINCH_POINT

    def _arm_valid(self, q5, jaw):
        return self.checker.evaluate(np.r_[q5, jaw], require_fixed_gripper=False)['valid']

    def _plan_approach(self, current):
        self.approach = solve_pinch_ik(self.rig, np.r_[self.target_xy, .06], current)
        self.down = solve_pinch_ik(self.rig, np.r_[self.target_xy, .019], self.approach)
        self.lift = solve_pinch_ik(self.rig, np.r_[self.target_xy, .06], self.down)
        plan = plan_joint_path(current, self.approach, self.checker.bounds,
                               lambda q: self._arm_valid(q, .5), seed=self.seed,
                               timeout_s=10, resolution_rad=.015)
        self.plan_reports.append(plan)
        if plan['status'] != 'solved':
            raise ControllerFailure('approach_planning_failed')
        for points, jaw in (([self.approach, self.down], .5), ([self.down, self.lift], .015)):
            if not validate_joint_path(points, lambda q: self._arm_valid(q, jaw), .005)['valid']:
                raise ControllerFailure('grasp_leg_collision')
        sweep = self._configuration_sweep(np.r_[self.down, .5], np.r_[self.down, .015])
        self.sweep_reports.append({'stage': 'planned_closure', **sweep})
        if not sweep['valid']:
            raise ControllerFailure('grasp_closure_sweep_invalid')
        self.approach_path = np.asarray(plan['path'])

    def _configuration_sweep(self, start, end):
        return validate_configuration_path(
            start, end, lambda q: self.checker.evaluate(q, require_fixed_gripper=False)['valid'],
            arm_resolution_rad=.005, jaw_resolution_rad=.002, max_samples=4096)

    def _set_motion(self, points, jaw, elapsed):
        self.points = np.asarray(points, dtype=float)
        self.jaw = float(jaw)
        self.duration = motion_duration(self.points)
        self.stage_started = float(elapsed)

    def _set_dwell(self, stage, q5, jaw, elapsed, duration):
        self.stage = stage
        self._set_motion([q5, q5], jaw, elapsed)
        self.duration = duration

    def _set_continuous_motion(self, points, elapsed):
        """Preserve holding bias while planning in achieved-configuration space.

        A position actuator's setpoint is not its achieved configuration under
        load. Capture the small equilibrium offset once per stage, never each
        tick. Geometry guards still inspect the reference and measured q.
        """
        points = np.asarray(points, dtype=float)
        offset = self.last_command[:5]-points[0]
        if not np.isfinite(offset).all() or np.max(np.abs(offset)) > .003:
            raise ControllerFailure('servo_offset_exceeds_arrival_tolerance')
        mapped = np.c_[points+offset, np.full(len(points), .5)]
        for bounds in (self.rig.jnt_range, self.rig.actuator_ctrlrange):
            if np.any(mapped < bounds[:,0]) or np.any(mapped > bounds[:,1]):
                raise ControllerFailure('mapped_servo_target_out_of_bounds')
        self.servo_offset = offset.copy()
        self.servo_start_command = self.last_command.copy()
        self.servo_transitions.append({'stage':self.stage, 'elapsed_s':float(elapsed),
                                       'reference_start':points[0].tolist(),
                                       'previous_command':self.last_command.tolist(),
                                       'fixed_offset_rad':offset.tolist()})
        self._set_motion(points, .5, elapsed)

    def _ingest_estimate(self, estimate, elapsed):
        if estimate is None or self.target_frozen:
            return
        if not isinstance(estimate, dict) or type(estimate.get('valid')) is not bool:
            raise ControllerFailure('malformed_visual_estimate')
        if not estimate['valid']:
            raise ControllerFailure('visual_estimate_rejected')
        stamp = estimate.get('timestamp_s')
        if (isinstance(stamp, bool) or not isinstance(stamp, (int, float)) or not np.isfinite(stamp)
                or stamp > elapsed+1e-9 or stamp < self.target_timestamp
                or elapsed-stamp > self.estimate_ttl):
            raise ControllerFailure('stale_or_future_visual_estimate')
        xy = self._target(estimate['xy'])
        # Existing path may retain sub-mm measurement jitter; update its target
        # at the hand-over replan, never through a simulator object pose.
        self.latest_xy = xy
        self.target_timestamp = float(stamp)

    def _occlusion_warning(self, q6, elapsed):
        """FK and known geometry only; never sample the execution free object.

        Spheres bounded by world cubes intentionally overestimate silhouettes.
        Probe the measured pose and existing planned commands 0.25/0.5s ahead;
        this predicts hand-over before the next scheduled RGB observation.
        """
        xy = getattr(self, 'latest_xy', self.target_xy)
        target_center = np.r_[xy, self.calibration.top_plane_z_m-TARGET_SIZE[2]/2]
        extent = np.array(TARGET_SIZE)/2 + np.array([.002, .002, .0005])
        target_bounds = projected_box_bounds(target_center, extent, self.calibration)
        candidates = [(0., q6)]
        if self.stage == 'approach':
            for lookahead in (.25, .5):
                fraction = (elapsed-self.stage_started+lookahead)/max(self.duration, 1e-9)
                candidates.append((lookahead, np.r_[sample_minimum_jerk(self.points, fraction), self.jaw]))
        for lookahead, candidate in candidates:
            self._fk(candidate)
            for geom_id in self.visible_robot_geoms:
                center = self.query.geom_xpos[geom_id]
                radius = float(self.rig.geom_rbound[geom_id])
                # A robot envelope entirely below the box cannot occlude its
                # visible top. This is conservative in depth, not an RGB claim.
                if center[2]+radius < self.calibration.top_plane_z_m:
                    continue
                robot_bounds = projected_box_bounds(center, np.full(3, radius), self.calibration)
                if bounds_overlap(robot_bounds, target_bounds):
                    return {'geom_id': int(geom_id), 'body': self.rig.body(int(self.rig.geom_bodyid[geom_id])).name,
                            'lookahead_s': lookahead, 'robot_bounds_px': robot_bounds.tolist(),
                            'target_bounds_px': target_bounds.tolist(),
                            'target_xy_uncertainty_m': .002}
        return None

    def replan_approach(self, q6, elapsed, estimate):
        if self.stage != 'approach' or self.target_frozen:
            raise ControllerFailure('replan_outside_visible_approach')
        if self.replans >= 3:
            raise ControllerFailure('approach_replan_budget')
        q6 = finite_vector(q6, 6, 'q6')
        self._ingest_estimate(estimate, elapsed)
        if elapsed-self.target_timestamp > self.estimate_ttl:
            raise ControllerFailure('visual_estimate_expired')
        self.target_xy = getattr(self, 'latest_xy', self.target_xy).copy()
        self._plan_approach(q6[:5])
        self._set_motion(self.approach_path, .5, elapsed)
        self.replans += 1

    def _payload_valid(self, q5):
        q6 = np.r_[q5, .015]
        if not self._arm_valid(q5, .015):
            return False
        origin, rotation, _ = self._fk(q6)
        center = origin+rotation @ self.payload_relative
        object_rotation = rotation @ self.payload_rotation
        for _, kind, world_center, world_rotation, size in self.world:
            local_center = world_rotation.T @ (center-world_center)
            extent = np.abs(world_rotation.T @ object_rotation) @ (np.array(TARGET_SIZE)/2)
            extent += self.payload_uncertainty
            if kind == int(mujoco.mjtGeom.mjGEOM_PLANE):
                distance = float(local_center[2]-extent[2])
            else:
                distance = box_clearance(local_center, extent, np.zeros(3), size)
            if not np.isfinite(distance) or distance < .0002:
                return False
        return True

    def _plan_transport(self, q6):
        _, _, current = self._fk(q6)
        centers = [current, [.18, self.target_xy[1], .06], [.18, 0, .06],
                   [.18, PLACE_CENTER[1], .06], [*PLACE_CENTER, .06], [*PLACE_CENTER, .023]]
        q = q6[:5].copy()
        self.transport = []
        for a, b in zip(centers, centers[1:]):
            a, b = np.asarray(a), np.asarray(b)
            points = [q.copy()]
            for fraction in np.linspace(0, 1, max(2, int(np.ceil(np.linalg.norm(b-a)/.003))+1))[1:]:
                goal = solve_pinch_ik(self.rig, a+(b-a)*fraction, q)
                if not validate_joint_path([q, goal], self._payload_valid, .01)['valid']:
                    raise ControllerFailure('estimated_payload_route_collision')
                q = goal
                points.append(q.copy())
            self.transport.append(np.asarray(points))
        self.transport_index = 0

    def _released_valid(self, q5, jaw=.5):
        return (self._arm_valid(q5, jaw)
                and min(self.released_query.distances(np.r_[q5, jaw]).values()) >= .001)

    def _separation_valid(self, q5, jaw=.5):
        if not self._arm_valid(q5, jaw):
            return False
        _, _, pinch = self._fk(np.r_[q5, jaw])
        if (np.linalg.norm(pinch[:2]-self.separation_pinch[:2]) > .0002
                or pinch[2] < self.separation_pinch[2]-.0002):
            return False
        distances = self.released_query.distances(np.r_[q5, jaw])
        if not all(distance >= self.separation_floors.get(name, .001)
                   for name, distance in distances.items()):
            return False
        vertices = self.released_query.pad_vertices()
        return all(np.max(np.abs(vertices[name][:,:2]-baseline[:,:2])) <= .0002
                   and np.min(vertices[name][:,2]-self.separation_high_z[name]) >= -.00005
                   for name, baseline in self.separation_vertices.items())

    def _return_path(self, start):
        direct = [start, self.initial_q[:5]]
        if validate_joint_path(direct, self._released_valid, .005)['valid']:
            return np.asarray(direct), 'validated_direct'
        plan = plan_joint_path(start, self.initial_q[:5], self.checker.bounds,
                               self._released_valid, seed=self.seed, timeout_s=10, resolution_rad=.005)
        self.plan_reports.append(plan)
        if plan['status'] != 'solved':
            raise ControllerFailure('released_object_return_planning_failed')
        return shorten_path(plan['path'], self._released_valid), 'validated_ompl_shortcuts'

    def _plan_separation(self, q6, elapsed):
        if q6[5] < .45:
            raise ControllerFailure('release_jaw_not_open')
        _, _, self.separation_pinch = self._fk(q6)
        distances = self.released_query.distances(q6)
        # Inflation may overlap a pad that is touching the released object.
        # This exception is local to vertical separation and never permits
        # deeper penetration or lateral return through the object.
        self.separation_floors = {}
        for name, distance in distances.items():
            if distance < .001:
                if name not in PAD_NAMES or distance < -.003:
                    raise ControllerFailure('release_initial_overlap_not_allowed')
                self.separation_floors[name] = distance-.00005
        self.separation_vertices = {name:v for name,v in self.released_query.pad_vertices().items()
                                    if name in self.separation_floors}
        self.separation_high_z = {name:v[:,2].copy() for name,v in self.separation_vertices.items()}
        points = [q6[:5].copy()]
        previous = distances
        for dz in np.linspace(0, .037, 14)[1:]:
            q = solve_pinch_ik(self.rig, self.separation_pinch+[0, 0, dz], points[-1])
            if not validate_joint_path([points[-1], q], self._separation_valid, .002)['valid']:
                raise ControllerFailure('vertical_separation_invalid')
            current = self.released_query.distances(np.r_[q, .5])
            if any(current[name] < min(previous[name], .001)-.00005
                   for name in self.separation_floors):
                raise ControllerFailure('vertical_separation_deepens_contact')
            previous = current
            points.append(q)
        if not self._released_valid(points[-1]):
            raise ControllerFailure('vertical_separation_did_not_clear')
        return_path, method = self._return_path(points[-1])
        required_s = motion_duration(points)+.6+motion_duration(return_path)+.6+1.5+.6+.1
        if elapsed+required_s > 90:
            raise ControllerFailure('insufficient_time_for_safe_return')
        self.release_record.update(separation_path=np.asarray(points).tolist(),
                                   initial_distances_m=distances, separation_floors_m=self.separation_floors.copy(),
                                   return_method=method, planned_return_path=return_path.tolist(),
                                   predicted_completion_s=elapsed+required_s)
        self.plan_reports.append({'stage':'release_return', **self.release_record})
        self.stage = 'separate'
        self._set_continuous_motion(points, elapsed)

    def _transition(self, q6, elapsed):
        if self.stage == 'approach':
            if not self.target_frozen:
                raise ControllerFailure('approach_finished_without_visual_handover')
            self.stage = 'descend'
            self._set_motion([q6[:5], self.down], .5, elapsed)
        elif self.stage == 'descend':
            sweep = self._configuration_sweep(q6, np.r_[self.down, .015])
            self.sweep_reports.append({'stage': 'measured_closure', **sweep})
            if not sweep['valid']:
                raise ControllerFailure('measured_closure_sweep_invalid')
            self._set_dwell('close', self.down, .015, elapsed, 6.)
        elif self.stage == 'close':
            origin, rotation, _ = self._fk(q6)
            self.payload_relative = rotation.T @ (np.r_[self.target_xy, .010]-origin)
            self.payload_rotation = rotation.T  # Known axis-aligned box hypothesis.
            self.stage = 'lift'
            self._set_motion([q6[:5], self.lift], .015, elapsed)
        elif self.stage == 'lift':
            self._set_dwell('hold', self.lift, .015, elapsed, 1.5)
        elif self.stage == 'hold':
            self._plan_transport(q6)
            self.stage = 'transport'
            self._set_motion(self.transport[0], .015, elapsed)
        elif self.stage in ('transport', 'lower'):
            self.transport_index += 1
            if self.transport_index < len(self.transport):
                self.stage = 'lower' if self.transport_index == len(self.transport)-1 else 'transport'
                self._set_motion(self.transport[self.transport_index], .015, elapsed)
            else:
                if self.released_query is None:
                    raise ControllerFailure('released_object_query_missing')
                origin, rotation, _ = self._fk(q6)
                center = origin+rotation @ self.payload_relative
                center[2] = .010  # Known tray support height; no execution pose.
                self.released_query.freeze(center)
                self.release_record = {'estimated_center_m':center.tolist(),
                                       'uncertainty_m':self.released_query.uncertainty_m,
                                       'estimate_frozen_at_s':elapsed,
                                       'source':'pre-opening FK and carried estimate; known support height'}
                self._set_dwell('release', self.points[-1], .5, elapsed, 6.)
        elif self.stage == 'release':
            self._plan_separation(q6, elapsed)
        elif self.stage == 'separate':
            points, method = self._return_path(q6[:5])
            if elapsed+motion_duration(points)+.6+1.5+.6+.1 > 90:
                raise ControllerFailure('insufficient_time_for_safe_return')
            self.plan_reports.append({'stage':'return_from_measured_pose', 'method':method,
                                      'path':points.tolist(), 'duration_s':motion_duration(points)})
            self.stage = 'retreat'
            self._set_continuous_motion(points, elapsed)
        elif self.stage == 'retreat':
            # Retain the terminal reference and holding offset across dwell.
            self.servo_start_command = self.last_command.copy()
            self.servo_transitions.append({'stage':'settle', 'elapsed_s':float(elapsed),
                                           'reference_start':self.initial_q[:5].tolist(),
                                           'previous_command':self.last_command.tolist(),
                                           'fixed_offset_rad':self.servo_offset.tolist()})
            self._set_dwell('settle', self.initial_q[:5], .5, elapsed, 1.5)
        elif self.stage == 'settle':
            self.done = True

    def update(self, q6, qvel6, elapsed, estimate=None):
        q6 = finite_vector(q6, 6, 'q6')
        qvel6 = finite_vector(qvel6, 6, 'qvel6')
        try:
            if self.done:
                return self._result(self.last_command)
            if not np.isfinite(elapsed) or elapsed < self.last_elapsed or elapsed < 0 or elapsed > 90:
                raise ControllerFailure('invalid_or_expired_controller_time')
            self.last_elapsed = float(elapsed)
            if self.failure_reason:
                return self._result(q6)
            if not self.checker.evaluate(q6, require_fixed_gripper=False)['valid']:
                raise ControllerFailure('measured_arm_configuration_invalid')
            if self.stage in ('retreat', 'settle') and not self._released_valid(q6[:5], q6[5]):
                raise ControllerFailure('measured_released_object_clearance_invalid')
            if self.stage == 'separate':
                if not self._separation_valid(q6[:5], q6[5]):
                    raise ControllerFailure('measured_separation_invalid')
                distances = self.released_query.distances(q6)
                vertices = self.released_query.pad_vertices()
                for name in self.separation_high_z:
                    self.separation_high_z[name] = np.maximum(self.separation_high_z[name], vertices[name][:,2])
                for name in list(self.separation_floors):
                    # Once clear, the initial-contact exception cannot return.
                    if distances[name] >= .001:
                        del self.separation_floors[name]
                    else:
                        self.separation_floors[name] = max(self.separation_floors[name], distances[name]-.00005)
            if not self.target_frozen:
                if elapsed-self.target_timestamp > self.estimate_ttl:
                    raise ControllerFailure('visual_estimate_expired')
                warning = self._occlusion_warning(q6, elapsed)
                if warning is not None:
                    # Do not rescue a rejected image. Do not ingest a possibly
                    # biased image on the predicted occlusion boundary either.
                    if estimate is not None and (not isinstance(estimate, dict)
                            or type(estimate.get('valid')) is not bool or not estimate['valid']):
                        raise ControllerFailure('visual_estimate_rejected')
                    latest = getattr(self, 'latest_xy', self.target_xy)
                    if np.linalg.norm(latest-self.target_xy) > .0005:
                        self.replan_approach(q6, elapsed, None)
                    self.target_frozen = True
                    self.freeze_record = {'elapsed_s': elapsed, 'estimate_timestamp_s': self.target_timestamp,
                                          'target_xy': self.target_xy.tolist(), 'occlusion_warning': warning,
                                          'assumption': 'stationary target until close; no post-handover visual servo'}
                else:
                    self._ingest_estimate(estimate, elapsed)
            age = elapsed-self.stage_started
            if age > self.duration+8:
                raise ControllerFailure('encoder_stage_timeout')
            arm_arrived = np.max(np.abs(q6[:5]-self.points[-1])) <= .003 and np.linalg.norm(qvel6[:5]) < .05
            if age >= self.duration+.6 and arm_arrived:
                self._transition(q6, elapsed)
                age = 0.
            self.reference = np.r_[sample_minimum_jerk(self.points, age/max(self.duration, 1e-9)), self.jaw]
            command = self.reference.copy()
            if self.stage in ('separate', 'retreat', 'settle'):
                command[:5] += self.servo_offset
                if age == 0:
                    command = self.servo_start_command.copy()
                for bounds in (self.rig.jnt_range, self.rig.actuator_ctrlrange):
                    if np.any(command < bounds[:,0]) or np.any(command > bounds[:,1]):
                        raise ControllerFailure('mapped_servo_target_out_of_bounds')
            if self.stage in ('transport', 'lower'):
                valid = self._payload_valid
            elif self.stage == 'separate':
                valid = self._separation_valid
            elif self.stage in ('retreat', 'settle'):
                valid = self._released_valid
            else:
                valid = lambda q: self._arm_valid(q, self.jaw)
            # Query achieved geometry, including the measured jaw. The loaded
            # servo setpoint can differ from this reference by a fixed bias.
            sweep = self._configuration_sweep(q6, self.reference)
            self.last_sweep_report = sweep
            if (not sweep['valid'] or
                    not validate_joint_path([q6[:5], self.reference[:5]], valid, .005)['valid']):
                if self.stage == 'approach' and not self.target_frozen and estimate is not None:
                    self.replan_approach(q6, elapsed, estimate)
                    command = q6.copy()
                    self.reference = command.copy()
                else:
                    raise ControllerFailure('current_pose_command_chord_invalid')
            return self._result(command)
        except (ControllerFailure, ValueError, RuntimeError) as error:
            self.failure_reason = str(error)
            return self._result(q6)

    def _result(self, command):
        if self.failure_reason is None:
            self.last_command = np.asarray(command).copy()
        return {'command': np.asarray(command).copy(), 'stage': self.stage, 'done': self.done,
                'geometric_reference':self.reference.copy(), 'servo_offset':self.servo_offset.copy(),
                'status': 'failed' if self.failure_reason else 'done' if self.done else 'running',
                'failure_reason': self.failure_reason, 'target_frozen': self.target_frozen,
                'replans': self.replans, 'controller_completion_is_task_success': False}
