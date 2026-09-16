# CVL-BP1 cluster-only continuation launch

The user explicitly authorized cluster-resident continuation and external backup
at the end, without restarting training or completed work. The operational
amendment is in [CLUSTER-CONTINUATION-20260917.md](CLUSTER-CONTINUATION-20260917.md).
The scientific source, original protocol, roles and workers remain unchanged.
This is not a completed study or a verified final backup.

## Publication and authentication

Implementation commit `bb3303f8acb0062268a718a308ea09dfaaef5b5f` was pushed to
`candidate-value-breadth-precision-preparation-20260915`; the remote hash matched
before starting the controller. The separate six-member source overlay is:

`/lustreFS/data/superworld/ckontzias/thesis/snapshots/cvl-bp1-cluster-continue-6d89f08fc8c6939b`

Manifest SHA256:
`6d89f08fc8c6939bf3020f7ad05c8fd813d2b011bccaa1d1c186fcc304dc5261`.
All members and the exact closure were verified on Prometheus; write bits were
removed from this new overlay only. Existing snapshots/artifacts were not edited.

New approval:
`/lustreFS/data/superworld/ckontzias/thesis/staging/cvl-bp1-cluster-continue-20260917/CLUSTER-CONTINUE-APPROVAL.json`

Approval SHA256:
`21985cc7994ce24fab4b08e6ff9ee46c36281b686145594701f8f679cb1b4b80`.
It records the explicit backup-timing amendment, exact source/role/protocol
identities, all 151 prior attempts, reconciled scheduler rows, 150 completed
coordinates/seals and all 300 remaining coordinates. Prior GPU charge is32,469s.
Source/control accounting at preparation was2,658,380bytes, below50MB.

## Tests

63 distinct local tests passed:52 existing preparation/recovery tests, four
isolated standard-library host-boundary tests, and seven new continuation tests.
All seven new tests plus the four host-boundary tests passed on actual Prometheus
Python3.6.8 with numerical imports prohibited. Tests were synthetic; no real
label collection, evaluator fitting or model/physics execution occurred in them.
The documented initial fixture/isolation invocation errors changed neither the
scientific code nor test expectations. Python checks used `-B`.

## Detached controller

Controller PID **123115**, start Unix UTC **1789598723.195947**, was launched once
with `start_new_session=True`, stdin disconnected, and stdout/stderr on Prometheus.
Its executable is `/usr/bin/python3 -B` and entry point is the new frozen
`breadth_precision_cluster_continue.py dispatch`. A separate exclusive launch
claim prevents an ambiguous second launch. No local companion is required.

Controls/logs and `CONTROLLER-PROCESS.json`:
`/lustreFS/data/superworld/ckontzias/thesis/staging/cvl-bp1-cluster-continue-20260917`

Run root (unchanged):
`/lustreFS/data/superworld/ckontzias/thesis/experiments/candidate-value-breadth-precision-20260915/run-70e3838c83561b8b`

At Unix UTC1789598751.144833 the detached process was alive and stderr was0bytes;
initial source authentication was still in progress before its first submission.
The first authorized coordinate is **breadth-142, reference1559, H75**. All150
completed outputs remain reused. Evaluator fitting had not begun before this
continuation; there is no trained model restart or replacement fit.

After authentication, the controller submitted **job301632** for breadth-142 at
Unix UTC1789598752.5662887. A direct Slurm check reported `RUNNING`,91 elapsed
allocation seconds, exit field0:0 (not a completion claim). Controller stderr
remained0bytes and no new stop existed. This confirms actual forward continuation,
not merely a prepared command or a laptop backup process.

## Monitoring and end backup

The existing `monitor-cvl-bp1` was updated and re-enabled through the supported
automation interface, not duplicated. It checks the new cluster control records
and Slurm directly, stays quiet for ordinary progress, and cannot submit/retry
or restart jobs. Missing obsolete backup leases are not new faults. Local app
or network unavailability can delay notifications, but does not stop the detached
cluster controller. Cluster-controller failures still stop without auto-restart.

New artifacts remain on Prometheus until completion. The final backup request
uses the accepted archive machinery and preserves the two old external archives.
`CLUSTER-COMPUTE-COMPLETE.json` is deliberately distinct from final externally
verified completion. No `DISPATCH-FINAL.json` is emitted by this controller.
The final SSD backup and checksum/coverage verification remain pending.

All original scientific/model-freeze gates, budgets, failure charges and protected
data boundaries remain intact. The three unrelated E12 drafts are untouched.
