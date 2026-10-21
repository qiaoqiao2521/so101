# F2 厂区工位上下料

## Goal
交付可导入、可编辑的单刚性工件托盘→抬高目标盘任务，完成真实夹起、搬运、放稳、脱离和回位，提供原物理评测入口。

## Scope
复用MuJoCo、IK/OMPL、station_executor、原网页和评分；新增place世界Z作为目标盘底座高度，默认0保持原场景。蓝盘底座、实际/规划XML、释放高度、预览和原放稳指标一致。先选10mm抬高，保持同一方块、盘尺寸和原八步语义；不可达/非法高度明确失败。

## Ownership
根Codex维护场景/Station适配、可调用评测、场景JSON、整合和此三文件。控制worker独占控制器/异步快照与相关测试；评分worker独占learning_env/placement与评分测试；UI worker只改隔离worktree /home/muqiao/worktrees/fishbot-f2-workcell-20261021 的RobotStation与专用验收。共享工作台edf61a2以后无人机工作原位保护，不重启公共服务。研究总三文件和PROJECT由F0根维护，本任务不修改。

## Plan
1. 高度语义贯穿场景、控制和评分（complete）。
2. 导入/编辑/保存UI与代表性配置（complete）。
3. 定向回归、原0高度API复验、新高度完整回合和明确拒绝案例（complete）。
4. 原评测JSON入口、文档、本地提交、限定canonical同步、推送和远端读回（complete）。

## Acceptance
物理裁决保持双指真夹持、物体位移、实际目标盘接触与静稳、释放净距及完整回位。记录场景/任务ID、运行方式、加载候选引用、裁判版本、单位、原裁决、失败原因和产物路径；未运行或缺裁判不记成功。策略演化只允许控制器/规划实现，不允许修改场景/评分/阈值冒充改进；不用内容哈希限制手工编辑。

## Next Step
用户从5192导入高盘任务并修改高度；后续新高度逐任务验证。共享无人机树保持原owner。

## F2b 最小路线策略插槽（2026-10-21）

范围：候选源码只生成运输高度偏好、原脱离路点前缀长度及IK初值选择；仍运行同一evaluate_station、模型、物理裁判与安全阈值。不改学习/50Hz/长扫掠主线、不改前端或研究总文件。

1. 复用现有transport/separation快照，接入不可变路线配置（complete）。
2. 定向检查实际候选加载、非法配置明确失败、worker配置保持（complete：91 tests / 104 subtests）。
3. 原0mm/10mm各baseline/candidate一轮，串行完整物理评测（complete：4/4原裁判通过）。
4. 对照结果、最短命令、限定同步、提交推送（complete）。

Next Step：F2c两轮CLI生成→实际评分→反馈接续已完成，本轮6/6通过；默认仍为基线。候选2原高度局部缩时仅单次观察，若要选优需另行成对复验。

## F2c CLI生成候选接续

厂区根用现有CodeBuddy、关闭工具访问，在私有cache生成首候选。本SO101对话维护接口与评测，并将实际反馈送同一前台CLI生成下一候选；每次先审查route_preferences范围，再协调窗口实际运行。不把手写shorter_route冒充CLI生成成果。

F2c执行：
1. 根生成候选与本对话只读范围审查（complete）。
2. 首候选两盘高实际评测及raised baseline→candidate交替复验（complete：4/4原裁判通过）。
3. 同一CodeBuddy前台CLI使用实际反馈生成第二候选，并在两盘高实际评测（complete：57mm/10点/continuation，2/2原裁判通过）。
4. 保留生成解析失败与错误说明；关联实际源码/receipt/原结果，不晋级默认策略，限定同步与交付（complete）。


## 后续候选与接口边界

根独立审阅六回合后，已将第二轮实际结果和说明错误反馈给同一前台CLI，第三候选57mm/9点/continuation已生成。当前暂缓/not_run，不自动追加仿真或晋级：其收益假设仅再缩少量脱离段，生成说明还混淆持物时长与hold阶段。先保留原owner固定的独立布局复核；再视需要比较现有认证运输高度的motion_duration，评估从“首个可行”扩展到“原认证路线中最短时长”的最小选择接口。仅列计划，未改模型、评分、执行器或原阈值，不恢复训练/50Hz/长扫掠或创建新平台。

