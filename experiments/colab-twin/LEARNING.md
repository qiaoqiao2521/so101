# 有限资源状态学习闭环

从同一份 MuJoCo 转换数据出发，官方小配置 ACT 与三层 Torch MLP 共用输入、绝对关节动作和归一化适配。MLP 不引入 imitation/SB3；官方 LeRobot 自身的 base 依赖仍须安装。三方会审与原始来源见[learning-review](../../plans/colab-digital-twin-20261001/learning-review.md)。

## 数据及动作契约

[learning_data.py](learning_data.py) 定义 `so101-state-transition-v1` 裸 HDF5；这是薄适配格式，不冒充 LeRobot 原生数据集。state6 是六关节实际位置；environment_state30 依次为六关节速度、物体位置/四元数/线角速度、放置目标、障碍中心/半尺寸、两指实际接触力。状态策略使用物体真值；部署视觉策略必须另行替换这些特权输入。

`obs_t → 执行command_t → obs_t+1` 在 2ms 物理步、默认20ms控制周期下对齐，命令在一个控制周期内保持。另存 `action` 专家绝对关节目标与 `executed_action` 实际执行目标；扰动样本 label_valid=false，动作chunk不得跨越无效段或回合。时钟、专家阶段、扰动标志只用于审计，不进入策略。浮点原始列为float64，模型归一化后为float32；旧float32-v1档案兼容读取并标记其存储精度。

