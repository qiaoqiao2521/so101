# 工作站草稿执行适配

`station_executor.py` 将网页 Station JSON 接到原 `run_visual_grasp.run_physical_episode`。输入支持裸 Station，或 `{id, submittedAt, station}` 任务快照。仅运行 MuJoCo 仿真，不访问机械臂串口或恢复训练。

```bash
~/.cache/so101-graspgenx/upstream/.venv/bin/python \
  experiments/colab-twin/station_executor.py \
  --station /absolute/task/request.json \
  --output-dir /absolute/task \
  --cancel-file /absolute/task/cancel.request
```

`--describe-json` 返回中文能力说明。`status.json` 原子更新，包含状态、阶段、仿真时间、原报告及产物路径。创建 cancel-file 后，原执行循环协作停止并保存报告及部分录像。界面只能在终态后显示已取消；无法规划、定位拒绝、碰撞保护、物理任务失败分别保留。

当前支持可复制、可修改放置目标的八步搬运任务：开爪→接近→抓取点→闭爪→抬升→放置→开爪→脱离。目标位置与参考系按已声明模板映射，实际运动由现有控制器规划；步骤 seconds=1 是编辑模板字段，不等于每段一秒。

- 方块世界坐标支持 X=0.24±0.01m、Y=-0.13±0.01m、Z=0.01m。
- 附加 obstacle 节点采用 50×56×130mm 轴对齐方盒，原内置障碍同时保留。
- 参考系逐级平移求和；机器人与取料区域保持原值。place 坐标系的 XY 为当前任务蓝盘中心，Z 为高出台面的底座高度，release/clear 随同移动并保持原相对偏移。
- 蓝盘保持同尺寸，底座投影需完整位于原工作台上；非负高度的可达性和碰撞由现有规划器逐任务检查。其他目标偏移、额外物体、程序重排和时长仍会列出具体原因；不会回退到旧场景。
- 释放复用已有 floor_yaw 和距底座28mm的指间高度；1mm 净距、释放2mm漂移/0.02N再接触等原物理标准不变。

输出包括 `resolved-station.json`、`episode/report.json`、轨迹、定位图和本次录像。录像以真实物理状态快照后置渲染，640×480、6.25fps；不推进物理、不制作脚本附着物体动画。无新内容哈希门锁或前序任务依赖，每个输出目录是独立回合。

## F2 工位高度与评测入口

[抬高10mm示例](scenarios/factory-loading/raised-10mm.json)可直接导入工作台。选择“放料坐标系”修改Z，释放点与脱离点沿父坐标系平移。实际托盘、碰撞底座、规划副本和预览使用同一高度。比如Z=0.01时，盘底顶面为0.012m，方块静稳中心为0.020m；原静稳高度容差仍为2mm。旧任务Z=0保持原几何和判定。

从本项目根调用已有物理评测：

```bash
~/.cache/so101-graspgenx/upstream/.venv/bin/python \
  experiments/colab-twin/evaluate_station.py \
  --station experiments/colab-twin/scenarios/factory-loading/raised-10mm.json \
  --output-dir experiments/colab-twin/output/factory-loading-local
```

每次调用创建独立run目录，输出`evaluation.json`和原始报告；根输出目录的同名JSON指向最近一次结果。字段含scenario_id、run_id、mode、state、verdict、metrics、units、failure_reason、candidate、scorer和artifacts。候选引用记录本次源码路径、Git提交、未提交文件及实际加载模块路径；它是来源描述，不是禁止二改的锁。进程返回0须原物理报告通过；未运行或缺报告记unscored，取消不算通过。

可用[原高度](scenarios/factory-loading/baseline-0mm.json)作回归，用[负高度](scenarios/factory-loading/invalid-negative-height.json)检查明确拒绝。不同布局应分别保留输入和结果；单场景成功不代表其他高度都能到达。策略改进可修改控制器或路线规划，比较时固定场景、评分器、物理参数和安全阈值。不得修改裁判来提高分数。本入口不启动训练、20+20评测或实体机械臂。

