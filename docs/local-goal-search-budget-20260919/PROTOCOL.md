# LGP-RB1: frozen-model common-refinement budget comparison

Status: preparation only, 19 September 2026. Research execution is disabled.
This is the one outcome-informed development follow-up requested after the
accepted LGP1 record `f42c189b2e18968303dee5a733cf670d2301a657`. LGP1 is not
amended. Continuation remains the working baseline; neither proposer is promoted.

## 1. Question and sole scientific change

Does the relative closed-loop usefulness of the frozen local-goal GMM and
diffusion proposers depend on common CEM refinement effort? Compare total
**scored populations 1, 5, 30**, not one initial population plus that many
updates. Each population contains 300 candidates; take 30 elites by the
unchanged stable ascending cost order and return the **projected final elite
mean** at every budget, including one population. No best-candidate arm.

The six final LGP1 checkpoints, input statistics, 32 development references,
training seeds 8301/8302/8303, horizons H75/H150, local-target generator,
LeWM and cost, 15-action local chunks, normalization/decoder, FP32 CEM,
support projection, fresh initialization, observation/history, schedule,
physical budgets 150/300 and endpoint are unchanged. No new training,
optimizer updates, data collection, scalar evaluator, CFG or extra arm.
Native SAGE and the continuation planner are not executed as comparators.

## 2. Frozen identity and historical reuse

`REUSE.json` identifies the actual executed LGP1 source manifest
`b54a55b16bcb83a5092f15703a63fadb81fdbce3fa91f4e6a21b907c934cf361`, input lock
`b21bac97520696b8bb2008a3cfef3f5188d4c59dd117bc158cc2fe2e86ff5aaa`, six
individual checkpoint bytes and seals, original all-six freeze
`a8a5a0ff456cd870e540f838d2c8b62d00b542be6d7a2da53b377fbd91cbc305`, canonical
approval, aggregate and all 192 original two-horizon worker seals/tasks.

The source manifest and exact runtime were recovered from the accepted,
member-authenticated final archive, not inferred from a proposed checkout.
`LEGACY-RUNTIME.py.txt` retains the executed runtime verbatim. Nine unchanged
scientific modules, six checkpoint files, source manifest and model freeze
were also byte-checked directly on Prometheus: 17 matches recorded in
`REMOTE-BYTE-COMPATIBILITY.json`. No checkpoint was deserialized or run for
that preparation check. The new export retains every other scientific file
in the old source closure, with only the explicit Policy budget/log extension.
The already accepted Windows preservation-path correction is also retained.

All 384 historical 30-population main episodes are reused with their original
source, approval, model and worker provenance. They are not fresh observations
or new resource charges. Their original records and endpoint evidence remain
unchanged. Authentication is repeated before any future submission and at
complete aggregation. Future technical compatibility is an execution gate,
not a substitute for historical provenance or a success-based filter.

## 3. Exact source roles and grid

The exact ordered 32 development source identifiers are in `REUSE.json` and
the unchanged LGP1 `DATA-ROLES.json`. No identifier selection by outcome.
`GRID.json` is executable, deterministic and contains:

| Stage | Allocations | Queries / episodes |
| --- | ---: | --- |
| First-decision compatibility | 2 GPU, one per family, seed 8301, source 1269 | 16 first-decision queries; zero delivered actions or completed episodes |
| Budget 1 main | 192 GPU | 384 new episodes |
| Budget 5 main | 192 GPU | 384 new episodes |
| Final analysis | 1 CPU | 1 complete aggregate |
| Historical budget 30 | zero new allocations | 384 reused episodes |

Each main job is one family × seed × source and executes both horizons in
the original order H75 then H150, with a fresh episode/policy for each.
Thus new main count = 2 budgets × 2 families × 3 seeds × 32 sources ×
2 horizons = **768**. Combined main count = **1,152**, not 1,152 independent
sources. Exactly zero fits and zero optimizer updates. There are **387 new
allocation coordinates: 386 GPU and one CPU**. No optional stages.

