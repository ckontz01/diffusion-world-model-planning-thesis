# CVL-1: full-budget candidate-value learning

Status: **executable implementation, outcome-informed method development;
NOT approved to launch**. Completion revision of preparation `4ed1b80`.
Prepared 14 September 2026 from accepted historical commit
`9e90b5ced087f7c12051b603e3553472b17db8e7`. This document is the resource/scientific
approval package, not a record of collected labels or a claim of efficacy.

## Recommended decision

Approve, if desired, one staged diffusion-only experiment: **96 training + 32
ranking-validation + 32 closed-loop development source references**, up to
**16,384 candidate-tail executions**, a fixed small value ensemble and logistic
control, then at most **512 closed-loop episodes**. Recommend an aggregate
**50 A6000 GPU-hour ceiling**, 2 CPU training wall-hours, 20 GB new remote
artifacts and 40 GB free on the external backup SSD. The two CPU wall-hours include
all evaluator fitting and both analysis jobs, not just neural fitting. Collection is likely about
19–29 GPU-hours, not minutes; uncertainty and fail-stop reservations are explicit
in [RESOURCE-PLAN.md](RESOURCE-PLAN.md). No confirmation or GMM work is inside this
envelope. A positive development result would justify proposing, not launching,
the matched-proposer mechanism study described below.

## Question and estimand

For a live decision at absolute time t, goal offset H and candidate action chunk
u of length 15, learn

`q(z_t, g, s_t, u, LeWM(z_t,u), H,t) = P(native success by 2H | execute u,
then original VAD continuation, original remaining budget 2H-t)`.

Native success during the first chunk counts. Discount is 1. The label is binary
native goal-reaching success, not distance, shortest-path feasibility, optimal
value, or recovery under all possible policies. A negative means failure under
this particular tail-policy/budget/RNG distribution, **not irrecoverability**.
The available latent and seven-state representation can alias unobserved physical
history; q is a conditional predictor, not a claim of a complete Markov state.

The main scientific intervention is replacing candidate scoring, initially not
learning a new proposer. Receding-horizon repeated use of q is a different policy
from its continuation label generator. Within-bank selection and subsequent
closed-loop behavior therefore require separate evidence.

## Historical boundary and frozen components

Accept the single-anchor ranking result at `9e90b5c` as-is. Its 32 references are
excluded from this allocation; none of its candidate outcomes are reused as
supervised labels. Do not rerun it, optimize a greedy/continuation mixture against
it, or infer that immediate selection is generally inferior. Continuation remains
the baseline. This is not historical SAGE-fidelity work.

Use unchanged `independent_pusht_runtime.build('vad_continuation',7201)` and the
existing fresh driver, initializer, goal rendering, checkpoint normalization,
float32 action decoding, native success predicate and physics stepping. The
existing E18 solver generates 64 first candidates and, at local delta >=30,
8 continuations each, scored by the mean of the lowest two costs. At delta=15 its
original first-only fallback remains the baseline. Keep the diffusion schedule,
guidance, adapter, LeWM, candidate counts and all frozen model tensors unchanged.
The accepted combined diffusion/adapter/LeWM tensor identity is
`f0c666cc011ab057390f7e1571cf3d8bde905d13ff11f1d406f6d3dd8575340d`.

The new hook runs the original solve and verifies its selected macro before
replacing only its returned action macro. All four selectors consume the same
full proposal workload, including second-level proposals even when their score
does not need them. This preserves proposal RNG advancement and isolates scoring;
it does **not** claim a speedup from skipping continuation generation. Do not
change or retrain any frozen module. Batch size is explicitly **one environment**.

## 1. Allocation and exposure

All candidate references come from the previously exposed independent collection
indices 0–1599. **Do not open, hash, model-evaluate or allocate 1600–5999.** No D5,
other protected partition, SAGE grid, new reference collection or training-set
augmentation is involved. References are independently collected source episodes,
not rows made independent by changing a horizon, start, seed or candidate.

[PROPOSED-ALLOCATION.json](PROPOSED-ALLOCATION.json) lists the exact proposed IDs.
It is generated without reading any research data: exclude the accepted 32,
sort remaining IDs by SHA-256 of
`candidate-value-v1-20260914|reference-allocation|<id>`, then take first 96 for
train, next 32 for validation and next 32 for closed-loop. Do not reshuffle on
outcomes. Before execution, identifier-only metadata must verify selected IDs
map to distinct original source keys and pin the exact permitted record bytes.
An alias/missing record is a blocker, not permission to silently replace a ref.
`candidate_value_freeze.py` authenticates the historical input lock and registry,
exports only the selected 160 identity/seed/path/hash fields, and rejects aliases.
It does not open any reference NPZ; nonselected registry outcome fields are not
used, reported or exported. Runtime/input capsule generation is still a deployment
step before launch approval; synthetic identity tests are not a real-input
certificate. No 1600–5999 reference payload may be opened or hashed.

