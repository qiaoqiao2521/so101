"""Bounded overview recording for this fixed workcell; never advances physics.

The control thread captures full integration state at the original video ticks.
A separate, deadline-bound process renders those states after control finishes.
Real-time perception does not use this recorder.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import mujoco
import numpy as np


SIGNATURE = int(mujoco.mjtState.mjSTATE_INTEGRATION)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


LOADED_SOURCE_SHA256 = digest(__file__)


def runtime_binding():
    root = Path(mujoco.__file__).parent
    library = root / ('libmujoco.so.'+mujoco.__version__)
    return {'version': mujoco.__version__, 'library_sha256': digest(library),
            'renderer_sha256': digest(root/'renderer.py'),
            'gl_backend': mujoco.gl_context.GLContext.__module__,
            'gl_environment': os.environ.get('MUJOCO_GL', 'auto')}


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def model_bytes(model):
    buffer = np.empty(mujoco.mj_sizeModel(model), dtype=np.uint8)
    mujoco.mj_saveModel(model, buffer=buffer)
    return buffer.tobytes()


def check_workcell(model):
    if model.nsensor or model.nplugin:
        raise ValueError('Deferred video requires the fixed sensor/plugin-free workcell')
    for name in ('control', 'passive', 'sensor', 'act_dyn', 'act_gain', 'act_bias', 'contactfilter', 'time'):
        if getattr(mujoco, 'get_mjcb_'+name)() is not None:
            raise ValueError('Deferred video does not reproduce callbacks: '+name)


def remaining(deadline):
    value = deadline-time.monotonic()
    if value <= 0:
        raise TimeoutError('video_deadline_exhausted')
    return value


def stop_owned_group(process):
    """The caller created this process with start_new_session=True."""
    if process.pid <= 1 or process.pid == os.getpgrp():
        raise RuntimeError('Refusing invalid video process group')
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=2)


class DeferredVideo:
    def __init__(self, model, path, *, max_frames, deadline):
        check_workcell(model)
        if (isinstance(max_frames, bool) or not isinstance(max_frames, int)
                or not 1 <= max_frames <= 2250 or not math.isfinite(deadline)):
            raise ValueError('Invalid video frame cap or deadline')
        remaining(deadline)
        if digest(__file__) != LOADED_SOURCE_SHA256:
            raise RuntimeError('Loaded video source changed')
        self.runtime = runtime_binding()
        self.worker_sha256 = LOADED_SOURCE_SHA256
        self.model, self.path = model, Path(path)
        self.deadline, self.max_frames = float(deadline), max_frames
        self.count, self.closed, self.process = 0, False, None
        self.state_size = mujoco.mj_stateSize(model, SIGNATURE)
        self.states = np.empty((max_frames, self.state_size), dtype=np.float64)
        self.ticks = np.empty(max_frames, dtype=np.int64)
        self.model_path = self.path.with_suffix('.mjb')
        self.state_path = self.path.with_suffix('.states.npz')
        self.manifest_path = self.path.with_suffix('.job.json')
        self.result_path = self.path.with_suffix('.video.json')
        for p in (self.path, self.model_path, self.state_path, self.manifest_path, self.result_path):
            if p.exists():
                raise FileExistsError(p)
        binary = model_bytes(model)
        with self.model_path.open('xb') as stream:
            stream.write(binary)
        self.model_sha256 = hashlib.sha256(binary).hexdigest()
        self.result = {'complete': False, 'captured_frames': 0, 'encoded_frames': 0,
                       'camera': 'overview', 'fps': 25, 'width': 640, 'height': 480,
                       'state_signature': SIGNATURE, 'state_size': self.state_size,
                       'max_frames': max_frames, 'model_sha256': self.model_sha256,
                       'runtime_binding': self.runtime}

    def capture(self, data, tick):
        if self.closed or self.count >= self.max_frames:
            raise RuntimeError('video_capture_closed_or_full')
        if isinstance(tick, bool) or not isinstance(tick, int) or tick != self.count*2:
            raise ValueError('Video ticks must preserve the original even-tick order')
        remaining(self.deadline)
        mujoco.mj_getState(self.model, data, self.states[self.count], SIGNATURE)
        if not np.isfinite(self.states[self.count]).all():
            raise ValueError('Nonfinite video integration state')
        self.ticks[self.count] = tick
        self.count += 1
        self.result['captured_frames'] = self.count

    def report(self):
        return dict(self.result)

    def close(self):
        if self.closed:
            return
        self.closed = True
        started = time.monotonic()
        try:
            if digest(__file__) != self.worker_sha256 or runtime_binding() != self.runtime:
                raise RuntimeError('Video source or runtime changed during the episode')
            if hashlib.sha256(model_bytes(self.model)).hexdigest() != self.model_sha256:
                raise RuntimeError('Video model changed during the episode')
            with self.state_path.open('xb') as stream:
                np.savez(stream, states=self.states[:self.count], ticks=self.ticks[:self.count])
            self.result['state_sha256'] = digest(self.state_path)
            if not self.count:
                self.result.update(complete=True, empty=True)
                return
            import imageio_ffmpeg
            executable = str(Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve())
            manifest = {**self.result, 'model_path': str(self.model_path.resolve()),
                        'state_path': str(self.state_path.resolve()),
                        'output_path': str(self.path.resolve()),
                        'worker_result_path': str(self.path.with_suffix('.worker.json').resolve()),
                        'mujoco_version': mujoco.__version__,
                        'worker_sha256': self.worker_sha256, 'encoder_path': executable,
                        'encoder_sha256': digest(executable), 'deadline': self.deadline}
            write_json(self.manifest_path, manifest)
            environment = dict(os.environ)
            environment.pop('BW_SESSION', None)
            with self.path.with_suffix('.worker.log').open('xb') as log:
                self.process = subprocess.Popen(
                    [sys.executable, str(Path(__file__).resolve()), '--job', str(self.manifest_path.resolve())],
                    stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                    start_new_session=True, env=environment)
                self.result['worker_pid'] = self.process.pid
                try:
                    code = self.process.wait(timeout=remaining(self.deadline))
                except (subprocess.TimeoutExpired, TimeoutError):
                    stop_owned_group(self.process)
                    self.result['worker_reaped'] = self.process.poll() is not None
                    raise TimeoutError('video_finalize_deadline') from None
            self.result.update(worker_returncode=code, worker_reaped=True)
            if code:
                stop_owned_group(self.process)
                raise RuntimeError('video_worker_failed: '+str(code))
            worker = json.loads(Path(manifest['worker_result_path']).read_text())
            if not (worker.get('complete') and worker.get('encoded_frames') == self.count
                    and worker.get('model_sha256') == self.model_sha256
                    and worker.get('state_sha256') == self.result['state_sha256']
                    and worker.get('worker_sha256') == manifest['worker_sha256']
                    and worker.get('encoder_sha256') == manifest['encoder_sha256']
                    and worker.get('runtime_binding') == self.runtime
                    and worker.get('encoder_returncode') == 0
                    and worker.get('ffmpeg_progress', {}).get('progress') == 'end'
                    and int(worker.get('ffmpeg_progress', {}).get('frame', '-1')) == self.count
                    and len(worker.get('frame_rgb_sha256', [])) == self.count
                    and all(isinstance(h, str) and len(h) == 64
                            and all(c in '0123456789abcdef' for c in h)
                            for h in worker.get('frame_rgb_sha256', []))
                    and self.path.is_file() and self.path.stat().st_size > 0
                    and digest(self.path) == worker.get('video_sha256')):
                raise RuntimeError('video_worker_result_invalid')
            audit_path = self.path.with_suffix('.rgb-audit.npz')
            if digest(audit_path) != worker.get('rgb_audit_sha256'):
                raise RuntimeError('video_rgb_audit_identity_invalid')
            with np.load(audit_path, allow_pickle=False) as archive:
                indices, rgb = archive['indices'], archive['rgb']
            expected = np.linspace(0, self.count-1, min(100, self.count), dtype=np.int64)
            if (not np.array_equal(indices, expected) or rgb.dtype != np.uint8
                    or rgb.shape != (len(expected), 480, 640, 3)
                    or any(hashlib.sha256(memoryview(np.ascontiguousarray(frame))).hexdigest()
                           != worker['frame_rgb_sha256'][int(index)]
                           for index, frame in zip(indices, rgb))):
                raise RuntimeError('video_rgb_audit_frames_invalid')
            if runtime_binding() != self.runtime or digest(__file__) != self.worker_sha256:
                raise RuntimeError('Video runtime changed during finalization')
            remaining(self.deadline)
            self.result.update(worker)
        except BaseException as error:
            self.result.update(complete=False, error_type=type(error).__name__, error=str(error))
            raise
        finally:
            try:
                if self.process is not None and not self.result.get('worker_reaped'):
                    stop_owned_group(self.process)
                    self.result['worker_reaped'] = True
            except BaseException as error:
                self.result.update(complete=False, cleanup_error=str(error))
            finally:
                self.result['finalization_wall_s'] = time.monotonic()-started
                write_json(self.result_path, self.result)


def render_job(job_path):
    job = json.loads(Path(job_path).read_text())
    result = {'complete': False, 'encoded_frames': 0}
    renderer = None
    raw = Path(job['output_path']).with_suffix('.rgb')
    try:
        for path, expected in ((job['model_path'], job['model_sha256']),
                               (job['state_path'], job['state_sha256']),
                               (__file__, job['worker_sha256']),
                               (job['encoder_path'], job['encoder_sha256'])):
            if digest(path) != expected:
                raise RuntimeError('Video input identity changed: '+str(path))
        if mujoco.__version__ != job['mujoco_version'] or job['state_signature'] != SIGNATURE:
            raise RuntimeError('Video runtime changed')
        if runtime_binding() != job['runtime_binding']:
            raise RuntimeError('Video library or renderer changed')
        remaining(job['deadline'])
        model = mujoco.MjModel.from_binary_path(job['model_path'])
        check_workcell(model)
        with np.load(job['state_path'], allow_pickle=False) as archive:
            states, ticks = archive['states'], archive['ticks']
        count = job['captured_frames']
        if (not 1 <= count <= 2250 or states.shape != (count, mujoco.mj_stateSize(model, SIGNATURE))
                or states.dtype != np.float64 or not np.isfinite(states).all()
                or not np.array_equal(ticks, np.arange(count, dtype=np.int64)*2)):
            raise ValueError('Invalid recorded video states or ordering')
        data = mujoco.MjData(model)
        renderer = mujoco.Renderer(model, height=480, width=640)
        hashes = []
        audit_indices = np.linspace(0, count-1, min(100, count), dtype=np.int64)
        audit_frames = []
        audit_set = set(audit_indices.tolist())
        render_started = time.monotonic()
        with raw.open('xb') as stream:
            for index, state in enumerate(states):
                remaining(job['deadline'])
                mujoco.mj_setState(model, data, state, SIGNATURE)
                mujoco.mj_forward(model, data)  # Independent replay data; never mj_step.
                renderer.update_scene(data, camera='overview')
                frame = renderer.render()
                if frame.shape != (480, 640, 3) or frame.dtype != np.uint8:
                    raise RuntimeError('Invalid replay RGB frame')
                pixels = memoryview(np.ascontiguousarray(frame)).cast('B')
                if stream.write(pixels) != 640*480*3:
                    raise OSError('Incomplete replay frame write')
                hashes.append(hashlib.sha256(pixels).hexdigest())
                if index in audit_set:
                    audit_frames.append(frame.copy())
        finished_renderer, renderer = renderer, None
        finished_renderer.close()
        render_wall = time.monotonic()-render_started
        if raw.stat().st_size != count*640*480*3:
            raise RuntimeError('Replay raw byte count mismatch')
        audit_path = Path(job['output_path']).with_suffix('.rgb-audit.npz')
        with audit_path.open('xb') as stream:
            np.savez(stream, indices=audit_indices, rgb=np.stack(audit_frames))
        progress = Path(job['output_path']).with_suffix('.ffmpeg-progress.txt')
        command = [job['encoder_path'], '-n', '-f', 'rawvideo', '-vcodec', 'rawvideo',
                   '-s', '640x480', '-pix_fmt', 'rgb24', '-r', '25.00', '-i', str(raw),
                   '-an', '-vcodec', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '10',
                   '-v', 'error', '-nostats', '-progress', str(progress), job['output_path']]
        encode_started = time.monotonic()
        completed = subprocess.run(command, stdin=subprocess.DEVNULL, check=True,
                                   timeout=remaining(job['deadline']))
        values = dict(line.split('=', 1) for line in progress.read_text().splitlines() if '=' in line)
        if values.get('progress') != 'end' or int(values.get('frame', '-1')) != count:
            raise RuntimeError('FFmpeg did not finish all captured frames')
        if not Path(job['output_path']).is_file() or Path(job['output_path']).stat().st_size <= 0:
            raise RuntimeError('Encoded video is missing')
        if digest(job['encoder_path']) != job['encoder_sha256']:
            raise RuntimeError('Encoder changed during recording')
        raw.unlink()  # Remove only this worker's exclusive temporary file after success.
        remaining(job['deadline'])
        result.update(complete=True, encoded_frames=count, frame_rgb_sha256=hashes,
                      render_wall_s=render_wall, encode_wall_s=time.monotonic()-encode_started,
                      encoder_returncode=completed.returncode, encoder_sha256=job['encoder_sha256'],
                      model_sha256=job['model_sha256'], state_sha256=job['state_sha256'],
                      worker_sha256=job['worker_sha256'], video_sha256=digest(job['output_path']),
                      rgb_audit_sha256=digest(audit_path),
                      runtime_binding=runtime_binding(), ffmpeg_progress=values, command=command)
    except BaseException as error:
        result.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        try:
            if renderer is not None:
                renderer.close()
        except BaseException as error:
            result.update(complete=False, cleanup_error=str(error))
        finally:
            write_json(job['worker_result_path'], result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    render_job(parser.parse_args().job)
