# CVL-BP1: Source breadth versus continuation-label precision

Status: executable preparation, **not authorized for real execution**. Prepared
15 September 2026. The accepted objective × capacity result is
`442c9659a8f8f99e81e492cb9258488b60e12666`. Continuation remains the working
diffusion baseline. `original_relative` remains the recorded training-only
nominee; this study neither promotes it nor substitutes a validation favorite.
CVL-1's `stop_no_ranking_promise`, historical outputs and E12 drafts are unchanged.

## 1. Question and fixed conditions

Does spending a nominally matched increment of continuation-outcome collection
on more source contexts or more tail draws yield more useful **within-bank
candidate selection**, under fixed original model capacity and optimizer-update
budgets? This is one development experiment, not confirmation or closed loop.

| Condition | Training sources | Tail draws per candidate | Collection change |
|---|---:|---:|---|
| A | Original 96 | Original 2 | Reuse accepted saved data |
| B | Original 96 + new 96 | 2 | Collect only the new 96 |
| C | Original 96 | 4 | Reuse the original 2; collect draws 2 and 3 on exactly the original banks |

Each condition has original-capacity absolute BCE and baseline-relative squared
error, seeds 8201/8202/8203, and the original three-seed ensemble definition:
mean sigmoid probability for BCE; mean baseline-centered score for relative.
That is **6 ensembles / 18 fits**, not 18 independently selected methods. No new
width, loss, feature, threshold, early stopping, seed selection, or model selection.
All six are evaluated on the same new evaluation sources. Old development
validation is not read by the new pipeline or used to select a configuration.

## 2. Source roles and exposure boundary

`DATA-ROLES.json` is the exact identifier-only manifest. Its allocation is
recomputed by `breadth_precision_contract.allocation()`:

1. Start with exposed integer indices 0–1599. Use the accepted lexical
   `identity_projection` reader; authenticate the original input lock and registry.
2. Exclude the union of the prior 32 bottleneck/single-anchor references and
   CVL's 96 train + 32 ranking-validation + 32 reserved closed-loop references.
   The later objective/capacity and diagnosis studies reused these roles; they
   did not add source allocations. The historical 32 are a single shared set,
   not counted twice. This excludes **192**, leaving **1,408**.
3. Sort eligible indices by SHA-256 of UTF-8
   `candidate-value-breadth-precision-20260915|source-allocation|<index>`, then index.
   Assign first 96 to additional training; next 32 to new model-held-out
   development evaluation. **1,280 remain unallocated by this lineage.**
4. The metadata projection established 1,600 unique `namespace:attempt` source
   keys. The 224 permitted original/new/evaluation records have disjoint roles.
   No outcome-based inclusion, replacements, candidate-row splitting, or
   reallocation after observing availability/outcomes is allowed.

First new train indices: 333, 894, 1125, 387. First new evaluation indices:
949, 977, 800, 1206. Full role membership and each permitted payload's recorded
path/hash/environment seed are in the manifest. Reading this identity metadata
did not open a source NPZ or decode registry performance fields. Reserved CVL
closed-loop payloads and all 1600–5999 payloads remain unopened.

"Model-held-out" means excluded from this evaluator's fitting and preprocessing;
it does not claim these exposed development sources form a fresh confirmation
holdout or establish absence from every historical proposer's training history.
The unit is a complete registered source reference, with all horizons, anchors,
candidates and draws kept together. Distinct registered source keys are not a
claim of independence between every possible similar physical state.

## 3. Frozen physical, proposal and sampling contract

Reuse the accepted CVL backend/source closure, proposer, adapter, LeWM,
fresh-state initializer, decoder, physical-success predicate and downstream
continuation. H75/H150 are equally weighted. Total primitive-action budget is
2H; the intervention executes one 15-action candidate chunk, then unchanged
continuation through the **original remaining budget**, with original early
native termination. Success during the candidate chunk counts. Zero means no
native success within this policy/budget, not irrecoverability.

Anchor slots remain `0, 30, H, 2H−15`. Prefixes follow unchanged continuation.
Terminal prefixes make subsequent anchors unavailable, not negative. Preserve
each original C availability entry; no attempt to make a missing bank available.
For new sources the same rule applies. Do not discard a source because of its
success, disagreement, or anchor count. An unexpected nonterminal missing bank
is a technical fault, not a new sample-selection rule.

Each complete bank has 64 candidate indices. The eight-index sampling rule is
the original one: include continuation's minimum-cost index and immediate's
minimum-cost index, de-duplicate their **indices**, then fill 6 or 7 slots from
remaining indices sorted by the original `candidate-sampling` SHA namespace.
Lowest original index resolves equal minimum costs. This includes nonwinners.
Identical action chunks at different indices are not silently deduplicated;
record original action collisions and coverage using the accepted helper.
Index coverage is 8/64, not an exhaustive action-space oracle. No outcomes for
the unlabelled 56 indices are inferred.

