# Prometheus storage migration status

Completed 8 August 2026.

## Outcome

- Cluster project root: `/lustreFS/data/superworld/ckontzias/thesis`
- Prometheus project usage after migration: approximately 135 GiB
- Live local WSL VHDX: `D:\WSL\Thesis-Ubuntu\ext4.vhdx`
- Live VHDX physical size after export/re-import: 17,293,115,392 bytes
  (16.11 GiB), down from 188.44 GiB
- External SSD free space after migration: approximately 435.05 GiB
- Retained WSL recovery tar: 15,567,093,760 bytes (14.5 GiB), SHA-256
  `6716df151938bd067d10571fb7f21f09a7618aec549ff4c31a1ed6dc7c01ed00`

## Verified datasets on Lustre

| Dataset | Expanded bytes | SHA-256 |
|---|---:|---|
| PushT | 46,300,921,856 | `b6ebd9ac94bbe9e383f6e7a9cd92d74e9aa665ea57b758ed3717b0ee7df8d4fb` |
| Cube | 101,942,558,720 | `0664d507c4ff12009010644c9ae950836f954e700c172ccf22e7423af1a55625` |

The compressed source revisions and hashes are recorded in
`dataset-sources.tsv`. The six released checkpoint/probe hashes are recorded
in `checkpoint-manifest.sha256`; all six passed verification on Lustre. The
Hi-LeWM Zenodo `package.zip` passed `artifact-manifest.sha256`.

## Migration jobs

- `294544`: canceled after discovering that compute nodes have no outbound
  internet route. No dataset was modified.
- `294546`: failed safely because `zstd` was absent from the compute-node
  `PATH`. No expanded dataset was promoted.
- `294548`: completed successfully. Both archives and both expanded datasets
  passed SHA-256 checks; redundant compressed dataset archives were removed.

The associated logs are retained in `migration-logs/` both here and on
Prometheus.

## Local cleanup

After job `294548` completed, the following reproducible local bulk copies
were permanently removed from `/home/chris/thesis`:

- PushT and Cube expanded datasets;
- six duplicated released checkpoint/probe files;
- the downloaded Hi-LeWM release ZIP;
- the extracted 2.5 GB release checkpoint bundle;
- redundant macOS archive metadata.

The retained WSL installation was boot-tested after compact re-import. It
preserves user `chris`, the thesis protocol, the Conda `thesis` environment,
the Prometheus private key, and working SSH access. Private SSH keys were not
copied to Lustre or OneDrive.

## Post-bootstrap local footprint

After Prometheus job `294570` completed and its evidence backup passed a fresh
SHA-256 check:

- `/home/chris/thesis` was reduced from 9.7 GiB to 3.0 GiB;
- one-time Python/Conda caches, test environments, and the duplicate OCI tar
  were permanently removed;
- the only file left under `/home/chris/thesis/tmp` is the validated 3.14 GB
  local SIF backup;
- the exact thesis PyTorch Docker image was removed, while unrelated Gaea,
  Mongo, Node, and Mailpit Docker assets were preserved;
- a 336 KiB, 45-file smoke evidence backup with its own passing hash manifest
  is stored at
  `/home/chris/thesis/backups/prometheus/2026-08-08-hi-lewm-smoke-294570`.

The WSL filesystem reports 28 GiB in use. Its VHDX remains 45,310,017,536
bytes because Windows requires administrator permission for `Optimize-VHD`;
the attempted compaction was denied and no unsafe sparse-VHD override was
used. The distro was restarted and both the backup hash check and Prometheus
SSH access passed afterward.

One incomplete Windows-side transport archive remains at
`D:\THESIS-TEMP\container-build\pytorch-2.5.1-cu121.tar` (1,421,450,240
bytes). Native PowerShell deletion was blocked by application policy and the
Windows-control runtime could not execute actions. It is not used by WSL or
Prometheus and can be deleted manually.
