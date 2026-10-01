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
2026-10-01 主线接续：新增本地 `experiments/colab-twin/run_staged.py` 四层单回合入口。复用已安装 MuJoCo3.3.7/Mink1.1.0/OMPL2.0.1；依赖导入、reset/10步、单次绕障和位置伺服执行均实际通过。TCP误差0.549mm，20ms碰撞无无效采样，关节限位超出0；378帧视频完整解码通过。32项回归检查通过，缺失依赖入口实际拒绝并保留阶段报告。输出按UUID分轮保留且被Git忽略。执行只覆盖静态路径和仿真位置伺服反馈，动态重规划、抓放、视觉和实体同步继续待办；GR00T云端尝试保持停止。

## Current Priority
2026-10-01 用户指定：运动自主规划以 **MuJoCo 为核心**，收敛为一条主线。在已有 Colab CPU 平台上接入位置 IK、OMPL RRTConnect、MuJoCo 碰撞检查、轨迹执行和统一评估；先完成给定目标与障碍的自主到达，再扩展抓放与视觉。已有 MoveIt/OMPL 配置、轨迹导出和评估字段作为续接资产；Gazebo 保留为后续本地 ROS 联调模块。AGY 的只读咨询也推荐这一方向。五轴位置到达已实现；接触抓放、视觉和实体同步继续留作下一阶段。

2026-09-22：主从跟随迟钝已完成静态/离线诊断；用户当前不便使用实体机械臂，后续采样与修复标记为待处理。不自动连接硬件、启动跟随或调整限幅，等用户明确继续后再开展。
## Knowledge Map
README.md；mint_follower_demo/SECURITY.md；workspaces/so101_ws/AGENTS.md；docs/ARCHITECTURE.md。

主从迟钝待办：`plans/teleop-latency-20260922/task_plan.md`；已有证据：同目录 `REPORT.md`。

运动规划路线：`docs/MUJOCO_MOTION_PLANNING.md`；选择依据：`docs/DECISIONS.md`。数字孪生实验：`experiments/colab-twin/README.md`；当前计划：`plans/colab-digital-twin-20261001/task_plan.md`。毕业设计、答辩材料和原始 Agent 咨询位于被 Git 排除的 `local-documents/`，只保留在本机。

GR00T / LIBERO 扩展（2026-10-01）：`experiments/gr00t-libero/README.md` 与 `plans/gr00t-libero-20261001/task_plan.md`。最后一次尝试（第六次）已按用户指令完成并停止。L4 上官方 GR00T frozen 安装通过，LIBERO 依赖实际进入 Python 3.12 client venv，环境错位问题已在云端修复；随后导入 Matplotlib 因继承的 `module://matplotlib_inline.backend_inline` 后端不可用而失败。失败归档已回收并通过清单/哈希核验，模型加载与策略回合未启动。远端 worker 已结束，执行连接仍未返回；根 Agent 对唯一控制进程发送 SIGTERM，新的有界清理路径实际保存报告并成功 unassign，最终 active_assignments=0。子进程现固定 `MPLBACKEND=agg`，本地无头 PNG 绘制通过；该后端修正尚未云端复验。此轮不再分配 GPU，后续云端尝试需用户新的明确指令。 保持 MuJoCo 主线；Panda 实验不代表 SO101 策略迁移。

## 2026-10-01 单臂夹取建模

用户指定先建模、改善场景，并纠正主从为现实系统；本轮只有一台从臂。找到本地BLD-001建模说明、主从场景生成器和动作模板；当前工程无其记载的Blender/GLB成品，LightArmPreview.vue与leader专属STL为零字节。复用完整的原生从臂13STL，新增grasp_workcell.py/preview_grasp_workcell.py及动态物体/夹爪检查。

新模型包含工作台、开放红/蓝料盘、相机支架、自由物体；生成1280×720三视图与100帧/4秒机械开合视频。原模型SHA仍d75253eb568e8a7214db9c631ab7bed4217f608a26f7276ebe9a7636cac82580。物体18×18×16mm、10g；实测中心z从0.012m落定至0.009784m，真实pick_floor接触。夹爪实际范围0.250019–0.799997rad，预览期间物体抬升约0；grasp_success/lift_success=null，尚未夹取成功。视频独立全量解码通过，34项回归检查通过。派生MJCF可编辑，原模型不改；无实体或云端操作。

结果保存在Git忽略的experiments/colab-twin/output/grasp-model-72f103318b2a4cf78c7b89f317ee53ed/。原场景建模说明只用于布局参考，仿真坐标和物理参数不当作实物标定；现场模板不复制发布。后续owner根Codex：先对位/接触建模，再以物体抬升与持续夹持验收；已有静态规划入口及遗留交接保留。
