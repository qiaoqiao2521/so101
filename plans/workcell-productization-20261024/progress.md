# SO101 产品化进度

## 2026-10-24 — M1b准入取证完成，M2取消与M4配方实施

Current：上一目标轮次=progress。新准入观察c0045f5f…原pass；14次poll（13未ready、1准入），最终14.613ms／完整拍33.843ms。job调用约.067ms，不是主要成本。最大116ms是callbacks105.803wall/3.227CPU，I/O与宿主等待尚待区分，不无据新增底层优化。

Done：M2六技能真实证据接点已审，不能把旧stage直接标技能成功。取消终态已修：请求和实际取消分列，晚到请求不遮原pass/fail，安全／清理原失败保留。M4新增可编辑station-recipe v1、两个X配方样例和前后端薄校验；原Station、任务与评分复用。未知可选元数据保留，历史验收不作为新任务通过；拒绝未支持单位／旋转／动态尺寸语义。根64项相关Python及68项前端数据检查已通过，均非物理验收。

Remaining：工作台首轮17项实际配方往返、旧任务不继承、文件读取竞态和390px检查通过，真实任务写请求0、页面异常0；独立审查另复现负时长被旧导入器改成1，已在配方路径明确拒绝，前端最终构建／该反例复验待做。新配方原完整物理与worker运行中取消待验。M2六技能生命周期／恢复、M3 20+20、M4同世界卸货未实现，不因静态交换降格验收。

Issues：工作台仓另有Drone记录器、测试、说明及其原计划在途修改，保留原owner，不混入SO101提交。首轮构建读取编辑中的导出返回类型失败，修正后webpack构建成功（2项原包体警告）；新时长反例修复后另做最终构建。AGY／Qoder此前不可用，CodeBuddy本轮再次空正文，内置GPT完成独立审查并复现上述缺陷。旧准入观察Kernel已确认COMPLETE，本机无原物理在跑；云验证沿用Kaggle。

Next：根固定SO101源码；将浏览器实际导出的new-recipe.json（station逐字段等于原X+20）送原物理及真实取消。前端并行补时长反例与最终构建，不修改在途物理源码。Knowledge=already_covered，沿用第20节分层验收；项目新事实只写本计划。

## 2026-10-24 — M1b 实测q异步回位4/4，保持显式候选

Current：本轮原物理与证据闭环结束，详见[m1b-return-results.md](m1b-return-results.md)。固定b317d4f在Kaggle同VM右B→C／左C→B四次原pass，源码运行期间未改。X开发布局保持，未改IK或盘壁阈值。

Done：根101相关CPU检查通过；同模型三对path/method/report和75state/arm/distance覆盖逐位等价。根与独立reader回读原4/4、244+244、全部15635轨迹、释放脱离回位、自由物体、视频和worker回执，warnings=0。候选return job均consumed/joined/owned_ack，首指令accepted+issued且保持连续。

Remaining：左首retreat完整拍143.018→33.347ms，右36.634→30.314ms；候选仍超20ms。process wall右50.884→49.745s，左50.878→51.119s；整程收益不一致，不切默认、不宣称提速或50Hz。原默认loaded_jaw_preload保留，候选显式可复跑。M2恢复、20+20、配方卸货仍未完成。

Issues：新等待右6拍／左13拍，原hold/release另有调度差；不把等待或其他VM秒数计入算法收益。原轨迹未存逐拍全部sweep点，只核已记录guard与原裁决。Qoder审查超时、CBC空正文未计有效复审。

Next：根Codex只针对候选接纳的controller 22.779/25.369ms做实际分段测量，区分绑定、桥接和首指令；先证因果再改动。Knowledge=already_covered，沿用Wiki《ROS2 与 FishBot》第20节，不把候选保留写成默认晋级。

## 2026-10-24 — M1b 实测回位候选，默认关闭

Current：X两侧已验开发布局沿用，不重写IK或放松盘壁阈值。接续旧周期最大140.476ms的separate→retreat入口。新Kaggle原观察ca00cc74…原物理pass，78.34sim/48.142episode-wall、49.470process-wall/59.080process-CPU；244+244、自由物体、释放脱离回位和490帧均独立回读。插桩复制快照额外120ms，cProfile树父帧不完整，不能把341ms最大拍写成原固有成本。

