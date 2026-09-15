# CVL-1 objective × capacity v1 — completed development comparison

15 September 2026. All **60 fixed fits completed** in one CPU allocation. CVL-1 remains **`stop_no_ranking_promise`**; the original evaluator artifacts and accepted learning diagnosis remain unchanged. No downstream launch.

## Outcome and one recommendation

The original-capacity relative ensemble was nominated **before validation**, under the committed training-fold rule, with only **+0.152 percentage points** versus continuation. Its development-validation effect was **−1.497 points**. All four new ensembles were negative on validation. The nomination remains `original_relative`; we do not replace it with a validation-favored configuration or seed.

**Recommendation: retain continuation as the working baseline and do not promote a learned selector from this study.** Keep the original-relative model only as the preserved training-only nominee for researcher review. Neither this weak cross-fit advantage nor the negative validation comparison justifies an automatic closed-loop experiment, new labels, more training, or a favorable-seed substitution. This interpretation adds no retroactive CVL-1 pass/fail gate.

| Fixed ensemble | Cross-fit effect (pp) | Full TRAIN effect (pp) | VALIDATION effect (pp) |
| --- | --- | --- | --- |
| original_bce | -0.391 | +12.717 | -3.060 |
| compact_bce | -1.606 | +6.727 | -1.823 |
| original_relative | +0.152 | +15.169 | -1.497 |
| compact_relative | -1.845 | +13.715 | -1.172 |

Effects are paired selected empirical success minus continuation on the same labelled-eight bank, equal source → horizon → available anchor, averaging both binary continuation draws. Continuation selected success is 16.536% on TRAIN and 11.914% on VALIDATION. These are sampled-candidate, policy/budget-conditional development quantities—not closed-loop efficacy, true candidate values, an oracle, or confirmation. Negatives do not mean irrecoverability.

## Interpretation: objective and capacity

**Supported:** both relative models strongly fit the training differences. Original-relative reaches TRAIN concordance 0.978 and +15.169 points; compact-relative reaches 0.932 and +13.715 points. Thus this implementation can learn substantial in-sample ranking structure. That is not independent efficacy.

**Not established:** a reproducible source-disjoint gain from the relative objective. Original-relative versus original-BCE improves pooled cross-fit selection by 0.543 points, but the fold contrasts are −1.215, −1.128, +0.174 and +4.340 points. Its positive pooled effect is not a consistent fold-wise advantage. At compact capacity the pooled objective contrast is −0.239 points; its sign also splits two positive/two negative folds. The four fits overlap in training sources, so these folds are not four independent replications.

**The simple capacity-reduction explanation is not supported by cross-fitting.** Compact minus original is −1.215 points for BCE and −1.997 for relative training. Relative compact loses to relative original in all four folds. Shrinking does improve the validation estimates (+1.237 BCE, +0.326 relative), but that reversal cannot be used to switch the frozen training-only nominee.

Validation relative-versus-BCE contrasts are +1.562 points at original capacity and +0.651 at compact capacity, yet both relative ensembles still lose to continuation. Original-relative gains 5.208 points of binary-draw outcome mass but loses 6.706; it departs in 81.641% of weighted banks. Its three seeds disagree on the winner in 83.464% of weighted validation banks. There is no single-seed rescue: the fixed ensemble is the method, and all seed outcomes are reported below.

**Unresolved:** whether a different, separately approved data/learning regime could generalize. This fixed 96-source study with two saved draws cannot separate limited outcome information, representation limitations and other generalization causes. It does not establish impossibility of value learning or justify a new encoder, feature search, label substitution, threshold sweep or redesign now.

## Scope, fitting and freeze

| Role | References | Available banks | Unavailable banks | Candidates | Binary draws | Positive draws |
| --- | --- | --- | --- | --- | --- | --- |
| train | 96 | 709 | 59 | 5672 | 11344 | 1368 |
| validation | 32 | 242 | 14 | 1936 | 3872 | 306 |

Four deterministic identifier-only folds, each 72 fitting /24 held-out sources; 48 cross-fit fits followed by 12 all-96 fits. Seeds 8201/8202/8203; 40 epochs, AdamW lr 0.0003, weight decay 0.0001, batch 256, gradient norm cap 1. Original architecture 619→128→64→1 has 87,681 parameters; compact 619→32→1 has 19,873. No feature engineering or new labels. Fit-specific evaluator normalization uses only fitting sources, with the same eight-candidate weighted normalizer for both objectives; proposer/checkpoint scaling remains unchanged.

| Full-data objective | Rows/fit | Positive targets | Zero targets | Negative targets | Optimizer steps/fit |
| --- | --- | --- | --- | --- | --- |
| original_bce | 11344 | 1368 | 9976 | 0 | 1800 |
| compact_bce | 11344 | 1368 | 9976 | 0 | 1800 |
| original_relative | 9926 | 542 | 8754 | 630 | 1560 |
| compact_relative | 9926 | 542 | 8754 | 630 | 1560 |

BCE retains eight candidates ×two draws per bank. Relative loss retains seven non-self candidates ×two draws, paired with the same bank/draw continuation: `(f(x_i)−f(x_b)−(y_i,d−y_b,d))²`. All 8,754 full-training zero differences remain; only the self-comparisons are omitted. Baseline advantage is exactly zero. Repeated use of a baseline is not new independent data. Across 60 fits, 81,120 optimizer steps were executed. There was no label rounding or distance target.

