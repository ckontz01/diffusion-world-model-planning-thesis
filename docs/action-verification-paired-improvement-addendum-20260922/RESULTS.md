# Complete paired-improvement addendum results

All 18 fixed cases are included. Source-data digests match AV0 in 18/18; all 25 accepted AV0 files retain their original bytes. Point metrics, original LTT tests and simultaneous quantiles replay exactly. Predictions use the unchanged full-branch estimator.

The new control accepts at least one threshold in 9/18 cases. Its smallest accepted threshold (or fallback) is identical to conditional-harm LTT in all 18 cases, so the deployed actions and reported test metrics are identical. Shared-error seed 92203 additionally accepts threshold .10 but still deploys threshold 0. This does not demonstrate an improvement over LTT.

## All calibration rule tests

Every rule uses all 512 calibration sources for its success-difference denominator. Only G+L discordant sources enter the binomial p-value. Critical value .05/5=.01. Calibration estimates are selection-affected descriptions, not fresh test evidence.

| Case | Seed | Threshold | G | L | Discordant | Ties | p-value | Accept | Net difference / 512 |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| shared_error | 92201 | 0 | 18 | 0 | 18 | 494 | 3.81469727e-06 | True | 0.0351562 |
| shared_error | 92201 | 0.05 | 12 | 0 | 12 | 500 | 0.000244140625 | True | 0.0234375 |
| shared_error | 92201 | 0.1 | 3 | 0 | 3 | 509 | 0.125 | False | 0.00585938 |
| shared_error | 92201 | 0.2 | 1 | 0 | 1 | 511 | 0.5 | False | 0.00195312 |
| shared_error | 92201 | 0.4 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| shared_error | 92202 | 0 | 25 | 0 | 25 | 487 | 2.98023224e-08 | True | 0.0488281 |
| shared_error | 92202 | 0.05 | 16 | 0 | 16 | 496 | 1.52587891e-05 | True | 0.03125 |
| shared_error | 92202 | 0.1 | 4 | 0 | 4 | 508 | 0.0625 | False | 0.0078125 |
| shared_error | 92202 | 0.2 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| shared_error | 92202 | 0.4 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| shared_error | 92203 | 0 | 19 | 0 | 19 | 493 | 1.90734863e-06 | True | 0.0371094 |
| shared_error | 92203 | 0.05 | 12 | 0 | 12 | 500 | 0.000244140625 | True | 0.0234375 |
| shared_error | 92203 | 0.1 | 7 | 0 | 7 | 505 | 0.0078125 | True | 0.0136719 |
| shared_error | 92203 | 0.2 | 6 | 0 | 6 | 506 | 0.015625 | False | 0.0117188 |
| shared_error | 92203 | 0.4 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| optimistic_search | 92201 | 0 | 4 | 20 | 24 | 488 | 0.999861419 | False | -0.03125 |
| optimistic_search | 92201 | 0.05 | 4 | 18 | 22 | 490 | 0.999572277 | False | -0.0273438 |
| optimistic_search | 92201 | 0.1 | 4 | 15 | 19 | 493 | 0.997787476 | False | -0.0214844 |
| optimistic_search | 92201 | 0.2 | 4 | 15 | 19 | 493 | 0.997787476 | False | -0.0214844 |
| optimistic_search | 92201 | 0.4 | 4 | 9 | 13 | 499 | 0.953857422 | False | -0.00976562 |
| optimistic_search | 92202 | 0 | 10 | 25 | 35 | 477 | 0.99700594 | False | -0.0292969 |
| optimistic_search | 92202 | 0.05 | 10 | 23 | 33 | 479 | 0.993234507 | False | -0.0253906 |
| optimistic_search | 92202 | 0.1 | 9 | 21 | 30 | 482 | 0.991937599 | False | -0.0234375 |
| optimistic_search | 92202 | 0.2 | 9 | 19 | 28 | 484 | 0.982150931 | False | -0.0195312 |
| optimistic_search | 92202 | 0.4 | 7 | 9 | 16 | 496 | 0.772750854 | False | -0.00390625 |
| optimistic_search | 92203 | 0 | 9 | 17 | 26 | 486 | 0.962240651 | False | -0.015625 |
| optimistic_search | 92203 | 0.05 | 8 | 15 | 23 | 489 | 0.953430176 | False | -0.0136719 |
| optimistic_search | 92203 | 0.1 | 8 | 14 | 22 | 490 | 0.933099747 | False | -0.0117188 |
| optimistic_search | 92203 | 0.2 | 8 | 13 | 21 | 491 | 0.905376434 | False | -0.00976562 |
| optimistic_search | 92203 | 0.4 | 6 | 6 | 12 | 500 | 0.612792969 | False | 0 |
| rare_override | 92201 | 0 | 0 | 9 | 9 | 503 | 1 | False | -0.0175781 |
| rare_override | 92201 | 0.05 | 0 | 9 | 9 | 503 | 1 | False | -0.0175781 |
| rare_override | 92201 | 0.1 | 0 | 9 | 9 | 503 | 1 | False | -0.0175781 |
| rare_override | 92201 | 0.2 | 0 | 5 | 5 | 507 | 1 | False | -0.00976562 |
| rare_override | 92201 | 0.4 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| rare_override | 92202 | 0 | 0 | 8 | 8 | 504 | 1 | False | -0.015625 |
| rare_override | 92202 | 0.05 | 0 | 8 | 8 | 504 | 1 | False | -0.015625 |
| rare_override | 92202 | 0.1 | 0 | 8 | 8 | 504 | 1 | False | -0.015625 |
| rare_override | 92202 | 0.2 | 0 | 4 | 4 | 508 | 1 | False | -0.0078125 |
| rare_override | 92202 | 0.4 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| rare_override | 92203 | 0 | 0 | 6 | 6 | 506 | 1 | False | -0.0117188 |
| rare_override | 92203 | 0.05 | 0 | 6 | 6 | 506 | 1 | False | -0.0117188 |
| rare_override | 92203 | 0.1 | 0 | 6 | 6 | 506 | 1 | False | -0.0117188 |
| rare_override | 92203 | 0.2 | 0 | 2 | 2 | 510 | 1 | False | -0.00390625 |
| rare_override | 92203 | 0.4 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| sparse_binary | 92201 | 0 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| sparse_binary | 92201 | 0.05 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| sparse_binary | 92201 | 0.1 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| sparse_binary | 92201 | 0.2 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| sparse_binary | 92201 | 0.4 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| sparse_binary | 92202 | 0 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| sparse_binary | 92202 | 0.05 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| sparse_binary | 92202 | 0.1 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| sparse_binary | 92202 | 0.2 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| sparse_binary | 92202 | 0.4 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| sparse_binary | 92203 | 0 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| sparse_binary | 92203 | 0.05 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| sparse_binary | 92203 | 0.1 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| sparse_binary | 92203 | 0.2 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| sparse_binary | 92203 | 0.4 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| progress_conflict | 92201 | 0 | 39 | 0 | 39 | 473 | 1.8189894e-12 | True | 0.0761719 |
| progress_conflict | 92201 | 0.05 | 34 | 0 | 34 | 478 | 5.82076609e-11 | True | 0.0664062 |
| progress_conflict | 92201 | 0.1 | 22 | 0 | 22 | 490 | 2.38418579e-07 | True | 0.0429688 |
| progress_conflict | 92201 | 0.2 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| progress_conflict | 92201 | 0.4 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| progress_conflict | 92202 | 0 | 42 | 0 | 42 | 470 | 2.27373675e-13 | True | 0.0820312 |
| progress_conflict | 92202 | 0.05 | 28 | 0 | 28 | 484 | 3.7252903e-09 | True | 0.0546875 |
| progress_conflict | 92202 | 0.1 | 10 | 0 | 10 | 502 | 0.0009765625 | True | 0.0195312 |
| progress_conflict | 92202 | 0.2 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| progress_conflict | 92202 | 0.4 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| progress_conflict | 92203 | 0 | 61 | 0 | 61 | 451 | 4.33680869e-19 | True | 0.119141 |
| progress_conflict | 92203 | 0.05 | 40 | 0 | 40 | 472 | 9.09494702e-13 | True | 0.078125 |
| progress_conflict | 92203 | 0.1 | 35 | 0 | 35 | 477 | 2.91038305e-11 | True | 0.0683594 |
| progress_conflict | 92203 | 0.2 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| progress_conflict | 92203 | 0.4 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| sequential_shift | 92201 | 0 | 160 | 0 | 160 | 352 | 6.84227766e-49 | True | 0.3125 |
| sequential_shift | 92201 | 0.05 | 160 | 0 | 160 | 352 | 6.84227766e-49 | True | 0.3125 |
| sequential_shift | 92201 | 0.1 | 160 | 0 | 160 | 352 | 6.84227766e-49 | True | 0.3125 |
| sequential_shift | 92201 | 0.2 | 130 | 0 | 130 | 382 | 7.34683969e-40 | True | 0.253906 |
| sequential_shift | 92201 | 0.4 | 0 | 0 | 0 | 512 | 1 | False | 0 |
| sequential_shift | 92202 | 0 | 162 | 0 | 162 | 350 | 1.71056941e-49 | True | 0.316406 |
| sequential_shift | 92202 | 0.05 | 162 | 0 | 162 | 350 | 1.71056941e-49 | True | 0.316406 |
| sequential_shift | 92202 | 0.1 | 162 | 0 | 162 | 350 | 1.71056941e-49 | True | 0.316406 |
| sequential_shift | 92202 | 0.2 | 139 | 0 | 139 | 373 | 1.43492963e-42 | True | 0.271484 |
| sequential_shift | 92202 | 0.4 | 5 | 0 | 5 | 507 | 0.03125 | False | 0.00976562 |
| sequential_shift | 92203 | 0 | 158 | 0 | 158 | 354 | 2.73691106e-48 | True | 0.308594 |
| sequential_shift | 92203 | 0.05 | 158 | 0 | 158 | 354 | 2.73691106e-48 | True | 0.308594 |
| sequential_shift | 92203 | 0.1 | 158 | 0 | 158 | 354 | 2.73691106e-48 | True | 0.308594 |
| sequential_shift | 92203 | 0.2 | 141 | 0 | 141 | 371 | 3.58732407e-43 | True | 0.275391 |
| sequential_shift | 92203 | 0.4 | 0 | 0 | 0 | 512 | 1 | False | 0 |

