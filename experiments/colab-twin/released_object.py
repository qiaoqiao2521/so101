"""Static estimated-object queries and independent release scoring.

The query owns a six-joint clone. It never receives execution object poses.
The audit consumes simulation truth only for scoring and failure termination.
"""
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from grasp_episode import PAD_NAMES
from grasp_workcell import TARGET_SIZE

BOX_CORNERS = np.array([[x,y,z] for x in (-1.,1.) for y in (-1.,1.) for z in (-1.,1.)])


def box_separation(center, rotation, extent, other_center, other_extent):
    """SAT separation lower bound for an OBB and a world-aligned box.

    A positive value guarantees at least that Euclidean clearance. Inside
    contact, this avoids libccd's unstable signed penetration on these pads.
    """
    axes = [*np.eye(3), *rotation.T]
    axes += [np.cross(a, b) for a in np.eye(3) for b in rotation.T]
    gaps = []
    for axis in axes:
        norm = np.linalg.norm(axis)
        if norm < 1e-10:
            continue
        axis = axis/norm
        radius = np.abs(rotation.T @ axis) @ extent + np.abs(axis) @ other_extent
        gaps.append(abs((center-other_center) @ axis)-radius)
    return float(max(gaps))


class ReleasedObjectQuery:
    def __init__(self, planning_scene, *, uncertainty_m=.002):
        if not np.isfinite(uncertainty_m) or not .002 <= uncertainty_m <= .005:
            raise ValueError('Released-object uncertainty must be 2..5 mm')
        tree = ET.parse(planning_scene)
        root = tree.getroot()
        ET.SubElement(root.find('worldbody'), 'geom', name='estimated_released_box',
                      type='box', size=' '.join(map(str, np.array(TARGET_SIZE)/2+uncertainty_m)),
                      pos='0 0 -1', contype='2', conaffinity='2', group='0')
        # The generated planning scene has absolute asset paths.
        self.model = mujoco.MjModel.from_xml_string(ET.tostring(root, encoding='unicode'))
        if self.model.nq != 6 or self.model.nv != 6:
            raise ValueError('Released-object query requires a static six-joint rig')
        self.data = mujoco.MjData(self.model)
        self.object_id = self.model.geom('estimated_released_box').id
        self.robot_ids = [i for i in range(self.model.ngeom) if self.model.geom_bodyid[i] != 0]
        # Match physical target contact masks, including both group-0 pads.
        # Render-only meshes and the two deliberately replaced fingertip hulls
        # cannot contact the physical block and are excluded identically here.
        self.robot_ids = [i for i in self.robot_ids
                          if (int(self.model.geom_contype[i]) & 2
                              or int(self.model.geom_conaffinity[i]) & 2)]
        self.uncertainty_m = float(uncertainty_m)
        self.center = None

    def freeze(self, center):
        center = np.asarray(center, dtype=float)
        if self.center is not None or center.shape != (3,) or not np.isfinite(center).all():
            raise ValueError('Freeze one finite release estimate only')
        self.center = center.copy()
        self.model.geom_pos[self.object_id] = center

    def distances(self, q6):
        if self.center is None:
            raise ValueError('Release estimate is not frozen')
        q6 = np.asarray(q6, dtype=float)
        if q6.shape != (6,) or not np.isfinite(q6).all():
            raise ValueError('Finite six-joint query required')
        self.data.qpos[:] = q6
        self.data.qvel[:] = 0
        mujoco.mj_forward(self.model, self.data)
        result = {}
        for i in self.robot_ids:
            name = self.model.geom(i).name
            if name in PAD_NAMES:
                distance = box_separation(self.data.geom_xpos[i], self.data.geom_xmat[i].reshape(3,3),
                                          self.model.geom_size[i], self.center,
                                          self.model.geom_size[self.object_id])
            else:
                distance = float(mujoco.mj_geomDistance(self.model, self.data, i, self.object_id, .1, None))
            result[name] = distance
        if not result or not all(np.isfinite(list(result.values()))):
            raise ValueError('Released-object distance query failed')
        return result

    def pad_vertices(self):
        """Vertices at the last distance-query pose; no execution state input."""
        result = {}
        for name in PAD_NAMES:
            i = self.model.geom(name).id
            result[name] = (self.data.geom_xpos[i]
                            + (BOX_CORNERS*self.model.geom_size[i]) @ self.data.geom_xmat[i].reshape(3,3).T)
        return result


def robot_target_force(model, data):
    """Sum all robot-to-target normal forces at one physical integration step."""
    target = model.geom('target_collision').id
    total = 0.
    for index, contact in enumerate(data.contact):
        if target not in (contact.geom1, contact.geom2):
            continue
        other = contact.geom2 if contact.geom1 == target else contact.geom1
        if model.geom_bodyid[other] == 0:
            continue
        wrench = np.zeros(6)
        mujoco.mj_contactForce(model, data, index, wrench)
        total += max(0., float(wrench[0]))
    return total


class ReleaseAudit:
    """Latch detachment and reject subsequent contact or excessive displacement."""
    def __init__(self):
        self.anchor = None
        self.quiet_s = 0.
        self.detached = False
        self.detached_at_s = None
        self.max_xy_drift_m = 0.
        self.post_detach_peak_force_n = 0.
        self.failure_reason = None
        self.samples = 0

    def start(self, xy):
        if self.anchor is None:
            xy = np.asarray(xy, dtype=float)
            if xy.shape != (2,) or not np.isfinite(xy).all():
                raise ValueError('Finite release anchor required')
            self.anchor = xy.copy()

    def update(self, xy, force_n, elapsed_s, dt=.002):
        if self.anchor is None:
            return
        xy = np.asarray(xy, dtype=float)
        if (xy.shape != (2,) or not np.isfinite(xy).all()
                or not np.isfinite([force_n,elapsed_s,dt]).all() or dt <= 0 or force_n < 0):
            self.failure_reason = 'release_audit_invalid_sample'
            return
        self.samples += 1
        drift = float(np.linalg.norm(np.asarray(xy)-self.anchor))
        self.max_xy_drift_m = max(self.max_xy_drift_m, drift)
        if self.detached:
            self.post_detach_peak_force_n = max(self.post_detach_peak_force_n, force_n)
            if force_n > .02:
                self.failure_reason = 'released_object_recontact'
        elif force_n <= .02:
            self.quiet_s += dt
            if self.quiet_s >= .2-1e-9:
                self.detached = True
                self.detached_at_s = float(elapsed_s)
        else:
            self.quiet_s = 0.
        if drift > .002 and self.failure_reason is None:
            self.failure_reason = 'released_object_displaced'

    def report(self):
        return {'passed':self.detached and self.failure_reason is None,
                'detached':self.detached, 'detached_at_s':self.detached_at_s,
                'anchor_xy_m':None if self.anchor is None else self.anchor.tolist(),
                'max_xy_drift_m':self.max_xy_drift_m,
                'post_detach_peak_force_n':self.post_detach_peak_force_n,
                'failure_reason':self.failure_reason, 'samples_2ms':self.samples,
                'thresholds':{'max_xy_drift_m':.002, 'force_n':.02, 'quiet_s':.2}}
