# Progress

## Current
2026-10-21 F2首片已交付。F2b最小路线策略插槽与四轮成对物理验证已完成（4/4通过），结果和接续见下文；候选未证明稳定收益，默认基线保持。

## Done
- 新增place世界Z作为非负蓝盘底座高度。真实/规划XML、实体底座、编辑预览、控制器、异步快照与评分已贯通，默认0兼容。
- 原评分从真实盘面计算静稳中心，只平移参考高度；原2mm静稳容差、25mm抬升、1s、双指接触、1mm碰撞余量与释放再接触/漂移判据不变。
- 根整合回归113 tests、116 subtests通过。UI Jest27、ESLint及生产构建通过。
- 10mm场景run `6e537ac9-2ff0-47c9-a6e3-6a70cd8b08a9` 原裁判通过：74.36sim / 91.065wall；实际抬升48.294mm，持物31.64s，静稳12.98s。最终方块中心(0.2387313,0.1390601,0.0199607)m，实际蓝盘顶面12mm；末态双指力0、盘底接触true，回位最大误差0.000102213rad。
- 释放审计通过：最大XY漂移0.297838mm，脱离后最大接触力0.0155403N，真实free object、weld=0、mocap=0。没有脚本搬动物体。
- 负高度run `434484fd-d92a-4545-b828-fe823d83fbcd` 在物理前明确拒绝，state=failed、verdict=unscored、passed=false；未回退原场景。
- `evaluate_station.py`复用原执行器，输出独立run目录及机器可读evaluation；取消/缺报告/原失败不会计为pass。来源记录实际路径、Git状态和加载模块，不新增内容锁。
- 可导入JSON位于 `experiments/colab-twin/scenarios/factory-loading/`，包含原高度、10mm和负高度。

- 默认0高度通过隔离工作台API重新运行，task `46bbbf49-4f0f-4443-b0ed-59e76fd9f384`：74.76sim / 66.778wall，实际抬升41.272mm，持物31.40s，静稳7.52s。最终物块中心Z=9.960725mm、实际盘顶2mm，回位最大误差0.000102589rad，释放XY漂移0.265794mm，脱离后接触力0。原succeeded和原report.passed一致。

## Evidence
SO101忽略目录 `experiments/colab-twin/output/factory-loading-20261021/` 保留上述evaluation、原报告、轨迹、XML和录像。UI独立树 `/home/muqiao/worktrees/fishbot-f2-workcell-20261021` 的 `apps/fishbot-control-station/workbench-review-tests/output/station-workcell-height/` 保存10项无运动检查与截图。15mm仅编辑预览通过，不冒充物理回合通过。首轮QA定位器失败保留在旁边 `station-workcell-height-selector-failure/`；首次构建局部依赖缺失日志保留/tmp，补全原安装后通过，未改上游源码/版本。

## Remaining
本轮F2无剩余实施项。共享无人机树保持原owner；本轮未运行20+20、训练、云GPU或实体。

## Next
用户在5192复制/导入并编辑工位；后续新布局逐任务验证，不用此单回合推断批次鲁棒性。

## Delivery
- SO101实现提交 `15484b3`，分支 `codex/colab-twin-20261001`；工作台实现提交 `8005ea7`，分支 `codex/f2-workcell-20261021`。后续文档提交记录验收与推送阻碍。
- GitHub API曾确认有效身份qiaoqiao2521 / 238822818，两个既有公开仓库身份一致。随后SO101推送连接github.com:443超时，UI推送无法取得密码；同命令环境的gh auth status返回账户登录超时，gh auth git-credential无法取得凭据，未修改凭据/全局网络/账号配置。该阻碍已在2026-10-21后续quickstart交付时解除：官方CLI活动账号凭据可用，命令级helper调用同一隔离配置的gh auth token后完成推送；未保存或输出Token、未修改全局账号配置。
- 本地入口 `http://127.0.0.1:5192/so101-station` HTTP200，隔离服务PID1927886；SO101_ROOT指向本交付树，独立任务目录在工作台workbench-tools/output/f2-height-20261021/tasks。普通5186当前未监听，未重启其他owner的服务。
- UI最终专用10项、原草稿13项均通过。桌面和390×844手机各13个STL加载；现有baseline原station逐字段保持。最终专用证据在 `station-workcell-height-baseline-preserved/`，原草稿在 `station-task-drafts-f2/`；首轮手机全页截图超时保留，视口截图修正后通过。