观测边界刷新 MuJoCo 派生量，再复制数组，避免新关节位置混入旧物体姿态。依据：[MuJoCo 3.3.7 simulation loop](https://mujoco.readthedocs.io/en/3.3.7/programming/simulation.html#simulation-loop)。

恢复采集可在固定布局的无接触起点或接近段施加有界关节指令。`--perturb-at-fraction`选择接近轨迹进度，`--perturb-offset-rad`指定五轴偏移，`--perturb-duration-s`须为整数控制周期；实际推进后立即记录非零速度，以actualq发出一拍制动标签，再从实际位姿和物体位置重新求IK、复验连接路径。`--reference-route`可复用已通过的参考路线，核对模型、端点及整条碰撞路径，避免混入随机绕行分支。没有直接改执行qpos或给旧轨迹加噪声。正常与恢复成功回合供训练；失败及部分回合保留审计分母。尚未优化噪声分布，因此称“有界扰动恢复采集”，不宣称完整复现[DART](https://proceedings.mlr.press/v78/laskey17a.html)。

学习采集版本`state-conditioned-v3`去掉运动端点的固定等待；在下降时用当前指间中心与物体相对位置触发闭爪，在蓝盘内物体高度低于14.5mm时触发松爪。这些是专家采集规则；策略输入依旧只有state/env，独立物理验收条件不变。

## 环境与运行

Python3.12使用独立learning-venv。固定Torch2.7.1+cu126、torchvision0.22.1+cu126与官方LeRobot提交，安装命令在[requirements-learning.txt](requirements-learning.txt)注释中。官方LeRobot要求NumPy<2.3，学习环境固定2.2.6；不覆盖现有planning/data环境。先按注释预装CUDA wheel，再以 `--no-sources` 安装文件，避免上游默认cu128源覆盖cu126；最后 `uv pip check --python "$SO101_LEARNING_VENV/bin/python"`。

从仓库根目录，使用独立环境的Python执行以下命令。输出目录必须是新目录；全部在 `.gitignore` 排除的output下。空夹是预期非零负例，仍继续保存该档案并用于审计。

```bash
python experiments/colab-twin/grasp_episode.py --place --record-dataset --output experiments/colab-twin/output/train-nominal
python experiments/colab-twin/grasp_episode.py --place --record-dataset --perturb-rad .02 --output experiments/colab-twin/output/train-recovery
python experiments/colab-twin/grasp_episode.py --place --record-dataset --empty-close --output experiments/colab-twin/output/train-negative
python experiments/colab-twin/run_learning.py --dataset experiments/colab-twin/output/train-nominal/expert.h5 experiments/colab-twin/output/train-recovery/expert.h5 experiments/colab-twin/output/train-negative/expert.h5
```

入口顺序：档案审计 → 一回合严格原动作回放 → ACT/MLP资源探针 → 单回合限时训练 → 纯策略抓放 → 满足单回合门槛后20正常+20扰动回合。失败时后层保持not_run，顶层返回非零，每层保留日志和报告。初始化、导入、CUDA预热与5次计算步骤分别计时；“10秒”只限制预热后计算。显存门槛同时使用allocated/reserved，记录当时CUDA空闲区域；不混用它与nvidia-smi物理卡容量。

ACT固定复用[官方配置/实现](https://github.com/huggingface/lerobot/tree/e0d50211ef236143ae867228662b7dfaba554f02/src/lerobot/policies/act)：dim256、4head、encoder2、decoder2、VAE encoder2、FF1024、chunk16、batch16。模型源文件SHA会核验；默认每控制周期重新观察并执行chunk首动作。ACT先通过资源门槛就选ACT；只有其资源/依赖探针失败且MLP探针通过才切MLP。不会因离线loss下降自行宣布任务成功。

入口默认训练上限为200epoch、5000step、120秒中的先到项，可显式改变预算。记录L1、KL、绝对关节误差、训练帧与保存重载差异。没有要求VAE总loss归零；没有单回合物理抓放成功，不启动批量训练或视觉。更多轨迹时先按完整episode划分train/validation，再fit训练集归一化；相邻帧随机切分不能证明泛化。

起步诊断可显式选择`--action-encoding arm_delta --velocity-scale-floor .1 --no-vae --dropout 0`：前五轴标签为相对当前q的偏移、夹爪仍为绝对目标，整段chunk均以起点q编码；执行时还原绝对弧度。HDF5动作契约没有改变。速度归一化最小尺度0.1rad/s只作用于六个qvel列，避免微小速度方差放大在线偏差。关闭VAE/dropout是有记录的确定性诊断变体，未改官方ACT源文件。[官方训练/推理latent处理](https://github.com/huggingface/lerobot/blob/e0d50211ef236143ae867228662b7dfaba554f02/src/lerobot/policies/act/modeling_act.py#L415-L468)。

输入消融默认关闭：`--mask-robot-velocity`将归一化env[0:6]机械臂速度置零；`--mask-object-velocity`将归一化env[13:19]物体线速度3＋自由关节局部角速度3置零。两项独立，训练chunk和推理共用同一适配器，布尔选项及确切索引随checkpoint/报告保存，旧checkpoint缺省false。先拒绝原始及归一化非有限值，再对新数组屏蔽；原HDF5、实际qvel、接触动力学、安全监测和动作不改。归一化零代表原训练均值，不等同于将物理速度置零。初始化允许显式增加屏蔽并记录from/to，不允许静默取消已有屏蔽；`run_learning.py`透传两标志及`--init-checkpoint`。下一项物体速度单变量消融保持已有robot mask、八档案、归一化与预算不变，从`output/policy-recovery-v5-qvel-masked-fit-20261001/policy.pt`初始化并显式增加`--mask-object-velocity`，结果待物理验收。

`--critical-sample-weight 5`对每回合前50帧、invalid间隙后首6帧、夹爪目标跳变附近±8帧加权，连续窗口不越间隙/episode，条件重叠不累乘。默认1保留逐epoch全量permutation；加权模式每epoch有放回抽N次，报告实际抽样数与唯一覆盖。`--train-recovery`使入口用所有合格正例训练，默认仍只用首个nominal。

本轮优先单回合时使用`run_learning.py --sanity-only`；物理通过返回`passed_single_episode_gate`，20+20与视觉保持not_run。诊断入口`diagnose_state_policy.py --checkpoint ... --dataset ... --evaluation ... --output ...`默认CPU/120秒上限，记录起步1/16/50帧、逐阶段误差、速度尺度和保存的在线前20步近邻覆盖；这些统计不能替代抓放验收。

### 显式执行与采集消融

`evaluate_state_policy.py --execute-chunk-steps 16`每生成一个chunk时用起点q一次还原全部绝对目标，再缓存执行16个20ms周期；reset清空缓存。不是每拍将缓存残差重新加到变化的q上。[官方chunk接口/队列](https://github.com/huggingface/lerobot/blob/e0d50211ef236143ae867228662b7dfaba554f02/src/lerobot/policies/act/modeling_act.py#L100-L137)。模型与权重不变，反馈频率降为320ms一次，需另做物理验收；默认1保持旧行为。

`--gripper-training-dataset <全部实际训练HDF5> --gripper-projection clip|nearest`为默认关闭的固定输出适配。哈希集合须精确等于checkpoint训练清单，全部必须合格正例，仅有效标签参与拟合。clip限制夹爪到训练min/max；nearest只接受恰好两个训练标签，以预测最近值选择，正好中点选较小值。只修改第六轴，不读阶段/时钟/几何来选择开闭；NaN/Inf先拒绝。适配参数和来源哈希保存在评测报告，原模型输出、投影后指令、扰动后执行指令在NPZ分别保存，失败指令也保留。pipeline的`--gripper-projection`自动绑定本次真实训练清单；不使用held-out数据来拟合范围。

`grasp_episode.py --place --record-dataset --approach-lookahead-rad .006`启用`state-conditioned-v4-approach-reactive`专家采集：仅approach以actualq在已验证路线上的投影推进，再前视0.006rad的关节路径距离；每拍actualq→目标连线按0.005rad验边，非法即停止。无缓存进度/时钟推进，终点允许1.5mrad静差及低速度，时钟只作失败超时。随后descend/lift/transport/lower仍沿用时间minimum-jerk，metadata明确记载；不宣称整条任务已反应式。此选项不改变默认v3采集或已有非学习仿真。

### 策略偏移前缀与有界权重接续

`state-conditioned-v5-policy-recovery`在同一初始场景真实执行已保存的策略`action`前缀，再从actualq/object重新求IK并接回验证后的参考路线。前缀全部`label_valid=false`，不参与训练；首有效标签是一拍actualq制动，保留当时实际速度，随后才记录专家纠正。NPZ来源SHA、执行周期数、实际恢复状态与参考进度进入metadata/report；这验证专家能从这些偏移恢复，不等于策略自主恢复，也不是完整[DART](https://proceedings.mlr.press/v78/laskey17a.html)。

只允许1..250周期且总时长≤5s，NPZ连续时间戳必须与采集周期一致；本轮20ms对应50/100/200/250拍，即1/2/4/5s。仅在无接触接近段使用：逐拍检查双指接触、物体抬升、五轴command−actualq≤5°、关节限位与actualq→command的0.005rad离散碰撞路径，失败即停止。需同时启用record-dataset和approach-lookahead，不能与额外扰动选项合用；不直接写执行qpos。

以下为仓库根目录的接续模板，使用已有产物和新的输出目录；修改周期数可分别采集四类前缀。

```bash
python experiments/colab-twin/grasp_episode.py --place --record-dataset \
  --reference-route experiments/colab-twin/output/learning-expert-raw64-nominal-20261001/report.json \
  --approach-lookahead-rad .006 \
  --recovery-prefix-npz experiments/colab-twin/output/policy-reactive-v4-chunk16-nearest-20261001/attempt-000-nominal/policy-transitions.npz \
  --prefix-control-cycles 250 \
  --output experiments/colab-twin/output/v5-prefix250-new

python experiments/colab-twin/train_state_policy.py --dataset \
  experiments/colab-twin/output/reactive-v4-nominal-20261001/expert.h5 \
  experiments/colab-twin/output/reactive-v4-startup-plus-20261001/expert.h5 \
  experiments/colab-twin/output/reactive-v4-startup-minus-20261001/expert.h5 \
  experiments/colab-twin/output/reactive-v4-approach-20261001/expert.h5 \
  experiments/colab-twin/output/policy-recovery-v5-prefix50-20261001/expert.h5 \
  experiments/colab-twin/output/policy-recovery-v5-prefix100-20261001/expert.h5 \
  experiments/colab-twin/output/policy-recovery-v5-prefix200-20261001/expert.h5 \
  experiments/colab-twin/output/policy-recovery-v5-prefix250-20261001/expert.h5 \
  --init-checkpoint experiments/colab-twin/output/reactive-v4-state-fit-20261001/policy.pt \
  --model act --action-encoding arm_delta --velocity-scale-floor .1 --no-vae --dropout 0 \
  --critical-sample-weight 5 --learning-rate .0002 \
  --max-epochs 200 --max-steps 7000 --max-wall-s 120 \
  --output experiments/colab-twin/output/v5-warmfit-new
```

`--init-checkpoint`只接续权重和原训练归一化，使用fresh Adam、新计数器/采样随机状态，不恢复旧优化器；不在新增八档案上重算归一化。模型配置、动作编码、速度尺度、物理模型、控制周期及官方ACT源码来源须一致；原训练SHA须属于本次合格训练集合，且不得进入validation。未指定初始化时仍只从当前合格训练行fit统计。沿用[固定官方ACT实现](https://github.com/huggingface/lerobot/tree/e0d50211ef236143ae867228662b7dfaba554f02/src/lerobot/policies/act)，不把训练集拟合写成held-out验收。

## 纯策略验收与止损

[evaluate_state_policy.py](evaluate_state_policy.py) 只从档案取得初始物理快照，不读取专家动作生成控制。step不调用IK/OMPL，模型输入仅state/env。独立监测器依据真实物体抬升、持续双指接触、盘底支撑、完整物体落入蓝盘、松爪和静稳判定成功。安全停止、掉块、未完整施加指定扰动或超时均计失败，保存全部attempt。相同训练快照回放标为重复性检查，不能当作未见场景泛化。

批量正常与扰动成功率各达到85%才标记视觉候选门槛；视觉仍为独立任务，不能机械冻结状态层就保证成功。当前没有相机数据、视觉训练、云端GPU分配或实体机械臂验收。

## 当前实测

2026-10-01本地RTX3050 Laptop物理显存4096MiB：首次官方ACT探针峰值allocated117.59MiB/reserved146MiB，5步计算0.1175s；MLP分别17.53/22MiB、0.00829s。两者资源门槛通过，不代表学习任务已通过。

首轮单轨迹ACT训练3133个有效转换，5000step/26epoch/117.59s；归一化chunk L1由0.91297降到0.03603，首动作MAE0.01160rad；CPU重载差3.58e-7。纯策略在0.52s触发碰撞保护，抓放失败。首轮float32动作回放物理抓放成功、时间与关节一致，但释放附近环境逐帧严格匹配失败；原失败报告保留。随后保存原始float64并统一观测刷新节拍，3133步state/env/time误差均0，严格重放通过。最新完整入口ACT再训5000步，首动作MAE0.01085rad，但纯策略0.36s障碍碰撞停止，40回合与视觉保持not_run。最新结果与可恢复接续见[progress](../../plans/colab-digital-twin-20261001/progress.md)。

后续v4四正例9404帧/9401有效标签，nominal2350步及startup-plus2351步独立raw64重放state/env/time差均0。ACT有界训练13491step/240.013s；同权重默认、chunk16及chunk16+nearest夹爪分别9.74/10.22/10.22s腕限位停止，均未抬升物体。三层MLP同四档案8000step/8.234s诊断后，默认16.08s盘壁碰撞、nearest夹爪9.92s桌面碰撞，也未过门槛。

v5四类前缀的专家恢复全部抓放成功，共9423帧/8823有效标签，600帧策略前缀排除训练。prefix250独立2372步重放state/env/time差均0，3项真实产物检查通过。八档案合计18224有效标签，以上有界权重接续实跑7000step/109.024s，allocated87.053MiB/reserved96MiB；输出`output/policy-recovery-v5-state-fit-20261001/policy.pt`。纯策略`output/policy-recovery-v5-baseline-20261001/report.json`在10.48s腕限位停止，仍无抬升；20+20和视觉未运行。

定向离线探针固定q及其他env，只将六轴qvel由专家值替成在线值，路线转角处腕目标偏移由+.002804变为-.004647rad，专家为+.005230rad；`output/v5-qvel-causal-audit-20261001/`已归档。随后一致屏蔽robot qvel、从v5权重接续八档案，实跑3886step/4epoch/120.039s，allocated87.053MiB/reserved96MiB，权重位于`output/policy-recovery-v5-qvel-masked-fit-20261001/policy.pt`。默认18.64s、chunk8+nearest 52s料盘底碰撞，无抬升；chunk16+nearest真实抓起并持续保持17.56s，但35.2s在蓝盘外首次开爪，35.4s判定payload_lost，完整抓放仍失败。

最新`output/v5-qvel-masked-physical-audit-20261001/release-probe.json`核对chunk边界1760拍的新预测与保存raw_action一致。固定实际q、物体姿态和其他env，仅替换六个物体速度为几何近邻训练值，jaw预测从.401425变为.017844；原始速度置零探针为.018514。实际物体速度与该近邻的归一化L2差分别为线速度105.75、角速度134.03，4/6轴超训练min/max；这是局部敏感性证据，不等同于新归一化屏蔽策略的在线结果。根Codex接续有界物体速度消融及单回合验收；没有增加载物collector，20+20/视觉未运行。全部数据、NPZ、权重、审计与日志仍由Git忽略。

本轮收尾：双速度屏蔽ACT（6657step/120.017s）在14.2s料盘底部碰撞停止；同输入MLP CPU对照也限位失败。训练观察范围clamp的离线探针未修正提前释放，不接入评测代码。最强候选仅证明真实抓取并抬持17.56s，完整抓放**未通过**。完整150项实现/产物测试通过，无跳过。根Codex接续当前[失败门槛与最短采集入口](../../plans/colab-digital-twin-20261001/progress.md)，保留所有权重/数据与失败报告；20+20和视觉未运行。

初始化可复用已验证权重和原统计，并重建Adam。`--mask-robot-velocity --mask-object-velocity --init-checkpoint ...`也可通过`run_learning.py --sanity-only --train-recovery`显式转发；所有来源和掩码随报告/权重保留。权重曾用的训练集合与统计最初拟合的集合分开记录；统计来源必须属于原训练集合，不能把继承统计描述成新数据重拟合。只用于当前状态仿真诊断，不作为永久关闭速度观测的决定。
