"""Controller regressions for interior q6 rejection; fake FK, no physics."""

import unittest

import numpy as np

import test_visual_grasp_controller as fixtures
import visual_grasp_controller as module


class VisualGraspSweepTests(unittest.TestCase):
    controller = fixtures.VisualControllerTests.controller

    def install_predicate(self, controller, predicate):
        def evaluate(q, *, require_fixed_gripper=True):
            self.assertFalse(require_fixed_gripper)
            q = np.asarray(q)
            self.assertEqual(q.shape, (6,))
            return {'valid': bool(predicate(q))}

        controller.checker.evaluate.side_effect = evaluate

    def test_planned_closure_rejects_interior_jaw_with_safe_endpoints(self):
        controller = self.controller()
        down = controller.down.copy()

        def valid(q):
            return not (np.array_equal(q[:5], down) and .24 < q[5] < .26)

        self.assertTrue(valid(np.r_[down, .5]))
        self.assertTrue(valid(np.r_[down, .015]))
        self.install_predicate(controller, valid)
        with self.assertRaisesRegex(module.ControllerFailure, 'grasp_closure_sweep_invalid'):
            controller._plan_approach(controller.initial_q[:5])
        report = controller.sweep_reports[-1]
        self.assertEqual(report['stage'], 'planned_closure')
        self.assertTrue(.24 < report['invalid_state'][5] < .26)

    def mixed_collision(self, controller):
        origin = float(controller.down[0])
        return lambda q: not (origin + .0008 < q[0] < origin + .0012 and .24 < q[5] < .27)

    def test_measured_closure_precheck_stops_before_first_close_command(self):
        controller = self.controller()
        controller.target_frozen = True
        q = np.r_[controller.down, .5]
        q[0] += .002
        valid = self.mixed_collision(controller)
        self.assertTrue(valid(q))
        self.assertTrue(valid(np.r_[controller.down, .015]))
        # The nominal fixed-arm closure is safe, unlike this measured chord.
        self.assertTrue(all(valid(np.r_[controller.down, jaw]) for jaw in np.linspace(.015, .5, 244)))
        self.install_predicate(controller, valid)
        controller.stage = 'descend'
        controller._set_motion([controller.down, controller.down], .5, 0.)
        result = controller.update(q, np.zeros(6), controller.duration + .61)
        self.assertEqual(result['failure_reason'], 'measured_closure_sweep_invalid')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['stage'], 'descend')
        np.testing.assert_array_equal(result['command'], q)
        self.assertEqual(controller.jaw, .5)
        self.assertEqual(controller.sweep_reports[-1]['stage'], 'measured_closure')

    def test_online_q6_chord_catches_combination_fixed_jaw_check_misses(self):
        controller = self.controller()
        controller.target_frozen = True
        q = np.r_[controller.down, .5]
        q[0] += .002
        valid = self.mixed_collision(controller)
        self.assertTrue(valid(q))
        self.assertTrue(valid(np.r_[controller.down, .015]))
        # Both fixed-q5 jaw sweeps and the old target-jaw arm chord are safe.
        for alpha in np.linspace(0., 1., 244):
            jaw = .5 + (.015 - .5) * alpha
            self.assertTrue(valid(np.r_[q[:5], jaw]))
            self.assertTrue(valid(np.r_[controller.down, jaw]))
            self.assertTrue(valid(np.r_[q[:5] + (controller.down - q[:5]) * alpha, .015]))
        self.install_predicate(controller, valid)
        controller._set_dwell('close', controller.down, .015, 0., 6.)
        result = controller.update(q, np.zeros(6), .1)
        self.assertEqual(result['failure_reason'], 'current_pose_command_chord_invalid')
        self.assertEqual(result['status'], 'failed')
        np.testing.assert_array_equal(result['command'], q)
        self.assertTrue(.24 < controller.last_sweep_report['invalid_state'][5] < .27)


if __name__ == '__main__':
    unittest.main()
