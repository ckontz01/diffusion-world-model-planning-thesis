# E10M multiseed pure velocity-diffusion P1 protocol

Date fixed before E10M execution: 2026-08-17  
Role: fixed-configuration P1 replication after E10V  
Forbidden inputs: D2 may not be reused; D3, C1, and I1 remain sealed

## Immutable prerequisite and fixed hypothesis

The immutable E10V aggregate is
`/lustreFS/data/superworld/ckontzias/thesis/results/acid-alternative/gdp-cem-e10v-p1/analysis/job-297780/summary.json`,
SHA-256
`5d23323681904fe369afcb4796976782cd6e4068b90fbc0e0d163e35092bacd9`.
Exactly one configuration passed all eight frozen E10V gates:

- true treatment: `vp_true_k05_g015`;
- deterministic velocity-DDIM evaluations: `5`;
- classifier-free guidance scale: `1.5`.

E10M does not reopen the E10V grid. It asks whether that exact pure-diffusion
configuration repeats across model seeds and new P1 contexts against
seed-matched shuffled-goal, unconditional, and diagonal-Gaussian controls.
There is no Gaussian anchor, ACID cost, verifier, success model, or protected
outcome in the treatment.

## Models and seeds

Retain the immutable seed-6101 E10V `vp_true` and `vp_shuffled_goal` models and
the immutable seed-6101 E7P `gaussian_true` model. Train new task-specific models
for seeds `6102` and `6103` under exactly three conditions:

1. `vp_true`;
2. `vp_shuffled_goal` using the same frozen within-role goal derangement; and
3. `gaussian_true` using the capacity-matched conditional diagonal-Gaussian
   architecture and NLL objective.

Velocity models retain the E10V architecture, 100-level cosine schedule,
velocity target, learned null goal, classifier-free goal-dropout probability
`0.15`, P1-training standardizers, optimizer, 30,000 steps, EMA, and precision.
Gaussian models retain the same backbone, action representation, optimizer,
30,000 steps, EMA, and precision, with diagonal log standard deviation clamped
to `[-5, 2]`.

Within a task and seed, all conditions use the same initialization namespace,
training-row order, and validation rows. True and shuffled velocity conditions
also use identical diffusion noise, timesteps, and dropout masks. Only the goal
pairing differs between the velocity conditions.

Each new model chooses its checkpoint on the exact 8,192 E10V checkpoint rows.
Velocity checkpoints minimize their assigned conditional velocity MSE;
Gaussian checkpoints minimize conditional diagonal-Gaussian NLL. Numeric
objectives are never compared across model families.

## Fresh fixed confirmation rows

Reconstruct all prior validation sets exactly: E7P checkpoint rows, E7P
selection rows, E8A rows, E10V checkpoint rows, and E10V final-selection rows.
Exclude their union. From the remaining P1-validation role, select 1,024 rows
without replacement using the first 64 SHA-256 bits of
`gdp-e10m-confirmation|task=<task>|seed=2026081708` as the NumPy seed. Record
every set hash and require zero overlap with all exclusions.

All three model seeds and every control use these identical confirmation rows.
The retained seed-6101 checkpoint payloads keep their historical E10V
row-selection metadata; the E10M evaluator must ignore that historical
evaluation-row field and explicitly apply the new E10M confirmation rows to
all seed-6101, seed-6102, and seed-6103 candidate banks.
The true recorded action is diagnostic only and is never supplied to a proposal
model.

## Fixed proposal evaluation

For every task, model seed, and confirmation context:

- draw 300 initial standard-normal action trajectories from a frozen
  seed/task/row namespace;
- generate the true and shuffled banks with exactly five deterministic
  velocity-DDIM evaluations and guidance scale 1.5;
- generate the same true model's unconditional bank with scale zero from the
  identical initial noise;
- generate 300 candidates from the seed-matched conditional diagonal Gaussian;
- inverse-standardize and apply the frozen P1-training robust bounds;
- evaluate each bank once through the exact cached-latent five-macro Le-WM
  rollout and select only by released terminal latent goal cost.

True, shuffled, and unconditional velocity banks share the same initial noise
within seed/task/context. Different model seeds have independent predeclared
namespaces. No configuration, guidance, denoising count, proposal fraction,
task, or control is searched in E10M.

## Metrics and replication gate

Report per-task medians for each model seed and equal-task means of those
medians for selected-action MSE, oracle-action MSE, minimum Le-WM goal cost,
candidate variance, unique candidates, robust-boundary fraction, generation
time, and rollout time. Also report equal-seed means and the full per-seed
contrasts.

A model seed passes only if all conditions hold:

1. true velocity has lower equal-task selected-action MSE than shuffled
   velocity and seed-matched Gaussian;
2. true velocity has lower equal-task oracle-action MSE than both;
3. true velocity has lower equal-task minimum goal cost than both;
4. true velocity beats its same-model unconditional bank on equal-task
   selected-action MSE and minimum goal cost;
5. true velocity has lower selected-action MSE than both learned controls on at
   least two of three tasks;
6. true velocity has lower minimum goal cost than both controls on at least two
   tasks; and
7. every task has finite positive variance, at least 285 unique candidates,
   and boundary fraction no more than 0.05 above the seed-matched Gaussian.

The E10M replication passes only if every seed `6101`, `6102`, and `6103`
passes all seven conditions, all equal-seed treatment contrasts have the
correct sign within every seed, all equal-seed mean contrasts have the correct
sign, and all row-isolation, lineage, deterministic-sampling,
exact-rollout, shape, finiteness, and hash checks pass.

Passing authorizes only writing and auditing a separately frozen untouched-data
protocol comparing pure velocity diffusion with ACID and all controls. It does
not itself authorize D3/C1/I1 access or a claim. Failure stops this exact pure
diffusion configuration; no E10M result may be rescued by changing a seed,
task, metric, row, guidance scale, denoising count, or gate after inspection.
