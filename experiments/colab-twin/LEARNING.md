# 有限资源状态学习闭环

从同一份 MuJoCo 转换数据出发，官方小配置 ACT 与三层 Torch MLP 共用输入、绝对关节动作和归一化适配。MLP 不引入 imitation/SB3；官方 LeRobot 自身的 base 依赖仍须安装。三方会审与原始来源见[learning-review](../../plans/colab-digital-twin-20261001/learning-review.md)。

## 数据及动作契约

[learning_data.py](learning_data.py) 定义 `so101-state-transition-v1` 裸 HDF5；这是薄适配格式，不冒充 LeRobot 原生数据集。state6 是六关节实际位置；environment_state30 依次为六关节速度、物体位置/四元数/线角速度、放置目标、障碍中心/半尺寸、两指实际接触力。状态策略使用物体真值；部署视觉策略必须另行替换这些特权输入。

`obs_t → 执行command_t → obs_t+1` 在 2ms 物理步、默认20ms控制周期下对齐，命令在一个控制周期内保持。另存 `action` 专家绝对关节目标与 `executed_action` 实际执行目标；扰动样本 label_valid=false，动作chunk不得跨越无效段或回合。时钟、专家阶段、扰动标志只用于审计，不进入策略。浮点原始列为float64，模型归一化后为float32；旧float32-v1档案兼容读取并标记其存储精度。

观测边界刷新 MuJoCo 派生量，再复制数组，避免新关节位置混入旧物体姿态。依据：[MuJoCo 3.3.7 simulation loop](https://mujoco.readthedocs.io/en/3.3.7/programming/simulation.html#simulation-loop)。

当前恢复采集只在固定布局的无接触起点施加有界关节指令，真实推进0.2s，再从实际位姿和物体位置重新求解、复验路径。不是直接改执行qpos或给旧轨迹加噪声。正常与恢复成功回合供训练；失败及部分回合保留审计分母。尚未优化噪声分布，因此称“有界扰动恢复采集”，不宣称完整复现[DART](https://proceedings.mlr.press/v78/laskey17a.html)。

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

ACT固定复用[官方配置/实现](https://github.com/huggingface/lerobot/tree/e0d50211ef236143ae867228662b7dfaba554f02/src/lerobot/policies/act)：dim256、4head、encoder2、decoder2、VAE encoder2、FF1024、chunk16、batch16。模型源文件SHA会核验；每控制周期重新观察并执行chunk首动作。ACT先通过资源门槛就选ACT；只有其资源/依赖探针失败且MLP探针通过才切MLP。不会因离线loss下降自行宣布任务成功。

训练上限为200epoch、5000step、120秒中的先到项。记录L1、KL、绝对关节误差、训练帧与保存重载差异。没有要求VAE总loss归零；没有单回合物理抓放成功，不启动批量训练或视觉。更多轨迹时先按完整episode划分train/validation，再fit训练集归一化；相邻帧随机切分不能证明泛化。

## 纯策略验收与止损

[evaluate_state_policy.py](evaluate_state_policy.py) 只从档案取得初始物理快照，不读取专家动作生成控制。step不调用IK/OMPL，模型输入仅state/env。独立监测器依据真实物体抬升、持续双指接触、盘底支撑、完整物体落入蓝盘、松爪和静稳判定成功。安全停止、掉块、未完整施加指定扰动或超时均计失败，保存全部attempt。相同训练快照回放标为重复性检查，不能当作未见场景泛化。

批量正常与扰动成功率各达到85%才标记视觉候选门槛；视觉仍为独立任务，不能机械冻结状态层就保证成功。当前没有相机数据、视觉训练、云端GPU分配或实体机械臂验收。

## 当前实测

2026-10-01本地RTX3050 Laptop物理显存4096MiB：首次官方ACT探针峰值allocated117.59MiB/reserved146MiB，5步计算0.1175s；MLP分别17.53/22MiB、0.00829s。两者资源门槛通过，不代表学习任务已通过。

首轮单轨迹ACT训练3133个有效转换，5000step/26epoch/117.59s；归一化chunk L1由0.91297降到0.03603，首动作MAE0.01160rad；CPU重载差3.58e-7。纯策略在0.52s触发碰撞保护，抓放失败。首轮float32动作回放物理抓放成功、时间与关节一致，但释放附近环境逐帧严格匹配失败；原失败报告保留。随后保存原始float64并统一观测刷新节拍，3133步state/env/time误差均0，严格重放通过。最新完整入口ACT再训5000步，首动作MAE0.01085rad，但纯策略0.36s障碍碰撞停止，40回合与视觉保持not_run。最新结果与可恢复接续见[progress](../../plans/colab-digital-twin-20261001/progress.md)。

根Codex负责接续。最近问题是离线动作误差与在线状态漂移、起点/接近恢复分布不足；先检查并补覆盖这些证据，再决定训练预算。不要跳过单回合物理验收直接扩容GPU或长训。
