# E11 pure velocity-diffusion untouched-D3 result

Date completed: 2026-08-18  
Evaluation array: `297835` (`576/576` completed, all exit `0:0`)  
Analysis job: `297836` (completed `0:0` in `00:00:28`)  
Frozen decision: `suite_conditional_superiority_to_reconstructed_acid`  
Protocol claim flag: `true`  
Official-ACID claim flag: `false`

## Frozen verdict

E11 passed both the preregistered diffusion-specific mechanism gate and the
hierarchical superiority gate. The allowed conclusion is:

> On the tested three-task Le-WM suite and fixed three-seed set, the pure
> goal-conditioned velocity-diffusion selector was superior to our
> published-equation ACID reconstruction. It achieved 93.39% equal-task
> success versus 83.31% for the reconstruction, a paired difference of
> +10.08 percentage points (95% start-cluster interval +8.31 to +11.89),
> while using one thirtieth as many candidate evaluations per planning
> decision.

This must not be shortened to “diffusion is superior to ACID.” The ACID arm is
a transparent reconstruction because official code was unavailable, the
result is conditional on three Le-WM tasks and three fixed model/planner-seed
blocks, and E11 does not test a population of training seeds or unseen task
families.

## Provenance and integrity

- Immutable snapshot:
  `/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e11-1c52b60488373719`
- Source-manifest SHA-256:
  `1c52b60488373719017138bc33cef78fbc23551fe8efcb3637113a1d0b93c07e`
- Protocol SHA-256:
  `9b4bde9e2f69a7b92abaaf33f9db3016b8f61e82bedbe662a71a054cf3832ce0`
- Aggregate `summary.json` SHA-256:
  `2dbce8498e541e4e4045b28837bdaad454ef080ed5e94d9bdba4e98898781c15`
- Paired-outcomes SHA-256:
  `de5d3e520ef908b399c140655938874388e52e1f2f37fecf132115a305658431`
- All 576 evaluation shards completed successfully; the locked analysis ran
  only through the full-array `afterok` dependency.
- The analyzer verified every shard checksum, the exact 576-cell design,
  frozen scorer/proposal/checkpoint identities, identical starts across arms,
  400 distinct D3 episodes per task, exact manifest selection, matched
  velocity-noise streams, and the expected RTX 6000 Ada host.
- The PushT, Reacher, and Cube D3 manifest hashes exactly matched the launch
  record. Their selected intersections with R0, D1, and D2 were zero.
- C1 and I1 were not read. No partial D3 outcome was opened before aggregation.
- All proposal and structural integrity gates passed. The treatment proposals
  were finite, retained positive diversity, and had a maximum observed
  boundary fraction of 11.85%, below the frozen 25% threshold.
- The aggregate bundle was copied locally and all four recorded content hashes
  passed. The 75-byte analysis stderr contains only an Apptainer bind-mount
  informational message.

An independent read-only calculation from `paired-outcomes.tsv` verified 3,600
unique `(task, eval_index, seed)` rows, 400 unique starts per task, all success
counts, all four primary point contrasts, and all exact sign-test counts. A
separate 100,000-repetition task-stratified bootstrap with seed `2026081812`
gave intervals differing from the frozen intervals by at most 0.03 percentage
points at an endpoint.

## Equal-task success

The design is balanced, so each rate below is based on 1,200 outcomes per task
and 3,600 outcomes across the fixed three-seed set. Those repeated-seed
outcomes are paired measurements, not 3,600 independent trials.

| Arm | PushT | Reacher | Cube | Equal-task |
|---|---:|---:|---:|---:|
| Released CEM (`b0`) | 88.83% | 81.92% | 67.83% | 79.53% |
| ACID reconstruction | 88.92% | **85.17%** | 75.83% | 83.31% |
| Reachability (M3) | 88.42% | 80.17% | 68.50% | 79.03% |
| Forward verifier | 88.92% | 82.50% | 71.42% | 80.94% |
| Gaussian selector | 91.33% | 80.67% | 99.92% | 90.64% |
| Shuffled-goal velocity | 80.67% | 73.58% | 83.75% | 79.33% |
| Unconditional velocity | 85.50% | 77.17% | 92.50% | 85.06% |
| **True goal-conditioned velocity** | **95.50%** | 84.67% | **100.00%** | **93.39%** |

The treatment recorded 3,362 successes across 3,600 fixed-seed evaluations,
versus 2,999 for reconstructed ACID and 3,263 for the Gaussian selector.

## Diffusion-specific mechanism gate

All three preregistered control contrasts were positive, their one-sided 95%
lower bounds were above zero, and the treatment exceeded both Gaussian and
shuffled controls on all three task point estimates.

| True velocity minus control | Difference | 95% two-sided interval | One-sided 95% lower | Exact one-sided sign p |
|---|---:|---:|---:|---:|
| Gaussian selector | **+2.75 pp** | [+1.64, +3.89] | +1.81 | `1.16e-6` |
| Shuffled-goal velocity | **+14.06 pp** | [+12.25, +15.89] | +12.53 | `7.01e-44` |
| Unconditional velocity | **+8.33 pp** | [+6.75, +9.94] | +7.00 | `6.89e-21` |

