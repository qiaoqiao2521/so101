# Progress

## Current
2026-10-21 F2高度链路及10mm完整物理回合通过；网页编辑及原0高度API回归已通过，本地提交完成，远端推送受认证/网络阻塞。

## Done
- 新增place世界Z作为非负蓝盘底座高度。真实/规划XML、实体底座、编辑预览、控制器、异步快照与评分已贯通，默认0兼容。
- 原评分从真实盘面计算静稳中心，只平移参考高度；原2mm静稳容差、25mm抬升、1s、双指接触、1mm碰撞余量与释放再接触/漂移判据不变。
- 根整合回归113 tests、116 subtests通过。UI Jest27、ESLint及生产构建通过。
- 10mm场景run `6e537ac9-2ff0-47c9-a6e3-6a70cd8b08a9` 原裁判通过：74.36sim / 91.065wall；实际抬升48.294mm，持物31.64s，静稳12.98s。最终方块中心(0.2387313,0.1390601,0.0199607)m，实际蓝盘顶面12mm；末态双指力0、盘底接触true，回位最大误差0.000102213rad。
- 释放审计通过：最大XY漂移0.297838mm，脱离后最大接触力0.0155403N，真实free object、weld=0、mocap=0。没有脚本搬动物体。
- 负高度run `434484fd-d92a-4545-b828-fe823d83fbcd` 在物理前明确拒绝，state=failed、verdict=unscored、passed=false；未回退原场景。
- `evaluate_station.py`复用原执行器，输出独立run目录及机器可读evaluation；取消/缺报告/原失败不会计为pass。来源记录实际路径、Git状态和加载模块，不新增内容锁。
- 可导入JSON位于 `experiments/colab-twin/scenarios/factory-loading/`，包含原高度、10mm和负高度。

- 默认0高度通过隔离工作台API重新运行，task `46bbbf49-4f0f-4443-b0ed-59e76fd9f384`：74.76sim / 66.778wall，实际抬升41.272mm，持物31.40s，静稳7.52s。最终物块中心Z=9.960725mm、实际盘顶2mm，回位最大误差0.000102589rad，释放XY漂移0.265794mm，脱离后接触力0。原succeeded和原report.passed一致。

## Evidence
SO101忽略目录 `experiments/colab-twin/output/factory-loading-20261021/` 保留上述evaluation、原报告、轨迹、XML和录像。UI独立树 `/home/muqiao/worktrees/fishbot-f2-workcell-20261021` 的 `apps/fishbot-control-station/workbench-review-tests/output/station-workcell-height/` 保存10项无运动检查与截图。15mm仅编辑预览通过，不冒充物理回合通过。首轮QA定位器失败保留在旁边 `station-workcell-height-selector-failure/`；首次构建局部依赖缺失日志保留/tmp，补全原安装后通过，未改上游源码/版本。

## Remaining
源码/示例/评测及UI本地验收完成。远端推送待恢复命令级Git认证/连接后接续；共享无人机树和原服务未改动。本轮未运行20+20、训练、云GPU或实体。

## Next
根Codex复核新账号认证后，仅推送两个既有分支并读回远端SHA；不重跑已通过的物理回合、不修改共享无人机树。

## Delivery
- SO101实现提交 `15484b3`，分支 `codex/colab-twin-20261001`；工作台实现提交 `8005ea7`，分支 `codex/f2-workcell-20261021`。后续文档提交记录验收与推送阻碍。
- GitHub API曾确认有效身份qiaoqiao2521 / 238822818，两个既有公开仓库身份一致。随后SO101推送连接github.com:443超时，UI推送无法取得密码；同命令环境的gh auth status返回账户登录超时，gh auth git-credential无法取得凭据，未修改凭据/全局网络/账号配置。远端推送尚未完成。接续owner为根Codex；先在隔离GH_CONFIG_DIR复验身份与凭据，再推送上述分支，不要求用户发送Token。
- 本地入口 `http://127.0.0.1:5192/so101-station` HTTP200，隔离服务PID1927886；SO101_ROOT指向本交付树，独立任务目录在工作台workbench-tools/output/f2-height-20261021/tasks。普通5186当前未监听，未重启其他owner的服务。
- UI最终专用10项、原草稿13项均通过。桌面和390×844手机各13个STL加载；现有baseline原station逐字段保持。最终专用证据在 `station-workcell-height-baseline-preserved/`，原草稿在 `station-task-drafts-f2/`；首轮手机全页截图超时保留，视口截图修正后通过。

## Preserved Work
canonical `/home/muqiao/dev/ros2/projects/so101` 的跟随器、设备配置、记录及历史未跟踪文件保持原位。F2覆盖前逐文件比较交付基线15fa5bf，18个既有目标文件与基线一致；已限定同步26个本轮文件及忽略的物理证据，无冲突覆盖。其余有效遗留归原跟随器/迁移工作，由根Codex接续，最短入口为该树git status与原迁移计划；用户记录/配置不入本次提交。

## Knowledge
already_covered：沿用Wiki ROS2与FishBot第20节，动作完成、真实接触和最终裁判分开核对；项目状态留此，不并发写研究总文件或知识库。
