"""Behavior tests using the installed OMPL, without ROS, MuJoCo or cloud jobs."""

import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

from joint_planner import plan_joint_path, validate_joint_path


BOUNDS = [[-1.0, 1.0] for _ in range(5)]
START = [-0.8, 0.0, 0.0, 0.0, 0.0]
GOAL = [0.8, 0.0, 0.0, 0.0, 0.0]


def misses_padded_blocker(q):
    # The core rectangle is padded beyond the discrete sampling resolution.
    return not (abs(q[0]) <= 0.23 and abs(q[1]) <= 0.38)


def segment_hits_core_rectangle(a, b):
    """Independent continuous 2D slab intersection, not sampled validation."""
    enter, leave = 0.0, 1.0
    for index, half_width in enumerate((0.2, 0.35)):
        delta = b[index] - a[index]
        if abs(delta) < 1e-15:
            if abs(a[index]) > half_width:
                return False
            continue
        crossings = sorted(((-half_width - a[index]) / delta, (half_width - a[index]) / delta))
        enter, leave = max(enter, crossings[0]), min(leave, crossings[1])
        if enter > leave:
            return False
    return enter <= leave


class JointPlannerTests(unittest.TestCase):
    def test_real_rrtconnect_routes_around_blocked_middle(self):
        self.assertTrue(misses_padded_blocker(START))
        self.assertTrue(misses_padded_blocker(GOAL))
        self.assertTrue(segment_hits_core_rectangle(START, GOAL))
        self.assertFalse(misses_padded_blocker([0.0] * 5))
        result = plan_joint_path(START, GOAL, BOUNDS, misses_padded_blocker, timeout_s=2.0)
        self.assertEqual(result["ompl_version"], "2.0.1")
        self.assertEqual(result["status"], "solved", result)
        self.assertTrue(result["exact_solution"])
        self.assertEqual(result["path"][0], START)
        self.assertEqual(result["path"][-1], GOAL)
        self.assertGreater(result["planning_seconds"], 0.0)
        self.assertTrue(result["validation"]["valid"])
        for a, b in zip(result["path"], result["path"][1:]):
            self.assertLessEqual(math.dist(a, b), 0.025 + 1e-12)
            self.assertFalse(segment_hits_core_rectangle(a, b))

    def test_validator_rejects_collision_between_valid_endpoints(self):
        report = validate_joint_path([START, GOAL], misses_padded_blocker, 0.025)
        self.assertFalse(report["valid"])
        self.assertEqual(report["invalid_segment"], 0)
        self.assertGreater(report["checked_states"], 2)
        self.assertFalse(misses_padded_blocker(report["invalid_state"]))

    def test_invalid_start_and_out_of_bounds_start_are_rejected(self):
        for start in ([0.0] * 5, [-1.1, 0.0, 0.0, 0.0, 0.0]):
            result = plan_joint_path(start, GOAL, BOUNDS, misses_padded_blocker)
            self.assertEqual(result["status"], "invalid_start")
            self.assertIsNone(result["path"])
            self.assertFalse(result["exact_solution"])

    def test_invalid_goal_is_rejected(self):
        result = plan_joint_path(START, [0.0] * 5, BOUNDS, misses_padded_blocker)
        self.assertEqual(result["status"], "invalid_goal")
        self.assertIsNone(result["path"])

    def test_impenetrable_wall_never_returns_approximate_path_as_solved(self):
        result = plan_joint_path(
            START, GOAL, BOUNDS, lambda q: abs(q[0]) >= 0.2, timeout_s=0.25
        )
        self.assertEqual(result["status"], "timeout", result)
        self.assertIsNone(result["path"])
        self.assertFalse(result["exact_solution"])
        self.assertIn(result["reason"], ("no_exact_solution", "approximate_solution_rejected"))

    def test_equal_start_goal_preserves_endpoints(self):
        result = plan_joint_path(START, START, BOUNDS, misses_padded_blocker, timeout_s=0.25)
        self.assertEqual(result["status"], "solved", result)
        self.assertEqual(result["path"][0], START)
        self.assertEqual(result["path"][-1], START)

    def test_seed_initializes_once_in_fresh_process(self):
        script = """
import json
from joint_planner import plan_joint_path
bounds = [[-1, 1]] * 5
start, goal = [-0.3] * 5, [0.3] * 5
results = [plan_joint_path(start, goal, bounds, lambda q: True, seed=seed)
           for seed in [17, 18]]
print(json.dumps({'statuses': [r['status'] for r in results],
                  'seeds': [r['rng_seed'] for r in results],
                  'requested': [r['requested_seed'] for r in results]}))
"""
        process = subprocess.run(
            [sys.executable, "-c", script], cwd=Path(__file__).parent,
            capture_output=True, text=True, check=True,
        )
        record = json.loads(process.stdout.splitlines()[-1])
        self.assertEqual(record["statuses"], ["solved", "solved"])
        self.assertEqual(record["seeds"], [17, 17])
        self.assertEqual(record["requested"], [17, 18])
        self.assertNotIn("Random number generation already started", process.stderr)


if __name__ == "__main__":
    unittest.main()
