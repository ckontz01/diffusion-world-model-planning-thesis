# Goal-Conditioned Velocity Diffusion for Le-WM Planning

Research repository for Christoforos Kontzias's University of Cyprus thesis on feasibility-aware planning with latent world models.

The project began as a comparison of post-hoc feasibility scores for hierarchical subgoals. It eventually produced a different and stronger method: a pure goal-conditioned velocity-diffusion model that proposes complete action sequences for a frozen Le-WM, followed by one model-cost evaluation. The change of method is central to the scientific record. The successful E11 method is **not** the original auxiliary diffusion-loss scorer.

## Current status

The new independent PushT benchmark is implemented and launched on branch
`independent-pusht-benchmark` (frozen source `63f0440`). Collector, common-runtime
SAGE integration, accepted E18 driver parity, and 22 analysis/orchestration
regressions passed. The prospective six-arm design has cumulative looks at
1,600/3,200/6,000 independent reference episodes with fixed sequential rules.
This is a new weak-policy reachable-goal distribution, not original SAGE paper
reproduction. Collection job300326 completed and all6,000 reference files are backed up locally.
A launcher-only array-index correction (`4a608e5`) passed23 tests and a real
container handoff check. Corrected array300339, analysis300340 and controller300341
use the same locked references and unchanged scientific design. No final
comparative outcome is available yet. See
[execution/recovery](cluster/prometheus/INDEPENDENT-PUSHT-RECOVERY.md),
[protocol](cluster/prometheus/INDEPENDENT-PUSHT-PROTOCOL.md), and
[progress](cluster/prometheus/INDEPENDENT-PUSHT-PROGRESS.md).


The [PushT design/feasibility package](cluster/prometheus/E18-DESIGN-FEASIBILITY-PACKAGE-2026-09-05.md)
is complete as preparatory analysis, not confirmation authorization. The allowed
metadata/exposure ledger leaves **82** H75/H150-compatible episodes;400/600/800
are currently infeasible. Exact LeWM training membership is unknown and none of
the82 is in SAGE's test split. At a true+5-point effect against each primary
control, historical-variance planning gives38%/28% marginal power and19% joint
power; doubling variance lowers joint power to9%. The feasible all-five-arm
option is2,460 runs, with1.70 central and4.93 conservative allocated A6000-hours.
It is not adequately powered five-point confirmation. Full-budget lifecycle
regressions and a non-efficacy exposed-input timing probe pass; the initializer,
driver, models and historical decisions are unchanged. No confirmation manifest
or execution is authorized. See the [preparatory history](cluster/prometheus/E18-DESIGN-FEASIBILITY-CHANGELOG-2026-09-05.md).

The bounded fresh-interface PushT integration now passes: the unchanged five
E18 arms completed50 exposed-record initializations,128 actual planning calls
and1,363 delivered actions with verified replanning, termination and new-episode
lifecycle. Missing evaluator non-action scalers are computationally irrelevant;
exact checkpoint normalization and action decoding are pinned. R3, model bytes
and historical outcomes remain unchanged. This is an engineering result, not
efficacy evidence. See the [integration result](cluster/prometheus/E18-FRESH-DRIVER-INTEGRATION-RESULT-2026-09-05.md)
and the [initial confirmation draft, superseded for sample-size planning by the package above](cluster/prometheus/E18-FRESH-CONFIRMATION-PROTOCOL-DRAFT-2026-09-05.md).
No confirmation record was accessed or protocol falsely labelled frozen.

As of 5 September 2026, two frozen untouched-holdout studies support complementary conclusions. E14 and its single preregistered E15 redesign stopped before closed-loop long-horizon comparison; E16 and E17 then isolated candidate-ranking headroom and an imperfect transition-state interface. The separately frozen E18 study produced positive, development-only closed-loop evidence for the resulting continuation planner. E19 subsequently completed a pinned native reproduction of official SAGE and stopped because the unchanged release's two-point fidelity rule failed. The new E19-L1 engineering follow-up localizes the exposed diagnostic discrepancies without changing any historical decision or running new episodes.

E11 remains the cleanest diffusion-specific result. On PushT, Reacher, and Cube, goal-conditioned velocity diffusion achieved 93.39% equal-task success, compared with 90.64% for a matched learned Gaussian selector and 83.31% for a published-equation reconstruction of ACID. Diffusion exceeded Gaussian by **+2.75 percentage points**, with a 95% paired start-cluster interval of **[+1.64, +3.89]**. Its **+10.08-point** comparison with reconstructed ACID, interval **[+8.31, +11.89]**, combines the learned one-shot-proposal advantage with the narrower diffusion-specific effect.

E13 resolved the direct comparison with a disclosed PRISM-DP reconstruction on a new untouched D4 holdout. At the primary `K=300` budget, velocity diffusion achieved 93.53% and PRISM-DP 92.97%: **+0.56 points**, 95% interval **[-0.47, +1.58]**. That does not establish superiority. It does pass the frozen compute-efficient-alternative gate: the one-sided lower bound remained inside the -3-point margin, and velocity diffusion was faster on every task while using fewer learned parameters, no second image encoder, and less peak CUDA memory.

E13's velocity-versus-Gaussian point difference was +2.56 points with interval [+1.39, +3.72], but the frozen mechanism-replication gate failed because the Gaussian Reacher proposals exceeded the registered 25% boundary/clipping limit for two seeds. This result may be reported, but not as an unqualified fresh mechanistic confirmation. Cube was saturated again, and the PRISM-DP task effects were mixed: velocity diffusion was -1.67 points on PushT, +3.33 on Reacher, and tied on Cube.

E14 tested whether the method could extend to variable-duration, long-horizon planning under SAGE's task and schedule interface. VAD diffusion beat its matched Gaussian on both registered offline metrics for all three seeds, on both PushT and Cube at every local duration, and beat shuffled-goal and unconditional controls. It nevertheless violated the frozen 25% proposal-boundary ceiling on Cube for all three seeds. CVD failed that integrity condition and the matched Gaussian terminal-cost comparison. Therefore neither endpoint entered Gate C: no P2 long-horizon closed-loop result, SAGE efficacy comparison, or D5 confirmation was produced. The [audited E14 Gate-B result](cluster/prometheus/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-GATE-B-RESULT-2026-08-23.md) is a promising mechanism result plus an honest validity stop, not a new paper claim.

The [post-E14 boundary diagnosis](cluster/prometheus/POST-E14-BOUNDARY-DIAGNOSTIC-RESULT-2026-08-25.md) reproduced every E14 boundary row and compared raw proposals with the exact deployed float32 action transforms. Cube's mean legal overshoot was about 2.49%, while the worst query banks reached the same 27--36% values that stopped E14; selected and full-bank means were nearly identical. Cube experts were legal but genuinely saturated at several coordinates. The correct target for one separately frozen E15 is therefore overshoot and hard clipping, not all boundary use. E14 remains failed and D5 remains sealed.

E15 applied one common smooth, legality-preserving action representation to boundary-aware VAD, a matched diagonal Gaussian, a direct eight-mode trajectory GMM, and the VAD conditioning nulls. All 22 banks passed the new expert-relative integrity rules with zero legal OOB values, zero exact boundary values, and 300 unique candidates; all six GMM task/seed banks passed their structural checks. VAD also beat Gaussian on both equal-task primary metrics for every seed. The mechanism gate still failed: Cube won both metrics at every duration, but PushT's selected true-local cost was worse than Gaussian at every duration, and true VAD did not beat unconditional VAD on the full frozen null rule. The final decision was `stop_before_gate_c_frozen_gate_b_failed`; no Gate C, SAGE efficacy comparison, or D5 result was produced. See the [audited E15 Gate-B result](cluster/prometheus/ACID-ALTERNATIVE-E15-BOUNDARY-AWARE-LONG-HORIZON-GATE-B-RESULT-2026-08-25.md).

E16 then tested the narrower hypothesis that E15's one-chunk far endpoint was a poor selector even when its VAD bank contained useful first branches. Exact replay of 90,000 seed-7201 validation banks per task found real oracle reranking headroom: on genuine far-goal rows, reranking only the far-ranked top 30 reduced mean next-local cost from 32.99 to 14.55 on PushT and from 68.06 to 34.94 on Cube. A fixed half-standard/half-zero-guidance bank was worse on both tasks, so low guidance was not promoted. The required latent-only state adapter passed PushT but failed all three frozen Cube thresholds (RMSE 0.805, maximum coordinate RMSE 1.698, median coordinate R-squared 0.401). E16 Stages B and C therefore remained blocked. The [audited E16 diagnostic result](cluster/prometheus/ACID-ALTERNATIVE-E16-CONTINUATION-DIAGNOSTIC-RESULT-2026-08-27.md) establishes candidate-ranking headroom, not closed-loop continuation efficacy.

E17 was the separately frozen follow-up interface preflight. It supplied current state, current latent, the bounded first action chunk, and Le-WM's terminal latent to a fixed residual state predictor. PushT passed comfortably. Cube improved dramatically over E16 and passed its overall, copy-current, median-R-squared, and all duration gates, but its worst-coordinate RMSE was 1.163 against the frozen 0.850 ceiling. Because both tasks were required, E17 stopped without a planner experiment, SAGE comparison, full-horizon diffusion, or protected-holdout use. See the [protocol](cluster/prometheus/ACID-ALTERNATIVE-E17-TRANSITION-STATE-ADAPTER-PREFLIGHT-PROTOCOL-2026-08-27.md), [launch record](cluster/prometheus/ACID-ALTERNATIVE-E17-TRANSITION-STATE-ADAPTER-PREFLIGHT-LAUNCH-2026-08-27.md), and [audited result](cluster/prometheus/ACID-ALTERNATIVE-E17-TRANSITION-STATE-ADAPTER-PREFLIGHT-RESULT-2026-08-27.md).

