# CVL-BP1 cluster-only continuation — 17 September 2026

## Explicit operational amendment

The user requested cluster-resident execution and monitoring, external backup
at the end, and explicitly said not to restart training. This supersedes only
the intermediate external-SSD readiness/backup gates in Protocol section 6 and
Resource Plan section 5 and the corresponding original execution approval.
Those original documents, approvals and frozen sources remain unchanged.
This is an operational amendment, not a claim that the original backup schedule
was followed. No scientific endpoint, model, seed, case, worker or budget changes.

The original scientific manifest remains
`70e3838c83561b8b24ea2f2c2f6875c2674d7c9b391e682c1023ba3641238975`;
protocol SHA256 remains
`284b420a0b0bb183689ac217346cc9a1444ba814fc0d3c8cf064952e80ec0f9c`.
The new controller is a separate frozen source overlay, bound to a new explicit
approval record. It calls the unchanged original scientific worker entry point.

## Exact continuation, not restart

150 fixed coordinates completed: breadth 0–141 and precision 0–7. Model fitting
has not started. Jobs 301630 and 301631 completed with exit 0:0, charged 173 and
292 seconds respectively. Their controller then stopped because the laptop
backup companion rejected its native-volume freshness/identity/headroom check.
No live or uncertain job remains. Preserve every old stop, log, approval and
artifact. Preserve both existing external archives; do not overwrite them.

The new authorization reconciles these scheduler rows and authenticates the
previous ledgers, approval, output seals and technical-only identity projections.
It binds all 151 previous allocation attempts (150 successful plus the original
63-second cancellation) and **32,469 GPU allocation seconds**. No earlier charge
is dropped. No completed task, candidate bank or training fit is restarted.

Continue exactly at `grid()[150:]`: **300 previously unsubmitted tasks**,
starting at breadth-142. This comprises 50 breadth +184 precision GPU collection
jobs, the single original CPU fit of all 18 models, 64 common evaluation GPU
jobs, and one CPU analysis. All 450 successful coordinates and 451 total attempts
remain required at completion. No retry or replacement is authorized.

Prior charges plus maximum remaining reservations: **249,669 GPU seconds** and
7,200 CPU allocation-wall seconds. Original 86 GPU-hour, two 4-CPU allocation-hour,
10GB remote, 500MB/job and 50MB source/control caps remain enforced. One A6000
study job at a time. No extra tranche, learning study or GPU preflight is added.

## Cluster-resident lifecycle

The controller is a detached process on Prometheus with cluster-side logs and
an exclusive claim. It polls Slurm for its exact active job, enforces budgets
and output caps, authenticates each terminal output, and submits the next fixed
task. It never calls a laptop helper, checks an SSD lease or waits for a laptop
backup acknowledgement. Loss of the local connection does not stop execution.
A cluster-host/controller failure still stops; there is no automatic restart.

Before fitting, verify all 384 training output seals and identities. Before
evaluation, require the unchanged `check_frozen` gate for all 18 models and
preprocessing, then seal-record the fit stage. Before analysis, verify all 64
evaluation outputs. Write explicit `CLUSTER-STAGE-{train,models,evaluation}.json`
records marked **not_a_backup=true**. These are authentication records, not extra
copies and not replacements for the scientific model freeze.

No partial scientific outputs are exposed to the operator. The same accepted
technical-only reader is used by dispatch; model fitting and analysis consume
only their authorized data at the original ordered stages. Reserved CVL
closed-loop 32 and all 1600–5999 payloads remain unopened.

## Completion and deferred durability

After analysis, seal terminal accounting and historical/current control records.
Create `BACKUP-REQUEST-cluster-final.json` covering every sealed root not already
covered by the two existing verified external archives. Create
`CLUSTER-COMPUTE-COMPLETE.json` with external_backup_verified=false. Do **not**
create `DISPATCH-FINAL.json` or claim a verified external backup at that point.

Final handoff still requires the accepted archive verifier and actual transfer
to the designated THESIS_SSD with 40GB free; no laptop-drive fallback. Verify
union coverage of the two old archives and final incremental archive, and retain
technical root logs/control evidence in the final preservation package. Report
transfer time/bytes separately. SSD absence at the end delays backup/handoff,
not cluster computation. The user accepted the corresponding exposure to loss
of cluster-resident, not-yet-externally-backed new artifacts. A checksum is not
an independent disaster-recovery copy.

New claim/ledger/stop names start `CLUSTER-CONTINUE-`; every old stop is historical.
On any new execution fault preserve outputs/accounting, stop without retry and
report the exact fault. Do not hide scientific underperformance or select a
favorable model. Preserve continuation baseline, historical decisions and E12 drafts.

## Verification

Focused synthetic tests simulate the whole 300-task remainder without real
physics, model fitting, labels or Slurm submission. They test no completed-task
retry, exclusive launch, exact budget/case accounting, original worker command,
training/model/evaluation ordering, model-freeze rejection, job-failure stop,
and honest distinction between compute completion and verified external backup.
Initial test fixtures lacked the already-completed training roots; the retained
stage guard rejected them. The fixture was corrected, not the guard.
The host-boundary tests install a process-wide prohibition on numerical imports;
they must run in an isolated process, not in the numerical regression suite.
An initial combined invocation correctly rejected those imports. Re-running in
the documented isolated process changes no implementation or test expectations.
