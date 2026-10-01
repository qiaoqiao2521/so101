# SO101

一个机械臂一个项目：本机最新跟随器、ROS/MoveIt/仿真、Java MES 与场景工具。

```bash
./so101.sh check
./so101.sh help
python3 -m unittest discover -s mint_follower_demo/tests
```

- mint_follower_demo/：跟随器Web应用、鉴权整改与动作导出。
- workspaces/so101_ws/：ROS工作区与Java MES（原根目录so101_ws已迁至此）。
- so101_gz_scene/：场景、映射与回放。
- tools/：离线布局检查。

阅读 mint_follower_demo/SECURITY.md，从环境配置管理员/操作员口令后，
可用 ./so101.sh follower 启动应用。该入口不调用旧start.sh的抢占端口/权限修改流程。
标定、串口配置和用户日志应在部署机器本地配置，不能套用他人的标定驱动机械臂。

本轮同步本机安全整改与回归测试；Humble依赖尚未整体迁至Jazzy，
离线测试不代表仿真或实机验收。旧so101_ws、so101-ros2-arm远端仍归档保留历史。

## Colab 数字孪生实验

运动自主规划以 MuJoCo 为核心，复用已有 SO101 模型与 OMPL 规划经验。位置 IK、OMPL 自动绕障、MuJoCo 物理执行已接入，本地与Colab CPU 20/20轮通过，可见场景与视频回收已复验通过；保留原合成轨迹基线。平台入口回收视频、轨迹与指标：

```bash
python3 experiments/colab-twin/run_colab.py --session so101-planning --episodes 20 --seed 0
```

详见 [自主规划路线与既有资产](docs/MUJOCO_MOTION_PLANNING.md)、[选择依据](docs/DECISIONS.md)、[实验说明](experiments/colab-twin/README.md) 和 [当前计划](plans/colab-digital-twin-20261001/task_plan.md)。毕业设计、答辩与中期报告副本放在本机 `local-documents/`，个人文档、原始咨询和实验输出均被 `.gitignore` 排除。

继续主线的本地逐层单回合入口（使用已安装实验固定依赖的 Python）：

```bash
python experiments/colab-twin/run_staged.py --render
```

依次核验依赖与 native imports → MuJoCo reset/10步 → 单次 IK/OMPL 绕障 → 一个位置伺服回合；失败即停止，后续阶段标记 `not_run`。2026-10-01 本机四层通过，末端误差 0.549 mm、20ms碰撞无无效采样、限位超出0，15.092秒/378帧视频完整解码通过；无云端分配或真机操作。静态路径的位置伺服反馈尚不包含动态重规划、抓放或视觉。


单臂夹取工位已建模：开放料盘、可移动物体、相机支架及三视图；物体真实支撑和夹爪开合已检查，尚未夹取/抬起。入口：`python experiments/colab-twin/preview_grasp_workcell.py`。详见[实验说明](experiments/colab-twin/README.md)。

## GR00T / LIBERO 策略实验

用户选定的扩展实验复用官方 GR00T N1.7 / LIBERO。CPU reset/物理步/双相机与 HF gated 配置访问已验证。最后一次尝试（第六次）已按用户指令完成并停止。L4 上官方 GR00T frozen 安装通过，LIBERO 依赖实际进入 Python 3.12 client venv，环境错位问题已在云端修复；随后导入 Matplotlib 因继承的 `module://matplotlib_inline.backend_inline` 后端不可用而失败。失败归档已回收并通过清单/哈希核验，模型加载与策略回合未启动。远端 worker 已结束，执行连接仍未返回；根 Agent 对唯一控制进程发送 SIGTERM，新的有界清理路径实际保存报告并成功 unassign，最终 active_assignments=0。子进程现固定 `MPLBACKEND=agg`，本地无头 PNG 绘制通过；该后端修正尚未云端复验。此轮不再分配 GPU，后续云端尝试需用户新的明确指令。 LIBERO 使用 Panda，尚未证明 SO101 策略迁移或任务成功。入口见 [实验说明](experiments/gr00t-libero/README.md) 和 [接续计划](plans/gr00t-libero-20261001/task_plan.md)，下载、模型、凭据及报告全部排除在 Git 之外。