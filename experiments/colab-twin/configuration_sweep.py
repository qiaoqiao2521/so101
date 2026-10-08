"""Bounded discrete checks of six-joint reference configurations.

The arm uses five-dimensional L2 spacing. The jaw has its own spacing.
These sampled straight chords do not certify continuous or physical motion.
Joint limits and geometry remain the supplied validity callback's responsibility.
"""

import math
import struct
from dataclasses import dataclass, field
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


def _immutable_context(value):
    """Own context values; floating-point identity includes signed zero."""
    if isinstance(value, (tuple, list)):
        return tuple(_immutable_context(item) for item in value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError('Sweep context floats must be finite')
        return ('float64', struct.pack('!d', value))
    if value is None or isinstance(value, (bytes, str, int, bool)):
        return value
    raise TypeError('Sweep context requires owned scalar values and tuples')


@dataclass(frozen=True, eq=False)
class SweepBinding:
    """Process-local arm guard ownership; not a continuous-motion certificate.

    Context records phase-specific hypotheses. Their separate guards still run.
    Object references bind ownership only; no simulation data is shared here.
    """
    owner: object = field(repr=False)
    checker: object = field(repr=False)
    model: object = field(repr=False)
    stage: str
    jaw_intent_rad: float
    context: tuple = ()
    guard_scope: str = 'arm_q6_chord'
    _jaw_bits: bytes = field(init=False, repr=False)

    def __post_init__(self):
        if self.owner is None or self.checker is None or self.model is None:
            raise ValueError('Sweep ownership requires owner, checker and model')
        if not isinstance(self.stage, str) or not self.stage:
            raise ValueError('Sweep stage requires a nonempty string')
        if self.guard_scope != 'arm_q6_chord':
            raise ValueError('Only the discrete arm q6 chord guard is supported')
        jaw = float(self.jaw_intent_rad)
        if not math.isfinite(jaw):
            raise ValueError('Sweep jaw intent must be finite')
        if not isinstance(self.context, tuple):
            raise TypeError('Sweep context must be a tuple')
        object.__setattr__(self, 'jaw_intent_rad', jaw)
        object.__setattr__(self, '_jaw_bits', struct.pack('!d', jaw))
        object.__setattr__(self, 'context', _immutable_context(self.context))

    def matches(self, other):
        return (isinstance(other, SweepBinding)
                and self.owner is other.owner and self.checker is other.checker
                and self.model is other.model and self.stage == other.stage
                and self._jaw_bits == other._jaw_bits
                and self.context == other.context and self.guard_scope == other.guard_scope)


@dataclass(frozen=True)
class ConfigurationSweepRequest:
    startq6: tuple
    endq6: tuple
    binding: SweepBinding
    arm_resolution_rad: float = .005
    jaw_resolution_rad: float = .002
    max_samples: int = 4096

    def __post_init__(self):
        object.__setattr__(self, 'startq6', tuple(_configuration(self.startq6, 'startq6')))
        object.__setattr__(self, 'endq6', tuple(_configuration(self.endq6, 'endq6')))
        if not isinstance(self.binding, SweepBinding):
            raise TypeError('Sweep request requires a SweepBinding')
        if struct.pack('!d', self.endq6[5]) != self.binding._jaw_bits:
            raise ValueError('Sweep jaw intent must match the requested endpoint')
        for name in ('arm_resolution_rad', 'jaw_resolution_rad'):
            object.__setattr__(self, name, _resolution(getattr(self, name), name))
        if (isinstance(self.max_samples, bool) or not isinstance(self.max_samples, Integral)
                or self.max_samples <= 0):
            raise ValueError('max_samples must be a positive integer')
        object.__setattr__(self, 'max_samples', int(self.max_samples))


class ConfigurationSweepInvocation:
    """Execute and consume one frozen request once, without cache or retries."""
    def __init__(self, startq6, endq6, *, binding, arm_resolution_rad=.005,
                 jaw_resolution_rad=.002, max_samples=4096):
        self._request = ConfigurationSweepRequest(
            startq6, endq6, binding, arm_resolution_rad, jaw_resolution_rad, max_samples)
        self._state = 'new'
        self._report = None

    @property
    def request(self):
        return self._request

    @property
    def state(self):
        return self._state

    def execute(self, valid):
        if self._state != 'new':
            raise RuntimeError('Sweep invocation has already started')
        self._state = 'running'
        request = self._request
        try:
            self._report = validate_configuration_path(
                request.startq6, request.endq6, valid,
                arm_resolution_rad=request.arm_resolution_rad,
                jaw_resolution_rad=request.jaw_resolution_rad, max_samples=request.max_samples)
        except BaseException:
            self._state = 'failed'
            raise
        self._state = 'completed'

    def consume(self, binding):
        if self._state != 'completed':
            raise RuntimeError('Sweep result is unavailable or already consumed')
        if not self._request.binding.matches(binding):
            self._state = 'failed'
            self._report = None
            raise RuntimeError('Sweep result ownership or context changed')
        report = self._report
        self._report = None
        self._state = 'consumed'
        return report
