# Execution stopped at mandatory CPU preflight

Decision: `stop_technical_preflight_failed`. This is not a scientific outcome.

The researcher approved the exact prepared experiment at
`dd0d2bc716e73d49f5d7cf5acf298adc34573032`. The scientific implementation and
protocol remain unchanged. Launch-support commit
`983ce24fa2d543d15d3b03aeb03c0f1510b23ffd` adds only Git-byte packaging,
CPU preflight checks, and the recorded approval. No historical file was amended.

## Frozen execution identity

- Snapshot: `/lustreFS/data/superworld/ckontzias/thesis/snapshots/single-anchor-ranking-20260914-6087d3c4fc304cef`.
- Source-manifest SHA-256: `6087d3c4fc304cef436665b4c849ec0b2a7ac5da3b4db02415f11e7352d9478b`.
- Protocol SHA-256: `43830bd18fcf8cf3d986cbd71d5bb8d5df0dee8fd7c88356c5070b5d76c8a1ae`.
- All 41 manifest entries verified on Prometheus. Source files are archived as
  read-only files; neither frozen source nor execution outputs were overwritten.
- Git-exported protocol bytes use LF. The actual frozen-byte hash is the one
  bound in `EXECUTION-APPROVAL.json`, not a Windows working-copy hash.
- The snapshot includes the approved local import closure, fixed selection,
  authenticated prior combined receipt, input pins, tests and launch-support code.

## Actual preflight and diagnosis

CPU job **301088**, partition `defq`, QoS `normal`, account `superworld`, requested
2 CPUs / 4 GiB / 10 minutes. It ended `FAILED`, exit `1:0`, after 7 seconds.
Both adjacent JSON seals were checked before interpreting their reports.

The existing host scheduler-control interpreter, `/usr/bin/python3` (3.6.8),
cannot import the prepared dispatcher: `ModuleNotFoundError: No module named
'numpy'`. The dispatcher imports `single_anchor_ranking` and
`verify_diffusion_extension`; their numerical import chains require NumPy even
though scheduling itself needs only metadata, hashes and standard-library tools.
This dependency boundary was a defect in the prepared implementation. Local
tests had NumPy installed, so those tests did not establish host compatibility.

The **same job's pinned-container preflight passed** all actual worker, verifier,
dispatcher and runtime imports and all **18 synthetic tests** (0 failures/errors).
It used the approved `hi-lewm-artifact-py311-cu121-swm006` environment in the
existing image: Python 3.11.10, NumPy 2.2.6, torch 2.5.1+cu121. No environment
substitution or upgrade was made. No checkpoint, model constructor, simulator
or reference payload was invoked. Imports and synthetic tests do not validate
real bank regeneration, physical replay or historical-tail identity.

The dispatcher was not started, no GPU job or technical-pilot branch was
submitted, and no experiment run root or monitoring process was started. The
failure was reported before its exact technical logs were read. No retry occurred.

## Accounting and preservation

Charged GPU allocation: **0 seconds**. CPU allocation: **7 wall-seconds × 2 CPUs
= 14 allocated CPU-seconds**; Slurm observed TotalCPU was 4.772 seconds. These
quantities have different scopes. Requested RAM was 4 GiB. Slurm reported batch
MaxRSS 3,464 KiB and extern MaxRSS 1,368 KiB; these short-job sampled step values
must not be treated as total container/process-tree memory or used to reduce the
memory request. No PyTorch CUDA allocator or total VRAM measurement exists.

The five preflight output/seal/log files total **7,978 bytes**. Frozen source
archive: **614,400 bytes**. Source-plus-approval-plus-preflight evidence archive:
**645,120 bytes**, backed up on the healthy external `THESIS_SSD` with matching
remote/external SHA-256
`c661bbcee5948b3dc01954de5ba4f1407f7deaf12f641d8d6999062e6d700b17`.

Backup: `D:/THESIS-BACKUPS/single-anchor-ranking-20260914/preflight-evidence-301088.tar`.
A separate non-sparse `BACKUP-RESERVE.bin` reserves exactly 6,000,000,000 bytes on
that SSD. Cluster originals and the frozen source archive are preserved. No bulk
data was written to C:. The three unrelated E12 drafts remain untracked and intact.
See `PREFLIGHT-301088.json` for the machine-readable receipt and report/log hashes.

## Narrow proposed remedy, not executed

Separate scheduler metadata validation (fixed identifiers, approval, manifests,
resource limits) into a standard-library-only host import boundary while keeping
all numerical/model/physics work in the unchanged pinned container. Preserve the
same manifest, approval and fail-stop checks; do not merely bypass validation or
install packages in the host environment. This would require a new source freeze
and an explicitly authorized replacement CPU preflight, retaining failed job
301088 and its accounting. It is not a scientific design change.

No repair, replacement preflight, automatic retry, GPU pilot, new experiment,
or resource-envelope expansion was launched after the failure. There is no
primary or secondary experiment result to report: all 512 approved branch
executions remain unexecuted. The next action is resolution of this specific
launch blocker under the no-retry rule, not another general research review.