All horizons, anchors, candidates, labels, tail draws and any future GMM rows from
a source stay in that source's split. The 32 closed-loop references are
**model-held-out development**, not untouched scientific confirmation: their
historical outcomes were already exposed. The selection rule is outcome-blind,
but the overall study is knowingly outcome-informed. Historical training exposure
of the frozen proposer is not reclassified as fresh confirmation.

|Split|References|Banks (maximum)|Candidate chunks|Tail executions|
|---|---:|---:|---:|---:|
|Train|96|768|6,144|12,288|
|Ranking validation|32|256|2,048|4,096|
|Closed-loop only|32|No label collection|—|512 episodes later|

The exact factorization is **128 references × 2 horizons × 4 anchor slots ×
8 distinct candidate indices × 2 continuation draws = at most 16,384 binary
outcomes**. These are 1,024 potential banks and 8,192 candidate-index rows,
not necessarily 8,192 unique action values. Each bank has 64 proposed indices;
only eight have labels. The separate original-prefix trajectories number 256
and are not extra supervised outcomes. Physical duplicates, unavailable anchors,
and actual tail/unique-chunk counts are reported separately.

Each collection reference has both H75 and H150 and four **absolute** anchors:
`(0,30,H,2H-15)`, i.e. `(0,30,75,135)` and `(0,30,150,285)`.
They cover an early intervention, a later first-cycle decision, cycle restart and
the final budget chunk. These are deliberate sparse decision strata, not all
possible planner states. Do not add an anchor in response to performance.

## 2. Prefixes, candidate sampling and coverage

For each reference/H, execute one fresh original-continuation prefix trajectory
with planner seed `seed('prefix', reference,H)` as implemented in the core. Cache
the four observable candidate-bank records only when the prefix reaches that
anchor without earlier native termination/truncation. Never continue a terminated
episode merely to create a late anchor; mark that anchor unavailable, with reason.
Do not impute a negative label or replace it with a new source. Anchor zero is a
decision before any post-action success check, matching the accepted convention.

For every live anchor, sample **eight distinct indices from its first-64 bank**:

1. Include the original continuation winner and immediate-distance winner (lowest
   original index on an exact tie).
2. If they differ, take six additional indices; if identical, take seven.
3. Additional indices are ordered by
   SHA-256(`VERSION|candidate-sampling|reference|H|t|candidate_index`).
   Take the first required entries among nonwinner indices, without replacement.

The sampler is fixed before new outcomes; it consumes neither planner nor global
RNG. Nonwinners have pseudorandom design inclusion probability 6/62 or 7/63,
winners 1. Index coverage is 8/64=12.5%; identical physical chunks can occupy
different indices. Do not resample to hide duplication. Record all 64 chunk
hashes, exact/1e-4-rounded unique counts, sampled unique count, winner overlap,
immediate/continuation rank percentiles and per-stratum coverage. Report the
fraction of live/unavailable anchors. A sampled-bank maximum is neither an
exhaustive oracle nor an estimate of optimal controllability.

Winner-enriched sampling changes the supervised population. Primary training and
ranking metrics target this declared eight-slot design, not a uniform full-64
distribution. Report uniform-over-sampled-eight as the non-neural selection
control. Do not call it uniform-over-64. Full-64 deployment is a declared change
in selection pressure, to be tested in closed loop, not silently equated with
offline eight-way validation.

## 3. Full-budget labels and exact RNG scope

For each live anchor's eight candidates, perform two candidate-tail draws. Each
branch constructs a fresh environment and policy, using the accepted explicit
fresh reset with the original record and recorded environment seed; prefix
planner seed is the same for every branch of this reference/H. Run the unchanged
continuation policy from t=0 to the anchor. Verify requested initialization,
prefix delivered actions, native state/dynamics/observations, schedule, bank and
post-bank RNG against the corresponding original prefix. **No mid-episode
visible-state setter, guessed private state reset or hidden physics step.**

At the designated solve boundary, return the selected bank chunk through the
ordinary policy buffer and decoder. Do not reset its stage, remove a buffer step,
or invoke legacy dataset evaluation. All later choices are the original VAD
continuation, not the learned selector or immediate arm. It replans normally
every 15 delivered actions, through the original remaining budget. No positive
label is generated solely because the requested goal equals the initial state.

