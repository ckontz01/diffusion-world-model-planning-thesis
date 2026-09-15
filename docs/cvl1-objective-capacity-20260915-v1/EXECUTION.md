# Objective × capacity v1 — execution record

The user authorizes one new saved-feature CPU learning study with four fixed
configurations, 48 cross-fit and 12 full-data fits. The historical result and
diagnosis are not modified. See [the frozen protocol](PROTOCOL.md).

## Prelaunch checks

17 focused synthetic tests passed, covering paired same-draw targets and zeros,
two binary draws, baseline identity, nonbinary-label rejection, hierarchical
weights, distinct new/historical tie rules, deterministic source-disjoint folds,
training-only/common normalization, exact parameter counts, zero relative baseline,
ensemble arithmetic, original-BCE optimizer equivalence on synthetic fixtures,
finite zero-target relative fitting, gain/loss reduction, recommendation rules,
exclusive size-reserved output, validation-read barrier and CPU reservations.

Source implementation: `analysis/cvl1-objective-capacity-20260915-v1/study.py`;
focused tests: `test_study.py`; read-only runtime wrapper: `run.sh` in the same
directory. Original model and data helpers are authenticated against accepted
CVL-1 source manifest, not copied or edited. Git/source/job/output identities and
actual accounting will be appended after launch/completion, without changing
the scientific protocol. No GPU or original simulator data is required.

The one submission requests account superworld, partition defq, qos normal,
4 CPUs, 8G memory and 02:00:00. A frozen source export, exclusive launch intent
and exclusive run directory precede the single `sbatch` call. The source export
only applies reversible CRLF→LF transport normalization, with its own hashes.
No job retry is authorized. Terminal artifacts and logs, including any failure,
are retained and backed up to the external THESIS_SSD.

## Frozen source and one submission

Commit `d2cf5c8f6381dd6684403c55321210d165a33ea6` was pushed to
`candidate-value-learning-preparation-20260914`; `git ls-remote` returned the
same full hash before submission. Only five new source/document files were
exported. Each export's CRLF→LF normalization was checked as exactly reversible.

- Source archive SHA-256: `29c2e1a6decac86c81810fb074df42cfe19a61244f1facfdab1ba2e5cc4d9a80`.
- Exported source manifest SHA-256: `9a3ede8d257698d62e50b3f088e64e33573d3c25de4f9d2a8f42935a4e500284`.
- Protocol SHA-256: `6cc00051d539a6562e05b5b445549dc564ade43f1a39429da85fe54b0fb80647`.
- Source: `/lustreFS/data/superworld/ckontzias/thesis/staging/cvl1-objective-capacity-20260915-v1/source-d2cf5c8-lf`.
- Run: `/lustreFS/data/superworld/ckontzias/thesis/experiments/cvl1-objective-capacity-20260915-v1/run-d2cf5c8`.
- One submitted CPU job: **301441**. No GPU request, retry or dependent job.

External source archive:
`D:/THESIS-BACKUPS/cvl1-objective-capacity-20260915-v1/source-d2cf5c8.tar`.
The remote archive hash matches it. The original three E12 drafts were still
untracked in `/home/chris/thesis` at launch; they were not opened or changed.

## Completed allocation, seals and backup

Job 301441 completed **0:0**, **201 allocated wall seconds**, 4 CPUs and 8GiB,
zero GPU allocations. Final Slurm TotalCPU is **656.057 seconds** (651.505 user,
4.552 system); allocated core-time is 804 seconds. The early terminal receipt
captured Slurm's not-yet-populated `00:00:00` CPU field; that receipt is preserved,
and the separate final scheduler receipt records the populated value, not zero use.

The worker's final completion telemetry reports 196.667792 wall seconds and
653.594758 process CPU seconds; reported maximum RSS is 809,873,408 bytes.
The 60 fits used 147.027633 wall seconds in total, 1.456372–4.496727 seconds per
fit, with 81,120 optimizer steps. No fit exceeded its 100-second reservation;
no failed allocation, retry, omitted configuration or extra fitting occurred.
The only stderr message was Apptainer's informational `/etc/localtime` underlay
bind-mount notice. No permission or environment change was made.

The pre-validation freeze SHA-256 is
`d8a592d215ec7819c191694b531ab08c4dd9dc54b19b6b4b6b1ec002df370582`.
It contains hashes for all 144 preceding output members, including 60 models,
five fitting-only scalers and the training-only recommendation. Those members
were rechecked before validation and against the external backup afterward.

The final results seal SHA-256 is
`f76f6eb465706c048d36547015da2178f0ba00429530c1fa4b336aec168c9e9a`.
All 145 root members and five 14-member model sub-seals verified: 215 member
checks. The worker wrote 90,840,277 bytes; the run with contemporaneous logs and
launch metadata was 90,851,777 bytes before the terminal accounting receipt.
New source/report/accounting supplements remain far below the 1GB total limit.

Terminal archive: `D:/THESIS-BACKUPS/cvl1-objective-capacity-20260915-v1/result-d2cf5c8.tar`,
90,972,160 bytes, SHA-256
`2545ec37b4b840a54926aa169bac16a9826174e8147d3c2edad8314522c5392d`.
Remote and external-SSD hashes agree. Backup scope includes only this new run:
all fitted evaluators/scalers, fold identities, predictions and original saved
labels as used in the new reports, aggregate/reference/bank reports, consumed-file
hashes, source/protocol, job logs and accounting. No original simulator dataset
copy. Final accounting and the committed publication supplement are separate
adjacent backups; the original terminal archive is not rewritten.

The publication formatter, added only after completion, transcribes frozen
statistics and copies all reference results; it performs no model evaluation,
fitting, new statistical calculation or recommendation selection. Its generated
[report](REPORT.md) and [all-reference results](REFERENCE-RESULTS.json) accompany
the exact machine-readable bank/candidate evidence in the terminal archive.
