# Exact observed-angle endpoint — conditional authorization

Reviewed base `183b8b785cd151c5d9f3d97edc10807f7599f633` and both prior
packages/receipts/disabled templates are preserved, not overwritten.

Per `docs/bottleneck/ANGLE-GUARD-20260914.md`, observed post-action and initialized
native angles admit exactly `[0, float64(2*pi)]`, inclusive at hex
`0x1.921fb54442d18p+2`. Requested initial and goal angles remain canonical
`[0,2*pi)`. Nonfinite, negative and strictly above-endpoint observations fail.
The existing reset comparison remains rtol0/atol1e-10. No epsilon, isclose,
clipping, modulo normalization, predicate or threshold change is introduced.

Boundary tests cover zero, exact endpoint, adjacent representable values,
invalid values, strict canonical admission, initialized observation admission,
and preservation of evidence bytes and native flags. The first-chunk/final-
budget successes and all previous relevant synthetic regressions remain.
No historical inventory, real-model inference or simulation was needed.

`ANGLE-TEST-RESULTS.json` and `ANGLE-EXPORTED-TESTS.json` record checkout and
exported-package tests. `ANGLE-PACKAGE.json` records new source/input/archive
hashes; input identities and all scientific settings/caps are unchanged.
The new source directory and tar are named `preparation-angle-20260918` under
the designated THESIS_SSD LGP1 backup directory. Generated approval remains
disabled. Any execution uses a separate `EXECUTION-APPROVAL.json` binding actual
hashes and the user's conditional authorization, only after publication and
exported tests pass. Execution progress belongs in `EXECUTION-LAUNCH.md`.

The user conditionally authorizes the existing fixed cache, six fits, eight
technical and384 main episodes:203 GPU allocations/336000 seconds and one
4CPU8GiB7200s CPU job, unchanged12GB storage/subcaps. No retries or resumes.
Technical failure requires a scoped decision, not silent repair or relaunch.
