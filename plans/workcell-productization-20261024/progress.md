# SO101 产品化进度

## 2026-10-24 — X向RGB拒绝17/17，原工作台Carry入口收口

Current：上一目标轮次=progress，X±11mm原物理2/2已完成并推送bf50087；本轮接原计划的目标缺失／遮挡／歧义拒绝，不重复抓放或扩大网页范围。

Done：原run_p0兼容{id,kind,initial_xy_m}负例声明；遮挡片／干扰物随目标平移，每例与异常恢复，原定位器／阈值不改。根58项相关检查通过。固定890616a，原Kaggle面板17/17通过：五正例最大误差.616511mm，12负例均拒绝且无xy/pixel/uncertainty。17原始PNG和overlay齐全，独立reader完整estimate重算17/17逐字段相同。原P0墙钟4.726051s，process wall/CPU=5.544141/7.334838s；详见[m1a-x-perception-results.md](m1a-x-perception-results.md)。

Preserved：原reset_scene实际8500步静置，不把本切片称零积分或抓放评测；不反馈物体真值给定位函数。云端原生COMPLETE，本机无拥有的抓放评测在跑，不与FishBot在途仿真争资源。qoder只读调用120s超时，仅一次，无有效结果，内置GPT接续，不修认证或新建调度器。高度／轴齐仍为先验，不声称异常姿态／高度已拒绝。

Done：5186原服务退出后沿原入口恢复，实际GET回读SO101 ready/resume_carry=true、Drone不支持Carry；两个历史终态resume分别409/405，无新任务或继续标记。13/25历史任务ID不变，首页与Carry产物实际被服务。工作台9个有效Carry文件已提交并推送5a30c26，远端SHA独立回读相同；Drone在途文件保持。详见[m2-carry-handoff-results.md](m2-carry-handoff-results.md)。本轮未做真实网页POST→等待→继续抓放。

Next：按用户指定继续X向逐请求IK／下降／全夹爪扫掠与盘壁证书准入，不将端点和内点插值为矩形可用域。原物理与定位面板分别保留；完整50Hz／20＋20仍未过。Knowledge=already_covered，沿用Wiki§20分开定位拒绝、物理动作与晋级；owner根Codex。Mint与Drone边界保持。

## 2026-10-24 — X向逐请求检查接续

Current：用户重新指定X向IK与盘壁净距。本轮=progress，[两项新请求已完成原物理](m1a-x-interior-results.md)：X=.229/.251、Y=−.13，原盘不动、原60mm高位及.5rad开度，均原pass。固定盘X±20mm既有结果未重跑，不把端点和新内点插值为连续安全域。

Done：原离线探针两点IK／下降／完整244点闭爪／抬升均通过，原285对无需补方向。全采样最小证书下界左1.012254mm、右1.026594mm，仅比1mm门槛多12–27µm；它不是精确欧氏净距或动态跟踪保证。两条直达接近诊断弦均在approach_obstacle/gripper拒绝，不能省原绕障。原件在output/x-request-probe-20261024。

Done：现有诊断CLI已补显式.35高位预收口和完整grasp扫掠选项，默认保持；每段覆盖数与失败pair独立报告，未认证值不叫minimum_certificate。根49项相关检查及内部GPT独立审核通过。固定66ee5d1，原Kaggle串行两例75.82／77.90sim、49.143／49.266episode-wall；planned/measured各244，抓放／释放／脱离／回位、自由物体和清理通过，录像474／487实帧。根与独立reader分别回读原件。

Preserved：前序Carry三例已回收原终态并更新其原报告，实际网页/API仍待根收口；工作台八个Carry文件及Drone在途改动保持。CodeBuddy本次只读返回空正文，未计有效审查。独立左释放重算仅2.71e−20m末位差，原exact-match=false保留；原裁决未改。

Remaining：完整周期左100／右63拍>20ms，50Hz未过；连续域／20＋20／网页新范围仍未验。静态本机MuJoCo3.3.7与云原物理3.15.0分列；本机两选定pair原生距离查询不等于整轨迹／云净距，不用于放行。

Next：复用原P0，对新X位置补目标缺失／遮挡／歧义拒绝；逐请求定位、规划和原物理仍分别验收，再决定网页范围。Carry新API仍由根接续，保留原在途工作。Knowledge=already_covered，沿用Wiki《ROS2 与 FishBot》§20的分层验收；owner根Codex。

## 2026-10-24 — Carry限时接续收口实施

Current：上一目标轮次=progress，固定盘左右两工位原物理已回读；本轮收口已在途Carry两仓12文件，不重启X项目或覆盖其他工作。见[m2-carry-handoff-results.md](m2-carry-handoff-results.md)。

Done：已复核当前009a79e、无本机在途物理，上一Kaggle终态。根审原hold/guard/时钟接点；修observer warning在warnings-as-errors下干扰控制的真实缺陷。根202相关Python通过，前端5runtime／56Jest／生产构建／13浏览器通过，均不是物理。CBC只读仍空正文，内部GPT完成独立审查，不作额度阻塞。

In progress：从真实网页导出的中心配方接原Kaggle，准备同源串行resume、waiting取消、原timeout三例。waiting仅姿态门，原Grasp证据单列，不引对象真值控制；原stage watchdog和90sim120wall不变。原API5186仍旧PID且暂无活动SO101／Drone任务，新字段未上线；根在整合后立即复核再受控重启。

