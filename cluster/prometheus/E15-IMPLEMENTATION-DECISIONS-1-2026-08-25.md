# E15 implementation decisions 1

Date: 25 August 2026  
Status: data-preflight technical record; no model training has begun

## Initial immutable data snapshot and job 299195

The initial data-only snapshot was
`gdp-cem-e15-data-984098235d86745b`, with source-manifest SHA-256
`984098235d86745b00b8a663f26f1672a9590389e39950bee371c15316d2a11c`.
Its static preflight passed four unit tests.

Both array cells of job `299195` stopped before row selection and before any
output cache or structural result was completed. The selector correctly built
the episode-role map from eligible E14 `P1_train` episodes only, but then
attempted to look up every row in the 440,000-row upstream cache, including
excluded E14 `P1_val` episode identifiers. The first excluded identifier
raised `KeyError`.

The correction initializes the per-row assignment to a sentinel and performs
episode-role lookup only at eligible `role == 0` positions. All later cell
masks already require eligibility, so excluded rows remain unselectable. A
regression test now includes upstream `role == 1` rows whose episode IDs are
absent from the eligible lookup and proves that no such row is selected.

This is an input-indexing correction only. It does not change the frozen split
hash, quotas, task, cell, action transform, data source, protected-data rule,
or any scientific threshold. Job `299195` produced no model, proposal,
Le-WM cost, success value, or usable cache. Its failed output locations are
preserved. The replacement requires a new immutable snapshot and a new output
root.