### C bank identity

Read accepted original training report/bank/prefix members through their existing
seals. Do not generate a replacement standalone prefix or new proposal bank for
C. Each branch still replays the required original prefix using the original
prefix and environment seeds; exact prefix actions/state/dynamics/flags and
initial observation must match. At the intervention, require equality of every
saved bank field, including features, action tensors, costs, pixels, physical
state and post-proposal RNG state. Reuse the original eight sampled indices and
coverage record. If replay does not reproduce the saved bank, **stop**; never
substitute the newly obtained proposals. The new C artifact references the old
bank hashes instead of overwriting or duplicating the old banks.

## 4. Tail streams, labels and weighting

For each `(source,H,anchor)`, original draws 0/1 use the exact accepted seeds
`candidate_value_contract.tail_seeds`. Draw 2 is `(seed0 XOR 2^30) OR 2^61`;
draw 3 is `(seed1 XOR 2^30) OR 2^61`. Original seeds are below 2^61. The high
domain bit separates the integers, and the low-bit change also separates RNGs
that use only the low 32 seed bits. This rule is fixed without observing outcomes.

Both proposal and GMM RNGs are reseeded at the accepted tail handoff, after the
intervention bank is generated/selected. All candidates within a bank share the
same seed for a given draw. Different draws must have distinct recorded RNG
states; C's new states must also differ from both saved original states. There
is no reference-, candidate-, or outcome-specific stream search. Synthetic CPU
RNG-output distinction is tested; actual recorded runtime RNG states are checked
inside collection, not by an extra GPU diagnostic allocation.

Store **each binary outcome**, not a rounded majority. A/B use both draws with
equal weight; C and common evaluation use all four with equal weight. Features
remain inference-available and unchanged. The relative objective uses each
candidate-minus-continuation binary difference on the **same coupled draw**,
excluding only the continuation self-pair and retaining zero differences.

Hierarchical weights are equal source, equal H, equal available anchor, equal
sampled index (7 alternatives for relative training; 8 for BCE), equal draw.
Extra draws do not increase a source's total weight. No positive resampling or
distance-target replacement. Sparse or zero-success banks remain in the data.

At `2H−15` there is no stochastic continuation after the candidate chunk.
Repeated labels at this slot must agree; preserve them for the fixed tensor
layout/weighting but report them as repeated deterministic outcomes, **not
additional independent evidence**. The original 157 available final-budget
banks imply 2,512 such new C outcome records. Earlier successes can also remove
tail execution; report actual steps and native termination from saved traces.

## 5. Fixed preprocessing, losses and matched updates

Use one common **accepted original-96 training-only normalizer**, authenticated
through the old fit seal, for every condition/objective/seed. Do not refit it on
B or C: this holds the feature coordinates fixed and isolates data allocation
from preprocessing changes. No new evaluation or old validation coefficient
fitting. The frozen diffusion planner's checkpoint normalization is unchanged.

Model: unchanged 619→128→64→1 MLP, 87,681 parameters. AdamW lr 3e−4,
weight decay 1e−4, gradient norm clip 1, original batch size 256 and original
seeded permutation/minibatch ordering. BCE is weighted binary cross-entropy
with logits. Relative is weighted squared error of
`f(candidate) − f(continuation)` against the saved draw-level outcome difference.
Relative scores are not probabilities; do not compute a probability calibration
claim from them.

| Objective | Updates per fit for A/B/C | Origin of fixed count |
|---|---:|---|
| BCE | **1,800** | Original A's 11,344 rows: 40 × ceil(11,344/256) |
| Relative | **1,560** | Original A's 9,926 paired rows: 40 × ceil(9,926/256) |

Cycle through seeded shuffled rows, retain the original short final minibatch,
and stop exactly at the update count. A thus retains its 40-epoch update count;
B/C do **not** receive 40 full epochs. Log actual row presentations and partial
passes. Matched updates are not a claim of exactly matched example exposure or
CPU seconds: short batches and data size differ. No checkpoint selection: use
the final fixed-update weights. **30,240 total optimizer updates /18 fits.**

## 6. Stage order and outcome barrier

The exact ordered execution grid is generated by `grid()`:

1. First four new-training sources ×2H (8 breadth jobs), then first four original
   sources ×2H (8 precision jobs). These **16 included jobs**, not extra data,
   provide technical throughput/storage/RSS checks only. No scientific gate.
