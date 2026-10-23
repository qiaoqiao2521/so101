"""Complete JSON values and original atomic publication failure semantics."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from route_policy import RoutePolicy, load_route_policy
from station_executor import atomic_json, run
from test_station_executor import station


class CompactStatusJsonTests(unittest.TestCase):
    def test_default_retains_original_human_readable_bytes(self):
        value = {'中文': ['换行\n引号"', -0., 1e-300, True, None], 'nested': {'axis': 6}}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'status.json'
            atomic_json(path, value)
            self.assertEqual(path.read_text(),
                             json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
            self.assertFalse(path.with_suffix('.tmp').exists())

    def test_compact_preserves_all_values_and_signed_zero(self):
        value = {'中文': ['引号"反斜杠\\', -0., 1e-300, 1e300, True, None],
                 'scene': [{'position': [1., 2., 3.], 'visible': False}]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'status.json'
            atomic_json(path, value)
            original = path.read_text()
            atomic_json(path, value, compact=True)
            compact = path.read_text()
            self.assertEqual(json.loads(original), json.loads(compact))
            self.assertEqual(json.loads(compact), value)
            self.assertIn('-0.0', compact)
            self.assertIn('中文', compact)
            self.assertTrue(compact.endswith('\n'))
            self.assertLess(len(compact), len(original))

    def test_invalid_payload_keeps_existing_file_and_original_error_type(self):
        circular = []
        circular.append(circular)
        for payload, error in (({'x': float('nan')}, ValueError),
                               ({'x': float('inf')}, ValueError),
                               (circular, ValueError), ({'x': object()}, TypeError)):
            for selected in (False, True):
                with self.subTest(payload_type=type(payload), selected=selected), \
                        tempfile.TemporaryDirectory() as folder:
                    path = Path(folder)/'status.json'
                    atomic_json(path, {'previous': True})
                    previous = path.read_bytes()
                    with self.assertRaises(error):
                        atomic_json(path, payload, compact=selected)
                    self.assertEqual(path.read_bytes(), previous)

    def test_replace_error_is_not_swallowed_or_reported_as_publication(self):
        for selected in (False, True):
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder)/'status.json'
                atomic_json(path, {'previous': True})
                previous = path.read_bytes()
                error = OSError('original replace failure')
                with patch.object(Path, 'replace', side_effect=error), \
                        self.assertRaises(OSError) as raised:
                    atomic_json(path, {'next': True}, compact=selected)
                self.assertIs(raised.exception, error)
                self.assertEqual(path.read_bytes(), previous)
                self.assertTrue(path.with_suffix('.tmp').exists())

    def test_cancel_and_invalid_scene_publish_same_complete_status(self):
        for cancelled in (True, False):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                source = root/'request.json'
                value = station()
                value['program'] = []
                source.write_text(json.dumps({'station': value}))
                cancel = root/'cancel.request' if cancelled else None
                if cancel is not None:
                    cancel.touch()
                statuses = []
                for selected in (False, True):
                    with patch('station_executor.atomic_json', wraps=atomic_json) as writer:
                        result = run(source, root, cancel,
                                     route_policy=RoutePolicy(compact_status_json=selected))
                    self.assertEqual(result, 0 if cancelled else 1)
                    statuses.append(json.loads((root/'status.json').read_text()))
                    self.assertTrue(all(call.kwargs == ({'compact': True} if selected else {})
                                        for call in writer.call_args_list))
                self.assertEqual(statuses[0], statuses[1])
                self.assertEqual(statuses[1]['status'], 'cancelled' if cancelled else 'failed')

    def test_explicit_candidate_only_selects_serialization_and_default_is_verified(self):
        root = Path(__file__).parent/'route_strategies'
        parent = load_route_policy(root/'direction_hint_single_pass.py')[0]
        child = load_route_policy(root/'compact_status_json.py')[0]
        self.assertFalse(RoutePolicy().compact_status_json)
        self.assertTrue(load_route_policy()[0].compact_status_json)
        self.assertFalse(child.scalar_direction_hints)
        self.assertEqual([key for key, value in child.preferences().items()
                          if parent.preferences()[key] != value], ['compact_status_json'])
        with self.assertRaises(ValueError):
            RoutePolicy(compact_status_json=1)


if __name__ == '__main__':
    unittest.main()
