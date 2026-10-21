# Progress

## Current
2026-10-21 F2c两轮真实CLI生成与物理反馈接续已完成，本轮6/6原裁判通过。第二候选原高度仅观察到局部脱离缩时，默认基线保持。四个后续worker已全部结束并归还资源；无新增仿真待运行。

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

F2c窗口释放前历史状态（已由下文实跑结果更新）：候选AST/实际load_route_policy读回完成，CodeBuddy receipt报告requested/reported模型均为deepseek-v4.1-flash、foreground_print=true、tools_disabled=true；这些只证明生成与加载，不是物理成绩。无人机owner明确暂不释放新15分钟批次，后已将两个短回合排在当前计时检查之后；截至本条尚无明确释放消息，因此物理运行数0，下一轮CLI反馈生成也未调用。执行owner仍为本SO101原对话；原线程收到资源释放消息即可用prepared.json两条argv接续，不需重开线程、重跑F2b或新建调度平台。基线固定，出现小增益再补相应布局baseline→candidate交替，之后才把真实结果送前台CLI生成下一候选并评测。


## F2c 第一轮真实CLI候选结果（2026-10-21）

无人机owner明确释放仅两个MuJoCo回合窗口后，执行series `5753e421-34d6-4378-9c62-87165b67aa99`；两个worker与串行runner在07:53:58 UTC全部结束，已立即回告并归还窗口。没有扩展物理批次、运行Gazebo/ROS/build或重启5187/5192。

候选为根实际生成的 `~/.cache/ros2-factory/codebuddy-so101-20261021/transport_057_full_separation.py`，原文不改。请求/报告模型名均为deepseek-v4.1-flash；实际load路径、entrypoint与worker偏好均匹配57mm/13/continuation。生成receipt只作来源，不代替原物理裁判。

| 场景 | run_id | 原裁判 | sim秒 | wall秒 | 实际运输/脱离mm |
|---|---|---|---:|---:|---|
| baseline-0mm | 49d4aa69-2972-4dda-a1b0-3c82975cb162 | pass/succeeded | 74.78 | 66.265 | 57 / 37 |
| raised-10mm | 9821a567-7e3b-4867-9955-4b68b4dc55b9 | pass/succeeded | 74.34 | 66.860 | 67 / 28.462 |

只读独立回读原report和trajectory：两轮grasp/place/controller_done=true、safety_stop=false、obstacle_contact_steps=0；free_object=true、weld=0、mocap=0，末态蓝盘底接触true、双指力0、物体速度约1e-11m/s。释放审计通过，最大漂移0.297798mm、脱离后最大力0.0155083N，回位最大误差0.000102589rad。各自与F2b baseline的初态qpos、contact/planning XML、裁判路径和释放阈值相同；未重新评分。

不选优：nominal总sim与基线相同，规划运输28.4834s反比基线28.4265s长；raised总sim只少0.10s，实际运输67mm、脱离28.462mm及运输规划28.3197s均与基线相同，尚无几何收益证据。必要交替baseline→candidate复验保留到下一窗口，不在已归还窗口追加。之后的CLI提示必须携带这一不确定性，不拿单次差值当成稳定改善。

产物位于 `experiments/colab-twin/output/cli-route-rounds-20261021/5753e421-34d6-4378-9c62-87165b67aa99/`：prepared.json、round1-results.json、round1-independent-checks.json、两轮原日志、evaluation及UUID完整轨迹/场景/报告/录像。全部受Git忽略。只读脚本首次将planning XML误写为planning-workcell.xml，实际grasp-planning.xml；修正后比较相同，无重跑/改判。

当前接续owner仍为本SO101原对话：以该真实反馈进行同CodeBuddy前台调用生成第二候选，保留私有prompt/stdout/stderr/receipt；实际仿真及raised交替复验等待无人机明确新窗口。无训练、云GPU、实体或默认策略变更。Knowledge：already_covered，沿用现有物理结果与命令完成分离原则。


F2c第二候选已实际生成（前台CodeBuddy一次，28.392s、CLI success、is_error=false）：`~/.cache/ros2-factory/codebuddy-so101-20261021/round2/candidate.py`，原文字面量57mm/10点/continuation。相对首CLI候选只改13→10。请求及事件报告模型名为deepseek-v4.1-flash，AST仅纯函数字面量、原RoutePolicy及load_route_policy实际读回通过。prompt包含首轮真实metrics/worker路线/单次噪声边界；原prompt、stdout.json、stderr.txt、parsed-result.json、receipt.json均在该私有目录，不入Git。

生成说明不作为事实：模型将nominal实际57mm误写60mm，附带clearance与因果推断亦未经证实，receipt.review_notes已标明；未改写候选源码或原生成结果。首轮解析错误因CLI JSON顶层为事件list而非dict，已从同一次保存的末尾result事件重解析，未再次调用CLI。候选2物理status仍not_run。

后续4条精确argv已保存series下followup-prepared.json：raised baseline→candidate1两轮，再candidate2两盘高各一轮。无人机已接收下一窗口协调请求；本轮生成期间仅文本CLI，无本机仿真/训练/build。等待明确释放再启动，仍不按小差值选优。


