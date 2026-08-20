# ACID-alternative v3: fresh-D2 Stage-A result

Date: 2026-08-16  
Analysis job: `297565`  
Endpoint-scoring array: `297564`  
Preregistered role: fresh D2 development  
Decision: **`stop_before_stage_b`**

## Bottom line

The diffusion idea produced real, repeatable signal, but this frozen study does
**not** authorize the claim that it is an alternative to ACID.

Four of the five preregistered Stage-A gates passed. The failed gate was the
RDX candidate-ranking comparison against the capacity-matched deterministic
forward verifier. RDX easily passed the corresponding comparison against the
published-equation ACID reconstruction, but its one-sided 95% lower bound
against forward was `-0.04419`, below the frozen non-inferiority margin of
`-0.03`. Under the protocol, this failure stops Stage B. No closed-loop v3-D2
arms were launched.

The fairest scientific reading is therefore:

- the residual-diffusion model learned action-specific structure across all
  three scorer seeds and all three Le-WM tasks;
- its RDX endpoint ranked physically bad candidates substantially better than
  the audited ACID reconstruction and learned reachability;
- its AE endpoint passed the same-pool candidate-selection non-inferiority gate
  against the ACID reconstruction;
- however, RDX did not establish non-inferiority to a simpler, capacity-matched
  deterministic forward verifier, and the diffusion scorer was much slower;
- consequently, these data support continued study of diffusion-derived
  diagnostics, not an alternative-to-ACID planning claim.

## What was frozen and tested

The protocol fixed two outputs of the residual-diffusion model before D2:

- **RDX**, conditional clean-residual mean-squared error, was the primary
  candidate-failure ranker;
- **AE**, the log conditional-to-unconditional error ratio, was the primary
  action-specific planning cost.

The fixed configuration used scorer seeds `6101`, `6102`, and `6103`, noise
levels `{0.25, 1.0, 4.0}`, eight deterministic draws per level, five Le-WM
transitions, and `lambda = 0.005`. The comparison used 50 fresh P3 starts in
each of PushT, Reacher, and Cube. Original CEM captured 300 candidates per
start, and every candidate was physically executed before scoring. The same
candidate pools and physical outcomes were used for every scorer.

The comparators were original CEM (`B0`), the published-equation ACID
reconstruction, a capacity-matched deterministic forward verifier, learned
reachability, shuffled-action residual controls, and legacy raw diffusion
transition verification (`DTV`, descriptive).

This is a same-candidate audit, not independently optimized closed-loop
planning. Stage B was the preregistered closed-loop test, but its launch
required all five Stage-A gates.

## Preregistered gate results

| Gate | Frozen requirement | Observed result | Decision |
|---|---|---:|---|
| 1 | RDX rank correlation positive in every task; equal-task two-sided 95% lower bound above 0 | Equal-task `0.19838`, lower `0.15356`; all task estimates positive | Pass |
| 2 | RDX minus shuffled RDX equal-task lower bound above 0 | Difference `0.03172`; two-sided lower `0.00610` | Pass |
| 3 | RDX non-inferior to forward and ACID; each one-sided 95% lower bound above `-0.03` | vs forward: `-0.02308`, lower `-0.04419`; vs ACID: `+0.13149`, lower `+0.09362` | **Fail (forward only)** |
| 4 | AE minus shuffled AE lower bound above 0 and no negative task point estimate | Equal-task `+0.14050`, two-sided lower `+0.09972`; all tasks positive | Pass |
| 5 | AE selection non-inferior to ACID: success lower above `-0.05`, RMSE upper below `+0.02` | Success difference `+0.01778`, one-sided lower `-0.02000`; RMSE difference `-0.00245`, one-sided upper `+0.01829` | Pass |

Because Gate 3 failed, the aggregate result is
`all_stage_a_gates_pass = false`, and the immutable manifest records
`stage_b_authorized = false`.

### Why Gate 3 failed

The equal-task RDX-minus-forward Spearman contrast was `-0.02308`. Its
one-sided 95% lower confidence bound was `-0.04419`; the separately reported
one-sided upper bound was `-0.00166`, and the two-sided 95% interval was
`[-0.04825, +0.00249]`. The preregistered decision used the one-sided lower
bound, which missed the `-0.03` margin by `0.01419`.

