# E18-FC1 fresh-interface confirmation — design ready for scope approval

**Status: not frozen, not executable, no holdout authorized.** The PushT
engineering prerequisite passed in job300308. This document does not reopen
that gate or request another initialization redesign. Two methodological
choices were presented to the user during integration and remain unanswered:

1. PushT-only H75/H150, or a two-task design retaining Cube behind a separate
   integration gate. The complete proposal below is PushT-only; Cube is deferred.
2. Minimum worthwhile improvement: proposed5 percentage points (alternative10).

These change the estimand/sample size, so silently committing one as the user's
confirmed protocol would be inappropriate. On approval, finalize those values,
seal this document and the pinned inputs/source references under a new immutable
FC1 protocol hash. Do not rewrite the older E18 outline, R3 or historical studies.

## Question, scope and claims

Does the unchanged E18 VAD continuation method improve success over both
VAD greedy300 and diagonal-Gaussian continuation under the new, explicit,
reset-independent PushT evaluation interface? Both H75 and H150 have equal
primary weight. Choosing PushT is an engineering-scoped, development-informed
choice, not a new two-task generalization claim or a replication of historical
SAGE fidelity. E17 remains failed; its unchanged adapter is a component of this
new planner-level hypothesis, not a retroactive gate pass.

All five historical E18 arms are retained unchanged:

- `vad_continuation`:64 first candidates,8 continuations each,mean of best2
  continuation costs. When remaining delta<30, use the frozen immediate score.
- `vad_greedy_300`:primary greedy control,300 first candidates.
- `diagonal_gaussian_continuation`:primary distribution-family control,64x8,
  identical continuation scoring and same adapter.
- `vad_greedy_576`:secondary compute-count control,576 first candidates.
- `direct_gmm_continuation`:secondary distribution control,64x8.

Do not add the earlier proposed greedy64 bank-sharing arm in this protocol:
it was not part of the unchanged five-arm integration and would require a
separately specified mechanistic driver. Equal RNG seeds do not imply identical
proposal banks across these arms; no such identity claim will be made.

## Pinned source, checkpoint and normalization inputs

- E18 planner source snapshot
  `/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e18-182ed1e7d1e99946`,
  manifest SHA256 `182ed1e7d1e9994638ab1fbc773c79cac8d68858b716e67ff8969e5b2e74e29c`;
  old protocol `aff490f3f000c7d9b261632dcd3ccfc76a630b2f44e41f78832c3719607b8459`.
- New driver snapshot `e18-fresh-integration-a9d1c26573158f93`, manifest
  `a9d1c26573158f93e3e17dba932129084795a05f2ac84eb7eaadb8bca881d540`.
- R3 initializer `798bb6749dd30b9c6a91ac7018422edbefd356f3bb6bc322bd8ca95987506a65`.
- LeWM checkpoint `c3883fb585f4d97b628922a13a43441fe63e883808014d25312aca1793820659`;
  loaded JEPA source `41bad7fd21e0f14aea4c9c3d39a9c87037e787746d953ab62cdc0677e938ce96`.
- E17 PushT adapter `c58726a3502bf52bbbaad6263c1f636ef393ecbd34835b021750f7451bed88b8`.
- Frozen E15 final-EMA training seeds7201/7202/7203 for each of VAD, Gaussian
  and GMM. Exact nine checkpoint paths/hashes and complete relevant coefficients
  are in `e18-fresh-integration-evidence/pins/PINNED-INPUTS.json`, sealed hash
  `cf48fd85336fbf4d65f12ef290cd3b08f3969da2c8a29842ece4c55e848f52df`.
  All nine hashes were rechecked; their normalization payloads are identical.
  This inventory read existing training checkpoints only, no dataset records.

No refitting: use checkpoint latent/state/u/planner-action coefficients and
the exact sealed R1 float64 action decoder. Use current/goal images and raw
state, not evaluator-side non-action scalers. Action block5; primitive plan
duration15; exact inherited diffusion schedule, evaluations, guidance, GMM
sampling and adapter architecture. The new protocol cannot tune any of these.

Runtime: existing E18 py311/cu121/stable_worldmodel006 environment in the pinned
Prometheus Apptainer image; A6000. Native source hashes:

