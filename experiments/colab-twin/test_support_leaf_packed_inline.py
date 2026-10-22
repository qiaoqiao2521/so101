"""Inline and optional-copy fallback retain the original full-scan oracle."""
import unittest

import test_support_tree as tree_tests


class InlinePackedLeafTests(tree_tests.SupportTreeTests):
    @classmethod
    def setUpClass(cls):
        cls.lib = tree_tests.build_test_library(leaf_packed=True, packed_inline=True)


class InlinePackedFallbackTests(tree_tests.SupportTreeTests):
    @classmethod
    def setUpClass(cls):
        cls.lib = tree_tests.build_test_library(leaf_packed=True, packed_inline=True,
                                              packed_empty=True)


if __name__ == '__main__':
    unittest.main()
