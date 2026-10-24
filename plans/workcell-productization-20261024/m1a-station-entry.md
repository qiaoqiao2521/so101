# M1a：从网页选择开发布局并运行

## 用户现在能做什么

打开 <http://127.0.0.1:5186/so101-station>，点击“载入 X+20mm 布局”或“载入 X−20mm 布局”，检查草稿后点击“规划并运行仿真”。当前运行使用提交快照；刷新查询原ID。原录像、报告、实时三维和取消入口继续复用。窄屏入口为 `/so101-station-mobile`。

载入只改草稿，不启动任务，也不继承历史成功。参数随原生布局、JSON导入导出和复制保留；原默认模板仍为±10mm。两个样例是已测新布局，声明矩形仅是视觉定位先验，不是整个区域抓放保证。

## 输入合同

新增显式 `Station.execution`：

```json
{
  "mode": "workspace-development-v1",
  "pick_xy_m": [0.26, -0.13],
  "pickup_hover_z_m": 0.054,
  "target_region_xy_m": [[0.21, 0.27], [-0.16, -0.10]]
}
```

- 省略execution使用原默认；null、未知mode、非法已知参数或节点矛盾明确拒绝，不回退旧场景。
- 未知可选元信息警告后保留，不进入执行参数。原物理阈值、控制策略和90sim/120wall不能由这些元信息改写。
- 红盘pick节点与声明中心一致；开发模式的approach/grasp世界XY与cube一致，approach设计Z为高位+.02m，grasp设计Z=.02m。
- 红盘整体由同一builder进入实体与规划模型。cube只用于原reset；控制器仍从RGB取得目标估计。

实际浏览器导出的可复跑输入：[右侧](../../experiments/colab-twin/scenarios/workspace-station/x-plus20.json)、[左侧](../../experiments/colab-twin/scenarios/workspace-station/x-minus20.json)。样例可编辑，改变后仍做原IK、路径、全部碰撞、planned/measured244、抓取、释放和回位裁决。

## 新网页完整物理：2/2通过

| 网页样例 / 新task ID | sim s | episode wall s | 抬升 mm | 持物 / 静稳 s |
| --- | ---: | ---: | ---: | ---: |
| X+20 / 6e86ec73-db38-4d19-b48d-56dec4c1006c | 78.02 | 59.131 | 40.937 | 35.14 / 7.56 |
| X−20 / f7c265d5-5668-4643-a2f0-b7db2bc05d83 | 78.08 | 58.445 | 40.766 | 33.34 / 7.54 |

这两回合从原网页按钮提交，经原task-runtime调用Station执行器，非直接开发CLI回放。各只有一次任务POST；项目浏览器harness对刷新后同ID、无重发、原报告和视频Range206读取的断言通过，pageerror=0。原harness的这些时序检查只保存checks标签，没有另存完整reload网络时序或206响应元数据；独立JSON读回不冒称重新证明了这些时序。

两例原report的passed/grasp/place/done均true，无安全停机、无障碍接触；自由物体weld=0/mocap=0。所有3901/3904条轨迹arm_valid/finite为真；planned与measured闭爪各244/244。释放后峰值力0，XY漂移.377293/.373667mm，保持原2mm/0.02N条件。终态落盘、脱离、回位成立，回位最大误差.000102544/.000101346rad。双worker均consumed/joined/owned_ack，无launch_unknown或cleanup_unconfirmed。

两份视频均488/488帧，ffprobe独立读回640×480、6.25fps，与原记录一致；根查看网页成功截图。旧X开发CLI4/4独立保留，没有拼成新网页六回合。

本次网页入口未开启EpisodeTiming，也未采集精确process wall/CPU；它们为unknown，不能用episode wall替代，更不能用旧Kaggle周期填补。未新增50Hz、20+20或抗扰动成绩。

## 来源与验证

- SO101执行源码引用 `084cc7f6e01b93da54a4351f3194cd26de858432`；工作台本轮源码 `abc0ac7`，浏览器执行检查 `2b9fd90`。运行前后SO101工作树及域内执行／评分源码无变化。原任务产物不自带执行commit证明，以上为根操作记录引用。
- 工作台属于独立FishBot工作树 `codex/workbench-code-rebuild-20261018`，不是主FishBot dirty main。并行无人机修改后来由原owner提交为 `de94a6d`；未覆盖、重做或混入SO101评分，不声称共享仓库全程冻结。
- 根复验50项Python检查；网页数据33项；任务服务3项；生产构建通过，原两项包体积警告保留。
- 桌面／390px无运动浏览器9项通过，零任务写请求。两份真实导出均由Python准入核实。另一组浏览器实际按钮运行上述两回合，原生任务、报告、录像和请求分别核对。
- 内部GPT独立读回两任务 `independent-readback.json`，warnings=0；agent-link的Qoder交叉核对浏览器账本。AGY调用参数不兼容、CodeBuddy空返回未算有效实现产出，未为此改认证或harness。

原件保存在工作台被忽略的 `workbench-tools/output/station-tasks/<task ID>/`。无运动浏览器证据在 `workbench-review-tests/output/workspace-samples/`；执行证据分别在 `workspace-execution-20261024-v1/`、`workspace-execution-20261024-left-v1/`，含原请求、结果和截图。不提交运行日志、录像或会话状态。

## 剩余工作

M1a整体仍in_progress：连续有效包络、姿态／尺寸边界和产品默认准入没有完成。当前程序仍复用完整抓放组合，任意技能组合、恢复、冻结20+20和连续卸货仍按原M2–M4推进。

M1b首步已只读定位：此前X批次15641个完整周期中281拍>20ms，controller主导218拍。两个最大尖峰发生在separate→retreat切换，原controller同步 `_return_path(achieved_q)`；下一步细分该调用，再沿原worker研究迁移，保留实测q桥接、全部碰撞和244扫掠。该旧批次审计不是本次网页计时，也没有新提速结论。
