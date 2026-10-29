# 固定红盘：改一个取料坐标后执行新任务

运行日期：2026-10-28；独立回读与交付日期：2026-10-29。R141 源码为 `784cd371902c99360d06df41baeed283a0e37a59`，Kaggle 实际任务 `muqiaoqiao/so101-x-linked-request-browser-20261028/1` 已 COMPLETE。接收源码与提交源码逐字一致，两例串行。

## 用户操作与实现

1. 在原 SO101 Station 网页选择“导入 JSON”，导入[左侧联动样例](../../experiments/colab-twin/scenarios/workspace-station/fixed-tray-linked-left.json)或[右侧联动样例](../../experiments/colab-twin/scenarios/workspace-station/fixed-tray-linked-right.json)。
2. 选择对象树中的“取料目标坐标系”。左样例将 X 从 `.2245` 改为 `.224`；右样例从 `.2555` 改为 `.256`。单位为米。
3. 点击“规划并运行仿真”。需要保存时使用原“导出 JSON”。

`pickup_request` 复用已有父坐标系解析；方块、接近点、抓取点沿各自局部偏移跟随。红盘 `pick` 与 `execution.pick_xy_m` 保持 `(.24,-.13)m`。单改 cube 时原来会留下两个旧设计点，先触发编辑一致性拒绝，尚未到 IK；此次通过数据组织消除重复编辑，没有新增控制引擎或点位白名单。

左保留 60mm 取料高位和 `.5rad` 开度；右保留 54mm 高位与 `.35rad` 高位预收爪。右侧两个调整分别承接此前的 IK 拒绝与盘壁扫掠问题，不按坐标自动选择工艺。高位若另改，接近点局部 Z 仍须同步。原八步、视觉先验、IK、285 对、1mm、244／原246点及 90sim／120wall 保持。

## 两次真实网页与物理结果

| 指标 | 左 X=.224m | 右 X=.256m |
| --- | --- | --- |
| 原任务 UUID | `c4c5eb7a-900e-4ae4-9259-7f674458ed00` | `ce9ce95d-661b-43f7-874b-5544d1c19470` |
| 网页／原物理 | passed／pass | passed／pass |
| 仿真 s／拍数 | 75.22／3761 | 78.30／3915 |
| episode wall s | 101.471347 | 97.704212 |
| 实际物理进程 wall／CPU s | 103.13／105.26 | 99.34／100.89 |
| 接近 OMPL 搜索／含后处理 s | .266113／.601153 | .332274／.622428 |
| 运输搜索／worker wall s | 4.473921／4.603009 | 4.769628／4.968191 |
| 脱离 worker wall s | 2.319974 | 2.184226 |
| 抬升 mm／持续持物 s | 40.963245／30.96 | 41.029740／34.12 |
| 放盘静稳 s | 7.54 | 7.54 |
| 释放 XY 漂移 mm／脱离后力 N | .184429／0 | .188403／0 |
| planned／measured 夹爪采样 | 244／244 | 246／246，另高位预收爪246 |
| 实际视频帧 | 471 | 490 |

两例真实夹起、搬运、放置、释放、脱离与回位均通过。安全停机、障碍接触均为0；自由物体 `free_object=true`，weld／mocap为0。回位最大 q6 误差两例均约 `.102544mrad`。两个实际 planner worker 均 consumed／joined，物理进程 exit0；全部任务和 worker 退出后才关闭自有 preview。

实际浏览器操作后，导出 Station 只改变 `pickup_request.position[0]`，其余执行内容相同；导入时仅步骤编辑器 ID 按原实现重建。导出→唯一 POST→原 request 严格相同。刷新恢复同 UUID，未重发。网页终态响应、原 status 内报告和磁盘 report 全值一致；原 status 没有顶层 id，用 request.id、目录、station_path/output_directory 和终态响应关联。

根已查看两侧真实编辑与成功截图。右侧提交前截图仍保留上一回合的已完成实时场景，只用它核输入框；右侧任务证据取新 UUID 的报告与成功截图。HTTP 报告下载的 `passed` 及视频 Range206 由原 QA 验证；下载 body 没有另存，不能声称独立保存了第二份完整 HTTP 报告。

独立回读对原 monitor、skill 与释放审计精确重放，左7340／右7320个2ms释放样本及脱离旗标一致。135项读回和补充身份核查无失败／关联缺证。测试数不替代上述物理结果。

## 定位、净距与计时边界

原 initial_qpos 中物体 X 确为 `.224`／`.256`，不是只改文档。RGB 交接目标分别为 `(.22412545947042734,-.13050833816470292)`、`(.2556298526685876,-.13050833816470292)m`；相对本次声明误差为 `.523591`／`.628822mm`。两估计恰与此前相邻中点相同，不能从这次0.5mm编辑宣称亚毫米视觉分辨能力。真值只用于重置与评价，没有传入控制策略。

本轮逐任务原1mm检查通过；没有重新计算整程最小距离。[此前R140净距](m1a-x-execution-clearance-results.md)属于其保存轨迹，不能直接作为这两个新任务的最小净距。连续X区域、默认准入及20＋20仍未通过。原控制交接后假设物体静止，没有新增动态视觉伺服。

网页 QA 命令 wall 为185.485305／191.760017s，包含载入、编辑、刷新与取证；物理 episode 仍受原120s上限。preview生命周期379.427436wall／333.098688CPU包含回收子进程，不与上表重复相加。本轮无原 EpisodeTiming，完整50Hz为unknown，历史未通过结论保持；不是性能A/B。两 worker 的 `sitecustomize: No module named 'wrapt'` 非致命警告原文保留。

## 证据、复跑与收尾

原件：`experiments/colab-twin/output/x-linked-request-20261028/kaggle-v1/so101-evidence.tgz`。根摘要 `root-readback.json`、独立 `independent-readback.json.gz` 与 `independent-identity-readback.json`；四张实际网页截图及 `right-linked-grasp-place.mp4` 可直接查看。

私有可复跑入口：`~/.cache/ros2-factory/codebuddy-so101-20261021/round141-x-linked-request/`，保留 manifest、原QA、builder、接收源码、派发回执和读回脚本。原工作台生产资产复用R134私有dataset，当前相关资产逐字核对；没有打包Carry／Drone在途改动。设置 `STATION_DOCUMENT`、`STATION_QA_PICKUP_FRAME_X`、`STATION_SINGLE_RUN=1` 后使用该私有QA与原preview即可复验；不要将整包称为最新工作台全部源码。

未展开TGZ或生成临时帧。独立JSON与独有Kaggle日志无损gzip、逐字回读后删除展开件，所选文件分配空间从32,837,632降到2,899,968字节，实际释放29,937,664字节。当前视频／截图、原输入、源码和失败警告保留。恢复：`gzip -dc independent-readback.json.gz > independent-readback.json`。清理明细见同目录 `cleanup.json`。

Next：这一片关闭“多点重复编辑→新X请求”缺口。连续区域准入仍需区域证据，不靠继续增加相邻单点宣称；M1b与M2 Carry已有待办独立接续，根Codex负责。Mint与实体操作不在本轮范围。Knowledge=already_covered，沿用Wiki《ROS2 与 FishBot》§20分层验收，具体结果留本计划。
