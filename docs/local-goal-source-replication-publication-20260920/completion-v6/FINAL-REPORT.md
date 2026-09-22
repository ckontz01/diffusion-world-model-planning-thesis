# LGP-RB2 — completed, authenticated and preserved

22 September 2026. All 1,537 unique research jobs completed successfully:
1,536 GPU source/seed jobs containing 12,288 fresh episodes, then one CPU
analysis job. Zero failed research jobs, retries, reused episodes or unresolved
submissions. The SSD preservation gate passed through separately authorized
R1 recovery; the failed first transfer remains recorded and unchanged.

**Main result:** the fixed five-population diffusion advantage did not replicate
on this 512-source development cohort. Diffusion5 achieved 14.3555% native success
and GMM5 15.1042%; the prespecified paired difference was **−0.7487 percentage
points**, 95% whole-source bootstrap interval **[−2.0833, +0.5859]**. This does
not establish diffusion superiority, equality, equivalence or noninferiority.
There is also no evidence here of a family-by-budget interaction. No proposer
is promoted and no historical decision or result is rewritten.

## Fixed question and population

This is outcome-informed, recent-method-role-disjoint **development replication**,
not untouched confirmation or a claim that every frozen component is source-unseen.
From previously exposed reference IDs 0–1599, 320 distinct registered role IDs
were excluded, leaving 1,280 eligible; the frozen hash order allocated 512 and
left 768. No replacement, favorable source/seed selection or old32 pooling.
The source identities are fully listed in the authenticated artifacts below.

Six unchanged final LGP1 proposer models; seed blocks 8301/8302/8303; arms
GMM5, diffusion5, GMM30, diffusion30; horizons 75/150 and physical budgets
150/300 primitive actions; 15-action chunks. Total scored populations include
the initial proposal. Each population has 300 candidates and 30 elites;
unchanged FP32 CEM, support projection and projected final-elite-mean return.
All normalizations, decoder, initializer, local-target generator and LeWM remain
fixed. No fitting, optimizer, training, new learning labels or new algorithm.

Every cell had a fresh World, episode, policy, history, buffers and random
streams. One read-only backend and two seed-specific models were shared per
job. Proposal seeds exclude budget/order; refinement has its separate stream.
Balanced eight-cell rotation placed each cell in each order position 192 times.
The first four jobs' 32 episodes are included, and their technical gate preceded
the fifth and every remaining submission. All 12,288 independent endpoint
checks, unchanged-model checks, common-initial-bank checks and seals passed.

Native success is the unchanged post-action combined agent/block position
norm <20 and reviewed angle difference <pi/9 at the same step; initial t0 is
excluded. No post-terminal work. This report reads the already-sealed completed
aggregate only after complete backup verification; the analyzer was not rerun.

## All four arms

Every arm contains 3,072 episodes: 512 sources × two horizons × three seed blocks.
Counts are descriptive; the **source**, not episode, seed or horizon, is the
independent statistical unit. Each source has equal weight and its six cells
have equal within-source weight. Intervals below are the original frozen
10,000-resample whole-source percentile bootstrap, seed 20260920.

| Arm | Native successes / 3,072 | Rate | 95% source-bootstrap interval |
| --- | ---: | ---: | ---: |
| GMM5 | 464 | 15.1042% | [13.2813%, 16.8945%] |
| Diffusion5 | 441 | 14.3555% | [12.6302%, 16.1784%] |
| GMM30 | 550 | 17.9036% | [16.1784%, 19.6615%] |
| Diffusion30 | 526 | 17.1224% | [15.2669%, 19.0104%] |

| Prespecified contrast | Difference (percentage points) | 95% interval |
| --- | ---: | ---: |
| **Primary: D5 − G5** | **−0.7487** | **[−2.0833, +0.5859]** |
| D30 − G30 | −0.7813 | [−2.3438, +0.7813] |
| Interaction: (D5 − G5) − (D30 − G30) | +0.0326 | [−1.9531, +2.0508] |
| D5 − D30 | −2.7669 | [−4.4596, −1.0409] |
| D5 − G30 | −3.5482 | [−5.2083, −1.8229] |

Secondary intervals are descriptive and not multiplicity-adjusted discoveries.
The two negative cross-budget intervals do not identify a diffusion-specific
budget mechanism. The near-zero estimated interaction does not prove absence
of interaction. No new margin, equivalence test, budget search or favorable
stratum claim is introduced. Historical RB1/LGP1 findings remain historical;
they are not pooled with these 512 sources.

