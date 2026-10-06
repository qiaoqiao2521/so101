"""Controller protocol/state-machine tests with fake FK/planning, no physics."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock
import numpy as np
import visual_grasp_controller as module


class VisualControllerTests(unittest.TestCase):
    def controller(self):
        rig = SimpleNamespace(nq=6, nv=6, ngeom=0,
                              jnt_range=np.tile([-3.,3.],(6,1)),
                              actuator_ctrlrange=np.tile([-3.,3.],(6,1)),
                              body=lambda name: SimpleNamespace(id=0))
        query = SimpleNamespace(qpos=np.zeros(6), qvel=np.zeros(6),
                                xpos=np.zeros((1, 3)), xmat=np.eye(3).reshape(1, 9))
        checker = Mock(bounds=np.tile([-3., 3.], (5, 1)))
        checker.evaluate.return_value = {'valid': True}

        def forward(rig, data):
            data.xpos[0] = data.qpos[:3] - module.PINCH_POINT

        def solve(rig, xyz, initial=None):
            return np.r_[xyz, 0., 0.]

        def plan(start, goal, *args, **kwargs):
            return {'status': 'solved', 'path': [list(start), list(goal)]}

        for target, replacement in [
            ('CollisionChecker', Mock(return_value=checker)),
            ('solve_pinch_ik', solve), ('plan_joint_path', plan),
        ]:
            p = patch.object(module, target, replacement)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(module.mujoco, 'MjData', return_value=query)
        p.start()
        self.addCleanup(p.stop)
        p = patch.object(module.mujoco, 'mj_forward', side_effect=forward)
        p.start()
        self.addCleanup(p.stop)
        p = patch.object(module.TopDownCalibration, 'from_mujoco_model',
                         return_value=module.TopDownCalibration())
        p.start()
        self.addCleanup(p.stop)
        return module.VisualGraspController(rig, [.24, -.13], [.24, .14, .06, 0, 0, .5])

    def test_minimum_jerk_endpoints_and_monotonic_waypoint_progress(self):
        path = np.array([[0., 0, 0, 0, 0], [1., 0, 0, 0, 0], [1., 1., 0, 0, 0]])
        np.testing.assert_array_equal(module.sample_minimum_jerk(path, 0), path[0])
        np.testing.assert_array_equal(module.sample_minimum_jerk(path, 1), path[-1])
        sampled = np.array([module.sample_minimum_jerk(path, t) for t in np.linspace(0, 1, 21)])
        self.assertTrue(np.all(np.diff(sampled[:, :2], axis=0) >= -1e-12))

    def test_observation_expires_before_handover(self):
        c = self.controller()
        c._occlusion_warning = lambda q, elapsed: {'lookahead_s': .5}
        result = c.update(c.initial_q.copy(), np.zeros(6), 1.01)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failure_reason'], 'visual_estimate_expired')
        self.assertFalse(c.target_frozen)

    def test_invalid_image_cannot_trigger_target_freeze(self):
        c = self.controller()
        c._occlusion_warning = lambda q, elapsed: {'lookahead_s': .5}
        q = np.array([.27, -.13, .06, 0, 0, .5])
        result = c.update(q, np.zeros(6), .5, {'valid': False, 'timestamp_s': .5})
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(c.target_frozen)

    def test_occlusion_warning_freezes_prior_valid_estimate_not_current_biased_image(self):
        c = self.controller()
        c._occlusion_warning = lambda q, elapsed: {'lookahead_s': .5}
        q = np.array([.27, -.13, .06, 0, 0, .5])
        result = c.update(q, np.zeros(6), .5,
                          {'valid': True, 'xy': [.245, -.13], 'timestamp_s': .5})
        self.assertEqual(result['status'], 'running')
        self.assertTrue(result['target_frozen'])
        self.assertEqual(c.freeze_record['estimate_timestamp_s'], 0)
        np.testing.assert_array_equal(c.target_xy, [.24, -.13])
        self.assertIn('stationary target', c.freeze_record['assumption'])
        result = c.update(q, np.zeros(6), 2., {'valid': False, 'timestamp_s': 2.})
        self.assertEqual(result['status'], 'running')
        self.assertFalse(result['controller_completion_is_task_success'])

    def test_projection_overlap_and_depth_direction(self):
        calibration = module.TopDownCalibration()
        target = module.projected_box_bounds([.24, -.13, .010], [.011, .011, .0085], calibration)
        aligned = module.projected_box_bounds([.244, -.078, .386], [.006, .006, .006], calibration)
        separated = module.projected_box_bounds([.1, .2, .3], [.006, .006, .006], calibration)
        self.assertTrue(module.bounds_overlap(target, aligned))
        self.assertFalse(module.bounds_overlap(target, separated))
        self.assertIsNone(module.projected_box_bounds([0, 0, 1.1], [.01]*3, calibration))

    def test_occlusion_uses_visible_robot_and_front_depth_not_target_truth(self):
        c = self.controller()
        c.visible_robot_geoms = [0]
        c.rig.geom_rbound = np.array([.006])
        c.rig.geom_bodyid = np.array([1])
        c.rig.body = lambda i: SimpleNamespace(name='forearm')
        c.query.geom_xpos = np.array([[.244, -.078, .386]])
        warning = c._occlusion_warning(c.initial_q, 0.)
        self.assertEqual(warning['body'], 'forearm')
        self.assertEqual(warning['lookahead_s'], 0.)
        c.query.geom_xpos[0] = [.24, -.13, -.02]
        self.assertIsNone(c._occlusion_warning(c.initial_q, 0.))

    def test_future_observation_and_backward_clock_fail(self):
        c = self.controller()
        q = c.initial_q.copy()
        result = c.update(q, np.zeros(6), .5,
                          {'valid': True, 'xy': [.24, -.13], 'timestamp_s': .6})
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failure_reason'], 'stale_or_future_visual_estimate')
        c.failure_reason = None
        result = c.update(q, np.zeros(6), .4)
        self.assertEqual(result['failure_reason'], 'invalid_or_expired_controller_time')

    def test_close_dwell_uses_encoders_not_object_or_grasp_truth(self):
        c = self.controller()
        c.target_frozen = True
        c._set_dwell('close', c.down, .015, 0, 6.)
        q = np.r_[c.down, .2]  # Jaw need not fully close around a hypothetical payload.
        result = c.update(q, np.zeros(6), 6.0)
        self.assertEqual(result['stage'], 'close')
        result = c.update(q, np.zeros(6), 6.61)
        self.assertEqual(result['stage'], 'lift')
        self.assertFalse(result['controller_completion_is_task_success'])
        np.testing.assert_allclose(c.payload_rotation, np.eye(3))

    def test_uncertain_payload_envelope_preserves_point_two_mm_margin(self):
        c = self.controller()
        c.payload_relative = np.zeros(3)
        c.payload_rotation = np.eye(3)
        c._fk = lambda q: (np.array([0., 0., .020]), np.eye(3), np.zeros(3))
        c.world = [('wall', int(module.mujoco.mjtGeom.mjGEOM_BOX),
                    np.array([.0211, 0., .020]), np.eye(3), np.array([.01, .1, .1]))]
        # .0211 - .009 - .002 - .010 = .0001, less than the .0002 margin.
        self.assertFalse(c._payload_valid(np.zeros(5)))
        c.world[0] = ('wall', int(module.mujoco.mjtGeom.mjGEOM_BOX),
                      np.array([.0213, 0., .020]), np.eye(3), np.array([.01, .1, .1]))
        self.assertTrue(c._payload_valid(np.zeros(5)))

    def test_replan_is_bounded_and_forbidden_after_handover(self):
        c = self.controller()
        c.replans = 3
        with self.assertRaisesRegex(module.ControllerFailure, 'replan_budget'):
            c.replan_approach(c.initial_q, 0,
                             {'valid': True, 'xy': [.24, -.13], 'timestamp_s': 0})
        c.target_frozen = True
        with self.assertRaisesRegex(module.ControllerFailure, 'outside_visible'):
            c.replan_approach(c.initial_q, 0, None)

    def test_return_shortcut_cannot_cut_through_obstacle(self):
        points=np.array([[0.,0,0,0,0],[0,1.,0,0,0],[1.,1.,0,0,0],[1.,0,0,0,0]])
        valid=lambda q: not (.2<q[0]<.8 and q[1]<.8)
        result=module.shorten_path(points,valid)
        self.assertGreater(len(result),2)
        self.assertTrue(module.validate_joint_path(result,valid,.005)['valid'])
        clear=module.shorten_path(points,lambda q:True)
        np.testing.assert_array_equal(clear,points[[0,-1]])

    def test_separation_cannot_return_below_recorded_high_water(self):
        c=self.controller();q=c.initial_q
        c.separation_pinch=q[:3].copy()
        c.separation_floors={'pad_gripper':-.00105}
        c.separation_vertices={'pad_gripper':np.zeros((8,3))}
        c.separation_high_z={'pad_gripper':np.full(8,.002)}
        c.released_query=Mock()
        c.released_query.distances.return_value={'pad_gripper':-.001}
        c.released_query.pad_vertices.return_value={'pad_gripper':np.tile([0,0,.0005],(8,1))}
        self.assertFalse(c._separation_valid(q[:5]))
        c.released_query.pad_vertices.return_value={'pad_gripper':np.tile([0,0,.002],(8,1))}
        self.assertTrue(c._separation_valid(q[:5]))
        self.assertFalse(c._released_valid(q[:5]))  # No contact exception on return.

    def test_continuous_phase_preserves_setpoint_without_treating_it_as_pose(self):
        c=self.controller();q=c.initial_q.copy();c.target_frozen=True
        offset=np.array([.0001,-.00056,-.00031,0,.00005])
        previous=q.copy();previous[:5]+=offset;c.last_command=previous.copy()
        c.stage='retreat'
        c._set_continuous_motion([q[:5],q[:5]+.01],0)
        # The setpoint may differ from a collision-free achieved pose under load.
        # This predicate permits only the geometric start, not the servo target.
        c._released_valid=lambda pose,jaw=.5: np.allclose(pose,q[:5],rtol=0,atol=1e-12)
        result=c.update(q,np.zeros(6),0)
        self.assertEqual(result['status'],'running')
        np.testing.assert_array_equal(result['command'],previous)
        np.testing.assert_array_equal(result['geometric_reference'],q)
        np.testing.assert_allclose(result['command'][:5]-q[:5],offset,atol=1e-17)
        c._released_valid=lambda pose,jaw=.5:True
        result=c.update(q,np.zeros(6),.02)
        np.testing.assert_array_equal(result['servo_offset'],previous[:5]-q[:5])
        self.assertGreater(np.linalg.norm(result['geometric_reference']-q),0)

    def test_phase_bias_is_recaptured_once_and_retained_through_settle(self):
        c=self.controller();c.target_frozen=True
        q=c.initial_q.copy();q[:5]+=.01
        c.last_command=q.copy();c.last_command[:5]+=.0005
        c.stage='retreat';c._set_continuous_motion([q[:5],c.initial_q[:5]],0)
        c._released_valid=lambda pose,jaw=.5:True
        terminal=c.update(c.initial_q.copy(),np.zeros(6),c.duration-.01)['command']
        terminal=c.update(c.initial_q.copy(),np.zeros(6),c.duration+.01)['command']
        result=c.update(c.initial_q.copy(),np.zeros(6),c.duration+.61)
        self.assertEqual(result['stage'],'settle')
        np.testing.assert_array_equal(result['command'],terminal)
        result=c.update(c.initial_q.copy(),np.zeros(6),c.stage_started+c.duration+.61)
        self.assertTrue(result['done'])
        np.testing.assert_array_equal(result['command'],terminal)
        repeated=c.update(c.initial_q.copy(),np.zeros(6),c.last_elapsed+.02)
        np.testing.assert_array_equal(repeated['command'],terminal)
        expired=c.update(c.initial_q.copy(),np.zeros(6),90.02)
        self.assertEqual(expired['status'],'done')
        np.testing.assert_array_equal(expired['command'],terminal)

    def test_large_bias_or_mapped_limit_violation_is_rejected_without_clipping(self):
        c=self.controller();q=c.initial_q.copy();c.stage='separate'
        c.last_command=q.copy();c.last_command[0]+=.00301
        with self.assertRaisesRegex(module.ControllerFailure,'servo_offset_exceeds'):
            c._set_continuous_motion([q[:5],q[:5]+.1],0)
        c.last_command=q.copy();c.last_command[0]+=.002
        goal=q[:5].copy();goal[0]=2.999
        with self.assertRaisesRegex(module.ControllerFailure,'out_of_bounds'):
            c._set_continuous_motion([q[:5],goal],0)


if __name__ == '__main__':
    unittest.main()
