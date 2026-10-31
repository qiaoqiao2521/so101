# 阶段准入收口：R165 GC与17点工程面板

日期：2026-10-31。按用户决定保留现有栈、停止R164周期内转移A/B。实际通道为根GPT＋原生GPT，Kaggle `muqiaoqiao/so101-staged-gc-grid-20261031/1` 已COMPLETE。原执行与评分源码固定95ca4a5；私有入口仅覆盖已有GC字段和计时／观察器，没有启用R164预收爪转移。

## 同机GC单变量原物理

同一VM串行automatic→deferred，同X224／54mm／.35、原同步阶段采图和双规划进程。两侧同GC hook、settle调用观察、逐拍三时钟。正常／中断拍保留原perf/thread，另记录process CPU；进程CPU包括本进程其它线程，不包括规划子进程。原90sim／120episode-wall、1mm、285对及所有物理判据保持。

| 原结果 | automatic | deferred |
|---|---:|---:|
| UUID | cac73e0c-1f5e-4b15-ade6-beb3bcfe9a6d | d31c4927-d5c2-47e7-85ea-ce55174a2106 |
| 原裁决 | pass | pass |
| 仿真 s | 75.52 | 75.60 |
| 原episode wall s | 90.579134 | 90.583407 |
| 外层pair记录process wall s | 92.485576 | 92.189811 |
| 外层pair记录CPU s | 69.965027 | 68.937320 |
| 完整拍数 | 3776 | 3780 |
| core wall P99 ms | 20.014182 | 19.071685 |
| core wall最大 ms | 69.557513 | 48.773029 |
| core wall >20ms拍 | 38 | 31 |
| process CPU最大 ms | 48.664823 | 48.761227 |
| process CPU ≥20ms拍 | 35 | 28 |
| thread CPU最大 ms | 48.675500 | 48.768527 |
| core deadline违约 | 69 | 62 |
| 发令确定迟到 | 45 | 34 |
| 控制期GC事件 | 149 | 0 |

两例真实抓起、放置、静稳、释放、脱离和回位通过。原246×3、运输准入29、脱离弦2及205保存状态fresh准入完整；无安全停机或障碍接触，free_object=true／weld=mocap=0。释放XY漂移.172283／.172319mm，脱离后力0N；两native规划进程exit0、joined及清理确认。

独立流读307项检查全部通过，根复用原R159物理／时钟reader再次核原报告与来源，`actual_pair_complete=true`，read_errors与额外观察errors均空。内部combined receipt的91.359939／91.035684s是嵌套区间，不能替代外层pair进程时长，也不能相加。

## GC是已观测的一项来源，不能解释全部尖峰

automatic控制期有136次gen0、12次gen1和1次gen2。gen2实际32.302936ms，callback执行线程CPU32.289227ms；它与tick2059／sim41.18s的transport controller段重合，该拍core wall44.939408ms。deferred控制期GC为0，原DeferredGCWindow在清理时collect并恢复原enabled状态，loader／callback／timing／update绑定均恢复。

GC事件没有保存callback线程ID，因此记录的是时间区间与CPU的重合，不额外推定所有callback都来自主线程。R161的87.79ms发生在另一VM／普通settle，本轮没有复现同一尖峰，不能倒推旧尖峰必为GC。

本轮settle子调用均无20ms尖峰。automatic／deferred的configuration_sweep最大2.288／1.657ms，released_chord最大7.357／4.334ms。原32.3ms GC在transport，不把它记成settle查询。

延期后wall P99已低于20ms，但process CPU仍28拍≥20ms，**D007软实时门未过**；旧完整50Hz同样未过。最高CPU拍依然是close阶段原全扫（controller42.221ms）和approach采图（perception约20ms再加其它成本）。不能把原中位耗时相加写成3–5ms保证。本轮总wall差约.296s且sim多.08s，不宣称已得到普遍整程加速，不切默认。

## 17点X工程面板

在同次实际固定盘planning模型上，固定Y=−.130m，X=.224至.256m，每2mm一格，共17点；每点从原R142参考q6独立求解。统一54mm／.35，复用原probe_workspace／原IK／完整抓取扫掠。没有新增RGB、物理episode或新规划器。

17点的approach／down／lift三阶段IK和五项full sweep全部通过；preclose及closure各246点，保留原285对／1mm。组件10.873506wall／8.799416CPU秒。原summary中的`not_admitted_points=17`保留：它是离线筛选，不是执行准入。

**17/17的start→approach直连诊断路径均无效，原失败保留。** 这不代替已有OMPL绕障，不能说17点全路径直连通过。原224／240／252／256mm物理锚点仍各有独立证据；本面板不证明所有中间X或未生成轨迹安全。连续域还缺IK分支及格点间几何变化上界，不靠平滑性或原最低1mm补称已证。

## 阶段解耦的实施边界

R164停止，不再运行其inline A/B。现有return／separation的start→poll→peek→fresh bridge→consume生命周期可复用，但释放后专用样本守卫不能直接用作预收爪证书。两个桥接点只覆盖桥本身，不能覆盖当前arm偏移下的整段jaw。

最小所需证据是阶段前的“整段jaw＋允许arm跟踪偏差”包络；执行期只做该包络命中、限位、跟踪与原接触保护。可复用私有R132 geometry_radii／向外运算，重建当前246点及相邻jaw区间；实际FK舍入与允许跟踪范围仍待核。未覆盖时保留原安全行为，不能新建空壳worker后默认放行，也不暂停物理或扣掉等待时间来称完整50Hz。

性能支线停止新增算术微优化。后续围绕上述一次阶段准入、明确静态目标的按需采图、经认证的撤退与重定位做可验收行为切片，再冻结20＋20。性能指标与任务成功分别报告；首次失败／恢复后成功分别统计。

## 原件、复跑与限制

- 原TGZ：`experiments/colab-twin/output/staged-gc-grid-20261031/kaggle-v1/so101-evidence.tgz`，保持Git忽略，未展开模型／视频。
- 同上一级`method-readback.json`与`independent-physical-readback.json`为两路读回。原云stage最终保存为`x17-original-screen`，因为command更新了stage字段；其后`x_grid_result=completed`、完整原件与原生COMPLETE均已核实。reader显式核此终态组合，没有改原日志或裁决。
- 私有入口：`~/.cache/ros2-factory/codebuddy-so101-20261021/round165-staged-gc-20261031/`。`build_kernel.py`复用冻结R159 bootstrap；`gc_launcher.py --r159-launcher FILE --source-dir SRC --station FILE --output OUT --gc-mode automatic|deferred --observe-settle`，只在云端运行。
- `x_grid_probe.py --scene XML --output JSON`是原离线工程探针。`read_result.py --tgz TGZ --output JSON`只读原件，不载模型。
- 12项pure/mock验证GC开关、三时钟、原异常与绑定恢复，原输入parser核17点；它们不代替本节两例原物理。

默认未切换，无实体／Mint改动。Knowledge=already_covered；新选择与项目实测留D007及本计划，沿用Wiki§20分层验收。清理与实际空间见progress。
