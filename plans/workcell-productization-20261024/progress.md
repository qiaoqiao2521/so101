# SO101 产品化进度

## 2026-10-28 — R136实际RGB输入18点原几何全通过

Current：固定6cf337b，Kaggle x-input-sensitivity v1终态；左右RGB中心各9点，18/18原IK／抓取腿／完整扫掠通过。共9240全扫采样，全285对；左244／右246闭爪保持。独立审计无unknown，原q6含jaw／XML／输入逐值回读；不是原物理、OMPL、连续域或50Hz成绩。[原结果](m1a-x-input-sensitivity-results.md)。

Next：按最小非reference原证书规则选左135°／右+X方向，准备固定RGB输入偏差原物理2例＋左零偏差回归；不是移动物体、概率覆盖或性能A/B。盘壁下界约1.000137／1.000354mm不当实际欧氏最近间隙，原1mm不改。新三例尚not_run。Owner=根Codex。Knowledge=already_covered；原计划边界继续。

## 2026-10-28 — R136 实际视觉输入离散敏感性实施中

Current：上一轮R135已终态并交付。本轮继续X方向IK／盘壁净距，使用R134左右真实首个有效RGB中心、各自原工程容差半径和原initial_qpos[:6]。预声明每侧中心＋四轴向＋四45°方向共18点；左60mm/.5，右54mm/.35。该半径不是统计置信界，18点不证明连续圆域。

Implementation：只给原离线probe补可选initial_q6；默认None保留原reference IK及后续诊断行为。显式初态原六值用于reference／frame／扫掠，五轴用于原IK seed链；首IK失败后不再尝试同点后续IK，下一点独立开始。原求解器、285对、1mm、244分辨率与controller／评分器不改。

Checks：根使用既有planning-venv完成原模块25项检查（含新增7项），全部通过；git diff检查通过。旧graspgenx venv已不存在、系统python无mujoco，首两次导入／入口失败保留，不安装新环境或误记为测试成功。

Pending：固定本轮薄适配源码到Kaggle串行原全抓取几何面板。新组件结果、整程物理及连续域均未验；不得以准备文件或静态通过代替成绩。Owner=根Codex；内置GPT分工薄实现、独立输入来源核验，外部callback不可用不阻塞。Knowledge=already_covered，Wiki《ROS2 与 FishBot》§20；新输入与失败留本计划。

## 2026-10-28 — X中点第二放置工位原物理3/3通过

Current：承接原网页中点2/2，两个新文档只把蓝盘移至(.20,.20)m。固定bef4ba4、Kaggle so101-x-second-place-20261028 v1三例原物理均pass：左右中点b76fe921／3412c142，加既有中心回归8c5ad216。原取料盘、程序、右54mm/.35工艺及1mm／全部对／完整244或246／90sim120wall保持。[结果与复跑](m1a-x-second-place-results.md)。

Done：原输入准入／仅place变更核实；独立126项无失败，六份XML确认蓝盘全几何平移、红盘／robot／option／actuator不变。原monitor／skill一致，原抓放／释放／脱离／回位、自由物体、零安全停机／障碍接触及worker清理通过，实视频491／511／499帧；根已看左右final图。左78.44sim／60.853process-wall／71.938CPU，右81.62／61.425／73.027，中心79.74／59.587／70.730；非性能A/B。

Remaining／Issues：11990完整拍、0中断，慢拍210／193／184，P95 20.388／19.687／19.175ms、最大172.635／160.545／159.744ms，完整50Hz仍false。中心释放漂移重放有2.71e-20m末位差，原值／unknown保留，判定与逐2ms旗标一致；左右精确。原非致命wrapt警告保留。新第二工位网页／连续域／20＋20未验。

Read-only：R134初始真值误差左.631417483／右.524660981mm，与名义误差近似。首次漏读trajectory造成“没有同步物体序列”的诊断已撤回；原20ms物体记录与非零视觉时间／两handover精确匹配，名义冻结到接触前采样近乎静止，不推广运动目标或拍间证明。像素／高度工程容差不当统计界，也不与1mm证书直接相减。

Resource／cleanup：本机Blender活动时未启本地仿真，沿原Kaggle CLI／串行runner，上传源码回读一致。三个原进程均wait回收，已启动worker joined／owned_ack。TGZ直接读、无临时帧；reader gzip核回读后释放49,152分配字节，原件／当前视频／两final图／配置和诊断保留。工作台Drone在途不动。Knowledge=already_covered，Wiki《ROS2 与 FishBot》§20。

Next：根先以两实际RGB中心、原初态q6和预声明工程扰动集做原IK／285对／全扫离散敏感性检查，按原种子保留拒绝，之后再选原物理临界输入。不插值开放普通±10mm或启动20＋20；M1b grid／FK／pending-hold与M2 Carry网页接续独立待办。

## 2026-10-28 — X中点原网页与物理2/2通过

Current：两个新中点已从原网页导入、HTTP创建任务、刷新原ID不重发并完成原抓放／释放／脱离／回位2/2。左9e4059a7原60mm/.5，右d2e1ca4e显式54mm/.35，红盘不动。Kaggle原v3终态；原执行器261e3e6、1mm／全部对／完整扫掠／90sim120wall及默认保持。[详情与复跑](m1a-x-web-midpoint-results.md)。

