# E10V pure velocity-diffusion P1 protocol

Date fixed before E10V execution: 2026-08-17  
Role: post-E8D P1-only method development  
Forbidden inputs: D2 may not be reused; D3, C1, and I1 remain sealed

## Preserved prior result and scientific boundary

E8D is preserved rather than superseded. Its immutable exposed-D2 aggregate is
`/lustreFS/data/superworld/ckontzias/thesis/results/acid-alternative/gdp-cem-e8d-d2/analysis/job-297745/summary.json`,
SHA-256
`89d76ee15d4fa4420288dc5306f7f18565d39fa13c959a0c52168995b10e531f`.
True GADR refresh reached `0.9067` equal-task success versus reconstructed
ACID's `0.8800`, but Gaussian and shuffled-GADR refresh both reached `0.9000`.
The improvement therefore did not isolate diffusion. E10V was designed after
that exposed result and cannot use D2 again for selection or evidence.

The earlier E7P pure epsilon-diffusion proposal failed on P1 because few-step
DDIM sampling from the near-zero-SNR cosine endpoint amplified epsilon error.
E7P and E8A both explicitly permit a separately frozen stable
velocity-prediction study on fresh P1-validation rows. E10V tests:

> Can a goal-conditioned velocity-prediction diffusion model generate complete
> behavior-supported 25-action proposals directly from noise, without a
> Gaussian anchor or ACID cost, and beat Gaussian, shuffled-goal, unconditional,
> and epsilon-diffusion proposal controls?

Passing E10V authorizes only multi-model-seed P1 replication. It does not
authorize D2 reuse, fresh-data access, or a publication claim.

## Immutable P1 inputs and fresh rows

Use the exact E7P P1 train/validation sequence caches and referenced flat Le-WM
latent caches. Training examples remain the episode-level P1-training role.

For every task, reconstruct and exclude from the validation role:

1. the 8,192 E7P checkpoint-selection rows selected by
   `gdp-e7p-validation-rows|<task>|6101`;
2. the 256 accepted E7P proposal-selection rows selected by
   `gdp-cem-e7p-selection|task=<task>|seed=2026081702`; and
3. the 512 E8A rows selected after those exclusions by
   `gdp-cem-e8a-selection|task=<task>|seed=2026081703`.

From the remaining validation rows, select 8,192 E10V checkpoint rows without
replacement using the first 64 SHA-256 bits of
`gdp-e10v-checkpoint|task=<task>|seed=2026081706`. Exclude those rows and select
512 final E10V proposal-evaluation rows using the first 64 SHA-256 bits of
`gdp-e10v-selection|task=<task>|seed=2026081707`. Record hashes and intersection
counts for every set. Any overlap invalidates the study.

## Pilot models

Train task-specific seed-6101 models for exactly two conditions:

1. `vp_true`: current latent, true t+25 goal latent, and true 25-action sequence;
2. `vp_shuffled_goal`: the identical inputs except for the existing
   deterministic, nonzero within-role cyclic goal derangement.

Both use the E7P capacity-matched architecture: 192-dimensional standardized
latents; 25 primitive actions modeled jointly; width 512; four FiLM residual
blocks; and 128-dimensional sinusoidal time embedding. Actions use a P1-train
standardizer and P1-train 0.001/0.999 robust bounds.

The diffusion schedule is the exact 100-level cosine schedule. The network
predicts velocity
`v = sqrt(alpha_bar) * epsilon - sqrt(1-alpha_bar) * x0`, so clean-action
reconstruction is
`x0 = sqrt(alpha_bar) * x_t - sqrt(1-alpha_bar) * v` and remains stable at the
near-zero-SNR endpoint.

Classifier-free training drops the goal with probability `0.15`, replacing it
with one learned null-goal vector while preserving the current latent. The
dropout mask, diffusion timestep, and Gaussian noise use frozen independent RNG
namespaces. True and shuffled conditions use the same initialization, training
row order, diffusion noise, timesteps, dropout masks, and validation banks; the
goal pairing is their only intended training difference. No Gaussian proposal
model, ACID scorer, world-model loss,
success predictor, contrastive margin, or D2-derived target enters training.

