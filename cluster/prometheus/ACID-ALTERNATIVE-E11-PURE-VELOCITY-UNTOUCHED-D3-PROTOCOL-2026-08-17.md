# E11 pure velocity-diffusion untouched-D3 closed-loop protocol

Frozen-design date: 2026-08-17  
Status: freeze candidate; D3 may be generated only from an audited immutable snapshot  
Protected inputs: C1 and I1 remain sealed and are never inputs to E11

## 1. Question and preserved evidence

E11 asks whether a pure goal-conditioned velocity-diffusion action generator,
without a Gaussian anchor, CEM refinement, ACID term, or verifier, improves
untouched closed-loop success over the reconstructed ACID baseline and over
matched proposal controls.

The design was fixed after, and preserves rather than hides, two development
outcomes:

1. E8D exposed-D2 GADR development, aggregate SHA-256
   `89d76ee15d4fa4420288dc5306f7f18565d39fa13c959a0c52168995b10e531f`:
   true GADR refresh achieved `0.9067` success versus reconstructed ACID's
   `0.8800`, but Gaussian and shuffled GADR achieved `0.9000`; diffusion was
   therefore not isolated.
2. E10M fixed-configuration multi-seed P1 replication, aggregate SHA-256
   `a685fd9da7f6050a98cdc7fe792d73fec4f83a3e1dc6dd083982fbe5c274f84c`:
   seeds 6101, 6102, and 6103 all passed all seven predeclared
   diffusion-specific open-loop gates for pure velocity proposals using five
   reverse evaluations and guidance 1.5.

E11 is the first closed-loop test of that frozen pure proposal model. E11 is a
conditional test on this three-task Le-WM suite; it does not establish
generalization to unseen task families or an official ACID implementation.

## 2. Untouched D3 starts

Use exactly 400 starts for each of PushT, Reacher, and Cube, one start from each
of 400 distinct P3 episodes. The fixed goal offset is 25, the environment
evaluation budget is 50, and `dataset_goal_step = start_step + 24`.

Before protocol freeze, identifier-only auditing found 1,760 PushT, 956
Reacher, and 889 Cube eligible P3 episodes after exclusions. No protected
outcome was read. The design leaves at least 489 eligible Cube episodes unused.

The manifest generator may read only:

- the episode partition manifest;
- the R0 identifier manifest;
- the D1 identifier manifest;
- the exposed D2 identifier manifest;
- dataset episode lengths and offsets;
- the frozen protocol and source-manifest bytes for integrity; and
- the complete dataset byte stream solely to verify its predeclared SHA-256.

It may not deserialize observation, action, reward, goal, or outcome arrays.

It must not read result summaries, episode success columns, videos, C1, or I1.
The R0, D1, and D2 episode unions are excluded even where partition separation
would already make an exclusion redundant.

For each eligible episode, enumerate `range(episode_length - 25)`. Choose that
episode's start with the lexicographically smallest SHA-256 digest of

`gdp-e11-d3<NUL><task><NUL>2026081709<NUL><episode_id><NUL><start_step>`.

Sort these one-per-episode records by `(digest, episode_id, start_step)` and
take the first 400. Record all input hashes, selected-row hash, counts, and
zero intersections. Existing output is never overwritten.

The 400 rows are split only for resource isolation into eight immutable,
contiguous 50-row shards by `eval_index`; sharding is not an analysis factor.
All arms receive the same rows in the same order.

No arm output, success count, metric, or video may be inspected after D3
manifest creation until all 576 evaluation shards have terminated and the
single aggregate analysis has run. Scheduler state, exit status, log existence,
and checksums may be monitored without opening metric-bearing files.

## 3. Fixed stack, models, and randomness

Use the already hashed released Le-WM checkpoints and Stable-WorldModel
datasets from E8D. Before D3 generation, remove write permission from the six
exact dataset/Le-WM files, verify their full hashes, and record file identity
metadata. Use model/scorer seeds `6101`, `6102`, and `6103`.

The velocity treatment is fixed to:

