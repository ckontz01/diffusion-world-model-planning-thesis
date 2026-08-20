# Protocol implementation amendments

Opened 8 August 2026 after the first successful artifact executions. This file
records implementation facts and previously unspecified operational choices;
it does not retroactively change observed results. No scorer has been trained
and no P1/P2 scorer data have been inspected at the time of this freeze.

## A-001 — Published baseline seed provenance

The paper reports three-seed aggregates, but the released PushT matrix lists
only seed `42` and supplies no B1 matrix specification. Seed `42` runs are
therefore development pilots. A publication-facing three-seed reproduction
requires either the original seed identities from the authors or a separately
predeclared independent seed set. No seed identities will be inferred from
rounded paper statistics.

## A-002 — Process-level determinism environment

Set `PYTHONHASHSEED=42`, `CUBLAS_WORKSPACE_CONFIG=:4096:8`, and
`EVAL_DETERMINISM=strict` before Python starts, in addition to the released
evaluator's in-process seeding. This is a reproducibility correction, not a
model or planner intervention. The environment values and determinism report
must be saved with each run.

## A-003 — PushT operational transition gap

Set the primary PushT transition gap to `Delta = 25` primitive environment
steps. The released dataset/training interface uses frame skip `5`; the
published empirical-macro configuration encodes chunks of `5` resulting model
tokens; and the artifact reports `raw_macro_len=25`. Thus M1 and M2 use real
pairs separated by 25 primitive steps, and M1 encodes the corresponding five
grouped action tokens with the frozen macro encoder.

Hi-LeWM was trained with variable waypoint gaps and an unconstrained B0 macro
latent has no explicit duration. Consequently, `Delta=25` is an operational
horizon match to the published B1 support construction, not a claim that every
B0 latent macro represents exactly 25 steps. This limitation must be stated in
the thesis. Candidate-attainment trials keep the candidate subgoal fixed for
25 primitive steps while the frozen low-level MPC continues its normal
receding-horizon replanning.

## A-004 — Episode partition allocation and pre-partition quarantine

The master protocol fixes hash seed `20260728` and episode-disjoint roles but
does not give allocation proportions. Freeze the remaining eligible PushT
episodes by the first 64 bits of

`SHA256("pusht_expert_train\0" + "20260728\0" + episode_id)`

interpreted as a uniform value in `[0,1)`:

- P1: `[0.0, 0.7)` — scorer training and validation;
- P2: `[0.7, 0.8)` — development and calibration;
- P3: `[0.8, 0.9)` — locked offline audit;
- P4: `[0.9, 1.0)` — locked closed-loop confirmation.

Before applying those thresholds, place the union of all episode IDs whose
outcomes were already exposed by infrastructure smoke or baseline-pilot runs
into `P0`. P0 is development-only and excluded from P1-P4. This avoids letting
the pre-partition baseline work leak observed episodes into either locked
partition. Partitioning uses episode IDs and lengths only, never outcomes,
states, pixels, or scorer values.

## A-005 — P1 internal train/validation split

The master protocol requires P1 validation for early stopping but does not set
its episode allocation. Within P1, assign episodes 90/10 by the first 64 bits
of

`SHA256("pusht_expert_train\0" + "20260728\0p1_train_val\0" + episode_id)`.

Values in `[0.0, 0.9)` are `P1_train`; values in `[0.9, 1.0)` are `P1_val`.
This second domain-separated hash is independent of scorer values and is
frozen before latent extraction or scorer training.

## A-006 — Scorer-pair enumeration and M3 separation balance

The master protocol fixes M3's total pair counts and separation range but does
not specify its separation distribution or within-separation sampler. Freeze
M3 to exactly 2,500 training pairs and 250 validation pairs at each integer
separation from 1 through 40. This realizes exactly 100,000 `P1_train` and
10,000 `P1_val` pairs with a balanced separation target.

Within each P1 role and separation, sample uniformly without replacement over
all valid within-episode `(start, start + separation)` pairs. Selection uses
domain-separated SHA-256 rejection sampling with seed `20260728`; collision
resolution is part of the recorded algorithm. Training and validation draw
only from their respective episode-disjoint roles.

M1 and M2 use every valid within-episode P1 pair at exactly `Delta=25`; no
pair subsampling is permitted. Record the realized counts, source episode
manifest hashes, pair-plan hash, and exact compressed M3 sample-manifest hash
before scorer training.

## A-007 — M3 head, ordering, loss, and training seeds

Primary-source verification of the TRM method fixes M3's feature map to
`[z_i, z_j, z_i - z_j, abs(z_i - z_j)]`, followed by two 256-unit hidden
layers with SiLU nonlinearities and a Softplus scalar output. Train with
Smooth-L1 loss against `separation / 40`. The master protocol's common
optimizer settings remain controlling: AdamW at `3e-4`, weight decay `1e-4`,
cosine decay, batch size 256, and validation-loss early stopping with patience
10. Set a hard cap of 200 epochs.

TRM samples pair order randomly although the label is symmetric. The frozen
M3 manifest records each pair chronologically; at input time, swap its order
when the least-significant bit of its recorded `selection_sha256` is one. This
gives a deterministic, approximately balanced random order without changing
the frozen pair set. For the M3 null, permute training labels only and retain
the true validation labels, matching the ASAR control description.

Use independent scorer-training seeds `20260728`, `20260729`, and `20260730`
for both the true and shuffled-label heads. These are scorer seeds, not claims
about the unavailable three baseline seeds used in the Hi-LeWM paper.

## A-008 — M2 denoiser and noise protocol

Standardize each LeWM latent dimension using the `P1_train` frame mean and
population standard deviation, with a numerical floor of `1e-6`. All M2 noise
scales are expressed in this standardized space. Compute and hash the statistics
once; P1 validation, P2 candidates, and later locked candidates use the frozen
training statistics without refitting.

The M2 epsilon network concatenates the noisy standardized target, the clean
standardized source, and a 64-dimensional sinusoidal embedding of `log(sigma)`.
Following DOSER's MLP design family, use four hidden Mish blocks; the hidden
width remains the master protocol's P2 choice between 512 and 1024. A linear
head predicts the injected epsilon. Train by mean squared epsilon-prediction
loss, sampling `sigma` uniformly from the declared grid
`{0.1, 0.25, 0.5, 0.75, 1.0}` and using every valid `Delta=25` P1 pair per
epoch. The common optimizer, batch size, early stopping, and three scorer seeds
remain unchanged; cap training at 50 epochs.

Validation uses true P1 validation pairs and a fixed, balanced assignment of
the five sigma levels with Gaussian noise from seed `20260728`, shared across
widths and training seeds. Deployment scoring uses the same eight fixed
standard-normal noise vectors for every candidate, generated once with seed
`20260728` and hashed. Common random numbers prevent candidate rankings from
being driven by different noise draws.

The primary M2 is deliberately not DOSER's EDM implementation: DOSER predicts
clean samples with EDM preconditioning and a log-logistic training schedule,
whereas the master protocol predeclares epsilon prediction and a single frozen
scoring level. This distinction must remain explicit in the thesis.

For the frozen mismatched-pair null, both its training and validation inputs
pair each target with a source from a different episode in the same P1 role.
Episode mappings and within-episode offsets are deterministic SHA-256 functions
of the scorer seed. The null therefore receives the same targets, pair counts,
architecture, optimizer, and validation-noise protocol while destroying only
the source-to-future relationship. Width selection is made on the true M2 arm;
the matched null uses that selected width.

## A-009 â€” Latent-cache provenance checksum ordering erratum

The P1/P2 latent extraction jobs `294589` and `294590` were submitted with a
runner that generated `checksums.sha256` immediately before appending the final
`finish_utc` line to `provenance.txt`. This makes only the recorded provenance
checksum stale; it does not affect the cache or manifest hashes. Job `294590`
was detected after completion: `latents.h5` and `manifest.json` validated, the
original checksum file was preserved, and a replacement checksum inventory was
generated with an accompanying erratum. Job `294589` was still running when
the issue was found and will receive the same documented post-completion
repair. The reusable runner now appends `finish_utc` before checksum creation.

## A-010 — Publication-facing PushT D75 planner row

Primary-source Table 4 and Table 5 verification fixes the matched online D75
configuration to high-level horizon `2`, high-level replan interval `5`,
low-level horizon `2`, and low-level receding horizon `1`. This is the row on
which the paper reports B0 at `15.3%` and B1 at `32.7%`. Its high-level CEM
budget is 1,200 candidates, 60 iterations, and top-k 10; its low-level CEM
budget is 1,200 candidates, 30 iterations, and top-k 150. The low-level action
block remains 5 primitive actions. Candidate-attainment trials hold the first
high-level subgoal fixed for 25 primitive steps while this low-level planner
replans normally every 5 primitive actions.

## A-011 — P2 stratum-3 development-pool capture

Freeze the initial P2 stratum-3 development audit to 12 episode-distinct query
pools, half the locked P3 count. Each pool contains 64 candidates and each
candidate later receives the master protocol's five repeated executions. P2
is development-only and its metrics are never reported as final results.

Queries use D75-eligible P2 episodes ordered by domain-separated SHA-256 under
seed `20260728`; their within-episode starts and CEM seeds use separate hash
domains.
For each query, run the unmodified stable-worldmodel `CEMSolver` with the D75
settings in A-010, retain its final 1,200-candidate population, and select 64
indices by a third domain-separated SHA-256 ordering. All candidates in a pool
therefore share one current state and goal. Save the complete final population,
nominal costs, selected macro sequences, first macro, and first predicted
subgoal. The capture adapter must verify that the final top-10 elite mean
exactly equals the action returned by the released solver.

## A-012 — Candidate-attainment repetitions and latent distance

Freeze the five low-level planner/environment seeds to `1070413377`,
`951166590`, `4200525716`, `38670800`, and `2537523285`. They are the low
32 bits of domain-separated SHA-256 values under root seed `20260728`. Every
candidate and every comparison arm uses the same five seeds.

To execute multiple candidates efficiently while preserving common random
numbers, batch the candidates but give each one the identical standardized
Gaussian CEM draw at each iteration. This is computationally equivalent to
running the released `CEMSolver` independently for every candidate with the
same seed. An automated equivalence test against separate official solves must
pass before every execution job; the initial test had exact zero difference.

For the imagined-candidate tolerance grid, define latent distance as
`sqrt(mean_d(((z_actual[d] - z_subgoal[d]) / std_P1_train[d])^2))`, using the
frozen per-dimension P1 training standard deviations and their `1e-6` floor.
Save raw latent MSE/RMSE, standardized RMSE, final latent, and final physical
state for every candidate execution. Do not assign binary attainment labels
until the P2 physical-versus-latent tolerance procedure is complete.

## A-013 — Bounded environment batching for candidate attainment

The first all-64 development resource attempt, job `294608`, passed input
validation but failed before completing an execution because evaluating the
effective `64 x 1200` low-level CEM population in one LeWM attention call
exceeded the CUDA kernel launch configuration. It produced no usable result.

Keep all 64 candidates in one statistical pool and preserve the common CEM
noise draws, but evaluate the frozen model cost in consecutive chunks of 16
candidates along the independent environment axis. No candidate population,
cost, elite selection, mean, variance, seed, or environment trajectory is
shared or altered by this computational partition. The solver equivalence
self-test uses a chunk size of one and remains exactly equal to separate
same-seed calls to the released `stable_worldmodel` solver (`max_abs = 0`).

The corrected all-64 resource run, job `294609`, completed at the published
low-level CEM budget (`1200/30/150`) in 349.443 seconds, with 1.198 GiB peak
allocated and 1.219 GiB peak reserved GPU memory. Its output checksum
inventory validates. Freeze 16 as the model-cost environment chunk size for
all P2 candidate-attainment executions.

## A-014 — M1 frozen macro targets and exact inverse-head architecture

For every frozen `Delta=25` M1 pair, take the 25 intervening primitive actions,
standardize the two raw action dimensions with the released artifact's dataset
scaler, group them into five 10-dimensional action tokens, and encode them once
with the frozen Hi-LeWM macro-action encoder. Cache the resulting 32-dimensional
macro target alongside the pair's source row, target row, and episode. The two
1,024-pair development extractions in jobs `294611` and `294612` produced
byte-identical HDF5 files, SHA-256
`120d7e745ea11bb7b9038e8c2bddbbc453ceecf32c59409bdf9a26e593d9815c`.

Interpret the master protocol's “3-layer MLP” literally as three linear
layers: `384 -> width -> width -> 32`, with Mish after the first and second
linear layers. The width remains the frozen P2 choice from `{256, 512}`. Both
input latents use the P1-train frame mean and population standard deviation.
For numerical conditioning, train against macro targets standardized with the
P1-train macro-target mean and population standard deviation; de-standardize
the network output before candidate scoring. The primary M1 score remains the
squared L2 residual in the original frozen macro-action latent space, exactly
as specified in the master protocol.

Use the common AdamW, learning rate, batch size, cosine schedule, and P1
early-stopping rules. For the shuffled-label null, construct a deterministic
within-role permutation separately for P1 train and validation by randomly
ordering all pair indices and cyclically shifting that order once. This is a
true permutation with zero fixed points; record its SHA-256 for every scorer
seed. Width selection is performed only for the true arm, and the null later
inherits the selected width.

## A-015 — P2 real-frame audit sampling and PushT physical criterion

Freeze the P2 tolerance-development audit to 12 pools of 64 candidates for
each real-frame stratum, mirroring the half-P3 development scale used for
stratum 3. A pool is a computational/statistical batch for strata 1 and 2;
unlike a planner proposal pool, its 64 candidates need not share a source
state. Use one source per P2 episode, with source episodes disjoint between the
two strata. Order episodes and choose D25-valid source steps using
domain-separated SHA-256 under seed `20260728`.

For stratum 1, pair every source with the frame exactly 25 primitive steps
later in the same episode. For stratum 2, assign a target episode using a
domain-separated SHA-256 order followed by a one-position cyclic shift, which
guarantees a different target episode and uses every selected target episode
once; choose its target step by a separate domain-separated hash. No outcome
or learned score enters candidate selection.

Inspection of the pinned `stable_worldmodel==0.0.6` PushT implementation fixes
the benchmark numerical tolerances to position error `< 20` pixels and wrapped
block-angle error `< pi/9`. Following the master protocol, the primary
real-frame criterion applies the position tolerance to the block's two
coordinates only. The required agent-pose sensitivity reproduces the released
`eval_state` implementation exactly: joint L2 error over agent and block
positions `< 20`, together with the same wrapped-angle tolerance. Record both
criteria and the continuous errors for every execution.

## A-016 — Attainment means minimum distance within the execution budget

The master protocol defines attainment within a 25-step low-level execution
budget, not proximity only at the terminal step. Therefore record the physical
state and frozen-encoder latent at reset and after every primitive environment
step (`t = 0, ..., 25`). For imagined candidates, the continuous attainment
statistic is the minimum P1-standardized latent RMSE over these 26 records; the
P2-selected tolerance is later applied to this minimum. Preserve terminal
distance as a diagnostic. For real-frame candidates, apply both physical
criteria from A-015 at every recorded state and use whether the criterion was
met at least once within the same inclusive trace.

The first stratum-3 execution array, job `294610`, used terminal-only latent
distance. It was stopped when this mismatch was identified, before any labels,
tolerances, scorer choices, or reported metrics were created. Its completed
task outputs are retained as explicitly discarded development diagnostics and
must not enter analysis. The replacement array must pass a new all-64 resource
test, save the complete traces and minimum-step indices, and use a distinct
output root and job identifier.

## A-017 — Corrected attainment execution release

The corrected all-64 trace resource test, job `294649`, completed successfully
at the frozen low-level CEM budget (`1200/30/150`) with the 16-environment
cost chunk. It recorded 26 states and latents per candidate, required 341.716
seconds of execution time, and peaked at 1,287,397,376 allocated bytes and
1,310,720,000 reserved bytes on an RTX A5000. Its checksum inventory validates;
all traces are finite; the stored minima and argmin steps exactly reproduce the
saved traces; and 62 of 64 candidates reached their minimum standardized
distance before the terminal step. This last diagnostic confirms that the
terminal-only outputs from job `294610` cannot be substituted for the required
within-budget statistic.

Release corrected stratum-3 execution array `294652` only from the script and
executor whose SHA-256 values are respectively
`0fefbbb44b0674bbddb39a1c06ba6a0448b698ebcaba53dbdb523aa9946b2d7e`
and
`75a78cb97e2b83b33eaffd02c418fe55f51a138117134f996c010e69c1447702`.
Its aggregate must use only the distinct
`p2-stratum3-job-294652` output root.

The independent-source/target real-frame executor passed smoke job `294657`.
The smoke output has valid checksums; physical and latent traces have 26
records; stored minima, argmins, and any-step attainment flags reproduce the
underlying traces exactly; and the released environment-success flag equals
the agent-included physical criterion over post-reset steps. Release the full
two-stratum real-frame execution as array `294659` only after that smoke test.

## A-018 — P2 raw-score selection across scorer replications

Before constructing any P2 stratum-3 labels or inspecting scorer AUROC, fix
budgeted-attainment failure (`1 - primary_at_least_3_of_5`) as the positive
class for all feasibility-score AUROCs. Compute each training seed's raw score
separately over all 12 P2 stratum-3 pools and use the arithmetic mean of the
three seed-specific AUROCs as the architecture-selection objective. This
selection precedes Platt fitting and therefore does not average incomparable
uncalibrated scores across seeds.

For M1, select the width in `{256, 512}` with the larger mean seed-specific
AUROC; an exact tie chooses width 256. For M2, evaluate every predeclared pair
in `{512, 1024} x {0.1, 0.25, 0.5, 0.75, 1.0}` and select the pair with the
largest mean seed-specific AUROC; exact ties choose the narrower width and
then the smaller noise level. The eight frozen noise vectors are shared across
candidates, widths, noise levels, and training seeds. M2's recorded raw score
is the mean over those eight draws of the squared L2 epsilon-prediction
residual (summing the 192 latent coordinates), matching the master equation.
M1's raw score is the squared L2 residual after de-standardizing its predicted
macro vector. M3's raw score is its nonnegative prediction multiplied by the
frozen 40-step target scale.

For the training-free G0 diagnostics, standardize every coordinate within its
64-candidate pool by the coordinate median and interquartile range; replace a
zero or non-finite interquartile range with one. Define isolation as the mean
Euclidean distance to the three nearest other candidates, separately in the
first-macro space (G0a) and subgoal-latent space (G0b). Larger values mean a
stronger predicted failure signal. These definitions are fixed before their
P2 labels are available.

## A-019 — Exact M2 plain-autoencoder interpretation control

The master protocol's capacity-matched plain-autoencoder control inherits the
P2-selected M2 width and all three scorer seeds; it receives no independent
architecture selection. Train it on the same true P1 Delta=25 pairs and the
same standardized latents as M2. Its clean conditional reconstruction network
takes concatenated `(z_t, z_(t+Delta))`, encodes through
`384 -> width -> width -> 64`, and decodes through
`64 -> width -> width -> width -> 192`, with Mish after every linear layer
except the output. It reconstructs the clean standardized target and uses
per-element MSE for training and early stopping. Its candidate score is the
squared L2 target-reconstruction residual in standardized latent coordinates.

The 64-dimensional bottleneck makes this a genuine reconstruction
autoencoder. The extra width layer keeps trainable capacity close to the M2
denoiser despite the autoencoder lacking M2's 64-dimensional sigma input;
record both exact parameter counts and their ratio. Use the identical AdamW,
learning rate, weight decay, batch size, cosine schedule, maximum epochs, and
early-stopping rule. This control affects only whether a successful M2 result
supports a diffusion-specific interpretation; it is not a promotion null and
does not enter M2's architecture or sigma selection.

## A-020 — Calibration direction and deterministic fitting

Because every raw score is defined in advance so that larger means greater
predicted failure, calibration must be monotone nondecreasing and may not use
P2 labels to reverse a scorer's direction. Fit one Platt map per selected true
model seed on all P2 stratum-3 candidates. Numerically standardize that seed's
raw P2 scores, then minimize mean binary cross-entropy plus `1e-6 * slope^2 / 2`
for `sigmoid(slope * standardized_score + intercept)`, subject to
`slope >= 0`, using deterministic projected Newton iterations with backtracking.
Store both standardized and equivalent raw-score parameters. The fixed primary
ensemble is the arithmetic mean of the three seed-specific calibrated failure
probabilities, as required by the master protocol.

For the isotonic sensitivity, sort by raw score, average exact score ties, and
apply the deterministic pool-adjacent-violators algorithm with nondecreasing
block probabilities. Clamp scores outside the P2 range to the nearest block at
later evaluation. Record P2 Brier score and 10-bin equal-width ECE as
development diagnostics; locked P3 supplies the reported calibration metrics.
Null and autoencoder scores are evaluated with the same fixed failure label,
but neither receives a calibrator for promotion or closed-loop planning.

## A-021 — P2 closed-loop weight selection and shared queries

Before any P2 scorer, calibration, or augmented closed-loop result is
available, freeze weight selection to the same 12 episode-distinct D75 PushT
queries captured for the P2 stratum-3 pools in job `294604`. Each query uses
its recorded source row, goal row, and 63-bit planner seed. There is one query
per development evaluation seed. Consequently, the P4 query count is also one
D75 query per each of its 40 predeclared evaluation seeds.

Run M1, M2, and M3 separately at every weight in
`{0.25, 0.5, 1, 2, 4}`. Each run uses the published D75 hierarchy and budget:
150 primitive evaluation steps; high horizon/receding horizon/action block
`2/1/1`, replanning every 5 primitive steps, and high CEM
`1200/60/10`; low horizon/receding horizon/action block `2/1/5` and low CEM
`1200/30/150`. Use the released latent-prior procedure. Reset the environment
to the recorded source frame and set the recorded D75 frame as the goal.

At every high-level CEM cost call, perform the frozen Hi-LeWM rollout exactly
once. Preserve its squared-L2 final-to-goal cost. Score the first predicted
latent and first proposed 32-dimensional macro action with all three selected
training-seed replicas of the relevant arm, apply each replica's frozen P2
Platt map, and average the three failure probabilities. The augmented cost is
exactly `nominal_goal_cost + w * mean_failure_probability`. The low-level
planner and the frozen world model are unchanged. An exact-zero comparison
between the wrapper's nominal component and the released `get_cost_high` must
pass before each job can execute an episode.

