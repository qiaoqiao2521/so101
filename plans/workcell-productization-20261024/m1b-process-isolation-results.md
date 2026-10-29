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
