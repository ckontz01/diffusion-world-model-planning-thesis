# CVL-1 authorized controller-only continuation — 15 September 2026

The user explicitly approved repairing the temporary-file inventory race and
resuming at training index **81**, retaining all 81 completed collection jobs,
both preflights, and their costs. The [original stop](DISPATCH-STOP-20260915.md)
and its external archive remain unchanged. This is not a new scientific run or
permission to retry a scientific failure.

## Narrow repair and execution contract

The size counter now performs one stat per encountered file and tolerates only
`FileNotFoundError` during concurrent temporary-file/directory removal. Permission
and I/O errors still stop dispatch; storage checks and their limits remain active.
This also applies to live Slurm log sizes. Nothing in a worker changes.

A separately authenticated controller overlay imports the contract from the
original immutable source and submits the original `run_candidate_value.sh`.
Source manifest `521a0e6627c570ffa30d12adc63f92cf9ba76dee2c9bc4c59d24f4982f4f45f2`,
protocol `6451cbd44e3fdfd430b3f6d1c69eb49a14bb493beaa1acdedee971a73978ff2c`,
capsule and original approval remain those in [RESTART-20260914.md](RESTART-20260914.md).
No new preflight, duplicate reference, scientific source rewrite, outcome
conversion, fitted model, or replacement label is introduced by this repair.

Before dispatch, a one-use `RESUME-APPROVAL.json` pins the controller bytes,
original dispatch log, original source/protocol/capsule/approval, exact 83-job
prefix, every adjacent seal, and reconciled allocation times. A fresh batched
Slurm check must establish all 83 jobs COMPLETED 0:0 and match the receipt.
All sealed members are rehashed; only top-level technical scalar identities
are decoded from historical reports. Partial scientific outcomes stay unopened.
Unexpected subsequent task artifacts, prior final decisions, missing seals,
different accounting, or any mismatch fail closed.

An exclusive `RESUME-CLAIM.json` prevents reuse. The original `DISPATCH.jsonl`
is never amended; new events go to `DISPATCH-RESUME.jsonl`. Completed coordinates
are explicitly rejected before submission. The original worker's source checks
and the full runtime authentication still execute. A fresh exact-source external
SSD readiness receipt is required.

The previously idle backup process was found absent before this continuation;
its existing stderr is empty. No stage had requested a backup and its destination
is empty. A separate watcher-restoration helper may restore only that exact idle
state: it rejects any existing stage request/acknowledgement, archive, destination
content, terminal decision or prior restoration claim. It uses the original
frozen `once` transfer/member-verification implementation unchanged. Its exclusive
claim lives outside the stage-archive directory. This is not a retry of a failed
transfer and cannot overwrite prior archives or the manual stopped-run backup.

## Accounting and remaining stages

Carry forward **17,151 GPU allocation seconds (4h45m51s)**, including failed
preflight 301159's 45 seconds and completed worker 301256's 89 seconds. CPU
fit/analysis usage is zero. The maximum remaining grid is:

|Stage|New jobs|Maximum allocation|
|---|---:|---:|
|Training collection indices 81–191|111|66,600 GPU seconds|
|Fit/support gate|1|6,000 CPU wall seconds|
|Conditional ranking collection|64|38,400 GPU seconds|
|Ranking/promise gate|1|600 CPU wall seconds|
|Conditional closed loop|32|19,200 GPU seconds|
|Final report|1|600 CPU wall seconds|

Thus at most 210 additional jobs, not a new 293-job run. Existing plus remaining
registered tasks total 293, with the earlier failed preflight separately charged.
Worst-case GPU allocation including spent time is **141,351 seconds (39h15m51s)**.
The original 50 GPU-hour / 7,200 CPU-wall-second / 20GB limits are unchanged;
the 50MB source/control reservation includes the controller overlay and receipts.
Technical/failed future allocations still count. There are no automatic retries,
case changes, budget increases, or changed sparse-support/ranking gates.

All original train/validation/closed/report backup boundaries remain mandatory.
The existing manually verified stopped-run archive is preservation evidence,
not a substitute for the complete train-stage backup. A final terminal package
also contains the continuation approval and exact controller bytes.

## Regression scope and limitations

`test_candidate_value_resume.py` synthetically tests disappearing files and
directories, propagation of permission/I/O faults, exact prefix/accounting and
approval rejection, sealed technical-only projection, all 210 remaining tasks,
unchanged original dispatch bytes, cumulative accounting, and refusal of a
second continuation. It executes no models, episodes, or cluster jobs.

The complete CVL and single-anchor regression suites passed **62/62 tests in
39.228 seconds** on the local CPU runtime, including two idle-watcher restoration
tests. Actual overlay/receipt hashes, verification results and first new
job are recorded in a separate launch receipt after deployment. Passing these
engineering tests says nothing about success-label support or learned ranking.
Models, initializer, decoder, historical decisions, protected data boundaries,
and E12 drafts remain unchanged.
