# M1a：固定红盘的 X 向补证

## 本轮结论

保持原红盘位置、几何、关节限位和 1mm 门槛。左侧 X−20mm 的原拒绝来自候选分离方向不足，下降／闭爪／抬升已完成补充数值认证。右侧 X+20mm 原大开度路线仍不能整链认证；显式高位收口候选已完成首轮原物理抓放，原中心回归通过。网页准入与默认不变。

左侧补证仍不是抓放成功。此前移动红盘的四次物理成功仍属于新布局；本轮新增的右侧固定盘物理结果独立记录。

## 实现范围

- `NativeSupport.certify_directions` 是独立可选 API。只对一个 mesh-box 对尝试调用方方向，沿用原 `certificate(full=true)`、区间投影、平方比较和算术环境检查。
- 原19轴查询实现与默认编译选项未改。额外查询使用独立本次 frame，不写回证书或方向历史。
- `mesh_box_axes.py` 从编译网格凸包面法线、凸包边与盒轴叉积生成搜索方向。凸包只用于找方向，实际认证仍投影全部原编译顶点；每个姿态重新计算。
- `probe_workcell_workspace.py` 增加显式高位和补方向诊断开关。原 `offline_screen_pass` 与原拒绝保持；额外结果放在 `extra_axis_screen`，始终标记 `not_physical/not_admitted`。
- 原配置路径检查遇失败即停。新增 `complete` 标明实际覆盖；`observed_samples=1/required_states=244` 不能冒称完整扫掠。下面右侧全64点另由独立局部脚本覆盖。
- 原生未认证结果的未计算平方字段可能为 NaN，诊断输出写作 null；`certified=false` 保持。没有将非有限值改成零或放行。

## 左侧：固定 X−20mm

世界目标 XY=.22/−.13m，原高位60mm，原下降高度19mm。原红盘中心仍为 .24/−.13m。

| 检查 | 实际采样 | 原19轴拒绝数 | 补方向后 |
| --- | ---: | ---: | --- |
| 原参考起姿 | 2 | 0 | 全部认证 |
| 下降 | 74 | 1 | 全部认证 |
| 闭爪 | 244 | 244 | 全部认证 |
| 抬升 | 74 | 1 | 全部认证 |

246 条新增几何对认证均使用完整支持投影，平方门成立；本轮选中见证下界最小12.083509mm。它是分离下界，不是最短欧氏净距，也不等于动态跟踪余量。原 `offline_screen_pass=false` 保留。

原件：`experiments/colab-twin/output/workspace-x-20261024/fixed-left-extra-axes.json`。

## 右侧：固定 X+20mm

60mm高位仍是原腕俯仰95°限位问题，参见 [原诊断](m1a-x-results.md)。本轮沿用已有54mm可解IK姿态，未改IK阈值、限位或红盘。

独立脚本从原保存关节姿态重建72点下降与244点闭爪，重现14＋50个拒绝。对这64个点逐一搜索网格凸包面／边叉盒轴，最后把候选方向交回原生区间门认证：

| 原拒绝组 | 本轮逐点覆盖 | 新方向认证 | 仍未认证 |
| --- | ---: | ---: | ---: |
| 下降 index58–71 | 14 | 0 | 14 |
| 闭爪 index0–49 | 50 | 18（index32–49） | 32 |
| 合计 | 64 | 18 | 46 |

浮点搜索的下降最佳投影间隙为−2.459943～+0.922209mm；它们不足以提供1mm证书。闭爪18个候选见证为1.025453～2.880327mm，全部经原生数值门复核。没有把“找不到证书”写成物理碰撞，也没有据负投影间隙调用物理运动。

原件及复跑脚本位于本机私有目录：

`/home/muqiao/.cache/ros2-factory/codebuddy-so101-20261021/round109-x-certificate/`

- `right_screen.py` / `right-screen.json`：64点完整浮点候选搜索，单进程单BLAS线程，26.590s，`mj_step_calls=0`。
- `native_readback.py` / `right-native-readback.json`：同64点、同几何对、同1mm门槛，18认证／46未认证。

## 验证与接续

