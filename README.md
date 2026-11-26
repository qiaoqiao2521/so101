# SO101

一个机械臂一个项目：本机最新跟随器、ROS/MoveIt/仿真、Java MES 与场景工具。

## 唯一仓库入口

SO101 统一在 [qiaoqiao2521/so101](https://github.com/qiaoqiao2521/so101) 开发与交付，默认入口为 `master`。已验证的仿真成果合入这里，实验分支继续保留用途与验收边界。

- `experiments/colab-twin/`：MuJoCo 抓放、IK/OMPL、视觉定位和工位执行器；当前进展见 [项目状态](PROJECT.md) 与 [工位产品化计划](plans/workcell-productization-20261024/task_plan.md)。
- `mint_follower_demo/`：轻量跟随器终端；本地尚未提交的改动需独立核验，不因仓库整理自动发布。
- `workspaces/so101_ws/`：已收纳的 ROS/MoveIt、Java MES 与场景资产。
- `apps/resources/`：资料导航与学习站，独立构建发布，源码在本仓库维护。

旧仓库 `so101_ws`、`so101-ros2-arm` 已归档，不再作为开发远端。此次按文件恢复缺失的前端与兼容源码，并将资料站纳入候选；旧仓库删除、私有来源可见性、完整构建和部署验收以 [四仓合并审查](docs/consolidation/2026-10-31.md) 为准，不能仅凭归档状态认定完成。FishBot 工作台仍是独立产品依赖。本地多个 Git 工作树共用本仓库，不是多个项目。历史未采纳的 `codex/multilink-safety-20261001` 已于 2026-11-17 合并保存源码，仍不接入正式入口，不代表官方复现或已批准运行。

## 先体验 SO101 工位

当前默认体验是已经接通的 **SO101 MuJoCo 抓放工位**：选择工位 A/B，调整允许的取放位置，运行一回合，再打开这一回合的报告、视频和三维回放。网页继续复用 FishBot 工作台，SO101 提供原视觉定位、IK/OMPL、抓放执行与物理判定。A0–A3.1 的历史实测范围见[当前工位计划](plans/workcell-productization-20261024/task_plan.md)；启动网页不自动派发抓放任务。

在当前执行机器上，把 `so101` 与 `fishbot-ros2-slam-tools` 放在相邻目录，然后运行：

```bash
./so101.sh workbench doctor
./so101.sh workbench start
```

`doctor` 检查工作台与运行环境并给出缺项；`start` 启动已有网页服务，打开输出地址的 `/so101-station`。先选工位，再明确点击“规划并运行仿真”；回看时选择原任务，不重新运行来找结果。`./so101.sh doctor` 是检查的快捷入口。

工作台不在相邻目录时，可显式配置仓库根或其中的 `apps/fishbot-control-station`：

```bash
export WORKBENCH_ROOT=/path/to/fishbot-ros2-slam-tools
./so101.sh workbench doctor
./so101.sh workbench start
```

也支持 `FISHBOT_ROOT`；两者同时设置时以 `WORKBENCH_ROOT` 为准。显式路径无效会直接指出配置问题，不悄悄改用别的环境。`SO101_ROOT` 由入口设置为当前仓库的绝对路径；已设置的 `SO101_PYTHON` 原样传给工作台。需要建立仿真 Python 环境时，在本仓库运行以下安装命令，再根据 `doctor` 提示完成工作台前端构建：

```bash
python3 -m venv .venv-station
.venv-station/bin/python -m pip install -r experiments/colab-twin/requirements-station-runtime.txt
export SO101_PYTHON="$PWD/.venv-station/bin/python"
./so101.sh workbench doctor
```

工作台启动参数可继续传入，例如 `./so101.sh workbench start --port 5186`。首次安装、运行环境检查与新物理回合验收是不同步骤；历史通过结果不会自动变成当前环境已验证。

### 编辑和执行各自支持什么

草稿可以继续编辑和预览。执行器支持原八步抓放，或等价的 `pick → transfer → place` 三段；`seconds=1` 是模板字段，不是自定义运行时长。底座固定，当前物体、障碍与坐标变换有明确范围；预览中摆得出来，不表示通过执行检查。工作台可读取 `station_executor.py --describe-json` 的 `execution_boundary` 和原有能力字段，在运行前说明当前可执行范围，保留超出范围的草稿用于预览。

新位置仍由原规划、碰撞与物理判定检查。先从 A/B 场景或已有配方修改一个参数，观察本回合结果；不把有限场景外推为任意物体、任意程序或实机抓放。

## 独立学习示例：SmolVLA 与 Sawyer

[预训练 SmolVLA 演示](experiments/pretrained-demo/README.md)用于认识成熟模型：它驱动 **Sawyer 仿真机械臂**，目前尚未适配 SO101，不是上面工位的控制策略。历史 4GB GPU 实跑推物、抓取移到目标、箱间搬运，最终默认 10 步观察设置各一回合达到官方目标范围判据，原 50 步抓放失败保留；这些判据没有验证松爪后静稳。

可按独立示例说明换任务或初态体验，再根据实际缺口决定是否适配。已有 SO101 工位、模型学习示例与实体跟随器分别说明能力；不因切换入口自动恢复训练、50Hz 微优化、20＋20重复评测或跨仓同世界硬拼。方向依据见 [D006](docs/DECISIONS.md#d006)，当前接续以[工位计划](plans/workcell-productization-20261024/task_plan.md)为准。

## 维护与实体跟随器入口

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
离线测试不代表仿真或实机验收。旧so101_ws、so101-ros2-arm远端已退役，完整Git历史和必要模型／录制保留在私有备份中。

## 历史分层实验：Colab 与接触抓放

下列命令和结论保留各历史阶段的复跑与研究来源，当前体验优先使用上面的 SO101 工位入口。历史“下一步”不自动恢复云端实验或训练任务。

运动自主规划以 MuJoCo 为核心，复用已有 SO101 模型与 OMPL 规划经验。位置 IK、OMPL 自动绕障、MuJoCo 物理执行已接入，本地与Colab CPU 20/20轮通过，可见场景与视频回收已复验通过；保留原合成轨迹基线。平台入口回收视频、轨迹与指标：

```bash
python3 experiments/colab-twin/run_colab.py --session so101-planning --episodes 20 --seed 0
```

详见 [自主规划路线与既有资产](docs/MUJOCO_MOTION_PLANNING.md)、[选择依据](docs/DECISIONS.md)、[实验说明](experiments/colab-twin/README.md) 和 [当前计划](plans/colab-digital-twin-20261001/task_plan.md)。毕业设计、答辩与中期报告副本放在本机 `local-documents/`，个人文档、原始咨询和实验输出均被 `.gitignore` 排除。

历史逐层单回合入口（使用已安装实验固定依赖的 Python）：

```bash
python experiments/colab-twin/run_staged.py --render
```

依次核验依赖与 native imports → MuJoCo reset/10步 → 单次 IK/OMPL 绕障 → 一个位置伺服回合；失败即停止，后续阶段标记 `not_run`。2026-10-01 本机四层通过，末端误差 0.549 mm、20ms碰撞无无效采样、限位超出0，15.092秒/378帧视频完整解码通过；无云端分配或真机操作。静态路径的位置伺服反馈尚不包含动态重规划、抓放或视觉。


单臂夹取工位已建模：开放料盘、可移动物体、相机支架及三视图；物体真实支撑和夹爪开合已检查，尚未夹取/抬起。入口：`python experiments/colab-twin/preview_grasp_workcell.py`。详见[实验说明](experiments/colab-twin/README.md)。

## GR00T / LIBERO 策略实验

用户选定的扩展实验复用官方 GR00T N1.7 / LIBERO。CPU reset/物理步/双相机与 HF gated 配置访问已验证。最后一次尝试（第六次）已按用户指令完成并停止。L4 上官方 GR00T frozen 安装通过，LIBERO 依赖实际进入 Python 3.12 client venv，环境错位问题已在云端修复；随后导入 Matplotlib 因继承的 `module://matplotlib_inline.backend_inline` 后端不可用而失败。失败归档已回收并通过清单/哈希核验，模型加载与策略回合未启动。远端 worker 已结束，执行连接仍未返回；根 Agent 对唯一控制进程发送 SIGTERM，新的有界清理路径实际保存报告并成功 unassign，最终 active_assignments=0。子进程现固定 `MPLBACKEND=agg`，本地无头 PNG 绘制通过；该后端修正尚未云端复验。此轮不再分配 GPU，后续云端尝试需用户新的明确指令。 LIBERO 使用 Panda，尚未证明 SO101 策略迁移或任务成功。入口见 [实验说明](experiments/gr00t-libero/README.md) 和 [接续计划](plans/gr00t-libero-20261001/task_plan.md)，下载、模型、凭据及报告全部排除在 Git 之外。
单臂障碍夹取已接通：`python experiments/colab-twin/grasp_episode.py --render`。本地单场景实测绕障后夹起10g自由物体38.7mm、持续夹持1.48s；指尖接触垫/力矩为仿真假设，放置与实物验收待办。详见[实验说明](experiments/colab-twin/README.md)。

搬运放置入口：`python experiments/colab-twin/grasp_episode.py --place --render`。单场景已实际完成红盘抓起、绕障到蓝盘、松爪撤离及稳定落定；41项回归检查通过，Noslip接触求解与局部指尖接触垫仍属于仿真假设。
