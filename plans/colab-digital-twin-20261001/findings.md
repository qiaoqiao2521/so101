# Findings

## 2026-10-01 学习会审补充

当前抓放trajectory.json不含arm qpos/qvel/ctrl，仅有物体和接触诊断；20ms诊断与40ms视频没有训练帧索引。固定搬运成功不证明任意扰动恢复。ACT官方固定版本支持无图像ENV状态、无视觉backbone；imitation有正式MLP-BC实现但整包依赖较多。本机原规划venv无Torch/LeRobot等学习依赖；两个模型均未训练或测内存。

AGY首轮CLI SUCCESS/exit0和原生done仍是部分正文；定向复核完整完成后改选状态ACT。ZCODE第一次取消无正文，短提示流式补取取得GLM-5.3-Flash实际完整回答、0工具事件，保留MLP先行意见；成功请求28063tokens不包含失败请求/AGY完整可归属用量。原始资料被Git忽略。详细可定位来源、引用锚修正和不采用的无依据结论见[learning-review.md](learning-review.md)。

- 对应开发根为 `/home/muqiao/dev/ros2/projects/so101`；旧 so101-win7 路径是兼容链接。
- 六份文档复制到被忽略的 `local-documents/graduation-20260629/`。本地 manifest 保存文件名、大小与 SHA256，manifest 也被忽略。
- 历史来源：Codex session `019ef2b7-61a2-7ce3-8789-665ed12b303b`，6 月 29 日答辩反思和 DOCX 转换；不把旧助手声明当本次执行证据。
- 当前 Colab CLI 0.6.0 已安装；`colab sessions` 认证调用成功。无需重新登录、导出浏览器凭据或更新 CLI。
- 有效模型含六个弧度关节和六个位置执行器，末端 site 为 gripperframe。模型 SHA256 为 d75253eb568e8a7214db9c631ab7bed4217f608a26f7276ebe9a7636cac82580。
- 复用 MuJoCo 包中的 13 个完整 STL；第三方源目录的同名 STL 是零字节。旧 scene.xml include 名称不匹配，本轮只在实验副本生成场景。
- Git 本地 HEAD 427e3eb 落后已发布 origin/master e5c0168 两提交。源码 app.py、静态前端、鉴权文档、teleop 测试、动作导出器与远端逐字相同；不能依据旧 index 把它们当未交付。
- 仓库远端已核对为 qiaoqiao2521/so101，保持 public/master；本轮不改可见性或重写历史。

## 2026-10-01 自主规划续接审计

- 用户选择 MuJoCo 为运动自主规划核心。原生 Colab 平台继续作为同一项目内部模块；不新建平行仓库。
- 当前主工程、repo-revival 整合快照、repo-scan 两个旧工程和 delivery 已定向比较；现存 MoveIt/OMPL 规划文件没有更完整的外部副本。旧 workspace / follower 路径已是兼容链接。
- `pick_place_runner.py` 实际调用 MoveGroup / OMPL，默认 RRTConnect，支持关节目标、重试和轨迹导出；2026-03-14 非空日志记录 7/7 预设目标通过，多点轨迹存在。本轮不重新认定当前运行或避障验收。
- 5月 MTC Cartesian IK/FK → Gazebo reach 只有开发记录与非空 suite summary。jitter20 的 200 个、jitter50 的 500 个逐轮 artifact 均为零字节；核心 C++ node / launch / evaluator / projector / recorder 缺失。本地快照及有界 Agent 历史没有找回原件。
- jitter50 summary 的 reach 采用 8 cm 阈值，平均距离 5.64 cm、p90 7.34 cm，不能作为精准抓取成功率。原 evaluator 缺失，周边门禁只消费指标，不能替代 TCP 距离计算。
- ROS URDF 是 17 visual / 0 collision；原生 MJCF 是 17 visual class geom / 13 collision class geom。后者仍须验证编译后的 mask、碰撞覆盖和凸包误差，不按 URDF 缺失结论重造全部几何。
- 原 Gazebo 世界桌高约0.75m，目标z约0.8m；MJCF使用自己的world/base/TCP坐标。迁移目标须显式转换并用FK核对。
- `lerobot` 独立源树含 Placo FK/IK；没有证据证明该实现已经在现有 SO101 Colab 平台运行，不作为已验收替代库。
- 实际 AGY CLI plan/sandbox 单次只读咨询返回 MuJoCo + Python IK/OMPL 的单方向建议，并推荐可达性→碰撞→跟踪顺序。仅基于摘要，未独立跑实验；原响应位于被忽略的 local-documents。
- Gazebo官方支持server与OGRE2/EGL无头渲染；本项目未在Colab实测。Jazzy默认搭配Harmonic，旧Classic/Humble链需要迁移；Colab免费且无正计算余额时限制远程桌面。
- MuJoCo3.3.7保持当前基线；Mink1.1.0与OMPL2.0.1是待隔离验收候选，本轮未安装/升级。官方依据集中在 `../../docs/MUJOCO_MOTION_PLANNING.md`。

