# R157–R163：原生全扫、异步相机与保守距离转移

日期：2026-10-30。Owner：根 Codex。候选来源：复用 R79 AsyncCamera、R154 双规划进程和 R153 固定节拍；根 GPT 与原生 GPT 工作者完成组合、实际发令观察及独立回读。

## 结论

X224 同步→异步、X256 异步→同步，两 Kaggle 实例内分别对照，原物理 **4/4 pass**。异步相机降低了两位置的主循环感知占用、计算慢拍和发令迟到，保留显式实验候选。右侧总耗时、P95 和最大拍反增，**没有可靠整程提速，完整 50Hz 未通过，不切默认**。

连续 X 沿用[单字段开发配方](../../experiments/colab-twin/scenarios/workspace-station/fixed-tray-x-editable.json)：只改 `pickup_request.position[0]`，开发建议 224–256mm。已有四位置原物理证据；每个新请求仍做原视觉、IK、碰撞及全扫，不外推所有中间位置必成功。

## 固定条件与发令时钟

- 实际生产／控制器／裁判源码仍为 `95ca4a57cd5b036fa98e7bb746dacc46c6b8b171`。云接收源码与提交包逐字相同；右包的七份执行文件与左包完全相同，只换既有右工位和先后顺序。
- 两边都使用 R154 双规划进程；唯一策略变量为同步或 R79 异步相机。原 640×480、RGB 定位、遮挡拒绝、源时间戳、1s TTL、90sim/120episode-wall 保留。
- 两边使用相同观察器，直接在原 `data.ctrl[:]=command` 写入前后计时。逐 tick 与原完整周期、轨迹 command 对齐；观察开销仍计入原拍。写入确切时刻位于两个时钟之间，不用 controller 返回时间代替。
- 原 epoch 每 20ms 释放一拍，不跳拍。计算超过20ms、core deadline、普通 tail deadline、发令迟到、相邻指令间隔分别记录。终态清理尾段单列。
- 相机合作退出；native render 挂起时仍不能保证硬取消。正常清理通过不代替异常取消测试。

## R159／R160 原物理与运行成本

| 位置／模式 | UUID | 原判 | sim s | episode wall s | process wall s | process CPU s |
|---|---|---|---:|---:|---:|---:|
| X224 同步 | 63c8d8e0-956a-4d5e-b299-0413981c83b7 | pass | 75.60 | 90.563918 | 92.094504 | 68.547690 |
| X224 异步 | 333c1a2a-ce10-4699-8686-36c22db37629 | pass | 75.52 | 90.462430 | 91.946746 | 67.756944 |
| X256 异步，先跑 | 99e8676b-1bad-45c4-8fae-8d2c637db6b7 | pass | 78.02 | 92.822102 | 94.366800 | 68.696743 |
| X256 同步 | 205370e8-9961-4651-b7cc-ea9cfc098add | pass | 77.94 | 92.001312 | 93.593116 | 67.691429 |

相对同实例同步版，process wall 左少 .147759s、右多 .773685s；CPU 左少 .790746s、右多 1.005314s。sim 左少 .08s、右多 .08s 为等待长度变化，不记为算法加速。跨实例秒数不累计。

| 位置／模式 | transport planner s | separation planner s | T/S prepare s |
|---|---:|---:|---|
| X224 同步 | 1.335070 | 1.139070 | 1.710837 / 2.252524 |
| X224 异步 | 1.339155 | 1.076640 | 1.687286 / 2.227478 |
| X256 异步 | 1.484602 | 1.071347 | 1.731086 / 2.219815 |
| X256 同步 | 1.393050 | 1.089861 | 1.689278 / 2.263803 |

预热、模型传递、规划、回收均保留原进程计时；这些嵌套成本不能再相加成总时间。

## 完整周期与实际发令

