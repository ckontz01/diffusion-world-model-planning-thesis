# Independent PushT study: execution and recovery

Branch: `independent-pusht-benchmark`. Frozen scientific source: `63f0440`.
Study root: `/lustreFS/data/superworld/ckontzias/thesis/experiments/independent-pusht/final-20260906-4a608e5`.
Source snapshot: `/lustreFS/data/superworld/ckontzias/thesis/snapshots/independent-pusht-4a608e5`.
Source-manifest SHA256: `d79c5f0f5515011885a1309d61985e1464c8c6738c7d9f4a3b161378836381ec`.

## Current submitted chain

- Collection/validation/lock: `300326`.
- Stage0 evaluation: `300339` (450 tasks, at most four GPUs).
- Stage0 complete-grid analysis and independent reaggregation: `300340`.
- Verified-decision controller: `300341`.

The controller submits later registered stages only if the verified decision
requires continuation. It stops at all-three-boundaries crossed, the registered
strong-adverse futility boundary, or maximum6000. It cannot tune a model or
select a favorable subset. Missing/failed tasks block analysis.

Use scheduler state and exit codes to monitor execution. Read comparative
summaries only after `INDEPENDENT-VERIFICATION.json` verifies the corresponding
`SUMMARY.json`. Do not read individual outcomes to choose a fix or method.
For a genuine execution failure, preserve the failed files and diagnose logs.
Do not blindly resubmit an entire stage or delete completed results.

## Data durability

Source, protocol, tests, pilot reports and launch context are pushed to GitHub.
Large raw reference/episode arrays remain in the study directory on Prometheus.
After collection locking or a completed verified stage, run from WSL:

```bash
python3 /home/chris/thesis/cluster/prometheus/backup_independent_pusht.py \
  --study /lustreFS/data/superworld/ckontzias/thesis/experiments/independent-pusht/final-20260906-4a608e5
```

This creates a separate copy under `/home/chris/thesis-artifacts/independent-pusht/`.
It checks reference hashes and only copies complete, independently verified
stage outputs. It does not invoke models, restart jobs, or create automation.
Record backup status and verified stage summaries in the Git branch afterward.
Never put raw gigabyte arrays, SSH keys, credentials, or unrelated files in Git.

## Interpretation

This is a new reachable-goal population generated using a weak random collection
policy. Initial proposals are uniform as specified, then reference trajectories
are conditioned on the declared full-trajectory validity rules. It is not the
original expert-trajectory distribution. H75/H150 are future-state offsets,
not minimal path lengths. New physical starts use R3's documented defaults.

Six final arms: unchanged five E18 variants and released native full SAGE.
SAGE's finite commands outside its declared Box are preserved and counted;
this is disclosed native behavior, not a secretly clipped weak baseline.
The explicit boxed-SAGE sensitivity pilot is preserved separately.

No result may be claimed until the scientific run and independent verification
actually complete. A scheduler submission is not a passed experiment.

Launcher-only amendment4a608e5 preserves the original63f0440 scientific protocol and all collection bytes. Old array300327 and dependents were cancelled after an environment-index failure before planning. Completed collection backup exists under the original final-20260906-63f0440 local artifact directory.

## User-owned verified-result archival process

`archive_verified_independent_pusht.py` is a standalone WSL archival exporter.
It checks for independently verified complete-look artifacts, copies their full
raw stage data to the second local disk location, verifies hashes and commits
only the generated reports/tables/verification records to this branch.
It never submits/cancels experiments, changes sample sizes, tunes models, or
interprets unverified partial outcomes. Five mocked publication/permission/hash
regression tests pass. A live one-shot check correctly exported no unverified
scientific results.

The exporter uses existing git authentication; no credential is stored in it.
It requires the Windows/WSL machine, network and existing SSH route to remain
available. A different current Git branch or foreign staged edits stop export
rather than committing elsewhere. Export interruption does not stop Slurm or
remove remote artifacts. No permanent cron or system service is installed.

It stops after a verified terminal record, three consecutive archival errors,
or its explicit process time cap. Process ID and launch record are recorded
separately. Status SSH probes use -n so they cannot consume interactive REPL
input; rsync's own SSH transport intentionally retains its protocol stdin.

## Incremental backup before complete-look analysis

`backup_completed_independent_pusht.py` copies tasks only after their DONE seal
is present. It verifies every exported JSON/NPZ byte hash without interpreting
those outcome payloads. The destination study contains an atomic
`COMPLETED-SHARD-BACKUP.json` index. It is additive and never deletes remote
artifacts or resubmits a task. Eight synthetic safety/integrity tests passed.

The launched bounded WSL process is recorded in
`independent-pusht-evidence/INCREMENTAL-BACKUP-PROCESS.json`. It needs the local
machine/network, stops after a verified terminal indication or three backup
errors, and has a168-hour process cap. This is software archival, not autonomous
ChatGPT monitoring. The separate complete-look exporter handles Git publication.

To perform a single idempotent backup from WSL:

```bash
python3 /home/chris/thesis/cluster/prometheus/backup_completed_independent_pusht.py   --study /lustreFS/data/superworld/ckontzias/thesis/experiments/independent-pusht/final-20260906-4a608e5   --once
```

Do not run duplicate persistent archivers. Inspect the recorded process and its
log first. Source code changes here never modify the frozen running snapshot.
