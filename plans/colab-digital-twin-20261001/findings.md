# Findings

- 对应开发根为 `/home/muqiao/dev/ros2/projects/so101`；旧 so101-win7 路径是兼容链接。
- 六份文档复制到被忽略的 `local-documents/graduation-20260629/`。本地 manifest 保存文件名、大小与 SHA256，manifest 也被忽略。
- 历史来源：Codex session `019ef2b7-61a2-7ce3-8789-665ed12b303b`，6 月 29 日答辩反思和 DOCX 转换；不把旧助手声明当本次执行证据。
- 当前 Colab CLI 0.6.0 已安装；`colab sessions` 认证调用成功。无需重新登录、导出浏览器凭据或更新 CLI。
- 有效模型含六个弧度关节和六个位置执行器，末端 site 为 gripperframe。模型 SHA256 为 d75253eb568e8a7214db9c631ab7bed4217f608a26f7276ebe9a7636cac82580。
- 复用 MuJoCo 包中的 13 个完整 STL；第三方源目录的同名 STL 是零字节。旧 scene.xml include 名称不匹配，本轮只在实验副本生成场景。
- Git 本地 HEAD 427e3eb 落后已发布 origin/master e5c0168 两提交。源码 app.py、静态前端、鉴权文档、teleop 测试、动作导出器与远端逐字相同；不能依据旧 index 把它们当未交付。
- 仓库远端已核对为 qiaoqiao2521/so101，保持 public/master；本轮不改可见性或重写历史。

## 2026-10-01 自主规划续接审计

- 用户选择 MuJoCo 为运动自主规划核心。原生 Colab 平台继续作为同一项目内部模块；不新建平行仓库。
- 当前主工程、repo-revival 整合快照、repo-scan 两个旧工程和 delivery 已定向比较；现存 MoveIt/OMPL 规划文件没有更完整的外部副本。旧 workspace / follower 路径已是兼容链接。
- `pick_place_runner.py` 实际调用 MoveGroup / OMPL，默认 RRTConnect，支持关节目标、重试和轨迹导出；2026-03-14 非空日志记录 7/7 预设目标通过，多点轨迹存在。本轮不重新认定当前运行或避障验收。
- 5月 MTC Cartesian IK/FK → Gazebo reach 只有开发记录与非空 suite summary。jitter20 的 200 个、jitter50 的 500 个逐轮 artifact 均为零字节；核心 C++ node / launch / evaluator / projector / recorder 缺失。本地快照及有界 Agent 历史没有找回原件。
- jitter50 summary 的 reach 采用 8 cm 阈值，平均距离 5.64 cm、p90 7.34 cm，不能作为精准抓取成功率。原 evaluator 缺失，周边门禁只消费指标，不能替代 TCP 距离计算。
- ROS URDF 是 17 visual / 0 collision；原生 MJCF 是 17 visual class geom / 13 collision class geom。后者仍须验证编译后的 mask、碰撞覆盖和凸包误差，不按 URDF 缺失结论重造全部几何。
- 原 Gazebo 世界桌高约0.75m，目标z约0.8m；MJCF使用自己的world/base/TCP坐标。迁移目标须显式转换并用FK核对。
- `lerobot` 独立源树含 Placo FK/IK；没有证据证明该实现已经在现有 SO101 Colab 平台运行，不作为已验收替代库。
- 实际 AGY CLI plan/sandbox 单次只读咨询返回 MuJoCo + Python IK/OMPL 的单方向建议，并推荐可达性→碰撞→跟踪顺序。仅基于摘要，未独立跑实验；原响应位于被忽略的 local-documents。
- Gazebo官方支持server与OGRE2/EGL无头渲染；本项目未在Colab实测。Jazzy默认搭配Harmonic，旧Classic/Humble链需要迁移；Colab免费且无正计算余额时限制远程桌面。
- MuJoCo3.3.7保持当前基线；Mink1.1.0与OMPL2.0.1是待隔离验收候选，本轮未安装/升级。官方依据集中在 `../../docs/MUJOCO_MOTION_PLANNING.md`。

## 本轮实现新证据

- 源MJCF13个移动collision mesh全部mask1/1；底座四个visual在派生场景复制为collision。排除同刚体、六对直接父子装配及固定底座安装；非相邻负距离shoulder/gripper自碰仍检出。
- 原生CCD在纯yaw相对不变时误报0，派生XML选择libccd；15yaw回归保持距离。其分离距离为近似凸包指标，不是实机安全。默认group3环境不可见的问题通过零mask的group2副本修正。
- MuJoCo实际夹爪状态会微小偏离固定指令，执行碰撞查询必须使用真实q6并解除精确固定要求，规划仍固定；不能以指令替换实际姿态。
- Colab CLI0.6.0远端Python错误不保证本地非零退出，timeout也不保证停止内核；以下载的严格产物/逐轮验收为依据，并在finally释放整个本次会话。
- 当前20轮只覆盖同一个盒子附近±3mm位置任务；离散路径0.025rad/执行20ms，不是连续碰撞、抓取、视觉或真实参数验收。

