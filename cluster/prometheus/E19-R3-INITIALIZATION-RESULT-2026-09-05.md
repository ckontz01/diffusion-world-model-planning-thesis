# E19-R3: fresh-state initializer implemented and engineering gates passed

**Decision: `opt_in_fresh_initialization_validated_on_exposed_pusht_records`.**

One reset-independent instantaneous initialization candidate is implemented and
validated in both pinned PushT runtimes. The new path matches the stored start
fields without stepping physics, gives actual-state observations to the normal
World interface, and passes real checkpoint-backed arm/batch checks. This is a
bounded engineering result, not a new planner experiment or a resolution of
the historical SAGE paper discrepancy.

## What is reconstructed

The sealed R1 records expose agent position/velocity and block position/angle.
Their proprioception agrees with those state entries. Neither their full column
inventory nor HDF5 root-schema inspection reveals block velocity, angular
velocity, forces, contact caches or additional controller state. No new dataset
row was read for this repair. Episode length/offset are indexing metadata.

The new interface uses recorded fields verbatim, including their stored numeric
precision. Missing block velocity/angular velocity and body forces/torques have
explicit zero defaults. Agent angle follows constructor geometry unless supplied;
optional recorded dynamic fields override the corresponding defaults. These
defaults are **assumptions**, not recovery of missing historical state. The PD
controller has no integral state; action-display/contact/coverage bookkeeping
starts empty. Unknown fields or inconsistent state/proprio fail validation.

## Source diff and legacy isolation

The source change is additive:

- `pusht_fresh_initialization.py`: new opt-in Gym ID, subclass/factory, validated
  record/reset adapter and separate signed-velocity-space helper.
- New R3 validators, runner/freezer scripts, regression tests, sealed review
  evidence and documentation; README receives only new R3 status/history text.
- **No edit** to native SAGE/E18 environment or planner source, diffusion models,
  historical snapshots, manifests, checkpoints, R1/R2 files or historical results.

The new class delegates legacy reset when no record is requested and inherits
the exact native `_set_state` and `step`. Its fresh branch invokes the pinned
native construction routine for new Space/bodies/handlers, sets public body
fields, and uses public spatial reindexing. It never copies or clears guessed
private physics state, samples for a favorable seed, removes collisions or
settles the state with a hidden step. Geometry, mass/moment, center of gravity,
materials, collision filters/handlers, PD gains, action scale, dt and subsequent
native stepping remain unchanged.

