# Diffusion proposals for world-model planning

**Christoforos Kontzias · University of Cyprus**

Thesis code and experiment records. Updated 20 September 2026.

**LGP-RB1 completed development update, 20 September 2026:** all768 new
episodes at1/5 scored populations completed, with384 historical30 episodes
reused unchanged. GMM/diffusion successes were3/10,19/25 and28/26 out of192
per family at1/5/30. The diffusion-minus-GMM differences were+3.646,+3.125
and−1.042 percentage points; both changes relative to30 have descriptive
source-bootstrap intervals crossing zero. All387 jobs succeeded and the full
new/historical archive union is verified on THESIS_SSD. Retain continuation;
promote neither proposer. See the [complete result and measured costs](docs/local-goal-search-budget-20260919/FINAL-REPORT.md)
and [all32 sources/horizon/seed strata](docs/local-goal-search-budget-20260919/FINAL-SOURCE-EFFECTS.md).

**LGP1 completed development update, 19 September 2026:** matched local-goal
diffusion achieved 26/192 native successes (13.542%), versus GMM 28/192 (14.583%)
inside the same shared planner. The paired difference was −1.042 percentage
points, with descriptive source-bootstrap interval [−7.292,+5.208] points over
32 already-exposed references. Lower offline action error did not establish
better closed-loop success. All384 main plus eight technical episodes, six
fixed models and final analysis are sealed and externally backed up.
Retain continuation; promote no model or automatic follow-up. Read the
[complete result](docs/local-goal-proposals-20260918/FINAL-REPORT.md) and
[all32 source effects](docs/local-goal-proposals-20260918/FINAL-SOURCE-EFFECTS.md).
The next two paragraphs preserve earlier launch/preparation status, not the
current completion state.

Execution update, 19 September 2026: LGP1's cache and all six fits/validations
are complete and frozen. The first technical episode job stopped before reset
because the policy omitted the pinned World's seed-binding interface. The
[scoped correction/recovery](docs/local-goal-proposals-20260918/POLICY-RECOVERY.md)
reuses every completed artifact; all47 synthetic tests passed locally, from
the export, and in the pinned cluster runtime. The
[recovery launch record](docs/local-goal-proposals-20260918/POLICY-RECOVERY-LAUNCH.md)
now verifies all four real technical jobs (eight episodes) completed successfully,
with unchanged models and sealed evidence. The existing integration/throughput
gate passed and main evaluation began as job301992. The study is not complete;
no partial scientific outcome or efficacy claim is reported.
The following18September paragraph records the earlier preparation status.

Preparation update, 18 September 2026: [LGP1 local-goal proposal comparison](docs/local-goal-proposals-20260918/README.md)
inspects the released SAGE interface and specifies matched new GMM/diffusion
proposers inside one shared planner. Synthetic-only preparation; no launch.
SI1 remains complete, continuation remains the baseline, and no learned evaluator
is promoted. The execution bindings are now implemented and synthetically tested;
real cache inference, fitting, simulation and cluster execution remain untested
and unauthorized. See the [completion record](docs/local-goal-proposals-20260918/IMPLEMENTATION-COMPLETION.md).

This project asks whether diffusion can generate useful action sequences for a learned world model, and whether looking beyond the first sequence helps the planner choose better actions. The world model, Le-WM, stays fixed; the learned action proposer is the part being studied.

The earlier large-scale PushT benchmark is complete. **Continuation-aware diffusion improved on greedy diffusion and Gaussian continuation, but SAGE achieved higher success.** Diffusion used less time per solver call. The results below include both sides of that comparison; they are distinct from the small LGP1 development result above.

That benchmark's code is on [`independent-pusht-benchmark`][code]. Result and source links point to recorded versions so they work from `main` as well.

## How the planner works

The short-horizon method generates 300 complete, 25-action sequences from noise, conditioned on Le-WM's representations of the current observation and goal. Le-WM predicts where each sequence leads, and the planner chooses the one with the lowest predicted goal cost. There is one candidate-selection stage, not an iterative cross-entropy method (CEM) search. The world model still has to roll out each sequence.

The longer-horizon version adds a second action sequence before making that choice. It generates 64 possible first chunks, each 15 actions long, and predicts the state after each one. A learned state adapter supplies the ordinary state-vector inputs needed to generate eight continuations from each predicted state. When the remaining goal offset allows a second chunk, the planner scores each first chunk by the mean cost of its two best continuations. At the last local stage of a planning cycle, it uses the first chunk's immediate goal cost instead. It executes the selected first chunk and replans.

The code calls the proposer **VAD**, for variable-duration action diffusion. This continuation planner was first tested in **E18 (the exploratory continuation study)**. It uses diffusion to propose actions, not to add a feasibility penalty to CEM. The [planner implementation][planner] and [E18 protocol][e18-protocol] give the details.

## Large-scale results: independent PushT evaluation

The study compared six methods on **1,600 independent reference trajectories**, with two goal offsets and three seed blocks: **57,600 individual evaluation runs**. Results were analyzed with repeated horizons and seeds grouped within each reference episode, rather than counted as independent samples.

**H75 and H150** mean that the goal comes from the reference state after 75 or 150 actions. They do not mean that reaching the goal necessarily requires that many actions. Each evaluated planner had a budget of at most twice that offset.

| Method | H75 success | H150 success | Overall success |
|---|---:|---:|---:|
| VAD continuation | 21.19% | 11.42% | 16.30% |
| Greedy VAD-300 | 20.54% | 7.65% | 14.09% |
| Gaussian continuation | 17.44% | 9.29% | 13.36% |
| Greedy VAD-576 | 21.44% | 8.81% | 15.12% |
| GMM continuation | 19.38% | 11.23% | 15.30% |
| Released full SAGE | 26.48% | 15.60% | 21.04% |

The greedy controls rank 300 or 576 first chunks without looking at a second chunk. The Gaussian and Gaussian mixture model (GMM) controls use the continuation structure with different learned proposal distributions. Overall success gives equal weight to both horizons and the three seed blocks.

VAD continuation improved on greedy VAD-300 by **2.21 percentage points** and Gaussian continuation by **2.94 points**. Both comparisons passed their prespecified superiority tests. It trailed SAGE by **4.74 points**. That comparison crossed the predeclared adverse-signal stopping boundary, so the study ended at its first planned analysis rather than continuing to 3,200 or 6,000 episodes. There were no recorded planner failures.

The median timed solver call was **129.7 ms for VAD continuation** and **963.9 ms for SAGE**, a ratio of about **7.43**. This is solver time, not full end-to-end latency. It is a speed–success trade-off, not evidence that diffusion matches SAGE's success rate.

