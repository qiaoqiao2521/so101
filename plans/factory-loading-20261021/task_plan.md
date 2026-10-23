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

## 当前接续 F2g（2026-10-22，用户直接授权）

持续原CLI→小候选→最小局部判定→原物理对照→有益跨工位，不逐轮询问。优先054已实际运行，但两轮在运输前原wall超时；保留失败，不切默认，低竞争再测。当前做每次IK分配MjData的等值/成本筛选；CLI首无效输出已反馈纠正。

产品方向：八步执行仍未解耦，后续复用动作段；Mint作为同产品轻量现场入口，已有动作/导出先核对再接，不盲改22项遗留。共享root状态由原owner维护，本owner维护SO101源码与计划、候选来源、原结果和复跑。完整抓放原裁判不因最小筛选集改变。

## F2h 接续（2026-10-22）
已物理验证054两工位、reuse候选两工位及反向复核，均2/2原pass但总墙收益不稳定，默认baseline。下轮继续现有CLI+原CLI评测，先局部判定再原物理；不盲扫参数、不改评分。用户提出可组合动作/最小可判定集/Mint收口仍待，不得改固定模板冒充通用能力。

## F2i 能力段、最小判定集与产品边界（2026-10-22）

1. 程序入口新增 `pick → transfer → place` 能力段。旧原子程序仍兼容；能力段验证时展开为原八步，不复制控制器。当前只接受完整抓放序列，缺段、重复段、未知段在构造 MuJoCo 前明确失败。能力段0mm输入已完成原物理通过；原子程序兼容回归另有一轮wall超时，原样保留，不据此改功能或作性能结论。
2. `factory_minimum_suite.py` 只筛选并列局部测量，要求等值证据、至少三对、中位收益和逐对一致性；`eligible_for_physical_ab` 只表示可继续花原物理回合，绝不代表任务成功。局部淘汰可早停，原120s/90s完整裁判仍是晋级依据。
3. Mint 跟随器是同一 SO101 产品下的低配现场终端后端，保留产品动作、发布状态、执行记录与动作包。现有 `export_action_to_ros2.py` 是旧单位到 URDF 弧度及 JointTrajectory 模板导出，不是当前 MuJoCo 任意轨迹运行接口，也不证明导出轨迹可执行。
4. 轻量终端与 Lichtblick/ROS 工作台并行。当前工作台只接原 MuJoCo 工位任务；Mint 不是其前端替代品。首个融合点限定为版本化动作资产和结果语义，不直接导入串口配置、标定、登录记录、现场录制或业务日志，不将 ROS 强加给 Mint。
5. canonical `/home/muqiao/dev/ros2/projects/so101` 的 22 项受控变动与未跟踪源码/计划继续由原 owner 分项核对；共享交付仅记录归口，不提交、不清理、不恢复两份 DOCX 删除。


## F2j 分离规划重复查询与 SAT 轴构造（2026-10-22）

1. CodeBuddy/DeepSeek Flash 生成单条精确位姿距离缓存，owner补二进制键、结果副本和异常/形状边界；`reuse_separation_distances` 默认false。原同工位A/B已2/2通过，但旧13对缺逐位证据且有计时回退，新增三对逐位交替计时inconclusive，保留实验、不切默认、不追加跨工位抓放。
2. 保留所有探索批次和原筛选器判定；不只取最后有利批次，不改逐对一致性条件。复跑工具`probe_separation_distances.py`记录全部路径/样本/守卫/报告逐位等值和wall/CPU。
3. 下一候选只合并SAT九次cross构造。Flash返回429且exit0，未生成候选；沿用CodeBuddy的DeepSeek Pro实际返回源码，局部等值与原成本筛选正在执行。通过后才接原物理及第二已有工位；资源仍先与FishBot/无人机协调。
4. 动作能力仍仅完整pick→transfer→place；任意任务组合及Mint资产合同未交付，继续保护canonical在途成果。


## F2k 原准备状态（已由下节实际结果接续）

批量SAT轴候选已通过实际nominal/200-200局部成本与三个工位逐位等值；220-170成本不一致。128相关测试通过。下一项只接nominal原完整A/B（prepared见progress），当前FishBot实际占用；不因未回消息创建新的人工审批，不与活实例并发。default-off候选不会因本地绿灯或单次墙钟差自动切默认。


