# 现成模型驱动机械臂仿真

目标：选择一个任务，观看下载的 SmolVLA 策略驱动 Sawyer 机械臂，再换任务或初态复跑。不训练模型，不访问实体机械臂。

## 运行

在仓库根目录运行。首次安装需要 `uv`、官方 `hf` CLI、Linux 和 NVIDIA GPU。

```bash
bash experiments/pretrained-demo/setup.sh
bash experiments/pretrained-demo/run.sh push
bash experiments/pretrained-demo/run.sh pick-place
bash experiments/pretrained-demo/run.sh bin-picking
```

第二个参数改变随机种子；第三个参数指定每次预测后执行多少步。演示默认 10，更频繁地根据新画面调整动作。权重原配置是 50，本次该设置抓放失败，原始结果保留。

```bash
bash experiments/pretrained-demo/run.sh pick-place 1 10
```

完整下载并成功运行过后，可以离线复跑：

```bash
HF_HUB_OFFLINE=1 bash experiments/pretrained-demo/run.sh bin-picking 0
```

每次运行在 `output/` 新建独立目录。查看 `eval_info.json` 的任务成功判定和 `videos/` 下的 MP4。进程退出成功仅代表评估完成，不代表抓放成功。输出、日志和权重不提交 Git。

## 选择依据与边界

- [官方权重](https://huggingface.co/lerobot/smolvla_metaworld/tree/cd6778d2cfa724c1bf5fc637490548e54d81dc4c)：约 450M 参数、907MB 文件，Apache-2.0；固定 revision。
- [LeRobot v0.6.1 官方 CI](https://github.com/huggingface/lerobot/blob/v0.6.1/.github/workflows/benchmark_tests.yml)：采用其中 MetaWorld 单回合命令，保留相机重命名及两个空相机配置。
- [任务表](https://github.com/huggingface/lerobot/blob/v0.6.1/src/lerobot/envs/metaworld_config.json)：推物、抓放、箱间搬运有原生任务定义；指令由官方环境传给策略，不等于任意自然语言都能可靠执行。
- 权重训练配置指向 MT50 数据。逐任务效果以本机实际评估为准，不把官方 smoke test 当作成功率保证。
- 使用独立缓存环境，不改变既有 SO101 环境；Sawyer 仿真演示不代表 SO101 已适配。
- 不使用先前自训 ACT、IK/OMPL 专家或手工动作替代此模型输出。

## 本次环境来源

实际安装：LeRobot 0.6.1、MetaWorld 3.0.0、MuJoCo 3.15.0、Gymnasium 1.4.0、Torch 2.7.1+cu126、Transformers 5.5.4。独立环境的 CUDA、环境 reset/step 和 EGL 渲染已验证。

策略 revision 固定；官方代码还通过模型 ID 加载视觉语言基座和 tokenizer。本次观察到 [SmolVLM2 基座](https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct/tree/7b375e1b73b11138ff12fe22c8f2822d8fe03467) revision `7b375e1b73b11138ff12fe22c8f2822d8fe03467`，因此不能称整个依赖链都已锁定。基座权重约 2.03GB；907MB 仅指任务策略文件。

## 2026-10-10 本机实际结果

全部使用 RTX 3050 Laptop 4GB、同一份公开权重，无新增训练、Colab 分配或实体操作。下表每行只有一回合，种子均为 0，不代表统计成功率。评测耗时不含安装、下载与模型加载。

| 任务 | 每次执行步数 | 官方任务判定 | 评测耗时 |
| --- | ---: | --- | ---: |
| 推物 | 50 | 成功 | 4.85 秒 |
| 推物（最终默认入口） | 10 | 成功 | 4.45 秒 |
| 抓取移到目标 | 50 | 失败 | 12.30 秒 |
| 抓取移到目标 | 10 | 成功 | 4.47 秒 |
| 箱间搬运到目标 | 10 | 成功 | 6.24 秒 |

原始结果分别位于 `output/push-seed0-steps50-apvsxb/`、`output/pick-place-seed0-steps50-5cGaMJ/`、`output/pick-place-seed0-steps10-s5nbPj/`、`output/bin-picking-seed0-steps10-2a52AP/`、`output/push-seed0-steps10-KBRUt6/`。每个目录保留 `eval_info.json`、原视频、参数和日志。抓放与箱间搬运另有明确标注的 8 倍慢放预览；它们不表示实时速度。

成功范围必须按官方判据解释：MetaWorld 3.0.0 的 `pick-place` 检查物体到目标距离 ≤7cm，`bin-picking` 检查 ≤5cm；两者不要求松爪后静稳。此次未验证释放落定、SO101 迁移或生产稳定性。官方包装器在成功时立即 reset，视频末帧可能出现重置跳变。

首次加载有一条等待基座下载时主动中断的启动记录，未进入模型控制，不计作任务回合。下载恢复后，基座完整文件 SHA-256 核对通过；所有正式回合由官方策略入口执行。