The evaluation data are new trajectories from a fixed block-near random controller, with future states used as reachable goals. All 6,000 collected references passed validation, including 12,000 goal-specific action replays; only the first 1,600 entered the comparison. This is a different population from the earlier expert-data evaluations, so their absolute success rates should not be compared directly.

Read the [full result][latest], [protocol][protocol], or [data card][data-card]. The [result archive][results] contains the exact summary, all 57,600 outcome rows, the episode tensor, checksums, and independent verification. The first-look bounds use the registered allowance for repeated analyses and three primary comparisons; they are not ordinary post-hoc 95% intervals.

## Earlier experiments

The project changed direction several times. This record includes the unsuccessful ideas, the studies stopped before evaluation, and the diagnostics that led to the current implementation. The labels are the ones used in the original files. E labels identify studies rather than software releases; not every number has a standalone experiment behind it.

**How to read the record.** P1–P4 and D1–D5 name data partitions or study-specific evaluation sets. They are not interchangeable. “Development” means the data could inform later design choices; “confirmation” refers to that study's reserved evaluation under its own protocol. “Not run” is different from a negative result. The engineering checks below test implementations, not planning success.

Each entry links to its evidence. Some early outcomes are recorded in the implementation log or the next protocol rather than a separate result report. Earlier success rates use different task populations and, in some cases, different simulator initialization, so they should not be ranked against the latest table.

### 1. The original hierarchical-planning work

These studies used hierarchical Le-WM planning. B0 is the baseline planner; B1 uses an empirical macro bank. M1 measures a macro inverse-cycle residual, M2 uses diffusion denoising error, and M3 predicts temporal separation as a reachability signal. This M2 scorer is not the later diffusion action proposer.

| Study | What was tested and what happened |
|---|---|
| **Hi-LeWM baseline pilot** | The released PushT 25-step setup ran successfully: B0 reached 42/50 successes and B1 43/50 in the clean pilot. This was an operational check, not an exact reproduction of the paper's three-seed results. [Report][baseline-pilot]. |
| **B1 repeatability and macro-bank check** | Repeated B1 GPU evaluations ranged from 84% to 88%, although the empirical macro bank itself was byte-identical. The report did not establish the exact cause of the remaining variation. [Report][baseline-pilot]. |
| **PushT P2 baseline/difficulty check** | Compared B0 and B1 on the longer, 75-step development queries before selecting the main hierarchical evaluation setting. This was a difficulty/setup check, not the later locked P4 result. [Implementation log, A-022–A-026][early-amendments]. |
| **M1, M2 and M3 development** | Trained the macro-cycle, denoising-error and temporal scorers, with matched nulls and an autoencoder control for M2. Model settings, calibration and planning weights were selected on P2 before the PushT P3 audit. [Frozen selections][p3-lock]. |
| **PushT P3 scorer audit** | All three scorers exceeded the required pooled AUROC threshold, but none passed the separate improvement-over-own-null interval test. No learned scorer advanced to P4. [Implementation log, A-043][early-amendments]. |
| **PushT P4 baseline comparison** | On 40 locked queries, B0 succeeded on 8 and B1 on 14. The 15-point difference had an interval of −2.5 to +32.5 points. M1/M2/M3 were not evaluated; this was not a diffusion result. [Implementation log, A-044][early-amendments]. |
| **Cube second-environment gate** | The hierarchical B0/B1 gate did not support using Cube as the second environment, so the program moved to TwoRoom. This was an environment-selection study, not the later flat-planning Cube experiments. [Archived chronology][early-history]. |
| **TwoRoom backbone and scorer preparation** | Converted the released base model, trained the hierarchical component, and built the M1/M2/M3 training and evaluation pipeline. These were preparation and validity checks, not confirmation of a scorer's planning benefit. [Implementation log, A-045–A-074][early-amendments]. |
| **TwoRoom P2 closed-loop development** | Completed the corrected development grid after invalidating an earlier cached-initial-state error. M3 was promising, but the later calibration audit showed that M2's contribution was constant and could not change the planner. [Implementation log, A-088–A-093 and A-099][early-amendments]. |
| **PushT execution-lineage and reset audit** | Rechecked the stored P2/P3 executions and a separate reset probe. No tested initial-label flips were found. The report explicitly did not rule out later trajectory effects; it is not proof against the restoration issue subsequently found in R1/R2. [Implementation log, A-094][early-amendments]. |
| **M2 source-conditioning diagnostic** | M2 used the correct source on genuine transitions, but that did not establish better failure ranking for imagined candidates. [Implementation log, A-095][early-amendments]. |
| **M2 real-frame reachability diagnostic** | On genuine source/target frames, M2's discrimination exceeded its null, autoencoder and incorrect-source controls. This positive offline finding did not establish better CEM choices or closed-loop control. [Implementation log, A-096][early-amendments]. |
| **PushT within-query ranking audit** | The high pooled discrimination scores mostly reflected differences between queries. There was little evidence that M2 reliably ordered candidates within the same query, which is what the planner needs. [Implementation log, A-097][early-amendments]. |
| **TwoRoom within-query ranking audit** | The same limitation appeared for M2 on TwoRoom. M3 had a positive within-query ranking result, still on development data. [Implementation log, A-098][early-amendments]. |
| **M2 calibration/intervention audit** | TwoRoom's fitted M2 calibration slopes were zero, making its cost identical across candidates. The completed weight grid therefore did not test an active diffusion intervention. PushT's M2 contribution was nonconstant. [Implementation log, A-099][early-amendments]. |
| **M2 width/noise-grid reanalysis** | Revisited the already evaluated width and noise settings. No fixed combination gave robust within-query ranking in both environments; the post-hoc maxima were not new confirmation. [Implementation log, A-100][early-amendments]. |
| **M2v2** | Replaced the old scorer with a multinoise conditional-versus-unconditional score and rank calibration. It did change planning, but failed the rule requiring useful results in both environments: selected PushT success was 2/12, tied with B0, while TwoRoom improved to 8/12 from 6/12. [Result][m2v2]. |

### 2. Transition verification and the first ACID comparisons

This phase moved to flat Le-WM planning on PushT, Reacher and Cube. Diffusion initially scored transitions proposed by CEM rather than generating the action candidates itself. ACID numbers here refer to the repository's published-equation reconstruction.

