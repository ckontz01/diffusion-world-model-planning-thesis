# ACID-alternative v3 amendment 1: pre-outcome provenance and timing repair

Date logged: 2026-08-16 11:15 EEST  
Applies to: `ACID-ALTERNATIVE-V3-MULTISEED-D2-PROTOCOL-2026-08-16.md`  
Protocol SHA-256: `c38e086ee09cbabaa9ab53246add92835d59f95173b5f35290f474abb94a4dfb`

## Timing and outcome status

This amendment was made before a D2 manifest, candidate pool, physical
execution, score, or outcome existed. The superseded Stage-A chain
(`297493` through `297500`) was cancelled while three training-array elements
had run for approximately four minutes. Its only completed scientific
artifact was the outcome-independent preflight from job `297492`; no D2 data
were selected or opened. Partial training artifacts from the cancelled chain
are invalid and may not be reused.

The superseded source-manifest SHA-256 was
`4f9b6b85f6f7043c486e4ed0959864584a9a53d9ca83f58ac2c0d68bf316b694`.
A new immutable source snapshot and source-manifest hash are required for all
reruns.

## Corrections

1. Section 6 required scorer parameter counts and scoring latency, but the
   initial analysis path recorded parameter counts without an exact
   per-scorer latency measurement. Each scorer now receives one complete
   300-candidate warmup pool followed by one CUDA-synchronized pass over all
   50 by 300 candidate sequences. The record excludes model loading and the
   shared Le-WM rollout and reports seconds, milliseconds per candidate
   sequence, and microseconds per transition. Residual diffusion reports the
   joint cost of producing RDX and AE because both outputs reuse the same
   conditional and unconditional denoiser evaluations.

2. Section 4 required the reconstructed ACID inference-noise stream to be
   keyed by task, scorer seed, planner seed, and cost-call index. The initial
   implementation seeded one persistent generator from only the first three
   fields and advanced its state implicitly. It now derives a fresh seed from
   all four declared fields for every cost call. Candidate and horizon tuples
   still receive independent Gaussian samples, with one sample and one Euler
   step exactly as frozen.

3. D2 scoring and closed-loop evaluation now reject a task, dataset,
   evaluation manifest, D2 provenance record, or upstream source-manifest hash
   that does not match the current immutable source snapshot. Parameter counts
   are also recomputed from loaded residual models and checked against their
   training summaries.

These are outcome-independent implementation and reporting repairs under
Section 8. They do not change either diffusion endpoint, any learned weight,
model, checkpoint rule, scorer seed, planner seed, data-selection rule,
bootstrap stream, metric, threshold, or scientific gate.