All new learned selectors retain continuation at an exact maximal-score tie; other maximal ties use lowest original index, with no epsilon. Original frozen controls retain their original lowest-index rule. No exact maximum ties occurred for the four new ensemble comparisons (see tie column). Relative scores are raw advantages, not probabilities; their magnitudes are not directly comparable to BCE.

The source/protocol were committed, pushed and remote-hash verified before fitting. The PRE-VALIDATION-FREEZE seals 144 pre-validation members, including all 60 models, scalers, cross-fit/full-TRAIN reports and training-fold recommendation. The reader rechecks those members before opening validation. The external backup independently matches that freeze. All validation sources remain previously exposed development data.

## Entire fixed comparison

All values below are frozen report transcriptions. Success, departure and ties are percentages; effects, gains and losses are percentage points. Gains/losses are unconditional weighted contributions, not conditional rates. Uniform is the labelled-eight expectation rather than a realized selector. TRAIN numbers for all full-data models are in-sample. Historical learned controls appearing with cross-fit results were trained on all 96 and are **not out-of-fold**; only the new models are.

### Source-held-out cross-fit (96 references)

| Selector | Success % | Effect pp | Gain pp | Loss pp | Depart % | Concordance | Brier | Log loss |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original_bce | 16.146 | -0.391 | +5.078 | +5.469 | 81.684 | 0.52324 | 0.14527 | 0.70372 |
| compact_bce | 14.931 | -1.606 | +4.210 | +5.816 | 81.684 | 0.48746 | 0.14498 | 0.53101 |
| original_relative | 16.688 | +0.152 | +5.838 | +5.686 | 84.418 | 0.54562 | — | — |
| compact_relative | 14.692 | -1.845 | +4.818 | +6.662 | 86.241 | 0.51553 | — | — |
| continuation | 16.536 | +0.000 | +0.000 | +0.000 | 0.000 | 0.53744 | — | — |
| immediate | 16.385 | -0.152 | +5.512 | +5.664 | 68.663 | 0.49868 | — | — |
| uniform_sampled8 | 15.598 | -0.939 | — | — | — | — | — | — |
| historical_ensemble | 29.253 | +12.717 | +13.737 | +1.020 | 81.207 | 0.90574 | 0.04209 | 0.13552 |
| historical_mlp8201 | 29.123 | +12.587 | +13.477 | +0.890 | 80.946 | 0.90175 | 0.04411 | 0.14171 |
| historical_mlp8202 | 29.167 | +12.630 | +13.780 | +1.150 | 82.509 | 0.90153 | 0.04365 | 0.13846 |
| historical_mlp8203 | 29.188 | +12.652 | +13.737 | +1.085 | 82.075 | 0.90253 | 0.04447 | 0.14107 |
| historical_linear | 16.233 | -0.304 | +5.534 | +5.838 | 83.160 | 0.52923 | 0.13634 | 0.44379 |
| historical_context | 14.822 | -1.714 | +5.165 | +6.879 | 87.847 | 0.50000 | 0.13966 | 0.45211 |
| historical_constant | 14.822 | -1.714 | +5.165 | +6.879 | 87.847 | 0.50000 | 0.13165 | 0.43294 |

### Full-data TRAIN (96 references; in-sample)

| Selector | Success % | Effect pp | Gain pp | Loss pp | Depart % | Concordance | Brier | Log loss |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original_bce | 29.253 | +12.717 | +13.737 | +1.020 | 81.207 | 0.90574 | 0.04209 | 0.13552 |
| compact_bce | 23.264 | +6.727 | +9.353 | +2.626 | 81.814 | 0.72727 | 0.05413 | 0.18000 |
| original_relative | 31.706 | +15.169 | +15.516 | +0.347 | 87.587 | 0.97821 | — | — |
| compact_relative | 30.252 | +13.715 | +13.976 | +0.260 | 88.108 | 0.93242 | — | — |
| continuation | 16.536 | +0.000 | +0.000 | +0.000 | 0.000 | 0.53744 | — | — |
| immediate | 16.385 | -0.152 | +5.512 | +5.664 | 68.663 | 0.49868 | — | — |
| uniform_sampled8 | 15.598 | -0.939 | — | — | — | — | — | — |
| historical_ensemble | 29.253 | +12.717 | +13.737 | +1.020 | 81.207 | 0.90574 | 0.04209 | 0.13552 |
| historical_mlp8201 | 29.123 | +12.587 | +13.477 | +0.890 | 80.946 | 0.90175 | 0.04411 | 0.14171 |
| historical_mlp8202 | 29.167 | +12.630 | +13.780 | +1.150 | 82.509 | 0.90153 | 0.04365 | 0.13846 |
| historical_mlp8203 | 29.188 | +12.652 | +13.737 | +1.085 | 82.075 | 0.90253 | 0.04447 | 0.14107 |
| historical_linear | 16.233 | -0.304 | +5.534 | +5.838 | 83.160 | 0.52923 | 0.13634 | 0.44379 |
| historical_context | 14.822 | -1.714 | +5.165 | +6.879 | 87.847 | 0.50000 | 0.13966 | 0.45211 |
| historical_constant | 14.822 | -1.714 | +5.165 | +6.879 | 87.847 | 0.50000 | 0.13165 | 0.43294 |

