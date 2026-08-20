# TwoRoom P2 candidate-pool ranking audit specification

Date frozen: 12 August 2026

## Scope and boundary

This is a read-only, development-only diagnostic of the completed TwoRoom P2
candidate audit. It reads the immutable P2 calibration artifact from job
`296059`. It must not read a TwoRoom P3 or P4 artifact, alter any scorer,
calibrator, candidate, physical label, planner setting, or frozen promotion
rule, or be presented as a confirmatory result.

The analysis is the direct environment-level replication of the PushT pool
audit frozen earlier on 12 August 2026. Its purpose is to determine whether a
globally pooled failure AUROC measures candidate ordering within a single
planning query or primarily separates easy planning queries from difficult
ones.

## Inputs and methods

Use `audit-and-calibrators.h5` and `manifest.json` from TwoRoom P2 calibration
job `296059`. Verify the HDF5 hash against the manifest before reading scores.
The positive class remains the frozen primary physical budgeted-attainment
failure label.

Evaluate every score array available under these frozen names:

- `M1_true` and `M1_permuted_null`;
- `M2_true`, `M2_mismatched_null`, and `M2_autoencoder_control`;
- `M3_true` and `M3_shuffled_null`; and
- either geometric G0 array if it is present.

For a three-replica learned score, compute each seed separately and use the
arithmetic mean of the three raw scores as the ensemble. Do not refit or
recalibrate a score for this audit.

## Frozen metrics

For each method report:

1. globally pooled candidate AUROC;
2. the number of all-attained, all-failure, and mixed-label pools;
3. AUROC for every mixed-label pool;
4. macro-average mixed-pool AUROC;
5. pair-weighted within-pool AUROC, weighting a mixed pool by
   `failures * attainments`;
6. AUROC after subtracting each pool's mean score;
7. Spearman correlation between pool mean score and pool failure prevalence;
8. between-pool score variance divided by total score variance; and
9. failure-rate reduction from selecting the lowest-scored top 1, 4, and 8
   candidates in every pool relative to that pool's full candidate prevalence.

For each ensemble, use 10,000 whole-pool bootstrap replicates with PCG64 seed
`20260812`. Report percentile 95% intervals for pooled AUROC, pair-weighted
within-pool AUROC, and the three top-k failure-rate reductions. Discard and
count a replicate only when it lacks both global classes or every resampled
pool is single-class.

## Frozen interpretation rules

- `pool_structure_limits_global_auroc`: fewer than half of pools contain both
  label classes.
- `global_signal_without_within_pool_ranking`: pooled ensemble AUROC is at
  least 0.70 while pair-weighted within-pool AUROC is at most 0.55.
- `useful_top4_ranking`: the lower 95% whole-pool-bootstrap bound for baseline
  failure rate minus lowest-score top-4 failure rate is above zero.
- `within_pool_ranking_above_chance`: the lower 95% whole-pool-bootstrap bound
  for pair-weighted within-pool AUROC is above 0.50.

These labels diagnose the P2 measurement only. They cannot select a new
configuration or weight, revise the original PushT or TwoRoom protocol, unlock
a locked partition, or support a publication claim by themselves.

