# SO101 Colab 运动规划实验

2026-10-06 视觉定位主线已实现并实际核验：P0 20位置最大误差0.614mm，4类拒绝反例通过。P1基线因前臂遮挡停止；唯一修正改用机器人投影包络提前交接。修正版真实抬升40.9mm、持物30.68s并在蓝盘最终落稳，但撤回推块约40.4mm，90s时仍未完成回位，整回合失败。一次修正已用尽，P2和20+20均未运行。 [结果与视频](output/visual-grasp-pilot-20261006/REPORT.md)。新入口为 `experiments/colab-twin/run_visual_grasp.py`，使用含冻结 `protocol.json` 的独立输出目录；P1未通过时拒绝推进后续阶段。既有已运行目录不可覆盖。本轮已止损，不把命令入口视为继续运行授权。

以下保留早期阶段说明。

复用 SO101 原生模型，在 Colab CPU 完成“目标位置与静态盒子 → Mink 位置 IK → OMPL RRTConnect 绕行 → MuJoCo 物理执行 → 视频和指标回收”。本地真实模型与 20 轮 ±3 mm 目标扰动已通过；Colab CPU / OSMesa 20轮通过，可见场景与视频回收已复验通过。视觉、接触抓放和真机同步继续作为后续任务。

## Colab GPU 视觉训练（2026-10-06）

本机已有四份同步RGB示范时，通过CLI上传原字节数据、运行固定官方ACT、收回权重并释放会话：

```bash
python3 experiments/colab-twin/run_vision_colab.py \
  --output experiments/colab-twin/output/vision-colab-NEW-RUN \
  --gpu L4 --gpu-minutes 30
```

每次使用新的output目录。`--prepare-only`只打包检查，不分配GPU；正式运行使用另一新目录。若CLI直连不稳定，可通过命令级`HTTP_PROXY`/`HTTPS_PROXY`使用本机已经运行的代理；不把代理凭据写入仓库，也不自动改系统设置。

默认使用`startup-weight=5`。显式追加`--local-balance`可复用已有近q起步/收尾1:1采样；其余训练参数和预算保持。开关写入上传job，远端fit及本地回收均核对报告采样模式，缺失或错配时拒绝作为完成结果。

入口复用现有Colab CLI 0.6.0安全适配层，独立会话身份、8MiB分片和逐文件SHA；仅同路径同内容的瞬时传输错误每片最多尝试3次（初次加2次重试，退避5/10秒），分配和训练不重试。远端采用独立Python3.12、固定Torch/cu126与LeRobot；五步batch8资源检查通过后，仅一次startup5/FP32训练，优化循环到5000步或600秒先到即停，保存2115步诊断快照。控制器分配后的总预算最多30分钟，另保留最多120秒释放窗口。

默认训练CLI仍限制120秒；600秒仅由`fit --extended-fit-budget`显式开启，物理evaluate预算和原七项离线门控保持。只有最终policy.pt参与准入；snapshot不替代失败最终模型。训练进程完成、文件回收、离线准入、物理抓放分别验收，更多GPU时间不预先保证成功。实际结果见[学习记录](LEARNING.md)。

## 运行

前提：本机 `colab` CLI 已登录且 `colab sessions` 成功。开发机 CLI 0.6.0，当前不要求 GPU。

```bash
python3 experiments/colab-twin/run_colab.py --session so101-planning --episodes 20 --seed 0
# 保留原六秒合成轨迹基线
python3 experiments/colab-twin/run_colab.py --session so101-baseline --mode baseline
```

本地安装固定依赖后，可运行相同实验。没有 OSMesa 时默认 EGL；已有环境变量 `MUJOCO_GL` 优先。

```bash
python3 -m venv /tmp/so101-planning-venv
/tmp/so101-planning-venv/bin/pip install -r experiments/colab-twin/requirements.txt
/tmp/so101-planning-venv/bin/python experiments/colab-twin/run_experiment.py --episodes 20 --no-render --output experiments/colab-twin/output/local
cd experiments/colab-twin
/tmp/so101-planning-venv/bin/python -m unittest test_collision_scene test_grasp_episode test_grasp_workcell test_joint_planner test_placement test_planning_execution test_position_ik test_run_colab test_staged
```