| Study | What was tested and what happened |
|---|---|
| **R0 — ACID reconstruction check** | The reconstruction recovered a positive ACID-over-CEM direction on all three tasks. Passing those direction checks was not exact numerical replication of the published results. [D1 report, section 3][d1]. |
| **D1 / v1 — diffusion transition verifier** | The primary diffusion score did not meet the comparison or action-conditioning requirements. Its aggregate closed-loop success was 3.24 points below reconstructed ACID; a favorable low-weight sensitivity could not replace the primary result. [Result][d1]. |
| **E0 — scalar density-contrast rescoring** | Reused the D1 banks to compare conditional and action-ablated diffusion scores without retraining. The next protocol records the completed result artifact and hash, but no separate E0 result table is available in the linked reports; no numerical E0 verdict is asserted here. [Specification][score-rescue]; [completion record][v2-pilot-protocol]. |
| **E1 — prediction-level guidance** | Recomputed denoising scores with guidance and additional noise draws. Averaging eight draws improved rank association, but the selected true-action score still did not beat its shuffled control. [Recorded findings][v2-pilot-protocol]. |
| **v2 — residual-diffusion pilot** | Trained on heavily corrupted transition residuals with action conditioning and a contrastive loss. Ranking improved over v1, but the primary raw-score advancement rule failed. This was a new model, not just E1 rescoring. [Result][v2-result]. |
| **E2 — action-evidence score** | Tested a conditional-versus-unconditional error contrast using the v2 model. It separated true from shuffled conditioning, but did not pass the full ranking/selection requirements. [Result][v2-result]. |
| **v3 Stage A — multiseed D2 candidate audit** | Residual diffusion beat reconstructed ACID on candidate-error ranking, but failed the required margin against the deterministic forward verifier. The planned v3 Stage B was not run. [Result][v3-result]. |
| **E3 — exposed-D2 closed-loop action evidence** | A separately specified exploratory study tested independently optimized planners. The action-evidence arm reached 79.78%, versus 84.89% for reconstructed ACID and 80.67% for its shuffled control; its promotion rule failed. [Result][e3]. |
| **E4 — inverse-action diffusion evidence** | Moved diffusion into inverse-action space. The models used successor information on real transitions, but the primary calibrated CIDER-tail score failed the candidate-audit rule. The E4 closed-loop stage was not run. [Specification][e4]; [failure recorded in E5][e5]. |
| **E5 — counterfactual-successor evidence** | Compared matching and mismatched successor conditions using the same model and noise. Neither the standalone score nor its forward-verifier combination advanced. [Specification][e5]; [archived outcome][early-history]. |
| **E6 — late-CEM quantile veto** | Used residual diffusion to reject a fixed fraction of candidates late in CEM rather than add a continuously weighted cost. The primary setting failed its advancement rule. [Specification][e6]; [archived outcome][early-history]. |
| **E6D — all-iteration matched controls** | Applied the veto throughout CEM and added the corresponding controls. True residual diffusion reached 85.33%, below the shuffled control's 88.67% and continuous reconstructed ACID's 88.00%. This ended the scalar-verifier branch. [Result][e6d]. |

### 3. Generating actions instead of scoring CEM transitions

| Study | What was tested and what happened |
|---|---|
| **E7 / E7P — first diffusion proposals** | E7 was the proposal-design draft; E7P was the executed P1 selection study. The epsilon-prediction model contained goal information, but sampling from terminal noise was unstable and worse than the conditional Gaussian on every task. It stopped before D2. [Draft][e7-draft]; [result][e7p]. |
| **E8A — Gaussian-anchored diffusion refinement** | Started from a learned Gaussian action proposal and refined it with moderate-noise diffusion. All nine offline advancement checks passed. This was development evidence for a hybrid, not pure diffusion from noise. [Result][e8a]. |
| **E8D — refinement in closed loop** | Learned proposals helped, but true diffusion refinement did not isolate an advantage over both Gaussian and shuffled controls. The frozen diffusion-specific rule failed; no fresh confirmation followed under E8D. [Result][e8d]. |
| **E9 — duplicate study abandoned** | The proposed action-evidence rerun duplicated E3's setup. It was cancelled before a valid evaluation and has no scientific result of its own. [Abandonment record][e9]. |
| **E10V — pure velocity-diffusion proposals** | Replaced epsilon prediction with velocity prediction. One of the 20 declared configurations passed the P1 checks: five denoiser evaluations and guidance 1.5. The selected model beat the Gaussian, shuffled, unconditional and old-epsilon controls under the registered rule. [Result][e10v]. |
| **E10M — multiseed proposal replication** | Kept E10V's selected configuration fixed and tested three model seeds on another P1 evaluation set. All three passed the proposal-quality checks. This justified a separate held-out closed-loop study, not a success-rate claim by itself. [Result][e10m]. |
| **E11 — held-out short-horizon confirmation** | On PushT, Reacher and Cube, diffusion reached **93.39%**, Gaussian **90.64%**, and reconstructed ACID **83.31%**. Diffusion minus Gaussian was **+2.75 points**, with a 95% paired start-cluster interval of **[+1.64, +3.89]**. Most of the larger ACID gap was already present with learned Gaussian proposals; it should not all be attributed to diffusion. [Result][e11]. |
| **E12 Stage A — native PRISM sanity check** | Ran the released PRISM and vanilla-MPPI artifacts on PushT and Cube. The results were close to the released sanity figures, but used different bundles from E11 and were not a matched diffusion comparison. [Result][e12]. |
| **E12 Stage B — matched PRISM component validity** | All nine PRISM-DP reconstruction models passed. Both Gaussian PriorHead variants failed the required validation improvement on every Reacher seed. E12 stopped before its planned efficiency and closed-loop stages; it did not create or consume its D4 holdout. [Result][e12]. |
| **E13 — held-out PRISM-DP comparison** | The narrower study compared the valid PRISM-DP reconstruction with diffusion. At 300 candidates, success was **93.53% versus 92.97%**; the difference was **+0.56 points**, with a 95% interval of **[−0.47, +1.58]**, which did not establish superiority. Diffusion met the specified three-point margin with lower measured resource use. A separate Gaussian comparison failed its Reacher proposal-boundary check. [Result][e13]. |

E11 and E13 retain their original evaluation interfaces. E11's diffusion–Gaussian separation came mainly from PushT and Reacher; Cube was nearly saturated. E13's task effects were mixed: diffusion was lower than PRISM-DP on PushT, higher on Reacher, and tied on Cube. Its 16-candidate comparison was secondary, not a replacement for the 300-candidate primary result.

### 4. Longer goals and continuation planning

