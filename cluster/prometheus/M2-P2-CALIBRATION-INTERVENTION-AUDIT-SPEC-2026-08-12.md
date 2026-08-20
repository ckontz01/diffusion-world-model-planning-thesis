# M2 P2 calibration and planner-intervention audit specification

Date frozen: 12 August 2026

## Scope

This is a read-only P2 diagnostic for the completed PushT and TwoRoom M2
closed-loop development grids. It reads no P3 or P4 artifact and changes no
score, calibrator, weight, candidate, planner, or locked decision.

The planner adds
`weight * mean_seed(sigmoid(raw_score * Platt_slope + Platt_intercept))`
to every candidate's nominal cost. A closed-loop weight grid tests a scorer
only if this term can vary among candidates in a CEM solve. A zero slope for
all three replicas makes the term exactly candidate-constant for every raw
score and every weight, so it cannot change elite ordering.

## Frozen inputs

- PushT calibration job `294843`, M2 weight grid array `294846`, and aggregate
  job `294847`;
- TwoRoom calibration job `296059`, M2 weight grid array `296070`, and
  aggregate job `296071`; and
- the exact online scoring implementation
  `feasibility_augmented_high_cost.py`.

Verify aggregate HDF5 hashes and every M2 task manifest/result-HDF5 hash
before using task diagnostics.

## Frozen measurements

For each environment report:

1. the three M2 Platt raw-score slopes and intercepts from the calibration
   manifest, checked against HDF5 attributes;
2. minimum, maximum, and number of unique calibration-set Platt probabilities;
3. across every M2 weight, query, and recorded final CEM population, the
   failure-probability span `max - min`;
4. the successful-query set at each weight; and
5. exact and maximum-absolute differences in selected high-level subgoals,
   step-current latents, step-subgoal latents, and final states between each
   weight and weight `0.25` on the same query.

## Frozen interpretation

- `constant_platt_calibrator`: all three raw-score slopes are exactly zero.
- `candidate_constant_penalty_by_construction`: the calibrator is constant;
  because the online implementation applies only the stated affine sigmoid
  and seed mean, every candidate receives the same learned penalty.
- `recorded_final_populations_constant`: every recorded candidate probability
  span is at most `1e-7`.
- `weight_outcomes_identical`: all five weights have the same per-query success
  vector.
- `m2_weight_grid_is_non_interventional`: both
  `candidate_constant_penalty_by_construction` and
  `weight_outcomes_identical` are true.

If the last flag is true, that environment's completed M2 weight grid is not
evidence for or against diffusion-assisted planning. It is evidence that the
chosen calibration erased the scorer before the planner could use it.

