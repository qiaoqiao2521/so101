"""Expose original MuJoCo visual geometry as a Foxglove SceneUpdate.

Preview runs forward kinematics only. Execution snapshots use the live MjData;
neither path integrates physics, attaches the payload, or approximates link FK.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import time
import warnings
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

SOURCE = Path(__file__).resolve().parents[2] / 'workspaces/so101_ws/src/so101_mujoco/models/so101.xml'
MESH_URL = '/api/so101/meshes/'


def vector(value):
    return dict(zip(('x', 'y', 'z'), map(float, value)))


def pose(position, rotation):
    quat = np.empty(4)
    mujoco.mju_mat2Quat(quat, np.asarray(rotation, dtype=float).reshape(9))
    return {'position': vector(position),
            'orientation': dict(zip(('w', 'x', 'y', 'z'), map(float, quat)))}


def mesh_manifest(source=SOURCE):
    source = Path(source)
    root = ET.parse(source).getroot()
    directory = (source.parent / root.find('compiler').get('meshdir', '.')).resolve()
    meshes = []
    for item in root.findall('./asset/mesh'):
        filename = Path(item.get('file')).name
        meshes.append({'name': item.get('name', Path(filename).stem), 'file': filename,
                       'url': MESH_URL + filename})
    return {'mesh_directory': str(directory), 'meshes': meshes}


class StationScene:
    def __init__(self, model, *, source=SOURCE):
        self.model = model
        self.meshes = {item['name']: item for item in mesh_manifest(source)['meshes']}
        self.visible = [i for i in range(model.ngeom)
                        if model.geom_group[i] != 3 and model.geom_rgba[i, 3] > 0]

    def update(self, data, *, elapsed_s=None, phase='preview', extra_boxes=(), markers=()):
        model = self.model
        now = time.time_ns()
        entity = {'timestamp': {'sec': now // 1_000_000_000, 'nsec': now % 1_000_000_000},
                  'frame_id': 'world', 'id': 'so101-workcell',
                  'lifetime': {'sec': 0, 'nsec': 0}, 'frame_locked': False,
                  'metadata': [{'key': 'source', 'value': 'MuJoCo live geometry'},
                               {'key': 'phase', 'value': phase},
                               {'key': 'simulation_s', 'value': str(float(data.time) if elapsed_s is None else elapsed_s)}],
                  'arrows': [], 'cubes': [], 'spheres': [], 'cylinders': [], 'lines': [],
                  'triangles': [], 'texts': [], 'models': []}
        for index in self.visible:
            position = data.geom_xpos[index].copy()
            rotation = data.geom_xmat[index].reshape(3, 3).copy()
            material = int(model.geom_matid[index])
            rgba = model.mat_rgba[material] if material >= 0 else model.geom_rgba[index]
            color = dict(zip(('r', 'g', 'b', 'a'), map(float, rgba)))
            kind = int(model.geom_type[index])
            size = model.geom_size[index]
            if kind == mujoco.mjtGeom.mjGEOM_MESH:
                mesh_id = int(model.geom_dataid[index])
                info = self.meshes.get(model.mesh(mesh_id).name)
                if info is None:
                    continue
                alignment = np.empty(9)
                mujoco.mju_quat2Mat(alignment, model.mesh_quat[mesh_id])
                # MuJoCo re-centres/rotates imported meshes. The URL serves the
                # original STL, so undo that asset transform exactly once.
                rotation = rotation @ alignment.reshape(3, 3).T
                position -= rotation @ model.mesh_pos[mesh_id]
                entity['models'].append({'pose': pose(position, rotation),
                    'scale': vector(model.mesh_scale[mesh_id]), 'color': color,
                    'override_color': True, 'url': info['url'], 'media_type': 'model/stl',
                    'data': ''})
            elif kind in (int(mujoco.mjtGeom.mjGEOM_BOX), int(mujoco.mjtGeom.mjGEOM_PLANE)):
                full_size = size * 2
                if kind == mujoco.mjtGeom.mjGEOM_PLANE:
                    full_size = np.array([max(.1, full_size[0]), max(.1, full_size[1]), .002])
                    position[2] -= .001
                entity['cubes'].append({'pose': pose(position, rotation),
                                        'size': vector(full_size), 'color': color})
            elif kind == mujoco.mjtGeom.mjGEOM_CYLINDER:
                entity['cylinders'].append({'pose': pose(position, rotation),
                    'size': vector([size[0]*2, size[0]*2, size[1]*2]),
                    'bottom_scale': 1., 'top_scale': 1., 'color': color})
            elif kind == mujoco.mjtGeom.mjGEOM_SPHERE:
                entity['spheres'].append({'pose': pose(position, rotation),
                                          'size': vector([size[0]*2]*3), 'color': color})
        for box in extra_boxes:
            entity['cubes'].append({'pose': pose(box['position_m'], np.eye(3)),
                'size': vector(np.asarray(box['half_size_m'])*2),
                'color': {'r': .65, 'g': .34, 'b': .16, 'a': 1.}})
        for xyz in markers:
            entity['spheres'].append({'pose': pose(xyz, np.eye(3)),
                'size': vector([.008]*3), 'color': {'r': .12, 'g': .66, 'b': .95, 'a': .7}})
        return {'deletions': [], 'entities': [entity]}


def preview_positions(station):
    """Resolve editable translated frames, skipping only malformed nodes."""
    nodes = {item['id']: item for item in station.get('nodes', [])
             if isinstance(item, dict) and isinstance(item.get('id'), str)}
    result = {'world': np.zeros(3)}

    def resolve(ident, seen=()):
        if ident in result:
            return result[ident]
        if ident in seen or ident not in nodes:
            raise ValueError('missing or cyclic parent: ' + ident)
        item = nodes[ident]
        value = np.asarray(item.get('position'), dtype=float)
        if value.shape != (3,) or not np.isfinite(value).all():
            raise ValueError('invalid position: ' + ident)
        result[ident] = resolve(item.get('parent', 'world'), (*seen, ident)) + value
        return result[ident]

    for ident in nodes:
        try:
            resolve(ident)
        except (ValueError, TypeError) as error:
            warnings.warn('WARNING preview skipped ' + str(error))
    return nodes, result


def preview(station=None, *, source=SOURCE):
    from grasp_episode import build_contact_scene, solve_pinch_ik
    station = {} if station is None else station
    nodes, positions = preview_positions(station)
    if 'place' in nodes and 'place' not in positions:
        raise ValueError('Cannot preview an invalid place frame')
    place = positions.get('place', np.array([.24, .14, 0.]))
    with tempfile.TemporaryDirectory(prefix='so101-scene-') as folder:
        model, rig, _ = build_contact_scene(Path(source), Path(folder), noslip_iterations=10,
                                           place_xy=place[:2].tolist(), place_height_m=float(place[2]))
        data = mujoco.MjData(model)
        data.qpos[:6] = np.r_[solve_pinch_ik(rig, np.array([.24, .14, .06])), .5]
        data.qpos[6:9] = positions.get('cube', [.24, -.13, .01])
        data.ctrl[:] = data.qpos[:6]
        if 'base' in positions:
            model.body_pos[model.body('base').id] = positions['base']
        for prefix, original in [('pick', [.24, -.13, 0.])]:
            if prefix in positions:
                shift = positions[prefix] - original
                for index in range(model.ngeom):
                    if model.geom(index).name.startswith(prefix + '_'):
                        model.geom_pos[index] += shift
        mujoco.mj_forward(model, data)
        boxes = [{'position_m': positions[ident], 'half_size_m': [.025, .028, .065]}
                 for ident, item in nodes.items()
                 if item.get('kind') == 'obstacle' and ident in positions]
        markers = [positions[ident] for ident, item in nodes.items()
                   if item.get('kind') == 'target' and ident in positions]
        return StationScene(model, source=source).update(data, elapsed_s=0.,
                     phase='preview', extra_boxes=boxes, markers=markers)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-json', action='store_true')
    parser.add_argument('--preview', type=Path)
    args = parser.parse_args()
    station = json.loads(args.preview.read_text()) if args.preview else None
    if isinstance(station, dict) and 'station' in station:
        station = station['station']
    scene = preview(station)
    result = dict(mesh_manifest(), scene=scene) if args.model_json else scene
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
