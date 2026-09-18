# LGP1 approved execution launch, 2026-09-18

Published correction/execution binding commit:
`9059d1f830be33c47aa77b3c026850e61a122b14`, pushed and read back from the remote
`local-goal-proposer-preparation-20260918` branch before submission.
The earlier pre-submission stop and packages remain preserved.

## Verification and immutable identities

- Checkout: 32 synthetic tests passed, zero failures/errors.
- Export: 32 synthetic tests passed, zero failures/errors; source seal verified
  before and after. No real-model inference or simulator run in these tests.
- Actual cluster host Python 3.9.6 imported the dispatcher without NumPy;
  source closure and separate execution approval verified.
- Source manifest SHA-256:
  `b514472d1d8a7f55b71b14b00000613b253db4737883aa5dd6850151a5e7dff2`.
- Unchanged INPUTS SHA-256:
  `b21bac97520696b8bb2008a3cfef3f5188d4c59dd117bc158cc2fe2e86ff5aaa`.
- Source archive SHA-256:
  `5d8273207cbf1d8c7db1d5145a429198f9d0435af4151ffe006f07ed8a000f14`.
- Actual uploaded execution approval SHA-256:
  `94a43338bcf4f98ea5cb615a565caa775cb7b89bb4fbc13e64462b5abe5f2961`.
- No prior LGP1 namespace or Slurm attempt before this launch; no old task was
  restarted. Source 961250 bytes, initial staging 1004774 bytes before
  generated host preflight/controller records.

## Cluster execution

All paths below are under `/lustreFS/data/superworld/ckontzias/thesis/`:

- Source: `snapshots/local-goal-proposals-20260918-b514472d1d8a7f55`.
- Control: `staging/lgp1-execution-b514472d1d8a7f55`.
- Run: `experiments/local-goal-proposals-20260918/run-b514472d1d8a7f55`.

The control directory contains the source tar, actual approval,
`HOST-PREFLIGHT.json`, exclusive `LAUNCH-INTENT.json`,
`CONTROLLER-PROCESS.json`, and controller stdout/stderr. Controller PID
2969990, Linux start ticks 851068991, launch Unix 1789753800.9892585.
The process identity was read back and matched; it was sleeping normally,
with no STOP record and empty controller stdout/stderr at the first check.

First submitted allocation: **301977**, task `cache`, submission Unix
1789753801.2406104. Slurm read back RUNNING, 4 CPUs, 24G RAM and one GPU;
elapsed 29 seconds at this initial snapshot. The 0:0 field on a RUNNING job
is not a terminal-success assertion. No partial scientific output was read.

The detached controller owns serial dispatch and scheduler waits independently
of laptop/SSD connectivity. Fixed limits remain 203 GPU jobs, 336000 GPU
allocation seconds, one 4CPU/8GiB/7200-second analysis allocation, six fits,
72000 updates, eight technical and 384 main episodes, and the existing storage
caps. All six models freeze before evaluations. Technical failures stop;
there is no automatic retry or resumption authority for this study.

## Preservation and pending completion

THESIS_SSD volume `0a2f1ba9-0000-0000-0000-100000000000` was verified with
331263406080 bytes free before packaging. The new source export and
member-verified tar reside in
`D:/THESIS-BACKUPS/local-goal-proposals-20260918/preparation-host-import-20260918`
and the adjacent `.tar`. Historical packages/templates were not overwritten.
This is a source backup, not a final research-output backup. Complete output
seals, model-freeze ordering, full endpoint/grid evidence, accounting and final
member-level SSD preservation remain required before the final report. Include
these staging/controller records in final control/log accounting and backup.
No result, efficacy claim, model promotion or further experiment is recorded.
