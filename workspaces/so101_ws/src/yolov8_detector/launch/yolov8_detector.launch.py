from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    image_topic = LaunchConfiguration("image_topic")
    detections_topic = LaunchConfiguration("detections_topic")
    status_topic = LaunchConfiguration("status_topic")
    model_path = LaunchConfiguration("model_path")
    conf_threshold = LaunchConfiguration("conf_threshold")
    device = LaunchConfiguration("device")
    target_classes = LaunchConfiguration("target_classes")
    max_detections = LaunchConfiguration("max_detections")
    status_period_sec = LaunchConfiguration("status_period_sec")

    return LaunchDescription([
        DeclareLaunchArgument("image_topic", default_value="/camera/color/image_raw"),
        DeclareLaunchArgument("detections_topic", default_value="/detections"),
        DeclareLaunchArgument("status_topic", default_value="/yolo/status"),
        DeclareLaunchArgument("model_path", default_value="yolov8n.pt"),
        DeclareLaunchArgument("conf_threshold", default_value="0.5"),
        DeclareLaunchArgument("device", default_value="cpu"),
        DeclareLaunchArgument("target_classes", default_value=""),
        DeclareLaunchArgument("max_detections", default_value="20"),
        DeclareLaunchArgument("status_period_sec", default_value="1.0"),
        Node(
            package="yolov8_detector",
            executable="yolov8_detector_node.py",
            output="screen",
            parameters=[
                {
                    "image_topic": image_topic,
                    "detections_topic": detections_topic,
                    "status_topic": status_topic,
                    "model_path": model_path,
                    "conf_threshold": conf_threshold,
                    "device": device,
                    "target_classes": target_classes,
                    "max_detections": max_detections,
                    "status_period_sec": status_period_sec,
                }
            ],
        ),
    ])
