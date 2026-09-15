# CVL-1 bounded learning diagnosis — completed 15 September 2026

**Conclusion:** the fixed MLPs fit the training candidate outcomes strongly but
generalized poorly to source-disjoint validation. On validation the ensemble
frequently departed from continuation with positive predicted advantage, yet
lost more outcomes than it gained. Two-draw cross-selection did not demonstrate
a stable advantage over continuation on the other saved draw. These findings
motivate, but do not validate, a later baseline-relative ranking objective.

The original decision **`stop_no_ranking_promise`** and all CVL-1 endpoints,
models, outputs and advancement rules remain unchanged. No closed-loop job,
optimizer step, replacement model, new label, simulator or world-model inference
was run. This is the one requested diagnosis, not a new efficacy experiment.

## 1. What was evaluated

The [pre-execution analysis contract](PROTOCOL.md) and tested implementation were
published at `f7ca86db1cd5aceeb1b07b237aa68c980e93760a`, following accepted CVL-1
result `36d953e5cf366965564cc09b2e8c9a33d407550a`. Only existing saved feature
matrices, labels and frozen evaluator artifacts were consumed. Accepted seals
and the existing JSON/NPZ/Predictor readers were used; collection reconstruction,
LeWM, diffusion, adapter and physics were not rerun.

|Population|References|Live banks|Unavailable anchors|Candidates × two saved draws|
|---|---:|---:|---:|---:|
|Training, **in-sample**|96|709|59|5,672 × 2|
|Ranking validation, source-disjoint|32|242|14|1,936 × 2|

All results use equal reference → horizon → available-anchor weights; candidate
and draw means are equally weighted within a bank. Conditional concordance uses
only informative banks/horizons/references, as in CVL-1: 251 banks/87 references
in training, 70 banks/27 references in validation. The remaining 458/172 banks
have tied empirical candidate values, not perfect concordance. Subgroup means
renormalize the same hierarchy within the declared stratum and are not averaged
back naively to recover the overall mean.

The labelled set is the original eight indices (including nonwinners) from each
64-bank. No outcomes were inferred for the other 56. All exact argmax ties use
lowest **original** candidate index. Context and constant scores tie across all
eight candidates; their deterministic selection is not uniform random selection.

## 2. Unchanged fixed models and controls

Selected success and effect are percentages/percentage points; concordance is
conditional on informative pairs. They concern candidate execution followed by
the original continuation tail, **not repeated learned-selector closed loop**.

|Scorer|Train selected %|Train Δ vs continuation (pp)|Train concordance|Validation selected %|Validation Δ (pp)|Validation concordance|
|---|---:|---:|---:|---:|---:|---:|
|MLP 8201|29.1233|+12.5868|0.9018|8.4635|−3.4505|0.5577|
|MLP 8202|29.1667|+12.6302|0.9015|8.8542|−3.0599|0.5320|
|MLP 8203|29.1884|+12.6519|0.9025|8.7891|−3.1250|0.5530|
|**Original ensemble**|**29.2535**|**+12.7170**|**0.9057**|**8.8542**|**−3.0599**|**0.5612**|
|Logistic|16.2326|−0.3038|0.5292|9.6354|−2.2786|0.5755|
|Context-only|14.8220|−1.7144|0.5000|9.6354|−2.2786|0.5000|
|Training constant, index ties|14.8220|−1.7144|0.5000|9.6354|−2.2786|0.5000|
|Continuation|16.5365|0|0.5374|11.9141|0|0.5018|
|Immediate|16.3845|−0.1519|0.4987|11.3932|−0.5208|0.4849|
|Uniform over sampled eight|15.5979|−0.9386|Not a scorer|10.3271|−1.5869|Not a scorer|

The ensemble exactly reproduces the accepted validation effect up to floating-
point reduction roundoff. Individual seeds are diagnostics, not eligible
substitutes. No individual seed has a positive validation effect. Logistic has
slightly higher validation concordance than the ensemble but still loses on
selected outcomes: pairwise concordance alone is not a top-choice criterion.

### Probability error, not distance-score error

Brier and log loss use both original binary draws, not a majority label. The
training constant remains 0.1559787393, never refitted on validation.

|Probability model|Train Brier|Train log loss|Validation Brier|Validation log loss|
|---|---:|---:|---:|---:|
|MLP 8201|0.044110|0.141712|0.114761|0.500914|
|MLP 8202|0.043653|0.138460|0.110527|0.499666|
|MLP 8203|0.044465|0.141070|0.111170|0.485502|
|Original ensemble|0.042086|0.135525|0.108904|0.471554|
|Logistic|0.136335|0.443791|0.154178|0.479336|
|Context-only|0.139665|0.452114|0.154869|0.480999|
|Training constant|0.131649|0.432941|0.095385|0.343947|

