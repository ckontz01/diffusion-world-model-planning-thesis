# E15 boundary-aware long-horizon diffusion versus SAGE development protocol

Date fixed before E15 model training: 25 August 2026  
Role: P1/P2 method development only  
Confirmation status: not authorized by this document

## 1. Focused research question

E15 is the one permitted outcome-informed redesign after E14. It asks one
focused question:

> Can one far-goal-conditioned, variable-duration velocity-diffusion proposer
> replace the published-equation SAGE reconstruction's learned latent-subgoal
> generator, eight-mode option prior, and 30 Le-WM-scored CEM populations while
> preserving long-horizon control quality?

The proposed method is a single bounded-action VAD network. It generates 300
complete local action options and uses one frozen-LeWM candidate-bank ranking
stage. It has no learned local-subgoal model and no CEM or MPPI refinement.

The scientific claim is not selected in advance. E15 also includes a matched
direct-goal eight-mode GMM and a matched diagonal Gaussian. If the GMM matches
or beats VAD, the result supports a broader learned-multimodal-proposal story,
not diffusion-specific superiority. If VAD cannot match full SAGE, E14/E15
remain an honest long-horizon limitation and E11/E13 remain the paper core.

## 2. Prior evidence and why one redesign is legitimate

E14 VAD beat its matched Gaussian on both registered offline metrics for every
seed, on both tasks and all three local durations, and beat shuffled-goal and
unconditional controls. It stopped because raw Cube proposals exceeded the
registered boundary rule before closed-loop evaluation.

The frozen post-E14 diagnostic reproduced that stop and showed:

- genuine raw action-domain overshoot followed by hard clipping;
- no material Le-WM selection amplification of the aggregate boundary mass;
- 300/300 unique candidates and little variance loss after clipping; and
- legitimate expert Cube saturation, especially on action coordinates 1--3.

The E15 data-only preflight then fixed a new episode-disjoint split and found
that about 21--22% of expert Cube coordinate-2 actions are exactly at a legal
limit, whereas PushT needs projection on less than 0.1% of elements. E15
therefore replaces hard output clipping with one common smooth legal-action
map and judges saturation relative to frozen expert geometry. It does not
weaken or reinterpret E14's failed rule.

This is the only boundary-aware VAD redesign authorized. A failure of E15's
fresh offline gate closes this long-horizon method line.

## 3. Comparator and artifact status

As of this freeze, no official SAGE code or checkpoint is linked from the
paper's arXiv record. The comparator remains **published-equation SAGE
reconstruction**, never “official SAGE.” It reuses the checksum-verified E14
subgoal and option-prior checkpoints without retraining or outcome-dependent
changes. The reconstruction deviations remain:

- the released 192-dimensional Le-WM CLS interface rather than spatial tokens;
- one current observation (`history_len=1`);
- PushT `state` (7 values) and Cube `observation` (28 values);
- cosine-loss coefficient `1.0`; and
- diagonal trajectory-mode covariance with log standard deviation in
  `[-5,2]`.

The archived SAGE source tar has SHA-256
`60167aed768eba55061f8a69e00ce6b81c19ff16e48bcbd6b16a59fd8d892180`.
The frozen normalized E14 training tree is
`experiments/gdp-cem-e14/development-run-20260823-99f92cbe/normalized-full-9e47eeb2`;
its normalization-audit SHA-256 is
`985454c195d2f785c665eb59d81efadb789512a4d03f3e44ffa3ac24140b6b40`.
Every reused checkpoint and summary must verify against its local
`sha256.txt` before evaluation.

The direct-goal eight-mode GMM introduced here is **not SAGE**. It deliberately
omits SAGE's local-subgoal generator and CEM and exists to isolate whether
diffusion contributes beyond generic multimodality.

## 4. Data firewall and immutable inputs

### 4.1 Offline data

The only E15 training and offline-gate artifacts are the successful data-only
preflight outputs:

| Task | Cache SHA-256 | Manifest SHA-256 |
|---|---|---|
| PushT | `2efc57e077cc6e5a627bf73b8ee50eeb308091d52fb734c71a79eb37279146a9` | `c8af1ddbf5e830a9257dba3a484d9eb10272d20fc11ea0f348080e9443c16dcc` |
| Cube | `b48ebb4735662d702289b9da12e55dc31766e8f1f245c1486f50e58cb0fb2994` | `e8c547962238fcd37b463acc0343b997af5525a90116c01b5f9f889fb23fd4a9` |

