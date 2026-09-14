# CVL-1 execution contract — launch approval absent

These commands document the completed pipeline; they are **not authorization to
execute research now**. No true approval receipt is created by packaging or tests.

## 1. Source-only export

From Git, export the reviewed full commit, not a moving branch:

```text
python cluster/prometheus/package_candidate_value.py --commit FULL_REVIEWED_COMMIT --out UNIQUE_SOURCE_TAR
```

The deterministic read-only tar contains the import closure, docs, input pins,
LF Slurm script, PACKAGE.json with full Git commit, and SOURCE-MANIFEST.sha256.
Existing files are never overwritten. Deploy only into a new immutable directory:

`/lustreFS/data/superworld/ckontzias/thesis/snapshots/candidate-value-learning-20260914-<sourcehash16>`.

Use a separate control directory for capsule/approval. Preserve an external-SSD
source-tar copy; do not add files to the authenticated source tree.

## 2. Metadata/runtime capsule before approval

On Prometheus, from exported source:

```text
python3 SOURCE/cluster/prometheus/candidate_value_freeze.py --source SOURCE --out CONTROL/LAUNCH-CAPSULE.json
```

It authenticates the historical input lock/registry, exports only 160 selected
identity/seed/path/hash rows without opening reference NPZs, checks exact frozen
checkpoints, pins their loader metadata, existing container/environment and runtime
code/config files. The source scan excludes data/checkpoint/result payloads.
Environment hashing is limited to the declared environment, not artifact roots.
No excluded reference payload is opened, hashed, allocated or evaluated.

Workers recheck approved hashes with no download, installation or fallback runtime.
Full runtime authentication is charged inside worker allocation time; exceeding
the cap stops technically, not permission to relax authentication or budgets.

The subsequent explicit researcher approval must bind this exact receipt:

```json
{
  "researcher_approved": false,
  "experiment": "candidate-value-v1-20260914",
  "source_sha256": "EXACT_SOURCE_MANIFEST_HASH",
  "capsule_sha256": "EXACT_CAPSULE_HASH",
  "protocol_sha256": "EXACT_PROTOCOL_HASH",
  "caps": {
    "gpu_seconds": 180000,
    "cpu_seconds": 7200,
    "storage_bytes": 20000000000,
    "job_bytes": 1000000000,
    "backup_free_bytes": 40000000000
  }
}
```

This false example deliberately cannot launch. Only subsequent explicit researcher
launch approval may produce the true, exact-hash receipt.

## 3. After approval only: backup then dispatcher

Run root is exactly
`/lustreFS/data/superworld/ckontzias/thesis/experiments/candidate-value-learning-20260914/run-<sourcehash16>`.
It must not exist before dispatch. Variables below denote the approved absolute
paths, not alternative roots or previous outputs.

WSL Thesis-Ubuntu, existing SSH alias prometheus:

```text
python candidate_value_backup.py --run RUN --approval CONTROL/APPROVAL.json --source-sha SOURCE_HASH
```

The companion has no model/dispatch capability. It checks `/mnt/d`, volume label
THESIS_SSD and 40GB free, writes a readiness receipt, and watches only this run.
Backups go to `D:/THESIS-BACKUPS/candidate-value-learning-20260914/run-<sourcehash16>`.
No C:/OneDrive fallback, credential extraction, overwrite or deletion.

Then on Prometheus:

```text
python3 SOURCE/cluster/prometheus/candidate_value_dispatch.py --source SOURCE --run RUN --approval CONTROL/APPROVAL.json --capsule CONTROL/LAUNCH-CAPSULE.json --source-sha SOURCE_HASH
```

Only the registered COST-PLAN grid can run. GPU: A6000/normal-a6000, one GPU,
four cores/24GiB. CPU: defq/normal, four cores/8GiB. The pinned Apptainer runtime
and source are read-only; only the new run is writable. No historical evaluator
is invoked. The first eight train jobs are inside the allocation, not extra jobs.

## 4. Stops and evidence

Both synthetic pinned-runtime preflights precede selected-record loading.
Training collection is sealed/backed up before fitting, fitting precedes validation
collection, and ranking promise gates closed loop. Backups must acknowledge exact
stage seals. Monitoring does not interpret partial scientific results.

A failed job, corruption, alias, cap violation, sparse stop, unpromising ranking
or missing backup stops advancement. No automatic retry/resume, replacement, seed
selection or extra budget. Retain partial failures and censored labels. Never
seal a possibly live allocation; uncertain terminal state or transfer needs manual
technical resolution, not new scientific authority.

Successful REPORT.json plus sha256.txt authenticate each job. TECHNICAL-FAILURE.json
is not a negative label. The ledger records reservations, jobs, actual terminal
allocation seconds and backup receipts. BANK-ROWS.json contains sampled-eight
discrimination/selection; REFERENCE-EFFECTS.json reports all 32 closed references.
Terminal evidence includes capsule, approval, source manifest and scheduler logs.

Real deployment identity and pinned-cluster preflights remain unexecuted. Local
tests do not establish operational cluster readiness or scientific efficacy.
