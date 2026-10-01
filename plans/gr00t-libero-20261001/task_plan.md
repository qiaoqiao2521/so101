# GR00T / LIBERO selected experiment

## Goal
User selected candidate 1 on 2026-10-01: connect the official GR00T N1.7 LIBERO policy to a feedback environment, while keeping SO101's existing MuJoCo motion-planning work intact.

## Scope and decisions
- Reuse SO101's existing repository and delivery worktree; no replacement repository or simulator stack.
- First verify real LIBERO reset, physical step, both cameras and official success predicate on CPU. This is environment verification, not autonomous policy success.
- Prepare a pinned official GR00T server/client path for one environment and one episode.
- User authorized existing paid Colab quota for a small sample. Hugging Face Cosmos access has not been granted; user will apply and report approval.
- Preserve existing hardware, calibration, serial settings and canonical dirty work. No actuation.
- Keep all upstream downloads, models, images, credentials and runtime reports ignored.

## Phases
1. Confirm ownership and official model/device requirements — complete.
2. Implement and verify isolated CPU environment — complete; root independently repeated real reset/10-step/two-camera smoke.
3. Review the bounded official GPU rollout entry — complete at static/interface level; no live policy acceptance yet.
4. Run one compatible Colab GPU policy episode — waiting for user model access and secure authentication.
5. Independently review, commit/push valid public files and record remaining acceptance — pending.

## Acceptance
Environment completion, policy rollout completion and task success must remain separate. A successful LIBERO policy test uses Panda and does not establish transfer to SO101. No claims of contact grasp, vision-guided SO101 planning or hardware acceptance follow from CPU reset/step.

## Preserved work
Canonical /home/muqiao/dev/ros2/projects/so101 contains prior index and local follower/doc changes. The existing clean delivery worktree starts at 63d57653c9e8c3ac672c206f9bcc9b255ff5a6db. Root Codex owns final reconciliation; inspect canonical status and existing project handoff before integrating remaining legacy work, never reset the index or overwrite it from the delivery worktree.

## Next step
Deliver verified public code and private local evidence, then resume one policy episode after Cosmos access approval. Start at experiments/gr00t-libero/README.md; use a compatible temporary Colab GPU, independently verify actual rollout result, and release the owned runtime even on failure.
