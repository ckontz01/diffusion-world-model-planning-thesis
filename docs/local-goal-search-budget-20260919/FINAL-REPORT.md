# LGP-RB1 completed development result — 20 September 2026

The exact fixed comparison completed, authenticated and externally preserved.
All 387 allocations succeeded: two compatibility GPU jobs, 384 paired-horizon
main GPU jobs and one CPU analysis. No failures, retries, training or optimizer
updates occurred. The 768 new episodes and 384 reused LGP1 episodes cover the
same 32 exposed sources; they are not 1,152 independent sources. Continuation
is retained; neither proposer is promoted. Historical LGP1 remains unchanged.

## Native success and paired contrasts

Each family/budget has 192 episodes (32 sources × two horizons × three seeds).
Within each source the six outcomes receive equal weight. Intervals below
are the frozen 10,000-resample, whole-source percentile bootstrap, seed20260919.
All differences are diffusion minus GMM, in percentage points (pp).

| Total scored populations | GMM native success | Diffusion native success | Paired difference, pp | Descriptive 95% interval, pp |
| --- | ---: | ---: | ---: | --- |
| 1 (new) | 3/192 = 1.5625% | 10/192 = 5.2083% | +3.6458 | [+1.0417, +6.7708] |
| 5 (new) | 19/192 = 9.8958% | 25/192 = 13.0208% | +3.1250 | [−3.6458, +9.8958] |
| 30 (reused) | 28/192 = 14.5833% | 26/192 = 13.5417% | −1.0417 | [−7.8125, +5.2083] |

The prespecified changes in the family difference relative to30 are:

- Budget1 minus30: **+4.6875pp**, interval **[−2.0833,+11.9792]pp**.
- Budget5 minus30: **+4.1667pp**, interval **[−5.7292,+14.0625]pp**.

The reused30 counts and source effects are unchanged. Its interval here uses
the newly frozen RB1 resampling seed; this is not an amendment to LGP1's
original interval. These outcome-informed development summaries are not
confirmatory findings or multiplicity-adjusted discoveries. In particular,
the positive budget1 interval does not establish the prespecified interaction:
both changes-relative-to30 intervals include zero.

[All 32 source effects and all horizon/seed strata](FINAL-SOURCE-EFFECTS.md),
[all 1,152 episode identities/outcomes with provenance](FINAL-EPISODES.json),
and the [aggregate projection](FINAL-AGGREGATE-PROJECTION.json) are published.
No source, seed or budget was selected for favorable presentation.

## Measured computation and delivered actions

Values below are measured, not30/n extrapolations. Stage values are pooled
means over each configuration's actual visited stages, not matched-state
comparisons. Every row contains96 two-horizon jobs. Old30 allocations are
historical charges, not new charges.

| Populations / family | Actions | Planning stages | Proposal ms/stage | Refinement ms/stage | Total planning ms/stage | GPU allocation seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 GMM | 43,039 | 2,870 | 11.127 | 38.150 | 114.722 | 2,383 |
| 1 diffusion | 42,404 | 2,832 | 33.950 | 39.361 | 139.056 | 2,487 |
| 5 GMM | 41,686 | 2,784 | 11.297 | 126.718 | 204.257 | 2,730 |
| 5 diffusion | 40,918 | 2,735 | 34.114 | 128.397 | 229.100 | 2,789 |
| 30 GMM, reused | 41,166 | 2,753 | 11.413 | 679.685 | 757.802 | 4,438 |
| 30 diffusion, reused | 40,932 | 2,732 | 34.239 | 680.144 | 781.561 | 5,120 |

New complete episode-driver times summed over192 episodes are470.816s,
532.995s,705.120s and760.880s respectively in the first four rows. Model/setup
times over96 jobs are926.065s,945.553s,962.260s and955.709s. These do not include
every wrapper/authentication/sealing cost; whole allocation remains the
complete-job measure. Historical30 separate reset/episode timers were not
saved and are unavailable, not reconstructed.

The new main executions delivered168,047 physical actions over11,221 planning
stages, with33,297 batched LeWM cost calls scoring9,989,100 candidate trajectories
(149,836,500 predicted primitive steps). Proposers supply the initial bank at
each stage; these are not9.99million independent model trials. Compatibility
adds16 first decisions and79,200 candidate trajectories, but zero delivered
actions and zero completed episodes. All budgets retain300 candidates,
30 elites and the projected final-elite-mean return.

Scoring is a subset of refinement and must not be added again. Context
encoding/local-target generation and small unpartitioned gaps are part of
total planning. New bank fingerprint times total0.401/0.411/0.388/0.398s in
the first four rows; projected hashing lies inside refinement and unprojected
hashing outside it. Do not subtract the combined timer from one component.
Historical30 had no fingerprint instrumentation. Actual trajectories, stage
counts and instrumentation differ; equal candidate counts do not mean equal
compute. Full per-configuration timing/call totals are in
[FINAL-ACCOUNTING.json](FINAL-ACCOUNTING.json).

## Execution, technical validity and resource accounting

