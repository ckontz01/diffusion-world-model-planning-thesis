# Thesis storage layout

## Canonical working storage

Prometheus is the canonical location for datasets, released checkpoints,
containers, and experiment outputs:

```text
/lustreFS/data/superworld/ckontzias/thesis/
├── artifacts/       # Immutable third-party release archives
├── backups/         # Cluster-side snapshots of unique small artifacts
├── containers/      # Pinned Apptainer images
├── data/stablewm/   # Expanded benchmark datasets and model checkpoints
├── downloads/       # Resumable source archives; removable after verification
├── envs/            # Cluster software environments
├── logs/            # SLURM and staging logs
├── manifests/       # Sources, hashes, and migration scripts
├── results/         # Thesis experiment outputs
├── src/             # Hi-LeWM code and thesis-control documents
└── tmp/             # Disposable project staging files
```

Do not place bulk data in `/trinity/home/ckontzias`; that home directory has a
20 GB quota. It is reserved for SSH configuration and small shell files.

## External SSD retention

The external SSD retains only:

- the `Thesis-Ubuntu` WSL installation;
- SSH credentials and cluster connection configuration;
- thesis source, protocol, manifests, and small local development tools;
- selected copies of unique trained models and final result bundles.
- `D:\WSL\Thesis-Ubuntu-backup-20260807.tar`, a verified 14.5 GB recovery
  export of the compact WSL installation (SHA-256
  `6716df151938bd067d10571fb7f21f09a7618aec549ff4c31a1ed6dc7c01ed00`).

Public benchmark datasets, published checkpoints, and downloadable release
archives do not need permanent SSD copies once their Prometheus copies have
passed the recorded SHA-256 checks.

## Backup rule

Lustre is working storage, not the sole backup. Every irreplaceable experiment
output must exist in at least two independent locations. Use Prometheus plus
the external SSD or OneDrive for result tables, configurations, logs, and
selected final checkpoints. Public datasets may instead be reconstructed from
the pinned revisions recorded in
`cluster/prometheus/dataset-sources.tsv`.

Never copy private SSH keys to Lustre, Git, or OneDrive.
