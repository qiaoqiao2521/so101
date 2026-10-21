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
