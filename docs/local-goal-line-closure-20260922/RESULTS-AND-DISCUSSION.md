# Local-goal proposals and refinement budget: results and discussion

## Question and shared-planner boundary

The local-goal development line asked whether a diffusion action proposer
could improve native closed-loop success relative to a matched conditional
Gaussian-mixture proposer within a common planner. This was a narrower question
than whether diffusion planning is generally useful. Local targets were
generated separately from the action proposer. Both families received the same
information definition and used the same world model, decoder, initialization,
action-support projection and local-target schedule. The intervention was the
proposer family, followed by a specified amount of common cross-entropy-method
(CEM) refinement. The local GMM comparator was not the released native SAGE
system. Neither historical continuation nor native SAGE was a live arm in this
line's main comparisons. [LGP1, “What was actually compared”][lgp1]

This boundary matters when interpreting either a positive or a negative result.
It holds much of the downstream planner fixed, but does not make the two
learning problems or their compute identical. GMM and diffusion have different
training objectives and proposal-generation procedures. Equal architecture
width, training rows and update counts are not equal optimization difficulty
or FLOPs. Conversely, a successful result elsewhere for a diffusion selector
need not carry over to a local proposer embedded in repeated refinement.
The experiments therefore evaluate specified systems, not an unrestricted
comparison between all possible diffusion and Gaussian methods. Continuation
is retained as the working system through a prospective priority decision,
not because RB2 measured its superiority over these arms. [LGP1][lgp1]

## LGP1: the matched thirty-population comparison

LGP1 evaluated 32 already-exposed source references at two goal horizons and
three fixed seed blocks. Each family therefore contributed 192 main episodes,
with 384 main episodes in total. The shared planner used 300 candidates per
population, 30 elites, 15-action chunks, FP32 refinement, support projection and
a projected final-elite-mean return. H75 and H150 had physical budgets of 150
and 300 primitive actions. At thirty scored populations, GMM succeeded in
28/192 episodes (14.5833%) and diffusion in 26/192 (13.5417%). The source-weighted
diffusion-minus-GMM estimate was −1.0417 percentage points. LGP1's original
descriptive 95% source-bootstrap interval was [−7.292, +5.208] points, as
published. It did not establish an advantage for diffusion or equivalence
between the families. [LGP1, “Primary native closed-loop result”][lgp1]

Diffusion had lower best-of-300 offline action reconstruction error for each
of the three fixed models, but this did not translate into higher measured
native success. That separation between an offline diagnostic and the
closed-loop endpoint is informative without identifying a cause. Target
mismatch, world-model ranking, refinement and training allocation remained
possible limitations rather than demonstrated faults. Planning also involved
different visited trajectories and contexts across arms, so their predicted
cost summaries were not a paired common-state causal intervention. The
correct historical conclusion was to retain continuation and promote neither
new proposer. The present closure preserves that conclusion and all original
recovery and accounting records. [LGP1, “Supporting measurements” and
“Bounded interpretation and recommendation”][lgp1]

## LGP-RB1: a small-source budget map

RB1 tested one and five scored populations while reusing the historical
thirty-population episodes. The initial proposal counts as a scored population.
It kept the six LGP1 models unchanged and retained the same 32 exposed sources,
two horizons and three seeds. Thus 768 new episodes and 384 reused episodes
did not create 1,152 independent sources. At one population, GMM achieved
1.5625% success and diffusion 5.2083%. At five, their rates were 9.8958% and
13.0208%; at thirty, the reused rates remained 14.5833% and 13.5417%.
The five-population difference was +3.1250 points [−3.6458, +9.8958], and
the thirty-population difference was −1.0417 points [−7.8125, +5.2083].
[RB1, “Native success and paired contrasts”][rb1]

RB1's thirty-population interval is its own already-published interval under
the frozen RB1 resampling seed. It does not replace LGP1's original interval
for the same reused outcomes. Figure A reproduces RB1's intervals in its
32-source panel and RB2's intervals in a separate 512-source panel. It makes
no pooled estimate. RB1's five-minus-thirty change in the family difference
was +4.1667 points [−5.7292, +14.0625]. Its one-minus-thirty change was
+4.6875 points [−2.0833, +11.9792]. Neither interval established the
prespecified budget interaction, even though the one-population family
contrast itself had a positive descriptive interval. [RB1][rb1]

The small-source pattern nevertheless motivated a concrete development
replication: diffusion at five populations appeared numerically close to its
own thirty-population success, with lower measured planning time. “Close”
was not an equivalence result, and choosing this operating point was
outcome-informed. RB1 measured five-population planning means of 204.257 ms
per stage for GMM and 229.100 ms for diffusion, versus 757.802 and 781.561 ms
for the reused thirty-population runs. These are averages over actual visited
stages, not matched-state measurements. Historical thirty-population complete
episode/reset timers were unavailable and were not reconstructed. RB1
therefore motivated replication of a limited success–compute pattern, not a
claim that CEM had erased an intrinsic diffusion advantage. [RB1, “Measured
computation” and “Bounded interpretation”][rb1]

