# Findings

## 2026-10-07 先找实际热点，再改善树极值初始化

仪器化520状态×285pair的14字段与原库逐位相同，tree占pair嵌套计时约82.5%，实际热点集中3网格。真实顶点greedy极值seed保留原DFS、strict双端剪枝、原index ties及nonfinite扫描回退；有限父界包络证明新剪枝不藏原算术失败。固定100扫的52点中位25.403685→13.535072ms（46.7200%），通过预设5%门。计数不是唯一顶点，仪器化时间不作收益。

完整周期P95改善至38.707517ms但仍1296周期超20ms；真实52扫仍17/1899超20ms，同步规划与录像成本保留。P1正式墙钟91.931966s较诊断76.144990s慢，物理字段相同，不能从静态比例推算整回合保证。P2固定10/10、dev-09余48.098790s墙钟，sim余2.48s；这些不构成留出泛化、硬实时或真机证据。[完整结果](../../experiments/colab-twin/output/visual-grasp-native-profile-20261007/REPORT.md)。

## 2026-10-07 小范围等值优化不等于在线全扫收益

保存完整周期中controller占排他费用70.73%、视频19.24%；controller内sweep属于子集，不能叠加。整个controller和diagnostics归零的乐观算术仍P95 22.772794ms，说明仅加速判定不足以通过现有完整周期。dev-09无视频，其捷径静态验证15.755535s；不要用名义P1录像成本预测最坏案例。

520状态静态拆分中native占82.56%、FK0.55%。逐位相同p/R的投影缓存只改善固定五轴244点预检，在线52点五轴也变化，改善0.7776%；世界常量复用改善0.8727%。每候选11892次状态评估（含重复）×285对的14字段逐位相同，但均未到预先冻结5%收益门，未进入物理评测，原生产恢复。源码重复存在，不代表它主导已编译代码的耗时；下一步按实际完整投影/树访问热点选优化。[证据](../../experiments/colab-twin/output/visual-grasp-world-constants-20261007/REPORT.md)。

## 2026-10-07 接近缩短和更强查询证书的验证边界

原shorten_path可复用于接近段，必须保留原路线/端点、.005rad独立连边和最终整路核验。128/512上限是候选边数，不是状态查询数；本轮最终静态11条共104510路线查询，加dev-01十次85410成本查询，共189920查询×285pair。dev-01/09预测省25.309725/9.447592s；实际抓放评分另验。

保守native找到足够分离证据会提前返回。1mm查询的返回下界低于2mm不能证明不存在更强证书；六个固定姿态查询显示起点1mm返回1.967667mm，而显式2mm查询可证2.310180mm。新可选certificate_margin_m只能等于或提高原guard，默认不变、拒绝更低/非有限参数。新捷径请求2mm，raw/final/online仍1mm；有限采样不构成连续路径或跟踪误差包络证明。

baseline实际P2 8/10且dev-05安全停机1，证明名义1mm捷径有效不等于受扰跟踪有效。完整循环revision1中位29.301654/P95 56.759456ms，50Hz仍失败；正式P1 74.14sim完整通过；原固定P2最终10/10，正常5/5、扰动5/5、完整注入5/5、安全停机0。开发门通过，完整50Hz仍失败；固定开发集合不替代留出或真机验收。[静态证据](../../experiments/colab-twin/output/visual-grasp-approach-shortcut-20261007/revision1b-static-report.json)、[原P1](../../experiments/colab-twin/output/visual-grasp-approach-shortcut-20261007/p1-revision1/report.json)、[原P2](../../experiments/colab-twin/output/visual-grasp-approach-shortcut-20261007/p2-revision1/report.json)及[416项评分复核](../../experiments/colab-twin/output/visual-grasp-approach-shortcut-20261007/revision1b-p2-review.md)。

dev-09旧释放起点82.78sim；本次为73.32sim，原回位预检79.94sim＋7.602465s≤90，实际87.52sim完成。case墙钟117.966399s，只余2.033601s；相对baseline增加22.578978s。路径变短与程序变快是不同事实，初始化查询和在线扫掠仍需计时。原26条累计4202.513212/9000s，旧14条前缀完整。

## 2026-10-07 累计接近路径耗尽后段预算，释放末接触尚未证异常

只读核固定P2全10例与P1，commit00faafb源码及保存结果保持。dev-01/09接近段42.02/38.50s，对应保存路径6.6272/6.0610rad；成功8例为22.98–27.38s。两例运输26.50/26.70s处于成功组24.76–27.36s范围，优先检查接近路径长度。源码直接使用OMPL返回路径，已有shorten_path只用于回位；没有验证新接近捷径或证明其足够短。

释放stage_started取冻结估计时刻86.06/82.78s，首post-step轨迹晚20ms，不能混用。原motion_duration每段至少2s；原释放6+.6s和脱离/回位/停留预算最低7.4s共14s，因此两例原准入预算下界100.06/96.78s已经越过90s。7.4s中的.1s是计划储备；该下界不是实际精确完工时刻。所有例只有一次接近计划、无重规划；缺失运输分腿持久化不等于未经规划。

成功8例在release末拍也有robot force，随后于separate阶段达到原连续.2s低力脱离标准。两失败末力落在成功组范围内，未证独立释放几何异常；两例没有完成脱离/回位，仍按原评分失败。后段跟踪误差和夹爪已开不能替代完整任务评分。

下一候选以原1mm、jaw=.5及现有shorten_path的.005rad复核密度核接近路线，再记录运输/脱离/回位各腿预算；当前OMPL接近计划使用.015rad。128上限是候选连边数，不是几何查询数，最终整路仍须复核；实际省时、安全和成本待核实。原P2 8/10、完整20ms未过，20＋20未运行。128输入绑定，原14次1799.422648/1800s台账不变；0新物理/FK/查询/渲染/训练/云端/实体。沿用Wiki按任务选择验收依据。[完整只读证据](../../experiments/colab-twin/output/visual-grasp-route-release-audit-20261007/REPORT.md)。

## 2026-10-07 完整顶点树加速保留判定，原P1通过、P2未过

2026-10-07 完整顶点树加速已接入并通过等值：44905扫掠姿态×285对、14字段逐位相同，106项相关回归通过。52点持物扫掠中位99.519→24.611ms，P95仍26.048ms；完整4063相邻控制周期中位28.058/P95 54.333/最大946.125ms，2146超20ms，50Hz未通过。原入口P1完整仿真抓放1/1：81.28sim/104.656wall、真实抬升40.896mm、释放后漂移0.313mm、回位完成且0安全停机。冻结P2为8/10（实际10/10、正常4/5、扰动4/5、完整扰动5/5、安全停机0），未达原10/10门。原1mm/0.2mm、90sim/120wall及总台账保持；20＋20未运行，ACT暂停。

52点成本未进20ms；完整计时含渲染、物理、监测、录像、规划及相邻调度间隙。14字段逐位等值和原P1成功分开记录，不宣称完整实时能力。新diag/P1完整4064行及旧1910前缀共同字段25项零差；原release quiet/2mm/force/回位评分保持。

dev-01在86.06sim才进入释放，最早原transition92.66sim超过90；末拍仍有单指力，未脱离。固定P2按原10分母执行，不加修正、放宽阈值或加预算。root下一步只读核累计路线时长与释放接触状态；完整50Hz扫掠/规划调度独立待办。dev-09在89.40sim因insufficient_time_for_safe_return停止，释放、脱离和回位均未完成。106项相关回归、静态112/周期44/P1物理33项审计通过只说明各自范围。

采用既有Wiki按任务选择验收。总台账1799.422648/1800s，没有训练/云端/实体；原模型、输入、保护路径/index/README及旧失败保持。source仅内核和专项测试改变，证据继续Git忽略。 [完整报告](../../experiments/colab-twin/output/visual-grasp-sweep-tree-20261007/REPORT.md)。


## 2026-10-07 在线夹爪余程扫掠成为调度瓶颈

单姿态2.45ms组件成本不能代表完整控制周期。保持8b94生产源码与全部原物理阈值，先做一次AST等值计时诊断：1910相邻start-to-start周期中位21.989/P95 198.571/最大961.496ms，1126超20ms。52姿态的持物余程检查持续存在，lift/hold body中位约115.5ms；首次close同拍重复全扫共488姿态，不能靠一次去重宣称50Hz。RGB/video等也计入周期；仅测到hold，后续搬运、释放、回位成本仍未知。

随后原入口P1复验0/1。夹起40.777mm并持物3.58s，原墙钟检查在38.22sim停止，未放置/释放/返回；安全停机0并不表示完整任务通过。当前生产源码、模型与四项native身份匹配，诊断和原P1共同1910拍11字段逐项相同。P2前置门禁实际拒绝，新增0案例；20＋20未启动。旧P2 6/10不改判，ACT暂停。

保存计时body与start-to-start的差异：11.111249ms拍间记账/调度间隙已计入后者，末截断单列；嵌套方法inclusive时间不相加。原raw的full_process_wall_s其实是episode调用，校正汇总不称整个CLI耗时。原120s墙钟检查没有被改为更大上限；正在执行的controller返回后才停止，P1 case实际120.170374s。沿用原ledger，八次总531.089930s、1800s账面余1268.910070s。

采用Wiki按当前任务选择验收依据：本轮交付实际调度负证据和新源码P1失败，不将证据审核通过称为算法或开发门成功。root下一步处理全余程重复判定成本；须保留全部采样/配对/原1mm及0.2mm，再做等值与完整周期门、原P1/P2。未实现新的缓存或批处理，不减采样、不放宽安全。[完整报告与独立审核](../../experiments/colab-twin/output/visual-grasp-scheduling-20261007/REPORT.md)。

## 2026-10-07 加速判定通过，完整夹爪离散扫掠已补齐

冻结C++候选在4560原pair＋3680指定pair/两阈值记录的11字段逐位等值；危险误证、合格缺证、边界误证均0。100次静态FK＋285对判定中位2.454/P95 2.564/最大2.691ms，0/100超20ms，几何预处理31.823ms单列。原方向、完整mesh/box、掩码、具体装配例外和六关节限位保持；无CCD距离输入。54项独立算术审核通过。源码内核和新编译库与冻结版本分别逐字节一致；65项生产适配核验和10项最终源码审核通过。

惰性loader在被忽略的output绑定source/compiler/flags/library；编译与锁等待有界。已加载handle固定CDLL，metadata只读重核磁盘来源，失配不换库。runner把C++与运行库身份纳入阶段门控，来源失败继续保存case证据。新的保守checker只接视觉抓放，返回认证下界而非真实最小距离；不支持的无限plane拒绝，其他实验原CCD路径保持。

计划闭爪、进入close前实测q6→闭合目标、在线实测q6→几何reference三处均有离散预检。五臂L2≤.005rad、jaw≤.002rad，含端点，4096样本上限，不裁剪或丢样；OMPL仍五维。24固定q5扫掠与8实测六维路径各244点，共7808点×285对全部通过，50项独立保存数组审核通过。dev-05/07/09无保存闭合姿态，未计作该批通过。最小返回下界1.005592mm，不当作真实最小距离或实物误差容忍度。固定整扫中位516.524ms、最大617.266ms，所以完整update/50Hz仍待验证，不能由单姿态预算推导通过。

97项去重相关回归通过，包括真实几何中间碰撞、三个旧漏检、缓存/编译/来源失配与最终门控；重复复验不累加用例。初轮适配审计误把3个授权文件要求旧hash，保留64/65记录后只修正hash/JSON，未重做矩阵。采用既有Wiki“按当前任务选择验收依据”：组件、离散路径与真实抓放分开。root下一步先核调度成本、下降路线和跟踪边界，再做新P1/P2；旧P2仍6/10、P3 NOT_RUN，ACT暂停。证据与成本图继续Git忽略，源码/测试及既有4份SpecMesh发布。[本轮报告](../../experiments/colab-twin/output/visual-grasp-support-fast-20261007/REPORT.md)。

## 2026-10-07 支持投影几何成立，实时成本不成立

原16保存位姿×285对均获1mm分离证据，4510条由包含原完整网格的局部外包盒证明，50条需全顶点支持。原17mesh/12box及198996引用点保持，没有取graph子集。方向非单位时仍用长度上界核平方门槛，每次运算向外扩展端点；缺证拒绝不等于证明碰撞。

1840指定pair对照各核两门槛。1mm严格不合格1040、合格720、边界80；0.2mm为320/1440/80，危险误放与合格缺证均0，边界均拒绝。独立longdouble全记录与有限Fraction精确算术核验通过，±1nm样本正确区分。证书只针对保存p/R表示的模型凸几何；不扩为理想FK、连续路径、自由载荷或实体安全。

候选不消费CCD距离/fromto，原4504个10mm饱和零连线pair所在保存位姿仍均获证，没有新CCD查询。100次静态FK＋帧构造＋285对证书中位103.359/P95 151.650/最大203.082ms，100/100超20ms，冻结成本门失败。组件尚未包含渲染/积分/监测，不能称50Hz通过，也不据此断言具体性能根因。

