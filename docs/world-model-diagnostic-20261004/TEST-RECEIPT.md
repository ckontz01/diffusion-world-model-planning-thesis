# Focused artificial verification

ARTIFICIAL-005 passed all26 component/package tests. ARTIFICIAL-006 exercised the artificial CLI estimator (deliberately adverse oracle fixture); ARTIFICIAL-007 verified finite workload arithmetic. These are implementation checks, not scientific results.

Cumulative scripted-test wall through007:3.3126174999633804s of14,400s. All tests used the native Windows bounded runner, four-core affinity mask15,8GiB job cap, single-thread library variables, hidden CUDA devices. Maximum measured job memory across these attempts69,750,784B. No GPU/Slurm allocations or research access.

All attempts retained:001(18 tests),002(20),003(25 tests, test-only AUTHORIZATION key mismatch),004(25 passed),005(26 passed),006/007 CLI checks. The003 failure was fixed by checking the actual disabled keys, without changing authority; it remains charged. Original started receipts are preserved alongside final receipts. Every new test reserves its full600s before running; no automatic retry.

Metadata reader failure was separately diagnosed: authenticated TSV masters use CRLF; PowerShell strips terminators from stdout. Reconstructing CRLF restores the exact whole-file SHA256. No master changed, no dataset payload was opened, no cluster failure was inferred. Source/row proposal is now authenticated metadata, not an allocation.

Covered: exact native plan retention, matrix action-byte identity, own backbone/layout/history, native sum versus mean, no outcome arguments, same S1, disjoint whole-parent roles, duplicate/tie rules, terminal/absorbing/truncation handling, complete fresh replay, absolute budget, separate tail ownership, independent saved-member/action/endpoint checking, parent-unit uncertainty, all-fail/negative/zero effects, disabled research entry points, and archive membership/no-overwrite/corruption handling.

Missing production bindings are listed in COMPATIBILITY.md; these tests do not certify a native campaign. Subsequent preservation/review accounting is retained separately in dated receipts.
