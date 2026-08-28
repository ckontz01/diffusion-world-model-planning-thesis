# E19 official SAGE reproduction and episode-overlap protocol

Date fixed before any E19 performance result: 28 August 2026

Evidence role: third-party release fidelity audit and identifier-only data-lineage
audit. A successful native reproduction is not itself a comparison with E18.

Protected comparison status: not authorized by this document

## 1. Purpose

The official implementation of *SAGE: Subgoal-Conditioned Action Generation
for Latent World Model Planning* became available after E18. E19 replaces the
earlier equation-based SAGE reconstruction as the implementation-fidelity
reference. It asks two questions without modifying SAGE scientifically:

1. Can the public release reproduce its complete 180-cell PushT/Cube paper
   table within the release's own two-percentage-point tolerance?
2. Are the released SAGE episode splits and paper manifests episode-disjoint
   from the data used to train or develop the exact E18 method?

E19 does not evaluate E18 against SAGE. It cannot read or create D5, and it
cannot launch a protected matched comparison.

## 2. Immutable upstream identities

The only permitted SAGE source is:

- Git repository: `https://github.com/PKU-ML/SAGE`;
- commit: `8219029fd52e89157e05aebb998ab26f0ef46966`;
- Git tree: `0c64066eeac97c27fee382c1879bb26968b3fd56`;
- license: the MIT file in that exact tree.

The only permitted released SAGE checkpoint source is:

- Hugging Face repository: `CLTRAY/SAGE`;
- snapshot revision: `1b5afbc8eeb1c8e99d9529099e1aa15f392a6346`.

All six checkpoint filenames, sizes, and SHA-256 digests must match the
unmodified `configs/checkpoints.json` in the pinned Git tree. In particular:

| Checkpoint | Bytes | SHA-256 |
|---|---:|---|
| `pusht_generator.pt` | 233878994 | `0b3647a3a41435969d750ec58176ef5f92a419c4eacae2b5cda74b35e63f90da` |
| `pusht_action_prior.pt` | 163404922 | `03ecab8f9d757eb8b3fc15e93481e830325428c24ede813c18f8692cc9b4bd80` |
| `pusht_far_action_prior.pt` | 163404602 | `60ed6831750e478b22c259b69e671236b41164f90284cb0422fe56d99e8c1425` |
| `cube_generator.pt` | 233981650 | `5f48e6d8eb3fab78d8f54bb36e1e275eefaf1fb82338a9b05e8f5cf5437a1352` |
| `cube_action_prior.pt` | 164984570 | `7ab6d2baefdcf5c2edf23192db6e969621fad621e21251b784c9e2309a0fb8eb` |
| `cube_far_action_prior.pt` | 164984186 | `32eb053197fddcb26ee7a86ea1d43fed2e95a3366423d646721a56fc8ca9fbde` |

The released evaluators, model code, manifests, paper configuration, and
summarizer must be executed from that tree without edits. E19 wrappers may
dispatch cells, validate identities, enforce an information barrier, and
collect hashes; they may not change a SAGE method, model, parameter, schedule,
budget, seed, start, success rule, or expected value.

## 3. Known release-packaging discrepancies

Before E19 was frozen, the pristine upstream release audit was run once. Its
semantic checks and all seven upstream unit tests passed, but its byte-level
manifest check reported exactly 36 failures. The release's `.gitattributes`
forces LF checkout, while every entry in `data/manifests/SHA256SUMS` matches
the same JSON bytes after LF-to-CRLF conversion. No semantic manifest hash
failed.

This is treated as an upstream line-ending packaging defect, not silently
repaired evidence. E19 must:

- run the pristine `scripts/audit_release.py` unchanged;
- require that its only failures are the exact 36 released manifest byte-hash
  lines;
- independently require all 36 embedded semantic hashes to pass;
- independently require all 36 recorded byte hashes to match LF-to-CRLF
  conversion and none to match any other transformation; and
- report that the pristine byte audit failed even if the compatibility audit
  passes.

The official checkout remains byte-unchanged. Evaluation consumes the
Git-checkout LF files, whose semantic identities are authenticated by the
unmodified evaluator.

