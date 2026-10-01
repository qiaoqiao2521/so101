"""Dynamic object and jaw checks for the single-arm modeling fixture."""
from pathlib import Path
import tempfile
import unittest
import hashlib
import mujoco
import numpy as np
from grasp_workcell import build_workcell


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
