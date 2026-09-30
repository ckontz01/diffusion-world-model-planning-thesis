# Historical timing reconciliation

Raw authenticated records take precedence. The authoritative compact ledger
is [HISTORICAL-TIMINGS-VERIFIED.json](HISTORICAL-TIMINGS-VERIFIED.json), with
129 records, complete artifact/source hashes, configurations, GPU/runtime,
measurement scopes and units. `HISTORICAL-TIMINGS.json` is the retained first
curation pass with a corrected task-label extraction defect, not the canonical
ledger. The old published reports are preserved at the base commit.

## D1 dedicated latency — scorer seed 6101, planner seed 7101

| Task / job | ACID checker ms | Three-noise DTV checker ms | ACID complete cost ms | DTV complete cost ms | ACID CEM ms | DTV CEM ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| PushT / 297060 | 4.014080 | 4.205568 | 58.400959 | 58.526159 | 1764.772400 | 1766.830627 |
| Reacher / 297119 | 4.006272 | 4.179984 | 57.891167 | 58.158527 | 1746.040527 | 1753.956055 |
| Cube / 297084 | 4.028416 | 4.182528 | 59.259247 | 59.979792 | 1791.947632 | 1810.920166 |

Table values are rounded displays; the JSON retains raw precision. Each
checker/cost call uses one saved context, 300 candidates × 5 transitions =
1,500 transitions, after 20 warmup calls, then 100 CUDA-event measurements.
Complete CEM uses 300 candidates, 30 rounds and 30 elites: 9,000 sequences /
45,000 predicted transitions per solve; one warmup and 10 timed solves.
No loading/physics is in these component/solver timers. Source: original
`benchmark_latency.py`, core 52acea… and frozen diagnostics, RTX 6000 Ada,
Python 3.11.10, torch 2.5.1+cu121, stable-worldmodel 0.0.6 on gpu09.cluster.
These are medians, not allocation durations or a single throughput pass.

The DTV checker is approximately 0.1915/0.1737/0.1541 ms **slower** than ACID.
ACID/DTV speed ratios are about .954/.958/.963, not a speedup. Whole CEM is
approximately 2.058/7.916/18.973 ms slower for DTV (0.117/0.453/1.059%).
Plain and forward whole-solver medians, respectively: PushT 1640.205/1680.394
ms; Reacher 1621.710/1668.370 ms; Cube 1653.026/1712.401 ms. Forward checker
medians are about 1.25 ms; retaining simpler controls is essential.

These dedicated timings are three-noise λ=.07, **not** the v3 λ=.005
deployment and **not** the D1 σ=.25 ablation.

| Separate single-environment episode wall benchmark | Plain s | ACID s | Three-noise DTV s | Forward s |
| --- | ---: | ---: | ---: | ---: |
| PushT / 297061 | 6.172595 | 6.397940 | 6.432349 | 6.263914 |
| Reacher / 297163 | 6.152149 | 6.428438 | 6.444074 | 6.274270 |
| Cube / 297085 | 6.596097 | 6.865300 | 6.874137 | 6.735570 |

These are five measured fresh single-environment episodes after one warmup,
with synchronized wall time around `evaluate_from_dataset`: reset, saved-data
preprocessing, CEM/replanning, environment steps and native termination. They
are not additive to the component table. Required operational host work is
included. No new episodes were executed in this preparation.

Single-noise .25, population 300, λ=.07 historical successes are PushT
90.28%, Reacher 83.33%, Cube 77.78%, equal-task 83.80%, each 24 starts ×
three declared seed pairs. All nine exact execution summaries/checkpoint
hashes/configurations were recovered, not inferred from a report label.
They include 24-environment evaluator elapsed totals, 1,440 cost calls per
run; these are retained in [SINGLE-NOISE-EXECUTIONS.json](SINGLE-NOISE-EXECUTIONS.json).
**Dedicated σ=.25 checker, single-environment episode and complete-solver
latency remain unavailable.** Batched evaluator totals cannot fill that gap.
Do not attach the σ=.25 successes to the three-noise latency table.

## v3 Stage A — large offline batch, not a planner

Reported across all three tasks × scorer seeds 6101/6102/6103: legacy DTV
0.04260 s vs reconstructed ACID 0.09652 s per **15,000 candidate sequences**
(50 pools × 300, 75,000 transitions). The reported offline throughput ratio
is about 2.266×, absolute batch-time saving 53.92 ms. These are rounded means
of nine one-pass timings, not repeated-call medians or online latency.
Individual records, including all unfavorable values, remain in the ledger.

