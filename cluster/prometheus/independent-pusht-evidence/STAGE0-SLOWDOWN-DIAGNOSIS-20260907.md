# First-stage slowdown: scheduler-only diagnosis

Observed 2026-09-06T21:19:55Z (7 September, 00:19 Cyprus); timing aggregation followed within one minute.
No per-episode outcomes, intermediate success summaries or planner metrics were opened.
Sources: live sacct/squeue/scontrol; frozen registry construction and runtime at 4a608e5.

## Measured completed-shard elapsed times

Each shard contains 64 independent references, both horizons, and one seed block (128 logical episodes).
These are scheduler execution times, excluding queue wait but including setup, planning, physics, early termination and output I/O.

| Arm | Stage-0 task indices | Completed shards | Median minutes | Mean minutes | Observed min-max minutes |
|---|---|---:|---:|---:|---:|
| VAD continuation | 0-74 | 75 | 5.500 | 5.495 | 5.267-5.767 |
| Greedy VAD-300 | 75-149 | 75 | 3.967 | 3.959 | 3.783-4.200 |
| Gaussian continuation | 150-224 | 75 | 4.033 | 4.044 | 3.900-4.217 |
| Greedy VAD-576 | 225-299 | 75 | 3.967 | 3.962 | 3.700-4.200 |
| GMM continuation | 300-374 | 75 | 4.000 | 4.006 | 3.783-4.150 |
| Full released SAGE | 375-449 | 28 | 31.367 | 31.297 | 29.483-32.900 |

All 375 E18-family shards completed. SAGE has 28/75 completed, two running, and 45 pending Resources.
The whole stage has 403/450 completed; no failed scheduler state appeared in the queried array.
The active jobs are task403 and task404, each requesting one GPU, four CPUs and24GB RAM.
The array throttle remains4. Node gpu09 reports four GPUs configured and all four allocated; this array occupies two.
The queried active task has Restarts=0 and no suspension recorded. Neither it nor the completed SAGE tasks has timed out.

## Interpretation

The registry groups methods rather than interleaving them: the five E18 arms come first, followed by SAGE.
The timing discontinuity occurs exactly at task375, the first SAGE shard.
SAGE's observed median shard time is about5.7 times VAD-continuation and about7.8 times the four-minute controls.
Native full SAGE is configured with300 candidates,30 CEM rounds and30 elites per planning call.
The substantial iterative workload is consistent with its longer observed job durations; this is not a diagnosed physics, disk or SSH slowdown.
Two workers completing roughly31-minute shards imply about3.8 shard completions per hour while both remain allocated, matching recent four-shard progress updates.
A shard-count percentage is not a remaining-time percentage because the last75 shards are substantially more expensive.
Whole-shard time is not an isolated algorithmic speed benchmark: episode termination and startup/I/O are included, and only28 SAGE shards were complete.
The matched final timing and efficacy claims remain subject to the registered complete-grid analysis.
No estimate of future completion time is made. No allocation, scheduler priority, method, candidate count, CEM rounds or registered scientific rule was changed.
The local WSL/backup incident affected access and archival; the inspected cluster jobs continued on gpu09.

## Diagnostic execution notes

An initial large interactive Python diagnostic was rejected as safety-indeterminate and did not run.
Permitted narrower read-only Slurm commands then supplied scheduler information; a local PowerShell aggregation computed the table above.
GitHub source inspection confirmed the registry's method order and SAGE configuration.
The table uses all completed shards per arm in the captured accounting response, not favorable selected jobs.
No new Slurm task, model call, success analysis or persistent monitoring process was started.
