# Progress

## Current
2026-10-22 F2f第二工位200/200/0mm的baseline与旧CLI2原物理2/2通过，实际路线相同，未性能晋级；owned清理后窗口已归还。按根要求仅静态准备prefer_054单变量提案及原评测入口，该新提案未运行/未构造模型，无新模型调用。

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

当前闭环范围已完成：首CLI候选两盘高2轮、raised交替基线/候选1共2轮、反馈生成的第二候选两盘高2轮，本轮6/6通过。连同先前手写F2b的4轮是独立批次，不冒充20+20或泛化通过。截至这六回合结束尚未调用第三轮CLI；后续文本反馈见下文，未运行持续后台Agent。

证据仍在同series：followup-all-results.json、followup-independent-checks.json、四份原日志及各UUID完整evaluation/report/trajectory/XML/录像；所有物理结果和源码副本均Git忽略，CLI原始输出/receipt仅私有cache。nominal候选2录像ffprobe可读：H.264、640×480、466帧、74.56s；未以视频元数据替代物理判据。后续仅如需正式选优，再协调新窗口进行nominal baseline→候选2交替复验；本轮无该额外授权窗口内任务遗留。

交付记录：前一次1e9d043推送45s超时，远端当时仍e277c0d；未将本地提交称为已交付。现合并本轮实际结果进行提交/推送与REST独立读回。canonical保留其他跟随器/设备/历史未跟踪工作，只有本计划三文件与忽略series同步。Knowledge：already_covered，现有ROS2/FishBot物理结果核验原则已覆盖，无新增共享知识或个人memory写入。


## F2c 第三轮文本反馈与暂缓理由

厂区根独立读回上述六份evaluation/原report和CLI事件后，要求继续把第二轮结果、分段耗时及错误说明送回同一前台CLI，且不要重跑六例。已完成该文本调用一次（41.666s，CLI success/is_error=false，请求与事件报告模型deepseek-v4.1-flash）。私有`~/.cache/ros2-factory/codebuddy-so101-20261021/round3/`保留prompt/stdout/stderr/parsed-result/receipt，实际生成原文字面量候选57mm/9点/continuation。AST纯函数与原loader读回通过，源码原文副本在series/candidate3-source.py。

本owner决定defer_not_promoted：候选3 physical_status=not_run，不追加MuJoCo、无新的资源窗口申请。相对候选2只少一个2.846mm的脱离位移点，模型自己也未给出可信全程收益；继续追逐sub-0.1s总时间缺乏价值，先做独立布局复核及更大运动段的可测比较。不把文本模型decision当成物理拒绝或成功。

仍需纠错：候选3说明将report.hold_duration_s约31.6s（物理持物累计时长）误当阶段hold等待。实际候选2nominal approach16.58s/transport25.92s/hold2.88s，raised16.58/25.76/2.86s。说明中的28.4834s规划运输只适用于nominal，raised是28.3197s；竖直IK上限也仅在当前姿态/布局观察到，不能推广。原生成文字保留，receipt.review_notes及series/round3-owner-decision.json明确纠正，未据此改控制器。

三参数的具体边界：运输偏好仅重排既有离散高度，未改变五段走廊；脱离仅截取原路点前缀；IK参数仅换初值，不能直接优化关节路径或接近段。只读源码确认_compute_transport在首条通过完整认证的高度break，然后才统计motion_and_arrival_s（visual_grasp_controller.py:677–729）。因此下一项最小可扩展策略可复用现有_transport_at_height完整认证和motion_duration，对少量已有可行高度按原规划时长排序；默认仍首个可行，保持原worker快照、完成预算及全程物理检查。此处只列待验证方向，尚未改接口或实现；额外认证耗时必须计入规划等待，不能把优化计算隐藏。

后续先由原owner固定独立XY/障碍布局变体，再将相同fixture用于baseline/candidate，不允许候选改场景/裁判。0/10mm仅同布局高度变化，不宣称跨布局提速。当前可交付仍是两轮生成候选的6次原物理通过与反馈链；第三候选仅保留为未测试提案，默认baseline不变。


## F2d 独立XY输入已准备，物理未运行

根认可第三候选暂缓，接续要求优先独立变体实际复核；路线成本排序扩展继续只留计划。已新增`experiments/colab-twin/scenarios/factory-loading/layout-place-220-170-0mm.json`，由本owner固定，baseline/candidate2共享此输入。相对baseline-0mm只改place.position=(0.22,0.17,0)m及名称/说明，其他节点逐项相同、八步程序相同；release/clear经原父坐标系解析为(0.22,0.17,0.03)/(0.22,0.17,0.10)m。方块仍(0.24,-0.13,0.01)，原内置障碍及盘尺寸保持；没有增加或移除障碍。

选择依据是STATION_EXECUTOR已有2026-10-20同目标原执行通过记录，优先复用已知可达范围。但旧回合不是此源码/候选的当前证明，也不是完全未见目标；本次只称F2候选的独立XY复核，0/10mm旧例不叫跨布局泛化。

原validate_station静态通过，实际load_route_policy读回baseline(None/13/continuation)、候选2(57mm/10/continuation)及真实cache入口。Python模块检查mujoco_imported=false；没有模型编译、物理推进、浏览器QA、构建或服务重启。

准确argv及静态解析保存在忽略series `experiments/colab-twin/output/independent-layout-20261021/92c6ff57-e579-4355-bdf4-069d5fc05100/prepared.json`，源候选原文副本candidate2-source.py在同目录。两条命令共用同一station，分别给baseline/candidate2独立输出根；候选不修改fixture或评分。当前status=static_pass_physical_not_run，原执行器仍创建每次独立UUID。文件允许二改，不设置内容哈希锁。

待明确窗口后，从SO101交付根按以下顺序运行，MUJOCO_GL=egl：

```bash
MUJOCO_GL=egl /home/muqiao/.cache/so101-graspgenx/upstream/.venv/bin/python experiments/colab-twin/evaluate_station.py --station experiments/colab-twin/scenarios/factory-loading/layout-place-220-170-0mm.json --candidate experiments/colab-twin/route_strategies/baseline.py --output-dir experiments/colab-twin/output/independent-layout-20261021/92c6ff57-e579-4355-bdf4-069d5fc05100/baseline
MUJOCO_GL=egl /home/muqiao/.cache/so101-graspgenx/upstream/.venv/bin/python experiments/colab-twin/evaluate_station.py --station experiments/colab-twin/scenarios/factory-loading/layout-place-220-170-0mm.json --candidate /home/muqiao/.cache/ros2-factory/codebuddy-so101-20261021/round2/candidate.py --output-dir experiments/colab-twin/output/independent-layout-20261021/92c6ff57-e579-4355-bdf4-069d5fc05100/candidate2
```

共享窗口当前仍归无人机规划构建/ground对照，FishBot已申请下一窗口先做occupied direct（原1000墙秒上限），via另约。本对话不抢占、不因看到空闲或其他任务终态而自行启动；待后续明确释放再做上面两个新回合，原六例不重跑。接续owner为本SO101原对话。结果需回读原report、真实场景和实际路线，保留失败，不按小差值晋级。Knowledge：already_covered，仍沿用原物理结果与消息/退出码分离原则。


## F2d 独立XY实际2/2通过，窗口已归还

无人机明确释放后，按原prepared两条argv在干净ef94271源码串行运行：baseline `2a5ef58f-0c0b-4cd1-b6ae-5f5dbec9e9af` succeeded/pass，75.26sim/97.781wall；候选2 `5831a62c-5435-4486-a65e-2e03627455ad` succeeded/pass，75.04sim/95.763wall。目标均(0.22,0.17)m，原0高度、方块/障碍/程序/评分不变。runner于08:55:56–08:59:12 UTC完成，两个subprocess均exit0，观测owned活动进程剩余=[]。已立即同时回告无人机与研究协调根归还，未扩批次或重启5187/5192，未跑ROS/Gz/build/浏览器QA。

本owner独立回读原报告/轨迹：两轮grasp/place/controller_done/release_audit通过，无安全停机/障碍接触；free_object=true、weld=mocap=0，末态盘底接触true、双指力0。最大释放XY漂移0.269350mm、脱离后接触力0，回位最大误差0.000101197rad。同初态qpos、contact/planning XML、裁判引用及释放阈值；未重新评分。

实际路线变化：运输60→57mm，规划motion_and_arrival 28.998944→29.020510s（反增0.021567s）；脱离34.153846→28.461538mm。分段差：transport+0.04、lower-0.04、separate-0.16、hold-0.06，其余相同，净-0.22sim。单次局部缩时不晋级，默认仍baseline；这是独立XY任务复核，不代表跨布局泛化。

证据在原series `experiments/colab-twin/output/independent-layout-20261021/92c6ff57-e579-4355-bdf4-069d5fc05100/`：pair-results.json含准确argv/实际PID/终态/owned清理，independent-checks.json含原报告与几何/时序对照；两个UUID保留原report/evaluation/trajectory/XML/录像。根亦已独立核对，原失败无覆盖，本轮没有新增物理失败。

F2e接续由根明确授权先做纯软件：复用完整路线认证和原motion_duration，默认首个可行，显式可比较少量可行高度。保持快照/回退/预算/原物理判据，额外认证耗时记录在原worker等待和总墙钟中。暂不模型编译/重native/ROS/build/浏览器QA；新的物理A/B需另获窗口。


## F2e 软件阶段记录（当时物理待验）

新增RoutePolicy.transport_candidates，默认1保留首条完整认证可行路线；显式2/3时沿原高度顺序收集前N条完整可行路线，按原motion_duration加每段0.6s到达守卫稳定取最短。没有替换_transport_at_height、IK、完整五段认证或物理裁判。原高度顺序/回退保留；仅完整通过者入选，等值保持顺序，可行者不足N则保留已认证结果，无可行者原失败，未知错误/取消仍向外传播。

原快照与binding已经通过preferences().items()携带新字段，不改worker或SweepBinding。原90s/14s预算、到达/释放/回位阈值保持。transport计划新增route_search（实际认证数量/请求数量/总墙钟）和各attempt认证耗时/原规划时长/selected，evaluate_station只做诊断透传；原worker等待与总墙钟包含额外搜索，motion_and_arrival不扣除搜索时间，两个墙钟指标不可重复相加。额外认证可能消耗既有预算，物理A/B可失败，不作实时或提速承诺。

手写示例`experiments/colab-twin/route_strategies/shortest_two_routes.py`仅返回transport_candidates=2，其余默认，用于后续单变量A/B；没有将手写示例冒充CLI候选。旧CLI1/2/3未改写，缺省新字段均为1。

轻量验证：`test_route_selection.py`新增11项合成路径/桩认证合同，阻止MjModel.from_xml_path/from_xml_string与MjData构造，覆盖默认不多搜、较短选择、不完整认证不入选、回退不足、等值稳定、原失败/取消传播、目标释放端点仍必需、实际计时、源加载/快照绑定及evaluation失败不变。连同原route_policy/transport_worker/evaluate_station纯软件测试，最终42 tests、62 subtests全部通过（pytest 0.75s）。未构造MuJoCo模型或推进物理，无ROS/Gz/build/浏览器QA。首轮新fixture用了旧同步binding，先缺q6、补q6后缺旧同步状态；已改为本次实际异步binding后通过，未改生产守卫。日志`/tmp/f2e-route-contracts.log`及忽略series副本保留。

未来成对入口已准备于`experiments/colab-twin/output/route-selection-ab-20261021/9d8a71f1-d133-41a5-922e-b0957c261237/prepared.json`：同独立XY220/170 fixture，baseline→shortest-two两个argv，MUJOCO_GL=egl。仅stdlib原静态解析与真实load_route_policy读回（mujoco_imported=false），输出根尚未生成物理evaluation。该新选项原物理A/B仍not_run，需无人机另给明确窗口；本次归还窗口不得复用。后续无人机先native48/箱顶取消，再由原owner安排FishBot fixed-direct，不自动抢占。

限定交付包含上述3个源文件、手写示例、纯合同测试和原说明/计划；learning_env、模型、场景fixture、worker生命周期、SweepBinding及其他物理阈值无修改。F2d2/2是旧ef94271上的证据，不能拿它冒充新选择选项通过。Knowledge：already_covered，原物理验收/计时边界原则已覆盖，项目实现状态留本计划。


计量补充：候选费用以原冻结worker起态比较，既有入场桥接/重验证仍会重新计算最终motion_and_arrival_s；attempt中记录的是各认证候选的起态费用，不能与桥接后总值硬等同。该选择不是完整任务墙钟优化保证。原桥接、上下文拒绝、14s回位保留与90s预算代码未修改。


## F2e 新版本原物理A/B实际完成：功能通过，未获提速

在无人机明确释放、协调根确认的同一两回合窗口中，只运行原prepared两个argv。干净源码a089eae，两轮同XY220/170 fixture，原90s/14s预算、模型/裁判/阈值不变。runner于09:29:48–09:31:38 UTC完成，两个subprocess均exit0，已观测owned活动进程剩余=[]，立即同时回告无人机与研究协调根归还，无扩批次/旧例重跑、无5187/5192服务重启、无ROS/Gz/build/浏览器QA。

