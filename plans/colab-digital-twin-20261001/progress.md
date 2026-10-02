# Progress

## Current

2026-10-01：真实AGY/CODEX/ZCODE方向会审完成。首轮独立判断，只请AGY追加一次针对模型顺序的复核；保留ZCODE状态MLP先行的分歧。根Codex建议同步数据/专家恢复→小配置无图像ACT→纯策略抓放→单相机视觉；4GB内存与训练效果未验证。原始响应、超时和引用核验在被忽略的local-documents/decision-consultation-20261001/；可发布会审见[learning-review.md](learning-review.md)。

本轮只完成会审、数据与验收约定，没有安装学习依赖、训练模型、改仿真代码或分配GPU。既有41项物理抓放检查不扩张为学习验收。下一步owner根Codex，最短入口是grasp_episode.py的advance记录和独立学习环境最小batch预检；S7b/S7c/S7d均未开始。保护原规划环境、自由物体动力学和原仓库index，现场遗留继续按原交接保留。

文档归档与 Colab CPU 基础平台完成；修正后的一命令运行成功并回收结果、释放会话。用户已选择运动自主规划以 MuJoCo 为核心，单主线整理和实际 AGY 咨询完成；位置IK、OMPL全局绕障和物理执行已接入，本地29项测试与真实Colab CPU20轮通过；修正了默认隐藏group3环境几何的显示问题，可见场景最终复验与视频回收已通过。

## Done

- 六份复制件校验 SHA256、Git ignore 和无索引记录。
- Colab CPU 会话分配与固定版本依赖安装成功。
- 17 文件的模型/脚本清单包上传；其中无个人文档或现场数据。
- `python3 experiments/colab-twin/run_colab.py --session so101-twin-final-20261001` 实际执行成功；MuJoCo 3.3.7/OSMesa，3000 步、6 秒、150 帧。
- 下载的 MP4 独立确认 640×480/25fps/150 帧并完整解码；CSV 150 行，全部数值有限、时间每 0.04 秒连续递增。
- 最大关节限位超出 0 rad；最大跟踪 RMSE 约 0.000575 rad。只代表合成轨迹物理基础实验，不代表碰撞自由规划或抓取。
- 四项资源清理失败路径测试通过；已有四项 teleop 回归、静态布局和前端语法检查通过。
- 本轮创建的全部 Colab CPU 会话均已释放；无 GPU 或真机操作。
- 两份历史修订 DOCX 和中期 Markdown 从远端副本保存在被忽略的 local-documents/prior-revisions，后续停止追踪，不重写历史。
- 完成本地 SO101 多工程/快照与有界历史核查；确认完整 MoveIt/RRTConnect 代码、缺失 MTC 源码和零字节逐轮证据。
- 实际调用 AGY 原生CLI单次只读咨询；采纳 MuJoCo + Python IK/OMPL 主方向。原始响应仅保留在被忽略的 local-documents。
- 整理 PROJECT / README / ARCHITECTURE / DECISIONS / 规划路线与现有计划，明确组件职责、复用资产、Gazebo/Colab边界和三步正反例验收。

## Remaining

S2/S3/S4全部完成：本地29项测试、真实Colab CPU20轮与可见视频回收均已通过。后续接触抓放、视觉与真机同步保持未完成。交付通过既有 master 非强制推送，版本由 Git 记录。

## Issues / Handoff

当前脏开发树使用旧 Git 基线，保留原状，在基于 origin/master 的隔离工作树完成本轮交付。已有工作区嵌套未出生 Git 与损坏历史备份保持不动。

根 Codex 接续范围：旧开发树与新远端基线的安全对齐；现场动作、串口配置、标定、登录/业务日志、录制和生成 ROS 导出保持本地。主从迟钝根因未实测，既有 `../teleop-latency-20260922/task_plan.md` 仍是恢复入口；不以本次离线仿真关闭该待办。

ROS/MES、Gazebo、真实 YOLO 与真机闭环保留原工作区任务状态；需要恢复时从 `../../workspaces/so101_ws/docs/任务清单.md` 进入，不重新宣布验收。

旧 `docs/HARDOFF_2026-06-26.md` 含明文 sudo/SSH 凭据及带凭据的历史命令，原件保留并精确忽略，不进入发布。根 Codex 未来如需复用，只从原件提取不含凭据、注明历史范围的结论；不复跑历史命令或恢复会话。

旧 `docs/SO101_MOTOR_TO_URDF_MAPPING_2026-06-27.md` 含现场舵机读数与临时映射，按项目“标定留本地”规则精确忽略并保留。其 wrist_roll 符号描述内部不一致，简化公式漏 scale；根 Codex 若恢复标定工作须核对当前源码与现场数据，不直接采用这份报告。其余两篇 Gazebo 历史报告已加历史边界，不作为当前运行验收。

MTC缺失核心和零字节逐轮产物留作待恢复历史，不从summary重造并冒充原件。根Codex从原生MJCF接续自主规划；规划与执行实例分开，碰撞检查必须覆盖路段。现场 `so101_gz_scene/{reality_map.yaml,calibration.yaml,calibration_report.txt}` 继续保留本机并精确忽略。

## Next

根Codex后续进入接触抓放、目标视觉或实体同步时，需要重新收敛任务验收；不把当前静态位置到达扩大为抓取/真机通过。主从迟钝待办继续保持，缺失MTC历史也保留恢复入口。

## 2026-10-01 接入实现

