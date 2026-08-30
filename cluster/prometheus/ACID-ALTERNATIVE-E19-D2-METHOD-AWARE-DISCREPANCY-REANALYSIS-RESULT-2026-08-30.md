# E19-D2 method-aware discrepancy reanalysis: valid non-unique stop

Date completed: 30 August 2026

## Terminal outcome

The separately frozen E19-D2 analyzer-only reanalysis is **internally valid**
and identifies two objective mismatch classes:

1. `exact_repeatability`;
2. `pusht_jpeg_transport_elite_membership`.

The unchanged decision rule requires exactly one uniquely attributable,
mechanically correctable mismatch class before an E20 reproduction can be
authorized. Two classes are non-unique. Therefore `e20_authorized=false`, the
terminal decision is
`prepare_author_evidence_no_unique_e20_correction`, and no E20 was drafted or
launched.

This result does not amend either earlier decision. E19 remains exactly
`stop_native_reproduction_failed`, and the first discrepancy diagnostic
remains exactly `diagnostic_invalid_stop_without_e20`.

## Why E19-D2 was separately justified

Static inspection found an outcome-independent defect in the first diagnostic
analyzer. Its unconditional trace gate required a `history_latents` event from
every method. Pinned official PushT `base_cem` does not call the history-latent
path when no generator is present, so the gate was impossible for prespecified
sentinel 0 regardless of any result.

E19-D2 changed only that event-validity expectation:

- `base_cem` must not emit `history_latents`;
- the four history-conditioned methods must emit it; and
- final-goal and local-goal evidence remain mandatory for every method.

The byte-identical parent analyzer supplied all mismatch definitions and E20
rules. E19-D2 reused the checksum-verified raw sentinel, trace, bank, and
comparison artifacts without rerunning an episode or comparison, and did not
open or consume the failed parent analyzer output.

## Frozen identity and execution

- Corrected snapshot:
  `/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e19-d2-511534515469599b`.
- Source-manifest SHA-256:
  `511534515469599b8c15a4ee84e339ae6b729ead9fde4a51705bda837fed4b1d`.
- E19-D2 protocol SHA-256:
  `c002316080240245f87553086ac1eb0202380374447ae049bdb291edd7abd248`.
- Parent analyzer SHA-256:
  `3ddecca36b538509a7664dd5bfdaa12fd6ae007e788a909c4a01f0a11811c710`.
- Parent diagnostic source-manifest SHA-256:
  `e347bc087381ecf0902581e8225165dbd64c887eba661b74b064c09d4e13d7fa`.
- Parent diagnostic protocol SHA-256:
  `e420dca314038141caa30cadf0fe67ba649e53803d393e85a52c5a87a321f319`.
- Run root:
  `/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19-d2/method-aware-reanalysis-run-20260830-51153451`.
- Readable validity-only job `300097`: completed `0:0`.
- Dependent sealed classification job `300098`: completed `0:0`.

The freeze retained the exact official SAGE commit
`8219029fd52e89157e05aebb998ab26f0ef46966` and tree
`0c64066eeac97c27fee382c1879bb26968b3fd56`, verified every source-manifest
entry, and passed nine tests.

The first D2 execution is also preserved. Its validity job `300095` passed,
but classification job `300096` failed with a technical `RecursionError`
before producing a classification because the replacement gate delegated to
the newly installed symbol. The corrected snapshot captures the immutable
parent gate before installation and adds a regression test. No partial result
from that failed execution was interpreted.

## Integrity and validity

Every adjacent checksum verified before classification was read. The readable
Stage-A `VALIDITY-ONLY.json` recorded `all_passed=true`, all six validity
booleans true, and `failed_checks=[]`. Its `sha256.txt` has SHA-256
`133c8dcbf499965abc63ebe63fcd8c7bebac6dd3d61b73d570f32c63a29cc9ab`.

Every Stage-B output also verified. The classification `sha256.txt` has
SHA-256
`115f9576c2d83d0206cf47cfdd19fccf449f1b6b404da5c42b7c32dc7a5b9cea`;
the aggregate `DISCREPANCY-AUDIT.json` has SHA-256
`4092bdcc2ffd1e3cb715553ad651aa3c87d7e3932fa67fa1fe42fd4a166b345f`.