## F2d 独立XY变体复核

根接续授权先验证独立配置，不实施路线排序扩展，不重跑原六例。

1. 固定`scenarios/factory-loading/layout-place-220-170-0mm.json`：蓝盘XY从(0.24,0.14)改为(0.22,0.17)m，Z=0；方块、原障碍、其他节点和八步程序不变（complete）。该目标有历史原执行通过记录，但尚未用于本轮候选比较。
2. 用原`validate_station`静态解析，读取实际baseline与候选2路径/偏好，准备同fixture两条准确argv（complete；未导入MuJoCo，未启动浏览器QA）。
3. 在无人机明确释放的两回合窗口中串行baseline→候选2（complete：2/2原物理裁判通过）。候选只读同一输入，不改fixture/裁判/阈值；保留原失败。
4. 回读原场景/报告/轨迹和分段差异，两个subprocess/runner终态与owned清理确认，立即回告两根归还窗口（complete；文档交付随当前收尾）。不按小差值晋级；此处仅独立放置目标复核，不宣称跨布局泛化或20+20。

准备产物：`experiments/colab-twin/output/independent-layout-20261021/92c6ff57-e579-4355-bdf4-069d5fc05100/prepared.json`。共享窗口先由无人机规划构建/ground对照、FishBot已排定occupied direct占用；本owner仅静态配置与文档，收到明确窗口前不运行物理。


## F2e 可选少量认证路线的原时长选择

根在独立回读F2d后授权下一软件切片。实现、纯软件合同检查及原物理A/B均已完成，窗口已归还。后续一次文本反馈已完成，无新物理窗口。

1. 复用_transport_at_height完整认证与原motion_duration；增加RoutePolicy.transport_candidates，默认1完全保留首个可行；显式2/3时比较前N条完整可行路线，按原五段运动时长+原每段0.6s到达守卫选择，等值保留原顺序。
2. 既有高度列表、失败回退、未知错误/取消传播、快照上下文、90s/14s预算与原物理检查保持。若可行路线不足N条，保留已认证者；无可行路线保留原失败。
3. 报告每个实际尝试的认证耗时/原规划时长、最终选择及整个搜索墙钟；复用原异步worker的等待/墙钟计量，不隐藏额外规划成本。只增加评价JSON的诊断透传，不改裁判。
4. 已用不构造MuJoCo模型的合成路径/桩认证完成42 tests / 62 subtests；覆盖：默认不多搜、较短者选择、仅完整认证可参选、回退不足N、等值稳定、未知错误传播、快照绑定新字段与时间记录。当前禁止模型编译、重native、ROS/build或浏览器QA。
5. 新策略已在无人机另给的两回合窗口完成A/B（2/2原物理通过，但额外计算使总sim增加0.70s）；默认仍为1。不重跑旧八例、不自动晋级或修改场景。不重写规划器、不新造调度平台。


F2e软件产物：RoutePolicy新增transport_candidates=1（默认首条），允许显式2/3比较；_compute_transport复用原完整认证与费用，只在完整通过结果中稳定取min。route_search/attempt诊断透传evaluation。手写示例route_strategies/shortest_two_routes.py只设2，并非CLI生成；其后原物理A/B已2/2通过，但本布局负收益不晋级。准确未来A/B命令与纯软件报告保存在`experiments/colab-twin/output/route-selection-ab-20261021/9d8a71f1-d133-41a5-922e-b0957c261237/prepared.json`。该A/B已实际完成并归还窗口，负收益不晋级；旧八个物理回合不重跑。


F2e实际对照：baseline认证1条、shortest-two认证2条后都选60mm；第二条57mm原费用更高。两轮原物理通过，但候选hold+0.70sim s、worker+1.155632wall s，无路线收益，不晋级。根接续授权在同一前台CodeBuddy DeepSeek CLI仅做一次文本反馈，允许返回可证伪候选或明确无收益/转向理由；优先说明何种已有任务条件值得检查，不盲追hold噪声、不故意削弱基线。该后续不追加物理/native/服务，下一回合另约。


## F2e 负收益文本反馈已完成