### Development VALIDATION (32 references)

| Selector | Success % | Effect pp | Gain pp | Loss pp | Depart % | Concordance | Brier | Log loss |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original_bce | 8.854 | -3.060 | +3.776 | +6.836 | 83.203 | 0.56122 | 0.10890 | 0.47155 |
| compact_bce | 10.091 | -1.823 | +3.971 | +5.794 | 78.906 | 0.56865 | 0.10149 | 0.36066 |
| original_relative | 10.417 | -1.497 | +5.208 | +6.706 | 81.641 | 0.58529 | — | — |
| compact_relative | 10.742 | -1.172 | +4.818 | +5.990 | 82.682 | 0.54613 | — | — |
| continuation | 11.914 | +0.000 | +0.000 | +0.000 | 0.000 | 0.50180 | — | — |
| immediate | 11.393 | -0.521 | +4.167 | +4.688 | 65.625 | 0.48491 | — | — |
| uniform_sampled8 | 10.327 | -1.587 | — | — | — | — | — | — |
| historical_ensemble | 8.854 | -3.060 | +3.776 | +6.836 | 83.203 | 0.56122 | 0.10890 | 0.47155 |
| historical_mlp8201 | 8.464 | -3.451 | +3.646 | +7.096 | 82.422 | 0.55767 | 0.11476 | 0.50091 |
| historical_mlp8202 | 8.854 | -3.060 | +3.516 | +6.576 | 84.375 | 0.53199 | 0.11053 | 0.49967 |
| historical_mlp8203 | 8.789 | -3.125 | +3.841 | +6.966 | 83.203 | 0.55297 | 0.11117 | 0.48550 |
| historical_linear | 9.635 | -2.279 | +3.776 | +6.055 | 81.901 | 0.57551 | 0.15418 | 0.47934 |
| historical_context | 9.635 | -2.279 | +3.451 | +5.729 | 83.203 | 0.50000 | 0.15487 | 0.48100 |
| historical_constant | 9.635 | -2.279 | +3.451 | +5.729 | 83.203 | 0.50000 | 0.09538 | 0.34395 |

Concordance is conditional on informative banks with unequal empirical candidate means: 251/709 TRAIN banks and 70/242 VALIDATION banks. Score ties contribute 0.5. It does not demonstrate useful continuation departures by itself. Probability losses/calibration apply only to BCE and historical probability scorers, never relative or distance scores. Historical outcomes match the accepted diagnosis; full original-BCE has the same selected outcomes, without amending that diagnosis.

## Fixed-seed sensitivity, score variation and ties

### Source-held-out cross-fit (96 references)

| Configuration | 8201 pp | 8202 pp | 8203 pp | Ensemble pp | Seed disagree % | Mean range | Mean std | Mean min | Mean max | Max tie % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original_bce | -1.302 | -0.760 | -0.087 | -0.391 | 46.528 | 0.07238 | 0.02342 | 0.05512 | 0.12750 | 0.000 |
| compact_bce | -0.694 | -1.237 | -2.192 | -1.606 | 51.519 | 0.06145 | 0.01964 | 0.08721 | 0.14866 | 0.000 |
| original_relative | +0.043 | -0.304 | -1.628 | +0.152 | 84.375 | 0.22728 | 0.07237 | -0.12082 | 0.10646 | 0.000 |
| compact_relative | -1.085 | -1.693 | -1.758 | -1.845 | 85.720 | 0.22836 | 0.07305 | -0.11632 | 0.11204 | 0.000 |

### Full-data TRAIN (96 references; in-sample)

| Configuration | 8201 pp | 8202 pp | 8203 pp | Ensemble pp | Seed disagree % | Mean range | Mean std | Mean min | Mean max | Max tie % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original_bce | +12.587 | +12.630 | +12.652 | +12.717 | 41.233 | 0.13498 | 0.04525 | 0.08984 | 0.22482 | 0.000 |
| compact_bce | +6.944 | +5.621 | +7.010 | +6.727 | 48.047 | 0.07248 | 0.02339 | 0.11931 | 0.19179 | 0.000 |
| original_relative | +15.104 | +14.844 | +15.256 | +15.169 | 67.882 | 0.26964 | 0.08816 | -0.13154 | 0.13810 | 0.000 |
| compact_relative | +13.368 | +12.760 | +13.173 | +13.715 | 70.095 | 0.25161 | 0.08024 | -0.12677 | 0.12484 | 0.000 |

### Development VALIDATION (32 references)

| Configuration | 8201 pp | 8202 pp | 8203 pp | Ensemble pp | Seed disagree % | Mean range | Mean std | Mean min | Mean max | Max tie % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original_bce | -3.451 | -3.060 | -3.125 | -3.060 | 52.604 | 0.07006 | 0.02245 | 0.04779 | 0.11785 | 0.000 |
| compact_bce | -1.367 | -0.716 | -1.562 | -1.823 | 55.599 | 0.05464 | 0.01714 | 0.07978 | 0.13442 | 0.000 |
| original_relative | -0.065 | -0.586 | -2.474 | -1.497 | 83.464 | 0.23014 | 0.07279 | -0.12066 | 0.10948 | 0.000 |
| compact_relative | -0.846 | +0.586 | -1.823 | -1.172 | 83.464 | 0.23409 | 0.07451 | -0.12544 | 0.10865 | 0.000 |

