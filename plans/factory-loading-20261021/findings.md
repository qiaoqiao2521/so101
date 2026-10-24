# Findings

- 当前SO101交付基线15fa5bf干净，已验证XY目标参数化；评分读取实际蓝盘XY但静稳中心Z固定.01m、释放支持判定固定.025m。
- 目标盘基准底面0、地板顶面.002m、18×18×16mm方块静稳中心.010m；新增place Z定义为相对原桌面的底座高度，所有Z阈值作坐标平移，容差保持。
- 共享工作台当前edf61a2已加入无人机并有独立owner持续工作。F2使用其同源隔离分支，不覆盖RobotStation进行中修改、不重启共享5186。
- 采用Wiki《ROS2与FishBot》第20节：动作结束与独立物理评分分别验证，评价条件不由候选修改；既有接口/GUI复用。

- 10mm目标盘单回合实测支持链路成立：实际floor顶面.012m、最终物块中心.0199607m，释放估计.020m，回位误差约.102mrad。原先默认37mm脱离偏好在该姿态不可达，已有逐段认证得到28.462mm安全脱离后验证直接回位；未新增固定高度补丁或放宽检查。
- 5mm额外编辑变化（10→15mm）可在网页保存/刷新后保留，五块蓝盘几何同步；该15mm只作编辑验证，没有物理成功结论。
- 统一评测入口以原report.passed与任务终态共同判定；取消或缺物理报告都不能计pass。负高度明确失败、未评分，不把拒绝计为抓放失败样本或成功。
- 原工作台生产构建需要workspace局部依赖：theme DataGrid固定6.18.7，顶层7.24.1不可代替。独立复制完整既有安装后构建通过，保持上游版本和源码。

## F2b 策略选择

复用现有transport/separation快照，以冻结RoutePolicy仅携带三项偏好。候选源码在evaluate_station实际执行，worker只接收选择结果；没有新增插件框架、裁判、模型或内容锁。shorter_route是候选名，不是性能结论：实测4/4通过但运输规划时长稍增，仿真总时长仅少0.20/0.04s，高盘wall增9.128s，不自动替换基线。

F2b只读阶段拆分：原高度候选transport增加0.18s、separate减少0.32s、hold减少0.06s，总减少0.20s；高盘transport增加0.10s、hold减少0.14s，其他段相同，总减少0.04s。hold包含异步规划等待，这些单次总时长小差异不能当成稳定路线优势。stage-timing.json保存于原series目录，未改变物理裁判。


F2c首个CodeBuddy候选57mm/13/continuation实际两轮通过。nominal运输改成57mm但motion_and_arrival比60mm基线长约0.0569s，总sim相同；raised首选67mm恰为基线70mm IK失败后的同一路线，运输规划28.3197s、脱离28.462mm亦相同，总sim少0.10s不能归因路线优化。下一候选必须接收实际采用路线和不确定性，baseline保持，微小差值用后续交替复验审查。


F2c反馈轮次已实际闭合：同一前台CodeBuddy工作流消费首轮原物理结果，生成57mm/10点/continuation独立候选，并在两盘高通过。raised交替baseline→候选1为74.38→74.30sim s，全部差在hold；候选2raised74.32sim，比候选1复验多0.02s，亦只有hold差。候选2nominal相对候选1transport不变、separate少0.32s、hold多0.04s，总少0.28s；这是可复验局部收益，不能从单次观察宣布全任务稳定提速。默认基线保留。

第二候选生成说明误述nominal实际高度，且附带未经核实的clearance/因果断言。保留原输出并用实际worker日志纠正：57mm而非60mm；只接受原RoutePolicy范围内的字面量源码，未把生成说明当评分或改写原裁判。后续改进先看实际采用路线、逐阶段时长、独立重复结果，而非仅看CLI退出或总wall时间。


候选3文本反馈误把持物累计31.6s当hold阶段；实际hold2.86s、approach16.58s、transport25.76s（raised候选2）。生成式解释即使已纠正上一轮高度错误，仍须与原分段数据对照。当前三参数只重排运输高度/截取脱离前缀/换IK初值；_compute_transport首个可行即break，费用统计在之后。若扩展，最小方向是复用原全路认证和motion_duration做已有可行路线排序，并计入额外规划耗时，尚未实施。


F2d固定输入只移动蓝盘XY到(0.22,0.17)m，保持高度/方块/障碍/程序。该XY在历史原执行器通过，作为已知可达范围选取；并非完全未见目标。当前原validate_station仅确认输入/父坐标与支持边界，未导入MuJoCo，不能当成当前候选物理通过。基线与候选2两条准确命令共享同一fixture，等待资源窗口后由原裁判独立复核。


F2d独立XY220/170两回合原裁判均通过；候选2较基线少0.22sim s，但原运输规划时长增加0.021567s，总改善主要来自短脱离和hold变化。默认基线保留。当前_transport_at_height已经全程认证，motion_duration已经统一；缺口仅_compute_transport首个可行即break，尚无可选的少量认证路线费用比较，适合只改该外层选择。


F2e无需新增规划器或worker协议：现有完整认证与motion_duration可直接复用，RoutePolicy的items快照也自动携带新字段。缺省transport_candidates=1保持首可行，显式2/3稳定选原费用最小者。额外认证开销属于原worker墙钟和实际hold阶段，单独route_search诊断是其子区间；不可拿较短规划时长自动推断更短端到端任务，也不可重复加两个墙钟。42项纯合同/62子测试不替代新物理A/B。


F2e物理A/B证明额外认证成本可见：两条认证后仍选60mm（费用28.998937s），57mm更慢（29.020504s）；hold2.88→3.58sim、worker1.156478→2.312110wall，动作段全同。默认1应保留。比较更多完整可行路线只提供选择能力，不保证当前固定走廊存在更优路线；下一文本反馈允许无候选，并要求先说明现有任务条件如何产生可测路线收益，不能故意削弱基线。


负收益反馈模型返回no_candidate可作为当前pair决策，但其解释仍含新错误：短前缀并未消失、neutral没有物理排除、固定五段走廊不会因加箱体自动生成新detour。已保留原模型输出并逐项纠正，无新物理或前序门锁。接下来有意义的路线收益条件应是原任务改变IK/关节路径费用，至少两原高度完整可行且费用排序实质反转，并覆盖真实认证等待；当前未证明有这样的新点，不自动建任务。


2026-10-22 F2f第二业务放置工位固定200/200/0mm；与220/170相比仅placeXY、名称说明及相应父坐标派生点变化，原八步/方块/障碍/阈值保持。原parser和实际baseline/CLI候选2 loader通过且mujoco未导入；历史同目标执行记录不代替当前可达或收益证明。本轮没有新模型调用或物理任务。


F2f200/200原物理2/2通过，但旧CLI2与baseline最终都回退到54mm运输、25.615mm脱离；仅hold少两拍，wall反增，不晋级。已测的可避免工作是先做两个失败的60/57mm端点IK。下一静态手写prefer_054只重排该高度优先，保留全部回退与完整认证，明确未运行；它不承诺运动变短或总时间更短，也不按未知宿主墙钟原因解释收益。

## 2026-10-22 F2g实际对照与范围纠偏

0075f323实际两回合均wall_time_limit且未进入运输；不是054收益或退化证据。阶段日志与planning条目不是同一事实：前者包含approach/descend/close，后者仅已有接近规划。原超时保持。高主机负载仅相关证据，process CPU未采集。

优先筛选候选的等值与局部实际成本，通过后才完整原裁判及第二已有工位；淘汰可早停，成功不能靠早停认定。Mint产品动作/发布/运行记录和已有ROS2导出可复用，官方单位与URDF/MuJoCo弧度分开；现有导出不支持运行时任意多点模板。canonical 22 tracked改动及私有数据保持，owner核对后分项收口。详见progress F2g。

## F2h 实测边界
054只在已知200/200减少失败端点；220/170完整任务无收益。相邻validity复用局部减少147/146次几何调用，但三组完整wall无稳定一致收益，故默认false。候选profile只在冻结worker、单一精确状态、原callback完成时复用；不得跨线程或把wall candidate/base轮次当固定节省。原裁判与所有物理同条件。

## F2i 能力与验收边界

`station_executor` 的固定八步是执行实现，已不再要求用户只能提交八条原子动作。新增能力段只提供意图编译：`pick` 展开为首四步，`transfer` 展开为第五、六步，`place` 展开为第七、八步。验证输出记录 `mode/segments/steps`，执行仍调用同一控制器、评分器与物理场景。当前范围是完整抓放能力复用，不是任意机器人技能编排或部分任务执行。

局部判定工具为每对测量保留来源、原verdict、`output_equivalent` 和实际耗时。不同输出、任一原失败、样本不足或中位收益不足均停止；逐对墙钟不一致则 `inconclusive`。`eligible_for_physical_ab` 不是成功或提速结论，只允许继续固定工位完整对照。

能力段0mm工位原物理回合 `1fccf040-0dc6-49e7-9502-37e071273bb1` 通过：输入模式 `segments`，展开为原八步，74.78sim/60.748wall秒。实际抬升41.272mm、持物31.42秒、静稳7.52秒；最终物块中心 `(0.238631,0.139046,0.009961)m`，释放脱离于67.44秒、最大XY漂移0.265805mm、脱离后接触力0N；回位完成，录像468/468帧。同坐标的原子版兼容回归 `416351fe...` 在57.90sim/121.276wall秒超时，仅执行到搬运后的lower早期，证明不能把该轮失败归因于能力段编译；两轮相邻却不能作性能A/B。

Mint 跟随器已有低配现场动作资产产品，研究工位已有 Lichtblick/ROS 实时执行与历史回放。二者共享 SO101 品牌和动作/结果术语，暂不共享运行协议。关节轨迹导出不能作为当前 MuJoCo 运行接口；后续接入须另做单位、加载与物理验收。


## F2j 分离查询的确定性收益与计时边界

原分离worker每次验证垂直边终点后，再对同q6查询距离；相邻边起点也重复。真实名义快照233次请求中27次可精确复用，全部205个保存样本保持。距离函数同时更新pad_vertices依赖的MuJoCo姿态，因此缓存须限定同冻结worker、最后精确shape/float64字节；异常可能已改姿态，下一查询必须失效旧键。

原三批探索共13对中位差-23.398ms，但有+16.687ms回退；旧比较只有Python数值等值，严格筛选因缺逐位证据reject。即使假设逐位等值，计时逐对一致性也未通过。只取最后5对或改用median-only会误称准入，已回收全部结果纠正。后续三对反向交替、逐字节输出比较也inconclusive。完整物理首对2/2pass只能证明当前工位行为，不能证明稳定整回合收益；sim差0.02s仅hold少1拍，分离阶段样本相同。


## F2k CLI生成的批量SAT轴候选

CodeBuddy/DeepSeek Pro实际输出将9个a-major/b-minor叉积合并为单次广播；生产数学body与CLI源码AST相同，仅重命名和docstring不同。原逐轴范数、1e-10跳过、归一化、投影和max保持；原box_separation仍保留。ReleasedObjectQuery新增显式选项，仅冻结分离worker用partial开启；主控制器/实时检查默认路径保持，独立reuse缓存关闭，避免多变量。

当前三已有工位全部路径/205或191保存样本/距离/守卫/数学报告逐位等值。原nominal集成三对中位-46.035ms、200/200三对-39.106ms，均逐对wall下降；220/170中位-77.351ms但一对+16.477ms，原成本筛选inconclusive。全部wall/CPU原值保留，不将最初CLI探针的较大绝对差外推；该探针未记录宿主频率，不能据此描述低频或争用原因。完整任务待原物理评测，默认保持baseline。


F2k后续原物理结果：两轮pass，但SAT全进程wall70.320→104.705s、CPU76.865→106.869s，分离worker也未兑现局部收益。未改运输worker同时变慢，说明现有记录不足以单独归因SAT；同场景、评分和初态已核，不等于已控制整个宿主条件。保持原默认，不扩完整抓放。下一项应测原循环分段wall/CPU和同窗宿主条件，先用短探针取得可区分假设的证据，不能继续只比较hold帧或挑有利计时。

## F2l 实际成本分布与局部候选退出

原循环默认关闭的分段计时已有短对照与完整物理证据。100拍有/无计时全部轨迹相等；完整3739拍与旧原baseline所有字段、八组binary64及两场景XML相等，原抓放/释放/回位pass。短段5.41ms中位不能外推完整周期：全轮P95 27.444ms、259次超过20ms，50Hz仍失败。

完整循环49.132s中控制器39.465s（80.3%），运输控制18.376s、闭爪6.805s；物理＋2ms守卫5.448s、诊断2.494s、callbacks1.416s。录像收尾1.408s，非本轮主要瓶颈。计时用wall和当前线程CPU；evaluate调用区间不含探针导入/最后写报，不是全进程。外层全进程时钟缺失就留null，不能与旧全进程结果计算收益。

100条真实运输输入的局部guard-core复算含5500个完整夹爪扫掠状态、5800次checker，全valid；这里部分控制上下文重建，不是完整update回放。剖析显示原native认证计算占主要成本，不能以删夹爪采样、重用过期认证或改变闭爪物理来冒充实现提速。

CLI12像素拼装保留6092输出逐位等值、原三对局部改善，但只作用于前6.54sim秒，暂缓完整A/B。CLI13数组快照修正缺失导入后，100绑定与30边界/副本所有权等值；原三对中位仅省4.275ms<5ms，淘汰。局部比较器抽取函数的递归名错误已单独修正，原计时未更换。两候选均未切默认，完整闭环和测试通过不能据此宣称算法提速。

CLI14单一-fno-math-errno编译实验在5500帧×285pair的原始字段与异常环境拒绝上等值，但三对summary成本全部增加，中位+7.423ms，因此不进完整抓放。原缓存的机器码检查必须先复制再用objcopy并指定独立输出；曾在已加载库上省略输出导致helper崩溃，原缓存字节/新进程加载/checker复验均已通过，失败保留。生产库不导出test宏钩子，CSR控制复用既有test-only库，不能将它用作性能基线。

同一语料5500条q6全唯一，不支持整姿态缓存假设。29几何有16个固定transform，44pair双固定，仅是后续工作量证据；不代表允许跳过检查。下一小候选只考虑full_tree动态DFS栈分配，原树遍历、算术及溢出fallback均须保持。

## F2m 原四顶点实现与物理对照（2026-10-22）

CLI15内联DFS栈原三对+16.960/+12.612/−33.613ms，中位变慢，淘汰；capacity=1强制spill及5500帧数值通过不改该结论。CLI16只统计：18500621次vertex_interval中重复1090635（5.9%），direct64潜在命中1.9%，未新增缓存。CLI18每轴首项无subnormal/zero term，排除本语料denormal瓶颈；绕过首轴+0比CLI17父版三对更慢，中位+17.640ms，淘汰。

