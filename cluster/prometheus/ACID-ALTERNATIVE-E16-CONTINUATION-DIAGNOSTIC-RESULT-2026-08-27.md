# E16 exact-bank continuation diagnostic and adapter-stop result

Date analyzed: 27 August 2026  
Evidence role: outcome-informed P1 development diagnostic only  
Claim status: no closed-loop efficacy claim

## Frozen decision

E16 Stage A completed with exact replay of the immutable E15 seed-7201 VAD
banks. It found substantial candidate-ranking headroom for a continuation
mechanism on both PushT and Cube. The preregistered latent-to-state interface
gate nevertheless failed on Cube. Therefore E16 Stages B and C were not run,
the failed gate was not tuned or rescued, and no SAGE or closed-loop
continuation comparison was produced under E16.

The diagnostic supports one narrower follow-up: a separately named and newly
frozen preflight for an action-conditioned transition-state adapter. It does
not authorize full-horizon trajectory diffusion, a latent-subgoal method, or
consumption of protected evidence.

## Integrity and information barrier

- Frozen protocol SHA-256:
  `c308ca8117c6b0ac82c1df898e1f8e5e5f35f6af52685d27bc237a1b208df332`.
- Immutable diagnostic source-manifest SHA-256:
  `3669dc328568ec483a67149712bd2a7c118005a2f6251a74e0fe5af01f424f01`.
- Exact-bank Slurm array 299313 (with its second array cell assigned job ID
  299316) completed successfully; dependent analyzer 299314 completed
  successfully.
- Both 90,000-row task banks passed their own `sha256.txt`; the aggregate
  `STAGE-A-AUDIT.json` and `task-first.tsv` passed their checksum file.
- The replay matched E15's selected far-goal and selected true-local costs with
  maximum absolute error exactly `0.0` on both tasks, below the frozen `2e-5`
  tolerance.
- The analyzer recorded 92 task-first rows: 45 `(delta,tau)` cells plus one
  task aggregate for each task. An independent HDF5 reaggregation reproduced
  the frozen task aggregates exactly.
- No P2 outcome, D3 metric, D4 metric, D5 artifact, P3, P4, C1, or I1 evidence
  was read.

## Stage A: what the exact banks showed

The primary table below is the frozen all-cell task aggregate. `Rank` is the
one-indexed far-goal rank of the candidate that was actually best for the
recorded next local latent. `Top-k recall` is the probability that this exact
local oracle survived inside the first k candidates under far-goal ranking.
`Top-k regret` is the remaining local-cost gap after an oracle reranks only
those k candidates.

| Task | Pearson / Spearman | Local-oracle far rank, median (mean; q90) | Top-30 recall / regret | Top-100 recall / regret | Greedy local cost | Top-30 local cost | Top-100 local cost | 300-way oracle cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| PushT | 0.153 / 0.148 | 103 (128.2; 293) | 33.66% / 6.51 | 49.64% / 3.21 | 31.33 | 14.12 | 10.81 | 7.61 |
| Cube | 0.367 / 0.341 | 74 (109.8; 279) | 37.29% / 16.95 | 55.78% / 8.80 | 64.18 | 33.28 | 25.13 | 16.33 |

These aggregates include the three trivial `delta=tau` cells. The frozen
task-first file makes that composition visible. A descriptive reaggregation
of only genuine far-goal rows (`delta>tau`, 84,000 queries per task) gives the
more relevant picture:

| Task | Pearson / Spearman | Local-oracle far rank, median (mean; q90) | Top-30 recall / regret | Top-100 recall / regret | Greedy local cost | Top-30 local cost | Top-100 local cost | 300-way oracle cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| PushT | 0.092 / 0.087 | 122 (137.3; 294) | 28.92% / 6.98 | 46.05% / 3.44 | 32.99 | 14.55 | 11.01 | 7.57 |
| Cube | 0.321 / 0.294 | 88 (117.5; 281) | 32.81% / 18.16 | 52.62% / 9.43 | 68.06 | 34.94 | 26.22 | 16.78 |

At the most relevant registered long offsets (`delta>=75, tau=15`), PushT's
far/local correlation was effectively zero (Pearson -0.014, Spearman 0.001)
and Cube's remained weak (0.220 / 0.196). Yet an oracle restricted to the
far-ranked top 30 reduced mean local cost from 21.66 to 9.54 on PushT and from
64.89 to 34.44 on Cube. The diagnostic conclusion is therefore specific:
the candidate banks contain substantially better immediate branches than the
greedy far endpoint chooses, so a principled second-stage reranker has room to
help. This is oracle headroom, not evidence that the proposed continuation
model will realize it.

## Fixed guidance mixture

The frozen diagnostic also replaced half of each 300-candidate bank with
same-noise, zero-guidance samples. It was not a sweep and does not define a new
arm.

| Task | Standard selected local cost | 150 standard + 150 zero-guidance | Difference | Standard action-oracle MSE | Mixed action-oracle MSE |
|---|---:|---:|---:|---:|---:|
| PushT | 31.33 | 39.79 | +8.46 (worse) | 0.00522 | 0.00486 |
| Cube | 64.18 | 71.83 | +7.65 (worse) | 0.02504 | 0.02306 |

The mixture marginally improved best-in-bank demonstrated-action coverage but
made the far-goal-selected candidate less locally plausible on both tasks.
Zero guidance is therefore not a selector repair and was not promoted.

## Frozen adapter gate

The E16 adapter attempted to decode standardized low-dimensional state from a
single standardized Le-WM CLS latent. It was trained on unique role-0 sources;
role-1 payload was opened only after the final EMA checkpoint existed.

| Task | Validation rows | Standardized RMSE | Maximum coordinate RMSE | Median coordinate R-squared | Frozen gate |
|---|---:|---:|---:|---:|---|
| PushT | 70,644 | 0.2736 | 0.5134 | 0.9964 | Pass |
| Cube | 74,380 | 0.8051 | 1.6975 | 0.4011 | **Fail** |

The gate required RMSE at most 0.50, maximum coordinate RMSE at most 0.85,
and median coordinate R-squared at least 0.50 on each task. Cube failed all
three. This is an interface failure, not evidence that the frozen VAD bank
lacks useful actions. It shows that Cube's CLS latent alone does not expose
enough information for this fixed decoder to reconstruct all 28 state
coordinates reliably.

## Scientific interpretation

E16 resolves the immediate diagnostic question but not the planning question:

1. E15's greedy far endpoint is a poor proxy for immediate branch quality,
   especially on PushT and at long offsets.
2. Useful branches often survive in a modest far-ranked shortlist, so a
   continuation reranker is not trying to create quality from an empty bank.
3. A same-noise zero-guidance mixture does not repair the selection problem.
4. The preregistered latent-only state interface is inadequate for Cube, so
   running E16's continuation planner would violate its protocol.

The authorized next preflight must predict the next standardized state from
the current state, current latent, the first bounded action chunk, and Le-WM's
terminal latent. Its architecture, gates, seed, and data firewall must be
frozen before role-1 validation output is read. Even a pass would authorize
only a separately frozen conservative two-stage planner study. Full-horizon
trajectory diffusion remains explicitly outside scope.

