# E19 official SAGE release defects and compatibility decisions

Date: 28 August 2026

Upstream: `PKU-ML/SAGE@8219029fd52e89157e05aebb998ab26f0ef46966`

This record was written before any E19 performance cell was run.

## Manifest byte checksums

The pristine `scripts/audit_release.py` reports exactly 36 byte-hash failures.
Every JSON semantic hash passes. The Git tree forces LF checkout through
`.gitattributes`; every released `SHA256SUMS` entry matches the same file after
LF-to-CRLF conversion. E19 does not edit the official checkout. Its independent
audit must recognize exactly this discrepancy and no other release-audit error.

## Unpublished Transformers pin

The pristine environment install fails because `transformers==5.1.2` is not a
published PyPI distribution. Versions 5.1.0 and 5.2.0 exist, but 5.1.2 does
not. The pinned source tree references Transformers only inside the lazy
PreJEPA `create_backbone` function. Official SAGE evaluation uses the released
LeWM implementation and does not call that function.

E19 uses `transformers==5.1.0`, the nearest published version in the requested
minor series. This is a dependency-only compatibility correction; no SAGE
source is patched. If Transformers enters the evaluated call path, E19 must
stop rather than treating the correction as harmless.

The first compatibility lock exposed one further resolver constraint:
published `transformers==5.1.0` requires `huggingface-hub>=1.3.0`, while the
release itself permits every version from `0.36` upward. E19 therefore pins the
minimum compatible version, `huggingface-hub==1.3.0`. This is also a
dependency-only resolution and does not alter SAGE source or evaluation logic.

## Missing HDF5 runtime dependency

The bundled `stable_worldmodel.data.formats.hdf5` imports `hdf5plugin`, but the
release environment does not declare it. E19 adds `hdf5plugin==7.0.0` so the
released Cube HDF5 input can be opened. This changes no SAGE method or model.
The resolved package lock is preserved with the Stage-A audit.

## Missing Cube Gaussian-CEM local-goal cache warmup

The released PushT `GaussianCEM.solve` primes the generated-local-goal cache
from the unexpanded planner query before it expands inputs across CEM
candidates. The released Cube implementation omits the equivalent call. For
Cube `lewm_generator` at horizons above 25, the first generated-goal request
therefore receives candidate-expanded rank-4 low-dimensional history. The
released helper only removes a history axis from rank-3 inputs, so the subgoal
generator later attempts to concatenate rank-3 visual tokens with a rank-5
low-dimensional token and aborts. The H25 special case does not call the
generator, while the prior-based methods prime the cache during proposal
construction.

E19 keeps the pinned official checkout byte-for-byte unchanged and uses a
wrapper that performs only the missing pre-expansion cache call before
delegating to the official Cube `GaussianCEM.solve`. This mirrors the release's
PushT behavior and changes no model tensor, generated goal, candidate, score,
planner update, seed, schedule, budget, or analysis. An exact-checkpoint,
synthetic-input A6000 preflight must prove the uncached rank defect and the
bit-identical cached lookup before any replacement reproduction array runs.
