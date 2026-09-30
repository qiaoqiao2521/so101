# Progress

## Current

文档归档与 Colab CPU 基础平台完成；修正后的一命令运行成功并回收结果、释放会话。用户已选择运动自主规划以 MuJoCo 为核心，单主线整理和实际 AGY 咨询完成；算法接入待开始，当前仍为合成轨迹。

## Done

- 六份复制件校验 SHA256、Git ignore 和无索引记录。
- Colab CPU 会话分配与固定版本依赖安装成功。
- 17 文件的模型/脚本清单包上传；其中无个人文档或现场数据。
- `python3 experiments/colab-twin/run_colab.py --session so101-twin-final-20261001` 实际执行成功；MuJoCo 3.3.7/OSMesa，3000 步、6 秒、150 帧。
- 下载的 MP4 独立确认 640×480/25fps/150 帧并完整解码；CSV 150 行，全部数值有限、时间每 0.04 秒连续递增。
- 最大关节限位超出 0 rad；最大跟踪 RMSE 约 0.000575 rad。只代表合成轨迹物理基础实验，不代表碰撞自由规划或抓取。
- 四项资源清理失败路径测试通过；已有四项 teleop 回归、静态布局和前端语法检查通过。
- 本轮创建的全部 Colab CPU 会话均已释放；无 GPU 或真机操作。
- 两份历史修订 DOCX 和中期 Markdown 从远端副本保存在被忽略的 local-documents/prior-revisions，后续停止追踪，不重写历史。
- 完成本地 SO101 多工程/快照与有界历史核查；确认完整 MoveIt/RRTConnect 代码、缺失 MTC 源码和零字节逐轮证据。
- 实际调用 AGY 原生CLI单次只读咨询；采纳 MuJoCo + Python IK/OMPL 主方向。原始响应仅保留在被忽略的 local-documents。
- 整理 PROJECT / README / ARCHITECTURE / DECISIONS / 规划路线与现有计划，明确组件职责、复用资产、Gazebo/Colab边界和三步正反例验收。

## Remaining

S2 模型/TCP/坐标/碰撞与位置 IK 隔离验收；S3 全局避障；S4 时间参数化、执行与小批量评估。后续接触抓放、视觉与真机同步保持未完成。交付通过既有 master 非强制推送，版本由 Git 记录。

## Issues / Handoff

当前脏开发树使用旧 Git 基线，保留原状，在基于 origin/master 的隔离工作树完成本轮交付。已有工作区嵌套未出生 Git 与损坏历史备份保持不动。

根 Codex 接续范围：旧开发树与新远端基线的安全对齐；现场动作、串口配置、标定、登录/业务日志、录制和生成 ROS 导出保持本地。主从迟钝根因未实测，既有 `../teleop-latency-20260922/task_plan.md` 仍是恢复入口；不以本次离线仿真关闭该待办。

ROS/MES、Gazebo、真实 YOLO 与真机闭环保留原工作区任务状态；需要恢复时从 `../../workspaces/so101_ws/docs/任务清单.md` 进入，不重新宣布验收。

旧 `docs/HARDOFF_2026-06-26.md` 含明文 sudo/SSH 凭据及带凭据的历史命令，原件保留并精确忽略，不进入发布。根 Codex 未来如需复用，只从原件提取不含凭据、注明历史范围的结论；不复跑历史命令或恢复会话。

旧 `docs/SO101_MOTOR_TO_URDF_MAPPING_2026-06-27.md` 含现场舵机读数与临时映射，按项目“标定留本地”规则精确忽略并保留。其 wrist_roll 符号描述内部不一致，简化公式漏 scale；根 Codex 若恢复标定工作须核对当前源码与现场数据，不直接采用这份报告。其余两篇 Gazebo 历史报告已加历史边界，不作为当前运行验收。

MTC缺失核心和零字节逐轮产物留作待恢复历史，不从summary重造并冒充原件。根Codex从原生MJCF接续自主规划；规划与执行实例分开，碰撞检查必须覆盖路段。现场 `so101_gz_scene/{reality_map.yaml,calibration.yaml,calibration_report.txt}` 继续保留本机并精确忽略。

## Next

根Codex从 `../../docs/MUJOCO_MOTION_PLANNING.md` 的第一步开始：确认TCP/坐标/五轴限位与现存碰撞几何，隔离验证位置IK及不可达目标。现有运行命令暂不变；不以本轮文档整理宣称自主规划已通过。
