# 2026-11-17 分支收敛

用户授权合并独有改动及依赖大版本升级。保留 Git 历史，不强推。

- 已合并 PR #1 Java-WebSocket 1.6.0、#9 zizmor-action 0.8.1、#4 npm minor/patch。
- 多连杆安全层历史实验并入 master 保存，但不恢复部署、不增加 so101.sh 入口。旧实验不是官方实现，也没有通过实体或当前物理仿真验收。
- 离线目录检查 0 failures；follower 4 项 unittest 通过。前端首轮 37 通过、4 因未安装 vue 无法加载，不能称完整构建通过。
- pip #14 存在明确约束冲突：learning 的 LeRobot 约束 numpy<2.3，而提议 2.5.4；mink 1.4 要求新 MuJoCo，但通用/learning 固定 3.3.7。不得仅为关闭 PR 破坏这些环境。
- Vite/plugin-vue、better-sqlite3、webpack-cli、Spring Boot 升级存在分支冲突，待同一主线进行兼容调整与构建。Maven 当前不可用，尚无后端编译证据。

仅静态与离线测试，无设备动作、GPU、服务器部署。


2026-11-17 补充：Vite 8.3.8 与 plugin-vue 6 合并解决锁文件冲突；前端 npm test 47/47 通过，生产构建通过（单块 572 KB 警告保留）。初轮缺依赖已解决。未做浏览器/机械臂验收。

2026-11-17 桌面 sequencer 本地尝试 better-sqlite3 13.0.3 / webpack-cli 7.2.3：依赖解析完成，但 build:main 10 个 TypeScript 错误（原仓库含 31 个空 TSX 占位）；Jest 21 suites 通过、7 失败，204 tests 通过、54 失败。未发布这两个升级，未验证 Electron 原生 ABI。PR #2/#7/#8/#14 保留，非仅因大版本拒绝。