| 位置／模式 | 完整拍 | >20ms | P95 ms | max ms | core deadline | 普通 tail deadline | 发令确定迟到 |
|---|---:|---:|---:|---:|---:|---:|---:|
| X224 同步 | 3780 | 33 | 15.255006 | 49.690406 | 62 | 62 | 38 |
| X224 异步 | 3776 | 20 | 15.045165 | 50.046988 | 38 | 38 | 23 |
| X256 异步 | 3901 | 24 | 14.176508 | 47.948455 | 43 | 44 | 30 |
| X256 同步 | 3897 | 30 | 14.089019 | 44.553631 | 56 | 56 | 37 |

四例 partial=0；发令写入括号跨截止点的歧义计数均0，表内迟到均在写入前已发生。普通 tail 仍完整核算，右异步比 core 多1次违约，不能省略。

相邻发令间隔中位均约20ms，但最大为左同步57.443／异步59.404ms、右异步56.336／同步54.343ms。平均频率与 P95 不能代替完整50Hz；此轮没有勾选该门槛。

左 approach 慢拍13→0，右12→4。主线程 perception 最大左20.835→.941ms、右20.904→1.340ms。两侧均减少同步图像占用；右剩余4拍不能全部归因图像。左采图拍 perception 中位20.262→.846ms，采图拍完整周期最大32.489→19.527ms。

异步左13、右12份循环观测全部交付且有效，源时间保持原值；交付时源年龄20–40ms。初始化另列。左14份含初始化定位记录跨模式逐字典相同。晚到不能改写为“刚拍摄”，静止目标冻结后的年龄语义也没有修改。

## 原物理与清理仍完整

四例原抓取、搬运、放置、释放、脱离及回位终态通过，无安全停机或障碍接触，free_object=true、weld=mocap=0。释放最大漂移左两例均.172283mm；右异步.187154mm、同步.186922mm；脱离后峰值力均0N。回位误差均约.000102544rad。

原 planned closure／预收爪／实测闭爪三次246点全部执行；transport admission 左29、右28，separation chord2，205保存样本的当前姿态准入完整。原 native checked=successful、无回退；没有用旧q证书或省略几何对。

运输与释放真实子进程均 ready、实际规划、consumed、owned_ack、joined、exitcode0，无未知回收或清理错误。两异步相机 context_closed／joined 均真；源绑定恢复、观察器错误与诊断错误均为空。四份独立读回证据完整；不是仅以 COMPLETE 或退出码0判成功。

## R158：保留逐像素失败，定位消费者等价

组件在同源码恢复14份已有真实渲染输入，按 AB／BA／AB 共42对。**原 `passed=false` 保留**：42对图像都非位级相同，每帧1–58个像素、总900个通道差值全部±1。同步自身跨轮42对也有41对出现同量级差异，因此不能把它归为异步独有的大幅偏差，也未证明具体底层原因。

42份原定位字典完全相同且有效，目标bbox内RGB变化0；主输入、源数组、恢复字段、时间戳与清理检查通过。保存图像用本地 OpenCV4.6.0 原公式复算，最终mask XOR均0；云版本5.0.0.93，不能把本地mask核验冒称云版本逐位证明。worker内部MjData未逐字段落盘，不补称字节一致。

据此把 R79 留作原物理候选，随后才有上文4/4实测；没有删除像素失败或改原物理阈值。组件本身不证明完整控制周期或抓放。原五项相机语义测试在云通过，sitecustomize/wrapt警告保留。

## R157：原生246点基线，不是提速结果

消费R156首个实际 `measured_closure`，对应 approach→pickup_preclose；不是最终下探闭爪。246次、285对、70110个pair结果逐字节重放一致，原flags及全部提示输入输出保留；输入未改、错误为空、handle已释放。

原生调用合计32.880268ms，thread CPU32.897964ms；创建几何context47.989425ms、缓冲准备3.979028ms、比较2.895655ms、cleanup.020581ms，组件总计92.397065ms。创建context不是每拍热点；组件不是完整周期测量。70292次轴评估已接近每pair一次，不支持继续盲调搜索顺序。

独立pair分块也不直接成立：原native有整帧回退、按geometry共享的witness提示及全对有效后提交历史，不能只拼接两个独立块来保持原结果。未制作或运行这种候选。

## 下一步与边界

