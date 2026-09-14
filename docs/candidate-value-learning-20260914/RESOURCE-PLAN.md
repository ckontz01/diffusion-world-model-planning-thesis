# CVL-1 resources and storage

Implemented execution envelope; launch remains unapproved.
[COST-PLAN.json](COST-PLAN.json) is generated arithmetically by
`prepare_candidate_value_package.py`; it opens no research data or SSH connection.

## Workload ceilings, with prefix replay charged

128 collection refs ×2 horizons ×4 anchors ×8 candidates ×2 tail draws gives
**16,384 candidate branches**. Two tails share one observed feature/candidate row:
8,192 candidate rows from at most 1,024 first64 banks. References remain n=128,
not n=16,384. Unavailable late anchors reduce counts, never authorize substitutions.

Every candidate branch recreates its prefix from t0, so its complete physical
workload is bounded by 2H, even for the last anchor. Add one original prefix/bank
trajectory per ref/H; all 65 trajectories per ref/H are charged. No assumption
that a seven-field state setter reproduces a native in-flight world.

|Collection ceiling|Count|
|---|---:|
|Fresh branch episodes|16,384|
|Original prefix/bank episodes|256|
|Primitive steps including prefixes|3,744,000|
|All solver calls|249,600|
|Full continuation solver calls|216,320|
|Cycle-final first-only calls|33,280|
|Proposer batches|465,920|
|Diffusion network forwards (existing two-pass guidance)|4,659,200|
|Model constructions, once per ref/H job|256|

Closed-loop adds at most 512 episodes, 115,200 steps, 7,680 solver calls,
14,336 proposal batches and 143,360 diffusion forwards, with 32 model constructions.
CPU fitting: three 87,681-parameter MLPs + one 620-parameter logistic control
and one 620-stored-parameter context-only diagnostic,
40 epochs each, at most 12,288 training rows. For the maximum row count, 48
minibatches/epoch gives 1,920 updates/model, 9,600 total. No proposer/adapter/LeWM
optimizer, backpropagation or fine-tuning. Ensembling changes value inference cost,
not proposal count; record that cost separately.

## Measured inputs and uncertain projections

Use only the accepted historical report, without reopening its numerical/backup
investigation: 109,870 actual physical steps; worker wall sum 2,297.099s;
construction sum 437.505s; allocated 2,963s across 64 jobs; 6,386 continuation and
956 first-only solves. Prior observed mean solve times: .13175849s full,
.07289795s first-only; p95 .13226187s/.07411497s; maxima 1.284026s/.0803727s.
These are planning inputs, not evidence that a new label collector achieves them.

|Collection planning scenario|GPU allocation-equivalent hours|
|---|---:|
|Planner-only historical mean (excludes physics/I/O/setup)|8.59|
|Amortized historical worker overhead + measured construction/allocation overhead|18.80|
|Unamortized historical allocation/step ratio|28.05|
|Twice p95 solver cost + 20ms/step +30s/job allowances|40.20|
|Historical maximum at every solve + same allowances|100.83 — infeasible under cap|

The 18.80h calculation subtracts estimated solver work from historical worker
time, scales the remaining per-step overhead, and adds model construction and
per-job allocation overhead separately. It is an approximation because native
termination, reset cost, serialization and cluster contention can change. The
28.05h scenario carries the older frequent construction overhead per step and is
more pessimistic. Recommend budgeting **19–29h collection**, plus roughly 0.6–1h
closed-loop and preflight/accounting; this is not a promise. The 40.20h scenario
is a conservative allowance, not a measured bound. No currency estimate: no
verified Prometheus billing tariff is available. GPU-hours are the cost unit.

Per-job limits matter too: under that twice-p95/20ms scenario, an H150 job could
take about 12.5min, exceeding the proposed 10min job cap even though the aggregate
40.20h fits 50h. Thus the envelope is feasible under the historical-throughput
scenarios, **not guaranteed under every conservative scenario**. The in-sample
technical pilot can stop it as infeasible; it cannot silently lengthen jobs or
reduce the branch budget. The fixed sample need not be made to appear affordable.

