# ACID-alternative E3: exploratory D2 closed-loop result

Date: 2026-08-16  
Closed-loop array: `297572`  
Analysis job: `297573`  
Protocol role: post-v3 exploratory D2 development  
Frozen decision: **`stop_diffusion_development_and_pivot`**

## Bottom line

The frozen diffusion action-evidence planner did **not** earn promotion to a
new confirmation study and did **not** establish itself as an alternative to
ACID.

Only two of the five frozen E3 promotion gates passed. AE, the true-action
conditional-versus-unconditional diffusion score, was non-inferior to the
capacity-matched deterministic forward verifier and had a mildly favorable
task pattern relative to original CEM. However, AE failed non-inferiority to
the published-equation ACID reconstruction, did not significantly beat
original CEM, and did not beat its shuffled-action diffusion control.

The equal-task success estimates were `0.84889` for ACID, `0.80889` for the
deterministic forward verifier, `0.80667` for RDX, `0.80667` for shuffled AE,
`0.79778` for true AE, and `0.78667` for original CEM. AE was `5.11`
percentage points below ACID and `0.89` points below its shuffled control.
Its `1.11`-point advantage over original CEM was too uncertain to pass the
two-sided superiority gate.

This result does not show that diffusion can never help planning. It shows
that this frozen residual-diffusion model, endpoint, weight, and Le-WM/CEM
integration did not provide robust action-specific closed-loop benefit on the
three-task matched suite. Under the protocol's irreversible rule, further
Le-WM diffusion redesign stops and the thesis pivots to a controlled
comparative/negative result.

## What was tested

The study independently optimized six planners on the same frozen D2 starts:

1. `b0`: original CEM using goal cost alone;
2. `acid`: the audited published-equation ACID reconstruction;
3. `forward`: a capacity-matched deterministic forward verifier;
4. `rdx`: conditional residual-diffusion error;
5. `ae`: true-action conditional-versus-unconditional diffusion evidence;
6. `ae_shuffled`: the matched shuffled-action AE null control.

PushT, Reacher, and Cube each used 50 identical starts. Scorer seeds
`6101/6102/6103` were paired with planner seeds `8301/8302/8303`. Every arm
used the same released Le-WM checkpoint, dataset, start/goal pair, CEM budget,
and environment implementation within a task. This produced 54 complete runs
and **2,700 closed-loop episodes**.

The planner configuration remained population 300, 30 CEM iterations, 30
elites, five latent transitions, five primitive actions per transition, goal
offset 25, and evaluation budget 50. Diffusion used sigmas
`{0.25, 1.0, 4.0}`, eight fixed draws per sigma, and `lambda = 0.005`; ACID
used its audited one-step noise construction and `lambda = 0.07`.

E3 was deliberately separate from the failed v3 Stage-B authorization. It
used already inspected D2 development starts, so it is neither fresh
confirmation nor v3 Stage B. C1 and I1 remained sealed.

## Frozen gate results

| Gate | Frozen requirement | Observed result | Decision |
|---|---|---:|---|
| 1 | AE minus ACID: equal-task one-sided lower bound above `-0.05`, and every task above `-0.10` | Equal-task `-0.05111`, lower `-0.08000`; Reacher lower `-0.16667`, Cube lower `-0.10667` | **Fail** |
| 2 | AE minus B0: equal-task two-sided lower bound above 0 | `+0.01111`, lower `-0.02222` | **Fail** |
| 3 | AE minus shuffled AE: equal-task two-sided lower bound above 0 | `-0.00889`, lower `-0.03778` | **Fail** |
| 4 | AE no more than 0.10 below B0 in any task and higher in at least two tasks | PushT `+0.00667`, Reacher `-0.04000`, Cube `+0.06667` | Pass |
| 5 | AE minus forward: equal-task one-sided lower bound above `-0.05` | `-0.01111`, lower `-0.03778` | Pass |

All gates were evaluated even after the first failure. The aggregate value is
`all_e3_promotion_gates_pass = false`, the decision is
`stop_diffusion_development_and_pivot`, and the separate claim decision is
`no_publication_claim_from_exploratory_e3`.

Gate 1 did not fail by a rounding technicality. AE's equal-task point estimate
was already slightly beyond the `-0.05` non-inferiority margin, its two-sided
95% interval versus ACID was entirely negative (`[-0.08444, -0.01778]`), and
the exact paired start-cluster sensitivity test favored ACID (`31` negative,
`14` positive, `105` ties; two-sided `p = 0.01609`).