CLI17复用历史SSE2双顶点的逐lane算术思路扩四lane；原种子与DFS叶都已有覆盖，没有发明新采样或删点。原scalar函数、full_scan、witness、节点次序与失败回退不变。AVX2仅函数target，原严格编译flags不变，不全局-mavx2；CPU不支持或trap未mask走scalar，四lane失败从原当前顶点scalar重试。修复CLI首版两个不存在的AVX比较intrinsic后，415单顶点边界/224树尾与tie、实际2256次向量调用通过；5500×285pair的12 numeric/6flag/提示ID逐字节同值，FE_DOWNWARD和FTZ/DAZ拒绝同值。三对原summary省132.310/137.645/126.288ms，median relative13.914%，当前factory_minimum_suite=eligible_for_physical_ab。

另存旧成本集诊断：held52/planned244/measured244中位改善11.55/11.73/13.88%，variable9.821%低于历史该候选的10%条件，保留accepted_local_cost=false，不四舍五入、不重测。不能把旧实验专属门槛机械新增为用户当前factory的前序锁；当前原三对/等值/5ms筛选已经通过，因此可以做诊断性原完整A/B，仍不能切默认或宣称旧门通过。

默认关闭接入后，预处理代码确认scalar分支与5eb6ab0原代码完全一致、enabled分支与已测CLI17原型完全一致；实际新两库5500帧逐位同值。49入口/loader/策略/计时与41树/quad/witness/碰撞回归通过。原evaluate_station --timing记录独占循环；run_pair只外层量全进程wall/CPU，不改原判定。

F2m原完整A/B结果推翻端到端收益预期：baseline→quad为60.874→64.892全进程wall、67.458→73.182CPU，controller43.043→45.475wall。除hold多3拍，其余各阶段拍数完全相同，运输和close同拍数计算也变慢。两轮物理均原pass、四XML/初态/裁判同值且实际库选项正确。因此quad不晋级，不能外推局部13.9%或把少等拍当算法提速；不新加10%前序锁，也不重复完整A/B找绿。真实负结果已送同CLI会话。

## F2n 加法原生计时与非轴方向表工作量

CLI19从原目录native会话接续151.201s，success但未产算法候选。owner采纳窄计时建议；不采纳“diffuse regression证明宿主频率/调度”、把transport控制19.5s当planning或新增≥10%物理门槛。当前没有归因证据，原factory筛选与评分保持。

从同一原baseline已保存轨迹，对close/transport全阶段各固定等距100输入，当前原scalar ABI加法计时，无cProfile、mj_step或新物理成绩。close8990扫掠状态、9090 native calls，局部core2.270124wall/native1.708421（75.26%），transport5500扫掠状态、5800native calls，core1.495139/native1.041217（69.64%）；200条均valid。控制上下文部分重建，只说明局部guard-core热点，不能称完整update/闭环占比；计时开销已包含。

帧内方向投影确实已有缓存，不能据重复pair再造缓存。另用私有整数计数测真实5500扫掠帧：nonaxis lookup319000/hit0/insert319000；Frame析构159500次，大小0有137500次，13/16各11000次。原12numeric/6flag/hint ID逐字节0差异，计数版耗时不作收益。下一单一假设为减少这些短表节点分配：按需局部小表、任意更大输入仍走原unordered_map溢出，原Key/full/zero语义、所有投影/数值/采样不改；仅CLI生成中，尚未局部或物理通过。

F2o小方向表跨工位未保住收益：nominal原A/B wall65.635→63.464s（候选少2.170s），200/200反转顺序baseline62.706/candidate63.931s（候选多1.224s）。四轮原物理均通过、同工位输入/裁判/库选项已核，但收益不稳定，整体不晋级，不将两组相加取平均冒充广泛提升。默认保持scalar/map，保留显式default-off候选。下一有证据方向为上下文snapshot与immutable的重复遍历，不继续扫缓存容量。

绑定二次遍历真实局部计时：close100 snapshot11.251ms＋ordinary validation11.266ms，transport100 12.136ms＋11.815ms，200原bindings完全.matches。二次校验共23.082ms，不是旧cProfile97ms；下一小候选只可用这一真实规模评估，不大改，不以本数冒充完整update或任务提速。

F2q有限包围盒scalar快路的证明需额外finite(local endpoints)，否则interval mul可掩盖非首NaN乘积。私有版本1324边界＋5500真实帧/raw+hints同值，实际快路39505顶点。但原三对−152.846/+1.890/−145.612ms，一对无改善，原screen=inconclusive；不忽略该对或追加完整物理。当前只查编译后是否有新的确定调用开销，不复跑相同源码。
### 2026-10-23 真实ABI输入与整回合判定

CLI23叶8局部中位省9.281%，但原nominal2/2物理通过时全进程61.300829对60.937976s，3740拍轨迹逐位同值而未提速，不晋级。新的原baseline ABI观察151589次main-update调用、26.483208s，占插桩controller62.6423%；原抓放仍pass，不能把该诊断59.279612s与旧未插桩回合作算法比较。

2816份拥有的真实输入覆盖11阶段，每条保存原hint_in。离线重新计算的基线与叶8numeric/flags/hint_out逐位同值、native-only省时，但探针未保存当时输出，不能宣称与当时输出同值或整回合已经获益。候选hint状态和阶段覆盖属于微基准代表性的输入条件，不能从稀疏重放自己重建原历史。
### 2026-10-23 局部复用不能绕过原拒绝，计数不等于净收益

在线端点缓存最终局部三对不一致，且实测原FE_DOWNWARD会拒绝时缓存仍返回true，已淘汰。盒子非轴map在2816真实输入中46416次查找0命中，但CLI27保留原数学的受限直算反而三对全慢，已淘汰，生产未改。mesh在接触阶段确有命中，不能用旧5500运输子集的0命中结论删全部缓存。原每条hint_in与阶段覆盖都属于实际工作量的输入条件；局部失败不追加整轮物理追收益。

### 2026-10-23 首个本轮跨工位收益：叶坐标连续副本

CLI28保持原点/order/tree/数学/全部采样，只改变scalar seed/DFS读取的存储地址，可选分配失败仍回原数据。实际17个mesh、198900个顶点的596700个binary64副本逐位一致；原full-scan oracle及2816份真实hint-restored输入、空副本/disabled控制、异常算术模式均同值。三对局部各省34–39ms，随后两工位反序原物理4/4通过，完整wall分别少1.925s（3.61%）和1.254s（2.27%），CPU/controller同降，仿真都反多0.04s。

据此只让工厂入口默认选择leaf_packed.py，显式baseline.py/RoutePolicy()与其他显式旧候选保持原样；没有改底层native全局缺省、原裁判或碰撞条件。无candidate默认入口另行完整抓放通过，其3741拍轨迹与显式候选全字段逐位一致。此为两个既有工位的实测实现收益，不是新规划算法、统计成功率或50Hz通过。

### 2026-10-23 已采用packed内联与同投影节点界复用

CLI29基于实际编译后4处CALL，只对packed helper加条件内联。三对局部均更快，两工位反序原物理4/4pass，相对packed父版全process分别少0.476/1.267s，CPU/controller同降；第一工位P95和worker略退化，未隐去。678c5e3已发布，显式packed父版和最初baseline均保留；“少了CALL”不是采用依据，实际任务收益才是。

CLI30排序/二分种子节点界表局部成本不一致，未应用生产。CLI31固定128槽直接索引，单次full_tree独占，只复用同节点、同local已经完成的有限区间值；冲突/缺项原路重算。2816真实输入、正常/empty/tiny原oracle和原算术拒绝同位，88份C内即时FP状态及原隔离陷阱检查通过。三对局部均快，两个已有工位反序原物理4/4pass；相对678父版wall55.582→51.401s、57.113→52.710s，CPU同降。

两边剔除全部hold周期后，非等待阶段拍数完全相同，controller仍省3.333/3.440s，不能用少等拍解释该收益。当前工厂默认已升级为seed_bound_direct.py，发布548717c；RoutePolicy()/baseline.py保留原版，packed与packed+inline父版显式可复跑。两个工位P95仍为24.831/25.166ms，50Hz未通过；原评分、点集、碰撞、释放与90sim/120wall保持。原结果和准确复跑入口见progress F2w/F2x，不将这些观察外推成统计保证。

### 2026-10-23 叶顶点复用淘汰

真实计数的514020次seed→DFS同顶点重复确实存在。CLI32完整叶成功后复用，经原oracle和2816逐位/disabled/empty/tiny控制同值，实际复用量也吻合。但原三对effect为−1.521/−13.147/+1.099ms，中位不足且一对变慢，原screen拒绝。候选未进入生产或完整物理，原默认保持548717c。不能把重复算术规模、等值或模型认同当作净收益；无收益时停掉这个候选，保留原成本，不扫描容量或重新计时挑绿。

### 2026-10-23 Python汇总快路无需新C接口

2816真实输入的原cert全部通过，当前整个_summarize约7.0–7.3us每次。CLI33仅增加全非零分支；创建查询绑定时选择一次，失败/空输入委托原方法。原方法体、C++源/ABI/库文件/flags均不改，metadata只额外标记Python实现，不修改native manifest。54边界与2816真实输出同值，包含原失败/非二元cert/NaN/Inf/空输入/异常；原workspace重入与生命周期继续通过。

原三对完整ABI+汇总调用（含两边同样结果归一化开销）均更快，两工位反序原物理4/4pass；wall53.075→49.698s、56.878→55.756s，CPU/controller同降，200/200的3857拍轨迹JSON完全相同、等待相同。两组剔除全部hold后controller仍少2.272/1.430s。原默认现选择summary_fast.py，seed_bound_direct父版保留原汇总；最初baseline与旧候选不叠加。

这是实际观察到的两工位实现收益，不把全差单独归因约7us组件，不将多批次收益相加，也不由局部统计宣称50Hz。第二工位运输worker更慢，其他分项和原全部失败留证。原碰撞、释放、自由物体和90sim/120wall保持，原完整评价入口没有修改。


## F2aa 控制周期长尾与同名换段（2026-10-23）

- 原CLI33两工位224/261个超20ms拍，close/release占169/183，controller占超时拍总墙钟约88%。保存q6/reference的40弦回放完整7868检查，原生ABI占1.137/1.637s（含cProfile扰动，不是当时逐拍native时钟）。
- 固定轴norm是保守区间值X/Y/Z分别1+4/3/2ULP，不能改成数学1。CLI34同帧复用原值虽等值，但原三对中位只省1.298ms，原5ms门拒绝，无生产/物理改动。
- 同名transport换腿更新stage_started，但update沿用换腿前age，造成新腿终点→起点的一拍脉冲。既有fake-FK fixture和两工位原实际轨迹均证明；CLI35显式修复最大单轴步进.780/.829rad→.00484/.00483rad，四轮原抓放/释放/脱离/回位通过。
- 该行为收益不等于稳定性能收益：nominal全process64.652→51.498s；第二工位反序52.130→55.402s更慢，P95第二24.355→26.894ms退化。默认仍summary_fast；新源default-off复跑，不调用逐位等值screen伪造策略改动等值。完整50Hz未过。
- 原2816实输入下full_tree待处理vector新建25438次、容量增长97559次，最大待处理12。计数版raw/hints与父版一致；这些是增长事件，不是实测malloc次数或提速。下一候选只改同投影栈存储，溢出必须原vector回退。

来源和复跑：私有ros2-factory/codebuddy-so101-20261021/round34-tail-audit、round35-axis-norm、round36-leg-age、round37-pending-stack；原物理准确argv及独立回读在output/leg-age-factory-20261023两个既有pair目录。采用的长期原则见Wiki/ROS2 与 FishBot第20节；本轮不新增共享知识机制。


## F2ab 保持原错误作用域的批量扫掠（2026-10-23）

- 只复用现有MuJoCo Python FK和现有C证书，按原顺序逐样本执行，不新造几何判据。直接C-FK原型虽约21%更快，但因绕过Python错误作用域未进入生产；保护版回调原Python FK，RuntimeError/ValueError按原invalid处理，FatalError/KeyboardInterrupt原对象传播，失败前缀/Data/raw/hints同值。
- 40保存实弦+16异常/拒绝边界生产读回同值，原三对整guard中位省.299391s。每进程初始化编译独立桥，原kernel/lib/flags不改，guard循环不编译；构建不可用回原路径，无新内容哈希门锁。
- 两工位反序4轮原物理pass，整进程省5.931/7.155s；剔除hold后仍省5.914/6.719s，候选反多9/13拍hold。分离worker两处都略慢，保留原时钟，不把它称规划加速。
- P95 19.138/22.298ms，超20ms168/231；只有一处P95进入20ms，完整50Hz未过。原1mm、释放2mm/.02N、90sim120wall及自由物体条件保持。第二工位子释放峰力.003611N在原界内，不称零力。
- 批量统计只属于本次选用的运行报告，不能因import一个模块就改变原native库元数据；可选诊断失败不得改写物理结果。默认入口与原报告/loader兼容77项检查通过。

采用源route_strategies/batch_configuration_sweep.py；原版与summary_fast父版保留，不叠加未晋级的换段修复。原两pair独立读回及非等待/规划/视频时钟在output/batch-sweep-factory-20261023/，原CLI和复跑在私有round38-batch-sweep、round39-protected-batch。

## F2ac 连续开合的可证伪假设（2026-10-23）

- 两轮真实batch轨迹close/release各331拍，首指令跳-.485/+.485rad，实际弦首拍分别244/191点。两阶段累计41478/41500采样点，仍133/163拍超过20ms。来源round40-jaw-dwell/parent-tail-audit.json；这些是按原前状态和原reference重算采样量，不是新物理或当时ABI插桩。
- 物理夹持后jaw约.121rad而闭爪命令.015rad，不能把两者混为一谈。连续策略从上一条命令衔接，使用既有6s dwell和原minimum-jerk；实际q到本拍目标继续原完整碰撞检查，整闭爪预检查244点保持。
- 原CLI39首稿把两1D点写成shape(2,)，实际中点调用AxisError，未接生产；同native会话CLI40仅修正为shape(2,1)，错误源和回执保留。新bool默认false、不叠加换段计时修复，84项相关检查通过。运动指令有意改变，仍须原抓放/接触/释放/脱离/回位及延迟实测，不由静态或局部测试认定收益。

- 首次真实原评测因separation_context_changed失败：预取冻结上一jaw命令.449795，而同拍改发.451485，原last_command绑定正确拒绝。CLI41只要求连续分支的本拍reference与上一已发命令均到精确最终jaw才预取，原实测>=.45/完整绑定/6+.6s与物理门保持；没有移除保护。失败原件及初始诊断脚本错误均保留。
- 修正后两工位反序4轮原物理pass，全process57.097628→52.463659s、64.256692→59.682278s，CPU和nonhold成本都降；子release反多22/32拍，第二hold多3拍，不能算少等待。原planned/measured各244点，实际弦close采样29553→6210来自目标距离缩短，密度和全路径检查保持。
- 连续开合已采用，原版及batch父版显式保留。P95 17.979/23.283ms，超20ms102/537，最大173.763/209.864ms，完整50Hz未过。第二子释放峰力.003687N在原界内，两个worker耗时并未更快。准确argv、source快照与独立指标在output/jaw-dwell-factory-20261023/{298eeb34-35de-48f9-96fd-c0342f69d2bb,aeecfa9f-0941-4b62-b369-8fba9a387bba}/；原失败为e9a89455-5150-4807-aef4-f955e1dd86dc。

