# Opt-in instantaneous PushT initialization

`pusht_fresh_initialization.py` implements one new engineering interface. It does
not patch `swm/PushT-v1`, native source, the native setter/step, checkpoint bytes,
or any historical experiment. Import has no registration side effect.

## Usage

```python
import stable_worldmodel as swm
from pusht_fresh_initialization import register, reset_world

world = swm.World(register(), num_envs=len(records), image_shape=(224, 224),
                  max_episode_steps=300, correct_velocity_space=True)
# Construct a NEW native scheduled policy for each episode/batch initialization.
# SAGE set_env alone does not clear _plan_call. Never clear guessed private state.
world.set_policy(new_policy)
info = reset_world(world, records, seed=32)  # seed is not the repair
# info comes from actual initialized bodies and normal rendering/wrappers.
```

One record is required per slot; every record is validated before any is queued.
The ordinary wrapped/vector reset consumes each queued record exactly once.
Direct Gym use supports `env.reset(options={'instantaneous_record': record})`.
Calling the new environment without an explicit/queued record delegates to its
unchanged native legacy reset. This is deliberate legacy availability, **not**
permission for a new dataset driver to silently fall back. Always pass explicit
records at every new scientific episode. Do not call legacy dataset-evaluation
methods afterward: they run legacy setters and overwrite observations with
dataset arrays. A future scientific driver must use this new reset interface
and pin its lifecycle, records, normalizers and protocol separately.

## Field interpretation

| Field | Rule |
|---|---|
| `state` (required, length7) | agent x/y, block x/y/angle, agent vx/vy; exact float64 representation of stored values, angle in [0,2pi) |
| `goal_state` (required, length7) | intended endpoint in the same convention; separately rendered without physics advancement |
| `proprio` (optional, length4) | must exactly agree with state entries 0,1,5,6; conflicts fail |
| `block_velocity` | recorded length2 value if supplied; otherwise canonical zero |
| `block_angular_velocity`, `agent_angular_velocity` | recorded scalar if supplied; otherwise canonical zero |
| `agent_force`, `block_force`, `agent_torque`, `block_torque` | recorded values if supplied; otherwise canonical zero |
| `agent_angle` | recorded scalar if supplied; otherwise constructor variation angle |

Unknown keys, nonfinite values, wrong dimensions and conflicting redundant
fields fail before existing physics is changed. The three exposed records
contain none of those optional block/controller dynamics. `action` is an input,
not a complete prior controller state, and is not treated as one. No finite-
difference estimate or selected reset seed is substituted for missing dynamics.
Episode index, step index, episode offset and episode length are identifiers,
not missing physics. Pixel arrays cannot recover absent solver/contact state.

## Construction and time

The pinned native PushT constructor's variation values (including explicit
`init_value`) are captured before any reset sampling. Its unchanged `_setup`
routine creates a new Pymunk Space, wall shapes, bodies and collision handlers.
Constructor center-of-gravity/damping overrides are reapplied. Public body
assignments set specified/default dynamics and
`Space.reindex_shapes_for_body` refreshes the spatial index without integration.
This reuses the native environment's construction routine; it is not a claim
that `_setup` is a stable public API across arbitrary future SWM releases.

Goal rendering uses disposable construction. The start receives a second fresh
space, never goal contacts. The target marker follows the supplied goal pose,
not a random reset marker. Native observations/info are then rebuilt; the normal
World wrappers render/rescale pixels and provide batch/history dimensions.
No initial image is overwritten with JPEG/HDF5 pixels of a different physical
state. Newly rendered images need not be byte-identical to dataset images.

Initialization integrates **zero time**. Contact/solver history starts fresh;
initial overlap is not removed or settled. Native collision handling applies
on subsequent normal steps. Mass, moment, local geometry, shape materials,
filters, sensors, collision handlers, PD control, action scaling, dt and native
step implementation are unchanged. `latest_action`/coverage/contact bookkeeping
starts empty. No private Chipmunk field is inspected or cleared. No collision
handler, integration callback or diffusion model is replaced.

Gym/environment RNG APIs accept the caller's reset seed, but no random sample
is used for fresh physics construction. Physical/observation independence from
reset history does not imply complete RNG-state equality. Only the pinned
SAGE/E18 runtime versions were validated; stochastic extensions need new tests.

## Separate metadata correction

`correct_velocity_space=True` changes only two lower bounds each in `state`
and `proprio` from0 to-512. SAGE already has these bounds. High bounds, dtype,
shape and values are unchanged. No clipping or warning suppression occurs;
other invalid observations should still be reported. This is not a universal
guarantee that arbitrary future dynamics stay inside a 512-velocity bound.

## Limits and promotion boundary

This is declared **initialization**, not full historical-state restoration.
It does not recover absent block momentum, forces, accumulated contact impulses,
original solver phase, controller history, unwrapped angle history, pre-
quantization physical values, historical RNG or exact original pixels. Canonical
defaults can change later trajectories relative to the original recorded run.

No evidence here resolves the historical SAGE paper discrepancy. No success
table, model comparison or confirmation result is produced. For E18 the arm
check establishes exact raw lowdim-input equivalence; it does not export or
validate the historical non-action scaler coefficients. Those must be pinned
for a future scientific driver, not refitted on a holdout. The interface is
ready for a separately specified engineering/scientific integration step, not
automatic reuse of old result labels or consumption of a confirmation split.

See the R3 plans, result, source diff on `e19-r3-fresh-state-initializer`, and
`verify_gdp_cem_e19_r3_result.py` for the executed gate and its exact scope.

Public physics API: https://www.pymunk.org/en/latest/pymunk.html#pymunk.Space.reindex_shapes_for_body
