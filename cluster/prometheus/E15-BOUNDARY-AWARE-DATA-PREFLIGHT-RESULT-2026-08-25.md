# E15 boundary-aware data preflight result

Date completed: 25 August 2026  
Role: structural P1 development data only  
Status: passed; full E15 scientific protocol may now be frozen  
Claim status: no model or performance claim; D5 remains sealed

## Result

The corrected data-only preflight created an episode-disjoint E15 split from
previous E14 `P1_train` rows and verified the common smooth bounded-action
representation. It performed no model training, Le-WM scoring, closed-loop
evaluation, or protected-data read.

| Task | Train rows | Validation rows | Train episodes | Validation episodes | Episode overlap |
|---|---:|---:|---:|---:|---:|
| PushT | 292,500 | 90,000 | 8,860 | 2,927 | 0 |
| Cube | 292,500 | 90,000 | 4,825 | 1,560 | 0 |

Every one of the 45 `(delta,tau)` cells contains exactly 6,500 training and
2,000 validation rows. Every selected row came from E14 `P1_train`. The
released float32 planner transform reproduced every active cached planner
action bit exactly; the maximum inverse round-trip discrepancy was one
float32 unit (`1.1920928955078125e-7`).

## Expert boundary geometry

The structural result confirms why E15 must use expert-relative saturation
checks rather than a universal low boundary rate.

- PushT's source data have a very small tail at or microscopically beyond the
  declared interval. Depending on duration and coordinate, only about
  `0.066%--0.094%` of E15 validation elements require projection.
- Cube uses exact limits legitimately. Across validation durations, projection
  rates are approximately `1.03%--1.06%` on coordinate 0,
  `7.09%--7.29%` on coordinate 1, `20.95%--21.87%` on coordinate 2,
  `9.20%--9.42%` on coordinate 3, and zero on coordinate 4.
- At the trajectory level, Cube's expert fraction within 1% of a limit has a
  mean of about 8%, with 99th percentiles of 36%, 33%, and 31.2% for
  `tau=15,20,25`. PushT's corresponding means are below 0.1% and its 99th
  percentiles are 3.33%, 2.5%, and 4%.
- The finite inverse target has `|u| = 8.664` for projected saturated values.
  This is expected expert structure, not by itself model pathology.

Accordingly, the E15 scientific gate will require generated actions to be
legal and strictly interior, but will bound near-limit and small-Jacobian mass
relative to the frozen expert distribution. This prevents both errors:
rejecting correct Cube behavior and accepting a model that collapses nearly
all mass against a limit.

## Provenance

- Corrected source snapshot:
  `gdp-cem-e15-data-1b97e2286e1237a8`
- Source-manifest SHA-256:
  `1b97e2286e1237a8c758ed5951e9a64433b2e41b4d10a6eb79215dcf8bc1fd46`
- Replacement Slurm array: `299197` (both cells completed `0:0`)
- PushT cache SHA-256:
  `2efc57e077cc6e5a627bf73b8ee50eeb308091d52fb734c71a79eb37279146a9`
- PushT manifest SHA-256:
  `c8af1ddbf5e830a9257dba3a484d9eb10272d20fc11ea0f348080e9443c16dcc`
- Cube cache SHA-256:
  `b48ebb4735662d702289b9da12e55dc31766e8f1f245c1486f50e58cb0fb2994`
- Cube manifest SHA-256:
  `e8c547962238fcd37b463acc0343b997af5525a90116c01b5f9f889fb23fd4a9`

Both output `sha256.txt` manifests verify. The output manifests record
`model_training_performed = false`, `p2_read = false`,
`d3_metric_read = false`, `d4_metric_read = false`, `d5_read = false`,
`protected_p3_p4_c1_i1_read = false`, and `claim_allowed = false`.

The failed initial array `299195` and its technical correction are retained in
[the implementation record](E15-IMPLEMENTATION-DECISIONS-1-2026-08-25.md).
