# E14 long-horizon diffusion and SAGE-reconstruction development protocol

Date fixed before E14 model training: 23 August 2026  
Role: P1/P2 method development and comparator validation only  
Confirmation status: not authorized by this document

## 1. Purpose

E11 established that a one-pass, goal-conditioned velocity-diffusion action
proposal can outperform matched Gaussian proposals and a published-equation
ACID reconstruction at a 25-step goal offset on the frozen Le-WM stack. E13
then showed statistical parity, with lower inference cost, against a disclosed
PRISM-DP reconstruction at that same offset. Neither study establishes that
the method remains useful when the requested goal is 50--150 environment steps
away.

E14 asks the acceptance-critical next question:

> Can a diffusion proposal retain its short-horizon mechanism advantage and
> support long-horizon frozen-world-model planning under the same task,
> horizon, schedule, and search interface used by SAGE?

This is a bounded development study. It may select one of two diffusion
endpoints on development data, but it may not read, generate, or evaluate a
new confirmation split. A separate immutable confirmation protocol is required
after every implementation and comparator-validity gate passes.

## 2. Primary-source and artifact status

The SAGE source is archived at
`downloads/sage-arxiv-2607.17973v1/source.tar.gz`, SHA-256
`60167aed768eba55061f8a69e00ce6b81c19ff16e48bcbd6b16a59fd8d892180`.
The arXiv source specifies the tasks, horizons, schedules, candidate budget,
CEM rounds, training-row counts, model depths/widths/heads, GMM mode count,
optimizer, selected epochs, and losses. As of this freeze, no official SAGE
code or checkpoint is linked from the arXiv record or author page. Therefore
E14's SAGE arm is always named **published-equation SAGE reconstruction**,
never official SAGE.

Three material details are not disclosed by the paper source:

1. the numerical coefficient on the cosine term in the subgoal loss;
2. the covariance parameterization and numerical bounds of the trajectory
   GMM; and
3. the numerical observation-history length and exact low-dimensional state
   fields.

The paper also describes spatial Le-WM tokens, whereas the released Le-WM
checkpoint and code used by all earlier thesis experiments expose a projected
192-dimensional DINOv2 CLS embedding to the predictor and goal cost. E14 keeps
that released interface and checkpoint. It does not modify the world model to
make the reconstruction appear closer to SAGE.

The frozen reconstruction choices are:

- one current 192-dimensional CLS latent, matching the released evaluator's
  `history_len=1` interface;
- PushT low-dimensional `state` (7 values) and Cube `observation` (28 values);
- cosine-loss coefficient `1.0`;
- diagonal covariance for each trajectory-level Gaussian, with log standard
  deviation clamped to `[-5, 2]`;
- all latent, state, and action standardizers fitted on P1-train only.

These deviations must appear in every result and paper table that includes the
reconstruction.

## 3. Data firewall

Only the already frozen P1 episode partition may train models or provide
offline validation rows. P1-train and P1-validation remain separated at the
episode level by the existing seed-20260728 split. A small closed-loop
development study may use P2 after the offline gates pass; P2 is development
data and has already been exposed in earlier work.

E14 development must not read metric-bearing D3 or D4 files. It must not read,
generate, or consume any proposed D5 manifest or outcome. Existing P3/P4, C1,
and I1 artifacts are protected. Identifiers needed only to prove exclusion may
be hashed without opening outcome files.

The P1 cache is built from the frozen flat-latent and five-step transition
caches for PushT and Cube. Every row contains:

- current latent at `t`;
- local latent at `t + tau`;
- far-goal latent at `t + delta`;
- current low-dimensional state;
- the expert primitive actions from `t` through `t + tau - 1`;
- episode, step, P1 role, `delta`, `tau`, and source-row identifiers.

