"""Run the existing independent full-scan oracle against enabled four-vertex code."""
import unittest

import test_support_tree as tree_tests


class SupportQuadTests(tree_tests.SupportTreeTests):
    @classmethod
    def setUpClass(cls):
        cls.lib = tree_tests.build_test_library(quad_vertices=True)


if __name__ == '__main__':
    unittest.main()
