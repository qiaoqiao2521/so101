# M1b：同次几何查询的完整明细交接

## 当前结果

固定5badfff的生产组件及原Station五例已结束，五例全部原pass。两左工位反序对照process wall分别减少4.924／5.002s，CPU均降，hold同拍。保留显式候选，不切默认。完整50Hz未过，P95和慢拍计数反增；详见下方生产结果。前文“待验”描述对应历史阶段。

## 已证实的局部收益

左固定盘close尾段的私有原型在Kaggle完成三对AB/BA/AB组件计时，均完整输出exact相同，候选wall中位比.716078、threadCPU中位比.715990。减少的是同姿态固定轴285对的第二次查询；每姿态全部285对仍认证，补充方向查询也仍执行。

这不是原物理抓放或完整50Hz验收。当前只支持继续实施默认关闭候选，尚不能采用默认或推算整程节省。新生产实现及原物理结果后续另列，不用私有monkeypatch替代生产代码。

## 来源、输入和隔离

源码固定 `500dc4792b3e650d535579276504c44247c9800f`，算法与前一05cc17c相同。Kaggle `muqiaoqiao/so101-refinement-detail-20261024/1` 已COMPLETE，component stage终态、原进程returncode0；没有Station verdict，physical_started=false。

云端Python3.13.15／MuJoCo3.15.0／NumPy2.4.6，沿用原bootstrap、runtime、command helper与preflight。preflight的原64×64渲染在组件进程之前，单独记录；组件检查期间禁止mj_step和Renderer，没有新IK、OMPL或抓放积分。原Station runner仅保存来源，未调用。

输入来自原左 `9645f2fa-3958-46a5-8727-958ebec8d448`：8条尾段派生弦加1条重建的244点完整闭爪，共571状态。它们由保存q6／reference推导，不是捕获的真实ABI调用输入。原XML、9条派生输入、原父策略和244报告逐字带入；只按原方式重映射资产目录。源码七项native开关按保存的loaded-jaw父配方设置，原packed／inline／seed-bound和summary_fast保持。

私有 `SameCallDetail` 只在当前checker调用内持有一份明细，在原owner锁内复制完整numeric/flags，消费后清空。核同owner/model/handle/thread、qpos、完整p/R、有序pair、margin二进制值；错配、重入或复制失败回原full-detail。没有跨姿态证书缓存或共享可变scratch。observer只包装原one-ABI helper，没有替换ctypes符号或关闭方向提示原生路径。

## 原三对计时

初始化、模型构造和warmup与三对分开。每段测量含对称的状态结果收集、9条路径检查及私有匹配／复制开销。

| pair / 顺序 | wall 原版→候选 s | threadCPU 原版→候选 s | wall比 |
| --- | ---: | ---: | ---: |
| 0 / B→C | 1.550167→1.148111 | 1.549279→1.147567 | .740637 |
| 1 / C→B | 1.601443→1.146758 | 1.601166→1.146419 | .716078 |
| 2 / B→C | 1.622729→1.154425 | 1.621824→1.154080 | .711409 |

原组件子进程wall16.678060s、userCPU17.480275s、systemCPU.380877s、totalCPU17.861152s，包含warmup、三对、故障和方向提示复核。它不是某次抓放耗时，不能直接减到上一轮整程。

## 调用量和等价范围

- 三对每次571状态。固定轴ABI由1142→571，原pair行325470→162735，即每姿态去掉一次重复285对；不是减少每次对数。
- 补充方向ABI仍571次，原570次方向提示＋1次完整方向搜索保持。不能写成“全部native调用减半”。
- 所有状态返回、9份完整路径报告、refinement stats、额外方向提示、native witness history和清空状态均exact相同。244点报告与原保存报告exact一致，required==checked。
- 普通和direction_hints=True两组另验上述完整等价，原方向分支实际创建情况分别false／true。numeric/flags共享scratch view计数均0。
- 十种故障首query均落原full-detail；有序pairs反转和关闭handle仍按原谓词首态拒绝。其它故障后的通过源于原查询／补证，不能写成错误直接放行。原拒绝会提前结束弦，不强求检查第二个端点。

首次本机功能汇总错误地要求所有故障检查两个端点，导致pairs／closed负例的汇总false；业务拒绝正确。旧源码／结果／日志保留，修正汇总按实际已处理状态及首query事件。后续父配方配置版及可搬云版功能结果独立保存；本机后台Drone／Blender存在时只做功能，不采用其偶发wall作性能证据。

## 尚缺与接续

私有原型的thread负例修改线程标识，不是实际并发压力；当前571姿态主要是补证后可行状态。生产适配须补真实碰撞拒绝、复制所有权、重入／关闭与默认回退测试，再在固定源码、原Station入口做物理对照。组件输出等价不能替代这些验收。

## 2026-10-25：生产候选接入，原物理待验

`loaded_jaw_midpoint_details.py` 完整继承midpoint父配方，仅打开 `reuse_refinement_details`，不自动开启mesh补证；RoutePolicy和checker缺省均false。原summary／detail接口、全部pair／244采样、补方向、原1mm、裁判、90sim120wall及回退保持。

生产使用薄的 `summary_with_details()` 接口，在原锁内复制完整numeric/flags后返回拥有的明细；不安装私有拦截器。checker仅在单调用闭包中消费，核owner/model/handle、原查询与checker调用世代、q/p/R/pairs/margin。输入转换或复制过程中重入、关闭handle、错配或可选复制失败都不能领取旧明细；refiner重新执行原detail。通过的明细只作一次原完整校验，不重复校验或省去校验。主控制器、transport、separation和实测守卫四处构造均传显式选择，原默认不变。

