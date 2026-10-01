# Progress

## Current

Independent safety deployment, base `16fb76e`, branch `codex/multilink-safety-20261001`. Old learning checkout and canonical Git/index are protected. Root Codex owns integration and publication.

## Done

Verified original paper and AEGIS equations/license; author algorithm code is not yet released. Separate worktree and CPU environment are deployed through `./so101.sh safety`.

41 checks passed. Derived five envelopes include continuous jaw sweep (.015–.5rad), correct world-frame derivatives and persistent CPU OSQP. Failed/infeasible/stale cases refuse the original action and latch. Independent review fixed final-integrated-state contact sampling and invalid timestamps; visible-point PCA estimates are denied by default.

Final `--render`: static blocking off/on contact samples 9424/0 (neither reaches); outward +y withdrawal off/on 2488/0, on reaches at8.26s, no joint-position violations. Full filter steady p99 2.47/2.44ms, startup8.81/8.28ms;41 checks and real rendered tracking pass. Four videos (1299frames) fully decoded and representative frames viewed. Raw output is ignored. Exact evidence/limits in [RESULTS.md](../../experiments/multilink-safety/RESULTS.md).

## Remaining

Scoped commit/push verification, then user review. Future work: complete obstacle geometry/perception, diverse physical scenarios, VLA integration and hardware braking. Previous learning work remains with the original Agent.

## Issues and next

Actual servo speed exceeded the model command rate; sampled-data adaptation is not continuous safety. Engineering buffer and gradient auxiliary reference were validated only in the two documented fixtures. Earlier incomplete/stopped trials are retained. RGB-D visible-point fit does not enclose hidden surfaces, so it cannot independently authorize collision protection. Root Codex owns integration and any later merge into the active training branch; do not copy over the original dirty worktree. No serial, VLA weights or cloud GPU used.
