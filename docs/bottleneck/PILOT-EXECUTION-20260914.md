# Concrete short-branch pilot specification

Outcome-informed engineering, not confirmation or a paper-reproduction rescue.
This specification must be committed before pilot output inspection. Full
canonical trajectory reduction and source-matched off-cluster preservation
are launch prerequisites; a submitted prerequisite is not a passed gate.

## Coordinates and evidence

Four fixed references 1269/582/525/722, H75/H150, checkpoint block7201,
elapsed anchors0/30, two independent processes per reference. Maximum16
distinct reference/horizon/anchor points, repeated twice. A terminated anchor
is unavailable; no replacement. Models load from the original independent
study runtime. Historical model-state hash, initial image/state/goal hash,
every preceding selected-plan hash, proposal/GMM RNG before/after hashes,
decoded prefix actions and requested initialization must match. Reset records
are original initial_request plus reference goals at t75/t150. No teleportation.
Physical/controller prefix agreement atol1e-10, rtol0 (the accepted R3 public
body/COG tolerance); pixels/goals/actions/plans/RNG and repeated banks exact.
Do not loosen a failing tolerance after viewing output.

## Banks, units and selection

Capture the unchanged baseline's first64 bank and next64x8 bank. Instrumentation
returns original outputs and verifies explicit stored noise regenerated from
the pre-proposal generator state consumes precisely the same stream. All four
conditions restart from the same post-first/pre-second RNG state. Restore the
baseline post-second state before proceeding to the next historical anchor.
Store both proposer bounded raw actions and planner-normalized actions. Physics
uses the existing sklearn decoder on planner float32 arrays, preserving actual
historical delivery (which may differ by rounding from bounded raw arrays).
There is no clipping or changed bound. Adapter receives original proposer raw
actions exactly as the baseline did. Actual states are cast FP32 and normalized
once with checkpoint state coefficients; actual LeWM encodings normalize once
with checkpoint latent coefficients. Original adapter prediction is already
normalized and stays fixed in the latent-only condition.

Capture original raw goal latent directly: do not reconstruct it by reversing
normalization. All conditions' scoring rollouts start from the ORIGINAL
predicted first-terminal latent. Actual latent enters only second-proposer
conditioning in the latent/joint conditions. First-bank immediate score is
raw-latent squared Euclidean distance to the original goal. Continuation score
is the mean of the lowest two of eight costs; argmin picks the first tie.
Greedy64 and continuation share exactly one first bank. No existing greedy300
or greedy576 arm is replaced.

## Physical intervention and termination

For each first candidate: construct fresh R3 environment, replay the exact
historical prefix, check anchor image/state/controller/goal, then execute at
most15 decoded actions. Native termination or truncation stops immediately.
Only branches active after all15 actions have a well-defined duration15
intermediate intervention. For already terminated branches, retain baseline
proposer inputs in ALL conditions, mark them inactive, and report first-chunk
success separately; never fabricate a successor at t15 or step after terminal.
This masking is part of the declared diagnostic, not a deployable oracle.

Then execute one selected physical two-chunk branch per condition: select first
branch by unchanged best-two-mean score; within that branch choose its minimum
predicted-cost second chunk (first-index tie). This is an explicitly diagnostic
30-action branch test, NOT what unchanged MPC executes after replanning. Also
execute greedy64's selected FIRST chunk. Retain every first-candidate physical
trace, the five selected traces, all candidate banks, all costs and masks.
It does NOT physically evaluate all2048 second candidates per anchor; do not
claim exhaustive second-bank ranking/coverage or distant-goal performance.

First-chunk comparisons use the same15-action cap for every selector. Report
committed two-chunk results only among the four context conditions, separately
from greedy64. Terminal flags do not filter candidates or add a success bonus
to selection. Report success/truncation/inactive counts and qualify active-only
errors. First-chunk physical oracle metric is the closest SAME-STEP maximum
of joint-position-distance/20 and historical-angle-error/(pi/9), excluding t0.
It is not a distant-goal oracle. No second-bank physical oracle is measured.

Maximum69 branch rollouts per active anchor (64first+4selectedtwo+1greedy),
1104 per repeat across all four records, 2208 across both repeats. Max physical
steps per anchor =64*(anchor+15)+4*(anchor+30)+(anchor+15)=69*anchor+1095,
plus each process's <=31 historical baseline actions per horizon. Worst case
68656 delivered/replayed primitive steps across both repeats. No hidden tail.
Overall remaining budget2H-anchor is respected. E18 delta=H-(elapsed mod H)
is75/45/150/120 at the specified anchors, tau15, second delta=delta-15.

## Acceptance and resource accounting

One A6000 allocation at a time, eight jobs (one reference x fresh repeat),
<=2hours/job; no new training. Before execution, CPU helper tests plus pinned
runtime imports/source checks must pass. Each job fails closed on replay,
identity, normalization, noise, bank or source mismatch. Technical failures
preserve outputs; do not reinterpret partial scientific outputs. After all
eight succeed, independently verify every seal, array identity across repeats,
selection arithmetic, active masks, supplied conditions, reference identities
and no-protected/no-training flags before aggregate interpretation.

The independent NumPy verifier requires exact repeat array bytes, decoded
actions, score/selector arithmetic and unchanged input components. Independent
FP32 normalization arithmetic allows rtol/atol1e-6; independent192-dimensional
squared-cost sums allow rtol2e-6/atol1e-5 for reduction-order roundoff. These
validation tolerances do not change planner selection, simulator replay or
historical success thresholds. Repeated simulator traces remain byte-exact.

Report measured GPU/CPU time, peak memory, bytes, branch/step counts and the
bounded32-reference extrapolation. Means on these four development records are
not efficacy estimates. Long-budget tail policy is UNRUN; no irrecoverability,
full coverage or publication novelty claim. No32-reference expansion launches
without review of measured pilot cost and findings.