```
world.py   15fc9e4a69d2ad81d29ca8fedd689b53e96887f7614fa98223ef5ddee37bbda6
wrapper.py 9d7298d987fb509d52e2b6423b6938d12ae20eefcdcc2d720f315729ed44f417
policy.py  37a55735dd169f5200c79b61b760664deb996e3704d416831a3dea12102b9e7a
PushT env  d8d0de35aaab5b846db4e79b0fbfd6b17375178cce40a25df5301c8030ca6d68
```

## Prospective records and endpoint contract

No candidate/holdout identifier is selected, generated, read or hashed now.
Only after explicit record-access authorization, an independent identifier-only
provenance gate must establish episode disjointness from all model/adapter/LeWM
training, prior evaluation and exposed engineering inputs, including all three
R1/R3 smoke episodes. If complete LeWM training identity cannot be certified,
stop and state that the intended fresh population is unavailable; do not
silently substitute a weaker disjointness claim.

The previously generated579 PushT common untouched candidates are not an
authorized FC1 set or proof that the proposed sample size is feasible. Do not
open protected D5, D3/D4 outcomes, P3/P4/C1/I1, or infer an authorization to
access their identifiers. Any necessary custodian exclusion certificate requires
separate authority; no forbidden outcome read is allowed by this draft.

Proposed record algorithm after authorization:

1. Freeze exact source dataset bytes and complete eligible/excluded episode-ID
   certificates. Eligibility depends only on recorded field availability,
   finite values, schema and length, never planner outcomes.
2. Eligible episodes must contain at least one start with a recorded endpoint
   at start+150. Rank eligible episodes by SHA256 of UTF8
   `e18-fc1-pusht-20260905|episode=<decimal-id>`, tie by numeric ID.
3. Select the fixed N episodes. Within each, rank valid starts with salt
   `e18-fc1-pusht-start-20260905|episode=<id>|start=<index>` and choose the first.
   The same start is used for both horizons, every arm and training-seed block.
4. Store explicit start and goal indices: H75 means exactly75 index transitions,
   goal=start+75; H150 means goal=start+150. Use inclusive endpoints. Seal IDs,
   input record hashes and the resulting execution registry before any planner
   sees confirmation records. Missing capacity stops; no automatic downsizing,
   replacement dataset or selected-subgroup analysis.

The R3 reset contract assigns recorded seven-dimensional start state, with
documented canonical zero defaults for unrecorded dynamics. Render fresh start
and goal images from the explicit states. Do not advance physics during reset,
overlay historical JPEGs, suppress collisions, choose a reset seed by outcomes,
or call the legacy dataset evaluator afterward. This new inclusive endpoint /
fresh-render convention is disclosed, not called identical historical E18.

## Episode execution and RNG lifecycle

PushT budget2H primitive actions (150 or300), including the action that first
causes termination. Fresh reset is decision0/time0 and consumes no action.
The unchanged schedule uses15-action blocks; after each H-action cycle it
restarts the original delta schedule if the episode is still active. Stop
immediately at native termination/truncation or action-budget exhaustion.
No zero-action success is awarded at reset: the native predicate is evaluated
after delivered steps, as in the validated driver. Invalid actions fail; no
clipping, legacy fallback, extra settling or automatic retry.

Native success: `norm(goal[:4]-state[:4])<20` and wrapped absolute angular
difference<pi/9. This includes agent and block xy, not block-only distance or
the unused coverage-threshold member. Primary Y=1 if native termination occurs
within budget; Y=0 on budget/native truncation without termination. Never
replace this predicate based on observed results.

Use one fresh policy/solver/RNG per episode, frozen shared networks, computation
batch1, at most three interleaved independent slots per GPU process. Fresh
episode proposal and GMM seed: inherited `derived_seed` applied to UTF8
`e18-fc1|task=pusht|episode=<id>|start=<index>|h=<H>|train_seed=<seed>`;
omit arm so blocks are paired. Use that same seed for the explicit environment
reset; wrapper ID generation has no computational dependency. Keep deterministic
Torch settings and no random data transforms. No solver state/caches from a
completed episode may be reused. Any registered launcher must bind exactly
this driver contract and pass the existing synthetic lifecycle regressions
before record-access authorization; it may not call a dataset evaluator.

