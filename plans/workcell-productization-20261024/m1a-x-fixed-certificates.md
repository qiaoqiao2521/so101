# M1a：固定红盘的 X 向补证

## 本轮结论

保持原红盘位置、几何、关节限位和 1mm 门槛。左侧 X−20mm 的原拒绝来自候选分离方向不足，下降／闭爪／抬升已完成补充数值认证。右侧 X+20mm 仍不能整链认证，不送物理运动、不扩大网页准入。

这不是新的抓放成功。此前移动红盘的四次物理成功仍属于新布局，不能代替本轮固定盘位。

## 实现范围

- `NativeSupport.certify_directions` 是独立可选 API。只对一个 mesh-box 对尝试调用方方向，沿用原 `certificate(full=true)`、区间投影、平方比较和算术环境检查。
- 原19轴查询实现与默认编译选项未改。额外查询使用独立本次 frame，不写回证书或方向历史。
- `mesh_box_axes.py` 从编译网格凸包面法线、凸包边与盒轴叉积生成搜索方向。凸包只用于找方向，实际认证仍投影全部原编译顶点；每个姿态重新计算。
- `probe_workcell_workspace.py` 增加显式高位和补方向诊断开关。原 `offline_screen_pass` 与原拒绝保持；额外结果放在 `extra_axis_screen`，始终标记 `not_physical/not_admitted`。
- 原配置路径检查遇失败即停。新增 `complete` 标明实际覆盖；`observed_samples=1/required_states=244` 不能冒称完整扫掠。下面右侧全64点另由独立局部脚本覆盖。
- 原生未认证结果的未计算平方字段可能为 NaN，诊断输出写作 null；`certified=false` 保持。没有将非有限值改成零或放行。

## 左侧：固定 X−20mm

世界目标 XY=.22/−.13m，原高位60mm，原下降高度19mm。原红盘中心仍为 .24/−.13m。

| 检查 | 实际采样 | 原19轴拒绝数 | 补方向后 |
| --- | ---: | ---: | --- |
| 原参考起姿 | 2 | 0 | 全部认证 |
| 下降 | 74 | 1 | 全部认证 |
| 闭爪 | 244 | 244 | 全部认证 |
| 抬升 | 74 | 1 | 全部认证 |

246 条新增几何对认证均使用完整支持投影，平方门成立；本轮选中见证下界最小12.083509mm。它是分离下界，不是最短欧氏净距，也不等于动态跟踪余量。原 `offline_screen_pass=false` 保留。

原件：`experiments/colab-twin/output/workspace-x-20261024/fixed-left-extra-axes.json`。

## 右侧：固定 X+20mm

60mm高位仍是原腕俯仰95°限位问题，参见 [原诊断](m1a-x-results.md)。本轮沿用已有54mm可解IK姿态，未改IK阈值、限位或红盘。

独立脚本从原保存关节姿态重建72点下降与244点闭爪，重现14＋50个拒绝。对这64个点逐一搜索网格凸包面／边叉盒轴，最后把候选方向交回原生区间门认证：

| 原拒绝组 | 本轮逐点覆盖 | 新方向认证 | 仍未认证 |
| --- | ---: | ---: | ---: |
| 下降 index58–71 | 14 | 0 | 14 |
| 闭爪 index0–49 | 50 | 18（index32–49） | 32 |
| 合计 | 64 | 18 | 46 |

浮点搜索的下降最佳投影间隙为−2.459943～+0.922209mm；它们不足以提供1mm证书。闭爪18个候选见证为1.025453～2.880327mm，全部经原生数值门复核。没有把“找不到证书”写成物理碰撞，也没有据负投影间隙调用物理运动。

原件及复跑脚本位于本机私有目录：

`/home/muqiao/.cache/ros2-factory/codebuddy-so101-20261021/round109-x-certificate/`

- `right_screen.py` / `right-screen.json`：64点完整浮点候选搜索，单进程单BLAS线程，26.590s，`mj_step_calls=0`。
- `native_readback.py` / `right-native-readback.json`：同64点、同几何对、同1mm门槛，18认证／46未认证。

## 验证与接续

原 native、可选方向API、原保守检查和空间探针的46项相关测试通过。现用packed／inline／seed-bound组合下新增7项测试也通过。负例覆盖真实右侧被拒姿态、相交／不足1mm、空／非法方向、错误算术环境、strict JSON，以及首失败前缀的覆盖声明。内部GPT独立回读左右原件，确认无缺失、重复或换对；CodeBuddy本次返回空结果，不计有效参与。

尚未接入生产检查器或物理执行。左侧仍需将补证作为显式候选接入全部规划／实测检查，再用原物理评分验证。右侧先核大张口活动指的路线：只检查在高位收至已有0.35rad开度后，下降、完整244点闭爪与双pad开口是否同时满足要求；不扫参数、不直接改控制器。

Carry接续改动另留在途，未混合交付。M1a整体、连续区域、20＋20、完整50Hz均未新增通过。

复跑左侧诊断：

```bash
cd experiments/colab-twin
python probe_workcell_workspace.py \
  --source ../../workspaces/so101_ws/src/so101_mujoco/models/so101.xml \
  --point fixed_x_minus20 .22 -.13 --extra-mesh-box-axes \
  --output output/workspace-x-20261024/fixed-left-extra-axes-new.json
```

右侧前缀诊断另加 `--pickup-hover-z-m .054`，目标改为 `.26 -.13`。首失败处停止，完整64拒绝点复核使用上述私有脚本；两者覆盖范围不同。
