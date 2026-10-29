# 规划进程隔离：组件与原物理验收

## R146：同输入组件，主线程长尾改善但总成本增加

2026-10-29，Kaggle `muqiaoqiao/so101-process-isolation-component-20261029/1` 已 COMPLETE。固定源码 `95ca4a57cd5b036fa98e7bb746dacc46c6b8b171`，生产Python与R145相同。根GPT与原生GPT实现私有观察入口，未修改生产worker、原评分、默认或任何物理检查。

复用R80原回合 `5635508a-3b8b-47e5-be15-297ac10f0f51` 的96条hold观测。保留每条q6、geometric_reference、时间及全部字段，原request／admission选段规则不变。旧回合来源为 `dfb9fc329b2d99b24c4e346ea230d6389a43986c`，本轮不是新的RGB观测或物理回合。组件保留原R80的 `float_first_context.py`，不称当前默认路线的完整A/B。

两侧都调用当前原 `_run_transport_plan`。工作者在原 `_compute_transport` 入口准备完成后报告ACK，再共同释放；每条守卫仅运行原 `_configuration_sweep` 和原载荷路径检查；实际在线弦为55/55点，不与闭爪244／246混为一谈。对照按Thread→spawn、spawn→Thread、Thread→spawn执行。三对各96条全部处于两侧实际规划区间，无after-planner行计入收益。

| 对照 | Thread P95／max ms | spawn P95／max ms | >20ms：Thread→spawn | Thread／spawn 整案例wall s |
| --- | ---: | ---: | ---: | ---: |
| 1 | 22.703／24.653 | 17.590／18.825 | 39→0 | 7.813981／8.924950 |
| 2 | 22.270／34.903 | 15.288／18.575 | 15→0 | 6.216334／6.988948 |
| 3 | 20.096／31.425 | 10.390／11.632 | 7→0 | 5.178669／9.997219 |

全部守卫输出相同，规划路径保留分段边界及binary64逐位相同。六例原守卫有效；原生MuJoCo3.15.0模型序列化后数值状态相同、模型地址独立，Snapshot及每次TransportPlan往返一致。三个spawn子进程均exit0、joined；原线程均consumed／owned_ack／joined。root独立回读上述字段，另一个原生GPT reader以缺件、无重叠、非零子进程退出等11项反例检查后，实际结果valid=true，无缺件或解析错误。

**保留为进入原物理对照的候选，不切默认。** 三对局部守卫P95与超20ms均改善，但每个spawn整案例wall更长，不能称整程提速。初始化本身也存在波动，不能把全部wall差归因于spawn。

## 成本与取消边界

- 原模型pickle约67.25MB；父进程序列化0.378～0.396s，spawn启动调用0.198～0.208s。启动至实际规划入口ACK为1.763～1.807s，包含模型与子进程导入／配置；这些重叠字段不能再求和。
- 子进程实际planner调用1.670～1.854s，结果约27KB；pickle约0.060～0.077ms。父进程守卫后收取／等待0.670～0.791s，清理约0.097s。这些成本均在整案例wall内。
- Thread总CPU为8.693009／7.124539／6.074994s；spawn为11.128461／9.131168／12.118583s。Thread工作线程CPU已含在父进程CPU，不重复相加。首个Thread另有0.642395s回收子进程CPU，只计整体成本，不归给线程规划器。
- 取消沿原cooperative Event；没有强杀或原生调用硬中断。R146没有注入取消，诊断recv／join也没有硬上限，不是生产取消验收。
- 未调用mj_step，没有完整控制周期、任务成功或实际调度deadline成绩。历史完整50Hz未通过状态保持；原244／246同步扫掠也没有被移走。

下一候选仅隔离transport。在控制器初始化阶段预热spawn和模型，原线程只作小快照／结果I/O桥；保留原任务生命周期、当前q准入、载荷／碰撞检查。提前取消或未发任务必须回收闲置子进程；启动失败保留原线程回退及明确记录。separation仍走原线程，不在一轮中混改两条路径。随后在同一X224输入完成baseline→候选原物理；只有有可靠收益才到第二已有工位反序复测。

