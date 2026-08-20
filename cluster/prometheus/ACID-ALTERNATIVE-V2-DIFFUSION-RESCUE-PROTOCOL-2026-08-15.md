# ACID-alternative v2 diffusion-rescue protocol

Date frozen: 2026-08-15 (Asia/Nicosia)  
Role: post-v1 development protocol; **not** a v1 amendment or confirmation protocol

## 1. Scientific boundary

The v1 D1 result is already known. In particular, the primary multiscale
diffusion transition verifier (DTV) did not establish itself as a robust
alternative to ACID, while the predeclared `lambda = 0.005` sensitivity was
encouraging. The authoritative v1 report is
`ACID-ALTERNATIVE-D1-RESULT-2026-08-15.md`, SHA-256
`6f6dbd01d33b82700fcc6f5816cc2e7b60c416120a040a2a58899758f700cc58`.

Everything in this protocol is consequently exploratory/development work. No
result below may be relabelled as a v1 primary result, and neither C1 nor I1 may
be opened, scored, executed, or inspected. A successful rescue must later be
frozen and tested on fresh data in a new confirmation stage; C1 will not be
repurposed for that stage.

The purpose is to test one concrete failure hypothesis: raw denoising error is
dominated by transition difficulty that is also visible to an action-ablated
model, obscuring the action-conditional support signal. The proposed rescue is
therefore a conditional-versus-marginal diffusion density contrast, not an
arbitrary retuning of the existing score.

## 2. Immutable E0 inputs

E0 reuses the completed D1 same-candidate artifacts for PushT, Reacher, and
Cube. Each task contains 24 independently selected start pools, 300 candidates
per pool, three scorer-training seeds (`6101`, `6102`, `6103`), a common frozen
world-model rollout per candidate, and one common physical execution per
candidate. The following stored quantities are permitted:

- B0 goal cost;
- true, shuffled-action, and action-ablated diffusion costs;
- true and shuffled-action deterministic-forward costs;
- faithful ACID and learned-reachability costs;
- predicted and physically executed latent trajectories;
- task distances and environment success labels already stored by D1.

No model is refit in E0. Input manifests and artifact hashes must validate, and
the implementation must reproduce the published v1 raw-DTV, forward, and ACID
within-pool rank correlations before emitting any new result.

E0 is explicitly outcome-selected follow-up analysis because the aggregate D1
results were inspected before this protocol. It can select a candidate design
for fresh development, but cannot support a publication claim on its own.

## 3. Frozen algebraic score family

All transforms are performed separately within each task, start pool, and
training seed over the same 300 candidates. Let:

- `C` be true-action DTV raw denoising cost;
- `S` be shuffled-action DTV raw denoising cost;
- `U` be action-ablated DTV raw denoising cost;
- `F` and `Fs` be true- and shuffled-action forward-verifier costs.

For a vector `x`, `z(x)` is its sample-mean-centered value divided by its sample
standard deviation (`ddof = 1`). `r(x)` is its exact stable midrank divided by
`N - 1`; ties receive their shared midrank. Any non-finite value or standard
deviation at or below `1e-8` invalidates the run.

The reference and eligible diffusion-rescue variants are:

| Label | Candidate cost | Role |
|---|---|---|
| `R0_raw` | `C` | v1 DTV reference only |
| `R1_z_ratio` | `z(C) - z(U)` | primary density-ratio candidate |
| `R2_rank_ratio` | `r(C) - r(U)` | calibration-robust ratio candidate |
| `G025` | `z(C) + 0.25 * (z(C) - z(U))` | scalar guidance diagnostic |
| `G050` | `z(C) + 0.50 * (z(C) - z(U))` | scalar guidance diagnostic |
| `G100` | `z(C) + 1.00 * (z(C) - z(U))` | scalar guidance diagnostic |
| `G200` | `z(C) + 2.00 * (z(C) - z(U))` | scalar guidance diagnostic |

`z(C) - z(S)` is computed as a diagnostic but is ineligible for selection
because a shuffled-label network is a null control, not a defensible deployed
component. The forward references are `F` and `z(F) - z(Fs)`.

Every eligible variant has a matched shuffled-label null obtained by replacing
`C` with `S` in its formula while retaining the same `U`. These nulls are not
eligible planner arms.

Lower values always mean more desirable candidates. For planner-selection
diagnostics, each score `q` is combined with B0 goal cost `J` as

`J + lambda * sd(J) / max(sd(q), 1e-8) * q`

at exactly `lambda in {0.005, 0.07}`. The former is the v1 sensitivity lead;
the latter is the v1 primary value. No other E0 lambda is permitted.

## 4. Frozen E0 analysis and selector

