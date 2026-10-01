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
4. Run one compatible Colab L4 policy episode — incomplete. Latest attempt passed system dependencies, uv installation and official GR00T frozen dependency installation; official LIBERO setup failed because dependencies entered system Python 3.13 instead of its Python 3.12 client venv. Same-runtime repair upload hit Contents PUT ReadTimeout before worker launch. Original report/log archive was recovered and actual unassign succeeded; final active_assignments=0. Child-environment isolation is locally verified, not cloud-accepted.
5. Independently review, commit/push valid public files and record remaining acceptance — complete; public code delivered on codex/colab-twin-20261001.

## Acceptance
Environment completion, policy rollout completion and task success must remain separate. A successful LIBERO policy test uses Panda and does not establish transfer to SO101. No claims of contact grasp, vision-guided SO101 planning or hardware acceptance follow from CPU reset/step.

## Preserved work
Canonical /home/muqiao/dev/ros2/projects/so101 contains prior index and local follower/doc changes. The existing clean delivery worktree starts at 63d57653c9e8c3ac672c206f9bcc9b255ff5a6db. Root Codex owns final reconciliation; inspect canonical status and existing project handoff before integrating remaining legacy work, never reset the index or overwrite it from the delivery worktree.

## Next step
Root Codex owns serial integration and the next bounded acceptance run. Current fixes isolate inherited uv settings, add safe Contents HTTP timeout diagnostics and perform bounded cleanup on SIGTERM. All 27 offline checks passed with installed Colab CLI 0.6.0 (22 lifecycle/artifact checks and 5 report/source checks). A separate real uv 0.11.15 no-network package probe confirmed installation into the activated venv after child-environment isolation. These checks do not establish live LIBERO setup, cloud SIGTERM cleanup or policy completion.

Latest attempt acquired L4 23034 MiB and passed official GR00T frozen installation. Recovered bootstrap failed at official_libero_setup; the local controller exited 143 for an unknown reason before producing its own report. Root recovered the immutable bootstrap archive, then attempted repair on the same runtime within the original 45-minute deadline. Upload hit Contents PUT ReadTimeout (25.485 seconds, no HTTP status); no repaired remote worker started. Actual unassign succeeded and the final live query confirmed active_assignments=0. gr00t_rollout_completed=false and task_success=null; no policy episode/video was produced. No quota-insufficient response was observed; account balance remains unverified.

Evidence SHA256: original bootstrap bc2fa5472f4fb0ed386249e74bc3357f6abd89941e09f5be6a2727bf997dadea; recovered ZIP a0ff39e90d56f84be0e24ff4e1be47b7e4a956781280257acf97459fe9030a0d; manually recovered local delivery a2cdfd56fdf3c1d72d2e31f4c70271a5264f3c3a0ac793a8c9a52262d7fb0fa5. Runtime evidence stays in ignored output. Earlier failed attempts remain recorded in findings/progress.

Further allocation stopped for this turn. Shortest next acceptance entry is one run_colab.py L4 single episode with authenticated HF Python and Colab CLI 0.6. Require official LIBERO setup success, pinned model loading, recovered policy report/video and actual unassign confirmation. This no longer waits for HF approval. Client seed controls random reset, without fixed benchmark init states or server RNG seeding. Exact-notebook-hash allocation POST lost-response recovery remains covered only by offline fault injection; SIGKILL still requires persisted-state recovery.
