# Included real-runtime tranche passed

Observed directly on Prometheus at Unix **1789901260.674325**. The four jobs are
included main work, not pilots or extra/repeated episodes. No scientific success
rates, actions/states, REPORT payloads or partial effects were read. The frozen
host-safe task reader authenticated all adjacent seals and technical projections.

| Slurm job | Source / seed | Terminal | Allocation seconds | Complete worker bytes | Worker wall seconds |
|---|---|---|---:|---:|---:|
| 302573 | 74 / 8301 | COMPLETED 0:0 | 72 | 1,490,469 | 65.110041 |
| 302574 | 74 / 8302 | COMPLETED 0:0 | 55 | 1,005,196 | 48.004476 |
| 302575 | 74 / 8303 | COMPLETED 0:0 | 80 | 1,810,300 | 73.225334 |
| 302576 | 1592 / 8301 | COMPLETED 0:0 | 73 | 1,602,423 | 66.427165 |

All four sealed records report eight completed episodes each, all eight native
endpoint checks passed, common initial proposal-bank checks passed, fresh episode
ownership and unchanged model tensors. Their source and approval identities match
the immutable v6 launch. Full technical records, seals and timestamps are retained
in TECHNICAL-TRANCHE-OBSERVATION.json. Seals authenticate the full worker files;
only the technical projection is displayed/read here.

Charged GPU total at this checkpoint: **280 seconds**, four successful attempts,
no failures or retries; CPU analysis has not started. Each job stays within its
300-second allocation, 240-second worker soft limit and 5,000,000-byte cap.
Python peak RSS across these workers is at most **1,629,302,784 bytes**; Torch peak
allocated GPU bytes **294,831,104**. These counters are not whole process-tree RSS,
CUDA-context memory or total reserved GPU memory. Setup and process CPU times are
recorded separately in the technical projection. Slurm top-level TotalCPU was
00:00:00 in the routine observation; do not treat that as zero worker CPU work.

Controller gate `TECHNICAL-TRANCHE-PASSED.json` was written at Unix
**1789901237.0791023**, SHA256
`5e5ce13f7dbccdc8f5b3b52603597c50525c7133c83268b800bdb185ce78acbc`.
It explicitly marks `scientific_selection=false`. The fifth job, **302577**,
`evaluation-8302-1592`, was submitted at **1789901237.101551**, after this gate.
The controller continued automatically as already approved; no new approval,
source modification, resumption or duplicate launch was used.

Exact controller PID438664/start_ticks865775824 still matched, stderr remained
zero bytes, STOP and COMPUTE-COMPLETE were absent. At observation, inclusive
remote occupancy **3,629,471,328 bytes** included **3,619,945,254 historical bytes**,
**3,617,686 new source/control bytes**, and **5,908,388 worker bytes**. Subsequent
live work naturally changes these counts. Full remaining GPU reservation at the
four-job boundary is 280 + 1,532 x 300 = **459,880 seconds**, below the unchanged
460,800-second cap; the CPU reservation remains 7,200 seconds.

This establishes technical acceptance of these included jobs, not scientific
efficacy or a guarantee that every later job meets throughput limits. The fixed
grid, all finite caps, fail-stop/no-retry rules and final preservation barrier
remain unchanged. No inference about outcomes or revised completion estimate is
made from early timings. The existing two-hour monitor was updated in place
through the scheduled-task tool and its saved prompt/status/schedule read back.
