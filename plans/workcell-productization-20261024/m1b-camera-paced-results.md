# R157–R160：原生全扫回放与异步相机实际对照

日期：2026-10-30。Owner：根 Codex。候选来源：复用 R79 AsyncCamera、R154 双规划进程和 R153 固定节拍；根 GPT 与原生 GPT 工作者完成组合、实际发令观察及独立回读。

## 结论

X224 同步→异步、X256 异步→同步，两 Kaggle 实例内分别对照，原物理 **4/4 pass**。异步相机降低了两位置的主循环感知占用、计算慢拍和发令迟到，保留显式实验候选。右侧总耗时、P95 和最大拍反增，**没有可靠整程提速，完整 50Hz 未通过，不切默认**。

连续 X 沿用[单字段开发配方](../../experiments/colab-twin/scenarios/workspace-station/fixed-tray-x-editable.json)：只改 `pickup_request.position[0]`，开发建议 224–256mm。已有四位置原物理证据；每个新请求仍做原视觉、IK、碰撞及全扫，不外推所有中间位置必成功。

## 固定条件与发令时钟

- 实际生产／控制器／裁判源码仍为 `95ca4a57cd5b036fa98e7bb746dacc46c6b8b171`。云接收源码与提交包逐字相同；右包的七份执行文件与左包完全相同，只换既有右工位和先后顺序。
- 两边都使用 R154 双规划进程；唯一策略变量为同步或 R79 异步相机。原 640×480、RGB 定位、遮挡拒绝、源时间戳、1s TTL、90sim/120episode-wall 保留。
- 两边使用相同观察器，直接在原 `data.ctrl[:]=command` 写入前后计时。逐 tick 与原完整周期、轨迹 command 对齐；观察开销仍计入原拍。写入确切时刻位于两个时钟之间，不用 controller 返回时间代替。
- 原 epoch 每 20ms 释放一拍，不跳拍。计算超过20ms、core deadline、普通 tail deadline、发令迟到、相邻指令间隔分别记录。终态清理尾段单列。
- 相机合作退出；native render 挂起时仍不能保证硬取消。正常清理通过不代替异常取消测试。

## R159／R160 原物理与运行成本

| 位置／模式 | UUID | 原判 | sim s | episode wall s | process wall s | process CPU s |
|---|---|---|---:|---:|---:|---:|
| X224 同步 | 63c8d8e0-956a-4d5e-b299-0413981c83b7 | pass | 75.60 | 90.563918 | 92.094504 | 68.547690 |
| X224 异步 | 333c1a2a-ce10-4699-8686-36c22db37629 | pass | 75.52 | 90.462430 | 91.946746 | 67.756944 |
| X256 异步，先跑 | 99e8676b-1bad-45c4-8fae-8d2c637db6b7 | pass | 78.02 | 92.822102 | 94.366800 | 68.696743 |
| X256 同步 | 205370e8-9961-4651-b7cc-ea9cfc098add | pass | 77.94 | 92.001312 | 93.593116 | 67.691429 |

相对同实例同步版，process wall 左少 .147759s、右多 .773685s；CPU 左少 .790746s、右多 1.005314s。sim 左少 .08s、右多 .08s 为等待长度变化，不记为算法加速。跨实例秒数不累计。

| 位置／模式 | transport planner s | separation planner s | T/S prepare s |
|---|---:|---:|---|
| X224 同步 | 1.335070 | 1.139070 | 1.710837 / 2.252524 |
| X224 异步 | 1.339155 | 1.076640 | 1.687286 / 2.227478 |
| X256 异步 | 1.484602 | 1.071347 | 1.731086 / 2.219815 |
| X256 同步 | 1.393050 | 1.089861 | 1.689278 / 2.263803 |

预热、模型传递、规划、回收均保留原进程计时；这些嵌套成本不能再相加成总时间。

## 完整周期与实际发令

| 位置／模式 | 完整拍 | >20ms | P95 ms | max ms | core deadline | 普通 tail deadline | 发令确定迟到 |
|---|---:|---:|---:|---:|---:|---:|---:|
| X224 同步 | 3780 | 33 | 15.255006 | 49.690406 | 62 | 62 | 38 |
| X224 异步 | 3776 | 20 | 15.045165 | 50.046988 | 38 | 38 | 23 |
| X256 异步 | 3901 | 24 | 14.176508 | 47.948455 | 43 | 44 | 30 |
| X256 同步 | 3897 | 30 | 14.089019 | 44.553631 | 56 | 56 | 37 |

四例 partial=0；发令写入括号跨截止点的歧义计数均0，表内迟到均在写入前已发生。普通 tail 仍完整核算，右异步比 core 多1次违约，不能省略。

相邻发令间隔中位均约20ms，但最大为左同步57.443／异步59.404ms、右异步56.336／同步54.343ms。平均频率与 P95 不能代替完整50Hz；此轮没有勾选该门槛。

左 approach 慢拍13→0，右12→4。主线程 perception 最大左20.835→.941ms、右20.904→1.340ms。两侧均减少同步图像占用；右剩余4拍不能全部归因图像。左采图拍 perception 中位20.262→.846ms，采图拍完整周期最大32.489→19.527ms。

异步左13、右12份循环观测全部交付且有效，源时间保持原值；交付时源年龄20–40ms。初始化另列。左14份含初始化定位记录跨模式逐字典相同。晚到不能改写为“刚拍摄”，静止目标冻结后的年龄语义也没有修改。

