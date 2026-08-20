# ACID-alternative E4-D2B closed-loop implementation freeze

Date frozen: 2026-08-16 (Asia/Nicosia)  
Role: conditional, post-E3 **exploratory development**  
Parent protocol: `ACID-ALTERNATIVE-E4-DIFFUSION-INVERSE-DEVELOPMENT-PROTOCOL-2026-08-16.md`  
Protected material: C1 and I1 remain sealed

## 1. Authorization boundary

E4-D2B may execute only if the immutable E4-D2A analysis says
`all_d2a_gates_pass=true`, its decision is
`authorize_e4_d2b_closed_loop`, and its content-addressed authorization file
validates against the D2A implementation freeze and source manifest. A failed
or incomplete D2A result cancels every D2B job through a scheduler dependency.

This document, the evaluator, cost wrapper, analysis, tests, and SLURM grid are
frozen before any E4-D2A score or outcome is inspected. D2 is exposed
development data. D2B can authorize multi-seed development, but it cannot
support a publication, confirmation, or alternative-to-ACID claim by itself.

## 2. Fixed inputs and planner

Each arm uses the same 50 D2 starts per task, the same frozen Le-WM checkpoint,
the same dataset, and the same environment evaluation code used by the audited
E3 run. The tasks are PushT, Reacher, and Cube. No task may be removed.

The shared planner configuration is:

- planner seed `8401` for every arm;
- CEM with 300 candidates, 30 iterations, and top 30 elites;
- horizon 5, receding horizon 5, and action block 5;
- goal offset 25 and evaluation budget 50; and
- 50 unique episode/start clusters per task.

All scorers consume the single world-model rollout produced for a CEM call.
Lower verifier cost means preferred. Unless explicitly named as a sensitivity
arm, the verifier is combined with goal cost by the published ACID spread rule
with `lambda=0.07`. A verifier with spread at or below `1e-8` has zero weight.
The shuffled E4 arm has reliability zero by construction and returns goal cost
exactly, without adaptive amplification.

## 3. Frozen physical arm grid

One independently optimized closed-loop run is made for every task and arm:

1. `b0`: original CEM goal cost;
2. `acid_l002`, `acid`, `acid_l014`: published one-sample ACID residual at
   `lambda` 0.02, 0.07, and 0.14;
3. `acid_flow`: ACID's flow-training residual evaluated directly on the exact
   proposed action, with four common draws at each E4 scoring level;
4. `acid_16_mean` and `acid_16_min`: mean and per-transition nearest residual
   from 16 ACID inverse samples;
5. `forward`: the existing capacity-matched deterministic forward verifier;
6. `reachability`: the existing learned temporal-reachability comparator;
7. `deterministic_inverse`: capacity-matched inverse action regression;
8. `gaussian_tail`: capacity-matched conditional/current-only diagonal-Gaussian
   likelihood-ratio tail score;
9. `cider_tail_l002`, `cider_tail`, `cider_tail_l014`: the primary calibrated
   inverse-diffusion CIDER tail at `lambda` 0.02, 0.07, and 0.14;
10. `cider_shuffled`: the E4 shuffled-successor artifact with reliability zero,
    required to reproduce B0 exactly;
11. `dide`: direct conditional inverse-denoising energy;
12. `cider_raw`: unthresholded conditional/current-only denoising-energy ratio;
13. `cider_mean_violation`: calibrated mean rather than upper-tail horizon
    reduction.

The primary method is `cider_tail` at `lambda=0.07`. The primary ACID
comparator is `acid` at `lambda=0.07`, because that is the published decision
rule reconstructed from the paper. The stronger ACID energy and multi-sample
arms, Gaussian control, and weight sweeps prevent an apparent win caused only
by one noisy inverse sample, generic conditional-density estimation, or a
lucky penalty weight.

Model seed `7101` is used for E4 and the two newly trained inverse controls.
Seed `6101` is used for ACID, forward, and reachability. Common noise is fixed
by task, artifact seed, horizon, and draw. Published one-sample ACID retains
its candidate-specific, call-indexed Gaussian stream; the exact proposed
action scores use common random numbers across candidates to reduce ranking
noise.

## 4. Fixed endpoints and intervals

The primary endpoint is binary environment success. Report success count and
rate for every task and arm. Bootstrap the 50 paired start clusters within
each task 100,000 times using seed `2026081612`; form the equal-task estimate by
averaging the three task bootstrap estimates. Report two-sided 95% intervals
for levels and paired contrasts and one-sided 95% lower bounds for
noninferiority diagnostics. Also report exact paired discordant-start counts,
wall time, CEM cost calls, peak CUDA memory, and the isolated D2A scorer latency.

Tasks are never pooled by episode count. Every task and every failed or
successful run remains visible. The shuffled arm's episode vector must be
bit-identical to B0 for each task; otherwise the study is invalid rather than
reinterpreted.

## 5. Frozen advancement decision

The parent protocol's seed-7101 gate is implemented literally. E4-D2B advances
to E4-M only if primary `cider_tail`:

1. has a higher equal-task success point estimate than primary `acid`;
2. has a higher equal-task success point estimate than `b0`;
3. is not below `acid` by more than 0.05 in any task;
4. is not below `b0` by more than 0.05 in any task; and
5. exceeds `cider_shuffled` in the equal-task point estimate, while the
   shuffled vector itself exactly reproduces B0.

These are development thresholds, not hypothesis-test significance claims.
Bootstrap intervals and exact paired counts are reported even when they do not
exclude zero.

Three additional labels are kept separate from advancement:

- **diffusion-specific development signal:** `cider_tail` is higher in
  equal-task point estimate than both `deterministic_inverse` and
  `gaussian_tail`, and its one-sided 95% lower contrast bound is above -0.05
  for each;
- **strong-ACID development signal:** `cider_tail` is higher in equal-task
  point estimate than `acid_flow`, `acid_16_mean`, and `acid_16_min`; and
- **weight robustness:** both CIDER sensitivity arms are no worse than the
  primary CIDER point estimate by more than 0.05 equal-task, with the analogous
  ACID sweep reported alongside them.

Failure of either additional label narrows the interpretation even if the
parent advancement gate passes. In particular, beating published one-sample
ACID but not the Gaussian control supports conditional support-ratio scoring,
not a diffusion-specific advantage.

## 6. Integrity and next boundary

- Outputs are write-once and all inputs are SHA-256 checked.
- C1/I1 paths are rejected and never read.
- Outcome-independent bugs require a dated amendment and complete rerun of all
  affected matched arms.
- No arm, task, start, score level, draw, or penalty weight is selected after
  D2B outcomes are inspected.
- If the advancement gate passes, only then may seeds `7102` and `7103` be
  trained and a later method be frozen for genuinely fresh evaluation.
- If it fails, E4 stops under this definition. Any further redesign is a new,
  explicitly post-outcome E5 study.

