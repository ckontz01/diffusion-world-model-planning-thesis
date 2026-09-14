# Proposed single-anchor ranking experiment — 14 September 2026

Status: implementation prepared; **researcher launch/resource approval required**.
No new real model, simulator or GPU execution is authorized by this preparation.
The completed32 diagnostic is accepted; no amendment, rerun or renewed acceptance
programme. This is outcome-informed development, not confirmation or SAGE fidelity.

## Question and fixed population

Does one immediate-ranking decision's first-chunk physical progress improve
eventual success under the SAME downstream continuation policy, or sacrifice
later opportunity? Preserve the original stopping decision
`stop_futility_strong_adverse_signal`, all models/checkpoints and artifacts.

Use exactly the existing BRANCH-PILOT-SELECTION.json ordering:
1269,582,525,722,567,716,630,1066,1074,1565,70,867,221,905,1287,621,
428,288,1488,757,641,855,1280,420,860,98,886,432,181,783,706,989.
H75/H150; absolute anchors0/30; training checkpoint block7201. All128 historical
anchors were available in the accepted receipt. Unexpected unavailability is a
technical mismatch to report, not permission to substitute a case.

256 logical branches =32 references ×2 horizons ×2 anchors ×2 selectors.
Recommend two fresh processes per reference, each containing all8 branches:
64 processes,512 branch executions. Repeat0 alone supplies scientific effects;
repeat1 checks exact arrays, not extra independent references.

## One decision, unchanged downstream policy

Each branch constructs the existing R3 fresh environment and a newly owned
original E18 policy/solver. The model weights may be shared read-only within the
process; policy objects and proposal/GMM generators may not be shared. Reproduce
the historical initial image/state/goal hash. Replay from original initial_request
through the ACTUAL historical continuation policy to the selected absolute anchor,
checking actions, selected-plan hashes, physical/controller state and lifecycle.
Every t30 branch starts from historical t0, never a t0 treatment trajectory.

At the anchor, call the original E18 continuation solver once. Its existing
encode/propose/adapter/rollout calls are observed without changing their outputs:
64 first chunks and64×8 continuations, original raw goal latent, and original
adapter/normalization. The solver already computes immediate squared latent cost
and original mean-of-lowest-two continuation score. The hook reconstructs those
two scores with the SAME torch expression and production continuation_score in
both arms; asserts that the original returned plan equals continuation argmin.
The continuation arm returns that same plan; immediate returns its immediate
argmin plan. First-index ties and all production arithmetic remain unchanged.
No extra model call or random draw is introduced by choosing a different index.

Verify regenerated intervention raw/planner banks, predicted/scoring latents,
raw/normalized inputs, costs, original scores and post-bank proposal RNG against
the authenticated saved diagnostic banks. These are recorded diagnostic banks,
NOT historical benchmark banks (which were not recorded). Historical benchmark
selected plans, lifecycle hashes and action/state traces are separately checked.

The original policy enqueues/decodes/delivers the selected first15 actions and
increments its stage normally. It is NOT replaced/reset at the hand-off. If the
chunk remains active, the policy replans from actual new observations at the next
absolute stage, using original continuation for the ENTIRE remaining budget.
Never use immediate selection again, execute the imagined second chunk as a tail,
force shared future actions/banks, or introduce a score weight/new tail/value model.
Cycle-final stages with delta15 retain the original first-only fallback; this is
part of unchanged continuation policy, not a second experimental intervention.

## RNG, schedule and state contract

Independent branches use the same historical seed and separately owned generators.
Prefix solves consume the historical sequence; intervention solves consume the
same two proposal draws. The saved post-bank proposal state must match exactly.
Both arms must have identical proposal/GMM and global torch CPU/CUDA states at
this boundary; score/index extraction is checked not to change them. The active
hand-off retains this proposal/GMM state: delivery of buffered actions must not
consume proposal randomness. Subsequent draws are coupled by corresponding
absolute planning stage and generator stream, without reseeding; candidate values
may diverge because actual observations differ. Early terminal branches stop and
do not consume unused future draws. No post-terminal equalization workload.

No new environment restoration logic or clearing of guessed physics internals.
Fresh construction + prefix replay carries native physical/controller/contact
history. Current observation state must equal the actual environment state;
goal pixels remain exact. At common anchors check controller/physical state with
rtol0/atol1e-10, and paired images/goals exactly. After same-index selection,
paired coupled traces/actions and non-timing lifecycle fields must match exactly.
The continuation control must reproduce the full historical tail: selected plan
hashes, RNG/schedule, actions, state (existing tolerance), length and native outcome.
Any genuine mismatch stops for diagnosis; no tolerance relaxation or rerun rescue.

Original absolute environment budget2H, schedule delta=H-(elapsed mod H), tau15.
Remaining budgets INCLUDING intervention chunk:

|Horizon|Anchor0|Anchor30|
|---|---:|---:|
|75|150|120|
|150|300|270|

At active hand-off, absolute time is anchor+15, buffer empty, stage=(anchor+15)/15.
Do not reset the budget or horizon cycle. Native termination/truncation ends the
branch immediately, including during the first chunk. No legacy dataset evaluator.

## Endpoints and analysis specified before execution

Primary: native success at any POST-action step from intervention through the
remaining original budget, including the first chunk. Exclude initial anchor
state. Retain the historical SAME-step predicate: combined four-coordinate
agent/block Euclidean position error<20 AND circular angle error<pi/9.
Angles admit the reviewed state endpoint2pi but goals remain strictly canonical;
no clipping/normalization/relaxed threshold. Offline flags must equal this predicate.