代码owner的核心133项和集成73项通过；最后一行恢复原 `direction_hints is True` 语义后，专项11项再次通过，覆盖1、np.bool_、None及ndarray，不引入新truthy含义。根另独立47项通过，含真实busy转换／float／复制重入、拥有数组、不同bound、父策略唯一差异及真实bar-box中途接触拒绝。初次RIGHT测试误要求跳过原detail，已改为验证原拒绝与原回退；业务拒绝未改。以上是软件／静态几何验证，不算抓放成功。

固定源码后，round120将先运行新的 `production-component.py`，直接比较生产checker的False/True，不安装私有明细handoff。同9弦／571状态、原244和三对全部输出、wall／threadCPU重验；不沿用私有28.4%作为生产数字。三对无收益或不等价则保留组件并记物理not_run；符合原最小判定后再调用原五例Station：左主B→C、左已有第二放置点C→B、原中心候选回归。拟用kernel `muqiaoqiao/so101-refinement-details-physical-20261025`，尚未提交运行。

原物理尚未验，不记新抓放通过，不切默认。原搜索候选4/4通过与完整50Hz未过的结论继续有效。

## 2026-10-25：生产组件与原物理全部终态

Kaggle `muqiaoqiao/so101-refinement-details-physical-20261025/1` 已COMPLETE，只提交一次，固定源码`5badfff07c3cfbc2afab91a654e93e68d801462f`，整组终态前源码冻结。生产组件直接比较False／True，没有安装私有handoff；原571态／9弦／285对／244报告保持，六份源码与输入逐字一致。

| pair / 顺序 | wall 原版→候选 s | threadCPU 原版→候选 s |
| --- | ---: | ---: |
| 0 / B→C | 1.522757→1.105607 | 1.521776→1.105364 |
| 1 / C→B | 1.590496→1.145400 | 1.590163→1.145168 |
| 2 / B→C | 1.603944→1.127357 | 1.603599→1.126323 |

中位wall／CPU比.720152／.720157。状态、完整报告、refinement stats、方向及native witness提示exact相同；固定轴ABI1142→571、pair行325470→162735，补方向571保持。原244报告exact，组件无Station verdict；进程成本单列component-process.json。七项native配置匹配保存策略，缺独立loaded-library flags收据保留未知。输入是保存状态派生弦，不是捕获的ABI输入。三对通过后才接原物理，准入布尔已独立重算。

原`evaluate_station.evaluate(timing=True)`、4114字节runner、预检和依赖保持。单VM串行、原90sim120wall／1mm／全部碰撞／244／评分／回退不变。两侧实际偏好仅`reuse_refinement_details`不同，midpoint和loaded-jaw preload保持；中心无execution开发配置。

| case / UUID | 原裁决 | sim / episode wall s | process wall / CPU s |
| --- | --- | ---: | ---: |
| left_baseline / f5f4ed94-8eb4-4851-b9e4-5233525b61e8 | pass | 74.10 / 81.596613 | 82.681711 / 91.790980 |
| left_details / 8196cd1f-0fc6-4a7f-b9c6-84fbacab05f4 | pass | 74.10 / 76.671093 | 77.757704 / 87.026121 |
| left_second_details / b3470756-266f-452d-9c37-4aa12b6fe894 | pass | 76.78 / 82.310480 | 83.414360 / 93.916142 |
| left_second_baseline / 71fc0ba2-4fd6-4a09-9e73-760b80f71f9e | pass | 76.80 / 87.276136 | 88.416640 / 98.532488 |
| center_details_regression / 07ee3c5c-983a-4896-afa4-69aeb70070ab | pass | 77.48 / 47.174269 | 48.300959 / 58.106001 |

同侧request、resolved Station、初始qpos/qvel、静态场景、原OMPL／最终接近路径和最终认证exact，最小接近证书下界均1.002711796mm；它不是精确盘壁距离。主工位整条保存trajectory亦exact；第二工位释放段差一拍，不能声称全链exact。中心最小接近证书下界1.000057110mm，不据少量点宣传连续安全域。

主／第二工位hold均163／182拍，nonhold controller分别少4.665780／4.949293s。close的331拍controller由18.033019→12.710361s、19.329768→12.942966s；transport反由17.712339→18.634073s、19.511175→21.195428s。总收益并非少等几帧，运输段须继续同输入计数，不猜定原因。

五例planned／measured各244/244且valid；其它29／2点准入分列，不能混作闭爪。抓放／释放／脱离／回位、free=true／weld0／mocap0、双worker consumed／owned_ack／joined及cleanup_unconfirmed=false均核实；return仍同步。无安全停机或障碍接触，脱离后峰值力0N，最大XY漂移依次.214601／.214601／.169735／.169735／.200111mm。独立Monitor和ReleaseAudit五例exact、差异0、unknown=[]；实视频464／464／480／480／485帧与原记录一致。根另61项原件与算术检查通过；初读字段名和将29点准入混作244闭爪的检查错误已按实际schema修正，未改原数据或判据。

| case | 完整拍数 | P50 / P95 / P99 / max ms | >20ms |
| --- | ---: | --- | ---: |
| left_baseline | 3705 | 16.959 / 35.381 / 144.102 / 599.022 | 627 |
| left_details | 3705 | 16.981 / 36.463 / 103.479 / 411.613 | 663 |
| left_second_details | 3839 | 18.371 / 38.338 / 102.546 / 422.784 | 1026 |
| left_second_baseline | 3840 | 17.366 / 36.119 / 150.993 / 652.281 | 770 |
| center_details_regression | 3874 | 9.600 / 16.106 / 27.964 / 77.859 | 98 |

最大峰下降但P95及慢拍数增加，完整50Hz仍未过。两个候选approach index303的diagnostics_and_record另有114.908／125.142ms峰，无更细原因，不能猜成GC、磁盘或宿主争用。原wrapper的physical_status仍是旧pending字符串，candidate_origin.physical_started=false也只是开跑前声明；保留原件，以实际五个evaluation/status/report终态为准。

