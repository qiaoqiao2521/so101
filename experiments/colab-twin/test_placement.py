"""Actual free-body transfer/release and meaningful failure boundaries."""
from pathlib import Path
import tempfile
import unittest
import json

from grasp_episode import run_episode
from placement import placement_acceptance

SOURCE = Path(__file__).resolve().parents[2]/'workspaces/so101_ws/src/so101_mujoco/models/so101.xml'


class PlacementTests(unittest.TestCase):
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
