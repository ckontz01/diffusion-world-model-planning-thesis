# CVL-1 terminal verification and accounting — 15 September 2026

The [result](RESULT-20260915.md) is `stop_no_ranking_promise`, matching both
`terminal/REPORT.json` and `DISPATCH-FINAL.json`. This is a scientific stop after
successful ranking analysis, not `stopped_preserved_no_retry`. The earlier
technical stops and authorized controller-only continuation remain unchanged.

## Identity

- Scientific implementation: `84141f281e507e68114cab2be05d75d259b10a63`.
- Snapshot: `/lustreFS/data/superworld/ckontzias/thesis/snapshots/candidate-value-learning-20260914-521a0e6627c570ff`.
- Source manifest: `521a0e6627c570ffa30d12adc63f92cf9ba76dee2c9bc4c59d24f4982f4f45f2` (62 entries).
- Protocol: `6451cbd44e3fdfd430b3f6d1c69eb49a14bb493beaa1acdedee971a73978ff2c`.
- Capsule: `a1f152f66a1a6f1b766691b4a12c18fc6489d921f82ca7fbca29d86714b21469`.
- Approval: `efa01d3c5512c34ec464bae9758e3046f9f90e6adb3745578ae83351004ef65a`.
- Controller overlay, not scientific source: `5dd6d487582d18c659f4c904ffffeedc41fea904`, manifest `2b6e81a76aefe5943872bf2f01e5561e75595f1b032b0eba431b258ed373e03b`.
- Run: `/lustreFS/data/superworld/ckontzias/thesis/experiments/candidate-value-learning-20260914/run-521a0e6627c570ff`.
- Fit adjacent seal: `90e491a7a186e7ef1968c70f29ecf49b3bfbe481f013ba051c10e33c77eb669c`.
- Ranking adjacent seal: `60ac044057bce693c5235360c43fc09162131804fdd55fdbb6289790616f4cea`.
- Terminal adjacent seal: `7caf3516421cd549369bde72932668b83108f424529dae1e4b5a72fc0ee7bafe`.

## Completed grid and charged resources

|Stage|Successful jobs|Allocated seconds|
|---|---:|---:|
|Synthetic A6000 preflights|2|160 GPU|
|Training collection|192|41,022 GPU|
|All five fits / support gate, 301371|1|203 CPU wall|
|Ranking-validation collection|64|13,960 GPU|
|Ranking analysis, 301439|1|99 CPU wall|
|Prior failed preflight, 301159|0 (one failed allocation)|45 GPU|
|Conditional closed loop / final closed analyzer|0|0|

There are **260 successful registered jobs plus one prior failed allocation**,
not 293 executed jobs. The 32 closed jobs and one final closed analyzer were
correctly skipped by the failed ranking gate. Last validation job 301438 finished
COMPLETED 0:0 in 305s; analyzer 301439 finished COMPLETED 0:0 in 99s. The final
heartbeat used one batched Slurm poll. Full job identities and stage coordinates
are preserved in terminal `REPORT.json` and the original/resumed dispatch ledgers.
The authenticated continuation receipt supplies original job 301256's 89s, which
occurred after the original controller log stopped; it is counted exactly once.

Total GPU charge: **55,187s = 15h19m47s**, including the failed 45s allocation;
total CPU allocation wall time **302s = 5m02s**, at four reserved cores (1,208
core-seconds). These are within 180,000 GPU seconds and 7,200 CPU wall seconds.
No GPU training job was used. Checksumming, source verification, transfer and
monitoring CPU/wall time are outside these compute-job sums, not claimed free.

First successful-chain submission: 2026-09-14T20:38:16.132Z. Terminal backup
acknowledged: 2026-09-15T15:45:34.218Z. This approximately 19h07m elapsed interval
includes queueing, backups and the overnight controller interruption; it is not
GPU utilization. Original failures and the manual stopped-run backup are preserved.

