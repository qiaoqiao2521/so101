# SO101 产品化进度

## 2026-10-24 — M1a 实施中：原物理待验

- 完成可复跑 FK/IK/保守碰撞离线探针及编译 frame 核对。11 个区内／边界／区外点，9 个通过；X±20mm 的不同拒绝原样保留，Y±20mm 进入下一轮原物理候选。产物 `experiments/colab-twin/output/workspace-m1a-20261024/report.json` 被 Git 忽略。
- 控制器新增可选静态目标区域，原默认、网页 ±10mm、碰撞／244／TTL／预算不变。开发 profile 复用原执行、原评分和 StationVideo，每例独立 UUID，保留原失败。
- 根独立实跑：7 项空间探针检查、69 项控制器／原 Station／原汇总检查、4 项开发入口检查通过；其中开发入口 mock 物理，不计抓放成功。原控制器检查一度因实验 venv 缺 cv2 导入失败，系统 cv2 也有 NumPy ABI 冲突；停止该分支，仅补隔离 venv 的匹配包后原检查通过，未降级已有依赖。
- 下一运行：Kaggle 单 VM 串行四例，主工位 center→Y+20mm，第二已有工位 Y−20mm→center。复用原 bootstrap 与串行进程 wall/CPU 记录，原每回合 90sim/120wall；不是性能 A/B，不切默认，不开放网页新区。原云 leaf 任务已确认 COMPLETE，无重复启动。
- 当前新四例原物理状态 `not_run`，50Hz、20+20、行为树、配方与同世界卸货均未新增验收。源码固定推送后才发起，整组终态前不再修改或提交运行源码。

## 2026-10-24 — D0 计划完成，实施未开始

用户请求：将工作区扩展、恢复技能、快慢环、工艺寻优、车臂配方协作写为 SpecMesh。根 Codex 与三个内部 GPT 工作者分别核运动学、周期／seed、配方／FishBot 所有权，根串行整合。

### 已完成

- 建立 [task_plan.md](task_plan.md) 和 [findings.md](findings.md)，列明阶段、原入口、验收、回退与缺证项。
- 修正前提：±10mm 是输入边界；IK 已松弛完整姿态；进程首次 seed、transport/separation worker 已存在。
- 保留现状：F2ce 两工位 4/4 原物理通过、性能不一致未采用；F2cf 148 拍 >20ms，完整 50Hz 未过。未改历史判定。
- 明确六技能复用原执行器、配方复用 Physics/bridge；5186 已由 FishBot runtime 提供。Mint 不改，任意编排／配方交换／连续卸货未实现。
- 算法工厂转为有证据的性能支线，无新瓶颈证据时不追加低层试验。默认保持 `loaded_jaw_preload.py`。

### 阶段状态

| 阶段 | 状态 | 尚缺证据 |
| --- | --- | --- |
| D0 前提／计划 | complete | 只完成文档，不代表功能通过。 |
| M1a 工作区 | planned | 坐标/FK、IK 区内外、定位遮挡、完整抓放。 |
| M1b 快慢交接 | planned | 全认证保留的交接及完整周期实测。 |
| M2 技能／恢复 | planned | 取消、失败保留、可认证撤退、物理恢复。 |
| M3 冻结面板 | not_run | 独立 20 正常＋20 扰动及完整回读。 |
| M4 配方／卸货 | planned | 往返、同世界两货物、取消／库存交接。 |
| M5 寻优面板 | planned | 稳定基线、可重复改善、采用／撤销。 |

### 下一实施入口

Owner：根 Codex。先读 `station_executor.py:170`、`grasp_episode.py:114`、`visual_grasp_controller.py:334` 和模型工具轴，形成 **M1a 坐标合同与只读工作区筛选**。先比原 IK，不直接删除 ±10mm 校验，不继续 SAT 微优化。局部通过后选区内外点，经原 `evaluate_station.py`／`run_physical_episode` 做原物理。

M1b 复用 F2cf 叶段报告定位剩余同步责任。M4 配方草案可独立进行；同世界实施回源 FishBot 连续计划，不修改其在途任务。共享仿真先核进程；如接 Kaggle，单列机器与负载。

### 文档验收与知识收尾

本轮仅做定向核查和文档；未启动仿真、训练、云任务、服务或实体动作。提交前只验变更范围、链接、状态一致性和 diff。原成绩均来自 F2 记录，无新增物理通过宣称。

文档检查：新三文件与研究索引共 27 个本地链接目标存在，`git diff --check` 通过；独立只读审查未发现技能／旧裁判、同世界／取消或阶段状态的实质阻塞。源码与评测产物未变。

跨仓索引已写入研究根 `PROJECT.md`。初查时该文件混有空地臂／无人机在途计划，未将其他 owner 的改动并入 SO101 提交。随后独立读回：研究根 `9cae17a` 已整合该索引，工作树干净；本仓计划 `6de1206` 已推送，GitHub API 与 `ls-remote` 均回读相同提交。跨仓索引 pending 已解除，研究根无远端，本地提交不冒充云端发布。

Knowledge=already_covered：采用 Wiki《ROS2 与 FishBot》第 20 节“动作成功、交接成立和候选晋级分别验证”。没有新运行结论，不改在途知识页。旧 F2cf 插桩经验回写的 pending 保持原 owner，本次状态不冒充其已完成。
