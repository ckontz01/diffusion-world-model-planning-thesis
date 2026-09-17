# CVL-BP1 final development report

Completed 17 September 2026 UTC; handoff 18 September local time. All 450
coordinates completed successfully across 451 attempts. All computation is over;
no follow-up or closed-loop evaluation was launched. Historical
`stop_no_ranking_promise`, the `original_relative` training-only nominee, and
continuation as the working baseline are unchanged.

## Primary result

None of the six fixed learned ensembles exceeds continuation's mean selected
empirical success on this common development set. More source breadth improves
BCE relative to A and C, but does not establish superiority over continuation.
Extra tail draws do not establish improved selection under either objective.
This is not evidence that data breadth always wins or that additional data
cannot help under a different, separately approved learning design.

All results use all 32 model-held-out development references, equal reference
weight, equal H75/H150 weight, and equal available-anchor weight. The outcome is
four-draw success after choosing a labelled candidate and following the frozen
continuation tail, not closed-loop learned-policy success. Only the eight sampled
indices per bank are evaluated. Percentages below are weighted estimates, not
independent episode success counts. Intervals are the preregistered descriptive
whole-source bootstrap intervals, not multiplicity-adjusted confirmation tests.

| Selector | Selected success (%) | Difference vs continuation (pp) | Descriptive interval (pp) |
|---|---:|---:|---:|
| Continuation | 14.128 | 0.000 | [0.000, 0.000] |
| Immediate | 13.021 | -1.107 | [-3.451, 1.270] |
| Uniform sampled eight | 12.207 | -1.921 | [-4.187, 0.171] |
| A BCE | 11.914 | -2.214 | [-5.632, 0.716] |
| B BCE | 13.542 | -0.586 | [-3.516, 2.246] |
| C BCE | 11.133 | -2.995 | [-6.087, 0.000] |
| A relative | 13.509 | -0.618 | [-3.516, 1.855] |
| B relative | 13.444 | -0.684 | [-3.613, 1.953] |
| C relative | 12.240 | -1.888 | [-5.306, 1.270] |

A uses original 96 sources/two draws; B adds 96 training sources/two draws;
C uses original 96 sources and unchanged candidate banks/four draws.

| Objective | B-A (pp; interval) | C-A (pp; interval) | B-C (pp; interval) |
|---|---:|---:|---:|
| BCE | 1.628 [0.000, 3.418] | -0.781 [-2.930, 1.270] | 2.409 [0.423, 4.720] |
| Relative | -0.065 [-1.758, 1.563] | -1.270 [-3.711, 0.977] | 1.204 [-1.009, 3.841] |

The BCE B-C descriptive interval is positive, but this is a comparison between
two learned selectors, not proof of superiority over continuation or grounds
for selecting a new deployed model. No model or seed is promoted.

## Secondary evidence and interpretation

Only 90 of 242 available evaluation banks have defined candidate-value
concordance; all banks remain included in primary selection outcomes.
Conditional concordance for A/B/C is 0.449/0.494/0.486 for BCE and
0.500/0.552/0.527 for relative. BCE Brier errors are
0.10724/0.08871/0.10572. Better probability error for B BCE does not by itself
establish useful policy improvement. Relative scores are not probabilities.

All learned ensembles depart from continuation frequently (76.4%-84.4% weighted
banks). Weighted gained outcomes remain smaller than lost outcomes for each:
A/B/C BCE gain 3.451/3.809/2.767 pp versus loss 5.664/4.395/5.762 pp;
A/B/C relative gain 4.134/4.134/3.809 pp versus loss 4.753/4.818/5.697 pp.
Positive predicted advantages therefore do not translate to positive empirical
mean effects. The frozen aggregate includes every seed as a diagnostic, all
strata, calibration, score dispersion and all reference-level controls; none is
used to substitute a favorable seed or subset.

**Recommendation:** retain continuation and do not advance any BP1 model to
closed loop or buy more tail repetitions on the strength of this result.
Treat the limited BCE breadth improvement as a development observation for
future deliberation, not a selected model or an automatically authorized study.
The remaining issue is useful candidate discrimination/generalization under
this fixed pipeline; BP1 does not uniquely identify its cause or prove a remedy.

