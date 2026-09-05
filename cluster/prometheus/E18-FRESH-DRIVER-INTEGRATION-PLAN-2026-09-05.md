# Fresh E18 driver integration — bounded engineering plan

Frozen before GPU execution. Separate from historical SAGE fidelity and from
E18 efficacy. Parent commit f3b94382e20144e218c33efac48bed75e22a0c39.
R3 initializer SHA256 798bb6749dd30b9c6a91ac7018422edbefd356f3bb6bc322bd8ca95987506a65
must not change. Historical sources, outcomes, checkpoints and gates stay fixed.

## Dependency and coefficient gate

Inspect exact E18 policy, planner, rollout and loaded LeWM encode/predict source.
The policy captures raw state before `_prepare_info`; the proposer uses its
checkpoint latent/state/u statistics. LeWM encode reads pixels (and optionally
action, which E18 removes), not state/proprio. Check real-input full versus
pixel/goal-only encoding bit identity and record accessed mapping keys. No
evaluator non-action scaler is fitted, guessed, or substituted. Recover all
relevant coefficients from the unchanged seed7201 family checkpoints and the
already-sealed R1 action scaler. Require the action decoder mean/std to equal
checkpoint planner-action statistics after float32 conversion; verify actual
planner-coordinate to primitive-action decoding numerically at atol 2e-7,
rtol 1e-6. Stop before planning if either gate fails.

## New driver contract

Use only the R3 explicit reset interface and normal wrapped environment steps.
One policy and solver (including proposal/GMM RNGs and diagnostics) per episode.
Loaded frozen networks can be reused only after checking their state is
unchanged and the actual encoder/predict path has no mutable goal/history cache.
Never call legacy dataset evaluation or overlay dataset images. Never step a
terminal episode. Resetting an unfinished episode or stepping a finished one
raises. An execution failure closes the episode; no automatic retry/fallback.

Batch convention: one independent policy/solver stream per episode, computation
batch1; an explicit coordinator may interleave three episode slots. This is
not native vectorized-batch3 throughput and must never be labelled as such.
It avoids shared solver RNG consumption depending on another slot's termination.
Check singleton versus three-slot execution bit identity using the same record,
seed and fixed planner. The frozen E18 planner's internal batch_size remains1.
This is a disclosed new evaluation interface, not historical E18 replication.

## Prespecified exposed smoke

Only R3 `inputs('e18')`: cases0/1/2, episode/start 8908/53,201/6,627/21.
Use the exact already-exposed E18 start and last endpoint from the R1 seals.
Their extraction convention is [start,start+offset), goal=start+offset-1:
case0/1 offset50, case2 offset125. No new H75/H150 endpoint is loaded.
H75/H150 below name the unchanged *planner schedule*, not these goal distances.

All five unchanged E18 arms, fixed training seed7201. Each arm:

1. Singleton case0, H75, smoke cap31 delivered primitive actions.
2. Three interleaved slots cases0/1/2, H75, cap31.
3. Same world slots reinitialized only after completion, same records and seeds,
   H75, cap31; require exact lifecycle/trace repeatability.
4. Same completed slots, rotated cases1/2/0, H150, cap31.

Maximum50 episodes,1550 primitive actions,150 actual planning calls (three
per episode at delivered actions0/15/30). Natural terminal/truncation flags stop
delivery earlier and are not a performance criterion. Integration requires
replanning at nonzero delivered time somewhere for every arm/H, no hidden
reset step, accurate initial physical/observation/goal fields, finite legal
decoded actions, delivered-action identity, current replanning inputs, finite
subsequent states, correct budget/natural termination dispatch, fresh next
episode initialization, empty policy/solver state, fresh seeded RNGs and frozen
parameters. No reward, coverage, success-rate table, ranking comparison or
efficacy gate is reported. Unit tests force heterogeneous early termination
independently of planner success, and exhaustion/error paths.

The general driver permits at most1e-10 absolute float64 body/COG coordinate
roundoff in requested-state assignment; supplied observation must equal actual
state bit-for-bit. The three exposed R3 records retain their stricter exact
assignment assertion. Decoder checks cover active actions, not zero padding.

The smoke cap31 is driver truncation after a complete delivered action, not
an alteration of the planner's H75/150 schedule or underlying2H budget.
The proposed scientific driver convention is explicit endpoints (goal index
start+H, inclusive endpoints), at most2H PushT primitive actions, and immediate
stop after a natural termination/truncation. It is intentionally not the old
exclusive-endpoint dataset overlay. Freeze prospective design only after this
integration passes; no holdout IDs are generated/read/hashed in this work.

## Scope and stop rules

Source/manifests and adjacent output checksums precede interpreting the complete
technical output. Failed logs may diagnose exact engineering failures; preserve
each immutable attempt. No success-based tuning, model change, R3 rewrite,
full SAGE grid, author contact, confirmation access or automatic scientific run.
Confirmation design choices remain separately declared, never inferred from
smoke success. No proposed same-proposal greedy64 control is implemented here:
the current five frozen arms are the integration target.
