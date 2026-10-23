"""One episode's optional cyclic-GC window; reference counting is unchanged."""
import gc
import time
import warnings


def peak_rss_kib():
    """Linux process high-water mark, including setup and measured cleanup."""
    try:
        import resource
        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (ImportError, OSError):
        return None


class DeferredGCWindow:
    def __init__(self):
        self.enabled_before = None
        self.finished = False
        self.details = None

    def begin(self):
        if self.enabled_before is not None:
            return
        self.enabled_before = gc.isenabled()
        self.details = {
            'mode': 'defer_automatic_cyclic_gc_during_control',
            'caller_enabled': self.enabled_before,
            'deferred': self.enabled_before,
            'thresholds': list(gc.get_threshold()),
            'collected_at_cleanup': None,
            'cleanup_wall_s': 0.,
            'cleanup_thread_cpu_s': 0.,
            'cleanup_error': None,
            'restored': False,
        }
        if self.enabled_before:
            gc.disable()

    def restore(self):
        """Also used by the outer episode finally if original cleanup raises."""
        if self.enabled_before is None:
            return
        if gc.isenabled() != self.enabled_before:
            (gc.enable if self.enabled_before else gc.disable)()
        self.details['restored'] = gc.isenabled() == self.enabled_before

    def finish(self, *, collect=True):
        if self.enabled_before is None or self.finished:
            return
        started, cpu = time.perf_counter(), time.thread_time()
        try:
            if self.enabled_before and collect:
                self.details['collected_at_cleanup'] = gc.collect()
        except Exception as error:
            self.details['cleanup_error'] = type(error).__name__
            warnings.warn('Optional deferred GC cleanup failed: '+type(error).__name__,
                          RuntimeWarning)
        finally:
            self.restore()
            self.finished = True
            self.details['cleanup_wall_s'] = time.perf_counter()-started
            self.details['cleanup_thread_cpu_s'] = time.thread_time()-cpu
