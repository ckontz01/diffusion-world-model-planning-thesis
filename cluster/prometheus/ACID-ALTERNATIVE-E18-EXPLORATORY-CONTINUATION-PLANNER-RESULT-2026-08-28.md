# E18 exploratory continuation-planner result

Date analyzed: 28 August 2026

Evidence role: outcome-informed P2 method development only

Claim status: positive exploratory mechanism evidence; not untouched-holdout confirmation

## Frozen decision

The exact frozen 64-by-8 VAD continuation planner passed both preregistered
development gates. Its equal-task/equal-horizon success was strictly higher
than both greedy VAD controls and both matched non-diffusion continuation
controls, and no task-average contrast crossed the allowed -5-point loss.
The final decision is therefore
`authorize_drafting_separate_frozen_confirmation_protocol`.

This decision does not repair or reinterpret E17. The Cube adapter still
failed E17's frozen worst-coordinate preflight, and E18 deliberately retained
that checkpoint unchanged. E18 used fresh P2 development starts only. It did
not create or consume D5, and no confirmation study was launched.

## Integrity and information barrier

- Frozen protocol SHA-256:
  `aff490f3f000c7d9b261632dcd3ccfc76a630b2f44e41f78832c3719607b8459`.
- Immutable source-manifest SHA-256:
  `182ed1e7d1e9994638ab1fbc773c79cac8d68858b716e67ff8969e5b2e74e29c`.
- Immutable snapshot:
  `/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e18-182ed1e7d1e99946`.
- Input audit job 299327, two-task identifier-manifest array 299328,
  240-cell evaluation array 299329, and analyzer 299330 all completed with
  exit code zero.
- The input audit verified all 18 frozen E15 proposers and both unchanged E17
  adapters, including the preserved E17 failure and `claim_allowed=false`.
- The complete barrier contained exactly 240 successful cells, 720 episodes,
  24 paired `(task, base_start)` clusters, and 2,700 planner diagnostic calls.
  All 240 cell checksum manifests passed independent verification.
- The aggregate output hashes were:
  - `E18-AUDIT.json`:
    `670e1aa3ece41a3e6282825a2aa01f93970970ca863066fe4a440b9b13cbfdf1`;
  - `TASK-FIRST.tsv`:
    `15c99fc55b962181b2dfd212e9f51d3a2b30d0ee8cabf6fa420f76fcd20d34d2`;
  - `ALL-EPISODES.tsv`:
    `f7c03f8d08e8d44c2a7529d09f479cd5a3f56a96e30cb053998ecf2c39c6cfbe`.
- A separate verifier recomputed cell identity and checksums, paired outcomes,
  all success tables, 10,000 task/base-start bootstrap resamples, timing,
  proposal validity, adapter-state diagnostics, and every frozen gate from
  the complete evaluation tree. It returned
  `independent_validation_passed`.
- No metric-bearing partial evaluation artifact was opened before all cells
  and the dependent analyzer completed. D3/D4 metric artifacts, D5, P3, P4,
  C1, and I1 were not read.

## What was evaluated

At each non-final 15-action planning stage, continuation arms sampled 64 first
chunks and eight second chunks per first chunk. The frozen E17 adapter
predicted the intermediate state after each first chunk, Le-WM evaluated all
512 continuations, and the first branch with the lowest mean of its best two
continuation costs was executed.

Five matched arms were evaluated on PushT and Cube at horizons 75 and 150,
using the same 12 base starts per task and learned seeds 7201--7203:

1. VAD greedy with 300 candidates;
2. VAD greedy with 576 candidates, matching continuation rollout count;
3. VAD continuation, the proposed planner;
4. diagonal-Gaussian continuation; and
5. direct eight-mode GMM continuation.

## Task-first closed-loop results

Each seed entry below is success over the same 12 paired base starts. The mean
is across all three model seeds.

| Task | Horizon | Arm | Seed 7201 | Seed 7202 | Seed 7203 | Mean |
|---|---:|---|---:|---:|---:|---:|
| PushT | 75 | VAD greedy 300 | 41.67% | 50.00% | 50.00% | 47.22% |
| PushT | 75 | VAD greedy 576 | 33.33% | 50.00% | 41.67% | 41.67% |
| PushT | 75 | **VAD continuation** | 33.33% | 50.00% | 66.67% | **50.00%** |
| PushT | 75 | Gaussian continuation | 58.33% | 25.00% | 58.33% | 47.22% |
| PushT | 75 | GMM continuation | 8.33% | 25.00% | 25.00% | 19.44% |
| PushT | 150 | VAD greedy 300 | 33.33% | 25.00% | 16.67% | 25.00% |
| PushT | 150 | VAD greedy 576 | 8.33% | 25.00% | 0.00% | 11.11% |
| PushT | 150 | **VAD continuation** | 58.33% | 50.00% | 25.00% | **44.44%** |
| PushT | 150 | Gaussian continuation | 25.00% | 25.00% | 25.00% | 25.00% |
| PushT | 150 | GMM continuation | 16.67% | 8.33% | 41.67% | 22.22% |
| Cube | 75 | VAD greedy 300 | 100.00% | 91.67% | 100.00% | 97.22% |
| Cube | 75 | VAD greedy 576 | 91.67% | 91.67% | 91.67% | 91.67% |
| Cube | 75 | **VAD continuation** | 100.00% | 91.67% | 100.00% | **97.22%** |
| Cube | 75 | Gaussian continuation | 100.00% | 91.67% | 100.00% | 97.22% |
| Cube | 75 | GMM continuation | 83.33% | 91.67% | 91.67% | 88.89% |
| Cube | 150 | VAD greedy 300 | 100.00% | 100.00% | 91.67% | 97.22% |
| Cube | 150 | VAD greedy 576 | 100.00% | 100.00% | 91.67% | 97.22% |
| Cube | 150 | **VAD continuation** | 100.00% | 100.00% | 100.00% | **100.00%** |
| Cube | 150 | Gaussian continuation | 91.67% | 91.67% | 100.00% | 94.44% |
| Cube | 150 | GMM continuation | 91.67% | 83.33% | 91.67% | 88.89% |

