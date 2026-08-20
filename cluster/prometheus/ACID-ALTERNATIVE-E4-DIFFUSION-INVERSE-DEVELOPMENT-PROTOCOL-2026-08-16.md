# ACID-alternative E4: conditional inverse-diffusion development protocol

Date frozen: 2026-08-16 (Asia/Nicosia)  
Role: explicitly post-E3 **exploratory method development**  
Protected material: C1 and I1 remain sealed and may not be read, scored, or
executed

## 1. Status and reason for the redesign

E3 remains a valid failed test of the frozen residual-diffusion AE method. Its
decision, `stop_diffusion_development_and_pivot`, is not changed, rescued, or
reinterpreted. At the researcher's explicit request, E4 opens a separately
named post-outcome exploratory line to test a materially different hypothesis.
Nothing in E4 is confirmatory, and D1/D2 are development data because their
outcomes have already influenced the research program.

The E3 architecture asked a high-dimensional latent-future denoiser whether an
action helped reconstruct an almost observed future. Its true and shuffled
models produced nearly identical raw spreads, while the per-pool adaptive
weight amplified both to the same fixed relative influence. Across E3's
non-clamped CEM calls,

`adaptive_weight * verifier_std / (lambda * goal_std) = 1`

up to floating-point error. A nearly collapsed null therefore remained a
full-strength planner perturbation. This is a calibration failure as well as
an architectural warning.

E4 reverses the conditional direction. It diffuses the low-dimensional action
block and conditions its denoising on the proposed latent transition. This
answers the same inverse-consistency question as ACID while evaluating the
planner's actual action directly rather than measuring its distance to one
sample drawn from a potentially multimodal inverse model.

This basic inverse-diffusion construction is not claimed as novel. Latent
Diffusion Planning already trains an action diffuser conditioned on two latent
states. The possible contribution tested here is narrower: using conditional
inverse-denoising evidence as a decision-time feasibility cost for an existing
action-conditioned world-model/CEM planner, with an explicit condition-use
null and null-safe calibration, in a matched comparison with ACID.

Primary methodological precedents are:

- [ACID](https://arxiv.org/abs/2607.02403), for inverse-dynamics consistency in
  action-conditioned world-model planning;
- [Latent Diffusion Planning](https://arxiv.org/abs/2504.16925), for a diffusion
  inverse-dynamics model over actions conditioned on latent endpoint pairs;
- [Beyond Penalization / DOSER](https://arxiv.org/abs/2605.08202), for using
  action-denoising reconstruction error as a support diagnostic and calibrating
  it from training-distribution percentiles; and
- [On the Limitations of Conditional Diffusion Models](https://arxiv.org/abs/2409.06364),
  for the need to verify that a conditional denoiser actually uses its
  condition rather than assuming conditional likelihood is informative.

## 2. Fixed scientific hypotheses

Let `z` and `z_next` be consecutive frozen Le-WM latents and let `a` be the
five-primitive-action block that connects them. E4 tests three ordered claims:

1. A conditional action denoiser can distinguish the supported triplet
   `(z, z_next, a)` from a triplet with a deranged successor or action.
2. Conditional evidence relative to a current-state-only action model is more
   robust than unconditional inverse reconstruction:

   `CIDER = log(E[a | z, z_next] + eps) - log(E[a | z] + eps)`.

   Lower CIDER means the proposed successor supplies evidence for the proposed
   action. This density-ratio orientation removes the preference for actions
   that are merely common under the behavior policy.
3. A one-sided, P1-calibrated tail penalty can improve CEM without forcing tiny
   null fluctuations to have a fixed influence.

`DIDE = E[a | z, z_next]` (direct inverse-denoising energy) is a required
secondary endpoint. CIDER is primary. The labels DIDE and CIDER are internal
descriptors, not novelty or naming claims.

## 3. Data boundary and stages

Only the existing P1-train and P1-validation transition caches may be used for
training, checkpoint selection, condition-use tests, or calibration. These
caches exclude I1. The initial mechanism pilot uses model seed `7101` for all
three tasks.

The stages are irreversible and ordered:

1. **E4-P0 (implementation):** unit tests, deterministic replay, lineage checks,
   parameter count, and one real-cache CUDA smoke test.
2. **E4-P1 (P1 mechanism):** train one true-successor model and one
   shuffled-successor control per task. No D1/D2 outcome may be scored before
   all six jobs and the predeclared gate are complete.
3. **E4-D2A (exposed candidate audit):** only after E4-P1 passes, score the
   already exposed D2 candidate pools. This is exploratory development, not
   fresh evidence.
4. **E4-D2B (closed loop):** permitted only if the fixed candidate-audit gate
   passes. It compares independently optimized planners on the exposed D2
   starts.
5. **E4-M (multi-seed development):** seeds `7102` and `7103` are trained only
   after a seed-7101 closed-loop signal. This prevents spending compute to
   stabilize a mechanism that did not work once.
6. **Future confirmation:** only a method frozen after E4-M may be evaluated on
   genuinely new isolated starts or a new backbone. C1/I1 are not repurposed.

## 4. Frozen E4-P1 model

Actions are the planner-coordinate action blocks stored in the transition
cache, standardized using the P1-train `acid_action_mean` and
`acid_action_std`. Latents are standardized using the existing P1-train latent
statistics.

For clean standardized action `x`, independently sample

`sigma in {0.25, 0.5, 1.0, 2.0, 4.0}`

uniformly and `epsilon ~ Normal(0, I)`, then form

`x_sigma = x + sigma * epsilon`.

The denoiser predicts clean `x` from standardized `z`, standardized `z_next`,
`x_sigma`, a 64-dimensional sinusoidal `log(sigma)` embedding, and an explicit
`successor_present` flag. Its architecture is width 384 with three residual
MLP blocks, expansion two, SiLU, and LayerNorm. Its trainable parameter count
must be within 10% of the audited ACID reconstruction. The larger tolerance
than E3 reflects the different output dimension; exact parameter counts are
reported and latency remains a required comparison.

Classifier-free successor dropout is `0.20`: the current latent remains, while
the successor is replaced by zeros and `successor_present=0`. Thus the dropped
branch estimates current-state-only action support rather than an unconditional
global action prior.

The true model uses the matching successor. The shuffled-successor control
uses a fixed single-cycle derangement of successors across P1-train rows while
retaining each row's current latent and action. Its marginal action data,
optimizer, architecture, random streams, and current-action relationship are
therefore preserved while information in the successor is destroyed. A
separate derangement is used for validation.

Training is deliberately a pure denoising objective; there is no contrastive
or classification loss that could supply the result independently of
diffusion:

`loss = mean(||x_hat - x||^2)`.

Optimization is fixed at 100,000 steps, batch size 512, AdamW with peak learning
rate `1e-4`, betas `(0.9, 0.999)`, weight decay `1e-4`, 1,000-step linear
warmup followed by cosine decay, gradient clip 1.0, and bfloat16 CUDA autocast.
Checkpoint-selection validation occurs every 5,000 steps on a fixed 20,000
P1-validation-pair subset with one fixed draw at every noise level. The
selected checkpoint minimizes mean training-condition denoising loss over all
five levels. After selection, the checkpoint is reloaded and the complete
mechanism diagnostic is run on at most 100,000 fixed P1-validation pairs with
four fixed draws. Both selection and final validation must reproduce exactly.

## 5. Frozen condition-use diagnostics and E4-P1 gate

Final validation uses fixed common noise for four comparisons at every sigma:

- matching successor and matching action;
- deranged successor with the same current and action;
- matching successor with a deranged action;
- current-state-only prediction for the matching action.

For each example, energies first average squared reconstruction error over
action dimensions and four fixed noise draws. Report pairwise accuracies,
mean/median margins, bootstrap intervals, and all five noise levels separately.
The primary P1 identification statistic is the equal-weight mean over
`sigma in {0.5, 1.0, 2.0, 4.0}`; `sigma=0.25` is diagnostic because copying the
lightly corrupted action may hide condition use.

E4-P1 passes only if every task satisfies all of the following:

1. the true model's matching-versus-deranged-successor pairwise accuracy is at
   least `0.65`;
2. its matching-versus-deranged-action pairwise accuracy is at least `0.65`;
3. its mean deranged-successor-minus-matching energy margin is positive;
4. its successor accuracy exceeds the matched shuffled-successor control by at
   least `0.10`;
5. its mean CIDER is lower for matching than deranged successors;
6. all scores are finite and noncollapsed, and checkpoint reload reproduces
   the selected validation record.

Failure stops E4 before D2 scoring. Results cannot be rescued by deleting a
task, choosing a sigma after inspection, or adding a contrastive loss under
this protocol.

## 6. Frozen P1 calibration and candidate cost

For each task and scoring sigma `{0.5, 1.0, 2.0, 4.0}`, compute CIDER using four
fixed common noise draws. From matching P1-validation triplets, store the 50th,
95th, and 99th percentiles. Define the scale

`s_sigma = max(q99_sigma - q95_sigma, 0.10)`

and transition violation

`v_sigma = relu((CIDER_sigma - q95_sigma) / s_sigma)`.

The per-transition score is the mean of the four `v_sigma` values, clipped at
10. The candidate score is the mean of the largest two scores among the five
planned transitions (a fixed 40% upper-tail mean). This makes ordinary
P1-like transitions cost zero and concentrates the penalty on a candidate's
weakest links.

A checkpoint is deployment-reliable only if its E4-P1 gate passes. A failed or
shuffled checkpoint receives reliability zero and therefore exactly reproduces
B0; it may not be adaptively amplified. A passing true checkpoint receives
reliability one. When candidate score spread is nonzero, combine it with goal
cost using the published ACID spread formula and the same primary
`lambda=0.07`; when it is zero, return goal cost unchanged. Fixed sensitivity
values `lambda in {0.02, 0.14}` are reported but cannot replace the primary
decision.

Required ablations are uncalibrated DIDE, unthresholded CIDER, mean rather than
upper-tail horizon reduction, and the shuffled-successor null. None may replace
the frozen calibrated CIDER endpoint after outcomes are seen.

## 7. Required matched controls

E4-D2A and any E4-D2B must report, on identical checkpoints, datasets,
candidate budgets, starts, and paired planner randomness:

1. original CEM/B0;
2. the audited published-equation ACID reconstruction;
3. ACID flow-training energy evaluated directly on the proposed action across
   matched noise/time points, to separate diffusion from support-energy
   scoring;
4. the existing capacity-matched deterministic forward verifier;
5. a capacity-matched deterministic inverse regressor;
6. true calibrated CIDER;
7. shuffled-successor CIDER, which is forced to B0 by the reliability rule;
8. DIDE and the fixed CIDER ablations as diagnostic arms.

If flow energy or deterministic inverse regression matches CIDER, the result
may support direct support evaluation but not a diffusion-specific advantage.
For a diffusion-specific claim, CIDER must beat both controls under the same
development and later confirmation rules.

## 8. E4-D2A and E4-D2B advancement rules

E4-D2A uses the already captured common D2 candidate pools and physical
executions. The primary endpoint is within-pool rank association with realized
rollout error, accompanied by top-decile failure enrichment, selected-candidate
success, and oracle regret. Every task is reported separately and tasks are
equally weighted.

E4-D2A advances only if calibrated CIDER:

1. has positive rank association in every task;
2. has an equal-task 95% bootstrap lower bound above zero;
3. exceeds shuffled CIDER with a paired 95% lower bound above zero;
4. is no worse than ACID by more than `0.03` in equal-task rank association;
5. has selected-candidate success no lower than B0 and no lower than ACID by
   more than `0.03` in the equal-task estimate.

E4-D2B then runs independent CEM optimization. Its primary endpoint is
environment success, with task-stratified start-cluster bootstrap intervals.
Seed-7101 advances to E4-M only if calibrated CIDER has a higher equal-task
point estimate than ACID and B0, is not below either comparator in any task by
more than `0.05`, and exceeds the forced-inert shuffled control. These are
development thresholds, not publication tests.

## 9. Integrity and allowed conclusions

- Source, protocol, calibration records, job grid, and analysis code are
  content-addressed and frozen before the next stage.
- All attempts and all task results are retained. No task, sigma, draw, or
  scorer seed is removed after inspection.
- Outcome-independent implementation errors require a dated amendment and a
  complete rerun of affected matched arms.
- E4 cannot alter E3's failure, and exposed D2 cannot establish publication
  validity.
- A credible “alternative to ACID” claim ultimately requires a frozen
  multi-seed method, a matched ACID implementation, a simpler deterministic
  inverse control, a flow-energy control, fresh isolated evaluation, confidence
  intervals, latency, and evidence that the diffusion-specific component—not
  arbitrary verifier capacity or calibration—caused the gain.

The honest terminal outcomes are therefore: stop at a failed mechanism gate;
report a post-hoc development signal that still requires confirmation; or,
only after new untouched data, support a scoped alternative-to-ACID claim.
