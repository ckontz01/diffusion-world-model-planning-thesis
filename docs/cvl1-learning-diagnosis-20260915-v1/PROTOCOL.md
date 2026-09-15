# CVL-1 learning diagnosis v1 — fixed CPU analysis

Authorized by the user after accepting result commit
`36d953e5cf366965564cc09b2e8c9a33d407550a`. This is a separate, outcome-informed
learning diagnosis, not an amendment to `stop_no_ranking_promise`. No new gates.

## Scope and execution bound

One CPU-only Slurm job: 4 CPUs, 8GiB, maximum 7,200 allocated wall seconds
(8 reserved core-hours), zero GPUs, no automatic retries or expansion. Use the
existing Python/Apptainer runtime without `--nv`, with CUDA devices hidden.
Only evaluator forward inference is allowed, under inference mode. No optimizer,
LeWM, diffusion, adapter, physics, new labels, source-record payloads, closed-loop
references or controller calls. Fixed train 96 / ranking-validation 32 source
references, both horizons, all available saved anchor banks; no exclusions by
diagnostic result. The original 32 reserved closed sources and 1600–5999 stay closed.

Use accepted stage seals and original JSON/NPZ readers, not a rerun of collection
integrity or simulator reconstruction. Read only collection REPORT.json (labels
and metadata), bank NPZs (saved x and costs), fitted evaluator/normalization files,
accepted seal/backup metadata, and the accepted aggregate result. Authenticate
these consumed files against accepted seals. Do not open prefix/branch traces,
source records, images outside bank files, or historical model checkpoints.
The existing frozen Predictor loads only the five evaluator artifacts.

Outputs are exclusively in a separately named analysis directory. The source
commit and source-package hash are fixed before submission. Retain raw diagnostic
JSON, bank/candidate rows, opened-file provenance, job logs and resource accounting;
back up to D:/THESIS-BACKUPS/cvl1-learning-diagnosis-20260915-v1 on THESIS_SSD.
Expected payload <20MB; hard output file limit 256MiB; no original output overwrite.

## Fixed quantities and weighting

Primary diagnosis is on the labelled eight indices, never inferred outcomes for
the other 56. Original ensemble = mean sigmoid probability of all three unchanged
MLPs (8201, 8202, 8203); each MLP is also reported separately but cannot replace
the ensemble. Logistic, context-only and training-constant probability are fixed.
Continuation/immediate retain original bank-cost ranking; neither is converted
to a success probability. Uniform means expected outcome over the labelled eight.
The training-constant selector uses the same index tie rule and is distinct from
uniform random selection. No refitting or selection of coefficients.

At every argmax (including binary draw selectors), exact ties are broken by
**lowest original candidate index**, not order within the sampled subset.
Continuation/immediate indices are the saved original winners. All means retain
equal reference, equal horizon within reference, equal available anchors within
horizon; candidates and the two draws get equal mass within banks. Conditional
concordance is reduced only over informative banks/horizons/references, matching
the original rule; report denominators. Strata are H75/H150 crossed with fixed
anchor slots 0, 30, H, 2H−15. Training is in-sample, not independent efficacy.

For every fixed scorer, report selected empirical success, difference versus
continuation, pairwise concordance on unequal two-draw mean outcomes (probability
ties count 0.5), concordance by individual draw, Brier/log loss against the binary
draws for probability models, raw score min/max and within-bank range/std/variance,
top-two gap and top-score tie count. Probability calibration uses the original
five bins [0,.2,.4,.6,.8,1]; no fitted calibration or threshold search. Original
saturation cutoffs .01/.99 are descriptive only. For raw negative-distance scores,
probability error/calibration are explicitly inapplicable, not fabricated.

## Two saved draws

Report y0 != y1, its direction, each candidate's ydraw−ycontinuation,draw and their
two-draw mean. Give candidate-wise gain/loss/tie fractions and all horizon/anchor
strata. Preserve both binary observations. Report raw counts beside weighted means.

Cross-draw: choose argmax y[:,0], evaluate y[chosen,1] and continuation on draw 1;
reverse 1→0. Average the two fixed directional effects for a descriptive summary.
Report selection-draw success, evaluation-draw success, evaluation-draw continuation,
effect, maximum-tie multiplicity, all-zero selection banks and departures. This
is not deployable, a true oracle, an upper bound, or an estimate of true candidate
value. Separately report final-budget anchors (remaining budget 15), with no
stochastic continuation after the forced chunk; do not present their agreement
as repeatability evidence for a stochastic tail. No claim that two draws are
independent source episodes or sufficient to identify label reliability.

## Ensemble loss decomposition and fixed-model disagreement

For each bank and every validation reference: departure from continuation, chosen
and baseline empirical success, gained and lost binary outcomes, predicted
probabilities and predicted advantage pchosen−pcontinuation. Gain minus loss
must equal the empirical selected-success difference. Report unconditional
weighted contributions and divide by departure mass only when explicitly labelled
conditional-on-departure. Also report predicted advantage / within-bank std when
std>0, raw score range/std, top-two separation and prediction-minus-empirical
advantage. These are descriptive decompositions, not tuned decision thresholds.

Report pairwise selected-index disagreement among three MLPs, ensemble, logistic
and context; seed probability dispersion and seed-only winner disagreement.
Do not choose a seed, subset, threshold, alternate model or new advancement rule.
All reference effects and bank/candidate evidence are saved, including unfavorable
and tied cases. Reproduce the original aggregate ensemble effect as a descriptive
identity check, not a new scientific gate.

## Deliverable

One report separating supported, contradicted and unresolved explanations. Assess
whether measurements motivate a later baseline-relative ranking objective, without
implementing/training it, promising it will work, or launching another study.
No expansion into additional integrity, restoration or proposer investigations.
