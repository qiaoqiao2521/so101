"""Station admission must preserve editable intent and avoid silent substitutions."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from route_policy import RoutePolicy
from station_executor import (FIXED_NODES, SEGMENTS, TEMPLATE, UnsupportedStation,
                              WORKSPACE_DEVELOPMENT_MODE, WORKSPACE_TARGET_REGION,
                              atomic_json, compile_program, describe, run, validate_station)


def station():
    return {'name': 'test', 'notes': '',
            'nodes': [{'id': key, 'kind': kind, 'parent': 'world', 'position': xyz.copy()}
                      for key, (kind, xyz) in FIXED_NODES.items()]+
                     [{'id': 'cube', 'kind': 'object', 'parent': 'pick', 'position': [0, 0, .01]}],
            'program': [{'id': str(i), 'action': action, 'target': target, 'seconds': 1}
                        for i, (action, target) in enumerate(TEMPLATE)]}


def workspace_station(side):
    value = station()
    cube_x, pick_x, hover, place_xy = ((.26, .26, .054, [.24, .14]) if side == 'right'
                                      else (.22, .235, .06, [.20, .20]))
    value['execution'] = {'mode': WORKSPACE_DEVELOPMENT_MODE, 'pick_xy_m': [pick_x, -.13],
                          'pickup_hover_z_m': hover,
                          'target_region_xy_m': copy.deepcopy(WORKSPACE_TARGET_REGION)}
    for node in value['nodes']:
        if node['id'] == 'pick':
            node['position'] = [pick_x, -.13, 0.]
        elif node['id'] == 'cube':
            node.update(parent='world', position=[cube_x, -.13, .01])
        elif node['id'] in ('approach', 'grasp'):
            node['position'] = [cube_x, -.13, hover+.02 if node['id'] == 'approach' else .02]
        elif node['id'] in ('place', 'release', 'clear'):
            node['position'][:2] = place_xy
    return value


def fixed_tray_workspace_station(cube_x, *, pickup_hover_z_m=.06, **options):
    value = workspace_station('right')
    value['execution'].update(pick_xy_m=[.24, -.13],
                              pickup_hover_z_m=pickup_hover_z_m, **options)
    for node in value['nodes']:
        if node['id'] == 'pick':
            node['position'] = [.24, -.13, 0.]
        elif node['id'] == 'cube':
            node['position'] = [cube_x, -.13, .01]
        elif node['id'] in ('approach', 'grasp'):
            node['position'] = [cube_x, -.13, pickup_hover_z_m+.02 if node['id'] == 'approach' else .02]
    return value


class AdmissionTests(unittest.TestCase):
    def test_carry_control_is_explicit_and_unsupported_modes_are_not_silently_automatic(self):
        self.assertNotIn('skill_control', validate_station(station()))
        value = station()
        value['skillControl'] = {'mode': 'hold-before-carry'}
        self.assertEqual(validate_station(value)['skill_control'], value['skillControl'])
        self.assertFalse(describe()['skill_control_modes']['hold-before-carry']['default'])
        self.assertTrue(describe()['skill_control_modes']['hold-before-carry']['original_deadlines_unchanged'])
        for declaration in (None, {}, 'hold-before-carry', {'mode': 'automatic'}, []):
            value['skillControl'] = declaration
            with self.subTest(declaration=declaration), self.assertRaisesRegex(UnsupportedStation, 'skillControl'):
                validate_station(value)

    def test_workspace_execution_is_explicit_and_keeps_default_admission(self):
        default = validate_station(station())
        for key in ('execution', 'development_only', 'not_admitted'):
            self.assertNotIn(key, default)
        value = station()
        value['nodes'][-1].update(parent='world', position=[.26, -.13, .01])
        with self.assertRaisesRegex(UnsupportedStation, 'cube'):
            validate_station(value)
        modes = describe()['execution_modes']
        self.assertEqual(modes['default']['declaration'], 'omit execution')
        self.assertTrue(modes[WORKSPACE_DEVELOPMENT_MODE]['not_admitted'])

    def test_both_workspace_x_examples_preserve_development_only_semantics(self):
        for side, cube_x, pick_x, hover, place_xy in (
                ('right', .26, .26, .054, [.24, .14]),
                ('left', .22, .235, .06, [.20, .20])):
            value = workspace_station(side)
            with self.subTest(side=side):
                result = validate_station(value)
                self.assertTrue(result['development_only'])
                self.assertTrue(result['not_admitted'])
                self.assertEqual(result['cube_xyz_m'], [cube_x, -.13, .01])
                self.assertEqual(result['execution']['pick_xy_m'], [pick_x, -.13])
                self.assertEqual(result['place_xy_m'], place_xy)
                self.assertEqual(result['resolved_positions_m']['approach'], [cube_x, -.13, hover+.02])
                self.assertEqual(result['resolved_positions_m']['grasp'], [cube_x, -.13, .02])
                value['execution']['pick_xy_m'][0] = 99
                self.assertEqual(result['execution']['pick_xy_m'], [pick_x, -.13])

    def test_fixed_tray_requests_keep_cube_separate_and_optional_defaults_absent(self):
        for cube_x in (.229, .251, .22, .26):
            value = fixed_tray_workspace_station(cube_x)
            with self.subTest(cube_x=cube_x):
                result = validate_station(value)
                self.assertEqual(result['resolved_positions_m']['pick'], [.24, -.13, 0.])
                self.assertEqual(result['cube_xyz_m'], [cube_x, -.13, .01])
                self.assertEqual(result['resolved_positions_m']['approach'], [cube_x, -.13, .08])
                self.assertNotIn('pickup_open_jaw_rad', result['execution'])
                self.assertNotIn('mesh_box_axis_refinement', result['execution'])
                self.assertTrue(result['not_admitted'])

    def test_linked_fixed_tray_examples_preserve_original_resolved_intent(self):
        fixtures = Path(__file__).parent/'scenarios/workspace-station'
        for side, source in (('left', 'fixed-x-minus15p5.json'),
                             ('right', 'fixed-x-plus15p5.json')):
            with self.subTest(side=side):
                original = json.loads((fixtures/source).read_text())
                linked = json.loads((fixtures/f'fixed-tray-linked-{side}.json').read_text())
                before = validate_station(original['station'])
                after = validate_station(linked['station'])
                for ident, position in before['resolved_positions_m'].items():
                    self.assertEqual(after['resolved_positions_m'][ident], position)
                self.assertEqual(linked['station']['execution'], original['station']['execution'])
                self.assertEqual(linked['station']['program'], original['station']['program'])
                self.assertTrue(after['development_only'])
                self.assertTrue(after['not_admitted'])
                self.assertEqual(linked['editingExample']['source'], source)

    def test_linked_fixed_tray_frame_edit_moves_targets_without_moving_tray(self):
        fixtures = Path(__file__).parent/'scenarios/workspace-station'
        for side, x in (('left', .224), ('right', .256)):
            with self.subTest(side=side):
                value = json.loads((fixtures/f'fixed-tray-linked-{side}.json').read_text())['station']
                next(node for node in value['nodes']
                     if node['id'] == 'pickup_request')['position'][0] = x
                result = validate_station(value)
                for ident in ('cube', 'approach', 'grasp'):
                    self.assertEqual(result['resolved_positions_m'][ident][0], x)
                self.assertEqual(result['resolved_positions_m']['pick'], [.24, -.13, 0.])
                self.assertEqual(result['execution']['pick_xy_m'], [.24, -.13])

    def test_linked_fixed_tray_json_roundtrip_keeps_optional_metadata(self):
        fixtures = Path(__file__).parent/'scenarios/workspace-station'
        for side in ('left', 'right'):
            with self.subTest(side=side), tempfile.TemporaryDirectory() as temporary:
                document = json.loads((fixtures/f'fixed-tray-linked-{side}.json').read_text())
                document['station']['execution']['editor_note'] = {'label': '本地二改', 'force': 999}
                destination = Path(temporary)/'station.json'
                atomic_json(destination, document)
                restored = json.loads(destination.read_text())
                self.assertEqual(restored, document)
                with self.assertWarnsRegex(RuntimeWarning, 'editor_note.*不参与执行'):
                    result = validate_station(restored['station'])
                self.assertEqual(result['execution']['editor_note'], {'label': '本地二改', 'force': 999})
                self.assertEqual(result['execution']['pickup_hover_z_m'],
                                 document['station']['execution']['pickup_hover_z_m'])

    def test_linked_fixed_tray_examples_keep_inconsistency_and_region_rejections(self):
        fixtures = Path(__file__).parent/'scenarios/workspace-station'
        for side in ('left', 'right'):
            for invalid in ('target_offset', 'outside_region'):
                with self.subTest(side=side, invalid=invalid):
                    value = json.loads((fixtures/f'fixed-tray-linked-{side}.json').read_text())['station']
                    if invalid == 'target_offset':
                        next(node for node in value['nodes']
                             if node['id'] == 'grasp')['position'][0] = .001
                        error = 'grasp'
                    else:
                        next(node for node in value['nodes']
                             if node['id'] == 'pickup_request')['position'][0] = .271
                        error = 'cube.*视觉先验'
                    with self.assertRaisesRegex(UnsupportedStation, error):
                        validate_station(value)

    def test_workspace_rejects_node_inconsistency_and_out_of_prior_cube(self):
        for ident, coordinate, delta in (('pick', 0, .001), ('approach', 0, .001),
                                         ('approach', 2, .001), ('grasp', 1, .001),
                                         ('grasp', 2, .001), ('base', 0, .001),
                                         ('jaw', 0, .001), ('release', 2, .001),
                                         ('clear', 2, .001), ('cube', 2, .001),
                                         ('cube', 0, .011)):
            value = workspace_station('right')
            next(node for node in value['nodes'] if node['id'] == ident)['position'][coordinate] += delta
            with self.subTest(ident=ident, coordinate=coordinate), self.assertRaisesRegex(UnsupportedStation, ident):
                validate_station(value)

    def test_workspace_rejects_null_bad_modes_bad_values_and_changed_prior(self):
        bad = [None, {}, {'mode': 'unknown'}]
        for field, invalid_values in (
                ('pick_xy_m', ([True, -.13], [.26], [float('nan'), -.13], ['.26', -.13])),
                ('pickup_hover_z_m', (True, None, '.054', float('inf'), .053999, .060001)),
                ('pickup_open_jaw_rad', (True, None, '.35', float('nan'), float('inf'), .349, .501)),
                ('mesh_box_axis_refinement', (None, 0, 1, 'true', [], {})),
                ('target_region_xy_m', (None, [[.20, .27], [-.16, -.10]],
                                       [[True, .27], [-.16, -.10]]))):
            for invalid in invalid_values:
                execution = workspace_station('right')['execution']
                execution[field] = invalid
                bad.append(execution)
        for execution in bad:
            value = workspace_station('right')
            value['execution'] = execution
            with self.subTest(execution=execution), self.assertRaisesRegex(UnsupportedStation, 'execution'):
                validate_station(value)

    def test_workspace_optional_metadata_warns_and_round_trips_without_becoming_parameters(self):
        value = workspace_station('right')
        value['execution']['editor_note'] = {'label': '我改过的工位', 'gripper_force': 999}
        with self.assertWarnsRegex(RuntimeWarning, 'editor_note.*不参与执行，原阈值不变'):
            result = validate_station(value)
        restored = json.loads(json.dumps(result, ensure_ascii=False))
        self.assertEqual(restored['execution']['editor_note'], value['execution']['editor_note'])
        self.assertEqual(restored['execution']['pickup_hover_z_m'], .054)
        self.assertTrue(restored['development_only'])
        self.assertTrue(restored['not_admitted'])
        value['execution']['editor_note']['gripper_force'] = 0
        self.assertEqual(result['execution']['editor_note']['gripper_force'], 999)

    def test_workspace_run_forwards_declaration_and_keeps_original_judge_limits(self):
        cancel_error = '用户停止了当前仿真'
        outcomes = (
            ('original_failure', {'passed': False, 'failure_reason': 'mock_only'}, False, 1, 'failed'),
            ('late_cancel_original_failure', {'passed': False, 'failure_reason': 'original_collision'}, True, 1, 'failed'),
            ('late_cancel_success', {'passed': True, 'failure_reason': None}, True, 0, 'succeeded'),
            ('cancel_cleanup_failure', {'passed': False, 'error_type': 'Cancelled', 'error': cancel_error,
                'failure_reason': cancel_error, 'planner_cleanup_error': 'join failed',
                'planner_cleanup_errors': [{'planner': 'return', 'error': 'join failed'}]}, True, 1, 'failed'),
            ('actual_cancel', {'passed': False, 'error_type': 'Cancelled', 'error': cancel_error,
                'failure_reason': cancel_error}, True, 0, 'cancelled'),
            ('cancel_with_original_cause', {'passed': False, 'error_type': 'Cancelled', 'error': cancel_error,
                'failure_reason': 'original_collision'}, True, 1, 'failed'),
            ('cancel_with_safety_stop', {'passed': False, 'error_type': 'Cancelled', 'error': cancel_error,
                'failure_reason': cancel_error, 'safety_stop': True}, True, 1, 'failed'),
        )
        cases = [(side, station() if side is None else workspace_station(side), outcomes[0], False)
                 for side in (None, 'right', 'left')]
        cases.extend((None, station(), outcome, False) for outcome in outcomes[1:])
        cases.extend((None, station(), outcome, True) for outcome in outcomes)
        cases.extend((name, value, outcomes[0], False) for name, value in (
            ('fixed_minus11', fixed_tray_workspace_station(.229)),
            ('fixed_plus11', fixed_tray_workspace_station(.251)),
            ('fixed_minus20', fixed_tray_workspace_station(.22, mesh_box_axis_refinement=True)),
            ('fixed_plus20', fixed_tray_workspace_station(.26, pickup_hover_z_m=.054,
                                                        pickup_open_jaw_rad=.35)),
            ('explicit_original', fixed_tray_workspace_station(.26, pickup_open_jaw_rad=.5,
                                                               mesh_box_axis_refinement=False)),
        ))
        for side, value, (label, report, request_cancel, expected_code, expected_state), carry in cases:
            if carry:
                value['skillControl'] = {'mode': 'hold-before-carry'}
                report = dict(report, simulation_s=20.)
            seen = {}

            def build_contact(source, folder, **kwargs):
                seen['builder'] = kwargs
                folder.mkdir(parents=True, exist_ok=True)
                for name in ('contact-workcell.xml', 'grasp-planning.xml'):
                    (folder/name).write_text('<mujoco><worldbody/></mujoco>')
                return object(), object(), folder/'contact-workcell.xml'

            def physical(source, output, budget, case, candidate, **kwargs):
                seen.update(budget=budget, case=case, controller=kwargs['controller_options'])
                kwargs['scene_builder'](source, output/'scene')
                kwargs['evidence_callback']({'schema': 'so101.physical-skill-evidence.v1',
                    'scope': 'observation_only', 'grasp': {'postcondition_met': True}})
                if carry:
                    gate = kwargs['controller_options']['transport_gate']
                    seen['carry_gate'] = gate
                    self.assertFalse(gate([0.]*6, 10.))
                    if not request_cancel:
                        (root/'carry-resume.request').touch()
                        self.assertTrue(gate([0.]*6, 11.))
                if request_cancel:
                    cancel.touch()
                return report

            names = ('quad_vertices', 'small_direction_cache', 'tree_leaf8', 'leaf_packed',
                     'packed_inline', 'seed_bound_direct', 'summary_fast')
            native = SimpleNamespace(**{'configure_'+name: lambda value: None for name in names})
            policy = RoutePolicy(mesh_box_axis_refinement=True)
            modules = {'support_native': native,
                       'grasp_episode': SimpleNamespace(build_contact_scene=build_contact,
                                                       numbers=lambda values: ' '.join(map(str, values))),
                       'run_visual_grasp': SimpleNamespace(SOURCE=Path('/unused-source.xml'),
                                                          run_physical_episode=physical),
                       'mujoco': SimpleNamespace(MjModel=SimpleNamespace(from_xml_path=lambda path: object()))}
            with self.subTest(side=side, outcome=label, carry=carry), tempfile.TemporaryDirectory() as folder, \
                    patch.dict(sys.modules, modules):
                root = Path(folder)
                cancel = root/'cancel.request'
                source = root/'request.json'
                source.write_text(json.dumps({'station': value}))
                (root/'status.json').write_text(json.dumps({'status': 'succeeded', 'report': {'passed': True}}))
                self.assertEqual(run(source, root, cancel, route_policy=policy), expected_code)
                status = json.loads((root/'status.json').read_text())
                self.assertEqual(status['status'], expected_state)
                self.assertEqual(status['report'], report)
                self.assertEqual(status['skill_evidence']['attempt_id'], root.name)
                self.assertTrue(status['skill_evidence']['grasp']['postcondition_met'])
                self.assertEqual(status['cancel_requested'], request_cancel)
                self.assertEqual(status['cancelled'], expected_state == 'cancelled')
                self.assertEqual(seen['budget'], {'max_episode_wall_s': 120, 'max_sim_s': 90})
                self.assertEqual(seen['case']['initial_xy_m'], validate_station(value)['cube_xyz_m'][:2])
                execution = value.get('execution', {})
                if 'mesh_box_axis_refinement' in execution:
                    self.assertEqual(seen['controller']['route_policy'],
                                     replace(policy, mesh_box_axis_refinement=execution['mesh_box_axis_refinement']))
                    self.assertIsNot(seen['controller']['route_policy'], policy)
                else:
                    self.assertIs(seen['controller']['route_policy'], policy)
                self.assertTrue(policy.mesh_box_axis_refinement)
                if 'pickup_open_jaw_rad' in execution:
                    self.assertEqual(seen['controller']['pickup_open_jaw_rad'], execution['pickup_open_jaw_rad'])
                else:
                    self.assertNotIn('pickup_open_jaw_rad', seen['controller'])
                if carry:
                    snapshot = status['carry_gate']
                    self.assertEqual(snapshot['state'], 'ended')
                    self.assertEqual(snapshot['attempt_id'], root.name)
                    self.assertEqual(snapshot['attempt']['passed'], report['passed'])
                    self.assertEqual(snapshot['attempt']['failure_reason'], report['failure_reason'])
                    self.assertEqual(snapshot['attempt']['planner_cleanup_errors'],
                                     report.get('planner_cleanup_errors'))
                    self.assertEqual(snapshot['attempt']['error_type'], report.get('error_type'))
                    self.assertEqual(snapshot['resume_file'], str(root/'carry-resume.request'))
                    self.assertEqual(snapshot['released_at_s'], None if request_cancel else 11.)
                    self.assertEqual(seen['carry_gate'].report()['state'], 'ended')
                else:
                    self.assertNotIn('transport_gate', seen['controller'])
                    self.assertNotIn('carry_gate', status)
                if side is None:
                    self.assertNotIn('pick_xy', seen['builder'])
                    self.assertNotIn('pickup_hover_z_m', seen['controller'])
                    self.assertNotIn('target_region_xy_m', seen['controller'])
                    self.assertNotIn('development_only', status)
                else:
                    execution = value['execution']
                    self.assertEqual(seen['builder']['pick_xy'], execution['pick_xy_m'])
                    self.assertEqual(seen['controller']['pickup_hover_z_m'], execution['pickup_hover_z_m'])
                    self.assertEqual(seen['controller']['target_region_xy_m'], execution['target_region_xy_m'])
                    self.assertEqual(status['execution'], execution)
                    self.assertTrue(status['development_only'])
                    self.assertTrue(status['not_admitted'])
                    self.assertTrue(status['layout']['not_admitted'])

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

    def test_place_height_follows_parent_and_keeps_relative_release_clear(self):
        value = station()
        for node in value['nodes']:
            if node['id'] == 'place':
                node['position'][2] = .010
            elif node['id'] in ('release', 'clear'):
                node['parent'] = 'place'
                node['position'][:2] = [0, 0]
        result = validate_station(value)
        self.assertEqual(result['place_height_m'], .010)
        self.assertEqual(result['resolved_positions_m']['release'], [.24, .14, .040])
        self.assertEqual(result['resolved_positions_m']['clear'], [.24, .14, .110])
        self.assertEqual(result['cube_xyz_m'], [.24, -.13, .010])

    def test_place_height_rejects_negative_and_unshifted_release_targets(self):
        for height in (-.010, .010):
            value = station()
            next(node for node in value['nodes'] if node['id'] == 'place')['position'][2] = height
            with self.subTest(height=height), self.assertRaisesRegex(UnsupportedStation, 'place|release'):
                validate_station(value)

    def test_nondefault_goal_does_not_need_python_coordinate_whitelist(self):
        value = station()
        for node in value['nodes']:
            if node['id'] in ('place', 'release', 'clear'):
                node['position'][:2] = [.38, .21]
        self.assertEqual(validate_station(value)['place_xy_m'], [.38, .21])

    def test_default_and_changed_cube_are_resolved(self):
        value = station()
        self.assertEqual(validate_station(value)['place_height_m'], 0.)
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

    def test_capability_segments_expand_to_reusable_atomic_plan(self):
        value = station()
        value['program'] = [
            {'id': 's1', 'capability': 'pick', 'seconds': 1},
            {'id': 's2', 'capability': 'transfer', 'seconds': 1},
            {'id': 's3', 'capability': 'place', 'seconds': 1},
        ]
        result = validate_station(value)
        self.assertEqual(result['program']['mode'], 'segments')
        self.assertEqual(tuple(result['program']['segments']), ('pick', 'transfer', 'place'))
        self.assertEqual(result['program']['steps'], TEMPLATE)
        self.assertEqual(tuple(SEGMENTS), ('pick', 'transfer', 'place'))

    def test_capability_plan_rejects_missing_duplicate_or_unknown_segments(self):
        for program, message in (
                ([], '八步完整抓放模板或 pick'),
                ([{'capability': 'pick', 'seconds': 1},
                  {'capability': 'pick', 'seconds': 1}], '要求能力段'),
                ([{'capability': 'pick', 'seconds': 1},
                  {'capability': 'transport', 'seconds': 1},
                  {'capability': 'place', 'seconds': 1}],
                 '不受支持')):
            with self.subTest(program=program), self.assertRaisesRegex(UnsupportedStation, message):
                compile_program(program)

    def test_capability_segment_ids_may_be_edited_without_changing_intent(self):
        program = [{'id': 'my-pick', 'capability': 'pick', 'seconds': 1},
                   {'id': 'custom', 'capability': 'transfer', 'seconds': 1},
                   {'id': 'my-place', 'capability': 'place', 'seconds': 1}]
        self.assertEqual(compile_program(program)['steps'], TEMPLATE)
        program[1].pop('id')
        self.assertEqual(compile_program(program)['steps'], TEMPLATE)

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
            status = json.loads((root/'status.json').read_text())
            self.assertEqual(status['status'], 'cancelled')
            self.assertTrue(status['cancel_requested'])
            self.assertTrue(status['cancelled'])

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