根Codex保留离线参照，不接入、不调参重跑本候选。下一候选可研究同一保守判定的高效实现，先核等值/边界和成本，尚未实施；然后仍须补完整q6/jaw扫掠与下降路线。原源/模型/1mm及0.2mm保持，P2仍6/10，20＋20未运行，ACT暂停。沿用Wiki按当前任务选择验收依据；[完整报告、数组与独立审核](../../experiments/colab-twin/output/visual-grasp-support-bound-20261007/REPORT.md)继续Git忽略，仅既有4份SpecMesh同步。


## 2026-10-07 小cap无漏报负例通过，仍存在假穿透

960个冻结指定pair对照及3840次legacy查询完成。原网格、5个box尺寸/旋转和16个旧q6保持，仅诊断内存搬移box。独立手算FK确认960证书有效：320个间隙>1mm、320个正间隙<1mm、80个接触、160个相交、80个精确门槛边界。边界不混入漏报统计。

10mm cap在560个不合格对照误放0/560（双序0/1120）；320个合格pair仍误拒36/320（72/640查询）。原100mm比较误拒256/320，同样无误放。真间隙+1.1mm可报−3.044693mm；+0.5mm可报−5.328930mm。缩小cap减少误拒，没有修复距离精度。最近低于门槛对照为0.999mm，不证明任意近门槛的无漏报；fromto长度自洽也不是表面距离证书。

冻结危险误放门控通过，生产接入仍暂缓。下一候选用原凸包支持投影分离下界独立裁决原1mm余量，未获分离证据时拒绝；须核全285对、饱和零连线、数值误差和成本。候选未实施，不用经验最大查询误差补偿，不改native/cap/原安全阈值。P2仍6/10，20＋20未运行，ACT暂停。根Codex负责接续；[证书、结果、图和审核](../../experiments/colab-twin/output/visual-grasp-distance-controls-20261007/REPORT.md)全部本地Git忽略，源/模型/旧物理证据保持。


## 2026-10-07 原报错pair被独立几何证伪，保留局部查询候选

原四个失败pair在选定姿态的legacy查询均低于1mm，但独立模型参照为dev-01 floor6.347763mm、dev-09 floor10.021287mm、dev-05 wall下界10.157617mm、dev-07 floor10.098390mm。不能再把原0.931/0.981/−1.842/0.654mm作为实际贴盘、穿盘或跟踪储备结论。16姿态的80个活动指爪/料盘pair下界均>1mm；只覆盖这些pair与姿态，不覆盖全285对或完整路径，不将旧P2改判通过。

