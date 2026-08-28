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

## 29 August 2026 — legacy serialization mapped to the official SAGE LeWM runtime

Preparation 299659, release audit 299660, and identifier-only overlap audit
299661 completed successfully.  The release gate, data-identity gate, exact
LeWM tensor-identity audit, and all checkpoint hashes passed.  The overlap
audit found that the official paper manifests intersect E18 training in 270
PushT episodes and 84 Cube episodes.  Therefore the native official
reproduction remains allowed, but a later matched E18-versus-SAGE comparison
on those paper manifests is forbidden.  The audit preserved common untouched
candidate splits containing 579 PushT and 280 Cube episodes.

Official reproduction array 299662 then failed uniformly before producing any
result: completed failing cells 0–21 had the identical stderr SHA-256
`ad28736ff69776c8ea29777f91db92d84f54cb665f4972e4fe4a7cfa5148d45e`
and raised `RuntimeError: Input type (float) and bias type (c10::BFloat16)
should be the same`.  Cell 22 was cancelled after it started, and the remaining
array plus analyzer 299663 were cancelled.  No `results.json`, official
summary, or performance metric was produced or read.

The root cause was serialization compatibility, not SAGE or checkpoint data.
The exact versioned LeWM object files serialize the historical names
`jepa.JEPA` and `module.ARPredictor`.  Loading those names from the historical
repository instantiated obsolete execution semantics: its action embedder
forces float32 into a bf16 convolution, and its `get_cost` unconditionally
re-encodes the far goal, silently discarding the local `goal_emb` injected by
official SAGE.  Patching that obsolete class would therefore make the job run
but would not reproduce official SAGE.

The correction is a two-file pickle-name compatibility layer placed before the
historical runtime on `PYTHONPATH`.  It maps `jepa.JEPA` to the pinned official
`stable_worldmodel.wm.lewm.lewm.LeWM` and `module.ARPredictor` to the pinned
official `Predictor`.  It changes neither official SAGE source nor checkpoint
bytes or tensors.  A pre-freeze proof loaded both exact versioned objects as
the official LeWM class and matched all 303 state entries bit-for-bit against
the corresponding legacy official-class object on both tasks.

Every replacement snapshot must now pass that class/tensor audit while being
frozen.  A separate non-performance A6000 runtime preflight must additionally
show exact synthetic cost parity, successful float32-to-bf16 action handling,
and preservation/use of an injected cached goal before the 180-cell official
array is eligible to start.  This correction changes only pickle class-name
resolution and technical validation; it does not change SAGE, LeWM tensors,
checkpoints, datasets, manifests, methods, cells, seeds, horizons, candidates,
CEM rounds, schedules, budgets, tolerance, scientific gates, or analysis.

The corrected immutable snapshot is `gdp-cem-e19-92d7f7d0d525cf08`, with
source-manifest SHA-256
`92d7f7d0d525cf08fd97a0b5a28d3985c498a80b2f74cb13d2a007c6e4be4acc`.
Its unchanged protocol SHA-256 is
`759f64b67a5c8e9d33e03c4d7027ede7edf99f1a4186236fb8f0879fc7ed0e20`.
Before submission it passed 11 E19 wrapper tests, seven unchanged upstream
SAGE tests, complete source-manifest verification, and the two-task frozen
official-class/tensor-identity preflight.  The replacement chain is preparation
299688, release audit 299689, identifier-only overlap/data audit 299690,
non-performance A6000 runtime preflight 299691, 180-cell official reproduction
array 299692, and unchanged official summarizer/analyzer 299693.  Array 299692
cannot start unless the synthetic runtime preflight passes.