The ensemble improves both errors strongly on training but is worse than the
unchanged constant on validation. Continuation/immediate negative costs are
ranking scores, not probabilities; probability error and calibration are
inapplicable. Uniform selection does not supply a fitted probability forecast.

### Score ranges and within-bank variation

Extrema below are raw observed probability extrema over the labelled candidates;
range, standard deviation and top-two gap are hierarchically weighted per-bank
means. These are distinct quantities, not pooled standard deviations.

|Model|Train global min–max|Val global min–max|Train range / SD / gap|Val range / SD / gap|
|---|---|---|---|---|
|MLP 8201|4.20e−9–0.99984|1.21e−7–0.92899|.13811 / .04630 / .03127|.07644 / .02435 / .02313|
|MLP 8202|1.47e−8–0.99974|1.90e−8–0.94299|.13512 / .04547 / .03211|.06886 / .02222 / .02387|
|MLP 8203|5.54e−8–0.99983|9.78e−9–0.96591|.13601 / .04587 / .03176|.07673 / .02476 / .02311|
|Ensemble|2.98e−8–0.99975|5.00e−8–0.93437|.13498 / .04525 / .03147|.07006 / .02245 / .02235|
|Logistic|.05622–.99604|.01997–.88239|.07507 / .02383 / .01588|.08221 / .02646 / .01909|
|Context|.09040–.99057|.04278–.84845|0 / 0 / 0|0 / 0 / 0|
|Constant|.15598–.15598|.15598–.15598|0 / 0 / 0|0 / 0 / 0|

Continuation score extrema were −459.595 to −3.406 train and −411.271 to −4.710
validation; within-bank range/SD/gap were 74.982/24.286/16.381 and
80.773/26.006/17.311. Immediate extrema were −456.490 to −3.406 and −438.238 to
−4.019; range/SD/gap 61.571/19.697/13.693 and 61.588/19.678/15.018. Their cost
units cannot be compared numerically with probability ranges. Uniform has no
candidate score range.

No MLP, ensemble or logistic bank had an exact top-score tie in either split.
Context and constant tied on every bank. Ensemble probability saturation at the
original descriptive cutoffs ≤.01 or ≥.99 covered 57.04% of training candidate
mass and 54.80% validation mass; these cutoffs are not new decision thresholds.

Fixed-bin ensemble calibration illustrates the changed relation between scores
and outcomes. Counts are raw candidate rows; means retain original weights within
each bin. Sparse high-score validation bins are not new efficacy subgroups.

|Bin|Train count|Train mean p / outcome|Val count|Val mean p / outcome|
|---|---:|---|---:|---|
|[0,.2)|4,675|.02018 / .01310|1,719|.02301 / .09553|
|[.2,.4)|341|.29139 / .30596|114|.27967 / .07692|
|[.4,.6)|205|.49887 / .56015|38|.49714 / .19231|
|[.6,.8)|173|.70195 / .76107|36|.70081 / .15385|
|[.8,1]|278|.94083 / .97434|29|.85829 / .38095|

## 3. Two saved continuation draws

Training had 510 disagreements among 5,672 candidate pairs; validation had 146
among 1,936. Raw rates are 8.99% and 7.54%; **hierarchically weighted rates are
10.1237% and 8.2520%**. Positive counts were 684/684 for train draw0/draw1 and
158/148 for validation. Equal aggregate counts do not imply identical labels.

For each candidate, its difference is y(candidate, draw)−y(continuation, same
draw). The saved candidate rows retain each signed difference and the two-draw
mean. Across sampled candidates:

|Split / draw|Gain fraction %|Loss fraction %|Tie fraction %|Mean difference (pp)|
|---|---:|---:|---:|---:|
|Train 0|5.8540|5.3494|88.7967|+0.5046|
|Train 1|4.7418|7.1235|88.1348|−2.3817|
|Validation 0|3.5645|5.5013|90.9342|−1.9368|
|Validation 1|4.2969|5.5339|90.1693|−1.2370|

The ensemble's fixed selections scored 29.6007%/28.9063% on train draws0/1,
versus continuation 15.0174%/18.0556%. On validation they scored
8.9844%/8.7240%, versus continuation 12.6302%/11.1979%: the negative selection
effect is not confined to one draw. Ensemble concordance by binary draw was
.8707/.8800 train and .5644/.5176 validation. Every individual model's per-draw
results are retained in the machine report.