## F2k 最新结果与接续

干净5d1bc1c按原prepared的nominal完整A/B已2/2pass，候选全进程wall与CPU均增加；仅hold少2拍。原baseline保持，SAT不晋级、不扩第二工位物理。两进程终态/owned清理与原释放/录像已核，资源已回告FishBot。下一步复用现有CLI消费真实负结果，先量出主循环分段wall/CPU及同窗宿主状态，再生成有证据的小补丁；原物理和计时准则不改。

## F2l 原循环短诊断（2026-10-22）

1. 默认关闭的边界计时接入原run_physical_episode，记录独占wall与当前线程CPU。保留原执行器、评分、录像和90sim/120wall。短探针用既有cancel_check在100拍后停止，原fail/incomplete不改写（complete）。
2. 原nominal工位100拍无计时→有计时串行对照，轨迹所有字段相等；八组数值字段与初态逐binary64相等，视频各13/13。周期中位5.406ms，controller占总循环wall66.0%、物理18.4%。仅approach 2sim秒，不外推完整任务/50Hz或上轮变慢原因（complete）。
3. 独立100拍只剖原controller.update，显示_occlusion_warning的5800次包围盒投影及通用np.r_拼装是可测子成本。cProfile有额外开销，不作为候选提速成绩（complete）。
4. 原CodeBuddy/DeepSeek Pro生成像素包围盒拼装候选，5800个FK查询＋292边界逐位同值，三对局部改善18.24–20.34ms、原screen为eligible。但原遮挡预警在6.54sim秒结束，按前缀粗算仅约0.06s潜在整轮收益；暂不做完整候选A/B，不切默认（complete）。
5. 单次原baseline完整计时，原物理pass、74.78sim，3739拍全部轨迹字段与八组binary64字段同旧baseline，原场景XML相同。循环49.132s中controller39.465s；transport控制18.376s、close6.805s。P95 27.444ms、259周期超过20ms，50Hz仍未通过（complete）。
6. 只复算100条已记录运输认证输入：5800次checker、5500全夹爪扫掠状态全部通过。原CLI快照复制首版NameError已反馈原native会话修正，100绑定/30边界/持有副本检查同值；原三对仅省3.697/4.275/4.458ms，中位低于5ms，reject，不改阈值、不重测。比较器递归名称缺口已单独纠正，保留原成本（complete）。
7. FishBot物理占用期间，原CLI生成单一-fno-math-errno实验，私有编译/5500帧×285pair的12 numeric+6flag逐字节、非有限及异常浮点拒绝等值通过。三对成本均增加，中位+7.423ms，reject；不重测、不进原物理，默认继续baseline（complete）。
8. 5500条q6按字节全唯一，避免再做整姿态缓存。CLI15内联DFS栈保留vector溢出，数值等值但三对成本不一致、中位增加12.612ms，淘汰；原vector不改（complete）。
9. CLI17四顶点AVX2在原5500帧上逐位等值，三对局部收益13.3–14.5%、中位13.914%；runtime不支持时保留scalar。CLI18首轴加法消除比CLI17三对更慢，淘汰，不组合。四顶点已接入默认关闭的RoutePolicy与原评测入口，90相关测试及集成5500帧同值。原nominal完整A/B两轮pass，但全进程60.874→64.892s、控制器+2.432s，reject、不扩第二工位，不切默认；原90sim/120wall及裁判不改（complete）。
10. CLI19已success，未产候选；owner只采纳ns_evaluate_hinted加法计时，拒绝宿主归因、将transport控制误写为planning及新增10%硬门。200保存输入实际局部测量已完成（complete）。
11. 非轴向cache原5500帧计数319000次插入/0命中，159500个Frame中137500空、11000为13项、11000为16项，原raw字段/hints同值。CLI20仅尝试按需小方向表＋原unordered_map溢出；不取消缓存、不复用跨帧证书，原5500帧逐位与强制溢出同值，三对中位省5.561%、原screen通过；默认关闭集成与52相关测试完成，原nominal完整A/B两轮pass、实测全进程少2.170s/CPU少2.257s，等待反而多1拍；200/200反转顺序候选反而多1.224s/CPU多1.629s，四物理pass但收益不稳定，整体不晋级、不切默认（complete）。
12. 先对已保存200条guard输入量snapshot与immutable重复遍历，再将实测与原源码送同CLI，只考虑保持全部绑定/float位值/失效检查的一次遍历实现；CLI21未产候选，实测可消除份额有限且会扩大接口/错误顺序范围，原实现保持，未追加物理（complete）。
13. 只计数原scalar DFS已finite(bound)叶中重复顶点finite分类，核清可复用的现有证明；不删任何点或pair、不修改种子/见证/原full_scan回退；CLI22私有版本1324边界/5500真实帧同值，但一对成本+1.890ms，原screen=inconclusive，未应用生产或进物理。只查编译后新瓶颈，不重测挑绿（complete）。

