# E8A P1-only Gaussian-anchored diffusion-refinement protocol

Date frozen: 2026-08-17  
Role: P1-only method rescue after E7P; no planner-success outcome access  
Forbidden inputs: D2, D3, C1, and I1 data or outcomes

## Motivation and fixed prior evidence

The accepted E7P aggregate is
`/lustreFS/data/superworld/ckontzias/thesis/results/acid-alternative/gdp-cem-e7p-selection/analysis/job-297717/summary.json`,
SHA-256
`bcd49f6fa7b7d1b03d8f95b4d46001e08b97c4725b43a55a953afc4ebe25544d`.
It stopped pure-noise GDP before D2. True epsilon diffusion beat its shuffled-goal
control in the equal-task aggregate, but lost badly to the conditional diagonal
Gaussian. Direct diffusion variance was far above the Gaussian and clean-action
reconstruction error was large despite low epsilon loss.

The diagnosed mechanism is the near-zero terminal signal-to-noise ratio of the
100-level cosine schedule: few-step DDIM from pure noise amplifies epsilon error.
E8A does not loosen the E7P gate or reuse its failed bank. It tests a different,
predeclared hypothesis:

> A moderate-noise epsilon-diffusion projection can add joint temporal/action
> structure to an already competent conditional-Gaussian proposal without the
> unstable pure-noise endpoint.

The method is **Gaussian-anchored diffusion refinement (GADR)**. It uses the
existing immutable seed-6101 E7P true, shuffled-goal, and Gaussian checkpoints;
there is no retraining in E8A.

## Fresh P1-validation contexts

For each task, reconstruct and exclude:

1. the 8,192 checkpoint-selection validation rows used by E7P training; and
2. the 256 accepted E7P proposal-selection rows.

From the remaining P1-validation sequence rows, select 512 rows without
replacement using the unsigned integer represented by the first 16 hexadecimal
digits of SHA-256 over
`gdp-cem-e8a-selection|task=<task>|seed=2026081703` as the NumPy seed.
All E8A conditions and configurations use these identical rows. The real
25-action sequence is diagnostic only and is never supplied to a model.

## Candidate construction

All work occurs in the E7P model-standardized primitive-action coordinates
until the final inverse transform.

For each context:

1. evaluate the conditional diagonal-Gaussian model once;
2. draw a complete 300-candidate Gaussian noise tensor from a fixed per-context
   namespace and form the base bank;
3. overwrite candidate zero with the predicted conditional mean;
4. clamp the base bank to the checkpoint's P1-train 0.001/0.999 robust bounds;
5. for each restart level, draw one complete 300-candidate standard-normal
   diffusion noise tensor from a separate fixed namespace;
6. forward-noise every base candidate to cosine-schedule timestep `r`;
7. either project directly to predicted clean actions with one epsilon-model
   evaluation at `r`, or reverse from `r` to zero with the frozen multi-step
   deterministic epsilon-DDIM grid, conditioned on the true-goal or
   shuffled-goal denoiser;
8. clamp every predicted clean action to the same standardized robust bounds
   before the next DDIM update and clamp the final result once more;
9. preserve base candidate zero and overwrite a fixed subset of candidates
   1 through 299 with the corresponding refined candidates.

The true and shuffled denoisers receive the same actual current/goal latents,
base candidates, forward noise, and candidate slots. Their training condition
is the only intended difference. The unrefined conditional-Gaussian bank is the
primary non-diffusion control.

## Frozen grid

- candidates: 300;
- cosine restart timestep: `{10, 20, 40}` out of 100;
- deterministic reverse evaluations: `{1, 5, 10}`. One evaluation means the
  direct predicted-clean projection at the restart timestep; larger counts use
  the rounded DDIM grid from the restart timestep through zero;
- refined fractions: `{0.25, 0.50, 0.75, 1.00}`;
- refined count: `round(299 * fraction)` candidates, starting at index one;
- candidate zero: always the unrefined conditional-Gaussian mean;
- world-model evaluation: one exact cached-latent five-macro Le-WM rollout per
  candidate bank, using the released summed terminal latent goal cost.

Inference configurations with duplicate rounded DDIM time indices are invalid.
For a fixed task, context, and restart timestep, all denoiser-evaluation counts
reuse the same forward-noise tensor; true and shuffled models also reuse it
exactly. Different restart timesteps use separate fixed namespaces.
The result must record the RNG namespace templates; hashes and counts for the
validation, excluded, available, and selected row sets; hashes for every
normalization tensor and the cosine schedule; every model/checkpoint hash; and
the real-stack equivalence and determinism checks.

## Metrics

For each task/configuration and the base Gaussian, report medians over the 512
fixed contexts for:

1. selected-action MSE of the minimum-Le-WM-cost candidate;
2. oracle minimum action MSE;
3. minimum Le-WM terminal goal cost;
4. candidate variance and unique-candidate count at `1e-4` precision;
5. fraction of standardized primitive coordinates exactly equal to either robust
   clipping boundary after the frozen clamp;
6. refinement displacement MSE from the paired Gaussian base;
7. proposal-generation and Le-WM-rollout latency.

Aggregate only as an equal-task mean of per-task medians. Never pool contexts
across tasks.

## Frozen selection and advancement rule

A `(restart, reverse_evaluations, fraction)` configuration is eligible only if:

- true GADR has lower equal-task selected-action MSE than both shuffled GADR
  and the unrefined conditional Gaussian;
- true GADR has lower equal-task minimum Le-WM goal cost than both controls;
- true GADR has lower equal-task oracle-action MSE than shuffled GADR and is no
  more than 2% above the unrefined Gaussian oracle-action MSE;
- true GADR has lower selected-action MSE than both controls on at least two of
  three tasks;
- true GADR has lower minimum goal cost than both controls on at least two of
  three tasks;
- its boundary-clipped fraction is no more than 0.05 above the unrefined
  Gaussian on the equal-task scale;
- the per-task median variance is finite and positive, the per-task median
  unique-candidate count is at least 285 of 300 on every task, and every
  lineage/equivalence/determinism check passes.

Among eligible configurations select lexicographically by:

1. lowest true-GADR equal-task selected-action MSE;
2. lowest true-GADR equal-task minimum goal cost;
3. fewer reverse denoiser evaluations;
4. lower restart timestep;
5. smaller refined fraction.

If none is eligible, E8A stops before D2. A separately frozen stable
velocity-prediction study may then be attempted on P1, but E7P or E8A may not be
retrofitted and no D2/D3 outcome may be opened. Passing E8A authorizes only a
new, separately frozen exposed-D2 development diagnostic. It authorizes no
claim and no D3, C1, or I1 access.
