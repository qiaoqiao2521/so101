"""Measure a short real station loop; deliberate truncation is never task success.

Uses the existing evaluator, controller, video and all original physical guards.
No synthetic pose replay, alternative scorer or changed episode deadline.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import resource
import sys
import time

from episode_timing import EpisodeTiming


class DiagnosticCycleLimit(RuntimeError):
    pass


def host_snapshot():
    fields = ('Threads:', 'Cpus_allowed_list:', 'voluntary_ctxt_switches:',
              'nonvoluntary_ctxt_switches:')
    return {'monotonic_s': time.monotonic(), 'load_average': os.getloadavg(),
            'process_status': [line for line in Path('/proc/self/status').read_text().splitlines()
                               if line.startswith(fields)],
            'cpu_ticks': Path('/proc/stat').read_text().splitlines()[0]}


def distributions(rows, key):
    values = sorted(row[key] for row in rows)
    if not values:
        return {'count': 0, 'total_s': 0., 'median_s': None, 'p95_s': None, 'max_s': None}
    n = len(values)
    middle = (values[(n-1)//2]+values[n//2])/2
    return {'count': n, 'total_s': sum(values), 'median_s': middle,
            'p95_s': values[min(n-1, (95*n+99)//100-1)], 'max_s': values[-1]}


def summarize(timing):
    complete = [row for row in timing.cycles if row['complete']]
    sections = {}
    for cycle in complete:
        for part in cycle['parts']:
            sections.setdefault(part['section'], []).append(part)
    totals = [{key: sum(p[key] for p in row['parts'])
               for key in ('wall_s', 'thread_cpu_s')} for row in complete]
    return {'complete_cycles': len(complete),
            'partial_cycles': sum(not row['complete'] for row in timing.cycles),
            'stages': dict(Counter(row['stage'] for row in complete)),
            'cycle': {key: distributions(totals, key) for key in ('wall_s', 'thread_cpu_s')},
            'sections': {name: {key: distributions(rows, key)
                               for key in ('wall_s', 'thread_cpu_s')}
                         for name, rows in sections.items()}}


def run_probe(station, output, *, cycles=100, collect_timing=True, candidate_path=None):
    # Import before process measurements; import time is not a control-cycle cost.
    import evaluate_station
    import run_visual_grasp
    from route_policy import BASELINE_SOURCE

    timing = EpisodeTiming()
    count = 0
    original_episode = run_visual_grasp.run_physical_episode

    def measured_episode(*args, **kwargs):
        original_cancel = kwargs.get('cancel_check')
        original_progress = kwargs.get('progress_callback')

        def check_cancel():
            if original_cancel is not None:
                original_cancel()
            if cycles is not None and count >= cycles:
                raise DiagnosticCycleLimit('diagnostic_cycle_limit')

        def progress(row):
            nonlocal count
            if original_progress is not None:
                original_progress(row)
            count += 1

        kwargs.update(cancel_check=check_cancel, progress_callback=progress,
                      timing=timing if collect_timing else None)
        return original_episode(*args, **kwargs)

    before = host_snapshot()
    usage0 = resource.getrusage(resource.RUSAGE_SELF)
    child0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.perf_counter()
    run_visual_grasp.run_physical_episode = measured_episode
    try:
        evaluator_code = evaluate_station.evaluate(
            station, output, candidate_path=candidate_path or BASELINE_SOURCE)
    finally:
        run_visual_grasp.run_physical_episode = original_episode
    wall_s = time.perf_counter()-started
    usage1 = resource.getrusage(resource.RUSAGE_SELF)
    child1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    after = host_snapshot()
    evaluation = json.loads((output/'evaluation.json').read_text())
    report_path = output/evaluation['run_id']/'episode/report.json'
    report = json.loads(report_path.read_text()) if report_path.is_file() else {}
    truncated = report.get('error_type') == 'DiagnosticCycleLimit'
    result = {
        'schema': 'so101.episode-timing-probe.v1',
        'mode': ('diagnostic_truncated' if truncated else
                 'diagnostic_original_termination' if report else 'diagnostic_not_run'),
        'physical_success': None,
        'scope': 'actual observed stages only; no whole-task/50Hz or slowdown-cause inference',
        'requested_cycles': cycles, 'observed_rows': count,
        'timing_enabled': collect_timing,
        'original_evaluation': str(output/'evaluation.json'),
        'original_verdict': evaluation['verdict'], 'original_exit_code': evaluator_code,
        'original_failure_reason': evaluation['failure_reason'],
        'run_id': evaluation['run_id'],
        'entrypoint_argv': sys.argv,
        'simulation_s': report.get('simulation_s'),
        'safety_stop': report.get('safety_stop'),
        'video_recording': report.get('video_recording'),
        'evaluation_interval': {'scope': 'evaluate() only; excludes imports and probe report serialization',
                    'wall_s': wall_s,
                    'self_cpu_s': usage1.ru_utime+usage1.ru_stime-usage0.ru_utime-usage0.ru_stime,
                    'children_cpu_s': child1.ru_utime+child1.ru_stime-child0.ru_utime-child0.ru_stime},
        'full_process': {'wall_s': None, 'cpu_s': None,
                         'note': 'Requires an external subprocess measurement; not inferred from this interval'},
        'host_before': before, 'host_after': after,
        'summary': summarize(timing), 'timing': timing.report(),
    }
    serialized = json.dumps(result, indent=2, allow_nan=False)+'\n'
    (output/evaluation['run_id']/'timing-probe.json').write_text(serialized)
    (output/'timing-probe.json').write_text(serialized)
    print(json.dumps({key: result[key] for key in
                      ('mode', 'run_id', 'observed_rows', 'simulation_s', 'evaluation_interval', 'summary')},
                     ensure_ascii=False), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--station', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--candidate', type=Path,
                        help='Explicit route source; diagnostics default to original baseline.py')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--cycles', type=int, default=100)
    mode.add_argument('--full-episode', action='store_true',
                      help='Observe original termination under unchanged 90sim/120wall limits')
    parser.add_argument('--no-timing', action='store_true', help='Uninstrumented transparency control')
    args = parser.parse_args()
    if args.cycles < 1:
        parser.error('--cycles must be positive')
    result = run_probe(args.station.resolve(), args.output_dir.resolve(),
                       cycles=None if args.full_episode else args.cycles,
                       collect_timing=not args.no_timing, candidate_path=args.candidate)
    if args.full_episode:
        return result['original_exit_code']
    return 0 if result['mode'] == 'diagnostic_truncated' and result['observed_rows'] == args.cycles else 1


if __name__ == '__main__':
    raise SystemExit(main())
