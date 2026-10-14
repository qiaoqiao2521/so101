"""Geometric and temporal regression cases for post-release handling."""
import unittest
import copy
from pathlib import Path
import tempfile
import mujoco
import numpy as np
from released_object import ReleaseAudit, ReleasedObjectQuery, box_separation, floor_yaw_rotation, rotation_matrix
from grasp_episode import PAD_NAMES


class ReleasedObjectTests(unittest.TestCase):
    def query(self, directory):
        scene=Path(directory)/'scene.xml'
        joints=''.join(f'<joint type="{kind}" axis="{axis}"/>' for kind in ('slide','hinge')
                       for axis in ('1 0 0','0 1 0','0 0 1'))
        scene.write_text(f'<mujoco><worldbody><body name="gripper">{joints}'
            f'<geom name="{PAD_NAMES[0]}" type="box" pos=".016 0 0" size=".002 .002 .002" contype="2" conaffinity="2"/>'
            f'<geom name="{PAD_NAMES[1]}" type="box" pos=".06 0 0" size=".002 .002 .002" contype="2" conaffinity="2"/>'
            '<geom name="robot_link" type="box" pos=".016 0 0" size=".002 .002 .002" contype="2" conaffinity="2"/>'
            '</body></worldbody></mujoco>')
        return ReleasedObjectQuery(scene)

    def test_oriented_pad_and_nonpad_queries_use_the_same_real_pose(self):
        yaw=np.pi/4;rotation=np.array([[np.cos(yaw),-np.sin(yaw),0],
                                     [np.sin(yaw),np.cos(yaw),0],[0,0,1]])
        with tempfile.TemporaryDirectory() as directory:
            query=self.query(directory);query.freeze([0,0,0],rotation)
            distances=query.distances(np.zeros(6))
            np.testing.assert_allclose(query.data.geom_xmat[query.object_id].reshape(3,3),rotation,atol=1e-15)
            self.assertLess(distances[PAD_NAMES[0]],0)
            self.assertLess(distances['robot_link'],0)
            rotation[:]=np.eye(3)
            self.assertFalse(np.array_equal(query.rotation,rotation))
            with self.assertRaises(ValueError):query.freeze([0,0,0])
        with tempfile.TemporaryDirectory() as directory:
            query=self.query(directory);query.freeze([0,0,0])
            self.assertGreater(query.distances(np.zeros(6))[PAD_NAMES[0]],0)

    def test_release_rotation_rejects_scale_reflection_and_nonfinite(self):
        for value in (np.eye(3)*2,np.diag([-1,1,1]),np.full((3,3),np.nan),np.zeros((2,2))):
            with self.subTest(value=value),self.assertRaises(ValueError):rotation_matrix(value)

    def test_worker_rejects_a_model_whose_real_rotation_does_not_match_snapshot(self):
        from separation_worker import SeparationSnapshot,_planning_context
        rotation=np.array([[0,-1,0],[1,0,0],[0,0,1.]])
        with tempfile.TemporaryDirectory() as directory:
            query=self.query(directory);query.freeze([0,0,0],rotation)
            snapshot=SeparationSnapshot(np.zeros(6),np.zeros(6),np.zeros(6),0,10.,[0,0,0],.002,rotation)
            for mismatch in ('quaternion','compiled_shortcut'):
                model=copy.copy(query.model)
                if mismatch=='quaternion':model.geom_quat[query.object_id]=[1,0,0,0]
                else:model.geom_sameframe[query.object_id]=mujoco.mjtSameFrame.mjSAMEFRAME_BODYROT
                with self.subTest(mismatch=mismatch),self.assertRaisesRegex(ValueError,'frozen estimate'):
                    _planning_context(copy.copy(query.model),model,snapshot)

    def test_known_floor_projection_retains_yaw_and_rejects_inversion(self):
        angle=.53;pitch=.001
        yaw=np.array([[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1]])
        tilt=np.array([[np.cos(pitch),0,np.sin(pitch)],[0,1,0],[-np.sin(pitch),0,np.cos(pitch)]])
        np.testing.assert_allclose(floor_yaw_rotation(yaw@tilt),yaw,atol=1e-15)
        with self.assertRaises(ValueError):floor_yaw_rotation(np.diag([1,-1,-1]))

    def test_sat_clearance_and_initial_overlap(self):
        extent=np.array([.004,.006,.008]); other=np.array([.011,.011,.010])
        overlap=box_separation(np.array([.014,0,0]),np.eye(3),extent,np.zeros(3),other)
        self.assertAlmostEqual(overlap,-.001)
        gaps=[box_separation(np.array([.014,0,z]),np.eye(3),extent,np.zeros(3),other)
              for z in np.linspace(0,.030,31)]
        self.assertTrue(np.all(np.diff(gaps)>=-1e-12))
        self.assertGreater(gaps[-1],.001)

    def test_rotated_box_is_not_treated_as_unrotated(self):
        angle=np.pi/4
        R=np.array([[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1]])
        self.assertGreater(box_separation(np.array([.016,0,0]),np.eye(3),np.array([.002,.020,.002]),
                                         np.zeros(3),np.array([.010,.010,.010])),0)
        self.assertLess(box_separation(np.array([.016,0,0]),R,np.array([.002,.020,.002]),
                                      np.zeros(3),np.array([.010,.010,.010])),0)

    def test_query_rejects_reduced_or_invalid_uncertainty_before_reading_scene(self):
        for value in (0,.0019,-1,float('nan'),float('inf'),.006):
            with self.subTest(value=value),self.assertRaises(ValueError):
                ReleasedObjectQuery('not-read.xml',uncertainty_m=value)

    def test_no_release_and_brief_zero_force_are_not_detachment(self):
        a=ReleaseAudit();self.assertFalse(a.report()['passed'])
        a.start([0,0])
        for i in range(99):a.update([0,0],0,i*.002)
        self.assertFalse(a.report()['passed'])
        a.update([0,0],.03,.200)
        self.assertEqual(a.quiet_s,0)

    def test_one_substep_recontact_latches_failure(self):
        a=ReleaseAudit();a.start([0,0])
        for i in range(100):a.update([0,0],0,i*.002)
        self.assertTrue(a.report()['passed'])
        a.update([0,0],.021,.202)
        a.update([0,0],0,.204)
        self.assertFalse(a.report()['passed'])
        self.assertEqual(a.failure_reason,'released_object_recontact')

    def test_displacement_before_detachment_is_not_hidden(self):
        a=ReleaseAudit();a.start([0,0]);a.update([.0021,0],.5,.002)
        a.start([.0021,0])  # Repeated release stages cannot move the anchor.
        self.assertEqual(a.failure_reason,'released_object_displaced')
        np.testing.assert_array_equal(a.anchor,[0,0])

    def test_allowed_initial_contact_then_stable_separation(self):
        a=ReleaseAudit();a.start([0,0])
        a.update([.0003,0],.5,.002)
        for i in range(100):a.update([.0004,0],0,.004+i*.002)
        self.assertTrue(a.report()['passed'])
        self.assertAlmostEqual(a.max_xy_drift_m,.0004)

    def test_nonfinite_force_cannot_count_as_quiet(self):
        a=ReleaseAudit();a.start([0,0]);a.update([0,0],float('nan'),.002)
        self.assertEqual(a.failure_reason,'release_audit_invalid_sample')
        self.assertFalse(a.report()['passed'])


if __name__=='__main__':unittest.main()
