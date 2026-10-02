"""Late-recovery admission and real HDF5 labels, without simulator execution."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

import collect_policy_recovery as collector
from learning_data import EpisodeRecorder, POLICY_OBSERVATION_KEYS, load_episode, training_rows
from learning_env import PhysicalTaskMonitor


def observation(index=0):
    state = np.arange(6, dtype=np.float64) * .01 + index * .001
    state[5] = .5
    environment = np.arange(30, dtype=np.float64) * .001 + index * .002
    environment[6:9] = [.24, -.13, .01]
    return {"observation.state": state, "observation.environment_state": environment,
            "time_s": 1. + index * .02}


def physical_row(time_s=1., **changes):
    return {"time_s": time_s, "finite_state": True, "arm_valid": True,
            "obstacle_contact": False, "tip_forces_n": [.03, .04],
            "object_z_m": .04, "floor_contact": False, "place_floor_contact": False,
            "in_place_tray": False, "object_speed_m_s": .01,
            "pinch_xyz_m": [.24, -.13, .06], **changes}


def metadata():
    return {"control_period_s": .02, "physics_dt_s": .002, "seed": 0,
            "model_sha256": "a" * 64, "scene_configuration": {},
            "initial_snapshot": {"qpos": observation()["observation.state"].tolist()}}


class PrefixBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.initial = observation()

    def archive(self, count=3, period=.02, **changes):
        times = self.initial["time_s"] + np.arange(count) * period
        commands = np.tile(np.array([.123456791, -.2, .3, -.4, .5, .015], dtype=np.float32), (count, 1))
        values = {"action": commands, "raw_action": commands + 2,
                  "timestamp": times, "next_timestamp": times + period,
                  **{key: np.repeat(self.initial[key][None], count, axis=0)
                     for key in POLICY_OBSERVATION_KEYS}, **changes}
        path = self.root / "prefix.npz"
        np.savez(path, **values)
        return path, values

    def test_uses_executed_commands_at_raw_precision_not_model_outputs(self):
        path, values = self.archive()
        commands = collector.load_recovery_prefix(path, 2, .02, self.initial)
        self.assertEqual(commands.dtype, np.dtype("float64"))
        np.testing.assert_array_equal(commands, values["action"][:2].astype(np.float64))
        self.assertFalse(np.array_equal(commands, values["raw_action"][:2]))

    def test_accepts_exact_sixty_second_boundary(self):
        path, _ = self.archive(count=3000)
        self.assertEqual(collector.load_recovery_prefix(path, 3000, .02, self.initial).shape, (3000, 6))
        path, _ = self.archive(count=1000, period=.06)
        self.assertEqual(collector.load_recovery_prefix(path, 1000, .06, self.initial).shape, (1000, 6))

    def test_rejects_invalid_cycles_and_budgets_before_loading(self):
        missing = self.root / "must-not-open.npz"
        for cycles, period in [(0, .02), (3001, .02), (True, .02), (1.5, .02),
                               (3000, .020001), (1, 60.000001), (1, 0.), (1, -.02),
                               (1, np.nan), (1, np.inf)]:
            with self.subTest(cycles=cycles, period=period), self.assertRaisesRegex(ValueError, "60 seconds"):
                collector.load_recovery_prefix(missing, cycles, period, self.initial)

    def test_control_period_origin_and_continuity_must_match_reset(self):
        _, good = self.archive()
        shifted = good["timestamp"] + .001
        cases = [{"timestamp": shifted, "next_timestamp": good["next_timestamp"] + .001},
                 {"next_timestamp": good["next_timestamp"] + .0001},
                 {"timestamp": np.array([1., 1.03, 1.05]),
                  "next_timestamp": np.array([1.02, 1.05, 1.07])}]
        for changes in cases:
            with self.subTest(changes=changes):
                path, _ = self.archive(**changes)
                with self.assertRaisesRegex(ValueError, "reset control cadence"):
                    collector.load_recovery_prefix(path, 3, .02, self.initial)

    def test_rejects_truncated_malformed_and_nonfinite_commands_or_times(self):
        for changes in [{"action": np.zeros((2, 6))}, {"action": np.zeros((3, 5))},
                        {"timestamp": np.array([1., 1.02])},
                        {"action": np.full((3, 6), np.nan)},
                        {"action": np.full((3, 6), np.inf)},
                        {"timestamp": np.array([1., np.nan, 1.04])},
                        {"next_timestamp": np.array([1.02, 1.04, np.inf])}]:
            with self.subTest(changes=list(changes)):
                path, _ = self.archive(**changes)
                with self.assertRaisesRegex(ValueError, "finite.*cadence"):
                    collector.load_recovery_prefix(path, 3, .02, self.initial)

    def test_initial_robot_and_scene_observations_must_match(self):
        for key in POLICY_OBSERVATION_KEYS:
            for invalid in (self.initial[key] + .001, np.full(self.initial[key].shape, np.nan),
                            self.initial[key][:-1]):
                with self.subTest(key=key, width=len(invalid)):
                    path, _ = self.archive(**{key: np.repeat(invalid[None], 3, axis=0)})
                    with self.assertRaisesRegex(ValueError, "reference scene"):
                        collector.load_recovery_prefix(path, 3, .02, self.initial)


class RecoveryAdmissionTests(unittest.TestCase):
    def sustained_monitor(self):
        monitor = PhysicalTaskMonitor(.01)
        monitor.update(physical_row(0.))
        row = physical_row(1.)
        monitor.update(row)
        return monitor, row

    def test_held_admits_current_one_second_dual_lift(self):
        monitor, row = self.sustained_monitor()
        collector.recovery_admission("held", observation(), row, monitor)

    def test_historical_grasp_does_not_admit_contact_loss_or_short_reacquisition(self):
        monitor, _ = self.sustained_monitor()
        lost = physical_row(1.02, tip_forces_n=[0., .04])
        monitor.update(lost)
        self.assertTrue(monitor.grasp_success)
        self.assertIsNone(monitor.lift_start)
        self.assertIsNone(monitor.failure_reason, "Exercise the interval before payload_lost is terminal")
        with self.assertRaisesRegex(RuntimeError, "sustained current"):
            collector.recovery_admission("held", observation(), lost, monitor)
        for time_s in (1.04, 1.54):
            row = physical_row(time_s)
            monitor.update(row)
        self.assertTrue(monitor.grasp_success)
        with self.assertRaisesRegex(RuntimeError, "sustained current"):
            collector.recovery_admission("held", observation(), row, monitor)

    def test_held_rejects_insufficient_duration_height_single_contact_and_support(self):
        for changes in ({"time_s": .98}, {"object_z_m": .0349},
                        {"tip_forces_n": [.02, .04]}, {"floor_contact": True},
                        {"place_floor_contact": True}):
            monitor, _ = self.sustained_monitor()
            row = physical_row(**changes)
            with self.subTest(changes=changes), self.assertRaisesRegex(RuntimeError, "sustained current"):
                collector.recovery_admission("held", observation(), row, monitor)

    def test_approach_rejects_either_contact_or_lift_at_boundary(self):
        monitor = PhysicalTaskMonitor(.01)
        allowed = physical_row(tip_forces_n=[.02, .02], object_z_m=.015)
        collector.recovery_admission("approach", observation(), allowed, monitor)
        for changes in ({"tip_forces_n": [.02001, 0.]}, {"tip_forces_n": [0., .02001]},
                        {"object_z_m": .01501}):
            row = physical_row(tip_forces_n=[0., 0.], object_z_m=.01)
            row.update(changes)
            with self.subTest(changes=changes), self.assertRaisesRegex(RuntimeError, "contact-free"):
                collector.recovery_admission("approach", observation(), row, monitor)

    def test_approach_rejects_low_closing_or_laterally_misaligned_prefix(self):
        # Contact-free is insufficient: an about-to-close low pose must not
        # receive a hover/open label that contradicts the grasp boundary.
        for pinch, jaw in (([.24, -.13, .025], .5), ([.24, -.13, .06], .3),
                           ([.26, -.13, .06], .5)):
            monitor = PhysicalTaskMonitor(.01)
            row = physical_row(tip_forces_n=[0., 0.], object_z_m=.01, pinch_xyz_m=pinch)
            current = observation()
            current["observation.state"][5] = jaw
            with self.subTest(pinch=pinch, jaw=jaw), self.assertRaises(RuntimeError):
                collector.recovery_admission("approach", current, row, monitor)

    def test_both_modes_reject_failed_unsafe_and_nonfinite_policy_observations(self):
        for mode in ("held", "approach"):
            for flag in ("finite_state", "arm_valid", "obstacle_contact"):
                monitor, row = self.sustained_monitor()
                row[flag] = flag == "obstacle_contact"
                with self.subTest(mode=mode, flag=flag), self.assertRaisesRegex(RuntimeError, "unsafe"):
                    collector.recovery_admission(mode, observation(), row, monitor)
            monitor, row = self.sustained_monitor()
            monitor.failure_reason = "payload_lost"
            with self.subTest(mode=mode), self.assertRaisesRegex(RuntimeError, "failed"):
                collector.recovery_admission(mode, observation(), row, monitor)
        for key in POLICY_OBSERVATION_KEYS:
            monitor, row = self.sustained_monitor()
            invalid = observation()
            invalid[key][0] = np.nan
            with self.subTest(key=key), self.assertRaisesRegex(RuntimeError, "Nonfinite"):
                collector.recovery_admission("held", invalid, row, monitor)

    def test_nonfinite_physical_evidence_cannot_admit_a_prefix(self):
        for field, value in (("tip_forces_n", [np.nan, 0.]), ("object_z_m", np.nan),
                             ("time_s", np.nan), ("object_speed_m_s", np.inf)):
            monitor = PhysicalTaskMonitor(.01)
            row = physical_row(tip_forces_n=[0., 0.], object_z_m=.01)
            row[field] = value
            monitor.update(row)
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                collector.recovery_admission("approach", observation(), row, monitor)


class ReleaseAdmissionTests(unittest.TestCase):
    def ready_release(self, **changes):
        monitor = PhysicalTaskMonitor(.01)
        monitor.update(physical_row(0.))
        monitor.update(physical_row(1.))
        row = physical_row(2., object_z_m=.013, in_place_tray=True, **changes)
        monitor.update(row)
        current = observation()
        current["time_s"] = row["time_s"]
        current["observation.state"][5] = .116
        current["observation.environment_state"][6:9] = [.24, .14, row["object_z_m"]]
        return monitor, row, current

    def admit(self, monitor, row, current, duration=1.):
        collector.recovery_admission("release", current, row, monitor,
                                     current_contact_duration_s=duration)

    def test_ready_release_uses_current_contact_clock_when_lift_clock_has_reset(self):
        monitor, row, current = self.ready_release()
        self.assertTrue(monitor.grasp_success)
        self.assertIsNone(monitor.lift_start)
        self.admit(monitor, row, current)

    def test_release_height_and_speed_boundaries_match_existing_release_condition(self):
        for z, speed in ((.010, .05), (.014499999, 0.)):
            monitor, row, current = self.ready_release()
            row.update(object_z_m=z, object_speed_m_s=speed)
            current["observation.environment_state"][8] = z
            with self.subTest(z=z, speed=speed):
                self.admit(monitor, row, current)

    def test_missing_nonfinite_or_malformed_current_contact_duration_is_rejected(self):
        monitor, row, current = self.ready_release()
        for duration in (None, np.nan, np.inf, -1., True, "1.2", np.array([1.2])):
            with self.subTest(duration=duration), self.assertRaisesRegex(RuntimeError, "duration evidence"):
                self.admit(monitor, row, current, duration)

    def test_historical_grasp_cannot_replace_current_one_second_dual_contact(self):
        monitor, row, current = self.ready_release()
        self.assertGreaterEqual(monitor.hold_duration, 1.)
        for duration in (0., .5, .999):
            with self.subTest(duration=duration), self.assertRaisesRegex(RuntimeError, "current sustained"):
                self.admit(monitor, row, current, duration)
        row["tip_forces_n"] = [.02, .04]
        with self.assertRaisesRegex(RuntimeError, "current sustained"):
            self.admit(monitor, row, current, 2.)

    def test_release_rejects_missing_historical_grasp_even_with_current_contact(self):
        monitor, row, current = self.ready_release()
        monitor.grasp_success = False
        with self.assertRaisesRegex(RuntimeError, "current sustained"):
            self.admit(monitor, row, current)

    def test_release_rejects_blue_outside_low_high_height_or_floor_support(self):
        for changes in ({"in_place_tray": False}, {"object_z_m": .009999},
                        {"object_z_m": .0145}, {"floor_contact": True},
                        {"place_floor_contact": True}, {"object_speed_m_s": .050001},
                        {"object_speed_m_s": -.01}):
            monitor, row, current = self.ready_release()
            row.update(changes)
            with self.subTest(changes=changes), self.assertRaisesRegex(RuntimeError, "current sustained"):
                self.admit(monitor, row, current)

    def test_release_rejects_failed_unsafe_or_nonfinite_physical_evidence(self):
        for field, value in (("finite_state", False), ("arm_valid", False),
                             ("obstacle_contact", True), ("object_z_m", np.nan),
                             ("object_speed_m_s", np.inf), ("time_s", np.nan),
                             ("tip_forces_n", [.03, np.nan]), ("in_place_tray", np.nan)):
            monitor, row, current = self.ready_release()
            row[field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.admit(monitor, row, current)
        monitor, row, current = self.ready_release()
        monitor.failure_reason = "payload_lost"
        with self.assertRaisesRegex(RuntimeError, "failed"):
            self.admit(monitor, row, current)

    def test_release_rejects_nonfinite_or_malformed_actual_observation(self):
        for key in POLICY_OBSERVATION_KEYS:
            for value in (np.full(observation()[key].shape, np.nan), observation()[key][:-1]):
                monitor, row, current = self.ready_release()
                current[key] = value
                with self.subTest(key=key, shape=value.shape), self.assertRaises(RuntimeError):
                    self.admit(monitor, row, current)
        for timestamp in (np.nan, True, "2.0", None, np.array([2.])):
            monitor, row, current = self.ready_release()
            current["time_s"] = timestamp
            with self.subTest(timestamp=timestamp), self.assertRaisesRegex(RuntimeError, "Nonfinite"):
                self.admit(monitor, row, current)


class LabelArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_successful_correction_trains_only_actual_valid_labels(self):
        recorder = EpisodeRecorder(self.root / "corrected.h5", metadata())
        command = np.array([.123456789123, -.2, .3, -.4, .5, .015], dtype=np.float64)
        for index in range(2):
            recorder.append(observation(index), None, command, observation(index+1),
                            False, "policy_prefix", True)
        brake = observation(2)["observation.state"].copy()
        recorder.append(observation(2), brake, brake, observation(3), True, "recovery_brake", False)
        path = recorder.finalize({"passed": True})
        episode = load_episode(path)
        self.assertTrue(np.isnan(episode["action"][:2]).all())
        self.assertEqual(episode["label_valid"].tolist(), [False, False, True])
        np.testing.assert_array_equal(episode["executed_action"][:2], np.tile(command, (2, 1)))
        rows = training_rows([path])
        self.assertEqual(rows["frame_index"].tolist(), [2])
        np.testing.assert_array_equal(rows["action"], brake[None])
        self.assertNotIn("stage", rows)
        self.assertNotIn("timestamp", rows)

    def failed_collection(self, *, mode, max_correction_s=60.):
        reference = self.root / "reference.h5"
        recorder = EpisodeRecorder(reference, metadata())
        recorder.append(observation(), np.zeros(6), np.zeros(6), observation(1), True, "reference", False)
        recorder.finalize({"passed": True})
        attempt = self.root / "attempt-000-nominal"
        attempt.mkdir()
        prefix = attempt / "policy-transitions.npz"
        commands = np.array([[.11, .12, .13, .14, .15, .5], [.21, .22, .23, .24, .25, .5]])
        # A saved later pose must not replace the state reached by real commands.
        np.savez(prefix, action=commands, timestamp=[1., 1.02], next_timestamp=[1.02, 1.04],
                 **{key: np.stack([observation()[key], np.full_like(observation()[key], 99.)])
                    for key in POLICY_OBSERVATION_KEYS})
        policy_report = self.root / "policy-report.json"
        policy_report.write_text(json.dumps({"expert_intervention": False,
            "policy_inputs": list(POLICY_OBSERVATION_KEYS), "attempts": [{"directory": attempt.name}],
            "reference_dataset_sha256": [hashlib.sha256(reference.read_bytes()).hexdigest()],
            "checkpoint_sha256": "b" * 64}))

        class CommandOnlyCell:
            period = .02
            baseline_z = .01

            def __init__(self, *args):
                self.index = 0
                self.model = SimpleNamespace(body=lambda name: SimpleNamespace(id=0))
                self.data = SimpleNamespace(time=1.,
                    xpos=np.array([[.24, -.13, .06]]) - collector.PINCH_POINT,
                    xmat=np.eye(3).reshape(1, 9))
                self.checker = SimpleNamespace(model=object())

            def reset(self):
                return observation()

            def step(self, command):
                self.index += 1
                after = observation(self.index)
                self.data.time = after["time_s"]
                return after, physical_row(after["time_s"], tip_forces_n=[0., 0.], object_z_m=.01)

        destination = self.root / "failed-correction"
        with patch.object(collector, "StateWorkcell", CommandOnlyCell), \
                patch.object(collector, "solve_pinch_ik", side_effect=RuntimeError("fixture planner failure")):
            report = collector.collect(reference, prefix, policy_report, self.root / "unused.xml",
                                       destination, cycles=2, mode=mode, max_correction_s=max_correction_s)
        return report, load_episode(destination / "expert.h5"), destination / "expert.h5", commands

    def test_collector_retains_unlabelled_failed_prefix_without_restoring_saved_pose(self):
        report, episode, path, commands = self.failed_collection(mode="held")
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["recorded_steps"], 2)
        self.assertIn("sustained current", report["error"]["message"])
        self.assertTrue(np.isnan(episode["action"]).all())
        self.assertFalse(episode["label_valid"].any())
        np.testing.assert_array_equal(episode["executed_action"], commands)
        np.testing.assert_array_equal(episode["next_observation.state"][-1], observation(2)["observation.state"])
        self.assertEqual(training_rows([path])["action"].shape, (0, 6))

    def test_failed_complete_attempt_excludes_even_valid_measured_brake_labels(self):
        report, episode, path, _ = self.failed_collection(mode="approach")
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error"]["message"], "fixture planner failure")
        self.assertEqual(episode["label_valid"].tolist(), [False, False, True])
        np.testing.assert_array_equal(episode["action"][2, :5], episode["observation.state"][2, :5])
        self.assertEqual(episode["action"][2, 5], .5)
        self.assertFalse(episode["eligible_for_training"])
        self.assertEqual(training_rows([path])["action"].shape, (0, 6))

    def test_first_correction_command_cannot_cross_its_simulation_budget(self):
        report, episode, path, _ = self.failed_collection(mode="approach", max_correction_s=.01)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error"]["type"], "TimeoutError")
        self.assertIn("simulation budget", report["error"]["message"])
        self.assertEqual(report["recorded_steps"], 2)
        self.assertFalse(episode["label_valid"].any())
        self.assertEqual(training_rows([path])["action"].shape, (0, 6))


class LowerChordGuardTests(unittest.TestCase):
    """Exercise the collector entry point; mocked execution is not physics proof."""
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.case = 0

    def collect_lower(self, *, payload_allowed, arm_open_allowed=True):
        self.case += 1
        root = self.root / str(self.case)
        root.mkdir()
        reference = root / "reference.h5"
        recorder = EpisodeRecorder(reference, metadata())
        recorder.append(observation(), np.zeros(6), np.zeros(6), observation(1), True, "reference", False)
        recorder.finalize({"passed": True})
        cycles = 51  # Real monitor admission needs a current full second of lift.
        attempt = root / "attempt-000-nominal"
        attempt.mkdir()
        prefix = attempt / "policy-transitions.npz"
        command = observation()["observation.state"].copy()
        command[5] = .015
        times = 1. + np.arange(cycles) * .02
        np.savez(prefix, action=np.repeat(command[None], cycles, axis=0),
                 timestamp=times, next_timestamp=times+.02,
                 **{key: np.repeat(observation()[key][None], cycles, axis=0)
                    for key in POLICY_OBSERVATION_KEYS})
        policy_report = root / "policy-report.json"
        policy_report.write_text(json.dumps({"expert_intervention": False,
            "policy_inputs": list(POLICY_OBSERVATION_KEYS), "attempts": [{"directory": attempt.name}],
            "reference_dataset_sha256": [hashlib.sha256(reference.read_bytes()).hexdigest()]}))
        cells, payload_queries = [], []

        class CommandOnlyCell:
            period = .02
            baseline_z = .01

            def __init__(self, *args):
                cells.append(self)
                self.steps = self.lower_steps = 0
                self.open_attempts = []
                self.arm_open_queries = []
                self.model = SimpleNamespace(body=lambda name: SimpleNamespace(id=0))
                self.data = SimpleNamespace(time=1., qpos=observation()["observation.state"].copy(),
                    xpos=np.array([[.24, -.13, .06]]) - collector.PINCH_POINT,
                    xmat=np.eye(3).reshape(1, 9))
                self.checker = SimpleNamespace(model=object(), evaluate=self.evaluate)

            def evaluate(self, q, **kwargs):
                if self.lower_steps >= 2 and q[5] == .5:
                    self.arm_open_queries.append(np.asarray(q).copy())
                    return {"valid": arm_open_allowed}
                return {"valid": True}

            def reset(self):
                return observation()

            def step(self, command):
                if self.steps >= cycles+1:
                    if command[5] == .5:
                        self.open_attempts.append(np.asarray(command).copy())
                        raise RuntimeError("fixture stops at geometry-admitted open command")
                    self.lower_steps += 1
                self.steps += 1
                self.data.qpos[:] = command
                after = observation(self.steps)
                after["observation.state"] = self.data.qpos.copy()
                in_tray = self.lower_steps >= 2
                z = .0144 if in_tray else .04
                after["observation.environment_state"][6:9] = [.24, .14 if in_tray else -.13, z]
                self.data.time = after["time_s"]
                # Opening is admitted with contact still live; release is not
                # supposed to wait for the tips to lose their force first.
                return after, physical_row(after["time_s"], object_z_m=z, in_place_tray=in_tray)

        def payload_checker(*args):
            def valid(q):
                payload_queries.append((cells[0].lower_steps, np.asarray(q).copy()))
                return payload_allowed
            return valid, {"last_rejection": {} if payload_allowed else {"pair": "fixture_floor"}}

        def transport(*args, **kwargs):
            current = cells[0].data.qpos[:5].copy()
            target = current.copy()
            target[0] += .05
            return [np.array([current, target])], {}

        output = root / "correction"
        with patch.object(collector, "StateWorkcell", CommandOnlyCell), \
                patch.object(collector, "plan_transport", side_effect=transport), \
                patch.object(collector, "carried_configuration_checker", side_effect=payload_checker):
            report = collector.collect(reference, prefix, policy_report, root / "unused.xml",
                                       output, cycles=cycles, mode="held")
        return report, load_episode(output / "expert.h5"), cells[0], payload_queries, cycles

    def test_lower_closed_payload_rejection_stops_before_execution(self):
        report, episode, cell, queries, cycles = self.collect_lower(payload_allowed=False)
        self.assertIn("Actual-to-expert chord invalid", report["error"]["message"])
        self.assertEqual(cell.lower_steps, 0)
        self.assertEqual(len(queries), 1)
        np.testing.assert_array_equal(queries[0][1], episode["next_observation.state"][-1, :5])
        self.assertEqual(episode["label_valid"].tolist(), [False]*cycles+[True])
        self.assertTrue(report["lower_closed_gripper_payload_chord_guard"])
        self.assertTrue(episode["metadata"]["lower_closed_gripper_payload_chord_guard"])

    def test_geometry_admitted_open_disables_payload_only_and_keeps_arm_guard(self):
        for arm_open_allowed in (True, False):
            with self.subTest(arm_open_allowed=arm_open_allowed):
                report, episode, cell, queries, cycles = self.collect_lower(
                    payload_allowed=True, arm_open_allowed=arm_open_allowed)
                self.assertEqual(cell.lower_steps, 2)
                self.assertEqual({tick for tick, _ in queries}, {0, 1})
                self.assertTrue(cell.arm_open_queries)
                self.assertEqual(len(cell.open_attempts), int(arm_open_allowed))
                expected = ("geometry-admitted open command" if arm_open_allowed else
                            "Actual-to-expert chord invalid")
                self.assertIn(expected, report["error"]["message"])
                self.assertEqual(episode["label_valid"].tolist(), [False]*cycles+[True]*3)
                np.testing.assert_array_equal(episode["executed_action"][-2:, 5], [.015, .015])


class ReleaseBranchTests(unittest.TestCase):
    """Mocked control flow and archive contracts, not new physics evidence."""
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.case = 0

    def collect_release(self, *, contact_interruption=False, support_interruption=None):
        self.case += 1
        root = self.root / str(self.case)
        root.mkdir()
        reference = root / "reference.h5"
        recorder = EpisodeRecorder(reference, metadata())
        recorder.append(observation(), np.zeros(6), np.zeros(6), observation(1), True, "reference", False)
        recorder.finalize({"passed": True})
        cycles = 61
        attempt = root / "attempt-000-nominal"
        attempt.mkdir()
        prefix = attempt / "policy-transitions.npz"
        command = np.array([.11, .12, .13, .14, .15, .015])
        times = 1. + np.arange(cycles) * .02
        np.savez(prefix, action=np.repeat(command[None], cycles, axis=0),
                 timestamp=times, next_timestamp=times+.02,
                 **{key: np.stack([observation()[key]] +
                                 [np.full_like(observation()[key], 99.)]*(cycles-1))
                    for key in POLICY_OBSERVATION_KEYS})
        policy_report = root / "policy-report.json"
        policy_report.write_text(json.dumps({"expert_intervention": False,
            "policy_inputs": list(POLICY_OBSERVATION_KEYS), "attempts": [{"directory": attempt.name}],
            "reference_dataset_sha256": [hashlib.sha256(reference.read_bytes()).hexdigest()]}))
        cells = []

        class ReleaseCell:
            period = .02
            baseline_z = .01

            def __init__(self, *args):
                cells.append(self)
                self.steps = self.open_steps = 0
                self.commands = []
                self.guard_queries = []
                self.model = SimpleNamespace(body=lambda name: SimpleNamespace(id=0))
                self.data = SimpleNamespace(time=1., qpos=observation()["observation.state"].copy(),
                    xpos=np.array([[.24, .14, .06]]) - collector.PINCH_POINT,
                    xmat=np.eye(3).reshape(1, 9))
                self.checker = SimpleNamespace(model=object(), evaluate=self.evaluate)

            def evaluate(self, q, **kwargs):
                self.guard_queries.append(np.asarray(q).copy())
                return {"valid": True}

            def reset(self):
                return observation()

            def step(self, command):
                self.steps += 1
                self.commands.append(np.asarray(command).copy())
                self.data.qpos[:] = command
                after = observation(self.steps)
                after["observation.state"] = self.data.qpos.copy()
                self.data.time = after["time_s"]
                in_tray = self.steps > 51
                if self.steps > cycles and command[5] == .5:
                    self.open_steps += 1
                supported = self.open_steps >= 2
                z = .01 if supported else (.013 if in_tray else .04)
                tips = [0., 0.] if supported or (contact_interruption and self.steps == 52) else [.03, .04]
                after["observation.environment_state"][6:9] = [.24, .14 if in_tray else -.13, z]
                return after, physical_row(after["time_s"], object_z_m=z, in_place_tray=in_tray,
                                          tip_forces_n=tips,
                                          floor_contact=support_interruption == "floor" and self.steps == 52,
                                          place_floor_contact=supported or (support_interruption == "place_floor" and self.steps == 52),
                                          object_speed_m_s=0.)

        output = root / "release-correction"
        with patch.object(collector, "StateWorkcell", ReleaseCell), \
                patch.object(collector, "plan_transport", side_effect=AssertionError("release must skip transport")) as transport, \
                patch.object(collector, "solve_pinch_ik", side_effect=AssertionError("release must skip IK")) as ik, \
                patch.object(collector, "carried_configuration_checker", side_effect=AssertionError("release must not carry falling payload")) as payload:
            report = collector.collect(reference, prefix, policy_report, root / "unused.xml",
                                       output, cycles=cycles, mode="release")
            transport.assert_not_called()
            ik.assert_not_called()
            payload.assert_not_called()
        return report, load_episode(output / "expert.h5"), cells[0], cycles

    def test_release_first_valid_label_opens_measured_pose_then_support_retreat_settle(self):
        report, episode, cell, cycles = self.collect_release()
        self.assertEqual(report["status"], "passed", report.get("error"))
        self.assertEqual(report["recovery_mode"], "release")
        self.assertNotIn("transport_planning", report)
        self.assertAlmostEqual(report["release_admission"]["current_dual_contact_duration_s"], 1.2)
        self.assertEqual(episode["metadata"]["recovery_mode"], "release")
        self.assertEqual(episode["metadata"]["release_admission"], report["release_admission"])
        self.assertTrue(np.isnan(episode["action"][:cycles]).all())
        self.assertFalse(episode["label_valid"][:cycles].any())
        self.assertTrue(episode["label_valid"][cycles:].all())
        np.testing.assert_array_equal(episode["action"][cycles, :5], episode["observation.state"][cycles, :5])
        self.assertEqual(episode["action"][cycles, 5], .5)
        self.assertEqual(set(episode["action"][cycles:, 5]), {.5})
        self.assertEqual(episode["stage"][cycles], "recovery_brake")
        self.assertIn("release", episode["stage"])
        self.assertIn("retreat", episode["stage"])
        self.assertIn("settle", episode["stage"])
        self.assertTrue(cell.guard_queries)
        self.assertTrue(all(q[5] == .5 for q in cell.guard_queries))
        self.assertTrue(report["physical_acceptance"]["grasp_success"])
        self.assertTrue(report["physical_acceptance"]["place_success"])
        self.assertEqual(episode["observation.state"].dtype, np.dtype("float64"))

    def test_release_short_contact_reacquisition_retains_invalid_failed_prefix(self):
        report, episode, cell, cycles = self.collect_release(contact_interruption=True)
        self.assertEqual(report["status"], "failed")
        self.assertIn("current sustained", report["error"]["message"])
        self.assertTrue(report["physical_acceptance"]["grasp_success"])
        self.assertGreaterEqual(report["physical_acceptance"]["hold_duration_s"], 1.)
        self.assertAlmostEqual(report["release_admission"]["current_dual_contact_duration_s"], .16)
        self.assertEqual(report["recorded_steps"], cycles)
        self.assertFalse(episode["label_valid"].any())
        self.assertTrue(np.isnan(episode["action"]).all())
        self.assertFalse(episode["eligible_for_training"])
        self.assertEqual(cell.open_steps, 0)

    def test_release_support_contact_resets_the_independent_current_contact_clock(self):
        for support in ("floor", "place_floor"):
            with self.subTest(support=support):
                report, episode, cell, cycles = self.collect_release(support_interruption=support)
                self.assertEqual(report["status"], "failed")
                self.assertIn("current sustained", report["error"]["message"])
                self.assertTrue(report["physical_acceptance"]["grasp_success"])
                self.assertAlmostEqual(report["release_admission"]["current_dual_contact_duration_s"], .16)
                self.assertEqual(report["recorded_steps"], cycles)
                self.assertFalse(episode["label_valid"].any())
                self.assertEqual(cell.open_steps, 0)


if __name__ == "__main__":
    unittest.main()