- 新增位置IK、五轴OMPL规划、派生碰撞场景、独立物理执行和公开障碍fixture；默认模式改为planning，原baseline保留。
- 本地29项测试通过；实际模型FK/IK、joint/ctrl交集、不可达拒绝、非相邻自碰/桌面/障碍、夹爪实际偏差、离散边中点碰撞、拒绝近似路径、错误目标执行失败、释放失败与种子溢出都覆盖。
- 第一次真实Colab：Python3.13.15 / MuJoCo3.3.7 / Mink1.1.0 / OMPL2.0.1 / OSMesa，主路径113点、7546物理步、15.092s、378帧。下载MP4独立解码378帧、640×480/25fps；CSV756行全部有限且时间连续。会话已释放且独立state删除。
- 20轮±3mm目标扰动均直接路径被挡，规划与物理执行20/20通过；均值0.545mm、p90 0.561 mm、最大0.589mm，主执行误差0.549mm，20ms碰撞检查无无效采样，关节超出0。平均规划时间约0.504s（仅本次CPU批次）。
- 有界不可达搜索返回unreachable、封闭场景invalid_start；独立有效起终点完全隔断测试拒绝OMPL approximate solution。
- 第一版画面未显示group3工作台/障碍，原始实验留存不覆盖；已加入group2零碰撞掩码可见副本，实际EGL预览与渲染scene测试通过，最终Colab20轮重新运行。
- 发布边界：上传包23个manifest条目+manifest；不含个人文档/标定/凭据/原始日志，所有文件hash核对；results.zip额外忽略，分次保存结果。
- 交付审查确认主工程939个未修改公开文件与delivery逐字一致，没有未理解的公开源码增量；旧Git index、嵌套历史及现场文件仍保持。同步本次已审查patch和新文件，不重置旧工程。

## 最终可见场景复验

- 命令：`python3 experiments/colab-twin/run_colab.py --session so101-planning-visible-20261001 --episodes 20`。实际成功；CPU/Python3.13.15/OSMesa，20/20自动绕障与物理执行通过，29项本地测试通过。
- 结果目录：`experiments/colab-twin/output/planning-20261001-053716-lzgpaif1/`（Git排除）。MP4完整解码378帧、640×480/25fps，CSV756行有限且时间递增，JSON逐轮20项均通过、直接路径均被挡，默认画面工作台/盒子已目视核查。
- 末端误差均值0.545mm、p90 0.561 mm、最大0.589mm，主执行0.549mm；规划均耗时0.510s。本次只覆盖单个静态障碍附近±3mm位置扰动。
- 最终bundle SHA256：`28689295fb99b69937124709e89c3bc647d42f6d75f1b80a3208711502c075ab`；manifest23个文件条目+manifest，自身哈希与上传源码一致，无个人/凭据数据。
- report SHA256：`ffefd2c8c02bfb27507e51b446c4d0d7d46a2ca4bd4b01941387f15ea677188c`；video SHA256：`4d0d4f66ff392eb2d72db9e64094d88924d5a3c699d5d7007f4ee119991594be`。
- 会话已释放；服务器查询没有活跃会话。主工程只应用本轮已审查patch并复制独立结果目录，保留其旧Git index和所有现场数据；交付从隔离worktree非强制推送至既有qiaoqiao2521/so101 master，提交号由Git记录。

本机README原有“唯一开发入口”和绝对路径说明保留在主工程；本轮只patch其实验段落，公开README沿用既有项目说明，不用发布副本覆盖本地入口。所有规划源码与测试在主工程和交付树逐字一致。

## 2026-10-01 主线逐层单回合接续

用户确认继续SO101 MuJoCo＋IK＋OMPL，并逐层通过后再继续。新增run_staged.py及三项阶段边界测试，复用现成环境（Python3.12.3、MuJoCo3.3.7、Mink1.1.0、OMPL2.0.1、NumPy2.5.3、imageio2.37.0）。没有模型训练、Colab分配或实体连接。

四层实际通过：依赖版本/导入；reset10步/0.02秒；直接插值被挡的113点IK/OMPL精确路径；独立位置伺服7546物理步/15.092秒。TCP误差0.549381679mm，20ms碰撞无效样本0，最大限位超出0。完整CSV756行有限、时间严格递增，末行TCP独立复算误差一致；视频378帧全量解码通过，工作台/盒子可见。32项回归检查通过；真实缺失依赖CLI负例停在第一层并保留后续not_run。动态重规划、抓放、视觉和真机仍未验收。

逐轮结果保存在本机被忽略的 experiments/colab-twin/output/staged-c5a0f2e203cf4453a7b501d6f8f4e62b/。最终候选代码与交付代码逐字一致；原始report SHA256 4ef35b169995ae9ef9db9dae1d929c4466f47863489ebdea90d6947ba5237c3c；MP4 SHA256 a41ef5e2bbcb2f9f77a4b9e9d43aa7322f8544a7d666395ce50d9b01cac9a885。渲染结果目录与既有批次隔离保留，视频/日志不入Git。

本次公开范围仅新入口/测试、README/PROJECT、实验说明与已有三份计划。按基线核验并保护canonical index和独立README入口；既有旧树/现场数据的接续责任继续归根Codex，沿用本文件Issues/Handoff。GR00T仍按用户“最后一次”保持停止；主线后续从此单回合入口进入，接触抓放/视觉/动态反馈需另行收敛验收。

## 2026-10-01 单臂夹取建模

用户指定先建模、改善场景，并纠正主从为现实系统；本轮只有一台从臂。找到本地BLD-001建模说明、主从场景生成器和动作模板；当前工程无其记载的Blender/GLB成品，LightArmPreview.vue与leader专属STL为零字节。复用完整的原生从臂13STL，新增grasp_workcell.py/preview_grasp_workcell.py及动态物体/夹爪检查。

新模型包含工作台、开放红/蓝料盘、相机支架、自由物体；生成1280×720三视图与100帧/4秒机械开合视频。原模型SHA仍d75253eb568e8a7214db9c631ab7bed4217f608a26f7276ebe9a7636cac82580。物体18×18×16mm、10g；实测中心z从0.012m落定至0.009784m，真实pick_floor接触。夹爪实际范围0.250019–0.799997rad，预览期间物体抬升约0；grasp_success/lift_success=null，尚未夹取成功。视频独立全量解码通过，34项回归检查通过。派生MJCF可编辑，原模型不改；无实体或云端操作。

结果保存在Git忽略的experiments/colab-twin/output/grasp-model-72f103318b2a4cf78c7b89f317ee53ed/。原场景建模说明只用于布局参考，仿真坐标和物理参数不当作实物标定；现场模板不复制发布。后续owner根Codex：先对位/接触建模，再以物体抬升与持续夹持验收；已有静态规划入口及遗留交接保留。

## 2026-10-01 加障碍夹取

新增grasp_episode.py及接触正反例。橙色障碍(.265,0,.065)m、半尺寸(.025,.028,.065)m；蓝盘上方→红盘上方的直接关节路径被挡，OMPL精确路径绕行，再下降/闭爪/抬升/保持。自由物体18×18×16mm、10g，无焊接/吸附/mocap；局部指尖接触垫与.15Nm夹爪力矩为仿真假设。原网格及原模型保留，sourceSHA不变。

