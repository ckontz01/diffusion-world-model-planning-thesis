# CVL-BP1 backup transport stop — 16 September 2026

Status: **stopped; terminal accounting and partial-artifact backup complete;
awaiting scoped recovery approval**. The initial stop observations below are
preserved; the terminal reconciliation follows at the end.
This is an infrastructure failure, not a scientific result. No scientific
outputs were inspected and no retry, recovery implementation or relaunch occurred.

## Observed fault

The external-SSD backup companion (WSL PID17325) exited on an SSH connection
timeout while testing for `BACKUP-REQUEST-train.json`. Its exact traceback ends
in `subprocess.CalledProcessError`, exit255. No archive transfer had begun; the
training-backup request did not exist. The stderr file is 1,602 bytes, with
last-write time **2026-09-16 16:30:47 UTC** and SHA-256
`aa0b534e041b5bd558f76fdabec3c34ee351bcff6be0877292f88030e3ba4338`.

The external volume remained mounted as `THESIS_SSD`, with 378,183,536,640 free
bytes at detection. Subsequent ordinary SSH diagnostics succeeded. The evidence
therefore identifies a failed network connection/probe, not a full disk or an
observed scientific/runtime fault. It does not establish the underlying network
outage's cause or duration.

## Authorized stop and preserved work

The heartbeat's single scheduler query found **102 allocations COMPLETED0:0**,
no failed job, and no active allocation at that snapshot. The still-live serial
controller then submitted **301578**, `breadth-94`, reference607, H75. This race
was identified from its technical dispatch ledger, not by a second scheduler poll.

At **16:56:27 UTC**, the monitor verified the exact controller PID3489337 and
command/run identity, wrote an exclusive stop-request receipt, and sent SIGINT
under the approved infrastructure-failure stop rule. The controller's existing
exception path requested cancellation of its exact active job301578, wrote
`DISPATCH-STOP.json`, and exited. Its recorded `KeyboardInterrupt` and empty
exception message are the deliberate monitor stop, **not the root cause**.
The root cause is recorded in `MONITOR-STOP-REQUEST-20260916.json` and the preserved
backup stderr.

The stopped controller records **21,729 terminal GPU-allocation seconds**,
zero CPU-stage seconds, plus **600 seconds retained as the unresolved active-job
reservation**. The cancelled job's actual terminal state and charge still require
the next permitted scheduler query. Do not replace the reservation with an
assumed elapsed value or claim terminal backup completion yet.

All 102 completed outputs and the interrupted allocation's partial files remain
in the original run directory. The snapshot, contract, models and historical
decisions are unchanged. No fit or new evaluation stage had started. No
scientific output, protected payload or old validation outcome was read.

## Receipts and required next action

The original launch-control directory on external D: preserves the backup stderr
and matching copies of the following stop receipts:

| Receipt | SHA-256 |
|---|---|
| `MONITOR-STOP-REQUEST-20260916.json` | `879ebc5056e49754411368471f403193fe0f333a15f1596ba4c6dce328d5f44b` |
| `DISPATCH-STOP.json` | `a0d9466eb923ec482d1e9583ec44df3eb64507f18d51fe03ec77897c85d51734` |

The original pending instruction was to **only reconcile the stopped run and
preserve it** (now completed below):

1. Use its one scheduler query for all103 exact submitted job IDs, including
   301578. Confirm the controller is absent and every allocation terminal; do
   not restart any process or submit anything.
2. Record actual total allocation charges, retaining the full reservation if
   terminal accounting is still unresolved. Preserve original ledger/stop records.
3. Seal the terminal partial artifacts without decoding scientific payloads and
   back them up using the accepted archive writer/verifier to the existing
   external study namespace. Verify exact archive/seal/member coverage. Do not
   copy a still-changing allocation or overwrite previous archives/receipts.
4. Commit/push the focused terminal-accounting and backup record, then request a
   scoped infrastructure-recovery decision and pause/delete the heartbeat.

No automatic retry, companion/controller restart, replacement source/bank,
budget increase, scientific change or discarded artifact is authorized. This
note does not amend `stop_no_ranking_promise`, promote a model, or report a CVL-BP1
scientific outcome.

