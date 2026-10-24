"""Optional operator release from the existing safe hold before Carry.

The controller decides when this gate is eligible. This module only observes
q6, elapsed time and an explicitly supplied marker; it never drives physics.
"""
from copy import deepcopy
from pathlib import Path
import warnings


class CarryGate:
    """Wait for a resume marker created after the first eligible hold call."""

    def __init__(self, resume_file: Path, *, on_change=None):
        self.resume_file = Path(resume_file)
        self.on_change = on_change
        self._state = 'pending'
        self._waiting_since = self._released_at = self._ended_at = None
        self._last_elapsed = None
        self._events = []
        self._attempt = None
        self._callback_errors = []

    def _changed(self):
        if self.on_change is None:
            return
        try:
            self.on_change(self.report())
        except Exception as error:
            self._callback_errors.append({'error_type': type(error).__name__,
                                          'error': str(error)})
            try:
                warnings.warn('WARNING carry gate observation callback failed: ' + str(error))
            except Exception as warning_error:
                # A display warning must not become a motion failure when the
                # host treats warnings as errors or its warning sink fails.
                self._callback_errors[-1]['warning_error_type'] = type(warning_error).__name__

    def __call__(self, q6, elapsed) -> bool:
        if self._state == 'ended':
            raise RuntimeError('carry_gate_ended')
        if self._state == 'released':
            return True
        self._last_elapsed = float(elapsed)
        if self._state == 'pending':
            if self.resume_file.exists():
                self._events.append({'event': 'rejected_early_resume',
                                     'elapsed_s': self._last_elapsed,
                                     'q6': [float(value) for value in q6]})
                self._changed()
                raise RuntimeError('carry_resume_before_waiting')
            self._state = 'waiting'
            self._waiting_since = self._last_elapsed
            self._events.append({'event': 'waiting', 'elapsed_s': self._last_elapsed,
                                 'q6': [float(value) for value in q6]})
            self._changed()
            return False
        if not self.resume_file.exists():
            return False
        self._state = 'released'
        self._released_at = self._last_elapsed
        self._events.append({'event': 'released', 'elapsed_s': self._last_elapsed,
                             'q6': [float(value) for value in q6]})
        self._changed()
        return True

    def report(self):
        end = (self._released_at if self._released_at is not None else
               self._ended_at if self._ended_at is not None else self._last_elapsed)
        wait = (max(0., end-self._waiting_since)
                if self._waiting_since is not None and end is not None else 0.)
        return deepcopy({'mode': 'hold-before-carry', 'state': self._state,
                         'resume_file': str(self.resume_file),
                         'waiting_since_s': self._waiting_since,
                         'released_at_s': self._released_at,
                         'ended_at_s': self._ended_at, 'wait_s': wait,
                         'events': self._events, 'attempt': self._attempt,
                         'callback_errors': self._callback_errors})

    def finalize(self, original_report):
        """Retain history and the original outcome after normal case cleanup."""
        if self._state == 'ended':
            return self.report()
        self._ended_at = original_report.get('simulation_s')
        self._attempt = deepcopy({key: original_report.get(key) for key in
                                  ('passed', 'error_type', 'failure_reason', 'error',
                                   'cancelled', 'safety_stop', 'planner_cleanup_error',
                                   'planner_cleanup_errors')})
        self._events.append({'event': 'ended', 'elapsed_s': self._ended_at,
                             'previous_state': self._state,
                             'reason': self._attempt['failure_reason'],
                             'error_type': self._attempt['error_type']})
        self._state = 'ended'
        self._changed()
        return self.report()
