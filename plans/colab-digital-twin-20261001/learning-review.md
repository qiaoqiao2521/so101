# SO101 有限资源仿真学习会审

日期：2026-10-01。冻结基线：`4489c71a3ec3152258063a0a0fad015363398c90`。本轮范围为三工具实际咨询、引用核验和接续方案；没有安装训练环境、训练模型或分配云端 GPU。

## 用户目标与历史定位

继续同一台 SO101 从臂，机械臂当前不可用，本机 RTX 3050 Laptop 只有 4096 MiB 显存。目标是 MuJoCo 仿真、自动示范、扰动后恢复、训练、纯策略仿真闭环；WASD 排除训练数据源，Isaac 的渲染负担不作为当前前置条件。

TraceMesh 找回原会话 `codex:01a0f3c6-1945-70c0-9fb8-e3566997bb62`，标题为“检索 ARM101 机械臂设计对话”。旧 CLI handoff 是 2 MiB 前缀且被截断，不能充当最新完整需求；随后通过 Codex app 的定点读取核对用户消息：`01a0f655-1a19-7b83-8628-f12c544d239d`（MuJoCo、恢复、无 WASD）、`01a0f655-aeb8-7fb1-bd85-d21257d7a243`（AGY/CODEX/ZCODE、引用）。只保存选中消息，不复制全对话。

## 实际讨论身份和结果

当前根 Codex 先写独立初判，之后才读取其他工具回复。AGY 与 ZCODE 通过现有本机原生 CLI 调用，使用给定的冻结源码和官方资料摘要；它们没有独立运行 SO101 实验。辅助证据核验者不冒充第四个讨论者。

| 参与者 | 第一轮判断 | 真实执行状态 |
| --- | --- | --- |
| Codex | 先状态闭环，MLP 可作诊断；正式模型优先复用 ACT，核实无图像输入与实际内存 | 当前根会话；独立初判在查看另两方观点之前冻结 |
| AGY | 首轮选择状态 MLP；看到官方无图像 ACT 与 imitation 依赖证据后，修订为小配置状态 ACT，MLP 作诊断 | 会话 `98c3a648-4c87-4628-b6c1-a47f86dc4c17`；首轮150秒内部超时部分正文；唯一定向复核14.276秒完整返回，无模型工具调用。AGY底层模型名未由CLI给出 |
| ZCODE | 保留先状态 MLP-BC、后无图像 ACT 的顺序；先验专家恢复，评估禁专家兜底 | 首次180秒无正文；唯一短提示补取131.594秒完整返回，实际模型 `builtin:bigmodel-coding-plan/GLM-5.3-Flash`，session `sess_ede6392b-eabb-4671-ba24-38c36921f063`；0工具事件 |

三工具已实际参与。首轮为独立判断，第二轮仅请 AGY 定向复核“成熟 MLP-BC 与无图像小配置 ACT 谁先进入本机试验”。ZCODE 没有被要求附和 AGY 的修订，保留 MLP 优先的分歧；不声称三方一致。

原始提示、CLI 回复、原生会话定位、哈希和超时记录只保存在被忽略的 `local-documents/decision-consultation-20261001/`。AGY原生步骤1/4由TraceMesh定点读回；首轮仍语义不完整，第二轮正文完整。ZCODE成功请求报告28063 tokens，首轮取消与AGY的完整可归属用量未知，不能将28063当总成本。超时限制不等于严格 Token 或费用封顶。Paperclip 调度、恢复没有在这次直接调用中验收。

## 当前建议与保留分歧

根 Codex 建议 **同步示范与专家恢复 → 小配置无图像 ACT → 纯策略抓放 → 单相机视觉 ACT**。理由是官方状态分支与后续视觉路线可以复用同一学习框架；小 MLP 保留为连通性诊断候选，暂不另引入整套 imitation 环境。[O1][O2][O4] 这是工程取舍，不是 ACT 在本任务上性能更好的实测结论，也没有宣布 MLP 不能成为实际策略。

ZCODE 的“MLP先打通管线”仍是合理反对意见。如果 ACT 的独立环境/最小反传验证失败，或成本明显超过既有资源，再选择薄 MLP；反之先继续官方 ACT。每个候选先接受实际资源检验，不依据多数表决认定可行。AGY提出20ms推理边界，ZCODE提出3.5GB显存与70%专家恢复率，均属建议值。本项目离线仿真可以等待推理，墙钟时间超过20ms不自动等同于物理控制周期失效；具体界限应在实验前定义，不能伪装为已通过或通用标准。

## 已核实的事实

1. 正常固定场景完成了自由物体接触抓取、绕障搬运、释放和落定；这是规划专家与位置伺服的结果。搬运路线仍按固定坐标构造，没有从任意偏离状态恢复的入口。[S1][S2]
2. `trajectory.json` 只保存物体、接触和有效性诊断，没有保存关节 `qpos/qvel` 或控制 `ctrl`。诊断每20ms、视频每40ms，视频没有统一训练帧索引。[S1]
3. LeRobot ACT 支持 `observation.environment_state` 无图像输入，有图像特征时才创建视觉 backbone。网络尺寸与动作块长度可配置；这证明可选路线存在，不证明本机4GB可训练。[O1][O2]
4. 成熟 MLP-BC 的具体入口是 `imitation.algorithms.bc.BC`，默认小 MLP；其整包还依赖 Gymnasium、SB3、seals、Sacred 等。不能把参数少直接等同于环境一定简单。[O3][O4]
5. DART 在专家执行中引入扰动并让专家纠正，还校准扰动分布；DAgger 聚合学习策略实际访问状态上的专家标签。固定 reset 随机化、离线加噪、受启发的恢复采集、完整复现算法应分别说明。[O5][O6]
6. 原仿真依赖环境没有 Torch、LeRobot、h5py、pyarrow、safetensors。训练依赖应在独立环境预检，保留已有 MuJoCo3.3.7/Mink/OMPL 环境。当前4GB空闲显存约3078MiB，仅是当时读数。

