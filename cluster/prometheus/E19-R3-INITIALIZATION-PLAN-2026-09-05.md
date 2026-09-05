# E19-R3: one opt-in instantaneous fresh-state initializer

User-authorized engineering repair; not a scientific reproduction or E20.
Preserve E19/R1/R2 sources, artifacts and decisions. No model changes, training,
planner solve, benchmark scoring, new candidate generation, full grid, holdout,
protected-data access or author contact. No cross-stack performance comparison.

## Contract and single candidate (specified before simulation)

At first decision, recorded physical fields equal the intended start without a
physics step. Unspecified dynamics use explicit reset-independent defaults;
observations are generated from actual initialized bodies. New opt-in Gym ID
and reset interface; native ID, setter and reset path remain unchanged.

Use native constructor/init_value geometry and native `_setup` construction;
new Pymunk Space/bodies/handlers, public assignments and public spatial reindex.
Preserve mass, moments, center of gravity, geometry, materials, collision rules,
PD gains, action scale, dt, control frequency and subsequent native `step`.
Render the recorded goal in disposable fresh construction, then independently
construct the start. Goal marker follows the supplied goal pose, rather than an
irrelevant reset goal. No contact solve/settling during initialization. Do not
remove collisions or infer/clear private contact bias. No seed chosen by outcome.

Already-exposed R1 PushT cases 0,1,2 only (three starts). Inventory sealed R1
endpoint column names/values first. State is agent xy, block xy/angle, agent vx/vy;
proprio redundantly checks agent values. Use recorded quantities if available.
No block velocities/angular velocity, forces, torque, solver contact state,
controller integral or prior controller target is present in exposed columns.
Zero block velocity, angular velocity, forces/torques are canonical defaults,
not recovered historical dynamics. Agent angle follows constructor geometry.
Native controller is PD with no integral state; latest_action is cleared and
contact/coverage counters are fresh. Native reset seed API is preserved, but
fresh geometry/dynamics use no random samples. No claim of complete RNG equality.
Expose optional explicit dynamic fields; reject un-inventoried keys and conflicting
state/proprio. Goal fields use the already exposed stack-specific R1 endpoint;
do not harmonize historical horizon conventions or select new records.

## Validation gates and bounded execution

1. Pure validation/metadata regression tests locally; native tests in each pinned
   stack. Verify parent source files and adjacent R1 input seals.
2. Three exposed cases, histories native seed32, native seed33, preserved R1
   repeat0/repeat1 reset geometries, two repeats, each stack: 48 scenarios.
   Each scenario fresh-initializes twice (idempotence), asserts zero calls to
   Space.step during fresh reset, requested fields, zero-default dynamics,
   fresh contact state, geometry/material identity, spatial index and observation
   consistency. Then exactly three saved primitive actions; compare technical
   trajectory hashes across histories/repeats, not reward/success. Old history
   priming is diagnostic only; no claim of recreating old private caches exactly.
3. Only after gate 2 passes, instantiate actual unchanged model/planner/policy
   arm constructors and checkpoints (all five PushT arms within each stack).
   No solve/inference-generated plan. Test singleton reference and intended batch
   sizes E18=3, SAGE=50, using only exposed records cycled/rotated through slots;
   duplicates explicitly labelled. Compare physical/init observation/input hashes
   within each stack across arms/slots and singleton, before any policy acts.
   Normalization must use existing pinned statistics, never fit to a holdout or
   select a repair by benchmark success. Disclose any setup boundary limitations.
4. Separate signed-velocity declaration correction: only lower bounds for the
   two velocity fields change to -512. Test observation/render and existing
   preprocessing values unchanged; no warning suppression, clipping or dtype
   change. Test legacy delegation and native stepping unchanged.

Freeze code and this plan before cluster execution. Seal new evidence; report
technical failures without treating them as scientific discrepancies. A harness
failure may be corrected transparently in a new snapshot, not silently overwritten.
No automatic expansion of cases/actions. Commit only R3 files and README/history
on e19-r3-fresh-state-initializer; preserve three untracked E12 drafts.

## Scope of reconstruction

This initializes a declared state, not a full continuation of the recorded
simulator trajectory. It cannot restore absent block momentum/contact impulses,
historical controller internals, exact original rendering or RNG state. Newly
rendered pixels intentionally replace inconsistent dataset/reset start pixels;
JPEG/lossless and cross-runtime differences remain separate questions. This is
not a resolution of the historical paper discrepancy.

Public API reference: https://www.pymunk.org/en/latest/pymunk.html#pymunk.Space.reindex_shapes_for_body
