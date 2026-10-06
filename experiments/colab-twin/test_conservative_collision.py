"""Finite geometry and fail-closed integration regressions, no dynamics."""
import unittest
from unittest.mock import patch

import mujoco
import numpy as np

from collision_scene import CollisionChecker
from conservative_collision import ConservativeCollisionChecker
from configuration_sweep import validate_configuration_path


def rig_xml(obstacle='box'):
    # Only the last hinge turns the narrow jaw bar. The obstacle intersects
    # the bar around 0.25 rad but remains clear of both closure endpoints.
    body = ('<geom name="jaw" type="box" pos=".04 0 0" size=".02 .003 .003" '
            'group="3" contype="1" conaffinity="1"/>')
    for i in reversed(range(6)):
        body = (f'<body name="link{i}"><joint name="joint{i}" type="hinge" '
                f'axis="0 0 1" limited="true" range="-1 1"/>'
                f'<inertial pos="0 0 0" mass=".1" diaginertia=".001 .001 .001"/>{body}</body>')
    return (f'<mujoco><compiler angle="radian"/><worldbody>{body}'
            f'<geom name="obstacle" type="{obstacle}" pos=".0484456 .0123702 0" '
            'size=".002 .002 .005" group="3" contype="1" conaffinity="1"/>'
            '</worldbody></mujoco>')


class ConservativeCollisionTests(unittest.TestCase):
    def checker(self):
        model = mujoco.MjModel.from_xml_string(rig_xml())
        checker = ConservativeCollisionChecker(model, gripper=.5, margin_m=.001)
        self.addCleanup(checker.native.close)
        return model, checker

    def test_real_rotating_jaw_endpoints_clear_middle_rejected(self):
        model, checker = self.checker()
        opened, closed = np.r_[np.zeros(5), .5], np.r_[np.zeros(5), .015]
        self.assertTrue(checker.evaluate(opened, require_fixed_gripper=False)['valid'])
        self.assertTrue(checker.evaluate(closed, require_fixed_gripper=False)['valid'])
        self.assertFalse(checker.evaluate(np.r_[np.zeros(5), .25], require_fixed_gripper=False)['valid'])
        result = validate_configuration_path(opened, closed,
                    lambda q: checker.evaluate(q, require_fixed_gripper=False)['valid'])
        self.assertFalse(result['valid'])

    def test_pair_policy_and_five_axis_bounds_match_original(self):
        model, checker = self.checker()
        original = CollisionChecker(model, gripper=.5, margin_m=.001)
        self.assertEqual(checker.pairs, original.pairs)
        self.assertEqual(checker.excluded_pairs, original.excluded_pairs)
        np.testing.assert_array_equal(checker.bounds, original.bounds)
        self.assertEqual(checker.margin_m, .001)
        self.assertEqual(checker.bounds.shape, (5, 2))

    def test_limits_nonfinite_and_actual_jaw_preserved(self):
        model, checker = self.checker()
        self.assertEqual(checker.evaluate(np.r_[np.zeros(5), .25])['reason'], 'gripper_not_fixed')
        self.assertFalse(checker.evaluate(np.r_[np.zeros(5), .25], require_fixed_gripper=False)['valid'])
        for q, reason in [(np.r_[np.zeros(5), 1.01], 'joint_limit'),
                          (np.r_[np.zeros(5), np.nan], 'configuration_shape_or_nonfinite')]:
            self.assertEqual(checker.evaluate(q, require_fixed_gripper=False)['reason'], reason)

    def test_library_failure_cannot_fall_back_to_approximate_distance(self):
        model, checker = self.checker()
        with patch.object(checker.native, 'evaluate', side_effect=RuntimeError('invalid environment')), \
                patch.object(mujoco, 'mj_geomDistance', side_effect=AssertionError('forbidden CCD')):
            result = checker.evaluate(np.zeros(5))
        self.assertFalse(result['valid'])
        self.assertEqual(result['reason'], 'geometry_certificate_unavailable')

    def test_static_query_cannot_mutate_execution_data(self):
        model, checker = self.checker()
        execution = mujoco.MjData(model)
        execution.qpos[:] = np.arange(6)*.01
        before = execution.qpos.copy()
        with patch.object(mujoco, 'mj_step', side_effect=AssertionError('forbidden integration')), \
                patch.object(mujoco, 'mj_forward', side_effect=AssertionError('FK only')), \
                patch.object(mujoco, 'mj_geomDistance', side_effect=AssertionError('forbidden CCD')):
            result = checker.evaluate(np.zeros(5))
        self.assertTrue(result['valid'])
        self.assertEqual(result['distance_kind'], 'certified_lower_bound')
        np.testing.assert_array_equal(execution.qpos, before)

    def test_unsupported_unbounded_plane_refused(self):
        model = mujoco.MjModel.from_xml_string(rig_xml('plane'))
        with self.assertRaisesRegex(ValueError, 'finite mesh/box'):
            ConservativeCollisionChecker(model)


if __name__ == '__main__':
    unittest.main()
