"""Clock semantics and incomplete-cycle accounting, independent of MuJoCo."""
import unittest
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from episode_timing import EpisodeTiming
from probe_episode_timing import distributions, run_probe, summarize


class TimingTests(unittest.TestCase):
    def test_exclusive_intervals_and_thread_cpu_are_not_process_cpu(self):
        values = iter(((0, 0), (100, 40), (120, 45), (200, 60), (210, 62), (230, 67)))
        timing = EpisodeTiming(clock=lambda: next(values))
        timing.start()
        timing.mark('initialization')
        timing.begin_cycle(0.)
        timing.mark('controller')
        timing.mark('physics_and_guards')
        timing.end_cycle('approach', .02)
        timing.begin_cleanup()
        result = summarize(timing)
        self.assertEqual(result['complete_cycles'], 1)
        self.assertEqual(result['stages'], {'approach': 1})
        self.assertAlmostEqual(result['cycle']['wall_s']['total_s'], 110/1e9)
        self.assertAlmostEqual(result['cycle']['thread_cpu_s']['total_s'], 22/1e9)
        self.assertAlmostEqual(sum(r['wall_s'] for r in timing.lifecycle), 120/1e9)
        self.assertEqual(timing.cycles[0]['sim_end_s'], .02)

    def test_cancelled_partial_cycle_is_retained_but_not_in_steady_statistics(self):
        values = iter(((0, 0), (5, 2), (7, 3), (17, 8)))
        timing = EpisodeTiming(clock=lambda: next(values))
        timing.start()
        timing.mark('initialization')
        timing.begin_cycle(0.)
        timing.mark('controller')
        timing.begin_cleanup()
        result = summarize(timing)
        self.assertEqual(result['complete_cycles'], 0)
        self.assertEqual(result['partial_cycles'], 1)
        self.assertEqual(result['cycle']['wall_s']['total_s'], 0.)
        self.assertEqual(timing.cycles[0]['parts'][-1]['section'], 'interrupted_cycle')

    def test_cleanup_without_a_started_cycle_is_supported(self):
        values = iter(((0, 0), (30, 10)))
        timing = EpisodeTiming(clock=lambda: next(values))
        timing.start()
        timing.begin_cleanup()
        self.assertEqual(timing.lifecycle[0]['section'], 'loop_exit')
        self.assertEqual(summarize(timing)['cycle']['wall_s']['median_s'], None)

    def test_quantiles_use_all_samples_and_do_not_hide_slow_pairs(self):
        rows = [{'wall_s': float(n)} for n in range(1, 101)]
        result = distributions(rows, 'wall_s')
        self.assertEqual(result['median_s'], 50.5)
        self.assertEqual(result['p95_s'], 95.)
        self.assertEqual(result['max_s'], 100.)

    def test_original_validation_failure_is_unscored_without_missing_report_crash(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            station = root/'invalid.json'
            station.write_text('{}')
            result = run_probe(station, root/'output')
            self.assertEqual(result['mode'], 'diagnostic_not_run')
            self.assertEqual(result['original_verdict'], 'unscored')
            self.assertIsNone(result['physical_success'])
            self.assertIsNone(result['full_process']['wall_s'])
            archived = root/'output'/result['run_id']/'timing-probe.json'
            self.assertEqual(json.loads(archived.read_text())['observed_rows'], 0)

    def test_probe_restores_original_entrypoint_when_evaluator_raises(self):
        import run_visual_grasp
        from route_policy import BASELINE_SOURCE
        original = run_visual_grasp.run_physical_episode
        with tempfile.TemporaryDirectory() as folder:
            for selected in (None, Path(folder)/'candidate.py'):
                with self.subTest(selected=selected):
                    with patch('evaluate_station.evaluate',
                               side_effect=RuntimeError('source error')) as evaluate:
                        with self.assertRaisesRegex(RuntimeError, 'source error'):
                            run_probe(Path(folder)/'station.json', Path(folder)/'output',
                                      candidate_path=selected)
                    self.assertEqual(evaluate.call_args.kwargs['candidate_path'],
                                     selected or BASELINE_SOURCE)
                    self.assertIs(run_visual_grasp.run_physical_episode, original)
        self.assertIs(run_visual_grasp.run_physical_episode, original)


if __name__ == '__main__':
    unittest.main()
