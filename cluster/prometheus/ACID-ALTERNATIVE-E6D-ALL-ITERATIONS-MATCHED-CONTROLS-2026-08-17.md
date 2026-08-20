# ACID-alternative E6D: all-iterations matched-control diagnostic

Date frozen: 2026-08-17  
Role: post-E6, exposed-D2 mechanism diagnosis  
Confirmation status: **not confirmation**  
Protected data: **C1 and I1 remain sealed and must not be read**

## Why this diagnostic exists

E6's sole primary endpoint, tail-five RDX gating at rejection fraction 0.40,
failed all five frozen pilot gates and must stop before D3. E6 also contained
a predeclared integration ablation that applied the same true-action RDX gate
in all 30 CEM iterations. That secondary arm reached an equal-task success
rate of `0.85333`, versus `0.81333` for the primary arm, `0.82000` for B0,
and `0.88000` for continuous ACID. Its task rates were PushT `0.88`, Reacher
`0.78`, and Cube `0.90`.

Those observed numbers are explicitly post-outcome method-development
evidence. The all-iterations arm cannot replace E6's failed primary endpoint.
It also lacks integration-matched shuffled-diffusion and non-diffusion
controls. E6D supplies only those missing controls. It does not retest or
promote E6 and cannot support a publication claim.

## Frozen inputs and anchors

- Tasks, 50 D2 starts per task, datasets, Le-WM checkpoints, preprocessing,
  seed-6101 scorers, planner seed 8301, and CEM configuration are identical to
  E6.
- E6 analysis job: `297657`.
- E6 analysis SHA-256:
  `84ae66457c70f5a8c386d682dab5a77bfd807f3fdf0c52de0ea7b3264ebbc0cc`.
- E6 immutable source-manifest SHA-256:
  `8af433ca7339f42c762b35b1f53d4e485926573531d66cd4bbe872f960240c1e`.
- The exact E6 `rdx_gate_all_q40` and `acid_cont` episode vectors are frozen
  anchors; E6D does not rerun or alter them.

No D3, C1, or I1 data may be selected or opened.

## New closed-loop arms

All arms reject the worst 40% of each 300-candidate verifier ranking during
all 30 CEM iterations. Feasible candidates retain Le-WM goal-cost ordering;
exactly 180 candidates remain eligible for the 30 elites.

1. `rdx_shuffled_gate_all_q40`: the seed-6101 residual-diffusion model trained
   with shuffled actions; integration-matched causal null.
2. `forward_gate_all_q40`: the seed-6101 capacity-matched deterministic
   forward verifier; integration-matched non-diffusion control.
3. `acid_gate_all_q40`: the seed-6101 published-equation ACID reconstruction
   used as a hard gate; score-family/integration diagnostic.

There are exactly nine new runs: three tasks by three arms. No cutoff,
tail-length, sign, weight, or task-specific setting may be changed.

## Frozen decision rule

The primary diagnostic contrast is the existing true-action all-iterations
RDX gate minus the new shuffled-action all-iterations RDX gate. Report paired
per-task and equal-task estimates with 100,000 paired-start bootstrap
replicates using seed `2026081701`.

The all-iterations hypothesis earns a separately frozen three-scorer-seed D2
replication only if all five point-estimate gates pass:

1. true RDX minus shuffled RDX is strictly positive on the equal-task mean;
2. true RDX minus the forward gate is strictly positive on the equal-task
   mean;
3. true RDX minus continuous ACID is at least `-0.05` on the equal-task mean;
4. true RDX is no more than `0.05` below shuffled RDX on any task and is
   strictly above it on at least two tasks;
5. true RDX is no more than `0.15` below continuous ACID on any task.

All gates are evaluated regardless of early failure. Passing authorizes only
a new multi-seed exposed-D2 replication. Failing ends RDX verifier gating and
redirects development to the separately motivated goal-conditioned diffusion
proposal approach. Neither outcome authorizes D3 or a claim.

## Interpretation boundaries

- E6D is selected after observing E6 and is therefore exploratory.
- The existing favorable Cube result may not substitute for the three-task
  rule.
- A win over shuffled diffusion but not the deterministic forward gate does
  not establish that diffusion is needed.
- The ACID implementation remains an audited publication reconstruction, not
  unreleased official author code.
- No protected-data access, task deletion, task-specific cutoff, or secondary
  endpoint substitution is allowed.

