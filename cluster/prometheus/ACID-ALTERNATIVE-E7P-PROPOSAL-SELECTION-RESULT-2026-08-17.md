# E7P P1-only proposal-selection result

Date completed: 2026-08-17  
Role: P1-validation method development; not confirmatory evidence

## Provenance

- training array: `297703` (`9/9` completed)
- accepted selection array: `297716` (`3/3` completed)
- analysis job: `297717` (completed)
- accepted selection snapshot: `gdp-cem-e7p-selection-9784aa64172a979f`
- source-manifest SHA-256: `9784aa64172a979f22ac012d6d2abe2c27e6764e0e5b5251fd8298f04ae2c49f`
- protocol SHA-256: `3c7ff146a43bb5d87e99d92dff0f9731f7ea4b186aedaec168db284ad744dbbc`
- official aggregate: `/lustreFS/data/superworld/ckontzias/thesis/results/acid-alternative/gdp-cem-e7p-selection/analysis/job-297717/summary.json`
- aggregate SHA-256: `bcd49f6fa7b7d1b03d8f95b4d46001e08b97c4725b43a55a953afc4ebe25544d`

The earlier selection array `297712` failed before its metric loop because of
the encoder-equivalence guard documented in the implementation errata. It
produced no accepted proposal-quality result and remains preserved.

## Result

The frozen selector chose 10 DDIM steps and a 0.25 matched-pool proposal
fraction, but neither integration passed its P1 advancement gate. True
diffusion did show goal information: at 10 DDIM steps it beat shuffled-goal
diffusion on equal-task selected-action MSE (`7.7350` versus `7.8997`) and
oracle-action MSE (`6.2094` versus `6.2752`), and it beat shuffled selected MSE
on PushT and Cube. It did not beat the conditional diagonal Gaussian on any
task.

| Task | True diffusion minus conditional-Gaussian selected-action MSE |
|---|---:|
| PushT | +13.2517 |
| Reacher | +1.9837 |
| Cube | +5.7068 |

Positive values are worse. The direct diffusion banks also had much larger
candidate variance than the conditional Gaussian. For example, PushT medians
were about `9.75` versus `0.0298`; its direct selected-action MSE was about
`13.30` versus `0.0515`.

The training diagnostics explain why this is a generation failure rather than
evidence that the goal condition is entirely ignored. Epsilon-prediction loss
was low, but reconstructing clean actions from uniformly sampled noise levels
was unstable: the true diffusion checkpoint's single-prediction validation
action MSE was `80.05` on PushT, `11.37` on Reacher, and `36.39` on Cube. The
100-level cosine schedule has near-zero terminal signal-to-noise ratio, so the
few-step DDIM reconstruction divides small epsilon-prediction errors by a very
small square root of cumulative alpha. Final robust clipping then produces
diverse but saturated candidates.

## Frozen decision

`stop_goal_conditioned_diffusion_proposal_before_d2`

No E7P model may be taken to D2, D3, C1, or I1. A separate P1-only rescue may
test a scientifically distinct mechanism—such as moderate-noise diffusion
refinement of the strong conditional-Gaussian proposal or a stable velocity-
prediction model—but it must use a new protocol, new result paths, and a fresh
P1 validation subset before any exposed-D2 run.
