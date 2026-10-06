# 有限资源仿真学习闭环

从同一份 MuJoCo 转换数据出发，官方小配置 ACT 与三层 Torch MLP 共用输入、绝对关节动作和归一化适配。MLP 不引入 imitation/SB3；官方 LeRobot 自身的 base 依赖仍须安装。三方会审与原始来源见[learning-review](../../plans/colab-digital-twin-20261001/learning-review.md)。

## 2026-10-06 学习支线暂停新增训练

用户已选择稳定自主抓放为主线：视觉定位＋已有IK/OMPL，ACT保留研究支线。当前A/B原门控失败与全部权重保留；原七项动作拟合指标仅诊断，不能当工程抓放的必要条件。暂停同配方加权/补训，也不自动追加新模型换图探针。

方法审查确认：h0残差统计用于全16槽，尾槽std约为h0的21–22倍；当前masked L1不能据此推出同倍数梯度放大。四相关示范没有独立验证选模。未来恢复学习前需预置独立数据分组、动作/预训练基线、h0与chunk分开报告、选模及总预算。详见[方法审查与新主线](../../plans/colab-digital-twin-20261001/method-review-20261006.md)。本轮仅CPU只读审核，无新增训练/物理。

## 2026-10-06 Colab已有local-balance：最终仍未过起步门控

2026-10-06 现有local-balance已透传Colab CLI并完成唯一L4训练：5000步/173.028s优化、峰值332MiB，权重回收且实例已实际释放。B2115五轴方向全对但首帧幅度不足；最终B5000首帧pan/flex/roll反向，原七门控失败四项，未启动物理或补训，S7e仍未过。

B2115原七项仅首帧幅度失败；B5000首帧pan/flex/roll反向、首10拍elbow投影0.481135低于0.5。相较A5000，h0三轴MAE改善、lift/elbow退化；不从平均拟合推出起步可执行。B同轮2115→5000并非单调改善，快照仍仅诊断。

已有采样开关通过`run_vision_colab.py --local-balance`显式启用，默认A保持；实际局部起点696/693、raw0/1各350/346，有效动作槽11136/9965。85项CPU测试与1549项独立算术核验通过，0物理/补训。

