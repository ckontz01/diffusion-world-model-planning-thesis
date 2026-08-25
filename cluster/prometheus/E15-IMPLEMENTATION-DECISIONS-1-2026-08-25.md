# E15 implementation decisions 1

Date: 25 August 2026  
Status: active frozen E15 development record

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

The resulting immutable offline/Gate-A snapshot is
`gdp-cem-e15-offline-fc6815036ca84793`, with source-manifest SHA-256
`fc6815036ca8479325505c9b0457a716f57a4359df918d738cdc2c639664ad69`.
Its containerized freeze completed nine tests and Python/shell compilation.
This post-freeze sentence records the generated identity and is not itself a
member of that immutable snapshot.
