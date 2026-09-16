# CVL-BP1 second recovery launch — 17 September 2026 local

**Status at the launch check: running, not a completed study.** Job **301630**
was `RUNNING`, scheduler exit field `0:0`, at 95 allocation seconds. A running
job's exit field is not a claim of successful completion. It is the first
previously unsubmitted coordinate, `breadth-140`, source 463, H75, with the
unchanged 600-second allocation limit. Its dispatch timestamp is
`1789596372.3643637` (16 September, 22:06:12 UTC; 17 September, 01:06:12 Nicosia).
No completed case was rerun and no partial scientific outcome was inspected.

## Authority and publication

The user answered **yes** to the specific request to repair the infrastructure
check and resume only the **302 unsubmitted tasks**, reusing all148 completed
outputs without changing science or budgets. The
[second recovery contract](RECOVERY2-20260917.md) records exact scope, native
volume identity/freshness checks, source authentication, no-retry rules and
backup ordering. The [previous stop](RECOVERY-STOP-20260916.md) is unchanged.

Implementation commit **`ae4ea049f308e56ee2f23ffc02809942b07666c7`** was pushed to
`candidate-value-breadth-precision-preparation-20260915`, and the remote branch
hash matched before launch. This is a separately frozen host-infrastructure
overlay; original scientific workers and both historical host snapshots remain
unchanged. The native helper is launched hidden without a permissions override.

| Identity | SHA-256 |
| --- | --- |
| Original scientific source manifest (81 members) | `70e3838c83561b8b24ea2f2c2f6875c2674d7c9b391e682c1023ba3641238975` |
| Unchanged scientific protocol | `284b420a0b0bb183689ac217346cc9a1444ba814fc0d3c8cf064952e80ec0f9c` |
| Unchanged source-role manifest | `ae77734061becc33ac37d9f094c918c1c77a844da7d3d12af15471a3d2eb107f` |
| Original execution approval | `e7f6d1e67b9ccc0babfb7b613806dc3826fc9d9dc0225c93fab7b54c424d9bc5` |
| Second host overlay manifest (8 members) | `e8f1e44b90e5370b1f90a82196892c51304be54da0f2d73e60b943a97a61ef5c` |
| Second recovery approval | `cb58d691f4890da5de9037123303d5891e50ab2745f675a0621b656fbec0a7e7` |
| Accepted prior terminal accounting | `2b0df6c05f7acf0ce1a629a8d428abbcf15b59d95614fe9451b003418eec8f53` |

The overlay is
`/lustreFS/data/superworld/ckontzias/thesis/snapshots/cvl-bp1-recovery2-e8f1e44b90e5370b`.
Its exact member hashes were checked on Prometheus and write bits removed
before launch. Original scientific source and the overlay's exact external-copy
closures also passed. All Python checks/launches used `-B`; the immutable
scientific source was not changed to implement or test the host repair.

## Verification before real submission

**56 distinct local tests passed**: 26 original preparation tests, 15 prior
host-recovery tests, 11 new second-recovery tests and four isolated host-boundary
tests. The 11 new tests plus four host-boundary tests also passed on actual
Prometheus Python3.6.8 with numerical imports forbidden. The full simulated
controller submitted exactly302 remaining tasks, preserved old ledgers and
charges, required the unchanged stage/model-freeze/backup order, and stopped
without another submission on a synthetic backup outage or job failure.

One initial new synthetic fixture mistakenly supplied a literal backslash-n
instead of a mount-output newline and was correctly rejected by the mount
guard. The fixture was corrected; the guard was not weakened. No real worker
ran during tests. Native PowerShell parsing and the actual read-only volume
identity/free-space check passed. The runtime native status record matches the
approved volume UniqueId, label, source and approval and is refreshed normally.

Prelaunch authorization checked the original runtime/source, all148 completed
identities through the accepted technical-only reader, both closed ledgers,
terminal accounting, complete backup coverage, no existing later-stage outputs
and the original aggregate reservations. The source/control accounting at that
check was 2,414,702 bytes, below the unchanged50MB reserve. No model or simulator
was run by these host checks.

The companion verified both existing external archives before publishing
readiness. An early read-only readiness check found that verification was still
in progress and prevented process launch; no controller or allocation was
started by that check. The controller was started once after readiness and a
fresh backup lease existed. There was no ambiguous or repeated submission.

## Processes and locations

- Run root:
  `/lustreFS/data/superworld/ckontzias/thesis/experiments/candidate-value-breadth-precision-20260915/run-70e3838c83561b8b`
- New remote controls:
  `/lustreFS/data/superworld/ckontzias/thesis/staging/cvl-bp1-recovery2-20260917`
- Remote controller PID **97218**, launch Unix UTC `1789596342.745771`.
- WSL backup companion PID **1261**, launch Unix UTC `1789596258.7502034`.
- Native Windows volume helper PID **29140**, launch local time
  `2026-09-17T01:03:44.2510254+03:00`.
- Local controls:
  `D:/THESIS-BACKUPS/cvl-bp1-recovery2-20260917/controls`
- Local overlay copy:
  `D:/THESIS-BACKUPS/cvl-bp1-recovery2-20260917/cvl-bp1-recovery2-e8f1e44b90e5370b`
- External study artifacts:
  `D:/THESIS-BACKUPS/candidate-value-breadth-precision-20260915/run-70e3838c83561b8b`

At22:07:32 UTC, the remote backup lease was24.07 seconds old, its recorded
external free space was377,715,621,888 bytes, controller stderr was0 bytes, and
neither a new backup stop nor `RECOVERY2-STOP.json` existed. Native-helper and
WSL-companion stderr were also0 bytes. All three processes were observed alive.
These are launch-time observations, not a claim of indefinite future health.

Both immutable backups remain verified and unchanged:

- `failure-20260916.tar`:312,852,480 bytes,
  SHA256 `5f09feeabd59032c129940c69a6ab5163f1bf4171d52bc37ef96b7fc4f558bba`.
- `recovery-stop-20260916.tar`:154,030,080 bytes,
  SHA256 `b5bbf19cc470ccbf58fad39f350ccfecf38fed2867b7eaf8344d2f8e6cc12d46`.

New train/models/evaluation/terminal backups are incremental, with final
coverage checked as their union with both archives above. No laptop fallback,
archive overwrite, completed-output deletion or historical-record replacement
was performed. Native/WSL liveness and stage backup failure still stop dispatch.

## Accounting and continuing boundary

Initial charged work is **32,004 GPU seconds (8h53m24s)** and zero CPU-stage
seconds, including the earlier63-second cancellation. Reuse148 completed
coordinates; execute only302 unsubmitted ones. Initial actual charges plus all
remaining maximum reservations are250,404 GPU seconds and7,200 CPU allocation-wall
seconds. Caps, case identities, seeds, sampling, streams, models, normalization,
update budgets, analysis and scientific advancement rules are unchanged.

The existing `monitor-cvl-bp1` automation was updated via the supported app
interface and re-enabled, not duplicated. It follows only new recovery records,
distinguishes both historical stops, stays quiet for healthy progress and cannot
launch or repair anything. A new failure requires preservation/accounting/backup
and a scoped handoff. No further replacement or automatic retry is authorized.

Partial outcomes stay sealed until the fixed study and all backups complete.
The reserved closed-loop32, all1600–5999 payloads and E12 drafts remain untouched.
Historical decisions and continuation baseline remain unchanged. This launch
does not establish a new scientific result or authorize any follow-up study.