### Fixed cross-draw selection, with no learned model

Choose the maximal binary outcome in the selection draw, breaking all ties by
lowest original index, then evaluate on the other saved draw. Continuation below
is always evaluated on that same evaluation draw.

|Split / select→evaluate|Selection-draw success %|Other-draw success %|Other-draw continuation %|Effect (pp)|Tied maximum %|All-zero selection banks %|
|---|---:|---:|---:|---:|---:|---:|
|Train 0→1|36.2847|19.6615|18.0556|+1.6059|88.1944|63.7153|
|Train 1→0|33.7674|18.7066|15.0174|+3.6892|90.8854|66.2326|
|Validation 0→1|26.5625|10.6771|11.1979|−0.5208|90.6250|73.4375|
|Validation 1→0|26.9531|12.7604|12.6302|+0.1302|89.0625|73.0469|

Mean directional effect is **+2.6476 points train and −0.1953 points validation**.
Mean maximum-tie multiplicities were 6.339/6.553 train and 6.730/6.641 validation.
Raw tied-maximum counts were 622/642 of 709 train and 219/217 of 242 validation;
raw all-zero selection counts 484/502 and 186/186. Weighted and raw rates differ.

This is a descriptive cross-draw check, **not a deployable selector, true oracle,
upper bound, or true candidate-value estimate**. The first draw supplies only one
binary observation; its many ties and fixed index rule do not identify the best
candidate. Near-zero validation transfer does not prove no learnable signal.

### Horizon and anchor strata (all prespecified strata retained)

Δ0/Δ1 are candidate-minus-continuation means over sampled candidates on the
same draw. Cross0/Cross1 are 0→1 and 1→0 effects. All differences are percentage
points; disagreement is a percentage. Each stratum has one bank per available
reference, so banks are its distinct-reference denominator.

|Split|H / anchor|Banks|Disagreement %|Δ0|Δ1|Cross0|Cross1|Ensemble Δ|
|---|---|---:|---:|---:|---:|---:|---:|---:|
|Train|75 / 0|96|20.1823|+5.3385|−0.7813|+3.1250|+7.2917|+23.4375|
|Train|75 / 30|94|13.2979|−3.0585|−5.4521|+4.2553|+3.1915|+15.4255|
|Train|75 / 75|81|7.0988|−0.6173|−6.7901|0|+6.1728|+10.4938|
|Train|75 / 135|70|0|−2.3214|−2.3214|+2.8571|+2.8571|+1.4286|
|Train|150 / 0|96|14.8438|+4.6875|−3.1250|−5.2083|+4.1667|+17.7083|
|Train|150 / 30|96|10.1563|+1.3021|+1.3021|+4.1667|+3.1250|+17.1875|
|Train|150 / 150|89|2.3876|−0.9831|−2.5281|−2.2472|−1.1236|+1.6854|
|Train|150 / 285|87|0|+0.5747|+0.5747|+2.2989|+2.2989|+2.2989|
|Validation|75 / 0|32|15.6250|−2.7344|+3.5156|0|0|+3.1250|
|Validation|75 / 30|32|8.9844|+1.5625|−0.3906|+6.2500|+12.5000|−3.1250|
|Validation|75 / 75|28|0.4464|0|+0.4464|0|0|0|
|Validation|75 / 135|27|0|0|0|0|0|0|
|Validation|150 / 0|32|14.4531|+2.3438|−6.6406|−6.2500|−6.2500|−1.5625|
|Validation|150 / 30|32|14.4531|−8.5938|+2.7344|+3.1250|−6.2500|−6.2500|
|Validation|150 / 150|30|3.3333|+0.4167|−4.5833|−6.6667|0|−3.3333|
|Validation|150 / 285|29|0|0|0|0|0|0|

At final-budget anchors, no stochastic continuation remains after the forced
15-action chunk. All paired outcomes agreed: 157 train banks across 91 references,
56 validation banks across 30 references. **Every candidate in every validation
final-budget bank failed on both saved draws**: eight-way ties, zero candidate
contrast and zero cross-draw effect. This is not evidence of stochastic-tail
repeatability. Some training final-budget candidates differed across indices
despite agreeing across draws; conditional cross effect there was +3.8462 points.
Before the final-budget anchors, weighted draw disagreement was 12.0768% train
and 10.0911% validation; mean cross effect +2.4306 and −0.2604 points. This
distinguishes deterministic-tail-end agreement from earlier stochastic sensitivity.

