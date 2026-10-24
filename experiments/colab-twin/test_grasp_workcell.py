"""Dynamic object and jaw checks for the single-arm modeling fixture."""
from pathlib import Path
import tempfile
import unittest
import hashlib
from unittest.mock import patch
import mujoco
import numpy as np
from grasp_workcell import build_workcell, PICK_CENTER
from grasp_episode import build_contact_scene, OBSTACLE


class PickTrayPlacementTests(unittest.TestCase):
    """Only compile geometry; these layout checks never advance physics."""
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.source = Path(__file__).resolve().parents[2]/'workspaces/so101_ws/src/so101_mujoco/models/so101.xml'
        with patch.object(mujoco, 'mj_step', side_effect=AssertionError('physics forbidden')):
            cls.default, cls.default_rig, _ = build_contact_scene(
                cls.source, Path(cls.directory.name)/'default')
            cls.shifted, cls.shifted_rig, _ = build_contact_scene(
                cls.source, Path(cls.directory.name)/'shifted', pick_xy=(.26, -.12))

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_default_pick_geometry_and_target_remain_at_original_positions(self):
        x, y = PICK_CENTER
        expected = {'pick_floor': (x, y, .001), 'pick_plaque': (x, y-.075, .001)}
        for side in (-1, 1):
            expected[f'pick_wall_x_{side}'] = (x+side*.059, y, .009)
            expected[f'pick_wall_y_{side}'] = (x, y+side*.059, .009)
        for name, position in expected.items():
            np.testing.assert_allclose(self.default.geom(name).pos, position, rtol=0, atol=1e-12)
        np.testing.assert_allclose(self.default.body('grasp_target').pos, (*PICK_CENTER, .012), rtol=0, atol=1e-12)
        np.testing.assert_allclose(self.default.geom('approach_obstacle').pos, OBSTACLE['pos'], rtol=0, atol=1e-12)

    def test_explicit_pick_center_moves_all_tray_geometry_in_both_models_only(self):
        delta = np.array([.02, .01, 0.])
        for original, shifted in ((self.default, self.shifted), (self.default_rig, self.shifted_rig)):
            pick_count = 0
            for index in range(original.ngeom):
                name = original.geom(index).name
                before, after = original.geom(index), shifted.geom(index)
                self.assertEqual(after.name, before.name)
                is_pick = name.startswith('pick_')
                pick_count += is_pick
                np.testing.assert_allclose(after.pos, before.pos+(delta if is_pick else 0.), rtol=0, atol=1e-12)
                for field in ('size', 'quat', 'contype', 'conaffinity', 'friction'):
                    np.testing.assert_array_equal(getattr(after, field), getattr(before, field))
            self.assertEqual(pick_count, 6)
            np.testing.assert_array_equal(shifted.body_pos, original.body_pos)
            np.testing.assert_array_equal(shifted.jnt_range, original.jnt_range)
            np.testing.assert_array_equal(shifted.qpos0, original.qpos0)

    def test_invalid_pick_centers_are_rejected(self):
        for center in ((True, -.13), (.24, False), (float('nan'), -.13),
                       (.24, float('inf')), ('0.24', -.13), (.24,), (.24, -.13, 0.), (2., -.13)):
            with self.subTest(center=center), self.assertRaises(ValueError):
                build_workcell(self.source, Path(self.directory.name)/'invalid', pick_xy=center)


class GraspWorkcellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory()
        cls.source=Path(__file__).resolve().parents[2]/'workspaces/so101_ws/src/so101_mujoco/models/so101.xml'
        cls.original=hashlib.sha256(cls.source.read_bytes()).hexdigest()
        cls.model,_=build_workcell(cls.source,Path(cls.directory.name))

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def data(self):
        data=mujoco.MjData(self.model)
        data.qpos[5]=.8
        data.ctrl[:]=data.qpos[:6]
        mujoco.mj_forward(self.model,data)
        return data

    def test_free_target_falls_and_stops_on_tray_without_attachment(self):
        data=self.data()
        joint=self.model.joint('target_free')
        address=int(joint.qposadr[0])
        data.qpos[address+2]+=.025
        initial=float(data.qpos[address+2])
        for _ in range(1000):mujoco.mj_step(self.model,data)
        mujoco.mj_forward(self.model,data)
        self.assertLess(float(data.qpos[address+2]),initial-.02)
        self.assertAlmostEqual(float(data.qpos[address+2]),.01,delta=.001)
        self.assertEqual(self.model.neq,0)
        self.assertEqual(self.model.nu,6)
        self.assertEqual(self.model.nq,13)
        self.assertTrue(np.all(np.isfinite(data.qpos)))
        target=self.model.geom('target_collision').id
        floor=self.model.geom('pick_floor').id
        self.assertTrue(any({int(c.geom1),int(c.geom2)}=={target,floor} for c in data.contact))
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(),self.original)

    def test_jaw_articulates_physically_with_target_remaining_supported(self):
        data=self.data()
        for value in (.25,.8):
            data.ctrl[5]=value
            for _ in range(500):mujoco.mj_step(self.model,data)
            self.assertAlmostEqual(float(data.qpos[5]),value,delta=.02)
        mujoco.mj_forward(self.model,data)
        self.assertAlmostEqual(float(data.body('grasp_target').xpos[2]),.01,delta=.001)


if __name__=='__main__':unittest.main()
