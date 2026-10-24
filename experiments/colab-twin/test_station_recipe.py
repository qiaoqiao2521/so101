"""Recipe boundary tests; all physical conditions remain with original Station."""
import copy
import json
from pathlib import Path
import unittest
import warnings

from station_executor import validate_station
from station_recipe import station_from_document


class RecipeTests(unittest.TestCase):
    def recipe(self):
        return json.loads((Path(__file__).parent/'scenarios/recipes/station_recipe_v1-x-plus20.json').read_text())

    def test_both_recipes_resolve_to_the_original_station_without_execution_metadata(self):
        for name in ('x-plus20', 'x-minus20'):
            root = Path(__file__).parent/'scenarios'
            document = json.loads((root/'recipes'/f'station_recipe_v1-{name}.json').read_text())
            original = json.loads((root/'workspace-station'/f'{name}.json').read_text())
            original = original.get('station', original)
            saved = copy.deepcopy(document)
            with warnings.catch_warnings(record=True) as observed:
                warnings.simplefilter('always')
                station = station_from_document(document)
            self.assertEqual(document, saved)
            self.assertEqual(station, original)
            self.assertEqual(validate_station(station), validate_station(original))
            self.assertNotIn('acceptanceReferences', station)
            self.assertTrue(any('历史验收' in str(item.message) for item in observed))

    def test_unknown_metadata_warns_without_reinterpreting_or_losing_the_original_payload(self):
        document = self.recipe()
        document['vendorNotes'] = {'freely_editable': [1, 2]}
        with self.assertWarnsRegex(UserWarning, 'vendorNotes'):
            station = station_from_document(document)
        self.assertEqual(station, document['station'])
        self.assertEqual(document['vendorNotes'], {'freely_editable': [1, 2]})

    def test_unsupported_required_semantics_do_not_reach_station_validation(self):
        for key, value in [('version', True), ('version', 2), ('units', 'mm'),
                           ('frameConvention', 'rotation'), ('executionScope', 'continuous_world'),
                           ('skills', ['place', 'pick', 'transfer'])]:
            document = self.recipe()
            document[key] = value
            with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, key):
                station_from_document(document)
        for key, value in [('executor', 'unknown'), ('platform', 'px4'), ('stationVersion', True)]:
            document = self.recipe()
            document['compatibility'][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, key):
                station_from_document(document)

    def test_rotation_dynamic_geometry_and_platform_conflicts_cannot_silently_degrade(self):
        for field in ('rotation', 'quaternion', 'orientation', 'rpy', 'transform', 'matrix',
                      'size', 'motion', 'enabled'):
            document = self.recipe()
            document['station']['nodes'][0][field] = False
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                station_from_document(document)
        document = self.recipe()
        document['station']['platform'] = 'px4'
        with self.assertRaisesRegex(ValueError, 'platform'):
            station_from_document(document)

    def test_legacy_station_and_original_envelope_keep_the_same_payload(self):
        station = self.recipe()['station']
        self.assertIs(station_from_document(station), station)
        self.assertIs(station_from_document({'format': 'robot-station', 'station': station}), station)


if __name__ == '__main__':
    unittest.main()