The bank/prefix seed is shared across both tail draws, so their feature vectors
and first chunks are identical. Immediately after generating the anchor bank,
assign each branch's explicit proposal generators the deterministic seeds from
`candidate_value_contract.tail_seeds(reference,H,t)`: interpret the first 15 hex
digits of SHA-256(`VERSION|tail-pair|reference|H|t`) as an integer, shift left one,
then use that even integer for draw 0 and its odd successor for draw 1. Paired
seeds are distinct by construction; the fixed grid also has a collision regression
test. Draw is **not** part of the
model input. Use the same tail seed across candidate indices (common random
numbers). The unused GMM generator is independently owned and recorded too.
Neither model parameters nor continuation algorithm changes. This deliberately
defines a two-draw Monte Carlo target for the original policy algorithm, not
bitwise reuse of its historical post-anchor noise sequence. Retain all initial,
pre-bank, post-bank and tail-initial generator state hashes. No candidate-specific
tail seed, global RNG borrowing, success-dependent seed search, cache sharing
between branches or policy object reuse. Environmental stochastic state follows
the identical fresh reset/prefix path; the intervention randomizes only the
explicit policy sampling streams. Verify no other inference RNG is consumed.

At a final-budget anchor, there may be no stochastic tail after the forced chunk;
the two declared streams can therefore yield identical outcomes. Distinct RNG
streams do not guarantee distinct trajectories or independent episodes.

Success during actions 1–15 is included; later native success also counts. Stop on
the first native success or truncation, or at absolute time `2H`. A success on the
last permitted step counts. An incomplete infrastructure/evaluator run is not a
negative. Any exception stops dispatch and leaves an incomplete, unvalidated
scientific record. A later verified planner failure may be described as a policy
failure (zero unless success already occurred), but the implementation does not
guess that classification, fit on partial failure output, or resume automatically.

Record first-chunk success separately for description, not a second tuned target.
Keep both binary outcomes in storage and weighted BCE. The corresponding equally
weighted fraction is exactly 0, 0.5 or 1 for selection reporting; never round it
to a majority label or replace it with a distance target.
The two Bernoulli outcomes are two draws for one candidate, not independent source
episodes. A noisy max over eight two-draw averages is an optimistic descriptive
sample statistic; do not advertise it as attainable oracle performance.

## 4. Model, objective and sparse successes

Feature vector, fixed order, **619 float32 entries**:

- Current LeWM latent 192, goal latent 192, candidate predicted terminal latent
  after the first 15 actions 192. Use the pinned proposer latent mean/std for all
  three, including the LeWM prediction; no replacement latent scaler in the frozen stack.
- Current seven-state vector in the pinned checkpoint's state normalization.
- Actual candidate 15x2 chunk in planner-action space (30); ordinary pinned
  decoder is still applied only at delivery.
- Six schedule/time entries: H/150, t/(2H), (2H-t)/300,
  `(H-t%H)/150`, tau/15 (=1), and integer cycle `t//H`.

No reference ID, RNG seed, split indicator, future simulator state, candidate
outcome, success flag, or actual future distance. Source IDs are metadata for
grouping/bootstrap only. No second-level successor labels or ground-truth future
inputs. The runtime hook constructs features from inference-time data only.

The pinned checkpoint transformations above are unchanged. A separate evaluator-
only weighted mean/std is fitted on training rows only (same hierarchical weights
as BCE); a standard deviation below 1e-6 uses scale 1. It is frozen with training
min/max before validation and applied identically at inference. This is not a
replacement for proposer/action normalization. No validation/closed-loop fitting,
feature selection, checkpoint choice, threshold tuning or candidate labels.

MLP: `619 →128 ReLU →64 ReLU →1 logit`, **87,681 parameters**. Train three fixed
initialization seeds 8201,8202,8203; average sigmoid probabilities at inference.
Do not choose the best seed. Minimal learned control: one **620-parameter logistic
regression** on exactly the same features and same labels, seed 8201. Non-neural
controls: original continuation, immediate selection, uniform sampled selection,
and a train-only constant success probability for calibration.

One inexpensive diagnostic is also fitted: a context-only logistic model with
the same 619-input storage shape but candidate-action and predicted-terminal
columns zeroed. It has 397 active context coordinates (current/goal/state/time),
398 effective parameters, and 620 stored parameters. It must predict exactly the
same score for all candidates in a bank. Its within-bank ties use the lowest
original sampled index. Context calibration can improve without any candidate
discrimination; report this explicitly. It is not a fifth closed-loop arm.

