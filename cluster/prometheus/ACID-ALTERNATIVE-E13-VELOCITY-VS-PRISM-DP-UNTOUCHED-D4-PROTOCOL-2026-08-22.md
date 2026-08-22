# E13 velocity diffusion versus PRISM-DP reconstruction on untouched D4

Frozen-design date: 2026-08-22

Status: freeze candidate; no E13 D4 manifest or outcome may be generated or
read until the protocol hash, immutable implementation snapshot, external
artifact audit, and P1-only integration smoke have all passed.

Protected inputs: P4, C1, and I1 remain sealed and are never inputs to E13.

## 1. Question and chronology

E13 asks whether E11's frozen Le-WM-latent-conditioned velocity-diffusion
action generator outperforms the disclosed E12 PRISM-DP best-of-N
reconstruction when both occupy the same one-pass proposal-and-selection
planner slot.

E13 was designed after:

- E11's untouched-D3 result;
- inspection of the public PRISM repository;
- completion of E12 native-artifact sanity checks;
- successful P1 training and validation of all nine E12 PRISM-DP
  reconstruction checkpoints; and
- E12's frozen Stage-B stop, caused only by six invalid Reacher Gaussian
  PriorHeads.

E12 did not generate a D4 manifest, run a D4 episode, or read a D4 outcome.
E13 is a new protocol, not a relaxation or continuation of E12. It excludes
the failed PRISM Gaussian PriorHead family rather than changing E12's
conjunctive validity rule after observing it.

E11 and E12 are prior evidence, not E13 confirmation. E11's motivating
equal-task success rates were 93.39% for velocity diffusion, 90.64% for its
capacity-matched Gaussian control, and 83.31% for the published-equation ACID
reconstruction. E13 will not reuse D3 outcomes in any interval or gate.

The primary comparison is:

`vp_select_k300 - prism_dp_select_k300`.

Both methods are diffusion-based. The comparison therefore does **not** test
"diffusion versus no diffusion." It tests the complete frozen E11 design
(Le-WM latent conditioning, velocity prediction, classifier-free guidance,
five deterministic reverse evaluations) against the disclosed PRISM-DP
reconstruction (pixel conditioning, epsilon prediction, ten deterministic
DDIM evaluations).

The E11 conditional diagonal Gaussian is retained as a prespecified mechanism
control. It is not the failed PRISM PriorHead and requires no new training.
No PRISM-PoG, ACID, CEM, SAGE, hybrid verifier, or new architecture is part of
E13.

## 2. Comparator status and permitted attribution

The public PRISM repository is pinned at commit
`baa0eb95efb812196b68796c258b1f0cf10b7625`. It omits
`dp_baseline/model.py`, `dp_baseline/scheduler.py`, and the diffusion-policy
checkpoint used for the public best-of-N table. The nine E12 models are thus
a disclosed reconstruction from the public documentation, not an official
PRISM-DP implementation or checkpoint.

E13 reuses, without retraining or checkpoint selection, the exact nine
PRISM-DP artifacts that passed E12's P1-only validity checks. The external E12
audit is pinned by SHA-256. E13 preflight must verify:

- the E12 audit itself and its training-source manifest;
- all nine summary and checkpoint hashes;
- `validity.passed = true` for every PRISM-DP entry;
- the exact task/seed grid `{PushT, Reacher, Cube} x {6101,6102,6103}`;
- the disclosed reconstruction flag and frozen architecture; and
- that E12 read neither D3 nor D4 outcomes while training these artifacts.

The E12 audit's overall status is `blocked` because unrelated PriorHeads
failed. E13 must record that status and may authorize only the nine explicitly
pinned valid PRISM-DP entries. It must not rewrite E12 as a passed study.

The strongest permitted comparator wording is:

"our disclosed reconstruction of PRISM-DP best-of-N on the tested Le-WM
suite."

"Official PRISM-DP," "exact PRISM reproduction," and unqualified "beats
PRISM" are prohibited.

## 3. Frozen learned artifacts

### 3.1 Proposed velocity-diffusion selector

Reuse the exact E11 checkpoints and inference path for model seeds `6101`,
`6102`, and `6103`:

