"""Fixed-period state workcell and stage-free physical task acceptance.

No expert is called by reset/step. Privileged object truth is deliberately part
of this state-only diagnostic; it is not a deployable visual policy interface.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import mujoco
import numpy as np

from collision_scene import CollisionChecker
from grasp_workcell import PLACE_CENTER


class SafetyStop(RuntimeError):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or {}


def observe(model, data):
    # mj_step integrates qpos last. Refresh derived poses and solver contacts at
    # the same boundary before copying any observation field.
    from grasp_episode import grasp_contacts
    mujoco.mj_forward(model, data)
    target = model.body('grasp_target').id
    forces = grasp_contacts(model, data)
    obstacle = model.geom('approach_obstacle')
    environment = np.r_[data.qvel[:6], data.xpos[target], data.xquat[target],
                        data.qvel[6:12], [*PLACE_CENTER, .01],
                        data.geom_xpos[obstacle.id], obstacle.size, list(forces.values())]
    return {'observation.state': data.qpos[:6].copy(),
            'observation.environment_state': environment.copy(),
            'time_s': float(data.time)}


def diagnostics(model, data, checker):
    from grasp_episode import grasp_contacts
    from placement import object_inside_tray
    names = [(model.geom(c.geom1).name, model.geom(c.geom2).name) for c in data.contact]
    target = model.body('grasp_target').id
    return {'time_s': float(data.time), 'object_z_m': float(data.xpos[target, 2]),
            'object_xyz_m': data.xpos[target].tolist(),
            'object_speed_m_s': float(np.linalg.norm(data.qvel[6:9])),
            'in_place_tray': object_inside_tray(data.xmat[target].reshape(3, 3), data.xpos[target]),
            'place_floor_contact': any('target_collision' in p and 'place_floor' in p for p in names),
            'tip_forces_n': list(grasp_contacts(model, data).values()),
            'floor_contact': any('target_collision' in p and ('pick_floor' in p or 'worktable' in p) for p in names),
            'obstacle_contact': any('approach_obstacle' in p for p in names),
            'arm_valid': bool(checker.evaluate(data.qpos[:6], require_fixed_gripper=False)['valid']),
            'finite_state': bool(np.all(np.isfinite(data.qpos)) and np.all(np.isfinite(data.qvel)))}


class PhysicalTaskMonitor:
    """Observe sustained contact lift then released, stationary blue-tray rest."""
    def __init__(self, baseline_z):
        self.baseline_z = baseline_z
        self.lift_start = self.settle_start = self.loss_start = None
        self.hold_duration = self.settled_duration = 0.0
        self.grasp_success = self.place_success = self.safety_stop = False
        self.failure_reason = None

    def update(self, row):
        t = row['time_s']
        if row['obstacle_contact'] or not row['arm_valid'] or not row['finite_state']:
            self.failure_reason = 'safety_stop'
            self.safety_stop = True
        lifted = (row['object_z_m'] - self.baseline_z >= .025 and
                  min(row['tip_forces_n']) > .02 and not row['floor_contact'] and
                  not row['place_floor_contact'])
        self.lift_start = (t if self.lift_start is None else self.lift_start) if lifted else None
        if self.lift_start is not None:
            self.hold_duration = max(self.hold_duration, t - self.lift_start)
            self.grasp_success |= self.hold_duration >= 1.0 - 1e-8
        settled = (self.grasp_success and row['in_place_tray'] and row['place_floor_contact'] and
                   max(row['tip_forces_n']) < .02 and row['object_speed_m_s'] < .002 and
                   abs(row['object_z_m'] - .01) < .002)
        self.settle_start = (t if self.settle_start is None else self.settle_start) if settled else None
        self.settled_duration = t-self.settle_start if self.settle_start is not None else 0.0
        self.place_success = self.settled_duration >= 1.0 - 1e-8
        supported_release = (row['in_place_tray'] and row['object_z_m'] < .025 and
                             row['object_speed_m_s'] < .05)
        lost = self.grasp_success and min(row['tip_forces_n']) < .02 and not supported_release
        self.loss_start = (t if self.loss_start is None else self.loss_start) if lost else None
        if self.loss_start is not None and t-self.loss_start >= .1-1e-8:
            self.failure_reason = 'payload_lost'
        return self.report()

    def report(self):
        return {'passed': bool(self.grasp_success and self.place_success and not self.failure_reason),
                'grasp_success': bool(self.grasp_success), 'place_success': bool(self.place_success),
                'hold_duration_s': self.hold_duration, 'settled_duration_s': self.settled_duration,
                'safety_stop': self.safety_stop, 'failure_reason': self.failure_reason}


class StateWorkcell:
    def __init__(self, source, output, metadata):
        from grasp_episode import build_contact_scene
        if hashlib.sha256(Path(source).read_bytes()).hexdigest() != metadata['model_sha256']:
            raise ValueError('Dataset and workcell source model differ')
        output = Path(output)
        output.mkdir(parents=True, exist_ok=False)
        scene = metadata['scene_configuration']
        from grasp_episode import OBSTACLE
        if any(not np.array_equal(scene['obstacle'][key], OBSTACLE[key]) for key in ('pos', 'size')):
            raise ValueError('This fixed-layout workcell does not support another obstacle configuration')
        self.model, rig, _ = build_contact_scene(Path(source), output,
                    jaw_force_cap_nm=scene['jaw_force_cap_nm'], noslip_iterations=scene['noslip_iterations'])
        self.checker = CollisionChecker(rig, gripper=.5, margin_m=.001)
        self.data = mujoco.MjData(self.model)
        self.metadata = metadata
        self.period = metadata['control_period_s']
        if not np.isclose(self.model.opt.timestep, metadata['physics_dt_s']):
            raise ValueError('Dataset physics timestep differs')
        self.ticks = round(self.period/self.model.opt.timestep)
        if self.ticks < 1 or not np.isclose(self.ticks*self.model.opt.timestep, self.period):
            raise ValueError('Control period must be integral physics steps')
        self.baseline_z = scene['baseline_object_z_m']

    def reset(self, joint_offset=None):
        mujoco.mj_resetData(self.model, self.data)
        snapshot = self.metadata['initial_snapshot']
        self.data.qpos[:] = snapshot['qpos']
        self.data.qvel[:] = snapshot['qvel']
        self.data.ctrl[:] = snapshot['ctrl']
        self.data.time = snapshot['time_s']
        if 'qacc_warmstart' in snapshot:
            self.data.qacc_warmstart[:] = snapshot['qacc_warmstart']
        if joint_offset is not None:
            raise ValueError('Use physical step commands for perturbations')
        return observe(self.model, self.data)

    def step(self, action):
        command = np.asarray(action, dtype=float)
        if command.shape != (6,) or not np.isfinite(command).all():
            raise SafetyStop('Nonfinite or malformed policy command')
        bounds = self.model.actuator_ctrlrange
        if np.any(command < bounds[:, 0]) or np.any(command > bounds[:, 1]):
            raise SafetyStop('Policy command exceeds actuator limits',
                             {'action': command.tolist(), 'actuator_bounds': bounds.tolist(),
                              'violating_axes': np.flatnonzero((command < bounds[:, 0]) |
                                                               (command > bounds[:, 1])).tolist(),
                              'observation.state': self.data.qpos[:6].tolist(),
                              'time_s': float(self.data.time)})
        # Match collection: copy a refreshed before-boundary, then hold a target.
        observe(self.model, self.data)
        self.data.ctrl[:] = command
        for _ in range(self.ticks):
            mujoco.mj_step(self.model, self.data)
            obstacle = self.model.geom('approach_obstacle').id
            if any(obstacle in (c.geom1, c.geom2) for c in self.data.contact):
                raise SafetyStop('Obstacle contact during physical step',
                                 {'action': command.tolist(), 'observation.state': self.data.qpos[:6].tolist(),
                                  'time_s': float(self.data.time)})
        obs = observe(self.model, self.data)
        row = diagnostics(self.model, self.data, self.checker)
        if not row['finite_state'] or not row['arm_valid']:
            raise SafetyStop('Nonfinite state, joint limit or self/world collision',
                             {'action': command.tolist(), 'observation.state': obs['observation.state'].tolist(),
                              'time_s': obs['time_s'],
                              'collision': self.checker.evaluate(self.data.qpos[:6], require_fixed_gripper=False)})
        return obs, row