legacy 10/20/50mm cap在同16姿态均无低于1mm查询，100mm原cap有6个；native对应2/7/13/15个，且原15点yaw回归有经独立凸包分离界证实的假零值。两代表姿态的静态forward与重新编译对照exact，排除这两类调用状态误用。稳定或更大距离不等于准确，cap截断值也不是远处真距。[官方API边界](https://mujoco.readthedocs.io/en/3.3.7/APIreference/APIfunctions.html#mj-geomdistance)。

局部legacy10mm查询仅作为下一候选，尚缺贴阈值/接触/穿透负例；生产flag/cap和原安全阈值不变，不直接切native、不据异常query抬高抓取姿态。通过候选负例后再补完整q6/jaw扫掠，FK路线弯曲与扫掠缺口仍保留。根Codex负责接续，P2仍6/10、20＋20未运行、ACT暂停新增训练。[证书、数组、原回归和方法审核](../../experiments/colab-twin/output/visual-grasp-distance-crosscheck-20261007/REPORT.md)及425项收尾复算保持原源/模型/输入；静态模型核验不替代完整物理任务。


## 2026-10-06 距离可靠性成为扫掠下降与跟踪修正前置

三项只读审查完成，原1mm/0.2mm/0.003rad及生产代码保持。预检只插值五轴并固定目标jaw，遗漏闭爪中间角度；24条扫掠58224样本复现dev-01中间查询小于1mm。该覆盖缺口与距离算法的可靠性是两个独立问题。

31条参考/117141静态样本确认dev-05/07的down端点按原查询不合格；旧dev-05的0.770161mm是首拒绝，不是全路线最小值。构造下降FK的XY弯曲1.343848–1.449605mm；Cartesian分段IK可约束路径形状，不能修复本身不合格的端点。dev-09完整参考仅94.388µm查询储备。

3652实测行的四姿态对照分离臂与jaw影响；dev-01/09终止拍同jaw查询差204.028/248.013µm符合局部顶点移动界，但不认证未来储备。更大的4.006840mm查询差超过全几何移动界583.102µm；dev-01 jaw变化0.0002rad带来5.213211mm查询跳变，而顶点移动仅16.557µm。说明原legacy距离存在数值不一致，不能把全量峰值直接转成安全补偿或物理穿透结论。[同版本官方警告](https://mujoco.readthedocs.io/en/3.3.7/APIreference/APIfunctions.html#mj-geomdistance)。

原native CCD分离姿态反例与本次legacy跳变共同保留；不直接切flag，不改变cap/安全阈值。先核关键距离，再补局部完整q6/jaw动作预检并选有效抓取/下降候选；均未实施。原P2仍6/10，20＋20未运行，ACT仍暂停。完整数组、异常pad查询、脚本和350项收尾复算见[本轮报告](../../experiments/colab-twin/output/visual-grasp-clearance-audit-20261006/REPORT.md)；输出继续忽略，根Codex负责接续。采用Wiki按当前任务选择验收依据，不用静态计算追认自由物体抓放。


## 2026-10-06 伺服连续性修复通过，开发批次未通过

2026-10-06 伺服目标连续性已修复并通过名义完整抓放：81.28s完成释放、脱离、避开已释放物体、回位和停留，安全停机0；三次换段首拍命令跳变0。冻结源码开发10例为6/10（正常4/5、计划扰动2/5），四例均在释放前失败，20正常＋20扰动未运行。

几何参考从实测q开始；separate和retreat捕获一次上一命令与实测q的偏置，段内固定，settle保持终点。名义最大偏置0.560012mrad；超0.003rad或映射目标越原joint/actuator范围即拒绝，不裁剪。几何守卫改为检查测量姿态至几何参考，舵机目标单独限位；不能把负载偏置解释为已经达到的几何姿态。释放物体包络、原几何余量与90s/120s限时保留。

P1在81.28s完整结束，真实抬升40.895624mm、双指持物30.68s；74.482s独立确认脱离，7100条2ms样本最大XY漂移0.312785mm、脱离后峰值0N，最终静稳6.98s、回位q5误差3.2679µrad、安全停机0。旧/新前3685行23共同字段exact；三次换段首拍命令跳变0。86项独立P1审计通过。

P2正常4/5、计划扰动2/5，开发门槛要求全10通过且安全停机0，当前未过。dev-05/07构造路线拒绝，0控制拍/0扰动仍计入分母；dev-06/08/09三个扰动完整注入10拍。六个进入释放的案例全部完成脱离/回位/停留；42600条2ms样本最大漂移0.319517mm、脱离后峰值均0N。558项独立P2核验通过只确认报告可靠，不追认任务成功。

四例释放前失败的静态距离查询：dev-01 close/28.24s活动指爪至红盘底0.931289mm，闭爪端点5.439730mm，须核整段夹爪扫掠；dev-05下降参考至盘侧壁0.770161mm，dev-07至盘底0.653964mm；dev-09 descend/40.76s实测至盘底0.980963mm、命令1.228963mm，须核跟踪余量。它们是低于1mm的正间隙守卫停止或规划拒绝，不直接称实际穿透碰撞；四例均未启用释放后的偏置。

49项相关测试/0skip，P1与P2开始后生产源码未改。只有两个生产文件和控制器测试变化；其余顶层Python及原MJCF哈希保持。P0复用不重跑；空p1-run.log为启动调度中断且无物理阶段，实际只有一个新P1候选。完整视频81.28s/2032帧解码通过。累计实验阶段墙钟290.473834s包含此前82.706686s及新P1/P2；没有训练、云端或实体操作。输出、脚本、日志和视频继续Git忽略，旧失败证据保留。

根Codex负责下一接续：检查夹爪闭合全程扫掠、下降路线与盘边间隙、实际跟踪误差所需余量。四个失败案例及原1mm安全余量保留；本次不追加抓取修正或批次。ACT继续暂停新增训练。 [伺服修复报告](../../experiments/colab-twin/output/visual-grasp-servo-20261006/REPORT.md)。采用既有Wiki按当前任务选择验收依据；静态代数与单元测试不代替自由物体接触、完整释放和回位证据。



## 2026-10-06 释放脱离与回位候选停止

2026-10-06 用户授权处理释放后的脱离、物体避碰与回位。新候选已接入估计释放盒、垂直脱离、带物体避碰的短回位和独立释放评分。静态路径预计81.3s；唯一物理回合在73.72s因末端下沉0.234mm触发脱离守卫，P1仍失败，未进入开发10例或20正常＋20扰动。

释放盒在开爪前通过FK与持物估计固定；不从执行物体真值定位。新独立nq6查询包含与物理target掩码兼容的机器人几何和两pad。pad用解析SAT避免本案例libccd负距跳变；初始接触只允许受限垂直离开，达到1mm后撤销例外。回位直连优先，OMPL fallback做有界简化并逐边验证。保持原模型、1mm臂余量、0.2mm持物余量与90s/120s限时。

新ReleaseAudit只在评分侧按2ms检查全部机器人目标接触，开爪前锚定XY，位移≤2mm，连续0.2s低接触力才记脱离；随后再接触失败。46项相关测试通过。唯一P1真实抬升40.896mm、持物30.68s；73.72s进入separate第一拍后停止，grasp=true/place=false，safety_stop=1，retreat/settle未运行。报告2ms最大XY变化0.313mm不等于完整撤回改善，未detached时0再接触峰值没有验收意义。

独立FK核验：pinch下沉233.724µm，越200µm下界；pad顶点下沉206–217µm，越50µm容差。XY154µm和臂碰撞检查仍有效，pad SAT间隙改善。首separate command重置为实测q，肩/肘命令跳变0.560/0.313mrad；同q/qvel的静态执行器查询确认原约−0.559/−0.313Nm保持力矩被清零。后续下沉的唯一因果尚未由动力学对照证明。

本轮候选已停止，原90s/120s限时及碰撞余量保留。根Codex负责下一次明确接续：先处理释放→抬离的伺服目标连续性与稳态偏置，再验证几何参考与执行参考的一致性。不得直接放宽回落阈值、把旧command硬接为路径起点，或提前按抓放分项结束。ACT继续暂停新增训练。

[完整报告与视频](../../experiments/colab-twin/output/visual-grasp-release-20261006/REPORT.md)。旧pilot失败保留，P0复用非重跑，预算账累计包含旧48.887s及本轮33.820s。原现场25项保护继续验证，原ACT与其他既有生产脚本保持。只读审计无物理重跑；2ms原始序列未单独存档，独立复算按20ms窗口及累计统计限定结论。


## 2026-10-06 视觉定位与释放撤回的实际边界

2026-10-06 视觉定位主线已实现并实际核验：P0 20位置最大误差0.614mm，4类拒绝反例通过。P1基线因前臂遮挡停止；唯一修正改用机器人投影包络提前交接。修正版真实抬升40.9mm、持物30.68s并在蓝盘最终落稳，但撤回推块约40.4mm，90s时仍未完成回位，整回合失败。一次修正已用尽，P2和20+20均未运行。

- 40mm指尖距离不能预测整臂遮挡。基线前臂遮挡时指尖仍距目标137.6mm；几何包络预警使交接提前到10.04s，使用10.00s有效估计。
- 定位误差通过不等于抓放整回合通过。原评分器在79.80s才首次满足抓放，控制器到90s仍在撤回。
- 释放与撤回需单独核验。开爪6s后固定指仍接触，随后推物约40.4mm；静态地图避障不等于避开已释放任务物体。
- 当前撤回的六关节规划模型没有加入已释放物体的估计占据体；静态碰撞查询无法排除再次触碰它。后续需补释放脱离与该障碍建模，不能只加时长或在评分首次通过时提前结束。
- RRT原始解没有自动得到最短路径。撤回路径约为端点直线关节距离的10.73倍，但直连安全性仍未验证。
- [完整报告](../../experiments/colab-twin/output/visual-grasp-pilot-20261006/REPORT.md)区分物理分项与整回合，不以最终盘内静止掩盖撤回问题。

## 2026-10-06 方法审查与工程主线

- 2026-10-06 用户已选择稳定自主抓放主线：视觉定位→已有IK/OMPL→伺服抓放，ACT作为支线暂停新增训练。集中方法审查与CPU逐槽统计完成；尾槽h15/h0标准差约21–22倍成立，但L1输出梯度不按残差幅度放大，尚无唯一根因结论。现有专家含目标/载荷真值控制依赖，须先隔离再接视觉。新视觉控制器与物理验收尚未实施。
- 原七项门控scope本来就是保守诊断；不能将逐动作幅比当作实际抓放必要条件。A/B结果仍是失败，不通过追认快照或改历史阈值修饰。
- 四条同布局/相关恢复数据需要按独立采集家族划分，帧数和采样次数不能当独立示范数量；训练统计不得读取验证/测试组。
- 现有专家读物体真实位置、姿态、盘底接触和载荷相对姿态影响动作。视觉主线要隔离这些控制依赖；评分器可保留真值，传感器代理与现实差异应显式声明。
- [方法审查与候选执行协议](method-review-20261006.md)含原始审核/官方配置/选模与OpenCV参考。当前不增加训练预算或迁移仿真平台。

## 2026-10-06 云端local-balance等步数对照

- 2026-10-06 现有local-balance已透传Colab CLI并完成唯一L4训练：5000步/173.028s优化、峰值332MiB，权重回收且实例已实际释放。B2115五轴方向全对但首帧幅度不足；最终B5000首帧pan/flex/roll反向，原七门控失败四项，未启动物理或补训，S7e仍未过。
- B5000相较A5000，h0 pan/flex/roll改善而lift/elbow退化；B自身2115→5000的肘h0 MAE0.156083→0.436829mrad、首帧方向退化。原七项门控不能用平均误差或较好的诊断快照替代。
- 局部1:1仅指完整池起点槽。实际起点696/693、有效动作槽11136/9965；raw0/1各350/346次，非局部曝光与A一致。排除旗标缺失或完全漏采，尚不能确定图像/梯度/优化谁是唯一瓶颈。
- 根Codex保留云端A/B两级权重；下一最短候选是冻结B2115/B5000、固定q0替换真实起步/收尾RGB，核对起步回退是否伴随图像动作区分减弱。本轮未执行换图探针；不凭本轮增加步数、改采样权重/主干/损失或以快照替代最终候选。 [来源与独立核验](progress.md#2026-10-06-colab现有local-balance完成最终门控未过)。

## 2026-10-06 冻结云端模型的局部图像动作辨别

- 固定q0换真实raw0/raw2349两RGB：2115→5000步响应0.001599→0.017197µrad；最终只占6mrad参考动作差0.000287%。同图重复差0与原保存首帧全chunk差0，响应可重复但任务量级不足，不称全局视盲或证明主干失效。
- 两图下最终输出均更接近收尾绝对目标；其中起步图距起步5.699520mrad、距收尾0.386042mrad。更多步数改善平均动作拟合，不等于利用图像区分这对任务状态。
- q_end与q0差0.137024mrad、203像素改变；固定q0+收尾图是反事实，只作描述性目标参照。末帧只有h0专家标签，不能拿padding检查尾槽准确率。六次重复不增加独立场景样本量。
- 下一训练变量选已有local-balance采样开关：与本轮A保持同Colab L4、5000步/600秒优化上限、2115诊断快照、四RGB、FP32/batch8/seed0/fresh Adam和原七项门控，仅开启近q真实起步/收尾1:1均衡。原B2115曾改善部分轴但肘轴退化，故这是等步数单变量验证，不是已证实修复。本轮未启动训练或改生产源码；执行前需在现有云端worker显式透传开关并验证默认A不变，不扩大预算或同时改主干/损失。 [本次证据](progress.md#2026-10-06-冻结云端模型起步收尾图像动作辨别)。

## 2026-10-06 Colab视觉训练与同轮2115至5000步对照

- Colab CLI 0.6.0现有安全适配层可承载四RGB原字节上传、独立Python3.12固定Torch/cu126与官方LeRobot安装、5步资源预检、唯一有界训练、双权重回收和实际unassign。L4本轮5000步优化171.180s、峰值reserved332MiB；不能据此保证未来网络/配额或持续运行性能。
- 首次直连在第3片ConnectTimeout、未启动worker，实例已释放；第二次控制器在分配前查询超时，无实例产生。使用本机已有代理的命令级HTTP_PROXY/HTTPS_PROXY后第三次控制器完成。该次仍有一次PUT和一次状态GET ReadTimeout，按预置有界规则恢复；不能把代理当作唯一根因或称网络故障彻底消除。
- 分片PUT/GET同路径同字节最多3次尝试；分配/训练不自动重试。只有训练完成不足以说明回收完成：原子recovery index写完、全包及逐文件哈希核对、真实释放分别留证。私有Colab会话信息不进入归档、上传包或Git。
- 同轮2115→5000步，首150拍h0五轴MAE全部下降，首10拍方向错误14/50→1/50。但最终首帧腕旋仍反向，其他四轴delta仅专家6.7%–36.4%；七项门控仍失败三项。训练集局部平均误差改善与最初观测可执行性分开验收。
- 更长训练仅在这次seed0轨迹中改善上述平均拟合；没有隔离视觉语义、采样或具体梯度成因。新模型未经真实策略轨迹/抓放评测，快照不能替代最终候选，S7e未通过。[协议、回收与原始数据](progress.md#2026-10-06-colab-l4完成5000步原起步门控仍未通过)。

## 2026-10-01 学习会审补充

当前抓放trajectory.json不含arm qpos/qvel/ctrl，仅有物体和接触诊断；20ms诊断与40ms视频没有训练帧索引。固定搬运成功不证明任意扰动恢复。ACT官方固定版本支持无图像ENV状态、无视觉backbone；imitation有正式MLP-BC实现但整包依赖较多。本机原规划venv无Torch/LeRobot等学习依赖；两个模型均未训练或测内存。

AGY首轮CLI SUCCESS/exit0和原生done仍是部分正文；定向复核完整完成后改选状态ACT。ZCODE第一次取消无正文，短提示流式补取取得GLM-5.3-Flash实际完整回答、0工具事件，保留MLP先行意见；成功请求28063tokens不包含失败请求/AGY完整可归属用量。原始资料被Git忽略。详细可定位来源、引用锚修正和不采用的无依据结论见[learning-review.md](learning-review.md)。

- 对应开发根为 `/home/muqiao/dev/ros2/projects/so101`；旧 so101-win7 路径是兼容链接。
- 六份文档复制到被忽略的 `local-documents/graduation-20260629/`。本地 manifest 保存文件名、大小与 SHA256，manifest 也被忽略。
- 历史来源：Codex session `019ef2b7-61a2-7ce3-8789-665ed12b303b`，6 月 29 日答辩反思和 DOCX 转换；不把旧助手声明当本次执行证据。
- 当前 Colab CLI 0.6.0 已安装；`colab sessions` 认证调用成功。无需重新登录、导出浏览器凭据或更新 CLI。
- 有效模型含六个弧度关节和六个位置执行器，末端 site 为 gripperframe。模型 SHA256 为 d75253eb568e8a7214db9c631ab7bed4217f608a26f7276ebe9a7636cac82580。
- 复用 MuJoCo 包中的 13 个完整 STL；第三方源目录的同名 STL 是零字节。旧 scene.xml include 名称不匹配，本轮只在实验副本生成场景。
- Git 本地 HEAD 427e3eb 落后已发布 origin/master e5c0168 两提交。源码 app.py、静态前端、鉴权文档、teleop 测试、动作导出器与远端逐字相同；不能依据旧 index 把它们当未交付。
- 仓库远端已核对为 qiaoqiao2521/so101，保持 public/master；本轮不改可见性或重写历史。

## 2026-10-01 自主规划续接审计

- 用户选择 MuJoCo 为运动自主规划核心。原生 Colab 平台继续作为同一项目内部模块；不新建平行仓库。
- 当前主工程、repo-revival 整合快照、repo-scan 两个旧工程和 delivery 已定向比较；现存 MoveIt/OMPL 规划文件没有更完整的外部副本。旧 workspace / follower 路径已是兼容链接。
- `pick_place_runner.py` 实际调用 MoveGroup / OMPL，默认 RRTConnect，支持关节目标、重试和轨迹导出；2026-03-14 非空日志记录 7/7 预设目标通过，多点轨迹存在。本轮不重新认定当前运行或避障验收。
- 5月 MTC Cartesian IK/FK → Gazebo reach 只有开发记录与非空 suite summary。jitter20 的 200 个、jitter50 的 500 个逐轮 artifact 均为零字节；核心 C++ node / launch / evaluator / projector / recorder 缺失。本地快照及有界 Agent 历史没有找回原件。
- jitter50 summary 的 reach 采用 8 cm 阈值，平均距离 5.64 cm、p90 7.34 cm，不能作为精准抓取成功率。原 evaluator 缺失，周边门禁只消费指标，不能替代 TCP 距离计算。
- ROS URDF 是 17 visual / 0 collision；原生 MJCF 是 17 visual class geom / 13 collision class geom。后者仍须验证编译后的 mask、碰撞覆盖和凸包误差，不按 URDF 缺失结论重造全部几何。
- 原 Gazebo 世界桌高约0.75m，目标z约0.8m；MJCF使用自己的world/base/TCP坐标。迁移目标须显式转换并用FK核对。
- `lerobot` 独立源树含 Placo FK/IK；没有证据证明该实现已经在现有 SO101 Colab 平台运行，不作为已验收替代库。
- 实际 AGY CLI plan/sandbox 单次只读咨询返回 MuJoCo + Python IK/OMPL 的单方向建议，并推荐可达性→碰撞→跟踪顺序。仅基于摘要，未独立跑实验；原响应位于被忽略的 local-documents。
- Gazebo官方支持server与OGRE2/EGL无头渲染；本项目未在Colab实测。Jazzy默认搭配Harmonic，旧Classic/Humble链需要迁移；Colab免费且无正计算余额时限制远程桌面。
- MuJoCo3.3.7保持当前基线；Mink1.1.0与OMPL2.0.1是待隔离验收候选，本轮未安装/升级。官方依据集中在 `../../docs/MUJOCO_MOTION_PLANNING.md`。

## 本轮实现新证据

- 源MJCF13个移动collision mesh全部mask1/1；底座四个visual在派生场景复制为collision。排除同刚体、六对直接父子装配及固定底座安装；非相邻负距离shoulder/gripper自碰仍检出。
- 原生CCD在纯yaw相对不变时误报0，派生XML选择libccd；15yaw回归保持距离。其分离距离为近似凸包指标，不是实机安全。默认group3环境不可见的问题通过零mask的group2副本修正。
- MuJoCo实际夹爪状态会微小偏离固定指令，执行碰撞查询必须使用真实q6并解除精确固定要求，规划仍固定；不能以指令替换实际姿态。
- Colab CLI0.6.0远端Python错误不保证本地非零退出，timeout也不保证停止内核；以下载的严格产物/逐轮验收为依据，并在finally释放整个本次会话。
- 当前20轮只覆盖同一个盒子附近±3mm位置任务；离散路径0.025rad/执行20ms，不是连续碰撞、抓取、视觉或真实参数验收。

## 主线逐层验收入口

复用当前MuJoCo/Mink/OMPL实现和现成planning-venv，未重新安装环境。run_staged.py只在依赖版本和实际导入通过后加载模型；run_gate拒绝越过未通过阶段，失败保留其原因及后续not_run状态。已采纳Obsidian Wiki/自动化开发范式与智能体协作.md“按当前任务选择验收依据”：依赖导入、仿真reset/step、精确路径与实际执行是分别观察的结果。

本机真实单回合：reset10步/0.02秒，IK误差0.323mm，113点精确绕行，物理执行7546步/15.092秒，TCP误差0.549mm，20ms碰撞无效样本0，限位超出0。独立CSV核验756行全有限、时间递增和末行TCP误差；视频完整FFmpeg解码378帧，预览显示工作台与障碍。模型与13STL记录SHA，源MJCF未修改。位置执行使用模型原位置伺服；路径仍预先规划，动态重规划未接入。

原29项回归加3项阶段边界检查通过：前层失败不调用后层、规划异常保留执行not_run、依赖失败持久化报告且不编译模型。真实系统Python缺少依赖的CLI负例退出1且task_success=null。脚本默认不渲染；--render可选，按运行环境已有MUJOCO_GL或OSMesa/EGL默认选择。该证据不扩大成动态障碍、抓放、视觉或实机同步。

## 2026-10-01 单臂夹取建模

用户指定先建模、改善场景，并纠正主从为现实系统；本轮只有一台从臂。找到本地BLD-001建模说明、主从场景生成器和动作模板；当前工程无其记载的Blender/GLB成品，LightArmPreview.vue与leader专属STL为零字节。复用完整的原生从臂13STL，新增grasp_workcell.py/preview_grasp_workcell.py及动态物体/夹爪检查。

新模型包含工作台、开放红/蓝料盘、相机支架、自由物体；生成1280×720三视图与100帧/4秒机械开合视频。原模型SHA仍d75253eb568e8a7214db9c631ab7bed4217f608a26f7276ebe9a7636cac82580。物体18×18×16mm、10g；实测中心z从0.012m落定至0.009784m，真实pick_floor接触。夹爪实际范围0.250019–0.799997rad，预览期间物体抬升约0；grasp_success/lift_success=null，尚未夹取成功。视频独立全量解码通过，34项回归检查通过。派生MJCF可编辑，原模型不改；无实体或云端操作。

结果保存在Git忽略的experiments/colab-twin/output/grasp-model-72f103318b2a4cf78c7b89f317ee53ed/。原场景建模说明只用于布局参考，仿真坐标和物理参数不当作实物标定；现场模板不复制发布。后续owner根Codex：先对位/接触建模，再以物体抬升与持续夹持验收；已有静态规划入口及遗留交接保留。

## 障碍接触夹取

原TCP位于固定指尖，不能直接当指间中心。派生夹持点在gripper局部(.006,0,-.094)m，使用独立状态求垂直姿态IK；下降到世界z=.019m以避开指尖/盘底碰撞。全网格凸包与小方块接触出现毫米级穿透/下挤，指尖接触垫替换仅目标与两块指爪的接触；其余链接和所有物理环境仍与目标碰撞，原网格仍负责机械臂与桌面/障碍碰撞。接触垫尺寸与摩擦、.15Nm夹爪力矩是未标定仿真假设。

MuJoCo3.3.7/libccd在worktable盒子和collision_shoulder_2距离查询distmax=1m时给出-.2456m假穿透；实际顶点最低z=.0162m且无物理接触，distmax=.1m返回+.0162m。checker改为max(.1,margin+.05)m的局部查询，远距离饱和；合法起点和真实中间障碍负例通过，既有碰撞测试继续通过。

物理执行使用单一MjData；IK/距离查询独立，避免运动学查询改变现场。障碍接触按2ms每步统计，机械臂限位/环境/自碰按20ms状态检查；规划边按.015rad离散验证，尚非连续碰撞证明。保持段须全部样本抬升≥25mm、双指法向力>.02N、无桌面/盘底支撑，持续≥1s；空夹或短暂抛起不能通过。

## 搬运放置验收与软接触下滑

保持竖直夹持的搬运路线采用内侧x=.18m绕行、3mm Cartesian采样及.01rad关节边验证。查询用实测指爪/物体相对姿态预测载物占位，仅写独立MjData；执行保持自由物体。载物箱体与较远料盘壁在.1m距离查询下再次出现假穿透，载物局部查询范围缩为.02m，大于该值的间隙为饱和值；余量.0002m只为单场景离散fixture。

正常软接触即使双指各约2N，物体仍以约.5mm/s下滑，二十多秒搬运会滑出指尖，最终落在两盘之间；升高力矩不能消除。MuJoCo3.3.7官方modeling.html#preventing-slip明确区分摩擦不足和soft-contact慢滑。搬运模式选Noslip10次后通过，.15Nm力矩和原接触几何不变；原抓起模式保留noslip=0。该配置是前向仿真假设，改变逆动力学/计算成本，未当作实物材质标定。

完整验收要求途中持续双指接触、最后物体整个旋转盒子XY投影在蓝盘内部；松爪后真实盘底接触、双指接触力归零、速度<.002m/s、z约.01m，机械臂撤离后持续≥1s。关闭Noslip的真实物理负例搬运滑落被停止，轨迹可恢复。没有物体动画/附着/weld/mocap。

## 状态学习实现校准

- mj_step后派生量与积分后的qpos不是同一边界；采集与回放需一致的forward刷新次数。状态与动作存float64、网络转float32后，原动作3133步所有state/env/time误差0；原float32档案在释放接触处严格逐帧匹配失败，原证据保留。
- 固定等待6秒闭爪使瞬时状态对应不同专家阶段。学习采集改以双指接触/夹爪速度推进、时间仅作失败超时；释放先确认活动指松开和盘底承托，固定指完全离开要等待撤离。
- 官方状态ACT本机反传约118MiB allocated，4GB不是本次阻碍；120秒内离线动作误差下降但纯策略0.36s碰撞停止。故数据、资源、回归、真实任务必须独立验收，后层not_run。
- 连续动作chunk不能跨invalid扰动帧或episode；专家stage/time不得成为策略输入。动作源仍是实际重规划纠正，不是扰动执行命令。

## 起步与接近恢复诊断（2026-10-01）

旧绝对ACT首步pan误差约-.02448rad，而专家arm指令与actualq的95%偏移仅约.0023–.0035rad；下一拍pan/elbow速度达到-1.178/-1.061rad/s，远超专家接近速度。旧恢复执行.2s后才采纠正，首valid速度接近零，不能覆盖起步失稳。根因证据支持先改变动作尺度与恢复时机，不能把4GB显存当作这次失败原因。

内部arm_delta、qvel尺度下限.1、关闭VAE/dropout的5000step诊断：首步arm最大误差.000187rad，首动作arm五轴MAE约.000022–.000188rad；但夹爪首步预测.50719而标签.5，20步实际漂至.55210，后续shoulder漂到下限附近。纯策略39.94s仍未抓起物体，限位停止；误差改善不等于过门槛。保存于ignored `output/state-delta-sanity-20261001`、`policy-delta-sanity-20261001`、`delta-first-audit-20261001`。

专家下降终点若静止后才闭爪，相近观测会因隐藏阶段收到不同jaw标签。新版在实际下降/下降放置运动中触发jaw切换；释放门槛按实测终点高度校准为14.5mm，去掉自由落体期间会重新闭爪的速度条件。四份v3实际成功，共12378帧/12375有效标签，jaw切换均在descend/lower，后续reclose=0。有界近邻k16、标准化L2半径.001、动作冲突门槛.05rad未发现冲突；这不证明观测充分性。

v3起点±.006rad/20ms恢复首valid pan速度+.263833/-.263756rad/s，接近35%处+.002rad/20ms首valid pan速度.047732rad/s。扰动最后nextobs与首valid状态/环境/时间逐字段相同，brake target等actualq。startup-plus独立3061步原动作回放state/env/time最大差0并完成抓放，3项真实产物测试全部通过无skip。覆盖仍限固定布局和这三类小扰动，尚不覆盖旧失稳的高速状态。

同v3权重的三项有界执行消融都没有过门槛：16步chunk90s超时、nearest夹爪10.38s腕限位、两者组合90s超时；全部未抬升物体。nearest将夹爪固定到训练两标签后仍腕漂移，说明误闭爪不是唯一根因。使用新chunk日志时，诊断把fresh inference与缓存动作区别标注，投影/扰动也与raw模型输出分开，不能拿不同执行语义误报适配器错误。

v3前.2s actual pan仅变化1.49e-9rad/wristflex5.08e-12，但命令由隐藏t逐步改变；前50个float32观测仍50unique，因此不是严格重复输入不可学的证明。它支持起步信号过弱的假设。v4只把approach改actual投影lookahead（.006rad），firstarm command-q为[+.002318,-.001471,-.000947,-.004806,-.002511]，前.38s实际arm位移L2 .153997rad；后续仍timed。4份成功采集共9404帧/9401valid，包含startup多轴±[.002,.001,-.001,.001,0]以及approach35%处[.002,-.001,.001,.001,0]，实际推进20ms。nominal2350步/startupplus2351步独立CPU回放全state/env/time差0，真实抓放与3项恢复artifact测试通过。尚不能据此宣称新学习策略已通过。

### v4/v5 有界诊断与剩余门槛

以下路径均相对`experiments/colab-twin/output/`，整个目录Git忽略。v4专家档案为`reactive-v4-{nominal,startup-plus,startup-minus,approach}-20261001/expert.h5`；独立重放为`reactive-v4-independent-replay-20261001/report.json`和`reactive-v4-startup-plus-independent-replay-20261001/report.json`。仅approach反应式，descend/lift/transport/lower仍依赖时间minimum-jerk，不扩展成全任务反应式专家。

`reactive-v4-state-fit-20261001/report.json`记录四档案ACT 13491step/240.013s（wall上限240s），arm_delta、qvel下限.1、noVAE/dropout0、关键行5倍采样；归一化只fit这四份训练行，未用held-out。权重SHA `d0142fecc159f3390a9cbeeb350ff83f0ab4518eab540e24480824fc7eb213d8`。纯策略`policy-reactive-v4-{baseline,chunk16,chunk16-nearest}-20261001/report.json`分别9.74/10.22/10.22s腕限位停止，全部未抓起。`reactive-v4-mlp-first-action-probe-20261001/report.json`同四档案三层MLP 8000step/8.234s，权重SHA `ac880325022a2a0d7e009bd0540ab3ce5d08e2181f9761b9c60fc112d74c7f4b`；`policy-reactive-v4-mlp-probe-20261001/report.json`16.08s盘壁碰撞、`policy-reactive-v4-mlp-nearest-20261001/report.json`9.92s桌面碰撞。更小网络同样未打通物理闭环。

v5从`policy-reactive-v4-chunk16-nearest-20261001/attempt-000-nominal/policy-transitions.npz`取真实策略action前50/100/200/250拍，源SHA `20db559734f7ae635ed1e8a43c788ba294c693e3b4f4bdd2646b6cac8831e21e`。`policy-recovery-v5-prefix{50,100,200,250}-20261001/expert.h5`四份专家恢复正例，共9423帧/8823valid；各档invalid前缀数恰为N，executed_action精确等于NPZ float32动作转double，训练排除600前缀帧。首valid观测精确接续前一nextobs，actualq制动且pan速度分别.043567/.049191/.044557/.033647rad/s。来源、哈希与恢复状态已保存；不是给专家标签加噪声。`policy-recovery-v5-independent-replay-20261001/report.json`独立2372步重放state/env/time差均0，抓放通过，3项真实artifact检查通过无skip；仍不等于纯策略成功或完整[DART](https://proceedings.mlr.press/v78/laskey17a.html)复现。

`policy-recovery-v5-state-fit-20261001/report.json`以v4四份＋v5四份18224valid行有界接续：lr2e-4、7000step/7epoch/109.024s，预算120s/7000step。初始化权重为上列v4 SHA，归一化沿用该checkpoint的原四训练档案统计；fresh Adam及新采样计数，不恢复优化器，不重算八档案统计。输出权重SHA `26268fb563824fb0fe4268a46faa55e1b798b12386e550989b766ae8aba04472`，CPU重载绝对rad差5.54e-8；allocated87.053MiB/reserved96MiB，无held-out证据。`policy-recovery-v5-baseline-20261001/report.json`纯策略10.48s腕目标越下限，未抬升/抓放。数据回放、离线拟合与策略执行仍分别判定；[官方ACT来源及运行契约](../../experiments/colab-twin/LEARNING.md)保持固定。

定向离线因果探针固定q与其他env，只替换六轴qvel为在线值，转角处腕target−q由+.002804变为-.004647rad（专家+.005230rad），默认及chunk执行均出现反向预测。支持qvel输入敏感性假设，不证明只屏蔽速度即可成功；`v5-qvel-causal-audit-20261001/`已归档。

随后仅增加训练/推理一致robot qvel屏蔽，`policy-recovery-v5-qvel-masked-fit-20261001/report.json`从v5权重接续同八档案，原四训练归一化沿d014→26268权重链继承，fresh Adam；3886step/4epoch/120.039s，allocated87.053/reserved96MiB，输出SHA `08de5fc1d29ca6849b614f0fa5ed6b6852b1785c60af9e0be61f517eb00ccc24`。`policy-recovery-v5-qvel-masked-{baseline,chunk8-nearest}-20261001/report.json`分别18.64/52s料盘底碰撞，无抬升；`policy-recovery-v5-qvel-masked-chunk16-nearest-20261001/report.json`真实抓起并持续持有17.56s，但35.2s首次开爪时物体(.177743,.087811,.048516)m仍在蓝盘外，35.4s判定payload_lost。策略真抓起与完整抓放失败分别记录，未更改计数或验收条件。

`v5-qvel-masked-physical-audit-20261001/release-probe.json`在fresh chunk边界1760拍核对保存raw_action，排除缓存动作比较错误。固定实际q及其他env，仅替换物体速度为几何近邻训练值，首jaw由.401425变为.017844；原始物体速度置零为.018514。actual对该近邻的归一化L2差：线速度105.745、角速度134.035，4/6轴越训练全范围，支持速度输入敏感性。名义真释放帧2060原jaw .3713、原始速度置零后.4573，仍开爪；运输反例仍闭爪。这些是离线局部替换，不能保证在线闭环或唯一根因，源码/权重/数据SHA与初始不可变probe均保留。

新增显式`--mask-object-velocity`只对归一化env[13:19]（线速度3/局部角速度3）置零；已有robot mask[0:6]独立保持。训练与推理共用适配器，原统计/原始数组/动作/实际动力学不改，有限性先检查，旧默认false，初始化from/to持久化且不可静默取消。物理监测仍用原data.qvel，包含静稳/支撑释放速度与全qvel有限性检查。下一项同八档案有界物体速度消融结果待验；载物恢复collector仅有只读方案、未创建源码/数据。完整单回合门槛未过，20+20/视觉/云端/实体验收均未新增。

本轮最终物理结果：robot-only-mask ACT有真实抓取/17.56s hold，但盘外提前释放；新增object-mask ACT 120s限时拟合后14.2s底部碰撞，MLP同输入CPU对照也限位失败；完整单回合仍未通过。精确观察范围clamp无法修正提前开爪，故不接入代码。150项完整测试仅证明实现及数据层边界。源、失败证据、归一化来源核对和最短接续边界见progress.md末节。下一项应区分接近末端/持物实际状态覆盖与候选控制精度，不能凭平均loss下降或局部counterfactual宣布恢复机制已解决。

## 2026-10-02 接近末端、持物纠正与五轴学习

最新门槛：v11在固定训练nominal初态的纯策略抓放**1/1通过**，1988周期/39.76仿真秒，持物23.10s、释放后蓝盘内静稳1s，无专家介入或安全停止。五轴ACT沿用v10的14档案训练权重，新增第15条只进入夹爪头训练；不是官方完整ACT或泛化成功率。20+20、视觉、云端和实体均未新增，v6–v10失败保留。[实际纯策略报告](../../experiments/colab-twin/output/policy-correction-v11-release-single-20261002/report.json)。

已新增[独立离线纠正采集器](../../experiments/colab-twin/collect_policy_recovery.py)：真实执行已有策略action前缀，前缀标签NaN/invalid；首有效标签从actualq制动，原始速度和观测时序保持。approach入口要求开爪、无接触/抬升及目标上方位置；held入口要求当前持续双指抬持，无盘底支撑/掉物。运动学和载物占位查询只写独立MjData，执行自由物体不恢复终点或改姿态。闭爪lower仍验实际q→command的载物连线，真实松爪后才退出载物假设。[载物查询](../../experiments/colab-twin/placement.py)、[采集边界反例](../../experiments/colab-twin/test_late_policy_recovery.py)。

| 守卫版纠正来源 | 有效 / 无效帧 | 专家成功证据 | 独立raw64回放证据 |
| --- | ---: | --- | --- |
| 450拍接近末端 | 1956 / 450 | [report](../../experiments/colab-twin/output/policy-correction-v6-450-guarded-20261001/report.json) | [2406步](../../experiments/colab-twin/output/policy-correction-v6-450-guarded-replay-20261001/report.json) |
| 1700拍持物 | 827 / 1700 | [report](../../experiments/colab-twin/output/policy-correction-v6-1700-guarded-20261001/report.json) | [2527步](../../experiments/colab-twin/output/policy-correction-v6-1700-guarded-replay-20261001/report.json) |
| 1756拍持物 | 807 / 1756 | [report](../../experiments/colab-twin/output/policy-correction-v6-1756-guarded-20261001/report.json) | [2563步](../../experiments/colab-twin/output/policy-correction-v6-1756-guarded-replay-20261001/report.json) |
| 分类策略1800拍持物 | 1089 / 1800 | [report](../../experiments/colab-twin/output/policy-correction-v6-classifier1800-guarded-20261001/report.json) | [2889步](../../experiments/colab-twin/output/policy-correction-v6-classifier1800-guarded-replay-20261001/report.json) |
| v7组合策略900拍慢抬持物 | 1462 / 900 | [report](../../experiments/colab-twin/output/policy-correction-v7-held900-guarded-20261002/report.json) | [2362步](../../experiments/colab-twin/output/policy-correction-v7-held900-guarded-replay-20261002/report.json) |
| v8组合策略2500拍蓝盘边缘持物 | 742 / 2500 | [report](../../experiments/colab-twin/output/policy-correction-v8-held2500-guarded-20261002/report.json) | [3242步](../../experiments/colab-twin/output/policy-correction-v8-held2500-guarded-replay-20261002/report.json) |
| v10组合策略2517拍蓝盘内低位松爪 | 397 / 2517 | [report](../../experiments/colab-twin/output/policy-correction-v10-release2517-guarded-20261002/report.json) | [2914步](../../experiments/colab-twin/output/policy-correction-v10-release2517-guarded-replay-20261002/report.json) |

七条共18903原始转换/7280有效/11623无效；加原八条为15条、25504有效/12226无效、37730原始转换，已逐份读取HDF5的`label_valid`核对。七次专家抓放和独立回放均成功，state/env/time差全0，均明确没有评测学习策略。这是同场景真实纠正覆盖，不是完整DART或泛化证据。v11五轴ACT保持14档案训练结果，仅夹爪头消费15档案。旧admission/forward尝试也保留，未混入当前guarded训练清单。以上原始数据与报告仍Git忽略。

第五条900拍的选择有[独立CPU只读诊断](../../experiments/colab-twin/output/late-recovery-v7-held900-offline-diagnostic-20261002.json)依据：原保存诊断最早874拍满足held准入；900拍实际采集边界held1.52s、双指1.419/1.422N、物体z=.037754m、腕1.476133rad距限约.1819rad，当前场景安全且已出现慢抬偏差。固定其他状态只换近邻物体速度，使离线新chunk首elbow/wrist残差从-.000548/+.000304变成-.002936/+.003119rad，靠近专家推进标签；只换q/xyz未出现同等恢复。该合成输入未执行、未作为标签，只支持速度敏感性和低速恢复覆盖的假设，不能当线上fix或唯一因果证明。实际新专家抓放及raw64回放才确认该纠正有效。

v6四个纯策略候选全部失败：[全ACT11.42s料盘底碰撞](../../experiments/colab-twin/output/policy-correction-v6-single-20261001/report.json)；[jaw输出行37.88s掉物](../../experiments/colab-twin/output/policy-correction-v6-gripper-single-20261001/report.json)，抓起且hold20.04s；[独立分类夹爪38.02s撞障](../../experiments/colab-twin/output/policy-correction-v6-classifier-single-20261001/report.json)，抓起且hold20.10s；[MLP12.94s料盘底碰撞](../../experiments/colab-twin/output/policy-correction-v6-mlp-single-20261001/report.json)，未抓起。全ACT/jaw行使用旧450-admission和1700/1756-forward，分类器/MLP使用前三条guarded；并非同一数据的严格架构消融，不能据此排序架构优劣。

显式`--arm-only-loss`沿官方确定性ACT可微forward，仅非padding前五轴L1参与训练；VAE关闭以免动作标签进入latent，dropout0，兼容显式初始化，与jaw-row-only互斥。ACT全参数可更新，第六轴未经监督，必须组合独立学习夹爪后执行。[损失与配置源码](../../experiments/colab-twin/train_state_policy.py)、[14项CPU反例测试](../../experiments/colab-twin/test_arm_only_training.py)。测试覆盖有限jaw或padding标签变化下loss/完整梯度完全相同、jaw输出行零梯度、前五行非零、fresh Adam、NaN/形状/空有效帧拒绝，以及默认仍官方六轴损失。运行入口拒绝裸`arm5_only`中间权重，组合头加载另验来源和统计。

v7[五轴ACT训练报告](../../experiments/colab-twin/output/policy-correction-v7-arm-fit-20261002/report.json)：12档案、lr1e-5、2721step/120.0169s，allocated87.053MiB/reserved96MiB；继承原四档案归一化和fresh Adam，robot-only mask保留，CPU重载绝对目标差1.11e-7rad。[学习夹爪报告](../../experiments/colab-twin/output/policy-correction-v7-decoupled-fit-20261002/report.json)：6000step/9.8998s，72个基础ACT状态tensor保持不变。相对v6同时改变数据、五轴损失、学习率和夹爪组合，不支持独立因果归因；两训练报告`task_acceptance=not_run`，无held-out验证。

v7同一组合权重SHA `7fef108267cee7ebfc894fddab55f93b1d52b46a547db0f2090f02e476fecfcd`，只改变执行观察窗口的三个单回合都0/1：[chunk16在22.54s腕限位停止](../../experiments/colab-twin/output/policy-correction-v7-decoupled-single-20261002/report.json)，抓起/hold6.06s/未放置；目标1.6579328rad仍限内，实测腕1.6586473rad超过1.65806rad上限。[chunk8在11.82s料盘底碰撞](../../experiments/colab-twin/output/policy-correction-v7-decoupled-chunk8-single-20261002/report.json)，未抓起。[chunk1在90s仿真超时](../../experiments/colab-twin/output/policy-correction-v7-decoupled-chunk1-single-20261002/report.json)，抓起/hold71.88s/未放置，无安全停止。更频繁观察改善某一边界不代表完成任务；尚不据此扩展为泛化或唯一原因。

[冻结旧ACT642f4f并用12条训练独立夹爪的对照](../../experiments/colab-twin/output/policy-correction-v7-frozen-origin-classifier-single-20261002/report.json)，checkpoint `597a807e5e2c75441c9bc871f918151549ce565e72f3f24ee22ff706801fe512`，21s payload_lost，抓起/hold2.66s/未放置。保持旧五轴也失败，不支持把五轴微调称为所有提前丢物的唯一来源。

v8按[固定训练参数](../../experiments/colab-twin/output/policy-correction-v8-arm-training-arguments-20261002.json)从v7 arm SHA `58d8b5a8384f044ff39e04c567ca6e174ff2a0715de762f6f70707c879f03f30`接续13档案、batch64、lr1e-5、五轴L1/120s上限；归一化与robot-only mask保留。[arm训练1504step/120.079s](../../experiments/colab-twin/output/policy-correction-v8-arm-fit-20261002/report.json)，allocated110.629MiB/reserved142MiB，输出SHA `00da58926f51a1408f73f3b5dc4280a895c8ef90de080c21f4a9affef51bdcd5`。[CPU夹爪训练6000step/7.898s](../../experiments/colab-twin/output/policy-correction-v8-decoupled-fit-20261002/report.json)，72个基础ACT tensor保持不变，组合SHA `0007471daee2fcef19b81b157a3f45f80174b997f804fa582d4e0acbfc047a67`。新增数据与batch同时改变，无法独立归因。

[v8 chunk16纯策略回合](../../experiments/colab-twin/output/policy-correction-v8-decoupled-single-20261002/report.json)仍0/1，真实抓起/hold60.42s/未放置。完成89.72s后`place_wall_x_-1`与`collision_gripper_1`间距.8471mm，小于原1mm余量，保护停止。末条有效诊断物体(.20221084,.11643329,.02516980)m进入完整蓝盘XY范围，但仍无盘底支撑、双指接触持续且未松爪；不是成功释放落定。[逐拍诊断](../../experiments/colab-twin/output/policy-correction-v8-decoupled-single-20261002/attempt-000-nominal/diagnostics.json)。

第六条实际执行v8前2500拍后，边界物体z=.045689m、持续持物31.94s、双指1.456/1.457N，无安全停止；蓝盘边缘通道→盘心→降放专家纠正已通过。[采集参数](../../experiments/colab-twin/output/policy-correction-v8-held2500-collection-arguments-20261002.json)与表中报告保留：3242raw/742valid/2500invalid，独立raw64 state/env/time全0。经双通过正式纳入第14条，不把前缀策略命令作为专家标签。没有降低安全阈值或修改任务成功标准。

v9按[14条数据清单](../../experiments/colab-twin/output/policy-correction-v9-training-datasets-20261002.json)和[实际参数](../../experiments/colab-twin/output/policy-correction-v9-arm-training-arguments-20261002.json)从v8 arm `00da58926f51a1408f73f3b5dc4280a895c8ef90de080c21f4a9affef51bdcd5`接续，batch64/lr1e-5/120s上限。[arm实际73step/120.1525s](../../experiments/colab-twin/output/policy-correction-v9-arm-fit-20261002/report.json)，整体405.6682s，wall_time_limit停止，allocated110.629MiB/reserved142MiB；arm SHA `3b2183da2a3a5f3e2103dad9d2fc4d863bb57a4482ab18ce530066fa03aea7ac`。实际4672次抽样/578关键抽样，4166个不同观测/chunk起点占25107个有效起点的16.593%；不是动作标签覆盖。按seed0重建73×64实际抽样，沿[chunk16与间隙/回合守卫](../../experiments/colab-twin/train_state_policy.py)展开得到74384非padding监督动作槽（含重复），目标源帧并集23501/25107=93.603%。新增742帧档案131个不同起点/713目标帧被覆盖。只能确认73步与未遍历全部观测起点，不能推断84%的标签未训练或将失败唯一归因更新不足。

[独立采样重建报告](../../experiments/colab-twin/output/late-recovery-v9-policy-independent-audit-20261002.json)保存上述准确口径及来源哈希；重建抽样与73步训练报告一致，新742帧档案实际141抽样/131不同起点/713目标帧。审核未运行模型训练或物理仿真。

[独立夹爪CPU6000step/9.234s](../../experiments/colab-twin/output/policy-correction-v9-decoupled-fit-20261002/report.json)，764730次抽样/90585关键次/25107不同观测起点，72个ACT tensor保持不变；其采样/步数与arm独立。组合SHA `efb9735d7a90bcf6e428310247bd82cf9cc2431b7c62b82658cddc001c9c3fa1`，[纯策略chunk16](../../experiments/colab-twin/output/policy-correction-v9-decoupled-single-20261002/report.json)27.08s payload_lost，抓起/hold11.22s/未放置，无安全停止，仍0/1。新增专家与回放成功不等于v9通关。

v10按[CPU实际参数](../../experiments/colab-twin/output/policy-correction-v10-arm-training-arguments-20261002.json)保留同14条数据、同ACT/五轴损失、batch64/lr1e-5/120s，仍从v8 arm `00da589...`重新初始化，不继承v9的73步。[CPU arm1201step/120.067s、整体144.551s](../../experiments/colab-twin/output/policy-correction-v10-arm-cpu-fit-20261002/report.json)，实际76729次抽样/9021关键次/23613不同观测起点，保存重载差0，arm SHA `b92adf12f9482467aa927aff1c71e8c94ae2cba6ed878b7743678b52abab57e6`。[独立夹爪CPU6000step/7.3647s](../../experiments/colab-twin/output/policy-correction-v10-decoupled-fit-20261002/report.json)，72个ACT tensor保持不变，组合SHA `cb8f8774f7cb7a67c06a910ebe5684e39ff0b9042070088fcbd1d73b75f06d48`。

[v10纯策略chunk16](../../experiments/colab-twin/output/policy-correction-v10-decoupled-single-20261002/report.json)完成52.20s后盘边保护停止：`place_wall_x_-1`/`collision_gripper_1`距离.936503mm低于原1mm余量，grasp=true/hold25.06s/place=false、0/1，expert_intervention=false。设备替换只为有界资源诊断，v9没有OOM，未换MLP架构；单点频率/利用率不足以证明慢训原因，设备及实际步数/数值变化无法严格归因。这是官方ACT五轴＋学习夹爪组合，不能称“官方完整ACT通关”。

v10失败后的[离线fresh夹爪探针](../../experiments/colab-twin/output/late-recovery-v10-release-cache-probe-20261002.json)在2500/2592/2600/2609拍均输出闭爪，低位蓝盘内状态缺少释放纠正；没有将探针当成线上修复。[最早保存低位准入2517拍](../../experiments/colab-twin/output/late-recovery-v10-release-boundary-selection-20261002.json)重新执行真实前缀后，actual物体(.21463836,.14002259,.01447777)m、当前连续双指接触36.46s、双指1.443/1.444N，无桌面/盘底支撑和安全停止。原held入口要求抬升≥25mm，无法采这种已下降至准备松爪的状态。

新增离线`--mode release`要求此前真实抓起、当前连续双指接触≥1s、完整物体在蓝盘、无支撑、z在[.010,.0145)m且速度≤.05m/s、原安全检查通过；失去接触或得到支撑重置独立接触时钟。首valid动作保持actual五轴q并开爪`.5`，跳过IK/运输，沿原守卫完成盘底承托、撤退与静稳。397有效纠正完成专家抓放/静稳3.76s，2517前缀全部invalid；2914步raw64另行回放差0。离线准入规则没有进入在线策略。[源码](../../experiments/colab-twin/collect_policy_recovery.py)、[边界及端到端反例](../../experiments/colab-twin/test_late_policy_recovery.py)、表中真实采集/回放来源保留。

v11只冻结v10五轴ACT SHA `b92adf12f9482467aa927aff1c71e8c94ae2cba6ed878b7743678b52abab57e6`并重训夹爪；ACT的14档案数据和原四档案输入/动作归一化保持。[15档案夹爪参数](../../experiments/colab-twin/output/policy-correction-v11-release-training-arguments-20261002.json)、[清单](../../experiments/colab-twin/output/policy-correction-v11-training-datasets-20261002.json)及[训练报告](../../experiments/colab-twin/output/policy-correction-v11-release-classifier-fit-20261002/report.json)：CPU6000step/7.1017s、整体9.9502s，72个ACT tensor不变，夹爪额外统计只fit15份合格行；组合SHA `f50a14052b48ad1237024a63cebddec032686441be1149c33e4c8bc5d071a007`。未继续重训五轴120s。

[v11纯策略chunk16](../../experiments/colab-twin/output/policy-correction-v11-release-single-20261002/report.json)1/1通过，1988周期/39.76s、hold23.10s、放置/静稳1s、无安全停止，expert_intervention=false；只读state/env，不调用IK/OMPL/阶段/时钟接管。固定nearest只把学习分类器的`.0150000114/.5000000092`浮点值投影到专家训练支持`.015/.5`，最大约1.15e-8rad量级，不按几何决定开闭。它是官方ACT五轴＋独立学习夹爪＋固定适配器的状态策略闭环，只验固定训练初态；新增标签和重训同时发生，不能据1/1证明标签是唯一因果。20+20/视觉not_run，未新增云端/实体或恢复成功率，所有失败保留。

此前[201项/55.101s](../../experiments/colab-twin/output/late-recovery-v7-final-tests-20261002.log)与[8档案绑定](../../experiments/colab-twin/output/late-recovery-v7-final-test-arguments-20261002.json)保留为历史，彼时12训练集另[独立审核](../../experiments/colab-twin/output/late-recovery-v7-independent-audit-20261002.json)，后续14总集另[数据审核](../../experiments/colab-twin/output/late-recovery-v9-data-audit-20261002.json)。release源码更新后的[212项/41.991s全测](../../experiments/colab-twin/output/late-recovery-v11-final-test-result-20261002.json)实际exit0/0 skips，源码前后哈希一致；[本次artifact参数](../../experiments/colab-twin/output/late-recovery-v11-final-test-arguments-20261002.json)绑定11份（四v5＋七guarded）及release2517回放，四份v4不在这11份artifact绑定内，不能把测试绑定扩大成15份。测试不替代物理单回合或泛化验收。本轮助手是Codex，未重新调用AGY；实际AGY来源和采用边界保持[原审核记录](learning-review.md)。

[v11独立Codex审计](../../experiments/colab-twin/output/late-recovery-v11-independent-audit-20261002.json)39项全true，SHA `24e341d401479ad57c39a5b2a13609738ca70247b2e3d5dac02d315402f8f565`。只读重算最终真实物体蓝盘范围/盘底承托/松爪/1s静稳，结果与报告一致；72个ACT tensor逐项相等，arm14/head15及原四归一化/15份夹爪统计误差0；prefixNaN/回放差0及212项11档案绑定一致。审核未重跑训练、推理或物理。物体最终(.21228807,.13849017,.00992145)m、双指力0、盘底支撑真实，安全和任务标准保持。

[同初态可见纯策略复跑](../../experiments/colab-twin/output/policy-correction-v11-release-visible-20261002/render-binding.json)通过，checkpoint仍f50a1405…，9个NPZ字段数组/全部diagnostics与首次逐项完全相同，渲染不修改物理状态；[995帧视频](../../experiments/colab-twin/output/policy-correction-v11-release-visible-20261002/attempt-000-nominal/pure-policy-grab-place.mp4)只作本机可见复验，不合并计算20+20或泛化成功率。


## 2026-10-02 v11 40轮批次的范围与失效解释

[v11批次report](../../experiments/colab-twin/output/policy-correction-v11-batch-20261002/report.json)实际为20/20正常、3/20扰动、20次扰动全部10拍；安全5、超时8、失物4。正常组全部NPZ数组相同，seed不影响reset，故这是单一训练初态重复性，不是20个独立场景。扰动是固定时间实际3.02s的五轴控制目标偏移，幅度各≤0.02rad持续0.2s，不能表述为大范围任意外力或连续吸引域已证明。

[命令/物理只读核对](../../experiments/colab-twin/output/v11-batch-lost-object-claim-check-20261002.json)发现22/24/36先在盘外高位学习开爪，37抓起后始终闭爪：四个payload_lost应分开检查，不作统一偏心夹持归因。21超时终点仍全物体盘内false、z42.09mm，没有几何开爪门控。28/29/34/35为pick_floor/活动爪1mm余量保护，33为蓝盘y负侧壁/夹爪余量保护，并非已证明发生实接触碰撞。各轮wall_s合计309.869s。

优先数据候选为脉冲后的前接触恢复，以及真实持物尚未失触前的继续闭爪纠正；仍须完整专家成功/raw64回放后才学习。若使用本批失败补标签，该批成为已见诊断集，另留新种子验收，保留固定正常回归。这个后续方案只记录为建议，未采集/微调/重评；当前S7d未通过、视觉未启动。原single/212测试证据保持其范围，本次文档核验没有重跑训练、physics或测试。

[独立审计](../../experiments/colab-twin/output/v11-batch-independent-audit-20261002.json)确认16汇总和40逐轮检查全部一致；96041次command中96036步完成进入NPZ，5条失败command仍保存在外层attempt。不能用最后正常snapshot覆盖安全停止。


## 2026-10-02 T1 三条持物纠正与冻结夹爪探针

实际补seed22/24/36开爪前的held专家完整纠正，新3359valid/3808invalid；各独立raw64差0，合并18份44897raw/28863valid/16034invalid。只用专家成功和真实回放双通过档案，原失败policy prefix全invalid，未手填闭爪后冒充成功。

冻结v10 arm72个状态tensor与原四归一化，18份数据仅重训8608参数夹爪，CPU6000step8.200s。新候选f2f87fac…已见22/24/36完整抓放0/3：22盘外高位开爪提前到17.94s、18.12s失物；24/36抓起后没有开爪命令，但分别蓝盘壁保护停止/高位闭爪超时。seed0仅1/1正常通过48.40s，比v11慢8.64s。两轮没有误开≠两轮恢复成功；高训练集准确率≠物理成功。详见[实际数据、参数、四轮报告与时序](progress.md#2026-10-02-t1-持物防误开爪执行完成候选未晋级)。

v12不替代v11，不混算不同权重成功率。五轴权重相同仍可能因夹爪接触反馈出现不同轨迹；本轮额外数据、夹爪统计和重训同时改变，不能将seed22的退化归为唯一因素。三档数据本身成功可保留，整策略候选仍未晋级。新增3artifact tests通过，旧212未重跑；独立审核均Codex。Seeds40..59未使用，T2/T3/T4与S7e未运行；最短owner根Codex先检查已见接近/放置状态覆盖再有界接续。


## 2026-10-02 最后一次A的止损与视觉输入边界

三条专家纠正与raw64重放通过不等于新arm策略通过。v13合格行32480、唯一1262step/120.0608s arm训练后，固定正常回合仍90s超时；无安全停止但未放置，因此首个失败即结束A，四个后续已见扰动及留出40..59均不跑。独立92项审计只核对来源/过滤/训练/旧head保留与实际失败，不能将数据或测试成功替代任务成功。精确产物见[progress](progress.md#2026-10-02-最后一次a完成首次正常探针失败按用户决定转b)。

视觉策略采用state6＋固定相机RGB，env30仅留在原HDF和物理判据中。每张RGB与obs_t同拍、动作之前渲染，2350帧原始动作再执行与raw64全部严格一致，避免接触后画面为前一动作提供未来信息。128×128固定视野同时覆盖两盘与障碍，目标较小；首轮只验证数据与资源，不假定视觉能够自然恢复偏差。[ACT原论文](https://arxiv.org/abs/2304.13705)研究视觉模仿和动作chunking，也指出误差累积；其结果不提供本SO101场景的成功率保证。


B实际显示资源与能力不同：随机小视觉ACT在4GB卡batch8只需峰值332MiB，3438step/120.016s与同CPU重载完全一致，但物体没抬起，64.74s盘壁余量保护停止。9帧专家训练态teacher-force jaw全对/arm MAE较小仍不等实际闭环成功；离线固定输入结果也不证明利用了图像。下一步先检查起步/接触偏差及RGB作用，而非把显存不足当失败解释或立刻盲目长训。232项测试成功仅为代码/绑定数据边界；完整物理门槛依旧未过。来源为progress末节与本轮汇总。


## 2026-10-02 B离线诊断：有RGB响应，未证明物体定位

- 冻结B首次闭爪33.00s，专家11.02s；同拍IK参考点－物体XY差4.4937mm对0.00607mm。B固定指法向峰值27.3059N、活动指全程0、双指夹持0帧，物体未抬升；jaw实际<0.1rad时35.48s、参考点世界Z33.8578mm。成功专家持物实际jaw约0.116rad，因此“合到0.015”不是物理成功判据。对准、合拢与抬升配合比“到了蓝盘”更有诊断价值；不能表述为零接触夹空或抓后滑脱。
- PINCH_POINT只是专家IK参考点；FK计算几何，接触力来自保存的真实同拍物理记录。未保存物体姿态、接触点/法向，单指接触伴随向下位移不能证明唯一物理或视觉因果。
- 固定q6直算chunk，12专家＋12实际稀疏帧、96替图比较：专家550/551/567黑图使闭→开，实际12帧各替图未出现jaw类别翻转，但部分整chunk五轴变化可达平均0.012068rad。模型在所测状态有RGB响应，不等于看到了方块或形成了纠偏；黑/灰/噪声分布外、异时刻图与q矛盾，不能当对象定位实验。9个真实刷新帧与旧CUDA首动作基本一致，非刷新帧新chunk不能冒充原执行命令。
- 原21成功档案52335raw/32480valid/19855invalid，parser准入一致；初始物体XYZ全同，held/release大量标签在抓起后，不能以档案数称多场景或抓前恢复覆盖。建议仅4档案8797valid的小批RGB候选，先起步/接近/下潜；新3份仍需RGB同步＋严格raw64回放准入。当前B失败状态是否被覆盖尚未知，未导出/训练。

方法参考[ACT原论文](https://arxiv.org/abs/2304.13705)与[离线机器人示范学习评估研究](https://arxiv.org/abs/2108.03298)，实际证据/时序/候选路径和局限见[本轮progress](progress.md#2026-10-02-b只读几何与rgb依赖诊断完成)。沿用知识页“按当前任务选择验收依据”，分开输入敏感性、数据准入、学习任务门槛；没有新物理rollout/训练/云端/实体/留出40..59，B仍0/1。


## 2026-10-03 四RGB档案重训后仍无指尖接触

- 三新增RGB与各独立raw64回放双通过，合旧nominal9458raw/8797valid/661invalid；nominal2350valid，严格接触前只1979valid（占22.50%，约nominal3倍），不把全部标签或档案数当接触前独立覆盖。新HDF/无效标签/相机与obs_t同步均精确，源Python52份未变。
- 当前入口原生支持多档案，chunk保留episode/frame边界；旧single数据资源不能复用。新batch8/5反传332MiB通过，唯一随机初始化训练1312step/120.045s优化，CPU保存重载严格0；不是从旧B微调。原fit诊断文字single train episode不准确，本次四份均训练、无独立留出，公开说明实际范围，不改源码放宽绑定。
- 新纯视觉0/1：4500拍/90s超时，双pad力全0、物体Z恒定9.92145mm、无抓起/持物/放置，无安全停止。closed67.20s、动作前IK参考XY19.9447mm，低位未对准；70.10s离线上升时仍无双指。旧B33s/4.49mm/单固定指接触与新轮不能混叙。20ms离线保存而非2ms力轨迹，力N而非力矩，时间/升高/连续双指阈值仅作诊断，不进入策略。
- 旧RGB响应探针只绑定cd298权重；新d4db模型未重测，不宣称对象定位。两轮数据/normalization/抽样步数共同变化，不是单因素消融，也不能唯一归因退化或用minibatch loss判定单回合已过拟合。新失败不能以延长预算/放宽保护/强制11–13s闭爪掩盖。

[实际层级证据及完整几何表](progress.md#2026-10-03-b四档案rgb闭环执行完成纯视觉抓放仍未通过)。本轮停止追加训练，下一建议先离线核固定观测拟合误差和相近观测标签冲突，再择一项有界改变；建议尚未执行。保留v11正常20/20与扰动3/20，S7d/S7e整体未通过，全部runtime继续Git忽略。

## 2026-10-03 固定专家观测的拟合与监督一致性

- 新d4db权重全8797起点、旧cd298原2350起点直接q6/RGB预测；模型/缓冲/52源码及输入哈希未变。专家动作仅作误差标签，noVAE零latent，不是teacher forcing。官方骨干使用FrozenBatchNorm2d，不支持普通BN训练/推理统计漂移假设；实际normalized masked L1最优统计量是逐维中位数，不能直接断言动作平均或随机特征数学上不可能学习。
- 采样准确重建为10493次chunk起点/8797=1.192793遍（末batch5），旧27482/2350=11.694468遍。重叠未来标签另计，帧数与epoch不是独立覆盖或欠拟合严重度证明；固定专家观测重构不是留出/任务验收。
- 同nominal全chunk五轴MAE旧1.7765/新6.3828mrad；严格接触前旧2.6722/新11.2131mrad。新第1拍0.5665、第16拍25.9349mrad；在专家目标位移范数≥.001rad的同nominal观测上，目标方向投影比例中位第1拍.9632、第16拍.2002（旧.9898/.6929），是目标命令统计而非实际执行速度/因果定论。
- 四档案首次闭爪至首次接触436观测全部预测closed；nominal离线首预测10.74s、专家11.02s，并非线上67.20s。低位539帧包含432closed，全部命中，但107open中56提前预测closed；分类正确不保证真实夹持。用户30–80mm窗口384帧全open，漏掉专家19.8mm首次闭爪点。接触/阶段真值仅供切片，不输入策略。
- 跨档Z0–80mm/XY≤40mm923帧；q6 L∞≤.002rad、全RGB MAE≤.5/255下1270相关近邻/880不同源帧。648closed近邻当拍/未来jaw均无分歧，五轴delta cos最低.9808；主差异集中v6 approach/descend交界，不支持普遍多模态冲突。全图相似可掩盖局部差别；最大8×8图块MAE≤2/255后975对无负cos。没有完全相同q6/RGB输入，不能由近邻比较证明全数据无冲突。
- 搬运有效帧占53.2%；全部有效future标签token占53.382%，冻结模型normalized L1误差总量占46.388%，接近占34.080%。这些都不是训练梯度归因。暂无依据直接给全部接触前5倍权重。

最小候选为复用现有`--execute-chunk-steps`，同冻结权重只改16→1，优先检验后部chunk误差影响；该参数同时改变执行窗口、观测与残差锚点节拍，最多增加16倍forward次数，不能孤立归因为视觉或保证h0偏离专家观测后有效。候选未执行，本轮训练/物理/渲染0，原B0/1与S7d/S7e失败状态保留；来源见[完整离线记录](progress.md#2026-10-03-b四档案离线拟合与监督一致性诊断完成)。

## 2026-10-03 chunk1首先暴露运行时间门槛

- 唯一同权重/同初态物理复验被原wall_time_limit截断：250完整20ms转移=5.00s仿真；原evaluate总120.500s，wrapper含保存120.595s，外层进程123.699s，actual exit1。上限仍在原step间检查，启动/最后一拍/保存使记录可略超过120s，未扩大预算。
- 250次预测回调累计98.883s、中位402.075ms/P95 475.068ms、最小234.521ms；250/250超过20ms。它包括归一化、设备传输、模型forward、输出回CPU/解码与jaw投影，排除EGL渲染和物理步；不能将其称纯GPU kernel时间。当前配置不能支持此前的实时50Hz预期。
- 权重d4db、52源码、reference/raw、相机/派生XML/初态不变，第1拍raw/action/q6/time与旧chunk16逐位一致。没有额外推理或线程调整；首拍后变化正是新观测/重锚点执行的结果，不用专家h0误差保证离流形表现。
- 本次尚未闭爪或产生保存的双指接触力，grasp/hold/place均未发生，无安全停止；不是“已走完但未抓起”。原任务未通过，chunk尾部是否主因及视觉表征是否不足都未被本次短前缀裁决。
- Torchallocated74.934/reserved102MiB仅是allocator峰值；不能代表全卡占用。事后新进程线程/GPU状态只作现状快照，未记录回合内历史，不能确证降频、线程或争用根因。

采用既有“按当前任务选择验收依据”：运行成本、模型输出与物理抓放分别记。37项轨迹和148项计时独立核验不代替抓放通过；[实际来源与局限](progress.md#2026-10-03-b冻结权重chunk1单回合复验因墙钟上限截断)。下一候选先拆分运行耗时，尚未执行；无重训/第二回合/云端/实体/留出，安全和S7d/S7e状态保持。

## 2026-10-03 热态离线调用未复现仿真持续慢回调

- 当前入口已用no_grad，不能当作尚未关闭反传。唯一profile共29前向，首冷400.374ms，12次后续原调用median8.229ms/P95 9.276ms；12仪表median7.073ms，raw/投影动作差0。当前默认线程8/8，也不足以支持“八线程必然导致402ms”。
- 主机分段median：state归一化0.014ms、RGB CPU重排0.025ms、RGB转换/H2D/255共0.117ms、policy forward6.454ms、finite检查含等待0.106ms、D2H/numpy含等待0.042ms、解码0.048ms。当前热态不存在持久百毫秒回传或格式开销；首冷未分段，不能把它指定到某一层。
- 同流CUDA Event的forward跨度6.473ms，包含骨干2.927ms/encoder0.971ms/decoder1.461ms及其余工作/投递间隙；不是纯kernel时间，不得将总段与子段相加。仪表尾部同步median0.023ms另列；原先/仪表后顺序和record/hook/lazy初始化会影响时序，仪表更快不是优化证据。
- operator profiler另占一次原前向，host16.464ms，不属于12次baseline；trace包含真实CUDA kernel，不能当CPU fallback。CPU operator inclusive time、operator GPU归因与leaf kernel会重叠，不能混合求和。
- 前轮250慢回调均>20ms，本轮仅首cold约400ms，不能以“冷启动”解释全部历史；本轮GPU P3/645MHz→P0/1500MHz仅组间快照，没有反事实或旧历史，不能证明频率是根因。离线无EGL/渲染/物理，优先检查运行路径差异，仍待实证。
- 旧chunk16是4500 runner/282 forward，总27.41s，forward平均的全包上界97.20ms，不可能全部恒定400ms；旧逐次median未记录。当前整体慢放120.50/5=24.10倍，400/20仅callback近似。chunk4预算须包括渲染/物理/加载等；300wall粗算12.45sim、15sim粗算361.5wall，均非实测且原CLI禁止wall>120。

方法依据[PyTorch2.7异步语义](https://docs.pytorch.org/docs/2.7/notes/cuda.html#asynchronous-execution)与[CUDA Event](https://docs.pytorch.org/docs/2.7/generated/torch.cuda.Event.html)，实际来源见[运行耗时记录](progress.md#2026-10-03-b离线耗时拆分热态原调用约8ms原仿真慢因仍未知)。沿用既有Wiki按任务选择验收范围，不将热态predict<20ms扩大为EGL完整环50Hz或抓放通过；无新训练、物理、渲染、云端或实体。

## 2026-10-03 静态同输入EGL路径未触发历史慢调用

- 唯一静态A-B-A：同q6/RGB/d4db/batch1/float32/no_grad/default backend/线程8/8，4cold-warm+A8+B8+A8，共28forward。B采用实际mujoco.egl.GLContext，原capture后立即原predict，不夹CUDA Event/getter/sync/status；输入仍冻结RGB，渲染仅作路径变量与证据。
- 原predict中位A6.4847/B6.8334/A-close6.4120ms；B渲染中位1.1119ms，两段中位7.9350ms、最大15.1634ms。首冷377.1950ms和初次render8.1631ms单列，不能解释历史全部250次慢回调；组序、热态和系统负载仍混杂，不由小幅差异定因果。
- 原rawHDF完整初态直接装入旧contactXML，仅一次mj_forward不积分；原primary和warmstart此次也逐位未变。8render/close后的9状态字段差0，8画面与存档RGB差0，28raw/投影动作及旧首拍差0；独立275项数组核验通过，原52源码/模型/输入SHA不变。
- 显式renderer.close释放GL/Mjr context，但全局EGL display可保留；A-close不是全新进程或GPU复位。静态路径未复现持续402ms，不能证明真实循环无EGL影响，也不能锁定context、功耗、线程或调度根因。

[mj_forward官方说明](https://mujoco.readthedocs.io/en/3.3.7/APIreference/APIfunctions.html#mj-forward)与[MuJoCo3.3.7渲染文档](https://mujoco.readthedocs.io/en/3.3.7/python.html#rendering)支持静态设置边界；[实际记录](progress.md#2026-10-03-b同输入egl与cuda静态对照未复现持续慢调用)区分预测、静态渲染和完整物理闭环。没有训练/精度修改/积分/抓放回合；完整50Hz、chunk1抓放和历史慢因仍待验证。

## 2026-10-03 同轨迹真实短循环热态未持续慢

- 唯一原evaluate前缀100拍/2sim，100次实际推理、1000执行积分、201observe和301mj_forward；后者由reset1加每拍2执行刷新与1独立checker刷新组成。前100状态/动作/时间、100条物理诊断与旧chunk1逐位一致，两个派生XML一致；本次运行仍没有持续复现旧402ms。
- 全100完整周期中位11.757ms，1/100超过20ms且就是首拍342.899ms（预测326.779ms）。后99周期中位11.742/P95 12.919/最大14.142ms，0/99超过20ms；不能省去首冷后声称全部100拍过20ms门槛。
- step中位3.717ms含10次mj_step合计.483ms、两次observe合计.576ms和diagnostics1.488ms；诊断内checker1.183ms已包含，不能重复加总。step余项含原验证、接触守卫及插桩CPU开销；285是checker配置pairs数，没有逐距离额外打点。
- monitor中位.0044ms，整拍减四顶层段残余中位.0590ms；该残余包括原记账、函数包装与调度，不能全部称OS等待。原循环无sleep或节拍deadline调度，仿真时间推进20ms不意味着真实50Hz。
- 初始化至首while约3.320s，100周期合计1.511s，结束tail约.0617s，原main共4.893s；outer7.386s还含解释器启动与诊断汇总。原task保持simulation_time_limit/exit1，计时诊断完成exit0；仅接触前2sim，未重新评价抓放或长期实时能力。

方法沿用既有Wiki按当前任务选择验收依据；[本机原区间和独立审计](progress.md#2026-10-03-b真实循环100拍计时热态短前缀低于20ms历史慢因仍未知)保存全部冷/热数据，172模型张量及52源码不变。原持续慢因仍未知；本次短循环快不能追认旧运行状态，也不能证明接触、持物、落盘阶段的20ms预算。


## 2026-10-03 chunk1快速回路仍未完成抓放

- 原wall120/sim90单次回合580次指令、5800积分，579保存行elapsed11.58s；第580次step的10次积分完整发生，terminal elapsed11.60s/absolute12.60s，因wrist_flex实测限位而没有返回新行/monitor。原task和外层exit1，外层13.599s，未墙钟截断。
- wrist_flex实测1.6581003327062775rad，原joint upper1.6580627293335335rad，越界3.7603372744e-5rad（0.002154515°）；下发1.6579903239325227rad在原ctrl upper1.65806以内。checker先用实测q做严格无容差范围检查，joint_limit返回distance/pair=null；不据此认定盘壁碰撞或精度/宿主机根因。
- 所有580命令夹爪都为open0.5；579完整诊断的双指法向力均0，物体z约9.92145mm，重算grasp/place/hold均0。末拍接触力未保存，不把已保存诊断扩展为全部580拍。原monitor safety=false仅覆盖已返回579拍，外层safety=true来自第580次step异常，二者范围不同。
- 后578完整周期中位11.336/P95 13.063/最大15.873ms，0拍超过20ms；首cycle402.449ms/predict391.684ms保留。末次异常尝试9.936ms单列，未混入完整周期。原自由运行无节拍等待，未进入抓取接触/持物/落盘，不能宣称完整50Hz。
- 独立173项物理和93项计时审计通过，旧250状态/动作/时间/diagnostic相同、前100逐拍RGB/q6/raw/action差0。每拍刷新h0未使当前冻结策略通过，专家观测上的h0误差与闭环rollout是不同证据；后槽退化不能解释本次全部瓶颈。

[本轮原报告与审计](progress.md#2026-10-03-b冻结chunk1完整回合关节限位安全停止抓放未通过)保存准确时间口径与终端证据。下个候选只读核接近段五轴/专家偏差及限位余量，尚未执行；不以本次小越界授权放宽限位、重训或重跑，历史持续慢原因仍未知。

### 2026-10-03 起步诊断与采样索引语义

- 接续只读核验已完成：前3秒策略并非主关节静止；同初始q下，首拍肩平转、肘部、腕旋方向已与专家不同。腕部先降后升，2.52s起目标残差连续转正。不能唯一归因动力学，也不把近限位单轴训练范围外等同完整RGB/state OOD。
- 四档初态q6相同，但前50原始帧只有nominal50条有效监督；其余first-valid原始帧为50/450/161，均已处于纠正接续。加载器保留 `frame_index[label_valid]`，不能用过滤后的行号或每档first50valid定义共同起步。
- 按冻结seed/source重建，8797个合法chunk起点均至少见过一次，nominal第0帧作为输入一次，前50帧共61次。不是GPU采样日志；随机均匀排列没有起步优先权，不能由重建次数证明唯一失败因果。
- 保存的q6距初态≤0.01rad的366条有效观测包含approach2、retreat64、settle300；nominal首末模型h0残差最大轴差0.486892µrad，专家差4.851291mrad。两帧q6/RGB不同，不能称同输入消融或确定视觉根因。来源为[冻结预测/目标数组](../../experiments/colab-twin/output/vision-b-offline-fit-20261003/four_episode-predictions.npz)和同步HDF。
- 用户明确选择原始帧<50的有效chunk起点5倍。本次扩展的是索引池，不复制HDF、不重新加权归一化、不乘损失或引入阶段输入。8997项完整池具有5:1次数；被预算截断的实际次数另记，采样份额不等于梯度份额。
- 新采样实现保留原视觉源码绑定。旧资源报告在新版被实际拒绝，旧checkpoint拒绝回归通过；旧d4db使用提交4a1cf3b的源码，新训练需重新通过绑定新源码的资源探针。本次16项[真实索引审计](../../experiments/colab-twin/output/vision-startup-sampling-20261003/report.json)及25项CPU回归只证明采样实现，未验收学习抓放效果。

### 2026-10-04 起步5倍训练后的局部与整体误差

- 新源码资源5step/batch8的reserved峰值332MiB，唯一fit3126step/120.002s；旧fit1312step/120.045s。相同墙钟和配置不保证相同步数，不能把新旧预测差当作等步数纯采样消融。
- sampler实际25002次起点、702次起步、两个完整8997池；CPU重构计数与报告相等，nominal frame0见13次，8797唯一行全见过。次数增加既含权重又含实际更新数变化。
- 新专家观测h0前150拍逐轴MAE全部改善，五轴均值0.638→0.346mrad；首10向专家投影0.179→0.749，但首帧投影0.115→0.031，pan/wrist_flex/wrist_roll反向。整体拟合改善不保证关键初态方向被修复。
- 首10拍同向率90%/100%/100%/80%/90%，前3秒平均掩盖少数起步错误。本轮保守0.5–1.5方向/幅度门槛在新模型预测前写入，不是历史物理验收标准。
- 离线仅150次batch1/no_grad CUDA前向，0优化/渲染/积分，172模型张量及源/输入不变；旧对照是保存的batch8/inference_mode数组，数值路径不同，不加载旧模型或认定视觉/动力学唯一因果。
- 门控未过，新抓放not_run；下一候选只读核首0–9拍与起点附近收尾样本的q6/RGB/专家标签，不能由当前证据直接决定增权重、改delta或放宽安全界限。[原结果与接续](progress.md#2026-10-04-起步5倍采样唯一训练离线方向门控未通过)。

### 2026-10-04 固定q6起步收尾RGB的局部响应

后续逐层响应已实际检查：backbone/图像投影的同层relative L2分别3.5773%/3.5952%，4×4空间cell最大7.8686%/7.9669%；encoder图像位置输出0.9982%、decoder h0 0.05974%、归一化五轴h0动作头0.9819%。这些分母、尺度及投影不同，不能作跨层因果损失率；主干非零响应不等于语义可分。q/latent输入和position固定，encoder q输出0.4942%的图像响应不属于q6输入变化。12原前向（8hook+4无hook）全部与保存输出逐位相同，8hook同图激活差0；53源码/6输入/172模型张量保持，无训练或物理。来源见[逐层原始记录](progress.md#2026-10-04-冻结模型逐层视觉响应探针)。

结合首帧近q有效邻居的2 approach/64 retreat/300 settle及chunk起点访问27/178/834，下一单变量候选选真实起步/收尾近q帧局部配对均衡，先检验监督竞争。该分布不是完整标签曝光或梯度份额，不能证明失效唯一原因；候选未实施，不由两个图像的数值差直接替换主干或增加视觉训练预算。

- 当前8d4db模型，固定nominal frame0 q6，整幅RGB在同相机frame0/2349间交替；6对共12次原runner batch1 CUDA/no_grad/float32前向，每次reset/execute1，无新增训练/渲染/积分。来源见[冻结协议与原始数组](progress.md#2026-10-04-固定q6起步收尾rgb反事实检查)。
- 同图全chunk重复误差0，起步图与前次保存的同模型/同输入首帧预测差0。h0五轴差L2 3.95995µrad、最大轴3.22753µrad；两个参考专家目标相距6.000mrad，图像效应仅其0.065999%。不能把非零响应等同正确任务辨别。
- 两图均输出pan负、flex正、roll正，仍与起步专家相反；raw jaw差89.69µrad，训练支持投影均open0.5。两图预测绝对目标距起步标签约6.039mrad、距收尾标签约0.414mrad，局部仍倾向收尾动作。
- 这隔离了本轮q6输入/解码锚点变化和同输入推理波动，但换的是全部RGB差异（含物体、细微机械臂像素），不隔离某个物体区域或特征层。反事实q0+收尾RGB与真实收尾q不同，不充当专家可执行新标签。
- 53份顶层Python、5份源输入与172模型张量保持；仪表路径有额外输入CPU拷贝，计时不当作50Hz证据。当前只支持局部图像辨别不足候选，不确认全局视盲、唯一根因、动力学或抓放结果。

### 2026-10-04 首两拍与收尾相近观测

- 首10专家标签轴序、符号、valid和同拍时序一致；保存h0目标等于raw action（差0）。按q_t重算lookahead目标误差6.94e-18rad，改用next_q重算差6.510mrad。next_q_t等于下一行q，首帧absolute1.00s/elapsed0，控制20ms/物理2ms。它支持档案语义一致，未新重放或渲染证明像素生成。
- 三条恢复档raw0–9均invalid，没有进入有效起步监督；首valid为50/450/161。新模型在专家frame0 pan/flex/roll、frame1 flex反向，frame2–9五轴全同向；不能外推实际策略会在0.04s自动恢复。
- frame0 q6半径0.01rad的366条有效邻居为2approach/64retreat/300settle，对应chunk起点访问27/178/834。chunk尾部标签曝光另有来源，起点访问次数不等于完整监督或梯度权重。
- frame2349与frame0 q6差0.137mrad L2；工件位置相差269.17mm，两图203像素不同。变化像素MAE23.31而全图MAE0.289，背景稀释不等于模型特征相同。
- frame0五轴预测绝对目标距起步rawlabel6.039mrad、距frame2349 settle rawlabel0.414mrad；统一起点锚比较等价。输出偏近收尾是描述性证据，局部辨别/监督竞争仍只是候选。
- 首10未发现完全相同raw q6＋RGB或float32归一化q6＋RGB但标签不同的行。0新前向/优化/GL/物理，53源和所有输入不变；不据此排除近似观测的表征问题。详见[本轮报告](progress.md#2026-10-04-首09拍观测与动作标签只读核验)。

## 2026-10-06 真实近q局部1比1采样已实施，原离线方向门控未过

局部1:1采样已接入并完成唯一有界训练：同四档、原归一化/模型/损失，2115step/120.033s，峰值332MiB、保存重载误差0。首帧pan/flex/roll改为同向，但elbow反向且首10拍全反向，原离线门控未过；固定q换图h0差仍仅4.429µrad。没有物理回合或补训，S7e仍未通过。

原池局部质量10/300改155/155但总8997/组外槽不变；按完整池chunk起点均衡，不能称有效动作槽或梯度严格1:1。本轮实际2115步少于旧3126步，预置快照未到达；数据抽样之外的优化步数差异限制因果推断，不以首帧部分轴修正宣称视觉辨别成功。first150 elbow MAE1.090709mrad，原gate基线0.606118；7项gate有5项未过，停止物理。

root保留默认均匀与原startup5行为；新局部均衡需显式 `fit --startup-weight 5 --local-balance`。本轮结果不支持仅靠局部起点均衡已解决起步/收尾辨别，且实际步数不同于旧3126，不能作等步数单变量因果结论。下一最短候选为只读核肘轴前150拍的逐槽拟合与局部抽样覆盖，区分早期输出偏差和覆盖变化；尚未执行，不自动追加训练、改主干或启动物理。 [范围与原始报告](progress.md#2026-10-06-真实近q局部1比1采样已实施原离线方向门控未过)。


## 2026-10-06 startup5等2115步对照完成，原离线门控仍未通过

- 只读肘轴审计排除完全漏采与近q有效槽肘标签正负竞争；起点曝光不能代替future目标曝光或梯度。
- 唯一新A采用原startup5、不启用local-balance，从头训练2115步/119.205s优化，峰值332MiB、重载误差0；复用原B的2115步权重。A前150条专家观测肘轴h0同向率100%、MAE0.206395mrad，B为40%/1.090709mrad；B其余四轴h0 MAE更小。A首帧肘幅仅专家0.686%，原7项门控仍有3项失败，未进入物理回合。
- A首10拍肘/腕旋投影0.380/0.472，前150腕俯仰MAE0.908849mrad劣于原d4db的0.849739；方向正确不等于幅度达标。
- 等步数比较已完成，已消除旧3126与2115步数不一致这一项混杂；单seed加历史B仍不足以证明唯一因果或采样普遍优劣。前置肘轴逐槽/覆盖只读审计也已完成：不是完全漏采，近q邻域未发现肘轴正负标签竞争。root保留两份失败模型与原阈值；接续应据五轴逐槽误差选择下一项最小验证，尚未决定或执行新的训练。S7e仍未通过，本轮止于离线，不补训B3126、不改安全界限。

[协议、原数组、逐槽对照与646项独立复核](progress.md#2026-10-06-startup5等2115步对照完成原离线门控仍未通过)。54份Python源码（含测试）不变，输出继续忽略；不以诊断完成追认S7e或物理通过。
