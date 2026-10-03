# DTV-EFF1: complete preserved matched success–cost result

3 October 2026. Actual final lineage: R4. This is the fixed estimation study, not a new selection, non-inferiority test, promotion, or follow-up experiment.

## Main result

DTV30 does **not** establish the intended general success–cost advantage over the historical ACID30 reconstruction. Equal-task success is 80.729% versus 83.472%: DTV30 minus ACID30 is **−2.743 percentage points**, with the frozen 32-cell Bonferroni percentile interval **[−5.250, −0.341] pp**. Complete cumulative planning cost is 4.17218 versus 4.14686 seconds/episode: **+0.02532 s**, family interval **[−0.07866, +0.13020] s**. Thus success is lower in this fixed family while a planning-cost advantage is not established. An interval crossing zero is not equivalence.

The task pattern is heterogeneous: Cube favors DTV30 on both primary axes; Reacher strongly favors ACID30 on success; PushT's primary differences remain unresolved. Cube cannot be selected as a substitute for the prospectively fixed equal-task result. No unfavorable cases, initial successes, fixed blocks, or configurations were dropped.

## All eight success–cost points

Success is native success percent. Cost is complete cumulative observation-to-action planning seconds per episode, including unsuccessful scientific outcomes and buffered-action work. Parent means average the three fixed blocks first; task means receive equal weight in the aggregate. These are point estimates; the exact nominal point intervals and all other frozen diagnostics are in [REPORT.json](REPORT.json).

| Configuration | PushT success % | PushT cost s | Reacher success % | Reacher cost s | Cube success % | Cube cost s | Equal-task success % | Equal-task cost s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DTV30 | 82.917 | 4.56426 | 77.083 | 5.29607 | 82.188 | 2.65622 | 80.729 | 4.17218 |
| DTV28 | 83.854 | 4.21363 | 79.167 | 4.90495 | 81.979 | 2.42877 | 81.667 | 3.84912 |
| ACID30 | 82.604 | 4.48858 | 89.792 | 5.12302 | 78.021 | 2.82898 | 83.472 | 4.14686 |
| ACID28 | 81.667 | 4.19484 | 87.917 | 4.80232 | 77.708 | 2.64074 | 82.431 | 3.87930 |
| Forward30 | 79.479 | 4.59108 | 81.979 | 5.01568 | 71.979 | 2.90546 | 77.813 | 4.17074 |
| Forward28 | 80.833 | 4.23444 | 81.979 | 4.70398 | 71.146 | 2.73591 | 77.986 | 3.89145 |
| Plain30 | 79.688 | 4.42777 | 81.458 | 4.94887 | 70.625 | 2.89803 | 77.257 | 4.09156 |
| Plain28 | 80.208 | 4.14116 | 81.458 | 4.63812 | 70.833 | 2.70461 | 77.500 | 3.82796 |

## Every prespecified primary/practical contrast

Every row is DTV30 minus the listed comparator. Positive success favors DTV30; negative cost favors DTV30. Intervals below are the unchanged Bonferroni percentile intervals across the 32-cell family (four comparisons × four scopes × two axes). All nominal 95% intervals are also retained in the complete report.

| Scope | Comparator | Success difference pp [family interval] | Planning difference s [family interval] |
|---|---|---:|---:|
| PushT | ACID30 | +0.312 [−3.978, +4.479] | +0.07568 [−0.10089, +0.26358] |
| Reacher | ACID30 | −12.708 [−18.021, −7.897] | +0.17305 [−0.03473, +0.37506] |
| Cube | ACID30 | +4.167 [+1.126, +7.188] | −0.17276 [−0.29455, −0.05904] |
| Equal task | ACID30 | −2.743 [−5.250, −0.341] | +0.02532 [−0.07866, +0.13020] |
| PushT | ACID28 | +1.250 [−2.917, +5.521] | +0.36942 [+0.19533, +0.54698] |
| Reacher | ACID28 | −10.833 [−16.458, −5.397] | +0.49375 [+0.28091, +0.69965] |
| Cube | ACID28 | +4.479 [+1.230, +7.812] | +0.01548 [−0.09685, +0.12129] |
| Equal task | ACID28 | −1.701 [−4.444, +0.868] | +0.29288 [+0.19086, +0.39307] |
| PushT | Forward30 | +3.438 [−0.332, +7.520] | −0.02682 [−0.18721, +0.13190] |
| Reacher | Forward30 | −4.896 [−10.208, +0.124] | +0.28039 [+0.07827, +0.48251] |
| Cube | Forward30 | +10.208 [+6.543, +14.375] | −0.24924 [−0.38603, −0.12181] |
| Equal task | Forward30 | +2.917 [+0.139, +5.458] | +0.00144 [−0.09339, +0.09753] |
| PushT | Plain30 | +3.229 [−0.417, +6.895] | +0.13649 [−0.00616, +0.27460] |
| Reacher | Plain30 | −4.375 [−9.603, +0.853] | +0.34719 [+0.15426, +0.53854] |
| Cube | Plain30 | +11.563 [+7.396, +16.289] | −0.24181 [−0.39215, −0.10106] |
| Equal task | Plain30 | +3.472 [+0.959, +6.042] | +0.08062 [−0.01332, +0.17357] |

DTV30 improves equal-task success over Forward30 and Plain30 within this frozen interval family, but neither comparison establishes a complete planning-cost saving. Against ACID28, DTV30 has a clearly higher complete planning cost and uncertain family-adjusted success difference. The eight points are all retained; no new post-outcome comparison family, budget selection, acceptable-loss margin, or efficacy gate is introduced.

## Timing interpretation and initial success

