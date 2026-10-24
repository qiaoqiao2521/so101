# M1a：固定红盘X请求接原Station

## 用户新增能力

原Station现在能显式消费固定红盘X向请求的预收爪和补充分离方向参数。红盘仍在(.24,−.13)m，cube独立声明位置；复用原workspace-development-v1，没有新模式、坐标自动选参或历史证书授权层。省略execution时仍走原默认。

四份可编辑样例为`experiments/colab-twin/scenarios/workspace-station/fixed-x-{minus11,plus11,minus20,plus20}.json`。±11mm沿用60mm/.5rad；左−20mm显式补证true；右＋20mm用54mm/.35rad。原默认／网页普通±10mm不扩大；开发请求的视觉矩形先验不等于连续可抓范围。

根35项Station／evaluate／recipe检查通过；四份真实JSON的盘与cube位置另验。CBC只读实调空正文，不计有效审查；内部GPT实施，根核源码和实际原件。定位器、控制器、IK/OMPL、原1mm、全部碰撞对、夹爪分辨率、原评分和90sim/120wall未改。仅Station透传已有能力。

## 新入口原物理

固定源码`2d7097ef7c911cfa2430ae630069ea65655d455a`。Kaggle实际kernel为`muqiaoqiao/so101-fixed-x-station-20261024/1`，已COMPLETE。创建时title生成实际slug，与最初metadata请求的x-station-fixed不同；只提交一次，未因slug查询失败重跑。

同VM串行五个独立进程，直接调用原evaluate_station.evaluate(timing=True)，bootstrap与ORIGINAL_RUNNER保持。云端Python3.13.15／MuJoCo3.15.0／NumPy2.4.6／T4。每个任务新UUID，原verdict保持：

| case / UUID | 原裁决 | sim / episode wall s | process wall / CPU s |
| --- | --- | ---: | ---: |
| right_original_open50 / 40fb77f8-1904-4dc8-bcb5-7edc8c6665a3 | fail：grasp_leg_collision | 0 / 3.291 | 4.571 / 6.119 |
| right_preclose35 / aefbda2f-2c95-4775-bfde-5c39ca8da3de | pass | 79.160 / 54.099 | 55.279 / 65.146 |
| left_original_axes / 81c926b8-a75a-4bee-a77a-dc3fd9e6b05c | fail：grasp_leg_collision | 0 / 3.108 | 4.045 / 5.679 |
| left_refined_axes / 9645f2fa-3958-46a5-8727-958ebec8d448 | pass | 74.020 / 98.140 | 99.281 / 108.873 |
| center_default_regression / c96c3515-c7a6-40d7-8649-eb1f9fade77b | pass | 77.400 / 51.399 | 52.620 / 62.374 |

两个负例仅显式关闭相应适配，不移动盘：右开度.5、左补证false。它们在初始化原抓取腿认证处拒绝，没有执行抓放；原错误名不是实际碰撞证明。中心取料不变、无execution，放置目标为原(.22,.17)m。不能把本组写成5次抓放全部成功。

## 完整物理与独立读回

- 五例的实际XML红盘均(.24,−.13,.001)m；同侧对照的初始qpos/qvel、静态模型完全相同。源码及评分引用均为固定提交，dirty_paths为空；保存原文与实际输入，只有声明的两项负例覆盖。
- 右侧planned/preclose/measured三次扫掠各246/246；左与中心planned/measured各244/244，required等于checked且原valid为true。右侧实际preclose后进入descend，下降命令保持.35rad，没有跳过到位等待。
- 左侧实测checker的384次补证全部认证，382次方向提示全部命中、另2次完整方向搜索；每次仍重新完整投影，原1mm保持。缺失其他case的计数记unknown，不当零。
- 三个成功任务真实抬升40.989／40.960／40.998mm，持物34.94／29.72／33.44s，蓝盘静稳7.54／7.54／7.38s。障碍接触与安全停机均0，自由物体、weld0/mocap0保持。
- 释放后71.802／66.662／70.200s完成脱离，最大XY漂移.192289／.214669／.199997mm，脱离后峰值力均0N；实际回位误差约.103/.103/.101mrad。transport/separation均consumed、owned_ack、joined且无未知清理；return为原同步validated_direct，没有独立return job。
- 原Monitor与2ms ReleaseAudit由独立reader重放，三个成功任务均逐字段exact一致，所有detached标志一致。视频实际495／463／484帧，与原capture/encode/report一致。根另直接读取原裁决、输入、模型、扫掠、轨迹、安全、视频与完整计时。

## 成本与未过项

| 成功请求 | 完整周期数 | P50 / P95 / P99 / max ms | >20ms |
| --- | ---: | --- | ---: |
| 右＋20mm | 3958 | 10.299 / 16.906 / 30.245 / 50.352 | 117 |
| 左−20mm | 3701 | 18.127 / 37.600 / 153.139 / 617.523 | 903 |
| 原中心 | 3870 | 10.131 / 16.401 / 29.959 / 77.634 | 114 |

完整50Hz三例均未过。左例初始化18.416s，其中接近路径shortcut14.996s；完整循环76.505s，controller累计59.928s，其中close19.102s、lift5.681s、transport18.722s。close首拍index1007/t20.16s完整617.523ms，controller608.364ms。原OMPL搜索仅.134171s，不能将本批主要成本泛称OMPL随机搜索或Python调度。

现有计时只能定位至上述层次，不能据此猜定controller内部哪项查询是唯一根因。本组是功能与失败路径验证，不是性能A/B；不同输入和旧VM的秒数不相减，不晋级默认、不改安全门。下一步只对已定位的shortcut／close重计算取证，再决定最小改动。

## 复跑与范围

```bash
python experiments/colab-twin/evaluate_station.py \
  --station experiments/colab-twin/scenarios/workspace-station/fixed-x-plus20.json \
  --output-dir experiments/colab-twin/output/fixed-x-station --timing
```

左侧改用fixed-x-minus20.json；负例复制该文档后仅将开度改.5或补证改false。原90sim/120wall保持，不操作实体机械臂。新±11mm的原Station完整物理本组未跑，已有开发CLI原物理结果不冒充此入口验收。新增障碍、位置、朝向、高度或盘布局仍须本次重验。

原件在`experiments/colab-twin/output/x-station-fixed-20261024/kaggle-v1/`，batch=`fcad7d10-5b77-4efa-98b9-59708c319dae`。root-readback.json与independent-readback.json分别保存根／独立取证；原TGZ和运行产物保持Git忽略。私有复建入口为round115-x-station-fixed/build_kernel.py --source-revision 2d7097ef7c911cfa2430ae630069ea65655d455a。

本轮是原Station CLI新入口验收，尚未做新固定盘样例的实际浏览器导入→HTTP任务；不冒充网页整链、连续工作区、20＋20或完整50Hz。Knowledge=already_covered，沿用Wiki《ROS2 与 FishBot》§20；owner根Codex。