[独立XY复核输入](scenarios/factory-loading/layout-place-220-170-0mm.json)把蓝盘中心改为(0.22,0.17)m、高度0，其他节点、内置障碍和程序保持原值。该输入在2026-10-21的baseline/candidate2两个完整物理回合均通过（75.26/75.04sim秒）。每策略仅一次观察，默认基线保持；历史记录或本次局部缩时不代替其他布局验收。

[第二放置工位输入](scenarios/factory-loading/layout-place-200-200-0mm.json)把蓝盘中心改为(0.20,0.20)m、高度0，与220/170工位共用原程序、方块、障碍和裁判。2026-10-22的baseline/原CLI候选2同输入完整回合均通过（77.04/77.00sim秒），都采用54mm运输和25.615mm脱离；0.04秒差仅在hold，默认保持，不宣称性能或泛化。

### 最小路线候选

`--candidate` 接受本地Python源码，实际执行其 `route_preferences()`。路线偏好包括：`transport_preference_m`重排原候选运输高度，`separation_steps`选择原13个上升路点的前缀，`ik_seed`选择原IK的延续初值或neutral初值。基线默认值为None、13、continuation；`route_strategies/shorter_route.py`选择51mm优先、前10点及continuation。所有碰撞采样、1mm净距、释放审计、时间判据和最终物理裁判均由原实现执行。

可选`transport_candidates`默认为1，保留首条完整认证可行路线。设为2或3时，沿原高度顺序寻找前N条完整可行路线，按原`motion_duration`加各段0.6s到达守卫取最短；等值保留原顺序。拒绝的高度不计入N，原高度回退列表保留；可行数量不足N时使用已认证者，无可行路线或未知错误仍明确失败。原90s/14s预算、异步快照和物理检查不变。

手写接口示例`route_strategies/shortest_two_routes.py`只设`transport_candidates=2`，其余均默认。该选项在2026-10-21独立XY的baseline/shortest-two两个完整物理回合均通过，但都选择60mm路线；多搜一条使该次hold增加0.70sim秒，默认仍为1，不将其当作提速成果。每个尝试记录认证墙钟、原路线时长及selected，`route_search`记录总搜索墙钟与实际认证数量并透传evaluation。原worker等待/墙钟照常包含额外规划成本；搜索时间与worker耗时重叠，不应重复相加，也不从任务总耗时中扣除。report.hold_duration_s是物理持物累计时间，hold阶段等待从trajectory分段读取。候选费用在冻结worker起态比较；原入场桥接仍会重新校验和计时，因此attempt费用不必等于最终motion_and_arrival_s。另有手写静态提案`route_strategies/prefer_054.py`，只把54mm移到高度顺序首位，针对200/200/0mm工位已测失败的60/57mm端点IK尝试；原回退、完整认证及其他默认值不变。此提案已在200/200与220/170工位完成原物理对照；仅200/200减少失败IK，整回合收益未稳定，默认仍为baseline。

```bash
~/.cache/so101-graspgenx/upstream/.venv/bin/python \
  experiments/colab-twin/evaluate_station.py \
  --station experiments/colab-twin/scenarios/factory-loading/raised-10mm.json \
  --candidate experiments/colab-twin/route_strategies/shorter_route.py \
  --output-dir experiments/colab-twin/output/route-comparison/raised-shorter
```

省略candidate实际加载已通过两工位对照的 `route_strategies/summary_fast.py`；直接station_executor缺省入口复用同一选择。显式传 `--candidate experiments/colab-twin/route_strategies/baseline.py` 可复跑原版，`seed_bound_direct.py`可复跑直接父版，`leaf_packed_inline.py`和`leaf_packed.py`保留此前实现；RoutePolicy()及其他显式旧候选不自动叠加任何后续开关。`evaluation.json`的candidate记录本次加载路径、入口源码路径、Git引用和实际返回的偏好；controller另记原执行器来源。`policy_execution`从本轮planning/report提取worker实际采用的运输高度与脱离目标。无效候选明确failed/unscored，不回退基线。正常候选的偏好经不可变快照传给原worker，不向它提供裁判或执行中的物体真值。

