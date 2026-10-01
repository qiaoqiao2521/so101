# GR00T N1.7 / LIBERO 接入

这条实验先验证 LIBERO 的环境，再接官方 GR00T 策略。LIBERO 使用 Franka Panda；本实验不代表 SO101 已完成策略迁移。源码、依赖、模型、配置、图像和运行报告都放在被 Git 排除的 `output/`。

2026-10-01 本机已验证 CPU environment-only：逐文件核验 1116 个源码/资产文件，Mesa llvmpipe 软件渲染，10 步推进 0.5 秒，两路图像正常；任务成功为 false，GR00T 策略未运行。未知任务、零步参数和缺失 GPU checkout 负例均拒绝，5 项报告/完整性边界测试通过。

[upstream.json](upstream.json) 固定 GR00T commit、它的 LIBERO submodule commit、LIBERO 10 发布 checkpoint revision 和最小下载文件。推理权重约 **6.915 GB**，不下载 optimizer、训练状态或演示训练集。Cosmos backbone 需要另行下载和 Hugging Face 访问权限。2026-10-01 已完成官方 HF CLI 授权，并实际下载 gated `config.json`（1505 bytes，SHA256 `bec4b3d446efa05807365c9e1cec03ac590836879d02f3a6da879971154bdd3b`）；这证明该文件访问可用，完整权重下载、模型加载与策略任务结果仍需各自验证。

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

需要兼容 CUDA GPU（默认 FA2/BF16 要求 Ampere 或更新架构，至少 16 GB 显存；T4 不满足默认栈）。`preflight.py` 和 `run_rollout.py` 使用现成 GPU；下面的 `run_colab.py` 按已获授权的小样本额度申请临时 L4 并负责释放。实验不训练或购买额度。