14. 原树实际9642174节点界/1648430叶/17192933叶顶点；GCC已内联排除调用假设。CLI23据此只选择一个现有LEAF_SIZE值或拒绝，不网格扫描、不动原finite与裁判，CLI23只选8，实际1324边界/5500原字段与hint同值，三对中位省9.281%、62集成回归通过。原nominal2/2pass且3740轨迹全字段逐位相同，但候选wall多0.363s，未提速；不晋级/不跨工位，默认保持16（complete）。

15. 沿原baseline真实循环采native ABI各阶段wall/线程CPU及拥有的p/R/pairs/margin/hint_in。原裁判pass，151589次main-update查询占插桩controller墙钟62.6%，11阶段各256个真实输入。2816份基线重算与叶8结果逐位同值，但不改变叶8整回合无收益结论（complete）。
16. 同一online守卫端点复用：三次CLI修正均保留；最终200保存输入等值，但局部三对−14.451/+19.071/−13.849ms且绕过原FE_DOWNWARD拒绝，reject，不应用生产或追加物理（complete）。
17. 原_summarize实测整个组件估1.039s，不为此新建C ABI。CLI27盒子非轴直算204边界/2816真实输入同值，实际16676次分支覆盖；三对+2.325/+4.597/+5.379ms，reject，不应用生产或跑物理（complete）。
18. CLI28叶顶点连续副本：原点/order/tree/数学/索引/提示不变，可选复制失败保留原路径。2816真实输入、原full-scan oracle、67相关回归同值；三对局部省34–39ms。两个既有工位四轮原裁判pass，反序实测wall分别少1.925s/1.254s，CPU与controller同降，候选sim反而都多0.04s，保留有效改进（complete）。
19. 工厂默认source选leaf_packed.py，显式baseline.py及RoutePolicy()保留原版，其他旧候选不叠加；36入口相关回归通过。不带--candidate的原完整抓放pass，实际加载路径/flags及自由物体条件已回读，与显式候选3741拍轨迹逐位相同。e18f580已提交推送并经GitHub REST/Git ls-remote独立读回，诊断工具保留原版缺省（complete）。
20. CLI29仅内联packed helper。原独立oracle/真实2816输入和三对局部均通过；两个已有工位反序原物理4/4pass，相对e18父版全process分别少0.476/1.267s，CPU/controller均降。保留首工位P95/worker回退，工厂默认升级为leaf_packed_inline.py，原版和packed父版保留，完整50Hz未过（complete）。
21. CLI30排序/二分版成本不一致，淘汰；CLI31固定128直接索引修正原语法失败后，三对省25.482/28.606/47.049ms，82回归/2816集成raw/88份FP状态检查通过。两个已有工位反序原物理4/4pass，相对678父版全process少4.181/4.403s；剔除全部hold后controller仍少3.333/3.440s，非等待阶段拍数同值。默认采用seed_bound_direct.py，38入口检查通过，原版/父版/全部安全与90sim120wall保持（complete）。
22. CLI32同投影完整seed叶值复用：正常/empty/tiny原oracle各9/9，2816真实输入raw全同位、实际复用514020点。但原三对effect−1.521/−13.147/+1.099ms，原screen拒绝；未接入生产或新增物理，原失败/成本留证并反馈同CLI，不重跑同源码挑绿（complete）。
23. CLI33 Python全通过汇总：54边界/2816实际输出同值、三对完整summary调用都更快；64相关回归与原5项workspace检查通过。两工位反序原物理4/4pass，wall少3.377/1.121s，CPU/controller同降，第二3857拍轨迹完全相同。默认选择summary_fast.py，39入口检查通过；原C库/flags/汇总及父版保留，原评分/安全/90sim120wall不变，不单独归因全差或宣称50Hz（complete）。


