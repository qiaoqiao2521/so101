# SO101 Colab 仿真实验平台

运动自主规划的 MuJoCo 主平台：复用现有 SO101 模型，在 Colab CPU 上跑离线物理实验，下载视频、轨迹和指标。当前仅完成合成轨迹基线；后续依次接入位置 IK、OMPL RRTConnect、MuJoCo 碰撞检查与轨迹执行。视觉、物理抓放和真机状态同步在自主到达验收后展开。

已有算法、缺失历史、Gazebo/Colab 可行性和验收顺序见 [规划路线](../../docs/MUJOCO_MOTION_PLANNING.md)。本目录的脚本和 requirements 本轮没有增加规划库，运行结果仍代表基础实验。

## 一次运行

前提：本机 `colab` CLI 可用且已完成用户登录；`colab sessions` 能成功返回。当前开发机 CLI 为 0.6.0，按其实际 `--help` 验证参数。

```bash
python3 experiments/colab-twin/run_colab.py --session so101-twin
```

脚本只分配 CPU，不要求 GPU；成功与失败都调用 `colab stop` 释放本次会话，使用本机缓存下的独立 session config，不干预其他会话。正常释放后删除这份 config；释放失败则保留并打印精确接续命令。若进程被强制杀死或机器断电，应在 `colab sessions` 中检查遗留会话，使用 `~/.cache/so101-colab/run-*/sessions.json` 对应配置接续释放。

输出位于本目录 `output/`，被根 `.gitignore` 排除：

- `simulation.mp4`：6 秒、25 fps 的 640×480 无头渲染。
- `trajectory.csv`：时间、六轴目标与实际弧度、末端米坐标、接触数。
- `report.json`：模型哈希、依赖版本、关节跟踪 RMSE、运动跨度和验收边界。
- `preview.png`、`scene.xml`、`results.zip`：预览、派生场景和可回收结果包。

## 模型和数据边界

模型来自仓库 `workspaces/so101_ws/src/so101_mujoco/models/so101.xml` 和其完整的 13 个 STL。上游来源为 [TheRobotStudio/SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100)，打包保留现有 Apache-2.0 许可证，manifest 对每个文件记录 SHA256。原模型文件不修改；实验副本增加工作台和静态方块。

旧 `models/scene.xml` 引用了不存在的 `so101_new_calib.xml`，本实验直接读取有效 `so101.xml`。`src/SO-ARM100/Simulation/SO101/assets/` 本机副本为零字节，禁止改用该目录打包。

上传采用明确文件清单，只含实验脚本、依赖、模型、网格和许可证。`local-documents/`、凭据、现场标定、录制、日志、ROS 构建和其他工作区内容都不进入上传包。

## 本阶段验收

验证六关节/六执行器、受限合成轨迹、有限状态、关节限位、末端实际移动和无头渲染。接触数与跟踪误差是观测值，不等于避障或抓取验收。初始轨迹只是小幅关节空间扫掠，`run_experiment.py` 的 `synthetic_target(time_s, initial)` 是后续定义业务实验动作的位置（单位为弧度）。

这是数字孪生实验基础，尚未验证真实机械臂参数、视觉识别、碰撞自由规划、抓取成功或实机同步。不把已有 ROS Humble 语义当作 Jazzy 移植完成。

接口依据：[Google Colab CLI](https://github.com/googlecolab/google-colab-cli)；CPU 无头渲染依据：[MuJoCo 官方可视化文档](https://mujoco.readthedocs.io/en/stable/programming/visualization.html)。
