# R152–R156：真实节拍、双规划进程与实际输入诊断

日期：2026-10-29。Owner：根 Codex。来源：根 GPT 与原生 GPT 子 Agent。

## 结论

组合运输与释放进程后，两个 X 位置反序原物理 4/4 通过。真实 20ms 调度下，慢拍与截止期违约都减少，保留显式实验候选。初始化与 CPU 成本增加，整程没有提速；最大拍仍超过 20ms，**完整 50Hz 未通过，不切默认**。

连续 X 使用已有 [统一开发配方](../../experiments/colab-twin/scenarios/workspace-station/fixed-tray-x-editable.json)。只改 `pickup_request.position[0]`，方块、接近点与抓取点联动。开发建议范围 224～256mm，Y=-130mm；224/240/252/256mm 已原物理通过，不代表所有中间位置必成功。原逐请求 RGB、IK、碰撞及完整扫掠仍执行，详见 [X 结果](m1a-x-unified-recipe-results.md)。

## 固定条件与实现范围

- 生产／裁判／控制器固定 `95ca4a57cd5b036fa98e7bb746dacc46c6b8b171`；文档 HEAD 不替代实际源码来源。
- X224 原版→组合，X256 组合→原版。每对同一 Kaggle VM、同一输入；跨 VM 秒数不累计。
- 组合薄入口直接导入冻结 R147 transport、R150 separation 与 R153 pacing。安装 T→S、卸载 S→T，原准备只执行一次；两个 worker 独立拥有原模型。
- 唯一异常修正：R147 预热回收状态不明时，阻止继续线程回退及启动 S；确认回收后的原回退保留。冻结的 R147/R150 文件没有改写。
- 保留原 90s 仿真／120s episode wall、1mm、285 pairs、原三次 246 点扫掠、fresh admission、释放物避碰和回位。无目标真值进入控制。
- 两次正常预热计入原 episode 初始化。READY/native/join 仍合作退出，不声称异常时硬抢占；外层清理和最终诊断写入另计入进程 wall/CPU。
- 原物理裁判不负责 50Hz。固定墙钟 epoch、不跳拍，另记 release/start/end/deadline；末拍之后的终态清理尾段单列，不混入普通拍 deadline。未记录实际 `data.ctrl` 发令时间，不称执行器命令频率已验证。

## R154／R155 原物理与真实周期

| 位置／模式 | UUID | 原裁决 | sim s | episode wall s | process wall s | process CPU s |
|---|---|---|---:|---:|---:|---:|
| X224 原版 | 9f50aef9-17ef-4222-921f-0b3459a633fd | pass | 75.70 | 86.387708 | 87.800674 | 60.379602 |
| X224 组合 | 486cda11-d6d6-4d8a-b1e3-78364b5716b1 | pass | 75.50 | 89.945404 | 91.333637 | 66.398741 |
| X256 组合（先跑） | b569a66b-97c5-4839-96e0-c2f8272a33c0 | pass | 78.04 | 92.835161 | 94.338722 | 69.108120 |
| X256 原版 | 0174fd58-b104-4e48-8b0b-57d5a08524b6 | pass | 78.24 | 88.696047 | 90.092558 | 61.851480 |

| 位置／模式 | 完整拍 | >20ms | P95 ms | max ms | core deadline miss | 普通 tail deadline miss | 最大起步迟到 ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| X224 原版 | 3785 | 74 | 15.675366 | 58.407830 | 168 | 168 | 143.167528 |
| X224 组合 | 3775 | 34 | 14.935451 | 47.925544 | 62 | 62 | 60.178142 |
| X256 组合 | 3902 | 30 | 14.240326 | 47.596327 | 59 | 59 | 53.719155 |
| X256 原版 | 3912 | 78 | 15.486128 | 46.182460 | 183 | 183 | 140.646473 |

四例 partial=0。两位置 hold 慢拍分别 32→0、46→2；release 17→11、14→10。右侧 max 反增，不能将 P95 改善称为全部尾延迟改善。两对 process wall 增加 3.532963／4.246164s，CPU 增加 6.019139／7.256640s。sim 各少 .20s 是实际等待长度变化，不能计为算法加速。

四例抓取、放置、释放、脱离及 controller_done 均通过；无安全停机、障碍接触，free_object=true、weld=mocap=0。释放漂移左 .173228→.172137mm、右 .188495→.187061mm，脱离后峰值力均 0N。原 status/report/evaluation 与实际进程来源分别回读，不能只依赖云端 COMPLETE。

