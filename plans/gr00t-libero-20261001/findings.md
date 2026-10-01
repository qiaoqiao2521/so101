# Findings

## Executed environment evidence
Root independently reran the final CPU smoke after review fixes: source/asset manifest verified 1116 files, Mesa llvmpipe software renderer, seeded reset, 10 real MuJoCo physical steps / 0.5 seconds, two 256x256 RGB cameras. environment_completed=true, task_success=false, gr00t_rollout_completed=false. Five boundary tests passed (failed-task result semantics, empty/missing episode rejection, T4 rejection, changed and unexpected source files). Unknown task, zero steps and missing GPU checkout remained failures. No GPU, model or hardware call occurred.

Independent review fixes: LFS skip applies to checkout and submodule; model cache is shared but each GPU episode uses a UUID artifact directory with video SHA256; source reuse and smoke reject altered files against the pinned archive manifest.

- GR00T source: 51d4c89f72fda44cbf77285c6a8114b52676b8a1.
- Its LIBERO gitlink: 8f1084e3132a39270c3a13ebe37270a43ece2a01.
- Public policy checkpoint: nvidia/GR00T-N1.7-LIBERO at 2ea293aa20ba7cf5bbf3ba17a5fbcb1a01cbfe21. Inference files in libero_10 total approximately 6.915 GB; optimizer states are unnecessary.
- Mandatory Cosmos-Reason2-2B backbone is gated; observed revision 9ce19a195e423419c349abfc86fd07178b230561. Official page requires login and agreement to contact-information sharing and model conditions. The original CPU preflight only checked credential presence and had no configured credential. Subsequently, official HF CLI OAuth login succeeded and gated config access was actually verified (1505 bytes, SHA256 bec4b3d446efa05807365c9e1cec03ac590836879d02f3a6da879971154bdd3b). This is access evidence for that file, not full model download or inference acceptance.
- Default BF16/FlashAttention2 stack requires compatible Ampere or newer GPU. T4 is not supported by that default stack. Existing paid Colab small-sample use is authorized; no runtime allocated during gated preflight.
- Local nvidia-smi cannot contact the driver. Driver repair is outside this experiment.
- Official LIBERO setup script unconditionally removes ~/.libero. Independent CPU setup avoids it; official GPU setup belongs only in a temporary VM with no existing user config.
- Knowledge adopted from Wiki/自动化开发范式与智能体协作.md: code/test evidence is separate from actual task behavior and delivery. Apply this by recording environment, rollout and success as three separate fields.

Sources: [GR00T](https://github.com/NVIDIA/Isaac-GR00T/tree/51d4c89f72fda44cbf77285c6a8114b52676b8a1), [Cosmos access](https://huggingface.co/nvidia/Cosmos-Reason2-2B), [FlashAttention](https://github.com/Dao-AILab/flash-attention#nvidia-cuda-support).

## Bounded Colab integration and live attempt evidence

The new wrapper uses existing google-colab-cli 0.6.0 and an authenticated huggingface_hub Python. Allocation/session metadata is per-run and private. Safe CLI suppresses native HTTP exception output, file logging, cell history and background updates; keep-alive also uses the safe wrapper. Actual Client.unassign return is required for runtime_released=true. Offline portable lifecycle tests do not establish cloud release or policy acceptance.

Remote bootstrap pins source and checkpoint revisions, skips LFS for clone/checkout/submodule, installs uv 0.11.15 to a temporary pip target and invokes its verified bin/uv executable. Root/model and LIBERO client environments remain separate. Existing ~/.libero is refused before invoking the official setup. The result ZIP allowlists JSON/log/MP4 files and hashes them; model weights and credentials stay outside it.

Attempt 2 actually acquired L4 with 23034 MiB VRAM and passed apt/EGL/FFmpeg; Python ensurepip failed before any policy episode. Root confirmed the runtime was unassigned. After the isolated uv bootstrap repair, attempt 4 ended with local delivery status=failed / error_type=TimeoutExpired. Runtime release is verified by actual unassign. No bootstrap report, video or policy result was recovered; the remote failure phase and task success are unknown. The repaired uv installation has not passed a live GPU workflow. Root stopped further allocation to improve timeout diagnostics and allocation POST lost-response recovery. The current blocker is Colab communication, not pending HF model approval.

One environment, one episode, max 720 steps, execution horizon 8. Client seed 0 controls randomized reset; there is no benchmark fixed-init loading or model-server RNG seed. The Panda task neither validates SO101 policy transfer nor a benchmark success rate.

Final read-only Colab query confirmed active_assignments=0. Attempt 4 local flags are gr00t_rollout_completed=false / task_success=null, without recovered remote evidence. Original local report SHA256: fa51fd267b209f21b5564b5a0f4b05070452bc1c0ba64e8a8e06170cd14899b2. Attempt 2 original local report SHA256: 76569625e9063f6e1d40da7b830c1d40712c91f5a72e91d72707f3db69ffef1f. Attempts 1 and 3 ended with assign ConnectTimeout and live assignment count 0; runtime_released=false there means no actual unassign confirmation, not evidence of a leftover GPU. Exact-notebook-hash recovery of a lost allocation POST response has offline fault-injection coverage only; no live recovery was verified.

Result recovery now requires a manifest with exact file coverage, sizes and hashes. Remote completion additionally requires nonempty video, matching hash and full FFmpeg decode. These implementation/offline boundaries remain separate from live model-policy acceptance.
