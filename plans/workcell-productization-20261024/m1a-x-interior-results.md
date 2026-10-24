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

49项probe／开发入口／扫掠相关检查通过。CBC只读调用空正文，不计有效审核；内部GPT独立复核，根验证。原件在 `output/x-request-probe-20261024/`，`full-screen-execution.json`保存实际参数与零积分记录。

```bash
cd /home/muqiao/dev/ros2/_delivery/so101-colab-20261001/experiments/colab-twin
/home/muqiao/.cache/so101-colab/planning-venv/bin/python probe_workcell_workspace.py \
  --source ../../workspaces/so101_ws/src/so101_mujoco/models/so101.xml \
  --point x_minus11 .229 -.13 --point x_plus11 .251 -.13 \
  --full-grasp-sweep --output output/x-interior-new-probe.json
```

复跑右端预收口：改为单点 `.26 -.13`，增加 `--pickup-hover-z-m .054 --pickup-open-jaw-rad .35`。该输出仍为not_physical／not_admitted。

## 原物理待验

沿原Kaggle串行runner和 `run_workspace_case.py`，使用 `scenarios/workspace-x-interior-m1a.json`。仅原reset fixture设置初始XY，控制仍消费RGB定位；不改控制器、评分器或物理参数。两例独立UUID，不将静态证书当作已完成抓放。

```bash
python run_workspace_case.py --profile scenarios/workspace-x-interior-m1a.json \
  --case left_minus11_original --output-dir output/x-interior-replay
```

另一例为 `right_plus11_original`。本轮不是性能A/B或连续工作区认证；两端点、两内点通过也不能替代逐请求验证及扰动面板。
