# Fresh driver implementation record

Branch `e18-fresh-driver-integration`, parent R3
`f3b94382e20144e218c33efac48bed75e22a0c39`. Bulk execution/artifacts remain on
Prometheus Lustre; canonical repo is external-SSD-backed WSL `/home/chris/thesis`.
Three unrelated E12 drafts and every historical source/result are preserved.

## Pre-execution work

Traced frozen E18 raw-state path, proposer normalization, pixel-only JEPA encode
and latent rollout. Added an explicit fail-closed driver and technical checker,
without editing R3 or inherited planner files. The checker uses exact R3 actual
checkpoint setup but constructs a new solver/policy per episode. No data fit.

First local unit run: fixture forwarded `verbose` into the local SAGE-style
environment constructor; removed that fixture-only argument (the E18 GPU World
does accept it). Next run exposed2.84e-14 float64 body/COG coordinate roundoff
on a synthetic position; defined1e-10 driver assignment tolerance, while keeping
observation-to-actual equality exact and exposed R3 accuracy checks unchanged.
Source inspection also scoped the decoder identity assertion to active actions,
not inactive zero padding. All changes preceded freeze/GPU execution. Nine
local lifecycle tests passed; remaining native warnings are input-list casting,
not a velocity-space regression. No alternative initializer was considered.

## One frozen GPU attempt

- Commit2e872c1; snapshot `e18-fresh-integration-a9d1c26573158f93`.
- Manifest `a9d1c26573158f93e3e17dba932129084795a05f2ac84eb7eaadb8bca881d540`.
- Run `.../experiments/e18-fresh-integration/run-20260905-a9d1c265`.
- Job300308, COMPLETED0:0, gpu09, elapsed2m05s.
- Nine driver regressions also ran in the actual E18 container before planning.
- All five arm outputs and complete source manifest verified before reading.
- Independent verifier:50 initialized episodes,128 actual planning calls,
  1,363 primitive actions, all frozen technical gates pass. No efficacy gate.

The first frozen GPU attempt passed; no scientific result was rescued or rerun.
Added a separately testable CPU evidence verifier and negative evidence tests
after execution. It does not change the executed wrapper or outcomes.
Before final handoff,37 initializer/R3/E18/driver local regression tests passed.

## Prospective input pins and confirmation preparation

Read and hash only the nine existing PushT final training checkpoints for
families VAD/Gaussian/GMM and seeds7201/7202/7203. All exact hashes passed and
all normalization payloads agree. Sealed PINNED-INPUTS.json SHA256
`cf48fd85336fbf4d65f12ef290cd3b08f3969da2c8a29842ece4c55e848f52df`;
no dataset, protected artifact or confirmation ID was opened. Wrote a detailed
prospective protocol draft, explicitly not frozen while the user-facing task
scope/effect-size questions are unanswered. Its conservative proposed sample
size and resource implications are disclosed, not automatically authorized.

The negative-evidence test initially addressed a nonexistent second planning
call in an early-terminated episode. Corrected that test to tamper with the
first planning position; no evidence/driver change. All nine evidence tests pass.

Final combined run:46 tests passed in15.94seconds (initializer, R3 boundary and
evidence tests, E18 specs/runtime/planner regressions, new driver and evidence
tests). Source-manifest and output/pinned-input seals, shell syntax and git
whitespace checks pass. The git diff against the R3 parent contains no changes
to the initializer or historical E18 runtime/planner. No new automation or
scientific launcher was created. Only relevant fresh-integration files, evidence,
prospective pins/draft and README are committed; the three E12 drafts stay untracked.
