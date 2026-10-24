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

局部检查只证明接线、复原、错误隔离与拒绝合同；实际渲染和原始PNG复算待固定源码后在原Kaggle环境执行。本机后台Blender不被抢占，不新建调度平台。

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