## 主线逐层验收入口

复用当前MuJoCo/Mink/OMPL实现和现成planning-venv，未重新安装环境。run_staged.py只在依赖版本和实际导入通过后加载模型；run_gate拒绝越过未通过阶段，失败保留其原因及后续not_run状态。已采纳Obsidian Wiki/自动化开发范式与智能体协作.md“按当前任务选择验收依据”：依赖导入、仿真reset/step、精确路径与实际执行是分别观察的结果。

本机真实单回合：reset10步/0.02秒，IK误差0.323mm，113点精确绕行，物理执行7546步/15.092秒，TCP误差0.549mm，20ms碰撞无效样本0，限位超出0。独立CSV核验756行全有限、时间递增和末行TCP误差；视频完整FFmpeg解码378帧，预览显示工作台与障碍。模型与13STL记录SHA，源MJCF未修改。位置执行使用模型原位置伺服；路径仍预先规划，动态重规划未接入。

原29项回归加3项阶段边界检查通过：前层失败不调用后层、规划异常保留执行not_run、依赖失败持久化报告且不编译模型。真实系统Python缺少依赖的CLI负例退出1且task_success=null。脚本默认不渲染；--render可选，按运行环境已有MUJOCO_GL或OSMesa/EGL默认选择。该证据不扩大成动态障碍、抓放、视觉或实机同步。

## 2026-10-01 单臂夹取建模

用户指定先建模、改善场景，并纠正主从为现实系统；本轮只有一台从臂。找到本地BLD-001建模说明、主从场景生成器和动作模板；当前工程无其记载的Blender/GLB成品，LightArmPreview.vue与leader专属STL为零字节。复用完整的原生从臂13STL，新增grasp_workcell.py/preview_grasp_workcell.py及动态物体/夹爪检查。

新模型包含工作台、开放红/蓝料盘、相机支架、自由物体；生成1280×720三视图与100帧/4秒机械开合视频。原模型SHA仍d75253eb568e8a7214db9c631ab7bed4217f608a26f7276ebe9a7636cac82580。物体18×18×16mm、10g；实测中心z从0.012m落定至0.009784m，真实pick_floor接触。夹爪实际范围0.250019–0.799997rad，预览期间物体抬升约0；grasp_success/lift_success=null，尚未夹取成功。视频独立全量解码通过，34项回归检查通过。派生MJCF可编辑，原模型不改；无实体或云端操作。

结果保存在Git忽略的experiments/colab-twin/output/grasp-model-72f103318b2a4cf78c7b89f317ee53ed/。原场景建模说明只用于布局参考，仿真坐标和物理参数不当作实物标定；现场模板不复制发布。后续owner根Codex：先对位/接触建模，再以物体抬升与持续夹持验收；已有静态规划入口及遗留交接保留。

## 障碍接触夹取

原TCP位于固定指尖，不能直接当指间中心。派生夹持点在gripper局部(.006,0,-.094)m，使用独立状态求垂直姿态IK；下降到世界z=.019m以避开指尖/盘底碰撞。全网格凸包与小方块接触出现毫米级穿透/下挤，指尖接触垫替换仅目标与两块指爪的接触；其余链接和所有物理环境仍与目标碰撞，原网格仍负责机械臂与桌面/障碍碰撞。接触垫尺寸与摩擦、.15Nm夹爪力矩是未标定仿真假设。

MuJoCo3.3.7/libccd在worktable盒子和collision_shoulder_2距离查询distmax=1m时给出-.2456m假穿透；实际顶点最低z=.0162m且无物理接触，distmax=.1m返回+.0162m。checker改为max(.1,margin+.05)m的局部查询，远距离饱和；合法起点和真实中间障碍负例通过，既有碰撞测试继续通过。

物理执行使用单一MjData；IK/距离查询独立，避免运动学查询改变现场。障碍接触按2ms每步统计，机械臂限位/环境/自碰按20ms状态检查；规划边按.015rad离散验证，尚非连续碰撞证明。保持段须全部样本抬升≥25mm、双指法向力>.02N、无桌面/盘底支撑，持续≥1s；空夹或短暂抛起不能通过。
