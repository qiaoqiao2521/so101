"""Transport-only dispatch; fake planner and geometry, no physical acceptance."""
import unittest
from unittest.mock import Mock, patch

from configuration_sweep import validate_configuration_path
from route_policy import RoutePolicy, load_route_policy, DEFAULT_SOURCE
import test_visual_grasp_controller as fixtures


class TransportPrefixDispatchTests(unittest.TestCase):
    def controller(self, **kwargs):
        return fixtures.VisualControllerTests.controller(self, **kwargs)

    def test_flag_is_explicit_and_parent_preferences_are_unchanged(self):
        self.assertFalse(RoutePolicy().transport_refinement_prefix)
        default, _ = load_route_policy(DEFAULT_SOURCE)
        self.assertFalse(default.transport_refinement_prefix)
        with self.assertRaisesRegex(ValueError, 'must be a boolean'):
            RoutePolicy(transport_refinement_prefix=1)
        from route_strategies.loaded_jaw_midpoint_details import route_preferences as parent
        from route_strategies.loaded_jaw_transport_prefix import route_preferences as child
        self.assertEqual(child(), {**parent(), 'transport_refinement_prefix': True})

    def test_constructor_keeps_original_batch_and_requests_separate_prefix(self):
        legacy = Mock(side_effect=lambda states: (len(states), -1))
        prefix = Mock(side_effect=lambda states: (len(states), -1))
        with patch('sweep_batch.make_validator', side_effect=[legacy, prefix]) as factory:
            c = self.controller(route_policy=RoutePolicy(batch_configuration_sweep=True,
                                                       mesh_box_axis_refinement=True,
                                                       transport_refinement_prefix=True))
        self.assertEqual(factory.call_count, 2)
        self.assertIs(c.batch_sweep_validator, legacy)
        self.assertIs(c.transport_prefix_validator, prefix)
        self.assertEqual(factory.call_args.kwargs,
                         {'direction_hints': False, 'refinement_prefix': True})

    def test_default_does_not_prepare_prefix(self):
        with patch('sweep_batch.make_validator') as factory:
            c = self.controller()
        factory.assert_not_called()
        self.assertIsNone(c.transport_prefix_validator)

    def test_prefix_only_selects_online_transport_not_other_stages_or_closures(self):
        c = self.controller()
        legacy = Mock(side_effect=lambda states: (len(states), -1))
        prefix = Mock(side_effect=lambda states: (len(states), -1))
        c.batch_sweep_validator, c.transport_prefix_validator = legacy, prefix
        start, end = c.initial_q.copy(), c.initial_q.copy()
        end[5] = .015
        for stage, purpose in [('transport', 'online_chord'), ('close', 'online_chord'),
                               ('lift', 'online_chord'), ('hold', 'online_chord'),
                               ('lower', 'online_chord'), ('separate', 'online_chord'),
                               ('transport', 'planned_closure'),
                               ('transport', 'measured_closure')]:
            with self.subTest(stage=stage, purpose=purpose):
                c.stage = stage
                legacy.reset_mock(); prefix.reset_mock(); c.checker.evaluate.reset_mock()
                report = c._configuration_sweep(start, end, purpose=purpose)
                self.assertTrue(report['valid'])
                self.assertEqual(report['required_states'], 244)
                self.assertEqual(report['checked_states'], 244)
                selected = stage == 'transport' and purpose == 'online_chord'
                self.assertEqual(prefix.call_count, int(selected))
                self.assertEqual(legacy.call_count, int(not selected))
                c.checker.evaluate.assert_not_called()

    def test_unavailable_prefix_retains_legacy_and_rejected_prefix_replays_full_scalar(self):
        c = self.controller(); c.stage = 'transport'
        start, end = c.initial_q.copy(), c.initial_q.copy(); end[5] = .015
        c.batch_sweep_validator = Mock(side_effect=lambda states: (len(states), -1))
        c.transport_prefix_validator = None
        c._configuration_sweep(start, end)
        c.batch_sweep_validator.assert_called_once()
        c.batch_sweep_validator.reset_mock(); c.checker.evaluate.reset_mock()
        c.transport_prefix_validator = Mock(return_value=None)
        report = c._configuration_sweep(start, end)
        self.assertEqual(report, validate_configuration_path(start, end, lambda q: True))
        self.assertEqual(c.checker.evaluate.call_count, 244)
        c.batch_sweep_validator.assert_not_called()


if __name__ == '__main__':
    unittest.main()