## Actual data, updates and resources

| New collection component | Sources | Available/unavailable banks | New outcome records | Physical steps | GPU allocation seconds |
|---|---:|---:|---:|---:|---:|
| Breadth | 96 | 717 / 51 | 11,472 | 2,558,666 | 41,890 |
| Precision | 96 | 709 / 59 | 11,344 | 2,465,042 | 40,860 |
| Evaluation | 32 | 242 / 14 | 7,744 | 1,701,083 | 23,948 |

Total new outcomes: 30,560 versus maximum 32,768; physical steps: 6,724,791.
Breadth allocation seconds include the original 63-second cancelled attempt;
physical steps are those reported for successful workers, not an assertion
that the interrupted attempt did no work. Missing anchors were not replaced.
Final-budget available banks were 164 breadth, 157 precision, and 56 evaluation.
Their recorded labels are respectively 2,624, 2,512, and 1,792; after one copy
per candidate, respectively 1,312, 1,256, and 1,344 are within-new-stage
deterministic repetitions. All 2,512 new precision final-budget labels add no
stochastic-tail information beyond the original saved labels. Repeats are not
independent references or evidence about stochastic tail values.

Training supports: A 96 sources/709 banks/11,344 outcomes; B 192/1,426/22,816;
C 96/709/22,688. The accepted original-96 normalizer is unchanged.
All 18 fits used seeds 8201/8202/8203, with exactly 1,800 BCE or 1,560 relative
updates per fit (30,240 total). Per-seed row presentations for A/B/C were
453,760/456,320/458,880 for BCE and 397,040/399,280/397,040 for relative.
Matched updates therefore did not silently become matched epochs or identical
example exposure. No evaluation outcomes were opened before model freeze.

GPU charge including the cancelled attempt: **106,698 seconds = 29.638 hours**,
below the 86-hour cap. CPU fit 356 seconds plus analysis 133 seconds =
489 allocation-wall seconds at four CPUs (1,956 allocated CPU-seconds), below
the 7,200-second cap. Maximum reported worker RSS: 2,001,854,464 bytes; this is
process RSS, not GPU memory or a scheduler aggregate for an entire node.
Run storage after auxiliary package creation: 1,557,827,446 bytes, before the
small final ACK/coverage records; comfortably below 10 GB including preservation.
Cluster-only controller elapsed time: 79,205.980 seconds (22.002 hours), including
queueing, polling, authentication and I/O, not GPU allocation time. This does not
include time in earlier stopped controllers.

## Preservation, verification and boundaries

Full completion checks authenticated source/runtime/protocol/roles/approvals,
all 450 worker technical identities/seals, the 18-model pre-evaluation freeze,
and training/model/evaluation stage ordering. No protected, reserved closed-loop,
or 1600-5999 payload access was added. No checkpoint, scientific source,
initialization, candidate sampling, objective, weighting or analysis changed.

External backup occurred **after** cluster computation under the explicit
[backup-timing amendment](CLUSTER-CONTINUATION-20260917.md), not the original
intermediate-backup schedule. Four verified archives cover all 450 coordinate
roots and 458 sealed roots in their union. The two historical archives are
unchanged. Final source/control/root logs and the incomplete first packaging
attempt are preserved in a new content-only package, with source metadata
recorded descriptively. User-approved content-only copying avoided applying
restricted attributes; no permission change or computation retry occurred.

The main archive is 1,089,720,320 bytes, SHA256
`90e7489d681b8cd72a175711286f3b5a2d3319a0f05910c1bfe89d7f5d9de72c`.
Auxiliary archive is 23,582,720 bytes, SHA256
`91cc9a3baf8c4e880772192281c3543ea277bc865f876623790d715704dfe8f3`.
Main transfer/verification took 74.229 seconds; auxiliary transfer plus
reverification of the four-archive union took 79.369 seconds. These are local
backup wall times, not Slurm charges. Real ACKs and FINAL-BACKUP-COVERAGE precede
DISPATCH-FINAL. Archive receipts and coverage are retained on both cluster and SSD.
The [coverage certificate](FINAL-BACKUP-COVERAGE.json) is also committed here.
Final local checks passed: seven synthetic cluster-continuation regression tests
and `git diff --check`. No new scientific execution or implementation change was
needed for finalization; the aggregate copy's hash matches the sealed cluster file.