The first two jobs each compare legacy30, new1, new5, new30 at each horizon:
2 families × 2 horizons × 4 versions = 16 first decisions. They use the first
already exposed development source, no action delivery/advance, and no success
endpoint. These are proposed real-runtime checks, not performed in preparation.

## 4. RNG coupling and honest bank evidence

Preserve `stream_seed((reference,horizon),absolute_stage,'proposal' or
'refinement',training_seed)` including its historical `lgp1|` prefix. Budget
is deliberately absent. Separate explicitly seeded generators isolate proposal
randomness from how much CEM noise is consumed. CEM draws exactly n−1 new
Gaussian populations for n scored populations. No global reseeding is added.

At the same state, history, target, model and declared stage, the initial
proposal bank must be bit-identical across budgets. Artificial-tensor tests
exercise both proposer implementations and the actual policy/CEM. Future
first-decision checks compare legacy and new initial-bank hashes and require
bit-identical legacy30/new30 returned chunks and round summaries. Both
families must pass before any main job is submitted. All six final model
identities are authenticated, even though the first-decision checks use the
prespecified seed 8301 pair rather than adding six technical arms.

After actions diverge, each policy observes its actual trajectory, history
and state, and generates its own local target. Equal source/stage seeds do
not imply equal future contexts/banks. Do not force shared future actions.
No intermediate population on an old30 trajectory is a shorter-budget
closed-loop outcome.

The historical aggregate actually saved context hashes, elite indices,
cost minima/means, population/elite spreads, unique counts, projection
summaries, timing, and compact physical endpoint evidence. It did **not**
save raw proposal banks, proposal-bank hashes, or full cost vectors.
`MEASURED-COST.json` lists the observed field inventory across all 5,485 old
main stages. Historical raw-bank equality cannot be established from it.
New runs add compact typed SHA-256 fingerprints of unprojected and projected
initial banks only, not full banks or new model inputs. No claim of
historical raw-bank equality will be made.

## 5. Endpoint, schedule and evidence

Primary endpoint is actual native closed-loop success within 2H physical
actions, excluding t0, with the unchanged combined agent/block position
norm <20 and angle distance <pi/9 at the same post-action step. Retain the
reviewed input/observed angle domains and native terminal/TimeLimit300 flags.
No altered success threshold, hindsight action selection or offline surrogate.

Reuse `FreshEpisode`, `lgp1_endpoint.verify_file` and the pinned fresh
initializer. Save every delivered action, post-action raw state, terminal
and truncation flag, absolute step, physical remaining budget and action-stage
index, plus authenticated requested/initialized/goal identities. Reject
unexplained early stopping, success inconsistent with states, missing or
mislabeled flags, and post-terminal actions. Require the full physical budget
unless a legitimate native event occurs. Preserve final-chunk and final-budget
success. Local cycles restart at H, but the physical budget remains 2H.

Technical failures preserve outputs and stop the new chain. No automatic
retry, replacement, resumption, configuration change or additional allocation
is in this launch proposal. An unfavorable result is never a technical fault.

## 6. Analysis fixed before new outcomes

Report success for both families at all three budgets, all 32 sources, all
horizons and all seeds. Within each source and budget, average the six
horizon × seed binary outcomes equally for each family. The primary paired
family difference is diffusion minus GMM. Report both differences-in-
differences, (diffusion−GMM)1 − (diffusion−GMM)30 and the analogous contrast
for budget5. Every source contributes; no outcome-dependent subset or model
selection. Horizons and seeds receive the original equal weighting.

Use 10,000 bootstrap resamples of the 32 whole sources, seed 20260919,
sharing the same resampling indices across all configurations and contrasts.
Report percentile 95% intervals as descriptive, outcome-informed development
summaries only. No confirmatory p-value, multiplicity-adjusted discovery,
favorable-budget confirmation claim or automatic promotion. Seeds, episodes,
candidates and repeated historical evidence are not independent sources.