## F2aa 完整50Hz长尾攻坚

- [x] 回读当前两工位原超时拍，分开controller、物理、回调、录像和worker。
- [x] 用保存的实输入核算闭爪/释放原扫掠组件成本，生成可证伪单变量。
- [x] CLI34等值候选原三对未达收益门，保留并淘汰；CLI35行为修复另按状态机反例和原物理验证，不伪造指令等值。
- [x] CLI35两工位反序原物理4/4通过；目标脉冲消除，但第二工位P95/整任务回退，仅保留default-off源。
- [x] 原DFS栈计数与CLI36固定inline32候选完成，28原边界/2816 raw通过，原三对中位更慢4.093ms，淘汰，不接生产/物理。

Next Step：核算批量执行原FK与原逐姿态证书的最小接入成本，禁止减244点或改原裁判/90sim120wall；当前无在途实例，默认保持summary_fast。


## F2ab 原扫掠批量执行

- [x] 本机MuJoCo 3.15.0官方头/库与model/data地址接口已核对，原kernel/lib不改。
- [x] 私有直接C-FK桥40实弦/失败前缀同值、原三对组件约21%更快；因错误作用域缺口未接入生产/物理。
- [x] 原Python FK保护版及生产40实弦/16边界同值，三对整guard可靠更快。
- [x] 默认关闭薄接入、133相关回归、两工位反序原物理4/4通过，完整墙钟/CPU/nonhold成本均下降。
- [x] 采用batch_configuration_sweep.py为工厂默认；77项默认/报告/原loader检查通过，保留原版和summary_fast父版。

Next Step：依据本轮余下close/release超时拍核验夹爪目标变化，再给原CLI一个连续目标策略；未实施，不降采样或改原门槛。当前P95 19.14/22.30ms且168/231拍超20ms，完整50Hz仍未通过。

## F2ac 既有时长内的夹爪目标连续性

- [x] 两工位实际close/release指令均一拍跳.485rad，首次原弦244/191点，133/163慢拍；完整扫掠仍保留。
- [x] 原CLI39首稿shape错误保留并反馈；CLI40修正，显式smooth_jaw_dwell默认关闭，84项相关回归通过。
- [x] 首对原物理因冻结last_command被演进指令改变而失败，保留并反馈CLI41，完整绑定保持；161相关回归通过。
- [x] 修正后同一nominal工位父batch→子连续目标原物理2/2pass，wall/CPU/nonhold均下降。
- [x] 同源码既有200/200工位反序原物理2/2pass，wall/CPU/nonhold也下降；采用smooth_jaw_dwell.py，父版及原版保留。

本候选有意改变开合目标，不能伪造逐位等值screen；所有完整闭爪预检/每拍实际弦、原6s+.6s等待、90sim120wall和评分保持。GitHub新账户token失效，e857f6e先本地保留，恢复登录后正常推送，不切旧账户。

Next Step：以本轮新基线复验既有refresh_leg_age，仅单字段改变。新实际最大三拍对应运输目标.62–.78rad跳变；旧summary父版的性能不一致结论保留，不无依据重测旧源码。新候选继续原物理两工位反序，未通过前不切默认。完整50Hz仍未过。

## F2ad 新基线的换段计时修复复验

- [x] 按F2ac原最大三拍定位；CLI42仅输出smooth_jaw_leg_clock.py，唯一变化refresh_leg_age=True。
- [x] 四项既有真实状态机回归通过，三条实际边界弦三对原guard都valid且成本下降；命令有意不同，不伪造output-equivalent裁决。
- [x] nominal父smooth→子换段修复原物理2/2pass，全process40.028→37.928s；剔除hold/release后同阶段同拍数仍更快。
- [x] 有收益后已有200/200反序原物理2/2pass，50.219→40.971s；同原规划路径，非等待同拍数也改善，采用smooth_jaw_leg_clock.py。
- [x] 原版/父版保持可跑，73项默认/失败透传/换段回归通过，完整50Hz仍未过。