根Codex保留云端A/B两级权重；下一最短候选是冻结B2115/B5000、固定q0替换真实起步/收尾RGB，核对起步回退是否伴随图像动作区分减弱。本轮未执行换图探针；不凭本轮增加步数、改采样权重/主干/损失或以快照替代最终候选。 [报告与等步数图](output/vision-colab-balance-20261006/REPORT.md)、[完整进度](../../plans/colab-digital-twin-20261001/progress.md#2026-10-06-colab现有local-balance完成最终门控未过)。以下保留前次检查及当时的接续候选。

## 2026-10-06 冻结云端模型：图像响应仍不足以区分起步与收尾

2026-10-06 已冻结同次Colab的2115/5000步模型，固定q0替换真实起步/收尾RGB，完成24次原runner前向。最终换图h0五轴差0.017197µrad，仅为6mrad专家目标差的0.000287%；两图输出均更近收尾参考，未产生起步所需区分。同图重复及原保存首帧全chunk差0，源码/权重/输入不变，0训练/物理/云端分配，S7e仍未过。

同次2115步快照响应0.001599µrad、5000步0.017197µrad；倍率增加不代表任务区分成立。最终起步图输出距起步目标5.699520mrad、距收尾参考0.386042mrad，换成收尾图几乎不变，jaw都open0.5。仅在该q0与两幅图上成立；q_end距q0为0.137mrad，反事实输入不产生新专家标签，末帧h1–h15只分析输出响应。

下一训练变量选已有local-balance采样开关：与本轮A保持同Colab L4、5000步/600秒优化上限、2115诊断快照、四RGB、FP32/batch8/seed0/fresh Adam和原七项门控，仅开启近q真实起步/收尾1:1均衡。原B2115曾改善部分轴但肘轴退化，故这是等步数单变量验证，不是已证实修复。本轮未启动训练或改生产源码；执行前需在现有云端worker显式透传开关并验证默认A不变，不扩大预算或同时改主干/损失。

[协议、图与原始结果](../../plans/colab-digital-twin-20261001/progress.md#2026-10-06-冻结云端模型起步收尾图像动作辨别)。以下保留历史结果，不用其图像响应替代新模型实测。

## 2026-10-06 Colab L4完成5000步，原起步门控仍未通过

本轮实际通过CLI上传四份原RGB HDF、核对内容哈希，在L4独立Python3.12环境完成官方LeRobot源码核验、5步CUDA/batch8预检和唯一5000步训练。优化171.180s，FP32、startup5、seed0、fresh Adam、模型/归一化/损失均保持；峰值reserved332MiB，保存重载差0。第2115步快照`bd8749b8…`仅诊断，最终`ea548c31…`才是准入候选。全部产物回收校验通过，实例已unassign；计费额度消耗未读取。

同一云端训练2115→5000步，前150条专家观测h0逐轴MAE（mrad）由`[0.511566,0.622766,0.156705,1.163642,0.577296]`降为`[0.276773,0.045201,0.095949,0.726564,0.340449]`。首10拍错误方向从14/50个轴观测降至1/50，但剩余错误就是首帧腕旋；首帧其他四轴预测/专家delta比仅`0.0801/0.3636/0.2089/0.0668`，腕旋为`-0.00650`。原7项门控仍失败3项（首帧方向、首帧幅度、首10拍同向），不能由平均改善放行。

新入口见[README](README.md#colab-gpu-视觉训练2026-10-06)。`run_vision_learning.py`默认120秒保持，只有显式`fit --extended-fit-budget`接受最多600秒；所有其他阶段和物理判据不变。云端入口固定一次5000步或600秒先到即停、2115步诊断快照，无自动补训或物理回合。

已回收权重在本机严格源码绑定后，各150次batch1/no_grad冻结前向；300次共12.062s内部计时，0优化/渲染/积分。对照限定为本次seed0训练进程的两个时间点，不证明全局收敛、图像语义改善或抓放泛化。历史本地2115与本次云端2115数值不同，不视为跨设备逐位确定复现。完整链路、首帧与逐槽证据见[进度与原始报告](../../plans/colab-digital-twin-20261001/progress.md#2026-10-06-colab-l4完成5000步原起步门控仍未通过)。S7e仍未通过；下一候选先冻结新模型检查起步/收尾局部动作辨别，尚未执行。

## 2026-10-06 startup5等2115步对照完成，原离线门控仍未通过

唯一新A采用原startup5、不启用local-balance，从头训练2115步/119.205s优化，峰值332MiB、重载误差0；复用原B的2115步权重。A前150条专家观测肘轴h0同向率100%、MAE0.206395mrad，B为40%/1.090709mrad；B其余四轴h0 MAE更小。A首帧肘幅仅专家0.686%，原7项门控仍有3项失败，未进入物理回合。

原5步资源预检通过；唯一A训练达到2115步上限，未延长120s优化预算。A/B数据、源码、归一化、模型与初始化方案、seed、优化器核对一致，但完整池末batch仅5行：两组均16917个起点，raw<50分别465/737次，不能把等步数写成等样本曝光或逐位确定性证明。B不重训、旧3126仅作次级参考。

原7项门控A通过4项；首帧幅度、首10拍肘/腕旋投影、前150拍腕俯仰MAE不退化三项未过。646项独立CPU审计通过。等步数比较已完成，已消除旧3126与2115步数不一致这一项混杂；单seed加历史B仍不足以证明唯一因果或采样普遍优劣。前置肘轴逐槽/覆盖只读审计也已完成：不是完全漏采，近q邻域未发现肘轴正负标签竞争。root保留两份失败模型与原阈值；接续应据五轴逐槽误差选择下一项最小验证，尚未决定或执行新的训练。S7e仍未通过，本轮止于离线，不补训B3126、不改安全界限。 [完整数值与原始来源](../../plans/colab-digital-twin-20261001/progress.md#2026-10-06-startup5等2115步对照完成原离线门控仍未通过)。以下记录保留各阶段当时状态。

## 2026-10-06 真实近q局部1比1采样已实施，原离线方向门控未过

局部1:1采样已接入并完成唯一有界训练：同四档、原归一化/模型/损失，2115step/120.033s，峰值332MiB、保存重载误差0。首帧pan/flex/roll改为同向，但elbow反向且首10拍全反向，原离线门控未过；固定q换图h0差仍仅4.429µrad。没有物理回合或补训，S7e仍未通过。

以nominal raw0 q6为锚、六轴L2≤0.01rad，真实approach起步2行与settle收尾300行在原8997池内均衡155/155，组外位置和值逐项保持。新增fit-only `--local-balance`须与 `--startup-weight 5`联用；默认旧行为保持，stage不进入策略。8797行归一化、chunk16/padding、六轴损失和随机初始化/Adam保持。完整池1:1只是chunk起点数，实际墙钟截断后局部291/285次、有效动作槽4656/4030。

40项相关CPU检查通过；新源码资源5步通过。原3126同一步数快照未到达，只有最终2115步模型，不补训或选择性换checkpoint。肘轴首帧+0.374473mrad，专家−0.947236mrad；前150拍肘轴MAE1.090709mrad，劣于原门控基线0.606118。其余首帧四轴方向/比例过关也不能替代五轴整体要求。同q换图仍没有所需动作切换，无法认定监督竞争已解决。

root保留默认均匀与原startup5行为；新局部均衡需显式 `fit --startup-weight 5 --local-balance`。本轮结果不支持仅靠局部起点均衡已解决起步/收尾辨别，且实际步数不同于旧3126，不能作等步数单变量因果结论。下一最短候选为只读核肘轴前150拍的逐槽拟合与局部抽样覆盖，区分早期输出偏差和覆盖变化；尚未执行，不自动追加训练、改主干或启动物理。 [原协议、完整数值、执行及审计](../../plans/colab-digital-twin-20261001/progress.md#2026-10-06-真实近q局部1比1采样已实施原离线方向门控未过)。以下日期段保留当时状态。

## 2026-10-04 逐层探针：视觉特征有响应，h0动作仍弱

同冻结8d4db/q0/两RGB，唯一12次前向：原调用A/B、hook交替4对、移除hook后A/B；原runner execute1/reset/no_grad/CUDA float32/threads2，外层硬60s，实际exit0/内部3.694s。hook复制原激活且返回None，全部12输出、真实模型输入与前次保存数组逐位一致，8次hook同图激活重复差0；没有训练、EGL渲染或物理推进。

同层对称relative L2：ResNet18 feature map 3.5773%、图像投影3.5952%、encoder图像位置输出0.9982%、decoder h0 0.05974%、归一化五轴h0动作头0.9819%；反归一化五轴残差差0.3979%（实际L2 3.960µrad）。层间尺度和线性投影不同，不能把这些百分比当作逐层信息损失率或归因依据。

q6、latent/q输入token、位置嵌入固定；encoder q位置输出仍有0.4942%差异，是图像参与self-attention混合的结果。4×4空间feature map中每格相对差约2.98–7.87%，感受野较宽，不把特征格当作精确方块定位图。主干并非对此图像对完全无响应，但非零特征差不证明已学会语义辨别；h0行为仍接近收尾，首帧三轴反向、夹爪open。

下一单变量候选：对真实起步/收尾近q帧局部1:1配对均衡采样，其余有效帧、模型、归一化、chunk和损失保持；先检验局部监督竞争，不生成固定q的伪专家标签。候选尚未实施，不额外做特征替换或自动重训；仍以已有离线方向准入为前置，再评价物理抓放。[协议、原激活和独立复算](../../plans/colab-digital-twin-20261001/progress.md#2026-10-04-冻结模型逐层视觉响应探针)。

## 2026-10-04 固定q6换RGB：局部图像响应弱，起步方向未纠正

冻结当前8d4db权重与nominal frame0 q6，仅切换frame0起步/2349收尾RGB，经原 `VisionPolicyRunner.predict` 执行12次交替前向，每图6次；batch1 CUDA/float32/no_grad/threads2、每次reset、execute1，仍预测16槽但本轮主要比较h0。没有训练、渲染或物理积分。

同图各6次全chunk输出重复差0，起步图输出与原保存首帧预测差0。6对五轴h0差L2均3.960µrad、最大轴3.228µrad，仅为对应专家目标6.000mrad差距的0.066%。两种图像下肩平转/腕俯仰/腕旋仍与起步专家反向，夹爪raw相差89.69µrad而投影均open0.5。起步图目标距起步标签6.039mrad、距收尾标签0.414mrad，收尾图也近收尾标签0.413mrad。

因此这对整幅图像有可重复的微弱影响，未形成任务所需的起步动作切换；不能宣称全局视盲、只归因方块像素、确定唯一瓶颈或认定抓放通过。收尾图配固定q0是局部反事实，原收尾q与q0相差0.137mrad，收尾标签比较只作描述。捕获输入的CPU拷贝属于仪表路径，latency不用于实时性能判断。

[逐轴数值、协议及独立复算](../../plans/colab-digital-twin-20261001/progress.md#2026-10-04-固定q6起步收尾rgb反事实检查)。后续逐层冻结诊断已执行，见本页首节；S7e方向/抓放仍未过。

## 2026-10-04 首0–9拍：标签正确，首帧输出偏近收尾

只读检查复用同步HDF、旧/新保存预测与训练访问记录；没有新模型前向、训练、渲染或物理推进。62项标签/时序及86项独立方法/结果核验通过：首10 nominal标签全有效、五轴专家方向均为 `+ − − − −`，另外三档raw0–9无效且排除。新/旧h0目标与raw action最大差0，当前q重算专家路线目标误差6.94e-18rad；没有发现轴序、符号或一拍错位。

方向错误集中frame0的pan/flex/roll和frame1的flex，frame2–9在专家观测上的五轴方向全对。frame0 q6半径0.01rad的366条有效近邻包括2 approach、64 retreat、300 settle；训练中这些行作为chunk起点分别出现27/178/834次，不能解释为完整标签曝光或梯度份额。frame0预测的五轴绝对目标距起步标签6.039mrad、距settle frame2349标签0.414mrad。

同一相机的两帧q6差0.137mrad（L2），但物体位置从红盘到蓝盘相差269.17mm；RGB有203/16384像素不同，变化像素MAE23.31uint8、整图MAE0.289被背景稀释。所核首10拍近邻中，完整raw q6＋RGB和float32归一化q6＋RGB均未找到矛盾标签。局部辨别不足/收尾监督竞争是候选，当前不能确认模型忽略方块或视觉特征混叠。

[数值、图像和来源](../../plans/colab-digital-twin-20261001/progress.md#2026-10-04-首09拍观测与动作标签只读核验)。当时提出的同q换图候选已接续执行，结果见本页首节；视觉抓放仍未通过。

## 2026-10-04 起步5倍采样实训：离线方向门控未通过

用户授权同四RGB/seed0/随机初始化/fresh Adam，仅启用 `fit --startup-weight 5` 的唯一120秒训练。当前源码新五步CUDA资源预检batch8通过，峰值reserved332MiB；3126step/120.002s优化，CPU保存重载误差0。实际25002次chunk起点抽样中起步702次，第0帧13次；两个完整8997项采样池及第三池部分抽样，归一化仍对应8797唯一有效行。

在新模型预测前，记录保守的下发诊断条件：首帧五轴方向一致且预测/专家delta比在0.5–1.5；首10拍逐轴同向100%及有向投影在0.5–1.5；前150拍逐轴h0 MAE不劣于旧保存数组、向专家整体投影不劣、起步夹爪保持open。这是本轮诊断准入，不替代原物理抓放/安全判据。

唯一150次batch1/no_grad CUDA离线前向完成：前150五轴平均MAE由0.638→0.346mrad，但首帧肩平转、腕俯仰、腕旋仍反向；首10拍同向率分别90%/100%/100%/80%/90%。门控未过，**没有执行新物理回合，也没有追加训练**。旧d4db失败证据保留，S7e任务未通过。

旧NPZ为batch8/inference_mode，新诊断为batch1/no_grad；相同120秒本轮3126步、旧1312步，不能把改善唯一归因采样。参数、逐轴表与独立审计见[本轮进度](../../plans/colab-digital-twin-20261001/progress.md#2026-10-04-起步5倍采样唯一训练离线方向门控未通过)。

## 2026-10-03 视觉 ACT 起步采样开关

用户选定 `label_valid & (raw_frame_index < 50)` 的 **chunk 起点采样权重5倍**。在下方 `fit` 命令中显式追加 `--startup-weight 5`；默认值1保留原均匀排列与随机数序列，其他阶段拒绝非1权重。

`VisionDataset` 先排除无效标签，并保留原始帧号。启用5倍后，每轮将有效原始帧0–49的索引放5份、其他有效索引放1份，再用训练种子洗牌；归一化仍只在唯一有效数据集上拟合。它不改变动作标签、chunk边界、损失、模型输入、推理、物理限位或优化预算，也不把每档案的前50个有效纠正样本当作起步。

当前四档8797个有效起点中仅nominal的50行命中，采样池扩展为8997项，完整池的起步份额为250/8997（2.779%）。120秒/步数上限可能截断采样池，不能将理论份额当作实际抽样比例或梯度份额。报告和checkpoint的 `training_sampler` 保存原始帧规则、逐档命中、采样池大小、种子及成功优化更新的实际起点/起步次数，完整采样池轮次与唯一数据轮次分别解释。

两份生产源码仍由资源报告与checkpoint严格绑定。新源码须先生成新的五步资源探针报告，不能沿用旧报告；旧d4db模型及报告继续对应基线提交 `4a1cf3b51d768b5f8004c62ce0a02a2522c4db18` 的源码，不放宽哈希校验。本轮只接入并验证采样改动，未运行新资源探针、训练或物理回合；接续证据见[当前进度](../../plans/colab-digital-twin-20261001/progress.md#2026-10-03-视觉起步chunk采样5倍接入)。


## 2026-10-02 当前路线：A止损后启动单相机视觉B

**2026-10-03 冻结chunk1完整单次抓放0/1，因关节限位安全停止。** d4db/nominal/execute1/原精度线程、wall120s/sim90s，仅一次原evaluate，无预热、重训、重试。实际580指令/5800积分，579完整轨迹；absolute12.60s/elapsed11.60s的第580次step已积分但因wrist_flex实测越过原上界0.002155°而未返回，无新轨迹行/monitor更新。下发目标仍在ctrl范围内；580次命令都未闭爪，579保存诊断双指力为0，原抓持/落盘判据不成立。原task与外层均exit1/safety_stop，外层13.599s；后578完整周期中位11.336/P95 13.063/最大15.873ms，首402.449ms单列，不把它删掉后宣称全部过20ms。173项物理＋93项计时独立审核通过，原250轨迹/诊断与前100RGB相同。h0专家观测低误差不能保证rollout安全或抓取；只读接近段轨迹/限位余量比较为下一候选，未执行，未验证接触阶段和长期50Hz。[原物理报告与审计](../../plans/colab-digital-twin-20261001/progress.md#2026-10-03-b冻结chunk1完整回合关节限位安全停止抓放未通过)。

**2026-10-03 真实循环100拍计时完成：后99拍低于20ms，完整50Hz仍未验收。** 同d4db权重、execute1、原float32/no_grad/后端/线程，唯一调用原evaluate，100拍/2sim/原wall60s/outer hard90s，无预热或重试。全100cycle中位11.757ms、最大342.899ms；仅首拍超过20ms，其中predict326.779ms。后99拍中位11.742/P95 12.919/最大14.142ms，0拍超过20ms。全100渲染/预测/step/monitor中位1.132/6.828/3.717/.004ms；step含观测、积分与诊断，不能重复相加。旧chunk1前100状态/动作/时序和诊断均差0，原源码/参数不变，没有再训或精度修改。原task保持exit1/simulation_time_limit/not_passed，计时诊断exit0；只覆盖接触前2sim，完整抓放与长期50Hz待验收，历史持续慢仍未定位。[区间、计数与独立证据](../../plans/colab-digital-twin-20261001/progress.md#2026-10-03-b真实循环100拍计时热态短前缀低于20ms历史慢因仍未知)。

**2026-10-03 前序同输入静态EGL/CUDA对照完成，完整闭环50Hz仍未验证。** 同一冻结q6/RGB与d4db权重，4次cold/warm后A8→静态render+predict8→close后A8，唯一28前向/8渲染/1次mj_forward/0积分，外层6.532s。三个原predict组中位6.485/6.833/6.412ms；B完整两段中位7.935ms、最大15.163ms。首冷377.195ms单列，不能解释历史250次持续慢。B渲染后立即原predict，不插CUDA Event/getter/sync，模型始终使用同一存档画面；独立275项数组核验确认28动作、8画面及静态状态差0。未重训、改精度/线程/模式，也没有物理任务回合；没有复现历史402ms，不证明渲染永远无影响或实际整环50Hz。当时提出真实物理循环候选，现已接续本页首段的短前缀计时；[参数、表格与本机证据](../../plans/colab-digital-twin-20261001/progress.md#2026-10-03-b同输入egl与cuda静态对照未复现持续慢调用)。

**2026-10-03 前序离线计时：热态原predict约8ms，原仿真402ms原因未复现。** 冻结权重、batch1/q6+RGB/float32张量/现有no_grad及默认后端，唯一29次离线前向、外层6.334s；首冷调用400.374ms，12次后续原调用中位8.229ms，12次仪表调用中位7.073ms，12组成对raw/action差严格0。仪表更短不证明优化，因为固定原先/仪表后顺序仍受热态与调度影响。CPU重排0.025ms、D2H含等待0.042ms，未发现当前热态持续百毫秒的预处理/回传瓶颈。没有EGL/物理/训练，不能以此解释原连续250次慢调用或证明整环50Hz；实际线程8/8和GPU组间快照仅本轮事实。[阶段表、原trace与归因边界](../../plans/colab-digital-twin-20261001/progress.md#2026-10-03-b离线耗时拆分热态原调用约8ms原仿真慢因仍未知)。当时提出EGL/CUDA路径候选，后续实际结果见本页首段；未改变推理模式、精度或线程，未启动chunk4/扩大预算。

**2026-10-03 最新单参数复验：chunk1被运行时间阻断，抓放效果未评定。** 用户授权的唯一回合保持d4db权重、初态、相机与物理标准，只将`--execute-chunk-steps 16`改为`1`。原120s墙钟上限下仅完成250拍/5.00s仿真，未闭爪/接触/抓起，actual exit1、wall_time_limit；无安全停止不等于任务通过。250次预测回调中位402.075ms/P95 475.068ms，250/250超过20ms；当前配置没有达到真实50Hz，不能由短执行窗口推出实时能力。模型仍预测16拍，首拍重观察/锚定的抓放收益尚无完整回合证据。独立37项轨迹及148项计时核验通过；无新增训练、第二回合或源代码修改。Torch峰值allocated74.934/reserved102MiB不包含EGL/驱动/其他进程。下一候选先诊断运行耗时，不从本次截断推断视觉表征失败；[完整记录与本机来源](../../plans/colab-digital-twin-20261001/progress.md#2026-10-03-b冻结权重chunk1单回合复验因墙钟上限截断)。

**2026-10-03 最新离线诊断：专家闭爪窗口无漏判，五轴后部chunk误差显著。** 冻结新权重在四份8797valid专家观测上预测，旧权重在原2350valid上对照；不向predict输入专家动作，不是autoregressive teacher forcing。首次闭爪至接触436/436预测闭爪，nominal逐专家观测扫描在10.74s已预测闭（不是线上67.20s的复现）；同nominal全chunk五轴MAE旧1.777/新6.383mrad，接触前第1拍新0.566mrad、第16拍25.935mrad。低位0–30mm539valid；q6/RGB严格近邻闭爪648对无jaw冲突，不能确立普遍“动作平均”根因。离线诊断提出同权重`--execute-chunk-steps 1`候选（320→20ms重观察/锚定），当时未执行；后续唯一物理复验的运行时间截断结果见本页首段。不承诺h0在偏离专家观测后仍可恢复。全量指标、图与独立审计见[离线诊断](../../plans/colab-digital-twin-20261001/progress.md#2026-10-03-b四档案离线拟合与监督一致性诊断完成)。B仍0/1，该离线诊断新增训练/物理回合/渲染均0。

**2026-10-03 最新结果：四档案RGB闭环已执行，纯视觉抓放仍0/1。** 三新增EGL RGB及各独立raw64回放全通过，合旧nominal8797valid/661invalid；严格接触前1979valid。新4数据资源batch8/5step/332MiB通过；现有入口从随机权重唯一训练1312step/120.045s优化、同CPU重载误差0。正常纯视觉4500拍/90s未抓起超时，无安全停止；首闭爪67.20s、参考点XY差19.94mm，两指力全0，接近表现未改善。原源码/旧模型保留，未再训/跑回合或使用40..59。前轮RGB响应仅适用于旧权重，新权重未做该探针。来源、完整时序与下一离线候选见[本轮progress](../../plans/colab-digital-twin-20261001/progress.md#2026-10-03-b四档案rgb闭环执行完成纯视觉抓放仍未通过)。

此前2026-10-02三项只读诊断已完成：旧B首闭爪33.00s、IK参考点XY偏差4.49mm；固定指接触但活动指全程无接触力，实际合拢时手臂已抬高，未实抓起。固定q6替图确能改变部分输出，尚不能证明方块定位或视觉纠偏。21份成功档案仅1份已有RGB；建议先选起步/接近/下潜4份共8797valid（新增导出3份），不是全量长训。诊断未训练、导出或运行新物理回合，B仍0/1。时间对齐图、精确来源与局限见[最新诊断](../../plans/colab-digital-twin-20261001/progress.md#2026-10-02-b只读几何与rgb依赖诊断完成)。

用户决定最后一次状态五轴接续失败便转B。A三条实际纠正/零误差回放合格，唯一1262step/120.0608s arm训练后组合原v11旧夹爪；正常seed0抓起/持物74.64s，90s超时未放置，首次失败即停止。四个已见扰动探针、20+20和留出40..59未跑，v11原状态基线仍正常20/20、旧扰动3/20；S7d整体未通过。原state格式、统计和权重保留，不将转B作为旧门槛通过。

[learning_vision.py](learning_vision.py) 与 [run_vision_learning.py](run_vision_learning.py) 是复用当前官方LeRobot ACT的薄视觉入口。模型仅接收 `observation.state` 六关节位置与 `observation.images.workcell` 固定相机RGB。原 `environment_state`、物理接触真值、clock和专家stage不进入model；它们只供物理环境和独立验收。动作保持五轴chunk-start残差＋绝对jaw，保存归一化并在同一锚点解码；nearest仅映射到专家训练两jaw值，不读取几何或指定开闭时刻。

RGB在 `obs_t`、执行 `command_t` 之前渲染；相机参数固定，不用物体真值跟随。2ms物理/20ms控制，128×128 uint8 RGB按HDF行保存，加载batch才转CHW float32/255。无效标签过滤后chunk不能跨无效段/回合；完整RGB导出再用原raw64动作实际回放，state/env/time必须逐帧严格一致。渲染只缩小画布/阴影/MSAA缓冲，原物理模型、1mm余量和1s蓝盘落定判据不改。

小模型为随机ResNet18＋ACT dim256/4heads/FF1024/encoder2/decoder2、chunk16、no VAE/dropout0；不下载预训练权重或另装框架。128×128里方块较小、抓取时会遮挡，先验真图像覆盖，不假定视觉天然更容易纠偏。依据：[固定官方ACT源码](https://github.com/huggingface/lerobot/tree/e0d50211ef236143ae867228662b7dfaba554f02/src/lerobot/policies/act)、[ACT原论文](https://arxiv.org/abs/2304.13705)。官方实现提供视觉模仿/动作chunking，不提供当前SO101任务的成功保证。

从本目录分别运行（先使用现有独立环境；各输出必须新目录；以下目录仅为示例）：

```bash
SO101_TASK_PY=/home/muqiao/.cache/so101-colab/learning-venv/bin/python

env MUJOCO_GL=egl "$SO101_TASK_PY" run_vision_learning.py export \
  --dataset output/reactive-v4-nominal-20261001/expert.h5 \
  --output output/vision-demo-rgb --device cpu

# 完整导出和原物理回放通过后，实际查看 report 所列 sample-*.png。
"$SO101_TASK_PY" run_vision_learning.py microbenchmark \
  --dataset output/vision-demo-rgb/expert-rgb.h5 \
  --output output/vision-demo-resource --device cuda

# 只有相机已查看、资源报告通过并绑定当前源码/相机/数据后才训练。
"$SO101_TASK_PY" run_vision_learning.py fit \
  --dataset output/vision-demo-rgb/expert-rgb.h5 \
  --resource-report output/vision-demo-resource/report.json --camera-reviewed \
  --output output/vision-demo-fit --device cuda

env MUJOCO_GL=egl "$SO101_TASK_PY" run_vision_learning.py evaluate \
  --dataset output/reactive-v4-nominal-20261001/expert.h5 \
  --checkpoint output/vision-demo-fit/policy.pt \
  --output output/vision-demo-nominal --device cuda
```

本机无OSMesa库，实际EGL渲染通过；export/evaluate分进程，进程退出释放GL后再做资源或训练。资源只试预设batch8五次forward/backward/Adam；OOM或两个峰值任一>3200MiB才最多降一次batch4。不虚称整个启动“10秒”：实际计算、总时间和allocated/reserved各自记录。成功资源报告原文及SHA嵌进checkpoint，加载还核对当前两生产源码、官方源、相机、raw/RGB档案、完整5step witness和峰值；源码改动后旧模型不可静默加载，旧产物仍保留。

训练是fresh Adam/lr1e-4，最多5000step/200epoch/120s优化循环，先到即停止；总时间另含初始化、保存和同设备CPU重载比较。初始模型随机，不承诺单轨迹120s可以过拟合。独立评估最多90s仿真/120s wall，执行chunk16每320ms用新图像推理一次，虽然图像按50Hz采样；不调用IK/OMPL/阶段机/专家，安全停止或超时总计任务失败。训练HDF本身的专家成功、loss下降、保存重载一致都不能代替学习抓放成功。

实际首轮RGB导出2350帧，专家hold25.5s/静稳3.02s，逐帧raw64三项差0；root查看五张sample，独立审核图像、帧号和原raw列全部一致。视觉资源batch8完整5step，总3.025s，allocated309.343MiB/reserved332MiB；CUDA报告总3761.75MiB与物理卡4096MiB分开记录。唯一视觉训练3438step/120.016s、重载差0，但纯策略未实抓起，64.74s蓝盘壁0.912153mm触发原1mm保护，完整任务0/1；232项源码/绑定数据测试通过、0skip。训练与单回合精确结果见[当前progress末节](../../plans/colab-digital-twin-20261001/progress.md)，不能从管线通过推断视觉任务已过。

全部实际argv、HDF、checkpoint、NPZ、图像和日志在Git忽略的output，本机有链接；公开仓库只发布源码与验收记录。接续owner根Codex，原现场22项变动/index/原MJCF保持，无实体/云端操作。

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

### 接近末端与持物纠正

[collect_policy_recovery.py](collect_policy_recovery.py) 是独立离线专家采集器，评测不导入它。先从同一初始快照真实执行策略 NPZ 的 `action` 前缀，最多3000拍且≤60s；纠正另限≤60s，整个尝试的wall预算≤120s。原 `grasp_episode.py` 的无接触≤5s入口保持原限制。

`--mode approach`要求无双指接触/抬升、实际夹爪张开、指间中心在目标上方至少35mm且XY偏差≤10mm；600拍源已进入下降/闭爪，不能冒称接近末端。`--mode held`要求当下双指持续抬持≥1s/≥25mm，未丢块、无盘底支撑、无碰撞。前缀全部invalid且专家标签NaN，首valid标签为实测五轴q制动；实际速度和前一next_obs连续保留。

`--mode release`仅用于离线采集低位松爪纠正：要求此前真实抓起、当前连续双指接触≥1s、完整物体在蓝盘内、无桌面/盘底支撑、物体z在[.010,.0145)m、速度≤.05m/s及原安全检查通过。当前接触时钟独立于已被下降重置的抬升时钟，丢失接触或得到支撑均重置；不能用历史hold时长替代。首valid动作保持actual五轴q并开爪`.5`，跳过运输/IK，再验证实际盘底承托、守卫撤退与静稳。[准入与采集](collect_policy_recovery.py)、[反例测试](test_late_policy_recovery.py)。该规则生成专家标签，未接入策略执行。

接近末端重新求hover/descend IK，持物从实际Cartesian位置连接剩余绕障腿；载物查询只操作独立MjData。完成抓放的专家纠正也必须另跑raw64原动作回放，两个报告都通过后才纳入训练。

```bash
python experiments/colab-twin/collect_policy_recovery.py \
  --reference experiments/colab-twin/output/reactive-v4-nominal-20261001/expert.h5 \
  --prefix experiments/colab-twin/output/policy-recovery-v5-qvel-masked-chunk16-nearest-20261001/attempt-000-nominal/policy-transitions.npz \
  --policy-report experiments/colab-twin/output/policy-recovery-v5-qvel-masked-chunk16-nearest-20261001/report.json \
  --cycles 1700 --mode held \
  --output experiments/colab-twin/output/late-held-new
python experiments/colab-twin/replay_learning_data.py \
  experiments/colab-twin/output/late-held-new/expert.h5 \
  --output experiments/colab-twin/output/late-held-new-replay
```

最新守卫版采集在闭爪下降放置时也验证actualq→command的载物占位连线，直到真实松爪才停止使用夹持占位假设；不是降低碰撞余量或修改执行物体姿态。此前admission/forward档案继续保留，当前训练使用新采集的guarded档案。[采集与下降守卫](collect_policy_recovery.py)、[独立载物查询](placement.py)。

| 当前纠正档案 | 有效专家标签 | 无效策略前缀 | 专家抓放 / raw64独立回放 |
| --- | ---: | ---: | --- |
| 450拍接近末端 | 1956 | 450 | [采集通过](output/policy-correction-v6-450-guarded-20261001/report.json) / [2406步回放通过](output/policy-correction-v6-450-guarded-replay-20261001/report.json) |
| 1700拍持物 | 827 | 1700 | [采集通过](output/policy-correction-v6-1700-guarded-20261001/report.json) / [2527步回放通过](output/policy-correction-v6-1700-guarded-replay-20261001/report.json) |
| 1756拍持物 | 807 | 1756 | [采集通过](output/policy-correction-v6-1756-guarded-20261001/report.json) / [2563步回放通过](output/policy-correction-v6-1756-guarded-replay-20261001/report.json) |
| 夹爪分类策略1800拍持物 | 1089 | 1800 | [采集通过](output/policy-correction-v6-classifier1800-guarded-20261001/report.json) / [2889步回放通过](output/policy-correction-v6-classifier1800-guarded-replay-20261001/report.json) |
| v7组合策略900拍慢抬持物 | 1462 | 900 | [采集通过](output/policy-correction-v7-held900-guarded-20261002/report.json) / [2362步回放通过](output/policy-correction-v7-held900-guarded-replay-20261002/report.json) |
| v8组合策略2500拍蓝盘边缘持物 | 742 | 2500 | [采集通过](output/policy-correction-v8-held2500-guarded-20261002/report.json) / [3242步回放通过](output/policy-correction-v8-held2500-guarded-replay-20261002/report.json) |
| v10组合策略2517拍蓝盘内低位松爪 | 397 | 2517 | [采集通过](output/policy-correction-v10-release2517-guarded-20261002/report.json) / [2914步回放通过](output/policy-correction-v10-release2517-guarded-replay-20261002/report.json) |

七份guarded档案共18903原始转换、7280有效标签、11623无效前缀；与原八份档案合并为15条、25504有效/12226无效帧，共37730原始转换。所有七次回放state/env/time最大差均0并完成抓放；报告明确`learned_policy_evaluated=false`。只覆盖上述同场景实际偏差，不证明扰动泛化。v11五轴ACT冻结于v10的14档案训练结果，仅夹爪头消费15档案。表内报告为本机被Git忽略的证据链接，原始数据、权重和日志不入库。

第五条来自[独立CPU只读诊断](output/late-recovery-v7-held900-offline-diagnostic-20261002.json)：保存状态中最早满足持物准入的边界为874拍，实际采集选择900拍并重新核验双指抬持1.52s、力1.419/1.422N、物体z=.037754m，腕实际1.476133rad距限约.1819rad。该边界在慢抬偏离已出现而尚未危险时接入专家。固定其余观测，仅将物体速度换成近邻训练值后，离线新chunk首动作的elbow/wrist残差由约-.000548/+.000304变为-.002936/+.003119rad，接近专家推进目标；这是假设输入上的敏感性反例，未执行、未加入标签，也不是线上修复。真正新增标签来自actual-state专家纠正及独立raw64回放。

第六条真实执行v8前2500拍后，实际持续持物31.94s、双指1.456/1.457N、物体z=.045689m，无安全停止；从蓝盘边缘当前位姿连接安全通道→盘心→降放，742个有效专家转换完成释放并稳定落盘。3242步raw64回放另行通过，原2500拍全部invalid。证明专家可从这处盘边偏离恢复，不等于v9已自主恢复。

第七条选择v10实际2517拍低位边界：[保存诊断的准入选择](output/late-recovery-v10-release-boundary-selection-20261002.json)后重新执行真实前缀，actual物体(.21463836,.14002259,.01447777)m、当前连续双指接触36.46s、双指1.443/1.444N，无支撑/安全停止。原held入口要求抬升≥25mm，无法覆盖这种准备松爪的低位状态。此处397条真实纠正完成开爪、承托和撤退，稳定3.76s；2517条前缀仍invalid，raw64回放2914步差0。此前[固定v10权重的新夹爪预测](output/late-recovery-v10-release-cache-probe-20261002.json)在2500/2592/2600/2609拍均闭爪，提示低位释放标签缺口；这是离线预测，不能单独证明因果或成功。

`train_state_policy.py --train-gripper-head-only --init-checkpoint ... --no-vae --dropout 0`是显式线性夹爪探针：仅官方ACT输出头第5行可变，fresh Adam零weight decay，保存前逐tensor验证其余参数/缓冲区完全不变。相同输入下五轴输出不变，不保证夹爪变化后的实际臂轨迹不变。默认全模型训练保持原行为。

全模型接续未通过接近段，线性夹爪头也未解决提前释放，因此加入显式的[组合探针](train_gripper_classifier.py)：ACT五轴参数不变，纯Torch夹爪分类网络为36→64→64→16×2。它读取base归一化且已经mask的state/env张量，robot qvel六槽仍为零；自己的输入统计仅fit合格训练行。二分类标签只来自专家实际`.015/.5`绝对目标，padding/无效间隙不计loss。模型不读取阶段、时钟，也没有按盘内位置强开爪的手工规则。

组合权重的`learned_gripper_classifier`及`policy_architecture`明确标明独立头、基础ACT来源、两套统计来源及各自训练SHA；旧权重加载不变。旧ACT训练入口拒绝静默丢弃组合头，要求显式选择基础checkpoint。以下是本机守卫版数据的接续模板，输出仍必须新建：

```bash
python experiments/colab-twin/train_gripper_classifier.py --dataset \
  experiments/colab-twin/output/reactive-v4-{nominal,startup-plus,startup-minus,approach}-20261001/expert.h5 \
  experiments/colab-twin/output/policy-recovery-v5-prefix{50,100,200,250}-20261001/expert.h5 \
  experiments/colab-twin/output/policy-correction-v6-{450,1700,1756}-guarded-20261001/expert.h5 \
  experiments/colab-twin/output/policy-correction-v6-classifier1800-guarded-20261001/expert.h5 \
  experiments/colab-twin/output/policy-correction-v7-held900-guarded-20261002/expert.h5 \
  experiments/colab-twin/output/policy-correction-v8-held2500-guarded-20261002/expert.h5 \
  experiments/colab-twin/output/policy-correction-v10-release2517-guarded-20261002/expert.h5 \
  --base-checkpoint experiments/colab-twin/output/policy-correction-v10-arm-cpu-fit-20261002/policy.pt \
  --device cpu --batch-size 128 --learning-rate .001 --critical-sample-weight 5 \
  --max-steps 6000 --max-wall-s 60 --max-epochs 200 --seed 0 \
  --output experiments/colab-twin/output/gripper-classifier-new
```

分类准确率属于训练拟合；只有独立`evaluate_state_policy.py`实际抓起、搬运、松爪并稳定落盘，才通过单回合门槛。ACT五轴与小夹爪网络组合不能简称“原版ACT已通过”。

### 五轴损失与独立学习夹爪

[train_state_policy.py](train_state_policy.py) 的显式`--arm-only-loss`只对非padding的前五轴计算L1，沿用官方ACT的可微模型forward；不是将整个ACT冻结或只更新五个输出行。前提为兼容ACT初始化、`--no-vae --dropout 0`，不能与`--train-gripper-head-only`同时使用。有限夹爪标签变化不影响五轴损失或参数梯度，NaN/Inf仍先拒绝；未监督的原ACT第六轴必须由独立学习夹爪替换。[梯度及默认分支反例](test_arm_only_training.py)、[夹爪组合边界](test_gripper_classifier.py)。

中间权重仍可保存重载以核验训练一致性，但[StatePolicyRunner](learning_models.py)拒绝缺少`learned_gripper_classifier`的`arm5_only`权重进入策略执行。最终组合继续只使用当前state/env；没有阶段、时钟、IK/OMPL接管或手工盘内开爪规则。默认未启用此选项时仍调用官方`policy(batch)`并监督全部六轴。

## 纯策略验收与止损

[evaluate_state_policy.py](evaluate_state_policy.py) 只从档案取得初始物理快照，不读取专家动作生成控制。step不调用IK/OMPL，模型输入仅state/env。独立监测器依据真实物体抬升、持续双指接触、盘底支撑、完整物体落入蓝盘、松爪和静稳判定成功。安全停止、掉块、未完整施加指定扰动或超时均计失败，保存全部attempt。相同训练快照回放标为重复性检查，不能当作未见场景泛化。

批量正常与扰动成功率各达到85%才标记视觉候选门槛；视觉仍为独立任务，不能机械冻结状态层就保证成功。当前没有相机数据、视觉训练、云端GPU分配或实体机械臂验收。

## 当前实测

### 2026-10-02 T1：持物纠正数据通过，夹爪候选未晋级

新补seed22/24/36三个真实held纠正，原prefix全部NaN/invalid，actual首valid五轴制动＋闭爪；专家完整抓放和各自raw64回放双通过，state/env/time最大差均0。新增7167raw/3359valid/3808invalid，合并[18份清单](output/policy-correction-v12-t1-training-datasets-20261002.json)为44897raw/28863valid/16034invalid。精确采集、回放与计数见[progress本节](../../plans/colab-digital-twin-20261001/progress.md#2026-10-02-t1-持物防误开爪执行完成候选未晋级)。

[CPU夹爪训练](output/policy-correction-v12-t1-gripper-fit-20261002/report.json)6000step/8.200s，冻结同v10 arm72个状态tensor及原四归一化，arm仍14档案；仅8608参数夹爪从随机初始化、fresh Adam和18份有效行的新额外输入统计重训。新组合SHA `f2f87facc42d878652434f67252830550b3b2c58c9308da829a4744cd3802189`。state6/env30、robot-only mask、chunk16/nearest、1mm保护和实际成功判据保持，未引入在线阶段、时钟或几何开闭规则。

[三条已见种子与一条正常argv](output/policy-correction-v12-t1-probe-arguments-20261002.json)均已实际执行：seed22在18.12s失物，首次盘外高位开爪17.94s，比旧26.88s更早；seed24抓起后开爪0但53.58s蓝盘壁保护停止；seed36抓起后开爪0但90s高位闭爪超时。完整扰动抓放**0/3**。seed0正常**仅1/1**通过48.40s、hold25.06s、蓝盘静稳1s，比v11慢8.64s。已训练种子不是泛化测试；没有误开也不能替代完成放置。详见[开爪时序](output/v12-t1-opening-analysis-20261002.json)、[独立审计](output/v12-t1-independent-audit-20261002.json)及[本轮汇总](output/v12-t1-gates-20261002/report.json)。

新增[3项真实artifact测试](output/policy-correction-v12-t1-artifact-test-result-20261002.json)通过、0skip，绑定新3份及seed36回放；源码无变动，旧212全测未重跑。本轮助手为Codex，无新的AGY/ZCODE批准。**T1执行完成但候选不替代v11**，旧20/20正常与3/20扰动不混算为新指标。Seeds40..59未使用，T2/T3/T4、视觉/云端/实物未运行；owner根Codex先检查已见接近/放置actual-state覆盖再单独接续。以上output链接均为被Git忽略的本机证据。

### v11批次与更早单回合的历史证据

2026-10-02批次接续：[v11正式40轮报告](output/policy-correction-v11-batch-20261002/report.json)与[执行参数](output/policy-correction-v11-batch-evaluation-arguments-20261002.json)已本地核验，checkpoint仍`f50a14052b48ad1237024a63cebddec032686441be1149c33e4c8bc5d071a007`。正常20/20，扰动3/20（seed20/25/31）；20次扰动均在实际3.02s连续施加10拍/0.2s、五轴目标偏移各≤0.02rad。总体安全停止5、simulation_time_limit8、payload_lost4；双方≥17/20的门槛未通过，视觉保持not_reached。[独立40轮审计](output/v11-batch-independent-audit-20261002.json)的16项汇总及40轮逐项核验均一致。正常20份NPZ每个字段数组完全相同：seed只采样扰动目标，reset仅复用同一训练参考初态；不写20种场景、独立泛化或吸引域已证明。逐轮wall_s合计309.869s，整进程时长未另记录，不采用“约4.5分钟”的叙述。

失效解释以[实际command/物理核对](output/v11-batch-lost-object-claim-check-20261002.json)为准：seed22/24/36在实际抓起后分别于26.88/25.28/24.00s、物体盘外高位首次预测开爪；seed37抓起后没有开爪command。不能将四轮都认作偏心抓取或物理滑脱。seed21最终物体(.18802,.14002,.04209)m、whole-object盘内false/支撑false，抓起后未输出开爪；策略只有学习state/env与固定训练标签投影，不存在“开爪几何条件”门控。该批次后的建议是先覆盖接近段actual-state纠正与盘外持物闭爪标签，再由实际回放/有界训练定验收；截至该批次结束尚未执行，随后仅执行上文T1。原批次成为已见诊断集；若用于补标签，下一验收必须另用未参与纠正的新扰动种子，并保留旧正常基线回归。仅借用[DART论文](https://proceedings.mlr.press/v78/laskey17a.html)的噪声示范/纠偏思路，不将固定随机脉冲和有限前缀纠正宣传为完整DART优化。

以下v11单回合记录保留批次前的验收快照，当前S7d以本段和[progress](../../plans/colab-digital-twin-20261001/progress.md)末节为准。

2026-10-02最新实测：七条guarded纠正与raw64回放通过，合并原八条为15档案。v11冻结v10的14档案五轴ACT，仅用15档案重训学习夹爪；相同训练初始场景的chunk16纯策略完成抓起、搬运、释放及蓝盘内静稳，单回合门槛**1/1通过**，1988控制周期/39.76仿真秒、hold23.10s、静稳1s，无专家介入或安全停止。只通过这一固定训练场景的重复性门槛；20+20、视觉、云端和实物均未新增。此前v6–v10失败完整保留。

| v6候选 | 本次单回合结果 | 使用的新增纠正数据 |
| --- | --- | --- |
| 全模型ACT接续 | [11.42s料盘底部碰撞，未抓起](output/policy-correction-v6-single-20261001/report.json) | 450-admission、1700/1756-forward三条 |
| 仅线性夹爪输出行 | [37.88s掉物；已抓起并持有20.04s](output/policy-correction-v6-gripper-single-20261001/report.json) | 同上三条旧admission/forward数据 |
| 冻结ACT五轴＋独立学习夹爪 | [38.02s撞障；已抓起并持有20.10s](output/policy-correction-v6-classifier-single-20261001/report.json) | 450/1700/1756三条guarded数据 |
| 三层MLP | [12.94s料盘底部碰撞，未抓起](output/policy-correction-v6-mlp-single-20261001/report.json) | 同上三条guarded数据 |

四次失败均保留原报告和动作，不能写成严格同数据的架构消融。训练清单可核对[全模型ACT参数](output/policy-correction-v6-training-arguments-20261001.json)、[夹爪输出行参数](output/policy-correction-v6-gripper-training-arguments-20261001.json)、[独立夹爪参数](output/policy-correction-v6-classifier-training-arguments-20261001.json)及[MLP参数](output/policy-correction-v6-mlp-training-arguments-20261001.json)。

v7从已核对来源的旧最佳ACT权重接续，12档案、五轴L1、lr1e-5、关键样本5倍采样、原四档案归一化和fresh Adam；[训练2721步/120.0169s](output/policy-correction-v7-arm-fit-20261002/report.json)，allocated87.053MiB/reserved96MiB，CPU保存重载绝对目标最大差1.11e-7rad。随后[独立夹爪训练6000步/9.8998s](output/policy-correction-v7-decoupled-fit-20261002/report.json)，验证72个基础ACT状态tensor保持不变。数据、训练损失、学习率和夹爪组合同时改变，结果不能独立归因；这两份报告均为`task_acceptance=not_run`，没有held-out证据。[全套201项测试/55.101s通过](output/late-recovery-v7-final-tests-20261002.log)证明实现检查通过，不能替代单回合任务验收。

同一v7组合checkpoint `7fef108267cee7ebfc894fddab55f93b1d52b46a547db0f2090f02e476fecfcd`的三次定向执行诊断均0/1：

| 每次观察后执行的窗口 | 实际物理结果 |
| --- | --- |
| 16拍 / 320ms | [22.54s腕限位停止](output/policy-correction-v7-decoupled-single-20261002/report.json)；抓起并持有6.06s，未放置。腕目标1.6579328rad在限内，实际1.6586473rad越过模型上限1.65806rad，安全停止仍计失败 |
| 8拍 / 160ms | [11.82s料盘底碰撞](output/policy-correction-v7-decoupled-chunk8-single-20261002/report.json)，未抓起 |
| 1拍 / 20ms | [90s仿真预算超时](output/policy-correction-v7-decoupled-chunk1-single-20261002/report.json)；抓起并持有71.88s，未放置，无安全停止 |

仅改变执行窗口也未过门槛；更频繁观察不保证任务继续推进，持物时长也不是成功替代指标。上述报告均`expert_intervention=false`，模型输入仍仅state/env，未降低碰撞/限位保护或更改物理成功判据。它们来自训练初始快照，不能当作未见场景泛化。

另将旧ACT权重`642f4f...`保持冻结，仅用当时12条训练集合学习新夹爪；组合checkpoint `597a807e5e2c75441c9bc871f918151549ce565e72f3f24ee22ff706801fe512`在[21s掉物](output/policy-correction-v7-frozen-origin-classifier-single-20261002/report.json)，抓起/hold2.66s/未放置。冻结旧五轴也未成功，不能把所有提前掉物单独归因到该次五轴微调；尚未证明唯一失败原因或独立夹爪已解决问题。[对应训练清单](output/policy-correction-v7-frozen-origin-classifier-training-arguments-20261002.json)。

v8的[实际有界训练参数](output/policy-correction-v8-arm-training-arguments-20261002.json)为13档案、五轴损失、初始化v7 arm SHA `58d8b5a8384f044ff39e04c567ca6e174ff2a0715de762f6f70707c879f03f30`、batch64、lr1e-5、120s上限，robot-only mask及归一化保持。[五轴ACT实际1504步/120.079s](output/policy-correction-v8-arm-fit-20261002/report.json)，allocated110.629MiB/reserved142MiB，arm checkpoint SHA `00da58926f51a1408f73f3b5dc4280a895c8ef90de080c21f4a9affef51bdcd5`；[独立夹爪CPU训练6000步/7.898s](output/policy-correction-v8-decoupled-fit-20261002/report.json)，最终组合SHA `0007471daee2fcef19b81b157a3f45f80174b997f804fa582d4e0acbfc047a67`，72个基础ACT状态tensor保持不变。数据与batch同时改变，不能将结果只归因新增纠正。201项/55.101s是此前完整测试结果；本阶段无新源码，不冒充v8重跑或任务验收。

[v8 chunk16纯策略回合](output/policy-correction-v8-decoupled-single-20261002/report.json)0/1：真实抓起并持有60.42s，89.72s时`place_wall_x_-1`与`collision_gripper_1`距离.8471mm触发原1mm余量保护。末条有效物体诊断位置(.20221084,.11643329,.02516980)m、`in_place_tray=true`，但`place_floor_contact=false`，双指仍约1.443/1.441N、夹爪命令仍闭合，未释放或稳定承托。[逐拍诊断](output/policy-correction-v8-decoupled-single-20261002/attempt-000-nominal/diagnostics.json)。进入盘内和持物时长不能替代完整放置验收。

随后从这次回合第2500拍真实持物状态采集“蓝盘边缘安全通道→盘心→降放”的专家纠正，[实际采集参数](output/policy-correction-v8-held2500-collection-arguments-20261002.json)保留。专家抓放和raw64回放双通过后，已纳入第14条及上述模板。v9按[14条固定数据清单](output/policy-correction-v9-training-datasets-20261002.json)和[实际训练参数](output/policy-correction-v9-arm-training-arguments-20261002.json)，从v8 arm `00da58926f51a1408f73f3b5dc4280a895c8ef90de080c21f4a9affef51bdcd5`初始化，batch64/lr1e-5/120s上限。

[v9五轴ACT报告](output/policy-correction-v9-arm-fit-20261002/report.json)实际73step/120.1525s，整体`total_s=405.6682`，wall_time_limit停止，allocated110.629MiB/reserved142MiB；保存arm SHA `3b2183da2a3a5f3e2103dad9d2fc4d863bb57a4482ab18ce530066fa03aea7ac`。5倍关键采样下实际4672次抽样、578次关键抽样；报告`actual_unique_row_count=4166`指不同观测/chunk起点，占25107个有效起点的16.593%，不是监督动作标签覆盖。按seed0的实际73×64抽样重建，并依[make_chunks](train_state_policy.py)的chunk16/invalid间隙/回合边界展开，非padding监督动作槽共74384次（含重复），源目标帧并集23501/25107=93.603%；新742帧纠正档案被抽中131个不同起点，其未来目标并集713帧。不能写成“84%的动作标签没训练”；只能确认本轮73步且尚未遍历全部观测起点，不能据此唯一归因掉物。

[独立采样重建与策略审核](output/late-recovery-v9-policy-independent-audit-20261002.json)保存上述起点/目标两套覆盖口径，4672抽样/578关键抽样与训练报告完全匹配；新742帧档案实际抽141次、131不同起点、713目标帧。该审核只读现有源码/产物，没有重新训练或运行物理仿真。

[独立夹爪CPU6000step/9.234s](output/policy-correction-v9-decoupled-fit-20261002/report.json)实际抽764730次/90585关键次/25107不同观测起点，保持72个ACT状态tensor不变；其采样与训练步数独立于arm。最终组合SHA `efb9735d7a90bcf6e428310247bd82cf9cc2431b7c62b82658cddc001c9c3fa1`。[chunk16纯策略](output/policy-correction-v9-decoupled-single-20261002/report.json)0/1，抓起并持有11.22s，27.08s payload_lost、未放置，无安全停止。原失败完整保留。

v10按[实际CPU训练参数](output/policy-correction-v10-arm-training-arguments-20261002.json)，相同14数据、ACT五轴损失、batch64/lr1e-5/120s上限，初始化仍为v8 arm `00da589...`，不继承v9的73步。[CPU arm实际1201step/120.067s、整体144.551s](output/policy-correction-v10-arm-cpu-fit-20261002/report.json)，76729次抽样/9021关键次/23613不同观测chunk起点，保存重载差0；arm SHA `b92adf12f9482467aa927aff1c71e8c94ae2cba6ed878b7743678b52abab57e6`。[独立夹爪CPU6000step/7.3647s](output/policy-correction-v10-decoupled-fit-20261002/report.json)，72个ACT状态tensor保持不变，最终组合SHA `cb8f8774f7cb7a67c06a910ebe5684e39ff0b9042070088fcbd1d73b75f06d48`。

[v10 chunk16纯策略](output/policy-correction-v10-decoupled-single-20261002/report.json)0/1：抓起/持物25.06s/未放置，完成52.20s后`place_wall_x_-1`与`collision_gripper_1`距离.936503mm触发原1mm余量保护。专家介入false，观察仅state/env；该策略是官方ACT五轴与独立学习夹爪的组合诊断，不能称“官方完整ACT已通关”。全部原失败报告和动作保留。

切CPU只做有界吞吐/覆盖诊断；v9无OOM，不是ACT资源门槛失败后切MLP，也不是永久架构选择。单点GPU频率/利用率不能证明v9慢训原因，设备改变与实际完成步数、数值路径变化也阻止严格因果归因。1201步仍在蓝盘边缘失败，本轮不以继续追加同样训练预算或放宽保护作为默认接续。

v10失败后的定向检查发现低位释放覆盖缺口，因此只补上述第15条并重训夹爪，没有再给五轴ACT追加120s预算。按[v11实际参数](output/policy-correction-v11-release-training-arguments-20261002.json)，基础ACT固定为v10 arm SHA `b92adf12f9482467aa927aff1c71e8c94ae2cba6ed878b7743678b52abab57e6`（14档案训练）；[夹爪15档案清单](output/policy-correction-v11-training-datasets-20261002.json)包含25504有效行。[CPU夹爪6000step/7.1017s、整体9.9502s](output/policy-correction-v11-release-classifier-fit-20261002/report.json)，72个基础ACT状态tensor完全不变；base输入/动作归一化沿原四档案统计，robot-only mask保留，夹爪额外输入统计仅fit15档案的合格行。组合checkpoint SHA `f50a14052b48ad1237024a63cebddec032686441be1149c33e4c8bc5d071a007`。

[v11实际纯策略报告](output/policy-correction-v11-release-single-20261002/report.json)及[执行参数](output/policy-correction-v11-release-evaluation-arguments-20261002.json)记录1/1通过：1988周期/39.76s、抓起/hold23.10s/放置/静稳1s，无安全停止。只读当前state/env，expert_intervention=false；初始快照来自训练nominal，非未见场景泛化。固定chunk16每320ms观察一次，五轴残差只在chunk起点解码。学习夹爪自己选择`.015/.5`，nearest适配器仅将`.0150000114/.5000000092`浮点输出投影回训练标签，1988次约1.15e-8rad量级修正，不读取几何、阶段、时间或专家动作决定开闭。它是“官方ACT五轴＋独立学习夹爪＋固定执行适配器”的状态策略闭环，不能写成官方完整ACT通关或不带适配器的模型验收。

当前完成固定训练初始场景单回合门槛；下一步如继续，只在冻结该候选后独立开展20正常＋20有界扰动，完整记录注入、安全与成功率。20+20仍not_run，尚无扰动恢复率、视觉或实体标定证据；不从1/1推断泛化或将低位标签当成唯一因果证明。

所有原失败继续保留，碰撞余量/限位/任务判据不变。此前[201项/55.101s](output/late-recovery-v7-final-tests-20261002.log)只证明其当时版本；[当次运行参数](output/late-recovery-v7-final-test-arguments-20261002.json)只绑定8条真实产物（四v5＋四v6 guarded），彼时12条训练集合另有[独立审核](output/late-recovery-v7-independent-audit-20261002.json)，后续14总集另有[数据审核](output/late-recovery-v9-data-audit-20261002.json)。新增release采集器后，[当前全套212项/41.991s、0 skip、exit0](output/late-recovery-v11-final-test-result-20261002.json)通过，源码测试前后哈希一致；[实际参数](output/late-recovery-v11-final-test-arguments-20261002.json)绑定11份HDF5（四v5＋七guarded）与release2517回放，四份v4训练档案不在这11份artifact绑定内。测试、各档案回放与纯策略任务是不同证据，不能相互替代。

[v11独立Codex审核](output/late-recovery-v11-independent-audit-20261002.json)39项检查全true：重算真实物理静稳1s、完整旋转物体蓝盘范围、支撑和松爪；逐tensor确认72个ACT不变、arm14/head15、原四归一化与夹爪15份统计误差0；确认invalid前缀NaN、raw64回放差0及212项当前源码/产物绑定。审核未训练、推理或运行物理，只审现有产物和源码；SHA `24e341d401479ad57c39a5b2a13609738ca70247b2e3d5dac02d315402f8f565`。最终真实物体(.21228807,.13849017,.00992145)m有蓝盘底支撑、双指接触力0；没有放宽成功判据。该审核来自Codex，非新的AGY批准。

同checkpoint/同固定初态的[可见纯策略复跑](output/policy-correction-v11-release-visible-20261002/render-binding.json)也通过，9个NPZ字段数组及全部物理diagnostics逐项与首次完全一致，渲染未修改执行状态。[995帧视频](output/policy-correction-v11-release-visible-20261002/attempt-000-nominal/pure-policy-grab-place.mp4)与[释放落盘细节](output/policy-correction-v11-release-visible-20261002/attempt-000-nominal/placed-detail.png)为本机忽略产物；这只是可见复验，不额外计入20+20或泛化成功率。

以下为前序实验的原始结果，保留失败演变；其中“没有载物collector”“下一项待验”等状态仅指当时，当前状态以上述日期段落及[progress](../../plans/colab-digital-twin-20261001/progress.md)为准。

2026-10-01本地RTX3050 Laptop物理显存4096MiB：首次官方ACT探针峰值allocated117.59MiB/reserved146MiB，5步计算0.1175s；MLP分别17.53/22MiB、0.00829s。两者资源门槛通过，不代表学习任务已通过。

首轮单轨迹ACT训练3133个有效转换，5000step/26epoch/117.59s；归一化chunk L1由0.91297降到0.03603，首动作MAE0.01160rad；CPU重载差3.58e-7。纯策略在0.52s触发碰撞保护，抓放失败。首轮float32动作回放物理抓放成功、时间与关节一致，但释放附近环境逐帧严格匹配失败；原失败报告保留。随后保存原始float64并统一观测刷新节拍，3133步state/env/time误差均0，严格重放通过。最新完整入口ACT再训5000步，首动作MAE0.01085rad，但纯策略0.36s障碍碰撞停止，40回合与视觉保持not_run。最新结果与可恢复接续见[progress](../../plans/colab-digital-twin-20261001/progress.md)。

后续v4四正例9404帧/9401有效标签，nominal2350步及startup-plus2351步独立raw64重放state/env/time差均0。ACT有界训练13491step/240.013s；同权重默认、chunk16及chunk16+nearest夹爪分别9.74/10.22/10.22s腕限位停止，均未抬升物体。三层MLP同四档案8000step/8.234s诊断后，默认16.08s盘壁碰撞、nearest夹爪9.92s桌面碰撞，也未过门槛。

v5四类前缀的专家恢复全部抓放成功，共9423帧/8823有效标签，600帧策略前缀排除训练。prefix250独立2372步重放state/env/time差均0，3项真实产物检查通过。八档案合计18224有效标签，以上有界权重接续实跑7000step/109.024s，allocated87.053MiB/reserved96MiB；输出`output/policy-recovery-v5-state-fit-20261001/policy.pt`。纯策略`output/policy-recovery-v5-baseline-20261001/report.json`在10.48s腕限位停止，仍无抬升；20+20和视觉未运行。

定向离线探针固定q及其他env，只将六轴qvel由专家值替成在线值，路线转角处腕目标偏移由+.002804变为-.004647rad，专家为+.005230rad；`output/v5-qvel-causal-audit-20261001/`已归档。随后一致屏蔽robot qvel、从v5权重接续八档案，实跑3886step/4epoch/120.039s，allocated87.053MiB/reserved96MiB，权重位于`output/policy-recovery-v5-qvel-masked-fit-20261001/policy.pt`。默认18.64s、chunk8+nearest 52s料盘底碰撞，无抬升；chunk16+nearest真实抓起并持续保持17.56s，但35.2s在蓝盘外首次开爪，35.4s判定payload_lost，完整抓放仍失败。

最新`output/v5-qvel-masked-physical-audit-20261001/release-probe.json`核对chunk边界1760拍的新预测与保存raw_action一致。固定实际q、物体姿态和其他env，仅替换六个物体速度为几何近邻训练值，jaw预测从.401425变为.017844；原始速度置零探针为.018514。实际物体速度与该近邻的归一化L2差分别为线速度105.75、角速度134.03，4/6轴超训练min/max；这是局部敏感性证据，不等同于新归一化屏蔽策略的在线结果。根Codex接续有界物体速度消融及单回合验收；没有增加载物collector，20+20/视觉未运行。全部数据、NPZ、权重、审计与日志仍由Git忽略。

本轮收尾：双速度屏蔽ACT（6657step/120.017s）在14.2s料盘底部碰撞停止；同输入MLP CPU对照也限位失败。训练观察范围clamp的离线探针未修正提前释放，不接入评测代码。最强候选仅证明真实抓取并抬持17.56s，完整抓放**未通过**。完整150项实现/产物测试通过，无跳过。根Codex接续当前[失败门槛与最短采集入口](../../plans/colab-digital-twin-20261001/progress.md)，保留所有权重/数据与失败报告；20+20和视觉未运行。

初始化可复用已验证权重和原统计，并重建Adam。`--mask-robot-velocity --mask-object-velocity --init-checkpoint ...`也可通过`run_learning.py --sanity-only --train-recovery`显式转发；所有来源和掩码随报告/权重保留。权重曾用的训练集合与统计最初拟合的集合分开记录；统计来源必须属于原训练集合，不能把继承统计描述成新数据重拟合。只用于当前状态仿真诊断，不作为永久关闭速度观测的决定。
