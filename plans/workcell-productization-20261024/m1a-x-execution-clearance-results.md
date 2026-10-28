# X方向：实际取料记录的可认证净距要求

日期：2026-10-28。R140，执行源码 `44577f185d099d246f179b1a8a7e731449895fe6`。沿用[R139固定姿态复查](m1a-x-clearance-readback-results.md)的方法，转为核算[R137两个实际抓放回合](m1a-x-input-bias-results.md)保存的实测q6。没有重跑抓放、IK或OMPL，没有修改控制器／评分器／线上1mm。

## 固定覆盖范围与来源

原回合左 `1035c5d7-bf48-42f9-9d35-bd838dc5116e`、右 `738b92ff-9543-4d64-a744-e33edefb9fbf`，原执行源码6cf337b。每例包含report初态q6、全部取料阶段连续前缀及第一条transport边界。不按guard或距离筛选记录。

| 记录 | 左 | 右 |
| --- | ---: | ---: |
| report初态 | 1 | 1 |
| approach | 861 | 802 |
| preclose | 0 | 61 |
| descend | 143 | 138 |
| close | 331 | 331 |
| lift | 143 | 138 |
| hold | 209 | 220 |
| 首transport边界 | 1 | 1 |
| 总计 | 1689 | 1692 |

原trajectory覆盖index0–1687／0–1690，最后elapsed33.76／33.82s。q6是在下发command、推进10×2ms、mj_forward／diagnostics后保存的实际状态；stage是该拍使用的指令阶段。初态另列，绝对time由首条time−elapsed派生；初态guard原未独立保存，保持null。全轨迹20ms间隔无缺口；本声明集逐条原guard通过。输入仅携带实测q6、时间、stage、index及原guard，没有目标物体真值或command。

## 原组件实测

Kaggle `muqiaoqiao/so101-x-execution-clearance-20261028/1`已COMPLETE，根读回接收源码与提交源码逐字一致。原MuJoCo3.15.0，左右原planning XML逐字相同；原六hinge模型、19方向、285对，关闭提示和补方向。盘壁子集从原285对中取含`pick_wall_`的68对，名单及排序由独立reader按原XML／配对政策复原核实。

每case先检查全部原1mm样本。随后维护已访问姿态共同可认证的要求下端；遇新姿态缺证则对该姿态二分降低下端。最后两类pair集合均逐条复查全部姿态在最终下端通过，并保留一个上端缺证的见证姿态。原门的阈值单调性支持此有限集合区间；没有把采样观察当作全区间数学证明。最终见证反序复查，且保存原1mm before／restored完整dict并逐值相等。恢复核验只针对四个最终见证，非3381帧逐条after复查。

| 样本集合 | 可认证要求区间 mm（显示约值） | 原trajectory index／elapsed／stage | 上端首先缺证的对 |
| --- | --- | --- | --- |
| 左，全285对 | [1.728968580, 1.728969282] | 1336／26.74s／lift | `pick_wall_x_-1`／`collision_gripper_1` |
| 左，盘壁68对 | [1.728968657, 1.728969359] | 同上 | 同上 |
| 右，全285对 | [3.058225756, 3.058226434] | 280／5.62s／approach | `approach_obstacle`／`collision_gripper_1` |
| 右，盘壁68对 | [5.282781515, 5.282782083] | 928／18.58s／descend | `pick_wall_x_1`／`collision_moving_jaw_so101_v1_0` |

原binary64数值和完整history留原件。左右表中的微小下端差异来自分别二分的网格，两个区间重叠，不是两种物理距离。≤1e-9m是二分区间宽度，不能当作几何或传感器精度。上端缺证也不等于碰撞。

原1mm基线全部3381姿态通过；两类pair集合最终下端各覆盖全部3381姿态。共54207次原native几何查询（含基线及四次见证恢复）。组件进程wall25.920565／CPU26.704471s；内部计时25.331632／23.443025另列，bootstrap／preflight不计其中，不与原任务wall相减当作算法收益。

### 五轴关节限位

用原XML范围及声明集实际q6复算，最小均为wrist_flex。左3.311017593°在首条approach（index0／.02s）；右2.0468929999°在首transport边界（index1690／33.82s）。右侧仅取料前缀单读约2.046932°，包含已声明边界后应使用新值。两者不是全回合最小余量；R138运输段约.838772°结论仍保留。

## 结论及限制

实际取料记录比R139两个选中静态姿态更窄，不能用静态1.937／9.372mm代表全程。左侧应关注抬升开始附近的夹爪／盘壁；右侧全场景瓶颈先出现在接近障碍，盘壁限制另在下降段。左见证实测jaw约.123rad，不能以闭合目标.015rad替换；本轮没有单变量归因哪一轴造成差异。

本轮核的是**保存状态上，机器人对静态工位及原自碰撞对的原方向证书**。规划模型没有自由物块，不证明被夹物块净距；20ms记录不补成未保存的2ms状态或连续轨迹。不是新的物理成功、连续X域、定位误差半径、20＋20、恢复或完整50Hz通过。原裁判、阈值、244／246扫掠和默认保持。

根逐值回读与独立reader均无失败／unknown。独立核原3381记录、285／68名单、所有final覆盖、query语义／计数／索引、区间更新及四个raw恢复，另以原XML纯数据复算关节余量。丢final行及负pair索引被拒，未知case保留unknown。测试统计不代替本轮实际几何结果。

## 原件、复跑与收尾

原件：`experiments/colab-twin/output/x-execution-clearance-20261028/kaggle-v1/so101-evidence.tgz`，包含约30.7MB未压缩报告的完整history，以约1.5MB TGZ保留，未展开。root-readback.json、紧凑independent-readback.json及cleanup.json同目录。私有源 `~/.cache/ros2-factory/codebuddy-so101-20261021/round140-x-execution-clearance/` 保留冻结component／manifest／XML、原运行器builder、接收源码、dispatch、输入读回及纯函数反例。

```bash
python3 ~/.cache/ros2-factory/codebuddy-so101-20261021/round140-x-execution-clearance/independent_reader.py \
  experiments/colab-twin/output/x-execution-clearance-20261028/kaggle-v1/so101-evidence.tgz
```

云与下载均终态，无本地模型或物理进程。下载仅取TGZ，未制造展开报告／临时帧；独有kernel log精确gzip。两个解码records副本与manifest内gzip逐字相同后删除，临时函数摘录删除，冻结输入和原R137证据保留。输出／私有文件分配1556480＋2154496→1556480＋1093632B，写cleanup记录前释放1060864B。恢复records及TGZ的命令见cleanup.json；清理后独立reader重新通过。Knowledge=already_covered，项目数值只写本计划。

Next：回到M1a原Station输入合同和具体拒绝路径，核已验X配置怎样服务新的任务输入，再决定最小适配；不据这些离散记录直接开放连续域，也不继续用增加静态姿态代替用户可复用能力。
