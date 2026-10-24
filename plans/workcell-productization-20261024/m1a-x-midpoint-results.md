# M1a/M1b：固定盘 X 请求的接近路径搜索对照

## 结论与保留边界

显式 `loaded_jaw_midpoint.py` 候选在两个已有工位完成反序原物理对照，四例均为原裁判 pass。本批左侧进程 wall 少14.621s、CPU少14.751s；右侧 wall 少2.547s、CPU少2.659s。收益集中在初始化的接近路径 shortcut，保留为可复跑候选，默认仍为原 loaded-jaw 策略。

该开关改变 `shorten_path` 对直连弦的试探顺序，**不是 IK 求解器、IK 高度搜索或 OMPL 算法改动**。原云 provenance 的描述把它写成“IK search order”；原件保持，本文据实际调用链纠正。最终执行的接近路径及其认证逐值相同，不代表异步搬运、释放、脱离和实测回位整条轨迹相同。

完整50Hz仍未过；没有连续工作区、20＋20或默认晋级结论。每工位只有一对原物理，本批的绝对秒数不作为通用性能保证。

## 固定输入与来源

- 源码 `05cc17cee2d81e9e33c73156e37bc1b9d0887ad8`，Kaggle `muqiaoqiao/so101-x-midpoint-20261024/1` 已 COMPLETE。四个原进程全部终态后才修改文档。
- 原 `evaluate_station.evaluate(timing=True)`、ORIGINAL_RUNNER、runtime 与 preflight 保持；云端 Python3.13.15、MuJoCo3.15.0、NumPy2.4.6、EGL/T4，四逻辑CPU。
- 左侧原 `fixed-x-minus20.json`，cube=(.22,−.13,.01)m，红盘固定(.24,−.13)m，放置(.24,.14)m，显式补证true。
- 右侧原 `fixed-x-plus20.json`，cube=(.26,−.13,.01)m，红盘仍固定，仅 place 节点改为已有第二目标(.20,.20,0)m；54mm接近高位、.35rad高位预收口保持。
- 同侧请求、resolved Station、初始qpos/qvel及静态模型相同。实际加载偏好的唯一差异为 `approach_midpoint_order=false→true`，`loaded_jaw_preload=true` 保持。没有使用缺少preload的旧独立midpoint配方。
- 原1mm、候选弦2mm、.005rad分辨率、最终完整认证、全部夹爪扫掠、评分、自由物体、90sim/120wall和所有回退保持；没有目标真值控制。

## 原物理成绩

顺序为左 B→C、右第二工位 C→B。只作同工位比较。

| case / UUID | 原裁决 | sim / episode wall s | process wall / CPU s |
| --- | --- | ---: | ---: |
| left_baseline / c98a9151-e990-445f-97ca-3b1ae7f1bc22 | pass | 74.080 / 106.321 | 107.803 / 118.025 |
| left_midpoint / 44f2d8dc-c04a-4b18-aaf9-2799f7b3dfcc | pass | 74.060 / 91.936 | 93.181 / 103.274 |
| right_midpoint / 1fe7fc35-a117-4027-bb1a-0e0ad1b483fe | pass | 82.300 / 56.170 | 57.415 / 68.771 |
| right_baseline / 884461ae-01c6-4f0d-bb5b-2102274bd347 | pass | 82.140 / 58.682 | 59.962 / 71.430 |

四例实际抓取、放置、静稳、释放、脱离和回位均完成，安全停机／障碍接触均0；free_object=true、weld=0、mocap=0。左 planned/measured 各244/244；右 planned/preclose/measured 各246/246/246，每项 required==checked。两个异步worker均consumed、owned_ack、joined，清理无未知；回位仍为原同步 validated_direct。

左两例抬升均40.960mm、持物29.74s、落盘静稳7.54s，释放后XY最大漂移均.214635mm；右两例抬升约34.987mm、持物37.72/37.62s、静稳7.50s。四例脱离后峰值力均0N。实际视频463/463/515/514帧，与原capture/encode/report一致。

根直接核原文件72项全部一致；独立reader另重放原Monitor和2ms ReleaseAudit，四例均逐字段exact一致，无未评分尾行。原报告及失败判断未改写。

## 实际计算收益