规划输入是 [planning_scenario.json](planning_scenario.json)：六轴起点、三维目标 m、静态盒子中心与半尺寸 m。规划只改变前五个臂关节，夹爪指令固定 0.35 rad；没有人工绕行 waypoint。MuJoCo 3.3.7 / Mink 1.1.0 / OMPL 2.0.1 已固定。

## 本地主线逐层单回合

在已安装 [requirements.txt](requirements.txt) 固定直接依赖的 Python 环境运行：

```bash
python experiments/colab-twin/run_staged.py --render
# 不检查渲染时省略 --render
python experiments/colab-twin/run_staged.py
```

该入口只运行本机 CPU 仿真，不连接 Colab、GR00T、ROS或串口。依赖层逐项检查指定版本并实际导入 native bindings；第二层加载原SO101模型及障碍，真实reset并推进10步；第三层复用Mink IK和OMPL求解，要求直接路径被挡、精确绕行及独立路段复检；第四层复用独立MuJoCo位置伺服执行实例，验收实际TCP、20ms碰撞样本和关节限位。第三层没有神经模型推理，第四层尚无动态重规划。

每次在 `output/staged-<UUID>/` 创建新目录，保存 `report.json`、`planning.json`、`execution.json`、`trajectory.csv` 和派生场景；`--render` 额外保存视频和预览。报告逐层记录 `not_run/running/passed/failed`，只有前层通过才运行后层。缺失依赖/安装版本不符会在第一层停止；不会自动安装、分配云端资源或退回合成轨迹。`servo_episode_completed` 与 `task_success` 分开记录，任务误差超过1cm、碰撞样本无效或限位超出0.01rad会拒绝。

2026-10-01本机单回合四层均通过：reset10步/0.02s；主路线113点；执行7546步/15.092s；TCP误差0.549mm，碰撞无效采样0，限位超出0。756行轨迹全部有限且时间递增，末行TCP独立复算误差一致；378帧视频完整解码且场景障碍可见。32项测试通过（原29项与3项阶段停止边界），系统Python缺失依赖的真实CLI负例退出1，后续三层均未执行。单静态fixture的一个回合不能扩大为抓放、视觉、动态避障或真机验收。

## 结果和验收

云端每次结果保存到本目录 `output/planning-<时间>-<随机后缀>/`，不覆盖以前实验；全部由 `.gitignore` 排除。

| 文件 | 内容 |
| --- | --- |
| `simulation.mp4` / `preview.png` | 640×480、25fps 主绕障物理执行与预览 |
| `trajectory.csv` | 每20ms时间、六轴实际/指令rad、实际TCP m和接触数 |
| `planning.json` | IK残差、被挡直接路径、OMPL精确路径及离散验证 |
| `benchmark.json` | 逐轮目标、规划/执行结果、失败原因、误差统计和负例 |
| `report.json` | 版本、模型SHA、最终误差、碰撞/限位、批次验收及边界 |
| `scene.xml` / `results.zip` | 派生场景与完整结果包；场景引用对应运行环境的模型资源目录 |

通过条件：主正例直接路径被挡但找到精确路径；物理末端误差 ≤1cm、20ms检查无无效碰撞样本、限位超出 ≤0.01rad；请求的批次全部通过；不可达和封闭场景必须拒绝；视频存在。`run_colab.py` 下载后再次检查这些结果。失败不会退回合成扫掠或直线路径。

路径每段按5D欧氏步长≤0.025rad检查。派生场景补底座网格，并显式排除相邻装配；非相邻自碰保留。libccd距离是近似凸包模型指标，不是实物安全间隙，离散采样不是连续碰撞保证。命令速度≤0.4rad/s，未保证拐角加速度、真实电机力矩或抓取。详细证据与边界见 [规划说明](../../docs/MUJOCO_MOTION_PLANNING.md)。