- a complete standardized 25-action trajectory from standard-normal noise;
- 300 candidates;
- five deterministic velocity-DDIM model evaluations;
- classifier-free guidance scale 1.5;
- E10M's P1-only latent/action statistics and robust action bounds;
- one Le-WM candidate rollout and execution of the lowest-cost actual
  candidate; and
- no CEM refinement, Gaussian initialization, ACID term, or auxiliary score.

The Gaussian proposal model uses the same architecture width, depth, optimizer
family, training budget, P1 data, and 300-candidate one-rollout selector slot.
The shuffled-goal velocity model uses paired training-noise/timestep streams.
The unconditional control is the true model's learned null-goal branch at
guidance zero.

Base planner seeds are `8301`, `8302`, and `8303`; matched velocity-proposal
seeds are `9101`, `9102`, and `9103`; independent Gaussian-proposal seeds are
`9201`, `9202`, and `9203`. For each task/seed/shard, derive the executed seed
as the first eight little-endian SHA-256 bytes modulo `2^63-1` of

`gdp-e11|<namespace>|<task>|<base_seed>|<shard>`.

Every arm in a task/seed/shard uses the same derived planner/environment seed.
The three velocity arms use the same derived velocity-proposal seed and hence
the same initial standard-normal bank at every planning call. The Gaussian arm
uses its separately namespaced seed. CEM arms use the same CEM Gaussian stream.
All timed shards must run on `gpu09.cluster` with an NVIDIA RTX 6000 Ada
Generation; the analyzer rejects mixed hardware.

## 4. Arms and budgets

Run exactly eight arms:

1. `b0`: released 30-iteration CEM and Le-WM goal cost;
2. `acid`: published-equation ACID reconstruction, `lambda = 0.07`, one
   independent inverse-flow draw per imagined transition, adaptive spread
   normalization, 300 candidates, 30 iterations, and 30 elites;
3. `reachability`: the horizon-matched temporal reachability head (M3),
   `lambda = 0.07`, otherwise the same CEM;
4. `forward`: the capacity-matched deterministic forward verifier,
   `lambda = 0.005`, otherwise the same CEM;
5. `gaussian_select`: conditional diagonal-Gaussian proposals;
6. `vp_shuffled_select`: shuffled-goal velocity proposals at guidance 1.5;
7. `vp_unconditional_select`: true velocity model at guidance zero; and
8. `vp_true_select`: primary goal-conditioned velocity treatment at guidance
   1.5.

ACID remains a transparent reconstruction because official code is
unavailable. It must not be described as an official reproduction.

Total design:
`3 tasks x 3 seeds x 8 arms x 400 starts = 28,800 closed-loop episodes`,
implemented as `3 x 3 x 8 x 8 = 576` resource shards. Selector arms use one
300-candidate Le-WM cost call per planning decision; CEM arms use 30.

## 5. Pre-D3 sensitivity justification

The sample size was fixed before D3 generation. Treating the three repeated
model seeds as fully correlated gives a conservative 1,200 task/start clusters.
A one-sided normal approximation to a paired binary sign/McNemar statistic
gives 80% minimum detectable success differences of approximately 1.6, 2.3,
2.8, and 3.2 percentage points when paired discordance is respectively 0.05,
0.10, 0.15, and 0.20. E8D true-refresh versus ACID had discordance 0.1067 and a
2.67-point difference. Because E11 averages three outcomes before a stratified
percentile bootstrap and effects may differ by task, these numbers are only a
worst-case-correlated sensitivity proxy, not power for the exact E11 gate and
not an assumed effect.

## 6. Integrity gates

Before D3 generation, all of the following must pass in an immutable snapshot:

- source-manifest and protocol hashes;
- exact dataset, Le-WM, scorer, proposal-summary, and proposal-checkpoint hashes;
- E10M prerequisite decision and all seven gates;
- stable velocity-target reconstruction and classifier-free algebra;
- deterministic checkpoint loading and velocity sampling;
- matched velocity initial-noise streams and separate Gaussian namespace;
- exact candidate counts, robust bounds, and action reshaping;
- exact cached/released Le-WM rollout equivalence already tested upstream;
- a closed-loop integration smoke on P1 only;
- D3 selection capacity and zero overlap using identifiers only; and
- rejection of C1, I1, result-summary, and non-E11 confirmation inputs.