`score_acid_alt_d2_task.py` first runs one 300-sequence warmup pool, then
synchronizes CUDA before and after `perf_counter` around one complete scorer
pass. Le-WM rollouts, checkpoint loading, saved-artifact deserialization and
statistic loading are excluded. CPU work **inside** the literal callable is
included. DTV does three epsilon predictions per transition, 225,000 network
pair evaluations, fixed shared noise generated outside the hot timer and
normalized latents. ACID does 75,000 one-step transformer evaluations;
independent CPU Gaussian noise is generated inside its callable, then moved
to CUDA, standardized action output is inverse-transformed and reduced.

Amendment 3's executed closure 2c8f… uses chunks ≤8,192 **transitions**, not
8,192 candidate sequences. Both literal DTV and ACID use this chunk interface;
ACID generates its full noise tensor before chunking. Its earlier oversized
attention batch failed before outcomes, and that record is not a latency
success. DTV's fixed bank and full-pass scores were checked against the older
shared-score artifact at rtol/atol 1e−6. The original v3 lambda .005 controls
selection/combined cost, not the standalone raw-cost timer. Stage B never ran.

Source-level differences can plausibly affect latency: 1,500 vs 75,000
transitions, wrapper vs flattened/chunked literal callable, common vs
independent ACID draws, event timing vs synchronized host timing, retained
CPU diagnostic copies and different aggregation. These are verified
differences, **not a causal attribution or proof of why the ordering reverses**.
No division of .04260 s by 50 is reported as a production-call measurement.

## E3 boundary: different models

[E3-TIMINGS.json](E3-TIMINGS.json) retains all 54 per-task/seed raw execution
durations and their source/runtime identities. Every run is 50 episodes,
3,000 cost calls = 900,000 candidate sequences / 4,500,000 transitions.
There is no dedicated scorer timing warmup: these are evaluator totals
including physics, with end synchronization, not complete-CEM microbenchmarks.

Published mean seconds per 50-episode run (range over nine runs): plain
369.60 (348.48–381.79), ACID 387.05 (368.37–407.10), forward 373.55
(350.98–390.71), RDX 562.33 (538.03–592.45), AE 560.54
(535.43–592.71), shuffled AE 560.03 (538.07–589.11).
RDX/AE use .25/1/4 and eight draws, conditional/unconditional work (240
network pairs per candidate), not the requested epsilon DTV (15) or .25
single-noise DTV (5). This boundary provides no DTV speed claim. E3's reported
7.03 evaluator GPU-hours and 9.39 allocation-hours differ because allocation
includes setup; neither is latency for one planning decision.

## E6D existing evaluator totals, including reused E6 anchors

| Task | continuous ACID s | all-gate ACID s | all-gate forward s | true RDX s | shuffled RDX s |
| --- | ---: | ---: | ---: | ---: | ---: |
| PushT | 372.277 | 377.377 | 350.248 | 542.877 | 540.674 |
| Reacher | 365.057 | 369.483 | 373.592 | 545.649 | 542.863 |
| Cube | 400.581 | 548.262 | 541.093 | 566.157 | 687.316 |

Displayed rounding only; exact totals are in the ledger. Each is one
50-episode evaluator, 3,000 cost calls, population 300/horizon 5, scorer 6101 /
planner 8301. GPU/runtime and source hashes accompany every record. ACID
continuous/true RDX are authenticated reused E6 anchors, not new E6D
measurements. New E6D controls come from the three-per-task original job
directories; stored runtime allocation identifiers are retained verbatim,
even when directory labels differ. No retrospective relabeling or rerun.

The evaluator uses wall time around execution with final synchronization;
model loading is before this boundary, while environment/replanning work is
inside. No separate dedicated warmup or per-call CUDA-event fields exist.
Cube's totals are unfavorable and must not be averaged away. None of these
is a raw epsilon DTV candidate and E6D is **not** in the future profiling grid.

## Conditional engineering bound, not a measured decomposition

There is no proven additive set of measured component medians: for example,
PushT isolated rollout + checker medians are not equal to its measured
complete-call median. Therefore no empirical exact eliminated-checker saving
is asserted. Under the strong hypothetical assumptions that each of 30
serialized rounds spends the isolated ACID median on the critical path,
trajectories/shared work are unchanged and all other costs remain fixed,
removing the checker entirely could save approximately 120.42/120.18/120.85
ms per PushT/Reacher/Cube solve, or 6.82/6.88/6.74% of their ACID CEM medians.
This is a conditional budget proxy, not an independently measured upper
bound or a proposal to remove a comparator. Do not subtract unmatched
episode durations to obtain it. No energy/training-cost saving is inferred.

## Decision

Artifacts are recoverable and permit a narrow timing test. Existing comparable
three-noise D1 measurements **do not support a planning-cost efficiency lead**;
the attractive v3 observation is offline throughput. Candidate A's exact
planning weight/RNG binding and Candidate B's dedicated latency remain
unmeasured. They are worth at most the proposed bounded test, not a new
success campaign or method-promotion claim.
