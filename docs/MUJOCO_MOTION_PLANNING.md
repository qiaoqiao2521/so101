# SO101：以 MuJoCo 为核心的运动自主规划

2026-10-01 用户指定一个主方向。本轮完成本地资产盘点、AGY 咨询与路线整理；自主规划代码尚未接入。当前已通过的是 Colab CPU / MuJoCo 3.3.7 / OSMesa 的六秒合成关节轨迹和结果回收。

## 目标与组件分工

第一阶段：输入起始关节、末端目标位置与静态障碍，自动生成无碰撞关节路径，在 MuJoCo 中执行并评估。第二阶段再增加可移动物体、接触抓放与视觉目标。实验尚未完成实体参数标定或真机状态同步，当前属于数字孪生的仿真基础。

```mermaid
flowchart LR
    target[目标位置与静态障碍] --> ik[位置 IK：候选关节目标]
    ik --> planner[OMPL RRTConnect：五轴路径]
    planner <--> validity[MuJoCo：碰撞与关节有效性]
    planner --> timing[轨迹时间与速度约束]
    timing --> execution[MuJoCo：物理执行]
    execution --> result[实际 TCP / 碰撞 / 误差 / 视频]
```

MuJoCo 本身不负责搜索全局路径。IK 求出能到达目标的关节角，OMPL 搜索如何绕过障碍，MuJoCo 检查候选状态并验证物理执行。Mink 是局部 IK，必须检查残差和可达性，不能代替全局避障。

SO101 为五个机械臂自由度加夹爪。初期固定夹爪，只规划五轴；先约束三维位置，再按任务放松或增加部分姿态约束。任意六维末端位姿不得默认视为可达。旧 SRDF 的 arm 链以 moving jaw 为末端，包含夹爪关节；迁移时需明确拆分，不能直接沿用其状态空间。

## 已有资产怎样续用

| 资产 | 入口 | 核查结果与使用方式 |
| --- | --- | --- |
| 原生 MJCF / 13 个完整 STL / 许可证 | [MuJoCo 模型](../workspaces/so101_ws/src/so101_mujoco/models/so101.xml) | 直接作为主模型；末端 site 为 `gripperframe`。XML 有 13 个 collision class geom，仍须核对编译后的碰撞掩码、覆盖、自碰与距离精度 |
| Colab CPU 自动运行与回收 | [平台说明](../experiments/colab-twin/README.md) | 分配、上传、执行、下载、释放已实际通过，继续使用同一入口 |
| MoveIt / OMPL RRTConnect | [配置](../workspaces/so101_ws/src/so101_moveit_config/config/ompl_planning.yaml)、[执行器](../workspaces/so101_ws/src/so101_moveit_config/scripts/pick_place_runner.py) | 保留五轴/夹爪语义、限速与轨迹导出经验；`range=0.0` 是自动参数，不当作已验证数值直接照搬 |
| 既有 suite / report 周边 | [suite runner](../workspaces/so101_ws/tools/e2e/run_mtc_reach_benchmark_suite.py)、[验收汇总](../workspaces/so101_ws/tools/e2e/run_pre_real_acceptance_suite.py) | 复用规划/执行/收敛/距离/失败原因字段与逐轮输出约定；这些周边代码不能替代缺失的原 evaluator |
| 视觉 target / 数据标签匹配 | [candidate exporter](../workspaces/so101_ws/tools/hardware/export_vision_dataset_to_lerobot_candidate.py) | 后续保留 raw 与 canonical target 区别，防止物体标签、目标坐标和轨迹错配 |

当前 ROS URDF 为 17 个 visual、0 个 collision，不能直接用于可靠 MoveIt 避障；这不等于原生 MJCF 也没有碰撞几何。先审查 MJCF 现存几何，按需要补齐简单碰撞体或凸分解。不要把 STL 的视觉形状、凸包和实际夹爪空隙默认视为一致。

旧 Gazebo 目标使用约 0.75 m 桌高和约 0.8 m 世界 z；原生 MJCF 在自身模型坐标下运行。迁移目标必须明确 world/base/TCP 变换，不能原样复制 xyz。五轴关节名、弧度单位、TCP site、夹爪状态和限位逐项对齐。

## 本地工程与历史边界

唯一开发根为 `projects/so101`；旧 `workspaces/so101_ws`、`so101-win7-follower-demo` 和桌面 follower 路径是兼容链接。`repo-revival/so101`、`repo-scan/so101-ros2-arm`、`repo-scan/so101` 与 delivery 是旧工程或发布副本；本轮所查规划文件没有更完整的 MTC 原件。独立 `lerobot` 源树存在 Placo FK/IK，可作后续比较，不把整个学习框架作为当前前置依赖。

