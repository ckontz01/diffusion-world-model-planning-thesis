# Recomputed A2 finite proposal; no inherited execution envelope

RESOURCE-PLAN.json and wm_diag0_a2.design provide checked arithmetic. Original130h proposal is NOT authority for A2; this grid happens to retain132GPU allocations/468,000 GPU seconds but adds123CPU tasks/13,800s and NEW source work. All figures are maxima conditional on bound native contracts, not measured throughput, actual charge or authorized launch.

| Work | Fixed maximum |
|---|---:|
| Collection |120 roots ×44 actions;5,280 controller steps;5,400 raw RGB frames|
| Bank helper worlds |128 reset+20-action replay worlds|
| Independent oracle prefix |2,048 worlds ×(20 replay+25 prefix)|
| Candidate-tail evaluation |4,096 worlds ×(20 replay+50 diagnostic)|
| Extra included technical restoration checks |8 worlds ×20 replay; no extra candidate tail|
| Total resets/controller actions |6,400 /386,880|
| Readout fit/validation frames over4 settings |1,024 /384|
| Native CEM decisions/sequences |4,224 /38,016,000|
| Retained-bank/extra parity forecast sequences |2,048 /128|
| Macro sequence transitions |190,090,880|
| Cost API calls |126,856|
| Le-WM predictor batch/DINO chunk predictor calls |317,140 /950,740|
| Conservative context/goal encoder calls/frames |253,712 /253,712|
| Additional realized-prefix/readout encoded frames |10,240 /1,408|

HistoryT=1, horizon5, grouped5 distinct controller actions. DINO300-population split100 into3 batches; previous unchunked call total cannot be inherited. Cached DINO contexts can reduce encoder calls, but this conservative maximum grants no arbitrary resampling/reforecasting. Branch-owned tails each at most one replan after25prefix, no unused-native-return reference extra evaluation because slot0 already in bank. Four first-setting jobs each include two16-sequence parity forecasts (eight cost calls total) and two additional reset/replay worlds (eight total). Actual per-layer/action/proprio/encoder physical runtime call multiplicities must be recorded, not mislabeled as one unbatched neural forward. If extra necessary native calls exceed caps, block rather than hide them.

Per task193,440 controller actions. PushT10 substeps each plus2 reset-internal space steps ×3,200 resets =1,940,800 maximum Pymunk integration steps. Reacher2 dm_control advances each =386,880; actual underlying MuJoCo integration count additionally multiplies native n_sub_steps, presently unbound and an execution gate. Rendering/controller/RNG calls are included in reservations; any native initialization settling/integrator work must be declared, not omitted. Source collection performs no world-model calls. Fit jobs encode352 frames/setting and one fixed ridge solve, no hyperparameter search.

## Proposed allocations and failures

Serial one exact NVIDIA RTX6000 Ada on gpu09/gpu09.cluster,4CPU/8GiB perGPU allocation:128 diagnostic root/backbone workers×3600s(3540work+60preserve);4 readout workers×1800s(1740+60). Total468,000 GPU allocation-wall seconds including ALL failures. No GPU is allocated now.

CPU4CPU/8GiB:120 source jobs×60s(45work+15preserve), preflight1200s, independent analysis3600s, one reviewed isolated conversion1800s; cumulative13,800CPU allocation-wall seconds including failures.255 successful logical tasks maximum:132GPU+123CPU. One native generation attempt/root; no replacement allowance. Every root/failed conversion/technical attempt/partial record retained and charged. No resubmission of successful/live/ambiguous work. Full-future reservations and allocation reconciliation required before any authorized technical repair.

Included tranche: first source root per task verifies deterministic complete reset/collection provenance within its counted source job; first diagnostic root in EACH setting checks RGB/no-extra-input, replay/snapshot-if-complete ownership, metadata-only goal installation, paired action/observation equivalence and exact returned-bank/score/forecast/chunk/cache seals. Four first setting jobs are NOT extra pilots or performance filters. Technical restoration/parity overhead counted above. If root unavailable or technical mismatch, stop, retain evidence, no favorable-case replacement. Readout jobs are counted before selector application, no research now.

Timing uncertainty: collection44 actions,45renders+reset/write must fit45s work. Typical controller step assumptions .005/.02/.05s imply .22/.88/2.2s before render/setup, not measurements. Parent max2,980 controller actions (helper20+16×45+32×70), or3,020 for a first-tranche setting (+40), versus old11,800. One33-decision Le-WM timing lead ~99s is inherited saved-input motivation only; DINO8–32× yields792–3168s plus up to152s hypothetical physical stepping and120s setup/encoding/parity. Slow cases/serialization/nativeGPU-memory may exceed3540work; no time increase or timing pilot authorized. Runtime tranche determines compatibility within its already-counted envelope, not scientific efficacy.

## Storage: full future and preparation copies charged

SOURCE-GENERATION44-action frames require120×45×224×224×3=812,851,200B raw RGB.12MB/root permits frames, full origin/source snapshots, action/state/event/hash provenance, capped1.44GB total. Per-step complete states can be hashed while origin/source are preserved; actual complete native-state serialization sizes must be checked. Do not delete needed evidence or truncate state to make it fit.

Le-WM64parent10MB+1MBlog, DINO64parent60MB+1MBlog;2Le-WM readout5MB+1MBlog,2DINO readout140MB+1MBlog. DINO full predicted+realized arrays2×16×5×196×384×4=48,168,960B, goal301,056B; PushT float64 head/mean/scale/intercept4,816,944B, plus action/endpoint/control evidence fits60MB only if authenticated native schema obeys reservation. Readout352×196×384×4=105,971,712B plus head/evidence fits140MB. Preserve original numerical features, never pool/cast to fit. Add123CPU logs≤100KB each, preflight/analysis/conversion evidence60MB, controls300MB and source closures20MB.

Original weights410,653,018B (unchanged Le-WM144,694,193 + acquired DINO/sharedencoder265,958,825); reserve same410,653,018B for separate safe export derived from same bytes, including plain buffers. Isolated compatible runtime image4GB proposed reservation; not acquired/built or evidence that dependency closure fits. Full individual live reservation11,555,606,036B <12GB; slack444,393,964B. Archive≤14GB, nativeSSD archive≤14GB. Complete future topology12GB live+14GB cluster archive+14GB SSD archive+1GB local/preparation/copies=41GB ≤42GB;1GB remaining includes every failed transfer/recovery, not usable without full-future reconciliation.

Opaque artifact acquisition265,958,825B <2GiB. Native originals plus local amendment archive plus SSD amendment archive ≲798MB plus code/metadata, within the1GB future preparation line AND5GiB preparation retained cap. No full research archive staged on Windows: eventual transfer must stream directly to SSD. Acquired source text/code/tests/metadata <1GB separately. Original historical backups are not repeated. The small A2 package's own whole/member SSD verification is NOT scientific acceptance or launch authority.

Local cumulative scripted preparation/tests capped14,400s4CPU/8GiB,600s fully reserved per attempt; share original ledger plus separately recorded2.6799084s receipt-copy work. All A2 attempts including source-path404 retained. Remaining reserve is computed in each receipt. No environment/dependency/security changes, native model forwards/physics, optimizer labels, jobs, monitoring or promotion now.
