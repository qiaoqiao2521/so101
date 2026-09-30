# SO101 architecture

跟随器Web应用位于mint_follower_demo，项目根由实际文件位置解析；默认ROS场景与workspace路径均在本项目内。场景工具从自身位置解析动作和映射文件，不再绑定个人桌面目录。

so101.sh是统一入口，check为纯静态检查，follower启动应用但不执行旧start.sh的fuser/权限修改逻辑。Humble基础环境保留原语义；没有在本轮替换为Jazzy或启动仿真。

嵌套历史/构建产物/私有标定原样保留。旧目录是指向此处的兼容软链接，不是另一份源码。

Colab 离线实验位于 `experiments/colab-twin/`。prepare_bundle.py 从现有 MuJoCo 包选取模型、13 个完整 STL和许可证，并加入规划组件与公开场景配置；run_colab.py 分配独立 CPU会话、安装固定依赖、上传、执行、下载并释放会话。run_experiment.py 只操作仿真关节，在派生场景增加工作台与静态方块，在Colab用OSMesa、本地可用EGL输出视频、CSV和指标。该链路不调用跟随器Runtime、ROS或串口。个人设计材料与输出分别位于根local-documents与实验output，两者均被忽略。

## 运动自主规划主线（2026-10-01，已接入）

MuJoCo 是模型、正向运动学、碰撞检查、物理执行和渲染的统一底座；IK 与路径搜索是独立算法组件。目标位置经位置 IK 转为五个臂关节目标，OMPL RRTConnect 在关节范围内搜索路径，状态与路段有效性由同一 MJCF 的 MuJoCo 规划数据实例检查。轨迹加上时间与速度约束后，由另一执行数据实例运行物理仿真，输出实际 TCP、关节状态、碰撞和目标误差。

规划查询使用 `mj_forward`，执行使用 `mj_step`，不得让候选状态查询改变执行状态。夹爪初期固定，五轴 arm 和 gripper 分工明确；无解、碰撞、超时、跟踪失败分别记录。`position_ik.py`、`joint_planner.py`、`collision_scene.py`、`planning_experiment.py` 已接入默认规划模式；`synthetic_target` 仅保留在显式 baseline 模式。

现有 MoveIt/ROS 接口保留在 workspace 内，复用其关节语义、RRTConnect 配置、轨迹导出和评估字段；运行时不作为第一阶段 Colab 依赖。Gazebo 用于后续本地 ROS 联调与独立对照，不另建硬件项目。模型差异、历史缺失和验收入口见 [规划路线](MUJOCO_MOTION_PLANNING.md)。

派生场景补固定底座碰撞，选择libccd并同步六对相邻装配排除；非相邻自碰仍检测。每条规划边≤0.025rad离散检查，执行每20ms用真实六轴状态查询。quintic弧长时间参数化仅保证命令速度≤0.4rad/s，不保证拐角加速度/电机力矩。输出分次保存到ignored output目录，每个云端会话状态独立且成功/失败都尝试释放。
