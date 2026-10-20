"""Run the supported station template with the existing MuJoCo/IK/OMPL executor.

Station JSON remains freely editable. Unsupported physical intent is reported
before simulation rather than being replaced with the historical default scene.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import time
import xml.etree.ElementTree as ET


TEMPLATE = [('open', ''), ('move', 'approach'), ('move', 'grasp'), ('close', ''),
            ('move', 'approach'), ('move', 'release'), ('open', ''), ('move', 'clear')]
FIXED_NODES = {
    'base': ('robot', [0, 0, 0]), 'jaw': ('tool', [0, 0, 0]),
    'pick': ('frame', [.24, -.13, 0]), 'place': ('frame', [.24, .14, 0]),
    'approach': ('target', [.24, -.13, .08]), 'grasp': ('target', [.24, -.13, .02]),
    'release': ('target', [.24, .14, .03]), 'clear': ('target', [.24, .14, .1]),
}
OBSTACLE_HALF_SIZE = [.025, .028, .065]


def describe():
    return {
        'executor': 'so101-mujoco-visual-grasp', 'simulation_only': True,
        'message': '已接入本机 MuJoCo、视觉定位、IK/OMPL 和原抓放控制器',
        'capabilities': ['原始八步完整抓放模板', '方块 XY 各 ±10mm',
                         '固定尺寸附加障碍', '协作停止', '新回合录像和物理报告'],
        'template': 'open → approach → grasp → close → approach → release → open → clear',
        'supported_cube_xy_m': {'center': [.24, -.13], 'half_extent': [.01, .01]},
        'cube_z_m': .01, 'cube_size_m': [.018, .018, .016],
        'fixed_nodes_world_m': {name: xyz for name, (_, xyz) in FIXED_NODES.items()},
        'additional_obstacle_size_m': [2*x for x in OBSTACLE_HALF_SIZE],
        'default_obstacle': {'center_m': [.265, 0, .065],
                             'size_m': [2*x for x in OBSTACLE_HALF_SIZE]},
        'limits': {'simulation_s': 90, 'wall_s': 120, 'collision_margin_m': .001},
        'notes': [
            '目标点用于识别固定抓放模板；当前不执行任意编辑的航点程序。',
            '默认设计高度映射为现有规划指间高度：接近/抬升60mm、抓取19mm、释放28mm；释放采用floor_yaw估计，脱离与回位由安全规划产生。',
            'seconds=1保留为模板草稿值；实际运动时长由原控制器规划，不按一秒强行插值。',
            '坐标系平移逐级累加；固定节点最终世界位置需保持模板值。',
            '新增障碍为50×56×130mm轴对齐方盒；原有默认障碍同时保留。',
        ],
    }


class UnsupportedStation(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__('；'.join(issues))


def validate_station(station):
    """Resolve translated frames and admit only the implemented physical template."""
    issues = []
    if not isinstance(station, dict):
        raise UnsupportedStation(['工作站必须为 JSON 对象'])
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
    for ident, (kind, xyz) in FIXED_NODES.items():
        node = by_id.get(ident)
        if node is None:
            issues.append(f'固定模板缺少节点：{ident}')
        elif node.get('kind') != kind:
            issues.append(f'节点 {ident} 必须为 {kind}')
        elif ident in resolved and any(abs(a-b) > 1e-8 for a, b in zip(resolved[ident], xyz)):
            issues.append(f'暂不支持修改 {ident} 世界位置，需保持 {xyz}')
    cube = by_id.get('cube')
    if cube is None or cube.get('kind') != 'object':
        issues.append('需要 cube 物体节点')
    elif 'cube' in resolved:
        x, y, z = resolved['cube']
        if abs(x-.24) > .01000001 or abs(y+.13) > .01000001 or abs(z-.01) > 1e-8:
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
    program = station.get('program')
    if not isinstance(program, list) or len(program) != len(TEMPLATE):
        issues.append('当前只支持原始八步完整抓放模板')
    else:
        for index, (step, (action, target)) in enumerate(zip(program, TEMPLATE)):
            if not isinstance(step, dict) or (step.get('action'), step.get('target', '')) != (action, target):
                issues.append(f'程序第 {index+1} 步需为 {action} {target}')
            elif isinstance(step.get('seconds'), bool) or step.get('seconds') != 1:
                issues.append(f'程序第 {index+1} 步 seconds 需保留模板值 1；自定义时长尚未实现')
    if issues:
        raise UnsupportedStation(issues)
    return {'cube_xyz_m': resolved['cube'], 'additional_obstacles': obstacles,
            'resolved_positions_m': resolved, 'mapping': describe()['notes']}


def atomic_json(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
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


def run(station_path, output, cancel_file):
    output.mkdir(parents=True, exist_ok=True)
    current = {'status': 'running', 'phase': 'validating', 'simulation_s': 0.,
               'message': '解析工作站草稿', 'simulation_only': True,
               'station_path': str(station_path), 'output_directory': str(output)}

    def publish(**changes):
        current.update(changes)
        atomic_json(output/'status.json', current)

    def check_cancel():
        if cancel_file is not None and cancel_file.exists():
            raise Cancelled('用户停止了当前仿真')

    publish()
    try:
        check_cancel()
        station = json.loads(station_path.read_text())
        if isinstance(station, dict) and 'station' in station:
            station = station['station']
        layout = validate_station(station)
        atomic_json(output/'resolved-station.json', layout)
        publish(phase='initializing', message='加载现有 MuJoCo / IK / OMPL 执行器',
                station_name=station.get('name', 'SO101'), layout=layout,
                capability=describe())
        os.environ.setdefault('MUJOCO_GL', 'egl')
        import mujoco
        from grasp_episode import build_contact_scene, numbers
        from run_visual_grasp import SOURCE, run_physical_episode

        def build_scene(source, folder, **kwargs):
            check_cancel()
            model, rig, path = build_contact_scene(source, folder, **kwargs)
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
        report = run_physical_episode(SOURCE, output/'episode',
                    {'max_episode_wall_s': 120, 'max_sim_s': 90}, case, None,
                    video=True, scene_builder=build_scene, progress_callback=progress,
                    cancel_check=check_cancel, video_factory=StationVideo, video_stride=8,
                    controller_options={'release_rotation_mode': 'floor_yaw',
                                        'release_pinch_height_m': .028})
        cancelled = cancel_file is not None and cancel_file.exists()
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