Score summaries are hierarchically averaged within-bank quantities, not global extrema. Raw per-candidate scores are in the backup. Seed rows are diagnostics, not independent samples or alternative selected models. In particular, the positive compact-relative seed 8202 validation estimate cannot replace its negative fixed ensemble or the pre-validation original-relative nomination.

## Fold effects and objective × capacity contrasts

| Held-out fold (24 sources) | original_bce | compact_bce | original_relative | compact_relative |
| --- | --- | --- | --- | --- |
| 0 | -0.694 | -3.212 | -1.910 | -3.559 |
| 1 | -0.868 | -3.733 | -1.997 | -2.865 |
| 2 | -0.260 | +0.347 | -0.087 | -2.778 |
| 3 | +0.260 | +0.174 | +4.601 | +1.823 |

| Scope | objective_original | objective_compact | capacity_bce | capacity_relative | interaction |
| --- | --- | --- | --- | --- | --- |
| Fold 0 | -1.215 | -0.347 | -2.517 | -1.649 | +0.868 |
| Fold 1 | -1.128 | +0.868 | -2.865 | -0.868 | +1.997 |
| Fold 2 | +0.174 | -3.125 | +0.608 | -2.691 | -3.299 |
| Fold 3 | +4.340 | +1.649 | -0.087 | -2.778 | -2.691 |
| crossfit | +0.543 | -0.239 | -1.215 | -1.997 | -0.781 |
| training | +2.452 | +6.988 | -5.990 | -1.454 | +4.536 |
| validation | +1.562 | +0.651 | +1.237 | +0.326 | -0.911 |

All contrasts are pp: objective = relative−BCE, capacity = compact−original, interaction = objective_compact−objective_original. No outcome-based fold exclusions.

## Descriptive reference intervals

| Configuration | Cross-fit pp [2.5%,97.5%] | Full TRAIN pp [2.5%,97.5%] | VALIDATION pp [2.5%,97.5%] |
| --- | --- | --- | --- |
| original_bce | -0.391 [-2.279, +1.497] | +12.717 [+10.286, +15.365] | -3.060 [-7.292, +0.846] |
| compact_bce | -1.606 [-3.559, +0.391] | +6.727 [+4.601, +9.006] | -1.823 [-5.208, +1.562] |
| original_relative | +0.152 [-1.845, +2.127] | +15.169 [+12.695, +17.860] | -1.497 [-5.794, +2.539] |
| compact_relative | -1.845 [-3.776, +0.109] | +13.715 [+11.415, +16.233] | -1.172 [-4.883, +2.148] |

These are the predeclared 10,000-resample whole-reference percentile summaries. They are descriptive development intervals, not confirmatory tests or valid post-selection coverage claims. Neither candidate rows, draws, seeds nor folds are counted as independent source references.

## BCE calibration (fixed bins; no fitted calibration)

### Source-held-out cross-fit (96 references)

| Model | Probability bin | Hierarchical mass % | Mean probability | Empirical outcome |
| --- | --- | --- | --- | --- |
| original_bce | [0.0,0.2) | 86.746 | 0.02236 | 0.12968 |
| original_bce | [0.2,0.4) | 5.008 | 0.28234 | 0.26381 |
| original_bce | [0.4,0.6) | 3.168 | 0.49407 | 0.31849 |
| original_bce | [0.6,0.8) | 3.098 | 0.69020 | 0.38967 |
| original_bce | [0.8,1.0] | 1.980 | 0.90217 | 0.40959 |
| compact_bce | [0.0,0.2) | 81.814 | 0.04250 | 0.13190 |
| compact_bce | [0.2,0.4) | 9.380 | 0.28406 | 0.19954 |
| compact_bce | [0.4,0.6) | 4.682 | 0.48584 | 0.36501 |
| compact_bce | [0.6,0.8) | 2.469 | 0.69614 | 0.32088 |
| compact_bce | [0.8,1.0] | 1.655 | 0.89554 | 0.26230 |

### Full-data TRAIN (96 references; in-sample)

| Model | Probability bin | Hierarchical mass % | Mean probability | Empirical outcome |
| --- | --- | --- | --- | --- |
| original_bce | [0.0,0.2) | 77.865 | 0.02018 | 0.01310 |
| original_bce | [0.2,0.4) | 6.641 | 0.29139 | 0.30596 |
| original_bce | [0.4,0.6) | 4.329 | 0.49887 | 0.56015 |
| original_bce | [0.6,0.8) | 3.554 | 0.70195 | 0.76107 |
| original_bce | [0.8,1.0] | 7.612 | 0.94083 | 0.97434 |
| compact_bce | [0.0,0.2) | 76.812 | 0.03153 | 0.02137 |
| compact_bce | [0.2,0.4) | 8.550 | 0.29549 | 0.30933 |
| compact_bce | [0.4,0.6) | 4.546 | 0.48954 | 0.55131 |
| compact_bce | [0.6,0.8) | 4.129 | 0.70220 | 0.73390 |
| compact_bce | [0.8,1.0] | 5.962 | 0.91567 | 0.96861 |

