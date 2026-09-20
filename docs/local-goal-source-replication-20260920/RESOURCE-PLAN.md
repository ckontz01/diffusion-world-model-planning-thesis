# RB2 finite resource proposal (execution disabled)

Exactly1536serial A6000 allocations ×300s =460,800allocation-seconds (128h),
including any failed/technical work. First4jobs/32episodes are part of that grid.
One final4CPU8GiB CPU allocation7200s; no other GPU/CPU scientific job. GPU workers
request4CPU24GiB. Worker soft limit240s,60s preservation margin. No auto retry,
requeue, resume or cap increase; failures do not reset charges. Queue waiting is
not charged compute; detached-controller elapsed time is reported separately.

## Timing calculation, not perfect batching

Published RB1/LGP1 per96two-horizon job charges for GMM5/diffusion5/GMM30/diffusion30:
2730/2789/4438/5120seconds. Sum of their per-job means=157.0521seconds for the eight
episodes, WITHOUT any credit for eliminating repeated setup. Their actual average
stages per two-horizon block are29.000/28.490/28.677/28.458. Adding enough measured
planning time to reach all30stages in each arm gives159.8098seconds/new job.
1536jobs ×that estimate =68.1855GPUhours. A25% multiplier for source/packaging/I/O
variation yields199.7622seconds/job and85.2319GPUhours. Thus preparation supports
approximately68–85hours as scenarios, not guaranteed runtime. All128hours stay
reserved. No GPU jobs have been run to validate these scenarios.

This deliberately retains four setups' observed overhead despite only one
backend/two models being loaded in the new job. It does not assume perfect reuse
speedup. New worlds, hashing, endpoint checks and duplicate compact-report storage
remain. 1.5×full-budget scenario=239.7147seconds approaches the240s soft boundary;
larger slowdowns can stop the study. Failed throughput is not authority to change
the resource binding. Measured inputs and their original accounting digest are
in MEASURED-COST-INPUTS.json. Historical timing lacks some new per-episode fields;
future arms use common instrumentation.

Maximum physical actions:512×3×4×(150+300)=2,764,800.
Maximum stages:184,320. Candidate trajectories:512×3×30×(5+5+30+30)×300
=967,680,000; batched scoring calls3,225,600 and predicted primitive steps
14,515,200,000. These are compute counts, not independent source observations.

## Byte reservations and RAM

New-worker cap8,000,000,000B. Main worker hard cap5,000,000B each;1536×5MB=7.68GB.
Analysis allowance200MB gives7.88GB reserved, leaving120MB for margins. Per-episode
10MB and endpointNPZ50KB ceilings remain but the5MB/job cap is stricter. Compact
endpoint total at50KB×12,288 <=614.4MB. No full candidate banks or video.
Rows retain round summaries, measured timers and bank hashes only. Per-cell JSON
and whole worker report duplication is included in5MB/job, not ignored.

Source/control/log reservation200MB. The24GB inclusive remote cap counts declared
LGP1/RB1 history, new source/live work/failures and the complete final new archive.
Prior completed occupancy≈3.620GB. Full7.88GBworker+0.2GBcontrol budget doubled for
archive plus history≈19.780GB, before tar/member overhead. At<=40,000archive files,
2,048B/file+10,240 <=82MB; still below24GB. Runtime byte checks use actual complete
history roots, not this rounded planning occupancy. No deletion to make room.

Peak historical worker Python RSS≈1.60GB and Torch allocatedGPU≈0.241GB, excluding
children/context/reserved memory. Holding two proposer models can increase these;
4CPU24GiB/A6000 is not claimed proven adequate by summing scoped counters. The
included first4jobs verify the unchanged hard caps and record actual costs/RAM.

## Packaging, verification, backup and operational overhead

Preparation source export<20MB. Frozen package includes exact inherited runtime
and identifiers, no model/data payload. Synthetic CPU tests and metadata queries
are preparation operations, not research GPU allocations. They will be recorded.

All independent endpoint/seal verification runs within the authorized workers and
single CPU analyzer. Final host archive/member hashing and external transfer are
separately timed operational preservation, not extra GPU jobs. Historical union
archive≈1.814GB must be reverified with the new final archive. Plan several minutes
of I/O/hash/transfer overhead, not a guaranteed bandwidth; report actual time.
Remote24GB includes the archive but not a second redundant copied model set.

Destination D:/THESIS-BACKUPS/local-goal-source-replication-20260920 only;
THESIS_SSD volume0a2f1ba9-0000-0000-0000-100000000000, at least40GBfree. Final backup
must verify every member and whole archive plus the whole existing LGP1/RB1 union.
No SSD/laptop gate during healthy cluster execution. No fallback, overwrite or
automatic transfer retry. Preparation and final archive namespaces are exclusive.
