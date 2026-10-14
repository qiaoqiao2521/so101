# 看 GraspGen-X 怎样挑抓取姿势

这是官方预训练模型的本地体验入口。给模型一个虚拟方块和 SO101 仿真指尖区域，它生成抓取候选；再查看实际 SO101 网格，以及五轴机械臂的静态姿态匹配误差。不训练，不操作实体，不执行物理抓放。

**当前夹爪输入是指尖区域近似，尚未验证完整夹爪扫掠体。** 模型分数不等于抓取成功率；漂亮候选也不代表 SO101 能执行。输入为完整物体表面几何上界，不是相机观测或真实定位。

## 运行

在 SO101 仓库根目录运行。需要 Linux、NVIDIA GPU、`uv` 和官方 `hf` CLI。首次准备会下载约1.69GB的生成器/评分器，以及独立环境所需的 CUDA 依赖；使用仓库外缓存，不改已有仿真或 SmolVLA 环境。

```bash
bash experiments/graspgenx-demo/setup.sh
bash experiments/graspgenx-demo/run.sh 0 16
```

第一个参数是随机种子，第二个参数是候选数。每次在 `output/` 创建独立目录，保留错误和原始结果，不覆盖旧回合。模型缓存路径可用 `SO101_GRASPGENX_CACHE` 指定。

结果包括：

- `preview.png`：模型最高分姿势与本轮静态匹配误差最小的姿势，使用原 SO101 网格。
- `report.json`：权重/配置哈希、模型版本、候选数、推理时间和 CUDA 分配/保留显存。
- `candidates.npz`：未经运动接受的候选与评分。
- `descriptor.json`：夹爪区域近似的来源、参数和未验证边界。
- `pose-inspection.json`：平移/旋转误差；只是有限次数局部求解，不证明全局不可达。

首次包安装使用官方基础依赖与轻量 `serve` extra。后者是官方 sweep-volume 构造器导入类型所需，不启动服务。没有安装 TensorRT 加速或官方端到端 cuRobo/Newton 栈。

## 2026-10-14 首次实际结果

本机 RTX3050 Laptop 4GB，Python3.11、Torch2.6.0+cu124、MuJoCo3.15.0，原权重，无精度改动或训练。第一份成功产物为 `output/20261014-153626-2150086/`：

| 项目 | 实测 |
| --- | --- |
| diffusion 候选 | 16个；官方生成器与评分器，无 OBB 混合 |
| 推理时间 | 1.234s；不含安装、下载、加载、姿态检查及渲染 |
| CUDA峰值 allocated/reserved | 607.16 / 650.00 MiB；不代表整卡总占用 |
| 模型评分最高候选0 | 本轮拟合误差21.71mm、29.84° |
| 本轮加权误差最小候选15 | 11.41mm、16.49°；不是安全或任务验收 |

目前没有完整姿态准入、路径/碰撞通过或物理抓取结果。不能据上述局部求解声称所有候选全局不可达，也不能把低模型评分当作必然失败。下一步应先核准夹爪完整描述和坐标契约，再冻结完整姿态门并接入原碰撞/物理验收；不默认开始训练。

最终入口复验保存在 `output/20261014-155217-2175777/`：16候选、推理0.6994s、同显存峰值。候选数组与首次成功结果逐位一致，静态检查与完整网格候选图均完成。这是同一固定输入的复跑，不是泛化或抓放成功率评测。

上游提交和模型/配置文件已固定；全部传递依赖尚未锁定。后续环境变化需重新验证，不能将本机一次准备成功称作跨平台即用。

首次失败分别保存在 `output/20261014-153139-2145392/` 和 `output/20261014-153437-2148392/`：前者缺官方 `serve` 的 msgpack 依赖，后者为 Trimesh 数组子类未被官方精确类型检查识别。补齐依赖、转成连续float32标准数组后运行成功，未修改上游代码或权重。

## 四组静态对照