Gate 3 is the most important mechanism failure. True-action AE did not improve
over the otherwise matched shuffled-action AE network. The equal-task
two-sided interval was `[-0.03778, +0.02000]`, and the exact sensitivity test
was also null (`22` negative, `16` positive, `112` ties;
`p = 0.41769`). Consequently, the closed-loop result cannot attribute any
planner benefit to correct action conditioning.

## Success by method and task

The table reports means over three paired scorer/planner seeds. The final
column gives the task-stratified equal-task estimate and two-sided 95%
start-cluster bootstrap interval.

| Method | PushT | Reacher | Cube | Equal-task success (95% interval) |
|---|---:|---:|---:|---:|
| Original CEM (`B0`) | `0.87333` | `0.80667` | `0.68000` | `0.78667 [0.73111, 0.84000]` |
| ACID reconstruction | `0.87333` | `0.86667` | `0.80667` | `0.84889 [0.79778, 0.89778]` |
| Deterministic forward | `0.86667` | `0.80000` | `0.76000` | `0.80889 [0.75778, 0.85778]` |
| RDX | `0.87333` | `0.81333` | `0.73333` | `0.80667 [0.75556, 0.85556]` |
| AE, true actions | `0.88000` | `0.76667` | `0.74667` | `0.79778 [0.74667, 0.84667]` |
| AE, shuffled actions | `0.88667` | `0.82667` | `0.70667` | `0.80667 [0.75778, 0.85333]` |

### Task-level interpretation

- **PushT was near ceiling.** Every arm lay between `0.86667` and `0.88667`.
  AE was only `0.00667` above B0 and `0.00667` above ACID, while shuffled AE
  was slightly higher still. PushT did not distinguish the mechanisms.
- **Reacher exposed AE's main failure.** AE scored `0.76667`, versus `0.86667`
  for ACID, `0.80667` for B0, and `0.82667` for shuffled AE. Its deficit was
  present across the three seed-level rates rather than being caused by one
  isolated failed run.
- **Cube showed a real but insufficient local benefit.** AE improved on B0 by
  `0.06667`, with a task-level two-sided 95% lower bound of `+0.02000`, and
  true AE exceeded shuffled AE by `0.04000`. Nevertheless, ACID reached
  `0.80667`, exceeding AE by `0.06000`; deterministic forward also reached
  `0.76000`.

The geometry-dependent Cube benefit is worth reporting as a diagnostic
observation, but selecting Cube and discarding Reacher after seeing these
results would violate the frozen three-task decision.

## Important secondary contrasts

| Contrast | Equal-task estimate | Two-sided 95% interval |
|---|---:|---:|
| AE minus ACID | `-0.05111` | `[-0.08444, -0.01778]` |
| AE minus B0 | `+0.01111` | `[-0.02222, +0.04667]` |
| AE minus shuffled AE | `-0.00889` | `[-0.03778, +0.02000]` |
| AE minus deterministic forward | `-0.01111` | `[-0.04222, +0.01778]` |
| RDX minus ACID | `-0.04222` | `[-0.07556, -0.00889]` |
| RDX minus B0 | `+0.02000` | `[-0.01111, +0.05333]` |

RDX's result is scientifically useful when read beside v3 Stage A. In the
same-candidate audit, RDX ranked realized candidate failures much better than
the ACID reconstruction. In independently optimized closed-loop CEM, however,
ACID exceeded RDX by `4.22` points with an interval entirely below zero for
RDX minus ACID. Candidate-level discrimination therefore did not guarantee a
planner-compatible score. Calibration, scale, and how a score reshapes CEM's
successive proposal distributions mattered more than the captured-pool rank
statistic alone.

The same disconnect applies to AE. Stage A showed action-specific candidate
signal, but the closed-loop true-versus-shuffled control did not show a
corresponding planning advantage. This is the strongest honest negative
finding of the study.

## Compute and runtime

All 54 runs used an NVIDIA RTX 6000 Ada Generation GPU and completed without
failure. Every run made 3,000 recorded CEM cost calls. The following times are
the evaluator's measured closed-loop time, excluding scheduler/container
startup overhead.

| Arm | Mean seconds per 50-episode run | Range (seconds) | Maximum PyTorch peak allocated VRAM |
|---|---:|---:|---:|
| B0 | `369.60` | `348.48–381.79` | `496,035,840` bytes |
| ACID | `387.05` | `368.37–407.10` | `503,354,880` bytes |
| Deterministic forward | `373.55` | `350.98–390.71` | `504,089,600` bytes |
| RDX | `562.33` | `538.03–592.45` | `504,257,536` bytes |
| AE | `560.54` | `535.43–592.71` | `504,257,536` bytes |
| Shuffled AE | `560.03` | `538.07–589.11` | `504,257,536` bytes |