原 native、可选方向API、原保守检查和空间探针的46项相关测试通过。现用packed／inline／seed-bound组合下新增7项测试也通过。负例覆盖真实右侧被拒姿态、相交／不足1mm、空／非法方向、错误算术环境、strict JSON，以及首失败前缀的覆盖声明。内部GPT独立回读左右原件，确认无缺失、重复或换对；CodeBuddy本次返回空结果，不计有效参与。

补充方向API尚未接入生产检查器。左侧仍需将补证作为显式候选接入全部规划／实测检查，再用原物理评分验证。右侧已完成高位0.35rad收口路线的静态检查和首轮原物理，详见下文；不扫参数，不改默认。

Carry接续改动另留在途，未混合交付。M1a整体、连续区域、20＋20、完整50Hz均未新增通过。

复跑左侧诊断：

```bash
cd experiments/colab-twin
python probe_workcell_workspace.py \
  --source ../../workspaces/so101_ws/src/so101_mujoco/models/so101.xml \
  --point fixed_x_minus20 .22 -.13 --extra-mesh-box-axes \
  --output output/workspace-x-20261024/fixed-left-extra-axes-new.json
```

右侧前缀诊断另加 `--pickup-hover-z-m .054`，目标改为 `.26 -.13`。首失败处停止，完整64拒绝点复核使用上述私有脚本；两者覆盖范围不同。


## 右侧下一候选：高位收口0.35rad

已完成同一姿态／原盘位的私有几何检查。高位0.5→0.35共244点、开度0.35下降72点、低位0.35→0.015共244点、原上升72点，总632点均由原19轴直接认证；没有调用新增补证放行。原开度对照仍重现64拒绝中的46未认证。

双pad顶点投影的最小总开口38.890855mm。轴齐20mm方块沿斜闭合轴的投影为27.679576mm，加两侧各2mm为31.679576mm，容量满足。然而同一down q5下，固定指侧名义投影余量在0.5与0.35开度下均仅0.160212mm，活动指侧由20.624598降为11.051067mm。该诊断只使用声明目标XY与pad顶点，不读取物体真值；两侧各2mm是诊断目标，不能冒充新执行硬阈值或保证稳定接触。

下一步实现显式开发参数 `pickup_open_jaw_rad=.35`，默认仍.5。高位收口须通过原扫掠、实测夹爪到位后才下降，再用原90sim/120wall物理回合验收。源码及三例profile已在82918d7固定并完成首轮原物理。私有原件为同目录 `preclose035_screen.py` 与 `preclose035-screen.json`。


### 显式执行候选与物理前检查

`VisualGraspController` 新增 `pickup_open_jaw_rad`，只支持原.5和显式.35。原.5不新增阶段、不改原分辨率。候选在视觉交接完成后，用实测高位q认证收口，再保持原高位等待夹爪误差≤.003rad且速度<.05rad/s；未到位不下降，阶段和总时钟不重置。非零完整高位／低位扫掠收紧分辨率，实际246点；零运动沿用原静态检查。在线弦认证、原90sim/120wall、IK／碰撞／成功评分保持。

根对包含Carry的工作文件独立跑91项相关测试；另直接从Git索引导出不含Carry的候选源码，83项控制器／扫掠检查再次通过。原中心回归和实际抓放已由Kaggle原物理通过，详见下文。开发入口：

```bash
python run_workspace_case.py --profile scenarios/workspace-x-preclose-m1a.json   --case right_preclose35 --output-dir output/workspace-x-preclose-dev
```

原大开度对照为 `right_original_open50`，原中心回归为 `center_regression`。保持原红盘，不据632个静态采样宣称闭环成功；不将预期对照失败改成pass。


## 首轮原物理：固定盘右侧通过

固定源码 `82918d77b7b3d52b9f123a5d91f3997dcc122836`，Kaggle `muqiaoqiao/so101-x-preclose-20261024/1`。同VM三例串行，原runner逐字相同，整组终态后才修改源码／记录；原裁判、原19轴、1mm、90sim/120wall和回退保持，不注入补方向API。这是功能验证，不是节拍A/B。