两异步回合仍有同步全扫／准入慢拍。左释放段另有9拍慢：部分physics_and_guards达9–13ms，与controller相加后超时。R161随后已完成原10次物理推进、接触力、release audit、障碍扫描与末次forward的细分，实际结果如下；不能将其观察开销与前两轮混作性能A/B。

旧R132异步全扫仍欠实际binary64 FK保守误差界、当前请求网格／终点与生命周期覆盖。R143已提供小漂移实测，不用相同物理重复采集；离散差值不能替代连续偏差箱证明，也不能把原246次fresh checker调用改写为“已执行”。保持原同步认证，不降低1mm阈值。

Knowledge=already_covered：沿用 Wiki《ROS2 与 FishBot》§20的分层验收。新实测和失败留本计划。

## R161：释放段扫描成本明确，完整50Hz仍未通过

Kaggle `muqiaoqiao/so101-physics-guard-diagnostics-20261030/1` 单X224异步回合已终态。固定95ca4a5及R159七份原执行文件，只观察主线程五类调用；原10次2ms推进、两个提前退出、lazy障碍扫描、释放记录和末forward顺序保留。没有修改全局MuJoCo函数、控制器、评分器、阈值或预算。8项观察器与7项读回纯检查通过；它们不代替原物理验收。

原UUID `0615808b-d516-428b-a17e-64cdc946f803` **pass**。75.58sim／90.987089episode wall／93.129066process wall／72.297255CPU秒；真实抬升40.964419mm、持物29.96s、静稳7.54s，释放漂移.172246mm、脱离后力0N、回位误差.000102544rad。原246×3／运输准入29／脱离弦2／205保存状态fresh准入全过，无障碍接触、安全停机、焊接或mocap附着。运输、释放进程与相机均正常回收；未声称异常native硬取消保证。

运输／释放规划分别1.314716／1.132903s；预热1.725501／2.250151s。成本在原进程wall/CPU内，不再重复相加。

3779拍全部对齐原周期、实际command和观察器；37790次mj_step及障碍扫描、7490次force/audit、3779次末forward完整，未遇提前退出或原异常。原观察器errors=[]，读回errors=[]。**29拍>20ms，P95 16.030250ms、最大87.787303ms；core与普通tail均75次deadline违约，实际发令46次确定迟到。完整50Hz未过。**

| 释放段每拍，364拍 | 中位wall ms | 最大wall ms |
|---|---:|---:|
| 10次mj_step合计 | .932031 | 3.710224 |
| robot_target_force合计 | 1.619086 | 4.778138 |
| release_audit.update合计 | .364409 | .767146 |
| 障碍接触扫描合计 | 1.274863 | 5.130250 |
| 末次mj_forward | .083012 | .322792 |

以上为互不重叠调用，不能再与父段相加。释放14慢拍；29个整程慢拍中21拍最大原子段为controller、8拍为physics_and_guards。最大87.787ms在settle，controller80.090ms，physics仅4.302ms；本次未继续细拆controller，不能断言GC、日志或某个几何算子是该尖峰根因。

释放tick3335／3336／3337外层残余wall为6.138／5.580／9.047ms，thread CPU仅.607／.594／.616ms。残余包含原分支、参数构造、记录及观察器本身，不能当纯Python计算量。全部观察成本留在原完整拍内，没有扣除或包装成提速；39.6MB原JSON仅在TGZ内保存，未展开副本。

下一片R162只验证原R156预收爪的几何距离转移：保留每个新点的实际FK输入，以compiled局部顶点包络计算几何位移上界，再从原距离下界扣除两物体位移；不足原1mm即回原全扫。当前仅组件准备，尚无新物理或性能通过。原R156最小下界3.225805mm提供首片余量，但不代表最终下探或任意新请求。它是新的保守证据类型，不能冒称原native numeric/hints逐位相同，也不能把两种下界的大小关系当真假裁判。

## R162：距离转移有组件收益，真实新请求尚待验证

Kaggle `muqiaoqiao/so101-affine-transfer-component-20261030/1` 已终态。原95ca4a5、原native编译配置、R156首个approach→pickup_preclose的246点／285对保持。新旧姿态取同次真实扫掠的相邻binary64 p/R；未做新请求FK、物理推进或控制器接线。15项纯数组／fake反例通过，不能代替原物理。