Complete disclosure: [all 512 source effects and all 24 strata](FINAL-SOURCE-EFFECTS.md),
[all 12,288 episode identities, native outcomes and endpoint-check metadata](FINAL-EPISODES.json),
[unrounded fixed aggregate projection](FINAL-AGGREGATE-PROJECTION.json).
No sources or strata are omitted. Protected raw reference/state/action arrays
are not published here.

## Actions, planning and model/scoring work

| Arm | Physical actions delivered | Planning stages / proposal samples | Batched scoring calls | Candidate trajectories | Predicted primitive steps |
| --- | ---: | ---: | ---: | ---: | ---: |
| GMM5 | 650,494 | 43,513 | 217,565 | 65,269,500 | 979,042,500 |
| D5 | 654,936 | 43,806 | 219,030 | 65,709,000 | 985,635,000 |
| GMM30 | 645,464 | 43,194 | 1,295,820 | 388,746,000 | 5,831,190,000 |
| D30 | 646,590 | 43,261 | 1,297,830 | 389,349,000 | 5,840,235,000 |

| Arm | Proposer network forwards | LeWM encoding calls | Local-target generator calls |
| --- | ---: | ---: | ---: |
| GMM5 | 43,513 | 130,539 | 37,837 |
| D5 | 219,030 | 131,418 | 38,079 |
| GMM30 | 43,194 | 129,582 | 37,613 |
| D30 | 216,305 | 129,783 | 37,649 |

The second table is derived from sealed stage counts and the frozen code, not a
GPU-kernel/internal-submodule profiler: one GMM or five diffusion forwards per
proposal sample; three LeWM encodings per stage; generator skipped when the
scheduled local target is the final goal. Scoring calls are budget × stages;
each evaluates 300 candidate trajectories with 15 predicted primitive steps.
These compute counts are not independent observations.

## Timing, allocation and memory