agent-link dsh实调120s超时，无有效审查结果；内部GPT只读未发现本轮复用新增回归。另确认父500dc47已有直接bound API特殊margin.__float__关闭native后的handle生命周期边界，普通checker预转float，本批不触发；未调用真实悬空指针，另留最小修复。

接续Owner=根Codex：保留候选、不切默认。transport/lift/hold同输入组件已完成，见下节；下一步先查完整运输弦中间采样，不从端点直接选择优化。连续X域、20＋20、完整50Hz、真实Carry HTTP整链未完成。Knowledge=already_covered，沿用Wiki§20。

生产原件在`experiments/colab-twin/output/refinement-details-physical-20261025/kaggle-v1/`，batch=`399996d5-3611-454c-9886-f3e474282647`。root-readback.json、independent-readback.json与TGZ保持Git忽略。私有复建入口`round120-refinement-details-physical/build_kernel.py --source-revision 5badfff07c3cfbc2afab91a654e93e68d801462f`；原evaluate命令显式指定`route_strategies/loaded_jaw_midpoint_details.py`复跑，对照用midpoint父版。

## 运输段诊断：额外入口存在，秒级归因尚不成立

固定源码`b236ff4c18314392f3f4cdcf128ee621e893e303`（相对5badfff只有文档），Kaggle `muqiaoqiao/so101-transport-detail-20261025/1` 已COMPLETE，单次提交。使用上一批两个原baseline各自的planning XML，资产目录仅重映射；lift／hold／transport每阶段均匀选9个保存帧，分别检查实测q6、reference q6、实测q5＋payload子谓词固定jaw=.015，共18组、162个声明查询。每组固定重复10遍，先B/C各预热一次，再AB/BA/AB；正式计时不装observer，计数另跑。原1mm、完整285对及七项native配置保持。

这些是物理推进后保存帧的派生输入，不是原始ABI调用或原控制弦；新鲜checker历史也不是现场阶段入口历史。只测机械臂几何子谓词，不测payload包络、worker／context、完整controller或抓放。mj_step及Renderer在组件内禁止；原bootstrap预检渲染单列。没有Station verdict或50Hz结果。

18组的所有返回、refinement stats、两类方向／witness历史在预热、计时及独立计数pass均exact。每组90返回；lift各组原80 clear／10需补证，候选固定轴100→90、原detail10→0、完整285对仍查，补方向仍10。6个lift组中4组三对wall／CPU全降、2组混合，不能统一报一个阶段加速比。

hold／transport各组90/90均原clear，两边固定轴90、detail0、补方向0、复制／provider消费0；候选仍进入summary_with_details90次。它没有减少这些样本的native工作，支持检查clear入口额外工作，但不证明整段秒级退化的唯一根因。

| transport样本 | CPU比中位 C/B | 配对CPU差中位 μs/query | 三对CPU／wall均更慢 |
| --- | ---: | ---: | --- |
| 主工位 measured q6 | 1.007335 | +3.207 | 否；CPU全慢但wall混合 |
| 主工位 reference q6 | 1.035761 | +14.834 | 否 |
| 主工位 q5＋.015 | 1.055900 | +24.376 | 否 |
| 第二工位 measured q6 | 1.032593 | +13.748 | 否 |
| 第二工位 reference q6 | 1.034404 | +14.511 | 否 |
| 第二工位 q5＋.015 | 1.048888 | +21.415 | 是 |

噪声反证保留：第二工位hold的q5＋.015没有少任何native查询，却三对都更快；reference组配对CPU差−216.9／+77.7／+66.6μs/query。不能从若干中位值外推原transport新增.922／1.684s，更不能宣称把50Hz问题定位完成。不据此重训、改精度、改阈值或直接改默认。

组件进程wall29.515147s／CPU30.673979s，含预热、对照、计数和文件输出，不能计作抓放节拍。实际loaded-library flags／metadata本次已归档，与配置一致；不是对上一批缺收据的补造。六输入逐字一致，根纯原件／算术78项和独立reader均通过，unknown=[]，ctypes ABI符号未改。agent-link zcode只读实调90s超时，无有效结论；根与内部GPT核源码及实际原件。

下一项只读组件：先在原分辨率下完整枚举这些保存q6→reference派生弦，数中间点是否也直接clear，再考虑复用既有batch入口作为完整原轴认证前缀。任何None／未认证／错误须回完整原scalar refiner；保留全部285对／原采样和244闭爪。旧round116的close九弦571态全需补证、batch前缀三对更慢，继续保留淘汰；不能因为运输端点clear就重贴旧失败为收益。尚未改生产或运行该新候选。

原件：`experiments/colab-twin/output/transport-detail-20261025/kaggle-v1/`，组件UUID=`7352919e-c4fc-4796-917e-9b87fd420b3d`；root-readback.json、independent-readback.json及TGZ均Git忽略。私有复跑入口`round121-transport-detail-probe/build_kernel.py`，同原bootstrap执行`SO101_ROOT=/tmp/so101-eval <original-runtime-python> probe.py`；输出按case／stage／variant分开，不池化成绩。Knowledge=already_covered，沿用Wiki§20；owner根Codex。

## 私有原型原件与复跑

原云件在 `experiments/colab-twin/output/refinement-detail-20261024/kaggle-v1/`，组件batch `ae67f286-8d55-4e6a-bcd7-291669ba91ab`，保持Git忽略。私有冻结五文件、版本失败和生成器在 `round119-refinement-detail/`；其 `cloud-prepare/build_kernel.py` 复用原bootstrap，逐字带入五文件，不改写测量函数。

```bash
env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 SO101_ROOT=/tmp/so101-eval \
  /tmp/so101-env/bin/python probe.py
```

命令在该五文件所在目录运行，默认warmup＋三对＋故障。`--functional`只做功能，不能给性能结论。Knowledge=already_covered，沿用Wiki《ROS2 与 FishBot》§20分开组件、动作与晋级；owner根Codex。