| case / UUID | 原裁决 | sim s | episode wall s | process wall / CPU s |
| --- | --- | ---: | ---: | ---: |
| right_original_open50 / 1d8288ea-6408-48a7-90ad-fc0a0657c795 | fail：grasp_leg_collision | 0 | 3.033 | 3.978 / 5.476 |
| right_preclose35 / be15f72b-6f14-4d50-9c4c-8ad68020b0d3 | pass | 79.26 | 50.714 | 51.808 / 61.861 |
| center_regression / 62a5a8c7-4b86-4089-847a-ab9582924a9a | pass | 76.62 | 48.717 | 49.819 / 59.551 |

原大开度在初始化抓取腿认证时拒绝，零物理拍、无录像／planning文件符合原失败路径；不将预期失败改判通过。两成功例自由物体、weld=0/mocap=0、全部状态finite/arm_valid、障碍接触0和safety_stop=false。保存规划模型的红盘floor仍(.24,−.13,.001)m。

右候选真实抬升40.989mm、持物35.02s、落盘静稳7.54s；原释放审计通过，71.902s已脱离，最大XY漂移.192482mm、脱离后峰值接触力0。原回位终态home最大q6误差.102544mrad，最大关节速度9.47e−8rad/s，transport／separation均consumed/joined/owned_ack且无未知清理。planned／高位preclose／measured闭爪各246点通过。下降前一物理记录在17.06s，夹爪距.35为1.328e−6rad、速度3.367e−7rad/s；17.08s记录进入descend，保持同一世界及单调时钟。

中心原244点planned／measured检查保持，持物32.84s，释放审计、脱离与回位通过。两视频实际ffprobe为496/496与479/479帧。

完整周期右3963／中心3831拍；P95为14.943／14.889ms，max50.616／48.890ms，分别72／68拍>20ms，完整50Hz仍未通过。不同输入不是性能对照，不把wall差报告为提速。

原件：`experiments/colab-twin/output/workspace-x-preclose-20261024/kaggle-v1/unpacked/so101-evidence/`，batch=`workspace-preclose/85640115-726c-4a24-8433-7e93c02a6dff/`。根独立readback保存于同kaggle-v1的`root-readback.json`。

接续：保留显式候选，不改默认／网页±10mm。已有第二放置工位(.20,.20)m复验也通过，见下文；连续工作区、扰动20＋20仍未验。


## 第二放置工位：原物理复验通过

固定 `46ab29ee5c0939793d7716fb24d250aa9a874e34`（相对82918d7只改开发case与结果记录，执行代码相同），Kaggle同kernel v2单例。第二放置目标(.20,.20)m，右侧取料仍(.26,−.13)m、原盘不移、高位54mm、显式开度.35。UUID `5e8a109c-2db5-4460-83a9-1968a5271124` 原pass，82.34sim／49.661episode-wall／50.742process-wall／60.844CPU。

独立读回确认：原红盘全部属性、robot/base/actuator/option、初始qpos/qvel与v1相同；实际place_floor与原release_plan目标为(.20,.20)m。preclose实测到位门与v1一致，三项完整夹爪扫掠各246。真实抬升34.987mm、持物37.70s、蓝盘静稳7.50s；75.020s完成脱离，最大漂移.171841mm、脱离后峰值力0；home实误差.101346mrad。无碰撞／安全停机，free=true/weld0/mocap0，双worker原owned_ack/joined/consumed且无不确定清理。录像515/515实帧。

原transport候选60／57mm因IK拒绝，按既有回退走54mm并完整认证；没有删回退或放松限位。完整4117拍，P95=16.059ms、P99=26.272ms、max=135.465ms，82拍>20ms，完整50Hz仍未通过。

| 成功例 | 初次OMPL / 含后处理 elapsed s | transport worker wall s | separation worker wall s |
| --- | ---: | ---: | ---: |
| 右侧主放置工位 | .133769 / .291910 | 2.383539 | 1.191756 |
| 原中心回归 | .140013 / .306186 | 2.180770 | 1.094895 |
| 右侧第二放置工位 | .164560 / .346693 | 2.863927 | 1.301937 |

