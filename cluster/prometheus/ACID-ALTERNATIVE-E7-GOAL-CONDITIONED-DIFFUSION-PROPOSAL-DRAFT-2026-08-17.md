# ACID-alternative E7 draft: goal-conditioned diffusion proposals for CEM

Date drafted: 2026-08-17  
Status: design draft; not yet frozen or authorized  
Data boundary: P1 and exposed D2 only during development; D3, C1, and I1 remain sealed

## Scientific hypothesis

The failed verifier studies used diffusion as a scalar anomaly score on futures
that Le-WM had already imagined. That asks a denoiser to do a job for which a
deterministic forward residual can be equally or more suitable. Diffusion's
specific advantage is instead joint, multimodal generation.

E7 tests a different mechanism:

> A goal-conditioned diffusion model trained on real P1 action sequences can
> keep CEM's search inside multiple plausible action modes, reducing world-model
> exploitation by construction and matching or exceeding ACID without using an
> action-consistency penalty.

The method is provisionally named **goal-conditioned diffusion-proposal CEM
(GDP-CEM)**. This name is descriptive only and is not a novelty claim.

## Exact match to the Le-WM benchmark

The released evaluation uses:

- goal offset: 25 primitive environment steps;
- planner horizon: five macro actions;
- action block: five primitive actions per macro action;
- CEM: 300 candidates, 30 iterations, 30 elites;
- receding horizon: all five macro actions, so one planned sequence executes
  for exactly 25 primitive steps before replanning.

For every eligible P1 start at primitive step `t`, the proposal cache therefore
contains:

- current latent `z_t` from the frozen Le-WM encoder;
- goal latent `z_(t+25)` from the same episode;
- the real standardized primitive action sequence `a_t ... a_(t+24)`;
- the same sequence reshaped as `(5 macro steps, 5 * primitive_action_dim)`;
- episode, start-step, and P1 train/validation role identifiers.

No sequence may cross an episode. P1 train and P1 validation remain separated
at the episode level. D2 examples must not be used for training.

## Proposal model

The primary model is a compact temporal conditional diffusion model over the
full 25-action sequence. It conditions on standardized `z_t`, standardized
`z_(t+25)`, and their difference. The action trajectory is represented as 25
primitive-action tokens and reshaped only at the planner boundary.

Frozen design candidates must be selected using P1 validation only:

- cosine DDPM training schedule with 100 noise levels;
- epsilon prediction with an exponential-moving-average inference copy;
- temporal transformer or one-dimensional U-Net with approximately matched
  capacity across all tasks;
- deterministic DDIM sampling with a small fixed number of inference steps;
- a fixed seed namespace independent of CEM's Gaussian RNG;
- optional goal dropout used only if classifier-free guidance is selected on
  P1 validation before any E7 closed-loop D2 run.

All action outputs are converted back to the released planner's standardized
action coordinates before entering CEM. Additional model-side action
standardization, if used, is fit on P1 train only and stored in the checkpoint.

## Matched planner integration

The primary GDP-CEM arm refreshes a fixed subset of candidates in every CEM
iteration:

1. preserve candidate zero as the ordinary current CEM mean;
2. draw the complete ordinary 300-candidate Gaussian tensor with the original
   CEM generator, even for candidates that will be overwritten;
3. overwrite a frozen fraction of candidates 1 through 299 with fresh
   conditional proposals from a separate deterministic proposal generator;
4. evaluate exactly 300 candidates with the unmodified Le-WM goal cost;
5. perform the original elite selection and mean/standard-deviation update
   unchanged.

Thus every arm retains exactly `300 * 30` Le-WM candidate evaluations per plan.
Diffusion sampling time and memory are additional costs and must be reported.
The proposal fraction and DDIM step count are selected once using only P1
validation diagnostics, then frozen across PushT, Reacher, and Cube.

A first-iteration-only injection is retained as a predeclared integration
ablation. It cannot replace the refresh-every-iteration primary endpoint. This
distinction tests whether ordinary CEM erases the learned multimodal proposal
after its first Gaussian update.

The primary GDP-CEM arm has no ACID score, reachability score, forward score,
or diffusion verifier penalty. A later `GDP-CEM + ACID` arm may diagnose
complementarity but cannot substitute for the diffusion-alone primary endpoint.

### Mode-preserving low-budget selector

The matched-budget CEM arm is accompanied by `GDP-Select`, which does not fit a
single Gaussian to a potentially multimodal diffusion population:

1. sample 300 complete goal-conditioned action sequences;
2. evaluate each once with the unchanged Le-WM terminal goal cost;
3. execute the lowest-cost actual sequence, never the cross-mode mean.

