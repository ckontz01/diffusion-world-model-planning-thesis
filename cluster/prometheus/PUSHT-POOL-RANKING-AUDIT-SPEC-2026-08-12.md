# PushT candidate-pool ranking audit — frozen post-hoc specification

Date frozen: 2026-08-12  
Scope: read-only diagnosis of the completed PushT P2 and locked P3 scorer artifacts  
Status: post-hoc; no method, threshold, weight, P3 conclusion, or P4 decision may be changed

## Motivation

The operational consumer of a scorer is a planner choosing among candidates from the same current-state query. A globally pooled AUROC can be high merely because pools with difficult source states receive higher scores than pools with easy source states, even if the scorer cannot rank candidates within a pool. This audit measures the within-query information that the planner can actually use.

## Frozen inputs

- P2 null/control and true-score artifact, job 294843. This contains the selected P2 raw scores and labels without rerunning or retuning a scorer.
- Locked P3 scorer audit, job 295115.
- The manifests and checksums associated with both artifacts.

The primary positive class is the existing candidate-level budgeted-attainment failure label. Scores retain their existing direction: larger means more likely to fail.

## Methods reported

Report raw-score ensembles for M1 true, M1 permuted null, M2 true, M2 mismatched-pair null, M2 autoencoder control, M3 true, and M3 shuffled null. Also report the two deterministic G0 scores where present. A three-seed ensemble is the arithmetic mean of raw scores; seed-specific results are retained separately.

## Frozen metrics

For each partition and score:

1. globally pooled candidate AUROC;
2. number of all-success, all-failure, and mixed-label pools;
3. AUROC in each mixed pool;
4. unweighted mean mixed-pool AUROC;
5. pair-weighted within-pool AUROC, weighting each mixed pool by `failures × attainments`;
6. AUROC after subtracting each pool's mean score;
7. Spearman correlation between pool-mean score and pool failure prevalence;
8. fraction of raw-score variance explained by differences between pool means;
9. failure rate among the 1, 4, and 8 lowest-scored candidates in every pool, compared with that pool's overall failure rate.

For the ensemble, use 10,000 whole-pool bootstrap replicates (PCG64 seed 20260812) to obtain 95% intervals for pooled AUROC, pair-weighted within-pool AUROC, and top-1/top-4/top-8 failure-rate reductions. Replicates lacking both global classes or any within-pool positive-negative pair are discarded and counted.

## Frozen interpretation rules

- `pool_structure_limits_global_auroc`: fewer than half of pools contain both label classes.
- `global_signal_without_within_pool_ranking`: pooled ensemble AUROC is at least 0.70 while pair-weighted within-pool AUROC is at most 0.55.
- `useful_top4_ranking`: the lower 95% pool-bootstrap bound for baseline failure rate minus lowest-score top-4 failure rate is above zero.
- `within_pool_ranking_above_chance`: the lower 95% pool-bootstrap bound for pair-weighted within-pool AUROC is above 0.50.

These labels diagnose what the existing experiment measured. They do not invalidate correctly executed data, and they cannot retroactively promote or reject a method. If global and within-pool conclusions differ, future experiments must select hyperparameters using a per-query ranking objective and then test that frozen objective on untouched queries.
