# 固定红盘 X 中点：原网页与物理整链

日期：2026-10-28。承接[中点 IK／盘壁诊断](m1a-x-gap-results.md)，本轮验证用户从原 Station 网页导入配置并实际运行。原执行器固定 `261e3e6813ce2a07fda919cb276491e478665161`，没有修改 IK、控制器、裁判或全局默认。

## 用户新增操作

在原 SO101 Station 网页选择「导入 JSON」，导入以下一份文档，再点击「规划并运行仿真」：

- [左 X−15.5mm](../../experiments/colab-twin/scenarios/workspace-station/fixed-x-minus15p5.json)：cube 世界 XY 为 `(.2245,-.13)m`，原 60mm 高位／`.5rad` 开度。
- [右 X＋15.5mm](../../experiments/colab-twin/scenarios/workspace-station/fixed-x-plus15p5.json)：cube 世界 XY 为 `(.2555,-.13)m`，显式 54mm 高位／`.35rad` 高位预收爪。

红盘均固定在 `(.24,-.13)m`。导入不运行；运行使用当前草稿快照。右侧的降低高位与预收爪分别处理已验证的 IK 拒绝和盘壁缺证，两者同时保留。没有按坐标自动选择工艺，也不从成功点插值开放连续区域。

## 真实浏览器与原物理结果

复用原 Kaggle CLI，在同一云 VM 串行运行原网页、HTTP 服务、隔离 Chromium 和 Station 执行器。没有 mock 或本地并发仿真。Kaggle `muqiaoqiao/so101-x-station-browser-20261028/3` 已终态 COMPLETE。

| 项目 | 左 X−15.5mm | 右 X＋15.5mm |
| --- | --- | --- |
| 原任务 UUID | `9e4059a7-3f24-4852-a8d5-c071ab92fd8b` | `d2e1ca4e-8226-4e01-9d46-7f411a2e842b` |
| 网页／原物理 | passed／pass | passed／pass |
| 仿真 s／拍数 | 75.16／3758 | 78.32／3916 |
| episode wall s | 91.305649 | 91.361726 |
| 实际物理进程 wall／CPU s | 92.82／94.48 | 92.91／94.94 |
| 原 OMPL 搜索／含后处理 s | .259614／.539199 | .229014／.518690 |
| 运输搜索／worker wall s | 4.104384／4.280666 | 4.531738／4.676352 |
| 脱离 worker wall s | 2.086086 | 2.073811 |
| 实际抬升 mm／持物 s | 40.968624／30.92 | 41.024345／34.12 |
| 原静稳 s | 7.54 | 7.54 |
| 释放 XY 漂移 mm／脱离后力 N | .186931／0 | .184860／0 |
| planned／measured 闭爪采样 | 244／244 | 246／246，另高位预收爪 246 |
| 实际录像帧 | 470 | 490 |

两例原抓取、放置、释放、脱离与回位均通过；安全停机与障碍接触为 0。自由物体、weld=0、mocap=0，原 1mm／全部碰撞对、采样分辨率与 90sim／120wall 保持。最终 q6 最大回位误差均约 `.102544mrad`，最大速度小于 `1e-7rad/s`。

实际 RGB 进入规划：左 `(.22412545947042734,-.13050833816470292)m`，右 `(.2556298526685876,-.13050833816470292)m`；相对声明位置误差分别 `.631418mm`、`.524661mm`。左值超出此前另一位置面板的 `.616511mm` 观测最大值，因此旧最大值不能当新位置的误差上界。取料盘没有随物体移动。原交接仍假设闭爪前物体静止，交接后没有视觉伺服；不是动态目标能力。

两次各一条真实创建任务 POST。刷新恢复原 UUID，未重复提交；原报告下载及录像 Range 206 均通过。导入／导出仅允许步骤编辑器 `program[].id` 重建，额外核 ID 非空唯一；坐标、节点 ID、动作顺序、时长、execution 和元信息严格一致。导出→实际 POST→原 request 全字段相同。