Remaining：Carry原物理和真实新API未验，完整六技能BT／同世界恢复、连续卸货仍未交付。Drone四文件为其原owner在途离线M2，保留，不混合提交或停别人进程。

Next：固定SO101源码并沿原runner跑三例，独立回读后更新此计划与工作台原计划；再接实际用户入口。M1a独立核对建议按每个新请求原验证，不把左右点插值成连续安全域；真实RGB姿态／高度仍有不可辨识先验。Knowledge=already_covered，采用Wiki§20分列物理、交接与晋级，项目新数据仅留本计划。

## 2026-10-24 — 左固定盘两放置工位原物理通过

Current：本目标轮次=progress，固定46f5ba5已完成左侧主／第二工位及中心默认回归；[结果与复跑](m1a-x-fixed-certificates.md)。结合580ec56已核右侧结果，原红盘X±20mm固定取料点均能在两已有放置工位真实抓放；默认／网页±10mm不改，不宣称连续区域。

Done：v2左a3adbf9c…pass74.10sim/96.873wall，v3第二3c482379…pass76.84sim/99.990wall；planned/measured各244、原19轴先查与285对／1mm保持，真实抬升／持物／静稳／释放／脱离／回位、自由物体与worker清理通过，464／481实帧。两次实测补证384/384，382hint＋2full，error0；方向建议每帧重投影，不复用认证。原左fbb037d9…初始化拒绝和v1真实超时均保留；中心476fc756…原pass，479实帧。

Done：根241相关检查、同套不含Carry的索引源码241检查通过；1522真实姿态三对与最终定点复核全部返回逐字段相同。根及独立reader核原件、固定场景／初态／RGB／monitor／源码，原runner／probe未改；三批次在完整终态后才改源码／提交。

Remaining：左主／第二完整3705／3842拍，P95=36.279／35.724ms，701／722拍>20ms；完整50Hz未过。close／lift慢拍已有阶段定位，尚缺主控内部剩余成本切片，不凭组件收益宣称整程提速。连续有效区域、20＋20、六技能halt／同世界恢复及FishBot连续卸货均未完成。

Next：根按M1a继续核连续包络与定位拒绝，按M1b只读拆close／lift保留全扫下的剩余成本；不改默认、不先跑新20＋20。Carry在途SO101四文件及工作台八文件保留，owner根，最短入口carry_gate.py／station_executor.py与原runtime测试，尚缺构建／浏览器／物理，不混入X结果。Knowledge=already_covered，沿用Wiki《ROS2 与 FishBot》§20；本轮新实测仅留原计划，不改记忆。

## 2026-10-24 — 左固定盘补证首轮真实超时，接方向建议复用

Current：上一轮为progress，首批已全部终态；[原件与结果](m1a-x-fixed-certificates.md)。26a0a1d原左93d949ce…grasp_leg_collision；显式候选2c6637a9…wall_time_limit停close22.56sim/120.757wall；原中心30819b8a…pass76.72sim。没有以COMPLETE或补证通过冒称抓放成功。

Done：候选planned/measured244全过、实测补证162/162 error0，但未持物／释放／回位；初始化41.025s、首close14.207s controller有实测计算成本。141捕获帧编码0，无有效录像。根235项包括不含Carry的索引源码同套235通过；根与独立reader核原物理及失败。中心480/480录像／释放／脱离／回位保持，52慢拍，完整50Hz未过。

In progress：根只读切分发现46,869方向构造／去重warm28ms、native4.5ms，实际270方向即有证。内部GPT做同checker/pair局部方向提示，每帧仍原完整投影；普通miss全回退、算术／ABI错误仍拒绝，所有pairs需通过。仅缓存方向，不缓存gap／valid／stage认证，不跨worker/model。原1mm、244、90sim120wall及默认保持。

Done：根原checker＋helper26a0a1d与方向提示1522姿态三对逐字段相同，14.398／14.819／14.523s→.868／.857／.873s，408次整帧重证，406hint＋2full，无跳点。早期只载旧helper的无效适配结果独立保留，不计收益。

Next：新候选普通miss／错误与精确计数负例，固定源码后沿原Kaggle重跑原左拒绝／候选／中心，可靠通过才第二放置工位。Carry两仓在途继续保留，owner根。Knowledge=already_covered，沿用Wiki§20，不写新记忆。

## 2026-10-24 — 固定左X−20mm补证执行候选实施中

Current：上一目标轮次=progress，右固定盘两放置工位原物理已通过且580ec56远端核实。本轮接左侧完整静态补证到显式执行候选，默认仍关闭；无在途本地或Kaggle物理评测，不重复上一轮。

In progress：现有immutable RoutePolicy传mesh_box_axis_refinement=False默认；原19轴先查询，只对no_separation_certificate的原失败mesh-box用完整顶点区间门补证，所有pairs都需认证，全局最小下界保留。root贯通主控、实测检查及transport/separation/return原worker，内部GPT实现refiner和batch逐点回退；不改payload/released守卫、原1mm、244点、限位／评分／90sim120wall。

