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

## 会审时的训练数据与恢复约定

本节保留会审时的约定；当前已实现的数据字段、守卫版纠正和训练门槛见[运行契约](../../experiments/colab-twin/LEARNING.md)及末尾实测更新，不能将当时“待实现”解释为当前仍缺少采集器。

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

## 用户后续收敛与实测实现

用户确认将保留分歧收敛为相同数据的ACT/MLP资源双探针，不引入独立MLP训练框架。已实现[分层入口](../../experiments/colab-twin/run_learning.py)与[运行契约](../../experiments/colab-twin/LEARNING.md)，正常/物理起点扰动恢复/空夹失败档案保留。两候选资源通过，官方小配置ACT进入单轨迹限时训练；纯策略碰撞停机尚未通过，因此20+20和视觉保持not_run。此前“待预检”的记录属于会审当时的状态，最新验证以progress为准。

## 2026-10-01：AGY 对起步偏差与恢复采集的实际审核

审查对象为提交 `5c41ca0d28fba1f20609c84a72a8de6a9625c8b0`，基线 `16fb76e84495d517c35a79dba08687f4c5ffa4fc`。实际调用本机AGY CLI，使用既有默认模型；未用Codex子Agent代替AGY。AGY会话为 `11ef62ca-91ac-414d-b850-1a1b6225f170`。首轮240s print timeout返回空响应，虽然CLI报SUCCESS，也记为未完成；随后仅要求基于已读材料收束结论，24.563s返回完整意见，无追加工具调用。CLI同时提示禁用slash expansion时plan标志不生效，故只读性质以实际工具与文件核对为据。

通过TraceMesh选定会话阅读器核对，原生记录完整解码：23次run_command、19次view_file，42份工具结果均完成。工具实际读取本次diff、相关源码和指定产物，计算报告/档案哈希，并独立运行一次 `test_recovery_collection.py`：3项通过、0.092s。根Codex另行运行相同3项检查：通过、0.090s。原生最终正文与CLI响应逐字一致，审查时20份源码/文档SHA未变化。没有新训练或物理回合；150项全测与既有物理结果是此前产物，不是本次重跑。

AGY的审核判定：实现和数据记录边界通过本次审查，未发现确定的新伪标签、终点恢复或专家接管后门；纯学习策略完整抓放仍未通过。主要保留意见是接近末端与持物搬运恢复样本不足；全速度屏蔽候选失败不支持其作为默认修复；统计拟合集与权重训练集需要分别保留来源。

| 判断 | 可核对来源 | 根Codex的采用边界 |
| --- | --- | --- |
| 接近段恢复采集真实且标签隔离 | [前缀校验及物理注入](../../experiments/colab-twin/grasp_episode.py)、[真实档案检查](../../experiments/colab-twin/test_recovery_collection.py)；v5四档案600帧前缀排除，独立重放2372步误差0 | 证明这四条采集/重放成立，不能证明起步泛化充分 |
| 当前采集入口缺少持物纠正 | `grasp_episode.py:366`反应式控制仅approach；`:468-476`前缀要求无接触/抬升且最多5s；四v5源均为同一策略轨迹的不同前缀 | 采用覆盖不足的保留意见；已有完整后段专家示范，每条v5含1170帧transport，缺的是从实际载物偏差状态出发的专门纠正 |
| 最强策略真实抓起但盘外释放 | `output/policy-recovery-v5-qvel-masked-chunk16-nearest-20261001/report.json`：grasp=true、hold17.56s、place=false；release-probe记录第1760拍/35.2s新chunk开爪，35.4s丢块 | S7d保持未完成；专家重放、测试及局部输入替换均不代替任务验收 |
| 速度与归一化来源仍需辨析 | `output/v5-qvel-masked-physical-audit-20261001/release-probe.json`及`support-clamp-probe.json`；`output/policy-recovery-v5-qvel-masked-origin-verified-20261001/report.json` | 输入敏感性不是唯一原因；四份统计源为nominal/startup-plus/startup-minus/approach，不能统称四份名义数据 |

表内 `output/` 路径均相对 `experiments/colab-twin/`，数据、权重及原始审核继续Git忽略。重要证据SHA：当前gate报告 `87af27ca8770117c7ed94eb9cc6c3920d986de02c684ccb234152f40bc2bd1e8`；最强候选报告 `f1a7236638fc2b3903e014edc2edd8938ab9a35407690cf34311da3f3f54cfa9`；独立重放报告 `848502e34d6b963732ce788b57fa5cffaf292ea7d0187a4421c0f94b3e2ab7a6`。完整审核响应JSON SHA `01fe03ad190f894a50c9d64c10cda07f5a29f4f073f9752c5ae80143d6e8be45`，原生公开块读回SHA `09a066d62de3e41a44600ff7e26444e6a746f7c0c69fe9b680b0a587c73c7735`。本地原文与调用审计保存在 `local-documents/agent-consultations/20261001-agy-startup-review/`。

