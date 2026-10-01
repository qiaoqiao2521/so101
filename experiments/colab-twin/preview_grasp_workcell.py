#!/usr/bin/env python3
"""Build/preview the grasp model; test dynamic support and real jaw articulation."""
import argparse
import ctypes.util
import hashlib
import json
import os
from pathlib import Path
import uuid
os.environ.setdefault('MUJOCO_GL', 'osmesa' if ctypes.util.find_library('OSMesa') else 'egl')
import imageio.v2 as imageio
import mujoco
import numpy as np
from grasp_workcell import build_workcell, TARGET_SIZE, TARGET_MASS_KG
from collision_scene import build_scene
from position_ik import solve_position_ik


def preview(source, output):
    output.mkdir(parents=True, exist_ok=False)
    # Choose a display pose using the original six-joint kinematic model, not
    # the old planner's fixed-six-coordinate collision checker on a free object.
    rig = build_scene(source, output/'pose-scene.xml', [], table_z=0)
    initial = np.array([0,0,0,0,0,.8],dtype=float)
    pose = solve_position_ik(rig, initial, np.array([.24,-.13,.095]), seed=0)
    if pose['status'] != 'solved':
        raise RuntimeError('No display pose for fixture')
    model, path = build_workcell(source, output)
    data = mujoco.MjData(model)
    data.qpos[:6] = pose['qpos']
    data.ctrl[:] = pose['qpos']
    object_id = model.body('grasp_target').id
    target_geom = model.geom('target_collision').id
    mujoco.mj_forward(model,data)
    start_z = float(data.xpos[object_id,2])
    for _ in range(1000):
        mujoco.mj_step(model,data)
    mujoco.mj_forward(model,data)
    settled_xyz = data.xpos[object_id].copy()
    if not np.all(np.isfinite(data.qpos)) or abs(settled_xyz[2]-.01)>.001:
        raise RuntimeError('Free target did not settle on the 2mm tray floor')
    support_contacts = []
    for c in data.contact:
        ids = (int(c.geom1),int(c.geom2))
        if target_geom in ids:
            other = ids[1] if ids[0]==target_geom else ids[0]
            support_contacts.append(model.geom(other).name)
    if 'pick_floor' not in support_contacts:
        raise RuntimeError('Target has no physical support contact')
    views = {'overview':([.23,0,.19],1.52,132,-30),
             'gripper_detail':([.22,-.13,.10],.46,140,-17),
             'topdown':([.24,0,.03],.92,90,-89)}
    with mujoco.Renderer(model,height=720,width=1280) as renderer:
        for name,(lookat,distance,azimuth,elevation) in views.items():
            camera=mujoco.MjvCamera()
            camera.lookat[:]=lookat
            camera.distance=distance
            camera.azimuth=azimuth
            camera.elevation=elevation
            renderer.update_scene(data,camera=camera)
            imageio.imwrite(output/(name+'.png'),renderer.render())
        frames=[]
        measured=[]
        object_z=[]
        camera=mujoco.MjvCamera()
        camera.lookat[:]=views['gripper_detail'][0]
        camera.distance,camera.azimuth,camera.elevation=views['gripper_detail'][1:]
        for step in range(2000):
            # An open/close mechanical preview, not a scripted grasp animation.
            data.ctrl[5]=.25+.55*(.5+.5*np.cos(2*np.pi*step/2000))
            mujoco.mj_step(model,data)
            if step%20==0:
                mujoco.mj_forward(model,data)
                measured.append(float(data.qpos[5]))
                object_z.append(float(data.xpos[object_id,2]))
                renderer.update_scene(data,camera=camera)
                frames.append(renderer.render().copy())
    imageio.mimsave(output/'jaw_motion.mp4',frames,fps=25,macro_block_size=16)
    if max(measured)-min(measured)<.4:
        raise RuntimeError('Physical jaw did not articulate')
    report={'kind':'so101_grasp_model_preview','status':'passed','arm_count':1,
            'arm_joints':6,'object_free_joint':True,'target_size_m':TARGET_SIZE,
            'target_mass_kg':TARGET_MASS_KG,'target_initial_z_m':start_z,
            'target_settled_xyz_m':settled_xyz.tolist(),'target_support_contacts':support_contacts,
            'target_max_lift_during_preview_m':max(object_z)-float(settled_xyz[2]),
            'jaw_actual_range_rad':[min(measured),max(measured)],'views':list(views),
            'frames':len(frames),'simulation_seconds':float(data.time),
            'source_model_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'mujoco_version':mujoco.__version__,'hardware_connected':False,'cloud_allocated':False,
            'grasp_success':None,'lift_success':None,
            'acceptance':'Editable workcell, dynamic object support and physical jaw motion only',
            'not_validated':['contact grasp','object lift','pick/place execution','hardware calibration']}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    print('Output: '+str(output))


def main():
    root=Path(__file__).resolve().parent
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path)
    parser.add_argument('--output',type=Path,default=root/'output')
    args=parser.parse_args()
    source=args.model or root.parents[1]/'workspaces/so101_ws/src/so101_mujoco/models/so101.xml'
    preview(source.resolve(),args.output.resolve()/('grasp-model-'+uuid.uuid4().hex))

if __name__=='__main__':main()
