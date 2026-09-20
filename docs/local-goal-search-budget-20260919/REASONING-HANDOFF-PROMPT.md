# LGP-RB1 completed result — worker handoff to GPT-6 Pro

The complete fixed study is finished, authenticated, backed up and committed.
Remote commit read-back matched **8a79e267cb0cb7b6243900cb3bc194e0eb069a85** on
`local-goal-search-budget-preparation-20260919`.

Immutable complete report:
https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/8a79e267cb0cb7b6243900cb3bc194e0eb069a85/docs/local-goal-search-budget-20260919/FINAL-REPORT.md

All32 source effects and all horizon/seed strata:
https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/8a79e267cb0cb7b6243900cb3bc194e0eb069a85/docs/local-goal-search-budget-20260919/FINAL-SOURCE-EFFECTS.md

Machine-readable aggregate projection, all episode identities/outcomes and accounting:
https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/8a79e267cb0cb7b6243900cb3bc194e0eb069a85/docs/local-goal-search-budget-20260919/FINAL-AGGREGATE-PROJECTION.json
https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/8a79e267cb0cb7b6243900cb3bc194e0eb069a85/docs/local-goal-search-budget-20260919/FINAL-EPISODES.json
https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/8a79e267cb0cb7b6243900cb3bc194e0eb069a85/docs/local-goal-search-budget-20260919/FINAL-ACCOUNTING.json

## Exact completion and preservation

All387 unique allocations302186–302572 COMPLETED0:0: two compatibilityGPU,
384 mainGPU jobs (two horizons each), oneCPU analysis. No failures, retries,
new fitting, optimizer updates or training data. Same six final LGP1 models,
32 exposed references, seeds8301/8302/8303, H75/H150, physical budgets150/300.
768 new main episodes at1/5 total scored populations plus384 unchanged reused
30-population episodes, preserving original provenance.300 candidates,
30 elites, projected final-elite-mean return everywhere. All sources/seeds
reported; no best-candidate return, scalar-evaluator revision or comparator added.

Both real first-decision compatibility jobs passed before main submission:
16 queries, no physical actions or complete episodes, common-state initial
proposal bank equality and exact legacy30/new30 actions/round summaries.
Budget absent from proposal seeds, refinement streams separate. Actual
trajectories/history thereafter. No claim of equality with unsaved historical
raw banks. Checkpoint/source/input/freeze identities, all adjacent seals,
full grid/order/resource caps and independent saved-state endpoint checks passed.
No scientific effects were read before verified external preservation.

New archive79,155,200bytes/2,798 members, SHA256
72c2717be4a10b0e103a05c6575710832e5ae4c9e9a21be573c8cb3c4441f175.
Verified on THESIS_SSD alongside the whole historical1,734,420,480-byte,
1,733-member LGP1 archive SHA256
24609c83f6c21d99edc579229ab990db184c6e0fa1133ebad4336882c35189fd.
New source/run/controllers/logs and all historical lineage are covered.
Aggregate SHA256 d37b483b986f3d4f9da82cc6d9d605dbc4bf11bde681bd09c633338872540f6a.

## Native success

Each family/budget has192 episodes;32 whole sources are the clustering units.
Within-source horizons/training seeds equally weighted. Differences in pp:

| Total populations | GMM | Diffusion | Diffusion−GMM | Descriptive95% source-bootstrap interval |
| --- | --- | --- | --- | --- |
| 1 new | 3/192=1.5625% | 10/192=5.2083% | +3.6458pp | [+1.0417,+6.7708]pp |
| 5 new | 19/192=9.8958% | 25/192=13.0208% | +3.1250pp | [−3.6458,+9.8958]pp |
| 30 reused | 28/192=14.5833% | 26/192=13.5417% | −1.0417pp | [−7.8125,+5.2083]pp |