The provenance audit records that raw artifacts were reused without an
episode rerun, the failed parent analyzer output was not read, the only
correction was the method-aware history-latent expectation, and all protected,
D5, E18-versus-SAGE, and author-contact flags remained false.

## Exact-repeatability mismatch

Fresh-process repeatability failed the frozen exact-hash rule for all five
prespecified sentinels. Every sentinel changed both its ordered trace hash and
its first-call bank hash across its two repeats.

| Sentinel | Cell | Method | Horizon | Bank exact | Trace exact | Result exact | Original E19 outcome exact |
|---:|---|---|---:|---|---|---|---|
| 0 | PushT array 1 | `base_cem` | 50 | No | No | No | No |
| 1 | PushT array 22 | `far_goal_prior_cem` | 125 | No | No | Yes | No |
| 2 | PushT array 58 | `generator_prior_top` | 125 | No | No | Yes | Yes |
| 3 | Cube array 131 | `lewm_generator` | 150 | No | No | Yes | Yes |
| 4 | Cube array 164 | `sage` | 75 | No | No | Yes | Yes |

Thus four of five coarse result outcomes repeated exactly, but none of the
five complete traces or candidate banks did; only three of five fresh outcomes
matched the original E19 outcome exactly. This establishes the registered
`exact_repeatability` mismatch class without by itself identifying a unique
mechanical source.

## Runtime-load and Cube-cache comparisons

The compatibility-loaded LeWM and strict official-runtime load matched on all
five real-input fixed banks:

- model states matched;
- bank reconstruction was valid;
- latents, costs, candidate ranks, and elite membership matched; and
- compatibility costs reproduced the E19 bank costs.

Accordingly `runtime_mismatch=false` and
`runtime_bank_reconstruction_valid=true`.

The Cube generated-goal cache audit also passed. It checked 4,530 events and
1,056 scoped unique stage keys with exact hit flags, expanded/unexpanded stage
keys, cached values, and returned goals. There were no collisions, hit
mismatches, return mismatches, or stage-key disagreements. Neither runtime
loading nor Cube cache identity is an objective mismatch class.

## PushT transport mismatch

The lossless HDF5 source and the JPEG-backed Lance transport were compared on
the actual E19 first-call banks for the two PushT sentinels. Both comparisons
were valid and confirmed that the source bank matched E19 before transport was
changed.

| Method | Records | Pixel mean absolute error | Pixel max error | Goal/history latents exact | Costs/order exact | Environments with changed elite membership | Mean Spearman rank correlation |
|---|---:|---:|---:|---|---|---:|---:|
| `base_cem` | 50 | 0.113402 | 23 | No | No | 31/50 | 0.997742 |
| `far_goal_prior_cem` | 50 | 0.111555 | 23 | No | No | 39/50 | 0.987320 |

The small pixel perturbation therefore propagated through real LeWM inputs to
non-identical latents, costs, candidate order, and elite membership. This is
the registered `pusht_jpeg_transport_elite_membership` mismatch class. The
diagnostic does not establish that this class alone explains the complete E19
paper discrepancy.

## Frozen decision and author evidence

Independent projection of the unchanged decision rule reproduced exactly two
mismatch classes, `internal_valid=true`, `e20_authorized=false`, and
`prepare_author_evidence_no_unique_e20_correction`. Zero classes would not
justify E20; multiple classes cannot specify one unique correction. No
checkpoint, planner setting, expected value, tolerance, manifest, E19 result,
or scientific gate was changed.

The analyzer generated a sealed author evidence packet for user review. It is
preserved in [the repository packet](e19-d2-author-evidence/README.md) and in
the immutable run. Its README and machine summary have SHA-256 values
`02288e157802261c7771528216845aacb12c3363cea9b1911339d835e05f4f24`
and `b63fbb600493cde4bb7a6f0183c9c1ac2344c0de04b17e237e07947eec4b56f3`.
No SAGE author was contacted.

No D5, D3/D4 metric artifact, P3, P4, C1, or I1 was accessed. E18 was not run
against SAGE. Any correspondence or new experiment requires a separate user
decision; E20 remains forbidden by this diagnostic.
