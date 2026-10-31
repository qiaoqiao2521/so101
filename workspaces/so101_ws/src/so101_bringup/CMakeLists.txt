cmake_minimum_required(VERSION 3.8)
project(so101_bringup)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch config scripts
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/action_template_mapping.py
  scripts/task_executor.py
  scripts/mock_yolo_node.py
  scripts/sync_action_template_mapping.py
  scripts/so101_leader_input_bridge.py
  scripts/leader_state_recorder.py
  scripts/leader_recording_replay.py
  scripts/leader_recording_trajectory_player.py
  scripts/leader_joint_state_mirror.py
  scripts/joint_trajectory_controller_state_recorder.py
  scripts/vision_episode_recorder_node.py
  scripts/vision_overlay_node.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
