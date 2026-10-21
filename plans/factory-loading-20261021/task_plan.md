# F2 厂区工位上下料

## Goal
交付可导入、可编辑的单刚性工件托盘→抬高目标盘任务，完成真实夹起、搬运、放稳、脱离和回位，提供原物理评测入口。

## Scope
复用MuJoCo、IK/OMPL、station_executor、原网页和评分；新增place世界Z作为目标盘底座高度，默认0保持原场景。蓝盘底座、实际/规划XML、释放高度、预览和原放稳指标一致。先选10mm抬高，保持同一方块、盘尺寸和原八步语义；不可达/非法高度明确失败。

## Ownership
根Codex维护场景/Station适配、可调用评测、场景JSON、整合和此三文件。控制worker独占控制器/异步快照与相关测试；评分worker独占learning_env/placement与评分测试；UI worker只改隔离worktree /home/muqiao/worktrees/fishbot-f2-workcell-20261021 的RobotStation与专用验收。共享工作台edf61a2以后无人机工作原位保护，不重启公共服务。研究总三文件和PROJECT由F0根维护，本任务不修改。

## Plan
1. 高度语义贯穿场景、控制和评分（complete）。
2. 导入/编辑/保存UI与代表性配置（complete）。
3. 定向回归、原0高度API复验、新高度完整回合和明确拒绝案例（complete）。
4. 原评测JSON入口、文档、本地提交、限定canonical同步、推送和远端读回（complete）。

## Acceptance
物理裁决保持双指真夹持、物体位移、实际目标盘接触与静稳、释放净距及完整回位。记录场景/任务ID、运行方式、加载候选引用、裁判版本、单位、原裁决、失败原因和产物路径；未运行或缺裁判不记成功。策略演化只允许控制器/规划实现，不允许修改场景/评分/阈值冒充改进；不用内容哈希限制手工编辑。

## Next Step
用户从5192导入高盘任务并修改高度；后续新高度逐任务验证。共享无人机树保持原owner。