Constraint：refiner/local hull和NativeSupport属于同一编译model owner；每个当前关节／geom姿态重算世界方向与投影。尺寸、mesh顶点／索引／类型、pair集合或model更换时须重建整个checker，不能只清轴缓存；不跨worker共享可变helper，不新增hash锁。显式False应覆盖已加载的True策略，状态记录实际开关。

Done：独立架构核对确认批量原生桥会绕开Python补证，候选开启时回原逐点检查，点数不减；诊断inspect递归与算术错误翻valid风险按原失败原因隔离。CodeBuddy本次两次空结果不计有效分析，回退GPT；不修认证或扩展平台。

Done：根235项相关测试通过；原固定左侧2／74／244／74点全查通过，246次整帧补证，无错误。原拒绝保留；闭爪全扫本机8.682s成本偏高，物理时限仍待验。真实右负例／FENV／ABI／全部pair／显式False与batch回退已覆盖。

Next：固定源码后用原Kaggle跑原左侧拒绝、显式补证、中心默认回归；仅可靠通过再第二放置工位复验。Carry四文件及工作台8文件继续保留在途，由root接续；Knowledge=already_covered，采用Wiki§20的固定原场景、独立评分和候选晋级分别验证。

## 2026-10-24 — 固定右X＋20mm两放置工位完成原物理

Current：右侧IK／盘壁切片已形成可复跑开发能力：[结果与入口](m1a-x-fixed-certificates.md)。原盘不动，54mm接近高位加0.35rad高位预收爪；默认.5及网页±10mm保持。非连续区域／非20＋20／非50Hz通过。

Done：v1原大开度1d8288ea…保持grasp_leg_collision原fail；候选be15f72b…pass79.26sim；原中心62a5a8c7…pass76.62sim。v2固定46ab29同执行代码，已有第二放置目标(.20,.20)的5e8a109c…pass82.34sim。两次右侧任务均真实抓放／释放／脱离／回位，原红盘／robot／初态不变；候选关键全扫各246、实测jaw到位后下降、双worker原确认清理。录像496／479／515实帧与报告一致。

Done：根及独立reader逐项回读，原monitor重放与skill_evidence完全一致，3个真实success不包含保留的原失败；UUID pointer不多算回合。原规划/进程wall/CPU／完整周期均已记录，不将跨VM／目标时长差当提速。代码与输入相关91检查、无Carry索引源码83检查、后续case8检查通过。

Remaining：右主／中心／右第二工位分别72／68／82拍>20ms，完整50Hz仍未过；左X−20mm虽静态整链补证，未接生产或物理；连续包络／扰动验收未过。

Next：根将左侧已验证分离方向作为显式候选接入原完整规划与实测检查，再跑原物理；原1mm、全点扫掠、限位／评分／90sim120wall保持。Carry两仓12文件保留在途、未混合提交，owner根Codex。Knowledge=already_covered，沿用Wiki§20；本轮只更新原计划。

## 2026-10-24 — 右X＋20mm固定盘首轮原物理通过

Current：固定82918d7的Kaggle v1三例全部终态，原开度1d8288ea…仍grasp_leg_collision/0sim/原fail；高位收口be15f72b…pass79.26sim，原中心62a5a8c7…pass76.62sim。结果与复跑见m1a-x-fixed-certificates.md，默认／网页边界不变。

Done：右真实抬升40.989mm、持物35.02s、释放／脱离／回位通过，原盘未动、全部状态有效、碰撞与安全停机0；三个关键jaw全扫各246点，实测jaw到位停止才下降，录像496/496。中心原244点、479/479视频与完整抓放通过。根已逐项回读；独立reader核终态中。

Remaining：右3963完整周期仍72拍>20ms、max50.616ms；非性能A/B、非连续包络、非20＋20，左补证未接物理。Carry在途保持未提交，不以静态诊断冒充任务成功。

Next：同右pickup与已有第二放置工位(.20,.20)做一次跨工位原物理。只加显式开发case，原评分／几何／阈值／90sim120wall保持；新批次仍固定源码，整组终态再写回。Knowledge=already_covered；owner根Codex。

## 2026-10-24 — 右固定盘高位收口候选实施中

Current：同原右X+20mm／54mm IK姿态，高位0.5→0.35、下降、低位闭爪及上升632点已全部通过原19轴，不依赖新增补证API。原场景和阈值保持。

Done：双pad容量38.890855mm>斜向20mm方块＋4mm=31.679576mm；固定指侧0.160212mm为原开度同样存在的薄侧，不据容量保证居中／抓取，不新增双侧2mm执行门槛。原件见m1a-x-fixed-certificates.md。

Done：内部GPT已加显式pickup_open_jaw_rad=.35及高位preclose段，默认.5不变；根91项相关检查通过，另对不含Carry的索引源码独立83项控制器／扫掠检查通过。开发profile/CLI透传8项已通过。高位和低位各保留至少244点、实测夹爪到位后才下降。另准备原Kaggle三例：原大开度拒绝、收口候选、原中心回归，待源码固定后启动。

Next：根独立审查候选及原守卫／计时，选择性提交，不混入Carry未验改动；云批次在整组终态前不改源码。Knowledge=already_covered；原物理未测，不记成功或晋级默认。

## 2026-10-24 — 固定盘 X 向数值补证已完成，右侧整链仍拒绝

