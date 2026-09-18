# LGP1 implementation completion — 18 September 2026

Preparation only. Implements the reviewed study, not a new research direction.
**Correction receipt:** see `PRE-LAUNCH-CORRECTIONS.md` and
`CORRECTION-PACKAGE.json` for the three subsequent pre-launch fixes. The original
`LAUNCH-PACKAGE.json` and 22-test records identify the preserved reviewed package,
not the corrected source. Both remain execution-disabled.
The previous source, disabled approval and ten-test record remain available at
`63e1d9229492aa193c625fdf19c78200f4614f22`. No historical result is amended.
Continuation stays the baseline; no scorer/model is promoted.

## Executable component boundary

| File in `cluster/prometheus` | Responsibility |
|---|---|
| `prepare_lgp1_inputs.py`, `lgp1_contract.py` | Accepted metadata/input hashes, task grid, approval, seals and caps |
| `lgp1_data.py` | Identifier-hash row selection, authenticated Lance reads, exact chronological blocks, shared cache and fitting-only normalization |
| `lgp1_train.py`, `local_goal_models.py` | Actual full-batch data loop, NLL/velocity losses, backward/optimizer, final weights, fixed diagnostic validation |
| `lgp1_tensor.py`, `local_goal_proposals.py` | FP32 tensor CEM and independent NumPy reference, staged decoder affine, common support projection |
| `lgp1_runtime.py`, `lgp1_worker.py` | Frozen backend and fresh singleton episode adapter; no legacy dataset evaluation |
| `lgp1_dispatch.py`, `run_lgp1.sh` | Exclusive serial jobs, before-submit claims, reservations, terminal charges, freeze ordering and hard stops |
| `lgp1_verify.py`, `lgp1_aggregate.py` | Saved-array/normalization/model/episode checks and complete 32-source paired aggregate |
| `lgp1_preserve.py` | Final-only complete archive; member-level digest validation and designated-SSD backup |
| `lgp1_package.py`, `lgp1_test_evidence.py` | Complete deterministic LF source closure, disabled approval and reproducible synthetic evidence |

All code is connected through the worker and dispatcher. This claim does not
mean the real runtime has been exercised. The approved next execution, if any,
must first construct and verify the real cache; metadata capacity is not a
completed data-validity check. Actual distinct selected episodes/windows are
written by that cache job, not invented in preparation.

## Preserved scientific contract

The three normalization roles remain separate: frozen generator statistics;
new fitting-only state/action statistics common to both proposers; pinned LeWM
planner/decoder coefficients. Validation is never used to fit preprocessing.
Each expert row uses history t-10,t-5,t, far frame t+delta, and exactly the 15
chronological recorded actions t through t+14, packed into three five-action
tokens. Generated targets are not relabelled to recorded endpoints. Final local
stages use the actual far latent. Invalid rows stop; none is silently replaced.

Both proposers supply **only the first population**. Later populations are the
same Gaussian CEM. Thirty rounds, 300 candidates, 30 elites, sample std, stable
lowest-index ties and final elite mean are fixed. Per-round projection, duplicate
counts and predicted costs are logged, not new scientific conditions. Native
success with the unchanged fresh initializer and physical 2H budget remains the
primary endpoint. Actual histories and targets may diverge between arms after
different actions. Historical SAGE/continuation remain reference systems only.

Episode-owned RNG identifiers include reference, H, training seed, stage and
purpose. Proposal and refinement consumption are separated; streams and buffers
do not survive a new episode. No success-based technical gate or favorable
validation checkpoint selection has been introduced.

## Pre-execution corrections and synthetic findings

`review_dtype_reproducer.py` executes the immutable old reference on artificial
arrays: old CEM round dtypes are FP32/FP64/FP64 and old affine output is FP64.
The repaired reference fixes bank/noise/projection/reduction to FP32. The later
pre-launch correction also casts coefficients to FP32 **before** each affine
operation, as authenticated against the pinned cluster sklearn source. The
reviewed package's float64-arithmetic/FP32-store claim was incorrect; its local
sklearn comparison did not authenticate the cluster implementation.
Tensor/reference parity uses identical supplied noise, not equal RNG seeds.

The final mean receives the same support operation to handle floating-point
roundoff. Encoded boundary coordinates that decode a ULP outside [-1,1] move
inward with `nextafter`; no new physical bound or post-delivery clipping. GMM
sampling uses one inverse-CDF categorical draw per whole trajectory; this is the
same mixture distribution without a CUDA multinomial determinism dependency.

An artificial 16-row fitting role exposed a minibatch-wrap bug in the new loop:
one permutation was insufficient for a batch of 128. The iterator now appends
permutations until a complete batch exists. This affects no historical run;
the real 80k-row design was not executed. The regression verifies exact row
presentations on the small artificial case.

