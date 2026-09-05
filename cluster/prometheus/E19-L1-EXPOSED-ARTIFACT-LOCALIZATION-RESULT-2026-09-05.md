# E19-L1: exposed-artifact localization result

Date: 5 September 2026. Outcome-informed engineering follow-up, not a new
efficacy experiment. [Plan](E19-L1-EXPOSED-ARTIFACT-LOCALIZATION-PLAN-2026-09-05.md).

## Conclusion

The earlier two D2 flags are diagnostic discrepancies, not two demonstrated
causes of the SAGE paper-table gap. L1 substantially localizes them:

- All five first planning calls have identical recorded computational fields
  across the two existing repeats, including their returned actions. Their
  first-call bank differences are confined to additional environment `info`
  fields; no opaque `repr` value occurs in any inspected bank or trace.
- All eight available first-call CEM banks reproduce historical costs exactly
  on fixed-input replay. The actual original top-k selection agrees with the
  recorded indices, which reconstruct the historical fitted mean and std.
- Later differences are real, not solely whole-bank metadata noise: they
  first appear in observations/state supplied after the first action block.
  One of 250 paired episode outcomes flips between the existing repeats.
- JPEG/lossless conversion changes an average of 0.92 or 1.48 of 30 elites,
  depending on the tested bank. It measurably changes the fitted distribution,
  but the authors' encoding and its effect on task success remain unknown.

No production planner defect or uniquely justified replacement configuration
is established. No source, checkpoint, dataset, manifest, tolerance, or result
from E19 or D2 was changed. Their decisions remain, verbatim:

- E19: `stop_native_reproduction_failed`.
- First discrepancy diagnostic: `diagnostic_invalid_stop_without_e20`.
- E19-D2: `prepare_author_evidence_no_unique_e20_correction`,
  `e20_authorized=false`.

The historical exactly-one-class rule is not a universal prohibition on
future source-justified engineering repairs. L1 nevertheless does not authorize
or launch E20. There were zero new environment episodes, zero new candidate
samples, no training, no protected-data access, no E18-versus-SAGE run, and no
author contact.

## Identity and execution

Successful fixed-bank job: `300296`, `COMPLETED`, exit `0:0`, 69 seconds,
NVIDIA RTX 6000 Ada Generation, PyTorch `2.5.1+cu121`. Twelve L1 tests passed in
that exact environment. A separate standard-library reduction added three
passing local tests and performed no inference. The independently implemented
[package verifier](verify_gdp_cem_e19_l1_result.py) passes.

Run root:
`/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19-l1/localization-run-20260905-93b2c74f`.

Frozen replay snapshot:
`/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e19-l1-93b2c74f3ab15b6f`.
Source-manifest SHA-256:
`93b2c74f3ab15b6f7d66074fd82f436d86d0ac3d6ac4c72dae1c41226e6e49f8`.
L1 plan SHA-256:
`002d7a4690551f9a54f4d6b19b785de2567e3fa00c4403e7c6c5b3e0450d715e`.

All 40 adjacent parent-file checksums, ten first-call content hashes, ten
trace content/identity checks, and the five prespecified E19 result hashes
passed before reduction. The unchanged parent snapshot is
`gdp-cem-e19-discrepancy-e347bc087381ecf0`; source-manifest SHA-256
`e347bc087381ecf0902581e8225165dbd64c887eba661b74b064c09d4e13d7fa`;
protocol SHA-256
`e420dca314038141caa30cadf0fe67ba649e53803d393e85a52c5a87a321f319`.
The frozen official SAGE commit remains
`8219029fd52e89157e05aebb998ab26f0ef46966`, tree
`0c64066eeac97c27fee382c1879bb26968b3fd56`.

The first L1 attempt, job `300295`, failed in report serialization before GPU
bank replay. An intentional NaN placeholder in the prior-top solver output
could not be written as strict JSON. Its outputs and snapshot are preserved;
the retry only added explicit nonfinite-metadata encoding and a regression
test. Details: [implementation history](E19-L1-IMPLEMENTATION-CHANGELOG-2026-09-05.md).

## What differs, and when

