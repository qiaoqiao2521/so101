"""Stage-free task acceptance examples, independent of the expert controller."""
import unittest

from learning_env import PhysicalTaskMonitor


def physical_row(time, **changes):
    row = {
        'time_s': time,
        'object_z_m': .05,
        'object_xyz_m': [.24, -.13, .05],
        'object_speed_m_s': .0,
        'tip_forces_n': [.5, .5],
        'floor_contact': False,
        'place_floor_contact': False,
        'in_place_tray': False,
        'obstacle_contact': False,
        'arm_valid': True,
        'finite_state': True,
    }
    row.update(changes)
    return row


def establish_real_lift(monitor):
    for tick in range(52):
        monitor.update(physical_row(tick * .02))


def released_rest(time):
    return physical_row(time, object_z_m=.01, object_xyz_m=[.24, .14, .01],
                        tip_forces_n=[0., 0.], in_place_tray=True,
                        place_floor_contact=True)


class PhysicalTaskAcceptanceTests(unittest.TestCase):
    def test_real_lift_and_released_rest_need_no_expert_stage(self):
        monitor = PhysicalTaskMonitor(.01)
        establish_real_lift(monitor)
        self.assertTrue(monitor.report()['grasp_success'])
        for tick in range(53, 106):
            monitor.update(released_rest(tick * .02))
        self.assertTrue(monitor.report()['passed'])

    def test_air_close_or_floor_supported_cube_cannot_establish_grasp(self):
        for changes in ({'tip_forces_n': [0., 0.]}, {'floor_contact': True},
                        {'place_floor_contact': True}, {'tip_forces_n': [.5, 0.]}):
            with self.subTest(changes=changes):
                monitor = PhysicalTaskMonitor(.01)
                for tick in range(60):
                    monitor.update(physical_row(tick * .02, **changes))
                for tick in range(61, 120):
                    monitor.update(released_rest(tick * .02))
                self.assertFalse(monitor.report()['passed'])
                self.assertFalse(monitor.report()['grasp_success'])

    def test_one_touch_in_tray_does_not_replace_continuous_rest(self):
        monitor = PhysicalTaskMonitor(.01)
        establish_real_lift(monitor)
        for tick in range(53, 75):
            monitor.update(released_rest(tick * .02))
        monitor.update(physical_row(1.5, object_z_m=.01, in_place_tray=True,
                                   tip_forces_n=[0., 0.], place_floor_contact=False))
        for tick in range(76, 101):
            monitor.update(released_rest(tick * .02))
        self.assertFalse(monitor.report()['passed'])
        self.assertLess(monitor.report()['settled_duration_s'], 1.)

    def test_payload_loss_remains_a_failure_after_later_tray_rest(self):
        monitor = PhysicalTaskMonitor(.01)
        establish_real_lift(monitor)
        for tick in range(53, 61):
            monitor.update(physical_row(tick * .02, tip_forces_n=[0., 0.]))
        for tick in range(62, 121):
            monitor.update(released_rest(tick * .02))
        self.assertFalse(monitor.report()['passed'])
        self.assertIsNotNone(monitor.report()['failure_reason'])

    def test_dropped_above_blue_tray_is_not_a_controlled_placement(self):
        monitor = PhysicalTaskMonitor(.01)
        establish_real_lift(monitor)
        for tick in range(53, 61):
            monitor.update(physical_row(tick * .02, tip_forces_n=[0., 0.],
                                       object_xyz_m=[.24, .14, .05],
                                       object_speed_m_s=.1, in_place_tray=True))
        for tick in range(62, 121):
            monitor.update(released_rest(tick * .02))
        self.assertFalse(monitor.report()['passed'])
        self.assertIsNotNone(monitor.report()['failure_reason'])

    def test_collision_failure_is_not_replaced_by_later_task_success(self):
        monitor = PhysicalTaskMonitor(.01)
        establish_real_lift(monitor)
        monitor.update(physical_row(1.04, obstacle_contact=True))
        for tick in range(53, 121):
            monitor.update(released_rest(tick * .02))
        self.assertFalse(monitor.report()['passed'])
        self.assertTrue(monitor.report()['safety_stop'])


if __name__ == '__main__':
    unittest.main()
