# E19-L1 implementation and execution history

This is a new outcome-informed engineering workstream on branch
`e19-l1-exposed-artifact-localization`, based on `37ae6f4`. It does not amend
E19, its first diagnostic, or E19-D2.

## Initial bounded implementation

Commit `b4f8cdd` added the L1 plan, field/tensor comparison helpers, a scoped
observer of the actual original top-k selection, 11 synthetic tests, a
fixed-bank-only runner, and a narrow snapshot freezer. No parent code was
edited. The local tests passed. All parent source/data seals are checked before
replay, and the cluster filesystem is bound read-only except the fresh L1 run.

Snapshot `gdp-cem-e19-l1-1ac380f0123e42f6`, source-manifest SHA-256
`1ac380f0123e42f62065ab4db7ccf7b75bdaf624b4ebe31e096e8565fdef5879`, ran as
job `300295` on gpu09. All 11 exact-environment tests passed, and the reader
localized the ten existing artifacts. It failed after 27 seconds, exit `1:0`,
when strict JSON encountered an intentional NaN placeholder in the existing
`generator_prior_top` solver output. No fixed-bank inference or episode ran in
that attempt. Its partial output, logs, and snapshot remain preserved under
`/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19-l1/localization-run-20260905-1ac380f0`.

## Report-format correction and successful replay

Commit `5f86c65` added explicit `nonfinite_scalar` metadata records and a
regression test. It also prevents equal NaN placeholders from becoming false
field differences through Python's `nan != nan` behavior. It never normalizes
or changes cost tensors, source trace hashes, or parent decisions. Nonfinite
*CEM costs* are still rejected. The corrected 12 tests passed locally and on
the cluster.

The seven-file immutable snapshot is
`/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e19-l1-93b2c74f3ab15b6f`;
source-manifest SHA-256
`93b2c74f3ab15b6f7d66074fd82f436d86d0ac3d6ac4c72dae1c41226e6e49f8`.
The unchanged L1 plan hashes to
`002d7a4690551f9a54f4d6b19b785de2567e3fa00c4403e7c6c5b3e0450d715e`.

Job `300296` completed, exit `0:0`, in 69 seconds using one NVIDIA RTX 6000
Ada Generation with PyTorch `2.5.1+cu121`. All eight CEM banks passed original
elite/mean/std and historical-cost reconstruction; all four JPEG/lossless cost
arrays matched the prior comparison. Checkpoint states were unchanged.

Run root:
`/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19-l1/localization-run-20260905-93b2c74f`.
The sealed `analysis/sha256.txt` itself hashes to
`1c7593a651832fefad9a6688f056116fd97e84f64cfa2f4ac73124679dd2fc3a`.
Both contained reports passed checksums on Lustre and after copying to WSL.

## Read-only reduction and independent review

A separate standard-library reducer locates the first divergence per
computational field and stage and summarizes elite overlap and boundary gaps.
It reads the same exposed traces and sealed L1 reports; it runs no model.
Its first invocation stopped before data reads/output because the login node's
older Python lacks `Path.is_relative_to`. The equivalent explicit resolved
parent-containment check corrected that utility compatibility issue. No
scientific setting or completed replay was changed or rerun.

The reducer then completed on the login node in the same run's fresh
`supplement/` directory. It records its own source SHA-256; three reduction
tests pass. All five first planning calls are computationally exact in the
recorded fields. The original 1,020 CEM-update pairs and all 250 paired outcome
identities are retained rather than rerun. An independent standard-library
package verifier checks the report seals, source identity, geometric/overlap
arithmetic, historical-fit agreement, all zero-replay-error conditions, and
scope flags. Its output is included in the small evidence package.

Five inspected E18 implementation modules were checked byte-for-byte against
the immutable E18 snapshot. The already existing six-file E18 unit suite
passed 12 tests locally; it does not replace a real-input simulator replay.
The review, corrected interpretation of the published E18 numbers, unsent
supplemental packet, and non-executable confirmation outline are new files.

E19/E19-D2 protocols, analyzers, results, checkpoints, manifests, and old author
packet remain unchanged. No D5 or other protected metric artifact was read or
hashed. There was no new episode, candidate sampling, training, E18-versus-SAGE
comparison, author contact, or full-grid submission. Bulk artifacts stay on
Lustre; the canonical repository is `/home/chris/thesis` in `Thesis-Ubuntu` on
the external SSD. The unrelated three E12 draft files remain untracked.

Final combined local check: 27 tests passed in 13.60 seconds (12 L1 fixed-bank
utility tests, three reduction tests, and 12 existing E18 tests). Both shell
scripts passed syntax checks. The independent evidence verifier and all seven
replay-source-manifest checks passed again. Git comparison with `37ae6f4`
confirmed no changes to the three historical E19/diagnostic result files, the
old D2 author packet, or the E18 evaluator/planner. Windows' WSL registry
confirmed `Thesis-Ubuntu` is backed by `D:\WSL\Thesis-Ubuntu`, not the laptop's
C: drive.