The byte-preserved [completed aggregate](FINAL-AGGREGATE.json), SHA256
`35781ce67c02ff9af665d8af4b2990b00fe80ab91aafbefc84a9ed8743faf400`,
contains all fixed models, controls, 32 reference rows, allocation contrasts and
strata. It is not a newly fitted or reanalyzed result. Four draws do not establish
true candidate values, and sampled-bank results are not exhaustive oracles.
The experiment does not establish closed-loop efficacy, a universal data-scaling
law, breadth/precision interaction, or historical SAGE fidelity.

## Every evaluation reference

Effects versus continuation in percentage points; both horizons and available
anchors reduced using the frozen weights. Reference-specific B-A/C-A/B-C and
controls are also included without rounding in the aggregate JSON.

| Reference | A BCE | B BCE | C BCE | A relative | B relative | C relative |
|---|---:|---:|---:|---:|---:|---:|
| 12 | -3.125 | -3.125 | -3.125 | -3.125 | -3.125 | -6.250 |
| 14 | -15.625 | -15.625 | -12.500 | -12.500 | -12.500 | -12.500 |
| 82 | 6.250 | 6.250 | 6.250 | 3.125 | 6.250 | 9.375 |
| 84 | -3.125 | 0.000 | -3.125 | -3.125 | -3.125 | -3.125 |
| 88 | -3.125 | 0.000 | -3.125 | -3.125 | 0.000 | -3.125 |
| 104 | 0.000 | 3.125 | 0.000 | 0.000 | 3.125 | 0.000 |
| 195 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 222 | -6.250 | -6.250 | -6.250 | -12.500 | -18.750 | -18.750 |
| 386 | 6.250 | 0.000 | 6.250 | 6.250 | 0.000 | 0.000 |
| 444 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 512 | 6.250 | 6.250 | 0.000 | 0.000 | 0.000 | 0.000 |
| 570 | 0.000 | 0.000 | 3.125 | -3.125 | -6.250 | 0.000 |
| 645 | 0.000 | 0.000 | 0.000 | 6.250 | 6.250 | -6.250 |
| 653 | 0.000 | -3.125 | -9.375 | 3.125 | 0.000 | -9.375 |
| 758 | 0.000 | 0.000 | 0.000 | 3.125 | 3.125 | 0.000 |
| 800 | 15.625 | 15.625 | 12.500 | 12.500 | 12.500 | 15.625 |
| 884 | 9.375 | 21.875 | 18.750 | 3.125 | 15.625 | 12.500 |
| 949 | -18.750 | 0.000 | -25.000 | 0.000 | 6.250 | -25.000 |
| 977 | -3.125 | 0.000 | -3.125 | 3.125 | -3.125 | 3.125 |
| 983 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 3.125 |
| 1096 | 3.125 | 9.375 | -9.375 | 0.000 | -3.125 | 6.250 |
| 1128 | -36.458 | -28.125 | -23.958 | -32.292 | -28.125 | -32.292 |
| 1130 | 0.000 | 3.125 | 3.125 | 3.125 | 6.250 | 3.125 |
| 1143 | -6.250 | -6.250 | -9.375 | -3.125 | -3.125 | -6.250 |
| 1206 | -12.500 | -6.250 | -12.500 | -6.250 | -6.250 | 3.125 |
| 1283 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 1299 | 0.000 | 0.000 | -3.125 | -3.125 | 6.250 | 3.125 |
| 1327 | 6.250 | -3.125 | -15.625 | 3.125 | 0.000 | -3.125 |
| 1389 | -9.375 | -6.250 | 0.000 | 15.625 | 0.000 | 6.250 |
| 1487 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 1573 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 1594 | -6.250 | -6.250 | -6.250 | 0.000 | 0.000 | 0.000 |
