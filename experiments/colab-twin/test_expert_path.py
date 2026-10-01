"""Meaningful geometry boundaries for the reactive expert, without simulation."""
import unittest

import numpy as np

from expert_path import joint_path_lookahead


def joint(x=0.0, y=0.0):
    return np.array([x, y, 0, 0, 0], dtype=np.float64)


class ExpertPathTests(unittest.TestCase):
    def test_static_start_has_a_nonzero_forward_target(self):
        target, progress = joint_path_lookahead([joint(), joint(1)], joint(), .006)
        np.testing.assert_allclose(target, joint(.006), rtol=0, atol=1e-15)
        self.assertEqual(progress, 0)

    def test_off_path_pose_is_attracted_toward_the_route_while_advancing(self):
        actual = joint(.5, .3)
        target, progress = joint_path_lookahead([joint(), joint(1)], actual, .2)
        np.testing.assert_allclose(target, joint(.7))
        self.assertEqual(progress, .5)
        self.assertLess(abs(target[1]), abs(actual[1]))

    def test_progress_depends_on_actual_pose_and_never_on_call_count(self):
        route = [joint(), joint(1)]
        for _ in range(5):
            target, progress = joint_path_lookahead(route, joint(), .2)
            np.testing.assert_allclose(target, joint(.2))
            self.assertEqual(progress, 0)
        target, progress = joint_path_lookahead(route, joint(.4), .2)
        np.testing.assert_allclose(target, joint(.6))
        self.assertEqual(progress, .4)
        _, progress = joint_path_lookahead(route, joint(.1), .2)
        self.assertEqual(progress, .1, "No hidden monotonic waypoint index")

    def test_endpoint_and_beyond_endpoint_targets_do_not_overshoot(self):
        route = [joint(), joint(1)]
        for actual, expected_progress in [(joint(.95), .95), (joint(1), 1), (joint(1.5), 1)]:
            with self.subTest(actual=actual):
                target, progress = joint_path_lookahead(route, actual, .2)
                np.testing.assert_array_equal(target, joint(1))
                self.assertEqual(progress, expected_progress)
        target, _ = joint_path_lookahead(route, joint(-.3), .1)
        np.testing.assert_allclose(target, joint(.1))

    def test_lookahead_interpolates_across_a_corner_and_ignores_zero_edges(self):
        route = [joint(), joint(), joint(1), joint(1), joint(1, 1), joint(1, 1)]
        target, progress = joint_path_lookahead(route, joint(.8), .4)
        np.testing.assert_allclose(target, joint(1, .2))
        self.assertEqual(progress, .4)
        # The returned target follows the route, but actual->target cuts this
        # corner. This test deliberately does not call that chord collision-free.
        midpoint = (joint(.8) + target) / 2
        self.assertLess(midpoint[0], 1)
        self.assertGreater(midpoint[1], 0)

    def test_ambiguous_returning_branch_uses_first_nearest_segment(self):
        route = [joint(), joint(1), joint()]
        target, progress = joint_path_lookahead(route, joint(), .2)
        np.testing.assert_allclose(target, joint(.2))
        self.assertEqual(progress, 0, "A repeated pose alone cannot identify a later branch")

    def test_inputs_are_not_modified_and_the_target_owns_its_data(self):
        route = np.array([joint(), joint(1)])
        actual = joint(.5)
        route.flags.writeable = actual.flags.writeable = False
        target, _ = joint_path_lookahead(route, actual, .2)
        target[:] = 9
        np.testing.assert_array_equal(route, np.array([joint(), joint(1)]))
        np.testing.assert_array_equal(actual, joint(.5))

    def test_malformed_nonfinite_and_degenerate_inputs_are_rejected(self):
        invalid = [
            ([], joint(), .1), ([joint()], joint(), .1),
            (np.zeros((2, 6)), joint(), .1), ([joint(), joint(1)], np.zeros(6), .1),
            ([joint(), joint()], joint(), .1),
            ([joint(), joint(np.nan)], joint(), .1),
            ([joint(), joint(1)], joint(np.inf), .1),
        ]
        invalid += [([joint(), joint(1)], joint(), lookahead)
                    for lookahead in (0, -.1, np.inf, np.nan, True, np.array([.1]))]
        for route, actual, lookahead in invalid:
            with self.subTest(route=route, actual=actual, lookahead=lookahead):
                with self.assertRaises(ValueError):
                    joint_path_lookahead(route, actual, lookahead)


if __name__ == "__main__":
    unittest.main()
