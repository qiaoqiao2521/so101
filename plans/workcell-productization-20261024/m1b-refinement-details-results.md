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

接续Owner=根Codex：保留候选、不切默认，先按实际transport/lift/hold谓词做同输入调用与成本证据。连续X域、20＋20、完整50Hz、真实Carry HTTP整链未完成。Knowledge=already_covered，沿用Wiki§20。

生产原件在`experiments/colab-twin/output/refinement-details-physical-20261025/kaggle-v1/`，batch=`399996d5-3611-454c-9886-f3e474282647`。root-readback.json、independent-readback.json与TGZ保持Git忽略。私有复建入口`round120-refinement-details-physical/build_kernel.py --source-revision 5badfff07c3cfbc2afab91a654e93e68d801462f`；原evaluate命令显式指定`route_strategies/loaded_jaw_midpoint_details.py`复跑，对照用midpoint父版。

## 私有原型原件与复跑

原云件在 `experiments/colab-twin/output/refinement-detail-20261024/kaggle-v1/`，组件batch `ae67f286-8d55-4e6a-bcd7-291669ba91ab`，保持Git忽略。私有冻结五文件、版本失败和生成器在 `round119-refinement-detail/`；其 `cloud-prepare/build_kernel.py` 复用原bootstrap，逐字带入五文件，不改写测量函数。

```bash
env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 SO101_ROOT=/tmp/so101-eval \
  /tmp/so101-env/bin/python probe.py
```

命令在该五文件所在目录运行，默认warmup＋三对＋故障。`--functional`只做功能，不能给性能结论。Knowledge=already_covered，沿用Wiki《ROS2 与 FishBot》§20分开组件、动作与晋级；owner根Codex。