## Selected rule on calibration: all 512 sources per case

| Case | Seed | Accepted thresholds | Selected threshold | G | L | Success | Override | Marginal harm | Conditional harm | Sample net diff | Known expected diff |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| shared_error | 92201 | 0, 0.05 | 0 | 18 | 0 | 0.595703 | 0.572266 | 0 | 0 | 0.0351562 | 0.044375 |
| shared_error | 92202 | 0, 0.05 | 0 | 25 | 0 | 0.556641 | 0.683594 | 0 | 0 | 0.0488281 | 0.0440527 |
| shared_error | 92203 | 0, 0.05, 0.1 | 0 | 19 | 0 | 0.539062 | 0.695312 | 0 | 0 | 0.0371094 | 0.0441602 |
| optimistic_search | 92201 | none | baseline fallback | 0 | 0 | 0.558594 | 0 | 0 | undefined | 0 | 0 |
| optimistic_search | 92202 | none | baseline fallback | 0 | 0 | 0.519531 | 0 | 0 | undefined | 0 | 0 |
| optimistic_search | 92203 | none | baseline fallback | 0 | 0 | 0.5 | 0 | 0 | undefined | 0 | 0 |
| rare_override | 92201 | none | baseline fallback | 0 | 0 | 0.791016 | 0 | 0 | undefined | 0 | 0 |
| rare_override | 92202 | none | baseline fallback | 0 | 0 | 0.816406 | 0 | 0 | undefined | 0 | 0 |
| rare_override | 92203 | none | baseline fallback | 0 | 0 | 0.837891 | 0 | 0 | undefined | 0 | 0 |
| sparse_binary | 92201 | none | baseline fallback | 0 | 0 | 0.00976562 | 0 | 0 | undefined | 0 | 0 |
| sparse_binary | 92202 | none | baseline fallback | 0 | 0 | 0.00390625 | 0 | 0 | undefined | 0 | 0 |
| sparse_binary | 92203 | none | baseline fallback | 0 | 0 | 0.00585938 | 0 | 0 | undefined | 0 | 0 |
| progress_conflict | 92201 | 0, 0.05, 0.1 | 0 | 39 | 0 | 0.753906 | 0.851562 | 0 | 0 | 0.0761719 | 0.0851563 |
| progress_conflict | 92202 | 0, 0.05, 0.1 | 0 | 42 | 0 | 0.785156 | 0.853516 | 0 | 0 | 0.0820312 | 0.0853516 |
| progress_conflict | 92203 | 0, 0.05, 0.1 | 0 | 61 | 0 | 0.789062 | 1 | 0 | 0 | 0.119141 | 0.1 |
| sequential_shift | 92201 | 0, 0.05, 0.1, 0.2 | 0 | 160 | 0 | 0.810547 | 1 | 0 | 0 | 0.3125 | 0.3 |
| sequential_shift | 92202 | 0, 0.05, 0.1, 0.2 | 0 | 162 | 0 | 0.828125 | 1 | 0 | 0 | 0.316406 | 0.3 |
| sequential_shift | 92203 | 0, 0.05, 0.1, 0.2 | 0 | 158 | 0 | 0.777344 | 1 | 0 | 0 | 0.308594 | 0.3 |

