# E7P P1-validation proposal-selection protocol

Date frozen: 2026-08-17  
Role: P1-validation-only mechanism qualification and inference selection  
Outcome access: no D2, D3, C1, or I1 data or outcomes may be read

## Fixed evaluation set

For each task, select 256 P1-validation sequence rows without replacement from
the immutable E7P cache using the first 64 bits of SHA-256 over
`gdp-cem-e7p-selection|task=<task>|seed=2026081702` as the NumPy RNG seed.
All model families and configurations use the same rows.

The real standardized 25-action sequence is a diagnostic reference only. It is
never supplied to a proposal model.

## Exact latent rollout

Load the frozen released Le-WM checkpoint for the task. Starting from cached
`z_t`, reproduce its five-macro autoregressive predictor rollout using each
candidate's five planner-coordinate macro actions. Compare the terminal
predicted latent with cached `z_(t+25)` using the released summed squared latent
goal cost. This avoids pixels while using the same frozen action encoder,
predictor, history truncation, and terminal latent criterion as closed-loop
planning.

The implementation must pass a separate real-stack equivalence test against
the released rollout on encoded P1 frames before its metrics are accepted.

## Candidate banks

- Candidate count: 300 per context.
- Diffusion DDIM inference-step candidates: `{5, 10, 20}`.
- Proposal fractions for matched CEM iteration-1 pools:
  `{0.25, 0.50, 0.75, 1.00}`.
- The CEM mean candidate is preserved for matched pools. The remaining slots
  are filled by the fixed fraction of proposals and ordinary standard-normal
  Gaussian candidates.
- GDP-Select banks contain 300 learned proposals and no mean or CEM Gaussian
  candidate.
- Candidate seeds are derived from task, condition, context row, DDIM step
  count, and a fixed namespace. The CEM Gaussian and learned-proposal RNG
  namespaces are separate.
- True diffusion and shuffled-goal diffusion receive the same true current and
  goal condition at evaluation. Their training condition is the only intended
  difference.
- All learned samples are inverse-standardized into planner coordinates and
  clipped to the P1-train 0.001/0.999 primitive-action quantiles recorded in
  the checkpoint.

## Metrics

For each context and candidate bank, record:

1. minimum Le-WM terminal goal cost;
2. action MSE between the minimum-goal-cost selected candidate and the real
   P1-validation action sequence;
3. oracle minimum action MSE over the bank;
4. mean per-coordinate candidate variance;
5. number of unique candidates after rounding planner coordinates to `1e-4`;
6. proposal-generation and Le-WM-rollout latency.

Report per-task medians and equal-task means of per-task medians. Do not pool
all contexts across tasks.

## Frozen selection rules

### DDIM steps for GDP-Select

A DDIM step count is eligible only if true diffusion has both lower equal-task
selected-action MSE and lower equal-task oracle-action MSE than shuffled-goal
diffusion at that step count. Among eligible counts, select the count with the
lowest true-diffusion equal-task selected-action MSE. Break exact ties in favor
of fewer DDIM steps. If none is eligible, the diffusion-specific P1 gate fails.

### Fraction for matched GDP-CEM

At the selected DDIM step count, identify the minimum true-diffusion equal-task
selected-action MSE across the four matched-pool fractions. Select the smallest
fraction whose selected-action MSE is no more than 2% above that minimum and
whose equal-task minimum Le-WM goal cost is no higher than the Gaussian-only
iteration-1 pool. If no fraction qualifies, the matched GDP-CEM P1 gate fails.

## Advancement gate

At least one integration may advance to a separately frozen, exposed-D2
one-seed diagnostic only if all of the following hold on P1 validation:

- true diffusion beats shuffled-goal diffusion on selected-action MSE and
  oracle-action MSE at the selected DDIM step count;
- true diffusion beats the conditional diagonal Gaussian on selected-action
  MSE;
- true diffusion beats each learned control on selected-action MSE in at least
  two of three tasks;
- true diffusion candidate variance is finite and positive on every task;
- at least 95% of its 300 candidates remain unique on every task;
- all lineage, exact-rollout equivalence, determinism, shape, and finiteness
  checks pass.

Failure stops the proposal branch before D2 unless a new scientific mechanism
and new protocol are written without consulting protected outcomes. Passing
authorizes only exposed-D2 development, never D3 or a claim.