AE took about `1.45x` ACID's end-to-end evaluator time and `1.50x` the
deterministic forward verifier's time. This relative difference is much
smaller than the isolated scorer-timing ratio from Stage A because Le-WM
rollout and environment evaluation are shared costs. The 54 evaluator
summaries totalled `7.03` measured GPU-hours; Slurm wall times, including
startup overhead, totalled `9.39` GPU-hours. The maximum reported PyTorch peak
allocation was about `0.47 GiB`; this is framework-allocated tensor memory,
not whole-device occupancy.

## Integrity and independent reproduction

The first authorization job, `297568`, failed after three seconds because a
bytecode-compilation check attempted to create `__pycache__` inside the
correctly read-only source snapshot. Dependent jobs `297569` and `297570`
never ran and were cancelled. No model, planner, environment, or outcome had
been executed or inspected.

Amendment 1 replaced only the bytecode-writing check with in-memory Python
source compilation. The estimand, six arms, tasks, starts, seeds, weights,
checkpoints, CEM budgets, endpoints, and gates were unchanged. Corrected
authorization job `297571` passed, followed by array `297572` and analysis
job `297573`.

The final audit established:

- 54 of 54 array elements were `COMPLETED` with exit code `0:0`;
- analysis job `297573` was `COMPLETED` with exit code `0:0`;
- 54 `summary.json` files and 54 per-run `sha256.txt` files existed and all
  listed hashes verified;
- all 2,700 episode rows formed the exact paired task/arm/seed grid;
- a separate local implementation recomputed every bootstrap interval, exact
  sign test, gate, and decision directly from the episode TSVs;
- the maximum numeric difference between independent and official analysis
  was exactly `0.0`;
- `v3_stage_b_authorized`, `confirmation_claim_allowed`, and
  `alternative_to_acid_claim_allowed` remained false;
- `protected_c1_i1_read` remained false.

## Artifact identity

- E3 protocol SHA-256:
  `c48eaf320c9b378af5e5d265397af8efd3485c45a288481d25f5161238af1fb0`
- E3 immutable source-manifest SHA-256:
  `323318f12407690c4ebff4a738cd3676c1321c29748da3fc8cb24aa0de6d63c5`
- Exploratory authorization SHA-256:
  `88b6901f2ad4d4eed8ad276849b1c91343fd4d25d9dfbbe422b0d5bef5eec8a5`
- Analysis summary SHA-256:
  `2a4134b49f770cd3f339d73233183d5bd2013b562aee751abc0e8a744959fdbb`
- Analysis manifest SHA-256:
  `c1dcc7c1fbd1c365254450d7b691f4d8b07ce0bf71a51426c2d007bdd263f643`
- Runs TSV SHA-256:
  `118b5c05a0030be63cc74f080a1b7baa778fe9acc09dee22fd7025ab4711d809`
- Independent reproduction audit SHA-256:
  `f5b32f9d99ad2064a3e997bacc07f30f5109a6c0f93f3e7885a83f5130116d18`
- Local final-manifest SHA-256 (451 entries; 452 files including the manifest):
  `a63ac570644a93c32d1c8f40b89f7f2856b40fd75afd51adea4afad344887a27`

## Allowed conclusion and thesis direction

The allowed conclusion is that the frozen AE score showed a local Cube
benefit over original CEM and remained non-inferior to a deterministic forward
verifier on the equal-task aggregate, but it did not provide robust
action-specific closed-loop improvement and was inferior to the tested ACID
reconstruction across the full suite.

This E3 study cannot support a publication claim that diffusion is an
alternative to ACID. Because three frozen promotion gates failed, AE is not
advanced to a new confirmation set and is not advanced to PLDM. C1 and I1
remain sealed rather than being spent to rescue a failed development choice.

The defensible thesis pivot is a controlled empirical account of when learned
feasibility or plausibility diagnostics do and do not translate into planning
improvement. The combined evidence now supports a stronger negative lesson:
good captured-pool ranking and detectable action conditioning are not
sufficient; a useful verifier must also be calibrated for the optimizer and
must beat matched null and simpler learned controls in closed loop. That can
be a credible thesis contribution, but it is a different claim from
"diffusion is an alternative to ACID."
