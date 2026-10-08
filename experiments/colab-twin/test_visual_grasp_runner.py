import itertools
"""Gate failures must prevent physics and final-test reuse."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from run_visual_grasp import (check_phase_prerequisites, load_protocol, source_hashes, digest,
                              record_collision_backend, finalize_episode_video, main,
                              run_physical_phase, run_physical_episode)


class PhaseAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.code={'visual_localization.py':'vision','run_visual_grasp.py':'runner'}
        self.native={'kernel_sha256':'kernel','library_sha256':'library',
                     'compiler_identity_sha256':'compiler','flags_sha256':'flags'}

    def report(self,name,**change):
        folder=self.root/name; folder.mkdir()
        value={'passed':True,'complete':True,'protocol_sha256':'protocol','source_sha256':'model',
               'code_sha256':self.code,'native_binding':self.native}
        value.update(change)
        (folder/'report.json').write_text(json.dumps(value))

    def check(self,phase='p3',variant='baseline',model='model'):
        with patch('run_visual_grasp.source_hashes',return_value=self.code), \
                patch('run_visual_grasp.digest',return_value='vision'), \
                patch('run_visual_grasp.native_binding',return_value=self.native):
            check_phase_prerequisites(self.root,phase,variant,'protocol',model)

    def test_failed_or_incomplete_perception_blocks_physics(self):
        self.report('p0',complete=False)
        with self.assertRaisesRegex(ValueError,'incomplete'): self.check('p1')

    def test_changed_source_blocks_physics(self):
        self.report('p0')
        with self.assertRaisesRegex(ValueError,'Source model'): self.check('p1',model='different')

    def test_changed_perception_cannot_reuse_p0(self):
        self.report('p0',code_sha256={'visual_localization.py':'different'})
        with self.assertRaisesRegex(ValueError,'Perception changed'): self.check('p1')

    def test_development_failure_blocks_final(self):
        self.report('p0');self.report('p1-baseline');self.report('p2-baseline',passed=False)
        with self.assertRaisesRegex(ValueError,'incomplete'): self.check()
        self.assertFalse((self.root/'final-test-started.json').exists())

    def test_final_test_is_one_shot_and_bound_to_code(self):
        self.report('p0');self.report('p1-baseline');self.report('p2-baseline')
        self.check()
        with self.assertRaises(FileExistsError):self.check()

    def test_development_result_cannot_validate_changed_controller(self):
        self.report('p0');self.report('p1-baseline');self.report('p2-baseline',code_sha256={'visual_localization.py':'vision','run_visual_grasp.py':'changed'})
        with self.assertRaisesRegex(ValueError,'Implementation changed'):self.check()

    def test_protocol_cannot_change_between_phases(self):
        p=self.root/'protocol.json';p.write_text('{"version":1}')
        load_protocol(self.root)
        p.write_text('{"version":2}')
        with self.assertRaisesRegex(ValueError,'Protocol changed'):load_protocol(self.root)

    def test_revision_requires_recorded_failed_baseline(self):
        self.report('p0')
        with self.assertRaisesRegex(ValueError,'recorded development'):self.check('p1','revision1')
        (self.root/'revision-reason.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'No failed baseline'):self.check('p1','revision1')

    def test_native_kernel_participates_in_source_binding(self):
        source = Path(__file__).with_name('support_kernel.cpp')
        self.assertEqual(source_hashes()['support_kernel.cpp'], digest(source))

    def test_native_runtime_change_blocks_final_without_consuming_test_lock(self):
        self.report('p0');self.report('p1-baseline')
        self.report('p2-baseline',native_binding=dict(self.native, library_sha256='other'))
        with self.assertRaisesRegex(ValueError, 'Native collision runtime changed'):
            self.check()
        self.assertFalse((self.root/'final-test-started.json').exists())

    def test_case_provenance_failure_preserves_report_and_closes_handle(self):
        checker = Mock(distance_kind='certified_lower_bound', margin_m=.001)
        status = {'passed':True, 'failure_reason':None}
        with patch('run_visual_grasp.library_metadata', side_effect=RuntimeError('disk identity changed')):
            record_collision_backend(status, checker)
        self.assertFalse(status['passed'])
        self.assertTrue(status['safety_stop'])
        self.assertEqual(status['failure_reason'], 'native_runtime_provenance_invalid')
        self.assertEqual(status['native_provenance_error'], 'disk identity changed')
        checker.native.close.assert_called_once_with()

    def test_case_provenance_failure_retains_prior_physical_failure(self):
        checker = Mock(distance_kind='certified_lower_bound', margin_m=.001)
        status = {'passed':False, 'failure_reason':'physical_task_not_complete'}
        with patch('run_visual_grasp.library_metadata', side_effect=RuntimeError('unavailable')):
            record_collision_backend(status, checker)
        self.assertEqual(status['failure_reason'], 'physical_task_not_complete')
        checker.native.close.assert_called_once_with()


class VideoFinalizationTests(unittest.TestCase):
    def writer(self, **changes):
        receipt=dict(complete=True,captured_frames=10,encoded_frames=10)
        receipt.update(changes)
        return Mock(report=Mock(return_value=receipt))

    def test_no_video_preserves_case(self):
        status={'passed':True}
        finalize_episode_video(None,status,0)
        self.assertEqual(status,{'passed':True})

    def test_complete_video_preserves_physical_success(self):
        writer=self.writer();status={'passed':True,'failure_reason':None}
        finalize_episode_video(writer,status,10)
        self.assertTrue(status['passed']);writer.close.assert_called_once_with()
        self.assertEqual(status['video_recording']['encoded_frames'],10)

    def test_bad_counts_or_incomplete_receipt_fail_successful_case(self):
        for change in ({'complete':False},{'captured_frames':9},{'encoded_frames':9}):
            with self.subTest(change=change):
                status={'passed':True};finalize_episode_video(self.writer(**change),status,10)
                self.assertFalse(status['passed']);self.assertEqual(status['failure_reason'],'video_finalize_failed')

    def test_empty_receipt_cannot_pass_grasp(self):
        status={'passed':True}
        finalize_episode_video(self.writer(captured_frames=0,encoded_frames=0),status,0)
        self.assertFalse(status['passed'])

    def test_encoder_deadline_failure_is_recorded(self):
        writer=self.writer(complete=False);writer.close.side_effect=TimeoutError('video_finalize_deadline')
        status={'passed':True};finalize_episode_video(writer,status,10)
        self.assertFalse(status['passed']);self.assertEqual(status['video_error_type'],'TimeoutError')

    def test_video_failure_keeps_physical_cause(self):
        writer=self.writer(complete=False);writer.close.side_effect=RuntimeError('encode failed')
        status={'passed':False,'failure_reason':'payload_lost'}
        finalize_episode_video(writer,status,10)
        self.assertEqual(status['failure_reason'],'payload_lost');self.assertEqual(status['video_error'],'encode failed')


class RuntimeBudgetTests(unittest.TestCase):
    """Nullable cumulative limits must retain accounting and finite case limits."""
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source=self.root/'model.xml';self.source.write_text('mock source')
        self.code={'run_visual_grasp.py':'runner'}
        self.native={'kernel_sha256':'kernel','library_sha256':'library',
                     'compiler_identity_sha256':'compiler','flags_sha256':'flags'}

    def invoke_main(self, total, spent, phase='p0'):
        protocol={'total_runtime_wall_s':total,'max_sim_s':90,'max_episode_wall_s':120}
        (self.root/'protocol.json').write_text(json.dumps(protocol))
        previous={'phase':'prior','variant':'baseline','wall_s':spent,'report':'prior/report.json'}
        ledger={'spent_wall_s':spent,'runs':[previous]}
        ledger_path=self.root/'runtime-budget.json';ledger_path.write_text(json.dumps(ledger))
        args=['run_visual_grasp.py','--root',str(self.root),'--source',str(self.source),'--phase',phase]
        with patch('sys.argv',args), \
                patch('run_visual_grasp.check_phase_prerequisites') as admission, \
                patch('run_visual_grasp.source_hashes',return_value=self.code), \
                patch('run_visual_grasp.native_binding',return_value=self.native), \
                patch('run_visual_grasp.time.monotonic',side_effect=[100.,103.]), \
                patch('run_visual_grasp.run_p0',return_value={'passed':True,'complete':True}) as p0, \
                patch('run_visual_grasp.run_physical_phase',return_value={'passed':True,'complete':True}) as physical, \
                patch('builtins.print'):
            code=main()
        return code,admission,p0,physical,ledger,read_json(ledger_path)

    def test_null_protocol_remains_bound_to_checksum(self):
        path=self.root/'protocol.json';path.write_text('{"total_runtime_wall_s":null}')
        protocol,binding=load_protocol(self.root)
        self.assertIsNone(protocol['total_runtime_wall_s'])
        self.assertEqual(binding,digest(path))
        path.write_text('{"total_runtime_wall_s":9000}')
        with self.assertRaisesRegex(ValueError,'Protocol changed'):
            load_protocol(self.root)

    def test_invalid_nonfinite_total_is_not_an_unlimited_setting(self):
        for total in (float('inf'),float('-inf'),float('nan'),True,'unlimited'):
            with self.subTest(total=total):
                (self.root/'protocol.json').write_text(json.dumps({'total_runtime_wall_s':total}))
                with self.assertRaisesRegex(ValueError,'finite number or null'):
                    load_protocol(self.root)

    def test_null_total_records_spent_beyond_former_limit_for_both_phase_paths(self):
        for phase in ('p0','p1'):
            with self.subTest(phase=phase):
                code,admission,p0,physical,before,after=self.invoke_main(None,9001.,phase)
                self.assertEqual(code,0);admission.assert_called_once()
                called=p0 if phase=='p0' else physical
                called.assert_called_once();self.assertIsNone(called.call_args.args[-1])
                passed_protocol=called.call_args.args[2 if phase=='p0' else 3]
                self.assertEqual((passed_protocol['max_sim_s'],passed_protocol['max_episode_wall_s']),(90,120))
                self.assertEqual(after['runs'][:-1],before['runs'])
                self.assertEqual(after['spent_wall_s'],9004.)
                self.assertEqual(after['runs'][-1]['wall_s'],3.)
                report=self.root/('p0' if phase=='p0' else 'p1-baseline')/'report.json'
                # A strict JSON serializer rejects Infinity, including nested values.
                json.dumps(read_json(report),allow_nan=False)
                json.dumps(after,allow_nan=False)
                self.assertEqual(read_json(report)['code_sha256'],self.code)

    def test_finite_total_still_passes_remaining_phase_deadline(self):
        code,_,p0,physical,before,after=self.invoke_main(9010.,9001.)
        self.assertEqual(code,0);physical.assert_not_called()
        self.assertEqual(p0.call_args.args[-1],109.)
        self.assertEqual(after['runs'][:-1],before['runs'])
        self.assertEqual(after['spent_wall_s'],9004.)

    def test_finite_total_exhausted_at_or_above_limit_never_starts_phase(self):
        for spent in (9000.,9001.):
            with self.subTest(spent=spent):
                (self.root/'protocol.json').write_text('{"total_runtime_wall_s":9000}')
                ledger_path=self.root/'runtime-budget.json'
                ledger_path.write_text(json.dumps({'spent_wall_s':spent,'runs':[]}))
                before=ledger_path.read_bytes()
                with patch('sys.argv',['runner','--root',str(self.root),'--source',str(self.source),'--phase','p0']), \
                        patch('run_visual_grasp.check_phase_prerequisites'), \
                        patch('run_visual_grasp.run_p0') as p0:
                    with self.assertRaisesRegex(RuntimeError,'budget exhausted'):
                        main()
                p0.assert_not_called();self.assertFalse((self.root/'p0').exists())
                self.assertEqual(ledger_path.read_bytes(),before)

    def test_null_phase_keeps_full_denominator_and_safety_failure(self):
        cases=[{'id':str(i),'perturbed':i==2} for i in range(3)]
        reports=[{'case':case,'passed':i!=1,'safety_stop':i==1,'failure_reason':'unsafe' if i==1 else None,
                  'simulation_s':89.,'wall_s':1.,'pulse_steps':10 if case['perturbed'] else 0}
                 for i,case in enumerate(cases)]
        with patch('run_visual_grasp.run_physical_episode',side_effect=reports) as episode, \
                patch('run_visual_grasp.time.monotonic',return_value=1000000.),patch('builtins.print'):
            report=run_physical_phase(self.source,self.root,self.root,{'p2':cases},'p2','baseline',None)
        self.assertEqual(episode.call_count,3)
        self.assertTrue(report['complete']);self.assertTrue(report['within_budget'])
        self.assertEqual((report['planned'],report['attempted'],report['successes']),(3,3,2))
        self.assertEqual(report['safety_stop'],1);self.assertFalse(report['passed'])
        self.assertEqual(report['fully_injected'],1)

    def test_finite_phase_stops_at_exact_deadline_and_stays_incomplete(self):
        cases=[{'id':str(i),'perturbed':False} for i in range(2)]
        result={'case':cases[0],'passed':True,'safety_stop':False,'failure_reason':None,
                'simulation_s':1.,'wall_s':1.,'pulse_steps':0}
        with patch('run_visual_grasp.run_physical_episode',return_value=result) as episode, \
                patch('run_visual_grasp.time.monotonic',side_effect=[99.,100.,100.]),patch('builtins.print'):
            report=run_physical_phase(self.source,self.root,self.root,{'p2':cases},'p2','baseline',100.)
        episode.assert_called_once()
        self.assertEqual((report['planned'],report['attempted']),(2,1))
        self.assertFalse(report['complete']);self.assertFalse(report['within_budget']);self.assertFalse(report['passed'])

    def test_case_retains_120_second_cap_and_shorter_finite_phase_cap(self):
        for index,(phase_deadline,end) in enumerate(((None,220.),(300.,220.),(150.,150.))):
            with self.subTest(phase_deadline=phase_deadline):
                with patch('run_visual_grasp.time.monotonic',side_effect=itertools.chain([100.], itertools.repeat(end))), \
                        patch('run_visual_grasp.build_contact_scene',side_effect=RuntimeError('mock initialization')) as build, \
                        patch('run_visual_grasp.mujoco.mj_step') as step:
                    report=run_physical_episode(self.source,self.root/str(index),
                                                {'max_episode_wall_s':120,'max_sim_s':90},
                                                {'id':'case','perturbed':False},phase_deadline)
                build.assert_called_once();step.assert_not_called()
                self.assertFalse(report['passed']);self.assertEqual(report['failure_reason'],'wall_time_limit')
                self.assertEqual(report['simulation_s'],0.)


def read_json(path):
    return json.loads(path.read_text())


if __name__=='__main__':unittest.main()