当前官方 HF CLI 2.0 OAuth device login 已完成，Cosmos gated 配置访问已验证，无需重复登录。其他环境需先在 [Cosmos-Reason2-2B 模型页](https://huggingface.co/nvidia/Cosmos-Reason2-2B) 取得权限，并在对应工具环境通过官方 `hf auth login` 登录。不要把 token 放进仓库、命令行参数或报告。

### Colab L4 单回合

`run_colab.py` 使用已有 Colab CLI **0.6.0** 的解释器，默认路径为 `~/.local/share/uv/tools/google-colab-cli/bin/python`；可用 `--colab-python` 指定对应环境。`colab_safe_cli.py` 固定检查该版本，阻止原 CLI 的请求日志、cell history 与背景更新写入。入口应由安装 `huggingface_hub` 且已完成官方授权的 Python 执行。

当前已验证的本机 HF 工具位于临时目录 `/tmp/hf-cli-20261001/`。在本实验目录启动：

```bash
HF_PYTHON=/tmp/hf-cli-20261001/bin/python
"$HF_PYTHON" run_colab.py --gpu-minutes 45
```

临时工具消失后，可在 ignored output 中重建工具环境，复用官方 CLI 的既有登录：

```bash
uv venv --python 3.12 output/hf-tools
uv pip install --python output/hf-tools/bin/python huggingface_hub==2.0.0
output/hf-tools/bin/python run_colab.py --gpu-minutes 45
```

可移植使用时，也可把 `HF_PYTHON` 配置为已安装 `huggingface_hub` 的环境 Python。`--gpu-minutes` 支持 **1..45**，是含分配、上传、安装、下载和单回合执行的总预算；释放步骤另外最多等待 120 秒。这是已有额度授权的一个 L4 小样本实验：**1 环境、1 episode、最多 720 步、每次执行 8 个预测动作**，没有训练或批量评测。

bootstrap 在全新 `/content/gr00t-colab` 工作目录中使用固定 GR00T / LIBERO 源码；clone、checkout、submodule 都启用 `GIT_LFS_SKIP_SMUDGE=1`。uv 固定 0.11.15，安装到临时工具目录并调用 `bootstrap-tools/bin/uv`，避开 Colab 自定义 Python 的 `ensurepip`；官方模型环境仍执行 `uv sync --frozen --python 3.12`，LIBERO client 使用官方独立环境。先记录 OS/Python/磁盘，再检查 GPU、EGL、FFmpeg 4–7 与 preflight。官方 LIBERO setup 会删除 `~/.libero`，因此存在既有配置的 VM 会被拒绝。

本机输出位于 `output/colab/<UUID>/`；远端仅打包阶段报告、脱敏日志和本轮视频，产物清单必须完整覆盖 ZIP 结果文件，下载后核对精确文件集合、大小与 SHA256；缺失清单或额外文件会被拒绝。HF 凭据经权限 0600 的临时文件传递，消费后删除，仅子进程环境使用；不进入参数、源码、报告或 ZIP。会话身份信息留在私有输出中，禁止提交、分享整个 output 或原始请求日志。释放失败时保留私有会话状态供接续；实际 `unassign` 返回成功才记为 `runtime_released=true`，`stop` 命令退出 0 本身不构成释放证据。

`seed=0` 仅用于官方 client 的随机 reset；没有加载 benchmark 固定初始状态，也没有固定模型 server RNG。单回合不能证明官方 benchmark 成功率或跨运行确定性。必须分别检查本机 delivery 的 `runtime_released`、bootstrap 的阶段状态、policy report 的 `gr00t_rollout_completed` 和终态 `task_success`，并查看本轮视频。`completed` 还要求本轮视频非空、哈希一致且 FFmpeg 全量解码通过；这项验收规则不等于真实 GPU 回合已通过。

### 当前云端运行证据

- 第二次尝试实际分配 L4，显存 **23034 MiB**，apt/EGL/FFmpeg 阶段通过；bootstrap 因 `ensurepip` 失败停止，策略未运行。该会话已实际 `unassign` 成功释放。原始本机报告 SHA256：`76569625e9063f6e1d40da7b830c1d40712c91f5a72e91d72707f3db69ffef1f`。
- 随后把 uv bootstrap 改为临时目录 pip target 安装，二进制路径 `bin/uv` 已用实际安装核实。第四次尝试随后因 Colab 通信超时结束（本机 delivery `status=failed`、`error_type=TimeoutExpired`），实际 `unassign` 成功，`runtime_released=true`。没有回收到 bootstrap 报告、视频或 policy 结果，远端阶段未知；本机 `gr00t_rollout_completed=false`、`task_success=null`，不能宣称 uv 修复已在 GPU 初始化流程中通过。原始本机报告 SHA256：`fa51fd267b209f21b5564b5a0f4b05070452bc1c0ba64e8a8e06170cd14899b2`。
- 当前结论：**HF 权限实测成功，策略闭环未完成，Colab 通信超时，运行时已释放**。本轮没有可核验的远端终止阶段、episode 长度或视频；任务成功为未知。最终只读查询确认 `active_assignments=0`。root 已停止继续分配，并补充超时诊断与分配 POST 丢响应时按精确 notebook hash 恢复会话的路径；该恢复路径仅有离线故障注入边界检查，尚无 live 验证。最短接续仍为上述一次 L4 单回合命令，条件是 Colab 通信稳定；无需等待 HF 审批。

### 现成 GPU 的手动入口

在兼容 GPU 上准备独立官方 checkout；跳过 demo LFS 数据：

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone --no-checkout https://github.com/NVIDIA/Isaac-GR00T output/upstream/Isaac-GR00T
GIT_LFS_SKIP_SMUDGE=1 git -C output/upstream/Isaac-GR00T checkout 51d4c89f72fda44cbf77285c6a8114b52676b8a1
GIT_LFS_SKIP_SMUDGE=1 git -C output/upstream/Isaac-GR00T submodule update --init external_dependencies/LIBERO
```

按 [官方安装说明](https://github.com/NVIDIA/Isaac-GR00T/tree/51d4c89f72fda44cbf77285c6a8114b52676b8a1#installation) 在该 checkout 执行 `uv sync --frozen --python 3.12`，安装 EGL、FFmpeg 4–7 等系统依赖。官方 `gr00t/eval/sim/LIBERO/setup_libero.sh` 包含删除 `~/.libero` 的命令；**只在没有既有用户配置的临时 Colab VM 中执行它**，本机应复用已准备好的官方 client 环境。单独设置 `LIBERO_CONFIG_PATH` 无法防止那条删除命令。我们的 CPU setup 不调用该脚本。

从本实验目录执行：

```bash
python3 preflight.py --gr00t-root output/upstream/Isaac-GR00T
python3 run_rollout.py --gr00t-root output/upstream/Isaac-GR00T --download-models
```

`preflight` 不访问或输出凭据，不检查账户 GPU 额度；退出 2 表示设备或 checkout 前置条件未满足。设备检查通过也不代表模型权限已取得。

`run_rollout` 先检查固定且无 tracked 修改的 checkout、LIBERO submodule 和 GPU，再通过官方 `hf download` 下载 allowlist。backbone 下载到独立 HF Hub cache；其 `main` 必须解析成锁定的已观察 revision，否则停止。之后 offline 启动官方 server/client，仅监听 localhost、1 环境、1 episode、种子 0、最多 720 步，并回收视频和日志。模型缓存在 `output/gr00t-models/` 共享复用；每轮报告、日志和视频独立放在 `output/rollout/<UUID>/`，视频附 SHA256，避免混入上一轮产物。

GPU 每轮 `report.json` 中 `gr00t_rollout_completed=true` 只表示官方策略闭环执行结束；**任务是否完成必须另看 `task_success`**。退出 0 可以对应 `task_success=false`。退出 1 为设置/执行失败，退出 2 为已知前置条件阻碍。GPU 路径目前未完成真实策略验证，不能据此宣称任务通过。

Colab wrapper 的 portable `test_colab.py` 只做离线生命周期、日志、临时凭据和产物边界检查；19 项通过，加上原有 5 项报告/源码检查，共 24 项。未安装可选 Colab SDK 时，仅真实 StateStore 检查跳过。它不分配 GPU，也不代表真实回合通过。

CPU setup 从固定源码 tar 生成逐文件 SHA256 manifest；复用和 smoke 都核验源码、模型资产、文件增删（仅排除生成的 pycache/egg-info），失败时停止。必要检查：`python3 -m unittest discover -s . -p 'test_*.py'`。实际环境验证报告和图像留在本机 ignored output，不提交运行时日志或模型。

来源：[官方 LIBERO 接入](https://github.com/NVIDIA/Isaac-GR00T/blob/51d4c89f72fda44cbf77285c6a8114b52676b8a1/examples/LIBERO/README.md)、[发布权重](https://huggingface.co/nvidia/GR00T-N1.7-LIBERO/tree/2ea293aa20ba7cf5bbf3ba17a5fbcb1a01cbfe21/libero_10)、[FA2 架构支持](https://github.com/Dao-AILab/flash-attention#nvidia-cuda-support)。
