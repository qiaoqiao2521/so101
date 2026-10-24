# M1a：X 方向诊断与工位适配

## 原布局拒绝的原因

- X+20mm（世界 XY=0.26/−0.13m）：原 60mm 高位的 8 个 IK 初值均失败。最佳位置误差 0.552042mm、竖直轴误差 0.621339°，腕俯仰到达 94.999939° 上限。移除 roll 偏好也不能解决。原零 roll／竖直工具分支的独立平面解需要 97.024133°，超限 2.024137°；该证明不覆盖任意工具姿态。
- 将高位改为 54mm 后，原 IK 能解，腕部上限余量 1.004261°。但原盘位下的下降／闭爪仍不能通过碰撞证书，因此未将仅改高度的候选送入原物理。
- X−20mm（0.22/−0.13m）：原下探 IK 能解。`pick_wall_x_-1 / collision_gripper_1` 的保守下界 0.880489mm，不够原 1mm；它不是实测最短净距。独立投影全部 14354 个编译网格顶点与墙体 8 角，单位轴 `(0.938970002274048, 0, 0.343999033181018)` 给出 16.773623mm 分离下界。说明该姿态存在更强证书；没有据此改写原检查器。
- `mj_geomDistance` 的负距离与上述投影不一致，原因未知；它没有参与准入。没有删除盘壁、缩小几何或放松阈值。

诊断来源：根 GPT 与内部 GPT 独立复核；本次工具列表未加载 agent-link，因此未伪称 AGY／CodeBuddy 参与。私有脚本位于 `/home/muqiao/.cache/ros2-factory/codebuddy-so101-20261021/round102-workspace-x-20261024/` 的 `ik/`、`wall/`、`root/`。原始记录仅为 FK／几何，不是物理回合。

## 本轮薄适配

- `build_workcell/build_contact_scene` 可显式传 `pick_xy`。只平移红盘的 floor、四壁和标牌；实体与规划模型同源。默认盘位、尺寸、高度、摩擦、目标默认位置不变，红盘必须完整在原台面内。
- `VisualGraspController` 新增 `pickup_hover_z_m=.06`。只用于原接近／抬升目标；开发取值域 .054–.06m 仍逐次经过原 IK、路径和全部碰撞认证，域本身不是通过承诺。下探仍 .019m。
- 开发入口读取 `pick_xy_m` 和 `pickup_hover_z_m`，原中心不传新参数。布局是声明的静态场景；目标初态只交给原 reset fixture，控制器仍接收 RGB 估计，不将物体真值接入策略。
- [workspace-x-m1a.json](../../experiments/colab-twin/scenarios/workspace-x-m1a.json) 只包含两个待验新布局与原中心对照。网页准入、默认 route、原裁判、1mm、planned/measured244、90sim/120wall 和回退不变。

| 开发例 | 目标 XY m | 红盘 XY m | 取料高位 m |
| --- | --- | --- | --- |
| center_primary | .24/−.13 | 原 .24/−.13 | 原 .06 |
| outside_x_plus20_layout | .26/−.13 | .26/−.13（+20mm） | .054 |
| outside_x_minus20_layout_secondary | .22/−.13 | .235/−.13（−5mm） | 原 .06 |
| center_secondary | .24/−.13 | 原 .24/−.13 | 原 .06 |

主放置工位 .24/.14m，第二放置工位 .20/.20m。托盘平移是新布局，不是原固定红盘工作区扩展；本轮也不是节拍性能 A/B。

## 离线验收

根独立以最终 builder 重新编译两组布局：原参考起姿、下降、闭爪 244 点、提升全部通过原保守检查。右侧下降最薄下界 1.004126mm，闭爪 1.037192mm；左侧下降 1.005412mm，闭爪 1.057120mm。下界很薄，不等于动态跟踪余量充足。

84 项相关检查通过，包含原控制器／Station／评分与新增参数／场景透传检查；adapter mock 不计物理成功。根投影复算与内部核查一致。`root/profile_screen.json` 为本机筛选证据，不准入产品。

## 原完整物理：4/4 pass

固定源码 `e7f921c83bc975917c872079aa592b03575b26ca`，Kaggle `muqiaoqiao/so101-workspace-x-m1a-20261024/1` 原生 COMPLETE。复用原 bootstrap／串行 runner，MuJoCo 3.15.0、NumPy 2.4.6、Tesla T4 EGL。每例90sim/120wall；没有在组内修改源码或提交。四例原 verdict/report.passed 均为 pass/true。

