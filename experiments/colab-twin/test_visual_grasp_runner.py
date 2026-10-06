"""Gate failures must prevent physics and final-test reuse."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from run_visual_grasp import check_phase_prerequisites, load_protocol


class PhaseAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.code={'visual_localization.py':'vision','run_visual_grasp.py':'runner'}

    def report(self,name,**change):
        folder=self.root/name; folder.mkdir()
        value={'passed':True,'complete':True,'protocol_sha256':'protocol','source_sha256':'model','code_sha256':self.code}
        value.update(change)
        (folder/'report.json').write_text(json.dumps(value))

    def check(self,phase='p3',variant='baseline',model='model'):
        with patch('run_visual_grasp.source_hashes',return_value=self.code),patch('run_visual_grasp.digest',return_value='vision'):
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


if __name__=='__main__':unittest.main()
