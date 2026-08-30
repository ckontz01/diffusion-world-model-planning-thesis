# E19-D2 implementation changelog

## Preserved decisions

- E19 remains exactly `stop_native_reproduction_failed`.
- The first discrepancy diagnostic remains exactly
  `diagnostic_invalid_stop_without_e20`.
- Its failed analyzer output is not opened, copied, hashed, or consumed.
- No episode, fixed-bank comparison, E18-versus-SAGE comparison, protected
  artifact, E20 run, or author contact is performed while preparing E19-D2.

## Source-derived analyzer defect

The parent analyzer SHA-256 is
`3ddecca36b538509a7664dd5bfdaa12fd6ae007e788a909c4a01f0a11811c710`.
Its unconditional `latents_present` check required a `history_latents` event
from every prespecified method. Pinned official PushT source shows that
`base_cem` skips generator warmup when `generator is None`, returns final-goal
latents directly from `_local_goal_latents()`, and never needs
`_history_latents()`. The parent sentinel 0 was PushT `base_cem`, so that gate
was impossible independently of any sealed outcome.

## E19-D2 design

- Reuse the ten checksum-verified sentinel/trace/bank directories and the
  checksum-verified comparison directory without rerunning them.
- Make only history-event validity method-aware. `base_cem` must have no
  history event; all four history-conditioned methods must have one. Final and
  local goal evidence remain mandatory for every method.
- Import the byte-identical parent analyzer and replace only `trace_gate()`;
  all mismatch definitions and E20 rules remain parent code.
- Stage A emits a readable, non-metric `VALIDITY-ONLY.json`. Stage B is sealed
  and can run only after Stage A passes.
- Regression tests cover valid history-free `base_cem`, invalid unexpected
  `base_cem` history, invalid history-free `sage`, and valid history-bearing
  `sage`.

## Immutable launch

- Canonical design commit: `f47a5eb` on branch
  `e19-d2-method-aware-discrepancy-reanalysis`.
- Immutable snapshot:
  `/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e19-d2-d8cc0e6ef8851079`.
- Source-manifest SHA-256:
  `d8cc0e6ef88510793836f8bb683568588ca3857386c4d675e1bb077b83fd9678`.
- Protocol SHA-256:
  `c002316080240245f87553086ac1eb0202380374447ae049bdb291edd7abd248`.
- Freeze validation passed all 16 source-manifest entries, eight analyzer tests,
  the exact parent analyzer/spec/tracer hashes, the clean official SAGE
  commit/tree, and all ten sentinel plus comparison adjacent checksums.
- Fresh output root:
  `/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19-d2/method-aware-reanalysis-run-20260830-d8cc0e6e`.
- Readable validity-only job: `300095`.
- Dependent sealed classification job: `300096`.
- No parent analyzer output is an input, and no episode or comparison job is
  submitted.

## Preserved first D2 classification execution failure

- Validity job `300095` completed and its readable non-metric output passed all
  six gates with `failed_checks=[]`.
- Dependent classification job `300096` failed after eight seconds with a
  `RecursionError` before producing a classification. Installing the
  method-aware gate into the legacy module caused that gate to call the newly
  installed symbol instead of the captured parent implementation.
- The failed chain and fresh output path remain preserved. No partial
  classification file was opened or interpreted.
- The transport-only correction captures the byte-identical parent
  `trace_gate` at import time and delegates to that fixed reference. A ninth
  regression test installs the replacement into the legacy module and proves
  that a valid history-free `base_cem` trace returns without recursion.
- No validity definition, mismatch definition, raw input, parent output,
  scientific setting, or E20 rule changes.

## Corrected immutable launch

- Technical correction commit: `9745478`.
- Immutable snapshot:
  `/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e19-d2-511534515469599b`.
- Source-manifest SHA-256:
  `511534515469599b8c15a4ee84e339ae6b729ead9fde4a51705bda837fed4b1d`.
- Protocol SHA-256 remains
  `c002316080240245f87553086ac1eb0202380374447ae049bdb291edd7abd248`.
- Freeze validation passed nine tests and retained the exact parent analyzer
  SHA-256.
- Fresh run root:
  `/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19-d2/method-aware-reanalysis-run-20260830-51153451`.
- Readable validity-only job: `300097`.
- Dependent sealed classification job: `300098`.
