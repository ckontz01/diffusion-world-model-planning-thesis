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

## 29 August 2026 — runtime-preflight legacy-history correction

Jobs 299688–299690 completed successfully, and their sealed release,
data-identity, overlap, checkpoint, and LeWM tensor-identity audits passed.
Runtime preflight 299691 then failed before writing an audit because its
synthetic-input builder directly accessed `predictor.num_frames`.  Historical
serialized predictors do not store that attribute.  The pinned official LeWM
runtime intentionally handles those objects with
`getattr(self.predictor, "num_frames", 3)`, but the new audit harness had not
mirrored that fallback.  Dependent evaluation 299692 and analyzer 299693 were
cancelled; no official evaluation cell ran and no performance artifact was
produced or read.

The audit now uses the identical official fallback, with a regression test for
both legacy and current predictor objects.  This is a non-performance
preflight-harness correction only.  It does not change the compatibility
mapping, official SAGE, LeWM execution, checkpoint bytes or tensors, datasets,
manifests, methods, cells, seeds, horizons, candidates, CEM rounds, schedules,
budgets, tolerance, scientific gates, or analysis.

The corrected audit snapshot is `gdp-cem-e19-45cc1704be7bd506`, with
source-manifest SHA-256
`45cc1704be7bd5069293410a925af76b797518c556238e8396f7b9483200cb87`
and the same protocol SHA-256.  It passed 12 E19 wrapper tests, seven unchanged
upstream tests, complete manifest verification, official runtime class
identity, and exact 303-tensor identity on both tasks.  Its replacement chain
is preparation 299694, release audit 299695, identifier-only overlap/data audit
299696, non-performance A6000 runtime preflight 299697, 180-cell official
reproduction array 299698, and unchanged official summarizer/analyzer 299699.

Runtime preflight 299697 exposed the same harness assumption for
`predictor.input_dim`: historical serialized predictors retain the dimension
in `pos_embedding` but do not store that convenience attribute.  It failed
before writing an audit; dependent jobs 299698–299699 were cancelled and no
evaluation or performance artifact existed.  The harness now derives the
predictor dimension from `pos_embedding.shape[-1]` when necessary and likewise
derives the action dimension from `patch_embed.in_channels` if the historical
action encoder lacks `input_dim`.  Both fallbacks are regression-tested.  The
complete updated synthetic preflight is executed once as a development-only,
non-performance A6000 diagnostic before another immutable snapshot is made.

Development-only A6000 diagnostic 299700 then executed that complete updated
preflight on both PushT and Cube and passed.  It verified official runtime
types, exact checkpoint hashes, exact 303-tensor identity, successful
float32-to-bfloat16 action handling, preservation and use of the injected
cached goal, finite outputs, and bit-exact reference-versus-versioned cost
parity with maximum absolute difference 0.0.  Its audit explicitly records no
performance, protected-metric, or D5 read.

The post-diagnostic immutable snapshot is `gdp-cem-e19-b4fef99885313bc9`,
with source-manifest SHA-256
`b4fef99885313bc975fe69ec7457a46a01aa31934bbf4c9e476225f26d8b2e9d`
and the unchanged protocol SHA-256.  Its dependency chain is preparation
299701, release audit 299702, identifier-only overlap/data audit 299703,
non-performance A6000 runtime preflight 299704, 180-cell official reproduction
array 299705, and unchanged official summarizer/analyzer 299706.  The same
complete A6000 preflight that passed in diagnostic 299700 remains a mandatory
`afterok` barrier before array 299705.

## 29 August 2026 — Cube LeWM+Generator cache-warmup correction

Jobs 299701–299704 completed successfully and all sealed preparation, release,
data-identity, overlap, LeWM tensor-identity, and non-performance runtime gates
passed. Official evaluation array 299705 then completed cells 0–126. Its Cube
`lewm_generator` cells 127–131, 133–137, and 139–143 failed before writing a
result; the three H25 cells 126, 132, and 138 completed because at H25 the
released evaluator uses the final goal directly and does not invoke the
generator. Every failed stderr file was byte-identical, with SHA-256
`88847a3619f8e86a2fc412df4882690db84ec2ee794d331b56123286047e21ff`.
The traceback ended in the unchanged official Cube generator with
`RuntimeError: Tensors must have same number of dimensions: got 3 and 5`.
No result or partial performance artifact was opened. After identifying the
identical technical failure, the remaining array work and dependent analyzer
299706 were cancelled; all existing artifacts were preserved.

The failure is an upstream execution omission rather than a model or
scientific-gate result. The pinned PushT `GaussianCEM.solve` explicitly warms
the generated-local-goal cache on the unexpanded planner query before
candidate expansion. The pinned Cube `GaussianCEM.solve` omits that line.
Consequently, Cube `lewm_generator` first asks for a generated goal after the
image inputs have gained a CEM-candidate axis: the native six-dimensional goal
becomes seven-dimensional, and the generator receives incompatible latent
ranks. Prior-based Cube methods prime the same cache while constructing their
proposal and therefore do not enter this failing path.

The compatibility runner now mirrors the exact PushT cache warmup for Cube:
when and only when a generator exists, it calls the existing
`CubeSAGEModel.local_goal(info)` once before delegating to the unchanged
official `GaussianCEM.solve`. The official SAGE checkout remains pristine;
checkpoint bytes and tensors, generated goal, candidate bank, CEM updates,
cost function, seeds, horizons, schedules, budgets, manifests, and analysis
are unchanged. Base CEM and every prior-based method are execution-identical.

A new mandatory non-performance A6000 preflight uses the exact Cube LeWM,
generator, and action-prior checkpoints with synthetic images. It must
reproduce the seven-dimensional uncached-input defect, show that the
unexpanded cache contains exactly one entry, prove that the candidate-expanded
lookup returns the cached goal bit-for-bit with a three-dimensional latent,
and verify that the compatibility runner is installed. It executes no episode
and reads no performance, protected-metric, or D5 artifact. A replacement
180-cell chain may be submitted only from a new immutable snapshot after this
preflight and all earlier E19 gates pass.

The corrected immutable snapshot is `gdp-cem-e19-a58f577120e1d00e`, with
source-manifest SHA-256
`a58f577120e1d00e74f9b227188023878cbbdbcd9aee0e78c5a86314dcf2ef0d`
and unchanged protocol SHA-256
`759f64b67a5c8e9d33e03c4d7027ede7edf99f1a4186236fb8f0879fc7ed0e20`.
It passed complete source-manifest verification, 16 E19 wrapper tests, seven
unchanged upstream SAGE tests, exact official commit/tree verification, and
the frozen CPU serialization/tensor preflight. Its replacement dependency
chain is preparation 299860, release audit 299861, identifier-only overlap and
LeWM/data audit 299862, the expanded non-performance A6000 runtime preflight
299863, 180-cell official reproduction array 299864, and unchanged official
summarizer/analyzer 299865. Evaluation cannot start unless both sealed runtime
audits pass.
