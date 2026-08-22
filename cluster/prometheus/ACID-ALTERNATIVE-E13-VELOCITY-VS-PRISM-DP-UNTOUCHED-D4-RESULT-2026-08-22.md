# E13 velocity diffusion versus PRISM-DP reconstruction: untouched-D4 result

Date: 22 August 2026

Status: complete, checksum-verified, and independently recomputed

Frozen decision: `compute_efficient_alternative_to_disclosed_prism_dp_reconstruction`

## Verdict

E13 does **not** establish that goal-conditioned velocity diffusion is superior to the disclosed PRISM-DP reconstruction. At the primary `K=300` budget, velocity diffusion achieved 93.53% equal-task success and PRISM-DP achieved 92.97%, a difference of **+0.56 percentage points** with a 95% paired start-cluster interval of **[-0.47, +1.58]**. The interval crosses zero, and the task effects were mixed: -1.67 points on PushT, +3.33 on Reacher, and a tie on the saturated Cube task.

E13 does support the narrower frozen claim that velocity diffusion is a **compute-efficient alternative** to this disclosed PRISM-DP reconstruction. Its one-sided 95% lower bound was -0.31 points, inside the prespecified -3-point margin; it had lower median paired runtime on every task; it used fewer active learned parameters, no second image encoder, and less peak allocated CUDA memory.

The E13 velocity-diffusion versus Gaussian contrast was statistically positive, but the frozen diffusion-mechanism replication gate did not pass because the Gaussian control exceeded the prespecified 25% proposal-boundary/clipping threshold on Reacher for two model seeds. E13 therefore cannot be presented as a clean new mechanistic replication of the E11 diffusion-specific result.

Allowed claim:

> Under the frozen three-task, three-seed `K=300` protocol, the E11 velocity-diffusion selector matched the success of our disclosed PRISM-DP best-of-N reconstruction within the prespecified three-point margin while using fewer learned parameters, no second image encoder, lower peak CUDA memory, and lower median paired runtime on every task.

This claim applies to the disclosed reconstruction in this repository, **not official PRISM**.

## Frozen study and information barrier

The [E13 protocol](ACID-ALTERNATIVE-E13-VELOCITY-VS-PRISM-DP-UNTOUCHED-D4-PROTOCOL-2026-08-22.md) was frozen before the identifier-only D4 manifests were generated. The study used:

- three tasks: PushT, Reacher, and Cube;
- 400 untouched D4 starts per task;
- three fixed model/planner seeds: 6101, 6102, and 6103;
- five arms: latent Gaussian `K=300`, velocity diffusion `K=16` and `K=300`, and PRISM-DP reconstruction `K=16` and `K=300`;
- 18,000 closed-loop episodes across 360 evaluation shards.

Slurm jobs were 298616 for the three identifier-only manifests, 298617 for the 360-cell evaluation array, and 298618 for the dependency-locked aggregate analyzer. Every manifest cell, evaluation cell, and the analyzer terminated `COMPLETED` with exit code `0:0`.

The analyzer verified all 360 shards before reading any metric-bearing file. It recorded:

```text
all_360_shards_complete_before_metric_read=true
d3_outcomes_read=false
protected_p4_c1_i1_read=false
```

No partial D4 metric, D3 outcome, or protected holdout was read before aggregate unlock.

## Task-first success rates

| Arm | PushT | Reacher | Cube | Equal-task |
|---|---:|---:|---:|---:|
| Latent Gaussian, `K=300` | 93.50% | 79.58% | 99.83% | 90.97% |
| PRISM-DP reconstruction, `K=16` | **97.25%** | 75.67% | 100.00% | 90.97% |
| PRISM-DP reconstruction, `K=300` | **97.25%** | 81.67% | 100.00% | 92.97% |
| Velocity diffusion, `K=16` | 95.50% | **85.08%** | 100.00% | **93.53%** |
| **Velocity diffusion, `K=300`** | 95.58% | 85.00% | 100.00% | **93.53%** |

Cube was at or extremely near ceiling for every learned proposal arm. It provides essentially no separation between the two primary methods.

## Primary `K=300` comparison

Velocity diffusion minus PRISM-DP reconstruction:

| Quantity | Result |
|---|---:|
| Equal-task difference | +0.56 points |
| PushT difference | -1.67 points |
| Reacher difference | +3.33 points |
| Cube difference | 0.00 points |
| Paired start-cluster 95% interval | [-0.47, +1.58] points |
| One-sided 95% lower bound | -0.31 points |
| Exact paired start-cluster sign test | 117 positive, 94 negative, 989 ties |
| Exact one-sided / two-sided p-value | 0.06485 / 0.12969 |

The frozen superiority gate required a positive point estimate, a strictly positive one-sided lower bound, positive effects on at least two tasks, no task loss worse than five points, and valid treatment/control proposal diagnostics. The point estimate, worst-task condition, and integrity diagnostics passed. The lower-bound and two-task-win conditions did not. Superiority is therefore false.

## Gaussian control and mechanism gate

Velocity diffusion minus the capacity-matched latent Gaussian control at `K=300` was:

- **+2.56 points** equal-task;
- +2.08 on PushT, +5.42 on Reacher, and +0.17 on Cube;
- 95% paired start-cluster interval **[+1.39, +3.72]**;
- one-sided 95% lower bound **+1.58 points**;
- 155 positive, 89 negative, and 956 tied start clusters; two-sided exact p = 0.0000285.

