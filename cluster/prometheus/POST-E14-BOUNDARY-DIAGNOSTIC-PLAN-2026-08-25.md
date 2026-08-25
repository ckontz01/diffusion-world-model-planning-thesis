# Post-E14 frozen-VAD boundary diagnostic plan

Date fixed before diagnostic execution: 25 August 2026

Role: outcome-informed P1 development-artifact diagnosis only

Method-selection or confirmation authority: none

## Purpose

E14 stopped before Gate C because every Cube VAD seed exceeded the prewritten
25% robust-boundary threshold. That stop remains valid. The stored E14 metric,
however, counted exact equality after clipping proposals to the 0.1% and 99.9%
P1-train action quantiles. It did not establish whether raw proposals exceeded
the environment's legal action limits, whether the world-model selector chose
the clipped candidates, or whether the same behavior was common in the expert
actions used for training.

This diagnostic answers those descriptive questions before any E15 design is
frozen. It cannot revise E14, choose a transform, tune a threshold, or authorize
new closed-loop or confirmation evaluation.

## Immutable inputs

For PushT and Cube, and model seeds 6101, 6102, and 6103, the diagnostic uses:

- the frozen E14 P1 train and episode-disjoint P1-validation cache;
- the frozen selected `vad_true` EMA checkpoint;
- the released frozen Le-WM checkpoint;
- the exact E14 candidate count, five-step deterministic sampler, guidance,
  candidate RNG seed, condition-cell order, and batch size;
- the frozen full E14 Gate-B `vad_true` row metrics; and
- the deployed environment source defining legal action spaces of `[-1, 1]`
  in every primitive-action dimension.

It regenerates no D3, D4, or D5 data. It must not read D3, D4, D5, P3, P4,
C1, or I1 metric-bearing files. P2 is not used.

## Required reproduction check

Full mode must regenerate all 40,000 P1-validation proposal banks per
task/seed and reproduce every stored E14 per-row robust-boundary fraction with
absolute tolerance `1e-7` and zero relative tolerance. Failure is a technical
validity stop. Smoke mode shares the original RNG stream only for its first
condition and therefore verifies that first row only.

## Frozen measurements

All rates exclude duration padding. The diagnostic reports, separately for
the full 300-candidate bank and the Le-WM-selected candidate:

- raw fraction outside P1 robust bounds;
- raw fraction outside environment legal bounds;
- exact robust-bound mass after E14 clipping;
- mass within relative boundary margins
  `{1e-6, 1e-4, 1e-3, 1e-2, 5e-2}` for robust and legal bounds;
- clipping displacement divided by robust-bound span;
- candidate variance before and after clipping; and
- unique candidate count before and after clipping at E14's `1e-4`
  standardized-action precision.

The rates are reported by task, seed, far-goal offset `delta`, local duration
`tau`, primitive-action dimension, and option time step. P1 training-cache and
validation-cache expert actions receive per-dimension quantiles, robust-bound
and legal-bound exceedance rates. These describe the exact distribution seen
by E14 training; they are not mislabeled as the unique-action distribution of
the original episode dataset.

## Interpretation discipline

This diagnostic has no pass/fail scientific gate beyond faithful
reproduction. In particular:

- a high robust-bound rate is not automatically called pathological;
- a low legal-bound violation rate does not erase the E14 validity failure;
- selected-candidate behavior is kept distinct from full-bank behavior;
- no boundary threshold may be chosen from these outputs and then portrayed
  as pre-registered; and
- no E15 endpoint, transform, loss, control, horizon, or gate is selected by
  this document.

After all six full cells are complete and validated, their findings may inform
one separately written and hashed E15 development protocol. D5 remains sealed
unless that later protocol passes its own prewritten offline and fresh P2
closed-loop development gates.