- frozen Le-WM current and 25-step goal latents;
- complete standardized 25-action trajectories;
- width 512 and four FiLM residual blocks;
- velocity prediction with classifier-free conditioning dropout 0.15;
- deterministic five-evaluation velocity-DDIM sampling;
- classifier-free guidance 1.5;
- E10M P1-only latent/action statistics and robust action bounds; and
- one Le-WM candidate-cost call followed by execution of the lowest-cost
  actual candidate.

No velocity model is retrained, fine-tuned, calibrated, or selected in E13.

### 3.2 Conditional Gaussian mechanism control

Reuse E11's exact capacity-matched conditional diagonal-Gaussian artifacts,
P1 statistics, robust action bounds, and one-pass selection path for the same
three seeds. This arm isolates iterative diffusion sampling from the benefit
of any learned goal-conditioned action proposal.

This Gaussian is distinct from PRISM's failed E12 PriorHead. The E11 Gaussian
artifacts already passed their own frozen prerequisite studies and are not
retrained in E13.

### 3.3 PRISM-DP best-of-N reconstruction

Reuse the exact E12 EMA checkpoints for all task/seed cells:

- paired current and start-plus-25 RGB observations at 224 by 224;
- shared small CNN image encoder producing 256-dimensional features;
- a 256-dimensional joint condition;
- FiLM-conditioned one-dimensional U-Net with channels 64, 128, 256, 512;
- epsilon prediction over a 25-action trajectory;
- 100-step squared-cosine DDPM training schedule;
- deterministic ten-step DDIM sampling;
- P1-train-only per-dimension min-max normalization to [-1, 1]; and
- robust clipping and conversion into the same planner action coordinates.

At evaluation, sample K complete action trajectories, run exactly one shared
Le-WM candidate-cost call, and execute the lowest-cost actual candidate at
the common replanning cadence. No PRISM-DP model is retrained, rescued, or
selected in E13.

## 4. Shared environment and randomness

Use the released Stable-WorldModel datasets, frozen Le-WM checkpoints,
preprocessing, task success callables, goal convention, and action scalers
already pinned by E11/E12.

- Tasks: PushT, Reacher, and Cube.
- Model seeds: `6101`, `6102`, `6103`.
- Goal offset: 25 environment steps.
- Dataset goal row: `start_step + 24`, matching the released evaluation
  convention.
- Closed-loop evaluation budget: 50 environment steps.
- Planner horizon: five macro actions.
- Action block: five primitive actions per macro.
- Replanning cadence: five primitive actions.
- Primary candidate count: K=300.
- Secondary candidate count: K=16 for the two diffusion-policy arms only.

Use base planner/environment seeds `8301`, `8302`, `8303`, velocity proposal
seeds `9101`, `9102`, `9103`, Gaussian proposal seeds `9201`, `9202`, `9203`,
and PRISM-DP proposal seeds `9301`, `9302`, `9303`.

For every task, seed, and resource shard, derive the executed stream seed as
the first eight little-endian SHA-256 bytes modulo `2^63-1` of:

`gdp-e13|<namespace>|<task>|<base_seed>|<shard>`.

Every arm in a task/seed/shard uses the same environment/planner seed. The
K=16 and K=300 variants within a proposal family use the same family stream,
so K=16 is the first 16 candidates of the corresponding K=300 stream.
Different proposal families retain distinct streams.

All timed E13 smoke and confirmation jobs must run on `gpu09.cluster` with an
NVIDIA RTX 6000 Ada Generation. The aggregate analyzer rejects mixed
hardware.

## 5. Untouched E13 D4 selection

All learned artifacts used P1 only. P2 is development-only, and D3 is exposed
and excluded. E13 D4 is drawn from unused P3 episode identifiers after
excluding every R0, D1, D2, and D3 episode. P4, C1, and I1 remain sealed.

The previously audited eligible episode capacities are:

- PushT: 1,360;
- Reacher: 556; and
- Cube: 489.

For each task, select exactly 400 distinct eligible episodes and one start per
episode. For every eligible episode enumerate
`range(episode_length - 25)`. Select that episode's start with the
lexicographically smallest SHA-256 digest of:

`gdp-e13-d4<NUL><task><NUL>2026082201<NUL><episode_id><NUL><start_step>`.

