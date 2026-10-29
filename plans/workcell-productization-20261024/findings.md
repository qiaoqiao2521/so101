# SO101 工位产品化：事实、决定与待证项

## 2026-10-29 补充：释放规划进程传递已同输入核实

[R149](m1b-process-isolation-results.md#r149原释放请求捕获与六次同输入规划完成)补齐原生模型和实际请求。原物理pass，Thread/spawn三对六例Snapshot／两路径／205样本逐位一致，实际report_json也相同。独立进程准备约1.51～1.54s，完整Plan约241KB、父端解码2.12～4.67ms，整组件总耗时反增。不能因进程边界可行就称50Hz改善；下一步仅separation的真实释放主循环A/B，运输保持原线程，所有当前q／ratchet准入保留。

## 2026-10-29 补充：运输进程隔离的实测边界

[R147／R148](m1b-process-isolation-results.md)同代码在X224／X256反序原物理4/4通过。hold超20ms分别47→1、71→14；全回合99→48、125→57。运输段控制长尾改善可复现，但总wall左近似持平、右增加1.646s，CPU增加；不能写成整程加速。release／闭爪／切换及RGB仍有慢拍，完整50Hz未通过。当前计时是计算预算，不是按绝对时钟调度的deadline计数。

下一separation候选必须捕获实际Snapshot与冻结估计模型：原request更新geom_pos／geom_quat／geom_sameframe，原worker还核size／uncertainty；主guard逐拍更新ratchet。不用相邻轨迹帧或真值补输入，不先跳过认证再称解耦。

日期：2026-10-24。本文保留初建核查及后续实施事实，作为产品化计划的证据入口。
初建D0仅编写计划；后续源码、服务和云仿真实测见各节及progress.md，不将初建状态当作当前整体状态。Mint与实体设备始终不在实施范围。

后续实施以progress和以下更新为准；上句仅描述D0初建。

## 2026-10-29：R146进程隔离组件

原96条真实guard／原运输planner三对反序，输出及路径逐位一致；主线程慢拍39／15／7→0／0／0。实际模型／Snapshot／Plan可原生传递，但约67MB模型与spawn初始化增加总成本，三对整案例wall都更长。只支持把重初始化放在激活前、保留原任务生命周期的transport-only物理候选，不证明完整50Hz或整体提速。[详细成本与限制](m1b-process-isolation-results.md)。旧1ms时间片、GC等淘汰记录保持，不重复这些试验。

## 2026-10-29：统一X配方与完整周期的新证据

R142同初态九个预声明X观测点显示，60mm/.5在X256mm仍原IK失败，54mm/.35九点原IK／完整扫掠均过。R144直接原评测完成左224、中心240、交界252的统一54mm工艺，另252原60mm对照4/4pass；右256沿同源R143无等待基准也pass。[原结果](m1a-x-unified-recipe-results.md)保留真实RGB、静态观察Y与物理reset输入的区别。

复用已有父坐标系与右工艺，新增单一[连续编辑开发配方](../../experiments/colab-twin/scenarios/workspace-station/fixed-tray-x-editable.json)。建议X224～256mm，逐请求视觉与原IK／285对／1mm／244或246全扫；不是点白名单，也不声明所有连续位置必成功。没有切默认或增加新执行器。

R143四个原物理pass补齐开爪等待0.6s数据，最大漂移左6.142e-8／右1.259e-8rad。首尾网格虽仍244／246，除固定终点外全部原binary64样本不同，exact-q缓存不能替代整个全扫。R132的实际FK与上下文覆盖缺口仍在，原同步认证保留。

本轮完整周期P95均低于20ms但仍有慢拍，不能勾选完整50Hz。R143慢拍351，其中hold176、release97；原全扫在本VM31～37ms，旧R127441ms不是当前耗时。R145 v2补齐556条更新，原pass／3795拍／91慢拍，其中73拍位于进入hold/release且worker运行的窗口；重复binding单次约.5ms，poll没有阻塞join。不能把wall−CPU直接叫GIL。v1观察器序列化失败保留；v2只修记录落盘。完整数据见[周期与漂移报告](m1b-pending-and-cycle-results.md)。

旧F2bo的1ms解释器时间片已有两站反证，本轮不重复；不再因微小绑定开销另造数组优化。下一项复用既有真实guard与原运输planner做Thread／spawn进程隔离组件验证；先核数据传递、取消退出和三对输出／路径等价，尚不接生产，也不宣称它能解决仍同步的完整闭爪认证。

## 新X请求的编辑联动缺口

原workspace-development-v1已支持固定视觉先验内的新XY，不是点位白名单。单改cube或hover时，approach／grasp设计节点仍保留旧位置，validate_station先报一致性问题，尚未到IK。原父坐标系解析可直接解决重复坐标：新增pickup_request世界框架，三个节点保留局部偏移；只改框架位置即可联动，红盘pick／execution.pick_xy不动。左右新样例保留原工艺／程序，4项数据回归及相关原单元检查通过；[R141](m1a-x-linked-request-results.md)现已完成真实网页只改frame X至.224／.256m，导出→唯一POST→request同值，两原物理均pass。新位置RGB估计与相邻中点恰相同，不能将0.5mm编辑当作亚毫米视觉分辨证明。没有新增模式、执行引擎或放宽准入。原describe的±10mm文本补“默认工位”，开发能力仍以既有execution声明和逐任务原判据为准。

## 实测取料段的限制对与静态选点不同

[R140](m1a-x-execution-clearance-results.md)复算R137原初态、全部取料／持物前缀与首transport边界，共3381实测姿态。原1mm全过；全285对可认证下端左约1.729mm在lift26.74s的红盘壁／夹爪，右约3.058mm在approach5.62s的障碍／夹爪。右盘壁68对单列约5.283mm在descend18.58s。这些是原方向族对保存状态的证书，不是欧氏净距、自由物块净距或连续轨迹；R139静态1.937／9.372mm不能代替全取料段。取料及交接边界最小五轴腕余量左3.311018°、右2.046893°，不能代替运输段约.838772°。原阈值／默认不改。

## X方向的约1.0001mm并非最近距离

R139复用R136原18个保存姿态、原MuJoCo3.15.0及285对，不求新IK或步进。抬高离线查询要求后，两个原选中姿态的全场景可认证下端分别1.937078476／9.371626854mm；原盘壁见证对则可证143.270339／37.531574mm，瓶颈已换对。原native首个通过方向即返回，因此约1.0001mm是早停见证，不能据此判贴壁或将其超出1mm的量当作误差半径。[原件与区间](m1a-x-clearance-readback-results.md)。仅保存姿态，不是全轨迹／欧氏最近距离／连续域；原IK、线上1mm与默认不变。

## 同一X取料配置已复用第二放置工位

R135只改place.position至(.20,.20)m，两中点加既有中心原物理3/3pass；输入、六份XML蓝盘全几何平移和红盘／robot／option／actuator不变均核实。全扫、释放脱离回位与原裁判保持，独立126项无失败。中心释放漂移仅2.71e-20m末位复算差异保留，不能写成全部浮点exact；原判定／逐2ms旗标一致。[三例原件](m1a-x-second-place-results.md)。新完整周期仍有210／193／184慢拍，不与上轮网页秒数作性能A/B。

R134现有trajectory包含20ms object_xyz_m／速度，不能误写没有同步真值；定点复核已撤回漏读诊断。除首帧用initial报告外，所有视觉时间与两handover精确匹配；名义冻结到首次正指尖力前的采样XY近乎静止，不证明运动目标或拍间瞬态。初始真值误差与声明误差近似，目标初始偏移不能解释约.6mm误差。定位输出约1.7mm是像素＋声明高度工程量，不是全域置信界，也不等于原1mm碰撞余量；后续必须按实际输入和原初态种子做离散敏感性检查，真值只用于评价。

## X中点工艺已贯通原网页

左.2245m原60mm/.5、右.2555m显式54mm/.35在固定红盘下，已由真实浏览器创建两个独立任务并完成原物理抓放／释放／脱离／回位。导出→POST→request严格一致；普通robot-station导入会重建program步骤UI ID，只有该字段可在fixture比较中忽略，动作顺序和execution不能忽略。原网页35项Station相关检查及新真实整链另列，不以测试数代替结果。[实测、计时与保留失败](m1a-x-web-midpoint-results.md)。

私有计时observer曾因缺GNU time使worker在物理Python启动前exit127。修正为显式安装及可选缺失时警告降级；两次原失败保持。QA整命令、物理episode、实际进程和包含子进程的preview生命周期分别计时，不能相加或串成提速；无原EpisodeTiming，完整50Hz仍未知。

本轮左中点实际RGB相对声明位置误差.631418mm，右.524661mm；旧P0另一位置面板最大.616511mm不能作为工作区定位误差上界。原控制仍从本次RGB规划，继续按逐请求取证。

## 左补证：复用同次明细，不复用跨姿态安全结论

原_bound.summary已在锁内算完整numeric/flags，MeshBoxAxes.refine随后对同FK再次执行285对native.evaluate。私有单调用拥有明细在571派生状态上将固定轴ABI1142→571，补方向571保持；原全部返回／报告／hint与244扫掠exact。固定500dc47的Kaggle三对wall/threadCPU均降，中位比.716078/.715990；[组件结果](m1b-refinement-details-results.md)不代表整程提速或物理通过。

明细须在锁内复制、单次消费；不持有scratch view，不跨姿态／owner／模型／margin复用。关闭或错配仍走原查询并保留原拒绝。生产默认关闭，已补实际碰撞／所有权／重入回退测试；新生产组件中位比.720152／.720157，五例原物理5/5。两左工位实际wall分别少4.924／5.002s、CPU均降且hold同拍，保留显式候选。已淘汰的batch前缀会新增工作，与去掉同次重复detail是不同方案。

整程计算减少不等于50Hz改善：本批两对P95及>20ms拍数均增加，transport controller还增.922／1.684s。不能从close收益推全阶段或跨VM累计秒数。后续固定b236ff4的18组云组件显示：lift每90查询仍10次补证可省detail；hold／transport样本90/90直接clear，两边native90不减，候选明细入口90次。运输每query配对CPU中位多3.2–24.4μs，但多组三对反向，hold还存在零工作节省却全快的反例，不能将整段秒级差异归因完成。先查完整弦中间采样，再决定是否用已有raw batch前缀；旧close全补证的失败继续淘汰。端点样本、完整弦和真实控制调用分别记证据。

## X请求的搜索顺序：原物理收益已证实，快环问题仍在

05cc17c的完整loaded-jaw midpoint候选只改变shorten_path直连弦试探顺序，不是IK或OMPL求解器。左B→C／右第二工位C→B的4/4原物理均pass；同侧raw和executed approach路径、最终认证exact相同，最终535／490点保持。左shortcut16.261→3.027s，右4.111→1.448s，实际process wall分别少14.621／2.547s且CPU均降。左hold不变、右候选多5拍，证据支持实际搜索工作减少。[原结果与复跑](m1a-x-midpoint-results.md)。

保留显式候选，原默认不变。初始化变快没有解决左close/lift的20.172／5.862s controller成本；候选完整周期仍有1512／170慢拍。只证明本面板，不能宣称全链路轨迹exact、连续工作空间或完整50Hz。前置局部批量前缀571状态全需补证，三对全部更慢，已淘汰；原外层384补证计数不能代指控制器内部全部查询。

## X向负例：场景必须随请求平移

原run_p0的缺失／遮挡／多候选负例全部固定在(.24,−.13)，不能据它证明新X位置的拒绝行为。新字典负例使目标、遮挡片、干扰物使用同一XY差值；每例恢复pos/size/rgba，原定位函数和阈值不改。拒绝还需没有metric pose，原始PNG与实际geom快照另存供独立复算。

新显式17项面板含原三位置正例／中心四负例和X±11两正例／八负例；默认协议仍原七项。原reset每例500步静置，不能称零积分或抓放成功。实际渲染及后续晋级见[m1a-x-perception-results.md](m1a-x-perception-results.md)。

## X向新请求：端点方案不能直接插值

固定红盘X=.229/.251、Y=−.13m的原静态检查均通过原60mm高位、.5rad开爪、IK残差及285对／244点扫掠，不需要X±20mm端点的补轴或预收口。全采样证书下界最小分别1.012254／1.026594mm；这是保守分离下界，不是精确净距或实测跟踪余量。两点直达接近弦均在approach_obstacle/gripper拒绝，取料腿通过不能替代原OMPL绕障和后续物理验收。

离线CLI原先把.5开度写死，默认不查闭爪，不能直接复跑右侧已验证工艺。本轮已补显式开度和完整扫掠诊断，原执行器、网页边界与原裁判不变。两个新请求已在固定66ee5d1的原云物理均pass，完整244／释放／脱离／回位保持；[原结果](m1a-x-interior-results.md)不外推连续域或50Hz。

证书下界接近1mm不能解释为几何只剩几微米。两选定pose/pair的本机原生查询分别156.247／7.012mm，而证书下界仍1.012／1.027mm；这是不同定义和范围的诊断数。原生distmax裁剪值不能称距离，也不能替代原安全证书。静态本机3.3.7与原云物理3.15.0分别记录，原件在output/x-request-probe-20261024及output/x-interior-20261024。

## 固定红盘右侧：工艺顺序已用原物理证实

X+20mm的60mm高位腕限位与大张口盘壁拒绝是两个约束。保留原95°限位和全部碰撞，使用已有54mm高位，先在高位实测收至.35且稳定，再下降；高／低位完整扫掠各246点。原大开度仍fail，显式候选在原主与(.20,.20)两个放置工位分别原pass79.26／82.34sim，原中心回归pass76.62sim，红盘未移。完整50Hz与连续工作区未验，默认不切。详细源／原件／失败和复跑见[m1a-x-fixed-certificates.md](m1a-x-fixed-certificates.md)。

## 固定红盘 X 向补证（2026-10-24）

左侧默认关闭的完整补证候选已过原19轴／285对／244点离线，但首轮原物理耗尽120s，停close22.56sim，未抓起。原中心回归通过。瓶颈为每帧构造46,869方向；方向建议复用在原1522姿态三对保持全部返回逐字段相同，约14.5→.87s，仅组件收益。第二候选46f5ba5已在原主／(.20,.20)工位原pass74.10／76.84sim，两次planned／measured244、释放／脱离／回位均过。主／第二工位分别701／722慢拍，仍非50Hz；默认与网页准入保持。每帧完整投影及全部worker／实测检查、原1mm保持，不复用安全结论。对应实现／反例／复跑见下方结果文档。

原19轴不足与真实可用路线分开。新增可选原生API沿用完整顶点区间投影／原平方门，默认查询不变。左X−20mm下降74／闭爪244／抬升74补证全过，原offline_screen_pass=false保留；右X+20mm采用已有54mm IK姿态，独立64拒绝点中18补证、46仍拒绝，不能凭补方向解锁。原件、失败覆盖与复跑见[m1a-x-fixed-certificates.md](m1a-x-fixed-certificates.md)。此段是补证API阶段的历史离线结果；后续原物理见上段，网页准入仍未扩大。

## M1b 回位瓶颈更新

- 同365db2b源的原X−20布局观察ca00cc74…完整抓放通过。只读profile记录75次arm检查与150次双pad SAT，但父帧统计缺失，且复制快照额外120ms；不使用其最大拍做性能A/B。
- 同MuJoCo3.15和同冻结MJB的5次无积分复算，原_return_path每次都是validated_direct、75状态、原.005rad分辨率；路径逐位一致。中位131.131ms；原arm检查累计约38.875ms、释放物距离累计90.489ms，未触发OMPL。旧140ms尖峰有具体同步计算证据，不能再笼统归因随机搜索或主机等待。
- 新候选保留算法与所有判据，只迁移实测q出发的完整回位规划。复用已consumed/joined的独占模型和原异步生命周期；结果接纳前保留上下文、实测桥接、首命令与预算。预计回位路径仍不能直接当作实测回位轨迹。
- 默认不开启候选；同输入等价、原完整物理与完整周期分别裁决。局部测试不是抓放通过；新增等待不能当作算法计算减少。
- 已完成三对同输入等价和两X布局反序4/4原物理。左首回位完整拍143.018→33.347ms、右36.634→30.314ms；候选仍超20ms，整程wall/CPU两侧方向不一致，不晋级默认。具体原件、指标和限制见[m1b-return-results.md](m1b-return-results.md)。
- 新只读准入回合c0045f5f…原pass。最终_poll_return14.613ms，其中job生命周期自身约.067ms；两次原validate_joint_path共6.652ms，binding约4.742ms。完整首retreat33.843ms，controller之外与poll之外仍有成本，不能称仅剩线程切换。原最大116.359ms在transport，callbacks105.803wall／3.227threadCPU；它证明主要是主线程等待，尚不能区分文件I/O与宿主调度。不能把全部归给SAT、GC或原算法计算。

## M2/M4 薄适配更新

- M2原物理抓取证据已过新完整抓放与真实取消；[结果](m2-grasp-evidence-results.md)。progress回调可在物理推进后、monitor更新前取消；因此轨迹行数不等于已评分行数。新证据记录实际observe数量，取消1511/1512行，不把完整轨迹重算hold3.56s盖掉原3.54s。显示层接收深拷贝，不能污染原证据；历史Grasp后置条件与最终attempt失败分开保存。

- 2026-10-24新配方原物理1/1与真实运行中取消已独立回读，见[m4-recipe-results.md](m4-recipe-results.md)。两项是功能／生命周期验收，不是性能A/B。完整回合最大60.075ms在transport，controller54.017wall/54.017CPU；两例close段也重复约40ms controller，不能套用前轮callbacks等待归因。下一次50Hz分析应按当前同源实测重定位。
- M2新接点审查：原progress_callback早于monitor.update，不能以stage发布技能成功。Grasp应以原持续双指接触／抬升monitor为后置证据；ReleaseAudit在脱离后仍可能因重接触转失败，Place与Retreat证据不可按阶段硬切。真值仅作裁判／展示，不反馈恢复控制。

- 原Station只根据cancel文件存在优先发布cancelled，会覆盖更早物理fail及晚到请求前已完成的pass。现已分列cancel_requested／cancelled，仅真实Cancelled且无原安全、清理和其他失败原因时取消；原report保留。22项Station CPU检查通过，不冒充运行中取消实测。
- 六技能不能只换阶段名：原progress在monitor.update前，close结束不证明抓住，Place的释放审计可能在Retreat中才完成。生命周期应消费初始视觉、实际issued、post-monitor、finally清理四类证据；完整恢复尚未实现。
- 配方复用原Station payload与原任务入口，不另写执行器。前端和CLI共同核米制、纯平移、独立episode、SO101执行器、固定技能声明；未知可选元数据与历史引用保留，历史pass不产生当前pass。节点rotation及SO101未执行的size/motion/enabled明确拒绝，避免旧容错导入器无声丢弃执行语义。
- 配方交换不等于FishBot同世界卸货。当前pick世界Z=0、cube Z=.01；车载高度、连续货物身份和同world/episode仍待实现。

## 已核事实

### 工位范围与运动学

- 当前输入合同要求工件中心 `XY=(0.24±0.01,-0.13±0.01)m`、`Z=0.01m`。
  这是执行器的显式检查，不能直接解释为机械臂只能移动 ±10mm；见 [station_executor.py:170–172](../../experiments/colab-twin/station_executor.py)。
- 实际 IK 接收 `xyz`，残差为位置误差乘 10、夹爪局部 Z 轴对齐世界竖直轴，以及 `q[4]*0.1`。
  它没有输入世界 yaw 或完整目标旋转矩阵；见 [grasp_episode.py:114–128](../../experiments/colab-twin/grasp_episode.py)。
- 求解器要求上述总残差范数 `<1e-5`，不能把 wrist-roll 项仅当作不影响接纳的软排序。
  该组合是否缩小可用工作空间尚未对照证明；见 [grasp_episode.py:130–137](../../experiments/colab-twin/grasp_episode.py)。
- 接近、下降、抬升及运输实际调用此 IK；见 [visual_grasp_controller.py:334–339、877–879](../../experiments/colab-twin/visual_grasp_controller.py)。
- 径向 yaw 需要工具轴、零位、父体变换和夹爪偏移映射，不能直接等同某个关节角。
  模型存在肩部偏移及局部关节轴；见 [so101.xml:49–102](../../workspaces/so101_ws/src/so101_mujoco/models/so101.xml)。
- 对象对称性决定可放宽的朝向。圆柱、方块和有朝向要求的零件不能采用同一 yaw 自由度假设。

### 性能与现有快慢环

- OMPL 已设置进程首次规划 seed：仅 `_INITIAL_SEED` 为空时调用 `setSeed(max(1,requested))`。
  报告明确记录 `rng_seed_scope=process_first_plan`；见 [joint_planner.py:105–112、162–164、190](../../experiments/colab-twin/joint_planner.py)。
- 这不等于每次规划重置 RNG。调用顺序、实例创建和输入仍需记录；官方区分全局 seed 与实例 seed。
  来源：[OMPL RNG 官方文档](https://ompl.kavrakilab.org/classompl_1_1RNG.html)。
- F2ce 在同一次 ratchet 中复用完全相同参数的纯 SAT 结果，保留原距离、forward、native 和 pad 查询。
  176 输入组件三对均省计算，中位 wall 省 119.533ms；见 [原进度:1697–1703](../factory-loading-20261021/progress.md)。

| F2ce 工位 | 原版→候选 process wall | 完整慢拍 >20ms | 原物理裁判 |
| --- | --- | --- | --- |
| 200/200，B→C | 54.044251→52.726573s | 139→123 | 2/2 通过 |
| 220/170，C→B | 49.478408→50.707895s | 80→106 | 2/2 通过 |

- 两站共 4/4 物理通过，但整程性能一好一坏，候选未晋级；见 [原进度:1705–1716](../factory-loading-20261021/progress.md)。
- 初始化和 transport worker 在候选介入前已有差异；固定非 hold/release 拍数的 CPU 也不一致。
  不能把约 ±1.3s 的整程差异归因于 SAT 或 OMPL 随机路长；需分别核原路径、阶段拍数和运行开销。
- F2cf 是原控制器的叶段观察：3867 完整拍，P50 10.229ms、P95 17.293ms、max 83.863ms，148 拍 >20ms。
  原任务通过，完整 50Hz 未通过；插桩秒数不能与其他 VM 拼成加速 A/B；见 [原进度:1725–1729](../factory-loading-20261021/progress.md)。
- 同回合 measured checker、configuration sweep、validate_joint_path 的 max 分别为 2.718、40.538、64.135ms。
  它们是 inclusive 时长，不能相加为总成本；见 [原进度:1733–1740](../factory-loading-20261021/progress.md)。
- 已观察到同步 244 闭爪认证和回位完整认证；一次 sweep 内发生 35.426ms gen2 GC。
  该事件只证明该插桩回合，不能据此解释全部历史尖峰或直接命名为 GIL 等待；见 [原进度:1742](../factory-loading-20261021/progress.md)。
- transport 和 separation 已有异步 worker。主线程继续轮询、检查上下文、认证现场桥接和首指令。
  见 [visual_grasp_controller.py:759–815、1031–1156](../../experiments/colab-twin/visual_grasp_controller.py)。
- 回位直接路径复验及必要时 OMPL 仍有同步入口；每次 update 仍检查实测状态。
  见 [visual_grasp_controller.py:991–1000、1372–1375](../../experiments/colab-twin/visual_grasp_controller.py)。

### 共享工位与连续世界

- 5186 `/so101-station` 由 FishBot 仓库的 `apps/fishbot-control-station/so101-runtime.cjs` 调用 SO101 执行器。
  这证明已有跨仓入口，不能按端口认定两套独立前端；见 [STATION_EXECUTOR.md:81](../../experiments/colab-twin/STATION_EXECUTOR.md)。
- 当前执行器接收 Station 或任务信封，每个输出目录是独立 episode；不能直接当作同世界连续卸货。
  见 [STATION_EXECUTOR.md:18–38](../../experiments/colab-twin/STATION_EXECUTOR.md)。
- FishBot 连续计划规定 Physics 是活动世界唯一 writer，bridge 持有任务与原生 Goal，Oracle 只读。
  继续扩展原 factory/workflow，不新建调度服务；见 [连续计划:42–45](/home/muqiao/dev/ros2/projects/fishbot/plans/continuous-twin-regression-20261024/task_plan.md:42)。
- 已验收运输使用 ideal 观测及显式 reset，不能据此宣称视觉或无 reset 连续任务已通过。
  见 [COOPERATION_WORKFLOW.md:141–151](/home/muqiao/dev/ros2/projects/fishbot/docs/COOPERATION_WORKFLOW.md:141)。
- 连续计划要求两个独立自由货物、同一 world/episode/源时钟/编码器/车体位姿，第一件送达后原位继续。
  禁止 reset、传送或改名替代连续性；见 [连续计划:125–129](/home/muqiao/dev/ros2/projects/fishbot/plans/continuous-twin-regression-20261024/task_plan.md:125)。

## 本轮决定

- 继续复用 MuJoCo、现有 IK/OMPL、控制器、评分器、FishBot 工作台和原 Workflow/bridge；本轮不选新引擎。
- 将径向 yaw 作为待比较候选；保留对象朝向与对称性合同，先验证 IK、碰撞、连续路径及真实接触。
- 将 ±150mm 作为待测产品目标，先定义它是 XY 方形范围还是半径，再发布实际测得的有效区域。
- 将 3–5ms 与 P99<20ms 作为架构目标，明确统计对象；不把它们写成锁 seed 后必然得到的结果。
- servo-only 与原完整周期分开报告；完整周期保留安全检查、感知、worker 准入、244 闭爪和回位切换。
  两者均报告样本数、P50/P95/P99/max 和 >20ms 数量；P99<20ms 不等同全部周期满足 50Hz。
- 快环只执行已获认证范围内的命令；迁出在线认证前，先证明慢环证据覆盖实际状态、上下文和执行区间。
  复用冻结快照、context binding、现场 achieved-q 桥接、首指令守卫、取消和原回退，不以删除检查提速。
- 原 planned/measured 244、trajectory guards、碰撞阈值、自由物体 weld0/mocap0、抓放释放脱离回位继续验收。
  双 worker consumed/joined/owned_ack、90sim/120wall 也保持；见 [原进度:1714、1729](../factory-loading-20261021/progress.md)。
- `station_recipe_v1` 定位为共享工位配置合同，先静态导入与预览，派发仍走原任务入口。
  待实现字段包括配方/资源身份、单位与 frame、模型/碰撞来源、能力段、显式观测模式及稳定 cargo/slot 绑定。
- recipe revision 用于来源与兼容描述，不设内容哈希锁；未知可选元数据警告并保留，不支持的执行语义只拒绝该配方。
- 任务运行绑定另存原 bridge UUID 与 station task ID；取消、超时先查询原任务，不因回执不明重复派发。
- 卸货与库存需绑定同一实际物理 body；货架落稳、卸载臂归位和托盘空闲成立后，按 cargo ID 更新一次。
- 行为树如后续采用，异步节点只负责启动、监控、结果与取消；耗时动作不能阻塞 tick。
  依据 [BT.CPP 异步节点官方文档](https://www.behaviortree.dev/docs/guides/asynchronous_nodes/)，该模式不保证自动并行或实时性能。

## 未知与验收入口

- 径向 yaw 是否改善工作空间、严格 wrist-roll 残差实际拒绝了哪些点、±150mm 可用区域：均待测。
- 本轮没有重新逐点复核原 A/B 路径；已有原进度不能支持“随机路长造成约 ±1.3s”结论。实施时继续保存原路径与规划事件，不能仅看总 wall。
- servo-only 3–5ms、完整周期 P99<20ms、所有切换拍 50Hz：均未取得新架构验收证据。
- `station_recipe_v1` 导出/导入、终点卸货、同世界无 reset 多货物及双 owner 取消汇合：均待实现或验收。
- 当前源码默认观测模式、任意动作编排、Mint teleop 接口：本轮未核实；Mint 不改。
- 性能采用同输入、同工位和反序成对比较；组件收益、原物理成功、整程性能及默认晋级分别裁决。
- 连续世界沿 FishBot 原计划进入实施；新卸货阶段单列预算，不能把扩展任务记成旧 360 秒任务通过。

## M1a 首切片：离线实测与开发入口

新 [空间探针](../../experiments/colab-twin/probe_workcell_workspace.py) 复用原 IK、保守证书、1mm 阈值和 .005rad 抓取腿检查，不推进物理、不认证完整闭爪或后半程。11 点中 9 点通过离线筛选。X−20mm 的 down 对 `pick_wall_x_-1/collision_gripper_1` 证书下界约 0.880489mm，不能认证 1mm 净距，不冒称已证明真实碰撞；X＋20mm 的 approach/lift 原 IK 失败。Y±20mm 端点与抓取腿通过，仅作为物理候选。

编译模型回读：base 位于 world 原点；shoulder_pan anchor 为 `(0.0388353,-8.97657e-9,0.0624)m`，其 world 轴约 `(0,0,-1)`；顶视相机 `(0.25,0,0.95)m`、R=I、fovy45°，局部 −Z 朝下。工具 pinch 是局部 `(.006,0,-.094)m` 的变换点。该结果是仿真 frame 核对，不是实体相机标定，也不能把径向 world 角直接当 pan 角。

源码另有控制器 `_target()` 的 ±10mm 限制。新增显式 `target_region_xy_m` 仅供开发配置使用，初始与后续 RGB 估计共用同一静态先验；默认表达式和消息保持。网页 validate/describe 仍为原 ±10mm。新 [开发入口](../../experiments/colab-twin/run_workspace_case.py) 按 [四案例 profile](../../experiments/colab-twin/scenarios/workspace-m1a.json) 复用原 `run_physical_episode`、评分与录像，输出 `development_only/not_admitted`；不能因开发案例成功就开放完整矩形区域。

当前本地原实验环境为 `/home/muqiao/.cache/so101-colab/planning-venv/bin/python`（MuJoCo3.3.7），旧 graspgenx venv 已不存在。为运行既有控制器检查，仅在该隔离环境新增与已验云环境同版 `opencv-python-headless==5.0.0.93`；没有改系统环境、NumPy 或 SciPy。Kaggle 继续复用原 bootstrap／串行 runner，单独记录其 MuJoCo3.15 环境，不跨机器比较速度。

## 已采用知识

- 来源：[Wiki《ROS2 与 FishBot》第20节:451–468](</home/muqiao/桌面/obsidian/my-programming-world/Wiki/ROS2 与 FishBot.md:451>)。
  本轮采用“动作、物理、交接、晋级分开”及“组件收益须回到原完整任务核实”的既有原则。
- Knowledge=already_covered，仅指本轮原则已被原页覆盖；本轮未修改知识页，不代表其他待审内容已收尾。

## X 方向：限位与证书分离（2026-10-24）

原 X+20mm、60mm高位已到腕俯仰95°边界，去掉roll偏好不解决；54mm高位可解但原盘位的低位仍不认证。X−20mm低位的0.880489mm为证书下界；全编译网格投影有16.773623mm分离轴证据，因此不能把它直接叫实际撞壁。详见[m1a-x-results.md](m1a-x-results.md)。

本次选择显式工位布局薄适配，保持原检查器、阈值、夹持／释放裁判。新参数与测试分别在grasp_workcell.py、grasp_episode.py、visual_grasp_controller.py及run_workspace_case.py。原网页与±10mm不变；局部筛选仅是原物理的前置。右侧最薄证书仅比1mm多约4μm，动态跟踪风险必须由原物理核验。

X开发布局随后在固定e7f921c的Kaggle v1原物理4/4通过；planned/measured244、RGB、释放/脱离/回位和worker独立回读均完整。新布局可复跑，原固定盘位X拒绝并未消失。完整50Hz未过。具体输入、成绩、反证与复跑见m1a-x-results.md，不将布局结果写成算法加速或区域全覆盖。

## Station入口接续的实际所有权

5186源码实际在FishBot的独立工作树`/home/muqiao/worktrees/fishbot-workbench-code-rebuild-20261018`，分支codex/workbench-code-rebuild-20261018，入口apps/fishbot-control-station/so101-runtime.cjs与Lichtblick RobotStation；不是主FishBot dirty main。复用原task-runtime、任务UUID、取消、scene与录像。此前仅写FishBot仓库相对路径的记录不足以确定运行checkout，本轮已更正。开发参数用显式execution对象而非隐藏profileID覆盖节点；只有省略execution才用原默认，坏声明保留给原准入拒绝。

## 新Station／网页结果与M1b下一证据

真实网页输入经新Station源码084cc7f，原物理左右2/2通过；不是重用开发CLI成功标签。证据与未采计时边界见m1a-station-entry.md。并行工作台Drone源码由原owner后续提交de94a6d；本轮未改其模块或主FishBot工作树。

旧X四回合timing的exclusive parts只读归因：15641完整周期，281拍>20ms；controller主导218、perception51、physics_and_guards12。最大140.476ms/135.697ms位于separate→retreat同步_return_path(q6[:5])，主线程CPU接近wall；尚未细分函数内部，不能归因于特定碰撞算子。worker的planned_return目前用于预算/报告，不可直接代替实测q回位。私有可复跑审计round102/m1b-slow-cycle-audit.json保留全部原index、stage和top10。下一步限于这一有证据的交接点，全部安全责任不丢。

## X向新位置的渲染拒绝取证

原P0负例固定于中心，不能用其通过声称X±11mm遮挡已验。现兼容显式位置声明，遮挡片／干扰物与目标同量平移，保留真实PNG供原定位器独立重算。固定890616a的Kaggle原17/17通过，五正例最大误差.616511mm，12负例均无坐标输出；17原始PNG的完整estimate重算一致。8500次原reset积分、P0与进程时钟单列，详见[m1a-x-perception-results.md](m1a-x-perception-results.md)。

该面板只补位置相关的观测拒绝证据。轴齐／高度仍为先验，不替代IK／盘壁证书、物理抓放或连续域准入。把目标移到新位置时，负例遮挡物也须移动；否则只是在新位置重复无效遮挡。Knowledge=already_covered：动作、观测与晋级分层仍沿用Wiki§20，未修改共享知识页。

## 固定盘请求的Station接线缺口

现有execution.pick_xy_m传给build_contact_scene，控制整只红盘；cube初始XY才由原reset设置。固定盘请求应保持前者(.24,-.13)，approach/grasp世界XY与cube一致。原模式已能表示这种分离，无需再造固定盘mode。端点还需将原开发CLI已有的pickup_open_jaw_rad和mesh_box_axis_refinement作为显式参数接入Station；默认与原模式保持。此次只补透传和可编辑样例，真实新入口物理验收另跑，不把已有开发CLI通过贴到新Station任务。

后续固定2d7097ef的新Station原物理已结束：两端点及原中心3/3pass，两项关闭适配的原初始化fail保留；实际XML盘位、输入差异、真实夹持释放脱离回位和完整扫掠均独立核实，见[m1a-x-station-fixed-results.md](m1a-x-station-fixed-results.md)。本次左侧98.140wall、903慢拍，主要已定位成本为初始化shortcut与close/controller；原OMPL搜索仅.134s，不借随机性解释全部差异，不从这些不同输入计算性能收益。

## X侧完整弦批量前缀：组件与owner交接分开

round122原全弦筛选与三对已终态，结果见[m1b记录](m1b-refinement-details-results.md#2026-10-25完整派生弦的批量前缀组件)。54条保存姿态派生弦的hold／transport全部raw clear，按原分辨率批量查询可降低Python组件成本；但独立shadow原型没有更新主checker的MjData和witness历史，六组全部不一致，不能生产采用。close571点全需补证，完整回退不减原查询。原报告exact仅证明路径布尔结果相同，不证明控制器副作用与交接成立。下一候选须同owner且原generation失效仍成立；不删refinement拒绝就直接上线。

## 同owner的实际状态比较与分阶段收益

round125已实测77个arena指针为NULL，102真实NumPy数组＋77 NULL标记组成179比较条目；前轮11个争议getter在native NULL时另行分配临时NumPy数组。不能把临时内容当MjData状态，也不能整体略过efm字段。保持私有候选不变后5functional和7组云内状态比较通过，详细证据与同版源码见[m1b结果](m1b-refinement-details-results.md)。根179项、独立414项读回通过；原数组bytes未归档，不称下载后独立字节验证。

同VM三对wall／CPU中，运输两工位中位wall比分别.734709／.720192；close三对全慢。snapshot／rollback成本已计入，支持继续显式transport-only生产适配，不支持全阶段开启或默认晋级。原1mm、285对／244、90sim120wall和原物理裁判保留；未新增Station物理、连续域、20＋20或完整50Hz成绩。外部CLI后续仅AGY／Zcode，已知耗尽的Qoder／CodeBuddy及停用dsh不试探；本轮Zcode超时不计审核成功。

## 正式运输前缀的作用域与首次异常

新增选项仅供transport online_chord，close仍完整原链，不能将前轮close负收益隐藏为全阶段优化。正式实现比私有原型增加逐FK binding／generation核验，成本须重新测量。首次FK异常与binding变化可能同时发生；后者不能优先触发回退，否则一次性异常会被第二次成功执行抹掉。已修复优先级并独立复现，83项本地协议回归通过；尚无本轮实际模型／完整物理成绩。

round126私有目录：`/home/muqiao/.cache/ros2-factory/codebuddy-so101-20261021/round126-production-transport-prefix/`。复用round120原runtime与component slot，实际有效数组bytes压缩归档，压缩在测量区间外；不再只保存云内比较回执。AGY90s超时保留，不能称外部审核通过。最新CLI约定以本轮AGENTS为准：Qoder／CBC每批调用前查usable，ZCode用edit，DSH暂停；旧文中的永久禁用描述仅属当时状态。


round126正式生产实现完成实际验收：5功能／7组三对与86份原数组归档独立同值，两transport三对wall／CPU均快；原Station两工位反序＋中心5/5pass。两站进程wall省1.373／2.376s，非hold controller亦下降；不以少1hold拍解释全部收益。原1mm／285对／244、自由物体、释放脱离回位保持，显式候选保留、不切默认。v1短ref fetch失败与v2旧physical_status文本均保留。完整50Hz仍未过；新时序仅定位最大close段controller约398ms，内部planned／measured尚未细分，不从残量猜OMPL或相机。证据、实际清理与下一步见[m1b结果](m1b-refinement-details-results.md)。

## 实测闭爪与单行提示反证

round127新增原物理通过，最大close进入拍不是两次完整扫掠叠加：原measured244占441.843ms，随后online只有2点3.975ms，transition是包含子项的442.048ms，不可相加。普通close仍330拍／6362点／12.096504s；lift143拍／8008点／5.228489s。仅搬出一次transition认证不能消除持续成本。

round128原输入fresh-state cProfile中，488次_detail_arrays包含全285对与单行hint各244次；不能据函数调用量声称全明细重复两遍。round129针对单行hint避免向量校验虽12份NPZ真实状态同字节、876请求全部命中，三对wall与CPU的第二对均变慢，故按原门槛淘汰。组件正确与收益稳定是不同条件，不能以55.644ms中位掩盖反向对；不进入原物理追绿。来源、实际失败和复跑入口见[m1b结果](m1b-refinement-details-results.md#2026-10-25实测闭爪归因与单行提示反证)。

已有预载只在lift→hold固定一次目标，输入为encoder和previouscommand；提前到lift可能缩短在线认证弦，但原sts3215增益、速度阻尼、力限幅及周期内变化需实测。静态同力不是接触轨迹或持物成功证明，先只读筛选。原1mm与所有点不减。

## 预载提前的时序与驱动力边界

round130真实143帧用前一trajectory状态对齐observer周期初，再把当前raw.command作为该周期输出；不可用周期末q冒充控制器观测。规划模型mj_forward静态驱动力6维同值，原分辨率理论点数减少，但原运动duration2.257558s与完整lift跨度2.86s相差原等待；在线实现使用原motion_duration，不能拿未来实际阶段跨度作策略输入。该筛查不读取物体真值，也不证明接触、2ms积分、完整抓放或提速。实际证据与默认关闭实现见[m1b结果](m1b-refinement-details-results.md#2026-10-25提前抬升预载静态筛查)。

## 提前抬升预载已完成原物理，不外推动态力相同

round131新源码2eea9bb，完整组件的候选端点独立通过原285对／1mm与全分辨率；不是只看理论点数。两工位反序原物理和中心5/5pass，实际process wall少1.318541／.991991s，CPU和同143拍lift成本同降。hold候选反多1／2拍，不能将收益归为少等。初态、请求、OMPL及实际接近路径同值；候选只在close结束后改变jaw。

独立原Monitor／SkillEvidence／ReleaseAudit重算与原报告exact，释放、脱离、回位与全部244保持。原物理仍未保存2ms actuator_force，不能把静态必要条件扩写成动态力等同；任务通过和完整50Hz也不同，候选492／458慢拍，最大428／420ms。保留显式策略，全局默认保持。证据、失败边界与复跑见[m1b本轮结果](m1b-refinement-details-results.md#2026-10-25提前抬升预载的正式组件与原物理)。

## 后台闭爪不能沿用旧姿态绑定

现有SweepBinding包含owner/model/checker、observation/request、实际start/end与场景语义；现有transport/return worker只提供生命周期及旧路径，现场仍另做fresh bridge，不能删绑定字段挪用其结果。可探索新的覆盖证据：nominal原244点增强margin须覆盖每对两侧几何运动，主线程再核当前采样grid、限位和模型／观测上下文；不能伪称原当前姿态已经查询244次。

R132原几何实测三组完整244均通过，增强1.001mm仍获证；compiled模型六个单hinge、anchor零，可限定此模型而不造通用运动学框架。私有理想半径／向外插值预算在同网格前提下可容纳拟议1e−7rad箱，但actual FK数值误差、fresh采样数／间距和pending-hold实际漂移仍缺证。R132不是新物理或异步接纳成功；详细来源和恢复见[m1b R132](m1b-refinement-details-results.md#2026-10-28r132闭爪增强净距与覆盖预算)。

## 2026-10-28：X中点须按实际RGB分别核IK与扫掠

X=.2555m名义60mm IK解高位余量仅.001181rad，预收口可修复名义下降缺证，却无法修复真实输入下的高位IK拒绝。实际RGB=(.2556298526685876,−.13050833816470292)m；原静态reference下也能复现与执行同残差.0007626829034486256。显式高位54mm使该诊断关节余量增至.047829rad；同解.5下降仍缺1mm证书，.35全扫通过。原物理同初态／同RGB仅改高位后抓放成功，左中点原配置也成功。保留失败，不放松IK／几何门槛，不将有限种子搜索叫全局无解，不以分离下界冒称欧氏盘壁净距。来源：[本轮原件及读回](m1a-x-gap-results.md)。

复用原probe、run_workspace_case、Kaggle bootstrap／串行runner与独立裁判即可，未新增调度平台或自动坐标选参。新profile只扩大明确可复跑的开发样例，不扩大网页合同；真实视觉输入与执行种子须纳入下一次筛查，不能用名义坐标的静态成功替代执行。

## 2026-10-28 — R136实际视觉输入敏感性

[18点原件结果](m1a-x-input-sensitivity-results.md)：原RGB中心＋各自约1.7mm工程半径的预声明18点，全原IK／完整几何通过。原q6未重解、原jaw未硬写.5；默认诊断保留。9240采样／285对／244或246，不含自由物体接触或OMPL。净距证书是分离下界，按它选物理候选不等于找真实最危险方向；实际输入偏差已在下文R137主工位、R138第二放置工位分别原物理3/3通过，连续域仍未证明。

## 2026-10-28 — R137固定感知偏差原物理

[原3/3结果](m1a-x-input-bias-results.md)：原中点物体／盘位不动，两个固定RGB偏差与零偏差回归均完成原抓放、释放脱离回位。41次原定位只改xy、不累计；原1mm／285对／244或246与90sim120wall保留，控制不用truth。固定输入偏差不等于移动物体、整圆域或恢复率；第二放置工位同偏差现已完成下文R138原物理3/3。原reader误将async return可选项强制为必需，按原flag纠正，不弱化实际启动worker清理；首失败保留。全50Hz仍未过。

## 2026-10-28 — R138跨放置路径与全程腕余量

[第二放置工位原3/3](m1a-x-input-bias-results.md#r138第二放置工位)：同两个原RGB偏差，只换蓝盘(.20,.20)m，409项读回无失败／unknown；原抓放、完整扫掠、释放脱离回位全部通过。11921条20ms实际q6中最小腕余量约.838772°在运输，原R135名义和本轮零对照也同量级，不能以抓取端点余量替代全程，也不能只怪新增偏差。完整50Hz仍未过，普通合同／默认／连续域与20＋20不变。

M2接续只读核实（工作台6f532492快照）：Carry UI/API/原标记物理链已存在，原station-execution.cjs缺活动waiting后的resume/cancel点击分支。下一片扩现QA并做真实网页整链；不重造UI/API，不将静态准备冒充新通过，实施前复核共享树边界。