### Development VALIDATION (32 references)

| Model | Probability bin | Hierarchical mass % | Mean probability | Empirical outcome |
| --- | --- | --- | --- | --- |
| original_bce | [0.0,0.2) | 88.428 | 0.02301 | 0.09553 |
| original_bce | [0.2,0.4) | 5.713 | 0.27967 | 0.07692 |
| original_bce | [0.4,0.6) | 1.904 | 0.49714 | 0.19231 |
| original_bce | [0.6,0.8) | 1.904 | 0.70081 | 0.15385 |
| original_bce | [0.8,1.0] | 2.051 | 0.85829 | 0.38095 |
| compact_bce | [0.0,0.2) | 85.938 | 0.04529 | 0.07983 |
| compact_bce | [0.2,0.4) | 6.982 | 0.28466 | 0.20979 |
| compact_bce | [0.4,0.6) | 3.613 | 0.47555 | 0.24324 |
| compact_bce | [0.6,0.8) | 1.123 | 0.66371 | 0.19565 |
| compact_bce | [0.8,1.0] | 2.344 | 0.92150 | 0.38542 |

Original/compact BCE validation Brier scores are 0.10890/0.10149, both worse than the unchanged training-constant 0.09538. Better probability error alone does not establish better within-bank selection.

## Every reference and evidence access

[REFERENCE-RESULTS.json](REFERENCE-RESULTS.json) includes every reference for all three reporting scopes and every fixed ensemble, seed and historical control: selected/baseline outcomes, effects, gains, losses, departures, predicted advantage and concordance. No favorable reference subset is selected. Complete bank-level metrics, each candidate score and both saved outcomes, strata and unavailable anchor identities are in the sealed backup. The compact per-reference effect tables below cover all four new ensembles; full controls/decomposition are in JSON.

### Source-held-out cross-fit (96 references) — every reference effect (pp)