F2c补充只读阶段计时：nominal transport +0.04s、hold -0.04s，其他段相同；raised仅hold -0.10s，运输/脱离/回位均无时长差。round1-stage-timing.json保留分段计数，支持暂不把微小总时长差归因路线。两个实际候选源码原文副本保存在同一忽略series的candidate1-source.py、candidate2-source.py，不设置内容锁，也不替代原实际加载路径。

本轮文档交付e277c0d1615b1d5681b6b7604fb2103463f68357已推送并经REST读回一致；源码、默认路线及原评分未变。canonical只同步三份所属计划与忽略series，逐文件确认匹配前次交付后才覆盖，无冲突。


资源接续：无人机owner最新明确暂不释放，箱顶取消网页runner仍active且可能接飞行；本对话遵守零新增MuJoCo。后续四回合仍not_run，pending原因是共享仿真资源在途，非物理失败或训练预算。owner仍为SO101本原对话；无人机在cancel实际terminal且进入纯分析后会明确释放2+2或整4回合。收到后最短入口：`python3 /home/muqiao/.cache/ros2-factory/codebuddy-so101-20261021/run_followup.py --batch repeat`，完成即回告；另获第二窗口后以`--batch round2`运行候选2。若明确整4窗口，可一次`--batch all`。不要因看见terminal或服务空闲而自行执行。运行后回读新evaluation/原report/trajectory及实际路线，再写结果和交付；不把已生成候选称为实际评测完成。


## F2c 当前交付：反馈生成与第二轮实际评测完成

无人机owner后来明确释放整4回合约5分钟窗口，已按授权原序列串行完成，前述pending状态仅是释放前历史。runner始于08:12:54 UTC、08:17:06 UTC结束；四个subprocess全部exit0，终态均succeeded/pass。已立即逐run回告无人机owner归还资源，无追加批次，无5187/5192重启、Gazebo、ROS、build、实体、训练或云GPU。

| 场景/候选 | run_id | sim秒 | wall秒 | 实际运输/脱离mm |
|---|---|---:|---:|---|
| raised baseline交替复验 | 674a0f41-f14a-4441-a8ca-fb21dcad8f75 | 74.38 | 75.102 | 67 / 28.462 |
| raised CLI候选1交替复验 | 2d136324-66b8-408d-82cb-6e2a07f9706d | 74.30 | 65.745 | 67 / 28.462 |
| nominal CLI候选2 | 42774180-48d9-49aa-b571-4101425773a0 | 74.50 | 53.396 | 57 / 28.462 |
| raised CLI候选2 | 9e05c80c-72f3-49a8-9210-3d69e845cd2e | 74.32 | 53.524 | 67 / 28.462 |

四轮源码固定于1e9d043364a413045ade8819126db38f1a5e15ef，运行时Git干净；相对75c67ad只有所属文档变化，原控制器/RoutePolicy/evaluate_station/learning_env无diff。candidate1/2的实际loaded_path、entrypoint与返回偏好对应真实cache文件，原文副本保留在series。候选2separation reason实际为policy_waypoint_prefix，请求/实际28.461538mm；不只是修改标签。

只读回读原report、trajectory、XML：四轮原passed、grasp/place/controller_done=true，无安全停机、无障碍接触；free_object=true、weld=mocap=0。末态蓝盘底接触true、双指力0、物体速度约1e-11m/s，最大回位误差0.000102213rad。释放原审计全部通过，最大XY漂移0.297878mm、最大脱离后再接触力0.0155267N。对照初态qpos、contact/planning XML、原裁判路径和释放阈值均相同，未另造裁判或放宽阈值。

区分结果：raised交替baseline74.38→候选1 74.30的-0.08s全部在hold，实际路线与规划时长不变；旧baseline74.44→新baseline74.38也有-0.06s hold变化。候选2nominal相对候选1：separate -0.32s、hold +0.04s、其他段相同，总-0.28s，运输规划只差0.00000029s。相对baseline则transport +0.04s、separate -0.32s，总-0.28s。候选2raised相对候选1复验反而+0.02s，仅hold变化。该局部动作缩短值得另行成对复验，不足以宣布稳定全程提速或选优；默认baseline不变。53s wall不归因模型/路线加速。

当前闭环范围已完成：首CLI候选两盘高2轮、raised交替基线/候选1共2轮、反馈生成的第二候选两盘高2轮，本轮6/6通过。连同先前手写F2b的4轮是独立批次，不冒充20+20或泛化通过。没有第三轮CLI调用或持续后台Agent。

证据仍在同series：followup-all-results.json、followup-independent-checks.json、四份原日志及各UUID完整evaluation/report/trajectory/XML/录像；所有物理结果和源码副本均Git忽略，CLI原始输出/receipt仅私有cache。nominal候选2录像ffprobe可读：H.264、640×480、466帧、74.56s；未以视频元数据替代物理判据。后续仅如需正式选优，再协调新窗口进行nominal baseline→候选2交替复验；本轮无该额外授权窗口内任务遗留。

交付记录：前一次1e9d043推送45s超时，远端当时仍e277c0d；未将本地提交称为已交付。现合并本轮实际结果进行提交/推送与REST独立读回。canonical保留其他跟随器/设备/历史未跟踪工作，只有本计划三文件与忽略series同步。Knowledge：already_covered，现有ROS2/FishBot物理结果核验原则已覆盖，无新增共享知识或个人memory写入。
