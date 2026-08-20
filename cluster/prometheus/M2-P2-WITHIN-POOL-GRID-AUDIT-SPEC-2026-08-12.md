# M2 P2 within-pool grid reanalysis specification

Date frozen: 12 August 2026

## Scope

Read only the completed PushT and TwoRoom P2 true-score selection artifacts.
Do not retrain, rescore a candidate, read P3/P4, or change an original selected
configuration. This is a post-hoc development diagnostic prompted by the
finding that the original global AUROC objective was poorly aligned with CEM's
within-query choice.

## Frozen analysis

For all ten already scored M2 configurations—width in `{512, 1024}` and sigma
in `{0.1, 0.25, 0.5, 0.75, 1.0}`—average the three frozen raw-score replicas
and report:

- globally pooled AUROC;
- pair-weighted within-pool AUROC over mixed-label pools;
- macro mixed-pool AUROC;
- pool-centered global AUROC; and
- failure-rate reduction from selecting the lowest-scored top 1, 4, and 8
  candidates per pool.

Select a descriptive within-pool configuration separately for each
environment by maximum pair-weighted within-pool AUROC, breaking exact ties by
narrower width and then smaller sigma. This selection is explicitly
selection-biased and cannot become a new frozen thesis setting from this
analysis.

Before viewing the full TwoRoom grid, also freeze a transfer diagnostic:
select the configuration using PushT P2 within-pool AUROC alone, then report
that same configuration's TwoRoom P2 metrics. Conversely, report the original
TwoRoom globally selected configuration on PushT. No reciprocal tuning is
allowed in the transfer diagnostic.

## Frozen descriptive flags

- `original_global_and_within_selection_match`: the original configuration is
  also the within-pool maximizer for that environment.
- `any_shared_configuration_above_0_60`: at least one fixed width/sigma pair
  has pair-weighted within-pool AUROC above `0.60` in both environments.
- `pusht_selected_transfer_above_0_60`: the PushT-within-pool-selected pair has
  TwoRoom within-pool AUROC above `0.60`.

These are search diagnostics, not hypothesis tests. With only three PushT and
four TwoRoom mixed pools, no grid maximum or threshold crossing is evidence of
generalization without a new untouched candidate set or paired closed-loop
test.