Sort the one-per-episode records by `(digest, episode_id, start_step)` and
take the first 400. Record all input hashes, capacities, exclusions,
intersections, selected-row hashes, and file identities. Existing output is
never overwritten.

The selector may read only episode identifiers, partition labels, episode
lengths/offsets, exclusion identifiers, frozen source/protocol bytes, and the
complete dataset byte stream solely for its declared SHA-256 verification.
It may not deserialize observations, actions, rewards, success flags, goals,
videos, D3 outcomes, or prior result summaries.

The 400 rows are split into eight immutable contiguous 50-row resource shards
by `eval_index`. Sharding is a resource device, not an analysis factor. Every
arm receives the same rows in the same order.

Once any E13 D4 manifest exists, no metric-bearing shard file may be opened
until all 360 required evaluation shards have terminated and the frozen
aggregate analyzer begins. During execution, monitoring is limited to Slurm
state, exit code, file existence, byte count, and checksums.

## 6. Arms and execution size

Run exactly five arms:

1. `latent_gaussian_select_k300`: E11 mechanism control;
2. `vp_select_k300`: primary proposed treatment;
3. `prism_dp_select_k300`: primary direct comparator;
4. `vp_select_k16`: secondary public-extension budget sensitivity; and
5. `prism_dp_select_k16`: secondary matched-budget sensitivity.

Total design:

`3 tasks x 3 model seeds x 5 arms x 400 starts = 18,000 episodes`,

implemented as:

`3 x 3 x 5 x 8 = 360` resource shards of 50 episodes.

Every arm performs one Le-WM candidate-cost call per planning decision. The
primary comparison is K=300. K=16 is secondary and cannot replace, select,
or rescue K=300.

## 7. Staged execution and information barriers

### Stage A — immutable freeze and static tests

Before reading E13 D4, freeze the protocol, code, source manifest, exact E11
artifact hashes, E12 audit hash, nine PRISM-DP artifact hashes, datasets,
world-model checkpoints, seeds, arms, candidate counts, gates, and analyzer.

Static tests must include Python compilation, shell syntax, array-index
bijection, seed namespaces, artifact-grid validation, manifest determinism,
no-overwrite publication, scheduler determinism, action normalization,
candidate shapes, and a full synthetic 360-shard aggregate.

### Stage B — outcome-free external artifact audit

On the cluster, validate all external hashes and the exact nine valid
PRISM-DP entries while preserving E12's overall blocked status. Verify the E11
velocity/Gaussian grids, E10M prerequisite, datasets, world models, partition
and exclusion manifests, and remaining P3 capacity. This stage may read P1
artifact metadata and identifier-only P3 inputs, but no D3 or D4 outcomes.

### Stage C — P1-only joint integration smoke

Before D4 exists, run the exact evaluation integration for all five arms on a
small deterministic P1 start set. It must check K=16 and K=300 candidate
counts, finite/nonconstant proposals, one Le-WM call per planning decision,
artifact hashes, GPU/host identity, output schema, and end-to-end execution.
P1 smoke success rates are non-confirmatory and may never enter an E13 claim.

An implementation error found in Stages A-C may be corrected only with a
written changelog, a new immutable snapshot, and complete repetition of
Stages A-C. Tasks, artifacts, gates, budgets, seeds, and statistical rules may
not change.

### Stage D — manifest creation and sealed D4 evaluation

Only after Stages A-C pass may the identifier-only D4 manifest be generated
and the complete 360-shard array submitted. No tuning, model replacement,
arm removal, task removal, threshold change, or implementation change is
allowed after manifest creation.

An execution failure may be rerun only with identical snapshot, manifest,
task, seed, arm, shard, and dependency hashes. A numerical validity failure
is a result, not an execution failure.

### Stage E — single frozen aggregate

The analyzer must first prove all 360 expected shards are present, complete,
hash-valid, configuration-valid, and mapped bijectively to the frozen array.
Only then may it deserialize episode outcomes and calculate the prespecified
tables, intervals, diagnostics, and gates.

## 8. Outcomes and inference

The primary outcome is binary environment success under the released task
callable. Report task-level tables before equal-task aggregates. Never pool
raw episodes across tasks. Explicitly report ceilings, especially Cube.

