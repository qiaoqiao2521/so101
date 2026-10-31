# 进度

## Current
2026-11-01：公开单仓整合、资料站部署和三个旧仓删除全部完成。so101/master为唯一SO101开发远端，原始数据和历史备份继续私有。

## Done
安全展开候选包；本地补丁检查与应用成功。未推送私有来源、未改可见性、未部署、未删库、未启动实体或仿真。

## Next
本地整合通过：Vue47测试＋Vite构建；Astro24资源／13页面构建、零断链及30浏览器检查；ROS44测试与两包构建安装。公开发布已获授权；接续master合入、资料站部署、Wiki／子模块保全及三旧库删除。

Knowledge=no_reusable_delta：本轮采用既有源码恢复和分层验收约定；新状态只写项目，不另建跨项目知识。


ROS选定两包 `colcon build --packages-select so101_bringup yolov8_detector` 已完成构建与隔离安装，恢复的八个bringup节点和YOLO可执行入口均已落盘。首次CMake自动选到用户Python3.11，因缺catkin_pkg失败；仅以 `-DPython3_EXECUTABLE=/usr/bin/python3` 选择Jazzy系统Python3.12后成功，没有安装或替换依赖。附带旧 `PYTHON_EXECUTABLE` 参数未使用警告保留；复跑只需Python3_EXECUTABLE。构建成功不代表节点运行、相机推理或实机成功。


## 历史备份与范围
三库bundle与恢复说明在 `/home/muqiao/备份/so101-consolidation-20261031/`。合计149,571,813bytes；各自bundle verify及空目录恢复fsck均通过，根再次独立验证bundle。docs/generated 1,034个非空文件共42,318,266bytes已包含。Wiki访问128和子模块外部对象保全仍pending；未删除旧仓。

## 本轮失败与保留警告
- git apply提示一处文件末尾空行：当前diff检查无空白错误。
- 根YOLO复跑目录笔误已改正；最终3项通过。
- CMake首轮用户Python3.11不含catkin_pkg；改选系统Python3.12后成功。
- Vite大分块、Astro默认i18n/404与CMake未使用变量提示仍保留，不改阈值隐藏警告。


## 本地交接与空间收尾
本地整合提交 `63ec08f` 包含113文件（原候选109、额外YOLO依赖声明和三份本轮计划），工作树源码已保存。未推送公开远端，未改默认分支／可见性／线上部署，旧仓仍保留。
已关闭本轮预览与隔离浏览器，删除自建重复候选files、隔离colcon build/install共3833856 allocated bytes。保留下载ZIP、patch、来源／审查／构建日志、Git历史bundle和浏览器证据；dist与依赖保留供可见性选择后的本地复核。磁盘free前后 24151904256/24156278784，不把其他任务变化归因本轮。
最短接续：先接收用户公开／私有选择；选定分支为 codex/so101-consolidation-20261031。完整ROS运行缺lerobot/ultralytics不自动安装；Wiki与子模块保全、资料站部署仍由根Codex接续，不能提前删库。


## 2026-11-01 — 发布授权与远端核对
已核qiaoqiao2521/238822818身份及so101公开、master默认。远端master仍为ec3d45a，当前整合分支仅领先2提交，可快进，无需改写历史。本轮113路径凭据特征复核未发现Token／私钥；私有来源保留授权写入来源清单。此前构建与测试对应执行源码未改，不机械重跑物理或ROS。三个指定旧库的备份缺口和部署依赖由独立审查接续，其他仓库不在删除范围。


## 2026-11-01 — 公开发布与资料站切换完成
公开 `master`、原仿真分支及整合分支已原子快进至78991ce，GitHub API独立回读一致。113个整合文件已公开，保留来源，原始录制／标定／备份未进入主库。

资料站从主仓 apps/resources 重建，24条内容、13页面构建及站内链接检查通过。新release为so101-78991ce-20261101，源站current已原子切换；原b12edee-20261018版本保留回滚。公网浏览器读取deployment.json确认sourceRepository=qiaoqiao2521/so101、sourcePath=apps/resources、sourceCommit=78991ce。根路径／SO101／FishBot／交付／来源／Pagefind及原独立demos/gansu-school均由源站返回200；没有覆盖现网Nginx或修改CF/DNS/Tunnel。切换前源站SSH一度超时，重查确认仍是旧版后才重试；urllib公网403不当作站点失败，隔离浏览器实际可访问。

三旧库refs与bundle一致，无新提交。GitHub Issues/PR/Releases/Tags/Actions artifacts/Deployments/Milestones/runs/Hooks/workflows均为0，每库10个labels已另存。Wiki认证Git128且公网wiki重定向主页，未发现当前可访问Wiki，原始响应留存。SO-ARM100固定2ca36d9完整快照87,257,688bytes已保全，229文件逐路径／blob／大小一致，含全部CAD与图片，补齐原gitlink文件树；不冒充整个上游Git历史。

剩余真实阻塞：当前gh OAuth只有repo/workflow等scope，没有delete_repo；日常Chrome未登录GitHub。已启动官方CLI设备授权等待用户授予删仓技术权限；不在源码记录设备码或凭据。三个旧仓尚未删除，授权后直接完成，不再次询问删除意图。


## 2026-11-01 — 三旧仓删除完成
用户完成GitHub官方CLI授权后，根核验同一qiaoqiao2521/238822818身份和delete_repo作用域。逐库重新核对仓库全名、admin权限、当前main与已备份Git提交一致，然后仅删除so101_ws、so101-ros2-arm、robot-resource-site。三次DELETE均成功，三次已认证GET均返回404，so101再次读取为public/master。详细回执在私有备份的deletion-receipt-20261101.json；不提交OAuth设备码或凭据。

本地旧资料站克隆源码和私有运维配置保留，移除其已删除的origin，原URL与操作回执留在私有备份，避免后续仍向旧仓推送。Mint脏工作树、FishBot仓库／工作台分支、其他GitHub仓库均未改动。

源码来源记录与README已更新为单仓实际状态。切换后的公网浏览器30项全部通过，隔离浏览器和本轮临时GitHub登录页已关闭。新构建静态文件保留作当前发布产物；旧线上版本保留回滚，未批量清理其他工作。完整算法、50Hz、实体与ROS运行验收边界不因合仓改变。