Current：[本轮结果](m1a-x-fixed-certificates.md)。用户最新X方向，未移动红盘、未改原19轴／默认、1mm、限位、244点或评分。原生可选方向API和可复跑诊断已实现，不接生产准入。

Done：固定左X−20mm参考2／下降74／闭爪244／抬升74实际全查并数值认证；246条新增几何对完整支持／平方门成立，最小见证下界12.083509mm，原offline_screen_pass=false保持。固定右54mm路线原64拒绝点逐点回读，原生18认证／46拒绝（下降0/14、闭爪18/50）；不将不认证写成物理碰撞。

Done：相关原native、保守检查和探针46项测试通过；内部GPT独立回读无缺失／换对。修复诊断覆盖表述（失败前缀complete=false）和原NaN输出（null且certified=false），真实右侧负例仍拒绝。无新物理／无性能或50Hz声明。

Next：根核高位0.35rad开口的下降／244点闭爪及双pad宽度几何，再决定候选。左侧数值补证也不能代替原物理验收。Carry接续两仓12文件保留在途，owner根；本轮只显式提交X诊断与结果。Knowledge=already_covered，沿用Wiki《ROS2 与 FishBot》§20；不写记忆或并行新知识页。

## 2026-10-24 — 接续固定红盘 X 向 IK／净距

Current：用户最新指定 X 方向。原盘 X+20mm／60mm 仍是腕限位；54mm 已有 IK，但下降与闭爪拒绝待查。X−20mm 原19轴证书不足，单姿态已有更强分离轴。先对原拒绝的 mesh-box 几何对补候选方向，用原完整顶点区间投影与1mm认证；不移动红盘，不改原裁判、几何或默认准入。

In progress：根负责轴候选／可复跑诊断；内部GPT补可选原生方向认证及独立右侧几何核验。agent-link/CodeBuddy本次返回空结果，回退内部GPT。完整物理候选须先过原下降／244点闭爪离线检查；未测不记成功。

Preserved：CarryGate 等待接续为在途工作，本轮未启动云批次；SO101四文件及工作台八文件保留，owner根Codex。其接口／前端局部检查已过，仍缺生产构建／浏览器／原物理，不作为已部署功能。最短入口为carry_gate.py、station_executor.py和工作台原runtime测试；本轮不混合提交。

Next：核左侧已知分离轴与右侧全部原拒绝点，区分漏方向、间隙不足与实际相交；Knowledge=already_covered，采用Wiki《ROS2 与 FishBot》§20中“固定场景、独立评分和候选晋级分别验证”，不以新布局替代固定盘位结果。

## 2026-10-24 — M2原物理Grasp证据到网页已实测

Current：本轮=progress；[完整结果](m2-grasp-evidence-results.md)。固定b21b1d9在Kaggle同VM串行新原完整抓放＋运输worker取消，整组终态后才回写源码仓。没有重训、改控制／评分／碰撞或放宽90sim120wall。

Done：3d3cefa8…原pass，77.90sim/57.770episode-wall、59.011process-wall/69.557CPU；真实抓放／释放／脱离／回位、planned/measured244、自由物体和双worker清理保持，碰撞／安全0，487/487实数录像。49f2d252…原fail/exit1、taskcancelled，30.22s原worker ack+alive触发、30.24s终止，abort/join/closed及无活线程确认，189/189录像。

Done：两例仅1个Grasp事件，index1383、27.68s；原双指接触／抬升／无支撑持续持物证据成立。根及独立reader逐行重放原monitor与helper，和原report.skill_evidence完全相同；顶层attempt UUID正确。取消只记录1511/1512行，未补算未处理末行，attempt仍false/Cancelled。历史未抓住／失物反例及后续失败保留通过。

Done：43相关Python、12网页执行数据测试与生产构建通过；10项桌面／390px浏览器通过，写请求／页面异常0。网页用真实回放HTTP fixture验证“曾抓住≠整任务完成”，不是新网页物理回合。显示callback深拷贝隔离缺口已独立复验修正。

Remaining：完整3895拍，P95=17.945ms、P99=31.779ms、max=51.915ms，159拍>20ms，完整50Hz仍未过；本轮非性能A/B。六技能可halt生命周期／同世界安全重抓、20+20、连续卸货仍未完成。

Next：根接满足前后置条件的技能生命周期；复用已核成熟BT能力，先证RUNNING／halt／清理，不以重启Station新世界冒充恢复。Knowledge=already_covered，沿用Wiki《ROS2 与FishBot》§20；来源与新时序只留本计划。根独立提交推送两仓成果，保留其他在途工作与Mint边界。

## 2026-10-24 — M2原物理Grasp证据接入中

Current：上一目标轮次=progress（配方原物理及实际取消交付）。本轮将原monitor首次grasp_success接为只观察证据，传到原status与网页；没有用stage替代成功，也未改变控制器／裁判／碰撞／90sim120wall。

Done：helper与接点已实现，事件仅在monitor.update后产生，记录观察拍数、首事件索引、时间和原接触／抬升事实；finalize在清理及最终deadline后复制原attempt结果。Station下一次原发布携带快照，不新增控制循环文件写入。根43项相关Python、12项网页执行数据检查和最终构建通过。独立审查发现callback嵌套引用会污染证据，已深拷贝隔离并加修改＋抛错回归，原顶层裁判始终未改。