They derive only from old E14 `P1_train`, using the frozen episode hash in the
data-preflight specification. Each task contains 292,500 training and 90,000
validation rows, balanced as 6,500/2,000 rows in each of 45 `(delta,tau)`
cells. The two E15 roles have no episode overlap. E15 training jobs may open
only role 0. No validation row is used for checkpoint selection, early
stopping, scheduler selection, or hyperparameter choice.

The validation data are fresh for E15 fitting and selection but not globally
untouched confirmation evidence; they came from the earlier E14 training
pool. They remain development evidence.

### 4.2 P2 closed-loop data

Gate C, if authorized, reuses exactly the unused E14 identifier-only P2
manifests with 20 shared starts per task and goal horizons `25,75,150`:

| Task | Query TSV SHA-256 | Manifest SHA-256 |
|---|---|---|
| PushT | `a2308d25a274c2459187220ed15a028734dd9bbfb92c7bd41b878f4d76df9ce3` | `8730a5d659cb6f084f42ae666ea9689c9cc9c0fbdd7d38728b626db6e6e3251d` |
| Cube | `936acc3998a4adaa2e6661111802f093e030e2cd3619059b4dc0b71a76fcaf35` | `704ac338599894ebd6ae7989c5ba7a151259104c05a58e4e11c87e27e6b9a017` |

They use selection seed `2026082301`, the same episode/start pairs across
horizons, and are explicitly development-only (`claim_allowed=false`).

### 4.3 Protected evidence

E15 must not open metric-bearing D3 or D4 artifacts. It must never generate,
open, hash, or consume D5. P3, P4, C1, and I1 remain protected. Passing E15
can authorize only drafting a separate immutable confirmation protocol.

## 5. Common bounded action representation

All three new learned proposal families--VAD, diagonal Gaussian, and direct
eight-mode GMM--use exactly the target and inverse fixed in the data preflight.
With

```text
s = nextafter(float32(1), float32(0))
r = float32(s * s),
```

the expert target is

```text
a_projected = clip(a_expert, -r, r)
u = atanh(a_projected / s),
```

and every generated raw action is

```text
a = s * tanh(u).
```

`u` is standardized per action coordinate using E15-train active elements
only. Generated raw actions are converted to the planner coordinates expected
by released Le-WM using the exact two-operation float32
`StandardScaler.transform`. No robust-quantile or legal-bound hard clip is
applied to a new learned E15 proposal.

All methods report expert target-projection rate, generated strict legal-OOB
rate, exact legal-limit rate, near-limit mass at relative margins
`1e-6,1e-4,1e-3,1e-2,5e-2`, pre-squash `|u|`, normalized tanh-Jacobian mass
below `1e-2,1e-3,1e-4`, and post-squash diversity. This prevents a method from
passing merely by moving clipped mass from exactly `1.0` to `0.999999`.

The published-equation SAGE reconstruction and released Base CEM retain their
already frozen E14 planner coordinates and clipping/search rules. Applying the
new transform to them would silently modify the comparators.

## 6. Proposed and matched learned models

All new learned models condition on the same E15-train-standardized current
Le-WM CLS latent, far-goal CLS latent, current low-dimensional state, remaining
goal offset `delta`, and requested local duration `tau`. They output a padded
25-step primitive-action trajectory with inactive positions masked exactly.
Model seeds are `7201,7202,7203`.

### 6.1 Boundary-aware VAD (proposed method)

VAD retains E11/E14's cosine 100-step schedule, velocity target,
classifier-free far-goal dropout `0.15`, guidance scale `1.5`, five
deterministic reverse evaluations, width 512, four FiLM residual blocks, time
embedding 128, and EMA `0.999`. At a planning stage it samples 300 action
options once, rolls all through frozen Le-WM for `tau` steps, and executes the
option with minimum terminal squared distance to the far-goal latent.

### 6.2 Matched diagonal Gaussian