| Study | What was tested and what happened |
|---|---|
| **E14 — variable-duration action diffusion (VAD)** | Extended proposals to local durations of 15, 20 and 25 actions and farther goals on PushT/Cube. Offline comparisons with Gaussian and conditioning nulls were positive, but Cube proposals exceeded the registered boundary limit. No closed-loop comparison followed under E14. [Result][e14]. |
| **E14 — coupled subgoal/action diffusion (CVD)** | Jointly generated a local latent subgoal and action sequence. Action coverage and internal consistency improved, but the selected true-local cost was worse than Gaussian and boundary checks also failed. The SAGE reconstruction was trained as part of E14, but not evaluated in closed loop. [Result][e14]. |
| **Post-E14 boundary diagnostic** | Replayed the proposal banks and separated legal expert saturation from raw proposal overshoot. The problem was not mainly Le-WM selecting extreme candidates; it motivated a shared smooth bounded-action representation. [Result][post-e14]. |
| **E15 data preflight** | Built an episode-disjoint development split and checked the common bounded-action transform before model training. The data/representation checks passed; this was not a planning experiment. [Result][e15-data]. |
| **E15 — boundary-aware long-horizon proposals** | Legal-action, diversity and GMM validity checks passed. VAD still failed the required PushT selected-local-cost direction and the unconditional-control comparison. It stopped before the closed-loop SAGE comparison or D5 confirmation. [Result][e15]. |
| **E16 Stage A — exact-bank and ranking diagnostic** | Reproduced E15's banks exactly and found better local options that greedy far-goal ranking missed. A fixed mixture of ordinary and zero-guidance samples worsened selected local cost. The oracle reranking result showed room for improvement, not a working continuation planner. [Result][e16]. |
| **E16 — latent-to-state adapter** | A decoder from a single Le-WM latent passed on PushT but failed on Cube. The planned continuation stages B/C were not run. [Result][e16]. |
| **E17 — action-conditioned state adapter** | Added current state, the proposed action chunk and predicted terminal latent. PushT passed; Cube failed the worst-coordinate error limit despite better overall errors. E17 produced no planner-success result. [Result][e17]. |
| **E18 — exploratory continuation planner** | A separate development study deliberately kept E17's unchanged adapter, including its Cube failure. On 12 starts per task, continuation reached **72.92%** versus **66.67%** for greedy VAD-300. Both development rules passed, but intervals versus greedy-300 and Gaussian still included zero. [Result][e18]. |

E18's clearest exploratory signal was PushT H150: 44.44% for continuation versus 25.00% for both greedy VAD-300 and Gaussian continuation. Cube was ceiling-heavy. The later large independent PushT study at the top of this README is the new evaluation, not a relabelling of this pilot.

### 5. SAGE reproduction and evaluation-interface checks

| Study | What was tested and what happened |
|---|---|
| **E19 — official SAGE release reproduction** | Completed 180 cells and 9,000 episodes with documented compatibility corrections. Only 29/60 published means met the release's ±2-point tolerance; full SAGE met it in 7/12 rows. The official evaluation episodes also overlapped E18 training. This was not an E18-versus-SAGE comparison. [Result][e19]. |
| **E19 initial discrepancy diagnostic** | The sentinel executions completed, but the analyzer's internal-validity check failed. That diagnostic was recorded as invalid, not as evidence that SAGE's computations were wrong. [Result][e19-diagnostic]. |
| **E19-D2 — method-aware reanalysis** | Corrected an impossible history-latent requirement for base CEM and reused the saved artifacts. It found exact-hash repeat differences and JPEG-encoding sensitivity; tested Le-WM runtime and Cube-cache checks passed. These were diagnostic flags, not two proven causes of the paper gap. [Result][e19-d2]. |
| **E19-L1 — field-level localization** | All five tested first planning calls and eight saved CEM-bank replays matched. Later differences first appeared in environment inputs; only 1/250 paired outcomes changed. JPEG/lossless conversion replaced averages of 0.92 and 1.48 of 30 elites, without identifying the authors' encoding. [Result][e19-l1]. |
| **E19-R1 — reset and fixed-action checks** | Twenty valid short traces exposed some PushT block-pose differences before action delivery, while delivered actions matched. Where historical CEM actions were unavailable, saved candidates were labelled diagnostic stimuli, not historical-plan replays. [Result][e19-r1]. |
| **E19-R2 — restoration localization** | Requested PushT fields were exact before the setter's physics step; that step introduced reset-dependent contact-correction motion. Fixed seeds repeated their own shifted states rather than fixing restoration. A separate warning audit identified incorrect signed-velocity bounds. [Result][e19-r2]. |
| **E19-R3 — fresh-state initialization** | The opt-in initializer passed 48 exposed-state scenarios and ten checkpoint-backed arm setup checks. It initializes fresh physics without a hidden simulation step. Missing dynamics have explicit defaults; no full historical state or planner-performance improvement was claimed. [Result][e19-r3]. |
| **Fresh E18 driver integration** | The five unchanged arms completed 50 exposed-record initializations, 128 actual planning calls and 1,363 delivered actions. Relevant normalization, action decoding, replanning and episode lifecycle passed. This closed the scoped PushT integration check, not an efficacy comparison. [Result][fresh-integration]. |

R2 also records two limits of the preceding diagnostics: R1's Cube path added global seeding absent from the official entry point, and the extra contact probe reproduced the displacement mechanism rather than exact historical R1 values.

### 6. Study design and the independent benchmark

| Study | What was tested and what happened |
|---|---|
| **Existing-data design and feasibility study** | The permitted metadata/exposure inventory left 82 provisional episodes. Power calculations did not support calling that an adequately powered five-point confirmation. No confirmation manifest or run was produced from that proposal. [Package][feasibility]. |
| **Expanded metadata-only capacity audit** | Broader permitted membership checks found 382 potential episodes under the recorded exclusions, including only nine in SAGE's test split. These were conditional capacity counts, not automatically released test data or performance results. [Audit][capacity]. |
| **Independent collector and common-driver pilots** | A separate 24-reference collection pilot tested the fixed block-near controller. Real E18/SAGE integration pilots, a separately labelled clipped-SAGE pilot and driver/preprocessing checks preceded the final comparison. Technical failures and their corrections remain in the progress log. [Record][independent-progress]. |
| **Full independent-data validation** | Collected 6,000 new references from 15,839 attempts without selecting by either compared planner. All 12,000 goal-specific reference-action replays passed. H75/H150 are temporal offsets, not shortest-path claims. [Data card][data-card]. |
| **Independent PushT comparison — latest completed study** | Evaluated the first 1,600 references: 57,600 runs. Continuation diffusion passed the registered superiority comparisons with greedy-300 and Gaussian, but trailed full SAGE and triggered the predeclared adverse-signal stop. The remaining stages were not run. [Full result][latest]. |

**Plans that did not become completed experiments.** These include the blocked stages named above, the proposed corrected **E20** SAGE reproduction, **D5** long-horizon confirmation, and a **PLDM** cross-backbone extension. The existing-data 82-episode fallback was not launched. The independent PushT study is not renamed E20, and unused stages or proposed controls are not counted as results. The detailed protocols and [archived research log][history] retain those plans and the intervening technical corrections.

