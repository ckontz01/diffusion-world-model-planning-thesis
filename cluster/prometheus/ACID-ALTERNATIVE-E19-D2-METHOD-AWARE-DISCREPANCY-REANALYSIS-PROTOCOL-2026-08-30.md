# E19-D2 method-aware discrepancy reanalysis protocol

Date frozen before any E19-D2 classification output: 30 August 2026

## Status and purpose

E19-D2 is a separately named, analyzer-only correction of the failed E19
official-SAGE discrepancy diagnostic. It does not amend E19's terminal decision
`stop_native_reproduction_failed`, and it does not rename or reinterpret the
first discrepancy diagnostic as passed.

Static inspection identified a deterministic defect in the frozen analyzer.
Its `trace_gate()` required `history_latents`, `final_goal_latents`, and a local
goal event for every method. Official PushT `base_cem`, however, has neither a
subgoal generator nor an action prior: `_local_goal_latents()` returns the final
goal directly, `GaussianCEM.solve()` skips generator warmup, and the execution
path does not call `_history_latents()`. The prespecified PushT `base_cem`
sentinel therefore could not pass the original unconditional conjunction even
when official execution was correct.

This defect was derived from the frozen analyzer and pinned official SAGE
source without opening any sealed diagnostic result, trace, bank, comparison,
or analysis output.

## Immutable parents

- E19 terminal decision: `stop_native_reproduction_failed`.
- Parent discrepancy snapshot:
  `/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0`.
- Parent source-manifest SHA-256:
  `e347bc087381ecf0902581e8225165dbd64c887eba661b74b064c09d4e13d7fa`.
- Parent protocol SHA-256:
  `e420dca314038141caa30cadf0fe67ba649e53803d393e85a52c5a87a321f319`.
- Parent analyzer SHA-256:
  `3ddecca36b538509a7664dd5bfdaa12fd6ae007e788a909c4a01f0a11811c710`.
- Parent raw run root:
  `/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19/discrepancy-diagnostic-run-20260829-e347bc08`.
- Official SAGE commit:
  `8219029fd52e89157e05aebb998ab26f0ef46966`.
- Official SAGE tree:
  `0c64066eeac97c27fee382c1879bb26968b3fd56`.

The ten checksum-verified sentinel directories and the checksum-verified
fixed-bank comparison directory are the only scientific inputs reused from the
parent diagnostic. The failed parent's `analysis/` directory, including its
`DISCREPANCY-AUDIT.json`, is forbidden input and must never be opened, copied,
hashed, or consumed by E19-D2.

No episode is rerun. Checkpoints, planner settings, expected values, tolerance,
sentinels, repeats, manifests, E19 result files, comparison banks, traces, and
the parent comparison output are immutable.

## Sole correction

Every method must retain final-goal and local-goal evidence. History-event
semantics become method-aware:

- `base_cem` must contain no `history_latents` event;
- `far_goal_prior_cem`, `lewm_generator`, `generator_prior_top`, and `sage`
  must contain at least one `history_latents` event; and
- an unknown method fails validity.

All other parent trace checks, Cube-cache checks, comparison definitions,
mismatch definitions, decision rules, and E20 authorization rules remain
unchanged. The byte-identical parent analyzer is imported and its
`trace_gate()` function alone is replaced with this preregistered method-aware
version.

Before freezing, regression tests must prove that a complete history-free
`base_cem` trace passes, an unexpected `base_cem` history event fails, a
history-free `sage` trace fails, and a complete `sage` trace with history
passes.

## Stage A: readable validity only

Stage A reads the checksum-verified raw inputs and writes only
`VALIDITY-ONLY.json` plus its adjacent `sha256.txt`. The JSON may contain only a
kind label, `all_passed`, these six Boolean gates, and `failed_checks`:

- `bank_hash_valid`;
- `trace_schema_valid`;
- `method_event_semantics_valid`;
- `identity_hashes_valid`;
- `comparison_schema_valid`; and
- `forbidden_read_flags_valid`.

It must not contain success rates, costs, ranks, elite identities, candidate or
latent values/hashes, cache values, transport magnitudes, mismatch results, or
any E20 classification. `failed_checks` may name exact technical categories and
sentinel/repeat identities. This file is explicitly readable after checksum
validation even if Stage A fails.

If any Stage-A Boolean is false, E19-D2 stops. Stage B must not run. The named
technical failure may motivate another separately prospective analyzer revision
only if its correction is objective and output-independent.

## Stage B: sealed classification

Stage B runs only after Stage A terminates successfully and its adjacent
checksum verifies. It executes the byte-identical parent analyzer in a new,
previously nonexistent output directory against the parent raw snapshot and
raw run root, after installing only the frozen method-aware `trace_gate()`.

The parent mismatch classes remain exactly:

1. `exact_repeatability`;
2. `compatibility_vs_official_runtime`;
3. `cube_generated_goal_cache`; and
4. `pusht_jpeg_transport_elite_membership`.

The parent E20 rule remains exact. Only one internally valid, uniquely
attributable, mechanically correctable mismatch among the latter three can
authorize drafting a corrected E20 protocol. E19-D2 never launches E20
automatically. Zero mismatches or multiple/non-unique mismatches forbid E20 and
may produce the parent's author-evidence packet for user review. E19-D2 does
not contact authors automatically.

Before Stage B completes successfully, no Stage-B JSON, TSV, author packet, or
scientific field may be opened. Scheduler state, exit codes, file existence,
byte counts, and checksums are permitted. Logs may be opened only to diagnose
an exact technical execution failure after that job is reported.

After Stage B succeeds, every adjacent checksum must verify before the aggregate
classification is read. Independently validate the parent/D2 source and
protocol hashes, ten-run/500-episode identity, method-aware trace semantics,
comparison schema, forbidden-read flags, unchanged parent mismatch definitions,
and the E20 decision rule before explaining zero, one, or multiple mismatch
classes.

## Prohibitions

E19-D2 must never:

- read or reuse the failed parent's analyzer output;
- rerun a sentinel episode or fixed-bank comparison;
- modify official SAGE, checkpoints, tensors, data, planner settings, seeds,
  horizons, candidates, CEM rounds, schedules, budgets, expected values,
  tolerance, manifests, traces, banks, or E19 results;
- access, generate, open, or hash D5, D3/D4 metric artifacts, P3, P4, C1, or I1;
- run E18 against SAGE;
- reinterpret E19 or the parent diagnostic as passed; or
- contact the SAGE authors automatically.
