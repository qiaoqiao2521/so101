# X 中点复用到第二放置工位

日期：2026-10-28。承接[原网页中点结果](m1a-x-web-midpoint-results.md)，原执行源码固定 `bef4ba45d24d70db568734187ca6ae453763c65f`。本轮只验证新放置请求，没有修改控制器、IK、评分器或默认策略。

## 新增可编辑配置

- [左 X−15.5mm，第二放置工位](../../experiments/colab-twin/scenarios/workspace-station/fixed-x-minus15p5-place200-200.json)。
- [右 X＋15.5mm，第二放置工位](../../experiments/colab-twin/scenarios/workspace-station/fixed-x-plus15p5-place200-200.json)。

与上轮左右文档相比，业务数据只把 `place.position` 从 `(.24,.14,0)` 改为 `(.20,.20,0)m`，名称／说明同步。红盘、cube、程序不变；左仍为60mm／.5rad，右仍为54mm／.35rad。`release/clear` 保持相对蓝盘偏移，解析后的世界坐标分别为 `(.20,.20,.03)`、`(.20,.20,.10)m`。

中心回归复用[既有第二放置工位](../../experiments/colab-twin/scenarios/factory-loading/layout-place-200-200-0mm.json)，没有新增中心配方。该文档的cube挂在pick下，以解析后的世界坐标比较，不要求JSON父节点形式与中点文档相同。

## 原物理三例

复用原Kaggle引导及串行runner，三次分别调用原 `evaluate_station.py --station ... --output-dir ... --timing`。本机有Blender工作，没有启动本地仿真。Kaggle `muqiaoqiao/so101-x-second-place-20261028/1` 已终态 COMPLETE；上传源码回读相同。没有新增调度器、网页包装或GNU time依赖。

| 项目 | 左中点 | 右中点 | 原中心回归 |
| --- | --- | --- | --- |
| 原UUID | `b76fe921-2cf3-40b9-83d2-0554a6fd8e6d` | `3412c142-38b7-450e-b6a6-9c412f894d70` | `8c5ad216-6b2b-41b3-a10d-726d014bcba4` |
| 原裁决／进程exit | pass／0 | pass／0 | pass／0 |
| sim s | 78.44 | 81.62 | 79.74 |
| episode wall s | 59.653595 | 60.211334 | 58.335462 |
| 实际process wall／CPU s | 60.853353／71.938389 | 61.424708／73.026830 | 59.587473／70.730162 |
| 原OMPL搜索／含后处理 s | .182978／.400814 | .185104／.388592 | .179939／.379911 |
| 运输搜索／worker wall s | 3.233755／3.323443 | 3.219273／3.300406 | 3.095728／3.179201 |
| 脱离worker wall s | 1.569803 | 1.694369 | 1.656602 |
| 实际最大抬升 mm | 40.881472 | 35.022283 | 40.889632 |
| 实际持物／静稳 s | 33.74／7.50 | 36.94／7.50 | 35.56／7.50 |
| 释放XY漂移 mm | .165289 | .194294 | .172127 |
| 脱离后峰值力 N | 0 | 0 | 0 |
| 夹爪完整扫掠 | planned/measured各244 | preclose/planned/measured各246 | planned/measured各244 |
| 实视频帧 | 491 | 511 | 499 |

三例均完成原抓取、搬运、放稳、释放、脱离和回位；安全停机／障碍接触0，自由物体、weld0／mocap0。回位q6最大误差约 `.101346mrad`，最大速度小于 `7.64e-8rad/s`。已启动运输与脱离worker均consumed／owned_ack／joined，无未知清理；串行runner wait回收三个原进程。

独立126项检查无失败：实际／planning共6份XML核实全部蓝盘几何只平移 `(-.04,+.06,0)m`，红盘全部几何、robot、option、actuator不变。输入原件与解析结果吻合，真实RGB进入原冻结交接，原monitor／skill逐行重放一致，安全坏行0，录像实际解码完整。根已查看左右final图，绿块位于新的蓝盘内。