| Reference | original_bce | compact_bce | original_relative | compact_relative |
| --- | --- | --- | --- | --- |
| 25 | +12.500 | +12.500 | +6.250 | -6.250 |
| 30 | -8.333 | +0.000 | -8.333 | +0.000 |
| 33 | +0.000 | +0.000 | +6.250 | +6.250 |
| 117 | +6.250 | +6.250 | +6.250 | +6.250 |
| 128 | -12.500 | -12.500 | -18.750 | -18.750 |
| 149 | -18.750 | -18.750 | -12.500 | -12.500 |
| 206 | +0.000 | -6.250 | +0.000 | +0.000 |
| 219 | +0.000 | +0.000 | +0.000 | -12.500 |
| 258 | -12.500 | -12.500 | -25.000 | -25.000 |
| 301 | +6.250 | -6.250 | -18.750 | -18.750 |
| 320 | -6.250 | -6.250 | -6.250 | +0.000 |
| 321 | -6.250 | +6.250 | +6.250 | +0.000 |
| 326 | +0.000 | +0.000 | +0.000 | +0.000 |
| 327 | +0.000 | +0.000 | +0.000 | +0.000 |
| 329 | +0.000 | +0.000 | +0.000 | +0.000 |
| 356 | +6.250 | +0.000 | +6.250 | +6.250 |
| 410 | +0.000 | +0.000 | +0.000 | +0.000 |
| 417 | +12.500 | +6.250 | +0.000 | +0.000 |
| 424 | +0.000 | +0.000 | +6.250 | +0.000 |
| 433 | -16.667 | -8.333 | -16.667 | -8.333 |
| 435 | +6.250 | +0.000 | +6.250 | +0.000 |
| 440 | +0.000 | -6.250 | +0.000 | -12.500 |
| 443 | -6.250 | -6.250 | -6.250 | -18.750 |
| 445 | +4.167 | +12.500 | +4.167 | +12.500 |
| 466 | -12.500 | -18.750 | -18.750 | -12.500 |
| 467 | +6.250 | +6.250 | +6.250 | +0.000 |
| 479 | -6.250 | -6.250 | -6.250 | -6.250 |
| 483 | +0.000 | +0.000 | +0.000 | +0.000 |
| 484 | -6.250 | -6.250 | -6.250 | -6.250 |
| 492 | +12.500 | +6.250 | +6.250 | +12.500 |
| 518 | +0.000 | +0.000 | -6.250 | -6.250 |
| 526 | +0.000 | +0.000 | +0.000 | +0.000 |
| 536 | -8.333 | -8.333 | -4.167 | +12.500 |
| 552 | -12.500 | -25.000 | +0.000 | +0.000 |
| 566 | -6.250 | -6.250 | -6.250 | -6.250 |
| 597 | +0.000 | +0.000 | +0.000 | +0.000 |
| 598 | -6.250 | -6.250 | -6.250 | -6.250 |
| 602 | +0.000 | -25.000 | -12.500 | -12.500 |
| 619 | +0.000 | +0.000 | +0.000 | +0.000 |
| 663 | -25.000 | -25.000 | +37.500 | +25.000 |
| 673 | +6.250 | +6.250 | +12.500 | +12.500 |
| 685 | +0.000 | +0.000 | +0.000 | +0.000 |
| 686 | -16.667 | -8.333 | +14.583 | -16.667 |
| 698 | +12.500 | -6.250 | +0.000 | +6.250 |
| 700 | +0.000 | +0.000 | +0.000 | +0.000 |
| 712 | -6.250 | -6.250 | +0.000 | -6.250 |
| 728 | +6.250 | +0.000 | +6.250 | +0.000 |
| 748 | +0.000 | -8.333 | +0.000 | +8.333 |
| 750 | +25.000 | +0.000 | -25.000 | -25.000 |
| 762 | -6.250 | -6.250 | +6.250 | -6.250 |
| 767 | +6.250 | -16.667 | -16.667 | -16.667 |
| 769 | +6.250 | +6.250 | +0.000 | -6.250 |
| 788 | +0.000 | +8.333 | -8.333 | -25.000 |
| 818 | +12.500 | +20.833 | +12.500 | +12.500 |
| 834 | -18.750 | -18.750 | -12.500 | -18.750 |
| 864 | +6.250 | +0.000 | +0.000 | +0.000 |
| 909 | +0.000 | +0.000 | +0.000 | +0.000 |
| 910 | +12.500 | +0.000 | +0.000 | -12.500 |
| 947 | +18.750 | +18.750 | +25.000 | +18.750 |
| 952 | +0.000 | +0.000 | +0.000 | +0.000 |
| 960 | -6.250 | -12.500 | -6.250 | -12.500 |
| 978 | +6.250 | +6.250 | +6.250 | +0.000 |
| 990 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1021 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1033 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1105 | -25.000 | -25.000 | +12.500 | -6.250 |
| 1138 | -6.250 | -6.250 | -6.250 | +0.000 |
| 1196 | -6.250 | -18.750 | -6.250 | -18.750 |
| 1197 | +12.500 | +12.500 | +12.500 | +12.500 |
| 1225 | -18.750 | +6.250 | -18.750 | +6.250 |
| 1242 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1255 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1264 | -6.250 | -6.250 | -6.250 | +0.000 |
| 1290 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1293 | +25.000 | +31.250 | +18.750 | +6.250 |
| 1313 | +0.000 | +0.000 | -6.250 | -6.250 |
| 1314 | +6.250 | +6.250 | +0.000 | +0.000 |
| 1319 | +0.000 | -12.500 | +6.250 | -6.250 |
| 1336 | -6.250 | -12.500 | -6.250 | -6.250 |
| 1357 | +6.250 | +6.250 | +6.250 | +6.250 |
| 1367 | +6.250 | +6.250 | +6.250 | +6.250 |
| 1374 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1407 | +12.500 | +12.500 | +12.500 | +12.500 |
| 1408 | -6.250 | -6.250 | +0.000 | +0.000 |
| 1444 | +8.333 | +16.667 | +0.000 | +0.000 |
| 1452 | -6.250 | -6.250 | -6.250 | +0.000 |
| 1472 | -12.500 | +0.000 | +0.000 | -12.500 |
| 1478 | -6.250 | +0.000 | +6.250 | -6.250 |
| 1481 | +12.500 | +12.500 | +6.250 | +0.000 |
| 1512 | +6.250 | +6.250 | +6.250 | +0.000 |
| 1534 | +0.000 | +0.000 | +25.000 | +25.000 |
| 1538 | -6.250 | -12.500 | +0.000 | -6.250 |
| 1556 | +0.000 | +0.000 | +6.250 | +6.250 |
| 1558 | +0.000 | +0.000 | +6.250 | +6.250 |
| 1564 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1584 | +6.250 | +6.250 | +6.250 | +0.000 |

### Full-data TRAIN (96 references; in-sample) — every reference effect (pp)

