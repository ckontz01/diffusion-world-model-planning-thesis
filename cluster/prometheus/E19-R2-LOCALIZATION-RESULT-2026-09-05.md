# E19-R2: targeted restoration localization

5 September 2026. Outcome-informed engineering, not a benchmark or a repair.

## Outcome

**The requested PushT state is correct immediately before the setter's
internal physics step. That step advances the agent and can import retained
contact-correction motion from the reset history into the block pose.**
Explicit reset seeds make that behavior repeatable; they do not make it a
correct, reset-independent restoration.

Decision: `localized_reset_contact_carryover_contract_not_yet_approved`.
R1 and all historical results remain unchanged. No diffusion/model change,
production environment patch, planning, E20, holdout access, benchmark
comparison or author contact occurred. Confirmation remains on hold.

## SAGE Cube global-seeding clarification

R1 calls `pusht.set_determinism(32)` for **both** SAGE tasks. That helper
seeds Python, global NumPy and Torch/CUDA, selects deterministic algorithms,
disables the named TF32 settings, and sets `PUSHT_CPU_MULTINOMIAL=1`.
The pinned official Cube main does not call that helper or perform that
global seeding. Its CEM constructor seeds a dedicated Torch generator.

Thus R1 Cube was an **additionally globally seeded engineering check**, not
an exact reproduction of the official Cube entry point's seeding conditions.
R1 also passes `world.evaluate(seed=32)` while official Cube omits that
argument. For this dataset path, the vendored dispatcher does not forward
that top-level seed: `_evaluate_from_dataset` resets using the endpoint
`seed` column, absent in these records, hence None. The top-level argument
does not establish explicit Cube environment seeding.

This is a disclosed R1 harness deviation, not an amendment to R1 or E19 and
not an inferred explanation of E19's performance discrepancy. No new Cube
simulation or global-seeding ablation was performed. The source audit stores
the actual pinned functions and file hashes.

## Preserved observation-space warning

All **180 saved R1 PushT step observations** were checked against the
installed declarations: keys, shape, float64 dtype, finiteness and numerical
bounds. **56 violate native bounds; all violations are negative velocity
components in E18's `proprio`/`state` spaces.** Every observation passes the
signed-velocity bounds already present in pinned SAGE. There are no remaining
shape, dtype, nonfinite, position or angle violations in this checked set.

Classification: **observation-space declaration defect**, separate from the
restoration-state defect. The installed E18 declaration has zero lower bounds
for velocities, despite valid signed physical velocities. Gymnasium's passive
checker warns and returns the existing step result; it does not clip or repair
the observation. Metadata-only correction is source-supported, but none was
applied here, and changing the declaration would not fix physical restoration.
This classification does not waive arbitrary future observation warnings.

## Direct setter boundaries and reset intervention

The frozen main diagnostic used the same exposed R1 cases 0 and 1 (PushT
8908/53 and 201/6), separately in both stacks. Two fresh processes per
record/stack/reset mode: native None, explicit 32, explicit 33. Each delivered
one original fixed-stimulus action. Total **24 initializations, 24 actions**.
It retained R1 decoding/buffering and native evaluation hooks. No new candidate
selection or model forward was performed.

Python line traces and delegating Space.step capture establish:

- All requested agent positions, block positions/angles and agent velocities
  are **bit-exact before physics in all 24 runs**. The snapshot immediately
  after the final position assignment equals the pre-step snapshot.
- The setter does not assign block linear/angular velocity, forces/torques,
  or contact-solver state. In this main diagnostic, public block velocity,
  angular velocity and forces are zero before the dataset setter step.
- The internal step is 0.01 seconds. Agent displacement is its requested
  velocity times 0.01, with maximum coordinate changes **0.20375017166139742**
  for case 0 and **0.9372322845458712** for case 1, regardless of reset mode.
- Each fixed seed repeats captured physical state exactly within its pair,
  and the new native pairs also happen to agree after assignments. This does
  **not** erase the preserved R1 counterexamples or recreate their entropy.
