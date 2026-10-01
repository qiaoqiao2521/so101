# Multi-Link safety deployment

## Intent and scope

User selected this fork to deploy the safety layer independently while another Agent owns state-policy training. Work in branch `codex/multilink-safety-20261001`, based on published `16fb76e`; preserve the old dirty training and canonical trees. Reuse SO101 MuJoCo geometry and interfaces. First target is local simulation; hardware remains unavailable and no serial device will be driven.

The author's official project currently says Code coming soon. Implement an explicitly named paper adaptation, using the published barrier equations and AEGIS provenance. Do not claim the author system, π₀.₅ timing or paper collision rates were reproduced.

## Plan and acceptance

1. Verify original paper/source/license and isolate checkout/runtime.
2. Build five geometry envelopes and analytic world-frame barrier gradients; test coordinate conventions independently.
3. Solve one CPU QP over five arm joints and auxiliary plane rates. Preserve joint limits; solver, perception or initial-state failure refuses execution.
4. Fit/travel a hazard from designated RGB-D observations; test actual sparse LK, gates and stale failures separately from oracle geometry trials.
5. Run paired identical SO101 nominal commands, shield off/on, with actual MuJoCo hazard contacts and task outcome. Record all failures and CPU latency percentiles, including startup separately. Generate visible local demonstration.
6. Document exact deployment command, differences/limitations, verify changed scope, commit and push this branch only. Previous training task retains its owner and artifacts.

## Adopted knowledge

CapMesh `inventory/community-alternatives.md` robotics-arm entry recommends existing SO101/LeRobot model assets; reuse the repository model and controller rather than create a separate robot project. Obsidian `Wiki/开发协作接入.md` keeps current acceptance in the project and distinguishes local checks from hardware claims.

## Status

Local simulation deployment complete: isolated runtime, 41 checks, actual RGB-D tracking gates and paired physical contact trials with decoded videos. Static blocking remains an incomplete task; outward retreat resumes and reaches the goal without contact. Source/scope review and branch-only delivery passed; implementation commit `cc01580` was read back from GitHub. Official code release, complete perception, VLA and hardware remain outside this deployment.
