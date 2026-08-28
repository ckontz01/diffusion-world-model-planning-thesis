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

## 28 August 2026 — checkpoint download moved to the login node

The second immutable snapshot was `gdp-cem-e19-c97b470100482281`, with
source-manifest SHA-256
`c97b4701004822811ca1483fd03c4a0f6339eee3ae9dfda640fc261040fd72ae`.
Its preparation job 299649 reached compute node `gpu04` and failed before any
checkpoint was downloaded or dataset conversion began because Prometheus
compute nodes cannot reach `huggingface.co`. Jobs 299650–299653 consequently
had unsatisfied dependencies and were cancelled. No evaluator ran and no
performance artifact was produced or read.

The exact six files are now downloaded on the network-enabled login node by
the unchanged pinned release's `scripts/download_checkpoints.py`, at the same
exact Hugging Face revision, and sealed with their release hashes. The compute
preparation job only copies those verified bytes into its unique run root.
This changes transport location only; it does not change any checkpoint,
source, dataset, manifest, method, cell, seed, horizon, planner setting, gate,
or analysis.