无需再次安装或训练。在仓库根运行：

```bash
bash experiments/graspgenx-demo/compare.sh 0 16 cli
```

第三个参数 `cli` 使用官方演示脚本的OBB默认值：36个yaw、Z偏移-2/0cm、`dense-topandside`。改为 `api` 则使用公共planner API默认值：36个yaw、Z偏移-8/-6/-4/-2/-1/0cm、`sparse`。二者不应混称同一默认配置；当前分数阈值-1、扩散每次16个和下游最多16个是本实验设置，不是整套官方CLI默认值。

每轮只运行一次官方GraspMoE。diffusion与OBB组分别取这一轮的分支子集，混合组取并集，再按同一评分器稳定排序选前16。保留 `pool.npz` 的全部候选及来源；这是共享候选池消融，四组不是独立重复，生成预算也不同。官方扩散分支默认至少40候选、最多6次尝试；本次16个/次实际运行3次，共48个，不能与旧一次16个推理直接作等预算比较。固定组只有原IK生成的一个场景先验姿态，也使用相同评分器，不证明感知泛化。

产物 `REPORT.md`、`comparison.json` 记录数量、来源、配对姿态误差和时间/显存；四个子目录各有候选图和静态拟合报告。图和模型分数均不证明碰撞、路径、接触或释放成功。

若要检查被评分裁掉的姿态，在运行结果目录上执行：

```bash
~/.cache/so101-graspgenx/upstream/.venv/bin/python experiments/graspgenx-demo/audit_pool.py \
  --root . --output experiments/graspgenx-demo/output/<本轮目录> --seed 0
```

该命令不重新推理，逐个检查所有保存候选，生成 `all-candidates/audit.json`、姿态报告与候选图。已有目录拒绝覆盖；有限局部求解仍不是全局不可达证明，不存在运动接受或物理成功率。

### 本机对照事实

2026-10-14，seed0，同一3500点方块和指尖近似。API配置原始48扩散+216OBB，CLI配置48扩散+360OBB。各组按评分选16个后，API混合组包含静态误差接近零的OBB顶抓；CLI混合组前16个全是OBB，配对加权误差最小者仍为41.23mm/40.00°。两轮扩散组相同，配对最佳0.227mm/5.084°。这只说明本轮评分排序与五轴姿态拟合存在区别，不能宣称API普遍更好或模型失败。

CLI混合推理1.687s、CUDA峰值allocated587.95MiB/reserved642MiB；不含模型加载、静态求解和绘图。完整输入和近似夹爪限制继续适用。API产物 `output/comparison-20261014-165300-2254125/`；CLI产物 `output/comparison-20261014-165422-2256124/`，均由Git忽略。

CLI全408候选已完成独立静态审计。OBB候选92的配对误差约为 `1.94e-10mm / 4.82e-11°`，只表示数值拟合接近零；它在OBB分支模型分数排第289，未进入前16。最高分候选297则为75.55mm/64.16°。因此评分裁剪后的16个不能代表整个候选池，也不能据此宣布无可达姿态。候选92尚未接受运动或通过碰撞/接触；下一适配应先核准夹爪描述，再加入可达性筛选。

## 完整夹爪资产与原安全检查

对已经完成全候选审计的结果目录执行。将 `<本轮目录>` 替换为实际目录；导出和候选诊断拒绝覆盖已有目录，预览可重生成。

```bash
~/.cache/so101-graspgenx/upstream/.venv/bin/python experiments/graspgenx-demo/export_gripper.py \
  --root . --output experiments/graspgenx-demo/output/<本轮目录>
~/.cache/so101-graspgenx/upstream/.venv/bin/python experiments/graspgenx-demo/preview_gripper.py \
  --root . --output experiments/graspgenx-demo/output/<本轮目录>
~/.cache/so101-graspgenx/upstream/.venv/bin/python experiments/graspgenx-demo/check_candidates.py \
  --root . --output experiments/graspgenx-demo/output/<本轮目录>
```

