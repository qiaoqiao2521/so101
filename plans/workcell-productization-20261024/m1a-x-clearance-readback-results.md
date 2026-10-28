# X方向：原1mm早停见证与可认证净距要求

日期：2026-10-28。R139，执行源码 `de094ee4d06b952649e7d4de869d9bcfe7b136a4`。承接[R136实际RGB输入](m1a-x-input-sensitivity-results.md)和[R137／R138原物理](m1a-x-input-bias-results.md)。本轮没有新IK、物理步进或抓放回合。

## 问题与原实现

X方向已有两种不同拒绝。右侧原60mm高位在实际RGB输入下出现腕部限位／IK残差失败，54mm高位可以求解；大开度仍有盘壁证书拒绝，显式.35rad预收口完成原物理。左侧部分姿态需要原完整几何补方向；旧失败仍保留。原IK约束位置、工具竖直轴及腕旋偏好，并未固定完整世界yaw，不能据5自由度直接归因于yaw封印。

R136保存的最小证书约1.000137／1.000354mm，不是最近距离。`support_kernel.cpp::pair_result`按原19方向查找，首个达到要求的证据即返回；`support_native.py::_summarize`再取285对返回见证的最小值。更强方向可能尚未访问，因此不能把见证减去1mm当作输入误差半径，也不能据最小见证给实际危险方向排序。

## 实际复算

Kaggle实际接纳 `muqiaoqiao/so101-x-saved-pose-clearance-20261028/1`，已COMPLETE。提交title解析为这个slug；原请求slug及警告保留，未重新提交。根读回云接收源码与提交源码逐字相同。

使用原MuJoCo3.15.0、R136原planning XML和保存的q6。每个原点只取其已保存的非reference最小证书姿态，共18个；没有重新运行18点IK或9240个扫掠采样。关闭方向提示及补方向，保留原19方向、285对和完整网格／box定义。

每姿态先逐值复现原1mm输出。固定FK所得几何，分别对全部285对及原见证那一对提高离线查询要求，以原native门二分；最后反序重查两端，并在同进程还原1mm比较原输出。未认证上端只表示缺少该要求下的原证书，不等于碰撞。二分停止宽度≤1e-9m只是数值分辨率，不是模型、标定或真实机器精度。

| 原已选姿态 | 原早停见证 mm | 全285对可认证要求区间 mm | 原见证对可认证要求区间 mm | 全场景上端首先缺证的对 |
| --- | ---: | --- | --- | --- |
| 左135°偏差，descent index73 | 1.000137072 | [1.937078476, 1.937079430] | [143.270339012, 143.270339966] | `pick_wall_x_-1`／`collision_gripper_1` |
| 右+X偏差，ascent index32 | 1.000353907 | [9.371626854, 9.371627808] | [37.531574249, 37.531575203] | `collision_wrist_1`／`collision_moving_jaw_so101_v1_0` |

左原见证对是`pick_wall_y_1`／`collision_lower_arm_1`，右原见证对是同盘壁／`collision_gripper_1`。提高查询要求后瓶颈对改变，所以原见证不应称为最近盘壁对。其他16个已保存姿态同样完成复算；18个姿态的全285对可认证下端范围1.937078476–9.517699242mm。完整点表留root-readback.json，不由此推断全部扫掠姿态或整个连续X区间。

实际1074次原native查询。组件内部wall3.706163s／CPU1.661547s；完整组件子进程观察wall4.023759s／CPU4.827714s另含导入及记账，bootstrap／preflight另列，不能相加或记为任务提速。原90sim／120wall、线上1mm和所有执行参数未变。

## 独立核验与限制

根46项读回及独立reader均通过，failures=[]、unknown=[]。原18行集合、q6／阶段／采样index／原证书、XML及冻结组件逐字或逐值对应；每次285或1对覆盖、valid／reason／计数、查询区间及反序端点均核实。人工损坏覆盖数被拒，未知区间保持unknown。原1mm恢复由已保存组件源码中的实际相等比较和true回执支持；恢复后的原dict未单独保存，不冒称独立raw重算。

本结果证明原约1.0001mm是早停见证，不能单凭该数认定贴壁。它仍是**固定保存姿态、原方向族的可认证要求区间**，不是精确欧氏距离、真实动态余量、定位误差包络、连续扫掠证明或新的抓放成功。原6次偏差抓放成绩仍来自R137／R138；完整50Hz、连续域、20＋20与恢复均未新增通过，默认保持。

## 原件与复跑

原件：`experiments/colab-twin/output/x-clearance-20261028/kaggle-v1/so101-evidence.tgz`，包含原manifest、XML、组件、完整查询history、runtime及进程记录。根root-readback.json和independent-readback.json保留。私有源位于 `~/.cache/ros2-factory/codebuddy-so101-20261021/round139-x-clearance/`，保留builder、冻结输入、接收源码、dispatch、纯函数反例和独立reader。

```bash
python3 ~/.cache/ros2-factory/codebuddy-so101-20261021/round139-x-clearance/independent_reader.py \
  experiments/colab-twin/output/x-clearance-20261028/kaggle-v1/so101-evidence.tgz
```

重新运行组件使用该目录SOURCE.md的原Kaggle CLI；查状态／取输出必须使用dispatch中实际接纳slug，不能重发来修名字。无新平台、内容执行锁或控制器改动。

云／下载均终态，无本地模型／物理进程。CLI下载的展开重复件逐字核对TGZ后删除，独有kernel log精确gzip保留；本轮证据目录分配761856→69632B，写cleanup记录前释放692224B。输入、源码及原TGZ保留；恢复命令见cleanup.json。Knowledge=already_covered，沿用Wiki《ROS2 与 FishBot》§20及既有保守下界解释。

后续[R140实际取料记录](m1a-x-execution-clearance-results.md)已复算3381姿态，取得不同的阶段瓶颈。保存静态姿态不能替代完整轨迹，更不能替代未保存的2ms状态。Carry网页准备暂停保留，用户当前优先X方向；不据这轮结果重写IK或放宽原阈值。