## 本轮实现新证据

- 源MJCF13个移动collision mesh全部mask1/1；底座四个visual在派生场景复制为collision。排除同刚体、六对直接父子装配及固定底座安装；非相邻负距离shoulder/gripper自碰仍检出。
- 原生CCD在纯yaw相对不变时误报0，派生XML选择libccd；15yaw回归保持距离。其分离距离为近似凸包指标，不是实机安全。默认group3环境不可见的问题通过零mask的group2副本修正。
- MuJoCo实际夹爪状态会微小偏离固定指令，执行碰撞查询必须使用真实q6并解除精确固定要求，规划仍固定；不能以指令替换实际姿态。
- Colab CLI0.6.0远端Python错误不保证本地非零退出，timeout也不保证停止内核；以下载的严格产物/逐轮验收为依据，并在finally释放整个本次会话。
- 当前20轮只覆盖同一个盒子附近±3mm位置任务；离散路径0.025rad/执行20ms，不是连续碰撞、抓取、视觉或真实参数验收。

## 主线逐层验收入口

复用当前MuJoCo/Mink/OMPL实现和现成planning-venv，未重新安装环境。run_staged.py只在依赖版本和实际导入通过后加载模型；run_gate拒绝越过未通过阶段，失败保留其原因及后续not_run状态。已采纳Obsidian Wiki/自动化开发范式与智能体协作.md“按当前任务选择验收依据”：依赖导入、仿真reset/step、精确路径与实际执行是分别观察的结果。

本机真实单回合：reset10步/0.02秒，IK误差0.323mm，113点精确绕行，物理执行7546步/15.092秒，TCP误差0.549mm，20ms碰撞无效样本0，限位超出0。独立CSV核验756行全有限、时间递增和末行TCP误差；视频完整FFmpeg解码378帧，预览显示工作台与障碍。模型与13STL记录SHA，源MJCF未修改。位置执行使用模型原位置伺服；路径仍预先规划，动态重规划未接入。

原29项回归加3项阶段边界检查通过：前层失败不调用后层、规划异常保留执行not_run、依赖失败持久化报告且不编译模型。真实系统Python缺少依赖的CLI负例退出1且task_success=null。脚本默认不渲染；--render可选，按运行环境已有MUJOCO_GL或OSMesa/EGL默认选择。该证据不扩大成动态障碍、抓放、视觉或实机同步。

## 2026-10-01 单臂夹取建模

用户指定先建模、改善场景，并纠正主从为现实系统；本轮只有一台从臂。找到本地BLD-001建模说明、主从场景生成器和动作模板；当前工程无其记载的Blender/GLB成品，LightArmPreview.vue与leader专属STL为零字节。复用完整的原生从臂13STL，新增grasp_workcell.py/preview_grasp_workcell.py及动态物体/夹爪检查。

新模型包含工作台、开放红/蓝料盘、相机支架、自由物体；生成1280×720三视图与100帧/4秒机械开合视频。原模型SHA仍d75253eb568e8a7214db9c631ab7bed4217f608a26f7276ebe9a7636cac82580。物体18×18×16mm、10g；实测中心z从0.012m落定至0.009784m，真实pick_floor接触。夹爪实际范围0.250019–0.799997rad，预览期间物体抬升约0；grasp_success/lift_success=null，尚未夹取成功。视频独立全量解码通过，34项回归检查通过。派生MJCF可编辑，原模型不改；无实体或云端操作。

结果保存在Git忽略的experiments/colab-twin/output/grasp-model-72f103318b2a4cf78c7b89f317ee53ed/。原场景建模说明只用于布局参考，仿真坐标和物理参数不当作实物标定；现场模板不复制发布。后续owner根Codex：先对位/接触建模，再以物体抬升与持续夹持验收；已有静态规划入口及遗留交接保留。