Equal-task solver-only seconds/episode are DTV30 4.14261 versus ACID30 4.11661. First-decision observation-to-action cost is 2.96978 versus 2.97337 s; later-decision cost is 1.17642 versus 1.14798 s. Average decision counts are 1.22882 versus 1.21007; average actions are 26.38160 versus 25.94965. These retained descriptive measurements do not establish a faster DTV solver. Later states and trajectories are policy-dependent.

Cube's DTV30 cost advantage accompanies fewer decisions (0.77292 versus ACID30 0.81563) and actions (15.04375 versus 16.68021); its first-decision costs are close (2.04634 versus 2.05175 s). Do not attribute all episode savings to solver speed. All setup, authentication, construction, reset, audit, CPU, peak memory and operational-time diagnostics remain in the complete report.

Initial native success is retained with zero actions/plans in the frozen primary population: PushT 1/320 parents (3/960 block episodes; 0.3125%), Reacher 0/320 (0%), Cube 132/320 (396/960; 41.25%). This substantial Cube initial-success frequency is descriptive context, not a reason to redefine the endpoint or remove those parents after inspection.

## Complete data and limitations

[REPORT.json](REPORT.json), copied byte-for-byte from the verified SSD archive, contains all 23,040 episode summaries, all 72 task/configuration/fixed-block points, all 960 parent identities and all parent contrast effects, all 32 contrasts with nominal and family intervals, and all worker setup/authentication diagnostics. Its SHA256 is `6c91986e059a01bc2c54fa28165fa4161d75904487760b5916078b45697dd727` (22,044,641 bytes). No estimator or scientific result was rerun during publication.

Independent units are 320 canonical parents per task, not 960 independent block episodes. Scorer seeds 6101/6102/6103 and proposals 7101/7102/7103 are fixed repeated blocks, not independent training-seed replication. The unchanged 10,000 shared whole-parent bootstrap uses seed 20261001. It assumes appropriate exchangeability of eligible parents; no finite-sample guarantee or untouched-test/population-wide confirmation is asserted. Bonferroni extreme percentile tails are relatively coarse at this resample count. The P2 developmental role and historical checkpoint exposure remain disclosed.

The short physical interface is H5 grouped actions, five primitive actions/group, 25-action replanning cadence and at most 50 delivered actions. These endpoints are not interchangeable with older longer-horizon success rates. ACID is the exact historical reconstruction, not official-code superiority evidence. There is no non-inferiority/equivalence claim, success-conditioned timing filter, fitting, reselection, training, model promotion, extra budget point or automatic next experiment. DTV-EFF0's failed 10% screen and smaller positive saved-input timing result, all historical decisions and E12 drafts remain unchanged.

## Acceptance, accounting and preservation

All 2,880 GPU workers × eight configurations = 23,040 episodes passed actual R4 independent endpoint/action/evidence acceptance. CPU preflight and analysis give 2,882 successful logical tasks. The included nine-worker/72-episode technical gate was reused, never repeated. Final actual attempts are 2,885, including failed allocations 312924/19 s, 312928/19 s and 312950/21 s, preserved and charged once. No successful worker was recomputed. Full attempt-level details are in [FINAL-ALLOCATION.json](FINAL-ALLOCATION.json).

GPU allocation: 166,945 seconds (166,886 successful +59 failed), below 864,000. CPU-stage allocation-wall: 587 seconds (178 preflight +409 analysis), below 14,400. Original serial RTX6000 Ada/gpu09, GPU 4 CPU/8 GiB/300 s and CPU 4 CPU/8 GiB/7,200 s limits were retained. No resource/security/data-access expansion occurred. Completion observation had no STOP, empty controller stderr, no live/pending/ambiguous allocation, and expected exited controller PID330036/start_ticks962433210.

One final study archive was created and whole/member verified on the cluster, then transferred once through the configured bastion into native Windows D:. Archive: **1,852,456,960 bytes /77,458 members**, SHA256 `bf1b68acd37a5356e1c5f64fedc3ad12393c413569fbe0ca07283f2b7d341a79`. [SSD-VERIFIED.json](SSD-VERIFIED.json) records actual whole/every-member verification on THESIS_SSD volume `0a2f1ba9-0000-0000-0000-100000000000`, with 312,258,342,912 bytes free at transfer start. Request SHA256: `4fd7a1f77f49abdce9d0147de30fa7d7d768907426a982f0c7e312d2bec6d35f`.

SSD destination: `D:/THESIS-BACKUPS/dtv-success-cost-20261001/run-bc3b36c71362f172/final.tar`. Its sibling `REQUEST.json` preserves the complete member inventory and source hashes. The archive includes original scientific source, all run/analysis/input/endpoint/worker records, reused models, original and R1–R4 source/control/approval/authority/STOP/error/partial/ledger/resolution records. No completed small package or historical-study archive was recreated or retransferred. Archive size is below 4.2 GB; run payload before archive was 1,265,745,607 bytes below 4 GB; all inclusive copies remain below the 13 GB envelope. Archive and transfer were within their separate 7,200 s deadlines (220.797 s orchestration, 40.082 s archive construction/readback; 184.938 s transfer orchestration, 160.438 s actual transfer/verification).

Post-preservation local report extraction first used an incorrect direct-script import context and failed before any output (0.419 s); invoking the unchanged helper as a module from the repository succeeded (9.534 s). This was an artifact-reading invocation issue, not a research/cluster fault, and did not repeat acceptance, analysis, archive, transfer or compute. No scientific closure was edited. The completion helpers and receipts are separate from all frozen executed packages.

Publication and handoff receipts are recorded separately after exact remote commit readback and delivery to the existing reasoning conversation. The same monitor is paused after that final handoff, retaining history. No automatic promotion or new experiment.