Secondary, reported separately: first-chunk success and closest joint margin;
margin at action15 hand-off for active branches with terminal-first cases explicitly
separate; closest joint margin over all post-anchor execution; delivered actions,
all/prefix/tail planning-call counts, native truncation and budget exhaustion.
Joint margin is same-step max(position norm/20, angle error/(pi/9)). Active-hand-off
descriptions are not survivor-filtered estimates of the primary effect. No primary
success analysis restricted to first-chunk survivors. No threshold tuning.

Average fixed anchors inside each horizon, then equal H75/H150 inside reference.
Require the complete fixed grid, no imputation/exclusion/replacement. Report all32
reference effects, horizon/anchor details and paired success wins/losses/ties at
both anchor and reference level (these levels are not interchangeable). Positive
success difference = immediate minus continuation; positive margin improvement =
continuation minus immediate. Two process repeats do not double sample size.
Use one designated repeat0, fixed10000 reference-bootstrap percentile95% intervals,
NumPy seed20260914. Exploratory development only; no multiplicity-controlled
confirmatory rejection rule, equivalence, all-task superiority or SAGE claim.
Sparse success is reported honestly; continuous endpoints do not replace primary.

## Independent acceptance and information barrier

Until all64 jobs complete successfully, inspect only scheduler/exit status,
existence/size/checksums; no partial scientific-result interpretation. After exact
failure is reported, inspect only that job's technical logs. Preserve its outputs;
no automatic retry, changed parameter, case substitution or budget expansion.
Repeat1 workers compare their saved arrays against their sealed repeat0 before
success, exposing only pass/failure through job status. This is a technical gate,
not partial effect analysis. First two jobs (reference1269 repeats0/1) are the
bounded technical pilot INSIDE64 jobs, not additional runs or success-based selection.

Then run the prepared NumPy-only verifier: all adjacent seals first, full source
and protocol identity, authenticated historical/prior inputs, exactly8 rows/process,
both repeats byte-identical, exact decoder dtype operations, independent squared
costs at unchanged rtol2e-6/atol1e-5, original-score ties, all stored plans decoded
to delivered actions, absolute schedule and RNG linkage, full caps or native
termination, no post-terminal steps, historical control and paired same-choice
identity, reconstructed physical/planning counts. Write a NEW sealed aggregate.
Normalizations/banks are exact against accepted saved arrays, not probe-fitted.

Runner assertions, independent saved-array checks and repeat equality are distinct.
The offline verifier does NOT regenerate neural outputs or hidden physics state.
An artifact assertion gap is not automatically evidence of a scientific defect;
localize it without changing frozen execution or thresholds after seeing outcomes.

## Resource contract proposed for approval

One A6000 at a time; existing approved Apptainer/Python3.11/swm006 runtime,
4CPUs,24GiB requested RAM,15-minute cap per reference/repeat allocation.
Do not shrink requests based on batch MaxRSS or PyTorch allocator peaks.
Aggregate GPU allocation review envelope14,400seconds (4hours), including failed
and timed-out allocations; exclude queue wait. Before dispatch reserve the full
next900seconds plus any outstanding reservation against actual charged seconds.
Stop if it cannot fit; do not silently enlarge. No automatic resubmission.
All64 worst-case individual caps would total16hours: the aggregate envelope is a
fail-stop ceiling, NOT a promise that all64 can finish if jobs approach their cap.

2,000,000,000-byte new run-root watermark (logs/temp/seals/banks included), reserve
64,000,000bytes before each dispatch;64MiB per-file cap. Poll size15seconds;
on overflow cancel ONLY current job, preserve reservation until terminal charge
is reconciled, and stop. This watermark may transiently overshoot, not a quota.
Controller interruption/ambiguous submission leaves evidence/reservation and requires
manual diagnosis, never automatic restart. No unattended process is started now.

Proposed post-grid CPU verification allocation:2CPUs/4GiB,30-minute cap, separately
reported, not hidden in GPU allowance. Pinned-runtime import/synthetic validation
before first real job is a proposed CPU-only10-minute-cap step; no real model or
physics in that preflight. Serial GPU pilot jobs must pass the runner's complete
real bank/replay/lifecycle tests and exact repeat gate before remaining dispatch.

New cluster root:
`/lustreFS/data/superworld/ckontzias/thesis/experiments/single-anchor-ranking-20260914/<approved-source-prefix>`.
Future read-only source snapshot separately named single-anchor-ranking-<commit>.
No original output is writable in the Apptainer ROOT:ro / newRUN:rw binds.
Backup all new sealed artifacts plus source/contract/accounting on healthy external
`D:/THESIS-BACKUPS/single-anchor-ranking-20260914/`; reserve6GB external free space
for run/analysis/source and safe copy margin. No bulk C:; do not overwrite pilot,
extension, historical archive or three unrelated E12 drafts. Hash-match scientific
bundles against the remote sealed receipt and report log-transport limitations.

See RESOURCE-PLAN.md and COST-PLANNING.json for independently counted work and
historical timing scenarios. The approval file must bind the final frozen source
manifest, this protocol hash, repeats2, job900s, aggregate14400s and storage2GB.
No approval file granting execution is created by this preparation.

## Forbidden scope

No training/checkpoint selection, architecture/adapter redesign, context replacement
arm, hybrid tuning, alternate tail, new cases, GMM/SAGE benchmark or confirmation.
Only selected32 inside exposed0–1599; never read payloads1600–5999 or protected
D5/D3/D4/P3/P4/C1/I1. Do not resume the terminated independent benchmark controller.
Return the concrete code/tests/protocol/resource plan for approval, then stop.
