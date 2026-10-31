---
title: SO101 学习路线
description: 从结构文件与装配，逐步理解遥操作、数据和策略学习。
---

SO101 是开源机械臂项目。这里把硬件、模型与学习软件的入口放在一起，方便你按阶段阅读。官方硬件由 [The Robot Studio 仓库](https://github.com/TheRobotStudio/SO-ARM100)提供，装配与软件接入见 [LeRobot SO101 指南](https://huggingface.co/docs/lerobot/so101)。

## 先明确要做什么

| 阶段 | 主要资料 | 完成后应能回答 |
| --- | --- | --- |
| 看懂结构 | STEP、STL、物料清单 | 主臂与从臂分别需要哪些零件？ |
| 组装硬件 | 官方装配与校准指南 | 电机、控制板和供电是否匹配？ |
| 学习仿真 | URDF、MJCF 与仿真器文档 | 哪些参数描述外观，哪些影响运动？ |
| 采集示范 | LeRobot 真机学习流程 | 相机、关节状态与动作如何对应？ |
| 学习策略 | ACT、SmolVLA 文档 | 数据和模型是否适合当前任务？ |

## 建议阅读顺序

1. 阅读[装配前准备](/so101/assembly/)，核对零件与文件用途。
2. 阅读[模型与仿真](/so101/simulation/)，建立格式和验证边界的概念。
3. 阅读 [LeRobot 安装指南](https://huggingface.co/docs/lerobot/installation)，确认版本与所需依赖。
4. 阅读 [LeRobot 真机学习流程](https://huggingface.co/docs/lerobot/il_robots)，再决定是否进入数据采集与训练。

## 选模型前先看数据

ACT 与 SmolVLA 文档解释的是策略及其使用流程。本站将它们归入通用资源，未提供适配你这套 SO101、相机和任务的成品权重承诺。

找现有模型时，核对机器人类型、动作定义、相机名称、图像尺寸、归一化信息与任务描述。信息不完整时，先向发布者确认。训练损失下降也不能代替实际任务评估。
