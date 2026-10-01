"""Portable, offline Colab orchestration safety tests.

Run with ``python -B -m unittest test_colab -v`` from this directory. All tests
except one use only stdlib fakes. The remaining test discovers the optional installed
Colab SDK's state types, opens only an isolated temporary store, and skips when
that SDK or its state dependencies are unavailable. No test calls the network,
reads account credentials, allocates a runtime, or invokes a model.

For the official uv wheel interface, reuse an already verified uv==UV_VERSION
wheel in a disposable directory: pip install --no-index --no-deps --target TOOLS
WHEEL, then call remote_bootstrap.uv_binary(Path(TOOLS)) and run the returned
executable with --version. Use the native TOOLS/bin/uv path; importing uv or
checking for a Python console script does not prove this native layout. Keep
this wheel/install check outside the offline unit suite.
"""
import contextlib
from enum import Enum
import hashlib
import importlib.util
import io
import json
import logging
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import types
import unittest
import uuid
from unittest.mock import patch
from zipfile import ZipFile
ROOT = Path(__file__).resolve().parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


entry = module('gr00t_review_entry', 'run_colab.py')
bootstrap = module('gr00t_review_bootstrap', 'remote_bootstrap.py')
safe_cli = module('gr00t_review_safe_cli', 'colab_safe_cli.py')


def native_state_module():
    # Import the state types directly from source, without importing the CLI
    # auth/common modules or opening the user's default session store.
    try:
        package_spec = importlib.util.find_spec('colab_cli')
    except (ImportError, ValueError):
        package_spec = None
    if package_spec is None or not package_spec.submodule_search_locations:
        raise unittest.SkipTest('Optional google-colab-cli SDK is not installed')
    state_path = next((Path(directory) / 'state.py'
                       for directory in package_spec.submodule_search_locations
                       if (Path(directory) / 'state.py').is_file()), None)
    if state_path is None:
        raise unittest.SkipTest('Optional Colab SDK state source is unavailable')
    spec = importlib.util.spec_from_file_location('gr00t_review_native_state', state_path)
    value = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(value)
    except ImportError:
        raise unittest.SkipTest('Optional Colab SDK state dependencies are unavailable') from None
    return value


def result_archive(path, files, *, manifest=True, covered=None):
    """Build a small synthetic result with real size/hash declarations."""
    files = {name: value if isinstance(value, bytes) else value.encode()
             for name, value in files.items()}
    with ZipFile(path, 'w') as archive:
        for name, value in files.items():
            archive.writestr(name, value)
        if manifest:
            members = files if covered is None else covered
            archive.writestr('artifact-manifest.json', json.dumps([
                {'file': name, 'bytes': len(files[name]),
                 'sha256': hashlib.sha256(files[name]).hexdigest()}
                for name in members]))


