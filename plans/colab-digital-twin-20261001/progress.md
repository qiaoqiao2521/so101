# Progress

## Current

2026-10-07 局部10mm查询静态负例完成：560个不合格pair对照误放0，但320个已证间隙>1mm对照误拒36个，存在+1.1mm→−3.045mm假穿透。冻结无漏报门控通过，距离可靠性仍未成立，生产接入暂缓。960证书/3840查询与独立手算FK核验完成，原模型、生产配置及安全阈值保持。下一候选改为独立凸包分离下界，尚未实施；完整jaw扫掠待修复，P2仍6/10，20＋20未运行，ACT暂停新增训练。 [本轮报告](../../experiments/colab-twin/output/visual-grasp-distance-controls-20261007/REPORT.md)。

## 2026-10-07 局部10mm负例完成，单独cap不足以修复距离

**Done：** 用户ok授权局部查询候选的有界静态贴阈值/接触/穿透对照。范围执行前冻结为960对照、3840query；原16q6/活动指爪网格/5种box、35迭代/tol1e-6、生产参数保持。所有证书及面选择先于首次查询，唯一矩阵3.171s完成，没有调参或查询重试。

独立几何审核用原编译参数手写FK，960/960证书有效；0 MuJoCo运动学/CCD。主查询16静态FK；全部forward/reset/积分/渲染0，训练/云端/硬件0。双序距离完全相同，不能将双序当作两套独立算法或独立样本。

**门控与精度：** 10mm危险误放0/560，但合格pair误拒36/320；100mm比较为0/560及256/320。精确1mm80对照单列，10mm放行68/80，100mm16/80。+1.1mm真距可返−3.044693mm，+0.5mm可返−5.328930mm；故冻结无漏报门控通过，不等于距离可靠。最贴近不合格间隙0.999mm，尚不证明任意近门槛无漏报。误差不作为物理穿透或跟踪补偿依据。

[完整报告与科学图](../../experiments/colab-twin/output/visual-grasp-distance-controls-20261007/REPORT.md)、独立证书与保存数组复算已落盘。67生产Python、原XML/4场景/13STL、旧物理结果及规范工作树25项保护保持；诊断产物继续Git忽略，仅现有4份SpecMesh串行同步。沿用Wiki按当前任务选择验收依据，静态指定pair对照不替代完整抓放。

**Remaining / Next：** 根Codex验证独立支持投影分离下界候选，明确原285对、近阈值数值边界、饱和零连线和20ms成本；尚未实施。10mm cap不单独接回生产，不改原1mm/0.2mm、native、抓取高度或下降端点。之后再补完整q6/jaw扫掠预检。P2仍6/10，P3 20正常＋20扰动NOT_RUN，ACT暂停新增训练。

## 2026-10-07 有界静态距离交叉验证完成

用户ok接续静态交叉核验。基线5fecb00，固定前次16个关键姿态、原285对碰撞几何，比较legacy/native及10/20/50/100mm诊断cap；生产flag/cap、原1mm机械臂/0.2mm持物/0.003rad偏置及20ms/2ms保持。原yaw回归继续2mm余量、jaw0.35rad、35次迭代/tol1e-6。没有积分/reset/渲染/训练/云端/实体或新物理回合。

独立参照使用原编译mesh凸包支持顶点与有限盒面；投影在面内时下界可实现，否则只给上下界。16姿态×5 pick箱体的80个活动指爪pair下界全部>1mm：16个floor精确模型证书、64壁对界；另2个native零值pair的面证书，共82对、18精确证书。原四报错pair与独立参照不符：dev-01 floor0.931→6.347763mm；dev-09 floor0.981→10.021287mm；dev-05 wall−1.842→下界10.157617mm；dev-07 floor0.654→10.098390mm。这是模型几何，不是实物标定，也不证明整条动作安全。原报错数值不能继续作为贴盘、穿盘或跟踪储备依据。