All trainable models: weighted binary cross-entropy on the two individual success
draws, 40 epochs, AdamW lr=3e-4, weight decay=1e-4, batch 256, gradient norm cap 1.
Hierarchical weights give equal reference, horizon, available anchor, sampled
candidate and tail draw mass. No class balancing that silently changes probability
meaning; no validation fitting, hyperparameter sweep, early stopping or post-hoc
calibration. Frozen components remain detached/eval/no-grad. Training initially
on CPU, with an isolated training RNG. Optimizer synthetic tests are not training
on any research data.

After the **complete training collection**, require at least 100 positive and
100 negative branch labels and positives on at least 20 distinct training
references. These are practical minimums, not a guarantee of learnability. If
not met, return `insufficient_success_support`; stop with the sparse-success
distribution and constant predictor. Do not expand data, oversample a new success
source, change labels to distance or silently launch a new objective. First pilot
stage below checks technical throughput only; it cannot trigger a label-driven
change of sampling or premature sparse-success stop.

## 5. Validation, progression and closed-loop study

Train/freeze all five fits (three MLP seeds, logistic, context diagnostic) before
opening validation labels. Validate within
the sampled-eight bank on the 32 source-disjoint references. Use the same two tail
draws to evaluate chosen-candidate empirical success for all selectors. Report:

- Paired selected-success difference vs continuation (primary development
  contrast), vs immediate and logistic; uniform sampled-eight baseline.
- Pairwise concordance on candidate pairs with different empirical success,
  tie rate and informative-bank/source counts. An all-tied bank has undefined
  concordance, not perfect rank correlation.
- Observed within-bank candidate-success values/variance; learned selection
  outcomes and differences versus the context-only diagnostic on the labelled
  eight only. No outcomes are inferred for the other 56 indices.
- Brier score and log loss vs train-only constant; calibration bins fixed at
  [0,.2,.4,.6,.8,1], with counts; sampled empirical max/regret explicitly qualified.
- H/anchor-specific effects and coverage. Reduce anchors equally within H then
  horizons equally within reference; report live-anchor denominators. Bootstrap
  whole references (10,000 draws, fixed namespace seed), never individual rows.

One fixed progression rule: complete integrity/lifecycle gates; adequate training
support; validation has informative banks on >=10 references; MLP selected-success
point difference is **positive vs continuation**; mean within-bank concordance,
averaged over informative anchors/H/references, is **greater than 0.5**. Brier,
log loss and calibration are supplementary, not advancement gates. This completion
revision explicitly replaces the preparation's Brier gate with discrimination;
no new outcomes were consulted. The rule asks for candidate-level promise beyond
ties/chance as well as useful selection on the sampled subset. No claim of
significance is required. If it fails, preserve the result and stop before
closed-loop; do not pick another model seed, mix scores or open its references.
Logistic is a complexity control, not a fallback selected by validation. A
logistic tie/win limits the need for the MLP, not evidence for diffusion novelty.

If this rule passes, execute a prospectively fixed 32-reference closed-loop
development set, both horizons equally weighted, two episode planner seeds
`seed('closed-loop',reference,H,draw)` shared across arms, four arms:

1. Original continuation (unchanged).
2. Immediate selector **over the same first64 bank**, not historical greedy300.
3. Frozen MLP ensemble argmax success probability.
4. Frozen logistic argmax probability.

This is **32×2×2×4=512 episodes**, at most 115,200 delivered primitive actions.
The three neural training seeds are a fixed probability ensemble in one arm,
not three separate closed-loop evaluations. Two evaluation draws are fresh
episode planner streams coupled across arms, not neural seeds or exact repeats.
There are zero additional exact-repeat episodes and no best-seed selection.
Each learned/control selector replans every 15 actions from its own actual state
until native termination or budget 2H. No single-anchor-only intervention here.
All arms run the identical original bank generation. Learned argmax ties use the
lowest original candidate index, not a tuned continuation blend. Invalid learned
scores fail rather than silently reverting to another policy. Fresh policy,
solver, cache, buffers and RNG per episode; a second episode after a completed
one must behave as an independently created episode.
At local delta=15, including each cycle-final chunk, the unchanged solver emits
its first-only 64-bank; the learned selector still scores that bank. At H the
original schedule restarts, but absolute t and remaining budget `2H-t` continue.
Inputs are each arm's actual current observation/state, never another arm's or
the original reference's future state. No legacy evaluator follows fresh reset.

Primary report: source-level paired native-success difference MLP minus original
continuation, equal horizons and two RNG draws; descriptive reference-bootstrap
95% interval. Immediate/logistic comparisons and H strata are secondary. Report
all arms, failure rates, steps, solver time, value-score time and total allocation,
not only a favorable subset. These are development estimates, not multiplicity-
adjusted confirmation claims or evidence of +5-point sensitivity. Report
off-prefix state/feature ranges, candidate-score saturation and arm divergence;
do not respond by online relabeling or retraining. Full-64 maximization can exploit
value error. This is precisely why within-bank success is insufficient.

