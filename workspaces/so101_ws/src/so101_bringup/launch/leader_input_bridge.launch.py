import os

from ament_index_python.packages import get_package_prefix
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import ExecuteProcess
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    package_prefix = get_package_prefix("so101_bringup")
    bridge_script = os.path.join(package_prefix, "lib", "so101_bringup", "so101_leader_input_bridge.py")

    return LaunchDescription(
        [
            DeclareLaunchArgument("leader_type", default_value="so101_leader"),
            DeclareLaunchArgument("port", default_value="__empty__"),
            DeclareLaunchArgument("publish_rate_hz", default_value="30.0"),
            DeclareLaunchArgument("calibration_path", default_value="__empty__"),
            DeclareLaunchArgument("raw_state_enabled", default_value="true"),
            DeclareLaunchArgument("status_topic_enabled", default_value="true"),
            DeclareLaunchArgument("adapter_factory", default_value="__empty__"),
            DeclareLaunchArgument("degraded_latency_ms", default_value="120.0"),
            DeclareLaunchArgument("positions_in_degrees", default_value="auto"),
            DeclareLaunchArgument("python_executable", default_value=os.path.expanduser("~/.venvs/lerobot/bin/python")),
            ExecuteProcess(
                cmd=[
                    LaunchConfiguration("python_executable"),
                    bridge_script,
                    "--ros-args",
                    "-p",
                    ["leader_type:=", LaunchConfiguration("leader_type")],
                    "-p",
                    ["port:=", LaunchConfiguration("port")],
                    "-p",
                    ["publish_rate_hz:=", LaunchConfiguration("publish_rate_hz")],
                    "-p",
                    ["calibration_path:=", LaunchConfiguration("calibration_path")],
                    "-p",
                    ["raw_state_enabled:=", LaunchConfiguration("raw_state_enabled")],
                    "-p",
                    ["status_topic_enabled:=", LaunchConfiguration("status_topic_enabled")],
                    "-p",
                    ["adapter_factory:=", LaunchConfiguration("adapter_factory")],
                    "-p",
                    ["degraded_latency_ms:=", LaunchConfiguration("degraded_latency_ms")],
                    "-p",
                    ["positions_in_degrees:=", LaunchConfiguration("positions_in_degrees")],
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
        ]
    )