All methods and weights share the source, goal, environment seed, high- and
low-level CEM seed, warm-start rules, and initial random candidate draws for a
query. Adaptive proposals may diverge after score-dependent elite selection,
as permitted by the master matching rule. For each arm, choose the weight with
the largest number of released benchmark successes across the 12 queries. An
exact tie chooses the smaller weight; no continuous endpoint or diagnostic is
used as a secondary tie-break. P2 success counts remain development-only and
must not appear as final results. Null and autoencoder controls do not receive
closed-loop weights.

## A-022 — Matched P2 D75 B0/B1 difficulty check

Before running a D75 baseline outcome on the P2 queries, freeze the environment
difficulty check to the same 12 source/goal/seed tuples specified in A-021 and
the same 150-step D75 planner budgets. Run each tuple once with B0 and once
with B1. B0 uses the released unconstrained high-level CEM. B1 changes only
that high-level solver to the released `EmpiricalMacroActionSolver`, with
4,096 training-set sequences, chunk length 5, residual scale 0.1, minimum
residual standard deviation 0.001, eight retained candidates, encoding batch
size 4,096, sequence-level sampling, and the query's recorded planner seed.
Both arms use the same frozen checkpoint, low-level solver, latent-prior
procedure, reset state, goal, evaluation budget, and benchmark success event.

Apply the master environment-substitution rule directly to these paired
development successes: replace Cube with TwoRoom if B0 is above 85% or below
5%, or if B1 exceeds B0 by less than 5 percentage points. With 12 queries this
means the first two triggers are respectively at least 11 or exactly 0 B0
successes, while the third trigger fires unless B1 has at least one more
success than B0. No selective reruns are allowed if the released B1 GPU path
exhibits its already documented same-seed non-bitwise behavior; retain the
single predeclared execution and record that limitation. These P2 rates and
the resulting environment choice are developmental, not final baseline
estimates.

## A-023 — Closed-loop release-gate metadata errata

The first B1 D75 gate, job `294766`, stopped before loading the world model
because the immutable candidate manifest spells its partition as `P2` while
the new validator expected lowercase `p2`. The second gate, job `294770`,
stopped immediately after context construction because the released
diagnostics field named `ctx.latent_dim` actually comes from
`_infer_latent_action_dim` and equals the 32-dimensional macro-action width;
the flattened encoded state used by planning and all scorers is 192
dimensional. Neither failed gate executed a planner step or produced an
outcome. Their dependent jobs were cancelled without running.

Correct the validator to require the manifest's exact `P2` value, require
`ctx.latent_dim == 32` as an artifact macro-width check, and independently
require both cached query state latents to have shape `(192,)`. These are
metadata/field-meaning corrections only. They do not alter a query, seed,
model, score, solver, budget, or endpoint.

## A-024 — CEM generator-seed audit erratum

Replacement B1 gate job `294780` passed query, model-context, state-latent,
macro-width, and planner-budget validation, then stopped before building the
empirical bank or executing a planner step because pinned
`stable_worldmodel==0.0.6` does not expose a `.seed` attribute on `CEMSolver`.
It retains the configured seed in its private Torch generator. Audit the
effective seed with `solver.torch_gen.initial_seed()` for both ordinary CEM
solvers and the released empirical-macro solver. This inspection change does
not alter the generator or its random stream. Job `294780` produced no
outcome, and its dependent jobs were cancelled without running.

## A-025 — B1 D75 release gate and paired-array release

After the pre-outcome corrections in A-023 and A-024, full-budget B1 gate job
`294783` completed one 150-step query with exactly 30 high-level solves, 1,800
high cost calls, and 2,160,000 candidate evaluations. Its saved empirical bank
has shape `(4096, 2, 32)` and `raw_macro_len=25`; the state-latent trace has
shape `(150, 192)`. Execution took 100.859 seconds on an RTX A5000, with
225,588,224 peak allocated and 352,321,536 peak reserved GPU bytes. The output
HDF5 SHA-256 is
`f3a7795fb1a89989e708b2ea0d8946d560ade62a672e9b063fa7066a1411299b`,
and its complete checksum inventory validates.

The gate query is an implementation smoke and is excluded from the 12-query
decision aggregate. Release the paired B0/B1 array as job `294793`; its
predeclared aggregate and environment decision is job `294798` and may run
only after every array task succeeds.

## A-026 — P2 D75 environment decision

All 24 tasks in paired B0/B1 array `294793` completed successfully and the
predeclared aggregate, job `294798`, passed its checksum, query-matching,
planner-budget, trace-shape, and empirical-bank audits. On the 12 shared P2
D75 queries, B0 succeeded on 2 queries (`16.67%`) and B1 also succeeded on 2
queries (`16.67%`). B0 therefore triggered neither absolute-difficulty bound,
but B1's improvement was 0 percentage points and triggered the frozen
less-than-5-point rule in A-022.

The second core environment is consequently TwoRoom, replacing Cube. These
rates are development-only and are not final baseline estimates. The decision
HDF5 SHA-256 is
`3f37ce353506ed46468a3f00eb70780858b18ac11f29fc160efadfc78ad356dd`,
and the aggregate verifies that all 24 tasks used the same immutable query
artifact and paired query identities.

## A-027 — Locked PushT P3 stratum-3 candidate sampling

Before capturing or executing a P3 candidate, freeze the locked PushT audit to
the master protocol's 24 episode-distinct query pools and 64 candidates per
pool. Use only the P3 episode partition. Under root seed `20260728`, order
D75-eligible episodes by domain-separated SHA-256 namespace
`p3_stratum3_pool_episode`, choose each within-episode source with namespace
`p3_stratum3_pool_start`, and derive its 63-bit CEM seed with namespace
`p3_stratum3_cem`. Capture the final population of the unchanged B0 D75 high
CEM (`1200/60/10`, horizon 2, action block 1), then select 64 population
indices by namespace `p3_stratum3_candidate`. Save the same complete actions,
nominal costs, first macros, predicted first subgoals, and exact elite-mean
solver check as P2.

The capture code was generalized by replacing the literal P2 hash namespace
with the partition-derived namespace. Before release, its P2 compatibility
test reproduced all 12 prior P2 query records and every one of the 768 prior
selected candidate indices exactly. A one-pool reduced-budget P3 smoke must
pass before the full 24-pool capture. Candidate capture is outcome-blind: no
attainment label or learned scorer is read, and no P3 value may choose a
tolerance, architecture, sigma, calibrator, weight, or query count.

## A-028 — P2 fixed-subgoal aggregation erratum and dependency repair

Fixed-subgoal execution array `294652` completed all 60 predeclared tasks and
its task artifacts remain the sole inputs to the aggregate. Aggregate job
`294658` then stopped after four seconds, before creating `aggregate.h5`, a
label, a tolerance decision, or any scientific result. The failure was an API
error in an internal consistency assertion: `final_raw_rmse` is a NumPy array,
but the assertion invoked the Torch-only method
`final_raw_rmse.square()`. Replace only that expression with the equivalent
NumPy operation `np.square(final_raw_rmse)`. The asserted equation, tolerances,
inputs, endpoints, and all protocol settings are unchanged. Do not rerun the
60 successful execution tasks.

Jobs `294677`, `294685`, `294687`, `294696`, `294706`, `294750`, `294751`, and
`294752` were submitted behind the failed aggregate and had not begun
execution. Cancel that stale chain and submit replacements behind a corrected
aggregate and the unchanged real-frame aggregate `294668`. To prevent a
replacement from silently reading an obsolete job directory, downstream
launchers must receive their upstream aggregate, label, scorer-selection,
null-training, autoencoder-training, and calibration job IDs explicitly at
submission and record them in provenance. This is dependency/provenance
bookkeeping only; it may not change a model, seed, candidate, label rule,
calibrator, planner, budget, endpoint, or selection rule.

Corrected aggregate job `294836` completed successfully from the unchanged
array `294652`; all checksum entries validate, `labels_assigned` remains
false, and its `aggregate.h5` SHA-256 is
`c0e66301f706cbd7c4f95c29a87ec3f3250b4511aa7f423d50385bc7ae072339`.
The replacement downstream IDs are label job `294838`, true-scorer selection
job `294839`, null-training array `294841`, autoencoder-training array
`294842`, and calibration job `294843`. Job `294838` waits on the unchanged
real-frame aggregate `294668`; every later replacement is linked by `afterok`
dependencies and explicit upstream-ID exports.

The replacement augmented closed-loop release gate is job `294845`, its
full P2 weight grid is array `294846`, and the predeclared weight-selection
aggregate is job `294847`. They depend in that order on calibration job
`294843`; the gate and grid both receive true-scorer job `294839` and
calibration job `294843` explicitly.

## A-029 — Frozen PushT development selections before P3 execution

All P2 development jobs and checksum inventories completed before any P3
candidate was executed. Real-frame aggregate `294668` evaluated 1,536 locked
candidates across the two real-frame strata with five executions each. It
selected standardized latent-RMSE tolerance
`delta = 0.7168711644368866` (grid index 8) with combined primary Cohen's
kappa `0.825350573356934` and observed agreement `0.9127604166666666`.
Its HDF5 SHA-256 is
`d748303d886df769ed3770cab3ef0b5e2b664848923219e1f47ce7997d51e971`.

The P2 imagined-candidate audit contains 768 candidates. Its physical
attainment prevalence under the primary at-least-3-of-5 label is
`0.46484375`, hence failure prevalence is `0.53515625`. Freeze M1 width 512;
M2 width 1024 and sigma 0.25; and the three fixed-seed M3 replicas. The
development mean-seed AUROCs for true versus null are respectively M1
`0.6358248084310772` versus `0.5472248915786915`, M2
`0.9286429900427325` versus mismatched-pair null `0.922538682950877`, and
M3 `0.6668802151842083` versus `0.6160056885690205`. The capacity-matched M2
autoencoder control has development mean-seed AUROC `0.8404997035310474`.
These are development diagnostics only: they make no promotion claim, and no
P2 value may alter the already declared P3 gate or interpretation rule.

Freeze the P2-selected closed-loop weights to M1 `2.0` (5/12 development
successes), M2 `1.0` (4/12), and M3 `0.25` (3/12), using the predeclared
success-count rule and smaller-weight tie-break. The corresponding immutable
HDF5 SHA-256 values are: labeled candidate audit `294838`,
`72031cd0ea7a02af2a33c61fb3db6f42c47b2982a31a544a2fe3fff011fc76c4`;
true-score selection `294839`,
`63bad1d8c97902f682a6aacfa21ef451f8c0cee7373a501b2de0d8f3e4b10ba1`;
null/control calibration `294843`,
`eced1f2842bc7ba9bda81ae4d2647200c3f30c7b1f25679025cfb9c60f9cad3f`;
and weight selection `294847`,
`0bec312e2b85ec462501b2643d0d0c003408d59328ce8919f8f0f6d7ffdf1818`.
P3 may report these frozen configurations but may not revise them.

## A-030 — Locked PushT P3 real-frame candidate sampling

Before generating a P3 real-frame pool, freeze both real-frame strata to 24
pools of 64 candidates, five executions per candidate, and Delta 25. Select
one source per episode after ordering D25-eligible P3 episodes with namespace
`p3_real_source_episode`; use disjoint episode sets for the two strata. Select
the within-episode source step with namespace `p3_real_source_step`. In the
same-trajectory stratum, the target is exactly source step plus 25. In the
cross-trajectory stratum, order target episodes with namespace
`p3_real_cross_target_order`, apply the one-position cyclic derangement, and
select the target step with namespace `p3_real_cross_target_step`. Every hash
also includes dataset identity, root seed `20260728`, and the applicable
episode and stratum identifiers. Do not exclude initially successful or
otherwise ambiguous candidates.

The pool generator was generalized only by making the partition, pool count,
classifications, and `p2`/`p3` hash namespace explicit. Generalized script
SHA-256 is
`6e210f49bad561ba3e2a6146ba22327fc5932c2ba0097155f0a46a06b68b7914`;
the original P2 script with SHA-256
`08c2f1c2cb41d7dff3b498b6e43c65c67bc9b960a4a0d34e69d5565390aa63ac`
remains in the immutable local control snapshot. Compatibility job `295087`
reproduced the original P2 `candidate-pools.h5` bit for bit, SHA-256
`3980cc3cd4df9243dfdeeca2a7d95626a1282ecfd7605a1cc84bc4e6e4ecd8e6`,
including every source/target episode and row hash. P3 real-frame generation
is outcome-blind; its values cannot tune a threshold, model, calibrator,
weight, query count, exclusion, or sample size.

## A-031 — P3 real-frame episode-capacity erratum

First P3 real-frame generation job `295088` stopped before creating an HDF5
candidate artifact. The locked P3 partition has 1,810 D25-eligible episodes,
whereas the one-source-per-episode clause in A-030 would require 3,072
episodes for two strata of 24 by 64 candidates. This was detectable from the
already frozen partition metadata: the 1,810 episodes contain 179,748 unique
D25-valid source rows, every episode has at least 24 such rows, and therefore
the candidate count—not row capacity—is feasible. No candidate execution,
attainment outcome, learned score, or P3 selection statistic was observed.

Supersede only A-030's one-source-per-episode rule. Retain the same
domain-separated episode order, then assign alternating episodes to two
disjoint sets of exactly 905 episodes. Within each stratum, use all 905
episodes: the first 631 in its frozen order contribute two adjacent candidate
slots and the remaining 274 contribute one, totaling 1,536 candidates. This
keeps repeated rows from an episode inside one 64-candidate pool. Select each
within-episode source step with the A-030 namespace plus occurrence index;
if two hashes collide, advance cyclically to the first unused valid step. For
the cross-trajectory stratum, retain the cyclic episode derangement and apply
the same occurrence-index and cyclic-collision rule to target steps. Require
all source rows within an episode to be distinct and require no source episode
to appear in both strata. The revised generator SHA-256 is
`7838f080466fab122c444b0ab1ee0594f416bc3d1511e1931423d5b03eddcd60`.

This correction changes neither the predeclared 24-by-64-by-5 sample size nor
any model, scorer, tolerance, calibrator, weight, endpoint, or promotion rule.
It is fixed from partition capacity alone before a successful P3 candidate
artifact exists.

Post-correction compatibility job `295089` again reproduced the original P2
candidate HDF5 bit for bit with SHA-256
`3980cc3cd4df9243dfdeeca2a7d95626a1282ecfd7605a1cc84bc4e6e4ecd8e6`.

## A-032 — P3 real-frame candidate artifact

Replacement generation job `295090` completed under A-031. Its checksum
inventory validates; the artifact contains exactly two strata, 24 pools per
stratum, 64 candidates per pool, 905 unique source episodes per stratum, and
at most two unique source rows per episode. Its `candidate-pools.h5` SHA-256 is
`390caf5b1ec32975a36d41242d38e039c2ad3c6ca1d9e1c727066c5e172ac771`.
This artifact is now the immutable P3 real-frame input. Its initial-state
diagnostics and all later P3 values remain forbidden as tuning inputs.

## A-033 — P3 execution gates and P2 compatibility proof

After the immutable P3 pre-execution lock was written, real-frame smoke job
`295091` was allocated to `gpu02` but remained in Slurm's configuring state;
its batch step never began and it created no output directory. It was canceled
and replaced without changing code or inputs. Replacement real-frame smoke
job `295092` completed on `gpu03`, and fixed-subgoal smoke job `295095`
completed on the same node. Each exercised two candidates at the explicitly
reduced smoke budget, passed the solver-equivalence self-test with maximum
absolute error zero, produced a valid checksum inventory, and is marked
`excluded_from_p3_audit=true`. Neither smoke outcome may enter a P3 estimate
or change any frozen choice.

The execution and aggregation programs were generalized only over partition,
pool count, and partition-specific classifications. Their SHA-256 values are:
real-frame execution
`89ecbb43fd066f4fb489aa9e9cfcacd46635563e81abd1d7dbd72df67db37862`;
fixed-subgoal execution
`d359b01b9819ad15c968cb5561d5232144ca3bc065124043378b8046082eaa38`;
real-frame aggregation
`cbf07550cc2340df3a43cdd70e6b08f517b647457e4f227e3e3ff9b7d63ec655`;
fixed-subgoal aggregation
`c8e8e88e5ee286f70e863aeaaecfc8541d76280e879a611bb899f22bbc8cc384`;
and tolerance labeling
`4b5e828c671ca742b50bda445d1389fa0d97a4e12cc1f8f3bcd4e67b8fcb04c4`.

Before any full P3 execution array was released, the generalized code was run
against the frozen P2 inputs. Real-frame compatibility job `295094`
reproduced aggregate HDF5 SHA-256
`d748303d886df769ed3770cab3ef0b5e2b664848923219e1f47ce7997d51e971`
bit for bit. Fixed-subgoal compatibility job `295096` reproduced
`c0e66301f706cbd7c4f95c29a87ec3f3250b4511aa7f423d50385bc7ae072339`
bit for bit, and label compatibility job `295097` reproduced
`72031cd0ea7a02af2a33c61fb3db6f42c47b2982a31a544a2fe3fff011fc76c4`
bit for bit. These implementation checks do not amend the pre-execution lock,
the P2 selections, the P3 sample sizes, or any promotion criterion.

## A-034 — Frozen P3 scorer-audit operationalization

Before P3 label job `295106` or any P3 learned-score evaluation began, and
without reading a P3 execution value, freeze scorer-audit script SHA-256
`f5b1cbae0eaff0d637bd90359c62dcafd3d9d291f34fc36f229ccf8f9b8dc7fb`
and launcher SHA-256
`5acc56da8324fa9d2401988ce8efb3bcd64b9fe5f3c2ed748d4c9b1037a1f322`.
The script hard-checks the immutable P2 selection and calibration HDF5 hashes,
the P3 candidate lineage, the P1 statistics and noise hashes, all 21 selected
true/null/control checkpoint hashes, all selected architectures, sigma, seed
orders, label rules, pool geometry, bootstrap settings, and score directions.
An outcome-blind preflight verified every P2 artifact, calibrator, and
checkpoint path, and a synthetic tied-score test verified the bootstrap AUROC
implementation against the audit metric implementation.

Operationalize the already frozen three-seed ensemble as follows. For a true
scorer, apply its corresponding seed's P2-frozen Platt map and average the
three failure probabilities. Consistent with A-020, do not fit or apply a
calibrator to a null. Average the three same-unit raw null scores, then compare
the AUROC of that null ensemble with the AUROC of the calibrated true
ensemble; AUROC does not require the two score vectors to share a numerical
scale. This yields the paired true-versus-own-null AUROCs used by the existing
promotion gate. Preserve true-scorer isotonic results as a sensitivity only.

Generate one shared NumPy PCG64 pool-resample table with seed `20260728`:
10,000 rows, each containing 24 pool indices sampled with replacement. Apply
each row identically to every true/null/control comparison, retaining all 64
candidates in every selected pool. Report two-sided 2.5th and 97.5th
percentiles with NumPy's linear quantile rule. Promotion requires the frozen
point AUROC threshold and a strictly positive lower endpoint for the paired
true-minus-null AUROC interval.

For the capacity-matched M2 autoencoder, average its three same-unit raw
reconstruction scores before computing ensemble AUROC. The frozen phrase
"beats the autoencoder" means strictly larger primary-label ensemble AUROC;
also report its paired bootstrap interval, but do not add that interval as a
new promotion threshold. G0a and G0b remain reported geometry diagnostics:
neither has a frozen own null or a P2-selected closed-loop weight, so neither
can enter P4 under the current lock.

## A-035 — Materialization of the frozen P4 PushT queries

The master protocol and A-021 fixed 40 P4 D75 evaluation seeds and one query
per seed, but did not serialize their source/goal tuples. Before P3 scorer job
`295115` or any promotion result exists, materialize that outcome-blind input
from the already frozen P4 partition and latent cache. Use root seed
`20260728` and namespace `p4_closed_loop`. Order all D75-eligible P4 episodes
by domain-separated SHA-256 namespace `p4_closed_loop_pool_episode` and take
the first 40. Within each episode choose a D75-valid source by namespace
`p4_closed_loop_pool_start`. Derive the unique 63-bit planner/environment seed
with namespace `p4_closed_loop_cem` over query index, episode, and source row.
The goal is exactly source row plus 75 in the same episode.

Read source and goal latents only from immutable P4 latent-cache job `294788`,
HDF5 SHA-256
`b8e9ab39497fa64b9f489e36a2dfc1462f8e77f455eaf8d7069750aadd83ffc7`.
The query artifact contains no CEM candidate population, learned score,
attainment label, environment outcome, or success value. It may not be
regenerated or filtered after a P3 result. Generator SHA-256 is
`7a3349f029f2fa0c7100a2cb82c19f8025ea5665bb524c9ddd6e1fbcd62ffa6f`;
launcher SHA-256 is
`9ffa314d9d7a8c8da396ffbf6fec4bbcaf23e72f3005adb8bdca3177b2b52991`.

Materialization job `295120` completed before the P3 promotion job. Its
checksum inventory validates; it contains exactly 40 episode-distinct D75
queries and 40 unique planner/environment seeds, with no outcome fields. Its
`queries.h5` SHA-256 is
`098559f55bf1e1b6cde440349e7bbe1debfd3d5441d9bf1b1e673f031c1758cd`.
This is the immutable PushT P4 query artifact.

## A-036 — P4 closed-loop runner compatibility and release rules

Before a P4 outcome, generalize the validated P2 closed-loop programs only
over the P2/P4 query schema, query count, partition classification, and output
classification. The augmented runner additionally requires the locked P3
audit, rejects an unpromoted method, and hard-checks its frozen weight: M1
`2.0`, M2 `1.0`, or M3 `0.25`. Baseline B0 and B1 use the same 40 P4 queries
and may run after the P3 audit completes, irrespective of which learned arms
promote. No failed learned arm may receive a P4 execution.