E18 is a separately frozen, outcome-informed exploratory study rather than a rescue of E17. It kept the failed E17 checkpoints unchanged and tested the planner-level question that E17 never reached: whether scoring 64 first chunks through eight action-conditioned continuations each can exploit E16's measured candidate-ranking headroom. On 12 fresh paired P2 starts per task, two horizons, and three seeds, VAD continuation reached 72.92% equal-task/equal-horizon success versus 66.67% for greedy VAD-300, 60.42% for compute-matched greedy VAD-576, 65.97% for diagonal-Gaussian continuation, and 54.86% for direct-GMM continuation. All four frozen point/task rules passed. Paired start-cluster intervals excluded zero against VAD-576 and GMM, but not against VAD-300 or Gaussian. PushT supplied the useful long-horizon signal; Cube was largely saturated. This authorizes drafting a separate confirmation protocol, not consuming D5 or treating E18 as confirmation. See the [frozen protocol](cluster/prometheus/ACID-ALTERNATIVE-E18-EXPLORATORY-CONTINUATION-PLANNER-PROTOCOL-2026-08-27.md), [launch record](cluster/prometheus/ACID-ALTERNATIVE-E18-EXPLORATORY-CONTINUATION-PLANNER-LAUNCH-2026-08-27.md), and [audited result](cluster/prometheus/ACID-ALTERNATIVE-E18-EXPLORATORY-CONTINUATION-PLANNER-RESULT-2026-08-28.md).

E19 pinned official SAGE commit `8219029fd52e89157e05aebb998ab26f0ef46966`, its exact released checkpoint snapshot, and the complete 180-cell PushT/Cube paper grid. All 180 cells and 9,000 episodes completed and passed the frozen identity audit before results were opened. The unchanged official summarizer nevertheless rejected the reproduction: 29 of 60 means were within its ±2-point tolerance, and the maximum absolute gap was 25.97 points. Generator Prior Top reproduced all 12 means, while the largest systematic shortfalls were concentrated in LeWM + Generator, especially Cube. An identifier-only audit also found that 270 PushT and 84 Cube paper-manifest episodes overlap E18 training. Therefore the released paper values are not treated as a validated thesis baseline, and no matched E18-versus-SAGE comparison on those manifests was drafted or launched. See the [frozen protocol](cluster/prometheus/ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-REPRODUCTION-AND-OVERLAP-PROTOCOL-2026-08-28.md) and [audited result](cluster/prometheus/ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-NATIVE-REPRODUCTION-RESULT-2026-08-29.md).

A separately frozen, outcome-informed E19 discrepancy diagnostic then ran two exact repeats of five prespecified sentinel cells plus a fixed-bank runtime/transport comparison. All ten sentinels and the comparison completed, but the sealed analyzer deliberately failed its frozen `internal_valid` gate. Under the preregistered failure barrier, its JSON/TSV outputs were checksum-validated but not opened or interpreted. The diagnostic is therefore invalid, identifies no mismatch class, authorizes no E20, and does not amend E19. See the [transparent diagnostic stop](cluster/prometheus/ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-DISCREPANCY-DIAGNOSTIC-RESULT-2026-08-30.md).

Static source inspection then established that the failed analyzer's history-latent gate was impossible for the prespecified generator-free `base_cem` sentinel independently of outcomes. A separately named E19-D2 reanalysis changed only that event-validity expectation, reused the checksum-verified raw artifacts without rerunning episodes, and preserved the first diagnostic as invalid. E19-D2 was internally valid but found two objective mismatch classes: no sentinel had exact fresh-process trace/bank repeatability, and PushT JPEG/Lance transport changed elite membership in 31/50 and 39/50 environments for the two tested banks. Strict official-runtime loading matched the compatibility load exactly, and the Cube cache audit passed. Because the frozen rule requires exactly one unique mismatch, E20 remains unauthorized; an evidence packet was prepared for review but not sent. See the [E19-D2 result](cluster/prometheus/ACID-ALTERNATIVE-E19-D2-METHOD-AWARE-DISCREPANCY-REANALYSIS-RESULT-2026-08-30.md).

E19-L1 then checked the already exposed artifacts field by field and replayed only fixed candidate banks. All five first planning calls agree in their recorded computational fields; initial bank differences are additional environment `info` fields, not different first candidates/costs. All eight available CEM banks reproduce historical costs and fitted distributions exactly, and no actual `repr` record or first-call elite-boundary tie was found. Later differences begin after the first action block, with one changed outcome in 250 existing paired episode comparisons. JPEG/lossless transport replaces an average of 0.92 and 1.48 of 30 elites in the two tested banks, but the authors' actual representation and any effect on success remain unknown. These are diagnostic discrepancies, not two proven causes of the paper-table gap. See the [L1 result](cluster/prometheus/E19-L1-EXPOSED-ARTIFACT-LOCALIZATION-RESULT-2026-09-05.md) and [unsent supplemental packet](cluster/prometheus/e19-l1-evidence/README.md).

The [shared-infrastructure review](cluster/prometheus/E18-SHARED-INFRASTRUCTURE-REVIEW-2026-09-05.md) also corrects the earlier interpretation of E18: PushT H150 was 44.44% versus 25.00% for both greedy VAD-300 and Gaussian continuation. Recorded timing ratios were approximately 2.00x and 1.85x, with the important qualification that these are batch-amortized seconds per context-stage. The reset/state-restoration interface remains an engineering gate before confirmation; E18 is not assumed immune to a problem discovered in SAGE. A [non-executable confirmation outline](cluster/prometheus/E18-CONFIRMATION-OUTLINE-2026-09-05.md) is prepared, but no holdout or new comparison is authorized.

The subsequently authorized [E19-R1 reset/fixed-stimulus check](cluster/prometheus/E19-R1-RESET-FIXED-STIMULUS-RESULT-2026-09-05.md) performed short engineering executions, not new planning or benchmark evaluation. Twenty valid traces delivered 300 post-restoration actions. Paired actions matched in all cases, but one PushT case in each stack already had differing block poses after restoration; initial dataset-overlaid states hid those differences. Cube qpos/qvel/targets matched while other integration fields differed; three pairs converged after one action and one E18 pair retained small numerical drift. Confirmation remains on hold pending resolution of the restoration contract. The diffusion planner and all historical decisions are unchanged.

The [R2 targeted localization](cluster/prometheus/E19-R2-LOCALIZATION-RESULT-2026-09-05.md) found exact requested PushT fields before the setter step, but different post-step block poses under explicit reset seeds 32 and 33. Repeatability under one seed therefore does not establish correct restoration. Retained contact/integration state is consumed during the setter's physics advancement. R2 also discloses R1's additional SAGE Cube global seeding and classifies the preserved E18 warning as signed-velocity bounds metadata. No production correction was made; arm/batch equivalence and confirmation remain gated on an approved restoration contract.

The subsequently authorized [R3 fresh-state repair](cluster/prometheus/E19-R3-INITIALIZATION-RESULT-2026-09-05.md) implements one opt-in instantaneous PushT initializer, leaving the native legacy path and every historical decision unchanged. On three exposed starts in both runtimes, 48 history/repeat scenarios passed exact-state, zero-hidden-step, observation, idempotence and fixed-action checks. All ten real checkpoint-backed arms then passed initialized-state/input and singleton/batch-slot equivalence at native batch sizes3 and50. Missing dynamics use documented canonical defaults, not claimed historical recovery. The separate velocity-space metadata correction changes no values. E18 non-action scaler coefficients were not refitted: that boundary is raw-input equality, not complete historical-preprocessing validation. No planner invocation, new scientific comparison or holdout access occurred; the scoped engineering gate is now passed.

The resulting paper claim is scoped: pure velocity diffusion is a strong learned action proposer and a compute-efficient alternative to the tested disclosed PRISM-DP reconstruction. The repository does not establish universal superiority, an official ACID reproduction, a comparison with official PRISM, or a validated efficacy comparison against official SAGE.

## E13 matched PRISM-DP results first, by task

E13 used 400 untouched D4 starts per task, three fixed seeds, five arms, and 18,000 closed-loop episodes. All 360 blinded evaluation shards completed before metric analysis was unlocked.

| Arm | PushT | Reacher | Cube | Equal-task |
|---|---:|---:|---:|---:|
| Latent Gaussian, `K=300` | 93.50% | 79.58% | 99.83% | 90.97% |
| PRISM-DP reconstruction, `K=16` | **97.25%** | 75.67% | 100.00% | 90.97% |
| PRISM-DP reconstruction, `K=300` | **97.25%** | 81.67% | 100.00% | 92.97% |
| Velocity diffusion, `K=16` | 95.50% | **85.08%** | 100.00% | **93.53%** |
| **Velocity diffusion, `K=300`** | 95.58% | 85.00% | 100.00% | **93.53%** |

