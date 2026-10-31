import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _discover_workspace_root() -> Path:
    share_dir = Path(get_package_share_directory("so101_bringup")).resolve()
    for candidate in [share_dir, *share_dir.parents]:
        if (candidate / "AGENTS.md").is_file() and (candidate / "docs").is_dir() and (candidate / "src").is_dir():
            return candidate
    return share_dir.parents[3]


def generate_launch_description():
    bringup_pkg = get_package_share_directory("so101_bringup")
    leader_bridge_script = os.path.join(bringup_pkg, "scripts", "so101_leader_input_bridge.py")
    default_output_dir = str(_discover_workspace_root() / "docs" / "generated" / "leader-recordings")

    return LaunchDescription(
        [
            DeclareLaunchArgument("port", default_value="/dev/ttyUSB0"),
            DeclareLaunchArgument("python_executable", default_value=os.path.expanduser("~/.venvs/lerobot/bin/python")),
            DeclareLaunchArgument("output_dir", default_value=default_output_dir),
            DeclareLaunchArgument("auto_start", default_value="false"),
            DeclareLaunchArgument("large_gap_threshold_sec", default_value="0.1"),
            DeclareLaunchArgument("motion_epsilon_rad", default_value="0.01"),
            ExecuteProcess(
                cmd=[
                    LaunchConfiguration("python_executable"),
                    leader_bridge_script,
                    "--ros-args",
                    "-p",
                    ["port:=", LaunchConfiguration("port")],
                ],
                output="screen",
                additional_env={
                    "PYTHONPATH": os.pathsep.join(
                        value for value in (
                            os.environ.get("LEROBOT_SITE_PACKAGES", ""),
                            os.environ.get("PYTHONPATH", ""),
                        ) if value
                    ),
                },
            ),
            Node(
                package="so101_bringup",
                executable="leader_state_recorder.py",
                name="leader_state_recorder",
                output="screen",
                parameters=[
                    {
                        "input_topic": "/leader/joint_states",
                        "output_dir": LaunchConfiguration("output_dir"),
                        "flush_every_n_frames": 1,
                        "log_every_n_frames": 30,
                        "auto_start": LaunchConfiguration("auto_start"),
                        "large_gap_threshold_sec": LaunchConfiguration("large_gap_threshold_sec"),
                        "motion_epsilon_rad": LaunchConfiguration("motion_epsilon_rad"),
                    }
                ],
            ),
        ]
    )