Also report for every arm, task, and seed:

- success count and rate;
- paired discordances;
- end-to-end and proposal-generation time;
- Le-WM calls and candidate evaluations;
- active trainable and total parameter counts;
- whether a second image encoder is required;
- peak CUDA memory;
- action boundary/robust-clipping fractions and proposal diversity; and
- checkpoint, source, protocol, manifest, hardware, and result hashes.

For each treatment-control contrast, first average the three paired seed
outcomes within each `(task, eval_index)` start cluster. The primary interval
is conditional on the fixed three seed blocks and uses 100,000 task-stratified
paired bootstrap repetitions over start clusters with seed `2026082202`.
Report the two-sided 2.5/97.5 percentile interval and one-sided fifth
percentile lower bound.

A secondary two-way paired bootstrap independently resamples the three seed
blocks and starts within each task with seed `2026082203`. Report the exact
paired sign test over non-tied start-cluster differences. Individual episodes
are never resampled as independent observations.

The K=300 comparison with PRISM-DP is the sole primary confirmatory contrast.
The Gaussian mechanism replication and both K=16 contrasts are prespecified
secondary analyses and do not alter the primary decision.

## 9. Frozen claim gates

### 9.1 Primary: superiority to the PRISM-DP reconstruction

`vp_select_k300 - prism_dp_select_k300` passes only if all conditions hold:

1. the equal-task point estimate is strictly positive;
2. the primary one-sided 95% start-cluster lower bound is above zero;
3. at least two of three task point estimates are positive;
4. no task estimate is below PRISM-DP by more than 0.05; and
5. both methods have finite, non-degenerate proposals in every task/seed.

If passed, the permitted wording is:

"The frozen E11 velocity-diffusion selector was superior to our disclosed
PRISM-DP best-of-N reconstruction on this three-task Le-WM suite under the
fixed K=300, three-seed protocol."

No result authorizes an unqualified claim of superiority to official PRISM.

### 9.2 Secondary: replication of the diffusion-specific mechanism

`vp_select_k300 - latent_gaussian_select_k300` is a successful independent
replication of the E11 mechanism only if:

1. its equal-task point estimate is strictly positive;
2. its one-sided 95% start-cluster lower bound is above zero;
3. at least two of three task estimates are positive;
4. no task estimate is below Gaussian by more than 0.05; and
5. both proposal families are finite and non-degenerate, with boundary
   fraction below 0.25 in every task/seed.

Failure of this secondary gate does not rewrite the primary PRISM-DP result,
but it prohibits presenting E13 as fresh confirmation that diffusion itself,
rather than the full proposed design, caused any primary advantage.

### 9.3 Compute-efficient alternative

If Gate 9.1 fails, a compute-efficiency claim versus the PRISM-DP
reconstruction is allowed only if K=300 velocity diffusion:

1. has a primary one-sided 95% success lower bound of at least -0.03;
2. has lower median paired end-to-end time over matched
   `(task, seed, shard)` blocks on every task; and
3. has at least one measured resource advantage: fewer active learned
   parameters, no second image encoder, or lower peak CUDA memory.

The exact measured advantage must be named. K=16 cannot rescue this gate.

### 9.4 K=16 sensitivity

Report `vp_select_k16 - prism_dp_select_k16` using the same task-first
statistics. It is a secondary robustness result only. No K=300 claim may be
replaced by whichever K looks more favorable.

## 10. Stopping and reporting rules

After D4 manifest creation, no implementation correction, retraining,
checkpoint selection, task deletion, arm deletion, candidate-budget change,
seed change, margin change, inference change, or new diagnostic may affect
the E13 result. Identical execution reruns are allowed only for documented
infrastructure failures and must preserve failed outputs.

If the primary gate fails, report the complete negative primary result. If
the mechanism gate fails, report it independently. If Cube is saturated or
Reacher differs in sign, place that task-level fact before the aggregate.

E13 cannot be rescued by adding ACID, PRISM-PoG, SAGE, a hybrid verifier,
another backbone, or a new architecture. Those require separate protocols.

Regardless of outcome, publish the protocol hash, immutable source-manifest
hash, exact artifact status, all per-task results, all prespecified gates,
and the fact that E12 stopped before D4.
