# R3 actual-arm/batch boundary check

Proceed only after core snapshot 30215e7fcfd0e614 passes both stacks' sealed
24-scenario validations. The initializer bytes must be identical to that snapshot.
This is the second engineering gate of R3, not a different repair candidate.

Instantiate all five unchanged PushT methods from each frozen stack, with their
real local checkpoint loaders, cost models, proposer/generator, adapter when
required, solver, scheduled policy, and native World/wrappers. Use E18 learned
seed7201/replicate1/shard0 and H75 constructor settings in both stacks, native
schedule and candidate parameters. The exposed R1 records retain their own goal
endpoints; this is an initialization check, not an H75 evaluation. Official
far_goal_prior_cem uses the released far-goal action-prior checkpoint.

No solver call: stop the real policy.get_action after its native preprocessing
and before inference/candidate generation. No results/benchmark reducer. Run
singleton references for all three exposed records, then full native batch size
(SAGE50/E18=3) cycling cases0,1,2, followed by one rotated assignment. Compare
actual initialized physical fields, raw supplied observations, prepared image
and action inputs, and SAGE history/slot keys. All duplicate slots are labelled.
Three saved primitive actions per singleton and first full-batch assignment,
through the unchanged native batch step; second assignment is initialization
only. Per arm: SAGE103 initializations/159 actions; E18=9 initializations/18
actions. Across ten arms:560 initializations/885 primitive actions. No success
values are retained or interpreted. Assert parameter versions/shapes unchanged.

## Preprocessing scope (explicit before this gate)

SAGE native policy process contains only released action statistics; reproduce
it exactly. E18's historical evaluator fits action/proprio/state StandardScalers
over the full dataset each invocation and did not export those scaler objects.
Use exact previously sealed R1 action mean/scale; do not refit or substitute
non-action scalers from new data. Actual E18 model/planner/policy constructors,
seeds, attachment and native image/action preprocessing execute, but the
non-action-scaler boundary is tested as raw state/proprio equality. This is not
full native-evaluator equivalence or validation of the missing scaler values.
For identical raw inputs and an identical fixed deterministic scaler, output
equality follows independently of scaler coefficients; future scientific use
must still pin/reuse those coefficients rather than fit to a confirmation set.

The separate velocity-bound correction cannot affect preprocessing (native
preparation reads input values/process/transform, not observation-space bounds).
Core tests compare values/render before and after correction; this gate checks
actual image/action preparation and unnormalized lowdim inputs. Do not conceal
this boundary by labelling dummy models or fitted-on-probe scalers as official.

Keep every historical source and decision unchanged. No diffusion modification,
training, full SAGE grid, E18-versus-SAGE performance comparison, protected or
holdout input. Independently reduce all ten adjacent sealed results and verify
complete identities before accepting the gate. Preserve technical failures.

## Preserved first arm-check harness failure / lifecycle correction

Job300302 (snapshot bde5784c50fef64c) failed during SAGE base_cem's first
full-batch raw-input comparison. Physical-state equality had passed. Native
ScheduledPolicy.set_env resets history/action buffers but not `_plan_call`;
the harness reused a policy across three singleton initializations, making
call metadata 3 rather than 0 at the batch boundary. No complete ARM-CHECK file
was written; three singleton initializations plus50 batch initializations and
nine primitive actions ran. This is not an initializer failure or an E19 result.

The replacement harness constructs a fresh native policy for every
initialization, reusing unchanged loaded model/solver objects that never solve.
It explicitly asserts call0 and slot indices, and exercises the actual saved
action scaler's roundtrip on the existing fixed stimuli (rtol1e-6/atol1e-7).
No planner/private counter is patched. The validated initializer is byte-identical.
The old snapshot, run directory and logs are preserved. The new complete
ten-arm check never reuses an old result. Future use of this new interface must
likewise construct a fresh policy per episode or separately validate its entire
lifecycle; `set_env` alone must not be advertised as a full reset.