## 障碍接触夹取

原TCP位于固定指尖，不能直接当指间中心。派生夹持点在gripper局部(.006,0,-.094)m，使用独立状态求垂直姿态IK；下降到世界z=.019m以避开指尖/盘底碰撞。全网格凸包与小方块接触出现毫米级穿透/下挤，指尖接触垫替换仅目标与两块指爪的接触；其余链接和所有物理环境仍与目标碰撞，原网格仍负责机械臂与桌面/障碍碰撞。接触垫尺寸与摩擦、.15Nm夹爪力矩是未标定仿真假设。

MuJoCo3.3.7/libccd在worktable盒子和collision_shoulder_2距离查询distmax=1m时给出-.2456m假穿透；实际顶点最低z=.0162m且无物理接触，distmax=.1m返回+.0162m。checker改为max(.1,margin+.05)m的局部查询，远距离饱和；合法起点和真实中间障碍负例通过，既有碰撞测试继续通过。

物理执行使用单一MjData；IK/距离查询独立，避免运动学查询改变现场。障碍接触按2ms每步统计，机械臂限位/环境/自碰按20ms状态检查；规划边按.015rad离散验证，尚非连续碰撞证明。保持段须全部样本抬升≥25mm、双指法向力>.02N、无桌面/盘底支撑，持续≥1s；空夹或短暂抛起不能通过。

## 搬运放置验收与软接触下滑

保持竖直夹持的搬运路线采用内侧x=.18m绕行、3mm Cartesian采样及.01rad关节边验证。查询用实测指爪/物体相对姿态预测载物占位，仅写独立MjData；执行保持自由物体。载物箱体与较远料盘壁在.1m距离查询下再次出现假穿透，载物局部查询范围缩为.02m，大于该值的间隙为饱和值；余量.0002m只为单场景离散fixture。

正常软接触即使双指各约2N，物体仍以约.5mm/s下滑，二十多秒搬运会滑出指尖，最终落在两盘之间；升高力矩不能消除。MuJoCo3.3.7官方modeling.html#preventing-slip明确区分摩擦不足和soft-contact慢滑。搬运模式选Noslip10次后通过，.15Nm力矩和原接触几何不变；原抓起模式保留noslip=0。该配置是前向仿真假设，改变逆动力学/计算成本，未当作实物材质标定。

完整验收要求途中持续双指接触、最后物体整个旋转盒子XY投影在蓝盘内部；松爪后真实盘底接触、双指接触力归零、速度<.002m/s、z约.01m，机械臂撤离后持续≥1s。关闭Noslip的真实物理负例搬运滑落被停止，轨迹可恢复。没有物体动画/附着/weld/mocap。

## 状态学习实现校准

- mj_step后派生量与积分后的qpos不是同一边界；采集与回放需一致的forward刷新次数。状态与动作存float64、网络转float32后，原动作3133步所有state/env/time误差0；原float32档案在释放接触处严格逐帧匹配失败，原证据保留。
- 固定等待6秒闭爪使瞬时状态对应不同专家阶段。学习采集改以双指接触/夹爪速度推进、时间仅作失败超时；释放先确认活动指松开和盘底承托，固定指完全离开要等待撤离。
- 官方状态ACT本机反传约118MiB allocated，4GB不是本次阻碍；120秒内离线动作误差下降但纯策略0.36s碰撞停止。故数据、资源、回归、真实任务必须独立验收，后层not_run。
- 连续动作chunk不能跨invalid扰动帧或episode；专家stage/time不得成为策略输入。动作源仍是实际重规划纠正，不是扰动执行命令。

## 起步与接近恢复诊断（2026-10-01）

旧绝对ACT首步pan误差约-.02448rad，而专家arm指令与actualq的95%偏移仅约.0023–.0035rad；下一拍pan/elbow速度达到-1.178/-1.061rad/s，远超专家接近速度。旧恢复执行.2s后才采纠正，首valid速度接近零，不能覆盖起步失稳。根因证据支持先改变动作尺度与恢复时机，不能把4GB显存当作这次失败原因。

内部arm_delta、qvel尺度下限.1、关闭VAE/dropout的5000step诊断：首步arm最大误差.000187rad，首动作arm五轴MAE约.000022–.000188rad；但夹爪首步预测.50719而标签.5，20步实际漂至.55210，后续shoulder漂到下限附近。纯策略39.94s仍未抓起物体，限位停止；误差改善不等于过门槛。保存于ignored `output/state-delta-sanity-20261001`、`policy-delta-sanity-20261001`、`delta-first-audit-20261001`。

