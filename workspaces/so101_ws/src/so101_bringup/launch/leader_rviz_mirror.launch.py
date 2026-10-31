import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    desc_pkg = get_package_share_directory("so101_description")
    bringup_pkg = get_package_share_directory("so101_bringup")

    urdf_file = os.path.join(desc_pkg, "urdf", "so101.urdf")
    rviz_config = os.path.join(desc_pkg, "rviz", "display.rviz")
    leader_bridge_script = os.path.join(bringup_pkg, "scripts", "so101_leader_input_bridge.py")

    with open(urdf_file, "r", encoding="utf-8") as f:
        robot_description = f.read()

    launch_bridge = LaunchConfiguration("launch_bridge")
    use_rviz = LaunchConfiguration("use_rviz")
    port = LaunchConfiguration("port")
    python_executable = LaunchConfiguration("python_executable")

    return LaunchDescription(
        [
            DeclareLaunchArgument("launch_bridge", default_value="true"),
            DeclareLaunchArgument("use_rviz", default_value="true"),
            DeclareLaunchArgument("port", default_value="/dev/ttyUSB0"),
            DeclareLaunchArgument("python_executable", default_value=os.path.expanduser("~/.venvs/lerobot/bin/python")),
            ExecuteProcess(
                cmd=[
                    python_executable,
                    leader_bridge_script,
                    "--ros-args",
                    "-p",
                    ["port:=", port],
                ],
                condition=IfCondition(launch_bridge),
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
