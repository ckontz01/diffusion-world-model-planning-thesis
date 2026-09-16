# CVL-BP1 authorized recovery launch — 16 September 2026

**Status at 18:22:56 UTC:** recovery is running, not a completed study.
Replacement allocation **301579** was `RUNNING` at 103 allocation seconds in the
launch check. It is the single authorized replacement of cancelled 301578:
`breadth-94`, reference607, H75. No partial scientific result was opened.

## Authority, unchanged source and published implementation

The user explicitly answered **YES** to repairing backup monitoring, reusing all
102 completed coordinates and resuming the unfinished fixed grid with one
replacement attempt. The [recovery contract](RECOVERY-301578-20260916.md) defines
the exact scope, preserved cost, output relocation and failure behavior.

Implementation was committed and pushed as
`0d372ad61e434a17234f92a1d0b4ce9b005c16e4` on
`candidate-value-breadth-precision-preparation-20260915`; `git ls-remote` matched
the local commit before launch. This changes host infrastructure only.

Scientific snapshot (unchanged):
`/lustreFS/data/superworld/ckontzias/thesis/snapshots/candidate-value-breadth-precision-20260915-70e3838c83561b8b`

| Identity | SHA-256 |
| --- | --- |
| Original source manifest, 81 members | `70e3838c83561b8b24ea2f2c2f6875c2674d7c9b391e682c1023ba3641238975` |
| Original protocol | `284b420a0b0bb183689ac217346cc9a1444ba814fc0d3c8cf064952e80ec0f9c` |
| Original source-role manifest | `ae77734061becc33ac37d9f094c918c1c77a844da7d3d12af15471a3d2eb107f` |
| Original execution approval | `e7f6d1e67b9ccc0babfb7b613806dc3826fc9d9dc0225c93fab7b54c424d9bc5` |
| Host-recovery overlay manifest | `47726fc626f9c7a620a78bd83a880f1e46e80a3a90e213ca4c4a42a03bcf7ec3` |
| One-use recovery approval | `9640ca030809f1bd0d176c6dacd5e4a8d160f08d0198bd158f4cdbd975de3260` |

The separately frozen overlay is
`/lustreFS/data/superworld/ckontzias/thesis/snapshots/cvl-bp1-recovery-301578-47726fc626f9c7a6`.
Its five members and manifest are verified, and write bits were removed before
launch. The worker command still invokes the **original scientific snapshot's**
`run_breadth_precision.sh`, with the original execution approval.

## Verification before submission

The 15 focused new recovery tests passed locally and on Prometheus Python3.6.
The existing 26 preparation tests passed separately. The four host-boundary
tests passed in an isolated interpreter; the on-host isolated host+recovery
suite passed all19 tests with numerical imports forbidden. The full mocked
dispatch submitted exactly348 remaining coordinates, retained all cancelled
charges, required training/model/evaluation backups in order, froze models
before evaluation and stopped on a simulated new failure without retry.

An initial combined local discovery incorrectly mixed the deliberately
numerical-import-forbidding host suite with the numerical synthetic suite;
four assertions failed from that test-process collision. Running the suites in
their intended separate interpreters passed, without changing scientific code
or tests. No real collection/training/evaluation ran during these tests.

The first isolated on-host invocation omitted `-B`, creating eight `.pyc` files
under the original source directory and three under the overlay. The strict
prelaunch source authentication rejected these extra files **before any job was
submitted**. Every manifested source byte was unchanged. The generated caches
were moved, not deleted, to the recovery control directory's
`host-test-bytecode-preservation/`, with original/new paths and hashes recorded.
The exact81-member scientific source closure was restored and verified. All
subsequent preparation/launch commands explicitly use `-B`; frozen scientific
workers already set `PYTHONDONTWRITEBYTECODE=1` and bind source read-only.

Final authorization passed the original runtime/source authentication, all102
completed output seals, exact terminal accounting, the accepted first16 resource
gate and the preserved failure backup. It decoded only permitted technical
metadata, not labels or other scientific outputs.

## Processes, paths and backup

- Run root:
  `/lustreFS/data/superworld/ckontzias/thesis/experiments/candidate-value-breadth-precision-20260915/run-70e3838c83561b8b`
- Recovery controls:
  `/lustreFS/data/superworld/ckontzias/thesis/staging/cvl-bp1-recovery-301578-20260916`
- Remote recovery controller PID **4125577**, started at Unix UTC
  `1789582848.5775642`; first replacement submission at `1789582873.91662`.
- WSL backup companion PID **24288**.
- External source/control copy:
  `D:/THESIS-BACKUPS/cvl-bp1-preparation-oByPHd/recovery-301578-20260916`
- External artifact destination:
  `D:/THESIS-BACKUPS/candidate-value-breadth-precision-20260915/run-70e3838c83561b8b`

The existing failure archive was reverified without extraction or scientific
decoding:312,852,480 bytes, SHA-256
`5f09feeabd59032c129940c69a6ab5163f1bf4171d52bc37ef96b7fc4f558bba`.
No replacement archive or laptop fallback was created. At the launch check,
THESIS_SSD had377,869,963,264 free bytes; the source/approval-bound backup lease
was3.41 seconds old, controller stderr was0 bytes and no recovery-stop record
existed. The original cancelled slot's nine output files and two temporary
files were preserved byte-for-byte under `interrupted-attempt-301578/`, in
addition to their original-path failure-archive copies.

Original dispatch/stop/accounting records remain unchanged. Recovery uses its
separate claim and dispatch ledger. Initial charges remain21,792 GPU seconds,
including cancelled63 seconds, and0 CPU stage seconds. All102 completed outputs
are reused. There are348 remaining fixed coordinates and no extra scientific
cases. Aggregate caps are unchanged; the detailed reservation arithmetic is in
the recovery contract.

## Continued operation and research barrier

The existing `monitor-cvl-bp1` heartbeat was updated and re-enabled; no duplicate
monitor was created. It monitors the recovery ledger, live processes, backup
liveness/receipts and exact scheduler IDs, and stays quiet for unchanged or
non-actionable state. It cannot dispatch, retry or broaden the study.

The monitor distinguishes the preserved historical `DISPATCH-STOP.json` from a
new `RECOVERY-STOP.json`. On a new failure it preserves and reconciles the exact
attempt, then requests scoped direction. The current approval does not grant
another replacement. On completion it requires450 successful coordinates,
451 total attempts including the historical cancellation, all resource charges,
unchanged seals and complete failure/train/models/evaluation/terminal backup
coverage before reading the final aggregate report.

There is no model promotion or efficacy claim. Historical decisions,
continuation baseline, reserved closed-loop32, all1600–5999 payloads and the
three unrelated E12 drafts remain unchanged/unopened as applicable.