Focused tests cover both real loss/backward paths, artificial optimizer steps,
checkpoint/sample round trips, common context, trajectory-mode ownership,
all-round FP32 parity, decoder arithmetic, train-only statistics, history spacing
and padding, target reuse/switch, schedule restart without budget restart,
native termination through the unchanged driver with a fake World, independent
slots and fresh ownership. Orchestration tests mock all 204 tasks, freeze
ordering, charged failures, ambiguous submission, lost scheduler connection,
storage stops and retry rejection. Archive tests verify saved-member bytes and
reject corruption; aggregate tests require the entire paired grid.

`PIPELINE-TEST-RESULTS.json` records exact test counts and environment. Synthetic
optimizer work is six updates on artificial tensors only. No real checkpoint,
frozen inference, research optimizer, simulator, label generation or GPU job was
used. GPU kernel determinism, full-width memory, real cache values and end-to-end
site performance remain explicitly untested.

## Fixed grid and resource boundary

- Shared cache: one 14,400s GPU job, 80k fitting + 8k validation rows.
- Six fits: 14,400s each, 12,000 updates ×128 rows each; **72,000 updates and
  9,216,000 row presentations** total. Each fit includes all fixed validation.
- Four technical jobs: two horizons each, eight episodes total, 1,200s/job.
- 192 main jobs: two horizons each, **384 episodes**, 1,200s/job.
- Exactly **203 GPU allocations / 336,000 maximum GPU-allocation seconds**;
  one **4CPU/8GiB/7,200s** CPU analysis allocation. GPU jobs:4CPU/24GiB/oneA6000.
- Remote 12GB total including one archive; worker payload5.9GB, source/control/
  logs200MB,10MB per episode. No increases, retries, case replacements or resumes.

Measured-cost gates use timing only. They can stop even a scientifically
promising fit. A catchable interruption preserves `interrupted.pt` with model,
optimizer and completed update count as **evidence, not resumable authorization**.
A kill/OOM can prevent that file; partial files and scheduler terminal charges
remain. A failed final validation also stops, even if final weights were saved.
Ambiguous submission retains its full reservation and stops without resubmitting.
Healthy cluster execution never depends on laptop or SSD liveness.

The terminal controller record includes all allocations, including final CPU
analysis; worker CPU/RSS/timing records and the final aggregate are preserved.
Context/proposal/scoring/refinement and physical delivery timings are supporting
accounting, not equal-FLOP claims. Host archive/transfer times are separate.

## Source freeze and future commands — disabled now

`CORRECTION-PACKAGE.json` now binds the current source-manifest and INPUTS hashes;
`LAUNCH-PACKAGE.json` preserves the previous package identity. The manifest
itself is also published beside this document. The package root contains a
generated **disabled** `APPROVAL-TEMPLATE.json`; create a separate approval only
after the bounded launch decision. Do not edit the source package or preserved
old document template. The input lock binds permitted expert metadata, all
official model/simulator source files, accepted checkpoint/transport hashes,
the fixed container image and only the 32 allowed reference-file identities.
Source hashes are checked before jobs; payload bytes are checked inside charged
workers immediately before allowed use. No reserved payload is in the allowlist.

Reconstruct an identical package on a suitable local path:

```text
python cluster/prometheus/lgp1_package.py --output <new-exclusive-source-directory>
```

Only after explicit approval, stage that authenticated directory at
`/lustreFS/data/superworld/ckontzias/thesis/snapshots/lgp1-<manifest-prefix>`.
The remote dispatcher uses the pinned CPU Python runtime and standard Slurm
client. This command is documented, **not run in preparation**:

```text
<pinned-runtime>/bin/python -B <source>/cluster/prometheus/lgp1_dispatch.py --source <source> --approval <separate-approved-json> --run /lustreFS/data/superworld/ckontzias/thesis/experiments/local-goal-proposals-20260918/run-<manifest-prefix>
```

The dispatcher refuses any previous study namespace or prior `lgp1-` allocation.
Its approval check rejects the disabled template. All six final models are
sealed before technical/main evaluation; all 203 GPU tasks before aggregation.
Only complete aggregates may be interpreted, not partial outcomes.

After compute completes, run `lgp1_preserve.py archive --source <source> --run
<run>` on the cluster. Then run `lgp1_preserve.py backup --request
<run>/final-preservation/BACKUP-REQUEST.json` with Windows Python locally.
It requires THESIS_SSD volume `0a2f1ba9-0000-0000-0000-100000000000`, at least
40GB free and exclusive destination `D:/THESIS-BACKUPS/local-goal-proposals-20260918`.
It streams directly to the SSD and verifies every tar member without extracting
research payloads. No backup acknowledgement precedes real verification. Partial
transfers remain evidence; no automatic retry. Preparation creates source files
only, not a research launch or an authorisation to execute these commands.

The next review is the bounded launch decision for this implementation. A
positive development result would establish a conditional proposer-family
effect in this shared modified planner, not SAGE superiority, fresh confirmation
or novelty from diffusion plus local goals.