左右释放审计精确重放；中心仅 `max_xy_drift_m` 存在末位差：原 `.00017212737510896898`，重放 `.00017212737510896895`，差约 `2.71e-20m`。原值、差异和唯一unknown均保留；逐2ms detached旗标及原判定一致，不写成全部浮点精确相同。三例 `sitecustomize: No module named 'wrapt'` 非致命启动警告也保留，不为清日志重跑。

## 完整周期仍未达50Hz

| 原完整周期 | 左中点 | 右中点 | 中心 |
| --- | ---: | ---: | ---: |
| 拍数 | 3922 | 4081 | 3987 |
| 中断拍 | 0 | 0 | 0 |
| P95／P99 ms | 20.388／31.613 | 19.687／31.540 | 19.175／29.045 |
| 最大 ms | 172.635 | 160.545 | 159.744 |
| 超过20ms拍数 | 210 | 193 | 184 |

共11990完整拍，与三个原report.steps一致；每拍物理时间推进20ms，计入全部原循环分段，没有去掉冷启动或只取完整子集。三例完整50Hz均false，P95低于20ms不能代替零违约。它是新工位能力验证，不是算法性能A/B；不能将本轮CLI wall与上轮浏览器wall相减，也不与旧轮累计提速。

## 已有数据补充的定位事实

并行只读核R134原XML／initial_qpos，确认六hinge后接目标freejoint；相对实际初态目标的定位误差为左 `.631417483mm`、右 `.524660981mm`，与相对声明位置误差近似。初态XY位移仅约 `2.56e-7mm`，不能解释半毫米量级误差。

首次审查遗漏了已有trajectory物体真值，曾误写“冻结后没有同步序列”；根要求定点复核后已撤回。R134左右实际3758／3916条20ms记录存在，除首帧使用原initial报告外，所有视觉时间及两次handover均可精确匹配。冻结到首次正指尖力前，采样XY漂移最大约 `8.78e-14／5.55e-14mm`，支持这两次名义回合目标静止；不证明拍间瞬态、持续移动目标或旋转鲁棒性。没有重跑名义回合取已有证据。

定位输出的约1.7mm工程量来自像素及声明顶面高度容差，不是统计置信界；handover中的2mm先验、相机误差与原1mm几何证书是不同量，不能直接相加减来放行。下一步先固定实际RGB中心、原初态q6及显式工程扰动集，复用原IK／全部285对／完整扫掠作离散敏感性筛查，保留原种子／分支／首拒绝；不据几个样点宣称连续圆盘安全。物体真值只用于离线评价。

## 复跑、原件与收尾

```bash
python experiments/colab-twin/evaluate_station.py \
  --station experiments/colab-twin/scenarios/workspace-station/fixed-x-plus15p5-place200-200.json \
  --output-dir experiments/colab-twin/output/x-second-place-replay --timing
```

左例替换为minus文档，中心用上文既有工位文档。两新文件保持原robot-station格式，可导入原网页；本轮实际验收是原CLI，第二工位的新浏览器／HTTP运行未另测。每次仍重新定位、规划和认证，不继承旧证书。

原件在 `experiments/colab-twin/output/x-second-place-20261028/kaggle-v1/so101-evidence.tgz`；根 `root-readback.json`、左右final图、`right-second-place-grasp-place.mp4` 保留。独立报告gzip逐字节回读后释放49,152已分配字节，恢复用 `gzip -dc independent-readback.json.gz > independent-readback.json`。TGZ直接读取，没有展开副本或临时帧；只有一份当前视频供查看，没有本轮云任务仍运行。私有构建／reader及定位诊断、撤回记录在 `~/.cache/ros2-factory/codebuddy-so101-20261021/round135-x-second-place/`。

Next：按上述实际输入做有界离散敏感性筛查，再决定物理临界方向；普通±10mm、连续域、20＋20及默认不改。M1b grid／FK／pending-hold覆盖与M2 Carry网页接续仍独立待办。Knowledge=already_covered，沿用Wiki《ROS2 与 FishBot》§20；具体新事实留本计划。