## 原件与复跑

私有入口：`~/.cache/ros2-factory/codebuddy-so101-20261021/round146-process-isolation/`。`process_probe.py`接受 `--source-dir`、`--input-root`、`--output`；`build_kernel.py`复用原云bootstrap与依赖，`kernel/`为已提交脚本，`accepted-v1/`已逐字核对。没有新增平台或调度器。

原件：`experiments/colab-twin/output/process-isolation-component-20261029/kaggle-v1/so101-evidence.tgz`；独立报告为同目录上层的 `method-readback.json`、`method-readback.md`。实际模型、Snapshot、96条原输入、每拍wall／threadCPU、规划重叠、所有路径和清理状态均保留。

第一次完整历史轨迹包超过Kaggle脚本1MB限制，两次提交均HTTP400拒绝；状态核对无接纳任务。第二次取得明确错误body后，仅改为上传实际选定96条全字段，其他四文件逐字不变，包降至183KB后首次接纳为v1。失败回执保留，未把拒绝算评测，也未改数据值或原裁判。原wrapt站点警告保留，实际组件exit0。

Knowledge=already_covered，沿用Wiki《ROS2与FishBot》§20组件、交接与完整任务分开验收。Owner=根Codex；Mint、实体设备及其他项目保持原所有权。

## 本轮空间收尾

磁盘曾仅余约90MiB。已逐文件核对四份旧SO101原TGZ，再清理其精确重复展开件，共释放 847544320 个文件分配字节。六份独有读回JSON／文本留在原路径，原TGZ、失败、配置和当前实视频保留；没有触碰模型库或其他项目。每项原路径、保留项和 `python3 -m tarfile -e` 恢复命令见新输出目录 `cleanup.json`。共享磁盘的其余变化不计为本轮清理收益。

## R147／R148：两取料位置反序原物理完成，保留局部长尾收益

2026-10-29，Kaggle `muqiaoqiao/so101-transport-process-20261029/1` 与 `muqiaoqiao/so101-transport-process-right-20261029/1` 均 COMPLETE。生产源码冻结95ca4a5，两个实际接纳脚本逐字回读一致。R147左X224为原版→候选，R148右X256为候选→原版；各对同VM串行、同配方。右配置与R143实际right输入全字段一致，launcher与R147逐字相同。不同VM绝对耗时不拼成累计加速。

候选仅在原初始化阶段预热transport子进程，原job线程作为小Snapshot／Plan的IPC桥；子进程运行原 `_run_transport_plan`。原当前q准入、全扫、载荷、上下文和单次消费均保留，separation仍为原线程。默认仍是原 `loaded_jaw_preload.py`，私有入口没有默认接管。

| 位置／实现 | 原判 | sim s | episode wall s | process wall s | process CPU s | 完整拍／>20ms | P95／P99／max ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 左224／baseline | pass | 75.90 | 50.781195 | 51.984385 | 61.290750 | 3795／99 | 16.587／29.754／52.686 |
| 左224／transport_process | pass | 76.42 | 50.751411 | 51.899476 | 63.008165 | 3821／48 | 14.971／27.346／60.193 |
| 右256／baseline | pass | 78.52 | 52.498580 | 53.639279 | 63.795143 | 3926／125 | 16.154／30.664／46.921 |
| 右256／transport_process | pass | 78.84 | 53.762599 | 55.285158 | 67.103984 | 3942／57 | 14.674／25.947／55.054 |

P95／P99统一使用nearest-rank `ceil(p*n)`。四回合partial均0，计时不扣除观察开销。原抓放、释放、脱离、回位均通过；安全停止／障碍接触0，物体自由、weld0、mocap0，原246点三次认证全部完成。视频原报告帧数完整；本轮不以回读报告代替视觉审美验收。

