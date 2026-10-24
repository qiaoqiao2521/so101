"""Optional construction evidence preserves original native query behavior."""
import itertools
import unittest
import numpy as np
from support_native import NativeSupport

class NativeGeometryEvidenceTests(unittest.TestCase):
    def points(self):
        return [np.asarray(list(itertools.product((-.01,.01),repeat=3)),dtype=np.float64)for _ in range(2)]

    def test_default_keeps_no_evidence(self):
        native=NativeSupport(self.points(),['box','box'])
        try:
            self.assertIsNone(native._construction_geometry)
            self.assertIsNone(native._construction_handle)
        finally:native.close()

    def test_evidence_matches_exact_inputs_and_owns_bytes(self):
        points=self.points();native=NativeSupport(points,['box','box'],capture_geometry=True)
        try:
            expected=(np.asarray([0,8,16],dtype=np.int64).tobytes(),
                      np.concatenate(points).tobytes(),np.asarray([0,0],dtype=np.int32).tobytes())
            self.assertEqual(native._construction_geometry,expected)
            self.assertEqual(native._construction_handle,native._handle)
            points[0][:]=999
            self.assertEqual(native._construction_geometry,expected)
            self.assertTrue(all(isinstance(row,bytes)for row in native._construction_geometry))
        finally:native.close()

    def test_evidence_does_not_change_original_query(self):
        original=NativeSupport(self.points(),['box','box'])
        observed=NativeSupport(self.points(),['box','box'],capture_geometry=True)
        try:
            poses=np.asarray([[0.,0.,0.],[.1,0.,0.]],dtype=np.float64)
            rotations=np.repeat(np.eye(3)[None],2,axis=0);pairs=np.asarray([[0,1]],dtype=np.int64)
            left=original.evaluate(poses,rotations,pairs,.002);right=observed.evaluate(poses,rotations,pairs,.002)
            self.assertEqual(left.keys(),right.keys())
            for key in left:np.testing.assert_array_equal(left[key],right[key])
        finally:original.close();observed.close()

    def test_close_invalidates_optional_evidence(self):
        native=NativeSupport(self.points(),['box','box'],capture_geometry=True)
        self.assertIsNotNone(native._construction_geometry);native.close();native.close()
        self.assertIsNone(native._construction_geometry);self.assertIsNone(native._construction_handle)

    def test_different_actual_inputs_produce_different_evidence(self):
        points=self.points();other=self.points();other[1]*=2
        left=NativeSupport(points,['box','box'],capture_geometry=True)
        right=NativeSupport(other,['box','box'],capture_geometry=True)
        try:self.assertNotEqual(left._construction_geometry,right._construction_geometry)
        finally:left.close();right.close()

if __name__=='__main__':unittest.main()