- 远端REST独立读回：SO101 `be48313b58cf6633346e388a64441a58261efa76`包含实现15484b3与两次交付记录；UI远端 `636d52b1863cd622c46ef979a57d02c506e91b70` 包含8005ea7及后续单回合QA选项。旧推送失败保留为历史，当前交付已完成。

## Preserved Work
canonical `/home/muqiao/dev/ros2/projects/so101` 的跟随器、设备配置、记录及历史未跟踪文件保持原位。F2覆盖前逐文件比较交付基线15fa5bf，18个既有目标文件与基线一致；已限定同步26个本轮文件及忽略的物理证据，无冲突覆盖。其余有效遗留归原跟随器/迁移工作，由根Codex接续，最短入口为该树git status与原迁移计划；用户记录/配置不入本次提交。

## Knowledge
already_covered：沿用Wiki ROS2与FishBot第20节，动作完成、真实接触和最终裁判分开核对；项目状态留此，不并发写研究总文件或知识库。

## F2b 接续
2026-10-21厂区根独立回读首片后，授权最小路线策略插槽及原0mm/10mm成对实际评测。当前接口实施中，未启动新物理回合；共享5192/5187及在途无人机核心保持原owner，已协调约8分钟本地MuJoCo串行窗口。

F2b接口首轮定向回归暴露既有SweepBinding只接收标量/tuple，新增dataclass直接进入快照被拒绝；已复现并仅在控制器三处快照转换成原有标量tuple，不修改原守卫或阈值。初次批量补丁有一个过时上下文导致原子拒绝，未部分写入，已纠正。

F2b接口定向91 tests / 104 subtests通过。路线配置只改候选顺序、原路点前缀和现有IK初值；scorer、模型、grasp_episode、placement、run_visual_grasp无diff。STATION_EXECUTOR旧“修改Z拒绝”已改为非负底座高度语义。

## F2b 四轮结果（2026-10-21）

实现固定于 `05142f276ab46cc4d70d7b10ece7fd354760b9a3`。原0mm/抬高10mm，各baseline与shorter_route一轮，四轮全部原裁判通过。

| 场景 | 策略 | sim秒 | wall秒 | 实际运输高mm | 实际脱离mm | run_id |
|---|---|---:|---:|---:|---:|---|
| baseline-0mm | baseline | 74.78 | 69.060 | 60.000 | 37.000 | 65a76c62-820f-4f4e-a2b2-4c6cfc3bf6db |
| baseline-0mm | shorter_route | 74.58 | 66.440 | 51.000 | 28.462 | 9370d0c9-b119-4483-bf75-99fe066b6025 |
| raised-10mm | baseline | 74.44 | 65.965 | 67.000 | 28.462 | 7f90943c-4232-4979-afd4-c74df59cc641 |
| raised-10mm | shorter_route | 74.40 | 75.093 | 61.000 | 28.462 | 6c745715-bffb-4e36-9031-817c7be05ad3 |

结论：候选实际执行了不同路线，原高度总仿真时间少0.20s，高盘少0.04s；但运输motion_and_arrival从28.4265/28.3197s增至28.6111/28.4088s，候选高盘wall反而增加9.128s。没有足够的稳定收益证据，默认仍为baseline，不自动晋级。每布局每策略仅一轮，不能解释为统计鲁棒性或归因到某一个参数。

