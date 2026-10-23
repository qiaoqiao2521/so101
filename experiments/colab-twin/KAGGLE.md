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
