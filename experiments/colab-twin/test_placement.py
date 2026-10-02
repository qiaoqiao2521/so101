"""Actual free-body transfer/release and meaningful failure boundaries."""
from pathlib import Path
import tempfile
import unittest
import json

import mujoco
import numpy as np

from collision_scene import CollisionChecker
from grasp_episode import build_contact_scene, run_episode, solve_pinch_ik
from learning_env import PhysicalTaskMonitor, diagnostics
from placement import carried_configuration_checker, placement_acceptance

SOURCE = Path(__file__).resolve().parents[2]/'workspaces/so101_ws/src/so101_mujoco/models/so101.xml'


class PlacementTests(unittest.TestCase):
    def query_fixture(self, folder):
        model, rig, _ = build_contact_scene(SOURCE, Path(folder))
        execution = mujoco.MjData(model)
        q = solve_pinch_ik(rig, np.array([.24, -.13, .06]))
        # Reset-only geometry fixture; the query itself may never write this state.
        execution.qpos[:6] = np.r_[q, .115]
        execution.qpos[6:9] = [.24, -.13, .05]
        execution.ctrl[:] = np.r_[q, .015]
        execution.qvel[:] = np.linspace(-.01, .01, model.nv)
        execution.qacc_warmstart[:] = np.linspace(.01, .02, model.nv)
        execution.time = 1.23
        mujoco.mj_forward(model, execution)
        return model, rig, execution, CollisionChecker(rig, gripper=.115, margin_m=.001)

    def test_carried_query_rejects_payload_floor_collision_without_mutating_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            model, rig, execution, checker = self.query_fixture(folder)
            before = {key: getattr(execution, key).copy() for key in
                      ('qpos', 'qvel', 'ctrl', 'qacc_warmstart', 'xpos', 'xmat')}
            time_before = execution.time
            valid, audit = carried_configuration_checker(model, execution, checker)
            self.assertTrue(valid(execution.qpos[:5]), audit)
            self.assertGreater(audit['payload_min_distance_m'], .0002)
            down = solve_pinch_ik(rig, np.array([.24, -.13, .019]), execution.qpos[:5])
            self.assertTrue(checker.evaluate(np.r_[down, execution.qpos[5]], require_fixed_gripper=False)['valid'])
            self.assertFalse(valid(down))
            self.assertLess(audit['last_rejection']['payload_distance_m'], .0002)
            self.assertIn(audit['last_rejection']['pair'], ('pick_floor', 'worktable'))
            for key, value in before.items():
                np.testing.assert_array_equal(getattr(execution, key), value, err_msg=key)
            self.assertEqual(execution.time, time_before)

    def test_carried_query_rejects_invalid_reference_and_configurations(self):
        with tempfile.TemporaryDirectory() as folder:
            model, _, execution, checker = self.query_fixture(folder)
            valid, audit = carried_configuration_checker(model, execution, checker)
            for q in (np.zeros(4), np.zeros(7), np.full(5, np.nan), np.full(6, np.inf), 'invalid'):
                self.assertFalse(valid(q), str(q))
                self.assertEqual(audit['last_rejection']['reason'], 'configuration_shape_or_nonfinite')
            self.assertTrue(valid(execution.qpos[:6]), audit)
            execution.qpos[0] = np.nan
            with self.assertRaisesRegex(ValueError, 'finite'):
                carried_configuration_checker(model, execution, checker)
            execution.qpos[0] = 0
            execution.qvel[7] = np.inf
            with self.assertRaisesRegex(ValueError, 'finite'):
                carried_configuration_checker(model, execution, checker)

    def test_unheld_geometry_query_does_not_admit_a_physical_grasp(self):
        with tempfile.TemporaryDirectory() as folder:
            model, _, execution, checker = self.query_fixture(folder)
            execution.qpos[6:9] = [.27, -.13, .05]
            execution.qvel[:] = 0
            mujoco.mj_forward(model, execution)
            valid, audit = carried_configuration_checker(model, execution, checker)
            self.assertTrue(valid(execution.qpos[:5]), audit)
            row = diagnostics(model, execution, checker)
            self.assertEqual(row['tip_forces_n'], [0, 0])
            monitor = PhysicalTaskMonitor(.01)
            monitor.update(row)
            monitor.update(dict(row, time_s=row['time_s']+1.2))
            self.assertFalse(monitor.report()['grasp_success'])
            self.assertFalse(monitor.report()['passed'])

    def test_real_transport_release_retreat_and_settle(self):
        with tempfile.TemporaryDirectory() as folder:
            report = run_episode(SOURCE, Path(folder)/'placed', place=True)
            self.assertEqual(report['status'], 'passed', report['metrics'])
            self.assertTrue(report['metrics']['place_success'])
            self.assertTrue(report['metrics']['transport_held'])
            self.assertEqual(report['metrics']['released_tip_forces_n'], [0, 0])
            self.assertGreaterEqual(report['metrics']['settled_duration_s'], 1)
            self.assertLess(report['metrics']['final_object_speed_m_s'], .002)
            self.assertEqual(report['metrics']['obstacle_contact_steps'], 0)
            self.assertEqual(report['metrics']['invalid_arm_samples'], 0)
            self.assertEqual(report['weld_count'], 0)
            self.assertEqual(report['assumptions']['noslip_iterations'], 10)
            self.assertGreater(report['transport_planning']['payload_min_distance_m'], .0002)

    def test_default_soft_contact_creep_stops_with_recoverable_trajectory(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'slip'
            with self.assertRaisesRegex(RuntimeError, 'Payload lost'):
                run_episode(SOURCE, output, place=True, noslip_iterations=0)
            rows = json.loads((output/'trajectory.json').read_text())
            self.assertEqual(rows[-1]['stage'], 'transport')
            self.assertFalse(any(r['stage']=='release' for r in rows))
            self.assertFalse(placement_acceptance(rows)['place_success'])

    def test_release_requires_support_whole_footprint_and_no_tip_force(self):
        base = {'time_s': 0, 'stage': 'settle', 'in_place_tray': True,
                'place_floor_contact': True, 'tip_forces_n': [0, 0],
                'object_speed_m_s': 0, 'object_z_m': .01,
                'object_xyz_m': [.24, .14, .01], 'floor_contact': False}
        carry = dict(base, stage='transport', place_floor_contact=False, tip_forces_n=[1, 1])
        rows = [carry]+[dict(base, time_s=i*.02) for i in range(76)]
        self.assertTrue(placement_acceptance(rows)['place_success'])
        for key, value in [('in_place_tray', False), ('place_floor_contact', False),
                           ('tip_forces_n', [1, 0]), ('object_speed_m_s', .01)]:
            bad = [dict(r) for r in rows]
            bad[-1][key] = value
            self.assertFalse(placement_acceptance(bad)['place_success'], key)


if __name__ == '__main__':
    unittest.main()
