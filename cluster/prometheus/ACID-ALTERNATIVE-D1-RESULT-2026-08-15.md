# ACID-alternative v1: D1 development result

Date: 2026-08-15  
Status: complete D1 evidence package; all predeclared analyses finished  
Scope: frozen Le-WM planners on PushT, Reacher, and OGBench single-cube

## 1. Verdict

The current diffusion transition verifier is **not supported as a robust
alternative to ACID**.

In the matched D1 development experiment, diffusion improved over original CEM
by only 1.39 percentage points pooled, with a two-sided 95% confidence interval
from -4.17 to +6.94 points. It was 3.24 points below ACID, and its one-sided
non-inferiority lower bound of -7.87 points crossed the frozen -5-point margin.
It was also 3.24 points below the capacity-matched deterministic forward
verifier. Only the breadth gate passed.

The mechanism diagnostics make the interpretation clearer. Diffusion error did
rank realized rollout error overall, but the true action-conditioned scorer did
not beat either its shuffled-action or action-ablated controls. It also ranked
realized error less well than the matched forward verifier. The present model
therefore appears to learn a useful generic transition or target-density signal,
not the proposed action-conditioned transition-support mechanism.

These are development results, not C1 confirmation. They reject promotion of
the current v1 method; they do not establish that every possible diffusion
verifier must fail.

The completed sensitivity grid does not reverse that decision. A lower
verifier weight (`lambda = 0.005`) is a promising hypothesis for a separately
frozen v2 study, but it is a descriptive value found inside an inspected
development grid, has no multiplicity-adjusted interval, and cannot replace
the v1 primary setting. Across each method's best pooled sensitivity point,
ACID remained highest at 86.11%, versus 85.19% for diffusion.

## 2. Matched closed-loop result

Each cell contains 72 paired trials: 24 fixed D1 starts by three paired
training/planner seeds. Rates are not pooled across tasks in the underlying
analysis; the pooled contrasts use equal task weight and resample start
identities while retaining their three seed runs.

| Task | Original CEM | ACID | Diffusion | Forward | Reachability |
|---|---:|---:|---:|---:|---:|
| PushT | 84.72% | 83.33% | **90.28%** | **90.28%** | 86.11% |
| Reacher | 79.17% | **91.67%** | 75.00% | 84.72% | 84.72% |
| Cube | 76.39% | **79.17%** | **79.17%** | **79.17%** | 75.00% |

The apparent PushT gain did not generalize to Reacher. Diffusion tied the
forward verifier on PushT and Cube, then lost to it by 9.72 points on Reacher.

| Pooled contrast | Estimate | Frozen interval | Development gate |
|---|---:|---:|---|
| Diffusion - original CEM | +1.39 pp | two-sided 95%: [-4.17, +6.94] pp | Fail: usefulness |
| Diffusion - ACID | -3.24 pp | one-sided 95% lower bound: -7.87 pp | Fail: ACID non-inferiority |
| Diffusion - forward | -3.24 pp | two-sided 95%: [-7.87, +0.93] pp | Fail: diffusion-specific benefit |

Closed-loop gate state:

- usefulness over original CEM: **fail**;
- non-inferiority to ACID: **fail**;
- superiority over the matched forward verifier: **fail**;
- breadth across tasks: **pass**;
- mechanism: **fail**, after the separate mechanism analysis below.

The most damaging task-level result is Reacher: diffusion was 16.67 points
below ACID, with a paired two-sided 95% interval from -31.94 to -2.78 points.

## 3. Native ACID reproduction gate

The reconstructed native ACID comparator passed every predeclared R0 gate on
all three tasks. This does not make it official author code; the official code
was unavailable at the implementation freeze. It does make the comparator a
transparent, equation-based reproduction that recovered the published gain
direction before the D1 comparison was interpreted.

| Task | R0 original CEM | Mean reconstructed ACID | ACID - CEM | Correct-action pairwise accuracy | Gate |
|---|---:|---:|---:|---:|---|
| PushT | 98.00% | 98.67% | +0.67 pp | 97.46% to 97.51% | Pass |
| Reacher | 80.00% | 82.00% | +2.00 pp | 73.30% to 73.32% | Pass |
| Cube | 76.00% | 80.67% | +4.67 pp | 96.83% to 96.88% | Pass |

Reacher recovered the required direction, but its gain was smaller than the
paper's reported 76% to 88% change. Results must therefore be described as a
reproduction of the direction under the thesis harness, not as exact numerical
replication of ACID.

## 4. Held-out correct-action identification

On P1 validation transitions, true diffusion strongly beat shuffled-action
diffusion on every task. However, it lost decisively to the capacity-matched
forward verifier on every task, especially Reacher.

