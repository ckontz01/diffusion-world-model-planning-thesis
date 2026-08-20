# ACID-alternative E3: exploratory D2 closed-loop protocol

Date frozen: 2026-08-16 (Asia/Nicosia)  
Role: post-v3 **exploratory development**, after inspection of v3 Stage-A results  
Protected material: C1 and I1 remain sealed and may not be read, scored, or executed

## 1. Why this follow-up exists

The frozen v3 fresh-D2 Stage-A audit passed four of five gates and stopped
before Stage B, as required. Its failed gate concerned **RDX**, the raw
residual-diffusion candidate-failure ranker, which did not establish
non-inferiority to the capacity-matched deterministic forward verifier. The
two gates directly concerning **AE**, the conditional-versus-unconditional
diffusion action-evidence score intended for planning, passed.

Consequently, v3 answered whether the fixed diffusion endpoints carried
candidate-level information, but it did not answer whether AE improves an
independently optimized CEM planner. This E3 study asks that remaining
closed-loop development question without changing the endpoints, models,
weights, tasks, seeds, or decision thresholds.

This is not v3 Stage B and does not override its failed authorization. The
v3 result remains `stop_before_stage_b`. E3 was authorized only after that
result was inspected, so every E3 result is exploratory even though the
closed-loop outcomes themselves have not previously been generated.

## 2. Claim boundary and irreversible decision

The strongest possible E3 conclusion is:

> On the already inspected D2 development starts, the frozen AE planner passed
> or failed the original closed-loop promotion criteria against original CEM,
> a published-equation ACID reconstruction, deterministic forward
> verification, and a shuffled-action AE control.

E3 cannot support a publication claim that diffusion is an alternative to
ACID. If all gates pass, AE is frozen permanently and promoted to a genuinely
new untouched confirmation study, followed by a PLDM cross-backbone test. If
any gate fails, development of diffusion scoring on the Le-WM data stops and
the thesis pivots to a controlled comparison/negative result. No additional
D2 score, mixture, weight, seed selection, task deletion, or endpoint redesign
is allowed after E3 outcomes are read.

## 3. Frozen upstream evidence and inputs

E3 reuses the exact audited v3 inputs:

- v3 protocol SHA-256:
  `c38e086ee09cbabaa9ab53246add92835d59f95173b5f35290f474abb94a4dfb`;
- final v3 source-manifest SHA-256:
  `2c8f890c31e9f5bf5e8b6769ccc424d7cd565278c422405d507d1c702d3580ea`;
- v3 Stage-A summary SHA-256:
  `0af2181b1060d761a295c885f2eae34af47a0fd94992a8f3a59cf05e57ecbe37`;
- v3 Stage-A manifest SHA-256:
  `3558b8612787035cfa92c17d8a36f46f379bb2812f67aa0a73438d8cab974053`;
- v3 Stage-A analysis job `297565`, whose decision is
  `stop_before_stage_b`, whose all-gates value is false, and whose
  `protected_c1_i1_read` value is false;
- D2 manifest job `297535`: 50 unique P3 episodes/starts per task, selected
  with seed `2026081603`, excluding R0 and separated at episode level from P1,
  D1, C1, and I1;
- exact D2 manifest/provenance SHA-256 pairs:
  - PushT: `85fd2bc499892be09a5e92000aab879e314ebc3100b11017c3864104d4d25e89`
    / `fcb07dfb55822bc6717c56016f62f26646a7486b8c834762d4bf0fd8eb771ede`;
  - Reacher: `a8683cccfd998017fdf52f21ec6b3a588a4cbda2578049ba007f8bd4f817fd61`
    / `f175561fd58908ef9d226c4dcd9bda0e67d8dd4adfe1d01b35a4a3dd2fe46a11`;
  - Cube: `bd131f4fc43e69311cf9722dfd678abb7cf888fe067ddf00f7310ff866eb7388`
    / `fa0dfb090aadeb1daadaf703707a64f049cac988c1c9074f0a09345eebb8a62b`;
- residual-diffusion training array `297533` for scorer seeds 6102 and 6103,
  plus the already frozen v2 seed-6101 checkpoints;
- the three audited ACID and deterministic-forward checkpoints per task;
- the released Le-WM checkpoints, datasets, preprocessing, and environment
  implementation used by v3.

The E3 authorization record must verify all frozen hashes above and must
explicitly record that it authorizes exploratory development only. It must
reject a passing-Stage-B or confirmatory interpretation.

## 4. Fixed tasks, arms, and seeds

Tasks are PushT, Reacher, and Cube. The six and only six closed-loop arms are:

1. `b0`: original CEM using goal cost alone;
2. `acid`: the audited published-equation ACID reconstruction;
3. `forward`: the capacity-matched deterministic forward verifier;
4. `rdx`: conditional clean-residual diffusion error;
5. `ae`: conditional-versus-unconditional log diffusion error ratio;
6. `ae_shuffled`: the matched shuffled-action AE control.