The goal is rendered in disposable fresh construction; the actual start then
gets a separate fresh space. The goal marker follows the supplied endpoint.
Normal observations/rendering/wrappers supply the policy input—there is no
legacy dataset overlay hiding a different physical state. This intentionally
does not promise identity with original JPEG/HDF5 pixels. Public reindex updates
the spatial index without the simulation integration performed by `Space.step`.
See the [Pymunk API](https://www.pymunk.org/en/latest/pymunk.html#pymunk.Space.reindex_shapes_for_body).

Initializer SHA256:
`798bb6749dd30b9c6a91ac7018422edbefd356f3bb6bc322bd8ca95987506a65`.
It is bit-identical in the core and both arm-check snapshots.

## Exposed-record validation

Three already-exposed PushT starts, four history preparations (native seed 32,
native seed 33 and preserved R1 reset geometries from repeats 0/1), two repeats
and two runtimes produced **48 scenarios**. Each fresh-initialized twice, then
executed exactly three saved primitive actions. Geometry priming is an
intervention, not an assertion of exact old private-cache reconstruction.

| Technical check | Result |
|---|---|
| Requested seven-field state at decision time | Exact in all 48 scenarios |
| Hidden physics advancement during fresh reset | Zero calls to Space.step across 96 fresh resets |
| Idempotence and reset-history independence | Same physical/observation/render/goal hashes for every case within each stack |
| Missing dynamics/defaults | Zero/default fields verified; fresh arbiters, current shape bounds |
| Geometry/material/control configuration | Same hash before and after fresh construction |
| Observation consistency | Recomputed native state/proprio equals requested fields; normal wrapped pixels independently checked in arm gate |
| Short fixed-action behavior | Three-action physical/observation/render trajectories agree across histories/repeats within each stack |
| Legacy path / optional fields | Native delegation, recorded optional dynamics and constructor overrides pass regression tests |

Core job **300301** completed 0:0 in 48 seconds. Both native runtimes passed the
11 core regression tests. All inventory/validation adjacent checksums passed.

## Actual arm setup and intended batch size

All five frozen E18 PushT arms and all five official SAGE PushT methods were
constructed using real local checkpoints, native model/proposer/generator/
adapter classes, native solvers and native scheduled policies. E18 used the
prespecified seed 7201/replicate 1/shard 0; constructor schedules/parameters were
H75. These are setup parameters, not new H75 evaluations: the three exposed
records retain their own already-exposed goal endpoints.

Each arm had three singleton references and batches at **E18=3** or **SAGE=50**,
with cases cycled through slots and then rotated. Duplicate records are labelled.
All ten arms passed within-stack physical/input equality across arms, slots,
singleton versus intended batch, and the two assignments. A three-action check
on the singleton and first full-batch assignment matched the core physical
trajectory hashes. Real policy input preparation executed; execution stopped
before solver invocation. Model parameter versions/shapes remained unchanged.

The arm gate totals **560 initializations and 885 fixed primitive actions**.
Job **300304** completed 0:0 in 3m18s; all ten adjacent seals and the independent
cross-arm/cross-slot/cardinality verifier passed. **Zero planner invocations**,
candidate generation, model-performance evaluation or stored success metrics.

### Explicit preprocessing boundary

SAGE native image/history/action preparation was checked using released
statistics. E18 uses its exact previously sealed R1 action scaler plus native
image preparation, with raw state/proprio equality checked before non-action
normalization. The historical E18 evaluator did not export its fitted state/
proprio scaler objects; this repair neither refit them over the dataset nor
substituted probe-fitted statistics. Accordingly this is **not** a validation of
those coefficient values or full historical-evaluator equivalence. Identical raw
inputs necessarily remain equal under the same fixed deterministic scaler, but
a future scientific driver must explicitly pin/reuse those coefficients.

### Preserved first harness failure

Job 300302 stopped in SAGE/base_cem's first full-batch raw-input gate after
physical equality passed. The harness had reused a policy across singleton
references. Native SAGE `set_env` does not clear `_plan_call`, so call-index
metadata differed. The replacement constructs a fresh native policy per
initialization and explicitly checks call 0/slot identity; it does not patch a
private counter or change the initializer. The failed snapshot, logs, 53
initializations and 9 actions remain preserved and are not included in the
passing-gate counts. No complete arm result or performance artifact existed.

## Separate observation-space correction

Only signed-velocity lower bounds in `state` and `proprio` change from 0 to -512;
SAGE's already-correct declaration remains equivalent. No observation value,
shape, dtype, high bound, action, render or normalizer is changed. Regression
tests compare values/images before and after; native preprocessing consumes
values, not those bounds. Native image preparation and the actual saved-action
scaler roundtrip were checked. No warnings were suppressed; unrelated bounds
violations remain actionable. This is not a claim that all possible velocities
are bounded by 512 under arbitrary future extensions.

## What this does not establish

- No recovery of absent historical block momentum, contact impulses, unwrapped
  angles, pre-quantization values, controller history, original pixels or RNG.
- No cross-runtime bitwise dynamics claim, SAGE fidelity claim, E18-versus-SAGE
  performance comparison, benchmark improvement or confirmation result.
- No diffusion change/retraining, full SAGE grid, protected data/holdout access,
  author contact, or change to any historical failure decision.

The user-approved initialization contract is implemented and passes this scoped
engineering gate. It need not remain an indefinite unexplained planner failure.
Using it scientifically now requires a separately specified driver/protocol that
pins its explicit defaults, fresh-policy lifecycle and normalizers; it must not
silently reuse historical result labels or consume a holdout automatically.

## Provenance and reproducibility

All bulk artifacts remain under
`/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19-r3/`:

- `run-20260905-30215e7f`, core snapshot SHA256
  `30215e7fcfd0e614f2233277f3c9854abc87172a8d688ec5c3e193b0757f8ee3`.
- `arms-20260905-88a476ab`, passing arm snapshot SHA256
  `88a476ab878979f90e6dd80de7365feac8ab39008f32fbe4047eff668f92cdd5`.
- `arms-20260905-bde5784c`, preserved failed arm harness, source SHA256
  `bde5784c50fef64c60fc37f48187254bfcfb415e2b980fe77176d162eb247d46`.

Passing exposed-record jobs used 656 fresh initialization calls and 1,029
primitive actions, plus the native history preparation for the core checks.
Including the preserved failed harness adds 53 initializations and 9 actions.
Synthetic API regression-test executions are separate from those record counts.

See [interface instructions](PUSHT-FRESH-INITIALIZATION-INTERFACE.md),
[implementation record](E19-R3-IMPLEMENTATION-CHANGELOG-2026-09-05.md),
[sealed review evidence](e19-r3-evidence/README.md), and the independent
`verify_gdp_cem_e19_r3_result.py`. Review evidence is about 692 KB and is stored
in the external-SSD-backed canonical WSL repository, not the stale Windows mirror.

Final checks: **57 local tests passed in 16.22 seconds**, including the new
initializer/interface/verifier tests and existing R1/R2/E18 regressions. The
independent R1 and R2 historical evidence verifiers still pass unchanged.
All new and parent source manifests were reverified after execution, as were
all result seals, shell syntax and whitespace checks. The three unrelated E12
drafts remain untracked and untouched.