## Baselines and evaluation details

**The ACID and PRISM-DP comparison arms are reconstructions.** Their numbers should not be presented as results from the authors' official implementations. E12 Stage A separately ran official PRISM artifacts as a sanity check; those were not matched diffusion-versus-PRISM results. The experiment reports document the implementation choices and remaining fidelity limitations.

**The latest SAGE comparison uses the released code and checkpoints under a common evaluation protocol.** It is separate from **E19 (the SAGE paper-reproduction study)**. E19 did not reproduce the complete released table within its tolerance, and its paper manifests overlapped the diffusion models' training episodes. The [E19 report][e19] records that outcome; the new benchmark does not resolve the historical reproduction discrepancy.

The latest comparison preserves SAGE's native handling of finite actions outside its declared action bounds. Those excursions are counted in the result archive; SAGE was not silently clipped or treated as failed for producing them. SAGE uses one released trained model with three evaluation-seed blocks, while the diffusion methods use their three fixed training checkpoints. The results do not establish how either method would behave across arbitrary retraining runs.

During the reproduction work, a PushT state setter was found to advance physics after assigning the requested state, sometimes carrying reset-dependent contact corrections into the starting pose. **R3 (the fresh-state initializer)** removes that hidden initialization step by constructing fresh physics before assigning the start. Missing block dynamics use documented defaults, not a claim of recovering the full historical simulator state. The independent study uses this [initialization interface][initializer]; earlier results retain their original setup.

## Finding the code

Most scripts live in `cluster/prometheus/`. The directory grew around individual experiments and still uses their original filenames so recorded commands and source hashes remain meaningful.

| What to inspect | Entry point |
|---|---|
| Continuation planning and action selection | [`gdp_cem_e18_closed_loop.py`][planner] |
| Independent reference-trajectory collection | [`independent_pusht_collect.py`][collector] |
| Checkpoint loading and model-specific interfaces | [`independent_pusht_runtime.py`][runtime] |
| Common six-method evaluation | [`independent_pusht_evaluate.py`][evaluator] |
| Statistics and result checks | [`analyze_independent_pusht.py`][analyzer] and [`verify_independent_pusht_analysis.py`][verifier] |

## Running and checking the experiments

This is a research repository, not a packaged library. To get the latest experiment code:

```bash
git clone --branch independent-pusht-benchmark https://github.com/ckontz01/diffusion-world-model-planning-thesis.git
cd diffusion-world-model-planning-thesis
```

The full evaluations use pinned Python environments and Apptainer containers on the CYENS Prometheus cluster. The scripts contain cluster-specific paths; cloning the repository alone does not supply the checkpoints, dependencies, or datasets. The [run wrapper][runner], [checkpoint manifest][pins], and [execution notes][recovery] record the setup used for the latest study. The older [workstation setup](REPRODUCIBILITY-SETUP.md) is retained as historical documentation.

Reading the results does not require cluster access. The compact outcome table and analysis files are committed in the [result archive][results]. Large reference and evaluation trajectories, model weights, latent caches, and container images are kept outside Git; their locations and hashes are recorded in the experiment documents. The latest results have a verified Windows recovery copy. Recovery of the older WSL bulk backups is a separate, unfinished operational task, not a missing analysis result.

## Research history

**20 September: LGP-RB1 completed and externally preserved.**
The exact frozen-model1/5/30 comparison completed387 allocations without
failures, retries or training. New GPU allocations totaled10,440seconds;
CPU analysis16seconds.768 new and384 unchanged reused episodes are reported
over32 exposed sources. Less refinement gave a more favorable diffusion-minus-
GMM point estimate, but both prespecified changes relative to30 remain uncertain;
budget1 absolute success is low. No favorable-budget confirmation or promotion.
The79,155,200-byte new archive passed2,798 member checks alongside the complete
1,733-member historical archive. [Final result](docs/local-goal-search-budget-20260919/FINAL-REPORT.md).

**19 September: LGP1 completed, authenticated and externally preserved.**
All204 scientific coordinates completed in207 attempts, including three charged
historical failures. GPU allocations totaled15,615seconds; the one CPU analysis
used16seconds. The original six-model freeze was reused without retraining.
Native success was14.583% GMM versus13.542% diffusion, with no demonstrated
diffusion advantage on32 exposed sources. Every source/horizon/seed is reported.
The1.734GB full historical/current archive passed1,733 member checks on THESIS_SSD.
A narrow Windows remote-path check was corrected only for final copying;
scientific source, artifacts and analysis remain unchanged. Retain continuation,
promote no model, and do not launch a follow-up. See the
[final report and accounting](docs/local-goal-proposals-20260918/FINAL-REPORT.md).

**18 September: SI1 saved-score information comparison completed.**
All 24 fixed CPU fits completed in one 102-second allocation. On 192 source-held-out
development references, treatment selected success was 14.442%, control 14.507%,
and continuation 15.668%. Treatment minus control was -0.065 percentage points;
slightly better probability error did not improve selection. Retain continuation;
promote no model. All outputs were sealed and backed up to the external SSD.
See the [complete report and all source effects](docs/candidate-value-score-information-20260918/FINAL-REPORT.md)
and [unaltered aggregate](docs/candidate-value-score-information-20260918/FINAL-AGGREGATE.json).

**18 September: saved-score information comparison prepared, not launched.**
The [SI1 protocol](docs/candidate-value-score-information-20260918/PROTOCOL.md)
compares the original 619 fields plus two zeros against the same fields plus
authenticated immediate/continuation costs. Four source-disjoint folds of the
192 B-training references give 24 fixed BCE fits. Preparation uses metadata and
synthetic tests only; training requires separate approval. Continuation remains
the baseline, with no model promotion or historical decision changes.

**18 September local (17 September UTC): CVL-BP1 completed and backed up.**
All450 coordinates succeeded (451 attempts including the preserved63s cancellation).
All18 models were frozen before evaluation; all32 development references are reported.
None of the six learned ensembles exceeds continuation on mean selected success.
Breadth improved BCE relative to its A/C versions, not demonstrably over continuation;
extra tail draws did not establish improvement. No model is promoted or follow-up launched.
Four verified SSD archives cover all450 outputs plus preservation evidence. Content-only
auxiliary packaging resolved the metadata-copy error without permission changes.
See the [final report](docs/candidate-value-breadth-precision-20260915/FINAL-REPORT.md)
and [unchanged aggregate](docs/candidate-value-breadth-precision-20260915/FINAL-AGGREGATE.json).