## LGP-RB2: fixed development replication

RB2 used a new 512-source cohort selected by the frozen identifier hash order
within exposed reference IDs 0–1599. Excluding 320 distinct registered role
IDs left 1,280 eligible sources, of which 512 were allocated and 768 left
unused. This established separation from the specified recent method roles.
It did not turn an exposed benchmark into untouched confirmation or prove
that every frozen component was universally source-unseen. No old 32-source
outcomes were pooled into RB2, and no favorable source or seed was substituted.
The six final LGP1 models were reused unchanged. There was no additional
fitting, optimizer work or new learning-label construction. [RB2, “Fixed
question and population”][rb2]

The four fixed arms were GMM5, diffusion5, GMM30 and diffusion30, crossed with
H75/H150 and seed blocks 8301/8302/8303. Each arm contained 3,072 episodes,
giving 12,288 fresh episodes. Every cell had its own World, policy, history,
buffers and random streams. A job shared a read-only backend and the two
seed-specific models, while an eight-cell rotation balanced order. Proposal
seeds omitted budget and order, with a separate refinement stream. Common
initial-bank checks did not assert common states after trajectories diverged.
The included first four jobs passed their technical gate before the remainder
was submitted. All 1,537 research jobs, including the final CPU analysis,
completed successfully with no research failure or retry. [RB2][rb2]

Native success required the combined agent/block position norm to be below
20 and the reviewed angle difference below π/9 at the same post-action step.
Initial-state success at t0 was excluded. A successful episode could terminate
early; physical budgets and legitimate terminal conditions otherwise governed
execution. The source reference was the statistical unit. Outcomes were
averaged equally over two horizons and three fixed seed blocks within each
source, and sources received equal weight. The published 95% intervals used
the frozen 10,000-resample whole-source percentile bootstrap with seed
20260920. The present synthesis copies those estimates and intervals; it
does not rerun that analysis or treat episode rows as independent trials.
[RB2, “All four arms”][rb2]

## Success, contrasts and replication outcome

| RB2 arm | Native successes / episodes | Success | Published 95% source interval |
| --- | ---: | ---: | --- |
| GMM5 | 464 / 3,072 | 15.1042% | [13.2813%, 16.8945%] |
| Diffusion5 | 441 / 3,072 | 14.3555% | [12.6302%, 16.1784%] |
| GMM30 | 550 / 3,072 | 17.9036% | [16.1784%, 19.6615%] |
| Diffusion30 | 526 / 3,072 | 17.1224% | [15.2669%, 19.0104%] |

The primary diffusion5-minus-GMM5 contrast was −0.7487 percentage points
[−2.0833, +0.5859]. Thus the development-selected five-population diffusion
lead did not replicate on this 512-source cohort. The observed ordering was
reversed, and the interval did not establish diffusion superiority. This is
not evidence of equivalence, nor proof that diffusion is universally worse.
The interval still allows small positive effects and larger negative effects
under the study's conditional estimand. There was no registered equivalence
or noninferiority margin to apply after seeing these results. [RB2][rb2]

| Prespecified RB2 contrast | Estimate (percentage points) | Published 95% interval |
| --- | ---: | --- |
| Primary: D5 − G5 | −0.7487 | [−2.0833, +0.5859] |
| D30 − G30 | −0.7813 | [−2.3438, +0.7813] |
| (D5 − G5) − (D30 − G30) | +0.0326 | [−1.9531, +2.0508] |
| D5 − D30 | −2.7669 | [−4.4596, −1.0409] |
| D5 − G30 | −3.5482 | [−5.2083, −1.8229] |

The interaction point estimate was near zero and its interval spanned both
directions. The hypothesis that reduced refinement preferentially revealed a
diffusion benefit was therefore unsupported, not disproven in every possible
setting. The two cross-budget contrasts were negative, but their intervals
are descriptive secondaries, not multiplicity-adjusted discoveries. They do
not identify a diffusion-specific causal mechanism. Full disclosure already
includes all 512 source effects and all 24 arm/horizon/seed strata. None is
selected here to rescue the primary finding. [RB2, “All four arms”][rb2]

## Measured success–computation trade-off

Figure B plots all four RB2 success rates against mean measured complete-episode
time. The means are only arithmetic divisions of the published episode-time
totals by 3,072: approximately 3.254 s for GMM5, 3.620 s for diffusion5,
11.014 s for GMM30 and 11.368 s for diffusion30. Vertical intervals are the
published success intervals; no time interval is invented. Both families had
lower measured episode time and lower point-estimated success at five than
at thirty populations. The descriptive success increases from five to thirty
were 2.7995 points for GMM and 2.7669 for diffusion. That shared pattern is a
success–compute trade-off, not evidence of statistical Pareto dominance or
equal-budget causal effects at identical visited states. [RB2, “Timing,
allocation and memory”][rb2]

