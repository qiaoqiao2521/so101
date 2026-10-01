# Multi-Link safety deployment

## Intent and scope

User selected this fork to deploy the safety layer independently while another Agent owns state-policy training. Work in branch `codex/multilink-safety-20261001`, based on published `16fb76e`; preserve the old dirty training and canonical trees. Reuse SO101 MuJoCo geometry and interfaces. First target is local simulation; hardware remains unavailable and no serial device will be driven.

The author's official project currently says Code coming soon. The Agent proceeded with its own adaptation without agreement to change the requested scope. The user rejected that substitution; the original official-deployment objective is not complete. Do not continue the adaptation.

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

Stopped after user rejection; adaptation unadopted and official deployment incomplete. Local experimental checks and branch publication happened, but do not fulfill the requested outcome. Preserve independent code/output for traceability; do not merge into the mainline or continue expansion. Previous learning work remains with its original owner.
