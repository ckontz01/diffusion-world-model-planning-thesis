# ACID-alternative v3 amendment 2: restore declared secondary comparators

Date logged: 2026-08-16 11:45 EEST  
Applies to: `ACID-ALTERNATIVE-V3-MULTISEED-D2-PROTOCOL-2026-08-16.md`  
Protocol SHA-256: `c38e086ee09cbabaa9ab53246add92835d59f95173b5f35290f474abb94a4dfb`

## Timing and outcome status

This amendment was made before a D2 manifest, candidate pool, physical
execution, score, or outcome existed. The superseded chain (`297508` through
`297515`) was cancelled while only P1 scorer-training array elements were
running. No D2 partition was selected or opened and no D2 artifact was
created. The partial training artifacts from that cancelled chain are invalid
and may not be reused.

The superseded source-manifest SHA-256 was
`ba0be723b4f057f1a2838a3cccc23dd74ea86df306543bc8ced742a0738ba1b6`.
A new immutable source snapshot and source-manifest hash are required for all
reruns.

## Corrections

1. The v2 rescue design specified learned reachability and the v1 raw
   diffusion transition verifier (DTV) in the eventual D2 comparison, but the
   v3 protocol accidentally omitted them while retaining ACID, deterministic
   forward, RDX, and AE. Both omitted methods are restored as secondary,
   descriptive comparators in Stage A and Stage B. This repairs baseline
   continuity; it does not create a new primary endpoint or scientific gate.

2. Learned reachability uses the already frozen v1 true-label checkpoints,
   scores each imagined sequence from its terminal predicted latent to the
   goal latent, and uses `lambda = 0.07`. Raw DTV uses the already frozen v1
   true-label epsilon-prediction checkpoints, sigmas `0.10/0.25/0.50`, the
   previously specified deterministic common-noise construction, and
   `lambda = 0.005`. All three scorer seeds are evaluated. Stage B therefore
   contains eight arms and 72 matched task/arm/scorer-planner-seed runs.

3. Stage A now reports the selected task-specific final and minimum distance
   where those measurements are present. This implements the reporting item
   already required by Section 6 and does not affect any selection or gate.

4. Timing records retain the protocol-required time per horizon transition
   and additionally count actual network-pair evaluations. The latter is five
   per sequence for forward and ACID, 15 for three-scale raw DTV, one for
   terminal-to-goal reachability, and 240 for the joint RDX/AE calculation
   (five transitions by three noise scales by eight draws by conditional and
   unconditional passes). This is reporting-only; the timed inference paths
   and endpoint values are unchanged.

The two diffusion endpoints (RDX and AE), model weights, data split, scorer and
planner seeds, candidate pools, bootstrap streams, thresholds, and all five
Stage-A and all five Stage-B gates remain unchanged. Learned reachability and
raw DTV are descriptive comparators only and cannot authorize Stage B, rescue
a failed gate, or replace AE in the alternative-to-ACID claim.
