# LGP-RB1 proposed execution envelope — not launch authorization

## Counts and hard limits

Exactly two first-decision compatibility GPU jobs (600 seconds each), 384
main GPU jobs (180 seconds each, two horizons/job), and one CPU analysis
allocation (7,200 seconds). One A6000 at a time, 4CPUs/24GiB per GPU job;
analysis 4CPUs/8GiB without GPU request/passthrough. Same site-approved
account/partitions/QoS and pinned Python3.11.10/Torch2.5.1+cu121 runtime.

**Maximum new GPU reservation: 70,320 allocation-seconds = 19.5333 GPU-hours.**
**CPU-analysis ceiling: 7,200 allocation-wall seconds = 2 hours (8 core-hours).**
These are new charges, not a reset of LGP1 historical accounting. Exactly
386GPU plus oneCPU allocations; no automatic failure/retry allocations.
Any technical failure consumes this envelope, preserves evidence and stops.
Main workers preserve a 30-second margin; compatibility/analysis preserve
60 seconds. A timeout is not permission to change scientific throughput or
increase caps. Pending queue time is not allocation time.

Zero fits, zero updates, zero new training examples. 768 new main episodes,
384 authenticated historical30 episodes, 1,152 combined episodes. The two
compatibility jobs execute 16 first decisions, zero physical actions and
zero complete technical episodes. No additional endpoint is introduced.

At full main physical budgets: 172,800 new delivered actions, at most
11,520 planning stages, and 10,368,000 scored candidate trajectories
(1,728,000 at budget1; 8,640,000 at budget5), each with15 primitive predicted
actions. Native early termination reduces actual counts, never enlarges
budgets. Compatibility adds79,200 candidate trajectories across its16
first-decision queries. These counts are workload, not independent evidence.

## Measured timing model, not round-count division

Accepted LGP1 recorded 9,558 main GPU allocation-seconds for192 jobs, 5,485
planning stages, and 4,221.451 stage-planning seconds. `MEASURED-COST.json`
retains each family/seed/source job's observed allocation, stage count and
component timing, and both proposed new budget estimates.

For each original paired-horizon job retain
`max(0, allocation − summed planning time)` as setup/delivery/other overhead.
Allow **30 stages** for each new H75/H150 job, regardless of the old success
or early stop. Scale only the measured refinement component by n/30; retain
context/proposal/other planning time. This is not total-time division by30.

| New main-work scenario | GPU allocation estimate |
| --- | ---: |
| Full physical budget, only refinement scales | 12,496.003s / 3.471h |
| Full physical budget, no refinement speedup | 19,548.117s / 5.430h |
| Twice the no-speedup estimate, plus both full technical reservations | 40,296.233s / 11.193h |
| Hard reservation, all386 new GPU jobs at their limits | 70,320s / 19.533h |

First two rows exclude technical compatibility (add at most1,200s); the
last two include it. CPU analysis is additional, capped at2 allocation-hours.
Per-main-job no-speedup estimates average50.907s and are at most58s; proposed
hard limit180s is a margin, not measured new-budget performance. New bank
hashing/synchronization, different trajectories, hardware contention and
cold filesystem/runtime overhead remain uncertain. Actual complete-job
timings and all failed allocations must be reported.

## Verification, control, setup and backup

Setup/container/source/input authentication and worker sealing consume the
same GPU job allocation; no extra setup GPU job. Technical compatibility
uses its two explicit reservations. Final endpoint and aggregate checks use
the one CPU allocation. The detached host controller reads metadata/seals
and verifies files serially outside Slurm; its wall/CPU time, source checks,
archive verification and transfer time must be separately recorded. They
are not included in the two-hour *analysis allocation* ceiling or disguised
as GPU time. A planning allowance of30 host core-minutes for metadata/hash/
archive work is an estimate, not an extra research allocation or license to
run research on the login node. No new dependencies or environment changes.

Expect source transport to be small (<10MB), new result transport conservatively
up to2.1GB. At10MB/s, 2.1GB is about3.5min of transfer; at1MB/s, about35min.
Re-reading the1.734GB old SSD archive is additional local verification I/O,
not a second network download. At50MB/s this alone takes about35s per pass;
real verification times will be measured. Queueing/network availability can
make elapsed completion longer; none of these estimates is a promised ETA.
For context, accepted LGP1's1.734GB archive took9.886s host wall/7.064s CPU
to construct and verify, and56.813s for transfer plus member verification
(`docs/local-goal-proposals-20260918/FINAL-ACCOUNTING.json`). These observations
are not a guaranteed bandwidth or a reason to omit future verification costs.
No laptop/SSD liveness gate stops healthy cluster execution. If the SSD is
unavailable at completion, keep compute intact and wait for reconnection.

## Storage, inclusive preservation and exclusive namespaces

Hard new worker ceiling **2,000,000,000bytes**; source/control/log reservation
**100,000,000bytes**; total remote ceiling **8,000,000,000bytes**, including
old preserved history, new work, failures and final archive. Per-episode
row-plus-endpoint cap remains10,000,000bytes; compact endpoint NPZ remains
at most50,000bytes. CPU aggregate worker cap200MB. Caps are intersecting,
not additive permission to exceed the total. Job filesystem guards,
controller checks and final archive-reservation check enforce them.

Historical remote occupancy was3,466,064,528bytes, including the accepted
1,734,420,480-byte archive; old main worker payloads were232,714,292bytes and
old analysis228,389,686bytes. New round logs cover 1+5 rather than30
populations per trajectory; roughly6/30 of one old grid's round storage,
plus768 compact endpoints, fingerprints, reports/accounting. This rough
scaling supports a conservative2GB new-worker ceiling; it is not a guarantee
based on identical trajectories. Adding2.1GB new live files and their2.1GB
archive to3.466GB history is approximately7.666GB, below8GB, leaving tar
overhead margin. Recheck actual history size and every cap before launch.

Future namespace is
`/lustreFS/data/superworld/ckontzias/thesis/experiments/local-goal-search-budget-20260919/run-<new-manifest-prefix>`.
Create it exclusively; no prior attempt, no overwrite, no old fit restart.
Historical models/results stay in their original roots. Backup only to
`D:/THESIS-BACKUPS/local-goal-search-budget-20260919` on the verified THESIS_SSD
volume with40GB free; reverify old+new archive union. The separate WSL
filesystem I/O issue is not modified or used for bulk storage.

## Remaining launch decision

Approve or decline this single exact387-allocation envelope after reviewing
the source package and synthetic test receipt. Preparation has no authorized
execution approval. No job, fit, simulator, frozen research-model forward
pass, new label or new scientific result is produced by preparation.
