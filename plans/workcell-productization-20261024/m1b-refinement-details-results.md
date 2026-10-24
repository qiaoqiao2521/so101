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