worker耗时与主回合重叠，不能相加；两个云VM和不同目标的wall差不作为提速。v2 batch=`349ac15b-0b7c-445e-aa45-89f6580d12fe`；原件在同output的`kaggle-v2/unpacked/so101-evidence/`。两轮各有根`root-readback.json`和独立`independent-readback.json`；原monitor逐行重放与skill_evidence全字段一致。两个指针文件对应同UUID，不多计回合。

**保留为右侧固定盘的显式开发能力。** 右侧同一取料点在两个已有放置工位均完成原抓放／释放／脱离／回位；中心默认回归通过；原大开度失败保留。不是连续工作区认证、扰动20＋20、网页新准入或50Hz达标。左侧补方向仍仅静态认证，下一步需显式接入完整规划／实测检查并用原物理验证；Carry接续继续独立保留。

## 左侧执行候选：补证接入，原物理待验

显式 `RoutePolicy.mesh_box_axis_refinement=True` 才开启，默认False。原19轴先查询，仅对 `no_separation_certificate` 的原失败mesh-box补方向；完整顶点区间门、285对、原1mm均保留。实测检查器与transport/separation/return上下文贯通；候选使批量桥回原逐点检查，避免绕过补证。显式False可覆盖加载策略的True。算术／ABI／非有限值错误保持原拒绝；右侧无证NaN哨兵只保留诊断失败，不放行。

根用原固定左侧IK结果复核，开启后参考2／下降74／闭爪244／抬升74点全通过，246次整帧补证、无error/rejected。闭爪全局最小下界1.409754449mm，最近对仍是 `pick_wall_y_1/collision_lower_arm_1`，不能把补证单对12mm当全场景净距。原版下降第74点拒绝、闭爪／抬升首点拒绝保留。闭爪244点本机8.682s，属于功能补证成本，不称提速。

235项相关测试通过。离线原件与复跑脚本在 `experiments/colab-twin/output/workspace-x-left-refinement-20261024/offline-screen.json` 和同目录 `offline_screen.py`。这些是采样几何检查，尚未物理积分，不代表抓放成功。

候选profile：`scenarios/workspace-x-left-refinement-m1a.json`，首批依次 `left_original_axes`、`left_refined_axes`、`center_regression`；可靠通过后再已有第二放置工位 `left_refined_axes_secondary`。原盘不移动、不改取料高度／夹爪开度／评分／90sim120wall，固定源码后沿原Kaggle运行。refiner与NativeSupport属于同一编译model owner，几何尺寸／mesh／pair改变须重建checker，不跨worker共享，不新增内容锁。默认和网页准入保持。

## 左侧首轮原物理：补证通过，执行超时

固定源码 `26a0a1d4779ff9d5db2155c8ede840f3498bfc70`；Kaggle `muqiaoqiao/so101-x-left-refinement-20261024/1`、batch `dc1e551c-7875-4660-bfd5-bf7af792a21b`。三例串行，原runner/probe不改，全部终态后才继续源码。中心回归通过不能替左侧候选成功。

| case / UUID | 原裁决 | sim s | episode wall s | process wall / CPU s |
| --- | --- | ---: | ---: | ---: |
| left_original_axes / 93d949ce-8479-494d-b7c9-4bc9650f2924 | fail：grasp_leg_collision | 0 | 2.995 | 3.998 / 5.505 |
| left_refined_axes / 2c6637a9-6544-404f-9044-ec2b68bee3de | fail：wall_time_limit | 22.56 | 120.757 | 121.779 / 123.497 |
| center_regression / 30819b8a-cac1-4cec-8ced-2199a428b9dd | pass | 76.72 | 47.980 | 49.096 / 58.732 |

左候选仍在close，未抬升／Grasp／释放／回位。planned与measured闭爪均244点通过，实测补证162/162、error=0，只有几何证据，不能记抓放成功。1128完整拍＋1中断拍，P95=351.625ms、max=14267.425ms、176拍>20ms。初始化41.025wall／40.129callingCPU，首close控制器14.207s；有具体计算成本，不能笼统归因宿主等待。原90sim／120wall不放宽。捕获141帧但编码0、`video_wall_time_limit`、无有效mp4，不将捕获数当录像帧。

