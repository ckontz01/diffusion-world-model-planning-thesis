# M2v2 P1/P2 feasibility specification (frozen before execution)

Date frozen: 2026-08-12

## Purpose and scope

This is one bounded redesign of the auxiliary diffusion feasibility score after the
original M2 was found to learn real D25 conditional structure but not to rank
imagined candidates robustly within CEM queries. It is exploratory P1/P2 work only.
It does not alter the original M2 artifacts, the locked P3/P4 protocol, or any
reported confirmatory result.

The test asks whether a conditional-versus-unconditional diffusion contrast removes
query-level target-density effects and produces a planner-relevant within-query
ordering. It does not claim that the contrast is an exact normalized likelihood.

## Frozen model pair

- Conditional member: the existing true-condition M2 checkpoint, width 1024, for
  seeds 20260728, 20260729, and 20260730 in each environment.
- Unconditional member: a new capacity-matched copy of the same 4-layer Mish MLP,
  trained on the same genuine P1 D25 target pairs, optimizer, sigma schedule,
  early-stopping rule, seed, and standardized latent space. Its source input is
  hard-zeroed on every training, validation, and scoring call.
- The unconditional member is not the earlier mismatched-source null. It models
  target denoising without source information.
- Width 1024 is fixed for both environments. No width selection is performed.
- No world-model weights are changed.

## Frozen raw score

For source latent `z`, proposed D25 subgoal `g`, seed `r`, noise level `sigma`, and
fixed standard-normal draw `epsilon_j`, define

`d[r,sigma](z,g) = mean_j ( ||epsilon_j - eps_cond(g + sigma*epsilon_j, sigma, z)||^2_2 - ||epsilon_j - eps_uncond(g + sigma*epsilon_j, sigma, 0)||^2_2 )`.

The fixed sigma grid is `{0.1, 0.25, 0.5, 0.75, 1.0}` and the already frozen bank
of eight 192-dimensional noise draws is reused. Conditional and unconditional
members receive exactly the same corrupted target on each comparison.

For every seed/sigma cell, mean `mu[r,sigma]` and population standard deviation
`sd[r,sigma]` are estimated from a deterministic 10,000-pair subset of genuine
P1-validation D25 transitions (subset seed 20260812). The M2v2 failure score is

`S(z,g) = mean_{r,sigma} ((d[r,sigma](z,g) - mu[r,sigma]) / sd[r,sigma])`.

Larger values mean less conditional denoising advantage and therefore greater
suspected transition failure. P2 labels, outcomes, and candidate scores are not
used to fit `mu` or `sd`. Every `sd` must exceed `1e-6`.

## Frozen online transformation and intervention gate

For each high-level CEM population independently, convert `S` to an exact midrank
failure penalty in `[0,1]`: the lowest score receives 0, the highest receives 1,
and exact ties receive their average rank. The augmented high-level cost is

`released Hi-LeWM nominal cost + weight * within-population M2v2 midrank`.

The P2 weight grid remains `{0.25, 0.5, 1.0, 2.0, 4.0}`. There is no Platt map and
no global cross-query calibration.

Every scored population must have raw-score span greater than
`max(1e-7, 1e-7 * max(1, abs(population mean)))`. A failure aborts that task rather
than silently producing a non-interventional constant penalty. Span and unique-score
diagnostics are recorded for every final CEM iteration.

## P2 offline diagnostic

Score the already executed 12 by 64 final-candidate artifact in PushT and TwoRoom.
Report, separately by environment:

- pooled AUROC (descriptive only);
- pair-weighted within-mixed-pool AUROC;
- pool-centered AUROC;
- top-1, top-4, and top-8 failure-rate reductions;
- 10,000 pool-bootstrap 95% intervals;
- comparison with the original selected M2, M1, and M3 values already recorded.

Because only 3/12 PushT pools and 4/12 TwoRoom pools are mixed, this diagnostic may
be imprecise and cannot by itself establish or reject planner utility.

## P2 paired closed loop

Run M2v2 on the same twelve frozen development queries and exact planner/environment
seeds in each environment at all five weights. Report every weight, never pool the
two environments, and select a descriptive environment-specific weight by:

1. greatest success count;
2. then greatest number of paired wins minus losses against B0;
3. then the smaller weight.

Use the existing exact matched B0 execution in PushT. In TwoRoom, the previously
audited zero-slope M2 arm is an exact nominal-cost surrogate only if all recorded
trajectories remain byte-identical across its five weights; otherwise run a fresh
nominal B0 before comparison. Existing M1 and M3 P2 runs provide context and are not
retuned.

## Prefrozen interpretation

The redesign is **operationally promising** only if all of the following hold:

1. no population fails the nonzero-span gate;
2. offline within-pool AUROC is above 0.5 in both environments;
3. offline top-4 failure-rate reduction is positive in at least one environment and
   nonnegative in the other;
4. the selected P2 weight improves over paired B0 by at least two successes in at
   least one environment and loses no more than one success in the other;
5. M2v2 changes at least one trajectory relative to B0 in each environment.

Meeting these rules justifies considering a separately frozen confirmation. It does
not make the thesis claim proven. Failing them means the present likelihood-ratio
form is not a robust alternative to ACID/learned reachability in this harness; the
thesis should pivot to the already specified diagnostic/comparative contribution or
to M3 rather than tuning M2v2 repeatedly on P2.

All unexpected failures, deviations, and reruns are append-only amendments.