本地实测抬升38.675mm，保持1.48s，两指持续正接触力且无底部支撑；逐2ms障碍接触0，20ms机械臂碰撞/限位无无效样本。38项测试通过，真实空夹负例拒绝。结果owner根Codex；放置释放、目标扰动批次、动态障碍反馈和真机验收仍待处理，GR00T不恢复云端尝试。

已回收本机忽略目录`experiments/colab-twin/output/grasp-1a87cf92da6f43498a3a7a1d7465bd56/`，953帧1280×720/25fps视频严格全量解码通过；1906条轨迹时间严格递增，保持段双指最小法向力分别1.972/1.971N，无底部支撑，最低抬升38.675mm。近景与绕行中段目视确认，原始模型SHA不变。

### 夹取可见性补充

原总览视频前约33秒物体保持盘底，抬升只出现在最后约4秒，广角与指尖遮挡使运动难以判断。新增固定近景grasp-closeup.mp4，只记录闭爪/抬升/保持。重新实际渲染的物理结果与原轮一致：38.675mm抬升、1.48s保持、逐步障碍接触0、20ms无无效姿态。261帧1280×720/25fps/10.44s近景严格全量解码通过，同机位抬升前后两帧目视确认物体离开料盘底，轨迹同步保存。输出位于被忽略的`experiments/colab-twin/output/grasp-closeup-8bc8e4fc3f9048ab92209fb01f2f182e/`；动作、接触假设及验收判据不变。

## 2026-10-01 搬运放置完成

新增placement.py、test_placement.py及--place入口，完整接续红盘抓起→竖直载物内侧绕障→蓝盘下降→松爪→撤离→落定。载物查询使用实测相对姿态和独立MjData，world碰撞间隙局部截断20mm，Cartesian3mm/关节边.01rad离散检查；执行方块仍为自由物体。Noslip10次解决原软接触约.5mm/s慢滑；夹爪保持.15Nm和原指尖接触垫，无焊接/动画附着。

41项测试通过；真实完整正例与noslip=0滑落停止负例均实际执行。最终中心(.238655524,.139143954,.009921450)m，距蓝盘中心1.6mm；全物体在蓝盘边界内，place_floor真实支撑，双指接触力0，平移速度3.66e-16m/s，撤离后稳定1.48s。途中双指持续接触、逐2ms障碍接触0、20ms机械臂碰撞/限位无无效样本。抬升段约40.777mm，物体在蓝盘释放后落定。

本机忽略目录`experiments/colab-twin/output/place-421c289686894ea6836e38fb04922a02/`保存派生MJCF、轨迹、报告、近景及全部视频。transport-place.mp4为972帧1280×720/25fps/38.88s，全量严格解码通过；总览也全量解码通过。固定镜头中段确认绿色方块在指尖绕障、红盘为空，最终近景确认蓝盘内方块与张开撤离的夹爪。原模型/index保持，不涉及云端GPU或实体。

下一步owner根Codex：按需求选择扰动批次或视觉输入；Noslip/摩擦/接触垫未经实物标定，固定内侧Cartesian路线不是通用动态障碍规划器。曾滑落失败的结果与部分轨迹仍留/tmp供诊断，关闭Noslip负例为稳定复现入口，执行损失接触≥100ms即停止。既有现场数据/旧树遗留继续按本计划保护与交接。

## S7 数据解耦、资源微基准与物理止损（2026-10-01）

用户以同一数据双探针收敛ACT/MLP分歧。实现learning_data/env/models/probe、train_state_policy、replay_learning_data、evaluate_state_policy、run_learning及独立边界测试。HDF5字段为state6/env30→absolute action6，另存实际executed_action、next_obs、时钟和invalid标签；固定2ms物理/20ms控制。专家用实际接触推进闭爪/释放；模型不接收阶段或时钟。原动作与状态保留float64，网络适配为float32；没有修改原MJCF/STL或已有规划环境。

采集共保留6次尝试（4成功、2失败）：首次float32正常采集因释放条件过严失败；修正后float32正常/恢复成功，空夹负例超时失败；raw64正常/恢复再次成功。最新分层入口选择raw64两正例＋保留空夹负例，共7887转换，其中6291训练候选、10扰动无效标签。恢复前真实执行±.02rad内的关节指令0.2s，再从实际q与物体位置重新IK/OMPL求解；第一纠正样本严格接续扰动结果。只有固定布局、起点扰动，未覆盖路线中段的误差分布，也未拟合DART噪声。

原float32回放：3133步物理抓放通过、关节误差1.91e-6rad、时间误差0；释放落盘附近角速度/接触力严格环境逐帧匹配失败，未放宽门槛。修正raw64存储与forward节拍后，独立回放与完整入口内回放均通过，state/env/time最大差全部0。

完整入口实际运行：`experiments/colab-twin/output/learning-gates-20261001/report.json`，退出码1，status=stopped。data、data_replay、resource、sanity_training通过；sanity_task失败；evaluation/vision=not_run。最新ACT五步compute0.10799s，allocated117.585MiB/reserved146MiB；MLP0.00569s、17.531/22MiB。RTX3050 Laptop物理4096MiB，CUDA可用区域3761.75MiB，两者分别记录。独立学习环境Torch2.7.1+cu126、NumPy2.2.6/h5py3.14.0，72包依赖检查通过；空环境cu126配方dry-run解析71包通过，上游默认cu128源需用--no-sources排除。

最新单轨迹ACT：3133帧，5000step、第26epoch、118.97s训练；chunk归一化L1=0.03301、首动作MAE=0.01085rad，GPU allocated117.585/reserved150MiB。权重SHA256 `2984659b93b016dfa9caf99f20633a592237a736fedbd026747d420edf71e8f5`；CPU重载最大预测差3.576e-7。仅正常单轨迹限时诊断，没有held-out或恢复训练，尚未完整过拟合。

纯策略回合只加载初始快照，所有控制由ACT输出，无IK/OMPL/stage/专家动作回退；0.36s后真实碰到障碍，SafetyStop按失败计数。并未将离线loss或资源通过写成抓放成功。第一轮原始档案模型同样0.52s碰撞停止。两次失败轨迹与权重都在ignored output保留，后续40回合及视觉无消耗。