The far-goal offsets are exactly
`{15,20,25,30,40,45,50,60,65,75,90,100,115,125,140,150}`. Local durations are
exactly `{15,20,25}`, restricted to `tau <= delta`. The sampler balances all
valid `(delta,tau)` pairs and selects exactly 400,000 training and 40,000
validation rows per task without replacement. Selection is deterministic and
recorded before training. Failure of any cell to supply its required quota is
an input-validity stop, not permission to sample with replacement.

## 4. Frozen SAGE reconstruction

The subgoal generator is a four-layer Transformer decoder of width 512 with
eight attention heads. Typed tokens represent current latent, far-goal latent,
low-dimensional state, `delta`, and `tau`; a goal-shaped decoder query predicts
a residual added to the far-goal latent. It trains for five epochs with batch
128, AdamW learning rate `1e-4`, weight decay `1e-4`, gradient clipping `1.0`,
and BF16. Its objective is mean SmoothL1 plus `1.0 * (1 - cosine)` in the
P1-train-standardized latent space.

The option prior is a three-layer Transformer decoder of width 512 with eight
heads and eight trajectory-level Gaussian modes. Five learned action queries
represent five primitive actions each; a duration mask activates three, four,
or five queries for `tau=15,20,25`. It trains for three epochs with the same
batch, optimizer, precision, and clipping settings. Every training row uses
the frozen subgoal generator's prediction (Gen100), not the true local latent.
Its objective is diagonal trajectory-mixture negative log likelihood over only
the active primitive-action dimensions.

At each planning stage the reconstruction samples 300 initial options from the
GMM, Le-WM scores them against the generated local latent, and the 30 best
candidates initialize 29 further released-Gaussian CEM updates. The total is
30 Le-WM-scored populations, matching SAGE and Base CEM.

## 5. Bounded diffusion development ladder

Both diffusion candidates use the E11 cosine schedule, velocity target,
classifier-free far-goal dropout `0.15`, five deterministic reverse
evaluations, guidance scale `1.5`, EMA `0.999`, and robust action bounds. Both
condition on current CLS latent, current low-dimensional state, far-goal CLS
latent, remaining `delta`, and requested `tau`, and both use a five-step
duration mask. Model width/depth remain 512/4. Training uses the same balanced
400k/40k cache and three fixed model seeds `6101,6102,6103`.

Two endpoints, and no others, are authorized:

1. **VAD (variable-duration action diffusion):** diffuse the padded 25-step
   action option only. At inference, sample 300 options once and let frozen
   Le-WM choose the option whose `tau`-step predicted terminal latent is
   closest to the far-goal latent. This is the minimal long-horizon extension
   of E11.
2. **CVD (coupled subgoal-action velocity diffusion):** diffuse one joint
   vector containing the standardized local-latent residual and padded action
   option. Each sample is therefore a paired proposed subgoal and action.
   Frozen Le-WM ranks a pair by terminal consistency with its sampled local
   latent; the far goal influences generation through conditioning rather than
   an added SAGE generator. CVD remains one learned diffusion network and one
   Le-WM scoring pass.

Each endpoint has a capacity-matched conditional diagonal-Gaussian control
with identical inputs, outputs, masking, training rows, and candidate count.
VAD and CVD also receive shuffled-far-goal and unconditional diagnostic models
for one fixed development seed. There is no ACID cost, reachability head,
SAGE subgoal network, CEM refinement, or learned success verifier inside either
diffusion endpoint.

## 6. Temporal schedule and evaluation budgets

E14 uses SAGE's published main schedule exactly:

| Goal horizon | Local option schedule |
|---:|---|
| 25 | `25` |
| 50 | `25 + 25` |
| 75 | `15 x 5` |
| 100 | `15 x 5 + 25` |
| 125 | `15 x 7 + 20` |
| 150 | `15 x 10` |

PushT receives `2H` environment steps and Cube receives `H`. Every method is
replanned at the same schedule boundaries. Base CEM and the SAGE reconstruction
use `K=300`, 30 rounds, and 30 elites per stage. Diffusion and Gaussian
selectors use `K=300` and exactly one Le-WM evaluation per stage. A secondary
`K=16` efficiency diagnostic is permitted only after the `K=300` development
result and cannot select the endpoint.