The pristine `environment.yml` has a second release-only defect: it requests
`transformers==5.1.2`, a version that was never published on PyPI. The public
index contains 5.1.0 followed by 5.2.0. Static inspection of the pinned tree
finds Transformers only in the lazy `create_backbone` path for the unused
PreJEPA baseline; the released LeWM/SAGE evaluation path does not call it.
E19 therefore preserves the failed pristine installation record and uses
`transformers==5.1.0`, the nearest published version in the requested minor
series, as an explicitly labelled dependency-only compatibility correction.
No source import or evaluator is patched. The full resolved environment is
locked before tests, and every official unit test and paper cell must still
pass. If the SAGE evaluation imports or exercises Transformers, the
compatibility classification is invalid and E19 stops.

Published `transformers==5.1.0` requires `huggingface-hub>=1.3.0`, which is
inside the release's declared `huggingface-hub>=0.36` range. E19 pins the
minimum compatible version, `huggingface-hub==1.3.0`, and records the initial
resolver failure caused by the superseded `0.36.0` compatibility lock.

## 4. Environment and local input identities

The target runtime is the paper environment: Python 3.10, PyTorch 2.5.1,
CUDA 12.1, cuDNN 9, and the exact published package versions in the pinned
`environment.yml`, except for the classified Transformers correction above
and `hdf5plugin==7.0.0`, which the bundled HDF5 reader imports but the release
forgot to declare. The environment lock, `python --version`, `pip freeze`,
CUDA visibility, and GPU identity are written before evaluation.

The local source datasets are immutable:

- PushT HDF5:
  `b6ebd9ac94bbe9e383f6e7a9cd92d74e9aa665ea57b758ed3717b0ee7df8d4fb`;
- OGBench Cube HDF5:
  `0664d507c4ff12009010644c9ae950836f954e700c172ccf22e7423af1a55625`.

The release names a PushT Lance dataset but supplies neither that dataset nor
a byte digest. Therefore E19 cannot claim byte identity with the authors'
private Lance copy. It deterministically converts the pinned public HDF5 with
the pinned release's own `stable_worldmodel.data.convert`, default Lance
writer, and JPEG quality 95. The conversion is a disclosed transport
reconstruction. The data audit must require:

- exact HDF5 source hashes;
- 18,685 PushT and 10,000 Cube episodes;
- exact episode-ID coverage, per-episode lengths, step numbering, and
  disjoint/complete released train-validation-test splits;
- every released evaluation record to name a test episode and a valid
  start/goal pair;
- exact equality of converted PushT episode IDs, step IDs, lengths, and all
  non-image values against the HDF5 source; and
- on a fixed SHA-256-ranked sample of 256 PushT frames, decoded Lance images
  must have mean absolute pixel error at most 3.0 and maximum absolute error
  at most 64 relative to the source. Both errors are reported.

The official LeWM policies must resolve to the released model revisions used
by this thesis and be audited at both source-weight and local serialized-model
levels:

- PushT source revision
  `22b330c28c27ead4bfd1888615af1340e3fe9052`, weights SHA-256
  `48938400ae3464c9680731287f583a9cb516f55a8ec64ea13a91be47fb15b607`,
  config SHA-256
  `2564086e961e7b5c7c04dffc451091115b389a590645ff19653c64fd0bc16e09`;
- Cube source revision
  `b0747c5002e86d2ce8f3cd8178004b97524c587d`, weights SHA-256
  `2839a907362f403f9136383016e91774373a295d958ae75121791f22a9fddf89`,
  config SHA-256
  `4d446944fe28922cc2c5763f43d4ef9132a457bd89e9a0ce5dbceac183994999`.

Native reproduction records the exact local object-checkpoint hash passed to
each unchanged evaluator. E19 uses the strictly converted, revision-labelled
objects already used by E18: PushT SHA-256
`c3883fb585f4d97b628922a13a43441fe63e883808014d25312aca1793820659`
and Cube SHA-256
`5175b8d7a99b3c19aeee08027c666fb0562e316f14c36e74ac3a52ecce531e07`.
It also compares their tensors against the earlier local object files. Before
any later matched protocol, parameter-level identity between the official
policy resolution and the E18 LeWM object must be demonstrated; filename or
serialization equality alone is insufficient.

## 5. Stage A: release, checkpoint, unit-test, and data audit

Stage A is non-performance-bearing. It must complete all of the following:

1. authenticate the Git commit/tree and the immutable E19 source snapshot;
2. perform the pristine and compatibility release audits in Section 3;
3. run the unmodified upstream test suite and require exactly seven passing
   tests with no failure, skip, or expected failure;
4. download at the exact SAGE Hugging Face revision and verify all six files;
5. perform the dataset checks in Section 4; and
6. record exact software, checkpoint, dataset, LeWM, and manifest hashes.

