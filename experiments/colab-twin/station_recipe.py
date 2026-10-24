"""Document-only recipe admission; motion remains with the original Station."""
from __future__ import annotations

import warnings


TRANSFORM_FIELDS = ('rotation', 'quaternion', 'orientation', 'rpy', 'transform', 'matrix')
RECIPE_FIELDS = {'format', 'version', 'units', 'frameConvention', 'executionScope',
                 'compatibility', 'recipe', 'station', 'skills', 'observation',
                 'provenance', 'acceptanceReferences'}


def station_from_document(document):
    """Keep legacy inputs; reject unsupported recipe semantics before loading models."""
    if not isinstance(document, dict):
        return document
    if document.get('format') != 'station-recipe':
        return document.get('station', document)
    expected = {'version': 1, 'units': 'm', 'frameConvention': 'translation-only',
                'executionScope': 'independent_episode'}
    for key, value in expected.items():
        if type(document.get(key)) is not type(value) or document[key] != value:
            raise ValueError(f'配方 {key} 不受支持；当前仅支持 {value}')
    compatibility = document.get('compatibility')
    for key, value in {'platform': 'so101', 'executor': 'so101-mujoco-visual-grasp',
                       'stationVersion': 1}.items():
        if (not isinstance(compatibility, dict) or type(compatibility.get(key)) is not type(value)
                or compatibility[key] != value):
            raise ValueError(f'配方 compatibility.{key} 不受支持；当前仅支持 {value}')
    identity = document.get('recipe')
    for key in ('id', 'name', 'revision'):
        if (not isinstance(identity, dict) or not isinstance(identity.get(key), str)
                or not identity[key].strip()):
            raise ValueError(f'配方 recipe.{key} 需要可编辑的非空字符串')
    if document.get('skills') != ['pick', 'transfer', 'place']:
        raise ValueError('配方 skills 仅支持 pick → transfer → place；由原 station.program 执行')
    station = document.get('station')
    if not isinstance(station, dict):
        raise ValueError('配方需要原 Station 对象')
    if station.get('platform', 'so101') != 'so101':
        raise ValueError('配方 station.platform 仅支持 so101')
    geometry = [('station', station)]
    if isinstance(station.get('nodes'), list):
        geometry.extend((f'station.nodes[{i}]', node) for i, node in enumerate(station['nodes'])
                        if isinstance(node, dict))
    for name, node in geometry:
        if name != 'station':
            for field in ('size', 'motion', 'enabled'):
                if field in node:
                    raise ValueError(f'配方 {name}.{field} 不受支持；SO101仅支持原固定尺寸静态几何')
        for field in TRANSFORM_FIELDS:
            if field in node:
                raise ValueError(f'配方 {name}.{field} 不受支持；当前仅支持米制平移')
    unknown = sorted(set(document)-RECIPE_FIELDS)
    if unknown:
        warnings.warn('配方附加字段仅作元数据，不参与执行：'+', '.join(unknown))
    if 'acceptanceReferences' in document:
        warnings.warn('历史验收仅作来源引用；本任务仍由原物理裁判重新判定')
    return station
