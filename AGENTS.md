# SO101 project

先读PROJECT.md和README.md，再读对应模块的AGENTS.md。一个机械臂项目，跟随器、ROS/MES和场景是内部模块。
唯一开发根为本目录；旧路径为兼容链接。不要用repo-revival的旧快照覆盖本机跟随器。
`./so101.sh check`只做静态检查，不控制机械臂。保留workspace的未出生Git和损坏历史备份，不删除。
Humble语义尚未迁移到Jazzy；不静默更改发行版。mock硬件不是Gazebo，单元测试不是真机。
鉴权配置从环境注入；不提交标定、用户日志或凭据。当前迁移记录见../../plans/hardware-consolidation-20260915/。