- 2026-03-14 [非空导出日志](../workspaces/so101_ws/docs/evidence/gzm-004-export-20260314212123.log) 与多点轨迹支持“七个预设关节目标的 MoveIt 规划执行通过”的历史结论；本轮没有重跑。
- 2026-05-07 的任务记录描述 Cartesian IK/FK candidate → MTC → Gazebo reach。现存非空 jitter50 summary 记录规划 100%、执行/收敛 96%、reach 100%，但 reach 阈值为 8 cm，平均距离约 5.64 cm。
- jitter20 的 200 个逐轮文件、jitter50 的 500 个逐轮文件均为零字节。MTC C++ node、launch、原 grasp evaluator、视觉 projector 和 recorder 源码缺失，不能按 summary 宣称当前可复跑或精准抓取通过。
- 本地快照、有效 Git 路径历史和有界 Agent 历史检索未找回缺失 MTC 原件。损坏 Git 和零字节归档保留，不能覆盖当前源码；缺失线作为可恢复待办，不阻塞原生 MuJoCo 接入。

## 算法与版本候选

| 组件 | 第一阶段候选 | 验证边界 |
| --- | --- | --- |
| 物理引擎 | MuJoCo 3.3.7 | 当前 Colab 基线已运行；原资产保持不变，场景修改在实验副本中完成 |
| 位置 IK | Mink 1.1.0 | 依赖声明要求 MuJoCo ≥3.3.6、Python ≥3.10 且 <3.14；未在 SO101 联调 |
| 全局路径 | OMPL 2.0.1 / RRTConnect | 已确认 Linux CPython 3.13 发布包；未在本平台安装或运行 |
| 时间与速度 | 第一版保守时间参数化 | 不提前引入新框架；后处理后的路径需再次有效性检查 |

最新版 Mink 1.3.0 要求 MuJoCo ≥3.10.0，不能无约束升级依赖。所有候选在隔离环境验收后再改 requirements。实现参考：[Mink 示例](https://github.com/kevinzakka/mink/blob/v1.1.0/examples/arm_ur5e.py)、[Mink 依赖](https://github.com/kevinzakka/mink/blob/v1.1.0/pyproject.toml)、[OMPL Python 示例](https://github.com/ompl/ompl/blob/main/demos/RigidBodyPlanning.py)、[OMPL 发布](https://pypi.org/project/ompl/)。

## 实现顺序与最短验收

1. **可达性与模型语义**：确认 TCP、五轴限位及坐标转换；给定可达位置，IK 收敛并通过 FK 残差检查；明显不可达目标必须返回无解。第一版仿真目标容差候选为 1 cm，作为新的配置和验收标准，不与旧 8 cm reach 数字混用。
2. **碰撞与路径**：验证碰撞检查器能检出刻意放置的障碍和自碰；构造起终点有效、直线路径被阻挡的场景，RRTConnect 自动绕行。检查路径中间路段和最小间隙；阻死通路应失败或超时，禁止默默回退到直线。
3. **执行与报告**：规划与执行使用独立 `MjData`；候选查询用 `mj_forward`，物理执行用 `mj_step`。记录实际 TCP、误差、碰撞、关节限位、控制指令和时间连续性；跟踪失败与规划失败分别报告。输出沿用平台的 CSV / JSON / MP4。

先跑上述正反例，再用固定随机种子做 20 轮小批量，报告成功率、距离分布、规划时间及失败原因。此处是待执行验收计划，不是已通过测试。MuJoCo 仿真结果不得当作真实机械臂参数或实机动作放行证据。

## Gazebo 可以在 Colab 用吗

可以作为条件成立的无头仿真候选，本项目尚未实测：

| 用途 | 判断 |
| --- | --- |
| 纯物理、轨迹与碰撞 | server-only 可用 CPU；须确认运行时 Ubuntu 与 Gazebo 软件包匹配 |
| 相机、深度图等渲染 | OGRE2 + EGL 的 `--headless-rendering`；官方推荐 GPU，也允许软件渲染，性能与驱动须实测 |
| 桌面 GUI | 需要显示和远程桌面；不作为本阶段 Colab 入口 |

Gazebo [官方无头渲染文档](https://gazebosim.org/api/sim/8/headless_rendering.html) 给出 server/EGL 例程。[官方 ROS 配对](https://gazebosim.org/docs/harmonic/ros_installation/) 中 Jazzy 默认搭配 Harmonic，Humble 默认搭配 Fortress；本工程旧 Classic 插件和 launch 仍需迁移。

[Colab FAQ](https://research.google.com/colaboratory/faq.html) 说明资源与虚拟机生命周期有限，免费且没有正计算余额的托管运行时限制 SSH/远程桌面等远程控制。后续若需要 Gazebo 对照，应做范围明确的无头实验；当前主线继续使用已经跑通的 MuJoCo。

## AGY 咨询与接续 owner

2026-10-01 实际用 AGY CLI 的 plan/sandbox 模式做单次只读咨询，仅提供上述核实摘要。AGY 推荐 MuJoCo + Python IK/OMPL，先验收可达性、碰撞检出与闭环跟踪。采纳主方向与顺序；其“Ground Truth”措辞仅能理解为仿真内参考，不能替代真实标定。其对性能和历史误差来源的判断仍属待验证意见。

根 Codex 负责从 [当前计划](../plans/colab-digital-twin-20261001/task_plan.md) 接续，第一项工作为模型/TCP/碰撞与位置 IK 的隔离验收。Gazebo、MTC 恢复与真机延迟保持各自历史边界。个人文档、原始咨询、标定和运行产物留在 Git 排除区。