Prespecified family-difference changes relative to30:
1−30: +4.6875pp [−2.0833,+11.9792].
5−30: +4.1667pp [−5.7292,+14.0625].
Frozen10,000 whole-source bootstrap resamples, seed20260919, shared across
configurations. Reused30 interval recomputed with this prespecified seed;
original LGP1 interval/result untouched. Descriptive outcome-informed development,
not confirmation, no multiplicity-adjusted claim or favorable-budget selection.

## Actual computation

Pooled observed proposal/refinement/total-planning milliseconds per stage,
followed by complete GPU allocation seconds per96 paired-horizon jobs:

- 1 GMM:11.127 /38.150 /114.722ms;2,383s allocation.
- 1 diffusion:33.950 /39.361 /139.056ms;2,487s.
- 5 GMM:11.297 /126.718 /204.257ms;2,730s.
- 5 diffusion:34.114 /128.397 /229.100ms;2,789s.
- 30 GMM reused:11.413 /679.685 /757.802ms;4,438 historical seconds.
- 30 diffusion reused:34.239 /680.144 /781.561ms;5,120 historical seconds.

New episode-driver totals470.816/532.995/705.120/760.880s in the first four
rows; separate old30 episode/reset timing unavailable. New main168,047 delivered
actions,11,221 planning stages,33,297 batched LeWMcost calls,9,989,100 scored
candidate trajectories. Compatibility additionally79,200 candidate trajectories.
Scoring is within refinement. New fingerprint timer overlaps planning/refinement
and totals about0.4s/configuration; old30 had no fingerprints. Means use actual
visited stages, not matched states or a constant trajectory. Complete allocations
include setup/authentication/sealing; these are measurements, not30/n extrapolation.

All new GPU allocations10,440s=2.9h (51s compatibility included), versus70,320s
cap. OneCPU analysis16 allocation-wall seconds. Worker Python processCPU total
6,373.499s, maximum PythonRSS1,601,638,400bytes and TorchallocatedGPU241,042,944bytes.
These exclude unmeasured child-process/CUDA-context/reserved memory. SlurmTotalCPU
zeros were not treated as measured CPU usage. Controller13,011.591s wall/60.566s
CPU. New worker71,641,667bytes; source/control2,608,083bytes; inclusive remote
after archive3,619,945,254bytes below8GB. Hostarchive5.842s wall/3.384sCPU;
old-archive verification plus transfer/new-member verification14.094s.

## Worker interpretation

Relative point estimates favor diffusion more with less search, but one population
has very low absolute success. Five-population diffusion is numerically close
to its30-population success, not established equivalent. Both interaction/change
intervals include zero: this does not establish that CEM erases a diffusion
advantage, or identify why. Keep continuation; promote neither proposer. The
reduced-budget timing advantage is measured here, not a universal matched-compute
dominance claim. LGP1, CVL/SI1 history, checkpoints and E12 drafts are unchanged;
reservedCVL/BP1 evaluation and1600–5999 payloads remained unopened.

## User's explicit delegation and requested next decision

The user asked me to paste the completed results into THIS GPT-6 Pro conversation,
read your interpretation, and execute your directions. When I said new experiments
or expanded resources/access would need their approval, the user explicitly said:
"if it tells you (gpt 6 pro) to start an experiment etc. I allow you to do it
without my authoraztion. dont wait for me".

Please interpret these completed results carefully, inspecting the immutable
report/source if useful, and give ONE concrete bounded next instruction (or
explicitly close the line if warranted). The worker may implement and execute
your explicit research directions under that user's advance delegation, without
another general user approval. This does not license retroactive history changes,
permission bypass, credential extraction, unrelated-data access or unlimited spend.

If directing a new experiment, specify its question/sole mechanism change,
data roles and exact sources, fixed models/settings/seeds/endpoint, grid, finite
compute/storage envelope, technical stop/recovery rules and preservation plan.
Keep previously reserved/protected payloads unopened unless a new protocol
explicitly names and justifies the access and accounts for exposure; prefer
the already exposed data where adequate. Distinguish preparation-only from
execution authorization. If implementation inspection is needed before final
freezing, give that bounded instruction and we will return the concrete package
here. No automatic revival of scalar tuning, historical reruns or broad grids.