候选为本地审阅过的源码。比较时只修改候选文件，不改 `learning_env.py`、模型、场景、释放/碰撞阈值或评分。该小接口用于路线选择，不提供通用插件、代码隔离或训练框架。

工作台通过现有独立 FishBot 仓库的 `apps/fishbot-control-station/so101-runtime.cjs` 调用本入口，Web 依赖与机器人依赖各自安装。工作台地址 http://127.0.0.1:5186/so101-station ，右侧显示本次任务的原生实时三维，本次录像与原报告位于任务栏；原历史录像使用独立入口。

### 能力段与局部判定

工作站 `program` 可以直接保存原八步原子动作，也可以保存三段能力：

```json
"program": [
  {"id": "s1", "capability": "pick", "seconds": 1},
  {"id": "s2", "capability": "transfer", "seconds": 1},
  {"id": "s3", "capability": "place", "seconds": 1}
]
```

验证时分别展开为 `open→approach→grasp→close`、`approach→release`、`open→clear`，由同一控制器执行。当前只接受完整抓放组合；缺段、重复、错误次序、原子动作与能力段混写都会在模型装载前明确失败。`station_executor.py --describe-json` 的 `segments` 是网页读取的能力目录，不是任意代码执行入口。

[能力段0mm工位](scenarios/factory-loading/capability-segments-0mm.json)只把原程序的表达从八条原子动作改成 `pick→transfer→place`，节点、坐标、方块、障碍和任务目标均与原高度工位相同。2026-10-22 该输入完成原完整物理回合 `1fccf040-0dc6-49e7-9502-37e071273bb1`：74.78sim/60.748wall秒，抓取、放置、静稳、释放脱离与回位均通过，安全停机0、障碍接触0。

候选局部筛选可用：

```bash
python3 experiments/colab-twin/factory_minimum_suite.py \
  --baseline baseline-measurements.json \
  --candidate candidate-measurements.json \
  --output screen.json
```

两份输入均含 `measurements` 数组；每对记录 `source`、原 `verdict`、`output_equivalent`、`measurement_s`。基线与候选的 `verdict` 必须都精确等于 `pass`；缺失、`unknown`、`unscored` 和 `fail` 均淘汰。工具只输出是否值得进入原物理 A/B；没有运行仿真、没有替代120s/90s原裁判，也不把局部失败当成任务完成。

能力段的原子版兼容回合 `416351fe-b43b-4b04-b45d-6dc538f4916a` 在57.90sim/121.276wall秒触发原120秒上限，保留为失败；其抓取成功、持物30.42秒、无安全停机，停在搬运后的lower早期。能力段回合在上述负载下完成74.78sim/60.748wall秒，因此该失败不能归因于能力段展开，也不能将任一回合计为性能基准。

2026-10-20：35项定向测试通过。默认CLI完整回合成功，74.76sim/53.13wall；修改方块X=.245m并添加障碍后25.30sim协作取消，初态与XML确认输入被消费。浏览器经HTTP重新启动的完整回合74.76sim/50.22wall成功，另一次网页取消在4.16sim结束；刷新未重发。首轮旧释放配置触发再次接触并正确终止，失败保留。

证据在 canonical `experiments/colab-twin/output/station-integration-20261020/` 及工作台忽略的 `workbench-tools/output/station-tasks/`；运行产物不入 Git。上述是固定任务接入验收，不代替20+20鲁棒性评测、实时50Hz或实机验证。

## 实际几何与编辑预览

