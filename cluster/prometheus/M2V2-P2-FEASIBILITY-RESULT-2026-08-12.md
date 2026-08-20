# M2v2 P1/P2 feasibility result

Date: 2026-08-12

## Bottom line

M2v2 is **not operationally promising under the rule frozen before execution**.
It is a genuine intervention and it produces one encouraging exploratory result in
TwoRoom, but it does not rank PushT candidates usefully or improve PushT closed-loop
success. It must not be promoted to P3/P4 or described as a demonstrated alternative
to ACID or a learned reachability metric on the basis of these data.

This is a useful negative/diagnostic result, not evidence that diffusion cannot ever
work. The evidence supports the narrower claim that the present multiscale
conditional-minus-unconditional denoising-error heuristic is not robust across the
two tested environments.

## Frozen redesign tested

- Existing width-1024 conditional M2 plus a newly trained capacity-matched
  zero-source unconditional companion.
- Three seeds, five noise levels, and eight common noise draws.
- Conditional-minus-unconditional squared epsilon-error, standardized only from a
  deterministic 10,000-pair P1-validation subset.
- Exact within-population midrank instead of a global Platt map.
- Five prefrozen weights: 0.25, 0.5, 1, 2, and 4.
- P1/P2 only; no P3/P4 data were read.

The design and decision gates were frozen in
`M2V2-P1-P2-FEASIBILITY-SPEC-2026-08-12.md`, SHA-256
`bc57c4500ed07daa8b43a3c4ef7432861649c854eaf4d6c06858dbc75c7cfb20`.

## P1 validity checks

All six unconditional companions trained and passed checksum validation. Across the
30 seed-by-noise cells, the P1-validation contrast standard deviation was safely
nonzero: approximately 0.872 to 4.499 in PushT and 0.423 to 0.905 in TwoRoom, versus
the prefrozen rejection threshold of `1e-6`.

Thus the downstream negative result is not caused by a collapsed unconditional
model or an identically constant contrast.

## Offline P2 candidate ranking

| Environment | Mixed pools | Pooled AUROC | Pair-weighted within-pool AUROC (95% pool bootstrap) | Top-4 failure reduction (95% pool bootstrap) | Between-pool score variance |
|---|---:|---:|---:|---:|---:|
| PushT | 3/12 | 0.2573 | 0.5045 [0.3333, 0.7619] | -0.02734 [-0.06901, 0.00260] | 99.996% |
| TwoRoom | 4/12 | 0.7486 | 0.5817 [0.1865, 0.6613] | +0.02995 [-0.00521, 0.09245] | 99.087% |

PushT is the decisive weakness: M2v2 is essentially at chance within pools, its
top-4 direction is harmful, and almost all score variation remains between queries.
TwoRoom is suggestive but too imprecise to establish useful ordering.

## Paired P2 closed loop

Every one of the 120 M2v2 tasks completed. Every scored CEM population passed the
nonzero-span gate, and every selected-weight trajectory changed relative to B0 in
both environments. Therefore this was an actual planner intervention, unlike the
old TwoRoom M2 grid whose zero Platt slopes made its penalty constant.

| Environment | B0 | w=0.25 | w=0.5 | w=1 | w=2 | w=4 | Prefrozen selected result |
|---|---:|---:|---:|---:|---:|---:|---|
| PushT | 2/12 | 2/12 | 2/12 | 1/12 | 1/12 | 1/12 | w=0.25: 2/12; 1 paired win, 1 loss; exact p=1.0 |
| TwoRoom | 6/12 | 5/12 | 6/12 | 6/12 | 4/12 | 8/12 | w=4: 8/12; 2 paired wins, 0 losses; exact p=0.5 |

The TwoRoom `8/12` result is encouraging but exploratory: the weight was selected on
these same twelve P2 queries, the exact paired test is not significant, and selected
M3 also achieves `8/12` with a different success pattern. In PushT, selected M2v2
does not improve B0 and is below the existing selected M1/M2/M3 counts of 5/12,
4/12, and 3/12.

## Prefrozen decision

The five decision components evaluate as follows:

1. all online population span gates pass: **yes**;
2. within-pool AUROC point estimate exceeds 0.5 in both environments: **yes**, but
   only barely in PushT and with wide intervals;
3. top-4 reduction is positive in one environment and nonnegative in the other:
   **no**, because PushT is -0.02734;
4. selected closed-loop arm gains at least two successes in one environment and
   loses no more than one in the other: **yes**;
5. selected arm changes at least one trajectory in both environments: **yes**.

Because all five were required, the overall decision is **false**. Per the frozen
rule: do not continue tuning M2v2 on P2 and do not promote this configuration. Pivot
the thesis toward the diagnostic/comparative contribution or the stronger M3 line.

## PushT conduct check

There is no current evidence that PushT was conducted incorrectly. Before M2v2, an
independent audit validated all 540 P2/P3 execution files and 34,560 candidate-repeat
records, including query/seed mappings, state traces, labels, hashes, and zero P2/P3
episode overlap. A separate 23,040-execution reset probe found zero primary or
released label flips from the released `_set_state` physics step. M2v2 reused that
same released simulator and closed-loop harness, and all new artifacts passed their
hash and span checks. The PushT negative result is therefore best treated as a model
failure unless new concrete contrary evidence appears.

## Compute cost

M2v2 is materially more expensive than the original single-sigma M2:

- PushT mean execution: 230.65 s/query, including 169.78 s of scorer time. Original
  M2 averaged 145.43 s/query and 36.71 s scorer time.
- TwoRoom mean execution: 19.84 s/query, including 4.00 s scorer time. Original M2
  averaged 17.20 s/query and 1.14 s scorer time.
- Maximum recorded PyTorch allocation was about 627 MB in PushT and 482 MB in
  TwoRoom; runtime, not memory, is the main cost.

## Canonical artifacts

- Training: Slurm array `296277` (six completed tasks).
- P1 references: job `296281`.
- Offline P2 audit: job `296282`.
- Real PushT smoke: job `296283`.
- Full P2 grid: job `296284` (120 completed tasks).
- Prefrozen decision: job `296285`.
- Decision manifest SHA-256:
  `fbba7d8bff1f42031bea855f4d050e37d33acd72ddd45fe0ff777d07527de491`.
- PushT offline audit manifest SHA-256:
  `0af7176d645f3413e70358bf6352d2e3cf22214e08745734042a3521d4e275aa`.
- TwoRoom offline audit manifest SHA-256:
  `ab058cf518f972978c16f032f5130f6dc3edc7f08464b111ec33602ccdc20e66`.