| Reference | original_bce | compact_bce | original_relative | compact_relative |
| --- | --- | --- | --- | --- |
| 25 | +12.500 | +12.500 | +12.500 | +12.500 |
| 30 | +8.333 | +0.000 | +8.333 | +8.333 |
| 33 | +12.500 | +6.250 | +18.750 | +18.750 |
| 117 | +31.250 | +18.750 | +37.500 | +31.250 |
| 128 | +18.750 | +18.750 | +18.750 | +18.750 |
| 149 | +6.250 | -6.250 | +6.250 | +6.250 |
| 206 | +0.000 | -12.500 | +6.250 | +6.250 |
| 219 | +0.000 | +0.000 | +6.250 | +6.250 |
| 258 | +0.000 | -12.500 | +0.000 | +0.000 |
| 301 | +25.000 | +18.750 | +25.000 | +25.000 |
| 320 | +6.250 | -6.250 | +6.250 | +6.250 |
| 321 | +25.000 | +18.750 | +25.000 | +12.500 |
| 326 | +0.000 | +0.000 | +0.000 | +0.000 |
| 327 | +0.000 | +0.000 | +0.000 | +0.000 |
| 329 | +6.250 | +0.000 | +6.250 | +6.250 |
| 356 | +6.250 | +6.250 | +12.500 | +12.500 |
| 410 | +0.000 | +0.000 | +0.000 | +0.000 |
| 417 | +12.500 | +6.250 | +25.000 | +18.750 |
| 424 | +6.250 | +0.000 | +6.250 | +6.250 |
| 433 | +6.250 | -8.333 | +6.250 | +6.250 |
| 435 | +12.500 | +12.500 | +12.500 | +12.500 |
| 440 | +25.000 | +18.750 | +25.000 | +18.750 |
| 443 | +12.500 | -6.250 | +12.500 | +12.500 |
| 445 | +37.500 | +37.500 | +37.500 | +37.500 |
| 466 | +18.750 | +18.750 | +18.750 | +18.750 |
| 467 | +12.500 | +6.250 | +12.500 | +12.500 |
| 479 | +18.750 | +12.500 | +18.750 | +18.750 |
| 483 | +0.000 | +0.000 | +0.000 | +0.000 |
| 484 | +0.000 | -6.250 | +0.000 | +0.000 |
| 492 | +18.750 | +12.500 | +18.750 | +12.500 |
| 518 | +6.250 | +0.000 | +6.250 | +6.250 |
| 526 | +0.000 | +0.000 | +6.250 | +6.250 |
| 536 | +33.333 | +33.333 | +25.000 | +25.000 |
| 552 | +18.750 | +18.750 | +18.750 | +18.750 |
| 566 | +6.250 | +0.000 | +6.250 | +6.250 |
| 597 | +6.250 | +0.000 | +6.250 | +6.250 |
| 598 | +0.000 | -6.250 | +6.250 | +6.250 |
| 602 | +6.250 | +0.000 | +6.250 | +6.250 |
| 619 | +0.000 | +0.000 | +12.500 | +6.250 |
| 663 | +50.000 | +25.000 | +50.000 | +50.000 |
| 673 | +12.500 | +12.500 | +25.000 | +12.500 |
| 685 | +12.500 | +0.000 | +18.750 | +12.500 |
| 686 | +22.917 | +16.667 | +22.917 | +31.250 |
| 698 | +18.750 | +6.250 | +18.750 | +18.750 |
| 700 | +6.250 | +6.250 | +12.500 | +12.500 |
| 712 | -6.250 | -6.250 | +6.250 | +0.000 |
| 728 | +14.583 | +14.583 | +14.583 | +14.583 |
| 748 | +25.000 | +0.000 | +31.250 | +31.250 |
| 750 | +37.500 | +12.500 | +50.000 | +50.000 |
| 762 | +6.250 | +6.250 | +12.500 | +12.500 |
| 767 | +6.250 | +6.250 | +6.250 | +6.250 |
| 769 | +25.000 | +6.250 | +25.000 | +25.000 |
| 788 | +8.333 | +8.333 | +22.917 | +16.667 |
| 818 | +66.667 | +45.833 | +66.667 | +45.833 |
| 834 | +0.000 | -18.750 | +0.000 | +0.000 |
| 864 | +6.250 | +0.000 | +12.500 | +12.500 |
| 909 | +0.000 | +0.000 | +0.000 | +0.000 |
| 910 | +18.750 | +12.500 | +25.000 | +25.000 |
| 947 | +31.250 | +25.000 | +31.250 | +31.250 |
| 952 | +12.500 | +0.000 | +12.500 | +12.500 |
| 960 | +18.750 | +0.000 | +18.750 | +18.750 |
| 978 | +6.250 | +0.000 | +12.500 | +6.250 |
| 990 | +12.500 | +12.500 | +12.500 | +12.500 |
| 1021 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1033 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1105 | +18.750 | +18.750 | +25.000 | +18.750 |
| 1138 | +18.750 | +18.750 | +18.750 | +18.750 |
| 1196 | +12.500 | +12.500 | +12.500 | +12.500 |
| 1197 | +12.500 | +12.500 | +12.500 | +12.500 |
| 1225 | +0.000 | +0.000 | +6.250 | +6.250 |
| 1242 | +6.250 | +0.000 | +6.250 | +0.000 |
| 1255 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1264 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1290 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1293 | +43.750 | +18.750 | +56.250 | +56.250 |
| 1313 | +0.000 | +0.000 | +6.250 | +0.000 |
| 1314 | +6.250 | +6.250 | +6.250 | +6.250 |
| 1319 | +18.750 | +6.250 | +18.750 | +18.750 |
| 1336 | +12.500 | +0.000 | +18.750 | +12.500 |
| 1357 | +12.500 | +6.250 | +12.500 | +12.500 |
| 1367 | +6.250 | +6.250 | +6.250 | +6.250 |
| 1374 | +6.250 | +0.000 | +6.250 | +6.250 |
| 1407 | +18.750 | +18.750 | +18.750 | +18.750 |
| 1408 | +6.250 | +6.250 | +12.500 | +12.500 |
| 1444 | +16.667 | +16.667 | +16.667 | +8.333 |
| 1452 | +0.000 | -6.250 | +6.250 | +6.250 |
| 1472 | +18.750 | +6.250 | +18.750 | +18.750 |
| 1478 | +18.750 | +0.000 | +18.750 | +18.750 |
| 1481 | +18.750 | +18.750 | +18.750 | +12.500 |
| 1512 | +12.500 | +6.250 | +18.750 | +18.750 |
| 1534 | +50.000 | +37.500 | +50.000 | +50.000 |
| 1538 | +0.000 | -6.250 | +16.667 | +16.667 |
| 1556 | +12.500 | +6.250 | +12.500 | +12.500 |
| 1558 | +18.750 | +12.500 | +25.000 | +18.750 |
| 1564 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1584 | +25.000 | +18.750 | +25.000 | +25.000 |

