# ACID-alternative v2 residual-diffusion pilot protocol

Date frozen: 2026-08-16 (Asia/Nicosia)  
Role: post-v1 architectural development; **not confirmation**

## 1. Why this new attempt exists

The v1 DTV and both frozen post-v1 score-only rescues have now been observed.
The scalar density-ratio E0 result is at
`job-297478/summary.json`, SHA-256
`aa03059c79a07f9d9335723de9688ff3e25618e7c70e3889020d2f221768a18f`.
The prediction-guidance E1 result is at `job-297481/summary.json`, SHA-256
`ab4d4d8ad6cb72674825d7b8a649371536d27e23505821c69f8d2dbaa5feed8e`.

E1 showed that averaging eight noise draws genuinely improves the original
DTV's equal-task rank correlation, from `0.15248` to `0.16859`, with paired
95% CI `[0.00516, 0.02745]` for the improvement. It did not establish the
desired mechanism: the selected true-action score (`0.16859`) was slightly
worse than its shuffled-action null (`0.17189`), Reacher remained weak
(`0.04813`), and the deterministic forward verifier remained stronger
(`0.21978`).

The original P1 validation results localize the likely cause. The epsilon
denoiser can infer injected noise from a lightly corrupted next latent and
therefore has a shortcut that does not require the action. This is especially
severe on Reacher (about `0.55` true-versus-permuted action accuracy for DTV,
versus about `0.95` for the matched forward verifier).

This protocol permits exactly one architectural response to that diagnosis:
train a diffusion model to reconstruct a heavily corrupted, standardized
latent **transition residual**, use classifier-free action conditioning, and
add a fixed action-contrastive auxiliary loss. This is a new model, not a
reinterpretation of v1. Its D1 evaluation remains exploratory because D1
outcomes are already known.

C1 and I1 remain prohibited. They may not be read, scored, executed, or used
for model selection. A successful pilot must still pass a three-seed expansion
and a separately frozen fresh-data D2 before any confirmation is considered.

## 2. Permitted data

Training and checkpoint selection use only the existing P1-train and P1-val
transition caches for PushT, Reacher, and Cube. Those caches contain frozen
Le-WM latents and five-primitive-action blocks and explicitly exclude I1.

The architectural pilot trains seed `6101` only, with one true-action model and
one shuffled-action control per task. After the P1 gate, the already-completed
D1 same-candidate artifacts may be used for exploratory ranking and
candidate-selection diagnostics. No environment interaction is performed in
this pilot because all 300 candidates per D1 pool already have common physical
executions.

## 3. Frozen model and representation

Let `z_t` and `z_next` be latents standardized by the existing P1-train latent
mean and standard deviation. Define the transition residual

`delta = z_next - z_t`.

Compute a second mean and population standard deviation for `delta` using only
P1-train pairs, and train on

`x = (delta - delta_mean) / delta_std`.

All residual dimensions must have standard deviation greater than `1e-6`; a
failure is fatal rather than silently clamped.

The model predicts clean `x` from:

- standardized current latent `z_t`;
- the normalized five-action block already stored in the transition cache;
- noisy residual `x_sigma = x + sigma * epsilon`;
- sinusoidal `log(sigma)` embedding;
- an explicit binary `condition_present` flag.

Architecture: one input projection, width `384`, three residual MLP blocks with
expansion `2`, SiLU activations, LayerNorm, a `64`-dimensional sinusoidal noise
embedding, and a latent-width output. This differs from v1 DTV only by the
conditioning flag and target parameterization. Its trainable parameter count
must remain within 2% of v1 DTV and the frozen deterministic-forward control.

## 4. Frozen training objective

For every minibatch, sample `sigma` independently and uniformly from the
discrete set `{0.25, 1.0, 4.0}` and sample standard-normal `epsilon`. The base
objective is mean squared clean-residual reconstruction error.

Classifier-free conditioning dropout is exactly `0.20`. Dropped examples use
an all-zero action vector and `condition_present = 0`; retained examples use
the stored action and `condition_present = 1`.

For examples with `sigma >= 1.0`, also evaluate the same noisy residual with a
fixed-point-free within-minibatch action permutation. Let `e_true` and
`e_wrong` be per-example clean-residual MSE under the true and permuted action.
The auxiliary term is

`mean(relu(0.05 + e_true - e_wrong))`.

The total loss is

`base_x0_loss + 0.50 * action_contrastive_loss`.

The shuffled-label control uses the identical architecture, optimizer, random
streams, dropout, sigma schedule, and contrastive objective, but its training
action lookup is a precomputed single-cycle derangement of P1-train pairs. Its
validation selection action uses a separate fixed derangement of P1-val pairs.