## F2ad 改变基线后的既有换段修复（2026-10-23，已采用）

- F2ac完成后新余下最大三拍173.763/148.316/127.600ms均对应旧age参考突跳，原CLI42只生成组合源，唯一字段refresh_leg_age=True；Controller沿用既有修复。旧summary基线性能不一致不变，本次有明确新瓶颈和新父版，未重复旧源码挑绿。
- 两工位反序原物理4/4pass，实际process40.028290→37.928470s、50.218805→40.971192s，CPU47.459069→45.279297s、58.718622→49.103637s。原运输规划路径完全相同；剔除全部hold/release后各阶段拍数同值，wall27.142446→26.927025s、35.936931→28.793605s。整程差额不全归于三个修复拍，不能把较少等待当作算法提速。
- 运输目标最大单轴步进.780291/.828836rad→.004836/.004829rad，各六次往返脉冲消失；这是目标变化，不称真实机械臂瞬间转过这些角度。P95 13.370898/13.446834ms，仍42/48拍超时、最大80.162557/91.543817ms，完整50Hz未过。原planned/measured各244点、全部实际弦、原native库/flags、1mm碰撞/释放门及90sim120wall保持。
- 两工位候选释放漂移.248956/.257223mm、脱离后峰力0N，原抓放/释放/脱离/回位均pass。首sim75.44→75.36只少4release拍，第二78.00→78.06反多2release/1hold拍；仍有非等待同拍数成本改善。四轮录像完整，原源/默认/策略选择和报告回归73项通过；采用smooth_jaw_leg_clock.py，原所有父版保留。

原件：output/smooth-leg-clock-factory-20261023/{d5ecdeae-6770-472a-90f5-6c8df739a9cc,f6ca982e-5d9b-4d51-8f92-4ee477e08f8f}/，含原评分、准确argv、source快照、独立完整及policy-and-transfer读回。原CLI/三对/复跑在私有round41-smooth-leg-clock。

## F2ae map冻结未晋级（2026-10-23）

- 标准cProfile原物理通过但有显著插桩开销，只作计数；随后原验证成功后的只读采样得到18类实际原输入、7762次阶段频率。CLI43仅生成map遍历改动，所有原字段/访问、float64位身份、符号零、拒绝与副本隔离保持，无缓存或新内容哈希门。
- 原私有及生产各三对均通过原组件screen；生产每绑定选择、async保持原路径，153相关回归通过。两者作用域是按实际次数加权的捕获形状，不称7762条唯一在线输入或全任务改善。
- nominal原物理2/2pass，process60.208307→59.548003s，但CPU67.761540→67.989059s、nonhold wall47.570173→47.844158s、P95 21.745085→22.363426ms、慢拍346→427均变差。排除全部hold/release后同阶段同拍数仍wall43.106746→43.277671s，不接受“少了墙钟所以提速”。原路径/评分/阈值与C库同值，实际map false/true已读回，释放漂移.249001mm、脱离后0N，原抓放/释放/脱离/回位通过。
- 完成时发现并行Blender进程平均CPU381%+312%、load1=15.19/16逻辑核；该宿主机争用会干扰性能归因，不能归咎或归功于候选。两个后台渲染随后自然结束，仅低占用GUI保留；没有停止其他任务。原物理pass保留，性能晋级淘汰，默认仍smooth_jaw_leg_clock.py；map仅显式default-off复跑，不追加第二工位或重跑同源挑绿。

原件output/context-map-factory-20261023/9939de33-5f26-4f4f-8c5e-8b0e89d086fe含host-load-readback及完整/策略/非等待读回；CLI、捕获、边界、三对和准确复跑入口在私有round43-context-map及prepared/source。原private run_pair.py增加前后负载只读记录，观察位于子进程wall/CPU计量窗口之外，无新锁/配额或自动停止其他工作。


## F2af 模型准备只改善启动时延（2026-10-23）

- 把实际65geom原模型copy从主线程挪到现有worker，主观察间隙42ms只降至38ms，三对均过20ms，淘汰该放置方案。不能据此泛化为已证明所有GIL原因。
- CLI45循环前准备三份独立模型，根只修强引用身份、标准query适用范围及锚点空行。释放估计的pos/quat/sameframe三行在交接前同步，原worker字节核验不动；yaw0/.25测试整模型与原现复制逐位相同。准备/清理计入总process，不是算法少算。原错误/回退/所有权/清理120项通过；初稿锚点拒绝和fixture错误保留，CLI修正429未伪造成成功。
- 两工位反序4/4原物理pass，请求拍56.078/84.884→16.682/13.403ms、55.215/87.078→15.687/11.150ms，复制尖峰改善可复现。全process37.778→38.448s和39.582→39.926s均未改善；剔除hold/release后相同阶段/拍数也未快，不晋级默认。P95约13.3ms仍不等于完整50Hz；子仍48/34慢拍，最大59.847/76.499ms。
- 全部原规划路径、native核/库/flags、4XML/初态/原裁判/释放门同值；两子漂移.248988/.257261mm、脱离后0N，无障碍碰撞或安全停机，录像完整。明确保留可选调度价值，不把它伪装成总耗时优化。

原件：output/worker-preallocation-factory-20261023/{5df8e9c8-1236-46fd-9831-8d5470e32bda,a86caf7a-b3ed-4bf9-9d43-5b0c9c8abfdf}/；准确argv、source、原评分、独立全周期/请求拍/策略读回与运行前后负载齐全。私有round44-model-copy/round45-preallocated-models保留来源和复跑。


## F2ag 原GC事件对齐真实慢拍（2026-10-23）

- 只读gc.callbacks观察当前原默认单回合，原物理pass、GC启用及阈值保持、0观察错误。874次主线程GC累计仅.278s，但控制窗口内4次gen2集中占21.518/45.874/37.059/58.133ms，对应25.283/59.374/44.691/68.339ms周期。说明累计成本小不能排除50Hz长尾问题。
- 没有据此断言其余慢拍也由GC造成；模型复制、闭爪全扫和worker接纳仍有独立费用。未禁用GC、未丢物理检查或改生产默认，未把带回调P95作为性能A/B。原窗口外另有gen2回收19.382ms。
- 新调度候选需原CLI生成，CodeBuddy429阻塞；已准备包含原测量和允许范围的native请求，尚未实施GC改动。

原件：output/gc-tail-diagnostic-20261023/98e68487-3f4c-415a-8910-e0bef6095e1a/含原评分与gc-cycle-readback.json；复跑私有round46-gc-observation/probe.py。


## F2ah GPT直接生成的GC调度候选（2026-10-23）

- CodeBuddy为可选外部助手，用户已明确允许当前GPT接续，不把额度当研发前序。禁止向「登录 X」对话发任何协调/进度/回写消息；后续也只检查实际进程避让。
- 第一binding-only局部没有gen2且成本screen reject，保留原失败；新的原遥测留存重放每次都出现gen2。三对18类/7762次原binding与所有3768/4/7340条记录同值，最大分配批30–32ms→.7–.8ms；吞吐screen inconclusive、含清理总成本不稳定，未伪造总体快。
- 67相关回归与两工位反序4轮原物理pass。首工位3770拍trajectory/contact/vision逐位相同；第二只视觉逐位同，异步等待多2拍。全process44.322→44.199s、53.463→52.353s，CPU52.406→51.939s、61.946→61.135s，但慢拍69→71/153→135且max95.760→93.937/96.965→116.429ms，不认为全局长尾通过。
- 清理174/191ms计入原回合/截止检查前，GC原状态恢复、阈值不变，内存峰值多119/114MiB，不能隐瞒此代价。原核/库/flags/全部安全/244点/评分与90sim120wall保持。保留显式开关，不切默认，不声称20+20或完整50Hz。
- GitHub原凭据失效且授权后直连超时并存。官方设备授权完成，再用现有本地3067代理仅作用于命令，读回用户qiaoqiao2521(id238822818)和目标仓库，5个积压提交正常推到ba9bc82，REST与ls-remote同值。没有改系统代理、使用旧账号或提交认证状态。

原件output/deferred-gc-factory-20261023/{47df0702-76f9-4e76-94f3-6168a663bf32,fc9546b7-fd55-42a4-8de6-84694153823e}/；本地round47-gc-window保留GPT来源、探针、旧拒绝与复跑。

## F2ai GC父版与预准备组合的首工位（2026-10-23）

- GPT只组合已有开关，唯一差异preallocate_worker_models；GC两边相同。局部三对最大交接间隙约105–110ms→.46–.52ms，但含全部准备与清理总成本均增加。
- 原首工位2/2pass，transport/separation启动拍80.516/111.319→21.631/11.329ms；准备177.422ms计入初始化，max111.319→79.085ms。P95、慢拍、全process/CPU及剔除等待后的成本均回退，不晋级默认或称算法提速。
- 原host快照显示中途新增后台Blender/FishBot等争用；保留这组实际结果及不确定性，不重跑原工位择绿。第二已有200/200反序只验证启动延迟是否可复现，完整50Hz未过。
- 原private成对runner每个case启动前重查共享任务，资源等待单独计时且不进入子进程性能；无强停、配额、锁或新调度服务。不能防止其它任务在case开始后再启动，仍记录结束时共享任务。

原件output/gc-preallocation-factory-20261023/03a1f13c-7f0b-4768-9cb5-7d031882518f/；private round48-gc-preallocation含来源、三对、资源检查与原入口。GC和预准备默认均关闭。

F2ai第二工位反序原2/2pass，父→子启动拍60.515/116.600→22.267/10.526ms，max116.600→94.251ms；process57.173→58.997s、CPU66.775→66.818s、P95 22.148→25.753ms、慢拍282→467，剔除hold/release仍退化。因此四轮原物理通过只证明功能与两处启动延迟，不能支持默认采用。子214.230s资源等待与实际process分开；准备155.257ms、GC清理198.306ms均计入成本。父中途新增后台Blender已留证，未重复同工位择绿。

第二原件output/gc-preallocation-factory-20261023/67b753ea-e547-461b-aac4-bfe6e73dee89/。默认保持，下一项依据已有profile的_fk 4644次/.690s，检查仅返回位姿的独立Data是否可以省掉完整动力学前向；尚未实测或接入。

## F2aj 只隔离独立FK，复用归档实现（2026-10-23）

- 2026-10-07已有FK+IK pose-only候选，完整周期P95只改善2.720935%、未过当时5%门，旧失败保持。当前只接独立_fk，IK保持，基线已换batch+smooth+leg-clock、MuJoCo3.15，不复用旧成绩。
- 原样复用归档forward_pose_query；有sensor/plugin/mocap或任意当前回调就每次退原full-forward。生产测试比对AST一致，未引入运行时内容锁。104相关回归通过，真实动态注册回调仍被调用。
- 7538个真实机器人q6/command的三项返回和调用方读取Data逐位同；生产完整helper三对.352652→.138482、.351655→.139964、.352818→.127403s，原screen eligible。仅组件收益，不外推完整50Hz。
- 首工位原2/2pass，process64.571→49.150s、CPU73.537→57.491s；去掉hold/release同拍数wall46.533→35.008s。原XML/初态/评分/阈值/native/path相同，实际仅pose_only_fk；视觉逐位同，动态非逐位同。父子宿主负载差异很大且中途新增编译/渲染，不能把15.42s全归因FK。第二已有200/200反序在实际资源检查后接续，默认保持。

原件output/pose-fk-factory-20261023/15afdef5-d6e1-4cc0-b8ac-4fc6d8268f60/，private round49-kinematics-fk包含旧反证、归档来源、原型/生产对照与复跑。第二工位待实际终态，不提前承诺采用。

F2aj第二已有工位反序原物理2/2pass，但父→子process58.056→84.727s、CPU67.794→94.381s、P95 21.102→38.528ms、慢拍258→1302；去除等待同拍数仍明显慢。原native/XML/目标/原路径/释放门同值，子漂移.257184mm、脱离后0N。资源检查后仍有新FishBot工作中途启动，保留实际负载，不把15秒名义改善或本对退化全归因算法或争用。两站结果不一致，默认保持。

第二独立对照same.scorer=false/pass=false，源于根在pair中途提交f28，Git commit/dirty_paths字段变化。原失败不改。额外比对确认4个评分/执行源码在两commit、当前及冻结裁判快照字节相同，只能说明代码没改，不能说来源门已过。后续成对终态后再提交。第二原件output/pose-fk-factory-20261023/f1b8be85-8c7a-4129-89a2-33e4fe8f00c9/含原计时、规划时钟与scorer-provenance-readback。

## F2ak 244点重复量与实际输入差异

同原采样/29几何/285pair只读数11条实际弦，计划闭爪244点中259/285对位姿恒定，但实测闭爪及多数在线弦仅44/285对恒定；约.000526rad的跟踪差足以改变其余精确键。90.877%不能当实际244控制尖峰的普遍收益；15.439%仍只是位姿复用数量上界，hint/FPU与每对计算成本未证明。未实现新缓存或跳过检查；下一项只量这44对原成本，值得才生成实现。原计数入口private round50-static-work-count/count.py。

私有原C入口复制加逐对clock归因：549状态/156465pair全部numeric/flags/hints与原入口逐位同，生产未改。可复用对占计划闭爪约57.45%计时，但实测闭爪仅3.643%（约1.776/48.738ms），在线代表仅3.36–3.82%；clock开销未扣，fresh提示重建也不冒称历史实际hin。否决为44对构建大缓存，先按同一局部数据排耗时pair和19方向搜索重复度，避免再花77s物理试错。旧固定轴norm复用已实测只省1.298ms，不重复该候选。

## F2al 成功方向可复用，几何证据必须重算

原pair284腕/活动指和pair2台面/肩在所有样本都用mode2/axis2、22次证书搜索；相邻所选mode/axis为242/243一致，在线运输52/54。新策略只存每对mode/index，每次从当前姿态重新构造原方向、双次原归一化及原certificate，全部pair/244点保留。任一hint失败、冷输入、trap或有界域外都整次原查询，不保留半成品证书。原树/投影/证书与原sb_run函数不改；无目标物体真值或pair/坐标硬编码。

这是搜索策略，成功时方向/下界/求证次数及顶点hint可不同；不能宣称raw14字段实施等值。私有2816实际ABI、802560有效性与17异常前缀通过，失败全查询numeric/flags/hints逐位同；独立200位Decimal核对三类实际pair的全部编译顶点包络及原margin。生产三对11弦/773点CPU .866855→.336694、.797435→.298601、.847955→.420132s，报告/最终Data逐位同。仅组件准入，不是整回合或50Hz成绩。