`station_scene.py --model-json` 输出原始 STL 白名单和默认完整场景。`station_scene.py --preview /absolute/station.json` 将草稿解析为标准 Foxglove SceneUpdate，仅调用 `mj_forward`，不推进物理。13 个原始 STL 对应 17 个机械臂和夹爪实例；编译时的 mesh 平移/旋转只反解一次。

`run_physical_episode` 的可选 `scene_callback(model, data, *, elapsed_s, phase, final=False, row=None)` 读取执行中的实际 `MjData`。不配置 callback 时保留原入口；显示导入、初始化或发送失败只警告，不覆盖物理结果。最后一帧在视频编码前强制发布。

工作站 `status.json` 新增 `scene`、`scene_seq`、`scene_time_s`、`scene_phase`、`scene_final`、`scene_source`、真实物块四元数与已有双指接触力。常规显示约 10Hz，阶段变化和终态强制更新；这不是完整控制周期 50Hz 的证明。Web 端复用原生 Foxglove 传输与 3D，不自行求连杆 FK。

2026-10-20 新实时三维验收：真实浏览器抓放任务 `e6ddc0ce-682c-4923-aebb-1990b3840784` 在 74.74sim/106.662wall 完成，夹取、放稳、脱离和回位均通过，无安全停止，静稳 7.52s；发布 838 个场景状态。网页取消任务 `5f390fa1-ad63-433f-ab4d-32cf7d9fe924` 在 5.12sim 结束，最后实际姿态保留，预览与任务切换可恢复该末态。根独立执行 19 项几何/执行适配测试通过，包含 XML/STL 独立变换对照、预览零物理步、可选显示导入失败不覆盖原定位拒绝。

证据在工作台忽略的 `workbench-review-tests/output/station-live/` 和 `workbench-tools/output/station-tasks/<id>/`。当前只验证固定模板与本机显示，仍不替代批次鲁棒性、50Hz、CY部署或实机验收。

## 同一任务目标贯穿执行

`validate_station` 输出 `place_xy_m`；`build_contact_scene(..., place_xy=...)` 从同一workcell生成实际模型与规划模型，重新编译两套XML。控制器、异步搬运快照和规划报告都携带同一个目标。物理评分读取实际 `place_floor` 中心，完整物块外廓需在原58mm内边界、真实接触、低速度和原静稳时长条件内。报告 `place_goal_xy_m` 记录真实场景目标。

修改place的XY不需要改Python。默认None保持旧中心；place的非负Z表示底座高度并贯穿执行/评分。释放/脱离点相对偏移或不支持的步骤仍明确拒绝。历史示范采集中的固定路径与state30语义保持，本次参数化对应工作台实际执行路径，不宣称所有旧实验入口都已泛化。

新目标暴露了原37mm竖直脱离路径偏好的腕限假设。现在仍优先规划37mm；仅在后续IK不可达、已有前缀满足原全臂/已释放物体净距且完整回位路径通过时采用该前缀。IK精度、1mm净距、pad单调脱离、q6/jaw全程采样及原释放审计不变。`release_plan.separation_end`记录实际距离与原因，不能把较短距离单独计为安全成功。


## 2026-10-20 数据驱动任务实际验收

| 任务目标 XY（m） | 入口 | 仿真/墙钟（s） | 结果 |
| --- | --- | --- | --- |
| (0.24, 0.14) | 浏览器默认任务0a7fa8c1 | 74.80 / 100.940 | 抓放、脱离、回位通过 |
| (0.20, 0.20) | 同页复制、改点、保存、刷新后新任务bc8ada28 | 77.06 / 110.560 | 通过；物块约(0.198959,0.198737,0.009961)m |
| (0.22, 0.17) | 首次失败输入原样CLI复验goal-a-repaired | 75.16 / 63.479 | 通过，原37mm脱离假设失败已修复 |