| 候选 | run_id | 原裁判 | sim秒 | 总wall秒 | 搜索wall秒 | worker wall秒 |
|---|---|---|---:|---:|---:|---:|
| baseline（认证1条） | be979351-8463-4156-a96e-82fcd9901d6a | succeeded/pass | 75.20 | 53.539450 | 1.110915 | 1.156478 |
| 手写shortest-two（认证2条） | 4a730145-f108-412b-a1ae-d0fe3d388d64 | succeeded/pass | 75.90 | 54.801624 | 2.272846 | 2.312110 |

实际候选加载/entrypoint与偏好对应baseline.py（transport_candidates=1）和手写shortest_two_routes.py（2），不冒充CLI生成。baseline完整认证60mm；shortest-two完整认证60mm、57mm，原起态费用分别28.998936900/29.020503877s，正确选较短60mm，第二条selected=false。两轮最终桥接费用28.998943327/28.998948604s，微小差来自入场桥接，不是搜索费用漏记。两轮实际脱离均34.153846mm、同原IK回退理由。

独立原报告/trajectory读回：两轮passed/grasp/place/controller_done/release_audit=true，无安全停机/障碍接触；free_object=true、weld=mocap=0，末态盘底真实接触、双指力0，最大释放XY漂移0.269188mm、脱离后接触力0，回位最大误差0.000101077rad。原初态qpos、contact/planning XML、裁判引用及release阈值逐项相同，运行时Git干净；未重新评分。

额外计算实际没有隐藏：stage hold从2.88→3.58s，其他阶段逐项相同，净+0.70sim s；transport request→admission从0.76→1.46sim s。搜索+1.161931wall s、worker+1.155632wall s、整回合+1.262174wall s；这些指标重叠，不重复相加。原worker joined=true、cleanup_unconfirmed=false，任务/runner与已观测子进程都终态。report.hold_duration_s31.98/32.68s仍指持物累计，不当作等待阶段。

决定：功能和两条完整认证/选择/执行链已验证；该布局首可行已经更短，多搜没有路线收益，反增等待。默认transport_candidates=1保持，不晋级，不因测试通过宣称优化成功，也不为寻找胜利追加3路搜索或重跑旧八例。每策略一次观察，不推出其他布局必然无收益或全局泛化结论。

证据保存在原series `experiments/colab-twin/output/route-selection-ab-20261021/9d8a71f1-d133-41a5-922e-b0957c261237/`：pair-results.json含实际argv/PID/终态/owned检查，independent-checks.json含原报告/几何/阶段/worker审计，两个UUID保留evaluation、原report/trajectory/planning/XML/录像。协调根亦已独立读回，默认保留结论一致。物理完成后仅更新手写示例的过时docstring与文档，运行逻辑未再修改；无新物理失败被覆盖。

根接续要求仅一次同前台CodeBuddy DeepSeek文本反馈：将以上负收益、worker成本、新字段范围及持物/hold边界送回，允许明确无候选/转向；不得改裁判、制造较弱基线或追逐hold噪声。当前先完成本pair所属审计/提交推送，然后仅文本/静态准备，不追加物理/native/服务，下一窗口另约。Knowledge：already_covered，原物理/开销/消息边界原则已覆盖。


## F2e 一次负收益CLI反馈：无新候选，理由独立纠错

按根授权，在pair审计8ad596f提交推送、REST读回后，仅前台调用同CodeBuddy一次：请求/事件报告模型均deepseek-v4.1-flash，tools禁用、无session持久化，21.884509s，CLI success/is_error=false。真实反馈含两候选/两高度原费用、route_search、worker、request→admission、全部阶段和总sim/wall，并明确持物累计/hold阶段、费用/墙钟的不同。最终decision=no_candidate、source=null，因此未创建新候选源码、未调用任何新物理/native/服务。

原prompt/stdout/stderr/parsed-result/receipt仅保留私有`~/.cache/ros2-factory/codebuddy-so101-20261021/round4/`；series中的model-feedback-round4.json保存来源、原决定与本owner审计，均受Git忽略。接受当前pair不出新可执行候选、默认1保留，不把该文本结论称为全局最优或物理淘汰证明。

独立纠错已写receipt.owner_review_notes并保留原文：
- “没有更短脱离前缀”错误；1..13仍可选，先前独立XY prefix10已观察到更短separate阶段，34.154mm IK回退不消灭更低前缀。
- “neutral已由之前结果排除”无证据；此前物理候选都continuation，neutral只有接口合同。
- “四字段已无任何更优可能”过度外推；本pair只比较60/57mm，未覆盖其他高度/布局或IK分支。
- 模型建议附加箱体迫使不同高度走新detour，但现有_transport_at_height仍是固定五段XY走廊，只改变高度；130mm箱体可能把全部高度堵住，不会自动生成新绕行，未采用该布局建议。
- 不采纳其“baseline必须先成功否则不跑候选”的新前序门控；既有独立评测不新增这项锁。失败保留。
- 模型给的固定盈亏阈值混合sim/wall时间，且只来自一次观察，不作为准入；阶段采样时长相等不等于轨迹逐位相同，也不能称原规划浮点费用低于某个统一测量分辨率。

仅保留可证伪任务条件的范围说明：同一独立固定任务内，首个可行高度的关节路径费用需实质大于另一完整可行高度，并在实际原回合中覆盖附加认证等待。placeXY变化可改变IK姿态/路径曲率；历史已执行(.20,.20)m可作为未来原owner参考点，当前可达性/费用反转未测，不创建或运行新fixture，不故意削弱默认基线来制造胜利。当前五段固定走廊本身不提供新的XY绕行候选；额外加箱体不能当作这项能力已有。

收尾：本pair2/2原物理通过、负收益保留、默认1不变、一次文本反馈已审。本切片无新待运行回合/独立后台Agent/轮询服务，不为继续工厂强造候选。canonical只同步所属文件与忽略证据，其他跟随器/设备工作保留；Knowledge：already_covered，物理/计量/模型说法需独立核对原则沿用已有知识。


## F2f 第二放置工位：仅静态准备（2026-10-22）

按根限定范围复用原场景族，新增`experiments/colab-twin/scenarios/factory-loading/layout-place-200-200-0mm.json`。业务含义为同一取料任务投递到第二放置工位，与既有220/170工位比较只改变目标、名称和说明；未采用模型“加箱自动绕行”的错误建议，没有新增/移除/移动障碍。

| 条件 | 工位220/170 | 工位200/200 | 静态对照 |
|---|---|---|---|
| place世界位置m | (0.22,0.17,0) | (0.20,0.20,0) | 仅XY变化 |
| release编辑世界位置m | (0.22,0.17,0.03) | (0.20,0.20,0.03) | 同父坐标相对偏移 |
| clear编辑世界位置m | (0.22,0.17,0.10) | (0.20,0.20,0.10) | 同父坐标相对偏移 |
| cube世界位置m | (0.24,-0.13,0.01) | (0.24,-0.13,0.01) | 相同 |
| 底座高度/盘尺寸 | 原0mm/原尺寸 | 原0mm/原尺寸 | 相同 |
| 原障碍/附加障碍 | 原内置保留/无附加 | 原内置保留/无附加 | 相同 |
| 程序、其他节点与顺序 | 原八步、原全部其他节点 | 同左 | JSON逐项相同 |
| 裁判、物理模型和阈值 | 原实现 | 原实现 | 本轮未改源码或构造模型 |

原validate_station已接受新fixture，父坐标解析与上表一致。历史(0.20,0.20)m原执行记录只用于选择已有业务目标范围，不能证明当前版本、当前输入或候选可达/成功。上表release/clear为编辑模板世界坐标；实际指间释放/脱离仍由原执行器映射和安全规划，静态坐标不冒充物理认证。

真实load_route_policy读回baseline（None/13/continuation/1）与原CLI候选2（57mm/10/continuation/1）的实际路径/entrypoint，未改写候选2、未新模型调用，也没有把手写shortest-two或source=null的round4当作候选2。该成对比较是两种既有配置，并不单独隔离运输高度和脱离前缀的因果作用。

忽略series：`experiments/colab-twin/output/station-family-20261022/6c536ef6-e8a1-4846-82cb-c22d474726eb/`。prepared.json记录准确argv/环境/真实加载、condition-comparison.json记录相同与不同条件和节点逐项对照、cli-candidate2-source.py保留原文。mujoco_imported=false，状态static_pass_physical_not_run；没有实际evaluation/report或子进程任务，不会从旧回合读取成功。

未来获得明确范围/窗口后，交付根可复用原入口（本轮只保存、不执行）：

```bash
MUJOCO_GL=egl /home/muqiao/.cache/so101-graspgenx/upstream/.venv/bin/python experiments/colab-twin/evaluate_station.py --station experiments/colab-twin/scenarios/factory-loading/layout-place-200-200-0mm.json --candidate experiments/colab-twin/route_strategies/baseline.py --output-dir experiments/colab-twin/output/station-family-20261022/6c536ef6-e8a1-4846-82cb-c22d474726eb/baseline
MUJOCO_GL=egl /home/muqiao/.cache/so101-graspgenx/upstream/.venv/bin/python experiments/colab-twin/evaluate_station.py --station experiments/colab-twin/scenarios/factory-loading/layout-place-200-200-0mm.json --candidate /home/muqiao/.cache/ros2-factory/codebuddy-so101-20261021/round2/candidate.py --output-dir experiments/colab-twin/output/station-family-20261022/6c536ef6-e8a1-4846-82cb-c22d474726eb/cli-candidate2
```

当前只静态软件，没有模型编译、MuJoCo推进、物理、ROS/build、浏览器QA、服务操作或新模型调用。执行owner本SO101对话，根负责后续资源协调；两条argv共用同一fixture及原判据，不加前序成功门禁、内容锁、调度平台或新原生队列服务。旧任务与负收益证据保留；本工位未测可达/收益明确待验，不宣称泛化或性能。Knowledge：already_covered，沿用原静态/物理结果边界原则，当前项目状态仅写本计划。


## F2f 第二放置工位实际2/2通过（2026-10-22）

协调根明确分配的有限两回合窗口内，干净5822529源码按原prepared串行运行，同200/200/0mm fixture、原裁判/模型/碰撞/90s与墙钟预算保持。runner在北京时间2026-10-22 01:27:49–01:31:05完成，两个subprocess均exit0，已观测owned活动进程剩余=[]。已立即同时回告协调根与无人机明确归还，不扩批次、不测试旧候选3、不扫参数或新模型，不动5187/5192或他仓在途。

| 配置 | run_id | 原终态/判定 | sim秒 | wall秒 | 搜索wall秒 | worker wall秒 |
|---|---|---|---:|---:|---:|---:|
| baseline | 8b42f4a9-4419-451e-9648-622114214b85 | succeeded/pass | 77.04 | 81.985163 | 1.696311 | 1.764526 |
| 原CLI候选2 | d0e2f4f1-b148-4355-ac1f-0099f5592904 | succeeded/pass | 77.00 | 111.061456 | 2.835881 | 2.912566 |

本owner独立回读原report/trajectory/resolved_station/XML：两轮passed/grasp/place/controller_done/release_audit=true，无安全停机/障碍接触；free_object=true、weld=mocap=0，末态盘底真实接触、双指力0、物体近静止。最大释放XY漂移0.267353mm、脱离后接触力0，回位最大误差0.000101346rad。同初态qpos、resolved_station、contact/planning XML、原scorer及release阈值，原90s/14s预算不变。两轮录制器complete=true，captured/encoded均482帧；没有用编码元数据代替物理判据。

实际执行：两者60mm、57mm端点IK均拒绝，再完整认证54mm。baseline尝试顺序60→57→54，CLI2为57→60→54；原起态路线费用均30.508508541s，最终入场桥接后30.508516595/30.508516296s。baseline请求37mm脱离、CLI2请求28.461538mm，均在下一IK不可达后原安全回退至25.615385mm。不是修改目标或放宽守卫强行成功。

原阶段计数仅hold155→153拍（3.10→3.06s，-0.04sim），其他阶段样本数相同，不能称逐点轨迹相同；transport request→admission0.98→0.94sim s。report.hold_duration_s33.56/33.52s是物理持物累计，不当成等待阶段。CLI2总wall反增29.076294s，搜索与worker分别增1.139570/1.148040wall s；这些指标重叠，不能重复相加或把全部wall差归因已定位的规划因素，剩余墙钟成因未诊断。本轮不晋级，默认baseline保持。

原产物在`experiments/colab-twin/output/station-family-20261022/6c536ef6-e8a1-4846-82cb-c22d474726eb/`：pair-results.json含精确argv/实际PID/终态/owned检查，independent-checks.json含原物理/释放/阶段/worker/场景对照；两个UUID完整保留evaluation、原report/trajectory/planning/XML/录像。根亦已独立读原文件确认。没有新增物理失败被覆盖；这两个业务工位的有限复核不构成广泛泛化或性能证明。

