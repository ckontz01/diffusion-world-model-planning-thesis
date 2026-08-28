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

## 28 August 2026 — historical LeWM deserialization runtime pinned

The third immutable snapshot was `gdp-cem-e19-31b3938c97265b52`, with
source-manifest SHA-256
`31b3938c97265b52231f37df23addf3c4bf83d31b3e5653969f03bbc74f98460`.
Preparation job 299654 completed the exact checkpoint staging and PushT
HDF5-to-Lance transport. Release-audit job 299655 completed. Identifier-only
audit job 299656 then failed before producing its audit because Python could
not deserialize the versioned LeWM object checkpoint: the pickle refers to the
historical top-level module `jepa`, which was not on `PYTHONPATH`. The dependent
evaluation and analyzer jobs 299657–299658 were cancelled. No evaluator ran
and no performance artifact was produced or read.

The correction pins the historical LeWM runtime repository
`https://github.com/lucas-maes/le-wm.git` at commit
`8edfeb336732b5f3ce7b8b210d0ba370a09e2cac` and tree
`40444957371d400fe9ac24db3f9d453081a35bea`. The freeze procedure archives
only the tracked files from that exact tree into `lewm-runtime/` inside the
immutable E19 snapshot, records the provenance in `FREEZE-AUDIT.json`, and
loads both exact versioned LeWM object checkpoints on CPU before sealing the
snapshot. The identifier audit and official evaluator add only this frozen
runtime directory to `PYTHONPATH`. This restores the class definitions needed
by the existing serialized objects; it does not change SAGE, LeWM parameters,
checkpoints, datasets, manifests, methods, cells, seeds, horizons, candidates,
CEM rounds, schedules, budgets, tolerance, gates, or analysis.

The first corrected immutable snapshot,
`gdp-cem-e19-1861a4ac09089d5e`, was never submitted. Its mandatory
post-freeze identity smoke test exposed a second audit-only defect before any
Slurm job or outcome evaluation: the state-digest helper attempted to reinterpret
a zero-dimensional integer tensor directly as bytes, which PyTorch rejects.
The helper now flattens every contiguous tensor before its byte view, and a
scalar-tensor regression test is part of the frozen wrapper suite. This changes
only deterministic audit hashing; it does not change any model or experiment.

## 29 August 2026 — corrected replacement chain launched

The corrected immutable snapshot is `gdp-cem-e19-e466db24b8ed85ad`, with
source-manifest SHA-256
`e466db24b8ed85ad6dd8c2d65bd03900a14b0834d158de0e7db8c07495d8fce0`.
Before submission it passed complete source-manifest verification, nine E19
wrapper tests, seven unchanged upstream SAGE tests, CPU deserialization of both
exact versioned LeWM checkpoints, and an exact legacy-versus-versioned identity
smoke in which all 303 state entries matched for both PushT and Cube.

The replacement dependency chain is jobs 299659–299663: preparation 299659,
release audit 299660, identifier-only overlap and LeWM/data audit 299661,
180-cell official reproduction array 299662, and unchanged official
summarizer/analyzer 299663. The scientific protocol and its SHA-256 remain
unchanged.