原pair审计已提交推送8ad596f后，同一前台CodeBuddy DeepSeek只调用一次（21.8845s、success、source=null/no_candidate）。接受“当前pair不提出新可执行候选”这一范围内决定，默认1保持；不采纳它关于参数空间已耗尽、无更短前缀、neutral已验证或箱体可生成新detour的错误/无证据断言，不新增前序成功门锁或固定盈亏阈值。

仅保留待核条件说明：已有placeXY可改变关节路径费用；历史已执行(.20,.20)m可作为将来原owner选点的参考，但当前没有新fixture/模型编译/物理任务，不承诺首可行会劣于下一条。需要的证据是同一固定任务中至少两条原路线完整可行、原费用有实质反转且端到端节省能覆盖实际额外等待；附加障碍只可能影响当前固定走廊可行性，不自动产生新XY绕行。本切片到此无待运行回合；新的行动由后续明确范围与窗口接续。


接续最短入口（当前不执行）：先读本计划F2e结论、`progress.md`末两节和忽略series的`model-feedback-round4.json`；round4 source=null，没有新候选可运行。由原owner选定下一项业务任务后，复制现有Station配置并只做原validate_station静态解析，用原load_route_policy检查单变量候选，生成新的UUID输出目录及baseline/candidate准确argv。不得复用已完成9d8a71f1的pair-results或将旧回合当下一轮。场景由owner固定，候选只读同一输入，仍沿现有前台CLI/原evaluate_station，不设前序成功门锁、不另造平台。当前窗口仍归无人机，未释放SO/F1；新的原物理回合另获明确窗口后执行。


## F2f 第二放置工位静态准备（2026-10-22）

根明确只做软件静态，固定历史曾执行的placeXY=(0.20,0.20)m、tray0mm，与220/170形成两个业务放置工位；不是为了制造优化胜利的新障碍布局。

1. 新fixture `experiments/colab-twin/scenarios/factory-loading/layout-place-200-200-0mm.json`，只改place.position、名称和说明，原八步程序/方块/障碍/裁判保持（complete）。
2. 原validate_station解析两个工位，逐项记录相同/不同条件；真实load_route_policy读取baseline及原CLI候选2，缺省transport_candidates仍1（complete）。未导入MuJoCo，未构造模型，未发新模型调用。
3. 保存可复跑argv、EGL环境与独立UUID输出根（complete）；准备时为physical_not_run，后来根明确窗口内的两回合已原物理2/2通过，不以静态合法推导泛化/性能。
4. 静态交付5822529已完成最小检查/限定同步/提交推送及回告；后续根授权的两回合也已终态清理并归还。当前仅备下一静态提案，新物理另约，不加平台/门禁或baseline前序成功要求。

记录位于忽略series `experiments/colab-twin/output/station-family-20261022/6c536ef6-e8a1-4846-82cb-c22d474726eb/`：prepared.json含原入口两条准确argv，condition-comparison.json含全部节点/程序/父坐标差异，cli-candidate2-source.py保留原候选文本副本。执行owner仍为本SO101原对话，根协调后续窗口；当前不物理/ROS/build/浏览器QA，也不构造MuJoCo模型。


## F2f 当前实际结果与下一静态方向

根明确给的两回合窗口已执行完：干净5822529、同200/200/0mm输入，baseline/旧CLI2均原完整物理通过（77.04/77.00sim秒；81.985/111.061wall秒）。两者实际同54mm运输、25.615mm脱离；差仅hold -0.04sim，默认不变。两个subprocess/runner终态与owned清理已核，立即向根/无人机归还，无扩批次/新模型调用。

根在独立读原数据后仅要求下一静态方向，已备手写`route_strategies/prefer_054.py`：只改transport_preference_m为.054，其他维持baseline的13/continuation/1。目标是减少当前已测失败的60mm/57mm端点IK尝试，非缩短运动路径。原loader与已观测高度顺序重排检查通过，备选不删除、完整认证不省略。静态prepared和原评测A/B argv位于`experiments/colab-twin/output/prefer-054-static-20261022/0075f323-8e42-4e49-947e-34bd91db3ef7/`；该新提案physical_not_run，未构造模型，需另获范围/窗口才运行。不扫参数，不改judge，不据单次端点耗时承诺总收益。
