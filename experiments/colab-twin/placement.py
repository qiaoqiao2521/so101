"""Upright carried-payload route queries and release/settle acceptance."""
import mujoco
import numpy as np
from grasp_workcell import TARGET_SIZE, PLACE_CENTER


def plan_transport(model, rig, execution, arm_checker, *, solve_ik, pinch_point):
    """Query a measured rigid grasp hypothesis in independent planning data.

    Only this query data sets the hypothetical payload pose. The executing
    object is always free and is moved exclusively by MuJoCo contact forces.
    """
    query = mujoco.MjData(model)
    gripper = model.body('gripper').id
    target_body = model.body('grasp_target').id
    target_geom = model.geom('target_collision').id
    rotation = execution.xmat[gripper].reshape(3, 3)
    relative_pos = rotation.T @ (execution.xpos[target_body] - execution.xpos[gripper])
    relative_rotation = rotation.T @ execution.xmat[target_body].reshape(3, 3)
    world_geoms = [i for i in range(model.ngeom) if model.geom_bodyid[i] == 0
                   and model.geom_contype[i] != 0]
    minimum = float('inf')
    rejected = {}
    def valid(q):
        nonlocal minimum
        arm_result = arm_checker.evaluate(np.r_[q, execution.qpos[5]], require_fixed_gripper=False)
        if not arm_result['valid']:
            rejected.update(arm_result)
            return False
        query.qpos[:6] = np.r_[q, execution.qpos[5]]
        mujoco.mj_forward(model, query)
        r = query.xmat[gripper].reshape(3, 3)
        query.qpos[6:9] = query.xpos[gripper] + r @ relative_pos
        quat = np.empty(4)
        mujoco.mju_mat2Quat(quat, (r @ relative_rotation).flatten())
        query.qpos[9:13] = quat
        mujoco.mj_forward(model, query)
        for geom in world_geoms:
            distance = float(mujoco.mj_geomDistance(model, query, target_geom, geom, .02, None))
            minimum = min(minimum, distance)
            if distance < .0002:
                rejected.update({'pair': model.geom(geom).name, 'payload_distance_m': distance})
                return False
        return True
    # Preserve vertical fingers along a dense Cartesian route; unconstrained
    # five-axis OMPL paths may rotate the grasp and lose the payload.
    r = execution.xmat[gripper].reshape(3, 3)
    current = execution.xpos[gripper] + r @ pinch_point
    centers = [current, [.18, -.13, .06], [.18, 0, .06],
               [.18, .14, .06], [.24, .14, .06], [.24, .14, .023]]
    q = execution.qpos[:5].copy()
    paths = []
    for a, b in zip(centers, centers[1:]):
        a, b = np.asarray(a), np.asarray(b)
        points = [q.copy()]
        for fraction in np.linspace(0, 1, max(2, int(np.ceil(np.linalg.norm(b-a)/.003))+1))[1:]:
            goal = solve_ik(rig, a + (b-a)*fraction, q)
            for t in np.linspace(0, 1, max(2, int(np.ceil(np.linalg.norm(goal-q)/.01))+1)):
                if not valid(q+(goal-q)*t):
                    raise RuntimeError(f'Carried route rejected near {a+(b-a)*fraction}: {rejected}')
            q = goal
            points.append(q.copy())
        paths.append(np.asarray(points))
    return paths, {'kind': 'upright_cartesian_ik', 'waypoints': sum(len(p) for p in paths),
                   'payload_min_distance_m': minimum, 'payload_clearance_m': .0002,
                   'joint_edge_resolution_rad': .01, 'cartesian_resolution_m': .003,
                   'grasp_relative_pos_m': relative_pos.tolist()}


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
