# SO101

## Why / User Intent
一台机械臂一个项目，以本机最新跟随器、ROS/MES和场景工具为准。
## Non-goals
不重新拆仓，不以公开旧快照覆盖本机，不自动运行机械臂或发布标定数据。
## Success
单一本地入口，内部组件按项目相对路径连接，源码和历史保全。
## Constraints
ROS工作区含Humble语义，本机仅Jazzy；不默认宣称已移植。workspaces/so101_ws的Git无有效HEAD，保留历史备份。
## Current State
2026-09-15本机跟随器/ROS工作区/场景归入本目录，旧路径兼容。2026-10-01 Colab CPU / MuJoCo 3.3.7 的六秒合成轨迹、无头渲染和结果回收已实际通过，位置 IK、OMPL 绕障和物理执行已接入，本地29项测试与Colab CPU 20轮目标扰动通过，可见场景与视频回收已复验通过。本机旧Git基线仍保留，发布通过独立delivery工作树串行整合。导入不再初始化硬件Runtime，回归测试使用合成数据；部署仍需本地配置和标定。
## Current Priority
2026-10-01 用户指定：运动自主规划以 **MuJoCo 为核心**，收敛为一条主线。在已有 Colab CPU 平台上接入位置 IK、OMPL RRTConnect、MuJoCo 碰撞检查、轨迹执行和统一评估；先完成给定目标与障碍的自主到达，再扩展抓放与视觉。已有 MoveIt/OMPL 配置、轨迹导出和评估字段作为续接资产；Gazebo 保留为后续本地 ROS 联调模块。AGY 的只读咨询也推荐这一方向。五轴位置到达已实现；接触抓放、视觉和实体同步继续留作下一阶段。

2026-09-22：主从跟随迟钝已完成静态/离线诊断；用户当前不便使用实体机械臂，后续采样与修复标记为待处理。不自动连接硬件、启动跟随或调整限幅，等用户明确继续后再开展。
## Knowledge Map
README.md；mint_follower_demo/SECURITY.md；workspaces/so101_ws/AGENTS.md；docs/ARCHITECTURE.md。

主从迟钝待办：`plans/teleop-latency-20260922/task_plan.md`；已有证据：同目录 `REPORT.md`。

运动规划路线：`docs/MUJOCO_MOTION_PLANNING.md`；选择依据：`docs/DECISIONS.md`。数字孪生实验：`experiments/colab-twin/README.md`；当前计划：`plans/colab-digital-twin-20261001/task_plan.md`。毕业设计、答辩材料和原始 Agent 咨询位于被 Git 排除的 `local-documents/`，只保留在本机。

GR00T / LIBERO 扩展（2026-10-01）：`experiments/gr00t-libero/README.md` 与 `plans/gr00t-libero-20261001/task_plan.md`。固定官方版本，CPU 环境真实 reset/step/双相机已验证；GPU 策略待 HF 权限与兼容 Colab GPU，已有付费额度小样本授权。保持 MuJoCo 主线；Panda 实验不代表 SO101 策略迁移。