class ArtifactContracts(unittest.TestCase):
    def test_remote_supports_parent_timeout_option(self):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'remote_bootstrap.py'), '--help'],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0)
        self.assertIn('--timeout', result.stdout,
                      'Parent launch supplies --timeout; remote parser must accept it')

    def test_exact_parent_bundle_is_accepted(self):
        with tempfile.TemporaryDirectory(prefix='gr00t-review-bundle-') as tmp:
            directory = Path(tmp)
            bundle = directory / 'bundle.zip'
            with ZipFile(bundle, 'w') as z:
                for name in entry.PUBLIC_FILES:
                    z.write(ROOT / name, name)
            with patch.object(bootstrap, 'BUNDLE', bundle):
                lock = bootstrap.unpack_bundle(directory / 'unpacked')
            self.assertEqual(lock['gr00t_revision'], bootstrap.GR00T_REVISION)

    def test_actual_bootstrap_package_is_recoverable(self):
        with tempfile.TemporaryDirectory(prefix='gr00t-review-report-') as tmp:
            directory = Path(tmp)
            artifacts = directory / 'artifacts'
            artifacts.mkdir()
            # Avoid Bootstrap.__init__, which intentionally copies a runtime
            # environment. This test uses only synthetic report metadata.
            boot = bootstrap.Bootstrap.__new__(bootstrap.Bootstrap)
            boot.token = ''
            boot.start = bootstrap.time.monotonic()
            boot.artifacts = artifacts
            boot.report = {'kind': 'gr00t_colab_bootstrap', 'status': 'failed',
                           'gr00t_rollout_completed': False, 'task_success': None}
            with patch.object(bootstrap, 'WORK', directory):
                archive = boot.package()
            report = entry.recover(archive, directory / 'recovered')
            self.assertEqual(report['kind'], 'gr00t_colab_bootstrap')

    def test_token_file_requires_private_mode_and_is_consumed(self):
        # An intentionally fictional string, never an account credential.
        fake = 'hf_' + 'A' * 20
        with tempfile.TemporaryDirectory(prefix='gr00t-review-token-') as tmp:
            token_file = Path(tmp) / 'fictional-token'
            token_file.write_text(fake)
            token_file.chmod(0o644)
            with self.assertRaises(bootstrap.PhaseFailure):
                bootstrap.consume_token(token_file)
            self.assertFalse(token_file.exists())
            token_file.write_text(fake)
            token_file.chmod(0o600)
            self.assertEqual(bootstrap.consume_token(token_file), fake)
            self.assertFalse(token_file.exists())

    def test_result_without_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='gr00t-review-no-manifest-') as tmp:
            directory = Path(tmp)
            archive = directory / 'result.zip'
            result_archive(archive, {'report.json': '{"status":"failed"}'}, manifest=False)
            with self.assertRaisesRegex(ValueError, 'manifest'):
                entry.recover(archive, directory / 'recovered')

    def test_result_manifest_must_cover_extra_members(self):
        with tempfile.TemporaryDirectory(prefix='gr00t-review-manifest-gap-') as tmp:
            directory = Path(tmp)
            archive = directory / 'result.zip'
            result_archive(archive, {'report.json': '{"status":"failed"}',
                                    'extra.log': 'synthetic evidence'}, covered=['report.json'])
            with self.assertRaisesRegex(ValueError, 'exact result archive'):
                entry.recover(archive, directory / 'recovered')


