# E5 counterfactual diffusion development protocol

Date fixed before E5-D2 scoring: 2026-08-16 (Asia/Nicosia)  
Role: post-outcome, exposed-D2 method development  
Protected data: C1 and I1 remain sealed and may not be read, scored, or used

## 1. Why E5 exists

E4's preregistered CIDER-tail endpoint failed its D2A advancement gate. The
secondary direct inverse-denoising energy (DIDE) had a slightly higher
equal-task candidate-rank association than published one-sample ACID, but that
observation is not diffusion-specific: the E4 shuffled-successor denoiser had
an even higher association than the true denoiser. Candidate-level true and
shuffled DIDE scores were also strongly correlated. Therefore DIDE mostly
measures generic action support and cannot support an alternative-to-ACID
claim.

This does not mean the successor condition was absent from the E4 model. On
held-out P1 real transitions, the true model's matching-versus-deranged
successor accuracy was 0.99847 for PushT, 0.95249 for Reacher, and 0.99915 for
Cube; the shuffled controls were approximately 0.50. E5 tests whether that
identified but smaller successor signal can be isolated from the action prior
on CEM candidates.

E5 does not alter or rescue E4. All E3 and E4 failures remain retained. D2 has
already influenced the research program, so every E5-D2 result is development
evidence only.

## 2. Frozen counterfactual score

For candidate `i`, planned transition `h`, noise level `sigma`, and a fixed
common noise bank, let

`E_match(i,h,sigma)`

be the E4 true denoiser's action-reconstruction energy using the candidate's
current latent, action, and matching predicted successor. Let

`E_wrong(i,h,sigma,o)`

use the same current latent, action, denoiser, noise level, and exact noise,
but replace the successor with the same-horizon successor from candidate
`(i + o) mod 300`. This differs in the successor only and avoids subtracting
energies produced by separately calibrated models.

The fixed 16 offsets are:

`{11, 29, 47, 67, 83, 101, 127, 149, 167, 191, 211, 229, 247, 263, 277, 293}`.

Each energy is first averaged over four fixed common noise draws. For the
first `K` offsets define the transition counterfactual successor denoising
advantage (CSDA), lower meaning more supported,

`g_K = mean_(sigma,o) [log(E_match + 1e-6) - log(E_wrong + 1e-6)]`.

The candidate score is the mean of the largest two `g_K` values among the five
planned transitions. The primary endpoint is `K=8`. Nested `K=4` and `K=16`
are fixed Monte-Carlo sensitivity endpoints and may not replace `K=8` based on
their outcome. Fixed diagnostics are the horizon mean, the pairwise error rate,
and `softplus` of the log ratio.

The identical procedure is run with the shuffled-successor E4 checkpoint. It
is a mechanism null, not a deployable planner: because that checkpoint failed
the P1 condition-use gate, any later planner must assign it reliability zero
and reproduce B0 exactly.

## 3. Fixed scale-free composites

Raw CSDA deliberately removes absolute action support. Two fixed composites
test whether the isolated signal is complementary. All empirical ranks are
computed within the same 300-candidate pool and scaled to `[0,1]`.

1. Standalone anchored diffusion:

   `S_anchor = 0.5 rank(DIDE) + 0.5 rank(CSDA_K8)`.

2. Forward-diffusion hybrid:

   `S_hybrid = 0.5 rank(forward verifier) + 0.5 rank(CSDA_K8)`.

The control for the second composite is

`S_forward_DIDE = 0.5 rank(forward) + 0.5 rank(DIDE)`.

No weight grid is allowed in E5-D2. These equal-weight formulas were fixed
before their E5-D2 values were computed. Candidate selection uses the same
spread normalization and `lambda=0.07` as the matched ACID comparison.

## 4. Required comparators and analyses

Every method uses the already executed identical D2 candidate pools. Report
PushT, Reacher, and Cube separately and with equal task weight. Required
comparators are B0, published one-sample ACID, ACID flow-training energy,
ACID-16-min, deterministic inverse regression, Gaussian inverse NLL, DIDE,
shuffled DIDE, the deterministic forward verifier, shuffled CSDA, and the
forward-DIDE composite.

The primary audit endpoint is within-pool Spearman association between score
and realized standardized rollout RMSE. Also report selected-candidate
success, selected RMSE, oracle regret, exact paired contrasts, and 100,000
start-cluster bootstrap resamples using seed `2026081614`.

## 5. Fixed D2 development decision

Condition identification requires all of the following point-estimate checks:

1. primary CSDA rank association is positive in every task;
2. primary CSDA has higher equal-task rank association than shuffled CSDA;
3. both nested `K=4` and `K=16` associations are positive in every task.

The standalone anchor advances only if condition identification passes and:

1. its equal-task rank association exceeds one-sample ACID;
2. it is not below ACID by more than 0.03 in any task;
3. it exceeds the shuffled DIDE-CSDA anchor in equal-task rank association;
4. selected success is not below ACID or B0 by more than 0.02.

If standalone fails, the hybrid advances only if condition identification
passes and:

1. forward-CSDA exceeds forward alone in equal-task rank association;
2. it is not below forward by more than 0.02 in any task;
3. selected success is no lower than forward;
4. forward-CSDA exceeds forward-DIDE, showing that the successor-specific
   term—not merely absolute denoising energy—adds the value.

The fixed priority is standalone anchor, then hybrid. If neither passes, this
counterfactual construction does not advance to fresh D3. A D2 point-estimate
pass merely authorizes a separately frozen D3 study; it is not evidence of a
publishable or alternative-to-ACID result.

## 6. Integrity and limitations

- E5 reuses the immutable seed-7101 E4 checkpoints; it does not retrain them.
- E5-D2 may read only already exposed D2 artifacts and P1 checkpoint metadata.
- C1/I1 paths, manifests, outcomes, and caches remain unopened.
- The source tree, endpoint list, offset list, and analysis code are hashed
  before E5-D2 submission.
- In-pool counterfactuals couple candidate scores and can be unrealistic at
  later horizons. That is a substantive limitation to test in closed loop,
  not a reason to suppress a failed D2 result.
- Raw denoising loss is not treated as a likelihood. E5 uses a same-action,
  same-noise, same-model contrast specifically to reduce action-prior and
  cross-model calibration effects.
- A fresh claim ultimately requires multiple scorer seeds, a frozen unused-P3
  D3 exclusion ledger, paired closed-loop evaluation, confidence intervals,
  latency, a shuffled/permuted null, ACID flow energy, deterministic and
  Gaussian controls, and an incremental comparison with the forward verifier.

The only honest E5-D2 outcomes are to stop this construction, or to freeze one
predeclared method for a fresh D3 test.
