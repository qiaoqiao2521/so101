import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
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


def _default_recording_path() -> str:
    recordings_dir = _discover_workspace_root() / "docs" / "generated" / "leader-recordings"
    candidates = sorted(recordings_dir.glob("leader-recording-*.jsonl"))
    if not candidates:
        return ""
    return str(candidates[-1])


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("input_path", default_value=_default_recording_path()),
            DeclareLaunchArgument("output_topic", default_value="/leader/joint_states"),
            DeclareLaunchArgument("loop", default_value="false"),
            DeclareLaunchArgument("rate_scale", default_value="1.0"),
            DeclareLaunchArgument("startup_delay_sec", default_value="1.0"),
            DeclareLaunchArgument("stamp_mode", default_value="now"),
            Node(
                package="so101_bringup",
                executable="leader_recording_replay.py",
                name="leader_recording_replay",
                output="screen",
                parameters=[
                    {
                        "input_path": LaunchConfiguration("input_path"),
                        "output_topic": LaunchConfiguration("output_topic"),
                        "loop": LaunchConfiguration("loop"),
                        "rate_scale": LaunchConfiguration("rate_scale"),
                        "startup_delay_sec": LaunchConfiguration("startup_delay_sec"),
                        "stamp_mode": LaunchConfiguration("stamp_mode"),
                    }
                ],
            ),
        ]
    )
