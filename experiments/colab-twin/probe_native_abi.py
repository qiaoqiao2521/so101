"""Observe original native calls and own sampled inputs; never replace a result."""
from __future__ import annotations

import argparse
import ctypes as C
import json
from pathlib import Path
import random
import sys
import threading
import time

import numpy as np

import support_native as native
import visual_grasp_controller as controller
from probe_episode_timing import run_probe


class NativeObserver:
    def __init__(self, sample_cap=256, seed=20261023):
        self.sample_cap = sample_cap
        self.rng = random.Random(seed)
        self.seed = seed
        self.main_thread = threading.get_ident()
        self.local = threading.local()
        self.handles, self.owners, self.groups, self.samples = {}, {}, {}, {}
        self.warnings = set()
        self.libraries = {}
        self.original_get = native._get_library
        self.original_init = native.NativeSupport.__init__
        self.original_update = controller.VisualGraspController.update

    def warn(self, message):
        if message not in self.warnings:
            print('WARNING: '+message, file=sys.stderr)
            self.warnings.add(message)

    @staticmethod
    def integer(value):
        return int(getattr(value, 'value', value))

    def install(self):
        observer = self

        def initialize(instance, points, kinds):
            observer.original_init(instance, points, kinds)
            owner = len(observer.owners)+1
            observer.owners[owner] = {'count': instance.geometry_count,
                                      'kinds': tuple(kinds), 'geometry': None}
            observer.handles[observer.integer(instance._handle)] = owner
            geometry = None
            if threading.get_ident() == observer.main_thread:
                try:
                    if all(type(p) is np.ndarray for p in points) and all(type(k) is str for k in kinds):
                        geometry = [np.array(p, dtype=np.float64, order='C', copy=True) for p in points]
                    else:
                        observer.warn('Unusual geometry input: timing continues without geometry sampling')
                except Exception as error:
                    observer.warn('Geometry sampling skipped: '+type(error).__name__)
            observer.owners[owner]['geometry'] = geometry

        def update(instance, *args, **kwargs):
            previous = getattr(observer.local, 'controller', None)
            observer.local.controller = instance
            try:
                return observer.original_update(instance, *args, **kwargs)
            finally:
                observer.local.controller = previous

        def get_library():
            library = observer.original_get()
            if id(library) not in observer.libraries:
                original = library.ns_evaluate_hinted
                observer.libraries[id(library)] = (library, original)

                def call(*args):
                    active = getattr(observer.local, 'controller', None)
                    thread = threading.get_ident()
                    scope = ('main_update' if active is not None else 'main_other') if thread == observer.main_thread else 'worker'
                    stage = str(active.stage) if active is not None else scope
                    try:
                        owner = observer.handles.get(observer.integer(args[0]))
                    except (IndexError, TypeError, ValueError):
                        owner = None
                    wall, cpu = time.perf_counter_ns(), time.thread_time_ns()
                    result = original(*args)
                    wall, cpu = (time.perf_counter_ns()-wall)/1e9, (time.thread_time_ns()-cpu)/1e9
                    try:
                        key = (owner, scope, stage, thread)
                        group = observer.groups.setdefault(key, {'calls': 0, 'wall_s': 0.,
                            'thread_cpu_s': 0., 'nonzero_status': 0})
                        group['calls'] += 1
                        group['wall_s'] += wall
                        group['thread_cpu_s'] += cpu
                        group['nonzero_status'] += int(result != 0)
                        if result == 0 and scope == 'main_update':
                            observer.sample(owner, stage, args)
                    except Exception as error:
                        observer.warn('Optional native observation skipped: '+type(error).__name__)
                    return result

                library.ns_evaluate_hinted = call
            return library

        native.NativeSupport.__init__ = initialize
        controller.VisualGraspController.update = update
        native._get_library = get_library

    def uninstall(self):
        native._get_library = self.original_get
        native.NativeSupport.__init__ = self.original_init
        controller.VisualGraspController.update = self.original_update
        for library, original in self.libraries.values():
            library.ns_evaluate_hinted = original

    def sample(self, owner, stage, args):
        geometry = self.owners.get(owner)
        if geometry is None or geometry['geometry'] is None:
            self.warn('No owned geometry for a native input; timing continues')
            return
        count, n = self.integer(args[4]), geometry['count']
        pool = self.samples.setdefault((owner, stage, count), {'seen': 0, 'rows': []})
        pool['seen'] += 1
        slot = len(pool['rows']) if len(pool['rows']) < self.sample_cap else self.rng.randrange(pool['seen'])
        if slot >= self.sample_cap:
            return
        row = {'query_index': pool['seen'], 'margin': float(args[5]),
            'positions': np.ctypeslib.as_array(args[1], shape=(n*3,)).reshape(n, 3).copy(),
            'rotations': np.ctypeslib.as_array(args[2], shape=(n*9,)).reshape(n, 3, 3).copy(),
            'pairs': np.ctypeslib.as_array(args[3], shape=(count*2,)).reshape(count, 2).copy(),
            'hint_in': np.ctypeslib.as_array(args[8], shape=(n*6,)).reshape(n, 3, 2).copy()}
        if slot == len(pool['rows']):
            pool['rows'].append(row)
        else:
            pool['rows'][slot] = row

    def save(self, folder, *, controller_wall_s=None):
        folder.mkdir(parents=True, exist_ok=True)
        owners, pools = {}, []
        for (owner, stage, count), pool in self.samples.items():
            if not pool['rows']:
                continue
            if owner not in owners:
                meta = self.owners[owner]
                path = folder/f'owner-{owner}-geometry.npz'
                np.savez_compressed(path, kinds=np.asarray(meta['kinds'], dtype='U4'),
                                    **{f'vertices_{i}': p for i, p in enumerate(meta['geometry'])})
                owners[owner] = {'geometry_count': meta['count'], 'path': str(path)}
            rows = sorted(pool['rows'], key=lambda row: row['query_index'])
            path = folder/f'owner-{owner}-{stage}-{count}-inputs.npz'
            np.savez_compressed(path, **{key: np.asarray([row[key] for row in rows]) for key in rows[0]})
            pools.append({'owner': owner, 'stage': stage, 'pairs_per_call': count,
                          'seen': pool['seen'], 'samples': len(rows), 'path': str(path)})
        groups = [dict(values, owner=key[0], scope=key[1], stage=key[2], thread_id=key[3])
                  for key, values in self.groups.items()]
        main_native = sum(row['wall_s'] for row in groups if row['scope'] == 'main_update')
        result = {'schema': 'so101.native-abi-observation.v1',
            'scope': 'Original ABI calls, read-only timing and sampled owned inputs; no algorithm speedup verdict',
            'timing': 'perf_counter_ns/thread_time_ns; clock boundary overhead included',
            'thread_scope': 'Main update intervals are sequential; worker wall intervals overlap and must not be summed into the loop',
            'sampling': {'cap_per_owner_stage_pair_count': self.sample_cap, 'seed': self.seed,
                         'method': 'uniform reservoir using an independent RNG; no physical truncation'},
            'replay_contract': 'Restore each recorded hint_in; do not infer hints by replaying the sampled sequence alone',
            'groups': groups, 'owners': owners, 'pools': pools, 'warnings': sorted(self.warnings),
            'observed_main_native_wall_s': main_native, 'observed_controller_wall_s': controller_wall_s,
            'native_fraction_of_observed_controller': main_native/controller_wall_s if controller_wall_s else None,
            'fraction_note': 'Denominator includes observer bookkeeping/copies; this is a diagnostic observation, not uninstrumented task performance'}
        (folder/'native-abi.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--station', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--sample-cap', type=int, default=256)
    args = parser.parse_args()
    if args.sample_cap < 1:
        parser.error('sample-cap must be positive')
    observer = NativeObserver(args.sample_cap)
    observer.install()
    try:
        original = run_probe(args.station.resolve(), args.output_dir.resolve(), cycles=None)
    finally:
        observer.uninstall()
    total = original['summary']['sections'].get('controller', {}).get('wall_s', {}).get('total_s')
    folder = args.output_dir.resolve()/original['run_id']/'native-abi'
    result = observer.save(folder, controller_wall_s=total)
    print(json.dumps({'native_abi': str(folder/'native-abi.json'),
                      'groups': len(result['groups']), 'sample_pools': len(result['pools']),
                      'native_fraction': result['native_fraction_of_observed_controller']}))
    return original['original_exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