## 4. Why the ensemble lost relative to continuation

Gain means chosen candidate succeeds and continuation fails on the same draw;
loss is the reverse. Gain−loss equals the selected-success difference under the
original weights, including ties and nondepartures.

|Quantity|Training|Validation|
|---|---:|---:|
|Raw departure banks / all banks|572 / 709|200 / 242|
|Weighted departure frequency|81.2066%|83.2031%|
|Raw gained / lost binary draw outcomes|181 / 14|17 / 24|
|Weighted gain contribution|+13.7370 pp|+3.7760 pp|
|Weighted loss contribution|−1.0200 pp|−6.8359 pp|
|Net empirical advantage|+12.7170 pp|−3.0599 pp|
|Predicted selected-minus-continuation advantage|+6.7863 pp|+3.9187 pp|
|Prediction minus empirical advantage|−5.9307 pp|+6.9786 pp|
|Mean predicted selected probability|22.4816%|11.7850%|
|Mean predicted continuation probability|15.6953%|7.8663%|
|Actual selected outcome|29.2535%|8.8542%|
|Actual continuation outcome|16.5365%|11.9141%|

On validation the scorer both underestimated continuation's outcome and assigned
higher predicted value to choices with lower empirical outcomes. Raw 17−24 is
not divided by a pooled row count to claim −3.06 points; the reference/horizon/
anchor weights account for the actual primary effect.

Conditional on departure (renormalizing the original departure mass), validation
gain/loss/net were +4.5383/−8.2160/−3.6776 points, versus predicted advantage
+4.7098 points. Training conditional net was +15.6601 points. These are
descriptive quantities, not permission to choose a departure threshold.

The validation ensemble's mean probability range was .07006, within-bank SD
.02245, top-two gap .02235, and mean standardized advantage 1.7060 SD units.
Mean seed probability dispersion was .02640 (train .02164). At least two MLPs
chose different winners on **52.6042%** of validation bank mass (train 41.2326%).
Pairwise MLP winner disagreement was 41.1458%, 36.9792%, 40.2344% on validation
(29.2101%, 30.5990%, 29.2535% train). Ensemble-vs-logistic disagreement was
73.9583% validation; ensemble-vs-context 87.1094%. Full pairwise matrices and
score dispersion are saved. Ranking choices are seed-sensitive even though all
three seeds have similarly negative aggregate validation effects.

### Every validation reference

All 32 are included in frozen allocation order. Departure is a percentage;
gain/loss/net are empirical contributions in percentage points; predicted
advantage is a probability difference in points, **not** an observed effect.

|Reference|Departure %|Gain pp|Loss pp|Net pp|Predicted advantage pp|Seed-winner disagreement %|
|---:|---:|---:|---:|---:|---:|---:|
|1036|87.5|0|6.25|−6.25|2.04977|75|
|1162|87.5|0|0|0|0.11937|50|
|1289|87.5|6.25|0|+6.25|4.08586|25|
|573|75|0|0|0|3.02731|62.5|
|39|100|18.75|0|+18.75|7.68986|50|
|702|100|12.5|0|+12.5|7.20821|62.5|
|81|100|6.25|0|+6.25|4.28601|62.5|
|59|75|6.25|0|+6.25|10.94204|0|
|846|87.5|12.5|0|+12.5|5.67472|75|
|264|100|6.25|0|+6.25|9.61128|62.5|
|1223|100|14.58333|14.58333|0|0.04137|58.33333|
|690|100|12.5|37.5|−25|8.79677|62.5|
|1495|87.5|0|0|0|3.46224|37.5|
|161|75|0|0|0|1.04765|50|
|426|87.5|0|0|0|0.94213|62.5|
|217|75|0|0|0|6.50290|50|
|1454|62.5|0|6.25|−6.25|0.57229|50|
|1501|75|0|12.5|−12.5|3.69805|62.5|
|94|87.5|0|0|0|5.79227|25|
|1521|100|12.5|41.66667|−29.16667|2.45459|75|
|588|75|0|6.25|−6.25|0.60963|50|
|861|100|6.25|6.25|0|2.39556|87.5|
|1271|75|0|0|0|0.35132|50|
|1001|62.5|0|12.5|−12.5|0.05458|75|
|26|62.5|0|25|−25|0.97202|62.5|
|907|62.5|0|0|0|4.35448|62.5|
|1416|87.5|6.25|6.25|0|3.03405|12.5|
|436|75|0|37.5|−37.5|2.79758|50|
|591|75|0|0|0|7.27479|37.5|
|77|87.5|0|6.25|−6.25|7.10371|37.5|
|1359|75|0|0|0|7.06585|62.5|
|1034|75|0|0|0|1.37995|37.5|

