---
title: 来源与使用说明
description: 查看资料的官方来源、核对范围、版本限制与第三方使用条件。
---

本站收录官方项目入口，并提供原创中文阅读说明。资源描述帮助选择阅读顺序；具体安装、装配和使用方法以原作者文档为准。本站与所列项目没有官方代理关系。

## 主要来源

| 来源 | 收录范围 |
| --- | --- |
| [The Robot Studio · SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100) | SO101 硬件、STL、STEP 与仿真文件说明 |
| [Hugging Face · LeRobot](https://huggingface.co/docs/lerobot/) | SO101 接入、安装、模仿学习与策略文档 |
| [鱼香 ROS](https://github.com/fishros) | FishBot 建模、导航与配套运动控制仓库 |
| [ROS 2 Jazzy](https://docs.ros.org/en/jazzy/) | 基础安装、教程、RViz、URDF 与 rosbag2 |
| [Nav2](https://docs.nav2.org/jazzy/) | Jazzy 导航概念与调参说明 |
| [micro-ROS](https://micro.vulcanexus.org/) | 微控制器与 ROS 2 的连接架构 |
| [MuJoCo](https://mujoco.readthedocs.io/en/stable/) | 物理仿真与建模文档 |
| [OMPL](https://ompl.kavrakilab.org/) | 采样式运动规划库 |

## 核对日期意味着什么

首批资源于 **2026-10-18** 核对来源与页面指向。此日期不代表上游发布日期，也不代表每项资源已完成安装、仿真、训练或实机测试。

ROS 官方文档可能要求浏览器校验。相关 Jazzy 页面路径同时对照 [ros2_documentation 的 Jazzy 源码](https://github.com/ros2/ros2_documentation/tree/jazzy/source)核对。链接打开受限时，可从官方文档首页进入对应章节。

## 版本与适配

Jazzy 文档是明确版本的学习入口，不表示所有 FishBot 仓库都已经支持 Jazzy。LeRobot 的安装、命令和数据格式也可能随版本变化。优先按设备配套教程选择版本，并保持文档、源码与依赖一致。

ACT 与 SmolVLA 收录为通用策略文档。具体模型能否用于你的 SO101，需要另行核对数据格式、动作空间、相机和任务条件。

## 使用与转载

第三方源码、模型、图片与课程各自保留原有条款。公开可访问不等于可以任意商业使用或重新打包销售。本站提供导航，未重新托管这些第三方材料。

[FishBot micro-ROS 运动控制仓库](https://github.com/fishros/fishbot_motion_control_microros)的 README 明示未经授权不得商用。引用或计划再分发相关材料时，请先向原作者确认。

发现失效链接或版本描述问题时，请通过已有沟通渠道提供页面名称、资源名称和问题现象。我们会据此核对原始来源。
