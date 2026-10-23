# Kaggle 原物理对照

复用原 `evaluate_station.py`、原串行 runner 和原安全判据。Kaggle 负责环境与计算，候选不接触实体机械臂。原每回合 90 秒仿真、120 秒墙钟限制继续包含初始化、物理循环和视频完成。

## 已验证的入口

私有任务：[SO101 Midpoint Physical AB 20261024](https://www.kaggle.com/code/muqiaoqiao/so101-midpoint-physical-ab-20261024)。使用现有 Kaggle 账号 `muqiaoqiao`；凭据保留本机，云端从公开 GitHub 仓库拉取源码。

- 版本 6：名义工位，原版→中点搜索候选。
- 版本 7：已有 200/200 放置工位，候选→原版。
- 版本 8：原方块 X 横移 5mm，候选→原版；仍在现有 ±10mm 输入范围内。

版本 7/8 会获取并检出 `116b090fe7b157cf0f83c2dab10a7365320a48a6`，记录实际来源。普通 Git 修订选择不限制用户编辑配置。两侧使用同一检出，评测期间不修改或提交源码。

用已登录的官方 CLI 回收版本 8 的完整启动脚本和元数据，再提交即可复跑该 5mm 对照：

```bash
kaggle kernels pull muqiaoqiao/so101-midpoint-physical-ab-20261024/8 \
  --metadata -p /tmp/so101-kaggle-replay
kaggle kernels push -p /tmp/so101-kaggle-replay --accelerator NvidiaTeslaT4
```

本机 CLI 独立安装于 `/home/muqiao/.local/share/ros2-factory/kaggle-cli/bin/kaggle`。本次访问使用命令级 `HTTPS_PROXY=http://127.0.0.1:3067`、`HTTP_PROXY` 同值；不修改全局代理或其他仿真环境。

结果用 `kaggle kernels output <owner/slug/version> -p <本地目录>` 回收。`so101-evidence.tgz` 包含原始报告、视频、完整周期计时、来源、主机观察和串行进程 wall/CPU。平台 COMPLETE 或 runner 退出 0 均不替代每个回合的原 verdict。

## 当前云镜像的实际适配

CLI 2.2.5；实际 Python 3.13.15、MuJoCo 3.15.0、NumPy 2.4.6、SciPy 1.17.1。完整依赖清单随每个云端产物保存。它是新环境，不能与本地绝对耗时拼成累计提速。

首次原生 venv 创建失败；随后 astral.sh 下载返回 403。有效路径从官方 PyPI 获取 uv 0.11.15 wheel，用 uv 创建隔离环境，不依赖底座 ensurepip。

分配两张 T4 后，实际 EGL 最初仍为 Mesa llvmpipe。只存在 Mesa vendor JSON。版本 3 两回合完成物理动作，但视频分别只有 148/474、158/475 帧，均原 wall_time_limit；失败原样保留。

在临时目录解包 NVIDIA 官方仓库中与实际驱动匹配的 `libnvidia-gl-580`、`libnvidia-gpucomp-580` 580.178.04-1ubuntu1，指定私有 EGL vendor JSON 和该目录的 LD_LIBRARY_PATH 后，实际 renderer 为 Tesla T4。没有替换宿主内核驱动。640×480 同模型热身后单帧约 118ms→1ms；这属于环境适配收益，不是候选算法收益。

新驱动/新云镜像须重新观察实际 renderer 和原评测。`nvidia-smi` 可见 GPU 不证明 OpenGL/EGL 已使用 GPU。官方说明见 [NVIDIA driver capabilities](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/docker-specialized.html#driver-capabilities)。

## 本轮决定

修复环境后三组原物理对照 6/6 通过，244 点计划/实测闭爪、原碰撞检查、自由物体、释放、脱离、回位、完整录像和 worker 清理均通过。

| 输入 | 原版→候选进程 wall / CPU（秒） | 原版→候选搜索（秒） |
| --- | --- | --- |
| 名义工位 | 59.759 / 69.506 → 54.987 / 64.746 | 4.016 → 1.331 |
| 200/200 放置工位，反序执行 | 55.744 / 65.532 → 55.201 / 64.748 | 3.611 → 1.101 |
| 方块 X +5mm，反序执行 | 51.424 / 60.169 → 51.585 / 60.568 | 3.506 → 1.157 |

三对最终路径各自逐位相同，最终全路径检查保留；偏移组最终检查为 505 状态，前两组为 513。搜索尝试 77→10、77→10、76→10。候选没有稳定的完整任务收益，因此默认仍是 `float_first_context.py`，中点搜索继续显式可选，不晋级。完整 50Hz 未通过。

原件与独立读回位于忽略目录 `output/kaggle-midpoint-factory-20261024/`；结论与接续见[原计划](../../plans/factory-loading-20261021/progress.md)。启动源码与候选来源另保留在本机既有工厂 cache 的 `round70-kaggle-midpoint/`，云端不可变版本是 cache 丢失后的恢复入口。


## 后续预编译打包器对照

[完整组件任务](https://www.kaggle.com/code/muqiaoqiao/so101-float-packer-component-20261024)版本2实际使用source9c585cd生产helper，三对准入；[原物理任务](https://www.kaggle.com/code/muqiaoqiao/so101-prebound-physical-ab-20261024)版本1为名义父→子、版本2为200/200子→父。4/4原物理通过。

按父→子process wall64.356→62.556、60.959→62.650s；两站同量主循环CPU均未下降，因此不晋级默认。首运行者在原episode计时窗外始终约多1.25s，须进一步定位启动/收尾，不能把它当算法提速。原件和独立读回在output/prebound-float-factory-20261024；下一轮只观察原默认的回调IO/GC与冷/热导入，尚未修改这些实现。


## 回调与视觉接续（2026-10-24）

- [原默认归因](https://www.kaggle.com/code/muqiaoqiao/so101-callback-attribution-20261024) v1：原抓放pass，IO/GC/冷热导入只读记录；131ms回调未复现，未改GC或发布器。
- [视觉组件拆分](https://www.kaggle.com/code/muqiaoqiao/so101-perception-components-20261024) v1：实际640×480静态图，分别量渲染和定位；不当整拍验收。
- [OpenCV掩码组件](https://www.kaggle.com/code/muqiaoqiao/so101-opencv-mask-component-20261024) v1：全RGB穷举同值、原19项视觉检查及完整组件三对准入。
- [掩码原物理](https://www.kaggle.com/code/muqiaoqiao/so101-opencv-mask-physical-ab-20261024) v1名义父→子、v2已有200/200子→父，4/4原pass。采用私有明确实现替换；detector-implementation.json记录实际来源，不能把相同route-policy当完全相同实现。

source450e5e34两站定位合计各省约13ms，但process wall父→子56.899→55.672、59.184→60.791s，整程不一致，不晋级。默认/阈值/90sim120wall/244保持，完整50Hz未过。原件及独立读回见output/callback-attribution-20261024、perception-components-20261024、opencv-mask-factory-20261024。实际控制循环渲染约14.7ms/次，与静态探针不同；下一项记录控制进程GL及子区间，不凭本页旧预检推断。


## 实际渲染与GPU状态观察

[真实控制渲染归因](https://www.kaggle.com/code/muqiaoqiao/so101-live-render-attribution-20261024) v1的原默认抓放通过，控制context确认Tesla T4，场景更新约.044ms、渲染约14.563ms。14份MJB/状态/pose/RGB用于离线复放；两种复放均未逐像素等同，不宣称同输入加速。

[节奏与NVML只读观察](https://www.kaggle.com/code/muqiaoqiao/so101-paced-render-observation-20261024) v1中，连续模式也出现慢读回；P0/585MHz与P8/300MHz关联到约1.46/13.91ms读回，但未干预时钟，尚非因果结论。GPU设置未改，图像逐像素检查失败保留。当前不靠重复出图或修改物理判据追绿。下一项是本任务GPU原生时钟配置权限与可恢复短对照；平台拒绝时不提权。


## 权限拒绝、读回格式与异步相机

- [时钟权限](https://www.kaggle.com/code/muqiaoqiao/so101-clock-control-component-20261024) v1：GPU0锁频及finally恢复均rc4，平台拒绝；未成功施加时钟，不宣称恢复成功，不提权重试。
- [RGBA组件](https://www.kaggle.com/code/muqiaoqiao/so101-rgba-readback-component-20261024) v1：28次同draw像素等值，但完整组件三对均更慢，原screen reject，不发物理。
- [异步相机协议](https://www.kaggle.com/code/muqiaoqiao/so101-async-camera-protocol-20261024) v1：14帧实际EGL定位同值、capture timestamp保留、主状态不变、owned线程/context正常退出；不当50Hz或任务通过。
- [异步相机原物理](https://www.kaggle.com/code/muqiaoqiao/so101-async-camera-physical-ab-20261024) v1名义原版→候选、v2已有200/200候选→原版，4/4原pass。真实实现外围替换通过camera-implementation.json与generated episode源码记录，不能只看同route-policy。

source dfb9fc32，两站视觉live慢拍13→0、13→2，capture到送达20–60ms，原1s TTL与无效结果拒绝保持。完整process wall原版→候选59.740→56.981、60.837→61.781s，CPU69.671→66.754、71.404→72.478s，整程收益不一致；完整慢拍仍103/147，不晋级默认，不宣称完整50Hz。

证据分别在output/clock-control-component-20261024、rgba-readback-factory-20261024、async-perception-factory-20261024；最后一项的independent-physical-inventory.json保留所有原物理与时间戳/清理核验。私有工厂cache round79-async-perception保存来源、协议、完整两站wrapper与read_camera.py。恢复云端来源用现有CLI：

```bash
kaggle kernels pull muqiaoqiao/so101-async-camera-physical-ab-20261024/1 -p RESTORE_PRIMARY --metadata
kaggle kernels pull muqiaoqiao/so101-async-camera-physical-ab-20261024/2 -p RESTORE_CROSS --metadata
```

复跑保持新版本私有、原90sim120wall/244与scorer，不将跨主机绝对秒数相加，不修改default。下一项只测1ms线程切换间隔的固定工作量组件，尚未有物理结论。


## 1ms线程切换间隔（F2bo，淘汰）

[固定guard组件](https://www.kaggle.com/code/muqiaoqiao/so101-switch-interval-component-20261024) v1在测量前缺指定旧run失败；v2先记录mounted-inputs.json，采用已验收cross原版5635508a，六例共用96条原检查输入、原并行运输planner。数值/路径/清理/恢复保持，三对guard窗口省29–65ms，但慢查询没有一致减少；原screen仅准入原物理。

[1ms原物理](https://www.kaggle.com/code/muqiaoqiao/so101-switch-interval-physical-ab-20261024) v1名义原版→候选、v2已有200/200候选→原版，source281b049，4/4原pass。原同步相机/route/评分/90sim120wall/244保持；私有switch-implementation.json记录实际生效和退出恢复。原版→候选process wall58.906→56.724、70.954→72.054s，CPU同样第二站回退，慢拍126→115、221→276。淘汰，不改默认、不扫更多间隔，完整50Hz未过。

CLI2.2.5源码pull/version有独立版本参数；kernel_sources的metadata回读只保存任务slug，本次实际挂载最新cross而非请求的旧名义输出。不要把两种接口混为固定版本输入。采用[官方metadata格式](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels_metadata.md)，并独立记录真实run/原裁决/来源；缺失旧回合保留失败，允许明确采用另一个已验收原版，并保持成对输入一致。

原件与独立库存：output/switch-interval-factory-20261024。复跑私有round80-switch-interval包含candidate.py、probe.py、physical_probe.py、read_switch.py和准确路径；下一项只读同guard的函数CPU/调用归因，不以profile时长作为性能A/B。


## guard归因（F2bp）

[固定guard调用归因](https://www.kaggle.com/code/muqiaoqiao/so101-hold-guard-cpu-profile-20261024) v1的原功能通过，但cProfile/thread_time的混线程计时无效，失败保留。v2使用标准库profile.Profile.runcall，只接主线程事件；同96个原guard及并行原planner数值/路径相同，时间/CPU记账/线程/恢复独立检查通过。仅归因，不把profile伪帧或插桩时间当基准。

原件output/guard-cpu-profile-20261024，来源私有round81。有效调用计数提示上下文递归/type判断很多；新私有round82先比较exact builtin快捷分派，保留原fallback和编码。38局部语义检查通过，尚未有组件收益或物理结论。
