"""Geometric and temporal regression cases for post-release handling."""
import unittest
import numpy as np
from released_object import ReleaseAudit, ReleasedObjectQuery, box_separation


class ReleasedObjectTests(unittest.TestCase):
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