Next Step：P95本轮13.371/13.447ms均在20ms内，但仍42/48拍超时。剩余hold/release占34/41拍；对原入口加标准cProfile诊断，保留原120wall/90sim。插桩成绩不冒充未插桩性能验收，未定瓶颈前不生成下一生产改动。

## F2ae 上下文遍历实际成本

- [x] 原同进程入口cProfile完成且原物理pass，7550次_sweep_binding、约392万递归冻结；不将插桩时钟作性能成绩。
- [x] 轻量只读观察器在原验证成功后捕获18类原输入/7762次阶段调用量，原完整抓放pass，原绑定字段与位编码保持。
- [x] CLI43仅将生成器遍历替换map；私有及生产构造两套原三对均可靠收益，153相关回归通过。
- [x] nominal父9340策略→显式map候选原物理2/2pass；wall略降，但CPU/nonhold/P95退化，无可靠整程收益。
- [x] 淘汰本轮晋级，不进第二工位；map保持显式default-off，原默认与所有失败证据保留。

Next Step：不盲目继续改采样或遍历。原剖析_start_transport/_start_separation单次累计.072/.117s，先核算模型复制与启动握手的主循环成本；验证GIL/所有权和小三对再决定候选。原入口补运行前后宿主机负载只读记录，计入独立诊断，不改裁判、控制时限或增加阻塞锁。GitHub登录仍401，待用户恢复后正常推送已有本地成果。


## F2af 控制窗口外准备独立规划模型

- [x] 原复制移入线程仍38ms，局部淘汰；同CLI已有草稿经根最小所有权审查，来源和429完整留证。
- [x] 位姿/旋转/独立所有权等值，生产3对启动间隙下降；120相关回归通过，默认仍旧父版。
- [x] nominal原物理2/2pass，准备与清理计入总wall/CPU；请求慢拍消除，但整程/CPU退化。
- [x] 已有200/200反序2/2pass，请求慢拍改善复现；整程仍慢，保持显式default-off，不切默认。

Next：剩余controller静态目标大尖峰先用GC回调只读对齐，不直接禁用或调整GC；原90sim120wall与全部安全标准不变。新CLI生成429额度耗尽，推送待新账户401恢复。


## F2ag 剩余控制器尖峰归因

- [x] 同原默认/原物理入口只读GC观察完成，原pass、GC设置不变、0回调错误。
- [x] 四个gen2事件与真实controller周期逐一对齐，21.5–58.1ms；其它长尾来源仍独立。
- [x] 用户允许当前GPT直接生成，已进入F2ah；原CodeBuddy429不再作为必需前序。
- [x] F2ah完成局部三对和两工位反序原物理4/4；GC仅显式候选，默认不变，完整50Hz未过。

Current：生产默认仍smooth_jaw_leg_clock.py。F2af四轮通过但整程未快，只保留可选；本轮4个A/B回合与1个诊断回合均实际完成，重仿真窗口归还。GitHub401复查仍阻塞push，有效代码与原计划本地提交保全，待新账户认证恢复后正常推送。


## F2ah GC实验与F2ai组合复验

- [x] 当前根GPT生成可选GC窗口，异常/原状态恢复及原case时限67项检查通过。
- [x] 记录第一探针覆盖错误和拒绝，原遥测分配重放三对验证目标长停顿；全成本不宣称稳定加速。
- [x] 两工位反序原物理4/4通过，GC清理/内存/新增慢拍和max退化均记录；默认保持。
- [x] 同显式GC父版只加已存在模型预准备：局部三对及两工位反序4/4原pass；启动峰值减少，但两处整程/非等待均退化，淘汰默认晋级。

Next：用原保存轨迹检查独立_fk只算运动学的输出等值和三对实际成本；碰撞/sweep、IK、物理推进与评分保持原实现，有局部收益才接原物理。GC组合保持显式可选，原默认不变。

## F2aj 独立FK查询

