# Goal-Conditioned Velocity Diffusion for Le-WM Planning

Research repository for Christoforos Kontzias's University of Cyprus thesis on feasibility-aware planning with latent world models.

The project began as a comparison of post-hoc feasibility scores for hierarchical subgoals. It eventually produced a different and stronger method: a pure goal-conditioned velocity-diffusion model that proposes complete action sequences for a frozen Le-WM, followed by one model-cost evaluation. The change of method is central to the scientific record. The successful E11 method is **not** the original auxiliary diffusion-loss scorer.

## Current status

As of 27 August 2026, two frozen untouched-holdout studies support complementary conclusions. The E14 long-horizon development study, its single preregistered E15 redesign, the E16 continuation diagnostic, and the E17 interface preflight all stopped before any closed-loop long-horizon comparison.

E11 remains the cleanest diffusion-specific result. On PushT, Reacher, and Cube, goal-conditioned velocity diffusion achieved 93.39% equal-task success, compared with 90.64% for a matched learned Gaussian selector and 83.31% for a published-equation reconstruction of ACID. Diffusion exceeded Gaussian by **+2.75 percentage points**, with a 95% paired start-cluster interval of **[+1.64, +3.89]**. Its **+10.08-point** comparison with reconstructed ACID, interval **[+8.31, +11.89]**, combines the learned one-shot-proposal advantage with the narrower diffusion-specific effect.

E13 resolved the direct comparison with a disclosed PRISM-DP reconstruction on a new untouched D4 holdout. At the primary `K=300` budget, velocity diffusion achieved 93.53% and PRISM-DP 92.97%: **+0.56 points**, 95% interval **[-0.47, +1.58]**. That does not establish superiority. It does pass the frozen compute-efficient-alternative gate: the one-sided lower bound remained inside the -3-point margin, and velocity diffusion was faster on every task while using fewer learned parameters, no second image encoder, and less peak CUDA memory.

E13's velocity-versus-Gaussian point difference was +2.56 points with interval [+1.39, +3.72], but the frozen mechanism-replication gate failed because the Gaussian Reacher proposals exceeded the registered 25% boundary/clipping limit for two seeds. This result may be reported, but not as an unqualified fresh mechanistic confirmation. Cube was saturated again, and the PRISM-DP task effects were mixed: velocity diffusion was -1.67 points on PushT, +3.33 on Reacher, and tied on Cube.

E14 tested whether the method could extend to variable-duration, long-horizon planning under SAGE's task and schedule interface. VAD diffusion beat its matched Gaussian on both registered offline metrics for all three seeds, on both PushT and Cube at every local duration, and beat shuffled-goal and unconditional controls. It nevertheless violated the frozen 25% proposal-boundary ceiling on Cube for all three seeds. CVD failed that integrity condition and the matched Gaussian terminal-cost comparison. Therefore neither endpoint entered Gate C: no P2 long-horizon closed-loop result, SAGE efficacy comparison, or D5 confirmation was produced. The [audited E14 Gate-B result](cluster/prometheus/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-GATE-B-RESULT-2026-08-23.md) is a promising mechanism result plus an honest validity stop, not a new paper claim.

The [post-E14 boundary diagnosis](cluster/prometheus/POST-E14-BOUNDARY-DIAGNOSTIC-RESULT-2026-08-25.md) reproduced every E14 boundary row and compared raw proposals with the exact deployed float32 action transforms. Cube's mean legal overshoot was about 2.49%, while the worst query banks reached the same 27--36% values that stopped E14; selected and full-bank means were nearly identical. Cube experts were legal but genuinely saturated at several coordinates. The correct target for one separately frozen E15 is therefore overshoot and hard clipping, not all boundary use. E14 remains failed and D5 remains sealed.

E15 applied one common smooth, legality-preserving action representation to boundary-aware VAD, a matched diagonal Gaussian, a direct eight-mode trajectory GMM, and the VAD conditioning nulls. All 22 banks passed the new expert-relative integrity rules with zero legal OOB values, zero exact boundary values, and 300 unique candidates; all six GMM task/seed banks passed their structural checks. VAD also beat Gaussian on both equal-task primary metrics for every seed. The mechanism gate still failed: Cube won both metrics at every duration, but PushT's selected true-local cost was worse than Gaussian at every duration, and true VAD did not beat unconditional VAD on the full frozen null rule. The final decision was `stop_before_gate_c_frozen_gate_b_failed`; no Gate C, SAGE efficacy comparison, or D5 result was produced. See the [audited E15 Gate-B result](cluster/prometheus/ACID-ALTERNATIVE-E15-BOUNDARY-AWARE-LONG-HORIZON-GATE-B-RESULT-2026-08-25.md).