三个回合均由原物理报告判定，不是统计成功率。浏览器前两轮之间没有改Python；同一程序只改变place坐标。默认仍60mm中转/37mm脱离；B采用54mm完整认证中转和25.615mm完整认证脱离，所有原采样与净距保持。报告记录每个候选拒绝原因和正式采用高度。最后异常分类补丁只允许已知IK不可达降级，未知后端错误和取消原样传播；91项测试及81个subtest通过，A在最终源码完整实跑，B保存快照在最终分类源码上重演结果逐字段一致、150/150脱离采样通过。

首测A在64.40sim脱离IK拒绝、首测B在32.14sim搬运IK拒绝均保留失败。两个固定高度属于旧路线偏好；改目标后只采用满足原全路径检查的替代路线，不改阈值、不回旧目标。未来位置若仍无法规划，任务继续明确失败。

证据：本项目忽略的`output/station-task-goals-20261020/`及工作台`workbench-review-tests/output/station-task-goals/`、`station-task-goals-before-hover-repair/`、`station-task-drafts/`和原任务目录。新增接口默认兼容；旧学习state30与其他历史采集入口的固定路径未扩展。


精确距离复用实验：`route_strategies/reuse_separation_distances.py`只开启默认false的`reuse_separation_distances`。它仅在冻结分离worker内复用最后同一shape/float64位姿的已完成距离查询，保留全部原采样与取消检查；完整原物理首对2/2通过，但局部计时仍不一致，未晋级。保存快照可用以下原地探针复核；其pass只表示局部等值，不代表物理抓放成功。

```bash
MUJOCO_GL=egl /home/muqiao/.cache/so101-graspgenx/upstream/.venv/bin/python \
  experiments/colab-twin/probe_separation_distances.py \
  --episode <已完成回合的episode目录> --output <新报告.json> --repeats 3
```


`route_strategies/batch_separation_axes.py`是独立的默认关闭候选，只将冻结分离worker的SAT叉积构造批量执行；原标量实现、全部查询和采样仍保留。可用同一保存快照探针加`--candidate experiments/colab-twin/route_strategies/batch_separation_axes.py`检查实际接入路径。开发与物理成绩以原计划最新段落为准，局部通过不等于完整抓放或整回合提速。

原循环分段计时沿用同一工位执行器、评分、录像和90sim/120wall。默认运行100拍后主动截断，原verdict仍为fail，探针记录diagnostic_truncated；这不是抓放验收。

```bash
MUJOCO_GL=egl /home/muqiao/.cache/so101-graspgenx/upstream/.venv/bin/python \
  experiments/colab-twin/probe_episode_timing.py \
  --station experiments/colab-twin/scenarios/factory-loading/capability-segments-0mm.json \
  --output-dir experiments/colab-twin/output/<新目录> --cycles 100
```

无计时透明性对照另加`--no-timing`；完整诊断改用`--full-episode`，仍由原判据结束。报告逐周期区分wall和当前线程CPU，并将初始化、控制后录像、清理另列；规划线程和编码子进程不能重复加到当前线程分项。`evaluation_interval`仅为原evaluate调用区间，不是全进程；`full_process`未外层测量时留null。每次timing-probe保存在该UUID目录，并在输出根保留最新读回。计时默认关闭，不改变原网页或evaluate_station普通调用。

### 显式四顶点实验与完整周期计时

原评测可加 `--timing`，在本次UUID目录保存 `timing.json`，记录循环各段独占wall与当前线程CPU。初始化、收尾和录像另列；这个文件不是完整进程时钟。全进程wall/CPU由外层调用者测量，评分、取消与120wall/90sim上限保持。

`--candidate experiments/colab-twin/route_strategies/quad_vertices.py` 显式选择CLI17四顶点实验，默认baseline仍scalar。同一进程加载原生库后，不支持热切另一实现；每个评测用原CLI新进程。支持AVX2且算术环境允许时并行算四个独立顶点，尾数和失败回退走原scalar；不减少顶点、碰撞pair或配置扫掠。

