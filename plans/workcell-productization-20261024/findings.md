# SO101 工位产品化：事实、决定与待证项

日期：2026-10-24。本文汇总本轮只读核实，作为产品化计划的证据入口。
本轮仅编写计划，不改变控制器、默认策略、运行服务、Mint 或实体设备，不新增仿真、训练或云任务。

后续实施以progress和以下更新为准；上句仅描述D0初建。

## 固定红盘右侧：工艺顺序已用原物理证实

X+20mm的60mm高位腕限位与大张口盘壁拒绝是两个约束。保留原95°限位和全部碰撞，使用已有54mm高位，先在高位实测收至.35且稳定，再下降；高／低位完整扫掠各246点。原大开度仍fail，显式候选在原主与(.20,.20)两个放置工位分别原pass79.26／82.34sim，原中心回归pass76.62sim，红盘未移。完整50Hz与连续工作区未验，默认不切。详细源／原件／失败和复跑见[m1a-x-fixed-certificates.md](m1a-x-fixed-certificates.md)。

## 固定红盘 X 向补证（2026-10-24）

原19轴不足与真实可用路线分开。新增可选原生API沿用完整顶点区间投影／原平方门，默认查询不变。左X−20mm下降74／闭爪244／抬升74补证全过，原offline_screen_pass=false保留；右X+20mm采用已有54mm IK姿态，独立64拒绝点中18补证、46仍拒绝，不能凭补方向解锁。原件、失败覆盖与复跑见[m1a-x-fixed-certificates.md](m1a-x-fixed-certificates.md)。未跑新物理、未扩大网页准入。

## M1b 回位瓶颈更新

- 同365db2b源的原X−20布局观察ca00cc74…完整抓放通过。只读profile记录75次arm检查与150次双pad SAT，但父帧统计缺失，且复制快照额外120ms；不使用其最大拍做性能A/B。
- 同MuJoCo3.15和同冻结MJB的5次无积分复算，原_return_path每次都是validated_direct、75状态、原.005rad分辨率；路径逐位一致。中位131.131ms；原arm检查累计约38.875ms、释放物距离累计90.489ms，未触发OMPL。旧140ms尖峰有具体同步计算证据，不能再笼统归因随机搜索或主机等待。
- 新候选保留算法与所有判据，只迁移实测q出发的完整回位规划。复用已consumed/joined的独占模型和原异步生命周期；结果接纳前保留上下文、实测桥接、首命令与预算。预计回位路径仍不能直接当作实测回位轨迹。
- 默认不开启候选；同输入等价、原完整物理与完整周期分别裁决。局部测试不是抓放通过；新增等待不能当作算法计算减少。
- 已完成三对同输入等价和两X布局反序4/4原物理。左首回位完整拍143.018→33.347ms、右36.634→30.314ms；候选仍超20ms，整程wall/CPU两侧方向不一致，不晋级默认。具体原件、指标和限制见[m1b-return-results.md](m1b-return-results.md)。
- 新只读准入回合c0045f5f…原pass。最终_poll_return14.613ms，其中job生命周期自身约.067ms；两次原validate_joint_path共6.652ms，binding约4.742ms。完整首retreat33.843ms，controller之外与poll之外仍有成本，不能称仅剩线程切换。原最大116.359ms在transport，callbacks105.803wall／3.227threadCPU；它证明主要是主线程等待，尚不能区分文件I/O与宿主调度。不能把全部归给SAT、GC或原算法计算。

## M2/M4 薄适配更新

- M2原物理抓取证据已过新完整抓放与真实取消；[结果](m2-grasp-evidence-results.md)。progress回调可在物理推进后、monitor更新前取消；因此轨迹行数不等于已评分行数。新证据记录实际observe数量，取消1511/1512行，不把完整轨迹重算hold3.56s盖掉原3.54s。显示层接收深拷贝，不能污染原证据；历史Grasp后置条件与最终attempt失败分开保存。