Optimization is fixed as follows:

- seed: `6101`;
- 100,000 optimizer steps;
- batch size: `512`;
- AdamW, peak learning rate `1e-4`, betas `(0.9, 0.999)`, weight decay `1e-4`;
- 1,000-step linear warmup followed by cosine decay;
- gradient-norm clip `1.0`;
- bfloat16 autocast on CUDA;
- validation every 5,000 steps on at most 100,000 P1-val pairs;
- immutable random seeds derived and recorded separately for sampling, noise,
  dropout, action permutation, and validation.

Checkpoint selection minimizes the same validation composite objective used in
training. Every validation also reports conditional reconstruction cost for
true and independently permuted actions, classifier-free unconditional cost,
pairwise true-action accuracy overall and separately at each of the three
sigmas, and the mean `wrong - true` margin.

## 5. P1 gate before D1 scoring

All six seed-6101 models must finish with finite artifacts and noncollapsed
score distributions. The true-action model advances to D1 scoring only if, in
every task:

1. overall true-versus-permuted P1-val pairwise accuracy is at least `0.70`;
2. its mean `wrong - true` reconstruction margin is positive;
3. its accuracy exceeds the matched shuffled-label model by at least `0.10`;
4. its accuracy at `sigma = 4.0` is at least `0.75`;
5. reloading the selected checkpoint exactly reproduces its validation result.

If this gate fails, D1 scoring is not used to rescue the model.

## 6. Frozen D1 pilot score

For each stored D1 transition residual, evaluate the selected model at
`sigma in {0.25, 1.0, 4.0}` with eight deterministic common noise draws. The
noise bank is derived from task, seed, sigma, and draw by a recorded SHA-256
rule. Conditional and unconditional predictions share each noisy input.

Two classifier-free guidance values are permitted:

`x_hat_g = x_hat_unconditional + g * (x_hat_conditional - x_hat_unconditional)`

for `g in {1.0, 1.5}`. Candidate cost is the mean squared error between
`x_hat_g` and the clean standardized residual, averaged over horizon, latent
dimensions, sigmas, and noise draws. The shuffled-label model produces the
matched null using the identical computation.

The primary mechanism endpoint is within-pool Spearman correlation between
candidate cost and physically realized standardized rollout RMSE. Select the
guidance value with larger equal-task mean correlation; a tie within `0.005`
chooses `g = 1.0`. Report every task, pool, and the seed-6101 result.

Uncertainty uses 100,000 pool-cluster bootstrap repetitions with seed
`2026081611`, resampling each task's 24 starts independently and weighting the
three tasks equally.

For candidate-selection diagnostics, combine the score with B0 goal cost using
the existing spread-adaptive formula at exactly `lambda in {0.005, 0.07}`.
Report standardized rollout RMSE, task distance when present, environment
success, and candidate-index agreement with B0, v1 raw DTV, ACID, and forward.

## 7. Gate for expanding to seeds 6102 and 6103

The selected pilot score advances only if all of the following hold:

1. task-level rank-correlation point estimates are positive in all tasks;
2. the equal-task correlation 95% lower bound is above zero;
3. the paired improvement over seed-6101 v1 raw DTV has a 95% lower bound above
   zero;
4. the paired improvement over the seed-6101 shuffled-label residual-diffusion
   null has a 95% lower bound above zero;
5. Reacher's point estimate is at least `0.075`;
6. the equal-task point-estimate gap to seed-6101 forward is no worse than
   `-0.030`, with no task gap worse than `-0.075`;
7. at `lambda = 0.005`, selected-candidate success is not below v1 raw DTV and
   selected standardized RMSE is not above v1 raw DTV.

If the pilot passes, train seeds `6102` and `6103` with no changes, rerun the
same analysis across all three seeds, and require the corresponding full
three-seed gates before freezing a fresh D2 protocol. D2 and any later C2 must
use data whose episode and tuple isolation is proven before outcomes are read.

## 8. Stop and reporting rules

- No additional width, depth, target, sigma, dropout, contrastive weight,
  margin, guidance, lambda, or seed may be tried under this protocol.
- All true and shuffled training runs, checkpoints, validation diagnostics,
  and D1 scores attempted under this protocol are retained and reported.
- A failure is a failure of this residual/classifier-free/contrastive design;
  it may not be hidden by pooling tasks or dropping Reacher.
- A success is only permission to expand development. It is not evidence from
  fresh confirmation data and cannot support the final publication claim.
- C1/I1 remain untouched throughout.

