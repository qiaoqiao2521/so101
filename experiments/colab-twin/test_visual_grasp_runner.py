"""Gate failures must prevent physics and final-test reuse."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from run_visual_grasp import check_phase_prerequisites, load_protocol, source_hashes, digest, record_collision_backend, finalize_episode_video


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


if __name__=='__main__':unittest.main()