Done：四份真实记录回放：成功与取消首抓取均27.68s；未抓住无事件；失物曾28.80s确认、终局仍payload_lost。旧schema与baseline来源明确；取消末拍未被原monitor处理，只回放1511/1512行，保留原Cancelled结果。输出在忽略目录output/m2-grasp-evidence-20261024；不是四次新物理。

Remaining：固定源码后用原Kaggle入口跑完整回合＋运输worker取消；网页证据展示的无运动QA待终结。六技能生命周期、行为树与同世界安全恢复尚未实现，Grasp证据不冒称完整M2。

Issues：已安装BT.CPP4.10.0/MIT与Nav2 BT1.3.13/Apache2.0，仅核本机包及头文件；SO101未适配，Python当前环境未见py_trees。Nav2 halt可等待取消future，不能放进50Hz循环；重新run Station会reset，不算同世界恢复。复用原资源和任务，不新造树引擎。

Next：根固定源码后接原物理并独立核证据时序／结果保真，再接真正的可halt技能与恢复。Knowledge=already_covered，沿用Wiki《ROS2 与FishBot》§20，项目新时序与数值留本计划。

## 2026-10-24 — M4配方交换原物理1/1，M2运行中取消清理通过

Current：本轮=progress，详见[m4-recipe-results.md](m4-recipe-results.md)。可编辑配方已接原网页／Station／CLI；浏览器导出原文交固定fd20512源码，在Kaggle串行完成完整任务及真实worker取消，原生COMPLETE后独立回读。两项不是性能A/B或两次抓放成功。

Done：完整任务10f9c86e…原pass，77.960sim/55.544episode-wall、56.735process-wall/67.325CPU；真实抓放、释放、脱离、回位、planned/measured244、自由物体与双worker清理保持，无碰撞／安全停机，488/488实数录像。取消0181e8f1…在30.220s原worker ack+alive后触发，30.240s原Cancelled、task cancelled，abort/join/closed确认，无活线程／清理错误；原物理fail/exit1保留，未执行放置与回位。

Done：64项相关Python、74项前端检查及最终构建通过；18项无运动浏览器通过，真实任务写请求0／页面异常0。文件读取期间任务变化时保住新ID／取消入口。独立审查复现并修正负时长静默改写，原普通草稿容错未变；未知可选元数据／历史引用可往返。实际云输入与浏览器原件逐字节相同。

Remaining：完整周期3898拍，P95=17.118ms、P99=33.579ms、max=60.075ms，134拍>20ms，完整50Hz仍未过。M2六技能生命周期、可认证撤退／重新定位重抓未实现；M3 20+20、M4同世界两件卸货仍未验，不用独立episode交换替代连续世界。

Issues：工作台此前Drone在途成果已由原owner提交至7fc5695，未覆盖或混入本轮改动；后续按实时树核对。CodeBuddy空正文保留，内置GPT独立审查与原件读回；未动Mint或实体机械臂。本机另有Blender渲染，未与其抢物理资源。

Next：M2由根将原monitor后置物理证据接到技能生命周期，取消与失败保留原因果，再实施安全恢复。Knowledge=already_covered，沿用Wiki《ROS2 与 FishBot》§20；项目新事实只留本计划。

## 2026-10-24 — M1b准入取证完成，M2取消与M4配方实施

Current：上一目标轮次=progress。新准入观察c0045f5f…原pass；14次poll（13未ready、1准入），最终14.613ms／完整拍33.843ms。job调用约.067ms，不是主要成本。最大116ms是callbacks105.803wall/3.227CPU，I/O与宿主等待尚待区分，不无据新增底层优化。

Done：M2六技能真实证据接点已审，不能把旧stage直接标技能成功。取消终态已修：请求和实际取消分列，晚到请求不遮原pass/fail，安全／清理原失败保留。M4新增可编辑station-recipe v1、两个X配方样例和前后端薄校验；原Station、任务与评分复用。未知可选元数据保留，历史验收不作为新任务通过；拒绝未支持单位／旋转／动态尺寸语义。根64项相关Python及68项前端数据检查已通过，均非物理验收。

Remaining：工作台首轮17项实际配方往返、旧任务不继承、文件读取竞态和390px检查通过，真实任务写请求0、页面异常0；独立审查另复现负时长被旧导入器改成1，已在配方路径明确拒绝，前端最终构建／该反例复验待做。新配方原完整物理与worker运行中取消待验。M2六技能生命周期／恢复、M3 20+20、M4同世界卸货未实现，不因静态交换降格验收。

Issues：工作台仓另有Drone记录器、测试、说明及其原计划在途修改，保留原owner，不混入SO101提交。首轮构建读取编辑中的导出返回类型失败，修正后webpack构建成功（2项原包体警告）；新时长反例修复后另做最终构建。AGY／Qoder此前不可用，CodeBuddy本轮再次空正文，内置GPT完成独立审查并复现上述缺陷。旧准入观察Kernel已确认COMPLETE，本机无原物理在跑；云验证沿用Kaggle。

Next：根固定SO101源码；将浏览器实际导出的new-recipe.json（station逐字段等于原X+20）送原物理及真实取消。前端并行补时长反例与最终构建，不修改在途物理源码。Knowledge=already_covered，沿用第20节分层验收；项目新事实只写本计划。

