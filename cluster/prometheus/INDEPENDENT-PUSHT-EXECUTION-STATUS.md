# Independent PushT implementation and live execution status

Status recorded 2026-09-06T00:17:24.631030+00:00.

**Implementation, independent data collection and technical validation are
complete. The full comparative experiment is NOT complete; its first large
stage is executing. No final superiority claim is made.**

## Completed work

- New collector, common six-arm evaluator, frozen analysis, independent outcome
  verifier, dependency-driven Slurm controller, backups and verified-result
  Git exporter are implemented and committed on `independent-pusht-benchmark`.
- 6,000 independent accepted references were generated from15,839 attempts.
  The dataset is a declared weak-policy reachable-goal population, not the
  historical expert-data distribution. Acceptance rules preceded final data.
- All6,000 reference files passed integrity/uniqueness checks. All12,000
  goal-specific reference-action replays (both horizons for every reference)
  passed in CPU job300346. No compared model was used to accept references.
- Twenty-three study/driver/analysis/orchestration regressions passed in the
  pinned cluster environment. Five separate archival safety/hash tests passed.
  Both real array-index handoff tests passed. E18 accepted-driver parity and
  native SAGE model pilots are archived; six common/vendor SAGE preprocessing
  combinations were bit-identical in supplementary model-free checks.
- R3, the historical E18 implementations, trained checkpoints and previous
  scientific results remain unchanged. The three E12 drafts remain untracked.

## Frozen study

Six arms: VAD continuation, greedy VAD300, Gaussian continuation, greedy VAD576,
direct GMM continuation, and released full SAGE. Common fresh physical starts,
goals, environment, two horizons and2H action budgets; native method differences
and SAGE's finite out-of-Box commands are retained and disclosed.

The three primary contrasts are continuation VAD minus greedy300, Gaussian
continuation and SAGE. The intended alternative is+5pp, not an observed+5pp
threshold. Cumulative looks are1,600,3,200 and6,000 distinct reference episodes.
One-sided per-contrast alpha spending is.001/.004/.0116666667 across looks.
The frozen protocol defines success, strong-adverse futility and maximum-sample
stopping. Fixed trained checkpoints and evaluation seeds are clustered within
episodes. Scope/power qualifications remain in the prospective protocol.

## Current execution

Source: `/lustreFS/data/superworld/ckontzias/thesis/snapshots/independent-pusht-4a608e5`.
Study: `/lustreFS/data/superworld/ckontzias/thesis/experiments/independent-pusht/final-20260906-4a608e5`.
Scientific freeze63f0440; launcher-only correction4a608e5.
Collection hash:`3cce1a2b74c84feeece9503dd2873d8db6abd609b546311ed374984ca4d93f68`.

At00:16:26 UTC, array300339 had12 completed tasks,2 running and the remaining
436 pending. Each first-stage task represents64 references under one method/
checkpoint block and both horizons. The first look requires all450 tasks,
57,600 logical runs;12 completed tasks are not a complete paired comparison.
Dependent analysis300340 and controller300341 are queued. The controller can
submit later stages only from the independently verified frozen decision.

The earlier array300327 failed before worker main because the clean container
removed its array-index environment variable. It and dependents300328/300329
were stopped and preserved. The corrected launcher passes the index explicitly;
no final planner had run in the failed array and the dataset was not regenerated.

## Durability and operational limits

All6,000 references and both execution configurations have hash-verified second
copies under `/home/chris/thesis-artifacts/independent-pusht/`. Completed raw
shards can be copied without interpreting outcomes. Final reports/tables are
published by user-owned WSL process11692 only after complete-look independent
verification. It uses existing Git/SSH authentication and can stop on network,
branch, credential or archival errors. Its continued operation requires the
local Windows/WSL machine to remain available. Cluster jobs and raw Lustre
artifacts persist independently of that local archival process.

Slurm controls the submitted computation; the WSL process controls archival.
The live source/protocol, launch records and recovery commands are sufficient
for another authorized session to resume inspection without reconstructing the
conversation. No permanent cron or system service was installed.

See `INDEPENDENT-PUSHT-RECOVERY.md`, `INDEPENDENT-PUSHT-DATA-CARD.md`,
`INDEPENDENT-PUSHT-PROTOCOL.md`, and `independent-pusht-evidence/`.