Generalized augmented-query script SHA-256 is
`3226ac321fe95fa457559fd493a1cf1201b162e2ac7a3503dbf982ce9fdf32dd`;
generalized B0/B1-query script SHA-256 is
`dc683135dff00e01f77bd6fb9c5bdb83e15f0f7092e6efd181cee8501ff21202`;
P4 promoted-arm array launcher SHA-256 is
`f061839827adddeaa048a2c24d3654a83399dcb2d5ba565de509d10e594775ce`;
and P4 B0/B1 array launcher SHA-256 is
`45ccb18293fd5512c11dc6265a88ba454890ec9c89bf26fda90377b56ec3c15a`.

Before release, generalized augmented compatibility job `295121` reproduced
the original P2 full-budget M2 gate HDF5 bit for bit, SHA-256
`4812217dbc97b879b0ef14e28f1df4b40f46f62216ee2777a80608258cfe1136`.
Generalized baseline compatibility job `295126` reproduced the original P2
full-budget B1 gate HDF5 bit for bit, SHA-256
`f3a7795fb1a89989e708b2ea0d8946d560ade62a672e9b063fa7066a1411299b`.
Both replacement checksum inventories validate. These checks are P2-only and
cannot change any P3 promotion or P4 result.

## A-037 -- Frozen P4 aggregation and inference operationalization

Before any P4 task began and without reading a P3 promotion or P4 outcome,
freeze P4 aggregation script SHA-256
`d8837f31c794d6280e192f660ec0e538a747d11bb9ca185b2f4ec56dc74c5498`
and launcher SHA-256
`cd99b35053a6dad973bc4d837cda31cc77f924b6f5e7f5c7de462bc0c8b0ba80`.
The aggregator requires the immutable 40-query artifact, the checksum-valid
P3 promotion artifact, all 80 B0/B1 query results, and exactly the learned-arm
roots named by the P3 promotion decision. It rejects an omitted promoted arm,
a supplied failed arm, changed query identity, planner budget, scorer weight,
cost count, scorer/checkpoint/calibrator/statistics/noise lineage, or checksum.

For each executed arm, report the success count of 40 and success percentage.
Generate one shared NumPy PCG64 query-resample table with seed `20260728`:
10,000 rows of 40 query indices sampled with replacement. Apply every row
identically to every arm. Report two-sided 2.5th and 97.5th percentiles using
NumPy's linear quantile rule for each success rate and each paired percentage-
point difference from B0. The complete query/evaluation seed is the unit; no
planning step is an independent observation.

Also report a two-sided exact paired sign-test p-value over discordant query
outcomes for each available contrast against B0. M2 versus B0 remains the
single primary endpoint and is not included in the Holm secondary family. If
M2 fails the locked P3 gate, record that the primary endpoint was not
evaluated rather than running it. Preserve unadjusted p-values for executable
PushT secondary contrasts (B1 and any promoted M1/M3); defer the final Holm
adjustment until all executable predeclared secondary-family contrasts,
including the second environment, are available. Arms made ineligible by a
locked promotion gate are not retroactively executed to fill the family.

Scheduled synthetic integration job `295143` completed successfully on the
cluster in the released container. It validated 40 matched queries across B0,
B1, and a promoted M2 arm, all lineage and cost gates, HDF5 serialization, the
shared 10,000-resample bootstrap geometry, and the exact sign-test edge case.
This test contains fabricated outcomes only and cannot affect any thesis
selection or result.

## A-038 -- Mechanical P3-to-P4 gate dispatch

Before P3 execution completed, freeze dispatcher SHA-256
`7fc4f2d3d2ea76c0a600e4473398b93d8185c3e811db48923cebac242df39abb`
and launcher SHA-256
`a4fefcbbe1dd5d5bec16da4fb8fa2c06f63b6112df78013e66a2d82ec8bf4f38`.
After locked scorer-audit job `295115` succeeds, the dispatcher verifies its
complete checksum inventory and the consistency of every arm's Boolean
promotion record with the promoted-arm list. It also hard-checks the frozen
baseline, learned-arm, and aggregate launcher hashes. It then performs only
the following mechanical actions:

1. retain already queued B0/B1 P4 array `295131`;
2. submit one 40-query array for each promoted learned arm, in M1/M2/M3 order,
   with each array dependent on the preceding P4 array;
3. omit every arm that failed the locked promotion gate; and
4. submit the frozen P4 aggregate after the last required array.

No candidate, label, metric, threshold, weight, seed, or outcome is changed or
selected by this dispatcher. It reads no P4 result. The canonical dispatch
receipt directory makes a second dispatch fail closed. A synthetic gate test
passed under the cluster host's Python 3.6.8: a fabricated promotion of M2
submitted M2 and the aggregate in the correct dependency order while never
submitting M1 or M3.

One-shot dispatcher job `295148` was submitted with dependency
`afterok:295115` while the P3 real-execution array was still in progress. Its
only scheduler-side effect before that dependency succeeds is to remain
pending.

## A-039 -- Erratum: second-environment substitution must evaluate Cube

A-022 and A-026 incorrectly applied the master protocol's second-environment
substitution thresholds to PushT development successes. Those PushT B0/B1
measurements and their checksum-valid artifact remain valid PushT development
diagnostics, but PushT difficulty cannot establish whether Cube is a useful
second environment. Retract only the A-026 conclusion that TwoRoom had already
replaced Cube. The second-environment choice is reopened before any Cube or
TwoRoom candidate, scorer, or confirmation outcome has been observed.

Apply the stated substitution rule to matched Cube development executions at
Cube's longest released offset, D75: replace Cube with TwoRoom if Cube B0 is
above 85% or below 5%, or if Cube B1 improves over Cube B0 by less than five
percentage points. Query count, exact sampling, and the integer realization
of those thresholds will be frozen after reading episode IDs and lengths only
and before running a Cube outcome.

Freeze Cube episode assignment under root seed `20260728` using the first 64
bits of

`SHA256("cube_single_expert\0" + "20260728\0" + episode_id)`

and the same P1/P2/P3/P4 intervals as PushT: 70/10/10/10 percent. No local
Cube episode outcome or source/goal identity has previously been exposed, so
Cube P0 is empty. The staged Cube dataset is the primary-source artifact from
`quentinll/lewm-cube` revision
`02a19a67a0dc8c9d6215f89c19e0a597691e152a`, with 101,942,558,720 expanded
bytes and recorded SHA-256
`0664d507c4ff12009010644c9ae950836f954e700c172ccf22e7423af1a55625`.

Outcome-blind schema-inspection launcher SHA-256 is
`fff1b39dfcdae80e165bc419bef82e2f2dd391a3adbaccf76fc78d4c8e51c50f`;
partition launcher SHA-256 is
`ce6f7a3d4c6e18aa6604cd16bf3247979be13167291b07f937e3f815b92f7a5c`.
Both operate only on HDF5 schema, episode IDs, episode lengths, and file
provenance. They do not read success events, physical states, images, actions,
latents, candidates, or scorer values.

## A-040 -- Frozen Cube P2 D75 substitution-gate queries

Outcome-blind Cube schema job `295153` and partition job `295154` completed.
The dataset contains 10,000 episodes of exactly 201 rows each. Seeded
assignment produced 7,003 P1, 957 P2, 1,007 P3, and 1,033 P4 episodes; the
partition TSV SHA-256 is
`39b59b7162d8cf932b5cab82a7f1a4b9f2e80be3fb5401b94d8e14335d91e2c3`.
Both jobs read only schema, episode indices, step indices, offsets, and
lengths. Their checksum inventories validate.

Before any Cube planner execution, freeze 12 episode-distinct P2 D75 queries,
matching the PushT development-gate sample size. Order all eligible Cube P2
episodes by domain-separated SHA-256 namespace
`cube_p2_d75_environment_gate_episode`; select the first 12. Within each
episode, choose a source step by namespace
`cube_p2_d75_environment_gate_start` modulo the 126 valid D75 starts. Derive a
unique 63-bit planner/environment seed from namespace
`cube_p2_d75_environment_gate_cem` over query index, episode, and source row.
The goal is exactly 75 rows after the source in the same episode.

Run each frozen query once with Cube B0 and once with Cube B1 using the
released Cube D75 planner row: 150 primitive steps; high horizon 2,
receding horizon 1, action block 1, replan interval 5, and CEM `1200/60/10`;
low horizon/receding horizon/action block `2/1/5` and CEM `1200/30/150`.
B1 changes only the high-level proposal solver to the released empirical
macro configuration. With 12 paired queries, the absolute Cube B0 triggers
are exactly 0 successes or at least 11 successes. The improvement trigger
fires unless Cube B1 has at least one more success than Cube B0. No selective
rerun is permitted.

Query generator SHA-256 is
`b3c519f4157c3515409a46c6235241597271009c44e910d28c46f68fb036a0f5`;
launcher SHA-256 is
`b10c7f7cf05e2ab26188631385287cb8362eb9daafa03f37cce07c0f419990dc`.
The query artifact contains no pixels, actions, states, latents, candidates,
labels, rewards, successes, or planner outcomes.

## A-041 -- Frozen Cube renderer and B0/B1 gate implementation

Query materialization job `295156` completed before any Cube planner or
environment step. Its checksum inventory validates. The immutable query HDF5
SHA-256 is
`5c6036906bd94f74c2041952d26e0ad67784d0c9966d8519880465db8a6ee5ce`,
the query manifest SHA-256 is
`6afc587bb1756a10b01ae85db5a90f1267ab5031e0f0dbd6e5ca2700b9df2b64`,
and the checksum-inventory SHA-256 is
`47ed0e098edaca137b054a9ee459f11cc90bbd65b157cbce08b0adc55566e38b`.
It contains exactly the 12 episode-distinct identities and unique seeds frozen
in A-040 and contains no outcome-bearing field.

The artifact's default EGL renderer cannot create a headless context on the
allocated cluster GPU nodes. Job `295160` failed at renderer import before
model/context construction, planner execution, or an environment step. Backend
probe job `295165` confirmed that EGL was unavailable and that no system
OSMesa library was installed. The first user-prefix setup job, `295166`, failed
during package retrieval and did not execute thesis code. These failures
contain no Cube outcome and therefore permit an implementation correction.

Use a user-owned, non-root OSMesa prefix at
`software/osmesa-ubuntu22.04`, assembled from the pinned Ubuntu 22.04 packages
recorded in its manifest. No system file or cluster module was changed. The
prefix manifest SHA-256 is
`c978482072874a8ef14502f006e5b2f88754b4524a06476019f22322cb8a9b33`,
its complete checksum-inventory SHA-256 is
`c27bed9ce81493520f20a5bf2e8f636cd5cf5e1757be8617280a48e337328a94`,
its installed-file inventory SHA-256 is
`0ce98ecf0d0737dc43be2a7b80385b1fbc83323fb97842672ced238375dbf41e`,
and its import-test SHA-256 is
`96a3ee53aafda3ba929a4bdeb5739402ba3636c7281c118955442256f626be49`.
The setup program SHA-256 is
`e142a3c10aadbd8067ec1a832d9bf1f0f89eeec2a46fe2aecc07b5bbb32490`.
Set `MUJOCO_GL=osmesa`, `PYOPENGL_PLATFORM=osmesa`, and prepend only this
prefix's library directory. This changes the off-screen rendering backend,
not benchmark physics, checkpoint weights, observations, actions, planner
budgets, or success events.

No-step B1 smoke job `295180` completed in the released container with the
frozen query, checkpoint, evaluation configuration, and OSMesa prefix. It
constructed the environment context and `4096 x 2 x 32` empirical-macro bank,
then stopped before the first planner or environment step. Its reporting rule
explicitly excludes it from results. The smoke HDF5 SHA-256 is
`7df7a1edb00244a3bad9dc0f6769a440cf9d552298c37c7c418960415423241f`,
identical to the earlier successful no-step smoke, and its manifest SHA-256 is
`1b51d6faa11e1d0ed96e7f003af688948a4ce2ca07d0f1afd8a1db54705eca1f`.
The no-step launcher SHA-256 is
`c50402478ca051caabce4bffc898eda0edf72abcb0fbc49ae7e8d87c81a2620a`.

Before any Cube outcome, freeze the scientific single-query program SHA-256
to
`478de34a5451778e47787bea131d321a852fbef7df450ac2d245f722ae437422`.
It hard-checks the query lineage, the dataset artifact's exact
101,942,558,720-byte size and recorded SHA-256, hierarchical checkpoint SHA-256
`50aaae8539904e86a835939f8d85af56ca83549ef181d0f6bca7e444437fe4c4`,
and released `hi_cube.yaml` SHA-256
`664bd25376ce94bd952af2d7b1afc193ab9623d32e9e5d2c28895a1eaf75c571`.
It applies the exact A-040 B0/B1 budgets, requires 30 high-level plans, 30
completed low-level blocks, 150 primitive steps, 1,800 high-level cost calls,
and 2,160,000 high-level candidate evaluations, and saves complete current,
goal, subgoal, and empirical-bank audit traces. B0 and B1 share each frozen
query and seed; only B1 replaces the high-level CEM proposal solver with the
released empirical-macro solver.

Freeze the `B0/B1 x 12` array launcher SHA-256 to
`b56aee6dc3f293d8b0e994970754c1b011e21a8bcce0443489b9b572af3b3014`.
Its maximum concurrency is one, an operational scheduling limit that does not
change any task. Freeze the decision aggregator SHA-256 to
`381b40530d2379477a09c9df4e5a9ba0242c289098c11d52e59b435db6ceb963`
and its launcher SHA-256 to
`776456592c37619c5e7e9fb4be8e869c73ee11b247c8af8882e3d978037fb6d8`.
The aggregator rejects a missing or extra task, changed query identity,
lineage, solver, empirical-bank geometry, budget, cost count, trace shape,
success value, or checksum. It then mechanically applies only A-040's three
triggers and records `Cube` or `TwoRoom`. These 12 paired development outcomes
are used only for second-environment selection and are never final estimates.
No selective task rerun is permitted.

Release the frozen 24-task array as job `295185`. Predeclare decision job
`295187` with scheduler dependency `afterok:295185`, so it can read the gate
only after every B0/B1 task completes successfully. Recording these scheduler
identifiers changes no frozen query, method, threshold, or implementation.

## A-042 -- Erratum: Cube post-step goal-info compatibility

Array `295185` exposed a Cube-specific diagnostic schema error. Task 0 failed
after its first environment transition because OGBCube replaces
`world.infos` during `world.step`, whereas the shared PushT-oriented
`InstrumentedHierarchicalPolicy.after_env_step` expected a `goal` field to
remain present. Task 1 reached the identical exception while the array was
being canceled. Tasks 2--23 never started, and dependent decision job `295187`
was canceled. The two attempted task directories contain only their initial
`provenance.txt`; neither contains a result HDF5, result manifest, checksum
inventory, success flag, success rate, or completed evaluation. No success or
other Cube outcome was available to inspect or to motivate a scientific
choice.

Correct only the diagnostic interface by using a Cube-specific world loop.
As before, it installs the immutable goal fields immediately before
`world.step`, when the policy chooses the action. After the environment has
already executed that action and replaced `world.infos`, install the same
immutable fields a second time immediately before the post-step diagnostic
encoder. This second installation cannot affect the selected action, the
completed environment transition, benchmark termination, planner proposals,
costs, or the next iteration, for which the released loop already reinstalls
the goal. Record and require exactly 150 post-step goal reinstatements in every
completed task.

The corrected scientific single-query program SHA-256 is
`5058c2f683d0e306b78202f8e40db78d87fc036cef64b3087c511951abadd3dc`.
The corrected decision aggregator SHA-256 is
`4e96c83cf5407019be2e280b53e9e120119be46d4c6ab50e8e985610940f0636`;
it rejects a missing or changed adapter declaration or reinjection count. The
array and aggregate launchers remain byte-identical to A-041.

No-step adapter probe job `295193` completed in the released container after
the correction. It constructed a synthetic post-step info mapping with the
goal absent, applied the adapter, and encoded finite current and goal tensors
of shape `1 x 192`; it executed zero planner or environment steps. Its HDF5
remains bit-identical to both earlier no-step smokes, SHA-256
`7df7a1edb00244a3bad9dc0f6769a440cf9d552298c37c7c418960415423241f`.
Its manifest SHA-256 is
`3592541179f734907a0ff5909783916805a63f70fa62835b5d51ddd861211903`.

Exclude all of array `295185` from the gate. A fresh execution must run the
entire predeclared 24-task grid, not selectively retry tasks 0 or 1, and must
use the same immutable queries, arms, seeds, budgets, checkpoint, and decision
thresholds. A-040's no-selective-rerun protection remains in force: the whole-
grid implementation retry is allowed only because the documented failure
produced no result or visible outcome and the correction was dictated solely
by the missing dictionary key.

Release the corrected whole-grid execution as array `295194` and predeclare
decision job `295196` with dependency `afterok:295194`. No output from the
excluded array is an input to either job.

## A-043 -- Locked P3 decision and P4 aggregate seed-validation erratum

The complete locked PushT P3 chain finished checksum-valid. Promotion artifact
job `295115` has audit-HDF5 SHA-256
`aa99a8a7846aafa112b50d451005db2afb3b2406193be26dd9ab40e3b55351bb`
and manifest SHA-256
`9a6dc80f4660f8065c2e534dda93226dc29cc226d7c72eed229ad811f3a18f99`.
All three learned signals passed the frozen AUROC-at-least-0.70 condition but
failed the independently required positive paired improvement-over-own-null
interval:

- M1: true AUROC `0.7493084172`, null AUROC `0.6997133336`, paired improvement
  interval `[-0.1152828230, 0.2285714286]`;
- M2: true AUROC `0.8031891640`, null AUROC `0.7572042857`, paired improvement
  interval `[-0.0143124987, 0.1328138658]`; and
- M3: true AUROC `0.8510355825`, null AUROC `0.5828976601`, paired improvement
  interval `[-0.0697737768, 0.5983939798]`.

Therefore `promoted_arms` is empty. In accordance with the frozen gate, M1,
M2, and M3 receive no P4 execution and the M2-versus-B0 primary endpoint is
recorded as not evaluated, not as a zero effect. The mechanical dispatcher,
job `295148`, submitted no learned arrays. Its dispatch JSON SHA-256 is
`b8cdb9ff437f9c99c7698281fdb468be0935a7a3c933dec34b401be80ce552a3`.
All 80 locked B0/B1 tasks in array `295131` completed successfully.

Predeclared aggregate job `295518` failed before reading a P4 task or writing
an aggregate result. Its output directory contains only `provenance.txt`. The
aggregator incorrectly required training seeds `[11, 22, 33]`, contradicting
A-007 and the complete P3 artifact, which both record scorer seeds
`[20260728, 20260729, 20260730]`. This is a validation-constant error, not a
scientific ambiguity.

Correct only that constant. The replacement aggregate program SHA-256 is
`62593e26926bf74cd4442c50daacad37a408b94ec1a7db84da5dfa747833ac0b`.
The launcher remains byte-identical, SHA-256
`cd99b35053a6dad973bc4d837cda31cc77f924b6f5e7f5c7de462bc0c8b0ba80`.
The bootstrap seed and samples, hypotheses, promotion decision, query set,
task outputs, statistical tests, intervals, and reporting rules are unchanged.
Run only the corrected aggregate against the existing immutable P3 and P4
artifacts; do not rerun any environment task.

Submit the corrected aggregate only as job `295597`, with promotion artifact
job `295115` and baseline array `295131` as its immutable inputs.

## A-044 -- Locked PushT P4 result

Corrected aggregate job `295597` completed successfully without rerunning any
environment task. Its checksum inventory validates. The confirmation HDF5
SHA-256 is
`141534822580c6d9d5ae14a08468e96081fb842ee7ccc6d91b921c9cb89a04f1`
and the manifest SHA-256 is
`48a30dc6e8784adc041d317b37c7a9de5b7de973e823035948f3a6ed24da576b`.

Over the 40 paired locked PushT D75 queries, B0 succeeded on 8 (`20%`, paired
query-bootstrap interval `[7.5%, 32.5%]`) and B1 succeeded on 14 (`35%`,
interval `[20%, 50%]`). B1 minus B0 is `+15` percentage points with paired
bootstrap interval `[-2.5, 32.5]`; 10 pairs favored B1, 4 favored B0, and the
two-sided exact paired sign-test p-value is `0.1795654296875`.

Because M2 failed the locked P3 promotion gate, the predeclared M2-versus-B0
primary endpoint was not evaluated. This is the protocol-defined primary
outcome and must not be replaced by an exploratory contrast. No learned arm
has a P4 result. The B1 contrast remains a secondary result; final Holm
adjustment is deferred until the executable second-environment contrasts are
available. PushT P3/P4 core execution is complete. The next core stage is the
protocol-selected TwoRoom environment.

## A-045 -- Frozen TwoRoom source, checkpoint-training repair, and core row

Before inspecting a TwoRoom planner outcome, scorer value, candidate label,
or training loss, freeze the second-environment implementation as follows.
The official TwoRoom dataset is `quentinll/lewm-tworooms` dataset revision
`6903a2de048b13819d812da0b4dd661290bc01e4`. Its
3,425,937,909-byte `tworoom.tar.zst` has primary LFS SHA-256
`494b1a02f0765cd9a0d9daf1786c419ced1009977fc45d01e3158932f8d080ca`.
The archive contains exactly one member, `tworoom.h5`. The staged expanded
file is 12,775,849,984 bytes with SHA-256
`129a36aa93ea0de488d2bcc876e396de9e3907bf66c6aae6394e542ef6a6d623`.
No HDF5 outcome, image, state, action, reward, success, episode identity, or
planner result was inspected while downloading, inventorying, and expanding
it.

Use the official base LeWM model from `quentinll/lewm-tworooms` model revision
`77adaae0bc31deab21c93740d1f8bb947cd0bdec`. Its 72,290,849-byte
`weights.pt` has primary LFS SHA-256
`566f223624ea4bfb39dbfe6ae731198dd6ea73b7b8919fed6b1ecafca810f7dd`;
its 1,313-byte `config.json` has recorded SHA-256
`2564086e961e7b5c7c04dffc451091115b389a590645ff19653c64fd0bc16e09`.
Strict conversion job `295598` loaded every state-dict key with zero missing
and zero unexpected keys. The converted 72,345,376-byte object checkpoint has
SHA-256
`83166a7ab38124d995f1206746990dce6ec627a31e469b8b5d8e0e5c980f0e86`.
Its conversion checksum inventory has SHA-256
`4c7b50aa26ee425c3f83e583fadecdf8919aa44950fbfee1267d8a6edb09e7f4`;
the converter launcher has SHA-256
`d5c3c8ecb0c6847d095585b246e0b39aada0884aecfde290eb4bbe8a0d994fd2`.

