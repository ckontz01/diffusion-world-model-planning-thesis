# SI1 completed development result

**Retain continuation; promote no model.** Adding the saved immediate/continuation costs did not improve the observed source-held-out selection mean. Treatment minus control was -0.065 percentage points, with a descriptive reference-bootstrap interval [-0.792, +0.716] pp. This is not evidence of equivalence or proof that these scores cannot help another evaluator.

All results use 192 out-of-fold sources, equal source/horizon/available-anchor weighting, the fixed three-seed ensembles and two saved outcomes per sampled candidate. Seeds, rows and draws are not independent sources. All 24 fits and 43,200 updates completed; no model was selected.

## Overall selection

| Selector | Selected success % | Effect vs continuation pp | Descriptive interval pp | Gained % | Lost % | Departure % |
|---|---:|---:|---|---:|---:|---:|
| continuation | 15.668 | +0.000 | [+0.000, +0.000] | 0.000 | 0.000 | 0.000 |
| immediate | 15.061 | -0.608 | [-2.018, +0.781] | 4.763 | 5.371 | 67.860 |
| control | 14.507 | -1.161 | [-2.517, +0.130] | 4.308 | 5.469 | 81.250 |
| scores | 14.442 | -1.226 | [-2.528, +0.022] | 4.058 | 5.284 | 76.172 |

Gained/lost values are weighted paired binary-outcome fractions, not counts of independent episodes. Treatment changes the selected candidate relative to control on 20.703% of weighted banks; paired gains are 1.172%, losses 1.237%. Against continuation it departs less often (76.172% versus control 81.250%) but still loses more outcomes than it gains.

## Secondary quantities

| Selector | Concordance | Brier | Log loss | Tied maxima % |
|---|---:|---:|---:|---:|
| continuation | 0.517565 | — | — | 0.000 |
| immediate | 0.488797 | — | — | 0.000 |
| control | 0.521606 | 0.129609 | 0.544044 | 0.000 |
| scores | 0.519730 | 0.128114 | 0.531089 | 0.000 |

Concordance is defined on 480 of 1,426 banks with empirical candidate-outcome variation; undefined banks are not scored as zero. All four selectors have unique maxima on all banks. Costs are not probabilities, so Brier/log loss do not apply to the two non-neural controls. Slightly better probability error does not establish better selection.

## Fold effects (percentage points versus continuation)

| Fold | Sources | Immediate | Control | Treatment | Treatment − control |
|---|---:|---:|---:|---:|---:|
| 0 | 48 | +0.130 | -2.344 | -2.474 | -0.130 |
| 1 | 48 | -0.174 | +0.998 | -0.564 | -1.562 |
| 2 | 48 | -1.866 | -0.347 | +0.217 | +0.564 |
| 3 | 48 | -0.521 | -2.951 | -2.083 | +0.868 |

## Horizon / anchor-slot effects (percentage points)

| Stratum | Available banks | Immediate | Control | Treatment | Treatment − control |
|---|---:|---:|---:|---:|---:|
| H150-slot0 | 192 | +1.302 | +2.865 | +3.125 | +0.260 |
| H150-slot1 | 192 | +0.000 | +1.823 | +0.260 | -1.562 |
| H150-slot2 | 180 | -0.278 | -0.833 | -0.833 | +0.000 |
| H150-slot3 | 174 | +0.000 | +0.000 | +0.000 | +0.000 |
| H75-slot0 | 192 | -3.385 | -3.646 | -2.344 | +1.302 |
| H75-slot1 | 188 | -1.596 | -2.660 | -3.191 | -0.532 |
| H75-slot2 | 161 | -1.242 | -2.484 | -1.242 | +1.242 |
| H75-slot3 | 147 | +0.000 | -2.041 | -2.041 | +0.000 |

Slots retain the original fixed schedule and availability. Stratum summaries condition on available sources; averaging this table equally does not reproduce the primary hierarchical weighting. No favorable fold or stratum was selected.

## Execution, preservation and resources