Learned reachability and legacy DTV are not E3 arms. Their existing results
remain descriptive evidence, but adding them here would silently enlarge the
agreed six-arm decision study.

Scorer seeds are `6101`, `6102`, and `6103`, paired respectively with planner
seeds `8301`, `8302`, and `8303`. B0 is rerun for all three planner seeds.
This gives 3 tasks x 6 arms x 3 paired seeds x 50 starts = **2,700 closed-loop
episodes** in 54 independent task/arm/seed runs.

## 5. Planner and scorer configuration

Every arm retains the v3 configuration:

- identical D2 starts, goals, world-model checkpoints, datasets, transforms,
  evaluation budget, and environment code;
- goal offset 25 primitive steps and evaluation budget 50 primitive steps;
- five Le-WM transitions, five primitive actions per transition;
- CEM population 300, 30 iterations, 30 elites, variance scale 1.0;
- identical planner seeds and CEM innovations within each paired unit;
- residual sigmas `{0.25, 1.0, 4.0}`, eight fixed draws per sigma, mean over
  five transitions, and adaptive spread weight `lambda = 0.005`;
- ACID's one deterministic independently keyed Gaussian draw per candidate
  and transition, one Euler step, and adaptive spread weight `lambda = 0.07`;
- unchanged RDX and AE signs, reductions, checkpoints, action
  standardization, and numerical epsilons.

Each arm independently affects all 30 CEM iterations, so candidate populations
may diverge after their first update. No Stage-A captured candidate pool or
physical outcome is consumed by the evaluator.

## 6. Frozen analysis

The primary endpoint is environment success. The paired unit is
`(task, D2 start, scorer/planner seed)`. Report each task separately and the
equal-task average; never pool episodes in proportion to task size.

Use 100,000 task-stratified start-cluster bootstrap repetitions with seed
`2026081605`. Resample starts within each task while keeping the three paired
seeds and all arms together. Report two-sided 95% intervals, one-sided bounds
where the corresponding gate is one-sided, and the exact paired sign-test
sensitivity analysis already implemented for the v3 closed-loop design.

Report success for every arm, all AE contrasts, the RDX contrasts with B0 and
ACID, per-run wall time, GPU identity, peak VRAM, CEM call counts, and all
failed runs. Secondary environment metrics returned by the evaluator may be
reported descriptively but cannot replace success in a gate.

AE passes the E3 promotion decision only if all five original closed-loop
requirements hold:

1. AE minus ACID has a one-sided 95% lower bound above `-0.05` equal-task and
   above `-0.10` in every task;
2. AE minus B0 has a two-sided 95% lower bound above zero equal-task;
3. AE minus shuffled AE has a two-sided 95% lower bound above zero equal-task;
4. AE is not more than 0.10 below B0 in any task and has a higher point
   estimate than B0 in at least two tasks;
5. AE minus deterministic forward has a one-sided equal-task 95% lower bound
   above `-0.05`.

RDX is secondary and cannot replace AE. All gates are reported even if an
earlier gate fails.

## 7. Outcome isolation, provenance, and repairs

- The protocol, authorization logic, evaluator, analyzer, launch scripts,
  source manifest, arm grid, and all referenced upstream hashes are frozen in
  a new content-addressed read-only snapshot before submission.
- Every result directory must be absent before its job starts. Every summary
  records source/protocol/authorization/checkpoint/dataset/manifest hashes,
  seeds, Slurm identifiers, runtime versions, GPU, and
  `protected_c1_i1_read=false`.
- The evaluator rejects any path containing a C1/I1 protected-data token and
  accepts only the recorded D2 manifest provenance.
- No E3 result may be labelled fresh, confirmatory, preregistered before D2,
  v3 Stage B, or evidence of an alternative-to-ACID claim.
- An outcome-independent implementation error may be repaired only through a
  dated amendment that preserves the estimand and invalidates/reruns every
  affected matched arm. Improvements or new analyses wait until after the
  irrevocable pass/fail decision and cannot change it.
- C1 and I1 remain untouched regardless of E3's outcome.

## 8. Required terminal decision

If every gate passes, write `promote_ae_to_new_confirmation`; freeze AE's
model, score, weight, planner integration, and analysis, then create a new
untouched confirmation set specifically for this frozen method. The old C1/I1
artifacts are not repurposed.

If any gate fails, write `stop_diffusion_development_and_pivot`; do not run
another Le-WM diffusion redesign. The thesis then reports the complete
controlled evidence comparing inverse dynamics, deterministic forward
prediction, diffusion-derived action evidence, and learned reachability,
including the negative planning result where applicable.
