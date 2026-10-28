# X方向固定RGB偏差：原物理3/3通过

日期：2026-10-28。R137，执行源码固定 `6cf337b6c66deb7e9c5583045f514b2f5f046b26`。承接[R136实际输入18点几何检查](m1a-x-input-sensitivity-results.md)。只增加可复跑的私有感知偏差验证，没有改生产控制器、IK、评分器、阈值或默认策略。

## 做了什么

保持原左X=.2245m、右X=.2555m工件和红蓝盘不动。按R136预声明规则选择已通过的非中心最小证书点：左每次有效RGB估计加 `(-1.2074000683763885,+1.2074000683763885)mm`，右加 `(+1.7062238887944753,0)mm`；再运行左零偏差对照。左仍60mm/.5rad，右54mm/.35rad高位预收口。

私有launcher在同进程包装原 `run_visual_grasp.localize_green_target`，只改变valid结果的xy；每次从该次raw加常量，不累积。invalid保持原对象，原异常传播，结束后恢复函数。原pixel、reason、uncertainty、诊断字段不改；原冻结后不额外刷新。控制未读取物体真值，原reset与裁判继续按原边界工作。

偏差后的XY不再与原pixel投影一一对应；初始overlay仍指raw定位。原uncertainty是raw条件工程量，不是偏差后相对truth的误差界。它是固定感知偏差实验，不是移动目标、随机扰动恢复率或整个1.7mm圆域证明。

## 三个完整原物理回合

Kaggle `muqiaoqiao/so101-x-input-bias-20261028/1` 已COMPLETE，接收源码回读相同，三例各独立进程串行调用原evaluate_station，原90sim／120episode-wall保持。每例新UUID、原独立裁决均pass，exit0。

| 指标 | 左固定偏差 | 右固定偏差 | 左零偏差回归 |
| --- | ---: | ---: | ---: |
| UUID | `1035c5d7-bf48-42f9-9d35-bd838dc5116e` | `738b92ff-9543-4d64-a744-e33edefb9fbf` | `10752898-372d-477e-b8a1-1a49273f01a5` |
| 仿真 s | 75.12 | 78.80 | 75.32 |
| episode wall s | 49.618928 | 48.837805 | 48.699026 |
| 完整进程 wall／CPU s | 50.766535／60.096452 | 49.977363／59.611283 | 49.819721／59.160419 |
| 真实抬升 mm | 40.974848 | 41.014992 | 40.968359 |
| 持物／静稳 s | 30.86／7.54 | 34.54／7.54 | 31.06／7.54 |
| 脱离后漂移 mm | 0.180492 | 0.197554 | 0.187114 |
| 脱离后峰值力 N | 0 | 0 | 0 |
| OMPL搜索／含后处理 s | 0.124656／0.294212 | 0.121756／0.263771 | 0.120402／0.265049 |
| 接近shortcut wall s | 4.222783 | 3.761448 | 4.084867 |
| 运输／脱离worker wall s | 2.057807／1.024540 | 2.336942／1.040733 | 2.061258／1.063322 |
| 实际视频帧 | 470 | 493 | 471 |

原monitor确认真实抓取和落盘；原monitor／skill及逐2ms释放审计精确重放。三例自由物体、weld0／mocap0，障碍接触与安全停机均0，所有采样guard坏行0。实际回位q6最大误差约.102544mrad，速度小于9.49e-8rad/s。运输与脱离两个实际worker均consumed／owned_ack／joined，cleanup_unconfirmed与launch_unknown均false。默认异步return=false，不虚构第三个worker。

左planned／measured各244点；右pickup_preclose、planned、measured各246点；原1mm／285对／全扫分辨率保持。三例原视频均完整解码，根查看左右final图，物体已在蓝盘，夹爪已脱离回位。原非致命sitecustomize缺wrapt警告保留，不为清日志重跑。

## 输入和完整周期回读

共41次原定位调用：14／13／14，全部valid。每条biased严格等于本条raw加一次原offset，其余字段逐值相等。两个偏差首点与R136静态点差均精确为0；零偏差则与原left_center比较，未把静态点强行送回控制器。无invalid调用，因此本批不新增遮挡拒绝实测；invalid保持原样只由mock与既有负例约束。

| 完整周期 | 左偏差 | 右偏差 | 零偏差 |
| --- | ---: | ---: | ---: |
| 受测拍数 | 3756 | 3940 | 3766 |
| 中断拍 | 0 | 0 | 0 |
| P95 ms | 16.134 | 14.693 | 16.008 |
| P99 ms | 26.906 | 28.703 | 27.317 |
| max ms | 51.654 | 43.927 | 51.245 |
| >20ms拍数 | 71 | 80 | 79 |

共11462完整拍，与三个原report.steps一致，中断0；完整50Hz三例仍false。P95小于20ms不等于全拍达标。这不是性能A/B，不能将本轮约50秒process-wall与其他云／网页批次相减，也不将等待变化记作算法提速。

包装的replace／to_dict／内存记录发生于原episode内；finally审计JSON在原evaluate完成后写出，不计入episode.wall_s或原timing，但包含在完整process-wall。原视频编码、task结束和120秒计时未改。

## 独立审计与原失败保留

根重跑独立reader最终398项通过，failed=[]、unknown=[]。首轮reader错误要求transport／separation／return三个receipt，产生三项失败；按原策略声明和源码核准，return仅在async_measured_return=true时启动。reader改为必需原transport／separation，并在明确开启时要求return；所有实际receipt的清理条件未弱化。首轮JSON.gz及纠错说明完整保留，没有修改物理源码或原成绩、没有云端重跑。

原件在 `experiments/colab-twin/output/x-input-bias-20261028/kaggle-v1/so101-evidence.tgz`。同目录root-readback.json、root-planning-clocks.json、independent-readback.json.gz、首轮independent-readback-first.json.gz、两final PNG和right-bias-grasp-place.mp4均可定位。私有wrapper／5项mock／构建／接收源码／输入在 `~/.cache/ros2-factory/codebuddy-so101-20261021/round137-x-input-bias/`；独立reader、反例与纠错在相邻round137-x-measurement-bias/。

复跑使用私有已保存physical-input-manifest.json和原Station文档；示例：

```bash
python bias_launcher.py --manifest physical-input-manifest.json --role left \
  --station /path/to/fixed-x-minus15p5.json --output-dir /path/to/new-result
```

在既有匹配依赖环境中将原experiments/colab-twin设为PYTHONPATH；right替换role和右文档，零对照role为left_zero_regression。它仍调用原evaluate并实际跑物理，不能用组件JSON冒充新回合。

## 收尾与接续

两个云任务已终态，串行runner已wait回收三进程；未动Mint／其他机器人／后台任务。完成的三个独立JSON无损gzip并逐字节回读，原分配520,192B→45,056B，实际释放475,136B。原TGZ、可编辑输入、源码、标定与当前回放保留；没有临时帧、上传分片或展开仿真副本。恢复见cleanup.json，通用命令 `gzip -dc independent-readback.json.gz > independent-readback.json`。

当前新增证据是两个固定感知偏差下的原抓放，不修改普通±10mm／默认，不宣称连续域或20＋20通过。下一片：在既有第二放置工位复验同两个偏差及原回归，检查跨放置路径的释放／脱离／回位；保持原裁判和原预算。M1a整体仍in_progress，M1b、恢复与冻结验收继续独立。Knowledge=already_covered，沿用Wiki《ROS2 与 FishBot》§20；新成绩只写原计划。