候选用29个compiled几何的局部顶点包络，逐乘加向外舍入计算几何位移上界，再从旧距离下界扣除两物体位移。每个点和每对都保留；余量不足、输入或上下文不适用时要求原整次全扫。它产生新的`affine_distance_transfer`证据，不冒称原numeric／hint逐位相同。两个保守下界不必有相同数值或固定大小关系。

三对顺序为native→transfer、transfer→native、native→transfer。原native全部70110对完整输出精确复现；三次转移完整，246个点索引对齐，全部70110对保留原1mm。旧最小下界3.225805mm，新最小下界3.130639mm。4行的348项Fraction分量包络及1140项下界减法核验通过，errors=[]。

| 对 | 原native调用 ms | 原context创建 ms | 原完整case ms | 转移准备 ms | 转移计算 ms | 转移含校验／读回 ms | 转移完整case ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 31.371 | 40.004 | 79.269 | 18.103 | 6.414 | 7.108 | 27.451 |
| 2 | 34.079 | 39.456 | 81.721 | 14.943 | 6.991 | 7.609 | 24.693 |
| 3 | 34.540 | 38.424 | 81.030 | 16.807 | 7.366 | 8.023 | 27.081 |

创建context不代表原快环每次的成本。当前转移仍有15–18ms准备、约7–8ms计算与核对；三次完整转移case均超过20ms，不能只拿原完整case减去转移内核声称提速。共同输入读回401.177ms、native加载15.673ms、组件入口830.051ms和进程1.023650s另列。此处没有抓放成功或完整50Hz新成绩。

独立流读核实738条native比较记录、原输入未改、handle释放及四份实际执行源码与冻结包一致；NPZ逐点最小值与各次报告一致，errors=[]。档案保存了当时的字节比较结果，没有另存每次native输出和每次转移完整数组，因此本次不冒称重新计算了这些未保存数组。非致命sitecustomize缺wrapt警告保留。

保留这个小候选，下一片R163补真实FK：按原MuJoCo3.15.0、原XML／资产、同geometry及pair顺序先复现旧246点p/R，再测试明确标注的合成小偏移。实际新请求、owner／取消世代／采样器／终点绑定、hint与回退生命周期仍未通过；当前IEEE最近舍入／渐进下溢假设须在接线前核实。不得用同网格相邻行充当后来请求，也不直接消费旧q证书。

## R163：真实FK与合成小偏移组件通过

Kaggle `muqiaoqiao/so101-fresh-fk-transfer-20261030/1` 复用原XML、原资产路径和MuJoCo3.15.0。29个compiled几何、IDs及285对顺序逐字节一致；原246点的p/R全部精确复现。zero组通过原完整numeric／flags／hint／direction比较，随后才运行五个臂轴各±1e−7rad的十组合成偏移；夹爪与原网格保持。不是后来实测漂移、任意关节盒或连续X域证明。

11组每组246×285均通过原native和转移1mm检查，转移最小下界3.225761mm；原同线程算术环境有效，RN、FTZ=false、DAZ=false、渐进下溢保留。全部Fraction抽查通过，errors=[]，native owner已关闭。9项pure/mock检查仅验证适配，原模型／native／FK实际运行均在云端。

独立流读确认四份执行源／20506B原XML／native flags与冻结输入一致；11份NPZ全体有限、shape／dtype正确，逐轴偏移和jaw保持准确。每条逐点最小值与数组一致，原native与转移各771210对完整。此读回不重新加载模型；旧geometry/pR/zero输出一致来自本次云实际比较记录。

| 成本 | 实测 |
|---|---:|
| 一次性模型＋checker建立 | 577.534ms |
| 一次性原数组／顶点包络预备 | 24.880ms |
| 一次性旧表绑定副本 | .131ms |
| 每组fresh FK含限位检查／复制 | 5.869–7.673ms |
| 每组转移含验证／结果整理 | 6.046–9.611ms |
| 同组fresh FK＋转移相加 | 12.477–16.231ms |
| 同组fresh FK＋原bound-frame链相加 | 46.844–71.204ms |

