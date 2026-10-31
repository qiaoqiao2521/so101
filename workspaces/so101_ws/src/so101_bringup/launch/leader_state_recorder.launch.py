from ament_index_python.packages import get_package_share_directory
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _discover_workspace_root() -> Path:
    share_dir = Path(get_package_share_directory("so101_bringup")).resolve()
    for candidate in [share_dir, *share_dir.parents]:
        if (candidate / "AGENTS.md").is_file() and (candidate / "docs").is_dir() and (candidate / "src").is_dir():
            return candidate
    return share_dir.parents[3]


def generate_launch_description():
    default_output_dir = str(_discover_workspace_root() / "docs" / "generated" / "leader-recordings")
    return LaunchDescription(
        [
            DeclareLaunchArgument("input_topic", default_value="/leader/joint_states"),
            DeclareLaunchArgument("output_dir", default_value=default_output_dir),
            DeclareLaunchArgument("flush_every_n_frames", default_value="1"),
            DeclareLaunchArgument("log_every_n_frames", default_value="30"),
            DeclareLaunchArgument("auto_start", default_value="false"),
            DeclareLaunchArgument("large_gap_threshold_sec", default_value="0.1"),
            DeclareLaunchArgument("motion_epsilon_rad", default_value="0.01"),
            DeclareLaunchArgument("sanitize_non_finite_auxiliary_fields", default_value="false"),
            Node(
                package="so101_bringup",
                executable="leader_state_recorder.py",
                name="leader_state_recorder",
                output="screen",
                parameters=[
                    {
                        "input_topic": LaunchConfiguration("input_topic"),
                        "output_dir": LaunchConfiguration("output_dir"),
                        "flush_every_n_frames": LaunchConfiguration("flush_every_n_frames"),
                        "log_every_n_frames": LaunchConfiguration("log_every_n_frames"),
                        "auto_start": LaunchConfiguration("auto_start"),
                        "large_gap_threshold_sec": LaunchConfiguration("large_gap_threshold_sec"),
                        "motion_epsilon_rad": LaunchConfiguration("motion_epsilon_rad"),
                        "sanitize_non_finite_auxiliary_fields": LaunchConfiguration("sanitize_non_finite_auxiliary_fields"),
                    }
                ],
            ),
        ]
    )