Done：同MuJoCo3.15、同MJB、无mj_step独立复算5次，原返回路径逐位相同；单次128.07–136.87ms，中位131.131ms。每次1条直接路径、75状态、75原arm检查及75释放物距离查询，未走OMPL。候选由根GPT实现，Qoder超时后内置GPT独立审查；新增async_measured_return.py显式开关，默认仍loaded_jaw_preload。复用原异步job、SeparationSnapshot和独占模型，从实际q快照计算原_return_path，现场再验桥接、首命令和90s预算；在线保护、244、评分、取消清理不变。审查发现issued回执缺口，已补到原data.ctrl写入后。

Remaining：根相关CPU回归与新交接反例核验后固定源码；先同输入三对无物理等价，再在Kaggle同VM运行X+的B→C及X−的C→B原evaluate_station --timing。未测候选不记成功，不由等待拍数变化记提速。整组终态前不改在途源码或提交。

Issues：本机Blender两段后台动画仍运行，未抢本地物理资源。原观察与复算原件在忽略目录output/m1b-return-profile-20261024；私有wrapper沿用round100/round103，候选物理沿用round104，不新建调度。当前候选原物理not_run、完整50Hz未通过。

Next：Owner=根Codex，固定通过局部核验的候选源码并推送，完成三对等价与原两工位反序物理。Knowledge=already_covered，沿用Wiki《ROS2 与 FishBot》第20节分层验收，新时序事实留本计划。

## 2026-10-24 — M1a Station／网页入口2/2原物理通过

详见[m1a-station-entry.md](m1a-station-entry.md)。两开发布局已接原5186网页选择、保存/刷新、复制/JSON与任务入口；新任务6e86ec73…、f7c265d5…分别78.02/78.08sim、59.131/58.445episode-wall，原真实抓放、释放、脱离、回位全部通过。planned/measured244、双worker、自由物体与488帧视频均独立核实，warnings=0，无障碍接触或安全停机。项目浏览器刷新同ID、一次POST和视频读取断言通过；独立离线读回不扩大为完整网络时序重演。新入口未采完整周期或精确process CPU，不补历史值。

根50项Python、33项网页数据、3项服务及生产构建通过；桌面/390px九项无运动浏览器通过，根查看截图。SO101运行引用084cc7f；工作台本轮abc0ac7/2b9fd90，另在途Drone改动已由原owner提交de94a6d，本轮保留其独立责任，不声称共享仓库全冻结。主FishBot与Mint未触碰，5187他人服务未停；本轮5186保持可用。

M1a总体仍in_progress，默认±10mm不变；新域仅开发先验。恢复/M2、20+20/M3、配方卸货/M4均未完成。M1b开始只读周期归因：旧X面板15641拍/281慢拍，最大140.476ms集中同步回位入口，下一步先细分_return_path，再论已有worker迁移，不做无依据SAT微调。该旧数据不是新网页计时。Knowledge=already_covered，第20节分层验收；新事实留本计划。

## 2026-10-24 — 接续 M1a：Station／网页入口实施中

上一目标轮次分类=progress：X两新布局及两中心原物理4/4，源码与证据已交付。当前沿M1a把已验参数接入原Station与既有网页，仍不宣称连续区域或M1a整体完成。

新增可编辑execution开发声明，缺省保留原±10mm；盘位／高位／静态视觉先验显式保存，节点与声明不一致则具体拒绝。未知可选元信息警告保留，不参与物理参数。原判据、244、90sim/120wall与原reset/RGB数据边界保留。网页添加两样例按钮，载入仅新建草稿并清除当前结果关联，原任务记录保留；导入、保存与复制保留execution。

实际工作台位于FishBot独立工作树 `/home/muqiao/worktrees/fishbot-workbench-code-rebuild-20261018`，既有codex分支，非dirty main。agent-link已发现可用：AGY实调参数不兼容失败，CodeBuddy实调返回空正文，未冒称有效产出；当前GPT与两个内置工作者完成薄实现。网页工作树另有DroneDiagnostics/drone-diagnostics在途修改，保留不纳入本轮提交；主FishBot的mecanum/delivery-timing也未触碰。

当前局部Python／数据层检查已做，根复验与生产构建进行中。浏览器与新Station原物理待验，不能由先前run_workspace_case成绩代替。Owner=根Codex；构建结束后先无运动浏览器往返，再资源允许时单次网页真实抓放。Knowledge=already_covered，第20节分层验收；输入合同与新结果留原计划。

## 2026-10-24 — X 新布局原物理4/4通过，保持开发能力