## 6. Stages and failure handling

No stage is authorized by this preparation. After explicit approval:

0. Export the implemented dependency closure with `package_candidate_value.py`;
   generate/verify the source/runtime/input capsule and obtain explicit approval
   bound to its hashes and this protocol before any new outcome. The worker,
   staged dispatcher, serializers, CPU fitting/analysis and SSD backup companion
   are implemented; see [IMPLEMENTATION.md](IMPLEMENTATION.md) and
   [EXECUTION.md](EXECUTION.md). Verify source identity/pinned bytes without
   opening protected reference payloads.
   Run at most two five-minute synthetic A6000 contract preflights, no new episodes.
1. First four training references (allocation order), both horizons: eight of the
   256 fixed collection jobs, not extra pilot references. Inspect technical
   invariants and resource counts only. Required full-job projections <=600s,
   <=16GiB sampled host RSS and <16GB projected collection payload (80% of the
   20GB global cap, retaining room for other stages); if exceeded,
   stop as resource-infeasible without changing settings. Never gate on success.
2. Complete remaining training jobs; authenticate seals and apply sparse gate.
   Fit the five fixed models on train labels only, freeze weights and receipts.
3. Complete the 64 validation collection jobs, authenticate seals, read aggregate
   validation once, apply the fixed progression rule. No architecture/label change.
4. If eligible, complete 32 closed-loop jobs and sealed analysis. Report all
   reference effects and costs. No automatic larger study or confirmation.

Infrastructure interruptions: preserve partial artifacts, classify using exact
technical logs, leave outcomes censored; **no automatic retry in this envelope**.
An exact retry requires explicit authorization and all consumed resources remain
charged. Scientific/planner failures are not retried to obtain success. Evaluator
defects invalidate affected scientific claims, preserve the source and outputs,
and require a separately reviewed correction; never quietly patch a running
snapshot. No mid-grid performance peeking outside the specified stage gates.
Sealed technical validity is a prerequisite, not scientific promise. A valid
but scientifically unpromising validation result is final for this envelope.
The exact registered maximum is 293 jobs: 290 GPU + three CPU; dispatch is
serial and stage-gated, not an automatically released all-stage array.

## 7. Matched GMM path (outside this launch envelope)

The hook is proposer-agnostic and observes the same existing solver interface.
The scientific question is a **proposer × evaluator** interaction, not merely
whether a new diffusion arm beats an older GMM arm with less training data.

First propose a zero-shot transfer check: apply this same frozen evaluator to
the existing `direct_gmm_continuation` checkpoint-seed 7201 first64 proposals,
pinning its original bytes and training provenance, without giving either family
new labels. Compare
continuation vs learned scoring within each family on the same source-disjoint
development refs, H, budgets and RNG scopes. Equal data means exactly the same
evaluator artifact for both. GMM distribution shift and the VAD-tail label target
limit this check: a negative GMM result would not establish diffusion superiority.

For a stronger later mechanism experiment, preregister a **balanced pooled label
set** at fixed total cost: same training sources/anchors, equal numbers of VAD
and GMM candidate chunks, common downstream original VAD continuation and budget
for both families. The target then measures candidate quality under the same tail
policy. Train one shared evaluator on the pooled set and give both deployment
proposers identical access to it. Neither arm gets additional family-specific
examples or tuning. Evaluate the 2×2 proposer/scorer factorial and report
`(learned−continuation)_VAD − (learned−continuation)_GMM`, source-paired.
Because each family's original continuation scorer includes its own second
proposal distribution, describe that baseline interaction honestly; also report
same-evaluator VAD vs GMM as the matched learned-selector contrast. Do not pool
unlabelled GMM rows as negative examples. New balanced labels, GMM validation and
all executions require their own approved envelope; none is included now.

## Contribution and limits

[RELATED-WORK.md](RELATED-WORK.md) reviews value-guided diffusion selection,
fixed-horizon value-augmented model-based planning and learned terminal values.
Known ingredients include almost this entire recipe. The proposed contribution
to test is **policy-/remaining-budget-matched native-success evaluation of
15-action proposals in this frozen diffusion/LeWM stack**, with source-disjoint
validation and explicit separation of evaluator and proposal-family effects.
It is not a novelty claim for diffusion plus value. No new scientific result,
confirmation access or claim that the historical paper discrepancy is resolved.
