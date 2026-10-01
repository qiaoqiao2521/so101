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

## GR00T / LIBERO 策略实验

用户选定的扩展实验复用官方 GR00T N1.7 / LIBERO。独立 CPU 环境已实际完成 reset、10 个物理步和双相机检查；HF CLI 授权与 Cosmos gated 配置下载已验证。Colab L4 的系统依赖阶段通过，策略回合仍受云端通信超时阻碍，最终会话清单为 0。单回合入口和恢复路径已接入；LIBERO 使用 Panda，尚未证明 SO101 策略迁移或任务成功。入口见 [实验说明](experiments/gr00t-libero/README.md) 和 [接续计划](plans/gr00t-libero-20261001/task_plan.md)，下载、模型、凭据及报告全部排除在 Git 之外。
