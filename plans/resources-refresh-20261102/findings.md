# 发现

## 本轮修正

用户纠正品牌为木乔；已修改站点配置、首页、交付页和README。域名与账号拼写不变。

24条原卡片的核对日期均为2026-10-18。本次逐条回读官方正文、目录或源码后，更新为2026-11-02；核对不包括安装、训练、仿真或实机适配。

- LeRobot GitHub最新release为v0.6.1，发布于2026-08-03。tag包元数据要求Python>=3.12；安装链接改为实际可读的v0.6.1版本文档。主干／安装指南的特定PyTorch条件不泛化为所有平台的最低版本。
- 官方SO101专项README明确新旧校准零位、夹爪0–100约定未映射、底座碰撞网格被移除、主臂仅URDF且部分参数估算。相关条件写回模型指南。
- SmolVLA文档已有官方smolvla_base预训练模型入口；补充直达模型卡，不声称任意任务开箱即用。
- FishBot建模仓默认humble、无jazzy；导航仓当前仅main，README的-b $ROS_DISTRO片段与实际分支不符。修正环境指南和卡片。
- Jazzy仍受支持至2029-05，但不是最新ROS2发行版。保留版本化教程，不要求既有套件追新。
- 5条ROS网页HTTP200实际是Anubis挑战；已逐条读取官方ros2_documentation/jazzy同名章节正文，不能把200当正文可读。

## 逐项来源与方法

| 资源ID | 官方证据与核对内容 |
| --- | --- |
| so101-hardware | TheRobotStudio/SO-ARM100 GitHub API仓库和README，项目/主从臂入口 |
| so101-assembly | HF SO101指南实页，装配/电机/校准 |
| so101-stl | GitHub API STL/SO101目录，Follower/Leader/Individual |
| so101-step | GitHub API STEP/SO101目录，13项结构文件 |
| so101-simulation | 官方Simulation README与SO101专项README，格式及校准限制 |
| lerobot-repository | GitHub仓库、latest release与v0.6.1 pyproject |
| lerobot-installation | 官方v0.6.1安装实页，Python与依赖选择 |
| lerobot-workflow | 官方il_robots实页，录制/训练/评估关系 |
| lerobot-act | 官方ACT实页，使用/训练流程边界 |
| lerobot-smolvla | 官方SmolVLA实页，预训练模型入口和微调条件 |
| mujoco-overview | 官方stable概览实页，物理引擎/模型说明 |
| mujoco-modeling | 官方stable建模实页，关节/惯性/接触说明 |
| ompl | 官方首页实页，规划库范围与接入要求 |
| fishbot-modeling | 官方GitHub README、元数据与实际分支 |
| fishbot-navigation | 官方GitHub README与实际分支，main与克隆片段差异 |
| fishbot-firmware | 官方README与LICENSE，运动控制及非商用限制 |
| nav2-start | Nav2 Jazzy实页，Getting Started正文及canonical |
| nav2-tuning | Nav2 Jazzy实页，轮廓/膨胀场/规划与控制调参 |
| microros-architecture | 官方新站实页，客户端/Agent/XRCE-DDS |
| ros2-jazzy-install | 官网挑战页；官方jazzy同路径rst，Ubuntu24.04与架构 |
| ros2-jazzy-tutorials | 官网挑战页；官方jazzy Tutorials.rst |
| rviz-guide | 官网挑战页；官方jazzy同路径rst，消息可视化与TF |
| urdf-tutorial | 官网挑战页；官方jazzy同路径rst，模型/关节/Xacro |
| rosbag2-tutorial | 官网挑战页；官方jazzy同路径rst，录制与回放 |

## 证据与协作

本轮原始来源、逐条HTTP／源码报告和独立FishBot核验位于忽略目录 experiments/colab-twin/output/resources-refresh-20261102/。root-official-pages.json保存根Agent实际读取的10份官方页面；release.json、stable-config.json及so101-calibration-models.json保存API原文。FishBot报告为fishbot-native-review.md，根Agent已回读对应报告、分支结论及官方原文。

外部CLI额度预检Qoder不可用、AGY可用；实际AGY派发180s超时且无报告。改用当前会话内置子Agent完成只读FishBot核验，根Agent完成合并、复核、构建与发布。未修建新的调度平台。

源码仅改apps/resources与本计划，保留框架版本、机器人代码、Mint工作树、现网域名／Nginx／隧道和独立演示路由。
