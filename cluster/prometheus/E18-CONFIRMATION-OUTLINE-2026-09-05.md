# E18 confirmation preparation — outline only, not frozen or executable

Date: 5 September 2026. This is preparation while the SAGE authors' response
is pending. No holdout is selected, listed, generated, opened, or hashed. No
job, sample-size commitment, final acceptance gate, or E20 protocol is created.

## Scientific question

Does the exact unchanged E18 VAD continuation planner improve closed-loop
success over greedy VAD-300 and matched diagonal-Gaussian continuation on
new episode-disjoint records? Keep PushT and Cube and both H75/H150 in the
design discussion. PushT H150 is the strongest exploratory signal (44.44%
versus 25.00% for both controls), but it was observed during development;
any decision to make it primary must be explicitly outcome-informed and
declared before obtaining fresh outcomes.

E18's aggregate intervals against these two controls include zero. Its small
development sample does not provide a reliable confirmatory effect-size
estimate. E17 remains failed; use of its unchanged adapter is a planner-level
hypothesis, not retroactive validation of the adapter's old gate.

### Proposed same-proposal greedy-64 control (not implemented)

Add a mechanistic control that receives exactly the continuation planner's
same first 64 proposals, in the same order and from the same sampled bank.
Choose by immediate endpoint cost instead of continuation cost. Sharing only
a seed is insufficient: verify the complete first-proposal tensor identity.
Keep the diffusion model, initial proposal generation, action transforms,
execution schedule and records unchanged. This control isolates the choice
of scoring rule at a fixed initial candidate population; it is not a
compute-matched substitute for greedy-300.

Its inferential role (secondary/mechanistic versus an additional primary
comparison), multiplicity treatment and timing accounting must be declared
before a future freeze. This addition does not change historical E18 arms,
implement a new planner, select a holdout, or authorize an evaluation.

## Work completed before this outline

- Corrected the earlier E18 numerical interpretation and clarified that its
  timing is amortized per context-stage, not standalone request latency.
- Reviewed shared transport, runtime, cache, selection, RNG and reset paths;
  the existing E18 unit suite passes. No production change was justified.
- Localized SAGE repeat drift to after an exact first planning call, which
  makes simulator state-restoration/step-boundary checks a pre-confirmation
  issue for both lineages.

See [shared-infrastructure review](E18-SHARED-INFRASTRUCTURE-REVIEW-2026-09-05.md).

## Requirements for a later freeze

1. Close the bounded reset/state-restoration engineering gate on already
   exposed/development records. Compare supplied and actual simulator states,
   renderings, primitive actions, and RNGs. Any validated correction gets its
   own source history; any changed evaluation stack must be disclosed rather
   than labelled identical to historical E18.
2. Freeze model, adapter and LeWM bytes, action transforms, normalization,
   candidate/continuation counts, best-two scoring, schedules, environment
   budgets, horizons, seed blocks and task weighting. No retraining or tuning
   on confirmation records. Keep greedy-576/GMM secondary only if their role
   and budget are justified and declared before freeze.
3. Agree a practically meaningful target effect, uncertainty requirement,
   multiplicity treatment for the two main comparisons, and sample-size
   calculation. Do not power the study as if the development +19.44-point
   estimate were known truth. Specify failed-cell handling in advance.
4. Freeze task-first aggregation with paired episode clusters. If multiple
   starts/horizons share an episode, keep them in one cluster; fixed training
   seeds are repeated blocks, not independent new episode evidence. Define
   simultaneous inferential claims before looking at outcomes.
5. Only after explicit authorization and an immutable protocol, construct an
   episode-level disjoint set against all training and exposed development
   inputs. Do not create or consume D5 automatically. Record provenance,
   exact IDs and hashes at that later authorized stage, not now.
6. Register separate timing measures: synchronized planner-stage time with
   batch size and amortization explicit; preprocessing; simulator/rendering;
   full episode wall time; peak memory. Lock warmup and aggregation rules.
7. Use the prospective information barrier for the full scientific evaluation:
   all cells complete, integrity/identity checks pass, then release aggregate
   outcomes. Already exposed engineering traces remain inspectable under a
   logged diagnostic scope; they are not an untouched efficacy holdout.

## Separate SAGE track

Do not wait for SAGE to make E18's scientific question meaningful, but do not
treat the released SAGE means as a validated baseline. Await the authors'
exact data/encoding, environment and per-seed outputs before asserting a
specific faithful SAGE reproduction configuration. A future technical repair
can address more than one objectively established defect under a new,
transparent protocol; the old D2 decision remains preserved.

A later matched E18-versus-SAGE comparison cannot use the official paper
manifests because they overlap E18 training (270 PushT and 84 Cube episodes).
The previously generated common untouched candidates (579 PushT, 280 Cube)
are candidate pools, not an automatically authorized confirmation set. No
candidate pool was opened or modified for this outline.

## Current authorization boundary

This document is ready for methodological review. It is not a preregistration,
does not unlock any dataset, and does not authorize a new evaluation. The
remaining design choices and real-input engineering checks must be completed
before a separate confirmation freeze.