**17 September: CVL-BP1 cluster-only continuation authorized and launched.**
The user moved external-SSD backup to the end, removing laptop liveness as a
dispatch dependency while retaining cluster-side authentication and the full
pre-evaluation model freeze. All150 completed tasks are reused; only300
previously unsubmitted tasks remain, starting at breadth-142. No completed work
or evaluator training is restarted. Original source, workers, science, budgets
and failure charges remain unchanged. Final external backup is still pending.
See the [operational amendment](docs/candidate-value-breadth-precision-20260915/CLUSTER-CONTINUATION-20260917.md)
and [cluster launch](docs/candidate-value-breadth-precision-20260915/CLUSTER-CONTINUATION-LAUNCH-20260917.md).

**17 September (local): CVL-BP1 resumed after the approved SSD-check repair.**
The second recovery reuses all 148 completed coordinates and submits only the
302 unsubmitted tasks, starting with job 301630 (`breadth-140`, source 463, H75).
The native Windows volume helper removes the failing WSL-to-Windows probe path;
fresh identity/headroom checks and fail-closed dispatch remain required. The
original scientific snapshot, budgets and all prior charges are unchanged.
The existing monitor is active again. The study is running, not complete, and
partial scientific results remain sealed. See the
[second recovery launch](docs/candidate-value-breadth-precision-20260915/RECOVERY2-LAUNCH-20260917.md).

**16 September: CVL-BP1 recovery paused after a WSL volume-probe failure.**
All 46 recovery allocations completed successfully, bringing the total to 148
completed coordinates. The backup companion's WSL-to-Windows volume-label query
failed; the recovery controller detected that stop and submitted no further job.
No new allocation failed or required cancellation. Total charged GPU allocation
is 8h53m24s, including the original cancelled attempt. The 148 completed outputs
and stop evidence have verified external-SSD backups. Monitoring is paused;
302 fixed coordinates remain, and partial scientific results remain unopened.
See the [recovery stop record](docs/candidate-value-breadth-precision-20260915/RECOVERY-STOP-20260916.md).
No second repair or resumption has been performed.

**16 September: CVL-BP1 resumed under one scoped infrastructure recovery.**
The user approved repairing backup liveness, reusing all102 completed outputs,
and one replacement for cancelled301578. At launch, replacement301579 ran the same
`breadth-94` coordinate from the unchanged scientific snapshot. The cancelled
63 seconds remain charged; the fixed remainder and aggregate caps are unchanged.
The separately frozen recovery controller checks fresh external-SSD liveness
before every submission. Monitoring was re-enabled at launch; the subsequent
stop is recorded above. No partial performance was inspected. See the
[recovery launch](docs/candidate-value-breadth-precision-20260915/RECOVERY-LAUNCH-20260916.md)
and its linked source/approval hashes, tests, accounting and preservation record.

**16 September: CVL-BP1 stopped on a backup-companion connection failure.**
An SSH timeout exited the external backup companion. The monitor stopped the
serial dispatcher under the approved infrastructure-failure rule, preserving
102 completed allocations and requesting cancellation of job301578. There was
no observed scientific failure and no partial outcome inspection. Terminal
accounting is now reconciled at6h3m12s GPU allocation; the stopped run has a
verified external-SSD archive. At that stop, monitoring was paused pending scoped recovery.
See the
[technical stop record](docs/candidate-value-breadth-precision-20260915/TECHNICAL-STOP-20260916.md).
No retry or relaunch was performed before the separately authorized recovery above.

**16 September: approved CVL-BP1 launched after a narrow host-side repair.**
The [launch record](docs/candidate-value-breadth-precision-20260915/LAUNCH-20260916.md)
binds the unchanged scientific protocol and resource envelope to the repaired
source. The first job is Slurm301452; the fixed serial dispatcher and external
THESIS_SSD backup companion are running. The first16 included jobs must pass
technical resource checks before the remaining stages proceed. No partial
scientific results are reported, and the study is not yet complete. Historical
decisions, continuation baseline and protected/reserved data boundaries remain
unchanged.

**15 September: source breadth versus continuation-label precision prepared; not launched.**
The [CVL-BP1 executable proposal](docs/candidate-value-breadth-precision-20260915/PROTOCOL.md)
compares original96×2 draws,192×2 draws and original96×4 draws with fixed
original-capacity BCE/relative ensembles and matched optimizer updates.
Identifier-only allocation assigns96 new training and32 new model-held-out
development sources, excluding all192 earlier allocated sources. The proposed
[resource envelope](docs/candidate-value-breadth-precision-20260915/RESOURCE-PLAN.md)
covers at most32,768 new outcomes before unavailable-anchor reductions; no new
labels, training, physics, GPU jobs or closed loop were authorized or executed
at that preparation stage. The later bounded launch approval is recorded above.
Continuation and the recorded `original_relative` nomination remain unchanged.

**15 September: fixed CPU-only objective × capacity comparison completed.**
The [60-fit study](docs/cvl1-objective-capacity-20260915-v1/REPORT.md) compared
original/compact evaluators under absolute BCE and baseline-relative squared
error, using only saved CVL-1 data. The training-only original-relative nominee
was +0.152 percentage points versus continuation in source-held-out cross-fitting,
but −1.497 points on exposed development validation; all four ensembles were
negative there. Objective effects varied across folds, and compact capacity did
not improve pooled cross-fitting. Continuation remains the working baseline;
the frozen nomination is preserved, not replaced using validation. One 201-second
4-CPU allocation completed all 60 fits, with external-SSD backup. CVL-1's
`stop_no_ranking_promise`, earlier diagnosis, checkpoints and historical results
remain unchanged. No new labels, GPU or closed-loop evaluation was used.

**15 September: one CPU-only CVL-1 learning diagnosis completed.** The
[saved-feature diagnosis](docs/cvl1-learning-diagnosis-20260915-v1/REPORT.md)
preserves `stop_no_ranking_promise`. Ensemble selection was +12.72 points versus
continuation in-sample but −3.06 points on validation; all three individual MLPs
had negative validation effects. Cross-draw selection averaged −0.20 points on
validation, with extensive binary ties. The report separates fitting/generalization,
paired outcome noise and predicted-versus-realized departure advantages. One
20-second CPU allocation used frozen evaluator forwards only; no labels, models,
world-model/simulator calls or closed-loop evaluations were added. A baseline-relative
ranking objective is recommended only as a separately approved future hypothesis.

