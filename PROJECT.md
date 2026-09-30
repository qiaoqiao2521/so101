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
2026-09-15本机跟随器/ROS工作区/场景归入本目录，旧路径兼容。公开总仓已同步（e5c0168），本机Git历史未整合。导入不再初始化硬件Runtime，回归测试使用合成数据；部署仍需本地配置和标定。
## Current Priority
2026-10-01：按答辩后的方向，先用 Colab CLI 建立 SO101 数字孪生实验平台。当前从现有 MuJoCo 模型、合成关节轨迹和无头渲染开始；视觉、自主规划与真机同步后续逐步接入。两个方案中的第二方案待用户定义。

2026-09-22：主从跟随迟钝已完成静态/离线诊断；用户当前不便使用实体机械臂，后续采样与修复标记为待处理。不自动连接硬件、启动跟随或调整限幅，等用户明确继续后再开展。
## Knowledge Map
README.md；mint_follower_demo/SECURITY.md；workspaces/so101_ws/AGENTS.md；docs/ARCHITECTURE.md。

主从迟钝待办：`plans/teleop-latency-20260922/task_plan.md`；已有证据：同目录 `REPORT.md`。

数字孪生实验：`experiments/colab-twin/README.md`；当前计划：`plans/colab-digital-twin-20261001/task_plan.md`。毕业设计与答辩材料位于被 Git 排除的 `local-documents/`，只保留在本机。