| Task | Diffusion | Shuffled diffusion | Forward |
|---|---:|---:|---:|
| PushT | 94.08% | 49.99% | 99.70% |
| Reacher | 54.78% | 49.97% | 94.91% |
| Cube | 96.96% | 50.09% | 99.89% |

The equal-task diffusion-minus-forward estimate was -16.23 points, with a 95%
interval from -16.33 to -16.13 points. The identification claim gate failed.

This diagnostic retains the scorer-training source lineage
`3074081ea1ebadd9...`; it is not relabelled as an output of the later
evaluator-only AA-021 source repair.

## 5. Same-candidate mechanism audit

The primary metric is within-candidate-pool Spearman correlation between score
and standardized realized rollout RMSE. There are 24 fixed pools per task and
three retained scorer seeds per pool.

| Contrast/statistic | Estimate | Two-sided 95% interval | Result |
|---|---:|---:|---|
| Diffusion rank correlation with realized error | +0.1525 | [+0.0867, +0.2168] | Positive rank signal |
| True diffusion - shuffled-action diffusion | -0.0081 | [-0.0149, -0.0015] | True conditioning is worse |
| True diffusion - action-ablated diffusion | -0.0053 | [-0.0131, +0.0022] | No conditioning advantage |
| Diffusion - forward rank correlation | -0.0673 | [-0.1319, -0.0017] | Forward ranks better |

The positive-rank subgate passed, but both action-conditioning subgates failed.
The complete mechanism gate therefore failed. Reacher's diffusion rank point
estimate was only +0.0273 and its task-level interval crossed zero.

## 6. Latency on RTX 6000 Ada

All latency measurements used one Prometheus RTX 6000 Ada allocation, the
frozen population of 300, 30 CEM iterations, identical captured tensors, CUDA
events after warm-up for component timings, and separate end-to-end episode
wall-clock runs.

### Median verifier call

| Task | ACID | Diffusion | Forward | Reachability |
|---|---:|---:|---:|---:|
| PushT | 4.014 ms | 4.206 ms | 1.256 ms | 0.489 ms |
| Reacher | 4.006 ms | 4.180 ms | 1.252 ms | 0.490 ms |
| Cube | 4.028 ms | 4.183 ms | 1.256 ms | 0.495 ms |

### Median end-to-end episode

| Task | Original CEM | ACID | Diffusion | Forward | Reachability |
|---|---:|---:|---:|---:|---:|
| PushT | 6.173 s | 6.398 s | 6.432 s | 6.264 s | 6.167 s |
| Reacher | 6.152 s | 6.428 s | 6.444 s | 6.274 s | 6.218 s |
| Cube | 6.596 s | 6.865 s | 6.874 s | 6.736 s | 6.627 s |

Diffusion added approximately 4.2% to 4.7% over original-CEM episode time and
was close to ACID latency. The forward verifier was roughly 3.3 times faster
than diffusion at the verifier call while also performing better in the pooled
closed-loop and identification comparisons. No compute-saving claim is
supported for diffusion.

## 7. Exploratory forward-verifier backup analysis

Because the forward verifier was the strongest learned control in the inspected
D1 result, job 297195 applied the same paired, task-stratified bootstrap to
forward-focused contrasts. This analysis was selected after seeing D1. It is
explicitly exploratory and is not a v1 claim gate.

| Exploratory contrast | Estimate | Interval | Interpretation |
|---|---:|---:|---|
| Forward - original CEM | +4.63 pp | two-sided 95%: [-0.46, +9.26] pp | Promising, but usefulness check fails |
| Forward - ACID | 0.00 pp | two-sided 95%: [-4.17, +3.70] pp | Pooled tie |
| Forward - reachability | +2.78 pp | two-sided 95%: [-2.78, +8.33] pp | Inconclusive |

For forward versus ACID, the pooled one-sided lower bound was -3.24 points and
would pass a -5-point pooled margin. The task-level rule still failed because
Reacher's one-sided lower bound was -15.28 points, below the frozen -10-point
task margin. Forward therefore cannot yet be called a robust ACID alternative.

It remains the best backup direction: it tied ACID's equal-task point estimate,
beat original CEM on all three task point estimates, had stronger held-out and
mechanism diagnostics than diffusion, and used a roughly 3.3-times faster
verifier call. A forward-primary claim must be frozen in a separate protocol
before any C1 outcome is generated.

One caution carries directly into that protocol. In the existing candidate
audit, the seed-mean raw rank-correlation advantage of true forward over its
shuffled-action control was +0.101 on PushT and +0.065 on Cube, but -0.106 on
Reacher. These are descriptive post-D1 checks without a newly frozen
inferential gate. They show that Reacher is not merely a wide confidence
interval; it is the task on which action conditioning also behaves in the
wrong direction.

## 8. Predeclared sensitivity analysis

