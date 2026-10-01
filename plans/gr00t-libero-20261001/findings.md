# Findings

## Executed environment evidence
Root independently reran the final CPU smoke after review fixes: source/asset manifest verified 1116 files, Mesa llvmpipe software renderer, seeded reset, 10 real MuJoCo physical steps / 0.5 seconds, two 256x256 RGB cameras. environment_completed=true, task_success=false, gr00t_rollout_completed=false. Five boundary tests passed (failed-task result semantics, empty/missing episode rejection, T4 rejection, changed and unexpected source files). Unknown task, zero steps and missing GPU checkout remained failures. No GPU, model or hardware call occurred.

Independent review fixes: LFS skip applies to checkout and submodule; model cache is shared but each GPU episode uses a UUID artifact directory with video SHA256; source reuse and smoke reject altered files against the pinned archive manifest.

- GR00T source: 51d4c89f72fda44cbf77285c6a8114b52676b8a1.
- Its LIBERO gitlink: 8f1084e3132a39270c3a13ebe37270a43ece2a01.
- Public policy checkpoint: nvidia/GR00T-N1.7-LIBERO at 2ea293aa20ba7cf5bbf3ba17a5fbcb1a01cbfe21. Inference files in libero_10 total approximately 6.915 GB; optimizer states are unnecessary.
- Mandatory Cosmos-Reason2-2B backbone is gated; observed revision 9ce19a195e423419c349abfc86fd07178b230561. Official page requires login and agreement to contact-information sharing and model conditions. User is applying. No local HF credential was configured during preflight; only presence was checked.
- Default BF16/FlashAttention2 stack requires compatible Ampere or newer GPU. T4 is not supported by that default stack. Existing paid Colab small-sample use is authorized; no runtime allocated during gated preflight.
- Local nvidia-smi cannot contact the driver. Driver repair is outside this experiment.
- Official LIBERO setup script unconditionally removes ~/.libero. Independent CPU setup avoids it; official GPU setup belongs only in a temporary VM with no existing user config.
- Knowledge adopted from Wiki/自动化开发范式与智能体协作.md: code/test evidence is separate from actual task behavior and delivery. Apply this by recording environment, rollout and success as three separate fields.

Sources: [GR00T](https://github.com/NVIDIA/Isaac-GR00T/tree/51d4c89f72fda44cbf77285c6a8114b52676b8a1), [Cosmos access](https://huggingface.co/nvidia/Cosmos-Reason2-2B), [FlashAttention](https://github.com/Dao-AILab/flash-attention#nvidia-cuda-support).
