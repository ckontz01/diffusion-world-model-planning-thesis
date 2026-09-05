# PushT continuation: design and feasibility package

Status: **preparatory analysis complete; no confirmation protocol frozen, no
confirmation manifest selected, no confirmation evaluation launched.**

## Decision

The currently permitted exposure ledger leaves **82 distinct, metadata-eligible
PushT episodes**, not 400/600/800. All 82 have unknown exact LeWM training
membership. None is eligible for a training-disjoint comparison with official
SAGE. This is a qualified capacity count, not a certificate that every future
physical-value check will pass or that no unregistered exposure ever occurred.

**Recommended feasible option:** use all 82 in one paired five-arm, H75/H150,
three-fixed-training-seed study, with the narrower purpose and inferential
assumptions below, *only if that limited-sensitivity objective is approved*.
Retain equal allocation to all five arms. Plan 2,460 episode-runs and a proposed
six-A6000-hour resource allowance, not an automatic allocation.

**Do not approve this as an adequately powered five-percentage-point
confirmation.** Under the optimistic historical variance inputs its probability
of establishing both +5-point true improvements is only 19%. The appropriate
decision is **no-go for the original five-point-sensitivity objective with the
currently available pool**. A larger design requires a count-only certificate
for additional protected allocations or a separately approved source of data;
extra seeds or starts do not solve the episode shortage.

## 1. Availability and exposure

Read-only metadata came from the pinned global partition registry, HDF5
episode-length metadata, permitted identifier arrays in the recorded P2
exposure stores, E14/E15/E17 training/validation identifiers, E16/E18 query
identifiers and the official SAGE split/paper manifests. No prospective state,
pixel or action values were loaded; no model was run on these episodes. No
eligible-episode list, selected start, or confirmation manifest was written.

| Global partition | Distinct episodes | Length at least 151 | Treatment here |
|---|---:|---:|---|
| P0 | 51 | 20 | Exclude baseline-exposed partition |
| P1 | 13,109 | 2,977 | Exclude training/validation partition conservatively |
| P2 | 1,930 | 453 | Apply episode-level exposure exclusions below |
| P3 | 1,810 | 406 | Exclude whole protected partition; D3/D4 membership not opened |
| P4 | 1,785 | 386 | Exclude whole protected partition; C1/I1 membership not opened |

The length criterion permits one common nonnegative start with both goal
indices `start+75` and `start+150` inside the episode. It does not count multiple
starts as multiple episodes. Metadata declares float32 state[7], proprio[4],
action[2] and uint8 224x224 RGB images. Missing block dynamics retain the accepted
R3 defaults; no new restoration analysis or coefficient fitting was performed.
Prospective finiteness and exact field-value checks remain deferred. Therefore
82 is the **metadata/exposure-qualified maximum**, potentially reducible at
approved pre-evaluation validation, not an unconditional guaranteed final N.

| Ordered exclusion from the 453 long P2 episodes | Newly excluded | Remaining |
|---|---:|---:|
| Earlier P2 candidate-pool/execution exposure | 357 | 96 |
| D1 fresh-development episodes | 1 | 95 |
| R0 | 0 | 95 |
| E14/E15 selected P2 queries | 4 | 91 |
| E18 P2 queries | 3 | 88 |
| E14/E15/E17 training/validation and E16 development | 0 additional | 88 |
| Exposed SAGE paper manifests and reused sentinels | 6 | 82 |
| Explicit R1/R3/driver counterexamples | 0 additional | **82** |

Exclusion counts are incremental, not independent sets to add twice. The first
line checks 128 earlier P2 identifier stores plus four pool stores, covering
1,538 distinct previously exposed episodes overall. The original 579 SAGE
"common untouched candidates" excluded E14–E18 exposure only; it is **not** an
H150-compatible, globally unexposed confirmation count. Subsequent diagnostics
reuse paper/sentinel records, and R3/integration reuse the three explicit
counterexamples. This audit is conditional on the completeness of that recorded
exposure lineage; unknown/unregistered uses are not asserted absent.

### Known versus unknown learned-component exposure

- Remaining overlap with the inspected E18 proposer/adapter training and
  validation sets: **0 of 82**. This also follows conservatively from removing P1.
