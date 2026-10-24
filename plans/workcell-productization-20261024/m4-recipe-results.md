# M4 配方交换与 M2 取消验收

## 交付范围

网页可导出、导入、编辑、保存、刷新和复制 `station-recipe` v1。配方包住原 Station，派发仍走原任务与控制器。历史验收只作引用；导入不执行，也不继承旧任务通过。

当前支持米制平移、SO101 固定尺寸静态几何、原八步及独立仿真回合。未知可选元数据保留；未支持的单位、旋转、动态几何、平台或时长明确拒绝。六技能控制、重抓恢复、车载高度和 FishBot 同世界连续卸货仍未实现。

## 固定来源与复跑

- SO101：`fd20512f345fa0ea8ab2027bb9f6d4cb88db6f90`；云运行的 controller、candidate、scorer Git 来源一致，dirty_paths 为空。原默认 `loaded_jaw_preload.py`，未启用异步回位候选。
- 工作台实现：FishBot `codex/workbench-code-rebuild-20261018` 的 `7ac8d86`，保留原 Lichtblick 面板／任务入口，不新建执行服务。
- 浏览器原件：工作台忽略目录 `workbench-review-tests/output/recipe-workflow/new-recipe.json`。它与首轮副本、云输入逐字节相同；内层 Station 逐字段等于原 `scenarios/workspace-station/x-plus20.json`。
- 云任务：私有 `muqiaoqiao/so101-recipe-exchange-20261024` v1，原生 COMPLETE。MuJoCo 3.15.0、NumPy 2.4.6、EGL；同 VM 串行两进程，不是性能 A/B。
- 原件：`experiments/colab-twin/output/recipe-exchange-20261024/kaggle-v1/unpacked/so101-evidence/`。batch 为 `recipe-exchange/7e61343d-efff-4ba3-95be-348acbbeb3db/`。
- 私有 wrapper：`~/.cache/ros2-factory/codebuddy-so101-20261021/round106-recipe-exchange/`，复用原 Kaggle bootstrap 与 ORIGINAL_RUNNER。来源为根 GPT＋内置 GPT；CodeBuddy 空正文不计有效审查。

正式复跑沿用 [执行入口](../../experiments/colab-twin/STATION_EXECUTOR.md)。将 `--station` 指向浏览器导出的原文件，执行原 `evaluate_station.py --timing`。原 90sim/120wall、1mm、全部碰撞和 planned/measured244 均保持。

## 实际完整物理与取消

| 指标 | 完整配方 | 运行中取消 |
| --- | --- | --- |
| UUID | `10f9c86e-4e7c-47f0-af94-c68d1df70daa` | `0181e8f1-873c-4918-a280-5d3723e5af8d` |
| 原物理 verdict / 退出码 | pass / 0 | fail / 1，按原样保留 |
| 任务终态 | succeeded | cancelled |
| 仿真 / episode wall | 77.960 / 55.544 s | 30.240 / 23.241 s |
| process wall / CPU | 56.735 / 67.325 s | 24.450 / 29.165 s |
| 抓取 / 放置 | true / true | true / false，未执行释放与回位 |
| 持物 / 静稳 | 34.980 / 7.540 s | 3.540 / 0 s |
| 安全停机 / 障碍接触拍 | false / 0 | false / 0 |
| 录像实测 / 原记录 | 488 / 488 帧 | 189 / 189 帧 |

完整回合真实抬升 41.002mm，planned/measured 闭合扫掠各244点有效；释放审计通过，70.602s 脱离，最大释放XY漂移 .208504mm，脱离后峰值力0N。自由物体、weld=0、mocap=0；末拍已回初态并停稳，controller_done=true。transport/separation 均 consumed、joined、owned_ack，无清理错误；本默认没有 return worker。根独立查看终态图并用 ffprobe 实数录像帧。

取消探针只在原 `_start_transport` 返回、worker `owned_ack=true` 且线程存活时写本任务 cancel-file；30.220s 实际触发，下拍原取消检查结束。原报告 error_type=Cancelled，cancel_requested/cancelled=true；worker abort_requested=true、joined=true、closed=true，原运行态 running 保留于 state_before_close，最终 rejected，无活线程或清理错误。包装方法恢复。它证明独立 episode 的协作取消与清理，不证明连续世界携物安全撤退或恢复。

晚到取消保持原 pass/fail、安全／清理失败保持 failed 的边界另有实际 mock 回归；没有把取消探针写成第二次抓放成功。

## 原完整周期与规划

| 指标 | 完整配方 | 取消前完整拍 |
| --- | --- | --- |
| 完整拍 / 不完整拍 | 3898 / 0 | 1511 / 1 |
| P50 / P95 / P99 | 10.771 / 17.118 / 33.579 ms | 8.020 / 15.030 / 18.088 ms |
| 最大 / >20ms | 60.075ms / 134拍 | 47.023ms / 13拍 |

数值按原计时各互斥分段求完整周期；取消末拍不混入完整拍百分位。完整50Hz仍未通过。完整回合接近规划 .128108s、含认证 elapsed .297912s，运输搜索2.826872s、运输worker2.905633s，脱离worker1.192246s；这些可重叠的分项不相加冒充总规划时间。取消回合运输被中止，不补造完成路线耗时。没有与不同 VM 的历史秒数拼算加速。

## 网页与源码核验

- 74项相关前端测试、64项相关Python测试、最终生产构建通过；webpack保留2项包体积警告。
- 最终浏览器18项通过：导入导出、历史引用不继承、编辑保存刷新、复制撤销、单位／旋转／动态／平台／负时长拒绝、390px及异步文件读取竞态。页面异常0，真实任务写请求0。
- 竞态使用隔离模拟响应，mock POST=1，保留新任务ID和取消入口；这不是网络物理取消证据。真实取消由上述原 MuJoCo 回合另验。
- 独立审查实复现负时长被旧导入器修成1的差异，已只在配方路径明确拒绝，普通草稿容错保留。最终浏览器负例确认拒绝后草稿未改变。

## 下一步与未完成项

M4交换切片已可使用，M4整体仍在进行。M2先补原物理证据与技能生命周期，再做可认证撤退、重新定位和重抓；不能把旧 stage 直接写成技能成功。M3冻结20+20、完整50Hz、连续工作区与同世界两件卸货均未通过或未实现。知识状态：already_covered，沿用 Wiki《ROS2 与 FishBot》§20；新数值只留本计划。
