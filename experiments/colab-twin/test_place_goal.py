"""Moved same-size trays score against the scene, without changing old data."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from grasp_episode import build_contact_scene
from grasp_workcell import PLACE_CENTER
from learning_env import PhysicalTaskMonitor, diagnostics, observe
from placement import object_inside_tray, placement_acceptance


SOURCE = Path(__file__).resolve().parents[2]/'workspaces/so101_ws/src/so101_mujoco/models/so101.xml'


class PlaceGoalGeometryTests(unittest.TestCase):
    def test_default_center_is_backward_compatible(self):
        center = np.r_[PLACE_CENTER, .01]
        self.assertTrue(object_inside_tray(np.eye(3), center))
        self.assertEqual(object_inside_tray(np.eye(3), center),
                         object_inside_tray(np.eye(3), center, PLACE_CENTER))

    def test_new_center_passes_and_old_center_is_rejected(self):
        new_center = np.asarray(PLACE_CENTER) + [.12, -.03]
        self.assertTrue(object_inside_tray(np.eye(3), np.r_[new_center, .01], new_center))
        self.assertFalse(object_inside_tray(np.eye(3), np.r_[PLACE_CENTER, .01], new_center))
        self.assertFalse(object_inside_tray(np.eye(3), np.r_[new_center, .01]))

    def test_original_58mm_inner_edge_is_unchanged(self):
        for tray in (np.asarray(PLACE_CENTER), np.asarray(PLACE_CENTER)+[.12, -.03]):
            self.assertTrue(object_inside_tray(np.eye(3), np.r_[tray+[.04899, 0], .01], tray))
            self.assertFalse(object_inside_tray(np.eye(3), np.r_[tray+[.04901, 0], .01], tray))

    def test_rotated_whole_footprint_is_required_at_both_centers(self):
        c, s = np.cos(np.pi/4), np.sin(np.pi/4)
        rotation = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        for tray in (np.asarray(PLACE_CENTER), np.asarray(PLACE_CENTER)+[.12, -.03]):
            center = np.r_[tray+[.047, 0], .01]
            self.assertTrue(object_inside_tray(np.eye(3), center, tray))
            self.assertFalse(object_inside_tray(rotation, center, tray))


class PlaceGoalDiagnosticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        _, _, path = build_contact_scene(SOURCE, Path(cls.folder.name))
        tree = ET.parse(path)
        for geom in tree.getroot().iter('geom'):
            if geom.get('name', '').startswith('place_'):
                position = np.fromstring(geom.get('pos'), sep=' ')
                position[:2] += [.12, -.03]
                geom.set('pos', ' '.join(map(str, position)))
        moved_path = Path(cls.folder.name)/'moved-place.xml'
        tree.write(moved_path)
        cls.model = mujoco.MjModel.from_xml_path(str(moved_path))

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def setUp(self):
        self.new_center = np.asarray(PLACE_CENTER)+[.12, -.03]
        self.data = mujoco.MjData(self.model)
        self.data.qpos[6:9] = [*self.new_center, .0099]
        self.data.qpos[9:13] = [1, 0, 0, 0]
        mujoco.mj_forward(self.model, self.data)
        self.checker = Mock()
        self.checker.evaluate.return_value = {'valid': True}

    def test_diagnostics_accepts_real_new_tray_and_floor_contact(self):
        row = diagnostics(self.model, self.data, self.checker)
        self.assertTrue(row['in_place_tray'])
        self.assertTrue(row['place_floor_contact'])
        self.assertEqual(row['tip_forces_n'], [0, 0])
        self.assertEqual(row['object_speed_m_s'], 0)

    def test_diagnostics_rejects_object_at_old_goal(self):
        self.data.qpos[6:8] = PLACE_CENTER
        mujoco.mj_forward(self.model, self.data)
        row = diagnostics(self.model, self.data, self.checker)
        self.assertFalse(row['in_place_tray'])
        self.assertFalse(row['place_floor_contact'])

    def test_historical_observation_goal_semantics_are_preserved(self):
        obs = observe(self.model, self.data)
        self.assertEqual(obs['observation.environment_state'].shape, (30,))
        np.testing.assert_array_equal(obs['observation.environment_state'][19:22], [*PLACE_CENTER, .01])


class RaisedPlaceScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.models = {}
        for height in (0., .02):
            model, _, _ = build_contact_scene(
                SOURCE, Path(cls.folder.name)/str(height), place_height_m=height)
            cls.models[height] = model

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def row_at(self, height, xyz):
        model = self.models[height]
        data = mujoco.MjData(model)
        data.qpos[6:9] = xyz
        data.qpos[9:13] = [1, 0, 0, 0]
        mujoco.mj_forward(model, data)
        checker = Mock()
        checker.evaluate.return_value = {'valid': True}
        return model, data, checker, diagnostics(model, data, checker)

    def lifted_monitor(self, reference):
        # Establish the original one-second, 25mm, bilateral-force condition.
        # The subsequent rest samples come from the real MuJoCo tray contacts.
        monitor = PhysicalTaskMonitor(.01)
        carry = dict(reference, stage='transport', object_z_m=.05,
                     object_xyz_m=[.24, -.13, .05], tip_forces_n=[.5, .5],
                     place_floor_contact=False, floor_contact=False,
                     in_place_tray=False, obstacle_contact=False, arm_valid=True)
        for tick in range(52):
            monitor.update(dict(carry, time_s=tick*.02))
        self.assertTrue(monitor.report()['grasp_success'])
        return monitor, carry

    def test_real_default_and_raised_floor_contacts_settle_for_one_second(self):
        for height in self.models:
            with self.subTest(height=height):
                model, data, checker, row = self.row_at(height, [*PLACE_CENTER, .0099+height])
                self.assertAlmostEqual(row['place_support_z_m'], .002+height)
                self.assertTrue(row['place_floor_contact'])
                monitor, carry = self.lifted_monitor(row)
                data.time = 2.
                rows = [carry]
                for tick in range(650):
                    mujoco.mj_step(model, data)
                    if tick % 10 == 9:
                        mujoco.mj_forward(model, data)
                        rest = diagnostics(model, data, checker)
                        monitor.update(rest)
                        rows.append(dict(rest, stage='settle'))
                self.assertTrue(monitor.report()['passed'], monitor.report())
                self.assertTrue(placement_acceptance(rows)['place_success'])
                self.assertTrue(rows[-1]['place_floor_contact'])
                self.assertLess(abs(rows[-1]['object_z_m']-(.010+height)), .002)

    def test_old_table_air_and_wrong_tray_cannot_score_raised_goal(self):
        height = .02
        for xyz in ([*PLACE_CENTER, .0099], [*PLACE_CENTER, .014+height],
                    [.40, .14, .010+height]):
            with self.subTest(xyz=xyz):
                _, _, _, row = self.row_at(height, xyz)
                self.assertFalse(row['place_floor_contact'])
                monitor, carry = self.lifted_monitor(row)
                settled = [dict(row, stage='settle', time_s=2+tick*.02) for tick in range(65)]
                for rest in settled:
                    monitor.update(rest)
                self.assertFalse(monitor.report()['passed'])
                self.assertFalse(placement_acceptance([carry, *settled])['place_success'])

    def test_rest_tolerance_stays_two_mm_relative_to_the_support_plane(self):
        for height in self.models:
            _, _, _, row = self.row_at(height, [*PLACE_CENTER, .0099+height])
            for error, accepted in ((.00199, True), (.00201, False)):
                with self.subTest(height=height, error=error):
                    monitor, carry = self.lifted_monitor(row)
                    rows = [dict(row, stage='settle', time_s=2+tick*.02,
                                 object_z_m=.010+height+error) for tick in range(65)]
                    for rest in rows:
                        monitor.update(rest)
                    self.assertEqual(monitor.report()['passed'], accepted)
                    self.assertEqual(placement_acceptance([carry, *rows])['place_success'], accepted)

    def test_supported_release_height_and_speed_limits_translate_without_relaxation(self):
        for height in self.models:
            _, _, _, row = self.row_at(height, [*PLACE_CENTER, .0099+height])
            for z, speed, lost in ((.02499+height, .049, False),
                                   (.02501+height, .049, True),
                                   (.02499+height, .051, True)):
                with self.subTest(height=height, z=z, speed=speed):
                    monitor, _ = self.lifted_monitor(row)
                    for tick in range(10):
                        monitor.update(dict(row, time_s=2+tick*.02,
                                            object_z_m=z, object_speed_m_s=speed,
                                            place_floor_contact=False))
                    self.assertEqual(monitor.report()['failure_reason'], 'payload_lost' if lost else None)
                    self.assertFalse(monitor.report()['place_success'])

    def test_high_supported_rest_does_not_replace_a_grasp(self):
        _, _, _, row = self.row_at(.02, [*PLACE_CENTER, .0299])
        monitor = PhysicalTaskMonitor(.01)
        for tick in range(65):
            monitor.update(dict(row, time_s=tick*.02))
        self.assertFalse(monitor.report()['grasp_success'])
        self.assertFalse(monitor.report()['passed'])

    def test_zero_height_rows_without_the_new_field_keep_the_old_result(self):
        _, _, _, row = self.row_at(0., [*PLACE_CENTER, .0099])
        legacy = dict(row)
        del legacy['place_support_z_m']
        reports = []
        for reference in (row, legacy):
            monitor, carry = self.lifted_monitor(reference)
            rows = [dict(reference, stage='settle', time_s=2+tick*.02) for tick in range(65)]
            for rest in rows:
                monitor.update(rest)
            reports.append((monitor.report(), placement_acceptance([carry, *rows])))
        self.assertEqual(reports[0], reports[1])

    def test_raised_goal_does_not_change_historical_state30(self):
        model, data, _, _ = self.row_at(.02, [*PLACE_CENTER, .0299])
        obs = observe(model, data)
        self.assertEqual(obs['observation.environment_state'].shape, (30,))
        np.testing.assert_array_equal(obs['observation.environment_state'][19:22], [*PLACE_CENTER, .01])


if __name__ == '__main__':
    unittest.main()
