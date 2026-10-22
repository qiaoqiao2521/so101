"""Original full-scan oracle and exact vertex coverage for finer BVH leaves."""
import unittest

import numpy as np
import test_support_tree as tree_tests


class SupportLeaf8Tests(tree_tests.SupportTreeTests):
    @classmethod
    def setUpClass(cls):
        cls.lib = tree_tests.build_test_library(tree_leaf8=True)

    def test_leaf_split_boundaries_and_complete_coverage(self):
        rng = np.random.default_rng(20261023)
        for count, nodes, largest in ((8, 1, 8), (9, 3, 5), (16, 3, 8),
                                      (17, 5, 8), (33, 9, 8)):
            with self.subTest(count=count):
                rows = self.compare(f'leaf8-split-{count}', rng.normal(size=(count, 3)),
                                    [[1., 1.], [-.5, -.5], [.25, .25]], fallback=False)
                self.assertEqual(rows[1]['info'][1:3], [nodes, largest])


if __name__ == '__main__':
    unittest.main()