Complete-episode timing includes World construction, initialization/reset,
planning, physical delivery, evidence saving/verification and World close.
It excludes shared backend/model setup, reported separately as 14,409.113 s
over the jobs. It therefore measures instrumented episodes rather than bare
model latency or fully amortized deployment cost. Planning means per visited
stage were 0.172633/0.196667 s for GMM5/diffusion5 and 0.725899/0.749793 s
for GMM30/diffusion30. Proposal means were about 7.2 ms for GMM and 31 ms for
diffusion. Much of the thirty-population runtime was shared refinement.
Scoring is already inside refinement, while fingerprinting overlaps planning
and refinement; adding these timers or subtracting all fingerprint time from
one component would misstate measured cost. [RB2][rb2]

The complete study charged 138,753 GPU allocation seconds, or 38.5425 A6000
hours, and 161 allocation-wall seconds for the GPU-free CPU analysis. Recorded
worker process CPU totaled 122,546.557 s. These are distinct quantities, and
four arms shared each GPU allocation, so there is no measured arm-level
allocation or worker-CPU split. Peak Python RSS was 1,647,009,792 bytes for
one worker process, not the full simulator child-process tree. Peak Torch
allocated GPU memory was 294,831,104 bytes, excluding reserved allocator
memory, context and driver memory. The 2,597,484 delivered actions and repeated
candidate evaluations are work counts, not additional independent evidence.
[RB2, “Actions, planning and model/scoring work” and “Timing”][rb2]

## Relationship to earlier evidence

Earlier positive evidence remains valid within its original scope. E11's
untouched-D3 short-horizon study used 400 starts per task on PushT, Reacher
and Cube, three fixed seed blocks, and binary success under each released
task callable. It reported diffusion minus matched Gaussian at +2.75 points
[+1.64, +3.89] and passed its registered comparison with a published-equation
ACID reconstruction, not official ACID. Its 11.23× measured elapsed-time ratio
was inference/evaluation timing excluding up-front proposal training. The
independent PushT study instead used 1,600 weak-policy-generated references,
H75/H150, fresh-state execution and its explicit post-action position/angle
predicate. Continuation passed the registered internal comparisons with
greedy VAD-300 and Gaussian continuation but stopped at the first-look futility
rule against released full SAGE. Its 7.432 solver-call median ratio excluded
surrounding work and was not end-to-end speed or noninferiority. Those bounds
used sequential comparison spending, unlike RB2's descriptive bootstrap.
These are separate populations, comparators and claim limits, not successive
points on an absolute-success time series. [E11 result][e11]; [E11 protocol,
§7][e11protocol]; [independent PushT result][independent]; [independent protocol,
“Execution”][independentprotocol]

## Interpretation and prospective closure

Taken together, this local-goal line does not establish a proposer-family
advantage that warrants promotion. LGP1 did not translate diffusion's offline
coverage improvement into higher native success. RB1 supplied a limited,
uncertain budget map. RB2 tested the selected five-population operating point
on a substantially larger, role-disjoint development cohort and did not
reproduce its lead or support the proposed budget interaction. This is a
useful negative development result with a measured resource trade-off, not a
blanket negative verdict on diffusion, a claim of universal GMM superiority,
or proof that refinement destroyed useful proposals. No untested causal fault
is assigned to the generator, decoder, world model, sampler or training.

The priority decision is consequently to close the present proposer-and-budget
line for now, retain continuation and promote neither local proposer.
No further round-count, seed, return-rule, sampler or training search follows
from this decision. The overall thesis is not declared finished. Existing
results, source allocations, checkpoints and E12 drafts remain unchanged.
RB2's scientific output was authenticated and preserved through the separately
authorized R1 transfer recovery before publication. The failed original copy
remains recorded; R1 changed preservation location, not scientific outcomes.
This closure uses those completed records without new simulations, inference,
resampling, subgroup analysis, archive creation or bulk transfer. [R1 location
and receipt][r1]; [prospective decision](DECISION.md)

[lgp1]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/07aa9bbe30a3bd89dcae6f3ad1f713979f2048c1/docs/local-goal-proposals-20260918/FINAL-REPORT.md
[rb1]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/8a79e267cb0cb7b6243900cb3bc194e0eb069a85/docs/local-goal-search-budget-20260919/FINAL-REPORT.md
[rb2]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/0b6507fc7398eb0624d0755035db22e666de74d5/docs/local-goal-source-replication-publication-20260920/completion-v6/FINAL-REPORT.md
[r1]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/28cbcf18ec16bcb496132c7c9bd0204a7cf2eca9/docs/local-goal-source-replication-publication-20260920/preservation-recovery-r1/LOCATION-AND-RECEIPT.md
[e11]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E11-PURE-VELOCITY-UNTOUCHED-D3-RESULT-2026-08-18.md
[e11protocol]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E11-PURE-VELOCITY-UNTOUCHED-D3-PROTOCOL-2026-08-17.md
[independent]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/INDEPENDENT-PUSHT-RESULT-2026-09-07.md
[independentprotocol]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/INDEPENDENT-PUSHT-PROTOCOL.md