The released checkpoint registry, SHA-256
`b69a093d0796c75db4a0df98fe4b3f9af5c29fd74fc7c05bd54ade3c9aac41cc`,
contains hierarchical checkpoints only for PushT and Cube. It publishes no
hierarchical TwoRoom checkpoint. Therefore train exactly one independent
TwoRoom hierarchical checkpoint from the official frozen base checkpoint.
This is required infrastructure for the selected environment; it is neither
an additional method nor an outcome-conditioned checkpoint choice.

The Zenodo package's advertised training entry point is not executable as a
trainer: packaged file `h_le_wm/train/hierarchical.py`, SHA-256
`da0cfb47e4ee9bd43e53371ac44a96503b9fde199436a70a8ccbb4b95bcc631e`,
is an evaluator with an evaluation Hydra configuration and calls
`evaluate_from_dataset`. This file is byte-identical to the corresponding
entry in the immutable package zip, SHA-256
`b89046841d679fe70f435540d62ae87b662ec34eb457919b098d152263f63967`.
Do not silently treat it as a working trainer.

Repair only the missing orchestration layer. The repair imports the released
HiJEPA class, pretrained-loader, macro-action encoder, high-level training
forward/loss, waypoint sampler and optimized collate path unchanged. It uses
the released configuration hashes
`418a6d5d48fc7ba13e5dddf43d7af1969737236ec31c98810c018f7b2aa63358`
for `hi_lewm.yaml` and
`ebc70b41a03ca2ec3167a071e2ad008d45f9802d07caaf89edcc146571a83221`
for `hi_tworoom.yaml`. The repair program SHA-256 is
`bc5a128cea1e024d943c47be7b8b791d4afa7610700d81d7e49dc3ec77af2552`.

Outcome-blind architecture inspection jobs `295599`--`295601` failed only
while resolving historical Python module names in the old base object
checkpoint and wrote no architecture artifact. Corrected inspection job
`295602` completed. Its architecture JSON SHA-256 is
`140bbf7d608c8168f029e9a84cab6bdcdeb70802f4ddbb7975caf629e1ea91ac`
and its checksum-inventory SHA-256 is
`54cd6256f2e611e294aaf2c6487b59ffe56df9e2c7d7d0f1a29387079b8ae387`.
It establishes that the released PushT checkpoint has 30,526,414 parameters,
of which 12,491,936 are trainable. Its encoder, low predictor, action encoder,
projector, and low prediction projection are exactly equal to the official
base checkpoint. The trainable branch is exactly a 32-dimensional continuous
macro-action encoder, a four-position high-level predictor, a linear
`32 -> 192` conditioning projection, and a cloned trainable high prediction
projection. The repair hard-requires these same parameter counts and module
shapes for TwoRoom.

Freeze independent training to seed `3072`, 15 epochs, one GPU, `bf16`, batch
size 128, AdamW at learning rate `5e-5` and weight decay `1e-3`, the released
cosine schedule, gradient clipping at `1.0`, 90/10 seeded row split, five
random-sorted waypoints over maximum span 15, and 32-dimensional continuous
macro-actions. Freeze the official low-level encoder, predictor, action
encoder, projector, and low prediction projection; train only the four
high-level components above. Use the complete official offline dataset, as
the released PushT/Cube backbone-training recipe does. The later P1/P2/P3/P4
partition restriction governs auxiliary scorer fitting, calibration, audits,
and confirmation; it does not retroactively redefine backbone pretraining.
No TwoRoom training loss or checkpoint may select an architecture, epoch,
seed, or hyperparameter.

The outcome-blind architecture-preflight launcher SHA-256 is
`b2c121b79b0e0aecbcbd18a74a048d2e609afc6c936c425bf825eec73dd832f7`.
The two-batch training smoke launcher SHA-256 is
`da878c30eb2e102456c769db0e26461e8c652dcca715b7744545f1aa9f640bfa`;
its losses and checkpoint are implementation-only and excluded from every
scientific estimate. Run production only after that smoke completes. The
production launcher SHA-256 is
`50449c488a3d5d2a540bf0af662995018a192e511fb0b93458bed8c1e40d7ae9`.
It requests one A6000 for at most 36 hours under `long-a6000`; hardware changes
wall time only, not the frozen training recipe.

For subsequent auxiliary-scorer work, freeze episode assignment under root
seed `20260728` using the first 64 bits of

`SHA256("tworoom\0" + "20260728\0" + episode_id)`

and the same P1/P2/P3/P4 intervals as PushT: 70/10/10/10 percent. P0 is empty
because no local TwoRoom episode or outcome has been exposed. Freeze the core
evaluation row to the released `hi_tworoom.yaml`: goal offset `D25`, evaluation
budget 50, high-level horizon/receding-horizon/action-block `2/1/1`, replan
interval 5, high CEM `300/20/10`, and low-level
horizon/receding-horizon/action-block `5/1/5` with low CEM `300/30/10`.
Accordingly M1 and M2 train on conditional jumps at exactly 25 environment
steps. B1 changes only the high-level proposal solver to the released
empirical-macro configuration. Repeat the environment-specific P1/P2/P3/P4
pipeline and frozen promotion gate; TwoRoom contrasts remain in the secondary
family. The physical attainability rule, exact query materialization, and
TwoRoom-specific artifact hashes must be frozen after outcome-blind schema and
geometry inspection and before their first relevant P2 execution.

## A-046 -- Outcome-blind TwoRoom schema, partitions, and physical criterion

Architecture-preflight job `295604` completed before production training or a
TwoRoom planner outcome. The dataset summary contains 10,000 episodes and
79,448 valid 18-step, frame-skip-5 training clips, split deterministically
into 71,504 training and 7,944 validation clips. Native actions are
two-dimensional and the frame-skip-packed model action dimension is 10. The
architecture is exactly the A-045-frozen 30,526,414-parameter HiJEPA with
12,491,936 trainable parameters and all five low-level components frozen. The
dataset-summary SHA-256 is
`22249dc9b0a8eaca241361d66e46f0190dc56d42ca53a9299cba9447938dea44`;
the architecture-summary SHA-256 is
`526e12d1172701528e8cb96b1ad6e29af8537ea1f94f6215c2708048ae7a51cb`;
and the checksum-inventory SHA-256 is
`5c6bc1b80ab1f7141dc76e04e5ff5afb597d23d5d005f793577a43f72738adaf`.
No batch was loaded and no loss was computed in this preflight.

Outcome-blind schema job `295606` and partition job `295607` then completed.
The schema runner SHA-256 is
`f6c610b7f06c84a311d0c55f2e8ae2d2e1ec20327a56b1594c0ec7412830bf93`;
its inspection JSON SHA-256 is
`09d27d1d03af80b3a115789451f02ff1050ddeedd8d42753937f0886ffa8944a`,
and its checksum-inventory SHA-256 is
`630186c6085028eda2047cb3df34b4487dff01c6dbe5721cc6415eaaa810dbd7`.
It enumerated HDF5 names, shapes, types, storage metadata, episode IDs, step
IDs, and episode lengths only. Although the file contains outcome-bearing
columns, it did not read their values. The dataset has 920,809 rows across
10,000 episodes; episode lengths range from 31 to 101, with median 101.

The partition runner SHA-256 is
`f43c12b0cbe840516293b4bdc694664aa6cb7f0d4ce943817b7730a3142d0a88`.
A-045's frozen hash rule assigns 6,927 episodes to P1, 1,042 to P2, 1,029 to
P3, and 1,002 to P4, with no P0 exclusions. The immutable partition TSV
SHA-256 is
`47971097b1979798345c298d91eb36f91a0884353789b7f8736e6a1f9e79f790`;
its summary SHA-256 is
`f6e1fd54520588a88dfa7cf17926f5a023f10c4095145fc63cac7d54c93ffaf1`,
and the partition checksum-inventory SHA-256 is
`bff3d842b33e63e55dc0abe3f2f8e20b7613d557c2ac59e18c73d2d535f7f0fb`.

Freeze the TwoRoom physical candidate-attainment rule directly from
stable-worldmodel `0.0.6` environment source, whose `two_room/env.py` SHA-256
is `5e1d392de5b02472062dbe872aded67fd465fcc8f7eaa1c02a753b2fc31c61f0`.
That benchmark terminates on strict Euclidean pixel distance
`norm(agent_position - target_position) < 16.0`. For a real-frame candidate,
use the candidate frame's two-dimensional agent position as the target and
label an execution physically attained iff the minimum corresponding distance
over the execution trace is strictly below 16.0 pixels. Use the same rule for
both within-episode and cross-episode real-frame strata. This is a
benchmark-defined success tolerance, not a value selected from P2 outcomes.
The P2 latent-tolerance procedure remains unchanged and will measure agreement
against this now-frozen physical label.

## A-047 -- TwoRoom smoke-run manual-optimization adapter erratum

Smoke job `295605` failed at Lightning's fit-time configuration validator,
before any training or validation batch, loss, optimizer step, or checkpoint.
Its output directory contains only the already outcome-blind effective
configuration, dataset summary, and architecture summary. The exact exception
states that automatic Trainer gradient clipping is unsupported for a
manual-optimization module. Preserve this failed attempt and do not treat it as
a training run or scientific result.

The frozen gradient-clipping value remains exactly `1.0` with norm clipping.
Correct only its adapter-level placement using the contract implemented by the
released `stable_pretraining.Manager`: immediately before `Trainer.fit`, move
the Trainer's clip value and algorithm to `gradient_clip_val_` and
`gradient_clip_algorithm_`, then clear the unsuffixed clip value inspected by
Lightning's automatic-optimization validator. At train start, the released
`spt.Module` resolves those suffixed values per optimizer, and its manual
training loop applies them through `self.clip_gradients`. This changes neither
the model, data, split, optimizer, scheduler, seed, precision, batch size,
epoch count, nor any scientific decision.

The corrected repair program SHA-256 is
`8f4e46c1685938777c48760993ff5593db1db8c4a151eb94ea25a58479960718`.
The corrected two-batch smoke launcher SHA-256 is
`930f37db7b0a5e081ee10b38b20bc539a5a5a7781bbee4ad5683e598c894febc`;
the corrected production launcher SHA-256 is
`eb4701d4e4109a8c1643656a26d92e9769d4ba2260db79ae4c4842f01c67ef7c`.
Retry the complete smoke run in a new job-specific output directory. Submit
production only if that retry loads its two training batches and two
validation batches, applies clip value `1.0`, and writes its final smoke object
checkpoint and completion record.

## A-048 -- TwoRoom smoke-run Resize API compatibility erratum

Corrected smoke job `295608` passed the A-047 manual-optimization validator
and entered Lightning's validation sanity-check data loader. Its first worker
failed while collating the first image batch, before a batch reached the model,
before any model forward, loss, optimizer step, or checkpoint. The released
preprocessor instantiated `stable_pretraining.data.transforms.Resize`, whose
`__call__` invokes `self.transform`; Stable-Pretraining `0.1.8` is paired here
with the frozen container's Torchvision `0.20.1+cu121`, whose v2 Resize base
class exposes the same implementation under `self._transform`. The observed
exception was `AttributeError: 'Resize' object has no attribute 'transform'`.
Preserve job `295608` as a failed implementation smoke, excluded from all
scientific estimates.

Bridge only this dependency API name: when the Resize class has no callable
`transform` but does have callable `_transform`, alias `transform` to
`_transform` before constructing the released image preprocessor. Do not
replace or modify the released ToImage or Resize instances, size,
interpolation, maximum size, antialiasing, normalization, source/target keys,
or tensor kernel. Record the dependency versions and selected bridge mode in
`compatibility-summary.json`. The Stable-Pretraining transforms source SHA-256
is `1df32305b18b6f82340f22def1be0cad17b312e09000efaa6138cd2ed71ec4f1`;
the container's Torchvision v2 geometry source SHA-256 is
`531e6084c084570a5860a078b016a625421f45bcfc12eb637c8fdcb246cd9e19`.

The twice-corrected repair program SHA-256 is
`08449300c53eddc8d3ed498c3300a4f23db3ecef7065d6abd54ad9f9d3fe8d76`.
The new smoke launcher SHA-256 is
`2a9df7fd8f8c16010dfe14edb41d3cb9612d08d068a7e786d5e8423c6e288974`;
the new production launcher SHA-256 is
`cf507a60423e1571a3087b7aa7bf536da4de0015800e68881cb3b51914c239bc`.
Retry the complete smoke in another new job-specific output directory, under
the unchanged A-047 acceptance conditions. This is an implementation erratum,
not a protocol or hyperparameter amendment.

## A-049 -- TwoRoom hierarchical trainer smoke gate passed

Smoke job `295609` completed with exit code zero under the A-047/A-048
implementation. It executed one validation sanity-check batch, exactly two
training batches and two end-of-epoch validation batches. The released
Stable-Pretraining optimizer check resolved `model_opt` to clip value `1.0`;
its `None` algorithm value follows Lightning's documented fallback to norm
clipping. The first backward pass gave gradients to every one of the 119
tracked trainable leaf parameters. Training and validation losses were finite,
and the run reached `max_epochs=1` normally.

The smoke object checkpoint is 122,425,211 bytes with SHA-256
`80b491807b871d7a22cd88610972cf896cd53ed0bdea39e9b03179b41754c378`.
Its completion-record SHA-256 is
`fec3c85c663ebbe44b4bdbf07c2be343b2118ede30a48081a8e08d982d11a9db`;
its compatibility-summary SHA-256 is
`1b6f8f3ea786a6ddcfda30865e4a489c512a614796640a49fab19b41375d5a67`;
and the complete manifest inventory SHA-256 is
`b5e14f9d0d9c3b926b730987ae292069282908a28dda84e64eaf2a3888573702`.
The compatibility summary records bridge mode
`alias_transform_to__transform`, Stable-Pretraining `0.1.8`, and Torchvision
`0.20.1+cu121`.

This satisfies the predeclared implementation smoke gate. The smoke checkpoint
and losses remain excluded from every scientific estimate and from checkpoint
selection. Production may now run once with the unchanged A-045 training
recipe and A-048 program/launcher hashes.

## A-050 -- TwoRoom hierarchical production launch record

After A-049 passed, production job `295612` started on `gpu09.cluster` at
`2026-08-10T08:44:24Z`. It uses the A-048 repair-program SHA-256
`08449300c53eddc8d3ed498c3300a4f23db3ecef7065d6abd54ad9f9d3fe8d76`
and production-launcher SHA-256
`cf507a60423e1571a3087b7aa7bf536da4de0015800e68881cb3b51914c239bc`,
with seed `3072`, 15 epochs, batch size 128, 32-dimensional macro-actions,
and the low-level components frozen. The job-specific output directory is
`tworoom_hierarchical_default-train-job-295612`; it may become the canonical
TwoRoom hierarchical checkpoint only after the runner verifies the epoch-15
object checkpoint and completion record. No intermediate loss or checkpoint
may alter or select the frozen training recipe.

## A-051 -- TwoRoom hierarchical production completion

Production job `295612` completed with exit code zero after `00:56:19`, at
`2026-08-10T09:40:34Z`. The epoch-15 object checkpoint is 122,426,498 bytes
with SHA-256
`5cfb75b6c4f49a36ad1e4a89450d888a73a013cbda84be474d128455e52288ae`.
The runner verified the final checkpoint and `COMPLETE.json`, created the
canonical symlink
`data/stablewm/runs/tworoom_hierarchical_default`, and successfully rechecked
every file in the immutable manifest inventory.

The completion-record SHA-256 is
`a5a86005bb64136114e8fc98fe90dc96ebadbbb6a13cb42cb9614836920953ba`;
the manifest-inventory SHA-256 is
`6a2a7fbe16ff90a58ab447a7afbdcb43d7ed1f38a6896beb0156ea4695397751`;
and the final provenance-record SHA-256 is
`160b7c22b19dfe01832feb7f519c853a6c509e710b213f49728cc21a83466fbd`.
This checkpoint is now the single frozen TwoRoom hierarchical backbone for all
subsequent scorer, audit, and planner comparisons. No intermediate checkpoint
was selected.

## A-052 -- Frozen TwoRoom P1 split and scorer-pair namespaces

Before TwoRoom latent extraction or scorer training, extend A-005 and A-006
without changing their allocations or sample counts. Use dataset namespace
`tworoom` for the domain-separated P1 split:

`SHA256("tworoom\0" + "20260728\0p1_train_val\0" + episode_id)`.

Assign the first-64-bit uniform value to `P1_train` on `[0.0, 0.9)` and
`P1_val` on `[0.9, 1.0)`. Use the same namespace `tworoom` in A-006's M3
rejection-sampling domain. M1 and M2 enumerate every valid within-episode P1
pair at exactly 25 environment steps. M3 samples exactly 2,500 training and
250 validation pairs without replacement at every integer separation from 1
through 40. These choices are episode- and geometry-outcome blind and inherit
the already frozen root seed `20260728`.

The P1-split generator SHA-256 is
`cd582f32463c34b0b53e30973490ee93d533fb83f60f9dc6a620afb30730d887`;
the scorer-pair generator SHA-256 is
`73b557d244ce42e75a370e4420df876828302adc7baa70e88bb234be29c136eb`;
the independent validator SHA-256 is
`21693714292a7bf411617748877506b654e9fbde1598b62e5d5911004d0f7498`;
and the outcome-blind launcher SHA-256 is
`bfc95a12ee4eeb4a86e9e50690fd50a97a5d36a0616873d43981e0421633e8b8`.
The launcher hard-checks the immutable master-partition SHA-256
`47971097b1979798345c298d91eb36f91a0884353789b7f8736e6a1f9e79f790`
and refuses to overwrite any split or pair artifact.

## A-053 -- TwoRoom P1-manifest launcher PATH erratum

Outcome-blind job `295635` verified the frozen master manifest and all three
generator/validator program hashes, then failed with exit code 127 before
executing Python because the launcher's clean container PATH omitted both the
project environment and `/opt/conda/bin`. It generated no P1 split, scorer-pair
manifest, validation file, or scientific value. Its sole provenance file is
preserved under directory
`scorer-pairs-seed-20260728-failed-job-295635`.

Correct only the PATH by adding the already frozen Hi-LeWM environment's
`bin` directory and the container's `/opt/conda/bin`; all A-052 rules,
programs, inputs, seeds, counts, and output refusal checks remain unchanged.
The corrected launcher SHA-256 is
`52b351e08e0c7a10e2beb13ad6d35a8c4b4a9e586b6e79980ace260e0bc8879f`.
Rerun the complete manifest generation and independent validation in a new
job.

## A-054 -- Frozen TwoRoom P1 latent-extraction adapter and smoke gate

Generalize the already used PushT frozen-latent extractor only by making its
evaluation configuration directory/name explicit and by adding an optional
leading-episode limit for implementation smoke tests. For TwoRoom, compose the
official `config/eval/hi_tworoom.yaml`, SHA-256
`13d671d15f31093c623d1e6d4d4448ce2f51bb7c81504dfc225aa48e17ec8da1`,
and load the A-051 canonical epoch-15 checkpoint. Preserve the released
ImageNet preprocessing, require the vectorized implementation to match the
released evaluator to maximum absolute error at most `1e-7`, require exact
repeat encoding of the first batch, use strict seed-42 process determinism,
and store float32 encoder latents only.

Before full P1 extraction, run a two-episode P1 implementation smoke. Its
cache, manifest, and values are excluded from scientific estimates and cannot
become canonical. Full extraction must then process every P1 frame, refuse any
episode limit, verify its output checksums, and create the canonical P1 link
only on success. The generalized extractor SHA-256 is
`3c3c069b6f6400276084cfedb6c2771ad40e14067f2f0aaac2ce5f4662232d4a`;
the smoke-launcher SHA-256 is
`0a500475eabf2c6606e728e257e8e56b80d73b26b17d5445b33be56609b7cdff`;
and the full-extraction launcher SHA-256 is
`f48a794f5bba19fa83583a6b87e84ac71b284a2ff1246cee3a061cfb0e9d12d7`.
Both launchers hard-check the frozen dataset, master partition, configuration,
and epoch-15 checkpoint hashes.

## A-055 -- Empty redirection sentinel from failed manifest launch

Retry job `295636` stopped at the launcher's overwrite refusal check before
running Python. The first failed job had opened its redirected P1 stdout path
before the missing `python` executable was reported, leaving a zero-byte file
outside the archived job directory. No P1 split, summary, pair manifest, or
value existed. Move that zero-byte sentinel into
`scorer-pairs-seed-20260728-failed-job-295635` with an `.empty.json` suffix.
The corrected A-053 launcher itself is unchanged; rerun it only after verifying
the canonical P1 split paths and scorer-pair directory are absent.

## A-056 -- TwoRoom P1 split and scorer-pair freeze completed

Outcome-blind job `295637` completed with exit code zero and the independent
validator accepted every count, offset, role, separation, uniqueness, and
source-hash invariant. P1 contains 6,927 episodes and 636,508 frames:
`P1_train` has 6,251 episodes and 573,858 frames; `P1_val` has 676 episodes
and 62,650 frames. The P1 split TSV SHA-256 is
`256dce7f81d30d562039395fdc4680c218c4f4ffe513f690e9c360c601d0ffa3`;
its summary SHA-256 is
`0cfd284b0dd68e0380cdb8fbd5937918320295c24aaba6c2d97c6e626d7793c1`.

At `Delta=25`, M1/M2 contain 417,583 training and 45,750 validation pairs;
the pair-plan SHA-256 is
`c484bee9dd149c6cc15336b796c641ad04251a330bf5b51e890da3d9e50514bc`.
M3 contains exactly 100,000 training and 10,000 validation pairs, all unique
and balanced at the A-052 counts for separations 1 through 40; its compressed
manifest SHA-256 is
`f1bccba16113e81ed581ce237023c522f5229cf4f023afe32c0904b628a6b5d7`.
The independent validation-record SHA-256 is
`31acda7070e787907b1893e06dd7d82467596afa516b36fa1893a4cfd38b22f7`;
the complete checksum-inventory SHA-256 is
`1e738245fb3eff5f4ddd56f168ad8c8757e1529969b849afda448e5f2c302f4a`.
These manifests are now immutable scorer inputs.