All 315 predeclared sensitivity evaluations completed: 105 per task, covering
the four CEM populations, the common verifier-weight grid, and the three
single-noise diffusion ablations. Every cell below contains the mean of 72
closed-loop trials (24 fixed D1 starts by three paired seeds). `Equal-task`
means the arithmetic mean of the three task rates; it is not raw episode
pooling. These are descriptive development sensitivities with no claim gate or
multiplicity-adjusted inference.

### CEM population, with `lambda = 0.07`

| Population | Scope | Original CEM | ACID | Diffusion | Forward | Reachability |
|---:|---|---:|---:|---:|---:|---:|
| 30 | PushT | 76.39% | 84.72% | 80.56% | 80.56% | 70.83% |
| 30 | Reacher | 72.22% | 84.72% | 70.83% | 68.06% | 66.67% |
| 30 | Cube | 69.44% | 68.06% | 73.61% | 72.22% | 72.22% |
| 30 | Equal-task | 72.69% | 79.17% | 75.00% | 73.61% | 69.91% |
| 50 | PushT | 76.39% | 80.56% | 84.72% | 83.33% | 80.56% |
| 50 | Reacher | 87.50% | 88.89% | 70.83% | 75.00% | 80.56% |
| 50 | Cube | 75.00% | 75.00% | 75.00% | 73.61% | 73.61% |
| 50 | Equal-task | 79.63% | 81.48% | 76.85% | 77.31% | 78.24% |
| 150 | PushT | 86.11% | 80.56% | 91.67% | 88.89% | 90.28% |
| 150 | Reacher | 83.33% | 95.83% | 80.56% | 77.78% | 80.56% |
| 150 | Cube | 73.61% | 73.61% | 79.17% | 79.17% | 70.83% |
| 150 | Equal-task | 81.02% | 83.33% | 83.80% | 81.94% | 80.56% |
| 300 | PushT | 83.33% | 83.33% | 90.28% | 90.28% | 86.11% |
| 300 | Reacher | 79.17% | 91.67% | 75.00% | 84.72% | 84.72% |
| 300 | Cube | 76.39% | 79.17% | 79.17% | 79.17% | 75.00% |
| 300 | Equal-task | 79.63% | 84.72% | 81.48% | 84.72% | 81.94% |

Population 150 gave diffusion its best population-sweep mean, 83.80%, only
0.46 points above ACID. That pooled reversal was not robust: on Reacher,
diffusion was 15.28 points below ACID. The population sweep therefore does not
repair the cross-task failure and does not show a monotonic compute/accuracy
advantage.

### Full-population verifier weight

Original CEM has no verifier weight and was not redundantly rerun in this grid.

| Lambda | Scope | ACID | Diffusion | Forward | Reachability |
|---:|---|---:|---:|---:|---:|
| 0.005 | PushT | 87.50% | 90.28% | 86.11% | 84.72% |
| 0.005 | Reacher | 84.72% | 88.89% | 88.89% | 88.89% |
| 0.005 | Cube | 73.61% | 76.39% | 77.78% | 75.00% |
| 0.005 | Equal-task | 81.94% | 85.19% | 84.26% | 82.87% |
| 0.04 | PushT | 87.50% | 90.28% | 87.50% | 90.28% |
| 0.04 | Reacher | 90.28% | 83.33% | 79.17% | 88.89% |
| 0.04 | Cube | 79.17% | 81.94% | 79.17% | 73.61% |
| 0.04 | Equal-task | 85.65% | 85.19% | 81.94% | 84.26% |
| 0.07 | PushT | 83.33% | 90.28% | 90.28% | 86.11% |
| 0.07 | Reacher | 91.67% | 75.00% | 84.72% | 84.72% |
| 0.07 | Cube | 79.17% | 79.17% | 79.17% | 75.00% |
| 0.07 | Equal-task | 84.72% | 81.48% | 84.72% | 81.94% |
| 0.10 | PushT | 81.94% | 87.50% | 87.50% | 88.89% |
| 0.10 | Reacher | 95.83% | 80.56% | 86.11% | 81.94% |
| 0.10 | Cube | 80.56% | 80.56% | 80.56% | 76.39% |
| 0.10 | Equal-task | 86.11% | 82.87% | 84.72% | 82.41% |

At `lambda = 0.005`, diffusion reached 85.19% equal-task success and had a
higher point estimate than ACID on each task. It exceeded forward on PushT,
tied it on Reacher, and trailed it by 1.39 points on Cube. This is the strongest
v2 lead in the sweep, not a rescued v1 result: the grid is development-only,
no interval or multiple-comparison correction supports selection, the frozen
primary value remains `0.07`, and the action-conditioning mechanism still
failed. The best pooled ACID point in the same grid was higher, 86.11% at
`lambda = 0.10`.

