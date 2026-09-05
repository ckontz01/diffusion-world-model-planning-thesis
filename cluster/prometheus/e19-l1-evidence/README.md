# E19-L1 supplemental author evidence — for user review, not sent

This supplements, but does not replace, the preserved E19-D2 packet. E19's
native reproduction failed its frozen tolerance; D2 retained its two diagnostic
classes and did not authorize E20. L1 is a new exposed-artifact engineering
follow-up, not another table reproduction or an accusation of a release bug.

## New measured facts

- All five existing sentinel pairs agree on their first planning call's
  recorded computational fields and returned actions. Initial complete-bank
  hash differences occur in additional numeric environment `info` fields;
  no actual opaque `repr` record was found.
- All eight available first-call CEM banks have exact historical cost replay
  and elite/mean/std reconstruction. Direct observation of the original top-k
  agrees with the saved indices. No boundary ties occur in those banks.
- Later differences begin after the first action block and before the next
  inference. PushT pixels/state differ at plan 1. Cube low-dimensional states
  differ at plan 1, before its pixels differ. The exact step-level cause is
  not identified by the stored traces.
- One of 250 paired episode outcomes changes between the existing repeats
  (PushT base CEM H50: 30 to 31 successes out of 50). The other four vectors
  repeat exactly. PushT far-goal prior CEM repeats at 5/50, versus its original
  E19 6/50. No new episode was executed.
- JPEG-versus-lossless transport replaces, on average, 0.92/30 elites in the
  base-CEM bank and 1.48/30 in the far-goal-prior bank; maximum replacements
  are 4 and 7. Mean Jaccard overlap is 0.94221 and 0.90971. The fitted means
  change, with mean absolute differences 0.02783 and 0.01523 in planner units.

These facts establish sensitivity and a narrower repeatability boundary, not
the authors' actual encoding or two causes of the paper-table discrepancy.
Passing the tested LeWM/runtime/cache checks is not a universal fidelity proof.

## Still useful from the authors

The exact table-generating Lance data or conversion recipe (including image
codec settings), execution environment and dependency versions, original
per-seed outcomes, and intended simulator reset/state-restoration procedure.
The source resets from a dataset seed when available, applies state hooks,
and overlays dataset observations; first input equality therefore does not
by itself verify full simulator-state restoration. No unsupported claim about
which configuration is correct should be attached to this request.

No message was sent and no reply was accessed by this task. The user is
awaiting the existing author correspondence.

## Evidence files

- [Full field localization](LOCALIZATION.json), sealed by [sha256.txt](sha256.txt).
- [Fixed-bank replay and per-record transport effects](FIXED-BANK-REPLAY.json),
  sealed by the same inventory.
- [Stage summary and overlap/gap distributions](supplement/STAGE-AND-SENSITIVITY-SUMMARY.json),
  with its [own seal](supplement/sha256.txt).
- [Independent package verification](VERIFICATION.json).
- [Exact seven-file replay source manifest](REPLAY-SOURCE-MANIFEST.sha256),
  SHA-256 `93b2c74f3ab15b6f7d66074fd82f436d86d0ac3d6ac4c72dae1c41226e6e49f8`.
- [Human result and limitations](../E19-L1-EXPOSED-ARTIFACT-LOCALIZATION-RESULT-2026-09-05.md).
- [Implementation/attempt history](../E19-L1-IMPLEMENTATION-CHANGELOG-2026-09-05.md).

These are small copies of sealed Lustre outputs. The bulk traces/banks remain
on Prometheus, and all parent results and protocols remain unchanged. No
protected data, new candidate sample, training, E20, or matched E18-versus-SAGE
evaluation was accessed or launched.