源码e7f921c在Kaggle v1单VM串行结束；两个X新布局与两个原中心全部原pass。右侧X+20mm用红盘+20mm／高位54mm，左侧X−20mm用红盘−5mm／原60mm；不是原固定盘包络扩展。原真实夹持、搬运、落盘、释放、脱离、回位、planned/measured244、双worker清理与自由物体均核实，无障碍接触或安全停机。详细原成绩、UUID、规划/进程wall/CPU见[m1a-x-results.md](m1a-x-results.md)。

根读回原件、RGB估计、计划路径末端FK、全回合关节余量并看右侧终态图；独立reader6项失败/缺证反例通过，真实warnings=0。四视频480/488/489/500帧与原记录一致，相机前置7/7、最大.616511mm。完整周期仍58/70/81/72拍>20ms，完整50Hz未过；20+20/恢复/配方/卸货未新增验收。原任务90sim/120wall、1mm与所有安全条件保留。

源码执行期间无改动/提交，组终态后才回写本记录。云原生COMPLETE，无拥有的本地评测在运行。下一步：将已验开发布局与原固定盘边界清楚交给用户；不直接开放连续工作区或再次做无依据底层优化。Knowledge=already_covered，沿用第20节分层验收；本轮新事实留在项目。

## 2026-10-24 — X 方向薄适配，原物理待验

已区分 X+20mm 高位腕限位与 X−20mm 盘壁证书不足；根独立复算全网格投影。详见 [m1a-x-results.md](m1a-x-results.md)。没有将保守下界当真实最短距离，也未用 libccd 负值作裁判。

新增显式红盘平移与 .054–.06m 取料高位参数，默认保持原值。选定右 +20mm 红盘／54mm高位与左 −5mm 红盘／60mm高位；候选原参考起姿、下降、244闭爪和提升证书全过。84 项相关检查通过，不计物理成功。将用 Kaggle 单 VM 串行运行两个新布局与两个原中心，仍为 90sim/120wall；新布局不是原固定盘位包络或算法提速。

当前整组原物理 not_run。源码固定推送后再发起，整组终态前不改在途源码。Owner=根 Codex。Knowledge=already_covered：原第20节分层验收原则；本次几何事实与布局成绩只写项目，不增加共享知识页。

## 2026-10-24 — M1a 首切片完成：范围外原物理 4/4

实际结果见 [m1a-results.md](m1a-results.md)。固定源码 `0ef4068` 在 Kaggle v1 串行运行四例：主工位中心／Y+20mm、第二工位 Y−20mm／中心，原物理 4/4 pass。原释放、脱离、回位、planned/measured 244、双 worker 清理、自由物体及四份视频均独立核实；无碰撞、安全停机 0。相机前置 3 正＋4 负全过，最大误差 0.616511mm。云离线 11 点同样 9 点通过。

仅新增两个固定范围外点的可复跑开发能力，不宣称整个 ±20mm 区域或 ±150mm。没有改 IK 目标、模型权重或安全判据；网页与默认仍为原 ±10mm。M1a 整体 in_progress，连续包络与产品准入仍待做；M1b、恢复、20+20、配方、卸货均未新增验收。完整周期仍分别有 68/52/65/79 拍 >20ms，50Hz 未通过。

根回读原始 JSON、完整周期、规划／进程 wall/CPU、碰撞、释放、回位与 ffprobe 实际帧数；内部 GPT reader 的 4 个缺证／失败反例通过，真实原件读回 warnings=0。运行源与原评分来源均为上述固定提交；整组终态前未改源码或提交。云原生 COMPLETE；无其他拥有的评测仍在运行。原 TGZ 是完整原件，重复 loose-file 下载客户端已停止，不使用其不完整副本。

Next：核 X−20mm 下探盘壁证书与 X＋20mm IK 残差的不同成因，再决定姿态／初值或布局适配；不直接全放开，也不转回 SAT 微调。Knowledge=already_covered，沿用原第20节分层验收原则；新项目实测留在本计划，不改在途 Wiki 或旧 pending。

## 2026-10-24 — M1a 实施中：原物理待验

