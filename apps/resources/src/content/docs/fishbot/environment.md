---
title: FishBot 环境准备
description: 对齐系统、ROS 发行版、源码分支与硬件版本。
---

先核对版本，再复制命令。教程中的 Ubuntu、ROS 发行版、仿真器和源码分支是一组配套条件。

## 保留一张版本表

| 项目 | 需要记录的内容 |
| --- | --- |
| 电脑或上位机 | CPU 架构、系统名称与版本 |
| ROS 2 | 发行版，如 Humble 或 Jazzy |
| 源码 | 仓库地址、分支或提交版本 |
| 仿真 | 仿真器名称与版本 |
| 机器人 | 底盘型号、控制板与固件版本 |
| 传感器 | 雷达、相机或 IMU 的型号与驱动 |

2026-11-02 核对时，[FishBot 建模仓库](https://github.com/fishros/fishbot)默认分支为 `humble`，没有 `jazzy` 分支。[FishBot 导航仓库](https://github.com/fishros/fishbot_nav)公开分支只有 `main`；README 仍给出 `-b $ROS_DISTRO` 的克隆写法，与当前分支情况不符，不能直接照搬。

先核对实际分支、套件教程和依赖，再选择环境。将源码下载到本地不等于已适配另一 ROS 发行版。

## 新学 ROS 2 从哪里开始

[ROS 2 Jazzy 官方安装页](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)说明其支持的 Ubuntu 二进制安装环境。Jazzy 的 Ubuntu 二进制包对应 Ubuntu 24.04，支持 amd64 与 arm64。已有套件若配套其他发行版，应先保持配套环境，再评估升级。

Jazzy 是支持至 2029 年 5 月的 LTS，已不是最新发行版；[官方发行表](https://docs.ros.org/en/rolling/Releases.html)已列出 2026 年 5 月发布的 Lyrical。本站保留 Jazzy 作为明确版本的学习入口，不代表 FishBot 全部源码支持 Jazzy，也不要求已有套件追新。

安装基础环境后，按 [Jazzy 基础教程](https://docs.ros.org/en/jazzy/Tutorials.html)学习命令行、工作空间和包。进入 FishBot 源码前，先理解发布者与订阅者如何交换消息。

## 分清上位机与控制板

上位机运行 ROS 2 节点、可视化和导航等软件。控制板承担底层采集与运动控制。使用 micro-ROS 的系统还涉及客户端与 Agent；其职责可从 [micro-ROS 架构说明](https://micro.vulcanexus.org/docs/overview/features/)了解。

软件编译成功只证明构建完成。接入硬件后，仍需分别确认设备识别、通信和消息内容。更换固件前，应先核对板卡和配套说明；本资料站不提供通用刷写命令。
