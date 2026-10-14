# Findings：GraspGen-X 与 SO101

## 2026-10-14：旋转释放与完整回位修复

- 首先只读复现：实际pad→方块物理距离0.3146mm；旧轴对齐估计给出-7.151mm。按已声明搬运FK旋转重算约-3mm，确认交接丢旋转是适配缺口，不等同于实际撞物。
- ReleasedObjectQuery冻结center＋SO3 rotation；pad先变换到物体框架，复用原OBB/AABB SAT，不另写碰撞算法；非pad使用MuJoCo真实旋转几何。更改四元数时设置[官方同框架标志](https://mujoco.readthedocs.io/en/stable/APIreference/APItypes.html#mjtsameframe)为NONE，避免编译时BODYROT捷径忽略新朝向。独立真实几何测试证明旋转生效。
- SeparationSnapshot拥有不可变旋转；worker核对中心、尺寸、四元数与编译标志，sweep/后台接纳绑定包含旋转。朝向变化、反射/尺度矩阵、过期旋转或错误模型朝向均拒绝。旧默认轴对齐行为保留。
- 已知平盘上方块落定：保留FK预计yaw，平放投影的角点改变量须不超原2mm；并在脱离后每2ms用实际8角点独立检查包络，只判失败不修正动作。该支撑假设不推广到任意形状或侧放。
- 仅补旋转仍近原3mm边界，核准显式释放参考23→28mm。旧默认不改；新高度经五段载荷路线、原14点/208采样脱离、1mm避碰及回位路线预验，static pad重叠2mm、预算下界64.892s。没有四舍五入、放宽3mm/1mm/0.2mm/2mm或延长90sim/120wall。
- 实际固定候选103完整回合：66.56sim/84.067wall、full=true、controller_done=true、物理和释放审计true；静稳14.08s、漂移0.592956mm、7140个2ms样本、再接触力0、回位误差0.000102520rad。实际脱离起态下，pad与估计包络重叠2.151381mm、持物角点误差最大1.719315mm、释放包络最小剩余0.228818mm；无无效机械臂采样或障碍接触。
- 170相关回归通过；source/trace/protocol绑定与实际阶段独立检查，录像完整解码且终态目视核查。成功目录 `full-cycle-20261014-212632-2677556`，前置 `transfer-preflight-20261014-212457`，均在原reviewed输出根；旧失败保留，权重/候选不变、无训练/实体。批次/新视觉门与50Hz未验证。

## 2026-10-14：新描述与实际抓放组件

- 复用固定官方ConfigWizard；运动检测只找到活动指，区域宽度为0，导致Step3 slider初始化失败。薄启动适配只显式选定真实固定/活动指网格，排除马达，采用已验框架与任务区间；官方跟踪源码未改。六步GUI保存后读回正确值，loopback服务与自有后台浏览器已关闭。
- 初次多字段GUI填入未全部传到后端，逐字段Enter与最终保存读回后纠正。初始失败目录保留，不将页面显示当作保存成功。
- 旧近似盒子与原网格微交约3.36µm。新的毫米网格区域经FCL表面/距离、watertight包含与包围检查，open/mid均1.9mm。区域针对原raw mesh，完整运动仍由原保守凸包内核单独判断。
- 新参数独立推理与池审计：48＋360=408、数值62、端点42、交集31、全244 jaw采样通过。首先选中OBB候选103（0.818573），复用原全位姿求解、OMPL预抓及原下降/抬升/闭爪路径，未改候选姿态或原安全阈值。
- 正例真正夹起41.6006mm、保持1.48s；空夹在6s闭爪窗口未建立双指接触，安全状态下拒绝。两者绑定最终contact_probe源码，原物体自由体、neq/nmocap=0、reset后不改object qpos。中断复验目录无report，保持incomplete，不计通过。
- 搬运前八角点最大误差1.4422mm，原2mm载荷假设成立；复用原TransportSnapshot/_run_transport_plan五段，独立0.005rad复查通过。实际搬运期角点最大误差1.7310mm。
- 完整回合物理监测grasp/place通过，蓝盘落定2.52s；释放审计1350个2ms样本，漂移0.5486mm、无再接触。controller在release阶段拒绝release_initial_overlap_not_allowed，整体失败，未脱离/回位。
- 状态字段补正后，用最终源码复验：55.60sim/33.654wall，物理grasp/place与释放组件通过，full=false、controller_done=false，仍为同一释放几何拒绝；非零退出且完整失败证据保留。两次异步调度下仿真时间有0.42s差异，不宣称逐位确定性。原视频对应的adapter字节快照SHA验证一致。
- 只读释放核查：pad_gripper估计重叠-7.15125mm，原允许最低-3mm；即使活动爪查询.5仍相同。实际方块yaw=31.0398°，原轴对齐释放盒子的2mm膨胀不足，最大角点外溢3.00905mm。说明搬运→释放接口丢掉旋转，且脱离起态需重新核准；尚未证明单改高度即可解决。不能扩大阈值或让物理真值驱动恢复。
- MuJoCo3.15原相机字段已改为cam_projection，兼容读取仍只接受透视并拒绝正交/未知。依据[官方API](https://mujoco.readthedocs.io/en/stable/APIreference/APItypes.html#mjtprojection)，新旧接口测试通过。原StateWorkcell增加可选2ms评分钩子，默认物理逐位不变、拒绝立即停止。
- 100项相关回归通过。新增依赖隔离于已有模型缓存，setup固定本机已测MuJoCo3.15/OMPL2.0.1/FCL0.7.0.11/rtree1.4.1/OpenCV4.11.0.86/FFmpeg适配0.6.0。上游跟踪源码、权重、原模型、规划算法及物理标准不变；全传递依赖仍未完全锁定。

## 完整几何/框架和闭爪诊断

- 官方向导要求两种状态的手指内侧区域盒，不是把整个夹爪实体扫过的体积填进12数条件；完整实体仍进入独立碰撞几何。来源：[向导说明](https://github.com/NVlabs/GraspGenX/blob/b9429097728cb1c430dd78b92edf17ba318aad03/README.md#integrating-a-new-gripper)。当前旧接触垫盒仅是暂定近指尖标注，向导/物理准入未完成。
- 直接由原MJCF提取完整夹爪两link、原网格与精确变换。独立URDF FK与MuJoCo的9jaw×2arm几何最大误差3.824e-9m，证明本机格式/框架一致，不证明实物精度。原模型/STL不修改。
- 原gripperframe site与当前模型框架完整相对旋转180°，site原点距pinch参考14.50mm；未把site直接代入新姿态。完整矩阵见frame-audit.json。SO101不默认采用对称等价姿态。
- 全408按原285对、1mm检查：62个数值复现、37个开爪证书，交集31个均完整244点闭爪通过。jaw0.5→0.015，步长≤0.002rad，未减样本/阈值。1e-6m/1e-5rad只用于严格数值复现，不是物理抓取允许误差。
- 原候选92虽然姿态数值接近零，未取得桌面余量证书而拒绝；无证书不是碰撞实证。筛后最高模型分候选103（OBB，0.7736）开爪下界2.023mm。31个全部motion_accepted=false，规划rig去除了目标，不能由此推断目标接触/全路径安全。
- 原采样/保守碰撞28回归通过；全部408记录、31×244、285对、输入/源码绑定和18组几何独立检查通过，零物理步。产物继续在同一被忽略CLI结果目录，未训练/额外推理/实体操作。

## 2026-10-14 接续：共享候选池与全量姿态诊断

- 人类授权接续其他任务后，选择原E2四组静态对照/E3残差诊断；未恢复旧训练、实时优化、20+20或实体联调。历史Next不作为自动队列。
- 固定上游的 [演示CLI](https://github.com/NVlabs/GraspGenX/blob/b9429097728cb1c430dd78b92edf17ba318aad03/scripts/demo_object_pc.py) 默认Z偏移-2/0cm、dense-topandside；[公共planner API](https://github.com/NVlabs/GraspGenX/blob/b9429097728cb1c430dd78b92edf17ba318aad03/graspgenx/samplers/planner.py) 默认六个Z偏移、sparse。两者不能混称同一默认配置。
- [官方run_graspmoe](https://github.com/NVlabs/GraspGenX/blob/b9429097728cb1c430dd78b92edf17ba318aad03/graspgenx/samplers/graspmoe.py) 返回扩散/OBB子集。本轮从同一池提取四组，记录不同生成预算；纯OBB是官方分支子集，不是新写算法或官方独立CLI模式。原IK固定组有一个先验姿态，也用同评分器；不证明感知泛化。
- seed0、3500点完整方块、同指尖描述：API48+216，CLI48+360；扩散子集逐位相同。原16/次在官方min40/max6下实际生成三次，不能与旧一次16比较等算力收益。
- 按分数取16：API混合有接近零残差OBB顶抓；CLI前16全OBB侧抓，配对加权最佳41.23mm/40.00°。扩散配对最佳0.227mm/5.084°，没有混配各自最小平移与旋转。
- CLI全408复核：OBB候选92评分排289，拟合约1.94e-10mm/4.82e-11°；最高分候选297为75.55mm/64.16°。证明本轮评分前16不代表整个池的拟合能力，不证明评分器普遍失效或候选92物理可用。0.1m/rad仅用于诊断排序，没有姿态接受阈值。
- 原始产物：`experiments/graspgenx-demo/output/comparison-20261014-165300-2254125/`（API）、`comparison-20261014-165422-2256124/`（CLI含all-candidates）。9项边界检查、真实入口、来源/排序、源码/输入/回执哈希和408分母已验证；无碰撞/物理成绩。
- 沿用Wiki“按当前任务选择验收依据”：模型推理、静态残差、碰撞路径与自由体接触分别验收。知识收尾already_covered，适配事实留在本计划。

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