The Gaussian has the same condition encoder, width, four residual blocks,
action target, mask, training rows, optimizer, steps, seeds, and candidate
count. It predicts one diagonal mean/log-standard-deviation trajectory in
standardized `u` space, with log standard deviation clamped to `[-5,2]`.

### 6.3 Matched direct-goal eight-mode trajectory GMM

The GMM uses the same condition encoder, width, four residual blocks, action
target, mask, rows, optimizer, steps, seeds, and `K=300`. It predicts eight
trajectory-level mixture weights and eight diagonal trajectory means and log
standard deviations in standardized `u` space. A single categorical draw
selects one mode for an entire trajectory; modes are not selected separately
per time step. Log standard deviations are clamped to `[-5,2]`.

Its training loss is active-dimension-normalized trajectory mixture NLL plus
`0.05` times the KL divergence from the batch-mean mode probability to a
uniform eight-mode distribution. The small balance term prevents a trivially
dead head without requiring every conditioned query to be uniformly
multimodal. No subgoal, CEM, diffusion step, or SAGE checkpoint is used.

### 6.4 Conditioning nulls

At fixed seed `7201`, VAD also trains:

- a shuffled-far-goal model, using a deterministic derangement inside each
  training `(delta,tau)` cell; and
- an unconditional model, with far-goal conditioning always replaced by the
  learned null token.

They share all other settings. They are diagnostic controls and never enter
closed-loop Gate C.

## 7. Training freeze

Every new model trains for exactly 30,000 optimizer steps with batch 1,024,
AdamW learning rate `2e-4`, weight decay `1e-4`, 1,000-step linear warmup,
gradient clipping `1.0`, BF16 autocast, deterministic sampling, and EMA
`0.999`. No validation artifact is opened during training. The scientific
checkpoint is the final EMA at step 30,000; there is no best-checkpoint or
early-stopping choice.

The exact trained conditions per task are VAD, Gaussian, and GMM for all three
seeds, plus shuffled and unconditional VAD for seed 7201: 11 checkpoints per
task, 22 total. Divergence, non-finite loss, wrong GPU, wrong input hash, or
wrong row access is a technical/training-validity failure, not permission to
change a hyperparameter.

Parameter counts, training wall time, peak allocated GPU memory, and final
train objective are reported for every condition. Parameter matching is by
shared trunk design and disclosed count, not by adding unused weights.

## 8. Gate A: implementation and lineage validity

Before any offline performance result is opened, tests and manifests must
prove:

1. both E15 cache and manifest hashes per task match Section 4;
2. training loads role 0 only and never opens validation rows;
3. all standardizers match the train-only arrays in the immutable cache;
4. the smooth transform is finite, strictly legal, differentiable in the
   tested interior, and matches an independent NumPy formula;
5. duration masking is exact in losses, sampling, uniqueness, and metrics;
6. velocity target and deterministic DDIM agree with independent synthetic
   checks;
7. Gaussian NLL and GMM trajectory-mixture NLL agree with independent
   formulas;
8. the GMM samples one component per whole trajectory and uses deterministic
   CPU categorical/noise draws under the fixed generator;
9. every model/configuration/parameter count and final checkpoint hash is
   recorded;
10. frozen Le-WM candidate tensors have exact released macro-action shapes;
11. SAGE full and one-stage planners load the unchanged E14 checkpoints;
12. no protected path or artifact is opened; and
13. all outputs record development-only status and `claim_allowed=false`.

Failure blocks Gate B until a purely technical correction is documented in
the implementation changelog and frozen in a new source snapshot. Scientific
settings cannot change.

## 9. Gate B: fresh offline proposal validity

After all 22 training jobs are terminal and checksum-valid, evaluate every one
of the 90,000 E15-validation rows per task. No partial metric may be opened
before all required evaluation cells are terminal and successful.

For every task, seed, `delta`, and `tau`, report:

- representable-expert best-of-300 raw-action MSE;
- best-of-300 MSE to the original unprojected expert action as a secondary
  diagnostic;
- Le-WM terminal cost of the far-goal-selected option against the recorded
  true local latent;
- far-goal selection cost;
- candidate variance and pairwise/diversity summaries;
- unique rounded full trajectories;
- all Section-5 boundary/Jacobian diagnostics;
- proposal, Le-WM scoring, and total synchronized latency; and
- for GMM, global mode mass, conditional entropy/effective modes, posterior
  winning-mode usage, and sampled mode counts.