**15 September: CVL-1 completed with `stop_no_ranking_promise`.** All 192
training and 64 ranking-validation collection jobs completed; training support
passed and all five fixed models were fitted. On the 32 validation references,
the fixed MLP ensemble selected-success effect versus continuation was **−3.06
percentage points** (descriptive reference-bootstrap 95% interval −7.29 to +0.85).
Concordance was 0.561 on informative comparisons, but the required positive
selection effect failed. No conditional closed-loop jobs ran. The
[final development report](docs/candidate-value-learning-20260914/RESULT-20260915.md)
records controls, all reference effects, verified SSD backups and **15h19m47s GPU
allocation**, including the prior failed preflight. This is a scientific stop,
not a technical retry opportunity or a general rejection of learned value scoring.
Historical results and frozen models remain unchanged.

**15 September: CVL-1 controller-only continuation authorized.** The user approved
the narrow temporary-file counter repair and continuation from training index 81.
The [continuation contract](docs/candidate-value-learning-20260914/CONTINUATION-20260915.md)
retains all completed outputs and 17,151 GPU seconds, uses the original immutable
workers and scientific protocol, and requires authenticated one-use resumption.
The earlier stop and backup record below remain historical; no scientific result
is amended and no completed collection task may be resubmitted.
The [verified launch receipt](docs/candidate-value-learning-20260914/CONTINUATION-LAUNCH-20260915.md)
records 62 passing regression tests and first resumed job **301257**, observed
running at index 81. Backup readiness is restored on the external SSD.

**15 September: CVL-1 collection paused by a dispatcher file-inventory race.**
The [technical stop record](docs/candidate-value-learning-20260914/DISPATCH-STOP-20260915.md)
documents 81 completed collection jobs and both preflights, 83 verified adjacent
seals, and a member-verified external stopped-run backup. Job 301256 completed
successfully after the dispatcher stopped on a disappearing temporary file.
Reconciled cost is 4h45m51s including the earlier failed allocation. No partial
scientific outcomes were interpreted, no models fitted, and no replacement
jobs launched. The monitor is paused; frozen scientific settings remain unchanged.

**15 September: CVL-1 technical collection tranche passed.** All eight jobs for
the four fixed references at both horizons completed with verified seals and
technical identities. The [gate record](docs/candidate-value-learning-20260914/TECHNICAL-PILOT-20260915.md)
reports maximum allocation 293s, sampled RSS 1.60GiB and the unchanged pilot-based
payload projection 0.714GB. Remaining training collection is proceeding under the
frozen gates. Success outcomes were not inspected; this is not an efficacy result.

**14 September: CVL-1 technical repair verified and restart authorized.**
The host/container mismatch was exactly three Python symlink aliases, with all
21,643 common runtime files identical. Stable link-aware authentication and
exclusive content-only evidence copying are verified; 55 local/exported tests pass.
The [restart receipt](docs/candidate-value-learning-20260914/RESTART-20260914.md)
records the new immutable source/capsule, both passed real preflights (301161,
301162), and the prior failed 45 seconds carried into the unchanged aggregate
budget. First collection job 301163 (reference 1444, H75) is running; the technical
pilot has not yet passed. Scientific gates and settings remain unchanged;
no new efficacy result is claimed.

**14 September: CVL-1 conditionally approved; real preflight stopped.**
The [launch receipt](docs/candidate-value-learning-20260914/LAUNCH-20260914.md)
records the separately frozen saved-physical-success and candidate-delivery
corrections, 52 passing local/exported tests, unchanged scientific protocol,
exact source/capsule/approval hashes and verified external-SSD readiness.
Registered preflight 0, Slurm 301159, failed after 45 allocated seconds on a
container-side runtime-tree authentication mismatch, before model or record access.
The [technical stop report](docs/candidate-value-learning-20260914/STOP-20260914.md)
preserves the separate terminal metadata-copy failure and verified external evidence
copy. No second job, labels, model fit, ranking result or closed-loop gain exists;
the frozen run was not patched or retried.

**14 September: full-budget candidate-value learning prepared, not launched.**
The [CVL-1 proposal](docs/candidate-value-learning-20260914/PROTOCOL.md) allocates
96/32/32 source-disjoint training/ranking-validation/closed-loop development
references within exposed 0–1599, excluding the accepted single-anchor 32. It
proposes up to 16,384 native-success candidate-tail labels, compact value and
logistic evaluators, and a conditional 512-episode closed-loop comparison with
continuation and immediate controls. Estimated collection 19–29 GPU-hours, proposed
aggregate cap 50 GPU-hours. The completion revision implements collection,
training/serialization, within-bank validation, conditional closed-loop execution,
source/runtime authentication, serial dispatch and sealed external-SSD backup.
The three neural seeds form one fixed ensemble; a context-only diagnostic is not
an additional closed-loop arm. Synthetic end-to-end tests only; exact deployment
capsule approval and registered runtime preflights precede any launch.
No new collection, research training,
evaluation or confirmation access occurred; the historical result is unchanged.
The [completion receipt](docs/candidate-value-learning-20260914/PREPARATION-RECEIPT.md)
records 47 passing synthetic/regression tests, the deployed immutable source and
selected-input/runtime capsule, verified external-SSD copies, and immutable review
links. The source is published; research launch approval remains absent.

**14 September: single-anchor ranking experiment completed.** On the same 32
exposed development references, both arms used identical anchor proposal workloads
and the unchanged continuation tail. Immediate selection improved first-chunk
joint margin on 29/32 references, but full-budget native success was 12/128 versus
16/128 for continuation selection: −3.125 points, exploratory reference-cluster
95% interval [−10.9375, +4.6875]. All 64 processes and the frozen verifier passed;
two repeats check repeatability, not independent sample size. GPU allocations
totaled 49.38 minutes. The [full result](docs/single-anchor-ranking-20260914/RESULT-20260914.md)
retains all reference effects, adverse cases, accounting and verified external
backup. This is outcome-informed development, not a new confirmation or SAGE
comparison; no next method was launched and historical decisions remain unchanged.

**14 September: outcome-informed bottleneck diagnostics.** The completed450-
shard study now has an authenticated, member-verified external-SSD archive.
The [complete trajectory reduction](docs/bottleneck/TRAJECTORY-RESULT-20260914.md)
rechecked all57600 runs without changing the historical endpoint or stopping
decision. Most terminal failures combine position and angle misses; those
categories are symptoms, not identified causes. The separately specified four-
reference same-bank/intermediate-context engineering pilot completed with
mixed effects and one local successful-bank selection counterexample, not a
resolved SAGE gap. Its [result](docs/bottleneck/PILOT-RESULT-20260914.md) records
the preserved checker failure, separate semantic supplement and measured costs.
The approved additional28 extension has completed all56 new jobs and combined
verification, with the original pilot reused unchanged and all64 bundles backed
up on the externalSSD. Its [combined32/additional28 report](docs/bottleneck/EXTENSION-RESULT-20260914.md)
finds a repeatable first-chunk margin-ranking signal, no added successes in new28,
and mixed context-replacement effects. Final RAM accounting is complete (maximum
Slurm batch MaxRSS1686004K); the completed report was delivered to the selected
reasoning chat for review. No next experiment was launched.
See [status](docs/bottleneck/STATUS.md) and the
[frozen extension contract](docs/bottleneck/EXTENSION-EXECUTION-20260914.md). No new model,
confirmation, architecture redesign or unused-reference evaluation is authorized
by these diagnostics.

