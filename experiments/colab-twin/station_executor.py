"""Run the supported station template with the existing MuJoCo/IK/OMPL executor.

Station JSON remains freely editable. Unsupported physical intent is reported
before simulation rather than being replaced with the historical default scene.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
from pathlib import Path
import time
import warnings
import xml.etree.ElementTree as ET


TEMPLATE = [('open', ''), ('move', 'approach'), ('move', 'grasp'), ('close', ''),
            ('move', 'approach'), ('move', 'release'), ('open', ''), ('move', 'clear')]
SEGMENTS = {
    'pick': (('open', ''), ('move', 'approach'), ('move', 'grasp'), ('close', '')),
    'transfer': (('move', 'approach'), ('move', 'release')),
    'place': (('open', ''), ('move', 'clear')),
}
SUPPORTED_SEGMENTS = ('pick', 'transfer', 'place')
FIXED_NODES = {
    'base': ('robot', [0, 0, 0]), 'jaw': ('tool', [0, 0, 0]),
    'pick': ('frame', [.24, -.13, 0]), 'place': ('frame', [.24, .14, 0]),
    'approach': ('target', [.24, -.13, .08]), 'grasp': ('target', [.24, -.13, .02]),
    'release': ('target', [.24, .14, .03]), 'clear': ('target', [.24, .14, .1]),
}
OBSTACLE_HALF_SIZE = [.025, .028, .065]
WORKSPACE_DEVELOPMENT_MODE = 'workspace-development-v1'
WORKSPACE_TARGET_REGION = [[.21, .27], [-.16, -.10]]


def describe():
    return {
        'executor': 'so101-mujoco-visual-grasp', 'simulation_only': True,
        'message': '已接入本机 MuJoCo、视觉定位、IK/OMPL 和原抓放控制器',
        'capabilities': ['按 pick → transfer → place 动作段组合搬运任务', '八步原程序仍可直接运行',
                         '蓝盘放置 XY 和底座高度可修改，逐任务检查规划', '方块 XY 各 ±10mm',
                         '固定尺寸附加障碍', '协作停止', '新回合录像和物理报告'],
        'template': 'open → approach → grasp → close → approach → release → open → clear',
        'segments': {name: [{'action': action, 'target': target} for action, target in steps]
                     for name, steps in SEGMENTS.items()},
        'supported_segment_sequences': [list(SUPPORTED_SEGMENTS)],
        'supported_cube_xy_m': {'center': [.24, -.13], 'half_extent': [.01, .01]},
        'execution_modes': {
            'default': {'declaration': 'omit execution',
                        'supported_cube_xy_m': {'center': [.24, -.13], 'half_extent': [.01, .01]},
                        'pickup_hover_z_m': .06, 'pick_xy_m': [.24, -.13]},
            WORKSPACE_DEVELOPMENT_MODE: {
                'development_only': True, 'not_admitted': True,
                'target_region_xy_m': [axis.copy() for axis in WORKSPACE_TARGET_REGION],
                'pickup_hover_z_range_m': [.054, .06],
                'example': {'mode': WORKSPACE_DEVELOPMENT_MODE, 'pick_xy_m': [.26, -.13],
                            'pickup_hover_z_m': .054,
                            'target_region_xy_m': [axis.copy() for axis in WORKSPACE_TARGET_REGION]},
                'node_mapping': {'pick': 'execution.pick_xy_m, world Z=0',
                                 'approach': 'cube world XY, world Z=pickup_hover_z_m+0.02',
                                 'grasp': 'cube world XY, world Z=0.02'},
                'scope': '固定视觉先验不是连续可抓取范围；已有点位通过不能继承到新布局，每次仍做原 IK、碰撞、244 点与物理裁决。',
            },
        },
        'cube_z_m': .01, 'cube_size_m': [.018, .018, .016],
        'fixed_nodes_world_m': {name: xyz for name, (_, xyz) in FIXED_NODES.items()
                                if name not in ('place', 'release', 'clear')},
        'placement': {'mode': 'tray_xy_and_base_height', 'default_center_m': [.24, .14],
                      'default_base_height_m': 0., 'base_height_min_m': 0.,
                      'base_height_source': 'place_world_z',
                      'reachability': 'checked_by_existing_planner'},
        'additional_obstacle_size_m': [2*x for x in OBSTACLE_HALF_SIZE],
        'default_obstacle': {'center_m': [.265, 0, .065],
                             'size_m': [2*x for x in OBSTACLE_HALF_SIZE]},
        'limits': {'simulation_s': 90, 'wall_s': 120, 'collision_margin_m': .001},
        'notes': [
            'program可直接使用原八步原子动作，也可使用pick→transfer→place三个能力段；能力段在验证时展开为同一原子动作。',
            '当前物理执行器支持完整抓放组合；缺段、重复段或其他次序会在仿真前明确失败。',
            '八步搬运任务支持修改place坐标系XYZ，Z表示蓝盘底座相对桌面的非负高度，release/clear保持相对偏移。',
            '默认设计高度映射为现有规划指间高度：接近/抬升60mm、抓取19mm、释放为蓝盘底座上方28mm；释放采用floor_yaw估计，脱离与回位由安全规划产生。',
            'seconds=1保留为模板草稿值；实际运动时长由原控制器规划，不按一秒强行插值。',
            '坐标系平移逐级累加；蓝盘保持同尺寸，抬高时添加实体底座，可达性与碰撞由现有规划器检查。',
            '新增障碍为50×56×130mm轴对齐方盒；原有默认障碍同时保留。',
        ],
    }


class UnsupportedStation(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__('；'.join(issues))


def workspace_execution(station):
    """Parse an explicit development declaration without widening defaults."""
    if 'execution' not in station:
        return None
    execution = station['execution']
    if not isinstance(execution, dict) or execution.get('mode') != WORKSPACE_DEVELOPMENT_MODE:
        raise UnsupportedStation([f'execution 必须声明 mode={WORKSPACE_DEVELOPMENT_MODE}；省略 execution 才使用原默认工位'])
    issues = []
    allowed = {'mode', 'pick_xy_m', 'pickup_hover_z_m', 'target_region_xy_m'}
    extras = [key for key in execution if key not in allowed]
    if extras:
        warnings.warn('WARNING: execution 附加字段 '+', '.join(sorted(map(str, extras)))+
                      ' 仅保留为来源信息，不参与执行，原阈值不变', RuntimeWarning, stacklevel=2)

    def finite_pair(value):
        return (isinstance(value, list) and len(value) == 2 and
                all(not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
                    for x in value))

    pick_xy = execution.get('pick_xy_m')
    if not finite_pair(pick_xy):
        issues.append('execution.pick_xy_m 必须为两个有限非布尔米制数')
    hover = execution.get('pickup_hover_z_m')
    if (isinstance(hover, bool) or not isinstance(hover, (int, float)) or
            not math.isfinite(hover) or not .054 <= hover <= .06):
        issues.append('execution.pickup_hover_z_m 必须为 .054..06m 内有限非布尔数')
    region = execution.get('target_region_xy_m')
    if (not isinstance(region, list) or len(region) != 2 or
            not all(finite_pair(axis) for axis in region) or region != WORKSPACE_TARGET_REGION):
        issues.append('execution.target_region_xy_m 必须保持固定视觉先验 [[0.21,0.27],[-0.16,-0.10]]；不代表连续物理已验')
    if issues:
        raise UnsupportedStation(issues)
    return {**copy.deepcopy(execution),
            'mode': WORKSPACE_DEVELOPMENT_MODE, 'pick_xy_m': [float(x) for x in pick_xy],
            'pickup_hover_z_m': float(hover),
            'target_region_xy_m': [axis.copy() for axis in WORKSPACE_TARGET_REGION]}


def compile_program(program):
    """Compile a legacy atomic program or reusable capability segments."""
    if not isinstance(program, list):
        raise UnsupportedStation(['program 必须为数组'])
    if any(isinstance(step, dict) and 'capability' in step for step in program):
        if not all(isinstance(step, dict) and 'capability' in step for step in program):
            raise UnsupportedStation(['原子动作与能力段不能混写'])
        segments = []
        for index, step in enumerate(program):
            capability = step.get('capability')
            if capability not in SEGMENTS:
                raise UnsupportedStation([f'程序第 {index+1} 段的 capability 不受支持：{capability}'])
            if isinstance(step.get('seconds'), bool) or step.get('seconds') != 1:
                raise UnsupportedStation([f'程序第 {index+1} 段 seconds 需保留模板值 1；自定义时长尚未实现'])
            segments.append(capability)
        if tuple(segments) != SUPPORTED_SEGMENTS:
            raise UnsupportedStation([
                f'当前完整抓放执行器要求能力段依次为 {", ".join(SUPPORTED_SEGMENTS)}；'
                f'收到 {", ".join(segments) if segments else "空序列"}'])
        steps = [row for capability in segments for row in SEGMENTS[capability]]
        return {'mode': 'segments', 'segments': segments, 'steps': steps}
    steps = []
    for index, step in enumerate(program):
        if not isinstance(step, dict):
            raise UnsupportedStation([f'程序第 {index+1} 步必须为对象'])
        action, target = step.get('action'), step.get('target', '')
        if index >= len(TEMPLATE) or (action, target) != TEMPLATE[index]:
            expected = TEMPLATE[index] if index < len(TEMPLATE) else ('<程序结束>', '')
            raise UnsupportedStation([f'程序第 {index+1} 步需为 {expected[0]} {expected[1]}'])
        if isinstance(step.get('seconds'), bool) or step.get('seconds') != 1:
            raise UnsupportedStation([f'程序第 {index+1} 步 seconds 需保留模板值 1；自定义时长尚未实现'])
        steps.append((action, target))
    if len(steps) != len(TEMPLATE):
        raise UnsupportedStation(['当前只支持原始八步完整抓放模板或 pick→transfer→place 能力段'])
    return {'mode': 'atomic', 'segments': list(SUPPORTED_SEGMENTS), 'steps': steps}


def validate_station(station):
    """Resolve translated frames and admit only the implemented physical template."""
    issues = []
    if not isinstance(station, dict):
        raise UnsupportedStation(['工作站必须为 JSON 对象'])
    execution = workspace_execution(station)
    nodes = station.get('nodes')
    if not isinstance(nodes, list):
        raise UnsupportedStation(['nodes 必须为数组'])
    by_id = {}
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get('id'), str):
            issues.append('每个节点需要字符串 id')
            continue
        ident = node['id']
        if ident in by_id or ident == 'world':
            issues.append(f'节点 id 重复或保留：{ident}')
        by_id[ident] = node
    resolved = {}

    def position(ident, trail=()):
        if ident == 'world':
            return [0., 0., 0.]
        if ident in resolved:
            return resolved[ident]
        if ident not in by_id or ident in trail:
            raise ValueError(f'节点父级缺失或循环：{ident}')
        node = by_id[ident]
        xyz = node.get('position')
        if (not isinstance(xyz, list) or len(xyz) != 3 or
                any(isinstance(x, bool) or not isinstance(x, (int, float)) or
                    not math.isfinite(x) for x in xyz)):
            raise ValueError(f'节点坐标必须为三个有限数：{ident}')
        parent = position(node.get('parent', 'world'), (*trail, ident))
        resolved[ident] = [float(a+b) for a, b in zip(xyz, parent)]
        return resolved[ident]

    for ident in by_id:
        try:
            position(ident)
        except (ValueError, TypeError) as error:
            issues.append(str(error))
    place = resolved.get('place', FIXED_NODES['place'][1])
    if place[2] < 0:
        issues.append('place 世界Z表示蓝盘底座高度，必须大于等于0')
    place_shift = [place[0]-.24, place[1]-.14, place[2]]
    for ident, (kind, original) in FIXED_NODES.items():
        xyz = [a+b for a, b in zip(original, place_shift)] if ident in ('place', 'release', 'clear') else original
        if execution is not None:
            if ident == 'pick':
                xyz = [*execution['pick_xy_m'], 0.]
            elif ident in ('approach', 'grasp'):
                xy = resolved.get('cube', [.24, -.13, .01])[:2]
                xyz = [*xy, execution['pickup_hover_z_m']+.02 if ident == 'approach' else .02]
        node = by_id.get(ident)
        if node is None:
            issues.append(f'固定模板缺少节点：{ident}')
        elif node.get('kind') != kind:
            issues.append(f'节点 {ident} 必须为 {kind}')
        elif ident in resolved and any(abs(a-b) > 1e-8 for a, b in zip(resolved[ident], xyz)):
            issues.append(f'{ident} 需保持模板偏移/高度，当前目标对应世界位置为 {xyz}')
    cube = by_id.get('cube')
    if cube is None or cube.get('kind') != 'object':
        issues.append('需要 cube 物体节点')
    elif 'cube' in resolved:
        x, y, z = resolved['cube']
        if execution is not None:
            if (any(value < low or value > high
                    for value, (low, high) in zip((x, y), WORKSPACE_TARGET_REGION)) or
                    abs(z-.01) > 1e-8):
                issues.append('cube 开发工位需在固定 target_region_xy_m 视觉先验内，Z=0.01m；仍须逐任务物理检查')
        elif abs(x-.24) > .01000001 or abs(y+.13) > .01000001 or abs(z-.01) > 1e-8:
            issues.append('cube 支持世界 XY=(0.24±0.01,-0.13±0.01)m，Z=0.01m')
    obstacles = []
    for ident, node in by_id.items():
        if ident in FIXED_NODES or ident == 'cube':
            continue
        if node.get('kind') == 'obstacle' and ident in resolved:
            obstacles.append({'id': ident, 'position_m': resolved[ident],
                              'half_size_m': OBSTACLE_HALF_SIZE.copy(),
                              'geom_name': f'station_obstacle_{len(obstacles)}'})
        elif node.get('kind') != 'frame':
            issues.append(f'暂不支持额外 {node.get("kind")} 节点：{ident}')
    try:
        program_plan = compile_program(station.get('program'))
    except UnsupportedStation as error:
        issues.extend(error.issues)
        program_plan = None
    if issues:
        raise UnsupportedStation(issues)
    return {'cube_xyz_m': resolved['cube'], 'place_xy_m': resolved['place'][:2],
            'place_height_m': resolved['place'][2],
            'additional_obstacles': obstacles,
            'resolved_positions_m': resolved, 'program': program_plan,
            'mapping': describe()['notes'],
            **({'execution': execution, 'development_only': True, 'not_admitted': True}
               if execution is not None else {})}


def atomic_json(path, value, *, compact=False):
    temp = path.with_suffix('.tmp')
    formatting = {'separators': (',', ':')} if compact else {'indent': 2}
    temp.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, **formatting)+'\n')
    temp.replace(path)


class Cancelled(RuntimeError):
    pass


class StationVideo:
    """Capture physical states and render a compact replay without advancing physics."""
    def __init__(self, model, path, *, max_frames, deadline):
        import mujoco
        self.model, self.path, self.deadline = model, path, deadline
        self.signature = mujoco.mjtState.mjSTATE_INTEGRATION
        self.states = []
        self.receipt = {'complete': False, 'captured_frames': 0, 'encoded_frames': 0,
                        'fps': 6.25, 'width': 640, 'height': 480}

    def capture(self, data, tick):
        import mujoco
        import numpy as np
        state = np.empty(mujoco.mj_stateSize(self.model, self.signature))
        mujoco.mj_getState(self.model, data, state, self.signature)
        self.states.append(state)
        self.receipt['captured_frames'] = len(self.states)

    def report(self):
        return dict(self.receipt)

    def close(self):
        if not self.states:
            self.receipt['complete'] = True
            return
        import imageio.v2 as imageio
        import mujoco
        data = mujoco.MjData(self.model)
        renderer = mujoco.Renderer(self.model, height=480, width=640)
        try:
            with imageio.get_writer(str(self.path), fps=6.25, codec='libx264', quality=7,
                                    macro_block_size=16) as writer:
                for state in self.states:
                    if time.monotonic() >= self.deadline:
                        raise TimeoutError('video_wall_time_limit')
                    mujoco.mj_setState(self.model, data, state, self.signature)
                    mujoco.mj_forward(self.model, data)
                    renderer.update_scene(data, camera='overview')
                    writer.append_data(renderer.render())
                    self.receipt['encoded_frames'] += 1
            self.receipt['complete'] = True
        finally:
            renderer.close()


def run(station_path, output, cancel_file, *, route_policy=None, timing=None):
    output.mkdir(parents=True, exist_ok=True)
    current = {'status': 'running', 'phase': 'validating', 'simulation_s': 0.,
               'message': '解析工作站草稿', 'simulation_only': True,
               'cancel_requested': False, 'cancelled': False,
               'station_path': str(station_path), 'output_directory': str(output)}

    def publish(**changes):
        current.update(changes)
        if getattr(route_policy, 'compact_status_json', False):
            atomic_json(output/'status.json', current, compact=True)
        else:
            atomic_json(output/'status.json', current)

    def check_cancel():
        if cancel_file is not None and cancel_file.exists():
            current['cancel_requested'] = True
            raise Cancelled('用户停止了当前仿真')

    publish()
    try:
        check_cancel()
        station = json.loads(station_path.read_text())
        from station_recipe import station_from_document
        station = station_from_document(station)
        layout = validate_station(station)
        if route_policy is None:
            from route_policy import load_route_policy
            route_policy = load_route_policy()[0]
        atomic_json(output/'resolved-station.json', layout)
        publish(phase='initializing', message='加载现有 MuJoCo / IK / OMPL 执行器',
                station_name=station.get('name', 'SO101'), layout=layout,
                capability=describe(),
                **({key: layout[key] for key in ('execution', 'development_only', 'not_admitted')}
                   if 'execution' in layout else {}))
        os.environ.setdefault('MUJOCO_GL', 'egl')
        from support_native import (configure_quad_vertices, configure_small_direction_cache,
                                    configure_tree_leaf8, configure_leaf_packed,
                                    configure_packed_inline, configure_seed_bound_direct,
                                    configure_summary_fast)
        configure_quad_vertices(bool(route_policy and route_policy.quad_vertices))
        configure_small_direction_cache(bool(route_policy and route_policy.small_direction_cache))
        configure_tree_leaf8(bool(route_policy and route_policy.tree_leaf8))
        configure_leaf_packed(bool(route_policy and route_policy.leaf_packed))
        configure_packed_inline(bool(route_policy and route_policy.packed_inline))
        configure_seed_bound_direct(bool(route_policy and route_policy.seed_bound_direct))
        configure_summary_fast(bool(route_policy and route_policy.summary_fast))
        import mujoco
        from grasp_episode import build_contact_scene, numbers
        from run_visual_grasp import SOURCE, run_physical_episode

        def build_scene(source, folder, **kwargs):
            check_cancel()
            development_options = ({'pick_xy': layout['execution']['pick_xy_m']}
                                   if 'execution' in layout else {})
            model, rig, path = build_contact_scene(source, folder, place_xy=layout['place_xy_m'],
                                                   place_height_m=layout['place_height_m'],
                                                   **development_options, **kwargs)
            for name in ('contact-workcell.xml', 'grasp-planning.xml'):
                filename = folder/name
                tree = ET.parse(filename)
                world = tree.getroot().find('worldbody')
                for obstacle in layout['additional_obstacles']:
                    ET.SubElement(world, 'geom', name=obstacle['geom_name'], type='box',
                                  pos=numbers(obstacle['position_m']),
                                  size=numbers(obstacle['half_size_m']), contype='1', conaffinity='3',
                                  group='0' if name == 'contact-workcell.xml' else '3',
                                  rgba='.65 .34 .16 1')
                tree.write(filename, encoding='utf-8', xml_declaration=True)
            check_cancel()
            return (mujoco.MjModel.from_xml_path(str(path)),
                    mujoco.MjModel.from_xml_path(str(folder/'grasp-planning.xml')), path)

        last_publish = 0.
        last_scene_publish = 0.
        scene_projector = None
        scene_sequence = 0

        def scene(model, data, *, elapsed_s, phase, final=False, row=None):
            nonlocal last_scene_publish, scene_projector, scene_sequence
            now = time.monotonic()
            if not final and phase == current.get('scene_phase') and now-last_scene_publish < .1:
                return
            if scene_projector is None:
                from station_scene import StationScene
                scene_projector = StationScene(model)
            scene_sequence += 1
            target = model.body('grasp_target').id
            publish(scene=scene_projector.update(data, elapsed_s=elapsed_s, phase=phase),
                    scene_seq=scene_sequence, scene_time_s=elapsed_s, scene_phase=phase,
                    scene_final=final, scene_source='MuJoCo physical execution',
                    q6=data.qpos[:6].tolist(), object_xyz_m=data.xpos[target].tolist(),
                    object_quat_wxyz=data.xquat[target].tolist(), simulation_s=elapsed_s,
                    **({'tip_forces_n': row['tip_forces_n']} if row is not None else {}))
            last_scene_publish = now

        def progress(row):
            nonlocal last_publish
            check_cancel()
            now = time.monotonic()
            if row['stage'] != current['phase'] or now-last_publish > .4:
                publish(phase=row['stage'], simulation_s=row['elapsed_s'],
                        message='仿真执行：'+row['stage'],
                        object_xyz_m=row['object_xyz_m'], q6=row['q6'])
                last_publish = now

        case = {'id': 'station', 'initial_xy_m': layout['cube_xyz_m'][:2],
                'perturbed': False, 'offset_rad': [0.]*5,
                'obstacle_geom_names': ['approach_obstacle']+
                    [row['geom_name'] for row in layout['additional_obstacles']]}
        controller_options = {'release_rotation_mode': 'floor_yaw', 'release_pinch_height_m': .028,
                              'place_xy': layout['place_xy_m'], 'place_height_m': layout['place_height_m'],
                              'route_policy': route_policy}
        if 'execution' in layout:
            controller_options.update(pickup_hover_z_m=layout['execution']['pickup_hover_z_m'],
                                      target_region_xy_m=layout['execution']['target_region_xy_m'])
        report = run_physical_episode(SOURCE, output/'episode',
                    {'max_episode_wall_s': 120, 'max_sim_s': 90}, case, None,
                    video=True, scene_builder=build_scene, progress_callback=progress,
                    **({'timing': timing} if timing is not None else {}),
                    scene_callback=scene,
                    cancel_check=check_cancel, video_factory=StationVideo, video_stride=8,
                    controller_options=controller_options)
        cancel_requested = current['cancel_requested'] or (cancel_file is not None and cancel_file.exists())
        # A late request cannot replace the physical result or an earlier cause.
        cancelled = (report.get('error_type') == 'Cancelled' and not report['passed']
                     and not report.get('safety_stop') and not report.get('planner_cleanup_error')
                     and not report.get('planner_cleanup_errors')
                     and (not report.get('failure_reason') or report['failure_reason'] == report.get('error')))
        artifacts = {'report': str(output/'episode/report.json'),
                     'trajectory': str(output/'episode/trajectory.json'),
                     'resolved_station': str(output/'resolved-station.json')}
        for key, filename in [('video', 'grasp-place.mp4'), ('image', 'final.png'),
                              ('localization', 'initial-localization.png')]:
            file = output/'episode'/filename
            if file.is_file():
                artifacts[key] = str(file)
        state = 'cancelled' if cancelled else 'succeeded' if report['passed'] else 'failed'
        publish(status=state, phase='complete' if state == 'succeeded' else state,
                cancel_requested=cancel_requested, cancelled=cancelled,
                message=('抓起、搬运、放置、脱离与回位完成' if state == 'succeeded'
                         else '用户已停止仿真' if cancelled else report.get('failure_reason', '仿真未完成')),
                simulation_s=report.get('simulation_s', 0), artifacts=artifacts,
                report=report, video=artifacts.get('video'),
                result={key: report.get(key) for key in ('passed', 'grasp_success', 'place_success',
                         'safety_stop', 'failure_reason', 'hold_duration_s', 'settled_duration_s')})
        return 0 if state in ('succeeded', 'cancelled') else 1
    except Exception as error:
        state = 'cancelled' if isinstance(error, Cancelled) else 'failed'
        publish(status=state, phase=state, message=str(error), error_type=type(error).__name__,
                cancel_requested=(current['cancel_requested'] or isinstance(error, Cancelled)
                                  or (cancel_file is not None and cancel_file.exists())),
                cancelled=state == 'cancelled',
                unsupported=getattr(error, 'issues', []))
        return 0 if state == 'cancelled' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--station', type=Path)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--cancel-file', type=Path)
    parser.add_argument('--describe-json', action='store_true')
    args = parser.parse_args()
    if args.describe_json:
        print(json.dumps(describe(), ensure_ascii=False))
        return 0
    if args.station is None or args.output_dir is None:
        parser.error('--station and --output-dir are required')
    return run(args.station.resolve(), args.output_dir.resolve(),
               args.cancel_file.resolve() if args.cancel_file else None)


if __name__ == '__main__':
    raise SystemExit(main())