## F2f 下一候选仅静态提出：优先已测可行54mm

根要求只静态提出一个直接作用于已测瓶颈、复用现有接口的方向及原评测入口。已新增手写`experiments/colab-twin/route_strategies/prefer_054.py`，仅返回transport_preference_m=.054，其余为baseline默认separation_steps13、continuation、transport_candidates1；并非CLI/模型生成，不激活为默认。

依据：当前baseline失败的60/57mm端点IK实际分别耗时0.150964/0.154562wall s，合计0.305526s；旧CLI2也做了相同两次拒绝，但耗时不同，不当固定节省承诺。方向是用原transport_heights把已完整认证的54mm移到首位，若它仍可行则避免前面两次失败求解；不删除其他高度、不省略共同释放端点或全路线认证、IK/碰撞/预算均不变。该候选不试图改变运输几何，主要完整认证工作仍保留；实际worker/整回合净收益可能不存在，需未来原A/B裁决。

原load_route_policy实际加载新文件，参数为.054/13/continuation/1。用当前记录的高度前缀60/57/54静态重排为54/60/57，原前缀各选择完整保留；原类本身仍保留全部其余回退。原validate_station解析同200/200输入通过，mujoco_imported=false，没有构造新模型、物理/native/ROS/build/浏览器QA/服务或新模型调用。

静态证据与未来同输入准确argv在`experiments/colab-twin/output/prefer-054-static-20261022/0075f323-8e42-4e49-947e-34bd91db3ef7/prepared.json`，新候选原文副本在同目录。status=static_proposal_physical_not_run；本次窗口已归还，不在本轮运行新候选或基线重测。原入口不变，未来明确范围/窗口后可复用：

```bash
MUJOCO_GL=egl /home/muqiao/.cache/so101-graspgenx/upstream/.venv/bin/python experiments/colab-twin/evaluate_station.py --station experiments/colab-twin/scenarios/factory-loading/layout-place-200-200-0mm.json --candidate experiments/colab-twin/route_strategies/prefer_054.py --output-dir experiments/colab-twin/output/prefer-054-static-20261022/0075f323-8e42-4e49-947e-34bd91db3ef7/prefer-054
```

该prepared另存同fixture的baseline argv；两项互相独立，不加前序成功门锁。交付仅原审计/计划/说明与这个5行手写静态提案，不改规划器/裁判或全局平台；后续实际窗口由根另约。Knowledge：already_covered，仍区分退出、原物理通过、候选收益及两个时钟，原状态写所属计划。

## F2g 实际054对照未达运输，保留超时证据（2026-10-22）

用户已直接授权持续优化；此前“仅静态/另等授权”的状态被本轮接续替代。研究根明确交资源后，干净1480457源码按0075f323 prepared原baseline→手写prefer054串行实际执行。原场景/裁判/90sim与120wall保持。

| 配置 | run_id | 原判定 | sim秒 | report wall秒 | 运输搜索 |
|---|---|---|---:|---:|---|
| baseline | e1d2c7c0-8df4-4034-8dd6-e6fa50097c63 | fail: wall_time_limit | 21.20 | 123.378898 | 未进入 |
| prefer-054 | 005c610b-6019-4bba-802f-30a04b603491 | fail: wall_time_limit | 19.88 | 123.535861 | 未进入 |

两轮原grasp/place/release均未通过，无安全停机，不能把缺少碰撞误记成完整任务安全成功；同initial_qpos、同原scorer，运输route_search/worker尚未启动，不填0充当提速。物理已到approach/descend/close附近，而planning.json只有approach条目；已纠正先前消息“仅approach规划”的歧义。report wall含终止清理因此可超过120s；没有放宽预算。runner已完成，owned_active_remaining=[]。完整报告、轨迹、录像状态、独立读回均保留该series。

现场/proc/loadavg33.18/26.38/16.84；根另核16逻辑CPU、load42.60/30.39/18.82，额外blender属media-studio，两个python3.12属reviewer统计，均非本SO101，不终止或调整其他owner。高负载与超时相关，但未证明唯一原因。本runner未收集process CPU及逐阶段wall，这些字段标unknown而不事后估计。结论：本组无法判断054算法收益，保留候选、不晋级、不认定算法失败；先局部筛选，低竞争再原同输入A/B。

CLI第5轮已使用现有前台CodeBuddy/deepseek-v4.1-flash，工具关闭；输入原源码及实测搜索1.696311s，其中完整路线1.379748s。方向仅检查每个IK调用新建MjData的开销。首返回虽CLI exit0，却是DSML Bash文本而非JSON补丁；工具未执行，未应用候选。错误原文/receipt保留private round5-ik-workspace并反馈同原CLI纠正，不能记作候选生成成功。

## 用户纠偏：复用能力优先，最小可判定集与Mint收口

1. 当前station_executor.TEMPLATE及validate_station仍逐项限制八步。这是实际边界，不能把界面编辑称通用技能编排。能力接续以现有接近/夹持/运输/释放/脱离回位为动作段，先明确输入、持物前后条件和失败/停止语义，再接现有执行器；不能仅放宽数组长度或删除校验宣称自由组合。实现尚未完成。
2. 最小可判定集分层：先同原输入的局部等值/规划成本，明确不等值或无成本收益即淘汰；通过才进入固定200/200与220/170已有工位完整对照。等待帧减少单独报告；完整抓放/碰撞/释放/回位及120s原超时仍由原裁判决定。局部提前结束标screen_rejected/incomplete，不能改原score或当成功。后续记录process CPU和分阶段wall，不仅sim/hold；暂不新增调度平台。
3. canonical projects/so101当前22个tracked变动确含Mint录制大幅重写与两份DOCX删除，另有未跟踪源码/计划。仅核状态与源码，未读凭据配置、未覆盖/提交/删除。PRODUCT_PLAN.md已有产品动作/发布/运行记录；mint_follower_demo/app.py具备对应功能，tools/export_action_to_ros2.py已有官方单位→URDF弧度映射和JointTrajectory/启动模板导出，不能误称为运行时任意轨迹接口。采用同一产品、轻量现场入口与研究工作台两后端的接续方向，优先复用动作资产和结果语义，不把ROS强加Mint。导出不等于当前MuJoCo可执行。
4. Mint遗留收口owner根Codex（本SO101），已向研究根核在途owner，未确认前保护全部录制、标定、日志和删除状态。最短入口：git diff --stat -- mint_follower_demo；随后app.py/static的代码差异与config单位转换独立检查。录制/登录/串口/业务日志不直接入库；DOCX删除需核实际意图，不擅自恢复或提交。现阶段不因代码存在宣称轻量终端已交付，也不整包git add -A。

Knowledge: already_covered；沿用原物理结果与消息/退出码分离原则。上述状态写本计划，不改研究根三文件。

## F2g 最小判定集已实际运行，淘汰一次无收益改动

新增手写离线工具`probe_transport_endpoints.py`，只重放已保存planning里的snapshot_q6/place/release与同一grasp-planning.xml，调用原solve_pinch_ik；三次baseline/candidate交替计时，含原共同释放端点。没有物理推进，不读取物体真值，不跳过原完整路线认证来批准执行。输出明确physical_success=null/full_route_certified=false。

200/200端点baseline60→57拒绝→54可达，候选先54；median wall0.538936→0.035347s，CPU0.536241→0.035347s。220/170原60可达，候选54可达；median wall0.026109→0.026942s，CPU0.026109→0.026918s，无局部收益。输出`output/prefer-054-screen-20261022/{200-200,220-170}.json`完整保留六条/工位记录。只支持200/200局部减少失败求解，不证明通用/完整路线/整回合提速；不切默认。

CLI5缩窄纠错后实际返回完整allocation-only函数，原文在private round5-ik-workspace/narrow-correction/candidate.py，receipt记录CodeBuddy/deepseek-v4.1-flash、32.043s、exit0。AST与原函数仅可选query=None及条件MjData分配不同；不是手写后冒称模型生成。保存原五运输段的17组精确Cartesian目标及seed（15可达+60/57两不可达），五次交替重复结果精确一致（解与拒绝文本）；median wall0.376892→0.381975s，CPU0.376296→0.381929s。局部无收益，淘汰，不应用生产、不再付完整抓放代价。原失败DSML与截断输出也保留，未隐去。

实际probe及逐输入结果在`output/ik-workspace-screen-20261022/report.json`。CLI6已接该负反馈，下一假设为同一worker内相邻边界q5重复认证；只提出缓存最后一个精确输入，原取消检查仍必须在外层每次运行。尚未接入生产或认定收益。

复跑局部端点（仅筛选，不是物理验收）：
```bash
MUJOCO_GL=egl /home/muqiao/.cache/so101-graspgenx/upstream/.venv/bin/python experiments/colab-twin/probe_transport_endpoints.py --episode experiments/colab-twin/output/station-family-20261022/6c536ef6-e8a1-4846-82cb-c22d474726eb/baseline/8b42f4a9-4419-451e-9648-622114214b85/episode --candidate experiments/colab-twin/route_strategies/prefer_054.py --output /tmp/so101-endpoint-screen.json
```

Knowledge: already_covered。全局产品组合与Mint收口仍按上一节，不以这次局部成本冒充产品交付。

## F2h 原物理跨工位与相邻认证复用（2026-10-22）

054在200/200新独立A/B `0ee57351...` 2/2原pass：baseline `488f6815...` 76.98sim/112.810wall，候选 `cb06b525...` 76.84/88.075；原search3.437598→1.564480wall s、worker3.504207→1.619765，sim差仅hold152→145。总墙差显著大于search差，不能把24.736s全归因54mm。220/170重测`f5f63a48...` 2/2 pass：baseline `2f350e20...` 75.20sim/68.462wall，候选75.26/69.704，search1.559964→1.521077，实际整回合反差1.243s。结论：54mm是200/200工位条件优化，不是跨工位稳定性能或默认方案；默认保持baseline。

局部`probe_transport_endpoints.py`三次交替：200/200端点medianwall .538936→.035347s；220/170 .026109→.026942s。局部只判暂停点，不能替代完整路线/物理判定。结果在`output/prefer-054-screen-20261022/`。

CLI allocation-only MjData候选在17个原IK目标/seed五次交替精确等值，但medianwall .376892→.381975s，淘汰。CLI首两次DSML/截断及最终有效源全部保留private cache，生产未应用。

新增CLI+owner最小接入的相邻validity复用，开关`reuse_adjacent_validity`默认false，仅`route_strategies/reuse_adjacent_validity.py`开启。只缓存同一冻结worker上一完成的精确q5结果；异常传播，不量化float，cache命中仍位于原取消wrapper内，因此每次调用先/后cancellation检查。200/200生产路径局部148边五轮精确equal，agent回调670→523、medianwall .430670→.324788s。原物理`9481868e...` 2/2 pass，search1.896608→1.578326、worker3.504?→见原t；完整wall69.077→69.624，未获益。220/170 `1d8019a1...` 2/2 pass，search3.030143→1.481029、wall110.717→102.227；反向`fe53ff24...` 2/2 pass，search2.249474→2.002898，但候选完整wall99.579 vs baseline92.273。三组完整任务墙钟方向不一致，故不晋级。所有run原grasp/place/release/return、free-object、video、cleanup均已独立保存；owned_active_remaining=[]。完整局部/轨迹/评测在对应输出。

复跑原物理入口与原`evaluate_station.py`不变；候选：
```bash
MUJOCO_GL=egl /home/muqiao/.cache/so101-graspgenx/upstream/.venv/bin/python experiments/colab-twin/evaluate_station.py --station experiments/colab-twin/scenarios/factory-loading/layout-place-220-170-0mm.json --candidate experiments/colab-twin/route_strategies/reuse_adjacent_validity.py --output-dir <new-dir>
```
测试38项通过（transport_worker+route_policy+route_selection），但测试不替代完整物理。下一轮从原report/trace找IK重复或路径认证之外的实证瓶颈；新候选必须先局部等值/成本，再完整原裁判。早停不能记成功。

## F2i 能力段与最小判定集实现（2026-10-22）

`station_executor.py` 新增能力目录与 `compile_program()`。旧八步原子程序和 `pick→transfer→place` 三种能力段均可验证；能力段在输出中展开为逐项相同的八步。当前只接受完整抓放序列，缺段、重复、错误次序、混写和未知能力在构造模型前明确 `UnsupportedStation`。`describe()` 暴露能力清单，供网页读取真实边界。

`test_station_executor.py`、`test_evaluate_station.py`、`test_factory_minimum_suite.py` 与原 `test_station_scene.py` 共40项通过。原 `baseline-0mm.json` 读回为 atomic 模式、三段及原八步顺序，place仍为 `(0.24,0.14,0)`；新增 `capability-segments-0mm.json` 读回为 segments 模式，几何与原工位逐项相同并展开为同一八步。

