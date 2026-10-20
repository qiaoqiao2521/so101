# 工作站草稿执行适配

`station_executor.py` 将网页 Station JSON 接到原 `run_visual_grasp.run_physical_episode`。输入支持裸 Station，或 `{id, submittedAt, station}` 任务快照。仅运行 MuJoCo 仿真，不访问机械臂串口或恢复训练。

```bash
~/.cache/so101-graspgenx/upstream/.venv/bin/python \
  experiments/colab-twin/station_executor.py \
  --station /absolute/task/request.json \
  --output-dir /absolute/task \
  --cancel-file /absolute/task/cancel.request
```

`--describe-json` 返回中文能力说明。`status.json` 原子更新，包含状态、阶段、仿真时间、原报告及产物路径。创建 cancel-file 后，原执行循环协作停止并保存报告及部分录像。界面只能在终态后显示已取消；无法规划、定位拒绝、碰撞保护、物理任务失败分别保留。

当前仅支持原始八步模板：开爪→接近→抓取点→闭爪→抬升→放置→开爪→脱离。目标位置与参考系按已声明模板映射，实际运动由现有控制器规划；步骤 seconds=1 是编辑模板字段，不等于每段一秒。

- 方块世界坐标支持 X=0.24±0.01m、Y=-0.13±0.01m、Z=0.01m。
- 附加 obstacle 节点采用 50×56×130mm 轴对齐方盒，原内置障碍同时保留。
- 参考系逐级平移求和；固定机器人与目标的世界位置保持模板值。
- 不支持的目标修改、节点、程序重排和时长会列出具体原因；不会静默使用旧场景。
- 释放复用已有 floor_yaw 和 28mm 指间高度；1mm 净距、释放2mm漂移/0.02N再接触等原物理标准不变。

输出包括 `resolved-station.json`、`episode/report.json`、轨迹、定位图和本次录像。录像以真实物理状态快照后置渲染，640×480、6.25fps；不推进物理、不制作脚本附着物体动画。无新内容哈希门锁或前序任务依赖，每个输出目录是独立回合。

工作台通过现有独立 FishBot 仓库的 `apps/fishbot-control-station/so101-runtime.cjs` 调用本入口，Web 依赖与机器人依赖各自安装。工作台地址 http://127.0.0.1:5186/so101-station ，右侧显示本次任务的原生实时三维，本次录像与原报告位于任务栏；原历史录像使用独立入口。

2026-10-20：35项定向测试通过。默认CLI完整回合成功，74.76sim/53.13wall；修改方块X=.245m并添加障碍后25.30sim协作取消，初态与XML确认输入被消费。浏览器经HTTP重新启动的完整回合74.76sim/50.22wall成功，另一次网页取消在4.16sim结束；刷新未重发。首轮旧释放配置触发再次接触并正确终止，失败保留。

证据在 canonical `experiments/colab-twin/output/station-integration-20261020/` 及工作台忽略的 `workbench-tools/output/station-tasks/`；运行产物不入 Git。上述是固定任务接入验收，不代替20+20鲁棒性评测、实时50Hz或实机验证。

## 实际几何与编辑预览

`station_scene.py --model-json` 输出原始 STL 白名单和默认完整场景。`station_scene.py --preview /absolute/station.json` 将草稿解析为标准 Foxglove SceneUpdate，仅调用 `mj_forward`，不推进物理。13 个原始 STL 对应 17 个机械臂和夹爪实例；编译时的 mesh 平移/旋转只反解一次。

`run_physical_episode` 的可选 `scene_callback(model, data, *, elapsed_s, phase, final=False, row=None)` 读取执行中的实际 `MjData`。不配置 callback 时保留原入口；显示导入、初始化或发送失败只警告，不覆盖物理结果。最后一帧在视频编码前强制发布。

工作站 `status.json` 新增 `scene`、`scene_seq`、`scene_time_s`、`scene_phase`、`scene_final`、`scene_source`、真实物块四元数与已有双指接触力。常规显示约 10Hz，阶段变化和终态强制更新；这不是完整控制周期 50Hz 的证明。Web 端复用原生 Foxglove 传输与 3D，不自行求连杆 FK。

2026-10-20 新实时三维验收：真实浏览器抓放任务 `e6ddc0ce-682c-4923-aebb-1990b3840784` 在 74.74sim/106.662wall 完成，夹取、放稳、脱离和回位均通过，无安全停止，静稳 7.52s；发布 838 个场景状态。网页取消任务 `5f390fa1-ad63-433f-ab4d-32cf7d9fe924` 在 5.12sim 结束，最后实际姿态保留，预览与任务切换可恢复该末态。根独立执行 19 项几何/执行适配测试通过，包含 XML/STL 独立变换对照、预览零物理步、可选显示导入失败不覆盖原定位拒绝。

证据在工作台忽略的 `workbench-review-tests/output/station-live/` 和 `workbench-tools/output/station-tasks/<id>/`。当前只验证固定模板与本机显示，仍不替代批次鲁棒性、50Hz、CY部署或实机验收。