## One bounded proposed launch envelope

- Serial single A6000; never multiple simultaneously running study workers.
- 256 collection jobs: one ref/H, at most 64 branches + original prefix,
  **10min/job**, four CPU cores, 24GiB requested RAM.
- 32 closed-loop jobs: one reference, both H, four arms, two seeds, **10min/job**,
  four CPU cores, 24GiB. These are conditional on the fixed validation gate.
- Two synthetic A6000 contract preflights, **5min/job**, same allocation shape.
- Maximum fixed reservations: **48h10min GPU allocation**. Aggregate hard ceiling
  **50h**, including failed allocations. The spare 1h50m is accounting headroom,
  not authority to add references, seeds, retries or an extra model search.
- Exactly three CPU jobs: fit all five models in 100 minutes, ranking analysis
  in 10 minutes, final closed-loop analysis in 10 minutes. Total maximum two
  allocation wall-hours at four cores/8GiB = eight reserved core-hours. Failed
  CPU allocations are included; no training-GPU reservation or extra fit exists.
- Before dispatch, require completed+currently-reserved+next full job reservation
  to fit the aggregate cap. Queue wait is recorded but not charged as GPU time.
  Ambiguous submission is a stop, never an automatic duplicate submission.
- Record Slurm allocation seconds, end-to-end worker and per-phase time, actual
  physics/call counts, host sampled MaxRSS, PyTorch allocated/reserved peaks and
  serialized byte counts. Neither sampled MaxRSS nor PyTorch peak is total node
  memory or total device VRAM. Do not reduce RAM from historical sampled peaks.
- First four training refs are a technical throughput/storage stage inside the
  fixed sample. Do not use their success outcomes to tune the sampling/model.

### Exact staged maximum

|Stage|Registered jobs|Maximum allocation|Maximum scientific work|
|---|---:|---:|---|
|Synthetic pinned-runtime preflight|2 GPU|10 GPU min|No reference episode|
|Initial training tranche, first four refs/both H|8 GPU|80 GPU min|512 tail outcomes + 8 prefixes|
|Remaining training collection|184 GPU|1,840 GPU min|11,776 outcomes + 184 prefixes|
|Five evaluator fits|1 CPU|100 CPU min|12,288 training rows, 9,600 updates total|
|Ranking-validation collection|64 GPU|640 GPU min|4,096 outcomes + 64 prefixes|
|Ranking analysis|1 CPU|10 CPU min|256 banks maximum|
|Conditional closed loop|32 GPU|320 GPU min|512 episodes|
|Final analysis|1 CPU|10 CPU min|32 paired source summaries|
|Total registered|293|2,890 GPU min + 120 CPU min|No exact-repeat or retry jobs|

Thus 50 GPU-hours includes all 290 GPU allocations: preflight, collection,
conditional closed loop, startup/authentication, I/O and any failed/technical
allocation. The 2 CPU-hours includes all five model fits, training-only feature
normalization, model serialization and both analysis jobs. It is a compute-job
allocation cap, not a claim that source packaging, scheduler polling, checksum
verification and SSD network transfer consume zero host CPU or finish in two
hours. Those control/transfer wall times are separately timestamped; no models
run on a login node or in the backup companion. Queue time is likewise separate.

Dispatch is serial. Actual terminal `sacct` seconds are charged before the next
reservation; a nonzero exit, ambiguous submission, storage failure or missing
accounting stops the run. A possibly live/ambiguous allocation retains its full
reservation in the log and must be reconciled manually, never resubmitted.
The pilot checks all eight completed jobs, no success-based early acceptance:
<=600 seconds each, <=16GiB sampled host RSS, projected collection payload <16GB.
The remaining 4GB is headroom for models, closed loop, logs and control artifacts.

