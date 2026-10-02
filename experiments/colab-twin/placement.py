"""Upright carried-payload route queries and release/settle acceptance."""
import mujoco
import numpy as np
from grasp_workcell import TARGET_SIZE, PLACE_CENTER


def carried_configuration_checker(model, execution, arm_checker):
    """Return a q5/q6 predicate and live audit for a measured grasp hypothesis.

    Freeze the current payload/gripper transform in independent query data.
    q5 uses the execution's measured jaw; q6 supplies its own jaw. This is a
    configuration query, not proof of contact or dynamic grasp stability: the
    caller must admit a sustained live grasp before executing a carried route.
    No execution field is written or forwarded here. Rebuild the predicate if
    the grasp transform changes. World distances saturate at the existing 20mm
    cap and the 0.2mm clearance remains a fixed-layout simulation assumption.
    """
    if (model.nq != 13 or model.nv != 12 or arm_checker.model.nq != 6 or
            not np.isfinite(execution.qpos).all() or not np.isfinite(execution.qvel).all()):
        raise ValueError('Carried query requires a finite SO101/free-payload reference state')
    query = mujoco.MjData(model)
    gripper = model.body('gripper').id
    target_body = model.body('grasp_target').id
    target_geom = model.geom('target_collision').id
    if (not np.isfinite(execution.xpos[[gripper, target_body]]).all() or
            not np.isfinite(execution.xmat[[gripper, target_body]]).all()):
        raise ValueError('Carried query requires finite refreshed gripper/payload poses')
    rotation = execution.xmat[gripper].reshape(3, 3)
    relative_pos = rotation.T @ (execution.xpos[target_body] - execution.xpos[gripper])
    relative_rotation = rotation.T @ execution.xmat[target_body].reshape(3, 3)
    world_geoms = [i for i in range(model.ngeom) if model.geom_bodyid[i] == 0
                   and model.geom_contype[i] != 0]
    audit = {'payload_min_distance_m': None, 'payload_clearance_m': .0002,
             'grasp_relative_pos_m': relative_pos.tolist(), 'last_rejection': {}}

    def valid(q):
        audit['last_rejection'] = {}
        try:
            q = np.asarray(q, dtype=float)
        except (TypeError, ValueError):
            q = np.empty(0)
        if q.shape == (5,):
            q = np.r_[q, execution.qpos[5]]
        if q.shape != (6,) or not np.isfinite(q).all():
            audit['last_rejection'] = {'reason': 'configuration_shape_or_nonfinite'}
            return False
        arm_result = arm_checker.evaluate(q, require_fixed_gripper=False)
        if not arm_result['valid']:
            audit['last_rejection'] = dict(arm_result)
            return False
        query.qpos[:6] = q
        mujoco.mj_forward(model, query)
        r = query.xmat[gripper].reshape(3, 3)
        query.qpos[6:9] = query.xpos[gripper] + r @ relative_pos
        quat = np.empty(4)
        mujoco.mju_mat2Quat(quat, (r @ relative_rotation).flatten())
        query.qpos[9:13] = quat
        mujoco.mj_forward(model, query)
        for geom in world_geoms:
            distance = float(mujoco.mj_geomDistance(model, query, target_geom, geom, .02, None))
            if not np.isfinite(distance):
                audit['last_rejection'] = {'reason': 'nonfinite_payload_distance', 'pair': model.geom(geom).name}
                return False
            minimum = audit['payload_min_distance_m']
            audit['payload_min_distance_m'] = distance if minimum is None else min(minimum, distance)
            if distance < .0002:
                audit['last_rejection'] = {'pair': model.geom(geom).name, 'payload_distance_m': distance}
                return False
        return True

    return valid, audit


def plan_transport(model, rig, execution, arm_checker, *, solve_ik, pinch_point, continue_forward=False):
    """Plan with a measured grasp query; the executing object remains free."""
    valid, audit = carried_configuration_checker(model, execution, arm_checker)
    gripper = model.body('gripper').id
    # Preserve vertical fingers along a dense Cartesian route; unconstrained
    # five-axis OMPL paths may rotate the grasp and lose the payload.
    r = execution.xmat[gripper].reshape(3, 3)
    current = execution.xpos[gripper] + r @ pinch_point
    centers = [current, [.18, -.13, .06], [.18, 0, .06],
               [.18, .14, .06], [.24, .14, .06], [.24, .14, .023]]
    if not isinstance(continue_forward, bool):
        raise ValueError('Forward recovery must be an explicit boolean')
    if continue_forward:
        # Expert-only suffix choice from current Cartesian position. Do not
        # retrace completed transport legs or use a source trajectory clock.
        route = np.asarray(centers[1:], dtype=float)
        edges = np.diff(route, axis=0)
        alpha = np.clip(np.sum((current-route[:-1])*edges, axis=1) /
                        np.sum(edges*edges, axis=1), 0, 1)
        distance = np.linalg.norm(route[:-1]+alpha[:, None]*edges-current, axis=1)
        segment = int(np.argmin(distance))
        centers = [current, *route[segment+1:]]
    q = execution.qpos[:5].copy()
    paths = []
    for a, b in zip(centers, centers[1:]):
        a, b = np.asarray(a), np.asarray(b)
        points = [q.copy()]
        for fraction in np.linspace(0, 1, max(2, int(np.ceil(np.linalg.norm(b-a)/.003))+1))[1:]:
            goal = solve_ik(rig, a + (b-a)*fraction, q)
            for t in np.linspace(0, 1, max(2, int(np.ceil(np.linalg.norm(goal-q)/.01))+1)):
                if not valid(q+(goal-q)*t):
                    raise RuntimeError(f"Carried route rejected near {a+(b-a)*fraction}: {audit['last_rejection']}")
            q = goal
            points.append(q.copy())
        paths.append(np.asarray(points))
    report = {'kind': 'upright_cartesian_ik', 'waypoints': sum(len(p) for p in paths),
                   'payload_min_distance_m': audit['payload_min_distance_m'], 'payload_clearance_m': .0002,
                   'joint_edge_resolution_rad': .01, 'cartesian_resolution_m': .003,
                   'grasp_relative_pos_m': audit['grasp_relative_pos_m']}
    if continue_forward:
        report.update(continue_from_actual_cartesian_projection=True, remaining_centers_m=np.asarray(centers).tolist())
    return paths, report


def placement_acceptance(rows):
    settled = [r for r in rows if r['stage'] == 'settle']
    if not settled:
        return {'place_success': False, 'settled_duration_s': 0.0}
    final = settled[-1]
    carried = [r for r in rows if r['stage'] == 'transport']
    held = bool(carried) and all(min(r['tip_forces_n']) > .02 and not r['floor_contact'] and not r['place_floor_contact'] for r in carried)
    good = all(r['in_place_tray'] and r['place_floor_contact'] and
               max(r['tip_forces_n']) < .02 and r['object_speed_m_s'] < .002
               and abs(r['object_z_m']-.01) < .002 for r in settled)
    duration = settled[-1]['time_s']-settled[0]['time_s']
    return {'place_success': bool(good and held and duration >= 1),
            'settled_duration_s': duration, 'transport_held': held, 'final_object_xyz_m': final['object_xyz_m'],
            'final_object_speed_m_s': final['object_speed_m_s'],
            'released_tip_forces_n': final['tip_forces_n']}


def object_inside_tray(rotation, center):
    # Project the rotated box onto the tray XY axes; check its entire footprint.
    extent = np.abs(rotation) @ (np.array(TARGET_SIZE)/2)
    return bool(np.all(np.abs(center[:2]-np.array(PLACE_CENTER))+extent[:2] <= .058))
