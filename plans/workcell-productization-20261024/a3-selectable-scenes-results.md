# A3.1 — 两个已有工位的网页选择与真实回看

日期：2026-11-06。已完成本地软件／MuJoCo切片，不操作实体机械臂。

## 用户入口

打开本机5186的 `/so101-station`，在“选择场景”加载工位A或B，再点击“规划并运行仿真”。选择仅生成独立草稿，不自动运行；修改场景后显示“自定义草稿”。运行期间不能切场景。选择后刷新保留原草稿，任务完成后从当前结果或历史任务打开本次录像、报告、抓取证据与三维回放。

复用原 `workspaceStationSample`，场景目录只新增名称和说明，没有新增一套参数、执行器、任务接口或播放器。原工位输入仍可导出／导入为Station或工位配方。

## 原样场景

| 场景 | 红盘中心 XY (mm) | 方块目标 XY (mm) | 蓝盘 XY (mm) | 接近高位 |
| --- | --- | --- | --- | --- |
| A · 近侧取料／斜向放盘 | 235, −130 | 220, −130 | 200, 200 | 60mm |
| B · 远侧取料／正向放盘 | 260, −130 | 260, −130 | 240, 140 | 54mm |

A的方块相对红盘偏X −15mm，不能把红盘中心也写成220mm。两者均沿原默认0.5rad接近开爪，不套用其他实验的54mm／0.35rad配方。原八步、固定障碍、IK/OMPL、碰撞扫掠与物理裁判保持。

两次网页导出的Station、POST正文和原 `scenarios/workspace-station/x-minus20.json`／`x-plus20.json` 全等。选择及刷新不派发任务，每个工位仅一次新任务POST；运行中两场景按钮禁用。

## 两次新物理回合

| 工位 | 完整任务 UUID | 原物理结果 | 仿真秒 | report wall秒 | 轨迹／力帧 | 视频帧 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| A | `42460e66-aab5-4c60-bda9-39ddf5d80245` | passed | 78.02 | 52.8662 | 3901 | 488 |
| B | `4ddaf8b6-3f72-42ec-a943-51419a036cba` | passed | 77.76 | 45.1246 | 3888 | 486 |

两者原 `grasp_success/place_success/controller_done=true`，无安全停机、障碍接触；自由物体、weld=0、mocap=0。报告wall为原字段，不是端到端总耗时；场景不同，不据此做算法加速对照。

| 原物理证据 | A | B |
| --- | ---: | ---: |
| 最大抬升 | 40.875mm | 41.002mm |
| 持物时长 | 33.26s | 34.86s |
| 蓝盘静稳 | 7.50s | 7.54s |
| 脱离时刻 | 70.700s | 70.402s |
| 脱离后最大XY漂移 | 0.17223mm | 0.20820mm |
| 脱离后峰值接触力 | 0N | 0N |

原释放审计均passed/detached，未放宽原2mm漂移／0.02N接触判据。末帧仍脱离、控制器完成；原回位成功条件保持。历史通过只用于确认场景来源，本表均为本轮新网页任务。

## 数据与网页验收

独立Python审计完整MCAP：各任务的UUID、原报告、skill_evidence、每帧关节、命令、接触力和目标位姿一致；完整几何／物体旋转可用，索引seek通过。目标位置最大误差0，旋转矩阵最大绝对误差A为4.61e-15、B为3.55e-15。两个MP4全部解码，帧数与原报告一致。

原A2只读QA用明确的两成功任务列表复跑。在同一浏览器上下文中，分别完成历史选择、保存后刷新、三维首／中／末、倒退、播放、阶段跳转、回放刷新，以及关闭回放标签页后工位再刷新。两个UUID、原终态与各自MCAP保持；控制POST=0、回放写入=0、pageError=0。桌面与窄屏共16张截图保留。

首次只读回看测试在popup事件后立即读取空URL失败，证据保留；改为等待同源首次导航后，使用同两任务完成v2验收，没有重跑抓放。原视频独立播放，未补造逐帧同步；原生面板仍区分原报告、独立验收与来源认证。

局部测试：Station 52项（原43＋新增9）与原execution 18项，共70/70；生产构建成功，仅原有两项包体积建议。旧workspace／recipe QA仅更新选择器并通过语法检查，本轮未冒充重跑其整套物理流程。

## 版本与复跑入口

网页与场景源：FishBot工作台分支 `codex/workbench-code-rebuild-20261018` 的 `d04b49e`；后续仅修只读QA的popup等待。两物理回合运行时SO101 HEAD为 `3b9cdb1`，原执行器源码未修改。

在工作台 `apps/fishbot-control-station`：

```bash
STATION_TEST_URL=http://127.0.0.1:5186 \
STATION_SAMPLE=x-minus20 STATION_SINGLE_RUN=1 \
STATION_QA_OUTPUT=workbench-review-tests/output/a3-new-a \
node workbench-review-tests/station-execution.cjs
```

B替换为 `x-plus20` 并使用新的独立输出目录。显式执行会创建新任务；已有任务只回看，不重复执行。

只读两任务验收复用 `so101-task-replay-browser.cjs` 的 `SO101_REPLAY_TASKS` 参数，传入本表UUID、原终态及唯一label。逐帧回读使用 `verify-so101-task-recording.py --task-dir TASK_DIR --require-full-scene`。

本地证据位于工作台 `workbench-review-tests/output/a3-near-run1-20261106/`、`a3-far-run1-20261106/`、`a3-scenes-replay-v2-20261106/`、`a3-independent-readback-20261106/`；原任务及MCAP保留在 `workbench-tools/output/station-tasks/UUID/`。运行产物保持Git忽略，不发布到公开源码仓库。

本片仅两个既有固定工位的单回合验收，不代表连续工作区、任意物体、20＋20、完整50Hz或真实机械臂通过。A3后续感知／新场景要素尚未启动。