## 2026-10-24 — M1b 实测q异步回位4/4，保持显式候选

Current：本轮原物理与证据闭环结束，详见[m1b-return-results.md](m1b-return-results.md)。固定b317d4f在Kaggle同VM右B→C／左C→B四次原pass，源码运行期间未改。X开发布局保持，未改IK或盘壁阈值。

Done：根101相关CPU检查通过；同模型三对path/method/report和75state/arm/distance覆盖逐位等价。根与独立reader回读原4/4、244+244、全部15635轨迹、释放脱离回位、自由物体、视频和worker回执，warnings=0。候选return job均consumed/joined/owned_ack，首指令accepted+issued且保持连续。

Remaining：左首retreat完整拍143.018→33.347ms，右36.634→30.314ms；候选仍超20ms。process wall右50.884→49.745s，左50.878→51.119s；整程收益不一致，不切默认、不宣称提速或50Hz。原默认loaded_jaw_preload保留，候选显式可复跑。M2恢复、20+20、配方卸货仍未完成。

Issues：新等待右6拍／左13拍，原hold/release另有调度差；不把等待或其他VM秒数计入算法收益。原轨迹未存逐拍全部sweep点，只核已记录guard与原裁决。Qoder审查超时、CBC空正文未计有效复审。

Next：根Codex只针对候选接纳的controller 22.779/25.369ms做实际分段测量，区分绑定、桥接和首指令；先证因果再改动。Knowledge=already_covered，沿用Wiki《ROS2 与 FishBot》第20节，不把候选保留写成默认晋级。

## 2026-10-24 — M1b 实测回位候选，默认关闭

Current：X两侧已验开发布局沿用，不重写IK或放松盘壁阈值。接续旧周期最大140.476ms的separate→retreat入口。新Kaggle原观察ca00cc74…原物理pass，78.34sim/48.142episode-wall、49.470process-wall/59.080process-CPU；244+244、自由物体、释放脱离回位和490帧均独立回读。插桩复制快照额外120ms，cProfile树父帧不完整，不能把341ms最大拍写成原固有成本。

Done：同MuJoCo3.15、同MJB、无mj_step独立复算5次，原返回路径逐位相同；单次128.07–136.87ms，中位131.131ms。每次1条直接路径、75状态、75原arm检查及75释放物距离查询，未走OMPL。候选由根GPT实现，Qoder超时后内置GPT独立审查；新增async_measured_return.py显式开关，默认仍loaded_jaw_preload。复用原异步job、SeparationSnapshot和独占模型，从实际q快照计算原_return_path，现场再验桥接、首命令和90s预算；在线保护、244、评分、取消清理不变。审查发现issued回执缺口，已补到原data.ctrl写入后。

Remaining：根相关CPU回归与新交接反例核验后固定源码；先同输入三对无物理等价，再在Kaggle同VM运行X+的B→C及X−的C→B原evaluate_station --timing。未测候选不记成功，不由等待拍数变化记提速。整组终态前不改在途源码或提交。

Issues：本机Blender两段后台动画仍运行，未抢本地物理资源。原观察与复算原件在忽略目录output/m1b-return-profile-20261024；私有wrapper沿用round100/round103，候选物理沿用round104，不新建调度。当前候选原物理not_run、完整50Hz未通过。

Next：Owner=根Codex，固定通过局部核验的候选源码并推送，完成三对等价与原两工位反序物理。Knowledge=already_covered，沿用Wiki《ROS2 与 FishBot》第20节分层验收，新时序事实留本计划。

## 2026-10-24 — M1a Station／网页入口2/2原物理通过

详见[m1a-station-entry.md](m1a-station-entry.md)。两开发布局已接原5186网页选择、保存/刷新、复制/JSON与任务入口；新任务6e86ec73…、f7c265d5…分别78.02/78.08sim、59.131/58.445episode-wall，原真实抓放、释放、脱离、回位全部通过。planned/measured244、双worker、自由物体与488帧视频均独立核实，warnings=0，无障碍接触或安全停机。项目浏览器刷新同ID、一次POST和视频读取断言通过；独立离线读回不扩大为完整网络时序重演。新入口未采完整周期或精确process CPU，不补历史值。

根50项Python、33项网页数据、3项服务及生产构建通过；桌面/390px九项无运动浏览器通过，根查看截图。SO101运行引用084cc7f；工作台本轮abc0ac7/2b9fd90，另在途Drone改动已由原owner提交de94a6d，本轮保留其独立责任，不声称共享仓库全冻结。主FishBot与Mint未触碰，5187他人服务未停；本轮5186保持可用。

M1a总体仍in_progress，默认±10mm不变；新域仅开发先验。恢复/M2、20+20/M3、配方卸货/M4均未完成。M1b开始只读周期归因：旧X面板15641拍/281慢拍，最大140.476ms集中同步回位入口，下一步先细分_return_path，再论已有worker迁移，不做无依据SAT微调。该旧数据不是新网页计时。Knowledge=already_covered，第20节分层验收；新事实留本计划。

## 2026-10-24 — 接续 M1a：Station／网页入口实施中

上一目标轮次分类=progress：X两新布局及两中心原物理4/4，源码与证据已交付。当前沿M1a把已验参数接入原Station与既有网页，仍不宣称连续区域或M1a整体完成。

