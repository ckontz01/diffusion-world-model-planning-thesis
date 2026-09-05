# E19-L1: exposed-artifact localization (engineering follow-up)

Date: 5 September 2026. Authorized by the user's attached review and request
to run the locally doable work while awaiting the SAGE authors. This is
outcome-informed engineering diagnosis, not an efficacy experiment or an
amendment to an earlier frozen decision.

## Immutable history and scope

E19 remains `stop_native_reproduction_failed`; the first diagnostic remains
`diagnostic_invalid_stop_without_e20`; E19-D2 remains
`prepare_author_evidence_no_unique_e20_correction` with `e20_authorized=false`.
Its two mismatch classes are diagnostic discrepancies, not two established
causes of the paper-table gap. The old exactly-one-class rule is preserved as
history, not imposed as a universal prohibition on future justified repairs.
E19-L1 does not authorize, draft, or launch E20.

Read only the ten already exposed sentinel runs under
`/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19/discrepancy-diagnostic-run-20260829-e347bc08/sentinels`,
their adjacent inventories, the successful comparison, the five prespecified
E19 baseline results, pinned source/model/data identity records, and the
already published E18 report and frozen E18 source. Parent snapshot:
`gdp-cem-e19-discrepancy-e347bc087381ecf0`; source-manifest SHA-256
`e347bc087381ecf0902581e8225165dbd64c887eba661b74b064c09d4e13d7fa`;
protocol SHA-256
`e420dca314038141caa30cadf0fe67ba649e53803d393e85a52c5a87a321f319`.
Use WSL Thesis-Ubuntu and SSH alias prometheus. Bulk artifacts stay on Lustre.

No new environment episode, training, planner search, new candidate sampling,
holdout construction, D5, D3/D4 metric artifact, P3/P4/C1/I1 access, E18 versus
SAGE comparison, or author contact is authorized here. No parent source,
manifest, checkpoint, result, expected value, tolerance, or decision is edited.
New outputs must use a fresh E19-L1 namespace and include checksums.

## Bounded measurements

1. Verify all ten adjacent inventories and identities before loading data.
   Compare ordered traces field by field. Report the first differing event
   and tensor field, every field/kind's difference count, and coverage of all
   CEM mean/std updates. Separate model inputs, numeric metadata, opaque repr
   records, candidates, latents, costs, elite indices, and solver outputs.
2. Rehash each complete first-call bank. Compare actual tensor values rather
   than torch.save file bytes alone; enumerate unsupported/repr-valued paths.
   Quantify changed episode outcomes from the existing result vectors. Do not
   infer per-episode behavior where the artifact did not save it.
3. Replay only the saved first-call candidate/cost banks in the pinned
   PyTorch 2.5.1 CUDA environment. Capture the original solver's actual topk
   output with a scoped operator observer; do not replace its selection.
   Check that recorded elites reconstruct its mean/std, retain exact ties,
   and report boundary gaps (including a descriptive relative 1e-6 gap band).
   Later-round magnitudes cannot be reconstructed from hashes alone.
4. Re-evaluate costs on the same saved inputs/candidates/local goals twice,
   without sampling or environment execution. Verify reconstruction against
   stored costs before interpreting replay differences.
5. For the same two already tested PushT first-call banks, reproduce the
   existing JPEG and lossless costs, then quantify elite intersection/Jaccard,
   boundary gaps, and fitted action mean/std changes per environment. These
   are sensitivity measurements, not evidence of which encoding the authors
   used or of any effect on success. Do not choose a replacement dataset.
6. Inspect shared E18 preprocessing/loading/reset/seeding/selection/timing
   source paths. Record what is shared and what is not; absence of a shared
   code path is not a universal runtime-equivalence proof. Record the E18
   numerical corrections using the committed report; never change its result.

Unit tests use synthetic inputs, including deliberately tied selections and
opaque metadata. At most one initial one-GPU fixed-bank replay job is needed;
technical execution errors may be diagnosed transparently in fresh attempts.
No blind performance information barrier is imposed on these already exposed
engineering artifacts. Do not spend a new 180-cell benchmark on instrumentation.

## Deliverables and stopping point

A field-level machine report, fixed-bank sensitivity report, tests, a concise
human result with limitations, an E18 shared-infrastructure checklist, and a
pre-confirmation outline that does not create any episode split. Keep the old
author packet intact; a separate supplemental note may be prepared for review
but not sent. Preserve the three untracked E12 drafts. Commit only relevant
new files and README/history additions. Missing author artifacts remain an
explicit limitation; no claim of an established correction follows merely
from a non-identical hash.
