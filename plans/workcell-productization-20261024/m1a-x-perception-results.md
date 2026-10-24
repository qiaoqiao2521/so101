# M1a：新X位置的RGB拒绝

## 范围与原实现

复用 `run_visual_grasp.py::run_p0` 和 `visual_localization.py::localize_green_target`。原字符串负例继续在红盘中心执行；新增字典只声明负例ID、类型和目标XY，不改变定位算法、相机、颜色／形状阈值或原1mm定位误差门槛。

目标仍由原reset_scene放置。遮挡片和干扰物以同一XY差值平移；半遮挡再沿原X方向偏移10mm。每例及异常退出恢复三个相关geom的pos/size/rgba。仅拒绝当前坏声明并记该行失败，不影响其他有效例；拒绝不得携带xy_m、pixel_xy或uncertainty_m。

原始RGB保存于 `rgb/<id>.png`，原overlay保留。报告记录实际data.geom_xpos、模型位置、尺寸和透明度，供独立核对场景；不能只拿预期坐标或叠字图复算视觉。

## 固定面板

配置：`experiments/colab-twin/scenarios/workspace-x-perception-m1a.json`。

| 类别 | 场景 | 数量 |
| --- | --- | ---: |
| 无遮挡正例 | 原center／X±20mm，加新X±11mm | 5 |
| 原中心负例 | 缺失／半遮挡／全遮挡／两个绿色候选 | 4 |
| 新位置负例 | 左右X±11mm各四种原负例 | 8 |

共17例。原P0默认三正＋四负协议不增项、不换ID。新面板仅通过配置显式增加案例，不放大网页准入，不替代抓放、持续视觉跟踪、旋转／高度先验拒绝或20＋20验收。

原reset_scene每例含500次积分静置，17例预期8500次；本切片不能称“零物理步”。物体真值只供原正例误差评分，定位器仍只收到RGB、静态标定和时间。无机械臂任务控制或实体设备操作。

## 代码来源与验证

Qoder经agent-link一次120s只读审查超时，没有有效结论；内部GPT实施，根独立审查。根58项P0接线／原定位器／runner相关检查通过，覆盖正反序复原、坏声明继续、无姿态拒绝、重复ID保留旧图、中文ID和目录失败不创建renderer。仅run_p0发生语义改动；物理入口、reset_scene、render_rgb与原bf50087函数结构一致，定位文件未改。

局部检查只证明接线、复原、错误隔离与拒绝合同；以下为固定源码后的真实渲染结果。本机共享仿真不被抢占，不新建调度平台。

## 原渲染结果与独立读回

固定源码 `890616aebd68d018c1e94ab9ee6d2d241ca240eb`，Kaggle `muqiaoqiao/so101-x-perception-20261024/1` 已 COMPLETE。原 P0 的 planned/attempted 均为17，complete/pass均为true；这是渲染定位面板，不是新增抓放回合。

| 原正例 | XY误差 mm | 原1mm门槛 |
| --- | ---: | --- |
| center | 0.616511 | pass |
| X−20mm | 0.512192 | pass |
| X＋20mm | 0.616511 | pass |
| X−11mm | 0.508394 | pass |
| X＋11mm | 0.544720 | pass |

中心及X±11mm共12个负例全部拒绝，且xy_m、pixel_xy、uncertainty_m均为null。缺失／全遮挡返回target_missing，半遮挡返回size_or_occlusion，双候选返回ambiguous_components。17份原始PNG及17份overlay完整，案例ID不重复，没有fixture_error。

原reset_scene实际执行8500次mj_step；P0墙钟4.726051s，原进程wall/CPU为5.544141/7.334838s。云端环境为Python3.13.15、MuJoCo3.15.0、NumPy2.4.6、T4。本机独立PNG读回环境与云运行分列，不将两者的耗时或库版本混为同环境结果。

根直接回读原report、进程记录和源码来源，并查看正例、半遮挡和双目标原始PNG。独立reader用固定版本定位器重算全部17份PNG，完整estimate字典17/17与原输出逐字段相同；同时核遮挡片／干扰物的平移、尺寸和透明度。定位器全文及reset_scene、render_rgb、物理入口函数与前版结构保持，未改IK、碰撞或原裁判。

原件：`experiments/colab-twin/output/x-perception-20261024/kaggle-v1/`，batch UUID为`aee44fb4-9b31-4891-a76d-d41b93977612`。根与独立读回分别为`root-readback.json`、`independent-readback.json`；完整原件在`unpacked/so101-evidence/`。产物保持Git忽略。

已知高度、轴齐方块、绿色和固定相机仍是先验；未保存每例运行时四元数／旋转矩阵，不声称已拒绝任意朝向或高度异常。离散17例也不证明连续区域、所有遮挡、实体标定、持续视觉跟踪或物理抓放。X向IK与盘壁结论仍取[原物理报告](m1a-x-interior-results.md)及[固定盘端点报告](m1a-x-fixed-certificates.md)。

复跑面板的原Python入口：

```python
import json
from pathlib import Path
from run_visual_grasp import SOURCE, run_p0
out = Path('output/x-perception-replay')
out.mkdir(parents=True, exist_ok=True)
protocol = json.loads(Path('scenarios/workspace-x-perception-m1a.json').read_text())
report = run_p0(SOURCE, out, protocol, deadline=None)
(out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
```

它沿用原渲染／定位入口，需已有EGL与MuJoCo环境。云端复跑沿私有round114构建器，保留原bootstrap与串行process计量；输出明确为rendered_perception_only，不伪装成物理抓放裁决。