保留分歧：AGY将起步覆盖称为“充分”，当前四条同源前缀与一次固定场景不能支持此泛化结论，突破起步也不能单独归功于新增数据。全mask失败只说明该候选失败，不能单独归因为丢失动量感知；归一化输入置零与原始物体速度置零也不是同一干预。AGY建议在第1500～1760拍才启用EMA/软饱和，本轮不采用：时间门控超出现行策略输入契约，且某一种滤波失败不能证伪所有速度相关原因。精确范围clip只被离线开爪反例否定，未做物理rollout。重新fit八档案统计可成为独立候选，但需配套重新训练/验证，不能直接换冻结权重的输入与动作解码尺度。

本轮只完成审核与记录，未实施上述候选。根Codex接续的最短检查保持为：先核对接近末端/持物偏离状态与现有正例的覆盖，再验证一条真实专家纠正能否完成物理抓放和raw64独立重放；通过后才有界训练并重过相同纯策略单回合。20+20、视觉、Colab及实体均未新增。

## 2026-10-02：审核意见后的实际接续

接近末端、持物与低位松爪覆盖已按实际状态补采。七条guarded正例为450拍接近、1700/1756拍持物、分类策略1800拍持物、v7组合900拍慢抬持物、v8组合2500拍蓝盘边缘持物及v10组合2517拍低位释放，共18903原始转换/7280有效专家标签/11623无效前缀；合并原八条为15条、25504有效/12226无效、37730原始帧。每条均完成专家抓放且独立raw64回放state/env/time差0，报告明确`learned_policy_evaluated=false`。[七条来源与回放证据](findings.md#2026-10-02-接近末端持物纠正与五轴学习)、[离线采集器](../../experiments/colab-twin/collect_policy_recovery.py)、[载物检查](../../experiments/colab-twin/placement.py)。v11沿用冻结v10的14档案五轴ACT，仅夹爪头消费15档案。最新固定训练初态纯策略单回合1/1通过，20+20/视觉未运行；不能把同源前缀或这一单回合称为充分的泛化证据。

v6全模型ACT11.42s碰料盘底、jaw输出行37.88s掉物、独立学习夹爪38.02s撞障、MLP12.94s碰料盘底，全部保留失败。前两者使用旧admission/forward三条，后两者使用前三条guarded；不是严格同数据消融，也不能把“持物更久”换算为完整抓放成功。[逐项报告和训练清单](../../experiments/colab-twin/LEARNING.md#当前实测)。

v7继续采用有界验证：确定性ACT的五轴非padding L1、12档案、lr1e-5、2721step/120.0169s，随后组合独立学习夹爪；未经监督的原ACT夹爪不得直接执行。[五轴训练](../../experiments/colab-twin/output/policy-correction-v7-arm-fit-20261002/report.json)、[夹爪训练](../../experiments/colab-twin/output/policy-correction-v7-decoupled-fit-20261002/report.json)、[梯度及默认行为检查](../../experiments/colab-twin/test_arm_only_training.py)。数据、损失、学习率和夹爪结构同时变化，无法独立归因；该组合也不能简称“原版ACT”。[201项检查55.101s通过](../../experiments/colab-twin/output/late-recovery-v7-final-tests-20261002.log)不等于抓放通过。

实际v7组合chunk16在22.54s腕限位停止（抓起/hold6.06s）、chunk8在11.82s料盘底碰撞（未抓起）、chunk1在90s超时（抓起/hold71.88s但未放置），同权重三项都0/1。[完整窗口诊断](../../experiments/colab-twin/LEARNING.md#当前实测)。限内目标不保证实际关节不越界，保持物体也不等于完成搬运放置；这些失败继续按原安全与任务标准计数。截至v7单回合仍未通过，之后根Codex按以下证据定向接续，没有提前开展20+20或视觉。

之后[冻结旧ACT并重学12条独立夹爪](../../experiments/colab-twin/output/policy-correction-v7-frozen-origin-classifier-single-20261002/report.json)也在21s掉物（hold2.66s）；不能把五轴微调认作所有失败的唯一原因。根Codex据[独立CPU900拍诊断](../../experiments/colab-twin/output/late-recovery-v7-held900-offline-diagnostic-20261002.json)选择安全持物刚成立后的慢抬边界补纠正：实际held1.52s、双指1.419/1.422N、距腕限约.1819rad。物体速度局部替换使离线预测重新靠近专家推进目标，只用于确定采集假设；真实新标签由[actual-state专家抓放](../../experiments/colab-twin/output/policy-correction-v7-held900-guarded-20261002/report.json)和[2362步raw64回放](../../experiments/colab-twin/output/policy-correction-v7-held900-guarded-replay-20261002/report.json)证明，非线上fix。

v8从v7五轴权重接续13档案、batch64/lr1e-5/120s上限；[arm实跑1504step/120.079s](../../experiments/colab-twin/output/policy-correction-v8-arm-fit-20261002/report.json)，allocated110.629MiB/reserved142MiB。[CPU学习夹爪6000step/7.898s](../../experiments/colab-twin/output/policy-correction-v8-decoupled-fit-20261002/report.json)后，[组合纯策略chunk16](../../experiments/colab-twin/output/policy-correction-v8-decoupled-single-20261002/report.json)抓起并持物60.42s，但89.72s蓝盘边缘.8471mm余量保护停止。末条有效物体位置(.20221084,.11643329,.02516980)m已在蓝盘范围，仍无盘底承托或释放；单回合0/1，不写通关。数据与batch同时变化，结果也无法独立归因新增纠正。

第2500拍实际持物边界的安全通道→盘心→降放纠正已[完成专家抓放](../../experiments/colab-twin/output/policy-correction-v8-held2500-guarded-20261002/report.json)并[3242步raw64回放差0](../../experiments/colab-twin/output/policy-correction-v8-held2500-guarded-replay-20261002/report.json)：742有效/2500invalid，准入持物31.94s、双指约1.45N、物体z=.045689m，安全检查保留。现正式纳入第14条，模板同步；v9从v8五轴权重接续14条、batch64/lr1e-5/120s上限，[数据清单](../../experiments/colab-twin/output/policy-correction-v9-training-datasets-20261002.json)与[参数](../../experiments/colab-twin/output/policy-correction-v9-arm-training-arguments-20261002.json)可核对。

[v9 arm仅73step/120.1525s、整体405.6682s](../../experiments/colab-twin/output/policy-correction-v9-arm-fit-20261002/report.json)，5倍关键抽样下4672次抽样/578关键次/4166不同观测起点，占25107有效chunk起点的16.593%；这不是动作标签覆盖。按seed0重建实际抽样并展开chunk16/间隙守卫，监督动作槽74384次含重复，目标源帧并集23501/25107=93.603%；新增742帧档案131起点/713目标。不能写成84%的标签未训练或凭73步唯一归因失败。[完整口径与源码](../../experiments/colab-twin/LEARNING.md#当前实测)。独立夹爪6000step/CPU9.234s覆盖全25107个观测起点，采样与arm独立。[组合纯策略](../../experiments/colab-twin/output/policy-correction-v9-decoupled-single-20261002/report.json)27.08s掉物、hold11.22s、无放置/安全停止，0/1，未通关。

[独立采样重建与策略审核](../../experiments/colab-twin/output/late-recovery-v9-policy-independent-audit-20261002.json)保存上述准确口径，未重跑训练或仿真；它来自Codex审核助手，不是AGY。

v10保持相同14数据和ACT架构，从v8 arm重新初始化，不继承v9的73步；batch64/lr1e-5/120s，[CPU诊断参数](../../experiments/colab-twin/output/policy-correction-v10-arm-training-arguments-20261002.json)保留。[arm实跑1201step/120.067s、整体144.551s](../../experiments/colab-twin/output/policy-correction-v10-arm-cpu-fit-20261002/report.json)，随后[夹爪CPU6000step/7.3647s](../../experiments/colab-twin/output/policy-correction-v10-decoupled-fit-20261002/report.json)。[最终组合纯策略](../../experiments/colab-twin/output/policy-correction-v10-decoupled-single-20261002/report.json)抓起/hold25.06s/未放置，完成52.20s后蓝盘边缘.936503mm低于1mm余量而保护停止，0/1。它是官方ACT五轴＋独立学习夹爪的组合诊断，不能写“官方完整ACT通关”。切CPU是有界吞吐检查，不是OOM或模型架构回退；单点频率读数及设备/步数/数值变化均不足以严格因果归因。

v10后[离线新夹爪预测](../../experiments/colab-twin/output/late-recovery-v10-release-cache-probe-20261002.json)在蓝盘内低位仍全闭爪，提示释放覆盖缺口；原held准入要求抬升≥25mm，无法采低位状态。按[保存诊断选择2517拍](../../experiments/colab-twin/output/late-recovery-v10-release-boundary-selection-20261002.json)，新离线release入口要求历史真实抓起、当前连续双指接触≥1s、完整蓝盘范围、无桌面/盘底承托、z在[.010,.0145)m、速度≤.05m/s及原安全边界。当前接触时钟独立计数、接触中断或支撑即重置，不用历史hold替代。真实前缀重执行后物体(.21463836,.14002259,.01447777)m、当前接触36.46s；首valid动作保持actual五轴q并开爪`.5`，跳过IK/运输，按原守卫承托、撤退、静稳。[397有效纠正专家成功](../../experiments/colab-twin/output/policy-correction-v10-release2517-guarded-20261002/report.json)及[2914步raw64差0](../../experiments/colab-twin/output/policy-correction-v10-release2517-guarded-replay-20261002/report.json)各自通过，2517前缀仍invalid。此离线专家规则未接入在线策略。

v11没有再训练五轴：固定v10 arm SHA `b92adf12f9482467aa927aff1c71e8c94ae2cba6ed878b7743678b52abab57e6`（14档案训练），仅按[15档案参数](../../experiments/colab-twin/output/policy-correction-v11-release-training-arguments-20261002.json)重训夹爪。[CPU6000step/7.1017s、整体9.9502s](../../experiments/colab-twin/output/policy-correction-v11-release-classifier-fit-20261002/report.json)，72个ACT状态tensor不变；base输入/动作归一化保持原四档案，夹爪额外统计只fit15份合格训练行。组合SHA `f50a14052b48ad1237024a63cebddec032686441be1149c33e4c8bc5d071a007`。

[v11纯策略chunk16](../../experiments/colab-twin/output/policy-correction-v11-release-single-20261002/report.json)完成1988周期/39.76仿真秒、hold23.10s、释放并蓝盘内静稳1s，无专家介入或安全停止，单回合1/1通过。观察只有state/env；nearest仅将分类器已经选择的`.0150000114/.5000000092`投影到训练标签`.015/.5`，最大约1.15e-8rad，不按几何/阶段/时钟查询专家动作。验收对象为官方ACT五轴＋独立学习夹爪＋固定执行适配器，不能称官方完整ACT或裸模型通关。初态来自训练nominal，只通过重复性门槛，20+20、扰动恢复率、视觉、Colab及实体标定仍无新增；新增标签与重训同时发生，不单独证明唯一因果。

此前201项全测的[8份产物绑定](../../experiments/colab-twin/output/late-recovery-v7-final-test-arguments-20261002.json)、[12训练集独立审核](../../experiments/colab-twin/output/late-recovery-v7-independent-audit-20261002.json)及后续[14总集数据审核](../../experiments/colab-twin/output/late-recovery-v9-data-audit-20261002.json)保留历史范围。release采集器新增源码后，[212项/41.991s、0 skip、exit0](../../experiments/colab-twin/output/late-recovery-v11-final-test-result-20261002.json)在当前源码通过，前后哈希一致；[本次参数](../../experiments/colab-twin/output/late-recovery-v11-final-test-arguments-20261002.json)绑定11份HDF5（四v5＋七guarded）及release2517回放，四份v4不在该artifact绑定内。不能把测试绑定写成15份或代替物理验收。全部旧失败保留。

[v11独立Codex审核](../../experiments/colab-twin/output/late-recovery-v11-independent-audit-20261002.json)39项全true，SHA `24e341d401479ad57c39a5b2a13609738ca70247b2e3d5dac02d315402f8f565`：独立重算1s真实支撑/松爪/静稳及完整物体蓝盘范围；核对72个ACT tensor不变、arm14/head15、原四归一化及15份夹爪统计误差0、前缀NaN/回放零误差、212源码和11档案绑定。审核仅只读源码/记录和离线算术，没有重跑模型或仿真。[同固定初态可见复跑](../../experiments/colab-twin/output/policy-correction-v11-release-visible-20261002/render-binding.json)也通过，9个NPZ字段数组及全部物理diagnostics与首次逐项完全一致；995帧视频只作可见复验，不能加入20+20或泛化成功率。

本轮新增检查与文档整理来自Codex助手，未发起新的AGY或ZCODE审核。上节AGY的实际会话`11ef62ca-91ac-414d-b850-1a1b6225f170`只审查其注明的旧提交和产物，不能延伸为对本轮release采集器、五轴损失或v7–v11模型的批准。原始报告、日志、HDF5、权重和咨询仍保存在Git忽略目录，仅交付源码与可追溯的结论。