## A-057 -- TwoRoom latent-smoke episode-key adapter erratum

Implementation-smoke job `295638` failed with exit code `1:0` after 43
seconds, before producing a completed cache or manifest. The released
TwoRoom dataset stores per-row episode identifiers under `ep_idx`, as already
recorded by the outcome-blind dataset inspection, whereas the A-054 extractor
still addressed the PushT spelling `episode_idx` when copying cache metadata.
Model construction, reference preprocessing, and the first repeated encoder
calculation occurred before this metadata write; no encoded batch was committed
to a completed cache and no value from this smoke is a scientific result.

Preserve the failed job directory and its 3,328-byte partial HDF5 file. The
partial-file SHA-256 is
`a4989cff6da2fb2557d3121d75162747739ef8a1884827f432c2c6b6b556d68d`;
the provenance-record SHA-256 is
`142aaf86eeb0f8dfa45f76632bf23c0b91515fddf584f4135a86175c77202006`;
the stdout SHA-256 is
`b6859884ab49827309a802cd74d482b4c790326e49a97bdde320d1df776f1f7d`;
and the stderr SHA-256 is
`3714494b88098f7f1fe3adaea57a117cefff06dddc6dabb2f11264807aed667a`.

Correct only the dataset-schema adapter: select `episode_idx` when present,
otherwise select `ep_idx`, fail if neither exists, and record the selected
source key in both the output HDF5 attributes and JSON manifest. Do not change
the encoder, preprocessing, checkpoint, partition, seed, episode limit,
batch size, determinism checks, acceptance thresholds, or cache layout. Freeze
the corrected program and launcher hashes before retrying the complete
two-episode smoke in a new job-specific directory.

## A-058 -- Corrected TwoRoom latent-adapter hashes and retry authorization

The A-057 correction resolves the input episode dataset once per extraction,
keeps the output cache key `episode_idx` unchanged for downstream consumers,
and records the selected input key as `source_episode_dataset`. Python syntax
checking and Bash syntax checking of both launchers passed. The corrected
extractor SHA-256 is
`65a4b66265ad31dc0c6e4539ba42498a2618ede6e1dd75cf12e206a9a1c69fee`;
the corrected two-episode smoke-launcher SHA-256 is
`25fa99d7d8093c31762e4481263aaaafb61a8c3e7866ba04de1db87b58426e64`;
and the corrected full-extraction launcher SHA-256 is
`c9c978a0e149aea1bd35249a51d8d2375c7c4ae1b1ed7b240b3109e687ab8cbe`.
Retry the complete A-054 smoke in a new job-specific directory. Full P1
extraction remains locked until that retry passes every A-054 gate.

## A-059 -- Corrected TwoRoom latent smoke passed

Corrected implementation-smoke job `295639` completed with exit code zero
after 43 seconds on an NVIDIA RTX 6000 Ada Generation GPU. It encoded all 139
frames from the first two P1 episodes into 192-dimensional float32 latents.
The selected source episode dataset was `ep_idx`; the released-evaluator
preprocessing comparison had maximum absolute error `0.0`, and an exact repeat
of the first encoder batch had maximum absolute error `0.0`. The first-batch
latent SHA-256 was
`9076f7c16659221cb0fad5cf72dc78ac0e4f39b9edef7777cd78cb7567a671ab`.

The excluded smoke HDF5 is 121,064 bytes with SHA-256
`cf400ef2a6c39e718b938307df70651e65215bab0a7b63456dcfea838198ea39`;
the manifest SHA-256 is
`ecf8ea05d19197edcecc7e9e0a6c7d7c8438b12578f3b252bd42d850429f26b4`;
the final provenance-record SHA-256 is
`b35489919a81a2673b2e504937f3152d488422f03a502c7f81c54cdfd93a873c`;
and the checksum-inventory SHA-256 is
`6648bd99af9671c60a17858e9666848be783e1aeccdfa51e10974235bed84863`.
An independent checksum replay passed, and the canonical full-P1 path remained
absent. This satisfies A-054's implementation gate. Run the full P1 extraction
once with the unchanged A-058 extractor and production-launcher hashes, with
no episode limit and no smoke artifact promoted to canonical status.

## A-060 -- TwoRoom full P1 latent-cache launch record

After A-059 passed, full extraction job `295640` started on `gpu09.cluster` at
`2026-08-11T16:58:17Z`. It uses the A-058 extractor SHA-256
`65a4b66265ad31dc0c6e4539ba42498a2618ede6e1dd75cf12e206a9a1c69fee`
and full-launcher SHA-256
`c9c978a0e149aea1bd35249a51d8d2375c7c4ae1b1ed7b240b3109e687ab8cbe`
to encode all 636,508 frames from all 6,927 frozen P1 episodes, with no
episode limit. The output directory is `p1-job-295640`; it may become the
canonical TwoRoom P1 cache only after the runner verifies the completed HDF5,
manifest, provenance, and checksum inventory. No partial cache or intermediate
value may be used for scorer training or scientific estimation.

## A-061 -- Frozen TwoRoom P1-train latent-standardization launcher

After A-060 completes successfully, compute A-008's per-coordinate mean and
population standard deviation over exactly the 573,858 frozen `P1_train`
frames in the canonical TwoRoom P1 cache. Retain the A-008 numerical floor of
`1e-6`, use no validation frame, and refuse any overwrite. The CPU launcher
must replay the full latent-cache checksum inventory, hard-check the master
partition and P1-split hashes, require a 192-dimensional result with count
573,858, and create the canonical statistics link only after verifying its
outputs.

The unchanged statistics program SHA-256 is
`014c25f51ac0c11c80503df4d23f06beb382e968e5f5c752c59fcf5c89ff7b2c`;
the TwoRoom statistics-launcher SHA-256 is
`6621d1c2f89479fb5bfcc71eda94ff0159a59f499c764649567df144eb100df7`.
This computation is a fixed preprocessing transform, not a model-selection
step. It remains locked until the full cache is canonical.

## A-062 -- Frozen TwoRoom M3 training launcher

Apply the unchanged A-007 M3 implementation to the frozen TwoRoom P1 cache
and A-056 balanced separation manifest. Train the true temporal labels and the
training-label permutation null at each of the three frozen scorer seeds
`20260728`, `20260729`, and `20260730`; validation labels remain true in every
arm. The architecture, 256 hidden units, Smooth-L1 objective, batch size,
optimizer, target scaling, maximum 200 epochs, patience 10, and deterministic
input-order rule are unchanged. The six tasks are replicates/null controls,
not candidates from which to select a seed.

The unchanged M3 program SHA-256 is
`8ab0124a858e8c4f3bb1f47c5020eda0adff2cbd93221ad87c22d1d85144e854`;
the TwoRoom six-task launcher SHA-256 is
`95800a32b6296a64b1f1b4e8bee4f73afd29e9d4d479de3ea9dac7b7127909cb`.
The launcher hard-checks the A-056 M3 manifest and summary, replays the full
canonical latent-cache inventory in every task, refuses overwrites, and
verifies all result inventories. It remains locked until A-060 succeeds.

## A-063 -- Frozen TwoRoom M2 smoke and true-width launchers

Apply the unchanged A-008 conditional epsilon-prediction program to the frozen
TwoRoom `Delta=25` pairs and A-061 standardization. First run one excluded
real-data implementation smoke at width 512 and seed `20260728`, limited to
8,192 training pairs, 2,048 validation pairs, and one epoch. Only after that
smoke produces a finite, reloadable checkpoint may the six complete true-arm
runs train widths 512 and 1024 at each of the three frozen scorer seeds. P1
validation controls early stopping within a run; it must not choose the width.
The width choice remains locked to the later development-P2 comparison, and
all confirmatory results remain untouched.

The unchanged M2 program SHA-256 is
`10e54d38d0d8f318eb53b0c21ce50933ef3b8d7b922d21a1132ea8d8723de521`;
the TwoRoom real-data-smoke launcher SHA-256 is
`a358e5ad7cddff5eddf2252d62ff361b1a388d36e32e554a884bf8797c3ee6e9`;
and the six-task true-width launcher SHA-256 is
`9c2a1115b562d5ef9908ac093b0563f3ddab5c50abd30be7c1d1a2084080f780`.
Both launchers replay the canonical latent and statistics inventories and
hard-check the A-056 pair plan and summary.

This authorization is for `condition=true` only. The existing program's
mismatched-pair hash domain contains the PushT namespace and therefore must not
be used for a TwoRoom null until a separately recorded dataset-namespace
adapter is implemented and tested. The true condition never enters that null
mapping code path.

## A-064 -- Predeclared TwoRoom M1 macro-target schema adapter

The unchanged M1 macro-target extractor already accepts an explicit dataset
name and policy and its diagnostic context resolves either `episode_idx` or
`ep_idx`. One direct HDF5 metadata read later in the same extractor still uses
only the PushT spelling `episode_idx`. Before any TwoRoom M1 target smoke,
apply the same non-scientific schema adapter used in A-057: choose
`episode_idx` when present, otherwise `ep_idx`, fail if neither exists, and
record the chosen source key in both the target HDF5 attributes and JSON
manifest. The output dataset schema, pair plan, action normalization, frozen
macro encoder, grouping, seed, subsets, and all numerical checks remain
unchanged. Freeze the corrected program and launchers before execution.

## A-065 -- Corrected TwoRoom M1 macro-target hashes and smoke gate

The A-064 adapter records `source_episode_dataset` while retaining the
standardized target-cache schema. Python syntax checking and Bash syntax
checking of both launchers passed. The corrected M1 target-extractor SHA-256 is
`4587be4f42c394b4569202da23980fa6fef0211f1139b9994ac13fb58bdc3795`;
the excluded 1,024-pair-per-role smoke-launcher SHA-256 is
`64135bd1016e013468b1b30abb5fd100773e2020422fe9a44fa4782e7e253ef8`;
and the all-pairs launcher SHA-256 is
`f789b5c33352901e838555139fca067e3dca1b397ecd3bab0647b98b0e59df4a`.

Both launchers use dataset name `tworoom`, the frozen A-051 epoch-15 policy,
the A-056 `Delta=25` pair plan, seed `20260728`, and the frozen TwoRoom dataset
and checkpoint hashes. Run the complete smoke first. Full extraction of
417,583 P1-train and 45,750 P1-validation macro targets is authorized only
after the smoke verifies finite 32-dimensional targets, episode-contiguous
action windows, source key `ep_idx`, output reloadability, and checksums. The
smoke remains excluded and cannot become canonical.

## A-066 -- TwoRoom M1 macro-target smoke passed

Implementation-smoke job `295641` completed with exit code zero after 35
seconds on an NVIDIA RTX 6000 Ada Generation GPU. It encoded exactly 1,024
P1-train and 1,024 P1-validation action windows. The dataset source key was
`ep_idx`; the raw action dimension was 2, grouping factor 5, macro input
dimension 10, five macro tokens represented each 25-step transition, and all
targets were finite with macro-action dimension 32. Every episode and
contiguity assertion passed.

The excluded target HDF5 is 341,496 bytes with SHA-256
`80cc60998fde8661b2dd12436ff5a0b53599aa7f14103f66da0058ca6ab4e5a9`;
the manifest SHA-256 is
`da024b20bea432e31058ae98e7640ce3cf0d57971f8f44c98a940a182a72af2f`;
the final provenance-record SHA-256 is
`a597e166603b5897aee886d4549e8d18e76a1f5756e5f54db749452a37ab34ab`;
and the checksum-inventory SHA-256 is
`b805e8f62c5aa36ab61e8799545a9d3b26da1821809fb5ffb5843cfd837e074a`.
An independent checksum replay passed and the canonical target path remained
absent. This satisfies A-065's gate; full all-pairs target extraction may now
run once with the unchanged A-065 hashes.

## A-067 -- TwoRoom full M1 macro-target cache completed

Full target job `295642` completed with exit code zero after 37 seconds. It
encoded every A-056 pair: 417,583 P1-train targets and 45,750 P1-validation
targets, with no subset selection. All action windows remained within their
declared episodes with contiguous step indices, all 32-dimensional targets
were finite, and the job created the canonical target link only after replaying
its inventory.

The completed target HDF5 is 70,582,663 bytes with SHA-256
`f084c25a1448682b88ede0c821a5ecea2623fbb5f321729e3b81387fb4cb5a04`;
the manifest SHA-256 is
`687337e7682a8294a641b56acfb63b4261bbc5e0ef00d512a0c98fd7ca3770a4`;
the final provenance-record SHA-256 is
`e5fe525a36d4ac4a84cbb7061ae1bea04618f9ee89bd3d56097c72e79606e843`;
and the checksum-inventory SHA-256 is
`90595f0a7d204202a99723d391cc1e0809172925cf6a165bfb11869a907a0da6`.
An independent checksum replay passed. The canonical TwoRoom M1 target path
resolves to immutable job directory `job-295642` and is now the only target
source authorized for M1 head training.

## A-068 -- Frozen TwoRoom M1 head smoke and true-width launchers

Apply the unchanged A-014 inverse-head program to the canonical A-067 targets,
the canonical full P1 latents, and A-061 standardization. First run one
excluded true-arm implementation smoke at width 256 and seed `20260728`, using
4,096 training pairs, 1,024 validation pairs, and two epochs. Only after the
smoke produces finite losses and a reloadable checkpoint may the six complete
true-arm runs train widths 256 and 512 at each frozen scorer seed. As with M2,
P1 validation controls early stopping only; later development-P2 failure AUROC
selects the width under A-018. No seed is selected.

The unchanged M1 head program SHA-256 is
`e7baf8d66bd77d53a49164592ecdc16e9b1f50b1f86baa473467ba2de9327733`;
the TwoRoom real-data-smoke launcher SHA-256 is
`c7bbd374c4223910c3b57336cef09bebb9f08262606cae7011c07c24f9b40346`;
and the six-task true-width launcher SHA-256 is
`67b18ce3c7bb9dae9ebf8ef2757aa619f9fd777855c91f8a7080319ec07365d8`.
Both launchers replay all canonical latent, statistics, and target inventories,
hard-check the A-056 pair plan, A-067 target hash, and A-051 checkpoint hash,
and refuse overwrites. The smoke remains locked until A-060 and A-061 succeed;
the true-width array remains locked until the smoke passes.

## A-069 -- TwoRoom post-cache dependency queue

Queue CPU standardization job `295643` with Slurm dependency
`afterok:295640`, and queue the six-task M3 array `295644` with the same strict
dependency on the full latent cache. Queue excluded M1 head smoke `295645` and
excluded M2 smoke `295646`, each with dependency `afterok:295643`. Thus no
consumer can start from a failed or partial cache, and both standardized-head
smokes require the canonical A-061 statistics. The M1 and M2 true-width arrays
remain unsubmitted until their respective smoke outputs are inspected and
frozen. These dependencies change scheduling only, not any data, model, seed,
or analysis rule.

## A-070 -- TwoRoom full P1 latent cache and standardization completed

Full extraction job `295640` completed with exit code zero after 45 minutes
48 seconds. It encoded all 636,508 frames from all 6,927 P1 episodes into
192-dimensional float32 latents on an NVIDIA RTX 6000 Ada Generation GPU. The
source episode key was `ep_idx`; released-evaluator preprocessing and exact
first-batch repeat checks both had maximum absolute error `0.0`, and the
first-batch latent SHA-256 matched the excluded smoke exactly:
`9076f7c16659221cb0fad5cf72dc78ac0e4f39b9edef7777cd78cb7567a671ab`.

The canonical HDF5 is 499,859,670 bytes with SHA-256
`e67129a6fb98442ed59c36cfd5274b10db02e5c0bc5acdc8db0a276f4bb8e4ee`;
the manifest SHA-256 is
`610f3a97a1bd78b73038f856c649e47bbb52aebccb3eb05dcd09d777261684ee`;
the final provenance-record SHA-256 is
`7bd40dc8de024fc6d34cc4e3c0908f63b8d60875af23435cc60e92aea28bebe0`;
and the checksum-inventory SHA-256 is
`6c19d68e50dca747ba493c8705329c29e56d030f096dacc9dc4b24b105e40cab`.
An independent replay passed and the canonical P1 link resolves to
`p1-job-295640`.

Dependent CPU job `295643` then computed A-008 statistics over exactly 573,858
P1-train frames and completed with exit code zero after seven seconds. No
dimension hit the `1e-6` floor; raw population standard deviations ranged from
`0.8505152837648239` to `1.1596633055677408`. The statistics NPZ SHA-256 is
`228b51d6fa57f22f4ebded964448d96c3f959e3a3c958d597e7bda77ee63e59f`;
its manifest SHA-256 is
`f289304e828eac7d21933b2051c7b7e3885f797c0da39875613e06f5da6acf5c`;
its final provenance-record SHA-256 is
`e909bcee2fad98fe52741ec6ee7bed05eda69b572fc771448a3547d4dd5021fb`;
and its inventory SHA-256 is
`5ae20346f02d804045afdae2b727b992cbd7b44c3f308bb5f77f4aab8f23fbcd`.
Its independent replay passed and the canonical statistics link resolves to
`p1-train-stats-job-295643`.

## A-071 -- TwoRoom M1 and M2 real-data smokes passed

M1 head smoke `295645` completed with exit code zero after 12 seconds. Both
epochs were finite, the second epoch was reloadable as best, and its final
validation standardized macro MSE was `0.829221710562706` over 1,024 frozen
validation pairs. The checkpoint SHA-256 is
`0c72eb4dc529c5bfc13af3614aba6f5173370b76d771e706f95384f91a7ed0ad`;
the result SHA-256 is
`70c6326e9a1109d391ce6bbc72c8d9080418d53e41de0ca9dbecc950497100a4`;
and the complete inventory SHA-256 is
`09a7234f9486ee705ff1746a8076a4a08178cf1ccf13badb980972a28829129a`.

M2 diffusion smoke `295646` completed with exit code zero after 13 seconds.
Its one epoch was finite and reloadable; final validation epsilon MSE was
`0.9929868777592977` over the frozen 2,048-pair smoke subset, with the five
sigma levels balanced at counts 410, 410, 410, 409, and 409. The checkpoint
SHA-256 is
`fbcdc84a703b11a3cccecd13903a3de75a014c58a30d73726a01c1097fb387af`;
the result SHA-256 is
`c5ac543dfc988fbd3a40de3e9d52e4ef572fc9ada59b452729962a2f798b9434`;
and the complete inventory SHA-256 is
`6d5a751140ab870760428554be0c497277b98466c1dba4ed1de9d257fe576160`.
Independent inventory replays passed for both excluded smokes. They satisfy
A-063 and A-068; both true-width production arrays may now run once with their
unchanged frozen hashes.

## A-072 -- TwoRoom M3 true and shuffled-label training completed

All six tasks of array `295644` completed with exit code zero and every
independent checksum replay passed. For true seeds `20260728`, `20260729`, and
`20260730`, the best validation RMSE values were respectively
`8.489071153709007`, `8.46936767235496`, and `8.49067633461202` steps. Their
result SHA-256 values are respectively
`9c9c4dbbc903abe4d7ef8a3f580df842adde98960d556a9a934919dd26f7acd4`,
`3cc299cf00475ec4161a860328a749d990daf49293c083038814079ebd801487`,
and
`9654b1cd335e1cdb7723b62c45a6a543998a1588ae7c4a4b46e05ea18fbc81ef`.
Their inventory SHA-256 values are respectively
`223fef451635f48f4831edf26943ec1425db0e38f050227d7cb101035828e6f6`,
`c434639167a74bd49cbfa1c397a38b9a6804084ae9ea2f3cd20bfb893455e462`,
and
`27f4b2f2a29d0dc5ea11a93d7965f129233e349a82b27b3e6ed0ac97fc5bcb92`.

For shuffled-label seeds `20260728`, `20260729`, and `20260730`, best
validation RMSE values were respectively `11.585929258942198`,
`11.571589044040165`, and `11.570522828682062` steps. Their result SHA-256
values are respectively
`c732f66448810a70d81c993512d8eaffe77100c95eae616e4d7e32eb9d32c85b`,
`1be76eb6b7c0897716f633f137c4cfdd1d9b154395e0a069063eca59ea730c14`,
and
`de61b764f15b1ee4f4f7fde3d74704c98caf3fad8d68bc93a82601c526a954b0`.
Their inventory SHA-256 values are respectively
`2731db9f5846130fca2d9ec5f5ad8c6822c1312243cb4f983264b6388df74ba7`,
`6a87fd3ab635c4a43fc20b276221455cd0f57e120aadf8c8ede25a64a959c794`,
and
`26081d06f9ea7c0cb8684fdcbdeeb8f21932bc42f6014a8284194fc1d40a8ad7`.
This true-versus-null separation is a training sanity check, not a claim about
planner-level failure prediction; M3 remains subject to the locked P2/P3
evaluation protocol.

## A-073 -- TwoRoom M1 and M2 true-width production launch record

After A-071 passed, launch M2 true-width array `295652` with A-063 launcher
SHA-256
`9c2a1115b562d5ef9908ac093b0563f3ddab5c50abd30be7c1d1a2084080f780`,
and M1 true-width array `295653` with A-068 launcher SHA-256
`67b18ce3c7bb9dae9ebf8ef2757aa619f9fd777855c91f8a7080319ec07365d8`.
Each array contains six true-arm tasks: both frozen widths crossed with all
three frozen scorer seeds, using every 417,583 P1-train pair and all 45,750
P1-validation pairs. These are development models; no P1 loss or completion
order may select a width or seed. Width selection remains exclusively the
later A-018 P2 failure-AUROC procedure. The null and autoencoder-control arrays
remain unsubmitted until that selection.

## A-074 -- TwoRoom M1 and M2 true-width training completed

All six M1 tasks in array `295653` and all six M2 tasks in array `295652`
completed with exit code zero. Independent replay of every task's checksum
inventory passed. All tasks consumed the same immutable A-056 pairs, A-067 M1
targets where applicable, A-070 latents/statistics, and frozen seeds. No task
was retried or selected.

