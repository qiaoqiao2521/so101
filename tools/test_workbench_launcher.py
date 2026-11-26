"""Exercise the real shell dispatch in isolated checkout fixtures, without devices."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1]


class WorkbenchLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='so101 launcher ')
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.project = self.parent / 'so101 checkout'
        (self.project / 'tools').mkdir(parents=True)
        for name in ('so101.sh', 'tools/workbench.sh'):
            shutil.copyfile(SOURCE / name, self.project / name)
        self.env = os.environ.copy()
        for key in ('WORKBENCH_ROOT', 'FISHBOT_ROOT', 'SO101_ROOT', 'SO101_PYTHON'):
            self.env.pop(key, None)
        self.env['LAUNCHER_TEST_PYTHON'] = sys.executable

    def workbench(self, name='fishbot-ros2-slam-tools', exit_code=0):
        target = self.parent / name
        (target / 'apps/fishbot-control-station').mkdir(parents=True)
        (target / 'fishbot.sh').write_text(
            '#!/usr/bin/env bash\n'
            'exec "$LAUNCHER_TEST_PYTHON" "$(dirname -- "$0")/capture.py" "$@"\n',
            encoding='utf-8')
        (target / 'capture.py').write_text(
            'import json, os, sys\n'
            'print(json.dumps({"args": sys.argv[1:], '
            '"root": os.environ.get("SO101_ROOT"), '
            '"python": os.environ.get("SO101_PYTHON"), '
            f'"selected": {str(target)!r}'
            f'}}))\nsys.exit({exit_code})\n',
            encoding='utf-8')
        return target

    def run_launcher(self, *args, **env):
        return subprocess.run(['bash', str(self.project / 'so101.sh'), *args],
                              cwd=self.parent, env={**self.env, **env},
                              text=True, capture_output=True, timeout=10)

    def test_help_needs_no_checkout_or_runtime(self):
        result = self.run_launcher('workbench', 'help')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('WORKBENCH_ROOT', result.stdout)

    def test_missing_workbench_has_actionable_error(self):
        result = self.run_launcher('doctor')
        self.assertEqual(result.returncode, 2)
        self.assertIn('WORKBENCH_ROOT=', result.stderr)

    def test_sibling_default_starts_existing_workbench_and_sets_own_root(self):
        self.workbench()
        result = self.run_launcher('workbench', SO101_ROOT='/unrelated/checkout')
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        self.assertEqual(actual['args'], ['workbench', 'start'])
        self.assertEqual(actual['root'], str(self.project))

    def test_explicit_app_directory_preserves_python_and_argument_boundaries(self):
        target = self.workbench('configured checkout')
        result = self.run_launcher('workbench', 'start', '--host', '127.0.0.1',
                                   '--label', 'a value with spaces',
                                   WORKBENCH_ROOT=str(target / 'apps/fishbot-control-station'),
                                   SO101_PYTHON='/configured/python with spaces')
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        self.assertEqual(actual['args'], ['workbench', 'start', '--host', '127.0.0.1',
                                         '--label', 'a value with spaces'])
        self.assertEqual(actual['python'], '/configured/python with spaces')

    def test_fishbot_root_supports_relative_paths_and_doctor_alias(self):
        target = self.workbench('chosen fishbot')
        result = self.run_launcher('doctor', '--json', FISHBOT_ROOT=target.name)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['args'], ['workbench', 'doctor', '--json'])

    def test_workbench_root_takes_precedence_and_propagates_failure(self):
        selected = self.workbench('selected checkout', exit_code=23)
        other = self.workbench()
        result = self.run_launcher('workbench', 'doctor', WORKBENCH_ROOT=str(selected),
                                   FISHBOT_ROOT=str(other))
        self.assertEqual(result.returncode, 23)
        self.assertEqual(json.loads(result.stdout)['selected'], str(selected))

    def test_invalid_explicit_root_does_not_silently_use_sibling(self):
        self.workbench()
        result = self.run_launcher('doctor', WORKBENCH_ROOT=str(self.parent / 'missing'))
        self.assertEqual(result.returncode, 2)
        self.assertIn('configured workbench', result.stderr)
        self.assertEqual(result.stdout, '')

    def test_unknown_command_does_not_delegate(self):
        self.workbench()
        result = self.run_launcher('workbench', 'run-robot')
        self.assertEqual(result.returncode, 2)
        self.assertIn('Unknown workbench command', result.stderr)


if __name__ == '__main__':
    unittest.main()