The per-task true-minus-Gaussian differences were +4.17 points on PushT,
+4.00 on Reacher, and only +0.08 on Cube. Cube was saturated: true velocity
was 1,200/1,200 and Gaussian was 1,199/1,200. Therefore the suite-wide
diffusion-over-Gaussian evidence comes materially from PushT and Reacher, not
from a meaningful Cube separation.

The shuffled and unconditional controls rule out explanations based only on
network capacity, unconditional sampling, or an arbitrary goal label. The
Gaussian contrast is the narrowest evidence that the diffusion proposal
treatment adds value beyond a capacity- and budget-matched learned proposal.

## Hierarchical comparison with reconstructed ACID

The primary treatment-minus-ACID contrast was **+10.08 percentage points**.
Its frozen 95% start-cluster interval was **[+8.31, +11.89]**, its one-sided
95% lower bound was **+8.61**, and its exact paired one-sided sign-test p-value
was `9.10e-15`.

Per-task differences were:

- PushT: **+6.58 points**;
- Reacher: **-0.50 points**; and
- Cube: **+24.17 points**.

Thus the treatment won two of three tasks and the only loss was within the
frozen five-point harm guard. The superiority gate passed exactly as written.
The result is nevertheless heterogeneous: the large Cube advantage contributes
substantially to the equal-task effect, and the treatment did not beat ACID on
Reacher.

The descriptive secondary differences were +13.86 points versus released CEM,
+14.36 versus reachability, and +12.44 versus the forward verifier. Their
two-sided 95% intervals were respectively [+12.03, +15.72], [+12.56, +16.19],
and [+10.67, +14.28]; all Holm-adjusted sign-test p-values were below `1e-27`.

## Stability across the fixed seed blocks

| Model seed | True velocity | ACID reconstruction | Gaussian selector | True − ACID | True − Gaussian |
|---:|---:|---:|---:|---:|---:|
| 6101 | 93.92% | 83.83% | 90.58% | +10.08 pp | +3.33 pp |
| 6102 | 93.00% | 83.25% | 90.67% | +9.75 pp | +2.33 pp |
| 6103 | 93.25% | 82.83% | 90.67% | +10.42 pp | +2.58 pp |

The sign and magnitude were stable across all three fixed blocks. This is not
a population-of-seeds claim; the primary interval conditions on these blocks.

## Inference-time compute

The selector evaluated 300 candidates once per planning decision. ACID
evaluated 300 candidates for each of 30 CEM iterations: 9,000 candidates per
decision. Across E11 this was 2.16 million versus 64.8 million candidate
evaluations and 7,200 versus 216,000 Le-WM cost calls.

| Task | Summed ACID elapsed | Summed true-velocity elapsed | Observed speedup | Median seconds saved per paired 50-episode block |
|---|---:|---:|---:|---:|
| PushT | 8,969.6 s | 646.2 s | 13.88× | 349.7 s |
| Reacher | 9,134.2 s | 750.0 s | 12.18× | 352.3 s |
| Cube | 9,586.4 s | 1,069.9 s | 8.96× | 358.1 s |

Total measured closed-loop elapsed time was 27,690 seconds for ACID and 2,466
seconds for the treatment, an 11.23× ratio. The treatment was faster on every
task. These are inference/evaluation measurements on matched hardware and do
not include the proposal model's up-front training cost.

The aggregate's `compute_efficient_alternative` flag is false only because the
protocol evaluates that fallback branch when strict superiority fails. The
superiority branch passed; the one-thirtieth compute ratio and every-task
timing criteria also passed.

## Honest scientific interpretation

This is a strong positive confirmatory result, but two mechanisms must not be
conflated:

1. A learned one-shot proposal distribution provides most of the advantage
   over iterative reconstructed ACID. The Gaussian selector already achieved
   90.64%, 7.33 points above ACID's 83.31%.
2. Goal-conditioned velocity diffusion adds a smaller but preregistered and
   statistically clean 2.75-point improvement over that matched Gaussian
   selector. Its much larger shuffled and unconditional contrasts show that
   learned goal conditioning is essential.

Therefore E11 supports the claim that goal-conditioned velocity-diffusion
proposals are a superior, far cheaper planning alternative to this ACID
reconstruction on the tested Le-WM suite. It does not support attributing the
entire ten-point ACID gap specifically to diffusion, claiming universal
superiority, or claiming equivalence to an official ACID implementation.

E11 also tests a pure diffusion **action-proposal generator**, not the earlier
auxiliary diffusion-loss plausibility scorer. The paper and thesis must present
that architectural pivot explicitly rather than implying that the original
post-hoc scoring idea produced this result.

## Publication implications and next steps

The result is substantial enough to anchor a thesis and a paper submission:
it is untouched-data confirmation, paired, multi-seed, mechanism-controlled,
computationally measured, and positive under a frozen gate. Publication
strength now depends more on transparent positioning and external validation
than on searching for a larger in-suite effect.

Next steps should not tune or rerun E11 D3:

1. preserve the remote and local bundles and generate the main paper tables
   directly from the hashed aggregate;
2. perform a line-by-line independent implementation audit of the ACID
   reconstruction and document every deviation forced by unavailable code;
3. report proposal-training cost separately from inference cost;
4. freeze a separate cross-backbone or external-task protocol, such as PLDM,
   if time permits; and
5. run an official matched ACID comparison if its authors release code.

No later extension may be described as rescuing or modifying E11. This result
stands as the frozen three-task Le-WM confirmation.
