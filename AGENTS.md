# SO101 project

先读PROJECT.md和README.md，再读对应模块的AGENTS.md。一个机械臂项目，跟随器、ROS/MES和场景是内部模块。
唯一开发根为本目录；旧路径为兼容链接。不要用repo-revival的旧快照覆盖本机跟随器。
`./so101.sh check`只做静态检查，不控制机械臂。保留workspace的未出生Git和损坏历史备份，不删除。
Humble语义尚未迁移到Jazzy；不静默更改发行版。mock硬件不是Gazebo，单元测试不是真机。
鉴权配置从环境注入；不提交标定、用户日志或凭据。当前迁移记录见../../plans/hardware-consolidation-20260915/。
具身智能云端与 Drive 闭环约定：历史实验大日志、快照与分卷包统一归档至素材盘私有 Google Drive（https://drive.google.com/drive/folders/15B-Z4LA6BUavWRFkrnhb32J85X5vdKnU），详见 `docs/experiment-storage.md` 与 `experiments/colab-twin/output/CLOUD-ARCHIVE-20261107.json`。本机仅保留可运行源码、SpecMesh、查询/恢复索引及当前回放、训练数据与权重；新产生的大体积中间产物在云端读回核验后须同步清理主仓与所有 worktree 副本。