### 9.1 Common bank-integrity rule

Every VAD, Gaussian, and GMM task/seed bank must be finite, have at least 285
unique full trajectories after rounding raw actions to `1e-4` on every
validation query, have strict legal-OOB fraction exactly zero, and have exact
`-1/+1` fraction exactly zero.

For each task and `tau`, let `Emean` and `Eq99` be the mean and 99th percentile
of the validation expert per-trajectory fraction for a diagnostic. Let
`Gmean` and `Gq99` be the corresponding generated-bank per-query values,
where a bank value averages candidates, active times, and coordinates. For
both (a) raw-action mass within 1% of a legal limit and (b) normalized tanh
Jacobian below `1e-3`, require:

```text
Gmean <= max(2 * Emean, Emean + 0.05)
Gq99  <= min(1.0, Eq99 + 0.15).
```

The expert references are recomputed from the immutable cache and must match
the data-preflight manifest. These thresholds were fixed from expert geometry
before any E15 model was trained. Other registered margins/Jacobian thresholds
are reported but do not gate.

### 9.2 GMM structural rule

For every task and GMM seed:

- every one of eight modes must have global mean prior mass at least `0.005`;
- at least six modes must be the maximum posterior-responsibility mode for at
  least `0.001` of validation rows; and
- equal-cell mean normalized prior entropy must be at least `0.25`, where
  entropy is divided by `log(8)`.

These checks establish that the nominal eight-mode control did not reduce to
one dead component. They do not require GMM to beat VAD offline. A structurally
valid GMM enters Gate C regardless of its offline ranking, preventing
performance-based filtering of the decisive control.

### 9.3 VAD mechanism and conditioning rule

VAD is eligible only if, for each seed:

1. equal-task representable-expert best-of-300 MSE is lower than Gaussian;
2. equal-task selected true-local Le-WM terminal cost is lower than Gaussian;
3. both directions hold separately on each task for at least two of the three
   local durations; and
4. at seed 7201, true VAD beats both shuffled-goal and unconditional VAD on
   both primary metrics in the equal-task result and on each task for at least
   two durations.

VAD is not required to beat GMM at Gate B. The VAD-versus-GMM scientific
question is reserved for the fixed closed-loop P2 comparison.

Gate C is authorized only if the common integrity rule passes for VAD,
Gaussian, and GMM, the GMM structural rule passes, and every VAD mechanism and
conditioning requirement passes. Otherwise the long-horizon line stops. No
new transform, endpoint, threshold, seed, loss, or rescue training is allowed.

## 10. Gate C: fixed P2 long-horizon comparison

### 10.1 Arms

Exactly six arms enter, all on the same starts, model/planner seeds, schedules,
environment budgets, candidate counts, Le-WM checkpoint, and GPU:

1. **released Base CEM**--300 candidates, 30 rounds, 30 elites;
2. **full published-equation SAGE reconstruction**--generated local subgoal,
   300 eight-mode GMM options, then 29 additional CEM populations (30 total);
3. **SAGE one-stage ablation**--the same generated local subgoal and 300 GMM
   options, ranked once by Le-WM against that local subgoal, no CEM;
4. **boundary-aware VAD**--300 direct far-goal options, one Le-WM ranking;
5. **direct-goal eight-mode GMM**--300 options, one Le-WM ranking; and
6. **boundary-aware diagonal Gaussian**--300 options, one Le-WM ranking.

SAGE one-stage is a new ablation of the disclosed reconstruction, not a
published SAGE baseline. It isolates what the local-subgoal/GMM stack achieves
before iterative refinement.

### 10.2 Horizons, schedules, and budgets

P2 uses goal horizons `25,75,150` and SAGE's published schedules:

| Goal horizon | Local option schedule |
|---:|---|
| 25 | `25` |
| 75 | `15 x 5` |
| 150 | `15 x 10` |

PushT receives `2H` environment steps; Cube receives `H`. All methods replan
at the same stage boundaries. There are 20 shared base starts per task and
three fixed model/planner seeds. Each task/base-start cluster retains all
arms, horizons, and seeds.