独立读回：两组的初态qpos、实际contact XML、planning XML、裁判来源及释放阈值逐项相同。四轮free_object=true、weld=0、mocap=0，实际盘底接触true、末态双指力0。最大释放XY漂移0.297998mm，最大脱离后再接触力0.015559N；原2mm/0.02N判据保持。最大回位误差0.000102589rad。

候选加载证据：每轮candidate.path/loaded_path/entrypoint_path指向实际baseline.py或shorter_route.py，commit均为上述实现提交；controller另有真实loaded_path。worker的policy_execution记录运输高度、原验证结果、脱离请求与实际目标，证明不是仅改变标签。IK neutral选择已做接口单测；本轮两个真实策略均使用continuation，未宣称neutral实测更优。

原始产物：`experiments/colab-twin/output/route-policy-pair-20261021/65909715-aa81-46ff-8617-7fc14d2db2ed`。comparison.json含四轮命令、退出码、原裁判、metrics、候选引用和worker实际选择；independent-checks.json为只读复核，不另造评分。每个子目录保存evaluation、原report、trajectory、实际/规划XML和视频；均被Git忽略。

最短调用见[执行器说明](../../experiments/colab-twin/STATION_EXECUTOR.md)：给evaluate_station.py增加 `--candidate experiments/colab-twin/route_strategies/shorter_route.py`，再以station选择原0mm或10mm。省略candidate会实际执行baseline.py；无效候选明确failed/unscored，不回退。

范围：91 tests、104 subtests通过；本轮没有修改learning_env、placement、grasp_workcell、grasp_episode、run_visual_grasp或模型/场景文件。STATION_EXECUTOR残留“修改Z拒绝”已局部修正。四轮源代码一致；没有恢复50Hz、长扫掠、训练、Gazebo、实体或云GPU。5192/5187保持原服务，已结束本轮全部MuJoCo子进程。

只读复核首次把XML误定位到episode根目录；实际在episode/scene，修正脚本后两组几何逐字节相同。未重跑或重判原物理回合。

F2c接续：厂区根已独立读到本轮四个产物，暂不按0.20/0.04s选优。根负责CodeBuddy前台print生成新候选（工具关闭、私有cache）；本对话当前仅完成F2b，不把手写候选称为CLI生成。新文件精确路径到位后再审阅、协调窗口和跑两种盘高，不重复本轮四例。

F2c输入已到位：厂区根实际CodeBuddy候选 `/home/muqiao/.cache/ros2-factory/codebuddy-so101-20261021/transport_057_full_separation.py`，receipt.json在同目录。根给出的工具禁用/前台调用由receipt追溯。本对话独立读回AST，仅有route_preferences函数及字面量返回：57mm偏好、13点、continuation；未改写该私有候选。CodeBuddy当前CLI2.168.2。计划先两盘高各候选一轮；若比相应基线小幅减少，则补该布局的baseline→候选交替复跑，不凭单次小差异选优；随后将物理结果送同CLI生成下一份独立候选并评测。当前等待新的本地仿真窗口，不启动Gazebo/云GPU。

F2b推送尝试在45s网络等待后超时，REST仍指向19c17fe，最新本地结果提交cd6080a尚待重试；未把本地提交称远端完成。原14个独占文件与证据已无冲突同步canonical。

F2b后续推送在命令级HTTP/1.1重试后成功（未修改全局网络），实现05142f2与结果cd6080a已交付；原45s失败记录保留，不将协议切换解释为已证明的网络根因。
F2c窗口：无人机owner明确当前高墙构建/组件/实飞不可并发，暂不启动新的MuJoCo批次；收到明确释放后接续。已准备两条准确命令于忽略目录 `experiments/colab-twin/output/cli-route-rounds-20261021/5753e421-34d6-4378-9c62-87165b67aa99/prepared.json`。首次prepared路径误放experiments/output，已整体移入受忽略目录并校正argv，未提交或执行旧路径。
