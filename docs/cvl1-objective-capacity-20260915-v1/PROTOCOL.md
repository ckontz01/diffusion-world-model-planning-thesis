# CVL-1 objective × capacity v1 — frozen execution contract

Authorized new CPU-only study, 15 September 2026. Accepted CVL-1 result
`36d953e5cf366965564cc09b2e8c9a33d407550a` (`stop_no_ranking_promise`) and
diagnosis `ea31f4447f7014778d980695768c8a3afd02ce6b` remain unchanged.
This is outcome-informed method development, not a historical amendment or
confirmation. No downstream launch is authorized by this study's result.

## 1. Fixed four-way comparison

| Configuration | Architecture | Objective | Parameters |
|---|---|---|---:|
| original_bce | 619→128→64→1, ReLU | absolute binary success BCE | 87,681 |
| compact_bce | 619→32→1, ReLU | absolute binary success BCE | 19,873 |
| original_relative | original | paired difference squared error | 87,681 |
| compact_relative | compact | paired difference squared error | 19,873 |

All retain seeds 8201/8202/8203, AdamW learning rate 0.0003, weight decay 0.0001,
40 epochs, minibatch 256, global gradient norm clip 1, float32 CPU arithmetic,
original isolated Torch initialization and training-order RNG namespace. No
early stopping, seed selection, threshold/feature/loss-weight search. Final-layer
bias cancels in the relative objective; it remains in the unchanged architecture
and optimizer. No newly imposed sparse-success pass/fail gate: all designated
fits run with their observed binary labels unless a technical/resource fault stops
the allocation. No target substitutions or data expansion are permitted.

For bank baseline b, relative target for candidate i and draw d is
`y[i,d] − y[b,d]`; prediction is `f(x[i]) − f(x[b])`. SAME bank and SAME draw
pairing is required. Exclude only i=b: each available bank contributes seven
candidates × two draws, including every zero difference. Loss weights are equal
source reference → horizon → available anchor → seven alternatives → two draws;
BCE uses eight candidates instead. Repeated baseline use does not increase the
number of independent sources. BCE consumes 16 rows/bank, relative 14 rows/bank.
Minibatches use the original `(row_loss * hierarchical_weight * total_rows).mean()`
estimator, without replacement per epoch. Normalization for BOTH objectives uses
all eight candidates and both draws with original hierarchical weights, fit on
the fitting references only, so objective does not also change the input scaler.

New BCE ensembles average three sigmoid probabilities; relative ensembles average
three baseline-subtracted raw scores. Each relative baseline is exactly zero.
Relative values are neither probabilities nor confidence bounds. All new seed
and ensemble selectors retain continuation when it is among the exact maxima;
otherwise select a maximum by lowest original candidate index. No epsilon.

## 2. Source-disjoint fitting and validation barrier

Only the accepted 96 TRAIN and 32 ranking-validation references and their saved
labelled-eight banks are used. No source-record/trajectory payloads, reserved 32
closed-loop references or 1600–5999 payloads. Existing accepted seals and JSON/NPZ
readers authenticate consumed features/labels; do not rerun the completed physics
audit. Frozen proposer normalization is already embedded in saved x and unchanged.

Four identifier-only folds: sort the 96 original TRAIN IDs by SHA-256 of the UTF-8
string `cvl1-objective-capacity-20260915-v1|fold|<reference>`, secondary numeric ID,
then take consecutive blocks of 24. Each of the four folds fits 72, holds out 24;
all horizons/anchors/candidates/draws of a reference stay together. Fold ID mapping
is written before loading labels. Each fold's evaluator scaler uses ONLY its 72
fitting refs, weighted original float64 mean/variance, original <1e-6 scale→1 rule,
stored float32. No original all-96 scaler is reused for a new fold.

4 configurations × 3 seeds × 4 folds = 48 fits. Then 4 × 3 on all 96 = 12 fits;
exactly 60 if execution completes. Fit order: folds 0,1,2,3,full; within each,
original_bce, compact_bce, original_relative, compact_relative; seeds ascending.
Full fits use the same fixed choices regardless of cross-fit results. No best seed.

Before reading ANY new validation report/bank: seal all full models/scaler, all
cross-fit results, full-data training reports, fit ledger, protocol/source identity
and training-fold recommendation in PRE-VALIDATION-FREEZE.json. Recheck those seals
before the validation reader runs. Validation is then evaluated once as the entire
fixed comparison; no model/normalizer/threshold/checkpoint decision follows that
read. Existing validation is exposed development, not fresh confirmation.