- 完成可复跑 FK/IK/保守碰撞离线探针及编译 frame 核对。11 个区内／边界／区外点，9 个通过；X±20mm 的不同拒绝原样保留，Y±20mm 进入下一轮原物理候选。产物 `experiments/colab-twin/output/workspace-m1a-20261024/report.json` 被 Git 忽略。
- 控制器新增可选静态目标区域，原默认、网页 ±10mm、碰撞／244／TTL／预算不变。开发 profile 复用原执行、原评分和 StationVideo，每例独立 UUID，保留原失败。
- 根独立实跑：7 项空间探针检查、69 项控制器／原 Station／原汇总检查、4 项开发入口检查通过；其中开发入口 mock 物理，不计抓放成功。原控制器检查一度因实验 venv 缺 cv2 导入失败，系统 cv2 也有 NumPy ABI 冲突；停止该分支，仅补隔离 venv 的匹配包后原检查通过，未降级已有依赖。
- 下一运行：Kaggle 单 VM 串行四例，主工位 center→Y+20mm，第二已有工位 Y−20mm→center。复用原 bootstrap 与串行进程 wall/CPU 记录，原每回合 90sim/120wall；不是性能 A/B，不切默认，不开放网页新区。原云 leaf 任务已确认 COMPLETE，无重复启动。
- 当前新四例原物理状态 `not_run`，50Hz、20+20、行为树、配方与同世界卸货均未新增验收。源码固定推送后才发起，整组终态前不再修改或提交运行源码。

## 2026-10-24 — D0 计划完成，实施未开始

用户请求：将工作区扩展、恢复技能、快慢环、工艺寻优、车臂配方协作写为 SpecMesh。根 Codex 与三个内部 GPT 工作者分别核运动学、周期／seed、配方／FishBot 所有权，根串行整合。

### 已完成

- 建立 [task_plan.md](task_plan.md) 和 [findings.md](findings.md)，列明阶段、原入口、验收、回退与缺证项。
- 修正前提：±10mm 是输入边界；IK 已松弛完整姿态；进程首次 seed、transport/separation worker 已存在。
- 保留现状：F2ce 两工位 4/4 原物理通过、性能不一致未采用；F2cf 148 拍 >20ms，完整 50Hz 未过。未改历史判定。
- 明确六技能复用原执行器、配方复用 Physics/bridge；5186 已由 FishBot runtime 提供。Mint 不改，任意编排／配方交换／连续卸货未实现。
- 算法工厂转为有证据的性能支线，无新瓶颈证据时不追加低层试验。默认保持 `loaded_jaw_preload.py`。

### 阶段状态

| 阶段 | 状态 | 尚缺证据 |
| --- | --- | --- |
| D0 前提／计划 | complete | 只完成文档，不代表功能通过。 |
| M1a 工作区 | planned | 坐标/FK、IK 区内外、定位遮挡、完整抓放。 |
| M1b 快慢交接 | planned | 全认证保留的交接及完整周期实测。 |
| M2 技能／恢复 | planned | 取消、失败保留、可认证撤退、物理恢复。 |
| M3 冻结面板 | not_run | 独立 20 正常＋20 扰动及完整回读。 |
| M4 配方／卸货 | planned | 往返、同世界两货物、取消／库存交接。 |
| M5 寻优面板 | planned | 稳定基线、可重复改善、采用／撤销。 |

### 下一实施入口

Owner：根 Codex。先读 `station_executor.py:170`、`grasp_episode.py:114`、`visual_grasp_controller.py:334` 和模型工具轴，形成 **M1a 坐标合同与只读工作区筛选**。先比原 IK，不直接删除 ±10mm 校验，不继续 SAT 微优化。局部通过后选区内外点，经原 `evaluate_station.py`／`run_physical_episode` 做原物理。

M1b 复用 F2cf 叶段报告定位剩余同步责任。M4 配方草案可独立进行；同世界实施回源 FishBot 连续计划，不修改其在途任务。共享仿真先核进程；如接 Kaggle，单列机器与负载。

### 文档验收与知识收尾

本轮仅做定向核查和文档；未启动仿真、训练、云任务、服务或实体动作。提交前只验变更范围、链接、状态一致性和 diff。原成绩均来自 F2 记录，无新增物理通过宣称。

文档检查：新三文件与研究索引共 27 个本地链接目标存在，`git diff --check` 通过；独立只读审查未发现技能／旧裁判、同世界／取消或阶段状态的实质阻塞。源码与评测产物未变。

跨仓索引已写入研究根 `PROJECT.md`。初查时该文件混有空地臂／无人机在途计划，未将其他 owner 的改动并入 SO101 提交。随后独立读回：研究根 `9cae17a` 已整合该索引，工作树干净；本仓计划 `6de1206` 已推送，GitHub API 与 `ls-remote` 均回读相同提交。跨仓索引 pending 已解除，研究根无远端，本地提交不冒充云端发布。

Knowledge=already_covered：采用 Wiki《ROS2 与 FishBot》第 20 节“动作成功、交接成立和候选晋级分别验证”。没有新运行结论，不改在途知识页。旧 F2cf 插桩经验回写的 pending 保持原 owner，本次状态不冒充其已完成。