This uses 300 rather than 9,000 Le-WM candidate evaluations per plan. It is an
efficiency endpoint, not a compute-matched substitute. Shuffled-goal diffusion
and the conditional diagonal Gaussian must use the identical selector. A
`GDP-Select` win over ACID is interpretable only if true diffusion also beats
both selector-matched learned controls. Report end-to-end latency in addition
to candidate count.

If P1-only diagnostics show that CEM mean updates visibly average distinct
proposal modes, a fixed-component mixture-CEM may be specified in a new frozen
development protocol. It may not be invented or selected after viewing E7D
closed-loop outcomes.

## Required controls

1. **Original CEM (B0):** released Gaussian CEM and Le-WM goal cost.
2. **Faithful reconstructed ACID:** the frozen published-equation
   reconstruction already used in the matched study.
3. **Custom-solver Gaussian control:** the E7 solver with proposal injection
   disabled; it must reproduce original CEM under the same seed.
4. **True-goal GDP-CEM refresh:** primary diffusion proposal arm, injected in
   every CEM iteration.
5. **Shuffled-goal diffusion:** same architecture, optimizer, seed, and
   refresh integration, trained after a deterministic within-role derangement
   of goal latents while retaining current latents and action sequences.
6. **Conditional diagonal-Gaussian proposal:** a capacity-matched
   non-diffusion model trained on the same P1 examples and injected through the
   identical refresh slot.
7. **True-goal GDP-CEM initialization:** diffusion proposals only in iteration
   1, reported as a predeclared integration ablation.
8. **GDP-Select family:** true diffusion, shuffled-goal diffusion, and
   conditional Gaussian each get the same one-pool, best-actual-candidate
   selector. These arms address mode preservation and compute efficiency.

A P1 nearest-neighbour action-sequence retrieval proposal is a desirable cheap
geometric control if its index can be implemented without changing the data
boundary or candidate budget.

## Development stages and stopping rules

### E7P: P1-only mechanism qualification

Before closed-loop D2 evaluation, require all of the following:

- cache lineage, shape, episode-boundary, and action-coordinate tests pass;
- the true model overfits a fixed tiny batch;
- held-out P1 denoising loss is lower for the true model than for the
  shuffled-goal model;
- generated action sequences are finite, diverse, and within a frozen robust
  range of P1 train actions;
- candidate-zero preservation, candidate count, CEM call count, and Gaussian
  RNG invariants pass;
- the custom-solver Gaussian control is numerically identical to released CEM
  in a synthetic test and matches a real-stack smoke run.

P1 validation may select one shared proposal fraction from
`{0.25, 0.50, 0.75, 1.00}` and one shared DDIM step count from a small frozen
set. Selection uses no closed-loop D2 success labels. The exact selection
metric and tie rule must be frozen before it is computed.

### E7D: exposed-D2 one-seed diagnostic

Run all required arms on all three tasks using scorer/proposal seed 6101,
planner seed 8301, and the same 50 D2 starts. Read no partial arm outcomes.

GDP-CEM advances only if all are true:

- its equal-task success rate is strictly above original CEM;
- it is strictly above shuffled-goal diffusion;
- it is strictly above the conditional-Gaussian proposal;
- it is no more than 0.05 below reconstructed ACID on the equal-task mean;
- it is not more than 0.15 below reconstructed ACID on any task;
- it improves over shuffled-goal diffusion on at least two of three tasks.

These are development gates, not publication claims.

`GDP-Select` is assessed separately under the same diffusion-specific control
requirements. It may advance even if matched-budget GDP-CEM fails, but only if
true `GDP-Select` is strictly above both selector-matched controls, strictly
above original CEM, and no more than 0.05 below ACID on the equal-task mean.

### E7R: exposed-D2 multi-seed replication

Only after E7D passes, train proposal seeds 6102 and 6103 and run paired planner
seeds 8302 and 8303. Freeze the full grid before submission. Advancement
requires a positive diffusion-specific contrast and practical non-inferiority
to ACID across seeds, with per-task reporting and paired confidence intervals.

### E7F: fresh-D3 confirmation

Only after E7R passes may a new D3 manifest be generated. Freeze code,
checkpoints, hyperparameters, seeds, starts, primary estimand, confidence
interval, multiplicity policy, latency measurements, and failure criteria
before authorizing D3. C1 and I1 remain outside this development branch unless
separately authorized by the thesis protocol.

## Honest interpretation

- A win by true and shuffled diffusion together would support a generic
  behavior-prior explanation, not goal-conditioned diffusion.
- A win by diffusion and the conditional Gaussian together would support
  learned proposal initialization, not diffusion-specific multimodality.
- A win only for `GDP-CEM + ACID` would establish complementarity, not an
  alternative to ACID.
- Only a fresh, frozen confirmation in which diffusion alone beats its nulls
  and is superior or meaningfully non-inferior to ACID can support the intended
  claim.