同输入cap对照：legacy四cap低于1mm姿态数0/0/0/6，native为2/7/13/15，分母均16。legacy局部10mm值得保留为下一候选，但只放行这组保存姿态，尚无贴阈值、接触或穿透负例，不能认定可靠或任务成功。cap是查询范围，原安全阈值不随cap改变。[同版本官方API边界](https://mujoco.readthedocs.io/en/3.3.7/APIreference/APIfunctions.html#mj-geomdistance)。

原15点yaw回归legacy15/15，native14/15；yaw−0.2142857142857144的lower_arm1/gripper0返回0，独立分离下界88.300193mm。+1µrad有限邻点另有base0/upperarm1假零值，分离下界50.695979mm。旧注释“五个wrist/jaw零值”模式未复现，不能混写；legacy稳定yaw距离也低于独立下界约88.317µm。两代表姿态各285对在kinematics→静态forward、memory flag→XML enable内存编译后距离和全部witness完全相同，排除这两类方法误用，不定位GJK/EPA唯一分支，也不推广其它版本。

[完整报告](../../experiments/colab-twin/output/visual-grasp-distance-crosscheck-20261007/REPORT.md)及[425项收尾复算](../../experiments/colab-twin/output/visual-grasp-distance-crosscheck-20261007/closeout-verification.json)保留证书、query/witness数组、原回归、内存fixture、方法来源及图表。四项实际报告合计43620次距离查询；独立几何参照0CCD，方法对照仅两次静态forward。67份顶层Python（含测试）、原XML/13STL、旧物理结果和规范工作树25保护路径保持。输出继续Git忽略，仅更新既有SpecMesh。采用Wiki按当前任务选择验收依据，不将模型静态证据扩为自由物体抓放和回位通过。

**Remaining / Next：** 根Codex执行局部10mm候选的有界贴阈值/接触/穿透负例验证，通过后再考虑接回完整q6/jaw扫掠预检。当前不改生产flag/cap/安全余量、抓取高度或下降端点，不以原异常距离重设跟踪补偿。原闭爪预检缺口和FK弯曲仍成立，修复未实施；P2仍6/10，20＋20未准入，ACT暂停新增训练。

## 2026-10-06 闭爪扫掠下降跟踪只读核验完成

用户要求检查夹爪闭合扫掠、下降路线和跟踪余量，保持原安全阈值。基线03a5cf1，原1mm机械臂/0.2mm持物余量、0.003rad偏置上限及20ms/2ms契约不变。没有生产修改、积分/reset/渲染、训练、云端或实体操作；P2仍6/10，P3仍not_run。

三个独立检查与根Codex整合完成：

- 8例进入close，24条固定q5扫掠共58224样本，另查2362条实际close行。dev-01保存down端点查询开4.852142/闭5.439730mm，但中间最小0.806306mm。源码只检查固定jaw的五轴段，未覆盖闭爪中间jaw；实际q6守卫仍在并保留原停机。
- 11构造下降、11支持lift、9实际换段参考共117141静态样本，最大五轴步长9.99938e-5rad，9保存参考重建误差0。dev-05最小原查询−1.841635mm、dev-07为0.653964mm，二者down端点不通过且未执行；旧dev-05的0.770161mm只是首拒绝点。FK构造下降的XY弯曲1.343848–1.449605mm，不能称末端垂直线。
- 3652保存行×4姿态=14608静态查询。dev-01/09终止拍固定实测jaw的臂跟踪查询差204.028/248.013µm；两点65细分没有移动界违例，但不能认证全程误差或真实距离。dev-09完整参考原查询超过1mm仅94.388µm。

独立距离一致性审查改变了归因边界：dev-01 jaw仅变0.0002rad，查询跳5.213211mm，14103个活动指爪顶点移动上界仅16.557µm；dev-09最大原同jaw查询差4.006840mm超过全285对几何移动上界583.102µm，同pair仍有4.167484mm跳变。当前native CCD被显式禁用，官方MuJoCo3.3.7 API提醒legacy距离不准确。[官方依据](https://mujoco.readthedocs.io/en/3.3.7/APIreference/APIfunctions.html#mj-geomdistance)。所以本轮扫掠“无效查询区间”不能直接宣称实际穿透，4.006840mm不能作为物理跟踪储备。

原pad/world异常及31输入完整保留，16负查询与分离AABB矛盾，标unsupported_metric，移出验收结论；未通过删异常或调整cap美化结果。独立诊断cap只用于同输入数值反例，生产cap与阈值不变。源中旧native CCD反例也保留，不直接改flag。

[完整报告](../../experiments/colab-twin/output/visual-grasp-clearance-audit-20261006/REPORT.md)、[独立收尾验证](../../experiments/colab-twin/output/visual-grasp-clearance-audit-20261006/closeout-verification.json)与可导出PNG/PDF保存输入/脚本绑定。根Codex350项无模拟器复算通过，67源/原模型、保存场景及规范工作树25个保护路径保持。只发布SpecMesh状态，全部结果/脚本/日志/图继续Git忽略。沿用Wiki按当前任务选择验收依据，静态一致性不替代自由物体抓放和完整释放。

**Remaining / Next：** 根Codex先做有界静态距离交叉验证，覆盖本轮跳变姿态、原终点与旧native CCD反例；然后才选择完整局部q6/jaw预检、有效抓取姿态/下降路线及跟踪储备。候选均未实施，不扩大OMPL维度、不修改原物理/安全判据、不再训练或重跑20＋20。单纯增加拒绝不能宣称抓放成功率提高。

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

## 2026-10-06 视觉定位通过，抓放整回合超时，按一次修正止损

**Done。** 2026-10-06 视觉定位主线已实现并实际核验：P0 20位置最大误差0.614mm，4类拒绝反例通过。P1基线因前臂遮挡停止；唯一修正改用机器人投影包络提前交接。修正版真实抬升40.9mm、持物30.68s并在蓝盘最终落稳，但撤回推块约40.4mm，90s时仍未完成回位，整回合失败。一次修正已用尽，P2和20+20均未运行。

新增RGB定位、仅编码器/视觉输入的控制器、独立物理runner及36项CPU测试。主模型与既有59份Python保持。初始布局/评分可读目标真值，控制器只有nq6规划rig，不接执行MjData或评分器输出。相机标定来自固定仿真参数，交接后采用静止目标假设，不能称全程视觉伺服。

[P0/P1报告与视频](../../experiments/colab-twin/output/visual-grasp-pilot-20261006/REPORT.md)保存逐拍接触、动作、RGB估计与源码哈希。原PhysicalTaskMonitor分项抓/放最终为true；首次物理通过79.80s，最终静稳11.20s。释放末固定指0.1651N，撤回峰值2.662N并推块40.4mm。撤回路径3.793rad按既有速度需23.707s，全程最低约100.11s。外层90s超时失败保持，没有改成通过。原安全停机0不意味着目标没有被再次接触。

**Stopped / Remaining / owner。** 本pilot已按一次修正上限停止。根Codex保留代码、失败视频与原物理判据。下一独立范围先审查释放脱离、估计物体包络和有界回位路线，并预计算完整时长；本轮不再修改控制、重跑物理或启动批次。ACT继续作为暂停新增训练的支线。

P0与两次P1运行合计48.887s；未耗尽30min预算。开发10例、冻结20+20未执行，不能报告批次成功率。原22项现场遗留（含业务/登录/串口配置及个人DOCX）、canonical索引、README和模型按25项哈希保护保留；这些材料尚无公开发布审查证据，不混入本次公开提交。后续owner仍为根Codex，接续入口为原HANDOFF及本节结果。实际产物继续Git忽略。

## 2026-10-06 方法审查完成，主线改为视觉定位与规划抓放

**Current / Done。** 2026-10-06 用户已选择稳定自主抓放主线：视觉定位→已有IK/OMPL→伺服抓放，ACT作为支线暂停新增训练。集中方法审查与CPU逐槽统计完成；尾槽h15/h0标准差约21–22倍成立，但L1输出梯度不按残差幅度放大，尚无唯一根因结论。现有专家含目标/载荷真值控制依赖，须先隔离再接视觉。新视觉控制器与物理验收尚未实施。 用户已确认路线，详见[方法审查与候选执行协议](method-review-20261006.md)与[D005](../../docs/DECISIONS.md#d005稳定自主抓放优先视觉定位与已有规划act转为支线)。

- 官方ACT网络源码与当前轻量训练配方分开：随机视觉主干/小模型/无VAE/残差统计及手写优化器均属当前实验选择，未证明成熟ACT不适用。
- [CPU动作尺度审核](../../experiments/colab-twin/output/vision-method-review-20261006/action-audit/REPORT.md)独立重建合法future slots：uniform h15/h0 std五轴22.2822/21.6649/21.6367/21.1013/20.8450，实际B5000约20.91–22.28倍。编码解码一致；标准差差异不是错一拍证据。L1非零残差的单输出梯度绝对值为1/N，不能把尺度比当参数梯度比；总loss不能替代h0质量。
- [数据/评价/工程接口审核](../../experiments/colab-twin/output/vision-method-review-20261006/evaluation-review.md)核对四相关示范、无独立验证选模、原门控为诊断，以及现专家目标/jaw/载荷真值依赖。后续须按采集家族/独立初态切分；工程主线不要求通过ACT逐动作拟合才能运行。
- 本轮0模型加载/前向/训练/GPU分配/新渲染/物理积分。学习/控制源码与既有权重不改；只新增CPU证据、方法与主线计划。

**Remaining / owner / 最短入口。** 根Codex下一入口是P0：验证场景topdown相机、标定平面与静态图像定位；之后将视觉估计接入抓放，并隔离物体真值控制旁路。候选pilot为定位→单回合→有限开发集→冻结20正常+20扰动，实际运行总预算30分钟、最多一轮定向修正；超时/失败如实停止，不缩小验收分母。ACT原门控仅诊断，历史失败保持；不恢复默认换图/加权/补训循环。 候选20位置定位误差≤2mm还不是抓取充分条件，IK/跟踪误差须计入总预算；20+20为以后冻结的任务验收，尚未运行。旧遗留/index/模型保留，原始审核产物继续Git忽略。

## 2026-10-06 Colab现有local-balance完成最终门控未过

**Current / Done。** 用户选择“现有local-balance”。新增云端CLI显式开关，默认A保持；worker在五步预检后仅fit透传，远端与回收两层核实际sampler模式。85项CPU测试通过，独立代码复核无阻断；两份学习源码不变。预置[范围](../../experiments/colab-twin/output/vision-colab-balance-preflight-20261006/scope.json)与[job对照](../../experiments/colab-twin/output/vision-colab-balance-preflight-20261006/prelaunch-comparison.json)固定四RGB、官方模型、归一化、FP32/batch8/seed0/fresh Adam1e-4、5000步/600s、2115诊断快照，仅local_balance false→true。

唯一Colab L4分配、一次fit；上传有一次PUT ReadTimeout，同分片原字节按既有规则重试恢复，未重分配或重训；五步CUDA/batch8资源检查通过。5000步/173.027871s优化，step_limit停止，peak reserved332MiB、CPU保存重载差0。worker耗时242.229s，控制器含传输与释放520.624s；原始权重/报告已校验回收，实际unassign完成。最终37a0ef24e088…，2115快照d2aa719a62dd…；不读取或推测Compute Units用量。[训练](../../experiments/colab-twin/output/vision-colab-balance-20261006/recovered/fit/report.json)、[回收与释放](../../experiments/colab-twin/output/vision-colab-balance-20261006/delivery.json)。

**原门控。** 两模型各150条nominal专家观测，合计300冻结CUDA前向，内部6.049s/外层7.981s。172项模型张量分别不变、59份Python/四RGB/模型哈希保持；原d4db门控基线与规范字节不变。B2115只失败首帧幅度：五轴比0.275534/0.445764/0.138850/0.171722/0.024803，方向均正确。最终B5000失败前四项：首帧pan/flex/roll反向，首10拍elbow投影0.481135<0.5；前150拍MAE/向量投影与jaw三项通过。相较A5000原3项失败增加为4项，不能用平均改善放行。

| 前150拍h0 MAE / mrad | A5000 | B2115诊断 | B5000最终 |
| --- | ---: | ---: | ---: |
| pan | 0.276773 | 0.223637 | 0.088468 |
| lift | 0.045201 | 0.143879 | 0.100889 |
| elbow | 0.095949 | 0.156083 | 0.436829 |
| flex | 0.726564 | 0.594621 | 0.123280 |
| roll | 0.340449 | 0.068325 | 0.084107 |

B5000相对A5000的h15五轴MAE均改善，但h0 lift/elbow变差；B自身2115→5000的elbow/roll h0误差及首帧方向退化，不能宣称长训单调改善。仅云端等步数对照，不混入旧本地B。[完整报告与图](../../experiments/colab-twin/output/vision-colab-balance-20261006/REPORT.md)、[最终](../../experiments/colab-twin/output/vision-colab-balance-20261006/offline/final-report.json)、[快照](../../experiments/colab-twin/output/vision-colab-balance-20261006/offline/step2115-report.json)。

**采样与独立复核。** 完整8997池局部槽155:155保持；5000步39988起点中raw<50命中1756次，局部起步/收尾696/693次，raw0/1各350/346次，有效动作槽11136/9965。A5000局部45/1344，非局部曝光一致；不能把完整池配比写成实际监督严格1:1。[独立CPU审核](../../experiments/colab-twin/output/vision-colab-balance-20261006/independent-review/report.json)1549断言通过，标量fsum指标重算最大差7.11e-14，重建A/B两级逐行曝光、原七项门控、数据/归一化/模型身份/源码与回收清单；该审核0模型加载/前向/GPU/训练/物理。

**Remaining / owner / 最短入口。** 采样旗标确实生效、起步两帧多次被采；没有证明唯一根因或采样普遍优劣，GPU同型号/单seed不保证跨实例逐位确定。S7e仍未通过，0新增物理/补训。根Codex保留云端A/B两级权重；下一最短候选是冻结B2115/B5000、固定q0替换真实起步/收尾RGB，核对起步回退是否伴随图像动作区分减弱。本轮未执行换图探针；不凭本轮增加步数、改采样权重/主干/损失或以快照替代最终候选。 原现场22项/index/顶层README/原MJCF保留，源码与报告同步canonical；产物、权重、日志继续Git排除。

## 2026-10-06 冻结云端模型起步收尾图像动作辨别

**Current / Done。** 用户指定先冻结新模型，检查起步/收尾RGB的动作辨别，再决定训练改动。[预置协议](../../experiments/colab-twin/output/vision-colab-image-discrimination-20261006/scope.json)固定同次Colab快照bd8749与最终ea548c、nominal raw0 q6、真实raw0/2349两图、原runner reset/execute1、FP32/batch1/no_grad/threads2。每模型6组交替，共24次前向；[唯一执行](../../experiments/colab-twin/output/vision-colab-image-discrimination-20261006/execution.json)exit0、内部4.266s/外层6.129s。没有新增训练、Colab分配、渲染或MuJoCo积分，不用诊断耗时作为50Hz证据。

两图203像素不同；实际q_end距q0为0.137024mrad L2。两个绝对专家h0目标重锚到q0后差6.000mrad。反事实q0+收尾RGB不是实际专家采样，不据此造新标签；raw2349为最后一帧，h1–h15无专家目标，仅记录换图的输出差。[真实RGB、动作对照与报告](../../experiments/colab-twin/output/vision-colab-image-discrimination-20261006/REPORT.md)。

| 固定q0检查 | 2115步快照 | 5000步最终 |
| --- | ---: | ---: |
| 换图h0五轴L2差 / µrad | 0.001599202 | 0.017197086 |
| 占6000µrad专家目标差 | 0.000026653% | 0.000286618% |
| 图像效应在专家目标差上的有符号投影 | -1.740063e-7 | 1.945534e-6 |
| 起步图输出距起步目标 / mrad | 6.627362 | 5.699520 |
| 起步图输出距收尾参考 / mrad | 1.205577 | 0.386042 |

最终两图下腕旋都反向、其他四轴起步幅度不足，jaw都投影open0.5、没有开闭切换。约10.75倍响应增长的绝对值仍很小，不能称已学会任务区分。起步图误差改善同时输出更近收尾参考；不等同网络完全不读图或采样是唯一根因。

每个模型172项state_dict张量前后哈希不变、无grad；59份生产/测试Python、9份输入（四RGB、一raw、两checkpoint、两旧预测）SHA保持。两个模型六次同图重复差0，起步RGB全chunk归一化/物理动作与对应旧保存首帧差0；固定q张量跨两模型/两图严格相同。[最终指标](../../experiments/colab-twin/output/vision-colab-image-discrimination-20261006/final-report.json)、[快照指标](../../experiments/colab-twin/output/vision-colab-image-discrimination-20261006/step2115-report.json)、[原始NPZ](../../experiments/colab-twin/output/vision-colab-image-discrimination-20261006/final-predictions.npz)。六次重复只用于确定数值稳定性，不是六个独立场景。

[独立CPU复核](../../experiments/colab-twin/output/vision-colab-image-discrimination-20261006/independent-review/report.json)263项通过，最大指标复算差8.88e-16，0模型加载/前向/GPU/物理。首次误用缺h5py的系统Python在导入时退出；改现有环境后发现CPU直接除255不能与CUDA逐bit比较（最大1ULP/5.96e-8）。修正为实测一致的float32倒数乘法、uint8回构差0后通过，只改独立审计假设，失败证据保留。最终h0归一化五轴差334/0/640/284/370 ULP，不能把微弱响应直接定为舍入噪声。

**Remaining / Next。** 下一训练变量选已有local-balance采样开关：与本轮A保持同Colab L4、5000步/600秒优化上限、2115诊断快照、四RGB、FP32/batch8/seed0/fresh Adam和原七项门控，仅开启近q真实起步/收尾1:1均衡。原B2115曾改善部分轴但肘轴退化，故这是等步数单变量验证，不是已证实修复。本轮未启动训练或改生产源码；执行前需在现有云端worker显式透传开关并验证默认A不变，不扩大预算或同时改主干/损失。 主线仍采用q6+RGB输入、原动作编码和物理标准；原七项门控未通过，物理not_run/S7e未过。根Codex负责接续，当前所有诊断脚本、数组、图和日志被Git忽略，仅公开结论。沿用Wiki“按当前任务选择验收依据”：这次交付局部辨别证据，不扩展为全局视觉能力或抓放成功。

## 2026-10-06 Colab L4完成5000步，原起步门控仍未通过

**范围与实现。** 最新用户要求“多用Colab CLI训练，进行下一步”，本轮明确采用原startup5、不启用local-balance，同四RGB、归一化、模型、batch8、FP32、seed0、随机初始化与fresh Adam1e-4。预置5000步或600秒优化先到即停，同run保存2115步；final policy.pt唯一候选，快照仅诊断，不挑快照替代失败最终权重。[预置范围](../../experiments/colab-twin/output/vision-colab-preflight-20261006/scope.json)、[网络恢复上限](../../experiments/colab-twin/output/vision-colab-preflight-20261006/transport-recovery-scope.json)、[代理范围](../../experiments/colab-twin/output/vision-colab-preflight-20261006/proxy-recovery-scope.json)均早于对应执行。

新增[run_vision_colab.py](../../experiments/colab-twin/run_vision_colab.py)与[remote_vision_worker.py](../../experiments/colab-twin/remote_vision_worker.py)：复用固定Colab CLI0.6.0安全层、独立会话和Python3.12环境、上传白名单及8MiB分片、逐文件SHA、原子回收索引与真实释放。分片幂等传输每片最多3次尝试（初次＋2重试），分配/训练不重试。控制器本次总预算30分钟，worker1200秒、fit外层660秒；默认runner仍120秒，只有fit显式extended-fit-budget最多600秒。没有修改网络结构、损失、采样器、精度或物理守卫。78项相关CPU测试通过，含预算边界、坏包/错SHA拒绝、传输失败释放和worker超时清理；测试完成不代表任务通过。[测试日志](../../experiments/colab-twin/output/vision-colab-preflight-20261006/cpu-tests.log)。

**网络与真实执行。** 第一次分配L4在第3片PUT遇ConnectTimeout，worker/训练未开始，实例已实际释放。第二次控制器在read-only check-connection失败，未分配实例。确认GNOME已有本机代理而进程无HTTP_PROXY/HTTPS_PROXY，第三次仅通过命令级代理执行成功；该次仍有一次上传和一次状态读取ReadTimeout，按有界规则恢复。总计3次控制器调用、2次实际分配、1次fit，无重复训练。不能由成功推出配额余额或网络唯一根因。[首次失败](../../experiments/colab-twin/output/vision-colab-startup5-20261006/delivery.json)、[分配前失败](../../experiments/colab-twin/output/vision-colab-startup5-recovery-20261006/delivery.json)、[成功与释放回执](../../experiments/colab-twin/output/vision-colab-startup5-proxy-20261006/delivery.json)。

四RGB原字节输入全部核验，官方LeRobot e0d50211及ACT源码SHA与本机固定版本一致；CUDA五步batch8预检通过。L4唯一fit最终5000步/171.179632s优化，因step_limit停止；worker安装至打包前241.279s，控制器含传输/释放约9分36秒，三者不是同一计时。峰值reserved332MiB、同CPU保存重载差0，实际39988个chunk起点/1105次起步命中。最终`ea548c3152a7539210828c715952683b2b6d30dfe40aa579192efb3be2e7c730`，2115快照`bd8749b8198e06cfa7c84e23bf855cd3330339288716f33ba764f112c5f7b48e`。Compute Units消耗未读取，不声称免费或扣除数值。[训练报告](../../experiments/colab-twin/output/vision-colab-startup5-proxy-20261006/recovered/fit/report.json)、[环境实证](../../experiments/colab-twin/output/vision-colab-startup5-proxy-20261006/recovered/imports.json)。

**原离线门控。** 严格加载本轮源码绑定的两模型，原门控规范字节保留；各150次batch1/no_grad本机CUDA前向，共300次/12.062s内部、15.628s外层，模型172张量/源码/四RGB在审计前后不变。只使用专家nominal raw0–149；0优化、渲染与物理积分。旧d4db保存数组仍为门控基线，没有以新云端快照改写阈值。首10拍方向错误从2115快照的14/50个轴观测降至最终1/50，但剩余错误在raw0腕旋。

| h0，前150条专家观测MAE / mrad | 2115步快照 | 5000步最终 |
| --- | ---: | ---: |
| shoulder_pan | 0.511566 | 0.276773 |
| shoulder_lift | 0.622766 | 0.045201 |
| elbow | 0.156705 | 0.095949 |
| wrist_flex | 1.163642 | 0.726564 |
| wrist_roll | 0.577296 | 0.340449 |

最终首帧五轴delta比依次为`0.080055 / 0.363609 / 0.208908 / 0.066753 / -0.006503`，其他四轴同向但不足原0.5下界，腕旋反向。原七项门控最终4项通过、3项失败；不能以平均改善代替首帧准入。h15各轴虽改善，但腕俯仰/腕旋MAE仍29.807/22.641mrad，不改用后部槽位执行。[完整报告与图](../../experiments/colab-twin/output/vision-colab-startup5-proxy-20261006/REPORT.md)、[原门控](../../experiments/colab-twin/output/vision-colab-startup5-proxy-20261006/offline-gate-spec.json)、[最终逐槽与切片](../../experiments/colab-twin/output/vision-colab-startup5-proxy-20261006/offline/final-report.json)、[快照](../../experiments/colab-twin/output/vision-colab-startup5-proxy-20261006/offline/step2115-report.json)。

[独立Codex CPU复核](../../experiments/colab-twin/output/vision-colab-startup5-proxy-20261006/independent-review/report.json)721项断言通过，重新计算切片与16槽指标最大差7.11e-14；核对数据/源码/回收清单/权重SHA并独立重建抽样。raw0/raw1最终作为起点出现25/20次、快照9/10次；不是完全未采。该审核0模型加载/前向/GPU/优化/物理，不能替代根审计的模型参数不变检查。

**Remaining / owner / 最短入口。** 同一run增加步数改善本轮局部拟合，但不证明图像语义或纯策略抓放；本地/云端2115数值不同，不声称跨设备逐位确定或唯一因果。最终门控失败，未追加训练/物理，S7e仍未过。根Codex下一候选先冻结5000步模型检查首帧近q起步/收尾动作辨别，再决定后续变量；未做。既有遗留22项/index/顶层README/原MJCF保持，runtime、权重、日志继续Git排除。未来训练优先Colab入口；本地准备数据、低成本审核与通过门控后的MuJoCo验收继续。

## 2026-10-06 startup5等2115步对照完成，原离线门控仍未通过

用户“赞成”后，按[预注册范围](../../experiments/colab-twin/output/vision-startup5-equal2115-20261006/scope.json)只新增A：原 `--startup-weight 5`、`local_balance=false`、随机初始化、seed0、fresh Adam1e-4、batch8、float32、threads2，最多2115步/120s优化/200epoch。若不足2115步就停止并标记对照未完成，不续训或重试；B复用既有490d9d71、无需再训练。本轮无论门控结果均不启动物理。

**前置只读审计已完成。** [肘轴逐槽与覆盖报告](../../experiments/colab-twin/output/vision-elbow-slot-audit-20261006/REPORT.md)确认B前150条h0肘误差全部偏正、90条反向；这90行均被采过，nominal raw0/1各141/150次。近q的366行在h0–h15所有有效肘标签均为负，不支持局部正负标签打架。完整池1:1起点、部分池抽样次数、future目标曝光和实际梯度必须分别描述；不改用h1或放大步长。

**资源与唯一训练。** 同两份视觉入口源码哈希绑定的[5步CUDA预检](../../experiments/colab-twin/output/vision-startup5-equal2115-20261006/microbenchmark/report.json)通过，batch8，peak allocated309.343/reserved332MiB。[A训练报告](../../experiments/colab-twin/output/vision-startup5-equal2115-20261006/fit/report.json)实际2115步、119.205101s优化、stop_reason=step_limit；含初始化/保存内部总124.045s，外层127.897s，后两者不当作优化预算超限。保存重载差0。A checkpoint SHA `fcb723af8c2c5000ef31e601f5f00ec613588b1576972ad4798ff950e334867a`，B仍为 `490d9d71eda07d69018fec736df3342beb1d8b45270770acf63dd4ba08abcc0e`。

同四档8797唯一valid归一化、8997采样池、chunk16与原模型/损失保持。两组均16917次chunk起点，但raw<50曝光A465/B737次，nominal raw0/1为A9/10、B141/150次；完整池末batch仅5行，16917不应写为2115×8。元数据核对数据/源码/模型/seed/初始化方案/优化器/步数一致；没有历史B初始张量和CUDA逐位确定性证据，不能声称除采样外所有执行过程逐位相同。

**同输入等步数结果。** A唯一150次batch1 CUDA/no_grad前向覆盖nominal raw0–149，内部6.739s；B使用原保存输出，未加载旧模型绕过源码绑定。五轴×16槽按同一专家观测及 `action[t+h]-q[t]` 标签比较；旧startup5的3126步结果仅作次级诊断。以下为首150观测h0 MAE，单位mrad：

| 轴 | A startup5 / 2115步 | B local-balance / 2115步 |
| --- | ---: | ---: |
| shoulder_pan | 0.098503 | 0.089926 |
| shoulder_lift | 0.104060 | 0.084447 |
| elbow | 0.206395 | 1.090709 |
| wrist_flex | 0.908849 | 0.432567 |
| wrist_roll | 0.247353 | 0.149180 |

A五轴h0同向率全100%，B除elbow40%外均100%；肘轴h15 MAE仍为A2.492832/B4.363806mrad。A肘拟合更好、B其余四轴h0误差更小，不能写成A全面胜出或B均衡采样已证明有害。相同步数下仍有差异，因而不能再单用少1011步解释B肘轴表现；单seed/历史运行和样本曝光差异限制仍在。完整[对比JSON](../../experiments/colab-twin/output/vision-startup5-equal2115-20261006/comparison-report.json)、[逐槽CSV](../../experiments/colab-twin/output/vision-startup5-equal2115-20261006/comparison-slots.csv)和[图](../../experiments/colab-twin/output/vision-startup5-equal2115-20261006/equal2115-comparison.png)均已保存。

**原门控仍失败。** [离线报告](../../experiments/colab-twin/output/vision-startup5-equal2115-20261006/offline-report.json)沿用[原7项规格](../../experiments/colab-twin/output/vision-startup5-equal2115-20261006/offline-gate-spec.json)，以d4db保存的batch8数组为基线，A/B比较不能替换该准入基线。A通过首帧/首10拍方向、前150整体投影和jaw open，共4项；失败如下：

- 首帧逐轴幅度：pan/lift/elbow/flex/roll的预测/专家比例为0.176/0.742/0.00686/0.159/0.080，只有lift位于原0.5–1.5区间。elbow虽同向，−0.006498mrad仅为专家−0.947236mrad的0.686%，不能称起步已修复。
- 首10拍逐轴投影：elbow0.380、wrist_roll0.472低于0.5，其余三轴在范围内。
- 首150逐轴MAE不劣化：wrist_flex0.908849mrad劣于d4db基线0.849739mrad。

`offline_gate_passed=false`、`rollout_allowed=false`，本轮物理not_run，不能记成抓放0/1。没有新渲染/积分、B补训、精度/阈值改动、40..59留出、云端或实体操作。

[独立Codex CPU审计](../../experiments/colab-twin/output/vision-startup5-equal2115-20261006/review/independent-result.json)646项通过：A/B共800行逐槽CSV×6项指标复算最大差0，核对4 raw/4 RGB、采样、七项门控、54源码和B权重/报告/预测未改；该审计0前向/优化/GPU/物理。采用既有Wiki“按当前任务选择验收依据”，实验执行完成不等于离线准入或抓放成功。全部新checkpoint、数组、日志、脚本与图保存在Git忽略的output，公开仅交付事实记录；owner根Codex，继续保留canonical现场22项/index/README/原MJCF。

**接续状态。** 等步数比较已完成，已消除旧3126与2115步数不一致这一项混杂；单seed加历史B仍不足以证明唯一因果或采样普遍优劣。前置肘轴逐槽/覆盖只读审计也已完成：不是完全漏采，近q邻域未发现肘轴正负标签竞争。root保留两份失败模型与原阈值；接续应据五轴逐槽误差选择下一项最小验证，尚未决定或执行新的训练。S7e仍未通过，本轮止于离线，不补训B3126、不改安全界限。

## 2026-10-06 真实近q局部1比1采样已实施，原离线方向门控未过

用户指定“真实起步/收尾近q帧局部1:1均衡采样、其余保持、先检验监督竞争”。[预注册范围](../../experiments/colab-twin/output/vision-local-balance-20261006/scope.json)和[原门控副本](../../experiments/colab-twin/output/vision-local-balance-20261006/offline-gate-spec.json)在训练前固化；final `policy.pt`为唯一验收候选，预算内3126步快照只作等步数诊断，不挑选候选。沿用Wiki“按当前任务选择验收依据”，将代码、离线预测与物理抓放分开验收。

**采样实现与验证。** 先在label_valid的8797行中，以nominal raw0 q6为锚、六轴未缩放L2≤0.01rad选真实行：raw<50且approach命中nominal0/1共2行；raw≥50且settle命中四档各75、共300行。64条近q retreat保持组外。保留原startup5采样池8997项及所有组外位置/值，局部原10/300项改成155/155；起步每池77/78次，收尾从300行无放回抽155。独立 `SeedSequence([seed,101])`只改局部，原基础采样和Torch RNG不被消耗。未修改或伪造q/RGB/动作；stage仅供离线采样，策略仍q6+RGB。

默认 `--local-balance=false` 保留旧分支；启用必须fit+startup-weight5。归一化在8797唯一行拟合，future chunk/padding及六轴L1损失保持。新增[15项CPU测试](../../experiments/colab-twin/test_local_balance_sampling.py)与原25项共[40项通过](../../experiments/colab-twin/output/vision-local-balance-20261006/cpu-tests.log)，含默认RNG、组外逐位保持、分组边界、实际计数、快照副本/预算。独立Codex源码评审通过，[实档5池核验](../../experiments/colab-twin/output/vision-local-balance-20261006/indices-report.json)通过；没有新AGY/ZCODE会审。

**唯一执行。** 新源码[五步CUDA预检](../../experiments/colab-twin/output/vision-local-balance-20261006/microbenchmark/report.json)batch8通过，内部3.969s/外层6.037s。沿原seed0、随机ACT/ResNet18、fresh Adam1e-4、batch8、120s/5000step/200epoch上限，[唯一fit](../../experiments/colab-twin/output/vision-local-balance-20261006/fit/report.json)实际2115step/120.032832s优化、内部总122.888s/外层124.893s，peak allocated309.343/reserved332MiB，同CPU重载误差0。原预算每次更新前检查，最后一个更新允许略越120s边界；没有延时补训。checkpoint SHA `490d9d71eda07d69018fec736df3342beb1d8b45270770acf63dd4ba08abcc0e`。3126快照 `not_reached`，不补做训练；实际步数不同，不能当严格等步数对照。

实际16917次chunk起点、737次raw<50；1完整池+第2池部分，局部起步291/收尾285次（两起步行141/150次），组外16341次。按被抽chunk起点所属组计非padding动作槽：起步4656/收尾4030/组外261456。1:1仅指完整池起点数；截断与回合末padding使实际次数及动作槽不等，动作槽也不等价于有效梯度。见fit记录和独立重建；8718个唯一chunk起点被抽到，不当成全部未来目标标签覆盖率。

**原离线门控。** [150次专家观测前向](../../experiments/colab-twin/output/vision-local-balance-20261006/offline-report.json)batch1/CUDA/no_grad/threads2，4.278s；四RGB/raw和172模型状态张量保持，未调用专家、渲染或积分。门控定义逐字沿用原协议，仍以旧d4db保存batch8数组为门控基线，旧8d4db保存batch1数组只作额外诊断；不绕过source binding加载旧权重。

| 首帧h0，mrad | 新策略delta | 专家delta | 方向 |
| --- | ---: | ---: | --- |
| shoulder_pan | +1.356358 | +2.317555 | 同向 |
| shoulder_lift | -1.244287 | -1.471036 | 同向 |
| elbow | +0.374473 | -0.947236 | 反向 |
| wrist_flex | -2.810959 | -4.805772 | 同向 |
| wrist_roll | -1.427544 | -2.510750 | 同向 |

首帧其他四轴比例0.585/0.846/0.585/0.569落入原0.5–1.5区间，但elbow比−0.395，前10拍elbow同向率0、投影−0.462；前150拍elbow同向率40%，MAE1.090709mrad，劣于原门控基线0.606118与最近startup5的0.559043。其余四轴前150同向率100%。整体方向投影0.98683好于门控基线0.95353、jaw全open，但不能覆盖坏轴：7项中5项未过（首帧方向/幅度、首10方向/幅度、逐轴MAE）。`rollout_allowed=false`，本轮物理 `not_run`，不是新抓放0/1。

[同q换图12次复核](../../experiments/colab-twin/output/vision-local-balance-20261006/rgb-report.json)原frame0 q6、原0/2349两RGB、原runner execute1/reset/no_grad，2.971s；同图重复差0、起步图预测与离线首帧逐位一致。五轴h0图像差4.429µrad（旧3.960），两图下肘轴仍反向、jaw都open；未形成所需动作切换。局部采样对比中预测发生变化，但没有等步数、多训练种子对照，不能把某轴变化或视觉表征确定为单一因果。总计162次离线前向、0新物理/渲染。

[独立Codex复算](../../experiments/colab-twin/output/vision-local-balance-20261006/independent-review.json)252项通过：独立重建采样、读取HDF/NPZ核标签与RGB、重算七项门控和换图差异；原数据/归一化/54源码/新旧checkpoint哈希一致。审核仅CPU，无构模/新前向/优化/仿真。v6无效前缀动作NaN按原契约同位置比较，有效标签全finite且精确相同。

**收尾与接续。** root保留默认均匀与原startup5行为；新局部均衡需显式 `fit --startup-weight 5 --local-balance`。本轮结果不支持仅靠局部起点均衡已解决起步/收尾辨别，且实际步数不同于旧3126，不能作等步数单变量因果结论。下一最短候选为只读核肘轴前150拍的逐槽拟合与局部抽样覆盖，区分早期输出偏差和覆盖变化；尚未执行，不自动追加训练、改主干或启动物理。 原物理/安全阈值、v11正常20/20和扰动3/20、旧视觉失败完整保留；所有runtime模型/数据/数组/日志继续Git忽略，公开只提交实现、测试与结论。主仓旧22项/index/README/原模型保持，根Codex串行整合交付。

## 2026-10-04 冻结模型逐层视觉响应探针

用户确认接续逐层探针；前置协议限定原8d4db/q0/同两RGB、最多12前向/硬60s、零训练/渲染/积分。实际唯一原runner序列为无hook A/B两次、hook A/B交替四对八次、移除hook后A/B两次；batch1/CUDA/float32/no_grad/threads2、每次reset/execute1保持。12次所有模型输入、完整chunk、raw及投影h0都与前轮保存基线逐位相同，8次hook的同图激活重复差0。

只在原模块forward上注册观察hook：对返回激活detach/clone保存、返回None，不替换模型输出；在原runner返回后转CPU落盘。捕获backbone feature_map、图像/关节/latent投影、encoder输入与位置嵌入/输出、decoder、action_head；没有添加第二次模型调用。每trial保存部分数组和实际计数，全部12次完成，进程exit0、内部耗时3.694s，外层硬60s未触发；该耗时包含激活捕获/压缩，不当作实时性能。

指标为同层对称relative L2：`2 ||B−A|| / (||A||+||B||)`；cosine distance与原norm/空间cell明细另存。不同层分母、尺度和投影不同，表中差异不能解释为逐层信息丢失比例或某一模块因果失效。

| 同层比较位置 | 单次激活shape | 起步/收尾相对L2差 | 同图重复最大差 |
| --- | --- | ---: | ---: |
| ResNet18 feature map | 1×512×4×4 | 3.577262% | 0 |
| 图像投影 | 1×256×4×4 | 3.595209% | 0 |
| encoder图像位置输出 | 16×256 | 0.998225% | 0 |
| encoder关节位置输出 | 1×256 | 0.494248% | 0 |
| decoder h0 | 256 | 0.059739% | 0 |
| 五轴h0归一化动作头 | 5 | 0.981892% | 0 |
| 五轴h0物理残差 | 5 | 0.397923%（实际L2差3.959955µrad） | 0 |

q6与归一化输入固定，encoder的latent/q输入token和position embeddings差0；图像投影展平后与encoder输入图像token逐位相同。encoder关节位置输出随图像变化，是self-attention混合后的输出，不属于输入q6变化；encoder图像位置输出也不再是单独的图像信息。主干每空间cell相对差2.9821–7.8686%、投影2.9126–7.9669%；宽感受野特征格不当作精确物体定位。53份顶层Python、6份输入与172模型张量保持，所有参数无grad。

独立548项CPU方法/结果复算通过：12输入/输出、9类激活重复、18token重组、32空间cell指标、53源码/6输入与172checkpoint张量哈希核验一致。运行模型前后保全依赖唯一执行脚本的before/after哈希断言，CPU独立核对checkpoint与保存前态，不新增模型/GPU调用。CPU直接除255与CUDA执行舍入差最多1ULP已记录；捕获RGB与旧CUDA输入、float32倒数乘法重构均逐位相同，未误判输入错误。另补jaw h0归一化差0.000400662、raw差89.688866µrad、投影仍open。

本轮支持：起步/收尾差异产生了非零主干及投影特征响应，h0动作响应仍弱；不能由3.6%认定语义可分、排除视觉瓶颈，也不能由decoder h0较小确认注意力或下游是唯一根因。首帧三轴反向、jaw open、原S7e未通过状态保持。零训练、EGL、积分、实体或云端操作。

下一单变量候选收敛为**真实起步/收尾近q帧的局部1:1配对均衡采样**。依据结合首帧邻域2 approach/64 retreat/300 settle及起点访问27/178/834，但起点访问不等于全部标签曝光/梯度，监督竞争仍是假设。候选要预先固定局部样本组、权重、与既有startup5规则的组合方式及实际draw统计；保持局部组的采样总权重、其余有效帧与组外优先级、原真实q/RGB/action、归一化、模型、chunk和损失，不把换图反事实改作同q伪专家标签；先检验局部监督，再决定是否需要视觉表征改动。候选未实施，不自动训练或增加探针。已有首帧/首10拍方向与步长、前150拍误差、夹爪open的完整离线门控仍为物理下发前置，不弱化成仅修一个轴或只看loss。

本机证据位于被Git排除的 [vision-layer-response-20261004](../../experiments/colab-twin/output/vision-layer-response-20261004/)：

- [scope.json](../../experiments/colab-twin/output/vision-layer-response-20261004/scope.json) 预先协议与源码/输入/现场哈希；[probe.py](../../experiments/colab-twin/output/vision-layer-response-20261004/probe.py) 唯一执行入口；[execution.json](../../experiments/colab-twin/output/vision-layer-response-20261004/execution.json) 实际12/8调用计数。
- [activations.npz](../../experiments/colab-twin/output/vision-layer-response-20261004/activations.npz) 实际各层输入/输出及12次动作；[report.json](../../experiments/colab-twin/output/vision-layer-response-20261004/report.json) 同层、空间cell与保全指标；[layer-response.png](../../experiments/colab-twin/output/vision-layer-response-20261004/layer-response.png) 图示。
- [method-review.json](../../experiments/colab-twin/output/vision-layer-response-20261004/method-review.json) 独立CPU方法与结果审计；本目录收尾文件记录同步/发布，不提交模型、图像、原始数据或运行日志。

实现依据：当前严格绑定的 `learning_vision.py` 原loader/runner，以及官方固定LeRobot ACT `modeling_act.py` 的backbone→投影→token混合→encoder→decoder→action_head路径；官方源码SHA `83d954f79ccd3eaa6774dbea92524939c8ac08359bb355ba7cd37b8601e1e3af`。沿用既有Wiki“按当前任务选择验收依据”，本轮只交付冻结层响应证据，不替代视觉语义、学习因果或物理抓放验收。

## 2026-10-04 固定q6起步收尾RGB反事实检查

用户指定固定q6、替换起步/收尾RGB，检查动作是否随图像切换。协议在前向前落盘：固定nominal frame0的原始float64 q6；只切换同相机frame0和2349的uint8 RGB；A/B交替6对，共12次实际前向。模型为已训练冻结的 `8d4db85e798f53aee2d63d59cd77e35f9ca9047450dfed99cc07ae157d224afd`，严格经当前源码绑定的 `load_visual_checkpoint` 加载，不使用旧d4db模型或放宽绑定。

执行保持原 `VisionPolicyRunner.predict` 的no_grad、CUDA/batch1/float32/threads2、q归一化、RGB CHW/255与动作逆归一化；每次reset、execute1，输出16槽并只执行层比较h0，无动作下发。包装器仅捕获原调用输入/返回，不另发第二次预测；所有trial归一化q6及解码锚点完全相同，不输入env、stage或time。

| 五轴 | 专家起步delta (mrad) | 起步RGB预测 (mrad) | 收尾RGB预测 (mrad) | 换图差：收尾−起步 (µrad) |
| --- | ---: | ---: | ---: | ---: |
| shoulder_pan | +2.317555 | -0.105538 | -0.106414 | -0.876371 |
| shoulder_lift | -1.471036 | -0.738442 | -0.735215 | +3.227529 |
| elbow | -0.947236 | -0.657571 | -0.658906 | -1.335434 |
| wrist_flex | -4.805772 | +0.053319 | +0.051717 | -1.602286 |
| wrist_roll | -2.510750 | +0.012467 | +0.012085 | -0.381535 |

- 6对h0五轴差L2均3.959954939µrad，最大轴3.227528736µrad；对应起步/收尾专家绝对目标L2差6.000mrad，图像效应为其0.065999%。同图各6次完整16槽归一化预测重复差0，原保存的同模型frame0 CUDA预测与本轮起步图输出也差0。
- 首帧pan/flex/roll在两图下都与起步专家反向。起步图预测五轴目标距起步标签6.038988mrad、距收尾标签0.413573mrad；收尾图分别为6.038219/0.413459mrad，仍近收尾动作。参考收尾标签重锚q0仅用于描述，原收尾q与q0相差0.137mrad，不把反事实观测当作新的专家可执行轨迹。
- raw jaw由0.493222840变为0.493312529rad（差89.688866µrad），训练支持投影均为open0.5，6对0次开闭切换。两图203像素变化、变化像素MAE23.31uint8；换的是全部RGB差异，不能单独归因方块区域或某个表征层。
- 实际进程exit0，探针内部耗时3.104s；软60s在调用间检查且不含imports，外层硬timeout70s，未触发任一上限。latency含额外输入CPU捕获，不用于推断真实50Hz。本轮仅12前向，0优化/训练/EGL渲染/物理积分/新抓放回合，53份顶层Python、5份输入源文件和172模型张量均不变。
- 独立CPU复算修正后333项通过。初版12项“CPU直接除255应与CUDA逐bit相同”检查未过，最大差5.96e-08/1ULP；捕获RGB与float32倒数乘法逐bit相同，原uint8重构一致，输入未错。修正审计假设和初次失败记录完整保留，未追加CUDA或模型调用；不宣传首次全部检查通过。

结论：这对图像对动作有微弱、稳定的局部影响，但没有引起所需的起步动作辨别；不确认全局视盲、视觉唯一根因或任何新抓放成功。S7e方向门控与视觉任务仍未通过；root下一改动未定，保留局部视觉辨别不足/收尾监督竞争候选及全部失败，不自动追加训练、改精度或推进仿真。

本机证据均在被Git忽略的 [vision-q0-rgb-counterfactual-20261004](../../experiments/colab-twin/output/vision-q0-rgb-counterfactual-20261004/)：

- [scope.json](../../experiments/colab-twin/output/vision-q0-rgb-counterfactual-20261004/scope.json) 前置协议、53源码与输入哈希；[probe.py](../../experiments/colab-twin/output/vision-q0-rgb-counterfactual-20261004/probe.py) 唯一执行入口。
- [report.json](../../experiments/colab-twin/output/vision-q0-rgb-counterfactual-20261004/report.json) 数值和边界；[predictions.npz](../../experiments/colab-twin/output/vision-q0-rgb-counterfactual-20261004/predictions.npz) 每次真实输入、16槽输出、raw/投影动作；[comparison.png](../../experiments/colab-twin/output/vision-q0-rgb-counterfactual-20261004/comparison.png) 换图和逐轴对照。
- [method-review.json](../../experiments/colab-twin/output/vision-q0-rgb-counterfactual-20261004/method-review.json) 独立CPU方法/结果复算，不增加模型前向；同步和发布保全由本目录收尾记录覆盖。

实现依据：[当前动作解码/图像变换](../../experiments/colab-twin/learning_vision.py)、同文件原runner与严格加载；官方LeRobot pinned revision仍为 `e0d50211ef236143ae867228662b7dfaba554f02`，`predict_action_chunk` 直接模型前向，不读取select_action队列。本轮采用既有Wiki“按当前任务选择验收依据”边界，只判静态图像响应，不扩大为物理抓放、实时或实体验收。

## Done

- 六份复制件校验 SHA256、Git ignore 和无索引记录。
- Colab CPU 会话分配与固定版本依赖安装成功。
- 17 文件的模型/脚本清单包上传；其中无个人文档或现场数据。
- `python3 experiments/colab-twin/run_colab.py --session so101-twin-final-20261001` 实际执行成功；MuJoCo 3.3.7/OSMesa，3000 步、6 秒、150 帧。
- 下载的 MP4 独立确认 640×480/25fps/150 帧并完整解码；CSV 150 行，全部数值有限、时间每 0.04 秒连续递增。
- 最大关节限位超出 0 rad；最大跟踪 RMSE 约 0.000575 rad。只代表合成轨迹物理基础实验，不代表碰撞自由规划或抓取。
- 四项资源清理失败路径测试通过；已有四项 teleop 回归、静态布局和前端语法检查通过。
- 本轮创建的全部 Colab CPU 会话均已释放；无 GPU 或真机操作。
- 两份历史修订 DOCX 和中期 Markdown 从远端副本保存在被忽略的 local-documents/prior-revisions，后续停止追踪，不重写历史。
- 完成本地 SO101 多工程/快照与有界历史核查；确认完整 MoveIt/RRTConnect 代码、缺失 MTC 源码和零字节逐轮证据。
- 实际调用 AGY 原生CLI单次只读咨询；采纳 MuJoCo + Python IK/OMPL 主方向。原始响应仅保留在被忽略的 local-documents。
- 整理 PROJECT / README / ARCHITECTURE / DECISIONS / 规划路线与现有计划，明确组件职责、复用资产、Gazebo/Colab边界和三步正反例验收。

## Remaining

S2/S3/S4全部完成：本地29项测试、真实Colab CPU20轮与可见视频回收均已通过。后续接触抓放、视觉与真机同步保持未完成。交付通过既有 master 非强制推送，版本由 Git 记录。

## Issues / Handoff

当前脏开发树使用旧 Git 基线，保留原状，在基于 origin/master 的隔离工作树完成本轮交付。已有工作区嵌套未出生 Git 与损坏历史备份保持不动。

根 Codex 接续范围：旧开发树与新远端基线的安全对齐；现场动作、串口配置、标定、登录/业务日志、录制和生成 ROS 导出保持本地。主从迟钝根因未实测，既有 `../teleop-latency-20260922/task_plan.md` 仍是恢复入口；不以本次离线仿真关闭该待办。

ROS/MES、Gazebo、真实 YOLO 与真机闭环保留原工作区任务状态；需要恢复时从 `../../workspaces/so101_ws/docs/任务清单.md` 进入，不重新宣布验收。

旧 `docs/HARDOFF_2026-06-26.md` 含明文 sudo/SSH 凭据及带凭据的历史命令，原件保留并精确忽略，不进入发布。根 Codex 未来如需复用，只从原件提取不含凭据、注明历史范围的结论；不复跑历史命令或恢复会话。

旧 `docs/SO101_MOTOR_TO_URDF_MAPPING_2026-06-27.md` 含现场舵机读数与临时映射，按项目“标定留本地”规则精确忽略并保留。其 wrist_roll 符号描述内部不一致，简化公式漏 scale；根 Codex 若恢复标定工作须核对当前源码与现场数据，不直接采用这份报告。其余两篇 Gazebo 历史报告已加历史边界，不作为当前运行验收。

MTC缺失核心和零字节逐轮产物留作待恢复历史，不从summary重造并冒充原件。根Codex从原生MJCF接续自主规划；规划与执行实例分开，碰撞检查必须覆盖路段。现场 `so101_gz_scene/{reality_map.yaml,calibration.yaml,calibration_report.txt}` 继续保留本机并精确忽略。

## Next

根Codex后续进入接触抓放、目标视觉或实体同步时，需要重新收敛任务验收；不把当前静态位置到达扩大为抓取/真机通过。主从迟钝待办继续保持，缺失MTC历史也保留恢复入口。

## 2026-10-01 接入实现

- 新增位置IK、五轴OMPL规划、派生碰撞场景、独立物理执行和公开障碍fixture；默认模式改为planning，原baseline保留。
- 本地29项测试通过；实际模型FK/IK、joint/ctrl交集、不可达拒绝、非相邻自碰/桌面/障碍、夹爪实际偏差、离散边中点碰撞、拒绝近似路径、错误目标执行失败、释放失败与种子溢出都覆盖。
- 第一次真实Colab：Python3.13.15 / MuJoCo3.3.7 / Mink1.1.0 / OMPL2.0.1 / OSMesa，主路径113点、7546物理步、15.092s、378帧。下载MP4独立解码378帧、640×480/25fps；CSV756行全部有限且时间连续。会话已释放且独立state删除。
- 20轮±3mm目标扰动均直接路径被挡，规划与物理执行20/20通过；均值0.545mm、p90 0.561 mm、最大0.589mm，主执行误差0.549mm，20ms碰撞检查无无效采样，关节超出0。平均规划时间约0.504s（仅本次CPU批次）。
- 有界不可达搜索返回unreachable、封闭场景invalid_start；独立有效起终点完全隔断测试拒绝OMPL approximate solution。
- 第一版画面未显示group3工作台/障碍，原始实验留存不覆盖；已加入group2零碰撞掩码可见副本，实际EGL预览与渲染scene测试通过，最终Colab20轮重新运行。
- 发布边界：上传包23个manifest条目+manifest；不含个人文档/标定/凭据/原始日志，所有文件hash核对；results.zip额外忽略，分次保存结果。
- 交付审查确认主工程939个未修改公开文件与delivery逐字一致，没有未理解的公开源码增量；旧Git index、嵌套历史及现场文件仍保持。同步本次已审查patch和新文件，不重置旧工程。

## 最终可见场景复验

- 命令：`python3 experiments/colab-twin/run_colab.py --session so101-planning-visible-20261001 --episodes 20`。实际成功；CPU/Python3.13.15/OSMesa，20/20自动绕障与物理执行通过，29项本地测试通过。
- 结果目录：`experiments/colab-twin/output/planning-20261001-053716-lzgpaif1/`（Git排除）。MP4完整解码378帧、640×480/25fps，CSV756行有限且时间递增，JSON逐轮20项均通过、直接路径均被挡，默认画面工作台/盒子已目视核查。
- 末端误差均值0.545mm、p90 0.561 mm、最大0.589mm，主执行0.549mm；规划均耗时0.510s。本次只覆盖单个静态障碍附近±3mm位置扰动。
- 最终bundle SHA256：`28689295fb99b69937124709e89c3bc647d42f6d75f1b80a3208711502c075ab`；manifest23个文件条目+manifest，自身哈希与上传源码一致，无个人/凭据数据。
- report SHA256：`ffefd2c8c02bfb27507e51b446c4d0d7d46a2ca4bd4b01941387f15ea677188c`；video SHA256：`4d0d4f66ff392eb2d72db9e64094d88924d5a3c699d5d7007f4ee119991594be`。
- 会话已释放；服务器查询没有活跃会话。主工程只应用本轮已审查patch并复制独立结果目录，保留其旧Git index和所有现场数据；交付从隔离worktree非强制推送至既有qiaoqiao2521/so101 master，提交号由Git记录。

本机README原有“唯一开发入口”和绝对路径说明保留在主工程；本轮只patch其实验段落，公开README沿用既有项目说明，不用发布副本覆盖本地入口。所有规划源码与测试在主工程和交付树逐字一致。

## 2026-10-01 主线逐层单回合接续

用户确认继续SO101 MuJoCo＋IK＋OMPL，并逐层通过后再继续。新增run_staged.py及三项阶段边界测试，复用现成环境（Python3.12.3、MuJoCo3.3.7、Mink1.1.0、OMPL2.0.1、NumPy2.5.3、imageio2.37.0）。没有模型训练、Colab分配或实体连接。

四层实际通过：依赖版本/导入；reset10步/0.02秒；直接插值被挡的113点IK/OMPL精确路径；独立位置伺服7546物理步/15.092秒。TCP误差0.549381679mm，20ms碰撞无效样本0，最大限位超出0。完整CSV756行有限、时间严格递增，末行TCP独立复算误差一致；视频378帧全量解码通过，工作台/盒子可见。32项回归检查通过；真实缺失依赖CLI负例停在第一层并保留后续not_run。动态重规划、抓放、视觉和真机仍未验收。

逐轮结果保存在本机被忽略的 experiments/colab-twin/output/staged-c5a0f2e203cf4453a7b501d6f8f4e62b/。最终候选代码与交付代码逐字一致；原始report SHA256 4ef35b169995ae9ef9db9dae1d929c4466f47863489ebdea90d6947ba5237c3c；MP4 SHA256 a41ef5e2bbcb2f9f77a4b9e9d43aa7322f8544a7d666395ce50d9b01cac9a885。渲染结果目录与既有批次隔离保留，视频/日志不入Git。

本次公开范围仅新入口/测试、README/PROJECT、实验说明与已有三份计划。按基线核验并保护canonical index和独立README入口；既有旧树/现场数据的接续责任继续归根Codex，沿用本文件Issues/Handoff。GR00T仍按用户“最后一次”保持停止；主线后续从此单回合入口进入，接触抓放/视觉/动态反馈需另行收敛验收。

## 2026-10-01 单臂夹取建模

用户指定先建模、改善场景，并纠正主从为现实系统；本轮只有一台从臂。找到本地BLD-001建模说明、主从场景生成器和动作模板；当前工程无其记载的Blender/GLB成品，LightArmPreview.vue与leader专属STL为零字节。复用完整的原生从臂13STL，新增grasp_workcell.py/preview_grasp_workcell.py及动态物体/夹爪检查。

新模型包含工作台、开放红/蓝料盘、相机支架、自由物体；生成1280×720三视图与100帧/4秒机械开合视频。原模型SHA仍d75253eb568e8a7214db9c631ab7bed4217f608a26f7276ebe9a7636cac82580。物体18×18×16mm、10g；实测中心z从0.012m落定至0.009784m，真实pick_floor接触。夹爪实际范围0.250019–0.799997rad，预览期间物体抬升约0；grasp_success/lift_success=null，尚未夹取成功。视频独立全量解码通过，34项回归检查通过。派生MJCF可编辑，原模型不改；无实体或云端操作。

结果保存在Git忽略的experiments/colab-twin/output/grasp-model-72f103318b2a4cf78c7b89f317ee53ed/。原场景建模说明只用于布局参考，仿真坐标和物理参数不当作实物标定；现场模板不复制发布。后续owner根Codex：先对位/接触建模，再以物体抬升与持续夹持验收；已有静态规划入口及遗留交接保留。

## 2026-10-01 加障碍夹取

新增grasp_episode.py及接触正反例。橙色障碍(.265,0,.065)m、半尺寸(.025,.028,.065)m；蓝盘上方→红盘上方的直接关节路径被挡，OMPL精确路径绕行，再下降/闭爪/抬升/保持。自由物体18×18×16mm、10g，无焊接/吸附/mocap；局部指尖接触垫与.15Nm夹爪力矩为仿真假设。原网格及原模型保留，sourceSHA不变。

本地实测抬升38.675mm，保持1.48s，两指持续正接触力且无底部支撑；逐2ms障碍接触0，20ms机械臂碰撞/限位无无效样本。38项测试通过，真实空夹负例拒绝。结果owner根Codex；放置释放、目标扰动批次、动态障碍反馈和真机验收仍待处理，GR00T不恢复云端尝试。

已回收本机忽略目录`experiments/colab-twin/output/grasp-1a87cf92da6f43498a3a7a1d7465bd56/`，953帧1280×720/25fps视频严格全量解码通过；1906条轨迹时间严格递增，保持段双指最小法向力分别1.972/1.971N，无底部支撑，最低抬升38.675mm。近景与绕行中段目视确认，原始模型SHA不变。

### 夹取可见性补充

原总览视频前约33秒物体保持盘底，抬升只出现在最后约4秒，广角与指尖遮挡使运动难以判断。新增固定近景grasp-closeup.mp4，只记录闭爪/抬升/保持。重新实际渲染的物理结果与原轮一致：38.675mm抬升、1.48s保持、逐步障碍接触0、20ms无无效姿态。261帧1280×720/25fps/10.44s近景严格全量解码通过，同机位抬升前后两帧目视确认物体离开料盘底，轨迹同步保存。输出位于被忽略的`experiments/colab-twin/output/grasp-closeup-8bc8e4fc3f9048ab92209fb01f2f182e/`；动作、接触假设及验收判据不变。

## 2026-10-01 搬运放置完成

新增placement.py、test_placement.py及--place入口，完整接续红盘抓起→竖直载物内侧绕障→蓝盘下降→松爪→撤离→落定。载物查询使用实测相对姿态和独立MjData，world碰撞间隙局部截断20mm，Cartesian3mm/关节边.01rad离散检查；执行方块仍为自由物体。Noslip10次解决原软接触约.5mm/s慢滑；夹爪保持.15Nm和原指尖接触垫，无焊接/动画附着。

41项测试通过；真实完整正例与noslip=0滑落停止负例均实际执行。最终中心(.238655524,.139143954,.009921450)m，距蓝盘中心1.6mm；全物体在蓝盘边界内，place_floor真实支撑，双指接触力0，平移速度3.66e-16m/s，撤离后稳定1.48s。途中双指持续接触、逐2ms障碍接触0、20ms机械臂碰撞/限位无无效样本。抬升段约40.777mm，物体在蓝盘释放后落定。

本机忽略目录`experiments/colab-twin/output/place-421c289686894ea6836e38fb04922a02/`保存派生MJCF、轨迹、报告、近景及全部视频。transport-place.mp4为972帧1280×720/25fps/38.88s，全量严格解码通过；总览也全量解码通过。固定镜头中段确认绿色方块在指尖绕障、红盘为空，最终近景确认蓝盘内方块与张开撤离的夹爪。原模型/index保持，不涉及云端GPU或实体。

下一步owner根Codex：按需求选择扰动批次或视觉输入；Noslip/摩擦/接触垫未经实物标定，固定内侧Cartesian路线不是通用动态障碍规划器。曾滑落失败的结果与部分轨迹仍留/tmp供诊断，关闭Noslip负例为稳定复现入口，执行损失接触≥100ms即停止。既有现场数据/旧树遗留继续按本计划保护与交接。

## S7 数据解耦、资源微基准与物理止损（2026-10-01）

用户以同一数据双探针收敛ACT/MLP分歧。实现learning_data/env/models/probe、train_state_policy、replay_learning_data、evaluate_state_policy、run_learning及独立边界测试。HDF5字段为state6/env30→absolute action6，另存实际executed_action、next_obs、时钟和invalid标签；固定2ms物理/20ms控制。专家用实际接触推进闭爪/释放；模型不接收阶段或时钟。原动作与状态保留float64，网络适配为float32；没有修改原MJCF/STL或已有规划环境。

采集共保留6次尝试（4成功、2失败）：首次float32正常采集因释放条件过严失败；修正后float32正常/恢复成功，空夹负例超时失败；raw64正常/恢复再次成功。最新分层入口选择raw64两正例＋保留空夹负例，共7887转换，其中6291训练候选、10扰动无效标签。恢复前真实执行±.02rad内的关节指令0.2s，再从实际q与物体位置重新IK/OMPL求解；第一纠正样本严格接续扰动结果。只有固定布局、起点扰动，未覆盖路线中段的误差分布，也未拟合DART噪声。

原float32回放：3133步物理抓放通过、关节误差1.91e-6rad、时间误差0；释放落盘附近角速度/接触力严格环境逐帧匹配失败，未放宽门槛。修正raw64存储与forward节拍后，独立回放与完整入口内回放均通过，state/env/time最大差全部0。

完整入口实际运行：`experiments/colab-twin/output/learning-gates-20261001/report.json`，退出码1，status=stopped。data、data_replay、resource、sanity_training通过；sanity_task失败；evaluation/vision=not_run。最新ACT五步compute0.10799s，allocated117.585MiB/reserved146MiB；MLP0.00569s、17.531/22MiB。RTX3050 Laptop物理4096MiB，CUDA可用区域3761.75MiB，两者分别记录。独立学习环境Torch2.7.1+cu126、NumPy2.2.6/h5py3.14.0，72包依赖检查通过；空环境cu126配方dry-run解析71包通过，上游默认cu128源需用--no-sources排除。

最新单轨迹ACT：3133帧，5000step、第26epoch、118.97s训练；chunk归一化L1=0.03301、首动作MAE=0.01085rad，GPU allocated117.585/reserved150MiB。权重SHA256 `2984659b93b016dfa9caf99f20633a592237a736fedbd026747d420edf71e8f5`；CPU重载最大预测差3.576e-7。仅正常单轨迹限时诊断，没有held-out或恢复训练，尚未完整过拟合。

纯策略回合只加载初始快照，所有控制由ACT输出，无IK/OMPL/stage/专家动作回退；0.36s后真实碰到障碍，SafetyStop按失败计数。并未将离线loss或资源通过写成抓放成功。第一轮原始档案模型同样0.52s碰撞停止。两次失败轨迹与权重都在ignored output保留，后续40回合及视觉无消耗。

可恢复交接owner为根Codex。最短入口：独立learning-venv运行LEARNING.md采集/回放/run_learning命令；当前checkpoint位于`output/learning-gates-20261001/sanity_training/policy.pt`。先检查开始几步预测与真实状态偏离、专家路径起步标签和接近段恢复覆盖，必要时追加一项有界诊断；不把下一步变成扩大GPU、批量长训或视觉。只通过数据回放不能证明策略泛化或实机可靠性。未完成的状态闭环在S7d保留明确失败门槛。

收尾验证：独立learning环境完整86项测试通过（含原规划/抓放真实正负例、数据精度与时序、chunk断点/归一化/重载、物理事件验收、假exit0止损）；Markdown相对链接和diff检查按提交范围验证。数据、权重、原始会审、日志与pip环境清单继续Git忽略。

旧树交接复核：canonical仍有22项tracked变动，包含322行app.py改动、静态界面、现场配置/录制/业务登录记录，以及个人文档迁出；旧HEAD/索引保持。HANDOFF/SECURITY解释主从计时及认证边界，teleop-latency计划明确等待硬件恢复。不能把现场日志/标定与个人原件提交到public远端；产品硬件参数验收仍缺，未用这次学习suite冒充。owner根Codex保留该树，最短恢复入口为plans/teleop-latency-20260922/task_plan.md、REPORT.md及mint_follower_demo/tests，用户恢复硬件任务前不驱动设备。已验证的仿真学习成果由独立delivery分支交付并同步可用源码，受保护树不重置、不清理、不覆盖。

## S7d 起步偏差与接近恢复（2026-10-01 接续）

用户要求先检查起步预测偏差和接近段恢复数据覆盖，再过一个纯策略抓放回合；本轮不启动20+20或视觉。实现CPU有界diagnose_state_policy.py，支持旧absolute与arm_delta checkpoint，起步1/16/50帧/逐阶段动作误差、速度归一化、保存在线前20步覆盖和有界近邻标签检查。报告保存模型/数据/源码hash与官方ACT来源；阶段仍只用于审计。

旧absolute首步pan/elbow/wrist错误约-.02448/-.01543/+.00988rad，下一拍速度pan/elbow约-1.178/-1.061rad/s；专家正常command-q只有几毫弧度。内部动作编码改为五轴arm_delta+absolute gripper，chunk未来目标均锚当前起点q，执行还原absolute；训练only qvel尺度下限.1rad/s，确定性noVAE/dropout0。默认absolute/原行为兼容，编码/归一化选项随checkpoint保存，官方ACT源不改。

首个5000step/82.81s候选：arm第一拍maxerror .000187rad，物理首动作MAE .001474rad（gripper占主要误差），GPUallocated87.05/reserved96MiB。但纯策略39.94s限位停止，物体仍留红盘；诊断发现gripper首command .50719，20拍actualq漂到.55210、qvel约.16rad/s，旧有恢复未覆盖这种偏离。该失败和权重保留，不因运行更久宣称通过。

采集v3专家：reference_route固定已通过路线，验证modelSHA/start/goal/wholepath；去掉学习端点固定等待，用下降几何触发闭爪、物体在蓝盘且z<.0145m时释放，无速度条件导致的反复闭爪。nominal＋startup±.006rad/20ms＋approach35%处+.002rad/20ms共4成功回合，12378frame/12375valid。扰动真实推进，保留非零速度，第一valid command是actualq制动，再从当前q/object重求IK并验证连接/剩余路径。startup首validpan速度+.263833/-.263756，approach+.047732rad/s；前一nextobs和第一validobs/state/env/time逐项一致。3项真实artifact测试全部通过无skip；独立v3startupplus原动作3061步state/env/time最大差全部0，抓放通过，无安全停止。

关键采样默认1兼容全量permutation；显式5倍覆盖每episode前50帧、invalid间隙后首6valid帧、jaw跳变附近±8帧，不跨episode/间隙且union不叠乘。v3四正例有界ACTfit：34509step/45epoch/600.002s，按wall上限停止，551748draw/12375unique，critical实际68204draw；dim256/chunk16模型3711494参数，allocated87.053/reserved96MiB。首动作MAE .000258rad，arm五轴MAE约.000019–.000105rad，gripper .001244rad；完整chunk归一化L1 .18112，未完整过拟合。权重 `output/state-delta-recovery-fit-20261001/policy.pt`。这些是四条固定布局训练轨迹的拟合，不是held-out或扰动恢复通过。

同权重默认首动作执行（每20ms重新推理）纯策略907周期/18.14s后腕关节axis3目标1.65816687超过1.65806上限，actualq1.65801771，未抓起物体。已增加SafetyStop的失败command/越界轴/时间诊断，不放宽限位。起步jaw .499759→.498278→.459505→.413686，qvel偏差放大；不是4GB OOM。报告位于ignored `output/policy-v3-baseline-20261001` 与 `v3-online-audit-20261001`。

`run_learning.py --sanity-only`明确只验一个回合，成功状态passed_single_episode_gate；默认仍保留完整入口。`--train-recovery`可显式纳入全部合格正例，负例只留审计；actionencoding/qvelfloor/VAE/dropout/weights/lr参数已转发。8项入口CPU边界测试通过。随后完成下述显式有界v4/v5训练诊断；单回合尚未通过，20+20/视觉保持未运行，owner根Codex。

### S7d 接续：反应式接近、策略前缀恢复与有界训练

v4只将approach改为actualq路径投影＋.006rad前视，每拍.005rad验边；后续下降/载物路线仍时间minimum-jerk。四专家正例9404帧/9401valid，起步前.38s arm位移L2 .153997rad。nominal2350步/startup-plus2351步独立raw64重放state/env/time差均0并完成抓放。产物：ignored `experiments/colab-twin/output/reactive-v4-{nominal,startup-plus,startup-minus,approach}-20261001/`、`reactive-v4-independent-replay-20261001/`及`reactive-v4-startup-plus-independent-replay-20261001/`（后两者同一output根）。

四档案ACT有界fit13491step/240.013s，输出`output/reactive-v4-state-fit-20261001/policy.pt`，权重SHA `d0142fecc159f3390a9cbeeb350ff83f0ab4518eab540e24480824fc7eb213d8`；归一化fit四份训练行。默认/chunk16/chunk16+nearest纯策略9.74/10.22/10.22s腕限位停止，无抬升；报告为同output根`policy-reactive-v4-{baseline,chunk16,chunk16-nearest}-20261001/`。同四档案MLP 8000step/8.234s，训练`reactive-v4-mlp-first-action-probe-20261001/`；纯策略`policy-reactive-v4-mlp-probe-20261001/`16.08s盘壁碰撞，`policy-reactive-v4-mlp-nearest-20261001/`9.92s桌面碰撞。均保留原权重/失败轨迹，不称通过。

v5采集只执行无接触策略前缀1/2/4/5s（50/100/200/250拍，20ms，最多250拍且≤5s），逐拍限位/碰撞/接触与command偏移检查后，以actualq制动、fresh IK接回参考路线。来源`output/policy-reactive-v4-chunk16-nearest-20261001/attempt-000-nominal/policy-transitions.npz`，SHA `20db559734f7ae635ed1e8a43c788ba294c693e3b4f4bdd2646b6cac8831e21e`；四正例`output/policy-recovery-v5-prefix{50,100,200,250}-20261001/`共9423帧/8823valid，600前缀帧全部排除训练。独立`output/policy-recovery-v5-independent-replay-20261001/report.json`2372步state/env/time差均0，真实抓放通过，3项artifact测试全部通过无skip。仅证明这些偏移后专家恢复及精确重放，不宣称完整DART或硬件可靠性。

八档案18224valid行在`output/policy-recovery-v5-state-fit-20261001/`以v4权重初始化，保持原四训练档案归一化，fresh Adam/new counters，lr2e-4；预算120s/7000step/200epoch，实际7000step/7epoch/109.024s。新权重SHA `26268fb563824fb0fe4268a46faa55e1b798b12386e550989b766ae8aba04472`，CPU重载差5.54e-8rad，allocated87.053/reserved96MiB。`output/policy-recovery-v5-baseline-20261001/report.json`10.48s腕目标越下限，无抬升/抓放；训练集拟合未提供held-out证据。可运行的采集/八档案接续模板与[官方ACT/DART引用](../../experiments/colab-twin/LEARNING.md)已补充；raw HDF5/NPZ/权重/日志均Git忽略。

离线定向探针固定q/其他env，只将六轴qvel由专家值替成在线值，转角腕target−q从+.002804变为-.004647rad（专家+.005230rad），`output/v5-qvel-causal-audit-20261001/`已归档。显式`--mask-robot-velocity`在训练/推理一致屏蔽归一化env[0:6]，原始数组/统计与实际动力学不改，有限性先拒绝，选项随checkpoint持久化、旧缺省false；初始化允许显式增加、不允许静默取消。入口透传两屏蔽标志及init-checkpoint，11项入口边界/透传测试通过；这不是当前整套测试或物理验收通过。

`output/policy-recovery-v5-qvel-masked-fit-20261001/`从v5权重26268初始化，同八档案、原四训练归一化继承、fresh Adam，3886step/4epoch/120.039s按wall上限停止，allocated87.053/reserved96MiB，输出SHA `08de5fc1d29ca6849b614f0fa5ed6b6852b1785c60af9e0be61f517eb00ccc24`。同output根`policy-recovery-v5-qvel-masked-baseline-20261001/`18.64s料盘底碰撞，无抬升；`policy-recovery-v5-qvel-masked-chunk8-nearest-20261001/`52s料盘底碰撞，无抬升；`policy-recovery-v5-qvel-masked-chunk16-nearest-20261001/`实际抓起并保持17.56s，35.2s在蓝盘外开爪、35.4s丢块，完整抓放失败。

`output/v5-qvel-masked-physical-audit-20261001/release-probe.json`在1760拍fresh chunk边界核对raw模型预测；实际姿态/其他env不动，仅将物体速度替为几何近邻训练值，jaw .401425→.017844，原始速度置零探针.018514。物体线/角速度归一化近邻差L2 105.745/134.035，4/6轴越训练范围；名义真释放反例零原始速度仍开爪。证据支持局部输入敏感性，不能以离线改输入宣称任务修复。

新增`--mask-object-velocity`只屏蔽归一化env[13:19]线速度3＋局部角速度3，与robot flag独立；训练/推理/保存重载共用适配器，旧默认false、初始化from/to明确，实际速度和物理监测保持。下一项同八档案、robot mask保持、额外object mask的有界fit及纯策略结果待根Codex填写；没有创建载物collector或新增数据。根Codex接续最终实验/整体验证，本节不预报完整单回合通过；20+20/视觉未运行，无新云端或实体动作。

### S7d 本轮止损与可恢复交接

双速度屏蔽ACT保持八训练档案、原四v4归一化统计和fresh Adam，lr2e-4；6657step/6epoch/120.017s后按wall上限停止，allocated87.053/reserved96MiB。权重SHA `84a4ef58d139be647a46f29c5be774325cd43e367ac89c3fa0f3d954c157e59d`，`output/policy-recovery-v5-all-velocity-masked-fit-20261001/`；chunk16+nearest在14.20s发生pick_floor与moving_jaw碰撞保护，未抬升。不是OOM，也未修改物理速度或接触/限位标准。该候选不替代已真实抓起的robot-only-mask候选。

同四v4数据、相同输入屏蔽和原统计的MLP CPU对照：37801step/65epoch/45.001s，`output/reactive-v4-all-velocity-masked-mlp-fit-20261001/`；nearest回合真实抓起并保持1.64s，15.92s actuator限位停止，完整抓放未通过。它是诊断对照，不是ACT资源失败后自动选择的新主线。仅限时拟合和平均误差不能证明局部控制精度与恢复泛化。

精确训练观察范围clip探针保留全部18224有效训练输入，但bad-release jaw .401425→.309138仍开，16项未来动作全开；不实现此adapter，不追加阈值猜测。来源`output/v5-qvel-masked-physical-audit-20261001/support-clamp-probe.json`。

归一化来源核对：robot-mask权重学过八档案，统计值实际逐项等于v4四档案。`output/policy-recovery-v5-qvel-masked-origin-verified-20261001/`仅更正来源归属，权重/统计/掩码逐项不变；保留原权重，未覆盖。初始化实现将权重训练来源与统计拟合来源分别保存，验证统计来源属于原训练集合。最终双maskcheckpoint明确记录四档案的统计来源。

当前单回合状态为**未通过**，S7d/S7e保持未完成；20+20、视觉、Colab/实体均未运行。最强物理候选仍是`output/policy-recovery-v5-qvel-masked-fit-20261001/policy.pt`＋chunk16＋nearest（八正例仅用于固定标签支持），真实grasp/17.56s hold后蓝盘外提前释放。模型评测无IK/OMPL/stage/专家兜底。

最短接续owner根Codex：先复核该候选在接近末端/载物搬运的实际状态覆盖，必要时单独采集一条真实偏差后的专家纠正，再过同一纯策略单回合。已提出但**未实现/未采集**的最薄载物入口为：从该候选NPZ前1000拍（20s）真实逐拍执行、全部排除训练标签；actual双指持续抬持门槛通过后，仅离线调用现有plan_transport生成纠正，独立raw64重放通过后才训练。不得恢复NPZ终点qpos、定时强开爪或将专家接管当作策略成功；现有approach前缀≤5s限制继续保留。该方向也需先验真，不能以增加预算替代覆盖证据。

最终完整150项测试通过，无跳过（40.177s）；包括真实规划/抓放正负例、四v5档案与独立重放绑定、遮罩/初始化/保存重载和单回合止损边界。日志`output/final-all-velocity-single-gate-tests-20261001.log`。默认旧absolute、全速度输入、单步执行保持兼容；本轮试验选项均显式记录。数据/权重/审计/log仍Git忽略。canonical现场22项tracked遗留按S7交接保留，根Codex不改变其旧索引/原模型或发布现场配置。

### S7d AGY 实际审核完成

按用户要求，实际AGY审查提交 `5c41ca0` 并引用本地源码及产物；原生会话 `11ef62ca-91ac-414d-b850-1a1b6225f170` 完整读回，与最终CLI正文一致。首轮超时空响应不算完成，一次无工具收束后才记完成。AGY和根Codex各独立执行3项真实恢复档案检查通过，本轮未重跑150全测、训练或物理回合。

AGY认可本次实现/记录边界，但完整策略抓放未通过；提出接近末端/持物实际偏差纠正覆盖不足。根Codex保留“起步覆盖充分”、速度唯一因果与按固定拍数滤波等分歧；四份旧统计合法继承不等于已证明漂移故障。具体引用、采用范围及未采用建议见[本次审核记录](learning-review.md#2026-10-01agy-对起步偏差与恢复采集的实际审核)。S7d/S7e状态不变；下一步owner根Codex，先覆盖证据再有界实验。

### S7d 接近末端与持物纠正初期记录（已被下文接续）

用户明确要求补齐纠正数据并重过纯策略单回合。根Codex在delivery树实现独立collect_policy_recovery.py，真实执行前缀后接管，前缀全invalid，首valid保持真实速度/状态连续；原grasp_episode前接触≤5s入口未扩大。接近末端用450拍（600拍已在低位闭爪，不按hover标注），持物用1700与1756拍；持物入场要求当下持续双指抬高≥25mm/≥1s。离线专家载物几何查询提取为placement helper，query-only，不操作真实执行qpos。

450入场加强版与1700/1756向前剩余路线纠正均实际抓放通过；各raw64独立重放核对后才进入新训练。初始1700回溯整条搬运路线也通过但不选择作新主训练，保留原产物；新held入口从当前Cartesian投影只连接剩余腿，避免向已完成路线反教。当前纯策略单回合仍未通过，训练/新策略验收待根Codex填写；20+20/视觉/硬件/云端均未启动。

### 2026-10-02 接近末端、持物及蓝盘边缘实际纠正

用户要求补齐实际偏差纠正后重过纯策略单回合。最终选择六份guarded新增档案：接近末端450拍、持物1700/1756拍、独立学习夹爪候选的1800拍、v7早期持物900拍、v8蓝盘接近corridor持物2500拍。六条共15989raw/6883valid/9106invalid；加原八份后14条共34816raw/25107valid/9709invalid。每份都从参考初态真实执行已保存的策略command，前缀expert标签NaN且全invalid；实际持续双指悬空持物才准入，首valid用actualq制动，速度/状态连续，没有恢复NPZ终点或附着物体。接管期间仅离线fresh IK/载物规划；模型评测不调用该入口。

六份专家纠正均完整抓放通过，各自raw64独立回放state/env/time最大差均0。载物下放的actual-to-target chord也检查自由物体的实测夹持占位；几何满足释放条件后不再假设物体刚性随爪。物理2ms/控制20ms、Noslip10、夹爪.15Nm、碰撞与关节限位全部保持。实际前缀与纠正各自≤60s、采集wall≤120s，前缀≤3000拍；原前接触≤250拍/5s入口不扩大。

实现新增`collect_policy_recovery.py`、学习状态夹爪组件及其独立训练。五轴ACT L1明确排除夹爪轴，官方可微model forward不改上游源码；裸arm-only checkpoint禁止执行，必须附学习夹爪。夹爪只读相同的归一化state6/env30，二次统计只拟合有效训练行；不接收阶段、时钟或几何开爪规则。训练夹爪时72个ACT状态张量逐项冻结不变，checkpoint保存完整组合，默认旧ACT/MLP训练入口兼容。

| 候选 | 纯策略实际结果 | 可引用产物（同一ignored output根） |
| --- | --- | --- |
| v6 full ACT（旧admission/forward数据） | 11.42s料盘底碰撞，无抓起 | `policy-correction-v6-single-20261001/report.json` |
| v6只训jaw输出行（旧数据） | 抓起并持物20.04s，37.88s盘外失物 | `policy-correction-v6-gripper-single-20261001/report.json` |
| 原ACT+11份guarded学习夹爪 | 持物20.10s，38.02s障碍碰撞 | `policy-correction-v6-classifier-single-20261001/report.json` |
| 11份guarded裸MLP | 12.94s料盘底碰撞，无抓起 | `policy-correction-v6-mlp-single-20261001/report.json` |
| v7五轴ACT+12份学习夹爪，chunk16 | 持物6.06s，完成22.54s后实际腕关节越限；command仍限内 | `policy-correction-v7-decoupled-single-20261002/report.json` |
| 同v7权重chunk8 / chunk1 | 11.82s料盘底碰撞 / 持物71.88s、90s超时，未放置 | `policy-correction-v7-decoupled-chunk{8,1}-single-20261002/report.json` |
| 原ACT+同v7学习夹爪 | 持物2.66s，21s盘外失物 | `policy-correction-v7-frozen-origin-classifier-single-20261002/report.json` |
| v8五轴ACT+13份学习夹爪，chunk16 | 持物60.42s并进入蓝盘范围；89.72s后蓝盘壁/夹爪0.8471mm间距保护停止，未释放/承托 | `policy-correction-v8-decoupled-single-20261002/report.json` |

这不是严格同数据模型消融：早期v6数据版本不同，v7/v8还同时改变数据与学习选项。只有v7三个执行窗口是同权重/同参考/同输入与固定标签支持的有界窗口对照。所有失败都保留原权重、实际command、逐拍诊断及报告。部分monitor的最后安全快照false不覆盖外层SafetyStop；安全停止一律任务失败。

独立CPU诊断未发现arm_delta chunk锚点错位。v7第900拍已实持1.52s，附近专家状态原本存在，但低速实际持物输入的动作缩小；只离线替换物体速度能改变预测，不能作为在线修复或唯一因果。新纠正因此覆盖actual-policy早期持物和之后的路线。v8第2500拍仍在蓝盘接近corridor、实持31.94s/抬高35.768mm；fresh纠正742valid，独立3242步回放差全0，才纳入第14条。

实现完整201项测试通过，无跳过，55.101s；日志`output/late-recovery-v7-final-tests-20261002.log`。这些是源码及绑定产物边界证据，不替代纯策略放置；这是release分支之前的历史测试；下文新212项覆盖最终源码。独立审计入口：`late-recovery-v7-independent-audit-20261002.json`、`late-recovery-v8-data-audit-20261002.json`、`late-recovery-v8-policy-audit-20261002.json`、`late-recovery-v9-data-audit-20261002.json`，均同ignored output根。

v9已完成：从v8 arm checkpoint `00da58926f51a1408f73f3b5dc4280a895c8ef90de080c21f4a9affef51bdcd5`初始化，保持原四份统计、robot-only mask，14档案、batch64/lr1e-5、优化循环目标≤120s，实际73step/120.152s，整次405.668s；组合夹爪后27.08s盘外失物，持物11.22s。独立采样重算：只覆盖4166/25107起点，但chunk标签并集23501/25107；不将起点覆盖混称为动作标签覆盖。GPU一时低频观测不证明失物的唯一原因。20+20/视觉/实体/云端未启动。

v9实际来源为`output/policy-correction-v9-arm-fit-20261002/report.json`、`policy-correction-v9-decoupled-fit-20261002/report.json`、`policy-correction-v9-decoupled-single-20261002/report.json`及`late-recovery-v9-policy-independent-audit-20261002.json`；精确argv为`policy-correction-v9-*-arguments-20261002.json`，14份数据清单`policy-correction-v9-training-datasets-20261002.json`。现场旧22项tracked遗留/index/原MJCF哈希保持，硬件Issues/Handoff仍由根Codex接续。


### 2026-10-02 末端释放纠正与纯策略单回合通过

v10在相同14档案上从v8五轴权重改用CPU有界接续，1201step/120.067s优化循环、144.551s全进程；固定初态纯策略抓起且进入蓝盘低位，但52.22s蓝盘左壁与夹爪间距0.9365mm触发原1mm保护。五轴权重SHA `b92adf12f9482467aa927aff1c71e8c94ae2cba6ed878b7743678b52abab57e6`；组合SHA `cb8f8774f7cb7a67c06a910ebe5684e39ff0b9042070088fcbd1d73b75f06d48`。失败与实测轨迹均保留，未降低安全阈值。低位状态重新推理仍预测闭爪，离线probe排除“缓存是唯一原因”，不作唯一因果证明。

从v10真实command执行2517拍，最早进入蓝盘内z=14.478mm且无地板支撑的状态；当前连续双指接触36.46s、历史实抬抓取通过。新增独立`release`离线模式，失去任一指接触或触地即重置当前接触计时；仅接受双指连续≥1s、盘内、10mm≤z<14.5mm、速度≤0.05m/s的安全状态。首valid为actual五轴制动＋开爪0.5，直接释放/承托/安全撤离/静置，不重新规划搬运。专家物理抓放与2914步raw64独立回放均通过，state/env/time差全0。2517步prefix全invalid且expert标签NaN，397条纠正valid；没有恢复NPZ终点qpos、额外沉降或附着物体。采集来源`output/policy-correction-v10-release2517-guarded-20261002/`，回放来源`policy-correction-v10-release2517-guarded-replay-20261002/`。

最终15份共37730raw/25504valid/12226invalid；七份本轮新增18903raw/7280valid/11623invalid，全部专家抓放与各自回放通过。清单`output/policy-correction-v11-training-datasets-20261002.json`。v11只训练独立状态夹爪8608参数，6000step/7.102s、全进程9.950s，CPU batch128/lr0.001/seed0/critical weight5；72个ACT状态张量和原四份归一化逐项保持。五轴ACT实际在14份数据上训练，夹爪在15份数据上训练，不能称官方完整ACT整体通过或ACT整体训练15份。组合checkpoint SHA `f50a14052b48ad1237024a63cebddec032686441be1149c33e4c8bc5d071a007`，位于`output/policy-correction-v11-release-classifier-fit-20261002/policy.pt`。

纯策略正式入口`output/policy-correction-v11-release-single-20261002/report.json`：completed_evaluation，固定初态一个正常回合1988控制拍/39.76s，实持23.10s，物体完全在蓝盘内、盘底支撑、双指释放且低速稳定1s；无安全停止/IK/OMPL/阶段/时钟输入/专家兜底。策略仅state6/env30，robot-only速度mask；chunk16固定当前锚点解码，nearest仅把学习夹爪浮点输出投影到训练标签0.015/0.5，并不读取几何或触发阶段开爪。此为有仿真真值的状态组合策略、同训练参考初态的单回合门槛，不是held-out、视觉、扰动恢复率或真机通过。

可见复验`output/policy-correction-v11-release-visible-20261002/`实际重新运行同一策略，渲染只读状态；全部1988步NPZ数组与逐步diagnostics和首轮完全相同，物理门槛再通过。`render-binding.json`保存checkpoint/两次report SHA与五项一致性；视频995帧/39.8s/25fps/1280×720，ffmpeg全量decode退出0，根Codex人工检查最终蓝盘物体和张爪细图。此复验仍同固定初态，不记作独立泛化批次。

最终源码回归212项/0skip/41.991s，actual exit0，绑定11份真实纠正HDF（旧四v5＋本轮七）与新release replay，前后源码hash相同；记录`output/late-recovery-v11-final-test-result-20261002.json`，精确参数`late-recovery-v11-final-test-arguments-20261002.json`，日志`late-recovery-v11-final-tests-20261002.log`。独立Codex审计`late-recovery-v11-independent-audit-20261002.json`核验数据、冻结权重、阶段隔离和实际落定；它不冒充AGY或ZCODE的新审核。完整汇总`output/late-recovery-single-gates-20261002/report.json`。

S7d-single已通过，S7d批次/S7e视觉继续未完成，20正常＋20扰动、视觉、实体与云端本轮未运行。接续owner根Codex：以本次组合权重与精确argv为基线，下一次先明确分回合/分种子评估范围与通过阈值，不能从1/1同初态提升为85%泛化成功率。权重、训练HDF、NPZ、视频、原始日志与审计只存ignored output；源码/公开文档同步并提交推送既有delivery分支。原现场22项旧变动与独立index/原模型均保留，既有硬件Issues/Handoff保持有效。


### 2026-10-02 S7d 40轮批次核验完成，门槛未通过

用户提供批次结果，根Codex回源实际产物核验，没有重跑40轮、采集或训练。checkpoint仍v11 `f50a14052b48ad1237024a63cebddec032686441be1149c33e4c8bc5d071a007`；[批次报告](../../experiments/colab-twin/output/policy-correction-v11-batch-20261002/report.json) SHA `ca487dd7ffd8e529834390c5ec467d2dbe7ae4e425bb1f732c010db97cc8f4bf`，[精确argv](../../experiments/colab-twin/output/policy-correction-v11-batch-evaluation-arguments-20261002.json)，原始日志及40轮NPZ/diagnostics继续ignored保存。

实际20正常/20扰动全部执行完，正常20/20、扰动3/20（seed20/25/31），双方≥17/20标准未达成。总体安全停止5/40=12.5%，超时8/40=20%，失物4/40=10%；若仅扰动组，分别为25%/40%/20%，分母必须注明。每次扰动实际从3.02s连续10拍/0.2s，五轴目标偏移≤0.02rad，无接触且未抬升；不是外力脉冲，也不保证实际joint displacement等于目标偏移。逐轮wall_s合计309.869s，不推断未记录的全进程耗时。

正常20轮使用同一训练reference/reset、确定性模型，seed只在perturbed时改变目标偏移；全部NPZ字段数组相同。因此只证明同初态可重复执行，不能表述为名义流形闭环稳定性或20种场景泛化。3个扰动方向实际恢复通过，不构成连续吸引域、任意方向或理论稳定性证明。沿用开发知识页“按当前任务选择验收依据”的已采纳原则：执行完成与验收通过分别记，不能扩大已观察范围；来源为Wiki/自动化开发范式与智能体协作.md。

最早失分集中于抓起之前：7个未抓取超时（23/26/27/30/32/38/39）＋4个pick_floor/活动指爪低于1mm余量停止（28/29/34/35），共11/17失败。余量停机不宣称实际碰撞穿透。seed33为place_wall_y_-1/夹爪0.998711mm余量停止，实际hold42.2s、放置仍false。seed21虽然hold74.12s，但终点物体(.18802,.14002,.04209)m未全进入蓝盘、无盘底支撑，不能认作低位待释放；学习策略也没有几何开爪条件门控。

[失物命令核对](../../experiments/colab-twin/output/v11-batch-lost-object-claim-check-20261002.json)：22/24/36在物体盘外高位且已实抓起后，于26.88/25.28/24.00s首次输出开爪0.5；37实抓起后没有开爪command。前3条优先检查学习夹爪在持物状态的误分类与监督覆盖，第4条再检查仍闭爪时的实际夹持/动力学；仅观察时序不能作为开爪单一因果验证，四轮不能笼统归因偏心滑脱。[独立40轮审计](../../experiments/colab-twin/output/v11-batch-independent-audit-20261002.json)16项汇总与40轮逐项核验全部一致，SHA `0e5bcee2706cb7ad42f9b53476079f8cda18892e5e5c68c213ee00951274d5da`。96041次有限command中96036步完成进入NPZ，5条安全失败command保留在各attempt last_command/failure_details；最后保存的安全物理快照不覆盖外层SafetyStop。核验来自独立Codex助手，不冒充新的AGY/ZCODE审核。

后续建议（尚未执行）：保持MuJoCo状态ACT五轴＋学习夹爪和原控制/安全约定，用已有grasp_episode短前接触prefix接口覆盖脉冲结束后的actual-state重新对准，用held离线入口补盘外持续持物闭爪标签。先选少量不同方向/失效类型，前缀保持invalid，专家从真实受扰状态重新求解；每条完整抓放与独立raw64回放通过后才纳入有界微调。此做法参考[DART原论文](https://proceedings.mlr.press/v78/laskey17a.html)的纠偏示范思路，未实现其噪声分布优化，不宣称完整算法复现。原20..39若用于训练则转为已见诊断集，正式复验另留未参与纠正的新扰动种子；旧正常基线检查退化。没有新增模型架构、GPU任务、实体或视觉。

当前S7d-single仍通过，S7d批次执行完成但任务门槛未通过，S7e未开始；owner根Codex。下一次需用户确定是否采用上述小批纠正＋有界微调方向；本次交付为统计复核、解释纠正及项目状态同步。40轮全部产物、17轮失败和v11权重保留，既有现场22项变动/index/原MJCF继续受保护。


### 2026-10-02 T1 持物防误开爪执行完成、候选未晋级

本轮仅执行用户先选的T1，未启动T2接近采集、T3五轴微调、T4批次或视觉。复用现有held离线采集器，真实执行旧v11失败回合的开爪前prefix，从实际持物位姿记录完整专家抓放；没有人工将失败切片改为成功档案。三个prefix全部NaN/invalid，首valid是actual五轴q制动＋闭爪`.015`，实际速度和观测时序连续保留。

| 已见seed / prefix | raw / valid / invalid | 专家完整抓放 | 独立raw64回放 |
| --- | --- | --- | --- |
| 22 / 1344拍 | 2437 / 1093 / 1344 | [通过](../../experiments/colab-twin/output/policy-correction-v12-t1-held-seed22-20261002/report.json) | [2437步通过](../../experiments/colab-twin/output/policy-correction-v12-t1-held-seed22-20261002-replay/report.json) |
| 24 / 1264拍 | 2431 / 1167 / 1264 | [通过](../../experiments/colab-twin/output/policy-correction-v12-t1-held-seed24-20261002/report.json) | [2431步通过](../../experiments/colab-twin/output/policy-correction-v12-t1-held-seed24-20261002-replay/report.json) |
| 36 / 1200拍 | 2299 / 1099 / 1200 | [通过](../../experiments/colab-twin/output/policy-correction-v12-t1-held-seed36-20261002/report.json) | [2299步通过](../../experiments/colab-twin/output/policy-correction-v12-t1-held-seed36-20261002-replay/report.json) |

三次state/env/time逐帧最大差均0，均`learned_policy_evaluated=false`。新3份7167raw/3359valid/3808invalid，加原15为[18份清单](../../experiments/colab-twin/output/policy-correction-v12-t1-training-datasets-20261002.json)、44897raw/28863valid/16034invalid。新valid只来自成功纠正，原policy prefix命令不作专家标签。边界是按旧float32 NPZ指令真实重执行的actual-state，不restore旧终点；相对旧保存观测有微小重执行差异，以新actual连续状态和raw64自身精确回放为准。

[精确训练参数](../../experiments/colab-twin/output/policy-correction-v12-t1-training-arguments-20261002.json)与[训练报告](../../experiments/colab-twin/output/policy-correction-v12-t1-gripper-fit-20261002/report.json)：从同一v10 arm `b92adf12f9482467aa927aff1c71e8c94ae2cba6ed878b7743678b52abab57e6`冻结72个ACT状态tensor，仍arm14/原四归一化/robot-only mask；夹爪8608参数从随机初始化、fresh Adam，仅用18成功档案拟合额外输入统计，CPU6000step/8.200103s（total11.291198s）。夹爪训练集chunk accuracy99.9478%、first-action99.9792%，范围仅训练行，不能当纯策略抓放或泛化成功。组合候选SHA `f2f87facc42d878652434f67252830550b3b2c58c9308da829a4744cd3802189`；没有继续训练五轴。

四轮均复用原reference reset、chunk16、固定训练标签nearest及原安全/成功阈值；策略只读state6/env30，不调用IK/OMPL/专家或stage/time，三次脉冲均3.02s实际注入10拍。精确[四轮argv](../../experiments/colab-twin/output/policy-correction-v12-t1-probe-arguments-20261002.json)保留。

| 回合 | 完整抓放 / 仿真时间 | 真实持物时长 | 结果与误开核对 |
| --- | --- | ---: | --- |
| seed22扰动 | [失败 / 18.12s](../../experiments/colab-twin/output/policy-correction-v12-t1-probe-seed22-20261002/report.json) | 1.10s | 17.94s盘外高位开爪，比旧26.88s更早8.94s；18.12s失物，无安全停止 |
| seed24扰动 | [失败 / 53.58s](../../experiments/colab-twin/output/policy-correction-v12-t1-probe-seed24-20261002/report.json) | 18.30s | 抓起后开爪命令0，仍在蓝盘y负壁/活动爪.996281mm触发原1mm保护；外层safety_stop计失败 |
| seed36扰动 | [失败 / 90.00s](../../experiments/colab-twin/output/policy-correction-v12-t1-probe-seed36-20261002/report.json) | 75.32s | 抓起后开爪命令0，物体已在蓝盘XY范围但z47.174mm、无盘底支撑，闭爪悬持直到仿真超时 |
| seed0正常 | [通过 / 48.40s](../../experiments/colab-twin/output/policy-correction-v12-t1-nominal-20261002/report.json) | 25.06s | 2420拍，释放后真实盘底支撑/零双指力/静稳1s，无安全停止；仅一次固定正常回归 |

[开爪与指令离线核对](../../experiments/colab-twin/output/v12-t1-opening-analysis-20261002.json)区分“盘外高位、当前双指接触且无支撑”的开爪与正常盘内释放；阈值仅用于审计，未进入在线策略。22的jaw指令首次与v11分叉在12.90s、arm在13.12s；虽然权重不变，夹爪改变实际接触后五轴轨迹也会改变。24/36在旧失物时点之后继续闭爪，表明这两轮早开未再出现，却不等于完成放置。22的新开爪前物体(.231762,-.131157,.055779)m、双指约1.397N；不能说T1已彻底消除误开，或宣称理论恢复率已提升。

新增[3项真实artifact测试](../../experiments/colab-twin/output/policy-correction-v12-t1-artifact-test-result-20261002.json)exit0/0skip，绑定新3份HDF及seed36独立回放；另外两份回放由实际报告和[独立Codex审计](../../experiments/colab-twin/output/v12-t1-independent-audit-20261002.json)核验。源码无变化，因此没有重跑全套212；旧212/11份绑定仍只证明当时范围。汇总及哈希见[本轮报告](../../experiments/colab-twin/output/v12-t1-gates-20261002/report.json)。数据、权重、日志、原始咨询和审计均被Git忽略，本节链接为本机证据。

结论：T1-data与冻结训练执行完成，但已见扰动抓放0/3、正常仅1/1；**T1任务目标未通过，v12不替代v11基线**。v11既有正常20/20、扰动3/20不变，不将两版混算新批次。Seeds40..59未读取、采集或执行；没有新的20+20/85%或视觉晋级证据。本轮独立助手均为Codex，不冒充新AGY/ZCODE审核。

最短接续owner根Codex：保留v11及全部新数据/失败候选，先在已见种子检查接近到抓起的开闭边界、盘壁接近及高位下降的actual-state标签覆盖；再单独启动T2/T3有界纠正和微调。不得靠延长本次90s、强开/强关爪规则或放宽1mm保护跳过门槛。T4先固定候选后才使用留出Seeds40..59，本轮不触碰该集合。


### 2026-10-02 最后一次A完成、首次正常探针失败，按用户决定转B

用户授权“再来一次机会，不行直接B”。A只执行一次五轴接续，不再重训夹爪。三条真实专家纠正均完成抓放，各独立raw64回放state/env/time最大差严格为0：

| 纠正 | 前缀 / raw / valid / invalid | 独立回放 |
| --- | --- | --- |
| v12 seed36盘内高位held | 2000 / 2587 / 587 / 2000 | [2587步通过](../../experiments/colab-twin/output/policy-correction-v13-last-a-held-seed36-20261002-replay/report.json) |
| v12 seed24安全高位held | 1660 / 2499 / 839 / 1660 | [2499步通过](../../experiments/colab-twin/output/policy-correction-v13-last-a-held-seed24-20261002-replay/report.json) |
| v11 seed23脉冲后无接触接近 | 161 / 2352 / 2191 / 161 | [2352步通过](../../experiments/colab-twin/output/policy-correction-v13-last-a-approach-seed23-20261002-replay/report.json) |

新增7438raw/3617valid/3821invalid；[21份实际训练清单](../../experiments/colab-twin/output/policy-correction-v13-last-a-training-datasets-20261002.json)共52335raw/32480valid/19855invalid。全部invalid前缀排除训练；held前缀专家标签NaN，原grasp_episode接近前缀保留有限动作但label_valid=false，同样不会学习。首valid保持真实速度与状态，以actual五轴q制动，随后重新解算专家纠正；无终点恢复或自由物体附着。

[唯一五轴训练](../../experiments/colab-twin/output/policy-correction-v13-last-a-arm-fit-20261002/report.json)从v10 `b92adf12…`初始化，fresh Adam、CPU batch64/lr1e-5，1262step/120.0608s优化循环、149.9137s总时间后停止；逐batch检查预算，不能称总进程严格120s。仅五轴动作损失，原四归一化和robot-only速度mask保持。72个ACT状态tensor中71个改变，共享主干允许随arm-only loss训练；这不是T1的72张量冻结。

新[compose_state_policy.py](../../experiments/colab-twin/compose_state_policy.py)显式组合新arm SHA `c8524aee…`与v11旧学习夹爪：新arm训练21档案，旧head仍15档案/原统计/原arm来源，六个head tensor逐项不变。合成SHA `5a9022d4…`；不将head出处改写为新arm全集，保存重载和组合预测严格一致。新增组合及相关训练测试29项通过；独立旧v11重载保持原权重/掩码/统计，不覆盖基线。

按首次失败停止，实际先执行[正常seed0](../../experiments/colab-twin/output/policy-correction-v13-last-a-nominal-20261002/report.json)：4500拍/90s，抓起并持物74.64s，却未释放落定，simulation_time_limit；无安全停止。终点物体(.205991,.122377,.037639)m已在蓝盘XY范围、仍双指悬持、无盘底支撑。仅能判断任务失败，不能据此证明arm唯一因果。已见扰动seeds23/24/36/22四个计划探针均not_run_after_first_failed_probe，20+20未启动、40..59未使用。

[独立Codex审计](../../experiments/colab-twin/output/v13-last-a-independent-audit-20261002.json)92项实际检查全true，SHA `c3a6c4350725d24b2a4338e7d3ec244a7357e9f4573abb280d45b4326adfd1ba`；审计通过仅说明证据一致，A任务失败。**A在此结束，按用户授权正式启动B**。v11状态基线20/20正常、3/20旧扰动保持，S7d整体仍未通过；不把转路线当作状态门槛晋级。

B先执行固定128×128相机RGB同步导出：原nominal2350转换全部渲染，EGL回放专家抓放通过，state/env/time逐帧差0；root实际查看0/587/1175/1762/2349五张sample，工作区完整，方块仅数个像素且接触时可能遮挡，接受有限资源诊断而非鲁棒性证明。图像在obs_t、执行command_t之前生成。实际报告和相机检查见[RGB导出](../../experiments/colab-twin/output/vision-b-rgb-20261002/report.json)与[camera-review](../../experiments/colab-twin/output/vision-b-rgb-20261002/camera-review.json)。后续资源/训练/纯策略结果在下一节填写；不连接实体或云端。


### 2026-10-02 B视觉首轮管线完成，纯策略抓放未通过

复用当前LeRobot ACT，小配置随机ResNet18（无下载/预训练）＋state6/RGB，完整六动作损失，不复用state策略的特权env30或阶段/时钟。RGB生产时的旧源码保留在ignored staging中；之后只修复资源/权重绑定，渲染/动作路径未变。导出、资源、训练与评测各自保存实际源码SHA，不将它们误写成全来自同一版本。

| 层级 | 实际结果 | 证据（本机ignored output） |
| --- | --- | --- |
| 同步RGB／原始动作物理回放 | 2350帧，EGL；state/env/time最大差0，专家完整抓放通过 | [export](../../experiments/colab-twin/output/vision-b-rgb-20261002/report.json)、[相机检查](../../experiments/colab-twin/output/vision-b-rgb-20261002/camera-review.json) |
| 本机CUDA五次反传 | batch8，5/5；allocated309.343MiB、reserved332MiB，总3.025s | [resource](../../experiments/colab-twin/output/vision-b-resource-20261002/report.json) |
| 唯一限时训练与保存重载 | 3438step／120.016s优化、122.731s总时间；同CPU设备推理重载误差0，15001542参数 | [fit](../../experiments/colab-twin/output/vision-b-fit-20261002/report.json) |
| 纯视觉策略同初态单回合 | **0/1，未实抓起、hold0、未放置**；完成3236拍/64.72s，下一个command推进至64.74s触发原1mm余量保护 | [evaluate](../../experiments/colab-twin/output/vision-b-nominal-20261002/report.json) |

B checkpoint SHA `cd298034a24fced617d2cd635acb89e4f3c46bcff451ef74fd53b2baeb4bd2c9`。模型只接收当前q6与RGB，chunk16每320ms重新推理；nearest仅映射训练两jaw值，没有几何开闭规则或IK/OMPL/专家介入。停止为蓝盘负y侧壁与活动指爪间距0.912153mm，不把保护停机说成已证实接触穿透。物体始终未抬升，终点(.239788,-.130018,.009921)m仍在红盘；不能把手臂走到蓝盘称搬运完成。安全失败command及其新状态在report保留，NPZ只保存3236个已完成的安全转换；最后monitor安全快照false不覆盖外层SafetyStop。

训练日志的L1采样为不同随机minibatch，不能直接当固定测试loss或宣称已近零过拟合。[九帧CPU离线探针](../../experiments/colab-twin/output/vision-b-nine-frame-diagnostic-20261002.json)只在专家训练观测上teacher-force：jaw9/9正确，五轴first-action平均MAE0.000723rad，起步两帧0.002281/0.002196rad；这不等于实际轨迹能抓起，也不证明模型已使用空间视觉。失败轨迹与探针仅提供下一步起步、接触前对准、图像遮挡及有效视觉特征检查入口，不作单一因果归因。

[B独立Codex审计](../../experiments/colab-twin/output/vision-b-independent-audit-20261002.json)81项实际证据检查全true，SHA `eafdd8ae3886ce6cd53c80c6337533ecaa4c3ee940a677efee7388ec0b7226d7`；覆盖原raw/RGB逐行、旧导出版本、新资源/训练源码、资源原文与权重、实际NPZ/失败command及CPU九帧诊断。它不冒充新AGY/ZCODE评审，审计通过也不修改任务失败。

新源码组合8项／视觉适配12项加入全套：[232 tests／0skip／47.896s、actual exit0](../../experiments/colab-twin/output/last-a-vision-b-final-test-result-20261002.json)，前后所有Python源码SHA一致。[精确测试参数](../../experiments/colab-twin/output/last-a-vision-b-final-test-arguments-20261002.json)绑定17份恢复HDF（旧11＋T1新3＋本轮A新3）与接近seed23新独立回放；原四份v4 nominal训练集不在这17个恢复绑定里，另有原物理回放和本轮RGB比对证据。接口/mock测试、真实数据回放、实际反传重载与纯策略物理门槛各自独立。

[本轮汇总](../../experiments/colab-twin/output/last-a-to-vision-b-gates-20261002/report.json) SHA `9c1f1ad5d01112c3db30d1a9edb340120326a539f70ea048bbc50404bf9a94e4`绑定A/B各层report、checkpoint与精确argv。**A结束，B数据→训练→仿真管线通过，但B纯视觉抓放未通过；S7d/S7e任务门槛均不改成passed。** 未追加第二次训练、未用40..59、未启动新的20+20，无实体或云端操作。

接续owner根Codex：保留原v11状态成功基线、全部纠正和B失败模型；下一步先针对固定首动作／接触前关键帧核对视觉动作偏差与RGB输入作用，再决定把已有成功恢复档案同步成RGB作小批接续。当前唯一nominal数据不作为未见恢复证据；本轮不自动加时长或降低安全判据。公开交付只含源码与文档，data/weight/log/审核/staging全部Git忽略；原现场22项/index/model仍受保护。


### 2026-10-02 B只读几何与RGB依赖诊断完成

本轮只核对冻结的B失败产物、专家档案与权重；没有新训练、物理step、rollout、RGB导出、GPU/云端/实体或留出40..59操作。根Codex[汇总](../../experiments/colab-twin/output/vision-b-diagnostics-20261002/report.json)绑定三项来源与52份未变Python源码。所有脚本、精确参数、图表和审计继续Git忽略；[接触前对齐图](../../experiments/colab-twin/output/vision-b-diagnostics-20261002/pregrasp-timing.png)仅绘制保存数组，两轨迹按各自首次闭爪命令对齐。

**几何与时序。** [FK审计](../../experiments/colab-twin/output/vision-b-pregrasp-audit-20261002/report.json)在独立查询数据上计算原q6的正向运动学，物体XYZ及接触力使用同拍已保存物理诊断，不重新模拟力。两次派生接触模型SHA相同。下列时间均相对reset，几何误差用同拍物体位置；IK参考点不是实际指垫中点：

| 指标 | 冻结B失败回合 | 成功专家nominal |
| --- | --- | --- |
| 首次闭爪command | 33.00s | 11.02s |
| 闭爪前IK参考点－物体XY差 | 4.4937mm | 0.00607mm |
| 闭爪前IK参考点世界Z | 21.8074mm | 19.7629mm |
| 固定指／活动指最大已保存法向力 | 27.3059N／0N | 1.4424N／1.6033N |
| 双指同时超过0.02N的已保存帧 | 0 | 1395 |

B固定指32.38s已有接触，早于33.00s闭爪命令；物体最低中心Z3.3148mm，未抬升。实际jaw首次<0.1rad在35.48s，此时IK参考点世界Z33.8578mm，双指力均0；35.92s首次<0.03rad时参考点已至42.9670mm。相反专家13.40s建立双指接触（当拍实际jaw0.1233rad），后续夹持时实际jaw约0.116rad，随后实抓起。<0.1是诊断阈值，不能作抓取成功判据；目标jaw0.015也不意味着持物时实际关节应达到0.015。

应修正“全程零接触夹空”解释：实际存在固定指接触及物体向下位移，但活动指始终无已保存接触力、未建立双指夹持；闭合与抬升配合值得优先检查。不能称成功抓取后滑脱，也不能单凭参考点三维距离断定唯一根因。[指垫方向审计](../../experiments/colab-twin/output/vision-b-pregrasp-audit-20261002/pad-direction-report.json)显示接触峰值时固定指几何位于物体上侧，但缺少保存的物体四元数、真实接触点和法向，不能进一步证明唯一施力方向或视觉/动力学单一因果。

**固定q6的RGB响应。** [CPU图像探针](../../experiments/colab-twin/output/vision-b-image-dependency-20261002/report.json)取12专家训练帧＋12失败稀疏帧（起步有重复，不是24个独立试验），比较原图/黑图/灰图/固定seed噪声/同场景异时刻图，96组counterfactual pairs。直接predict_action_chunk绕过runner缓存，17次CPU forward含重复/重载，计算1.663s、无优化器；相同CPU预测重载及重复误差0。专家550/551/567帧黑图使首jaw从闭变开，五轴整chunk平均绝对差约0.00454–0.00557rad；专家12帧黑图首jaw共5帧翻转，另2帧是释放时开→闭。实际失败12稀疏帧在四种替图下，首动作及完整16拍jaw类别均未翻转，黑图首动作五轴变化中位数仅5.526e-5rad；但frame2000整chunk五轴平均差0.012068rad，不能说模型完全忽略RGB。

[真实chunk刷新一致性](../../experiments/colab-twin/output/vision-b-image-dependency-20261002/rollout-refresh-consistency.json)中，9个刷新稀疏帧CPU首动作与旧CUDA保存值最大差五轴1.809e-7rad／jaw3.881e-6rad；非刷新帧重新计算的是假设新chunk，不是当时缓存执行动作。黑/灰/噪声属于分布外输入，异时刻真图也与固定q冲突且改变机器人外观，未隔离方块位置。因此可否定所测状态上的严格RGB输出独立性，不能证明方块定位、正确视觉伺服、强视觉依赖或恢复泛化。

**数据候选而非全量开训。** [21档案复核](../../experiments/colab-twin/output/vision-b-diagnostics-20261002/archive-review.json)共52335raw／32480valid／19855invalid，[原解析器准入](../../experiments/colab-twin/output/vision-b-diagnostics-20261002/archive-admission-check.json)全部合格、raw64及2ms/20ms一致；这是原成功记录与解析核对，不是本轮21份新物理零误差回放。21份初始物体XYZ均为(0.24,-0.13,0.00992145)m，许多held/release有效标签从抓起后才开始，不能直接弥补当前抓前失败或宣称多场景覆盖。

建议下一次仅做4份RGB小批：已有nominal2350；新增prefix50起步恢复2350raw/2300valid、v6-450接近下潜2406raw/1956valid、v13-seed23脉冲后接近2352raw/2191valid。总9458raw/8797valid/661invalid，新增RGB导出仅3份。选取理由是先覆盖起步、接近和下潜，不先堆持物/释放标签；这些来自旧状态策略偏差，尚未证明覆盖当前B实际闭合/抬升错误。每份新RGB仍须obs_t对齐、完整原raw64物理回放state/env/time差0、invalid前缀排除且chunk不跨无效段，按完整episode划分，不能把相邻帧当独立留出。此处仅形成候选清单，未导出或再训练；是否改善必须由下一次纯视觉单回合真实抓放判断。

本轮采用既有Wiki/自动化开发范式与智能体协作.md“按当前任务选择验收依据”：RGB输入敏感性、数据准入和实际抓放分别记证据。相关方法来源为[ACT论文](https://arxiv.org/abs/2304.13705)的视觉模仿/action chunking及[离线机器人示范学习研究](https://arxiv.org/abs/2108.03298)的数据质量与评估区分；它们不证明这份SO101候选已能定位或恢复。[独立Codex审计](../../experiments/colab-twin/output/vision-b-diagnostics-20261002/independent-audit.json)只核对本轮冻结产物/源码；[文档审计](../../experiments/colab-twin/output/vision-b-diagnostics-20261002/documentation-audit.json)另核五篇公开变动的链接与事实。两项均不冒充AGY/ZCODE新讨论。

B仍0/1、S7e任务未通过；v11既有20/20正常与3/20旧扰动保留，S7d未通过。生产Python与模型未变，因此未重跑上一轮232项实现/产物测试；本轮验证为真实离线探针、独立复核及文档链接/diff检查。接续owner根Codex：先上述小批RGB准入、有效接触前样本与闭合/抬升标签核对，再唯一有界训练和纯视觉单回合门槛；不预报成功率、不恢复A、不调整安全阈值。


### 2026-10-03 B四档案RGB闭环执行完成，纯视觉抓放仍未通过

用户授权三份新增EGL同步RGB、各独立raw64回放、四档案唯一120s训练与一个纯视觉正常回合。本轮全部按范围执行，没有第二次训练/rollout、留出40..59、云端或实体操作，生产Python52份前后哈希不变，旧B/v11权重和失败证据保留。[九阶段汇总](../../experiments/colab-twin/output/vision-b-pilot-gates-20261003/report.json)绑定实际退出、各层report、权重和几何；[精确argv](../../experiments/colab-twin/output/vision-b-pilot-gates-20261003/commands.json)与逐阶段execution/log全部Git忽略。专家回放通过、训练执行完成和学习任务通过分别记。

| 新增档案 | raw / valid / invalid | EGL同步RGB＋原raw64比对 | 独立原动作回放 |
| --- | --- | --- | --- |
| prefix50起步恢复 | 2350 / 2300 / 50 | [完整2350帧通过](../../experiments/colab-twin/output/vision-b-pilot-rgb-prefix50-20261003/report.json) | [2350步通过](../../experiments/colab-twin/output/vision-b-pilot-replay-prefix50-20261003/report.json) |
| v6-450接近下潜 | 2406 / 1956 / 450 | [完整2406帧通过](../../experiments/colab-twin/output/vision-b-pilot-rgb-v6-450-20261003/report.json) | [2406步通过](../../experiments/colab-twin/output/vision-b-pilot-replay-v6-450-20261003/report.json) |
| v13-seed23接近恢复 | 2352 / 2191 / 161 | [完整2352帧通过](../../experiments/colab-twin/output/vision-b-pilot-rgb-approach-seed23-20261003/report.json) | [2352步通过](../../experiments/colab-twin/output/vision-b-pilot-replay-approach-seed23-20261003/report.json) |

六次完整执行均actual exit0、专家实际抓放通过、state/env/time逐帧差0。新RGB复制原label_valid与NaN位置，prefix50/v13无效标签虽有限值仍排除，v6前缀NaN保持。原nominal为2350valid（不是2300）；四份合计9458raw/8797valid/661invalid。root检查每新档案quarter/half共6张样本，机位和布局一致、方块较小且接触附近仍有遮挡；[相机记录](../../experiments/colab-twin/output/vision-b-pilot-gates-20261003/camera-review.json)。[真实四RGB准入](../../experiments/colab-twin/output/vision-b-pilot-gates-20261003/visual-admission.json)逐个核8797起点的frame/episode连续性，chunk不跨无效段或回合。

[原HDF独立基线审计](../../experiments/colab-twin/output/vision-b-pilot-independent-20261003/baseline-audit.json)按严格接触前口径（排除首次产生任一指垫>0.02N的transition），四份659/609/211/500、共1979valid，占22.50%；只约nominal的3.003倍，不能称接触前4倍独立覆盖。含首次接触transition的obs_t则1983，口径不能混用；transport标签4680占53.20%。各档案仍同初始物体/场景，不作为多场景或独立视觉留出证据。

| 后续层级 | 实际结果 | 来源 |
| --- | --- | --- |
| 绑定四RGB的CUDA五次反传 | batch8、5/5、allocated309.3428MiB/reserved332MiB，总3.155s | [resource](../../experiments/colab-twin/output/vision-b-pilot-resource-20261003/report.json) |
| 唯一随机初始化ResNet18＋ACT/fresh Adam训练 | **1312step / 120.045s优化**，123.270s总时间；峰值allocated309.3433MiB/reserved332MiB；同CPU保存重载误差0 | [fit](../../experiments/colab-twin/output/vision-b-pilot-fit-20261003/report.json) |
| 冻结新权重后纯视觉单回合 | **0/1；4500拍/90s超时**，grasp=false/hold0/place=false，无安全停止；actual exit1 | [evaluate](../../experiments/colab-twin/output/vision-b-pilot-nominal-20261003/report.json) |

新checkpoint SHA `d4dbfc3e840637b1605148d19349f1bf324f9e071fc4064750952aa224d68509`，只读q6＋固定128×128RGB，env/stage/time及IK/OMPL不入策略。保留chunk16每320ms新推理、20ms控制、2ms物理及原1mm/限位/真实释放/1s落定标准。资源探针虽绑定四份哈希，5step抽合并前8行，只证明同形状反传显存；fit遍历/打乱四档案8797valid。旧fit report诊断文字仍写single train episode，实际是一次四档案训练、没有独立留出；不为文案修改生产源码使旧权重失去绑定入口。

[20ms逐拍FK与接触时序审计](../../experiments/colab-twin/output/vision-b-pilot-pregrasp-20261003/report.json)实际exit0/2.840s，25输入哈希保持，三份派生机器人几何一致，physics/render/推理/训练均0：

| 离线诊断 | 新四档案B | 旧单档案B | 成功专家 |
| --- | --- | --- | --- |
| 首次闭爪command，elapsed | **67.20s** | 33.00s | 11.02s |
| 动作前IK参考点－物体XY差 | **19.9447mm** | 4.4937mm | 0.00607mm |
| 双指同时>0.02N观测帧 | **0** | 0 | 1395 |
| 升高≥1mm持续≥0.1s的离线事件 | 70.10s | 34.26s | 13.86s |

新B全4500拍固定/活动指力均严格0，物体中心Z始终约9.92145mm，未实抬升；因此未记录到指尖接触且未形成实际抓取，不能沿用旧B单指接触解释。首次close动作后参考点Z29.705mm、夹爪仍约0.4994rad；70.10s离线升高时jaw0.13557rad且双指力0，jaw<0.1rad在70.32s、<0.03rad在70.76s（参考点Z31.5915mm）。专家先13.40s双指接触，再13.86s升高，相差0.46s；新B没有双指事件，不能构造“接触后抬升”的时间差。

pick原始XY20mm窗口内最低参考点68.52s/Z24.1883mm，全局最低68.30s/Z24.1704mm，窗口边缘差仅0.0179mm；全程最近XY4.3127mm发生在75.88s，但参考点Z已73.6538mm，不能当抓取对准。升高阈值和连续双指0.2s仅是离线诊断，参考点不是pad中点；20ms保存观测不是2ms接触实测。力单位N而非力矩，也未记录真实接触法向的世界分量。11–13s闭爪时间不是强制规则或独立任务通过条件。

本轮数据/归一化/抽样访问和训练步数同时变化，旧B3438step与新1312step均是各自120s优化，不能把退化唯一归因数据或架构；不同minibatch loss也不是固定验证误差。前轮RGB替图响应只绑定旧`cd298…`权重，新`d4db…`没有再做该探针，不能移植成新模型已使用对象视觉或已定位。[独立Codex本轮审计](../../experiments/colab-twin/output/vision-b-pilot-independent-20261003/report.json)核各层冻结产物及公开文档，不冒充AGY/ZCODE新讨论。

**数据/资源/训练执行完成，纯视觉抓放仍未通过。** v11正常20/20与旧扰动3/20保留，S7d/S7e整体未通过；没有把无安全停止或新数据准入当成功。原232项实现/产物测试来源仍只覆盖原范围，生产源码未改，因此本轮未重复跑全套；验证为新HDF准入、六次完整专家回放、五步资源、实际训练重载、唯一物理回合、离线几何及独立审计。采用既有Wiki“按当前任务选择验收依据”的范围区分。

接续owner根Codex：本轮停止追加训练/采集/rollout，保存全部新RGB、权重、超时及逐拍证据。下一建议先离线检查固定专家/实际观测的动作拟合误差、相近观测是否存在监督冲突与低位对准覆盖，再决定优化预算/数据/模型的单项改动；建议尚未执行，不凭这次失败承诺视觉天然更容易纠偏或自动扩大训练。全部runtime继续Git忽略，原现场22项/index/README/原MJCF不变。

### 2026-10-03 B四档案离线拟合与监督一致性诊断完成

用户授权四档案接触前动作拟合、低位监督覆盖与相近输入标签一致性离线切片。本轮冻结新d4db与旧cd298权重，未追加优化/采集/物理回合/渲染/云端/实体/留出40..59；原B0/1、S7d/S7e整体未通过事实不变。沿用既有Wiki“按当前任务选择验收依据”：数据重构、输入近邻检查和学习任务完成分开。

**拟合与闭爪。** [完整重构报告](../../experiments/colab-twin/output/vision-b-offline-fit-20261003/report.json)实际exit0、内部77.293s/含启动79.687s，CUDA峰值allocated91.705/reserved124MiB；新8797全部有效chunk起点/旧原2350起点，batch8，模型及缓冲哈希保持，生产Python52份未变。新/旧batch与singleton normalized差分别6.68e-6/7.44e-5；只用q6/RGB，action真值仅作比较，不进入predict。每一有效chunk严格按起点q共同解码五轴残差，jaw保持绝对目标；padding/invalid/档案边界保留。

[固定切片](../../experiments/colab-twin/output/vision-b-offline-fit-20261003/slices.json)按独立episode/frame masks连接，angular MAE单位mrad（1e-3rad），不是Cartesian精度。下表旧/新均同nominal专家观测，完整chunk只统计有效future槽，hold基线在全部槽保持chunk-start q：

| 同nominal切片 | 帧数 | 旧五轴全chunk MAE | 新五轴全chunk MAE | hold基线 |
| --- | --- | --- | --- | --- |
| 全有效观测 | 2350 | 1.7765 | 6.3828 | 10.6723 |
| 严格接触前 | 659 | 2.6722 | 11.2131 | 18.1097 |
| 接触前Z0–30mm/XY≤20mm | 135 | 0.4696 | 0.8293 | 1.5337 |
| 首次闭爪至首次接触（含产生接触transition） | 109 | 0.1805 | 0.3977 | 0.2461 |

四档案严格接触前1979起点：新五轴当拍.5436mrad/全chunk9.7937mrad，对照hold1.4430/15.9632mrad；有学习收益但未充分复现全部动作。首次闭爪至接触436观测全部预测closed；该窗口新五轴当拍.2860/全chunk.3997mrad，比hold.1873/.2499差。raw jaw误差与投影分类分别记录，不把类别正确当实际夹持。低位539起点中的432closed全命中，107open却56预测提前closed；不能说夹爪毫无误差。

nominal逐专家观测h0扫描在**10.74s**首预测closed（专家11.02s/旧扫描10.84s），它不是运行中的首次闭爪；线上67.20s仍为前轮原物理记录。新模型在示范观测没有晚闭爪漏判，不能从实际迟滞直接断定训练标签没学会，也不能据此确认方块视觉定位。

**后部chunk。** [图与原数据](../../experiments/colab-twin/output/vision-b-offline-fit-20261003/offline-fit.png)、[目标方向投影](../../experiments/colab-twin/output/vision-b-offline-fit-20261003/directional-progress.json)只重算保存数组，没有新模型推理。同nominal接触前：新h0五轴MAE.5665mrad、h15为25.9349mrad（旧.2075/10.5571）；专家目标位移范数≥.001rad时，预测目标位移在专家方向的投影比例中位h0=.9632、h7=.4110、h15=.2002（旧.9898/.9853/.6929）。这是目标命令的统计，不是实际速度，也不能单独解释6倍运行延迟；但明确支持优先检查执行chunk后部。

**覆盖与冲突。** [独立覆盖/FK报告](../../experiments/colab-twin/output/vision-b-offline-coverage-20261003/report.json)仅mj_kinematics9458次，真实物理step0；[coverage/masks](../../experiments/colab-twin/output/vision-b-offline-coverage-20261003/coverage.json)严格排除首次产生任一pad>.02N的transition。用户Z30–80mm/XY≤40mm只384valid，全open；补Z0–30mm539valid（432closed），覆盖专家首次闭爪约Z19.8mm。合Z0–80mm923，不能把8797帧说成独立抓前样本。

[跨档完整观测近邻](../../experiments/colab-twin/output/vision-b-offline-coverage-20261003/supplement-consistency.json)取跨档双向q6 L∞最近邻去重，q6≤.002rad且RGB全图MAE≤.5/255，1270对/880不同源帧（高度相关）；648涉及closed的近邻当拍/未来jaw均无分歧，五轴delta cos最低.9808/最大当拍delta差.0942mrad。最大分歧集中nominal descend与v6 frame452 approach交界：当拍delta差3.201mrad、未来16拍19.758mrad、qvel差.0604rad/s；速度未输入策略。没有完全相同q6+RGB跨档输入，近邻局部差异不证明不可辨识或普遍冲突。

[局部图块敏感性](../../experiments/colab-twin/output/vision-b-offline-coverage-20261003/tile-sensitivity.json)揭示全图MAE会掩盖局部像素差；再要求最大8×8tile MAE≤2/255后975对均无负delta cosine。尚无充分证据支持“多专家普遍左右打架→平均动作→67s晚闭爪”的完整因果。

**机理与口径。** 训练循环按seed重建：新10493次chunk-start访问/8797=1.192793遍，旧27482/2350=11.694468遍；末batch5/6，重叠future标签另算，不是10496/1.18或完整监督曝光/独立覆盖。官方noVAE为零latent，称固定专家观测重构而非teacher forcing；损失是masked normalized L1（统计最优为中位数，不是L2均值），backbone使用FrozenBatchNorm2d，没有普通BN训练/推理统计切换。来源：[编码/解码与runner](../../experiments/colab-twin/learning_vision.py)、[实际训练循环](../../experiments/colab-twin/run_vision_learning.py)、[固定官方源码](https://github.com/huggingface/lerobot/blob/e0d50211ef236143ae867228662b7dfaba554f02/src/lerobot/policies/act/modeling_act.py)。随机ResNet/有限步数不能证明数学上无法学习或特征无序；数据、normalization和步数同时变，不能唯一归因为优化预算。

future标签token搬运占53.382%、冻结模型normalized L1误差总量占46.388%；接近误差总量占34.080%，闭爪占.340%。这是当前固定预测误差分布，**不是训练梯度归因**；不能用帧比例直接宣传超过一半梯度耗在搬运，更不能据此直接5倍加权所有接触前。专家观测重构改善也不保证偏离后闭环恢复。

[独立Codex数组审计](../../experiments/colab-twin/output/vision-b-offline-independent-20261003/report.json)与[近邻独立审计](../../experiments/colab-twin/output/vision-b-offline-independent-20261003/consistency-report.json)回源HDF与冻结源码重算，未重复推理/物理/渲染/训练，不能冒充新AGY/ZCODE会审。辅助绘图首次因learning venv无matplotlib退出1，改为HDF时间/jaw导出保存数组后用已有系统matplotlib绘图exit0，无安装/环境修改；审核脚本首次外部STL相对路径处理错误保留失败记录并修正，均不属于模型产物通过证据。

**下一候选（尚未执行）**：使用已有`--execute-chunk-steps 1`，同冻结d4db权重/同场景/同物理标准，只改变执行参数16→1，先验证后部chunk误差影响；模型仍预测16拍，但每20ms执行首拍并重新观察/锚定（原320ms）。执行窗口与观测/锚点节拍内在联动，不能把结果孤立归因为视觉，也不保证h0在陌生状态有效；forward需求最多16倍，若后续执行须记录实际耗时/峰值及原失败退出。本轮没有运行候选、增加训练/采集，暂不重采样/引入预训练或冻结视觉层。root负责接续，全部诊断NPZ/图/脚本/log继续Git忽略，原现场22项/index/README/MJCF保留。

### 2026-10-03 B冻结权重chunk1单回合复验因墙钟上限截断

用户授权一个同初态纯视觉物理回合，仅`--execute-chunk-steps 16→1`，冻结checkpoint SHA `d4dbfc3e840637b1605148d19349f1bf324f9e071fc4064750952aa224d68509`。复用原evaluate入口；不再训练/采集、调线程或改变物理/安全标准。保留120s墙钟与90s仿真上限，seed0、CUDA、reference raw、固定128×128RGB、原2ms物理/20ms控制、1mm余量与1s蓝盘落定一致。模型仍输出16拍，执行每拍刷新q6/RGB并重设残差锚点，不输入env真值、clock、stage、IK或OMPL。

**唯一回合实际退出1，运行时间阻断；抓放对照尚未完成。** [原物理报告](../../experiments/colab-twin/output/vision-b-chunk1-nominal-20261003/report.json)SHA `179aa8dcff8e81459c41b2ac7bbedc4286a1e59b8d6fe80a83252ac7f856206e`，failure_reason=wall_time_limit：

| 实际记录 | 结果 | 来源 |
| --- | --- | --- |
| 原evaluate墙钟 / 外层进程 | 120.4996s / 123.6989s；实际退出1，无外层超时重试 | [execution](../../experiments/colab-twin/output/vision-b-chunk1-gates-20261003/execution.json)、[outer](../../experiments/colab-twin/output/vision-b-chunk1-gates-20261003/outer-execution.json) |
| 完整控制转移 / 仿真推进 | 250拍 / **5.00s**；最后动作时刻elapsed4.98s，最后完整物理状态elapsed5.00s | [保存NPZ](../../experiments/colab-twin/output/vision-b-chunk1-nominal-20261003/policy-transitions.npz) |
| 抓取 / 持物 / 放置 | false / 0s / false，未闭爪或接触，无安全停止 | [物理报告](../../experiments/colab-twin/output/vision-b-chunk1-nominal-20261003/report.json)、[轨迹审计](../../experiments/colab-twin/output/vision-b-chunk1-audit-20261003/report.json) |
| 原预测回调耗时，中位 / P95 | **402.0746ms / 475.0680ms**；最小234.5213/最大921.2401ms，250/250超过20ms | [独立重算](../../experiments/colab-twin/output/vision-b-chunk1-gates-20261003/latency-audit.json) |
| 回调总时间 / Torch峰值allocated、reserved | 98.8825s / 74.9336、102MiB | [逐次计时NPZ](../../experiments/colab-twin/output/vision-b-chunk1-gates-20261003/prediction-latencies.npz)、[execution](../../experiments/colab-twin/output/vision-b-chunk1-gates-20261003/execution.json) |

[仅计时包装器](../../experiments/colab-twin/output/vision-b-chunk1-gates-20261003/run_once.py)SHA `39b0d9056d7e99d61a448f5decc2908bfdf594bf2ad389091c6bd9807a6b87db`每次只调用原predict一次，原参数/返回/action保持；没有额外模型调用、CUDA同步、线程设置或物理步，结束恢复原方法。计时覆盖归一化、设备传输、模型forward、回CPU/解码/jaw投影，**不包含EGL渲染或物理推进**，不是纯GPU kernel耗时；Torch峰值不含EGL、驱动与其他进程。wrapper_evaluation_s120.5947计时截至原main返回，包含原evaluate内部产物保存，不包含包装器随后写出的计时NPZ与execution报告；原limit在step间检查，启动/最后step/保存可使总记录略超120s，不意味着本轮放宽上限。

[独立轨迹/FK审计](../../experiments/colab-twin/output/vision-b-chunk1-audit-20261003/report.json)37项通过，actual exit0/2.574s，SHA `2923a3d6d6b0feccca9634da8afe04acc29dd62dbe602e370b85511d0eb191b7`：250完整行、最后命令与最后行匹配、无未保存停止tick；抓取/持物/放置监视器与原report一致，保存双pad力均0。权重/参考数据/相机/原模型/派生XML/初态及52份生产Python前后相同。[早期对照](../../experiments/colab-twin/output/vision-b-chunk1-audit-20261003/early-comparison.json)第1拍raw_action/投影action/q6/time与旧chunk16逐位一致；同sim5s新/旧PINCH参考点距物体XY278.18/270.44mm，尚是早期前缀，不作为接近末端或抓取结果。该审计仅读取保存数据/mj_kinematics，没有新物理步、渲染、推理或训练；报告中的“teacher-forced”应读作固定专家观测重构，前轮并未输入专家动作。

[独立计时审计](../../experiments/colab-twin/output/vision-b-chunk1-gates-20261003/latency-audit.json)148项通过，SHA `d9e3b1b0274e5fc6d720804c48a2c620e2ccffd0194e7425b800b0f7b690cd52`：直接从NPZ重算统计，250predict=250转移、一个runner、输入仅q6/RGB，核对原调用次数、source52/两历史权重与limits；没有再调用模型/物理/渲染。两位均为Codex只读审计，不冒充新AGY/ZCODE会审。[事后运行快照](../../experiments/colab-twin/output/vision-b-chunk1-gates-20261003/postrun-runtime-snapshot.json)来自另一个新进程及nvidia-smi，不是本回合内历史；不能用它断言CPU线程、GPU降频或其他进程争用已被证实为根因。

**归因边界与接续。** 本次未达到专家11.02s闭爪及抓取窗口，不能确认chunk1改善抓放，也不能把“仍未通过”解释为chunk尾部不是瓶颈或视觉表征必然失败。目标方向投影20%不是“方向错80%”，专家观测h0误差也不保证偏离后动作有效。当前运行配置不支持此前毫秒级/真实50Hz预期；下一候选应先有界离线拆分预处理、传输、forward与解码耗时，记录实际调用和运行状态，再决定执行调度/运行配置的一项改动，候选尚未执行。不自动延长预算、启动第二回合或重训。

B/S7e任务仍未通过，v11固定正常20/20、旧扰动3/20与S7d未过状态保持；40..59、云端、实体未使用。沿用“按当前任务选择验收依据”，本轮验证为唯一物理回合、独立只读轨迹/计时、输入/源码哈希、文档链接与diff；生产源码未变，不重复声称232项测试覆盖新的物理结果。root负责可恢复接续；全部NPZ/计时/脚本/日志仍Git忽略，公开只交付本轮事实记录，原现场22项/index/README/MJCF保持。

### 2026-10-03 B离线耗时拆分热态原调用约8ms原仿真慢因仍未知

用户授权先做冻结模型离线predict耗时拆分，不启动chunk4/8、延长墙钟或新的抓放回合。唯一诊断读取已保存chunk1帧0/100/200的q6与RGB，以及nominal专家frame550的q6/RGB；只读这些部署输入，不输入env/阶段/时钟/专家动作。保持d4db权重、float32张量、batch1、eval/no_grad、原图像转换/残差锚点/jaw投影与后端默认值；cuDNN allow_tf32=true、matmul allow_tf32=false仅记录，未修改精度/compile/inference_mode/线程。实际PyTorch2.7.1+cu126，进程内getter线程8/8。

[唯一profile报告](../../experiments/colab-twin/output/vision-b-runtime-profile-20261003/report.json)SHA `ca20df35faf8a6fdd806e9e02738d2dba8355be872677e3895d54a6ccbd82e4f`；[真实execution](../../experiments/colab-twin/output/vision-b-runtime-profile-20261003/execution.json)actual exit0、外层6.3340s/内4.0219s、外层硬timeout120s，无重试。cold1+warm3+12原调用+12仪表+1operator共29前向，新增优化/物理/渲染均0。[原调用与镜像脚本](../../experiments/colab-twin/output/vision-b-runtime-profile-20261003/profile_predict.py)SHA `f8d8599a4c26bd3679ebe6fe0989ea026e977743e4c3806d875db80b41ae74dd`，[外层](../../experiments/colab-twin/output/vision-b-runtime-profile-20261003/run_profile_once.py)SHA `5ae4191b55fb7ac1ced3a44a97e27ab7c6cb68b37379d442010601947c7f2860`；[独立脚本审查](../../experiments/colab-twin/output/vision-b-runtime-profile-20261003/script-review.json)核调用上限、路径、末尾同步与异常/partial保留。

**当前独立离线进程未持续复现402ms。** 首冷原predict400.3743ms，后续三个warm调用8.2854/5.4163/6.2554ms。12次未打点原调用median8.2287/P95 9.2764ms；12次镜像仪表median7.0727ms，12组成对raw/action最大差严格0，初始原raw与已保存旧chunk1首拍差0。仪表后调用反而更短不能视作优化：原先/仪表后固定顺序、GPU热态与事件/钩子投递仍影响时序，输出等值只证明本次输入上算术结果未变。首冷没做阶段打点，不能将400ms定位到某一层；也不能用一次冷启动解释前轮全部250次>20ms。

| 仪表阶段，12次中位数 | Host毫秒 | 同流CUDA Event毫秒 |
| --- | --- | --- |
| state归一化CPU / RGB布局CPU | 0.0144 / 0.0249 | — |
| state张量/H2D / RGB转换/H2D/div255 | 0.0388 / 0.1172 | 0.0574 / 0.1352 |
| 完整policy forward（含下列子段） | **6.4544** | **6.4732** |
| ResNet18骨干 | 2.7245 | 2.9271 |
| Transformer encoder / decoder | 0.9493 / 1.4389 | 0.9712 / 1.4609 |
| finite检查（含等待） | 0.1064 | 0.1205 |
| prediction回CPU/numpy（含等待） | **0.0417** | 0.0565 |
| 解码 / 队列与jaw投影CPU | 0.0476 / 0.0279 | — |

CUDA通常异步，原finite布尔检查已经可能等待GPU，D2H等待不能直接称为传输瓶颈；依据[PyTorch2.7异步执行](https://docs.pytorch.org/docs/2.7/notes/cuda.html#asynchronous-execution)及[Event文档](https://docs.pytorch.org/docs/2.7/generated/torch.cuda.Event.html)。本次按原顺序测量，没有逐段强制sync；CUDA Event对象在call前创建，但record懒初始化/钩子开销计入仪表差异。末尾Event同步仅在完整call后，median0.0230ms另列，不包含在instrumented_host_ms。Event反映流时间跨度及CPU投递间隙/竞争，不是纯kernel忙碌时间。各子段含在policy总段，不能重复相加；表中各自中位数也不是同一条样本的和。

[额外一次operator trace](../../experiments/colab-twin/output/vision-b-runtime-profile-20261003/operator-trace.json)输出动作差0、host16.4641ms，开启profiler有开销，不并入baseline。cuDNN卷积21次的self_device归因合计1.2422ms；trace包含真实CUDA kernel及memcpy，排除本轮CPU-only路径。operator GPU归因、CUDA kernel leaf与CPU inclusive时间存在重叠，不混合加总成“总算力”。模型/缓冲完整哈希前后相同、参数grad均None，52份生产Python及全部输入哈希保持。

[保存产物独立核验](../../experiments/colab-twin/output/vision-b-runtime-profile-20261003/result-audit-final.json)重算rows统计、核输入/源码哈希和trace设备leaf；12组动作差0与operator差0是运行时断言witness，未保存各对完整动作数组，因此不声称审计者重新计算这些数组或再推理。初审一个CPU `aten::result_type`计数差异保留：trace中父与唯一子同名，安装的Torch profiler_util.py `_remove_dup_nodes`会合并子节点，解释key_averages计数减少；最终补充不修改原trace/report或再调用模型。

[历史计时核对](../../experiments/colab-twin/output/vision-b-runtime-profile-20261003/historical-timing-review.json)回源原队列与4500拍报告：旧chunk16实际282次forward，全部恒定400ms需要112.8s，超过旧总27.4108s；只能推出forward平均全包上界97.20ms，不能还原旧median/P95。当前120.4996/5=24.10倍整体慢放；callback98.8825s，其余21.6170s是加载/渲染/物理/监测/保存的综合，不是单独渲染时间。chunk4在同5sim前缀下约24.72s墙钟仅是callback预算外推；300wall约12.45sim、15sim约361.5wall均非实测。当前CLI明确拒绝max-wall-s>120，单设max-simulation-s15不会延长墙钟；15sim最多是抓取前缀，不替代专家约47sim完整抓放。

**尚未定位原仿真持续慢的具体原因。** 本轮组间GPU快照P3/645MHz→P0/1500MHz仅属于本次离线进程，不能拿前次事后P8快照作反事实；同样，当前8/8线程下快调用不证明历史线程相同，也不证明某个设置能修复原慢。[源码路径复核](../../experiments/colab-twin/output/vision-b-runtime-profile-20261003/runtime-path-review.json)确认原evaluate在循环前只加载模型/创建renderer一次，循环是capture→predict→physics；每次render绑定已有GLContext并读像素，不是重建context。离线路径没有EGL/渲染/物理循环，下一最小候选是同冻结输入/权重的有界EGL/CUDA路径对照与同步计时，记录实际运行状态；尚未执行，不把上下文切换、功耗或争用写成已证实原因。

本轮采用既有Wiki“按当前任务选择验收依据”，方法资料通过find-docs核官方2.7版本，诊断与结果由Codex独立只读复核，不冒充新AGY/ZCODE讨论。B/S7e仍未过，chunk1实际抓放对照未完成；v11正常20/20与旧扰动3/20、S7d未过、原物理/安全/落定门槛保留。没有新增抓放回合、训练、图像渲染、留出40..59、云端或实体操作；root接续，运行产物/trace/脚本/日志继续Git忽略，原现场22项/index/README/MJCF保持。

### 2026-10-03 B同输入EGL与CUDA静态对照未复现持续慢调用

用户指定下一步核对同输入EGL/CUDA路径，暂不重训或改精度，并保留“完整闭环50Hz尚未验证”。本轮仅静态同输入A-B-A，没有新增物理任务回合。冻结d4db checkpoint、原q6与128×128 uint8存档RGB（旧chunk1初始帧）、batch1、execute1、float32/no_grad、原归一化/解码/jaw投影及后端；进程内线程8/8、cuDNN TF32=true/matmul TF32=false仅记录，没有修改。模型始终使用冻结画面，不把渲染输出替换为新观测。

[唯一报告](../../experiments/colab-twin/output/vision-b-egl-cuda-aba-20261003/report.json)SHA `7244b1d460299fa54da99a6cc7e2e4491fc6a3f623d1e8227a61ade670fc532d`；[真实execution](../../experiments/colab-twin/output/vision-b-egl-cuda-aba-20261003/execution.json)actual exit0、外层6.5325s/内层4.2950s、硬timeout60s、唯一attempt1/no retry。4次cold-warm+A8+B8+close后A8，共28原predict和28真实model forward；8静态capture、一个renderer、一次显式close。新优化/积分/任务回合0，完整抓放效果没有重新评定。

| 同一冻结输入，每组8次 | Predict中位ms | Predict P95 ms | Predict最大ms |
| --- | --- | --- | --- |
| A：尚未创建renderer | 6.4847 | 6.9660 | 7.0383 |
| B：原静态capture后立即predict | 6.8334 | 7.3294 | 7.4848 |
| A：renderer.close后 | 6.4120 | 7.1815 | 7.3752 |

B原capture中位1.1119ms、最大8.1631ms；capture+predict两段中位7.9350ms/P95 12.9041ms/最大15.1634ms。首次模型调用377.1950ms单列，随后warm7.0870/6.4611/6.5748ms；初次渲染8.1631ms保留在8次render/pair统计中，不计入predict段。静态model/data/renderer设置873.0674ms、close16.6850ms在callback之外，没有摊进各组。B包含原capture内部CPU状态保全检查，计时只用perf_counter；capture返回后仅取主机时间即进入原predict，没有CUDA Event/getter/显式sync、GPU查询、hash或保存插入。每次predict返回后才检查、保存完整动作/输入hash/静态快照，保存的组间空隙不计入callback，也不是实时循环验收。

静态场景直接读取原派生contact-workcell.xml及13原STL，完整snapshot来自原nominal rawHDF，checkpoint本身没有initial_snapshot。恢复qpos13/qvel12/ctrl6/warmstart12/time后只调用一次mj_forward刷新几何与派生量；[官方API](https://mujoco.readthedocs.io/en/3.3.7/APIreference/APIfunctions.html#mj-forward)说明此调用不做时间积分。此次primary、warmstart与其他记录字段前后差也全0，后续八次render和close以forward后快照为基准逐位比较。禁止mj_step/step1/step2与resetData三入口，没有StateWorkcell.reset/step或生成新物理XML。实际GL context类型为mujoco.egl.GLContext；[安装版渲染语义](https://mujoco.readthedocs.io/en/3.3.7/python.html#rendering)及[静态源码协议审查](../../experiments/colab-twin/output/vision-b-egl-cuda-aba-20261003/static-protocol-review.json)核close释放GL/Mjr，但global EGL display保留，因此后A不是全新进程或GPU复位。

[内层脚本](../../experiments/colab-twin/output/vision-b-egl-cuda-aba-20261003/run_aba.py)SHA `7e0a8adc9e064ecc96d47375841591bee6a033450f59d1a62ce23affc5b67c29`，[唯一外层](../../experiments/colab-twin/output/vision-b-egl-cuda-aba-20261003/launch_once.py)SHA `222f6123872e751ad30dbcb2907639a203ed45e05e2f4173d229419830c04b78`。源码协议反馈与根最终AST/SHA核对先于启动，正式脚本审查记录在诊断完成后落盘，保留真实时序，不声称该JSON已在执行前存在。计数由原调用与CPU model prehook记录、禁用积分/reset入口并回源核对；不是native全面调用trace。异常清理结果单列cleanup.json，本次context已释放、error=null；未重试或改原生产文件。

[独立静态数组审计](../../experiments/colab-twin/output/vision-b-egl-cuda-aba-20261003/state-pixel-audit.json)SHA `0b865e7331820ae3a2ef77514c7dc87b281dc9b511b8cba504afdbe4bdd07ac5`，actual exit0/0.316s，275项通过。仅stdlib/numpy/h5py读取原产物：从完整raw snapshot核forward前后及8B/close后9字段差全0；8RGB逐位一致且等于冻结存档RGB，最大像素差0；从[28组完整动作](../../experiments/colab-twin/output/vision-b-egl-cuda-aba-20261003/actions.npz)独立重算raw/投影动作及旧初始动作差0，并复核group统计、源码/输入SHA、计数和退出。该审计没有新增模型/GL/FK/forward/积分/GPU查询。模型权重/缓冲哈希前后一致、grad均None是本次运行witness，源52和checkpoint/raw/XML/STL文件哈希另独立核对；不通过再次推理“验证”原输出。

[独立调用与结果审查](../../experiments/colab-twin/output/vision-b-egl-cuda-aba-20261003/result-audit.json)SHA `cdada7cf69e0d2d76504b0351038fcb945da4c74bc397c20043511e88eb58520`，347项通过：复核完整动作/像素/状态数组、全部统计、artifactSHA、预算及cleanup，不调用模型/GL或物理；与275项静态数组审计是两份独立范围，不合并成新的任务成功次数。[正式脚本记录](../../experiments/colab-twin/output/vision-b-egl-cuda-aba-20261003/script-review-final.json)保留32项代码检查通过与落盘晚于launch的时序，不能包装为未启动状态通过。

**结论只覆盖当前静态路径。** 没有持续复现旧402ms；不能认定已修复历史慢循环，也不能将EGL上下文、GPU频率、线程或调度写成唯一根因。A-B-A有顺序、热态与系统负载混杂，每组仅8次；不将约0.35ms差异解释为因果效应。静态capture+predict<20ms只核两段，未包含真实physics、monitor、调度或保存开销与长时尾延迟，完整闭环50Hz仍未验证。下一候选冻结配置下有界检查真实循环render→predict→physics→monitor与实际调度，尚未执行。

沿用按当前任务选择验收依据；本轮Codex独立只读审核不冒充AGY/ZCODE新会审。B/S7e、chunk1完整抓放、v11正常20/20与旧扰动3/20、S7d未通过状态保持；未使用40..59、云端或实体。原生产源码没有变化，不重复232项测试作为新物理/实时通过证据。root串行接续，全部模型、NPZ、脚本、日志和审计仍Git忽略；公开仅交付本轮事实记录，原现场22项/index/README/MJCF保持。

### 2026-10-03 B真实循环100拍计时热态短前缀低于20ms历史慢因仍未知

用户授权对真实循环的物理推进、监测与调度做有界计时。复用原run_vision_learning.main/evaluate唯一调用，不复制控制循环、不重训或改精度。固定d4db checkpoint、原nominal初态/场景/seed0、execute1、float32/no_grad、原后端和线程8/8；相机使用真实逐拍RGB＋当前q6，env/阶段/clock不进入policy。原循环只收紧为max-wall60s/max-simulation2s，最多100拍；outer hard90s/attempt1/无重试、额外预热forward0，原2ms物理/20ms控制、1mm余量/限位/1s落定标准保持。

[唯一计时报告](../../experiments/colab-twin/output/vision-b-loop-timing-20261003/report.json)SHA `7b87e60e66b157fdbacbce14f3ca3e3f642b368a7188d75cf139d8357f8adb2b`；[execution](../../experiments/colab-twin/output/vision-b-loop-timing-20261003/execution.json)diagnostic actual exit0、外层7.3860s，原main actual exit1/4.8930s，原[任务报告](../../experiments/colab-twin/output/vision-b-loop-timing-20261003/evaluate/report.json)保留failed/simulation_time_limit/not_passed。实际100完整拍、仿真增量1.9999999999998905s；100capture/predict/model forward/step/diagnostics/checker/monitor，1000mj_step、201observe和301mj_forward。没有warm额外推理或新的第二回合，计时完成不标记抓放通过。

**完整周期与首次冷调用都保留。** 原while头的既有perf_counter检查至下一相同检查定义cycle，包含限时/仿真边界、各原调用、记账和插桩CPU开销；此外保存render进入→monitor返回工作段。100cycle中位11.7568ms/P95 12.9701ms/最大342.8987ms，1/100超过20ms且为首拍。首拍predict326.7785ms、render6.7879ms、step9.2342ms，均完整保留；后99cycle中位11.7420ms/P95 12.9191ms/最大14.1422ms，0/99超过20ms，后99predict中位6.8213ms。本次没有复现旧连续250次约402ms，不能由当前一次首冷解释全部旧慢调用。

| 顶层互不重叠段，全100拍中位数 | 毫秒 | 范围 |
| --- | --- | --- |
| 原capture_rgb | 1.1325 | EGL出图、像素读取及原状态保全检查 |
| 原runner.predict | 6.8278 | CPU准备、模型、原finite等待、D2H/解码/投影 |
| 原cell.step | 3.7167 | 两次观测刷新、10次积分、接触守卫及诊断 |
| 原monitor.update | .0044 | 消费真实诊断，不再推进物理 |
| cycle减上述四段的残余 | .0590 | 原记账、包装/CPU计数开销及调度等复合间隙 |

以上各中位数来自不同拍，不能加成严格的中位总周期。step内10次mj_step总中位.4830ms，两次observe总.5764ms，diagnostics1.4883ms；其checker1.1830ms已经包含在diagnostics内，另有独立query数据的mj_forward，不能与step/诊断重复相加。step排除直接子段后的残余中位1.1775ms仍含原命令检查、10次接触guard和测量CPU开销，不归为纯积分或特定OS等待。checker配置285个pairs，未逐mj_geomDistance打点，不能把其整体时间都写成纯距离kernel。

初始化至首while3.3201s，100cycle区间合计1.5112s，末次边界至原main返回tail.0617s，三者合为4.8930s。初始化含checkpoint加载约1.9975s、cell构建1.0457s、renderer创建.2019s；结束包含close17.3384ms、原NPZ保存2.0183ms、两次JSON写4.7546/.1957ms，以及未单独包装的PNG导入/编码和其他结束成本。outer7.3860s还含解释器/import与诊断产物汇总、模型只读比较，不摊入每拍；未把tail全部说成序列化。

[原调用包装脚本](../../experiments/colab-twin/output/vision-b-loop-timing-20261003/run_loop.py)SHA `5d244080f5acd2fdddf5d86b405827a7c032e426bb1b68b71fd99354a6b5f8b0`，[唯一外层](../../experiments/colab-twin/output/vision-b-loop-timing-20261003/launch_once.py)SHA `b1b40c8d9e96b9008bf1336a03558d8d21f18f4312b7ecfd87553df6f01bcf3a`。[正式执行前审查](../../experiments/colab-twin/output/vision-b-loop-timing-20261003/script-review.json)SHA `d1af3dcc2cda966cda8b8686176f3a5c5b86b7cbb9c82b5fc39668c68b177ac7`，33项通过，落盘且绑定最终SHA后才有invocation。所有计时用主机clock，CPU hook只数真实forward；没有CUDA Event/getter/显式sync/status查询插入render→predict，也没有sleep/节拍等待/优先级修改。只内存记录，原main结束后保存完整区间/输入/动作/统计并恢复全部方法；hard90强制终止可能来不及写内存区间，此边界事先保留，本轮未触发。

[独立轨迹与区间审计](../../experiments/colab-twin/output/vision-b-loop-timing-20261003/artifact-audit.json)SHA `d3cd64a58a272b422dc91e1149cfe3f8f73e9caf051b4ba9b38d462872cb5492`，13323检查通过，actual exit0/.7658s，仅stdlib/numpy/h5py读取产物。独立重算旧chunk1前100的timestamp/next_timestamp/q6/next_q6/raw/action最大差全0，100条diagnostic逐项相同、两个派生XML SHA相同；首态与rawHDF一致，最后命令对应最后完整保存行，无丢失terminalcommand。实际1000积分全用执行data；301forward=reset1＋每拍2执行data刷新＋1checker独立data刷新，嵌套区间及exclusive计算合法。100拍没有闭爪、抓起、持物、放盘或安全停止，是接触前前缀，不是走完全程的抓放失败。

[第二份独立计时审查](../../experiments/colab-twin/output/vision-b-loop-timing-20261003/result-audit.json)SHA `2ae58b6b17e0f1f36310aaf625369f4f402e1bb717838317529498523082915d`，83项通过，重算events父子、20列timings NPZ、全100/后99全部统计与预算/真实时序。两份审核范围分别记录，不合并为任务成功次数；审核没有构建模型/GL或执行物理。运行结束只读逐项比较172个state tensors与已加载checkpoint，torch.equal均true、grad均None；52份生产Python/原输入文件前后SHA不变，没有optimizer或模型行为修改。

**归因与接续边界。** 本次短前缀的后99完整周期均低于20ms，显示当前配置在这些无抓取阶段有计算余量；原循环自由运行，没有50Hz节拍调度，且首冷超限。它不证明长期实时能力、接触/持物/落盘尾延迟或完整抓放，历史持续402ms原因仍未知；需要慢状态的现场证据，不能倒推功耗、context或线程根因。下一候选为同冻结配置接续完整chunk1抓放与分段计时，原120s墙钟/90sim上限，尚未执行；不自动追加重复探针、精度变化或重训。

采用既有Wiki按当前任务选择验收依据；只交付短前缀运行成本及轨迹保全。B/S7e、chunk1完整抓放与S7d整体仍未通过，v11正常20/20与旧扰动3/20保持；40..59、云端与实体未使用。root接续，Codex独立审计不冒充AGY/ZCODE新会审；所有模型、输入/区间/轨迹、脚本和日志继续Git忽略，公开只交付本轮事实记录，原现场22项/index/README/MJCF保持。


### 2026-10-03 B冻结chunk1完整回合关节限位安全停止抓放未通过

用户明确授权一次冻结d4db/nominal/execute-chunk-steps1、原wall120s/sim90s的完整纯视觉抓放回合。唯一复用原main/evaluate，保留原2ms/20ms、1mm余量、关节限位和1s落定判据；不追加预热、重训、精度/线程/后端或节拍修改。外层hard150s只覆盖进口初始化、原退出保存和计时汇总，不扩大原回合120s预算，无重试。生产52源码未改，正式32项[预启动审查](../../experiments/colab-twin/output/vision-b-chunk1-full-timing-20261003/script-review.json)SHA`321a5cd240b15ac405145eec31dcbf863e621c9893e9f9fbf2d12c624574c561`先落盘，launcher强制绑定两个最终脚本SHA后才生成唯一invocation。

**结果0/1，安全停止，未被墙钟截断。** [原任务报告](../../experiments/colab-twin/output/vision-b-chunk1-full-timing-20261003/evaluate/report.json)passed=false/task_acceptance=not_passed/safety_stop=true/failure_reason=safety_stop；原main、helper及[外层执行](../../experiments/colab-twin/output/vision-b-chunk1-full-timing-20261003/execution.json)actualexit均1，outer13.599308s，原报告total10.448100s，wrapper原main10.450353s。计时[完整记录](../../experiments/colab-twin/output/vision-b-chunk1-full-timing-20261003/report.json)status=completed_single_attempt_measurement，SHA`559bbcb40b0192d74f83d91e4df94ba6c4211f2f9f3938415d56eae34c071bc8`，只表示唯一试验及计时记录完成，不强标物理任务通过。

初态absolute1.000s，579完整轨迹到absolute12.580s/elapsed11.580s；第580条命令在absolute12.580s下发，10次积分全部完成至absolute12.600s/elapsed11.600s，然后step抛SafetyStop，无第580个保存行/monitor更新。580render/predict/model_forward/step、5800mj_step、1161observe、580diagnostics、581checker、579monitor；1740mj_forward=1161执行data刷新＋579checker独立data刷新。末拍两次checker（diagnostics和异常详情）均先在joint_limit返回，没有mj_forward，不能将checker调用数直接当作forward数。

第4轴wrist_flex实测1.6581003327062775rad，派生XML原关节上界1.6580627293335335rad，差3.760337274405501e-5rad=0.002154515°；最后下发1.6579903239325227rad，比ctrl上界1.65806低6.9676067477e-5rad。原collision_scene.py:256按实测q严格无容差检查，reason=joint_limit、distance/pair=null；不能写成盘壁碰撞或命令越ctrl限位。原末命令与终端time/qpos/qvel/ctrl/warmstart直接复制保留，没有额外forward/FK/诊断调用。

**抓取未成立。** 580命令（包括终端尝试）全为open0.5，closed0.015未出现；579保存诊断边界双指法向力均0，无双指接触/25mm抬升/1s持物，物体z9.921450320mm仍在红盘支撑，蓝盘释放/稳定落定未成立。独立顺序重算原monitor得到grasp/place=false、hold/settled0；其safety_stop=false只覆盖已返回579行，不能否定外层第580次step异常的safety_stop=true。末拍接触力没有单独保存，20ms边界诊断也不排除未保存的2ms短接触；不夸大为所有积分步接触证明。

| 分段，全579个完整周期中位数 | ms |
| --- | --- |
| 原EGL capture_rgb | 1.1211 |
| 原predict | 6.5061 |
| 原step（观测、10积分、守卫、诊断） | 3.6219 |
| 原monitor | 0.0042 |
| 原记账、测量及调度等复合残余 | 0.0588 |

全579cycle中位11.3380/P95 13.0839/最大402.4495ms，1拍超过20ms且为首拍（predict391.68435ms）；后578中位11.3361/P95 13.0627/最大15.8733ms，0拍超过20ms，均到下一原while墙钟检查。第580异常尝试从原while检查到cleanup入口9.9363ms单列，step2.3932ms，无monitor，不混入完整周期或称next-cycle节拍。setup3.309535s＋579cycles7.022846s＋异常尝试.009936s＋tail.108035s=main10.450353s；outer还含解释器/import及诊断汇总。10次积分合计中位.4964ms已包含于step，父子段和各列中位数不重复/严格相加；残余不是单独OS等待。本轮all580predict中位6.5057ms与主表completed579的6.5061ms不同口径，前者单独保存。

[独立物理与原数组审计](../../experiments/colab-twin/output/vision-b-chunk1-full-timing-20261003/artifact-audit.json)173项通过，SHA`072d87369031a803e418dff792e6bc352195b6266fcab2aa6df18d9ebae2307d`，审计actualexit0。独立核旧chunk1前250六数组及diagnostic逐项相同、前100RGB/state/raw/action差0；原初态/派生scene/源码/冻结权重SHA一致，终端动作确实不同于最后完整保存行且10次积分记录齐全。只读XML/AST范围与原monitor标量重算，不构建模型、GL或FK。

[独立计时审查](../../experiments/colab-twin/output/vision-b-chunk1-full-timing-20261003/result-audit.json)93项通过，SHA`140a08d37b48f49b4125f97fce60699f265adb208a72568eab43f7103744f7ad`，重算events父子/20列NPZ、正常/异常周期和真实预算；保存全部冷/后续口径，172模型state tensors完全相同且gradNone。计时postprocess按tick线性索引，控制路径仍原循环，source/input SHA不变。

**Remaining / Next：** 每拍只执行h0仍未使当前冻结策略通过；专家观测上的低h0误差不足以证明实际rollout对齐或安全。下一最短候选是只读比较接近段五轴与专家轨迹、核wrist_flex实测/下发目标及限位余量，再决定是否需要恢复数据，未执行。本次没有抓取接触/持物/落盘阶段或长期paced50Hz证据，历史持续402ms仍未知；不将本次单冷拍倒推为原全部慢调用，也不将11.34ms外推为90sim必完成。

沿用Wiki按当前任务选择验收依据；root接续，全部模型、轨迹/RGB、脚本/区间/日志/审计继续Git忽略。无新训练、精度改动、重复回合或放宽阈值；B/S7e抓放及S7d均未过，v11正常20/20与旧扰动3/20保持，40..59/云端/实体未使用。独立Codex审计不冒充AGY/ZCODE会审；原现场22项/index/README/MJCF保全。

### 2026-10-03 视觉起步chunk采样5倍接入

**Current / Done：** 用户选定 `label_valid & (raw_frame_index < 50)` 的chunk起点采样权重5倍。本轮交付代码、CPU验证及原数据索引审计，未执行GPU资源探针、模型训练/推理、渲染或物理回合。

- `run_vision_learning.py fit --startup-weight 5` 显式启用，默认1走原 `rng.permutation(N)`，连续三轮及后续随机数序列精确相同；非fit使用5在输出目录创建前拒绝。
- `VisionDataset.frames` 保留排除invalid后的原始帧号；每完整采样轮起步索引5份、其他1份，再以原seed洗牌。当前四档有效数2350/2300/1956/2191共8797，起步命中50/0/0/0，采样池8997。完整池250/8997＝2.779%不冒充截断训练或梯度份额。
- 报告与checkpoint保存 `training_sampler` 的规则、权重、逐档命中、池大小、seed，以及成功optimizer更新的 `chunk_start_draw_count`、`startup_draw_count`；完整池轮数单列。模拟步数/墙钟截断及同步失败测试确认未完成批次不记入成功更新次数。
- 原归一化仍在8797唯一有效样本上拟合；与旧fit JSON逐项完全相同。数据、标签、chunk长度、模型结构、RGB处理、动作解码、推理和物理标准未改，仅两生产源码更新。

**Validation：** `python -B -m unittest -v test_startup_sampling test_learning_vision` 实际exit0，25项/0skip，框架内部0.232s；新增13项覆盖采样边界、无效标签筛选、随机序列兼容、参数拒绝和mock优化计数，其余12项为原视觉适配回归。模型、优化器和CUDA路径均mock，未开展实际学习。[CPU测试日志](../../experiments/colab-twin/output/vision-startup-sampling-20261003/cpu-tests.log)。

[真实四档索引审计](../../experiments/colab-twin/output/vision-startup-sampling-20261003/report.json)实际exit0，16项通过：原始eligible索引/chunk长度与冻结NPZ相同、每个完整池索引恰为5或1次、归一化完全相同、四RGB/raw hash与baseline输入保持、仅两预期生产源码变化，旧资源报告确因源码绑定拒绝。[完整采样索引](../../experiments/colab-twin/output/vision-startup-sampling-20261003/sampling-indices.npz)与[审计脚本](../../experiments/colab-twin/output/vision-startup-sampling-20261003/audit_sampling.py)留在Git忽略的output。首次审计脚本误用不存在的context-manager接口，exit1且尚未进行索引检查；[失败记录](../../experiments/colab-twin/output/vision-startup-sampling-20261003/first-index-audit-attempt.json)保留，改显式finally关闭后通过，未修改输入。

独立Codex源码/测试评审无阻塞问题，未冒充新的AGY/ZCODE会审。采用既有Wiki“按当前任务选择验收依据”：这里只确认采样实现，不扩大为起步方向、完整50Hz或视觉抓放成功。S7d/S7e仍未通过，旧v11正常20/20、旧扰动3/20与d4db失败证据保留。

**Remaining / Next：** root负责接续。新源码不能使用旧资源报告或静默载入旧d4db；基线源码绑定提交 `4a1cf3b51d768b5f8004c62ce0a02a2522c4db18`。后续明确执行时，先做绑定新源码/同四档数据的五步资源探针，再按原120s/5000step上限单变量训练；先核对首帧及前3秒方向/步长，再独立验收纯视觉抓放。不开新视觉主干、不放大delta、不修改限位，也不自动进入云端、实体或留出种子。

### 2026-10-04 起步5倍采样唯一训练，离线方向门控未通过

**Current / Done：** 用户授权新源码资源预检→一次 `fit --startup-weight 5` 原120s/5000step预算→首帧/前3秒离线核验→通过后唯一纯视觉回合。采用既有Wiki“按当前任务选择验收依据”，将资源/训练/诊断与实际抓放分开。本轮源文件与dcaae70一致，无生产代码、模型结构、动作编码、精度、物理或限位修改。

[预先记录的范围](../../experiments/colab-twin/output/vision-startup5-20261004/scope.json)绑定53份顶层Python、四RGB/raw、旧d4db和原MJCF。四档顺序为nominal/prefix50/v6-450/seed23；seed0、随机ACT及随机ResNet18、fresh Adam/lr1e-4、batch8、epoch200上限。没有续载旧权重，不把本轮称为微调。若资源只通过batch4，原执行脚本会在fit前停止，以保护batch8对照。

[资源报告](../../experiments/colab-twin/output/vision-startup5-20261004/microbenchmark/report.json)actualexit0，batch8完整5step，内部3.789s/外层6.388s；peak allocated309.343/reserved332MiB，两份源码/相机/四档数据/官方ACT绑定通过。[唯一fit报告](../../experiments/colab-twin/output/vision-startup5-20261004/fit/report.json)actualexit0，3126step/120.002158s优化，total123.329s、outer125.631s；原优化墙钟上限在新更新前检查，因此最后一次更新可使实际优化时间略跨120s。本轮峰值仍332MiB，CPU同设备保存重载exact/误差0，新checkpoint SHA `8d4db85e798f53aee2d63d59cd77e35f9ca9047450dfed99cc07ae157d224afd`。总进程时间含初始化/重载保存，不当作优化预算加长。

8797唯一行、8997项池；实际25002次chunk起点，其中702次命中nominal原始0–49行（2.808%），2完整池＋第3池部分抽样。重构与成功更新计数一致，frame0见13次、所有唯一行都见过；归一化与旧四档完全相同。旧1312步对应10493次起点/61次起步；同120s并非等步数因果消融，不能把预测改善只归因权重5。

**离线准入在新模型预测前固化。** [门控定义](../../experiments/colab-twin/output/vision-startup5-20261004/offline-gate-spec.json)要求首帧五轴方向与专家相同且delta比0.5–1.5；首10拍逐轴同向100%且有向投影0.5–1.5；前150拍逐轴MAE及整体方向投影不劣于旧保存数组、投影后的jaw全open。0.5–1.5是本轮保守的诊断准入，新设而非既有物理门槛，不能替代原抓持/释放/稳定判据。

[离线报告](../../experiments/colab-twin/output/vision-startup5-20261004/offline-report.json)actualexit0/outer7.754s，唯一150次batch1/no_grad CUDA前向，仅专家nominal原始0–149（elapsed0–2.98s），0优化/渲染/积分，源码和172模型张量均不变。旧对照来自保存batch8/inference_mode数组，不绕过新源码load gate加载旧d4db；接近浮点噪声的差值不宣称训练收益。[完整预测与目标数组](../../experiments/colab-twin/output/vision-startup5-20261004/offline-predictions.npz)。

| 首帧h0，mrad | 新策略delta | 专家delta | 方向 |
| --- | ---: | ---: | --- |
| shoulder_pan | -0.105538 | +2.317555 | 反向 |
| shoulder_lift | -0.738442 | -1.471036 | 同向，比例0.502 |
| elbow | -0.657571 | -0.947236 | 同向，比例0.694 |
| wrist_flex | +0.053319 | -4.805772 | 反向 |
| wrist_roll | +0.012467 | -2.510750 | 反向 |

首10拍同向率90%/100%/100%/80%/90%，幅度投影逐轴在0.5–1.5且整体0.179→0.749；第10–29、30–49、50–149方向全对。前150逐轴MAE均改善、五轴均值0.638→0.346mrad、整体投影0.954→1.066，但首帧投影0.115→0.031，不能用前3秒平均改善遮掉最初错误。门控3项未过（首帧方向/幅度、首10方向），`rollout_allowed=false`。

[独立Codex结果审核](../../experiments/colab-twin/output/vision-startup5-20261004/independent-report.json)actualexit0，69项通过：CPU元数据与禁止构模哨兵核新load绑定/旧d4db拒绝，独立重建采样计数、重算全部切片和门控；旧解码h0目标与raw action最大差实际0。末次53源/四RGB/新旧checkpoint哈希不变，0模型构造/前向/CUDA kernel/训练/渲染/物理，5份公开文档数值和验收边界一致。

**Remaining / Issues / Next：** 本轮按门控停止，新物理回合not_run，不写成新抓放0/1，也不重试训练/加预算/放宽限位。S7e仍未通过、旧d4db关节限位失败保留。root保留新模型、完整采样与预测证据；下一最短候选是只读核首0–9拍与起点附近收尾样本的输入和标签，区分局部拟合、观测相似性和动作监督；未做，不预先定视觉/动力学唯一原因。本轮没有新AGY/ZCODE会审；独立Codex结果审核单独存档，runtime及旧现场资料继续排除发布。

### 2026-10-04 首0–9拍观测与动作标签只读核验

**Current / Done：** 用户指定“检查首0–9拍的观测与动作标签”。范围仅CPU读取四同步RGB/raw、旧/新保存预测、专家路线和seed0抽样重构；[范围与哈希](../../experiments/colab-twin/output/vision-first10-audit-20261004/scope.json)固定53份顶层Python、新8d4db/旧d4db模型及四RGB。本轮没有新模型构造/前向、CUDA计算、优化、相机渲染、MuJoCo积分或抓放。

[标签审核](../../experiments/colab-twin/output/vision-first10-audit-20261004/labels-report.json)actualexit0，62/62通过，真实四raw SHA实算且与RGB provenance一致，全部raw列完整复制/float64保留。nominal首10全valid、未扰动、jaw .5，专家五轴delta每帧为 `+ − − − −`；另外三档raw0–9全invalid，首valid0/50/450/161，不混入起步监督。新/旧保存h0目标与raw action_t最大差0，执行command也与action exact；RGB frame/time对应obs_t，next_q_t=下一行q exact，20ms/2ms契约保持。

独立用保存参考路线及当前q_t重算lookahead动作，最大差6.94e-18rad；故意改用next_q重算则差6.510mrad。源码 `grasp_episode.py:289–299,373–377` 是当前observe→设command→积分→保存，`learning_vision.py:299–302,339–342` 保留原始valid索引并以chunk起点q编码。支持标签没有一拍错位；没有新重放/渲染验证像素生成。absolute1.00–1.18s对应elapsed0–0.18s。

[观测和保存预测报告](../../experiments/colab-twin/output/vision-first10-audit-20261004/observations-report.json)actualexit0，内部1.402s，8797合法起点中只缓存379幅已有RGB；[原数组](../../experiments/colab-twin/output/vision-first10-audit-20261004/observation-arrays.npz)保留输入、目标、预测、候选pixels与实际chunk起点访问。不是新网络推理，第2–9拍方向结论只限专家观测。

| nominal原始帧 | elapsed秒 | 保存h0方向错误轴 | 作为chunk起点的重构次数 |
| --- | ---: | --- | ---: |
| 0 | 0.00 | shoulder_pan / wrist_flex / wrist_roll | 13 |
| 1 | 0.02 | wrist_flex | 14 |
| 2–9 | 0.04–0.18 | 五轴同向 | 各13–15 |

[首10五轴残差图](../../experiments/colab-twin/output/vision-first10-audit-20261004/first10-deltas.png)由保存数组生成，蓝线专家target−q、橙线新模型h0−q。方向错误局限于首两拍，未宣称其幅度拟合或真实策略起步通过。

**相近关节观测与收尾。** 描述性q6 L2≤0.01rad半径内，frame0有366有效邻居：approach2/retreat64/settle300；训练中这些行作为chunk起点共27/178/834次。frame1有371近邻，frame2起局部近邻仅approach3。访问次数通过3126更新/8997池/seed0重构，起点次数不等于chunk尾部标签总曝光或梯度权重。stage和物体真值只用于审计，不进入策略输入。

frame0最接近RGB的非起步邻居为同nominal frame2349 settle：q6 L2差0.000137rad（0.137mrad）、最大单轴差0.0914mrad；物体位置从[.24,-.13,.009921]移到[.238622,.139171,.009921]，相差269.17mm。128×128图有203像素变化，变化像素平均绝对差23.31uint8、全图平均仅0.2888uint8，后者受静态背景稀释。[保存RGB及差异图](../../experiments/colab-twin/output/vision-first10-audit-20261004/first0-neighbor-rgb.png)可见工件分别在红/蓝盘；图为已有pixels排版，不是新仿真渲染。

[同锚目标对照](../../experiments/colab-twin/output/vision-first10-audit-20261004/target-comparison.json)：首帧五轴预测绝对目标距起步标签6.03899mrad、距frame2349收尾标签0.413573mrad；等价于用同frame0 q重新锚定两份标签。输出更近收尾成立，但q/RGB均不同，不是假定同输入的反事实模型试验。首10对应候选中没有完全相同raw q6＋RGB或归一化float32 q6＋RGB却标签不同的行；像素近似不证明模型视觉特征相同。

[独立方法与结果审核](../../experiments/colab-twin/output/vision-first10-audit-20261004/method-review.json)86/86通过，0构模/前向/GPU/物理：重新核全部10帧近邻、delta、stage/visit计数、q与RGB精确冲突统计、top pixels、统一锚目标距离及真实物体位置，53源/四RGB/新旧checkpoint哈希不变。labels62和method86为不同审计集合，不加成学习成功指标。绘图开始误选无matplotlib的学习/内置运行时，两次import失败都在读输入前，日志保留；改用已有系统Python绘制NPZ，未安装或修改依赖。

**Remaining / Issues / Next：** 标签轴序/同拍错位没有证据，优先保留起点与收尾观测的局部辨别不足/监督竞争候选；不称已证明视觉忽略或状态本身不可解。root下一最短入口是同frame0 q6下替换原起步/收尾RGB的有界反事实前向，检查预测是否随图像切换；本轮未做，不重训、改主干、增权重、加阶段/时钟输入或放宽限位。S7e方向门控/视觉抓放仍未通过，0新物理回合，全部新图/脚本/日志/数组继续Git忽略。沿用Wiki“按当前任务选择验收依据”；没有新AGY/ZCODE会审，原现场22/index/README/模型保留。
