# ACID-alternative v1 D1 final provenance pointer

Date: 2026-08-15  
Role: post-sealing convenience pointer; intentionally outside the immutable
audit and backup manifests to avoid self-reference

## Authoritative result report

- local path:
  `cluster/prometheus/ACID-ALTERNATIVE-D1-RESULT-2026-08-15.md`
- SHA-256:
  `6f6dbd01d33b82700fcc6f5816cc2e7b60c416120a040a2a58899758f700cc58`

## Immutable sensitivity result

- Prometheus path:
  `/lustreFS/data/superworld/ckontzias/thesis/results/acid-alternative/analysis/d1/sensitivity/job-297131/summary.json`
- SHA-256:
  `9af2d7dba0be0f5d7e342313a628d3044e958854098029ef4df2b76f5fc49f33`
- completed evaluations: 315, comprising 105 per task

## Authoritative Prometheus audit

- path:
  `/lustreFS/data/superworld/ckontzias/thesis/audits/acid-alternative-v1/d1-final-20260815T201058Z`
- `audit-manifest.sha256` file SHA-256:
  `af93d9b73a8e02ad90e3cda2fdeb10ec4a73951453b3d0aebb2732d4824e818d`
- verified contents: 967 files; 487 effective Slurm accounting records,
  all `COMPLETED|0:0`; 72 training summaries; 45 primary summaries; 315
  sensitivity summaries; seven source-snapshot manifests; 3,411 stable
  job-ledger entries
- permissions at verification: zero writable files or directories

The earlier sealed audit
`d1-final-20260815T200518Z` remains intact but is superseded as the final
control-plane record because it contains the pre-AA-025 SSD backup helper. It
does not differ in scientific results.

## Immutable external-SSD backup

- WSL path:
  `/home/chris/thesis-backups/prometheus/acid-alternative-v1/20260815-final`
- `BACKUP-MANIFEST.sha256` file SHA-256:
  `db61d7aa8560f6c511e6c7f17b208cc20f6c9dda3e07a3840316d5979a2ae9d4`
- verified contents: 2,491 files, 71 MB
- permissions at verification: zero writable files or directories
- copied audit-manifest hash matches the authoritative Prometheus audit
- copied report hash matches the local result report

## Scientific state

- The current frozen diffusion transition verifier is not supported as a
  robust alternative to ACID.
- The predeclared `lambda = 0.005` sensitivity is a promising development-only
  v2 hypothesis, not a rescued v1 primary result.
- C1 and I1 remain unauthorized and unseen.
- No scientific output was overwritten or modified during finalization.

