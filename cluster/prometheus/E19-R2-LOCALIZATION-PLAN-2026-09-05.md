# E19-R2 targeted restoration localization

Outcome-informed engineering diagnostic authorized 5 September 2026. R1,
E18, E19, D2 and L1 remain unchanged. No diffusion redesign, production fix,
model inference, planning, training, benchmark comparison, author contact or
protected/confirmation data access is authorized here.

## Fixed scope before execution

Use R1 STIMULI.json (SHA-256
`45ac71f23c4ff96df15a7eb2c019456c7847bec4cae3582c57dbefb8f085848a`),
cases 0 and 1 only: PushT episode/start 8908/53 and 201/6. These are the
already-exposed records containing the E18 and SAGE R1 counterexamples.
Use both installed stacks, separately, one environment each. For each
record/stack run two fresh processes for each reset mode: native None,
explicit seed 32, explicit seed 33. Total: 24 fresh initializations and
24 post-restoration actions, plus unchanged native reset/setter physics.
No replacement of seeds based on observed behavior. An unseeded fresh reset
does not reconstruct the exact entropy-derived R1 reset.

Reuse the frozen R1 interface harness as an imported dependency, without
editing it. Limit its post-restoration cap to one action in R2 process memory.
Its original 15-action buffer and stored stimulus remain intact; only the
first action is delivered. No second planner/stub call can occur.

Observe the unchanged PushT setter at entry, after each Python assignment,
and immediately before/after the native space.step(dt), including its two
reset-internal calls. Read requested state, body pose/velocity/angular
velocity/force/torque, contacts, shape cached bounds, space configuration,
environment/controller attributes, actual RNG/variation state and source
hashes. Use Python line tracing and a delegating Space.step wrapper; do not
replace integration functions, mutate physics quantities, skip a native step,
or introduce a repair. Opaque private Chipmunk fields remain unavailable.

The explicit-reset modes change only the base environment reset seed and
record both received and effective values. All global seeding, native hooks,
decoding and action delivery stay as in R1 PushT. Explicit seeding is a
diagnostic intervention, not a proposed production correction.

## Source and preserved-artifact audits

Explain R1's SAGE Cube global-seeding helper and evaluate(seed=32) against
the pinned official Cube entry point and dataset evaluator. Do not run Cube
again merely to conceal the R1 deviation. Classify the preserved E18 PushT
observation-space warning by checking actual saved reset/step observations
against installed bounds, shape, dtype and finiteness, and against the pinned
SAGE velocity-bound declaration. Never suppress the warning or edit old logs.

## Interpretation and conditional next stage

Separate: (a) requested position/angle/agent velocity assignment correctness,
(b) deterministic advancement during setter step, (c) retained reset-state
differences, (d) physical state versus supplied dataset observation, and
(e) within-seed repeatability versus cross-seed correctness. Agreement under
one seed does not establish the intended restoration contract.

Stop after the bounded localization if the intended contract remains
unresolved. State the earliest difference and what is and is not causally
identified. A correction must specify the timestamp/fields being restored,
how unspecified dynamics/contact state are initialized, and how observations
are regenerated, with source justification. Do not implement one merely to
make repeated runs equal. Only after resolving that contract should a
separately specified initialized-state arm-equivalence check be executed,
including native batch sizes (SAGE 50; E18 3). Static routing inspection is
allowed now, but is not a substitute for that conditional dynamic check.

Seal each trace and audit. Read aggregate results after all 24 runs complete;
exact technical failures may be diagnosed without interpreting partial results.
Preserve all artifacts and report complete execution accounting. Freeze source
and this plan before simulation, use read-only parent mounts, and commit only
R2 source/evidence/docs plus README/history updates, preserving E12 drafts.
