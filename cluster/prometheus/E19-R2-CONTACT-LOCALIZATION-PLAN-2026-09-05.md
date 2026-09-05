# R2 contact-localization extension, specified before execution

The initial frozen R2 job 300299 completed all 24 one-action runs. Requested
fields were exact before the setter physics step, but its new native resets
did not recreate the R1 failures. Do not search seeds or erase those results.

Preserved R1 SAGE case 1/repeat 1 has a block-wall penetration after reset;
E18 case 0/repeat 1 has a block-agent penetration. The corresponding repeat
0 geometries have no contacts. All four recorded reset states have zero
agent/block velocities, angular velocities, forces and torques. The exact
installed Chipmunk/Munk source integrates pending bias velocities during
position updates; these fields are not available through the Python ABI.

## Fixed intervention

Eight fresh isolated native PushT environments: two processes for each of
the four above recorded reset geometries. Native reset(seed=32), then call
the unchanged _set_state with the recorded R1 after-reset geometry (agent
position, block position/angle, agent velocity). Assert the unrepresented
recorded velocities/forces are zero rather than silently dropping them.
Then call unchanged _set_state with that same trace's requested dataset
state. No env.step action, policy, World evaluator, dataset load, model,
planner, success analysis or holdout. Total eight initializations and 32
native setter physics steps: 16 internal reset, eight geometry priming,
eight dataset restoration. This is a contact-state reconstruction probe,
not an exact replay of R1's unknown reset RNG history.

Capture before/after each original physics step without replacing the body
integration functions. Compare primed public body/contact state with the
recorded R1 reset envelope and the resulting dataset restoration with R1's
after-hook state. Label numerical agreement and any residual explicitly.
If geometry priming recovers the R1 displacement, that localizes a retained
contact-state mechanism; it does not prove a particular production repair
or full private-state identity. Do not modify R1 or the initial R2 artifacts.

Use only R1 cases already in the original R2 scope and the already-recorded
good/bad reset geometries, with no outcome-dependent seed/candidate search.
Keep all eight outputs even if reconstruction fails. Analyze after completion
and checksum validation. This extension is targeted engineering under the
user's current request, not another benchmark. Confirmation and arm/batch
equivalence remain gated on an agreed restoration contract.