Native reproduction is authorized only if every Stage-A gate other than the
explicitly classified pristine CRLF packaging defect passes.

## 6. Parallel identifier-only overlap audit

The overlap audit may read episode IDs, start indices, roles, split files, and
hashes only. It must not read success, cost, rank, regret, timing, prediction,
or any other metric-bearing field. It compares the released SAGE train,
validation, test, and paper-manifest episode sets against, separately:

- E15 proposer training and validation episode IDs;
- E17 adapter training and validation episode IDs;
- E14 offline validation and selected P2 episode IDs;
- E15 offline validation and selected P2 episode IDs;
- E16 diagnostic evaluation episode IDs;
- E17 preflight validation episode IDs; and
- E18 executed P2 evaluation episode IDs.

For E18, `training episodes` means the union of the frozen E15 proposer-train
and E17 adapter-train episodes because E18 trained no additional model.

The audit reports every pairwise intersection count, a SHA-256 digest of each
sorted identifier set, and a short identifier preview for nonzero
intersections. Its critical matched-comparison gate is:

`official_paper_manifest_episodes ∩ E18_training_episodes = empty`

It also constructs, without sampling outcomes, the complete candidate set of
released SAGE test episodes untouched by E15/E17 training or validation and
by every known E14-E18 development/evaluation episode. These identifier-only
candidate files do not authorize evaluation.

## 7. Stage B: complete official native reproduction

Stage B contains exactly the release's complete component table:

`2 benchmarks * 5 methods * 3 seeds * 6 horizons = 180 cells`.

Each cell consumes its released 50-record manifest, giving 9,000 total
episodes. The methods are exactly:

1. `base_cem`;
2. `far_goal_prior_cem`;
3. `lewm_generator`;
4. `generator_prior_top`; and
5. `sage`.

Seeds are 32, 42, and 52. Horizons are 25, 50, 75, 100, 125, and 150. The
released schedules, 300 candidates, 30 CEM rounds, 30 elites, action block 5,
three-frame history, frameskip 5, bf16 setting, and environment budgets are
unchanged.

The 180 cells run as isolated A6000 jobs with at most three concurrent cells.
Before every cell is terminal and successful, monitoring is limited to
scheduler state, exit codes, file existence, byte counts, and checksums.
Neither partial logs nor any `results.json` may be opened. A dependent
analyzer is the first process permitted to read performance.

The analyzer first validates all 180 identities, 9,000 episode outcomes,
checkpoint hashes, source hashes, schedules, budgets, and result-file hashes.
It then runs the pinned release's unmodified `scripts/summarize_results.py`
with its default 2.0-point tolerance. Stage B passes only if the released
summarizer exits successfully for every one of the 60 benchmark/method/
horizon means. Every per-seed value and difference from the released mean is
reported; no failed cell may be rerun with changed settings.

## 8. Stopping rule and possible later matched protocol

The native reproduction is an implementation-fidelity audit and may complete
regardless of overlap. It is never presented as E18-versus-SAGE evidence.

A separate matched H75/H150 protocol may be drafted only after:

- Stage A passes;
- Stage B passes the unmodified two-point summarizer; and
- the critical paper-manifest/E18-training overlap is exactly zero.

That later protocol, if authorized, must freeze exact unchanged E18 and
official full SAGE on identical records, LeWM parameters, schedules, budgets,
and planner seeds. It must include `vad_greedy_300`, E18 diagonal-Gaussian
continuation, official `lewm_generator`, official full `sage`, and a clearly
labelled derived official-prior best-of-300 ablation. It may not be launched
by E19.

If the critical overlap is nonzero, no matched performance evaluation on the
released paper manifests is allowed. Work stops after native reproduction
and construction of the identifier-only common untouched candidate split. A
new separately frozen protocol must use that common episode-level split.

## 9. Evidence firewall and amendments

E19 must never generate, open, hash, or consume D5, D3/D4 metric artifacts,
P3, P4, C1, or I1. It may read only the exposed identifier fields explicitly
listed in Section 6 and the public official SAGE reproduction outcomes after
the 180-cell information barrier closes.

Technical execution faults may be corrected only through a dated
implementation record that preserves the pinned upstream trees, checkpoints,
datasets, manifests, cells, methods, parameters, seeds, schedules, gates, and
all existing artifacts. A release-fidelity failure, tolerance failure, or
overlap is a scientific/data-lineage result and cannot be tuned or rescued.