新增可编辑execution开发声明，缺省保留原±10mm；盘位／高位／静态视觉先验显式保存，节点与声明不一致则具体拒绝。未知可选元信息警告保留，不参与物理参数。原判据、244、90sim/120wall与原reset/RGB数据边界保留。网页添加两样例按钮，载入仅新建草稿并清除当前结果关联，原任务记录保留；导入、保存与复制保留execution。

实际工作台位于FishBot独立工作树 `/home/muqiao/worktrees/fishbot-workbench-code-rebuild-20261018`，既有codex分支，非dirty main。agent-link已发现可用：AGY实调参数不兼容失败，CodeBuddy实调返回空正文，未冒称有效产出；当前GPT与两个内置工作者完成薄实现。网页工作树另有DroneDiagnostics/drone-diagnostics在途修改，保留不纳入本轮提交；主FishBot的mecanum/delivery-timing也未触碰。

当前局部Python／数据层检查已做，根复验与生产构建进行中。浏览器与新Station原物理待验，不能由先前run_workspace_case成绩代替。Owner=根Codex；构建结束后先无运动浏览器往返，再资源允许时单次网页真实抓放。Knowledge=already_covered，第20节分层验收；输入合同与新结果留原计划。

## 2026-10-24 — X 新布局原物理4/4通过，保持开发能力

源码e7f921c在Kaggle v1单VM串行结束；两个X新布局与两个原中心全部原pass。右侧X+20mm用红盘+20mm／高位54mm，左侧X−20mm用红盘−5mm／原60mm；不是原固定盘包络扩展。原真实夹持、搬运、落盘、释放、脱离、回位、planned/measured244、双worker清理与自由物体均核实，无障碍接触或安全停机。详细原成绩、UUID、规划/进程wall/CPU见[m1a-x-results.md](m1a-x-results.md)。

根读回原件、RGB估计、计划路径末端FK、全回合关节余量并看右侧终态图；独立reader6项失败/缺证反例通过，真实warnings=0。四视频480/488/489/500帧与原记录一致，相机前置7/7、最大.616511mm。完整周期仍58/70/81/72拍>20ms，完整50Hz未过；20+20/恢复/配方/卸货未新增验收。原任务90sim/120wall、1mm与所有安全条件保留。

源码执行期间无改动/提交，组终态后才回写本记录。云原生COMPLETE，无拥有的本地评测在运行。下一步：将已验开发布局与原固定盘边界清楚交给用户；不直接开放连续工作区或再次做无依据底层优化。Knowledge=already_covered，沿用第20节分层验收；本轮新事实留在项目。

## 2026-10-24 — X 方向薄适配，原物理待验

已区分 X+20mm 高位腕限位与 X−20mm 盘壁证书不足；根独立复算全网格投影。详见 [m1a-x-results.md](m1a-x-results.md)。没有将保守下界当真实最短距离，也未用 libccd 负值作裁判。

新增显式红盘平移与 .054–.06m 取料高位参数，默认保持原值。选定右 +20mm 红盘／54mm高位与左 −5mm 红盘／60mm高位；候选原参考起姿、下降、244闭爪和提升证书全过。84 项相关检查通过，不计物理成功。将用 Kaggle 单 VM 串行运行两个新布局与两个原中心，仍为 90sim/120wall；新布局不是原固定盘位包络或算法提速。

当前整组原物理 not_run。源码固定推送后再发起，整组终态前不改在途源码。Owner=根 Codex。Knowledge=already_covered：原第20节分层验收原则；本次几何事实与布局成绩只写项目，不增加共享知识页。

## 2026-10-24 — M1a 首切片完成：范围外原物理 4/4

实际结果见 [m1a-results.md](m1a-results.md)。固定源码 `0ef4068` 在 Kaggle v1 串行运行四例：主工位中心／Y+20mm、第二工位 Y−20mm／中心，原物理 4/4 pass。原释放、脱离、回位、planned/measured 244、双 worker 清理、自由物体及四份视频均独立核实；无碰撞、安全停机 0。相机前置 3 正＋4 负全过，最大误差 0.616511mm。云离线 11 点同样 9 点通过。

仅新增两个固定范围外点的可复跑开发能力，不宣称整个 ±20mm 区域或 ±150mm。没有改 IK 目标、模型权重或安全判据；网页与默认仍为原 ±10mm。M1a 整体 in_progress，连续包络与产品准入仍待做；M1b、恢复、20+20、配方、卸货均未新增验收。完整周期仍分别有 68/52/65/79 拍 >20ms，50Hz 未通过。

根回读原始 JSON、完整周期、规划／进程 wall/CPU、碰撞、释放、回位与 ffprobe 实际帧数；内部 GPT reader 的 4 个缺证／失败反例通过，真实原件读回 warnings=0。运行源与原评分来源均为上述固定提交；整组终态前未改源码或提交。云原生 COMPLETE；无其他拥有的评测仍在运行。原 TGZ 是完整原件，重复 loose-file 下载客户端已停止，不使用其不完整副本。

Next：核 X−20mm 下探盘壁证书与 X＋20mm IK 残差的不同成因，再决定姿态／初值或布局适配；不直接全放开，也不转回 SAT 微调。Knowledge=already_covered，沿用原第20节分层验收原则；新项目实测留在本计划，不改在途 Wiki 或旧 pending。

