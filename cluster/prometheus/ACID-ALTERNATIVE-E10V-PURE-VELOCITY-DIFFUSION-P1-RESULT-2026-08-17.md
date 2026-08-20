# E10V pure velocity-diffusion P1 result

Date completed: 2026-08-17  
Training array: `297778` (6/6 completed)  
Evaluation array: `297779` (3/3 completed)  
Analysis job: `297780` (completed)  
Aggregate:
`/lustreFS/data/superworld/ckontzias/thesis/results/acid-alternative/gdp-cem-e10v-p1/analysis/job-297780/summary.json`  
Aggregate SHA-256:
`5d23323681904fe369afcb4796976782cd6e4068b90fbc0e0d163e35092bacd9`  
Source-manifest SHA-256:
`b843a68dda3355499cada1d580853654efa404bc5f5d2375fbee14b4121e3e5d`

## Integrity

- Every training, task-evaluation, and analysis job completed successfully.
- All source and result checksums passed.
- E10V used newly isolated P1-validation rows only.
- D2 was not reused; D3, C1, and I1 remained sealed.
- The method used no Gaussian initialization and no ACID/verifier cost.

## Frozen selection

Exactly one of the 20 predeclared pure-velocity configurations passed all eight
gates:

- reverse denoiser evaluations: `5`;
- classifier-free guidance scale: `1.5`;
- treatment label: `vp_true_k05_g015`;
- shuffled control: `vp_shuffled_goal_k05_g015`;
- same-model unconditional control: `vp_true_k05_g000`.

The monitor initially abbreviated the shuffled label as the selected
configuration; direct inspection of the immutable aggregate confirms that the
selected treatment is `vp_true_k05_g015`.

## Equal-task P1 medians

| Proposal | Selected-action MSE | Oracle-action MSE | Minimum Le-WM goal cost | Boundary fraction |
|---|---:|---:|---:|---:|
| **Pure true velocity diffusion** | **0.6207** | **0.3457** | **1.8913** | 0.0051 |
| Pure shuffled-goal velocity | 0.7490 | 0.4191 | 7.6081 | 0.0053 |
| Same true model, unconditional | 0.6585 | 0.3878 | 4.6409 | 0.0019 |
| Conditional diagonal Gaussian | 0.7500 | 0.4379 | 2.2471 | 0.0385 |
| Old true epsilon diffusion | 7.6844 | 6.1705 | 48.0043 | 0.9518 |

All proposal banks retained 300 of 300 unique candidates. Stable velocity
prediction removed the old epsilon sampler's near-total boundary saturation.

## Per-task selected-action MSE

| Task | True velocity | Shuffled velocity | Gaussian | Unconditional |
|---|---:|---:|---:|---:|
| PushT | **0.0453** | 0.1035 | 0.0465 | 0.0895 |
| Reacher | 1.5546 | **1.5011** | 1.7687 | **1.5166** |
| Cube | **0.2621** | 0.6425 | 0.4348 | 0.3693 |

True velocity beat both shuffled and Gaussian on selected-action MSE in PushT
and Cube. It beat both on minimum goal cost in Reacher and Cube. Reacher is the
important remaining weakness: true conditioning improved goal cost strongly
but not selected-action MSE versus shuffled or unconditional sampling.

## Frozen decision

Decision:
`authorize_separately_frozen_multiseed_p1_velocity_replication`.

This is the first result in the project where a pure diffusion mechanism beats
Gaussian, shuffled-goal, unconditional, and old epsilon controls under the
predeclared gate. It is still one model seed and a 20-configuration P1
development grid, so it is not confirmation and says nothing yet about
closed-loop success versus ACID. The selected `5`-evaluation, `1.5`-guidance
configuration must now be frozen without retuning and replicated with model
seeds 6102/6103 on another isolated P1 set before any protected-data study.