- [x] 核对旧2026-10-07失败原型，原样复用带全量回退的forward_pose_query，仅接FK不改IK。
- [x] 原型7538真实机器人姿态等值、三对完整helper；生产单变量及104相关回归通过。
- [x] 生产7538姿态/三对和原nominal物理A/B完成，原2/2pass；负载差异明确披露，不把整程15.42s全归因FK。
- [x] 同源码第二已有200/200反序原物理2/2pass，但整程/非等待退化，原来源一致性检查未过；拒绝默认晋级。
- [x] 原件/反证/实际源写回，保持显式；代码及首工位f28fc85已推，追加第二结论正常收尾。

## F2ak 扫掠重复工作计数

- [x] 按原采样及pair策略数11条保存弦；计划244和实测244的精确重复量分别259/285、44/285，未造缓存或追加物理。
- [x] 私有原C逐对归因，全部raw输出同位；44静态pair仅占实测约3.64%成本，淘汰大缓存方向，不追加物理。
- [x] 同一小样本定位高耗时对重复22次搜索后选同一Z方向；拒绝重复旧固定轴norm候选。

## F2al 当前姿态方向提示

- [x] 根GPT生成每次扫掠私有方向索引，复用原证书与原sb_run；冷启动/失败/不支持输入整次原查询回退。
- [x] 私有实际ABI2816输入/802560有效性判断一致，17个异常/前缀案例及独立200位Decimal顶点包络检查通过。
- [x] 正式接口101相关回归；11条实际弦773点报告/最终Data同值，生产三对CPU均明显减少；不冒充raw14字段等值。
- [x] 源码071987e固化后原nominal与已有200/200反序4/4物理通过，整对终态前未改源或提交。
- [x] 两处原对照来源检查通过，完整抓放/释放/脱离/回位、安全0；局部及两处同拍数CPU明显减少，采用direction_hint_sweep.py为新默认，旧父版保留。

## F2am 在方向提示父版复验已有模型预准备

- [x] 据F2al实际62/144ms规划启动尖峰，仅重用原preallocate_worker_models；不叠加GC、FK或改评分。
- [x] 同新场景三对原生产helper/原异步交接独立且同值，最大主线程空档102–117ms→.48–.68ms；总成本不稳定、两对增加，按启动时延收益准入，不当整体加速。
- [x] 原nominal及已有200/200反序4/4原pass，整程/CPU/两处启动拍均改善，采用direction_hint_preallocated.py，旧父版保留。
- [x] 记录nominal慢拍62→79反退及跨站42→12改善，完整50Hz未过；默认切换78项入口/原回退检查通过。

## F2an 新默认剩余长尾的只读GC观察

- [x] 原round46观察器只换显式新默认/输出；原物理pass，GC前后启用/阈值不变、回调错误0。
- [x] 四次gen2回收20.192/30.843/35.527/44.210ms与四个实际慢拍重合；全回合9慢拍，GC不是全部原因。

## F2ao 既有GC窗口在新默认上的显式对照

- [x] Root GPT仅新增direction_hint_preallocated_gc.py，复用原窗口/线程退出/恢复，57相关回归通过，默认不改。
- [x] 新真实遥测+旧18形状分配重放三对输出同值/CPU减少，但原wall screen=inconclusive；第二子无GC仍有190ms，反证保留。
- [x] 原nominal两轮物理通过，P95/max/慢拍改善；据此执行已有200/200反序，两轮物理仍通过但耗时与尾延迟回退。
- [x] 四项独立读回、原来源/评分一致性通过；GC清理计入总成本且状态恢复。两工位收益矛盾，拒绝默认晋级，保留显式候选与局部190ms反证。

## F2ap 原几何内核的本机编译局部筛选

- [x] 只在私有进程追加-march=native；2816输入/802560判定的raw数值、flags、顶点/方向提示逐位同，原源码/严格FP flags/bridge保持。
- [x] 11条真实弦773点报告/最终Data同值，三对中位只省.381ms，低于原5ms门，淘汰；不追加第二工位或整轮物理。

## F2aq 新默认完整控制器计数复核

- [x] 标准cProfile原入口回合d4933ea9原pass，source7ad3982干净；抓放/释放/脱离/回位通过，原planned/measured均244点。
- [x] 当前_sweep_binding7618次、不可变访问4099595次、snapshot3096746次；只作主线程计数/归因，47.468s插桩进程不作性能A/B。