## Artifacts and backups

Remote root template (not created or submitted):
`/lustreFS/data/superworld/ckontzias/thesis/experiments/candidate-value-learning-20260914/run-<sourcehash>`.
Source snapshot is separately named `candidate-value-learning-20260914-<sourcehash>`.
Neither the accepted single-anchor run nor historical source is an output target.

Keep bank64 feature/action arrays, sampled indices, declared sampling probabilities,
all-bank chunk hashes, prefix provenance, decoder/statistics hashes, RNG states
and observation hashes. Save anchor observation/goal images once per live bank,
not every candidate replay. Keep low-dimensional actual states/dynamics, delivered
actions, native flags and timestamps to audit labels; these are audit-only fields
in a separate group, never the trainer's feature matrix. Do not save all tail
proposal banks, video, image streams or model activations. Stream branch artifacts
to disk instead of retaining hundreds of live worlds/tensors.

Float32 feature64 matrices are approximately 162MB (1024×64×619×4); anchor image
pairs about 308MB uncompressed. At the full step ceiling, seven float64 state
fields are about 210MB, ten dynamic fields 300MB, float32 actions 30MB. Duplicated
checkpoints are not needed; pin original bytes once. These first-order estimates
suggest a low-single-digit GB payload, but actual schemas/compression/logs matter.
Use a conservative **20GB remote artifact ceiling**, with a 1GB next-job storage
reservation and actual per-job caps. No outcome pruning to stay under quota.

The 20,000,000,000-byte remote ceiling includes label/bank/trace files, evaluator
weights and preprocessing, receipts, Slurm stdout/stderr, temporary files,
technical/failed outputs and terminal evidence copies. A conservative 50MB of
that ceiling is reserved for source tar + extracted source + capsule/approval;
the dispatcher rejects a larger source/control package. A 1GB next-job reservation
is checked against used+reserved bytes. During a job, the monitor counts its
outputs, temporary directory and logs and cancels on observed excess; a process
file-size limit also applies. This is fail-stop monitoring, not an OS disk quota:
transient writes between 20-second checks can overshoot and are preserved, never
deleted to pretend compliance.

Backup target, only after approval/data generation:
`D:/THESIS-BACKUPS/candidate-value-learning-20260914/` on the external THESIS_SSD.
Require **40GB free** for payload + archive/verification headroom before launch.
Check the actual external volume identity; do not silently fall back to C: or
OneDrive. Small source/docs may stay in the recovery Git workspace. Preserve old
archives and reserves unchanged. Produce per-job SHA-256 seals, model/training
receipts, stage manifests, aggregate report, code/protocol archive and a
member-verified external copy. Store raw research artifacts outside Git; commit
small protocol/result/accounting manifests only. Back up train, validation and
closed-loop stages after sealing. No deletion of failed or unfavorable rows.

The implemented WSL companion checks both `/mnt/d` and volume label `THESIS_SSD`,
streams nonoverlapping sealed stages to exclusive tar files, verifies every
member without extracting a second copy, and acknowledges the exact request hash.
Completed terminal failures can be sealed and backed up without marking them
scientifically valid. Ambiguous/live allocations are not falsely sealed. A failed
transfer leaves its partial archive and stops; no automatic retry. The remote
20GB payload and its external backup are two distinct copies, not a 20GB combined
two-site limit. Forty GB external free space is the separate backup prerequisite.

## Readiness boundary

The selected-record collector, runtime glue, fit/serialization, ranking and
closed-loop analysis, hash-authenticated worker, staged dispatcher, source exporter
and external backup companion are implemented. Synthetic tests exercise the full
pipeline; actual pinned-cluster preflights and measured throughput are not claimed
to have passed. No research execution was launched. The next decision is approval
of this fixed envelope; deployment capsule checks and the registered technical
preflights remain mandatory and fail closed.
