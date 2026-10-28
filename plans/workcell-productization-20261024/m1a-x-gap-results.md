# M1a：X 区间中点的 IK 与盘壁认证

## 新增可复用能力

固定红盘与 Y=−.13m，新增两个中点请求。左 X=.2245m 用原60mm高位／.5rad开度完成抓放；右 X=.2555m 用显式54mm高位／.35rad预收爪完成抓放。原中心两次回归通过。仅新增[可编辑开发样例](../../experiments/colab-twin/scenarios/workspace-x-gap-midpoints-m1a.json)，没有重写IK、默认选参、网页扩域或新认证引擎。

本轮承接[既有±20mm端点](m1a-x-fixed-certificates.md)和[±11mm内点](m1a-x-interior-results.md)。这些是离散请求，不是连续X域、定位误差包络、20＋20或完整50Hz通过。后台闭爪包络R132仍保留未完证明，本轮按用户要求先处理X向。

## 原静态筛查

Kaggle `muqiaoqiao/so101-x-gap-midpoint-20261028/1`，固定源码 `3602f5b0ad97aaf9004b991527a70c2f008e3729`。原 `probe_workcell_workspace`、8种子IK、原1mm／285对和完整扫掠；无物理步进。根22项检查和独立grid读回通过。

| 点／配置 | reference | 高位预收口 | 下降 | 闭爪 | 抬升 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 中心，60mm／.5 | 2 | — | 76 | 244 | 76 |
| 左中点，60mm／.5 | 2 | — | 74 | 244 | 74 |
| 右中点，60mm／.5 | 2 | — | **77/84拒绝前缀** | 244 | 84 |
| 右中点，60mm／.35 | 2 | 246 | 84 | 246 | 84 |

除标注拒绝外均完整通过。17条扫掠中16完整、1失败前缀，实际1861个采样，7个后续下降采样未访问；没有用成功前缀代替完整路径。完整通过项逐姿态报告全部285对认证。独立reader从固定源码提取原采样纯函数，全部实际q6与原网格前缀逐位一致。

右原开度下降index76的拒绝对为 `pick_wall_x_1 / collision_moving_jaw_so101_v1_0`：`no_separation_certificate`，285对检查、284对认证，该对分离下界.941157812mm。**缺少1mm证书不等于实际接触，也不是精确欧氏盘壁净距。** 右两配置reference、三阶段q5、种子来源与高度完全相同；只改变开度后通过，隔离出夹指扫掠影响。左中点无需补方向，右中点名义坐标无需降高。

成功组最低采样认证下界：中心1.010529mm、左1.075406mm、右预收口1.067331mm。右原下降成功前缀的1.003016mm不能代表整条下降。右名义60mm高位关节余量仅.001181113rad（约.068°），尚无动态／输入不确定性保证。

## 原物理V1：静态通过不能替代实际RGB输入

Kaggle `muqiaoqiao/so101-x-gap-physical-20261028/1`，同源码。复用原 `run_workspace_case`、串行runner、MuJoCo3.15.0和原独立评分。原红盘／物理／控制／碰撞／90sim120wall未改，定位结果真实进入IK。

| case／UUID | 原裁决 | sim／episode-wall s | process-wall／CPU s |
| --- | --- | --- | --- |
| left_mid_original／f73a57cd-91be-4771-903f-0181c19d5e0b | pass | 75.36／50.735 | 52.074／61.753 |
| right_mid_original_open50／190ba11d-bcda-4118-8631-e53591665b39 | fail：IK残差拒绝 | 0／2.668 | 3.567／5.185 |
| right_mid_preclose35／e6ea8462-7211-4046-a6b5-90b9a4687ae5 | fail：同一IK残差 | 0／2.684 | 3.659／5.225 |
| center_default_regression／e008400b-fea8-437e-a23b-1d67efb12bb6 | pass | 76.66／49.284 | 50.388／60.066 |

右两例实际RGB为(.2556298526685876,−.13050833816470292)m，比名义坐标偏(+.129853,−.508338)mm，总.524661mm。原IK拒绝残差均`.0007626829034486256`，不是米制位置误差；0步、无实际撞盘、夹取或释放。两条路径高位均60mm。静态reference种子与物理稳态种子略有不同，V1本身不能把失败单独归因于RGB误差，更不能证明全局无解。

左例真实最大抬升40.968mm、持物31.12s、静稳7.54s，68.002s完成脱离，XY漂移.187192mm、脱离后力0。原中心最大抬升40.998mm，释放与回位通过。两成功例原monitor／skill与2ms释放审计独立重放一致，planned/measured闭爪244点完整、worker清理已确认；实际录像471／480帧。V1独立114项检查无失败。首次reader把未执行候选当作已到释放的错误记录保留，修正reader后按实际轨迹分类，没有改原成绩。