E16 then tested the narrower hypothesis that E15's one-chunk far endpoint was a poor selector even when its VAD bank contained useful first branches. Exact replay of 90,000 seed-7201 validation banks per task found real oracle reranking headroom: on genuine far-goal rows, reranking only the far-ranked top 30 reduced mean next-local cost from 32.99 to 14.55 on PushT and from 68.06 to 34.94 on Cube. A fixed half-standard/half-zero-guidance bank was worse on both tasks, so low guidance was not promoted. The required latent-only state adapter passed PushT but failed all three frozen Cube thresholds (RMSE 0.805, maximum coordinate RMSE 1.698, median coordinate R-squared 0.401). E16 Stages B and C therefore remained blocked. The [audited E16 diagnostic result](cluster/prometheus/ACID-ALTERNATIVE-E16-CONTINUATION-DIAGNOSTIC-RESULT-2026-08-27.md) establishes candidate-ranking headroom, not closed-loop continuation efficacy.

E17 was the separately frozen follow-up interface preflight. It supplied current state, current latent, the bounded first action chunk, and Le-WM's terminal latent to a fixed residual state predictor. PushT passed comfortably. Cube improved dramatically over E16 and passed its overall, copy-current, median-R-squared, and all duration gates, but its worst-coordinate RMSE was 1.163 against the frozen 0.850 ceiling. Because both tasks were required, E17 stopped without a planner experiment, SAGE comparison, full-horizon diffusion, or protected-holdout use. See the [protocol](cluster/prometheus/ACID-ALTERNATIVE-E17-TRANSITION-STATE-ADAPTER-PREFLIGHT-PROTOCOL-2026-08-27.md), [launch record](cluster/prometheus/ACID-ALTERNATIVE-E17-TRANSITION-STATE-ADAPTER-PREFLIGHT-LAUNCH-2026-08-27.md), and [audited result](cluster/prometheus/ACID-ALTERNATIVE-E17-TRANSITION-STATE-ADAPTER-PREFLIGHT-RESULT-2026-08-27.md).

The resulting paper claim is scoped: pure velocity diffusion is a strong learned action proposer and a compute-efficient alternative to the tested disclosed PRISM-DP reconstruction. The repository does not establish universal superiority, an official ACID reproduction, or a comparison with official PRISM.

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

## ACID comparator status

The repository contains a clean-room, published-equation ACID reconstruction, not the authors' official code. The implementation follows the disclosed architecture and training/planning choices, including a four-layer, three-head width-192 flow-matching inverse model, standardized actions, Euler inference, a per-step consistency cost, adaptive scaling, 200,000 updates, and the 300-candidate/30-iteration/30-elite CEM setting.

Important choices were necessarily reconstructed because the paper did not specify every implementation detail. The local training split also differs from the paper's described data use, and the local R0 gains do not match the paper's reported task pattern closely enough to treat fidelity as settled. Consequently:

- Allowed: “published-equation ACID reconstruction,” with local numbers and caveats.
- Not allowed: “official ACID,” “exact ACID reproduction,” or unqualified “diffusion beats ACID.”
- Required next work: line-by-line implementation appendix, neutral request to the authors for code/checkpoints or clarification, and a development-only ACID compute-budget curve at candidate counts 30, 50, 150, and 300.

## Current publication plan

The method and all E11--E17 evidence stay frozen. E17 triggered its prewritten two-task stop rule, so this continuation line is closed before planner evaluation. The focused next work is:

1. Build the thesis/paper manuscript around task-first E11 and E13 results before pooled results, including Cube saturation and the opposite PushT/Reacher E13 effects.
2. Report E14 and E15 together as transparent development evidence: E14 identified the boundary failure, E15 fixed it technically but failed the task-robust mechanism and unconditional-null rules. Do not imply a closed-loop SAGE result.
3. Report E12's PRISM artifact-validity stop and E13's non-superiority/compute-efficiency result, always limiting PRISM claims to the disclosed reconstruction.
4. Complete the line-by-line ACID fidelity appendix, published-number comparison, and compute-budget curve as secondary evidence. Keep diffusion-plus-ACID outside the present method.
5. Finish reproducibility packaging, frozen-table generation, limitations, and the author-code/checkpoint correspondence record before starting another benchmark family.
6. Do not rescue E15--E17 by changing a failed gate, and do not consume D5. Consider a separately justified PLDM cross-backbone study only after a manuscript-gap review with the supervisor; it must not reinterpret the stopped long-horizon sequence.

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

The repository supports a scoped positive result for the tested Le-WM suite and fixed seed blocks. It does not establish universal superiority, an official ACID reproduction, official-PRISM performance, a population-of-training-seeds effect, or that every diffusion formulation is useful. E13 supports a compute-efficient-alternative claim against the disclosed PRISM-DP reconstruction, not superiority. E14 does not establish long-horizon closed-loop performance because its endpoints stopped at bank validity. E15 fixed that bank-validity problem but then failed its task-robust VAD and unconditional-null requirements, so it also establishes no SAGE or long-horizon closed-loop comparison. The repository preserves these negative diffusion studies because they explain the final method's scope and prevent selective reporting.