两侧独立核验确认三次246、separation2、205个保存样本 fresh 准入、连续首命令及双 worker owned_ack/joined。运输准入左29、右28，都是原 required=checked，不能固定套用左点数。组合左T PID262／S PID277，右T PID183／S PID198真实规划并exit0/joined，无fallback/cleanup error；不以仅有 `both_process_planners_active` 作结论。回位最大误差四例均约.000102544rad。

原native计数checked=native=successful、fallback0；左66808→65979、右69780→68954，随实际拍数变化，不能当跳过几何对加速。两process预热左1.709／2.180s、右1.773／2.243s；实际planner左1.264／1.101s、右1.467／1.123s；join成本也在原进程计时内，不重复相加。

## 残余慢拍与下一项证据

左侧组合 34 慢拍：approach14、preclose1、close2、transport2、release11、separate1、retreat1、settle2。

approach 中 13 拍为 .5、1.0…6.5s 的原定时感知，perception 19.305～20.332ms，完整拍 27.832～32.229ms；另 5.36s 拍来自 controller/physics/callbacks 共同耗时，不能统称 RGB。源码每次只 render 与 localize 各一次，循环录像只存状态，不存在已证实的重复渲染。

R156 已完成下文实际观察。诊断开销全计，不挪入 R154/R155 性能对照。首次 `purpose=measured_closure` 实际对应高位预收爪，不能称为最终下探闭爪。

旧固定轴 norm、静态 pair 缓存、小方向表、`-march=native` 均有无收益或收益反转记录，不重复试验。没有实际提示输入／输出，不凭六组冷提示网格猜当前 warm hint 回退成本。

## R153 原控制器单独诊断

R152 v2 同实例的独立原控制器回合 `a4bfe5d4-9c38-47f5-acb5-9cfc17ac3bcf` 原物理 pass，75.84sim／87.203845 episode wall／88.643429 process wall／64.976396 CPU。3792完整拍、105拍>20ms、P95 17.502060ms、max52.956176ms，普通截止期违约247，最大起步迟到266.772ms。

原246×3及其余准入、205保存样本、双worker回收、释放脱离回位均通过。循环内 status 写入最大2.875ms、callback最大6.023ms；终态18.063ms写入在循环外。没有复现R151的53ms callback，不能把此前等待归因于日志IO或GIL。此回合不是原版／候选性能A/B，不能与无节拍旧回合直接比秒数。

## R152 有限组件诊断与保留失败

六组原 R143 网格含244／246点。仅在原 batch 的 FK 与 query 外加计时，全部285对、方向提示／回退和完整输出保留。代码／库 warm、构造器提示 cold，不重建 R143 原拍的 warm history。

1. v1 缺 `/usr/bin/time`，组件及物理均未启动；保留失败。后改为标准库进程 wall 与 `RUSAGE_CHILDREN` 差值，不增加环境依赖。
2. v2 六组18对计时输出／结束状态相同，独立 untimed 逐点14字段也相同；但首组四个辅助 MjData 字段不等，完整六组验收失败。
3. v3 仅重测首组，`mj_copyData` 后运行前仍有同四字段差异，未运行新物理。
4. v4 只在运行前显式复制四数组，逐字段复制当时相同；整体 before/source unchanged/end 仍有辅助字段差异，完整组件继续失败，不删检查、不修结束状态、不再重复同样试验。

只取 v2 完整比较通过的另外五组15对，query占插桩 wall 的92.9366%，FK占3.7100%。这是有限成本定位，不是优化收益；完整六组不记通过。不能因该诊断影响原始物理裁决，也不能以未落盘 raw buffer 的比较回执冒充读者重新逐位核算。

## R156：原物理通过，感知子段与实际预收爪 ABI 完整

Kaggle `muqiaoqiao/so101-live-input-diagnostics-20261029` v1 终态。接收源码逐字相同，冻结95ca4a5原输入／原评分器／90sim与120episode-wall。私有观察器只记录，原渲染和native调用各执行一次；异常不覆盖原返回或原异常。无生产默认变更。

原UUID `1221c6d5-4ecd-4326-bf36-e71ea1e467e7` pass：75.78sim、86.940189episode wall、94.908196process wall、69.997289CPU。原抓放、释放脱离及回位均通过；安全停机false、障碍接触0、free=true、weld=mocap=0。原246×3／transport29／separation2完整，native checked=native=successful=66843、fallback0；205保存样本当前姿态准入及双worker consumed／owned_ack／joined均通过。释放漂移.173264mm、脱离后0N、回位误差约.000102544rad。

