# E8D GADR exposed-D2 closed-loop result

Date completed: 2026-08-17  
Evaluation array: `297744` (30/30 tasks completed, exit `0:0`)  
Analysis job: `297745` (completed, exit `0:0`)  
Analysis summary:
`/lustreFS/data/superworld/ckontzias/thesis/results/acid-alternative/gdp-cem-e8d-d2/analysis/job-297745/summary.json`  
Summary SHA-256:
`89d76ee15d4fa4420288dc5306f7f18565d39fa13c959a0c52168995b10e531f`  
Immutable source-manifest SHA-256:
`c328324213fddc13a8a4df5136819a7414cb91efde8d09f93597923f6f456453`

## Integrity verdict

- Every run and analysis checksum passed.
- Released B0 and the custom-solver B0 replay produced bit-identical success
  vectors in every task.
- The exact frozen datasets, starts, Le-WM checkpoints, proposal checkpoints,
  ACID checkpoints, seeds, budgets, and configuration were validated.
- D3, C1, and I1 were not accessed.
- These are exposed-D2, one-model-seed development results. No claim is
  authorized by this study alone.

## Closed-loop success

| Arm | PushT | Reacher | Cube | Equal-task mean |
|---|---:|---:|---:|---:|
| Released CEM (B0) | 0.86 | 0.84 | 0.76 | 0.820 |
| Custom CEM replay | 0.86 | 0.84 | 0.76 | 0.820 |
| Reconstructed ACID | 0.88 | 0.92 | 0.84 | 0.880 |
| Conditional-Gaussian refresh | 0.88 | 0.82 | 1.00 | 0.900 |
| Shuffled-GADR refresh | 0.84 | 0.86 | 1.00 | 0.900 |
| **True-GADR refresh** | **0.86** | **0.86** | **1.00** | **0.907** |
| True-GADR first iteration only | 0.86 | 0.84 | 1.00 | 0.900 |
| Conditional-Gaussian selector | 0.92 | 0.86 | 1.00 | 0.927 |
| Shuffled-GADR selector | 0.94 | 0.84 | 1.00 | 0.927 |
| **True-GADR selector** | **0.92** | **0.82** | **1.00** | **0.913** |

## Frozen primary contrasts

For true-GADR refresh:

| Contrast | Estimate | 95% two-sided interval | Exact paired sign test |
|---|---:|---:|---:|
| minus ACID | +0.0267 | [-0.0200, +0.0800] | p = 0.4545 |
| minus B0 | +0.0867 | [+0.0267, +0.1467] | p = 0.0146 |
| minus Gaussian refresh | +0.0067 | [-0.0333, +0.0467] | p = 1.0000 |
| minus shuffled-GADR refresh | +0.0067 | [-0.0267, +0.0400] | p = 1.0000 |

The ACID contrast is highly task-dependent: `-0.02` PushT, `-0.06`
Reacher, and `+0.16` Cube. The overall point win therefore comes entirely
from Cube. All three learned-proposal refresh arms reached 1.00 on Cube, so
Cube does not distinguish diffusion from a simple learned Gaussian proposal.

True-GADR selector was `+0.0333` versus ACID, but `-0.0133` versus both the
Gaussian and shuffled selectors. It used only 100 Le-WM cost calls per task,
versus 3,000 for ACID, but did not isolate a diffusion-specific benefit.

## Runtime and memory

- True-GADR refresh: 368--439 seconds per task, about 19 seconds total proposal
  time, and about 0.54 GiB peak allocated CUDA memory.
- ACID: 368--439 seconds per task, 3,000 Le-WM cost calls, and about 0.47 GiB
  peak allocated CUDA memory.
- True-GADR selector: 23--42 seconds per task and 100 Le-WM cost calls.
- Gaussian selector: 23--42 seconds per task and 100 Le-WM cost calls.

The selector result establishes a strong planning-efficiency observation, but
the Gaussian selector is at least as strong as the diffusion selector.

## Frozen decision and honest interpretation

The aggregate decision is
`stop_gadr_before_multiseed_or_fresh_data`. Refresh gates 1--4 and 6--7
passed, but gate 5 failed: true GADR did not strictly beat shuffled GADR on at
least two tasks. The selector failed its Gaussian, shuffled, and per-task
diffusion-specific gates. No E8D arm is authorized for multi-seed D2 or fresh
D3 confirmation under the frozen protocol.

The strongest defensible statement is: **goal-conditioned learned proposals
substantially improved this one-seed planner and exceeded reconstructed ACID's
point estimate, especially on Cube, but the experiment did not show that
diffusion caused the improvement.** The present evidence supports a learned
proposal or planning-efficiency thesis more strongly than a claim that
diffusion is an alternative superior to ACID.

Any further diffusion method must be a new, explicitly labeled redesign,
developed without reusing D2 for selection. A scientifically motivated next
diagnostic is to test on P1 whether the current denoiser actually uses the goal
and whether a goal-contrastive or classifier-free-guided residual diffusion
model adds information beyond the conditional Gaussian. Such a redesign may
proceed to a newly frozen untouched split only if it first beats Gaussian and
shuffled controls on P1 across model seeds.