Cube is explicitly a ceiling-heavy task here: VAD continuation and greedy
VAD-300 were at or above 95% for both horizons. The more diagnostic result is
PushT, especially horizon 150, where continuation VAD reached 44.44% versus
25.00% for greedy VAD-300 and Gaussian continuation, 11.11% for compute-matched
greedy VAD-576, and 22.22% for GMM continuation.

## Aggregate contrasts and uncertainty

| Arm | PushT task average | Cube task average | Equal-task/equal-horizon |
|---|---:|---:|---:|
| VAD greedy 300 | 36.11% | 97.22% | 66.67% |
| VAD greedy 576 | 26.39% | 94.44% | 60.42% |
| **VAD continuation** | **47.22%** | **98.61%** | **72.92%** |
| Gaussian continuation | 36.11% | 95.83% | 65.97% |
| GMM continuation | 20.83% | 88.89% | 54.86% |

The registered paired contrasts use 10,000 bootstrap resamples of
`(task, base_start)` clusters. Each resampled cluster retains both horizons,
all arms, and all three seeds; episodes and seeds are not treated as
independent observations.

| Contrast: VAD continuation minus... | Point difference | Paired 95% interval | Frozen comparator rule |
|---|---:|---:|---|
| VAD greedy 300 | +6.25 pp | [-0.69, +13.89] pp | Pass |
| VAD greedy 576 | +12.50 pp | [+4.86, +20.83] pp | Pass |
| Gaussian continuation | +6.94 pp | [-2.78, +16.67] pp | Pass |
| GMM continuation | +18.06 pp | [+8.33, +27.78] pp | Pass |

All four point differences were positive, and all task-average differences
were also positive. Therefore both the frozen continuation-mechanism gate and
the diffusion-specificity gate passed. The uncertainty is more cautious than
the binary gate: the intervals exclude zero against compute-matched greedy
VAD-576 and GMM, but include zero against greedy VAD-300 and diagonal
Gaussian. This development experiment supports a confirmation study; it is
not, by itself, a settled superiority claim.

## Timing and adapter-domain diagnostics

| Arm | Mean post-first-stage median seconds per planner call |
|---|---:|
| VAD greedy 300 | 0.0568 |
| VAD greedy 576 | 0.0569 |
| **VAD continuation** | **0.1134** |
| Gaussian continuation | 0.0614 |
| GMM continuation | 0.0623 |

Continuation VAD was about twice as slow as greedy VAD and about 1.8 times as
slow as the non-diffusion continuation controls. E18 is therefore a
performance/mechanism result, not an efficiency result.

Every proposal bank met the frozen legality and diversity rules, and every
adapter prediction was finite. However, Cube remained the adapter-domain
warning identified by E17. The maximum absolute standardized predicted state
reached 10.37 for Cube VAD continuation, 22.57 for Cube Gaussian continuation,
and 57.83 for Cube GMM continuation. These values are reported rather than
post-hoc clipped or used to tune the result.

## Scientific interpretation

E18 answers its narrow development question positively:

1. The actual two-stage continuation score improved VAD's point estimate over
   both 300-candidate greedy selection and a 576-rollout compute control on
   both task averages. Extra candidate count alone did not explain the gain.
2. VAD continuation also exceeded both a diagonal-Gaussian and a multimodal
   GMM continuation planner under the same adapter, starts, horizons, branch
   counts, best-two rule, and Le-WM budget. The result is therefore not merely
   evidence that any learned proposal distribution plus lookahead helps.
3. The strongest useful evidence is PushT at horizon 150. Cube is largely
   saturated and should not carry the paper narrative.
4. The limited 12-start development sample leaves intervals overlapping zero
   for the greedy-300 and Gaussian contrasts. A new untouched confirmation is
   necessary before claiming robust superiority over those controls.
5. E17 remains failed, the adapter was chosen through outcome-informed
   development, and E18 cannot validate the adapter preflight retroactively.

The next legitimate step is to draft, review, and checksum-freeze a separate
confirmation protocol before exposing any new holdout. That protocol should
retain the exact E18 method and primary controls, use task-first reporting and
the same start-cluster bootstrap, and define the claim language in advance.
It must not be launched or consume D5 merely because E18 passed.