If any item fails, stop before D3 generation. An implementation correction
requires a new immutable snapshot and audit but may not change the statistical
design. Once D3 is generated, no tuning, rescue arm, or implementation change
is permitted; an execution failure may only be rerun from the identical
snapshot, manifest, arm, seed, shard, and hashes.

## 7. Outcomes and inference

The primary outcome is binary environment success under the released task
callable. Report every task, model seed, and arm separately; equal-task and
equal-seed means; end-to-end and proposal time; Le-WM cost calls and candidate
evaluations; peak CUDA memory; boundary fraction; and proposal diversity.

For a treatment-control contrast, first average the three paired seed outcomes
within each `(task, eval_index)`. The primary interval is conditional on this
fixed set of three model/planner-seed blocks and uses 100,000
task-stratified paired bootstrap repetitions over start clusters with seed
`2026081710`. The reported two-sided interval is the 2.5th and 97.5th percentile;
the one-sided lower bound is the 5th percentile. A secondary two-way bootstrap
resamples the same model-seed block across tasks and independently resamples
starts within tasks, preserving arm pairing, with seed `2026081711`. Also
report the exact paired sign test over non-tied start-cluster differences.
Never weight tasks by their raw episode counts. No claim about a population of
training seeds is permitted from three fixed seed blocks.

Secondary comparisons of the true treatment with B0, reachability, and forward
are descriptive and receive Holm-adjusted two-sided sign-test p-values as one
family. They do not enter either primary claim gate.

The Gaussian, shuffled-goal, and unconditional mechanism tests form an
intersection-union gate: all three one-sided nulls must be rejected, so they
are not separately multiplicity-adjusted. The ACID test is hierarchical and
is considered only after that gate passes. This gatewise interpretation does
not imply that every reported interval belongs to one simultaneous confidence
set.

## 8. Frozen interpretation

### Diffusion-specific mechanism gate

The mechanism passes only if `vp_true_select`:

1. has strictly higher equal-task success than Gaussian, shuffled-goal, and
   unconditional selectors;
2. has a one-sided 95% start-cluster lower bound above zero versus Gaussian,
   shuffled-goal, and unconditional selectors;
3. exceeds both Gaussian and shuffled-goal point estimates on at least two of
   three tasks; and
4. has finite proposals, positive diversity, boundary fraction below 0.25 in
   every task/seed, and all integrity checks.

The unconditional control is the same trained model at guidance zero, so its
contrast isolates use of the learned goal branch rather than independent-model
training variability.

### Superiority to reconstructed ACID

A suite-conditional superiority claim is permitted only if the mechanism gate
passes and `vp_true_select - acid` has:

1. a positive equal-task point estimate;
2. a one-sided 95% start-cluster lower bound above zero;
3. a positive point estimate on at least two tasks; and
4. no task point estimate below ACID by more than 0.05.

The task-win and five-point harm clauses are practical consistency guards, not
per-task superiority tests. The wording must be “superior to our
published-equation ACID reconstruction on the tested Le-WM suite and fixed
three-seed set,” never “superior to ACID” without those qualifications.

### Compute-efficient alternative

If strict superiority fails, a compute-efficient-alternative result is allowed
only if the mechanism gate passes, the one-sided 95% lower bound versus ACID is
at least `-0.03`, selector Le-WM candidate evaluations per planning decision
are at most one thirtieth of ACID's, and the median paired
treatment-minus-ACID time difference across matched 50-episode
`(task, seed, shard)` blocks is below zero on every task. This is a
non-inferiority/efficiency statement, not superiority.

If neither route passes, report the complete negative result. No task, seed,
start, arm, model, guidance scale, denoising count, success definition,
confidence procedure, margin, or gate may change after D3 exists. PLDM or any
cross-backbone study requires a later, separately frozen protocol and cannot
rescue E11.