## 2026-10-25：完整派生弦的批量前缀组件

Kaggle `muqiaoqiao/so101-clear-chord-prefix-20261025/1` 已COMPLETE，源固定 `42f5a553f28ef3c431021b92613d879456aa6073`。组件正常终态，进程wall27.977228s／CPU29.101108s；无Station verdict、无物理积分。原preflight渲染单列。根直接回读122项通过，无缺项；Zcode只读审核90s超时，未取得有效审核，不计参与成功。

从上轮两baseline保存的post-step q6到reference构造54条完整派生弦，另保留9条close／571状态负对照。这些不是捕获的真实ABI输入或controller重放。原采样arm .005rad／jaw .002rad／max4096，全部285对、1mm与原完整标量补证回退保持。先逐点全弦筛选，再分组warmup和AB／BA／AB；构造与编译不含在成对计时内。

| 工位／段 | 弦／状态 | 原查询直接认证 | prefix接受／回退 | wall中位比 | CPU中位比 |
| --- | ---: | ---: | ---: | ---: | ---: |
| left_baseline／lift | 9／504 | 448 | 8／1 | 0.824379 | 0.823889 |
| left_baseline／hold | 9／325 | 325 | 9／0 | 0.724220 | 0.724300 |
| left_baseline／transport | 9／261 | 261 | 9／0 | 0.709250 | 0.709258 |
| left_second_baseline／lift | 9／504 | 448 | 8／1 | 0.882897 | 0.882792 |
| left_second_baseline／hold | 9／318 | 318 | 9／0 | 0.687821 | 0.687819 |
| left_second_baseline／transport | 9／261 | 261 | 9／0 | 0.708594 | 0.708670 |
| original_close_negative_control／close | 9／571 | 0 | 0／9 | 0.983820 | 0.983948 |

六组lift／hold／transport的三对wall和CPU全部更快，7组完整路径报告均exact相同。每组完整判定为true，required==checked；逐状态full检查全部285对认证。两个lift各56个姿态需要补证，候选回退完整56点，另外448点原轴直接认证。hold／transport全部raw clear，未删除几何检查，只批量执行原查询。close571点全部需补证，候选额外尝试9个原生点后仍完整标量571点；本VM观测三对略快不证明重复工作有收益，也不推翻旧round116全慢证据。

**不进入生产或原物理。** 六组的主检查器final q6与witness历史三对均不同；候选raw shadow最后姿态虽与baseline相同，独立owner状态不能作为主owner交接。close因全部回退，主姿态／历史相同。原型明确production_eligible=false，不能只凭报告相同领取生产资格。副作用、generation、完整MjData与异常回退尚需同owner验证。

完整原件：`experiments/colab-twin/output/clear-chord-prefix-20261025/kaggle-v1/so101-evidence.tgz`，组件UUID `e4f05702-5c50-4963-a633-b69ea92a998e`。根独立算术、原输入字节、全285对和完整244报告在同目录 `root-readback.json`；私有源码与复建入口为 `/home/muqiao/.cache/ros2-factory/codebuddy-so101-20261021/round122-clear-chord-prefix/{probe.py,build_kernel.py,root_readback.py}`。本轮未改生产源码／默认，无新IK、物理、连续域、20＋20或完整50Hz通过。

下一步仅做同owner默认关闭的私有原型：全raw clear才能接收；其它情况完整恢复并走原scalar／refiner。先在同一7组与原244对照验证报告、数据和提示历史，含异常和重入失效。通过组件以后才考虑薄生产选项与原Station两工位反序；不直接采用本版shadow。

### 已执行产物归档与清理

根在round122开始前核验round120／121原TGZ全部regular文件，与unpacked逐字节相同且无额外文件，才删除两个重复展开目录。round120169文件、round12129文件已验证；原TGZ保留，独立reader JSON用原生gzip压缩并验证解压字节一致。目标已分配空间分别减少102,473,728B／13,574,144B，共 **116,047,872B（约110.7MiB）**。共享盘空闲19,010,514,944→19,126,702,080B，不将其它任务变动算作本轮清理收益。

保留round120原TGZ14,897,121B、独立reader gzip1,628,781B、root读回与日志；round121原TGZ263,925B、独立reader gzip17,894B、root读回与日志。所需后续小输入已选入round122私有fixture；在途round122与其它Blender／Mint／模型目录未清理。脚本及逐项恢复命令：`round122-clear-chord-prefix/cleanup_previous.py`、`cleanup-readback.json`。

恢复任一轮时，将下例中的目录替换为 `refinement-details-physical-20261025` 或 `transport-detail-20261025`：

```bash
python3 -m tarfile -e experiments/colab-twin/output/transport-detail-20261025/kaggle-v1/so101-evidence.tgz experiments/colab-twin/output/transport-detail-20261025/kaggle-v1/unpacked
gzip -dk experiments/colab-twin/output/transport-detail-20261025/kaggle-v1/independent-readback.json.gz
```

Knowledge=already_covered，已读回Wiki《ROS2 与 FishBot》§20的分层验收与无收益反证；本轮新数据只留项目。Owner根Codex。

## 2026-10-25：同owner私有候选被功能检查拦下

round122独立reader另从原件核161项，0失败，共2744个screen状态；复核全部285对、1mm、完整244、三对算术和主data／hint差异。独立报告已压缩保留。原TGZ35个regular文件与unpacked逐字节相同且无额外文件后，删除重复展开并gzip独立报告；实际释放5,648,384已分配字节。原件位于`output/clear-chord-prefix-20261025/kaggle-v1/`（相对experiments/colab-twin），按前文相同tarfile／gzip命令可恢复。root读回、TGZ和小输入保留。清理原件为私有round123的cleanup-readback.json。