class SafeCLIContracts(unittest.TestCase):
    def invoke_fake(self, action, *, argv=None, state_store=None, assignment=None,
                    request_error=None, state_module=None, assign_error=None,
                    lookup_result=None, lookup_observer=None, unassign_observer=None,
                    assign_observer=None, contents_module=None):
        package = types.ModuleType('colab_cli')
        common = types.ModuleType('colab_cli.common')
        common.state = types.SimpleNamespace(_history=None, config_path=None,
                                             store=state_store)
        cli = types.ModuleType('colab_cli.cli')
        cli.setup_logging = lambda *a, **kw: self.fail('Native file logging enabled')
        cli.auto_update = types.SimpleNamespace(run_background_check=lambda: self.fail('Update network called'))
        client = types.ModuleType('colab_cli.client')
        class Assignment(types.SimpleNamespace):
            pass
        class Variant(str, Enum):
            DEFAULT = 'DEFAULT'
            GPU = 'GPU'
            TPU = 'TPU'
        class Accelerator(str, Enum):
            NONE = 'NONE'
            L4 = 'L4'
        client.Assignment, client.Variant, client.Accelerator = Assignment, Variant, Accelerator
        class Client:
            def _issue_request(self, endpoint, method='GET', **kwargs):
                if request_error is not None:
                    raise request_error
                return None
            def assign(self, *args, **kwargs):
                if assign_observer is not None:
                    assign_observer(*args, **kwargs)
                if assign_error is not None:
                    raise assign_error
                if assignment is None:
                    raise AssertionError('A test must explicitly supply an assignment')
                return assignment
            def _get_assignment(self, notebook_hash, variant=None, accelerator=None):
                if lookup_observer is not None:
                    lookup_observer(notebook_hash, variant, accelerator)
                return lookup_result(client) if callable(lookup_result) else lookup_result
            def _post_assignment(self, *args, **kwargs):
                raise AssertionError('Recovery must never submit an allocation POST')
            def list_assignments(self):
                raise AssertionError('Recovery must not enumerate unrelated assignments')
            def unassign(self, endpoint):
                if unassign_observer is not None:
                    unassign_observer(endpoint)
                return None
        client.Client = Client
        common.state.client = Client()
        commands = types.ModuleType('colab_cli.commands')
        contents = contents_module or types.ModuleType('colab_cli.contents')
        if contents_module is None:
            contents.requests = types.SimpleNamespace(request=lambda *a, **k: self.fail('Unexpected contents transport'))
        session = types.ModuleType('colab_cli.commands.session')
        run = types.ModuleType('colab_cli.commands.run')
        package.cli, package.common, package.contents = cli, common, contents
        commands.session, commands.run = session, run
        cli.main = lambda: action(cli, common, client, session, run)
        if state_module is None:
            state_module = types.ModuleType('colab_cli.state')
            state_module.SessionState = types.SimpleNamespace
        fake_modules = {'colab_cli': package, 'colab_cli.cli': cli,
                        'colab_cli.contents': contents,
                        'colab_cli.common': common, 'colab_cli.client': client,
                        'colab_cli.state': state_module,
                        'colab_cli.commands': commands,
                        'colab_cli.commands.session': session,
                        'colab_cli.commands.run': run}
        captured = io.StringIO()
        old_disable = logging.root.manager.disable
        try:
            with patch.dict(sys.modules, fake_modules), patch.object(safe_cli.importlib.metadata, 'version', return_value='0.6.0'), patch.object(sys, 'argv', argv or ['colab_safe_cli.py', 'synthetic-command']), contextlib.redirect_stdout(captured):
                code = safe_cli.main()
        finally:
            logging.disable(old_disable)
        return code, json.loads(captured.getvalue()), captured.getvalue()

    def test_native_output_and_exception_text_never_escape(self):
        marker = 'PRIVATE_TEST_MARKER_NOT_A_CREDENTIAL'
        def action(cli, common, client, session, run):
            cli.setup_logging(False)
            cli.auto_update.run_background_check()
            common.state._history.log_event('test', 'execution', {'code': marker})
            print(marker)
            print(marker, file=sys.stderr)
            logging.error(marker)
            raise RuntimeError(marker)
        code, report, text = self.invoke_fake(action)
        self.assertEqual(code, 1)
        self.assertEqual(report['error_type'], 'RuntimeError')
        self.assertNotIn(marker, text)
        self.assertFalse(report['unassign_completed'])

    def test_stop_without_unassign_cannot_confirm_release(self):
        code, report, _ = self.invoke_fake(lambda *args: None)
        self.assertEqual(code, 0)
        self.assertFalse(report['unassign_completed'])

    def test_real_unassign_return_is_required(self):
        def action(cli, common, client, session, run):
            client.Client().unassign('fictional-endpoint')
        code, report, _ = self.invoke_fake(action)
        self.assertEqual(code, 0)
        self.assertTrue(report['unassign_completed'])

    def test_keepalive_reenters_safe_wrapper_with_isolated_config(self):
        spawned = []
        fictional_config = str(ROOT / 'fictional-private-state.json')
        def fake_spawn(command, **kwargs):
            spawned.append((command, kwargs))
            return types.SimpleNamespace(pid=42)
        def action(cli, common, client, session, run):
            self.assertIs(session.spawn_keep_alive, run.spawn_keep_alive)
            session.spawn_keep_alive('fictional-endpoint', 'fictional-session',
                                     types.SimpleNamespace(value='oauth2'), fictional_config)
        with patch.object(safe_cli.subprocess, 'Popen', side_effect=fake_spawn):
            code, _, _ = self.invoke_fake(action)
        self.assertEqual(code, 0)
        self.assertEqual(len(spawned), 1)
        command, kwargs = spawned[0]
        self.assertEqual(command[:2], [sys.executable, str(ROOT / 'colab_safe_cli.py')])
        self.assertIn('--config', command)
        self.assertIn(fictional_config, command)
        self.assertTrue(kwargs['start_new_session'])
        for stream in ('stdin', 'stdout', 'stderr'):
            self.assertEqual(kwargs[stream], subprocess.DEVNULL)

    def test_assignment_identity_survives_keepalive_connect_timeout(self):
        # Both supported session flag spellings must preserve an exact cleanup
        # target before the native new command's keep-alive preflight. Exercise
        # the installed StateStore, then reopen the file to prove persistence.
        marker = 'FICTIONAL_PROXY_MARKER_NOT_A_CREDENTIAL'
        native_state = native_state_module()
        try:
            from requests.exceptions import ConnectTimeout
        except ImportError:
            self.skipTest('Optional Colab SDK Requests dependency is unavailable')
        assigned = types.SimpleNamespace(
            endpoint='fictional-owned-endpoint',
            runtime_proxy_info=types.SimpleNamespace(
                token=marker, url='https://fictional-runtime.invalid/?auth=' + marker))
        failing_url = ('https://colab.research.google.com/tun/m/'
                       'fictional-owned-endpoint/keep-alive/?opaque=' + marker)
        for session_flag in ('-s', '--session'):
            with self.subTest(session_flag=session_flag), tempfile.TemporaryDirectory(prefix='gr00t-review-owned-state-') as tmp:
                state_path = Path(tmp) / 'sessions.json'
                store = native_state.StateStore(str(state_path))
                argv = ['colab_safe_cli.py', '--config', str(state_path),
                        'new', session_flag, 'fictional-owned-session', '--gpu', 'L4']

                def action(cli, common, client, session, run):
                    # Equivalent to the native CLI callback: choose isolated
                    # state before creating/authenticating the Client.
                    common.state.config_path = str(state_path)
                    owned_client = client.Client()
                    value = owned_client.assign(
                        uuid.uuid4(),
                        variant=types.SimpleNamespace(value='GPU'),
                        accelerator=types.SimpleNamespace(value='L4'))
                    self.assertIs(value, assigned)
                    saved_before_ping = store.get('fictional-owned-session')
                    self.assertIsNotNone(saved_before_ping,
                                         'Native store.add runs after preflight; wrapper must save earlier')
                    self.assertEqual(saved_before_ping.endpoint, assigned.endpoint)
                    owned_client._issue_request(failing_url, method='GET', timeout=10)
                    self.fail('The synthetic keepalive timeout must abort new')

                previous_umask = safe_cli.os.umask(0o077)
                try:
                    code, report, text = self.invoke_fake(
                        action, argv=argv, state_store=store, assignment=assigned,
                        request_error=ConnectTimeout(marker), state_module=native_state)
                finally:
                    safe_cli.os.umask(previous_umask)
                self.assertEqual(code, 1)
                self.assertEqual(report['error_type'], 'ConnectTimeout')
                self.assertFalse(report['unassign_completed'])
                self.assertEqual(report['request_failure']['phase'], 'keepalive')
                self.assertEqual(report['request_failure']['host'], 'colab.research.google.com')
                self.assertEqual(report['request_failure']['method'], 'GET')
                reopened = native_state.StateStore(str(state_path))
                self.assertEqual(list(reopened.list()), ['fictional-owned-session'])
                saved = reopened.get('fictional-owned-session')
                self.assertEqual(saved.endpoint, assigned.endpoint)
                self.assertEqual(saved.token, marker)
                self.assertEqual(saved.url, assigned.runtime_proxy_info.url)
                self.assertEqual((saved.variant, saved.accelerator), ('GPU', 'L4'))
                self.assertIsNone(saved.keep_alive_pid)
                self.assertEqual(state_path.stat().st_mode & 0o777, 0o600)
                self.assertNotIn(marker, text)
                self.assertNotIn('fictional-runtime.invalid', text)
                self.assertNotIn('?opaque=', text)
                self.assertNotIn(assigned.endpoint, text)

    def test_lost_assign_response_recovers_only_persisted_hash(self):
        marker = 'FICTIONAL_POST_RESPONSE_SECRET'
        notebook_hash = uuid.uuid4()
        lookups, releases, removals = [], [], []
        with tempfile.TemporaryDirectory(prefix='gr00t-review-intent-') as tmp:
            config = Path(tmp) / 'sessions.json'
            config.write_text('{}')
            config.chmod(0o600)
            store = types.SimpleNamespace(get=lambda name: None,
                                          remove=lambda name: removals.append(name))
            name = 'fictional-recovery-session'
            prefix = ['colab_safe_cli.py', '--config', str(config)]

            def allocation_started(hash_value, **kwargs):
                # This executes inside the original assign stub, proving the
                # identity is on disk before any allocation request is issued.
                intent = safe_cli.load_intent(config, name)
                self.assertEqual(intent['notebook_hash'], str(hash_value))
                self.assertEqual(safe_cli.intent_path(config).stat().st_mode & 0o777, 0o600)

            def allocate(cli, common, client, session, run):
                client.Client().assign(notebook_hash, variant=client.Variant.GPU,
                                       accelerator=client.Accelerator.L4)

            code, report, text = self.invoke_fake(
                allocate, argv=[*prefix, 'new', '-s', name, '--gpu', 'L4'],
                state_store=store, assign_error=TimeoutError(marker),
                assign_observer=allocation_started)
            self.assertEqual(code, 1)
            self.assertFalse(report['unassign_completed'])
            self.assertTrue(safe_cli.intent_path(config).exists())
            self.assertNotIn(marker, text)

            def lookup(hash_value, variant, accelerator):
                lookups.append((hash_value, variant.value, accelerator.value))

            code, report, text = self.invoke_fake(
                lambda *args: self.fail('Recovery must bypass native stop/session selection'),
                argv=[*prefix, 'stop', '-s', name], state_store=store,
                lookup_result=lambda client: client.Assignment(
                    endpoint='fictional-owned-endpoint',
                    runtime_proxy_info=types.SimpleNamespace(token=marker,
                                                            url='https://fictional.invalid/?token=' + marker)),
                lookup_observer=lookup, unassign_observer=releases.append)
            self.assertEqual(code, 0)
            self.assertTrue(report['unassign_completed'])
            self.assertEqual(lookups, [(notebook_hash, 'GPU', 'L4')])
            self.assertEqual(releases, ['fictional-owned-endpoint'])
            self.assertEqual(removals, [name])
            self.assertFalse(safe_cli.intent_path(config).exists())
            self.assertNotIn(marker, text)
            self.assertNotIn('fictional.invalid', text)
            self.assertNotIn('fictional-owned-endpoint', text)

    def test_absent_or_untyped_lookup_never_claims_release(self):
        for found in (types.SimpleNamespace(token='FICTIONAL_GET_TOKEN'),
                      types.SimpleNamespace(endpoint='unrelated-untyped-endpoint')):
            with self.subTest(found_type=type(found).__name__), tempfile.TemporaryDirectory(prefix='gr00t-review-absence-') as tmp:
                config = Path(tmp) / 'sessions.json'
                config.write_text('{}')
                config.chmod(0o600)
                name = 'fictional-missing-state'
                store = types.SimpleNamespace(get=lambda name: None,
                                              remove=lambda name: self.fail('Unconfirmed scope must be retained'))
                safe_cli.persist_intent(config, name, uuid.uuid4(),
                                        types.SimpleNamespace(value='GPU'),
                                        types.SimpleNamespace(value='L4'))
                code, report, text = self.invoke_fake(
                    lambda *args: self.fail('Recovery must bypass native CLI'),
                    argv=['colab_safe_cli.py', '--config', str(config), 'stop', '-s', name],
                    state_store=store, lookup_result=found,
                    unassign_observer=lambda endpoint: self.fail('No exact typed Assignment to release'))
                self.assertEqual(code, 1)
                self.assertFalse(report['unassign_completed'])
                self.assertEqual(report['error_type'], 'RecoveryUnconfirmed')
                self.assertEqual(report['recovery_lookup'], 'absent_or_unrecognized')
                self.assertTrue(safe_cli.intent_path(config).exists())
                self.assertNotIn('FICTIONAL_GET_TOKEN', text)
                self.assertNotIn('unrelated-untyped-endpoint', text)

    def test_contents_timeout_is_scoped_and_forwarded(self):
        calls = []
        def transport(method, url, **kwargs):
            calls.append((method, kwargs))
            return types.SimpleNamespace(status_code=200)
        original = types.SimpleNamespace(request=transport)
        contents = types.ModuleType('colab_cli.contents')
        contents.requests = original
        def action(*args):
            self.assertIsNot(contents.requests, original)
            self.assertIs(original.request, transport, 'Global requests callable must remain untouched')
            contents.requests.request('GET', 'https://runtime.example.invalid/api/contents/report.json',
                                      params={'content': '1'})
            contents.requests.request('PUT', 'https://runtime.example.invalid/api/contents/test.json',
                                      timeout=(2, 3), json={'content': 'synthetic'})
        with patch.object(safe_cli.time, 'monotonic', side_effect=[1.0, 2.0, 3.0, 3.25]):
            code, report, _ = self.invoke_fake(
                action, argv=['colab_safe_cli.py', 'download', '-s', 'fictional-session'],
                contents_module=contents)
        self.assertEqual(code, 0)
        self.assertEqual(calls[0][1]['timeout'], (10, 25))
        self.assertEqual(calls[0][1]['params'], {'content': '1'})
        self.assertEqual(calls[1][1]['timeout'], (2, 3))
        self.assertEqual(report['contents_request']['phase'], 'contents_put')
        self.assertEqual(report['contents_request']['elapsed_s'], 0.25)
        self.assertEqual(report['contents_request']['status_code'], 200)
        self.assertNotIn('request_failure', report)
        self.assertIs(contents.requests, original)
        self.assertIs(original.request, transport)

    def test_contents_errors_record_only_safe_transport_metadata(self):
        marker = 'FICTIONAL_CONTENTS_SECRET_DO_NOT_DISPLAY'
        unsafe_url = ('https://fictional-user:' + marker + '@runtime.example.invalid/'
                      'api/contents/report.json?colab-runtime-proxy-token=' + marker)
        for error_name in ('ConnectTimeout', 'ReadTimeout', 'HTTPError', 'HTTPStatusResponse'):
            with self.subTest(error_name=error_name):
                error_class = type('HTTPError' if error_name == 'HTTPStatusResponse' else error_name,
                                   (Exception,), {})
                error = error_class(unsafe_url + marker)
                error.response = types.SimpleNamespace(status_code=403, text=marker)
                def transport(method, url, **kwargs):
                    if error_name == 'HTTPStatusResponse':
                        return types.SimpleNamespace(status_code=403, text=marker)
                    raise error
                original = types.SimpleNamespace(request=transport)
                contents = types.ModuleType('colab_cli.contents')
                contents.requests = original
                def action(*args):
                    contents.requests.request('GET', unsafe_url,
                                              params={'colab-runtime-proxy-token': marker})
                    # SDK's raise_for_status occurs after requests.request.
                    raise error
                with patch.object(safe_cli.time, 'monotonic', side_effect=[10.0, 12.5]):
                    code, report, text = self.invoke_fake(
                        action, argv=['colab_safe_cli.py', 'download', '-s', 'fictional-session'],
                        contents_module=contents)
                self.assertEqual(code, 1)
                diagnostic = report['request_failure']
                self.assertEqual(diagnostic['host'], 'runtime.example.invalid')
                self.assertEqual(diagnostic['method'], 'GET')
                self.assertEqual(diagnostic['phase'], 'contents_get')
                self.assertEqual(diagnostic['status_code'], 403)
                self.assertEqual(diagnostic['elapsed_s'], 2.5)
                self.assertEqual(diagnostic['type'], None if error_name == 'HTTPStatusResponse' else error_name)
                for forbidden in (marker, 'fictional-user', 'api/contents',
                                  'colab-runtime-proxy-token', '?', 'https://'):
                    self.assertNotIn(forbidden, text)
                self.assertIs(contents.requests, original)
                self.assertIs(original.request, transport)


