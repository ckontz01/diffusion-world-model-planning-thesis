# Extension launch chronology

The user approved the exact additional28 design. Scientific runner source differs
from the pilot only in the fixed allowlist and corresponding SHA-order length.
No completed pilot source/output is edited or reused as a new execution.

Initial freezebcf573a passed99 local tests, shell syntax and all56 manifest entries:
snapshot `/lustreFS/data/superworld/ckontzias/thesis/snapshots/diffusion-bottleneck-extension-bcf573a`;
manifest `36bd7b43ff3f33a5f103c3564750204b03f86d1506056761429b85f0586158ac`;
contract `7ad78113edc32053890bf2ec22dc4f2127aa79cd85bb21c9b893fd17ff74123a`.

The lightweight dispatcher then failed before its first subprocess was created:
login-node Python3.6 rejects subprocess.check_output(text=True). No sbatch command
or model execution occurred. The empty run-root DISPATCH.jsonl and frozen source
remain preserved. This is execution compatibility, not a scientific failure.
The sole correction uses universal_newlines=True (equivalent text decoding,
supported by Python3.6), with a regression that checks the exact call signature.
Scientific code, contract, data, seeds, models, limits and analysis are unchanged.
A separately frozen corrected source/run root is required; no in-place amendment.

## Corrected launch

Source54e3acf passed100 local tests and shell syntax. All57 frozen manifest entries
verified. Contract SHA unchanged. Snapshot:
`/lustreFS/data/superworld/ckontzias/thesis/snapshots/diffusion-bottleneck-extension-54e3acf`.
Manifest `94a57124ca1b5dbf311023869d618377de978856cc3ef4b25de007c16b6a9565`;
tar `bf69afa64526c51fcd320eace7659f6634123b21664c327ea980f8fe398a92f6`.
Run root:
`/lustreFS/data/superworld/ckontzias/thesis/experiments/diffusion-bottleneck/extension-20260914-54e3acf`.

Dispatcher submitted301003 for index8/ref567/repeat0 at2026-09-14T09:27:03Z.
First observed scheduler state PENDING(Resources), not running. Subsequent exact
job IDs and terminal allocation sizes are in append-only DISPATCH.jsonl. No
second job is submitted until a successful terminal state. No new scientific
artifact was opened at launch. Unrelated E14 pending jobs are unchanged.

Combined report runner is frozen in the same snapshot. New backup verification
is byte-only and will run after combined acceptance, alongside rechecking the
eight pilot copies rather than rewriting them. Completion/results remain pending.

Local thread heartbeat `complete-additional-28-bottleneck-diagnostic` is ACTIVE
every10minutes, created through the app. It inspects only execution metadata until
the completion barrier, then continues frozen verification, backup and reporting.
It stays quiet for unchanged/non-actionable state and is removed after final
completion. Local follow-up requires the computer and app to remain running.

## Exact failed job301003 — packaging only

Job301003 FAILED1:0 after11 allocated seconds. Dispatcher stopped; no later job
was submitted. The exact failed job was reported before its stderr was read.
The test loader could not import `archive_diffusion_bottleneck_backup.py`, omitted
by the freeze file-selection glob. That helper also imports the omitted
`audit_diffusion_bottleneck_preservation.py`. Both already exist unchanged in Git.
The run root contains only dispatcher metadata, test stdout/stderr and tmp-8;
there is no ref567 output directory. Because tests precede the runner command,
no model/simulator execution occurred. Stderr12129bytes, SHA256
`f94ebb56b34a367a2acb1134fb59c02cf9774dfd788f6fecbecc08e9fbb2413d`.
Test discovery reported98 tests including one failed import, not a100-test pass.

Ordinary package repair includes both unchanged dependencies in a separately
frozen package and tests the extracted package before GPU launch. The dispatcher
charges the prior11seconds against the same7200-second ceiling; it does not
reset spent cost. No scientific runner, protocol, tolerance or analysis change.
All prior source/output directories are preserved. No failed scientific result
is being retried; this is the first actual execution of the same frozen case.

## Repackaged source265b618 and CPU preflight

Source265b618 includes the prior11-second budget charge and regression. The
package now includes both unchanged helper dependencies. All101 tests passed
from the extracted archive before transfer; all60 remote manifest entries
verified. The scientific runner and execution contract are unchanged.

Snapshot:
`/lustreFS/data/superworld/ckontzias/thesis/snapshots/diffusion-bottleneck-extension-265b618`.
Manifest `160d0dfc93c32ce578f6aa1fed55b6c615dcf984f60229d44c7fbf2b756abbee`;
tar `6020c7592a4a11069416aa1d38bab95492b4356d17d0e3f30cd1396a0ad98d27`.
CPU-only package preflight301009 submitted with2CPUs/4GB/10min in the pinned
Python3.11 Apptainer runtime. Its terminal state has not yet been inspected.
Logs: `.../experiments/diffusion-bottleneck/extension-package-preflight-265b618`.
No model or episode is part of this package preflight.

The new sequential dispatcher must not start until301009 completes0:0 with101
tests passing. Intended new run root:
`/lustreFS/data/superworld/ckontzias/thesis/experiments/diffusion-bottleneck/extension-20260914-265b618`.
The prior54e3acf dispatcher has exited; it must not be restarted. Analysis script
`D:/THESIS-TEMP/analyze-extension-265b618.sh` is prepared but not run, and the
new external backup destination is `D:/THESIS-BACKUPS/bottleneck-20260914/extension-265b618`.

## Preflight passed; frozen scientific dispatch started

Heartbeat2026-09-14T10:17:45.843Z inspected301009: COMPLETED0:0, ElapsedRaw5,
batch MaxRSS3464K as reported by Slurm (not a claim about total container memory).
The package-test stderr ends with101 tests in2.490s, OK. No model/episode ran in
that check. The new run directory was confirmed absent before starting once.

Frozen controller launched via SSH tool session17250. At2026-09-14T10:18:44Z it
recorded the prior11-second charge and submitted301010, index8/ref567/repeat0.
No scientific output or evaluator log was read. No terminal state is asserted
for301010 at this launch check. The controller performs its frozen metadata-only
sequential checks; future job identities remain in DISPATCH.jsonl. Do not restart
or duplicate the controller. The existing heartbeat now follows this active run.

## External SSD disconnect and read-only recovery

At heartbeat2026-09-14T10:41:45.688Z, Windows no longer listed D:, WSL could
not attach D:/WSL/Thesis-Ubuntu/ext4.vhdx, and local SSH tool session17250
ended with a server timeout. No remote job or controller was restarted.
After the user reconnected the SSD, Windows reported THESIS_SSD Healthy/OK,
WSL/SSH worked, and the original remote controller was found alive as PID1140172
with the exact265b618 source/run arguments. The local session is closed; use
the remote process and append-only ledger for monitoring, not a session restart.

The ledger continued during the disconnect. Scheduler inspection confirmed all28
submitted jobs through301040 (indices8-35) COMPLETED0:0:1985 allocation seconds,
plus the previously charged11seconds =1996seconds. This is28 of56 processes,
not28 completed references. No scientific output/log was opened. No recovery
mutation, duplicate dispatch, scientific rerun or change to the frozen controls
was needed. The controller continues autonomously on Prometheus.
