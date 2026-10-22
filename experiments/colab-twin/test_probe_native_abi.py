"""The observer must own inputs and preserve the actual native result/errors."""
from contextlib import redirect_stderr
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import numpy as np

import support_native as native
from probe_native_abi import NativeObserver


class NativeObserverTests(unittest.TestCase):
    def inputs(self):
        points = np.array([[x, y, z] for x in (-.01, .01)
                           for y in (-.01, .01) for z in (-.01, .01)])
        return [points, points.copy()], np.array([[0., 0., 0.], [.03, 0., 0.]])

    def test_real_native_result_owned_input_and_callable_restoration(self):
        points, positions = self.inputs()
        rotations = np.tile(np.eye(3), (2, 1, 1))
        observer = NativeObserver(sample_cap=2)
        observer.install()
        owner = None
        try:
            observer.local.controller = SimpleNamespace(stage='fixture')
            owner = native.NativeSupport(points, ['box', 'box'])
            result = owner.bind_pairs(np.array([[0, 1]])).summary(positions, rotations, .001)
            self.assertTrue(result['valid'])
            positions[:] = 99.
            points[0][:] = 99.
        finally:
            if owner is not None:
                owner.close()
            observer.uninstall()
        self.assertIs(native._get_library, observer.original_get)
        self.assertIs(native.NativeSupport.__init__, observer.original_init)
        for library, original in observer.libraries.values():
            self.assertIs(library.ns_evaluate_hinted, original)
        with tempfile.TemporaryDirectory() as directory:
            result = observer.save(Path(directory))
            self.assertEqual(result['pools'][0]['samples'], 1)
            arrays = np.load(result['pools'][0]['path'], allow_pickle=False)
            np.testing.assert_array_equal(arrays['positions'][0], [[0., 0., 0.], [.03, 0., 0.]])
            np.testing.assert_array_equal(arrays['hint_in'], -np.ones((1, 2, 3, 2), dtype=np.int64))
            geometry = np.load(next(iter(result['owners'].values()))['path'], allow_pickle=False)
            self.assertLess(np.max(geometry['vertices_0']), 1.)
            self.assertGreater(result['observed_main_native_wall_s'], 0.)

    def test_optional_sampling_failure_cannot_change_result_or_bad_geometry_error(self):
        observer = NativeObserver()
        observer.install()
        owner = None
        try:
            with self.assertRaisesRegex(ValueError, 'nonempty'):
                native.NativeSupport([], [])
            points, positions = self.inputs()
            owner = native.NativeSupport(points, ['box', 'box'])
            observer.local.controller = SimpleNamespace(stage='fixture')

            def unavailable(*args):
                raise RuntimeError('diagnostic failure')

            observer.sample = unavailable
            with redirect_stderr(io.StringIO()) as warnings:
                result = owner.bind_pairs(np.array([[0, 1]])).summary(
                    positions, np.tile(np.eye(3), (2, 1, 1)), .001)
            self.assertTrue(result['valid'])
            self.assertIn('WARNING', warnings.getvalue())
        finally:
            if owner is not None:
                owner.close()
            observer.uninstall()
        self.assertIs(native._get_library, observer.original_get)
        self.assertIs(native.NativeSupport.__init__, observer.original_init)


if __name__ == '__main__':
    unittest.main()
