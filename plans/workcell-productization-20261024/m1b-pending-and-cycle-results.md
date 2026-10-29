# 闭爪等待漂移与完整50Hz诊断

2026-10-29，R143原源码 `78a9edaeeaf9a90b066f7590e2162621246597dd`，Kaggle `muqiaoqiao/so101-closure-pending-observation-20261029/1` 一次提交，四例串行终态。没有生产异步证书准入或默认变更。

## 实际干预与原裁判

在原下降到位条件成立时，pending组保持原开爪目标额外 `.6s` 仿真时间；期间仍执行每拍实际姿态、在线弦、物理推进与所有原保护。等待后再以**当拍实际q6**执行原完整 measured closure。baseline使用同观察器但不增加等待。左右顺序为 B→P、P→B；右侧高位预收爪不延迟。

此举验证等待期间的真实漂移，不是加速候选。原90sim／120wall、阶段超时、1mm、285对、244／原246均保持。观察先存内存，原清理后落盘；其开销包含在原完整周期，不从成绩扣除。

| 回合 | 原任务 UUID | 原裁决 | sim s | process wall／CPU s | 完整拍 |
| --- | --- | --- | ---: | ---: | ---: |
| 左224基准 | `bf6c93a8-cf0f-4ae4-9323-4773573b6011` | pass | 75.28 | 50.670562／59.897561 | 3764 |
| 左224等待 | `71608e2d-d8f4-4d89-a2ab-2111f394a91f` | pass | 75.90 | 49.556968／58.658296 | 3795 |
| 右256等待 | `2694327f-7cb0-4254-a203-9e5879fb447a` | pass | 79.00 | 50.798248／60.487083 | 3950 |
| 右256基准 | `639ba731-46ad-4771-89d1-1c041d36b8ed` | pass | 78.52 | 49.878168／59.274472 | 3926 |

四回合抓放、静稳、释放脱离回位全部通过；安全停机和障碍接触0，自由物体、weld0／mocap0及worker consumed／joined／owned_ack保持。左原两次完整244，右原三次完整246；所有原checked等于required，观察器与原扫掠报告精确相符。没有用等待帧变化冒充加速。

## 漂移：能等待，但旧姿态证书不能直接复用

左右pending各采31条输入，保持的reference／command均未改变，实际最大关节漂移分别 `6.141952046956334e-8`、`1.2591399145556181e-8rad`。六轴都落在R132拟议 `±1e-7rad` 箱内。首到位与新扫掠的原采样数仍244／246。

但“同采样数”不等于“同采样姿态”。独立按原binary64插值重建，左只有最后1/244、右只有最后1/246个样本逐位相同，其余都变了。exact-q缓存不能覆盖整次扫掠；不能把小漂移舍入成0。

R132尚缺实际FK数值覆盖、有效观测／模型所有权／取消交接；本轮只补了保持开爪的真实漂移及首尾网格计数，未完成覆盖证明。`production_admission_allowed=false`继续保留。报告中的fresh end与采样reference逐位比较为false，来自原终点与轨迹插值的末位差异，不替换原终点或放松比较。

## 完整周期与剩余慢拍

| 回合 | P50 ms | P95 ms | P99 ms | 最大 ms | >20ms拍 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 左基准 | 9.609 | 16.375 | 28.341 | 50.161 | 84 |
| 左等待 | 9.530 | 15.701 | 28.340 | 48.857 | 80 |
| 右等待 | 9.503 | 14.584 | 32.351 | 50.191 | 110 |
| 右基准 | 9.452 | 14.700 | 27.594 | 49.929 | 77 |

15435个完整周期、0个partial，四回合全部有>20ms拍，**完整50Hz未通过**。EpisodeTiming只有连续分段时长和仿真时标；没有实际计划释放／绝对deadline，因此调度违约数为null／unknown，不把计算超预算计数冒称调度违约。

总计351个慢拍：hold176、release97，合计273／351（77.8%）；close4、preclose2。原下降后全扫本轮31.317～37.332ms，右高位预收爪31.389～33.342ms；不能把其它源码／机器上R127的441.843ms当成当前耗时，也不能把跨环境差异记成本轮提速。

阶段和section重合只定位范围，不能据此断言是GC、GIL、磁盘或某个查询。持物和释放仍保留原worker、实际姿态和载荷保护。下一项优先按同回合细分hold／release的当前调用成本；不重做已淘汰的GC窗口，不以闭爪异步一项声称可清除全部慢拍。

## 原件、校验与收尾

