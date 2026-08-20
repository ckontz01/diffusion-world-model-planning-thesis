# ACID-alternative E4-D2A implementation freeze

Date: 2026-08-16 (Asia/Nicosia)  
Role: post-E3, post-P1 **exploratory development** on already exposed D2 data  
Parent protocol: `ACID-ALTERNATIVE-E4-DIFFUSION-INVERSE-DEVELOPMENT-PROTOCOL-2026-08-16.md`  
Protected material: C1 and I1 remain sealed

## 1. Activation rule

This document freezes implementation details that were not fully specified in
the parent protocol. It authorizes no outcome access by itself. E4-D2A may run
only if the immutable E4-P1 gate reports
`advance_to_e4_d2a_exposed_candidate_audit` for all three tasks. All source and
this document must be content-addressed in a new read-only snapshot before the
first E4 score is computed on a D2 candidate.

The D2 candidate pools and physical executions already exist and have already
influenced earlier E3 development. D2A is therefore diagnostic development,
never confirmation, even though E4 endpoints have not yet been computed on it.

## 2. Primary E4 endpoint

The primary endpoint is the parent protocol's calibrated conditional inverse
denoising evidence ratio (`CIDER-tail`): four fixed common-noise draws at each
of `sigma={0.5,1,2,4}`, a P1 q95/q99 one-sided violation at each transition,
the equal-sigma mean, and the mean of the worst two of five planned
transitions. Common random numbers are keyed by task, scorer seed, sigma,
draw, and horizon position and are shared across candidates. The true
seed-7101 P1 checkpoint is primary.

The shuffled-successor E4 checkpoint is scored for diagnosis but has
deployment reliability zero. Its planning cost and selected candidate must be
exactly B0; it cannot acquire influence through spread normalization.

Required E4 ablations are direct inverse-denoising energy (`DIDE`), raw mean
`CIDER`, mean rather than upper-tail calibrated violation, and shuffled CIDER.
No ablation can replace `CIDER-tail` after outcomes are read.

## 3. ACID controls

The audited paper-equation ACID reconstruction at training seed 6101 is the
primary ACID comparator. It uses native frozen latents, standardized actions,
one Gaussian action sample, one Euler step, planner-coordinate squared action
residual, mean over five transitions, and the published adaptive weight with
`lambda=0.07`. Existing seeds 6102 and 6103 are reported as sensitivity and
are not used to choose the primary seed.

Three deliberately stronger diagnostics are frozen before E4-D2A:

1. `ACID-flow-energy`: the flow-matching training residual of the exact
   proposed action, averaged over the same four noise levels and four common
   draws used by E4. This separates direct support-energy evaluation from a
   diffusion-specific advantage.
2. `ACID-16-mean`: the mean planner-coordinate action residual over 16
   independent one-step inverse samples per transition.
3. `ACID-16-min`: the minimum residual over those 16 samples at each
   transition, then the horizon mean. This is a generous support-distance
   version of ACID for multimodal inverse dynamics.

The 16-sample banks are deterministic and keyed by task, scorer seed, draw,
and horizon position. They use common random numbers across candidates. These
diagnostics strengthen the baseline; they do not replace published one-sample
ACID as the named primary comparator.

## 4. Non-diffusion controls

Two capacity-matched inverse controls use the identical P1 transition cache,
standardizers, train/validation split, seed 7101, width 384, three residual
MLP blocks, 100,000 optimization steps, batch size 512, AdamW, `1e-4` peak
learning rate, 1,000-step warmup plus cosine decay, `1e-4` weight decay,
gradient clipping at 1, and bfloat16 training:

- `deterministic-inverse`: predicts the standardized action from the current
  and successor latents with action MSE. Its candidate cost is mean action MSE
  over the five transitions.
- `Gaussian-ratio`: predicts diagonal-Gaussian action mean and log scale.
  Log scale is clamped to `[-5,2]`; the loss is Gaussian NLL. With probability
  0.20 the successor alone is dropped while the current latent is retained.
  Its raw transition score is
  `NLL(a|z,z_next)-NLL(a|z)`. P1 q95/q99 calibration and the same worst-two
  horizon reduction produce `Gaussian-tail`.

Both controls must be within 10% of the ACID parameter count and must replay
their selected P1 checkpoint exactly. Gaussian-ratio is an added stringent
control: if it matches E4, the result supports conditional density-ratio
verification, not diffusion specifically.

The existing capacity-matched deterministic forward verifier at seed 6101 is
also required, with seeds 6102/6103 reported as sensitivity.

## 5. Same-candidate measurements

Every endpoint is evaluated on the identical stored Le-WM trajectory, action
sequence, physical execution, candidate pool, goal cost, and environment
success label. There are 50 start pools and 300 candidates per pool for each
of PushT, Reacher, and Cube. No candidate is regenerated.

For each endpoint and pool report:

- Spearman association between verifier cost and standardized physical rollout
  RMSE (higher positive association is better);
- top-decile failure enrichment: physical RMSE in the 30 candidates with
  highest verifier cost minus physical RMSE in all 300 candidates;
- selected-candidate environment success and physical RMSE;
- oracle regret relative to the physically lowest-RMSE candidate; and
- CUDA-synchronized scorer latency after a one-pool warmup, excluding loading
  and the shared world-model rollout.

For candidate selection, B0 selects minimum goal cost. A reliable verifier
with within-pool spread greater than `1e-8` uses

`goal + 0.07 * std(goal) / std(verifier) * verifier`.

If its spread is at most `1e-8`, it selects B0 exactly. Shuffled CIDER always
selects B0 regardless of numerical spread. Sensitivities at lambda 0.02 and
0.14 are reported without replacing lambda 0.07.

A calibrated score is allowed to be identically zero within a pool: this means
that no candidate exceeds the P1 support threshold. Such a pool receives rank
association zero (no ranking information), zero top-decile enrichment, and B0
selection. Deterministic tie breaking uses candidate index order. A method is
declared globally collapsed only if every candidate in every pool of a task is
identical; that task then fails the positive-association advancement rule.

## 6. Analysis and immutable advancement gate

Inference is performed without reading aggregate outcomes; analysis runs only
after all three task artifacts exist. Bootstrap resampling uses 100,000 paired
draws clustered by D2 start, with equal weight for tasks. Each task remains
visible and is never replaced by a pooled-only result.

E4-D2A advances to closed-loop E4-D2B only if primary `CIDER-tail`:

1. has positive within-pool rank association in every task;
2. has an equal-task two-sided 95% bootstrap lower bound above zero;
3. exceeds shuffled CIDER with a paired two-sided 95% lower bound above zero;
4. is no worse than primary one-sample ACID by more than 0.03 in equal-task
   rank association, using a one-sided 95% lower bound; and
5. has selected-candidate success no lower than B0 and no lower than ACID by
   more than 0.03 in the equal-task point estimate.

The analysis additionally reports paired contrasts against ACID-flow-energy,
ACID-16-mean, ACID-16-min, deterministic inverse, Gaussian-tail, and forward.
A diffusion-specific interpretation is allowed only if CIDER-tail exceeds the
deterministic inverse and Gaussian-tail point estimates and is not worse than
either by more than 0.03 at the one-sided 95% bound. This interpretation gate
does not change the D2B advancement gate.

No D2A result permits an alternative-to-ACID publication claim. A positive
result authorizes only the frozen closed-loop development test, then
multi-scorer-seed development, followed by genuinely fresh confirmation.