Slurm302186–302572:387 unique jobs, all COMPLETED0:0. Compatibility302186/302187
used27/24s and passed before any main submission. Both families passed exact
common-state initial-bank equality and legacy30/new30 returned-action/round
summary checks on the16 specified first decisions. That does not claim equality
against historical raw banks, which were never saved, or identical banks after
physical trajectories diverge. All six checkpoint identities and the original
freeze were verified. Proposal seeds omit budget; proposal/refinement streams
remain separate.

New allocation totals: **10,440 GPU seconds =2.9 GPU-hours**, including51s
compatibility; **16 CPU allocation-wall seconds** for analysis302572. Caps were
70,320 and7,200 respectively. Recorded worker Python process CPU totals
6,373.499s, including7.687s analysis; Slurm's returned TotalCPU zeros are not
used as actual CPU estimates. The controller used13,011.591s wall /60.566s CPU.
Queue waiting is excluded from allocation charges but included in controller
elapsed time.

Maximum worker Python RSS was1,601,638,400bytes; maximum PyTorch allocated GPU
memory241,042,944bytes. Analysis RSS55,672,832bytes. These scopes exclude
unmeasured child-process memory and CUDA context/reserved memory; they are not
whole-node peak measurements. Resource requests remained4CPU/24GiB with one
A6000 serially, and4CPU/8GiB without GPU for the single analysis.

The sealed analyzer independently reconstructed all1,152 endpoints from
the authenticated initial/goal identities, delivered actions, post-action
physical states, terminal/truncation flags and schedule. It retained the native
combined-position/angle predicate, excludedt0, required full budgets absent
legitimate termination, and checked population/call counts and model/source
lineage. All387 worker/aggregate seals and192 historical worker seals passed
post-completion authentication. The768 new endpoint NPZs have maximum18,817bytes,
below50,000. No partial scientific effects were inspected before preservation.

## Storage, preservation and published identity

New worker bytes71,641,667; source/control/log bytes2,608,083. Inclusive remote
occupancy after final archive/request:3,619,945,254bytes, below8,000,000,000.
The final archive is79,155,200bytes /2,798 members. All copied member hashes and
whole archive bytes passed on THESIS_SSD volume
`0a2f1ba9-0000-0000-0000-100000000000`, initially329,512,144,896bytes free.
Destination: `D:/THESIS-BACKUPS/local-goal-search-budget-20260919/run-a0bcdb48029909e0`.
The whole historical LGP1 archive (1,734,420,480bytes /1,733 members) was
reverified in place. New source/run/controller/logs plus historical source,
models, endpoints and failures are covered by that archive union. The original
preparation archive remains unchanged. There was no laptop backup fallback.

Host archive construction/member verification used5.842s wall /3.384s CPU;
SSD old-archive verification plus transfer/new-member verification used14.094s.
This is preservation overhead, not GPU compute or analysis allocation.

| Artifact | SHA-256 |
| --- | --- |
| Executed source manifest | `a0bcdb48029909e0b54a86d8b59c54fc4fa60a3734a9634c761e5caea4c9778b` |
| Separate execution approval | `76365cdc4cffc323a9182fa48c883c2fd9258f358737fa6294196b102debec1c` |
| Unchanged input lock | `b21bac97520696b8bb2008a3cfef3f5188d4c59dd117bc158cc2fe2e86ff5aaa` |
| Original six-model freeze | `a8a5a0ff456cd870e540f838d2c8b62d00b542be6d7a2da53b377fbd91cbc305` |
| Complete aggregate | `d37b483b986f3d4f9da82cc6d9d605dbc4bf11bde681bd09c633338872540f6a` |
| Aggregate adjacent seal | `1f7875497c1b1a087e3eec27d41cc1a3a560e4277d9f487ce45aca46a409bbec` |
| Compute-complete record | `841065f821e02ca080a70b2f0b5e2797da68ad854bcdf6b913438e7c7f9a727f` |
| New final archive | `72c2717be4a10b0e103a05c6575710832e5ae4c9e9a21be573c8cb3c4441f175` |
| Historical final archive | `24609c83f6c21d99edc579229ab990db184c6e0fa1133ebad4336882c35189fd` |

The new stdlib-only publication script reads completed authenticated archive
members; it does not modify the executed source or scientific analysis.
Nine publication consistency checks passed. The33 exported synthetic tests
and both real compatibility jobs are inherited execution evidence, not claimed
as rerun for this report. No filesystem/dependency/permission repair was made.
E12 drafts and protected/reserved payloads were untouched.

## Bounded interpretation and handoff

Diffusion's relative point estimate is more favorable with less refinement,
but budget1 has very low absolute success. Budget5 diffusion is numerically
close to its own30-budget success, not established equivalent. The uncertain
changes in family difference do not prove that CEM erases a diffusion advantage,
and visited-state summaries cannot identify that mechanism. Faster measured
planning at reduced budgets is real here, but is not a general matched-compute
dominance result or a favorable-budget confirmation.

Recommendation: retain continuation and promote neither proposer; use the full
success–computation pattern, not the best cell, to motivate at most one clearly
specified mechanism question. Per the user's20September delegation, this final
record will be sent to the selected GPT-6 Pro conversation for interpretation
and bounded next directions. Any new study gets its own immutable protocol,
roles and finite envelope; this record and all prior decisions remain unchanged.