At `K=300`, velocity diffusion's primary one-sided 95% lower bound against PRISM-DP was -0.31 points, above the frozen -3-point margin, but not above zero. Its median paired seconds per episode were lower by approximately 20.02% on PushT, 16.24% on Reacher, and 12.85% on Cube. The honest conclusion is equal measured success within uncertainty plus a consistent resource advantage—not superiority.

Full records: [frozen E13 protocol](cluster/prometheus/ACID-ALTERNATIVE-E13-VELOCITY-VS-PRISM-DP-UNTOUCHED-D4-PROTOCOL-2026-08-22.md), [audited E13 result](cluster/prometheus/ACID-ALTERNATIVE-E13-VELOCITY-VS-PRISM-DP-UNTOUCHED-D4-RESULT-2026-08-22.md), and [independent result verifier](cluster/prometheus/verify_gdp_cem_e13_result.py).

## E11 results first, by task

E11 used 400 untouched starts per task, three fixed model/planner seeds, eight arms, and 28,800 closed-loop episodes. All 576 blinded Slurm shards completed before aggregate analysis was unlocked.

| Arm | PushT | Reacher | Cube | Equal-task |
|---|---:|---:|---:|---:|
| Released CEM | 88.83% | 81.92% | 67.83% | 79.53% |
| ACID reconstruction | 88.92% | **85.17%** | 75.83% | 83.31% |
| Reachability (M3) | 88.42% | 80.17% | 68.50% | 79.03% |
| Forward verifier | 88.92% | 82.50% | 71.42% | 80.94% |
| Gaussian selector | 91.33% | 80.67% | 99.92% | 90.64% |
| Shuffled-goal velocity diffusion | 80.67% | 73.58% | 83.75% | 79.33% |
| Unconditional velocity diffusion | 85.50% | 77.17% | 92.50% | 85.06% |
| **Goal-conditioned velocity diffusion** | **95.50%** | 84.67% | **100.00%** | **93.39%** |

The per-task diffusion-minus-ACID differences were +6.58 points on PushT, -0.50 on Reacher, and +24.17 on Cube. The frozen suite rule required a positive aggregate lower confidence bound, wins on at least two tasks, and no loss worse than five points; it passed exactly as written. E8D informed the design of E11, but the E11 implementation, controls, decision rules, and protocol hash were frozen before D3 was generated or evaluated.

The diffusion-minus-Gaussian differences were +4.17 points on PushT, +4.00 on Reacher, and +0.08 on Cube. Cube therefore supports the suite comparison with ACID but does not meaningfully separate diffusion from Gaussian: diffusion succeeded on 1,200/1,200 fixed-seed evaluations and Gaussian on 1,199/1,200.

The primary bootstrap did not resample individual seed-runs as independent. For each task it averaged the three paired fixed-seed outcomes at each of 400 starts, then resampled those start clusters. The inference is conditional on the three fixed seed blocks; it is not a population-of-training-seeds claim.

Full records: [frozen E11 protocol](cluster/prometheus/ACID-ALTERNATIVE-E11-PURE-VELOCITY-UNTOUCHED-D3-PROTOCOL-2026-08-17.md), [launch record](cluster/prometheus/ACID-ALTERNATIVE-E11-D3-LAUNCH-2026-08-17.md), and [audited E11 result](cluster/prometheus/ACID-ALTERNATIVE-E11-PURE-VELOCITY-UNTOUCHED-D3-RESULT-2026-08-18.md).

## What the final method does

The final treatment is a proposal generator, not a plausibility penalty:

1. Freeze Le-WM and encode the current observation and goal.
2. Condition a velocity-prediction diffusion model on those latents.
3. Generate 300 complete 25-action sequences using five deterministic velocity-DDIM evaluations and classifier-free guidance 1.5.
4. Roll the 300 sequences through Le-WM once.
5. Select the sequence with the best predicted goal cost and execute it.

There is no Gaussian initialization, CEM refinement, ACID term, reachability term, or auxiliary verifier in this treatment. The Gaussian arm receives the same training data and conditioning and proposes the same number of action sequences, but represents them with a single diagonal bell-shaped distribution. It must remain in the paper: without it, the experiment would show that learned proposals help, not that diffusion adds anything beyond a simpler learned proposal.

E11 evaluated 300 candidates once per decision. The reconstructed ACID arm evaluated 300 candidates across 30 CEM iterations. Measured aggregate evaluation time was 2,466.1 seconds for diffusion, 2,302.9 seconds for Gaussian, and 27,690.2 seconds for reconstructed ACID. Thus diffusion was about 7.1% slower than Gaussian; the approximately 11.23x ACID speedup belongs mainly to the one-shot proposal architecture, not specifically to diffusion.

## How the research question evolved

### 1. Original question: can a diffusion loss act as a subgoal feasibility meter?

The initial proposal used frozen Hi-LeWM as an experimental chassis. Hi-LeWM would generate candidate latent subgoals, while external auxiliary networks would score the first committed high-level transition:

- B0: ordinary Hi-LeWM high-level CEM.
- B1: empirical-macro proposal restriction from the Hi-LeWM work.
- M1: macro inverse-dynamics cycle consistency, inspired by ACID.
- M2: conditional diffusion denoising error on frozen latent transition pairs.
- M3: a horizon-matched temporal-reachability head.

LeWM is a JEPA-style latent world model, not a diffusion model. The original M2 therefore had to be a separate denoiser trained on real pairs `(z_t, z_(t+Delta))`. At planning time, known noise was added to an imagined subgoal and the denoising residual was used as a candidate score. The hypothesis was that real, supported transitions would be easier to denoise than unsupported imagined transitions.

That architecture was coherent, but the experiments eventually showed that a plausible offline score does not necessarily provide useful within-CEM ranking or closed-loop control.

### 2. Final question: can diffusion generate better action proposals than iterative ACID-guided search?

After several verifier designs failed their prewritten controls, the project stopped treating diffusion as another scalar CEM penalty. The method moved to the part of the problem where diffusion has a clearer architectural advantage: representing a coordinated, potentially multimodal distribution over complete action sequences.

The final research question is therefore:

> On a frozen Le-WM suite, do pure goal-conditioned velocity-diffusion action proposals improve closed-loop success over a capacity- and budget-matched Gaussian proposal, while remaining competitive with released CEM and a transparent published-equation ACID reconstruction?

That pivot must remain explicit in any thesis or paper. The original post-hoc scorer produced important negative results and motivated the redesign; it did not produce E11's positive result.

## Historical development

This chronology was reconstructed on 20 August 2026 from the complete Codex task transcript—1,819 user and assistant messages from 28 July through 20 August—and cross-checked against the dated protocols, hashes, Slurm records, and result reports in this repository. Two explicitly withdrawn, unrelated wrong-chat detours were excluded because they were not part of the thesis.

### 28 July: novelty audit and pre-data protocol

- The starting document was a novelty memo rather than a complete proposal. The first audit concluded that feasibility-aware planning, reachability scoring, and inverse-consistency costs already had substantial precedent, but the exact controlled comparison of action consistency, diffusion support, and temporal reachability at one frozen hierarchical interface appeared not to have been published.
- The honest publication assessment was conditional: strong master's-thesis scope, plausible workshop or paper potential, but no guaranteed main-track novelty from simply adding another cost term.
- The literature map expanded around ACID, trajectory reachability metrics, Hi-LeWM, SAGE, PRISM, WAV, WorldDP, RC-aux, FF-JEPA, hierarchical RL, and diffusion-based out-of-distribution scoring.
- Several rounds of external critique corrected paper titles, author names, mechanisms, metadata confidence, and claim wording. The protocol gained matched controls, shuffled-label nulls, development/confirmation separation, per-environment reporting, and an amendment rule.
- The surviving material was consolidated into the [pre-data master protocol and verified paper map](thesis-master-protocol-and-paper-map-2026-07-28.md); superseded drafts were removed to prevent version drift.

### 28-31 July: compute, storage, and reproducibility decisions

- V100, A100, RTX A6000/RTX 6000 Ada, Colab, RunPod, and dedicated cloud options were compared. The core study required one capable GPU per job rather than model parallelism; 64 GB host RAM was considered comfortable, with candidate microbatching available for smaller VRAM cards.
- Hi-LeWM was chosen as the initial experimental chassis because it supplied frozen predictors, hierarchical planning, checkpoints, environments, and a precise subgoal-scoring interface. It was not an ACID benchmark: ACID had used flat Le-WM, PLDM, DINO-WM, and other stacks.
- A Windows CPU environment and the released checkpoints were validated first. Because the laptop drive was nearly full and Windows paths caused packaging friction, a fresh Ubuntu 24.04 WSL2 distribution and Conda environment were installed on an external Intenso 500 GB SSD.
- The local setup passed the supported preflight and checkpoint tests. Large public datasets were later moved off the SSD; the historical workstation setup is recorded in [REPRODUCIBILITY-SETUP.md](REPRODUCIBILITY-SETUP.md).

### 5-8 August: Prometheus access and bootstrap

- A dedicated Ed25519 SSH identity was created inside the SSD-backed WSL installation. SSH login worked once CYENS provisioned the account; a missing Slurm association was diagnosed and then fixed by IT.
- Live probes established that the `defq` partition exposed RTX A5000 GPUs and the `a6000` partition exposed 48 GB NVIDIA RTX 6000 Ada GPUs. The latter became the primary comparison hardware.
- Prometheus Lustre became the canonical bulk-data and compute location. The SSD retained WSL, configuration, source, selected artifacts, and backups. The current policy is documented in [STORAGE-LAYOUT.md](STORAGE-LAYOUT.md).
- The Hi-LeWM checkpoint evaluation stack was containerized and validated. A checkpoint smoke job completed successfully. One important artifact limitation was recorded: checkpoint evaluation worked, but the released Hi-LeWM training entry point did not contain the advertised trainer.

