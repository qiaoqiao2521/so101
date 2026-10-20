"""Station admission must preserve editable intent and avoid silent substitutions."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from station_executor import FIXED_NODES, TEMPLATE, UnsupportedStation, run, validate_station


def station():
    return {'name': 'test', 'notes': '',
            'nodes': [{'id': key, 'kind': kind, 'parent': 'world', 'position': xyz.copy()}
                      for key, (kind, xyz) in FIXED_NODES.items()]+
                     [{'id': 'cube', 'kind': 'object', 'parent': 'pick', 'position': [0, 0, .01]}],
            'program': [{'id': str(i), 'action': action, 'target': target, 'seconds': 1}
                        for i, (action, target) in enumerate(TEMPLATE)]}


class AdmissionTests(unittest.TestCase):
    def test_place_frame_moves_release_and_clear_by_same_task_goal(self):
        value = station()
        for node in value['nodes']:
            if node['id'] == 'place':
                node['position'] = [.22, .17, 0]
            elif node['id'] in ('release', 'clear'):
                node['parent'] = 'place'
                node['position'][:2] = [0, 0]
        result = validate_station(value)
        self.assertEqual(result['place_xy_m'], [.22, .17])
        self.assertEqual(result['resolved_positions_m']['release'], [.22, .17, .03])
        self.assertEqual(result['resolved_positions_m']['clear'], [.22, .17, .1])

    def test_place_height_is_still_explicitly_unsupported(self):
        value = station()
        next(node for node in value['nodes'] if node['id'] == 'place')['position'][2] = .02
        with self.assertRaisesRegex(UnsupportedStation, 'place'):
            validate_station(value)

    def test_nondefault_goal_does_not_need_python_coordinate_whitelist(self):
        value = station()
        for node in value['nodes']:
            if node['id'] in ('place', 'release', 'clear'):
                node['position'][:2] = [.38, .21]
        self.assertEqual(validate_station(value)['place_xy_m'], [.38, .21])

    def test_default_and_changed_cube_are_resolved(self):
        value = station()
        self.assertEqual(validate_station(value)['cube_xyz_m'], [.24, -.13, .01])
        value['nodes'][-1]['position'][0] = .009
        self.assertAlmostEqual(validate_station(value)['cube_xyz_m'][0], .249)

    def test_frame_reparent_preserving_world_position_is_supported(self):
        value = station()
        value['nodes'].append({'id': 'offset', 'kind': 'frame', 'parent': 'world', 'position': [.1, 0, 0]})
        value['nodes'][0]['parent'] = 'offset'
        value['nodes'][0]['position'] = [-.1, 0, 0]
        self.assertEqual(validate_station(value)['resolved_positions_m']['base'], [0, 0, 0])

    def test_additional_obstacle_gets_explicit_physical_dimensions(self):
        value = station()
        value['nodes'].append({'id': 'obs', 'kind': 'obstacle', 'parent': 'world', 'position': [.4, 0, .065]})
        obstacle = validate_station(value)['additional_obstacles'][0]
        self.assertEqual(obstacle['position_m'], [.4, 0, .065])
        self.assertEqual(obstacle['half_size_m'], [.025, .028, .065])

    def test_changed_release_target_is_rejected(self):
        value = station()
        next(n for n in value['nodes'] if n['id'] == 'release')['position'][0] += .001
        with self.assertRaisesRegex(UnsupportedStation, 'release'):
            validate_station(value)

    def test_program_reorder_or_duration_edit_is_rejected(self):
        for mutation in ('order', 'duration'):
            value = station()
            if mutation == 'order':
                value['program'][0], value['program'][1] = value['program'][1], value['program'][0]
            else:
                value['program'][0]['seconds'] = 2
            with self.assertRaises(UnsupportedStation):
                validate_station(value)

    def test_missing_parent_cycle_and_nonfinite_rejected(self):
        for parent, xyz in [('missing', [0, 0, .01]), ('cube', [0, 0, .01]), ('pick', [float('nan'), 0, .01])]:
            value = station()
            value['nodes'][-1].update(parent=parent, position=xyz)
            with self.assertRaises(UnsupportedStation):
                validate_station(value)

    def test_unknown_object_and_cube_outside_region_are_not_ignored(self):
        value = station()
        value['nodes'].append({'id': 'second-cube', 'kind': 'object', 'parent': 'world', 'position': [.2, 0, .01]})
        with self.assertRaisesRegex(UnsupportedStation, 'second-cube'):
            validate_station(value)
        value = station()
        value['nodes'][-1]['position'][0] = .011
        with self.assertRaisesRegex(UnsupportedStation, 'cube'):
            validate_station(value)

    def test_preexisting_cancel_writes_terminal_status_without_importing_physics(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cancel = root/'cancel.request'
            cancel.touch()
            self.assertEqual(run(root/'missing.json', root, cancel), 0)
            self.assertEqual(json.loads((root/'status.json').read_text())['status'], 'cancelled')

    def test_validation_failure_writes_unsupported_reasons(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/'request.json'
            value = station()
            value['program'] = []
            source.write_text(json.dumps({'station': value}))
            self.assertEqual(run(source, root, None), 1)
            status = json.loads((root/'status.json').read_text())
            self.assertEqual(status['status'], 'failed')
            self.assertTrue(status['unsupported'])


if __name__ == '__main__':
    unittest.main()