AGY 首轮“数分钟训练”“视觉 ACT 极高概率 OOM”“SB3/CleanRL 自带成熟 BC”缺少本机测量或具体实现出处，不采用。当前 `ctrl` 是绝对关节位置目标；增量动作若被选择必须有明确转换，不能混称。

## 训练数据与恢复约定（待实现）

先定义一个固定控制周期，确保专家与策略评估一致；物理步保留2ms。必须在下发动作前记录 `observation_t`，再执行一个控制周期，记录 `observation_t+1`。不能拿事后物体诊断配事前控制作为训练样本。

| 字段 | 内容与边界 |
| --- | --- |
| `observation.state` | 6维关节位置及需要的速度；明确 rad / rad/s 和固定关节顺序 |
| `observation.environment_state` | 当下物体姿态、目标和障碍几何等仿真真值；特权输入须明确标记，归一化配置需核验 |
| `expert_action` | 专家根据当前实际状态给出的6维绝对关节位置目标，含夹爪 |
| `executed_action` | 实际执行目标；若有动作扰动，与专家标签分开保存，避免学习扰动本身 |
| 时间与索引 | episode ID、样本 ID、控制周期、时刻、随机种子、场景/模型配置；RGB接入时同拍对齐 |
| 诊断与验收 | 接触、失败原因、stage、终止状态；保留用于筛选，但 stage/参考路径/全局时钟不交给策略 |

首轮仅开展有界 reset 扰动和无接触接近段扰动。后者必须真实执行偏移，再从实际状态重新检查、求解、执行恢复；不能仅重置后跑原路线便称为恢复。夹持丢失时保存失败并停止，当前没有重新抓取专家，不能承诺搬运中任意恢复。正示范、失败、专家标签无法取得的样本分别标识，不静默丢失失败分母。

动作扰动的时序须单独校验：`obs_t → 执行 u_t → obs_t+1 → 查询专家纠正 a*_t+1`，训练配对为新状态与其专家纠正，实际扰动指令另外保存。只增加这一记录方式还没有复现 DART 的扰动分布优化。

状态观测是否足够区分闭爪等待、抬升、释放等相似状态尚未验证。历史窗口、接触观测或动作块可作为解决候选；禁止用专家阶段标签掩盖这个问题。按完整回合、布局和随机种子划分训练/验证/测试；同回合相邻帧不能跨划分。

## 接续顺序和验收

1. **数据与专家门槛**：补 `reset/observe/step` 薄接口及同步采集；先保留原正常抓放通过，再验证预声明的扰动与恢复正反例。报告所有尝试、成功、失败和无专家标签数量。
2. **资源门槛**：一个独立环境做导入、一个小 batch 的 forward/backward/optimizer step、保存重载和一次推理；记录依赖、参数量、内存和用时。达到实际资源门槛后再启动限步训练，不直接长训。
3. **策略门槛**：模型独立生成动作并完成 MuJoCo 回合；测试不调用 IK/OMPL/专家生成动作。限位/碰撞停止器可以保留，但介入按失败计。复用实际夹持、抬升、蓝盘支撑、释放与稳定持续时间标准。[S2]

分别报告正常任务成功率、预声明扰动恢复率、碰撞/停止率以及失败视频；不要用训练 loss、专家成功或退出0替代策略成功。首次回合数量和成功目标属于项目实验设置，应运行前固定；本轮没有制造“20/20模型成功”的结果。

## 引用

- [S1：固定 SO101 抓放采样与执行源码](https://github.com/qiaoqiao2521/so101/blob/4489c71a3ec3152258063a0a0fad015363398c90/experiments/colab-twin/grasp_episode.py#L185-L257)
- [S2：固定 SO101 搬运路线与放置验收](https://github.com/qiaoqiao2521/so101/blob/4489c71a3ec3152258063a0a0fad015363398c90/experiments/colab-twin/placement.py#L44-L83)
- [O1：LeRobot ACT 固定配置](https://github.com/huggingface/lerobot/blob/e0d50211ef236143ae867228662b7dfaba554f02/src/lerobot/policies/act/configuration_act.py)
- [O2：ACT 无图像模型分支](https://github.com/huggingface/lerobot/blob/e0d50211ef236143ae867228662b7dfaba554f02/src/lerobot/policies/act/modeling_act.py#L333-L413)
- [O3：imitation BC 官方文档](https://imitation.readthedocs.io/en/latest/algorithms/bc.html)
- [O4：imitation 固定版本依赖](https://github.com/HumanCompatibleAI/imitation/blob/e5ef18806c449ca47153b494a02471c5e2ae3a14/setup.py)
- [O5：DART 原论文正式来源](https://proceedings.mlr.press/v78/laskey17a.html)
- [O6：DAgger 原论文正式来源](https://proceedings.mlr.press/v15/ross11a.html)
- [O7：MuJoCo3.3.7 防滑设置](https://mujoco.readthedocs.io/en/3.3.7/modeling.html#preventing-slip)
- [O8：LeRobot 仿真采集→训练→评估教程](https://huggingface.co/docs/lerobot/main/en/il_sim)（Panda示例，不是本项目SO101验收）。

本方案延续 Obsidian `Wiki/自动化开发范式与智能体协作.md` 的“按当前任务选择验收依据”：工具回复证明意见来源，源码证明支持分支，实跑才能证明本机模型行为。接触垫、摩擦和 Noslip 仍为未标定假设，仿真学习结果不等于真实机械臂迁移。[O7]
