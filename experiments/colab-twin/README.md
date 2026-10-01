# SO101 Colab 运动规划实验

复用 SO101 原生模型，在 Colab CPU 完成“目标位置与静态盒子 → Mink 位置 IK → OMPL RRTConnect 绕行 → MuJoCo 物理执行 → 视频和指标回收”。本地真实模型与 20 轮 ±3 mm 目标扰动已通过；Colab CPU / OSMesa 20轮通过，可见场景与视频回收已复验通过。视觉、接触抓放和真机同步继续作为后续任务。

## 运行

前提：本机 `colab` CLI 已登录且 `colab sessions` 成功。开发机 CLI 0.6.0，当前不要求 GPU。

```bash
python3 experiments/colab-twin/run_colab.py --session so101-planning --episodes 20 --seed 0
# 保留原六秒合成轨迹基线
python3 experiments/colab-twin/run_colab.py --session so101-baseline --mode baseline
```

本地安装固定依赖后，可运行相同实验。没有 OSMesa 时默认 EGL；已有环境变量 `MUJOCO_GL` 优先。

```bash
python3 -m venv /tmp/so101-planning-venv
/tmp/so101-planning-venv/bin/pip install -r experiments/colab-twin/requirements.txt
/tmp/so101-planning-venv/bin/python experiments/colab-twin/run_experiment.py --episodes 20 --no-render --output experiments/colab-twin/output/local
cd experiments/colab-twin
/tmp/so101-planning-venv/bin/python -m unittest discover -p 'test_*.py'
```

规划输入是 [planning_scenario.json](planning_scenario.json)：六轴起点、三维目标 m、静态盒子中心与半尺寸 m。规划只改变前五个臂关节，夹爪指令固定 0.35 rad；没有人工绕行 waypoint。MuJoCo 3.3.7 / Mink 1.1.0 / OMPL 2.0.1 已固定。

## 本地主线逐层单回合

在已安装 [requirements.txt](requirements.txt) 固定直接依赖的 Python 环境运行：

```bash
python experiments/colab-twin/run_staged.py --render
# 不检查渲染时省略 --render
python experiments/colab-twin/run_staged.py
```

该入口只运行本机 CPU 仿真，不连接 Colab、GR00T、ROS或串口。依赖层逐项检查指定版本并实际导入 native bindings；第二层加载原SO101模型及障碍，真实reset并推进10步；第三层复用Mink IK和OMPL求解，要求直接路径被挡、精确绕行及独立路段复检；第四层复用独立MuJoCo位置伺服执行实例，验收实际TCP、20ms碰撞样本和关节限位。第三层没有神经模型推理，第四层尚无动态重规划。

每次在 `output/staged-<UUID>/` 创建新目录，保存 `report.json`、`planning.json`、`execution.json`、`trajectory.csv` 和派生场景；`--render` 额外保存视频和预览。报告逐层记录 `not_run/running/passed/failed`，只有前层通过才运行后层。缺失依赖/安装版本不符会在第一层停止；不会自动安装、分配云端资源或退回合成轨迹。`servo_episode_completed` 与 `task_success` 分开记录，任务误差超过1cm、碰撞样本无效或限位超出0.01rad会拒绝。

2026-10-01本机单回合四层均通过：reset10步/0.02s；主路线113点；执行7546步/15.092s；TCP误差0.549mm，碰撞无效采样0，限位超出0。756行轨迹全部有限且时间递增，末行TCP独立复算误差一致；378帧视频完整解码且场景障碍可见。32项测试通过（原29项与3项阶段停止边界），系统Python缺失依赖的真实CLI负例退出1，后续三层均未执行。单静态fixture的一个回合不能扩大为抓放、视觉、动态避障或真机验收。

## 结果和验收

云端每次结果保存到本目录 `output/planning-<时间>-<随机后缀>/`，不覆盖以前实验；全部由 `.gitignore` 排除。

| 文件 | 内容 |
| --- | --- |
| `simulation.mp4` / `preview.png` | 640×480、25fps 主绕障物理执行与预览 |
| `trajectory.csv` | 每20ms时间、六轴实际/指令rad、实际TCP m和接触数 |
| `planning.json` | IK残差、被挡直接路径、OMPL精确路径及离散验证 |
| `benchmark.json` | 逐轮目标、规划/执行结果、失败原因、误差统计和负例 |
| `report.json` | 版本、模型SHA、最终误差、碰撞/限位、批次验收及边界 |
| `scene.xml` / `results.zip` | 派生场景与完整结果包；场景引用对应运行环境的模型资源目录 |

通过条件：主正例直接路径被挡但找到精确路径；物理末端误差 ≤1cm、20ms检查无无效碰撞样本、限位超出 ≤0.01rad；请求的批次全部通过；不可达和封闭场景必须拒绝；视频存在。`run_colab.py` 下载后再次检查这些结果。失败不会退回合成扫掠或直线路径。

路径每段按5D欧氏步长≤0.025rad检查。派生场景补底座网格，并显式排除相邻装配；非相邻自碰保留。libccd距离是近似凸包模型指标，不是实物安全间隙，离散采样不是连续碰撞保证。命令速度≤0.4rad/s，未保证拐角加速度、真实电机力矩或抓取。详细证据与边界见 [规划说明](../../docs/MUJOCO_MOTION_PLANNING.md)。

## 模型、上传和资源边界

源模型 [so101.xml](../../workspaces/so101_ws/src/so101_mujoco/models/so101.xml) 与13份完整STL哈希保持不变。上游 [TheRobotStudio/SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100) 的 Apache-2.0 许可证随包保存。旧 `models/scene.xml` include名称错误；旧 `src/SO-ARM100/Simulation/SO101/assets/` 为零字节，不用于实验。

上传采用明确清单：模型、13STL、许可证、脚本、依赖与公开配置；manifest记录每个文件SHA256。个人材料、现场标定、凭据、录制、日志和ROS构建不进入包。脚本不调用跟随器Runtime、ROS或串口。

每次云端运行用 `~/.cache/so101-colab/run-*/sessions.json` 的独立状态。成功或失败都尝试 `colab stop`；正常释放后删状态，失败保留并打印恢复命令。强制终止/断电后的接续owner为根Codex，按该配置检查并释放遗留会话。

接口参考：[Colab CLI](https://github.com/googlecolab/google-colab-cli)、[MuJoCo可视化](https://mujoco.readthedocs.io/en/stable/programming/visualization.html)。