新增 `factory_minimum_suite.py`：同原输入至少三对局部测量；输出不等价、任一 verdict 不是精确 `pass`、样本不足或中位收益未达门槛即淘汰；逐对耗时不一致为 inconclusive；只有一致局部收益才 `eligible_for_physical_ab`。该工具不运行物理，不替原裁判判成功。测试覆盖快失败、输出不等价伪造成功、缺失/unknown/unscored 和阈值边界。

原物理执行已接续完成：

| 输入 | run_id | 原裁判 | sim/wall秒 | 结果 |
|---|---|---|---:|---|
| capability-segments-0mm | `1fccf040-0dc6-49e7-9502-37e071273bb1` | pass | 74.78 / 60.748 | 抓取、放置、静稳、释放脱离、回位通过；安全停机0、障碍接触0；录像468/468帧 |
| baseline-0mm兼容轮 | `416351fe-b43b-4b04-b45d-6dc538f4916a` | fail | 57.90 / 121.276 | 原120秒墙钟上限；抓取成功、持物30.42秒、无安全停机，停在lower早期，失败保留 |

能力段轮的释放审计通过：67.44秒发生实际脱离，锚点XY最大漂移0.265805mm（原2mm阈值），脱离后最大接触力0N（原0.02N阈值）；`free_object=true`、`weld=0`、`mocap=0`。最终物块中心Z=9.960725mm，实际盘顶2mm，settle 7.52秒。两回合未修改评分器、碰撞守卫、释放审计、90s/120s上限或默认候选，owned MuJoCo子进程运行后剩余为空。

原子版兼容轮的超时不能判为能力段功能失败：它运行时候选/控制器/评分器的 `loaded_path` 指向本树原模块，resolved program确为 atomic；能力段输入随后在相同源码状态下通过。相邻轮次受宿主负载影响，不构成性能比较，也不重写失败。原始 `evaluation/report/trajectory/XML/录像` 位于Git忽略的 `experiments/colab-twin/output/composable-regression-20261022/` 和 `.../composable-segments-regression-20261022/`。

产品归口：Mint跟随器继续作为 SO101 同产品的低配现场终端，与 Lichtblick/ROS 研究工作台并行。共享层起点仅为版本化产品动作和结果语义；现有关节轨迹导出不是 MuJoCo 运行接口。canonical 22项受控变动、未跟踪源码/计划及DOCX删除保护原位，不纳入本交付。

Knowledge：already_covered。沿用现有ROS2/GUI物理裁判分离和动作资产单位边界，无新增共享知识写入。


## F2j 精确距离复用原物理2/2通过，成本仍不晋级（2026-10-22）

Current：默认baseline；精确距离复用仅保留默认关闭实验。下一方向为SAT轴构造，同一CodeBuddy/DeepSeek Pro候选先局部等值/成本。FishBot在途时不并发物理。

| 配置 | run_id | 原裁判 | sim / report wall秒 | 分离worker秒 | 请求/真实距离查询 |
|---|---|---|---:|---:|---:|
| baseline | c885b8a7-e55c-4bc6-80f0-f62d70c79184 | pass | 74.78 / 59.606815 | 0.729375 | 233 / 233 |
| distance-cache | 4f075f92-ca2e-43d6-88d5-28ace521544d | pass | 74.76 / 59.017086 | 0.587250 | 233 / 206 |

Done：双指抓取/搬运/静稳/释放/回位均通过，safety_stop=false、障碍接触0、free_object=true、weld=mocap=0，录像各468/468。释放XY漂移0.265805/0.265794mm、脱离后峰值力0N；hold144→143拍，其余阶段样本数相同。单次完整wall差不能全部归因分离缓存。该组未记录进程总wall/CPU，明确null，不从report.wall推算。

局部证据：三批13对全部保留；旧比较仅Python数值相等，严格原筛选器因缺逐位证据reject，且其中一对wall回退。新增严格float64字节检查三对通过等值，但计时inconclusive。因此暂停该候选的新物理，而不是反复测到有利结果。此前实际A/B已运行，保留其原pass，不把事后计时纠正称先验准入。完整产物与独立回读：`experiments/colab-twin/output/separation-distance-cache-ab-20261022/20261021T185831Z/pair-readback.json`；全部探索/严格筛选在`local-screens/`。第一批仅从本turn工具输出恢复，来源注明，未伪造原stdout。

代码与验证：CLI9原文位于private `~/.cache/ros2-factory/codebuddy-so101-20261021/round9-separation-distance-cache/`；owner修复浮点signed-zero键和字典所有权。原113项相关测试通过；随后补shape与部分异常姿态失效并通过28项相关测试。两个物理回合早于该异常边界补强，正常finite-q6命中逻辑未变；严格局部复算使用补强后的当前源码。

Next：CLI10 Flash的429/exit0/空stdout原样保留，未称候选成功；同harness切DeepSeek Pro实际生成单次broadcast cross函数，pending局部结果。不新增调度服务、训练或实体操作。

Knowledge：already_covered；沿用Wiki《ROS2 与 FishBot》第20节的独立物理评分/候选晋级边界与双时钟解释。当前计时、失败和来源留本计划，无个人memory写入。


## F2k 批量SAT轴局部通过，完整物理结果见后续接续

Done：原生CodeBuddy/DeepSeek Pro生成源码，owner仅做现有接口接入；`batch_separation_axes`默认false，候选入口`route_strategies/batch_separation_axes.py`。数学body与私有CLI源码AST比较相同。128项相关回归通过，其中新增462组阈值邻域/旋转的SAT逐位对照及真实query/pad位姿对照。主控制器、评分、碰撞阈值和回退不变。

Done：同一已有原释放快照各3对交替。nominal和200/200严格逐位等值且成本筛选eligible_for_physical_ab；220/170严格等值但成本inconclusive，不挑掉其慢样本。产物`experiments/colab-twin/output/separation-cross-axes-20261022/local-summary.json`保留全部原计时与来源。

Next：原nominal完整baseline→candidate命令与输入已保存`output/separation-cross-axes-20261022/dba35cbb-0660-4d66-b7b4-7054ae69a5c2/prepared.json`，尚未运行；同原evaluate_station和90sim/120wall。private run_pair.py仅顺序调用原CLI并记录完整process wall/CPU，不新增调度器。当前FishBot141/9111实际sim/bridge占用，因此无新SO101物理。接实际释放后运行；有净收益再接另一已有工位，不能以局部eligible或测试代替原抓放裁判。

Knowledge：already_covered，沿用上述独立评分、双时钟与默认不晋级原则。


此前资源阻塞时的交接记录（已由下节实际结果接续）：F2j/F2k 软件交付775d658已推至`qiaoqiao2521/so101`的`codex/colab-twin-20261001`；Git ls-remote和GitHub REST均独立读回相同完整提交。默认候选仍baseline。最后现场核查FishBot141/9111的sim/bridge仍active，owner正在执行第二单，没有启动新的SO101评测、也未停其他owner实例。资源占用是当前物理阻塞；无owned SO101运行或后台自续承诺。下一owner根Codex，空档先核实际重实例，再运行下列已准备的原CLI二轮；完整结果前不写F2k已验收。

```bash
python3 /home/muqiao/.cache/ros2-factory/codebuddy-so101-20261021/round10-batched-cross-axes/run_pair.py /home/muqiao/dev/ros2/_delivery/so101-colab-20261001/experiments/colab-twin/output/separation-cross-axes-20261022/dba35cbb-0660-4d66-b7b4-7054ae69a5c2/prepared.json
```

该helper只串行调用prepared内两条原evaluate_station argv，逐轮保存进程wall/CPU；未知/失败保留，原任务时限不改。不能为等待资源机械重跑已完成局部批次或只取有利结果。


## F2k 完整物理A/B已完成：2/2通过，无端到端净收益（2026-10-22）

Current：原baseline保持；SAT批量轴默认关闭，本组不晋级、不扩第二工位完整抓放。启动前现场已无其他机器人重实例，沿原prepared串行执行，源为干净5d1bc1c。

| 配置 | run_id | 原判定 | sim秒 | report wall秒 | 全进程wall秒 | 全进程CPU秒 |
|---|---|---|---:|---:|---:|---:|
| baseline | afdb6cfc-84b3-454f-a8e0-1bcedf5ec76d | pass | 74.78 | 68.644547 | 70.319986 | 76.864662 |
| batch-SAT | 44ec6f60-5a04-409c-8b98-d34074a7a0c4 | pass | 74.74 | 103.930547 | 104.705051 | 106.869326 |

Done：两轮原抓取/搬运/放置/静稳/释放/回位均通过，safety_stop=false、障碍接触0、free_object=true、weld=mocap=0，录像各468/468。释放XY最大漂移0.265805/0.265783mm，脱离后峰值力0N，静稳均7.52s。resolved_station、初态qpos和四XML逐字节相同，实际评分器引用相同；候选实际记录distance_kernel=batched_cross_axes，233次查询与205个保存样本完整保留。

分段回读：hold144→142拍，其他阶段计数相同；0.04sim差仅hold。分离worker墙钟0.594886→1.813300s，未改的运输worker也从1.277194→2.118864s，运输search1.233085→2.036460s。整进程wall增加34.385066s、CPU增加30.004664s；这些重叠指标不能相加。原轨迹没有逐阶段wall/CPU或连续宿主频率/争用记录，不能把全差归因于SAT、GIL、GPU或宿主调度。局部数学等值/成本通过没有转化为本组端到端收益。

产物仍在原dba35cbb目录：pair-process-results.json包含准确argv/PID/退出和两时钟；pair-readback.json独立汇总原report/trajectory/planning/释放/录像及输入对照，原两UUID产物完整保留。本次helper无修改评分、物理阈值、90sim/120wall或场景。两个进程exit0；现场核无owned evaluate_station/run_visual_grasp残留，已向FishBot回告资源归还。

Next：将本组实际负结果送同一CodeBuddy/DeepSeek Pro，先分离真实循环计算与宿主条件，再提下一小改动。短探针若提前停止仍记incomplete，不得算抓放成功；不重复完整A/B直到原数据支持新假设。本轮没有默认变更、训练、实体操作或新调度器。

Knowledge：already_covered；沿用Wiki《ROS2 与 FishBot》第20节的独立物理评分和候选晋级边界。项目结果留本计划，不写个人memory。


CLI11负反馈已闭合：同一前台CodeBuddy/DeepSeek Pro消费上述真实A/B与源码边界，67.103s、success，工具关闭。返回下一步先做窄wall/CPU诊断，没有新候选应用或额外物理。私有round11-post-sat-feedback保留prompt/stdout/stderr/receipt/原答复。owner只采纳分段计时方向，拒绝“查询/样本数量相等足以排除几何原因”的过度断言；两物理轨迹有小差异，计数不证明数值相等。worker也不在run_physical_episode内部，具体打点须按真实源码落位。

当前最短接续：先复用run_physical_episode原循环和既有回调做小规模分段wall/CPU测量，分别覆盖controller.update、10次物理积分、diagnostics/monitor与录像记账。局部截断仍记incomplete；先确认昂贵阶段再生成下一策略/实现候选，不盲加完整抓放批次。当前没有后台运行。

## F2l 100拍真实循环分段计时（2026-10-22）

新增默认关闭的timing边界与probe_episode_timing.py，仍调用原evaluate_station。100拍主动停止是DiagnosticCycleLimit，原verdict=fail、passed=false，探针physical_success=null；没有抓放验收或50Hz通过声明。计时只用当前线程CPU，规划线程/编码子进程另记，不将重叠指标相加。代码相关25项测试通过。

原nominal无计时d3234253-c62e-436d-b381-8217ec2e2a81与有计时835c11b0-8bc6-4ae1-90cc-d50e3456ba21均运行100拍/2sim秒；全部trajectory字段相等，elapsed/q6/qvel/command/geometric_reference/servo_offset/object_xyz/tip_forces及初态逐binary64相等。各13帧完整录像、safety_stop=false。评测调用区间wall4.377499/4.235059s仅为透明性对照，不是性能收益证据。原探针process字段实际排除了导入和最后写探针报告，不是全进程；后续工具已改名evaluation_interval，full_process留null，原文件保留。

有计时100拍：完整周期wall中位5.406075ms、P95 8.216732ms，当前线程CPU中位5.406184ms。总循环wall0.582502s，其中controller0.384576s（66.0%）、物理与2ms守卫0.107100s（18.4%）、diagnostics/记账0.056028s（9.6%）、callbacks0.019207s、定位0.011158s。初始化3.254750s，录像收尾0.332112s另列。仅approach，不涵盖持物、释放、回位、异步等待或长扫掠，不能解释此前完整70→104s差异。

独立第三个100拍只对原controller.update开cProfile，保存于同series/controller-profile。5800次projected_box_bounds、6700次np.r_，遮挡预测为可测子成本；剖析开销不作微基准。CodeBuddy/DeepSeek Pro round12正在消费该证据，只允许像素包围盒单函数实现候选，不改变遮挡范围、角点、保守判定、阈值或任务条件。局部淘汰后不机械追加完整物理。

