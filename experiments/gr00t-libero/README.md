# GR00T N1.7 / LIBERO 接入

这条实验先验证 LIBERO 的环境，再接官方 GR00T 策略。LIBERO 使用 Franka Panda；本实验不代表 SO101 已完成策略迁移。源码、依赖、模型、配置、图像和运行报告都放在被 Git 排除的 `output/`。

2026-10-01 本机已验证 CPU environment-only：逐文件核验 1116 个源码/资产文件，Mesa llvmpipe 软件渲染，10 步推进 0.5 秒，两路图像正常；任务成功为 false，GR00T 策略未运行。未知任务、零步参数和缺失 GPU checkout 负例均拒绝，5 项报告/完整性边界测试通过。

[upstream.json](upstream.json) 固定 GR00T commit、它的 LIBERO submodule commit、LIBERO 10 发布 checkpoint revision 和最小下载文件。推理权重约 **6.915 GB**，不下载 optimizer、训练状态或演示训练集。Cosmos backbone 需要另行下载和 Hugging Face 访问权限。

## CPU 环境验证

在本目录执行，需 Python 3.12、uv、curl。Ubuntu 软件渲染需要 OSMesa；下面的可选参数仅下载并解压运行库，不安装系统包。它仍需要本机兼容的 Mesa/LLVM 依赖。

```bash
python3 setup_cpu.py --download-osmesa
LD_LIBRARY_PATH="$PWD/output/osmesa/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
  timeout 180s output/cpu-venv/bin/python smoke_environment.py
```

已具备系统 OSMesa 时可省略 `--download-osmesa` 和 `LD_LIBRARY_PATH`。脚本使用官方 `OffScreenRenderEnv`，执行 seeded reset → 10 个 no-op 物理步 → 双相机 256×256 RGB → 官方 `check_success()`，保存四张 PNG 和机器报告 `output/environment-smoke/report.json`。配置通过独立的 `LIBERO_CONFIG_PATH` 创建，避免修改 `~/.libero`。

`report.json` 必须检查三个不同字段：

- `environment_completed=true`：环境、物理步进、有限状态和两路非恒定图像检查完成。
- `task_success`：最终状态的官方任务成功判定；no-op 通常为 false。
- `gr00t_rollout_completed=false`：本命令始终不运行模型。随机小动作也只是环境验证。

该 reset 使用随机种子，没有载入 benchmark 固定初始状态；不作为正式成功率评测。可选 `--action random` 只生成有界小动作。负例入口为 `--task DOES_NOT_EXIST`（报告失败、退出 1）和 `--steps 0`（参数拒绝、退出 2）。

## GPU 策略入口

需要现成 CUDA GPU（默认 FA2/BF16 要求 Ampere 或更新架构，至少 16 GB 显存；T4 不满足默认栈）。此模块不分配 Colab runtime、不购买额度、不训练。

用户先在 [Cosmos-Reason2-2B 模型页](https://huggingface.co/nvidia/Cosmos-Reason2-2B) 登录、接受条件并取得访问权限，再通过 Hugging Face 官方 CLI 登录。不要把 token 放进仓库、命令行参数或报告。

在兼容 GPU 上准备独立官方 checkout；跳过 demo LFS 数据：

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone --no-checkout https://github.com/NVIDIA/Isaac-GR00T output/upstream/Isaac-GR00T
GIT_LFS_SKIP_SMUDGE=1 git -C output/upstream/Isaac-GR00T checkout 51d4c89f72fda44cbf77285c6a8114b52676b8a1
GIT_LFS_SKIP_SMUDGE=1 git -C output/upstream/Isaac-GR00T submodule update --init external_dependencies/LIBERO
```

按 [官方安装说明](https://github.com/NVIDIA/Isaac-GR00T/tree/51d4c89f72fda44cbf77285c6a8114b52676b8a1#installation) 在该 checkout 执行 `uv sync --python 3.12`，安装 EGL、FFmpeg 4–7 等系统依赖。官方 `gr00t/eval/sim/LIBERO/setup_libero.sh` 包含删除 `~/.libero` 的命令；**只在没有既有用户配置的临时 Colab VM 中执行它**，本机应复用已准备好的官方 client 环境。单独设置 `LIBERO_CONFIG_PATH` 无法防止那条删除命令。我们的 CPU setup 不调用该脚本。

从本实验目录执行：

```bash
python3 preflight.py --gr00t-root output/upstream/Isaac-GR00T
python3 run_rollout.py --gr00t-root output/upstream/Isaac-GR00T --download-models
```

`preflight` 不访问或输出凭据，不检查账户 GPU 额度；退出 2 表示设备或 checkout 前置条件未满足。设备检查通过也不代表模型权限已取得。

`run_rollout` 先检查固定且无 tracked 修改的 checkout、LIBERO submodule 和 GPU，再通过官方 `hf download` 下载 allowlist。backbone 下载到独立 HF Hub cache；其 `main` 必须解析成锁定的已观察 revision，否则停止。之后 offline 启动官方 server/client，仅监听 localhost、1 环境、1 episode、种子 0、最多 720 步，并回收视频和日志。模型缓存在 `output/gr00t-models/` 共享复用；每轮报告、日志和视频独立放在 `output/rollout/<UUID>/`，视频附 SHA256，避免混入上一轮产物。

GPU 每轮 `report.json` 中 `gr00t_rollout_completed=true` 只表示官方策略闭环执行结束；**任务是否完成必须另看 `task_success`**。退出 0 可以对应 `task_success=false`。退出 1 为设置/执行失败，退出 2 为已知前置条件阻碍。GPU 路径目前未完成真实策略验证，不能据此宣称任务通过。

CPU setup 从固定源码 tar 生成逐文件 SHA256 manifest；复用和 smoke 都核验源码、模型资产、文件增删（仅排除生成的 pycache/egg-info），失败时停止。必要检查：`python3 -m unittest discover -s . -p 'test_*.py'`。实际环境验证报告和图像留在本机 ignored output，不提交运行时日志或模型。

来源：[官方 LIBERO 接入](https://github.com/NVIDIA/Isaac-GR00T/blob/51d4c89f72fda44cbf77285c6a8114b52676b8a1/examples/LIBERO/README.md)、[发布权重](https://huggingface.co/nvidia/GR00T-N1.7-LIBERO/tree/2ea293aa20ba7cf5bbf3ba17a5fbcb1a01cbfe21/libero_10)、[FA2 架构支持](https://github.com/Dao-AILab/flash-attention#nvidia-cuda-support)。
