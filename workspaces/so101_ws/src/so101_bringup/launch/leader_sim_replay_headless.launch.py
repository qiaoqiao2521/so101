import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, IncludeLaunchDescription, RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    gazebo_pkg = get_package_share_directory("so101_gazebo")

    use_gzclient = LaunchConfiguration("use_gzclient")
    controller_load_delay_sec = LaunchConfiguration("controller_load_delay_sec")
    replay_start_delay_sec = LaunchConfiguration("replay_start_delay_sec")
    post_replay_wait_sec = LaunchConfiguration("post_replay_wait_sec")

    gazebo_scene = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(gazebo_pkg, "launch", "scene.launch.py")),
        launch_arguments={
            "use_rsp": "true",
            "spawn_robot": "true",
            "use_gzclient": use_gzclient,
            "cleanup_existing": "true",
            "software_rendering": "true",
        }.items(),
    )

    load_jsb = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            "/controller_manager",
            "--controller-manager-timeout",
            "120",
        ],
        output="screen",
    )

    load_jtc = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_trajectory_controller",
            "--controller-manager",
            "/controller_manager",
            "--controller-manager-timeout",
            "120",
        ],
        output="screen",
    )

    trajectory_player = Node(
        package="so101_bringup",
        executable="leader_recording_trajectory_player.py",
        name="leader_recording_trajectory_player",
        output="screen",
        parameters=[
            {
                "input_path": LaunchConfiguration("input_path"),
                "trajectory_topic": "/joint_trajectory_controller/joint_trajectory",
                "command_mode": LaunchConfiguration("command_mode"),
                "follow_joint_trajectory_action": LaunchConfiguration("follow_joint_trajectory_action"),
                "action_server_wait_sec": LaunchConfiguration("action_server_wait_sec"),
                "action_result_timeout_sec": LaunchConfiguration("action_result_timeout_sec"),
                "goal_time_tolerance_sec": LaunchConfiguration("goal_time_tolerance_sec"),
                "control_recorder": LaunchConfiguration("control_recorder"),
                "recorder_start_service": "/leader/start_recording",
                "recorder_stop_service": "/leader/stop_recording",
                "recorder_service_wait_sec": LaunchConfiguration("recorder_service_wait_sec"),
                "startup_delay_sec": replay_start_delay_sec,
                "settle_sec": LaunchConfiguration("trajectory_settle_sec"),
                "rate_scale": LaunchConfiguration("rate_scale"),
                "min_point_dt_sec": LaunchConfiguration("min_point_dt_sec"),
                "wait_for_subscribers_sec": LaunchConfiguration("wait_for_subscribers_sec"),
                "initial_hold_sec": LaunchConfiguration("initial_hold_sec"),
                "prepend_first_point_copy": LaunchConfiguration("prepend_first_point_copy"),
                "header_start_delay_sec": LaunchConfiguration("header_start_delay_sec"),
                "preposition_first_point_sec": LaunchConfiguration("preposition_first_point_sec"),
                "command_dump_path": PathJoinSubstitution([LaunchConfiguration("output_dir"), "player-command.json"]),
                "action_feedback_path": PathJoinSubstitution([LaunchConfiguration("output_dir"), "action-feedback.jsonl"]),
                "action_result_path": PathJoinSubstitution([LaunchConfiguration("output_dir"), "action-result.json"]),
            }
        ],
    )

    controller_state_recorder = Node(
        package="so101_bringup",
        executable="joint_trajectory_controller_state_recorder.py",
        name="joint_trajectory_controller_state_recorder",
        output="screen",
        parameters=[
            {
                "input_topic": "/joint_trajectory_controller/controller_state",
                "output_path": PathJoinSubstitution([LaunchConfiguration("output_dir"), "controller-state.jsonl"]),
                "flush_every_n_messages": 20,
                "log_every_n_messages": 200,
            }
        ],
    )

    recorder = Node(
        package="so101_bringup",
        executable="leader_state_recorder.py",
        name="sim_joint_state_recorder",
        output="screen",
        parameters=[
            {
                "input_topic": "/joint_states",
                "output_dir": LaunchConfiguration("output_dir"),
                "flush_every_n_frames": LaunchConfiguration("flush_every_n_frames"),
                "log_every_n_frames": LaunchConfiguration("log_every_n_frames"),
                "auto_start": False,
                "large_gap_threshold_sec": LaunchConfiguration("large_gap_threshold_sec"),
                "motion_epsilon_rad": LaunchConfiguration("motion_epsilon_rad"),
                "sanitize_non_finite_auxiliary_fields": True,
            }
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("input_path", default_value=""),
            DeclareLaunchArgument("output_dir", default_value=""),
            DeclareLaunchArgument("use_gzclient", default_value="false"),
            DeclareLaunchArgument("controller_load_delay_sec", default_value="20.0"),
            DeclareLaunchArgument("replay_start_delay_sec", default_value="1.0"),
            DeclareLaunchArgument("post_replay_wait_sec", default_value="1.0"),
            DeclareLaunchArgument("trajectory_settle_sec", default_value="2.0"),
            DeclareLaunchArgument("command_mode", default_value="topic"),
            DeclareLaunchArgument(
                "follow_joint_trajectory_action",
                default_value="/joint_trajectory_controller/follow_joint_trajectory",
            ),
            DeclareLaunchArgument("action_server_wait_sec", default_value="10.0"),
            DeclareLaunchArgument("action_result_timeout_sec", default_value="0.0"),
            DeclareLaunchArgument("goal_time_tolerance_sec", default_value="0.0"),
            DeclareLaunchArgument("control_recorder", default_value="true"),
            DeclareLaunchArgument("recorder_service_wait_sec", default_value="5.0"),
            DeclareLaunchArgument("wait_for_subscribers_sec", default_value="5.0"),
            DeclareLaunchArgument("rate_scale", default_value="1.0"),
            DeclareLaunchArgument("min_point_dt_sec", default_value="0.001"),
            DeclareLaunchArgument("initial_hold_sec", default_value="0.0"),
            DeclareLaunchArgument("prepend_first_point_copy", default_value="false"),
            DeclareLaunchArgument("header_start_delay_sec", default_value="0.0"),
            DeclareLaunchArgument("preposition_first_point_sec", default_value="0.0"),
            DeclareLaunchArgument("flush_every_n_frames", default_value="10"),
            DeclareLaunchArgument("log_every_n_frames", default_value="100"),
            DeclareLaunchArgument("large_gap_threshold_sec", default_value="0.1"),
            DeclareLaunchArgument("motion_epsilon_rad", default_value="0.01"),
            gazebo_scene,
            TimerAction(period=controller_load_delay_sec, actions=[load_jsb]),
            RegisterEventHandler(
                OnProcessExit(
                    target_action=load_jsb,
                    on_exit=[load_jtc],
                )
            ),
            recorder,
            controller_state_recorder,
            RegisterEventHandler(
                OnProcessExit(
                    target_action=load_jtc,
                    on_exit=[trajectory_player],
                )
            ),
            RegisterEventHandler(
                OnProcessExit(
                    target_action=trajectory_player,
                    on_exit=[
                        TimerAction(
                            period=post_replay_wait_sec,
                            actions=[
                                EmitEvent(
                                    event=Shutdown(reason="leader headless sim replay finished")
                                )
                            ],
                        )
                    ],
                )
            ),
        ]
    )
