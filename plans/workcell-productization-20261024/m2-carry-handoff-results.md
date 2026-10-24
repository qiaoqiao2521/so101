# M2：限时等待与Carry接续

## 本轮范围

沿用原Station、任务ID、控制器hold、IK/OMPL、worker和评分。用户可在到达原hold姿态后，限时继续Carry或取消；默认不声明仍自动执行。不增加行为树引擎、调度平台、对象真值控制或物理重置。

CarryGate只读q6、当前时钟和同attempt输入文件。False保留原hold目标，全部原守卫／物理／时钟继续；原阶段超时和90sim／120wall保持。waiting不是Grasp成功；Grasp仍取独立原monitor证据，后续失败和取消不改判。

## 已实现与局部验证

- 原SO101四文件在途实现已审阅；补回调告警隔离，防止PYTHONWARNINGS=error使展示失败变成控制故障。
- 前端／API原八文件补取消竞态：已请求取消拒绝resume；迟到resume响应不覆盖较新取消或失败终态。原server随后恢复，实际接口读回见下文，局部测试与真实API检查分列。
- 根202项相关Python检查通过（含取消、超时、扫掠与transport/separation/return worker）。前端5项runtime、56项Jest、最终生产构建与13项无运动浏览器检查通过；真实控制POST=0、pageerror=0，4次测试POST由HTTP fixture接收。waiting＋未抓住原件仍显示未确认；390px无溢出。
- 网页导出的 `carry-recipe.json` 原文保存为 `experiments/colab-twin/scenarios/station-carry-m2.json`，普通中心工位，不移动盘或放宽±10mm。

## 原物理面板

固定已推送源码，在Kaggle沿原runner串行三例：

1. `resume_after_wait`：从原status观察waiting，1仿真秒后写本attempt的继续标记，验原完整抓放／释放／脱离／回位。
2. `cancel_while_waiting`：同样观察后写原取消标记，保留原Cancelled物理失败和清理。
3. `original_timeout_without_resume`：不写继续标记，验证原encoder_stage_timeout，不能改为成功或无限等待。

操作fixture只根据gate状态及仿真时钟决定何时发输入，不依赖对象真值、不改控制器／评分器。等待事件前是否已Grasp成功由根独立回放原monitor验证；不是把物理裁判喂给控制策略。保持原1mm、244点、限位、全部回退及90sim／120wall。每例单独UUID、过程wall/CPU、完整周期、录像和清理回执。

### 原件已回收：一例完整通过、两例原失败保留

固定d93d60f，Kaggle `muqiaoqiao/so101-carry-handoff-20261024/1` 已COMPLETE。独立reader逐例回放原monitor与释放审计；根另直接读原report和status gate，确认原终态及同UUID的连续时钟。

| case / UUID前缀 | 原物理裁决 | sim / episode wall s | process wall / CPU s |
| --- | --- | --- | --- |
| resume / c222f385 | pass，完整抓放／释放／脱离／回位 | 77.58 / 52.566 | 53.933 / 63.569 |
| cancel / 1628fa1c | fail，任务cancelled | 32.30 / 22.526 | 23.578 / 27.996 |
| no resume / f6d0af2d | fail，原encoder_stage_timeout | 38.60 / 25.718 | 26.743 / 31.840 |

三例均28.48s由原monitor确认Grasp，31.22s进入waiting；resume于32.22s释放同attempt门，cancel于32.30s结束，no-resume等待7.38s后原超时。两失败未启动transport，不改判为抓放通过。三例planned/measured闭爪均244点；成功例485实帧，完整周期104拍>20ms，完整50Hz仍未通过。

原件及逐项读回在 `output/carry-handoff-20261024/kaggle-v1/independent-readback.json`。这验证原物理输入标记链，尚不证明网页实际POST或新API已上线；源码中的云路径是原件来源，非本机执行路径。

## 剩余

5186已沿原workbench-preview.cjs恢复，保持原SO101_ROOT与隔离Python。实际GET显示SO101 ready=true、resume_carry=true，Drone ready=true、resume_carry=false；13个SO101与25个Drone历史任务ID全部保留。已结束SO101任务resume返回409，Drone返回405，均未写继续标记或创建任务。首页、原主包和包含Carry入口的chunk实际被服务，11项读回通过。

原runtime五项检查本轮重跑通过；Jest56项、原最终构建和13项浏览器检查对应源码未变，沿用已验结果，不声称本轮重跑浏览器。实际API证据在FishBot原工作树`apps/fishbot-control-station/workbench-review-tests/output/carry-handoff/live-api-readback.json`。

工作台9个有效文件（含原进度）已在`codex/workbench-code-rebuild-20261018`提交并推送`5a30c26f985efc614dcaf2e6f4f9efcbdfffa449`；远端独立回读相同。Drone在途修改保持，不混入SO101交付。尚缺真实HTTP活动任务进入waiting后继续／取消与原物理的整条验证；本次历史终态拒绝不能代替它。完整六技能RUNNING/halt、同世界安全恢复、连续卸货及20＋20仍按原主计划推进。Carry不是完整M2的替代验收。