## 原物理V2：只改高位，补上实际视觉坐标诊断

Kaggle同kernel `/2`，仍为同源码。右预收口.35不变，仅把高位60→54mm；同VM先重复原失败，再运行54mm，再中心回归。既有bootstrap／runner／裁判保留，没有用归档视觉坐标替换在线控制输入。

同VM额外对V1归档RGB坐标运行原静态probe：60mm的approach/lift均拒绝，残差与物理相同；54mm三阶段可解，高位关节余量.047829287rad（约2.74°）；54mm／.5仍缺抓取腿证书，54mm／.35完整通过。54mm大开度下降62/69、index61拒绝，仍是原盘X壁／活动夹指对，分离下界.906100121mm；预收口两高位/低位收口各246，下降／上升各69点全部通过，同高度q5逐位一致。诊断实际1009/1016采样，7个首失败后未访问。这说明归档坐标在原静态种子下也能复现拒绝，种子差异不是复现该拒绝的必要条件；不是放宽IK残差获得通过，也不把有限搜索失败叫数学无解。

| case／UUID | 原裁决 | sim／episode-wall s | process-wall／CPU s |
| --- | --- | --- | --- |
| right_mid_preclose35／694810f8-be55-4d85-a781-143726115040 | fail：原IK残差保留 | 0／2.887 | 3.825／5.267 |
| right_mid_low54_preclose35／56777bb6-b11b-4a54-b68f-60c1063ce15c | pass | 78.54／50.873 | 51.966／61.869 |
| center_default_regression／8c04645c-17ac-469c-a97c-245bb75665a2 | pass | 76.70／49.111 | 50.275／60.008 |

右成功例整程最大抬升41.024mm、持物34.28s、静稳7.54s；71.182s完成脱离，XY漂移.185207mm，脱离后峰值力0。碰撞接触／安全停机0，原自由物体／weld0／mocap0与释放回位要求保持。V2独立160项检查无失败、无未决项；原monitor／skill／7360条2ms释放样本重放一致。三项夹爪扫掠各246点，回位误差.102544mrad，录像实际491帧。V1右60、V2右60和右54的RGB、全部初态与固定几何逐值相同，除case ID外请求仅改变高位。

## 完整周期与范围

| 成功例 | 完整拍数 | P95／max ms | >20ms |
| --- | ---: | --- | ---: |
| V1左中点 | 3768 | 16.563／50.481 | 147 |
| V1中心 | 3833 | 15.043／44.653 | 81 |
| V2右54mm预收口 | 3927 | 14.798／45.597 | 77 |
| V2中心 | 3835 | 14.796／44.167 | 70 |

完整50Hz仍未通过。初次OMPL搜索／含后处理分别为左.129187/.295606s、右成功.123691/.304242s；完整进程与仿真耗时见上表。不同坐标、配置和VM的秒数不当算法提速，不与旧轮相加。只保留显式新样例，原默认／网页±10mm不变。

## 复跑与证据

```bash
cd experiments/colab-twin
python run_workspace_case.py \
  --profile scenarios/workspace-x-gap-midpoints-m1a.json \
  --case right_mid_low54_preclose35 --output-dir output/x-gap-replay
```

左中点选 `left_mid_original`；原60mm失败选 `right_mid_preclose35`；大开度原拒绝和中心也保留在同profile。使用已有EGL／native依赖环境，仅软件仿真。不同布局、目标姿态、定位器、光照或障碍仍须本次原评测，不能继承本轮成绩。

原件：`experiments/colab-twin/output/x-gap-midpoint-20261028/` 下 `kaggle-v1/` 静态及 `physical-kaggle-v{1,2}/` 原物理TGZ、独立readback；根 `root-physical-summary.json`。私有构建和独立reader：`~/.cache/ros2-factory/codebuddy-so101-20261021/round133-x-gap/`；上传源码分别读回相符。静态cloud-run.scope残留旧cProfile描述，已单列过时字段，实际probe／payload／输出才作为本轮证据。

静态25重复展开文件逐字节核对后清理，释放176,128已分配字节；原物理直接读TGZ，未展开或生成临时视频帧。保留原归档、失败、读回、当前可看录像及可编辑样例；恢复用 `python3 -m tarfile -e so101-evidence.tgz unpacked`。Knowledge=already_covered：沿用Wiki《ROS2 与 FishBot》§20的输入／实际动作／物理裁决分层，不新增知识页。

Next：将两个已验请求接原Station网页入口并单独验收；后续候选须使用实际视觉输入检查IK与完整净距，不按名义坐标自动扩大连续域。M1b后台覆盖证明、第二放置工位的新中点复测和冻结20＋20仍为独立未验项。
