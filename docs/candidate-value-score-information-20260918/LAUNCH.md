# SI1 launch — 18 September 2026

Researcher-approved prepared commit: `b1cfcdd8e062ca995feb439e4d8cefe2dac40f08`.
One submitted allocation: **301953**, job name `si1-score-info`, account `superworld`, partition `defq`, QoS `normal`, 4 CPUs, 8 GiB, 7,200 seconds, no GPU request/passthrough and `--no-requeue`.

Source: `/lustreFS/data/superworld/ckontzias/thesis/snapshots/candidate-value-score-information-20260918-68145e6458da0b90`.
Manifest SHA-256: `68145e6458da0b90255dd98e4fa2b9469dea12907797d7830c9bd233314be35c`.
Lineage SHA-256: `633be15376a195ee35ef33b72694638b20967ecb82be2658f1eb0367c9aee8c5`.
Execution approval SHA-256: `9cbddb0a9e19ab162961a38253efc0fefcc3e8936ec70a84cedbbe4955a23cef`.

Run parent: `/lustreFS/data/superworld/ckontzias/thesis/experiments/candidate-value-score-information-20260918`.
Exclusive output: `run-68145e6458da0b90`; approval/submission records and Slurm logs: `control/`.
Submission UTC Unix time: 1789684262.457796.
External backup destination: `D:/THESIS-BACKUPS/candidate-value-score-information-20260918/execution-68145e6458da0b90`.
THESIS_SSD identity `0a2f1ba9-0000-0000-0000-100000000000` verified, approximately 331 GB free, destination absent before launch.

Preflight verified all published package members, disabled template preservation, absence of prior named SI1 allocations and output namespace, and available site CPU partition. A pre-submission operational check initially treated the container Python symlink as a host executable; corrected it to verify the existing `/opt/conda/bin/python` symlink. The failed check created no output namespace or approval and submitted no allocation. Both launcher versions remain in staging; no prepared source/runtime or scientific setting changed.

The preceding local WSL connection fault was resolved by shutdown/restart after a checksum-verified external VHDX preservation copy. No account recreation or manual filesystem repair occurred. The preservation copy is infrastructure recovery, not an SI1 experimental artifact.

No retries or extra allocations. Partial scientific outputs remain unopened. Completion requires terminal accounting, seal verification and verified external backup before aggregate interpretation.