### Single-noise diffusion ablation at population 300 and `lambda = 0.07`

| Inference noise | PushT | Reacher | Cube | Equal-task |
|---:|---:|---:|---:|---:|
| 0.10 | 93.06% | 72.22% | 80.56% | 81.94% |
| 0.25 | 90.28% | 83.33% | 77.78% | 83.80% |
| 0.50 | 86.11% | 77.78% | 77.78% | 80.56% |
| Multi-noise primary | 90.28% | 75.00% | 79.17% | 81.48% |

The single `sigma = 0.25` ablation improved the diffusion pooled point by 2.31
points relative to the multi-noise primary scorer, but remained 0.93 points
below primary ACID and retained material task variation. It is another v2
hypothesis, not evidence that the frozen multi-noise method is an ACID
alternative.

## 9. What can honestly be claimed

Supported:

- a matched comparison of original CEM, reconstructed native ACID, learned
  reachability, a conditional diffusion transition verifier, and a
  capacity-matched deterministic forward verifier on the three released Le-WM
  tasks;
- the frozen diffusion verifier produced a useful error-ranking signal, but it
  did not show the proposed action-conditioning mechanism;
- the cheaper deterministic forward verifier was the stronger learned control
  in the frozen primary, identification, and mechanism comparisons;
- the frozen primary effect was task-dependent: promising on PushT, neutral on
  Cube, and poor on Reacher.

Not supported:

- that diffusion is a robust alternative to ACID;
- that diffusion repairs original CEM planning across the suite;
- that the benefit is specifically caused by diffusion rather than by adding a
  learned verifier;
- that the result generalizes beyond Le-WM or to PLDM;
- an exact reproduction of ACID's published numbers or use of official ACID
  code.

## 10. Publication and next-study decision

This v1 result is not publishable as the intended positive
"diffusion replaces ACID" paper. It can still be scientifically useful as a
careful negative and diagnostic study: a seemingly strong diffusion score on
PushT and held-out data failed to generalize, failed its action-conditioning
controls, and was beaten by a simpler forward verifier.

A defensible full paper would need one of three explicitly separate paths:

1. **Negative-study path:** reconcile the scorer-training/evaluator source
   lineages without changing the frozen method, run the untouched C1 protocol,
   and publish the confirmatory null/failure analysis if it persists.
2. **Forward-verifier pivot:** freeze a new primary forward-versus-ACID and
   forward-versus-CEM protocol, retain the unchanged forward arm, and use an
   untouched confirmation set. The existing C1 starts can remain eligible only
   if their outcomes stay unseen and the source-lineage authorization is
   reconciled before execution.
3. **Diffusion redesign:** close v1, formulate an exploratory v2 around the
   failed action-conditioning mechanism, use fresh development data for model
   selection, and preregister the chosen redesign before testing it once on an
   untouched confirmation set.

The current D1 results have been inspected. They cannot be used to tune v1 and
then presented on its frozen C1 set as if the redesign had been prespecified.
C1 remains locked and no C1 or I1 outcome has been generated.

## 11. Reproducibility anchors

- frozen scorer-training core manifest:
  `3074081ea1ebadd9ef08fef68ce1d81e6b7db656d873ef9d8470690b6fd0c1fc`;
- scorer-training orchestration manifest:
  `b96b968214392e30e188728372a64375c4fd2707afc5e0eec66b6af1e59387b2`;
- repaired closed-loop evaluator core manifest:
  `52acea39e4a1f6dadfa5d5be4ec6206a9aefb46159e5def7355a8575f0062f1d`;
- primary diagnostics manifest:
  `53065f818adf09b30469306e64d5bf76388481f4595896ef4be1e1855d69b278`;
- AA-024 diagnostics manifest:
  `2a55d07d912bf1b6c39f36219c603e3b45c38c3a0a4ccdb475c5bc0d93971614`;
- effective global jobs: closed loop 297129, validation 297125, mechanism
  297165, and sensitivity 297131;
- sensitivity summary SHA-256:
  `9af2d7dba0be0f5d7e342313a628d3044e958854098029ef4df2b76f5fc49f33`;
- explicitly post-D1 exploratory forward analysis: job 297195, script SHA-256
  `01ab429822e50684d2b51722fe3a5fa366a1f3996517813f021768377da83f26`;
- primary source files and every repair are described in
  `ACID-ALTERNATIVE-V1-PROTOCOL-2026-08-12.md` and
  `ACID-ALTERNATIVE-V1-AMENDMENTS-2026-08-13.md`.

The accompanying final provenance ledger validates the immutable source
manifests, effective Slurm accounting records, job-local checksums, and all 315
sensitivity summaries. Job-local result directories are unique and no
scientific result has been overwritten.