Plan indices below are zero-based. Events were aligned by plan, event kind,
and within-kind occurrence, with exact order and no missing event on either
side. All 1,020 paired recorded CEM mean/std updates were inspected; the 120
update pairs in the four CEM sentinels' first planning calls match exactly.

| Sentinel, seed 32 | First later input difference relevant to computation | First recorded computational difference | First returned-action difference |
|---|---|---|---|
| s0: PushT base CEM, H50 | Plan 1: raw/processed pixels and `state` | Plan 1, round 0: costs and fit; round-0 candidates still match | Plan 1 |
| s1: PushT far-goal prior CEM, H125 | Plan 1: raw/processed pixels and `state` | Plan 1: history latents, then round-0 candidates/costs/fit | Plan 1 |
| s2: PushT generator prior top, H125 | Plan 1: raw/processed pixels and `state` | Plan 1: history latents, local goal, top action | Plan 1 |
| s3: Cube LeWM + Generator, H150 | Plan 1: `observation`, control and simulator-state fields; pixels first differ at plan 5 | Plan 1: generated local goal and costs; fitted mean/std first differ at plan 5, round 1 | Plan 5 |
| s4: Cube SAGE, H75 | Plan 1: `observation`, control and simulator-state fields; pixels first differ at plan 2 | Plan 1: generated local goal, then round-0 candidates/costs/fit | Plan 1 |

At plan 0, PushT bank differences are exactly `block_pose`, `id`, `n_contacts`,
`pos_agent`, and `render_time`. Cube differences are exactly
`privileged/block_0_pos`, `privileged/block_0_quat`, `privileged/block_0_yaw`,
`proprio/effector_pos`, `proprio/effector_yaw`, and `proprio/joint_pos`.
Their numerical differences are retained in the machine report, not discarded
as harmless. The recorded pixels, model history/goal/local-goal outputs,
candidate banks or top actions, costs, elites, fitted distributions, and final
actions match for the first planning call.

This localizes the first *observed* later drift to the interval between the
first returned action block and the next solver input. It does not identify
the exact simulator step or a specific faulty setter, hidden state, RNG,
physics operation, or renderer. The trace has no per-step simulator-state
capture. Subsequent active-environment filtering also changes array layouts
after outcomes diverge; later whole-tensor differences are not independent
failures.

Both evaluator families reset, apply dataset state hooks, and overlay dataset
observations into the solver input. Thus equality of the first input dictionary
is not proof of equality of the full physical simulator state. See the
[shared E18 review](E18-SHARED-INFRASTRUCTURE-REVIEW-2026-09-05.md).

## Actual behavioral differences in the existing artifacts

Each entry is successes out of 50 fixed records. No new outcomes were sampled.

| Sentinel | Original E19 | Existing repeat 0 | Existing repeat 1 | Episode flips between repeats |
|---|---:|---:|---:|---:|
| s0 | 30 | 30 | 31 | 1: index 19, failure to success |
| s1 | 6 | 5 | 5 | 0; both lose original index 48 |
| s2 | 17 | 17 | 17 | 0 |
| s3 | 11 | 11 | 11 | 0 |
| s4 | 44 | 44 | 44 | 0 |

The only fresh-repeat success-rate change is +2 percentage points in s0.
Four of five repeat pairs have identical episode-success vectors, including
both Cube sentinels. The two repeats do not estimate a variability distribution
reliably, and their 1/250 flip rate is not an independent-binomial confidence
claim. Diagnostic elapsed times include trace overhead and must not be used
as native planner latency measurements.

## Instrumentation and fixed-input checks

The old tracer really performs a second `torch.topk` after the official fit.
L1 instead observes the output of the *actual original operation*, without
replacing it or selecting twice. In all eight saved first-call CEM banks:

- Each original fit invokes top-k exactly once; its captured indices agree
  with the recorded index order in all 50 environments.
- Recorded elites reconstruct both historical fitted mean and effective std
  bit-for-bit. Captured fit outputs and elite costs also match history.
- There are zero exact elite-boundary ties and zero gaps within the
  predeclared descriptive relative `1e-6` band.
- Two cost replays of each fixed input/candidate/local-goal bank are exact,
  and both agree with the historical 50-by-300 float32 cost array; maximum
  absolute difference is 0.0. Checkpoint state and fit-time CUDA RNG state
  remain unchanged.

