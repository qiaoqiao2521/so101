# M1b：实测回位计算迁移

日期：2026-10-24。状态：原物理对照4/4通过（原版2例、候选2例）；切换尖峰下降，整程收益不一致，默认保持原版。完整50Hz未通过。

## 原因和实现

旧X面板最大140.476ms位于separate→retreat。新原观察ca00cc74…抓放通过，保留原冻结模型与实测输入。同MuJoCo3.15无积分复算5次，原_return_path均为validated_direct，75状态、75次arm检查与75次释放物距离查询；路径逐位相同。中位131.131ms，未走OMPL。插桩原回合的快照复制另耗120ms，cProfile缺父帧；这些开销不当作原控制性能。

候选来源：根GPT。agent-link Qoder审查超时，内置GPT完成独立审查；CBC返回空正文，未冒充有效审查。新增[return_worker.py](../../experiments/colab-twin/return_worker.py)，复用原AsyncTransportPlanningJob和SeparationSnapshot，不新增调度器。实测q发起原_return_path，独占模型复用前要求分离worker已consumed/joined。等待期间原物理和分离保护继续，原阶段超时不重置。

接纳时保留冻结释放估计／原上下文绑定，重新认证实测q到快照起点的桥接、首reference、连续首command、偏置与限位、90s预算。原每拍守卫、244闭爪全扫、释放／自由物体判据、90sim/120wall与原IK/OMPL回退保留。审查发现issued未回执，已在原data.ctrl赋值后修复，不在controller内提前报已发出。

默认源仍loaded_jaw_preload.py；[async_measured_return.py](../../experiments/colab-twin/route_strategies/async_measured_return.py)仅显式选择。没有改IK、物理评分器、盘壁1mm或X开发布局。

## 同输入与边界核验

- 根运行101项相关CPU检查通过，其中15项新测试覆盖快照／路径、取消、单次消费、未就绪、桥接内部碰撞、上下文／观测变化、90s边界、首命令和第三worker清理。分析fixture不计物理成功。
- 同MuJoCo3.15、同原MJB，三对反序检查path binary64、method、report和每个arm／distance输入结果均一致。每支75状态，原.005rad分辨率；mj_step尝试0。离线runner的unscored保留，不伪造物理pass。
- 固定源和原评分引用均为b317d4f1d459b99cce6e4df34c042141772e6810，dirty_paths=[]。整对运行终态前未修改源码或提交。

## 原物理与完整周期

Kaggle私有so101-async-return-ab-20261024 v1，同一VM串行、每例独立进程。顺序右B→C、左C→B。B=默认原版，C=候选；不是20+20。

| 例 | 原裁判 | sim / episode wall s | process wall / CPU s | 完整周期 P50/P95/P99 ms | max ms / >20ms数 | 首retreat完整周期 ms |
| --- | --- | --- | --- | --- | --- | --- |
| 右B | pass | 78.02 / 49.737 | 50.884 / 60.277 | 9.544 / 16.781 / 27.864 | 57.415 / 92 | 36.634 |
| 右C | pass | 78.04 / 48.633 | 49.745 / 59.233 | 9.418 / 15.251 / 29.595 | 46.820 / 78 | 30.314 |
| 左C | pass | 78.46 / 50.032 | 51.119 / 61.228 | 9.613 / 16.823 / 28.338 | 50.771 / 97 | 33.347 |
| 左B | pass | 78.18 / 49.783 | 50.878 / 60.677 | 9.606 / 16.545 / 28.219 | 143.018 / 90 | 143.018 |

精确episode wall以原report为准，不由process差值推算。CPU进程值含子进程总用量；周期thread CPU只覆盖主调用线程。周期统计包含原全部exclusive parts和首拍，无删除冷启动或阶段切换。

| 例 | UUID |
| --- | --- |
| 右B | 0ab7faa8-50b2-4636-9c6e-8f61410c7f10 |
| 右C | cae1b40c-276a-4c6d-b083-2580572e60cd |
| 左C | 4bb7ccc6-8011-4535-8ec4-dac075459da0 |
| 左B | eef7537b-8cc8-4816-a5f6-31dfeb380d32 |

四例原抓放、放稳、释放、脱离、回位均通过；自由物体true、weld/mocap0，安全停机和障碍接触0，回位误差约0.000102rad。planned/measured均244/244 valid。全部15635条已记录轨迹arm_valid／finite_state为true。四视频实读488/488/491/489帧，符合原记录；不把录像本身当物理成功。

两候选return job均consumed/joined/owned_ack，无launch_unknown或cleanup_unconfirmed；admission accepted/issued、桥接和首命令守卫均true。首actuator command与首retreat轨迹command一致。候选worker wall右.102s／左.339s，包含线程调度，不能拿它与另VM的131ms局部复算相减。

原运输route_search wall右B/C为2.271/2.296s，左C/B为2.536/2.604s。这些发生在候选介入前，不归因异步回位。新增回位等待右.12sim／6拍，左.26sim／13拍；hold与release另有调度拍数差。不能把全进程右省1.140s、左多.242s统一记为算法收益。

## 决定与下一入口

保留显式候选用于M1b交接研究，不切默认。左切换143.018→33.347ms，右36.634→30.314ms；候选接纳的controller段仍22.779/25.369ms，完整首拍仍超20ms。完整周期和整程收益未共同达标，不能勾选50Hz。

Next：根Codex对候选接纳段做有界分段计时，区分worker轮询／绑定、实测桥接、首指令和原在线保护。先取得真实调用证据，再选最小改动；不删检查，也不以另一次完整抓放成功冒充因果改进。M2恢复、M3冻结20+20、M4同世界卸货均未新增验收。

## 复跑与原件

从experiments/colab-twin运行，原默认将candidate改回loaded_jaw_preload.py；另一工位将station改为x-minus20.json：

```bash
python evaluate_station.py --station scenarios/workspace-station/x-plus20.json \
  --candidate route_strategies/async_measured_return.py \
  --output-dir output/m1b-return-recheck --timing
```

原件：`experiments/colab-twin/output/m1b-async-return-20261024/kaggle-v1/so101-evidence.tgz`。解包根含cloud-run.json、runtime.json、freeze.log、return-ab/*/prepared.json及pair-process-results.json；逐UUID保留evaluation/status、原report/planning/trajectory/jaw-sweeps/release-2ms、完整timing与视频。独立读回independent-readback.json和根复算root-cycle-comparison.json在解包根。全部被Git忽略。

复用的私有wrapper：`/home/muqiao/.cache/ros2-factory/codebuddy-so101-20261021/round104-async-return/build_kernel.py`，沿用round100原生串行runner；根读回与独立reader一致，后者3个缺证／失败反例通过。原轨迹未保存逐周期全部sweep样本，因此只核已记录guard、closure/admission证据和原判决，不声称重演所有内部几何调用。
