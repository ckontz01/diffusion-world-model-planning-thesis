# Post-E14 boundary diagnostic implementation decisions 1

Date: 25 August 2026

Status: pre-full-run technical implementation record

## Initial immutable snapshot

The first diagnostic snapshot was
`gdp-post-e14-boundary-3971bb230cad54e1`, with source-manifest SHA-256
`3971bb230cad54e1b62bd0c9d3954c95c5f487a302a436b8d93ba13f66be38dc`.
Its static preflight passed three unit tests.

## Smoke job 299172 technical failure

The one-cell smoke job failed before loading the E14 cache, endpoint model, or
world model and before producing any output artifact. The diagnostic referred
to `spec.EXPECTED_GPU_NAME`, a constant added in the later Gate-C wrapper
snapshot but absent from the immutable E14 offline snapshot used as this
diagnostic's base. Python raised `AttributeError` immediately after detecting
CUDA.

The correction defines the same exact required device string,
`NVIDIA RTX 6000 Ada Generation`, inside the diagnostic module. It does not
change a task, row, seed, model, candidate, metric, threshold, or
interpretation.

The empty failed smoke output location is preserved. A new immutable snapshot
and a new output location are required for the replacement smoke.

## Revised static-freeze compatibility correction

The first attempt to freeze the analyzer stopped during test collection. The
immutable E14 offline base predates the later `read_sha256_records` helper that
the analyzer initially imported. No replacement smoke or full diagnostic was
submitted. The analyzer now contains its own strict two-file GNU-checksum
reader. The failed staging directory is preserved and the corrected freeze
uses a new staging location.

## Analyzer fixed before full execution

Before any full diagnostic cell was submitted, a deterministic six-cell
analyzer and synthetic tests were added. The analyzer validates every output
hash and all-row E14 reproduction claim, reports predeclared row-distribution
quantiles and equal-task/equal-seed descriptive summaries, and has no
scientific gate or E15 authorization authority.