The primary mechanism endpoint is Spearman correlation between candidate cost
and physically realized standardized rollout RMSE. Correlations are computed
within each pool and scorer seed, then averaged within task. The headline mean
weights PushT, Reacher, and Cube equally.

Uncertainty uses 100,000 cluster-bootstrap repetitions. Start identity is
resampled independently within each task; all three scorer-seed measurements
for a selected start remain together. The bootstrap seed is `2026081517`.
Two-sided 95% percentile intervals are reported for levels and paired
contrasts. Task-level point estimates and intervals may never be replaced by a
pooled-only result.

Among `R1_z_ratio`, `R2_rank_ratio`, `G025`, `G050`, `G100`, and `G200`, select
the largest equal-task mean rank correlation. If multiple estimates are within
`0.005` of the maximum, choose the earliest in that listed order. This rule is
applied once and may not be revised after output is seen.

Also report, without using them to change the selector:

- the paired contrast to `R0_raw`;
- the paired contrast to the selected variant's matched shuffled null;
- the paired contrast to true forward verification;
- selected-candidate standardized RMSE, final/minimum task distance, and
  environment success at both frozen lambdas;
- candidate-selection agreement with B0, raw DTV, ACID, and forward;
- all per-task and per-seed results.

## 5. Promotion gate for a fresh v2 run

The selected E0 rescue advances only if **all** of the following hold:

1. its task-level rank-correlation point estimate is positive in all three
   tasks;
2. its equal-task rank-correlation two-sided 95% lower bound is above zero;
3. its paired improvement over `R0_raw` has a two-sided 95% lower bound above
   zero;
4. its paired improvement over its matched shuffled-label null has a two-sided
   95% lower bound above zero;
5. on Reacher its point estimate is at least `0.075` and at least `0.040`
   greater than `R0_raw`;
6. its equal-task point-estimate gap to the true forward verifier is no worse
   than `-0.030`, and no single-task gap is worse than `-0.075`;
7. at `lambda = 0.005`, its equal-task selected-candidate success is not below
   raw DTV and its equal-task selected standardized RMSE is not above raw DTV.

Failure is evidence against this particular density-ratio rescue, not proof
that every possible diffusion model is unsuitable.

## 6. Prediction-level guidance follow-up

The strongest fair follow-up, whether or not scalar E0 passes, is a single
predeclared recomputation on the same D1 trajectories using the frozen true,
shuffled, and action-ablated diffusion checkpoints. It must not retrain them.
For common noisy inputs and common noise `epsilon`, construct

`epsilon_g = epsilon_U + g * (epsilon_C - epsilon_U)`

and score mean squared `epsilon - epsilon_g`. The fixed grid is:

- guidance `g in {0.5, 1.0, 1.5, 2.0, 3.0}`;
- sigma set in `{(0.10, 0.25, 0.50), (0.25,)}`;
- noise draws in `{1, 8}`.

The first noise draw must exactly reproduce the corresponding v1 seed-derived
noise. Additional draws use an immutable, recorded seed derivation from scorer
seed, task, sigma, and draw index. The matched null replaces `epsilon_C` with
the shuffled-action prediction. The same selector, endpoints, bootstrap, and
promotion gates in Sections 4 and 5 apply across these 20 configurations, with
ties within `0.005` resolved by lower draw count, the multiscale sigma set,
lower `g`, then lexical label. This is an exploratory architecture diagnostic,
not confirmation.

## 7. Fresh-data requirement after promotion

If either frozen rescue family passes, its chosen formula and `lambda = 0.005`
are frozen before creating D2. D2 must use starts from development-designated
episodes never used in R0, legacy P2/P3/P4, D1, C1, or I1, verified by episode
and tuple manifests before execution. If the existing data cannot supply such
starts, new environment trajectories must be generated; protected partitions
must not be borrowed.

D2 will compare B0, faithful ACID, learned reachability, raw DTV, the chosen
diffusion rescue, and the capacity-matched deterministic forward verifier on
the same candidate pools, budgets, starts, seeds, and physical outcomes. Its
protocol and gates must be hashed before any D2 outcome is opened. A later
confirmation set, called C2, must remain unseen until the final v2 method is
frozen.

## 8. Stop and reporting rules

- No unlisted transform, lambda, sigma, guidance value, noise count, endpoint,
  task deletion, or pooling rule may be added to E0 after seeing its result.
- Every tried configuration is reported, including nulls and failures.
- Forward superiority cannot be hidden; it is central to whether the effect is
  diffusion-specific.
- If the rescue fails, the result is retained and the next architectural idea,
  if any, receives a new dated protocol before testing.
- C1/I1 remain untouched unless the user separately authorizes the already
  frozen v1 confirmation procedure. This v2 work never implies that authority.