## Selected rule on test: all 2048 sources per case

| Case | Seed | Accepted thresholds | Selected threshold | G | L | Success | Override | Marginal harm | Conditional harm | Sample net diff | Known expected diff |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| shared_error | 92201 | 0, 0.05 | 0 | 94 | 0 | 0.567871 | 0.577148 | 0 | 0 | 0.0458984 | 0.0453516 |
| shared_error | 92202 | 0, 0.05 | 0 | 91 | 0 | 0.562012 | 0.6875 | 0 | 0 | 0.0444336 | 0.0434985 |
| shared_error | 92203 | 0, 0.05, 0.1 | 0 | 75 | 0 | 0.556641 | 0.675293 | 0 | 0 | 0.0366211 | 0.0421484 |
| optimistic_search | 92201 | none | baseline fallback | 0 | 0 | 0.520996 | 0 | 0 | undefined | 0 | 0 |
| optimistic_search | 92202 | none | baseline fallback | 0 | 0 | 0.519531 | 0 | 0 | undefined | 0 | 0 |
| optimistic_search | 92203 | none | baseline fallback | 0 | 0 | 0.528809 | 0 | 0 | undefined | 0 | 0 |
| rare_override | 92201 | none | baseline fallback | 0 | 0 | 0.787598 | 0 | 0 | undefined | 0 | 0 |
| rare_override | 92202 | none | baseline fallback | 0 | 0 | 0.806641 | 0 | 0 | undefined | 0 | 0 |
| rare_override | 92203 | none | baseline fallback | 0 | 0 | 0.806641 | 0 | 0 | undefined | 0 | 0 |
| sparse_binary | 92201 | none | baseline fallback | 0 | 0 | 0.0151367 | 0 | 0 | undefined | 0 | 0 |
| sparse_binary | 92202 | none | baseline fallback | 0 | 0 | 0.0117188 | 0 | 0 | undefined | 0 | 0 |
| sparse_binary | 92203 | none | baseline fallback | 0 | 0 | 0.0126953 | 0 | 0 | undefined | 0 | 0 |
| progress_conflict | 92201 | 0, 0.05, 0.1 | 0 | 168 | 0 | 0.783203 | 0.853516 | 0 | 0 | 0.0820312 | 0.0853516 |
| progress_conflict | 92202 | 0, 0.05, 0.1 | 0 | 179 | 0 | 0.791992 | 0.877441 | 0 | 0 | 0.0874023 | 0.0877441 |
| progress_conflict | 92203 | 0, 0.05, 0.1 | 0 | 199 | 0 | 0.788574 | 1 | 0 | 0 | 0.097168 | 0.1 |
| sequential_shift | 92201 | 0, 0.05, 0.1, 0.2 | 0 | 585 | 0 | 0.798828 | 1 | 0 | 0 | 0.285645 | 0.3 |
| sequential_shift | 92202 | 0, 0.05, 0.1, 0.2 | 0 | 598 | 0 | 0.805176 | 1 | 0 | 0 | 0.291992 | 0.3 |
| sequential_shift | 92203 | 0, 0.05, 0.1, 0.2 | 0 | 651 | 0 | 0.816406 | 1 | 0 | 0 | 0.317871 | 0.3 |

## Practical comparison averaged over the three fixed seeds

| Case | New accepted cases | New sampled net diff | New known expected diff | Old LTT sampled net diff | Old simultaneous sampled net diff |
|---|---:|---:|---:|---:|---:|
| shared_error | 3/3 | 0.0423177 | 0.0436662 | 0.0423177 | 0 |
| optimistic_search | 0/3 | 0 | 0 | 0 | 0 |
| rare_override | 0/3 | 0 | 0 | 0 | 0 |
| sparse_binary | 0/3 | 0 | 0 | 0 | 0 |
| progress_conflict | 3/3 | 0.0888672 | 0.0910319 | 0.0888672 | 0 |
| sequential_shift | 3/3 | 0.298503 | 0.3 | 0.298503 | 0 |

The sequential-shift numbers concern the original **single intervention with fixed reference tail**. They do not certify repeatedly using the accepted rule in shifted states. No repeated-policy simulation or new run was added. No inference should use candidates, repeated draws or horizons as independent sources.

The known expected difference is available only from this artificial generator. Positive test differences are descriptive observations under fixed fixtures, not a proof of a universal robotics mechanism. No-acceptance cases remain results. The original conclusion is unchanged: **no differentiated treatment yet**.