## 原物理与清理仍完整

四例原抓取、搬运、放置、释放、脱离及回位终态通过，无安全停机或障碍接触，free_object=true、weld=mocap=0。释放最大漂移左两例均.172283mm；右异步.187154mm、同步.186922mm；脱离后峰值力均0N。回位误差均约.000102544rad。

原 planned closure／预收爪／实测闭爪三次246点全部执行；transport admission 左29、右28，separation chord2，205保存样本的当前姿态准入完整。原 native checked=successful、无回退；没有用旧q证书或省略几何对。

运输与释放真实子进程均 ready、实际规划、consumed、owned_ack、joined、exitcode0，无未知回收或清理错误。两异步相机 context_closed／joined 均真；源绑定恢复、观察器错误与诊断错误均为空。四份独立读回证据完整；不是仅以 COMPLETE 或退出码0判成功。

## R158：保留逐像素失败，定位消费者等价

组件在同源码恢复14份已有真实渲染输入，按 AB／BA／AB 共42对。**原 `passed=false` 保留**：42对图像都非位级相同，每帧1–58个像素、总900个通道差值全部±1。同步自身跨轮42对也有41对出现同量级差异，因此不能把它归为异步独有的大幅偏差，也未证明具体底层原因。

42份原定位字典完全相同且有效，目标bbox内RGB变化0；主输入、源数组、恢复字段、时间戳与清理检查通过。保存图像用本地 OpenCV4.6.0 原公式复算，最终mask XOR均0；云版本5.0.0.93，不能把本地mask核验冒称云版本逐位证明。worker内部MjData未逐字段落盘，不补称字节一致。

据此把 R79 留作原物理候选，随后才有上文4/4实测；没有删除像素失败或改原物理阈值。组件本身不证明完整控制周期或抓放。原五项相机语义测试在云通过，sitecustomize/wrapt警告保留。

## R157：原生246点基线，不是提速结果

消费R156首个实际 `measured_closure`，对应 approach→pickup_preclose；不是最终下探闭爪。246次、285对、70110个pair结果逐字节重放一致，原flags及全部提示输入输出保留；输入未改、错误为空、handle已释放。

原生调用合计32.880268ms，thread CPU32.897964ms；创建几何context47.989425ms、缓冲准备3.979028ms、比较2.895655ms、cleanup.020581ms，组件总计92.397065ms。创建context不是每拍热点；组件不是完整周期测量。70292次轴评估已接近每pair一次，不支持继续盲调搜索顺序。

独立pair分块也不直接成立：原native有整帧回退、按geometry共享的witness提示及全对有效后提交历史，不能只拼接两个独立块来保持原结果。未制作或运行这种候选。

## 下一步与边界

两异步回合仍有同步全扫／准入慢拍。左释放段另有9拍慢：部分physics_and_guards达9–13ms，与controller相加后超时。下一项 R161 只细分原10次物理推进、接触力、release audit、障碍扫描与末次forward，先查真实成本；当前仅私有准备，尚未运行。

旧R132异步全扫仍欠实际binary64 FK保守误差界、当前请求网格／终点与生命周期覆盖。R143已提供小漂移实测，不用相同物理重复采集；离散差值不能替代连续偏差箱证明，也不能把原246次fresh checker调用改写为“已执行”。保持原同步认证，不降低1mm阈值。

Knowledge=already_covered：沿用 Wiki《ROS2 与 FishBot》§20的分层验收。新实测和失败留本计划。

## 原件与复跑

原TGZ位于 `experiments/colab-twin/output/`，Git忽略，未重复展开模型或帧：

- `input-components-20261030/kaggle-v1/so101-evidence.tgz`：R157／R158组件，包括像素失败。
- `paced-camera-composition-20261030/kaggle-v1/so101-evidence.tgz`：R159左同步→异步。
- `paced-camera-right-20261030/kaggle-v1/so101-evidence.tgz`：R160右异步→同步。

云入口分别为 `muqiaoqiao/so101-input-components-20261030/1`、`muqiaoqiao/so101-paced-camera-composition-20261030/1`、`muqiaoqiao/so101-paced-camera-right-20261030/1`，均已终态。包内保存实际源码、输入、原报告与进程计时。

私有可复跑目录前缀 `/home/muqiao/.cache/ros2-factory/codebuddy-so101-20261021/`：

- `round157-native-abi-replay/replay_native.py`：原生重放；需要原R156输入及原编译配置，在云执行。
- `round158-camera-composition/build_kernel.py`：原组件包；`read_camera_rgb.py`只读已保存图像。
- `round159-paced-camera-composition/launcher.py --source-dir SRC --station FILE --output OUT --camera sync|async`：原评测薄入口。相邻冻结依赖由 `build_kernel.py` 完整打包，不另造执行器。
- `round160-paced-camera-right/build_kernel.py`：复用R159原包，只换右输入和反序。
- 两物理目录的 `read_result.py --tgz TGZ --output JSON`：标准库原件回读，同时写MD；右reader保留28点准入。对应纯反例8项／3项通过，不当物理通过。

本轮cleanup收据与空间变化见[progress.md](progress.md)及右侧output目录。原失败、最终证据、源码与可恢复输入保留。
