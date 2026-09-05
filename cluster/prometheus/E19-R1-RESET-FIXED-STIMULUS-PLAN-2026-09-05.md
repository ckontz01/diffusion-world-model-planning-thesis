# E19-R1: bounded reset and fixed diagnostic action stimulus

Outcome-informed engineering test, authorized 5 September 2026. Preserve
E19, D2, L1 and E18 verbatim. No new planning, model inference, training,
benchmark table, full reproduction, author contact or holdout access.

## Selection fixed before execution

Use repeat zero of the sealed e347bc08 sentinel banks. Five cases, identified
by sentinel and original manifest row: (0,19), (0,0), (2,0), (3,0), (3,1).
The first was implicated in the existing PushT outcome difference; the others
are fixed index controls, including Cube state-field differences and the
PushT prior-top method. Resolve and record episode/start IDs before reset.
For CEM select the first candidate by increasing index whose first 15
primitive actions are finite, have maximum absolute value > 1e-8 and contain
at least two distinct scalar values. Fail if no candidate qualifies; never
use cost, elites or success to select. For prior-top use saved top_actions;
fail rather than substitute if its first 15 actions are ineligible.

Record the source artifact seal/content hash, task, original manifest identity,
row, candidate index, raw macro shape/dtype and selected values/hash. CEM is
labelled **fixed diagnostic action stimulus**, never historical selected plan.
Prior-top is labelled saved historical planner output, truncated to 15 actions.

## Separate interfaces and action semantics

Two fresh processes for each case in each stack: 20 short initializations,
at most 300 post-restoration primitive environment steps. Native reset-internal
settling steps are recorded separately and are not modified. One environment per process removes
batch-position ambiguity; original 50/3-environment interactions are not
certified. Do not force a reset seed. SAGE retains its global seed 32;
E18 uses its recorded deterministic seed derivation for replicate 1/shard 0
and an H75 (PushT) or H150 (Cube) interface configuration. Dataset starts and
goal offsets retain each source sentinel's exposed interval, with each
stack's native endpoint convention recorded, not silently harmonized.

Decode SAGE stored coordinates with its exact checkpoint action statistics.
In SAGE use its unchanged scheduled-policy buffering/decoding, supplying a
fixed-return solver with no model. In E18 express the same environment-space
stimulus in its StandardScaler coordinates and use unchanged E18ScheduledPolicy
buffering/decoding with a fixed-return solver. Refit only the existing action
normalizer from the same public training HDF5 action column, as E18 did;
no protected artifact or holdout is involved. Record rounding differences,
stored coordinates, re-encoded coordinates, world-policy output, base-env
step input, and any existing control transformation. Add no clipping.
Use an explicit 15-action diagnostic buffer, not a new scientific schedule.
Stop before another solver call or benchmark aggregation. Native termination
is recorded only as execution control; early stops are coverage limitations.

## Restoration and observations

Execute the native World dataset initialization, not a rewritten reset path.
Observe reset arguments, actual environment RNG (without initializing it by
reading a property), global RNG, space RNGs, and state after reset and each
dataset hook. Log hook arguments and actual physical state. Snapshot MuJoCo
integration state using the installed mjSTATE_INTEGRATION API, all relevant
data/controller/target fields and model physics hashes. Snapshot PushT bodies,
velocities, forces, contacts and public space parameters; explicitly mark
unexposed Pymunk solver caches as unavailable, not proven equal.

Record fresh observations/renders and dataset-overlay inputs separately;
never require raw pixel identity across encodings/resolutions. Check whether
observation probes change captured physical/RNG state. Record state after
every primitive step. Numeric info fields left over from reset are compared
with freshly derived fields, not automatically dismissed as harmless.

## Interpretation and failures

Inspect engineering logs as needed; no blind scientific outcome selection.
Seal outputs and compare by stack/case/episode/start/stage. First divergent
reset/restoration/action/physical/observation field is descriptive evidence,
not automatic proof of its causal effect. Report restoration correctness
where dataset fields specify a target, and limits where hidden state is
unspecified. Any correction requires demonstrated basis and a regression
test in separate work. Preserve technical harness failures and version any
harness-only correction. No automatic E20 or confirmation authorization.

## Harness-only correction after job 300297

The first immutable R1 snapshot (2c5ea97ae66b1f47) counted Cube's native
reset-internal step calls toward the stimulus budget and therefore omitted
the before-first-action event. All eight Cube traces are preserved but are
not valid complete restoration/replay evidence. The twelve PushT traces
contain that event and all 15 stimulus steps. The corrected counter logs
reset-internal actions separately, leaves native reset behavior unchanged,
and is regression-tested. The replacement runner executes only cases 3/4
in both stacks, twice each (eight processes), using the same deterministic
selection and source bytes. No outcome-based stimulus or model change.