### 8-12 August: the original Hi-LeWM scorer program

- A small PushT B0/B1 operational pilot returned 42/50 versus 43/50, establishing that the pipeline worked but not providing a thesis result.
- A development environment gate found Cube less useful for the initial hierarchy question: B0 reached 8/12 and empirical-macro B1 5/12, so the frozen rule selected TwoRoom as the second environment.
- A TwoRoom hierarchical backbone was trained and verified, followed by latent extraction and M1/M2/M3 development.
- The original M2 looked promising when candidates were pooled: PushT P2 AUROC was 0.9286 and locked P3 AUROC 0.8032. Its matched nulls were nearly as strong, however, and the predeclared conditional advantage interval included zero.
- A deeper audit found the real issue. Most candidate pools did not contain both successes and failures; pooled AUROC was therefore a poor proxy for the within-query ranking CEM needed. PushT within-pool AUROC was about 0.47, and the TwoRoom online calibration collapsed to a constant penalty.
- M2v2 used conditional-minus-unconditional, multinoise scoring and rank-based calibration. It became genuinely interventional but still failed: PushT did not improve over B0, while TwoRoom's 8/12 versus 6/12 observation was small, exploratory, and also matched by M3. The frozen promotion rule stopped it.

See the [implementation/amendment history](cluster/prometheus/PROTOCOL-IMPLEMENTATION-AMENDMENTS-2026-08-08.md) and [M2v2 result](cluster/prometheus/M2V2-P2-FEASIBILITY-RESULT-2026-08-12.md).

### 12-15 August: direct ACID-suite reconstruction and D1

- The project explicitly corrected an earlier naming problem: M1 was only a single-macro MLP adaptation of ACID, not ACID itself.
- To test the stronger claim, a new flat Le-WM program was built on PushT, Reacher, and Cube with released checkpoints, common datasets, matched starts, native per-step scoring, learned reachability, and a capacity-matched deterministic forward verifier.
- Because the official ACID page still listed code as “coming soon,” ACID was reconstructed from the published equations and disclosed hyperparameters: flow-matching inverse dynamics, standardized actions, per-step residual cost, adaptive CEM weighting, and the paper's candidate/iteration settings. It remains labeled a reconstruction.
- D1's frozen primary diffusion verifier did not establish a robust alternative. It was 3.24 points below ACID and forward at the primary setting, and Reacher was the main failure. A predeclared `lambda=0.005` sensitivity reached 85.19%, which motivated a new study but could not rescue v1 after outcomes were known.

See the [v1 protocol](cluster/prometheus/ACID-ALTERNATIVE-V1-PROTOCOL-2026-08-12.md), [runbook](cluster/prometheus/ACID-ALTERNATIVE-V1-RUNBOOK-2026-08-14.md), and [D1 result](cluster/prometheus/ACID-ALTERNATIVE-D1-RESULT-2026-08-15.md).

### 15-16 August: residual diffusion, multiseed D2, and closed-loop rejection

- V2 trained a residual diffusion verifier and an action-evidence endpoint. It clearly learned action conditioning and improved candidate-failure ranking over v1, but its registered true-versus-shuffled and selection gates did not all pass.
- V3 froze those endpoints across multiple scorer seeds on fresh D2 candidate pools. Four of five Stage-A gates passed. Residual diffusion strongly beat the ACID reconstruction as a failure ranker, but failed the required non-inferiority margin against the simpler deterministic forward verifier.
- A separately frozen E3 exploratory closed-loop study then gave the action-evidence planner its direct chance. Across 2,700 episodes, true action evidence achieved 79.78% equal-task success versus 84.89% for reconstructed ACID and 80.67% for its shuffled control. Only two of five gates passed, producing the frozen decision `stop_diffusion_development_and_pivot`.

See the [V2 result](cluster/prometheus/ACID-ALTERNATIVE-V2-RESIDUAL-DIFFUSION-PILOT-RESULT-2026-08-16.md), [V3 Stage-A result](cluster/prometheus/ACID-ALTERNATIVE-V3-MULTISEED-D2-STAGE-A-RESULT-2026-08-16.md), and [E3 result](cluster/prometheus/ACID-ALTERNATIVE-E3-EXPLORATORY-D2-CLOSED-LOOP-RESULT-2026-08-16.md).

### 16-17 August: last verifier-family tests

- E4 moved diffusion into inverse-action space and introduced conditional inverse denoising evidence. Its P1 diagnostics showed that the models genuinely used the successor, including strong Reacher identification, but the frozen D2A CIDER-tail endpoint had near-zero candidate-ranking value and did not unlock closed-loop D2B.
- E5 used same-model, same-noise counterfactual successors to isolate successor-specific evidence. That signal was anti-predictive on PushT and Cube and damaged the strong forward verifier when combined with it. It did not advance.
- E6 changed integration rather than the model: diffusion vetoed the worst quantile of candidates late in CEM instead of acting as a continuous reward. The primary arm achieved 81.33% versus 88.00% for ACID, 83.33% for shuffled diffusion, and 84.67% for the forward gate. It failed all five advancement gates.
- E6D added the missing all-iteration matched controls. True diffusion reached 85.33%, below continuous ACID at 88.00% and without the required diffusion-specific advantage. This closed the scalar-verifier route.

See the [E4 protocol](cluster/prometheus/ACID-ALTERNATIVE-E4-DIFFUSION-INVERSE-DEVELOPMENT-PROTOCOL-2026-08-16.md), [E5 record](cluster/prometheus/ACID-ALTERNATIVE-E5-COUNTERFACTUAL-DIFFUSION-DEVELOPMENT-2026-08-16.md), [E6 protocol](cluster/prometheus/ACID-ALTERNATIVE-E6-QUANTILE-CONSTRAINED-CEM-PROTOCOL-2026-08-16.md), and [E6D result](cluster/prometheus/ACID-ALTERNATIVE-E6D-ALL-ITERATIONS-MATCHED-CONTROLS-RESULT-2026-08-17.md).

### 17 August: pivot from verification to proposal generation

- E7P trained a goal-conditioned joint-action epsilon-diffusion proposal model with Gaussian and shuffled-goal controls. It contained goal information but pure terminal-noise sampling was unstable and lost to the conditional Gaussian on every task; the frozen decision stopped it before D2.
- E8A used Gaussian-anchored diffusion refinement. It passed all nine P1 gates and showed that true-goal denoising could improve an already competent Gaussian proposal.
- E8D tested that mechanism in exposed-D2 closed loop. True GADR reached 90.67% versus 88.00% for reconstructed ACID, but Gaussian and shuffled proposal arms performed similarly or better. Cube saturated. The prewritten diffusion-specific rule failed, so this result supported learned proposals, not diffusion itself.
- E9 was abandoned before producing a valid result when its proposed method was recognized as a duplicate of the already rejected action-evidence design. The abandonment was retained rather than hidden.

See [E7P](cluster/prometheus/ACID-ALTERNATIVE-E7P-PROPOSAL-SELECTION-RESULT-2026-08-17.md), [E8A](cluster/prometheus/ACID-ALTERNATIVE-E8A-GAUSSIAN-ANCHORED-DIFFUSION-REFINEMENT-RESULT-2026-08-17.md), [E8D](cluster/prometheus/ACID-ALTERNATIVE-E8D-GADR-D2-RESULT-2026-08-17.md), and [E9](cluster/prometheus/ACID-ALTERNATIVE-E9-ABANDONED-DUPLICATE-2026-08-17.md).

### 17-18 August: pure velocity diffusion and untouched confirmation

- E10V replaced unstable epsilon prediction with velocity prediction, added classifier-free goal conditioning, generated directly from noise, and removed Gaussian anchoring and verifier costs. Exactly one of 20 frozen configurations passed all eight P1 gates: five deterministic evaluations with guidance 1.5.
- E10M retrained the selected configuration for seeds 6101, 6102, and 6103. All three independently passed all seven gates. The equal-seed mean selected-action MSE improvement over Gaussian was -0.1297, with consistent shuffled and unconditional advantages.
- Only then was E11 frozen and the untouched D3 holdout consumed once. The positive result at the start of this README is the outcome.

See the [E10V result](cluster/prometheus/ACID-ALTERNATIVE-E10V-PURE-VELOCITY-DIFFUSION-P1-RESULT-2026-08-17.md), [E10M result](cluster/prometheus/ACID-ALTERNATIVE-E10M-MULTISEED-PURE-VELOCITY-P1-RESULT-2026-08-17.md), and [E11 result](cluster/prometheus/ACID-ALTERNATIVE-E11-PURE-VELOCITY-UNTOUCHED-D3-RESULT-2026-08-18.md).

### 18-22 August: audit, E12 validity stop, and E13 PRISM-DP comparison

