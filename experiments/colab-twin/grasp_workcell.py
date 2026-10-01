"""Editable single-SO101 contact workcell, separate from the six-DOF planner."""
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
from collision_scene import build_scene

TARGET_SIZE = (0.018, 0.018, 0.016)
TARGET_MASS_KG = 0.010
PICK_CENTER = (0.24, -0.13)
PLACE_CENTER = (0.24, 0.14)


def numbers(values):
    return ' '.join(format(float(x), '.9g') for x in values)


def build_workcell(source, output):
    """Reuse original arm geometry; add a freely moving 10g target and open trays.

    Dimensions/friction are simulation fixtures, not measured hardware values.
    No weld, adhesion, mocap parenting or scripted object movement is used.
    """
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    build_scene(source, output / 'arm-scene.xml', [], table_z=0)
    tree = ET.parse(output / 'arm-scene.xml')
    root = tree.getroot()
    world, asset = root.find('worldbody'), root.find('asset')
    root.set('model', 'so101_single_arm_grasp_workcell')
    option = root.find('option')
    option.set('integrator', 'implicitfast')
    option.set('cone', 'elliptic')
    for element in list(world):
        if element.tag == 'light' or element.get('name') in ('worktable', 'visible_worktable'):
            world.remove(element)
    for texture in list(asset.findall('texture')):
        if texture.get('type') == 'skybox':
            asset.remove(texture)
    ET.SubElement(asset, 'texture', name='studio_sky', type='skybox', builtin='gradient',
                  rgb1='.96 .97 .98', rgb2='.83 .87 .91', width='512', height='3072')
    for material in asset.findall('material'):
        motor = material.get('name', '').startswith('sts3215')
        material.set('rgba', '.075 .09 .11 1' if motor else '.78 .58 .22 1')
        material.set('specular', '.25')
        material.set('shininess', '.2')
    visual = root.find('visual')
    for element in list(visual):
        visual.remove(element)
    ET.SubElement(visual, 'global', offwidth='1280', offheight='960')
    ET.SubElement(visual, 'quality', shadowsize='4096', offsamples='4')
    ET.SubElement(visual, 'headlight', ambient='.25 .25 .25', diffuse='.25 .25 .25', specular='.1 .1 .1')
    ET.SubElement(visual, 'rgba', haze='.94 .96 .98 1')
    ET.SubElement(world, 'light', name='key_light', pos='-.3 -.5 1.2', dir='.3 .4 -1',
                  diffuse='.65 .63 .60', ambient='.15 .15 .15', castshadow='true')
    ET.SubElement(world, 'light', name='fill_light', pos='.7 .4 .9', dir='-.4 -.3 -1',
                  diffuse='.35 .39 .44', castshadow='false')

    def geom(name, kind, pos, size, color, *, physical=False, **extra):
        return ET.SubElement(world, 'geom', name=name, type=kind, pos=numbers(pos),
                             size=numbers(size), rgba=color, group='0',
                             contype='1' if physical else '0',
                             conaffinity='1' if physical else '0', **extra)

    # Table dimensions echo the existing BLD-001 workcell, translated so base z=0.
    geom('worktable', 'box', (.25, 0, -.023), (.45, .35, .023), '.72 .75 .77 1', physical=True)
    geom('table_edge', 'box', (.25, 0, -.047), (.455, .355, .008), '.18 .22 .27 1')
    geom('studio_floor', 'plane', (0, 0, -.72), (3, 3, .01), '.91 .93 .95 1')
    for x in (-.12, .62):
        for y in (-.28, .28):
            geom(f'leg_{x}_{y}', 'box', (x,y,-.39), (.018,.018,.32), '.25 .30 .35 1')
    geom('robot_mount_plate', 'box', (0,0,-.001), (.065,.065,.001), '.30 .35 .40 1')
    for x in (-.048,.048):
        for y in (-.048,.048):
            geom(f'mount_bolt_{x}_{y}', 'cylinder', (x,y,.002), (.003,.002), '.13 .17 .20 1')

    for prefix, center, color in [('pick', PICK_CENTER, '.64 .30 .23 1'),
                                   ('place', PLACE_CENTER, '.20 .39 .58 1')]:
        x,y = center
        geom(prefix+'_floor', 'box', (x,y,.001), (.06,.06,.001), '.45 .49 .52 1', physical=True)
        for side in (-1,1):
            geom(f'{prefix}_wall_x_{side}', 'box', (x+side*.059,y,.009), (.001,.06,.009), color, physical=True)
            geom(f'{prefix}_wall_y_{side}', 'box', (x,y+side*.059,.009), (.06,.001,.009), color, physical=True)
        # Front plaque and a category strip give visual identity without obstructing the arm.
        geom(prefix+'_plaque', 'box', (x,y-.075,.001), (.038,.008,.001), color)
    body = ET.SubElement(world, 'body', name='grasp_target', pos=numbers((*PICK_CENTER,.012)))
    ET.SubElement(body, 'freejoint', name='target_free')
    ET.SubElement(body, 'geom', name='target_collision', type='box', size=numbers([x/2 for x in TARGET_SIZE]),
                  rgba='.28 .57 .43 1', mass=str(TARGET_MASS_KG), group='0',
                  contype='1', conaffinity='1', condim='4', friction='.8 .005 .0001')
    ET.SubElement(body, 'site', name='target_center', size='.001', rgba='0 0 0 0')
    # Camera fixture is display-only and outside the moving workspace.
    geom('camera_post', 'cylinder', (.55,.27,.30), (.009,.30), '.32 .38 .43 1')
    geom('camera_boom', 'box', (.40,.27,.59), (.16,.009,.009), '.32 .38 .43 1')
    geom('camera_body', 'box', (.25,.27,.565), (.03,.02,.015), '.08 .10 .13 1')
    geom('camera_lens', 'cylinder', (.25,.27,.544), (.009,.006), '.14 .22 .29 1')
    for name, pos, axes in [('overview', (.87,-.84,.68), (.72,.69,0,-.36,.38,.85)),
                            ('topdown', (.25,0,.95), (1,0,0,0,1,0))]:
        ET.SubElement(world, 'camera', name=name, pos=numbers(pos), xyaxes=numbers(axes))
    path = output / 'workcell.xml'
    tree.write(path, encoding='utf-8', xml_declaration=True)
    model = mujoco.MjModel.from_xml_path(str(path))
    if model.nq != 13 or model.nu != 6 or model.body('grasp_target').mass != TARGET_MASS_KG:
        raise RuntimeError('Unexpected arm/object layout or object mass')
    return model, path