随后固定源码`2a167c095eb44bebacb2bfca591c09117a7f6262`，只提交一次Kaggle `muqiaoqiao/so101-same-owner-prefix-20261025/1`。云原生COMPLETE，但组件returncode1／complete=false；**不能记成功**。UUID `4cf17f15-fa36-43f5-a7cf-d99333b00707`，进程wall2.476774s／CPU3.241770s。functional在计时之前发现差异，七组性能对照全部未运行，原物理未启动。

私有候选复用原batch循环，同一checker／data／native owner，不临时切refinement标志。每次raw尝试前在原锁内复制完整MjData与witness；无分离证书才恢复并完整scalar补证。原invalid-q／native／FK错误前缀透传，非预期异常原样传播，避免重试洗掉瞬时错误。查询generation在可能覆盖scratch前递增且不回滚，只作失效令牌，不宣称与原版查询次数相同。内部GPT只读审查两轮指出并纠正两层吞错／重试问题；生产代码和RoutePolicy未改。

5项真实云functional为clear及一次性FK RuntimeError、ValueError、LookupError、KeyboardInterrupt。五项的原路径报告／异常、提示历史和后续原查询均相同；五项全部可见NumPy数据数组的字节比较均false。因此候选未过功能门槛、不进入计时或物理；完整50Hz、连续域、20＋20和默认均未变化。

本次诊断脚本遗漏保存具体差异字段，只留data_arrays_equal=false，无法归因。根保留原失败、不猜是初始化噪声、不先剔除字段。下一动作是保持私有候选逐字相同，在云端只补字段名、dtype、shape和数值差异；无论结果是否一致都不跑性能对照。生命周期close／重入／native-status／invalid-q注入仍未验，不能用这5项替代生产资格。

原件：`experiments/colab-twin/output/same-owner-prefix-20261025/kaggle-v1/so101-evidence.tgz`，私有复建`round123-same-owner-prefix/build_kernel.py`；下一只读字段探针`round124-data-field-diagnostic/`已准备，尚未运行。Knowledge=already_covered，仍沿Wiki§20分层验收；owner根Codex。

## 2026-10-25：数据差异已定位，原生NULL状态仍待实测

固定c15bde3，Kaggle `muqiaoqiao/so101-data-field-diagnostic-20261025/1`原生终态，字段诊断完成、候选仍未通过。组件UUID `866f57c8-454a-4428-a351-b9256eea9f26`，进程wall2.788950s／CPU3.528708s；performance_pairs_run=false，无Station verdict。候选same_owner_prefix.py与失败版逐字相同，未改算法或阈值。

每run观察179个Python NumPy字段。clear差异11字段：efm_K_rownnz、efm_aid、efm_ak/as/c/ca/ck/diag/sdiag及map_dof2idof、map_idof2dof；其余4项只剩上述7个efm浮点字段。qpos、几何姿态等其它字段没有观测到差异。报告／异常／历史／后续查询仍一致，不能据此改写原失败。

