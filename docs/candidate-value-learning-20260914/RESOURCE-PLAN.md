# CVL-1 resources and storage

Proposal only. [COST-PLAN.json](COST-PLAN.json) is generated arithmetically by
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
CPU training: three 87,681-parameter MLPs + one 620-parameter logistic control,
40 epochs each, at most 12,288 training rows. For the maximum row count, 48
minibatches/epoch gives 1,920 updates/model, 7,680 total. No proposer/adapter/LeWM
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
- CPU training maximum two wall-hours at four cores/8GiB = eight core-hours;
  stop if exceeded. No training-GPU reservation is assumed.
- Before dispatch, require completed+currently-reserved+next full job reservation
  to fit the aggregate cap. Queue wait is recorded but not charged as GPU time.
  Ambiguous submission is a stop, never an automatic duplicate submission.
- Record Slurm allocation seconds, end-to-end worker and per-phase time, actual
  physics/call counts, host sampled MaxRSS, PyTorch allocated/reserved peaks and
  serialized byte counts. Neither sampled MaxRSS nor PyTorch peak is total node
  memory or total device VRAM. Do not reduce RAM from historical sampled peaks.
- First four training refs are a technical throughput/storage stage inside the
  fixed sample. Do not use their success outcomes to tune the sampling/model.

## Artifacts and backups

Proposed remote root (not created or submitted):
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

## Readiness boundary

This preparation provides a tested feature/sampling/model/metric core and an
opt-in observer-selector hook, plus a concrete execution contract. The real
collection loader, persistent result writer, frozen-driver glue, sealed aggregate
analyzer and approval-gated dispatcher still need implementation and preflight
against that contract before launch. There is deliberately no real-execution CLI
in the new files. Approval should authorize completing that bounded glue, not
waive it or allow changing this scientific design after outcomes are seen.
