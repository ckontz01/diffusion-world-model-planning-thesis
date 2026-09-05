# E19-R2 implementation history

## Scope and source inspection

Created branch `e19-r2-restoration-localization` from R1 result commit
`1d11369`. R1 source/results/evidence and historical E18/E19/D2/L1 decisions
are not edited. The three unrelated untracked E12 drafts are excluded.

Inspected pinned SAGE Cube and PushT entry points, the vendored dataset
evaluator, both installed PushT setters/reset implementations, Gymnasium's
passive checker, and the preserved R1 step traces. No new Cube execution
is needed to document R1's additional global seeding.

An initial read-only inspection of the opaque CFFI `cpBody` type's fields
aborted the Python process in the CFFI backend before creating any simulator.
No pointer-layout guessing, private-field write, or retry of that access was
used. The diagnostic records public Pymunk body/contact/shape state and
explicitly leaves private solver caches unavailable. A subsequent safe
module/export inventory reported Pymunk 6.8.0 and Chipmunk
`7.0.3-7a29dcfa49931f26632f3019582f289ba811a2b9`, without accessing bodies.

## Frozen narrow run

Six seed/warning tests passed locally before freezing. Snapshot:
`/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e19-r2-a4320292c95507a9`.
Source-manifest SHA-256:
`a4320292c95507a900bae1dfd43ec45f188300e0efbe3d9707f8ceb17ec84e02`.
All five entries and shell syntax passed verification before submission.
Job **300299** uses run root
`/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19-r2/run-20260905-a4320292`.

The R2 module imports the immutable replacement R1 harness, restricts the
post-restoration action cap to one in process memory, wraps only native
reset/step dispatch, and uses Python line tracing for the unchanged setter.
Explicit seed modes change only base-env reset seed. A delegating Space.step
wrapper records boundaries and calls the original exactly once; integration
functions, checkpoint/model code and production environment files are not
modified. Parent snapshots/data are mounted read-only; only the fresh R2
run directory is writable. No old output is reused as a new execution.

The four reducer tests subsequently passed alongside the six harness tests.
They cover stage uniqueness, role isolation, specified-versus-unspecified
state fields and center-of-mass versus body-origin coordinates.

## Preserved-observation audit

The source/observation audit runs on CPU with no simulator creation. It
verifies the seals of all twelve preserved R1 PushT traces, then classifies
all 180 saved step observations. It stores native source hashes and relevant
source functions alongside the observation values/checks. This is separate
from the new-run information barrier and reads no protected or benchmark
result artifact.

## Main diagnostic outcome and contact extension

Job 300299 completed 0:0 in 6m53s. All 24 interfaces and 24 localization
traces passed seals, identity, cap and setter-boundary coverage checks. All
requested fields were exact before the native physics step. New native pairs
did not recreate the bad R1 reset history, but explicit seed 32 versus 33
produced different block states after the step in both stacks. Within-seed
agreement must not be reported as correctness. Seed 32 itself retains contact
bias; seed 33 did not move the block in these tested restorations.

The source and already-exposed R1 reset envelopes motivated one separately
specified contact reconstruction, not a search for failing random seeds.
Its two geometry/zero-dynamics tests passed before freeze. Snapshot:
`/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e19-r2-contact-ba78531c42633638`;
source-manifest SHA-256
`ba78531c4263363877b2e2ccbbabfb5b53e33316133ffb6e67e3032780b8adfb`.
Job **300300** completed 0:0 in 1m23s, output root
`/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19-r2/contact-20260905-ba78531c`.

All eight probes passed execution and seals. Their fixed seed-32 baseline
was named `neutral_reset` in the trace, but was **not neutral**: it perturbed
the subsequently primed R1 geometry. The final good-geometry body states
match R1; the bad-geometry states have the same contact-dependent displacement
mechanism but residual position differences of 0.00887249 (SAGE) and
0.01287850 (E18) versus R1. This is not exact replay. We preserve the plan,
misnamed trace stage and numerical residuals; no seed-33 replacement was run.

Exact runtime-reported Chipmunk/Munk revision sources were inspected to
interpret bias integration. Private bias values are inferred from measured
center-of-mass/angle increments and the native equations, not claimed as
directly captured. No integration callback was replaced and no physics field
was repaired. Combined execution: 32 initializations, 24 actions and 104
recorded setter physics steps, plus native physics substeps inside actions.

The new result proposes explicit restoration-contract requirements but does
not choose an unvalidated production patch. Static arm-routing inspection is
documented; the conditional native-batch/arm execution is deferred until that
contract is approved. No protected or confirmation data was consumed.

## Final verification

All **41 local tests passed in 23.48 seconds**: 14 new R2 tests and 27
existing R1/E18 tests. Both independent evidence verifiers passed. The main
and contact source manifests and every new artifact seal were rechecked
after execution, alongside immutable R1, discrepancy and E18 parent source
manifests. Shell syntax and git whitespace checks passed. No old R1 source,
plan, evidence or result file was amended. Only new R2 files and README
current-status/history text are included in the result commit.
