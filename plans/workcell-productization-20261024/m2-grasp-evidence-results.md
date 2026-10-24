# M2 原物理抓取证据到网页

## 已交付的行为

原`PhysicalTaskMonitor.update`首次确认抓取后，执行器保存一个Grasp后置条件事件。它记录实际双指接触、抬升、无支撑、持物时长、时间及观察索引；没有复制原阈值判断。close或hold阶段本身不产生成功。原控制器、评分器、碰撞、1mm、244、90sim/120wall均保持。

原status与report携带`skill_evidence`。Station沿原task/attempt ID发布，网页明确显示“曾确认持续持物；不代表本回合完成”。后续失物、取消、清理或deadline失败保留原结果。显示回调仅收到独立深拷贝，不能修改保存的嵌套证据；断线警告一次，不能改变控制和原裁决。循环不新增文件写入。

这完成M2的一个物理证据接点，**尚未完成六技能生命周期、可组合行为树、halt后安全撤退、同世界重新定位与重抓**。

## 固定来源与原件

- SO101源码：`b21b1d9b54c07d1ba4d082a2bb689cd2aa528072`；controller/candidate/scorer Git引用一致且dirty_paths为空。原默认`loaded_jaw_preload.py`，异步回位开关保持关闭。
- 工作台：FishBot既有`codex/workbench-code-rebuild-20261018`，实现提交`92c2962`。复用原RobotStation、runtime和任务HTTP，不新增执行平台。
- 私有Kaggle：`muqiaoqiao/so101-m2-grasp-evidence-20261024` v1，原生COMPLETE；复用round107/round106包装器、原`evaluate_station.py --timing`及原运输取消探针。
- 原物理与独立读回：忽略目录`experiments/colab-twin/output/m2-grasp-evidence-20261024/kaggle-v1/unpacked/so101-evidence/`。输入仍为浏览器导出的X+20原配方；原件与云输入相同。
- 四类历史回放：同级`output/m2-grasp-evidence-20261024/{summary,success-replay,cancel-replay,ungrasped-replay,payload_lost-replay}.json`。回放不是新物理，未改输入或用重算结果覆盖原报告。

## 新原物理结果

| 指标 | 完整抓放 | 运输worker运行中取消 |
| --- | --- | --- |
| UUID | `3d3cefa8-0872-4203-ac3b-150e1dd3daf1` | `49f2d252-d660-440f-a158-de53c015c708` |
| 原verdict / code | pass / 0 | fail / 1，保持原规则 |
| 原task状态 | succeeded | cancelled |
| sim / episode wall | 77.900 / 57.770s | 30.240 / 24.098s |
| process wall / CPU | 59.011 / 69.557s | 25.284 / 30.047s |
| 轨迹行 / 实际观察行 | 3895 / 3895 | 1512 / 1511 |
| 首Grasp事件 | index1383，27.680s | index1383，27.680s |
| 事件数量 | 1 | 1 |
| 录像实数 / 原记录 | 487 / 487帧 | 189 / 189帧 |

两回合首证据相同：stage=lift，双指力1.689148/1.694116N，抬升34.866426mm，取料与放料支撑均无接触，原持物时长约1s。根按报告的实际观察行重放原monitor与helper，证据对象逐字段相同；status顶层证据与report相同，仅另带本次attempt UUID。

完整回合真实抓放、释放、脱离、回位通过；持物34.94s，静稳7.54s，70.542s脱离，释放XY最大漂移.208403mm，脱离后力0N。planned/measured244均有效，3895行arm_valid/finite均真，无障碍接触／安全停机；自由物体、weld=0、mocap=0。末拍回位最大五轴误差.102544mrad，速度最大9.48e-8rad/s；transport/separation均consumed/joined/owned_ack，无清理错误，默认没有return worker。

取消在30.220s确认原transport worker ack+alive后写专属marker，原检查于30.240s终止。原Cancelled、物理fail/exit1、task cancelled保留；worker abort_requested/joined/closed确认，无活线程或清理错误。取消末行已经推进物理，但未送入monitor，所以证据只记录1511行；last_elapsed=30.220s，原hold3.54s。没有把未处理末行补成3.56s，也未把历史抓取改成整回合成功。放置／释放／脱离／回位未到达，不计通过。

## 完整周期与规划

| 指标 | 完整抓放 | 取消前完整拍 |
| --- | --- | --- |
| 完整拍 / 中断拍 | 3895 / 0 | 1511 / 1 |
| P50 / P95 / P99 | 11.201 / 17.945 / 31.779ms | 8.323 / 14.793 / 18.133ms |
| max / >20ms | 51.915ms / 159拍 | 51.150ms / 13拍 |

完整50Hz仍未通过。上述不是性能A/B，不与上一VM的绝对秒数拼算加速或回归。完整回合接近solve .135929s／含认证elapsed .315287s，运输搜索2.690883s、worker2.778677s，脱离worker1.233226s；分项有重叠，不相加作总规划时间。取消未完成运输规划，不补造其完成耗时。

## 反例、软件与页面

- 四类真实记录回放：成功和取消均首事件27.68s；未抓住4500行无事件、原simulation_time_limit；seed37失物3404行曾28.80s确认，终局保持payload_lost。旧baseline取原专家报告，旧elapsed取已证pre-action初始时间；缺stage保持None，schema适配明确。
- 43项相关Python检查通过，含原Station结果保真、callback传递和修改／抛错回调隔离。12项网页执行数据检查及生产构建通过，保留2项原包体警告。
- 10项实际桌面／390px浏览器检查通过，写请求0、页面异常0。输入为真实记录回放的HTTP fixture，明确不是新物理任务；验证close/hold不误报、历史抓取与取消／失物分离、旧记录不补造及移动端不溢出。截图与报告在工作台忽略目录`workbench-review-tests/output/grasp-evidence/`。
- 根与内置GPT独立复核。已修显示callback的嵌套别名问题；未把它夸大为原物理裁判被篡改。CodeBuddy此前空正文，不计有效审查。

## 接续边界

本机已核BT.CPP4.10.0/MIT、Nav2 BT1.3.13/Apache-2.0。来源为`/opt/ros/jazzy/share/*/package.xml`及StatefulActionNode、BtActionNode原头文件；安装不等于SO101已适配。Nav2 halt可能等待取消future，不可塞入50Hz循环。重新run Station会reset新世界，不是同世界恢复。

下一步实现满足前后置条件的可halt技能，继续保留原任务owner、失败和worker清理；同世界停稳、支撑／可见性和撤退认证成立后，才允许恢复。M2整体、M3冻结20+20、M4同世界两件卸货与完整50Hz继续未完成。Knowledge=already_covered，沿用Wiki《ROS2 与FishBot》§20；本轮事实只留项目。