产物：experiments/colab-twin/output/episode-loop-timing-20261022/short-100/{control,timed}/timing-probe.json及transparency-readback.json。复跑：在experiments/colab-twin使用原Python执行probe_episode_timing.py --station scenarios/factory-loading/capability-segments-0mm.json --output-dir output/<新目录> --cycles 100；透明性对照另加--no-timing。实际资源已归还FishBot，无owned物理残留。

Knowledge：already_covered，沿用Wiki《ROS2 与 FishBot》第20节双时钟、独立验收及局部证据边界。

### F2l 完整原版与后续局部候选

一次原baseline完整计时ef1db833-45a4-49f1-a796-a54d11f4fd4d已原pass：74.78sim、grasp/place/controller_done=true，持物31.42s、静稳7.52s、抬升41.271785mm、障碍接触0、安全停机false、free_object=true、weld=mocap=0；释放后力0N、XY漂移0.265805mm，468/468录像。与历史原baseline afdb6cfc的3739拍全部trajectory字段相等，八组数值逐binary64及两场景XML字节相等。此对照只核透明性，不是不同宿主时刻的性能A/B。

主循环3739周期合计49.132078wall/48.592849当前线程CPU；controller39.464553wall/39.050429CPU，物理＋2ms守卫5.447515wall，诊断2.494416、callbacks1.416229、实时定位0.095707；初始化3.226248、录像收尾1.407813另列。运输控制18.376051s、闭爪控制6.805051s。全周期wall中位15.068856ms、P95 27.443683ms、最大154.894327ms，259/3739超过20ms，完整50Hz未通过。

时钟口径修正：原探针process字段54.270431wall、55.847570self CPU、3.317409children CPU实际是evaluate()调用区间，排除探针导入和最后探针JSON序列化。全进程wall/CPU未外层测量，留null；不可与旧70.319986全进程数算收益，也不可将children CPU重复加到当前线程阶段。原timing-probe保留，analysis和independent-readback明确修正；工具后续字段改evaluation_interval，并将每次报告保存在原UUID内，避免同root重跑覆盖证据。

CLI12像素拼装局部screen原eligible，所有6092输出逐位相等，三对局部wall省18.590/20.338/18.239ms；但只影响前6.54sim秒，按前100拍粗算约0.06s潜在整轮收益，并非实测提速。该候选暂缓完整A/B，默认不变。原响应解析首次把消息数组误当对象，已保留解析错误并从同一原stdout恢复，无额外模型调用。

100个已记录运输guard-core输入局部复算全valid，无mj_step/无任务成绩。5500个configuration-sweep状态与5800次checker表明完整夹爪扫掠是主要成本。cProfile带额外开销：core1.663s、sweep1.492、native summary-frame1.048、binding0.194；不将剖析比例当未剖析成本。仅部分上下文从现有构造器与记录重建，不能称完整update重放。保存transport-core/profile_core.py、results.json及pstats。

CLI13只尝试减少snapshot数组逐标量递归，保留原全部字段、独立所有权、signed zero、原_immutable_context与全部扫掠点。首版真实调用snapshot_context(np.zeros(3))因缺RoutePolicy导入NameError；failure-v0.json与candidate-v0.py保留，已通过CodeBuddy原native session反馈实际错误及ndarray subclass回退边界。修正8.438s完成，100绑定context.matches、30边界与修改原数组后副本保持均通过；原三对局部wall省3.697/4.275/4.458ms，中位4.275ms低于原5ms门槛，reject，不进生产/完整A/B。初版局部比较器另有基线函数抽取后未绑定递归名称的错误，local-screen-v0-harness-error保留；只纠正边界读回并保留三对原计时，没有重测挑有利批次。后续native原始认证计算是主要成本，不删5500状态。

当前27相关测试通过（含原验证失败不因缺report崩溃、异常后原入口恢复）；原生OpenGL导入出现第三方/proc/cpuinfo ResourceWarning，测试仍正常通过，未因此改依赖。FishBot实际sim/bridge已占用，后续仅CLI/native局部检查，不并发新SO101物理、没有默认变更或20＋20/实体。

完整复跑：原Python执行probe_episode_timing.py --station scenarios/factory-loading/capability-segments-0mm.json --output-dir output/<新目录> --full-episode。仍为原90sim/120wall；analysis.json和independent-readback.json位于同series/full-baseline。

### F2l native编译候选淘汰与DFS接续

计时代码及三文件5eb6ab04a2f08853a627467acfb4ea4d8d5d1273已推qiaoqiao2521原分支；ls-remote与GitHub API均读回一致。原默认保持，27测试及原完整物理证据见上。

CLI14（CodeBuddy/DeepSeek Pro 74.922s）只增加-fno-math-errno，原源码/其他严格flags不变。单独私有库编译成功、text字节有差异。5500原扫掠帧×285pair，每对12 numeric＋6flag的binary64/int64字节全部相同，非有限输入等值；FE_DOWNWARD及FTZ/DAZ均被两库拒绝且原始字段相等。几何计时用两份非test库；既有test-only库仅用于当前线程CSR控制。三对原summary路径baseline0.957237/0.962461/0.958746s，candidate0.969289/0.967353/0.966169s，均更慢，中位+7.423ms，原screen=reject/no_median_local_effect。没有完整候选物理、默认切换或阈值调整。

辅助实验错误完整保留：首次objcopy dump没有指定独立输出，触碰了已加载原cache库并导致诊断helper退出139；原库字节仍匹配原构建清单，独立新进程原加载和原checker烟测通过。后续仅操作私有副本且显式给独立输出。第二次误把test宏下MXCSR钩子当生产导出而AttributeError，未进入计时；改用项目已有test-only库控制CSR，实际比较库仍为生产构建。两错误不归咎候选，不隐去失败，也未将编译成功当算法验收。

产物位于同series/native-errno/{frames.npz,raw-readback.json,local-screen.json,exact-duplicate-readback.json}。私有round14-native-errno保留原CLI/格式恢复、compile-receipt、两次辅助失败、原library完整性读回与probe_native.py复跑。116.864s同native会话负反馈已success；owner不采纳对已淘汰候选追加sqrt计时，三对有符号差不能冒充对称噪声带，原异常浮点行为也不能凭模型文字保证。

实际语料复算：5500条q6各不相同；29个几何中16个transform固定、13个各5500种，44个pair两端固定。这里只量重复，不删285对检查或缓存旧证书。源码full_tree每次创建std::vector DFS pending栈，作为CLI15新假设：小内联数组＋原vector spill，全部节点/左右push顺序/浮点/失败fallback保持。当前仅生成候选、未应用生产；FishBot141/9111实际占用，无owned SO101物理。

## F2m CLI15–18与四顶点接入（2026-10-22）

CLI15内联DFS栈数值通过但三对+16.960/+12.612/−33.613ms，中位+12.612ms，reject；原动态栈保留。CLI16统计18500621次顶点计算、重复5.9%、direct64潜在1.9%，未做新缓存。CLI17原生CodeBuddy/DeepSeek Pro产出AVX2四顶点leaf实现，实际编译错误已在同native会话反馈修复：两AVX比较intrinsic改标准_mm256_cmp_pd。原v0/修正版/CLI回执保存在私有round17-quad-leaf。CLI18首轴zero-add补丁实际比父版三对更慢，中位+17.640ms，淘汰，原四顶点不混入此改动。

原5500帧×285pair/12numeric+6flag及hint ID逐字节同值，向量disabled控制、非有限、FE_DOWNWARD与FTZ/DAZ原拒绝行为同值。415边界＋224尾槽/tie实际向量调用2256次通过。原三对summary为0.950885→0.818575、0.949761→0.812116、0.948166→0.821877s，中位改善13.914%；这仅局部，不是抓放/50Hz成绩。历史100case成本集variable9.821%未达旧10%原样保留，accepted_local_cost=false；当前factory原筛选已经eligible，owner纠正此前将历史专属门槛机械充当前序约束的范围错误。

已按默认关闭quad_vertices接入RoutePolicy、support_native编译选择及station_executor，活动库不热替换，不支持CPU保留scalar。原evaluate_station新增可选--timing，仅记录原loop、不会主动截断。集成预处理scalar与原生产、quad与已测CLI原型分别一致；实际新库5500帧仍0差异。49入口/loader/策略/计时＋41树/quad/witness/碰撞回归通过，diff check通过。

当前正在原nominal执行baseline→quad完整物理A/B。prepared：experiments/colab-twin/output/quad-vertices-factory-20261022/45c622be-b068-46fb-9b44-92ad1d4aab9a/prepared.json。两库均已在同一集成检查预编译，原90sim/120wall、原裁判、全部完整扫掠/碰撞/释放标准保持。现场无其他机器人重实例后启动，已向FishBot告知串行占用。尚无新物理结果，不切默认；有实际净收益再另一已有工位。

Knowledge：already_covered，沿用Wiki《ROS2 与 FishBot》第20节独立评分与双时钟。

### F2m 原完整物理A/B已完成：2/2pass、候选reject

| 配置 | run_id | sim秒 | 全进程wall秒 | 全进程CPU秒 | controller wall秒 | controller线程CPU秒 |
|---|---|---:|---:|---:|---:|---:|
| baseline | 87870522-48af-4b8d-9f9d-b4213ae257de | 74.76 | 60.873834 | 67.457896 | 43.042943 | 42.565434 |
| quad | 69c9822e-de93-4723-9d6f-394b03bfe019 | 74.82 | 64.892332 | 73.181694 | 45.474544 | 44.958760 |

两轮原grasp/place/controller_done、释放脱离/回位均pass，无安全停机/障碍接触，free_object=true、weld=mocap=0，录像各468/468；静稳各7.52s。resolved-station、四XML及初始qpos逐binary64相同，实际评分器引用相同，baseline无quad宏、candidate实际加载quad宏，非只记录意向。除hold143→146拍外，approach829/descend147/close331/lift148/transport1294/lower130/settle107/release331/separate147/retreat131均相同。

候选全进程wall+4.018499s（+6.60%）、CPU+5.723798s；controller wall+2.431601s、线程CPU+2.393327s。相同拍数的transport与close控制分别增加1.080139/1.191603s，lift/lower/release少量改善不足以抵消。不能把0.06sim等待差或局部13.9%当成算法净收益。周期P95 29.742751→33.012865ms，超20ms 477→671，50Hz仍未通过。无连续频率/热状态/争用测量，不归因AVX降频或宿主异常。

结论：本组reject，不晋级、不切默认、不追加第二工位完整抓放。保留quad_vertices为显式default-off复跑候选；原入口默认仍原scalar。prepared、原两UUID、pair-process-results及pair-readback完整保留在上述45c622be目录。原loop时钟与外层全进程时钟分别记录；无放宽物理、评分或90sim/120wall。现场无owned仿真残留，已回告FishBot归还资源。

接续：同native会话CLI19正在消费真实负结果、分段wall/CPU及实际Context/绑定源码，只允许下一有证据的小改动或最小区分测量，不复跑本组挑绿。根Codex继续局部验证，资源空档且局部有益后再原物理；不把CLI退出/静态测试算业务完成。Knowledge：already_covered，同前第20节；本轮无全局memory修改。

CLI19首次从repo目录resume返回exit0但stderr为No conversation found、stdout空，不能计成功。原session实际属于私有round17-quad-leaf目录；保留cwd-error四回执后，从原目录以相同native session恢复，未新建独立会话或丢弃上下文。

## F2n 当前接续：实际native份额与方向表统计

002266dd90384cf825f30d18ed10b328e0a2f76f已推原qiaoqiao2521分支，Git ls-remote与GitHub REST均独立读回一致。90相关测试、5500帧接入同值及两轮原物理结果见上。默认仍scalar，实验quad未晋级。

CLI19原目录native会话151.201s/success，没有候选。owner仅采纳加法ABI计时，拒绝无证据的宿主归因、“19.5s运输规划”误读和额外10%物理门。私有trace_core.py从同一原baseline全close/transport各等距100输入复算：close8990扫掠状态/9090ABI calls，局部core2.270124wall、native1.708421（75.26%）；transport5500状态/5800calls，core1.495139、native1.041217（69.64%），200条全valid。无cProfile/mj_step，部分上下文重建，不能称完整update/物理成绩；原callable已恢复。证据同series/native-share/readback.json。

进一步私有整数计数不改任何数学：5500帧×285pair、159500个Frame，nonaxis查找319000次、0命中、插入319000次；缓存大小0有137500次、13和16各11000次。raw12numeric/6flag/hints全部0差异，instrumented成本不算提速。原方向投影缓存已有，下一项不再造缓存或取消其语义，只尝试短表存储减少节点分配。原生CodeBuddy/DeepSeek Pro CLI20同一会话正在据实际源码/计数生成按需小表＋原unordered_map任意溢出候选。原scalar、全部285pair/采样、数学/阈值/90sim/120wall保持；没有新候选物理或默认切换，尚须原三对筛选。

