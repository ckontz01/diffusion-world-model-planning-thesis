# Fresh E18 driver integration: engineering pass

Decision: `fresh_e18_driver_integration_passed_on_exposed_pusht_records`.
No efficacy claim; no confirmation data accessed or scientific comparison run.
The R3 initializer, original planner implementations, checkpoints and every
historical decision remain unchanged. This closes the bounded PushT driver
integration gate, not SAGE release fidelity or a general Cube integration gate.

## What now reaches computation

Static inspection of the loaded `jepa.JEPA` source, read-key instrumentation and
real exposed-input tests agree:

| Input | Actual dependency / pinned source |
|---|---|
| Current and goal pixels | Fresh wrapper render, unchanged E18 image transform; LeWM `encode` reads `pixels` only after E18 removes `action`. Full-info and minimal-info latents were bit-identical. |
| Raw current state | Captured before `_prepare_info`; normalized by each unchanged proposer checkpoint's `state_mean`/`state_std`. |
| Latent and action-proposal normalization | The checkpoint's `latent_mean/std`, `u_mean/std`, `interior_scale`, `target_raw_limit`, and `planner_action_mean/std`, not fitted evaluator coefficients. |
| Evaluator state/proprio/goal-state/goal-proprio scalers | Do not affect this E18/LeWM computation. Neither recovered nor substituted; no fit was performed. |
| Delivered primitive action | The already-sealed R1 action scaler, checked against every tested family checkpoint's planner-action statistics. |

Exact recovered decoder coefficients (float64):

```
mean  = [-0.007812564379916172,  0.006860687229453032]
scale = [ 0.20846744284501714,   0.20674862637362224]
```

Their float32 values equal all three seed7201 family checkpoints exactly.
Fixed action roundtrip maximum error: 5.960464477539063e-08. Every active first
and continuation proposal bank was checked against the frozen raw/planner
coordinate conversion; every selected delivered action was checked against its
actual plan and decoder at atol2e-7/rtol1e-6. Zero-padded inactive actions are not
delivered and are excluded from the inverse-transform identity assertion.
Complete relevant coefficient arrays and their checkpoint provenance are
preserved in each sealed evidence file. No probe-fitted scalers were used.

## New interface and lifecycle

`FreshEpisode` requires the explicit R3 environment and an explicit complete
record. It calls `reset_world`, never legacy dataset evaluation, and never
overlays recorded JPEGs on freshly initialized states. The test temporarily
made the legacy setter raise; it was never reached. Normal wrapped stepping,
control and physics remain unchanged. No reset physics step occurred.

Each episode gets a newly constructed E18 policy and solver with fresh owned
proposal/GMM generators, empty action buffer, stage0 and empty diagnostics.
Frozen models are shared: their full tensor state hashes are unchanged, and
inspection of the actual encode/predict path finds no persistent episode
goal/history cache. Generator continuity is checked at every planning call;
reset identity and complete short trajectory/plan/action hashes agree between
fresh repeated episodes and singleton/interleaved execution.

The driver stops action delivery on the first natural termination, native
truncation or declared action budget. It rejects subsequent steps, replacement
of unfinished episodes and reused policy/solver instances. Native `World.reset`
does not clear its high-level terminal attributes; the new driver owns and
initializes those bookkeeping flags explicitly. A failed operation is terminal
for that driver instance, with no implicit retry or legacy fallback.

Batch convention is **independent episode computation batch1**, with a
round-robin coordinator tested at one and three slots. This is not a claim
about vectorized-batch3 solver throughput. Independently owned RNGs prevent
another slot's early termination from changing the current episode's stream.
R3's prior native batch3 initialization check is preserved separately.

## Fixed scope and observed technical coverage

All five unchanged E18 arms, fixed training seed7201, three already-exposed
PushT episode/start pairs:8908/53,201/6,627/21. No new endpoint was loaded.
The stored E18 endpoint rule was exclusive [start,start+offset), with goal
start+offset-1 and offsets50,50,125. H75/H150 label the unchanged schedules
tested here, not the distance between these particular exposed endpoints.

Job300308 completed0:0 on gpu09/A6000 in2m05s. All five adjacent seals and the
source manifest passed before the aggregate technical interpretation. The
independent CPU verifier passed all identities, coefficient gates, lifecycle
counts, replan positions, repeated-episode and cross-arm initial-input checks.

- 50 episode initializations;128 actual planning calls;1,363 primitive actions.
- At most31 delivered actions per episode, planning at0/15/30 where still active.
- Both schedules and every arm exercised subsequent replanning.
- Natural termination and budget completion both occurred; no success rate or
  arm-performance table is computed. Separate unit tests force natural and
  wrapper termination, and heterogeneous slot completion without performance
  selection.
- Fresh initialization after completed episodes, unchanged goal images,
  current-state replanning inputs, exact action delivery, finite subsequent
  inputs, zero hidden initialization steps and frozen model state all passed.

These are repeated engineering probes on exposed records, not50 independent
confirmation episodes. Reset defaults remain the R3 assumptions, not recovery
of missing historical block/contact/controller dynamics. The driver tolerates
at most1e-10 absolute float64 body/COG coordinate roundoff on general inputs;
observations must equal actual state bit-for-bit, and these exposed R3 records
retained their stricter requested-state exact-equality gate.

## Provenance and disposition

- Integration source commit `2e872c1`.
- Snapshot `/lustreFS/data/superworld/ckontzias/thesis/snapshots/e18-fresh-integration-a9d1c26573158f93`.
- Source-manifest SHA256 `a9d1c26573158f93e3e17dba932129084795a05f2ac84eb7eaadb8bca881d540`.
- Run `/lustreFS/data/superworld/ckontzias/thesis/experiments/e18-fresh-integration/run-20260905-a9d1c265`.
- R3 initializer SHA256 `798bb6749dd30b9c6a91ac7018422edbefd356f3bb6bc322bd8ca95987506a65`.
- Loaded LeWM source SHA256 `41bad7fd21e0f14aea4c9c3d39a9c87037e787746d953ab62cdc0677e938ce96`.

See [fixed plan](E18-FRESH-DRIVER-INTEGRATION-PLAN-2026-09-05.md),
[driver](e18_fresh_driver.py), [independent verifier](verify_e18_fresh_integration.py),
and [sealed evidence](e18-fresh-integration-evidence/README.md).
Confirmation protocol preparation is now scientifically separate from the
closed PushT engineering gate. No diffusion architecture, denoising schedule,
guidance, checkpoint, SAGE grid or historical decision was changed.
