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
2026-10-02 学习接续完成单回合门槛：补七条接近末端、早期持物、搬运、蓝盘接近及低位释放的实际策略偏差纠正，专家完整抓放与各自独立raw64回放均通过，state/env/time差全0；15份档案共25504有效标签，12226前缀/无效标签排除。五轴ACT在14份数据上训练，v11冻结这72个ACT状态张量，仅用15份数据重训独立学习夹爪。当前212项测试通过，无跳过，绑定11份纠正档案及最新释放回放。v11纯策略同一固定初态39.76s/1988拍完成抓起、绕障、蓝盘释放与稳定1s，无专家或安全停止；可见复跑动作/物理记录完全一致，995帧视频全量解码通过。S7d-single已完成。随后v11固定参考初态40轮评估全部结束：正常20/20、扰动3/20且20次均完整注入10拍；安全停止5次、仿真超时8次、失物4次。S7d整体未通过，S7e视觉与真机未运行。正常组20次NPZ数组完全相同，只证明重复性；小幅五轴目标脉冲恢复仍不足。随后已执行T1：补seed22/24/36三条held完整专家纠正及raw64零误差回放，合并18档案28863valid/16034invalid；冻结同一v10 ACT72状态张量，仅CPU6000step/8.200s重训夹爪。v12已见扰动探针0/3（22更早误开失物、24盘壁安全停止、36闭爪高位超时），正常仅复验1/1、48.40s。候选不替代v11；Seeds40..59保持未使用，S7d/S7e仍未通过，T2/T3/T4未启动。详见当前progress末节。可复现实验与owner根Codex见experiments/colab-twin/LEARNING.md及当前计划progress.md。数据/权重/审计Git忽略，现场22项旧变动/index/原MJCF保持。
2026-09-15本机跟随器/ROS工作区/场景归入本目录，旧路径兼容。2026-10-01 Colab CPU / MuJoCo 3.3.7 的六秒合成轨迹、无头渲染和结果回收已实际通过，位置 IK、OMPL 绕障和物理执行已接入，本地29项测试与Colab CPU 20轮目标扰动通过，可见场景与视频回收已复验通过。本机旧Git基线仍保留，发布通过独立delivery工作树串行整合。导入不再初始化硬件Runtime，回归测试使用合成数据；部署仍需本地配置和标定。
2026-10-01 主线接续：新增本地 `experiments/colab-twin/run_staged.py` 四层单回合入口。复用已安装 MuJoCo3.3.7/Mink1.1.0/OMPL2.0.1；依赖导入、reset/10步、单次绕障和位置伺服执行均实际通过。TCP误差0.549mm，20ms碰撞无无效采样，关节限位超出0；378帧视频完整解码通过。32项回归检查通过，缺失依赖入口实际拒绝并保留阶段报告。输出按UUID分轮保留且被Git忽略。执行只覆盖静态路径和仿真位置伺服反馈，动态重规划、抓放、视觉和实体同步继续待办；GR00T云端尝试保持停止。

## Current Priority

2026-10-01 用户进一步指定：有限资源下接续“MuJoCo仿真→自动示范→扰动恢复→模型训练→仿真策略闭环”，WASD不作为训练数据源；要求真实AGY/CODEX/ZCODE有引用讨论。实际会审完成，保留MLP与无图像ACT的顺序分歧。根Codex建议先补同步数据和专家恢复，再预检小配置状态ACT；模型选择尚无本机训练证据，不算已交付策略。详见[学习会审与接续门槛](plans/colab-digital-twin-20261001/learning-review.md)。训练依赖使用独立环境，保留已通过的规划环境；不重新分配GR00T/Isaac云端GPU。

2026-10-01 用户指定：运动自主规划以 **MuJoCo 为核心**，收敛为一条主线。在已有 Colab CPU 平台上接入位置 IK、OMPL RRTConnect、MuJoCo 碰撞检查、轨迹执行和统一评估；先完成给定目标与障碍的自主到达，再扩展抓放与视觉。已有 MoveIt/OMPL 配置、轨迹导出和评估字段作为续接资产；Gazebo 保留为后续本地 ROS 联调模块。AGY 的只读咨询也推荐这一方向。五轴位置到达及单场景静态障碍接触抓取、搬运、释放落定已实现；扰动批次、视觉和实体同步继续留作下一阶段。

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

## 2026-10-01 障碍夹取接续

主线已完成单个静态障碍场景的自由物体接触夹取：grasp_episode.py使用指间中心垂直IK、OMPL绕行和同一物理状态中的下降/闭爪/抬升/保持；直接路径被挡，抬升38.675mm、双指持续夹持1.48s，逐步障碍接触0，20ms实际机械臂碰撞/限位检查无无效样本。38项回归测试及真实空夹负例通过，953帧/38.12s视频完整解码并检查近景。

指尖接触垫、摩擦和.15Nm夹爪力矩是派生仿真假设，未做实体标定；原始MJCF/STL保留，无焊接/动画附着。结果保存在被忽略的experiments/colab-twin/output/单轮目录。当前下一步是放置/释放/落定及扰动批次；动态重规划、实体与云端模型仍未验收。根Codex沿用已有计划接续，不恢复GR00T GPU尝试。

## 2026-10-01 搬运放置

新增placement.py与`grasp_episode.py --place --render`：夹起后保持竖直沿内侧绕障，载物占位/关节边独立查询，进入蓝盘下降、松爪、撤离并落定。Noslip10次解决软接触慢滑，夹爪力矩仍.15Nm；未修改自由物体状态或原模型。最终物体距蓝盘中心约1.6mm、真实盘底支撑、双指接触力0、撤离后稳定1.48s。逐步障碍接触0，20ms机械臂碰撞/限位无无效样本；41项测试通过，真实滑落停止负例与部分轨迹保留。972帧/38.88s固定机位搬运放置视频全量解码通过。

此为固定单场景前向仿真，接触垫/摩擦/Noslip均未做实体标定。下一步owner根Codex：扰动批次或视觉目标接入；动态障碍、实体与云端神经模型仍未验收。结果继续按UUID保存在Git忽略的output目录，原模型/index/现场数据不变。

## 2026-10-01 有限资源状态学习

已实现统一raw64 HDF5、真实起点扰动/专家恢复、严格动作回放、官方ACT/裸Torch MLP资源双探针及分层止损入口。原动作3133步state/env/time误差0；两模型均通过4GB本机资源门槛。选ACT做5000step/约119秒单轨迹诊断，权重保存重载一致，首动作MAE0.01085rad；纯策略0.36秒后障碍碰撞停机，抓放未通过，20+20/视觉未启动。入口experiments/colab-twin/LEARNING.md；owner根Codex，先处理在线状态偏离/恢复覆盖。data/weight/log继续Git排除，未连接机械臂或分配云端GPU。
