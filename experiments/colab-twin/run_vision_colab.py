#!/usr/bin/env python3
"""One bounded Colab visual-ACT training job, byte-exact inputs and verified recovery."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
import signal
import subprocess
import sys
import time
import uuid
from zipfile import ZipFile, ZIP_STORED

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SHARD_BYTES = 8 * 2**20
DATASETS = [
    'output/vision-b-rgb-20261002/expert-rgb.h5',
    'output/vision-b-pilot-rgb-prefix50-20261003/expert-rgb.h5',
    'output/vision-b-pilot-rgb-v6-450-20261003/expert-rgb.h5',
    'output/vision-b-pilot-rgb-approach-seed23-20261003/expert-rgb.h5',
]
SOURCES = ['learning_data.py', 'learning_vision.py', 'run_vision_learning.py',
           'requirements-learning.txt', 'remote_vision_worker.py']


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''):
            digest.update(block)
    return digest.hexdigest()


def write(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.partial')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def split_file(path, destination):
    destination.mkdir(exist_ok=False)
    parts = []
    with path.open('rb') as stream:
        while block := stream.read(SHARD_BYTES):
            p = destination / f'part-{len(parts):04d}.bin'
            p.write_bytes(block)
            parts.append({'file': p.name, 'bytes': len(block), 'sha256': sha(p)})
    return {'zip': {'file': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path)},
            'shard_size_bytes': SHARD_BYTES, 'shards': parts}


def validate_index(index):
    if not isinstance(index, dict) or not isinstance(index.get('zip'), dict):
        raise ValueError('Missing archive identity')
    if not re.fullmatch(r'[0-9a-f]{64}', str(index['zip'].get('sha256', ''))):
        raise ValueError('Missing archive hash')
    size = index['zip'].get('bytes')
    if type(size) is not int or not 0 < size <= 256 * 2**20:
        raise ValueError('Recovered archive exceeds the bounded artifact size')
    parts = index.get('shards')
    if not isinstance(parts, list) or not 1 <= len(parts) <= 64:
        raise ValueError('Invalid artifact shard count')
    seen = set()
    for part in parts:
        name = part.get('file', '')
        if not isinstance(name, str) or name in ('', '.', '..') or PurePosixPath(name).name != name or '\\' in name or name in seen:
            raise ValueError('Invalid artifact shard name')
        seen.add(name)
        if type(part.get('bytes')) is not int or not 0 < part['bytes'] <= SHARD_BYTES:
            raise ValueError('Invalid artifact shard size')
        if not re.fullmatch(r'[0-9a-f]{64}', str(part.get('sha256', ''))):
            raise ValueError('Missing artifact shard hash')
    if sum(p['bytes'] for p in parts) != size:
        raise ValueError('Artifact shard lengths do not cover archive')


def recover(archive, destination):
    allowed = {'report.json', 'runtime.json', 'imports.json', 'artifact-manifest.json',
               'microbenchmark/report.json', 'fit/report.json',
               'fit/policy.pt', 'fit/policy-step-2115.pt'}
    with ZipFile(archive) as source:
        members = source.infolist()
        names = [m.filename for m in members]
        if len(set(names)) != len(names) or not {'artifact-manifest.json', 'report.json'} <= set(names):
            raise ValueError('Duplicate members or missing manifest')
        if sum(m.file_size for m in members) > 256 * 2**20:
            raise ValueError('Unpacked results exceed size limit')
        for item in members:
            path = PurePosixPath(item.filename)
            valid_log = (len(path.parts) == 2 and path.parts[0] == 'logs'
                         and path.suffix == '.log')
            if item.is_dir() or path.as_posix() != item.filename or '..' in path.parts or path.is_absolute() or '\\' in item.filename:
                raise ValueError('Unsafe artifact path')
            if item.filename not in allowed and not valid_log:
                raise ValueError('Unexpected artifact: ' + item.filename)
        manifest = json.loads(source.read('artifact-manifest.json'))
        rows = manifest['files']
        if len(rows) != len(names) - 1 or {r['file'] for r in rows} != set(names) - {'artifact-manifest.json'}:
            raise ValueError('Manifest does not cover exact artifact set')
        for row in rows:
            data = source.read(row['file'])
            if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
                raise ValueError('Artifact content hash mismatch')
        worker = json.loads(source.read('report.json'))
        if worker.get('status') not in ('completed', 'failed'):
            raise ValueError('Recovered worker lacks terminal status')
        if worker['status'] == 'completed':
            required = {'runtime.json', 'imports.json', 'microbenchmark/report.json',
                        'fit/report.json', 'fit/policy.pt'}
            if not required <= set(names):
                raise ValueError('Completed worker lacks training evidence')
            fit = json.loads(source.read('fit/report.json'))
            if (fit.get('status') != 'completed_diagnostic' or fit.get('checkpoint_reload_exact') is not True
                    or fit.get('batch_size') != 8
                    or hashlib.sha256(source.read('fit/policy.pt')).hexdigest() != fit.get('checkpoint_sha256')):
                raise ValueError('Completed fit checkpoint is unverified')
        destination.mkdir(exist_ok=False)
        for name in names:
            p = destination / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(source.read(name))
    return json.loads((destination / 'report.json').read_text())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--gpu', choices=['L4', 'T4', 'A100'], default='L4')
    parser.add_argument('--gpu-minutes', type=int, default=30)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args(argv)
    if not 5 <= args.gpu_minutes <= 30:
        parser.error('GPU ownership budget must be 5..30 minutes')
    os.umask(0o077)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    run_id = uuid.uuid4().hex[:12]
    session = 'so101-vision-' + run_id
    remote = '/content/' + session
    files = [ROOT / n for n in SOURCES + DATASETS]
    manifest = {'files': [{'file': p.relative_to(REPO).as_posix(),
                          'bytes': p.stat().st_size, 'sha256': sha(p)} for p in files]}
    source_hash = {n: sha(ROOT / n) for n in ['learning_vision.py', 'run_vision_learning.py']}
    job = {'dataset_paths': [(ROOT / p).relative_to(REPO).as_posix() for p in DATASETS],
           'source_sha256': source_hash, 'visual_dataset_sha256': [sha(ROOT / p) for p in DATASETS],
           'max_steps': 5000, 'max_wall_s': 600, 'snapshot_step': 2115, 'seed': 0,
           'startup_weight': 5, 'local_balance': False, 'batch_size': 8,
           'precision': 'float32', 'physical_scope': 'not_run',
           'acceptance_candidate': 'final policy.pt only; snapshot is diagnostic',
           'requested_gpu': args.gpu}
    write(output / 'job.json', job)
    write(output / 'input-manifest.json', manifest)
    bundle = output / 'input.zip'
    with ZipFile(bundle, 'w', compression=ZIP_STORED) as archive:
        for p in files:
            archive.write(p, 'project/' + p.relative_to(REPO).as_posix())
        archive.write(output / 'job.json', 'job.json')
        archive.write(output / 'input-manifest.json', 'input-manifest.json')
    index = split_file(bundle, output / 'upload-shards')
    write(output / 'upload-index.json', index)
    report = {'status': 'prepared', 'session': session, 'requested_gpu': args.gpu,
              'started_utc': datetime.now(timezone.utc).isoformat(), 'gpu_minutes': args.gpu_minutes,
              'runtime_released': False, 'remote_worker_completed': False,
              'artifact_recovery_verified': False, 'physical_scope': 'not_run', 'calls': []}
    write(output / 'delivery.json', report)
    if args.prepare_only:
        print(json.dumps({'status': 'prepared', 'shards': len(index['shards']), 'output': str(output)}))
        return 0
    state_dir = Path.home() / '.cache/so101-colab' / session
    state_dir.mkdir(parents=True, mode=0o700, exist_ok=False)
    state_file = state_dir / 'sessions.json'
    state_file.write_text('{}')
    cli_python = Path.home() / '.local/share/uv/tools/google-colab-cli/bin/python'
    prefix = [str(cli_python), str(REPO / 'experiments/gr00t-libero/colab_safe_cli.py'),
              '--config', str(state_file)]
    report['private_state_file'] = str(state_file)
    deadline = time.monotonic() + args.gpu_minutes * 60
    owned = False

    def call(*command, timeout=90, cleanup=False):
        limit = timeout if cleanup else min(timeout, deadline - time.monotonic())
        if limit <= 0:
            raise TimeoutError('Cloud job deadline reached')
        began = time.monotonic()
        try:
            result = subprocess.run([*prefix, *map(str, command)], capture_output=True,
                                    text=True, timeout=limit)
            try:
                value = json.loads(result.stdout)
            except ValueError:
                value = {'exit_code': 1, 'error_type': 'InvalidSafeCLIResult'}
            if not isinstance(value, dict):
                value = {'exit_code': 1, 'error_type': 'InvalidSafeCLIResult'}
            success = result.returncode == 0 and value.get('exit_code') == 0
        except subprocess.TimeoutExpired:
            # Never expose partial stdout/stderr: native CLI errors may include credentials.
            value = {'exit_code': 1, 'error_type': 'TimeoutExpired'}
            success = False
        entry = {'command': command[0], 'elapsed_s': time.monotonic() - began,
                 'result': value}
        report['calls'].append(entry)
        write(output / 'delivery.json', report)
        if not success:
            raise RuntimeError('Colab ' + str(command[0]) + ' failed: ' + str(value.get('error_type') or (value.get('request_failure') or {}).get('type') or value.get('error_category')))
        return value

    def transfer(*command, timeout=90):
        # PUT of identical bytes to the owned shard, and GET to the same local
        # destination, are idempotent. Allocation/exec/fit are never retried.
        for attempt in range(3):
            try:
                return call(*command, timeout=timeout)
            except RuntimeError:
                result = report['calls'][-1]['result']
                failure = result.get('request_failure') or {}
                retryable = (failure.get('type') in ('ConnectTimeout', 'ReadTimeout', 'ConnectionError')
                             or failure.get('status_code') in (502, 503, 504))
                if not retryable or attempt == 2:
                    raise
                if deadline - time.monotonic() <= 150:
                    raise TimeoutError('No remaining budget for transfer retry')
                time.sleep(5 * (attempt + 1))

    def exec_code(name, code):
        path = output / name
        path.write_text(code)
        return call('exec', '-s', session, '-f', path, '--timeout', '60', timeout=90)

    def terminate(signum, frame):
        raise KeyboardInterrupt('bounded job termination')

    old_signal = signal.signal(signal.SIGTERM, terminate)
    try:
        connection = call('check-connection', timeout=75)
        if connection.get('connection_verified') is not True:
            raise RuntimeError('Account connection not verified')
        report['initial_active_assignments'] = connection['active_assignments']
        owned = True  # Allocation can succeed even when the response is lost.
        report['status'] = 'allocating'
        call('new', '-s', session, '--gpu', args.gpu, timeout=180)
        exec_code('init_remote.py', f'from pathlib import Path\nPath({remote!r}).mkdir(exist_ok=False)\n')
        report['status'] = 'uploading'
        for i, part in enumerate(index['shards']):
            transfer('upload', '-s', session, output / 'upload-shards' / part['file'],
                 remote + '/' + part['file'], timeout=90)
            print(json.dumps({'phase': 'upload', 'part': i + 1, 'total': len(index['shards'])}), flush=True)
        launch = f'''import hashlib,json,subprocess,sys
from pathlib import Path
from zipfile import ZipFile
w=Path({remote!r}); index={index!r}; manifest={manifest!r}
with (w/'input.zip').open('wb') as output:
    for part in index['shards']:
        data=(w/part['file']).read_bytes()
        assert len(data)==part['bytes'] and hashlib.sha256(data).hexdigest()==part['sha256']
        output.write(data)
assert hashlib.sha256((w/'input.zip').read_bytes()).hexdigest()==index['zip']['sha256']
with ZipFile(w/'input.zip') as z:
    expected={{'job.json','input-manifest.json'}}|{{'project/'+r['file'] for r in manifest['files']}}
    assert len(z.namelist())==len(expected) and set(z.namelist())==expected
    for row in manifest['files']:
        data=z.read('project/'+row['file'])
        assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
    for name in expected:
        p=w/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
with (w/'worker-launch.log').open('wb') as log:
    p=subprocess.Popen([sys.executable,str(w/'project/experiments/colab-twin/remote_vision_worker.py'),'--work-dir',str(w)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
(w/'worker-pid.json').write_text(json.dumps({{'pid':p.pid}}))
'''
        exec_code('launch_remote.py', launch)
        report['status'] = 'running'
        failures = 0
        while time.monotonic() < deadline - 150:
            time.sleep(30)
            try:
                call('download', '-s', session, remote + '/artifacts/report.json',
                     output / 'live-report.json', timeout=45)
                live = json.loads((output / 'live-report.json').read_text())
                report['last_worker_status'] = live.get('status')
                report['last_worker_phase'] = live.get('phase')
                print(json.dumps({'phase': 'worker', 'status': live.get('status'),
                                  'worker_phase': live.get('phase')}), flush=True)
                failures = 0
                if live.get('status') in ('completed', 'failed'):
                    break
            except (RuntimeError, ValueError, OSError):
                failures += 1
                if failures >= 3:
                    raise RuntimeError('Three consecutive status retrieval failures')
        else:
            raise TimeoutError('Worker did not finish within cloud budget')
        # index.json is written last, after packaging all output shards. A terminal
        # training report alone does not mean recovery is ready. No training retry.
        for attempt in range(3):
            time.sleep(5)
            try:
                call('download', '-s', session, remote + '/recovery/index.json',
                     output / 'recovery-index.json', timeout=45)
                break
            except RuntimeError:
                if attempt == 2:
                    raise
        recovered = json.loads((output / 'recovery-index.json').read_text())
        validate_index(recovered)
        pieces = output / 'download-shards'; pieces.mkdir()
        for part in recovered['shards']:
            target = pieces / part['file']
            transfer('download', '-s', session, remote + '/recovery/' + part['file'], target)
            if target.stat().st_size != part['bytes'] or sha(target) != part['sha256']:
                raise ValueError('Downloaded shard mismatch')
        result_zip = output / 'results.zip'
        with result_zip.open('wb') as stream:
            for part in recovered['shards']:
                stream.write((pieces / part['file']).read_bytes())
        if sha(result_zip) != recovered['zip']['sha256']:
            raise ValueError('Downloaded archive mismatch')
        worker = recover(result_zip, output / 'recovered')
        report['artifact_recovery_verified'] = True
        report['remote_worker_completed'] = worker.get('status') == 'completed'
        report['status'] = 'completed' if report['remote_worker_completed'] else 'failed'
    except BaseException as error:
        report['status'] = 'failed'
        report['error_type'] = type(error).__name__
        report['error'] = str(error) if isinstance(error, (ValueError, RuntimeError, TimeoutError)) else type(error).__name__
    finally:
        if owned:
            try:
                released = call('stop', '-s', session, cleanup=True, timeout=120)
                report['runtime_released'] = released.get('unassign_completed') is True
            except BaseException as error:
                report['cleanup_error_type'] = type(error).__name__
        signal.signal(signal.SIGTERM, old_signal)
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        write(output / 'delivery.json', report)
    print(json.dumps({k: report[k] for k in ('status', 'artifact_recovery_verified', 'runtime_released')}, ensure_ascii=False), flush=True)
    return 0 if report['status'] == 'completed' and report['runtime_released'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