可恢复交接owner为根Codex。最短入口：独立learning-venv运行LEARNING.md采集/回放/run_learning命令；当前checkpoint位于`output/learning-gates-20261001/sanity_training/policy.pt`。先检查开始几步预测与真实状态偏离、专家路径起步标签和接近段恢复覆盖，必要时追加一项有界诊断；不把下一步变成扩大GPU、批量长训或视觉。只通过数据回放不能证明策略泛化或实机可靠性。未完成的状态闭环在S7d保留明确失败门槛。

收尾验证：独立learning环境完整86项测试通过（含原规划/抓放真实正负例、数据精度与时序、chunk断点/归一化/重载、物理事件验收、假exit0止损）；Markdown相对链接和diff检查按提交范围验证。数据、权重、原始会审、日志与pip环境清单继续Git忽略。

旧树交接复核：canonical仍有22项tracked变动，包含322行app.py改动、静态界面、现场配置/录制/业务登录记录，以及个人文档迁出；旧HEAD/索引保持。HANDOFF/SECURITY解释主从计时及认证边界，teleop-latency计划明确等待硬件恢复。不能把现场日志/标定与个人原件提交到public远端；产品硬件参数验收仍缺，未用这次学习suite冒充。owner根Codex保留该树，最短恢复入口为plans/teleop-latency-20260922/task_plan.md、REPORT.md及mint_follower_demo/tests，用户恢复硬件任务前不驱动设备。已验证的仿真学习成果由独立delivery分支交付并同步可用源码，受保护树不重置、不清理、不覆盖。

## S7d 起步偏差与接近恢复（2026-10-01 接续）

用户要求先检查起步预测偏差和接近段恢复数据覆盖，再过一个纯策略抓放回合；本轮不启动20+20或视觉。实现CPU有界diagnose_state_policy.py，支持旧absolute与arm_delta checkpoint，起步1/16/50帧/逐阶段动作误差、速度归一化、保存在线前20步覆盖和有界近邻标签检查。报告保存模型/数据/源码hash与官方ACT来源；阶段仍只用于审计。

旧absolute首步pan/elbow/wrist错误约-.02448/-.01543/+.00988rad，下一拍速度pan/elbow约-1.178/-1.061rad/s；专家正常command-q只有几毫弧度。内部动作编码改为五轴arm_delta+absolute gripper，chunk未来目标均锚当前起点q，执行还原absolute；训练only qvel尺度下限.1rad/s，确定性noVAE/dropout0。默认absolute/原行为兼容，编码/归一化选项随checkpoint保存，官方ACT源不改。

首个5000step/82.81s候选：arm第一拍maxerror .000187rad，物理首动作MAE .001474rad（gripper占主要误差），GPUallocated87.05/reserved96MiB。但纯策略39.94s限位停止，物体仍留红盘；诊断发现gripper首command .50719，20拍actualq漂到.55210、qvel约.16rad/s，旧有恢复未覆盖这种偏离。该失败和权重保留，不因运行更久宣称通过。

采集v3专家：reference_route固定已通过路线，验证modelSHA/start/goal/wholepath；去掉学习端点固定等待，用下降几何触发闭爪、物体在蓝盘且z<.0145m时释放，无速度条件导致的反复闭爪。nominal＋startup±.006rad/20ms＋approach35%处+.002rad/20ms共4成功回合，12378frame/12375valid。扰动真实推进，保留非零速度，第一valid command是actualq制动，再从当前q/object重求IK并验证连接/剩余路径。startup首validpan速度+.263833/-.263756，approach+.047732rad/s；前一nextobs和第一validobs/state/env/time逐项一致。3项真实artifact测试全部通过无skip；独立v3startupplus原动作3061步state/env/time最大差全部0，抓放通过，无安全停止。

关键采样默认1兼容全量permutation；显式5倍覆盖每episode前50帧、invalid间隙后首6valid帧、jaw跳变附近±8帧，不跨episode/间隙且union不叠乘。v3四正例有界ACTfit：34509step/45epoch/600.002s，按wall上限停止，551748draw/12375unique，critical实际68204draw；dim256/chunk16模型3711494参数，allocated87.053/reserved96MiB。首动作MAE .000258rad，arm五轴MAE约.000019–.000105rad，gripper .001244rad；完整chunk归一化L1 .18112，未完整过拟合。权重 `output/state-delta-recovery-fit-20261001/policy.pt`。这些是四条固定布局训练轨迹的拟合，不是held-out或扰动恢复通过。

同权重默认首动作执行（每20ms重新推理）纯策略907周期/18.14s后腕关节axis3目标1.65816687超过1.65806上限，actualq1.65801771，未抓起物体。已增加SafetyStop的失败command/越界轴/时间诊断，不放宽限位。起步jaw .499759→.498278→.459505→.413686，qvel偏差放大；不是4GB OOM。报告位于ignored `output/policy-v3-baseline-20261001` 与 `v3-online-audit-20261001`。

`run_learning.py --sanity-only`明确只验一个回合，成功状态passed_single_episode_gate；默认仍保留完整入口。`--train-recovery`可显式纳入全部合格正例，负例只留审计；actionencoding/qvelfloor/VAE/dropout/weights/lr参数已转发。8项入口CPU边界测试通过。随后完成下述显式有界v4/v5训练诊断；单回合尚未通过，20+20/视觉保持未运行，owner根Codex。

### S7d 接续：反应式接近、策略前缀恢复与有界训练

v4只将approach改为actualq路径投影＋.006rad前视，每拍.005rad验边；后续下降/载物路线仍时间minimum-jerk。四专家正例9404帧/9401valid，起步前.38s arm位移L2 .153997rad。nominal2350步/startup-plus2351步独立raw64重放state/env/time差均0并完成抓放。产物：ignored `experiments/colab-twin/output/reactive-v4-{nominal,startup-plus,startup-minus,approach}-20261001/`、`reactive-v4-independent-replay-20261001/`及`reactive-v4-startup-plus-independent-replay-20261001/`（后两者同一output根）。