公开候选route_strategies/direction_hint_sweep.py仅相对原默认加一bool。原ABI观察者在factory前后安装都保留逐点调用；新符号缺失保留原batch；protected Python FK/首错前缀/原异常对象/owner锁不变。101回归通过。复跑与来源private round51-direction-hints/{candidate-origin.json,production_probe.py,production-results.json,regression.py,regression-results.json}；候选来源Root GPT，未冒称调用CodeBuddy。

正式代码再次回放同2816输入/802560判断及17前缀通过；另工位11弦773点公开报告/最终Data同值，三对CPU 1.124660→.446490、.990270→.342418、1.063456→.472374s。两工位原物理4/4pass、独立来源门均过；实际process84.384→56.037s、79.304→48.649s，CPU91.038→62.512s、85.337→55.976s。候选仿真分别多.66/.74s，不是少等拍。

nominal剔除hold/release后同3264拍，CPU59.235→37.856s；第二工位另剔除相差一拍的lower，同3236拍CPU52.896→29.578s。所有原点/阈值/路径保持，候选实际检查点还更多。P95 30.064→18.786ms、28.520→20.759ms，但第二最大151.738→184.787ms反退，仍104/235慢拍，完整50Hz未过。主机中途Chrome多核、第二父版新增Blender均保留，不把整个30秒差额全归因策略；采用依据是两处相反顺序、六对局部及同拍数CPU证据。

F2am只在已采用方向提示父版开启既有模型预准备；F2af/F2ai未节省总成本的旧反证不改。实际新父版运输/分离请求62.005/143.672ms，复用原helper三对最大空档102.376/116.824/104.967→.481/.684/.632ms；总成本156.145→172.269、184.258→175.153、156.856→205.992ms，不能称算法少算。新策略来源Root GPT，原模型独立性/旋转/回退代码不改；原probe复制更新真实场景及策略字段，复跑private round52-direction-preallocation。

F2am原两工位反序4/4通过，新父版process41.205→36.451s、37.354→32.488s，CPU49.508→43.758s、44.916→40.306s；剔除hold/release两站各自同阶段同拍数，CPU27.464→24.281s、24.997→21.179s。初始化131.319/102.612ms计入完整进程。两处启动拍67.353/108.481→16.184/13.525ms、51.901/84.765→12.197/9.632ms。模型ready/used均真、无回退，原几何/路径/评分门与全部物理保持。因父版更换而重新实测采用，不能改写F2af/F2ai旧负收益。

P95 14.094→12.491ms、13.603→10.349ms，max108.481→57.592ms、84.765→75.114ms；nominal慢拍62→79反退，跨站42→12改善，完整50Hz未过。剩余静稳controller52.587ms线程CPU，非规划启动；不能把所有长尾说成复制或OS等待。下一项先复用原GC只读观察器绑定新默认，不盲目再次开启GC延后或扩大预算。

F2an新默认只读GC观察已原物理pass。四次main-thread gen2各20.192/30.843/35.527/44.210ms，重合的完整周期26.405/38.425/41.803/54.849ms；静稳最长明确有GC贡献。全回合9慢拍，其中5个并不由这四次回收解释。GC前后enabled=true、thresholds=[700,10,10]，observer错误/未闭事件0。这是插桩归因，31.404s不是无插桩性能对照。

F2ao仅开既有defer_cyclic_gc。局部保留旧18形状/7762绑定作为fixture，只替换为新实际遥测分配；不宣称实际20ms循环。三对CPU1.686→1.328、1.681→1.465、1.707→1.502s，输出同值；全wall1.723→1.328、1.711→1.877、1.727→1.510s，第二反退且子max190.781ms、GC次数0，原screen=inconclusive保留。不能声称三对墙钟/最大延迟一致获益，也不能把190ms无证据全归因宿主。鉴于已有实际四次GC因果、原窗口已验证和本轮57回归，通过显式原物理实验检验GC尾延迟收益；不据该局部报告晋级默认。

F2ao两工位4/4原物理pass，来源与原评分均同。首工位process53.096→30.074s、CPU60.767→37.590s、慢拍169→12；第二200/200反序process32.666→37.105s、CPU40.356→44.397s、慢拍12→30，P95 9.999→12.011ms、max76.519→81.937ms回退。第二剔除hold/release/lower后同3236拍，CPU19.461→22.519s仍回退，不能把少2仿真拍当收益。拒绝默认晋级，保留显式direction_hint_preallocated_gc.py；GC默认false。

清理137.842/193.114ms计入原进程，两个worker原join/ownership均确认，GC恢复true/error=null；候选峰RSS比各自父版多26.195/45.332MiB。首工位父版运行中新增Blender，不能把23s差额全归GC；跨站前已有ffmpeg并在候选运行中结束，不能排除负载影响，也不能据此把实际回退改成成功。原局部screen=inconclusive与190ms反证保持。四轮抓起/放盘/静稳/释放/脱离/回位、安全0、障碍0、完整视频及free-object条件均通过。完整50Hz未过。

下一项只做原C内核严格浮点下的本机编译局部筛选。已有方向提示路径在线controller仍约4–5ms，实测244点闭爪仍有单拍超20ms；先比较本机指令选择能否减少同一份几何工作。只在私有build追加-march=native，不开fast-math、不改精度或点数；原实际ABI/公开结果等值和三对实测优先，没有组件收益即止损。尚无本项结果或生产修改。

F2ap局部完成，Root GPT私有round55-host-native/probe.py只追加-march=native，原bridge单独保持相同。2816原ABI/802560判定的numeric/flags/hout/dout逐位同；新名义工位11条实际弦、773点公开报告/最终Data同值。三对wall47.298→46.917、47.010→46.950、46.678→45.964ms；线程CPU47.279→46.916、47.009→46.931、46.677→45.962ms。原screen=reject/median_local_effect_below_threshold，中位仅省.381ms，未过原5ms门。淘汰，不追加跨站/整程，不修改生产编译选项或默认。

当前原件仍有同步退回规划与接近段感知等非GC慢拍，不能凭旧119百万调用的profile给新内核排热点。下一步复用标准cProfile+原evaluate_station.py做当前默认一次真实计数，明确它会扰动时钟；只用于调用量/热点定位，保持全部原物理门，不当作性能A/B。

F2aq当前默认标准cProfile已原物理pass：run d4933ea9，source7ad3982干净，76.00sim、47.468process-wall/54.740process-CPU。主线程总89941742次调用；_sweep_binding7618次、snapshot3096746次、_immutable_context4099595次，构造累计8.443s属于插桩时钟，不冒称未插桩成本或worker成本。原244点、抓放/释放/脱离/回位和完整475帧视频均过；independent-profile-readback.json与main.pstats保留。

F2ar据此合并_sweep_binding的snapshot递归与SweepBinding的不可变编码，所有字段仍每次重新读取，有限值/float64位身份/排序键/副本隔离检查保持。原snapshot和_immutable_context保留为默认，异步绑定不变；新fused_context_freeze默认false。Root GPT没有引入跨请求结果复用或新内容锁。

私有原型对18旧捕获上下文形状、原7762阶段次数和34边界及复制/正负零检查同值，三对wall1.731712→.697419、1.694410→.691199、1.854305→1.126521s。正式完整构造器同数据三对1.757154→.717590、1.782356→.781854、1.728119→.702169s，原screen eligible。此数据已是旧snapshot后的拥有值，范围明确为代表结构重放，不伪称当前7762个唯一在线观测；正式185相关回归进一步核对真实controller输入中的数组/字典/RoutePolicy、变动拒绝和原物理失败透传。下一步仍须原物理A/B，尚未采用。

F2ar原物理两工位反序4/4pass，source fbaea07全程干净且两对均原来源门通过，实际仅fused_context_freeze变化。process32.330→30.717s、37.052→33.466s，CPU40.151→37.879、45.007→41.058s；剔除hold/release后，两站各自同阶段/拍数CPU21.108→20.245、24.171→21.858s。候选第一站反多4仿真拍，第二站少2release拍，不能把少等拍当计算收益。原所有规划/244点/抓放/释放/脱离/回位通过，采用direction_hint_single_pass.py为默认，原父版保留。

P95 11.447→10.490ms、14.047→11.947ms，max95.515→49.828、109.640→78.637ms，慢拍14→12、39→30。第二站hold慢拍6→10回退仍保留，完整50Hz未过。首父运行中新增Blender、第二候选开始load1较父高，不能保证完全同负载或把全部3.585s强归于一次树遍历；采用依据是两站反序、局部三对和同拍数CPU改善。GC/本机编译旧失败不改。

F2as下一项仅检查原标量_arm_valid的重复方向搜索。F2aq该主线程布尔接口8682次，源码当前仍走原ns_evaluate_hinted，已有方向提示只在batch扫掠启用。先用真实机器人q6私有复用原C方向入口，比较布尔谓词与最终Data及三对成本；数值下界/方向提示可以改变，不能把它们记作raw等值。当前不动生产或评分，不扩展到需要数值下界的shortcut/diagnostics。

F2as私有实测完成：从已采用候选的approach/close/transport/release/retreat各选100个真实q6，只传机器人关节和夹爪角；500个原_arm_valid布尔输出及最终FK Data相同，全为正常valid样本。原C源码/二进制相同，候选独立ctypes对象上的私有Pythonobserver调用已有ns_evaluate_direction_hinted，包含该额外Python开销。三对wall98.590→77.464、99.207→87.047、109.622→71.840ms，CPU98.569→77.055、98.811→86.516、102.879→71.241ms，原screen eligible，中位省21.126ms。数值下界/方向/hint输出未宣称等值；无物理成绩或生产开关。

该探针尚不覆盖碰撞拒绝、异常环境、owner重入和观察者修改。下一步只将已有C方向入口接到可选的标量布尔调用，保留默认原summary、原异常/观察者/缺符号回退；不能把私有observer当生产接法，也不能把500个名义状态当全域验证。private round58-scalar-direction保存完整源、Root GPT来源及local-results.json。

F2as正式边界：只有布尔_arm_valid选择方向复用，ConservativeCollisionChecker默认3位置summary调用保持，所有需要数值下界的路径不选新入口。索引不是证书，原C仍逐帧全重新证明且失败/不支持时走原C搜索；observer或缺符号走原Python/ABI，不能跳过用户安装的观察。240回归通过，但正式组件和原物理尚未运行；NaN字典测试断言错误的原日志保留，不能将它描述成算法失效或通过。

F2as正式组件移除了私有Python observer，以真实生产_arm_valid开关重测500实际q6；三对wall省28.887/26.204/33.142ms，CPU同向，原screen eligible。只有布尔与最终FK Data等值，未宣称原数值下界/方向/提示同位；尚需原物理证明任务与总成本收益。等待2794.826s单独记，不能作为算法提速。

F2as名义原物理2/2pass且原评分/244点/所有成功条件保持，但去掉hold/release后同3264拍CPU23.119→23.672s，完整成本收益未被证实。拒绝默认晋级，不追加第二工位；候选中途新增Blender的干扰与worker时钟改善均保留，不据此删负例。F2at据原profile的482次状态JSON写入与实际callback慢拍，仅筛选现有stdlib紧凑编码，数据/发布频次/原子替换/NaN拒绝不变，生产尚未修改。

F2at复用现有stdlib紧凑JSON编码的私有482次代表结构写入三对wall中位省.695993s；解析值保持，原字节空白有意不同。64生产相关回归通过，默认false只选status发布；不减少任何字段、发布触发或物理检查。正式组件和原物理仍待执行，不能从插桩4.682s或局部秒数推算任务提速。

F2at正式writer同482次三对wall.819→.225、.871→.232、.901→.258s，线程CPU同向，原screen eligible；原代表运行态的解析值和原错误语义保持，不能外推完整任务或把旧screen字段称为原JSON字节等值。默认false，下一步原物理才判定收益。

F2at首工位原物理2/2pass，94.375→51.817process-s与同3264拍CPU44.874→29.710s均受明显宿主负载变化混杂；未将42.558s归于格式选项。实际scene发布653→347仍按原墙钟触发，不作同量写入证明；正式三对482次才支持组件收益。保留原数据，接第二已有200/200工位反序，不改默认、不重复首工位择绿。

F2at第二已有工位反序2/2原pass，process38.628→37.426s、CPU46.844→45.512s；剔除hold/release/lower后同3236拍CPU24.450→23.279s，callbackCPU1.181→.594s但发布307→293，不冒称相同写入次数。采用紧凑实时status，首站42s差仍按宿主混杂，release慢拍15→24及分离worker反慢保留，完整50Hz未过。默认入口compact_status_json.py，底层flag仍false，91相关默认回归通过；历史single-pass/原版可复跑。下一项先更新旧于两项采用的主线程profile，方向列表已是std::array19，不重复重写。

F2au新默认原物理profile/pass：主线程_immutable_snapshot_context3787928次/5.404累计插桩秒，validate_joint_path3889次主要来自update3803与shorten_path78。下一F2av仅把原float判断移到容器判断前，保持所有位编码/错误，用旧18代表结构/34边界及原7762权重先三对。原C方向已是19数组，原积分守卫不改；未测局部不记成功。

## F2av 浮点分支前移的组件证据（2026-10-23）

当前F2au归因只支持热类型判断假设，不是算法或50Hz结论。Root GPT的私有round61保留原helper作为父版，仅把相同float分支移至tuple/list前；原float64位编码、有限值拒绝、dict键合同、数组复制和错误不变。18旧捕获形状按7762旧次数加权，另34边界及4拥有/正负零检查共56项同值；三对wall .781317→.684620、.741920→.689402、.752161→.716843s，CPU同向，原screen eligible。它不是当前7624个唯一在线输入，也不是完整构造器或物理成绩。

生产最小接入新增默认false的float_first_context、独立同语义helper与显式候选；只在snapshot_context=True选用，异步和其他freeze保留原路径。88项相关回归通过，默认compact_status_json保持。正式完整构造器三对由round61/production_probe.py接原资源等待；不把旧two-pass父版作为当前基线，不重复已拒绝scalar/GC/编译候选。

F2av正式完整构造器：双方都使用当前fused实现，原async保持；同18旧代表/7762旧次数三对wall .930442→.802920、.977845→.884843、.881772→.809585s，线程CPU .930344→.802684、.976967→.884380、.881667→.809548s，全部matches双向同值，原screen eligible。等待.042644s另计；不将约93ms中位组件节省当整轮加速。原件round61/production-local-screen.json，接原名义父→子物理；默认保持。