- Official SAGE split among those 82: **73 training, 9 validation, 0 test**.
- Exact LeWM checkpoint episode membership: **unknown for all 82**. Its
  [pinned model card](https://huggingface.co/quentinll/lewm-pusht/blob/22b330c28c27ead4bfd1888615af1340e3fe9052/README.md)
  identifies the PushT dataset, not an exact realized episode-training manifest.
  The [pinned LeWM training repository](https://github.com/lucas-maes/le-wm/tree/8edfeb336732b5f3ce7b8b210d0ba370a09e2cac)
  documents the `pusht_expert_train` training input. Dataset-level provenance
  does not prove which individual episodes this checkpoint consumed.
- Consequently **0 episodes are certified unseen by every learned component**.
  This does not mean all 82 are proven LeWM training episodes. The feasible
  claim is conditional on the shared pretrained world model and documented
  planner-training disjointness, not all-model training-disjoint generalization.

### Reserving data for SAGE

Reserving all currently eligible SAGE-test episodes reserves **zero** and leaves
82 for E18. Reserving 20, 40 or all 82 of these would leave 62, 42 or zero for
E18, but would still create **zero training-disjoint SAGE episodes**: they are
already in SAGE training/validation. Do not pay that opportunity cost under a
false clean-SAGE claim.

There are 406+386=792 H150-compatible episodes in the **excluded** P3/P4
partitions before their protected allocations and exposure exclusions. These
are metadata upper bounds, **not available sample sizes**. No custodian's
intersection/exclusion certificate was available for releasing any of them;
none is included in 82. This package neither opened their protected memberships
nor manufactured a certificate by running an unrestricted reader. The separate
[count-certificate request](E18-PROTECTED-COUNT-CERTIFICATE-REQUEST-2026-09-05.md)
specifies the counts needed if expansion is considered. The 400/600/800 designs
are infeasible **under current permissions and certified availability**, not a
claim that no possible future allocation can supply them.

## 2. Historical episode-level planning inputs

The sealed E18 240-cell/720-row analysis was verified before reading its already
exposed PushT outcomes. PushT contributes 360 rows: **12 distinct episodes**, one
start each, five arms, two horizons, three fixed training seeds7201/7202/7203.
No seed-run is treated as an independent episode. If multiple starts existed,
the analysis would average them within episode before estimating variance.

For episode i and arm a, define `Ybar(i,a) = mean over H75,H150 and the three
fixed training seeds of success(i,a,H,seed)`. The paired contrasts are
`D1=Ybar(VAD continuation)-Ybar(VAD greedy300)` and
`D2=Ybar(VAD continuation)-Ybar(Gaussian continuation)`.

| Quantity | D1 | D2 |
|---|---:|---:|
| Historical mean | +11.111 pp | +11.111 pp |
| Sample variance (proportion squared, denominator11) | 0.07239057 | 0.10269360 |
| Leave-one-episode-out mean range | +6.061 to +13.636 pp | +6.061 to +16.667 pp |
| Leave-one-episode-out variance range | 0.045960–0.079293 | 0.072222–0.112626 |
| Exploratory episode-bootstrap variance 95% percentile range | 0.017466–0.117845 | 0.017466–0.188552 |

Covariance is **0.05218855**; correlation **0.60528868**. Removing episode16150
reduces both means to +6.061 pp and covariance to0.023737; removing14514 reduces
the Gaussian contrast substantially. Covariance across all leave-one-out fits
ranges0.023737–0.060101. Every episode's paired values and every deletion are in
the machine-readable planning report.

**These are uncertain planning inputs from twelve development episodes and the
older evaluation interface.** Endpoint, fresh rendering and initialization
semantics differ in the proposed interface. The bootstrap is itself unstable
at N=12 and cannot establish transportability of the variance or correlation.
Neither the +11.1-point mean nor a favorable bootstrap bound is treated as the
expected confirmation effect. No historical result or decision is amended.

## 3. Primary claims and exact simulated procedure

Two separately reportable primary claims:

1. The equal-episode/equal-horizon/fixed-three-seed mean success of unchanged VAD
   continuation exceeds VAD greedy300: null `mu1 <= 0`.
2. The same mean exceeds diagonal-Gaussian continuation: null `mu2 <= 0`.

For each contrast, compute the episode mean, sample standard deviation with
denominator N−1, and `T=mean/(SD/sqrt(N))`. Reject its one-sided null iff
`mean - t(0.975,N-1)*SD/sqrt(N) > 0`. This is Bonferroni allocation of a nominal
family alpha0.05 to two one-sided alpha0.025 tests. A claim that **both** controls
are beaten requires both tests to reject; a single rejection establishes only
that named comparison. This is not an unadjusted conjunction-only test.

**+5 pp is the simulated TRUE effect against zero, not an observed-estimate
threshold.** For example a precise observed +3 pp can establish superiority; an
uncertain +8 pp may fail. An improvement of at least5 pp would require a
different null/margin and is not a claim authorized by this design.

This proposed Student procedure explicitly replaces the earlier outline's
percentile-bootstrap gate for planning purposes; no frozen analysis has been
changed. It is an approximate episode-level procedure, conditional on
exchangeability/independence of distinct episodes after the filters, not an exact
finite-sample distribution-free test. The catalog mean of a census of82 fixed
episodes is directly descriptive; generalization beyond it requires the
episode-population assumption. No finite-population correction is used to
artificially improve power. Checkpoint seeds are fixed, not sampled training
replicates for a population-of-seeds claim.

Greedy576 and direct-GMM continuation remain fully evaluated secondary controls;
their contrasts and intervals are descriptive, without extra unadjusted
confirmatory claims. Beating greedy300 does not by itself establish equal-compute
superiority: continuation spends additional candidate rollouts. Greedy576 helps
separate that issue, but delta15 final chunks also differ in nominal budgets.

## 4. Power, precision and false-positive simulations

20,000 Monte Carlo replicates per design/scenario/null configuration, RNG seed
2026090502. Each sampled unit is a *paired episode contrast*, on the feasible
1/6 grid obtained by averaging six binary outcomes per arm. The common VAD arm
imposes `|D1-D2|<=1`; the simulation enforces this. Maximum-entropy distributions
match the stated means, marginal variances and covariance to at most1e-7.
They are planning scenarios, not fitted models of fresh-interface behavior.
The actual Student rule above is evaluated on every replicate.

Each ordinary scenario includes `(mu1,mu2)=(.05,.05),(0,0),(0,.05),(.05,0)`.
The bounded extreme uses shared D1=D2 in{-1,+1}, giving variance0.9975 at+.05
and correlation1; its incompatible mixed-null configurations are explicitly
not simulated. Empirical correlation is retained for the2x/4x scenarios;
the0.25-variance scenarios vary correlation independently.

| N | Available now? | Scenario | Power vs greedy300 | Power vs Gaussian | Power for both |
|---:|:---:|---|---:|---:|---:|
| **82** | Metadata-qualified maximum | Historical variance | 38.05% | 28.43% | **19.34%** |
| 82 | Yes, qualified | 2x historical variance | 22.06% | 16.39% | 9.20% |
| 82 | Yes, qualified | 4x historical variance | 13.21% | 10.71% | 4.93% |
| 82 | Yes, qualified | Variance0.25, rho0 | 14.42% | 14.43% | 2.16% |
| 82 | Yes, qualified | Variance0.25, rho0.5 | 14.61% | 14.37% | 5.35% |
| 82 | Yes, qualified | Bounded extreme, rho1 | 7.30% | 7.30% | 7.30% |
| 400 | **No** | Historical variance | 96.00% | 87.86% | 86.15% |
| 400 | No | 2x historical variance | 74.09% | 58.46% | 51.61% |
| 400 | No | 4x historical variance | 45.35% | 33.92% | 25.02% |
| 400 | No | Variance0.25, rho0 / rho0.5 | 50.93% / 51.81% | 51.59% / 50.78% | 26.58% / 34.68% |
| 400 | No | Bounded extreme, rho1 | 17.17% | 17.17% | 17.17% |
| 600 | **No** | Historical variance | 99.48% | 96.91% | 96.64% |
| 600 | No | 2x historical variance | 89.55% | 77.12% | 73.26% |
| 600 | No | 4x historical variance | 62.22% | 47.73% | 39.34% |
| 600 | No | Variance0.25, rho0 / rho0.5 | 68.69% / 68.66% | 68.42% / 68.36% | 47.22% / 53.72% |
| 600 | No | Bounded extreme, rho1 | 24.52% | 24.52% | 24.52% |
| 800 | **No** | Historical variance | 99.96% | 99.27% | 99.23% |
| 800 | No | 2x historical variance | 95.76% | 87.56% | 85.73% |
| 800 | No | 4x historical variance | 74.35% | 59.48% | 52.50% |
| 800 | No | Variance0.25, rho0 / rho0.5 | 80.68% / 80.67% | 80.84% / 80.42% | 65.02% / 69.64% |
| 800 | No | Bounded extreme, rho1 | 29.60% | 29.60% | 29.60% |

Monte Carlo SE is at most0.354 percentage points for these power estimates;
uncertainty in the development variance and interface change is much greater.

Expected margins subtracted to form the simultaneous one-sided lower bounds:

| N | Historical D1/D2 | 2x historical D1/D2 | Variance0.25, either contrast | Extreme |
|---:|---:|---:|---:|---:|
| 82 | 5.89 / 7.02 pp | 8.34 / 9.94 pp | 10.97 pp | 21.95 pp |
| 400, infeasible | 2.64 / 3.15 pp | 3.74 / 4.45 pp | 4.91 pp | 9.82 pp |
| 600, infeasible | 2.16 / 2.57 pp | 3.05 / 3.63 pp | 4.01 pp | 8.01 pp |
| 800, infeasible | 1.87 / 2.22 pp | 2.64 / 3.14 pp | 3.47 pp | 6.93 pp |

An individual two-sided95% interval has twice the displayed margin as its total
width; those two-sided intervals are not jointly95% simultaneous intervals.
At4x historical variance the D1/D2 margins are11.80/14.07 pp at82,
5.29/6.30 pp at400,4.31/5.14 pp at600 and3.73/4.45 pp at800.
At N82 the approximate **marginal**80%-power detectable effects are8.42/10.03 pp
using historical variances,11.91/14.19 pp at2x, and16.85/20.07 pp at4x.
Those are not effects with80% joint power. The feasible study can detect some
larger effects and estimate directions/magnitudes; it cannot reliably rule out
or establish five-point differences.

Across the simulated global nulls, family-wise rejection ranged2.425%–5.080%.
The maximum5.080% has MC SE0.155 pp (rough95% MC interval4.78%–5.38%). The
largest partial-null false-positive rate was2.710%. These checks do not reveal
a large family-wise inflation in these scenarios, **but do not certify a
universal finite-sample guarantee**. Lattice discreteness matters: in the N82
perfectly correlated extreme, each identical test rejects2.87% under zero,
rather than exactly2.5%, although family-wise error remains2.87%.

If a distribution-free finite-sample guarantee is required, a conservative
Bonferroni Hoeffding lower bound for D in[-1,1] subtracts
`sqrt(2*log(40)/N)` (30.0 pp at82). That is a clearly less sensitive alternative,
not a post-outcome switch or a way to manufacture five-point feasibility.
Every scenario's precision, actual matched moments, null checks and MC error
is retained in [planning.json](e18-design-feasibility-evidence/planning-v1/planning.json).

## 5. Workload and resource cost

Independent computation batch1; up to three independent GPU workers, not
vectorized-batch3 throughput. Per distinct episode: five arms x two horizons x
three training seeds = **30 episode-runs**, at most450 planning calls and6,750
delivered primitive actions. H75 budgets150 actions/10 calls; H150 budgets300
actions/20 calls. All runs use fresh policy/solver/RNG lifecycle.

A bounded calibration on the stored exposed8908/53 input, seed7201, A6000gpu09
(job300309, completed0:0 in55s including tests) performed80 solver calls: four
remaining durations x five arms x(one warmup+three measurements). No evaluation
episode was executed and no performance rate was computed. Accepted model
tensors were hash-identical before/after. Median preparation+solve wall seconds:

| Arm | delta15 final chunk | Largest measured long-branch median |
|---|---:|---:|
| VAD greedy300 | 0.0719 | 0.0717 |
| VAD greedy576 | 0.0720 | 0.0722 |
| VAD continuation | 0.0717 | 0.1282 |
| Gaussian continuation | 0.0460 | 0.0764 |
| Direct-GMM continuation | 0.0460 | 0.0765 |

These batch1 timings are not the historical batch3-amortized timings. They are
single-input resource proxies, not benchmark timing claims. All unmeasured
long durations use the largest measured long median. Same-architecture seeds
7202/7203 are extrapolated, not newly calibrated.

| N | Episode-runs | Max planner calls | Max primitive actions | Planner wall hours | Central allocated GPU hours | Conservative envelope |
|---:|---:|---:|---:|---:|---:|---:|
| **82** | **2,460** | **36,900** | **553,500** | **0.84** | **1.70** | **4.93 h** |
| 400, infeasible | 12,000 | 180,000 | 2,700,000 | 4.09 | 8.07 | 23.63 h |
| 600, infeasible | 18,000 | 270,000 | 4,050,000 | 6.14 | 12.07 | 35.39 h |
| 800, infeasible | 24,000 | 360,000 | 5,400,000 | 8.19 | 16.08 | 47.15 h |

Central allocated hours assume5ms per native action/physics/render,50ms reset
and record I/O per run,15 persistent arm-seed workers, measured loading plus10s
process overhead per worker. **These overhead coefficients are assumptions,
not measurements.** At82,2ms and10ms/action give1.24 and2.47h;50% of maximum
planning/action work at5ms gives0.89h. The conservative envelope doubles the
entire10ms scenario. It is not a confidence interval or a performance-selected
early-termination forecast. Three GPUs imply an optimistic central0.57h wall
time, excluding queue/imbalance. A six-GPU-hour allowance is proposed only.

Keeping all arms is inexpensive here: primary arms account for1,476 runs and
the two secondary arms984. Evaluating secondary arms on half the episodes
would reduce total run count by20%, **not necessarily measured compute by20%**;
their costs differ. No allocation reduction is recommended or implemented.
For a total budget B, the proposed six-hour allowance would leave B−6h for
future work; SAGE's new-interface workload is not calibrated or authorized.
Preserving compute does not repair the absence of a clean SAGE episode pool.

## 6. Completed technical regression coverage

The **unchanged** FreshEpisode and actual E18ScheduledPolicy were exercised with
a deterministic model-free solver, at H75/H150 and1/3 independent slots, through
two complete150/300-action budgets and another fresh initialization after
completion. Every chunk contains distinctive actions to check delivery order.

- Exact delta sequences `H,H-15,...,15`, repeated twice; tau15 throughout.
- Complete delivery of both final chunks, empty buffer and schedule exhaustion
  at the budget; no action or planner call after termination.
- Second cycle restarts deltaH; second episode restarts stage0 with a new
  policy/solver, and reproduces the same fixed action sequence.
- Single-slot and three-slot delivered sequences agree exactly.
- Existing tests retain natural termination, wrapper termination, missing
  explicit-reset failure, invalid-action failure and no legacy fallback.
- Separate real-solver timing calls exercised delta15 and both continuation and
  greedy long branches for all five arms; the actual short planning/action
  lifecycle remains covered by the accepted integration pass.

Four full-budget tests passed both locally and in the pinned remote swm006
environment. This test alone supplies model-free deterministic actions and
suppresses terminal flags so all chunks execute; it uses32px renders for test
speed. **Neither intervention is in production.** It is not an efficacy run or
full-budget real-model repeatability study. The existing short real-model RNG
ownership checks are preserved, not extrapolated into a new efficacy claim.
The remaining warning is Gymnasium's generic array coercion warning, not the
already-corrected signed-velocity declaration.

## 7. Proposed protocol and failure handling (not frozen)

- **Scope/initialization:** PushT only, equal H75/H150. Accepted instantaneous
  R3 reset and fresh driver required; legacy dataset evaluation forbidden.
  Same common start within each episode, goal indices start+H inclusive,
  separately fresh-rendered start and goal observations. Endpoint choice is
  not taken from legacy exclusive-end chunks. Physical missing-state defaults
  remain the documented assumptions. No normalization fit or redesign.
- **Allocation:** one start per distinct eligible episode, all five unchanged
  arms and fixed trained seeds7201/7202/7203. Selection rule proposed as
  outcome-independent salted-hash ranking of eligible starts within episode;
  salt, starts and final manifest are not chosen now. Initial planner RNG seeds
  derived from study/episode/start/horizon/trained-seed/purpose, independent of
  arm. Shared seed labels do not mean different arms consume identical banks.
- **Endpoint/outcome:** at most2H delivered primitive actions, stop on first
  native success or truncation or budget. Freeze the native PushT success rule
  (agent/block xy norm<20 and wrapped block-angle difference<pi/9), not unused
  coverage95%, before execution. No hidden reset step, clipping, policy reuse
  or fallback. Report failures separately from successful completion.
- **Infrastructure interruptions:** a documented node loss, preemption or
  transport interruption may receive at most two identical retries, preserving
  input/model/source hashes, seeds, resources, attempts and logs. Retry only an
  incomplete logical run, never a scientifically poor completed outcome. No
  best-attempt selection. Duplicate valid artifacts must agree under the frozen
  repeatability rule; otherwise stop and investigate technically while blinded.
  Repeated infrastructure noncompletion leaves the study incomplete; do not
  quietly remove episodes or replace them with exposed/reserve records.
- **Planner failures:** reproducible solver exception, invalid/NaN action or
  planner-specific resource failure under the fixed resource allocation counts
  as an unsuccessful run (Y=0) in the intention-to-evaluate primary outcome,
  with an explicit failure category/rate. Do not retry scientifically failed
  planning. Separate infrastructure evidence from deterministic planner failure
  using a predeclared classifier, not observed success. A sensitivity table can
  disclose these failures but may not remove them from the primary denominator.
- **Evaluator defects:** wrong reset, endpoint, action delivery, budget,
  observation or outcome computation invalidates the affected scientific
  measurements, not a planner score. Stop the affected scope, preserve all
  artifacts, determine scope from code/technical evidence while outcomes remain
  blinded, and seek an independently approved correction/protocol disposition.
  This is not an automatic all-grid rescue and not an infrastructure retry.
- **Information barrier:** no partial arm performance review or success-based
  tuning. Require complete expected identities, technical statuses and artifact
  seals before aggregate outcome release. An unresolved infrastructure/evaluator
  issue prevents confirmatory claims; it must not become silent missingness.

All new inference and retry decisions remain design proposals. The accepted
driver is untouched and does not implement an implicit retry coordinator.

## 8. Remaining approval choices

1. Accept a limited-sensitivity N≤82 study conditional on the shared pretrained
   LeWM and the recorded exposure ledger, **or keep five-point sensitivity as a
   requirement and do not execute yet**. No sample size is approved by this file.
2. If a larger or clean SAGE sample is wanted, obtain the requested count-only
   protected-allocation/exposure certificate; decide explicitly which remaining
   episodes and compute, if any, to reserve. Do not assume upper-bound counts
   are releasable or interpret SAGE training/validation episodes as held out.
3. Approve the paired Student/Bonferroni inferential assumption (or choose a
   separately planned stricter bounded-data procedure), all-arm allocation,
   failure classification/retry limits, and proposed six-hour resource allowance.

After—not before—those choices, prospective value validation, complete source/
checkpoint/endpoint/seed/procedure pins and the final independent protocol check
would precede any confirmation freeze/access. No confirmation preparation here
changes E18, E19, R1–R3, the driver, initializer or model checkpoints.

## Reproducibility

- [Metadata/exposure audit](e18_design_metadata.py) and [final count evidence](e18-design-feasibility-evidence/metadata-v3/availability.json).
- [Historical and simulation code](e18_design_power.py), [workload code](e18_design_workload.py), and [calibration evidence](e18-design-feasibility-evidence/timing-job-300309/timing.json).
- [Full-budget tests](test_e18_full_budget_lifecycle.py), [analysis regressions](test_e18_design_feasibility.py), and [implementation history](E18-DESIGN-FEASIBILITY-CHANGELOG-2026-09-05.md).
- [Read-only independent package verifier](verify_e18_design_package.py) and
  [verification record](e18-design-feasibility-evidence/VERIFICATION.json).
- New branch `e18-confirmation-design-feasibility`, parent286088e. All adjacent
  input seals verified; no historical decision file edited.