- 2026-10-24新配方原物理1/1与真实运行中取消已独立回读，见[m4-recipe-results.md](m4-recipe-results.md)。两项是功能／生命周期验收，不是性能A/B。完整回合最大60.075ms在transport，controller54.017wall/54.017CPU；两例close段也重复约40ms controller，不能套用前轮callbacks等待归因。下一次50Hz分析应按当前同源实测重定位。
- M2新接点审查：原progress_callback早于monitor.update，不能以stage发布技能成功。Grasp应以原持续双指接触／抬升monitor为后置证据；ReleaseAudit在脱离后仍可能因重接触转失败，Place与Retreat证据不可按阶段硬切。真值仅作裁判／展示，不反馈恢复控制。

- 原Station只根据cancel文件存在优先发布cancelled，会覆盖更早物理fail及晚到请求前已完成的pass。现已分列cancel_requested／cancelled，仅真实Cancelled且无原安全、清理和其他失败原因时取消；原report保留。22项Station CPU检查通过，不冒充运行中取消实测。
- 六技能不能只换阶段名：原progress在monitor.update前，close结束不证明抓住，Place的释放审计可能在Retreat中才完成。生命周期应消费初始视觉、实际issued、post-monitor、finally清理四类证据；完整恢复尚未实现。
- 配方复用原Station payload与原任务入口，不另写执行器。前端和CLI共同核米制、纯平移、独立episode、SO101执行器、固定技能声明；未知可选元数据与历史引用保留，历史pass不产生当前pass。节点rotation及SO101未执行的size/motion/enabled明确拒绝，避免旧容错导入器无声丢弃执行语义。
- 配方交换不等于FishBot同世界卸货。当前pick世界Z=0、cube Z=.01；车载高度、连续货物身份和同world/episode仍待实现。

## 已核事实

### 工位范围与运动学

- 当前输入合同要求工件中心 `XY=(0.24±0.01,-0.13±0.01)m`、`Z=0.01m`。
  这是执行器的显式检查，不能直接解释为机械臂只能移动 ±10mm；见 [station_executor.py:170–172](../../experiments/colab-twin/station_executor.py)。
- 实际 IK 接收 `xyz`，残差为位置误差乘 10、夹爪局部 Z 轴对齐世界竖直轴，以及 `q[4]*0.1`。
  它没有输入世界 yaw 或完整目标旋转矩阵；见 [grasp_episode.py:114–128](../../experiments/colab-twin/grasp_episode.py)。
- 求解器要求上述总残差范数 `<1e-5`，不能把 wrist-roll 项仅当作不影响接纳的软排序。
  该组合是否缩小可用工作空间尚未对照证明；见 [grasp_episode.py:130–137](../../experiments/colab-twin/grasp_episode.py)。
- 接近、下降、抬升及运输实际调用此 IK；见 [visual_grasp_controller.py:334–339、877–879](../../experiments/colab-twin/visual_grasp_controller.py)。
- 径向 yaw 需要工具轴、零位、父体变换和夹爪偏移映射，不能直接等同某个关节角。
  模型存在肩部偏移及局部关节轴；见 [so101.xml:49–102](../../workspaces/so101_ws/src/so101_mujoco/models/so101.xml)。
- 对象对称性决定可放宽的朝向。圆柱、方块和有朝向要求的零件不能采用同一 yaw 自由度假设。

### 性能与现有快慢环

- OMPL 已设置进程首次规划 seed：仅 `_INITIAL_SEED` 为空时调用 `setSeed(max(1,requested))`。
  报告明确记录 `rng_seed_scope=process_first_plan`；见 [joint_planner.py:105–112、162–164、190](../../experiments/colab-twin/joint_planner.py)。