The task-level point estimates show that this was not merely an ACID issue:

| Task | RDX rank correlation | RDX minus forward |
|---|---:|---:|
| PushT | `0.22121` | `-0.04376` |
| Reacher | `0.12582` | `+0.03162` |
| Cube | `0.24810` | `-0.05709` |

Forward was stronger on PushT and Cube; RDX was stronger on Reacher. Changing
the margin, endpoint, task mix, or transformation after seeing this pattern
would violate the protocol.

## Candidate-ranking evidence

Equal-task Spearman correlations with physically realized standardized latent
rollout RMSE were:

| Ranker | Correlation | Two-sided 95% interval |
|---|---:|---:|
| Deterministic forward | `0.22146` | `[0.17549, 0.26706]` |
| RDX, true actions | `0.19838` | `[0.15356, 0.24259]` |
| Legacy DTV | `0.17521` | `[0.13262, 0.21740]` |
| RDX, shuffled actions | `0.16665` | `[0.12445, 0.20832]` |
| AE, true actions | `0.11821` | `[0.08384, 0.15291]` |
| ACID reconstruction | `0.06689` | `[0.04433, 0.09003]` |
| Learned reachability | `0.01551` | `[-0.01437, 0.04541]` |
| AE, shuffled actions | `-0.02229` | `[-0.04352, -0.00098]` |

Important paired equal-task contrasts were:

| Contrast | Estimate | Two-sided 95% interval |
|---|---:|---:|
| RDX minus ACID | `+0.13149` | `[+0.08637, +0.17633]` |
| RDX minus reachability | `+0.18287` | `[+0.12847, +0.23697]` |
| RDX minus shuffled RDX | `+0.03172` | `[+0.00610, +0.05772]` |
| RDX minus legacy DTV | `+0.02317` | `[-0.01145, +0.05769]` |
| RDX minus forward | `-0.02308` | `[-0.04825, +0.00249]` |
| AE minus shuffled AE | `+0.14050` | `[+0.09972, +0.18226]` |

The AE true-minus-shuffled point estimate was positive in every task: PushT
`+0.19964`, Reacher `+0.07355`, and Cube `+0.14830`. This is the clearest D2
evidence that the learned action conditioning mattered. RDX's pooled
true-minus-shuffled contrast also passed, but its Cube point estimate was
slightly negative (`-0.01197`), so that result is not uniform task by task.

## Same-pool candidate selection

The table below reports the equal-task result after each scorer selected from
the already captured and physically executed 300-candidate pool. Lower RMSE
and higher success are better.

| Method | Standardized RMSE | Success |
|---|---:|---:|
| Original CEM (`B0`) | `0.41043` | `0.62000` |
| ACID reconstruction | `0.41169` | `0.61333` |
| Deterministic forward | `0.41356` | `0.63778` |
| Learned reachability | `0.41425` | `0.60889` |
| Legacy DTV | `0.40542` | `0.62889` |
| AE, true actions | `0.40924` | `0.63111` |
| AE, shuffled actions | `0.41445` | `0.61778` |
| RDX, true actions | `0.42231` | `0.63111` |

AE's point estimates were slightly better than ACID's: RMSE difference
`-0.00245` and success difference `+0.01778`. These observations satisfy the
frozen same-pool Gate 5, but they are not a closed-loop comparison. Once CEM
updates are influenced by each method, candidate populations can diverge; the
blocked Stage B was designed to test that harder question.

## Training gate and seed replication

Before D2 was generated, all nine task-by-seed true models passed the P1 gate.
Pairwise action accuracy ranges were:

| Task | True-action accuracy across seeds | Shuffled-action accuracy across seeds |
|---|---:|---:|
| PushT | `0.99445` to `0.99461` | `0.50287` to `0.50959` |
| Reacher | `0.93951` to `0.94106` | `0.49967` to `0.50150` |
| Cube | `0.99913` to `0.99923` | `0.49908` to `0.50428` |

This establishes that the action-discrimination mechanism replicated across
the three training seeds. It does not by itself establish planning benefit;
the fresh-D2 gates address that distinction.

## Compute cost

