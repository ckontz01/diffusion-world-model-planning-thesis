# CVL-BP1 backup transport stop — 16 September 2026

Status: **stopped; terminal accounting and partial-artifact backup pending**.
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

The next heartbeat must **only reconcile the stopped run and preserve it**:

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
