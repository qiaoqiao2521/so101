# M1a：X向新请求的IK与盘壁检查

## 范围

固定红盘不动，新增取料X=.229/.251、Y=−.13m两个请求。使用原60mm高位、.5rad开爪、原IK／绕障／1mm／285对／244点／90sim120wall；不套用端点特殊参数，不扩大网页准入。

## 原静态检查

| 请求 | 下降点数 | 完整闭爪点数 | 抬升点数 | 全采样最小认证下界 |
| --- | ---: | ---: | ---: | ---: |
| X−11mm | 74 | 244 | 74 | 1.012254mm |
| X＋11mm | 81 | 244 | 81 | 1.026594mm |

两个请求每个采样均通过全部285对。上表是保守分离下界，不是精确欧氏净距或动态跟踪保证。两条直接接近诊断弦均在第27个采样被原障碍／夹爪检查拒绝，不能省略原OMPL绕障；静态通过不等于任务通过。

现有 `probe_workcell_workspace.py` 新增显式开度和完整扫掠选项。默认.5不变；.35只在高位预收口，随后下降／闭爪／抬升。高位／低位两次非零收口沿原controller的jaw_span/244分辨率，实测各246点。失败前缀保存observed/required/complete和原拒绝，只有真实通过的有限min_distance_m才进入minimum_certificate。

右端X=.260／54mm原.5负例仍拒绝：下降59/72、闭爪1/244；显式.35的预收口246／下降72／闭爪246／抬升72全部原证书通过。无积分或渲染，未使用物体真值作控制输入。

49项probe／开发入口／扫掠相关检查通过。CBC只读调用空正文，不计有效审核；内部GPT独立复核，根验证。原件在 `output/x-request-probe-20261024/`，`full-screen-execution.json`保存实际参数与零积分记录。本机静态环境为Python3.12.3／MuJoCo3.3.7；后文原云物理为Python3.13.15／MuJoCo3.15.0，不混为同版本测量。

```bash
cd /home/muqiao/dev/ros2/_delivery/so101-colab-20261001/experiments/colab-twin
/home/muqiao/.cache/so101-colab/planning-venv/bin/python probe_workcell_workspace.py \
  --source ../../workspaces/so101_ws/src/so101_mujoco/models/so101.xml \
  --point x_minus11 .229 -.13 --point x_plus11 .251 -.13 \
  --full-grasp-sweep --output output/x-interior-new-probe.json
```

复跑右端预收口：改为单点 `.26 -.13`，增加 `--pickup-hover-z-m .054 --pickup-open-jaw-rad .35`。该输出仍为not_physical／not_admitted。

## 几何查询与认证下界的区别

本机对上述最低证书所对应的两个固定姿态，另调用已安装 `mj_geomDistance`：左盘壁／下臂返回156.246559mm，右盘壁／活动指返回7.011770mm；原证书下界分别1.012254／1.026594mm。左查询初始distmax=.1m时为裁剪值，扩大查询范围至1m才取得有效fromto；裁剪记录保留，不称100mm实距。

这是本机3.3.7的两对原生查询，原mjDSBL_NATIVECCD配置未改，不是精确三角面、整轨迹最小距离、云端结果或跟踪余量。查询distmax与原安全margin=.001分列；不把这些诊断数喂给放行逻辑。原件为 `native-geom-distance.json`。

## 原物理：两个新请求完成

固定源码 `66ee5d106b8287ba5213b3049e148b4db3c453c6`，Kaggle `muqiaoqiao/so101-x-interior-requests-20261024/1` 已COMPLETE。沿原串行runner和 `run_workspace_case.py`，使用 `scenarios/workspace-x-interior-m1a.json`。仅原reset fixture设置初始XY，控制仍消费RGB定位；控制器、评分器和物理参数未改。

| 原请求 / UUID | 原裁决 | sim / episode wall s | process wall / CPU s |
| --- | --- | --- | --- |
| left_minus11_original / 768e93c6-2cc5-46c8-92ff-e88dcf3c0510 | pass | 75.82 / 49.143 | 50.227 / 59.554 |
| right_plus11_original / f846c307-869f-4f77-b0cf-639a7badd6ce | pass | 77.90 / 49.266 | 50.363 / 59.982 |

两例真实抬升40.973／41.031mm、持物31.60／34.30s、蓝盘静稳均7.54s。planned/measured闭爪各244点，两例3791／3895条轨迹全部finite/arm_valid，碰撞与安全停机0，自由物体、weld0/mocap0保持。释放68.462／70.542s脱离，XY最大漂移.220805／.177592mm，脱离后峰值力0；回位q6最大误差均.102544mrad，停稳速度<1e−7rad/s。

初次OMPL搜索／含后处理为.121331/.279792s和.127085/.277025s；transport worker为2.377516／2.208082s，separation worker为1.058765／1.052485s。两类worker均consumed、owned_ack、joined，cleanup_unconfirmed=false。录像实际474／487帧，与原report一致。

完整周期3791／3895拍，P95=16.088／15.217ms、max44.763／44.042ms，仍100／63拍>20ms，完整50Hz未通过。这是两个新位置的功能验收，不是算法加速A/B，不能和端点或不同云VM的秒数相减。

两例RGB交接估计为(.22899247,−.13050834)和(.25080426,−.13050834)m；均先在原遮挡预测处冻结目标，仍假设交接后工件静止，没有新增持续视觉跟踪。源及评分引用干净，原90sim／120wall保持。根原件检查在 `output/x-interior-20261024/kaggle-v1/root-readback.json`，独立reader另回放monitor／释放审计并核模型、源、视频与时钟。

独立reader核原monitor/helper重放完全一致，未评分尾行0；释放7370／7360条2ms样本的detached旗标和原裁决一致。左例重算最大漂移有2.71×10⁻²⁰m末位差，原JSON的matches_original_report=false如实保留，不声称逐位相等、不覆盖原数值或放宽物理门槛。目标X不同，静置后目标Z／四元数／速度有极小差；机器人初始q6/qvel6、固定盘和模型配置一致。

```bash
python run_workspace_case.py --profile scenarios/workspace-x-interior-m1a.json \
  --case left_minus11_original --output-dir output/x-interior-replay
```

另一例为 `right_plus11_original`。本轮不是性能A/B或连续工作区认证；两端点、两内点通过也不能替代逐请求验证及扰动面板。
