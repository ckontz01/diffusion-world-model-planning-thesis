# E15 implementation decisions 1

Date: 25 August 2026  
Status: complete; frozen Gate B stopped E15 before Gate C

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

## Replacement data snapshot and job 299197

The corrected snapshot is
`gdp-cem-e15-data-1b97e2286e1237a8`, with source-manifest SHA-256
`1b97e2286e1237a8c758ed5951e9a64433b2e41b4d10a6eb79215dcf8bc1fd46`.
Its four static tests passed, and both cells of replacement array `299197`
completed successfully. The two output checksum manifests verify.

The immutable outputs are under
`experiments/gdp-cem-e15/data-preflight-1b97e228/{pusht,cube}`. Their content
hashes are recorded in the data-preflight result. These outputs contain only
the frozen P1 split, bounded expert targets, train-only standardizers, and
registered structural geometry. No learned model, P2 result, or protected
outcome was produced or read.

## Scientific protocol and training snapshot

The long-horizon scientific protocol was frozen before model training with
SHA-256
`bcbe66b3b7b2635473d5bd98b3a450c5e136879f275ac3a0ddd6d4bdb254755b`.
The immutable training snapshot is
`gdp-cem-e15-training-ebd6109b65528f6b`, with source-manifest SHA-256
`ebd6109b65528f6b201c2de7deac29888a25e570f60d11ea9e6298374b61301c`.

Actual-data GPU preflight array `299199` completed both PushT and Cube cells
successfully on NVIDIA RTX 6000 Ada Generation GPUs. Each preflight loaded
292,500 role-0 rows, read zero validation payload rows, instantiated VAD,
matched diagonal Gaussian, and direct eight-mode trajectory GMM models, and
completed a forward/loss/backward step for each family. Both checksum records
verify. Full 22-cell training array `299201` was then submitted from the same
immutable snapshot. No validation or protected outcome was opened before that
submission.

## Offline implementation completion before Gate B

The first interrupted local construction of the E15 offline evaluator was
never frozen or executed. Its recovered draft was syntactically complete but
reported only the two gating boundary diagnostics. Before creating an offline
snapshot, the reporter was completed to include every Section-5 registered
near-boundary margin and Jacobian threshold, expert target-projection rate,
pre-squash magnitude summaries, post-squash coordinate spread, analytic mean
pairwise raw-action RMSE, and per-row rounded-trajectory uniqueness. This is a
reporting-completeness correction only: it does not alter a model, sample,
candidate count, selection rule, threshold, or gate.

The direct GMM sampler now returns its categorical component identifiers in
addition to sampled trajectories. Sampling itself is unchanged: one CPU-drawn
component is still used for the entire trajectory, followed by deterministic
CPU Gaussian noise. The identifiers are required solely for the frozen sampled
mode-count diagnostic.

The post-barrier analyzer encodes the protocol literally: equal-cell means,
task-first per-cell tables, expert-relative boundary rules, eight-mode GMM
structural checks, all-seed VAD-versus-Gaussian comparisons, per-task
two-of-three-duration directions, and the seed-7201 shuffled/unconditional
null comparisons. Full-validation metrics may be opened only by this analyzer
after all 22 evaluation cells terminate successfully. A separate Gate-A
validator first checks all 22 train-only smoke results and strictly loads the
unchanged E14 SAGE subgoal/option checkpoints referenced by normalization audit
SHA-256
`985454c195d2f785c665eb59d81efadb789512a4d03f3e44ffa3ac24140b6b40`.

The first immutable offline/Gate-A snapshot,
`gdp-cem-e15-offline-fc6815036ca84793` (source-manifest SHA-256
`fc6815036ca8479325505c9b0457a716f57a4359df918d738cdc2c639664ad69`),
completed nine tests and Python/shell compilation but was not executed. A
pre-execution audit found that Gate A checked the static-preflight protocol
hash and protected-data flags but did not also compare the static record's
training-source-manifest field with the frozen training snapshot. That lineage
comparison was added before any smoke or validation result existed. It changes
no scientific setting and requires a replacement immutable offline snapshot.

The replacement is `gdp-cem-e15-offline-d970a18e4921eb2c`, with
source-manifest SHA-256
`d970a18e4921eb2c4d3d2ed7f6fdd295b583320b43fef1a88908000d82a8a22e`.
Its containerized freeze again passed all nine tests and compilation checks.
This post-freeze identity sentence is not itself a member of the immutable
snapshot.

## Gate-B analyzer protocol-conformance correction before outcome access

While the 22 full-validation cells were still running and before any partial
or aggregate validation metric was opened, a source audit found that the
frozen common bank-integrity loop covered VAD, diagonal Gaussian, and direct
GMM at all three seeds but omitted the two seed-7201 VAD conditioning-null
banks. Section 9.1 says every VAD bank must satisfy the same finiteness,
uniqueness, strict-legality, exact-boundary, and expert-relative saturation
rules. A null bank that failed those rules would also weaken the registered
true-versus-null conditioning comparison.

