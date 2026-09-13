# What the completed paired outcomes tell us

13 September 2026. This is a new exploratory analysis of the completed 1,600-reference study, not a new planner experiment or a change to its stopping decision. No model, simulator, or cluster job was run. The 4,400 unevaluated references were not accessed.

The exact summary, binary outcome tensor and historical verifier were read from repository commit `001aad99a2e2e6a141797e0c516604e7188d706a`. All three content hashes matched before analysis. The tensor reproduced every method/horizon success rate and every original primary difference and reference-level standard error. A separate standard-library ZIP/NPY reader and integer counter checked the new pair tables and contrasts without importing the diagnostic implementation or NumPy.

## 1. SAGE does not succeed on every case diffusion solves

There are 9,600 paired reference/horizon/fixed-seed measurements for each method pair: 1,600 references × 2 horizons × 3 blocks. These are not 9,600 independent trials.

| VAD continuation and full SAGE | Paired measurements |
|---|---:|
| Both succeed | 681 |
| VAD succeeds; SAGE fails | 884 |
| SAGE succeeds; VAD fails | 1,339 |
| Both fail | 6,696 |
| Total | 9,600 |

This reproduces VAD's 1,565 successes (16.30%) and SAGE's 2,020 (21.04%). Averaging both horizons and three blocks within each reference, 344 references favor VAD, 590 favor SAGE, and 666 tie.

A hypothetical selector with advance knowledge of both complete-policy outcomes would succeed on 2,904 measurements, or 30.25%. **That is a nondeployable between-policy oracle, not an achieved hybrid and not evidence that VAD's candidate bank contains SAGE's successful actions.** The complementarity could reflect state-specific capabilities, sampling variation, distinct trajectories, or several factors. These binary outcomes do not identify which explanation is responsible or whether the better policy can be selected in advance.

## 2. Continuation's advantage over greedy diffusion is concentrated at H150

H75 and H150 denote reference endpoints 75 and 150 actions after initialization, not minimum solution lengths.

| VAD continuation minus control | H75 difference | H150 difference | Overall difference |
|---|---:|---:|---:|
| Greedy VAD-300 | +0.6458 pp | +3.7708 pp | +2.2083 pp |
| Greedy VAD-576 | −0.2500 pp | +2.6042 pp | +1.1771 pp |
| Gaussian continuation | +3.7500 pp | +2.1250 pp | +2.9375 pp |
| GMM continuation | +1.8125 pp | +0.1875 pp | +1.0000 pp |
| Full SAGE | −5.2917 pp | −4.1875 pp | −4.7396 pp |

For greedy-300, the within-reference difference between the H150 and H75 treatment effects is +3.125 points. The new 10,000-resample reference-cluster percentile interval is [+1.417, +4.812] points. This supports investigating the longer-offset effect, while the H75 contrast remains uncertain: +0.646 points with interval [−0.646, +1.958]. The H150 interval is [+2.625, +4.917].

These intervals are **post-result, unadjusted exploratory summaries**. They are not adjusted for the earlier sequential stopping rule or the 20 inspected diagnostic contrasts and are not new registered confirmation claims. The historical primary tests remain in the original SUMMARY.json. The new script reports the whole diagnostic family, not only favorable intervals.

## 3. GMM remains an important control

Diffusion continuation's aggregate point advantage over GMM is one point. At H150 the difference is only +0.1875 points, with exploratory interval [−0.9375, +1.3333]. The aggregate exploratory interval is [+0.1146, +1.8750], but it is not a multiplicity- or sequentially-adjusted primary test. We should not turn this into an unqualified claim that diffusion beats all multimodal alternatives.

The three seed blocks are fixed trained-checkpoint/evaluation blocks. Neither the bootstrap nor these contrasts estimates variability over arbitrary independent retrainings.

## 4. A gain is not the same as uniformly safer selection

Against greedy-300, continuation succeeds on 887 paired measurements where greedy fails, but loses on 675 where greedy succeeds. That nets the recorded +2.208-point effect. These controls have different first-bank sizes, so this is not a same-candidate comparison and cannot isolate second-stage ranking by itself.

The next intervention should compare greedy choice and continuation choice from an identical 64-candidate first bank with controlled random streams. Actual simulator branch outcomes are then needed to distinguish missing useful proposals from bad branch ranking or inaccurate intermediate-state predictions.

## 5. Two implementation details for the next stage

The archived analyzer uses a single Euclidean norm over the four agent/block position coordinates, together with an angle criterion at the same post-action step. Applying separate 20-unit position cutoffs would change the endpoint. The new raw-trajectory reducer keeps the combined rule and labels component-level observations as supplementary diagnostics only.

The old incremental backup worker skips shards already listed in its index. Its restart alone cannot establish post-filesystem-incident byte integrity. The new backup verifier rehashes every indexed shard, including previously copied shards. It has not yet run on the user's actual backups.

## What this changes about the research plan

The evidence justifies examining different successful strategies and the larger H150 continuation benefit. It does not yet justify selecting an adapter redesign, deeper search, a value function, or a policy router as the winning solution. Those remain hypotheses for the declared controlled branch study. Native SAGE, the old VAD system, and the completed study remain unchanged.

## Reproduction and limitations

- `PAIRED-OUTCOME-DIAGNOSTICS.json`: all 15 method pairs, all 20 contrasts, fixed-block success rates, and exploratory bootstrap results.
- `INDEPENDENT-OUTCOME-RECHECK.json`: separate numerical verification of counts, point estimates and standard errors. It does not independently reproduce bootstrap quantiles or physics.
- `SUMMARY-DIAGNOSTICS.json`: the earlier aggregate-arithmetic view; it does not purport to contain individual pairing.
- `TEST-LOG.txt`: 51 local synthetic regression tests. These are not remote-runtime or new environment results.

Initial attempts to transfer the binary artifact did not yield a checksum-valid local file and were not analyzed. A later complete base64 transfer produced exactly 9,889 bytes with SHA256 `afb181230eb36d0d6081477bef910814f8b2c0208d913063df48131e4e2af7e2`; only that verified file supplied outcomes. The summary SHA256 is `305be6aa678445dce5ceddda6bae14657a730810e448121df6c8783c4318da6d`. All original repository files are unchanged.