Knowledge：already_covered，同前独立评分/双时钟；CLI工作目录错误与原回执已保留，不写新memory。根Codex接续，当前无owned物理进程。

## F2o 小方向表原完整A/B（2026-10-23，执行中）

CLI20同native会话210.796s/success返回纯make_candidate。按需unique_ptr的16项表，仅首次非轴投影插入时分配；第17项迁移全部原条目到原unordered_map，之后复用map。原Key/full/zero、project的查找与插入位置、全部数学/285pair/采样不改，未组合quad。私有源码与CLI原函数保留。

原5500帧×285pair/12numeric+6flag/hints逐位0差异，capacity=1强制原map溢出也0差异；非有限及FE_DOWNWARD/FTZ_DAZ拒绝同值。原三对summary 1.291777→1.219946、1.244200→1.154812、1.205031→1.138987s，各省71.831/89.388/66.044ms，中位relative5.561%，原screen=eligible_for_physical_ab，没有10%附加门或新采样配方。

已接入默认关闭small_direction_cache与原路由入口，原quad保持false。集成preprocess确认default与002266d原代码相同、enabled与已测CLI20原型相同；新两库5500帧仍0差异。52相关回归通过，含两容量1/16各160次插入和67个distinct key对原map查找/首次值/溢出/空表延迟分配对照。原native flags保持严格FP；无评分/物理/阈值/回退变化。

当前原nominal prepared：experiments/colab-twin/output/frame-direction-cache-factory-20261023/7cc17a87-a607-4e69-bdb3-0eb823f1e841/prepared.json，baseline→candidate顺序原evaluate_station --timing，原90sim/120wall、视频和实际释放检查保持。两库同窗已预编译，外层run_pair记录完整process wall/CPU；尚无物理成绩，不切默认。启动前实际进程空闲，FishBot快照正在整理其失败/提交，已告知占用。

Knowledge：already_covered，同前第20节；根Codex接续。

### F2o nominal原A/B已完成：观察到正收益，第二工位执行中

nominal baseline 5ad3e1b5-00bd-482f-a916-57356c8efeb4：原pass，74.76sim、65.634911全进程wall、73.322960CPU，controller46.516841wall/46.107822线程CPU；candidate 0aeb5603-6b9a-4fd3-b7ad-0b41ea9fe255：原pass，74.78sim、63.464497wall、71.066181CPU，controller45.295691/44.898041。全进程wall少2.170414s（3.31%）、CPU少2.256779s（3.08%），controller wall少1.221150s。

除hold143→144拍外其余阶段拍数相同，transport/close计算分别少0.483509/0.364320s；不是等待少拍。原场景/四XML/初态binary64/裁判引用一致，实际candidate加载SMALL_DIRECTION_CACHE宏且quad关闭。两轮grasp/place/controller_done、释放/脱离/回位均pass，safety=false、障碍0、free_object=true、weld=mocap=0，原释放阈值和完整录像保持。周期P95 32.360051→31.359032ms、超20ms 708→575，仍非50Hz通过。physics等未改部分也有耗时差，不把整轮3.31%宣称为隔离的确定算法收益。

按原用户要求，已有200/200工位继续独立复测，不重新调参；反转为candidate→baseline，原90sim/120wall。prepared：experiments/colab-twin/output/frame-direction-cache-factory-20261023/0d8d83f4-839a-4cce-8250-5505d3daface/prepared.json。两轮运行中，原默认未改；完成后与nominal一起判断保留或淘汰。现场无其他机器人重实例，已向FishBot说明继续占用。

### F2o 第二工位完成：收益不稳定，整体不晋级

200/200反转顺序：candidate 50694131-0226-4f51-b335-2611da440c71原pass，77.06sim、63.930543全进程wall、72.119606CPU，controller45.585871wall/45.053339线程CPU；baseline e0945351-f3ee-4b8b-b672-261adababd8f原pass，77.04sim、62.706387wall、70.490140CPU，controller44.721304/44.252835。候选wall多1.224156s（1.95%）、CPU多1.629466s，controller多0.864567wall/0.800504线程CPU。

同工位resolved-station、四XML、初态qpos binary64及裁判引用相同，实际native选择正确；除hold155→156拍，其余阶段计数完全相同。两轮仍完整抓放/静稳/释放/脱离/回位pass，safety=false、障碍0、free_object=true、weld=mocap=0。P95候选31.758245ms、原版29.406746ms，仍非50Hz通过。

四轮原物理均pass不等于性能通过。nominal+3.31%观察收益没有跨工位复现，整体不晋级、不切默认，保留default-off原样复跑与全部正负结果；不复测找绿，不调16容量。现场无owned仿真残留，已向FishBot回告归还。

下一项先核已有_sweep_binding内部snapshot和SweepBinding.__post_init__/_immutable_context对同一树的两次遍历。原cProfile200次binding0.194s，其中immutable0.097s，另snapshot0.089s；此处不将cProfile成本当未剖析成绩。先做已保存200输入加法分段与输出matches检查，若有实测重复成本再送同CLI单一小改动；暂不新跑完整抓放。

## F2p 绑定双遍历的实际局部成本（2026-10-23）

私有binding_cost.py从同原baseline全阶段等距close100/transport100输入，隔离原snapshot构造与普通SweepBinding校验，不开cProfile、不推进物理。close snapshot11.251425ms/validation11.266458ms；transport snapshot12.136002ms/validation11.815101ms，200/200与完整原方法.matches，原构造入口已恢复。总二次校验约23.082ms/200，远小于旧cProfile0.097s，不按剖析膨胀值外推。原snapshot含拥有副本，普通SweepBinding仍做原owner/model/checker/stage/jaw/guard_scope和finite/signedzero规范化。产物同series/binding-cost/readback.json。

实际小成本支持一次非常小的单遍历候选，不支持大改或宣称数秒收益。CLI21同native会话已收到两工位正负结果、200输入加法计时、原_sweep_binding与配置绑定源码；仅允许所有字段/归属/上下文变更失效/浮点位值及public原行为保持的小实现。先局部三对，收益不足即淘汰；不得复用上一绑定、去掉consume检查、增加hash/版本门或改变评分/物理。当前CLI前台运行，无owned物理进程。

Knowledge：already_covered，维持双时钟与原裁判；根Codex接续。

F2p闭合：CLI21原native会话145.585s/success，没有make_candidate。owner接受“收益上限有限、需保留混合raw/snapshot字段与错误顺序，当前不值得扩大接口”的结论，不把约23ms二次校验全部视为可消除，也不采纳不存在的额外physical bar或“禁止所有私有已验证包装”的误读。原_sweep_binding与普通SweepBinding一行未改，未为此追加物理。

新的窄只读核查：原full_tree在DFS节点已计算向外舍入AABB投影并确认finite(bound)后，叶顶点仍重复执行逐轴finite分类。先只数此严格位置覆盖多少实际顶点、保持所有原检查；不碰种子/witness/full_scan或放宽非有限回退。旧2026-10-08 finite报告已精读：它基于query guard＋quad，逐packet延迟检查，variable8.526%未达其旧10%门。当前只查scalar DFS有限包围盒证明的工作量，不能冒充旧候选已过门或直接复活旧实现。

F2q实际计数已回读：原5500帧×285pair共有18500621次vertex_interval，其中17192933次在原DFS叶finite(bound)之后，失败顶点0。12numeric/6flag/hint ID同原版0差异；计数版不计收益。额外核验发现synthetic helper只校验finite points、不校验local coefficients，而interval mul可能忽略非首NaN乘积。因此单凭finite(bound)不够，任何候选必须使非有限local endpoints走完整原checked路径，不能新提前返回或改首失败prefix。

CLI22原native会话正在核实finite local＋原向外包围盒界对scalar DFS逐点finite分类的证明，只允许一处叶循环快路，seed/witness/full_scan/遍历/数学DAG/全部采样与物理阈值均不变。未产候选前不改生产、不宣称能省12×1719万次就必然提速，也不组合quad/小表。

## F2q DFS有限包围盒快路：等值通过，原局部成本inconclusive（2026-10-23）

CLI22同native会话228.920s/success给出纯make_candidate，只在scalar DFS叶循环选择相同DAG、无重复finite分类的helper。helper由SUPPORT_LEAF_BOUND_FAST显式开启且不组合quad/map；local endpoints仍须finite，非有限系数保留完整原checked路径。原seed/witness/full_scan/有限bound检查/遍历/提示/数学次序一行未改。当前只在私有源码编译，未应用生产。

独立原tree＋full_scan对照1324边界/随机用例0差异，包括NaN/Inf局部系数、signedzero/subnormal、尾数/极端neighbor溢出与宽界回退；非有限系数快路调用0，实际快路39505个顶点，避免测到纯fallback误认优化。5500真实帧×285pair的12numeric/6flag/hints及macro-disabled控制均0差异；非有限frame、FE_DOWNWARD、FTZ/DAZ原拒绝行为相同。边界报告完成至成本前raw-readback间隔2.945s，边界编译/执行已结束，不将并发编译计入成本；原全部批次保留。

原三对summary baseline1.870493/1.607353/1.496730s，candidate1.717648/1.609244/1.351118s，effect −152.846/+1.890/−145.612ms，中位relative8.171%。原factory screen=inconclusive/pair_has_no_consistent_wall_reduction；不因中位好看忽略第二对，不进物理、不改默认、不重跑本源码找绿。root正在查看实际编译循环是否已有unswitch/inlining，只有明确的新实现假设才再交CLI。

复跑私有round22-bounded-leaf/{compile.py,check_boundaries.py,probe_native.py}；实际报告同series/bounded-leaf/{boundary-readback.json,raw-readback.json,local-screen.json}。算法正确性与成本结论分开；尚未证明任意binary64全集或sticky FP异常位等值，不作其声明。

6f3df7a1cdd98542a8da522d840ad182bcd46e35已推原qiaoqiao2521分支，GitHub REST与重试后Git ls-remote均读回一致；首次ls-remote超时保留为网络检查失败，不当成push失败或两路验证成功。当前生产无新改动，无owned物理运行。Knowledge：already_covered。

F2q编译检查已闭合：严格原flags生成assembly/objdump，未见full_tree/leaf-fast独立符号或直接helper调用，GCC已内联；不为不存在的调用开销再提always_inline。原成本inconclusive保留，无相同源码复测或新物理。

## F2r 原BVH工作量与单一分叶假设（2026-10-23）

新增原默认整数计数（非22候选）：5500帧×285pair，18500621vertex调用、其中17192933在DFS叶，9642174节点bound、1648430访问叶，平均每访问叶10.43点、原max16。全部raw/hints0差异，不用instrumented时间算收益。

同native CLI23正在根据节点界与逐点工作量选择唯一有依据的leaf常量改动或明确拒绝，不扫8/16/32网格；只允许改原LEAF_SIZE，其余树构造算法/全顶点拥有/精确一次叶覆盖/严格bound/全部原finite检查/种子见证/full_scan与物理判据保持。当前只有生成请求，未改生产或有新物理。Knowledge：already_covered，根Codex接续。

### F2r LEAF_SIZE=8局部通过，原nominal物理执行中

CLI23同native会话107.493s/success选择唯一8并返回仅替换原常量的一行纯变换。owner不采纳其把per-pair计数称per-full_tree以及“bounds增长15%/整体18–20%”的估算；实际计数与成本如下，不用模型估值作收益。

原5500帧等值计数：总vertex18500621→12639103，叶内17192933→11843122；node bounds9642174→12136172，访问叶1648430→1977319。原所有顶点仍拥有且恰好一次入叶，只是原严格BVH多做界检查、少扫描被其认证排除的内部顶点。不是删除路径/夹爪采样或碰撞pair，原finite/scalar/full_scan一行未改；未组合22快路/quad/短表。

1324独立原tree/full-scan边界状态与端点0差异、1204案例实际树结构变化、顶点覆盖全部完整；结构node数/最大叶数按意图不同，不伪称字节相等。5500帧×285pair原12numeric/6flag/hints与恢复16控制0差异，非有限frame/FE_DOWNWARD/FTZ_DAZ原拒绝同值。原三对summary1.371987→1.297591、1.344439→1.219665、1.467567→1.292590s，各省74.396/124.774/174.976ms，中位relative9.281%，原screen=eligible_for_physical_ab。边界先结束再运行成本，不混并发。

默认关闭tree_leaf8接原RoutePolicy/native编译/执行器。集成default preprocess同6f3df7a原代码、enabled同已测CLI23原型；新两库5500帧仍0差异。62相关回归通过，含真实叶8 split结构、全覆盖与原full-scan oracle，diff check通过。

原nominal现在candidate→baseline执行（反转前轮primary顺序），prepared：experiments/colab-twin/output/tree-leaf8-factory-20261023/c6815941-fb67-427e-8b2d-ba81d674a344/prepared.json。两库已同窗预编译，原90sim/120wall、全部安全与评分/录像保持；未有新物理结果，不切默认。启动前计数/测试进程均结束、无其他机器人重实例，Drone快照idle，FishBot/Drone已收到串行资源占用通知。

