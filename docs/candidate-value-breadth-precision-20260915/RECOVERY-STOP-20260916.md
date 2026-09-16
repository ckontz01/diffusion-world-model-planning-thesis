# CVL-BP1 recovery infrastructure stop — 16 September 2026

**Status: paused, incomplete; no new scientific decision.** The one-use recovery
recorded in [RECOVERY-LAUNCH-20260916.md](RECOVERY-LAUNCH-20260916.md) stopped after
46 successful allocations. Together with the 102 previously completed
coordinates, **148 of 450 fixed coordinates are complete**. All completed output
bytes and failure evidence are preserved and externally backed up. No partial
scientific outcomes were opened or interpreted.

## Exact fault and containment

The WSL backup companion (previous PID 24288) exited during its recurring external
volume-identity check. Its exact technical stderr records:

```text
WSL ... ERROR: UtilAcceptVsock:273: accept4 failed 110
subprocess.CalledProcessError: ... powershell.exe ...
(Get-Volume -DriveLetter D).FileSystemLabel ... returned non-zero exit status 1
```

The backup error is a WSL-to-Windows interop/query failure. A subsequent native
Windows volume query succeeded and identified D: as `THESIS_SSD`; this establishes
availability at the later preservation check, not the exact earlier fault time.
There is no evidence here of a scientific worker defect or lost result bytes.
No stage archive transfer was in progress when the companion failed.

The companion recorded `BACKUP-RECOVERY-STOP.json`. The recovery controller
(previous remote PID 4125577) raised `RuntimeError: Backup companion stopped`
before another submission. Its `RECOVERY-STOP.json` has `active_job=null`, no
unresolved reservation, and `no_automatic_retry=true`. The liveness stop worked
as specified: the last bounded worker finished, then dispatch ceased. Neither
process was restarted. No new job was cancelled or resubmitted.

The exact failed processes were reported before their technical logs were read.
No evaluator logs, scientific reports, labels, banks, predictions or fit metrics
were opened. The old `DISPATCH-STOP.json` remains an unchanged historical record,
not evidence of a second worker failure.

## Terminal accounting and fixed remainder

One Slurm poll at **2026-09-16T21:34:51Z** corroborated all 46 exact recovery job
IDs as `COMPLETED`, exit `0:0`. The closed recovery ledger supplies the individual
allocation charges. Its last job is **301629**, `breadth-139`, reference 1395,
H150, with 286 allocation seconds. The next **unsubmitted** coordinate is
`breadth-140`, reference 463, H75; it is not a failed case needing a retry.

| Accounting item | Count / charge |
| --- | ---: |
| Previously completed coordinates | 102 |
| Newly completed recovery coordinates | 46 |
| Total completed coordinates | 148 |
| Total attempted allocations, including old cancelled 301578 | 149 |
| Original successful allocation time | 21,729 GPU seconds |
| Preserved original cancellation | 63 GPU seconds |
| Recovery allocation time | 10,212 GPU seconds |
| Total charged allocation time | **32,004 GPU seconds (8h53m24s)** |
| CPU scientific-stage allocation time | 0 seconds |
| New failed/cancelled jobs at this stop | 0 |
| Unresolved reservations / active jobs | 0 |

The unchanged remainder has **302 coordinates**: 52 breadth and 184 precision
collection jobs, one CPU fit, 64 evaluation jobs and one CPU analysis. This is
300 GPU allocations plus two CPU allocations. Prior actual charges plus those
remaining maximum reservations would be 250,404 GPU seconds (69h33m24s) and
7,200 CPU allocation-wall seconds, within the original caps. This arithmetic is
not authorization to resume.

The original caps remain 309,600 GPU seconds, 7,200 CPU allocation-wall seconds,
10GB remote artifacts, 500MB per allocation, 50MB source/control and 40GB free on
the external SSD. Prior failed/cancelled charges and preservation bytes count.
Scientific source, roles, streams, candidate banks, labels, models, update
budgets, weighting and analysis remain unchanged.