Done：原35项Station／评分／recipe检查及两文档准入通过；独立91项无失败，原monitor／skill／2ms释放精确重放，左244／右三项246、自由物体、回位与470／490实帧核实。根已看实际网页截图。左75.16sim／92.82process-wall／94.48CPU，右78.32／92.91／94.94；非性能A/B，网页命令wall另列。无原EpisodeTiming，本轮完整50Hz unknown，历史未过保持。

Issues：v1仅步骤UI ID重建引起测试拒绝，无POST；v2私有observer缺/usr/bin/time导致两worker exit127，物理未启动，原失败保留。v3补可选依赖／警告降级后真实通过。sitecustomize缺wrapt启动警告原文保留。普通帮助±10mm未改，显式开发文档不等于连续域放行。

Resource／cleanup：本机FishBot／渲染占用时未启动本地物理，复用私有Kaggle输入与既有CLI；未复制凭据、会话或node_modules。原任务终态及worker退出后才TERM/wait自有preview，无物理worker被杀。TGZ直接读、无临时帧；reader gzip逐字节回读后释放30,601,216已分配字节，上传硬链接已删但不虚报空间收益。失败、配置、当前视频和两截图保留。

Next：原网页样例已可导入；根继续同请求在已有(.20,.20)m放置工位复验，再核定位误差覆盖，不直接扩大普通±10mm／连续域或启动20＋20。M1b grid／FK／pending-hold与M2 Carry网页接续独立待办。工作台Drone在途变动由其原owner接续，本切片不混提交。Knowledge=already_covered，Wiki《ROS2 与 FishBot》§20。

## 2026-10-28 — X中点两层问题已分开，两个新请求原物理通过

Current：按用户要求接续X方向IK与盘壁净距。新增左X=.2245m原60mm／.5配置抓放通过，右X=.2555m显式54mm／.35预收爪通过；固定盘不动。原中心两次通过；三次右60mm失败原样保留。只有离散新请求，默认／网页±10mm、连续域、20＋20与完整50Hz未改。

Done：Kaggle原静态screen核1861实际采样。名义右60mm可解但下降缺证，预收口同解通过；进入真实RGB后，两开度都在原IK残差.0007626829034486256处零步拒绝。用归档RGB与原静态reference复现同拒绝；改54mm可解，仍须.35避免原盘壁／活动夹指缺证。V2同初态／RGB只改高位后完成真实抓放、释放、脱离与回位，不改IK残差／95°限位／1mm／285对／244分辨率／原90sim120wall。缺证不当实际接触或欧氏净距。

Evidence：原物理source=3602f5b；Kaggle so101-x-gap-physical-20261028 v1为2pass／2fail，v2为2pass／1fail。左75.36sim／52.074process-wall，右54mm78.54／51.966；真实抬升40.968／41.024mm、脱离漂移.187192／.185207mm，脱离后力0。独立114／160项读回无失败；原monitor／skill／释放重放、自由物体、回位、worker清理和真实视频核实。新右仍77拍>20ms，完整50Hz未通过，不能把本轮当提速A/B。

Delivery：新增可编辑workspace-x-gap-midpoints-m1a.json，保留成功与失败case，沿原CLI复跑；原执行器／默认无代码改动。原件、root与独立readback在output/x-gap-midpoint-20261028；静态旧scope过时字段／reader首次错误保留，未改成绩。25个重复展开逐字节核后清理，释放176,128分配字节；物理TGZ直接读取，保留491帧当前回放，没有临时帧。当前拥有的云任务均终态，不碰Mint或其他机器人。

Next：先将两个已验新请求接原Station网页并单独验收；第二放置工位新中点、定位不确定性与连续域仍须独立证据。M1b/R132的FK数值界／实际grid／pending-hold覆盖证明保留待续，不冒称后台准入完成。Knowledge=already_covered，Wiki《ROS2 与 FishBot》§20；本轮局部事实留原计划。详细结果与复跑见[m1a-x-gap-results.md](m1a-x-gap-results.md)。

## 2026-10-28 — 闭爪增强净距筛查通过，后台覆盖证明继续

Current：上一目标轮=progress（round131原物理及交付）；本轮R132也是progress，新增原244点增强门槛的实际云端证据与覆盖边界。Kaggle `muqiaoqiao/so101-closure-envelope-screen-20261028/1`在75663a6终态，三组均244/244、全285对有效，121项独立检查通过。仅原几何组件，无新抓放／异步接纳／默认切换／50Hz成绩。

Done：原1mm、额外1µm即1.001mm、保存原close开始后.1s的小偏移起点三个完整网格通过；baseline原报告exact、增强组网格逐位同值。分离下界最小分别1.375845688／1.375845688／1.375846257mm；对应原障碍—前臂对，不叫最短欧氏盘壁净距。冷启动／后续耗时.758／.496／.497s不是性能A/B，不当提速。strict SweepBinding仍保持，旧姿态结果不可直接消费。

Done：真实compiled模型为8body单链／6单hinge、joint anchor全0、29组mesh/box、285原对。私有理想刚体预算覆盖body／geom偏置、双侧运动及原binary64插值的向外区间；拟议每轴1e−7rad箱在同244网格条件下位移界最大.677006µm，小于增强门槛的额外约1µm，原限位箱内。四项纯Python测试通过。该数字不是MuJoCo FK浮点误差证明；网格数／spacing须实际重新核验、FK误差和真实pending-hold漂移仍未覆盖，production_admission_allowed=false。

