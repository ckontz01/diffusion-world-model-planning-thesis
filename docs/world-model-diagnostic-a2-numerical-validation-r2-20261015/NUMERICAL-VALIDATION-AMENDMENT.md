# WM-DIAG0-A2 numerical validation amendment request

Status: disabled proposal for the human's scientific and resource decision. The campaign remains stopped. No new inference, implementation of the amended gate, or resumption is authorized by this document.

The original full uncached DINO parity check failed. An encoding-only diagnostic also found a discrepancy between encoding one RGB image and encoding 16 repetitions together. A reference conditioned on the same encoded input could test the recurrence separately, but cannot turn the original end-to-end failure into a pass. Pro reviewed the immutable code and receipt and requested this explicit amendment rather than a production change.

## Frozen numerical routes

All DINO routes use the same authenticated encoder bytes and pinned source. RGB starts as HWC uint8, becomes CHW float32 divided by 255, then Resize224, CenterCrop224 and normalization by mean and standard deviation 0.5. The native encoder transform resizes to 196 pixels, yielding 196 patches of 384 float32 exported coordinates. Encoder and predictor execution use the fixed BF16 autocast. No precision or preprocessing change is proposed.

| Role | RGB batch | Feature shape and ownership |
|---|---:|---|
| Readout fitting and validation | 8 | Each image produces 196 by 384 features. The accepted fit uses 256 frames and validation uses 96 per setting. No validation tuning. |
| Realized oracle prefix | 5 | The five sampled frames produce 5 by 196 by 384 features, owned by that fresh candidate prefix. |
| Source and goal | 1 | T=1 source and terminal goal encodings are cached in a fresh solve dictionary. Retained-bank prediction has a history-keyed cache owned by the fixed adapter. No cross-root or changed-observation reuse. |
| Original uncached reference | 16 | The same source RGB is expanded before encoding, then passed through original VWorldModel.rollout. No production cache is supplied. |

Actions remain five groups of five distinct 2D physical actions, normalized by the existing constants. DINO planning retains chunks of 100, recurrent nonvisual channels, up to three latent history entries, constant-zero measured proprioception, original terminal visual MSE and branch-owned tails. Le-WM and its gate are unchanged.

## Separate acceptance obligations

| Obligation | Current status |
|---|---|
| Original full uncached RGB-to-forecast parity | Failed at the frozen rtol 2^-6 and atol 2^-8; preserved, not superseded as a pass. |
| Native recurrence conditioned on the same canonical visual input | Proposed and not tested. It would establish conditional recurrence agreement only. |
| Comparability of actual role batches 1, 5 and 8 | Not established. The measured discrepancy concerns batches 1 and 16, not those other pairs. |

The batch1-versus16 diagnostic found 521,584 of 1,204,224 visual coordinates outside tolerance, with maximum absolute discrepancy 2.336855411529541. Action and constant-proprio encodings matched exactly. This identifies an input-path non-equivalence, not a particular kernel cause, its scientific materiality, or the absence of another downstream discrepancy. Similar terminal scalar costs do not establish full feature equivalence.

## Reference only amendment design

Leave the experimental adapter, accepted heads, scores, bank and scientific grid byte-identical. Only the proposed reference acceptance basis would change, explicitly for DINO. The failed PushT uncached comparison remains failed; the original Reacher uncached comparison remains untested, not passed.

For the retained failed PushT bank, compute a canonical source visual tensor independently through the pinned original encoder at batch1. Authenticate its RGB, preprocessing, model and configuration identities. Require exact equality with the adapter's actual initial cached visual tensor. Do the corresponding batch1 goal check.

A separately reviewed, statically named reference subclass would inherit the original VWorldModel.rollout, encode, encode_act, encode_proprio, predict, replace_actions_from_z and separate_emb methods. Its only override would supply the authenticated canonical float32 visual tensor at the returned encode_obs['visual'] boundary, expanded to the 16 candidates. Its proprio output would still be independently computed by original encode_proprio from the allowed constant zeros. Raw RGB identity and T=1 are checked before the boundary. It must never receive adapter-predicted trajectories or action/proprio encodings.