## Proposed estimand, sample size and inferential gate

The proposal is a **+5-percentage-point minimum worthwhile estimate**, with
two primary superiority comparisons. This value is a design choice, not an
estimate taken from development. For episode e and control c define:

```
D[e,c] = mean over H in {75,150} and seeds {7201,7202,7203}
         of (Y[e,H,seed,vad_continuation] - Y[e,H,seed,c])
Delta[c] = mean_e D[e,c]
```

Proposed N=3,200 distinct episode clusters. A conservative normal-approximation
calculation uses Var(D)<=1, one-sided Bonferroni alpha=.025 per comparison and
80% marginal power for superiority at Delta=.05:
`ceil((1.959964+0.841621)^2/.05^2)=3,140`, rounded upward to3,200.
This is a worst-variance planning approximation, not exact bootstrap power or
80% power for the joint practical-effect gate. At the exact worthwhile-effect
boundary, requiring the point estimate>=.05 further limits pass probability.
No effect/discordance estimate from the smoke is used. A +10-point alternative
would require a different, separately agreed N; do not amend N after outcomes.

This deliberately exposes the resource/feasibility consequence:3,200 episodes
x2 horizons x3 fixed training seeds x5 arms =96,000 closed-loop episode runs,
not96,000 independent samples. No compute expenditure is authorized now.
If the required fresh population is unavailable or this cost is unsuitable,
revise the design before freeze/access, not after inspecting a smaller run.

Bootstrap20,000 resamples of whole paired episode clusters, fixed NumPy
PCG64 seed20260905, resampling the same cluster indices across both contrasts.
Keep both horizons and all three trained-checkpoint blocks together. Use
percentile2.5% one-sided lower bounds per primary contrast (Bonferroni family
coverage at least95% in the bootstrap approximation). Joint primary confirmation
requires for **both** controls: Delta>=.05 and lower bound>0, plus all technical
validity gates. Report each contrast regardless of pass/fail. No optional
stopping, post-hoc weighting or protected-data-informed power recalculation.

Report per-horizon results and greedy576/GMM contrasts with descriptive paired
95% intervals, clearly secondary/nonconfirmatory. Fixed trained checkpoints are
blocks, not independent evidence about a training-seed population. No pooled
episode-run binomial interval pretending all96,000 runs are independent.

## Technical validity, information barrier and timing

Require exact source/checkpoint/normalization/input identities; every registered
cell and episode; current initialized observations; no hidden reset steps;
legal finite decoded actions; exact schedule and budget accounting; no stepping
after completion; correct fresh policy/RNG state; finite encoder/adapter/cost
outputs; all frozen E18 candidate uniqueness/boundary/continuation validity
checks from the pinned analyzer's per-stage validation. In particular no
illegal or exact-boundary raw actions, first-candidate minima285/548/61 for
greedy300/greedy576/continuation, and at least7 unique second candidates. Timing
must be finite/nonnegative with the unchanged component method disclosed.

A failed execution preserves artifacts and blocks the barrier. Diagnose exact
technical logs only; never rescue a scientific/validity failure. Any required
technical correction gets a separate immutable source/protocol amendment and
user approval before a complete replacement grid; no selective cell selection.
No partial performance file is opened before every cell terminates successfully
and the sealed analyzer passes identities/completeness. Then release **all**
aggregate outcomes, including negative ones.

Report synchronized end-to-end planner latency at computation batch1,
unchanged CUDA-event component times, CPU preprocessing, simulator/rendering,
whole episode elapsed time and peak allocated CUDA memory. No three-slot
amortized timing may be presented as one-request latency. Warm up using one
fixed exposed case0/H75 planning call per arm/process, discard its timings and
construct fresh episode policy/solver/RNG before confirmation. Retain first
confirmation episode timing; no data-dependent timing exclusions. Timing
comparison is secondary, not a workaround for a failed success gate.

## Authorization boundary

Integration is passed and complete. The final protocol freeze awaits the
explicit scope/effect design choices above; no new restoration work is needed.
After freeze, dataset eligibility/registry certification and a separate explicit
launch authorization are still necessary. No author contact, full SAGE grid,
E18-versus-SAGE run, new model or automatic confirmation access is authorized.