- Slurm 301953: COMPLETED, exit 0:0; one allocation, no retries. Partition defq, account superworld, 4 CPUs, 8 GiB, no GPU TRES or passthrough. Queue approximately 1 second; allocation 102 seconds (408 reserved CPU-core-seconds).
- Worker reported 97.203 seconds wall and 339.093 process CPU seconds; Slurm TotalCPU 341.640 seconds. Worker peak RSS 967,847,936 bytes; Slurm sampled batch MaxRSS 697,768 KiB. These measure different scopes/sampling and are reported separately.
- Exactly 24 fits × 1,800 updates = 43,200. Total row presentations: 10,994,304 (includes repeated minibatches, not new labels or independent samples). Per-fit row presentations, timings and fitting-source IDs are in FINAL-AGGREGATE.json.
- 1,426 available banks; 110 unavailable slots; 11,408 candidate-index rows; 22,816 original binary records. No new labels, tail streams or model-based rollouts. Deterministic-tail repetitions remain repeated records, not added independent evidence.
- Worker seal verified all 40 members. Complete archive verified all 68 members: source including disabled template, separate execution approval, all 24 weights, four normalizers/freeze records/prediction files, reports, Slurm logs, accounting and operational launcher versions.
- Unique archived payload: 20,442,378 bytes; archive: 20,500,480 bytes. Remote payload plus archive at sealing: 40,942,858 bytes, before small manifest/receipt/documentation additions. All are far below the 1 GB ceiling; final inventory accompanies the handoff.
- External backup: D:/THESIS-BACKUPS/candidate-value-score-information-20260918/execution-68145e6458da0b90 on verified THESIS_SSD. SI1-COMPLETE.tar SHA-256: 57deab4d1f30b3618f336c0c73bad45827e64301aa7ae3664bedc0e35d715e41.
- Source manifest: 68145e6458da0b90255dd98e4fa2b9469dea12907797d7830c9bd233314be35c. Worker seal: 73384f244abd42067fc13ae64318abfa6a1c3036708fc45bc34ec8cdc4e7c3e3.
- Execution approval: 9cbddb0a9e19ab162961a38253efc0fefcc3e8936ec70a84cedbbe4955a23cef. Final aggregate SHA-256: 4d3aed3f401680be2f616fd15d8dd47810857ec9fe22cbbf72e099fb908d6eab.

## Bounded interpretation

Access to these two saved lookahead costs was not sufficient to improve this fixed BCE selector on the evaluated source-held-out development banks. The result supports retaining continuation, not promoting either learned ensemble. It does not isolate the individual costs, demonstrate equivalence, establish a general limitation of learned evaluation, or measure closed-loop efficacy. Intervals are descriptive: fold training sets overlap and this is historically exposed development data. No follow-up study, threshold tuning, seed selection, additional labels or closed-loop launch is authorized by this result. Historical decisions and E12 drafts are unchanged.

## All 192 source effects (percentage points)

Continuation effect is zero for every source. Full selected outcomes and secondary metrics for every source, fold and stratum are also preserved in FINAL-AGGREGATE.json.