Pending analyzer job `299220` was therefore cancelled before execution. The
22 sealed evaluations remain unchanged and continue from immutable source
snapshot `d970a18e4921eb2c`. A replacement post-barrier analyzer applies the
already frozen thresholds to all 22 evaluated banks and records the immutable
evaluation-source hash separately from its own corrected analyzer-source
hash. This expands protocol enforcement only; it changes no data, model,
checkpoint, candidate sample, metric definition, threshold, seed, or
comparison direction.

The corrected analyzer snapshot is
`gdp-cem-e15-offline-e0fb137d34750b0c`, source-manifest SHA-256
`e0fb137d34750b0c1d7e8c239d5a7b3d9c84b2c50c81d870f12aa04ff6ccc039`.
Its ten containerized tests passed. Replacement analyzer job `299257` is
dependent on successful completion of the unchanged full-validation array
`299219`; it is the only Gate-B analyzer authorized to release the aggregate.

## Gate-C implementation decisions fixed before Gate-B outcome access

Gate-C code was prepared while the 22-model training array and the dependent
offline validity chain were still running. No Gate-B metric or decision had
been opened. Preparing this code does not authorize its execution: no Gate-C
snapshot, manifest, evaluation, or result may be created unless the immutable
Gate-B analyzer returns its exact registered authorization decision.

The identifier-only execution registry is task-first and contains exactly 432
cells: two tasks, six arms, three replicates, three horizons, and four shards
of five base starts. Replicate `1,2,3` maps to E15 model seeds
`7201,7202,7203` and reused SAGE-reconstruction seeds `6101,6102,6103`.
Planner and proposal seeds are deterministic functions of task, horizon,
replicate, and shard and are identical across arms in each matched cell. The
immutable P2 query files themselves enforce the same 20 episode/start pairs
across all three horizons.

The SAGE one-stage ablation uses the unchanged reconstructed SAGE subgoal and
option-prior checkpoints. It generates the local subgoal and one 300-option
trajectory-GMM population, ranks that population once against the generated
local subgoal with Le-WM, and executes the minimum-cost member. It does not
take an elite mean and performs no later CEM update. Full SAGE and Base retain
their already frozen 30-population implementations.

Every planner stage is synchronized immediately before and after the entire
call. Encoding, proposal generation, and Le-WM rollout/scoring are marked by
CUDA-event intervals and resolved only after that one outer synchronization;
the timer never inserts a synchronization barrier between SAGE's CEM rounds.
This avoids making the 30-population comparator artificially slower merely to
obtain component measurements. The nonnegative residual of total wall time
after the measured components is reported together with proposal generation
as `proposal_and_selection`; this includes conditioning, CPU work,
bookkeeping, ranking, and selection. End-to-end wall time is the primary
efficiency quantity.

For the registered five-times latency rule, each task/horizon/arm value is the
median of all synchronized post-first-call end-to-end stage times pooled over
the three replicates and four shards, divided by the five parallel contexts.
The gate ratio is full SAGE divided by VAD after taking an equal-weight mean
over the four task/horizon cells formed by the two tasks and horizons 75 and
150. Horizon 25 timing remains reported but does not enter this long-horizon
ratio. This estimator was fixed before closed-loop outcomes.

The post-barrier analyzer must revalidate the passed Gate-A and Gate-B audit
files and hashes, all 432 result checksum manifests, all 2,160 episode rows,
and exact paired start identity before constructing any metric table. Its
10,000-draw paired bootstrap is stratified by task and resamples the 20
task/base-start clusters; each sampled cluster retains every arm, horizon, and
replicate. Replicates are averaged within the retained cluster and are never
resampled as independent observations. It reports task/horizon intervals plus
the registered all-horizon, long-horizon, and horizon-150 paired contrasts.
The analyzer runs only after every evaluation-array cell terminates
successfully, preserving the closed-loop information barrier.

## Final Gate-B execution and stop

All 22 cells of sealed validation array `299219` completed with exit code
`0:0`. Corrected dependent analyzer `299257` then completed with exit code
`0:0`. Its checksum manifest verifies
`GATE-B-AUDIT.json` and `TASK-FIRST-PER-CELL.tsv`.

The final audit records `artifact_count = 22`; all 22 common-integrity banks
and all six direct-GMM structural banks passed. The VAD mechanism and
conditioning gate failed because the registered task-first VAD-over-Gaussian
direction did not hold on PushT and true VAD did not beat unconditional VAD
under the complete null rule. The immutable decision is
`stop_before_gate_c_frozen_gate_b_failed`.

No Gate-C snapshot, identifier manifest, evaluation, or analyzer job was
created. The already blinded Gate-C source remains an unexecuted implementation
artifact only. P2 and D5 were not read, generated, or consumed. The audited
scientific result is recorded in
[the E15 Gate-B report](ACID-ALTERNATIVE-E15-BOUNDARY-AWARE-LONG-HORIZON-GATE-B-RESULT-2026-08-25.md).