## 5. Supported, contradicted and unresolved explanations

**Supported by these measurements:**

- A substantial in-sample-to-validation generalization gap. All MLPs exhibit it
  in selection, discrimination and probability error. This is consistent with
  overfitting; it is not proof of one particular overfitting mechanism.
- Poor validation alignment between predicted relative advantage and realized
  paired advantage. Frequent departures lost more weighted outcomes than gained.
- Sparse, tied and draw-sensitive candidate contrasts. Validation cross-draw
  selection does not reproduce its selection-draw advantage on the other draw.
  These measurements weaken interpretation of two-draw empirical maxima as
  recoverable improvement; they do not eliminate the possibility of signal.
- Seed-sensitive candidate ordering. Ensembling reduces some probability error,
  but does not repair the selected-outcome deficit in this fixed study.

**Contradicted as complete explanations:**

- “The MLP could not fit any candidate-level signal”: training concordance .906
  and a +12.72-point in-sample selection effect contradict a total fitting failure.
- “One bad neural seed caused the stop”: all three seeds have negative validation
  effects; no favorable seed is selected.
- “Scores were flat or ties caused learned selection failure”: MLP/ensemble/
  logistic scores vary, with no exact maximum ties. Flat context scores are an
  intentional control, not the behavior of the MLPs.
- “A large sampled empirical maximum proves a transferable opportunity”: the
  fixed cross-draw check does not establish such an opportunity on validation.

**Still unresolved:** true candidate values and their ordering; how much of the
gap arises from limited source diversity, noisy two-draw targets, representation
aliasing or fitting/calibration; whether baseline-relative training would improve
generalization; and any closed-loop consequence. This diagnosis cannot attribute
these mechanisms causally or turn validation strata into independently selected
training cases. It does not reopen initialization, normalization or collection.

## 6. One recommendation, without implementation

If another learning experiment is separately approved, **test a baseline-relative
candidate-ranking objective against the unchanged continuation choice**, using
candidate-minus-continuation outcomes paired within the same bank and draw,
source-disjoint evaluation and the original continuation control. The specific
motivation is the observed mismatch between positive predicted advantages and
negative realized departure outcomes, despite fitting candidate outcomes in-sample.
Do not treat pooled BCE/calibration or raw candidate success as sufficient evidence
of a useful replacement decision.

This is a bounded next hypothesis, not an assumed fix: approximately 90% of
validation candidate-vs-continuation binary comparisons tie, and cross-draw
transfer is near zero. A relative objective could still fit noise, miss rare gains,
or degrade the baseline. No objective, threshold, regularizer, dataset, model,
training run or new pass/fail rule is implemented or approved here. CVL-1 remains
stopped; any later experiment requires its own prospectively approved contract.

## 7. Resources and preserved evidence

One job, **301440 COMPLETED 0:0**, used **20 CPU allocation wall seconds at four
CPUs/8GiB**, i.e. 80 reserved core-seconds, versus the proposed 7,200-second ceiling.
Worker elapsed time was 16.5654s, process CPU time 32.7476s and process maximum RSS
423,424,000 bytes. There were zero GPU allocations, optimizer steps, new labels,
simulator calls and world-model calls. Packaging/transfers are separate small
control operations, not charged as allocated research-job wall time.

Results and original-model/source identities are documented in
[EXECUTION.md](EXECUTION.md). The output seal is
`19ccd6003085e8c2b8aca70555153314fe203b8b05151fee077b9763c01546a7`.
All new numeric JSON, consumed-file provenance, logs and launch receipts are
preserved in the remote separate analysis directory and an external SSD archive:

`D:/THESIS-BACKUPS/cvl1-learning-diagnosis-20260915-v1/result-f7ca86db.tar`

Archive size **15,923,200 bytes**, SHA-256
`7fcd6f3c1fc7a8f76ad87e85f335fc911fee00060452e3dcf4b17de525f730b2`.
Local/remote hashes match and all four sealed result members were verified from
the archive without extraction. The original CVL-1 outputs were not overwritten.
Machine output contains every train and validation reference, scorer, draw,
candidate and declared stratum; no cherry-picked subgroup replaces the report.
No monitor or follow-up experiment was started.