同版官方源码提供了可核实假设：[Python getters](https://github.com/google-deepmind/mujoco/blob/3.15.0/python/mujoco/structs.cc#L856)按模型尺寸暴露arena字段，[InitPyArray](https://github.com/google-deepmind/mujoco/blob/3.15.0/python/mujoco/structs.h#L981)只对空shape特殊处理，原[resetData](https://github.com/google-deepmind/mujoco/blob/3.15.0/src/engine/engine_io.c#L1231)将arena指针清为NULL；[字段宏](https://github.com/google-deepmind/mujoco/blob/3.15.0/include/mujoco/mjxmacro.h#L940)中的部分shape仍为nv／nactuator。NULL传给Python数组构造可能得到独立未初始化内容，不能以getter的shape判定原生数据有效。这是源码解释，当前云件尚未读取指针，未证明本次就是NULL。与nflex是否为0不能混为一谈。

下一步保持私有候选不变，用同包原生头文件生成只读arena指针观察器。逐字段记录NULL／非NULL及原计数，NULL显式作为NULL比较；有原生数据的全部NumPy数组继续逐字节比较，不能按efm或map名称整体排除。先验证初始／setup前后、5项functional和后续查询，再决定是否跑原7组计时；仍不接生产。原件`experiments/colab-twin/output/data-field-diagnostic-20261025/kaggle-v1/so101-evidence.tgz`；私有round124包含原probe、builder与提交回执，round125准备中。Knowledge=no_reusable_delta：因实际NULL尚未确认，暂留项目假设，不写共享知识；owner根Codex。

## 2026-10-25：原生NULL确认，同owner组件有收益但不晋级

固定 `f922da9c5147fbe6963cfb766c7409d4bd0377bd`，Kaggle `muqiaoqiao/so101-native-data-observation-20261025/1` 终态。UUID `b0f8df6b-5802-49e8-b8b7-8b74456b8e6b`，组件process wall30.162657s／CPU31.377228s；无Station verdict／无物理积分。原bootstrap、preflight、运行依赖和command／save保持，原preflight渲染单列。

只读原生观察器由同包 `MJDATA_ARENA_POINTERS` 生成78字段，未猜结构偏移、未解引用字段内容；header／runtime均3015000，原编译收据成功。76份观测的77字段为原生NULL，另有102个真实NumPy数组，共179个比较条目；contact唯一非NULL arena字段为_MjContactList，ncon=0。不能写成“179个有效数组”。efm_active、全部nefm*、nisland／nidof／nefc均0。

前轮11个争议字段在baseline／candidate均实测NULL。对每个字段额外调用两次Python getter，只记录所有权与shape，不读取内容：OWDATA=true、base=None、不同对象、不共址且不共享内存。它们确是独立临时数组，不能用其未初始化字节代表原生MjData。与[同版getter](https://github.com/google-deepmind/mujoco/blob/3.15.0/python/mujoco/structs.cc#L856)、[InitPyArray](https://github.com/google-deepmind/mujoco/blob/3.15.0/python/mujoco/structs.h#L981)、[resetData](https://github.com/google-deepmind/mujoco/blob/3.15.0/src/engine/engine_io.c#L1231)机制相符。新版观察将每个NULL显式保留为NULL；其余102有效数组仍全量字节比较，未按字段名删比较。原round123失败与round124差异原件不改写。

私有候选same_owner_prefix.py与round123逐字相同；更正的是观察方法。功能5/5通过：初始状态、make_prefix前后、路径报告、历史、有效数据／NULL状态及后续查询相同。一次性RuntimeError／ValueError在第2次FK保留原invalid；LookupError／KeyboardInterrupt按原类型传播、FK同为2次，没有被重试洗掉。原native-status／invalid-q／close／reentry注入仍未覆盖，generation仅为单调失效令牌，不宣称与scalar次数相同。

### 同VM原三对组件计时

完整MjData复制、回退、hint复制和前缀计数在计时内；模型、编译、checker／snapshot分配为setup，原生指针／数组观察在计时外。每组warmup后AB／BA／AB。表内wall、CPU均为候选／原版比，小于1更快。

| 工位／段 | wall三对原版→候选 s | wall中位比 | CPU中位比 |
| --- | --- | ---: | ---: |
| left_baseline／lift | 0.402492→0.356467；0.403173→0.351728；0.398769→0.356361 | 0.885649 | 0.885634 |
| left_baseline／hold | 0.132086→0.095441；0.132519→0.094383；0.131655→0.103357 | 0.722565 | 0.722573 |
| left_baseline／transport | 0.104418→0.076717；0.103794→0.075667；0.104495→0.083997 | 0.734709 | 0.734598 |
| left_second_baseline／lift | 0.438450→0.384557；0.417795→0.362422；0.421038→0.362845 | 0.867465 | 0.867455 |
| left_second_baseline／hold | 0.129205→0.096167；0.133769→0.094864；0.129989→0.100415 | 0.744300 | 0.744363 |
| left_second_baseline／transport | 0.113935→0.077116；0.107827→0.077656；0.109005→0.080868 | 0.720192 | 0.720156 |
| original_close_negative_control／close | 1.077678→1.082724；1.054478→1.120950；1.073826→1.080212 | 1.005947 | 1.005963 |

六组lift／hold／transport三对wall／CPU均更快；7组完整原路径报告、历史和q6相同，云内102有效数组＋77个NULL标记的比较回执也全部相同。screen仍覆盖原2744状态、285对、1mm；close244报告8次均与原件exact。两个lift仍8条raw-clear／1条完整回退；hold／transport9条全clear；close9条全回退，额外9次raw查询、原571scalar不减，三对全慢。这支持继续做仅运输段的默认关闭候选，不支持全阶段启用。

根179项和独立reader414项读回0失败。独立核原报告、全部hint／q6／时间／native状态、计时算术、编译C源和getter所有权。**原始数组bytes没有归档**：数组字节等价来自云内比较代码与各对回执，不能称下载后独立字节复算。下一生产验证应将所需原数组压缩保存，避免把这层缺证带入正式晋级。

**仍不生产采用。** 私有适配动态派生原batch循环，没有进入生产API、RoutePolicy或控制器。无新的原Station抓放、完整50Hz、连续工作区或20＋20结果。默认仍loaded_jaw_preload；原1mm、285对／244、原裁判和90sim/120wall未改。下一步做薄的显式transport-only前缀，保留默认refinement回退；补真实错误、观察器／binding、close／重入及generation边界，再按原同输入组件和两工位反序物理验收。不能直接复制私有源码变换或NULL观察器到控制器热路径。

原件：`experiments/colab-twin/output/native-data-observation-20261025/kaggle-v1/so101-evidence.tgz`；root-readback.json及independent-readback.json.gz保留。私有源码、来源、builder和提交回执在`/home/muqiao/.cache/ros2-factory/codebuddy-so101-20261021/round125-native-data-observation/`；原C源码／编译收据在TGZ内。

### 本轮追加清理与知识接续

round123／124各37个归档regular文件已逐字节核对，无缺失／额外文件后删除重复unpacked，保留原失败TGZ与root字段报告；分别释放471,040／512,000B。round125独立读回结束后42个归档regular文件同样核对，再删除展开、gzip独立reader，释放9,834,496B；目标已分配10,555,392→720,896B，独有TGZ／root／压缩reader和小fixture保留。对应私有cleanup-readback.json、cleanup-current-readback.json记录前后量及恢复命令。

本接续已记录的清理累计132,513,792已分配字节（约126.4MiB），不将共享磁盘其它任务的空闲变化算为收益。任一原件恢复：`python3 -m tarfile -e <该目录/so101-evidence.tgz> <该目录/unpacked>`；独立报告恢复用`gzip -dk <independent-readback.json.gz>`。当前没有拥有的本地FK／评测进程或在途云任务；未停他人Blender／FishBot／Drone，未动Mint。

Knowledge=pending：候选经验为“MuJoCo同版NULL arena getter不等于有效数据，按原生分配状态比较，保留原错误”。原Wiki《ROS2 与 FishBot》§20与开发知识入口均已有在途修改，本轮未并发写入或整仓提交。Owner根Codex；最短接续是读两文件现有diff，在原分层验收节补同版源码和本轮native NULL证据，并同步入口触发词，再独立读回。不得将本段pending当已回写知识。

## 2026-10-25 正式运输前缀：代码完成，云验收待执行

RoutePolicy新增默认关闭的 `transport_refinement_prefix`；显式 `loaded_jaw_transport_prefix.py` 仅在完整detail-reuse父候选上增加该选项。新validator仍使用同owner／同C循环，仅transport online_chord调度，close及全部244点保持原链。保守证书不足恢复原完整MjData／hint后完整回退；实际异常优先于绑定变化，不重放一次性失败。

本地83项mock／协议测试通过，含关闭owner、重入、绑定变化、invalid-q、观察器及首次异常；不能当实模FK或物理通过。独立审查发现并复现异常优先级缺口后修复，原反例保留。新生产实现的逐FK身份检查成本必须重新测量，不沿用round125私有速度数字。

复跑：`round126-production-transport-prefix/build_kernel.py --source-revision <本轮提交>`。沿用原Kaggle bootstrap、component slot及Station runner；正式7组＋5功能及完整数组bytes归档后，组件准入才执行左B→C／第二放置工位C→B／中心回归。当前尚未提交云任务，未产生本轮原物理结论。原默认loaded_jaw_preload不变。

## 2026-10-25 正式运输前缀：两工位原物理与中心回归

源码 `58da5048275cff2669e84f89ada0df5d92cd207a`。Kaggle private `muqiaoqiao/so101-transport-prefix-physical-20261025/2` 已终态，原bootstrap／runtime／runner字节保持，cloud拉回源码与提交的kernel相同。基线为完整detail-reuse父候选；仅新增 `transport_refinement_prefix=true`，不拿全局preload作弱对手。两工位B→C／C→B及原中心候选回归串行执行，无共享任务竞争。

| 原case | 原run ID | sim(s) | 进程wall(s) | 进程CPU(s) | 原裁决 |
| --- | --- | ---: | ---: | ---: | --- |
| 左基线 | 07f71a35-1a80-4422-9de1-2a4a4316f0fb | 74.06 | 74.963946 | 83.864978 | pass |
| 左候选 | 2432273e-69c5-4edb-b0f4-19bb59d7f906 | 74.02 | 73.590872 | 82.564069 | pass |
| 第二放置候选 | 19efdab0-a9f1-44af-b192-8605a8826de4 | 76.74 | 75.982074 | 85.634905 | pass |
| 第二放置基线 | 8fecd9fd-6bc4-40b9-a4c0-78caa5ce8b3a | 76.80 | 78.357657 | 88.159918 | pass |
| 中心回归 | 81030a70-a616-46ee-8ed2-94b1104e8df1 | 77.42 | 47.904504 | 57.466926 | pass |

左／第二进程wall分别省1.373075／2.375584s，CPU省1.300909／2.525013s。原请求、resolved场景、初始qpos/qvel、OMPL路径、实际接近路径及最终路径认证一致。非hold controller累计46.612581→44.652556、48.742175→45.800050s；hold为162／162和183／182拍。sim与hold微差完整保留，不把少1拍当加速，也不与round120或其它VM秒数串成累计收益。

正式组件先于物理完成：5功能、7组／各三对全部报告、覆盖、hint、q6及有效原Data字节等价。86份NPZ共56,841,270原有效数组bytes，每份102有效数组＋77原生NULL标记；独立解码复算，不再仅信云summary。运输两组wall中位比.842309／.823997，CPU.842314／.824007，全部6对均更快。close中位1.006343（两慢一快），完整571状态与原244报告一致，保持负对照，不在controller close启用。本组件进程31.327947wall／31.639800CPU包含准备、回放和存证，不是工位节拍。

5原物理均保留1mm、全部285对、planned／measured完整244、无障碍接触／无安全停机、free_object、weld0/mocap0、原2ms释放审计和完整回位。两左候选实有1195／1298批、34655／37642原状态及fallback0；中心原refinement关闭，走原direction batch，中心通过不当该前缀提速证据。独立715项全通过、unknown0；根重读原裁决与逐字段bytes也无失败（根字段数是存证检查，不作算法质量指标）。

完整50Hz仍未通过：左候选P95 36.469ms／477拍>20ms／max404.727ms，第二34.112ms／489／405.447ms；中心亦103慢拍。现有分段最大close的controller397.814／398.626ms，不能归给OMPL随机性或相机；planned／measured内部归因尚缺。下一项核现有闭爪244同步责任与worker交接，不以减少点数、阈值或全阶段前缀换成绩。保留显式候选，不切全局默认，不宣称连续X域或20＋20。

失败原件：v1误传短ref，fetch128，组件与物理0次；v2仅改完整提交参数。原cloud的physical_status仍留component_admitted_pending_original_runner，而stage=transport_prefix_physical_terminal、5份原verdict均pass；独立读回保留该警告，不回写原件。

证据目录：`experiments/colab-twin/output/transport-prefix-physical-20261025/kaggle-v2/`，含原 `so101-evidence.tgz`、`root-summary.json`、`root-readback.json.gz`、`root-physical-readback.json.gz`、`independent-readback.json.gz`、`next-bottleneck-readback.json`与cleanup回执。原物理批次目录UUID `5f8e184d-0367-4f4f-8d8a-9141751956d0`。私有round126保留build_kernel.py、production-component.py、原fixture、原station_probe、两reader、云精确源和提交回执；原CLI复跑仍使用STATION_EXECUTOR中的显式候选命令。

清理：v1五个与v2 266个regular原件逐字节相同、无额外／缺失后移除重复展开；3派生JSON gzip后逐字节回读一致，本轮释放104,292,352已分配B。原TGZ／最终视频／轨迹／输入均在归档保留。恢复：`python3 -m tarfile -e <kaggle-v2/so101-evidence.tgz> <kaggle-v2/unpacked>`；派生报告用 `gzip -dk <报告.json.gz>`。不把上一轮已释放量重复记入本轮。

Knowledge=pending：根Codex仍须先核原Wiki§20／入口在途改动，再串行写回native NULL和首次异常经验；本轮记录仅为本项目事实。无新平台、定时器、实体动作或其它聊天消息。

## 2026-10-25：实测闭爪归因与单行提示反证

源码固定`9cca89ab9e77df753296c8a6ff5f47089b47e338`。本节新增一次原左侧物理和两个只读／私有组件批次；三者范围不同，不串成累计加速。

### round127：原完整闭爪的实际时序

Kaggle `muqiaoqiao/so101-close-attribution-20261025/1`，原Station UUID `63bbbf0e-abab-4078-bce9-c4bb9d764e94`，74.04sim／85.055249episode-wall／86.564906process-wall／96.658863CPU。原裁决pass，planned／measured各244、原1mm／285对、抓放／释放／脱离／回位、自由物体weld0／mocap0通过，无安全停机或障碍接触；释放漂移.214634884mm，脱离后峰值力0N。44项独立检查全部通过。observer仅扩展原timing记录，原checker一次性观察恢复后调用，transport前缀仍1195次／34655状态／fallback0。

| 位置 | 原点数 | wall ms | CPU ms | 归属 |
| --- | ---: | ---: | ---: | --- |
| update1008，sim20.14，descend→close | — | 451.885330 | 约451.806 | update总量 |
| `_transition` | — | 442.047557 | — | 包含measured子项，不重复相加 |
| `measured_closure` | 244 | 441.842506 | 441.768244 | 原全扫 |
| 随后`online_chord` | 2 | 3.975422 | 3.978814 | 非第二次全244 |
| 同拍GC | — | .454 | — | 已包含于闭爪子项 |

普通close（排除进入拍）330次online／6362点，12.096503617wall／12.092411831CPU秒；含进入拍331次／6364点／12.100479039wall。最慢普通online为update1260，sim25.18，48点121.551492ms。lift在线143次／8008点，5.228489298wall秒。原planned_closure发生于初始化／replan，未被update观察器计时，不据本结果猜其耗时。

完整3702拍P50／P95／P99／max为17.507488／41.209125／117.995219／460.323155ms，880拍>20ms；这是插桩结果，完整50Hz未过。不能将本进程与round126未插桩进程绝对秒数作A/B。现有worker没有可直接接纳的closure任务，SweepBinding含实际起点、观察时序与上下文；提前完成但现场起点变化的证书不能直接复用。

### round128：保存原输入的cProfile

Kaggle `muqiaoqiao/so101-close-profile-20261025/1`。原XML与上述244／48点真实弦逐字保留，fresh query MjData／hint，先预热再cProfile；不是原历史MjData恢复，也不是Station任务。两原报告exact，34项独立检查通过，无未知。244点profile wall.572910651s，`_hint_detail`244次累计.077932469s；48点hint48次累计.015212753s。`_detail_arrays`488／96次分别是全285对＋单行hint各244／48次，不能解释成双倍全明细。两组所有点均需原几何补证，不能用raw-clear捷径跳过。

`production_component_not_admitted`与physical_started=false是该只读profile的明确边界，不是物理失败。原查询、native flags和全部采样保持。cProfile有插桩成本，不用其秒数预报生产加速。

### round129：单行hint校验等值但收益不一致，淘汰

私有GPT候选仅在已预热owner实例的`_hint_detail`校验已认证单行native数组；不支持／未认证／异常走原helper，原调用错误不被重试抹去。原全285对、native几何、方向、阈值与点数保持。11项无模型测试包含358个原AST差分输入；外部Codex CLI只读未写文件，未将其声称的14／492算交付。

Kaggle `muqiaoqiao/so101-single-hint-20261025/2`，原244／48点各AB／BA／AB。876次候选请求，fallback0；原report／hint／统计／generation／恢复同值，12份NPZ的102有效数组＋77 NULL标记独立原字节比较一致，共7,931,340B。独立117项检查全部通过、unknown为空。安装／恢复／计数已含计时，状态归档在计时外。

| 成对序号 | 244点wall节省 s | 48点wall节省 s | 合计wall节省 s | 合计CPU节省 s |
| --- | ---: | ---: | ---: | ---: |
| 1，B→C | .042334453 | .013309499 | .055643952 | .055792359 |
| 2，C→B | −.002614534 | −.000149354 | −.002763888 | −.002671905 |
| 3，B→C | .052240065 | .018366226 | .070606291 | .067639094 |

原三对均省>5ms且CPU均降门槛未通过。**淘汰晋级，不接生产，不追加同候选物理追绿。** 中位数为正不能消除反向对。私有helper还不具备生产observer／自定义方法身份回退合同，未宣称生产实现完成。

v1漏`arena_observation.prepare()`，baseline快照报RuntimeError，零完整配对；v2仅补setup初始化，候选不变。独立reader旧scene路径／旧字段／清理后展开路径错误已依据原TGZ修正，失败日志保留，不重跑云端。后续Codex CLI只读审查120s超时，不计审查通过。

### 原件、复跑和实际清理

私有复跑脚本均在`/home/muqiao/.cache/ros2-factory/codebuddy-so101-20261021/`：round127-close-attribution、round128-close-profile、round129-single-hint-validation，各保留build_kernel、精确云源码、提交回执、原输入和独立reader。复建沿用既有Kaggle component／Station入口，不新建调度器。

原件目录分别为`experiments/colab-twin/output/close-attribution-20261025/kaggle-v1`、`close-profile-20261025/kaggle-v1`、`single-hint-validation-20261025/kaggle-v1`与`kaggle-v2`。原TGZ、日志、root小摘要、gzip独立读回与cleanup-readback.json保持git忽略。

round127核53原件、round128核27原件、round129 v1／v2核31／46原件，归档与展开全部字节相同且无缺／额外；删除重复展开并压缩独立JSON，实际分别释放32,092,160／282,624／196,608／1,638,400已分配字节，合计34,209,792B。不重计round126或更早清理。

恢复指定目录：`python3 -m tarfile -e <目录>/so101-evidence.tgz <目录>/unpacked`；恢复派生读回：`gzip -dk <目录>/<对应报告>.json.gz`。只删已核可重建副本，原输入、最终证据、私有源码和失败保留。

下一项只读核已有loaded-jaw preload提前至lift的执行器力矩／采样成本。原6s闭爪和全部244不改；单帧力矩饱和不能证明20ms周期中等效。没有可靠收益不切默认，不宣称连续X域、20＋20或完整50Hz。