3789完整拍、partial0；96拍>20ms、P95 17.082563ms、max58.916409ms；core与普通tail截止期违约均230。诊断复制和回调在原拍内，后置压缩6.343208s在process wall／CPU内。不能将本回合总耗时和R154／R155跨VM相减。完整50Hz仍未通过；实际执行器发令时钟仍未记录。

### 感知主要耗时已定位

1次初始化独立列出；13次循环感知逐份匹配0.5～6.5s的approach拍、原定位结果和完整perception时间窗，观察错误0。

| 子段 | wall中位 ms | wall P95／max ms | thread CPU中位 ms |
|---|---:|---:|---:|
| update_scene | .057950 | .067834 | .058037 |
| render | 14.802738 | 14.909983 | 14.803178 |
| copy | .066404 | .075557 | .066623 |
| localize | 5.258181 | 5.482462 | 5.259492 |

实际预检为NVIDIA EGL／Tesla T4；不能将高thread CPU直接解释为软件渲染或GPU计算时间。原640×480画面的一次render与一次localize已接近20ms，copy不是主要瓶颈。已找到F2bn／R79的现成AsyncCamera线程候选，旧两工位4/4不等于当前组合验收。下一候选优先复用其快照／原worker生命周期接入当前双规划进程，保留原分辨率、RGB定位、遮挡拒绝、源时间戳与1s TTL；先同输入组件，再决定原物理。当前组合尚未实施或验收，不重造进程相机、不改为低分辨率或复用过期估计。

### 实际捕获范围与下一复用入口

捕到首个 `purpose=measured_closure`，实际stage=approach，与原 `pickup_preclose` 报告逐字段相同。246查询×285对、29几何／198996顶点，所有native status=0；bridge info=[246,-1,246,246,0]。保存完整构造几何、输入／输出、见证与方向提示；raw数组14834784B、压缩4287838B。独立结构读回完整，无回退／采集错误。含采集开销的扫掠48.812460ms不是纯native基准。

原运行还调用了第二次同purpose，最终下探闭爪仍246全扫通过，但其ABI未捕获。不能将预收爪样本冒充最终闭爪热状态，也不为补这个范围立即重跑全物理。此份实际246点已可用于独立native组件回放，先核完整输出等价再谈改进。读者曾遇NumPy2/1模块名差异；只对自有可信pickle映射模块名后成功，首次失败JSON保留，不改变raw字节。

原件：`experiments/colab-twin/output/live-input-diagnostics-20261029/kaggle-v1/so101-evidence.tgz`。根paced读回同目录；独立入口在私有 `round156-live-input-diagnostics/`：`read_physical.py`、`read_perception.py`、`readback/read_sweep_capture.py`。原物理、诊断完整性、组件复用与性能采用分别判断。Knowledge=already_covered，项目新证据留在本计划。

## 产物与复跑

原TGZ均保留于 `experiments/colab-twin/output/`（Git忽略）：

- `closure-profile-paced-20261029/kaggle-v1..v4/so101-evidence.tgz`：各版本失败／有限结果与v2原物理。
- `combined-paced-20261029/kaggle-v1/so101-evidence.tgz`：左原版→组合。
- `combined-paced-right-20261029/kaggle-v1/so101-evidence.tgz`：右组合→原版。

根按原件独立回读 deadline，原生子 Agent 独立回读原物理／全部扫掠／worker／源码。私有入口基目录：`/home/muqiao/.cache/ros2-factory/codebuddy-so101-20261021/`。

- `round154-combined-process/build_kernel.py`：冻结左同VM包；`independent_readback.py`：原物理摘要。
- `round155-combined-paced-right/build_kernel.py`：仅右输入与反序，其余payload／bootstrap／runner不变。
- `round153-paced-cycle/read_paced.py --tgz TGZ --output OUT --case-label paced_combined --case-root ARCHIVE_CASE_ROOT`：从实际archive目录选择案例；原版用paced_original，保留共同process/cloud记录。
- `round152-closure-profile/read_component.py TGZ --selected-only --output OUT`：只回读失败首组重测；v2完整六组不加selected-only。

实际云入口为 `muqiaoqiao/so101-closure-profile-and-paced-20261029` v1–v4、`muqiaoqiao/so101-combined-paced-20261029` v1、`muqiaoqiao/so101-combined-paced-right-20261029` v1。每次接纳源码均逐字回读；不重新提交未知在途请求。

7项组合owner纯测试、7项paced reader、18项组件fixture/reader检查已过；这些检查不替代上述物理结果，也未证明实际OS故障取消。R155构建只变右输入／顺序，16项纯检查通过。Knowledge=already_covered，沿用《ROS2 与 FishBot》§20的分层验收。