class ParentAcceptanceContracts(unittest.TestCase):
    def invoke_parent(self, deadline=False, release=True, scenario=None):
        fake_hf = types.ModuleType('huggingface_hub')
        fake_hf.get_token = lambda: 'FICTIONAL_TEST_VALUE_NOT_AN_ACCOUNT_TOKEN'
        transport_marker = 'FICTIONAL_TRANSPORT_OUTPUT_SECRET'
        with tempfile.TemporaryDirectory(prefix='gr00t-review-parent-') as tmp:
            root = Path(tmp)
            for name in entry.PUBLIC_FILES:
                (root / name).write_bytes((ROOT / name).read_bytes())
            (root / 'colab_safe_cli.py').write_text('# synthetic path; never executed\n')
            clock = [0.0]
            stopped = []
            live_downloads = []
            termination_sent = [False]
            class Process:
                returncode = None
                def poll(self):
                    if scenario == 'sigterm' and not termination_sent[0]:
                        termination_sent[0] = True
                        signal.raise_signal(signal.SIGTERM)
                    return self.returncode
                def communicate(self, **kwargs):
                    return '', None
                def terminate(self):
                    self.returncode = -15
                def kill(self):
                    self.returncode = -9
                def wait(self, **kwargs):
                    return self.returncode
            process = Process()
            def spawn(*args, **kwargs):
                clock[0] = 61.0 if deadline else 0.0
                process.returncode = None if deadline or scenario in {'poll_retry', 'sigterm'} else 0
                return process
            def sleep(seconds):
                clock[0] += seconds
            def command(argv, **kwargs):
                verb = argv[4]
                response = {'exit_code': 0, 'error_type': None, 'unassign_completed': False}
                if verb == 'check-connection':
                    response['connection_verified'] = True
                if verb == 'upload' and str(argv[-1]).endswith('/hf-token'):
                    self.assertEqual(Path(argv[-2]).stat().st_mode & 0o777, 0o600)
                    self.assertNotIn(fake_hf.get_token(), ' '.join(map(str, argv)))
                if verb == 'stop':
                    if scenario == 'sigterm':
                        self.assertTrue(termination_sent[0])
                        self.assertEqual(process.returncode, -15)
                        self.assertEqual(signal.getsignal(signal.SIGTERM), signal.SIG_IGN)
                        self.assertEqual(kwargs['timeout'], 120)
                        # A second genuine in-process SIGTERM during cleanup
                        # must not interrupt the bounded release/report path.
                        signal.raise_signal(signal.SIGTERM)
                    stopped.append(True)
                    response['unassign_completed'] = release
                if verb == 'upload' and scenario == 'malformed_cli':
                    return subprocess.CompletedProcess(argv, 0, 'malformed:' + transport_marker, '')
                if verb == 'download':
                    if str(argv[-2]).endswith('/artifacts/report.json'):
                        live_downloads.append(True)
                        if len(live_downloads) == 1:
                            raise subprocess.TimeoutExpired(argv, kwargs['timeout'],
                                                            output=transport_marker, stderr=transport_marker)
                        Path(argv[-1]).write_text(json.dumps({'phase': 'model_download_and_rollout',
                                                            'status': 'failed'}))
                        process.returncode = 0
                        return subprocess.CompletedProcess(argv, 0, json.dumps(response), '')
                    if scenario == 'final_download_timeout':
                        raise subprocess.TimeoutExpired(argv, kwargs['timeout'],
                                                        output=transport_marker, stderr=transport_marker)
                    # A clean CLI exit and a retrieved, failed application
                    # report must never turn into an accepted experiment.
                    result_archive(argv[-1], {'report.json': json.dumps({
                        'kind': 'gr00t_colab_bootstrap', 'status': 'failed'})})
                return subprocess.CompletedProcess(argv, 0, json.dumps(response), '')
            output = io.StringIO()
            old_umask = entry.os.umask(0o077)
            try:
                with patch.object(entry, 'ROOT', root), patch.dict(sys.modules, {'huggingface_hub': fake_hf}), patch.object(entry.sys, 'argv', ['run_colab.py', '--gpu-minutes', '3' if scenario == 'poll_retry' else '1']), patch.object(entry.subprocess, 'run', side_effect=command), patch.object(entry.subprocess, 'Popen', side_effect=spawn), patch.object(entry.time, 'monotonic', side_effect=lambda: clock[0]), patch.object(entry.time, 'sleep', side_effect=sleep), contextlib.redirect_stdout(output):
                    code = entry.main()
            finally:
                entry.os.umask(old_umask)
            runs = list((root / 'output/colab').glob('*'))
            self.assertEqual(len(runs), 1)
            report = json.loads((runs[0] / 'report.json').read_text())
            state_exists = (runs[0] / 'private-session').exists()
            self.assertFalse((runs[0] / 'private-session/hf-token').exists())
            self.assertNotIn(fake_hf.get_token(), output.getvalue())
            self.assertNotIn(transport_marker, output.getvalue())
            self.assertNotIn(transport_marker, json.dumps(report))
            self.assertTrue(stopped)
            return code, report, state_exists

    def test_exec_zero_does_not_accept_failed_application(self):
        code, report, state_exists = self.invoke_parent()
        self.assertEqual(code, 1)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['bootstrap']['status'], 'failed')
        self.assertNotIn('error_type', report)
        self.assertTrue(report['runtime_released'])
        self.assertFalse(state_exists)

    def test_watchdog_stops_this_run_and_cleans_local_token(self):
        code, report, state_exists = self.invoke_parent(deadline=True)
        self.assertEqual(code, 1)
        self.assertEqual(report['error_type'], 'TimeoutError')
        self.assertTrue(report['runtime_released'])
        self.assertFalse(state_exists)

    def test_missing_unassign_confirmation_retains_private_state(self):
        code, report, state_exists = self.invoke_parent(release=False)
        self.assertEqual(code, 1)
        self.assertFalse(report['runtime_released'])
        self.assertTrue(state_exists)

    def test_transient_live_download_timeout_retries_without_accepting_failure(self):
        code, report, state_exists = self.invoke_parent(scenario='poll_retry')
        self.assertEqual(code, 1)
        self.assertEqual(report['bootstrap']['status'], 'failed')
        self.assertEqual(report['poll_failures'], 1)
        self.assertEqual(report['last_poll_failure']['error_type'], 'TimeoutExpired')
        self.assertNotIn('failed_colab_command', report)
        self.assertNotIn('error_type', report)
        self.assertTrue(report['runtime_released'])
        self.assertFalse(state_exists)

    def test_final_download_timeout_records_only_fixed_failure_metadata(self):
        code, report, state_exists = self.invoke_parent(scenario='final_download_timeout')
        self.assertEqual(code, 1)
        self.assertEqual(report['error_type'], 'TimeoutExpired')
        self.assertEqual(report['failed_colab_command']['command'], 'download')
        self.assertEqual(report['failed_colab_command']['error_type'], 'TimeoutExpired')
        self.assertTrue(report['runtime_released'])
        self.assertFalse(state_exists)

    def test_malformed_cli_stdout_zero_is_rejected(self):
        code, report, state_exists = self.invoke_parent(scenario='malformed_cli')
        self.assertEqual(code, 1)
        self.assertEqual(report['failed_colab_command']['command'], 'upload')
        self.assertEqual(report['failed_colab_command']['error_type'], 'MissingSafeCLIResult')
        self.assertTrue(report['runtime_released'])
        self.assertFalse(state_exists)

    def test_sigterm_enters_cleanup_and_restores_previous_handler(self):
        previous = signal.getsignal(signal.SIGTERM)
        original_calls = []
        def original_handler(signum, frame):
            original_calls.append(signum)
            raise AssertionError('Prior handler must be overridden until cleanup ends')
        signal.signal(signal.SIGTERM, original_handler)
        try:
            code, report, state_exists = self.invoke_parent(scenario='sigterm')
            self.assertEqual(code, 1)
            self.assertEqual(report['status'], 'failed')
            self.assertEqual(report['error_type'], 'TerminationRequested')
            self.assertTrue(report['runtime_released'])
            self.assertFalse(state_exists)
            self.assertNotIn('cleanup_error_type', report)
            self.assertEqual(original_calls, [])
            self.assertIs(signal.getsignal(signal.SIGTERM), original_handler)
        finally:
            signal.signal(signal.SIGTERM, previous)


if __name__ == '__main__':
    unittest.main(verbosity=2)
