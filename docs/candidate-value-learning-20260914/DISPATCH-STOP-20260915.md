# CVL-1 dispatcher temporary-file race — 15 September 2026

**Technical dispatch stop, not a scientific result.** The frozen implementation
and protocol in [RESTART-20260914.md](RESTART-20260914.md) are unchanged.
No replacement dispatcher, worker, source patch, retry or stage advancement was
launched in response. The heartbeat is paused pending an authorized repair.

## What happened

At 2026-09-15T01:40:45 UTC the dispatcher recorded `dispatch_stopped`, retaining
`active_job=301256`, during training index 80 (reference 219, H75). Its traceback
locates the failure in `candidate_value_dispatch.py:14`, called from line 81:

```python
def bytes_used(run):
    return sum(p.stat().st_size for p in Path(run).rglob('*') if p.is_file())
```

The exception was `FileNotFoundError` for `tmp-train-80/jbve68ex` under the run.
The existence/type check and size lookup are separate filesystem operations;
the temporary file disappeared between them. This is a storage-inventory race,
not evidence of changed checkpoint bytes, invalid physics, or poor learning.
The same counter also scans other live output trees. No assertion about which
library created/deleted that file is needed or established.

The dispatcher stopped before collecting this worker's terminal accounting.
The one batched Slurm check at the 01:50 heartbeat established:

|Job|Task|State|Exit|Allocation seconds|
|---|---|---|---|---:|
|301254|train 78, reference 206, H75|COMPLETED|0:0|166|
|301255|train 79, reference 206, H150|COMPLETED|0:0|235|
|301256|train 80, reference 219, H75|COMPLETED|0:0|89|

Thus 81/192 training-collection tasks completed at scheduler level, alongside
the two successful preflights. Indices 0–79 were acknowledged by the dispatcher;
index 80 finished after its monitoring process failed. All 83 adjacent seals
have independently verified member hashes, including train-80. This is not a
claim that the interrupted dispatcher ran its final `check_report` on train-80,
or that the full collection's scientific validity/support gate has passed.
Training index 81 has no output directory and no submission in DISPATCH.jsonl.
No fit, ranking-validation, closed-loop, or final-analysis stage ran.

## Accounting and information barrier

Last logged cumulative GPU allocation: 17,062 seconds, including the earlier
failed preflight's 45 seconds. Adding job 301256's observed 89 seconds gives
**17,151 seconds = 4h 45m 51s**. The old DISPATCH log is not amended; this is a
separate reconciliation. Its previously outstanding reservation was 600 seconds,
not an additional allocation to add on top of the reconciled 89 seconds.
CPU fit/analysis allocation remains zero. The original 50-hour cap is not reset.

Preserved run files total **233,939,118 logical bytes**; source/control costs
remain additionally covered by the original 50MB reservation. Actual candidate,
bank, success and unavailable-anchor counts remain unopened. No success-support
or ranking-promise decision, trained model, control effect, or efficacy claim
exists. Partial scientific payloads were hashed/copied, never deserialized or
interpreted. Protected partitions, 1600–5999, and E12 drafts were untouched.

## Independent external preservation

The interrupted dispatcher's `active_job` guard correctly avoided sealing a
possibly live run; therefore no `terminal/` seal, `DISPATCH-FINAL.json`, or
automatic stage backup acknowledgement was produced. After scheduler completion,
a separate one-shot content backup preserved all **10,278 run files** on the
verified external THESIS_SSD, without remote writes or permission changes.

External location:
`D:/THESIS-BACKUPS/candidate-value-learning-20260914/dispatch-stop-20260915-301256/`

`preserved-run.tar` is **242,216,960 bytes**. Every regular member was checked
against a remote SHA-256 inventory, with duplicate/path/link checks; the remote
inventory was recomputed afterward and was identical. All 83 preflight/train
adjacent seals also match the copied bytes and exact member sets. The control
log, capsule, approval, and readiness receipt were separately content-verified.
This is a verified manual stopped-run backup, **not** a completed automatic
train-stage receipt or a scientific validity certificate. No archive was
overwritten, failed transfer retried, or output removed.

|Evidence|SHA-256|
|---|---|
|Run archive|`f76408b9808f4f9ce1429a9d0555bee087a0abec1ba5686a687de7ca409a78ad`|
|Remote-file inventory|`593ef045ea413f67aa7e3c4f734348bf739a566d34fec08bcc6983602cdefa7d`|
|Dispatcher traceback|`10af5f090e8020f74b94a7cf6b23223fd26d0efefe69037a476f0471564e8232`|
|Unmodified DISPATCH.jsonl|`effb2591eb3eb9be4161d05e9aafb39e390d5bc61822532dc7794ea876d7019e`|

The source/capsule/protocol identities remain exactly those in the restart
receipt. A future technical repair must preserve completed outputs and costs,
handle disappearance specifically without masking permission/I/O errors, and
reconcile the already-completed job before any continuation. This report does
not authorize resubmitting completed jobs, bypassing storage checks, altering
scientific gates, or restarting the immutable dispatcher.