Training-fold recommendation: rank the four fixed ensemble configurations by
pooled source-held-out hierarchical selected-success difference versus continuation.
If the maximum is not positive, recommend no learned model and retain continuation.
Otherwise nominate the largest difference for later review only. Exact ties prefer
compact_bce, compact_relative, original_bce, original_relative, in that order
(compact first, then BCE). This is a predeclared training-only recommendation rule,
not a new CVL-1 gate or permission for a downstream experiment. Report all four
regardless of recommendation and preserve the nomination after validation.

## 3. Fixed reporting

Primary: two-draw empirical success of the selected candidate minus continuation
on the SAME labelled-eight bank. Equal reference, equal horizon within reference,
equal available anchor within horizon. Unavailable terminal anchors stay absent,
not failures; list them. Equal two-draw mass. Never infer values for the 56
unlabelled candidates, claim a sampled maximum is optimal, or use row/seed/fold
counts as independent source sample sizes. We do not compute an oracle endpoint.

Separate source-held-out cross-fit results, full-data in-sample TRAIN results and
once-frozen development VALIDATION results. All four ensembles, every fixed seed,
historical three MLPs/original ensemble/logistic/context/constant, continuation,
immediate and uniform labelled-eight expectation are reported. Historical learned
controls retain original all-96 scalers/models and LOWEST ORIGINAL INDEX ties;
their numbers on cross-fit references remain IN-SAMPLE historical controls, not
out-of-fold estimates. The new tie rule is not retroactively applied to them.

Every reference and bank: effect, selected/baseline empirical success, gained and
lost binary-draw mass, departure, selected index, predicted score advantage;
gain minus loss equals the empirical effect. Preserve candidate scores and both
outcomes. Report pairwise concordance on unequal two-draw means (score ties 0.5),
informative-pair/bank counts, exact maximum ties, baseline-at-maximum, score min/max,
range/std, top-two gap; new ensemble seed winner disagreement and score dispersion.
Concordance aggregates are conditional on defined banks, as in the original.

BCE/historical probability models only: binary-draw Brier and log loss and fixed
five bins [0,.2,.4,.6,.8,1]; hierarchical bin sums before dividing by bin mass.
No probability calibration or probability loss for relative or distance scores.
Uniform is expected success over the sampled eight, not an actual chosen action.

Objective contrasts: relative−BCE at each capacity. Capacity contrasts:
compact−original within each objective. Interaction = objective_compact minus
objective_original. Report all four folds separately, pooled cross-fit and full
TRAIN/VALIDATION; folds share fitting data and are not independent replications.
Report all seed results without selecting one. Descriptive whole-reference
percentile bootstrap intervals use the original fixed 10,000-resample function;
no post-selection/confirmatory coverage or significance claims.

## 4. Resource reservations, packaging and preservation

ONE CPU Slurm allocation, 4 CPUs, 8GiB, 02:00:00 hard limit, zero GPUs, no retries.
Reserve 100 seconds for EACH of the 60 fits (6,000s), plus 1,100s total worker
setup/scaling/inference/reporting/authentication/writes and 100s batch startup/exit
margin: 7,200 allocated wall seconds maximum (8 allocated core-hours). All failed
work counts. Every fit has a hard 100s timer; unused fit seconds do not allow a
fit to exceed its own cap. Before each fit, release spent reservations, charge
actual fit and overhead time, and require all remaining reservations to fit.
Stop rather than alter cases, retry, enlarge budgets or silently omit fits.
The global and overhead timers also apply during analysis. No GPU device exposure
or Apptainer --nv; thread limits 4, interop 1. The historical root is mounted read-only,
only the new output directory is writable. No simulator imports or controller call.

The new artifacts cap is decimal 1,000,000,000 bytes: models, normalizers,
predictions, reports, source/logs/accounting. Exclusive writes reserve bytes before
writing, maximum 980MB for worker output, 20MB retained for source/log/accounting;
per-file shell limit 64MiB. Expected <150MB; no full original dataset copy. Preserve
all 60 model files, source/folds/protocol, per-fit times and optimizer counts,
predictions/bank/reference metrics, pre-validation freeze, consumed-file hashes,
final output hashes and Slurm accounting. Back up source and the new terminal
run to D:/THESIS-BACKUPS/cvl1-objective-capacity-20260915-v1 on external THESIS_SSD;
verify archive hash and every new sealed member, not a new physical-data audit.

Focused synthetic tests before commit/push and one launch. Commit all design and
reporting choices; verify remote commit hash; export only this source, tests,
wrapper and protocol. Reversible CRLF→LF export normalization is transport only,
recorded in the source manifest. No original file is overwritten. Preserve E12
drafts. Deliver one report and one evidence-supported next recommendation; no
new architecture, label collection, policy or downstream experiment automatically.
