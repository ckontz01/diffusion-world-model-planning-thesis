# E6D exposed-D2 all-iterations matched-control result

Date completed: 2026-08-17  
Role: post-E6 exposed-D2 diagnostic; not confirmatory evidence

## Immutable inputs and output

- protocol SHA-256: `808f16435775c04b36862637efa200bc4eb47797089ac3f913be962035ed9fd4`
- source-manifest SHA-256: `be1fbf7803460e2e92bff190e6123f1237e794a4c9625ea836b90ec84c6d9750`
- prerequisite E6 summary SHA-256: `84ae66457c70f5a8c386d682dab5a77bfd807f3fdf0c52de0ea7b3264ebbc0cc`
- SLURM authorization job: `297689`
- SLURM evaluation array: `297690`
- SLURM analysis job: `297691`
- official summary: `/lustreFS/data/superworld/ckontzias/thesis/results/acid-alternative/e6d-allgate-controls/analysis/job-297691/summary.json`
- official summary SHA-256: `740e02e12d3b757f82af7d53b604707825941d19d73c46e869f49bc6fd27cc79`

## Equal-task success rates

| Arm | Success rate |
|---|---:|
| continuous reconstructed ACID | 0.8800 |
| shuffled-goal all-iteration RDX q40 | 0.8867 |
| all-gate reconstructed ACID q40 | 0.8667 |
| true all-iteration RDX q40 | 0.8533 |
| forward all-iteration verifier q40 | 0.8067 |

The true RDX arm was 0.0333 below its shuffled-goal control, 0.0133 below the
matched all-gate ACID arm, and 0.0267 below continuous reconstructed ACID. Its
per-task success rates were PushT 0.88, Reacher 0.78, and Cube 0.90. The
shuffled control was PushT 0.88, Reacher 0.90, and Cube 0.88.

## Frozen decision

Gates 1 and 4 failed because true RDX did not beat the shuffled control in the
equal-task aggregate and did not produce the required per-task pattern. Gates
2, 3, and 5 passed. The frozen decision is therefore:

`end_rdx_verifier_gating`

This result permits no claim and no D3 access. It closes the scalar residual-
diffusion-verifier route. It does not test the separate E7P hypothesis that a
goal-conditioned joint-action diffusion model can improve the planner's
proposal distribution.
