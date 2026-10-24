"""Read-only skill evidence from the original physical task monitor.

A grasp event records a historical postcondition, not whole-attempt success.
The caller owns task association and must observe only after monitor.update.
"""
from copy import deepcopy


def deliver_evidence(callback, snapshot):
    """The display may edit its snapshot; the saved physical evidence stays owned."""
    callback(deepcopy(snapshot))


class PhysicalSkillEvidence:
    """Capture the first original-monitor grasp confirmation without judging it."""

    _OUTCOME_FIELDS = (
        'passed', 'error_type', 'failure_reason', 'safety_stop',
        'planner_cleanup_error', 'planner_cleanup_errors',
    )

    def __init__(self):
        self._grasp = {
            'postcondition_met': False,
            'first_met_elapsed_s': None,
            'evidence': None,
        }
        self._attempt = dict.fromkeys(self._OUTCOME_FIELDS)
        self._events = []
        self._count = 0
        self._last_elapsed_s = None

    def observe(self, row, monitor_status, baseline_z):
        """Return one detached event only on first exact monitor confirmation."""
        index = self._count
        self._count += 1
        elapsed = row.get('elapsed_s')
        self._last_elapsed_s = float(elapsed) if elapsed is not None else None
        if self._grasp['postcondition_met'] or monitor_status.get('grasp_success') is not True:
            return None

        object_z = row.get('object_z_m')
        proof = deepcopy({
            'source': 'PhysicalTaskMonitor.update',
            'elapsed_s': self._last_elapsed_s,
            'time_s': row.get('time_s'),
            'stage': row.get('stage'),
            'tip_forces_n': row.get('tip_forces_n'),
            'lift_m': (float(object_z) - float(baseline_z)
                       if object_z is not None and baseline_z is not None else None),
            'floor_contact': row.get('floor_contact'),
            'place_floor_contact': row.get('place_floor_contact'),
            'hold_duration_s': monitor_status.get('hold_duration_s'),
        })
        self._grasp = {
            'postcondition_met': True,
            'first_met_elapsed_s': self._last_elapsed_s,
            'evidence': proof,
        }
        event = {
            'skill': 'Grasp',
            'event': 'postcondition_met',
            'observation_index': index,
            'elapsed_s': self._last_elapsed_s,
            'evidence': deepcopy(proof),
        }
        self._events.append(event)
        return deepcopy(event)

    def finalize(self, report):
        """Copy the original outcome, including any later failure or cleanup error."""
        self._attempt = deepcopy({key: report.get(key) for key in self._OUTCOME_FIELDS})
        return self.report()

    def report(self):
        """Return an isolated snapshot; an unfinished attempt has unknown outcome."""
        return deepcopy({
            'schema': 'so101.physical-skill-evidence.v1',
            'scope': 'observation_only',
            'observations': {'count': self._count, 'last_elapsed_s': self._last_elapsed_s},
            'grasp': self._grasp,
            'attempt': self._attempt,
            'events': self._events,
        })