专家下降终点若静止后才闭爪，相近观测会因隐藏阶段收到不同jaw标签。新版在实际下降/下降放置运动中触发jaw切换；释放门槛按实测终点高度校准为14.5mm，去掉自由落体期间会重新闭爪的速度条件。四份v3实际成功，共12378帧/12375有效标签，jaw切换均在descend/lower，后续reclose=0。有界近邻k16、标准化L2半径.001、动作冲突门槛.05rad未发现冲突；这不证明观测充分性。

v3起点±.006rad/20ms恢复首valid pan速度+.263833/-.263756rad/s，接近35%处+.002rad/20ms首valid pan速度.047732rad/s。扰动最后nextobs与首valid状态/环境/时间逐字段相同，brake target等actualq。startup-plus独立3061步原动作回放state/env/time最大差0并完成抓放，3项真实产物测试全部通过无skip。覆盖仍限固定布局和这三类小扰动，尚不覆盖旧失稳的高速状态。

同v3权重的三项有界执行消融都没有过门槛：16步chunk90s超时、nearest夹爪10.38s腕限位、两者组合90s超时；全部未抬升物体。nearest将夹爪固定到训练两标签后仍腕漂移，说明误闭爪不是唯一根因。使用新chunk日志时，诊断把fresh inference与缓存动作区别标注，投影/扰动也与raw模型输出分开，不能拿不同执行语义误报适配器错误。

v3前.2s actual pan仅变化1.49e-9rad/wristflex5.08e-12，但命令由隐藏t逐步改变；前50个float32观测仍50unique，因此不是严格重复输入不可学的证明。它支持起步信号过弱的假设。v4只把approach改actual投影lookahead（.006rad），firstarm command-q为[+.002318,-.001471,-.000947,-.004806,-.002511]，前.38s实际arm位移L2 .153997rad；后续仍timed。4份成功采集共9404帧/9401valid，包含startup多轴±[.002,.001,-.001,.001,0]以及approach35%处[.002,-.001,.001,.001,0]，实际推进20ms。nominal2350步/startupplus2351步独立CPU回放全state/env/time差0，真实抓放与3项恢复artifact测试通过。尚不能据此宣称新学习策略已通过。

### v4/v5 有界诊断与剩余门槛

以下路径均相对`experiments/colab-twin/output/`，整个目录Git忽略。v4专家档案为`reactive-v4-{nominal,startup-plus,startup-minus,approach}-20261001/expert.h5`；独立重放为`reactive-v4-independent-replay-20261001/report.json`和`reactive-v4-startup-plus-independent-replay-20261001/report.json`。仅approach反应式，descend/lift/transport/lower仍依赖时间minimum-jerk，不扩展成全任务反应式专家。

`reactive-v4-state-fit-20261001/report.json`记录四档案ACT 13491step/240.013s（wall上限240s），arm_delta、qvel下限.1、noVAE/dropout0、关键行5倍采样；归一化只fit这四份训练行，未用held-out。权重SHA `d0142fecc159f3390a9cbeeb350ff83f0ab4518eab540e24480824fc7eb213d8`。纯策略`policy-reactive-v4-{baseline,chunk16,chunk16-nearest}-20261001/report.json`分别9.74/10.22/10.22s腕限位停止，全部未抓起。`reactive-v4-mlp-first-action-probe-20261001/report.json`同四档案三层MLP 8000step/8.234s，权重SHA `ac880325022a2a0d7e009bd0540ab3ce5d08e2181f9761b9c60fc112d74c7f4b`；`policy-reactive-v4-mlp-probe-20261001/report.json`16.08s盘壁碰撞、`policy-reactive-v4-mlp-nearest-20261001/report.json`9.92s桌面碰撞。更小网络同样未打通物理闭环。