2026-10-22该实验原nominal A/B两轮均完成抓放/释放/回位，但60.874→64.892全进程秒、controller+2.432秒，因此不晋级、不切默认。局部13.9%收益没有转化为整轮收益，候选仅保留供原样复跑。完整50Hz仍未通过，结果见原厂区计划F2m。

`route_strategies/small_direction_cache.py` 是CLI20独立候选，默认关闭且不组合quad。只将每帧非轴投影缓存改为按需16项小表；第17个不同键迁移至原unordered_map，空表不分配。全部方向投影、碰撞pair、扫掠与原数学仍保留。当前局部5500帧/强制溢出同值、三对中位省5.561%，原两工位四轮抓放均通过，但nominal省2.170s、200/200反而多1.224s，收益不稳定，不晋级或切默认。局部筛选不是任务成功或默认采用。

`route_strategies/tree_leaf8.py` 是CLI23独立候选，只改变BVH分叶大小，保留全部顶点、碰撞pair、路径采样与原保守计算。默认关闭；原三对局部成本下降，但完整抓放61.301对原60.938秒，未提速，不晋级。两轮3740拍轨迹全字段逐位相同；不将局部省时称为整回合收益。

可选ABI观察沿原完整执行入口运行，不替换原生结果，也不改变原90sim/120wall。按真实阶段记录调用wall/线程CPU，并保存拥有的几何、p/R/pairs/margin/hint_in。回放每条采样时恢复其原hint_in，不能从稀疏样本自行推导提示历史。worker墙钟可能重叠，不并入主循环总和。当前探针没有保存原始输出；离线两实现相等不等于与当时输出逐位核对。

两个诊断入口默认显式选择原版baseline.py，避免工厂默认升级后改变历史对照。需要测量已采用实现时，在probe_episode_timing.py或probe_native_abi.py添加`--candidate experiments/colab-twin/route_strategies/leaf_packed.py`。

```bash
MUJOCO_GL=egl /home/muqiao/.cache/so101-graspgenx/upstream/.venv/bin/python \
  experiments/colab-twin/probe_native_abi.py \
  --station experiments/colab-twin/scenarios/factory-loading/capability-segments-0mm.json \
  --output-dir <新的诊断目录>
```

### 已采用：叶顶点连续存储

CLI28只复制原mesh顶点为geom.order顺序的连续数组，每个同规模NativeSupport几何句柄约增加4.55MiB坐标副本，不是整个进程的RSS增量。原points/order/tree、逐点标量数学、全部路径采样/碰撞pair/安全阈值保持；可选副本分配失败时使用原数组。没有改变路线、IK初值或物体状态输入。

| 已有工位 | 原版全进程墙钟 | packed全进程墙钟 | CPU原版→packed | 原物理结果 |
| --- | ---: | ---: | ---: | --- |
| nominal，baseline→candidate | 53.338s | 51.413s | 60.628→58.451s | 两轮通过 |
| 200/200，candidate→baseline | 55.171s | 53.917s | 62.906→61.518s | 两轮通过 |

两个工位候选都反多0.04sim秒，controller墙钟分别少1.630/1.084s，收益不来自少等待。规划分项、释放/碰撞结果及原对照保存在[当前计划](../../plans/factory-loading-20261021/progress.md)。完整50Hz仍未通过。CLI28采用时的不带candidate入口另有完整抓放通过记录，并与该版本显式候选3741拍轨迹全字段逐位相同；该历史单回合用于接线验证，不当成额外性能对照或后续版本的默认实跑。

### 已采用：packed叶函数内联

CLI29沿用CLI28的点集合、顺序和数学，仅在支持的GCC兼容编译器下内联`leaf_vertex_interval_packed`。显式`leaf_packed.py`保留父版，`baseline.py`保留最初原版；其他候选不自动叠加。低层开关仍默认关闭，由工厂默认source选用已验证组合。

| 已有工位 | packed父版全进程墙钟 | packed+inline全进程墙钟 | CPU父版→子版 | 原物理结果 |
| --- | ---: | ---: | ---: | --- |
| nominal，child→parent | 53.339s | 52.863s | 61.054→59.864s | 两轮通过 |
| 200/200，parent→child | 56.511s | 55.244s | 63.473→63.003s | 两轮通过 |

