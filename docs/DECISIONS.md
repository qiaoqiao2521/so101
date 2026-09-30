# SO101 decisions

## D001：运动自主规划以 MuJoCo 为核心

日期：2026-10-01。状态：用户指定的主方向；位置 IK、OMPL 绕障与物理执行已接入，本地与Colab CPU20轮通过，可见场景与视频回收已复验通过。

采用 Colab CPU + MuJoCo 原生 MJCF + Python 规划组件。MuJoCo 负责模型、运动学查询、碰撞检查、物理执行与渲染；位置 IK 使用 Mink 1.1.0，路径搜索使用 OMPL 2.0.1 / RRTConnect。两库已做兼容性和 SO101 小规模验收，沿用 MuJoCo 3.3.7。

理由：现有 Colab 无头运行及结果回收已通过；本地具有完整 MJCF、网格、规划配置和轨迹接口。旧 ROS/Humble 运行环境与本机 Jazzy 不同，MTC 核心源码和逐轮证据缺失，不能作为当前平台的必需依赖。

已有 MoveIt/OMPL 成果用于续接模型语义、参数和接口。Gazebo 保留为本地 ROS 联调模块；GPU cuRobo 留到有明确计算环境和对照需求时再评估。用户此前提到的两方案由本次“一个方向、MuJoCo 为核心”的指令收敛。

本次实际调用 AGY 原生 CLI 作只读咨询；它也选择 MuJoCo + Python IK/OMPL，并建议先验证可达性、碰撞检出和跟踪。咨询基于已核实的摘要，没有独立运行实验。原始响应留在本机被忽略的 `local-documents/agent-consultations/20261001-mujoco-direction/`。

重访条件：需要持续 ROS/DDS 集成、特定 Gazebo 传感器/插件，或 CPU 规划性能不足且已有可验证 GPU 环境。验收尺度、复用清单与官方来源见 [规划路线](MUJOCO_MOTION_PLANNING.md)。

## D002：原生碰撞装配与数值策略

日期：2026-10-01。状态：实际模型正反例已验证。保留源模型与13网格，仅派生场景补四个底座碰撞网格；同body/直接父子连杆与固定底座安装接触作为明确装配例外，非相邻自碰保留。物理XML同步六对父子contact/exclude，防止凸包装配重叠影响执行。

MuJoCo3.3.7 nativeCCD出现纯底座旋转时分离距离误报0，派生XML显式disable nativeccd，走libccd。15个yaw回归点保持一致；真正负距离非相邻肩部/抓手自碰和静态盒子/桌面仍能检出。libccd分离距离近似，阈值和最小距离仅用于该仿真凸包模型，不能推作实体安全。后续需要精准夹爪空隙或连续碰撞保证时，重新验证几何与碰撞算法；不无约束升级引擎。