中心真实抬升40.998mm、持物32.92s、静稳7.54s，69.364s脱离、XY漂移.211361mm、脱离后力0，home误差.102544mrad，480/480实数录像。3836完整拍P95=14.251ms、max45.140ms、52拍>20ms，50Hz仍未过。原左baseline在初始化拒绝，无轨迹／视频；空集合不作物理状态通过证明。

根与独立reader从原件核原裁决与monitor/skill_evidence。原件：`experiments/colab-twin/output/workspace-x-left-refinement-20261024/kaggle-v1/`，含root-readback.json与独立读回。无碰撞、安全停机或算术错误，不等于任务完成。

下一单变量依据：同固定左down姿态三开度的只读拆分显示，46,869个方向构造／去重warm约28.3–28.5ms，native约4.5ms，实际270方向即找到证书。尝试同checker/pair仅复用方向建议，每帧重新完整投影；失败回完整方向搜索，错误仍拒绝。不得复用gap／valid／阶段认证或跨worker共享；默认补证保持关闭。组件原件为同output的 `readonly-component-timing.json`，不将本机与云wall串成提速。

## 左侧第二候选：只复用方向建议

`MeshBoxAxes` 的 `reuse_direction_hints` 诊断默认False；只在显式补证执行器中启用。每个同checker/native/model的ordered pair仅保存局部方向；新姿态按当前mesh旋转重建世界方向，再调用原NativeSupport完整顶点区间门。提示无证回原完整搜索；算术／ABI错误仍拒绝。只有全帧全部pairs通过，才更新提示。不保存距离／valid／阶段认证，也不跨worker/model共享。

根复放原参考2＋下降74＋闭爪244＋抬升74，以及v1实际1128行q6，共1522姿态。原版checker与helper均从26a0a1d读取，三对交替B/C、C/B、B/C，每对全部原返回结果逐字段完全相同；408次缺证整帧全部重新认证，候选406次单方向成功＋2次完整方向搜索，无错误或拒绝。局部wall分别14.398→.868s、14.819→.857s、14.523→.873s；CPU同向，原扫描点数不变。结果为组件复放收益，不能推算整程提速或50Hz。

一次早期筛选只载入旧helper却套新checker，缺少hint_stats导致适配异常，已标无效并单独保留 `hint-local-screen-invalid-reference.json`；未用于上述三对结论。有效原件 `hint-local-screen.json`，私有复跑入口 `~/.cache/ros2-factory/codebuddy-so101-20261021/round111-x-left-refinement/local_screen.py`。固定新源码后再用同profile原物理验证；v1超时不删除、不改判，不放宽原120s。

最终定点核验：hint单方向返回须evaluations=1、成功index=0，miss＋full真实计2次native调用。相关241项检查通过；提示负gap/NaN后全回退、坏ABI/FENV不救回、owner隔离与所有pairs失败不发布均覆盖。统计/ABI小修后的1522姿态再验全部返回逐字段一致，原16.289→候选1.010s、408/408整帧重新认证，原件 `hint-final-readback.json`。原默认与Carry在途代码未纳入本候选。

## 左侧两放置工位：原物理通过

固定源码 `46f5ba590bec2fe4c32542d69f6898f5360c1cae`。Kaggle同kernel v2先串行原左、提示候选、中心；v3在同源码独立验证已有第二放置工位(.20,.20)m。原红盘(.24,−.13)m不移动，取料始终(.22,−.13)m；原60mm高位／.5rad开爪、1mm、全部285对、244点扫掠、90sim／120wall及裁判保持。默认不开启补证，网页准入未变。