All scorer timings below are CUDA-synchronized full-D2 passes on an NVIDIA RTX
6000 Ada, after one warm-up pool. They cover 15,000 candidate sequences and
exclude loading and the shared Le-WM rollout. RDX and AE are produced jointly.

| Scorer | Seconds per 15,000 sequences | Approx. ms per candidate |
|---|---:|---:|
| Learned reachability | `0.00628` | `0.00042` |
| Deterministic forward | `0.01558` | `0.00104` |
| Legacy DTV | `0.04260` | `0.00284` |
| ACID reconstruction | `0.09652` | `0.00643` |
| Residual diffusion, joint RDX + AE | `0.78885` | `0.05259` |

The joint residual-diffusion score was about `8.17x` the ACID scoring time and
`50.62x` the deterministic-forward scoring time in this implementation. It
used roughly 2.03 million parameters, versus roughly 2.01 million for the
capacity-matched forward verifier and 1.82 million for ACID. Absolute scorer
latency remained below one second for all 15,000 candidates, but relative cost
is a real disadvantage and must be reported.

## Outcome-independent repair and audit trail

The first endpoint-scoring array, job `297539`, failed on all three tasks after
22 seconds because 75,000 ACID transition tuples were sent through scaled-dot-
product attention in one CUDA launch. Dependent analysis job `297540` never
ran and was cancelled. No endpoint artifact or Stage-A statistic existed or
was inspected at that point.

Amendment 3 fixed only inference batching: it generated the identical complete
Gaussian tensor, flattened in the same order, evaluated consecutive chunks of
at most 8,192 tuples, and restored the original shape. The equations,
checkpoints, candidates, outcomes, seeds, lambdas, endpoints, bootstraps, and
gates did not change. Synthetic analysis job `297561`, amended preflight job
`297562`, and exact CUDA batching smoke job `297563` passed before rerunning
the endpoint scores as job `297564`.

All relevant production jobs then completed successfully. The Slurm queue was
empty at the final audit. C1 and I1 were not read
(`protected_c1_i1_read = false`).

## Artifact identity

- Protocol SHA-256:
  `c38e086ee09cbabaa9ab53246add92835d59f95173b5f35290f474abb94a4dfb`
- Pre-amendment upstream source manifest:
  `875a9cbc19dba78db1706169b7f2d8bc97a70913d82b55f793735dfe8c2df388`
- Amended source manifest:
  `2c8f890c31e9f5bf5e8b6769ccc424d7cd565278c422405d507d1c702d3580ea`
- Stage-A summary SHA-256:
  `0af2181b1060d761a295c885f2eae34af47a0fd94992a8f3a59cf05e57ecbe37`
- Stage-A manifest SHA-256:
  `3558b8612787035cfa92c17d8a36f46f379bb2812f67aa0a73438d8cab974053`
- Pool-level TSV SHA-256:
  `b699cb94447d7319debb3c13d636ee6b413f8410a675442e2ce430824db988a2`
- P1 gate SHA-256:
  `93d260a6368ed3c2d71d7c7377759bf43a07056b7beae8f264d1fd5bad308c1a`

The downloaded local copies of `summary.json`, `manifest.json`,
`pool-level.tsv`, `provenance.txt`, and `sha256.txt` were independently hashed;
all four hashes listed by the remote `sha256.txt` matched byte for byte.

## Allowed conclusion and next decision

This study permits a claim that a fixed residual-diffusion verifier carries
replicable action-specific and candidate-failure information on fresh starts
across PushT, Reacher, and Cube. It also permits reporting that RDX outperformed
this ACID reconstruction as a failure ranker and that AE passed a same-pool
selection non-inferiority test against it.

It does **not** permit the preregistered alternative-to-ACID claim, because
Stage A did not fully pass and closed-loop Stage B was not run. It also cannot
show that diffusion is preferable to a generic learned verifier, because the
simpler deterministic forward model was the strongest primary ranker and was
far faster.

The v3 protocol is complete at its declared stopping point. Any subsequent
redesign must be described as a new development study, must treat all existing
D1/D2 results as development evidence, and must use genuinely new data for a
future confirmatory test. The protected C1/I1 data remain available for the
eventual final design; they must not be opened merely to rescue this failed
gate.