四档案ACT有界fit13491step/240.013s，输出`output/reactive-v4-state-fit-20261001/policy.pt`，权重SHA `d0142fecc159f3390a9cbeeb350ff83f0ab4518eab540e24480824fc7eb213d8`；归一化fit四份训练行。默认/chunk16/chunk16+nearest纯策略9.74/10.22/10.22s腕限位停止，无抬升；报告为同output根`policy-reactive-v4-{baseline,chunk16,chunk16-nearest}-20261001/`。同四档案MLP 8000step/8.234s，训练`reactive-v4-mlp-first-action-probe-20261001/`；纯策略`policy-reactive-v4-mlp-probe-20261001/`16.08s盘壁碰撞，`policy-reactive-v4-mlp-nearest-20261001/`9.92s桌面碰撞。均保留原权重/失败轨迹，不称通过。

v5采集只执行无接触策略前缀1/2/4/5s（50/100/200/250拍，20ms，最多250拍且≤5s），逐拍限位/碰撞/接触与command偏移检查后，以actualq制动、fresh IK接回参考路线。来源`output/policy-reactive-v4-chunk16-nearest-20261001/attempt-000-nominal/policy-transitions.npz`，SHA `20db559734f7ae635ed1e8a43c788ba294c693e3b4f4bdd2646b6cac8831e21e`；四正例`output/policy-recovery-v5-prefix{50,100,200,250}-20261001/`共9423帧/8823valid，600前缀帧全部排除训练。独立`output/policy-recovery-v5-independent-replay-20261001/report.json`2372步state/env/time差均0，真实抓放通过，3项artifact测试全部通过无skip。仅证明这些偏移后专家恢复及精确重放，不宣称完整DART或硬件可靠性。

八档案18224valid行在`output/policy-recovery-v5-state-fit-20261001/`以v4权重初始化，保持原四训练档案归一化，fresh Adam/new counters，lr2e-4；预算120s/7000step/200epoch，实际7000step/7epoch/109.024s。新权重SHA `26268fb563824fb0fe4268a46faa55e1b798b12386e550989b766ae8aba04472`，CPU重载差5.54e-8rad，allocated87.053/reserved96MiB。`output/policy-recovery-v5-baseline-20261001/report.json`10.48s腕目标越下限，无抬升/抓放；训练集拟合未提供held-out证据。可运行的采集/八档案接续模板与[官方ACT/DART引用](../../experiments/colab-twin/LEARNING.md)已补充；raw HDF5/NPZ/权重/日志均Git忽略。

离线定向探针固定q/其他env，只将六轴qvel由专家值替成在线值，转角腕target−q从+.002804变为-.004647rad（专家+.005230rad），`output/v5-qvel-causal-audit-20261001/`已归档。显式`--mask-robot-velocity`在训练/推理一致屏蔽归一化env[0:6]，原始数组/统计与实际动力学不改，有限性先拒绝，选项随checkpoint持久化、旧缺省false；初始化允许显式增加、不允许静默取消。入口透传两屏蔽标志及init-checkpoint，11项入口边界/透传测试通过；这不是当前整套测试或物理验收通过。

`output/policy-recovery-v5-qvel-masked-fit-20261001/`从v5权重26268初始化，同八档案、原四训练归一化继承、fresh Adam，3886step/4epoch/120.039s按wall上限停止，allocated87.053/reserved96MiB，输出SHA `08de5fc1d29ca6849b614f0fa5ed6b6852b1785c60af9e0be61f517eb00ccc24`。同output根`policy-recovery-v5-qvel-masked-baseline-20261001/`18.64s料盘底碰撞，无抬升；`policy-recovery-v5-qvel-masked-chunk8-nearest-20261001/`52s料盘底碰撞，无抬升；`policy-recovery-v5-qvel-masked-chunk16-nearest-20261001/`实际抓起并保持17.56s，35.2s在蓝盘外开爪、35.4s丢块，完整抓放失败。

`output/v5-qvel-masked-physical-audit-20261001/release-probe.json`在1760拍fresh chunk边界核对raw模型预测；实际姿态/其他env不动，仅将物体速度替为几何近邻训练值，jaw .401425→.017844，原始速度置零探针.018514。物体线/角速度归一化近邻差L2 105.745/134.035，4/6轴越训练范围；名义真释放反例零原始速度仍开爪。证据支持局部输入敏感性，不能以离线改输入宣称任务修复。

新增`--mask-object-velocity`只屏蔽归一化env[13:19]线速度3＋局部角速度3，与robot flag独立；训练/推理/保存重载共用适配器，旧默认false、初始化from/to明确，实际速度和物理监测保持。下一项同八档案、robot mask保持、额外object mask的有界fit及纯策略结果待根Codex填写；没有创建载物collector或新增数据。根Codex接续最终实验/整体验证，本节不预报完整单回合通过；20+20/视觉未运行，无新云端或实体动作。

### S7d 本轮止损与可恢复交接

双速度屏蔽ACT保持八训练档案、原四v4归一化统计和fresh Adam，lr2e-4；6657step/6epoch/120.017s后按wall上限停止，allocated87.053/reserved96MiB。权重SHA `84a4ef58d139be647a46f29c5be774325cd43e367ac89c3fa0f3d954c157e59d`，`output/policy-recovery-v5-all-velocity-masked-fit-20261001/`；chunk16+nearest在14.20s发生pick_floor与moving_jaw碰撞保护，未抬升。不是OOM，也未修改物理速度或接触/限位标准。该候选不替代已真实抓起的robot-only-mask候选。

同四v4数据、相同输入屏蔽和原统计的MLP CPU对照：37801step/65epoch/45.001s，`output/reactive-v4-all-velocity-masked-mlp-fit-20261001/`；nearest回合真实抓起并保持1.64s，15.92s actuator限位停止，完整抓放未通过。它是诊断对照，不是ACT资源失败后自动选择的新主线。仅限时拟合和平均误差不能证明局部控制精度与恢复泛化。

精确训练观察范围clip探针保留全部18224有效训练输入，但bad-release jaw .401425→.309138仍开，16项未来动作全开；不实现此adapter，不追加阈值猜测。来源`output/v5-qvel-masked-physical-audit-20261001/support-clamp-probe.json`。

