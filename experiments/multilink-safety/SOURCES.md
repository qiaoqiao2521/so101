# Sources and local adaptation

Checked against primary sources on 2026-10-01. No policy weights, detector,
cloud VLM, or author videos are required by this local CPU demonstration.

1. Agarwal and Raghunathan, [Multi-Link Safety Filtering for VLA Policies Around
   Moving Hazards, v1](https://arxiv.org/html/2609.40007v1#S3.SS1), §III-A equation
   (2): separate auxiliary plane per guarded link; shared CBF-QP; alpha 10.
   §IV specifies twist weight I6/25 and auxiliary-rate weight I3. §III-C states
   that moving-hazard velocity, estimation error, sample-and-hold execution,
   and imperfect link-motion prediction prevent an end-to-end invariance
   guarantee; its infeasible program executes the nominal command.
2. Hu et al., [AEGIS / VLSA, v2](https://arxiv.org/html/2512.11891v2#S4.SS3),
   §IV-C equation (9), supplies the rotating supporting-plane barrier.
   The public [AEGIS implementation](https://github.com/THU-RCSCT/vlsa-aegis/blob/2457feed5968ae803926e178c8ce8243b9ecdcf9/main/utils.py#L78-L152)
   was checked at commit `2457feed5968ae803926e178c8ce8243b9ecdcf9`.
   Its returned velocity coefficients are in body coordinates; this local
   implementation independently derives world-coordinate gradients, verified
   by central differences. No upstream source module is vendored.
   The upstream [MIT license](https://github.com/THU-RCSCT/vlsa-aegis/blob/2457feed5968ae803926e178c8ce8243b9ecdcf9/LICENSE)
   names Copyright (c) 2023 Lifelong Robot Learning; retain its full notice if
   subsequently copying substantial source from that repository.
3. The [Multi-Link project-page repository](https://github.com/yathAg/multilink-safety-filter/tree/fd71a010c03a0bae4e797eefb6d9cce246b6cca0)
   at commit `fd71a010c03a0bae4e797eefb6d9cce246b6cca0` contains the website and
   media. Its [code button](https://github.com/yathAg/multilink-safety-filter/blob/fd71a010c03a0bae4e797eefb6d9cce246b6cca0/index.html#L28-L31)
   says code is coming soon. This work is a local adaptation, not deployment
   of unreleased author code or reproduction of the paper's reported numbers.

## Adaptation boundary

`cbf_filter.py` uses first-five-joint velocities directly and the world twist
Jacobian at each model-derived ellipsoid center. It does not use the paper's
`J_link @ pinv(J_ee)` map. The gripper is excluded from the QP because the
geometry module conservatively covers its configured complete jaw sweep;
its command still requires a hard range check. Hazard translation velocity
adds an explicit derivative term. A successful result must also satisfy
joint position and velocity bounds and independently checked QP residuals.
Any absent plane certificate, invalid input, solver failure, or excessive
residual returns `stopped` with no action; no nominal fallback exists.

An auxiliary plane that loses its margin after a pose update may be replaced
by a newly optimized plane **only if its barrier value verifies the same
margin on the current measured geometry**. This local re-certification does
not move bodies or excuse overlapping volumes. It is a discrete auxiliary
state change rather than the paper's purely integrated plane update. Affected
guard indices, old/new barrier values, and re-certification latency are
reported; cold re-certification may exceed steady-state CPU timing.

The optional `barrier_buffer_m` (default zero) raises only the QP's desired
clearance from `margin_m` to `margin_m + barrier_buffer_m`. The independent
hard certificate remains `h >= margin_m`; the buffer never admits a geometry
that lacks that certificate. In the interval between the hard and soft
thresholds, the QP must request increasing clearance. This engineering
allowance anticipates sampled position-servo error, but it is not a derived
robust-control bound or a continuous-time safety guarantee. Both thresholds
are included in runtime metrics.

The filter is sampled at the chosen control period, and actual position-servo
dynamics do not exactly realize the predicted joint velocity. Its five
ellipsoids protect only the documented distal-link volume, excluding the
upper arm, base, and carried payload. Perception validity/age is the caller's
responsibility. A stop command alone cannot protect against an obstacle that
continues moving into a stationary robot. CPU timings and simulation contact
results must be measured locally; neither is a hardware safety certification.