F2av首工位终态：667bd6c干净源码，60aa6404-1516-4f88-a6db-3f3721034274的父55373c9b-2aa5-41be-a277-e39bde7dd26f/子0e56b2d2-7453-4553-9cc7-60807bb8fb1e均原pass。47.374765→42.096212process-s、54.951899→50.392922CPU-s；sim75.98→76.00，反而多1hold拍。去掉hold/release同3264拍，wall30.186544→27.119947、线程CPU30.123009→27.006922、controller19.594019→17.497929s。组件中位只省93ms，不能将整个5.279s强归此次分支顺序；宿主load1父11.03→11.18、子11.18→12.29且GUI持续活跃，未控制频率/调度。保留本对，按协议只接第二已有200/200反序，不重复首站择绿。

完整P95 15.806564→14.811197ms、max64.719597→52.436018ms、慢拍118→98，完整50Hz未过。原planned/measured均244、全部物理/释放/脱离/回位通过，安全0/障碍0/free=true/weld-mocap0；子释放漂移.250053mm、脱离后0N、475/475视频。原评分/四XML/初态/native/释放阈值/运输路径相同，动态轨迹不声称逐位相同，仅float_first_context变化。四独立读回及components-readback.json保留源、原job与所有扫掠。

F2av第二已有200/200反序终态：source9c03874（只追加首站记录、生产代码同667bd6c）干净，35dfc6d2-731d-40fc-a368-be292b940cba中子ae4bb144-0dae-42ea-8c56-5d540251022a→父836e82ed-3640-49d6-8d8c-96c7c3aeb79e，原2/2pass。按父→子process42.849242→38.173933、CPU51.418274→46.695404s，sim78.88→78.82，少1hold/2release拍。排除hold/release后同3366拍/阶段CPU28.157109→24.707023、wall28.242948→24.739509、controller18.387134→16.173074s。原完整周期/评分保留全部拍，诊断剔除不当降阈值。

P95 15.001964→13.067320ms、max116.915574→89.358165ms、慢拍93→54；完整50Hz仍未过。两边planned/measured各244，真抓起/落稳/释放/脱离/回位全过，安全0/障碍0/free=true/weld-mocap0，子释放漂移.258684mm、脱离后0N、493/493视频。源/评分/native/四XML/初态/规划路径均相同，实际只float_first_context变化。三对完整构造器及两站反序同工作量CPU均改善，采用该显式候选为默认，旧compact-status/原版可复跑；116相关默认检查通过。两站绝对秒数不相加，未控制频率和桌面负载，不将全部4–5s宣称分支本身收益。

## F2aw 策略字典转换的最小候选（2026-10-23）

当前运行时asdict对每个字段递归且deepcopy，F2au原未改preferences路径7897调用/.923744累计插桩秒支持筛选。Root GPT仅为所有值均原生不可变标量的策略生成新字典，任何复杂值仍原asdict；无缓存、无新依赖、原字段顺序与复制/错误保持。私有19边界/拥有/原异常检查同值，三对同7897旧权重wall .163390→.039891、.163546→.036686、.176172→.042718s，原screen eligible。它只测同一当前策略，不冒称当前所有独立输入或物理收益。

先前私有报告失败因np.bool_不能JSON序列化，计时未存，不算有效测量；仅改报告布尔转换后重新按协议测。新增测试初版错把原RoutePolicy按字段顺序编码与普通dict排序编码等同，纠正测试参照，生产不变。round62保留两次原错误/source/log/receipt，不抹成全程全绿。生产显式flat_policy_preferences默认false，88相关回归通过；正式完整构造器使用同一策略值并对照原return asdict(self)，避免把不同flag元数据误当输出差异。

F2aw完整构造首版原screen reject/no_median_local_effect，三对.898340→.870102、.827548→.835062、.837497→.865005s保持原件。随后核对18旧样本，route_policy全是预展开tuple、RoutePolicy对象0个；因此没有触达候选方法，不能将它当优化无效的证据。原JSON/log/script和production-fixture-attempt-1-audit.json全部保留。当前控制器fused路径会直接传真实策略对象，修正仅把该字段恢复为同一当前selected冻结RoutePolicy，其余旧样本不动；计时外两侧各18目标调用，双向binding.matches成立。

修正后的原三对wall1.247925→1.395055、1.199280→1.142444、1.243226→1.033598s，CPU1.245282→1.356301、1.197083→1.127939、1.241354→1.031795s；中位wall省.056836s但首对退.147130s，原screen=inconclusive/pair_has_no_consistent_wall_reduction。没有为择绿追加相同测量；本轮不晋级默认、不追加原物理，保留显式default-off源码及复跑以说明边界，不能宣传完整任务提速。私有原prototype的单方法收益仍成立，但不足以证明完整构造收益。

## F2ax 省去固定字段结构访问（2026-10-23）

当前_sweep_binding实际构造35个(name,value)字段；原通用encoder还遍历键和中间tuple。旧18代表形状有21/24/35字段，按7762旧次数计顶层/键/中间访问上界545996，不冒称当前唯一在线值。私有Root GPT候选仅在精确原生tuple对+原生str键时直接保留键，每个值仍用原float-first编码；任意非标准形状完整回退，无缓存/数学/所有权/阈值改变。恢复同一当前RoutePolicy对象后，64检查同值，计时外原helper访问7944→6744、候选实际调用18次，确认触达目标。

三对旧权重局部wall1.257042→1.139917、1.352788→1.195879、1.268308→1.171552s，CPU同向，原screen eligible，等待488.983190s另计。最小生产named_context_freeze默认false，只选单遍快照，异步和非snapshot保持；102相关回归通过。当前未过完整构造器/物理，不按组件晋级。

F2ax正式完整构造三对：恢复相同当前策略对象、真实生产SweepBinding，计时外原baseline0/候选15次实际选中，三个async代表仍原路径。三对wall1.013599→.931669、1.070700→.933880、1.034931→.966241s，CPU1.013199→.931051、1.070290→.933465、1.034522→.966033s，输出双向matches同值，原screen eligible；资源等待15.449619s另计。只支持当前代表结构下完整组件收益，不冒称当前唯一输入或物理任务提速；下一步固化后原名义父→子，默认不变。

F2ax原名义物理终态：source c244b25两侧干净，仅named_context_freeze变化，pair35c4a3cf-f8a9-47f3-a7f3-69a4ad387c94中父01d11403-4eaa-4d22-b245-5744fc79eca8→子bc6c1ad3-43ab-40bb-ac92-69aa638f1b82，原2/2pass。process44.696024→54.841364s、CPU52.918897→62.786353s；sim76.00→75.92s仅少1hold/3release拍。剔除hold/release后同3264拍CPU29.356399→35.194566s、wall29.680359→35.687373s、controller19.533059→23.039843s，明确没有可采用的实际成本收益，拒绝默认晋级且不追加第二工位。

完整P95 16.880320→20.216508ms、max78.270529→127.878064ms、慢拍101→198，完整50Hz未过。原四独立读回通过，评分/四XML/初态/native/运输路径/释放阈值保持；planned/measured闭爪各244点，抓起/搬运/落稳/释放/脱离/回位全过、安全0/障碍0/free=true/weld-mocap0，双方475/475视频。子抬升40.999039mm、hold32.18s、settle7.52s、detach68.58s、释放漂移.249976mm、脱离后0N。

运输worker1.602125→1.769021s、分离1.079568→1.652728s，均joined/owned_ack且cleanup_unconfirmed=false，初始化4.646845→5.632617s计入process；峰RSS1334028→1348544KiB。资源等待288.960736/.050620s单列，实际load1父13.16→16.71、子16.71→19.04，Chrome/GUI/ffmpeg仍有变化，既不把全部10.145s归因编码器，也不据宿主干扰改写实际回退为成功。完整原件及components-readback.json保留于output/named-context-factory-20261023/35c4a3cf-f8a9-47f3-a7f3-69a4ad387c94。默认仍float_first_context；本轮Root GPT候选、原局部收益与物理反证并存。

## F2ay 当前默认的部分回合计数（2026-10-23）

复用原标准cProfile和round10原runner。首段等待最后写于14:53:14 UTC，当前宿主启动约15:06:34，原runner已消失、runs=[]且无evaluation/pstats；归类interrupted_before_physical_start，不是物理失败。保留pair-process-results-before-restart.json、pair-console-before-restart.log和interruption-readback.json，再用同一prepared恢复，未改生产源码或默认。

恢复后source3459889干净，run b27bb920-f451-462b-b8da-e873d6a7a94a原verdict=fail/wall_time_limit。67.58sim、123.021035报告wall、130.914600实际process-wall/83.978684process-CPU。已抓起40.998841mm、持物32.30s，但place=false/settled=0、release_audit未detached，脱离/回位未完成；安全0、障碍0、free=true/weld-mocap0，planned/measured闭爪各244点。视频仅423捕获/0编码、complete=false，不能宣称完整产物。

运输worker6.815939s且joined/owned_ack；分离worker在原墙钟退出时abort_requested=true、state=rejected，joined/owned_ack且cleanup_unconfirmed=false。初始化14.346100s和清理/产物落盘保留在总成本；恢复后资源等待.175506s单列。原启动观察active=[]，运行中出现Blender29863；load1 11.95→42.48，ffmpeg/Chrome亦活跃。保留这些混杂，不能把131s全归因代码、插桩或宿主中的任何单项，也不放宽120s重测。

本轮只提供部分主线程归因：3379完整拍和1未完整拍，_sweep_binding6772次、_immutable_float_first_context3310824次、validate_joint_path3463次、scalar summary22188次；工作线程未插桩。原完整拍P95 73.405771ms/max255.357161ms/2344慢拍属于有插桩且未完成回合，不作无插桩速度对照或50Hz成绩。证据output/post-float-first-profile-20261023/4d681d22-bb8e-4de1-bb14-70580ef579ba/independent-profile-readback.json。下一项先看当前原始数组字段和Python逐浮点编码，不直接重复旧CLI13前置snapshot或已淘汰的named/flat/GC候选。

## F2az 原生数组字节编码筛选（2026-10-24）

Root GPT私有round65-array-bit-context，仅将原生float64一/二维数组复制为独立大端数组，再检查有限值并构造相同逐元素字节token。原类型/形状回退保持，无跨请求缓存；本项与旧CLI13前置snapshot不同。当前构造器原AST静态地图循环在b27bb920记录的六关节规划场景上生成12几何/36数组：24个shape3、12个shape3×3。计时外父36次tolist，子36次astype/36次tobytes，actual_path_verified=true；没有复用已展开tuple漏测新分支。

35项值/错误/负零/非连续/只读/副本拥有检查同值，但同地图字段和当前策略的SweepBinding组件三对wall .651431→1.452214、.662612→1.466075、.668792→1.452461s；线程CPU .651376→1.445277、.662446→1.440201、.668405→1.429502s，全部增加。原screen reject/no_median_local_effect，中位多.800783s，等待719.079694s单列。只按6772次部分回合绑定计数重复同一真实静态地图，不冒称全部35字段、6772唯一在线输入或完整物理收益。

淘汰且不追加全上下文/原物理/第二工位，无生产接入或默认变化。independent-readback.json保留原screen、路径计数、输入来源与三对反证；复跑private round65-array-bit-context/probe.py。已将小数组额外分配的反证反馈给Root GPT：下一私有变体round66-array-row-context只保留原tolist、逐浮点math.isfinite/struct.pack并减少已知浮点行中的递归分派，不改精度/阈值/缓存。尚无该变体成本结果。

F2ba准备时发现旧cache/so101-graspgenx目录已缺失，并非只有解释器软链接失效；原因/操作方未知，未推断为算法故障。原语法命令127记录于round66/runtime-missing-before-probe.json。优先检查了项目已知环境位置和用户数据目录，未发现迁移副本；复用已安装CPython3.11.15，在.local/share/ros2-factory/venv311新建独立环境，不重新拉取GraspGenX仓库或改变项目执行架构。

原requirements.txt的SciPy1.18.1只支持Python>=3.12，不能充当已删除3.11环境的完整锁定清单；首安装解析失败保留runtime-install-attempt-1.log/json。保留已记录的CPython3.11.15与MuJoCo3.15.0，兼容解析后NumPy2.4.6、SciPy1.17.1、Mink1.1.0、OMPL2.0.1、imageio2.37.0、imageio-ffmpeg0.6.0，18包精确清单存runtime-freeze.txt。旧NumPy/SciPy版本不可考证，因此明示为新环境，不声称完全还原或跨环境拼接原秒数。

runtime-recovery-readback.json确认原station_executor等9项模块导入，原六关节规划场景nq=nv=6/ngeom=65，CPU reset/step10次至.020s、qpos有限；不渲染、不接实机。该检查不是完整抓放或50Hz验收。后续原版/候选须同用新的明确Python路径；若进入物理A/B，以其中原版的原评分作为新环境基线，保留旧物理证据的旧环境范围。

## F2ba 逐行浮点编码的完整组件反证（2026-10-24）

Root GPT按F2az反证，仅对原生float64一/二维数组保留原tolist拥有快照，逐行执行原math.isfinite/struct.pack，省去每个叶子的通用递归调用；其余类型/形状原回退。私有round66静态地图组件35检查同值，计时外父331次encoder/36次tolist，子79次encoder+60次行函数/36次tolist，实际触达。6772次重复三对wall .649227→.628857、.639544→.628041、.639656→.624185s，CPU同向，原screen eligible；仅中位15.470ms组件收益，不是任务提速。

首次完整探针在导入VisualGraspController时发现cv2缺失，未进入setup或计时；原CLI入口的延迟导入此前没有触发该模块。full-probe-attempt-1.py/log/json保留，补装opencv-python-headless5.0.0.93并固定NumPy2.4.6，当前19包清单存runtime-freeze-with-vision.txt，原18包与初组件runtime记录不覆盖。runtime-vision-readback.json确认实际视觉控制器导入，仍不宣称完整物理通过。

完整探针复用当前全部native配置、原控制器构造器、原RGB定位估计/复位编码器及0秒原update，完整35字段中40个原生数组；父encoder477/tolist40，子encoder206+行64/tolist40，双向matches同值。setup2.836590wall/2.022693thread-CPU秒，update=running、stage=approach；记录为实际起步快照的完整_sweep_binding，不冒称所有阶段或唯一在线输入。等待3.080383s单列，清理走原close/native.close。

完整三对wall .878410→.935663、.900879→.898933、.962584→1.188648s；线程CPU .877217→.929914、.898603→.897447、.959851→1.181438s。原screen reject/no_median_local_effect，中位wall多.057253s，两退一微改善，不重复择绿。淘汰，不接生产、不追加原物理/跨站，默认float_first_context不变；independent-local-readback.json与independent-full-readback.json分别保留局部准入和完整拒绝，不能只挑局部正结果。

下一回合F2bb是新环境原版复跑验收：旧解释器/依赖目录缺失，虽然已完成CPU reset/step及真实控制器初始化，重建后尚无完整原物理裁决。沿用原名义场景、原默认、原计时和90sim/120wall，通过完整抓放/释放/脱离/回位确认可复跑，再用该环境的实测瓶颈选下一候选；不重复上下文微调、不把这轮无候选基线算作提速。

## F2bb 新环境完整原物理已通过（2026-10-24）

