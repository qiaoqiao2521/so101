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