| case / run UUID | sim s | process wall s | process CPU s | 接近 OMPL规划 / 含后处理 elapsed s |
| --- | ---: | ---: | ---: | ---: |
| center_primary / f651ece0-fdda-4a09-9f39-e348aed99309 | 76.68 | 48.086 | 57.280 | .118442 / .277841 |
| outside_x_plus20_layout / e49d9f7a-6eb0-41e9-b5a4-203802d8c36f | 77.98 | 48.189 | 57.702 | .116176 / .251529 |
| outside_x_minus20_layout_secondary / 5e19019a-cae8-464c-990b-739f7d5edd60 | 78.24 | 49.816 | 59.837 | .154401 / .322657 |
| center_secondary / d580d920-ddfc-4667-a4f8-c12f6bf557d0 | 79.92 | 50.223 | 60.258 | .151649 / .322491 |

任务 episode wall 分别47.004/47.094/48.718/49.117s，进程 wall还含初始化／收尾，CPU含子线程，两者不混用。transport worker wall分别2.066/2.304/2.559/2.769s，separation worker1.020/1.122/1.460/1.397s；它们与主回合重叠，不能相加为总规划耗时。不同取料／盘位不是性能A/B，不报告提速。

四例均核实自由物体（weld=0/mocap=0）、真实抬升约40.9–41.0mm，双指持物32.88/35.00/33.34/35.68s，蓝盘静稳约7.50–7.54s。原释放、脱离、回位通过；障碍接触0、安全停机false，原planned/measured闭爪各244/244 valid，所有轨迹arm_valid/finite为真。释放后峰值接触力0，XY漂移.211/.209/.172/.172mm，原2mm/0.02N门槛未动。双worker全部consumed/joined/owned_ack，无unknown launch或未确认清理。

实际保存的物理／规划MJCF红盘位置一致，reset目标XY为.24/.26/.22/.24。RGB初始估计分别约(.240349,−.130508)、(.259651,−.130508)、(.220063,−.130508)、(.240349,−.130508)m，控制器没有直接接收reset真值。X方向相机前置3正＋4渲染负例7/7，最大误差.616511mm。固定尺寸／高度／轴对齐仍是原定位先验。

根对保存的执行接近路径末端做独立FK：高位Z为.060/.054/.060/.060m；这是**计划关节端点的FK**，不是新增实际笛卡尔传感器字段。保存q6的全回合腕俯仰最大值93.8586/93.9705/94.1612/94.1612°，原上限余量1.1414/1.0295/.8388/.8388°，未靠裁剪或放宽95°实现。后两例余量包含第二放置工位与回位，不能归因于取料段。

| case | 完整周期数 | P50 / P95 / P99 ms | max ms | >20ms | 视频实际帧 |
| --- | ---: | ---: | ---: | ---: | ---: |
| center_primary | 3834 | 9.270 / 15.101 / 26.208 | 42.124 | 58 | 480 |
| outside_x_plus20_layout | 3899 | 9.312 / 14.636 / 27.761 | 46.440 | 70 | 488 |
| outside_x_minus20_layout_secondary | 3912 | 9.503 / 15.858 / 27.704 | 140.476 | 81 | 489 |
| center_secondary | 3996 | 9.413 / 16.354 / 25.086 | 135.697 | 72 | 500 |

完整50Hz仍未通过；本轮不是20+20或扰动鲁棒性验收。原报告与ffprobe帧数一致，四视频完整；根查看右侧终态图确认绿块留在蓝盘，截图不替代原物理判定。

## 证据与结论

原件目录：`experiments/colab-twin/output/workspace-x-20261024/kaggle-v1/unpacked/so101-evidence/`（被Git忽略）。主批次 `workspace-pilot/ec30c508-f14b-4c22-bc47-c4c6308a1c79/`；每例UUID下保留原report/trajectory/planning/release/jaw-sweeps/录像。根回读与独立reader的6项缺证／失败反例检查通过，真实 `independent-readback.json` warnings=0；`planned-height-readback.json`与`x-runtime-margins.json`补记根只读核验。没有缺失、重复或额外case。

**保留为可复跑的开发布局能力。** 两个X点原物理成功，但没有证明原固定红盘下的X±20mm可用；原两类失败仍有效。原碰撞检查器未增强，也未发布连续区域或改网页准入。下一步以这个开发profile为明确产品输入候选，补布局／能力边界后再决定公开入口；不因4/4单例把薄余量当扰动保证。M1a整体仍in_progress，M1b／恢复／20+20／卸货未新增通过。

复跑入口（每例独立目录，不覆盖原证据）：

```bash
cd experiments/colab-twin
python run_workspace_case.py --profile scenarios/workspace-x-m1a.json \
  --case outside_x_plus20_layout --output-dir output/workspace-x-dev
```