- Crucially, **seed 32 and seed 33 disagree after the setter step**, despite
  identical requested fields and zero public block velocities before it.

| Both stacks, within-stack comparison | Seed 32 block-position error after setter | Seed 33 error | Angle difference |
|---|---:|---:|---:|
| Case 0 | 0.2378083845933361 | 0 | 0.002577922279134226 rad |
| Case 1 | 0.18998697228494166 | 0 | 0.002577922279134004 rad |

These matching numerical effects in the two installed stacks are observations,
not a general cross-version equivalence claim.

Before the step, the cross-seed difference in captured body/contact state is
the retained contact arbiters. Shape cached bounds, reset goal/environment
attributes and RNG states also retain reset information; they are logged
separately, not all labelled causal. Position assignments update body transforms
but do not turn the old contact graph into a freshly initialized graph.
Recorded contact-point geometry after teleportation is not a new collision
query, so its distances are not themselves a fresh-contact validation.

For seed 32, the block center-of-mass change is
`[-0.1415232442258798, -0.1435159975097804]` with public velocity zero, and
angle change is approximately `-0.0025779222791342`. The different reported
body-origin displacements follow from the rotated nonzero center of gravity.

The exact runtime-reported [Chipmunk revision](https://github.com/slembcke/Chipmunk2D/blob/7a29dcfa49931f26632f3019582f289ba811a2b9/src/cpBody.c)
and [Munk revision](https://github.com/viblo/Munk2D/blob/ade7ed72849e60289eefb7a41e79ae6322fefaf3/src/cpBody.c)
integrate ordinary plus bias velocities for position/angle, then clear the
bias fields. From that formula, the measured residual implies linear bias
approximately `[-14.152324422588, -14.351599750978]` and angular bias
`-0.2577922279134` before this step. **Those bias values are kinematic
inferences, not direct reads of opaque private fields.** The step source
integrates positions before new collision detection, then solves contacts for
subsequent correction: [native step ordering](https://github.com/slembcke/Chipmunk2D/blob/7a29dcfa49931f26632f3019582f289ba811a2b9/src/cpSpaceStep.c).

The public block velocities being zero rules out ordinary retained block
velocity as the explanation for this specific pre-action displacement.
Together, the boundaries, cross-seed intervention and native equations localize
the problem to retained contact/integration state consumed during restoration,
not action delivery or the diffusion model.

## Preserved-counterexample contact probe and limitation

A separately frozen eight-initialization extension used the four recorded R1
good/bad reset geometries: SAGE case 1/repeats 0 and 1; E18 case 0/repeats 0
and 1, each in two fresh processes. It ran **zero primitive actions** and no
World/policy/model. After reset(seed=32), the unchanged setter first received
the recorded reset geometry, then the original requested dataset state.

The bad preserved SAGE geometry contains a block-wall penetration; the bad
E18 geometry contains a block-agent penetration. Both had zero recorded public
velocities/forces. The probe generated the same contact-dependent kind of
displacement in each stack and was repeatable, but **did not exactly
reconstruct the old bad R1 outputs**:

| Probe | Block displacement | Preserved R1 displacement | Maximum position residual versus R1 |
|---|---:|---:|---:|
| SAGE bad reset geometry | 0.6512830650 | 0.6424105757 | 0.0088724893 |
| E18 bad reset geometry | 1.0448108764 | 1.0319323789 | 0.0128784975 |

The good-geometry probe's final body states match the corresponding R1 body
states, but its intermediate primed state also is not an exact R1 reset copy.
The reason this is not an exact reconstruction is explicit: the extension
used seed 32 as its baseline, and the main analysis shows that this baseline
already carries contact bias. The trace's `neutral_reset` label is therefore
a misnomer, not a validated neutrality claim. That residual shifts the primed
geometry before it generates the next contact state. All outputs are retained;
no seed-33 retry or outcome-directed matching attempt was launched. This
extension supports the mechanism, not exact historical private-state recovery.

## Required restoration contract, not a matching trick

A production correction is **not yet selected**. The current setter is not a
pure timestamp-preserving inverse of the seven-field dataset observation.
That observation contains agent velocity, not a complete block/contact physics
snapshot. Two distinct contracts must not be conflated:

1. **Instantaneous dataset-start initialization:** at first policy input,
   specified physical fields must match the requested timestamp, unspecified
   dynamics/contact state must follow a declared reset-independent rule, and
   observations must reflect that actual initialized state. No silent physics
   advancement may be hidden inside a nominal state assignment.
2. **Legacy setter compatibility:** preserve its explicit physics advancement
   and disclose the resulting state/time offset and reset-history dependence.
   This cannot be described as exact restoration of the requested timestamp.

For a new confirmation interface, the first is the proposed contract, subject
to approval and source/author intent where official reproduction is claimed.
It needs explicit rules for missing block velocity/angular velocity, forces,
contact caches and observation rebuilding. Reconstructing a canonical fresh
space and refreshing collision geometry without advancing time is a candidate
implementation direction, **not an implemented or validated fix**. Simply
seeding reset, zeroing visible velocity, clearing one private field, removing
one line, or suppressing the warning is not sufficient evidence of correctness.

## Planner-arm and intended-batch gate

Static inspection confirms that E18 arms use the same World construction,
task callables and dataset-start dispatch; its planner/proposal seed derivation
does not include the arm name. SAGE method branches converge to a common
World/callable path within each task. Nevertheless, model construction occurs
before evaluation, and identical setup code is not proof of equivalent actual
initialized states under entropy-seeded resets.

**No dynamic planner-arm/batch check was launched**, because the contract above
is not resolved. The next separately specified check must verify, before any
arm can act, requested versus actual fields, reset-independent initialization
of omitted fields, rebuilt observations, RNG provenance, environment-index
mapping and within-stack arm equality. Include a small one-initialization probe
at intended native batch sizes: E18 **3**, SAGE **50**, using only these exposed
records (any duplicate slots clearly labelled). Do not claim planner RNG or
model-construction equivalence from a dummy-arm label. That check must precede,
not consume, a confirmation holdout.

## Provenance, counts and evidence

- Main snapshot `gdp-cem-e19-r2-a4320292c95507a9`, source-manifest SHA-256
  `a4320292c95507a900bae1dfd43ec45f188300e0efbe3d9707f8ceb17ec84e02`;
  job **300299**, completed 0:0, **6m53s**.
- Contact snapshot `gdp-cem-e19-r2-contact-ba78531c42633638`, source SHA-256
  `ba78531c4263363877b2e2ccbbabfb5b53e33316133ffb6e67e3032780b8adfb`;
  job **300300**, completed 0:0, **1m23s**.
- Combined: **32 simulator initializations, 24 primitive actions, 104 recorded
  setter-internal physics steps** (including reset). Normal action execution
  additionally uses its unchanged native physics substeps. No simulation was
  performed by source audits or reducers.
- The initial 24-run/24-action and subsequent eight-run/zero-action barriers,
  all adjacent seals, exact case/repeat identities, original-source hashes and
  before/after coverage were checked before aggregate interpretation.

Raw traces and full analysis remain on Prometheus under
`/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19-r2/` in
`run-20260905-a4320292` and `contact-20260905-ba78531c`.
Only the [review evidence](e19-r2-evidence/README.md) is copied to the
external-SSD-backed canonical WSL repository. See the [implementation
history](E19-R2-IMPLEMENTATION-CHANGELOG-2026-09-05.md) and
[independent local verifier](verify_gdp_cem_e19_r2_result.py).

Final verification: **41 local tests passed** (14 R2 tests plus 27 existing
R1/E18 tests); both independent R1/R2 evidence verifiers passed. Both new
snapshot manifests, the R1/diagnostic/E18 parent manifests and all new artifact
seals were reverified after execution. Shell syntax and git whitespace checks
passed. The three unrelated E12 drafts remain untouched and untracked.
