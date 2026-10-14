# AlphaNIST 官方资产与 SO101 本体合同审查

2026-10-14，Asia/Shanghai。SpecMesh v1.1。状态：review_complete / waiting_official_assets。

## 目标与授权

用户通过协作对话要求共同推进软件方向，并明确补入AlphaNIST。根转交本项目进行官方交付和SO101接口审查；本Agent已读回原人类消息。只维护SO101计划，不编辑ROS2研究根三文件。

先保全[已验收的固定方块完整抓放](../graspgenx-feasibility-20261014/progress.md)，再核对官方源码、权重、许可和接口。选择大于努力：缺官方发布入口时不造论文复现替代品，不触发训练、云GPU、实体操作或旧学习任务。

## 判定与接续门

当前官方资产门未过，交付只指审查。最短官方接入入口目前是[官网](https://alpha-nist.github.io/)及[论文v1](https://arxiv.org/html/2610.13354v1)，没有核实可运行的AlphaNIST命令。

待官方发布后，依次核准出处与许可、固定revision/权重hash、读取观察/动作schema及控制器、隔离加载官方Panda环境、完成原生单回合。取得真实资源实测后才判断4GB或已有云额度是否适合推理；不把训练GPU-hours当作推理显存要求。

只有原生门通过，才核准SO101自由度、完整姿态可达性、夹爪、接触和传感映射；不能补零/截断动作、用IK替代论文策略后仍称AlphaNIST迁移。机器人能力缺口需明确再决定最小适配，保护现有执行链。

## 验收边界

官方交付状态与接口差异都有来源；未知明确登记，训练、单件/多件评测和实际部署分别报告。现有GraspGen-X/IK/OMPL成绩只作工程比较。策略内涌现排序与显式工作流编排分别验收。洗衣柔性物体与实际衣物处理不在本项目当前范围。

来源、缺口与具体接续见[findings](findings.md)、[progress](progress.md)。