## 2026-10-24 — M1a 实施中：原物理待验

- 完成可复跑 FK/IK/保守碰撞离线探针及编译 frame 核对。11 个区内／边界／区外点，9 个通过；X±20mm 的不同拒绝原样保留，Y±20mm 进入下一轮原物理候选。产物 `experiments/colab-twin/output/workspace-m1a-20261024/report.json` 被 Git 忽略。
- 控制器新增可选静态目标区域，原默认、网页 ±10mm、碰撞／244／TTL／预算不变。开发 profile 复用原执行、原评分和 StationVideo，每例独立 UUID，保留原失败。
- 根独立实跑：7 项空间探针检查、69 项控制器／原 Station／原汇总检查、4 项开发入口检查通过；其中开发入口 mock 物理，不计抓放成功。原控制器检查一度因实验 venv 缺 cv2 导入失败，系统 cv2 也有 NumPy ABI 冲突；停止该分支，仅补隔离 venv 的匹配包后原检查通过，未降级已有依赖。
- 下一运行：Kaggle 单 VM 串行四例，主工位 center→Y+20mm，第二已有工位 Y−20mm→center。复用原 bootstrap 与串行进程 wall/CPU 记录，原每回合 90sim/120wall；不是性能 A/B，不切默认，不开放网页新区。原云 leaf 任务已确认 COMPLETE，无重复启动。
- 当前新四例原物理状态 `not_run`，50Hz、20+20、行为树、配方与同世界卸货均未新增验收。源码固定推送后才发起，整组终态前不再修改或提交运行源码。

## 2026-10-24 — D0 计划完成，实施未开始

用户请求：将工作区扩展、恢复技能、快慢环、工艺寻优、车臂配方协作写为 SpecMesh。根 Codex 与三个内部 GPT 工作者分别核运动学、周期／seed、配方／FishBot 所有权，根串行整合。

### 已完成

- 建立 [task_plan.md](task_plan.md) 和 [findings.md](findings.md)，列明阶段、原入口、验收、回退与缺证项。
- 修正前提：±10mm 是输入边界；IK 已松弛完整姿态；进程首次 seed、transport/separation worker 已存在。
- 保留现状：F2ce 两工位 4/4 原物理通过、性能不一致未采用；F2cf 148 拍 >20ms，完整 50Hz 未过。未改历史判定。
- 明确六技能复用原执行器、配方复用 Physics/bridge；5186 已由 FishBot runtime 提供。Mint 不改，任意编排／配方交换／连续卸货未实现。
- 算法工厂转为有证据的性能支线，无新瓶颈证据时不追加低层试验。默认保持 `loaded_jaw_preload.py`。

### 阶段状态

| 阶段 | 状态 | 尚缺证据 |
| --- | --- | --- |
| D0 前提／计划 | complete | 只完成文档，不代表功能通过。 |
| M1a 工作区 | planned | 坐标/FK、IK 区内外、定位遮挡、完整抓放。 |
| M1b 快慢交接 | planned | 全认证保留的交接及完整周期实测。 |
| M2 技能／恢复 | planned | 取消、失败保留、可认证撤退、物理恢复。 |
| M3 冻结面板 | not_run | 独立 20 正常＋20 扰动及完整回读。 |
| M4 配方／卸货 | planned | 往返、同世界两货物、取消／库存交接。 |
| M5 寻优面板 | planned | 稳定基线、可重复改善、采用／撤销。 |

### 下一实施入口

Owner：根 Codex。先读 `station_executor.py:170`、`grasp_episode.py:114`、`visual_grasp_controller.py:334` 和模型工具轴，形成 **M1a 坐标合同与只读工作区筛选**。先比原 IK，不直接删除 ±10mm 校验，不继续 SAT 微优化。局部通过后选区内外点，经原 `evaluate_station.py`／`run_physical_episode` 做原物理。

M1b 复用 F2cf 叶段报告定位剩余同步责任。M4 配方草案可独立进行；同世界实施回源 FishBot 连续计划，不修改其在途任务。共享仿真先核进程；如接 Kaggle，单列机器与负载。

### 文档验收与知识收尾

本轮仅做定向核查和文档；未启动仿真、训练、云任务、服务或实体动作。提交前只验变更范围、链接、状态一致性和 diff。原成绩均来自 F2 记录，无新增物理通过宣称。

文档检查：新三文件与研究索引共 27 个本地链接目标存在，`git diff --check` 通过；独立只读审查未发现技能／旧裁判、同世界／取消或阶段状态的实质阻塞。源码与评测产物未变。

跨仓索引已写入研究根 `PROJECT.md`。初查时该文件混有空地臂／无人机在途计划，未将其他 owner 的改动并入 SO101 提交。随后独立读回：研究根 `9cae17a` 已整合该索引，工作树干净；本仓计划 `6de1206` 已推送，GitHub API 与 `ls-remote` 均回读相同提交。跨仓索引 pending 已解除，研究根无远端，本地提交不冒充云端发布。

Knowledge=already_covered：采用 Wiki《ROS2 与 FishBot》第 20 节“动作成功、交接成立和候选晋级分别验证”。没有新运行结论，不改在途知识页。旧 F2cf 插桩经验回写的 pending 保持原 owner，本次状态不冒充其已完成。
