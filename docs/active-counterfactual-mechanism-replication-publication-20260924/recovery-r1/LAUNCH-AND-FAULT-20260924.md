# ACVM1 R1 launched; import collision and full-reservation blocker

**Current state: stopped, no live or ambiguous allocations. No fitting update or evaluation has completed.** R1 fixed the missing compute-node Python bootstrap but exposed a separate study-module import-path collision. A further launch cannot satisfy the unchanged aggregate CPU ceiling plus full-future reservation after the newly incurred8 seconds. No further retry, patch to an executed source, timeout reduction or cap increase has been made.

## R1 launch and authority

Source/authority commit `d7c84d2c0da96b05127235367fe76748b62f5fdd` and export/SSD-receipt commit `534ceaaab9688a242317af6718a5b7831fdb9c14` were pushed and exact full remote branch identities verified before staging. Recovery source manifest `2af896606b8d7f9ae7c581e50f1bacde13d2ec7fbdb4194e905d43e9625cf905`; enabled recovery approval `2ed6e058571174301b23d3040a255634b65c5d5ddfe4140bc9892c84aaa5203b`. Original scientific source and worker approval remain unchanged.

R1 stage and launch were each invoked once. Staged approval and source identities matched. Controller PID2804013/start_ticks901721716 launched at Unix1790260328.237092,24September14:32:08 UTC. It submitted replacement304591 / `fit-pair1-joint` at Unix1790260331.520292. The controller later recorded terminal charges and exited through its fail-stop path; exact process identity was absent at reconciliation. Original controller2760213 remains exited and untouched.

New source:
`/lustreFS/data/superworld/ckontzias/thesis/snapshots/active-counterfactual-mechanism-replication-control-r1-2af896606b8d7f9a`

New control:
`/lustreFS/data/superworld/ckontzias/thesis/staging/active-counterfactual-mechanism-replication-control-r1-2af896606b8d7f9a`

Run remains:
`/lustreFS/data/superworld/ckontzias/thesis/experiments/active-counterfactual-mechanism-replication-v1/run-9f91156fd11a5d54`

## Exact new failure

Job304591 used the unchanged CPU resources on nodegpu01: defq/normal,4CPUs/8GiB,120-minute limit, no GPU. It reached the pinned container Python3.11 worker successfully, confirming that the missing host Python3.9 failure was resolved. It then failed `FAILED|1:0`, `ElapsedRaw=8`, with:

```text
ImportError: cannot import name 'finite' from 'tree'
(/lustreFS/data/superworld/ckontzias/thesis/envs/hi-lewm-artifact-py311-cu121-swm006/lib/python3.11/site-packages/tree/__init__.py)
```

The authenticated study `model.py` imports `finite` from study `tree.py`. The inherited runtime adds study dependency directories after site-packages, allowing the unrelated installed `tree` package to win. This is a production import-resolution defect; the local artificial environment did not contain that colliding installed package. The necessary correction is explicit authenticated study-module precedence/origin checks in a new recovery wrapper, without editing the historical model/tree implementation or changing/removing installed dependencies. It should be tested with an artificial colliding package and real import resolution before any further research launch.

The failure happened on `from model import JointModel`, before checkpoint/dataset deserialization or any optimizer update. The only failed-worker artifact is `fit-pair1-joint/FAILURE.json`; no weights, fit trace or scientific result exists. Original reused data/checkpoints remain sealed. No evaluation payload, physics, Le-WM forward or scientific aggregate was opened.

R1 STOP SHA256: `70fe437716a441d34d9845a3af90ad09d7f3de988c4ea105a9e454289ef73eac`. `OBSERVE-02.json` preserves the exact traceback. `FAULT-RECONCILIATION.json` includes independent exact-ID scheduler reconciliation, both original and R1 failure accounting, control records, technical error logs and complete five-root file inventory. Unrelated site balance footers remain on cluster; publication records only their hashes/lengths. The old STOP and all old/new submission/log files are unchanged.

## The exact resource blocker

| Quantity | Allocation-wall seconds |
|---|---:|
| Original failure304589 |0 |
| R1 failure304591 |8 |
| Four remaining CPU fits at7200 each |28,800 |
| Remaining CPU analysis at7200 |7,200 |
| Combined full reservation required before next launch |**36,008** |
| Currently approved aggregate CPU ceiling |**36,000** |

No jobs remain live or ambiguous; independent sacct rows exactly match the two terminal ledger rows. There are2 failed attempts,0 successful tasks and8197 logical tasks still required. The8-second charge is retained at Slurm whole-second resolution. GPU charges remain0 and the full GPU reservation remains2,457,600 seconds.

The user's direct instruction authorizes diagnosed technical repair and launch, but does not explicitly expand the earlier numerical resource ceiling. Therefore, the next launch is blocked by the **8-second full-reservation shortfall**, not by a request for redundant permission to fix an import path. Reducing nominal reservations, dropping a task, shortening timeouts, pretending the failed charge is0, or using expected actual fit speed would violate the frozen contract.

The smallest requested resource change is aggregate CPU-stage ceiling **36,008 allocation-wall seconds**, with derived4CPU reservation144,032 core-seconds. Every per-task limit and all GPU/storage/scientific limits stay unchanged. A subsequent finite package would preserve both failed attempts and explicitly account for one new replacement plus8196 never-submitted tasks:8199 cumulative attempts if successful. This is not permission for an unlimited retry loop.

R1 preparation's12 artificial tests, failed local test history, source/export, SSD backup and delivered authority remain preserved. No R2 source package has been frozen or launched. Old monitors remain paused; all historical studies, protected roles, E12 and AV1's unlaunched status remain unchanged.
