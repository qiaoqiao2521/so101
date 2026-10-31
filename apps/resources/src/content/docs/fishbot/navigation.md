---
title: FishBot 建图与导航
description: 理解地图、定位、规划与控制的关系，按依赖顺序阅读导航资料。
---

导航不是一个参数或一条命令。机器人需要知道自身运动、周围障碍和当前位置，才能规划并跟踪路线。

## 先分清几个环节

| 环节 | 主要问题 | 典型输入或结果 |
| --- | --- | --- |
| 驱动与里程计 | 机器人怎样运动？ | 速度、编码器、里程计 |
| 坐标变换 TF | 数据在哪个坐标系？ | 机器人与传感器的相对关系 |
| 建图 | 周围环境是什么样？ | 传感器数据与地图 |
| 定位 | 机器人在地图哪里？ | 位姿估计 |
| 规划与控制 | 怎样到目标？ | 路径与运动指令 |

从[FishBot 导航仓库](https://github.com/fishros/fishbot_nav)了解项目组织，再结合 [Nav2 Jazzy 学习入口](https://docs.nav2.org/jazzy/getting_started/)阅读通用导航概念。Nav2 官方示例的机器人配置不能直接当作 FishBot 配置。

## 建议的观察顺序

1. 核对传感器与里程计消息的坐标系。
2. 在 RViz 中观察 TF 与传感器显示。
3. 核对地图与定位结果。
4. 观察规划路径与局部代价地图。
5. 对照机器人轮廓和控制参数分析运动。

使用 [RViz 用户指南](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/RViz/RViz-User-Guide/RViz-User-Guide.html)学习显示方式。使用 [Nav2 调参指南](https://docs.nav2.org/jazzy/configuration_and_development/tuning_guide/)理解轮廓、膨胀与规划控制的关系。

## 常见判断误区

地图出现，不代表定位准确。路径出现，不代表底盘能可靠跟踪。机器人停住，也可能是障碍判断、坐标、数据延迟或控制配置的问题。先保留现象与相关数据，再逐项排查。

学习记录可参考 [rosbag2 官方教程](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Recording-And-Playing-Back-Data/Recording-And-Playing-Back-Data.html)。回放是历史消息；判断现场导航能力，需要另行观察实际机器人和实际环境。