独立 91 项读回无失败：原 monitor／skill 及各 7330 条 2ms 释放样本精确重放，未评分尾行 0；完整夹爪扫掠、实视频解码、自由物体与回位核实。根已查看两张真实网页截图，原任务名／UUID、完成状态、蓝盘内物体、录像和物理摘要可见。已确认原任务终态、worker 退出；仅随后 TERM／wait 自有 preview，没有杀物理 worker。

## 耗时范围与保留失败

网页 QA 命令 wall 为 142.442699／149.966138s，包含载入、导入导出、刷新和取证；分别单列浏览器进程树 CPU 8.435986／8.538439s。物理进程仍使用原 episode 120s 上限。preview 生命周期 CPU 271.204812s 已包含回收的物理／FK 子进程，不能再与物理 CPU 相加。这轮不是性能 A/B，不与旧 CLI 或不同 VM 的秒数相减。

- v1：两例导入导出断言失败，仅步骤 UI ID 重建；没有任务 POST 或物理。原失败、原严格读回和修正后的诊断保留。
- v2：导入、POST、原 request 已贯通，但私有计时包装依赖云端缺失的 `/usr/bin/time`，两 worker exit127，物理 Python 未启动。保留原失败；无报告不算物理通过。
- v3：仅私有云 bootstrap 补 GNU time，包装器在可选计时器缺失时警告并继续原执行器。正常／缺失分支参数传递已核；不改执行语义。两个 worker 的 `sitecustomize: No module named 'wrapt'` 非致命警告原文保留，不为清日志重跑。

云 `physical_started` 字段仅表示发现任务记录，不能单独证明 MuJoCo 启动。本次物理成功取自原报告、轨迹和独立重放。

## 范围与复跑

这两个显式开发文档可从原网页运行。普通模式仍为 ±10mm，通用帮助文字未按开发文档动态改写；不把该文字当作这两次实际请求的坐标。连续 X 域、第二放置工位中点、定位不确定性覆盖、20＋20尚未验收。原网页入口没有 EpisodeTiming，本轮完整 50Hz 为 unknown；历史完整 50Hz 未通过结论保持。

命令行复跑使用原入口（需现有 MuJoCo／EGL／native 环境）：

```bash
python experiments/colab-twin/evaluate_station.py \
  --station experiments/colab-twin/scenarios/workspace-station/fixed-x-plus15p5.json \
  --output-dir experiments/colab-twin/output/x-midpoint-replay --timing
```

网页 QA 复用工作台 `apps/fishbot-control-station/workbench-review-tests/station-execution.cjs`；设置 `STATION_DOCUMENT` 为文档绝对路径、`STATION_SINGLE_RUN=1`，必要时设置 `STATION_CHROME_BIN` 和原 preview URL。真实服务须连接上述 SO101 源码；不新建平台。

原件在 `experiments/colab-twin/output/x-station-browser-20261028/kaggle-v{1,2,3}/so101-evidence.tgz`；根 `root-readback.json`、两张 `*-web-success.png` 和 `right-midpoint-web-grasp-place.mp4` 可直接查看。独立 reader 报告 gzip 无损压缩并逐字节回读，释放 **30,601,216 已分配字节**；恢复用 `gzip -dc independent-readback.json.gz > independent-readback.json`。物理 TGZ 未展开，没有临时帧。已移除完成上传的重复硬链接，因另一链接保留而释放 0 字节，不虚报空间收益。当前资产包、构建器、原失败及恢复入口均保留在私有 `~/.cache/ros2-factory/codebuddy-so101-20261021/round134-station-browser/`。

Next：先验证同两请求在已有 `(.20,.20)m` 放置工位的完整任务，再处理输入不确定性覆盖。M1b 的 grid／FK 数值误差／pending-hold 证明、M2 Carry 网页等待接续仍独立待办。Knowledge=already_covered，沿用 Wiki《ROS2 与 FishBot》§20；具体运行事实留本计划。
