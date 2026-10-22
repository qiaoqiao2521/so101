"""Packed leaf loads and optional-copy failure use the original full-scan oracle."""
import unittest

import test_support_tree as tree_tests


class PackedLeafTests(tree_tests.SupportTreeTests):
    @classmethod
    def setUpClass(cls):
        cls.lib = tree_tests.build_test_library(leaf_packed=True)


class PackedLeafFallbackTests(tree_tests.SupportTreeTests):
    @classmethod
    def setUpClass(cls):
        cls.lib = tree_tests.build_test_library(leaf_packed=True, packed_empty=True)


if __name__ == '__main__':
    unittest.main()