- 这不等于每次规划重置 RNG。调用顺序、实例创建和输入仍需记录；官方区分全局 seed 与实例 seed。
  来源：[OMPL RNG 官方文档](https://ompl.kavrakilab.org/classompl_1_1RNG.html)。
- F2ce 在同一次 ratchet 中复用完全相同参数的纯 SAT 结果，保留原距离、forward、native 和 pad 查询。
  176 输入组件三对均省计算，中位 wall 省 119.533ms；见 [原进度:1697–1703](../factory-loading-20261021/progress.md)。

| F2ce 工位 | 原版→候选 process wall | 完整慢拍 >20ms | 原物理裁判 |
| --- | --- | --- | --- |
| 200/200，B→C | 54.044251→52.726573s | 139→123 | 2/2 通过 |
| 220/170，C→B | 49.478408→50.707895s | 80→106 | 2/2 通过 |

- 两站共 4/4 物理通过，但整程性能一好一坏，候选未晋级；见 [原进度:1705–1716](../factory-loading-20261021/progress.md)。
- 初始化和 transport worker 在候选介入前已有差异；固定非 hold/release 拍数的 CPU 也不一致。
  不能把约 ±1.3s 的整程差异归因于 SAT 或 OMPL 随机路长；需分别核原路径、阶段拍数和运行开销。
- F2cf 是原控制器的叶段观察：3867 完整拍，P50 10.229ms、P95 17.293ms、max 83.863ms，148 拍 >20ms。
  原任务通过，完整 50Hz 未通过；插桩秒数不能与其他 VM 拼成加速 A/B；见 [原进度:1725–1729](../factory-loading-20261021/progress.md)。
- 同回合 measured checker、configuration sweep、validate_joint_path 的 max 分别为 2.718、40.538、64.135ms。
  它们是 inclusive 时长，不能相加为总成本；见 [原进度:1733–1740](../factory-loading-20261021/progress.md)。
- 已观察到同步 244 闭爪认证和回位完整认证；一次 sweep 内发生 35.426ms gen2 GC。
  该事件只证明该插桩回合，不能据此解释全部历史尖峰或直接命名为 GIL 等待；见 [原进度:1742](../factory-loading-20261021/progress.md)。
- transport 和 separation 已有异步 worker。主线程继续轮询、检查上下文、认证现场桥接和首指令。
  见 [visual_grasp_controller.py:759–815、1031–1156](../../experiments/colab-twin/visual_grasp_controller.py)。
- 回位直接路径复验及必要时 OMPL 仍有同步入口；每次 update 仍检查实测状态。
  见 [visual_grasp_controller.py:991–1000、1372–1375](../../experiments/colab-twin/visual_grasp_controller.py)。

### 共享工位与连续世界

- 5186 `/so101-station` 由 FishBot 仓库的 `apps/fishbot-control-station/so101-runtime.cjs` 调用 SO101 执行器。
  这证明已有跨仓入口，不能按端口认定两套独立前端；见 [STATION_EXECUTOR.md:81](../../experiments/colab-twin/STATION_EXECUTOR.md)。
- 当前执行器接收 Station 或任务信封，每个输出目录是独立 episode；不能直接当作同世界连续卸货。
  见 [STATION_EXECUTOR.md:18–38](../../experiments/colab-twin/STATION_EXECUTOR.md)。
- FishBot 连续计划规定 Physics 是活动世界唯一 writer，bridge 持有任务与原生 Goal，Oracle 只读。
  继续扩展原 factory/workflow，不新建调度服务；见 [连续计划:42–45](/home/muqiao/dev/ros2/projects/fishbot/plans/continuous-twin-regression-20261024/task_plan.md:42)。
- 已验收运输使用 ideal 观测及显式 reset，不能据此宣称视觉或无 reset 连续任务已通过。
  见 [COOPERATION_WORKFLOW.md:141–151](/home/muqiao/dev/ros2/projects/fishbot/docs/COOPERATION_WORKFLOW.md:141)。
- 连续计划要求两个独立自由货物、同一 world/episode/源时钟/编码器/车体位姿，第一件送达后原位继续。
  禁止 reset、传送或改名替代连续性；见 [连续计划:125–129](/home/muqiao/dev/ros2/projects/fishbot/plans/continuous-twin-regression-20261024/task_plan.md:125)。

## 本轮决定

- 继续复用 MuJoCo、现有 IK/OMPL、控制器、评分器、FishBot 工作台和原 Workflow/bridge；本轮不选新引擎。
- 将径向 yaw 作为待比较候选；保留对象朝向与对称性合同，先验证 IK、碰撞、连续路径及真实接触。
- 将 ±150mm 作为待测产品目标，先定义它是 XY 方形范围还是半径，再发布实际测得的有效区域。
- 将 3–5ms 与 P99<20ms 作为架构目标，明确统计对象；不把它们写成锁 seed 后必然得到的结果。
- servo-only 与原完整周期分开报告；完整周期保留安全检查、感知、worker 准入、244 闭爪和回位切换。
  两者均报告样本数、P50/P95/P99/max 和 >20ms 数量；P99<20ms 不等同全部周期满足 50Hz。
- 快环只执行已获认证范围内的命令；迁出在线认证前，先证明慢环证据覆盖实际状态、上下文和执行区间。
  复用冻结快照、context binding、现场 achieved-q 桥接、首指令守卫、取消和原回退，不以删除检查提速。
- 原 planned/measured 244、trajectory guards、碰撞阈值、自由物体 weld0/mocap0、抓放释放脱离回位继续验收。
  双 worker consumed/joined/owned_ack、90sim/120wall 也保持；见 [原进度:1714、1729](../factory-loading-20261021/progress.md)。
- `station_recipe_v1` 定位为共享工位配置合同，先静态导入与预览，派发仍走原任务入口。
  待实现字段包括配方/资源身份、单位与 frame、模型/碰撞来源、能力段、显式观测模式及稳定 cargo/slot 绑定。
- recipe revision 用于来源与兼容描述，不设内容哈希锁；未知可选元数据警告并保留，不支持的执行语义只拒绝该配方。
- 任务运行绑定另存原 bridge UUID 与 station task ID；取消、超时先查询原任务，不因回执不明重复派发。
- 卸货与库存需绑定同一实际物理 body；货架落稳、卸载臂归位和托盘空闲成立后，按 cargo ID 更新一次。
- 行为树如后续采用，异步节点只负责启动、监控、结果与取消；耗时动作不能阻塞 tick。
  依据 [BT.CPP 异步节点官方文档](https://www.behaviortree.dev/docs/guides/asynchronous_nodes/)，该模式不保证自动并行或实时性能。

## 未知与验收入口

- 径向 yaw 是否改善工作空间、严格 wrist-roll 残差实际拒绝了哪些点、±150mm 可用区域：均待测。
- 本轮没有重新逐点复核原 A/B 路径；已有原进度不能支持“随机路长造成约 ±1.3s”结论。实施时继续保存原路径与规划事件，不能仅看总 wall。
- servo-only 3–5ms、完整周期 P99<20ms、所有切换拍 50Hz：均未取得新架构验收证据。
- `station_recipe_v1` 导出/导入、终点卸货、同世界无 reset 多货物及双 owner 取消汇合：均待实现或验收。
- 当前源码默认观测模式、任意动作编排、Mint teleop 接口：本轮未核实；Mint 不改。
- 性能采用同输入、同工位和反序成对比较；组件收益、原物理成功、整程性能及默认晋级分别裁决。
- 连续世界沿 FishBot 原计划进入实施；新卸货阶段单列预算，不能把扩展任务记成旧 360 秒任务通过。

## M1a 首切片：离线实测与开发入口

新 [空间探针](../../experiments/colab-twin/probe_workcell_workspace.py) 复用原 IK、保守证书、1mm 阈值和 .005rad 抓取腿检查，不推进物理、不认证完整闭爪或后半程。11 点中 9 点通过离线筛选。X−20mm 的 down 对 `pick_wall_x_-1/collision_gripper_1` 证书下界约 0.880489mm，不能认证 1mm 净距，不冒称已证明真实碰撞；X＋20mm 的 approach/lift 原 IK 失败。Y±20mm 端点与抓取腿通过，仅作为物理候选。

编译模型回读：base 位于 world 原点；shoulder_pan anchor 为 `(0.0388353,-8.97657e-9,0.0624)m`，其 world 轴约 `(0,0,-1)`；顶视相机 `(0.25,0,0.95)m`、R=I、fovy45°，局部 −Z 朝下。工具 pinch 是局部 `(.006,0,-.094)m` 的变换点。该结果是仿真 frame 核对，不是实体相机标定，也不能把径向 world 角直接当 pan 角。

源码另有控制器 `_target()` 的 ±10mm 限制。新增显式 `target_region_xy_m` 仅供开发配置使用，初始与后续 RGB 估计共用同一静态先验；默认表达式和消息保持。网页 validate/describe 仍为原 ±10mm。新 [开发入口](../../experiments/colab-twin/run_workspace_case.py) 按 [四案例 profile](../../experiments/colab-twin/scenarios/workspace-m1a.json) 复用原 `run_physical_episode`、评分与录像，输出 `development_only/not_admitted`；不能因开发案例成功就开放完整矩形区域。

当前本地原实验环境为 `/home/muqiao/.cache/so101-colab/planning-venv/bin/python`（MuJoCo3.3.7），旧 graspgenx venv 已不存在。为运行既有控制器检查，仅在该隔离环境新增与已验云环境同版 `opencv-python-headless==5.0.0.93`；没有改系统环境、NumPy 或 SciPy。Kaggle 继续复用原 bootstrap／串行 runner，单独记录其 MuJoCo3.15 环境，不跨机器比较速度。

## 已采用知识

- 来源：[Wiki《ROS2 与 FishBot》第20节:451–468](</home/muqiao/桌面/obsidian/my-programming-world/Wiki/ROS2 与 FishBot.md:451>)。
  本轮采用“动作、物理、交接、晋级分开”及“组件收益须回到原完整任务核实”的既有原则。
- Knowledge=already_covered，仅指本轮原则已被原页覆盖；本轮未修改知识页，不代表其他待审内容已收尾。

## X 方向：限位与证书分离（2026-10-24）

原 X+20mm、60mm高位已到腕俯仰95°边界，去掉roll偏好不解决；54mm高位可解但原盘位的低位仍不认证。X−20mm低位的0.880489mm为证书下界；全编译网格投影有16.773623mm分离轴证据，因此不能把它直接叫实际撞壁。详见[m1a-x-results.md](m1a-x-results.md)。

本次选择显式工位布局薄适配，保持原检查器、阈值、夹持／释放裁判。新参数与测试分别在grasp_workcell.py、grasp_episode.py、visual_grasp_controller.py及run_workspace_case.py。原网页与±10mm不变；局部筛选仅是原物理的前置。右侧最薄证书仅比1mm多约4μm，动态跟踪风险必须由原物理核验。

X开发布局随后在固定e7f921c的Kaggle v1原物理4/4通过；planned/measured244、RGB、释放/脱离/回位和worker独立回读均完整。新布局可复跑，原固定盘位X拒绝并未消失。完整50Hz未过。具体输入、成绩、反证与复跑见m1a-x-results.md，不将布局结果写成算法加速或区域全覆盖。

## Station入口接续的实际所有权

5186源码实际在FishBot的独立工作树`/home/muqiao/worktrees/fishbot-workbench-code-rebuild-20261018`，分支codex/workbench-code-rebuild-20261018，入口apps/fishbot-control-station/so101-runtime.cjs与Lichtblick RobotStation；不是主FishBot dirty main。复用原task-runtime、任务UUID、取消、scene与录像。此前仅写FishBot仓库相对路径的记录不足以确定运行checkout，本轮已更正。开发参数用显式execution对象而非隐藏profileID覆盖节点；只有省略execution才用原默认，坏声明保留给原准入拒绝。

## 新Station／网页结果与M1b下一证据

真实网页输入经新Station源码084cc7f，原物理左右2/2通过；不是重用开发CLI成功标签。证据与未采计时边界见m1a-station-entry.md。并行工作台Drone源码由原owner后续提交de94a6d；本轮未改其模块或主FishBot工作树。

旧X四回合timing的exclusive parts只读归因：15641完整周期，281拍>20ms；controller主导218、perception51、physics_and_guards12。最大140.476ms/135.697ms位于separate→retreat同步_return_path(q6[:5])，主线程CPU接近wall；尚未细分函数内部，不能归因于特定碰撞算子。worker的planned_return目前用于预算/报告，不可直接代替实测q回位。私有可复跑审计round102/m1b-slow-cycle-audit.json保留全部原index、stage和top10。下一步限于这一有证据的交接点，全部安全责任不丢。