| 同工位 B→C 指标 | 左固定盘 | 右第二放置工位 |
| --- | ---: | ---: |
| 候选弦尝试 | 79→10 | 74→11 |
| 候选弦认证状态 | 8110→2157 | 7145→2366 |
| 最终认证状态 | 535→535 | 490→490 |
| 总认证状态 | 8645→2692 | 7635→2856 |
| shortcut wall s | 16.260996→3.026695 | 4.111321→1.447591 |
| 初始化 wall s | 20.036685→6.597678 | 7.676877→5.108921 |
| OMPL search s | .143276→.147389 | .171177→.168995 |
| hold完整拍 | 162→162 | 259→264 |
| 非hold循环 wall s | 77.731963→77.069079 | 42.522022→42.532413 |

两侧原OMPL路径、最终3点接近路径、最终完整认证及最小认证下界均exact相同。下界左1.002712mm、右1.001882mm，这是完整接近路径的保守分离下界，不是精确欧氏距离或盘壁专属净距。

左初始化减少13.439s，其中shortcut减少13.234s；右初始化减少2.568s，其中shortcut减少2.664s。右候选反而多5拍hold和.16sim秒，仍减少实际进程wall/CPU，故不是少等待形成的假提速。其他循环、编码、启动和调度差额保留，不能全部归给算法。

本批右候选实际11条／2366候选状态，不覆盖为本机先前10条／2167状态。中点试探在任意几何条件下不保证得到同一条最短路径，本批等价由原输出实际证明。

## 完整周期与下一瓶颈

| case | 完整周期 | P50 / P95 / P99 / max ms | >20ms |
| --- | ---: | --- | ---: |
| left_baseline | 3704 | 19.786 / 41.957 / 164.669 / 660.480 | 1714 |
| left_midpoint | 3703 | 19.509 / 40.835 / 161.445 / 673.253 | 1512 |
| right_midpoint | 4115 | 10.866 / 18.557 / 32.173 / 164.089 | 170 |
| right_baseline | 4107 | 10.888 / 18.744 / 31.646 / 162.004 | 175 |

四例均非完整50Hz。初始化改善不解决循环尖峰。左候选close331拍controller累计20.172s、lift143拍5.862s；原版20.414/5.862s，仍是下一项具体取证入口。不能把本轮搜索顺序的收益宣传成伺服实时性通过。

## 前置局部对照与淘汰证据

round117对原保存路径作无积分／无渲染重放。独立fresh checker，左／右各三对AB/BA/AB，最终路径12次与原云端保存路径逐位相同，最终1mm/.005rad认证保持。左wall中位比.205，右.304；仅用于选择本轮原物理候选，不拼算本机MuJoCo3.3.7与云3.15.0提速。

round116批量前缀＋标量补证原型已淘汰。8条尾段派生弦及完整244闭爪共571状态，全部没有原轴证书；候选每点新增batch调用，标量571次没有减少。三对1.752→2.025、1.843→2.398、1.775→2.564s，全慢，完整报告相同。没有接生产或浪费整程物理。571是所选局部样本，不能外推全部场景。

原报告384次补证属于物理外层checker；不包含控制器所有内部弦查询。轨迹推导的6364/5869常规弦状态也不是捕获的ABI输入计数。两种范围保持区分。

## 复跑与原件

```bash
python3 experiments/colab-twin/evaluate_station.py \
  --station experiments/colab-twin/scenarios/workspace-station/fixed-x-minus20.json \
  --candidate experiments/colab-twin/route_strategies/loaded_jaw_midpoint.py \
  --output-dir experiments/colab-twin/output/x-midpoint-replay --timing
```

原版仅改 `--candidate` 为 `loaded_jaw_preload.py`。右第二工位复制plus20文档，仅改place节点(.20,.20,0)，与本批实际requests一致。新进程重新认证，不继承历史成功。

原件：`experiments/colab-twin/output/x-midpoint-20261024/kaggle-v1/`，batch `8e9fa7a7-e0ce-4782-9a9e-4e3fd549e6c1`；含原TGZ、运行日志、四任务、root-readback.json和independent-readback.json，保持Git忽略。私有云复建入口 `round118-x-midpoint/build_kernel.py --source-revision 05cc17cee2d81e9e33c73156e37bc1b9d0887ad8`；局部round116/117保留反证与复跑程序。

保留显式候选，不切默认。原中心候选回归、重复整程分布与完整50Hz仍待验证；下一步先取左close/lift的实际内部调用，保留原全扫和物理阈值。Knowledge=already_covered，沿用Wiki《ROS2 与 FishBot》§20；owner根Codex。
