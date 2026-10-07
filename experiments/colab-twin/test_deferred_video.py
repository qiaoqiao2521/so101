"""State ownership and bounded video completion; no physics or real rendering."""
from contextlib import ExitStack, contextmanager
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import mujoco
import numpy as np

import deferred_video as video


class WorkerProcess:
    """A terminated worker or one that times out once before being reaped."""
    pid = 71337

    def __init__(self, code=0, timeout=False, interrupt=False):
        self.code, self.timeout, self.interrupt = code, timeout, interrupt
        self.returncode, self.wait_timeouts = None, []

    def wait(self, timeout):
        self.wait_timeouts.append(timeout)
        if self.interrupt and len(self.wait_timeouts) == 1:
            raise KeyboardInterrupt('mock parent interrupted while waiting')
        if self.timeout and len(self.wait_timeouts) == 1:
            raise subprocess.TimeoutExpired('mock video worker', timeout)
        self.returncode = self.code
        return self.code

    def poll(self):
        return self.returncode


class DeferredVideoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.model = mujoco.MjModel.from_xml_string(
            '<mujoco><size nuserdata="2"/><worldbody>'
            '<camera name="overview" pos="0 0 1"/>'
            '<body><joint name="j" type="slide"/>'
            '<geom type="sphere" size=".01"/></body></worldbody>'
            '<actuator><position joint="j"/></actuator></mujoco>')
        self.data = mujoco.MjData(self.model)
        self.data.time = 1.25
        self.data.qpos[:] = .125
        self.data.qvel[:] = -.25
        self.data.ctrl[:] = .375
        self.data.qacc_warmstart[:] = .5
        self.data.qfrc_applied[:] = .625
        self.data.xfrc_applied[:, 0] = .75
        self.data.userdata[:] = [.875, 1.]
        self.encoder = self.root/'mock-ffmpeg'
        self.encoder.write_bytes(b'not an executable; subprocess is mocked')
        forbidden = AssertionError('Unit tests must not integrate, forward or render')
        for name in ('mj_step', 'mj_forward', 'Renderer'):
            p = patch.object(video.mujoco, name, side_effect=forbidden)
            p.start()
            self.addCleanup(p.stop)

    def recorder(self, name='video', max_frames=2):
        return video.DeferredVideo(self.model, self.root/(name+'.mp4'),
                                   max_frames=max_frames, deadline=time.monotonic()+60)

    def captured(self, name='video', count=2):
        recorder = self.recorder(name, max_frames=count)
        for index in range(count):
            self.data.time = 1.25+index*.04
            self.data.qpos[:] = .125+index*.01
            recorder.capture(self.data, index*2)
        return recorder

    def write_receipt(self, manifest, change=None, *, output=True):
        path = Path(manifest['output_path'])
        if output:
            path.write_bytes(b'mocked encoded video')
        count = manifest['captured_frames']
        audit = path.with_suffix('.rgb-audit.npz')
        indices = np.linspace(0, count-1, min(100, count), dtype=np.int64)
        frames = np.zeros((len(indices), 480, 640, 3), dtype=np.uint8)
        np.savez(audit, indices=indices, rgb=frames)
        rgb_digest = hashlib.sha256(frames[0].tobytes()).hexdigest()
        receipt = {key: manifest[key] for key in
                   ('model_sha256', 'state_sha256', 'worker_sha256', 'encoder_sha256',
                    'runtime_binding')}
        receipt.update(complete=True, encoded_frames=count, encoder_returncode=0,
                       ffmpeg_progress={'progress': 'end', 'frame': str(count)},
                       frame_rgb_sha256=[rgb_digest]*count,
                       rgb_audit_sha256=video.digest(audit),
                       video_sha256=video.digest(path) if output else '0'*64)
        if change:
            change(receipt)
        video.write_json(manifest['worker_result_path'], receipt)

    @contextmanager
    def worker(self, *, code=0, timeout=False, interrupt=False, change=None, output=True,
               receipt=True, invalid_json=False):
        process = WorkerProcess(code, timeout, interrupt)
        launches = []

        def launch(command, **kwargs):
            manifest = json.loads(Path(command[-1]).read_text())
            launches.append((command, kwargs, manifest))
            if invalid_json:
                Path(manifest['worker_result_path']).write_text('{broken')
            elif receipt:
                self.write_receipt(manifest, change, output=output)
            return process

        with patch('imageio_ffmpeg.get_ffmpeg_exe', return_value=str(self.encoder)), \
                patch.object(video.subprocess, 'Popen', side_effect=launch) as popen, \
                patch.object(video.os, 'killpg') as kill, \
                patch.object(video.os, 'getpgrp', return_value=42424):
            yield SimpleNamespace(process=process, launches=launches, popen=popen, kill=kill)

    def job(self, name='worker', count=2):
        recorder = self.captured(name, count)
        with self.worker():
            recorder.close()
        # The following test invokes render_job directly, with every renderer,
        # forward/setState and encoder operation mocked.
        recorder.path.unlink()
        recorder.path.with_suffix('.rgb-audit.npz').unlink()
        manifest = json.loads(recorder.manifest_path.read_text())
        Path(manifest['worker_result_path']).unlink()
        return recorder, manifest

    @contextmanager
    def replay(self, frames, *, encoder_error=None, progress=None, output=True):
        renderer = Mock()
        renderer.render.side_effect = list(frames)
        commands = []

        def encode(command, **kwargs):
            commands.append((command, kwargs))
            if encoder_error:
                raise encoder_error
            if output:
                Path(command[-1]).write_bytes(b'mocked encoded video')
            target = Path(command[command.index('-progress')+1])
            text = progress if progress is not None else f'frame={len(frames)}\nprogress=end\n'
            target.write_text(text)
            return SimpleNamespace(returncode=0)

        with ExitStack() as stack:
            stack.enter_context(patch.object(video.mujoco.MjModel, 'from_binary_path',
                                             return_value=self.model))
            render_factory = stack.enter_context(patch.object(video.mujoco, 'Renderer',
                                                               return_value=renderer))
            set_state = stack.enter_context(patch.object(video.mujoco, 'mj_setState'))
            forward = stack.enter_context(patch.object(video.mujoco, 'mj_forward'))
            run = stack.enter_context(patch.object(video.subprocess, 'run', side_effect=encode))
            yield SimpleNamespace(renderer=renderer, factory=render_factory,
                                  set_state=set_state, forward=forward, run=run,
                                  commands=commands)

    def test_snapshot_owns_complete_integration_state(self):
        recorder = self.recorder()
        expected = np.empty(recorder.state_size)
        mujoco.mj_getState(self.model, self.data, expected, video.SIGNATURE)
        recorder.capture(self.data, 0)
        self.data.qpos[:] = 9
        self.data.ctrl[:] = 8
        self.data.userdata[:] = 7
        self.data.qacc_warmstart[:] = 6
        recorder.capture(self.data, 2)
        np.testing.assert_array_equal(recorder.states[0], expected)
        self.assertFalse(np.array_equal(recorder.states[0], recorder.states[1]))
        self.assertFalse(np.shares_memory(recorder.states, self.data.qpos))
        with self.worker():
            recorder.close()
        with np.load(recorder.state_path, allow_pickle=False) as archive:
            np.testing.assert_array_equal(archive['states'][0], expected)
            np.testing.assert_array_equal(archive['ticks'], [0, 2])

    def test_frame_cap_and_tick_order_never_drop_or_reorder(self):
        recorder = self.recorder(max_frames=2)
        for tick in (True, -2, 1, 2, np.int64(0)):
            with self.subTest(tick=tick), self.assertRaises(ValueError):
                recorder.capture(self.data, tick)
            self.assertEqual(recorder.count, 0)
        recorder.capture(self.data, 0)
        for tick in (0, 1, 4):
            with self.subTest(tick=tick), self.assertRaises(ValueError):
                recorder.capture(self.data, tick)
        recorder.capture(self.data, 2)
        with self.assertRaisesRegex(RuntimeError, 'full'):
            recorder.capture(self.data, 4)
        self.assertEqual(recorder.report()['captured_frames'], 2)

    def test_nonfinite_snapshot_is_rejected_without_consuming_frame(self):
        recorder = self.recorder()
        for field in ('qpos', 'qvel', 'ctrl', 'qacc_warmstart', 'qfrc_applied', 'userdata'):
            array = getattr(self.data, field)
            old = array.copy()
            for bad in (np.nan, np.inf, -np.inf):
                with self.subTest(field=field, bad=bad):
                    array.flat[0] = bad
                    with self.assertRaisesRegex(ValueError, 'Nonfinite'):
                        recorder.capture(self.data, 0)
                    self.assertEqual(recorder.count, 0)
            array[:] = old
        recorder.capture(self.data, 0)
        self.assertEqual(recorder.count, 1)

    def test_constructor_rejects_invalid_caps_and_expired_deadlines(self):
        for cap in (True, 0, -1, 2251, 1.0, np.int64(1)):
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                video.DeferredVideo(self.model, self.root/'bad.mp4', max_frames=cap,
                                    deadline=time.monotonic()+60)
        for deadline in (float('nan'), float('inf'), -float('inf')):
            with self.subTest(deadline=deadline), self.assertRaises(ValueError):
                video.DeferredVideo(self.model, self.root/'bad.mp4', max_frames=1,
                                    deadline=deadline)
        with self.assertRaises(TimeoutError):
            video.DeferredVideo(self.model, self.root/'bad.mp4', max_frames=1,
                                deadline=time.monotonic()-1)
        self.assertFalse((self.root/'bad.mjb').exists())

    def test_existing_owned_paths_are_not_overwritten(self):
        for index, suffix in enumerate(('.mp4', '.mjb', '.states.npz', '.job.json', '.video.json')):
            path = self.root/f'owned-{index}.mp4'
            existing = path.with_suffix(suffix)
            existing.write_bytes(b'prior owner')
            with self.subTest(suffix=suffix), self.assertRaises(FileExistsError):
                video.DeferredVideo(self.model, path, max_frames=1,
                                    deadline=time.monotonic()+60)
            self.assertEqual(existing.read_bytes(), b'prior owner')

    def test_callbacks_are_rejected_without_installing_any_callback(self):
        for name in ('control', 'passive', 'sensor', 'act_dyn', 'act_gain', 'act_bias',
                     'contactfilter', 'time'):
            with self.subTest(name=name), \
                    patch.object(video.mujoco, 'get_mjcb_'+name, return_value=object()), \
                    self.assertRaisesRegex(ValueError, 'callbacks: '+name):
                self.recorder(name)
            self.assertFalse((self.root/(name+'.mjb')).exists())

    def test_sensors_and_plugins_are_rejected_before_serialization(self):
        for sensors, plugins in ((1, 0), (0, 1)):
            with self.subTest(sensors=sensors, plugins=plugins), \
                    patch.object(video, 'model_bytes') as binary, \
                    self.assertRaisesRegex(ValueError, 'sensor/plugin-free'):
                video.DeferredVideo(SimpleNamespace(nsensor=sensors, nplugin=plugins),
                                    self.root/'unsupported.mp4', max_frames=1,
                                    deadline=time.monotonic()+60)
            binary.assert_not_called()

    def test_model_change_fails_before_worker_and_retains_failure_report(self):
        recorder = self.captured(count=1)
        self.model.geom_rgba[0, 0] = .125
        with self.worker() as worker, self.assertRaisesRegex(RuntimeError, 'model changed'):
            recorder.close()
        worker.popen.assert_not_called()
        self.assertFalse(recorder.state_path.exists())
        self.assertFalse(json.loads(recorder.result_path.read_text())['complete'])

    def test_zero_frames_complete_without_starting_worker(self):
        recorder = self.recorder()
        with self.worker() as worker:
            recorder.close()
            recorder.close()
        worker.popen.assert_not_called()
        result = json.loads(recorder.result_path.read_text())
        self.assertTrue(result['complete'])
        self.assertTrue(result['empty'])
        self.assertEqual(result['encoded_frames'], 0)
        with np.load(recorder.state_path, allow_pickle=False) as archive:
            self.assertEqual(archive['states'].shape, (0, recorder.state_size))

    def test_success_is_bound_to_inputs_and_owned_process_and_is_idempotent(self):
        recorder = self.captured()
        with patch.dict(video.os.environ, {'BW_SESSION': 'test secret to remove'}), \
                self.worker() as worker:
            recorder.close()
            recorder.close()
        worker.popen.assert_called_once()
        command, kwargs, manifest = worker.launches[0]
        self.assertTrue(kwargs['start_new_session'])
        self.assertNotIn('BW_SESSION', kwargs['env'])
        self.assertEqual(command[-2], '--job')
        self.assertEqual(manifest['state_sha256'], video.digest(recorder.state_path))
        self.assertEqual(manifest['encoder_sha256'], video.digest(self.encoder))
        self.assertEqual(manifest['worker_sha256'], video.digest(video.__file__))
        self.assertEqual(manifest['runtime_binding'], video.runtime_binding())
        self.assertGreater(worker.process.wait_timeouts[0], 0)
        worker.kill.assert_not_called()
        self.assertTrue(recorder.report()['complete'])
        with self.assertRaisesRegex(RuntimeError, 'closed'):
            recorder.capture(self.data, 4)
        copy = recorder.report()
        copy['complete'] = False
        self.assertTrue(recorder.report()['complete'])

    def test_worker_timeout_kills_owned_group_and_reaps_with_bounded_wait(self):
        recorder = self.captured(count=1)
        with self.worker(timeout=True, code=-signal.SIGKILL) as worker, \
                self.assertRaisesRegex(TimeoutError, 'finalize_deadline'):
            recorder.close()
        worker.kill.assert_called_once_with(worker.process.pid, signal.SIGKILL)
        self.assertEqual(worker.process.wait_timeouts[-1], 2)
        result = json.loads(recorder.result_path.read_text())
        self.assertFalse(result['complete'])
        self.assertTrue(result['worker_reaped'])
        self.assertTrue(recorder.state_path.is_file())

    def test_nonzero_worker_exit_fails_even_with_a_success_receipt(self):
        recorder = self.captured(count=1)
        with self.worker(code=9) as worker, self.assertRaisesRegex(RuntimeError, 'worker_failed: 9'):
            recorder.close()
        self.assertEqual(recorder.report()['worker_returncode'], 9)
        self.assertFalse(recorder.report()['complete'])
        worker.kill.assert_called_once_with(worker.process.pid, signal.SIGKILL)

    def test_parent_keyboard_interrupt_still_reaps_worker_and_saves_failure(self):
        recorder = self.captured(count=1)
        with self.worker(interrupt=True, code=-signal.SIGKILL) as worker, \
                self.assertRaises(KeyboardInterrupt):
            recorder.close()
        worker.kill.assert_called_once_with(worker.process.pid, signal.SIGKILL)
        self.assertEqual(worker.process.wait_timeouts[-1], 2)
        self.assertIsNotNone(worker.process.poll())
        result = json.loads(recorder.result_path.read_text())
        self.assertFalse(result['complete'])
        self.assertTrue(result['worker_reaped'])
        self.assertEqual(result['error_type'], 'KeyboardInterrupt')
        self.assertTrue(recorder.state_path.is_file())

    def test_worker_receipt_checks_each_input_identity_and_frame_count(self):
        changes = {'complete': False, 'encoded_frames': 3, 'model_sha256': 'other',
                   'state_sha256': 'other', 'worker_sha256': 'other', 'encoder_sha256': 'other',
                   'runtime_binding': {'library_sha256': 'other'}}
        for index, (key, bad) in enumerate(changes.items()):
            recorder = self.captured('bad-receipt-'+str(index), count=1)
            with self.subTest(key=key), self.worker(change=lambda r, k=key, b=bad: r.update({k: b})), \
                    self.assertRaisesRegex(RuntimeError, 'result_invalid'):
                recorder.close()
            self.assertFalse(json.loads(recorder.result_path.read_text())['complete'])

    def test_exit_zero_cannot_accept_invalid_encoding_or_output_integrity(self):
        changes = (
            ('encoder-exit', lambda r: r.update(encoder_returncode=9), True),
            ('progress-end', lambda r: r.update(ffmpeg_progress={'progress': 'continue', 'frame': '1'}), True),
            ('progress-count', lambda r: r.update(ffmpeg_progress={'progress': 'end', 'frame': '0'}), True),
            ('rgb-count', lambda r: r.update(frame_rgb_sha256=[]), True),
            ('video-hash', lambda r: r.update(video_sha256='0'*64), True),
            ('video-missing', None, False),
        )
        for name, change, output in changes:
            recorder = self.captured(name, count=1)
            with self.subTest(name=name):
                with self.worker(change=change, output=output), self.assertRaises(RuntimeError):
                    recorder.close()
                self.assertFalse(recorder.report()['complete'])

    def test_missing_or_malformed_worker_receipt_is_failure(self):
        for name, settings, expected in (
                ('missing', {'receipt': False}, FileNotFoundError),
                ('malformed', {'invalid_json': True}, json.JSONDecodeError)):
            recorder = self.captured(name, count=1)
            with self.subTest(name=name), self.worker(**settings), self.assertRaises(expected):
                recorder.close()
            self.assertFalse(json.loads(recorder.result_path.read_text())['complete'])

    def test_rgb_audit_tampering_wrong_indices_and_pixel_hash_are_rejected(self):
        for name in ('tampered-bytes', 'wrong-indices', 'wrong-pixels'):
            recorder = self.captured(name)
            audit = recorder.path.with_suffix('.rgb-audit.npz')

            def change(receipt, mode=name):
                if mode == 'tampered-bytes':
                    with audit.open('ab') as stream:
                        stream.write(b'tampered after recording')
                    return
                with np.load(audit, allow_pickle=False) as archive:
                    indices, frames = archive['indices'].copy(), archive['rgb'].copy()
                if mode == 'wrong-indices':
                    indices = indices[::-1]
                else:
                    frames[0, 0, 0, 0] = 1
                np.savez(audit, indices=indices, rgb=frames)
                receipt['rgb_audit_sha256'] = video.digest(audit)

            expected = 'identity_invalid' if name == 'tampered-bytes' else 'frames_invalid'
            with self.subTest(name=name), self.worker(change=change), \
                    self.assertRaisesRegex(RuntimeError, expected):
                recorder.close()
            self.assertFalse(json.loads(recorder.result_path.read_text())['complete'])

    def test_deadline_after_worker_success_still_fails(self):
        recorder = self.captured(count=1)
        with self.worker(), patch.object(video, 'remaining', side_effect=[.1, TimeoutError('expired')]), \
                self.assertRaises(TimeoutError):
            recorder.close()
        self.assertFalse(recorder.report()['complete'])

    def test_group_stop_refuses_invalid_or_callers_group(self):
        for pid in (0, 1, 42424):
            process = Mock(pid=pid)
            with self.subTest(pid=pid), patch.object(video.os, 'getpgrp', return_value=42424), \
                    patch.object(video.os, 'killpg') as kill, self.assertRaises(RuntimeError):
                video.stop_owned_group(process)
            kill.assert_not_called()
            process.wait.assert_not_called()

    def test_worker_success_preserves_frame_order_and_exact_encoder_contract(self):
        recorder, manifest = self.job()
        frames = [np.full((480, 640, 3), value, dtype=np.uint8) for value in (17, 203)]
        with self.replay(frames) as replay:
            video.render_job(recorder.manifest_path)
        replay.factory.assert_called_once_with(self.model, height=480, width=640)
        self.assertEqual(replay.forward.call_count, 2)  # Mock only, no engine evaluation.
        self.assertEqual(replay.set_state.call_count, 2)
        with np.load(recorder.state_path, allow_pickle=False) as archive:
            for index, call in enumerate(replay.set_state.call_args_list):
                np.testing.assert_array_equal(call.args[2], archive['states'][index])
                self.assertEqual(call.args[3], video.SIGNATURE)
        for call in replay.renderer.update_scene.call_args_list:
            self.assertEqual(call.kwargs, {'camera': 'overview'})
        replay.renderer.close.assert_called_once()
        command, kwargs = replay.commands[0]
        for flag, value in (('-r', '25.00'), ('-s', '640x480'), ('-crf', '10'),
                            ('-progress', str(recorder.path.with_suffix('.ffmpeg-progress.txt')))):
            self.assertEqual(command[command.index(flag)+1], value)
        self.assertEqual(command.count('libx264'), 1)
        self.assertEqual(command.count('yuv420p'), 1)
        self.assertTrue(kwargs['check'])
        self.assertGreater(kwargs['timeout'], 0)
        result = json.loads(Path(manifest['worker_result_path']).read_text())
        self.assertTrue(result['complete'])
        self.assertEqual(result['encoded_frames'], 2)
        self.assertEqual(result['frame_rgb_sha256'],
                         [hashlib.sha256(f.tobytes()).hexdigest() for f in frames])
        self.assertEqual(result['video_sha256'], video.digest(recorder.path))
        audit = recorder.path.with_suffix('.rgb-audit.npz')
        self.assertEqual(result['rgb_audit_sha256'], video.digest(audit))
        with np.load(audit, allow_pickle=False) as archive:
            np.testing.assert_array_equal(archive['indices'], [0, 1])
            np.testing.assert_array_equal(archive['rgb'], frames)
        self.assertFalse(recorder.path.with_suffix('.rgb').exists())

    def test_worker_rejects_invalid_recorded_states_before_render_or_encode(self):
        for name in ('nonfinite', 'shape', 'dtype', 'order'):
            recorder, manifest = self.job(name)
            with np.load(recorder.state_path, allow_pickle=False) as archive:
                states, ticks = archive['states'].copy(), archive['ticks'].copy()
            if name == 'nonfinite': states[0, 0] = np.nan
            elif name == 'shape': states = states[:, :-1]
            elif name == 'dtype': states = states.astype(np.float32)
            elif name == 'order': ticks = ticks[::-1]
            np.savez(recorder.state_path, states=states, ticks=ticks)
            manifest['state_sha256'] = video.digest(recorder.state_path)
            video.write_json(recorder.manifest_path, manifest)
            with self.subTest(name=name), self.replay([]) as replay, \
                    self.assertRaisesRegex(ValueError, 'recorded video states'):
                video.render_job(recorder.manifest_path)
            replay.factory.assert_not_called()
            replay.run.assert_not_called()
            self.assertFalse(json.loads(Path(manifest['worker_result_path']).read_text())['complete'])

    def test_worker_rejects_input_identity_change_before_model_load(self):
        recorder, manifest = self.job()
        recorder.model_path.write_bytes(b'changed model')
        with patch.object(video.mujoco.MjModel, 'from_binary_path') as load, \
                self.assertRaisesRegex(RuntimeError, 'input identity changed'):
            video.render_job(recorder.manifest_path)
        load.assert_not_called()
        self.assertFalse(json.loads(Path(manifest['worker_result_path']).read_text())['complete'])

    def test_runtime_drift_before_parent_finalize_prevents_worker_launch(self):
        for key in ('library_sha256', 'renderer_sha256'):
            recorder = self.captured('parent-runtime-'+key, count=1)
            changed = dict(recorder.runtime, **{key: 'changed'})
            with self.subTest(key=key), self.worker() as worker, \
                    patch.object(video, 'runtime_binding', return_value=changed), \
                    self.assertRaisesRegex(RuntimeError, 'source or runtime changed'):
                recorder.close()
            worker.popen.assert_not_called()
            self.assertFalse(recorder.state_path.exists())
            self.assertFalse(json.loads(recorder.result_path.read_text())['complete'])

    def test_runtime_drift_after_worker_success_cannot_be_marked_complete(self):
        recorder = self.captured(count=1)
        changed = dict(recorder.runtime, library_sha256='changed')
        with self.worker(), patch.object(video, 'runtime_binding',
                                         side_effect=[recorder.runtime, changed]), \
                self.assertRaisesRegex(RuntimeError, 'runtime changed during finalization'):
            recorder.close()
        self.assertFalse(json.loads(recorder.result_path.read_text())['complete'])

    def test_worker_runtime_drift_is_rejected_before_model_or_renderer(self):
        recorder, manifest = self.job()
        changed = dict(manifest['runtime_binding'], library_sha256='changed')
        with patch.object(video, 'runtime_binding', return_value=changed), \
                patch.object(video.mujoco.MjModel, 'from_binary_path') as load, \
                self.assertRaisesRegex(RuntimeError, 'library or renderer changed'):
            video.render_job(recorder.manifest_path)
        load.assert_not_called()
        self.assertFalse(json.loads(Path(manifest['worker_result_path']).read_text())['complete'])

    def test_renderer_close_failure_retains_report_and_original_failure(self):
        for name, frame in (('ordinary-close', np.zeros((480, 640, 3), dtype=np.uint8)),
                            ('cleanup-close', np.zeros((1, 2, 3), dtype=np.uint8))):
            recorder, manifest = self.job(name, count=1)
            with self.subTest(name=name), self.replay([frame]) as replay:
                replay.renderer.close.side_effect = OSError('mock renderer close failed')
                expected = OSError if name == 'ordinary-close' else RuntimeError
                with self.assertRaises(expected):
                    video.render_job(recorder.manifest_path)
                replay.renderer.close.assert_called_once()
                replay.run.assert_not_called()
            result = json.loads(Path(manifest['worker_result_path']).read_text())
            self.assertFalse(result['complete'])
            self.assertTrue(recorder.path.with_suffix('.rgb').is_file())
            if name == 'ordinary-close':
                self.assertEqual(result['error_type'], 'OSError')
            else:
                self.assertEqual(result['error_type'], 'RuntimeError')
                self.assertIn('Invalid replay RGB', result['error'])
                self.assertIn('mock renderer close failed', result['cleanup_error'])

    def test_ffmpeg_errors_preserve_raw_and_propagate_failure(self):
        errors = (subprocess.TimeoutExpired('mock ffmpeg', .01),
                  subprocess.CalledProcessError(7, 'mock ffmpeg'))
        for index, error in enumerate(errors):
            recorder, manifest = self.job('ffmpeg-error-'+str(index), count=1)
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            with self.subTest(error=type(error).__name__), self.replay([frame], encoder_error=error) as replay, \
                    self.assertRaises(type(error)):
                video.render_job(recorder.manifest_path)
            replay.renderer.close.assert_called_once()
            self.assertTrue(recorder.path.with_suffix('.rgb').is_file())
            self.assertFalse(json.loads(Path(manifest['worker_result_path']).read_text())['complete'])

    def test_ffmpeg_incomplete_progress_or_missing_video_preserves_raw(self):
        cases = (('not-end', 'frame=1\nprogress=continue\n', True),
                 ('wrong-count', 'frame=0\nprogress=end\n', True),
                 ('missing-output', 'frame=1\nprogress=end\n', False))
        for name, progress, output in cases:
            recorder, manifest = self.job(name, count=1)
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            with self.subTest(name=name), self.replay([frame], progress=progress, output=output), \
                    self.assertRaises(RuntimeError):
                video.render_job(recorder.manifest_path)
            self.assertTrue(recorder.path.with_suffix('.rgb').is_file())
            self.assertFalse(json.loads(Path(manifest['worker_result_path']).read_text())['complete'])

    def test_invalid_rgb_rejects_before_ffmpeg_and_closes_renderer(self):
        for name, frame in (('shape', np.zeros((1, 2, 3), dtype=np.uint8)),
                            ('dtype', np.zeros((480, 640, 3), dtype=np.float32))):
            recorder, manifest = self.job(name, count=1)
            with self.subTest(name=name), self.replay([frame]) as replay, \
                    self.assertRaisesRegex(RuntimeError, 'Invalid replay RGB'):
                video.render_job(recorder.manifest_path)
            replay.run.assert_not_called()
            replay.renderer.close.assert_called_once()
            self.assertFalse(json.loads(Path(manifest['worker_result_path']).read_text())['complete'])


class OwnedWorkerGroupTests(unittest.TestCase):
    def test_real_isolated_sleep_worker_timeout_is_killed_and_reaped(self):
        # This is the only real subprocess test. It creates no MuJoCo model,
        # renderer or encoder, and never signals an inherited process group.
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            self.assertGreater(process.pid, 1)
            self.assertNotEqual(process.pid, os.getpgrp())
            self.assertEqual(os.getpgid(process.pid), process.pid)
            with self.assertRaises(subprocess.TimeoutExpired):
                process.wait(timeout=.03)
            video.stop_owned_group(process)
            self.assertEqual(process.poll(), -signal.SIGKILL)
            with self.assertRaises(ProcessLookupError):
                os.killpg(process.pid, 0)
        finally:
            if process.poll() is None:
                # The process was started above in its own new session.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=2)


if __name__ == '__main__':
    unittest.main()