Final dispatch recorded 766,733,864 bytes before terminal copies; the completed
run measured **771,318,540 bytes** after terminal/control output. Adding the frozen
50,000,000-byte source/control reservation gives 821,318,540 bytes against the
20,000,000,000-byte limit. It is a point-in-time file-size accounting, not an
OS-enforced peak disk quota. Largest reported collection sampled host RSS was
1,817,690,112 bytes (train), and 1,715,126,272 (validation); fit 621,056,000 and
ranking analyzer 463,159,296. Sampled RSS is not total node RAM or total GPU VRAM.
No unmeasured device peak is invented.

## Integrity and independent physical checks

Before aggregate interpretation, the remote validation-stage 65 seals (fit plus
64 validation workers) and terminal-stage two seals (ranking analyzer plus
terminal evidence) were checked against exact backup-request seals, with every
member rehashed. Technical report projections matched source/capsule, kind/index,
reference role and all no-protected/historical-unchanged flags. Training's 194
sealed directories had already passed the same stage validation before fitting.
All source-manifest entries were rechecked at finalization.

The authenticated analyzer calls `validated_banks` from the unchanged
`candidate_value_data.py` before reducing outcomes. That path independently
reconstructs every saved post-action physical success against the pinned record
goal (four-coordinate norm <20 and circular angle <pi/9), checks native
termination and remaining budget, reconstructs decoding from pinned coefficients,
and compares actual delivered candidate actions exactly. It rechecks branch
prefix actions/states/dynamics/flags, sampler coverage, full label grid, paired
stream distinction/candidate coupling, and physical-step totals. These checks
are executed by the sealed successful fit and ranking jobs, not inferred merely
from saved success flags. Final reporting did not rerun models or episodes.

Only permitted train/validation records were used; the closed-loop role was not
opened, and no 1600–5999 payload, protected metric artifact, confirmation, GMM or
SAGE evaluation was accessed. No scientific source or tensor was changed.

## External SSD backup scope

Destination: `D:/THESIS-BACKUPS/candidate-value-learning-20260914/run-521a0e6627c570ff/`
on verified `THESIS_SSD`, never C:/OneDrive. The stage watcher finished with empty
stderr. Both controller and watcher were absent after completed terminal backup,
consistent with normal completion, not an idle service failure.

|Archive|Bytes|SHA-256|
|---|---:|---|
|train.tar|579,891,200|`5c83be11244deb25c0214731fc9f1074b909eadcb44ddf99530c89663e8e7c5f`|
|validation.tar|200,867,840|`4c2a16f7955566f37bc9d2b0a40916785545f78cfeb5280c82eb8d4fdeda4fc6`|
|terminal.tar|5,672,960|`d80dfccf1fdc2c99331606f0191365e085a90dda278193e51ca9cac5383c1935`|

Train contains both preflights plus all 192 train outputs. Validation contains
fit and all 64 validation outputs. Terminal contains the ranking analysis and
terminal evidence, including capsule/approval, source manifest, controller and
continuation receipt, ledgers and run-level Slurm logs. There is no closed-stage
archive because no such jobs ran. The original source export, controller package,
failed-preflight and manual stopped-run archives remain separately preserved.

Exact request SHA-256 values:

- Train: `85c97eb0975b67b11a617d7d9ab31249a64cce5fdaa90f0cc4501b89d669df58`.
- Validation: `5a1e3bceb62fa2373f02c81610f52eced720ef38e6839d03cf7de224da026e7b`.
- Terminal: `5e9ac6ddb2bf941524dd251dc19b6e025957829c026656f33338a7be4e6673e3`.

Each remote acknowledgement matches its exact request and local receipt. Local
archive hashes and all internal seal/member hashes are independently verified
without extraction or overwriting. Bulk scientific files remain outside Git.
Final re-verification covered 194 / 65 / 2 adjacent seals and 23,975 / 8,185 /
537 sealed members in train / validation / terminal archives, respectively.
Only this result, verification receipt and README history are new finalization
edits. The three unrelated E12 drafts are not staged or modified.

Final local synthetic regression checks passed: **40 candidate-value tests in
42.715s**, plus **22 historical single-anchor tests in 0.225s**. `git diff --check`
passed. These tests use synthetic data; they do not retrain research models or
evaluate new references. WSL Git status still listed exactly the three unrelated
untracked E12 drafts. The completed monitor is removed after verified publication;
no next experiment is scheduled by this result.
