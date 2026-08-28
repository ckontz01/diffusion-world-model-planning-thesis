# E19 implementation changelog

## 28 August 2026 — Prometheus QoS wall-time correction

The first immutable snapshot was
`gdp-cem-e19-2fcb443bb41702a3`, with source-manifest SHA-256
`2fcb443bb41702a37f64a7033ce77893f1bd8f3aee55e69b38cfddb8347f3c03`.
Its submission created jobs 299644–299648. No job started and no evaluator or
performance artifact was created. Prometheus reported
`QOSMaxWallDurationPerJobLimit` because the `normal` QoS has `MaxWall=1-00:00:00`,
while the preparation wrapper requested 48 hours and the evaluation wrapper
requested 36 hours. The complete dependency chain was cancelled before
execution.

The only correction is to request 24 hours for both affected wrappers. This
does not change source models, checkpoints, datasets, manifests, methods,
cells, seeds, horizons, candidates, CEM rounds, schedules, budgets, outputs,
gates, or analysis. The failed snapshot and scheduler records remain preserved.
No protected data or performance metric was read.