## Fixed optimization

- AdamW, betas `(0.9, 0.999)`, weight decay `1e-4`;
- peak learning rate `2e-4`;
- 1,000-step linear warmup followed by cosine decay;
- batch size 1,024 and 30,000 optimization steps;
- gradient-norm clipping at 1.0;
- CUDA bfloat16 autocast with float32 velocity-MSE loss;
- EMA decay 0.999;
- validation every 1,000 steps on the fixed 8,192 fresh checkpoint rows;
- checkpoint chosen only by minimum conditional velocity MSE, with earlier-step
  tie breaking.

Validation also records unconditional MSE, deterministic alternate-pairing MSE,
clean-action reconstruction MSE, and the assigned-versus-alternate goal gap, but
these diagnostics do not choose checkpoints.

## Pure proposal generation

On the 512 fresh final P1 contexts, generate 300 complete action trajectories
directly from matched standard-normal noise. There is no conditional-Gaussian
initialization and no ACID or other verifier cost.

Use deterministic velocity-DDIM with inference-evaluation counts
`{5, 10, 20, 40}` and classifier-free guidance scales
`{0.0, 1.0, 1.5, 2.0, 3.0}`. Guidance is
`v_uncond + scale * (v_cond - v_uncond)`; scale zero is the same-model
unconditional control and scale one is ordinary conditional sampling. At each
reverse evaluation, reconstruct clean actions with the stable velocity formula,
clamp only that clean estimate to the P1-train robust bounds, derive the
consistent noise estimate, and take the deterministic DDIM update. Clamp the
final clean sample once more.

For each task, context, and inference count, true and shuffled models and every
guidance scale use the same initial noise bank. Existing immutable E7P
`gaussian_true`, `diffusion_true`, and `diffusion_shuffled_goal` checkpoints are
evaluated on the same fresh contexts as fixed non-velocity controls. The old
epsilon controls use their frozen 10-step sampler; the Gaussian uses one
300-candidate bank. The real action sequence is diagnostic only and is never
provided to a proposal model.

Every candidate bank is inverse-standardized to planner coordinates and
evaluated by one exact cached-latent five-macro Le-WM rollout. Selection uses
only the released terminal latent goal cost.

## Metrics and frozen gate

Report per-task medians and equal-task means of per-task medians for:

1. selected-action MSE of the minimum-Le-WM-cost candidate;
2. oracle minimum action MSE;
3. minimum terminal Le-WM goal cost;
4. candidate variance and unique candidates at `1e-4` precision;
5. robust-boundary fraction;
6. proposal generation and Le-WM rollout time.

A `(reverse evaluations, guidance scale)` velocity configuration is eligible
only if all conditions hold:

1. true velocity diffusion has lower equal-task selected-action MSE than
   shuffled velocity diffusion, the conditional Gaussian, and old true epsilon
   diffusion;
2. it has lower equal-task oracle-action MSE than those same controls;
3. it has lower equal-task minimum Le-WM goal cost than shuffled velocity and
   the conditional Gaussian;
4. it has lower selected-action MSE than both shuffled velocity and Gaussian on
   at least two of three tasks;
5. it has lower minimum goal cost than both on at least two tasks;
6. it beats the same true model's matched scale-zero unconditional bank on
   selected-action MSE and minimum goal cost;
7. every task has finite positive candidate variance, at least 285 unique
   candidates, and boundary fraction no more than 0.05 above Gaussian; and
8. all row isolation, lineage, stable-v oracle reconstruction, deterministic
   sampling, exact rollout equivalence, shape, finiteness, and hash checks pass.

Select eligible configurations lexicographically by lowest true selected-action
MSE, lowest true minimum goal cost, fewer reverse evaluations, and guidance
scale closest to 1.0. If none is eligible, stop pure diffusion before multi-seed
training or protected data. If one is eligible, freeze it and train seeds
6102/6103 on P1 only; all three model seeds must repeat the control advantages
before any separately proposed untouched-data study.

No configuration, scale, reverse count, task, metric, control, row, or gate may
be changed after E10V P1 results are inspected to rescue a failure.
