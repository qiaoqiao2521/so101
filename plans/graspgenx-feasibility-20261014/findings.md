# Findings：GraspGen-X 与 SO101

日期：2026-10-14，Asia/Shanghai。最初范围：当前文件、官方网页、公开源码与仓库元数据的只读核查。随后人类明确授权试模型，新增本地结果见末节；物理抓放与实体仍未执行。

## 官方证据与版本定位

官方源码当次 HEAD：`b9429097728cb1c430dd78b92edf17ba318aad03`，由 GitHub commits/main API 核对。模型元数据 revision：`7c834043c11a11417e31d6d5ea9355801e40a2c1`。夹爪数据仓库 revision：`19a03c00d19aeaf052d0f6801f0041982d676e8a`。这些是仓库元数据，不是已下载权重的完整性验证。

| 编号 | 一手来源 | 本轮核实范围 |
| --- | --- | --- |
| O1 | [官方说明](https://github.com/NVlabs/GraspGenX/blob/b9429097728cb1c430dd78b92edf17ba318aad03/README.md) | 部分物体点云或网格输入、新夹爪向导、首次导入自动取资产、默认混合规划器；端到端示例不是 SO101 证明 |
| O2 | [源码 LICENSE](https://github.com/NVlabs/GraspGenX/blob/b9429097728cb1c430dd78b92edf17ba318aad03/LICENSE) | 源码 Apache-2.0 |
| O3 | [模型目录](https://huggingface.co/adithyamurali/GraspGenXModel/tree/7c834043c11a11417e31d6d5ea9355801e40a2c1)、[模型卡](https://huggingface.co/adithyamurali/GraspGenXModel/blob/7c834043c11a11417e31d6d5ea9355801e40a2c1/README.md) | 公开非 gated 元数据；生成器 `release/gen/epoch_736.pth` 与评分器 `release/dis/epoch_1056.pth`、各自 config.yaml 条目存在；未取权重字节 |
| O4 | [NVIDIA Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/) | 模型卡采用该许可，不能归为源码 Apache-2.0；使用和分发前按许可保留相应条款/通知 |
| O5 | [夹爪数据仓库](https://huggingface.co/datasets/adithyamurali/gripper_descriptions/tree/19a03c00d19aeaf052d0f6801f0041982d676e8a) | 数据卡标 MIT、非 gated；元数据列出26个 config.json，无路径含 so100/so101 的条目 |
| O6 | [官方候选分派](https://github.com/NVlabs/GraspGenX/blob/b9429097728cb1c430dd78b92edf17ba318aad03/graspgenx/samplers/planner.py#L20) | 世界框架候选 `(K,4,4)`、评分 `(K,)` 和 `diff/obb` 标签；默认 GraspMoE 合并两分支；diffusion 路线仍使用评分器 |
| O7 | [官方夹爪读取](https://github.com/NVlabs/GraspGenX/blob/b9429097728cb1c430dd78b92edf17ba318aad03/graspgenx/x_grippers.py#L104)、[活动双指配置例](https://huggingface.co/datasets/adithyamurali/gripper_descriptions/blob/19a03c00d19aeaf052d0f6801f0041982d676e8a/gripper_descriptions/assets/x_grippers/arx_x5/config.json) | 配置含 open/close、fingertip、sweep_volume、links、standoff、bbox、symmetric、type；支持 revolute_2f 类型，但未验证 SO101 配置 |
| O8 | [依赖定义](https://github.com/NVlabs/GraspGenX/blob/b9429097728cb1c430dd78b92edf17ba318aad03/pyproject.toml) | 当前项目声明 Python≥3.10、Torch≥2.1且<2.7、NumPy1.26.4等；与已运行 SmolVLA 环境不能视为同一依赖契约 |
| O9 | [原论文](https://arxiv.org/abs/2606.00998v1) | 跨夹爪六维抓取及扫掠体条件表示的研究依据；论文结论不等于本地 SO101 结果 |

网页工具首次未能读取模型页，随后通过官方 README 链接及公开 Hugging Face API 核对。一次误将夹爪资产查询为 models 端点，收到401；实际资产是 datasets 类型，正确端点成功。不能将该401当作夹爪资产 gated 的证据。

## 输入、输出与夹爪适配边界

官方生成器接收物体几何，不是 RGB→语言指令→关节控制的完整策略。输出抓取位姿与评分不包含 SO101 五轴关节目标，也不直接定义其闭爪执行轨迹。点云入口仍需分割和可靠米制坐标。网格上界、仿真深度、学习深度与真实相机数据是不同证据，分别评价。

官方向导要求 URDF+meshes，标注开闭状态及扫掠体，约定 +Z 为接近轴、+X 为闭合方向。SO101 夹爪须使用自身固定指/活动指几何和运动学；原 `PINCH_POINT=[.006,0,-.094]` 属本地 gripper body 框架，不能直接作为官方抓取变换的位置部分。框架变换、非对称闭合轨迹和指尖/接触垫的一致性均待定。

26个官方 config.json 中没有找到 so100/so101 命名路径，只证明当次资产索引未发现相应命名条目，不能证明所有别名、外部贡献或零样本适配均不存在。官方跨夹爪支持提供适配入口，不保证本地夹爪有效。数据卡 MIT 声明不替代逐项网格/URDF 的第三方通知核对，该项留在未来资产准入。

源码 O7 缺少部分缓存时会使用占位值；不要将“导入成功”当成夹爪几何有效。未来准入需核对实际配置与推理使用字段，不把未消费的可选表示混同为硬依赖，也不接受占位碰撞几何代替完整检查。

默认 GraspMoE 包含几何 OBB 和 diffusion 候选，统一评分。对照必须保留候选来源和评分来源。固定抓取/纯 OBB/`--planner diffusion`/默认 GraspMoE 四组适用于分离工程收益；纯 OBB 的具体独立复用入口仍待核实，当前 CLI choices 只有 diffusion、graspmoe。

## 本地可复用资产与真实缺口

1. [当前 PROJECT](../../PROJECT.md) 与[主计划](../colab-digital-twin-20261001/task_plan.md)明确优先已有演示。新模型不是自动恢复训练、性能优化或云资源的理由。
2. [position_ik.py](../../experiments/colab-twin/position_ik.py#L104) 使用 `position_cost=1.0, orientation_cost=0.0`。成功返回只按平移误差判定。其源码还在每次迭代把未使用的旋转目标设成当前旋转。
3. [solve_pinch_ik](../../experiments/colab-twin/grasp_episode.py#L97) 则约束指间中心、竖直轴并偏好固定 wrist roll；它不是任意 SE(3) 抓取求解器。五个手臂关节加一个夹爪关节不等于六个可独立控制的手臂位姿自由度。
4. [joint_planner](../../experiments/colab-twin/joint_planner.py)、[visual_grasp_controller](../../experiments/colab-twin/visual_grasp_controller.py)、[released_object](../../experiments/colab-twin/released_object.py) 可复用关节路径、跟踪、开合扫掠、持物、释放、脱离与回位检查。原夹爪体积的完整覆盖不自动包含官方新框架或新增物体。
5. [placement](../../experiments/colab-twin/placement.py) 的载荷相对变换是假设查询；源码明确几何配置有效不证明实际接触和动态持物稳定。
6. [现成演示](../../experiments/pretrained-demo/README.md) 已有公开模型体验；其 Sawyer 目标范围成功不是 SO101、释放落定或统计成功率。这些能力仍分开验收。

## 现有门槛及可迁移范围

主要协议来源：[R3e protocol](../../experiments/colab-twin/output/visual-grasp-r3e-summary-20261009/protocol.json)。它针对已知直立绿色18×18×16mm方块、固定工位和标定俯视 RGB。属于既有协议，不能直接当作新增物体或点云管线的验收结果。

| 项目 | 当前来源及门槛 | 新计划边界 |
| --- | --- | --- |
| 输入位置 | protocol：P0 XY≤2mm，20正例+4缺失/遮挡/歧义负例 | 点云有效性和3D误差门需新增推导；不能等同姿态容差 |
| 手臂与载荷 | protocol/controller：1mm/0.2mm余量，完整 q6/jaw 与碰撞检查 | 原阈值保持；新几何覆盖集合另核对 |
| 抬升保持 | learning_env.py:71–77：≥25mm、两指各>0.02N、无支撑、持续≥1s | 原方块直接沿用；接触垫、摩擦、Noslip为仿真假设 |
| 释放落定 | learning_env.py:78–83、placement.py:118–138：盘内、有支撑、指力<0.02N、速度<2mm/s、≥1s；原中心z约10mm±2mm | 新形状支撑高度及整个物体在盘内的判据待定，不能套固定方块高度 |
| 脱离 | released_object.py:117–168：力0.02N、quiet0.2s、XY drift≤2mm | 继续验证清离、已释放物体避碰和回位 |
| 完整回合 | run_visual_grasp.py:319：monitor通过、controller done、release audit通过且扰动完整 | 部分抬起/末帧到位不算完成；原回位跟踪规则保持 |
| 时间 | protocol：物理2ms、控制20ms、单例90sim/120wall；累计null | 不取消单例边界；50Hz单独判定，资源适配门待定 |
| 开发与留出 | run_visual_grasp.py:398–414：开发全部成功且安全0；原P2为5正常+5扰动；P3为20正常全过、20扰动至少17过、安全0 | 新源重新绑定，不继承旧成绩；新增物体泛化标准待定；本轮均not_run |

候选完整姿态误差、到位姿态连续性、候选接受比例、显存/时延限额、跨物体统计方案及小车运输评分的具体接口均待定。不得用论文评分、固定10步演示或其他机器人数字填补。

## 采用的既有知识

采用 `Wiki/自动化开发范式与智能体协作.md#按当前任务选择验收依据`：资料与代码能证明接口存在，实际物理评分才能证明抓放完成。因此计划把候选质量、路径通过、接触保持、释放回位分层，不由单个 passed 字段或进程退出证明全部完成。

参考 `CapMesh/inventory/community-alternatives.md` 的复用准则：现成官方候选生成与本地规划优先组合。当前缺口是 SO101 几何/姿态契约，不是需要重建通用模型或另一套执行生命周期。本轮未新增能力选型决定或共享知识页。

## 本轮来源快照

canonical 工作区 HEAD：`427e3eb72760ac71e8a272498b28fd90ff8de1a2`。该目录存在多项既有 dirty/untracked 工作，含本地配置、日志和个人文档变动；HEAD 不代表这些当前文档或实验源码已经提交。以下 SHA-256 绑定本轮实际读取字节：

| 文件 | SHA-256 |
| --- | --- |
| PROJECT.md | `bf85361fc44d64f8c75e74dc044c89d9e3d6c8a11bb41a8cd7b9da5f55f61e73` |
| 主 task_plan.md | `c4500457c127a10eab9888c92685297d6a7a641ac5b129861ffe5584d2a52156` |
| position_ik.py | `77d7a49aac4816cc369ff61655fb9a0672c39beb5800d5cc82532dca444afbda` |
| grasp_episode.py | `e7808be611fc8c355adcfd2018944da854cfefb8ce7d792bf7b4167ec566e339` |
| learning_env.py | `d792db45e7ced2d80a10195d591184d5e6ba9ab7fec66a3a57405aa84c589049` |
| run_visual_grasp.py | `07345f576e89f4136e377d156207beba3a02b5461dfd07d96f9c309e5f2e8d02` |
| placement.py | `20a9d91a4e4bb2c69a6832b9f1b2e8cf1f44c615384f4d17625a1c7121a2358b` |
| pretrained-demo README.md | `e3d3aea3dd255dfa141c46062987616d330f5b6a2fa7bdc5ed2bd286fa8c6461` |

上述快照对应最初规划核查，不是完整适配或任务成功报告。

## 用户授权后的本地模型试用

用户明确确认继续试 GraspGen-X。新增[体验模块](../../experiments/graspgenx-demo/README.md)只薄适配几何输入、候选记录和静态检查；复用官方 `GraspGenXSampler.from_sweep_volume` 与配置/采样入口，未修改生成器、评分器或上游源码。

这条官方入口只需要 sweep_volume_v2 条件。其默认占位 mesh/TSDF 等字段不被当前两个已发布 backbone 消费；本试验没有拿占位 mesh 做碰撞检查，而是另存原 SO101 网格用于显示。描述符仍只是原仿真指尖区域近似，不是完整 URDF 夹爪向导验收。因此本次可以证明模型产生候选，不能证明 SO101 精确夹爪兼容、完整抓取姿态可达或物理成功。

实际取得并核对官方生成器与评分器：SHA-256分别为 `8b55f31cdb8340a573b4df27b027c15cff326bd6debcb389bf631d2aaab7ac44` 和 `cbf3f3bdb2e4c03fca8486ed24de0e6a8a859e6bd22bce2f1434a610335abd3e`。原配置合并后，两者 backbone 均为 ptv3vanilla，夹爪条件均为 sweep_volume_v2。可选 PointNet++ 扩展导入警告不等于本次使用了该 backbone。

本机RTX3050 4GB，生成16个diffusion候选，推理1.2337s、allocated/reserved峰值607.16/650MiB。使用完整方块网格表面3500点，非相机可见点云。首次缺serve依赖、随后Trimesh数组子类精确类型检查失败，均保留；官方权重未变，补依赖和标准float32数组后成功。

静态检查在五轴关节/执行器限位内尝试完整位姿拟合，未执行 `mj_step`。模型最高分候选0残差21.71mm/29.84°；本轮按既定位置/旋转加权残差最小的候选15为11.41mm/16.49°。这只是有限次数局部求解，没有完整姿态门、路径/碰撞通过或物理接触证据；非零残差不能证明全局不可达。

根研究的选题顺序未改变。本地试用由SO101原对话维护，原整体适配计划仍需根研究审阅后再安排后续；本次通知不自动扩大训练、评测或GPU分配。
