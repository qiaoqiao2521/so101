# 旧工作台前端：组件与兼容入口

本目录保留 SO101 旧 Vue 工作台的姿态编辑、任务状态、设备状态与采集质量界面。它连接已有 Java MES API 和 ROS WebSocket，尚未改接当前 MuJoCo 工位运行时。

当前 MuJoCo 交互网页位于 FishBot 仓库的工作台分支；入口与跨仓依赖见 [合并审查](../../../docs/consolidation/2026-10-31.md)。恢复本目录不代表将旧 Gazebo／Java 路线重新设为主产品。

## 恢复范围

本次从固定旧提交恢复 39 个源码文件和 1 个演示音频，保留主仓库非空的 App、样式、测试与依赖锁文件。随后纠正采集质量面板的过时说明。逐文件来源见主仓库合并清单。

## 开发与验证

在本目录执行：

```sh
npm ci
npm test
npm run build
npm run preview -- --host 127.0.0.1
```

默认 API 为本机 8080，使用 `VITE_API_BASE` 和 `VITE_WS_BASE` 指向已授权的开发服务。浏览器页面启动不等于后端、ROS、仿真或真实机械臂已启动。

## 复用边界

- 优先提取姿态／序列编辑、运行事件、采集质量、状态新鲜度与放行理由。
- `LightArmPreview.vue` 使用示意几何；其 TCP 显示不构成 SO101 正运动学、碰撞或可达性验收。
- `FixedActionWorkbench.vue` 与 `PoseWorkbenchTab.vue` 有重复功能，后续整合保留一个交互入口。
- 旧演示百分比不能作为真实任务进度；任务结果由运行时与物理证据决定。
- 本目录是来源可追溯的兼容资产；实际接入当前主界面仍需单独验证 API 与运行结果。