Channel：外部callback URL/socket当前均未配置，按新版派发规则直接内置/root/closure_envelope_review独立审查／回读，无外部额度请求或queue修复。私有task/dispatch/handoff保留，原生结果返回；未发送其它对话。首reader把XML default geom计入，已按worldbody实际geom枚举修正，原失败日志保留，无云端重跑。

Cleanup：25原件归档与展开逐字节一致，无缺／额外，删除重复展开、压缩独立及预算报告并解压回读，实际释放24,182,784已分配字节。原TGZ／log／gzip读回／恢复命令及私有源码保留；没有拥有的在途云任务，不碰Mint／其它机器人。

Next：R133限定此六hinge链，先补实际采样网格／间距接纳条件、MuJoCo 3.15 FK数值误差界，再验证保持开爪等后台期间的真实偏移。全部成立才做默认关闭的worker薄适配及原物理对照；不放松binding、不删除244点、不将本组件叫异步安全通过。Knowledge=already_covered：采用Wiki《ROS2 与 FishBot》§20“组件与完整任务分别验收”；未证实的包络推导只留项目。此前NULL getter专项回写pending不冒称已完成，owner仍根Codex。详见[m1b R132](m1b-refinement-details-results.md#2026-10-28r132闭爪增强净距与覆盖预算)。

## 2026-10-25 — 抬升预载原物理5/5，两工位有实测收益

Current：round131固定`2eea9bb40caac88c3ca24cfec5b6a30223d77afe`，Kaggle `muqiaoqiao/so101-lift-preload-physical-20261025/1`整批终态。正式143弦三对准入后，两个放置工位反序与中心原物理5/5pass；独立1200项通过，Monitor／SkillEvidence／ReleaseAudit逐样本exact、unknown为空。保留显式loaded_jaw_lift_preload候选，全局默认loaded_jaw_preload不变。

Done：两个工位实际process wall77.847164→76.528623、79.345562→78.353571s；CPU87.243938→85.823958、89.443861→88.398259s。lift各143拍，controller5.055299→3.980717、4.934555→3.992697s；剔除全部hold仍少.880057／.689949s。候选hold反多1／2拍，第二仿真反多.08s，不把等待变化当提速、不与旧批相加。

Done：原完整几何组件8008→5664点，每点原.005arm／.002jaw、285对与1mm；三对wall省1.067722／.896867／1.060837s、CPU均降。实际轨迹首lift／hold／release连续，一次锁存及每拍jaw与各自原motion_duration／minimum-jerk精确相同。原planned／measured各244，抓放、释放脱离回位、自由物体weld0/mocap0、无障碍接触／安全停机、双worker consumed／joined／owned_ack全部核实。五视频464／464／481／480／484实帧对应原记录。

Remaining：完整50Hz未过，主候选492慢拍／P95 38.304ms／max428.373ms，第二458／37.562／419.930ms；中心119慢拍。物理未保存每2ms actuator_force，静态力相同不扩写成动态力逐拍相同。原wrapper physical_status遗留pending文本，以terminal与五原裁决确认终态，原元数据不重写。连续X域、20＋20和工作台整链不从本轮推定。

Delivery／cleanup：源2eea9bb已推且REST／ls-remote一致；本结果仅整批终态后回写。166归档原件逐字节验证无差／缺／额外，保留一份当前候选视频，移除重复展开并压缩独立JSON，实际释放95,911,936已分配字节；TGZ、root摘要、视频、gzip读回与恢复入口保留。无拥有的云评测仍运行，未碰Mint／其它机器人／他人渲染。

Next：原244点measured闭爪同步尖峰和普通close持续认证仍未解决；先按已保存真实时序明确现场状态绑定／覆盖包络，再决定交接方案，不继续单行hint微优化或删点。下一批未启动，不重复本轮或运行20＋20。Knowledge=pending，根保留原共享Wiki在途diff，项目结果已在本计划落盘。详见[m1b本轮结果](m1b-refinement-details-results.md#2026-10-25提前抬升预载的正式组件与原物理)。

## 2026-10-25 — 抬升预载静态筛查通过，默认关闭实现待原物理

Current：round130 Kaggle `muqiaoqiao/so101-early-lift-static-force-20261025/1`终态。143个周期初冻结状态的6维驱动力／广义驱动力均与原指令同值；独立1738项通过。它是规划模型mj_forward，不是动态接触／任务／提速证据。新显式`loaded_jaw_lift_preload.py`已实现，默认关闭，尚未跑候选完整物理。

Done：原trajectory在周期末保存command和状态，已与前一raw状态及observer起止逐条exact对齐。云端阶段跨度2.86s诊断ramp理论8008→6065点；独立按原motion_duration=2.257558s复算5664点，静态jaw均−.15。后者仅离线算术，不冒充新云mj_forward。单帧饱和不证明2ms积分中始终等效。

Done：生产选项复用一次encoder／previouscommand锁存，原close6s与planned／measured244不改，仅从lift开始按原运动duration连续ramp；hold1.5s及后续守卫保持。147项相关mock／协议测试通过，覆盖默认、连续首拍、只锁一次、释放与弦内部碰撞；不计真实FK或物理。初次私有helper缩进在写前compile拒绝、首次测试的报告stage字段假设错误均已修，不改原日志。

Next：固定源后复用原Kaggle组件与Station入口，完整143条原／新弦及静态force、三对wall／CPU通过才接两工位反序＋中心五例；保存原失败、不切默认。原1mm／285对／244、90sim120wall、评分器与全部回退保持。

Cleanup：round130的25个原件逐字节核对无差／缺／额外，删除展开；独立JSON压缩回读一致，实际释放2,162,688已分配字节。TGZ／日志／gzip报告／恢复命令保留。首准备的周期错位与首reader混同数据／代码revision错误保留，Kaggle按title归一slug后的错误status查询未触发重投。Knowledge=pending，原共享Wiki在途diff仍由根串行处理。

## 2026-10-25 — 左侧闭爪真实归因完成，单行提示优化淘汰

Current：round127／128／129全部云任务终态；生产源码仍为9cca89a，无默认切换。原左X−20mm插桩物理1/1通过，定位到244点实测闭爪认证与持续在线弦成本。单行hint校验候选状态等值，但三对收益不一致，淘汰；不再重复跑同候选追绿。详见[m1b结果](m1b-refinement-details-results.md#2026-10-25实测闭爪归因与单行提示反证)。

Done：round127原run63bbbf0e-abab-4078-bce9-c4bb9d764e94通过，74.04sim／86.564906process-wall／96.658863CPU，原1mm／285对／planned244／measured244、抓放释放脱离回位和自由物体保持。update1008从descend进入close：451.885ms，其中measured_closure244点441.843ms，随后online_chord仅2点3.975ms；不是两次完整244点叠加。普通close330拍的在线6362点耗时12.096504s，lift143拍8008点耗时5.228489s。插桩成本单列，不能与未插桩批次算提速；完整50Hz仍未过。

Done：round128用原保存244／48点弦及XML，fresh query MjData/hint进行原cProfile，两报告与原件exact。hint校验244次累计77.932ms，但488次_detail_arrays是244个全285对＋244个单行hint，不是重复两次全285对。round129私有单行校验实际876请求无回退，12份真实NPZ共7,931,340数组字节相同；独立117项通过。三对合并wall节省55.644／−2.764／70.606ms，CPU第二对也更慢，原门槛不通过；未接生产，未启动候选原物理。

Failures：round129 v1漏arena_observation.prepare，baseline首次快照报错，零完整配对；v2仅补setup初始化，候选不变。独立reader的旧路径／字段错误已按原schema改正，原失败日志保留。外部Codex CLI首次只读无文件交付、后续120s审查超时，均不计有效实现／审查成功；根与内部GPT完成实际私有文件和独立回读。

Cleanup：round127／128／129的53／27／31＋46个归档原件逐字节核对且无额外／缺失，删除重复unpacked；独立JSON压缩后解压回读一致。合计实际释放34,209,792已分配字节，不重计先前清理。TGZ、日志、gzip独立报告和各cleanup-readback.json保留；恢复入口见结果文档。未停止他人渲染／Colab或触碰Mint。

Next：根Codex先核现有loaded_jaw_preload能否提前至lift，读取原执行器系数并在原保存q6／qvel下对比反事实力矩与原采样成本。只做只读组件，不改6s闭爪、244点、1mm、285对或原裁判。单帧饱和不证明20ms动态等效，后续仍须新源码原物理；当前没有新可交付算法、连续域、20＋20或完整50Hz成绩。

Knowledge=pending：沿用Wiki《ROS2 与 FishBot》§20对组件／交接／完整任务的分层；原共享知识页已有在途修改，根串行核diff后再回写，不冒称已更新。

## 2026-10-25 — 正式运输前缀两工位受益，原物理5/5通过

Current：round126完整源58da5048275cff2669e84f89ada0df5d92cd207a，Kaggle `muqiaoqiao/so101-transport-prefix-physical-20261025/2`终态。正式组件等值且两运输组三对wall／CPU均快，接原Station串行5例全部原pass。独立715项通过、unknown为空；根另重读实际数组和原裁决。保留显式 `loaded_jaw_transport_prefix.py` 为X左侧已验候选，全局默认仍loaded_jaw_preload，不将固定点推成连续域。

Done：两工位进程wall74.963946→73.590872、78.357657→75.982074s，CPU83.864978→82.564069、88.159918→85.634905s。非hold controller46.612581→44.652556、48.742175→45.800050s；hold162→162、183→182，第二组少1拍不当算法收益。原初态、场景、OMPL及实际接近路径一致。主候选1195批／34655原状态，次候选1298批／37642原状态，fallback0；不是改等待或路径获得的局部胜利。

Done：5功能、7组报告／hint／q6及86份原NPZ独立字节重建一致；102有效数组＋77NULL标记，原始有效数组字节共56,841,270B。运输两组wall中位比.842309／.823997；close中位1.006343且三对两慢一快，继续禁用其前缀。原1mm／285对／244闭爪、无障碍碰撞／无安全停机、自由物体weld0/mocap0、释放脱离回位全保留。中心回归亦原pass，但不是中心前缀收益对照。

Remaining：完整50Hz未过，左候选477慢拍／max404.727ms、第二489／405.447ms，P95为36.469／34.112ms。现有完整分段记录最大close拍controller397.814／398.626ms；尚未细分该拍内planned与measured认证，不将其猜成OMPL或相机。下一步沿原244闭爪调用与现有worker合同核清同步责任，再决定能否预计算或安全交接；不全阶段开启本前缀，也不重复无假设物理。

Failure retained：v1用短ref58da504，GitHub fetch128，组件／物理均未启动。改传相同完整提交后v2运行，不改bootstrap、算法或裁判。v2原cloud physical_status遗留pending文本，但终态stage及5份原verdict独立已验；不修改原件掩盖元数据缺口。

Delivery／cleanup：源已推送58da504，账户／REST／ls-remote一致。本批所有评测终态才写本节。v1的5原件和v2的266原件逐字节核对后移除重复展开，3份派生JSON压缩并解压回读一致，本轮释放104,292,352已分配字节；TGZ、root摘要、gzip独立报告与恢复命令保留在output/transport-prefix-physical-20261025。详见[m1b结果](m1b-refinement-details-results.md)。无本地物理、Mint或其它机器人资源操作，无恢复定时器。

Knowledge=pending：采用原Wiki§20“组件、交接和完整任务分别验证”。NULL getter及首次失败经验待根Codex核原两页在途diff后合入；本轮只写项目实测，不冒称知识已更新。

## 2026-10-25 — 运输专用批量前缀接入，原物理待验

Current：round126接入正式 `transport_refinement_prefix`，默认false。显式候选仅继承 `loaded_jaw_midpoint_details.py` 并开此选项；控制器仅在transport阶段的online_chord选择新validator。其它阶段、planned／measured闭爪244点、1mm和全部285对保持原链。无默认晋级、连续域、20＋20或完整50Hz通过宣称。

Done：同owner原C循环复用；完整MjData快照、回滚和hint成本计入调用。无法给出保守证书时恢复原状态并完整scalar/refiner回退；binding／generation变化不覆盖新状态。独立审查发现“一次性FK异常同时改变绑定被回退抹去”，已修复为保留首次RuntimeError／ValueError失败，其他BaseException原样传播。83项本地mock／协议回归通过；不是实模FK或物理结果。AGY同步审核90s超时，不计成功；内部GPT独立复现修复反例通过。

Next：固化源后在Kaggle复用原bootstrap／component slot／evaluate_station，先正式组件7组与5功能、完整状态原bytes和三对wall／CPU；两运输组均可靠受益才串行原Station左工位B→C、第二放置工位C→B及中心回归。失败保留并停止该批物理；不将私有round125收益当正式实现收益。当前云任务尚未提交，完整批次在途期间不改源码或提交。

Knowledge=pending：原Wiki§20和入口已有在途修改，根Codex继续串行处理；本轮采用该节“组件、交接和完整任务分别验收”，新NULL getter经验仍未回写。清理：本轮仅新增小源码／探针，没有删除旧原件或重复计算既有132,513,792B清理量。无本地模型或实体动作，Mint不动。

## 2026-10-25 — 同owner组件通过，运输受益／闭爪全慢

Current：round125固定f922da9，原Kaggle v1终态。5功能检查通过，7组原完整报告／hint／q6同值，云内有效数组比较回执相同。根179项／独立414项读回0失败；不是Station物理或生产资格。详见[m1b结果](m1b-refinement-details-results.md)。

Done：原生78字段实测77为NULL，102个有效NumPy数组＋77个NULL标记组成179条目；11争议getter确为独立临时数组。未删除有效字段，原round123失败保留。私有候选逐字不变，更正观察方法后同owner普通及一次性异常状态／首次失败语义成立。原始数组bytes未归档，独立核代码和回执不冒充离线字节复算。

Done：完整snapshot成本计入三对，运输wall中位比主.734709／次.720192，CPU同向，六组lift／hold／transport均三对快；close三对wall／CPU全部慢、中位1.005947／1.005963，571scalar与完整244保持。因此只保留transport-only接入候选，不全阶段开启，不切默认。

Done：round123／124重复展开实际释放983,040B；round125完成42原件核对和独立报告压缩后释放9,834,496B。原TGZ／root／gzip reader／小输入保留，恢复命令见结果文档。累计已记录清理132,513,792B；无拥有的评测仍运行，不动Mint及他人资源。

Next：根Codex做默认关闭的薄transport-only生产选项，补native错误／invalid-q／observer／binding／close／reentry与generation边界，后续保存压缩原数组；通过组件后再原Station两工位反序物理。私有动态源码派生和诊断观察器不进入控制热路径。完整50Hz、连续域、20＋20未过。Knowledge=pending：Wiki§20及入口已有在途修改，根下一接续先核diff，再写NULL getter经验并读回；本轮未宣称已写。

## 2026-10-25 — 11个arena字段差异已定位，先核原生NULL

Current：round124字段诊断终态，5项原比较仍false；具体差异仅efm／island映射11字段，四个异常case仅7个efm浮点字段。其它179字段中的观测、错误和历史事实见[m1b结果](m1b-refinement-details-results.md)。无计时或新物理。

Done：根与GPT独立核同版官方Python getter、InitPyArray、resetData和arena宏，识别“native NULL但Python固定shape”假设；未按字段名删比较，也未把源码解释当现场证明。原失败保留。

Next：根集成GPT的只读native pointer观察器，在云端核每字段是否NULL、相关计数及setup前后；有原生数据字段仍字节相等，NULL明确记录。功能全过才做同7组计时，仍不生产qualify／不改默认。Knowledge=no_reusable_delta，未确认的假设只留项目。

## 2026-10-25 — 同owner功能未过，暂停计时而非洗掉失败

Current：round123源2a167c0，云v1终态。原生COMPLETE但组件exit1／complete=false，5项functional的全部数组字节比较均false，性能pairs未运行，原物理未启动。report／error／hint／followup均相同，但不能据此晋级。原失败与遗漏字段证据保留，详见[m1b记录](m1b-refinement-details-results.md)。

Done：仅私有同owner适配完整mj_copyData／witness回退，原查询generation失效和严重异常传播保持；GPT只读审查两轮纠正瞬态错误被重试风险。未改生产或默认。round122独立161项回读0失败，完成archive验证后清重复展开，另释放5,648,384B，原TGZ／压缩reader／root报告保留。

Next：根Codex用逐字不变的私有候选做云端字段诊断，仅补dtype／shape／数值差异，不跑性能。原数组差异原因未明，不先排除字段；close／reentry等生产边界仍待验。无新IK／物理／50Hz／连续域／20＋20通过。Knowledge=already_covered，Wiki§20。

## 2026-10-25 — X侧完整弦组件终态，shadow不晋级

Current：round122源42f5a55，原Kaggle v1已COMPLETE。根122项读回通过；7组完整原报告exact，全部285对／1mm／原244和完整scalar回退保持。无新物理、无IK改动，默认不变。详见[m1b结果](m1b-refinement-details-results.md#2026-10-25完整派生弦的批量前缀组件)。

Done：两个工位54派生弦全量筛选，lift各504点中448原轴clear，hold325／318及transport各261点全clear。六组三对wall／CPU均更快，transport中位wall比.709250／.708594。close571点全部回退且原244exact。组件不是controller或抓放，不能算整程提速。

Rejected：shadow原型六组主data与witness历史均不同，production_eligible=false；不接执行器、不因报告相同跳过交接验收。Zcode只读90s超时，内部GPT接审，不改认证配置。

Done：已验证归档后删除round120／121重复unpacked，压缩独立reader，保留TGZ和关键读回；实际释放116,047,872已分配字节。恢复命令和逐项证据见上文m1b结果。当前fixture与他人在途工作不动。

Next：根Codex仅做同owner私有前缀，先解决原生查询世代、MjData／hint恢复及异常回退，再同7组／244等价；组件成立后才考虑生产选项与原Station反序物理。X±20mm仍是两个已验固定点，完整50Hz／连续域／20＋20未过。Knowledge=already_covered，Wiki§20已读回，无跨项目新结论。

## 2026-10-25 — 运输段同输入诊断完成，未改生产

Current：上一轮=progress，原物理5/5与结果b236ff4已推。接续原运输反增问题，固定b236ff4在Kaggle so101-transport-detail-20261025 v1完成18组同输入组件；[完整诊断](m1b-refinement-details-results.md)。本轮不是新抓放或50Hz验收。

Done：两原baseline各自模型、3阶段×3jaw变体，162声明查询；每组90返回，预热和AB/BA/AB无hook计时，另计数。全部返回／hint/stat exact，实际285对与配置不变。lift各组原80 clear／10需补证，候选省10 detail、补方向10保持；hold／transport全部90 clear、两边native90，没有native工作减少，但候选仍进明细入口90次。根78项及独立原件读回通过，6输入逐字一致、actual library flags齐、unknown=[]。

Remaining：transport配对CPU差中位每query增加3.2–24.4μs，仅第二工位固定jaw组三对wall／CPU均慢，其余有反向对。hold某组零工作节省却三对更快，噪声反证保留。不能归因原整段新增.922／1.684s，不据此加采样／调参／改默认。原5/5和4.924／5.002s整程收益仍有效，完整50Hz仍未过。

Next：根先完整检查保存q6→reference弦的所有原采样点，再决定既有raw batch认证前缀是否值得组件对照；未获证／None／错误回原scalar refiner，不减少285对或244。旧round116 close全需补证且更慢的失败保持，不原样重跑。当前只准备私有新探针，无生产改动／新物理。组件process wall29.515s／CPU30.674s单列。zcode实调90s超时，根／内部GPT完成独立核验。Knowledge=already_covered，owner根Codex。

## 2026-10-25 — 生产明细组件与原物理五例完成

Current：固定5badfff，Kaggle so101-refinement-details-physical-20261025 v1已COMPLETE，五原进程均终态pass；[生产结果](m1b-refinement-details-results.md)。新收益来自实际评测，没有重跑上一批。

Done：生产组件三对完整返回exact，wall／CPU中位比.720152／.720157；571态／285对／原244保持，固定轴ABI1142→571、补方向571不减。原左主B→C／左第二点C→B／无execution中心回归5/5。两工位process wall少4.924007／5.002280s，CPU少4.764859／4.616346s；hold同拍163／182，nonhold controller少4.665780／4.949293s。close 18.033→12.710／19.330→12.943s，不是等待帧收益。

Done：同侧原OMPL／接近路径／最终认证exact，1.002711796mm分离证书下界保持；原1mm／244／裁判／90sim120wall未改。五例抓放／释放／脱离／回位、free／weld0／mocap0及双worker清理核实，无安全停机／障碍接触。根61项通过，独立Monitor／ReleaseAudit五例exact、unknown=[]，实视频464／464／480／480／485帧。主trajectory exact，第二释放差一拍，不外推整链。原件Git忽略。

Remaining：保留显式候选、不切默认。主P95 35.381→36.463ms、慢拍627→663；第二36.119→38.338ms、770→1026，完整50Hz没有改善。transport controller反增.922／1.684s；先核真实谓词与同输入调用量，不猜GC／负载或盲调参数。

Issues：wrapper残留pending字符串，以五原裁判终态为准；组件缺独立loaded-library flags收据保留未知。dsh实调120s超时，内部GPT只读未发现本轮回归；既有直接bound特殊margin转换关闭handle边界另留最小修复，正常checker预转float不触发。

Next：整组终态后才回写／提交本轮。根接原组件检查transport/lift/hold输出及成本。完整50Hz、连续X域、20＋20、真实Carry HTTP整链仍未过，既有失败保留。Knowledge=already_covered，沿用Wiki§20；owner根Codex。

## 2026-10-25 — 同次明细生产候选完成接线，待固定源码原评测

Current：承接24日原物理搜索收益与组件三对，不重启项目。[本轮代码与组件](m1b-refinement-details-results.md)。原4/4抓放仍是最近物理成绩，新明细候选还不是物理通过。

Done：薄summary_with_details在原owner锁内返回拥有明细，checker局部单次消费；query与checker调用世代及q/p/R/pairs/margin/owner/handle不符则回原detail。原输入转换真实重入、复制重入与关闭native均退回；原方法、返回、1mm／全点／评分／超时保持。四处checker构造已透传，RoutePolicy默认false，loaded_jaw_midpoint_details仅继承父版加一个bool，不偷开补证、不改默认。

Done：owner核心133、集成73通过；恢复原direction_hints is True语义后专项11通过。根另独立47项通过，含真实bar-box端点clear／中间接触拒绝、原完整244扫掠要求、真实busy重入与owned数组。diff检查通过。初次RIGHT测试误判detail回退的期望已纠正，原未获证和错误拒绝不改。

Next：固定源码后沿原Kaggle先重测生产组件三对，等价且wall／CPU均降才接原五例：左主B→C／左第二点C→B／原中心候选。私有round120已备原runner与输入，拟slug so101-refinement-details-physical-20261025；尚未运行，不记成功。整组终态前冻结源码；根独立回读并沿原计划接续。Knowledge=already_covered，沿用Wiki§20；owner根Codex。

## 2026-10-24 — 左补证重复查询已云计时，默认关闭适配实施中

Current：四物理搜索对照已独立回读并推500dc47；本轮直接接左close/lift的实际瓶颈，无新本地仿真。详见[m1b-refinement-details-results.md](m1b-refinement-details-results.md)。

Done：同姿态summary已计算完整285对，refine再次native.evaluate重算。私有同次拥有明细原型571态／9弦保留全部返回、报告、hint与原244闭爪exact；固定轴ABI1142→571，补方向仍571，不称全部native减半。十故障首query回原detail，pairs反转／关闭native原拒绝保持；旧汇总错误和未配置父策略版本独立保留。独立GPT只读审查通过，真实碰撞和实际并发覆盖仍待生产阶段。

Done：原Kaggle so101-refinement-detail-20261024 v1已COMPLETE；固定500dc47，三对1.550167→1.148111、1.601443→1.146758、1.622729→1.154425s，wall/threadCPU中位比.716078/.715990，完整输出exact。原组件process16.678wall/17.861CPU，仅组件无Station verdict／无抓放积分，原preflight渲染单列。根及独立reader已分别核原件、完整状态、计数、五文件及故障；运行后Git状态没有单独收据，保留unknown。

In progress：实施薄的同次summary拥有明细接口和默认关闭RoutePolicy候选，继承loaded-jaw midpoint，不改原默认、Station合同、碰撞阈值、全扫或评分。源变动由代码owner串行完成，根负责独立审查／原物理；不能把私有monkeypatch或组件收益当生产完成。

Next：补真实拒绝／所有权／回退和透传检查，固定新源码后沿原Station做两工位反序物理。原完整50Hz仍未过，原搜索候选4/4证据和所有失败保持。Knowledge=already_covered，沿用Wiki§20；owner根Codex。

## 2026-10-24 — X两工位搜索候选完成原物理，实际整程成本下降

Current：承接05cc17c固定源码，Kaggle so101-x-midpoint-20261024 v1已COMPLETE，原四进程全部终态。详见[m1a-x-midpoint-results.md](m1a-x-midpoint-results.md)。本轮=progress，未重复上一批、未操作实机或Mint。

Done：左B→C、右已有第二放置工位C→B，4/4原pass。左process wall/CPU107.803/118.025→93.181/103.274s；右59.962/71.430→57.415/68.771s。左shortcut79→10候选弦、8110→2157状态、16.261→3.027s；右74→11、7145→2366、4.111→1.448s。省的是shorten_path直连弦认证，不是IK求解；原云provenance的不准确IK措辞在结果文档纠正、原件不改。

Done：同侧原始OMPL／最终接近路径与最终认证exact相同，最终535／490状态保持；loaded-jaw preload保留，唯一偏好差异为midpoint。左hold均162拍，右候选反多5拍／.16sim秒，不把等待差当收益。后续异步／释放／实测回位轨迹不是整链exact相同，不作此声明。

Done：原抓取／放置／静稳／释放／脱离／回位、全部碰撞／1mm／90sim120wall保持，左244/244、右246/246/246，安全停机／障碍接触0，free/weld0/mocap0，双worker确认清理。根直接原件72项通过，独立Monitor及ReleaseAudit四例exact重放，实视频463/463/515/514帧。全部运行产物保持Git忽略。

Remaining：完整50Hz仍未过；左候选3703拍P95 40.835/max673.253ms、1512慢拍；右4115拍P95 18.557/max164.089ms、170慢拍。初始化收益不能算作快环改进，左close/lift controller仍20.172/5.862s。每工位只有一对，不推全场景收益或连续工作区，不切默认。

Next：保留显式loaded_jaw_midpoint入口；按原实测继续拆左close/lift内部认证，不再复试已全慢的批量前缀。网页普通导入解绑旧任务修复3bce2c7已推并独立核远端；真实Carry HTTP链仍单列未验。Knowledge=already_covered，沿用Wiki§20；owner根Codex。

## 2026-10-24 — 左侧成本分离，复用中点搜索候选

Current：上一轮=progress。固定盘原Station真实5例已终态，本轮先定位close与shortcut，再实际验证新文档网页导入，不把状态重述当新运行。

Done：原左close331拍controller19.102s，后137拍占15.612s；首close另含measured_closure244。轨迹算术推导常规chord6364点、后137拍5869点，非ABI实测。启用补证会关闭batch；原report的384补证是外部checker，不能外推controller内部频次。CBC只读实调空正文，内部GPT核调用链及原计时。

Rejected：round116私有批量前缀＋标量补证重放9条派生弦共571状态，完整报告六次一致、244保持，但样本571点全部原轴无证，候选每点多一次batch而标量不减。三对1.752→2.025、1.843→2.398、1.775→2.564s，全部更慢；未接生产／未跑无意义物理。仅本机MuJoCo3.3.7的独立FK/几何，无积分／渲染。

Done：round117复用原shorten_path的midpoint_order，两站各三对AB/BA/AB。左候选79→10、8110→2157状态，final535保留，wall三对12.269→2.346／11.863→2.435／11.975→2.454s；右74→10、7145→2167，final490保留，2.351→.607／1.831→.578／1.946→.592s。12次输出与原cloud executed_path逐位相同，原1mm/.005final和独立fresh checker复核通过。未将本地3.3.7成本当云3.15物理提速。

In progress：新增显式loaded_jaw_midpoint.py，仅在完整loaded_jaw_preload父配方开启approach_midpoint_order；旧midpoint配方缺preload不直接复用。默认不变，100项相关检查通过。新原物理两工位反序A/B待固定源码后执行，保留原90sim120wall／全部碰撞、244、释放及回退。

Done：网页发现普通Station导入继承旧成功记录，已用原detachTask修复，仅清展示关联、不删历史／取消任务。四固定X样例20项浏览器通过、原recipe QA19项、Jest56项、生产构建通过（两原告警）；真实控制写请求/pageerror均0，真实13条历史保留。工作台提交3bce2c7，根已核实际输入／服务main与历史；远端读回待本轮收口。真实新HTTP→物理链另验，不与无运动导入拼成功。

Next：固定候选源后沿原Kaggle runner跑左主工位B→C、右第二已有放置工位C→B；只差搜索顺序，逐任务原裁判及完整周期。原失败和未过50Hz保留，可靠整程收益之前不切默认。Knowledge=already_covered，沿用Wiki§20；原件在round116/117私有目录，owner根Codex。

## 2026-10-24 — 固定红盘X请求原Station通过，原拒绝保留

Current：承接X向IK／盘壁问题，不重复原开发CLI成绩。发现原execution.pick_xy_m表示整只红盘平移，不能把cube位置填进去继承固定盘证据。复用原workspace-development-v1，盘与物体分开；不新增mode或授权层。

Done：新增显式pickup_open_jaw_rad=.5/.35及mesh_box_axis_refinement布尔透传。补证仅复制本任务RoutePolicy，省略继承、显式false关闭；原默认不改，不按坐标选参。四个固定盘Station样例覆盖X±11/±20mm，pick始终(.24,-.13)，cube独立声明。本次根35项Station／原evaluate／recipe检查通过，实际四份JSON解析也一致；尚非物理交付。

Review：agent-link CBC本次只读返回空正文，不计有效结论；内部GPT找出盘／目标混淆并实施，根核diff及原样例解析。新模式提议经源码复核后否决，现模式足够。原IK／OMPL／1mm／244／90sim120wall与原裁判未改，Mint和其他Agent在途工作保持。

Done：固定2d7097ef，Kaggle实际slug so101-fixed-x-station-20261024 v1已COMPLETE；两端点新Station完整抓放与原中心回归3/3原pass，右.5／左false负例两次原grasp_leg_collision、0sim保持fail。详见[m1a-x-station-fixed-results.md](m1a-x-station-fixed-results.md)。两端点sim/wall分别79.16/54.099s与74.02/98.140s；中心77.40/51.399s。五例实际红盘固定；右三扫各246、左与中心各244，原释放／脱离／回位、自由物体与清理通过。根与独立reader另读原件、Monitor与ReleaseAudit exact重放和495/463/484实帧。

Remaining：完整50Hz仍未过，右117／左903／中心114慢拍；左P95 37.600ms、最大617.523ms。左初始化shortcut14.996s、close控制器累计19.102s；OMPL搜索.134s，不把主要成本猜为随机搜索。不是性能A/B，不与旧VM差秒或切默认。±11mm样例本组未跑Station，网页新固定盘样例整链也未验。

Next：基于原完整计时只读拆shortcut／close的重计算，保留每次IK、原1mm与全部扫掠；新固定盘样例的浏览器导入与实际HTTP链另按原任务入口验收。不插值开放连续区域，不先跑20＋20。Knowledge=already_covered，沿用Wiki§20；owner根Codex。

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
