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