- Independent critique prompted explicit checks of the E11 gate chronology, bootstrap unit, task-level heterogeneity, Cube saturation, ACID fidelity, and timing attribution. The gate and clustering implementation passed audit; the scientific caveats remained.
- The paper direction was narrowed around the +2.75-point diffusion-versus-Gaussian result. The +10.08-point reconstructed-ACID comparison remains important supporting evidence but cannot all be attributed to diffusion.
- SAGE and PRISM became central related baselines after the method changed from verifier to action proposal. PRISM's released Gaussian/diffusion-policy code and SAGE's goal-conditioned action generation require direct novelty and benchmark audits.
- A diffusion-plus-ACID hybrid was discussed but deliberately deferred. The current method stays pure: diffusion proposes, Le-WM scores once, and no ACID term is added.
- E12 froze a matched PRISM comparison before generating its new D4 holdout. Its 12 native PushT/Cube sanity cells reproduced the released PRISM means closely. All nine matched PRISM-DP reconstructions then passed P1 validity, as did every PushT/Cube Gaussian PriorHead.
- Both PriorHead goal conventions failed the frozen 15% validation-MSE improvement rule on all three Reacher seeds. The final P1-only audit found 21 valid and six invalid artifacts, set `stage_b_passed = false`, and prohibited Stages C and D. No E12 D4 manifest or outcome was generated or read.
- A new DP-only E13 protocol was then frozen separately. It compared the unchanged E11 velocity-diffusion treatment with the already valid disclosed PRISM-DP reconstruction, retained the E11 latent Gaussian as a mechanism control, and generated a new identifier-only D4 holdout behind a 360-shard information barrier.
- At `K=300`, velocity diffusion reached 93.53% versus 92.97% for PRISM-DP. The +0.56-point interval crossed zero and the task effects were mixed, so superiority failed. The frozen compute-efficient-alternative gate passed because the one-sided lower bound stayed inside -3 points while velocity diffusion was faster and lighter on every registered resource test.
- The E13 velocity-minus-Gaussian contrast was +2.56 points with a positive interval, but the mechanism-replication gate failed its registered integrity check because Gaussian Reacher proposals were boundary-limited for two seeds. This outcome was retained without tuning or rerunning D4.

See the [E12 protocol](cluster/prometheus/ACID-ALTERNATIVE-E12-PRISM-MATCHED-UNTOUCHED-D4-PROTOCOL-2026-08-20.md), [implementation changelog](cluster/prometheus/ACID-ALTERNATIVE-E12-IMPLEMENTATION-CHANGELOG-1-2026-08-20.md), [Stage-B validity result](cluster/prometheus/ACID-ALTERNATIVE-E12-STAGE-B-VALIDITY-RESULT-2026-08-22.md), [E13 protocol](cluster/prometheus/ACID-ALTERNATIVE-E13-VELOCITY-VS-PRISM-DP-UNTOUCHED-D4-PROTOCOL-2026-08-22.md), and [E13 result](cluster/prometheus/ACID-ALTERNATIVE-E13-VELOCITY-VS-PRISM-DP-UNTOUCHED-D4-RESULT-2026-08-22.md).

### 23 August: E14 long-horizon development and Gate-B stop

- E14 froze a published-equation SAGE reconstruction and two duration-conditioned diffusion endpoints before training: action-only VAD and coupled subgoal-action CVD. It used PushT and Cube, far-goal offsets 15-150, local durations 15/20/25, 400,000 P1-training rows and 40,000 episode-disjoint P1-validation rows per task, and three fixed model seeds.
- The SAGE reconstruction and all endpoint/control families trained successfully. Scheduler, hidden-CRLF path, checksum-parser, wrapper, and final NumPy-JSON serialization faults were corrected as implementation-only errata without changing scientific inputs or gates.
- VAD beat its Gaussian control on oracle action error and selected true-local Le-WM cost for every seed. The direction held on both tasks at all three durations, and true VAD beat both shuffled-goal and unconditional controls. However, its maximum Cube boundary fractions were 27.17%, 36.38%, and 35.47%, above the frozen 25% limit. PushT stayed below the limit and all banks remained finite with 300 unique candidates.
- CVD improved action coverage, generated-local error, and terminal consistency, but was worse than Gaussian on selected true-local cost for all three seeds, failed the required task-duration direction, and also exceeded the boundary ceiling.
- The final audit therefore recorded `stop_before_gate_c_no_diffusion_endpoint_passed_gate_b`. Gate C was not launched, SAGE was not evaluated in closed loop, and no D5 artifact or protected outcome was read.

See the [E14 protocol](cluster/prometheus/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md), [implementation decisions](cluster/prometheus/ACID-ALTERNATIVE-E14-IMPLEMENTATION-DECISIONS-1-2026-08-23.md), [serialization erratum](cluster/prometheus/E14-GATE-B-SERIALIZATION-ERRATUM-2026-08-23.md), and [Gate-B result](cluster/prometheus/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-GATE-B-RESULT-2026-08-23.md).

### 25 August: post-E14 boundary diagnosis and one-redesign decision

- A six-cell P1-only diagnostic regenerated the frozen VAD banks for PushT and Cube and reproduced all 40,000 stored E14 boundary rows per task/seed.
- Legal limits were mapped through the exact installed float32 `StandardScaler`. Intermediate one-ULP shortcut results were excluded and preserved in the technical record rather than silently reused.
- Cube's raw legal-OOB mean was 2.49%, with per-seed worst-bank values of 27.17%, 36.38%, and 35.47%. The main excess was action coordinate 2. Selection by Le-WM did not materially increase the mean.
- Cube expert actions had zero legal overshoot but substantial legitimate limit saturation. PushT had a small released-data tail outside its declared action box, which the next study must report as a projection rate.
- The diagnosis supports exactly one separately frozen boundary-aware E15 with matched Gaussian and eight-mode GMM controls. It does not reopen E14, produce a SAGE result, or authorize D5.

See the [diagnostic plan](cluster/prometheus/POST-E14-BOUNDARY-DIAGNOSTIC-PLAN-2026-08-25.md), [implementation record](cluster/prometheus/POST-E14-BOUNDARY-IMPLEMENTATION-DECISIONS-1-2026-08-25.md), and [audited result](cluster/prometheus/POST-E14-BOUNDARY-DIAGNOSTIC-RESULT-2026-08-25.md).

### 25 August: E15 boundary-aware redesign and final Gate-B stop

- E15 froze exactly one outcome-informed redesign before model training. It compared boundary-aware VAD with a matched diagonal Gaussian, a direct-goal eight-mode trajectory GMM, shuffled-goal VAD, and unconditional VAD on fresh P1 validation rows from PushT and Cube.
- All 22 trained artifacts passed smoke and Gate A. All 22 sealed validation cells completed before the aggregate was opened, and every bank passed the common legality, diversity, exact-boundary, and expert-relative saturation checks. The transform therefore fixed the technical failure that stopped E14.
- VAD beat Gaussian on both equal-task metrics for seeds 7201, 7202, and 7203. Task-first analysis exposed heterogeneity: VAD won both metrics for Cube at all three durations but improved only action coverage on PushT, where Gaussian retained lower selected true-local Le-WM cost at every duration.
- True VAD passed the shuffled-goal comparison but failed the unconditional null comparison. The unconditional model had slightly lower oracle action error, Cube had no winning duration, and PushT won only `tau=15` under the two-metric rule.
- The final frozen decision was `stop_before_gate_c_frozen_gate_b_failed`. Gate C was not created or launched, the SAGE and GMM closed-loop comparison was not run, and D5 and all other protected evidence remained sealed. Under the preregistered plan, this closes the long-horizon rescue line.

See the [E15 protocol](cluster/prometheus/ACID-ALTERNATIVE-E15-BOUNDARY-AWARE-LONG-HORIZON-PROTOCOL-2026-08-25.md), [implementation decisions](cluster/prometheus/E15-IMPLEMENTATION-DECISIONS-1-2026-08-25.md), and [Gate-B result](cluster/prometheus/ACID-ALTERNATIVE-E15-BOUNDARY-AWARE-LONG-HORIZON-GATE-B-RESULT-2026-08-25.md).

### 27 August: E16 continuation diagnosis and interface stop

- E16 left E15 immutable and replayed the exact seed-7201 VAD banks for all 90,000 role-1 P1 queries per task before computing any new rank diagnostic. Both tasks reproduced E15's selected far and local costs with zero numerical error.
- Far-goal and immediate-local rankings disagreed strongly. Restricting an oracle reranker to the far-ranked top 30 roughly halved selected local cost on both tasks, including the registered long-offset subset. This is concrete headroom for a two-stage selector, not proof that a learned continuation realizes it.
- Replacing half the bank with same-noise zero-guidance samples slightly improved demonstrated-action oracle MSE but worsened the far-selected local cost by 8.46 on PushT and 7.65 on Cube. It was not promoted.
- The preregistered latent-only adapter passed PushT but failed Cube's RMSE, worst-coordinate, and median-R-squared thresholds. As required, no E16 Stage B, closed-loop Stage C, SAGE comparison, or protected holdout was launched.
- The only authorized follow-up is a separately frozen action-conditioned transition-state adapter preflight using exposed P1 data. Full-horizon trajectory diffusion remains outside scope.

See the [E16 protocol](cluster/prometheus/ACID-ALTERNATIVE-E16-CONTINUATION-AWARE-DIRECT-VAD-DEVELOPMENT-PROTOCOL-2026-08-27.md) and [audited diagnostic result](cluster/prometheus/ACID-ALTERNATIVE-E16-CONTINUATION-DIAGNOSTIC-RESULT-2026-08-27.md).

### 27 August: E17 action-conditioned adapter preflight stop