M1 width-256 seeds `20260728`, `20260729`, and `20260730` reached best P1
validation standardized macro MSE values `0.05736221429168201`,
`0.057442471842948206`, and `0.05736379196083611`. Their result SHA-256
values are respectively
`23624157e0c23588e38c0947702ab748651cb25ebf3ee26269305fef6ccfd704`,
`9b0c107ddf7303c1431607c1d278a8bcab05e19ad8781ae1b125e7b11e5d2d80`,
and
`bc176a014d2c68ba14cc9e249c9c8cf47638281bd6f2ff0ffd46542917cd6831`;
their inventory SHA-256 values are respectively
`57e12dfceb8cf1a1ee87d3f585d08c85787945b0da03afc99ae7b13bbed1cef6`,
`b0aacff421e1c6cf02891b7acafb16bdc3a0d7d575929a1748b648f0b40843c4`,
and
`0de5a954a3bb4c6b3a35662a078b46fd0c5e5a037a36a03d6098d245a691fade`.

M1 width-512 seeds `20260728`, `20260729`, and `20260730` reached best P1
validation standardized macro MSE values `0.05774432868123706`,
`0.05777998906536832`, and `0.057596829179857596`. Their result SHA-256
values are respectively
`2ca1cab750d9ed3a85b65f3be29a0afb39da9a40e435c0c782d97011b577805c`,
`e54a5a9e79c0604b65399d94aa506e1c4be96aa122a6335ac5f0ce72e8895b38`,
and
`869240b64d0ebca91a9c8845a2d01f80aa3ffbf4af8bff885dba9b0d3de79b99`;
their inventory SHA-256 values are respectively
`58846c2acd11dcca08e4d09b372a8119c933e162b3124faef3aa78d88e8fcb94`,
`93312d3900e5496d2ebcd5262eb0e3982c02d5537dca74f5132653d06af901cd`,
and
`0b96e350e62339f0576419ee31c8d2d8be4d91937b8e385721b4477e8dabc518`.

M2 width-512 seeds `20260728`, `20260729`, and `20260730` reached best P1
validation epsilon MSE values `0.08606392276395648`,
`0.08514531850901674`, and `0.08536407170530226`. Their result SHA-256
values are respectively
`f383e9205a14ffd09a76b540b416e44f30be18f247f009dfa6a4b95dc32c9389`,
`57c3235cd054b5c9376f64a6126242f970810dddb7017875d92729af14897dea`,
and
`e6f7805a3267d5695fb7a50f38baf7ff902e0dfb8fe07a53ba2bf5f626b5b71a`;
their inventory SHA-256 values are respectively
`ffc469ec63f18c6caf5c6a90c1e07a417c2b5584bae9f51d59d30a92f1fc475b`,
`30cd48c07557dd312a480e46ca179430c136aa834d2e64a1f350cde29e87dde0`,
and
`c7b9aa87b7095b00dfdd1f597f9e2372dad06a4a97526e01d16482da94c253ad`.

M2 width-1024 seeds `20260728`, `20260729`, and `20260730` reached best P1
validation epsilon MSE values `0.04277854912485147`,
`0.042355518598156984`, and `0.04250756039645502`. Their result SHA-256
values are respectively
`a83e25f65ee7d5fa0c178e5b7aea8576626699b28934ad060b72fb08d0c52f98`,
`f9b5ca15a20f6d58de8e0f1c000b1dd1c68fb461745772de47f6613c3646ef7c`,
and
`d06a76941cfd9f22fb593a0b9c9dee4be09dbe3099f99c0f7ae1bf83f130b533`;
their inventory SHA-256 values are respectively
`7c0c445169fd737a77a1da5cc47daf58cfd56a72072d1800fe802c416a79d949`,
`908e804aa5dc20756ec21f7468aaa41e1fda9ddc118367bc188abd17739f9510`,
and
`c0745a6b4743a8e871307dd989cd4fdaf6b12d59d75b02afa31264a0758b9707`.

The P1 validation differences above are recorded as training diagnostics only.
They do not select M1 or M2 width and do not unlock null/control training.
A-018's development-P2 planner-failure AUROC remains the sole selection rule.

## A-075 -- Outcome-blind TwoRoom P2 materialization and episode-capacity adapter

Before any TwoRoom P2 candidate execution or auxiliary-scorer evaluation,
freeze the P2 latent-cache and candidate-materialization adapters below. No
TwoRoom P2 execution, attainment label, auxiliary-scorer value, or
hyperparameter-selection statistic was inspected in making this amendment.

The TwoRoom P2 partition contains exactly 1,042 episodes and every one is
`D25`-eligible because its frozen minimum episode length is 31. The master
P2 real-frame audit requires 12 pools by 64 candidates for each of two
strata, or 1,536 source slots, so A-015's PushT-specific one-source-episode
per slot rule is infeasible from partition capacity alone. Supersede that
clause only for TwoRoom. Order all eligible P2 episodes by the already frozen
domain-separated SHA-256 rule under root seed `20260728`, then assign
alternating episodes to two disjoint source sets of exactly 521 episodes.
Within each stratum, the first 247 episodes in frozen order contribute two
adjacent candidate slots and the remaining 274 contribute one, totaling 768
candidates. Repeated source rows within an episode must be distinct, must
remain in one 64-candidate pool, and include occurrence index in the source-
step hash. For the cross-trajectory stratum, retain the one-position cyclic
episode derangement and include occurrence index in the target-step hash.
No source episode may appear in both real-frame strata. This is the same
capacity-only remedy as A-031, with counts determined mechanically by the
smaller TwoRoom P2 partition.

Use dataset hash namespace `tworoom` and the exact domains
`p2_real_source_episode`, `p2_real_source_step`,
`p2_real_cross_target_order`, and `p2_real_cross_target_step`. The first
real-frame target remains exactly source step plus 25 in the same episode;
the second remains a hashed frame from a different episode. Read physical
agent position from `pos_agent` and require it to equal `proprio` exactly at
every selected source and target row. Apply A-046's strict `< 16.0`-pixel
attainment criterion later during execution; neither initial distance nor a
learned score may affect candidate selection or exclusion.

Generalized real-frame materializer
`create_p2_real_frame_candidate_pools.py` has SHA-256
`5a1ca3c7b4f604e279e796e40c88f96ba262f4db3816acc615204f10b433cfa8`.
Its TwoRoom P2 launcher has SHA-256
`87be9785035561e5fb85058a5ce0c7b3f0efcbdb4a134630fd7d34a4acaea48b`.
The generalization preserves the existing PushT default and adds an explicit
TwoRoom environment namespace, schema adapter, physical-state diagnostic,
and the capacity branch above.

Freeze stratum 3 to 12 episode-distinct P2 query pools of 64 candidates. Use
dataset hash namespace `tworoom` and domains `p2_stratum3_pool_episode`,
`p2_stratum3_pool_start`, `p2_stratum3_cem`, and
`p2_stratum3_candidate`. Each query is a within-episode `D25` source/goal
pair. Run the unmodified released high-level CEM row from `hi_tworoom.yaml`:
horizon/receding-horizon/action-block `2/1/1`, 300 samples, 20 iterations,
top-k 10, variance scale 1.0. Retain the complete final population and select
64 indices solely by the frozen candidate hash order; also require the final
elite mean to equal the released solver's returned action exactly. The
environment-generalized capture program has SHA-256
`ebccf6add034322a29fbafeb333e3c5997a7b6a5fa4284940362b5fa7ff8b9fb`.
Its one-pool, eight-candidate implementation-smoke launcher has SHA-256
`87fbc0423efa6320265d5eff4b96880e8687e74dac6e665beb1f327985c60721`;
its full launcher has SHA-256
`be043a3bcf52edc1caed1a6db11f3f2b8f2ce3adba1a7acc38205f2a2260998c`.

The frozen-encoder P2 latent launcher has SHA-256
`6726f5a68a61dd1c32cf0cee2fddd36ce22b2eb978cee5cc709340609ed3019e`.
It uses the same A-070 encoder/checkpoint/preprocessing contract and merely
changes the partition from P1 to P2. Candidate artifacts and their complete
source/query row hashes must be recorded in a later amendment before the
first TwoRoom P2 execution. P2 materialization diagnostics remain development
metadata and cannot be reported as confirmatory results.

## A-076 -- Immutable TwoRoom P2 candidates and pre-execution lock

The outcome-blind TwoRoom P2 latent and candidate jobs completed before any
candidate execution, attainment label, auxiliary-scorer value, or P2
hyperparameter-selection statistic was produced. This amendment freezes their
exact artifacts and the execution adapters before the first relevant P2
environment step.

P2 latent job `295664` encoded all 95,824 frames from all 1,042 P2 episodes
to 192-dimensional `float32` latents. Released-evaluator preprocessing had
maximum absolute error `0.0`; the source episode key was `ep_idx`. The latent
HDF5 SHA-256 is
`b03ea3b509339d9e1c35d39746f80ccf626bb77a2d651fcde03470bc1081999a`;
its manifest SHA-256 is
`4306d44540ae6147206fc56109ebfcf4c8755eb3f878d6056a5aacd87f2c9290`;
and its provenance SHA-256 is
`7f35669afd8dd08496e6620300b79f9ed169aba692d54628a8428fb84025f5a9`.

Real-frame materialization job `295665` completed A-075's capacity adapter.
The artifact contains exactly two strata, 12 pools per stratum, 64 candidates
per pool, 521 unique and mutually disjoint source episodes per stratum, and
at most two distinct source rows per episode. Its candidate HDF5 SHA-256 is
`af751c6c3bb1d001972981c6f8c987944303c66eee358b337dce92c9854f8816`;
its manifest SHA-256 is
`809a219643c06bad1ee3edefa26c143f1cc60c42628da18e881bf9deadb5a328`;
and its provenance SHA-256 is
`63623b0dad0a6a3c9e79aaa0d09dae8a2c8d0ac3631160b46fb8afee9d2c16ef`.
For same-trajectory and cross-trajectory strata respectively, source-row
SHA-256 values are
`3b16a556247412b31da681d4da6b38ba2be302e489bdea97fccb03beb913b773`
and
`83220c76af82bcf5437b811be439daf619133623eaa06d54f52aeaeea2c358d8`;
target-row SHA-256 values are
`34b3a8d340b66abefe995c79ac3f60da838683897c565090bbf790ec8a13e5e7`
and
`670cd844e14c114f608d8679d984cd2d8b7d9d3d5585b6f838e4ea6aba5a3d5b`.
The artifact asserted exact `pos_agent == proprio` equality at every selected
row. Initial-distance summaries in its manifest are diagnostics only and did
not filter, relabel, or alter a candidate.

Stratum-3 implementation-smoke job `295666` passed exact same-seed repeat and
released-solver elite-mean checks. Full capture job `295667` then completed
all 12 episode-distinct query pools under the A-075 configuration; every one
of its 12 final elite means equaled the released solver action exactly. The
full candidate HDF5 SHA-256 is
`022a16c75bbcaf75a8ea77a98ea226ab7566a714d9b211ad5f9381f261285531`;
its manifest SHA-256 is
`05820c34abe3ad8c189b06878e2bd39d95e9f4ff953812af2974fbf18afcfc24`;
and its provenance SHA-256 is
`45878626109eb2f454f9a6e6f19aad5caa1cf8195e93fa29f60c56cd59e797c2`.
That manifest is the immutable exact query materialization: it records each
pool's episode, source row and step, goal row and step, planner seed, selected
final-population indices, complete final population, nominal costs, selected
macro sequences, and predicted first subgoals. No query, pool, candidate, or
seed may now be replaced based on an execution or score.

Freeze TwoRoom candidate execution to A-012's same five numerical repeat
seeds and common-random-number equivalence rule. The real-frame executor
SHA-256 is
`7f1755e835323103cbf9f70813643ba35ce41009ad01c0dc7c5aed2546e1ce7c`;
the fixed-imagined-subgoal executor SHA-256 is
`c35c854322c0d07354597ecafdeba3b9e4bb03970b107c4f565db64d2bb408be`.
Both use the released TwoRoom low-level horizon/receding-horizon/action-block
`5/1/5`, CEM `300/30/10`, a 25-primitive-step attainment horizon, and cost
environment chunks of 16. Real-frame execution records the strict physical
`< 16.0`-pixel minimum-distance label and the standardized latent-distance
trace. Imagined-subgoal execution records the same latent-distance trace but
assigns no label until the P2 real-frame tolerance is selected.

The two-candidate implementation-smoke launcher SHA-256 is
`f741db3cda40d666b0d2840439e469d2d455f0774a3e61680074bfa6d1d93698`;
the eight-candidate published-budget resource-smoke launcher SHA-256 is
`9c07f4f67eef4bb907fc66f1b069ff5119aecad430c707d82da99425195cd358`.
The full 120-task real-frame array launcher SHA-256 is
`eabcb4d9105560c809568853297fcb724854b912294da35bb8dd8712eb6cd790`;
the full 60-task stratum-3 array launcher SHA-256 is
`7165605ebe4de03b6cd09b91109d97673068b9923cd3a6d43f5b9b6bce52ab13`.
Run implementation smoke, then resource smoke, before releasing either full
array. Smoke artifacts and metrics are implementation-only and excluded from
all scientific estimates.

## A-077 -- TwoRoom stepped-info goal-restoration erratum

First execution-smoke job `295668` failed after its first TwoRoom environment
step and before completing either smoke arm. It produced no execution HDF5,
manifest, checksum inventory, candidate label, aggregate, scorer value, or
selection statistic; its `real` and `imagined` output directories are empty.
The retained stdout SHA-256 is
`5750631a87176990d599b720bfa2ec1e0912f672abcb46d30e06b423aba088a3`,
stderr SHA-256 is
`666b0679adb58f5952e03a53e02343b848bcd9b3e7ff8a4bdfb40707c157be70`,
and provenance SHA-256 is
`76cc90901442eaf9d0bb1e53da83e8c96bb05de9a6895cf6696d6e7f3420ffe6`.

The stack trace establishes an environment-adapter difference: the
`stable_worldmodel==0.0.6` TwoRoom step replaces `World.infos` and therefore
drops the previously injected `goal` image before the released diagnostic
policy's `after_env_step` hook reads it. Correct only that metadata lifecycle.
Immediately after every `world.step()`, restore the exact same immutable goal
broadcast that was supplied immediately before the step, then call
`after_env_step`. This does not alter an environment action, state, reward,
termination, random number, candidate, goal, model invocation, planner
configuration, or trace horizon; it makes persistent fixed-goal metadata
available to the diagnostic hook across environments.

The corrected shared fixed-subgoal/execution helper SHA-256 is
`4b732061d29e6e6dd8eeb7def7035ad6e6a1ca572c8f9e55fa3ad5901e5880f3`.
The real-frame executor remains
`7f1755e835323103cbf9f70813643ba35ce41009ad01c0dc7c5aed2546e1ce7c`
and imports that corrected helper. Its full launcher now explicitly verifies
and records both program hashes. Supersede A-076's affected launcher hashes
with implementation smoke
`183a03722f240cd269cc44f306172177b93bd1e4dc5836095975bb8e39672e6b`,
resource smoke
`0a6e3822afd60eab87361f96911db0925870bcc544979dc94a0eca339bb7e25f`,
full real-frame array
`6ccaa0fec389bfcf886ffcd7f0735518de682fb9a38eb18bac657f44182fb6a4`,
and full stratum-3 array
`7b9f5922f091810b6aac0598e489b7f84acf87c573c05df9ccc85e19c0255889`.
All candidates, query rows, seeds, physical criteria, and planner budgets remain
exactly those frozen in A-075 and A-076.

## A-078 -- TwoRoom execution smokes passed and full arrays released

Corrected implementation-smoke job `295669` completed both the real-frame and
imagined-subgoal paths with exit code zero. Each path executed two candidates
for 25 primitive steps under the reduced `64/2/8` smoke CEM and passed the
exact common-random-number solver-equivalence check with maximum absolute
difference `0.0`. The real manifest SHA-256 is
`347192ad45f5812381ebbf7bc4b21f569d139341646c90f4c53b00d773f91777`;
the imagined manifest SHA-256 is
`5e6c602728cb1db75bfe26ed883b98991ed72fa90b03f138496cbb8ea29ce701`;
and the complete smoke checksum-inventory SHA-256 is
`29857d7dd4b528ae22868c456f8826cd51a991e8d00de6ececd8cf94c04452e7`.

Published-budget resource-smoke job `295670` then completed both paths with
exit code zero using eight candidates, low-level horizon/receding-horizon/
action-block `5/1/5`, and CEM `300/30/10`. Real and imagined execution times
were respectively `15.3460693359375` and `15.194332361221313` seconds; peak
reserved GPU memory was 408,944,640 bytes for each. The real manifest SHA-256
is `a9a15906dc8a77be77ec805c1121c2ace2a7ccd6890f468947f4684a12265399`;
the imagined manifest SHA-256 is
`9335643c4917f1779f013f316823d34304a3b5e0c716ebd7546d2835f408b8b9`;
and the complete resource-smoke checksum-inventory SHA-256 is
`70080efdae5dcc9df196f119020df5d2cd5278540e4401b6f3a17c5ff6f23936`.

All smoke metrics remain implementation-only and excluded from every
scientific estimate. These gates release the immutable 120-task P2 real-frame
array and 60-task P2 stratum-3 array frozen in A-077, with no candidate,
query, seed, label rule, model, or planner change.

## A-079 -- Frozen TwoRoom P2 aggregation and tolerance-labeling chain

Before running either TwoRoom P2 aggregate, inspecting an individual
candidate outcome, constructing a stratum-3 label, or evaluating an auxiliary
scorer on P2, freeze the complete aggregation and labeling chain below. The
full real-frame execution array is job `295671`, rooted at
`derived/candidate-executions/tworoom-v1/p2-real-frame-job-295671`; the full
imagined-subgoal execution array is job `295675`, rooted at
`derived/candidate-executions/tworoom-v1/p2-stratum3-job-295675`. Both consume
only the immutable candidate artifacts, five repeat seeds, execution budgets,
and code frozen by A-075 through A-078.

The environment-generalized real-frame aggregator
`aggregate_p2_real_frame_executions.py` has SHA-256
`7324dec34cb16b60d3fcbf081614119bd143a218a6afe4fff875eb352144af17`;
its TwoRoom launcher has SHA-256
`2ffee024c4d12cdfd048497691447a9a22fc6c3a3a0039583c7581b447c6014e`.
The environment-generalized imagined-subgoal aggregator
`aggregate_p2_fixed_subgoal_executions.py` has SHA-256
`7479228a3670d062061da96cbf6c28db5dd82cb36db3728ad867943ed10f850c`;
its TwoRoom launcher has SHA-256
`fb8a29dc766ea54b48e51c5ecadc0e5b0b3cef2bfbac91781f5af31b193a5091`.
The environment-generalized tolerance-labeling program
`label_p2_stratum3_with_selected_tolerance.py` has SHA-256
`5762e3df0b725a6235176ece7474c222974f017770d078404e59ceec4e22f3e7`;
its TwoRoom launcher has SHA-256
`c3221124e5d211f706bf590bcc2096b65f4887344f5afee69d0105d3305e9c58`.
The generalizations add only explicit TwoRoom schema, classification, physical
state, and frozen-budget branches and retain the previous PushT defaults.

For each real-frame execution, the primary physical per-repeat label is
whether minimum Euclidean agent-position error over `t = 0, ..., 25` is
strictly `< 16.0` pixels. The primary candidate label is attainment in at
least three of the five frozen repetitions. For each candidate and repetition,
the latent comparison is whether minimum P1-standardized latent RMSE over the
same inclusive trace is `<= delta`; its candidate label is likewise at least
three of five. Evaluate exactly the ten log-spaced values
`numpy.logspace(log10(0.05), log10(1.0), 10)`. Select the value with maximum
combined Cohen's kappa against the primary physical candidate labels over both
locked real-frame strata; if multiple values are equal to absolute tolerance
`1e-15`, choose the smaller delta. No per-stratum result may choose a separate
tolerance.

Apply that single selected delta unchanged to every immutable stratum-3
candidate execution. Define the stratum-3 primary attainment label as latent
attainment in at least three of five repetitions and the failure label as its
logical complement, exactly as required by A-018. Submit the real aggregate
only after successful completion of array `295671`, the imagined-subgoal
aggregate only after successful completion of array `295675`, and the labeler
only after successful completion of both aggregates. Record all resulting job
IDs and immutable output hashes in a later amendment. P2 outcomes remain
development-only and cannot be reported as confirmatory evidence.

## A-080 -- Frozen TwoRoom P2 true-scorer selection adapter

Before the TwoRoom P2 label job or any auxiliary scorer evaluation completes,
freeze the environment-generalized raw-score selection program
`score_and_select_p2_true_scorers.py` at SHA-256
`57be0645a9e7a671a40a18d23994e3ff04a7af0f8c0a445eba726d3925ba141d`.
Its TwoRoom launcher has SHA-256
`db52ae6dd2a21797fe62ff9ca3de1ffd402c7db4449005223c1cababe467ec3f`.
The adapter changes only explicit environment classification and immutable
training-job path resolution; the PushT defaults and all A-018 equations,
candidate flattening, metrics, and tie breaks remain unchanged.

Consume the completed label artifact from job `295684`, itself dependent on
real aggregate `295682` and imagined-subgoal aggregate `295683`. Resolve the
TwoRoom true training replicas only from M1 array `295653`, M2 array `295652`,
and M3 array `295644`. For M1, score every width in `{256, 512}` and all three
seeds. For M2, score every width in `{512, 1024}`, every sigma in
`{0.1, 0.25, 0.5, 0.75, 1.0}`, and all three seeds. For M3, score all three
true replicas and the already frozen shuffled-label replicas from the same
array. Also compute the fixed training-free G0a macro-space and G0b
subgoal-space three-nearest-neighbor isolation diagnostics.

Reuse A-008's single deployment common-random-number bank rather than drawing
an environment-specific replacement. Its `noise.npy` SHA-256 is
`3a94b491079e6030137480352d1ac0d985214db6ebd96f271539b2022edcf74b`
and its manifest SHA-256 is
`9723272e798a6d40b54caaa8529d83afa90dcc62f621141c3fc12eba761d5deb`.
The eight vectors are shared across every candidate, width, sigma, and seed.

