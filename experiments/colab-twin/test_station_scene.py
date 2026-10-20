"""Geometry contract for original STL meshes and live MuJoCo snapshots."""
import copy
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from grasp_episode import build_contact_scene
from station_scene import SOURCE, StationScene, mesh_manifest, preview
from test_station_executor import station
import run_visual_grasp
import station_executor


def rotation(quaternion):
    matrix = np.empty(9)
    quaternion = np.asarray(quaternion, dtype=float)
    mujoco.mju_quat2Mat(matrix, quaternion / np.linalg.norm(quaternion))
    return matrix.reshape(3, 3)


class SceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix='station-scene-test-')
        cls.model, cls.rig, _ = build_contact_scene(SOURCE, Path(cls.folder.name))
        cls.projector = StationScene(cls.model)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def data(self):
        result = mujoco.MjData(self.model)
        result.qpos[:6] = [.3, -.4, .25, -.2, .1, .5]
        result.qpos[6:9] = [.24, -.13, .01]
        mujoco.mj_forward(self.model, result)
        return result

    def test_manifest_contains_original_thirteen_stls(self):
        manifest = mesh_manifest()
        self.assertEqual(len(manifest['meshes']), 13)
        for mesh in manifest['meshes']:
            self.assertTrue((Path(manifest['mesh_directory']) / mesh['file']).is_file())
            self.assertEqual(mesh['url'], '/api/so101/meshes/' + mesh['file'])

    def test_full_visual_arm_and_world_primitives(self):
        entity = self.projector.update(self.data())['entities'][0]
        self.assertEqual(len(entity['models']), 17)
        self.assertEqual(len(entity['cylinders']), 6)
        self.assertEqual(len(entity['cubes']), 26)
        self.assertTrue(any(np.allclose(list(box['size'].values()), [.9, .7, .046])
                            for box in entity['cubes']))
        self.assertEqual(entity['frame_id'], 'world')

    def test_raw_stl_poses_equal_uncompiled_mjcf_visual_frames(self):
        """Independent original XML transforms detect mesh double-centering."""
        data = self.data()
        models = iter(self.projector.update(data)['entities'][0]['models'])
        root = ET.parse(SOURCE).getroot()
        for body in root.findall('.//body'):
            body_id = self.model.body(body.get('name')).id
            body_rotation = data.xmat[body_id].reshape(3, 3)
            for geom in body.findall('geom'):
                if geom.get('class') != 'visual':
                    continue
                actual = next(models)['pose']
                local_position = np.fromstring(geom.get('pos', '0 0 0'), sep=' ')
                local_quaternion = np.fromstring(geom.get('quat', '1 0 0 0'), sep=' ')
                expected_position = data.xpos[body_id] + body_rotation @ local_position
                expected_rotation = body_rotation @ rotation(local_quaternion)
                np.testing.assert_allclose(list(actual['position'].values()), expected_position, atol=2e-12)
                np.testing.assert_allclose(rotation(list(actual['orientation'].values())),
                                           expected_rotation, atol=2e-12)

    def test_payload_rotation_is_live_not_forced_upright(self):
        data = self.data()
        data.qpos[9:13] = [np.cos(.4), 0., 0., np.sin(.4)]
        mujoco.mj_forward(self.model, data)
        boxes = self.projector.update(data)['entities'][0]['cubes']
        target = next(box for box in boxes
                      if np.allclose(list(box['size'].values()), [.018, .018, .016]))
        np.testing.assert_allclose(list(target['pose']['orientation'].values()), data.xquat[-1], atol=1e-12)

    def test_snapshot_does_not_mutate_physical_data(self):
        data = self.data()
        before = (data.qpos.copy(), data.qvel.copy(), float(data.time))
        self.projector.update(data, elapsed_s=7.2)
        np.testing.assert_array_equal(data.qpos, before[0])
        np.testing.assert_array_equal(data.qvel, before[1])
        self.assertEqual(data.time, before[2])

    def test_preview_resolves_cube_parent_and_extra_obstacle_without_steps(self):
        value = copy.deepcopy(station())
        value['nodes'][-1]['position'][0] = .008
        value['nodes'].append({'id': 'extra', 'kind': 'obstacle', 'parent': 'world',
                               'position': [.4, .2, .065]})
        with patch.object(mujoco, 'mj_step', side_effect=AssertionError('preview integrated physics')):
            entity = preview(value)['entities'][0]
        cube = next(box for box in entity['cubes']
                    if np.allclose(list(box['size'].values()), [.018, .018, .016]))
        np.testing.assert_allclose(list(cube['pose']['position'].values()), [.248, -.13, .01])
        obstacle = entity['cubes'][-1]
        np.testing.assert_allclose(list(obstacle['pose']['position'].values()), [.4, .2, .065])
        self.assertEqual(len(entity['spheres']), 4)

    def test_task_goal_builds_matching_physical_planning_and_preview_tray(self):
        center = [.22, .17]
        value = copy.deepcopy(station())
        next(node for node in value['nodes'] if node['id'] == 'place')['position'][:2] = center
        with tempfile.TemporaryDirectory() as folder:
            physical, planning, _ = build_contact_scene(SOURCE, Path(folder), place_xy=center)
        for model in (physical, planning):
            np.testing.assert_array_equal(model.geom_pos[model.geom('place_floor').id, :2], center)
            np.testing.assert_array_equal(model.geom_pos[model.geom('pick_floor').id, :2], [.24, -.13])
        entity = preview(value)['entities'][0]
        self.assertTrue(any(np.allclose(list(box['size'].values()), [.12, .12, .002])
                            and np.allclose(list(box['pose']['position'].values()), [*center, .001])
                            for box in entity['cubes']))

    def test_tray_off_table_is_rejected_without_falling_back(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, '台面'):
                build_contact_scene(SOURCE, Path(folder), place_xy=[.8, .14])

    def rejected_episode(self, root, *, runner=None, **kwargs):
        """Stop at the existing initial vision rejection, without a renderer."""
        data = self.data()
        rejected = SimpleNamespace(valid=False, reason='test_missing_target',
                                   to_dict=lambda: {'valid': False})
        renderer = SimpleNamespace(close=lambda: None)
        with patch.object(run_visual_grasp, 'reset_scene', return_value=data), \
             patch.object(run_visual_grasp, 'CollisionChecker', return_value=object()), \
             patch.object(run_visual_grasp, 'record_collision_backend'), \
             patch.object(run_visual_grasp.TopDownCalibration, 'from_mujoco_model'), \
             patch.object(run_visual_grasp.mujoco, 'Renderer', return_value=renderer), \
             patch.object(run_visual_grasp, 'render_rgb', return_value=np.zeros((2, 2, 3))), \
             patch.object(run_visual_grasp, 'localize_green_target', return_value=rejected), \
             patch.object(run_visual_grasp, 'save_overlay'):
            report = (runner or run_visual_grasp.run_physical_episode)(SOURCE, root,
                {'max_episode_wall_s': 30, 'max_sim_s': 90},
                {'initial_xy_m': [.24, -.13], 'perturbed': False}, time.monotonic()+30,
                scene_builder=lambda *a, **k: (self.model, self.rig, None), **kwargs)
        return data, report

    def test_scene_hook_none_preserves_existing_rejection(self):
        with tempfile.TemporaryDirectory() as root:
            _, report = self.rejected_episode(Path(root)/'episode')
        self.assertFalse(report['passed'])
        self.assertEqual(report['failure_reason'], 'initial_localization_rejected: test_missing_target')

    def test_scene_hook_forces_terminal_actual_state_on_early_failure(self):
        updates = []
        def receive(model, data, **info):
            updates.append((data, data.qpos.copy(), info))
        with tempfile.TemporaryDirectory() as root:
            data, report = self.rejected_episode(Path(root)/'episode', scene_callback=receive)
        self.assertFalse(report['passed'])
        self.assertEqual([row[2]['final'] for row in updates], [False, True])
        self.assertIs(updates[-1][0], data)
        np.testing.assert_array_equal(updates[-1][1], data.qpos)

    def test_display_callback_failure_does_not_replace_physical_failure(self):
        def disconnected(*args, **kwargs):
            raise ConnectionError('display disconnected')
        with tempfile.TemporaryDirectory() as root, self.assertWarnsRegex(UserWarning, 'scene update failed'):
            _, report = self.rejected_episode(Path(root)/'episode', scene_callback=disconnected)
        self.assertEqual(report['failure_reason'], 'initial_localization_rejected: test_missing_target')

    def test_optional_display_import_failure_preserves_original_physical_result(self):
        original_runner = run_visual_grasp.run_physical_episode

        def rejected(source, output, protocol, case, deadline, **kwargs):
            _, report = self.rejected_episode(output, runner=original_runner,
                                              scene_callback=kwargs['scene_callback'])
            return report

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/'request.json'
            source.write_text(json.dumps({'station': station()}))
            with patch.object(run_visual_grasp, 'run_physical_episode', side_effect=rejected), \
                 patch.dict('sys.modules', {'station_scene': None}), \
                 self.assertWarnsRegex(UserWarning, 'scene update failed'):
                code = station_executor.run(source, root, None)
            status = json.loads((root/'status.json').read_text())
        self.assertEqual(code, 1)
        self.assertEqual(status['report']['failure_reason'],
                         'initial_localization_rejected: test_missing_target')


if __name__ == '__main__':
    unittest.main()
