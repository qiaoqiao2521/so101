"""Decide whether a measured candidate earns another full physical station run.

This is review plumbing around existing reports. It never runs physics, changes a
reporter's verdict, or treats a fast failing screen as a successful task.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import statistics


@dataclass(frozen=True)
class ScreenLimits:
    min_samples: int = 3
    max_median_effect_s: float = 0.005
    max_wall_effect_s: float = 0.0

    def __post_init__(self):
        if isinstance(self.min_samples, bool) or not isinstance(self.min_samples, int) \
                or self.min_samples < 1:
            raise ValueError('min_samples requires a positive integer')
        for name in ('max_median_effect_s', 'max_wall_effect_s'):
            value = float(getattr(self, name))
            if value < 0:
                raise ValueError(f'{name} requires a nonnegative value')
            object.__setattr__(self, name, value)


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} requires a finite number')
    value = float(value)
    if not np_isfinite(value):
        raise ValueError(f'{name} requires a finite number')
    return value


def np_isfinite(value):
    return value == value and value not in (float('inf'), float('-inf'))


def screen(baseline, candidate, *, baseline_label='baseline', candidate_label='candidate',
           limits=None):
    """Screen paired local measurements without absorbing their verdict."""
    limits = ScreenLimits() if limits is None else limits
    if not isinstance(limits, ScreenLimits):
        raise TypeError('Screen limits must be immutable ScreenLimits')
    baseline, candidate = list(baseline), list(candidate)
    if len(baseline) != len(candidate) or len(baseline) < limits.min_samples:
        raise ValueError('Paired screens require equal sample counts above the minimum')
    rows = []
    for index, (left, right) in enumerate(zip(baseline, candidate), 1):
        if not isinstance(left, dict) or not isinstance(right, dict):
            raise ValueError('Each measurement requires an object')
        output_equal = left.get('output_equivalent') is True \
            and right.get('output_equivalent') is True
        baseline_s = _number(left.get('measurement_s'), 'baseline measurement_s')
        candidate_s = _number(right.get('measurement_s'), 'candidate measurement_s')
        wall_delta = candidate_s-baseline_s
        rows.append({'pair': index, 'baseline_s': baseline_s, 'candidate_s': candidate_s,
                     'effect_s': wall_delta, 'output_equal': output_equal,
                     'baseline_source': left.get('source'), 'candidate_source': right.get('source'),
                     'baseline_verdict': left.get('verdict'), 'candidate_verdict': right.get('verdict')})
    effects = [row['effect_s'] for row in rows]
    median = statistics.median(effects)
    unpassed = [row['pair'] for row in rows if row['baseline_verdict'] != 'pass'
                or row['candidate_verdict'] != 'pass']
    equal = all(row['output_equal'] for row in rows)
    if unpassed:
        decision, reason = 'reject', 'original_or_candidate_pair_not_passed'
    elif not equal:
        decision, reason = 'reject', 'outputs_are_not_byte_equivalent'
    elif median >= 0:
        decision, reason = 'reject', 'no_median_local_effect'
    elif median >= -limits.max_median_effect_s:
        decision, reason = 'reject', 'median_local_effect_below_threshold'
    elif max(effects) >= limits.max_wall_effect_s:
        decision, reason = 'inconclusive', 'pair_has_no_consistent_wall_reduction'
    else:
        decision, reason = 'eligible_for_physical_ab', 'consistent_local_effect'
    return {
        'schema': 'so101.factory-minimum-screen.v1',
        'limits': asdict(limits), 'labels': {'baseline': baseline_label, 'candidate': candidate_label},
        'pairs': rows,
        'summary': {'sample_count': len(rows), 'median_effect_s': median,
                    'min_effect_s': min(effects), 'max_effect_s': max(effects),
                    'outputs_byte_equivalent': equal, 'unpassed_pairs': unpassed},
        'decision': decision, 'reason': reason,
        'scope': ('Local screening only. eligible_for_physical_ab is not a task pass, '
                  'speedup claim, or substitute for the original 120s/90s physical evaluator.'),
    }


def _load_measurements(path):
    path = Path(path)
    value = json.loads(path.read_text())
    rows = value.get('measurements') if isinstance(value, dict) else _array_rows(value)
    if not isinstance(rows, list):
        raise ValueError(f'{path} requires a measurements array')
    result = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f'{path} measurement rows must be objects')
        copied = dict(row)
        copied.setdefault('source', str(path))
        result.append(copied)
    return result


def _array_rows(value):
    if isinstance(value, list):
        return value
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline-label', default='baseline')
    parser.add_argument('--candidate-label', default='candidate')
    parser.add_argument('--min-samples', type=int, default=3)
    parser.add_argument('--max-median-effect-s', type=float, default=.005)
    parser.add_argument('--max-wall-effect-s', type=float, default=0.)
    args = parser.parse_args()
    result = screen(
        _load_measurements(args.baseline), _load_measurements(args.candidate),
        baseline_label=args.baseline_label, candidate_label=args.candidate_label,
        limits=ScreenLimits(args.min_samples, args.max_median_effect_s, args.max_wall_effect_s))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'decision': result['decision'], 'reason': result['reason'],
                      'output': str(args.output)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