Retain A-018's failure positive class and arithmetic mean of the three
seed-specific raw-score AUROCs. Select M1 width by maximum mean AUROC, with
the narrower width on a tie. Select the M2 width/sigma pair by maximum mean
AUROC, with narrower width and then smaller sigma on a tie. Do not select a
training seed. Do not use a P1 validation loss, completion order, calibrated
score, null result, G0 diagnostic, or closed-loop outcome for either choice.
The selected settings merely unlock the matched M1/M2 nulls, M2 autoencoder
control, calibration, and later P2 weight search; they make no promotion or
confirmatory claim. Record the submitted selection job ID and immutable output
hashes in a later amendment.

## A-081 -- TwoRoom M2 mismatched-null hash-namespace adapter and test

A-063 prohibited the M2 mismatched-pair null from using its embedded PushT
hash namespace. Before training a TwoRoom M2 null, generalize only the two
domain-separated hashes that order null source episodes and select within-
episode offsets. The corrected `train_m2_diffusion_head.py` has SHA-256
`f74f12c945d7542f9af0e8ea0f96247b3beb6338869ab0d0589f7b10a2f69efd`.
It accepts an explicit `dataset_hash_namespace`, defaults to the legacy
`pusht_expert_train` value for backward compatibility, records the selected
namespace in mismatched-pair metadata, and otherwise leaves the network,
true-pair branch, noise process, losses, optimizer, early stopping, seeds, and
all numerical settings unchanged. TwoRoom null training must pass the exact
namespace `tworoom`.

Freeze the outcome-blind namespace validator
`validate_m2_null_namespace.py` at SHA-256
`cfdb9095b9ddf501408b99fe3ef55b09861faf8bc99f33ad30dbe90b1aa04c6e`
and its CPU launcher at SHA-256
`b2ab4acb93a860c14454a615491147a2c9f1ea36151cf0f64ad6377b5c8f8c57`.
Against the immutable A-056 pair plan, it must independently verify for both
P1 roles that the `tworoom` mapping is byte-repeatable, bijective, has no
fixed episode, leaves every target row unchanged, changes source rows, and is
distinct from the legacy PushT mapping. It reads no latent, model, P2
candidate, execution, label, or scorer outcome. The selected-width M2 null
array remains locked until this validator finishes successfully and its
artifact inventory is recorded.

## A-082 -- TwoRoom M2 null-namespace validation passed

CPU validation job `295698` completed with exit code zero in seven seconds.
For P1 training, its `tworoom` namespace produced a bijective 6,251-episode
derangement with zero fixed points, mapping SHA-256
`94d4a22cd9d9d54fb0b47f5ddfc929d70cb3a8c43a86ffcdcd2da3aac158e6ed`,
and source-row SHA-256
`1fc1b1f694f45b60ff20314c0cf3c86c25082a510addb75bb42ffadd0d5c5b08`
over all 417,583 pairs. For P1 validation, it produced a bijective 676-episode
derangement with zero fixed points, mapping SHA-256
`f7ed982848a25b53f7d976fedb9ffbdaa1b002cbeb9fbba31f0257a49e2c0432`,
and source-row SHA-256
`912bc743ed49aa23f6fe7ef1f966711b9a60ab8aa2afdae77725b05d96fe6d6c`
over all 45,750 pairs. Both repeated byte-identically, retained the exact true
target rows, changed source rows, and differed from the legacy PushT mapping.

The result JSON SHA-256 is
`df409129d40db4139f48dda60760498d12fae010bfa8cf97ec74706e86ffa0ce`;
the final provenance SHA-256 is
`9dc7a2c87279b10642734cf31bcef68f902716ea9e81a334e88c9c7ece1a1885`;
and the checksum-inventory SHA-256 is
`001422adabf8515b653afed18d4b77a0413efaca6118b7d610b59b96a76b3f30`.
An independent inventory replay passed. This satisfies A-063 and A-081's
namespace gate; selected-width TwoRoom M2 null training may be released only
after the still-locked P2 true-scorer selection completes.

## A-083 -- Frozen selected-width TwoRoom null and autoencoder launchers

Before P2 scorer selection job `295691` completes, freeze the selected-width
matched-null launcher at SHA-256
`fdf89b744ac01645cc421520fc104a0eaf418baf10a5fd1fea4d0af64a9f5d71`.
It reads M1 and M2 widths only from job `295691` after a successful dependency,
trains all three fixed scorer seeds, and refuses any width outside the declared
sets. M1 uses the unchanged permuted-label program SHA-256
`e7baf8d66bd77d53a49164592ecdc16e9b1f50b1f86baa473467ba2de9327733`.
M2 uses A-081's corrected program SHA-256
`f74f12c945d7542f9af0e8ea0f96247b3beb6338869ab0d0589f7b10a2f69efd`
with condition `mismatched` and explicit namespace `tworoom`; every task also
requires and records successful namespace-validation job `295698`. The nulls
inherit the selected true width but receive no independent model or sigma
selection.

Freeze the selected-width TwoRoom autoencoder-control launcher at SHA-256
`39fde38eb4397b162aef3970737fd5d827a9c9fc05f2ddecb6031bdde9a244d5`.
It uses unchanged control program SHA-256
`d744791aef0e6ca0c68ee023ea87d45c1e29ab15973aa0525c2b12f49b5172f3`,
the exact M2-selected width, all three scorer seeds, and the same true P1
`Delta=25` pair plan and standardized latent cache. It replays the existing
architecture self-test result SHA-256
`0b6abc902ce6589d862a5c038171b407cd6578ed96f796d51a44e54bed561062`.
Its imported M2 support functions come from A-081's program, whose true-pair
enumeration remains byte-identical and does not enter either null hash branch.

Both launchers hard-check the A-051 checkpoint, A-056 pair plan, A-067 M1
target cache where applicable, A-070 P1 latents/statistics, selected-scorer
inventory, code hashes, and all canonical input inventories. They remain
unsubmitted until selection job `295691` completes successfully. These models
are matched diagnostics: their validation losses, completion order, or P2
scores may not revise the already selected true architecture or M2 sigma.

## A-084 -- Frozen TwoRoom P2 null/control scoring and calibration adapter

Before true-scorer selection job `295691` completes, freeze the environment-
generalized null/control scoring and calibration program
`score_nulls_autoencoder_and_fit_p2_calibrators.py` at SHA-256
`991528668f89bd653339296f9fbe88e179a5011f6d7a973d93cb7e7ac30270e9`.
Its TwoRoom launcher has SHA-256
`a72727cf6e98caae4c94834543b6b535a16e7dd3951e73ddb19935f4eb72494f`.
The adapter adds explicit TwoRoom input/output classifications and verifies
that both train and validation metadata in every M2 mismatched-null result use
hash namespace `tworoom`; no score, metric, or fitting equation changes.

After successful completion of both A-083 arrays, score the three selected-
width M1 permuted nulls, three selected-width M2 mismatched nulls at the single
P2-selected sigma, and three selected-width M2 autoencoder controls on the
same immutable 768 P2 candidates and labels as the true scorers. Retain the
already computed three M3 shuffled-label scores. Use A-008's exact eight-vector
noise bank for both true and mismatched M2 scoring. Null and control results
remain diagnostics and cannot change a selected architecture, sigma, seed, or
closed-loop weight.

Fit A-020's nondecreasing L2-regularized Platt calibrator independently to
each true M1, M2, and M3 seed, then average the three probabilities per method.
Also fit the predeclared deterministic nondecreasing PAVA isotonic sensitivity.
No null or autoencoder receives a deployment calibrator. P2 Brier score and
10-bin equal-width ECE are development diagnostics only. The launcher must
receive and record the exact label, true-score, null-array, and autoencoder-
array job IDs, replay all their inventories, and create the canonical
calibration link only after a complete checksum-verified result.

## A-085 -- Frozen TwoRoom P2 augmented closed-loop weight-development chain

Before inspecting any TwoRoom P2 scorer, calibration, or augmented-planner
outcome, freeze the environment-generalized augmented-cost wrapper
`feasibility_augmented_high_cost.py` at SHA-256
`5645a2cdd6dca588a5fed6be87942195c1d69d597b38e48867a79f648b476d7c`,
the environment-generalized query executor
`run_p2_augmented_closed_loop_query.py` at SHA-256
`cff14fef29775e1679975ee8103d0859d1259bb03880aa7c66b385e7447560cd`,
and the environment-generalized weight-grid aggregator
`aggregate_p2_augmented_closed_loop_grid.py` at SHA-256
`e934eee73ad7ac23f36f1c7a70cdd88482648c0976d000a85e3603cdb367f72c`.
The executor imports the corrected fixed-world loop helper frozen by A-077,
SHA-256
`4b732061d29e6e6dd8eeb7def7035ad6e6a1ca572c8f9e55fa3ad5901e5880f3`.
These adapters retain all PushT defaults and add only explicit TwoRoom
classification, artifact-path, released-planner-budget, state-reporting, and
goal-metadata branches.

Freeze the full-budget one-query release launcher at SHA-256
`afb969d71cc3792f14f43331628609ea9003fda9ec0eb05b60075d2bc65d9906`,
the 180-task weight-grid launcher at SHA-256
`7ce21714bbefef35abf31dff728e010a8a87e160f4370332ac7ffaadf9454d23`,
and its CPU aggregation launcher at SHA-256
`91a8cd9f8209bc569c981f6ab63895e225e8afc239737e398f02b1e92289c0b4`.
Each GPU launcher hard-checks the frozen program and helper hashes, dataset
SHA-256
`129a36aa93ea0de488d2bcc876e396de9e3907bf66c6aae6394e542ef6a6d623`,
checkpoint SHA-256
`5cfb75b6c4f49a36ad1e4a89450d888a73a013cbda84be474d128455e52288ae`,
released `config/eval/hi_tworoom.yaml` SHA-256
`13d671d15f31093c623d1e6d4d4448ce2f51bb7c81504dfc225aa48e17ec8da1`,
candidate HDF5 SHA-256
`022a16c75bbcaf75a8ea77a98ea226ab7566a714d9b211ad5f9381f261285531`,
and complete candidate, true-selection, calibration, and A-008 noise
inventories before executing.

Use exactly the 12 immutable, episode-distinct P2 stratum-3 D25 queries in
the candidate artifact. Run each query for exactly 50 primitive environment
steps. The released high planner has horizon 2, receding horizon 1, action
block 1, replan interval 5, 300 candidates, 20 CEM iterations, top-10 elites,
and warm starts. The released low planner has horizon 5, receding horizon 1,
action block 5, 300 candidates, 30 iterations, top-10 elites, and warm starts.
Thus every task must record 10 high solves, 200 augmented high-cost calls, and
60,000 scored candidates. The nominal-cost equivalence check must pass at
exact maximum absolute difference zero before acting. The loop must restore
the immutable TwoRoom goal metadata both before and after every environment
step, because stable-worldmodel 0.0.6 replaces its info dictionary. Released
benchmark success is the logical OR of `world.terminateds` over all 50 steps;
no post-hoc geometric success threshold is substituted.

For each of M1, M2, and M3, evaluate exactly the weights
`{0.25, 0.5, 1.0, 2.0, 4.0}` on all 12 shared queries, for 180 tasks total.
The cost is the released squared-L2 final-goal cost plus the weight times the
arithmetic mean of the three independently Platt-calibrated seed-specific
failure probabilities. For M1 the score consumes the current latent, first
predicted subgoal, and first proposed macro action; M2 and M3 consume the
current latent and first predicted subgoal, with M2 using A-008's eight fixed
noise draws. Select each method's weight by largest released benchmark success
count over the 12 queries, breaking an exact tie toward the smaller weight.
No weight is shared across methods.

Do not submit the one-query M2/weight-1/pool-0 release smoke until the A-084
calibration artifact completes successfully. Treat its outcome as an
implementation-only gate. Do not submit the 180-task grid until that smoke
passes its exact artifact, nominal-equivalence, budget, trace, and checksum
checks. Aggregate only after every grid task completes successfully. Every
count and selected weight is P2 development-only; it may freeze P3 settings
but may not be reported as confirmatory evidence or used to revise a scorer
architecture, sigma, seed, calibration method, candidate set, or planner
budget.

## A-086 -- Frozen mechanical continuation of the TwoRoom P2 gates

To prevent a manual job-ID transcription error or a later stage being
released before its predecessor passes, freeze the outcome-gated dispatcher
`dispatch_tworoom_p2_pipeline_a085.py` at SHA-256
`e3fddb0181806dec61f470ecf80928b75a1789b113a035f5b0341fb3a5a7f425`
and its CPU launcher at SHA-256
`f81c0f81a8f9fe0e400ff9e57e9a1c8053584c0bb4b9625f2fbba786dd27dcbc`.
This is scheduling infrastructure only and changes no scientific setting,
score, label, model, query, weight, seed, planner, metric, or tie break.

Queue only the `after-selection` dispatcher now, with scheduler dependency
`afterok:295691`. It must replay the complete job-295691 inventory and verify
the TwoRoom classification, P2-only marking, 768-candidate coverage, allowed
M1/M2 widths and M2 sigma, and HDF5 hash before it submits either A-083
training array. It then submits the null/control calibration job with an
`afterok` dependency on both dynamically returned array IDs, passing the
frozen label job `295684`, selection job `295691`, and exact two training job
IDs. Finally, it queues—not executes—the next CPU dispatcher after successful
calibration.

The `after-calibration` stage replays both selection and calibration
inventories, requires the calibrated M1 width, M2 width, and M2 sigma to equal
the true-scorer selections exactly, and verifies the stored true-score HDF5
hash before submitting the A-085 one-query smoke. The `after-smoke` stage runs
only after that smoke exits successfully and independently requires the exact
TwoRoom classification, M2/weight-1/pool-0 identity, released D25 and 50-step
planner rows, zero-difference nominal-cost check, 200 cost calls, 10 high
solves, 60,000 candidate evaluations, 50 recorded steps, frozen candidate
hash, and matching scorer/calibration hashes. Only then may it submit the
180-task grid and its dependent aggregate.

The final `after-aggregate` stage runs only after the aggregate exits
successfully. It replays every upstream gate and requires exactly 180 tasks,
12 shared queries per weight, three method records, an allowed selected weight
and success count in `[0, 12]` for each method, all frozen artifact hashes, and
the canonical selection link. It submits nothing and writes a checksum-
verified completion receipt. Every dispatcher receipt must record the exact
`sbatch` commands and returned job IDs. A failed semantic or checksum gate
exits nonzero, so its dependent stage is never released. The dispatcher may
read P2 values only at the stage where the protocol already permits them; it
cannot change any frozen setting in response.

## A-087 -- TwoRoom P2 continuation dispatcher submitted

After local and remote SHA-256 equality, remote Bash syntax validation,
Prometheus Python 3.6 compilation and help-import validation, and a successful
SLURM `--test-only` check, submit the A-086 `after-selection` CPU dispatcher
as job `295742`. Its scheduler dependency is exactly `afterok:295691`, its
exported stage is `after-selection`, its exported true-score job is `295691`,
and `scontrol` records the frozen launcher path
`scripts/run_dispatch_tworoom_p2_pipeline_a085.slurm`. At submission it is
pending for the unfulfilled dependency and has requested one CPU, 1 GiB RAM,
ten minutes, account `superworld`, partition `defq`, and QOS `normal`.

Job `295742` is orchestration only. No A-083 training array, calibration,
augmented smoke, weight grid, or weight aggregate was submitted by this act.
Those job IDs may be created only by the checksum- and semantics-gated stages
specified in A-086 after their respective `afterok` dependencies become
satisfied.

## A-088 -- TwoRoom inclusive-t0 state-cache failure and invalidation

Execution arrays `295671` and `295675` both completed every task with exit
code zero, but their frozen independent aggregators correctly rejected the
artifacts before any tolerance or scorer outcome could be produced. Real-frame
aggregate job `295682` failed with exit code `1:0` at the first task because
`state_trace[0]` did not equal the frozen source state. Imagined-subgoal
aggregate job `295683` failed identically. Consequently label job `295684`
became `DependencyNeverSatisfied`; scorer-selection job `295691` and dispatcher
job `295742` remained behind unsatisfied dependencies. No P2 tolerance,
candidate label, scorer selection, calibration, or augmented-planner outcome
exists from this chain.

Diagnosis was restricted to reset semantics and raw trace consistency. In
stable-worldmodel 0.0.6, the TwoRoom dataset stores agent position as
`proprio`, while the live environment publishes the same value under both
`proprio` and `state`. The released evaluation reset correctly invokes
TwoRoom `_set_state(proprio)` and `_set_goal_state(goal_proprio)`, so the
physical environment begins at the requested dataset position. However, its
cached vector `world.infos["state"]` retained the preceding random-reset value
at t=0 because the offline batch contained no `state` alias. From t=1 onward,
the environment returned the correctly initialized trajectory. For the first
real-frame task, all 64 stale t=0 rows were identical even though its 64
dataset source rows were distinct, while t=1 displacement from the requested
sources ranged from approximately 0.55 to 7.08 pixels and was compatible with
the frozen action dynamics. The imagined task showed the same pattern.

This is not harmless metadata: the primary physical criterion explicitly
takes the minimum over inclusive steps 0 through 25. A stale random t=0 value
can create a false attainment. Therefore arrays `295671` and `295675` and all
their per-task physical labels are invalid and permanently excluded from
scientific analysis. Do not weaken either aggregate check, rewrite any old
artifact, or salvage a label by post-hoc editing. Preserve the failed outputs
and logs as an audit trail and rerun every execution into new job-ID paths.

## A-089 -- Frozen TwoRoom t0 synchronization correction and rerun gates

Before a corrected execution is submitted, freeze
`execute_fixed_subgoal_candidates.py` at SHA-256
`f1ddb5d09104f0cd94f0beda28b7ab342efd1bccc51e2839b7107812434e0023`
and `execute_p2_real_frame_candidates.py` at SHA-256
`41d47f266b3a4f86b5a632b7a0a49179a68be2fcd1526f0c65306bb44bea1a95`.
For TwoRoom only, both batch builders now copy the dataset `proprio` vector to
the `state` alias and `goal_proprio` to `goal_state` before constructing
history-broadcast infos. The shared world loop then compares the cached live
t=0 state against the dataset-backed initial state with exact array equality
and aborts before acting on any mismatch. Every successful manifest records
an `initial_state_sync` gate with status `ok`, exact `true`, and maximum
absolute difference `0.0`. No model, candidate, action, CEM, seed, horizon,
threshold, latent statistic, or label equation changes.

Freeze the corrected two-candidate implementation-smoke launcher at SHA-256
`c546ccaa806e90f20fb07f3085dd5c705b65dd6a8b344c6445ac06f18cb935fb`.
It must run both the real-frame and imagined-subgoal paths and may release no
full array unless both new exact t0 gates and complete output inventories pass.
Freeze the corrected 120-task real-frame launcher at SHA-256
`1e7624454bdd85391c7b89f8f4db00ce9a6e2c13878e1f8b77e3608398c2c81d`
and the corrected 60-task imagined-subgoal launcher at SHA-256
`0dd70b54a571a5761fc1d815709acc0da246a39508ef71fb691013f3dfd61277`.
Both retain the candidate sets, five repeat seeds, planner budgets, and task
mapping frozen in A-077 and must write only to new array-job namespaces.

The real and imagined aggregate launchers now accept their completed corrected
array IDs explicitly and have SHA-256 values
`56135aab2f77180cee606a58b7072e20389cae5f9f4b1235dc5e0845f0bdd64b`
and
`cefb1051026fe0cc29dc34abc494a188d9f90a6a79fb62596e50142761c63228`,
respectively. Their Python aggregation programs and exact source-state checks
remain unchanged. The A-085 augmented smoke and grid import the corrected
shared loop and are refrozen at launcher SHA-256 values
`03b38bb3728605f9941c31326e08098cb78121b441209e4ef282dfa8a34dc62d`
and
`27d058b82d51ffc036706d2c81e62ceab3d5885794dbc7d58c07dbdccd57d51d`.
The A-086 dispatcher is correspondingly refrozen at program SHA-256
`deb23fa6b168c7855277be323b2bc9acd013ac628f0f9a40709b1dde4a4d7057`
and launcher SHA-256
`169fae7a530ff6c4f20291b182668cda9958fba4f2dd1277a62ff1651f4dc540`.
These supersede only the named launcher/program hashes in A-085 through A-087;
all scientific rules remain unchanged.

## A-090 -- Corrected TwoRoom t0 synchronization smoke passed

Corrected two-path implementation-smoke job `295860` completed with exit code
zero in 54 seconds on an NVIDIA RTX 6000 Ada Generation. Both the real-frame
and imagined-subgoal manifests record `initial_state_sync.status = "ok"`,
`exact = true`, `physical_key = "state"`, and `max_abs = 0.0`. An independent
HDF5 replay compared every t=0 row against its frozen dataset-backed source
and reproduced exact equality with maximum absolute error `0.0` in both
paths. All output inventory checks passed.

The real smoke HDF5 SHA-256 is
`66a84120daa5cdcecbae97201f9ae4e562bff9ec3c47a1241b6f53b6e4bf34f4`
and its manifest SHA-256 is
`15492cebbd5bbafcb9873bd3de56418fa035feaabb8840dbbdb8574460c572b9`.
The imagined smoke HDF5 SHA-256 is
`b5c5811b8e5de3a491aac7faba167fc37eb7b7ec243f3d93d0b2f3809d54fa38`
and its manifest SHA-256 is
`db82aea70e013eda1b162f50f3a2db1588905f308f0859670f61a0b8282f6408`.
The final provenance SHA-256 is
`da56d1d79f6eacb3fb07ef232deed376805263900f5cf0fb37823e63936fed38`
and the checksum-inventory SHA-256 is
`e9e6ea3c5340276a74e9a22a1fa9f73a26041fb7940cf53cc60cd1245c3de712`.

This implementation-only result satisfies A-089's rerun gate. It authorizes
fresh full execution arrays with no change to the frozen scientific design;
the smoke's metric values remain excluded from every estimate and selection.

## A-091 -- Corrected TwoRoom P2 execution and analysis chain submitted

