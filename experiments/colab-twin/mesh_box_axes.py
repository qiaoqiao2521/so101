"""Extra search directions for an uncertified mesh/box pair.

Directions are suggestions only. NativeSupport reprojects every complete
geometry using the original interval certificate and unchanged margin.
This module does not install a checker, modify geometry, or admit a task.
"""
from __future__ import annotations

import math
import mujoco
import numpy as np
from scipy.spatial import ConvexHull


def _json_value(value):
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return None if isinstance(value, float) and not math.isfinite(value) else value


class MeshBoxAxes:
    def __init__(self, model):
        self.model = model
        self._mesh_axes = {}

    def _local_axes(self, gid):
        mid = int(self.model.geom_dataid[gid])
        if mid not in self._mesh_axes:
            begin = int(self.model.mesh_vertadr[mid])
            count = int(self.model.mesh_vertnum[mid])
            points = np.asarray(self.model.mesh_vert[begin:begin+count], dtype=float)
            hull = ConvexHull(points)
            edges = {tuple(sorted((int(tri[i]), int(tri[j]))))
                     for tri in hull.simplices for i, j in ((0, 1), (1, 2), (2, 0))}
            edge_vectors = np.asarray([points[j]-points[i] for i, j in sorted(edges)])
            self._mesh_axes[mid] = (hull.equations[:, :3].copy(), edge_vectors)
        return self._mesh_axes[mid]

    def directions(self, data, first, second):
        kinds = [int(self.model.geom_type[g]) for g in (first, second)]
        mesh, box = int(mujoco.mjtGeom.mjGEOM_MESH), int(mujoco.mjtGeom.mjGEOM_BOX)
        if sorted(kinds) != sorted((mesh, box)):
            return np.empty((0, 3))
        mesh_gid, box_gid = (first, second) if kinds[0] == mesh else (second, first)
        normals, edges = self._local_axes(mesh_gid)
        mesh_r = data.geom_xmat[mesh_gid].reshape(3, 3)
        box_r = data.geom_xmat[box_gid].reshape(3, 3)
        world_edges = edges @ mesh_r.T
        axes = np.concatenate((normals @ mesh_r.T, box_r.T,
                               np.cross(world_edges[:, None, :], box_r.T[None, :, :])
                               .reshape(-1, 3)))
        lengths = np.linalg.norm(axes, axis=1)
        axes = axes[np.isfinite(lengths) & (lengths > 1e-12)]
        axes = axes / np.linalg.norm(axes, axis=1)[:, None]
        # Dedupe changes search order only. Every retained direction still
        # needs an independent full-geometry interval certificate.
        signs = np.where(axes[np.arange(len(axes)), np.argmax(np.abs(axes), axis=1)] < 0, -1., 1.)
        axes *= signs[:, None]
        _, indices = np.unique(np.round(axes, 10), axis=0, return_index=True)
        return np.ascontiguousarray(axes[np.sort(indices)])

    def inspect(self, checker, q6, *, margin_m=None):
        """Report original and supplemental results; never replace original."""
        margin = checker.margin_m if margin_m is None else margin_m
        evaluate = getattr(checker, '_evaluate_original', checker.evaluate)
        original = evaluate(q6, require_fixed_gripper=False,
                            certificate_margin_m=margin)
        return self.refine(checker, original, margin_m=margin)

    @staticmethod
    def _detail_arrays(details, count, margin):
        """Reject malformed/error ABI rows before considering any new axes."""
        shapes = {'certified': (), 'support_mode': (), 'direction_index': (),
                  'evaluations': (), 'reason': (), 'orientation': (), 'n': (3,),
                  'projection_a': (2,), 'projection_b': (2,), 'gap_lower': (),
                  'norm_squared_upper': (), 'squared_gap_lower': (),
                  'squared_threshold_upper': (), 'lower_bound_m': ()}
        arrays = {key: np.asarray(details[key]) for key in shapes}
        if any(value.shape != (count, *shapes[key]) for key, value in arrays.items()):
            raise ValueError('Native certificate detail shapes do not match pair count')
        if arrays['certified'].dtype.kind != 'b':
            raise ValueError('Native certificate flags must be boolean')
        for key in ('direction_index', 'evaluations', 'orientation'):
            if arrays[key].dtype.kind not in 'iu':
                raise ValueError('Native certificate indices must be integral')
        if np.any(arrays['evaluations'] < 0):
            raise ValueError('Native certificate evaluation counts must be nonnegative')
        for key in ('n', 'projection_a', 'projection_b', 'gap_lower', 'norm_squared_upper',
                    'squared_gap_lower', 'squared_threshold_upper', 'lower_bound_m'):
            if arrays[key].dtype.kind != 'f' or not np.isfinite(arrays[key]).all():
                raise ValueError('Native certificate numeric evidence must be finite')
        certified = arrays['certified']
        expected = np.where(certified, 'separation_certified', 'no_separation_certificate')
        if not np.array_equal(arrays['reason'], expected):
            raise ValueError('Native certificate contains an error or inconsistent reason')
        if (np.any(arrays['lower_bound_m'][certified] < margin)
                or np.any(arrays['norm_squared_upper'][certified] <= 0)
                or np.any(np.all(arrays['n'][certified] == 0, axis=1))
                or np.any(arrays['gap_lower'][certified] <= 0)
                or np.any(arrays['squared_threshold_upper'][certified] <= 0)
                or np.any(arrays['squared_gap_lower'][certified]
                          < arrays['squared_threshold_upper'][certified])
                or np.any(arrays['direction_index'][certified] < 0)
                or np.any(arrays['evaluations'][certified] <= 0)
                or np.any(~np.isin(arrays['orientation'][certified], (-1, 1)))):
            raise ValueError('Native certificate has invalid certified bounds or axes')
        return arrays

    @staticmethod
    def _rejected_pair_details(checker, details, count):
        """Keep diagnostic failure rows even when their numeric proof is absent.

        Native no-certificate rows may contain NaN sentinels. These rows are
        display-only; they never become eligible for supplemental execution.
        """
        certified = np.asarray(details.get('certified'))
        if certified.shape != (count,) or certified.dtype.kind != 'b':
            return []
        rows = []
        for index in np.flatnonzero(~certified):
            first, second = checker.pairs[index]
            row = {'pair_index': int(index), 'pair': [checker._names[first], checker._names[second]],
                   'certified': False, 'original_detail_only': True}
            for key, value in details.items():
                array = np.asarray(value)
                if array.ndim and array.shape[0] == count:
                    row[key] = _json_value(array[index].tolist())
            row['original_lower_bound_m'] = row.get('lower_bound_m')
            rows.append(row)
        return rows

    def refine(self, checker, original_result, *, margin_m=None):
        """Refine an already queried pose; never call checker.evaluate here.

        Only missing mesh/box certificates are eligible. Any error in any
        original or supplemental pair retains the complete original rejection.
        """
        original = original_result
        result = {'original': original, 'supplemental_valid': original['valid'],
                  'pairs': [], 'not_physical': True, 'not_admitted': True,
                  'refined_result': original}
        if (original['valid'] or original.get('reason') != 'uncertified_geometry_clearance'
                or original.get('certificate_reason') != 'no_separation_certificate'):
            return result
        try:
            margin = checker.margin_m if margin_m is None else float(margin_m)
            count = len(checker.pairs)
            if (not math.isfinite(margin) or margin < checker.margin_m
                    or original.get('checked_pairs') != count):
                raise ValueError('Refinement must retain the original margin and all pairs')
            p = checker.data.geom_xpos[checker.geometry_ids].copy()
            rotations = checker.data.geom_xmat[checker.geometry_ids].reshape(-1, 3, 3).copy()
            if not np.isfinite(p).all() or not np.isfinite(rotations).all():
                raise ValueError('Refinement needs a finite original FK frame')
            raw_details = checker.native.evaluate(p, rotations, checker.pair_indices, margin)
            try:
                details = self._detail_arrays(raw_details, count, margin)
            except Exception:
                result['pairs'] = self._rejected_pair_details(checker, raw_details, count)
                raise
            if int(details['certified'].sum()) != original.get('certified_pairs'):
                raise ValueError('Original summary and detailed pair coverage disagree')
            missing = np.flatnonzero(~details['certified'])
            if not len(missing):
                raise ValueError('Original rejected frame has no missing pair certificate')
            bounds = details['lower_bound_m'].copy()
            for index in missing:
                first, second = checker.pairs[index]
                row = {'pair_index': int(index), 'pair': [checker._names[first], checker._names[second]],
                       'original_lower_bound_m': float(bounds[index]), 'certified': False}
                result['pairs'].append(row)
                directions = self.directions(checker.data, first, second)
                row['direction_count'] = len(directions)
                if len(directions):
                    row['queried'] = True
                    detail = self._detail_arrays(checker.native.certify_directions(
                        p, rotations, checker.pair_indices[index], directions, margin), 1, margin)
                    if bool(detail['certified'][0]) and detail['support_mode'][0] != 'full':
                        raise ValueError('Supplemental certificate must project complete vertices')
                    row.update({key: _json_value(np.asarray(value)[0].tolist())
                                for key, value in detail.items()})
                    if row['certified'] is True:
                        bounds[index] = float(detail['lower_bound_m'][0])
            result['supplemental_valid'] = all(row['certified'] is True for row in result['pairs'])
            if result['supplemental_valid']:
                nearest = int(np.argmin(bounds))
                first, second = checker.pairs[nearest]
                result['refined_result'] = dict(
                    original, valid=True, min_distance_m=float(bounds[nearest]),
                    pair_lower_bound_m=float(bounds[nearest]), reason='clear',
                    certificate_reason='separation_certified',
                    pair=[checker._names[first], checker._names[second]],
                    certified_pairs=count, checked_pairs=count)
        except Exception as error:
            result['supplemental_valid'] = False
            result['error'] = str(error)
        return result