| Arm | Complete episodes total (s) | Planning total (s) | Proposal total (s) | Refinement total (s) | Scoring total (s) | Bank fingerprint total (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GMM5 | 9,997.242 | 7,511.770 | 312.785 | 5,074.877 | 4,232.878 | 6.005 |
| D5 | 11,119.466 | 8,615.209 | 1,355.054 | 5,121.620 | 4,262.240 | 6.241 |
| GMM30 | 33,834.923 | 31,354.471 | 312.499 | 28,923.792 | 25,091.057 | 5.997 |
| D30 | 34,923.248 | 32,436.787 | 1,342.294 | 28,971.925 | 25,124.396 | 6.184 |

Planning seconds per stage, G5/D5/G30/D30 respectively:
0.172633 / 0.196667 / 0.725899 / 0.749793. Proposal seconds per stage:
0.007188 / 0.030933 / 0.007235 / 0.031028. These are observed instrumented
times, not pure model latency or guarantees for another cohort/hardware.

Complete-episode wall includes World construction, initialization/reset,
planning, physical delivery, evidence save/verification and World close.
Shared backend/model setup is separately 14,409.113 seconds over all jobs.
World creation/reset/physical delivery/evidence/close totals for every arm are
preserved in [full accounting](FINAL-ACCOUNTING.json).
Scoring is inside refinement; fingerprint time overlaps planning/refinement.
Do not add these overlapping timers or blindly subtract fingerprints to claim
unmeasured deployment speed. Four arms share an allocation; no arm-level GPU
allocation or worker CPU split is invented.

- GPU allocation: **138,753 seconds = 38.5425 A6000-hours**, below 460,800 seconds
  (128 hours). 1,536 serial allocations, each 4 CPU / 24 GiB, within 300 seconds.
  Longest observed GPU allocation: 106 seconds.
- CPU analysis job 304173: **161 allocation seconds**, 4 CPU / 8 GiB, no GPU,
  below 7,200 seconds. This is allocation wall, not 161 CPU-seconds of work.
- GPU-worker measured process CPU: 122,434.568 seconds; analysis process CPU:
  111.988 seconds; total worker process CPU: **122,546.557 seconds**.
- GPU-worker measured wall: 127,703.469 seconds; analysis wall: 157.049 seconds;
  total 127,860.519 seconds. Worker timers end after report writing but before
  technical/seal writing, so they do not cover the full allocation.
- Detached controller: 167,537.980 elapsed seconds (including waiting/control
  overhead), 2,701.259 process CPU seconds. Queue waiting is excluded from
  charged allocation; controller elapsed is not GPU time.
- Peak worker Python RSS: **1,647,009,792 bytes**; peak Torch allocated GPU:
  **294,831,104 bytes**. RSS is one Python process, not the complete simulator
  child-process tree. Torch excludes reserved allocator memory, CUDA context,
  driver and other processes. Top-level Slurm TotalCPU=0 is not actual worker CPU.

The historical 68–85 hour preparation scenarios were not runtime guarantees;
the observed allocation is reported without retroactively changing those plans.
Success/GPU-hour is not substituted for the fixed native-success endpoint.

## Authentication, storage and preservation

Executed source manifest:
`a8fa92772272e11a279aac6c13699fc5b6da9f8160bd3264bab15e3f6bf68cec`.
Enabled approval:
`013dfa0c2498a627e84057d7f53a758871cae010c8f51a0db4553717a697e49b`.
Original six-model freeze:
`a8a5a0ff456cd870e540f838d2c8b62d00b542be6d7a2da53b377fbd91cbc305`.
Completed aggregate REPORT.json SHA256:
`0236f5fdbd274b61900429922fbe578d5d418aa8599004b7e5041842f915eeae`.
Analysis seal: `b48bb493f702f94928206ef41d4a238c1fa648abbdc5cf625790e48a013fc5ca`.
COMPUTE-COMPLETE: `22768015b5421f7a050df3b3e3bfbf83e1fe2531a3681ce63d0664a49db2df0f`.

[Authentication](FINAL-AUTHENTICATION.json) and [publication checks](FINAL-PUBLICATION-CHECKS.json)
bind exact accessed archive members, source/approval/model identities and included
tranche gate. All unique jobs, exact episode grid, source means, 24 strata,
endpoint metadata and scoring arithmetic were checked read-only. Original
bootstrap estimates/intervals were reused unchanged, not recomputed or selected.

Completed worker output occupancy: 2,805,809,087 bytes. Compute-complete snapshot
source/control occupancy: 10,693,778; historical occupancy: 3,619,945,254;
inclusive snapshot: 6,436,448,119 bytes. These are time-specific accounting
snapshots, not the later archive-inclusive count. R1 observed **9,320,146,032
inclusive remote bytes**, below 24 GB, with zero new remote recovery files.
All successful artifacts, preparation v1–v6, original failure and old studies
remain preserved; nothing was deleted to fit.

The cluster archive was created **once**, 2,875,822,080 bytes / 32,393 members,
SHA256 `fa17faef59d068b6a71d0ca40a3178b7f1be0a4e78688282a1bd846eb8a8b2aa`.
Archive wall/process CPU: 78.858 / 41.206 seconds. The first SSD SSH stream
timed out; its 1,202,438,144-byte partial and failure receipt remain unchanged.
That transfer failed; it was not disguised as success or restarted wholesale.

R1 authenticated/copied the retained prefix into a separate new directory and
transferred only the missing 1,673,383,936 bytes in 25 serial ranges. All ranges
succeeded on first attempt; 3 metadata SSH invocations, zero retries/failures/
unresolved processes. Session wall 347.703 seconds; Windows worker process CPU
through sealing 127.5 seconds; remote helper CPU 12.313 seconds. Final verification
before receipt consumed 50.640 seconds of wall. Network-wire overhead was not
measured; archive payload is not a wire-byte claim.

Successful SSD archive:
`D:/THESIS-BACKUPS/local-goal-source-replication-20260920/run-a8fa92772272e11a-recovery-r1/final.tar`.
Whole-file SHA and every member passed the original request, as did the complete
historical LGP1/RB1 union. New recovery-directory footprint, including retained
chunks/logs: 4,560,503,669 bytes, below 8 GB. Final designated THESIS_SSD free:
323,615,612,928 bytes; exact required volume identity and ≥40 GB passed again.

[R1 receipt and exact location mapping](../preservation-recovery-r1/LOCATION-AND-RECEIPT.md)
were committed/pushed/remote-verified at
`28cbcf18ec16bcb496132c7c9bd0204a7cf2eca9` before opening the aggregate.
The original request destination is not rewritten. Recovery receipt and
session-complete bind the new destination separately. Recovery did not change
research, rerun the analyzer or regenerate the archive.

## Limits and next handoff

This tests one development-selected operating point on one exposed benchmark
population. It is not untouched confirmation, broad-task evidence, a SAGE
comparison, an equivalence/noninferiority result or a model-promotion decision.
The six trained models and three seed blocks are fixed, not 12,288 independent
model replications. No historical32 pooling, source/seed pseudoreplication,
favorable subgroup selection or post-result tuning.

Reserved CVL closed-loop, BP1 evaluation, reference IDs 1600–5999 and earlier
protected D5/D3/D4/P3/P4/C1/I1 payload boundaries remain closed. Continuation,
CVL stop/no-ranking promise, original-relative history, checkpoints and all
three E12 drafts remain unchanged. Return this complete result to the selected
GPT-6 Pro conversation for interpretation and one concrete bounded next
instruction under the user's standing delegation. R1 itself authorizes no
further experiment or recovery session.
