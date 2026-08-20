# ACID-alternative v2 E2 action-evidence protocol

Date frozen: 2026-08-16 (Asia/Nicosia)  
Role: post-v2, outcome-selected D1 exploration; **not confirmation**

## 1. Fixed motivation

The residual-diffusion seed-6101 pilot is complete. Its P1 gate passed on all
three tasks, but its D1 promotion gate did not pass in full. The selected raw
conditional reconstruction score (`RDX0_G100`) achieved equal-task Spearman
correlation `0.2520618316`, exceeding v1 raw diffusion by `0.0924020483` with
95% CI `[0.0280397397, 0.1594048329]` and exceeding the deterministic forward
verifier by `0.0281178556` as a point estimate. However, the paired advantage
over the shuffled-action residual-diffusion model had 95% CI
`[-0.0050822255, 0.0747304702]`, and the frozen `lambda=0.005` selection gate
missed because RMSE was `0.3711809067` versus `0.3646906901` for v1 raw
diffusion, despite higher success (`0.6388888889` versus `0.625`).

The P1 mechanism result is unambiguous: true-action versus permuted-action
accuracy was `0.99445`, `0.94106`, and `0.9992267` on PushT, Reacher, and
Cube, while matched shuffled-label controls were `0.5028667`, `0.5015`, and
`0.4999333`. The D1 result therefore suggests that raw reconstruction error
mixes two signals: generic transition-manifold difficulty and action-specific
evidence. E2 tests one fixed decomposition of those signals. It is not a
retroactive v2 rescue and cannot change the recorded v2 gate failure.

Immutable observed inputs are:

- v2 P1 gate summary SHA-256
  `630eb6dfb7802ca8de5ff20e96d2c2a652af2b2d74d75c12ef23197226a16560`;
- v2 D1 summary SHA-256
  `74f0fcfea152f9ce0930b142171149b037b53a5a36a7134339c0b7ee6fc635a9`;
- v2 D1 cost archive SHA-256
  `a959d93b704b78cd3999faa946ad1db0f7dfe16b93084257cbdbcd99491e6223`.

## 2. Frozen E2 score

No model is retrained. For every stored D1 transition, load the already
selected seed-6101 true-action and shuffled-action residual-diffusion
checkpoints. Reproduce the v2 noise bank exactly:

- `sigma in {0.25, 1.0, 4.0}`;
- eight deterministic common noise draws;
- the v2 SHA-256 seed derivation;
- the same imagined current latent, standardized residual, candidate action,
  and candidate/horizon aggregation.

For each model and candidate compute:

- `C_cond`: MSE of the ordinary conditional prediction (`g=1.0`);
- `C_uncond`: MSE with zero action and `condition_present=0`.

The single permitted E2 candidate score is

`L = log(C_cond + 1e-12) - log(C_uncond + 1e-12)`.

The true-action model produces `AE_TRUE`; the shuffled-action model produces
the matched null `AE_SHUFFLED`. Lower values mean that conditioning makes the
imagined transition substantially easier to denoise; higher values mean that
the proposed action adds little or adverse explanatory evidence. There is no
alternative epsilon, sigma subset, aggregation, absolute value, sign flip,
weight, guidance value, or task-specific form.

The implementation must reproduce every stored v2 `RDX0_G100` and
`NULL_RDX0_G100` candidate cost with maximum absolute error at most `1e-6`
before E2 results are accepted.

## 3. Frozen analysis

The primary endpoint is within-pool Spearman correlation between `AE_TRUE`
and physically realized standardized rollout RMSE. `AE_SHUFFLED` is analyzed
identically. Uncertainty uses the same 100,000 pool-cluster bootstrap draws,
seed `2026081611`, 24 starts per task, and equal task weighting as v2.

Report:

1. per-task and equal-task correlations for `AE_TRUE` and `AE_SHUFFLED`;
2. paired `AE_TRUE - AE_SHUFFLED`, `AE_TRUE - R0_raw`, and
   `AE_TRUE - F0_forward` contrasts;
3. candidate-selection success and standardized RMSE under the unchanged
   spread-adaptive rule at `lambda in {0.005, 0.07}`;
4. candidate-index agreement with B0, v1 raw diffusion, forward, and ACID;
5. score distributions, finite-value checks, reproduction error, latency,
   source hashes, checkpoint hashes, and data lineage.

## 4. Frozen promotion gate

E2 advances only if every condition below holds:

1. `AE_TRUE` correlation is positive in PushT, Reacher, and Cube;
2. its equal-task 95% lower confidence bound is above zero;
3. the paired `AE_TRUE - AE_SHUFFLED` equal-task 95% lower bound is above
   zero;
4. the paired improvement over v1 raw diffusion has a 95% lower bound above
   zero;
5. Reacher's point estimate is at least `0.075`;
6. the equal-task point-estimate gap to forward is no worse than `-0.030`,
   with no task gap worse than `-0.075`;
7. at `lambda=0.005`, success is not below v1 raw diffusion and standardized
   RMSE is not above v1 raw diffusion;
8. both true and null score distributions are finite and noncollapsed, and
   the v2 conditional-cost reproduction guard passes.

Passing permits a newly frozen three-seed development expansion; it is not
confirmation. Failure stops E2. No result may be rescued by choosing a task,
lambda, sign, or unregistered transformation after inspection.

## 5. Data boundary

E2 may read only P1-trained checkpoints and the already observed D1
same-candidate artifacts. C1 and I1 remain prohibited and unread. Any future
claim requires fresh, isolated D2 data and a subsequently frozen confirmation
protocol.