Following A-090, submit corrected real-frame array `295861` and corrected
imagined-subgoal array `295865`. Each writes only beneath its new array-job
namespace; neither can overwrite or be confused with invalid arrays `295671`
and `295675`. At submission, tasks 0 through 2 of real array `295861` began on
the three GPUs allowed by the account, while all other tasks waited under the
account GRES limit without failure.

Submit real aggregate `295866` with exact dependency `afterok:295861` and
export `EXECUTION_ARRAY_JOB_ID=295861`. Submit imagined aggregate `295867`
with exact dependency `afterok:295865` and export
`EXECUTION_ARRAY_JOB_ID=295865`. Submit tolerance/label job `295868` only after
both aggregates succeed, then submit true-scorer selection job `295869` only
after label job `295868` succeeds and with export
`LABELED_JOB_ID=295868`. `scontrol` confirms all four launcher paths,
dependencies, partitions, memory requests, and exports.

Refreeze the mechanical continuation dispatcher for the corrected label and
true-selection IDs. Its program SHA-256 is now
`260789c6a22d8259450b00f89937d2cde8adef3cdbd5d3bae0dba0da04300d21`
and its launcher SHA-256 is
`939fd28c408a72cb7a3ce6e0c3658c4f257b00aba456c04bd016993aa68f9fc7`.
The only dispatcher changes from A-089 are the immutable predecessor IDs
`295868` and `295869`; its semantic validators, frozen downstream launcher
hashes, and scientific rules are unchanged. Queue a replacement
`after-selection` dispatcher only with dependency `afterok:295869` after
remote hash, Python 3.6, Bash, and SLURM submission validation pass.

## A-092 -- Corrected continuation gate active; stale chain retired

Remote byte equality, Python 3.6 compilation, Bash syntax, and SLURM
`--test-only` submission checks passed for the A-091 dispatcher. Submit its
replacement `after-selection` gate as job `295871` with exact dependency
`afterok:295869` and export `TRUE_SCORE_JOB_ID=295869`. `scontrol` records the
frozen launcher, one CPU, 1 GiB RAM, ten-minute limit, account `superworld`,
partition `defq`, and QOS `normal`; the job is pending only for its intended
dependency.

Cancel the three unexecutable pending jobs from the invalid chain—label
`295684`, scorer selection `295691`, and dispatcher `295742`—after the complete
corrected replacement chain is present. SLURM records all three as cancelled
by user 1201 with zero elapsed execution time. This cancellation removes only
stale scheduler entries; it deletes or changes no dataset, invalid execution
artifact, failure log, protocol file, model, or valid result.

As an early full-array consistency check, the first three tasks of corrected
real array `295861` completed with exit code zero. An independent replay of
task `stratum-0/pool-00/repeat-0` confirms exact equality between all 64 t=0
state rows and the frozen source rows with maximum absolute error `0.0`; its
manifest repeats the exact A-089 synchronization gate. This does not replace
the full aggregate validation and exposes no value used for selection.

## A-093 -- Corrected TwoRoom P2 development pipeline completed

The corrected TwoRoom execution and analysis chain completed without a
nonzero exit. Real-frame array `295861` produced all 120 expected task
artifacts, imagined-subgoal array `295865` completed all 60 tasks, and
aggregate jobs `295866` and `295867`, tolerance/label job `295868`, true-scorer
selection job `295869`, and continuation dispatcher `295871` all completed
with exit code zero. The selected scorer configuration is M1 width `512` and
M2 width `512` at sigma `1.0`. The true-score HDF5 SHA-256 is
`ef85085ddbddbcdd2f883d4be93387883d7648595b188e4b27f221c3b155d019`
and its manifest SHA-256 is
`3f558218dd5c9d7c6d5e01c030d93b84683bbef12c645e6c7018b35366f9cdd0`.

The matched-null array `296057`, selected M2 autoencoder array `296058`,
null/control scoring and calibration job `296059`, and post-calibration
dispatcher `296060` completed with exit code zero. Calibration artifact
checksums verify; its HDF5 SHA-256 is
`0a0f99fbc176514490b0d7d2cd5efeb64655a2b789ea47b8d20691b5b9637ade`
and its manifest SHA-256 is
`51a45e8d2495fac61ad00e44b85505a83f7073637338a424811e634774002018`.
Full-budget augmented smoke `296068` completed successfully and recorded
episode success, after which dispatcher `296069` released the frozen grid.

All 180 tasks of augmented closed-loop weight grid `296070` completed with
exit code zero. Aggregate/selection job `296071` selected weights M1 `0.25`,
M2 `0.25`, and M3 `4.0`. The selection HDF5 SHA-256 is
`0d11297264579992782a8e6c27308044e4dd8dc8caf4ce66de2e3611571c36b8`
and its manifest SHA-256 is
`9012dcd29f279d623708047aff4004015fbfe2cb74277e7cdcc52ab17d36c54a`.
Final validator `296072` recorded `status = "ok"` and
`pipeline_complete = true`, with no further submissions.

An independent post-run audit found no non-completed state or nonzero exit in
the corrected pipeline and verified every checksum listed by the final
calibration, augmented-selection, and completion-validator inventories. This
closes the TwoRoom P2 development-only stage. Its values remain development
results and must not be reported as P3 confirmatory estimates.

## A-094 -- Independent PushT execution-lineage and reset-semantics audit

After the TwoRoom cached-t0 defect was found, perform a separate read-only
audit of every completed PushT P2 and P3 candidate execution rather than
assuming that the shared implementation implied the same defect. Corrected
audit job `296260` inspected all 540 execution HDF5 files, representing 34,560
candidate/repeat records across P2 fixed, P2 real-frame, P3 fixed, and P3
real-frame roots. Every artifact hash, partition and episode mapping,
same-trajectory D25 or cross-trajectory target relationship, dataset-backed
source and target state, stored t0 row, latent trace, physical trace, inclusive
minimum, primary label, and released-environment label passed independent
recomputation. P2 and P3 source episodes have intersection count zero. Maximum
numeric trace disagreement was below `2e-7`; one float32 argmin near-tie had a
score gap of only `8.92919810313586e-09` and did not change its stored minimum
value or any label. The audit JSON SHA-256 is
`cef3da249ea8813825bebcd7848b8a580785361dcf92ea2b84b81aa50b8d584a`.

The stored-row audit could not by itself establish the simulator's internal
state immediately after released PushT `_set_state`, which advances physics by
`dt=0.01`. Direct environment probe job `296258` therefore replayed 23,210
unique environment-seed/source-row pairs. The agent-position displacement was
exactly the recorded velocity times `0.01` up to approximately `4.02e-14`,
with median `0.7611` pixels and maximum `5.8342` pixels; block position, block
angle, and velocities otherwise agreed. Recomputing inclusive-t0 physical
classification for all 23,040 real-frame candidate executions produced zero
primary block-only flips and zero released joint-label flips. The probe JSON
SHA-256 is
`e72db154f7a22577b699fd96502cb9c602304d7a87d9304ed8b442b63d76b05d`.
The probe did not rerun planning and cannot rule on later trajectory changes,
but it rejects the hypothesis that the observed PushT result arose from the
TwoRoom-style cached-state or label-reconstruction error.

## A-095 -- Exploratory PushT M2 source-conditioning diagnostic

Freeze the P1/P2-only conditioning diagnostic at specification SHA-256
`3a6ab0966f67f8ee251f997a1c00ea573555bdc4a2055f79320ac792984b865a`
before running job `296259`. It used the already selected M2 width `1024`,
sigma `0.25`, three training seeds, and eight fixed score-noise draws; it read
no P3/P4 artifact and exactly reproduced job `294839` scores with maximum
absolute error zero.

On 10,000 held-out genuine P1 D25 transitions, replacing each correct source
with a different-episode source increased ensemble error by mean
`20.1275108`, with paired bootstrap interval `[19.7974187, 20.4579027]`, and
the difference was positive for `99.6%` of pairs. Thus M2 does use its source
on genuine transitions. On the 768 P2 imagined candidates, however,
correct-source AUROC `0.9188561` did not reliably beat wrong-pool AUROC
`0.8592488` (difference interval `[-0.0035095, 0.2394337]`) and was below
mean-source AUROC `0.9552025` (difference interval
`[-0.1690339, 0.0009701]`). The correct-minus-wrong conditional penalty had
AUROC `0.4143273`. Under the pre-frozen rules, source use is supported but
improved imagined-candidate failure ranking and the conditional-penalty
variant are not. The HDF5 SHA-256 is
`690d3ad663d0b00be2961073462253eb8f313e8ea78093360bd0e683a12044bf`
and manifest SHA-256 is
`f1b5332ff93f46be50ac7756f6d413f5667a9b4f6e1dfc6b33eb5c00831426a0`.

## A-096 -- Exploratory PushT M2 real-frame reachability diagnostic

Freeze specification SHA-256
`8c774161d8ea6b93cad47a6a9526f9dacf316fb891052fa0393d821ca03e06b8`
before job `296265`. This P2-only audit scored all 1,536 already executed
source/target pairs for which both endpoints are genuine offline frames. Its
primary metric macro-averages AUROC over the same-trajectory D25 and
cross-trajectory strata so that their very different failure prevalences
cannot create the result by themselves.

Correct-source M2 achieved macro-stratum AUROC `0.6740016`, with whole-pool
bootstrap interval `[0.6379667, 0.7039518]`. The corresponding values were
`0.5649507` for the mismatched-training null, `0.5812300` for the capacity-
matched autoencoder, `0.5928541` with wrong sources, and `0.6002317` with the
mean source. Correct-source minus each comparator had a strictly positive
95% interval: null `[0.0924797, 0.1250051]`, autoencoder
`[0.0650758, 0.1188040]`, wrong source `[0.0512010, 0.1067035]`, and mean
source `[0.0482541, 0.0982513]`. The result is stronger on cross-trajectory
pairs (AUROC `0.7728685`) than on same-trajectory D25 failures
(`0.5751346`). It is therefore positive evidence that the auxiliary diffusion
model learns conditional real-frame reachability, but not evidence by itself
that it improves within-query CEM choice or closed-loop success. The output
HDF5 SHA-256 is
`5b475b0e1eee7a7e90151541b81f92cc982c4550b90c92cedda12dd4e33ffb12`
and manifest SHA-256 is
`d68f4710f63777db8116b7281ce485853a3f75a80366625c48b4dea3eef8babb`.

## A-097 -- PushT pooled-AUROC gate is not a within-query ranking test

Freeze specification SHA-256
`ca9c4d5275fa9007947f78e2b74332478f2a7d41f22e0644a3a7c2ac86bab814`
before read-only audit job `296263`. The operational planner compares
candidates from one current-state query, whereas the original P2 selection
and P3 gate pooled candidates from different queries. The audit therefore
reports within-pool AUROC and lowest-score top-k selection in addition to the
original pooled metric.

Only 3 of 12 P2 pools were mixed-label; six were all-failure and three were
all-attained. Only 1 of 24 P3 pools was mixed-label; fourteen were all-failure
and nine were all-attained. For selected M2, the P2 ensemble had pooled AUROC
`0.9188561` but pair-weighted within-pool AUROC `0.5802771`, interval
`[0.4333333, 0.6266234]`. Lowest-score top-4 selection reduced mean failure
by only `0.0143229`. On P3, ensemble pooled AUROC was `0.8067331`, while the
only mixed pool had within-pool AUROC `0.47`; lowest-score top-4 selection
increased mean failure by `0.0091146`, with interval
`[-0.0273438, -0.0091146]`. More than `99.99%` of M2 score variance in both
partitions was between pools. M1, M3, their nulls, and the autoencoder show the
same severe scarcity of identifiable within-query comparisons, although
their ordering on the single P3 mixed pool differs.

The execution data remain valid, and A-043's locked negative promotion
decision remains the protocol result. This audit instead shows that a high
global candidate AUROC mostly measured whole-query difficulty and was poorly
aligned with the scorer's CEM consumer. Future scorer selection and gates need
query-level ranking metrics, deliberately diagnostic candidate sets, and
ultimately paired closed-loop intervention; the original pooled AUROC must not
be described as evidence of useful candidate ordering. The output HDF5
SHA-256 is
`76a30b64d23ac3ca9525816a5f6f30e7ad2f9d62079eb9816553ff6bd46d7f76`
and manifest SHA-256 is
`35f65b89c1dce6b4ad447973d949c95ccf7452efcd89a8c006ae296e90020600`.

## A-098 -- TwoRoom P2 within-pool replication

Freeze the direct TwoRoom replication at specification SHA-256
`fe78a5c599df1f49268f154b51ed28d1f9def0935011ad74a88857f7446136b4`
before job `296267` reads the completed P2 calibration artifact. No TwoRoom P3
or P4 artifact is read. Eight of twelve pools are all-attained and four are
mixed; none is all-failure. Thus only one third of queries identify a
within-pool ranking.

Selected M2 has pooled ensemble AUROC `0.6328655`, but pair-weighted
within-pool AUROC `0.4923686`, with whole-pool bootstrap interval
`[0.3573701, 0.8888889]`. Its lowest-score top-4 failure-rate reduction is
only `0.0091146`, interval `[-0.0325521, 0.0572917]`. The mismatched M2 null
has within-pool AUROC `0.5076314` and the autoencoder control `0.4652346`; none
passes the pre-frozen within-pool or useful-top-4 rule. In contrast, the M3
true head has within-pool AUROC `0.6342566`, interval
`[0.5119048, 0.6564204]`, and top-4 reduction `0.05078125`, interval
`[0.0026042, 0.12109375]`, although this remains P2 development evidence.

The selected M2 result therefore replicates the lack of robust within-query
candidate ordering rather than the high pooled PushT value. The output HDF5
SHA-256 is
`223082ee6b08d1bcdb017f1de6c29a5f7757d8d1cda902695ad81ada2744e8b7`
and manifest SHA-256 is
`cbcf30546618fc9d3d8ee16b6e041401a8779be5bbd729ef69b787881e89a87f`.

## A-099 -- TwoRoom M2 closed-loop grid was non-interventional

Freeze the cross-environment P2 calibration/intervention audit at
specification SHA-256
`be56403cf6cac2b79cea7dee6302bb38913df07f6898598e7d289254f8f5afce`
before running job `296272`. The audit validates every M2 task hash in the
PushT and TwoRoom P2 grids and checks the exact online formula in
`feasibility_augmented_high_cost.py`, SHA-256
`5645a2cdd6dca588a5fed6be87942195c1d69d597b38e48867a79f648b476d7c`.

PushT's three M2 Platt raw-score slopes are positive
`[0.0733101, 0.0688856, 0.0629954]`. Across 1,800 recorded final CEM
populations, failure-probability span is always nonzero, with median
`0.0008231` and maximum `0.0728959`; success identities and trajectory arrays
vary across weights. Its M2 weight grid was therefore an actual, if often
weak, planner intervention.

TwoRoom's three slopes are exactly `[0, 0, 0]`. Consequently every raw M2
score is mapped to the seed-intercept prevalence probability, and the seed
mean is candidate-constant. All 600 recorded final CEM populations have
probability span exactly zero. For every one of the twelve queries,
high-level subgoals, step-current latents, step-subgoal latents, final states,
and success outcomes are bit-identical across all five weights. Each weight
succeeds on exactly pools `{0, 2, 4, 6, 8, 11}`. Therefore the completed
TwoRoom M2 grid could not change CEM elite ordering and is not evidence for or
against diffusion-assisted planning. It tested the zero-slope calibrator, not
M2's raw score. The audit manifest SHA-256 is
`c90ae3bf1e830f176c2300885c848ee6b2fc8ebb07d772c409036881cb73cff4`.

## A-100 -- Existing M2 grid does not yield a robust within-pool rescue

Freeze the post-hoc P2 grid reanalysis at specification SHA-256
`ba5a385521393151e6f1b5ddaece8e688d0315dd26ca9aa517cc030ca4be3f2d`
before job `296275`. It evaluates all ten already computed M2 combinations
without retraining or reading a locked partition. Because it searches the
same sparse mixed pools, every maximum is descriptive and selection-biased.

On PushT, the original global selection `(width=1024, sigma=0.25)` has
within-pool AUROC `0.5802771`; the descriptive within-pool maximum is
`(1024, 0.1)` at `0.6242869`, but its top-4 failure-rate reduction is
`-0.0065104`. On TwoRoom, the original `(512, 1.0)` has within-pool AUROC
`0.4923686`; the descriptive maximum is `(1024, 1.0)` at `0.5686829`, with
top-4 reduction `0.0091146`. The PushT-selected `(1024, 0.1)` transfer value
on TwoRoom is only `0.3827021`. No fixed width/sigma combination exceeds
within-pool AUROC `0.60` in both environments.

Thus the operational weakness is not explained solely by the original
sigma/width choice. The current single-noise epsilon-residual score has no
robust cross-environment within-query ranking result in the already trained
grid. The audit manifest SHA-256 is
`e4ced77323462fbf509725bc26f2c62228fab3335de7305d6ec1cdd39d0e7684`.

## A-101 -- Freeze one P1/P2-only M2v2 redesign before execution

Freeze `M2V2-P1-P2-FEASIBILITY-SPEC-2026-08-12.md` at SHA-256
`bc57c4500ed07daa8b43a3c4ef7432861649c854eaf4d6c06858dbc75c7cfb20`
before training or scoring the redesign. This is an exploratory response to
A-095 through A-100, not a revision of the original M2 result and not access
to P3/P4.

M2v2 pairs each existing width-1024 conditional M2 seed with a newly trained,
capacity-matched companion on the same genuine P1 D25 targets. The companion's
source input is hard-zeroed on every call. For each of the three seeds and all
five frozen noise levels, M2v2 subtracts unconditional epsilon squared-L2
error from conditional error under the same eight corruptions, standardizes
that contrast using a deterministic 10,000-pair P1-validation subset, and
averages the fifteen cells. Larger values denote less conditional advantage.
Online, exact within-population midranks replace the global Platt map, and a
nonzero-span gate aborts any non-interventional population.

The five weights remain `{0.25, 0.5, 1.0, 2.0, 4.0}`. Both environments use
the same twelve frozen P2 queries and planner/environment seeds. The offline
within-pool and paired closed-loop interpretation, including the stop/pivot
rule, was frozen in the specification before job `296277` began. Companion
training is job `296277`; dependent P1-reference, offline-audit, smoke,
full-grid, and decision jobs are `296281`, `296282`, `296283`, `296284`, and
`296285`, respectively. No original scorer, planner, P3, or P4 file is
overwritten.

## A-102 -- M2v2 is interventional but fails the prefrozen robust-promotion rule

All six job-`296277` companions completed and all 30 seed-by-sigma P1
validation contrast cells were non-degenerate. Contrast population standard
deviations ranged from approximately `0.872` to `4.499` in PushT and `0.423`
to `0.905` in TwoRoom, far above the frozen `1e-6` rejection threshold.

Offline job `296282` gives the following P2 candidate-pool results. PushT has
pair-weighted within-pool AUROC `0.5044825`, pool-bootstrap interval
`[0.3333333, 0.7619048]`, and top-4 failure-rate reduction `-0.0273438`,
interval `[-0.0690104, 0.0026042]`. Its between-pool score-variance fraction
remains `0.9999615`. TwoRoom has within-pool AUROC `0.5816846`, interval
`[0.1865079, 0.6612777]`, and top-4 reduction `0.0299479`, interval
`[-0.0052083, 0.0924479]`; its between-pool fraction is `0.9908727`.
The PushT and TwoRoom offline manifest SHA-256 values are, respectively,
`0af7176d645f3413e70358bf6352d2e3cf22214e08745734042a3521d4e275aa`
and
`ab058cf518f972978c16f032f5130f6dc3edc7f08464b111ec33602ccdc20e66`.

The real PushT smoke job `296283` passed, then all 120 job-`296284` tasks
completed with no failure. Every scored population passed the nonzero-span
gate and every selected-weight trajectory differed from its paired B0
trajectory, so M2v2 was an actual intervention in both environments. PushT
success counts across weights `0.25, 0.5, 1, 2, 4` are `[2, 2, 1, 1, 1]`
versus B0 `2/12`. The frozen tie-break selects `0.25`: it has one paired win,
one loss, ten ties, and exact two-sided p `1.0`. Existing selected P2 counts
are M1 `5/12`, original M2 `4/12`, and M3 `3/12`.

TwoRoom counts are `[5, 6, 6, 4, 8]` versus the independently revalidated
exact nominal B0 surrogate `6/12`. The frozen rule selects weight `4`: it has
two paired wins, zero losses, ten ties, and exact p `0.5`. This exploratory
`8/12` matches selected M3's count but not its query identities; their direct
comparison is two wins, two losses, eight ties. It is therefore an
encouraging environment-specific lead, not confirmatory evidence.

Four of the five prefrozen decision components pass: nonzero intervention,
point-estimate within-pool AUROC above `0.5` in both environments, the
cross-environment closed-loop gain rule, and trajectory change. The required
top-4 condition fails because PushT is negative. Hence job `296285` records
`operationally_promising_under_prefrozen_rule=false` and the frozen decision
is not to retune M2v2 repeatedly on P2 or promote it to P3/P4. The appropriate
pivot is the diagnostic/comparative thesis or M3 unless a new, separately
motivated method is specified without using these P2 outcomes.

M2v2 is also costly: mean PushT execution/scorer time is `230.65/169.78`
seconds per query versus original M2 `145.43/36.71`; TwoRoom is
`19.84/4.00` versus `17.20/1.14`. The job-`296285` decision-manifest SHA-256
is
`fbba7d8bff1f42031bea855f4d050e37d33acd72ddd45fe0ff777d07527de491`.
The human-readable result summary
`M2V2-P2-FEASIBILITY-RESULT-2026-08-12.md` has SHA-256
`8c4659e80d814681244c28d91b5b346bd2ff308d7ac954aa36e78b0552a69eaa`.

This result does not reverse the prior PushT conduct audit. The M2v2 run used
the same released reset, simulator labels, query identities, and planner path
that passed the 34,560-record execution audit and the separate 23,040-case
reset probe with zero primary or released label flips. In the absence of a
new concrete inconsistency, the PushT negative result is a scorer failure,
not evidence of an incorrectly conducted benchmark.
