"""Replay only saved planning endpoint IK; never a physical success verdict."""
import argparse,json,time,statistics,sys
from pathlib import Path
import numpy as np
import mujoco
sys.path.insert(0,str(Path(__file__).resolve().parent))
from grasp_episode import solve_pinch_ik
from route_policy import load_route_policy
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--episode',type=Path,required=True)
parser.add_argument('--candidate',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--repeats',type=int,default=3)
a=parser.parse_args()
if a.repeats < 1:
    parser.error("--repeats must be positive")
plans=json.loads((a.episode/'planning.json').read_text())
p=next(x for x in plans if x.get('stage')=='transport_execution_plan')
model=mujoco.MjModel.from_xml_path(str((a.episode/'scene/grasp-planning.xml').resolve()))
initial=np.asarray(p['waiting']['snapshot_q6'])[:5]
place=np.asarray(p['place_xy']);release=p['release_world_height_m'];base=p['place_height_m']
heights=[float(z)for z in np.arange(.06+base,release,-.003)]+[release]
policy,loaded=load_route_policy(a.candidate)
original,_=load_route_policy()
rows=[]
for repeat in range(a.repeats):
 for label,configuration in ([('baseline',original),('candidate',policy)] if repeat%2==0 else [('candidate',policy),('baseline',original)]):
  wall=time.perf_counter();cpu=time.process_time();attempts=[]
  # Same mandatory release endpoint check as the original transport planner.
  try:solve_pinch_ik(model,np.r_[place,release],initial if configuration.ik_seed=='continuation' else None)
  except RuntimeError as error:
   if not str(error).startswith('No vertical pinch IK candidate'):raise
   rows.append({'repeat':repeat,'label':label,'release_endpoint_failure':str(error),'wall_s':time.perf_counter()-wall,'cpu_s':time.process_time()-cpu,'attempts':[]});continue
  for height in configuration.transport_heights(heights,base):
   w=time.perf_counter();c=time.process_time();record={'height_m':height}
   try:
    q=solve_pinch_ik(model,np.r_[place,height],initial if configuration.ik_seed=='continuation' else None)
    record.update(status='reachable_endpoint_only',q5=q.tolist())
   except RuntimeError as error:
    if not str(error).startswith('No vertical pinch IK candidate'):raise
    record.update(status='rejected_endpoint',reason=str(error))
   record.update(wall_s=time.perf_counter()-w,cpu_s=time.process_time()-c);attempts.append(record)
   if record['status']=='reachable_endpoint_only':break
  rows.append({'repeat':repeat,'label':label,'wall_s':time.perf_counter()-wall,'cpu_s':time.process_time()-cpu,'attempts':attempts})
result={'mode':'saved_planning_endpoint_screen','physical_success':None,'full_route_certified':False,'source_episode':str(a.episode.resolve()),'candidate':loaded,'original_model_path':str((a.episode/'scene/grasp-planning.xml').resolve()),'snapshot_q5':initial.tolist(),'rows':rows,'summary':{label:{'median_wall_s':statistics.median(x['wall_s']for x in rows if x['label']==label),'median_cpu_s':statistics.median(x['cpu_s']for x in rows if x['label']==label)}for label in ['baseline','candidate']},'limits':'Stops at first reachable endpoint, not first certified route. Cannot approve a controller, grasp/place, collision, release, return or total-runtime speedup.'}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2));print(json.dumps(result['summary']),flush=True)