The final aggregate retains all 1,152 episode identities and outcomes with
provenance, all 32 paired source effects, 36 budget/family/horizon/seed strata,
new worker accounting and original30 resource provenance. Supporting
diagnostics never replace native success. No scientific pass/fail gate is
introduced; only predeclared technical validity requirements apply.

## 7. Timing boundaries

Keep the measured LGP1 stage timers: context includes frame encoding and
local-target generation; proposal is synchronized sampling only; scoring
is synchronized LeWM cost time; refinement total includes CEM, projection,
refinement draws, cost, final decoding and buffer preparation. Scoring is
a subset of refinement, not an additive extra. Stage `seconds` is end-to-end
planning from context construction through decoded buffering/log construction.
Unchanged small untimed gaps mean these timers are not an exact partition.

New optional bank fingerprinting is read-only and separately timed. The first
projected-bank hash occurs inside refinement; the unprojected hash occurs
outside it. The combined hash time overlaps these totals: do not subtract it
all from refinement or count it twice. Historical30 has no bank-hash overhead.
Report that instrumentation difference, rather than calling it perfectly
matched compute. Both new budgets and both families use identical hashing.

Also save setup/model-load time, fresh-reset time, complete per-episode driver
time, physics/action-delivery time, total worker wall/process CPU/peak RSS and
peak GPU allocation, plus Slurm allocation time. The complete-job measure
includes setup, source/container/input authentication, execution and worker
sealing; controller verification, archive construction, transfer and byte
verification are separately timed/accounted. Historical30 lacks the newly
separated reset/episode timers; mark them unavailable, not reconstructed.
Equal candidate counts are not equal proposer compute.

## 8. Execution contract, barrier and preservation

`lgprb1_package.py` exports a separate source closure on the designated SSD,
checks unchanged component hashes, seals `LGP-RB1-SOURCE-MANIFEST.sha256`,
creates a **disabled** `APPROVAL-TEMPLATE.json`, and verifies every tar member.
No reviewed LGP1 source or output is overwritten. A future separate researcher
approval must bind the actual source/protocol/reuse/grid hashes, six model
lineages, exact grid and all caps. The launch, controller and worker reject
the disabled template before execution imports/submission. Existing old
training/dispatch files are retained for source closure, not authorized paths.

After approval only, `lgprb1_launch.py` creates an exclusive control namespace
and a detached Prometheus controller. It authenticates historical reuse,
rejects prior LGP-RB1 attempts, and serially dispatches the exact grid using
the existing pinned container/runtime. No dependency installation, permission
change, GPU substitute, local SSD lease or historical-controller restart.
Each terminal allocation is charged before failure handling. An ambiguous
submission is preserved for reconciliation, never blindly resubmitted.

While incomplete, read only scheduler/accounting, process identity, seals,
bytes and technical projections. Do not inspect partial effects to change the
study. Final result reading follows full-grid/endpoint/source authentication
and byte/member-verified external preservation. Reserved CVL closed-loop,
BP1 evaluation and references1600–5999 remain unopened; no protected metrics.

`lgprb1_preserve.py` builds the new source/run/control archive only after
completion, then verifies its copied members and complete archive on
`D:/THESIS-BACKUPS/local-goal-search-budget-20260919`, THESIS_SSD volume
`0a2f1ba9-0000-0000-0000-100000000000`, at least40GB free. It also re-verifies
the entire existing 1,734,420,480-byte LGP1 archive, preserving the union of
historical source/models/outcomes/control and the new chain. No laptop
fallback, no overwritten backup and no fake acknowledgment. Resource caps
and failure reservations are in `RESOURCE-PLAN.md`; actual archive and
transfer durations are reported, not called GPU compute.

## 9. What this can establish

This tests budget dependence for these six frozen proposers inside this shared
planner on these exposed development sources. It can distinguish whether the
family difference changes with common refinement and the measured compute
tradeoff. It cannot establish untouched confirmation, broad proposer
superiority, a new method, effects of retraining, or how a best-candidate
return/different planner would behave. LGP1 and all earlier decisions remain
unchanged regardless of the new result.
