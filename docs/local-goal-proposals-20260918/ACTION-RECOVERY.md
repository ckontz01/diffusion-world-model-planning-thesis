# LGP1 recorded-action guard: diagnosis and one authorized replacement

Authority: the user explicitly instructed "okay investigae, fix it and launch
it again" after the failed cache allocation was reported. This supersedes the
no-retry rule for this one identified failed cache attempt only. It does not
authorize changing cases, targets, models, success criteria or total caps.

## Exact failure and bounded read-only diagnosis

Original job **301977** is terminal FAILED, exit1:0, elapsed46 seconds,4CPUs,
24GiB and one GPU. Slurm TotalCPU38.115s; batch MaxRSS1158112K. The worker
recorded wall38.519001058994036s and process CPU32.053456727000004s. The old
controller is absent. No fit or evaluation was submitted. The failed root is
360083028 bytes, including allocated partial arrays, and remains sealed and
preserved. Partial arrays are not consumed as successful cache data.

Diagnosis read only the selected identifiers and action windows through the
first support failure (selected index154, the155th window), plus the same
15-action window from HDF5. No latent, partial scientific metric, reserved
reference, model inference or simulator was used by this diagnosis.
The first failing tuple is P1_train expert episode12540,t39,delta15. It is
eligible under the frozen registry/exclusions; expert episode IDs are not the
separate collected development-reference namespace.

At original steps51/52, Y actions are float32 **1.413864016532898** and
**1.0367851257324219**. The15x2 HDF5 and Lance action arrays are byte-identical;
this is not rounding, clipping during transport, or a pixel-coordinate mix-up.
HDF5 offset1571608, episode length205; episode/step alignment was verified.
The unchanged window bytes SHA-256 is
`058fb23a28b0525a8de861fdc23e45aba6093d81fbbb3984f416413175ac71ea`.

The current pinned WeakPolicy source clips its actions, but that is not proof
that every command in this already released expert dataset obeys that policy's
bound. The inspected stored commands establish the counterexample directly.
No claim about the original dataset collector's exact history is needed here.

## Correction and unchanged scientific definition

PROTOCOL section5 specifies recorded expert actions as both proposers' targets.
Section4's [-1,1] projection is an online candidate/delivered-action constraint.
The implementation incorrectly imposed that online bound on stored training
commands. Remove only that assertion from `aligned`; retain finite values,
shape, source/step alignment, roles, selection and packing checks. Preserve
all original recorded target bytes: no clipping, filtering, replacement,
normalization change, coordinate conversion or altered target definition.

Online proposal support projection, round-trip boundary treatment, decoder,
driver delivered-action rejection and endpoint checks remain unchanged. Both
families learn from exactly the same recorded targets and fit-only statistics.
Targets outside the execution Box remain an explicit data/modeling limitation;
they are not permission to execute an out-of-bound action.

Synthetic regressions verify positive/negative outside-Box targets are retained
byte-for-byte, nonfinite values still fail, and online support remains bounded.
They also verify prior-charge reservation and failed-artifact storage counting.
The full existing suite, including the host-import and native endpoint tests,
is rerun on checkout and export before launch.

## Exact one-time operational recovery and caps

The new immutable source and output namespace retain the original failed run,
source, controls, ledger and seals. The dispatcher admits exactly that one
prior terminal failure, verifies its sealed identity and fresh Slurm state,
and refuses an active old controller, additional attempts or an existing new
run. No automatic subsequent retry exists.

The original complete new chain reserves336000GPU-seconds. Charge the failed
46seconds and reduce only the replacement cache allocation ceiling from14400
to14340seconds (239minutes). Workload stays80000/8000rows. Total worst-case
reservation is **46+335940=335986seconds**, below the unchanged336000cap.
Worker preservation alarms use the replacement limit. Other limits and all
scientific budgets are unchanged. This explicitly authorizes one extra failed
attempt:203 successful GPU coordinates plus the preserved failure means
204GPU attempts; with oneCPU analysis,205total attempts, not a claim that the
historical203-attempt limit was met. There is still only one active GPU job.

The old partial cache counts toward the same5.9GBworker cap. Old/new source,
control and logs count toward200MB; all retained directories count toward12GB.
Final preservation includes the failed run/source/control and recovery control
as named inventory roots, and checks archive reservation against the combined
bytes. No deletion or laptop fallback is used. Backup remains after computation.

## Preserved failed-attempt identities

- DISPATCH.jsonl: `6e9e963aaec8cbac438f91ba8622198625cc82746c5d18858ef0e07fc36ea326`
- cache/sha256.txt: `24c839df422d27d2830abb42057eef7a1bc973866c063b82292c72119343873d`
- cache/FAILURE.json: `e9b471a1e01aee453b6a76839f1cb66c19b0303da1107c2da27bdf81a5939e4a`
- STOP.json: `c24798d724ff888661bf39bc5c0961ffd316fac94821538d5675f74200c8ebc8`

Old run: `/lustreFS/data/superworld/ckontzias/thesis/experiments/local-goal-proposals-20260918/run-b514472d1d8a7f55`.
No scientific conclusion or performance interpretation follows from this fault.