`experiments/colab-twin/output/closure-pending-observation-20261029/kaggle-v1/so101-evidence.tgz` 保存四份原evaluation、report、planning、timing、trajectory、jaw-sweeps、观察器和视频。独立读回为同目录 `independent-readback.json.gz`，单遍流式读取，无缺件／歧义。根另回读原cloud终态、原report和逐拍sections。

私有入口：`~/.cache/ros2-factory/codebuddy-so101-20261021/round143-closure-pending-observation/`。`pending_launcher.py`与`test_pending_launcher.py`分别为实际观察器和9项纯逻辑测试；计时边界曾在提交前修正，加入受控时钟反例，云端使用修正版。`summarize_result.py <TGZ> --output <JSON>` 的5项合成检查通过，但实际结论只来自上述原物理件。

下载仅TGZ，没有展开视频或帧。派生JSON压缩后逐字回读再删除展开件，恢复 `gzip -dk independent-readback.json.gz`；保留全部原件、配置及失败。cleanup回执记录实际释放字节。Knowledge=already_covered，沿用Wiki§20真实调用输入与组件／整程分开；Owner=根Codex。

## R145：当前同回合的持物／释放调用归因

Kaggle `muqiaoqiao/so101-hold-release-attribution-20261029` 使用同一 `78a9eda` 源码、X224／54mm／.35输入和原裁判。v1原物理pass，但观察器落盘遇到NumPy布尔值，细分记录缺失；保留此失败，不据其归因。只修JSON数值标量转换并补13项测试后提交v2，原控制器与计时边界不变。两版接收源码均逐字核对。

| 版本 | 原任务UUID | sim s | process wall／CPU s | 完整拍 | P95／最大 ms | >20ms拍 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| v1，细分记录缺失 | `2206345b-0369-438f-9122-68aff9c539a4` | 75.76 | 59.398710／69.750292 | 3788 | 18.967126／94.759683 | 170 |
| v2，细分记录完整 | `360bf3f4-ae3a-4169-bbea-9c691a0576cf` | 75.90 | 49.994158／59.095877 | 3795 | 15.831228／51.706794 | 91 |

表内分位数使用linear插值。两次均原pass：真实抓放、释放脱离回位、246×3、双worker consumed／joined／owned_ack、安全与障碍接触0。v2持物30.58s、静稳7.54s、释放XY漂移.173373mm、脱离后峰力0N。不同VM的两行不是性能A/B，不能把差值归功于序列化修复。

v2的556条进入hold／release的更新全部唯一匹配原完整周期，observer错误0、恢复检查全过。进入hold且运输worker running的102拍有52慢拍；进入release且分离worker running的48拍有21慢拍。两个worker尚未启动的对应105／301拍无慢拍。这里按更新进入阶段分类，原timer按更新后的阶段记名，包含两次阶段切换，不能把两种分组直接混加。

- `_async_transport_binding` 209次共105.581ms，`_separation_binding` 101次共54.669ms；单次P95约.625／.613ms。重复快照不是当前主要长尾，不继续仅抠绑定索引。
- 最慢交接拍51.706794ms中，controller44.140375ms／线程CPU35.023576ms。顶层包含poll20.726815ms、ratchet9.511179ms、在线sweep6.192945ms、path4.282392ms、context .616415ms及残余2.810629ms。poll内还有子检查，不能再叠加父子耗时。
- worker运行中常规hold拍也出现controller30.144485ms／CPU16.695716ms，包含sweep18.706116ms／CPU9.166872ms。窗口重合和wall−CPU只证明相关等待，不能直接命名为GIL原因。
- 原poll使用 `join(timeout=0)`，没有阻塞等规划结束。无参join属于回合清理；不能删除清理来制造周期通过。

原完整周期仍91拍超20ms；没有计划释放／绝对deadline记录，截止违约数继续unknown。**完整50Hz未通过。** R132的后台闭爪覆盖证明仍独立缺失，一项worker调度改进也不能替代完整246认证。

旧F2bo的1ms解释器时间片已在第二工位反证，保持淘汰，不重做。下一项限定为既有真实guard输入＋原运输规划器的Thread／spawn进程隔离组件对照：先验证模型、快照、结果传递与取消／退出，三对检查输出及规划路径相同，再考虑原物理。当前只有实验设计，尚未提交云任务或接生产，不新建调度平台。

原件位于 `output/hold-release-attribution-20261029/kaggle-v1/` 和 `kaggle-v2/` 的TGZ；同目录 `v1-physical-readback.json`、`v2-physical-readback.json` 及 `v1/v2-method-readback.json.gz` 分开保存物理与细分核验。私有 `round145-hold-release-attribution/` 保存v1原launcher、v2修复、builder、接收源码和复跑入口。观察器全部开销仍计入原周期；6项reader缺件／嵌套反例通过。
