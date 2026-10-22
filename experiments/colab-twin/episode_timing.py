"""Optional exclusive wall/main-thread CPU measurements of the original loop."""
from __future__ import annotations

import time


class EpisodeTiming:
    def __init__(self, *, clock=None):
        self.clock = clock or (lambda: (time.perf_counter_ns(), time.thread_time_ns()))
        self.cycles = []
        self.lifecycle = []
        self.active = None
        self.previous = None

    def start(self):
        self.previous = self.clock()

    def mark(self, section):
        current = self.clock()
        wall, cpu = (current[i]-self.previous[i] for i in range(2))
        row = {'section': section, 'wall_s': wall/1e9, 'thread_cpu_s': cpu/1e9}
        destination = self.lifecycle if self.active is None else self.active['parts']
        destination.append(row)
        self.previous = current

    def begin_cycle(self, elapsed_s):
        self.active = {'sim_start_s': elapsed_s, 'parts': []}

    def end_cycle(self, stage, elapsed_s):
        self.mark('loop_tail')
        self.active.update(stage=stage, sim_end_s=elapsed_s, complete=True)
        self.cycles.append(self.active)
        self.active = None

    def begin_cleanup(self):
        if self.active is not None:
            self.mark('interrupted_cycle')
            self.active.update(stage='interrupted', complete=False)
            self.cycles.append(self.active)
            self.active = None
        else:
            self.mark('loop_exit')

    def report(self):
        return {'clock': 'perf_counter_ns / thread_time_ns',
                'cpu_scope': 'calling thread only; excludes planning threads and encoder children',
                'intervals': 'exclusive successive boundaries; instrumentation overhead is included',
                'cycles': self.cycles, 'lifecycle': self.lifecycle}
