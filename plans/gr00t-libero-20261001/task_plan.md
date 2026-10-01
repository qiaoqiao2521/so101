# GR00T / LIBERO selected experiment

## Goal
User selected candidate 1 on 2026-10-01: connect the official GR00T N1.7 LIBERO policy to a feedback environment, while keeping SO101's existing MuJoCo motion-planning work intact.

## Scope and decisions
- Reuse SO101's existing repository and delivery worktree; no replacement repository or simulator stack.
- First verify real LIBERO reset, physical step, both cameras and official success predicate on CPU. This is environment verification, not autonomous policy success.
- Prepare a pinned official GR00T server/client path for one environment and one episode.
- User authorized existing paid Colab quota for a small sample. Official HF CLI OAuth authorization and actual gated Cosmos config download are now verified. Full weight download, model loading, policy completion and task success require separate evidence.
- Preserve existing hardware, calibration, serial settings and canonical dirty work. No actuation.
- Keep all upstream downloads, models, images, credentials and runtime reports ignored.

## Phases
1. Confirm ownership and official model/device requirements — complete.
2. Implement and verify isolated CPU environment — complete; root independently repeated real reset/10-step/two-camera smoke.
3. Review the bounded official GPU rollout entry — complete at static/interface level; no live policy acceptance yet.
4. Run one compatible Colab L4 policy episode — blocked by current Colab communication timeout. Attempt 2 acquired L4 (23034 MiB), passed apt/EGL/FFmpeg, failed at ensurepip before policy execution, and was actually unassigned. Attempt 4 ended with local status=failed / error_type=TimeoutExpired and actual unassign success. No bootstrap report, video or policy result was recovered. The uv repair is not GPU-validated.
5. Independently review, commit/push valid public files and record remaining acceptance — complete; public code delivered on codex/colab-twin-20261001.

## Acceptance
Environment completion, policy rollout completion and task success must remain separate. A successful LIBERO policy test uses Panda and does not establish transfer to SO101. No claims of contact grasp, vision-guided SO101 planning or hardware acceptance follow from CPU reset/step.

## Preserved work
Canonical /home/muqiao/dev/ros2/projects/so101 contains prior index and local follower/doc changes. The existing clean delivery worktree starts at 63d57653c9e8c3ac672c206f9bcc9b255ff5a6db. Root Codex owns final reconciliation; inspect canonical status and existing project handoff before integrating remaining legacy work, never reset the index or overwrite it from the delivery worktree.

## Next step
Public CPU and policy-entry code was delivered previously. This continuation integrates run_colab.py, colab_safe_cli.py, remote_bootstrap.py and portable test_colab.py on the existing delivery branch. All 24 offline checks passed (19 Colab lifecycle/artifact checks and 5 existing report/source checks). Further allocation has stopped after communication timeout; recovery when allocation POST succeeds but its response is lost has received offline boundary checks, while live recovery is unverified. Start at experiments/gr00t-libero/README.md with an authenticated HF Python and the existing Colab CLI 0.6 interpreter. Recover reports/videos, independently check policy completion and terminal task success, and require actual unassign confirmation even on failure. Runtime outputs, session state and credentials remain private and ignored.

Current closeout: gated model file access passed; policy rollout incomplete; attempt 4 local delivery failed with TimeoutExpired; runtime_released=true based on actual unassign. There is no remote bootstrap/policy report, video or episode length, so terminal task success and remote failure phase remain unknown. The original local attempt 4 report SHA256 is fa51fd267b209f21b5564b5a0f4b05070452bc1c0ba64e8a8e06170cd14899b2. Final read-only Colab query confirmed active_assignments=0. Local gr00t_rollout_completed=false and task_success=null record the absence of policy completion evidence; do not assign an episode length or video hash. Allocation POST lost-response recovery by exact notebook hash is covered only by offline fault injection, not a live recovery acceptance.

Shortest next acceptance entry remains one run_colab.py L4 single episode once Colab communication is stable and allocation-response recovery is checked; this no longer waits for HF approval. Require recovered policy report/video and actual unassign confirmation. Client seed controls reset, without fixed benchmark init states or server RNG seeding.
