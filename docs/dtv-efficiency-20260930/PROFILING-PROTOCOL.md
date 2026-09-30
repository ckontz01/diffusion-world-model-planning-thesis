# DTV-EFF0 profiling protocol — disabled

`EXECUTION-APPROVAL.json` has execute=false. The current instruction permits
only artifact recovery, implementation, artificial CPU tests and publication/
small-package preservation. A new explicit execution instruction and its
recorded provenance, matching package-manifest and binding hashes, are
required. Merely flipping a field is not authorization. No monitor exists.

## Fixed grid and inputs

Nine serial workers: PushT/Reacher/Cube × existing scorer seeds
6101/6102/6103. All exact checkpoints and source/runtime inventories are in
`BINDINGS.json`, `SOURCE-AUTHENTICATION.json`, `FINAL-RECOVERY.json` and
`evidence/AUTHENTICATED-BYTES.json`. No fastest-seed selection. Each worker
uses D1 capture rows 0/1 with exact historical episode/start/goal identities:
six distinct contexts and 18 context/seed pairs. No role is reallocated and
no saved payload is opened in preparation. The metadata manifests pin both
candidate banks and saved predicted-trajectory artifacts. A separate A-only
reconciliation lane uses all 50 existing v3 pools (15,000 sequences), never
pretending this is a production-size planning call.

Five fixed policies: plain goal; historical reconstructed ACID (v3 independent
per-candidate/transition noise, λ=.07); deterministic forward (v3 λ=.005);
legacy DTV .10/.25/.50 (v3 λ=.005); D1 single-noise .25 (original λ=.07).
No new mathematical scorer, compiler, quantization, training or lower-budget
sweep. This is the disclosed historical reconstruction, not official ACID
code. A later success–cost study would require reasonable lower-budget
ACID/forward/plain points, but no broad sweep is designed or launched now.

## Three separately reported boundaries

A: checker alone on identical saved 300×5 predicted trajectories/actions,
native normalization/noise/reductions. No dummy plain-checker cached-output
timer. v3 offline A reconciliation uses original 8,192-transition chunks and
300-sequence warmup. B: original single-rollout complete cost call on identical
saved candidate actions, including goal encoding, rollout, reductions and
required diagnostic CPU work. C: released 30-round CEM, 300 samples/30 elites,
five grouped transitions, original final-elite mean, from saved preprocessed
pixels/history/goal to returned standardized planner actions. Physics,
raw-image preprocessing and physical action inverse-processing are excluded.
Missing pixels/goal or latent-cache inputs are a blocker, not a substitute
boundary. The original interface performs image encoding; no encoding cache
is added by this package.

Same captured context and newly owned private planner stream (seed 7101)
for each arm. Reset means/variance and RNG before each solve; matched first
draws, but later action banks may diverge when scorer choices diverge. No
cross-arm population forcing or reuse of a changing score. D1's noise bank is
reconstructed from its exact seed/shape; v3 ACID uses cost-call-index keys.
Level A uses the first-production-call index 1; its offline reconciliation
uses the original 8201 planner key (warmup index 0; measured index 1).

## Timing and equivalence

Five cyclic Latin-order blocks, two repetitions per block, each arm once in
each position. Two contexts per worker. Three warmup calls for A/B and one
warmup solve for C, reset before measured calls. Fixed counts; no adaptive
stopping on favorable timing. Two offline reconciliation repetitions per
ACID/forward/legacy worker arm after one 300-sequence warmup.

Separate synchronized wall and CUDA-event time around the complete call or
solve. No inserted inner-kernel synchronization. Original per-round CPU cost
conversion, diagnostics and final copies/print stay charged. Empty-boundary
control is reported, not automatically subtracted. Extra hashes and audit
work are outside hot timers with separate cost records. Raw records,
median/IQR/p95/p99, absolute ms saved and ratios are reported per task/seed/
context/level; no mixing of boundaries or outcomes. Runtime repetitions are
not independent success samples.

Model-loading/setup is timed separately. First operational B calls and first
C solves are measured before their equivalence/solver warmup, separately from
post-equivalence reset calls and warm blocks. Shared Le-WM and reused DTV
weights may already be warm from earlier arms; these are explicitly first
**operational** calls, not an assertion that every arm is simultaneously on a
cold physical device. Additional warmup never advances the measured stream.

Untimed original-vs-transparent-wrapper checks cover raw scores, independent
scaling/reductions, exact top-k indices, returned elite mean and planner RNG.
Legacy DTV is independently compared with the v1 raw callable using the same
noise bank. Saved B0 costs and trajectories must reproduce. Original justified
rtol=atol=1e−6, exact discrete indices/RNG; no tolerance relaxation. Artificial
CPU tests exercise original copied source and original released CEM, not a
made-up efficacy target. Real-runtime equivalence remains a future technical
gate, included in the proposed allocation, not a preparation inference run.