## 7. Development gates

### Gate A: cache and architecture validity

The cache must prove exact episode containment, exact `delta` and `tau`, no
P1-train/P1-validation episode overlap, balanced pair counts, correct raw-row
joins, finite arrays, train-only standardizers, source hashes, and no protected
read. Model tests must prove duration masking, deterministic sampling, mixture
NLL against an independent formula, classifier-free behavior, and exact
candidate/Le-WM shape compatibility. Parameter counts and every deviation from
SAGE's disclosed design are reported before performance is inspected.

### Gate B: offline conditioning and proposal validity

On the fixed 40k P1-validation cache, report per task, `delta`, and `tau`:
training-family objective, expert-action error, best-of-300 action error,
Le-WM terminal cost, candidate variance, unique-candidate count, robust-boundary
fraction, and latency. CVD additionally reports generated-local-latent error
and Le-WM/action-to-sampled-subgoal consistency.

A diffusion endpoint remains eligible only if all of the following hold for
each model seed:

- every proposal bank is finite, has at least 285 unique rounded candidates,
  and has robust-boundary fraction at most 25%;
- its equal-task best-of-300 action error and Le-WM cost are both lower than
  its matched Gaussian control;
- the direction holds separately on PushT and Cube for at least two of the
  three local durations;
- the fixed-seed true model beats both its shuffled-goal and unconditional
  controls on equal-task best-of-300 action error and Le-WM cost; and
- CVD, if considered, beats its Gaussian control on local-latent error and
  terminal consistency as well.

### Gate C: P2 closed-loop endpoint selection

Only endpoints passing Gate B enter a fixed P2 development pilot at horizons
`25,75,150`, with 20 shared queries per task and three model seeds. The arms
are released Base CEM, published-equation SAGE reconstruction, every eligible
diffusion endpoint, and its matched Gaussian. Queries, seeds, schedules,
candidate banks, and environment budgets are identical across matched arms.

An endpoint is confirmable only if it:

- exceeds its matched Gaussian on equal-task/equal-horizon success;
- has no task-horizon loss to Gaussian worse than five percentage points;
- is at least 15 percentage points above released Base CEM at horizon 150 on
  at least one task, showing that it addresses a genuinely long-horizon
  failure rather than merely preserving H25 performance; and
- stays within five points of the SAGE reconstruction in the equal-task,
  equal-horizon average or is faster by at least 5x per planning stage.

If both endpoints pass, select the endpoint with the larger paired
equal-task/equal-horizon success difference over its own Gaussian control.
Ties within one percentage point are broken by lower median stage latency.
This selection rule is fixed before any P2 E14 outcome is generated.

Failure of the SAGE reconstruction's structural tests or grossly invalid
behavior blocks a SAGE comparison but does not erase the diffusion-versus-
Gaussian or diffusion-versus-released-CEM development results. It cannot be
"rescued" after outcomes by changing undisclosed reconstruction choices.

## 8. What passing authorizes

Passing Gates A--C authorizes writing a separate D5 confirmation protocol.
That future protocol must freeze untouched starts, exclusions, model/checkpoint
hashes, all arms, all six horizons, three model seeds, clustered inference,
non-inferiority/superiority margins, task-first reporting, latency and training
cost accounting, and an information barrier before D5 is generated.

E14 development itself cannot support a paper claim. Any later claim must say
"published-equation SAGE reconstruction" unless official SAGE code is released
and run. Adjacent diffusion work--Diffuser-style state-action trajectory
models, Hierarchical Diffuser, Subgoal Diffuser, and HDFlow--prevents a broad
claim that diffusion or diffusion-generated subgoals are new. The intended
narrow claim is about one-pass, duration-conditioned diffusion proposals for a
frozen Le-WM planner, isolated against matched Gaussian proposals and evaluated
under SAGE's long-horizon protocol.