| version / case / UUID | 原裁决 | sim s | episode wall s | process wall / CPU s |
| --- | --- | ---: | ---: | ---: |
| v2 left_original_axes / fbb037d9-280f-4ffc-9967-81f3ceca55c7 | fail：grasp_leg_collision | 0 | 2.989 | 3.897 / 5.422 |
| v2 left_refined_axes / a3adbf9c-05c0-400b-885b-c282ca15f87f | pass | 74.10 | 96.873 | 98.038 / 107.612 |
| v2 center_regression / 476fc756-73d0-4afc-83b3-462558ed35b3 | pass | 76.64 | 49.698 | 50.801 / 60.927 |
| v3 left_refined_axes_secondary / 3c482379-89ab-4e22-8099-8ec26e6915bc | pass | 76.84 | 99.990 | 101.107 / 111.514 |

左侧主／第二工位分别真实抬升40.960／40.875mm、持物29.72／32.08s、静稳7.54／7.50s。原释放审计通过，66.742／69.520s脱离，XY漂移.214669／.169735mm、脱离后峰值力0；回位最大q6误差.102544／.101346mrad，最终速度9.44e−8／7.64e−8rad/s。无碰撞／安全停机，所有已运行行finite/arm_valid，自由物体、weld0/mocap0不变。

两次planned／measured闭爪各244点通过；主控和实测保守检查均走同一显式开关，批量桥未绕过Python补证。两次实测checker各384次整帧补证全部成功、error0：382次提示＋2次完整搜索，全部是当前p/R下的原native完整顶点重投影。未归档逐调用ABI轨迹；计数／源码和物理原件分别作为对应证据，不称连续CCD。原左初始化拒绝和v1墙钟超时完整保留。

两例transport／separation均consumed／owned_ack／joined，cleanup_unconfirmed=false，无遗留worker。第二工位分离路线沿原 `vertical_ik_limit_after_clearance` 回退，在25.615mm已认证高度接原回位；下一28.462mm IK残差.001365仍拒绝，未改95°限位、原阈值或删回退。录像实际ffprobe为464/464与481/481帧。

| 左侧成功例 | 初次OMPL / 含后处理 s | transport / separation worker wall s | 完整拍数 | P95 / P99 / max ms | >20ms |
| --- | ---: | ---: | ---: | --- | ---: |
| 主放置工位 | .141553 / .295674 | 1.974707 / 1.233394 | 3705 | 36.279 / 152.306 / 641.217 | 701 |
| 第二放置工位 | .173686 / .372213 | 2.512371 / 1.595698 | 3842 | 35.724 / 153.213 / 634.892 | 722 |

中心回归3832拍，P95=14.786ms、max45.634ms、100拍>20ms；479/479实帧、抓放／释放／脱离／回位通过。**本轮不是整程提速A/B或50Hz通过。** 不能用v1失败前缀wall与v2完整成功相减，或把不同云VM／放置目标的秒数累加。主工位close与lift分别251／143慢拍，controller独占累计19.534／5.505s；这只定位下一步应测的阶段，尚未定位内部剩余算子。

根与独立reader分别从原件重放原monitor／skill_evidence，并核固定场景、初态、RGB估计、源码、全扫、释放和清理。v2 batch=`d1ff1b6d-4fb2-4284-b824-0056668e40ab`，v3 batch=`b6967709-1488-4899-9446-ab6a7eb37db3`；原件在 `experiments/colab-twin/output/workspace-x-left-refinement-20261024/kaggle-v{2,3}/`，各含root／independent-readback.json。

已验证入口（在现有EGL／native依赖环境中运行，仍是开发case）：

```bash
cd /home/muqiao/dev/ros2/_delivery/so101-colab-20261001/experiments/colab-twin
/home/muqiao/.cache/so101-colab/planning-venv/bin/python run_workspace_case.py \
  --profile scenarios/workspace-x-left-refinement-m1a.json \
  --case left_refined_axes --output-dir output/left-refined-replay
```

第二工位选择 `left_refined_axes_secondary`；原版对照 `left_original_axes`，中心回归 `center_regression`。云端沿私有round111原构建器固定上述SHA，原runner／probe逐字相同。

**固定红盘X−20mm与X+20mm均已在两个已有放置工位完成原物理抓放。** 这是显式开发能力，不是整个±20mm连续区域、扰动20＋20、网页新默认或50Hz认证。连续包络、六技能同世界恢复与卸货仍依原计划推进；Carry在途两仓改动独立保留。