v5从`policy-reactive-v4-chunk16-nearest-20261001/attempt-000-nominal/policy-transitions.npz`取真实策略action前50/100/200/250拍，源SHA `20db559734f7ae635ed1e8a43c788ba294c693e3b4f4bdd2646b6cac8831e21e`。`policy-recovery-v5-prefix{50,100,200,250}-20261001/expert.h5`四份专家恢复正例，共9423帧/8823valid；各档invalid前缀数恰为N，executed_action精确等于NPZ float32动作转double，训练排除600前缀帧。首valid观测精确接续前一nextobs，actualq制动且pan速度分别.043567/.049191/.044557/.033647rad/s。来源、哈希与恢复状态已保存；不是给专家标签加噪声。`policy-recovery-v5-independent-replay-20261001/report.json`独立2372步重放state/env/time差均0，抓放通过，3项真实artifact检查通过无skip；仍不等于纯策略成功或完整[DART](https://proceedings.mlr.press/v78/laskey17a.html)复现。

`policy-recovery-v5-state-fit-20261001/report.json`以v4四份＋v5四份18224valid行有界接续：lr2e-4、7000step/7epoch/109.024s，预算120s/7000step。初始化权重为上列v4 SHA，归一化沿用该checkpoint的原四训练档案统计；fresh Adam及新采样计数，不恢复优化器，不重算八档案统计。输出权重SHA `26268fb563824fb0fe4268a46faa55e1b798b12386e550989b766ae8aba04472`，CPU重载绝对rad差5.54e-8；allocated87.053MiB/reserved96MiB，无held-out证据。`policy-recovery-v5-baseline-20261001/report.json`纯策略10.48s腕目标越下限，未抬升/抓放。数据回放、离线拟合与策略执行仍分别判定；[官方ACT来源及运行契约](../../experiments/colab-twin/LEARNING.md)保持固定。

定向离线因果探针固定q与其他env，只替换六轴qvel为在线值，转角处腕target−q由+.002804变为-.004647rad（专家+.005230rad），默认及chunk执行均出现反向预测。支持qvel输入敏感性假设，不证明只屏蔽速度即可成功；`v5-qvel-causal-audit-20261001/`已归档。

随后仅增加训练/推理一致robot qvel屏蔽，`policy-recovery-v5-qvel-masked-fit-20261001/report.json`从v5权重接续同八档案，原四训练归一化沿d014→26268权重链继承，fresh Adam；3886step/4epoch/120.039s，allocated87.053/reserved96MiB，输出SHA `08de5fc1d29ca6849b614f0fa5ed6b6852b1785c60af9e0be61f517eb00ccc24`。`policy-recovery-v5-qvel-masked-{baseline,chunk8-nearest}-20261001/report.json`分别18.64/52s料盘底碰撞，无抬升；`policy-recovery-v5-qvel-masked-chunk16-nearest-20261001/report.json`真实抓起并持续持有17.56s，但35.2s首次开爪时物体(.177743,.087811,.048516)m仍在蓝盘外，35.4s判定payload_lost。策略真抓起与完整抓放失败分别记录，未更改计数或验收条件。

`v5-qvel-masked-physical-audit-20261001/release-probe.json`在fresh chunk边界1760拍核对保存raw_action，排除缓存动作比较错误。固定实际q及其他env，仅替换物体速度为几何近邻训练值，首jaw由.401425变为.017844；原始物体速度置零为.018514。actual对该近邻的归一化L2差：线速度105.745、角速度134.035，4/6轴越训练全范围，支持速度输入敏感性。名义真释放帧2060原jaw .3713、原始速度置零后.4573，仍开爪；运输反例仍闭爪。这些是离线局部替换，不能保证在线闭环或唯一根因，源码/权重/数据SHA与初始不可变probe均保留。

新增显式`--mask-object-velocity`只对归一化env[13:19]（线速度3/局部角速度3）置零；已有robot mask[0:6]独立保持。训练与推理共用适配器，原统计/原始数组/动作/实际动力学不改，有限性先检查，旧默认false，初始化from/to持久化且不可静默取消。物理监测仍用原data.qvel，包含静稳/支撑释放速度与全qvel有限性检查。下一项同八档案有界物体速度消融结果待验；载物恢复collector仅有只读方案、未创建源码/数据。完整单回合门槛未过，20+20/视觉/云端/实体验收均未新增。

本轮最终物理结果：robot-only-mask ACT有真实抓取/17.56s hold，但盘外提前释放；新增object-mask ACT 120s限时拟合后14.2s底部碰撞，MLP同输入CPU对照也限位失败；完整单回合仍未通过。精确观察范围clamp无法修正提前开爪，故不接入代码。150项完整测试仅证明实现及数据层边界。源、失败证据、归一化来源核对和最短接续边界见progress.md末节。下一项应区分接近末端/持物实际状态覆盖与候选控制精度，不能凭平均loss下降或局部counterfactual宣布恢复机制已解决。