The original native recurrence would therefore independently execute action encoding, autoregression, causal masking, nonvisual propagation, action replacement, temporal indexing and output extraction. Compare all five visual forecast positions at the unchanged tolerance; retain exact cached-cost bits and the unchanged terminal-cost tolerance. The claim would be conditional recurrence agreement, not original uncached RGB-to-forecast equivalence. No reference wrapper is implemented now.

## Proposed minimum additional measurement

Use only the two already accepted root000 RGB windows, one per task. Fix five common frame indices [20, 26, 32, 38, 44] and an eight-image context [20, 23, 26, 29, 32, 35, 38, 44]. No training labels, readout outputs, choices or efficacy enter this selection.

For each task, encode the five common images individually, as the five-image batch, and within the eight-image batch. Repeat that exact sequence once to check same-route repeatability. Compare matching images, not different frames. This requires 14 visual encoder calls and 36 frames per task: 28 calls and 72 frames overall. It also executes 28 native constant-proprio encoder calls, 28 native batched Resize196 operations, and 72 per-image preprocessing pipelines. There are no action-encoder, predictor, scorer, CEM or physics calls in this component.

Compare full float32 patch features under the existing tolerance, and same-route repeats for exact bits. Preserve input/feature identities and numerical discrepancy counts. These fixed mixed-image contexts qualify only the tested inputs; they cannot establish arbitrary batch invariance. No FP32/backend/precision sweep, alternative root, tolerance search or selection of the most agreeable execution path is proposed.

The conditional recurrence component uses the existing 16-candidate bank. Its production forecast, independent cached-cost forecast and original conditional native forecast require 15 predictor batch calls, seven action-encoder calls, nine proprio-encoder calls, six actual visual encoder calls/frames, three counted cost/reforecast API operations and three terminal-score reductions. The native reference's fixed visual supplier performs no encoder forward. No CEM, world reset or controller action is needed for these checks.

Combined new verification workload: 34 actual visual encoder calls and 78 frames, 37 proprio calls, seven action calls, 15 predictor calls and three cost/reforecast API operations. The two frozen task adapters require two original predictor-bundle deserializations and two restricted encoder-state loads inside the already authorized cluster runtime; no acquisition or host loading. The explicit reference constructor reuses authenticated read-only modules without another checkpoint load. No optimizer, training, decoder, S1 scorer or simulator runs.

Propose one finite 180-second GPU allocation, 120 work plus 60 preservation, on the existing exact GPU/node, with four CPUs and 8GiB. The proposed 26MB output allowance retains the production predicted array, goal array, strict manifests and compact numerical evidence, with 100KB logs. Reference and role comparisons run in memory; they do not publish scientific aggregates. Persisting these forecast arrays is necessary for later authenticated reuse: failed in-memory forecasts from job317171 were not saved. Stop on any failed check; do not retry automatically. This allocation remains disabled.

## Accepted failed and remaining work

All 120 source windows, four readouts and PushT Le-WM root000 are accepted and their sealed members were reauthenticated. Preserve and reuse them, without refitting or rerunning. The old source-generation failure and authorized single same-seed persistence retry remain included in CPU and physical accounting.

Original DINO job317171 failed after its helper reset and 20 replay actions, bank construction and three forecast paths, before any oracle/evaluation branches or additional restoration checks. Its six saved bank/trace/proof files are content-authenticated. Reconstruct and independently validate the bank from those bytes before reuse; do not rerun CEM or pretend its unsaved forecasts exist.

The remaining scientific work is three included technical parents, 124 grid parents and CPU analysis. The proposed new validation would supply sealed forecast/goal/tensor-check evidence to a later versioned continuation of the failed parent. That continuation would still perform its ordinary fresh helper and both additional fresh replay checks, then every required oracle/evaluation world. It must authenticate the saved source, bank, forecasts, head and reference receipt before use. This continuation and its independent validator are not implemented or declared ready.

## Exact proposed resource gap

Current actual charges are 249 GPU allocation-seconds and 1,436 CPU-stage seconds. The encoding-only diagnostic contributed 13 GPU seconds, 17 encoded frames and zero predictor calls or resets. All failures remain charged.

