# Archival recovery — 6 September 2026

Recorded during the user-requested live status check; no scientific changes.

- Last cluster check: 2026-09-06T13:29:31Z (16:29 Cyprus).
- Stage-0 array 300339: 370 completed shards, 2 live workers (one in Prolog),
  and 78 pending Resources. Accounting briefly listed only one running worker.
- Analysis 300340 and controller 300341 remain pending on dependencies.
- No independently verified analysis or terminal result was available.
- The incremental backup stopped after three SSH `No route to host` errors.
- Its last prior successful copy covered 343 sealed shards.
- Neither existing archival program was running when checked.
- SSH connectivity had recovered; the one-shot catch-up exited successfully,
  copying 25 additional shards: 368 total, 2,682,239,369 verified bytes.
- The verified-result exporter one-shot returned zero new verified looks.
- Restarted the unchanged archival scripts; no duplicate process was present.
- WSL backup PID: 10146. WSL verified-result exporter PID: 10163.
- Both use 300-second intervals and a 144-hour cap; local connectivity is required.
- The first restarted backup reached 369 shards and 2,689,480,526 verified bytes.
- Backup log: /home/chris/thesis-artifacts/independent-pusht/INCREMENTAL-BACKUP.log
- Export log: /home/chris/thesis-artifacts/independent-pusht/VERIFIED-ARCHIVE-RECOVERY-20260906.log
- No partial comparative outcomes were interpreted. No Slurm jobs were changed.
- Frozen source, protocol, models, reference collection, and E12 drafts unchanged.