2. Remaining 184 breadth and184 precision jobs. No model training before both
   training components are complete and sealed/backed up.
3. One CPU allocation fits all18 fixed models, records in-sample training
   diagnostics, and seals all model weights, normalization and fit receipts in
   `PRE-EVALUATION-FREEZE.json`. No new evaluation payload/outcome is used here.
4. Verify/backup that complete model freeze, **then** collect the32 common
   evaluation sources ×2H with four draws (64 jobs). This is stricter than only
   prohibiting reading the outcomes: collection itself waits for the freeze.
5. Verify all evaluation seals, back up the data, then run one CPU analyzer.
   Report all fixed configurations, not a chosen winner. Seal/back up the final
   report, predictions, source-level rows and actual-resource ledger. Stop.

During collection dispatch reads only authenticated technical scalar metadata,
scheduler status, byte counts and checksums. No inspection of partial empirical
effects. Training can consume the completed training data; the analysis consumes
the new evaluation only after the full model freeze and all64 jobs complete.
There are no automatic scientific follow-ups, closed-loop jobs, or additional
training modes in this dispatcher. Failures preserve partial outputs, cancel a
known active allocation, and stop. No automatic retry, revised seed/case,
sample-size adjustment, or cap increase. Unknown submission status requires
human reconciliation before any further action.

## 7. Analysis fixed before new outcomes

Primary outcome for a selector/bank is the mean of its four empirical binary
successes minus continuation's mean **on those same draws and sampled indices**.
Reduce equally over live anchors, then both H, then all32 sources. Report all
six ensembles and all32 reference-level effects, plus fixed continuation,
immediate and uniform-sampled-eight controls. Individual neural seeds are
diagnostic rows, not alternative model nominations. For learned-score ties,
retain continuation if tied at maximum; otherwise use lowest original index,
as in the accepted objective/capacity implementation. Original distance controls
retain their own original-index tie rule. No threshold sweep or favorable subset.

Report, separately within BCE and relative: **B−A, C−A and B−C**, including
paired per-source effects. The first two compare each collection investment to
the unchanged allocation; the third compares the two nominal investments.
Use the accepted fixed-seed 10,000 whole-source bootstrap percentile intervals
as descriptive uncertainty, both versus continuation and for paired allocation
contrasts. These are not multiplicity-adjusted confirmatory claims, tests or
retroactive promotion gates. No automatic "best" method recommendation from
significance or the largest evaluation mean.

Secondary reports: in-sample training fit; conditional within-bank concordance
(undefined when empirical candidate values are all equal); pair counts and
available-bank denominators; departure/gain/loss; score range/std/top gaps/ties;
fixed-model disagreement; BCE Brier/log loss/calibration; reference/H/anchor
strata and final-budget/no-tail accounting. Keep probabilities, relative scores
and four-draw empirical outcomes distinct. Store bank predictions so every
aggregate is traceable. Neither empirical best-of-eight values nor four draws
establish true optimal candidate values.

## 8. What this can and cannot distinguish

It can estimate whether, for this frozen sampler, continuation label policy,
capacity, update budget and exposed development distribution, **new source
contexts** or **more coupled tail samples on the same contexts/candidates**
produce better learned within-bank choices. Keeping C banks unchanged directly
avoids confusing label precision with changed proposals. The shared evaluation
draws isolate differences in which indices the fixed models select.

It cannot prove more data is the remedy, identify a universal scaling law, or
separate every type of generalization error. B varies context and candidate
coverage; C changes Monte Carlo target precision but not candidate coverage.
There is no fourth condition with both breadth and precision, so their
interaction is not identified. Nominal new-outcome ceilings are matched for B/C,
not actual labels, physical steps or GPU costs; missing anchors and deterministic
final slots matter. Four evaluation draws are noisy estimates, not ground truth.
Fixed updates may under-use extra data; that is part of this cost-controlled
question, not an optimization search. This is not closed-loop policy efficacy,
fresh confirmation, historical SAGE fidelity, or evidence about GMM versus
diffusion proposal quality. Data scaling itself is not a claimed novel method.

## 9. Execution proposal and approval

Recommend **this one fixed 96/96/32 design**, with the envelope in
`RESOURCE-PLAN.md`: 86 A6000 allocation-hours, two4-CPU allocation-hours,
10 GB new remote bytes, and40 GB external-SSD free-space reserve. It has a
clear matched nominal training collection budget and a common held-out-model
development test. Approval of this preparation is **not launch approval**.
`IMPLEMENTATION.md` gives source-only packaging and the guarded future commands.
No real labels, evaluator fits, planner/world-model/physics calls or GPU jobs
were executed to prepare it.