Pin Python 3.11.10 / torch 2.5.1+cu121 / stable-worldmodel 0.0.6 and recovered
source hashes, existing container/env, FP32 parameters/inputs, inference mode,
four CPU threads, no autocast, deterministic algorithms, cuDNN benchmark=false,
cuDNN deterministic=true, original CUDA defaults matmul TF32=false and cuDNN
TF32=true. Exact one visible NVIDIA RTX 6000 Ada Generation on the authenticated
gpu09/gpu09.cluster association; record actual allocation and UUID/properties
when available. Reject wrong name/host/task/allocation. No environment repair.

CUDA allocated/reserved peaks are per timed boundary; the resident scope
includes Le-WM, all three reused scorer models, selected inputs and allocator
cache. Report scoped process CPU and RSS high water, not total node memory or
whole-GPU utilization. These differ from old per-arm-only memory scopes.
Authentication/setup and equivalence-plus-warmup wall scopes are also saved;
the latter overlaps its separately timed first calls and must not be summed
with them. The original world-model loader receives the authenticated exact
checkpoint prefix. A colliding directory is rejected, preventing its original
"newest checkpoint in directory" fallback from substituting other weights.

## Full-work reservation and finite stops

Each worker: 4 CPU, 8 GiB RAM, one exact GPU, 800-second hard limit
(740 work + 60 preservation). Nine × 800 = **7,200 allocation seconds / 2 GPU
hours**, including model setup, equivalence and every failed allocation.
Serial dispatch reserves all remaining tasks before submission. No retries,
requeue, duplicate allocation, restart/resume loop, cap reset, role replacement
or config change. Any ambiguous submission stops with its raw response;
terminal failures are charged/preserved and require a new scoped decision.
An unsuccessful or unfavorable timing is not a repair opportunity.

Per worker: 100 timed C solves, 20 equivalence C solves, 10 first/reset C
solves and 10 warmup C solves = **140**, not episodes. Whole grid: 900 warmed
timed C solves and 1,260 total C solves / 37,800 CEM rounds, plus fixed A/B
and offline passes. All are saved-input inference only. Historical 1.6–1.81 s
CEM medians would put C work around 38 minutes aggregate, *if* transferable;
they do not establish future throughput. The full allocation ceiling remains
two hours. If the fixed workload reaches its soft limit, preserve failure;
do not shorten the protocol or expand resources.

4 MB per worker including profile, seal or failure; 36 MB workers, up to
20 MB package/control/log/analysis, 60 MB live; 62 MB archive reservation;
250 MB inclusive new timing artifacts, including retained failures. Existing
checkpoint/input bytes are read in place, not copied into the new archive.
CPU final acceptance/report/preservation preparation: at most 600 seconds,
4 threads/8 GiB, no GPU. This is proposed future work, not current spending
authority. Current preparation's separate limit is 7,200 local scripted
wall-seconds, four threads/8 GiB/250 MB, accounted in its receipt.

Independent acceptance requires exactly nine successful unique allocations,
full timing identities, all hashes, all finite charges, real equivalence and
no omitted cell. One new-study-only report is produced by `accept.py`.
Only this small profiling package/report/receipts/logs are to be archived,
transferred natively to designated THESIS_SSD and verified whole/member;
no historical study archive is retransferred. Keep every failure/partial;
no overwrite, deletion, fallback disk or automatic transfer retry.

## Frozen utility screen and decision

Candidate merit requires a complete-CEM **wall-time** saving of at least 10%
vs ACID in each task/seed/context median, reproduced at ≥10% in at least four
of five blocks for each cell. Also report event times and absolute savings,
and compare the retained plain and forward controls. Offline A alone cannot
advance the line. All smaller/negative results are still reported. This
stringent screen is research utility, not a theorem or a success/safety
guarantee. It does not grant a next stage, promote a model, amend old claims
or establish training/energy savings. A justified alternative latency/memory
constraint would need a separately frozen decision before timings, not a
post-outcome replacement for this criterion.

## Executable commands (no submission performed)

`python -m dtv_efficiency.campaign --run <exclusive remote run>` prints the
exact nine-worker plan without submission. `--submit` is blocked by the false
approval. A separately authenticated enabled approval outside the frozen
template must bind the package and input contract.

`python -m dtv_efficiency.profile --job pusht-6101 --output <exclusive path>`
is also blocked before importing torch or opening research tensors.
The real production entry point uses the existing environment through the
original Apptainer route in the generated plan. `accept.py` requires the full
completed ledger and seals. See `README.md` for current CPU tests and backup.