### 10.3 Timing and resource measurement

Every planning stage synchronizes CUDA immediately before and after the full
planner call. End-to-end stage latency includes observation/goal encoding,
proposal generation, and all Le-WM scoring, but excludes environment stepping.
Proposal generation and Le-WM scoring are also synchronized and reported
separately. Report all-call and post-first-call medians, peak allocated GPU
memory, active learned parameters, number of learned proposal components, and
Le-WM-scored candidate populations.

“30-fold” may describe only the population-count ratio. Any wall-clock
efficiency statement must use measured matched-hardware latency.

### 10.4 Analysis unit and task-first reporting

Report success first by task and horizon, then by seed. The pooled development
summary is the equal-task/equal-horizon mean, never an episode-weighted pool.
Paired bootstrap resampling is stratified by task and resamples the 20 base
starts within each task; every resampled cluster keeps all horizons, arms, and
seeds paired. Individual episodes and the three model seeds are not treated as
independent bootstrap observations.

Cube ceiling behavior must be stated explicitly wherever present.

### 10.5 Frozen D5-authorization rule

VAD can authorize drafting a focused untouched confirmation only if all of the
following development conditions hold:

**Mechanism against simple proposals**

- VAD minus Gaussian equal-task/equal-horizon success is positive;
- no VAD-minus-Gaussian task/horizon cell is below `-0.05`.

**Diffusion specificity against multimodality**

- VAD minus direct GMM equal-task/equal-horizon success is positive;
- no VAD-minus-GMM task/horizon cell is below `-0.05`; and
- VAD has positive task-specific mean difference over GMM on at least two of
  three horizons for each task.

**Genuinely long-horizon relevance**

- at horizon 150, VAD is at least `+0.15` above released Base CEM on at least
  one task.

**Full SAGE comparison--one of two routes**

1. *Superiority-development route:* over the genuinely long P2 horizons
   `{75,150}`, VAD minus full SAGE is positive in the equal-task mean, is
   nonnegative at horizon 150, and no task/horizon cell is below `-0.05`; or
2. *Efficiency/non-inferiority-development route:* over `{75,150}`, VAD is no
   worse than `-0.03` in the equal-task mean, is no worse than `-0.03` at
   horizon 150, no task/horizon cell is below `-0.10`, and full SAGE's median
   synchronized end-to-end stage latency is at least five times VAD's.

The SAGE one-stage arm is mandatory and reported mechanistically but does not
add a separate authorization inequality. All point differences, paired
intervals, and latency ratios are reported even if a gate fails.

These are development gates, not final hypothesis tests. Passing authorizes a
separate D5 protocol; it does not itself support a confirmatory superiority or
non-inferiority claim.

## 11. What a later confirmation must do

No D5 artifact may be created automatically. If Gate C passes, a separately
reviewed and hashed protocol must freeze, before generating identifiers:

- untouched starts and exclusions;
- all six reported arms;
- primary long horizons `{75,100,125,150}` with all six SAGE horizons shown;
- model/checkpoint/source hashes;
- a paired sensitivity/sample-size calculation based on P2 discordance;
- superiority or non-inferiority estimand and margin selected by the frozen
  Gate-C route;
- task-first clustered inference that keeps arms/horizons/seeds paired;
- synchronized latency and resource accounting; and
- a complete information barrier until every evaluation cell is terminal.

If E15 Gate B or Gate C fails, D5 remains untouched and the focused
long-horizon diffusion claim is not pursued further.

## 12. Claim discipline

Even a successful E15/D5 result must say **published-equation SAGE
reconstruction** unless official artifacts are released and run. E11 and E13
remain separate short-horizon confirmatory evidence; they are not pooled with
P1/P2 development results. ACID and PRISM remain secondary context for the
focused long-horizon paper.

The strongest authorized future claim, conditional on untouched confirmation,
is narrow:

> A compact far-goal-conditioned velocity-diffusion proposer can replace this
> disclosed SAGE reconstruction's explicit local-subgoal generator,
> trajectory GMM, and iterative CEM while preserving or improving long-horizon
> success at substantially lower measured planning cost.

The protocol does not authorize a broad claim that diffusion planning,
best-of-N world-model ranking, or diffusion-generated trajectories are new.
