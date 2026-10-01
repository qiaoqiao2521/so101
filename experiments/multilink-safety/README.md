# SO101 多连杆安全过滤实验

在本地 MuJoCo 动作接口前增加 CPU 安全过滤器：实际关节状态 → 五个连杆包络/Jacobian → 分离平面 CBF-QP → 六维绝对关节目标。只操作仿真，不导入跟随器 Runtime，不连接串口，不下载 VLA 权重。

这是 [Multi-Link Safety Filtering](https://arxiv.org/html/2609.40007v1) 的**本地关节空间适配**。截至 2026-10-01，作者项目页仍为 `Code (coming soon)`，不能称为官方源码部署。公式、参考实现及差异见 [SOURCES.md](SOURCES.md)。

## 部署与运行

在此工作树根目录运行，需已安装 `uv`：

```bash
./so101.sh safety --check     # 独立依赖、单元/集成检查、真实 RGB-D 渲染跟踪检查
./so101.sh safety --render    # 同起点/指令/障碍轨迹，安全层关闭与开启的成对物理实验
./so101.sh safety --tracking-check
```

入口自动创建/复用 `$HOME/.cache/so101-safety/venv` 的 Python 3.12 环境，使用 [固定依赖](requirements.txt)，不会修改原规划或训练环境。可通过 `SO101_SAFETY_VENV` 指定本实验的独立环境。渲染默认使用可用的 OSMesa/EGL，可显式设置 `MUJOCO_GL`。

每轮生成新的 `output/paired-<UUID>/` 或 `output/tracking-<UUID>/`，包含派生 MJCF、JSON 指标和视频/截图。整个 `output/` 已加入 Git 忽略；失败结果也保留，不覆盖上一轮。脚本有 60 秒仿真时长上限；实验未满足验收时返回非零。

## 如何接动作接口

```python
from runtime import SimulationSafetyAdapter
from cbf_filter import Ellipsoid

adapter = SimulationSafetyAdapter(model)  # 每回合 reset；20ms/.3rad/s/12mm硬间距+6mm减速余量
result = adapter.apply(data, nominal_joint_target, oracle_hazard,
                       hazard_velocity=known_translation_velocity)
if result.action is None:
    terminate_episode(result.metrics["reason"])  # 调用方的停止处理，绝不执行原始动作
else:
    data.ctrl[adapter.ctrl_indices] = result.action
```

模块与脚本同目录；外部脚本需将此目录加入模块搜索路径。目标为六维绝对关节角（弧度），顺序在 `runtime.JOINT_NAMES`。障碍中心/半轴为世界坐标米，旋转矩阵右手正交；障碍速度是世界坐标米/秒。过滤器刷新实际 FK，不改 `qpos`、`ctrl` 或仿真时间；物理推进由调用方负责。演示额外使用仿真重力补偿，实机伺服未验证。

`accepted` 表示本次原动作通过当前模型约束；`modified` 表示被修正；`stopped` 的动作始终为 `None`。适配器锁存停止，必须显式 `reset()`，不存在求解失败后退回原动作的分支。旧平面失效时，可重算并验证当前几何的新分离平面；真实重叠仍拒绝执行，重算耗时单独计量。

默认 QP 在 18mm 间距前开始减速，当前几何证书低于 12mm 则停止。额外 6mm 余量用于本仿真伺服的滞后与离散误差，没有经过实机误差界推导；它加强 QP 的避让要求，不降低硬停止门槛。

## 保护范围与验收

- 五椭球覆盖模型碰撞网格：前臂三个、手腕一个、固定/活动夹指一个。夹指连续开合包络限定为 `.015–.5 rad`，实际位置或目标越出此范围会停止。
- 上臂、肩、底座、携带物体及一般自碰撞不在 CBF 保护范围内。模型几何没有实物标定。
- 成对实验使用同一简单关节目标策略和**仿真障碍真值**，没有 VLA。每 2ms 物理步后刷新接触，20ms 控制边界也检查，包括退出前最后一个状态。
- 静态障碍挡路时，未到目标算任务失败。障碍退出实验要求安全层无接触并到达目标。指标将接触、任务到达、安全完成、停止及延迟分别记录，不能把零接触等同于任务成功。
- 延迟记录首次初始化、后续 p50/p95/p99、最大值、重新认证耗时与控制周期超时数。它是本机有限样本测量，不是论文的硬件实时保证。

RGB-D 模块用人工指定 bbox 初始化可见点 PCA 包络，每五步做一次稀疏 LK 平移跟踪；失踪、深度异常、过期或无效时间戳锁存停止。它未实现作者的 VLM/检测器、MVEE、旋转估计或模板搜索恢复，**可见点包络不能覆盖隐藏的完整障碍**。适配器默认拒绝这种包络；`allow_visible_enclosure=True` 只允许显式的仿真研究，不能据此声明整体碰撞保护。跟踪渲染检查与真值碰撞实验分别验收。

这是采样位置伺服上的实验安全层；仿真终止不代表物理刹停，不保证障碍继续逼近时的安全，也不构成功能安全认证。最新实测见 [RESULTS.md](RESULTS.md)，独立任务接续见 [progress.md](../../plans/multilink-safety-20261001/progress.md)。
