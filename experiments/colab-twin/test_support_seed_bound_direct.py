"""Same-projection reuse, optional packed fallback and slot collisions."""
import unittest

import test_support_tree as tree_tests


class SeedBoundTests(tree_tests.SupportTreeTests):
    @classmethod
    def setUpClass(cls):
        cls.lib = tree_tests.build_test_library(leaf_packed=True, packed_inline=True,
                                              seed_bound_direct=True)


class SeedBoundPackedFallbackTests(tree_tests.SupportTreeTests):
    @classmethod
    def setUpClass(cls):
        cls.lib = tree_tests.build_test_library(leaf_packed=True, packed_inline=True,
                                              seed_bound_direct=True, packed_empty=True)


class SeedBoundCollisionTests(tree_tests.SupportTreeTests):
    @classmethod
    def setUpClass(cls):
        cls.lib = tree_tests.build_test_library(leaf_packed=True, packed_inline=True,
                                              seed_bound_direct=True, seed_bound_tiny=True)


if __name__ == '__main__':
    unittest.main()