- E17 froze one residual state predictor before opening role-1 output. Its inputs were the current low-dimensional state, current latent, bounded first action chunk, and Le-WM terminal latent; a copy-current predictor was the explicit baseline.
- Both 30,000-step final EMA checkpoints were written before role-1 validation was opened. PushT used 83,215 validation rows and Cube 84,636, with task aggregates and durations 15/20/25 reported separately.
- PushT passed every gate with RMSE 0.0988, worst-coordinate RMSE 0.2353, median coordinate R-squared 0.9989, and a model/copy-current RMSE ratio of 0.0998.
- Cube passed its overall RMSE (0.3560), median coordinate R-squared (0.9982), model/copy ratio (0.2986), and every duration gate. It failed the registered worst-coordinate ceiling: 1.1626 versus 0.8500. Three of 28 coordinate RMSEs exceeded the ceiling.
- Both tasks were mandatory. The final decision was `stop_transition_adapter_preflight_failed`; no continuation planner, SAGE comparison, full-horizon trajectory diffusion, or protected holdout was created or run.

See the [E17 protocol](cluster/prometheus/ACID-ALTERNATIVE-E17-TRANSITION-STATE-ADAPTER-PREFLIGHT-PROTOCOL-2026-08-27.md), [launch record](cluster/prometheus/ACID-ALTERNATIVE-E17-TRANSITION-STATE-ADAPTER-PREFLIGHT-LAUNCH-2026-08-27.md), and [audited result](cluster/prometheus/ACID-ALTERNATIVE-E17-TRANSITION-STATE-ADAPTER-PREFLIGHT-RESULT-2026-08-27.md).

### 28 August: E18 exploratory continuation-planner pass

- E18 preserved the failed E17 decision and both unchanged adapter checkpoints, then asked a distinct planner-level development question on fresh P2 starts. It did not use E17 as authorization and did not read D5 or other protected evidence.
- The frozen planner compared 64-by-8 VAD continuation with greedy VAD at 300 candidates, compute-matched greedy VAD at 576 candidates, diagonal-Gaussian continuation, and direct eight-mode GMM continuation. All arms shared starts, horizons, seeds, Le-WM checkpoints, action maps, and registered rollout budgets.
- All 240 evaluation cells and 720 episodes completed before analysis. A separate verifier reproduced all success tables, 10,000 `(task, base_start)` clustered bootstrap resamples, validity checks, timing summaries, and frozen gates.
- VAD continuation achieved 72.92% equal-task/equal-horizon success, beating greedy VAD-300 by +6.25 points, greedy VAD-576 by +12.50, Gaussian continuation by +6.94, and GMM continuation by +18.06. Its task-average differences were positive for both PushT and Cube against every comparator.
- The 95% intervals were [-0.69, +13.89], [+4.86, +20.83], [-2.78, +16.67], and [+8.33, +27.78] points respectively. Thus the frozen exploratory gates passed, while uncertainty still overlaps zero for the VAD-300 and Gaussian contrasts.
- PushT horizon 150 was the most informative result: 44.44% for VAD continuation versus 25.00% for VAD-300 and Gaussian, 11.11% for VAD-576, and 22.22% for GMM. Cube was ceiling-heavy. VAD continuation was also slower, so E18 is mechanism/performance evidence rather than an efficiency result.
- The final decision is `authorize_drafting_separate_frozen_confirmation_protocol`. No confirmation was launched, E17 remains failed, and E18 is not an untouched-holdout claim.

See the [E18 protocol](cluster/prometheus/ACID-ALTERNATIVE-E18-EXPLORATORY-CONTINUATION-PLANNER-PROTOCOL-2026-08-27.md), [launch record](cluster/prometheus/ACID-ALTERNATIVE-E18-EXPLORATORY-CONTINUATION-PLANNER-LAUNCH-2026-08-27.md), [audited result](cluster/prometheus/ACID-ALTERNATIVE-E18-EXPLORATORY-CONTINUATION-PLANNER-RESULT-2026-08-28.md), and [independent verifier](cluster/prometheus/audit_gdp_cem_e18_result.py).

### 29 August: E19 official SAGE native-reproduction stop

- E19 pinned the public SAGE Git tree and exact Hugging Face checkpoint revision, retained the unchanged official summarizer, and reproduced the complete 180-cell paper grid under a 9,000-episode information barrier.
- All cells completed successfully. The independent audit verified every task, method, horizon, seed, checkpoint, planner setting, source hash, protocol hash, and output hash before performance was read.
- The unchanged official two-point summarizer failed: 29 of 60 released means were within tolerance. The maximum absolute difference was 25.97 points, and the analyzer deliberately returned failure after sealing the complete result.
- Fidelity was heterogeneous rather than uniformly poor. Generator Prior Top passed 12/12 rows, Cube SAGE passed 5/6, and Cube Far-goal Prior CEM passed 5/6. LeWM + Generator passed only 2/12 overall and missed all six Cube rows, with systematic negative gaps up to 25.97 points.
- The identifier-only audit found 270 overlapping PushT episodes and 84 overlapping Cube episodes between the official paper manifests and E18 training. It preserved common untouched candidate sets of 579 PushT and 280 Cube episodes.
- Native reproduction failure and nonzero overlap each block the proposed matched comparison on official paper manifests. No matched protocol or evaluation was launched, and no D5 or other protected metric artifact was read.

See the [E19 protocol](cluster/prometheus/ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-REPRODUCTION-AND-OVERLAP-PROTOCOL-2026-08-28.md), [implementation changelog](cluster/prometheus/E19-IMPLEMENTATION-CHANGELOG-2026-08-28.md), and [audited result](cluster/prometheus/ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-NATIVE-REPRODUCTION-RESULT-2026-08-29.md).

### 30 August: E19 discrepancy diagnostic invalid stop

- A separately frozen diagnostic repeated five prespecified E19 sentinel cells
  twice and completed its fixed-bank official-runtime/transport comparison.
- All ten sentinel jobs and the comparison completed successfully. The sealed
  analyzer then returned failure solely through its final frozen
  `internal_valid` guard, after writing a checksum-valid output manifest.
- Because the analyzer did not terminate successfully, none of its audit,
  trace, bank, rank, cost, elite, cache, or metric-bearing content was opened
  or interpreted. The failed subgate is intentionally not inferred.
- The terminal handling is `diagnostic_invalid_stop_without_e20`. E19 remains
  `stop_native_reproduction_failed`; no E20, author packet, author contact,
  E18-versus-SAGE comparison, or protected-data read occurred.

See the [frozen diagnostic protocol](cluster/prometheus/ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-DISCREPANCY-DIAGNOSTIC-PROTOCOL-2026-08-29.md), [implementation changelog](cluster/prometheus/E19-DISCREPANCY-IMPLEMENTATION-CHANGELOG-2026-08-29.md), and [terminal result](cluster/prometheus/ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-DISCREPANCY-DIAGNOSTIC-RESULT-2026-08-30.md).

### 30 August: E19-D2 method-aware discrepancy reanalysis

- Static source inspection proved that the first diagnostic analyzer required
  a history-latent event that official generator-free PushT `base_cem` cannot
  emit. This defect was independent of any sealed outcome.
- E19-D2 changed only that event expectation, imported the byte-identical
  parent mismatch definitions and E20 rules, and reused the checksum-verified
  raw sentinel, trace, bank, and comparison artifacts without rerunning them.
  The failed parent analyzer output remained unread.
- The corrected validity-only stage passed all six gates, and the sealed
  classification completed successfully with `internal_valid=true`.
- Exact repeatability failed for all five sentinels: every fresh-process trace
  and first-call bank hash changed. Four of five coarse outcomes repeated
  exactly, and three of five matched their original E19 outcomes exactly.
- Compatibility-loaded and strict official-runtime LeWM state, latents, costs,
  ranks, and elites matched on every tested real bank. The Cube cache audit
  also passed 4,530 events and 1,056 scoped stage keys without a mismatch.
- PushT lossless-HDF5 versus JPEG/Lance transport changed latents, costs,
  candidate order, and elite membership in 31/50 `base_cem` and 39/50
  `far_goal_prior_cem` environments.
- The two objective mismatch classes are non-unique, so the frozen decision is
  `prepare_author_evidence_no_unique_e20_correction` with
  `e20_authorized=false`. E19 and the first diagnostic keep their original
  failed decisions. No E20, protected-data read, E18-versus-SAGE comparison,
  or author contact occurred.

See the [E19-D2 protocol](cluster/prometheus/ACID-ALTERNATIVE-E19-D2-METHOD-AWARE-DISCREPANCY-REANALYSIS-PROTOCOL-2026-08-30.md), [implementation changelog](cluster/prometheus/E19-D2-IMPLEMENTATION-CHANGELOG-2026-08-30.md), [audited result](cluster/prometheus/ACID-ALTERNATIVE-E19-D2-METHOD-AWARE-DISCREPANCY-REANALYSIS-RESULT-2026-08-30.md), and [review packet](cluster/prometheus/e19-d2-author-evidence/README.md).

### 5 September: fresh E18 scientific-driver integration

- Preserved the accepted R3 initializer and all frozen E18 model/planner bytes.
- Proved real-input pixel-only encoder dependence and raw-state checkpoint
  normalization; matched action decoding to all three tested proposer families.
  Independently pinned all nine existing training checkpoints and verified their
  normalization payloads agree, with no dataset read or fit.
