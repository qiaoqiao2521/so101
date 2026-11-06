# A2 — 每次任务的结果与三维回放

日期：2026-11-06。范围：现有本地 MuJoCo、原网页任务入口与保存记录。未操作实体机械臂。

## 实现

复用 FishBot 工作台的无人机产物合同：`onTaskFinished`、`ensureArtifacts`、同任务产物 URL、原生 MCAP 播放器和 `EpisodeReview`。SO101 新增离线任务记录适配器，不重造录制平台或任务状态库。

任务结束后，由自己的 `request.json`、`status.json`、原物理报告、逐拍轨迹和保存模型生成 `episode.mcap`。内容包括关节、命令、接触力、阶段、原报告与 `skill_evidence`。新增的 `object_rotation` 只记录物体旋转，不进入策略或控制器。模型投影仅用 `mj_forward`，不重新推进物理。

结果页保留本任务视频、报告和抓取证据；回看链接只接受当前 UUID 下的 MCAP。历史任务选择同时支持 SO101 和无人机。任务回放布局使用原生三维、接触力曲线、关节曲线和阶段结果。

旧视频未保存逐帧仿真时钟，本轮不假造图像与 MCAP 同步。视频在任务结果页独立播放。旧轨迹缺物体旋转时显示位置标记，明确降级。转换失败不修改原物理终态；空轨迹不生成虚构回放。历史列表不会批量转换所有旧任务。

两次物理任务执行时 SO101 HEAD 为 `48ef3b7`；后续改动限于工作台回放、浏览器验证和文档，未再修改控制器或物理标准。

## 两次新网页任务

| 任务 UUID | 原终态 | 仿真秒 | 执行报告 wall 秒 | 逐拍记录 | 视频帧 |
| --- | --- | ---: | ---: | ---: | ---: |
| `b996faa5-fedb-4712-a67e-aca132d743e3` | succeeded，原物理 passed | 76.58 | 47.1153 | 3829 | 479 |
| `4e11341d-9269-4325-ac27-12bcf52eff12` | cancelled，原物理未通过 | 4.94 | 9.0742 | 247 | 31 |

正常回合：`grasp_success/place_success/controller_done=true`，`safety_stop=false`，障碍接触 0；抬升 40.998mm、持物 32.82s、落盘静稳 7.54s。释放审计通过，69.224s 脱离，释放后 XY 漂移 0.21155mm，脱离后峰值力 0N。自由物体、weld=0、mocap=0。原回位成功判据仍由完整物理报告裁决。

取消回合：原 `error_type=Cancelled`，没有抓取成立证据，界面不得显示成功。运行中刷新没有重复派发；两个任务使用不同 UUID。

本表 wall 是原执行报告字段，不等于浏览器等待、视频编码和 MCAP 转换的整个端到端耗时。本轮不作算法提速对照。

首次 `c792ef86-d957-48c3-87e2-797c39541a21` 因重建环境漏 `cv2` 在仿真 0 秒失败，原记录保留。补依赖后使用新 UUID 重试，未覆盖失败记录。

## 独立回读

新任务 MCAP 分别覆盖 0–76.58s／0–4.94s，索引 seek 可用。全部关节、命令、接触力、任务 ID、原报告和抓取证据一致。目标位置误差为 0，旋转矩阵最大绝对误差分别为 `3.50e-15`／`4.44e-16`。两份记录均 `geometry=true`、`object_orientation=true`。

两个 MP4 全部解码成功，帧数与各自报告一致；分辨率 640×480、6.25fps。视频取样与轨迹采样各保留原节拍，不把帧数相同当同步证明。

## 源码与复跑

SO101：`experiments/colab-twin/run_visual_grasp.py`、`requirements-station-runtime.txt`。轻量环境不安装训练模型。

工作台仓库 `fishbot-ros2-slam-tools`，分支 `codex/workbench-code-rebuild-20261018`：

- `apps/fishbot-control-station/so101-runtime.cjs`、`so101-recording.cjs`。
- `workbench-tools/so101_to_mcap.py --task-dir TASK_DIR --task-id UUID`。
- `workbench-review-tests/verify-so101-task-recording.py --task-dir TASK_DIR --require-full-scene`。
- `workbench-review-tests/so101-task-replay-browser.cjs`。
- `docs/SO101_TASK_REPLAY.md`：启动与用户操作。

原始任务保留于工作台 `workbench-tools/output/station-tasks/UUID/`。浏览器与视频读回证据位于 `workbench-review-tests/output/a2-physical-retry-20261106/`；MCAP 逐帧回读位于 `workbench-tools/output/a2-recording-validation-20261106/new-task-readback.json`。这些运行产物保持本地，不提交公开仓库。

本轮不代表完整 50Hz、冻结 20＋20、任意物体、连续安全域或 FishBot 同世界卸货验收通过。

## 网页最终验收

常用5186执行的 `so101-task-replay-a2-5186-v6-20261106/result.json` 已通过。两个真实任务在同一浏览器上下文中分别完成历史选择、保存后刷新、原生三维首／中／末与倒退、播放、阶段定位、回放刷新；关闭回放标签页后，主工位再刷新仍保留自己的布局、UUID、终态与MCAP链接。控制POST=0，回放写入=0，pageError=0；两次scene-mode POST只切换查看对象。桌面与窄屏16张截图保留，根已独立查看实际三维与结果页面。

历史选择复用原提交去掉layoutUrl的逻辑，并用已有layout=名字固定当前工位。没有新增存储层。原生回合面板保留“独立验收无报告／来源未绑定”的提示；本轮只绑定任务产物与保存数据，不伪造独立来源认证。
