# 进度

## Current
根 Codex 在 codex/so101-consolidation-20261031 独立分支接续下载候选，用户可见性问题待答。

## Done
安全展开候选包；本地补丁检查与应用成功。未推送私有来源、未改可见性、未部署、未删库、未启动实体或仿真。

## Next
本地整合通过：Vue47测试＋Vite构建；Astro24资源／13页面构建、零断链及30浏览器检查；ROS44测试与两包构建安装。等待用户可见性选择，不推送私有来源。后续还需网站部署、Wiki／子模块保全，才能讨论旧库删除。

Knowledge=no_reusable_delta：本轮采用既有源码恢复和分层验收约定；新状态只写项目，不另建跨项目知识。


ROS选定两包 `colcon build --packages-select so101_bringup yolov8_detector` 已完成构建与隔离安装，恢复的八个bringup节点和YOLO可执行入口均已落盘。首次CMake自动选到用户Python3.11，因缺catkin_pkg失败；仅以 `-DPython3_EXECUTABLE=/usr/bin/python3` 选择Jazzy系统Python3.12后成功，没有安装或替换依赖。附带旧 `PYTHON_EXECUTABLE` 参数未使用警告保留；复跑只需Python3_EXECUTABLE。构建成功不代表节点运行、相机推理或实机成功。


## 历史备份与范围
三库bundle与恢复说明在 `/home/muqiao/备份/so101-consolidation-20261031/`。合计149,571,813bytes；各自bundle verify及空目录恢复fsck均通过，根再次独立验证bundle。docs/generated 1,034个非空文件共42,318,266bytes已包含。Wiki访问128和子模块外部对象保全仍pending；未删除旧仓。

## 本轮失败与保留警告
- git apply提示一处文件末尾空行：当前diff检查无空白错误。
- 根YOLO复跑目录笔误已改正；最终3项通过。
- CMake首轮用户Python3.11不含catkin_pkg；改选系统Python3.12后成功。
- Vite大分块、Astro默认i18n/404与CMake未使用变量提示仍保留，不改阈值隐藏警告。