两工位controller墙钟分别少0.395/0.938s，各少一拍hold；不把等待差视作全部提速。nominal的运输和分离worker反而更慢，完整周期P95从25.819增至26.142ms；200/200的P95从26.681降至25.947ms。采用依据是当前三对局部和两个已有工位的全任务/CPU收益，不宣称所有规划更快、统计稳定性或完整50Hz通过。四回合原抓放、释放脱离、回位、自由物体与全部安全判据通过；证据和复跑入口见原计划F2w。

### 已采用：同投影节点界复用

`route_strategies/seed_bound_direct.py`是CLI31已采用实现：保留packed+inline父版，只在一次full_tree调用内用128槽保存已计算的有限seed节点界。DFS按同node ID精确命中；冲突、缺项或非有限仍执行原dot/finite/full_scan。缓存不跨投影、姿态、帧或模型。CLI30排序/二分版成本不一致，未应用生产；CLI31首个无效Python交付及原CLI语法修复均留证。

| 已有工位 | packed+inline父版全进程墙钟 | 加节点界复用后墙钟 | CPU父版→子版 | 原物理结果 |
| --- | ---: | ---: | ---: | --- |
| nominal，parent→child | 55.582s | 51.401s | 62.137→58.763s | 两轮通过 |
| 200/200，child→parent | 57.113s | 52.710s | 65.196→60.309s | 两轮通过 |

两边均剔除全部hold周期后，非等待阶段拍数完全相同，controller仍分别少3.333/3.440s，非等待循环少3.776/3.916s。全进程差分别4.181/4.403s，不将任何少等拍当作算法提速。nominal两worker反而更慢；200/200两worker改善，分项保留。两工位P95分别27.597→24.831ms、26.591→25.166ms，完整50Hz仍未通过。

原四轮抓放、释放脱离、回位、碰撞与自由物体条件全部通过，原90sim/120wall/阈值保持。82项相关回归、2816真实输入及强制碰撞/空副本控制同值；默认选择变更另有38项入口/失败透传检查。原全量结果、失败、候选来源及准确复跑见[原计划F2x](../../plans/factory-loading-20261021/progress.md#f2x-同次树投影的节点界重复计算2026-10-23)。


### 已采用：Python全通过汇总

CLI33只减少汇总结果中的重复数组转换。创建查询绑定时选择快速方法；cert非零全部通过时直接返回原argmin结果，混合/失败/空输入委托保留的原方法。原C++、C ABI、原生库文件与flags完全不变，返回元数据用python_summary单独标记Python选择，pinned native manifest保持。显式seed_bound_direct.py仍使用原汇总。

| 已有工位 | 节点界父版全进程墙钟 | 加快速汇总后墙钟 | CPU父版→子版 | 原物理结果 |
| --- | ---: | ---: | ---: | --- |
| nominal，child→parent | 53.075s | 49.698s | 60.294→57.710s | 两轮通过 |
| 200/200，parent→child | 56.878s | 55.756s | 64.670→63.045s | 两轮通过 |

第二工位3857拍trajectory JSON字节完全相同、sim与hold相同；两工位剔除全部hold后，非等待阶段拍数仍相同，controller分别少2.272/1.430s。完整原抓放、释放脱离、回位与全部安全/自由物体判据四轮通过。该表是相邻成对观察；全差不能单独归因一个约7us的组件，也不与前轮收益相加。

54边界/2816真实输出及64相关回归同值，原workspace重入/生命周期5项在开启配置下通过，默认指针变更39项入口检查通过。P95 nominal23.573ms、200/20026.277ms，完整50Hz仍未过。CLI32叶值复用虽等值但局部成本不足，未应用生产。完整来源/失败/分段时钟及复跑在原计划F2y/F2z。
