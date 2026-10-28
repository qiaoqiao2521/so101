# X方向实际视觉输入敏感性：原IK与全几何18/18通过

日期：2026-10-28。R136，源码固定 `6cf337b6c66deb7e9c5583045f514b2f5f046b26`。承接[两中点网页原物理](m1a-x-web-midpoint-results.md)及[第二放置工位](m1a-x-second-place-results.md)。本轮是实际MuJoCo规划模型的几何组件检查，没有物理步进、OMPL或新抓放成功。

## 输入与原检查

取R134首个有效RGB中心：左 `(0.22412545947042734,-0.13050833816470292)m`，右 `(0.2556298526685876,-0.13050833816470292)m`。逐侧使用原 `uncertainty_m`：左 `.001707521551908091m`、右 `.0017062238887944753m`。每侧中心、四轴向和四45°方向共9点，坐标以原binary64中心加偏移生成，没有十进制取整。它是条件工程容差面板，不是概率置信界或连续圆域证明。

起始q6取各原report.initial_qpos[:6]；包括原夹爪 `.4999999999754389rad`。新可选 `initial_q6` 只补离线诊断：原六值进入reference／frame／静态扫掠，五轴作为每点原IK首seed；成功后仍按approach→down→lift续接，首IK失败后同点后续not_attempted。默认None保留原reference求解及失败后续诊断。原solver、8 seeds、残差、控制器、评分器均不改。

两份原planning XML逐字相同：固定红蓝盘、无自由目标六hinge模型。左60mm/.5，右54mm/.35；原1mm、285对、.005rad臂间距、.002rad或更密jaw间距及完整244／246保持；未启额外几何轴。规划模型不含手指与自由物体接触，不能由本表推断已抓住。

## 实测结果

Kaggle `muqiaoqiao/so101-x-input-sensitivity-20261028/1`已COMPLETE，接收源码回读逐字一致。MuJoCo3.15.0，左右各独立组件进程，无mj_step。独立原件审计通过，无unknown，18点原IK、端点、下降提升腿与完整抓取扫掠全通过。共9240个实际全扫采样（左3546、右5694），每个采样的原285对检查保持。直达接近弦仍只作诊断，不替代原任务OMPL。

| 侧 | 离散输入 | 非reference抓取扫掠最小证书 mm | 所在段 | 闭爪点数 |
| --- | --- | ---: | --- | ---: |
| left | `left_center` | 1.047919209 | descent | 244 |
| left | `left_x_plus_r` | 1.024916639 | descent | 244 |
| left | `left_y_plus_r` | 1.018380264 | descent | 244 |
| left | `left_x_minus_r` | 1.033890783 | ascent | 244 |
| left | `left_y_minus_r` | 1.010530420 | descent | 244 |
| left | `left_xy_plus_plus_45` | 1.000433213 | descent | 244 |
| left | `left_xy_minus_plus_135` | 1.000137072 | descent | 244 |
| left | `left_xy_minus_minus_225` | 1.005923591 | descent | 244 |
| left | `left_xy_plus_minus_315` | 1.007829720 | descent | 244 |
| right | `right_center` | 1.028042614 | closure | 246 |
| right | `right_x_plus_r` | 1.000353907 | ascent | 246 |
| right | `right_y_plus_r` | 1.030489824 | descent | 246 |
| right | `right_x_minus_r` | 1.083765208 | closure | 246 |
| right | `right_y_minus_r` | 1.022905079 | closure | 246 |
| right | `right_xy_plus_plus_45` | 1.032895066 | closure | 246 |
| right | `right_xy_minus_plus_135` | 1.041437316 | closure | 246 |
| right | `right_xy_minus_minus_225` | 1.040539945 | closure | 246 |
| right | `right_xy_plus_minus_315` | 1.017320321 | closure | 246 |

证书值是保守分离下界，不是实测欧氏最近距离，也不能把它减去1mm当作可用输入误差半径。最小下界靠近门槛，可能受原认证计算的停止精度影响；“最小证书”不等于物理最危险方向。

后续[R139固定姿态复查](m1a-x-clearance-readback-results.md)已实证早停影响：原两选中姿态的全285对可认证下端为1.937078476／9.371626854mm，且瓶颈对改变。下文保留原预声明选点规则与原值，不将事后更强证书写成当时选点依据。

按预声明规则，只在已通过的非中心点中，排除恒定reference与直达诊断，按preclose／descent／closure／ascent原最小证书排序，精确并列取manifest先后：左选 `(-1.2074000683763885,+1.2074000683763885)mm`，证书1.000137072mm，红盘 `pick_wall_y_1` 对前臂 `collision_lower_arm_1`，descent样点73；右选 `(+1.7062238887944753,0)mm`，证书1.000353907mm，同盘壁对 `collision_gripper_1`，ascent样点32。其余方向仍全部保留。

左右组件wall6.549573／4.715619s，CPU4.475496／5.122732s；这是组件开销，不是速度A/B、任务节拍或完整50Hz。

## 复跑与证据

新增CLI接受 `--initial-q6 Q0 Q1 Q2 Q3 Q4 JAW`；原两种scene入口都转发。使用原planning XML，逐角色读取归档manifest.points，设置原hover／jaw并加 `--full-grasp-sweep`。不传初态仍沿用旧行为。完整可复跑Kaggle材料位于 `~/.cache/ros2-factory/codebuddy-so101-20261021/round136-x-input-sensitivity/` 的input-manifest.json、build_kernel.py、kernel/及原件reader。

原件：`experiments/colab-twin/output/x-input-sensitivity-20261028/kaggle-v1/so101-evidence.tgz`；独立与根点表在同output目录。原输入及两份XML均逐字核对；原q6含jaw精确保留。根原模块25项检查通过（本地MuJoCo3.3.7仅作代码回归，不混入云几何成绩）。旧venv不存在／系统python无mujoco的入口失败保留，未新装环境。

## 接续

R137准备把上述常量偏差加在本轮每次valid RGB估计上，invalid原样，冻结后不刷新；物体和盘位不动，原判据／90sim120wall不动。两个方向加左零偏差回归，经原evaluate_station串行真实物理验收。实际raw+offset须另核与本轮静态点之差；pixel overlay仍指raw位置，uncertainty仍是raw工程量，不冒称偏差后的真实误差界。现已完成[R137三例原物理3/3](m1a-x-input-bias-results.md)；第二放置工位同偏差也已完成[R138原物理3/3](m1a-x-input-bias-results.md#r138第二放置工位)。

普通±10mm／默认不改，连续域、完整50Hz、20＋20与M1a整体仍未通过。Knowledge=already_covered，Wiki《ROS2 与 FishBot》§20；本轮事实留本计划。

补充只读IK余量：54个原端点q5用原XML关节范围复算，与各原joint_min_margin_rad逐值相同；最小均为wrist_flex，左8.292634°、右1.949415°。这是本18点端点余量，不是动态跟踪误差界。原始root-ik-margin-readback.json保留。独立报告已压缩为independent-readback.json.gz，精确恢复与本轮空间收尾见[R137](m1a-x-input-bias-results.md)。
