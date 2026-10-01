"""Real-model positive/negative contact-grasp acceptance, without rendering."""
import hashlib
from pathlib import Path
import tempfile
import unittest

import mujoco
import numpy as np

from grasp_episode import (PAD_NAMES, build_contact_scene, grasp_acceptance,
                           load_policy_prefix, run_episode, solve_pinch_ik)
from collision_scene import CollisionChecker

SOURCE = Path(__file__).resolve().parents[2]/'workspaces/so101_ws/src/so101_mujoco/models/so101.xml'


class ContactGraspTests(unittest.TestCase):
    def test_policy_prefix_preserves_cadence_and_duration_limit(self):
        initial = {'observation.state': np.zeros(6),
                   'observation.environment_state': np.zeros(30)}
        values = {key: np.repeat(value[None], 250, axis=0) for key, value in initial.items()}
        values.update(action=np.ones((250, 6), dtype=np.float32),
                      timestamp=1+np.arange(250)*.02,
                      next_timestamp=1+np.arange(1, 251)*.02)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'prefix.npz'
            np.savez(path, **values)
            np.testing.assert_array_equal(load_policy_prefix(path, 250, .02, initial), values['action'])
            with self.assertRaisesRegex(ValueError, 'five seconds'):
                load_policy_prefix(path, 250, .04, initial)
            with self.assertRaisesRegex(ValueError, 'control period'):
                load_policy_prefix(path, 50, .04, initial)
            values['timestamp'][20] += .02
            values['next_timestamp'][20] += .02
            np.savez(path, **values)
            with self.assertRaisesRegex(ValueError, 'control period'):
                load_policy_prefix(path, 50, .02, initial)

    def test_actual_obstacle_grasp_and_empty_close_negative(self):
        original = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as folder:
            # A non-recording 30ms period must not validate unused 200ms noise.
            positive = run_episode(SOURCE, Path(folder)/'positive', control_period_s=.03)
            self.assertEqual(positive['status'], 'passed', positive['metrics'])
            self.assertFalse(positive['direct_approach']['valid'])
            self.assertTrue(positive['planning']['exact_solution'])
            self.assertGreater(positive['metrics']['final_lift_m'], .025)
            self.assertGreaterEqual(positive['metrics']['hold_duration_s'], 1)
            self.assertEqual(positive['metrics']['obstacle_contact_steps'], 0)
            self.assertEqual(positive['metrics']['invalid_arm_samples'], 0)
            self.assertEqual(positive['weld_count'], 0)
            negative = run_episode(SOURCE, Path(folder)/'negative', empty_close=True)
            self.assertEqual(negative['status'], 'failed')
            self.assertFalse(negative['metrics']['grasp_success'])
            self.assertLess(negative['metrics']['final_lift_m'], .001)
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), original)

    def test_contact_masks_preserve_world_and_other_link_collisions(self):
        with tempfile.TemporaryDirectory() as folder:
            model, rig, _ = build_contact_scene(SOURCE, Path(folder))
            target = model.geom('target_collision').id
            def collides(name):
                g = model.geom(name).id
                return bool((model.geom_contype[target] & model.geom_conaffinity[g]) or
                            (model.geom_contype[g] & model.geom_conaffinity[target]))
            for name in (*PAD_NAMES, 'worktable', 'pick_floor', 'approach_obstacle', 'collision_gripper_0'):
                self.assertTrue(collides(name), name)
            for name in ('collision_gripper_1', 'collision_moving_jaw_so101_v1_0'):
                self.assertFalse(collides(name), name)
            self.assertEqual(model.nq, 13)
            self.assertEqual(rig.nq, 6)
            self.assertEqual(model.nmocap, 0)
            self.assertEqual(model.neq, 0)
            self.assertEqual(model.body('grasp_target').mass, .01)
            np.testing.assert_allclose(model.actuator_forcerange[-1], [-.15, .15])

    def test_large_table_clearance_and_ik_execution_state_independent(self):
        with tempfile.TemporaryDirectory() as folder:
            model, rig, _ = build_contact_scene(SOURCE, Path(folder))
            execution = mujoco.MjData(model)
            before = execution.qpos.copy()
            q = solve_pinch_ik(rig, np.array([.24, .14, .06]))
            np.testing.assert_array_equal(execution.qpos, before)
            checker = CollisionChecker(rig, gripper=.5)
            result = checker.evaluate(q)
            self.assertTrue(result['valid'], result)
            self.assertGreater(result['min_distance_m'], .002)
            # A true obstacle collision is still rejected with the local cap.
            middle = solve_pinch_ik(rig, np.array([.265, 0, .06]))
            result = checker.evaluate(middle)
            self.assertFalse(result['valid'], result)

    def test_transient_lift_and_one_sided_contact_are_rejected(self):
        rows = [{'time_s': t, 'stage': 'hold', 'object_z_m': .05,
                 'tip_forces_n': [1, 1], 'floor_contact': False,
                 'obstacle_contact': False, 'arm_valid': True, 'finite_state': True}
                for t in np.arange(0, 1.5, .02)]
        self.assertTrue(grasp_acceptance(rows, .01)['grasp_success'])
        rows[30]['tip_forces_n'] = [0, 1]
        self.assertFalse(grasp_acceptance(rows, .01)['grasp_success'])
        rows[30]['tip_forces_n'] = [1, 1]
        rows[30]['object_z_m'] = .011
        self.assertFalse(grasp_acceptance(rows, .01)['lift_success'])


if __name__ == '__main__':
    unittest.main()
