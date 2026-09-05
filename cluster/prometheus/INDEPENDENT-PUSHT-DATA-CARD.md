# Independent PushT reachable-goal dataset v1

## Purpose and provenance

This dataset supports a new matched planning benchmark. It is NOT a replication
of the historical PushT expert-data or SAGE paper evaluation distribution.
All compared models were frozen before these trajectories were generated.

- Generator version: `independent-pusht-reference-v1`.
- Final namespace: `final-20260906-primary-v1`.
- Collection source freeze: `63f0440`; unchanged after any final model output.
- Complete collection SHA256:
  `3cce1a2b74c84feeece9503dd2873d8db6abd609b546311ed374984ca4d93f68`.
- Accepted references:6,000 from15,839 attempts.
- Rejections:1,335 initial-geometry penetrations;8,504 trajectories with at
  least one agent/block position outside the arena. No compared planner was
  called during generation or used to choose accepted records.
- All6,000 accepted references had at least one recorded block-contact action.
- Initially solved by the evaluation predicate:2 at H75 and0 at H150.
  These were retained, not removed after inspection.
- Median block displacement:98.9252 coordinate units at H75;170.0687 at H150.

## Sampling and acceptance

Proposal agent xy is uniform on[50,450]^2, block xy uniform on[100,400]^2,
block angle uniform on[0,2pi). Each reference has an independent hashed stream
for initial sampling and for the fixed weak collection policy. R3 canonical
initial momentum/forces/contact history are zero. Native physical parameters,
control law, geometry and stepping are not trained or altered.

The weak controller samples a relative position increment uniformly, clips the
resulting target to a100-unit box around the block, then converts it back to
native action coordinates. This encourages contact but does not optimize a
specified final goal. The accepted population is CONDITIONAL on surviving the
full150-step validity rules. It is not uniform over all starts after rejection,
and it is not an expert-goal distribution.

The temporary rendering marker has no task objective during reference
collection. Native success flags relative to that marker are saved but are not
used to stop, accept, or select a reference. Goals are assigned afterward from
states75 and150. The same reference start is used for both horizons.

A temporal offset of150 does not establish a minimal path length of150.
Reference trajectories prove a feasible route from the declared initial state;
they do not prove optimality, unique routes, or equal difficulty to the paper.

## Record contents

Each compressed NPZ contains:

|Key|Shape|Meaning|
|---|---|---|
|initial_request|7|Exact vector passed to the fresh initializer|
|states|151x7|Agent xy, block xy/angle, agent velocity at t0..150|
|actions|150x2|Actually executed fixed-policy primitive commands|
|dynamics|151x10|Recorded block velocity/angular velocity, agent angular velocity, forces and torques|
|contacts|150|Native per-action contact count|
|temporary_marker_success|150|Collection-only flag, not a task-selection filter|

The initial request is retained separately from the observed state to avoid
silently changing floating-point body/center-of-gravity conversions on replay.
Data do not store a complete private physics/contact snapshot at every step.
They support replay from the specified clean start with saved actions; this is
not a claim of arbitrary middle-of-trajectory private-state restoration.

## Validation and durability

All6,000 record hashes, shapes, finite values, action bounds, arena bounds,
unique starts and start-goal fingerprints passed the primary collection gate.
That gate also checked64 witness replays:32 evenly spaced references, each with
its H75 and H150 goal rendered independently. Subsequently CPU job300346 replayed
ALL6,000 references under both goals:12,000 goal-specific reference-action
replays passed. This was a separate completed validation, not an inference
from the witness sample. No compared model was called.

Raw arrays are stored read-only on Prometheus in the collection directory.
The original and launcher-corrected execution directories share identical,
read-only hardlinks to those records. Both logical study configurations and
all6,000 reference files have a separately hash-verified WSL disk backup.
A hardlink is not a second physical backup; the WSL copy supplies that separation.
Git stores generator code, protocol, hashes, counts, tests and execution context.
Large data arrays are not embedded in Git history.

## Intended interpretation

Results concern frozen planning methods on this new reachable-goal population.
Use episode-level paired inference, not the much larger count of repeated
arm/horizon/checkpoint runs. SAGE's three blocks are evaluation-seed blocks of
one released trained model. E18 uses its three frozen training checkpoints.
Do not describe those as three separately trained SAGE models.

Do not claim that synthetic construction proves the sampled states are far
from every training state. The exact generated trajectories are new; state
similarity, support overlap and generalization beyond this population remain
separate questions. No method superiority follows from this data card.
