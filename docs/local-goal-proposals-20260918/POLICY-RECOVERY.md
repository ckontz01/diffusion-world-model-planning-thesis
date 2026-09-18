# LGP1 policy-interface correction and scoped recovery — 2026-09-19

Authority: the user explicitly said “okay proceed” after the confirmed
`World.set_policy` defect and the commitment to reuse all six trained models.
This is one technical recovery, not another scientific design or permission for
automatic retries. Historical packages, failures, trained weights and decisions
remain unchanged. No metrics were used to choose this correction.

## Confirmed cause and missed test coverage

Job301987 (`technical-gmm-8301-1269`) failed1:0 after22allocation seconds before
the first reset/action: the installed `World.set_policy` calls both `set_env`
and `set_seed`. LGP1 supplied the former, but omitted the latter. The prior
integration test substituted a `set_policy` that called only `set_env`, hiding
the actual contract. The policy-history test bypassed World attachment too.
All six fits/validations completed and the original all-six freeze is preserved.

Installed World source SHA256:
`15fc9e4a69d2ad81d29ca8fedd689b53e96887f7614fa98223ef5ddee37bbda6`.
The existing authenticated source capture is executed for set_policy/reset/
step/close tests, not rewritten as a mock. The old interface fails that test.

## Narrow policy repair and meaningful regression coverage

`Policy.set_seed` confirms the same frozen construction seed while the policy
is fresh. It does not reseed global NumPy/Python/Torch RNGs, introduce a new
stream, reset a running policy or accept a different seed. Existing proposal
and refinement stream keys (source, horizon, absolute stage, seed) are unchanged.

New synthetic tests use the actual Policy, FreshEpisode, proposer samplers,
30-round CEM, decoder/projection and authenticated World methods. Artificial
frozen predictions and a fake physics pool are explicit remaining boundaries.
Both families execute full150/300action budgets, cycle-final stages, cycle
restart, terminal/truncation handling and a fresh second episode. They check
binding to the vector pool, action type/support, stream repeatability and global
RNG non-interference. No research model or simulator is used by these tests.

The full exported suite must also pass in the pinned cluster container on CPU,
with no GPU passthrough or dependency changes. The first existing charged
technical coordinate additionally runs strict-CUDA synthetic checks of both
samplers and actual policy/CEM before real integration. Its global RNG states
are restored. These tests do not establish real-model/physics throughput.
The four unchanged technical jobs must all succeed before main evaluation;
their existing throughput and endpoint checks remain intact. No extra episode,
data, candidates, optimizer update, model or success-based advancement rule.

## Reuse, exact accounting and no implicit scientific restart

All10 prior GPU attempts are terminal:301977,301979–301987. Charges are
46+3388+252+57+293+297+506+507+509+22 =5877seconds; CPU-stage charge0.
Cache and all six successfully completed fit coordinates are verified/reused
in their original read-only roots. No model copy/retraining/validation restart.
The worker rejects cache or fit execution under this recovery authorization.

Remaining:4technical+192main GPU allocations at1200seconds and one7200second
CPU analysis. Maximum combined GPU reservation5877+196×1200=241077seconds,
below unchanged336000. Final expected attempts206GPU+oneCPU=207, versus203
successful GPU coordinates+oneCPU coordinate. Three failed allocations are
retained; the validation-only replacement never repeated optimizer updates.
Total unique fitting remains72000updates/9216000row presentations; this recovery
adds zero. The allocation-count amendment is explicit, not an increased time cap.

Original freeze hash:
`a8a5a0ff456cd870e540f838d2c8b62d00b542be6d7a2da53b377fbd91cbc305`.
Stopped dispatch hash:
`746b42c91685237004ef4f0d4fd0055a46357e861647df0bca4a41ba881e47f4`.
Failed worker seal:
`d53a0c2a910a700b572b41d6b24eecccce073b43b1a74b80cff6cff48d2e5beb`.

New source/run/control namespaces are exclusive. The original freeze is copied
byte-for-byte; each reused root retains its original source/approval identity.
Preflight reconciles every historical job, rejects unexpected/live attempts,
checks previous controller PID/start identities and successful output seals.
Only the failed technical coordinate and unsubmitted work can be dispatched.
Any new failure stops and preserves evidence; no automatic retry is introduced.

The200MBcontrol/5.9GBworker/12GBtotal caps include all three prior source/run/
control chains plus this one. Final preservation covers their union, original
models/cache and all new outputs; byte-verified backup is on the designated
THESIS_SSD only. Remote execution has no laptop/SSD liveness gate.

## Remaining uncertainty

Synthetic interface/kernel checks are not successful real integration. Actual
frozen LeWM/generator, rendered observations, physics and runtime throughput are
still to be established by the unchanged technical stage. A new concrete failure
or infeasible timing stops the chain; neither a scientific setting nor an
allocation limit will silently change to make it pass. No efficacy claim.
