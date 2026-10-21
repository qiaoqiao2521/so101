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

[第二放置工位输入](scenarios/factory-loading/layout-place-200-200-0mm.json)把蓝盘中心改为(0.20,0.20)m、高度0，与220/170工位共用原程序、方块、障碍和裁判。2026-10-22仅完成原静态parser及baseline/原CLI候选2真实loader检查，当前版本的可达性、物理结果和收益未测；未来比较须让两策略读取同一fixture。

### 最小路线候选

`--candidate` 接受本地Python源码，实际执行其 `route_preferences()`。路线偏好包括：`transport_preference_m`重排原候选运输高度，`separation_steps`选择原13个上升路点的前缀，`ik_seed`选择原IK的延续初值或neutral初值。基线默认值为None、13、continuation；`route_strategies/shorter_route.py`选择51mm优先、前10点及continuation。所有碰撞采样、1mm净距、释放审计、时间判据和最终物理裁判均由原实现执行。

可选`transport_candidates`默认为1，保留首条完整认证可行路线。设为2或3时，沿原高度顺序寻找前N条完整可行路线，按原`motion_duration`加各段0.6s到达守卫取最短；等值保留原顺序。拒绝的高度不计入N，原高度回退列表保留；可行数量不足N时使用已认证者，无可行路线或未知错误仍明确失败。原90s/14s预算、异步快照和物理检查不变。

手写接口示例`route_strategies/shortest_two_routes.py`只设`transport_candidates=2`，其余均默认。该选项在2026-10-21独立XY的baseline/shortest-two两个完整物理回合均通过，但都选择60mm路线；多搜一条使该次hold增加0.70sim秒，默认仍为1，不将其当作提速成果。每个尝试记录认证墙钟、原路线时长及selected，`route_search`记录总搜索墙钟与实际认证数量并透传evaluation。原worker等待/墙钟照常包含额外规划成本；搜索时间与worker耗时重叠，不应重复相加，也不从任务总耗时中扣除。report.hold_duration_s是物理持物累计时间，hold阶段等待从trajectory分段读取。候选费用在冻结worker起态比较；原入场桥接仍会重新校验和计时，因此attempt费用不必等于最终motion_and_arrival_s。

```bash
~/.cache/so101-graspgenx/upstream/.venv/bin/python \
  experiments/colab-twin/evaluate_station.py \
  --station experiments/colab-twin/scenarios/factory-loading/raised-10mm.json \
  --candidate experiments/colab-twin/route_strategies/shorter_route.py \
  --output-dir experiments/colab-twin/output/route-comparison/raised-shorter
```

省略candidate即实际加载 `route_strategies/baseline.py`。`evaluation.json`的candidate记录本次加载路径、入口源码路径、Git引用和实际返回的偏好；controller另记原执行器来源。`policy_execution`从本轮planning/report提取worker实际采用的运输高度与脱离目标。无效候选明确failed/unscored，不回退基线。正常候选的偏好经不可变快照传给原worker，不向它提供裁判或执行中的物体真值。

候选为本地审阅过的源码。比较时只修改候选文件，不改 `learning_env.py`、模型、场景、释放/碰撞阈值或评分。该小接口用于路线选择，不提供通用插件、代码隔离或训练框架。

工作台通过现有独立 FishBot 仓库的 `apps/fishbot-control-station/so101-runtime.cjs` 调用本入口，Web 依赖与机器人依赖各自安装。工作台地址 http://127.0.0.1:5186/so101-station ，右侧显示本次任务的原生实时三维，本次录像与原报告位于任务栏；原历史录像使用独立入口。

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
