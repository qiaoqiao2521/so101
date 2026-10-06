"""Bounded discrete checks of six-joint reference configurations.

The arm uses five-dimensional L2 spacing. The jaw has its own spacing.
These sampled straight chords do not certify continuous or physical motion.
Joint limits and geometry remain the supplied validity callback's responsibility.
"""

import math
from numbers import Integral


def _configuration(values, name):
    try:
        result = [float(value) for value in values]
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must contain six finite joint angles") from error
    if len(result) != 6 or not all(math.isfinite(value) for value in result):
        raise ValueError(f"{name} must contain six finite joint angles")
    return result


def _resolution(value, name):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be positive and finite")
    return value


def _segments(length, resolution):
    if length <= resolution:
        return 1
    # Protect exact-multiple boundaries from a rounded-down total length.
    # Integer ratios also avoid overflow when the requested spacing is tiny.
    outward = math.nextafter(length, math.inf)
    if not math.isfinite(outward):
        return None
    numerator, denominator = outward.as_integer_ratio()
    step_numerator, step_denominator = resolution.as_integer_ratio()
    top, bottom = numerator * step_denominator, denominator * step_numerator
    return (top + bottom - 1) // bottom


def validate_configuration_path(startq6, endq6, valid, *, arm_resolution_rad=.005,
                                jaw_resolution_rad=.002, max_samples=4096):
    """Check a sampled q6 chord, preserving both supplied endpoints.

    A budget rejection invokes no callback. No samples are dropped to fit.
    Malformed inputs raise; callback exceptions propagate to the caller.
    Reports contain only JSON-compatible scalars, lists and None.
    """
    start = _configuration(startq6, 'startq6')
    end = _configuration(endq6, 'endq6')
    arm_resolution = _resolution(arm_resolution_rad, 'arm_resolution_rad')
    jaw_resolution = _resolution(jaw_resolution_rad, 'jaw_resolution_rad')
    if not callable(valid):
        raise TypeError('valid must be callable')
    if isinstance(max_samples, bool) or not isinstance(max_samples, Integral) or max_samples <= 0:
        raise ValueError('max_samples must be a positive integer')
    max_samples = int(max_samples)
    report = {'valid': False, 'checked_states': 0, 'reason': None,
              'arm_resolution_rad': arm_resolution, 'jaw_resolution_rad': jaw_resolution,
              'max_samples': max_samples, 'required_states': None,
              'max_arm_step_rad': 0., 'max_jaw_step_rad': 0.,
              'invalid_state': None, 'invalid_sample_index': None}
    arm_length, jaw_length = math.dist(start[:5], end[:5]), abs(end[5] - start[5])
    if not all(math.isfinite(value) for value in (arm_length, jaw_length)):
        report['reason'] = 'nonfinite_path_length'
        return report
    arm_segments = _segments(arm_length, arm_resolution)
    jaw_segments = _segments(jaw_length, jaw_resolution)
    if arm_segments is None or jaw_segments is None:
        report['reason'] = 'nonfinite_path_length'
        return report
    segments = max(arm_segments, jaw_segments)
    report['required_states'] = segments + 1
    if segments + 1 > max_samples:
        report['reason'] = 'sample_budget_exceeded'
        return report
    states = [start.copy()]
    for index in range(1, segments):
        alpha = index / segments
        states.append([a + (b - a) * alpha for a, b in zip(start, end)])
    states.append(end.copy())
    spacing_failure = None
    for index, (first, second) in enumerate(zip(states, states[1:]), 1):
        arm_step = math.dist(first[:5], second[:5])
        jaw_step = abs(second[5] - first[5])
        report['max_arm_step_rad'] = max(report['max_arm_step_rad'], arm_step)
        report['max_jaw_step_rad'] = max(report['max_jaw_step_rad'], jaw_step)
        if not all(math.isfinite(value) for value in (arm_step, jaw_step)):
            report['reason'] = 'nonfinite_sample_spacing'
            return report
        if spacing_failure is None and (arm_step > arm_resolution or jaw_step > jaw_resolution):
            spacing_failure = index
    if spacing_failure is not None:
        report.update(reason='sample_spacing_exceeded', invalid_sample_index=spacing_failure,
                      invalid_state=states[spacing_failure].copy())
        return report
    for index, state in enumerate(states):
        report['checked_states'] += 1
        if not bool(valid(state.copy())):
            report.update(reason='invalid_state', invalid_sample_index=index,
                          invalid_state=state.copy())
            return report
    report.update(valid=True, reason='clear')
    return report
