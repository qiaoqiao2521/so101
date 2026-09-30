"""Offline acceptance using the complete, existing SO101 mesh model."""
import hashlib
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from collision_scene import CollisionChecker, build_scene


SOURCE = Path(__file__).resolve().parents[2] / (
    "workspaces/so101_ws/src/so101_mujoco/models/so101.xml"
)
INITIAL = np.array([0, 0, 0, 0, 0, 0.35], dtype=float)


class CollisionSceneAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temp.name)
        cls.source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        cls.asset_hashes = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (SOURCE.parent / "assets").glob("*.stl")
        }
        cls.scene_path = cls.folder / "scene.xml"
        cls.model = build_scene(SOURCE, cls.scene_path, [])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.checker = CollisionChecker(self.model)

    def test_complete_meshes_active_masks_and_source_preserved(self):
        source_xml = ET.parse(SOURCE).getroot()
        self.assertEqual(len(source_xml.findall("./asset/mesh")), 13)
        self.assertEqual(len(self.asset_hashes), 13)
        self.assertEqual(len(source_xml.findall(".//geom[@class='collision']")), 13)
        collision_ids = np.flatnonzero(self.model.geom_group == 3)
        self.assertEqual(len(collision_ids), 18)  # 13 moving + 4 fixed base + table.
        self.assertEqual(sum(self.model.geom_type[i] == mujoco.mjtGeom.mjGEOM_MESH
                             for i in collision_ids), 17)
        self.assertTrue(np.all(self.model.geom_contype[collision_ids] == 1))
        self.assertTrue(np.all(self.model.geom_conaffinity[collision_ids] == 1))
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), self.source_hash)
        for path in (SOURCE.parent / "assets").glob("*.stl"):
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                             self.asset_hashes[path.name])

    def test_initial_valid_and_checker_state_independent(self):
        execution = mujoco.MjData(self.model)
        execution.qpos[:] = [0.2, 0.1, -0.1, 0.2, 0.3, 0.35]
        before = execution.qpos.copy()
        result = self.checker.evaluate(INITIAL)
        self.assertTrue(result["valid"], result)
        self.assertGreater(result["min_distance_m"], self.checker.margin_m)
        self.assertEqual(self.checker.data.ncon, 0)
        np.testing.assert_array_equal(execution.qpos, before)
        self.assertIsNot(execution, self.checker.data)

    def test_environment_has_visible_copies_without_extra_collisions(self):
        model = build_scene(SOURCE, self.folder / "visible.xml", [{
            "name": "blocker", "pos": [0.346, -0.17, 0.226],
            "size": [0.035, 0.035, 0.045], "rgba": [0.9, 0.25, 0.15, 1],
        }])
        checker = CollisionChecker(model)
        visual_ids = []
        for name in ("worktable", "blocker"):
            collision, visible = model.geom(name).id, model.geom(f"visible_{name}").id
            visual_ids.append(visible)
            self.assertEqual(model.geom_bodyid[visible], 0)
            self.assertEqual(model.geom_group[visible], 2)
            self.assertEqual(model.geom_contype[visible], 0)
            self.assertEqual(model.geom_conaffinity[visible], 0)
            self.assertEqual(model.geom_group[collision], 3)
            self.assertEqual(model.geom_contype[collision], 1)
            self.assertEqual(model.geom_conaffinity[collision], 1)
            for field in ("geom_type", "geom_pos", "geom_quat", "geom_size", "geom_rgba"):
                values = getattr(model, field)
                np.testing.assert_array_equal(values[visible], values[collision])
        self.assertEqual(sum(model.geom(i).name.startswith("visible_")
                             for i in range(model.ngeom) if model.geom(i).name), 2)
        self.assertTrue(all(not set(pair).intersection(visual_ids) for pair in checker.pairs))
        result = checker.evaluate(INITIAL)
        self.assertTrue(result["valid"], result)
        self.assertAlmostEqual(result["min_distance_m"],
                               self.checker.evaluate(INITIAL)["min_distance_m"], places=10)
        # The normal renderer's scene includes group 2, while group 3 remains
        # hidden. Inspect the generated render scene without needing OpenGL.
        data = mujoco.MjData(model)
        data.qpos[:] = INITIAL
        mujoco.mj_forward(model, data)
        scene = mujoco.MjvScene(model, maxgeom=1000)
        option = mujoco.MjvOption()
        mujoco.mjv_updateScene(model, data, option, None, mujoco.MjvCamera(),
                             mujoco.mjtCatBit.mjCAT_ALL, scene)
        shown = {int(geom.objid) for geom in scene.geoms[:scene.ngeom]
                 if geom.objtype == mujoco.mjtObj.mjOBJ_GEOM}
        self.assertTrue(set(visual_ids).issubset(shown))
        self.assertNotIn(model.geom("blocker").id, shown)
        self.assertNotIn(model.geom("worktable").id, shown)

    def test_pure_base_yaw_preserves_clearance(self):
        # MuJoCo 3.3.7 native CCD previously returned zero for five of these
        # separated poses. Keep the persisted libccd choice and real invariant.
        self.assertTrue(self.model.opt.disableflags &
                        int(mujoco.mjtDisableBit.mjDSBL_NATIVECCD))
        distances = []
        for yaw in np.linspace(-1.5, 1.5, 15):
            result = self.checker.evaluate([yaw, 0, 0, 0, 0])
            self.assertTrue(result["valid"], result)
            distances.append(result["min_distance_m"])
        self.assertLess(np.ptp(distances), 1e-10)

    def test_only_concrete_assembly_neighbours_are_exempt(self):
        self.assertEqual(self.model.nexclude, 6)
        mount_exclusions = 0
        for exclusion in self.checker.excluded_pairs:
            first, second = [self.model.geom(name).id for name in exclusion["pair"]]
            a, b = [int(self.model.geom_bodyid[i]) for i in (first, second)]
            reason = exclusion["reason"]
            if reason == "same_rigid_body":
                self.assertEqual(a, b)
            elif reason == "direct_parent_child_joint":
                self.assertNotEqual(a, 0)
                self.assertNotEqual(b, 0)
                self.assertTrue(self.model.body_parentid[a] == b or
                                self.model.body_parentid[b] == a)
            else:
                self.assertEqual(reason, "fixed_base_worktable_mount")
                self.assertIn("worktable", exclusion["pair"])
                self.assertIn("base", [self.model.body(i).name for i in (a, b)])
                mount_exclusions += 1
        self.assertEqual(mount_exclusions, 4)

    def test_obstacle_inside_gripper_is_rejected(self):
        self.checker.evaluate(INITIAL)
        center = self.checker.data.geom_xpos[
            self.model.geom("collision_gripper_1").id
        ].copy()
        model = build_scene(SOURCE, self.folder / "blocked.xml", [{
            "name": "blocker", "pos": center.tolist(), "size": [0.015] * 3,
        }])
        checker = CollisionChecker(model)
        result = checker.evaluate(INITIAL)
        self.assertFalse(result["valid"], result)
        self.assertEqual(result["reason"], "obstacle_collision")
        self.assertIn("blocker", result["pair"])
        self.assertLess(result["min_distance_m"], -0.001)
        blocker = model.geom("blocker").id
        # The anchored base exemption applies only to its mounting table.
        base_pairs = [pair for pair in checker.pairs if blocker in pair and
                      any(model.body(int(model.geom_bodyid[i])).name == "base"
                          for i in pair)]
        self.assertEqual(len(base_pairs), 4)

    def test_nonadjacent_self_collision_found_by_seeded_sampling(self):
        rng = np.random.default_rng(928)
        hit = None
        for _ in range(20):
            q = rng.uniform(self.checker.bounds[:, 0], self.checker.bounds[:, 1])
            result = self.checker.evaluate(q)
            if result["reason"] == "self_collision" and result["min_distance_m"] < -0.001:
                hit = result
                break
        self.assertIsNotNone(hit, "No negative-distance self collision in fixed real-model sample")
        first, second = [self.model.geom(name).id for name in hit["pair"]]
        a, b = [int(self.model.geom_bodyid[i]) for i in (first, second)]
        self.assertNotEqual(a, b)
        self.assertNotEqual(self.model.body_parentid[a], b)
        self.assertNotEqual(self.model.body_parentid[b], a)

    def test_table_is_an_environment_collision(self):
        model = build_scene(SOURCE, self.folder / "raised-table.xml", [], table_z=0.12)
        result = CollisionChecker(model).evaluate(INITIAL)
        self.assertFalse(result["valid"], result)
        self.assertEqual(result["reason"], "table_collision")
        self.assertIn("worktable", result["pair"])
        self.assertLess(result["min_distance_m"], 0)

    def test_nonfinite_shape_limits_and_gripper_validation(self):
        for q in ([0] * 4, [0] * 7, [0, 0, np.nan, 0, 0], [0, 0, np.inf, 0, 0]):
            result = self.checker.evaluate(q)
            self.assertFalse(result["valid"])
            self.assertIsNone(result["min_distance_m"])
        outside = INITIAL.copy()
        outside[0] = self.model.jnt_range[0, 1] + 0.01
        self.assertEqual(self.checker.evaluate(outside)["reason"], "joint_limit")
        actual = INITIAL.copy()
        actual[5] = 0.25
        self.assertEqual(self.checker.evaluate(actual)["reason"], "gripper_not_fixed")
        result = self.checker.evaluate(actual, require_fixed_gripper=False)
        self.assertIsNotNone(result["min_distance_m"])
        self.assertEqual(self.checker.data.qpos[5], 0.25)
        actual[5] = self.model.jnt_range[5, 1] + 0.01
        self.assertEqual(self.checker.evaluate(actual, require_fixed_gripper=False)["reason"],
                         "joint_limit")

    def test_source_overwrite_and_invalid_obstacle_rejected(self):
        with self.assertRaises(ValueError):
            build_scene(SOURCE, SOURCE, [])
        bad_obstacles = [
            {"name": "bad", "pos": [0, 0, np.nan], "size": [0.01] * 3},
            {"name": "bad", "pos": [0, 0, 0], "size": [0, 0.01, 0.01]},
            {"name": "worktable", "pos": [0, 0, 0], "size": [0.01] * 3},
            {"name": "bad", "pos": [0, 0, 0], "size": [0.01] * 3,
             "rgba": [1, 0, 0, 2]},
        ]
        for obstacle in bad_obstacles:
            with self.subTest(obstacle=obstacle), self.assertRaises(ValueError):
                build_scene(SOURCE, self.folder / "invalid.xml", [obstacle])


if __name__ == "__main__":
    unittest.main()
