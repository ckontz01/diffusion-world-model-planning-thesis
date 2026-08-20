# E10M multiseed pure velocity-diffusion P1 result

Date completed: 2026-08-17  
Training array: `297788` (18/18 completed)  
Evaluation array: `297789` (3/3 completed)  
Analysis job: `297790` (completed)  
Aggregate:
`/lustreFS/data/superworld/ckontzias/thesis/results/acid-alternative/gdp-cem-e10m-p1/analysis/job-297790/summary.json`  
Aggregate SHA-256:
`a685fd9da7f6050a98cdc7fe792d73fec4f83a3e1dc6dd083982fbe5c274f84c`  
Source-manifest SHA-256:
`3231a9d92fc7f6ebf333a7a361adafd40c43eb6240fa377710d9eaaa48b12c65`

## Integrity and decision

- All 18 new training jobs, all three task evaluations, and analysis completed.
- Every result and source checksum passed.
- D2 was not reused; D3, C1, and I1 remained sealed.
- The configuration was fixed at five velocity-DDIM evaluations, guidance 1.5,
  and 300 candidates; E10M performed no hyperparameter search.
- All three model seeds (`6101`, `6102`, `6103`) passed all seven gates.
- Every per-seed and equal-seed mean contrast had the required sign.

Frozen decision:
`authorize_writing_separately_frozen_untouched_data_protocol`.

This authorizes writing and auditing the final protocol, not accessing protected
data or making a claim.

## Equal-task metrics by model seed

| Seed | Proposal | Selected-action MSE | Oracle-action MSE | Minimum goal cost |
|---:|---|---:|---:|---:|
| 6101 | **True velocity** | **0.6199** | **0.3445** | **1.8319** |
| 6101 | Shuffled velocity | 0.7627 | 0.4287 | 6.3852 |
| 6101 | Gaussian | 0.7392 | 0.4361 | 2.2018 |
| 6101 | Unconditional | 0.6710 | 0.3905 | 4.3895 |
| 6102 | **True velocity** | **0.6061** | **0.3458** | **1.8284** |
| 6102 | Shuffled velocity | 0.7562 | 0.4227 | 5.9462 |
| 6102 | Gaussian | 0.7390 | 0.4352 | 2.1733 |
| 6102 | Unconditional | 0.6633 | 0.3873 | 4.4421 |
| 6103 | **True velocity** | **0.6080** | **0.3429** | **1.8455** |
| 6103 | Shuffled velocity | 0.7467 | 0.4295 | 6.0886 |
| 6103 | Gaussian | 0.7449 | 0.4343 | 2.2290 |
| 6103 | Unconditional | 0.6674 | 0.3901 | 4.3402 |

## Equal-seed mean treatment contrasts

Negative values favor true velocity diffusion.

| Contrast | Selected-action MSE | Oracle-action MSE | Minimum goal cost |
|---|---:|---:|---:|
| True minus Gaussian | **-0.1297** | **-0.0908** | **-0.3661** |
| True minus shuffled | **-0.1439** | **-0.0826** | **-4.3047** |
| True minus unconditional | **-0.0559** | **-0.0449** | **-2.5553** |

All candidate banks retained 300 of 300 unique proposals. True velocity had
roughly 0.5--0.7% boundary coordinates versus roughly 3.8% for Gaussian.

## Stable task pattern

The same qualitative pattern repeated across all seeds:

- PushT: true velocity beat shuffled and Gaussian on selected-action MSE, while
  Gaussian retained a lower minimum predicted goal cost.
- Cube: true velocity strongly beat every control on action and goal metrics.
- Reacher: true velocity beat Gaussian and had much lower goal cost, but
  shuffled or unconditional sampling sometimes had slightly lower
  selected-action MSE.

Thus the equal-task benefit is not produced by one lucky model seed. The next
scientific question is whether this proposal-quality advantage survives
closed-loop physical control and beats reconstructed ACID on untouched starts.
The final study must retain the true/shuffled/Gaussian/unconditional controls,
all three model seeds, fixed candidate budgets, paired starts, latency, and
confidence intervals. It must not tune on D2 again.
