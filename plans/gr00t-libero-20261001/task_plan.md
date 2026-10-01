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
4. Run one compatible Colab L4 policy episode — incomplete; final requested attempt stopped at Matplotlib backend import after successful GR00T installation and correct LIBERO venv dependency installation. Actual GPU release confirmed. No further cloud attempts without new user instruction.
5. Independently review, commit/push valid public files and record remaining acceptance — complete; public code delivered on codex/colab-twin-20261001.

## Acceptance
Environment completion, policy rollout completion and task success must remain separate. A successful LIBERO policy test uses Panda and does not establish transfer to SO101. No claims of contact grasp, vision-guided SO101 planning or hardware acceptance follow from CPU reset/step.

## Preserved work
Canonical /home/muqiao/dev/ros2/projects/so101 contains prior index and local follower/doc changes. The existing clean delivery worktree starts at 63d57653c9e8c3ac672c206f9bcc9b255ff5a6db. Root Codex owns final reconciliation; inspect canonical status and existing project handoff before integrating remaining legacy work, never reset the index or overwrite it from the delivery worktree.

## Prior retry handoff (superseded by final stop boundary below)
Root Codex owns serial integration and the next bounded acceptance run. Current fixes isolate inherited uv settings, add safe Contents HTTP timeout diagnostics and perform bounded cleanup on SIGTERM. All 27 offline checks passed with installed Colab CLI 0.6.0 (22 lifecycle/artifact checks and 5 report/source checks). A separate real uv 0.11.15 no-network package probe confirmed installation into the activated venv after child-environment isolation. These checks do not establish live LIBERO setup, cloud SIGTERM cleanup or policy completion.

Latest attempt acquired L4 23034 MiB and passed official GR00T frozen installation. Recovered bootstrap failed at official_libero_setup; the local controller exited 143 for an unknown reason before producing its own report. Root recovered the immutable bootstrap archive, then attempted repair on the same runtime within the original 45-minute deadline. Upload hit Contents PUT ReadTimeout (25.485 seconds, no HTTP status); no repaired remote worker started. Actual unassign succeeded and the final live query confirmed active_assignments=0. gr00t_rollout_completed=false and task_success=null; no policy episode/video was produced. No quota-insufficient response was observed; account balance remains unverified.

Evidence SHA256: original bootstrap bc2fa5472f4fb0ed386249e74bc3357f6abd89941e09f5be6a2727bf997dadea; recovered ZIP a0ff39e90d56f84be0e24ff4e1be47b7e4a956781280257acf97459fe9030a0d; manually recovered local delivery a2cdfd56fdf3c1d72d2e31f4c70271a5264f3c3a0ac793a8c9a52262d7fb0fa5. Runtime evidence stays in ignored output. Earlier failed attempts remain recorded in findings/progress.

Further allocation stopped for this turn. Shortest next acceptance entry is one run_colab.py L4 single episode with authenticated HF Python and Colab CLI 0.6. Require official LIBERO setup success, pinned model loading, recovered policy report/video and actual unassign confirmation. This no longer waits for HF approval. Client seed controls random reset, without fixed benchmark init states or server RNG seeding. Exact-notebook-hash allocation POST lost-response recovery remains covered only by offline fault injection; SIGKILL still requires persisted-state recovery.

## Final user-authorized attempt and stop boundary

The sixth and last requested attempt acquired L4 and passed official GR00T frozen installation (136.069 s). LIBERO dependencies now installed into its activated Python 3.12.3 venv: the child UV isolation repair is live-verified. Setup failed after 50.594 s at Matplotlib import because inherited MPLBACKEND=module://matplotlib_inline.backend_inline was unavailable in that independent environment. No GPU preflight, full model loading or policy episode followed.

Root downloaded the complete original result ZIP and verified manifest coverage/sizes/hashes. The remote worker had ended while the execution connection still awaited return. After confirming the installation failure, root sent SIGTERM to the single verified owned controller. The new bounded cleanup saved its local report (TerminationRequested) and actual unassign succeeded. Final live query confirmed active_assignments=0. This deliberately requested termination is not the remote setup failure cause; SIGTERM cleanup now has live release evidence. SIGKILL recovery remains outside that handler.

The child process now pins MPLBACKEND=agg alongside the unchanged EGL MuJoCo renderer. A real local Matplotlib headless PNG draw passed; this backend correction is not cloud-accepted. All 27 offline checks passed after the change. Original local report SHA256 690066e3bdfd9aa81b16f9cf018867ddab15a7d569a7aa95d07eec145b5ed5c5; bootstrap e1111c048a5695f719d73436b62910c369b5fe06e4c4860819f3c89936899771; ZIP c5469e7243c40a05bae68120abc7dfd7c29b211ca25678196d5abb17c56e9126. Original reports/archives remain immutable and ignored.

User said this was the last attempt: no further GPU allocation or automatic retry. Root Codex preserves the recovered evidence and remaining acceptance entry; any future cloud attempt requires a new explicit user instruction. Policy completion remains false and task success null. Preserve the MuJoCo SO101 mainline and canonical legacy-work handoff.