两项同组互不重叠计时之和只是组件估算；不是一次已测的控制周期。原bound-frame链包含Python复制与记录，不能当R162纯C调用。Fraction审计／压缩落盘另在每case总wall内；组件入口2.432s、完整进程2.671s。未剔除准备成本，也不宣称完整50Hz通过。

下一片仅把预收爪候选接到既有控制器：激活前用当前工位的nominal approach准备旧表，当前请求仍用原sampler和全部fresh FK，覆盖不足执行原全扫。原当前SweepBinding、异常与取消、最终下探闭爪及其它阶段保持。同步在原版／候选两侧观察普通settle调用，以定位R161的2点扫掠尖峰，不把87.8ms误记成246点闭爪阻塞。

## 原件与复跑

原TGZ位于 `experiments/colab-twin/output/`，Git忽略，未重复展开模型或帧：

- `input-components-20261030/kaggle-v1/so101-evidence.tgz`：R157／R158组件，包括像素失败。
- `paced-camera-composition-20261030/kaggle-v1/so101-evidence.tgz`：R159左同步→异步。
- `paced-camera-right-20261030/kaggle-v1/so101-evidence.tgz`：R160右异步→同步。
- `physics-guard-diagnostics-20261030/kaggle-v1/so101-evidence.tgz`：R161原物理与五类调用原件；同上一级`method-readback.json/.md`为独立读回。
- `affine-transfer-component-20261030/kaggle-v1/so101-evidence.tgz`：R162云组件、完整逐点结果、NPZ与实际执行源码；上一级`independent-readback.json`为独立读回。
- `fresh-fk-transfer-20261030/kaggle-v1/so101-evidence.tgz`：R163原模型与11份新states／p/R／native下界／转移下界完整NPZ、报告、执行源码；上一级`independent-readback.json`为独立回读。

云入口分别为 `muqiaoqiao/so101-input-components-20261030/1`、`muqiaoqiao/so101-paced-camera-composition-20261030/1`、`muqiaoqiao/so101-paced-camera-right-20261030/1`，均已终态。包内保存实际源码、输入、原报告与进程计时。

私有可复跑目录前缀 `/home/muqiao/.cache/ros2-factory/codebuddy-so101-20261021/`：

- `round157-native-abi-replay/replay_native.py`：原生重放；需要原R156输入及原编译配置，在云执行。
- `round158-camera-composition/build_kernel.py`：原组件包；`read_camera_rgb.py`只读已保存图像。
- `round159-paced-camera-composition/launcher.py --source-dir SRC --station FILE --output OUT --camera sync|async`：原评测薄入口。相邻冻结依赖由 `build_kernel.py` 完整打包，不另造执行器。
- `round160-paced-camera-right/build_kernel.py`：复用R159原包，只换右输入和反序。
- 两物理目录的 `read_result.py --tgz TGZ --output JSON`：标准库原件回读，同时写MD；右reader保留28点准入。对应纯反例8项／3项通过，不当物理通过。
- `round161-physics-guard-diagnostics/build_kernel.py`：复用R159，单case诊断；`physics_guard_launcher.py --r159-launcher FILE --source-dir SRC --station FILE --output OUT`固定原async。相邻`read_result.py --tgz TGZ --output JSON`保留单case来源、原裁判、实际发令与逐tick叶段读回，7项反例通过。
- `round162-affine-transfer/build_kernel.py`：复用R158原bootstrap，引用R156原件；`component_probe.py --tgz TGZ --source-dir SRC --output JSON --native`在云执行三对组件，不推进物理。冻结算法及假设见同目录`affine_transfer.py`与`HANDOFF.md`。
- `round163-fresh-fk-transfer/build_kernel.py`：同bootstrap及R156原件；`fresh_fk_probe.py --source-dir SRC --tgz TGZ --output JSON`仅在云执行真实FK/native组件。`--inspect-only`只读XML与数组，不建模型。

本轮cleanup收据与空间变化见[progress.md](progress.md)及右侧output目录。原失败、最终证据、源码与可恢复输入保留。
