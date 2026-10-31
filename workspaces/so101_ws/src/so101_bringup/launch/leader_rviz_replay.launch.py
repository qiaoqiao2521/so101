import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
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
    desc_pkg = get_package_share_directory("so101_description")

    urdf_file = os.path.join(desc_pkg, "urdf", "so101.urdf")
    rviz_config = os.path.join(desc_pkg, "rviz", "display.rviz")

    with open(urdf_file, "r", encoding="utf-8") as f:
        robot_description = f.read()

    use_rviz = LaunchConfiguration("use_rviz")

    return LaunchDescription(
        [
            DeclareLaunchArgument("input_path", default_value=_default_recording_path()),
            DeclareLaunchArgument("loop", default_value="false"),
            DeclareLaunchArgument("rate_scale", default_value="1.0"),
            DeclareLaunchArgument("startup_delay_sec", default_value="1.0"),
            DeclareLaunchArgument("stamp_mode", default_value="now"),
            DeclareLaunchArgument("use_rviz", default_value="true"),
            Node(
                package="so101_bringup",
                executable="leader_recording_replay.py",
                name="leader_recording_replay",
                output="screen",
                parameters=[
                    {
                        "input_path": LaunchConfiguration("input_path"),
                        "output_topic": "/leader/joint_states",
                        "loop": LaunchConfiguration("loop"),
                        "rate_scale": LaunchConfiguration("rate_scale"),
                        "startup_delay_sec": LaunchConfiguration("startup_delay_sec"),
                        "stamp_mode": LaunchConfiguration("stamp_mode"),
                    }
                ],
            ),
            Node(
                package="so101_bringup",
                executable="leader_joint_state_mirror.py",
                name="leader_joint_state_mirror",
                output="screen",
            ),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                parameters=[{"robot_description": robot_description}],
                output="screen",
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                arguments=["-d", rviz_config],
                condition=IfCondition(use_rviz),
                output="screen",
            ),
        ]
    )