- One frozen GPU attempt, job300308, passed. Fifty exposed-record initializations,
  128 real planning calls and1,363 actions exercise both schedules, independent
  three-slot interleaving, replanning, early/budget termination and reinitialization.
- No historical SAGE-fidelity or efficacy claim, new holdout, model change,
  restoration redesign or automatic scientific run. The PushT engineering gate
  is closed; statistical scope/effect choices remain before confirmation freeze.
  See [plan](cluster/prometheus/E18-FRESH-DRIVER-INTEGRATION-PLAN-2026-09-05.md),
  [result](cluster/prometheus/E18-FRESH-DRIVER-INTEGRATION-RESULT-2026-09-05.md),
  [implementation history](cluster/prometheus/E18-FRESH-DRIVER-IMPLEMENTATION-CHANGELOG-2026-09-05.md)
  and [protocol draft](cluster/prometheus/E18-FRESH-CONFIRMATION-PROTOCOL-DRAFT-2026-09-05.md).

### 5 September: E19-R3 opt-in fresh-state initialization

- Implemented the user-approved instantaneous initialization contract using new
  native physics construction and public spatial reindex; retained legacy source
  and stepping. Exposed data do not contain block momentum/contact state, so
  defaults are explicit assumptions. Fresh observations replace dataset overlays.
- Core job300301 passed48 exposed-record scenarios with96 fresh resets and no
  initialization physics step. Successful arm job300304 passed all ten real
  checkpoint-backed methods at batches3/50, with560 initializations and885 short
  fixed primitive actions; no solver or benchmark metric was used.
- Preserved failed harness300302: reused SAGE policy call metadata was not reset
  by native set_env. Constructed fresh policies for the replacement gate without
  modifying the initializer, native source or a private counter.
- Signed-velocity bounds corrected separately. E18 non-action normalization
  remains an explicitly disclosed raw-input boundary; no holdout statistics fit.
  See the [result](cluster/prometheus/E19-R3-INITIALIZATION-RESULT-2026-09-05.md),
  [interface](cluster/prometheus/PUSHT-FRESH-INITIALIZATION-INTERFACE.md) and
  [implementation record](cluster/prometheus/E19-R3-IMPLEMENTATION-CHANGELOG-2026-09-05.md).

### 5 September: E19-R2 targeted restoration localization

- Job 300299 completed 24 fresh one-action engineering runs on two exposed
  PushT records, with native resets and prespecified explicit seeds 32/33.
  Requested fields were exact before physics; seed-dependent contact-state
  carryover produced different restored block poses despite paired repeatability.
- Job 300300 performed eight isolated contact-geometry probes with no actions.
  The bad R1 reset geometries reproduced the kind of displacement, not the
  exact historical values; its seed-32 baseline was not contact-neutral.
  The limitation and all residuals are preserved, without a retry to improve fit.
- Source/old-trace audit clarified R1 Cube global seeding and classified all
  56 out-of-bounds observations among 180 checked R1 PushT steps as E18
  signed-velocity declaration violations.
- No historical decision, diffusion model or production environment changed.
  The restoration contract must be approved before dynamic arm/batch checks
  or confirmation. See the [result](cluster/prometheus/E19-R2-LOCALIZATION-RESULT-2026-09-05.md)
  and [implementation history](cluster/prometheus/E19-R2-IMPLEMENTATION-CHANGELOG-2026-09-05.md).

### 5 September: E19-R1 reset and fixed diagnostic stimulus

- Authorized saved-candidate substitution was labelled as an engineering
  stimulus, never a historical selected CEM plan. The prior-top control used
  saved returned actions. Candidate choice was index-based, not cost-based.
- Job 300297's twelve PushT traces were complete; its eight Cube traces
  mixed native reset steps into the action counter and lacked before-action
  coverage. They remain preserved. A regression-tested counter correction
  reran only those eight Cube cases in job 300298 with unchanged stimuli.
- The twenty valid traces passed seals, identity and complete 15-step
  coverage checks. Actual paired actions agreed. PushT restoration had
  physical counterexamples in both stacks; Cube restored specified state
  exactly but retained other integration-state differences.
- Decision: hold confirmation pending restoration-contract resolution. No
  model/environment repair, E20, new benchmark, author contact or holdout.
  See the [result](cluster/prometheus/E19-R1-RESET-FIXED-STIMULUS-RESULT-2026-09-05.md)
  and [implementation history](cluster/prometheus/E19-R1-IMPLEMENTATION-CHANGELOG-2026-09-05.md).

### 5 September: E19-L1 exposed-artifact localization

- Kept E19, the first invalid diagnostic, E19-D2 and the old author packet
  unchanged. The historical two-class rule remains part of D2, not a general
  ban on future objectively justified repairs.
- Verified the ten exposed runs' 40 sealed files and five original baseline
  hashes. Compared actual tensors, all recorded CEM updates and paired episode
  outcomes. No opaque `repr` record occurred; all five first computational
  planning calls were exact. Later observation/state drift remains unresolved
  at the simulator reset/step boundary.
- Fixed-bank job `300296` passed 12 exact-environment tests, all eight original
  elite/mean/std reconstructions and exact historical cost replays. Preserved
  the prior report-serialization failure `300295` and documented its narrow
  nonfinite-metadata correction.
- Quantified transport changes as 46 and 74 replacements out of 1,500 elite
  slots, rather than interpreting the 31/50 and 39/50 any-change flags as
  wholesale replacement or a demonstrated success loss.
- Added three CPU reduction tests, an independent package verifier, the E18
  shared-infrastructure review and confirmation outline. The existing E18
  unit suite passed 12 tests. No new episode, holdout, training, E20, SAGE
  comparison or author contact occurred.

See the [plan](cluster/prometheus/E19-L1-EXPOSED-ARTIFACT-LOCALIZATION-PLAN-2026-09-05.md), [implementation history](cluster/prometheus/E19-L1-IMPLEMENTATION-CHANGELOG-2026-09-05.md), [result](cluster/prometheus/E19-L1-EXPOSED-ARTIFACT-LOCALIZATION-RESULT-2026-09-05.md) and [review packet](cluster/prometheus/e19-l1-evidence/README.md).

## Compact experiment ledger

| Stage | Question | Outcome |
|---|---|---|
| Hi-LeWM B0/B1 pilot | Does the released hierarchy run correctly? | Operational pass; no thesis claim. |
| Original M2/P3 | Does latent denoising error identify failed subgoals? | Some pooled signal; conditional advantage and within-pool ranking gate failed. |
| M2v2 | Do conditional-minus-unconditional multinoise scores improve planning? | Interventional but no PushT gain; stopped before confirmation. |
| D1/v1 | Does a per-step diffusion transition verifier match reconstructed ACID? | Primary method lost; low-weight sensitivity motivated a new study only. |
| V2 | Does residual diffusion restore action use? | Stronger ranking and action signal; not all gates passed. |
| V3 Stage A | Does the effect replicate across seeds on fresh D2 pools? | Beat ACID ranking, but failed non-inferiority to deterministic forward. |
| E3 | Does action evidence improve independently optimized CEM? | 79.78% versus 84.89% ACID and 80.67% shuffled; failed. |
| E4-E6D | Can inverse evidence, counterfactuals, or quantile vetoes rescue a diffusion verifier? | No frozen endpoint isolated a useful diffusion-specific planner effect. |
| E7P | Can pure epsilon diffusion propose actions? | Goal-aware but unstable and worse than Gaussian. |
| E8A | Can diffusion refine Gaussian proposals on P1? | All P1 gates passed. |
| E8D | Does Gaussian-anchored refinement help closed loop? | Learned proposals helped; diffusion-specific gate failed. |
| E9 | Duplicate action-evidence retry | Abandoned transparently before a valid evaluation. |
| E10V | Can pure velocity diffusion beat matched P1 controls? | One frozen configuration passed every gate. |
| E10M | Does that configuration replicate across model seeds? | All three seeds passed every gate. |
| E11 | Does pure diffusion work on untouched D3 closed loop? | Positive: 93.39%, +2.75 points over Gaussian, +10.08 over ACID reconstruction. |
| E12 | Does E11 remain favorable against matched PRISM-style proposal competitors? | Stopped before P2/D4: all DP reconstructions were valid, but both PriorHeads failed on every Reacher seed. |
| E13 | Is pure velocity diffusion competitive with the valid disclosed PRISM-DP reconstruction on untouched D4? | No superiority: +0.56 points, interval [-0.47, +1.58]. Passed the frozen compute-efficient-alternative gate; fresh Gaussian mechanism gate failed its integrity condition. |
| E14 | Does duration-conditioned diffusion support SAGE-style long-horizon planning? | Stopped at offline Gate B: VAD beat Gaussian and null controls but exceeded the Cube boundary ceiling; CVD also failed matched terminal cost. No closed-loop SAGE comparison. |
| Post-E14 diagnosis | Was E14's Cube boundary failure artificial, expert-like saturation, or selection-induced? | Genuine raw overshoot plus hard clipping on a minority of Cube banks; expert saturation itself is legitimate; Le-WM selection was not the main cause. One separately frozen redesign is justified. |
| E15 | Does one boundary-aware redesign preserve VAD's mechanism and support a fair GMM/SAGE comparison? | Bank integrity and GMM structure passed, but VAD failed the PushT task-first direction and unconditional-null rule. Stopped before Gate C; no SAGE comparison or D5. |
| E16 | Did E15's exact VAD banks contain better first branches than greedy far-endpoint selection exposed, and could the fixed latent-only interface support continuation? | Substantial top-k oracle reranking headroom on both tasks; zero-guidance mixture worsened selection. PushT adapter passed, Cube adapter failed, so no continuation or closed-loop stage ran. |
| E17 | Can current state plus the proposed first action chunk and Le-WM latents provide a safe transition-state interface for the conservative continuation reranker? | PushT passed. Cube improved strongly and passed all duration gates but failed the frozen worst-coordinate RMSE ceiling (1.163 versus 0.850). Both tasks were required, so no planner study ran. |
| E18 | Can the unchanged failed-E17 adapter still provide useful ranking information inside the actual 64-by-8 continuation planner on development-only starts? | Positive exploratory result: 72.92% equal-task/equal-horizon success; +6.25 points over greedy VAD-300, +12.50 over compute-matched VAD-576, +6.94 over Gaussian continuation, and +18.06 over GMM continuation. Both frozen gates passed, but intervals overlapped zero versus VAD-300 and Gaussian. E17 remains failed; no D5 confirmation ran. |
| E19 | Does the pinned official SAGE release reproduce its complete paper grid, and are its episode manifests disjoint from E18 training? | No. All 180 cells and 9,000 episodes were valid, but the unchanged ±2-point summarizer passed only 29/60 means; maximum gap 25.97 points. Official manifests also overlapped E18 training by 270 PushT and 84 Cube episodes. No matched comparison was authorized. |
| E19 discrepancy diagnostic | Can exact sentinel repeats and read-only intermediate comparisons isolate one objective technical cause of the E19 gap? | Invalid stop. Ten sentinel repeats and the fixed-bank comparison completed, but the sealed analyzer failed its frozen internal-validity gate. Outputs were not interpreted; no mismatch class, E20, or author packet was authorized. |
| E19-D2 reanalysis | Does the outcome-independent method-event defect explain the first diagnostic's invalidity, and does a method-aware gate isolate one unique cause? | The corrected analyzer was valid, but found two classes: exact fresh-process repeatability failed for all five sentinels, and PushT JPEG/Lance transport changed elite membership. Runtime-load and Cube-cache parity passed. Multiple classes forbid E20; an unsent evidence packet was prepared. |
| E19-L1 engineering localization | What actually differs in the exposed repeats, and are the tracer/transport flags established causes? | All first planning calls and fixed-input CEM replays agree; later state/observation drift produces one flip in 250 paired outcomes. Transport replaces a mean 0.92/30 and 1.48/30 elites. No author-encoding mismatch or full-table root cause is established; no new episode or E20 ran. |

