# Resource proposal and assumptions

Recommend two fresh processes/reference:64 jobs,512 logical branch-to-budget
executions;256 unique comparisons-by-arm before repeats. Scientific n=32.
Models construct once/process, environments/policies separately for all8 branches.
No separate helper world is replayed: each arm's actual prefix is included below.
The first two reference1269 jobs are the technical pilot and count toward64.

|Upper bound|One repeat|Two repeats|
|---|---:|---:|
|Post-anchor actions|53760|107520|
|Prefix actions|3840|7680|
|Total physical steps|57600|115200|
|Post-anchor solves|3584|7168|
|Prefix solves|256|512|
|All solves|3840|7680|
|Full continuation solves|3328|6656|
|Cycle-final first-only solves|512|1024|
|Proposer batch calls|7168|14336|
|Diffusion network forward calls (5DDIM ×2CFG)|71680|143360|
|Current/goal encoder calls|7680|15360|
|State-adapter calls|3328|6656|
|Latent rollout batch calls|7168|14336|
|LeWM predictor calls (3macros/rollout)|21504|43008|
|Action-encoder calls|21504|43008|
|Candidate latent trajectories|1949696|3899392|
|Model constructions|32|64|
|Environment constructions|256|512|

Recomputed by direct enumeration in single_anchor_ranking.bounds and independent
test sums:32×2arms×(150+120+300+270)=53760;32×2arms×2horizons×30=3840.
Bounds include duplicate per-arm prefix planning for exact policy-state replay.
Encoder calls are top-level encode invocations, not image counts/layer calls.
Forward counts refer to the unchanged two-pass guidance implementation, not FLOPs.
State/goal image encoding within reset/render is NOT counted as model inference.
Timing/counts stop at native termination; no artificial padding after success.

## Empirical planning input — not new inference

COST-PLANNING.json reads only timing fields for the selected32 historical
reference rows/checkpoint7201 from the existing external archive. Each selected
shard is matched to the accepted combined receipt BEFORE parsing. No unselected
reference outcome is summarized; no protected or unevaluated payload accessed.
The new experiment has not run. The older common interface/cluster timing is an
uncertain planning input, not an established new-workload throughput guarantee.

790 observed full-continuation solves:mean0.131758s,p950.132262s,max1.284026s.
119 cycle-final first-only solves:mean0.072898s,p950.074115s,max0.080373s.
These synchronized wrapper solve times include CUDA/host planning but not complete
model construction/reset/physics/write/allocation overhead. The isolated maximum
is retained, not removed as an outlier. No old short-branch wall-time multiplier.

For two-repeat maximum call counts, add explicit UNMEASURED conservative allowances
of30seconds/process for construction/reset/hash/serialization plus0.02seconds per
physical step:1920+2304=4224seconds. These are allowances, not measured components.
New source verification/loading existing banks also consumes I/O/setup; first two
approved jobs are the bounded test of whether the assumptions remain adequate.

|Scenario|Planner seconds|Added allowance|Total allocation planning scenario|
|---|---:|---:|---:|
|Historical mean per solve|951.63|4224|86.26min|
|Historical p95 per solve|956.23|4224|86.34min|
|Twice historical p95|1912.46|4224|102.27min|
|Historical maximum at EVERY solve|8628.78|4224|214.21min|

Propose15min/job and4hours aggregate fail-stop GPU allocation, serial1A6000,
4CPUs/24GiB RAM unchanged. These scenarios leave uncertainty for load/I/O/runtime
instrumentation;4hours is a review ceiling, not a forecast or automatic extension.
If next full900s reservation cannot fit, stop with incomplete fixed grid. Charge
failures and timeouts before rejecting them; queue wait excluded. No retry.

RAM context: prior new56 batch MaxRSS max1.607899GiB, original pilot1.630GiB,
PyTorch allocated189994496bytes/reserved201326592bytes. These are NOT total
container/node RAM or total device VRAM. Retain24GiB until actual approved full
tail records establish their own accounting. Keep global tensor references only
for intervention evidence, not every tail candidate bank.

## Storage, verification, preservation

Store two intervention banks per anchor (one independently generated in each arm),
scores/latents, anchor physical/controller/pixels/goal, RNG states, decoded traces,
each selected plan, lifecycle diagnostics and hashes. Do not store all tail
candidate banks or videos. Approximate10–20MB/process,640MB–1.28GB/64, plus logs/
temporary/seals; exact image/history shape/compression affect this estimate.
Propose2GB run watermark and64MB dispatch reserve,64MiB per-file cap. Stop on
actual limits, never discard required arrays to fit. No silent data reduction.

NumPy-only verifier reads all64 adjacent seals before scientific arrays; compares
two processes at a time, independent saved arithmetic/full traces and repeat
bytes, then fixed reference-bootstrap. CPU2cores/4GiB,30min cap proposed; expected
minutes/I/O-bound, NOT extrapolated directly from44s short-branch verifier. Allow
a separate CPU-only10min import/synthetic preflight before real launch. CPU costs
and actual batch RSS/times/bytes are reported separately from GPU allocations.
External backup reserve6GB on healthy THESIS_SSD; preserve cluster originals and
hash-match backups. Source/compact receipts can stay in repo; no bulk laptop C:.

## Approval and launch sequence

1. Researcher approves this protocol/repeats and resource envelope (or requests
   explicit amendments before any new real inference/physics).
2. Freeze a separately named source package from the approved Git commit; include
   exact local Python import closure, pinned-input JSON, fixed selection, protocol,
   existing authenticated combined receipt and new tests. Verify full manifest,
   reviewed runtime-source hashes and protocol; reject CRLF shell wrappers. Record
   final source/protocol hashes in the explicit approval record.
3. Run proposed CPU-only import/synthetic preflight in the existing site-approved
   runtime. This is execution packaging verification, not a new research review.
4. Use approval-gated serial dispatcher. First two jobs provide16 branch executions
   and exact repeat gate; failures stop with evidence. Successful completed pilot
   jobs are reused, never repeated for labels or performance. Then remaining62.
5. After all64, proposed CPU verifier, source-matched backup, actual Slurm accounting,
   sealed descriptive report. Any defect gets localized without retuning outcomes.

This preparation has not created a launch approval, snapshot on Prometheus,
Slurm job, real runtime validation, controller or monitoring automation.