归一化来源核对：robot-mask权重学过八档案，统计值实际逐项等于v4四档案。`output/policy-recovery-v5-qvel-masked-origin-verified-20261001/`仅更正来源归属，权重/统计/掩码逐项不变；保留原权重，未覆盖。初始化实现将权重训练来源与统计拟合来源分别保存，验证统计来源属于原训练集合。最终双maskcheckpoint明确记录四档案的统计来源。

当前单回合状态为**未通过**，S7d/S7e保持未完成；20+20、视觉、Colab/实体均未运行。最强物理候选仍是`output/policy-recovery-v5-qvel-masked-fit-20261001/policy.pt`＋chunk16＋nearest（八正例仅用于固定标签支持），真实grasp/17.56s hold后蓝盘外提前释放。模型评测无IK/OMPL/stage/专家兜底。

最短接续owner根Codex：先复核该候选在接近末端/载物搬运的实际状态覆盖，必要时单独采集一条真实偏差后的专家纠正，再过同一纯策略单回合。已提出但**未实现/未采集**的最薄载物入口为：从该候选NPZ前1000拍（20s）真实逐拍执行、全部排除训练标签；actual双指持续抬持门槛通过后，仅离线调用现有plan_transport生成纠正，独立raw64重放通过后才训练。不得恢复NPZ终点qpos、定时强开爪或将专家接管当作策略成功；现有approach前缀≤5s限制继续保留。该方向也需先验真，不能以增加预算替代覆盖证据。

最终完整150项测试通过，无跳过（40.177s）；包括真实规划/抓放正负例、四v5档案与独立重放绑定、遮罩/初始化/保存重载和单回合止损边界。日志`output/final-all-velocity-single-gate-tests-20261001.log`。默认旧absolute、全速度输入、单步执行保持兼容；本轮试验选项均显式记录。数据/权重/审计/log仍Git忽略。canonical现场22项tracked遗留按S7交接保留，根Codex不改变其旧索引/原模型或发布现场配置。

### S7d AGY 实际审核完成

按用户要求，实际AGY审查提交 `5c41ca0` 并引用本地源码及产物；原生会话 `11ef62ca-91ac-414d-b850-1a1b6225f170` 完整读回，与最终CLI正文一致。首轮超时空响应不算完成，一次无工具收束后才记完成。AGY和根Codex各独立执行3项真实恢复档案检查通过，本轮未重跑150全测、训练或物理回合。