原round67-runtime-baseline/prepared-path.txt指向output/runtime-baseline-20261024/9a4b28f8-b4bb-480a-8d80-a7e09c20471a。source cb1cbb11两处来源及评分器均干净，当前19包独立环境，run9d93c587-1077-41de-af32-7bcf7f749b63原verdict=pass。原75.84sim、27.365738报告wall、28.492444实际process-wall/36.274256process-CPU；等待Blender释放81.839267s单列，前后active=[]，load1 5.42→3.97。这是新环境可复跑核准，不是新候选A/B，也不能与旧环境绝对秒数拼成加速。

真实抬起40.999072mm、持物32.16s、静稳7.52s；原抓放、释放、脱离和回位完成。release_audit通过，68.50s脱离、XY漂移.249938mm、脱离后峰力0N；free=true/weld=0/mocap=0，安全停机0/障碍接触0。planned/measured闭爪各244点，trajectory全部有限/arm_valid，3792完整拍、无不完整拍；视频474/474。运输worker.939300s、分离.501839s，均joined/owned_ack、cleanup_unconfirmed=false；初始化3.419332s与清理/视频/落盘均保留在实际进程成本中，不将嵌套worker成本相加。

完整周期P50 6.150171ms/P95 8.462118ms/max47.300546ms，仍5拍超20ms：approach11.20s 23.600519ms、close19.52s 21.025798ms、transport41.80s 38.038357ms、release66.42s 47.300546ms、separate68.14s 27.505590ms。前三处/释放主峰的controller wall接近线程CPU，不能一律归因宿主等待；分离准入controller22.823ms/CPU19.019ms且实际核对205保存样本。尚未给GC与准入细项打点，不凭位置猜根因。independent-runtime-readback.json保存逐项核准、所有完整周期、生命周期与主机范围；完整50Hz仍未过。

F2bc只读定向归因由Root GPT复用round53 GC观察器，并只给原_poll_separation启用cProfile；原GC enable/thresholds和原方法结果保持。不同于F2ay全主线程插桩，本轮仅核准新环境5拍长尾的GC重合和准入子调用，计时只作归因，不作新性能A/B或默认晋级。private round68-runtime-tail-observation保存probe-origin.json/probe.py；原共享资源观察/90sim120wall/244/全部回退保持，终态前不改源提交。

## F2bc 实际长尾归因与接近搜索瓶颈

原观察回合05cf510a-a394-4fc9-a0b9-1509173da003、source5a3f012干净，原pass/75.84sim，实际28.709569wall/37.053630CPU，等待.029944s单列。完整3792拍、原planned/measured各244、完整抓放/释放/脱离/回位均过；independent-runtime-readback.json和independent-tail-readback.json位于output/runtime-tail-observation-20261024/bbbbd0d4-fbc4-4922-8a4b-e9027a7120a3。观察后的P95 8.436273/max46.110834ms/8慢拍只属于插桩归因，不替换F2bb无局部profile基线或宣称提速。

主线程gen2三次22.581675/33.800125/39.786837ms，分别与approach11.44、transport41.52、release66.32s长尾拍重合；另一次47.430294ms在循环外。GC before/after均enabled=true、thresholds=[700,10,10]；无callback错误/未闭事件，timer与原方法恢复。49次原_poll_separation合计81.748ms插桩累计，其中_separation_binding58.567ms、一次205保存样本校验7.002ms；这些嵌套时钟不可相加或冒称无插桩耗时，也不将F2bb另一回合的每个尖峰重新分类。保持已拒绝GC窗口的旧反证。

另读F2bb原planning：接近路径249原始点，77次连接尝试中75失败，候选采样7494点、最终复核513点，耗时1.565786s，最后选0→173→248。瓶颈是按远到近顺序反复验证相近的失败连接，不是减少执行等待帧。此证据支持只调整接近路径搜索顺序；其余运动段和原裁判保持。

## F2bd 中点搜索顺序的局部实测

Root GPT私有round69-shortcut-order先试整段直连，再对中点连接做有界探测，返回实际已通过原2mm证书的连接；没有命中则按原降序遍历未测候选，预算耗尽退回原相邻边。几何可行性不保证单调，此启发式不宣称全局最长连接；所有选中路径仍用原1mm守卫、.005rad完整复核。没有使用物体真值、缓存不同姿态判定或减少244点闭爪检查。

私有同一原始路径三对wall1.870799→.670654、1.851120→.635369、1.821911→.627067s，CPU同向；候选尝试77→10、候选状态7494→2237，最终仍513点且选中路径逐binary64相同，原screen eligible。等值范围是选中路径/最终判定，不是有意变化的搜索trace。8项边界检查覆盖非单调回退、零/一预算、原最终拒绝及原异常对象透传。

最小生产approach_midpoint_order默认false，原shorten_path默认降序代码保留；仅_plan_approach显式读取该选项，放物后的返回规划仍走原默认。正式生产组件三对wall1.608318→.526674、1.583427→.531428、1.576164→.515375s，CPU同向，路径/最终513状态保持，原screen eligible、中位省1.060789s。private production-local-screen.json和independent-local-readback.json留存；这些仍不是完整物理收益。默认float_first_context不变，显式route_strategies/approach_midpoint_order.py待原两站物理核准。

## F2be Kaggle 执行与搜索顺序的跨坐标反证

用户回答“kaggle做”后，本地等待 runner 精确停止（尚无实际评测），原后台动画没有被终止。so101 定时任务已删除。官方 Kaggle CLI 2.2.5 独立环境、既有 muqiaoqiao 身份和私有 kernel 已实际验证；不是新调度平台，不向其他对话发消息。源码固定116b090，云端无本机凭据。

