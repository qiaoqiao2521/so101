# SO101 decisions

## D001：运动自主规划以 MuJoCo 为核心

日期：2026-10-01。状态：用户指定的主方向；算法接入待实现。

采用 Colab CPU + MuJoCo 原生 MJCF + Python 规划组件。MuJoCo 负责模型、运动学查询、碰撞检查、物理执行与渲染；候选位置 IK 使用 Mink，路径搜索使用 OMPL RRTConnect。两库先做兼容性和 SO101 小规模验收，沿用当前 MuJoCo 3.3.7，暂不升级引擎。

理由：现有 Colab 无头运行及结果回收已通过；本地具有完整 MJCF、网格、规划配置和轨迹接口。旧 ROS/Humble 运行环境与本机 Jazzy 不同，MTC 核心源码和逐轮证据缺失，不能作为当前平台的必需依赖。

已有 MoveIt/OMPL 成果用于续接模型语义、参数和接口。Gazebo 保留为本地 ROS 联调模块；GPU cuRobo 留到有明确计算环境和对照需求时再评估。用户此前提到的两方案由本次“一个方向、MuJoCo 为核心”的指令收敛。

本次实际调用 AGY 原生 CLI 作只读咨询；它也选择 MuJoCo + Python IK/OMPL，并建议先验证可达性、碰撞检出和跟踪。咨询基于已核实的摘要，没有独立运行实验。原始响应留在本机被忽略的 `local-documents/agent-consultations/20261001-mujoco-direction/`。

重访条件：需要持续 ROS/DDS 集成、特定 Gazebo 传感器/插件，或 CPU 规划性能不足且已有可验证 GPU 环境。验收尺度、复用清单与官方来源见 [规划路线](MUJOCO_MOTION_PLANNING.md)。