| Source | Immediate | Control | Treatment | Treatment − control |
|---:|---:|---:|---:|---:|
| 25 | +6.250 | +12.500 | +6.250 | -6.250 |
| 30 | -8.333 | -8.333 | -8.333 | +0.000 |
| 33 | +0.000 | +6.250 | +0.000 | -6.250 |
| 62 | +0.000 | +6.250 | +6.250 | +0.000 |
| 92 | -6.250 | +0.000 | +0.000 | +0.000 |
| 96 | +0.000 | -6.250 | -6.250 | +0.000 |
| 117 | +6.250 | +6.250 | +6.250 | +0.000 |
| 121 | +0.000 | +0.000 | +0.000 | +0.000 |
| 123 | +0.000 | +0.000 | +0.000 | +0.000 |
| 128 | -6.250 | -6.250 | -6.250 | +0.000 |
| 149 | -18.750 | -12.500 | -12.500 | +0.000 |
| 152 | -6.250 | -6.250 | -6.250 | +0.000 |
| 157 | +0.000 | +0.000 | +0.000 | +0.000 |
| 160 | +0.000 | +0.000 | +6.250 | +6.250 |
| 206 | -6.250 | -6.250 | -6.250 | +0.000 |
| 219 | -12.500 | +0.000 | +0.000 | +0.000 |
| 225 | +6.250 | +0.000 | -25.000 | -25.000 |
| 241 | +0.000 | -25.000 | -25.000 | +0.000 |
| 245 | +0.000 | +0.000 | +0.000 | +0.000 |
| 246 | -37.500 | -6.250 | -12.500 | -6.250 |
| 257 | +0.000 | +0.000 | +0.000 | +0.000 |
| 258 | -12.500 | -25.000 | -25.000 | +0.000 |
| 260 | +6.250 | +0.000 | +0.000 | +0.000 |
| 280 | +0.000 | +0.000 | +0.000 | +0.000 |
| 289 | -6.250 | +0.000 | +0.000 | +0.000 |
| 301 | -31.250 | -18.750 | -18.750 | +0.000 |
| 307 | +25.000 | +12.500 | +12.500 | +0.000 |
| 320 | +0.000 | -6.250 | -6.250 | +0.000 |
| 321 | +0.000 | +18.750 | +12.500 | -6.250 |
| 326 | +0.000 | +0.000 | +0.000 | +0.000 |
| 327 | +0.000 | +0.000 | +0.000 | +0.000 |
| 329 | +0.000 | +0.000 | +0.000 | +0.000 |
| 333 | +0.000 | +0.000 | +0.000 | +0.000 |
| 356 | +0.000 | +6.250 | +6.250 | +0.000 |
| 357 | -6.250 | -12.500 | -6.250 | +6.250 |
| 387 | +0.000 | +6.250 | +6.250 | +0.000 |
| 396 | +6.250 | +0.000 | +0.000 | +0.000 |
| 410 | +0.000 | +0.000 | +0.000 | +0.000 |
| 411 | +0.000 | +0.000 | +0.000 | +0.000 |
| 417 | -6.250 | +6.250 | +6.250 | +0.000 |
| 424 | +0.000 | +0.000 | +0.000 | +0.000 |
| 431 | +25.000 | +12.500 | +12.500 | +0.000 |
| 433 | -8.333 | -8.333 | -8.333 | +0.000 |
| 435 | -6.250 | +0.000 | +0.000 | +0.000 |
| 440 | +6.250 | +0.000 | -6.250 | -6.250 |
| 443 | -6.250 | -6.250 | -6.250 | +0.000 |
| 445 | +37.500 | +25.000 | +12.500 | -12.500 |
| 454 | +0.000 | +0.000 | +0.000 | +0.000 |
| 463 | +0.000 | +0.000 | +0.000 | +0.000 |
| 465 | +6.250 | +0.000 | +0.000 | +0.000 |
| 466 | +0.000 | +0.000 | -12.500 | -12.500 |
| 467 | -6.250 | +0.000 | +0.000 | +0.000 |
| 479 | -6.250 | -6.250 | -6.250 | +0.000 |
| 483 | +0.000 | +0.000 | +0.000 | +0.000 |
| 484 | -6.250 | -6.250 | -6.250 | +0.000 |
| 485 | -8.333 | -29.167 | +0.000 | +29.167 |
| 486 | +0.000 | +0.000 | +0.000 | +0.000 |
| 488 | +0.000 | +0.000 | +0.000 | +0.000 |
| 492 | -6.250 | +0.000 | +0.000 | +0.000 |
| 513 | +0.000 | +0.000 | +0.000 | +0.000 |
| 514 | -37.500 | +0.000 | -25.000 | -25.000 |
| 518 | -6.250 | +6.250 | +0.000 | -6.250 |
| 526 | +0.000 | +0.000 | +0.000 | +0.000 |
| 536 | +0.000 | -8.333 | -8.333 | +0.000 |
| 552 | +6.250 | -6.250 | -6.250 | +0.000 |
| 556 | -6.250 | -6.250 | -6.250 | +0.000 |
| 557 | +0.000 | +6.250 | +6.250 | +0.000 |
| 566 | -6.250 | -6.250 | -6.250 | +0.000 |
| 576 | +0.000 | -6.250 | -6.250 | +0.000 |
| 597 | +0.000 | +0.000 | +0.000 | +0.000 |
| 598 | -6.250 | -6.250 | -6.250 | +0.000 |
| 602 | -12.500 | +0.000 | +0.000 | +0.000 |
| 606 | +0.000 | +8.333 | +8.333 | +0.000 |
| 607 | +0.000 | +0.000 | +0.000 | +0.000 |
| 609 | +6.250 | +12.500 | +6.250 | -6.250 |
| 619 | +0.000 | +0.000 | +0.000 | +0.000 |
| 627 | +0.000 | +0.000 | +0.000 | +0.000 |
| 633 | -6.250 | -12.500 | -12.500 | +0.000 |
| 648 | +0.000 | +0.000 | +0.000 | +0.000 |
| 649 | +0.000 | +0.000 | +0.000 | +0.000 |
| 660 | +0.000 | -6.250 | -6.250 | +0.000 |
| 663 | +12.500 | +12.500 | +12.500 | +0.000 |
| 664 | +6.250 | +0.000 | +0.000 | +0.000 |
| 673 | +0.000 | +6.250 | +6.250 | +0.000 |
| 685 | +0.000 | +0.000 | +0.000 | +0.000 |
| 686 | +16.667 | +0.000 | +0.000 | +0.000 |
| 698 | -6.250 | +6.250 | +6.250 | +0.000 |
| 700 | +0.000 | +0.000 | +0.000 | +0.000 |
| 711 | -12.500 | -12.500 | -12.500 | +0.000 |
| 712 | -6.250 | -6.250 | -6.250 | +0.000 |
| 728 | +8.333 | +6.250 | +14.583 | +8.333 |
| 737 | +0.000 | +0.000 | +0.000 | +0.000 |
| 748 | +8.333 | +8.333 | +8.333 | +0.000 |
| 750 | -12.500 | -12.500 | +0.000 | +12.500 |
| 762 | +0.000 | -6.250 | -6.250 | +0.000 |
| 767 | +6.250 | +0.000 | +0.000 | +0.000 |
| 769 | +6.250 | +0.000 | +12.500 | +12.500 |
| 772 | +0.000 | -6.250 | -6.250 | +0.000 |
| 778 | -25.000 | -25.000 | +0.000 | +25.000 |
| 782 | -16.667 | +2.083 | +2.083 | +0.000 |
| 788 | -2.083 | +0.000 | +0.000 | +0.000 |
| 806 | +0.000 | +0.000 | +0.000 | +0.000 |
| 808 | +0.000 | +0.000 | +0.000 | +0.000 |
| 813 | -6.250 | +0.000 | +0.000 | +0.000 |
| 818 | +29.167 | +0.000 | +0.000 | +0.000 |
| 825 | +0.000 | +0.000 | +0.000 | +0.000 |
| 834 | -18.750 | -18.750 | -18.750 | +0.000 |
| 859 | +0.000 | +0.000 | +0.000 | +0.000 |
| 864 | +0.000 | +6.250 | +0.000 | -6.250 |
| 870 | +6.250 | +0.000 | +6.250 | +6.250 |
| 894 | +0.000 | +0.000 | +0.000 | +0.000 |
| 895 | +12.500 | +18.750 | +18.750 | +0.000 |
| 898 | +0.000 | +0.000 | +0.000 | +0.000 |
| 909 | +0.000 | +0.000 | +0.000 | +0.000 |
| 910 | +6.250 | +6.250 | +6.250 | +0.000 |
| 915 | +2.083 | -14.583 | -14.583 | +0.000 |
| 936 | -6.250 | +6.250 | +6.250 | +0.000 |
| 938 | +6.250 | -6.250 | -6.250 | +0.000 |
| 944 | +0.000 | +6.250 | +0.000 | -6.250 |
| 947 | +12.500 | +12.500 | +18.750 | +6.250 |
| 952 | +0.000 | +6.250 | +6.250 | +0.000 |
| 955 | -6.250 | +0.000 | +0.000 | +0.000 |
| 960 | +6.250 | +0.000 | -12.500 | -12.500 |
| 978 | +0.000 | +0.000 | +0.000 | +0.000 |
| 990 | +0.000 | +0.000 | +0.000 | +0.000 |
| 999 | +18.750 | +6.250 | +6.250 | +0.000 |
| 1021 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1033 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1037 | +12.500 | +12.500 | +12.500 | +0.000 |
| 1056 | +16.667 | +25.000 | +25.000 | +0.000 |
| 1057 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1079 | +4.167 | -25.000 | -25.000 | +0.000 |
| 1102 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1105 | -12.500 | +0.000 | +0.000 | +0.000 |
| 1120 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1125 | -12.500 | -12.500 | -12.500 | +0.000 |
| 1137 | -12.500 | +0.000 | +0.000 | +0.000 |
| 1138 | +6.250 | +0.000 | +0.000 | +0.000 |
| 1161 | -6.250 | -6.250 | -6.250 | +0.000 |
| 1170 | +0.000 | -6.250 | -6.250 | +0.000 |
| 1180 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1182 | -6.250 | -6.250 | -6.250 | +0.000 |
| 1187 | +12.500 | -12.500 | -12.500 | +0.000 |
| 1196 | -18.750 | -18.750 | -18.750 | +0.000 |
| 1197 | +12.500 | +0.000 | +0.000 | +0.000 |
| 1215 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1225 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1227 | +0.000 | -6.250 | +0.000 | +6.250 |
| 1228 | -25.000 | +0.000 | +0.000 | +0.000 |
| 1233 | -18.750 | -25.000 | -6.250 | +18.750 |
| 1242 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1255 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1260 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1264 | -6.250 | +0.000 | +0.000 | +0.000 |
| 1290 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1293 | +6.250 | +0.000 | +12.500 | +12.500 |
| 1313 | -6.250 | -6.250 | +0.000 | +6.250 |
| 1314 | +0.000 | +6.250 | +0.000 | -6.250 |
| 1319 | +0.000 | +6.250 | +6.250 | +0.000 |
| 1336 | +6.250 | -12.500 | -12.500 | +0.000 |
| 1338 | +0.000 | +6.250 | +6.250 | +0.000 |
| 1350 | +0.000 | -6.250 | -6.250 | +0.000 |
| 1357 | +0.000 | +6.250 | +6.250 | +0.000 |
| 1364 | +0.000 | +0.000 | +6.250 | +6.250 |
| 1367 | +0.000 | +6.250 | +6.250 | +0.000 |
| 1374 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1378 | +12.500 | -12.500 | -12.500 | +0.000 |
| 1380 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1395 | -6.250 | +0.000 | -6.250 | -6.250 |
| 1407 | +12.500 | +18.750 | +18.750 | +0.000 |
| 1408 | +6.250 | +12.500 | +0.000 | -12.500 |
| 1420 | +6.250 | +6.250 | -6.250 | -12.500 |
| 1422 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1444 | +16.667 | +8.333 | +8.333 | +0.000 |
| 1452 | -6.250 | -6.250 | -6.250 | +0.000 |
| 1458 | -12.500 | -12.500 | -12.500 | +0.000 |
| 1469 | +12.500 | +6.250 | +6.250 | +0.000 |
| 1472 | -12.500 | -12.500 | -12.500 | +0.000 |
| 1478 | +6.250 | +6.250 | +12.500 | +6.250 |
| 1481 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1512 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1534 | +37.500 | +25.000 | +12.500 | -12.500 |
| 1537 | +0.000 | -12.500 | -12.500 | +0.000 |
| 1538 | +0.000 | -6.250 | +0.000 | +6.250 |
| 1543 | -25.000 | -37.500 | -37.500 | +0.000 |
| 1556 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1558 | +0.000 | +6.250 | +12.500 | +6.250 |
| 1559 | +6.250 | +6.250 | +6.250 | +0.000 |
| 1564 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1576 | +0.000 | +0.000 | +0.000 | +0.000 |
| 1584 | -12.500 | +6.250 | +6.250 | +0.000 |
| 1590 | +0.000 | -50.000 | -50.000 | +0.000 |