Those efficacy conditions were positive. The frozen mechanism gate nevertheless failed its proposal-integrity condition. The Gaussian Reacher boundary/robust-clipping maximum was 30.31% for seed 6102 and 47.45% for seed 6103, above the registered 25% ceiling. Seed 6101 was 24.86%, just below the ceiling. This does not erase the observed contrast, but it prevents E13 from being called an unqualified fresh replication that diffusion itself caused the advantage.

E11 remains the clean untouched study supporting the diffusion-specific comparison against Gaussian. E13 adds a caution that the Gaussian baseline can become boundary-limited on Reacher under this D4 construction.

## Secondary `K=16` comparison

Velocity diffusion minus PRISM-DP at `K=16` was +2.56 equal-task points, with a 95% interval of [+1.47, +3.64]. Its task effects were 0.00 on Cube, -1.75 on PushT, and +9.42 on Reacher. This comparison was explicitly frozen as secondary-only and cannot substitute for the primary `K=300` decision. It does, however, show that the methods' relative behavior is task-dependent rather than a uniform suite-wide advantage.

## Efficiency result

The paired timing comparison used 24 matched blocks per task. Negative time differences favor velocity diffusion.

| Task | Median seconds/episode difference | Velocity/PRISM-DP ratio | Approximate reduction |
|---|---:|---:|---:|
| PushT | -0.1302 s | 0.7998 | 20.02% |
| Reacher | -0.1268 s | 0.8376 | 16.24% |
| Cube | -0.1335 s | 0.8715 | 12.85% |

Additional frozen resource checks all favored velocity diffusion:

- active learned parameters: 7,245,554-7,322,429 for velocity diffusion versus 19,302,466-19,303,429 for PRISM-DP;
- peak allocated CUDA memory: 525,480,960 versus 573,415,424 bytes;
- velocity diffusion did not require PRISM-DP's second image encoder.

The compute-efficient-alternative gate was prespecified to pass only if superiority failed, the primary one-sided lower bound remained at least -3 points, velocity diffusion was faster on every task, and at least one registered resource advantage held. All of those conditions passed.

## Inference and independent audit

The primary bootstrap did not treat individual seed-episodes as independent. For each task, the three fixed-seed paired outcomes were first averaged within each of 400 starts; those 1,200 task-start clusters were then resampled within task and tasks were weighted equally. The primary bootstrap used 100,000 repetitions and frozen seed 2026082202. A secondary two-way paired seed-block/start bootstrap used 100,000 repetitions and seed 2026082203.

After the immutable aggregate was complete, [the read-only independent verifier](verify_gdp_cem_e13_result.py) reconstructed all rates, contrasts, exact sign tests, both bootstrap families, integrity failures, and gates from the 3,600 paired task/seed/start rows. It reproduced the frozen analyzer's decision exactly.

## Provenance hashes

| Artifact | SHA-256 |
|---|---|
| Frozen protocol | `65d56b613f12ad896c395e6feb4fc6d39f404bc802045369d0a88b638690af58` |
| Frozen source manifest | `3f66e2a3ca673c5d3c3ddff74d41927e8ad412cd9baa89dddcf95f2ab062ee7a` |
| Aggregate `summary.json` | `d273cc1c9ec84cca0f57835987fe9be87299d1d2622864cd2fefa6536bc4078e` |
| Aggregate `paired-outcomes.tsv` | `802aa3ea75bad585b85c692b1345f1b81de1920e8f688d39302c689b295e7c2c` |
| Aggregate `input-manifest.json` | `fc7bbb7deefe5689f21c64ba34dddfff4fc87800503100d820bffa11320ac8d8` |
| Aggregate `audit.txt` | `96b21d3831604d96623a12c777e5306a70771a57ecd884af6f03ef6d965a64e8` |
| PushT D4 manifest TSV | `b3d4b6e5257d6ab501ec3c949adab496cd6d1f68bab8f76cf0676d9387043e88` |
| PushT D4 manifest provenance | `8d1335436b34ec1b8a4559fc1028b5c177333b15e1e226ff8c0f07c33d3f9e0d` |
| Reacher D4 manifest TSV | `65fa0ab167c038ac87f5d09011e759481f446d3e18aa48ad1c1722cb3eed84bb` |
| Reacher D4 manifest provenance | `311cbf3fd1640bc90fc98e759f18e54b86ca88397aa389c6bc7bfb1a27e4ba1a` |
| Cube D4 manifest TSV | `979cfd73fec0ce04ae1ab3b472f4f644796289bb3374b70f90b30f0b49c85cc6` |
| Cube D4 manifest provenance | `7773af535b4acf0691ec72e5a6ca2dac0de705d48f3f485af6a7fcd8b70fd159` |

The immutable source snapshot was:

```text
/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e13-3f66e2a3ca673c5d
```

## Scientific implication

The most defensible E13 conclusion is not “diffusion beats PRISM.” It is:

1. At equal `K=300`, velocity diffusion and this disclosed PRISM-DP reconstruction had statistically indistinguishable aggregate success, with a small positive point estimate and mixed task effects.
2. Velocity diffusion met the frozen non-inferiority-style margin and was measurably lighter and faster, supporting a compute-efficient-alternative claim.
3. E13's positive velocity-versus-Gaussian contrast is descriptive and statistically strong, but the registered Gaussian integrity failure prevents using this study as an unqualified mechanism replication.
4. Cube was saturated, so PushT and Reacher carry the meaningful method separation.
5. Nothing in E13 supports claims about official PRISM, universal superiority, or untested backbones.

No gate, arm, seed, task, budget, checkpoint, or D4 outcome was tuned or rerun after this result.