This falsifies the second-top-k explanation for these first-call banks only.
Later-round raw candidate/cost arrays were not saved. For example, s3 later
has recorded elite-index differences before its fitted distribution differs;
the available hashes cannot distinguish a tied reorder from other numerically
equivalent selections. No later-round tie diagnosis is claimed.

No actual opaque `repr` record was found. The fallback remains an instrumentation
risk, not an observed cause. The prior-top method has no CEM cost bank and
intentionally returns NaN cost placeholders; it is reported as not applicable
to CEM replay, not counted as a model nonfinite failure.

## Transport sensitivity beyond a binary flag

For the same two previously tested first-call banks, reconstructed JPEG and
lossless costs/history latents match the old comparison hashes exactly, and
JPEG costs match the stored native bank. Candidates remain unchanged.
Means below include all 50 environments, including unchanged elite sets.

| Quantity | PushT base CEM H50 | PushT far-goal prior CEM H125 |
|---|---:|---:|
| Environments with any elite replacement | 31/50 | 39/50 |
| Total replacements / 1,500 elite slots | 46 | 74 |
| Replaced elites per environment, mean (range) | 0.92 (0–4) | 1.48 (0–7) |
| Mean elite intersection out of 30 | 29.08 | 28.52 |
| Mean Jaccard similarity | 0.94221 | 0.90971 |
| Median JPEG 30th/31st cost gap | 0.47087 | 0.21539 |
| Median lossless 30th/31st cost gap | 0.49194 | 0.14450 |
| Mean absolute fitted-mean change | 0.02783 | 0.01523 |
| Maximum absolute fitted-mean change | 0.25391 | 0.13354 |
| RMS fitted-mean change | 0.04545 | 0.02514 |
| Mean absolute fitted-std change | 0.01752 | 0.01083 |

Fit differences are in planner-coordinate action units, not pixels or success
percentages. The two banks have different action-horizon geometry. Both JPEG
and lossless banks have zero exact or relative-`1e-6` selection-boundary ties.
The JPEG minimum boundary gaps are 0.0009613 and 0.00390625; complete per-record
gaps, overlap, latent changes, and mean/std changes are included in the reports.

Encoding therefore affects genuine optimizer decisions, not just a tie-order
artifact. Nevertheless this compares **our two representations**, not either
one against the authors' table-generating dataset. Neither encoding has been
selected as a fix. No new success comparison was run, so the direction and
magnitude of any effect on the full-table discrepancy remain unestablished.

## What is ready while awaiting the authors

The [supplemental evidence note](e19-l1-evidence/README.md) is prepared for user
review, not sent. The old D2 packet remains unchanged. Missing author artifacts
are the exact table dataset/conversion recipe, environment, and per-seed
outputs; these are needed to establish release fidelity, not to permit all
future engineering work.

The shared-infrastructure source review and 12 existing E18 unit tests pass
their limited checks, but do not certify fresh real-input simulator equivalence.
A separate [E18 confirmation outline](E18-CONFIRMATION-OUTLINE-2026-09-05.md)
records the corrected H150 signal and timing scope without creating a holdout.
Reset/state restoration and step-boundary repeatability remain a concrete
pre-confirmation engineering gate, not an assumed SAGE-only problem.

## Small evidence package

- [Field-level localization](e19-l1-evidence/LOCALIZATION.json), SHA-256
  `1702440f27a643610d8996e28c56f24eb05bb0c8938bdef84175b791084f9196`.
- [Fixed-bank replay](e19-l1-evidence/FIXED-BANK-REPLAY.json), SHA-256
  `40f0f4b1b543fefbcad543e3f99f825767207f84f8495267c7f931d8c18808ca`.
- [Stage/sensitivity reduction](e19-l1-evidence/supplement/STAGE-AND-SENSITIVITY-SUMMARY.json),
  SHA-256 `b416caaa8e4402e36b0cc42d38f4afccec6f729aa93acb940919ee0277b0d654`.
- [Independent package verification](e19-l1-evidence/VERIFICATION.json).

Only these small reports and source/documentation additions were copied to
the external-SSD-backed canonical WSL repository. Bulk banks and traces remain
on Prometheus/Lustre. The three unrelated untracked E12 drafts are preserved.