## F2ar 上下文单遍快照与编码

- [x] Root GPT私有单遍原型，18旧捕获形状/7762真实阶段次数及34边界/复制/正负零检查同值，三对局部wall一致减少。
- [x] 正式默认false的fused_context_freeze只改变当前_sweep_binding预处理与该次构造；异步绑定、owner/阶段/有限值/位身份检查保留。185相关回归通过。
- [x] 正式完整构造器三对wall1.757154→.717590、1.782356→.781854、1.728119→.702169s，原screen eligible；不是当前唯一在线样本或物理成绩。
- [x] source fbaea07固化后nominal与已有200/200反序4/4原pass，原来源/评分一致性均过、244点全保留。
- [x] 两站总process/CPU及各自同阶段同拍数CPU改善，采用direction_hint_single_pass.py；原父版保留，完整50Hz未过。

## F2as 标量布尔臂检查的方向搜索局部核算

- [x] 私有500实际q6原_arm_valid布尔/最终FK相同，三对wall98.590→77.464、99.207→87.047、109.622→71.840ms，原screen eligible；只复用方向索引，每次重新求证。
- [x] 默认关闭的最小生产接入，240相关回归通过：失败/异常/重入/观察者/缺符号回退保持，只选_arm_valid布尔接口。
- [x] 正式500姿态三对wall112.987→84.100、109.520→83.315、113.387→80.245ms，布尔/最终FK相同，原screen eligible。
- [x] source9e3bf73原名义父→子2/2物理pass；同3264拍CPU23.119→23.672s回退，收益不足以晋级，淘汰且不追加跨站，默认保持。

Current：默认compact_status_json.py；direction_hint_preallocated.py/方向提示/smooth父版均保留。GC/pose_only_fk默认关闭，完整50Hz未过。F2ar两工位4/4通过并采用；F2as原物理安全通过但等工作量成本回退，已淘汰；F2at先筛选状态JSON序列化热点。全部在途检查终态后才提交。GitHub新账户与3067命令级代理正常，绝不向「登录 X」发消息。

Current：GitHub新账号+命令级3067代理已恢复，ba9bc82远端读回一致，b3e839a已正常推送；CodeBuddy不再阻塞生成。本对话串行使用实际空闲仿真资源，原runner逐case检查，等待单独计量；绝不向「登录 X」发送消息。

F2as生产接入：默认关闭的标量方向索引路径与9项新边界回归已完成，240相关检查通过。正式500姿态三对组件待原资源等待结束；未启动原物理、未切默认。最短入口：private round58-scalar-direction/production_probe.py，再prepare_physical.py与既有round10 run_pair.py。

## F2at 状态发布序列化局部筛选

- [x] 原profile482次状态写入热点；私有同482次三对wall.996→.306、.981→.285、1.021→.258s，解析值/原错误边界保持，原screen eligible。
- [x] 最小生产compact_status_json默认false，仅status发布选紧凑编码；全部字段/频次/原子替换/非有限值拒绝保持，64相关回归通过。
- [x] 正式组件同482次三对wall.819→.225、.871→.232、.901→.258s，解析值/原失败保持，原screen eligible。
- [x] sourcea846fe7原名义父→子2/2pass，244点/评分保持；原始94.375→51.817s受宿主重负载变化干扰，未认定42.558s算法收益。
- [x] 第二已有200/200反序2/2原pass；38.628→37.426process-s，剔除hold/release/lower后同3236拍CPU24.450→23.279s，保留release慢拍15→24反证。
- [x] 两站4/4物理安全及三对正式组件通过，采用compact_status_json.py；原single-pass父/原版均保留，91默认相关回归通过，完整50Hz仍未过。

## F2au 新默认的当前调用归因

- [ ] 现有F2aq profile早于单遍上下文和状态JSON两项采用，先复用标准cProfile与原evaluate_station做一次当前默认计数，保留原物理/244点/90sim/120wall。插桩秒数不作性能或50Hz成绩。
- [ ] 从当前热点与调用方选择下一项局部探针；原C方向列表已经是固定19项数组，不重写已存在能力，不复跑已淘汰的标量方向/GC/编译候选。
