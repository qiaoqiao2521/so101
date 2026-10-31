---
title: 常用术语
description: 用简短说明理解资料目录中的机器人、ROS 2 与学习术语。
---

这些解释用于快速阅读。涉及具体配置时，请回到对应项目与版本的官方文档。

## 结构与仿真

| 术语 | 简短说明 |
| --- | --- |
| Leader / Follower | 遥操作中输入动作的主臂与执行动作的从臂 |
| STL | 描述表面三角网格的文件格式，常用于打印零件 |
| STEP | 常用于 CAD 交换的结构文件格式 |
| URDF | 用连杆和关节描述机器人的 XML 格式 |
| MJCF | MuJoCo 的模型与场景描述格式 |
| 碰撞模型 | 用于计算接触或障碍关系的几何描述，可能不同于外观网格 |
| 运动规划 | 在约束条件下寻找从起点到终点的运动路径 |

继续阅读：[SO101 模型与仿真](/so101/simulation/)、[URDF 教程](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/URDF/URDF-Main.html)。

## ROS 2 与导航

| 术语 | 简短说明 |
| --- | --- |
| 节点 Node | 承担某项功能、参与 ROS 2 通信的软件单元 |
| 话题 Topic | 节点发布和订阅消息的命名通道 |
| TF | 管理坐标系之间的位置与姿态关系 |
| 里程计 Odometry | 对机器人相对运动的估计，会随运动累积误差 |
| SLAM | 同时估计自身位置并建立环境地图 |
| 定位 Localization | 根据传感器与地图等信息估计当前位置 |
| Nav2 | ROS 2 的导航软件框架 |
| 代价地图 Costmap | 为导航表示障碍与通行代价的地图 |
| Footprint | 用于规划与碰撞判断的机器人平面轮廓 |
| micro-ROS Agent | 连接微控制器客户端与 ROS 2 系统的代理程序 |
| rosbag2 | 记录与回放 ROS 2 消息的工具 |

继续阅读：[FishBot 建图与导航](/fishbot/navigation/)、[ROS 2 教程](https://docs.ros.org/en/jazzy/Tutorials.html)。

## 数据与策略学习

| 术语 | 简短说明 |
| --- | --- |
| Episode | 一次从开始到结束的任务过程 |
| Dataset | 按约定格式组织的示范或观测数据集合 |
| Policy | 根据观测生成动作的策略 |
| ACT | Action Chunking with Transformers，一种模仿学习策略 |
| VLA | Vision-Language-Action，联合处理视觉、语言与动作的模型方向 |
| 微调 Finetuning | 在已有模型基础上，使用特定数据继续训练 |
| 评估 Evaluation | 在预先约定的任务条件下观察结果与失败情况 |

继续阅读：[LeRobot 真机学习流程](https://huggingface.co/docs/lerobot/il_robots)、[ACT](https://huggingface.co/docs/lerobot/act)、[SmolVLA](https://huggingface.co/docs/lerobot/smolvla)。
