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

## 当前验收

根独立以最终 builder 重新编译两组布局：原参考起姿、下降、闭爪 244 点、提升全部通过原保守检查。右侧下降最薄下界 1.004126mm，闭爪 1.037192mm；左侧下降 1.005412mm，闭爪 1.057120mm。下界很薄，不等于动态跟踪余量充足。

84 项相关检查通过，包含原控制器／Station／评分与新增参数／场景透传检查；adapter mock 不计物理成功。根投影复算与内部核查一致。`root/profile_screen.json` 为本机筛选证据，不准入产品。

原完整物理：**not_run**。待固定源码推送后，复用既有 Kaggle bootstrap 和串行 runner 执行四例。每例独立回读原 verdict、完整周期、规划／进程 wall/CPU、夹持、碰撞、释放、脱离、回位、244 和 worker 清理；未过结果原样保留。完整 50Hz 与 20+20 尚未新增通过。

复跑入口（每例独立目录，不覆盖原证据）：

```bash
cd experiments/colab-twin
python run_workspace_case.py --profile scenarios/workspace-x-m1a.json \
  --case outside_x_plus20_layout --output-dir output/workspace-x-dev
```