## Terminal reconciliation and verified preservation

The next permitted scheduler query covered all **103 exact submitted IDs** and
their accounting steps. All are terminal, with the controller and companion
absent. **102 allocations completed0:0;301578 is CANCELLED by1201 after63s.**
Its allocation-level exit field0:0 does not make a cancelled job successful.
No further cancellation, compute allocation, model execution or retry was needed.

| Accounting | Reconciled value |
|---|---:|
| Completed-allocation GPU seconds |21,729|
| Cancelled-allocation GPU seconds |63|
| Total GPU allocation |**21,792s =6h3m12s**|
| CPU fitting/analysis allocation |0s|
| Original unresolved reservation |600s, now resolved to the actual63s|
| Frozen scientific source, checkpoints or settings changed |None|

The original `DISPATCH-STOP.json` remains untouched; a separate
`TERMINAL-SCHEDULER-ACCOUNTING-20260916.json` records all scheduler rows and the
resolved accounting. Its remote and external-copy SHA-256 is
`7d26dce2044dc9f089b86c804f21237f567dcd5fdbddd0ca32d39ee0a853d952`.

Every original run file was inventoried by path, byte count and SHA-256 without
decoding scientific content: **13,132 files /298,996,848 bytes**. The102 completed
output directories and their original seals are unchanged. A new, separately
named `failure-preservation-20260916` directory holds byte-identical copies of
the remaining logs, temporary files, interrupted `breadth-94` partials, controller
and backup evidence, plus preservation metadata. Its seal establishes preservation
integrity, **not scientific validity of the interrupted output**. Original-file
hashes were checked unchanged after copying. No original file was deleted or
overwritten.

The accepted `candidate_value_backup.once` writer and `verify_archive` reader
archived the102 original sealed directories plus that preservation directory.
They verified exact archive membership and every adjacent-seal/member hash.
The backup and verification took **24.730 wall seconds**, with no Slurm allocation.
The archive is **312,852,480 bytes**, well within the unchanged storage ceiling.
External free space afterward was377,870,684,160 bytes. No laptop-storage fallback
was used; the remote originals and launch-control copy also remain preserved.

Archive:
`D:\THESIS-BACKUPS\candidate-value-breadth-precision-20260915\run-70e3838c83561b8b\failure-20260916.tar`

| Preservation identity | SHA-256 |
|---|---|
| Archive |`5f09feeabd59032c129940c69a6ab5163f1bf4171d52bc37ef96b7fc4f558bba`|
| Backup request |`5a32ad65a667018d2987a74132a41fb56f4de70651525ca7ab546db8aa0cdb7c`|
| Preservation inventory |`53decb75027930501b1aec135e6dbf79c48982075ae4780942173f054901dcf4`|
| Preservation-directory seal |`69ac542110489ccba4d977c5c612773110130137210501984a93d891c947350a`|
| External verification receipt |`e0ad5f3391160c1178238f2f21fcba20fd2d3749785c1abd9648fa8518f4b963`|

The remote `BACKUP-ACK-failure-20260916.json` agrees with the verified external
receipt's exact request/archive hashes and byte count. The control receipt and
accounting copy are preserved on external D:; the large scientific archive is
not placed in Git. All three unrelated E12 drafts remain untracked and untouched.

The heartbeat `monitor-cvl-bp1` is **PAUSED** after this terminal handoff. No
scientific inference, evaluator fitting, common evaluation or outcome-driven
decision was made. The study is incomplete, not a new scientific stop decision.

### Remaining authorization

Recovery has **not** been implemented or launched. A scoped recovery would need
explicit approval to repair backup-liveness handling, preserve/reuse all102
authenticated completed allocations, resume only unfinished fixed coordinates,
and replace the single technically cancelled allocation. That replacement would
be one additional attempted allocation relative to the original450-attempt plan;
the63 spent seconds must remain charged and the original aggregate compute,
storage, data-role and scientific limits must not silently increase. No scientific
result is available to justify changing any case, seed, objective or setting.