| 指标（原版→候选） | 左224 | 右256 |
| --- | ---: | ---: |
| hold >20ms | 47→1 | 71→14 |
| hold P95 ms | 30.745→13.516 | 32.537→21.976 |
| release >20ms | 23→28 | 32→25 |
| 全回合 >20ms | 99→48 | 125→57 |

**结论：transport等待段长尾改善在两处复现；整程提速未成立，完整50Hz未通过。** 候选左process wall仅少0.084909s，右反增1.645879s，CPU两侧增加。左hold多24拍、右多15拍，不作算法收益。右候选hold的P95本身仍超过20ms。释放段、同步闭爪认证与切换仍留下超时拍；左候选最大60.193ms在release、transport进程已退出，不能归因于运输进程。右最大55.054ms同样保留。

原循环按仿真时间推进，EpisodeTiming只有完整分段时长和仿真时间，没有实际计划释放／开始／截止期时钟。现有>20ms为计算预算超限，实际调度deadline-miss计数仍unknown。不得将P95低于20ms或局部worker收益写成完整50Hz通过。

### 实际进程与原判身份

| 位置 | baseline UUID | candidate UUID |
| --- | --- | --- |
| 左224 | `7ff2207f-9667-4911-a302-7ad54aeff3ba` | `0f5fd449-89f3-48a4-bd08-db661d108cca` |
| 右256 | `bbdb46c9-4f07-4b6c-af27-e83f5e32c343` | `892abb54-c925-4e2e-b13a-368a02ef8c52` |

两例候选均真实ready／planner_started，原job consumed，子进程exit0／joined，无inactive fallback、uncaught error或cleanup error。左／右预热1.691877／1.773415s；模型均67246696B；原planner在child内为1.316231／1.702978s，IPC桥含清理为1.405180／1.803729s。这些开销已计入原episode／整process wall，不能再相加或删去。子进程总生存期包含预热后的闲置，不冒充规划时间。

10项私有生命周期fake检查、R147读回7项反例和R148新增6项反例通过。它们不证明原生调用可硬取消；实际OS启动中断／部分pipe写失败／主机故障与任务取消仍未实测，不据此切默认。R148 Markdown阶段表复用时曾列名顺序错误，JSON键正确；仅修表头后重新读回，原件未变。

### 复跑与下一项

私有候选：`~/.cache/ros2-factory/codebuddy-so101-20261021/round147-transport-process/transport_process_launcher.py`，以 `--source-dir`、`--station`、`--output` 显式调用，默认仅此入口选择process；普通evaluate_station不变。R148目录 `round148-transport-process-right/` 保存完全相同launcher、右侧原JSON、反序builder和accepted-v1。入口与原样例均保留，可复跑。

原件分别为 `experiments/colab-twin/output/transport-process-20261029/kaggle-v1/so101-evidence.tgz` 与 `transport-process-right-20261029/kaggle-v1/so101-evidence.tgz`；两目录的 `method-readback.json/.md` 是独立回读。来源：根GPT编排、原生GPT实现／独立读回，沿用既有云CLI；不声称CodeBuddy生成本候选。

下一项只考察separation进程隔离。其request会更新原估计模型的geom_pos／geom_quat／geom_sameframe，并严格核size；需捕获真实完整Snapshot、原冻结模型与补丁，再比较原planner全路径、样本坐标、全部距离和pad vertices。若旧原件缺失，不用邻近帧猜或物体真值补。主release守卫带逐拍ratchet状态，没有同状态证据不能用静态检查代替它的长尾。R147已保存Snapshot全部字段值的可追溯映射和205个完整样本，但缺请求时两个原生模型、实际geom四数组和Plan.report_json原字符串；需要补真实捕获而非重跑无新增知识的对照。当前下一项未运行，原244／246同步扫掠的后台准入证明仍独立缺失。

Knowledge=already_covered；沿用第20节分层验收。两云任务与自有child全部终态，未启本地物理或改其它工位工作树。原件TGZ直接流读，未展开帧／模型，无本轮重复大文件需删除。
