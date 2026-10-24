# M1a 第一轮：两个范围外点完成原完整抓放

日期：2026-10-24。运行源码 `0ef406820ad3d4a8457909d148f249728ab73324`。原默认 `loaded_jaw_preload.py`，原 IK、评分、碰撞阈值、244 点及 90sim/120wall 不变。未加径向 yaw 投影、未训练模型。

## 结果与适用范围

在原固定红盘内，Y+20mm 和 Y−20mm 两个点完成抓起、搬运、放稳、释放、脱离、回位。另两个中心点对照也通过。它证明原 ±10mm 输入范围外存在可用点；不证明整个 ±20mm 矩形、连续扇区或 ±150mm 已可用。网页与普通 Station 准入仍保持原范围，开发入口明确 `development_only/not_admitted`。

| 案例 | 物体 XY / 目标盘 XY（m） | 原裁判 | sim（s） | 进程 wall / CPU（s） | 完整周期 >20ms |
| --- | --- | --- | --- | --- | --- |
| center_primary | .24,−.13 / .24,.14 | pass | 76.68 | 47.987 / 57.066 | 68 / 3834 |
| outside_y_plus20 | .24,−.11 / .24,.14 | pass | 74.74 | 45.980 / 55.064 | 52 / 3737 |
| outside_y_minus20_secondary | .24,−.15 / .20,.20 | pass | 82.26 | 51.284 / 61.337 | 65 / 4113 |
| center_secondary | .24,−.13 / .20,.20 | pass | 79.78 | 48.088 / 58.080 | 79 / 3989 |

这些是不同任务的功能验收，不是提速 A/B。不能从耗时差推导算法收益。完整周期 P95 依次 15.466/14.553/15.739/15.243ms，max 42.800/45.482/134.536/128.312ms，**完整 50Hz 未通过**。

## 独立回读

- 四例原 report 的 grasp/place/controller_done 均为 true；无安全停机、无障碍接触，原始轨迹 arm_valid/finite 全部成立。
- 物体均为自由物体，weld=0、mocap=0。planned/measured 闭爪各 244/244 状态、原阈值不变。
- 两个 worker 均 consumed、joined、owned_ack，launch_unknown/cleanup_unconfirmed 均 false。
- 持物 32.90/31.42/37.42/35.58s，最终静稳 7.54/7.54/7.50/7.50s。释放后 XY 最大漂移约 0.2114/0.1748/0.1699/0.1722mm，脱离后峰值力均 0N。
- 末态在目标盘支撑且 released_detached；回位五轴最大差约 0.000101–0.000103rad。ffprobe 独立解码帧数 480/468/515/499，与 capture/encoded 完全一致。
- 四个 run ID 依次为 `14d5f105-92ea-44e7-90bb-f42ced145a27`、`fdb4ff25-df68-4eb2-8983-a766c6c8d244`、`cef4a14b-ad60-4165-98e2-26a7fe30c5b7`、`d2ed9746-9bdb-4b1e-b11d-617cb54c6032`。

## 相机与离线边界

复用原 `run_p0` 渲染：中心、Y±20mm 三个正例定位通过，误差依次 0.616511/0.421178/0.349623mm；本 M1 前置面板声明 1mm 条件，不改原抓放裁判。missing、half_occluded、fully_occluded、two_candidates 四个负例均被拒绝。它是固定仿真相机核验，不是实体标定，也没有证明任意旋转目标。

本地 MuJoCo3.3.7 与云 MuJoCo3.15 的原 IK/保守证书筛选均为 11 点中 9 点通过。X−20mm 下探的证书下界约 0.880489mm，不能认证原 1mm 净距；X＋20mm 接近／抬升原 IK 失败。两者未被送入盲目完整回合，保留为后续定位问题的证据。

## 复跑与原件

```bash
python3 experiments/colab-twin/probe_workcell_workspace.py \
  --source workspaces/so101_ws/src/so101_mujoco/models/so101.xml --output workspace-screen.json
python3 experiments/colab-twin/run_workspace_case.py \
  --case outside_y_plus20 --output-dir experiments/colab-twin/output/workspace-replay
```

[profile](../../experiments/colab-twin/scenarios/workspace-m1a.json)可列出四例。Kaggle 原入口：[SO101 Workspace M1a](https://www.kaggle.com/code/muqiaoqiao/so101-workspace-m1a-20261024)，本轮为版本1；CLI 按 `muqiaoqiao/so101-workspace-m1a-20261024/1` 回收实际版本。

本机原件位于 `experiments/colab-twin/output/workspace-m1a-20261024/kaggle-v1/unpacked/so101-evidence/`：`cloud-run.json`、`runtime.json`、`workspace-screen.json`、`workspace-localization/report.json`、`workspace-pilot/*/pair-process-results.json`、各 UUID 原 report/trajectory/timing/release/video，以及 `independent-readback.json`。这些运行产物被 Git 忽略。

来源与收尾：原 Kaggle bootstrap、依赖、EGL 适配与串行进程测量复用既有 round100；内部 GPT 提供薄参数、探针、开发入口及读回，根实际运行和独立验收。私有 cache `round101-workspace-m1a` 保留生成器、精确云脚本和 reader。原 TGZ 已完整回收并解包；停止了继续重复下载同批 loose 文件的本机 CLI，未中断云评测。云版本原生 COMPLETE，四例终态；没有实体动作、没有新增定时器、没有向其他聊天发送消息。

## 接续

M1a 首切片完成，整体工作区仍在扩展中。下一项先分离 X 方向的 IK 残差与盘壁净距失败，决定是否适配姿态／初值或工位布局。仅对证据充分的点位或包络准备产品准入；不把此次 4/4 当作冻结 20+20、恢复能力或完整 50Hz 通过。