## 模型、上传和资源边界

源模型 [so101.xml](../../workspaces/so101_ws/src/so101_mujoco/models/so101.xml) 与13份完整STL哈希保持不变。上游 [TheRobotStudio/SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100) 的 Apache-2.0 许可证随包保存。旧 `models/scene.xml` include名称错误；旧 `src/SO-ARM100/Simulation/SO101/assets/` 为零字节，不用于实验。

上传采用明确清单：模型、13STL、许可证、脚本、依赖与公开配置；manifest记录每个文件SHA256。个人材料、现场标定、凭据、录制、日志和ROS构建不进入包。脚本不调用跟随器Runtime、ROS或串口。

每次云端运行用 `~/.cache/so101-colab/run-*/sessions.json` 的独立状态。成功或失败都尝试 `colab stop`；正常释放后删状态，失败保留并打印恢复命令。强制终止/断电后的接续owner为根Codex，按该配置检查并释放遗留会话。

接口参考：[Colab CLI](https://github.com/googlecolab/google-colab-cli)、[MuJoCo可视化](https://mujoco.readthedocs.io/en/stable/programming/visualization.html)。

## 单臂夹取工位建模

2026-10-01用户明确只需一台从臂，主从留在现实系统。复用原SO101网格和关节，不复制现场动作模板或标定。按本地BLD-001桌面工位说明的布局思路，新增单臂派生MJCF：0.9×0.7m工作台、开放取/放料盘、相机支架，以及18×18×16mm、10g自由运动绿色物体。桌面顶面转为原生MuJoCo base z=0；这是一组仿真fixture，不是实物测量坐标。

```bash
python experiments/colab-twin/preview_grasp_workcell.py
```

使用现成requirements环境，仅本机执行。每次生成独立的 `output/grasp-model-<UUID>/workcell.xml`、总览/俯视/夹爪近景PNG、4秒夹爪开合视频和报告。前述路径均被Git忽略。原MJCF/STL保持不变；没有Blender依赖。现存BLD-001提示词有内容，但其记载的Blender/GLB/OBJ成品在当前工程中不存在；LightArmPreview.vue和原leader专属STL为空文件，不能冒称已复原成品。动作模板只作为接续资产，本轮不执行现场动作或连接串口。

模型实测：自由物体在重力下落定于料盘底，并出现真实pick_floor接触；夹爪由原位置执行器从约0.25到0.80rad实际开合。无weld/adhesion/物体跟随机械臂的动画绑定，物体在开合预览中未抬起。报告grasp_success/lift_success为null；这轮验收仅为模型、支撑接触和机械开合，抓取/抬起尚待验证。加入自由物体后nq=13、nu=6，旧固定六坐标CollisionChecker不适用于整个新模型，未强行复用到抓取规划。下一步从jaw/object对位及实际接触进入，再验收物体抬升和放置。

建模实现见 [grasp_workcell.py](grasp_workcell.py) 与 [preview_grasp_workcell.py](preview_grasp_workcell.py)。物体质量/摩擦只是公开仿真假设；自由关节和接触语义参考[MuJoCo 3.3.7 XML](https://mujoco.readthedocs.io/en/3.3.7/XMLreference.html#body-freejoint)。

### 单臂绕障接触夹取（本地）

```bash
python experiments/colab-twin/grasp_episode.py --render
```

复用原生SO101网格，增加橙色静态障碍；起点在蓝盘上方，直接关节插值被挡，OMPL精确路径绕行到红盘，再垂直接近、闭爪、抬升并保持。规划用移除自由物体的六轴副本，执行一直保留同一个13坐标物理状态，只给位置执行器发送目标。物体没有焊接、吸附或动画附着；此入口使用SciPy求解指间中心/垂直夹持姿态，已有位置到达入口仍使用Mink。

原夹爪整网格凸包不适合指尖/小物体接触；派生模型添加8×12×16mm指尖接触垫，替换仅两块指爪凸包与目标的接触，其余机械臂/环境碰撞保留。夹爪力矩上限0.15Nm、接触垫摩擦1.0、物体10g均为实验假设，未经实物标定。保留原始MJCF/STL和原夹爪开合预览入口。

2026-10-01本地实测：直接路径被挡，绕行精确解通过；抬升约38.7mm、双指正接触力持续1.48s；2ms逐步障碍接触为0，20ms实际关节碰撞检查无无效采样。空夹物理负例失败，38项测试通过。这是单场景仿真接触夹持验收，尚未完成放置、动态障碍重规划或实体夹取。

每次输出到独立UUID目录，视频、近景、report/trajectory及派生MJCF均被Git忽略。`--empty-close`是负例入口：reset时把物体移离夹持位置，正常执行相同关节动作，应该返回失败。视频用`--render`启用，额外生成固定机位的`grasp-closeup.mp4`（仅闭爪/抬升/保持），便于观察物体离开盘底；已有目录拒绝覆盖。

距离查询使用至少0.1m的局部范围，大于该范围的距离被截断，不能当作实测间隙。这样规避MuJoCo3.3.7/libccd在大桌面盒子、1m查询范围下的假穿透；真实中间障碍拒绝和既有碰撞测试继续通过。

### 搬运放置

```bash
python experiments/colab-twin/grasp_episode.py --place --render
```

完成红盘夹取→绕障搬到蓝盘→下降→松爪→抬手撤离→落定。接近仍用OMPL；搬运使用本场景预选的内侧绕行点、竖直姿态IK和载物碰撞验证（Cartesian间距≤3mm、关节边间距≤.01rad）。载物查询依据当前实测夹持相对位姿，使用独立MjData；执行中的方块一直是自由物体，未附着或设置其运动轨迹。载物距离查询截断在20mm，200μm余量只是离散规划fixture，非实物安全间隙。

搬运模式启用`noslip_iterations=10`，夹爪力矩仍为.15Nm、接触垫和摩擦不变。默认软接触回合出现约.5mm/s缓慢下滑，最终滑出指尖；提高夹持力未解决。按[MuJoCo3.3.7防滑说明](https://mujoco.readthedocs.io/en/3.3.7/modeling.html#preventing-slip)使用Noslip摩擦后处理，仍依赖实际接触，不等于物体焊接；逆动力学语义和计算成本会改变，此入口只验证前向仿真。原抓起入口不加`--place`仍保留默认软接触设置。

2026-10-01本地实测：载物途中双指持续接触，障碍接触0、20ms机械臂碰撞/限位无无效样本；最终物体中心(.238656,.139144,.009921)m，距蓝盘中心约1.6mm。松爪后双指接触力0，物体整体在盘内、真实place_floor支撑、平移速度接近0，撤离后稳定1.48s。41项测试通过：实际完整正例、关闭Noslip后滑落即停的负例、缺少底面支撑/超出盘边/仍被夹住/速度未稳定等拒绝边界。

`transport-place.mp4`为固定机位972帧/38.88s/1280×720搬运放置过程；`placed_detail.png`为最终近景。原总览、夹取近景、轨迹、报告和派生MJCF也分轮保存并被Git忽略。掉落超过100ms即停止，失败时保留已执行轨迹；这是固定单场景验收，扰动批次、动态障碍、实体模型标定和真机仍待验证。

## 状态学习与可止损管线

同一HDF5数据适配官方小配置ACT/裸Torch MLP，独立学习环境、5步显存探针、限时单回合训练与纯策略物理验收，见[LEARNING.md](LEARNING.md)。采集正反例及原动作回放先于训练；数据、权重和运行报告继续排除出Git。状态学习尚未通过纯策略抓放验收。

完整含学习测试使用独立learning环境：`python -m unittest discover -s experiments/colab-twin -p "test_*.py"`（从仓库根运行）。规划环境不要求Torch/h5py。