云 Python 3.13.15 原生 venv/ensurepip 失败、astral.sh 403 均保存。官方 PyPI uv wheel 创建环境成功。T4 分配存在，但实际 EGL 是 Mesa llvmpipe；v3 原两回合虽然抓放/释放/回位完成，视频仅148/474、158/475，均原120s墙钟失败，不改判。v4查实际GL vendor/renderer才定位。v5按nvidia-smi实际580.178.04，从NVIDIA官方Ubuntu24.04仓库解包同版本libnvidia-gl/gpucomp到临时目录，私有vendor JSON与LD_LIBRARY_PATH使实际renderer=Tesla T4；640×480同模型热身约118→1ms，只记环境收益。官方 [driver capabilities](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/docker-specialized.html#driver-capabilities) 区分compute/utility与graphics，不从GPU可见推断图形加速。

修复后v6名义原版ab43f72a→子4a07667e；v7已有200/200反序子8908ce53→父a0257b9e；v8方块X+5mm反序子6dc67851→父4d1b2564，6/6原pass。按父→子process wall/CPU分别59.759498/69.506346→54.987126/64.746146、55.744291/65.532078→55.200622/64.747542、51.424321/60.168788→51.585106/60.567585s。搜索4.015863→1.330635、3.611382→1.100844、3.506285→1.156890s，尝试77→10、77→10、76→10；最终路径各对逐位相同，最终513/513/505点完整复核保留。

方块偏移组是在原±10mm范围内固定X+5mm，仅改同一物体输入，不改静态环境/判据，策略仍只用RGB定位/q6。两个原有工位取料点相同，所以增加此单一变体用于验证与接近优化相关的坐标。偏移组虽搜索省2.349394s、初始化省2.168247s，但同3283个非hold/release拍CPU33.626948→34.305411s，整程反慢.160785wall/.398797CPU；不把分段收益当完整收益，不追加同例追绿。默认float_first_context不变，中点搜索只保留显式来源，不晋级。

每轮原244点、自由物体、碰撞/限位、释放漂移、脱离/回位和所有worker清理均通过；v6视频474/474两轮，v7两轮492/492，v8父478/478、子477/477。完整P95父→子17.067704→16.896831、16.196930→17.095961、14.852263→15.522410ms；慢拍127→128、147→150、117→115，完整50Hz仍未过。原软件EGL失败和这些安全通过分别记录，原时钟未删拍。所有JSON/视频与五种独立读回保存在output/kaggle-midpoint-factory-20261024，复跑见experiments/colab-twin/KAGGLE.md。


## F2bf 预绑定Struct的私有完整组件结果

原F2ay部分插桩回合确实调用struct.pack1654240次、浮点优先helper递归3310824次；仅用作结构线索，不把旧3.11环境的秒数当Kaggle3.13成本。Root GPT私有round71只把有限float叶的struct.pack('!d',value)替换为一次构造的Struct('!d').pack；每个值仍新建原byte token，类型、有限检查、负零、排序、数组tolist复制和错误保持，无结果缓存。

私有Kaggle muqiaoqiao/so101-float-packer-component-20261024 v1复用上轮v8成功baseline的原grasp-planning.xml、真实RGB估计和reset q6，原控制器构造/0秒update后，仅重复完整_sweep_binding。29值/错误/拥有检查通过；计时外原229次generic pack，子1次generic+228次compiled；两侧helper均477次，双向matches同值，确认走到目标。6772次重复的三对wall1.450869→1.382857、1.498944→1.401262、1.444858→1.422921s，线程CPU同向；原screen eligible，中位省.068012s。范围仅一个真实起点的完整组件，不是全阶段、唯一在线输入、物理成功或50Hz成绩。

原cloud wrapper曾携带上轮midpoint的candidate_origin描述；实际candidate.py/probe源码和当前round71来源文件明确为预绑定packer。原字段不覆盖，independent-component-readback.json注明这一元数据复用瑕疵并核对实际candidate源码逐字节相同。后续正式packet使用本轮来源，不冒称CLI生成。组件原件保存在output/prebound-float-factory-20261024/component-v1。

生产只加默认关闭的prebound_float_pack选择及同值helper；中点搜索不叠加。首轮新增fallback测试错误地向原非snapshot路径传ndarray，原拒绝正确；仅改测试为该路径支持的标量tuple，未放宽类型或修改实现。77项相关测试通过，原所有权和原非snapshot/named路径保持。正式接入后的完整组件尚未测，不凭私有结果宣称生产提速。


F2bf正式组件v2已实际完成：source9c585cd、实际encoder_source=configuration_sweep.py/_immutable_prebound_float_context，同一候选策略对象中只将reference强制为旧encoder。29检查与实际compiled228/generic1路径通过；三对wall1.585310→1.532471、1.577534→1.545221、1.656146→1.539245s，CPU同向，原screen eligible，中位省.052839s。该v2来源字段已改为本轮描述；v1旧描述原样保留并独立说明。原件component-v2和independent-component-readback.json不当物理成绩。

原物理source9c585cd，两侧干净、唯一prebound_float_pack变化。名义paira47e7ef1：父e6536f3d→子b2f25a5f，wall64.356296→62.556288s、CPU74.174232→72.902600s、sim75.82→75.86。200/200反序pair363c3c4b：子de6815c8→父04128d49，按父→子wall60.958649→62.650278s、CPU71.690680→73.237305s，sim均78.66。4/4原pass，原计划/实测244、自由物体、全部碰撞/释放/脱离/回位与workers清理均过，视频名义父474/474/子475/475，第二站两侧492/492；原C库/flags/四XML/初态/阈值与规划运输路径保持。

同量非hold/release：名义3264拍CPU41.327230→41.396429s；第二站3366拍39.704162→39.870501s，均无可采用的控制链成本收益。原完整P95父→子19.101252→19.029101、17.186022→17.951875ms；慢拍148→148、154→162，max149.687→57.914、148.470→151.417ms。完整50Hz未过，默认float_first_context不变。局部打包收益保留为事实，但不晋级或追加物理追绿。

实际process wall减去全部原episode生命周期/完整周期后，名义父/子余量2.407206/1.155890s，反序第二站父/子1.152166/2.397721s：先运行者约多1.25s，独立于候选。这是计时窗外启动/收尾差，不凭猜测全算为import或算法。名义原版最长拍在hold30.999999s，callbacks130.985wall/4.464thread-CPU毫秒，源数据只说明主线程等待。F2bg定向观察IO和全局GC，再区分文件操作、其他线程暂停与导入冷启动；不先改变GC或发布调度。


## F2bg 原默认回调/启动的真实归因

Kaggle私有so101-callback-attribution-20261024版本1，源码450e5e34，原e7e5fd52原pass。原3788拍、244/抓放/释放/脱离/回位/完整474帧、两个worker清理均过。52.392385process-wall/61.514648CPU秒只属于带观察的默认回合，不替代无插桩性能；P95 15.041296ms/max60.788477ms/115慢拍，完整50Hz未过。

160次GC事件中主线程gen0/1/2为145/13/1，worker gen0为1。唯一gen2为35.373009ms，在50.90s控制器区间；未找到worker GC解释先前131ms回调的证据。本轮callback整体最大6.044649ms，atomic_json/文件write/replace最大3.246828/2.183711/1.078208ms，最慢atomic区间无GC重叠；scene.update最大3.126980ms，与1.640948ms主线程gen1重合。嵌套时钟不相加。所有方法恢复、观察无错、GC设置保持。先前131ms等待未复现，不声明根因已解决，不据此造异步发布器或改GC。

同模块冷/热导入4.345017/0.774024wall秒，CPU3.012986/1.977449秒，4个目标pyc由无到有；CPU含导入库线程。证明当前冷/热差和缓存创建，不将此前约1.25s计时窗外余量全部算导入。准备成本分列。原件及independent-attribution-readback.json在output/callback-attribution-20261024/v1。

## F2bh 静态真实姿态的完整视觉组件

私有so101-perception-components-20261024 v1复用上述通过回合的场景和0..6s关节姿态，静态自由物体仅用于生成测试图像，未给控制器真值。13份640×480 uint8 RGB，完整渲染40次中位1.937163ms（update_scene .028104、render1.835264、copy .071582ms），原定位39次中位4.812061ms。另行cProfile显示mask表达式是定位函数最大self成本，cvtColor和连通域各约.634/.930ms。39结果同值，但与原循环约20ms区域不一致，不能把组件结果当整拍或唯一根因。

独立读回首次误用共享64×64 graphics preflight形状检查，已保留independent-readback-attempt-1.json；改读实际perception-frames.npz，确认13×480×640×3 uint8，当前readback通过。没有改探针或物理结果。该反证只属于读回目标选择，非算法失败。

## F2bi OpenCV掩码的局部收益与完整任务反证

Root GPT沿用现有OpenCV5的inRange、uint8饱和减法与compare，保持HSV H40..92/S≥55/V≥30、G-R≥10、G-B≥6。负差值饱和到0仍不通过正阈值；输出仍为bool，再进入完全相同的连通域、尺寸/遮挡拒绝和标定计算。[官方数组运算](https://docs.opencv.org/5.0/main_modules/core_array.html)核实端点包含和饱和语义，实际5.0.0穷举16777216种RGB并逐值核验，不只凭文档推定。

私有component v1：308同值/负步幅检查、原19项视觉测试均过。完整render_rgb+localize（104帧/次）三对wall .778854→.658316、.853530→.735098、.863767→.741707s，线程CPU同向；原screen eligible，约省1.159ms/图，仅为组件准入。未新增生产开关，实际物理通过private physical-probe.py外围显式替换run_visual_grasp的定位函数，副本仅替换mask表达式，其余函数原源码复用。两侧策略/控制器/评分相同，实际差异由detector-implementation.json记录，不能因Git clean或route-policy delta为空就把它误写成完全原实现。

原物理名义dd574067：父ccf67022→子36717b2e，wall56.898594→55.672351、CPU65.968246→64.966110s、sim75.86→75.80s。200/200反序ae817356：子4305dc0a→父b55e90bc，按父→子wall59.184210→60.791135、CPU69.114080→70.791598s、sim78.64→78.70s。4/4原pass，planned/measured各244，原native/flags/XML/初态/裁判/安全阈值和规划路径保持；释放/脱离/回位、自由物体及worker清理全过，视频475/475→474/474和492/492两侧。

真实循环每侧14次定位（含初始化），候选mask实际调用14次，baseline0；14个结果与timestamp一致，方法全部恢复、GC设置保持。循环13次定位分别62.949→50.087、66.294→52.379ms，组件收益在真实任务中重现。此收益只约13ms，不能解释process秒级差；同3264/3366非hold/release拍CPU37.218970→36.590408、38.984965→39.796654s方向不一致。完整P95父→子16.831275→16.145838、17.496097→19.118577ms，慢拍125→121、157→180；两侧接近段仍13慢拍。无可靠完整任务收益，保持私有证据、不切默认、不追加追绿回合，完整50Hz仍未过。

额外实际render_rgb在名义两侧分别191.311/191.062ms（13次），约14.7ms/次；这是下一项比对的真实线索。DeferredVideo在控制退出后另进程渲染，不能把该耗时归因同时录像。F2bj只读拆控制进程GL与渲染子区间，再决定改动，不据预检NVIDIA结果推定控制进程或先禁阴影/降分辨率。原件output/opencv-mask-factory-20261024及independent-physical-inventory.json保存全部对照。


## F2bj 控制进程的实际GL与渲染子区间

source b37171cb干净，私有so101-live-render-attribution v1原cbe532f0原pass；75.86sim/54.252358process-wall/63.422622CPU，3793完整拍，原抓放/244/释放/脱离/回位/475帧与worker清理全过。P95 15.700948/max59.458898ms/115慢拍仅属于观察回合，完整50Hz未过。

从真正正在渲染的context读取NVIDIA/Tesla T4/driver580.178.04。13次RGB中update_scene中位.044484ms、合计.589194ms；Renderer.render中位14.562754ms、合计189.129708ms，RGB整体190.717758ms。方法与GC设置全部恢复、无观察错误。14个状态/派生pose/RGB和实际MJB保存，仅用于离线图像复放，未进入策略输入。原录像仍在控制退出后另进程渲染。

新进程对积分状态forward和保存render poses两种复放均0/14逐像素相同，分别最多48/56像素不同；两种复放虽中位1.976/1.799ms，不能叫同输入加速。保留所有差异和原始exact=false，不放宽像素判据。原cloud-run通用STATE.scope沿用旧paired字样；实际cases/runs只有1个原默认观察，observer/独立readback明确无候选/无A/B。元数据用词瑕疵保留说明，未改原物理裁决。

## F2bk 同context出图节奏与像素读回

私有so101-paced-render-observation v1沿上轮原MJB/姿态，在一个context内做burst与按实际中位.233840443s间隔出图三对，各42样本。间隔单列，不把sleep计为渲染成本；NVML只读clock/pstate，不改变设置。实际Tesla T4，NVML全部query成功。逐像素比较仍false、最多59像素不同，不因进入同context就宣称已等值。

三对burst/paced的render中位2.000/2.340、14.457/14.701、14.006/14.722ms；连续模式后两组同样慢，不能把“只要连续渲染”当修复。时间集中在mjr_readPixels：GPU0调用前P0/585MHz的23样本读回中位1.459570ms，P8/300MHz的46样本13.905005ms；其余P8/360、375MHz各6/9样本也约13.4/13.5ms。此处是状态关联，不是控制过频率的因果实验。GPU1始终P8/300MHz。

已核对[NVIDIA原生锁频/恢复说明](https://docs.nvidia.com/deploy/nvidia-smi/index.html)及[NVML查询](https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlDeviceQueries.html)。后续F2bl优先尝试当前私有任务内原生命令、明确设备与finally恢复；未授权提权、GPU reset、驱动/功率修改或别的任务资源操作。平台不允许时记录真实拒绝，不重复权限尝试。图像/控制/评分均不变，环境收益不能冒充算法收益。


## F2bl 原生时钟权限真实拒绝

私有so101-clock-control-component-20261024 v1确认Tesla T4/GPU0和空GPU进程表后，原生--lock-gpu-clocks=585,585返回4，平台明确拒绝权限；finally --reset-gpu-clocks同样返回4。clock_applied=false，没有执行有效时钟对照，没有成功恢复回执，不进行提权或重复权限尝试。原件与independent-clock-readback.json在output/clock-control-component-20261024/v1。

## F2bm RGBA原生读回：同像素但更慢

核对MuJoCo3.15.0原生mjr_readPixels与Python绑定，私有候选仅临时设置readPixelFormat为GL_RGBA，原生完成MSAA resolve，再复制为原RGB3；异常/退出恢复原格式，深度/分割路径回退原实现。28次同一已绘制帧按两种读取顺序均逐像素相等，缓冲区边界/GL错误0/格式恢复通过。4项局部语义检查和84次定位同值保持。

完整渲染+定位三对原版→候选.168728→.306468、.281103→.304399、.283074→.307708s，全部更慢，原screen reject/no_median_local_effect。42次实际RGBA路径、0回退，不以同值掩盖负收益，不进行该候选物理。私有so101-rgba-readback-component-20261024 v1；output/rgba-readback-factory-20261024/component-v1及independent-component-readback.json保留原件。

## F2bn 真实异步相机：视觉长尾改善，整程收益不稳定

来源Root GPT，未冒称CodeBuddy生成。沿用AsyncTransportPlanningJob的plan_type扩展、owned/join/close，以独立模型和逐帧MjData复制在worker渲染RGB。控制器只收到原localize_green_target输出与capture timestamp；原1s TTL、冻结后迟到无效帧拒绝、初始同步定位及最终截图保留。worker驻留时间与控制重叠，不相加为规划成本。原评分器、原规划/控制和安全条件未改，私有camera-implementation.json显式记录真实替换函数、一次episode调用及所有还原。

本地5项协议测试通过；私有so101-async-camera-protocol-20261024 v1实测14个EGL帧定位相等、timestamp保留、主qpos/qvel不变、context在owned线程关闭。该组件只验协议，约1ms快照提交不称完整50Hz。完整物理另用so101-async-camera-physical-ab-20261024 v1/v2，同source dfb9fc32，名义原版→候选与已有200/200候选→原版。

| 工位 | 原版→候选process wall / CPU(s) | 完整慢拍 | 视觉live慢拍 / 最大拍(ms) |
| --- | --- | --- | --- |
| 名义 | 59.740308 / 69.670976 → 56.980533 / 66.754354 | 124→103 | 13→0 / 34.981→18.471 |
| 200/200，反序 | 60.836932 / 71.404051 → 61.781233 / 72.478014 | 154→147 | 13→2 / 33.533→20.769 |

4/4原pass；XML/初态/native核与flags/原裁判/阈值、接近和运输规划路径均同。planned/measured各244，全部碰撞/自由物体/抓放/释放/脱离/回位保持；视频474/474→475/475、492/492两侧完整，两个planner与相机均joined/owned_ack、无cleanup_unconfirmed。两子释放漂移.249861/.258347mm，脱离后峰力0N。

两站每侧14个定位输出/拍摄时刻相同，候选13个周期帧全部送达、无丢弃，送达年龄20–60ms。视觉live各328拍；原完整P95 17.264→16.054、17.551→17.533ms，但完整最大56.058→55.105、155.017→152.843ms，不能声称全程50Hz。sim75.84→75.86、78.62→78.72s，仅hold/release计数变化不记提速；同3264/3366非hold/release拍CPU39.173939→36.745708、39.675125→39.691872s，第二站无改善。

决定：视觉阻塞削减是可复现的局部调度收益，尚不足以替换整程默认；保留私有候选与反证，不追第三站。output/async-perception-factory-20261024/independent-physical-inventory.json汇总完整/相机/搜索/策略/worker读回。私有round79-async-perception保存candidate.py/camera.py、generated原episode适配、physical_probe.py/read_camera.py及primary/cross路径；云端不可变v1/v2可恢复完整来源。Next F2bo的1ms切换间隔是待测假设；[Python3.13官方文档](https://docs.python.org/3.13/library/sys.html#sys.setswitchinterval)明确该值只是理想时间片，真实切换可更长，不能宣称硬实时。


## F2bo 实际挂载来源与1ms调度反证

Root GPT仅用sys.setswitchinterval(.001)建立私有作用域，finally恢复原.005；不改物理控制或图像路径。首版组件指定旧名义run1d465740，但挂载不含该回合，IndexError发生于任何测量之前。v1原件/独立失败读回保留，不算算法失败或成功。v2 mounted-inputs.json实证仅含最新cross原版5635508a，明确发WARNING后采用这个已经独立验收的原版，三对始终共用同一96行输入。

[当前Kaggle元数据说明](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels_metadata.md)的kernel_sources格式为用户/任务名，不能以附加/version假定挂载旧输出；本机CLI2.2.5的源码下载另有version_label支持，不混淆下载与挂载。后续组件先读实际挂载来源。这里只记录本次实测，不推断其他接口绝不支持版本化。

私有so101-switch-interval-component-20261024 v2：原96次配置扫掠+payload弦检查与原运输planner并行，六例所有查询均发生在planner存活期间；各检查完整输出一致、规划路径逐位同、worker全部owned/joined、间隔与异常退出均恢复。guard窗口2.006142→1.977355、2.034717→1.970130、1.973015→1.943474s；含join总wall2.414782→2.409544、2.435837→2.371231、2.467487→2.380770s，CPU同向。原screen eligible只是原物理准入，不是任务通过。

单次查询主CPU中位仍约12ms，wall约21ms，差约9ms；慢查询64→63、63→66、61→63，没有一致降低。1ms仅理想解释器时间片，未证明原等待由GIL引起，不能据本次小收益宣称硬实时。

私有so101-switch-interval-physical-ab-20261024 v1/v2，source281b049，原同步RGB及float_first路线保持，只私有作用域改变解释器调度。switch-implementation.json记录实际每次控制update值、唯一调度改动、原episode方法不变、before/after及观察方法恢复，防止相同Git/route被误读为无实现差异。

| 工位 | 原版→候选process wall / CPU(s) | 完整慢拍 / P95(ms) | 同量非hold/release CPU(s) |
| --- | --- | --- | --- |
| 名义 | 58.905745 / 68.831895 → 56.723904 / 66.385433 | 126→115 / 17.285→16.194 | 38.575252→36.964280 |
| 200/200，反序 | 70.954440 / 82.778527 → 72.053734 / 83.941889 | 221→276 / 20.709→21.659 | 46.727576→47.090300 |

4/4原pass，源/原XML/初态/native核/flags/裁判/阈值、接近与运输路径、14个同步定位输出均同。planned/measured各244，全部物理安全、自由物体、抓放/释放/脱离/回位保持；worker全部owned/joined无abort/cleanup_unconfirmed，视频474→475和493→492完整。子释放漂移.249861/.258422mm、脱离后0N。sim75.82→75.86、78.74→78.68s仅等待拍变化，不当算法提速。候选最大53.142/178.009ms，完整50Hz未过。

第二站所有完整成本与毛刺回退，淘汰1ms，不改变默认，不再扫间隔或追绿。原件output/switch-interval-factory-20261024/independent-physical-inventory.json；私有round80保存候选、组件v1失败/v2来源收据、原物理和read_switch.py。两Kaggle任务的不可变版本可恢复源码，但输入挂载必须另读实际来源，且不跨云实例串累计加速。下一项只读cProfile归因同96个guard，函数self/cumulative计数分列；插桩时长不作基准。


## F2bp 分析器自验与有效调用归因

私有so101-hold-guard-cpu-profile-20261024 v1，source6ce44bc：cProfile(timer=time.thread_time)的原数值/worker/退出检查通过，但独立检查发现后台SciPy规划帧、28个负时间条目，短窗口内还有上千秒self时间。原profile_completed=true仅覆盖当时原始检查，不代表计时有效；independent-profile-readback.json明确measurements_valid=false，原统计保留，不用其时间或调用图提出优化。

已读[CPython3.13.15的_lsprof实现](https://raw.githubusercontent.com/python/cpython/v3.13.15/Modules/_lsprof.c)：本版enable通过sys.monitoring全局事件注册回调，不能假定只收主线程；混合事件不能用各线程独立累计的thread_time当同一时间轴。[同版本profile.Profile.runcall](https://raw.githubusercontent.com/python/cpython/v3.13.15/Lib/profile.py)使用sys.setprofile入口。改用后保留原96检查/并行原planner，不改变算法、模型、间隔或物理。这里不泛化其他Python版本的行为。

v2实测profile回调只有主线程；无scipy/optimize及_run_transport_plan帧，全部时间非负，只有一个真实guard loop，累计3.313124s不超过实际带插桩主线程CPU6.082037s。profile伪文件条目还计入准备/收尾，明确排除它的4.576733s self字段，不把它当算法热点。原96次guard输出与F2bo未插桩原版完全相同，规划路径相同，worker/钩子/5ms设置均恢复，独立有效性检查通过。

可靠调用计数为：_configuration_sweep96、_sweep_binding192、_immutable_float_first_context91776、_immutable_context17472、isinstance213792、pack43872、mj_kinematics5472。纯Python分析器明显增加高调用量路径开销，因此只用调用结构定位候选；self/cumulative时间不当未插桩成本或整程加速。原件output/guard-cpu-profile-20261024/v1/v2分别保留失败与修正版；私有round81包含来源和准确代码。

候选F2bq先沿用float-first编码，仅对type(value)恰为内置float/tuple/list/bytes/str/int/bool的值缩短分支，其余交回原函数。38项本地对照覆盖finite/signed zero/shape/子类/数组/错误/owned副本，全部同值。没有重复采用旧prebound pack，也不改缓存或安全规则；尚未测收益。新组件继续用同96个原guard与原planner，检查实际binding token和函数路径后再三对无分析器计时。

F2bq实测v1在测量前UnboundLocalError；v2仅消除局部sweep别名遮蔽。三对guard1.695650→1.680278、1.775722→1.989206、1.915226→1.714951s，含join差+.006890/+.172954/−.178682s，CPU差+.004172/+.294101/−.283681s。输出、binding、路径及清理均同，原screen=inconclusive。独立protocol_valid=true不等于收益，停止此方向，无物理晋级或默认变化。

F2br假设来自原bf95258a实际轨迹：hold177拍jaw残差中位.106221101rad；transport1294拍中位.106221519rad，双指最小1.474156/1.486890N；lower130拍最小1.485481/1.482202N。原contact-workcell.xml工件mass=.01kg、friction=.8/.005/.0001。闭合目标与被工件阻挡的实际角度之间的距离是实际在线认证工作，不能跳点；可试编码器一次性减半残差作为策略变化，但必须实测力和物体保持，不将静态摩擦估算作验收。候选不读取目标真值；原始闭合及释放扫掠、安全条件保持。

F2br v1原采集通过，但静态构造了collision_scene旧类，退出缺native属性；首例耗时/汇总不采用。v2改用原捕获控制器的实际conservative类型，记录native batch与正确checked_states字段，未改候选或物理。Kaggle原采集13e4dd07原pass，原planned/measured各244、全部自由物体/释放/脱离/回位/完整录像及worker清理独立通过；父进程包含静态试验，不作性能基线。

三对独立live MjData副本，3.5sim/175拍：每侧checked_states9625→5915；guard wall1.790512→1.333257、1.794487→1.319471、1.816197→1.308139s，CPU同向。原全部间距、payload检查、原有限/碰撞/持续夹持判据保持；每对关节、物体状态、双指力逐拍完全相同，双方最小1.701371/1.706333N。候选目标.015→.068110524，仅缩短被完整认证的命令弦。原XML夹爪forcerange±.15，候选仍处大闭合误差区；静态观测不支持“力降低”的原猜测，后续直接记录实际actuator_force核验饱和，不把相同静态状态推广为动态保证。

私有完整候选只在lift→hold读取一次编码器/旧命令、沿原1.5s hold连续坡道改变jaw，后续hold/transport/lower保持该目标。原_poll_transport仅两个待认证端点同步为实际目标，AST还原后与原方法完全同；不修改检查主体、模型、阈值或评分。16个实际类局部检查含一次锁定、起止连续、阶段范围、两个端点、异常退出还原。待原完整A/B，不切默认。

F2br私有原物理source6ef85f70：名义796670f1（6791f1d4→519e72b2）、200/200反序02761778（a7ea4be0→0ee9df35）共4/4原pass。两侧模型、初态、原scorer/阈值、native库/flags、接近/运输路径与14次定位输出相同；全部planned/measured各244、释放/脱离/回位、完整视频与worker清理保持。真实覆盖另见preload-implementation.json；same route-policy不等于没有控制器改动。

| 工位 | 原版→候选process wall/CPU(s) | sim(s) | 非hold/release CPU(s)/拍数 | 完整慢拍/P95(ms) |
| --- | --- | --- | --- | --- |
| 名义 | 62.630972/72.755506→56.096788/66.642117 | 75.80→76.62 | 40.803190→34.857922，同3264 | 128→138 /17.793→16.879 |
| 200/200反序 | 61.429735/72.007610→56.591874/67.158207 | 78.70→79.76 | 40.090904→34.652309，3366→3367 | 165→143 /17.917→17.226 |

第二站lower反多1拍，不能说所有非等待工作量相同。原native全扫掠checked_states110382→66860、117561→70892，分辨率不改，目标弦变短；候选hold多38/50拍仍较快。持物三阶段实际actuator_force每拍为原负向饱和−.15，模型未调。释放漂移子.211512/.172091mm、脱离后0N；候选最大53.764/147.724ms，完整50Hz未过。

原运输worker wall2.290536→2.690439、2.656558→3.323889s，分离worker1.149735→1.313412、1.529367→1.482379s；只说明并行规划等待未优化，不能把整体收益称规划提速或将worker时间累加。原接近planner planning_seconds.138820→.137816、.174164→.184948s单列保留。原件/独立pair、feature、policy、search、startup、physics和库存位于output/loaded-jaw-preload-factory-20261024；private kernel physical v1/v2保留准确源码。

正式接入只新增default-off布尔项、显式策略文件和上述四处控制行为；原方法覆盖被移除，原scorer/模型/C++未改。166相关测试通过，待绑定新源码的原物理，不先改变默认。

正式源码46031fff的Kaggle formal-ab v1/v2均终态：名义63c9aafd、200/200反序44f6782a共4/4原pass。native_route_strategy标记与实际loaded_path/preferences/方法路径均检查：两侧都运行Git控制器，唯一策略差异loaded_jaw_preload。原模型/初态/native kernel/flags/裁判/阈值、接近/运输路径、244点和全部自由物体/释放/脱离/回位/录像/清理保持。

| 工位 | 原版→正式策略wall/CPU(s) | sim(s) | 非hold/release CPU(s)/拍数 | 完整慢拍/P95(ms) |
| --- | --- | --- | --- | --- |
| 名义 | 57.144542/66.594016→51.039758/60.786096 | 75.80→76.62 | 36.968793→31.787454，同3264 | 127→83 /16.344→15.916 |
| 200/200反序 | 54.868112/64.620440→50.695892/60.672692 | 78.72→79.74 | 35.359965→31.077601，3366→3367 | 153→101 /16.221→16.163 |

第二站lower多1拍。候选多等待、原完整扫掠仍逐点认证，原始闭合仍244；全程native状态110382→66860、117510→70864。原运输worker wall2.088899→2.241538、2.486840→2.805327s，未提速；分离1.219243→1.196707、1.578827→1.624508s。最大51.163/134.155ms，完整50Hz未过。原件与独立库存output/loaded-jaw-formal-factory-20261024；私有round84保存正式入口、两路径与云版本，不与前轮不同负载秒数相加。

决定：正式两站wall/CPU与匹配阶段工作量支持采用。工厂DEFAULT_SOURCE选择loaded_jaw_preload.py，低层RoutePolicy()及显式父版不变，44切换相关测试通过。随后用不加私有观察器/不传candidate的原CLI验默认；尚未有此验收结果。余下极慢拍仍需进一步定位，不能用这次收益宣称完整50Hz。

原默认CLI验收source14d53ce6，3f16af29原pass：原参数直接evaluate_station.py --timing，不带candidate或私有观察器。实际默认加载loaded_jaw_preload.py，一次encoder latch记录；全部原物理/244/来源/完整周期/479视频和清理通过。76.60sim/47.539583process-wall/56.329792CPU；3830完整拍，P95 14.453ms/max42.783ms、62拍超20ms。单回合只验默认可用，不能把它与其他VM/观察范围的数值相减算新收益。原件output/loaded-jaw-stock-default-20261024，独立runtime及default-selection读回齐全。

下一条已定位证据：正式200/200回位切换cycle3734（t=74.68s）总134.155ms，controller127.240wall/127.232thread-CPU，前帧separate、当帧retreat。_return_path原直接路径验证.005rad，method=validated_direct；不能归因等待或OMPL重搜。ReleasedObjectQuery.distances对pad调用scalar SAT，现成box_separation_batched尚只用于可选冻结worker。F2k worker-only完整70.320→104.705s的负结果与220/170局部inconclusive保留；新假设仅是此同步return范围复用现成批量轴的CPU收益，先同值/同点/三对组件，不先发新物理或假定能过20ms。数学实现原作者CodeBuddy/DeepSeek Pro，当前薄接入由Root GPT，不冒称新CLI生成。

F2bs三对完整_return_path组件（source62af0840，实际挂载正式cross候选0c829902/source46031fff）：从原归档FK释放估计重建几何、初态及实际执行回位起点/目标，复算原完整函数。每例75次原native arm+释放距离查询；q6、全部距离、pad末状态和回位路径逐位相同，并与归档直接路径同值。scalar→batch wall138.169→98.729、126.985→95.962、148.977→99.955ms；CPU差−39.451/−30.990/−48.638ms。正常/异常实例方法恢复通过，原screen准入，独立读回protocol_valid=true。并非整程物理或20ms达标。

原件output/return-batch-axes-factory-20261024/component-v1；actual mounted-inputs、四个必要输入副本及每个binary64距离可复查。私有round86复用原CodeBuddy F2k数学函数，Root GPT只写_return_path作用域接入；新的原物理将以线程身份+stage约束仅控制线程separate→retreat启用，冻结worker不启用，避免复跑旧worker-only方案或混变量。默认保持已采用loaded_jaw_preload，下一步200/200父→子，净收益才220/170反序。


## F2bs 同步回位批量轴：局部收益与整程分开

source775302c，Kaggle私有so101-return-batch-axes-physical-ab-20261024 v1/v2。200/200 B→C feb87d4a（0af776bc/8a11ca2b）、220/170 C→B 115731af（76530350/2ccf1ea5）共4/4原pass。只在main/separate→retreat的_return_path复用既有CodeBuddy batch数学，route均为已采用loaded_jaw_preload；actual_policy_delta=[]，因此另核真实方法/线程/阶段与实际scalar/batch计数。冻结worker保持原scalar，全部原模型/评分/native flags/244/物理/自由物体与回退保持。

| 工位 | 原版→候选process wall/CPU(s) | 主return wall/CPU(ms) | 完整回位拍(ms) | 非hold/release CPU(s)/拍数 |
| --- | --- | --- | --- | --- |
| 200/200 | 50.183834/59.805410→49.636662/59.476717 | 145.006/144.941→103.350/103.342 | 166.345→123.033 | 30.867530→30.655970，同3367 |
| 220/170反序 | 51.464911/61.554807→54.096420/62.575940 | 62.031/62.017→50.641/50.637 | 79.000→72.602 | 31.762723→32.342046，同3285 |

第二站在尚未启用候选的3047拍前缀CPU已多.560170s，初始化wall多1.846296s；不把全程变慢归因11ms局部改动，也不据此宣称整体提速。主return两个站都少CPU，但慢拍70→74、121→125，候选最大123.033/72.602ms，完整50Hz未过；不晋级默认，不靠追加回合追绿。sim79.72→79.76、77.38→77.38s，等待采样不当加速。

v1恢复观察器误用实例属性不存在；原worker已在separation_worker.py安装requested_distances，故两侧原false并非回调丢失。原failed检查存independent-return-axes-readback-v1-absence-criterion.json，v1精确worker身份未观测的限制保留。v2仅观察字段改为原函数身份/slot，四项局部普通/worker回调与异常恢复回归过，两侧完整物理身份/slot均通过。不得把原v1观察错误改写成原物理失败或冒称当时身份全验。

原件output/return-batch-axes-factory-20261024/independent-physical-inventory.json分列初始化/shortcut/worker/main-return/完整周期/CPU/释放；原版及候选独立物理读回核对原阈值与全244、0碰撞、完整视频、owned/joined无abort。原件及run ID/复跑位于private round86、云端不可变v1/v2。Source/数学同源，v2只修观察器，未用不同负载绝对秒数串累计收益。

下一个F2bt只比较同原返回输入的SAT布尔阈值查询：原max(gaps)>=margin可以由任一原轴的同值gap证明。必须保留几何有限值/异常行为，不跳过其他robot几何；未能证明或不支持的数值域走完整scalar，原数值距离API不改。尚未有测试或收益，先局部准入，不能称新算法已通过。


## F2bt 原SAT布尔阈值的充分见证

原box_separation返回15个同序gap的max。只消费>=.001时，任一个原world轴同值gap>=.001即可证明原max比较为真。仅支持普通binary64有限有界数组与原underflow忽略环境；否则完整scalar回退。所有robot几何仍逐一检查，后续非有限几何仍报原错误，不向数值距离消费者返回近似值。8项回归及真实75点组件逐点判断/原arm调用/最终path/pad保持，原numeric API独立扫描确认，三对CPU/wall一致省约67ms。此候选不叠加F2bs批量轴。

sourceade153f；Kaggle私有component v1及physical v1/v2真实源码、scope和private均独立读回。200/200原B→C 3c1e480b、220/170 C→B d971930d，4/4原pass，实际只main/separate作用域激活，原worker scalar及身份/槽均恢复。全部原244/模型/native/裁判/阈值/自由物体/抓放释放脱离回位/完整视频/清理保持。

| 工位 | 原版→候选process wall/CPU(s) | main return wall/CPU(ms) | 完整回位拍(ms) | 非hold/release CPU(s)/拍数 |
| --- | --- | --- | --- | --- |
| 200/200 | 58.193510/69.066153→58.710048/69.785220 | 126.439/126.374→74.009/74.002 | 141.942→91.393 | 36.171169→36.277212，同3367 |
| 220/170反序 | 47.555413/56.758502→49.377854/58.377603 | 56.334/56.321→33.110/33.108 | 72.069→49.546 | 29.542729→30.018006，同3285 |

两个站都没有整程成本收益，因此不晋级默认；仅保存局部及尾延迟有效的证据。主线程真实分别查75/37点，robot几何1275/629，pad见证150/74，原native arm每点照常；不是删点/放宽阈值。sim79.68→79.78、77.44→77.50s，候选反多5/3拍，不用等待差算算法提速。慢拍186→152、68→92，P95 19.380→18.432、15.098→15.675ms，最大91.393/50.547ms，完整50Hz未过。

第二站前缀3047同拍CPU26.797225→27.228020s、初始化6.679→7.098s，说明总差已有作用域前变化；不作唯一原因判断，也不删除完整实测回退。原件output/return-clearance-witness-factory-20261024/independent-physical-inventory.json分列所有原指标和生命周期。private round87的首次SaveKernel400与后来缩短title/slug成功均保留，未改候选；组件/物理Kaggle确切slug及版本在progress中。下一项仅拆分剩余回位成本，避免继续只优化SAT后无依据外推总任务。


## F2bu 剩余回位成本的有界只读拆分

Kaggle so101-return-cost-attribution-20261024 v1/sourceec99737，独立检查有效。75点原arm/姿态/数值布尔/路径/pad保持，所有观察器恢复；主线程唯一、无负时间，75/1125/150实际调用量排除把后续离线75点复核计入的错误。使用inclusive timer而非跨线程cProfile，父子时长不可相加；raw与independent-return-cost-readback.json在output/return-cost-attribution-20261024/v1。

插桩原arm36.0ms、原release96.4ms（SAT71.3/forward4.6/nonpad6.5）；阈值候选arm34.0ms、release38.0ms（witness12.7/forward4.3/nonpad6.6）。这里支持剩余认证工作值得调查，不支持新提速或硬性50Hz下限。arm FK仅约.7ms，不据此重开旧pose-only方向；原F2as全局scalar hints未快的反证不变。

源码_poll_separation保留accepted_plan和planned_return_path；_transition在separate结束用实测q再走完整_return_path。worker与main回位输入只有终点相同不等于整条路径相同，不能用近似q命中缓存。下一F2bv只取证独立模型/浮点环境及真实原采样，暂不编写路线复用或放宽原阈值。private round89的观察器只读原默认任务并保留所有方法/槽及模型导出失败信息；必须先真实物理和独立读回，编译通过不算成果。