AGY认可本次实现/记录边界，但完整策略抓放未通过；提出接近末端/持物实际偏差纠正覆盖不足。根Codex保留“起步覆盖充分”、速度唯一因果与按固定拍数滤波等分歧；四份旧统计合法继承不等于已证明漂移故障。具体引用、采用范围及未采用建议见[本次审核记录](learning-review.md#2026-10-01agy-对起步偏差与恢复采集的实际审核)。S7d/S7e状态不变；下一步owner根Codex，先覆盖证据再有界实验。

### S7d 接近末端与持物纠正初期记录（已被下文接续）

用户明确要求补齐纠正数据并重过纯策略单回合。根Codex在delivery树实现独立collect_policy_recovery.py，真实执行前缀后接管，前缀全invalid，首valid保持真实速度/状态连续；原grasp_episode前接触≤5s入口未扩大。接近末端用450拍（600拍已在低位闭爪，不按hover标注），持物用1700与1756拍；持物入场要求当下持续双指抬高≥25mm/≥1s。离线专家载物几何查询提取为placement helper，query-only，不操作真实执行qpos。

450入场加强版与1700/1756向前剩余路线纠正均实际抓放通过；各raw64独立重放核对后才进入新训练。初始1700回溯整条搬运路线也通过但不选择作新主训练，保留原产物；新held入口从当前Cartesian投影只连接剩余腿，避免向已完成路线反教。当前纯策略单回合仍未通过，训练/新策略验收待根Codex填写；20+20/视觉/硬件/云端均未启动。

### 2026-10-02 接近末端、持物及蓝盘边缘实际纠正

用户要求补齐实际偏差纠正后重过纯策略单回合。最终选择六份guarded新增档案：接近末端450拍、持物1700/1756拍、独立学习夹爪候选的1800拍、v7早期持物900拍、v8蓝盘接近corridor持物2500拍。六条共15989raw/6883valid/9106invalid；加原八份后14条共34816raw/25107valid/9709invalid。每份都从参考初态真实执行已保存的策略command，前缀expert标签NaN且全invalid；实际持续双指悬空持物才准入，首valid用actualq制动，速度/状态连续，没有恢复NPZ终点或附着物体。接管期间仅离线fresh IK/载物规划；模型评测不调用该入口。

六份专家纠正均完整抓放通过，各自raw64独立回放state/env/time最大差均0。载物下放的actual-to-target chord也检查自由物体的实测夹持占位；几何满足释放条件后不再假设物体刚性随爪。物理2ms/控制20ms、Noslip10、夹爪.15Nm、碰撞与关节限位全部保持。实际前缀与纠正各自≤60s、采集wall≤120s，前缀≤3000拍；原前接触≤250拍/5s入口不扩大。

实现新增`collect_policy_recovery.py`、学习状态夹爪组件及其独立训练。五轴ACT L1明确排除夹爪轴，官方可微model forward不改上游源码；裸arm-only checkpoint禁止执行，必须附学习夹爪。夹爪只读相同的归一化state6/env30，二次统计只拟合有效训练行；不接收阶段、时钟或几何开爪规则。训练夹爪时72个ACT状态张量逐项冻结不变，checkpoint保存完整组合，默认旧ACT/MLP训练入口兼容。

| 候选 | 纯策略实际结果 | 可引用产物（同一ignored output根） |
| --- | --- | --- |
| v6 full ACT（旧admission/forward数据） | 11.42s料盘底碰撞，无抓起 | `policy-correction-v6-single-20261001/report.json` |
| v6只训jaw输出行（旧数据） | 抓起并持物20.04s，37.88s盘外失物 | `policy-correction-v6-gripper-single-20261001/report.json` |
| 原ACT+11份guarded学习夹爪 | 持物20.10s，38.02s障碍碰撞 | `policy-correction-v6-classifier-single-20261001/report.json` |
| 11份guarded裸MLP | 12.94s料盘底碰撞，无抓起 | `policy-correction-v6-mlp-single-20261001/report.json` |
| v7五轴ACT+12份学习夹爪，chunk16 | 持物6.06s，完成22.54s后实际腕关节越限；command仍限内 | `policy-correction-v7-decoupled-single-20261002/report.json` |
| 同v7权重chunk8 / chunk1 | 11.82s料盘底碰撞 / 持物71.88s、90s超时，未放置 | `policy-correction-v7-decoupled-chunk{8,1}-single-20261002/report.json` |
| 原ACT+同v7学习夹爪 | 持物2.66s，21s盘外失物 | `policy-correction-v7-frozen-origin-classifier-single-20261002/report.json` |
| v8五轴ACT+13份学习夹爪，chunk16 | 持物60.42s并进入蓝盘范围；89.72s后蓝盘壁/夹爪0.8471mm间距保护停止，未释放/承托 | `policy-correction-v8-decoupled-single-20261002/report.json` |

这不是严格同数据模型消融：早期v6数据版本不同，v7/v8还同时改变数据与学习选项。只有v7三个执行窗口是同权重/同参考/同输入与固定标签支持的有界窗口对照。所有失败都保留原权重、实际command、逐拍诊断及报告。部分monitor的最后安全快照false不覆盖外层SafetyStop；安全停止一律任务失败。

独立CPU诊断未发现arm_delta chunk锚点错位。v7第900拍已实持1.52s，附近专家状态原本存在，但低速实际持物输入的动作缩小；只离线替换物体速度能改变预测，不能作为在线修复或唯一因果。新纠正因此覆盖actual-policy早期持物和之后的路线。v8第2500拍仍在蓝盘接近corridor、实持31.94s/抬高35.768mm；fresh纠正742valid，独立3242步回放差全0，才纳入第14条。

实现完整201项测试通过，无跳过，55.101s；日志`output/late-recovery-v7-final-tests-20261002.log`。这些是源码及绑定产物边界证据，不替代纯策略放置；这是release分支之前的历史测试；下文新212项覆盖最终源码。独立审计入口：`late-recovery-v7-independent-audit-20261002.json`、`late-recovery-v8-data-audit-20261002.json`、`late-recovery-v8-policy-audit-20261002.json`、`late-recovery-v9-data-audit-20261002.json`，均同ignored output根。

v9已完成：从v8 arm checkpoint `00da58926f51a1408f73f3b5dc4280a895c8ef90de080c21f4a9affef51bdcd5`初始化，保持原四份统计、robot-only mask，14档案、batch64/lr1e-5、优化循环目标≤120s，实际73step/120.152s，整次405.668s；组合夹爪后27.08s盘外失物，持物11.22s。独立采样重算：只覆盖4166/25107起点，但chunk标签并集23501/25107；不将起点覆盖混称为动作标签覆盖。GPU一时低频观测不证明失物的唯一原因。20+20/视觉/实体/云端未启动。

v9实际来源为`output/policy-correction-v9-arm-fit-20261002/report.json`、`policy-correction-v9-decoupled-fit-20261002/report.json`、`policy-correction-v9-decoupled-single-20261002/report.json`及`late-recovery-v9-policy-independent-audit-20261002.json`；精确argv为`policy-correction-v9-*-arguments-20261002.json`，14份数据清单`policy-correction-v9-training-datasets-20261002.json`。现场旧22项tracked遗留/index/原MJCF哈希保持，硬件Issues/Handoff仍由根Codex接续。


### 2026-10-02 末端释放纠正与纯策略单回合通过

v10在相同14档案上从v8五轴权重改用CPU有界接续，1201step/120.067s优化循环、144.551s全进程；固定初态纯策略抓起且进入蓝盘低位，但52.22s蓝盘左壁与夹爪间距0.9365mm触发原1mm保护。五轴权重SHA `b92adf12f9482467aa927aff1c71e8c94ae2cba6ed878b7743678b52abab57e6`；组合SHA `cb8f8774f7cb7a67c06a910ebe5684e39ff0b9042070088fcbd1d73b75f06d48`。失败与实测轨迹均保留，未降低安全阈值。低位状态重新推理仍预测闭爪，离线probe排除“缓存是唯一原因”，不作唯一因果证明。

从v10真实command执行2517拍，最早进入蓝盘内z=14.478mm且无地板支撑的状态；当前连续双指接触36.46s、历史实抬抓取通过。新增独立`release`离线模式，失去任一指接触或触地即重置当前接触计时；仅接受双指连续≥1s、盘内、10mm≤z<14.5mm、速度≤0.05m/s的安全状态。首valid为actual五轴制动＋开爪0.5，直接释放/承托/安全撤离/静置，不重新规划搬运。专家物理抓放与2914步raw64独立回放均通过，state/env/time差全0。2517步prefix全invalid且expert标签NaN，397条纠正valid；没有恢复NPZ终点qpos、额外沉降或附着物体。采集来源`output/policy-correction-v10-release2517-guarded-20261002/`，回放来源`policy-correction-v10-release2517-guarded-replay-20261002/`。

最终15份共37730raw/25504valid/12226invalid；七份本轮新增18903raw/7280valid/11623invalid，全部专家抓放与各自回放通过。清单`output/policy-correction-v11-training-datasets-20261002.json`。v11只训练独立状态夹爪8608参数，6000step/7.102s、全进程9.950s，CPU batch128/lr0.001/seed0/critical weight5；72个ACT状态张量和原四份归一化逐项保持。五轴ACT实际在14份数据上训练，夹爪在15份数据上训练，不能称官方完整ACT整体通过或ACT整体训练15份。组合checkpoint SHA `f50a14052b48ad1237024a63cebddec032686441be1149c33e4c8bc5d071a007`，位于`output/policy-correction-v11-release-classifier-fit-20261002/policy.pt`。

纯策略正式入口`output/policy-correction-v11-release-single-20261002/report.json`：completed_evaluation，固定初态一个正常回合1988控制拍/39.76s，实持23.10s，物体完全在蓝盘内、盘底支撑、双指释放且低速稳定1s；无安全停止/IK/OMPL/阶段/时钟输入/专家兜底。策略仅state6/env30，robot-only速度mask；chunk16固定当前锚点解码，nearest仅把学习夹爪浮点输出投影到训练标签0.015/0.5，并不读取几何或触发阶段开爪。此为有仿真真值的状态组合策略、同训练参考初态的单回合门槛，不是held-out、视觉、扰动恢复率或真机通过。

可见复验`output/policy-correction-v11-release-visible-20261002/`实际重新运行同一策略，渲染只读状态；全部1988步NPZ数组与逐步diagnostics和首轮完全相同，物理门槛再通过。`render-binding.json`保存checkpoint/两次report SHA与五项一致性；视频995帧/39.8s/25fps/1280×720，ffmpeg全量decode退出0，根Codex人工检查最终蓝盘物体和张爪细图。此复验仍同固定初态，不记作独立泛化批次。

最终源码回归212项/0skip/41.991s，actual exit0，绑定11份真实纠正HDF（旧四v5＋本轮七）与新release replay，前后源码hash相同；记录`output/late-recovery-v11-final-test-result-20261002.json`，精确参数`late-recovery-v11-final-test-arguments-20261002.json`，日志`late-recovery-v11-final-tests-20261002.log`。独立Codex审计`late-recovery-v11-independent-audit-20261002.json`核验数据、冻结权重、阶段隔离和实际落定；它不冒充AGY或ZCODE的新审核。完整汇总`output/late-recovery-single-gates-20261002/report.json`。

S7d-single已通过，S7d批次/S7e视觉继续未完成，20正常＋20扰动、视觉、实体与云端本轮未运行。接续owner根Codex：以本次组合权重与精确argv为基线，下一次先明确分回合/分种子评估范围与通过阈值，不能从1/1同初态提升为85%泛化成功率。权重、训练HDF、NPZ、视频、原始日志与审计只存ignored output；源码/公开文档同步并提交推送既有delivery分支。原现场22项旧变动与独立index/原模型均保留，既有硬件Issues/Handoff保持有效。


### 2026-10-02 S7d 40轮批次核验完成，门槛未通过

用户提供批次结果，根Codex回源实际产物核验，没有重跑40轮、采集或训练。checkpoint仍v11 `f50a14052b48ad1237024a63cebddec032686441be1149c33e4c8bc5d071a007`；[批次报告](../../experiments/colab-twin/output/policy-correction-v11-batch-20261002/report.json) SHA `ca487dd7ffd8e529834390c5ec467d2dbe7ae4e425bb1f732c010db97cc8f4bf`，[精确argv](../../experiments/colab-twin/output/policy-correction-v11-batch-evaluation-arguments-20261002.json)，原始日志及40轮NPZ/diagnostics继续ignored保存。

实际20正常/20扰动全部执行完，正常20/20、扰动3/20（seed20/25/31），双方≥17/20标准未达成。总体安全停止5/40=12.5%，超时8/40=20%，失物4/40=10%；若仅扰动组，分别为25%/40%/20%，分母必须注明。每次扰动实际从3.02s连续10拍/0.2s，五轴目标偏移≤0.02rad，无接触且未抬升；不是外力脉冲，也不保证实际joint displacement等于目标偏移。逐轮wall_s合计309.869s，不推断未记录的全进程耗时。

正常20轮使用同一训练reference/reset、确定性模型，seed只在perturbed时改变目标偏移；全部NPZ字段数组相同。因此只证明同初态可重复执行，不能表述为名义流形闭环稳定性或20种场景泛化。3个扰动方向实际恢复通过，不构成连续吸引域、任意方向或理论稳定性证明。沿用开发知识页“按当前任务选择验收依据”的已采纳原则：执行完成与验收通过分别记，不能扩大已观察范围；来源为Wiki/自动化开发范式与智能体协作.md。

最早失分集中于抓起之前：7个未抓取超时（23/26/27/30/32/38/39）＋4个pick_floor/活动指爪低于1mm余量停止（28/29/34/35），共11/17失败。余量停机不宣称实际碰撞穿透。seed33为place_wall_y_-1/夹爪0.998711mm余量停止，实际hold42.2s、放置仍false。seed21虽然hold74.12s，但终点物体(.18802,.14002,.04209)m未全进入蓝盘、无盘底支撑，不能认作低位待释放；学习策略也没有几何开爪条件门控。

[失物命令核对](../../experiments/colab-twin/output/v11-batch-lost-object-claim-check-20261002.json)：22/24/36在物体盘外高位且已实抓起后，于26.88/25.28/24.00s首次输出开爪0.5；37实抓起后没有开爪command。前3条优先检查学习夹爪在持物状态的误分类与监督覆盖，第4条再检查仍闭爪时的实际夹持/动力学；仅观察时序不能作为开爪单一因果验证，四轮不能笼统归因偏心滑脱。[独立40轮审计](../../experiments/colab-twin/output/v11-batch-independent-audit-20261002.json)16项汇总与40轮逐项核验全部一致，SHA `0e5bcee2706cb7ad42f9b53476079f8cda18892e5e5c68c213ee00951274d5da`。96041次有限command中96036步完成进入NPZ，5条安全失败command保留在各attempt last_command/failure_details；最后保存的安全物理快照不覆盖外层SafetyStop。核验来自独立Codex助手，不冒充新的AGY/ZCODE审核。

后续建议（尚未执行）：保持MuJoCo状态ACT五轴＋学习夹爪和原控制/安全约定，用已有grasp_episode短前接触prefix接口覆盖脉冲结束后的actual-state重新对准，用held离线入口补盘外持续持物闭爪标签。先选少量不同方向/失效类型，前缀保持invalid，专家从真实受扰状态重新求解；每条完整抓放与独立raw64回放通过后才纳入有界微调。此做法参考[DART原论文](https://proceedings.mlr.press/v78/laskey17a.html)的纠偏示范思路，未实现其噪声分布优化，不宣称完整算法复现。原20..39若用于训练则转为已见诊断集，正式复验另留未参与纠正的新扰动种子；旧正常基线检查退化。没有新增模型架构、GPU任务、实体或视觉。

当前S7d-single仍通过，S7d批次执行完成但任务门槛未通过，S7e未开始；owner根Codex。下一次需用户确定是否采用上述小批纠正＋有界微调方向；本次交付为统计复核、解释纠正及项目状态同步。40轮全部产物、17轮失败和v11权重保留，既有现场22项变动/index/原MJCF继续受保护。
