"""Real cyclic collection and restoration through original episode failures."""
import gc
from pathlib import Path
import unittest
from unittest.mock import patch
import weakref

from episode_gc import DeferredGCWindow
from route_policy import load_route_policy
from run_visual_grasp import run_physical_episode


class GCWindowTests(unittest.TestCase):
    def setUp(self):
        self.enabled = gc.isenabled()
        self.addCleanup(gc.enable if self.enabled else gc.disable)

    def test_cycles_survive_control_and_are_collected_in_cleanup(self):
        class Node:
            pass
        gc.enable()
        thresholds = gc.get_threshold()
        window = DeferredGCWindow()
        self.addCleanup(window.restore)
        window.begin()
        self.assertFalse(gc.isenabled())
        value = Node()
        value.link = value
        reference = weakref.ref(value)
        del value
        self.assertIsNotNone(reference())
        window.finish()
        self.assertIsNone(reference())
        self.assertTrue(gc.isenabled())
        self.assertEqual(gc.get_threshold(), thresholds)
        self.assertTrue(window.details['restored'])
        self.assertIsNone(window.details['cleanup_error'])
        self.assertGreaterEqual(window.details['collected_at_cleanup'], 1)

    def test_callers_disabled_gc_is_preserved_without_forced_collection(self):
        gc.disable()
        window = DeferredGCWindow()
        self.addCleanup(window.restore)
        window.begin()
        with patch('episode_gc.gc.collect') as collect:
            window.finish()
            collect.assert_not_called()
        self.assertFalse(gc.isenabled())
        self.assertFalse(window.details['deferred'])
        self.assertTrue(window.details['restored'])

    def test_outer_episode_finally_preserves_original_errors_and_restores_gc(self):
        for original in (RuntimeError('original cleanup failure'), KeyboardInterrupt()):
            with self.subTest(error=type(original).__name__):
                gc.enable()
                def interrupted(*args, gc_window, **kwargs):
                    gc_window.begin()
                    self.assertFalse(gc.isenabled())
                    raise original
                with patch('run_visual_grasp._run_physical_episode', side_effect=interrupted):
                    with self.assertRaises(type(original)) as caught:
                        run_physical_episode(None, None, None, None, None)
                self.assertIs(caught.exception, original)
                self.assertTrue(gc.isenabled())

    def test_collection_error_restores_caller_and_is_not_retried(self):
        gc.enable()
        window = DeferredGCWindow()
        self.addCleanup(window.restore)
        window.begin()
        with patch('episode_gc.gc.collect', side_effect=RuntimeError('optional')) as collect:
            with self.assertWarnsRegex(RuntimeWarning, 'deferred GC cleanup'):
                window.finish()
            window.finish()
            collect.assert_called_once()
        self.assertTrue(gc.isenabled())
        self.assertEqual(window.details['cleanup_error'], 'RuntimeError')

    def test_failed_worker_join_skips_forced_collection_but_restores_state(self):
        gc.enable()
        window = DeferredGCWindow()
        self.addCleanup(window.restore)
        window.begin()
        with patch('episode_gc.gc.collect') as collect:
            window.finish(collect=False)
        collect.assert_not_called()
        self.assertTrue(gc.isenabled())

    def test_unselected_episode_does_not_change_gc(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                (gc.enable if enabled else gc.disable)()
                with patch('run_visual_grasp._run_physical_episode', return_value={'passed': False}):
                    self.assertEqual(run_physical_episode(None, None, None, None, None), {'passed': False})
                self.assertEqual(gc.isenabled(), enabled)

    def test_policy_differs_only_in_gc_with_other_experiments_disabled(self):
        parent = load_route_policy(
            Path(__file__).parent/'route_strategies/smooth_jaw_leg_clock.py')[0].preferences()
        candidate = load_route_policy(Path(__file__).parent/'route_strategies/defer_cyclic_gc.py')[0].preferences()
        self.assertEqual([key for key in parent if parent[key] != candidate[key]], ['defer_cyclic_gc'])
        self.assertFalse(parent['defer_cyclic_gc'])
        self.assertFalse(candidate['map_context_freeze'])
        self.assertFalse(candidate['preallocate_worker_models'])


if __name__ == '__main__':
    unittest.main()
