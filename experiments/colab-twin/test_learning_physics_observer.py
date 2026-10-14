"""The opt-in 2ms audit must not change default workcell dynamics."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

import mujoco
import numpy as np

from grasp_episode import OBSTACLE,solve_pinch_ik
from learning_env import StateWorkcell


class PhysicsObserverTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        source=Path(__file__).resolve().parents[2]/"workspaces/so101_ws/src/so101_mujoco/models/so101.xml"
        metadata={"model_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
                  "scene_configuration":{"jaw_force_cap_nm":.15,"noslip_iterations":10,
                      "baseline_object_z_m":.01,"obstacle":OBSTACLE},
                  "control_period_s":.02,"physics_dt_s":.002}
        self.env=StateWorkcell(source,Path(self.folder.name)/"scene",metadata)
        self.command=np.r_[solve_pinch_ik(self.env.checker.model,np.array([.24,.14,.06])),.5]
        self.env.data.qpos[:6]=self.command;self.env.data.ctrl[:]=self.command
        mujoco.mj_forward(self.env.model,self.env.data)

    def tearDown(self):
        self.folder.cleanup()

    def test_every_physics_tick_and_same_result_as_default(self):
        original=copy.copy(self.env.data)
        self.env.step(self.command)
        expected=copy.copy(self.env.data)
        self.env.data=original
        samples=[]
        self.env.step(self.command,physics_observer=lambda model,data:samples.append(float(data.time)))
        np.testing.assert_allclose(samples,np.arange(1,11)*.002,atol=1e-12,rtol=0)
        np.testing.assert_array_equal(self.env.data.qpos,expected.qpos)
        np.testing.assert_array_equal(self.env.data.qvel,expected.qvel)
        np.testing.assert_array_equal(self.env.data.qacc_warmstart,expected.qacc_warmstart)

    def test_observer_failure_stops_before_next_integration(self):
        def reject(model,data):
            raise RuntimeError("release rejection")
        with self.assertRaisesRegex(RuntimeError,"release rejection"):
            self.env.step(self.command,physics_observer=reject)
        self.assertAlmostEqual(self.env.data.time,.002)


if __name__=="__main__":unittest.main()
