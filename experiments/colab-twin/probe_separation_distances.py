"""Replay a saved release proposal; no reset, physics integration or scoring.

Baseline and candidate share the same saved estimate and planning scene. Local
pass means equal planning output, never physical task success. Every pair and
both clocks are retained, including slower candidate measurements.
"""
from dataclasses import asdict, replace
from contextlib import nullcontext
import argparse
import copy
import json
from pathlib import Path
import runpy
import struct
import time
from unittest.mock import patch

import mujoco
import numpy as np

from factory_minimum_suite import screen
from released_object import ReleasedObjectQuery
from route_policy import DEFAULT_ROUTE_POLICY, load_route_policy
from separation_worker import SeparationSnapshot, run_separation_plan


def exact(value):
    """Compare actual float64 bytes, including signed zero, without hashes."""
    if isinstance(value, (float, np.floating)):
        return struct.pack('=d', value)
    if isinstance(value, dict):
        return tuple((key, exact(item)) for key, item in value.items())
    if isinstance(value, (list, tuple, np.ndarray)):
        return tuple(exact(item) for item in value)
    return value


def planning_output(plan):
    report = json.loads(plan.report_json)
    # Only this declared preference and diagnostic counters intentionally vary.
    for record in (*report['plan_reports'], report['release_record']):
        policy = record.get('separation_end', {}).get('route_policy', {})
        policy.pop('reuse_separation_distances', None)
        policy.pop('batch_separation_axes', None)
    return exact((plan.paths, [asdict(row) for row in plan.samples],
                  report['plan_reports'], report['release_record'],
                  report['separation_context']))


def probe(episode, output, repeats=3, distance_kernel=None, candidate=None):
    episode = Path(episode).resolve()
    saved = json.loads((episode/'report.json').read_text())
    values = dict(saved['separation_proof']['snapshot'])
    release = saved['release_plan']
    values.update(rotation=release.get('rotation_world', np.eye(3)),
                  place_height_m=release.get('place_height_m', 0.))
    snapshot = SeparationSnapshot(**values)
    scene = episode/'scene/grasp-planning.xml'
    rig = mujoco.MjModel.from_xml_path(str(scene))
    released = ReleasedObjectQuery(scene, uncertainty_m=snapshot.uncertainty)
    released.freeze(snapshot.center, snapshot.rotation)
    kernel = (runpy.run_path(str(distance_kernel), init_globals={'np': np})['box_separation']
              if distance_kernel else None)
    candidate_policy = (load_route_policy(candidate)[0] if candidate else
                        replace(DEFAULT_ROUTE_POLICY, reuse_separation_distances=kernel is None))
    rows, checks = [], []
    for repeat in range(repeats):
        outputs = {}
        order = ('baseline', 'candidate') if repeat % 2 == 0 else ('candidate', 'baseline')
        pair = []
        for label in order:
            policy = DEFAULT_ROUTE_POLICY if label == 'baseline' else candidate_policy
            left, right = copy.copy(rig), copy.copy(released.model)
            scope = (patch('released_object.box_separation', kernel)
                     if label == 'candidate' and kernel else nullcontext())
            with scope:
                start_wall, start_cpu = time.perf_counter(), time.process_time()
                try:
                    plan = run_separation_plan(left, right, replace(snapshot, route_policy=policy))
                except Exception as error:
                    wall_s, cpu_s = time.perf_counter()-start_wall, time.process_time()-start_cpu
                    row = dict(pair=repeat+1, label=label, verdict='fail',
                               exception_type=type(error).__name__, exception=str(error))
                else:
                    wall_s, cpu_s = time.perf_counter()-start_wall, time.process_time()-start_cpu
                    outputs[label] = planning_output(plan)
                    row = dict(pair=repeat+1, label=label, verdict='pass',
                               worker_steps=json.loads(plan.report_json)['worker_steps'])
            row.update(wall_s=wall_s, cpu_s=cpu_s)
            pair.append(row)
        equal = (len(outputs) == 2 and outputs['baseline'] == outputs['candidate'])
        for row in pair:
            row['output_equivalent'] = equal
        rows.extend(pair)
        checks.append(equal)
        if not equal:
            break
    result = dict(mode='saved_release_planning_screen', source_episode=str(episode),
                  physical_success=None, physics_steps=0, rows=rows,
                  candidate_kernel=str(distance_kernel) if distance_kernel else None,
                  candidate_source=str(candidate) if candidate else None,
                  comparison='all path, sample, guard and mathematical report float64 bytes',
                  scope='Local equivalence and cost only; original physical evaluator remains required.')
    if len(checks) >= 3:
        groups = {label: [dict(measurement_s=row['wall_s'],
                              output_equivalent=row['output_equivalent'],
                              verdict=row['verdict'], source=str(episode))
                          for row in rows if row['label'] == label]
                  for label in ('baseline', 'candidate')}
        result['screen'] = screen(groups['baseline'], groups['candidate'])
    else:
        result['screen'] = dict(decision='reject', reason='incomplete_or_unequal_pairs')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(output=str(output), decision=result['screen']['decision'],
                          reason=result['screen']['reason'], pairs=len(checks))))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--episode', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=3)
    candidates = parser.add_mutually_exclusive_group()
    candidates.add_argument('--distance-kernel', type=Path,
                        help='Local source exporting box_separation; disables pose-cache candidate')
    candidates.add_argument('--candidate', type=Path, help='Use the existing route_preferences entrypoint')
    args = parser.parse_args()
    if args.repeats < 3:
        parser.error('--repeats must be at least 3 for the existing paired screen')
    probe(args.episode, args.output, args.repeats, args.distance_kernel, args.candidate)


if __name__ == '__main__':
    main()