### Development VALIDATION (32 references) — every reference effect (pp)

| Reference | original_bce | compact_bce | original_relative | compact_relative |
| --- | --- | --- | --- | --- |
| 26 | -25.000 | -25.000 | -25.000 | -18.750 |
| 39 | +18.750 | +12.500 | +18.750 | +12.500 |
| 59 | +6.250 | +0.000 | +0.000 | +6.250 |
| 77 | -6.250 | -6.250 | -6.250 | +0.000 |
| 81 | +6.250 | +6.250 | +0.000 | +0.000 |
| 94 | +0.000 | -6.250 | +0.000 | +0.000 |
| 161 | +0.000 | +0.000 | +6.250 | +0.000 |
| 217 | +0.000 | +6.250 | +6.250 | +0.000 |
| 264 | +6.250 | +0.000 | +0.000 | +0.000 |
| 426 | +0.000 | +0.000 | +0.000 | +0.000 |
| 436 | -37.500 | -25.000 | -25.000 | -37.500 |
| 573 | +0.000 | +6.250 | +6.250 | +6.250 |
| 588 | -6.250 | -6.250 | +6.250 | +0.000 |
| 591 | +0.000 | -6.250 | +0.000 | +0.000 |
| 690 | -25.000 | +0.000 | -25.000 | -25.000 |
| 702 | +12.500 | +25.000 | +18.750 | +18.750 |
| 846 | +12.500 | +12.500 | +6.250 | +12.500 |
| 861 | +0.000 | +0.000 | +6.250 | -6.250 |
| 907 | +0.000 | +0.000 | +12.500 | +0.000 |
| 1001 | -12.500 | -6.250 | +0.000 | +0.000 |
| 1034 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1036 | -6.250 | +6.250 | +12.500 | +6.250 |
| 1162 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1223 | +0.000 | -14.583 | -6.250 | -6.250 |
| 1271 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1289 | +6.250 | +0.000 | +0.000 | +0.000 |
| 1359 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1416 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1454 | -6.250 | -6.250 | -6.250 | +0.000 |
| 1495 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1501 | -12.500 | -18.750 | -25.000 | -6.250 |
| 1521 | -29.167 | -12.500 | -29.167 | +0.000 |

## Resources, identities and backup

Job **301441** completed 0:0. One allocation, **201 wall seconds at 4 CPUs/8GiB**, 804 allocated core-seconds (0.2233 core-hours), versus the 7,200-wall-second ceiling. Final Slurm TotalCPU is **656.057 CPU seconds**; the early receipt captured a not-yet-populated 00:00:00 and is preserved, not interpreted as zero use. Final worker telemetry: 196.668 wall seconds, 653.595 process CPU seconds, maximum RSS 809,873,408 bytes. Fits used 147.028 wall seconds total, range 1.456–4.497 seconds per fit, below every 100-second reservation. All 60 completed; no failed allocation or retry. Only stderr was an informational Apptainer localtime underlay message.

New worker payload **90,840,277 bytes**; run including contemporaneous logs/launch metadata **90,851,777 bytes** before the terminal receipt, well below decimal 1GB. The terminal archive is **90,972,160 bytes**. Source/report/accounting supplements are small and remain inside the envelope. 17 synthetic tests passed before launch. No GPU, new label, simulator, LeWM, diffusion, adapter, closed-loop payload or 1600–5999 payload was used. The three E12 drafts remain unchanged.

| Identity | Value |
| --- | --- |
| Frozen execution source commit | `d2cf5c8f6381dd6684403c55321210d165a33ea6` |
| Source archive SHA-256 | `29c2e1a6decac86c81810fb074df42cfe19a61244f1facfdab1ba2e5cc4d9a80` |
| LF source manifest SHA-256 | `9a3ede8d257698d62e50b3f088e64e33573d3c25de4f9d2a8f42935a4e500284` |
| Protocol SHA-256 | `6cc00051d539a6562e05b5b445549dc564ade43f1a39429da85fe54b0fb80647` |
| Pre-validation freeze SHA-256 | `d8a592d215ec7819c191694b531ab08c4dd9dc54b19b6b4b6b1ec002df370582` |
| Final results seal SHA-256 | `f76f6eb465706c048d36547015da2178f0ba00429530c1fa4b336aec168c9e9a` |
| Terminal backup SHA-256 | `2545ec37b4b840a54926aa169bac16a9826174e8147d3c2edad8314522c5392d` |

Cluster run: `/lustreFS/data/superworld/ckontzias/thesis/experiments/cvl1-objective-capacity-20260915-v1/run-d2cf5c8`. External THESIS_SSD backup: `D:/THESIS-BACKUPS/cvl1-objective-capacity-20260915-v1/result-d2cf5c8.tar`, plus `source-d2cf5c8.tar`, final accounting receipt and publication supplement. Remote/local archive hashes match. All 145 root-sealed files and five 14-member model sub-seals verified (215 member checks), plus all 144 pre-validation members. Backup scope is new models/scalers, reports/predictions, source, job logs and accounting; the original simulator dataset was not copied.

Execution details: [EXECUTION.md](EXECUTION.md). Fixed definitions: [PROTOCOL.md](PROTOCOL.md). This Markdown is publication-only transcription of the sealed study aggregates, not a rerun or altered reporting procedure.
