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
from learning_env import diagnostics, observe
from placement import object_inside_tray


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


if __name__ == '__main__':
    unittest.main()