导出直接来自当前MuJoCo模型，保留完整固定/活动指、马达网格、关节轴与变换，生成URDF、原网格、开爪视觉网格和逐零件凸包。独立yourdfpy FK对照9个jaw值×2个arm姿态，本轮18组最大顶点差3.824e-9m；1e-6m只是格式/数值一致性门，不是实物精度。生成资产全部被忽略，不改原模型。

`config.json` 使用官方资产格式，但内侧盒子仍来自旧指尖接触垫近似，`fingertip`仍是本地pinch参考。完整几何导出通过不等于官方向导已完成；模型描述和实体标定继续待验。SO101一指固定、一指转动，保守设 `symmetric=false`，不接受未经证明的180°等价姿态。官方模型条件是内侧区域盒子；它与整个夹爪实体的运动/碰撞几何分别审查。

原 `gripperframe` site不能冒充模型框架：本轮相对模型框架旋转180°，其原点与pinch参考相距14.50mm。`frame-audit.json`记录完整变换；不通过改坐标或目标姿态消除拟合误差。

同一CLI的408候选，复用原完整285碰撞对和1mm余量：62个数值复现（1e-6m/1e-5rad），37个开爪端点取得分离证书，两者交集31个；31个均通过0.5→0.015rad完整244点闭爪检查（jaw步长≤0.002rad）。诊断排序首位候选103；其开爪最小分离下界2.023mm。候选92未取得桌面余量证书，被保守拒绝；未取得证书不是实际碰撞证明。

结果位于 `collision-diagnostic/{REPORT.md,report.json}`；完整资产与图位于 `gripper-assets/so101_sim_tip_region/`。这些31个仍未接受运动：内侧盒子、物理姿态门、接近/下降路径、目标实体接触、载物/释放/回位均未覆盖。原规划rig移除了自由目标，目标不能由此声称碰撞安全。没有训练、额外推理、物理推进或实体操作。

## 官方来源与许可

- [官方源码](https://github.com/NVlabs/GraspGenX/tree/b9429097728cb1c430dd78b92edf17ba318aad03)：固定提交，Apache-2.0。
- [官方模型](https://huggingface.co/adithyamurali/GraspGenXModel/tree/7c834043c11a11417e31d6d5ea9355801e40a2c1)：生成器和评分器文件均按官方元数据 SHA-256 校验；权重采用 NVIDIA Open Model License，不能归为 Apache-2.0。
- [官方 sweep-volume 接口](https://github.com/NVlabs/GraspGenX/blob/b9429097728cb1c430dd78b92edf17ba318aad03/graspgenx/grasp_server.py#L123)：复用官方构造、配置加载与采样，不另实现生成模型。
- [官方GraspMoE](https://github.com/NVlabs/GraspGenX/blob/b9429097728cb1c430dd78b92edf17ba318aad03/graspgenx/samplers/graspmoe.py)：并集、分支来源、OBB生成及评分；固定组复用其评分函数。该私有函数与固定上游提交绑定，升级需复验。
- [官方演示参数](https://github.com/NVlabs/GraspGenX/blob/b9429097728cb1c430dd78b92edf17ba318aad03/scripts/demo_object_pc.py)：CLI默认值；公共API默认值另见 `graspgenx/samplers/planner.py`。
- [官方夹爪向导](https://github.com/NVlabs/GraspGenX/blob/b9429097728cb1c430dd78b92edf17ba318aad03/scripts/gripper_config_wizard.py)：两种内侧区域标注和资产格式。当前导出未伪称完成其GUI确认。
- [现有可行性计划](../../plans/graspgenx-feasibility-20261014/task_plan.md)：完整夹爪、姿态、碰撞和抓放的待验门槛。

源码、依赖、权重和运行产物分开管理。第三方源码/权重留在缓存并保留其许可；输出、日志及二进制文件由本目录 `.gitignore` 排除。