| Cumulative quantity with full remaining work | Existing maximum | Proposed total | Exception needed |
|---|---:|---:|---:|
| DINO predictor batch or chunk calls | 950,740 | 950,755 | +15 |
| Cost and reforecast API operations | 126,856 | 126,859 | +3 |
| Retained-bank reforecast sequences | 2,048 | 2,064 | +16 |
| Additional technical parity sequences | 128 | 160 | +32 |
| Predicted macro sequence transitions | 190,090,880 | 190,091,120 | +240 |
| World resets | 6,401 | 6,402 | +1 PushT reset |
| PushT reset-internal integrator steps | 6,400 | 6,402 | +2 |

The forecast and API increments are alternative units of the same repeated work, not separate extra workloads. No exception is implemented. An independently validated helper-free continuation could avoid the reset increment, but no such implementation or receipt exists; this straightforward proposal does not depend on it.

Other full-future ceilings fit without transfer between budgets:

- GPU allocation-seconds: 249 + 180 + 127 times 3,600 = 457,629, below 468,000. All required remaining allocations retain their full bounds.
- CPU-stage seconds: 1,436 + 3,600 analysis + 1,800 unused conversion reserve = 6,836, below 13,800. The conversion reserve remains unconsumed and unreassigned.
- Le-WM predictor calls remain 317,140; native CEM decisions remain 4,224 and CEM sequences remain 38,016,000 because the failed bank is reused.
- Controller actions are at most 386,812, below 386,924. The accepted Le-WM parent used 132 fewer than its maximum; this is resource metadata, not an efficacy-based selection. PushT actions are at most 193,328, total Pymunk integration steps 1,939,682, and Reacher dm_control/MuJoCo steps 386,968. Their existing aggregate limits remain unchanged.
- Actual-code full-future encoded-frame bound is 142,987, below 265,360, including all heads, accepted/failed work, the 17-frame probe and proposed 78-frame verification. This uses the source/goal cache once per DINO CEM solve, not a refund of a charge.
- Conservative live reservation: 12,844,699,989 plus 10MB failed-DINO evidence/control allowance, 1.1MB completed probe allowance, 26.1MB new verification/output/log allowance and 1MB new decision/source/copy allowance = 12,882,899,989 bytes, below 13GB. Existing 14GB archive and 44GB inclusive caps remain unchanged. A reused forecast must be hardlinked or counted again, never assumed free.

The finite proposed all-study GPU-attempt bound becomes 135: 132 successful scientific tasks, the retained failed DINO attempt, the completed encoding-only probe and one proposed verification allocation. Pending cancellations that never allocated are not charged as executed attempts. No additional failure/replacement envelope is implied.

The existing nonrefundable 2,000-second preparation charge still covers this documentation; cumulative charged preparation remains 14,104.10301460012 seconds. No new allowance, installation, model download or monitor is requested.

## Required decision and stop

The human must explicitly review the reference-only gate split and the listed finite resource exceptions before any proposed measurement. The evidence must then return for the interpretation decision: a frozen operational four-pipeline comparison is not automatically an encoding-invariant consequence substitution. Any actual representation, precision or readout change requires a different reviewed amendment, not a technical relabeling.

Approving this request would authorize only the specified numerical verification after its code, independent checks, exact frozen contract, publication and SSD preservation are complete. It would not immediately launch the remaining grid or call the original uncached gate passed. The required role compatibility and interpretation decisions remain visible.

## Preserved evidence

Original scientific source: 8aede74fef94f220f46087e4354124f078d4ca33; contract f08e53e73035171340fe2438e3061685a3be6d1f18a8b132540717bd447a60dc. Encoding diagnostic source: 6927cef4382d87d33993cb3803e39556d2c00be9. [Numerical finding](https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/4fb2db44788e9b08fe92626a0b1a5a80dd63bd57/docs/world-model-diagnostic-a2-parity-r1-20261015/ENCODING-FINDING-001.txt) and [exact probe receipt](https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/4fb2db44788e9b08fe92626a0b1a5a80dd63bd57/docs/world-model-diagnostic-a2-parity-r1-20261015/OBSERVE-ONE.json) remain immutable. The original STOPs, failures, authorities and packages remain unchanged.

Pro's completed scientific decision is in the [existing reasoning chat](https://chatgpt.com/c/6a8714c3-0da0-83eb-b9e5-9171a1dadcd5). Computer Use delivered the request after a transient model-loading error; one persisted request received the completed review. Only this new compact decision package is to be preserved, not old archives. Any eventual final-study archive must include the new diagnostic and amendment lineage as well as the original study records.