## ACID comparator status

The repository contains a clean-room, published-equation ACID reconstruction, not the authors' official code. The implementation follows the disclosed architecture and training/planning choices, including a four-layer, three-head width-192 flow-matching inverse model, standardized actions, Euler inference, a per-step consistency cost, adaptive scaling, 200,000 updates, and the 300-candidate/30-iteration/30-elite CEM setting.

Important choices were necessarily reconstructed because the paper did not specify every implementation detail. The local training split also differs from the paper's described data use, and the local R0 gains do not match the paper's reported task pattern closely enough to treat fidelity as settled. Consequently:

- Allowed: “published-equation ACID reconstruction,” with local numbers and caveats.
- Not allowed: “official ACID,” “exact ACID reproduction,” or unqualified “diffusion beats ACID.”
- Required next work: line-by-line implementation appendix, neutral request to the authors for code/checkpoints or clarification, and a development-only ACID compute-budget curve at candidate counts 30, 50, 150, and 300.

## Current publication plan

The method and all E11--E19 evidence stay frozen. E17 triggered its prewritten two-task stop rule and remains failed. E18 nevertheless found a positive planner-level development signal with the unchanged checkpoint and passed its separately frozen rules. E19 then showed that the pinned official SAGE release does not reproduce its full paper table under the release's own tolerance, and that the official paper manifests overlap E18 training. E19-D2 found non-unique repeatability and PushT transport discrepancies, so it does not authorize an E20 rerun. E18's narrow authorization for a standalone confirmation protocol remains distinct, but official SAGE paper values and manifests cannot supply a validated matched comparator. The focused next work is:

1. Build the thesis/paper manuscript around task-first E11 and E13 results before pooled results, including Cube saturation and the opposite PushT/Reacher E13 effects.
2. Report E14 and E15 together as transparent development evidence: E14 identified the boundary failure, E15 fixed it technically but failed the task-robust mechanism and unconditional-null rules. Do not imply a closed-loop SAGE result.
3. Report E12's PRISM artifact-validity stop and E13's non-superiority/compute-efficiency result, always limiting PRISM claims to the disclosed reconstruction.
4. Complete the line-by-line ACID fidelity appendix, published-number comparison, and compute-budget curve as secondary evidence. Keep diffusion-plus-ACID outside the present method.
5. Finish reproducibility packaging, frozen-table generation, limitations, and the author-code/checkpoint correspondence record before starting another benchmark family.
6. Keep E18 confirmation separate from SAGE reproduction fidelity. The scoped PushT fresh-initialization and actual-driver engineering gates are now passed; resolve the confirmation draft's task scope/effect target and sample-size feasibility before the final protocol/record freeze. No further PushT restoration redesign is required by these passed gates. E19-L1 qualifies the interpretation of D2's flags without changing its failed authorization decision; the historical exactly-one-class rule is not a universal prohibition on future documented, source-justified repairs. Await the authors' exact artifacts and prepare evidence supplements for user review; never contact them automatically. Do not use the released SAGE means as a validated baseline or draft/launch a matched comparison on its overlapping official paper manifests. Any later matched comparison needs a separately justified, episode-disjoint protocol and explicit authorization. Do not tune E18, change failed E15--E17 gates, or consume D5 automatically. Consider a separately justified PLDM cross-backbone study only after the manuscript-gap review.

The paper's most defensible established headline remains approximately:

> Across frozen untouched Le-WM evaluations, goal-conditioned velocity diffusion improved success by 2.75 points over a matched learned Gaussian proposal and matched a disclosed PRISM-DP reconstruction within a prespecified three-point margin while using fewer learned parameters and lower inference resources.

## Repository layout

```text
.
├── README.md
├── thesis-master-protocol-and-paper-map-2026-07-28.md
├── REPRODUCIBILITY-SETUP.md
├── STORAGE-LAYOUT.md
├── requirements-wsl-cpu-lock.txt
├── verify_wsl_setup.py
└── cluster/prometheus/
    ├── ACID-ALTERNATIVE-*.md       # frozen protocols, amendments, and reports
    ├── acid_alternative/           # core comparator/model/evaluation package
    ├── acid_alternative_diagnostics/
    ├── *.py                        # training, evaluation, analysis, and audits
    ├── *.slurm and *.sh            # Prometheus orchestration
    ├── tests/                      # integrity/submission-graph tests
    ├── manifests/                  # small reproducibility manifests
    └── cluster-state/              # selected immutable provenance records
```

The flat `cluster/prometheus` layout is historical: scripts were synchronized directly with the cluster during rapid, frozen experiment cycles. It is retained so recorded paths, hashes, and Slurm commands continue to resolve.

## Data and artifacts not stored in Git

This repository intentionally excludes public datasets, released upstream checkpoints, trained model weights, latent caches, Apptainer images, raw per-episode results, bulk candidate pools, upstream source checkouts, SSH material, and local backups. They are too large, reproducible from official sources, security-sensitive, or all three.

Canonical bulk working data live under the CYENS Prometheus Lustre project. Selected irreplaceable artifacts and recovery material are backed up on the external SSD. Summary reports and content hashes are tracked here so a result can be identified without committing bulk data. See [STORAGE-LAYOUT.md](STORAGE-LAYOUT.md) and the manifests under `cluster/prometheus`.

## Reproducibility notes

- Primary timed experiments used NVIDIA RTX 6000 Ada GPUs through Slurm on Prometheus.
- Released Le-WM/Hi-LeWM and stable-worldmodel components are external dependencies and are not vendored here.
- The local WSL CPU setup is a historical verification environment; after 8 August, bulk datasets and checkpoints moved to Prometheus.
- Result Markdown files are summaries of immutable bundles. Raw outputs remain on Prometheus and in selected SSD backups.
- Any manuscript table should be generated from the frozen aggregate bundle or recomputed from its paired-outcome files, never copied from chat prose.
- Paper metadata and BibTeX should be generated from primary records at writing time; the July paper map is a verified planning document, not a permanent bibliographic database.

## Claim boundary

The repository supports a scoped positive result for the tested Le-WM suite and fixed seed blocks. It does not establish universal superiority, an official ACID reproduction, official-PRISM performance, a population-of-training-seeds effect, or that every diffusion formulation is useful. E13 supports a compute-efficient-alternative claim against the disclosed PRISM-DP reconstruction, not superiority. E14 does not establish long-horizon closed-loop performance because its endpoints stopped at bank validity. E15 fixed that bank-validity problem but then failed its task-robust VAD and unconditional-null requirements, so it also establishes no SAGE or long-horizon closed-loop comparison. E19 executed official SAGE but failed the unchanged release-fidelity gate and found nonzero episode overlap with E18 training; it therefore does not establish an efficacy comparison against official SAGE. The repository preserves these negative studies because they explain the final method's scope and prevent selective reporting.