The project started with a different idea: use diffusion denoising error to judge whether imagined transitions were feasible. Those scores did not give reliable planning gains, which led to action proposal generation instead. Later studies tested action bounds, goal conditioning, continuation scoring, and simulator initialization. Several approaches failed their planned checks; those reports remain part of the repository.

The [archived research log][history] preserves the detailed chronology and earlier instructions. It is a historical snapshot, not the current project status. The latest result is the completed PushT study above: positive gains over the two main internal controls, lower solver time than SAGE, and lower success than SAGE on this evaluation population.

[code]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/tree/independent-pusht-benchmark
[latest]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/INDEPENDENT-PUSHT-RESULT-2026-09-07.md
[protocol]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/INDEPENDENT-PUSHT-PROTOCOL.md
[data-card]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/INDEPENDENT-PUSHT-DATA-CARD.md
[results]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/tree/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/independent-pusht-evidence/look-0
[e11]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E11-PURE-VELOCITY-UNTOUCHED-D3-RESULT-2026-08-18.md
[e13]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E13-VELOCITY-VS-PRISM-DP-UNTOUCHED-D4-RESULT-2026-08-22.md
[e18]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E18-EXPLORATORY-CONTINUATION-PLANNER-RESULT-2026-08-28.md
[e18-protocol]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E18-EXPLORATORY-CONTINUATION-PLANNER-PROTOCOL-2026-08-27.md
[e19]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-NATIVE-REPRODUCTION-RESULT-2026-08-29.md
[initializer]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/PUSHT-FRESH-INITIALIZATION-INTERFACE.md
[planner]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/gdp_cem_e18_closed_loop.py
[collector]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/independent_pusht_collect.py
[runtime]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/independent_pusht_runtime.py
[evaluator]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/independent_pusht_evaluate.py
[analyzer]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/analyze_independent_pusht.py
[verifier]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/verify_independent_pusht_analysis.py
[runner]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/run_independent_pusht.sh
[pins]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/INDEPENDENT-PINNED-INPUTS.json
[recovery]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/INDEPENDENT-PUSHT-RECOVERY.md
[history]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/README.md#historical-development
[baseline-pilot]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/BASELINE-PILOT-STATUS-2026-08-08.md
[early-amendments]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/PROTOCOL-IMPLEMENTATION-AMENDMENTS-2026-08-08.md
[p3-lock]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/P3-PRE-EXECUTION-LOCK-2026-08-09.md
[early-history]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/README.md#historical-development
[m2v2]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/M2V2-P2-FEASIBILITY-RESULT-2026-08-12.md
[d1]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-D1-RESULT-2026-08-15.md
[score-rescue]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-V2-DIFFUSION-RESCUE-PROTOCOL-2026-08-15.md
[v2-pilot-protocol]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-V2-RESIDUAL-DIFFUSION-PILOT-PROTOCOL-2026-08-16.md
[v2-result]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-V2-RESIDUAL-DIFFUSION-PILOT-RESULT-2026-08-16.md
[v3-result]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-V3-MULTISEED-D2-STAGE-A-RESULT-2026-08-16.md
[e3]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E3-EXPLORATORY-D2-CLOSED-LOOP-RESULT-2026-08-16.md
[e4]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E4-DIFFUSION-INVERSE-DEVELOPMENT-PROTOCOL-2026-08-16.md
[e5]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E5-COUNTERFACTUAL-DIFFUSION-DEVELOPMENT-2026-08-16.md
[e6]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E6-QUANTILE-CONSTRAINED-CEM-PROTOCOL-2026-08-16.md
[e6d]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E6D-ALL-ITERATIONS-MATCHED-CONTROLS-RESULT-2026-08-17.md
[e7-draft]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E7-GOAL-CONDITIONED-DIFFUSION-PROPOSAL-DRAFT-2026-08-17.md
[e7p]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E7P-PROPOSAL-SELECTION-RESULT-2026-08-17.md
[e8a]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E8A-GAUSSIAN-ANCHORED-DIFFUSION-REFINEMENT-RESULT-2026-08-17.md
[e8d]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E8D-GADR-D2-RESULT-2026-08-17.md
[e9]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E9-ABANDONED-DUPLICATE-2026-08-17.md
[e10v]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E10V-PURE-VELOCITY-DIFFUSION-P1-RESULT-2026-08-17.md
[e10m]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E10M-MULTISEED-PURE-VELOCITY-P1-RESULT-2026-08-17.md
[e12]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E12-STAGE-B-VALIDITY-RESULT-2026-08-22.md
[e14]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-GATE-B-RESULT-2026-08-23.md
[post-e14]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/POST-E14-BOUNDARY-DIAGNOSTIC-RESULT-2026-08-25.md
[e15-data]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/E15-BOUNDARY-AWARE-DATA-PREFLIGHT-RESULT-2026-08-25.md
[e15]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E15-BOUNDARY-AWARE-LONG-HORIZON-GATE-B-RESULT-2026-08-25.md
[e16]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E16-CONTINUATION-DIAGNOSTIC-RESULT-2026-08-27.md
[e17]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E17-TRANSITION-STATE-ADAPTER-PREFLIGHT-RESULT-2026-08-27.md
[e19-diagnostic]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-DISCREPANCY-DIAGNOSTIC-RESULT-2026-08-30.md
[e19-d2]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E19-D2-METHOD-AWARE-DISCREPANCY-REANALYSIS-RESULT-2026-08-30.md
[e19-l1]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/E19-L1-EXPOSED-ARTIFACT-LOCALIZATION-RESULT-2026-09-05.md
[e19-r1]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/E19-R1-RESET-FIXED-STIMULUS-RESULT-2026-09-05.md
[e19-r2]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/E19-R2-LOCALIZATION-RESULT-2026-09-05.md
[e19-r3]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/E19-R3-INITIALIZATION-RESULT-2026-09-05.md
[fresh-integration]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/E18-FRESH-DRIVER-INTEGRATION-RESULT-2026-09-05.md
[feasibility]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/E18-DESIGN-FEASIBILITY-PACKAGE-2026-09-05.md
[capacity]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/E18-EXPANDED-CAPACITY-AUDIT-RESULT-2026-09-06.md
[independent-progress]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/INDEPENDENT-PUSHT-PROGRESS.md
