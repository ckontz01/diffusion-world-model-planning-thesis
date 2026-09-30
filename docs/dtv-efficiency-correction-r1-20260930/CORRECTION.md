# Exact narrow correction

Authority: supplied correction attachment SHA-256
`74c5ac1cbe58347cde9ddf74b9bdf1862698c181e1ba2649f3f914df9ebd1d7d`.
It authorizes preparation only; it does not enable the false approval.

The reviewed manifest SHA-256 is
`a9a3b495e479916dfc64279e2c099a76a8817119c53607770b04e22f693796ae`.
The reviewed bindings SHA-256 is
`c8dc6785db94109bf4141e3c31e48e64d2e2b9267f56cacad76fd653a11faed9`.
Every old manifest member is hash-checked before a new export is frozen.

## Changed execution controls

The new command builder generates exactly `--time=00:13:00`, reserves
780 seconds per worker and all nine workers (7,020 seconds). The aggregate
actual GPU-allocation ceiling remains 7,200 seconds, including failures.
720 seconds of work and 60 seconds of preservation replace the inaccurate
historical scheduler contract. Old values in the untouched reviewed record
are historical, not the new executable contract.

The outer worker starts a monotonic clock at module entry, before authority,
source/checkpoint authentication, torch import or model/input loading.
The child inherits this same absolute deadline; it never starts a new clock.
All long operations run under the outer process wait, not solely a between-call
`budget()` check. No deadline wrapper enters `measured()` or the original CEM.

At the deadline the POSIX supervisor signals the owned child process group
with TERM, waits at most 5 seconds, then KILL and waits at most 5 seconds.
It records exit status or an unresolved process identity. Completed records
and equivalence checks are incrementally journalled after their measured
boundaries. The interrupted operation is not reported as a completed timing.
No tensors, predictions or work-in-progress CUDA state are invented/recovered.

This is a bounded signalling/wait path, **not guaranteed cleanup of
uninterruptible kernel, driver, native spawn or filesystem operations**.
The supervisor itself has to write evidence; blocked I/O can prevent that.
The scheduler's nominal 780-second limit is the additional outer guard, not
an assertion that all hardware cleanup completes at precisely that second.
Interpreter startup before the first Python statement is not measured by
the monotonic clock; actual allocation wall time still charges it.
The nominal 60-second allowance includes up to 10 seconds of termination
waits, then at most 50 seconds remain for evidence/sealing under that guard.
No timeout automatically retries, advances a task or expands the ceiling.

After normal completion, `CONTROL-SEAL.json` authenticates profile, original
seal, both journals and both supervisor records. Full output bytes are checked
before profile/seal creation. A fault retains journals and `FAILURE.json`,
plus deadline/supervision evidence when the supervisor can write it.

## Accounting visibility

One successful `sbatch` response binds one exact allocation ID. Every raw
submission/accounting stdout, stderr and return code is retained. Only an
initially empty successful `sacct` response receives a 60-second allowance,
at five-second polls, beginning at the successful submission response.
Command failures/timeouts, conflicting IDs/task names, duplicate/extra rows,
late first visibility, unknown states or absence after prior visibility stop
as unresolved. They are not assumed completed and receive no guessed charge.

Explicit live states stay live; explicit terminal states carry exact elapsed
charges, including failed, cancelled or timed-out allocations. A terminal
fault is charged once before refusal, with its cumulative value propagated
into STOP evidence. A record-cap fault also preserves the triggering raw
response/charge. No second submission, reservation reset or next task follows
an unresolved allocation. Existing run namespaces are rejected, preventing
an implicit restart from repeating successful/live/ambiguous work.

## Unchanged scientific code

The original helpers, `measured()` boundary, entire inference workload body
and utility comparison function are checked against the reviewed source
using exact AST equality (ignoring source locations only). Candidate definitions,
weights/noise, ACID reconstruction, forward/plain controls, checkpoint/input
roles, callable/CEM semantics, precision, synchronization and balanced order
are unchanged. No sigma sweep or workload reduction is introduced.

Only `dtv_efficiency_r1/` and this correction directory are added. The source
diff is generated against the reviewed modules; the additional modules are
included as new files. Exact byte hashes will be fixed by the new manifest
after full tests and preserved by the exclusive small SSD export.
