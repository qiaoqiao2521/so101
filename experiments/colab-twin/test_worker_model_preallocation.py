"""Owned native models, fresh release estimates and original cleanup failures."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import mujoco
import numpy as np

from released_object import ReleasedObjectQuery
from route_policy import load_route_policy
import visual_grasp_controller as module


class WorkerModelPreallocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.scene = Path(cls.directory.name)/'six-joints.xml'
        body = ''.join('<body pos="0 0 .05"><joint axis="0 1 0"/>'
                       '<geom type="sphere" size=".01"/>' for _ in range(6))
        cls.scene.write_text('<mujoco><worldbody>'+body+'</body>'*6+'</worldbody></mujoco>')

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def controller(self):
        controller = module.VisualGraspController.__new__(module.VisualGraspController)
        controller.rig = mujoco.MjModel.from_xml_path(str(self.scene))
        controller.released_query = ReleasedObjectQuery(self.scene)
        controller.plan_reports = []
        controller.transport_job = controller.separation_job = None
        return controller

    def test_prepared_models_are_independent_and_no_copy_occurs_at_handoff(self):
        controller = self.controller()
        controller._prepare_worker_models()
        with patch.object(module.copy, 'copy', side_effect=AssertionError('late clone')):
            transport = controller._transport_worker_model()
            separation, released = controller._separation_worker_models()
        self.assertIsNot(transport, separation)
        for clone, source in ((transport, controller.rig), (separation, controller.rig),
                              (released, controller.released_query.model)):
            np.testing.assert_array_equal(clone.qpos0, source.qpos0)
            self.assertFalse(np.shares_memory(clone.geom_pos, source.geom_pos))
            clone.qpos0[0] = .3
            self.assertEqual(source.qpos0[0], 0.)
        record = controller.plan_reports[-1]
        self.assertEqual(record['models_prepared'], 3)
        self.assertTrue(record['used_transport'] and record['used_separation'])
        json.dumps(record, allow_nan=False)

    def test_handoff_copies_the_latest_estimated_center_and_yaw(self):
        controller = self.controller()
        controller._prepare_worker_models()
        yaw = .25
        rotation = np.array([[np.cos(yaw), -np.sin(yaw), 0.],
                             [np.sin(yaw), np.cos(yaw), 0.], [0., 0., 1.]])
        query = controller.released_query
        query.freeze([.2, .1, .01], rotation)
        _, released = controller._separation_worker_models()
        for name in ('geom_pos', 'geom_quat', 'geom_sameframe'):
            self.assertEqual(getattr(released, name).tobytes(), getattr(query.model, name).tobytes())
        self.assertIsNot(released, query.model)

    def test_replaced_sources_use_independent_current_models(self):
        for changed in ('rig', 'query', 'released_model', 'object_id'):
            with self.subTest(changed=changed):
                controller = self.controller()
                controller._prepare_worker_models()
                prepared = controller._prepared_worker_models
                original_rig = controller.rig
                if changed == 'rig':
                    controller.rig = copy.copy(controller.rig)
                elif changed == 'query':
                    controller.released_query = ReleasedObjectQuery(self.scene)
                elif changed == 'released_model':
                    controller.released_query.model = copy.copy(controller.released_query.model)
                else:
                    controller.released_query.object_id = (controller.released_query.object_id+1) % controller.released_query.model.ngeom
                rig, released = controller._separation_worker_models()
                self.assertIsNot(rig, prepared['separation_rig'])
                self.assertIsNot(released, prepared['released_model'])
                self.assertIs(prepared['source_rig'], original_rig)
                self.assertFalse(controller.plan_reports[-1]['used_separation'])
                if changed == 'rig':
                    self.assertIsNot(controller._transport_worker_model(), prepared['transport_rig'])

    def test_custom_query_and_optional_preparation_failure_keep_eager_path(self):
        class CustomQuery(ReleasedObjectQuery):
            pass
        controller = self.controller()
        controller.released_query = CustomQuery(self.scene)
        with self.assertWarnsRegex(UserWarning, 'released_query_unsupported'):
            controller._prepare_worker_models()
        self.assertIsNone(controller._prepared_worker_models)
        self.assertIsNot(controller._transport_worker_model(), controller.rig)
        controller = self.controller()
        with patch.object(module.copy, 'copy', side_effect=MemoryError('optional preparation')):
            with self.assertWarnsRegex(UserWarning, 'MemoryError'):
                controller._prepare_worker_models()
        self.assertIsNone(controller._prepared_worker_models)
        rig, released = controller._separation_worker_models()
        self.assertIsNot(rig, controller.rig)
        self.assertIsNot(released, controller.released_query.model)

    def test_original_cleanup_error_retains_models_and_both_jobs_are_closed(self):
        controller = self.controller()
        controller._prepare_worker_models()
        prepared = controller._prepared_worker_models
        first, second = Mock(), Mock()
        original = RuntimeError('original worker cleanup failed')
        first.close.side_effect = original
        controller.transport_job, controller.separation_job = first, second
        with self.assertRaises(RuntimeError) as caught:
            controller.close()
        self.assertIs(caught.exception, original)
        self.assertIs(controller._prepared_worker_models, prepared)
        first.close.assert_called_once()
        second.close.assert_called_once()
        first.close.side_effect = None
        controller.close()
        self.assertIsNone(controller._prepared_worker_models)

    def test_original_path_tolerates_unprepared_controller_fixtures(self):
        controller = self.controller()
        self.assertIsNot(controller._transport_worker_model(), controller.rig)
        rig, released = controller._separation_worker_models()
        self.assertIsNot(rig, controller.rig)
        self.assertIsNot(released, controller.released_query.model)

    def test_selection_stays_opt_in_with_current_parent_and_map_disabled(self):
        parent = load_route_policy()[0].preferences()
        candidate = load_route_policy(Path(__file__).parent/'route_strategies/preallocate_worker_models.py')[0].preferences()
        self.assertFalse(parent['preallocate_worker_models'])
        self.assertFalse(candidate['map_context_freeze'])
        self.assertEqual({key for key in parent if parent[key] != candidate[key]},
                         {'preallocate_worker_models'})


if __name__ == '__main__':
    unittest.main()
