# Proposed finite research envelope (not spending authority)

Exact arithmetic and authenticated exposed inputs are in `PLANNING-EVIDENCE.json` and `BINDINGS.json`.

| Quantity | Fixed count / bound |
|---|---:|
| Parent sources | 320/task; 960 total |
| Source/block GPU workers | 960/task; 2,880 total |
| Closed-loop episodes | 23,040 |
| CPU preflight + CPU analysis | 2 |
| Scheduled unique successful tasks if no fault | 2,882 |
| Included technical tranche | 9 workers / 72 episodes (already included) |
| Delivered physical controller actions | 1,152,000 maximum |
| Planning decisions | 46,080 maximum |
| Scored populations / world-rollout API calls | 1,336,320 maximum |
| Candidate sequences | 400,896,000 maximum |
| Predicted grouped transitions | 2,004,480,000 maximum |
| Learned checker invocations | 1,002,240 maximum |
| Learned checker transition tuples | 1,503,360,000 maximum |

Each world rollout contains the declared five grouped transitions; internal neural-module operations are not mislabeled as one physical simulation step or one neural forward. Each learned checker evaluates 1,500 transition tuples/population without new chunking. Existing model encode/rollout internals are unchanged. Native physics internal integration substeps and construction/reset work are measured by the interface, not falsely counted as only 1,152,000 raw integration ticks. No inference, fitting or physics is performed in preparation.

GPU workers: serial one exact RTX 6000 Ada on gpu09, 4 CPUs / 8GiB RAM, Slurm **00:05:00**, 240s work deadline +60s preservation, no requeue. Full-grid allocation ceiling is exactly 2,880 x300 = **864,000 GPU allocation-seconds / 240 hours**, including every attempt. No spare attempt is silently granted. Before each dispatch actual charges plus the worst-case entire remaining workload must fit. Technical failure/ambiguous submission stops for reconciliation; poor outcomes or throughput do not permit changes.

CPU preflight and analysis: each 4 CPUs /8GiB / **02:00:00**, no GPU, 7,140s work +60s preservation. Aggregate **14,400 CPU-stage allocation-wall seconds /4 hours**, not CPU-core seconds. Preflight hashes whole datasets, all reused checkpoints and the exact container without decoding evaluation payloads. Worker dataset size/device/inode/mtime/ctime must stay bound before/after its allowlisted two-frame read; final analysis rehashes each dataset. Archives use a separate bounded 7,200s host operation; native transfer has a 7,200s wall deadline. Lost network access is not research failure and does not permit recomputation.

## Historical scenario, not demonstrated future throughput

The three authenticated old episode-timing summaries used one warm-up plus five measured episodes. The measured per-arm seconds (DTV column is the **old three-noise proxy**, not a measurement of new single-noise closed-loop cost) are:

| Task | Old DTV proxy | ACID | Older forward proxy | Plain |
|---|---:|---:|---:|---:|
| PushT | 6.432349 | 6.397940 | 6.263914 | 6.172595 |
| Reacher | 6.444074 | 6.428438 | 6.274270 | 6.152149 |
| Cube | 6.874137 | 6.865300 | 6.735570 | 6.596097 |

These are historical short-horizon episode timings, not timings of the prospective fresh/early-terminating interface. The old forward weight differs from the exact profiled .005 comparator. Treat DTV/forward numbers only as explicit planning proxies. Assign both budgets the historical 30-population proxy rather than assert that 28 is exactly equally fast. Add an **assumed** 15s shared authentication/model setup per worker (historical EFF0 authentication/setup observations motivate its scale but do not establish new HDF5 or physics setup cost). World/environment construction could exceed this allowance.

| Explicit assumed policy-work slowdown | GPU allocation proxy, setup included |
|---|---:|
| Direct historical scenario, 1x | 53.4063h |
| 2x | 94.8126h |
| 3x | 136.2189h |
| Full declared worker ceiling | 240h |

Queue/controller overhead, CPU hashing/analysis/archive/transfer and unmeasured interface/setup differences add wall time. These scenarios are not guarantees. No saved-input solver timing is multiplied by a guessed fixed decision count and called measured episode throughput; no smaller timeout, rebatching or concurrency increase is selected for an attractive forecast.

## Complete storage reservation

Per GPU worker **1,000,000 bytes includes all eight reports, raw partial/complete trace/timing journals, allowlisted input NPZ, worker metadata, supervisor/child/final seals and failure evidence**. Logs reserve 100,000 bytes/worker. Preflight reserves 1MB+100k logs; analysis 40MB+100k logs, including all 23,040 episode summaries and all worker setup/authentication records; source including manifest 20MB; control/receipts 100MB. Reused 27 scorers plus three world checkpoints total **428,451,336 bytes**, authenticated from retained byte records and included in the final new-study archive.

Worst-case live reserved bytes = **3,757,651,336**. Enforce **4GB live**, **4.2GB archive**, **13GB inclusive** (live/source/retained history plus host archive plus SSD copy). At most approximately 60,000 archive members with a conservative 2KiB/member overhead fits the 4.2GB archive envelope; no hidden logs/partials or deleted evidence. Request/inventory/ACK metadata has separate control slack. Retained failures count and may block continuation; no cap reset is allowed. The full-grid artificial report footprint is explicitly tested, not extrapolated from a tiny analysis fixture.

Designated final SSD root is `D:/THESIS-BACKUPS/dtv-success-cost-20261001`, THESIS_SSD volume `0a2f1ba9-0000-0000-0000-100000000000`, at least 40GB free. Whole archive and every member must verify before ACK. Do not rearchive/retransfer historical studies or use laptop/fallback disks.

Preparation is separately limited to 14,400 cumulative local scripted wall seconds, four threads,8GiB,1GB new artifacts. Artificial failures are preserved in exclusive test receipts; metadata transport faults and a conservative auxiliary-script reserve are charged. Only the new small immutable review package is backed up now. No scheduled monitor is created.