## Preservation and external backup

Run root:
`/lustreFS/data/superworld/ckontzias/thesis/experiments/candidate-value-breadth-precision-20260915/run-70e3838c83561b8b`

Recovery control directory:
`/lustreFS/data/superworld/ckontzias/thesis/staging/cvl-bp1-recovery-301578-20260916`

External destination:
`D:/THESIS-BACKUPS/candidate-value-breadth-precision-20260915/run-70e3838c83561b8b`

The new sealed `recovery-stop-preservation-20260916/` bundle includes terminal
accounting, closed recovery controls and ledger, exact technical logs, source
and approval evidence, and an exhaustive opaque file-hash coverage inventory.
All **19,580 pre-existing run file hashes were unchanged** after preservation.
Existing files were not deleted, overwritten or relocated during this stop.

The accepted one-shot archive writer and seal verifier produced
`recovery-stop-20260916.tar`: **154,030,080 bytes**, verified against its exact
backup request. It contains the 46 newly completed output directories, the
preserved interrupted-attempt and recovery-evidence directories, and the new
preservation bundle: 49 sealed roots. The unchanged earlier
`failure-20260916.tar` covers the original 102 completed outputs and earlier stop
evidence. These archives jointly preserve all 148 completed coordinates; some
recovery evidence is intentionally duplicated, but no new outcome is invented.

The transfer and verification took **20.16569117 seconds** of local wall time,
with zero Slurm allocations and no scientific payload decoding. The one-shot
operation used a native Windows volume-identity check plus WSL mount/free-space
checks; it did not modify or restart the failed companion or relax permissions.
The local receipt and remote ACK agree on archive hash, request hash, byte count
and `verified=true`. An independent Windows SHA-256 calculation matched the
new archive. The run occupied 457,892,697 bytes after its backup ACK, before any
later activity; no laptop bulk-data fallback was used.

| Preserved artifact | SHA-256 |
| --- | --- |
| New external archive | `b5bbf19cc470ccbf58fad39f350ccfecf38fed2867b7eaf8344d2f8e6cc12d46` |
| New external receipt | `ebb4d9606f7ecc75484c1d50505a9dae5a4dcfa59864ee1a622cb1cad3244a83` |
| New remote backup ACK | `3d806dd5824bb2dc6baa504543e398f18bc01dbb9b69383ac3aae8d86aa9b245` |
| New backup request | `2e800637463fc1fbb121e8939875c553f004d71c4fbf84320001567af0321383` |
| New preservation bundle seal | `02872c95d13378823f3bdef4faf6e79a8c3daf487acfe5f370115d0ba68db626` |
| Recovery terminal accounting | `2b0df6c05f7acf0ce1a629a8d428abbcf15b59d95614fe9451b003418eec8f53` |
| Exact backup-companion technical stderr | `637bb6aaf7e6cb5406e3de9cd61e33416ffc5a5539da26c4d4b1e5b47b3851cc` |
| Earlier failure archive, 312,852,480 bytes | `5f09feeabd59032c129940c69a6ab5163f1bf4171d52bc37ef96b7fc4f558bba` |

## Paused boundary and next decision

The existing `monitor-cvl-bp1` automation was **paused**, not duplicated or
deleted. No second infrastructure repair, new controller/companion, job retry,
resubmission or scientific change was performed. The earlier user approval was
used for the single recovery above; its new-failure rule requires scoped
direction before another resumption.

The bounded next decision is whether to repair volume-probe reliability and
resume only the 302 unsubmitted fixed coordinates, reusing all 148 completed
outputs and retaining all costs, caps, immutable science and backup gates. No
completed coordinate needs rerunning. This record does not implement that work
or treat eventual success of such a repair as established.

`stop_no_ranking_promise`, the historical `original_relative` nominee,
continuation baseline, all historical artifacts and the three E12 drafts remain
unchanged. The reserved CVL closed-loop 32 and all 1600–5999 payloads remain
unopened. There is no new efficacy claim, model promotion or scientific stop.
