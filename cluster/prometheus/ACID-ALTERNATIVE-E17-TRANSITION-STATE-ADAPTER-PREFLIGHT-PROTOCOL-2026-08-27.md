# E17 action-conditioned transition-state adapter preflight protocol

Date frozen before cache generation, training, or role-1 adapter output: 27 August 2026

Role: outcome-informed P1 infrastructure preflight only

Planner or confirmation status: not authorized by this document

## 1. Why this separate preflight exists

E15 and E16 remain failed and immutable. E16 reproduced the exact E15
seed-7201 VAD banks and found substantial oracle headroom for reranking a
far-ranked shortlist. Its frozen latent-only state adapter passed PushT but
failed Cube, so E16 Stages B and C were correctly blocked.

The evidence authorizing this preflight is pinned by:

- E16 Stage-A audit SHA-256
  `1eea0b08254b1de721f3db3c2106f51cfad825a27a5997134c5cbe2e34aea257`;
- E16 task-first table SHA-256
  `790e7b7074cb4fb553c30a658548c132177380f72c962cb491ddcec307ff7773`;
- E16 PushT adapter summary SHA-256
  `d1cdb460c46f34119b3f2d25ae25e8626814f7ff5d09cf2931c430471e7f4e66`;
  and
- E16 Cube adapter summary SHA-256
  `791593d4c9cf01647d47d28809ef552c78854661c7ed0772edc4db390e33b210`.

E17 asks only whether the missing interface can be made accurate by providing
the information a one-chunk transition actually depends on:

> Can a fixed action-conditioned model predict the next standardized
> low-dimensional state from the current state, current Le-WM latent, the
> bounded first action chunk, and Le-WM's predicted terminal latent?

This is infrastructure for the same conservative two-stage continuation idea.
It is not a new action proposer, not a latent subgoal, not a path critic, and
not full-horizon trajectory diffusion.

## 2. Evidence firewall

Only already exposed E15 P1 development data may be used. The immutable E15
episode-disjoint role-0 rows train the adapter. After this protocol is frozen,
the deterministic builder transforms and seals role-0 and role-1 features
without fitting a model or computing a validation metric. The training program
opens only role-0 cache payload until the final EMA checkpoint is written; it
opens the sealed role-1 payload once afterward for the fixed P1 gate. There is
no validation-based early stopping, checkpoint selection, architecture
selection, threshold selection, or retry.

E17 must not generate, open, hash, or consume D5, metric-bearing D3 or D4
artifacts, P3, P4, C1, or I1. It must not read P2 outcomes. A passing adapter
does not create a planner result; it authorizes only drafting a separately
named and newly frozen conservative continuation study.

## 3. Frozen inputs and examples

Tasks are PushT and Cube. For each task, the builder verifies the released
Le-WM checkpoint, raw expert dataset, E15 P1 cache, latent file, manifests, and
all hashes already pinned by `gdp_cem_e15_specs.py`.

One example is retained for each unique `(role, source_index, tau)` key, where
`tau` is 15, 20, or 25 primitive actions. Duplicate E15 rows with different
far-goal offsets must agree exactly on the source, local target, bounded action
prefix, current state, episode, and step before they can be collapsed. Role-0
and role-1 episodes remain disjoint.

For every retained row:

1. take the E15 train-standardized current CLS latent and current state;
2. take the E15 smoothly bounded raw action prefix, padded to 25 primitive
   actions, plus its fixed active mask;
3. transform that bounded prefix through the released planner scaler;
4. roll it once through the frozen released Le-WM for exactly `tau` actions;
5. standardize the predicted terminal CLS latent with E15's role-0 latent
   statistics; and
6. read the true raw state at `source_step + tau`, verify episode/step and
   latent-row alignment, then standardize it with E15's role-0 state
   statistics.

The builder is a deterministic feature transformation, not a fitted model.
Its cache contains role-0 and role-1 features in role order and is sealed by a
manifest and SHA-256 before training begins.

The supervised actions are expert P1 prefixes because counterfactual generated
actions do not have observed next-state labels. This limits what a pass means:
it establishes an interface on held-out expert transitions, not accuracy for
arbitrary off-support planner proposals.

## 4. Frozen model

The input vector concatenates, in this order:

1. standardized current latent `z_t` (192);
2. standardized predicted terminal latent `z_hat_(t+tau)` (192);
3. their difference `z_hat_(t+tau) - z_t` (192);
4. standardized current low-dimensional state;
5. the flattened 25-step bounded raw action tensor;
6. the 25-element action-active mask as floats; and
7. a three-way one-hot code for `tau in {15,20,25}`.

The task-specific input dimension is therefore
`576 + state_dim + 25*action_dim + 25 + 3`.

The network is fixed as:

```text
LayerNorm(input_dim) -> Linear(input_dim,512) -> SiLU
three residual blocks, each:
    LayerNorm(512) -> Linear(512,512) -> SiLU -> Linear(512,512)
    output = (input + block_output) / sqrt(2)
LayerNorm(512) -> Linear(512,state_dim)
predicted_next_state = current_state + predicted_standardized_residual
```

There is no dropout, stochastic-depth, auxiliary loss, ensemble, goal input,
far-horizon input, or validation-selected component.

## 5. Frozen training

One model is trained independently per task with:

- seed 8171;
- MSE on standardized next state;
- AdamW with learning rate `1e-3`, betas `(0.9,0.999)`, and weight decay
  `1e-4`;
- batch size 1024;
- 30,000 updates;
- 1,000-step linear warmup followed by cosine decay;
- global gradient-norm clipping at 1.0;
- BF16 autocast;
- EMA 0.999; and
- deterministic PyTorch algorithms and fixed batch-generator streams.

The scientific checkpoint is the final EMA at update 30,000. No intermediate
checkpoint is evaluated on role 1.

## 6. Frozen role-1 gate

After the final checkpoint exists, report the model and the copy-current
baseline separately for each task and for each `tau`. Metrics are standardized
RMSE, per-coordinate RMSE, per-coordinate R-squared, median coordinate
R-squared, and per-example RMSE quantiles.

A task passes only if all of the following hold on its unique role-1 examples:

1. every prediction and metric is finite;
2. overall standardized RMSE is at most 0.50;
3. maximum coordinate standardized RMSE is at most 0.85;
4. median coordinate R-squared is at least 0.50;
5. model RMSE is at most 90% of copy-current RMSE; and
6. for each `tau` in 15, 20, and 25, RMSE is at most 0.65 and median coordinate
   R-squared is at least 0.35.

The preflight passes only if both tasks pass. A failure is a scientific
interface failure and cannot be rescued by retraining, changing gates, adding
capacity, or selecting another seed on the same role-1 data.

## 7. Reporting and stopping

The aggregate analyzer verifies every cache/model checksum, input and protocol
hash, final-step identity, role ordering, no-validation-before-checkpoint flag,
and protected-evidence flags before reading the two summaries. It reports
task-first and `tau`-first results and records one of:

- `adapter_preflight_passed_both_tasks`; or
- `stop_transition_adapter_preflight_failed`.

If both tasks pass, the next action is to draft—not run—a separately frozen
matched continuation protocol. That future study must keep VAD, diagonal
Gaussian, and direct GMM continuation mechanisms identical; include greedy
VAD rollout-count controls and published-equation SAGE; use fresh P2 starts;
and keep full-horizon trajectory diffusion outside scope.

If either task fails, this line stops. E17 never automatically launches a
planner evaluation or consumes protected evidence.