Knowledge：already_covered；根Codex接续，有实际净收益才另工位反转复测。

### F2r 原nominal完成：行为逐位同原版，未提速，不晋级

candidate 942864f6-2295-430f-b634-73b8221c7c1e原pass，74.80sim、61.300829全进程wall、68.894366CPU；baseline e95c0346-5f74-4144-a713-494c8c414da3原pass，74.80sim、60.937976wall、68.534318CPU。候选wall多0.362854s/CPU多0.360048s，controller wall43.325426对43.210704、线程CPU42.898801对42.825183，未有净收益。

同工位resolved-station、四XML、初态/裁判/实际native宏选择均已核。两轮全部3740行trajectory各字段递归按float64字节比较完全相同（trajectory-transparency.json），包括所有阶段/hold145拍均相同，确非少等拍。原完整抓放/静稳/释放脱离/回位全pass，safety=false、障碍0、free_object=true、weld=mocap=0。P95候选30.971402ms对原29.540441ms，50Hz仍未过。

结论：不晋级、不切默认，不跑另一工位、不扫4/32或改阈值。显式default-off代码保留原样复跑。两轮原process/report/planning/timing/录像与输入完备，源/结果见c6815941目录；已向FishBot/Drone回告此组结束。

后续先核微基准代表性：旧fixture只收100条运输sweep的5500帧，guard-core还有300次其他checker调用；旧成本脚本从hint=-1开始只回放5500帧，没有证明与原整轮每次ns_evaluate_hinted的输入提示及调用历史相同。普通online_chord端点确为self.reference，与记录geometric_reference一致，不能误称已发现命令端点重建Bug。真正缺口是阶段覆盖、查询顺序和hint输入未直接采集。

准备沿原probe_episode_timing/evaluate_station做一次原baseline实时ABI加法计时与每阶段固定seed reservoir输入采样，记录实际p/R/pairs/margin/hint_in及拥有几何副本，不从q6重建，不干预原返回/动作。诊断不是新算法验收；原90sim/120wall保持，若终止仍保存原fail和仅已观测阶段，不追加配额。当前原source/评分冻结，无owned物理，待探针检查与资源空档后串行。Knowledge：pending，微基准提示状态的可复用结论待真实ABI证据完成后由根Codex回读原第20节判断补写。

## F2s 真实循环ABI计时与拥有输入采样（2026-10-23，已完成）

沿原run_probe/evaluate_station新增可选probe_native_abi.py：只包ns_evaluate_hinted的真实调用，按main_update/live stage、main_other与worker线程分别量wall/线程CPU；worker墙钟重叠不相加。主循环每owner/stage/pair_count用独立seed reservoir最多保存256个真实p/R/pairs/margin/hint_in拥有副本，保存原Geometry/kinds，不从q6构造输入，不替换原参数或返回值。原库/类/函数入口在finally恢复；可选采样错误只warn并保留原原生结果。

8相关测试通过，实际小几何原native查询验证返回不变、修改原输入后已采副本不变、初始hint=-1完整保存、异常构造仍原失败和采样故障不改变原结果、入口恢复。原叶8相关62项与5500集成同值已通过；未因此改其他源码或扩展评分。

原baseline诊断691d01ca-4091-404d-8f86-d7b1976e03a4完成，原裁判pass，74.78sim、59.279612全进程wall、66.866704CPU，抓放/释放脱离/回位通过，safety=false、hold31.42s、静稳7.52s。prepared：experiments/colab-twin/output/actual-native-abi-20261023/9c766cda-6ded-41fc-aa62-701d705511a7/prepared.json。原90sim/120wall、全部安全/录像与评价保持；时钟/复制开销包含在诊断时间，不与未插桩旧回合算提速。外层沿用run_pair，不新增调度平台。

main_update共151589次native调用，wall26.483208s，占插桩controller42.276892s的62.6423%。其中transport76024次/12.634672s，close30546次/5.188880s，release12930次/2.510419s，其余阶段见native-abi.json。main_other及worker另列，worker墙钟不累加。11阶段各256份、共2816份真实p/R/pairs/margin/hint_in，拥有原几何副本；独立回读输入形状/有限值/索引/序号均通过、warnings为空。探针没有保存当时numeric/flags/hint_out，不虚称与当时输出逐位核对。P95插桩29.042647ms，仍不宣称50Hz。

私有round24在2816份确切ABI输入上逐条恢复原hint_in，baseline重算与CLI23叶8的12numeric/6flag/hint_out逐位相同。11阶段native-only中位均有局部收益（5.93%–9.29%），但这不是全回合计时，不能翻转已完成的叶8物理无收益结论。原诊断回合已退出、资源已回告FishBot/Drone释放。

## F2t 同一在线守卫的端点重复认证（2026-10-23）

原update先认证实测q6，_configuration_sweep保留并认证首末q6，再由原validate_joint_path调用_arm_valid及持物/已释放物体检查；存在重复端点的源码依据，真实重复数与可复用份额仍待局部核算。旧5500份仅sweep内全唯一，不代表这些外围查询也唯一。原reuse_adjacent_validity仅用于冻结worker规划，不冒充在线已实现。

CLI25复用同native会话、关闭工具、前台等待，输入真实原结果和上述原函数，仅允许同一online守卫内、完全相同float64姿态的默认关闭候选，保留所有原采样/阈值/绑定和额外物体检查。不得跨update/stage/model/checker复用，不缓存未完成查询，不从输入真值救策略。当前尚未生成或应用候选，无新物理回合。

CLI25首版139.237s/success，但缓存覆盖整个update，跨阶段切换/规划/后续命令守卫，owner拒绝、未应用。反馈后修正版272.521s/success改为局部显式dict，仅arm-valid阶段传给本次sweep和jointpath。原200份保存守卫输入计数close9190次仅100次重复、transport5700次仅101次重复；全部原查询实际执行、重复报告0差异，只有外围端点存在少量重复。该重放包含部分重建payload上下文，不是完整update或新物理成绩。

修正版私有200输入原报告与最终checker qpos/qvel/geom_xpos/geom_xmat均0差异；三对3.338299→3.273805、3.308163→3.287762、3.313720→3.294827s，均略快。但独立反例“q1完成→q1命中→q2写入后抛错”发现finally把q2失败现场错误恢复成q1，违反异常副作用保持。原局部结果verdict=reject，不进物理，不因正计时忽略反例。原CLI已收到完整计数、三对和失败例，要求命中时原位恢复原kinematics或明确no_candidate，当前前台运行。复跑/来源在私有round25-online-reuse/{ask.py,correct.py,count_guard.py,screen.py,fix_exception.py}，生产控制器与默认策略一行未改。

7b8457b442ecd44466acc85049f3fec824dc7566已提交推送叶8淘汰证据与真实ABI观察工具，GitHub REST和Git ls-remote均独立读回一致。首次push超时且REST读回旧HEAD，随后同一目标push成功；不把首次超时写成成功。

F2t闭合：CLI25第三版190.333s/success，命中时同步恢复原qpos/qvel/kinematics，实际异常反例已修复，200保存守卫报告及最终数据仍0差异。但原三对3.288897→3.274446、3.288109→3.307180、3.284064→3.270216s，effect −14.451/+19.071/−13.849ms，不一致。另在原FE_DOWNWARD现有拒绝模式下，缓存q1仍返回true，原checker返回false；不能用“这些函数不会改环境”替代实际当前环境检查。最终reject，两份原失败、三次CLI来源和全部原成本保留；不应用生产、不进物理。已反馈同native CLI并明确停止此方向，不追加补丁追回收益。

## F2u 汇总归约预检与分类型原缓存工作量（2026-10-23）

私有round26只量原_summarize：11阶段各32份、352份原ABI重算输出，32次循环×3批，单次中位6.855us；按151589调用估整个组件约1.039s，尚未扣不可消除的字典/取值成本。该值是组件估计，不是整回合省时；暂不为此增加C ABI或结构改造，无候选或新物理。

round27复用原整数计数，2816份真实ABI输入逐条恢复原hint_in，原12numeric/6flag/hints同计数版0差异。旧5500运输输入0命中不能泛化：真实descend有1017/21706、close有1289/22606命中，全部属于mesh coarse。按几何类型/full进一步计数，11阶段BOX coarse+full共46416次查找、0命中，mesh缓存确有实际价值。所有计数非性能测量。

CLI27已收到F2t最终失败、真实分类型计数及原Frame/project/hinted入口。仅请求默认关闭的BOX非轴分支省去map查找/插入：只在原已有traps-masked enabled且方向三分量非零时重算原完整标量投影；mesh/轴缓存、任何含零方向、未知/未屏蔽陷阱、原unhinted入口及全部原数学/有限检查/回退保持。保留原map作为其他分支回退，不引用物体真值，不组合旧候选。当前CLI前台运行，无新生产改动或物理回合；先等值和原三对，只有收益明确才跑原裁判。

F2u闭合：CLI27同native会话80.385s/success，私有SUPPORT_BOX_DIRECT宏控制Frame.direct，仅从原hinted入口的已有masked enabled设置。204原project边界/重复方向/含±0/轴/mesh/极端输入，numeric/status0差异、回退cache_size0差异，65案例实际绕开原map；原FE_DOWNWARD全部拒绝。2816份确切ABI输入逐条原hint_in恢复，12numeric/6flag/hint_out及提交提示、macro-disabled control与原summary均同值；11阶段实际直算计数均非零，完整原数学仍执行。

原三对全慢：0.511606→0.513931、0.510622→0.515220、0.510723→0.516103s，effect +2.325/+4.597/+5.379ms，中位+4.597ms，原factory screen=reject/no_median_local_effect。未应用生产，不进物理，不重跑本源码挑绿。CLI来源、204边界、原所有计数/三对及复跑在私有round27-nonaxis-projection/{ask.py,compile.py,check_boundaries.py,probe_actual.py}。这轮不以“所有BOX没有命中”推断分支重算必然更快，也不把编译/等值检查当交付。

## F2v 原叶读取布局核算（2026-10-23）

下一项只量原seed/DFS叶中同一批顶点的64-byte存储足迹。私有round28-leaf-layout/count_layout.py沿真实2816 ABI输入/原提示，原逐点计算不变，仅整数计数；同时给出原存储涉及行数与同顺序连续数组的保守行数上界。该值不是硬件cache miss或CPU收益，不在未计数前宣称缓存瓶颈。当前无新候选、树/点集合/数学/评分/默认均未改；有依据才交原CLI提出小布局适配。

F2v原工作量已回读：2816份真实输入共DFS899502叶/9535033顶点，原涉及7084261条64-byte存储行；按同顺序连续数组的保守上界4735042条。seed50876叶/600593点，对应456103→286682条。该度量不是CPU cache miss；原计数版12numeric/6flag/hint_out0差异、超16点叶0。

CLI28同native会话126.247s/success，返回纯make_candidate。SUPPORT_LEAF_PACKED仅对scalar seed/DFS叶使用geom.order顺序的拥有坐标副本；原points/order/tree、初始vertex0、witness、full_scan和全部数学/有限检查/同值索引保持。可选副本分配失败回原points，未组合旧quad/smallcache/leaf8。owner纠正说明中“单几何约950点”的无依据估计：实际17个mesh、198900个顶点，596700个binary64值，副本约4.55MiB。

私有原full-scan oracle正常/强制分配失败各9项、各96对照行均通过；实际所有596700个副本值逐位一致，强制失败时17个mesh副本全空、原数据仍完整。首轮复用测试harness漏kernel_sha256元数据，9项主体通过但tearDown报错，保留tree-readback-initial-missing-metadata.json；仅修复既有测试元数据后重跑，未删除或放宽任何原oracle。

2816真实ABI输入恢复原hint_in，原numeric/flags/raw hint_out/提交hint、macro-disabled和强制空副本控制0差异，实际10135626次叶顶点读取走packed。三对0.521978→0.483332、0.510603→0.476287、0.512787→0.476933s，effect −38.646/−34.315/−35.854ms，原screen=eligible_for_physical_ab。只表示局部通过，不当作整回合收益。

现已默认关闭接入原RoutePolicy/native build/station_executor/route_strategies/leaf_packed.py。67相关回归通过，含正常/强制分配失败的原full-scan oracle。集成default预处理同原c77d6ff、enabled同CLI原型；生产两库预热完成，实际2816输入再与原库逐位同值，NaN/Inf/零margin及原FE_DOWNWARD、FTZ_DAZ拒绝行为保持。未新增C ABI、内容锁或物理规则。

即将原nominal baseline→candidate两轮，prepared：experiments/colab-twin/output/packed-leaf-factory-20261023/f6ee53dd-c6ee-4ebc-af26-4aa23fdd5aa4/prepared.json。原90sim/120wall、完整视频与评分保持，用原run_pair量完整process wall/CPU及原timing分段；测量期间冻结全部源码/文档/HEAD与dirty路径，不改默认。两根已通知；无人机明确未开新仿真，FishBot明确已清理。未有本候选物理结果，只有有净收益才进已有第二工位。

