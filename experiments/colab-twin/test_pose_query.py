"""Independent FK outputs, live callbacks, fallback and original errors."""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import mujoco
import numpy as np

from grasp_episode import PINCH_POINT, forward_pose_query
from route_policy import RoutePolicy, load_route_policy
from visual_grasp_controller import VisualGraspController


CALLBACKS = ('control', 'passive', 'sensor', 'act_dyn', 'act_gain',
             'act_bias', 'contactfilter', 'time')


class PoseQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bodies = ''.join(f'<body name="{name}" pos=".02 0 .03"><joint type="hinge"/>'
                         '<geom type="sphere" size=".01" mass=".1" contype="0" conaffinity="0"/>'
                         for name in ('a', 'b', 'c', 'd', 'e', 'gripper'))
        cls.model = mujoco.MjModel.from_xml_string(
            '<mujoco><worldbody>'+bodies+'</body>'*6+'</worldbody></mujoco>')

    def test_real_controller_pose_and_owned_returns(self):
        controller = VisualGraspController.__new__(VisualGraspController)
        controller.rig = self.model
        controller.query = mujoco.MjData(self.model)
        controller.gripper_id = self.model.body('gripper').id
        controller.route_policy = RoutePolicy(pose_only_fk=True)
        full = mujoco.MjData(self.model)
        for pose in (np.zeros(6), np.arange(6)/10, -np.arange(6)/10):
            full.qpos[:] = pose
            full.qvel[:] = 0
            mujoco.mj_forward(self.model, full)
            origin, rotation, pinch = controller._fk(pose)
            for name in ('xpos', 'xmat', 'geom_xpos', 'geom_xmat', 'qpos', 'qvel'):
                self.assertEqual(getattr(full, name).tobytes(),
                                 getattr(controller.query, name).tobytes(), name)
            self.assertEqual(pinch.tobytes(), (origin+rotation @ PINCH_POINT).tobytes())
            self.assertFalse(np.shares_memory(origin, controller.query.xpos))
            self.assertFalse(np.shares_memory(rotation, controller.query.xmat))

    def test_default_full_path_does_not_inspect_callbacks(self):
        with patch.object(mujoco, 'get_mjcb_control', side_effect=AssertionError('unexpected inspection')), \
                patch.object(mujoco, 'mj_forward') as full:
            model, data = object(), object()
            forward_pose_query(model, data)
            full.assert_called_once_with(model, data)

    def test_each_current_callback_falls_back(self):
        data = mujoco.MjData(self.model)
        for name in CALLBACKS:
            with self.subTest(name=name), \
                    patch.object(mujoco, 'get_mjcb_'+name, return_value=object()), \
                    patch.object(mujoco, 'mj_forward') as full, \
                    patch.object(mujoco, 'mj_kinematics') as pose:
                forward_pose_query(self.model, data, pose_only=True)
                full.assert_called_once_with(self.model, data)
                pose.assert_not_called()

    def test_actual_callback_registered_between_queries_is_honored(self):
        data = mujoco.MjData(self.model)
        forward_pose_query(self.model, data, pose_only=True)
        calls = []
        def passive(model, query):
            calls.append(float(query.qpos[0]))
        previous = mujoco.get_mjcb_passive()
        try:
            mujoco.set_mjcb_passive(passive)
            forward_pose_query(self.model, data, pose_only=True)
            self.assertEqual(len(calls), 1)
            self.assertIs(mujoco.get_mjcb_passive(), passive)
        finally:
            mujoco.set_mjcb_passive(previous)

    def test_sensor_plugin_mocap_and_unknown_rigs_fall_back(self):
        for field in ('nsensor', 'nplugin', 'nmocap', None):
            values = dict(nsensor=0, nplugin=0, nmocap=0) if field else {}
            if field:
                values[field] = 1
            model, data = SimpleNamespace(**values), object()
            with self.subTest(field=field), patch.object(mujoco, 'mj_forward') as full, \
                    patch.object(mujoco, 'mj_kinematics') as pose:
                forward_pose_query(model, data, pose_only=True)
                full.assert_called_once_with(model, data)
                pose.assert_not_called()

    def test_selected_errors_propagate_unchanged(self):
        for mode, name in ((False, 'mj_forward'), (True, 'mj_kinematics')):
            for failure in (RuntimeError('original FK failure'), KeyboardInterrupt()):
                with self.subTest(mode=mode, failure=type(failure).__name__), \
                        patch.object(mujoco, name, side_effect=failure):
                    with self.assertRaises(type(failure)) as raised:
                        forward_pose_query(self.model, mujoco.MjData(self.model), pose_only=mode)
                    self.assertIs(raised.exception, failure)

    def test_policy_is_single_delta_and_original_remains_default(self):
        parent, _ = load_route_policy()
        child, _ = load_route_policy(Path(__file__).parent/'route_strategies/pose_only_fk.py')
        self.assertEqual([k for k, value in parent.preferences().items()
                          if child.preferences()[k] != value], ['pose_only_fk'])
        self.assertFalse(RoutePolicy().pose_only_fk)
        with self.assertRaises(ValueError):
            RoutePolicy(pose_only_fk=1)


if __name__ == '__main__':
    unittest.main()