### F2v 第一工位原物理2/2pass，进入既有第二工位

baseline a3dee934-9768-4a88-bded-30ba7c3e113d：74.78sim、53.338079全process wall、60.628044CPU；candidate 0853db70-beb1-41b1-a7a9-435c17216a44：74.82sim、51.413476wall、58.451418CPU。实测wall少1.924603s（3.6083%）、CPU少2.176626s，controller wall38.058793→36.428636、同线程CPU37.731216→36.080063。候选hold144→146拍（多2拍），其他阶段拍数全同，不把少等待当提速。

规划分列：transport worker wall1.061594→1.049835s，原route_search1.021650→1.006519s；separation worker0.530913→0.538116s，没有虚称所有规划都更快。原resolved输入、四XML、初始qpos/qvel、裁判与释放阈值均相等，实际native flags只差SUPPORT_LEAF_PACKED。两轮完整抓放/静稳/释放脱离/回位通过，safety=false、障碍0、free_object=true、weld=mocap=0、录像各468帧；释放漂移0.265805/0.265827mm、脱离后力0N。P95 25.794732→25.393870ms，仍有234/227拍超过20ms，50Hz未通过。独立回读在原pair目录independent-pair-readback.json。

按既有规则不凭单工位切默认。下一组是已有200/200工位candidate→baseline，prepared：experiments/colab-twin/output/packed-leaf-factory-20261023/bffaf73d-f3b7-4d15-9683-6fffabf16ab6/prepared.json。两库复用已预热版本，源/默认/裁判均不改，反转顺序；已通知两根继续串行占用，无并发机器人重实例。尚无第二工位结果。

### F2v 第二工位通过，采用工厂默认入口

200/200反序实跑：candidate f82a4d50-5d1c-4a60-b880-db919d68af42，77.10sim、53.916716全process wall、61.517536CPU；baseline 990054ff-077e-494f-b28f-7b5e2c387f4f，77.06sim、55.171011wall、62.905704CPU。两轮原pass，候选wall少1.254295s（2.2735%）、CPU少1.388168s，controller wall少1.083668s、线程CPU少1.021668s；sim反多0.04s，仍不是少等拍。

运输worker wall1.430474→1.342000s，分离worker0.706425→0.709473s，分别记录，不宣称分离加速。P95 26.773985→25.502755ms，超过20ms的周期245→241，50Hz仍未通过。原输入/四XML/初态/裁判/释放阈值与实际flags均独立核对；抓放/释放脱离/回位、零障碍接触及自由物体条件通过。完整读回在该pair的independent-pair-readback.json，两组原所有四轮与失败前代均保留。两组终态确认，已回告两根释放资源。

基于原局部三对一致、两既有工位反序全process/CPU/controller均下降，以及完整原裁判4/4通过，保留CLI28并在工厂入口采用。RoutePolicy()及baseline.py仍原版；DEFAULT_SOURCE仅指向leaf_packed.py，evaluate_station与直接station_executor.run缺省时复用同loader。显式其他旧候选仍按原字段缺省false，不自动叠加；底层native API缺省与全局模型不改。新增默认/原版分离及原失败透传测试，36相关入口测试通过。

当前验证唯一新内容是“不带--candidate”的默认入口：prepared：experiments/colab-twin/output/packed-leaf-default-20261023/e2c24c9a-1f6c-4c88-a297-27609bcedc13/prepared.json。单回合原90sim/120wall/评分/录像保持，不与前轮异时序数据算新收益。已通知两根串行占用一次；开始后冻结源码/HEAD/dirty路径，尚无默认入口物理结果。

默认入口4f59686e-4e80-4612-9d13-81521777b8e9已完成：原pass，74.82sim、51.695749全process wall、59.048693CPU。实际loaded_path/entrypoint均leaf_packed.py，preferences只开leaf_packed，实际flags仅加SUPPORT_LEAF_PACKED。抓放/释放脱离/回位通过，safety=false、障碍0、free_object=true、weld=mocap=0；释放漂移0.265827mm、脱离后力0N。默认与前轮显式候选3741拍trajectory所有字段按binary64字节完全相同，独立读回在该目录default-independent-readback.json。这是默认接线验证，不从51.696s再推新收益。进程结束，已向两根释放仿真资源。

默认升级的兼容收口：probe_episode_timing/run_probe及probe_native_abi默认显式传baseline.py，避免历史原版诊断被新的工厂默认选择影响；两探针可用--candidate显式测已采用版本。8诊断相关回归通过，原异常恢复和显式候选转发仍保持。此补丁不改物理执行或评分，无需重复原五轮物理。

Knowledge：updated。既有Wiki《ROS2 与 FishBot》第20节新增“性能微基准要保留真实调用状态”段，既有《开发知识入口》补hint_in/阶段覆盖/组件与整回合的入口。已读回原页410行与入口95行，确认来源是本项目ABI观察及原任务对照。保留该独立vault原有403行等未提交工作，没有覆盖或把它们混入本仓发布；本轮仅新增一段与一条入口，不宣称vault已提交推送。

当前本轮实现、五轮原物理、局部/默认/诊断检查与文档已完成；根Codex串行提交推送后继续读实际剩余热点，原裁判、计时、失败证据与原版复跑均保留。不追加20+20、训练、实体动作或无依据参数扫描。

发布已完成：e18f5802d6f1fee81824852b46b8745a942b9392推送原qiaoqiao2521/so101分支，GitHub REST及Git ls-remote独立读回一致。源与两个新增测试/候选文件均已入库；private CLI回执、全部原运行报告/录像仍留忽略目录，不提交运行时日志。发布时本交付仓库干净；独立Mint与原vault遗留均保留。

## F2w 已采用packed的实际编译后调用（2026-10-23）

沿已预热生产PACKED库的nm、objdump和相同严格flags的GCC unswitch报告核查，不凭源码猜已内联。实际保留leaf_vertex_interval_packed约1.6KiB独立函数；objdump有4处直接CALL（三个seed_extreme constprop路径、一处project内DFS循环），函数入口仍比较packed start/finish再选坐标源。前轮真实2816输入有10135626次packed顶点求值，不把该逻辑计数冒充硬件性能计数。

与旧CLI22“原scalar函数已经内联”属于不同源码。CLI29同native会话仅请求SUPPORT_PACKED_INLINE宏使这一现有helper在已验证GCC编译器always_inline，其他平台/关闭宏保留原路径；不改函数体、FPE/finite检查、加载策略或循环，不加SIMD。先与e18 PACKED父版比较，原非packed与disabled作等值控制；三对局部收益需胜过当前已采用父版，不能靠旧原版较慢掩盖子改动退化。当前CLI前台运行，尚无新候选或物理成绩，无owned重仿真。

CLI29已success/50.130s，只在原helper前加宏控制always_inline+inline。owner不采纳“没有inline关键字就是未内联原因”“必然消除empty dispatch”“函数体不变即可先称位等价”等泛化，实际检查编译后输出。四个原CALL在child均消失，parent/disabled各仍4处，主体/所有算术检查/迭代次序均未改。

私有验证初轮工具失败：本目录inspect.py遮蔽Python标准库inspect，NumPy导入报缺cleandoc，未形成任何候选或成本判定；记录harness-name-collision.json，仅改名probe_compiler_lowering.py并移除其自有pyc后重跑工具。生产版本及原五轮结果不受该私有命名问题影响；不是重跑成本挑绿。

正常/强制空副本原full-scan oracle各9项通过、全部596700个副本值同位。2816真实输入及原hint_in、原非packed、parent、disabled和强制空副本控制，raw numeric/flags/hint_out/提交hint及summary均同值；原FE_DOWNWARD/FTZ_DAZ拒绝保持，实际packed求值10135626次。原三对父版→child：0.477809→0.471918、0.479515→0.469166、0.477512→0.466503s，effect −5.891/−10.349/−11.009ms，原screen=eligible_for_physical_ab；只与已采用e18父版比，不拿最初原版掩盖子改动。

默认关闭接入packed_inline字段、原native flag选择及leaf_packed_inline.py，仅此显式源同时开packed+inline；默认仍leaf_packed.py。71相关回归通过，含原full-scan正常/空副本；生产parent预处理同e18、child同CLI原型，2816集成再同值、非有限/零margin/原两种算术拒绝同值。两库已预热，无重训/评分/物理改动。

下一组原nominal child→e18 parent，prepared：experiments/colab-twin/output/packed-inline-factory-20261023/e98e198d-3f69-47b9-9fe4-6c09b38892eb/prepared.json。label baseline实际source是leaf_packed.py（已采用父版），child是leaf_packed_inline.py，原baseline.py仍可显式复跑。原90sim/120wall和所有录像/评分保持，源/HEAD/dirty路径在整个pair冻结。有实际净收益才进已有第二工位；尚无本候选物理结果。

F2w首组已完成：child 7cb861f8-1abc-4408-bf7f-e8c0501e7142原pass，74.76sim、52.862758全process wall、59.864069CPU；parent 8b0cd05c-ab90-48b2-8dc5-cfe506cdb6b1原pass，74.78sim、53.339244wall、61.054488CPU。child观测wall少0.476486s（0.8933%）、CPU少1.190419s，controller wall少0.394674s/线程CPU少0.440362s；只少1拍hold，不将其视为全部收益。原输入/四XML/初态/裁判/释放阈值同值、实际flags只多INLINE，完整抓放/释放脱离/回位与自由物体条件均原pass。

如实保留代价：transport worker child1.166213对parent1.068233s、separation0.575688对0.559937s，两项都未提速；完整P95 child26.142244对parent25.818598ms，超过20ms周期250对247，尾部未改善，50Hz未过。此处只是一组成对观察，不据此切默认或作全部因果归因。完整报告在原pair的independent-pair-readback.json。

按用户要求进已有200/200工位反序parent→child，prepared：experiments/colab-twin/output/packed-inline-factory-20261023/28aa2baf-1b18-43cd-b0aa-cdebff7df2c5/prepared.json。无新场景/源改动，仍原90sim/120wall/录像/评分；下一组完成后综合总耗时、CPU和完整周期记录决定保留，不把首组少量正差称稳定收益。当前默认仍已采用e18 packed。

Knowledge：pending。候选经验是稀疏微基准必须保存每条真实hint_in，组件收益不替代全任务；后者已由Wiki《ROS2 与 FishBot》第20节覆盖。原Wiki及问题入口已有未提交工作，先保留，不并发改写。根Codex在本轮收尾协调后判断是否补充输入历史的适用条件；最短证据是本节native-abi.json与leaf8-replay-diagnostic.json。

### F2w 第二工位及采用结果

200/200反序parent→child两轮完成：parent 27d3e593-8291-4bf6-a9f8-d6dcc11e5dea原pass，77.10sim、56.511005全process wall、63.473038CPU；child e0f97eb3-f4a8-49e1-a47c-cd64d968c712原pass，77.08sim、55.244056wall、63.003495CPU。实测wall少1.266950s（2.24195%）、CPU少0.469543s，controller wall少0.937665s、线程CPU少0.923485s；hold158→157拍，其他阶段拍数相同。运输worker1.479782→1.416425s，分离worker0.717557→0.735930s，分离没有提速。P95 26.681323→25.946717ms，超过20ms周期280→268，仍不通过50Hz。

四回合原抓放、静稳、释放脱离、回位均pass，safety=false、障碍接触0、free_object=true、weld=mocap=0。第二工位原输入/四XML/初态/裁判/释放阈值相同，实际flags只多INLINE；释放漂移0.267470/0.267431mm、脱离后力0N、录像各482/482。独立回读保存于28aa2baf-1b18-43cd-b0aa-cdebff7df2c5/independent-pair-readback.json。owned进程已结束，已向FishBot/Drone归还资源。

三对局部与两个已有工位全process、CPU及controller均下降，保留CLI29并令DEFAULT_SOURCE选择leaf_packed_inline.py；leaf_packed.py保留e18父版、baseline.py与RoutePolicy()保留最初原版。只变默认source，不叠加旧候选、不改原裁判或物理。首工位P95与两worker回退完整保留，采用是当前观察到的吞吐收益，不宣称全部阶段更快、统计稳定或50Hz成功。默认路径转发和原失败透传已定向验证；不为一次source指针变更机械追加第五个完整物理回合。

本次回归命令误写不存在的test_probe_episode_timing模块：73个有效用例通过、1个模块加载失败。纠正为既有test_episode_timing后补验6/6通过；没有修改测试或生产源码来消除命令错误。原71项集成回归、两份原full-scan正常/空副本oracle与2816逐位证据仍在。git diff --check通过。发布前再次验证qiaoqiao2521用户ID238822818及原so101 fetch/push目标，不触碰Mint或独立vault。

Knowledge：already_covered。上一pending由本轮收口：Wiki《ROS2 与 FishBot》第20节及《开发知识入口》已包含真实hint_in、阶段覆盖和组件/整任务边界；本轮只是该原则的又一个实例，没有新增通用机制或修改独立vault的必要。
